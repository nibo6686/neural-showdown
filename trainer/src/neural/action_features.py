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
VARIABLE_POWER_DAMAGE_MOVE_IDS = {
    "reversal",
    "flail",
    "gyroball",
    "electroball",
    "grassknot",
    "lowkick",
    "heavyslam",
    "heatcrash",
}

# Mechanics-repair batch 1: fixed-damage, multi-hit and weather-dependent
# accuracy move ids. These do not add or reorder any feature names — they only
# steer `resolve_action_impact` to compute exact impact, route to the oracle, or
# fail closed (impact_unknown) instead of emitting a wrong-exact value.

# Fixed-damage moves whose damage @smogon/calc resolves exactly from user level
# (and still honors type immunity). Routed to the oracle like variable-power.
FIXED_DAMAGE_ORACLE_MOVE_IDS = {"seismictoss", "nightshade"}
# Fixed-damage / counter moves whose exact damage depends on target current HP or
# on damage received this turn, neither of which the diagnostic oracle resolves
# (it returns 0). These fail closed rather than emit a wrong-exact 0-damage value.
FIXED_DAMAGE_FAIL_CLOSED_MOVE_IDS = {
    "superfang",
    "ruination",
    "endeavor",
    "mirrorcoat",
    "counter",
    "metalburst",
}
# Multi-hit moves whose total damage / hit distribution cannot be represented
# faithfully in the single expected/min/max impact fields. The oracle reports
# per-hit rolls (flattened), so these fail closed instead of under-reporting.
MULTI_HIT_MOVE_IDS = {
    "bulletseed",
    "rockblast",
    "iciclespear",
    "tailslap",
    "scaleshot",
    "dragondarts",
    "dualwingbeat",
    "surgingstrikes",
    "tachyoncutter",
    "populationbomb",
    "tripleaxel",
}
# Moves whose hit chance depends on current weather (protocol-observable).
WEATHER_DEPENDENT_ACCURACY_MOVE_IDS = {
    "blizzard",
    "thunder",
    "hurricane",
    "bleakwindstorm",
}

# Batch 3: two-turn charge / delayed-damage moves. The oracle returns the on-hit
# damage as if it lands this turn. That is only exact when the move actually fires
# this turn (sun or Power Herb for Solar Beam, Power Herb for Meteor Beam; never
# for the always-delayed Future Sight). Otherwise the immediate damage is wrong
# timing and the impact fails closed.
TWO_TURN_CHARGE_MOVE_IDS = {"solarbeam", "meteorbeam", "futuresight"}
# Dynamic-type move that becomes Stellar-typed when Terastallized; Stellar STAB
# (2x) and effectiveness are not representable by the standard type chart, so it
# fails closed rather than emit a wrong-exact value.
DYNAMIC_TYPE_FAIL_CLOSED_MOVE_IDS = {"terastarstorm"}

# Batch 4: conditional-execution and turn/history-conditional-power moves whose
# success or power depends on the opponent's same-turn action, the first-active
# turn, the user's form, the target's item, the within-turn move order, or prior
# move-failure history not plumbed to the oracle. The impact must not encode
# "deals this damage" when the move may fail or its power may double, so these
# fail closed (impact_unknown). The dependency label records why.
CONDITIONAL_FAIL_CLOSED_MOVE_DEPENDENCY = {
    "suckerpunch": "opponent_action",
    "thunderclap": "opponent_action",
    "focuspunch": "opponent_action",
    "fakeout": "first_active_turn",
    "firstimpression": "first_active_turn",
    "doubleshock": "user_type_and_self_effect",
    "hyperspacefury": "user_form_and_self_effect",
    "poltergeist": "target_item_presence",
    "payback": "same_turn_order",
    "avalanche": "same_turn_hit",
    "lashout": "same_turn_stat_drop",
    "stompingtantrum": "prior_move_failure",
    "temperflare": "prior_move_failure",
}
CONDITIONAL_FAIL_CLOSED_MOVE_IDS = set(CONDITIONAL_FAIL_CLOSED_MOVE_DEPENDENCY)
# Moves whose damage is exact (the calc bypasses screens) but that conditionally
# remove the target's screens — a field/side change coarsely flagged, not exact.
SCREEN_BREAK_ON_HIT_MOVE_IDS = {"brickbreak", "psychicfangs"}

# Batch 5: moves whose *damage* itself is wrong-exact — Beat Up (per-ally-Attack
# damage the calc returns as 0) and Fickle Beam (random double-power branch
# collapsed to one value). These fail closed. Knock Off / Bug Bite / Grassy Glide
# are NOT here: their damage is exact, so it is kept; only their unrepresented
# next-state effect (item removal / stolen berry / terrain-conditional priority)
# leaves them INEXACT, documented for a future v7 typed field.
FINAL_FAIL_CLOSED_MOVE_DEPENDENCY = {
    "beatup": "party_attack_stats",
    "ficklebeam": "random_power",
}
FINAL_FAIL_CLOSED_MOVE_IDS = set(FINAL_FAIL_CLOSED_MOVE_DEPENDENCY)
# Guaranteed-critical-hit moves: the calc already includes the crit in the damage
# rolls, so the impact must report crit_included=True (not the default False).
GUARANTEED_CRIT_MOVE_IDS = {"wickedblow", "flowertrick"}
OPPONENT_ACTION_BRANCH_MOVE_IDS = {"suckerpunch", "thunderclap", "focuspunch"}
ACTIVE_TURN_BRANCH_MOVE_IDS = {"fakeout", "firstimpression"}
TARGET_SWITCH_BRANCH_MOVE_IDS = {"pursuit"}
TARGET_SWITCH_POWER_BRANCH_MOVE_IDS = {"payback", "pursuit"}
PRIOR_TURN_OR_HISTORY_BRANCH_MOVE_IDS = {
    "payback",
    "avalanche",
    "lashout",
    "stompingtantrum",
    "temperflare",
}
RANDOM_CALL_MOVE_IDS = {"metronome", "sleeptalk", "copycat", "mirrormove", "naturepower", "assist"}
BINDING_MOVE_IDS = {"bind", "wrap", "firespin", "whirlpool", "sandtomb", "infestation", "magmastorm", "snaptrap"}
RESIDUAL_PRESSURE_MOVE_IDS = {"toxic", "toxicthread", "leechseed", "saltcure"} | BINDING_MOVE_IDS
PHASING_OR_FORCED_SWITCH_MOVE_IDS = {"roar", "whirlwind", "dragontail", "circlethrow", "partingshot", "chillyreception", "teleport"}
SELF_PIVOT_MOVE_IDS = {"uturn", "voltswitch", "flipturn", "partingshot", "teleport", "chillyreception"}
HIT_REQUIRED_SELF_PIVOT_MOVE_IDS = {"uturn", "voltswitch", "flipturn", "partingshot"}
DAMAGING_SELF_PIVOT_MOVE_IDS = {"uturn", "voltswitch", "flipturn"}
STAT_DROP_SELF_PIVOT_MOVE_IDS = {"partingshot"}
SELF_KO_ALWAYS_MOVE_IDS = {"explosion", "selfdestruct", "mistyexplosion"}
SELF_KO_IF_SUCCESSFUL_MOVE_IDS = {"memento", "healingwish", "lunardance", "finalgambit"}
HEALING_WISH_SACRIFICE_MOVE_IDS = {"healingwish", "lunardance"}
STAT_DROP_SACRIFICE_MOVE_IDS = {"memento"}
HP_COST_SELF_KO_MOVE_IDS = {"steelbeam", "mindblown", "chloroblast"}
TARGET_PHAZING_MOVE_IDS = {"roar", "whirlwind", "dragontail", "circlethrow"}
HIT_REQUIRED_PHAZING_MOVE_IDS = {"dragontail", "circlethrow"}
SUBSTITUTE_BLOCKABLE_PHAZING_MOVE_IDS = {"dragontail", "circlethrow"}

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

# --- legal-action-v6: repeat-chain context/provenance ---
ACTION_FEATURE_VERSION_V6 = "legal-action-v6"
SLICE7_ACTION_FEATURE_NAMES = [
    "repeat_chain_is_rollout",
    "repeat_chain_is_fury_cutter",
    "repeat_chain_count_norm",
    "repeat_chain_multiplier_norm",
    "repeat_chain_state_known",
    "repeat_chain_state_exact",
    "repeat_chain_provenance_protocol_complete",
    "repeat_chain_provenance_inferred_lower_bound",
    "repeat_chain_provenance_unknown",
    "repeat_chain_reset_observed",
    "rollout_defense_curl_active",
    "rollout_defense_curl_known",
    "rollout_forced_continuation_active",
]
ACTION_FEATURE_NAMES_V6 = ACTION_FEATURE_NAMES_V5 + SLICE7_ACTION_FEATURE_NAMES
ACTION_FEATURE_DIM_V6 = len(ACTION_FEATURE_NAMES_V6)

