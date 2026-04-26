import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .featurize import GLOBAL_DIM, POKEMON_DIM, REQUEST_DIM, featurize_battle
from .schema import BattleView, ChoiceRequestView


BASE_FEATURE_DIM = GLOBAL_DIM + (6 * POKEMON_DIM) + (6 * POKEMON_DIM) + REQUEST_DIM
VALUE_EXTRA_DIM = 16
VALUE_FEATURE_DIM = BASE_FEATURE_DIM + VALUE_EXTRA_DIM
VALUE_FEATURE_VERSION = "base-v1-plus-value-extras-v1"


def final_result_from_winner(winner: Optional[str]) -> float:
    if winner == "p1":
        return 1.0
    if winner == "p2":
        return -1.0
    return 0.0


def discounted_terminal_return(final_result: float, steps_to_terminal: int, gamma: float) -> float:
    if gamma <= 0:
        raise ValueError("gamma must be positive.")
    return float(final_result) * (float(gamma) ** max(0, int(steps_to_terminal)))


def adapt_feature_vector(vector: np.ndarray, input_size: int) -> np.ndarray:
    if vector.shape[0] == input_size:
        return vector.astype(np.float32, copy=False)
    if vector.shape[0] > input_size:
        return vector[:input_size].astype(np.float32, copy=False)
    padded = np.zeros(input_size, dtype=np.float32)
    padded[: vector.shape[0]] = vector.astype(np.float32, copy=False)
    return padded


def flatten_trace_steps(trace: Dict[str, Any]) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for turn in trace.get("turns", []):
        if not isinstance(turn, dict):
            continue
        turn_number = int(turn.get("turn", len(flattened) + 1) or 0)
        for local_index, step in enumerate(turn.get("steps", [])):
            if not isinstance(step, dict):
                continue
            enriched = dict(step)
            enriched.setdefault("turn", turn_number)
            enriched.setdefault("step_index", len(flattened))
            enriched.setdefault("turn_step_index", local_index)
            flattened.append(enriched)
    return flattened


