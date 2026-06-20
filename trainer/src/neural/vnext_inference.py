"""Opt-in vNext (v7/v5) action-rank inference harness.

Isolated, fail-closed path that loads the `VNextDiagnosticMLP` rank head with
strict schema/fingerprint validation, scores precomputed legal-action candidates,
masks unavailable candidates, and serializes the selected candidate to a Showdown
choice string. It does NOT generate features, run battles, train, or change any
live default. It is never imported by the default v2/v3 live path; callers opt in
explicitly (e.g. via `is_enabled()` / `NEURAL_VNEXT_INFERENCE=1`).

Feature generation (v7 state + v5 candidate features) is deliberately left to the
caller: this harness consumes already-built feature vectors and refuses any vector
whose dimension does not exactly match the trained schema (no pad/truncate).
"""

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import torch

from .train_vnext_diagnostic import (
    EXPECTED_ACTION_DIM,
    EXPECTED_STATE_DIM,
    build_diagnostic_model,
    load_and_validate_diagnostic_config,
    validate_vnext_checkpoint_metadata,
)

VALID_CANDIDATE_KINDS = ("move", "move_tera", "switch")
SAFE_FALLBACK_CHOICE = "default"


def is_enabled() -> bool:
    """Opt-in flag. Default off; the live bot path never depends on this."""
    return os.environ.get("NEURAL_VNEXT_INFERENCE", "").strip() in {"1", "true", "True", "yes"}


def serialize_candidate_command(candidate: Dict[str, Any]) -> Optional[str]:
    """Map a candidate to the exact Showdown choice string, or None on failure.

    Tera moves are a distinct command from the plain move. Slots must be valid
    (moves 1-4, switches 1-6); anything else returns None (fail closed).
    """
    kind = str(candidate.get("kind") or "")
    if kind in ("move", "move_tera"):
        slot = candidate.get("move_slot")
        if not isinstance(slot, int) or isinstance(slot, bool) or not 1 <= slot <= 4:
            return None
        command = f"move {slot}"
        if kind == "move_tera" or bool(candidate.get("is_tera")):
            command = f"{command} terastallize"
        return command
    if kind == "switch":
        slot = candidate.get("switch_slot")
        if not isinstance(slot, int) or isinstance(slot, bool) or not 1 <= slot <= 6:
            return None
        return f"switch {slot}"
    return None