# --- legal-action-v7 (batch 1): typed status + stat-delta effects ---
# Append-only after the byte-identical 331D v6 prefix. This first slice replaces
# the v6 coarse next-state booleans (which remain in the prefix for backward
# compatibility) with typed, oracle-derived status chances and stat-stage deltas.
# Later v7 batches will append further typed-effect slices (volatile/item/timing/
# hazards/...); see `legal_action_v7_typed_effect_schema_design.md`.
ACTION_FEATURE_VERSION_V7 = "legal-action-v7"
STATUS_EFFECT_KEYS = ["brn", "par", "psn", "tox", "slp", "frz", "confusion"]
STAT_EFFECT_KEYS = ["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"]
SLICE8_STATUS_STAT_FEATURE_NAMES = (
    [f"effect_target_status_{key}_chance" for key in STATUS_EFFECT_KEYS]
    + [f"effect_self_status_{key}_chance" for key in STATUS_EFFECT_KEYS]
    + [f"effect_target_boost_{stat}_stage" for stat in STAT_EFFECT_KEYS]
    + ["effect_target_stat_chance"]
    + [f"effect_self_boost_{stat}_stage" for stat in STAT_EFFECT_KEYS]
    + ["effect_self_stat_chance"]
)
# --- legal-action-v7 (batch 2): typed volatile effects ---
# Appended after the byte-identical 361D v7 batch-1 prefix (v6 + SLICE8). Confusion
# stays in the batch-1 status slice (not duplicated here).
SLICE9_VOLATILE_FEATURE_NAMES = [
    "effect_target_flinch_chance",
    "effect_target_trap_chance",
    "effect_target_taunt",
    "effect_target_encore",
    "effect_target_disable",
    "effect_target_leech_seed",
    "effect_target_yawn",
    "effect_target_heal_block",
    "effect_target_volatile_other",
    "effect_self_substitute",
    "effect_self_protect",
    "effect_self_destiny_bond",
    "effect_self_magnet_rise",
    "effect_self_volatile_other",
]
# --- legal-action-v7 (batch 3): typed item effects ---
# Appended after the frozen 375D batch-2 prefix. Item-state provenance is emitted
# only for moves whose result actually depends on an item; ordinary moves remain
# all-zero throughout this slice.
SLICE10_ITEM_EFFECT_FEATURE_NAMES = [
    "effect_target_item_removal_chance",
    "effect_target_item_removal_state_known",
    "effect_target_item_removal_state_unknown",
    "effect_knock_off_damage_boost_applied",
    "effect_target_item_known",
    "effect_target_item_unknown",
    "effect_target_item_present",
    "effect_target_berry_eaten_or_stolen",
    "effect_items_swapped",
    "effect_user_item_consumed",
    "effect_target_item_suppressed",
    "effect_all_items_suppressed",
    "effect_item_other",
]
# --- legal-action-v7 (batch 4): typed priority and timing effects ---
# Appended after the frozen 388D batch-3 prefix. Priority values are signed and
# normalized by /7; all other values are booleans except delayed turns (/3).
SLICE11_TIMING_PRIORITY_FEATURE_NAMES = [
    "effect_base_priority_norm",
    "effect_effective_priority_norm",
    "effect_priority_condition_known",
    "effect_priority_boosted_by_terrain",
    "effect_priority_boosted_by_ability",
    "effect_priority_blocked",
    "effect_priority_conditional",
    "effect_requires_charge_turn",
    "effect_charges_this_turn",
    "effect_attacks_this_turn",
    "effect_charge_skipped_by_weather",
    "effect_charge_skipped_by_item",
    "effect_user_must_recharge_next_turn",
    "effect_user_locked_into_move",
    "effect_delayed_future_damage",
    "effect_delayed_damage_turns_norm",
    "effect_timing_unknown",
    "effect_timing_other",
]
# --- legal-action-v7 (batch 5): typed HP side effects ---
# Appended after the frozen 406D batch-4 prefix. Fractions are expressed in
# natural [0,1] units and remain separate from current-turn damage.
SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES = [
    "effect_recoil_damage_fraction",
    "effect_recoil_max_hp_fraction",
    "effect_drain_damage_fraction",
    "effect_user_heal_max_hp_fraction",
    "effect_target_heal_max_hp_fraction",
    "effect_self_damage_max_hp_fraction",
    "effect_hp_cost_max_hp_fraction",
    "effect_crash_damage_max_hp_fraction",
    "effect_hp_condition_known",
    "effect_healing_blocked",
    "effect_hp_cost_blocked",
    "effect_hp_effect_conditional",
    "effect_hp_effect_amount_unknown",
    "effect_hp_effect_other",
]
# --- legal-action-v7 (batch 6): typed field and side effects ---
# Appended after the frozen 420D batch-5 prefix.
SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES = [
    "effect_target_side_stealth_rock_setup",
    "effect_target_side_spikes_setup",
    "effect_target_side_toxic_spikes_setup",
    "effect_target_side_sticky_web_setup",
    "effect_user_side_hazards_removed",
    "effect_target_side_hazards_removed",
    "effect_user_side_reflect_setup",
    "effect_user_side_light_screen_setup",
    "effect_user_side_aurora_veil_setup",
    "effect_target_side_screens_removed",
    "effect_weather_sun_set",
    "effect_weather_rain_set",
    "effect_weather_sand_set",
    "effect_weather_snow_set",
    "effect_terrain_grassy_set",
    "effect_terrain_electric_set",
    "effect_terrain_psychic_set",
    "effect_terrain_misty_set",
    "effect_trick_room_set",
    "effect_magic_room_set",
    "effect_wonder_room_set",
    "effect_gravity_set",
    "effect_user_side_tailwind_setup",
    "effect_user_side_safeguard_setup",
    "effect_user_side_mist_setup",
    "effect_user_side_lucky_chant_setup",
    "effect_terrain_removed",
    "effect_side_conditions_swapped",
    "effect_field_side_condition_known",
    "effect_field_side_effect_blocked",
    "effect_field_side_effect_conditional",
    "effect_field_side_other",
]
# --- legal-action-v7 (batch 7): action risk/probability summaries ---
# Appended after the frozen 452D batch-6 prefix. These are action-selection-time
# summaries only; current-state sleep/confusion counters stay out of action v7.
SLICE14_ACTION_RISK_FEATURE_NAMES = [
    "hit_chance_known",
    "hit_chance",
    "miss_chance",
    "on_hit_damage_available",
    "expected_damage_includes_miss",
    "crit_chance_known",
    "crit_chance",
    "guaranteed_crit",
    "accuracy_context_partial",
    "accuracy_context_unknown",
    "may_fail_due_to_opponent_action",
    "may_fail_due_to_active_turn",
    "may_fail_due_to_target_switch",
    "may_fail_due_to_prior_turn_or_history",
    "may_fail_due_to_priority_prevention",
    "succeeds_if_target_attacks",
    "succeeds_if_target_switches",
    "power_boost_if_target_switches",
    "branch_condition_known",
    "branch_condition_hidden_now",
    "branch_pressure_present",
    "random_call_move",
    "callable_pool_known",
    "callable_count",
    "callable_damaging_count",
    "callable_status_count",
    "callable_avg_base_power",
    "callable_has_priority",
    "callable_has_recovery",
    "callable_has_status",
    "callable_has_phazing_or_forced_switch",
    "callable_pool_depends_on_party",
    "callable_pool_depends_on_last_move",
    "callable_pool_depends_on_sleep_state",
    "callable_pool_depends_on_format_rules",
    "callable_distribution_unknown",
    "random_call_fail_closed",
    "multihit_distribution_known",
    "multihit_min",
    "multihit_max",
    "multihit_expected",
    "sequential_accuracy_stops_on_miss",
    "per_hit_accuracy_known",
    "per_hit_accuracy",
    "per_hit_power_changes",
    "loaded_dice_modified",
    "skill_link_guaranteed",
    "contact_per_hit",
    "multihit_distribution_unknown",
    "delayed_pressure_created",
    "delayed_turns_until_effect",
    "delayed_targets_opp_slot",
    "delayed_damage_deferred_to_rollout",
    "residual_pressure_created",
    "residual_kind_known",
    "residual_duration_known",
    "residual_source_known",
    "binding_pressure_created",
    "future_damage_unknown_now",
]
# --- legal-action-v7 (batch 8): forced decisions and secondary modifiers ---
# Appended after the frozen 511D batch-7 prefix.
SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES = [
    "self_pivot_move",
    "self_pivot_requires_hit",
    "self_pivot_after_damage",
    "self_pivot_after_stat_drop",
    "self_pivot_forces_replacement_decision",
    "self_pivot_may_fail_due_to_immunity_or_miss",
    "self_pivot_branch_known",
    "self_pivot_branch_unknown",
    "user_self_ko_move",
    "user_self_ko_guaranteed",
    "user_self_ko_if_successful",
    "user_self_ko_forces_replacement_decision",
    "user_sacrifice_for_tempo",
    "user_sacrifice_with_healing_wish_effect",
    "user_sacrifice_with_stat_drop_effect",
    "user_sacrifice_damage_based",
    "forces_target_switch",
    "forces_target_switch_if_hits",
    "forced_target_switch_random",
    "forced_target_switch_user_selected",
    "phazing_blocked_by_substitute_possible",
    "phazing_priority_negative",
    "forced_switch_pressure_present",
    "user_item_may_force_self_switch",
    "target_item_may_force_target_switch",
    "eject_button_possible",
    "eject_pack_possible",
    "red_card_possible",
    "item_trigger_branch_known",
    "item_trigger_branch_unknown",
    "secondary_chance_base_known",
    "secondary_chance_base",
    "secondary_chance_modified_known",
    "secondary_chance_modified",
    "secondary_chance_modifier_serene_grace",
    "secondary_chance_blocked_by_shield_dust_possible",
    "secondary_chance_blocked_by_covert_cloak_possible",
    "secondary_removed_by_sheer_force_possible",
    "flinch_chance_modified",
    "status_chance_modified",
    "stat_drop_chance_modified",
]
ACTION_FEATURE_NAMES_V7 = (
    ACTION_FEATURE_NAMES_V6
    + SLICE8_STATUS_STAT_FEATURE_NAMES
    + SLICE9_VOLATILE_FEATURE_NAMES
    + SLICE10_ITEM_EFFECT_FEATURE_NAMES
    + SLICE11_TIMING_PRIORITY_FEATURE_NAMES
    + SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES
    + SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES
    + SLICE14_ACTION_RISK_FEATURE_NAMES
    + SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES
)
ACTION_FEATURE_DIM_V7 = len(ACTION_FEATURE_NAMES_V7)
# The frozen 361D v7 batch-1 prefix (v6 + typed status/stat) and its fingerprint
# must stay byte-identical as later v7 batches append further effect slices.
ACTION_FEATURE_NAMES_V7_BATCH1 = ACTION_FEATURE_NAMES_V6 + SLICE8_STATUS_STAT_FEATURE_NAMES
ACTION_FEATURE_DIM_V7_BATCH1 = len(ACTION_FEATURE_NAMES_V7_BATCH1)
# The frozen 375D v7 batch-2 prefix (v6 + status/stat + volatile).
ACTION_FEATURE_NAMES_V7_BATCH2 = (
    ACTION_FEATURE_NAMES_V6 + SLICE8_STATUS_STAT_FEATURE_NAMES + SLICE9_VOLATILE_FEATURE_NAMES
)
ACTION_FEATURE_DIM_V7_BATCH2 = len(ACTION_FEATURE_NAMES_V7_BATCH2)
# The frozen 388D v7 batch-3 prefix (batch 2 + typed item effects).
ACTION_FEATURE_NAMES_V7_BATCH3 = ACTION_FEATURE_NAMES_V7_BATCH2 + SLICE10_ITEM_EFFECT_FEATURE_NAMES
ACTION_FEATURE_DIM_V7_BATCH3 = len(ACTION_FEATURE_NAMES_V7_BATCH3)
# The frozen 406D v7 batch-4 prefix (batch 3 + typed priority/timing).
ACTION_FEATURE_NAMES_V7_BATCH4 = ACTION_FEATURE_NAMES_V7_BATCH3 + SLICE11_TIMING_PRIORITY_FEATURE_NAMES
ACTION_FEATURE_DIM_V7_BATCH4 = len(ACTION_FEATURE_NAMES_V7_BATCH4)
# The frozen 420D v7 batch-5 prefix (batch 4 + typed HP side effects).
ACTION_FEATURE_NAMES_V7_BATCH5 = ACTION_FEATURE_NAMES_V7_BATCH4 + SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES
ACTION_FEATURE_DIM_V7_BATCH5 = len(ACTION_FEATURE_NAMES_V7_BATCH5)
# The frozen 452D v7 batch-6 prefix (batch 5 + typed field/side effects).
ACTION_FEATURE_NAMES_V7_BATCH6 = ACTION_FEATURE_NAMES_V7_BATCH5 + SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES
ACTION_FEATURE_DIM_V7_BATCH6 = len(ACTION_FEATURE_NAMES_V7_BATCH6)
# The frozen 511D v7 batch-7 prefix (batch 6 + action risk/probability).
ACTION_FEATURE_NAMES_V7_BATCH7 = ACTION_FEATURE_NAMES_V7_BATCH6 + SLICE14_ACTION_RISK_FEATURE_NAMES
ACTION_FEATURE_DIM_V7_BATCH7 = len(ACTION_FEATURE_NAMES_V7_BATCH7)


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


