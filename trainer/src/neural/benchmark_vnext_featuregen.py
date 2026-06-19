import argparse
import hashlib
import json
import os
import subprocess
import time
import tracemalloc
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .action_features import (
    ACTION_FEATURE_DIM,
    ACTION_FEATURE_DIM_V5,
    ACTION_FEATURE_NAMES_V5,
    ACTION_FEATURE_VERSION,
    ACTION_FEATURE_VERSION_V5,
    build_action_feature_vector_v5,
)
from .build_action_rank_dataset import (
    _action_label_from_event,
    _chosen_index,
    _legal_actions_from_private_state,
)
from .build_live_private_value_dataset import (
    _reconstructed_completed_private_teams,
    _reconstructed_private_state_for_side,
    _trajectory_prefix_for_training,
)
from .live_opponent_beliefs import build_opponent_beliefs
from .live_private_features import (
    FEATURE_DIM,
    FEATURE_DIM_V7,
    FEATURE_NAMES_V7,
    FEATURE_VERSION,
    FEATURE_VERSION_V7,
    build_live_private_feature_vector,
    public_feature_vector_from_trajectory,
)
from .logging_helper import print_line_safe
from .parse_replay_logs import parse_protocol_log
from .resolved_action_impact import resolve_action_impact
from .tactical_state import build_tactical_state


BENCHMARK_VERSION = "vnext-featuregen-tiny-v1"
DEFAULT_MANIFEST = Path("artifacts/training_plan/manifests/diagnostic_300_manifest.json")
DEFAULT_OUTPUT_DIR = Path("artifacts/training_plan/benchmarks/vnext_featuregen_tiny_10")
DEFAULT_SEED = 20260619
DEFAULT_BATTLES = 10
SPLIT_QUOTAS_10 = {"train": 4, "validation": 3, "test": 3}
RARE_MECHANICS = {
    "transform",
    "illusion",
    "type_change",
    "tailwind",
    "recharge_lock_constraints",
    "encore",
    "disable",
}


def _stable_key(seed: int, replay_id: str, namespace: str) -> str:
    return hashlib.sha256(f"{seed}:{namespace}:{replay_id}".encode("utf-8")).hexdigest()


def _mechanic_score(entry: Dict[str, Any]) -> int:
    mechanics = entry.get("mechanics") if isinstance(entry.get("mechanics"), dict) else {}
    total = sum(bool(value) for value in mechanics.values())
    rare = sum(bool(mechanics.get(name)) for name in RARE_MECHANICS)
    return total + 3 * rare


def select_manifest_subset(
    manifest: Dict[str, Any],
    *,
    size: int = DEFAULT_BATTLES,
    seed: int = DEFAULT_SEED,
) -> List[Dict[str, Any]]:
    entries = manifest.get("entries") if isinstance(manifest.get("entries"), list) else []
    if size <= 0 or size > len(entries):
        raise ValueError(f"Subset size must be between 1 and {len(entries)}, got {size}.")
    if size == 10:
        quotas = dict(SPLIT_QUOTAS_10)
    else:
        available_splits = [name for name in ("train", "validation", "test") if any(row.get("split") == name for row in entries)]
        quotas = {name: 1 for name in available_splits[: min(size, len(available_splits))]}
        remaining = size - sum(quotas.values())
        for index in range(remaining):
            quotas[available_splits[index % len(available_splits)]] += 1

    selected: List[Dict[str, Any]] = []
    for split, count in quotas.items():
        candidates = [row for row in entries if row.get("split") == split]
        candidates.sort(
            key=lambda row: (
                -_mechanic_score(row),
                abs(int(row.get("turn_count", 0) or 0) - 25),
                _stable_key(seed, str(row.get("replay_id")), split),
            )
        )
        if len(candidates) < count:
            raise ValueError(f"Split {split!r} has only {len(candidates)} entries; need {count}.")
        selected.extend(candidates[:count])
    if len(selected) != size:
        raise ValueError(f"Subset selection produced {len(selected)} entries, expected {size}.")
    ids = [str(row.get("replay_id")) for row in selected]
    if len(ids) != len(set(ids)):
        raise ValueError("Subset selection produced duplicate replay IDs.")
    return sorted(selected, key=lambda row: (str(row.get("split")), str(row.get("replay_id"))))


