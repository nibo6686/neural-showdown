import hashlib
import math
import re
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
from .tactical_state import (
    TACTICAL_STATE_FEATURE_NAMES,
    TACTICAL_FEATURE_VERSION,
    build_tactical_state,
    snapshot_with_private_state,
    tactical_state_feature_vector,
)


FEATURE_VERSION_V1 = "live-private-belief-v1"
FEATURE_VERSION = "live-private-belief-v2"
FEATURE_VERSION_V3 = "live-private-belief-v3"
FEATURE_VERSION_V4 = "live-private-belief-v4"
FEATURE_VERSION_V5 = "live-private-belief-v5"
FEATURE_VERSION_V6 = "live-private-belief-v6"
FEATURE_VERSION_V7 = "live-private-belief-v7"

V3_TYPES = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting",
    "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost",
    "Dragon", "Dark", "Steel", "Fairy",
]
V3_STAGE_STATS = ["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"]
V3_CURRENT_TYPE_SOURCES = ["unknown", "species", "request", "protocol_typechange", "protocol_tera"]
V3_BASE_TYPE_SOURCES = ["unknown", "species", "request"]
V4_IDENTITY_BUCKETS = 32
V4_ITEM_STATES = ["unknown", "held", "none", "removed", "consumed"]
V4_ABILITY_STATES = ["unknown", "known", "changed", "none", "suppressed"]
V4_STATE_SOURCES = ["unknown", "request", "protocol"]
V4_IDENTITY_FIELDS = [
    "own_active_current_item",
    "own_active_last_item",
    "opponent_active_current_item",
    "opponent_active_last_item",
    "own_active_base_ability",
    "own_active_current_ability",
    "opponent_active_base_ability",
    "opponent_active_current_ability",
]
V5_SPECIES_SOURCES = ["unknown", "request", "protocol", "sim_core", "species_fallback"]
V5_STATUS_SOURCES = ["unknown", "request", "protocol", "sim_core", "inferred"]
V5_STATUS_STATES = ["unknown", "none", "brn", "par", "slp", "psn", "tox", "frz", "fainted"]
V5_SPECIES_STATES = ["unknown", "known"]
V5_ROSTER_PLACEMENTS = ["unknown", "active", "bench"]
V5_ROSTER_LIFE_STATES = ["unknown", "alive", "fainted"]
V5_ACTIVE_SPECIES_FIELDS = [
    "own_active_base_species",
    "own_active_current_species",
    "own_active_displayed_species",
    "opponent_active_base_species",
    "opponent_active_current_species",
    "opponent_active_displayed_species",
]
V6_TERA_SOURCES = ["unknown", "request", "protocol", "sim_core", "fallback"]
V6_TERA_AVAILABILITY_STATES = ["unknown", "available", "unavailable", "used"]
V6_TERA_ACTIVE_STATES = ["unknown", "inactive", "active"]
V6_WEATHER_STATES = ["unknown", "none", "rain", "sun", "sand", "snow", "hail", "other"]
V6_TERRAIN_STATES = ["unknown", "none", "electric", "grassy", "misty", "psychic"]
V6_ACTIVITY_STATES = ["unknown", "inactive", "active"]
V6_FIELD_SOURCES = ["unknown", "protocol", "sim_core", "fallback"]
V6_PSEUDO_WEATHER = ["trickroom", "gravity", "magicroom", "wonderroom"]
V6_SIDE_CONDITIONS = ["reflect", "lightscreen", "auroraveil", "tailwind", "safeguard", "mist"]

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