@lru_cache(maxsize=1)
def _raw_move_blocks() -> Dict[str, str]:
    for path in _move_data_candidates():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        blocks: Dict[str, str] = {}
        pattern = re.compile(r"\n\s*([a-z0-9]+)\s*:\s*\{")
        position = 0
        while True:
            match = pattern.search(text, position)
            if not match:
                break
            move_id = match.group(1)
            block, position = _extract_object_block(text, match.end() - 1)
            if block:
                blocks[move_id] = block
        return blocks
    return {}


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
    if (
        base_power > 0
        or move_id in VARIABLE_POWER_DAMAGE_MOVE_IDS
        or move_id in FIXED_DAMAGE_ORACLE_MOVE_IDS
        or move_id in FIXED_DAMAGE_FAIL_CLOSED_MOVE_IDS
    ):
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
    tactical_state: Optional[Dict[str, Any]] = None,
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
    if to_id(name) == "curse":
        tactical = tactical_state if isinstance(tactical_state, dict) else {}
        own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
        active = _active_team_member(private)
        current_types = own.get("active_current_types") or active.get("types") or []
        if any(str(value).lower() == "ghost" for value in current_types):
            self_delta = {}
            target_delta = {}
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
    slice5 = slice5_action_feature_vector(action, private_state, tactical_state)
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
    from .action_side_effects import move_next_state_effects, move_side_effects, move_stat_deltas

    kind = str(action.get("kind") or "").lower()
    is_switch = kind == "switch"
    is_move = kind.startswith("move")
    name = _action_name(action)
    category = classify_action_category(action)
    meta_index, _ = load_move_metadata()
    meta = meta_index.get(to_id(name), {}) if is_move else {}
    se = move_side_effects(name) if is_move else {}
    deltas = move_stat_deltas(name) if is_move else {"self": {}, "target": {}}
    # Batch 2: coarse secondary/status/volatile presence fills the existing
    # next-state change flags so a real effect is not encoded as a wrong-exact
    # "no change". Booleans only; exact type/chance/magnitude stay unrepresented.
    nse = (
        move_next_state_effects(name)
        if is_move
        else {"opp_status_or_volatile": False, "opp_stat_change": False, "own_status_or_volatile": False, "own_stat_change": False}
    )

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
        is_move
        and (
            category == "hazard"
            or removal
            or meta.get("has_side_condition")
            or to_id(name) in SCREEN_BREAK_ON_HIT_MOVE_IDS
        )
    )
    values.extend(
        [
            max(-1.0, min(1.0, float(_impact_get(imp, "next_opp_hp_delta")))),
            max(-1.0, min(1.0, float(_impact_get(imp, "next_own_hp_delta")))),
            float(bool(_impact_get(imp, "next_own_hp_delta_known"))),
            float(bool(deltas.get("self")) or nse["own_stat_change"]),
            float(bool(deltas.get("target")) or nse["opp_stat_change"]),
            float(bool(_impact_get(imp, "next_own_status_change")) or nse["own_status_or_volatile"]),
            float(bool(_impact_get(imp, "next_opp_status_change")) or nse["opp_status_or_volatile"]),
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


def slice7_repeat_chain_feature_vector(
    action: Dict[str, Any],
    tactical_state: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """Append-only repeat-chain context for Rollout and Fury Cutter."""
    move_id = to_id(_action_name(action))
    is_rollout = move_id == "rollout"
    is_fury_cutter = move_id == "furycutter"
    if not (is_rollout or is_fury_cutter):
        return np.zeros(len(SLICE7_ACTION_FEATURE_NAMES), dtype=np.float32)

    tactical = tactical_state if isinstance(tactical_state, dict) else {}
    own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
    chain = own.get("repeat_chain") if isinstance(own.get("repeat_chain"), dict) else {}
    known = bool(chain.get("known"))
    exact = bool(chain.get("exact")) and known
    provenance = str(chain.get("provenance") or "unknown")
    chain_move = to_id(chain.get("move"))
    matches = chain_move == move_id
    count = int(chain.get("successful_count", 0) or 0) if known and matches else 0
    multiplier = float(chain.get("multiplier", 1.0) or 1.0) if known and matches else 1.0
    if provenance not in {"protocol_complete", "inferred_lower_bound", "unknown"}:
        provenance = "unknown"
    if not known:
        provenance = "unknown"

    values = [
        float(is_rollout),
        float(is_fury_cutter),
        _clip(count / 4.0),
        _clip(multiplier / 32.0),
        float(known),
        float(exact),
        float(provenance == "protocol_complete"),
        float(provenance == "inferred_lower_bound"),
        float(provenance == "unknown"),
        float(bool(chain.get("reset_observed"))),
        float(is_rollout and bool(chain.get("defense_curl_active"))),
        float(is_rollout and bool(chain.get("defense_curl_known"))),
        float(is_rollout and bool(chain.get("forced_continuation_active"))),
    ]
    return np.asarray(values, dtype=np.float32)


def build_action_feature_vector_v6(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
    impact: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v6 = unchanged v5 prefix + repeat-chain context."""
    base = build_action_feature_vector_v5(action, private_state, tactical_state, impact)
    slice7 = slice7_repeat_chain_feature_vector(action, tactical_state)
    features = np.concatenate([base, slice7]).astype(np.float32)
    if features.shape[0] != ACTION_FEATURE_DIM_V6:
        raise ValueError(
            f"Action v6 feature size mismatch: got {features.shape[0]}, expected {ACTION_FEATURE_DIM_V6}."
        )
    return features


def slice8_typed_status_stat_feature_vector(action: Dict[str, Any]) -> np.ndarray:
    """legal-action-v7 batch 1: typed status chances + stat-stage deltas.

    Status fields carry the probability of each condition (e.g. 0.30 for a 30%
    burn, not 1.0); guaranteed-status moves carry 1.0. Stat fields carry the signed
    stage (normalized by /6) and a per-side application chance. Switches and
    non-move actions, and ordinary moves with no such effect, are all zero. Derives
    only from move metadata (the oracle), independent of impact/state.
    """
    from .action_side_effects import move_typed_effects

    kind = str(action.get("kind") or "").lower()
    if not kind.startswith("move"):
        return np.zeros(len(SLICE8_STATUS_STAT_FEATURE_NAMES), dtype=np.float32)

    eff = move_typed_effects(_action_name(action))
    target_status = eff["target_status"]
    self_status = eff["self_status"]
    target_stat = eff["target_stat"]
    self_stat = eff["self_stat"]

    def _stage(stages: Dict[str, Any], stat: str) -> float:
        return max(-1.0, min(1.0, float(stages.get(stat, 0)) / 6.0))

    values: List[float] = []
    values.extend(_clip(float(target_status.get(key, 0.0))) for key in STATUS_EFFECT_KEYS)
    values.extend(_clip(float(self_status.get(key, 0.0))) for key in STATUS_EFFECT_KEYS)
    values.extend(_stage(target_stat["stages"], stat) for stat in STAT_EFFECT_KEYS)
    values.append(_clip(float(target_stat["chance"])))
    values.extend(_stage(self_stat["stages"], stat) for stat in STAT_EFFECT_KEYS)
    values.append(_clip(float(self_stat["chance"])))

    vector = np.asarray(values, dtype=np.float32)
    if vector.shape[0] != len(SLICE8_STATUS_STAT_FEATURE_NAMES):
        raise ValueError(
            f"Action v7 slice-8 size mismatch: got {vector.shape[0]}, "
            f"expected {len(SLICE8_STATUS_STAT_FEATURE_NAMES)}."
        )
    return vector


def slice9_typed_volatile_feature_vector(action: Dict[str, Any]) -> np.ndarray:
    """legal-action-v7 batch 2: typed volatile effects.

    Flinch carries its secondary probability; guaranteed-on-hit volatiles are 1.0.
    Switches and non-move actions, and ordinary moves with no volatile, are zero.
    Derives only from move metadata (the oracle).
    """
    from .action_side_effects import move_volatile_effects

    kind = str(action.get("kind") or "").lower()
    if not kind.startswith("move"):
        return np.zeros(len(SLICE9_VOLATILE_FEATURE_NAMES), dtype=np.float32)

    fields = move_volatile_effects(_action_name(action))
    vector = np.asarray(
        [_clip(float(fields.get(name, 0.0))) for name in SLICE9_VOLATILE_FEATURE_NAMES],
        dtype=np.float32,
    )
    if vector.shape[0] != len(SLICE9_VOLATILE_FEATURE_NAMES):
        raise ValueError(
            f"Action v7 slice-9 size mismatch: got {vector.shape[0]}, "
            f"expected {len(SLICE9_VOLATILE_FEATURE_NAMES)}."
        )
    return vector


def slice10_typed_item_effect_feature_vector(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v7 batch 3: typed current-turn and next-state item effects.

    Move semantics come from bundled Showdown metadata. Item identity/state comes
    from the existing private/tactical battle snapshots. Unknown target state is
    surfaced explicitly and never treated as a held item.
    """
    from .action_side_effects import item_is_berry, move_item_effects

    kind = str(action.get("kind") or "").lower()
    if not kind.startswith("move"):
        return np.zeros(len(SLICE10_ITEM_EFFECT_FEATURE_NAMES), dtype=np.float32)

    semantics = move_item_effects(_action_name(action))
    if not any(bool(value) for value in semantics.values()):
        return np.zeros(len(SLICE10_ITEM_EFFECT_FEATURE_NAMES), dtype=np.float32)

    tactical = tactical_state if isinstance(tactical_state, dict) else {}
    opponent = tactical.get("opponent") if isinstance(tactical.get("opponent"), dict) else {}
    target_state = str(opponent.get("active_item_state") or "unknown").lower()
    target_item = to_id(opponent.get("active_item"))
    target_known = target_state in {"held", "none", "removed", "consumed"} or bool(target_item)
    target_present = bool(target_item) or target_state == "held"

    own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
    own_item = to_id(own.get("active_item"))
    own_state = str(own.get("active_item_state") or "unknown").lower()
    private = private_state if isinstance(private_state, dict) else {}
    team = private.get("team") if isinstance(private.get("team"), list) else []
    active = next((mon for mon in team if isinstance(mon, dict) and mon.get("active")), {})
    if active:
        own_item = to_id(active.get("item"))
        own_state = str(active.get("item_state") or ("held" if own_item else "none")).lower()
    own_power_herb = own_item == "powerherb" and own_state == "held"

    target_relevant = bool(
        semantics.get("removes_target_item")
        or semantics.get("eats_target_berry")
        or semantics.get("swaps_items")
    )
    removal_known = bool(semantics.get("removes_target_item") and target_known)
    removal_unknown = bool(semantics.get("removes_target_item") and not target_known)
    removal_chance = float(removal_known and target_present)
    berry_eaten = bool(
        semantics.get("eats_target_berry")
        and target_known
        and target_present
        and item_is_berry(target_item)
    )
    user_consumed = bool(semantics.get("charge_move") and own_power_herb)

    fields = {
        "effect_target_item_removal_chance": removal_chance,
        "effect_target_item_removal_state_known": float(removal_known),
        "effect_target_item_removal_state_unknown": float(removal_unknown),
        "effect_knock_off_damage_boost_applied": float(
            semantics.get("knock_off") and target_known and target_present
        ),
        "effect_target_item_known": float(target_relevant and target_known),
        "effect_target_item_unknown": float(target_relevant and not target_known),
        "effect_target_item_present": float(target_relevant and target_known and target_present),
        "effect_target_berry_eaten_or_stolen": float(berry_eaten),
        "effect_items_swapped": float(semantics.get("swaps_items")),
        "effect_user_item_consumed": float(user_consumed),
        "effect_target_item_suppressed": float(semantics.get("suppresses_target_item")),
        "effect_all_items_suppressed": float(semantics.get("suppresses_all_items")),
        "effect_item_other": float(semantics.get("item_other")),
    }
    vector = np.asarray(
        [_clip(float(fields.get(name, 0.0))) for name in SLICE10_ITEM_EFFECT_FEATURE_NAMES],
        dtype=np.float32,
    )
    if vector.shape[0] != len(SLICE10_ITEM_EFFECT_FEATURE_NAMES):
        raise ValueError(
            f"Action v7 slice-10 size mismatch: got {vector.shape[0]}, "
            f"expected {len(SLICE10_ITEM_EFFECT_FEATURE_NAMES)}."
        )
    return vector


def _active_mon(private_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    private = private_state if isinstance(private_state, dict) else {}
    team = private.get("team") if isinstance(private.get("team"), list) else []
    return next(
        (mon for mon in team if isinstance(mon, dict) and mon.get("active")),
        team[0] if team and isinstance(team[0], dict) else {},
    )


def _grounded_state(
    side: Dict[str, Any],
    fallback_mon: Optional[Dict[str, Any]] = None,
) -> Optional[bool]:
    """Return proven grounded/airborne state, or None when reconstruction is insufficient."""
    mon = fallback_mon if isinstance(fallback_mon, dict) else {}
    volatiles = {to_id(value) for value in (side.get("volatiles") or [])}
    item = to_id(side.get("active_item") or mon.get("item"))
    ability = to_id(
        side.get("active_current_ability")
        or side.get("active_base_ability")
        or mon.get("ability")
        or mon.get("base_ability")
    )
    types = side.get("active_current_types") or side.get("active_base_types") or mon.get("types") or []
    type_ids = {to_id(value) for value in types}

    if {"smackdown", "ingrain"} & volatiles or item == "ironball":
        return True
    if {"magnetrise", "telekinesis"} & volatiles or item == "airballoon":
        return False
    if "flying" in type_ids or ability == "levitate":
        return False
    if type_ids:
        return True
    return None


def slice11_typed_timing_priority_feature_vector(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v7 batch 4: typed priority, charge, lock and delayed timing."""
    from .action_side_effects import move_timing_effects

    kind = str(action.get("kind") or "").lower()
    if not kind.startswith("move"):
        return np.zeros(len(SLICE11_TIMING_PRIORITY_FEATURE_NAMES), dtype=np.float32)

    timing = move_timing_effects(_action_name(action))
    base_priority = int(timing.get("base_priority", 0) or 0)
    effective_priority = base_priority
    tactical_present = isinstance(tactical_state, dict)
    tactical = tactical_state if tactical_present else {}
    own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
    opponent = tactical.get("opponent") if isinstance(tactical.get("opponent"), dict) else {}
    active = _active_mon(private_state)

    priority_dynamic = False
    priority_known = True
    terrain_boost = False
    ability_boost = False
    priority_blocked = False
    priority_conditional = False

    move_id = to_id(_action_name(action))
    terrain = to_id(tactical.get("terrain"))
    if move_id == "grassyglide":
        priority_dynamic = True
        if not tactical_present:
            priority_known = False
        elif terrain != "grassyterrain":
            priority_known = True
        else:
            grounded = _grounded_state(own, active)
            priority_known = grounded is not None
            if grounded:
                effective_priority += 1
                terrain_boost = True

    ability = to_id(
        own.get("active_current_ability")
        or own.get("active_base_ability")
        or active.get("ability")
        or active.get("base_ability")
    )
    if ability == "prankster" and timing.get("category") == "status":
        priority_dynamic = True
        effective_priority += 1
        ability_boost = True
    elif ability == "triage" and timing.get("heal_flag"):
        priority_dynamic = True
        effective_priority += 3
        ability_boost = True
    elif ability == "galewings" and to_id(timing.get("type")) == "flying":
        priority_dynamic = True
        hp = own.get("active_hp_fraction", active.get("hp_fraction"))
        if hp is None:
            priority_known = False
        elif abs(float(hp) - 1.0) < 1e-9:
            effective_priority += 1
            ability_boost = True

    # Psychic Terrain blocks positive-priority moves against a grounded target.
    if effective_priority > 0 and terrain == "psychicterrain":
        target_grounded = _grounded_state(opponent)
        priority_dynamic = True
        if target_grounded is None:
            priority_known = False
            priority_conditional = True
        elif target_grounded:
            priority_blocked = True

    requires_charge = bool(timing.get("requires_charge"))
    delayed_future = bool(timing.get("delayed_future_damage"))
    charges_this_turn = False
    attacks_this_turn = False
    skipped_weather = False
    skipped_item = False
    timing_unknown = False

    own_item = to_id(active.get("item") or own.get("active_item"))
    own_item_known = bool(active) or str(own.get("active_item_state") or "unknown") in {
        "held",
        "none",
        "removed",
        "consumed",
    }
    has_power_herb = own_item == "powerherb" and not bool(own.get("active_item_suppressed"))

    if delayed_future:
        attacks_this_turn = False
    elif requires_charge:
        weather_known = tactical_present
        solar_weather_skip = move_id in {"solarbeam", "solarblade"} and to_id(tactical.get("weather")) in {
            "sunnyday",
            "sun",
            "desolateland",
        }
        if has_power_herb:
            attacks_this_turn = True
            skipped_item = True
        elif solar_weather_skip:
            attacks_this_turn = True
            skipped_weather = True
        elif own_item_known and (weather_known or move_id not in {"solarbeam", "solarblade"}):
            charges_this_turn = True
        else:
            timing_unknown = True

    if priority_dynamic and not priority_known:
        priority_conditional = True

    def _priority_norm(value: int) -> float:
        return max(-1.0, min(1.0, float(value) / 7.0))

    fields = {
        "effect_base_priority_norm": _priority_norm(base_priority),
        "effect_effective_priority_norm": _priority_norm(effective_priority),
        "effect_priority_condition_known": float(priority_dynamic and priority_known),
        "effect_priority_boosted_by_terrain": float(terrain_boost),
        "effect_priority_boosted_by_ability": float(ability_boost),
        "effect_priority_blocked": float(priority_blocked),
        "effect_priority_conditional": float(priority_conditional),
        "effect_requires_charge_turn": float(requires_charge),
        "effect_charges_this_turn": float(charges_this_turn),
        "effect_attacks_this_turn": float(attacks_this_turn),
        "effect_charge_skipped_by_weather": float(skipped_weather),
        "effect_charge_skipped_by_item": float(skipped_item),
        "effect_user_must_recharge_next_turn": float(timing.get("must_recharge")),
        "effect_user_locked_into_move": float(timing.get("locks_user")),
        "effect_delayed_future_damage": float(delayed_future),
        "effect_delayed_damage_turns_norm": float(timing.get("delayed_turns", 0) or 0) / 3.0,
        "effect_timing_unknown": float(timing_unknown),
        "effect_timing_other": float(timing.get("timing_other")),
    }
    vector = np.asarray(
        [float(fields.get(name, 0.0)) for name in SLICE11_TIMING_PRIORITY_FEATURE_NAMES],
        dtype=np.float32,
    )
    if vector.shape[0] != len(SLICE11_TIMING_PRIORITY_FEATURE_NAMES):
        raise ValueError(
            f"Action v7 slice-11 size mismatch: got {vector.shape[0]}, "
            f"expected {len(SLICE11_TIMING_PRIORITY_FEATURE_NAMES)}."
        )
    return vector


def slice12_typed_hp_side_effect_feature_vector(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v7 batch 5: typed recoil, drain, healing, cost and crash effects."""
    from .action_side_effects import move_hp_side_effects

    kind = str(action.get("kind") or "").lower()
    if not kind.startswith("move"):
        return np.zeros(len(SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES), dtype=np.float32)

    effect = move_hp_side_effects(_action_name(action))
    if not any(bool(value) for value in effect.values()):
        return np.zeros(len(SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES), dtype=np.float32)

    tactical_present = isinstance(tactical_state, dict)
    tactical = tactical_state if tactical_present else {}
    own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
    opponent = tactical.get("opponent") if isinstance(tactical.get("opponent"), dict) else {}
    active = _active_mon(private_state)
    move_id = to_id(_action_name(action))

    user_heal = float(effect.get("user_heal_max_hp_fraction", 0.0) or 0.0)
    target_heal = float(effect.get("target_heal_max_hp_fraction", 0.0) or 0.0)
    condition_known = False
    conditional = bool(effect.get("conditional"))
    amount_unknown = bool(effect.get("amount_unknown"))

    weather = to_id(tactical.get("weather"))
    terrain = to_id(tactical.get("terrain"))
    ability = to_id(
        own.get("active_current_ability")
        or own.get("active_base_ability")
        or active.get("ability")
        or active.get("base_ability")
    )

    if move_id in {"moonlight", "morningsun", "synthesis"}:
        conditional = True
        if tactical_present:
            condition_known = True
            if weather in {"sunnyday", "sun", "desolateland"}:
                user_heal = 0.667
            elif weather in {"raindance", "rain", "primordialsea", "sandstorm", "hail", "snow", "snowscape"}:
                user_heal = 0.25
            else:
                user_heal = 0.5
        else:
            amount_unknown = True
    elif move_id == "shoreup":
        conditional = True
        if tactical_present:
            condition_known = True
            user_heal = 0.667 if weather == "sandstorm" else 0.5
        else:
            amount_unknown = True
    elif move_id == "healpulse":
        conditional = True
        condition_known = bool(ability)
        target_heal = 0.75 if ability == "megalauncher" else 0.5
        amount_unknown = not condition_known
    elif move_id == "floralhealing":
        conditional = True
        if tactical_present:
            condition_known = True
            target_heal = 0.667 if terrain == "grassyterrain" else 0.5
        else:
            amount_unknown = True

    hp_cost = float(effect.get("hp_cost_max_hp_fraction", 0.0) or 0.0)
    hp_cost_blocked = False
    if hp_cost:
        conditional = True
        hp = own.get("active_hp_fraction", active.get("hp_fraction"))
        if hp is not None:
            condition_known = True
            hp_cost_blocked = float(hp) <= hp_cost

    own_constraints = {
        to_id(value)
        for value in list(own.get("constraint_volatiles") or []) + list(own.get("volatiles") or [])
    }
    target_constraints = {
        to_id(value)
        for value in list(opponent.get("constraint_volatiles") or []) + list(opponent.get("volatiles") or [])
    }
    healing_blocked = bool(
        (user_heal or effect.get("drain_damage_fraction")) and "healblock" in own_constraints
    ) or bool(target_heal and "healblock" in target_constraints)

    fields = {
        "effect_recoil_damage_fraction": effect.get("recoil_damage_fraction", 0.0),
        "effect_recoil_max_hp_fraction": effect.get("recoil_max_hp_fraction", 0.0),
        "effect_drain_damage_fraction": effect.get("drain_damage_fraction", 0.0),
        "effect_user_heal_max_hp_fraction": user_heal,
        "effect_target_heal_max_hp_fraction": target_heal,
        "effect_self_damage_max_hp_fraction": effect.get("self_damage_max_hp_fraction", 0.0),
        "effect_hp_cost_max_hp_fraction": hp_cost,
        "effect_crash_damage_max_hp_fraction": effect.get("crash_damage_max_hp_fraction", 0.0),
        "effect_hp_condition_known": float(condition_known),
        "effect_healing_blocked": float(healing_blocked),
        "effect_hp_cost_blocked": float(hp_cost_blocked),
        "effect_hp_effect_conditional": float(conditional),
        "effect_hp_effect_amount_unknown": float(amount_unknown),
        "effect_hp_effect_other": float(effect.get("hp_effect_other")),
    }
    vector = np.asarray(
        [_clip(float(fields.get(name, 0.0))) for name in SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES],
        dtype=np.float32,
    )
    if vector.shape[0] != len(SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES):
        raise ValueError(
            f"Action v7 slice-12 size mismatch: got {vector.shape[0]}, "
            f"expected {len(SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES)}."
        )
    return vector


def slice13_typed_field_side_effect_feature_vector(
    action: Dict[str, Any],
    tactical_state: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v7 batch 6: typed hazards, screens, weather, terrain and rooms."""
    from .action_side_effects import move_field_side_effects

    kind = str(action.get("kind") or "").lower()
    if not kind.startswith("move"):
        return np.zeros(len(SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES), dtype=np.float32)

    effect = move_field_side_effects(_action_name(action))
    if not any(bool(value) for value in effect.values()):
        return np.zeros(len(SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES), dtype=np.float32)

    tactical_present = isinstance(tactical_state, dict)
    tactical = tactical_state if tactical_present else {}
    weather = to_id(tactical.get("weather"))
    move_id = to_id(_action_name(action))
    condition_known = False
    blocked = False
    conditional = bool(effect.get("conditional"))

    if move_id == "auroraveil":
        conditional = True
        if tactical_present:
            condition_known = True
            blocked = weather not in {"hail", "snow", "snowscape"}

    fields = {
        "effect_target_side_stealth_rock_setup": effect.get("target_stealthrock", 0.0),
        "effect_target_side_spikes_setup": effect.get("target_spikes", 0.0),
        "effect_target_side_toxic_spikes_setup": effect.get("target_toxicspikes", 0.0),
        "effect_target_side_sticky_web_setup": effect.get("target_stickyweb", 0.0),
        "effect_user_side_hazards_removed": effect.get("remove_user_hazards", 0.0),
        "effect_target_side_hazards_removed": effect.get("remove_target_hazards", 0.0),
        "effect_user_side_reflect_setup": effect.get("user_reflect", 0.0),
        "effect_user_side_light_screen_setup": effect.get("user_lightscreen", 0.0),
        "effect_user_side_aurora_veil_setup": effect.get("user_auroraveil", 0.0),
        "effect_target_side_screens_removed": effect.get("remove_target_screens", 0.0),
        "effect_weather_sun_set": effect.get("weather_sun", 0.0),
        "effect_weather_rain_set": effect.get("weather_rain", 0.0),
        "effect_weather_sand_set": effect.get("weather_sand", 0.0),
        "effect_weather_snow_set": effect.get("weather_snow", 0.0),
        "effect_terrain_grassy_set": effect.get("terrain_grassy", 0.0),
        "effect_terrain_electric_set": effect.get("terrain_electric", 0.0),
        "effect_terrain_psychic_set": effect.get("terrain_psychic", 0.0),
        "effect_terrain_misty_set": effect.get("terrain_misty", 0.0),
        "effect_trick_room_set": effect.get("trickroom", 0.0),
        "effect_magic_room_set": effect.get("magicroom", 0.0),
        "effect_wonder_room_set": effect.get("wonderroom", 0.0),
        "effect_gravity_set": effect.get("gravity", 0.0),
        "effect_user_side_tailwind_setup": effect.get("user_tailwind", 0.0),
        "effect_user_side_safeguard_setup": effect.get("user_safeguard", 0.0),
        "effect_user_side_mist_setup": effect.get("user_mist", 0.0),
        "effect_user_side_lucky_chant_setup": effect.get("user_luckychant", 0.0),
        "effect_terrain_removed": effect.get("remove_terrain", 0.0),
        "effect_side_conditions_swapped": effect.get("swap_side_conditions", 0.0),
        "effect_field_side_condition_known": float(condition_known),
        "effect_field_side_effect_blocked": float(blocked),
        "effect_field_side_effect_conditional": float(conditional),
        "effect_field_side_other": effect.get("field_side_other", 0.0),
    }
    vector = np.asarray(
        [_clip(float(fields.get(name, 0.0))) for name in SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES],
        dtype=np.float32,
    )
    if vector.shape[0] != len(SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES):
        raise ValueError(
            f"Action v7 slice-13 size mismatch: got {vector.shape[0]}, "
            f"expected {len(SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES)}."
        )
    return vector


def _weather_hit_chance_for_move(move_id: str, accuracy: Optional[float], tactical_state: Optional[Dict[str, Any]]) -> Tuple[float, bool, bool, bool]:
    if accuracy is None:
        return 1.0, False, False, True
    if move_id not in WEATHER_DEPENDENT_ACCURACY_MOVE_IDS:
        return _clip(float(accuracy) / 100.0), True, False, False
    if not isinstance(tactical_state, dict):
        return _clip(float(accuracy) / 100.0), False, True, True
    weather = to_id(tactical_state.get("weather"))
    if move_id == "blizzard" and weather in {"hail", "snow", "snowscape"}:
        return 1.0, True, False, False
    if move_id in {"thunder", "hurricane"}:
        if weather in {"raindance", "rain", "primordialsea"}:
            return 1.0, True, False, False
        if weather in {"sunnyday", "sun", "desolateland"}:
            return 0.5, True, False, False
    return _clip(float(accuracy) / 100.0), True, True, False


def _crit_chance_for_move(move_id: str, block: str, damaging: bool) -> Tuple[bool, float, bool]:
    if not damaging:
        return True, 0.0, False
    guaranteed = move_id in GUARANTEED_CRIT_MOVE_IDS or bool(re.search(r"\bwillCrit\s*:\s*true", block))
    if guaranteed:
        return True, 1.0, True
    ratio = int(_field_number(block, "critRatio") or 1)
    if ratio <= 1:
        return True, 1.0 / 24.0, False
    if ratio == 2:
        return True, 1.0 / 8.0, False
    if ratio == 3:
        return True, 0.5, False
    return True, 1.0, True


def _active_item_ability(
    private_state: Optional[Dict[str, Any]],
    tactical_state: Optional[Dict[str, Any]],
) -> Tuple[str, str]:
    tactical = tactical_state if isinstance(tactical_state, dict) else {}
    own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
    active = _active_mon(private_state)
    item = to_id(active.get("item") or own.get("active_item"))
    ability = to_id(
        own.get("active_current_ability")
        or own.get("active_base_ability")
        or active.get("ability")
        or active.get("base_ability")
    )
    return item, ability


def _parse_multihit(block: str) -> Optional[Tuple[int, int, bool]]:
    array_match = re.search(r"\bmultihit\s*:\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]", block)
    if array_match:
        return int(array_match.group(1)), int(array_match.group(2)), True
    number_match = re.search(r"\bmultihit\s*:\s*(\d+)", block)
    if number_match:
        value = int(number_match.group(1))
        return value, value, False
    return None


def _expected_hits_for_sequential(max_hits: int, hit_chance: float) -> float:
    chance = _clip(hit_chance)
    return sum(chance ** hit for hit in range(1, max_hits + 1))


def _callable_pool_summary(move_ids: Sequence[str]) -> Dict[str, float]:
    metadata, _ = load_move_metadata()
    ids = [to_id(move_id) for move_id in move_ids if to_id(move_id) in metadata]
    count = len(ids)
    if not count:
        return {
            "callable_count": 0.0,
            "callable_damaging_count": 0.0,
            "callable_status_count": 0.0,
            "callable_avg_base_power": 0.0,
            "callable_has_priority": 0.0,
            "callable_has_recovery": 0.0,
            "callable_has_status": 0.0,
            "callable_has_phazing_or_forced_switch": 0.0,
        }
    damaging = 0
    status = 0
    total_bp = 0.0
    has_priority = False
    has_recovery = False
    has_status = False
    has_phazing = False
    for move_id in ids:
        meta = metadata.get(move_id) or {}
        flags = set(meta.get("flags") or [])
        category = str(meta.get("category") or "").lower()
        base_power = float(meta.get("base_power", 0.0) or 0.0)
        total_bp += base_power
        if category != "status" and base_power > 0:
            damaging += 1
        if category == "status":
            status += 1
        has_priority = has_priority or int(float(meta.get("priority", 0.0) or 0.0)) > 0
        has_recovery = has_recovery or bool(meta.get("has_heal") or meta.get("has_drain") or "heal" in flags)
        block = _raw_move_blocks().get(move_id, "")
        has_status = has_status or category == "status" or bool(re.search(r"\b(status|volatileStatus)\s*:", block))
        has_phazing = has_phazing or move_id in PHASING_OR_FORCED_SWITCH_MOVE_IDS
    return {
        "callable_count": float(count),
        "callable_damaging_count": float(damaging),
        "callable_status_count": float(status),
        "callable_avg_base_power": total_bp / float(count),
        "callable_has_priority": float(has_priority),
        "callable_has_recovery": float(has_recovery),
        "callable_has_status": float(has_status),
        "callable_has_phazing_or_forced_switch": float(has_phazing),
    }


def _known_active_move_ids(private_state: Optional[Dict[str, Any]]) -> List[str]:
    private = private_state if isinstance(private_state, dict) else {}
    out: List[str] = []
    for move in _active_moves(private):
        move_id = to_id(move.get("id") or move.get("name") or move.get("move"))
        if move_id:
            out.append(move_id)
    active = _active_mon(private)
    for move in active.get("moves") or []:
        move_id = to_id(move.get("id") if isinstance(move, dict) else move)
        if move_id and move_id not in out:
            out.append(move_id)
    return out


def _nature_power_called_move(tactical_state: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(tactical_state, dict):
        return None
    terrain = to_id(tactical_state.get("terrain"))
    if terrain == "electricterrain":
        return "thunderbolt"
    if terrain == "grassyterrain":
        return "energyball"
    if terrain == "mistyterrain":
        return "moonblast"
    if terrain == "psychicterrain":
        return "psychic"
    return "triattack"


def _apply_random_call_fields(
    fields: Dict[str, float],
    move_id: str,
    private_state: Optional[Dict[str, Any]],
    tactical_state: Optional[Dict[str, Any]],
) -> None:
    metadata, _ = load_move_metadata()
    if move_id == "metronome":
        pool = [mid for mid, meta in metadata.items() if "metronome" in set(meta.get("flags") or [])]
        fields.update(_callable_pool_summary(pool))
        fields["random_call_move"] = 1.0
        fields["callable_pool_known"] = 1.0
        return
    if move_id == "sleeptalk":
        active_pool = []
        for mid in _known_active_move_ids(private_state):
            flags = set((metadata.get(mid) or {}).get("flags") or [])
            if mid != "sleeptalk" and "nosleeptalk" not in flags and "charge" not in flags:
                active_pool.append(mid)
        fields["random_call_move"] = 1.0
        fields["callable_pool_depends_on_sleep_state"] = 1.0
        if active_pool:
            fields.update(_callable_pool_summary(active_pool))
            fields["callable_pool_known"] = 1.0
        else:
            fields["callable_distribution_unknown"] = 1.0
            fields["random_call_fail_closed"] = 1.0
        return
    if move_id == "naturepower":
        called = _nature_power_called_move(tactical_state)
        fields["random_call_move"] = 1.0
        if called:
            fields.update(_callable_pool_summary([called]))
            fields["callable_pool_known"] = 1.0
        else:
            fields["callable_distribution_unknown"] = 1.0
            fields["random_call_fail_closed"] = 1.0
        return
    if move_id == "copycat":
        fields["random_call_move"] = 1.0
        fields["callable_pool_depends_on_last_move"] = 1.0
        fields["callable_distribution_unknown"] = 1.0
        fields["random_call_fail_closed"] = 1.0
        return
    if move_id == "mirrormove":
        fields["random_call_move"] = 1.0
        fields["callable_pool_depends_on_last_move"] = 1.0
        fields["callable_distribution_unknown"] = 1.0
        fields["random_call_fail_closed"] = 1.0
        return
    if move_id == "assist":
        fields["random_call_move"] = 1.0
        fields["callable_pool_depends_on_party"] = 1.0
        fields["callable_pool_depends_on_format_rules"] = 1.0
        fields["callable_distribution_unknown"] = 1.0
        fields["random_call_fail_closed"] = 1.0
        return
    if move_id == "beatup":
        fields["callable_pool_depends_on_party"] = 1.0
        fields["callable_distribution_unknown"] = 1.0
        fields["random_call_fail_closed"] = 1.0
        return
    if move_id == "ficklebeam":
        fields["callable_distribution_unknown"] = 1.0
        fields["random_call_fail_closed"] = 1.0


def _apply_multihit_fields(
    fields: Dict[str, float],
    move_id: str,
    block: str,
    hit_chance: float,
    hit_chance_known: bool,
    private_state: Optional[Dict[str, Any]],
    tactical_state: Optional[Dict[str, Any]],
) -> None:
    parsed = _parse_multihit(block)
    if parsed is None:
        return
    min_hits, max_hits, is_range = parsed
    sequential = bool(re.search(r"\bmultiaccuracy\s*:\s*true", block))
    item, ability = _active_item_ability(private_state, tactical_state)
    loaded_dice = item == "loadeddice"
    skill_link = ability == "skilllink"

    fields["contact_per_hit"] = float("contact" in set((load_move_metadata()[0].get(move_id) or {}).get("flags") or []))
    fields["per_hit_power_changes"] = float("move.hit" in block)
    fields["loaded_dice_modified"] = float(loaded_dice)
    fields["skill_link_guaranteed"] = float(skill_link)

    if skill_link:
        fields["multihit_min"] = float(max_hits)
        fields["multihit_max"] = float(max_hits)
        fields["multihit_expected"] = float(max_hits)
        fields["multihit_distribution_known"] = 1.0
        fields["per_hit_accuracy_known"] = float(hit_chance_known)
        fields["per_hit_accuracy"] = float(hit_chance)
        return

    if loaded_dice and is_range and min_hits == 2 and max_hits == 5:
        fields["multihit_min"] = 4.0
        fields["multihit_max"] = 5.0
        fields["multihit_expected"] = 4.5
        fields["multihit_distribution_known"] = 1.0
        fields["per_hit_accuracy_known"] = float(hit_chance_known)
        fields["per_hit_accuracy"] = float(hit_chance)
        return
    if loaded_dice and max_hits == 10 and min_hits == 10:
        fields["multihit_min"] = 4.0
        fields["multihit_max"] = 10.0
        fields["multihit_expected"] = 7.0
        fields["multihit_distribution_known"] = 1.0
        fields["sequential_accuracy_stops_on_miss"] = 0.0
        fields["per_hit_accuracy_known"] = float(hit_chance_known)
        fields["per_hit_accuracy"] = float(hit_chance)
        return

    fields["per_hit_accuracy_known"] = float(hit_chance_known)
    fields["per_hit_accuracy"] = float(hit_chance)
    fields["sequential_accuracy_stops_on_miss"] = float(sequential)
    if sequential:
        if not hit_chance_known:
            fields["multihit_distribution_unknown"] = 1.0
            return
        fields["multihit_min"] = 0.0
        fields["multihit_max"] = float(max_hits)
        fields["multihit_expected"] = _expected_hits_for_sequential(max_hits, hit_chance)
        fields["multihit_distribution_known"] = 1.0
        return
    if is_range and min_hits == 2 and max_hits == 5:
        fields["multihit_min"] = 2.0
        fields["multihit_max"] = 5.0
        fields["multihit_expected"] = 3.1
        fields["multihit_distribution_known"] = 1.0
    elif is_range:
        fields["multihit_min"] = float(min_hits)
        fields["multihit_max"] = float(max_hits)
        fields["multihit_expected"] = (float(min_hits) + float(max_hits)) / 2.0
        fields["multihit_distribution_known"] = 1.0
    else:
        fields["multihit_min"] = float(min_hits)
        fields["multihit_max"] = float(max_hits)
        fields["multihit_expected"] = float(max_hits)
        fields["multihit_distribution_known"] = 1.0


def slice14_action_risk_feature_vector(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
    impact: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v7 batch 7: action-level risk/probability/provenance."""
    kind = str(action.get("kind") or "").lower()
    if not kind.startswith("move"):
        return np.zeros(len(SLICE14_ACTION_RISK_FEATURE_NAMES), dtype=np.float32)

    metadata, _ = load_move_metadata()
    move_id = to_id(_action_name(action))
    meta = metadata.get(move_id, {})
    block = _raw_move_blocks().get(move_id, "")
    category = str(meta.get("category") or "").lower()
    damaging = category != "status" and float(meta.get("base_power", 0.0) or 0.0) > 0
    accuracy = meta.get("accuracy")

    hit_chance, hit_known, partial_accuracy, unknown_accuracy = _weather_hit_chance_for_move(
        move_id, accuracy, tactical_state
    )
    if isinstance(impact, dict) and impact.get("accuracy_known") and impact.get("hit_chance") is not None:
        hit_chance = _clip(impact.get("hit_chance"))
        hit_known = True
        unknown_accuracy = False

    imp = impact if isinstance(impact, dict) else {}
    on_hit_damage = bool(imp.get("available") and not imp.get("non_damaging") and imp.get("expected_fraction") is not None)
    on_hit_expected = _clip(imp.get("expected_fraction", 0.0))
    crit_known, crit_chance, guaranteed_crit = _crit_chance_for_move(move_id, block, damaging)

    fields: Dict[str, float] = {name: 0.0 for name in SLICE14_ACTION_RISK_FEATURE_NAMES}
    fields.update(
        {
            "hit_chance_known": float(hit_known),
            "hit_chance": float(hit_chance if hit_known else 0.0),
            "miss_chance": float((1.0 - hit_chance) if hit_known else 0.0),
            "on_hit_damage_available": float(on_hit_damage),
            "expected_damage_includes_miss": on_hit_expected * hit_chance if on_hit_damage and hit_known else 0.0,
            "crit_chance_known": float(crit_known),
            "crit_chance": float(crit_chance),
            "guaranteed_crit": float(guaranteed_crit),
            "accuracy_context_partial": float(partial_accuracy),
            "accuracy_context_unknown": float(unknown_accuracy),
        }
    )

    opponent_action = move_id in OPPONENT_ACTION_BRANCH_MOVE_IDS
    active_turn = move_id in ACTIVE_TURN_BRANCH_MOVE_IDS
    target_switch = move_id in TARGET_SWITCH_BRANCH_MOVE_IDS
    target_switch_power = move_id in TARGET_SWITCH_POWER_BRANCH_MOVE_IDS
    prior_history = move_id in PRIOR_TURN_OR_HISTORY_BRANCH_MOVE_IDS

    tactical = tactical_state if isinstance(tactical_state, dict) else {}
    opponent = tactical.get("opponent") if isinstance(tactical.get("opponent"), dict) else {}
    terrain = to_id(tactical.get("terrain"))
    priority = int(float(meta.get("priority", 0.0) or 0.0))
    priority_prevention = False
    priority_condition_known = False
    if priority > 0 and terrain == "psychicterrain":
        grounded = _grounded_state(opponent)
        priority_prevention = grounded is not False
        priority_condition_known = grounded is not None

    branch_present = bool(
        opponent_action
        or active_turn
        or target_switch
        or target_switch_power
        or prior_history
        or priority_prevention
    )
    fields.update(
        {
            "may_fail_due_to_opponent_action": float(opponent_action),
            "may_fail_due_to_active_turn": float(active_turn),
            "may_fail_due_to_target_switch": float(target_switch),
            "may_fail_due_to_prior_turn_or_history": float(prior_history),
            "may_fail_due_to_priority_prevention": float(priority_prevention),
            "succeeds_if_target_attacks": float(move_id in {"suckerpunch", "thunderclap"}),
            "succeeds_if_target_switches": float(target_switch),
            "power_boost_if_target_switches": float(target_switch_power),
            "branch_condition_known": float(priority_condition_known and priority_prevention),
            "branch_condition_hidden_now": float(branch_present and not (priority_condition_known and priority_prevention)),
            "branch_pressure_present": float(branch_present),
        }
    )

    if move_id in RANDOM_CALL_MOVE_IDS or move_id in {"beatup", "ficklebeam"}:
        _apply_random_call_fields(fields, move_id, private_state, tactical_state)

    _apply_multihit_fields(fields, move_id, block, hit_chance, hit_known, private_state, tactical_state)

    flags = set(meta.get("flags") or [])
    delayed = "futuremove" in flags
    hazard = move_id in {"spikes", "toxicspikes", "stealthrock", "stickyweb"}
    residual = move_id in RESIDUAL_PRESSURE_MOVE_IDS or hazard
    binding = move_id in BINDING_MOVE_IDS
    if delayed:
        fields["delayed_pressure_created"] = 1.0
        fields["delayed_turns_until_effect"] = 2.0
        fields["delayed_targets_opp_slot"] = 1.0
        fields["delayed_damage_deferred_to_rollout"] = 1.0
        fields["future_damage_unknown_now"] = 1.0
    if residual:
        fields["residual_pressure_created"] = 1.0
        fields["residual_kind_known"] = 1.0
        fields["residual_source_known"] = 1.0
        fields["residual_duration_known"] = 0.0 if binding else 1.0
        fields["binding_pressure_created"] = float(binding)

    vector = np.asarray(
        [float(fields.get(name, 0.0)) for name in SLICE14_ACTION_RISK_FEATURE_NAMES],
        dtype=np.float32,
    )
    if vector.shape[0] != len(SLICE14_ACTION_RISK_FEATURE_NAMES):
        raise ValueError(
            f"Action v7 slice-14 size mismatch: got {vector.shape[0]}, "
            f"expected {len(SLICE14_ACTION_RISK_FEATURE_NAMES)}."
        )
    return vector


def _extract_balanced_region(text: str, start: int) -> Tuple[str, int]:
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
            if depth == 0:
                return text[start : index + 1], index + 1
    return text[start:], len(text)


def _top_level_objects_in(region: str) -> List[str]:
    objects: List[str] = []
    index = 0
    while index < len(region):
        if region[index] == "{":
            obj, end = _extract_object_block(region, index)
            if obj:
                objects.append(obj)
                index = end
                continue
        index += 1
    return objects


def _remove_self_blocks(text: str) -> str:
    work = text
    while True:
        match = re.search(r"\bself\s*:\s*\{", work)
        if not match:
            return work
        _, end = _extract_object_block(work, match.end() - 1)
        work = work[: match.start()] + work[end:]


def _secondary_objects(block: str) -> List[str]:
    objects: List[str] = []
    work = block
    for key in ("secondaries", "secondary"):
        while True:
            match = re.search(r"\b" + key + r"\s*:\s*[\{\[]", work)
            if not match:
                break
            region, end = _extract_balanced_region(work, match.end() - 1)
            objects.extend(_top_level_objects_in(region))
            work = work[: match.start()] + work[end:]
    return objects


def _secondary_chance_profile(move_id: str, block: str) -> Dict[str, float]:
    base = 0.0
    flinch = 0.0
    status = 0.0
    stat_drop = 0.0
    for obj in _secondary_objects(block):
        chance_match = re.search(r"\bchance\s*:\s*(\d+)", obj)
        chance = _clip((int(chance_match.group(1)) if chance_match else 100) / 100.0)
        target_text = _remove_self_blocks(obj)
        has_flinch = bool(re.search(r"\bvolatileStatus\s*:\s*['\"]flinch['\"]", target_text))
        has_status = bool(re.search(r"\bstatus\s*:\s*['\"][a-z]+['\"]", target_text))
        boosts = re.search(r"\bboosts\s*:\s*\{([^}]*)\}", target_text, re.DOTALL)
        has_stat_drop = bool(boosts and re.search(r":\s*-\d+", boosts.group(1)))
        has_any = has_flinch or has_status or has_stat_drop or bool(re.search(r"\bon[A-Z]\w*\s*\(", obj))
        if has_any:
            base = max(base, chance)
        if has_flinch:
            flinch = max(flinch, chance)
        if has_status:
            status = max(status, chance)
        if has_stat_drop:
            stat_drop = max(stat_drop, chance)

    if move_id == "triattack":
        base = max(base, 0.20)
        status = max(status, 0.20)
    elif move_id == "direclaw":
        base = max(base, 0.50)
        status = max(status, 0.50)

    return {
        "base": base,
        "flinch": flinch,
        "status": status,
        "stat_drop": stat_drop,
    }


def _side_item_info(side: Dict[str, Any]) -> Tuple[str, bool]:
    item = to_id(side.get("active_item"))
    state = str(side.get("active_item_state") or "unknown").lower()
    known = bool(item) or state in {"held", "none", "removed", "consumed"}
    return item, known


def _side_ability_info(side: Dict[str, Any]) -> Tuple[str, bool]:
    ability = to_id(side.get("active_current_ability") or side.get("active_base_ability"))
    state = str(side.get("active_ability_state") or "unknown").lower()
    known = bool(ability) or state in {"known", "active", "suppressed", "none"}
    return ability, known


def _own_item_ability_info(
    private_state: Optional[Dict[str, Any]],
    tactical_state: Optional[Dict[str, Any]],
) -> Tuple[str, bool, str, bool]:
    tactical = tactical_state if isinstance(tactical_state, dict) else {}
    own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
    active = _active_mon(private_state)
    item = to_id(active.get("item") or own.get("active_item"))
    item_state = str(active.get("item_state") or own.get("active_item_state") or "unknown").lower()
    item_known = bool(item) or item_state in {"held", "none", "removed", "consumed"}
    ability = to_id(
        own.get("active_current_ability")
        or own.get("active_base_ability")
        or active.get("ability")
        or active.get("base_ability")
    )
    ability_state = str(own.get("active_ability_state") or active.get("ability_state") or "unknown").lower()
    ability_known = bool(ability) or ability_state in {"known", "active", "suppressed", "none"}
    return item, item_known, ability, ability_known


def _own_hp_fraction_for_cost(
    private_state: Optional[Dict[str, Any]],
    tactical_state: Optional[Dict[str, Any]],
) -> Optional[float]:
    tactical = tactical_state if isinstance(tactical_state, dict) else {}
    own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
    hp = own.get("active_hp_fraction")
    if hp is None:
        hp = _active_mon(private_state).get("hp_fraction")
    if hp is None:
        return None
    return _clip(hp)


def _self_hp_cost_fraction(move_id: str) -> float:
    if move_id in HP_COST_SELF_KO_MOVE_IDS:
        return 0.5
    return 0.0


def slice15_forced_decision_secondary_feature_vector(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
    impact: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v7 batch 8: forced-decision and secondary-chance provenance."""
    kind = str(action.get("kind") or "").lower()
    if not kind.startswith("move"):
        return np.zeros(len(SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES), dtype=np.float32)

    metadata, _ = load_move_metadata()
    move_id = to_id(_action_name(action))
    meta = metadata.get(move_id, {})
    block = _raw_move_blocks().get(move_id, "")
    fields: Dict[str, float] = {name: 0.0 for name in SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES}

    accuracy = meta.get("accuracy")
    hit_chance, hit_known, _, _ = _weather_hit_chance_for_move(move_id, accuracy, tactical_state)
    if isinstance(impact, dict) and impact.get("accuracy_known") and impact.get("hit_chance") is not None:
        hit_chance = _clip(impact.get("hit_chance"))
        hit_known = True

    self_pivot = move_id in SELF_PIVOT_MOVE_IDS
    pivot_requires_hit = move_id in HIT_REQUIRED_SELF_PIVOT_MOVE_IDS
    if self_pivot:
        fields.update(
            {
                "self_pivot_move": 1.0,
                "self_pivot_requires_hit": float(pivot_requires_hit),
                "self_pivot_after_damage": float(move_id in DAMAGING_SELF_PIVOT_MOVE_IDS),
                "self_pivot_after_stat_drop": float(move_id in STAT_DROP_SELF_PIVOT_MOVE_IDS),
                "self_pivot_forces_replacement_decision": 1.0,
                "self_pivot_may_fail_due_to_immunity_or_miss": float(pivot_requires_hit),
                "self_pivot_branch_known": float((not pivot_requires_hit) or hit_known),
                "self_pivot_branch_unknown": float(pivot_requires_hit and not hit_known),
            }
        )

    hp_cost = _self_hp_cost_fraction(move_id)
    hp_fraction = _own_hp_fraction_for_cost(private_state, tactical_state)
    hp_cost_self_ko_known = hp_cost > 0.0 and hp_fraction is not None and hp_fraction <= hp_cost
    self_ko = move_id in SELF_KO_ALWAYS_MOVE_IDS or move_id in SELF_KO_IF_SUCCESSFUL_MOVE_IDS or hp_cost > 0.0
    if self_ko:
        guaranteed = move_id in SELF_KO_ALWAYS_MOVE_IDS
        if_successful = move_id in SELF_KO_IF_SUCCESSFUL_MOVE_IDS or hp_cost_self_ko_known
        fields.update(
            {
                "user_self_ko_move": 1.0,
                "user_self_ko_guaranteed": float(guaranteed),
                "user_self_ko_if_successful": float(if_successful),
                "user_self_ko_forces_replacement_decision": float(guaranteed or if_successful),
                "user_sacrifice_for_tempo": float(move_id in SELF_KO_ALWAYS_MOVE_IDS or move_id in SELF_KO_IF_SUCCESSFUL_MOVE_IDS),
                "user_sacrifice_with_healing_wish_effect": float(move_id in HEALING_WISH_SACRIFICE_MOVE_IDS),
                "user_sacrifice_with_stat_drop_effect": float(move_id in STAT_DROP_SACRIFICE_MOVE_IDS),
                "user_sacrifice_damage_based": float(move_id == "finalgambit" or hp_cost > 0.0),
            }
        )

    phazing = move_id in TARGET_PHAZING_MOVE_IDS
    if phazing:
        priority = int(float(meta.get("priority", 0.0) or 0.0))
        if_hits = move_id in HIT_REQUIRED_PHAZING_MOVE_IDS
        fields.update(
            {
                "forces_target_switch": 1.0,
                "forces_target_switch_if_hits": float(if_hits),
                "forced_target_switch_random": 1.0,
                "forced_target_switch_user_selected": 0.0,
                "phazing_blocked_by_substitute_possible": float(move_id in SUBSTITUTE_BLOCKABLE_PHAZING_MOVE_IDS),
                "phazing_priority_negative": float(priority < 0),
                "forced_switch_pressure_present": 1.0,
            }
        )

    tactical = tactical_state if isinstance(tactical_state, dict) else {}
    own_side = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
    target_side = tactical.get("opponent") if isinstance(tactical.get("opponent"), dict) else {}
    own_item, own_item_known, own_ability, own_ability_known = _own_item_ability_info(private_state, tactical_state)
    target_item, target_item_known = _side_item_info(target_side)
    target_ability, target_ability_known = _side_ability_info(target_side)

    profile = _secondary_chance_profile(move_id, block)
    has_self_stat_drop = move_id in {"dracometeor", "overheat", "leafstorm", "fleurcannon", "makeitrain", "closecombat", "superpower", "vcreate", "psychoboost"}
    if own_item == "ejectpack" and has_self_stat_drop:
        fields["user_item_may_force_self_switch"] = 1.0
        fields["eject_pack_possible"] = 1.0
        fields["item_trigger_branch_known"] = 1.0
    elif has_self_stat_drop and not own_item_known:
        fields["item_trigger_branch_unknown"] = 1.0
    if target_item == "ejectbutton" and (float(meta.get("base_power", 0.0) or 0.0) > 0 or profile["base"] > 0.0):
        fields["target_item_may_force_target_switch"] = 1.0
        fields["eject_button_possible"] = 1.0
        fields["item_trigger_branch_known"] = 1.0
    if target_item == "redcard" and float(meta.get("base_power", 0.0) or 0.0) > 0:
        fields["red_card_possible"] = 1.0
        fields["item_trigger_branch_known"] = 1.0

    base = profile["base"]
    base_known = base > 0.0
    serene = own_ability == "serenegrace"
    sheer_force = own_ability == "sheerforce" and base_known
    shield_dust = target_ability == "shielddust" and base_known
    covert_cloak = target_item == "covertcloak" and base_known
    blocked = shield_dust or covert_cloak or sheer_force
    modifier_known = bool(
        base_known
        and (
            serene
            or blocked
            or (own_ability_known and target_ability_known and target_item_known)
        )
    )

    multiplier = 2.0 if serene else 1.0
    def _modified(chance: float) -> float:
        if not chance:
            return 0.0
        if blocked:
            return 0.0
        return _clip(chance * multiplier)

    if base_known:
        fields.update(
            {
                "secondary_chance_base_known": 1.0,
                "secondary_chance_base": base,
                "secondary_chance_modified_known": float(modifier_known),
                "secondary_chance_modified": _modified(base),
                "secondary_chance_modifier_serene_grace": float(serene),
                "secondary_chance_blocked_by_shield_dust_possible": float(shield_dust),
                "secondary_chance_blocked_by_covert_cloak_possible": float(covert_cloak),
                "secondary_removed_by_sheer_force_possible": float(sheer_force),
                "flinch_chance_modified": _modified(profile["flinch"]),
                "status_chance_modified": _modified(profile["status"]),
                "stat_drop_chance_modified": _modified(profile["stat_drop"]),
            }
        )

    vector = np.asarray(
        [_clip(float(fields.get(name, 0.0))) for name in SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES],
        dtype=np.float32,
    )
    if vector.shape[0] != len(SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES):
        raise ValueError(
            f"Action v7 slice-15 size mismatch: got {vector.shape[0]}, "
            f"expected {len(SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES)}."
        )
    return vector


def build_action_feature_vector_v7(
    action: Dict[str, Any],
    private_state: Optional[Dict[str, Any]] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
    impact: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """legal-action-v7 = frozen prefixes + append-only typed-effect slices."""
    base = build_action_feature_vector_v6(action, private_state, tactical_state, impact)
    slice8 = slice8_typed_status_stat_feature_vector(action)
    slice9 = slice9_typed_volatile_feature_vector(action)
    slice10 = slice10_typed_item_effect_feature_vector(action, private_state, tactical_state)
    slice11 = slice11_typed_timing_priority_feature_vector(action, private_state, tactical_state)
    slice12 = slice12_typed_hp_side_effect_feature_vector(action, private_state, tactical_state)
    slice13 = slice13_typed_field_side_effect_feature_vector(action, tactical_state)
    slice14 = slice14_action_risk_feature_vector(action, private_state, tactical_state, impact)
    slice15 = slice15_forced_decision_secondary_feature_vector(action, private_state, tactical_state, impact)
    features = np.concatenate([base, slice8, slice9, slice10, slice11, slice12, slice13, slice14, slice15]).astype(np.float32)
    if features.shape[0] != ACTION_FEATURE_DIM_V7:
        raise ValueError(
            f"Action v7 feature size mismatch: got {features.shape[0]}, expected {ACTION_FEATURE_DIM_V7}."
        )
    return features


def action_feature_schema(version: str) -> Dict[str, Any]:
    if version == ACTION_FEATURE_VERSION_V5:
        return {
            "version": ACTION_FEATURE_VERSION_V5,
            "dim": ACTION_FEATURE_DIM_V5,
            "names": ACTION_FEATURE_NAMES_V5,
            "builder": build_action_feature_vector_v5,
        }
    if version == ACTION_FEATURE_VERSION_V6:
        return {
            "version": ACTION_FEATURE_VERSION_V6,
            "dim": ACTION_FEATURE_DIM_V6,
            "names": ACTION_FEATURE_NAMES_V6,
            "builder": build_action_feature_vector_v6,
        }
    if version == ACTION_FEATURE_VERSION_V7:
        return {
            "version": ACTION_FEATURE_VERSION_V7,
            "dim": ACTION_FEATURE_DIM_V7,
            "names": ACTION_FEATURE_NAMES_V7,
            "builder": build_action_feature_vector_v7,
        }
    raise ValueError(f"Unsupported explicit action feature version: {version!r}.")


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
        "v6_feature_version": ACTION_FEATURE_VERSION_V6,
        "v6_feature_dim": ACTION_FEATURE_DIM_V6,
        "v6_feature_names": ACTION_FEATURE_NAMES_V6,
        "v6_slice7_feature_names": SLICE7_ACTION_FEATURE_NAMES,
        "v7_feature_version": ACTION_FEATURE_VERSION_V7,
        "v7_feature_dim": ACTION_FEATURE_DIM_V7,
        "v7_feature_names": ACTION_FEATURE_NAMES_V7,
        "v7_slice8_feature_names": SLICE8_STATUS_STAT_FEATURE_NAMES,
        "v7_slice9_feature_names": SLICE9_VOLATILE_FEATURE_NAMES,
        "v7_slice10_feature_names": SLICE10_ITEM_EFFECT_FEATURE_NAMES,
        "v7_slice11_feature_names": SLICE11_TIMING_PRIORITY_FEATURE_NAMES,
        "v7_slice12_feature_names": SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES,
        "v7_slice13_feature_names": SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES,
        "v7_slice14_feature_names": SLICE14_ACTION_RISK_FEATURE_NAMES,
        "v7_slice15_feature_names": SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES,
        "tactical_feature_dim": len(TACTICAL_ACTION_FEATURE_NAMES),
        "tactical_feature_names": TACTICAL_ACTION_FEATURE_NAMES,
        "move_metadata_source": source,
    }
