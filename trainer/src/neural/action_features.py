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
ACTION_FEATURE_VERSION_V4 = "legal-action-v4"

ACTION_STATS = ["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"]

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

# --- legal-action-v4: explicit move side-effects / stat deltas (diagnostic) ---
SLICE5_ACTION_FEATURE_NAMES = (
    [f"self_stat_delta_{stat}" for stat in ACTION_STATS]
    + [f"opponent_stat_delta_{stat}" for stat in ACTION_STATS]
    + ["self_has_stat_drop", "self_has_stat_boost", "opponent_has_stat_drop"]
    + [
        "effect_recoil",
        "effect_drain_or_heal",
        "effect_recharge",
        "effect_locks_user",
        "effect_switch_move",
        "effect_has_drawback",
        "effect_priority_norm",
    ]
    + [
        "class_damage",
        "class_status",
        "class_setup",
        "class_recovery",
        "class_hazard",
        "class_pivot",
        "class_protect",
    ]
    + ["cmd_move", "cmd_switch", "cmd_tera_move", "cmd_forced_switch"]
    + ["lock_disabled", "lock_encore_compatible", "lock_choice_compatible"]
    + ["switch_target_known", "switch_target_slot_norm"]
    + [
        f"switch_target_species_hash_{family}_bucket_{bucket:02d}"
        for family in ("a", "b")
        for bucket in range(32)
    ]
)
ACTION_FEATURE_NAMES_V4 = ACTION_FEATURE_NAMES + SLICE5_ACTION_FEATURE_NAMES
ACTION_FEATURE_DIM_V4 = len(ACTION_FEATURE_NAMES_V4)

# --- legal-action-v5: resolved immediate impact / next-state diagnostics ---
ACTION_FEATURE_VERSION_V5 = "legal-action-v5"
IMPACT_METHODS = ["unavailable", "non_damaging", "approximate", "belief_fallback", "smogon_calc"]
NEXT_STATE_SOURCES = ["unavailable", "immediate_estimate", "branch"]
# Structural hazard-removal move ids (representation only, mirrors existing id sets).
REMOVAL_MOVE_IDS = {"rapidspin", "defog", "mortalspin", "tidyup", "courtchange"}

SLICE6_ACTION_FEATURE_NAMES = (
    [
        "impact_expected_damage_fraction",
        "impact_min_damage_fraction",
        "impact_max_damage_fraction",
        "impact_damage_uncertainty",
        "impact_ko_chance",
        "impact_two_hko_proxy",
        "impact_hit_chance",
        "impact_accuracy_known",
        "impact_immune",
        "impact_resisted",
        "impact_super_effective",
        "impact_type_effectiveness_norm",
        "impact_stab",
        "impact_stab_known",
        "impact_damage_includes_crit",
    ]
    + [f"impact_method_{method}" for method in IMPACT_METHODS]
    + [
        "impact_vs_current_type",
        "impact_used_tera",
        "impact_used_stat_stages",
        "impact_used_item_ability",
        "impact_used_field",
        "impact_used_exact_attacker_stats",
        "impact_used_exact_defender_stats",
        "impact_target_known",
        "impact_target_inferred",
        "action_non_damaging",
        "action_is_removal",
        "impact_unknown",
    ]
    + ["next_state_delta_available"]
    + [f"next_state_source_{source}" for source in NEXT_STATE_SOURCES]
    + [
        "next_opp_hp_delta",
        "next_own_hp_delta",
        "next_own_hp_delta_known",
        "next_own_stat_change",
        "next_opp_stat_change",
        "next_own_status_change",
        "next_opp_status_change",
        "next_field_or_side_change",
        "next_forced_switch_or_pivot",
        "terminal_flags_from_branch",
        "terminal_ko_applied",
        "terminal_win",
        "terminal_loss",
    ]
)
ACTION_FEATURE_NAMES_V5 = ACTION_FEATURE_NAMES_V4 + SLICE6_ACTION_FEATURE_NAMES
ACTION_FEATURE_DIM_V5 = len(ACTION_FEATURE_NAMES_V5)


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


def action_name(action: Dict[str, Any]) -> str:
    return _action_name(action)