FEATURE_NAMES_V1 = list(PUBLIC_FEATURE_NAMES) + PRIVATE_FEATURE_NAMES + OPPONENT_BELIEF_FEATURE_NAMES
FEATURE_DIM_V1 = len(FEATURE_NAMES_V1)
FEATURE_NAMES = FEATURE_NAMES_V1 + TACTICAL_STATE_FEATURE_NAMES
FEATURE_DIM = len(FEATURE_NAMES)
V3_SLICE1_FEATURE_NAMES = (
    [f"own_active_{stat}_stage_norm" for stat in V3_STAGE_STATS]
    + [f"opponent_active_{stat}_stage_norm" for stat in V3_STAGE_STATS]
    + [f"own_active_base_type_{type_name.lower()}" for type_name in V3_TYPES]
    + [f"opponent_active_base_type_{type_name.lower()}" for type_name in V3_TYPES]
    + [f"own_active_current_type_{type_name.lower()}" for type_name in V3_TYPES]
    + [f"opponent_active_current_type_{type_name.lower()}" for type_name in V3_TYPES]
    + [f"own_active_base_type_source_{source}" for source in V3_BASE_TYPE_SOURCES]
    + [f"opponent_active_base_type_source_{source}" for source in V3_BASE_TYPE_SOURCES]
    + [f"own_active_current_type_source_{source}" for source in V3_CURRENT_TYPE_SOURCES]
    + [f"opponent_active_current_type_source_{source}" for source in V3_CURRENT_TYPE_SOURCES]
)
FEATURE_NAMES_V3 = FEATURE_NAMES + V3_SLICE1_FEATURE_NAMES
FEATURE_DIM_V3 = len(FEATURE_NAMES_V3)
V4_SLICE2_FEATURE_NAMES = (
    [
        f"{field}_hash_{family}_bucket_{bucket:02d}"
        for field in V4_IDENTITY_FIELDS
        for family in ("a", "b")
        for bucket in range(V4_IDENTITY_BUCKETS)
    ]
    + [f"own_active_item_state_{state}" for state in V4_ITEM_STATES]
    + [f"opponent_active_item_state_{state}" for state in V4_ITEM_STATES]
    + [f"own_active_item_source_{source}" for source in V4_STATE_SOURCES]
    + [f"opponent_active_item_source_{source}" for source in V4_STATE_SOURCES]
    + ["own_active_item_suppressed", "opponent_active_item_suppressed"]
    + [f"own_active_ability_state_{state}" for state in V4_ABILITY_STATES]
    + [f"opponent_active_ability_state_{state}" for state in V4_ABILITY_STATES]
    + [f"own_active_ability_source_{source}" for source in V4_STATE_SOURCES]
    + [f"opponent_active_ability_source_{source}" for source in V4_STATE_SOURCES]
    + ["own_active_ability_suppressed", "opponent_active_ability_suppressed"]
)
FEATURE_NAMES_V4 = FEATURE_NAMES_V3 + V4_SLICE2_FEATURE_NAMES
FEATURE_DIM_V4 = len(FEATURE_NAMES_V4)
V5_SLICE3_FEATURE_NAMES = (
    [
        f"{field}_hash_{family}_bucket_{bucket:02d}"
        for field in V5_ACTIVE_SPECIES_FIELDS
        for family in ("a", "b")
        for bucket in range(V4_IDENTITY_BUCKETS)
    ]
    + [
        f"{side}_roster_slot_{slot}_species_hash_{family}_bucket_{bucket:02d}"
        for side in ("own", "opponent")
        for slot in range(1, 7)
        for family in ("a", "b")
        for bucket in range(V4_IDENTITY_BUCKETS)
    ]
    + [
        f"{side}_active_{flag}"
        for side in ("own", "opponent")
        for flag in ("transformed", "displayed_species_uncertain", "illusion_revealed")
    ]
    + [
        f"{side}_active_species_source_{source}"
        for side in ("own", "opponent")
        for source in V5_SPECIES_SOURCES
    ]
    + [
        f"{side}_active_status_{status}"
        for side in ("own", "opponent")
        for status in V5_STATUS_STATES
    ]
    + [
        f"{side}_active_status_source_{source}"
        for side in ("own", "opponent")
        for source in V5_STATUS_SOURCES
    ]
    + [
        f"{side}_active_{status}_turns_public_{field}"
        for side in ("own", "opponent")
        for status in ("sleep", "toxic")
        for field in ("known", "norm")
    ]
    + [
        name
        for side in ("own", "opponent")
        for slot in range(1, 7)
        for name in (
            *[f"{side}_roster_slot_{slot}_species_state_{state}" for state in V5_SPECIES_STATES],
            *[f"{side}_roster_slot_{slot}_placement_{placement}" for placement in V5_ROSTER_PLACEMENTS],
            *[f"{side}_roster_slot_{slot}_life_state_{state}" for state in V5_ROSTER_LIFE_STATES],
            *[f"{side}_roster_slot_{slot}_species_source_{source}" for source in V5_SPECIES_SOURCES],
            *[f"{side}_roster_slot_{slot}_status_{status}" for status in V5_STATUS_STATES],
            *[f"{side}_roster_slot_{slot}_status_source_{source}" for source in V5_STATUS_SOURCES],
        )
    ]
)
FEATURE_NAMES_V5 = FEATURE_NAMES_V4 + V5_SLICE3_FEATURE_NAMES
FEATURE_DIM_V5 = len(FEATURE_NAMES_V5)
V6_SLICE4_FEATURE_NAMES = (
    [
        f"{side}_tera_availability_{state}"
        for side in ("own", "opponent")
        for state in V6_TERA_AVAILABILITY_STATES
    ]
    + [
        f"{side}_active_tera_state_{state}"
        for side in ("own", "opponent")
        for state in V6_TERA_ACTIVE_STATES
    ]
    + [
        f"{side}_active_tera_type_{type_name.lower()}"
        for side in ("own", "opponent")
        for type_name in V3_TYPES
    ]
    + [
        f"{side}_tera_source_{source}"
        for side in ("own", "opponent")
        for source in V6_TERA_SOURCES
    ]
    + [
        f"{side}_{field}"
        for side in ("own", "opponent")
        for field in ("tera_action_available", "current_type_is_tera")
    ]
    + [f"weather_state_{state}" for state in V6_WEATHER_STATES]
    + [f"weather_source_{source}" for source in V6_FIELD_SOURCES]
    + ["weather_turns_public_known", "weather_turns_public_norm"]
    + [f"terrain_state_{state}" for state in V6_TERRAIN_STATES]
    + [f"terrain_source_{source}" for source in V6_FIELD_SOURCES]
    + ["terrain_turns_public_known", "terrain_turns_public_norm"]
    + [
        f"{effect}_{suffix}"
        for effect in V6_PSEUDO_WEATHER
        for suffix in (
            *[f"state_{state}" for state in V6_ACTIVITY_STATES],
            "turns_public_known",
            "turns_public_norm",
        )
    ]
    + [
        f"{side}_{condition}_{suffix}"
        for side in ("own", "opponent")
        for condition in V6_SIDE_CONDITIONS
        for suffix in (
            *[f"state_{state}" for state in V6_ACTIVITY_STATES],
            "turns_public_known",
            "turns_public_norm",
        )
    ]
    + [
        f"{side}_stealthrock_state_{state}"
        for side in ("own", "opponent")
        for state in V6_ACTIVITY_STATES
    ]
    + [
        f"{side}_spikes_layers_{layers}"
        for side in ("own", "opponent")
        for layers in ("unknown", "0", "1", "2", "3")
    ]
    + [
        f"{side}_toxicspikes_layers_{layers}"
        for side in ("own", "opponent")
        for layers in ("unknown", "0", "1", "2")
    ]
    + [
        f"{side}_stickyweb_state_{state}"
        for side in ("own", "opponent")
        for state in V6_ACTIVITY_STATES
    ]
)
FEATURE_NAMES_V6 = FEATURE_NAMES_V5 + V6_SLICE4_FEATURE_NAMES
FEATURE_DIM_V6 = len(FEATURE_NAMES_V6)

