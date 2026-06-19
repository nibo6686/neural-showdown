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
