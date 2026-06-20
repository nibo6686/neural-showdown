"""legal-action-v5 (Slice 6) resolved-impact action features.

Asserts v3/v4 immutability and prefix integrity, name/dim stability, explicit
unavailable flags, and that resolved damage / KO / effectiveness / accuracy /
Soak / SpA-drop fields react through the real Smogon-backed estimator. Diagnostic
only; no live defaults are touched.
"""

import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM,
    ACTION_FEATURE_DIM_V4,
    ACTION_FEATURE_DIM_V5,
    ACTION_FEATURE_NAMES,
    ACTION_FEATURE_NAMES_V4,
    ACTION_FEATURE_NAMES_V5,
    ACTION_FEATURE_VERSION,
    ACTION_FEATURE_VERSION_V4,
    ACTION_FEATURE_VERSION_V5,
    SLICE6_ACTION_FEATURE_NAMES,
    build_action_feature_vector,
    build_action_feature_vector_v4,
    build_action_feature_vector_v5,
)
from neural.resolved_action_impact import resolve_action_impact
from neural.resolved_action_impact_diagnostic import (
    _action,
    _approx,
    evaluate_resolved_impact_counterfactuals,
)
from neural.tactical_state import build_tactical_state


def _idx(name):
    return ACTION_FEATURE_NAMES_V5.index(name)


def _val(vec, name):
    return float(vec[_idx(name)])


def _v5(move, attacker, defender, *, kind="move", side_conditions=None, **extra):
    action = _action(move, kind, **extra)
    impact = resolve_action_impact(action, _approx(attacker, defender, side_conditions=side_conditions))
    return build_action_feature_vector_v5(action, {"team": [{**attacker, "active": True}]}, {}, impact)


_LATIOS = {"species": "Latios", "level": 80, "types": ["Dragon", "Psychic"]}
_BLASTOISE = {"species": "Blastoise", "level": 80, "hp_fraction": 1.0, "types": ["Water"]}