def _git_commit() -> Optional[str]:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def _names_fingerprint(names: Sequence[str]) -> str:
    payload = json.dumps(list(names), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _damage_client() -> Any:
    command_json = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")
    cwd = os.environ.get("NEURAL_SIM_CORE_CWD")
    if not command_json or not cwd:
        return None
    from .env_client import SimCoreClient

    client = SimCoreClient(json.loads(command_json), cwd)
    client.ping()
    return client


def _opponent_view(tactical_state: Dict[str, Any]) -> Dict[str, Any]:
    opponent = tactical_state.get("opponent") if isinstance(tactical_state.get("opponent"), dict) else {}
    species = opponent.get("active_current_species") or opponent.get("active_species")
    if not species:
        return {"opponent_team": []}
    mon = {
        "species": species,
        "hp_fraction": opponent.get("active_hp_fraction", 1.0),
        "types": list(opponent.get("active_current_types") or opponent.get("active_base_types") or []),
        "status": opponent.get("active_status"),
        "item": opponent.get("active_item"),
        "ability": opponent.get("active_current_ability"),
        "boosts": dict(opponent.get("boosts") or {}),
        "tera_type": opponent.get("active_tera_type"),
        "terastallized": bool(opponent.get("active_terastallized")),
    }
    return {"opponent_team": [mon]}


def _decision_features(
    *,
    trajectory: Dict[str, Any],
    side: str,
    turn_number: int,
    event: Dict[str, Any],
    completed_teams: Dict[str, Dict[str, Dict[str, Any]]],
    sets_path: Optional[str],
    damage_client: Any,
) -> Optional[Dict[str, Any]]:
    chosen_label = _action_label_from_event(event)
    if not chosen_label:
        return None
    context_turn = max(0, int(turn_number) - 1)
    prefix = _trajectory_prefix_for_training(trajectory, context_turn)
    public_features, _ = public_feature_vector_from_trajectory(prefix, perspective_side=side)
    private_state = _reconstructed_private_state_for_side(
        trajectory,
        side=side,
        through_turn=context_turn,
        completed_teams=completed_teams,
    )
    opponent_belief = build_opponent_beliefs(
        protocol_log=prefix.get("protocol_log", []),
        trajectory=prefix,
        player_side=side,
        sets_path=sets_path,
    )
    tactical_state = build_tactical_state(prefix.get("protocol_log", []), perspective_side=side)
    private_state["opponent_belief"] = opponent_belief
    private_state["tactical_state"] = tactical_state
    state_features, state_debug = build_live_private_feature_vector(
        public_features=public_features,
        private_state=private_state,
        opponent_belief=opponent_belief,
        trajectory=prefix,
        player_side=side,
        tactical_state=tactical_state,
        feature_version=FEATURE_VERSION_V7,
    )
    actions = _legal_actions_from_private_state(private_state, chosen_label)
    chosen_ordinal = _chosen_index(actions, chosen_label)
    if chosen_ordinal is None or not actions:
        return None

    approx_state = {
        "private_state": private_state,
        "opponent_belief": opponent_belief,
        "tactical_state": tactical_state,
        "view": _opponent_view(tactical_state),
    }
    action_features = []
    impact_methods: Counter[str] = Counter()
    for action in actions:
        impact = resolve_action_impact(action, approx_state, client=damage_client)
        impact_methods[str(impact.get("method") or "unavailable")] += 1
        action_features.append(
            build_action_feature_vector_v5(
                action,
                private_state,
                tactical_state=tactical_state,
                impact=impact,
            )
        )
    return {
        "state_features": state_features,
        "state_debug": state_debug,
        "actions": actions,
        "action_features": action_features,
        "observed": [1 if index == chosen_ordinal else 0 for index in range(len(actions))],
        "impact_methods": impact_methods,
        "turn": int(turn_number),
        "side": side,
    }


def benchmark_metadata(
    *,
    manifest: Dict[str, Any],
    selected_entries: Sequence[Dict[str, Any]],
    seed: int,
) -> Dict[str, Any]:
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "state_feature_version": FEATURE_VERSION_V7,
        "state_feature_dim": FEATURE_DIM_V7,
        "state_feature_names_sha256": _names_fingerprint(FEATURE_NAMES_V7),
        "action_feature_version": ACTION_FEATURE_VERSION_V5,
        "action_feature_dim": ACTION_FEATURE_DIM_V5,
        "action_feature_names_sha256": _names_fingerprint(ACTION_FEATURE_NAMES_V5),
        "live_default_state_feature_version": FEATURE_VERSION,
        "live_default_state_feature_dim": FEATURE_DIM,
        "live_default_action_feature_version": ACTION_FEATURE_VERSION,
        "live_default_action_feature_dim": ACTION_FEATURE_DIM,
        "dtype_on_disk": "float16",
        "generation_dtype": "float32",
        "storage_layout": "one state row per decision; separate candidate action rows linked by candidate_state_indices",
        "state_vectors_duplicated_per_candidate": False,
        "selection_seed": seed,
        "manifest_version": manifest.get("manifest_version"),
        "manifest_seed": manifest.get("seed"),
        "manifest_catalog_checksum": manifest.get("catalog_checksum"),
        "profile_versions": sorted({
            str(row.get("profile_version"))
            for row in selected_entries
            if row.get("profile_version")
        }),
        "selected_replay_ids": [str(row.get("replay_id")) for row in selected_entries],
        "selected_splits": {str(row.get("replay_id")): str(row.get("split")) for row in selected_entries},
        "source_commit": _git_commit(),
        "information_boundary": (
            "Public replay protocol prefixes and randbats opponent beliefs are used. "
            "Own-side private state follows the existing replay-training assumption that "
            "later public reveals may complete the own roster/moves; no true hidden opponent "
            "team or original private request payload is read."
        ),
    }