def classify_action_category(action: Dict[str, Any]) -> str:
    kind = str(action.get("kind") or "").lower()
    label = str(action.get("label") or "")
    if not kind and label.lower().startswith("switch:"):
        kind = "switch"
    elif not kind and label.lower().startswith(("move:", "move_tera:")):
        kind = "move_tera" if label.lower().startswith("move_tera:") else "move"
    if kind == "switch":
        return "switch"

    name = _action_name(action)
    move_id = to_id(name)
    metadata, _ = load_move_metadata()
    meta = metadata.get(move_id, {}) if move_id else {}
    category = str(meta.get("category") or "").lower()
    base_power = float(meta.get("base_power", 0.0) or 0.0)
    flags = set(meta.get("flags", []))
    is_tera = kind == "move_tera"

    if kind not in {"move", "move_tera"}:
        return "unknown"
    if not move_id:
        return "unknown"
    if category == "status":
        if is_tera:
            return "tera_status"
        if move_id in {"protect", "detect", "spikyshield", "kingsshield", "banefulbunker", "silktrap", "burningbulwark"}:
            return "protect"
        if bool(meta.get("has_heal") or meta.get("has_drain") or "heal" in flags) or move_id in {"recover", "roost", "synthesis", "slackoff", "softboiled", "rest", "milkdrink", "shoreup", "wish"}:
            return "recovery"
        if bool(meta.get("has_side_condition")) or move_id in {"spikes", "toxicspikes", "stealthrock", "stickyweb"}:
            return "hazard"
        if bool(meta.get("has_boosts")) or move_id in {"swordsdance", "nastyplot", "calmmind", "bulkup", "dragondance", "quiverdance", "shellsmash", "irondefense", "amnesia", "agility"}:
            return "setup"
        return "status"
    if base_power > 0:
        return "tera_damage" if is_tera else "damage"
    return "unknown"


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


def _species_hash_buckets(name: Any) -> List[float]:
    """64-dim two-family bucket hash for a switch-target species (diagnostic)."""
    identity = to_id(name)
    values = [0.0] * 64
    if not identity:
        return values
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    values[int.from_bytes(digest[0:4], "little") % 32] = 1.0
    values[32 + (int.from_bytes(digest[4:8], "little") % 32)] = 1.0
    return values


def _signed_stat(value: Any) -> float:
    try:
        return max(-1.0, min(1.0, float(value) / 2.0))
    except (TypeError, ValueError):
        return 0.0