# --- Slice 5: move identity, revealed PP, and action/move constraints (v7) ---
V7_MOVE_SLOTS = 4
V7_MOVE_PROVENANCE = ["unknown", "request", "protocol", "sim_core", "inferred"]
V7_CONSTRAINT_STATES = ["unknown", "inactive", "active"]


def _v7_move_slot_names(side: str, present_label: str) -> List[str]:
    names: List[str] = []
    for slot in range(1, V7_MOVE_SLOTS + 1):
        prefix = f"{side}_active_move_slot_{slot}"
        names.extend(
            f"{prefix}_id_hash_{family}_bucket_{bucket:02d}"
            for family in ("a", "b")
            for bucket in range(V4_IDENTITY_BUCKETS)
        )
        names.extend(
            [
                f"{prefix}_{present_label}",
                f"{prefix}_unknown",
                f"{prefix}_disabled",
                f"{prefix}_pp_known",
                f"{prefix}_pp_norm",
            ]
        )
        names.extend(f"{prefix}_provenance_{prov}" for prov in V7_MOVE_PROVENANCE)
    return names


def _v7_state_names(prefix: str) -> List[str]:
    return [f"{prefix}_{state}" for state in V7_CONSTRAINT_STATES]


V7_OWN_CONSTRAINT_NAMES = (
    [
        "own_known_move_count_norm",
        "own_unknown_move_slot_count_norm",
        "own_disabled_move_count_norm",
        "own_selectable_move_count_norm",
    ]
    + _v7_state_names("own_recharge_state")
    + _v7_state_names("own_two_turn_lock_state")
    + _v7_state_names("own_single_move_lock_state")
    + _v7_state_names("own_encore_lock_state")
    + [
        "own_choice_lock_inferred",
        "own_force_switch",
        "own_must_recharge",
        "own_wait_forced",
        "own_trapped",
    ]
    + _v7_state_names("own_taunt_state")
    + _v7_state_names("own_torment_state")
    + _v7_state_names("own_healblock_state")
    + _v7_state_names("own_imprison_state")
    + _v7_state_names("own_disable_state")
    + ["own_substitute_present"]
    + [
        f"own_constraint_locked_move_id_hash_{family}_bucket_{bucket:02d}"
        for family in ("a", "b")
        for bucket in range(V4_IDENTITY_BUCKETS)
    ]
)

V7_OPPONENT_CONSTRAINT_NAMES = (
    [
        "opponent_active_revealed_move_count_norm",
        "opponent_active_unknown_move_slot_count_norm",
    ]
    + _v7_state_names("opponent_taunt_state")
    + _v7_state_names("opponent_torment_state")
    + _v7_state_names("opponent_healblock_state")
    + _v7_state_names("opponent_imprison_state")
    + _v7_state_names("opponent_disable_state")
    + _v7_state_names("opponent_encore_lock_state")
    + [
        "opponent_substitute_present",
        "opponent_pp_known_any",
    ]
)

V7_SLICE5_FEATURE_NAMES = (
    _v7_move_slot_names("own", "known")
    + _v7_move_slot_names("opponent", "revealed")
    + V7_OWN_CONSTRAINT_NAMES
    + V7_OPPONENT_CONSTRAINT_NAMES
)
FEATURE_NAMES_V7 = FEATURE_NAMES_V6 + V7_SLICE5_FEATURE_NAMES
FEATURE_DIM_V7 = len(FEATURE_NAMES_V7)


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


def _stage_value(side: Dict[str, Any], stat: str) -> float:
    boosts = side.get("boosts") if isinstance(side.get("boosts"), dict) else {}
    try:
        return max(-1.0, min(1.0, float(boosts.get(stat, 0) or 0) / 6.0))
    except (TypeError, ValueError):
        return 0.0


def _type_values(side: Dict[str, Any], key: str) -> List[float]:
    active = {str(value).lower() for value in (side.get(key) or []) if str(value)}
    return [float(type_name.lower() in active) for type_name in V3_TYPES]


def _source_values(side: Dict[str, Any], key: str, sources: Sequence[str]) -> List[float]:
    source = str(side.get(key) or "unknown")
    if source not in sources:
        source = "unknown"
    return [float(source == candidate) for candidate in sources]


def v3_slice1_feature_vector(tactical_state: Optional[Dict[str, Any]]) -> np.ndarray:
    state = tactical_state if isinstance(tactical_state, dict) else {}
    own = state.get("own") if isinstance(state.get("own"), dict) else {}
    opponent = state.get("opponent") if isinstance(state.get("opponent"), dict) else {}
    values = [
        *(_stage_value(own, stat) for stat in V3_STAGE_STATS),
        *(_stage_value(opponent, stat) for stat in V3_STAGE_STATS),
        *_type_values(own, "active_base_types"),
        *_type_values(opponent, "active_base_types"),
        *_type_values(own, "active_current_types"),
        *_type_values(opponent, "active_current_types"),
        *_source_values(own, "base_type_source", V3_BASE_TYPE_SOURCES),
        *_source_values(opponent, "base_type_source", V3_BASE_TYPE_SOURCES),
        *_source_values(own, "current_type_source", V3_CURRENT_TYPE_SOURCES),
        *_source_values(opponent, "current_type_source", V3_CURRENT_TYPE_SOURCES),
    ]
    vector = np.asarray(values, dtype=np.float32)
    if vector.shape[0] != len(V3_SLICE1_FEATURE_NAMES):
        raise ValueError(
            f"Live-private v3 slice-1 size mismatch: got {vector.shape[0]}, "
            f"expected {len(V3_SLICE1_FEATURE_NAMES)}."
        )
    return vector


def _identity_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _identity_hash_values(value: Any) -> List[float]:
    identity = _identity_id(value)
    values = [0.0] * (V4_IDENTITY_BUCKETS * 2)
    if not identity:
        return values
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    values[int.from_bytes(digest[0:4], "little") % V4_IDENTITY_BUCKETS] = 1.0
    values[V4_IDENTITY_BUCKETS + (int.from_bytes(digest[4:8], "little") % V4_IDENTITY_BUCKETS)] = 1.0
    return values


