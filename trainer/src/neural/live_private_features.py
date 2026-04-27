import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .build_replay_value_dataset import (
    FEATURE_NAMES as PUBLIC_FEATURE_NAMES,
    FEATURE_VERSION as PUBLIC_FEATURE_VERSION,
    _apply_event,
    _feature_vector,
    _initial_state,
    _new_recent,
)
from .live_opponent_beliefs import build_opponent_beliefs
from .live_private_state import extract_private_side_state
from .parse_replay_logs import parse_protocol_log


FEATURE_VERSION = "live-private-belief-v1"

PRIVATE_FEATURE_NAMES = [
    "missing_private_state",
    "own_remaining_count_norm",
    "own_active_hp_fraction",
    "own_team_hp_fraction_slot_1",
    "own_team_hp_fraction_slot_2",
    "own_team_hp_fraction_slot_3",
    "own_team_hp_fraction_slot_4",
    "own_team_hp_fraction_slot_5",
    "own_team_hp_fraction_slot_6",
    "own_team_hp_mean",
    "own_team_hp_min",
    "own_team_hp_max",
    "own_fainted_count_norm",
    "active_move_count_norm",
    "disabled_move_count_norm",
    "active_move_pp_fraction_slot_1",
    "active_move_pp_fraction_slot_2",
    "active_move_pp_fraction_slot_3",
    "active_move_pp_fraction_slot_4",
    "active_move_pp_mean",
    "active_move_pp_min",
    "own_team_item_known_fraction",
    "own_active_item_known",
    "own_team_ability_known_fraction",
    "own_active_ability_known",
    "own_active_tera_type_known",
    "tera_available_visible",
    "force_switch",
    "wait",
    "trapped",
    "legal_move_count_norm",
    "legal_switch_count_norm",
    "legal_action_count_norm",
]

OPPONENT_BELIEF_FEATURE_NAMES = [
    "opponent_active_species_known",
    "opponent_revealed_move_count_norm",
    "opponent_candidate_count_log_norm",
    "opponent_candidate_entropy_norm",
    "opponent_top_possible_move_count_norm",
    "opponent_possible_ability_count_norm",
    "opponent_possible_tera_type_count_norm",
    "opponent_revealed_item",
    "opponent_revealed_ability",
    "opponent_revealed_tera",
    "opponent_fainted_count_norm",
    "opponent_remaining_estimate_norm",
    "opponent_filter_relaxed",
    "opponent_known_count_norm",
]

FEATURE_NAMES = list(PUBLIC_FEATURE_NAMES) + PRIVATE_FEATURE_NAMES + OPPONENT_BELIEF_FEATURE_NAMES
FEATURE_DIM = len(FEATURE_NAMES)


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return low
    if not math.isfinite(number):
        return low
    return max(low, min(high, number))


def _safe_count_norm(count: int, denominator: int) -> float:
    return _clip(float(count) / float(max(1, denominator)))


def _hp_fraction(mon: Dict[str, Any]) -> float:
    for key in ("hp_fraction", "hp_ratio"):
        if mon.get(key) is not None:
            return _clip(float(mon.get(key) or 0.0))
    if mon.get("fainted"):
        return 0.0
    return 1.0


