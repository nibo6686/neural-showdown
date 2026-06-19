"""Diagnostic-only resolved-impact counterfactuals for `legal-action-v5` (Slice 6).

Each scenario changes exactly one controlled variable and shows that the v5
resolved-impact fields react. Damage is the real Smogon calc via `damage_engine`.
These are representation tests (does the field move in the right direction?), not
tactical rules. No training, no checkpoints, no live defaults touched.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .action_features import (
    ACTION_FEATURE_DIM_V4,
    ACTION_FEATURE_NAMES_V5,
    ACTION_FEATURE_VERSION_V5,
    build_action_feature_vector_v5,
)
from .resolved_action_impact import resolve_action_impact


def _approx(attacker: Dict[str, Any], defender: Dict[str, Any], *, side_conditions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "private_state": {"team": [{**attacker, "active": True}]},
        "view": {"opponent_team": [defender]},
        "tactical_state": {
            "own": {"active_current_types": list(attacker.get("types") or [])},
            "opponent": {"side_conditions": dict(side_conditions or {})},
        },
    }


def _action(move: str, kind: str = "move", **extra: Any) -> Dict[str, Any]:
    action = {"kind": kind, "label": f"{kind}: {move}", "move": move}
    action.update(extra)
    return action


def _v5(move: str, attacker: Dict[str, Any], defender: Dict[str, Any], *, kind: str = "move", side_conditions=None, **action_extra) -> np.ndarray:
    action = _action(move, kind, **action_extra)
    impact = resolve_action_impact(action, _approx(attacker, defender, side_conditions=side_conditions))
    return build_action_feature_vector_v5(action, {"team": [{**attacker, "active": True}]}, {}, impact)


def _val(vec: np.ndarray, name: str) -> float:
    return float(vec[ACTION_FEATURE_NAMES_V5.index(name)])


def _changed(left: np.ndarray, right: np.ndarray) -> List[str]:
    indices = np.where(~np.isclose(left, right, atol=1e-7))[0]
    return [ACTION_FEATURE_NAMES_V5[index] for index in indices]


_LATIOS = {"species": "Latios", "level": 80, "types": ["Dragon", "Psychic"]}
_BLASTOISE = {"species": "Blastoise", "level": 80, "hp_fraction": 1.0, "types": ["Water"]}
_GYARADOS = {"species": "Gyarados", "level": 80, "hp_fraction": 1.0, "types": ["Water", "Flying"]}


def evaluate_resolved_impact_counterfactuals() -> Dict[str, Any]:
    # 1. damaging vs non-damaging
    damaging = _v5("Psychic", _LATIOS, _BLASTOISE)
    non_damaging = _v5("Calm Mind", _LATIOS, _BLASTOISE)

    # 2. immune vs not (Ground vs Flying)
    diglett = {"species": "Diglett", "level": 80, "types": ["Ground"]}
    flying = {"species": "Charizard", "level": 80, "hp_fraction": 1.0, "types": ["Fire", "Flying"]}
    grounded = {"species": "Blastoise", "level": 80, "hp_fraction": 1.0, "types": ["Water"]}
    immune = _v5("Earthquake", diglett, flying)
    not_immune = _v5("Earthquake", diglett, grounded)

    # 3. resisted vs super-effective (Psychic vs Steel/Psychic vs Fighting)
    metagross = {"species": "Metagross", "level": 80, "hp_fraction": 1.0, "types": ["Steel", "Psychic"]}
    hariyama = {"species": "Hariyama", "level": 80, "hp_fraction": 1.0, "types": ["Fighting"]}
    resisted = _v5("Psychic", _LATIOS, metagross)
    super_eff = _v5("Psychic", _LATIOS, hariyama)

    # 4. same move before/after a current-type change (Soak: mono-Normal Eevee ->
    # pure Water flips Thunderbolt from neutral to super-effective). A mono-type
    # target is used because the calc's type override replaces by index, so it is
    # only reliable when the override fully covers the base types (see audit).
    raichu = {"species": "Raichu", "level": 80, "types": ["Electric"]}
    eevee = {"species": "Eevee", "level": 80, "hp_fraction": 1.0, "types": ["Normal"]}
    before_soak = _v5("Thunderbolt", raichu, dict(eevee))
    after_soak = _v5("Thunderbolt", raichu, {**eevee, "types_override": ["Water"]})

    # 5. same move before/after a Tera-current-type change (Charizard -> Tera Water)
    before_tera = _v5("Surf", _BLASTOISE, dict(flying))
    after_tera = _v5(
        "Surf",
        _BLASTOISE,
        {**flying, "types": ["Water"], "terastallized": True, "tera_type": "Water"},
    )

    # 6. same special move before/after own SpA drop
    spa_full = _v5("Psychic", _LATIOS, _BLASTOISE)
    spa_dropped = _v5("Psychic", {**_LATIOS, "boosts": {"spa": -2}}, _BLASTOISE)

    # 7. same special move before/after Light Screen
    no_screen = _v5("Psychic", _LATIOS, _BLASTOISE)
    light_screen = _v5("Psychic", _LATIOS, _BLASTOISE, side_conditions={"lightscreen": 1})

    # 8. Draco Meteor vs Psyshock (v4 metadata + v5 resolved)
    draco = _v5("Draco Meteor", _LATIOS, _BLASTOISE)
    psyshock = _v5("Psyshock", _LATIOS, _BLASTOISE)

    # 9. switch action
    switch_impact = resolve_action_impact(_action("Latias", "switch", index=9))
    switch = build_action_feature_vector_v5(
        _action("Latias", "switch", index=9), {"team": [{"species": "Latias"}]}, {}, switch_impact
    )
    move = _v5("Psychic", _LATIOS, _BLASTOISE)

    # 10. accuracy: 100% vs lower-accuracy move
    accurate = _v5("Psychic", _LATIOS, _BLASTOISE)  # 100
    inaccurate = _v5("Focus Blast", _LATIOS, _BLASTOISE)  # 70

    return {
        "action_feature_version": ACTION_FEATURE_VERSION_V5,
        "action_feature_dim": int(damaging.shape[0]),
        "v4_prefix_dim": ACTION_FEATURE_DIM_V4,
        "synthetic": True,
        "comparisons": {
            "damaging_vs_non_damaging": {
                "changed": _changed(damaging, non_damaging),
                "damaging_expected": _val(damaging, "impact_expected_damage_fraction"),
                "non_damaging_flag": _val(non_damaging, "action_non_damaging"),
                "non_damaging_method": _val(non_damaging, "impact_method_non_damaging"),
            },
            "immune_vs_not": {
                "changed": _changed(immune, not_immune),
                "immune_flag": _val(immune, "impact_immune"),
                "immune_expected": _val(immune, "impact_expected_damage_fraction"),
            },
            "resisted_vs_super_effective": {
                "changed": _changed(resisted, super_eff),
                "resisted_flag": _val(resisted, "impact_resisted"),
                "super_effective_flag": _val(super_eff, "impact_super_effective"),
            },
            "soak_current_type_change": {
                "changed": _changed(before_soak, after_soak),
                "before_expected": _val(before_soak, "impact_expected_damage_fraction"),
                "after_expected": _val(after_soak, "impact_expected_damage_fraction"),
            },
            "tera_current_type_change": {
                "changed": _changed(before_tera, after_tera),
                "before_super_effective": _val(before_tera, "impact_super_effective"),
                "after_resisted": _val(after_tera, "impact_resisted"),
            },
            "own_spa_drop_changes_special_damage": {
                "changed": _changed(spa_full, spa_dropped),
                "full_expected": _val(spa_full, "impact_expected_damage_fraction"),
                "dropped_expected": _val(spa_dropped, "impact_expected_damage_fraction"),
            },
            "light_screen_reduces_damage": {
                "changed": _changed(no_screen, light_screen),
                "no_screen_expected": _val(no_screen, "impact_expected_damage_fraction"),
                "light_screen_expected": _val(light_screen, "impact_expected_damage_fraction"),
            },
            "draco_vs_psyshock": {
                "changed": _changed(draco, psyshock),
                "draco_self_spa_delta": _val(draco, "self_stat_delta_spa"),
                "psyshock_self_spa_delta": _val(psyshock, "self_stat_delta_spa"),
                "draco_expected": _val(draco, "impact_expected_damage_fraction"),
                "psyshock_expected": _val(psyshock, "impact_expected_damage_fraction"),
                "draco_method_smogon": _val(draco, "impact_method_smogon_calc"),
            },
            "switch_vs_move": {
                "changed": _changed(switch, move),
                "switch_non_damaging": _val(switch, "action_non_damaging"),
                "switch_method_unavailable": _val(switch, "impact_method_unavailable"),
                "switch_cmd_switch": _val(switch, "cmd_switch"),
            },
            "accuracy_known_high_vs_low": {
                "changed": _changed(accurate, inaccurate),
                "accurate_hit_chance": _val(accurate, "impact_hit_chance"),
                "inaccurate_hit_chance": _val(inaccurate, "impact_hit_chance"),
            },
        },
    }


if __name__ == "__main__":  # pragma: no cover
    import json

    print(json.dumps(evaluate_resolved_impact_counterfactuals(), indent=2, default=list))