def _enum_values(value: Any, choices: Sequence[str]) -> List[float]:
    normalized = str(value or "unknown")
    if normalized not in choices:
        normalized = "unknown"
    return [float(normalized == choice) for choice in choices]


def v4_slice2_feature_vector(tactical_state: Optional[Dict[str, Any]]) -> np.ndarray:
    state = tactical_state if isinstance(tactical_state, dict) else {}
    own = state.get("own") if isinstance(state.get("own"), dict) else {}
    opponent = state.get("opponent") if isinstance(state.get("opponent"), dict) else {}
    identities = [
        own.get("active_item"),
        own.get("active_last_item"),
        opponent.get("active_item"),
        opponent.get("active_last_item"),
        own.get("active_base_ability"),
        own.get("active_current_ability"),
        opponent.get("active_base_ability"),
        opponent.get("active_current_ability"),
    ]
    values: List[float] = []
    for identity in identities:
        values.extend(_identity_hash_values(identity))
    values.extend(_enum_values(own.get("active_item_state"), V4_ITEM_STATES))
    values.extend(_enum_values(opponent.get("active_item_state"), V4_ITEM_STATES))
    values.extend(_enum_values(own.get("active_item_source"), V4_STATE_SOURCES))
    values.extend(_enum_values(opponent.get("active_item_source"), V4_STATE_SOURCES))
    values.extend(
        [
            float(bool(own.get("active_item_suppressed"))),
            float(bool(opponent.get("active_item_suppressed"))),
        ]
    )
    values.extend(_enum_values(own.get("active_ability_state"), V4_ABILITY_STATES))
    values.extend(_enum_values(opponent.get("active_ability_state"), V4_ABILITY_STATES))
    values.extend(_enum_values(own.get("active_ability_source"), V4_STATE_SOURCES))
    values.extend(_enum_values(opponent.get("active_ability_source"), V4_STATE_SOURCES))
    values.extend(
        [
            float(bool(own.get("active_ability_suppressed"))),
            float(bool(opponent.get("active_ability_suppressed"))),
        ]
    )
    vector = np.asarray(values, dtype=np.float32)
    if vector.shape[0] != len(V4_SLICE2_FEATURE_NAMES):
        raise ValueError(
            f"Live-private v4 slice-2 size mismatch: got {vector.shape[0]}, "
            f"expected {len(V4_SLICE2_FEATURE_NAMES)}."
        )
    return vector


def _status_state(side_or_mon: Dict[str, Any], *, active: bool = False) -> str:
    fainted = bool(side_or_mon.get("active_fainted") if active else side_or_mon.get("fainted"))
    if fainted:
        return "fainted"
    status = side_or_mon.get("active_status") if active else side_or_mon.get("status")
    if str(status or "") in V5_STATUS_STATES:
        return str(status)
    source = side_or_mon.get("active_status_source") if active else side_or_mon.get("status_source")
    species = (
        side_or_mon.get("active_current_species") or side_or_mon.get("active_species")
        if active
        else side_or_mon.get("current_species") or side_or_mon.get("species")
    )
    return "none" if species and str(source or "unknown") != "unknown" else "unknown"


def _roster_slots(side: Dict[str, Any]) -> List[Dict[str, Any]]:
    known = [dict(mon) for mon in (side.get("known_team") or []) if isinstance(mon, dict)]
    return (known + [{} for _ in range(6)])[:6]


def v5_slice3_feature_vector(tactical_state: Optional[Dict[str, Any]]) -> np.ndarray:
    state = tactical_state if isinstance(tactical_state, dict) else {}
    own = state.get("own") if isinstance(state.get("own"), dict) else {}
    opponent = state.get("opponent") if isinstance(state.get("opponent"), dict) else {}
    sides = {"own": own, "opponent": opponent}
    active_identities = [
        own.get("active_base_species"),
        own.get("active_current_species") or own.get("active_species"),
        own.get("active_displayed_species") or own.get("active_species"),
        opponent.get("active_base_species"),
        opponent.get("active_current_species") or opponent.get("active_species"),
        opponent.get("active_displayed_species") or opponent.get("active_species"),
    ]
    roster = {name: _roster_slots(side) for name, side in sides.items()}
    values: List[float] = []
    for identity in active_identities:
        values.extend(_identity_hash_values(identity))
    for side_name in ("own", "opponent"):
        for mon in roster[side_name]:
            values.extend(_identity_hash_values(mon.get("base_species") or mon.get("species")))
    for side_name in ("own", "opponent"):
        side = sides[side_name]
        values.extend(
            [
                float(bool(side.get("active_transformed"))),
                float(bool(side.get("active_displayed_species_uncertain"))),
                float(bool(side.get("active_illusion_revealed"))),
            ]
        )
    for side_name in ("own", "opponent"):
        values.extend(_enum_values(sides[side_name].get("active_species_source"), V5_SPECIES_SOURCES))
    for side_name in ("own", "opponent"):
        values.extend(_enum_values(_status_state(sides[side_name], active=True), V5_STATUS_STATES))
    for side_name in ("own", "opponent"):
        values.extend(_enum_values(sides[side_name].get("active_status_source"), V5_STATUS_SOURCES))
    for side_name in ("own", "opponent"):
        side = sides[side_name]
        status = _status_state(side, active=True)
        turns = side.get("active_status_turns_public")
        for status_id in ("slp", "tox"):
            known = status == status_id and turns is not None
            values.extend([float(known), _clip(float(turns or 0) / 15.0) if known else 0.0])
    for side_name in ("own", "opponent"):
        for mon in roster[side_name]:
            species = mon.get("base_species") or mon.get("species")
            species_state = "known" if _known(species) else "unknown"
            placement = "active" if mon.get("active") else "bench" if species else "unknown"
            life_state = "fainted" if mon.get("fainted") else "alive" if species else "unknown"
            values.extend(_enum_values(species_state, V5_SPECIES_STATES))
            values.extend(_enum_values(placement, V5_ROSTER_PLACEMENTS))
            values.extend(_enum_values(life_state, V5_ROSTER_LIFE_STATES))
            values.extend(_enum_values(mon.get("species_source"), V5_SPECIES_SOURCES))
            values.extend(_enum_values(_status_state(mon), V5_STATUS_STATES))
            values.extend(_enum_values(mon.get("status_source"), V5_STATUS_SOURCES))
    vector = np.asarray(values, dtype=np.float32)
    if vector.shape[0] != len(V5_SLICE3_FEATURE_NAMES):
        raise ValueError(
            f"Live-private v5 slice-3 size mismatch: got {vector.shape[0]}, "
            f"expected {len(V5_SLICE3_FEATURE_NAMES)}."
        )
    return vector