class VNextActionRanker:
    """Strictly-validated vNext rank-head scorer over precomputed candidates."""

    def __init__(
        self,
        model: torch.nn.Module,
        *,
        device: torch.device,
        state_dim: int,
        action_dim: int,
        metadata: Dict[str, Any],
    ) -> None:
        self.model = model
        self.device = device
        self.state_dim = int(state_dim)
        self.action_dim = int(action_dim)
        self.metadata = metadata

    @classmethod
    def load(
        cls,
        config_path: Path,
        checkpoint_path: Path,
        *,
        allow_unfingerprinted: bool = False,
        device: Optional[torch.device] = None,
    ) -> "VNextActionRanker":
        config = load_and_validate_diagnostic_config(Path(config_path))
        dataset_cfg = config["dataset"]
        checkpoint_path = Path(checkpoint_path)
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"vNext checkpoint does not exist: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        schema = validate_vnext_checkpoint_metadata(
            checkpoint,
            expected_state_version=str(dataset_cfg["state_feature_version"]),
            expected_action_version=str(dataset_cfg["action_feature_version"]),
            expected_state_dim=int(dataset_cfg["state_feature_dim"]),
            expected_action_dim=int(dataset_cfg["action_feature_dim"]),
            expected_state_feature_names_sha256=dataset_cfg["state_feature_names_sha256"],
            expected_action_feature_names_sha256=dataset_cfg["action_feature_names_sha256"],
            require_fingerprints=not allow_unfingerprinted,
        )
        resolved_device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = build_diagnostic_model(config).to(resolved_device)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        metadata = {
            "config_path": str(Path(config_path)),
            "checkpoint_path": str(checkpoint_path),
            "schema_validation": schema,
            "state_feature_version": str(dataset_cfg["state_feature_version"]),
            "action_feature_version": str(dataset_cfg["action_feature_version"]),
            "parameter_count": int(sum(p.numel() for p in model.parameters())),
        }
        return cls(
            model,
            device=resolved_device,
            state_dim=int(dataset_cfg["state_feature_dim"]),
            action_dim=int(dataset_cfg["action_feature_dim"]),
            metadata=metadata,
        )

    def score(self, state_vector: np.ndarray, candidates: Sequence[Dict[str, Any]]) -> np.ndarray:
        """Score candidates with the rank head. Raises on any dimension mismatch.

        No pad/truncate: a wrong-sized state or action vector is a hard error.
        """
        sv = np.asarray(state_vector, dtype=np.float32)
        if sv.shape != (self.state_dim,):
            raise ValueError(
                f"State vector shape {sv.shape} != ({self.state_dim},); "
                "vNext inference does not pad or truncate."
            )
        if not candidates:
            raise ValueError("score() requires at least one candidate.")
        feats = []
        for candidate in candidates:
            af = np.asarray(candidate.get("action_features"), dtype=np.float32)
            if af.shape != (self.action_dim,):
                raise ValueError(
                    f"Action feature shape {af.shape} != ({self.action_dim},); "
                    "vNext inference does not pad or truncate."
                )
            feats.append(af)
        action_arr = np.stack(feats)
        with torch.no_grad():
            state_tensor = torch.from_numpy(sv).unsqueeze(0).to(self.device)
            embedding = self.model.encode_states(state_tensor).expand(len(feats), -1)
            scores = self.model.rank_from_embeddings(
                embedding, torch.from_numpy(action_arr).to(self.device)
            )
        return scores.detach().cpu().numpy()

    def _fallback(self, reason: str, ranked: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return {
            "ok": False,
            "choice": SAFE_FALLBACK_CHOICE,
            "selected": None,
            "ranked": ranked or [],
            "reason": reason,
        }

    def recommend(
        self, state_vector: np.ndarray, candidates: Sequence[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Fail-closed: return a safe `default` choice on any inconsistency."""
        try:
            if not candidates:
                return self._fallback("no_legal_candidates")
            available = [
                candidate
                for candidate in candidates
                if candidate.get("available", True) and not candidate.get("disabled", False)
            ]
            if not available:
                return self._fallback("all_candidates_unavailable")
            scores = self.score(state_vector, available)
            order = np.argsort(-scores, kind="stable")
            ranked = [
                {
                    "kind": str(available[int(j)].get("kind") or ""),
                    "label": available[int(j)].get("label"),
                    "score": float(scores[int(j)]),
                }
                for j in order
            ]
            top = available[int(order[0])]
            choice = serialize_candidate_command(top)
            if not choice:
                return self._fallback("command_serialization_failed", ranked=ranked)
            return {
                "ok": True,
                "choice": choice,
                "selected": {
                    "kind": str(top.get("kind") or ""),
                    "label": top.get("label"),
                    "move_slot": top.get("move_slot"),
                    "switch_slot": top.get("switch_slot"),
                    "is_tera": bool(top.get("is_tera")) or str(top.get("kind")) == "move_tera",
                    "score": float(scores[int(order[0])]),
                },
                "ranked": ranked,
                "reason": None,
            }
        except Exception as exc:  # noqa: BLE001 - fail closed for any inference error
            return self._fallback(f"{type(exc).__name__}: {exc}")


def safe_load(
    config_path: Path, checkpoint_path: Path, *, allow_unfingerprinted: bool = False
) -> Dict[str, Any]:
    """Load wrapper that fails closed: returns {ok, ranker|None, reason}."""
    try:
        ranker = VNextActionRanker.load(
            config_path, checkpoint_path, allow_unfingerprinted=allow_unfingerprinted
        )
        return {"ok": True, "ranker": ranker, "reason": None}
    except Exception as exc:  # noqa: BLE001 - fail closed on load failure
        return {"ok": False, "ranker": None, "reason": f"{type(exc).__name__}: {exc}"}


def dataset_group_candidates(dataset: Any, state_index: int) -> List[Dict[str, Any]]:
    """Build harness candidates from a diagnostic dataset group (for parity tests)."""
    rows = dataset.candidate_rows_by_state[int(state_index)]
    action_features = dataset.action_features[rows].astype(np.float32)
    kinds = dataset.candidate_kinds[rows]
    return [
        {
            "action_features": action_features[i],
            "kind": str(kinds[i]),
            "available": True,
            "row": int(rows[i]),
        }
        for i in range(len(rows))
    ]


def top1_over_split(ranker: "VNextActionRanker", dataset: Any, split: str) -> float:
    """Harness top-1 over a dataset split (for offline-evaluator parity checks)."""
    groups = dataset.split_group_state_indices[split]
    hits = 0
    total = 0
    for state_index in groups:
        rows = dataset.candidate_rows_by_state[int(state_index)]
        labels = dataset.action_rank_labels[rows]
        chosen = int(np.flatnonzero(labels == 1)[0])
        candidates = dataset_group_candidates(dataset, int(state_index))
        scores = ranker.score(dataset.state_features[int(state_index)].astype(np.float32), candidates)
        hits += int(int(np.argmax(scores)) == chosen)
        total += 1
    return hits / max(1, total)


def measure_latency(
    ranker: "VNextActionRanker", dataset: Any, split: str, *, max_groups: int = 200
) -> Dict[str, Any]:
    groups = dataset.split_group_state_indices[split][: max(1, int(max_groups))]
    latencies_ms: List[float] = []
    for state_index in groups:
        candidates = dataset_group_candidates(dataset, int(state_index))
        state_vector = dataset.state_features[int(state_index)].astype(np.float32)
        start = time.perf_counter()
        ranker.score(state_vector, candidates)
        latencies_ms.append((time.perf_counter() - start) * 1000.0)
    return {
        "groups": len(latencies_ms),
        "mean_ms": float(np.mean(latencies_ms)) if latencies_ms else None,
        "p95_ms": float(np.percentile(latencies_ms, 95)) if latencies_ms else None,
        "max_ms": float(np.max(latencies_ms)) if latencies_ms else None,
    }
