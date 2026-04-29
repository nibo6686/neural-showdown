import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

from .action_features import ACTION_FEATURE_DIM, build_action_feature_vector, classify_action_category
from .build_replay_value_dataset import FEATURE_NAMES as PUBLIC_FEATURE_NAMES
from .checkpoints import torch_load
from .live_private_features import build_live_private_feature_vector
from .models.action_ranker import ActionRankerMLP
from .sim_branch_evaluator import evaluate_actions as evaluate_branch_actions
from .tactical_state import _species_types, build_tactical_state


PolicyLoader = Callable[[], Tuple[Optional[torch.nn.Module], Optional[Dict[str, Any]]]]
_CANONICAL_ACTION_RANKER_PATH = Path("artifacts/checkpoints/gen9randombattle_action_ranker.pt")
DEFAULT_ACTION_RANKER_V2_PATH = Path("artifacts/checkpoints/gen9randombattle_action_ranker_v2.pt")
DEFAULT_ACTION_VALUE_RANKER_V2_PATH = Path("artifacts/checkpoints/gen9randombattle_action_value_ranker_v2.pt")
DEFAULT_ACTION_RANKER_PATH = _CANONICAL_ACTION_RANKER_PATH
_action_ranker_model: Optional[ActionRankerMLP] = None
_action_ranker_metadata: Optional[Dict[str, Any]] = None


def _env_action_ranker_path() -> Optional[Path]:
    override = os.environ.get("NEURAL_ACTION_RANKER_CHECKPOINT", "").strip()
    return Path(override) if override else None


def reset_action_ranker_cache() -> None:
    global _action_ranker_model, _action_ranker_metadata
    _action_ranker_model = None
    _action_ranker_metadata = None


def load_action_ranker_once(
    *,
    path: Optional[Path] = None,
    device: torch.device,
) -> Tuple[Optional[ActionRankerMLP], Optional[Dict[str, Any]]]:
    global _action_ranker_model, _action_ranker_metadata
    env_path = _env_action_ranker_path()
    if path is not None:
        selected_path = path
    elif env_path is not None:
        selected_path = env_path
    elif DEFAULT_ACTION_VALUE_RANKER_V2_PATH.exists():
        selected_path = DEFAULT_ACTION_VALUE_RANKER_V2_PATH
    elif DEFAULT_ACTION_RANKER_PATH != _CANONICAL_ACTION_RANKER_PATH:
        selected_path = DEFAULT_ACTION_RANKER_PATH
    elif DEFAULT_ACTION_RANKER_V2_PATH.exists():
        selected_path = DEFAULT_ACTION_RANKER_V2_PATH
    else:
        selected_path = DEFAULT_ACTION_RANKER_PATH
    if _action_ranker_model is not None or _action_ranker_metadata is not None:
        return _action_ranker_model, _action_ranker_metadata
    if not selected_path.exists():
        _action_ranker_metadata = {"warning": f"Action ranker checkpoint missing: {selected_path}"}
        return None, _action_ranker_metadata
    checkpoint = torch_load(selected_path, device)
    input_size = int(checkpoint.get("input_size", 0) or 0)
    hidden_sizes = list(checkpoint.get("hidden_sizes", [256, 128]))
    action_dim = int(checkpoint.get("action_dim", ACTION_FEATURE_DIM))
    model = ActionRankerMLP(input_size=input_size, hidden_sizes=hidden_sizes).to(device)
    model.load_state_dict(checkpoint["model_state_dict"], strict=False)
    model.eval()
    _action_ranker_model = model
    _action_ranker_metadata = {
        **checkpoint,
        "path": str(selected_path),
        "input_size": input_size,
        "action_dim": action_dim,
        "model_type": str(checkpoint.get("model_type") or "action-ranker"),
        "response_method": str(checkpoint.get("response_method") or ("action_value_ranker" if checkpoint.get("model_type") == "action-value-ranker" else "action_ranker")),
    }
    return _action_ranker_model, _action_ranker_metadata


def _model_output_value(output: Any) -> float:
    if isinstance(output, tuple):
        value_tensor = output[1]
    elif isinstance(output, dict):
        value_tensor = output.get("value") or output.get("values")
    else:
        value_tensor = output
    return float(value_tensor.squeeze().detach().cpu().item())