def slice5_action_feature_vector(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v4 add-on: explicit move side-effects, per-stat deltas, command
    identity, lock compatibility, and switch-target identity. Diagnostic only."""
    from .action_side_effects import move_side_effects, move_stat_deltas

    private = private_state if isinstance(private_state, dict) else {}
    kind = str(action.get("kind") or "").lower()
    is_switch = kind == "switch"
    is_tera = kind == "move_tera" or bool(action.get("is_tera_action"))
    is_move = kind.startswith("move")
    name = _action_name(action)

    se = move_side_effects(name) if is_move else {}
    deltas = move_stat_deltas(name) if is_move else {"self": {}, "target": {}}
    self_delta = deltas.get("self", {})
    target_delta = deltas.get("target", {})
    category = classify_action_category(action)
    disabled = bool(action.get("disabled"))

    values: List[float] = []
    values.extend(_signed_stat(self_delta.get(stat, 0)) for stat in ACTION_STATS)
    values.extend(_signed_stat(target_delta.get(stat, 0)) for stat in ACTION_STATS)
    values.extend(
        [
            float(any(v < 0 for v in self_delta.values())),
            float(any(v > 0 for v in self_delta.values())),
            float(any(v < 0 for v in target_delta.values())),
        ]
    )
    values.extend(
        [
            float(bool(se.get("recoil"))),
            float(bool(se.get("heals_user"))),
            float(bool(se.get("recharge"))),
            float(bool(se.get("locks_user"))),
            float(bool(se.get("switch_move"))),
            float(bool(se.get("has_drawback"))),
            _clip((float(se.get("priority", 0) or 0) + 7.0) / 14.0) if is_move else 0.0,
        ]
    )
    values.extend(
        [
            float(category in {"damage", "tera_damage"}),
            float(category in {"status", "tera_status"}),
            float(category == "setup"),
            float(category == "recovery"),
            float(category == "hazard"),
            float(bool(se.get("switch_move")) and not is_switch),
            float(category == "protect"),
        ]
    )
    forced_switch = bool(private.get("force_switch"))
    values.extend(
        [
            float(is_move and not is_tera),
            float(is_switch and not forced_switch),
            float(is_tera),
            float(is_switch and forced_switch),
        ]
    )
    values.extend(
        [
            float(disabled),
            float(is_move and not disabled),
            float(is_move and not disabled),
        ]
    )
    target_mon = _find_switch_target(action, private) if is_switch else {}
    values.extend(
        [
            float(is_switch and bool(target_mon.get("species"))),
            _clip((int(action.get("index", 0) or 0) - 8) / 4.0) if is_switch else 0.0,
        ]
    )
    values.extend(_species_hash_buckets(target_mon.get("species")) if is_switch else [0.0] * 64)

    vector = np.asarray(values, dtype=np.float32)
    if vector.shape[0] != len(SLICE5_ACTION_FEATURE_NAMES):
        raise ValueError(
            f"Action v4 slice-5 size mismatch: got {vector.shape[0]}, "
            f"expected {len(SLICE5_ACTION_FEATURE_NAMES)}."
        )
    return vector


def build_action_feature_vector_v4(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v4 = legal-action-v3 (unchanged prefix) + Slice-5 side-effects."""
    base = build_action_feature_vector(action, private_state, tactical_state)
    slice5 = slice5_action_feature_vector(action, private_state)
    features = np.concatenate([base, slice5]).astype(np.float32)
    if features.shape[0] != ACTION_FEATURE_DIM_V4:
        raise ValueError(f"Action v4 feature size mismatch: got {features.shape[0]}, expected {ACTION_FEATURE_DIM_V4}.")
    return features


def _impact_get(impact: Optional[Dict[str, Any]], key: str, default: Any = 0.0) -> Any:
    if isinstance(impact, dict) and key in impact and impact[key] is not None:
        return impact[key]
    return default


def slice6_resolved_impact_feature_vector(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
    impact: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v5 add-on: resolved immediate impact + next-state diagnostics.

    ``impact`` is the optional normalized dict from
    ``resolved_action_impact.resolve_action_impact``. When it is missing for a
    damaging move, the resolved fields are present but flagged unavailable
    (``impact_unknown=1``, ``impact_method_unavailable=1``). Action-intrinsic
    classification (non-damaging, removal, stat/field change) is derived from the
    move itself and stays valid even without a resolved impact.
    """
    from .action_side_effects import move_side_effects, move_stat_deltas

    kind = str(action.get("kind") or "").lower()
    is_switch = kind == "switch"
    is_move = kind.startswith("move")
    name = _action_name(action)
    category = classify_action_category(action)
    meta_index, _ = load_move_metadata()
    meta = meta_index.get(to_id(name), {}) if is_move else {}
    se = move_side_effects(name) if is_move else {}
    deltas = move_stat_deltas(name) if is_move else {"self": {}, "target": {}}

    damaging = is_move and category in {"damage", "tera_damage"}
    non_damaging = not damaging
    removal = bool(is_move and to_id(name) in REMOVAL_MOVE_IDS)

    imp = impact if isinstance(impact, dict) else None
    available = bool(imp and imp.get("available"))
    if imp and imp.get("method"):
        method = str(imp.get("method"))
    elif is_switch:
        method = "unavailable"
    elif non_damaging:
        method = "non_damaging"
    else:
        method = "unavailable"
    if method not in IMPACT_METHODS:
        method = "unavailable"
    impact_unknown = float(damaging and not available)

    type_eff = float(_impact_get(imp, "type_effectiveness", 1.0))
    values: List[float] = [
        _clip(_impact_get(imp, "expected_fraction")),
        _clip(_impact_get(imp, "min_fraction")),
        _clip(_impact_get(imp, "max_fraction")),
        _clip(_impact_get(imp, "max_fraction") - _impact_get(imp, "min_fraction")),
        _clip(_impact_get(imp, "ko_chance")),
        float(bool(_impact_get(imp, "two_hko_proxy"))),
        _clip(_impact_get(imp, "hit_chance")),
        float(bool(_impact_get(imp, "accuracy_known"))),
        float(bool(_impact_get(imp, "immune"))),
        float(bool(_impact_get(imp, "resisted"))),
        float(bool(_impact_get(imp, "super_effective"))),
        _clip(type_eff / 4.0),
        float(bool(_impact_get(imp, "stab"))),
        float(bool(_impact_get(imp, "stab_known"))),
        float(bool(_impact_get(imp, "crit_included"))),
    ]
    values.extend(float(method == candidate) for candidate in IMPACT_METHODS)
    values.extend(
        [
            float(bool(_impact_get(imp, "vs_current_type"))),
            float(bool(_impact_get(imp, "used_tera"))),
            float(bool(_impact_get(imp, "used_stat_stages"))),
            float(bool(_impact_get(imp, "used_item_ability"))),
            float(bool(_impact_get(imp, "used_field"))),
            float(bool(_impact_get(imp, "used_exact_attacker_stats"))),
            float(bool(_impact_get(imp, "used_exact_defender_stats"))),
            float(bool(_impact_get(imp, "target_known"))),
            float(bool(_impact_get(imp, "target_inferred"))),
            float(non_damaging),
            float(removal),
            impact_unknown,
        ]
    )

    source = str(_impact_get(imp, "next_state_source", "unavailable"))
    if source not in NEXT_STATE_SOURCES:
        source = "unavailable"
    values.append(float(source != "unavailable"))
    values.extend(float(source == candidate) for candidate in NEXT_STATE_SOURCES)
    field_change = bool(
        is_move and (category == "hazard" or removal or meta.get("has_side_condition"))
    )
    values.extend(
        [
            max(-1.0, min(1.0, float(_impact_get(imp, "next_opp_hp_delta")))),
            max(-1.0, min(1.0, float(_impact_get(imp, "next_own_hp_delta")))),
            float(bool(_impact_get(imp, "next_own_hp_delta_known"))),
            float(bool(deltas.get("self"))),
            float(bool(deltas.get("target"))),
            float(bool(_impact_get(imp, "next_own_status_change"))),
            float(bool(_impact_get(imp, "next_opp_status_change"))),
            float(field_change),
            float(bool(se.get("switch_move")) or is_switch),
            float(bool(_impact_get(imp, "terminal_from_branch"))),
            float(bool(_impact_get(imp, "terminal_ko"))),
            float(bool(_impact_get(imp, "terminal_win"))),
            float(bool(_impact_get(imp, "terminal_loss"))),
        ]
    )

    vector = np.asarray(values, dtype=np.float32)
    if vector.shape[0] != len(SLICE6_ACTION_FEATURE_NAMES):
        raise ValueError(
            f"Action v5 slice-6 size mismatch: got {vector.shape[0]}, "
            f"expected {len(SLICE6_ACTION_FEATURE_NAMES)}."
        )
    return vector


def build_action_feature_vector_v5(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
    impact: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v5 = legal-action-v4 (unchanged prefix) + Slice-6 resolved impact.

    ``impact`` is optional and diagnostic-only; when omitted, resolved fields carry
    explicit unavailable flags. Damage estimation is never triggered here.
    """
    base = build_action_feature_vector_v4(action, private_state, tactical_state)
    slice6 = slice6_resolved_impact_feature_vector(action, private_state, impact)
    features = np.concatenate([base, slice6]).astype(np.float32)
    if features.shape[0] != ACTION_FEATURE_DIM_V5:
        raise ValueError(f"Action v5 feature size mismatch: got {features.shape[0]}, expected {ACTION_FEATURE_DIM_V5}.")
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
        "v4_feature_version": ACTION_FEATURE_VERSION_V4,
        "v4_feature_dim": ACTION_FEATURE_DIM_V4,
        "v4_feature_names": ACTION_FEATURE_NAMES_V4,
        "v4_slice5_feature_names": SLICE5_ACTION_FEATURE_NAMES,
        "v5_feature_version": ACTION_FEATURE_VERSION_V5,
        "v5_feature_dim": ACTION_FEATURE_DIM_V5,
        "v5_feature_names": ACTION_FEATURE_NAMES_V5,
        "v5_slice6_feature_names": SLICE6_ACTION_FEATURE_NAMES,
        "tactical_feature_dim": len(TACTICAL_ACTION_FEATURE_NAMES),
        "tactical_feature_names": TACTICAL_ACTION_FEATURE_NAMES,
        "move_metadata_source": source,
    }