def _weather_state(value: Any, known: bool) -> str:
    if not known:
        return "unknown"
    weather = _identity_id(value)
    return {
        "": "none",
        "raindance": "rain",
        "primordialsea": "rain",
        "sunnyday": "sun",
        "desolateland": "sun",
        "sandstorm": "sand",
        "snow": "snow",
        "hail": "hail",
    }.get(weather, "other")


def _terrain_state(value: Any, known: bool) -> str:
    if not known:
        return "unknown"
    terrain = _identity_id(value)
    return {
        "": "none",
        "electricterrain": "electric",
        "grassyterrain": "grassy",
        "mistyterrain": "misty",
        "psychicterrain": "psychic",
    }.get(terrain, "unknown")


def _activity_state(active: bool, known: bool) -> str:
    if not known:
        return "unknown"
    return "active" if active else "inactive"


def _duration_values(container: Dict[str, Any], key: str, active: bool) -> List[float]:
    raw = container.get(key) if isinstance(container.get(key), dict) else {}
    known = bool(active and raw.get("turns_since_started") is not None)
    return [float(known), _clip(float(raw.get("turns_since_started", 0) or 0) / 10.0) if known else 0.0]


def _tera_availability(side: Dict[str, Any]) -> str:
    value = str(side.get("tera_availability_state") or "unknown")
    return value if value in V6_TERA_AVAILABILITY_STATES else "unknown"


def v6_slice4_feature_vector(tactical_state: Optional[Dict[str, Any]]) -> np.ndarray:
    state = tactical_state if isinstance(tactical_state, dict) else {}
    state_known = bool(state.get("perspective_side"))
    own = state.get("own") if isinstance(state.get("own"), dict) else {}
    opponent = state.get("opponent") if isinstance(state.get("opponent"), dict) else {}
    sides = {"own": own, "opponent": opponent}
    field_durations = state.get("field_durations") if isinstance(state.get("field_durations"), dict) else {}
    field_effects = {_identity_id(value) for value in (state.get("field_effects") or [])}
    values: List[float] = []
    for side_name in ("own", "opponent"):
        values.extend(_enum_values(_tera_availability(sides[side_name]), V6_TERA_AVAILABILITY_STATES))
    for side_name in ("own", "opponent"):
        side = sides[side_name]
        active_known = bool(side.get("active_species") or side.get("active_current_species"))
        values.extend(
            _enum_values(
                _activity_state(bool(side.get("active_terastallized")), active_known),
                V6_TERA_ACTIVE_STATES,
            )
        )
    for side_name in ("own", "opponent"):
        tera_type = str(sides[side_name].get("active_tera_type") or "").lower()
        values.extend([float(tera_type == type_name.lower()) for type_name in V3_TYPES])
    for side_name in ("own", "opponent"):
        values.extend(_enum_values(sides[side_name].get("tera_source"), V6_TERA_SOURCES))
    for side_name in ("own", "opponent"):
        side = sides[side_name]
        values.extend(
            [
                float(bool(side.get("tera_action_available"))),
                float(
                    bool(side.get("active_terastallized"))
                    and str(side.get("current_type_source") or "") == "protocol_tera"
                ),
            ]
        )

    weather = _weather_state(state.get("weather"), state_known)
    values.extend(_enum_values(weather, V6_WEATHER_STATES))
    values.extend(_enum_values("protocol" if state_known else "unknown", V6_FIELD_SOURCES))
    values.extend(_duration_values(field_durations, "weather", weather not in {"unknown", "none"}))

    terrain = _terrain_state(state.get("terrain"), state_known)
    values.extend(_enum_values(terrain, V6_TERRAIN_STATES))
    values.extend(_enum_values("protocol" if state_known else "unknown", V6_FIELD_SOURCES))
    values.extend(_duration_values(field_durations, "terrain", terrain not in {"unknown", "none"}))

    for effect in V6_PSEUDO_WEATHER:
        active = effect in field_effects
        values.extend(_enum_values(_activity_state(active, state_known), V6_ACTIVITY_STATES))
        values.extend(_duration_values(field_durations, effect, active))

    for side_name in ("own", "opponent"):
        side = sides[side_name]
        side_known = state_known and bool(side)
        conditions = side.get("side_conditions") if isinstance(side.get("side_conditions"), dict) else {}
        durations = (
            side.get("side_condition_durations")
            if isinstance(side.get("side_condition_durations"), dict)
            else {}
        )
        for condition in V6_SIDE_CONDITIONS:
            active = bool(conditions.get(condition))
            values.extend(_enum_values(_activity_state(active, side_known), V6_ACTIVITY_STATES))
            values.extend(_duration_values(durations, condition, active))

    for side_name in ("own", "opponent"):
        side = sides[side_name]
        side_known = state_known and bool(side)
        conditions = side.get("side_conditions") if isinstance(side.get("side_conditions"), dict) else {}
        values.extend(
            _enum_values(
                _activity_state(bool(conditions.get("stealthrock")), side_known),
                V6_ACTIVITY_STATES,
            )
        )
    for side_name in ("own", "opponent"):
        side = sides[side_name]
        conditions = side.get("side_conditions") if isinstance(side.get("side_conditions"), dict) else {}
        layers = str(max(0, min(3, int(conditions.get("spikes", 0) or 0)))) if state_known else "unknown"
        values.extend(_enum_values(layers, ["unknown", "0", "1", "2", "3"]))
    for side_name in ("own", "opponent"):
        side = sides[side_name]
        conditions = side.get("side_conditions") if isinstance(side.get("side_conditions"), dict) else {}
        layers = str(max(0, min(2, int(conditions.get("toxicspikes", 0) or 0)))) if state_known else "unknown"
        values.extend(_enum_values(layers, ["unknown", "0", "1", "2"]))
    for side_name in ("own", "opponent"):
        side = sides[side_name]
        conditions = side.get("side_conditions") if isinstance(side.get("side_conditions"), dict) else {}
        values.extend(
            _enum_values(
                _activity_state(bool(conditions.get("stickyweb")), state_known and bool(side)),
                V6_ACTIVITY_STATES,
            )
        )

    vector = np.asarray(values, dtype=np.float32)
    if vector.shape[0] != len(V6_SLICE4_FEATURE_NAMES):
        raise ValueError(
            f"Live-private v6 slice-4 size mismatch: got {vector.shape[0]}, "
            f"expected {len(V6_SLICE4_FEATURE_NAMES)}."
        )
    return vector


