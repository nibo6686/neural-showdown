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

from .action_features import _action_name, classify_action_category, load_move_metadata, to_id


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
) -> Dict[str, Any]:
    """Resolve one action's immediate impact into a normalized impact dict."""
    kind = str(action.get("kind") or "").lower()
    if kind == "switch":
        return _apply_branch_impact(_unavailable_impact(non_damaging=True), branch_impact)

    approx_state = approx_state if isinstance(approx_state, dict) else {}
    name = _action_name(action)
    metadata, _ = load_move_metadata()
    meta = metadata.get(to_id(name), {})
    base_power = float(meta.get("base_power", 0.0) or 0.0)
    category = str(meta.get("category") or "").lower()
    accuracy = meta.get("accuracy")
    hit_chance = _clip(float(accuracy) / 100.0) if accuracy is not None else 1.0

    # Non-damaging move: damage is known to be zero, not "unavailable".
    if category == "status" or base_power <= 0:
        impact = _unavailable_impact(non_damaging=True, method="non_damaging")
        impact["available"] = True
        impact["hit_chance"] = hit_chance
        impact["accuracy_known"] = accuracy is not None
        impact["next_state_source"] = "immediate_estimate"
        return _apply_branch_impact(impact, branch_impact)

    if estimate is None:
        from .damage_engine import estimate_action_damage

        estimate = estimate_action_damage(action=action, approx_state=approx_state, client=client)
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
    smogon = method == "smogon_calc"

    type_eff = est.get("type_effectiveness")
    type_eff = float(type_eff) if type_eff is not None else 1.0
    expected = _clip(float(est.get("average_percent", 0.0) or 0.0) / 100.0)
    max_fraction = _clip(float(est.get("max_percent", 0.0) or 0.0) / 100.0)
    target_hp = _defender_hp_fraction(approx_state)

    move_type = str(meta.get("type") or "")
    attacker_types = _attacker_types(approx_state)
    stab_known = bool(attacker_types) and bool(move_type)
    stab = bool(stab_known and move_type in attacker_types)

    rollout_input = est.get("rollout_damage_input") if isinstance(est.get("rollout_damage_input"), dict) else {}
    target_inferred = bool(rollout_input.get("defender_inferred_fields"))

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
        "accuracy_known": accuracy is not None,
        "immune": bool(est.get("immune")) or type_eff == 0.0,
        "resisted": 0.0 < type_eff < 1.0,
        "super_effective": type_eff > 1.0,
        "type_effectiveness": type_eff,
        "stab": stab,
        "stab_known": stab_known,
        "crit_included": False,  # calc uses non-crit rolls; crit handling deferred
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
