"""Read-only offline-to-live inference readiness audit for the vNext v7/v5
action-rank checkpoint.

Loads the rank-only config + checkpoint, strictly validates schema/dimension/
fingerprint metadata, runs a controlled inference path (the same model scoring a
live decision would use), checks that each selected candidate maps to a valid
Showdown choice string (with Tera distinct), cross-checks score parity against
``evaluate_vnext_action_rank``, measures model-scoring latency, and scans the
current live code paths for v2/v3 assumptions.

Does not train, promote checkpoints, change live defaults, or run any matches.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import torch

from .evaluate_vnext_action_rank import evaluate as offline_evaluate
from .train_vnext_diagnostic import (
    build_diagnostic_model,
    load_and_validate_diagnostic_config,
    load_diagnostic_dataset,
    validate_vnext_checkpoint_metadata,
)

VALID_CANDIDATE_KINDS = {"move", "move_tera", "switch"}
# Live files audited for legacy v2/v3 assumptions and vNext readiness.
LIVE_FILES = (
    "trainer/src/neural/live_action_recommender.py",
    "trainer/src/neural/live_eval_server.py",
)
VNEXT_MARKERS = (
    "VNextDiagnosticMLP",
    "legal-action-v5",
    "live-private-belief-v7",
    "build_action_feature_vector_v5",
    "resolve_action_impact",
)
LEGACY_MARKERS = (
    "ActionRankerMLP",
    "build_action_feature_vector(",
    "np.pad",
    "move_tera",
)


def candidate_to_showdown_command(kind: str, action_index: int) -> Optional[str]:
    """Contract a live serializer must honor (slot indexing reconciled live).

    Tera is a distinct command from the plain move; switches use the switch verb.
    """
    if kind == "move":
        return f"move {action_index}"
    if kind == "move_tera":
        return f"move {action_index} terastallize"
    if kind == "switch":
        return f"switch {action_index}"
    return None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _scan_live_paths() -> Dict[str, Any]:
    root = _repo_root()
    findings: Dict[str, Any] = {}
    for rel in LIVE_FILES:
        path = root / rel
        if not path.is_file():
            findings[rel] = {"exists": False}
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        findings[rel] = {
            "exists": True,
            "vnext_marker_hits": {m: text.count(m) for m in VNEXT_MARKERS if text.count(m)},
            "legacy_marker_hits": {m: text.count(m) for m in LEGACY_MARKERS if text.count(m)},
        }
    any_vnext = any(f.get("vnext_marker_hits") for f in findings.values() if isinstance(f, dict))
    return {"files": findings, "any_live_file_references_vnext": bool(any_vnext)}


def audit_readiness(
    config_path: Path,
    checkpoint_path: Path,
    *,
    split: str = "validation",
    sample_groups: int = 200,
) -> Dict[str, Any]:
    config = load_and_validate_diagnostic_config(config_path)
    dataset = load_diagnostic_dataset(config)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

    # 1) Strict schema/fingerprint validation (fingerprints required for live use).
    schema_validation = validate_vnext_checkpoint_metadata(
        checkpoint,
        expected_state_feature_names_sha256=dataset.validation["state_feature_names_sha256"],
        expected_action_feature_names_sha256=dataset.validation["action_feature_names_sha256"],
        require_fingerprints=True,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_diagnostic_model(config).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    parameter_count = int(sum(p.numel() for p in model.parameters()))

    groups = dataset.split_group_state_indices[split]
    sampled = groups[: max(1, int(sample_groups))]

    kind_counts: Dict[str, int] = {}
    command_failures: List[Dict[str, Any]] = []
    tera_commands: List[str] = []
    move_commands: List[str] = []
    determinism_ok = True
    latencies_ms: List[float] = []

    with torch.no_grad():
        for state_index in sampled:
            rows = dataset.candidate_rows_by_state[int(state_index)]
            af = dataset.action_features[rows].astype(np.float32)
            kinds = dataset.candidate_kinds[rows]
            action_indices = dataset.candidate_action_indices[rows]
            state = torch.from_numpy(
                dataset.state_features[int(state_index)].astype(np.float32)
            ).unsqueeze(0).to(device)
            actions = torch.from_numpy(af).to(device)

            start = time.perf_counter()
            embedding = model.encode_states(state).expand(len(rows), -1)
            scores = model.rank_from_embeddings(embedding, actions).cpu().numpy()
            latencies_ms.append((time.perf_counter() - start) * 1000.0)

            # Determinism: re-score must be identical.
            scores2 = model.rank_from_embeddings(
                model.encode_states(state).expand(len(rows), -1), actions
            ).cpu().numpy()
            if not np.allclose(scores, scores2, atol=1e-6):
                determinism_ok = False

            picked = int(np.argmax(scores))
            kind = str(kinds[picked])
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
            command = candidate_to_showdown_command(kind, int(action_indices[picked]))
            if kind not in VALID_CANDIDATE_KINDS or not command:
                command_failures.append({"state_index": int(state_index), "kind": kind})
            elif kind == "move_tera":
                tera_commands.append(command)
            elif kind == "move":
                move_commands.append(command)

    # 2) Parity vs the offline evaluator over the full split (same model + features).
    offline = offline_evaluate(config_path, checkpoint_path, split=split, example_count=0)

    # Audit-recomputed top-1 over the full split for a like-for-like comparison.
    audit_top1_hits = 0
    total = 0
    with torch.no_grad():
        for state_index in groups:
            rows = dataset.candidate_rows_by_state[int(state_index)]
            labels = dataset.action_rank_labels[rows]
            chosen = int(np.flatnonzero(labels == 1)[0])
            state = torch.from_numpy(
                dataset.state_features[int(state_index)].astype(np.float32)
            ).unsqueeze(0).to(device)
            actions = torch.from_numpy(dataset.action_features[rows].astype(np.float32)).to(device)
            embedding = model.encode_states(state).expand(len(rows), -1)
            scores = model.rank_from_embeddings(embedding, actions).cpu().numpy()
            audit_top1_hits += int(int(np.argmax(scores)) == chosen)
            total += 1
    audit_top1 = audit_top1_hits / max(1, total)
    parity_top1_match = abs(audit_top1 - offline["model"]["top1"]) < 1e-9

    tera_distinct = (not tera_commands) or all(
        cmd not in set(move_commands) for cmd in tera_commands
    )
    live_scan = _scan_live_paths()

    blockers: List[str] = []
    if not live_scan["any_live_file_references_vnext"]:
        blockers.append(
            "Live path has no vNext support: it loads ActionRankerMLP with v2 state / v3 "
            "action features and pad/truncates; it cannot load the VNextDiagnosticMLP checkpoint."
        )
    blockers.append(
        "Live candidate generation (legal_action_candidates) emits only move/switch and "
        "no move_tera candidates, so Tera actions cannot be scored or selected live."
    )
    blockers.append(
        "Live path does not build live-private-belief-v7 state or legal-action-v5 action "
        "features (no resolve_action_impact per candidate), so live features would not match "
        "training schema/order."
    )
    blockers.append(
        "No candidate->Showdown choice serializer exists for vNext candidates (move / "
        "move terastallize / switch) wired to model selection."
    )

    summary = {
        "checkpoint_path": str(checkpoint_path),
        "config_path": str(config_path),
        "split": split,
        "schema_validation": schema_validation,
        "model_parameter_count": parameter_count,
        "device": device.type,
        "sampled_groups": int(len(sampled)),
        "selected_candidate_kind_counts": kind_counts,
        "command_serialization_failures": command_failures,
        "all_selected_candidates_serializable": not command_failures,
        "tera_command_distinct_from_move": tera_distinct,
        "tera_commands_seen": len(tera_commands),
        "scoring_determinism_ok": determinism_ok,
        "model_scoring_latency_ms": {
            "groups": len(latencies_ms),
            "mean": float(np.mean(latencies_ms)) if latencies_ms else None,
            "p95": float(np.percentile(latencies_ms, 95)) if latencies_ms else None,
            "max": float(np.max(latencies_ms)) if latencies_ms else None,
            "note": "Model scoring only; excludes live feature generation (state v7 + "
            "per-candidate resolve_action_impact), which dominates real live latency.",
        },
        "offline_scorer_parity": {
            "offline_evaluator_top1": offline["model"]["top1"],
            "audit_recomputed_top1": audit_top1,
            "top1_match": parity_top1_match,
            "groups": total,
        },
        "live_path_scan": live_scan,
        "blockers_before_private_match": blockers,
        "private_matches_run": False,
        "live_defaults_changed": False,
    }
    return summary


def main(argv: Sequence[str] = None) -> Dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--split", default="validation")
    parser.add_argument("--sample-groups", type=int, default=200)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    summary = audit_readiness(
        Path(args.config),
        Path(args.checkpoint),
        split=args.split,
        sample_groups=args.sample_groups,
    )
    text = json.dumps(summary, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return summary


if __name__ == "__main__":
    main()
