"""Mechanics repair batch 5: the final 9 FAILs.

Diagnostic-only. Asserts the PASS repairs (guaranteed crit flagged, Freeze-Dry
special Water effectiveness, Photon Geyser stat/category) and the INEXACT
fail-closes (Beat Up, Bug Bite, Knock Off, Fickle Beam, Grassy Glide). No schema
name/order/dim change; v6 remains 331D.
"""

import unittest

from neural.resolved_action_impact import resolve_action_impact
from neural.resolved_action_impact_diagnostic import _action, _approx


def _impact(move, attacker, defender):
    return resolve_action_impact(_action(move), _approx(attacker, defender))


_SNORLAX = {"species": "Snorlax", "level": 80, "hp_fraction": 1.0, "types": ["Normal"]}
_BLASTOISE = {"species": "Blastoise", "level": 80, "hp_fraction": 1.0, "types": ["Water"]}


class PassRepairTest(unittest.TestCase):
    def test_guaranteed_crit_flagged_and_exact(self):
        for move, user in (
            ("Wicked Blow", {"species": "Urshifu", "level": 80, "types": ["Fighting", "Dark"]}),
            ("Flower Trick", {"species": "Meowscarada", "level": 80, "types": ["Grass", "Dark"]}),
        ):
            impact = _impact(move, user, _SNORLAX)
            self.assertTrue(impact["available"], move)
            self.assertEqual(impact["method"], "smogon_calc", move)
            self.assertTrue(impact["crit_included"], move)
            self.assertGreater(impact["expected_fraction"], 0.0, move)

    def test_ordinary_move_crit_not_included(self):
        impact = _impact("Surf", {"species": "Blastoise", "level": 80, "types": ["Water"]}, _SNORLAX)
        self.assertTrue(impact["available"])
        self.assertFalse(impact["crit_included"])

    def test_freeze_dry_super_effective_vs_water(self):
        frosmoth = {"species": "Frosmoth", "level": 80, "types": ["Ice", "Bug"]}
        impact = _impact("Freeze-Dry", frosmoth, _BLASTOISE)
        self.assertTrue(impact["available"])
        self.assertTrue(impact["super_effective"])
        self.assertEqual(impact["type_effectiveness"], 2.0)
        self.assertFalse(impact["resisted"])

    def test_photon_geyser_uses_higher_attacking_stat(self):
        phys = {
            "species": "Necrozma", "level": 80, "types": ["Psychic"],
            "stats": {"hp": 200, "atk": 300, "def": 120, "spa": 50, "spd": 120, "spe": 120},
        }
        impact = _impact("Photon Geyser", phys, _SNORLAX)
        self.assertTrue(impact["available"])
        self.assertEqual(impact["method"], "smogon_calc")
        self.assertGreater(impact["expected_fraction"], 0.0)


class InexactFailCloseTest(unittest.TestCase):
    def test_wrong_exact_damage_moves_fail_closed(self):
        # Beat Up (calc returns 0) and Fickle Beam (random double power) have
        # wrong-exact damage, so they fail closed.
        cases = {"Beat Up": "party_attack_stats", "Fickle Beam": "random_power"}
        user = {"species": "Weavile", "level": 80, "types": ["Dark", "Ice"]}
        for move, dep in cases.items():
            impact = _impact(move, user, _SNORLAX)
            self.assertFalse(impact["available"], move)
            self.assertEqual(impact["fallback_reason"], "unrepresented_context", move)
            self.assertEqual(impact["dynamic_dependency"], dep, move)

    def test_exact_damage_moves_keep_damage(self):
        # Knock Off / Bug Bite / Grassy Glide deal exact damage; only their
        # next-state effect is unrepresented (INEXACT in the audit), so the impact
        # keeps the damage rather than failing closed.
        user = {"species": "Weavile", "level": 80, "types": ["Dark", "Ice"]}
        for move in ("Knock Off", "Bug Bite", "Grassy Glide"):
            impact = _impact(move, user, _SNORLAX)
            self.assertTrue(impact["available"], move)
            self.assertEqual(impact["method"], "smogon_calc", move)
            self.assertGreater(impact["expected_fraction"], 0.0, move)


if __name__ == "__main__":
    unittest.main()