def _v7_move_slot_values(move: Optional[Dict[str, Any]]) -> List[float]:
    """Per-slot move-identity features. ``move`` is None for an unknown/empty slot."""
    if not isinstance(move, dict):
        return (
            [0.0] * (V4_IDENTITY_BUCKETS * 2)
            + [0.0, 1.0, 0.0, 0.0, 0.0]
            + _enum_values("unknown", V7_MOVE_PROVENANCE)
        )
    name = move.get("name") or move.get("id")
    values = list(_identity_hash_values(name))
    disabled = float(bool(move.get("disabled")))
    pp = move.get("pp")
    maxpp = move.get("maxpp")
    if isinstance(pp, (int, float)) and isinstance(maxpp, (int, float)) and float(maxpp) > 0:
        pp_known, pp_norm = 1.0, _clip(float(pp) / float(maxpp))
    else:
        pp_known, pp_norm = 0.0, 0.0
    source = str(move.get("source") or "")
    provenance = {"request": "request", "protocol": "protocol", "sim_core": "sim_core", "randbats": "inferred"}.get(
        source, "inferred" if move.get("inferred") else "unknown"
    )
    values.extend([1.0, 0.0, disabled, pp_known, pp_norm])
    values.extend(_enum_values(provenance, V7_MOVE_PROVENANCE))
    return values


def _opponent_revealed_moves(opponent: Dict[str, Any]) -> List[Dict[str, Any]]:
    species = opponent.get("active_base_species") or opponent.get("active_species")
    revealed_map = opponent.get("revealed_moves_by_species")
    moves = revealed_map.get(species) if isinstance(revealed_map, dict) and species else None
    moves = moves if isinstance(moves, list) else []
    return [{"name": str(name), "source": "protocol"} for name in moves if str(name)][:V7_MOVE_SLOTS]


def _has_constraint(side: Dict[str, Any], name: str) -> bool:
    volatiles = {_identity_id(v) for v in (side.get("volatiles") or []) if isinstance(side.get("volatiles"), list)}
    constraint = {
        _identity_id(v) for v in (side.get("constraint_volatiles") or []) if isinstance(side.get("constraint_volatiles"), list)
    }
    return name in volatiles or name in constraint


def _v7_volatile_state(side: Dict[str, Any], name: str, known: bool) -> List[float]:
    if not known:
        return _enum_values("unknown", V7_CONSTRAINT_STATES)
    return _enum_values("active" if _has_constraint(side, name) else "inactive", V7_CONSTRAINT_STATES)