def validate_benchmark_arrays(arrays: Dict[str, np.ndarray], metadata: Dict[str, Any]) -> Dict[str, Any]:
    states = arrays["state_features"]
    actions = arrays["action_features"]
    state_ids = [str(value) for value in arrays["state_replay_ids"].tolist()]
    state_splits = [str(value) for value in arrays["state_splits"].tolist()]
    candidate_state_indices = arrays["candidate_state_indices"]
    replay_split_pairs = set(zip(state_ids, state_splits))
    replay_to_splits: Dict[str, set] = {}
    for replay_id, split in replay_split_pairs:
        replay_to_splits.setdefault(replay_id, set()).add(split)
    manifest_ids = set(str(value) for value in metadata["selected_replay_ids"])
    checks = {
        "state_dim_3208": states.ndim == 2 and states.shape[1] == FEATURE_DIM_V7,
        "action_dim_318": actions.ndim == 2 and actions.shape[1] == ACTION_FEATURE_DIM_V5,
        "state_dtype_float16": states.dtype == np.float16,
        "action_dtype_float16": actions.dtype == np.float16,
        "candidate_state_indices_valid": (
            candidate_state_indices.ndim == 1
            and candidate_state_indices.shape[0] == actions.shape[0]
            and (candidate_state_indices.size == 0 or (
                int(candidate_state_indices.min()) >= 0
                and int(candidate_state_indices.max()) < states.shape[0]
            ))
        ),
        "no_battle_crosses_splits": all(len(splits) == 1 for splits in replay_to_splits.values()),
        "all_examples_trace_to_manifest": set(state_ids).issubset(manifest_ids),
        "metadata_records_v7_v5": (
            metadata.get("state_feature_version") == FEATURE_VERSION_V7
            and metadata.get("action_feature_version") == ACTION_FEATURE_VERSION_V5
        ),
        "metadata_records_name_fingerprints": (
            metadata.get("state_feature_names_sha256") == _names_fingerprint(FEATURE_NAMES_V7)
            and metadata.get("action_feature_names_sha256") == _names_fingerprint(ACTION_FEATURE_NAMES_V5)
        ),
        "metadata_records_manifest_profile_source": (
            bool(metadata.get("manifest_version"))
            and bool(metadata.get("manifest_catalog_checksum"))
            and bool(metadata.get("profile_versions"))
            and bool(metadata.get("source_commit"))
        ),
        "live_defaults_unchanged": (
            metadata.get("live_default_state_feature_version") == "live-private-belief-v2"
            and metadata.get("live_default_action_feature_version") == "legal-action-v3"
        ),
        "state_not_duplicated_per_candidate": not metadata.get("state_vectors_duplicated_per_candidate"),
    }
    return {"passed": all(checks.values()), "checks": checks}