def load_trace(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_trace_step(trace: Dict[str, Any], step_index: int) -> Tuple[Dict[str, Any], int, bool]:
    steps = flatten_trace_steps(trace)
    if not steps:
        raise ValueError("Trace does not contain any decision steps.")
    for index, step in enumerate(steps):
        if int(step.get("step_index", index)) == int(step_index):
            return step, index, True
    clamped_index = min(max(0, int(step_index)), len(steps) - 1)
    return steps[clamped_index], clamped_index, False


def _active_index(team: Sequence[Dict[str, Any]]) -> Optional[int]:
    for index, pokemon in enumerate(team):
        if pokemon.get("active"):
            return index
    return 0 if team else None


def _blank_field() -> Dict[str, Any]:
    return {
        "weather": None,
        "terrain": None,
        "pseudo_weather": [],
        "side_conditions": {"self": {}, "opponent": {}},
    }


def _minimal_pokemon(
    species: str,
    hp_ratio: float,
    status: Optional[str],
    boosts: Optional[Dict[str, int]] = None,
    *,
    slot: int = 0,
    active: bool = True,
) -> Dict[str, Any]:
    return {
        "slot": slot,
        "ident": species,
        "name": species,
        "species": species,
        "details": species,
        "active": active,
        "fainted": float(hp_ratio or 0.0) <= 0.0,
        "hp_text": None,
        "hp_ratio": float(hp_ratio or 0.0),
        "status": status,
        "gender": None,
        "level": 100,
        "item": None,
        "ability": None,
        "base_ability": None,
        "moves": [],
        "revealed_moves": [],
        "types": [],
        "tera_type": None,
        "terastallized": False,
        "stats": {},
        "boosts": dict(boosts or {}),
        "volatiles": [],
        "possible_roles": [],
        "possible_moves": [],
        "possible_abilities": [],
        "possible_tera_types": [],
    }


def _trace_step_species(step: Dict[str, Any], prefix: str) -> str:
    direct = step.get(f"{prefix}_species")
    if direct:
        return str(direct)
    if prefix == "p1":
        return str(step.get("active_species") or step.get("species") or "Unknown")
    return str(step.get("opponent_active_species") or step.get("opponent_species") or "Unknown")


def _trace_step_hp(step: Dict[str, Any], prefix: str) -> float:
    for key in [f"{prefix}_hp_ratio", "hp_ratio" if prefix == "p1" else "opponent_hp_ratio"]:
        if key in step and step.get(key) is not None:
            return float(step.get(key) or 0.0)
    return 0.0


def _trace_step_status(step: Dict[str, Any], prefix: str) -> Optional[str]:
    for key in [f"{prefix}_status", "status" if prefix == "p1" else "opponent_status"]:
        if key in step:
            status = step.get(key)
            return str(status) if status else None
    return None


def _normalize_legal_actions(raw_actions: Any) -> List[Optional[Dict[str, Any]]]:
    actions: List[Optional[Dict[str, Any]]] = [None] * 13
    if not isinstance(raw_actions, list):
        return actions
    for fallback_index, action in enumerate(raw_actions):
        if not action:
            continue
        if not isinstance(action, dict):
            continue
        raw_index = action.get("index", fallback_index)
        try:
            action_index = int(raw_index)
        except (TypeError, ValueError):
            continue
        if not 0 <= action_index < 13:
            continue
        label = str(action.get("label") or action.get("choice") or f"action:{action_index}")
        choice = str(action.get("choice") or _choice_from_index(action_index))
        kind = str(action.get("kind") or ("switch" if action_index >= 8 else "move"))
        move_name = action.get("move")
        if move_name is None and label.startswith("move:"):
            move_name = label.split(":", 1)[1]
        actions[action_index] = {
            "index": action_index,
            "kind": kind,
            "choice": choice,
            "label": label,
            "move": str(move_name) if move_name else None,
            "slot": action.get("slot"),
        }
    return actions


def _choice_from_index(action_index: int) -> str:
    if 0 <= action_index <= 3:
        return f"move {action_index + 1}"
    if 4 <= action_index <= 7:
        return f"move {action_index - 3} terastallize"
    return f"switch {action_index - 7}"


def _move_slots_from_actions(actions: Sequence[Optional[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    moves: List[Dict[str, Any]] = []
    seen_slots = set()
    for action_index, action in enumerate(actions):
        if not action or action.get("kind") != "move":
            continue
        slot = int(action.get("slot") or ((action_index % 4) + 1))
        if slot in seen_slots or not 1 <= slot <= 4:
            continue
        seen_slots.add(slot)
        move_name = str(action.get("move") or action.get("label") or f"move {slot}")
        if move_name.startswith("move:"):
            move_name = move_name.split(":", 1)[1]
        moves.append(
            {
                "slot": slot,
                "move": move_name,
                "id": re.sub(r"[^a-z0-9]+", "", move_name.lower()),
                "pp": 1,
                "maxpp": 1,
                "target": "normal",
                "disabled": False,
                "type": None,
                "category": None,
                "base_power": 0,
                "accuracy": None,
            }
        )
    moves.sort(key=lambda item: item["slot"])
    return moves


def minimal_view_request_from_trace_step(trace: Dict[str, Any], step: Dict[str, Any]) -> Tuple[BattleView, ChoiceRequestView]:
    actions = _normalize_legal_actions(step.get("legal_actions"))
    legal_mask = [action is not None for action in actions]
    p1_boosts = step.get("p1_boosts") or step.get("boosts") or {}
    p2_boosts = step.get("p2_boosts") or {}

    view: BattleView = {
        "env_id": str(trace.get("env_id") or ""),
        "format": str(trace.get("format") or "gen9randombattle"),
        "gen": 9,
        "turn": int(step.get("turn", 0) or 0),
        "player": "p1",
        "opponent": "p2",
        "terminated": False,
        "winner": trace.get("winner"),
        "names": {"p1": "Agent-1", "p2": "Agent-2"},
        "team_size": {"p1": 6, "p2": 6},
        "active": {"self": 0, "opponent": 0},
        "field": _blank_field(),
        "self_team": [
            _minimal_pokemon(
                _trace_step_species(step, "p1"),
                _trace_step_hp(step, "p1"),
                _trace_step_status(step, "p1"),
                p1_boosts,
                slot=0,
            )
        ],
        "opponent_team": [
            _minimal_pokemon(
                _trace_step_species(step, "p2"),
                _trace_step_hp(step, "p2"),
                _trace_step_status(step, "p2"),
                p2_boosts,
                slot=0,
            )
        ],
    }

    request: ChoiceRequestView = {
        "player": "p1",
        "wait": False,
        "team_preview": False,
        "force_switch": False,
        "trapped": False,
        "rqid": None,
        "active": {
            "moves": _move_slots_from_actions(actions),
            "can_terastallize": any(bool(action) for action in actions[4:8]),
            "tera_type": None,
            "trapped": False,
            "can_switch": any(bool(action) for action in actions[8:13]),
        },
        "side": [],
        "legal_actions": {
            "mask": legal_mask,
            "actions": actions,
            "available_indices": [index for index, action in enumerate(actions) if action is not None],
        },
        "raw": {},
    }
    return view, request


def view_request_from_step(trace: Dict[str, Any], step: Dict[str, Any]) -> Tuple[BattleView, Optional[ChoiceRequestView]]:
    view = step.get("view")
    request = step.get("request")
    if isinstance(view, dict):
        return view, request if isinstance(request, dict) else None
    return minimal_view_request_from_trace_step(trace, step)


def _remaining_fraction(team: Sequence[Dict[str, Any]]) -> float:
    if not team:
        return 0.0
    remaining = sum(1 for pokemon in team if not pokemon.get("fainted") and float(pokemon.get("hp_ratio") or 0.0) > 0.0)
    return float(remaining) / 6.0


def _active_volatiles_fraction(team: Sequence[Dict[str, Any]]) -> float:
    index = _active_index(team)
    if index is None or index >= len(team):
        return 0.0
    volatiles = team[index].get("volatiles", [])
    return min(1.0, float(len(volatiles)) / 10.0) if isinstance(volatiles, list) else 0.0


def _choice_label(step: Dict[str, Any]) -> str:
    return str(step.get("chosen_action_choice") or step.get("chosen_action_label") or step.get("chosen_action") or "")


def repeated_action_count(step_history: Sequence[Dict[str, Any]], current_step: Optional[Dict[str, Any]]) -> int:
    if not current_step:
        return 0
    label = _choice_label(current_step)
    if not label:
        return 0
    count = 0
    for previous in reversed(step_history):
        if _choice_label(previous) != label:
            break
        count += 1
    return count


def _parse_hp_fraction(text: str) -> Optional[float]:
    if not text:
        return None
    percent = re.search(r"(\d+(?:\.\d+)?)%", text)
    if percent:
        return max(0.0, min(1.0, float(percent.group(1)) / 100.0))
    fraction = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if fraction:
        denominator = float(fraction.group(2))
        if denominator > 0:
            return max(0.0, min(1.0, float(fraction.group(1)) / denominator))
    return None


def _recent_protocol_features(protocol_lines: Sequence[str]) -> Tuple[float, float, float, float, float]:
    damage_to_p1 = 0.0
    damage_to_p2 = 0.0
    last_switch = 0.0
    last_faint = 0.0
    recent_count = min(1.0, float(len(protocol_lines)) / 20.0)
    for line in protocol_lines[-20:]:
        if not isinstance(line, str):
            continue
        if line.startswith("|switch|"):
            last_switch = 1.0
        if line.startswith("|faint|"):
            last_faint = 1.0
        if line.startswith("|-damage|"):
            parts = line.split("|")
            ident = parts[2] if len(parts) > 2 else ""
            hp_text = parts[3] if len(parts) > 3 else ""
            hp_fraction = _parse_hp_fraction(hp_text)
            if hp_fraction is None:
                continue
            damage = max(0.0, 1.0 - hp_fraction)
            if ident.startswith("p1"):
                damage_to_p1 = max(damage_to_p1, damage)
            if ident.startswith("p2"):
                damage_to_p2 = max(damage_to_p2, damage)
    return damage_to_p1, damage_to_p2, last_switch, last_faint, recent_count


def value_extra_features(
    view: BattleView,
    request: Optional[ChoiceRequestView],
    *,
    protocol_history: Optional[Sequence[str]] = None,
    step_history: Optional[Sequence[Dict[str, Any]]] = None,
    current_step: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    vector = np.zeros(VALUE_EXTRA_DIM, dtype=np.float32)
    own_team = view.get("self_team", [])
    opp_team = view.get("opponent_team", [])
    legal_actions = request.get("legal_actions", {}).get("actions", []) if request else []
    legal_action_items = [action for action in legal_actions if action]
    legal_move_count = sum(1 for action in legal_action_items if action.get("kind") == "move")
    legal_switch_count = sum(1 for action in legal_action_items if action.get("kind") == "switch")
    active = request.get("active") if request else None

    vector[0] = _remaining_fraction(own_team)
    vector[1] = _remaining_fraction(opp_team)
    vector[2] = _active_volatiles_fraction(own_team)
    vector[3] = _active_volatiles_fraction(opp_team)
    vector[4] = min(1.0, float(len(legal_action_items)) / 13.0)
    vector[5] = min(1.0, float(legal_move_count) / 8.0)
    vector[6] = min(1.0, float(legal_switch_count) / 5.0)
    vector[7] = float(bool(active and active.get("can_terastallize")))
    vector[8] = float(bool(request and request.get("force_switch")))
    vector[9] = float(bool(request and request.get("trapped")))
    vector[10] = min(1.0, float(repeated_action_count(step_history or [], current_step)) / 5.0)
    damage_to_p1, damage_to_p2, last_switch, last_faint, recent_count = _recent_protocol_features(protocol_history or [])
    vector[11] = damage_to_p1
    vector[12] = damage_to_p2
    vector[13] = last_switch
    vector[14] = last_faint
    vector[15] = recent_count
    return vector


def featurize_value_state(
    view: BattleView,
    request: Optional[ChoiceRequestView],
    *,
    protocol_history: Optional[Sequence[str]] = None,
    step_history: Optional[Sequence[Dict[str, Any]]] = None,
    current_step: Optional[Dict[str, Any]] = None,
    include_extras: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    base = featurize_battle(view, request)
    if not include_extras:
        return base.flat.astype(np.float32), base.legal_mask.astype(np.float32)
    extras = value_extra_features(
        view,
        request,
        protocol_history=protocol_history,
        step_history=step_history,
        current_step=current_step,
    )
    return np.concatenate([base.flat, extras]).astype(np.float32), base.legal_mask.astype(np.float32)


def action_labels_from_request(request: Optional[ChoiceRequestView]) -> List[Dict[str, Any]]:
    if not request:
        return []
    labels = []
    actions = request.get("legal_actions", {}).get("actions", [])
    for index, action in enumerate(actions):
        if not action:
            continue
        labels.append(
            {
                "index": int(action.get("index", index)),
                "label": str(action.get("label") or action.get("choice") or f"action:{index}"),
                "choice": str(action.get("choice") or ""),
                "kind": str(action.get("kind") or "unknown"),
            }
        )
    return labels


def finite_mean(values: Iterable[float]) -> float:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    return float(np.mean(clean)) if clean else 0.0