def v7_slice5_feature_vector(tactical_state: Optional[Dict[str, Any]]) -> np.ndarray:
    state = tactical_state if isinstance(tactical_state, dict) else {}
    own = state.get("own") if isinstance(state.get("own"), dict) else {}
    opponent = state.get("opponent") if isinstance(state.get("opponent"), dict) else {}

    own_moves = [mv for mv in (own.get("active_moves") or []) if isinstance(mv, dict)]
    opponent_moves = _opponent_revealed_moves(opponent)

    values: List[float] = []
    for slot in range(V7_MOVE_SLOTS):
        values.extend(_v7_move_slot_values(own_moves[slot] if slot < len(own_moves) else None))
    for slot in range(V7_MOVE_SLOTS):
        values.extend(_v7_move_slot_values(opponent_moves[slot] if slot < len(opponent_moves) else None))

    # --- own constraints ---
    own_known = bool(own_moves) or bool(own.get("active_species"))
    n = len(own_moves)
    selectable = [mv for mv in own_moves if not mv.get("disabled")]
    disabled_count = sum(1 for mv in own_moves if mv.get("disabled"))
    first = own_moves[0] if n == 1 else None
    first_id = _identity_id(first.get("name") or first.get("id")) if first else ""
    first_locked = bool(first and first.get("pp") is None)  # locked moves omit PP in the request
    is_recharge = bool(n == 1 and first_id == "recharge")
    is_two_turn_lock = bool(first_locked and not is_recharge)
    is_single_move_lock = bool(n > 1 and len(selectable) == 1)
    has_encore = _has_constraint(own, "encore")
    choice_lock_inferred = bool(is_single_move_lock and not has_encore)

    locked_move = None
    if is_two_turn_lock:
        locked_move = first.get("name") or first.get("id")
    elif is_single_move_lock:
        locked_move = selectable[0].get("name") or selectable[0].get("id")

    def state_enum(active: bool) -> List[float]:
        if not own_known:
            return _enum_values("unknown", V7_CONSTRAINT_STATES)
        return _enum_values("active" if active else "inactive", V7_CONSTRAINT_STATES)

    values.extend(
        [
            _clip(n / 4.0),
            _clip((4 - min(4, n)) / 4.0) if own_known else 1.0,
            _clip(disabled_count / 4.0),
            _clip(len(selectable) / 4.0),
        ]
    )
    values.extend(state_enum(is_recharge))
    values.extend(state_enum(is_two_turn_lock))
    values.extend(state_enum(is_single_move_lock))
    values.extend(_v7_volatile_state(own, "encore", own_known))
    values.extend(
        [
            float(choice_lock_inferred),
            float(bool(own.get("force_switch"))),
            float(is_recharge),
            float(bool(own.get("wait"))),
            float(bool(own.get("trapped"))),
        ]
    )
    values.extend(_v7_volatile_state(own, "taunt", own_known))
    values.extend(_v7_volatile_state(own, "torment", own_known))
    values.extend(_v7_volatile_state(own, "healblock", own_known))
    values.extend(_v7_volatile_state(own, "imprison", own_known))
    values.extend(_v7_volatile_state(own, "disable", own_known))
    values.append(float(_has_constraint(own, "substitute")))
    values.extend(_identity_hash_values(locked_move))

    # --- opponent constraints ---
    opp_known = bool(opponent.get("active_base_species") or opponent.get("active_species"))
    values.extend(
        [
            _clip(len(opponent_moves) / 4.0),
            _clip((4 - min(4, len(opponent_moves))) / 4.0) if opp_known else 1.0,
        ]
    )
    values.extend(_v7_volatile_state(opponent, "taunt", opp_known))
    values.extend(_v7_volatile_state(opponent, "torment", opp_known))
    values.extend(_v7_volatile_state(opponent, "healblock", opp_known))
    values.extend(_v7_volatile_state(opponent, "imprison", opp_known))
    values.extend(_v7_volatile_state(opponent, "disable", opp_known))
    values.extend(_v7_volatile_state(opponent, "encore", opp_known))
    values.append(float(_has_constraint(opponent, "substitute")))
    values.append(0.0)  # opponent_pp_known_any: opponent exact PP is never request-visible

    vector = np.asarray(values, dtype=np.float32)
    if vector.shape[0] != len(V7_SLICE5_FEATURE_NAMES):
        raise ValueError(
            f"Live-private v7 slice-5 size mismatch: got {vector.shape[0]}, "
            f"expected {len(V7_SLICE5_FEATURE_NAMES)}."
        )
    return vector


def validate_live_private_feature_metadata(
    *,
    feature_version: str,
    feature_dim: int,
    expected_version: str,
) -> None:
    expected = {
        FEATURE_VERSION_V1: FEATURE_DIM_V1,
        FEATURE_VERSION: FEATURE_DIM,
        FEATURE_VERSION_V3: FEATURE_DIM_V3,
        FEATURE_VERSION_V4: FEATURE_DIM_V4,
        FEATURE_VERSION_V5: FEATURE_DIM_V5,
        FEATURE_VERSION_V6: FEATURE_DIM_V6,
        FEATURE_VERSION_V7: FEATURE_DIM_V7,
    }
    if expected_version not in expected:
        raise ValueError(f"Unsupported expected feature version: {expected_version!r}.")
    if feature_version != expected_version or int(feature_dim) != expected[expected_version]:
        raise ValueError(
            f"Feature metadata version/dim mismatch: got {feature_version!r}/{feature_dim}; "
            f"expected {expected_version!r}/{expected[expected_version]}."
        )


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
    prefix_log = []
    current_turn = 0
    for line in protocol_log:
        text = str(line)
        parts = text.strip().split("|") if text.strip().startswith("|") else []
        if len(parts) >= 3 and parts[1] == "turn":
            try:
                current_turn = int(parts[2])
            except ValueError:
                current_turn = through_turn
        if current_turn > int(through_turn):
            break
        prefix_log.append(text)
    prefixed["protocol_log"] = prefix_log
    return prefixed


