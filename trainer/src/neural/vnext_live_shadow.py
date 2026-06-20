"""Opt-in vNext recommendation *shadow mode* for the live eval workflow.

Given the same real Showdown payload the browser extension already sends to the
local server, this builds `live-private-belief-v7` state and `legal-action-v5`
candidates (including `move_tera` when Tera is legal), scores them with the
`VNextActionRanker` from `vnext_inference`, and returns a dry-run recommendation
+ diagnostics. It never sends a command to Showdown, never modifies browser
state, and is gated by `NEURAL_VNEXT_INFERENCE` (default off). The default
`/evaluate` path does not import or depend on this module.

Fail closed: if state/candidate/feature generation or scoring is inconsistent, it
returns a safe `choice:"default"` with an explicit reason and missing fields
rather than guessing. No pad/truncate is used.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .action_features import ACTION_FEATURE_DIM_V5, build_action_feature_vector_v5
from .build_action_rank_dataset import _legal_actions_from_private_state
from .live_private_features import (
    FEATURE_DIM_V7,
    FEATURE_VERSION_V7,
    build_features_from_live_payload,
)
from .resolved_action_impact import resolve_action_impact
from .tactical_state import build_tactical_state
from . import vnext_inference as vinf

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = _REPO_ROOT / "configs/diagnostic_1000_action_rank_v7_v5.rank_only.windows.json"
DEFAULT_CHECKPOINT = (
    _REPO_ROOT
    / "artifacts/diagnostic_training/diagnostic_1000_action_rank_v7_v5_rank_only/model.best.pt"
)

_ranker_cache: Dict[str, Any] = {}
_damage_client_cache: Dict[str, Any] = {}


def shadow_enabled() -> bool:
    """Opt-in gate; mirrors the harness flag. Default off."""
    return vinf.is_enabled()


def _config_path() -> Path:
    return Path(os.environ.get("NEURAL_VNEXT_CONFIG", str(DEFAULT_CONFIG)))


def _checkpoint_path() -> Path:
    return Path(os.environ.get("NEURAL_VNEXT_CHECKPOINT", str(DEFAULT_CHECKPOINT)))


def _load_ranker() -> Dict[str, Any]:
    key = f"{_config_path()}|{_checkpoint_path()}"
    if key not in _ranker_cache:
        _ranker_cache[key] = vinf.safe_load(_config_path(), _checkpoint_path())
    return _ranker_cache[key]


def _damage_client() -> Any:
    if "client" in _damage_client_cache:
        return _damage_client_cache["client"]
    command_json = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")
    cwd = os.environ.get("NEURAL_SIM_CORE_CWD")
    client = None
    if command_json and cwd:
        try:
            from .env_client import SimCoreClient

            client = SimCoreClient(json.loads(command_json), cwd)
            client.ping()
        except Exception:
            client = None
    _damage_client_cache["client"] = client
    return client


def _norm_species(species: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(species or "").lower())


def _switch_slot_map(private_state: Dict[str, Any]) -> Dict[str, int]:
    """1-based team position per species (Showdown `switch N` counts all slots)."""
    team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
    mapping: Dict[str, int] = {}
    for index, mon in enumerate(team):
        if isinstance(mon, dict):
            species = _norm_species(mon.get("species"))
            if species and species not in mapping:
                mapping[species] = index + 1
    return mapping


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


def _adapt_candidate(action: Dict[str, Any], features: np.ndarray, switch_slots: Dict[str, int]) -> Dict[str, Any]:
    kind = str(action.get("kind") or "")
    candidate: Dict[str, Any] = {
        "action_features": features,
        "kind": kind,
        "label": action.get("label"),
        "available": not bool(action.get("disabled", False)),
    }
    if kind in ("move", "move_tera"):
        slot = action.get("slot")
        candidate["move_slot"] = int(slot) if isinstance(slot, (int, float)) else None
        candidate["is_tera"] = kind == "move_tera"
    elif kind == "switch":
        species = _norm_species(str(action.get("label") or "").split(":", 1)[-1])
        candidate["switch_slot"] = switch_slots.get(species)
    return candidate


def _fail(reason: str, *, missing_fields: Optional[List[str]] = None, **extra: Any) -> Dict[str, Any]:
    result = {
        "ok": False,
        "mode": "vnext_dry_run",
        "choice": vinf.SAFE_FALLBACK_CHOICE,
        "fallback_reason": reason,
        "missing_fields": missing_fields or [],
        "command_sent_to_showdown": False,
        "battle_played_by_model": False,
        "live_defaults_changed": False,
    }
    result.update(extra)
    return result


def build_dry_run(
    *,
    log: Sequence[str],
    room_id: str,
    url: str,
    player: Optional[str],
    request_payload: Optional[Dict[str, Any]],
    legal_actions: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a vNext dry-run recommendation from a real live payload. Fail closed."""
    timings: Dict[str, Optional[float]] = {}
    overall_start = time.perf_counter()

    loaded = _load_ranker()
    if not loaded["ok"]:
        return _fail(f"ranker_load_failed: {loaded['reason']}")
    ranker = loaded["ranker"]

    # State (v7) + reconstruction in one call. No pad/truncate: dim must match.
    try:
        start = time.perf_counter()
        state_features, _debug, private_state, opponent_belief, trajectory = build_features_from_live_payload(
            log=list(log),
            room_id=room_id,
            url=url,
            player=player,
            request_payload=request_payload,
            legal_actions=list(legal_actions),
            feature_version=FEATURE_VERSION_V7,
        )
        timings["state_feature_generation_ms"] = (time.perf_counter() - start) * 1000.0
    except Exception as exc:
        return _fail(f"state_feature_generation_failed: {type(exc).__name__}: {exc}")

    state_vector = np.asarray(state_features, dtype=np.float32)
    if state_vector.shape != (FEATURE_DIM_V7,):
        return _fail(
            "state_feature_dim_mismatch",
            state_feature_dim=int(state_vector.shape[0]) if state_vector.ndim == 1 else None,
        )

    missing: List[str] = []
    if not (private_state.get("active_moves") or private_state.get("force_switch")):
        missing.append("active_moves")
    if not private_state.get("team"):
        missing.append("team")
    player_side = private_state.get("player_side")
    if player_side not in ("p1", "p2"):
        missing.append("player_side")
    if missing:
        return _fail("missing_required_live_fields", missing_fields=missing)

    tactical_state = (
        private_state.get("tactical_state")
        if isinstance(private_state.get("tactical_state"), dict)
        else build_tactical_state(list(log), perspective_side=player_side)
    )

    # Candidates (move / move_tera / switch) from the same generator training used.
    start = time.perf_counter()
    actions = _legal_actions_from_private_state(private_state, "")
    timings["action_candidate_generation_ms"] = (time.perf_counter() - start) * 1000.0
    if not actions:
        return _fail("no_legal_candidates")

    approx_state = {
        "private_state": private_state,
        "opponent_belief": opponent_belief,
        "tactical_state": tactical_state,
        "view": _opponent_view(tactical_state),
    }
    switch_slots = _switch_slot_map(private_state)
    client = _damage_client()

    candidates: List[Dict[str, Any]] = []
    impact_methods: Dict[str, int] = {}
    impact_total_ms = 0.0
    try:
        for action in actions:
            istart = time.perf_counter()
            impact = resolve_action_impact(action, approx_state, client=client)
            impact_total_ms += (time.perf_counter() - istart) * 1000.0
            method = str(impact.get("method") or "unavailable")
            impact_methods[method] = impact_methods.get(method, 0) + 1
            features = np.asarray(
                build_action_feature_vector_v5(action, private_state, tactical_state=tactical_state, impact=impact),
                dtype=np.float32,
            )
            if features.shape != (ACTION_FEATURE_DIM_V5,):
                return _fail(
                    "action_feature_dim_mismatch",
                    action_feature_dim=int(features.shape[0]) if features.ndim == 1 else None,
                )
            candidates.append(_adapt_candidate(action, features, switch_slots))
    except Exception as exc:
        return _fail(f"action_feature_generation_failed: {type(exc).__name__}: {exc}")
    timings["sim_core_impact_resolution_ms"] = impact_total_ms

    kind_counts: Dict[str, int] = {}
    for candidate in candidates:
        kind_counts[candidate["kind"]] = kind_counts.get(candidate["kind"], 0) + 1

    start = time.perf_counter()
    recommendation = ranker.recommend(state_vector, candidates)
    timings["model_scoring_ms"] = (time.perf_counter() - start) * 1000.0

    serialize_start = time.perf_counter()
    schema = ranker.metadata.get("schema_validation", {})
    response = {
        "ok": bool(recommendation["ok"]),
        "mode": "vnext_dry_run",
        "choice": recommendation["choice"],
        "fallback_reason": recommendation.get("reason"),
        "missing_fields": [],
        "selected": recommendation.get("selected"),
        "candidates": recommendation.get("ranked", []),
        "candidate_kind_counts": {
            "move": kind_counts.get("move", 0),
            "move_tera": kind_counts.get("move_tera", 0),
            "switch": kind_counts.get("switch", 0),
        },
        "tera": {
            "can_tera": bool(private_state.get("can_tera") and not private_state.get("tera_used")),
            "tera_candidates_generated": kind_counts.get("move_tera", 0),
        },
        "switch_candidate_count": kind_counts.get("switch", 0),
        "impact_methods": impact_methods,
        "schema": {
            "state_feature_version": FEATURE_VERSION_V7,
            "state_feature_dim": int(state_vector.shape[0]),
            "action_feature_version": ranker.metadata.get("action_feature_version"),
            "action_feature_dim": ACTION_FEATURE_DIM_V5,
            "fingerprint_status": schema.get("status"),
            "fingerprints_complete": schema.get("fingerprints_complete"),
        },
        "player_side": player_side,
        "command_sent_to_showdown": False,
        "battle_played_by_model": False,
        "live_defaults_changed": False,
    }
    timings["response_serialization_ms"] = (time.perf_counter() - serialize_start) * 1000.0
    timings["request_parse_ms"] = None  # parsed by FastAPI upstream of this call
    timings["total_ms"] = (time.perf_counter() - overall_start) * 1000.0
    response["latency_ms"] = timings
    return response