class LegalActionV5Test(unittest.TestCase):
    def test_last_respects_scales_and_unknown_history_fails_closed(self):
        defender = {"species": "Mew", "level": 80, "hp_fraction": 1.0}
        zero = resolve_action_impact(
            _action("Last Respects"),
            _approx({"species": "Houndstone", "level": 80, "allies_fainted": 0}, defender),
        )
        three = resolve_action_impact(
            _action("Last Respects"),
            _approx({"species": "Houndstone", "level": 80, "allies_fainted": 3}, defender),
        )
        # v5 clips damage fractions at 1.0, so the 4x oracle increase saturates.
        self.assertGreater(three["expected_fraction"], zero["expected_fraction"] * 2.5)
        unknown = resolve_action_impact(
            _action("Last Respects"),
            _approx({"species": "Houndstone", "level": 80}, defender),
        )
        self.assertFalse(unknown["available"])
        self.assertEqual(unknown["fallback_reason"], "last_respects_fainted_allies_unknown")

        tactical = build_tactical_state(
            [
                "|start",
                "|switch|p1a: Houndstone|Houndstone, L80|100/100",
                "|switch|p1a: Pikachu|Pikachu, L80|0 fnt",
                "|faint|p1a: Pikachu",
                "|switch|p1a: Houndstone|Houndstone, L80|100/100",
            ],
            perspective_side="p1",
        )
        live_like = _approx({"species": "Houndstone", "level": 80}, defender)
        live_like["tactical_state"] = tactical
        live_impact = resolve_action_impact(_action("Last Respects"), live_like)
        self.assertTrue(live_impact["available"])
        self.assertGreater(live_impact["expected_fraction"], zero["expected_fraction"])

    def test_live_tactical_boosts_scale_stored_power(self):
        attacker = {"species": "Espeon", "level": 80}
        defender = {"species": "Mew", "level": 80, "hp_fraction": 1.0}
        base = _approx(attacker, defender)
        base["tactical_state"]["own"].update({"boosts": {}, "boosts_known": True})
        boosted = _approx(attacker, defender)
        boosted["tactical_state"]["own"].update(
            {"boosts": {"spa": 2, "spe": 2}, "boosts_known": True}
        )
        base_impact = resolve_action_impact(_action("Stored Power"), base)
        boosted_impact = resolve_action_impact(_action("Stored Power"), boosted)
        self.assertGreater(boosted_impact["expected_fraction"], base_impact["expected_fraction"] * 4.0)

        unknown = _approx(attacker, defender)
        unknown_impact = resolve_action_impact(_action("Stored Power"), unknown)
        self.assertFalse(unknown_impact["available"])
        self.assertEqual(unknown_impact["fallback_reason"], "positive_boost_stages_unknown")

    def test_curse_uses_existing_fields_for_ghost_and_non_ghost_forms(self):
        defender = {"species": "Mew", "level": 80, "hp_fraction": 1.0}
        ghost_action = _action("Curse")
        ghost_state = _approx(
            {"species": "Gengar", "level": 80, "types": ["Ghost", "Poison"]}, defender
        )
        ghost_impact = resolve_action_impact(ghost_action, ghost_state)
        ghost = build_action_feature_vector_v5(
            ghost_action,
            {"team": [{"species": "Gengar", "types": ["Ghost", "Poison"], "active": True}]},
            ghost_state["tactical_state"],
            ghost_impact,
        )
        normal_action = _action("Curse")
        normal_state = _approx(
            {"species": "Snorlax", "level": 80, "types": ["Normal"]}, defender
        )
        normal_impact = resolve_action_impact(normal_action, normal_state)
        normal = build_action_feature_vector_v5(
            normal_action,
            {"team": [{"species": "Snorlax", "types": ["Normal"], "active": True}]},
            normal_state["tactical_state"],
            normal_impact,
        )
        self.assertEqual(_val(ghost, "self_stat_delta_atk"), 0.0)
        self.assertEqual(_val(ghost, "next_own_hp_delta"), -0.5)
        self.assertEqual(_val(ghost, "next_opp_status_change"), 1.0)
        self.assertGreater(_val(normal, "self_stat_delta_atk"), 0.0)
        self.assertLess(_val(normal, "self_stat_delta_spe"), 0.0)
        self.assertEqual(_val(normal, "next_own_hp_delta"), 0.0)
    def test_rage_fist_resolved_impact_scales_with_times_attacked(self):
        defender = {"species": "Cresselia", "level": 80, "hp_fraction": 1.0, "types": ["Psychic"]}
        averages = []
        for hits in (0, 1, 2):
            attacker = {
                "species": "Annihilape",
                "level": 76,
                "types": ["Fighting", "Ghost"],
                "times_attacked": hits,
            }
            impact = resolve_action_impact(_action("Rage Fist"), _approx(attacker, defender))
            self.assertEqual(impact["method"], "smogon_calc")
            averages.append(impact["expected_fraction"])
        self.assertGreater(averages[1], averages[0] * 1.8)
        self.assertGreater(averages[2], averages[1] * 1.4)

        gunk_zero = resolve_action_impact(
            _action("Gunk Shot"),
            _approx(
                {"species": "Annihilape", "level": 76, "types": ["Fighting", "Ghost"], "times_attacked": 0},
                defender,
            ),
        )
        gunk_two = resolve_action_impact(
            _action("Gunk Shot"),
            _approx(
                {"species": "Annihilape", "level": 76, "types": ["Fighting", "Ghost"], "times_attacked": 2},
                defender,
            ),
        )
        self.assertAlmostEqual(gunk_zero["expected_fraction"], gunk_two["expected_fraction"], places=7)

    def test_rage_fist_unknown_counter_fails_closed(self):
        impact = resolve_action_impact(
            _action("Rage Fist"),
            _approx(
                {"species": "Annihilape", "level": 76, "types": ["Fighting", "Ghost"]},
                {"species": "Cresselia", "level": 80, "hp_fraction": 1.0, "types": ["Psychic"]},
            ),
        )
        self.assertFalse(impact["available"])
        self.assertEqual(impact["fallback_reason"], "rage_fist_times_attacked_unknown")

    def test_reversal_hp_scaling_and_unknown_hp_fail_closed(self):
        defender = {"species": "Mew", "level": 80, "hp_fraction": 1.0}
        high_hp = resolve_action_impact(
            _action("Reversal"),
            _approx({"species": "Lucario", "level": 80, "hp_fraction": 1.0}, defender),
        )
        low_hp = resolve_action_impact(
            _action("Reversal"),
            _approx({"species": "Lucario", "level": 80, "hp_fraction": 0.05}, defender),
        )
        self.assertEqual(high_hp["method"], "smogon_calc")
        self.assertGreater(low_hp["expected_fraction"], high_hp["expected_fraction"] * 5.0)

        unknown = resolve_action_impact(
            _action("Flail"),
            _approx({"species": "Snorlax", "level": 80}, defender),
        )
        self.assertFalse(unknown["available"])
        self.assertEqual(unknown["fallback_reason"], "variable_power_user_hp_unknown")

    def test_speed_ratio_variable_power_moves(self):
        defender_fast = {"species": "Mew", "level": 80, "hp_fraction": 1.0, "stats": {"spe": 300}}
        defender_slow = {"species": "Mew", "level": 80, "hp_fraction": 1.0, "stats": {"spe": 50}}
        gyro_slow = resolve_action_impact(
            _action("Gyro Ball"),
            _approx({"species": "Ferrothorn", "level": 80, "stats": {"spe": 30}}, defender_fast),
        )
        gyro_fast = resolve_action_impact(
            _action("Gyro Ball"),
            _approx({"species": "Ferrothorn", "level": 80, "stats": {"spe": 200}}, defender_slow),
        )
        self.assertGreater(gyro_slow["expected_fraction"], gyro_fast["expected_fraction"] * 5.0)

        electro_fast = resolve_action_impact(
            _action("Electro Ball"),
            _approx({"species": "Electrode", "level": 80, "stats": {"spe": 300}}, defender_slow),
        )
        electro_slow = resolve_action_impact(
            _action("Electro Ball"),
            _approx({"species": "Electrode", "level": 80, "stats": {"spe": 50}}, defender_fast),
        )
        self.assertGreater(electro_fast["expected_fraction"], electro_slow["expected_fraction"] * 2.0)

    def test_target_weight_variable_power_moves(self):
        attacker = {"species": "Mew", "level": 80}
        grass_light = resolve_action_impact(
            _action("Grass Knot"),
            _approx(
                attacker,
                {"species": "Gastly", "level": 80, "hp_fraction": 1.0, "stats": {"hp": 200, "spd": 100}},
            ),
        )
        grass_heavy = resolve_action_impact(
            _action("Grass Knot"),
            _approx(
                attacker,
                {"species": "Gengar", "level": 80, "hp_fraction": 1.0, "stats": {"hp": 200, "spd": 100}},
            ),
        )
        self.assertGreater(grass_heavy["expected_fraction"], grass_light["expected_fraction"] * 2.0)

        kick_light = resolve_action_impact(
            _action("Low Kick"),
            _approx(
                attacker,
                {"species": "Pichu", "level": 80, "hp_fraction": 1.0, "stats": {"hp": 200, "def": 100}},
            ),
        )
        kick_heavy = resolve_action_impact(
            _action("Low Kick"),
            _approx(
                attacker,
                {"species": "Raichu", "level": 80, "hp_fraction": 1.0, "stats": {"hp": 200, "def": 100}},
            ),
        )
        self.assertGreater(kick_heavy["expected_fraction"], kick_light["expected_fraction"] * 2.0)

    def test_weight_ratio_moves_and_fixed_power_control(self):
        attacker = {"species": "Copperajah", "level": 80}
        light_target = {
            "species": "Donphan",
            "level": 80,
            "hp_fraction": 1.0,
            "stats": {"hp": 200, "def": 100},
        }
        heavy_target = {
            "species": "Mudsdale",
            "level": 80,
            "hp_fraction": 1.0,
            "stats": {"hp": 200, "def": 100},
        }
        heavy_slam_light = resolve_action_impact(_action("Heavy Slam"), _approx(attacker, light_target))
        heavy_slam_heavy = resolve_action_impact(_action("Heavy Slam"), _approx(attacker, heavy_target))
        self.assertGreater(
            heavy_slam_light["expected_fraction"],
            heavy_slam_heavy["expected_fraction"] * 2.0,
        )

        heat_crash_light = resolve_action_impact(_action("Heat Crash"), _approx(attacker, light_target))
        heat_crash_heavy = resolve_action_impact(_action("Heat Crash"), _approx(attacker, heavy_target))
        self.assertGreater(
            heat_crash_light["expected_fraction"],
            heat_crash_heavy["expected_fraction"] * 2.0,
        )

        psychic_high_hp = resolve_action_impact(
            _action("Psychic"),
            _approx({"species": "Mew", "level": 80, "hp_fraction": 1.0}, heavy_target),
        )
        psychic_low_hp = resolve_action_impact(
            _action("Psychic"),
            _approx({"species": "Mew", "level": 80, "hp_fraction": 0.05}, heavy_target),
        )
        self.assertAlmostEqual(
            psychic_high_hp["expected_fraction"],
            psychic_low_hp["expected_fraction"],
            places=7,
        )

    def test_versions_dims_and_prefix_integrity(self):
        self.assertEqual(ACTION_FEATURE_VERSION, "legal-action-v3")
        self.assertEqual(ACTION_FEATURE_VERSION_V4, "legal-action-v4")
        self.assertEqual(ACTION_FEATURE_VERSION_V5, "legal-action-v5")
        self.assertEqual(ACTION_FEATURE_DIM, 165)
        self.assertEqual(ACTION_FEATURE_DIM_V4, 269)
        self.assertEqual(ACTION_FEATURE_DIM_V5, 318)
        self.assertEqual(ACTION_FEATURE_DIM_V5, ACTION_FEATURE_DIM_V4 + len(SLICE6_ACTION_FEATURE_NAMES))
        # v4 is the exact ordered prefix of v5; names unique.
        self.assertEqual(ACTION_FEATURE_NAMES_V5[:ACTION_FEATURE_DIM_V4], ACTION_FEATURE_NAMES_V4)
        self.assertEqual(ACTION_FEATURE_NAMES_V5[ACTION_FEATURE_DIM_V4:], SLICE6_ACTION_FEATURE_NAMES)
        self.assertEqual(len(set(ACTION_FEATURE_NAMES_V5)), len(ACTION_FEATURE_NAMES_V5))

    def test_v3_and_v4_remain_exact_prefixes_of_v5_vector(self):
        action = _action("Draco Meteor")
        private = {"team": []}
        v3 = build_action_feature_vector(action, private, {})
        v4 = build_action_feature_vector_v4(action, private, {})
        v5 = build_action_feature_vector_v5(action, private, {}, None)
        self.assertTrue(np.allclose(v5[:ACTION_FEATURE_DIM], v3))
        self.assertTrue(np.allclose(v5[:ACTION_FEATURE_DIM_V4], v4))

    def test_unavailable_impact_fields_are_explicit(self):
        # A damaging move built without a resolved impact: fields present, flagged.
        v5 = build_action_feature_vector_v5(_action("Surf"), {"team": []}, {}, None)
        self.assertEqual(_val(v5, "impact_unknown"), 1.0)
        self.assertEqual(_val(v5, "impact_method_unavailable"), 1.0)
        self.assertEqual(_val(v5, "next_state_source_unavailable"), 1.0)
        self.assertEqual(_val(v5, "impact_expected_damage_fraction"), 0.0)

    def test_damaging_move_populates_damage_fields(self):
        v5 = _v5("Surf", _BLASTOISE, {"species": "Charizard", "level": 80, "hp_fraction": 1.0, "types": ["Fire", "Flying"]})
        self.assertEqual(_val(v5, "impact_method_smogon_calc"), 1.0)
        self.assertGreater(_val(v5, "impact_expected_damage_fraction"), 0.0)
        self.assertEqual(_val(v5, "impact_super_effective"), 1.0)
        self.assertEqual(_val(v5, "impact_unknown"), 0.0)
        self.assertLess(_val(v5, "next_opp_hp_delta"), 0.0)

    def test_non_damaging_move_flags(self):
        v5 = _v5("Calm Mind", _LATIOS, _BLASTOISE)
        self.assertEqual(_val(v5, "action_non_damaging"), 1.0)
        self.assertEqual(_val(v5, "impact_method_non_damaging"), 1.0)
        self.assertEqual(_val(v5, "impact_unknown"), 0.0)
        self.assertEqual(_val(v5, "impact_expected_damage_fraction"), 0.0)

    def test_immunity_and_effectiveness(self):
        immune = _v5("Earthquake", {"species": "Diglett", "level": 80, "types": ["Ground"]},
                     {"species": "Charizard", "level": 80, "hp_fraction": 1.0, "types": ["Fire", "Flying"]})
        self.assertEqual(_val(immune, "impact_immune"), 1.0)
        self.assertEqual(_val(immune, "impact_expected_damage_fraction"), 0.0)
        resisted = _v5("Psychic", _LATIOS, {"species": "Metagross", "level": 80, "hp_fraction": 1.0, "types": ["Steel", "Psychic"]})
        self.assertEqual(_val(resisted, "impact_resisted"), 1.0)
        self.assertEqual(_val(resisted, "impact_super_effective"), 0.0)

    def test_soak_current_type_changes_resolved_impact(self):
        eevee = {"species": "Eevee", "level": 80, "hp_fraction": 1.0, "types": ["Normal"]}
        raichu = {"species": "Raichu", "level": 80, "types": ["Electric"]}
        before = _v5("Thunderbolt", raichu, dict(eevee))
        after = _v5("Thunderbolt", raichu, {**eevee, "types_override": ["Water"]})
        self.assertEqual(_val(before, "impact_super_effective"), 0.0)
        self.assertEqual(_val(after, "impact_super_effective"), 1.0)
        self.assertGreater(_val(after, "impact_expected_damage_fraction"), _val(before, "impact_expected_damage_fraction"))

    def test_spa_drop_reduces_resolved_special_damage(self):
        full = _v5("Psychic", _LATIOS, _BLASTOISE)
        dropped = _v5("Psychic", {**_LATIOS, "boosts": {"spa": -2}}, _BLASTOISE)
        self.assertLess(
            _val(dropped, "impact_expected_damage_fraction"),
            _val(full, "impact_expected_damage_fraction"),
        )

    def test_switch_action_has_valid_unavailable_fields(self):
        impact = resolve_action_impact(_action("Latias", "switch", index=9))
        v5 = build_action_feature_vector_v5(
            _action("Latias", "switch", index=9), {"team": [{"species": "Latias"}]}, {}, impact
        )
        self.assertEqual(_val(v5, "action_non_damaging"), 1.0)
        self.assertEqual(_val(v5, "impact_method_unavailable"), 1.0)
        self.assertEqual(_val(v5, "cmd_switch"), 1.0)  # v4 switch field still valid
        self.assertEqual(_val(v5, "impact_unknown"), 0.0)  # switch is not "unknown damage"

    def test_accuracy_known_high_vs_low(self):
        accurate = _v5("Psychic", _LATIOS, _BLASTOISE)
        inaccurate = _v5("Focus Blast", _LATIOS, _BLASTOISE)
        self.assertEqual(_val(accurate, "impact_accuracy_known"), 1.0)
        self.assertEqual(_val(accurate, "impact_hit_chance"), 1.0)
        self.assertAlmostEqual(_val(inaccurate, "impact_hit_chance"), 0.7, places=3)

    def test_all_counterfactuals_change_features(self):
        report = evaluate_resolved_impact_counterfactuals()
        self.assertEqual(report["action_feature_version"], ACTION_FEATURE_VERSION_V5)
        self.assertEqual(report["action_feature_dim"], ACTION_FEATURE_DIM_V5)
        for name, comparison in report["comparisons"].items():
            self.assertTrue(comparison["changed"], f"counterfactual {name} produced no change")


if __name__ == "__main__":
    unittest.main()