def build_live_private_feature_vector(
    *,
    public_features: np.ndarray,
    private_state: Optional[Dict[str, Any]] = None,
    opponent_belief: Optional[Dict[str, Any]] = None,
    trajectory: Optional[Dict[str, Any]] = None,
    player_side: Optional[str] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
    feature_version: str = FEATURE_VERSION,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    public = np.asarray(public_features, dtype=np.float32).reshape(-1)
    if public.shape[0] != len(PUBLIC_FEATURE_NAMES):
        raise ValueError(f"Expected {len(PUBLIC_FEATURE_NAMES)} public features, got {public.shape[0]}.")
    private = private_state_feature_vector(private_state)
    opponent = opponent_belief_feature_vector(opponent_belief, trajectory=trajectory, player_side=player_side)
    if tactical_state is None:
        protocol_log = (trajectory or {}).get("protocol_log") if isinstance(trajectory, dict) else []
        if isinstance(protocol_log, list):
            tactical_state = build_tactical_state(
                protocol_log,
                perspective_side=player_side if player_side in ("p1", "p2") else "p1",
            )
        else:
            tactical_state = {}
    tactical_state = snapshot_with_private_state(tactical_state, private_state)
    tactical = tactical_state_feature_vector(tactical_state)
    v2_features = np.concatenate([public, private, opponent, tactical]).astype(np.float32)
    if v2_features.shape[0] != FEATURE_DIM:
        raise ValueError(f"Live-private feature size mismatch: got {v2_features.shape[0]}, expected {FEATURE_DIM}.")
    if feature_version == FEATURE_VERSION:
        features = v2_features
        feature_names = FEATURE_NAMES
    elif feature_version == FEATURE_VERSION_V3:
        features = np.concatenate([v2_features, v3_slice1_feature_vector(tactical_state)]).astype(np.float32)
        feature_names = FEATURE_NAMES_V3
    elif feature_version == FEATURE_VERSION_V4:
        features = np.concatenate(
            [
                v2_features,
                v3_slice1_feature_vector(tactical_state),
                v4_slice2_feature_vector(tactical_state),
            ]
        ).astype(np.float32)
        feature_names = FEATURE_NAMES_V4
    elif feature_version == FEATURE_VERSION_V5:
        features = np.concatenate(
            [
                v2_features,
                v3_slice1_feature_vector(tactical_state),
                v4_slice2_feature_vector(tactical_state),
                v5_slice3_feature_vector(tactical_state),
            ]
        ).astype(np.float32)
        feature_names = FEATURE_NAMES_V5
    elif feature_version == FEATURE_VERSION_V6:
        features = np.concatenate(
            [
                v2_features,
                v3_slice1_feature_vector(tactical_state),
                v4_slice2_feature_vector(tactical_state),
                v5_slice3_feature_vector(tactical_state),
                v6_slice4_feature_vector(tactical_state),
            ]
        ).astype(np.float32)
        feature_names = FEATURE_NAMES_V6
    elif feature_version == FEATURE_VERSION_V7:
        features = np.concatenate(
            [
                v2_features,
                v3_slice1_feature_vector(tactical_state),
                v4_slice2_feature_vector(tactical_state),
                v5_slice3_feature_vector(tactical_state),
                v6_slice4_feature_vector(tactical_state),
                v7_slice5_feature_vector(tactical_state),
            ]
        ).astype(np.float32)
        feature_names = FEATURE_NAMES_V7
    else:
        raise ValueError(
            f"Unsupported live-private feature_version={feature_version!r}; "
            f"expected one of {FEATURE_VERSION!r}, {FEATURE_VERSION_V3!r}, "
            f"{FEATURE_VERSION_V4!r}, {FEATURE_VERSION_V5!r}, {FEATURE_VERSION_V6!r}, "
            f"or {FEATURE_VERSION_V7!r}."
        )
    if features.shape[0] != len(feature_names):
        raise ValueError(
            f"Live-private {feature_version} size mismatch: got {features.shape[0]}, "
            f"expected {len(feature_names)}."
        )
    debug = {
        "feature_version": feature_version,
        "feature_dim": len(feature_names),
        "v1_feature_dim": FEATURE_DIM_V1,
        "public_feature_version": PUBLIC_FEATURE_VERSION,
        "tactical_feature_version": TACTICAL_FEATURE_VERSION,
        "used_private_state": bool(isinstance(private_state, dict) and private_state.get("team")),
        "used_opponent_belief": bool(isinstance(opponent_belief, dict) and opponent_belief.get("opponents")),
        "used_tactical_state": bool(tactical_state),
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
    feature_version: str = FEATURE_VERSION,
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
    tactical_state = build_tactical_state(
        list(log),
        perspective_side=player_side if player_side in ("p1", "p2") else "p1",
    )
    tactical_state = snapshot_with_private_state(tactical_state, private_state)
    private_state["tactical_state"] = tactical_state
    features, debug = build_live_private_feature_vector(
        public_features=public_features,
        private_state=private_state,
        opponent_belief=opponent_belief,
        trajectory=trajectory,
        player_side=player_side if player_side in ("p1", "p2") else None,
        tactical_state=tactical_state,
        feature_version=feature_version,
    )
    debug["tactical_snapshot"] = tactical_state
    debug.update(public_debug)
    debug["feature_names_preview"] = FEATURE_NAMES[:8]
    debug["feature_values_preview"] = [float(v) for v in features[:8].tolist()]
    return features, debug, private_state, opponent_belief, trajectory


def feature_schema() -> Dict[str, Any]:
    return {
        "feature_version": FEATURE_VERSION,
        "feature_dim": FEATURE_DIM,
        "feature_names": FEATURE_NAMES,
        "v3_feature_version": FEATURE_VERSION_V3,
        "v3_feature_dim": FEATURE_DIM_V3,
        "v3_feature_names": FEATURE_NAMES_V3,
        "v3_slice1_feature_names": V3_SLICE1_FEATURE_NAMES,
        "v4_feature_version": FEATURE_VERSION_V4,
        "v4_feature_dim": FEATURE_DIM_V4,
        "v4_feature_names": FEATURE_NAMES_V4,
        "v4_slice2_feature_names": V4_SLICE2_FEATURE_NAMES,
        "v5_feature_version": FEATURE_VERSION_V5,
        "v5_feature_dim": FEATURE_DIM_V5,
        "v5_feature_names": FEATURE_NAMES_V5,
        "v5_slice3_feature_names": V5_SLICE3_FEATURE_NAMES,
        "v6_feature_version": FEATURE_VERSION_V6,
        "v6_feature_dim": FEATURE_DIM_V6,
        "v6_feature_names": FEATURE_NAMES_V6,
        "v6_slice4_feature_names": V6_SLICE4_FEATURE_NAMES,
        "v7_feature_version": FEATURE_VERSION_V7,
        "v7_feature_dim": FEATURE_DIM_V7,
        "v7_feature_names": FEATURE_NAMES_V7,
        "v7_slice5_feature_names": V7_SLICE5_FEATURE_NAMES,
        "v1_feature_version": FEATURE_VERSION_V1,
        "v1_feature_dim": FEATURE_DIM_V1,
        "v1_feature_names": FEATURE_NAMES_V1,
        "public_feature_version": PUBLIC_FEATURE_VERSION,
        "public_feature_dim": len(PUBLIC_FEATURE_NAMES),
        "tactical_feature_version": TACTICAL_FEATURE_VERSION,
        "tactical_feature_dim": len(TACTICAL_STATE_FEATURE_NAMES),
        "tactical_feature_names": TACTICAL_STATE_FEATURE_NAMES,
    }