def _legal_action_to_dict(action: Any) -> Dict[str, Any]:
    if isinstance(action, dict):
        return dict(action)
    if hasattr(action, "model_dump"):
        return action.model_dump()
    if hasattr(action, "dict"):
        return action.dict()
    return {}


def _request_active_moves(request_payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(request_payload, dict):
        return []
    active = request_payload.get("active")
    active_block = active[0] if isinstance(active, list) and active else active if isinstance(active, dict) else {}
    moves = active_block.get("moves") if isinstance(active_block, dict) else None
    if not isinstance(moves, list):
        return []
    result = []
    for index, move in enumerate(moves):
        if not isinstance(move, dict):
            continue
        name = move.get("move") or move.get("name") or move.get("id") or f"move {index + 1}"
        try:
            pp_empty = move.get("pp") is not None and int(move.get("pp") or 0) <= 0
        except (TypeError, ValueError):
            pp_empty = False
        result.append(
            {
                "index": int(move.get("index", index) if move.get("index") is not None else index),
                "kind": "move",
                "label": f"move: {name}",
                "move": name,
                "slot": int(move.get("slot", index + 1) if move.get("slot") is not None else index + 1),
                "disabled": bool(move.get("disabled", False) or pp_empty),
                "pp": move.get("pp"),
                "maxpp": move.get("maxpp"),
                "source": "request.active.moves",
            }
        )
    return result


def _request_switches(request_payload: Optional[Dict[str, Any]], existing_labels: Sequence[str]) -> List[Dict[str, Any]]:
    if not isinstance(request_payload, dict):
        return []
    side = request_payload.get("side") if isinstance(request_payload.get("side"), dict) else {}
    team = side.get("pokemon") if isinstance(side.get("pokemon"), list) else []
    existing = {label.lower() for label in existing_labels}
    switches = []
    switch_index = 8
    for slot, mon in enumerate(team):
        if not isinstance(mon, dict):
            continue
        if mon.get("active") or mon.get("fainted") or "fnt" in str(mon.get("condition", "")):
            continue
        details = str(mon.get("details") or mon.get("ident") or f"slot {slot + 1}")
        species = details.split(",", 1)[0].split(": ", 1)[-1].strip()
        label = f"switch: {species}"
        if label.lower() in existing:
            continue
        switches.append(
            {
                "index": int(mon.get("index", switch_index) if mon.get("index") is not None else switch_index),
                "kind": "switch",
                "label": label,
                "slot": slot,
                "disabled": False,
                "source": "request.side.pokemon",
            }
        )
        switch_index += 1
    return switches


def _normalize_payload_legal_actions(raw_legal_actions: Sequence[Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for fallback_index, action in enumerate(raw_legal_actions):
        action_dict = _legal_action_to_dict(action)
        kind = str(action_dict.get("kind") or "")
        label = str(action_dict.get("label") or "")
        if not label:
            continue
        display_label = label
        if kind == "move" and not display_label.lower().startswith("move:"):
            display_label = f"move: {display_label}"
        if kind == "switch" and not display_label.lower().startswith("switch:"):
            display_label = f"switch: {display_label}"
        candidates.append(
            {
                "index": int(action_dict.get("index") if action_dict.get("index") is not None else fallback_index),
                "kind": kind,
                "label": display_label,
                "slot": action_dict.get("slot"),
                "disabled": bool(action_dict.get("disabled", False)),
                "source": "payload.legal_actions",
            }
        )
    return candidates


def legal_action_candidates(payload: Any) -> List[Dict[str, Any]]:
    request_payload = getattr(payload, "request", None)
    raw_legal_actions = getattr(payload, "legal_actions", []) or []
    active = request_payload.get("active") if isinstance(request_payload, dict) else None
    active_block = active[0] if isinstance(active, list) and active else active if isinstance(active, dict) else {}
    force_switch_raw = request_payload.get("forceSwitch") if isinstance(request_payload, dict) else None
    force_switch = any(bool(v) for v in force_switch_raw) if isinstance(force_switch_raw, list) else bool(force_switch_raw)
    trapped = bool(active_block.get("trapped") or active_block.get("maybeTrapped"))
    if raw_legal_actions:
        candidates = _normalize_payload_legal_actions(raw_legal_actions)
    else:
        candidates = _request_active_moves(request_payload)
        labels = [str(candidate["label"]) for candidate in candidates]
        if force_switch:
            candidates = _request_switches(request_payload, [])
        elif not trapped:
            candidates.extend(_request_switches(request_payload, labels))

    seen = set()
    deduped = []
    for candidate in candidates:
        key = (candidate.get("index"), candidate.get("kind"), candidate.get("label"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _latest_turn(trajectory: Dict[str, Any]) -> int:
    turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    latest = 0
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        try:
            latest = max(latest, int(turn.get("turn", 0) or 0))
        except (TypeError, ValueError):
            continue
    protocol = trajectory.get("protocol_log") if isinstance(trajectory.get("protocol_log"), list) else []
    for line in protocol:
        parts = str(line).split("|")
        if len(parts) >= 3 and parts[1] == "turn":
            try:
                latest = max(latest, int(parts[2]))
            except ValueError:
                continue
    return latest


def _active_private_mon(private_state: Dict[str, Any]) -> Dict[str, Any]:
    team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
    for mon in team:
        if isinstance(mon, dict) and mon.get("active"):
            return mon
    return team[0] if team and isinstance(team[0], dict) else {}


def _mon_view_from_state(side_state: Dict[str, Any], *, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    fallback = fallback or {}
    species = str(side_state.get("active_species") or fallback.get("species") or fallback.get("name") or "Unknown")
    ident = str(side_state.get("active_ident") or fallback.get("ident") or species)
    hp_fraction = side_state.get("active_hp_fraction")
    if hp_fraction is None:
        hp_fraction = fallback.get("hp_fraction", fallback.get("hp_ratio", 1.0))
    try:
        hp_ratio = max(0.0, min(1.0, float(hp_fraction if hp_fraction is not None else 1.0)))
    except (TypeError, ValueError):
        hp_ratio = 1.0
    level = fallback.get("level")
    if level is None:
        details = str(fallback.get("details") or "")
        if ", L" in details:
            try:
                level = int(details.rsplit(", L", 1)[1].split(",", 1)[0].strip())
            except (TypeError, ValueError):
                level = None
    level = int(level or 80)
    status = side_state.get("active_status")
    if status is None:
        status = fallback.get("status")
    types = fallback.get("types") if isinstance(fallback.get("types"), list) else []
    if not types:
        types = _species_types(species)
    return {
        "slot": int(fallback.get("slot", 0) or 0),
        "ident": ident,
        "name": species,
        "species": species,
        "details": str(fallback.get("details") or f"{species}, L{level}"),
        "active": True,
        "fainted": bool(side_state.get("active_fainted") or fallback.get("fainted") or hp_ratio <= 0.0),
        "hp_text": fallback.get("condition"),
        "hp_ratio": hp_ratio,
        "hp_fraction": hp_ratio,
        "status": status,
        "level": level,
        "item": fallback.get("item"),
        "ability": fallback.get("ability") or fallback.get("base_ability"),
        "base_ability": fallback.get("base_ability"),
        "moves": list(fallback.get("moves") or []),
        "revealed_moves": list(fallback.get("revealed_moves") or []),
        "types": list(types),
        "tera_type": fallback.get("tera_type") or fallback.get("teraType") or side_state.get("active_tera_type"),
        "terastallized": bool(side_state.get("tera_used") or fallback.get("terastallized")),
        "stats": dict(fallback.get("stats") or {}),
        "boosts": dict(side_state.get("boosts") or fallback.get("boosts") or {}),
        "volatiles": list(side_state.get("volatiles") or fallback.get("volatiles") or []),
    }


def _trace_payload_for_branch_evaluation(
    *,
    payload: Any,
    trajectory: Dict[str, Any],
    private_state: Dict[str, Any],
    player_side: str,
    candidates: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    if not isinstance(trajectory, dict):
        return payload

    protocol = trajectory.get("protocol_log") if isinstance(trajectory.get("protocol_log"), list) else []
    if not protocol and not trajectory.get("turns"):
        return payload
    tactical_state = private_state.get("tactical_state") if isinstance(private_state.get("tactical_state"), dict) else None
    if tactical_state is None:
        tactical_state = build_tactical_state(protocol, perspective_side=player_side)
    own_state = tactical_state.get("own") if isinstance(tactical_state.get("own"), dict) else {}
    opp_state = tactical_state.get("opponent") if isinstance(tactical_state.get("opponent"), dict) else {}
    request_payload = getattr(payload, "request", None)
    if not isinstance(request_payload, dict):
        request_payload = None

    active_private = _active_private_mon(private_state)
    own_view = _mon_view_from_state(own_state, fallback=active_private)
    opp_view = _mon_view_from_state(opp_state)
    turn = _latest_turn(trajectory)
    current_step = {
        "step_index": 0,
        "turn": turn,
        "view": {
            "env_id": str(trajectory.get("env_id") or ""),
            "format": str(trajectory.get("format") or "gen9randombattle"),
            "gen": 9,
            "turn": turn,
            "player": player_side,
            "opponent": "p2" if player_side == "p1" else "p1",
            "terminated": False,
            "winner": trajectory.get("winner"),
            "names": dict(trajectory.get("players") or {}),
            "team_size": {"p1": 6, "p2": 6},
            "active": {"self": 0, "opponent": 0},
            "field": {
                "weather": tactical_state.get("weather"),
                "terrain": tactical_state.get("terrain"),
                "pseudo_weather": list(tactical_state.get("field_effects") or []),
                "side_conditions": {
                    "self": dict(own_state.get("side_conditions") or {}),
                    "opponent": dict(opp_state.get("side_conditions") or {}),
                },
            },
            "self_team": [own_view],
            "opponent_team": [opp_view],
        },
        "request": request_payload,
        "legal_actions": [dict(candidate) for candidate in candidates],
        "p1_species" if player_side == "p1" else "p2_species": own_view.get("species"),
        "p2_species" if player_side == "p1" else "p1_species": opp_view.get("species"),
        "p1_hp_ratio" if player_side == "p1" else "p2_hp_ratio": own_view.get("hp_ratio"),
        "p2_hp_ratio" if player_side == "p1" else "p1_hp_ratio": opp_view.get("hp_ratio"),
        "p1_status" if player_side == "p1" else "p2_status": own_view.get("status"),
        "p2_status" if player_side == "p1" else "p1_status": opp_view.get("status"),
        "p1_boosts" if player_side == "p1" else "p2_boosts": own_view.get("boosts"),
        "p2_boosts" if player_side == "p1" else "p1_boosts": opp_view.get("boosts"),
    }
    trace = dict(trajectory)
    trace["turns"] = [{"turn": turn, "steps": [current_step]}]
    trace["protocol_log"] = list(protocol)
    return {"trace": trace}


def _policy_features_for_model(
    *,
    policy_metadata: Dict[str, Any],
    public_features: np.ndarray,
    live_features: np.ndarray,
) -> np.ndarray:
    input_size = int(policy_metadata.get("input_size", len(PUBLIC_FEATURE_NAMES)))
    if input_size == live_features.shape[0]:
        return live_features.astype(np.float32)
    if input_size == public_features.shape[0]:
        return public_features.astype(np.float32)
    selected = live_features if live_features.shape[0] < input_size else live_features[:input_size]
    if selected.shape[0] == input_size:
        return selected.astype(np.float32)
    padded = np.zeros(input_size, dtype=np.float32)
    padded[: selected.shape[0]] = selected
    return padded


def _policy_probs(
    *,
    policy_loader: PolicyLoader,
    public_features: np.ndarray,
    live_features: np.ndarray,
    device: torch.device,
) -> Tuple[Optional[np.ndarray], Dict[str, Any], List[str]]:
    policy_model, policy_metadata = policy_loader()
    metadata = policy_metadata or {}
    if policy_model is None or metadata.get("warning"):
        return None, metadata, [str(metadata.get("warning") or "No replay-policy checkpoint found; action recommendations limited.")]

    features = _policy_features_for_model(
        policy_metadata=metadata,
        public_features=public_features,
        live_features=live_features,
    )
    x = torch.tensor(features, dtype=torch.float32, device=device).unsqueeze(0)
    with torch.no_grad():
        policy_logits, _ = policy_model(x)
        probs = torch.softmax(policy_logits.squeeze(0), dim=0).detach().cpu().numpy()
    return probs, metadata, []


def _switch_proxy_private_state(private_state: Dict[str, Any], action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if str(action.get("kind")) != "switch":
        return None
    label = str(action.get("label") or "")
    target_species = label.split(":", 1)[1].strip() if ":" in label else label.strip()
    if not target_species:
        return None

    proxy = deepcopy(private_state)
    team = proxy.get("team") if isinstance(proxy.get("team"), list) else []
    selected = None
    for mon in team:
        if not isinstance(mon, dict):
            continue
        species = str(mon.get("species") or "")
        if species.lower() == target_species.lower():
            selected = mon
            break
    if selected is None:
        return None
    for mon in team:
        if isinstance(mon, dict):
            mon["active"] = False
    selected["active"] = True
    proxy["active_species"] = selected.get("species") or target_species
    proxy["active_moves"] = [
        {"id": str(move).lower().replace(" ", ""), "name": str(move), "pp": 1, "maxpp": 1, "disabled": False}
        for move in selected.get("moves", [])[:4]
        if str(move)
    ]
    return proxy


def _estimate_switch_value(
    *,
    action: Dict[str, Any],
    private_state: Dict[str, Any],
    public_features: np.ndarray,
    opponent_belief: Dict[str, Any],
    trajectory: Dict[str, Any],
    player_side: Optional[str],
    value_model: Optional[torch.nn.Module],
    value_metadata: Dict[str, Any],
    device: torch.device,
) -> Tuple[Optional[float], Optional[str], Dict[str, Any]]:
    if value_model is None or not value_metadata.get("uses_live_private_features"):
        return None, None, {}
    proxy_state = _switch_proxy_private_state(private_state, action)
    if proxy_state is None:
        return None, None, {}
    features, _ = build_live_private_feature_vector(
        public_features=public_features,
        private_state=proxy_state,
        opponent_belief=opponent_belief,
        trajectory=trajectory,
        player_side=player_side,
    )
    x = torch.tensor(features, dtype=torch.float32, device=device).unsqueeze(0)
    with torch.no_grad():
        estimated_value = _model_output_value(value_model(x))
    return estimated_value, "switch_proxy", {"proxy_feature_dim": int(features.shape[0])}


def _switch_damage_fields() -> Dict[str, Any]:
    return {
        "damage_method": "not_applicable_switch",
        "damage_rolls": [],
        "average_percent": None,
        "min_percent": None,
        "max_percent": None,
        "ko_chance": None,
        "immune": None,
        "type_effectiveness": None,
        "tera_damage_bonus": None,
    }


def _empty_score_components(
    *,
    current_value: float,
    ranker_score: Optional[float],
    policy_prob: Optional[float],
    rollout_expected_value: Optional[float],
    rollout_weight: float,
    ranker_weight: float,
    policy_weight: float,
    final_score: Optional[float],
) -> Dict[str, Any]:
    return {
        "current_value": float(current_value),
        "ranker_score": ranker_score,
        "policy_prob": policy_prob,
        "rollout_expected_value": rollout_expected_value,
        "rollout_weight": float(rollout_weight),
        "ranker_weight": float(ranker_weight),
        "policy_weight": float(policy_weight),
        "final_score": final_score,
    }


class ActionValueEstimator:
    def __init__(
        self,
        *,
        value_model: Optional[torch.nn.Module],
        value_metadata: Dict[str, Any],
        policy_loader: PolicyLoader,
        action_ranker_model: Optional[ActionRankerMLP],
        action_ranker_metadata: Optional[Dict[str, Any]],
        device: torch.device,
    ) -> None:
        self.value_model = value_model
        self.value_metadata = value_metadata
        self.policy_loader = policy_loader
        self.action_ranker_model = action_ranker_model
        self.action_ranker_metadata = action_ranker_metadata or {}
        self.device = device

    def estimate(
        self,
        *,
        payload: Any,
        legal_action: Dict[str, Any],
        private_state: Dict[str, Any],
        opponent_belief: Dict[str, Any],
        trajectory: Dict[str, Any],
        public_features: np.ndarray,
        live_features: np.ndarray,
        current_value: float,
        policy_probs: Optional[np.ndarray],
    ) -> Dict[str, Any]:
        action_index = int(legal_action.get("index", 0) or 0)
        disabled = bool(legal_action.get("disabled", False))
        policy_prob = (
            float(policy_probs[action_index])
            if policy_probs is not None and 0 <= action_index < len(policy_probs) and not disabled
            else 0.0
        )
        player_side = private_state.get("player_side") if private_state.get("player_side") in ("p1", "p2") else None
        estimated_value, proxy_method, proxy_components = _estimate_switch_value(
            action=legal_action,
            private_state=private_state,
            public_features=public_features,
            opponent_belief=opponent_belief,
            trajectory=trajectory,
            player_side=player_side,
            value_model=self.value_model,
            value_metadata=self.value_metadata,
            device=self.device,
        )
        ranker_score = None
        if self.action_ranker_model is not None:
            state_dim = int(self.action_ranker_metadata.get("state_dim", live_features.shape[0]))
            action_dim = int(self.action_ranker_metadata.get("action_dim", ACTION_FEATURE_DIM))
            state_part = live_features.astype(np.float32)
            if state_part.shape[0] != state_dim:
                state_part = state_part[:state_dim] if state_part.shape[0] > state_dim else np.pad(state_part, (0, state_dim - state_part.shape[0]))
            private_context = dict(private_state)
            private_context["opponent_belief"] = opponent_belief
            action_features = build_action_feature_vector(legal_action, private_context).astype(np.float32)
            if action_features.shape[0] != action_dim:
                action_features = action_features[:action_dim] if action_features.shape[0] > action_dim else np.pad(action_features, (0, action_dim - action_features.shape[0]))
            ranker_input = np.concatenate([state_part, action_features]).astype(np.float32)
            x_ranker = torch.from_numpy(ranker_input).to(self.device).unsqueeze(0)
            with torch.no_grad():
                ranker_score = float(self.action_ranker_model(x_ranker).squeeze().detach().cpu().item())

        if ranker_score is not None:
            method = str(self.action_ranker_metadata.get("response_method") or "action_ranker")
        elif proxy_method and policy_probs is not None:
            method = "policy_prior+switch_proxy"
        else:
            method = proxy_method or ("policy_prior" if policy_probs is not None else "rollout_unavailable")
        value_component = 0.0 if estimated_value is None else 0.05 * float(estimated_value)
        score = 0.0 if disabled else float(ranker_score if ranker_score is not None else policy_prob + value_component)
        action_category = classify_action_category(legal_action)
        damage_fields = _switch_damage_fields() if action_category == "switch" else {
            "damage_method": None,
            "damage_rolls": [],
            "average_percent": None,
            "min_percent": None,
            "max_percent": None,
            "ko_chance": None,
            "immune": None,
            "type_effectiveness": None,
            "tera_damage_bonus": None,
        }
        return {
            "index": action_index,
            "label": str(legal_action.get("label") or f"action:{action_index}"),
            "kind": str(legal_action.get("kind") or "unknown"),
            "action_category": action_category,
            "disabled": disabled,
            "policy_prob": policy_prob if policy_probs is not None else None,
            "ranker_score": ranker_score,
            "estimated_value": estimated_value,
            "score": score,
            "score_components": {
                "policy_prob": policy_prob if policy_probs is not None else None,
                "ranker_score": ranker_score,
                "current_value": float(current_value),
                "estimated_value_weight": 0.0 if ranker_score is not None else 0.05 if estimated_value is not None else 0.0,
                **proxy_components,
            },
            "method": method,
            "rollout_count": 0,
            "depth": 0,
            "mean_value": estimated_value,
            "std_value": None,
            "diagnostics": {
                "damage": _switch_damage_fields() if action_category == "switch" else {},
                "speed_order": {},
                "switch_hazards": {},
                "restrictions": {},
            },
            **damage_fields,
        }


def recommend_actions(
    *,
    payload: Any,
    private_state: Dict[str, Any],
    opponent_belief: Dict[str, Any],
    trajectory: Dict[str, Any],
    public_features: np.ndarray,
    live_features: np.ndarray,
    current_value: float,
    value_model: Optional[torch.nn.Module],
    value_metadata: Dict[str, Any],
    policy_loader: PolicyLoader,
    device: torch.device,
    limit: int = 5,
) -> Dict[str, Any]:
    candidates = legal_action_candidates(payload)
    if not candidates:
        return {
            "top_actions": [],
            "action_recommendation_method": "no_legal_actions",
            "policy_checkpoint_loaded": False,
            "policy_checkpoint_path": None,
            "warnings": ["No legal actions supplied by request."],
        }

    policy_probs, policy_metadata, warnings = _policy_probs(
        policy_loader=policy_loader,
        public_features=public_features,
        live_features=live_features,
        device=device,
    )
    action_ranker_model, action_ranker_metadata = load_action_ranker_once(device=device)
    if action_ranker_model is None and action_ranker_metadata and action_ranker_metadata.get("warning"):
        warnings.append(str(action_ranker_metadata["warning"]))
    estimator = ActionValueEstimator(
        value_model=value_model,
        value_metadata=value_metadata,
        policy_loader=policy_loader,
        action_ranker_model=action_ranker_model,
        action_ranker_metadata=action_ranker_metadata,
        device=device,
    )
    all_rows = [
        estimator.estimate(
            payload=payload,
            legal_action=candidate,
            private_state=private_state,
            opponent_belief=opponent_belief,
            trajectory=trajectory,
            public_features=public_features,
            live_features=live_features,
            current_value=current_value,
            policy_probs=policy_probs,
        )
        for candidate in candidates
    ]

    rollout_cfg = {
        "rollouts_per_action": int(os.environ.get("NEURAL_ROLLOUTS_PER_ACTION", "8")),
        "value_checkpoint": None,
        "rollout_mode": os.environ.get("NEURAL_ROLLOUT_MODE", "auto"),
    }

    # Attempt to evaluate actions via simulator branching (best-effort fallback to trace continuation).
    try:
        player_side = private_state.get("player_side") if private_state.get("player_side") in ("p1", "p2") else "p1"
        opponent_policy = os.environ.get("NEURAL_OPPONENT_POLICY", "uniform")
        sim_payload = _trace_payload_for_branch_evaluation(
            payload=payload,
            trajectory=trajectory,
            private_state=private_state,
            player_side=player_side,
            candidates=candidates,
        )
        sim_results = evaluate_branch_actions(sim_payload, player_side, candidates, opponent_policy, rollout_cfg) or []
    except Exception as exc:  # pragma: no cover - best-effort
        sim_results = []

    # Merge sim rollout expected values into rows when available and compute final_score
    label_to_sim = {str(r.get("label")): r for r in sim_results}
    # Normalize ranker_score if present
    ranker_scores = [r.get("ranker_score") for r in all_rows if r.get("ranker_score") is not None]
    rank_min = min(ranker_scores) if ranker_scores else None
    rank_max = max(ranker_scores) if ranker_scores else None
    def normalize_rank(s: Optional[float]) -> float:
        if s is None or rank_min is None or rank_max is None or rank_max == rank_min:
            return 0.0
        return float((s - rank_min) / (rank_max - rank_min))

    rollout_weight = float(os.environ.get("NEURAL_ROLLOUT_WEIGHT", "0.75"))
    ranker_weight = float(os.environ.get("NEURAL_RANKER_WEIGHT", "0.20"))
    policy_weight = float(os.environ.get("NEURAL_POLICY_WEIGHT", "0.05"))

    for row in all_rows:
        sim = label_to_sim.get(row.get("label"))
        expected_value = sim.get("expected_value") if sim else None
        row["expected_value"] = expected_value
        if sim:
            for key in (
                "action_category",
                "method",
                "rollout_mode",
                "approximate_state",
                "rollout_count",
                "opponent_actions_considered",
                "top_resulting_states",
                "approximation_warnings",
                "rollout_unavailable_reason",
                "rollout_unavailable_details",
                "diagnostics",
                "damage_method",
                "damage_rolls",
                "average_percent",
                "min_percent",
                "max_percent",
                "ko_chance",
                "immune",
                "type_effectiveness",
                "tera_damage_bonus",
            ):
                if key in sim:
                    row[key] = sim.get(key)
        row["action_category"] = row.get("action_category") or classify_action_category(row)
        if row["action_category"] == "switch":
            row.update(_switch_damage_fields())
            diagnostics = row.get("diagnostics") if isinstance(row.get("diagnostics"), dict) else {}
            diagnostics["damage"] = _switch_damage_fields()
            row["diagnostics"] = diagnostics
        # compute normalized ranker score
        row_norm_rank = normalize_rank(row.get("ranker_score"))
        policy_prob = float(row.get("policy_prob") or 0.0)
        if expected_value is not None:
            # Compose final score using weights; keep numeric fields safe
            row["final_score"] = (
                rollout_weight * float(expected_value)
                + ranker_weight * float(row_norm_rank)
                + policy_weight * float(policy_prob)
            )
            row["method"] = sim.get("method") if sim and sim.get("method") else row.get("method")
        else:
            # Fallback to previous score
            row["final_score"] = float(row.get("score") or 0.0)
        row["score_components"] = _empty_score_components(
            current_value=current_value,
            ranker_score=row.get("ranker_score"),
            policy_prob=row.get("policy_prob"),
            rollout_expected_value=expected_value,
            rollout_weight=rollout_weight,
            ranker_weight=ranker_weight,
            policy_weight=policy_weight,
            final_score=row.get("final_score"),
        )

    def assign_rank(field: str, rank_field: str) -> None:
        rankable = [row for row in all_rows if not row.get("disabled") and row.get(field) is not None]
        ranked_for_field = sorted(rankable, key=lambda item: float(item.get(field) or 0.0), reverse=True)
        for rank, row in enumerate(ranked_for_field, start=1):
            row[rank_field] = rank
        for row in all_rows:
            row.setdefault(rank_field, None)

    assign_rank("ranker_score", "ranker_only_rank")
    assign_rank("expected_value", "rollout_only_rank")
    assign_rank("final_score", "final_rank")

    enabled = [row for row in all_rows if not row.get("disabled")]
    rows = enabled if enabled else all_rows
    ranked = sorted(rows, key=lambda item: item.get("final_score", item.get("score", 0.0)), reverse=True)
    if not enabled:
        warnings.append("All legal actions are marked disabled or forced; returning disabled actions.")
    if policy_probs is None:
        warnings.append("No replay-policy checkpoint found; action recommendations limited.")

    methods = {row["method"] for row in ranked}
    if "exact_sim_rollout" in methods:
        recommendation_method = "exact_sim_rollout"
    elif "approx_sim_rollout" in methods:
        recommendation_method = "approx_sim_rollout"
    elif "action_value_ranker" in methods:
        recommendation_method = "action_value_ranker"
    elif "action_ranker" in methods:
        recommendation_method = "action_ranker"
    elif "policy_prior+switch_proxy" in methods or "switch_proxy" in methods:
        recommendation_method = "policy_prior+switch_proxy"
    elif policy_probs is not None:
        recommendation_method = "policy_prior"
    else:
        recommendation_method = "rollout_unavailable"

    def top_label(field: str) -> Optional[str]:
        candidates_for_field = [row for row in rows if not row.get("disabled") and row.get(field) is not None]
        if not candidates_for_field:
            return None
        return str(max(candidates_for_field, key=lambda item: float(item.get(field) or 0.0)).get("label"))

    action_category_counts: Dict[str, int] = {}
    for row in rows:
        category = str(row.get("action_category") or "unknown")
        action_category_counts[category] = action_category_counts.get(category, 0) + 1

    return {
        "top_actions": ranked[:limit],
        "all_action_estimates": rows,
        "action_recommendation_method": recommendation_method,
        "rollout_mode": rollout_cfg.get("rollout_mode"),
        "rollouts_per_action": rollout_cfg.get("rollouts_per_action"),
        "rollout_weight": rollout_weight,
        "ranker_weight": ranker_weight,
        "policy_weight": policy_weight,
        "top_action_by_ranker": top_label("ranker_score"),
        "top_action_by_rollout": top_label("expected_value"),
        "top_action_by_final_score": str(ranked[0].get("label")) if ranked else None,
        "action_category_counts": action_category_counts,
        "policy_checkpoint_loaded": policy_probs is not None,
        "policy_checkpoint_path": policy_metadata.get("path"),
        "action_ranker_loaded": action_ranker_model is not None,
        "action_ranker_path": (action_ranker_metadata or {}).get("path"),
        "action_ranker_input_size": (action_ranker_metadata or {}).get("input_size"),
        "action_value_ranker_loaded": action_ranker_model is not None
        and (action_ranker_metadata or {}).get("response_method") == "action_value_ranker",
        "action_value_ranker_path": (action_ranker_metadata or {}).get("path")
        if (action_ranker_metadata or {}).get("response_method") == "action_value_ranker"
        else None,
        "warnings": sorted(set(warnings)),
    }
