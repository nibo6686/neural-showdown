from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .live_opponent_beliefs import build_opponent_beliefs
from .live_private_features import build_live_private_feature_vector, public_feature_vector_from_trajectory, trajectory_prefix
from .live_private_state import extract_private_side_state
from .tactical_state import build_tactical_state
from .value_features import select_trace_step, view_request_from_step


def _trace_step_turn(step: Dict[str, Any]) -> int:
    try:
        return int(step.get("turn", 0) or 0)
    except (TypeError, ValueError):
        return 0


def build_approx_battle_state(
    trace: Dict[str, Any],
    *,
    player_side: str,
    legal_actions: List[Dict[str, Any]],
    step_index: int = 0,
    sets_path: Optional[str] = None,
) -> Dict[str, Any]:
    selected_step, selected_index, found = select_trace_step(trace, step_index)
    prefix_turn = _trace_step_turn(selected_step)
    prefix = trajectory_prefix(trace, prefix_turn) if prefix_turn > 0 else dict(trace)
    protocol_log = prefix.get("protocol_log") if isinstance(prefix.get("protocol_log"), list) else []

    view, request = view_request_from_step(prefix, selected_step)
    if not isinstance(request, dict):
        request = None
    if not isinstance(view, dict):
        view = {}

    private_state = extract_private_side_state(
        request_payload=request,
        legal_actions=list(legal_actions),
        player_hint=player_side,
        active_species_hint=trace.get("active_species") if isinstance(trace, dict) else None,
        sets_path=sets_path,
    )
    inferred_player = private_state.get("player_side") if private_state.get("player_side") in ("p1", "p2") else player_side
    tactical_state = build_tactical_state(protocol_log, perspective_side=inferred_player)
    opponent_belief = build_opponent_beliefs(
        protocol_log=list(protocol_log),
        trajectory=prefix,
        player_side=inferred_player,
        sets_path=sets_path,
    )

    public_features, public_debug = public_feature_vector_from_trajectory(prefix, perspective_side=inferred_player)
    live_features, live_debug = build_live_private_feature_vector(
        public_features=public_features,
        private_state=private_state,
        opponent_belief=opponent_belief,
        trajectory=prefix,
        player_side=inferred_player,
        tactical_state=tactical_state,
    )

    if isinstance(selected_step.get("self_types"), list):
        view.setdefault("self_team", [{}])
        if view.get("self_team"):
            view["self_team"][0]["types"] = [str(value) for value in selected_step.get("self_types") if str(value)]
    if isinstance(selected_step.get("opponent_types"), list):
        view.setdefault("opponent_team", [{}])
        if view.get("opponent_team"):
            view["opponent_team"][0]["types"] = [str(value) for value in selected_step.get("opponent_types") if str(value)]

    warnings: List[str] = []
    if not found:
        warnings.append("step_index_clamped")
    if private_state.get("inferred_from_randbats"):
        warnings.append("opponent_beliefs_inferred_from_randbats")
    if not protocol_log:
        warnings.append("missing_protocol_prefix")

    return {
        "approximate_state": True,
        "format": str(trace.get("format") or "gen9randombattle"),
        "player_side": inferred_player,
        "step_index": int(selected_index),
        "turn": _trace_step_turn(selected_step),
        "trace_step": selected_step,
        "view": view,
        "request": request,
        "private_state": private_state,
        "opponent_belief": opponent_belief,
        "public_features": public_features,
        "public_feature_debug": public_debug,
        "live_features": live_features,
        "live_feature_debug": live_debug,
        "tactical_state": tactical_state,
        "protocol_prefix": list(protocol_log),
        "legal_actions": list(legal_actions),
        "warnings": warnings,
        "source": "approximate_decision_rollout",
    }
