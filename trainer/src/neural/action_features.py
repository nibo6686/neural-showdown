import hashlib
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .tactical_state import TACTICAL_ACTION_FEATURE_NAMES, tactical_action_feature_vector


MOVE_TYPES = [
    "Normal",
    "Fire",
    "Water",
    "Electric",
    "Grass",
    "Ice",
    "Fighting",
    "Poison",
    "Ground",
    "Flying",
    "Psychic",
    "Bug",
    "Rock",
    "Ghost",
    "Dragon",
    "Dark",
    "Steel",
    "Fairy",
]
CATEGORIES = ["Physical", "Special", "Status"]
ACTION_FEATURE_VERSION_V1 = "legal-action-v1"
ACTION_FEATURE_VERSION = "legal-action-v3"

BASE_FEATURE_NAMES = [
    "kind_move",
    "kind_switch",
    "action_index_norm",
    "move_slot_norm",
    "switch_slot_norm",
    "name_hash_sin",
    "name_hash_cos",
]
MOVE_TYPE_FEATURE_NAMES = [f"move_type_{name.lower()}" for name in MOVE_TYPES]
CATEGORY_FEATURE_NAMES = [f"move_category_{name.lower()}" for name in CATEGORIES]
MOVE_NUMERIC_FEATURE_NAMES = [
    "base_power_norm",
    "accuracy_norm",
    "priority_norm",
    "pp_fraction",
    "disabled",
    "target_self",
    "target_adjacent",
    "target_foe",
    "target_all",
    "flag_status",
    "flag_setup",
    "flag_recovery",
    "flag_pivot",
    "flag_hazard",
    "flag_protect_like",
    "appears_in_request_moves",
    "appears_only_from_randbats",
]
SWITCH_FEATURE_NAMES = [
    "target_hp_fraction",
    "target_fainted",
    "target_has_status",
    "target_item_known",
    "target_ability_known",
    "target_tera_known",
    "target_known_move_count_norm",
    "target_known_from_request",
    "target_inferred",
    "current_active_hp_fraction",
    "current_active_low_hp",
]
TERA_FEATURE_NAMES = [
    "is_tera_action",
    "can_tera",
    "tera_already_used",
    *[f"tera_type_{name.lower()}" for name in MOVE_TYPES],
    *[f"move_type_before_tera_{name.lower()}" for name in MOVE_TYPES],
    *[f"move_type_after_tera_{name.lower()}" for name in MOVE_TYPES],
    "tera_stab_bonus",
    "tera_defensive_type_change",
    "tera_matches_move_type",
    "tera_blast_type_change",
]
ACTION_FEATURE_NAMES_V1 = (
    BASE_FEATURE_NAMES + MOVE_TYPE_FEATURE_NAMES + CATEGORY_FEATURE_NAMES + MOVE_NUMERIC_FEATURE_NAMES + SWITCH_FEATURE_NAMES + TERA_FEATURE_NAMES
)
ACTION_FEATURE_DIM_V1 = len(ACTION_FEATURE_NAMES_V1)
ACTION_FEATURE_NAMES = ACTION_FEATURE_NAMES_V1 + TACTICAL_ACTION_FEATURE_NAMES
ACTION_FEATURE_DIM = len(ACTION_FEATURE_NAMES)


def to_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _move_data_candidates() -> List[Path]:
    root = _repo_root()
    return [
        root / "sim-core" / "node_modules" / "pokemon-showdown" / "data" / "moves.ts",
        root / "pokemon-showdown" / "data" / "moves.ts",
        Path("sim-core/node_modules/pokemon-showdown/data/moves.ts"),
    ]


def _extract_object_block(text: str, start: int) -> Tuple[str, int]:
    depth = 0
    block_start = None
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
            if block_start is None:
                block_start = index
        elif char == "}":
            depth -= 1
            if block_start is not None and depth == 0:
                return text[block_start : index + 1], index + 1
    return "", start + 1


def _field_string(block: str, field: str) -> Optional[str]:
    match = re.search(rf"\b{re.escape(field)}\s*:\s*\"([^\"]+)\"", block)
    return match.group(1) if match else None


def _field_number(block: str, field: str) -> Optional[float]:
    match = re.search(rf"\b{re.escape(field)}\s*:\s*(-?\d+(?:\.\d+)?)", block)
    return float(match.group(1)) if match else None


def _field_accuracy(block: str) -> Optional[float]:
    if re.search(r"\baccuracy\s*:\s*true", block):
        return 100.0
    return _field_number(block, "accuracy")