def run_benchmark(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    battles: int = DEFAULT_BATTLES,
    seed: int = DEFAULT_SEED,
    sets_path: Optional[str] = None,
) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected_entries = select_manifest_subset(manifest, size=battles, seed=seed)
    metadata = benchmark_metadata(manifest=manifest, selected_entries=selected_entries, seed=seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    subset_path = output_dir / "subset_manifest.json"
    dataset_path = output_dir / "vnext_features_tiny_10.npz"
    metadata_path = output_dir / "feature_metadata.json"
    report_json_path = output_dir / "benchmark_report.json"
    report_md_path = output_dir.parent / "vnext_featuregen_tiny_10_report.md"
    subset_path.write_text(
        json.dumps({"metadata": metadata, "entries": selected_entries}, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    state_rows: List[np.ndarray] = []
    state_replay_ids: List[str] = []
    state_splits: List[str] = []
    state_turns: List[int] = []
    state_sides: List[str] = []
    action_rows: List[np.ndarray] = []
    candidate_state_indices: List[int] = []
    candidate_action_indices: List[int] = []
    candidate_kinds: List[str] = []
    observed_actions: List[int] = []
    failures: List[Dict[str, str]] = []
    battle_counts: Counter[str] = Counter()
    impact_methods: Counter[str] = Counter()

    client = None
    started = time.perf_counter()
    tracemalloc.start()
    try:
        client = _damage_client()
        if client is None:
            raise RuntimeError(
                "Benchmark requires NEURAL_SIM_CORE_COMMAND_JSON/NEURAL_SIM_CORE_CWD; "
                "run through scripts/run_windows.ps1."
            )
        for ordinal, entry in enumerate(selected_entries, start=1):
            replay_id = str(entry["replay_id"])
            path = Path(str(entry["path"]))
            before_states = len(state_rows)
            try:
                trajectory = parse_protocol_log(
                    path.read_text(encoding="utf-8", errors="replace").splitlines(),
                    replay_id=replay_id,
                    format_name="gen9randombattle",
                    source_path=str(path),
                )
                completed_teams = _reconstructed_completed_private_teams(trajectory)
                turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
                for turn_record in sorted(turns, key=lambda item: int(item.get("turn", 0) or 0)):
                    turn_number = int(turn_record.get("turn", 0) or 0)
                    events = turn_record.get("events") if isinstance(turn_record.get("events"), list) else []
                    for event in events:
                        if not isinstance(event, dict) or event.get("type") not in ("move", "switch"):
                            continue
                        side = event.get("side")
                        if side not in ("p1", "p2"):
                            continue
                        decision = _decision_features(
                            trajectory=trajectory,
                            side=side,
                            turn_number=turn_number,
                            event=event,
                            completed_teams=completed_teams,
                            sets_path=sets_path,
                            damage_client=client,
                        )
                        if not decision:
                            battle_counts["skipped_unmatched_decision"] += 1
                            continue
                        state_index = len(state_rows)
                        state_rows.append(decision["state_features"])
                        state_replay_ids.append(replay_id)
                        state_splits.append(str(entry["split"]))
                        state_turns.append(decision["turn"])
                        state_sides.append(decision["side"])
                        impact_methods.update(decision["impact_methods"])
                        for action, features, observed in zip(
                            decision["actions"],
                            decision["action_features"],
                            decision["observed"],
                        ):
                            action_rows.append(features)
                            candidate_state_indices.append(state_index)
                            candidate_action_indices.append(int(action.get("index", 0) or 0))
                            candidate_kinds.append(str(action.get("kind") or ""))
                            observed_actions.append(int(observed))
                if len(state_rows) == before_states:
                    failures.append({"replay_id": replay_id, "reason": "no valid decision states"})
                else:
                    battle_counts["valid"] += 1
            except Exception as exc:
                failures.append({"replay_id": replay_id, "reason": f"{type(exc).__name__}: {exc}"})
            print_line_safe(
                f"benchmark-vnext-featuregen | battle={ordinal}/{len(selected_entries)} "
                f"states={len(state_rows)} candidates={len(action_rows)} failures={len(failures)}"
            )
    finally:
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        if client is not None:
            client.close()

    arrays = {
        "state_features": np.asarray(state_rows, dtype=np.float16),
        "state_replay_ids": np.asarray(state_replay_ids),
        "state_splits": np.asarray(state_splits),
        "state_turns": np.asarray(state_turns, dtype=np.int16),
        "state_sides": np.asarray(state_sides),
        "action_features": np.asarray(action_rows, dtype=np.float16),
        "candidate_state_indices": np.asarray(candidate_state_indices, dtype=np.int32),
        "candidate_action_indices": np.asarray(candidate_action_indices, dtype=np.int16),
        "candidate_kinds": np.asarray(candidate_kinds),
        "observed_actions": np.asarray(observed_actions, dtype=np.int8),
        "state_feature_version": np.asarray(FEATURE_VERSION_V7),
        "state_feature_names": np.asarray(FEATURE_NAMES_V7),
        "action_feature_version": np.asarray(ACTION_FEATURE_VERSION_V5),
        "action_feature_names": np.asarray(ACTION_FEATURE_NAMES_V5),
        "manifest_catalog_checksum": np.asarray(str(manifest.get("catalog_checksum") or "")),
        "source_commit": np.asarray(str(metadata.get("source_commit") or "")),
    }
    if not state_rows or not action_rows:
        raise ValueError("Benchmark produced no feature rows.")
    validation = validate_benchmark_arrays(arrays, metadata)
    if not validation["passed"]:
        raise ValueError(f"Benchmark validation failed: {validation['checks']}")
    np.savez_compressed(dataset_path, **arrays)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    elapsed = time.perf_counter() - started
    dataset_bytes = dataset_path.stat().st_size
    output_bytes = sum(path.stat().st_size for path in output_dir.glob("*") if path.is_file())
    splits = Counter(state_splits)
    report = {
        **metadata,
        "command": (
            ".\\scripts\\run_windows.ps1 -Action benchmark-vnext-featuregen "
            "-SimCoreMode native"
        ),
        "output_dir": str(output_dir),
        "files_produced": [
            str(subset_path),
            str(dataset_path),
            str(metadata_path),
            str(report_json_path),
            str(report_md_path),
        ],
        "battles_requested": battles,
        "battles_processed": len(selected_entries),
        "valid_battles": int(battle_counts["valid"]),
        "failed_battles": len(failures),
        "failures": failures,
        "decision_states": len(state_rows),
        "legal_action_candidates": len(action_rows),
        "average_legal_actions_per_state": len(action_rows) / max(1, len(state_rows)),
        "split_state_counts": dict(splits),
        "impact_method_counts": dict(impact_methods),
        "runtime_total_sec": elapsed,
        "runtime_per_battle_sec": elapsed / max(1, len(selected_entries)),
        "runtime_per_decision_state_sec": elapsed / max(1, len(state_rows)),
        "runtime_per_action_candidate_sec": elapsed / max(1, len(action_rows)),
        "dataset_size_bytes": dataset_bytes,
        "dataset_size_mb": dataset_bytes / (1024 * 1024),
        "total_output_size_bytes": output_bytes,
        "total_output_size_mb": output_bytes / (1024 * 1024),
        "dense_uncompressed_payload_bytes": int(arrays["state_features"].nbytes + arrays["action_features"].nbytes),
        "peak_python_tracemalloc_bytes": int(peak_memory),
        "peak_python_tracemalloc_mb": peak_memory / (1024 * 1024),
        "validation": validation,
        "warnings": [
            "Peak memory is Python tracemalloc heap only; it excludes sim-core and NumPy native allocations.",
            "Own-side reconstructed state follows the existing replay-training future-public-reveal assumption.",
            "This is a 10-battle feasibility benchmark, not the full diagnostic_300 materialization.",
        ],
        "schema_bug_found": False,
        "ready_for_full_diagnostic_300": len(failures) == 0 and validation["passed"],
    }
    report_json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    report_md_path.write_text(_report_markdown(report), encoding="utf-8")
    print_line_safe(
        f"benchmark-vnext-featuregen done | battles={len(selected_entries)} "
        f"states={len(state_rows)} candidates={len(action_rows)} runtime={elapsed:.2f}s "
        f"dataset_mb={report['dataset_size_mb']:.2f}"
    )
    return report


def _report_markdown(report: Dict[str, Any]) -> str:
    checks = report["validation"]["checks"]
    lines = [
        "# vNext Feature Generation Tiny-10 Benchmark",
        "",
        f"- Command: `{report['command']}`",
        f"- Battles: {report['valid_battles']} valid / {report['failed_battles']} failed",
        f"- Decision states: {report['decision_states']:,}",
        f"- Legal action candidates: {report['legal_action_candidates']:,}",
        f"- Average legal actions/state: {report['average_legal_actions_per_state']:.2f}",
        f"- Runtime: {report['runtime_total_sec']:.2f}s total; "
        f"{report['runtime_per_battle_sec']:.2f}s/battle; "
        f"{report['runtime_per_decision_state_sec'] * 1000:.2f}ms/state; "
        f"{report['runtime_per_action_candidate_sec'] * 1000:.2f}ms/candidate",
        f"- Dataset size: {report['dataset_size_mb']:.2f} MiB compressed",
        f"- Dense state/action payload: {report['dense_uncompressed_payload_bytes'] / (1024 * 1024):.2f} MiB",
        f"- Peak Python tracemalloc heap: {report['peak_python_tracemalloc_mb']:.2f} MiB",
        f"- State: `{report['state_feature_version']}`, {report['state_feature_dim']}D",
        f"- Action: `{report['action_feature_version']}`, {report['action_feature_dim']}D",
        f"- Dtype/layout: {report['dtype_on_disk']}; {report['storage_layout']}",
        f"- State duplicated per candidate: {report['state_vectors_duplicated_per_candidate']}",
        f"- Split state counts: {report['split_state_counts']}",
        f"- Impact methods: {report['impact_method_counts']}",
        "",
        "## Validation",
        "",
    ]
    for name, passed in checks.items():
        lines.append(f"- [{'x' if passed else ' '}] `{name}`")
    lines.extend([
        "",
        "## Files Produced",
        "",
    ])
    for path in report["files_produced"]:
        lines.append(f"- `{path}`")
    lines.extend([
        "",
        "## Warnings and Decision",
        "",
    ])
    lines.extend(f"- {warning}" for warning in report["warnings"])
    lines.extend([
        "",
        f"- Schema bug found: **{'yes' if report['schema_bug_found'] else 'no'}**",
        f"- Ready for full `diagnostic_300` feature materialization: "
        f"**{'yes' if report['ready_for_full_diagnostic_300'] else 'no'}**",
        "- Training gate: **closed**; labels, full materialization, training command, "
        "and materialized-feature sanity checks remain outstanding.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark v7/v5 feature generation on a tiny manifest subset.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--battles", type=int, default=DEFAULT_BATTLES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--sets-path", default=None)
    args = parser.parse_args()
    run_benchmark(
        manifest_path=Path(args.manifest),
        output_dir=Path(args.output_dir),
        battles=args.battles,
        seed=args.seed,
        sets_path=args.sets_path,
    )


if __name__ == "__main__":
    main()