def _known(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _active_team_member(private_state: Dict[str, Any]) -> Dict[str, Any]:
    team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
    for mon in team:
        if isinstance(mon, dict) and mon.get("active"):
            return mon
    return team[0] if team and isinstance(team[0], dict) else {}


def private_state_feature_vector(private_state: Optional[Dict[str, Any]]) -> np.ndarray:
    if not isinstance(private_state, dict) or not private_state.get("team"):
        values = [1.0] + [0.0] * (len(PRIVATE_FEATURE_NAMES) - 1)
        return np.asarray(values, dtype=np.float32)

    team = [mon for mon in private_state.get("team", []) if isinstance(mon, dict)]
    active = _active_team_member(private_state)
    moves = [move for move in private_state.get("active_moves", []) if isinstance(move, dict)]
    legal_actions = [action for action in private_state.get("legal_actions", []) if isinstance(action, dict)]

    hp_values = [_hp_fraction(mon) for mon in team[:6]]
    padded_hp = hp_values + [0.0] * max(0, 6 - len(hp_values))
    remaining = sum(1 for hp, mon in zip(padded_hp, team + [{}] * 6) if hp > 0.0 and not mon.get("fainted"))
    fainted = sum(1 for mon in team if bool(mon.get("fainted")) or _hp_fraction(mon) <= 0.0)

    pp_values: List[float] = []
    disabled_count = 0
    for move in moves[:4]:
        if move.get("disabled"):
            disabled_count += 1
        pp = move.get("pp")
        maxpp = move.get("maxpp")
        if isinstance(pp, (int, float)) and isinstance(maxpp, (int, float)) and float(maxpp) > 0:
            pp_values.append(_clip(float(pp) / float(maxpp)))
        elif _known(move.get("name") or move.get("id")):
            pp_values.append(1.0)
        else:
            pp_values.append(0.0)
    padded_pp = pp_values + [0.0] * max(0, 4 - len(pp_values))

    legal_move_count = sum(1 for action in legal_actions if str(action.get("kind", "")).startswith("move") and not action.get("disabled"))
    legal_switch_count = sum(1 for action in legal_actions if str(action.get("kind", "")) == "switch" and not action.get("disabled"))
    legal_count = sum(1 for action in legal_actions if not action.get("disabled"))

    values = [
        0.0,
        _safe_count_norm(remaining, 6),
        _hp_fraction(active) if active else 0.0,
        *padded_hp[:6],
        float(np.mean(padded_hp[:6])) if padded_hp else 0.0,
        float(np.min(padded_hp[:6])) if padded_hp else 0.0,
        float(np.max(padded_hp[:6])) if padded_hp else 0.0,
        _safe_count_norm(fainted, 6),
        _safe_count_norm(len(moves), 4),
        _safe_count_norm(disabled_count, 4),
        *padded_pp[:4],
        float(np.mean(padded_pp[:4])) if padded_pp else 0.0,
        float(np.min(padded_pp[:4])) if padded_pp else 0.0,
        _safe_count_norm(sum(1 for mon in team if _known(mon.get("item"))), 6),
        float(_known(active.get("item"))),
        _safe_count_norm(sum(1 for mon in team if _known(mon.get("ability") or mon.get("base_ability"))), 6),
        float(_known(active.get("ability") or active.get("base_ability"))),
        float(_known(active.get("tera_type"))),
        float(any(bool(move.get("can_tera")) for move in moves) or bool(private_state.get("can_tera"))),
        float(bool(private_state.get("force_switch"))),
        float(bool(private_state.get("wait"))),
        float(bool(private_state.get("trapped"))),
        _safe_count_norm(legal_move_count, 8),
        _safe_count_norm(legal_switch_count, 5),
        _safe_count_norm(legal_count, 13),
    ]
    return np.asarray(values, dtype=np.float32)


def _species_from_event_text(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value)
    if ": " in text:
        text = text.split(": ", 1)[1]
    return text.split(",", 1)[0].strip() or None


def infer_opponent_active_species(trajectory: Dict[str, Any], player_side: Optional[str]) -> Optional[str]:
    if player_side not in ("p1", "p2"):
        return None
    opponent_side = "p2" if player_side == "p1" else "p1"
    active_species = None
    turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    for turn in sorted(turns, key=lambda item: int(item.get("turn", 0) or 0)):
        events = turn.get("events") if isinstance(turn.get("events"), list) else []
        for event in events:
            if not isinstance(event, dict) or event.get("side") != opponent_side:
                continue
            if event.get("type") == "switch":
                active_species = _species_from_event_text(event.get("details") or event.get("actor"))
            elif event.get("type") in ("move", "tera", "damage", "heal", "status", "boost", "unboost"):
                active_species = _species_from_event_text(event.get("actor") or event.get("target")) or active_species
    return active_species


def infer_own_active_species(trajectory: Dict[str, Any], player_side: Optional[str]) -> Optional[str]:
    if player_side not in ("p1", "p2"):
        return None
    active_species = None
    turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    for turn in sorted(turns, key=lambda item: int(item.get("turn", 0) or 0)):
        events = turn.get("events") if isinstance(turn.get("events"), list) else []
        for event in events:
            if not isinstance(event, dict) or event.get("side") != player_side:
                continue
            if event.get("type") == "switch":
                active_species = _species_from_event_text(event.get("details") or event.get("actor"))
            elif event.get("type") in ("move", "tera", "damage", "heal", "status", "boost", "unboost"):
                active_species = _species_from_event_text(event.get("actor") or event.get("target")) or active_species
            elif event.get("type") == "faint":
                fainted = _species_from_event_text(event.get("target") or event.get("actor"))
                if fainted == active_species:
                    active_species = None
    return active_species


def _entropy_from_top_candidates(opponent: Dict[str, Any]) -> float:
    candidates = opponent.get("top_candidates") if isinstance(opponent.get("top_candidates"), list) else []
    probs = [float(c.get("prob", 0.0) or 0.0) for c in candidates if isinstance(c, dict) and float(c.get("prob", 0.0) or 0.0) > 0]
    if not probs:
        count = int(opponent.get("candidate_count", 0) or 0)
        return 1.0 if count > 1 else 0.0
    total = sum(probs)
    if total <= 0:
        return 0.0
    normalized = [p / total for p in probs]
    entropy = -sum(p * math.log(p) for p in normalized if p > 0)
    return _clip(entropy / math.log(max(2, len(normalized))))


def _union_count_from_top_candidates(opponent: Dict[str, Any], field: str) -> int:
    values = set()
    candidates = opponent.get("top_candidates") if isinstance(opponent.get("top_candidates"), list) else []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        raw = candidate.get(field)
        if isinstance(raw, list):
            values.update(str(item) for item in raw if str(item))
    return len(values)


def _inferred_count(opponent: Dict[str, Any], field: str) -> int:
    inferred = opponent.get("inferred") if isinstance(opponent.get("inferred"), dict) else {}
    values = inferred.get(field) if isinstance(inferred.get(field), list) else []
    return len(values)


def opponent_belief_feature_vector(
    opponent_belief: Optional[Dict[str, Any]],
    *,
    trajectory: Optional[Dict[str, Any]] = None,
    player_side: Optional[str] = None,
) -> np.ndarray:
    opponents = []
    if isinstance(opponent_belief, dict) and isinstance(opponent_belief.get("opponents"), list):
        opponents = [entry for entry in opponent_belief["opponents"] if isinstance(entry, dict)]

    active_species = infer_opponent_active_species(trajectory or {}, player_side)
    selected: Dict[str, Any] = {}
    if active_species:
        active_key = active_species.lower()
        for opponent in opponents:
            if str(opponent.get("species", "")).lower() == active_key:
                selected = opponent
                break
    if not selected and opponents:
        selected = opponents[-1]

    revealed = selected.get("revealed") if isinstance(selected.get("revealed"), dict) else {}
    revealed_moves = revealed.get("moves") if isinstance(revealed.get("moves"), list) else []
    candidate_count = int(selected.get("candidate_count", 0) or 0)
    fainted_count = sum(
        1
        for opponent in opponents
        if isinstance(opponent.get("revealed"), dict) and bool(opponent.get("revealed", {}).get("fainted"))
    )
    filter_relaxed = any(bool(opponent.get("filter_relaxed")) for opponent in opponents)

    values = [
        float(bool(active_species or selected.get("species"))),
        _safe_count_norm(len(revealed_moves), 4),
        _clip(math.log1p(max(0, candidate_count)) / math.log(101.0)),
        _entropy_from_top_candidates(selected),
        _safe_count_norm(_union_count_from_top_candidates(selected, "moves"), 24),
        _safe_count_norm(_inferred_count(selected, "abilities"), 6),
        _safe_count_norm(_inferred_count(selected, "tera_types"), 18),
        float(_known(revealed.get("item"))),
        float(_known(revealed.get("ability"))),
        float(_known(revealed.get("tera_type"))),
        _safe_count_norm(fainted_count, 6),
        _clip((6.0 - float(fainted_count)) / 6.0),
        float(filter_relaxed),
        _safe_count_norm(len(opponents), 6),
    ]
    return np.asarray(values, dtype=np.float32)


def public_feature_vector_from_trajectory(
    trajectory: Dict[str, Any],
    *,
    through_turn: Optional[int] = None,
    perspective_side: str = "p1",
) -> Tuple[np.ndarray, Dict[str, Any]]:
    state = _initial_state(trajectory)
    recent = _new_recent()
    latest_turn = 0
    turn_records = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    for turn_record in sorted(turn_records, key=lambda item: int(item.get("turn", 0) or 0)):
        turn_number = int(turn_record.get("turn", 0) or 0)
        if through_turn is not None and turn_number > through_turn:
            break
        latest_turn = turn_number
        recent = _new_recent()
        events = turn_record.get("events") if isinstance(turn_record.get("events"), list) else []
        for event in events:
            if isinstance(event, dict):
                _apply_event(state, recent, event)
    features = _feature_vector(state, recent, latest_turn)
    if perspective_side == "p2":
        features = mirror_public_features(features)
    elif perspective_side != "p1":
        raise ValueError(f"Unsupported perspective_side={perspective_side!r}; expected p1 or p2.")
    return features, {"latest_turn": latest_turn, "perspective_side": perspective_side}


def mirror_public_features(features: np.ndarray) -> np.ndarray:
    """Convert p1-oriented public replay features into p2-as-self features."""
    values = np.asarray(features, dtype=np.float32).copy()
    if values.shape[0] != len(PUBLIC_FEATURE_NAMES):
        raise ValueError(f"Expected {len(PUBLIC_FEATURE_NAMES)} public features, got {values.shape[0]}.")
    swap_pairs = [
        (1, 2),
        (4, 5),
        (7, 8),
        (10, 11),
        (13, 14),
        (16, 17),
        (19, 20),
        (22, 23),
        (25, 26),
    ]
    negate_indices = [3, 6, 9, 12, 15, 18, 21, 24, 27]
    for left, right in swap_pairs:
        values[left], values[right] = values[right], values[left]
    for index in negate_indices:
        values[index] = -values[index]
    return values


def trajectory_prefix(trajectory: Dict[str, Any], through_turn: int) -> Dict[str, Any]:
    prefixed = dict(trajectory)
    turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    prefixed["turns"] = [
        turn for turn in turns if isinstance(turn, dict) and int(turn.get("turn", 0) or 0) <= int(through_turn)
    ]
    prefixed["total_turns"] = int(through_turn)
    protocol_log = trajectory.get("protocol_log") if isinstance(trajectory.get("protocol_log"), list) else []
    prefixed["protocol_log"] = list(protocol_log)
    return prefixed


def build_live_private_feature_vector(
    *,
    public_features: np.ndarray,
    private_state: Optional[Dict[str, Any]] = None,
    opponent_belief: Optional[Dict[str, Any]] = None,
    trajectory: Optional[Dict[str, Any]] = None,
    player_side: Optional[str] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    public = np.asarray(public_features, dtype=np.float32).reshape(-1)
    if public.shape[0] != len(PUBLIC_FEATURE_NAMES):
        raise ValueError(f"Expected {len(PUBLIC_FEATURE_NAMES)} public features, got {public.shape[0]}.")
    private = private_state_feature_vector(private_state)
    opponent = opponent_belief_feature_vector(opponent_belief, trajectory=trajectory, player_side=player_side)
    features = np.concatenate([public, private, opponent]).astype(np.float32)
    if features.shape[0] != FEATURE_DIM:
        raise ValueError(f"Live-private feature size mismatch: got {features.shape[0]}, expected {FEATURE_DIM}.")
    debug = {
        "feature_version": FEATURE_VERSION,
        "feature_dim": FEATURE_DIM,
        "public_feature_version": PUBLIC_FEATURE_VERSION,
        "used_private_state": bool(isinstance(private_state, dict) and private_state.get("team")),
        "used_opponent_belief": bool(isinstance(opponent_belief, dict) and opponent_belief.get("opponents")),
    }
    return features, debug


def build_features_from_live_payload(
    *,
    log: Sequence[str],
    room_id: str,
    url: str,
    player: Optional[str],
    request_payload: Optional[Dict[str, Any]],
    legal_actions: Sequence[Dict[str, Any]],
    sets_path: Optional[str] = None,
) -> Tuple[np.ndarray, Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    trajectory = parse_protocol_log(
        log,
        replay_id=room_id,
        format_name="gen9randombattle",
        source_path=url,
        metadata={"source": "live_eval", "player": player or ""},
    )
    request_side = None
    if isinstance(request_payload, dict) and isinstance(request_payload.get("side"), dict):
        side_id = request_payload["side"].get("id") or request_payload["side"].get("sideid") or request_payload["side"].get("side")
        if side_id in ("p1", "p2"):
            request_side = str(side_id)
    hinted_side = request_side or (player if player in ("p1", "p2") else None)
    private_state = extract_private_side_state(
        request_payload=request_payload,
        legal_actions=list(legal_actions),
        player_hint=player,
        active_species_hint=infer_own_active_species(trajectory, hinted_side),
        sets_path=sets_path,
    )
    player_side = private_state.get("player_side") if private_state.get("player_side") in ("p1", "p2") else player
    public_features, public_debug = public_feature_vector_from_trajectory(
        trajectory,
        perspective_side=player_side if player_side in ("p1", "p2") else "p1",
    )
    opponent_belief = build_opponent_beliefs(
        protocol_log=list(log),
        trajectory=trajectory,
        player_side=player_side if player_side in ("p1", "p2") else None,
        sets_path=sets_path,
    )
    features, debug = build_live_private_feature_vector(
        public_features=public_features,
        private_state=private_state,
        opponent_belief=opponent_belief,
        trajectory=trajectory,
        player_side=player_side if player_side in ("p1", "p2") else None,
    )
    debug.update(public_debug)
    debug["feature_names_preview"] = FEATURE_NAMES[:8]
    debug["feature_values_preview"] = [float(v) for v in features[:8].tolist()]
    return features, debug, private_state, opponent_belief, trajectory


def feature_schema() -> Dict[str, Any]:
    return {
        "feature_version": FEATURE_VERSION,
        "feature_dim": FEATURE_DIM,
        "feature_names": FEATURE_NAMES,
        "public_feature_version": PUBLIC_FEATURE_VERSION,
        "public_feature_dim": len(PUBLIC_FEATURE_NAMES),
    }