def _field_flags(block: str) -> List[str]:
    match = re.search(r"\bflags\s*:\s*\{([^}]*)\}", block, re.DOTALL)
    if not match:
        return []
    return sorted(set(re.findall(r"([a-zA-Z0-9_]+)\s*:", match.group(1))))


def _parse_moves_ts(path: Path) -> Dict[str, Dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    moves: Dict[str, Dict[str, Any]] = {}
    pattern = re.compile(r"\n\s*([a-z0-9]+)\s*:\s*\{")
    position = 0
    while True:
        match = pattern.search(text, position)
        if not match:
            break
        move_id = match.group(1)
        block, position = _extract_object_block(text, match.end() - 1)
        if not block:
            continue
        moves[move_id] = {
            "id": move_id,
            "name": _field_string(block, "name") or move_id,
            "type": _field_string(block, "type"),
            "category": _field_string(block, "category"),
            "base_power": _field_number(block, "basePower") or 0.0,
            "accuracy": _field_accuracy(block),
            "priority": _field_number(block, "priority") or 0.0,
            "target": _field_string(block, "target"),
            "flags": _field_flags(block),
            "has_boosts": bool(re.search(r"\bboosts\s*:", block)),
            "has_heal": bool(re.search(r"\bheal\s*:", block)),
            "has_drain": bool(re.search(r"\bdrain\s*:", block)),
            "has_self_switch": bool(re.search(r"\bselfSwitch\s*:", block)),
            "has_side_condition": bool(re.search(r"\bsideCondition\s*:", block)),
        }
    return moves


@lru_cache(maxsize=1)
def load_move_metadata() -> Tuple[Dict[str, Dict[str, Any]], str]:
    for path in _move_data_candidates():
        if path.exists():
            return _parse_moves_ts(path), str(path)
    return {}, "missing"


def _hash_pair(name: str) -> Tuple[float, float]:
    digest = hashlib.sha1(to_id(name).encode("utf-8")).digest()
    raw = int.from_bytes(digest[:4], "little") / float(2**32)
    angle = raw * math.tau
    return math.sin(angle), math.cos(angle)


def _clip(value: Any, low: float = 0.0, high: float = 1.0, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(low, min(high, number))


def _action_name(action: Dict[str, Any]) -> str:
    label = str(action.get("label") or action.get("move") or action.get("name") or "")
    if ":" in label:
        label = label.split(":", 1)[1]
    return label.strip()


def _active_moves(private_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    moves = private_state.get("active_moves") if isinstance(private_state.get("active_moves"), list) else []
    return [move for move in moves if isinstance(move, dict)]


def _find_move_record(action: Dict[str, Any], private_state: Dict[str, Any]) -> Dict[str, Any]:
    action_index = int(action.get("index", -1) if action.get("index") is not None else -1)
    action_name = to_id(_action_name(action))
    action_slot = int(action.get("slot", 0) or 0)
    moves = _active_moves(private_state)
    if action_slot > 0 and 0 <= action_slot - 1 < len(moves):
        return moves[action_slot - 1]
    if 0 <= action_index < len(moves):
        return moves[action_index]
    for move in moves:
        if to_id(move.get("name") or move.get("move") or move.get("id")) == action_name:
            return move
    return {}


def _active_team_member(private_state: Dict[str, Any]) -> Dict[str, Any]:
    team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
    for mon in team:
        if isinstance(mon, dict) and mon.get("active"):
            return mon
    return team[0] if team and isinstance(team[0], dict) else {}


def _find_switch_target(action: Dict[str, Any], private_state: Dict[str, Any]) -> Dict[str, Any]:
    target = to_id(_action_name(action))
    team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
    for mon in team:
        if isinstance(mon, dict) and to_id(mon.get("species") or mon.get("details") or mon.get("ident")) == target:
            return mon
    return {}


def _hp_fraction(mon: Dict[str, Any]) -> float:
    if mon.get("hp_fraction") is not None:
        return _clip(mon.get("hp_fraction"))
    if mon.get("fainted"):
        return 0.0
    return 1.0 if mon else 0.0


def _move_flag_features(meta: Dict[str, Any], move_name: str) -> Dict[str, float]:
    flags = set(meta.get("flags", []))
    move_id = to_id(move_name)
    is_status = str(meta.get("category") or "").lower() == "status"
    return {
        "flag_status": float(is_status),
        "flag_setup": float(bool(meta.get("has_boosts"))),
        "flag_recovery": float(bool(meta.get("has_heal") or meta.get("has_drain") or "heal" in flags)),
        "flag_pivot": float(bool(meta.get("has_self_switch") or move_id in {"uturn", "flipturn", "voltswitch", "partingshot", "chillyreception", "teleport"})),
        "flag_hazard": float(bool(meta.get("has_side_condition") or move_id in {"spikes", "toxicspikes", "stealthrock", "stickyweb"})),
        "flag_protect_like": float(move_id in {"protect", "detect", "spikyshield", "kingsshield", "banefulbunker", "silktrap", "burningbulwark"}),
    }


def _active_species_types(active: Dict[str, Any]) -> List[str]:
    types = active.get("types") if isinstance(active.get("types"), list) else []
    if types:
        return [str(value) for value in types if str(value)]
    try:
        from .tactical_state import _species_types

        return _species_types(active.get("species") or active.get("details") or "")
    except Exception:
        return []


def _private_can_tera(private_state: Dict[str, Any], active: Dict[str, Any], moves: Sequence[Dict[str, Any]]) -> bool:
    if private_state.get("tera_used"):
        return False
    if private_state.get("force_switch"):
        return False
    if private_state.get("can_tera"):
        return True
    if active.get("can_tera") or active.get("canTerastallize"):
        return True
    return any(bool(move.get("can_tera") or move.get("canTerastallize")) for move in moves if isinstance(move, dict))


def _tera_type(private_state: Dict[str, Any], active: Dict[str, Any], action: Dict[str, Any]) -> Optional[str]:
    return (
        action.get("tera_type")
        or private_state.get("active_tera_type")
        or active.get("tera_type")
        or active.get("teraType")
    )


def _tera_feature_values(
    *,
    action: Dict[str, Any],
    private_state: Dict[str, Any],
    active: Dict[str, Any],
    move_id: str,
    move_type: str,
) -> List[float]:
    kind = str(action.get("kind") or "").lower()
    is_tera = kind == "move_tera" or bool(action.get("is_tera_action")) or "terastallize" in str(action.get("choice") or "").lower()
    active_moves = _active_moves(private_state)
    can_tera = _private_can_tera(private_state, active, active_moves)
    tera_type = str(_tera_type(private_state, active, action) or "")
    before_type = str(move_type or "")
    after_type = tera_type if move_id == "terablast" and tera_type else before_type
    own_types = _active_species_types(active)
    defensive_change = bool(is_tera and tera_type and set(own_types or []) != {tera_type})
    tera_matches_move = bool(is_tera and tera_type and before_type and tera_type.lower() == before_type.lower())
    tera_stab_bonus = bool(is_tera and before_type and (tera_matches_move or before_type in own_types))
    tera_blast_change = bool(is_tera and move_id == "terablast" and tera_type and after_type.lower() != before_type.lower())
    return [
        float(is_tera),
        float(can_tera),
        float(bool(private_state.get("tera_used"))),
        *(float(tera_type.lower() == type_name.lower()) for type_name in MOVE_TYPES),
        *(float(before_type.lower() == type_name.lower()) for type_name in MOVE_TYPES),
        *(float(after_type.lower() == type_name.lower()) for type_name in MOVE_TYPES),
        float(tera_stab_bonus),
        float(defensive_change),
        float(tera_matches_move),
        float(tera_blast_change),
    ]


def _target_features(target: Optional[str]) -> List[float]:
    text = str(target or "").lower()
    return [
        float(text in {"self", "adjacentally", "allyside"}),
        float("adjacent" in text),
        float("foe" in text or text == "normal" or text == "any"),
        float("all" in text),
    ]


def build_action_feature_vector(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    private = private_state if isinstance(private_state, dict) else {}
    tactical = tactical_state if isinstance(tactical_state, dict) else private.get("tactical_state", {})
    kind = str(action.get("kind") or "").lower()
    action_index = int(action.get("index", 0) or 0)
    name = _action_name(action)
    name_sin, name_cos = _hash_pair(name)
    values: List[float] = [
        float(kind.startswith("move")),
        float(kind == "switch"),
        _clip(action_index / 12.0),
        _clip((int(action.get("slot", 0) or 0) - 1) / 3.0) if kind.startswith("move") and int(action.get("slot", 0) or 0) > 0 else _clip(action_index / 3.0) if kind.startswith("move") else 0.0,
        _clip((action_index - 8) / 4.0) if kind == "switch" else 0.0,
        name_sin,
        name_cos,
    ]

    meta_index, _ = load_move_metadata()
    move_record = _find_move_record(action, private) if kind.startswith("move") else {}
    move_id = to_id(move_record.get("id") or move_record.get("name") or name)
    meta = meta_index.get(move_id, {}) if kind.startswith("move") else {}
    move_type = str(meta.get("type") or "").lower()
    category = str(meta.get("category") or "").lower()
    values.extend(float(move_type == type_name.lower()) for type_name in MOVE_TYPES)
    values.extend(float(category == category_name.lower()) for category_name in CATEGORIES)

    pp = move_record.get("pp")
    maxpp = move_record.get("maxpp")
    if isinstance(pp, (int, float)) and isinstance(maxpp, (int, float)) and float(maxpp) > 0:
        pp_fraction = _clip(float(pp) / float(maxpp))
    elif move_record:
        pp_fraction = 1.0
    else:
        pp_fraction = 0.0
    flags = _move_flag_features(meta, name) if kind == "move" else {
        "flag_status": 0.0,
        "flag_setup": 0.0,
        "flag_recovery": 0.0,
        "flag_pivot": 0.0,
        "flag_hazard": 0.0,
        "flag_protect_like": 0.0,
    }
    known_from_request = bool(move_record.get("known_from_request") or move_record.get("source") == "request")
    inferred = bool(move_record.get("inferred") or move_record.get("source") == "randbats")
    values.extend(
        [
            _clip(float(meta.get("base_power", 0.0) or 0.0) / 250.0),
            _clip(float(meta.get("accuracy", 100.0) or 100.0) / 100.0),
            _clip((float(meta.get("priority", 0.0) or 0.0) + 7.0) / 14.0),
            pp_fraction if kind.startswith("move") else 0.0,
            float(bool(action.get("disabled"))),
            *_target_features(meta.get("target")),
            flags["flag_status"],
            flags["flag_setup"],
            flags["flag_recovery"],
            flags["flag_pivot"],
            flags["flag_hazard"],
            flags["flag_protect_like"],
            float(kind.startswith("move") and known_from_request),
            float(kind.startswith("move") and inferred and not known_from_request),
        ]
    )

    active = _active_team_member(private)
    target_mon = _find_switch_target(action, private) if kind == "switch" else {}
    target_moves = target_mon.get("moves") if isinstance(target_mon.get("moves"), list) else []
    values.extend(
        [
            _hp_fraction(target_mon) if kind == "switch" else 0.0,
            float(kind == "switch" and bool(target_mon.get("fainted"))),
            float(kind == "switch" and bool(target_mon.get("status"))),
            float(kind == "switch" and bool(target_mon.get("item"))),
            float(kind == "switch" and bool(target_mon.get("ability") or target_mon.get("base_ability"))),
            float(kind == "switch" and bool(target_mon.get("tera_type"))),
            _clip(len(target_moves) / 4.0) if kind == "switch" else 0.0,
            float(kind == "switch" and bool(target_mon.get("known_from_request", True)) and not target_mon.get("inferred")),
            float(kind == "switch" and bool(target_mon.get("inferred") or target_mon.get("inferred_from_randbats"))),
            _hp_fraction(active),
            float(_hp_fraction(active) <= 0.33) if active else 0.0,
        ]
    )
    values.extend(
        _tera_feature_values(
            action=action,
            private_state=private,
            active=active,
            move_id=move_id,
            move_type=str(meta.get("type") or "") if meta else "",
        )
    )
    base_features = np.asarray(values, dtype=np.float32)
    if base_features.shape[0] != ACTION_FEATURE_DIM_V1:
        raise ValueError(f"Action v1 feature size mismatch: got {base_features.shape[0]}, expected {ACTION_FEATURE_DIM_V1}.")
    tactical_features = tactical_action_feature_vector(
        action,
        private_state=private,
        tactical_state=tactical,
        move_id=move_id,
        move_type=str(meta.get("type") or "") if meta else None,
    )
    features = np.concatenate([base_features, tactical_features]).astype(np.float32)
    if features.shape[0] != ACTION_FEATURE_DIM:
        raise ValueError(f"Action feature size mismatch: got {features.shape[0]}, expected {ACTION_FEATURE_DIM}.")
    return features


def feature_schema() -> Dict[str, Any]:
    _, source = load_move_metadata()
    return {
        "feature_version": ACTION_FEATURE_VERSION,
        "feature_dim": ACTION_FEATURE_DIM,
        "feature_names": ACTION_FEATURE_NAMES,
        "v1_feature_version": ACTION_FEATURE_VERSION_V1,
        "v1_feature_dim": ACTION_FEATURE_DIM_V1,
        "v1_feature_names": ACTION_FEATURE_NAMES_V1,
        "tactical_feature_dim": len(TACTICAL_ACTION_FEATURE_NAMES),
        "tactical_feature_names": TACTICAL_ACTION_FEATURE_NAMES,
        "move_metadata_source": source,
    }
