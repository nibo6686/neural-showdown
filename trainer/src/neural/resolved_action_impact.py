"""Diagnostic resolved-impact provider for `legal-action-v5` (Slice 6).

Produces a normalized "impact" dict for one action by calling the existing
Smogon-backed `damage_engine` (`estimate_action_damage`). It is **diagnostic
only**: nothing here is wired into the live recommender's default action ranking,
and `legal-action-v5` feature generation only consumes an impact dict if one is
supplied — the live default (`legal-action-v3`) never calls this.

Provenance is explicit. Damaging moves resolve through the real calc
(`smogon_calc`) or its heuristic fallback (`approximate`); non-damaging moves and
switches are reported as such rather than as "0 damage of unknown quality".

`next_state` deltas are limited to what is honestly derivable from the immediate
estimate (opponent HP delta = −expected damage). Full own-HP / stat / status /
field deltas and terminal KO/win/loss flags are only populated when an explicit
`branch_impact` dict is passed (a seeded one-turn transition), otherwise they stay
zero with `next_state_source = immediate_estimate`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .action_features import (
    CONDITIONAL_FAIL_CLOSED_MOVE_DEPENDENCY,
    CONDITIONAL_FAIL_CLOSED_MOVE_IDS,
    DYNAMIC_TYPE_FAIL_CLOSED_MOVE_IDS,
    FINAL_FAIL_CLOSED_MOVE_DEPENDENCY,
    FINAL_FAIL_CLOSED_MOVE_IDS,
    FIXED_DAMAGE_FAIL_CLOSED_MOVE_IDS,
    FIXED_DAMAGE_ORACLE_MOVE_IDS,
    GUARANTEED_CRIT_MOVE_IDS,
    MULTI_HIT_MOVE_IDS,
    TWO_TURN_CHARGE_MOVE_IDS,
    VARIABLE_POWER_DAMAGE_MOVE_IDS,
    WEATHER_DEPENDENT_ACCURACY_MOVE_IDS,
    _action_name,
    classify_action_category,
    load_move_metadata,
    to_id,
)

WEATHER_RAIN_IDS = {"raindance", "rain", "primordialsea"}
WEATHER_SUN_IDS = {"sunnyday", "sun", "desolateland"}
WEATHER_SNOW_IDS = {"snow", "hail"}


def _clip(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return low
    if number != number:  # NaN
        return low
    return max(low, min(high, number))


def _attacker_types(approx_state: Dict[str, Any]) -> List[str]:
    tactical = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
    own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
    for key in ("active_current_types", "active_base_types"):
        types = own.get(key)
        if isinstance(types, list) and types:
            return [str(t) for t in types if str(t)]
    private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
    team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
    active = next((m for m in team if isinstance(m, dict) and m.get("active")), team[0] if team else {})
    types = active.get("types") if isinstance(active, dict) else None
    if isinstance(types, list) and types:
        return [str(t) for t in types if str(t)]
    try:
        from .tactical_state import _species_types

        return _species_types((active or {}).get("species"))
    except Exception:
        return []


def _defender_hp_fraction(approx_state: Dict[str, Any]) -> float:
    view = approx_state.get("view") if isinstance(approx_state.get("view"), dict) else {}
    team = view.get("opponent_team") if isinstance(view.get("opponent_team"), list) else []
    mon = team[0] if team and isinstance(team[0], dict) else {}
    hp = mon.get("hp_fraction")
    return _clip(hp) if hp is not None else 1.0


def _weather_adjusted_hit_chance(
    move_id: str, base_accuracy: Any, approx_state: Dict[str, Any]
) -> tuple[float, bool]:
    """Hit chance for a weather-dependent-accuracy move.

    Weather is protocol-observable, so when the tactical state is present its
    weather (``None`` = clear) is authoritative and the hit chance is exact.
    When no tactical state is supplied the weather context is unsupported and the
    accuracy fails closed (not exact) rather than claiming the clear-weather value.
    """
    clear = _clip(float(base_accuracy) / 100.0) if base_accuracy is not None else 0.7
    tactical = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else None
    if tactical is None:
        return clear, False
    weather = to_id(tactical.get("weather"))
    if move_id == "blizzard":
        return (1.0, True) if weather in WEATHER_SNOW_IDS else (clear, True)
    # thunder / hurricane / bleakwind storm: perfect in rain, halved in harsh sun.
    if weather in WEATHER_RAIN_IDS:
        return 1.0, True
    if weather in WEATHER_SUN_IDS:
        return 0.5, True
    return clear, True


def _charge_resolves_immediately(move_id: str, approx_state: Dict[str, Any]) -> bool:
    """Whether a two-turn charge move actually deals its damage this turn.

    Future Sight is always delayed. Solar Beam skips the charge in harsh sun;
    any charge move skips it while holding Power Herb. Otherwise the move charges
    this turn and deals no immediate damage, so the on-hit estimate is wrong-timing.
    """
    if move_id == "futuresight":
        return False
    private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
    team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
    attacker = next(
        (mon for mon in team if isinstance(mon, dict) and mon.get("active")),
        team[0] if team and isinstance(team[0], dict) else {},
    )
    if to_id(attacker.get("item")) == "powerherb":
        return True
    if move_id == "solarbeam":
        tactical = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
        return to_id(tactical.get("weather")) in WEATHER_SUN_IDS
    return False


def _unavailable_impact(*, non_damaging: bool, method: str = "unavailable") -> Dict[str, Any]:
    return {
        "available": False,
        "non_damaging": non_damaging,
        "method": method,
        "expected_fraction": 0.0,
        "min_fraction": 0.0,
        "max_fraction": 0.0,
        "ko_chance": 0.0,
        "two_hko_proxy": 0.0,
        "hit_chance": 0.0,
        "accuracy_known": False,
        "immune": False,
        "resisted": False,
        "super_effective": False,
        "type_effectiveness": 1.0,
        "stab": False,
        "stab_known": False,
        "crit_included": False,
        "vs_current_type": False,
        "used_tera": False,
        "used_stat_stages": False,
        "used_item_ability": False,
        "used_field": False,
        "used_exact_attacker_stats": False,
        "used_exact_defender_stats": False,
        "target_known": False,
        "target_inferred": False,
        "next_state_source": "unavailable",
        "next_opp_hp_delta": 0.0,
        "next_own_hp_delta": 0.0,
        "next_own_hp_delta_known": False,
        "terminal_from_branch": False,
        "terminal_ko": False,
        "terminal_win": False,
        "terminal_loss": False,
    }


def _apply_branch_impact(impact: Dict[str, Any], branch_impact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(branch_impact, dict):
        return impact
    impact["next_state_source"] = "branch"
    for key in (
        "next_opp_hp_delta",
        "next_own_hp_delta",
        "next_own_hp_delta_known",
        "terminal_from_branch",
        "terminal_ko",
        "terminal_win",
        "terminal_loss",
    ):
        if key in branch_impact:
            impact[key] = branch_impact[key]
    impact["terminal_from_branch"] = True
    return impact


def resolve_action_impact(
    action: Dict[str, Any],
    approx_state: Optional[Dict[str, Any]] = None,
    *,
    client: Any = None,
    estimate: Optional[Dict[str, Any]] = None,
    branch_impact: Optional[Dict[str, Any]] = None,
    enable_repeat_chain: bool = False,
) -> Dict[str, Any]:
    """Resolve one action's immediate impact into a normalized impact dict."""
    kind = str(action.get("kind") or "").lower()
    if kind == "switch":
        return _apply_branch_impact(_unavailable_impact(non_damaging=True), branch_impact)

    approx_state = approx_state if isinstance(approx_state, dict) else {}
    name = _action_name(action)
    metadata, _ = load_move_metadata()
    move_id = to_id(name)
    meta = metadata.get(move_id, {})
    base_power = float(meta.get("base_power", 0.0) or 0.0)
    category = str(meta.get("category") or "").lower()
    accuracy = meta.get("accuracy")
    hit_chance = _clip(float(accuracy) / 100.0) if accuracy is not None else 1.0

    if move_id == "curse":
        attacker_types = {str(value).lower() for value in _attacker_types(approx_state)}
        if not attacker_types:
            impact = _unavailable_impact(non_damaging=True)
            impact["fallback_reason"] = "curse_current_type_unknown"
            impact["dynamic_dependency"] = "current_types"
            return _apply_branch_impact(impact, branch_impact)
        impact = _unavailable_impact(non_damaging=True, method="non_damaging")
        impact["available"] = True
        impact["hit_chance"] = hit_chance
        impact["accuracy_known"] = accuracy is not None
        impact["next_state_source"] = "immediate_estimate"
        if "ghost" in attacker_types:
            impact["next_own_hp_delta"] = -0.5
            impact["next_own_hp_delta_known"] = True
            impact["next_opp_status_change"] = True
        return _apply_branch_impact(impact, branch_impact)

    # Fixed-damage / counter moves: exact damage depends on target current HP or
    # damage taken this turn, which the oracle does not resolve (it returns 0).
    # Fail closed rather than emit a wrong-exact value or misclassify as 0 damage.
    if move_id in FIXED_DAMAGE_FAIL_CLOSED_MOVE_IDS:
        impact = _unavailable_impact(non_damaging=False)
        impact["fallback_reason"] = "fixed_damage_target_context_unresolved"
        impact["dynamic_dependency"] = "damage_taken" if move_id in {"mirrorcoat", "counter", "metalburst"} else "target_hp"
        return _apply_branch_impact(impact, branch_impact)

    # Multi-hit moves: the oracle reports per-hit rolls (flattened), so the single
    # expected/min/max fields cannot faithfully represent the multi-hit total or
    # 2-5 hit distribution. Fail closed rather than under-report a per-hit value.
    if move_id in MULTI_HIT_MOVE_IDS:
        impact = _unavailable_impact(non_damaging=False)
        impact["fallback_reason"] = "multihit_total_unrepresented"
        impact["dynamic_dependency"] = "multihit"
        return _apply_branch_impact(impact, branch_impact)

    # Two-turn charge / delayed-damage moves: only deal damage this turn under
    # specific conditions (sun / Power Herb; never Future Sight). Otherwise the
    # on-hit estimate is wrong-timing, so fail closed instead of emitting it.
    if move_id in TWO_TURN_CHARGE_MOVE_IDS and not _charge_resolves_immediately(move_id, approx_state):
        impact = _unavailable_impact(non_damaging=False)
        impact["fallback_reason"] = "two_turn_charge_delayed_damage"
        impact["dynamic_dependency"] = "charge_timing"
        return _apply_branch_impact(impact, branch_impact)

    # Tera Starstorm becomes Stellar-typed when Terastallized; Stellar STAB (2x)
    # and effectiveness are not representable by the standard type chart.
    if move_id in DYNAMIC_TYPE_FAIL_CLOSED_MOVE_IDS:
        impact = _unavailable_impact(non_damaging=False)
        impact["fallback_reason"] = "stellar_type_not_representable"
        impact["dynamic_dependency"] = "stellar_type"
        return _apply_branch_impact(impact, branch_impact)

    # Conditional-execution / turn-history-power moves: success or doubled power
    # depends on the opponent's same-turn action, the first-active turn, the
    # user's form, the target's item, within-turn order, or prior-move-failure
    # history not plumbed to the oracle. Do not encode "deals this damage" when
    # the move may fail or its power may double -> fail closed.
    if move_id in CONDITIONAL_FAIL_CLOSED_MOVE_IDS:
        impact = _unavailable_impact(non_damaging=False)
        impact["fallback_reason"] = "conditional_execution_or_history"
        impact["dynamic_dependency"] = CONDITIONAL_FAIL_CLOSED_MOVE_DEPENDENCY[move_id]
        return _apply_branch_impact(impact, branch_impact)

    # Final batch: moves needing state v6 does not carry (party Attack stats,
    # target berry, target item removal, a random power branch, terrain-conditional
    # priority). The oracle would emit a wrong-exact value, so fail closed.
    if move_id in FINAL_FAIL_CLOSED_MOVE_IDS:
        impact = _unavailable_impact(non_damaging=False)
        impact["fallback_reason"] = "unrepresented_context"
        impact["dynamic_dependency"] = FINAL_FAIL_CLOSED_MOVE_DEPENDENCY[move_id]
        return _apply_branch_impact(impact, branch_impact)

    # Non-damaging move: damage is known to be zero, not "unavailable".
    if category == "status" or (
        base_power <= 0
        and move_id not in VARIABLE_POWER_DAMAGE_MOVE_IDS
        and move_id not in FIXED_DAMAGE_ORACLE_MOVE_IDS
    ):
        impact = _unavailable_impact(non_damaging=True, method="non_damaging")
        impact["available"] = True
        impact["hit_chance"] = hit_chance
        impact["accuracy_known"] = accuracy is not None
        impact["next_state_source"] = "immediate_estimate"
        return _apply_branch_impact(impact, branch_impact)

    if move_id == "ragefist":
        private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
        team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
        attacker = next(
            (mon for mon in team if isinstance(mon, dict) and mon.get("active")),
            team[0] if team and isinstance(team[0], dict) else {},
        )
        tactical = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
        own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
        counter_known = attacker.get("times_attacked") is not None or bool(own.get("active_times_attacked_known"))
        if not counter_known:
            impact = _unavailable_impact(non_damaging=False)
            impact["fallback_reason"] = "rage_fist_times_attacked_unknown"
            impact["dynamic_dependency"] = "times_attacked"
            return _apply_branch_impact(impact, branch_impact)

    if move_id in {"reversal", "flail"}:
        private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
        team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
        attacker = next(
            (mon for mon in team if isinstance(mon, dict) and mon.get("active")),
            team[0] if team and isinstance(team[0], dict) else {},
        )
        hp_known = attacker.get("cur_hp") is not None or attacker.get("hp_fraction") is not None
        if not hp_known:
            impact = _unavailable_impact(non_damaging=False)
            impact["fallback_reason"] = "variable_power_user_hp_unknown"
            impact["dynamic_dependency"] = "user_hp"
            return _apply_branch_impact(impact, branch_impact)

    if move_id in {"gyroball", "electroball"}:
        private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
        team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
        attacker = next(
            (mon for mon in team if isinstance(mon, dict) and mon.get("active")),
            team[0] if team and isinstance(team[0], dict) else {},
        )
        view = approx_state.get("view") if isinstance(approx_state.get("view"), dict) else {}
        opponents = view.get("opponent_team") if isinstance(view.get("opponent_team"), list) else []
        defender = opponents[0] if opponents and isinstance(opponents[0], dict) else {}
        attacker_speed_known = bool(attacker.get("species")) or isinstance(attacker.get("stats"), dict)
        defender_speed_known = bool(defender.get("species")) or isinstance(defender.get("stats"), dict)
        if not (attacker_speed_known and defender_speed_known):
            impact = _unavailable_impact(non_damaging=False)
            impact["fallback_reason"] = "variable_power_speed_unknown"
            impact["dynamic_dependency"] = "speed_ratio"
            return _apply_branch_impact(impact, branch_impact)

    if move_id in {"grassknot", "lowkick", "heavyslam", "heatcrash"}:
        private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
        team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
        attacker = next(
            (mon for mon in team if isinstance(mon, dict) and mon.get("active")),
            team[0] if team and isinstance(team[0], dict) else {},
        )
        view = approx_state.get("view") if isinstance(approx_state.get("view"), dict) else {}
        opponents = view.get("opponent_team") if isinstance(view.get("opponent_team"), list) else []
        defender = opponents[0] if opponents and isinstance(opponents[0], dict) else {}
        needs_attacker_weight = move_id in {"heavyslam", "heatcrash"}
        if not defender.get("species") or (needs_attacker_weight and not attacker.get("species")):
            impact = _unavailable_impact(non_damaging=False)
            impact["fallback_reason"] = "variable_power_weight_unknown"
            impact["dynamic_dependency"] = "weight"
            return _apply_branch_impact(impact, branch_impact)

    if move_id == "lastrespects":
        private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
        team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
        attacker = next(
            (mon for mon in team if isinstance(mon, dict) and mon.get("active")),
            team[0] if team and isinstance(team[0], dict) else {},
        )
        tactical = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
        counter_known = attacker.get("allies_fainted") is not None or bool(tactical.get("history_complete"))
        if not counter_known:
            impact = _unavailable_impact(non_damaging=False)
            impact["fallback_reason"] = "last_respects_fainted_allies_unknown"
            impact["dynamic_dependency"] = "allies_fainted"
            return _apply_branch_impact(impact, branch_impact)

    if move_id in {"storedpower", "powertrip"}:
        private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
        team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
        attacker = next(
            (mon for mon in team if isinstance(mon, dict) and mon.get("active")),
            team[0] if team and isinstance(team[0], dict) else {},
        )
        tactical = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
        own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
        boosts_known = isinstance(attacker.get("boosts"), dict) or bool(own.get("boosts_known"))
        if not boosts_known:
            impact = _unavailable_impact(non_damaging=False)
            impact["fallback_reason"] = "positive_boost_stages_unknown"
            impact["dynamic_dependency"] = "boosts"
            return _apply_branch_impact(impact, branch_impact)

    if enable_repeat_chain and move_id in {"rollout", "furycutter"}:
        tactical = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
        own = tactical.get("own") if isinstance(tactical.get("own"), dict) else {}
        chain = own.get("repeat_chain") if isinstance(own.get("repeat_chain"), dict) else {}
        if not (chain.get("known") and chain.get("exact")):
            impact = _unavailable_impact(non_damaging=False)
            impact["fallback_reason"] = "repeat_chain_state_unknown"
            impact["dynamic_dependency"] = "repeat_chain"
            return _apply_branch_impact(impact, branch_impact)

    if estimate is None:
        from .damage_engine import estimate_action_damage

        estimate = estimate_action_damage(
            action=action,
            approx_state=approx_state,
            client=client,
            include_repeat_chain_context=enable_repeat_chain,
        )
    est = estimate if isinstance(estimate, dict) else {}

    damage_method = str(est.get("damage_method") or "")
    source = str(est.get("rollout_damage_source") or "")
    fallback = est.get("fallback_reason")
    if damage_method == "non_damaging_move":
        method = "non_damaging"
    elif damage_method == "smogon_calc" and source in {"node_module", "sim_core_rpc"} and not fallback:
        method = "smogon_calc"
    else:
        method = "approximate"
    if (
        move_id in VARIABLE_POWER_DAMAGE_MOVE_IDS or move_id in FIXED_DAMAGE_ORACLE_MOVE_IDS
    ) and method != "smogon_calc":
        impact = _unavailable_impact(non_damaging=False)
        impact["fallback_reason"] = str(fallback or "variable_power_oracle_unavailable")
        impact["dynamic_dependency"] = (
            "user_level"
            if move_id in FIXED_DAMAGE_ORACLE_MOVE_IDS
            else "user_hp"
            if move_id in {"reversal", "flail"}
            else "speed_ratio"
            if move_id in {"gyroball", "electroball"}
            else "weight"
        )
        return _apply_branch_impact(impact, branch_impact)
    smogon = method == "smogon_calc"

    type_eff = est.get("type_effectiveness")
    type_eff = float(type_eff) if type_eff is not None else 1.0
    expected = _clip(float(est.get("average_percent", 0.0) or 0.0) / 100.0)
    max_fraction = _clip(float(est.get("max_percent", 0.0) or 0.0) / 100.0)
    target_hp = _defender_hp_fraction(approx_state)

    # Use the resolved (dynamic) move type from the oracle so STAB matches the
    # actual type used (Weather Ball, Ivy Cudgel, Judgment, ...); falls back to
    # the static metadata type for ordinary moves.
    move_type = str(est.get("move_type_resolved") or meta.get("type") or "")
    attacker_types = _attacker_types(approx_state)
    stab_known = bool(attacker_types) and bool(move_type)
    stab = bool(stab_known and move_type in attacker_types)

    rollout_input = est.get("rollout_damage_input") if isinstance(est.get("rollout_damage_input"), dict) else {}
    target_inferred = bool(rollout_input.get("defender_inferred_fields"))

    accuracy_known = accuracy is not None
    if move_id in WEATHER_DEPENDENT_ACCURACY_MOVE_IDS:
        hit_chance, accuracy_known = _weather_adjusted_hit_chance(move_id, accuracy, approx_state)

    impact = {
        "available": True,
        "non_damaging": False,
        "method": method,
        "expected_fraction": expected,
        "min_fraction": _clip(float(est.get("min_percent", 0.0) or 0.0) / 100.0),
        "max_fraction": max_fraction,
        "ko_chance": _clip(est.get("ko_chance", 0.0)),
        # Cheap 2HKO proxy: two average rolls vs the target's remaining HP.
        "two_hko_proxy": float(2.0 * expected >= target_hp and target_hp > 0.0),
        "hit_chance": hit_chance,
        "accuracy_known": accuracy_known,
        "immune": bool(est.get("immune")) or type_eff == 0.0,
        "resisted": 0.0 < type_eff < 1.0,
        "super_effective": type_eff > 1.0,
        "type_effectiveness": type_eff,
        "stab": stab,
        "stab_known": stab_known,
        "crit_included": move_id in GUARANTEED_CRIT_MOVE_IDS,  # calc bakes the guaranteed crit into the rolls
        "vs_current_type": True,  # calc reads the defender's current types (incl. Soak/Tera)
        "used_tera": str(action.get("kind") or "") == "move_tera" or bool(action.get("is_tera_action")),
        "used_stat_stages": smogon,  # Smogon calc honors boosts; heuristic does not
        "used_item_ability": smogon,
        "used_field": smogon,
        "used_exact_attacker_stats": bool(est.get("used_exact_attacker_stats")),
        "used_exact_defender_stats": bool(est.get("used_exact_defender_stats")),
        "target_known": True,
        "target_inferred": target_inferred,
        "next_state_source": "immediate_estimate",
        "next_opp_hp_delta": -expected,  # immediate: opponent loses ~expected HP fraction
        "next_own_hp_delta": 0.0,
        "next_own_hp_delta_known": False,
        "terminal_from_branch": False,
        "terminal_ko": False,
        "terminal_win": False,
        "terminal_loss": False,
    }
    return _apply_branch_impact(impact, branch_impact)


def resolve_impacts_for_actions(
    actions: List[Dict[str, Any]],
    approx_state: Optional[Dict[str, Any]] = None,
    *,
    client: Any = None,
) -> List[Dict[str, Any]]:
    """Convenience: resolve a batch of actions (diagnostic scripts only)."""
    return [resolve_action_impact(action, approx_state, client=client) for action in actions]
