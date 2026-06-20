"""Mechanics repair batch 4: conditional execution/success and turn/history power.

Diagnostic-only. Asserts that moves whose success or power depends on the
opponent's same-turn action, the first-active turn, the user's form/target item,
within-turn order, or unplumbed prior-move-failure history fail closed
(impact_unknown) instead of claiming they deal damage; that singles-exact moves
(Fusion Bolt, Pollen Puff) stay PASS; that Brick Break / Psychic Fangs keep their
exact (screen-bypassing) damage while flagging the screen removal as a field/side
change; and that an ordinary move is unaffected. No schema name/order/dim change.
"""

import unittest

from neural.action_features import (
    SLICE6_ACTION_FEATURE_NAMES,
    slice6_resolved_impact_feature_vector,
)
from neural.resolved_action_impact import resolve_action_impact
from neural.resolved_action_impact_diagnostic import _action, _approx

_CRESSELIA = {"species": "Cresselia", "level": 80, "hp_fraction": 1.0, "types": ["Psychic"]}


def _impact(move, attacker, defender=_CRESSELIA):
    return resolve_action_impact(_action(move), _approx(attacker, defender))


def _field_flag(move):
    vec = slice6_resolved_impact_feature_vector(_action(move), None, None)
    return float(vec[SLICE6_ACTION_FEATURE_NAMES.index("next_field_or_side_change")])


class ConditionalExecutionTest(unittest.TestCase):
    def test_first_turn_moves_fail_closed(self):
        # Fake Out / First Impression only work on the first active turn.
        for move in ("Fake Out", "First Impression"):
            impact = _impact(move, {"species": "Lopunny", "level": 80, "types": ["Normal"]})
            self.assertFalse(impact["available"], move)
            self.assertEqual(impact["fallback_reason"], "conditional_execution_or_history", move)
            self.assertEqual(impact["dynamic_dependency"], "first_active_turn", move)

    def test_opponent_action_dependent_moves_fail_closed(self):
        for move in ("Sucker Punch", "Thunderclap", "Focus Punch"):
            impact = _impact(move, {"species": "Houndstone", "level": 80, "types": ["Ghost"]})
            self.assertFalse(impact["available"], move)
            self.assertEqual(impact["dynamic_dependency"], "opponent_action", move)

    def test_poltergeist_depends_on_target_item(self):
        impact = _impact("Poltergeist", {"species": "Dragapult", "level": 80, "types": ["Dragon", "Ghost"]})
        self.assertFalse(impact["available"])
        self.assertEqual(impact["dynamic_dependency"], "target_item_presence")


class HistoryPowerTest(unittest.TestCase):
    def test_same_turn_and_prior_failure_power_fail_closed(self):
        cases = {
            "Payback": "same_turn_order",
            "Avalanche": "same_turn_hit",
            "Lash Out": "same_turn_stat_drop",
            "Stomping Tantrum": "prior_move_failure",
            "Temper Flare": "prior_move_failure",
        }
        for move, dep in cases.items():
            impact = _impact(move, {"species": "Garchomp", "level": 80, "types": ["Dragon", "Ground"]})
            self.assertFalse(impact["available"], move)
            self.assertEqual(impact["dynamic_dependency"], dep, move)

    def test_fusion_moves_exact_in_singles(self):
        # The partner-fusion same-turn doubling cannot occur in singles -> exact.
        impact = _impact("Fusion Bolt", {"species": "Zekrom", "level": 80, "types": ["Dragon", "Electric"]})
        self.assertTrue(impact["available"])
        self.assertEqual(impact["method"], "smogon_calc")
        self.assertGreater(impact["expected_fraction"], 0.0)


class ConditionalUtilityTest(unittest.TestCase):
    def test_pollen_puff_damages_in_singles(self):
        impact = _impact("Pollen Puff", {"species": "Volcarona", "level": 80, "types": ["Bug", "Fire"]})
        self.assertTrue(impact["available"])
        self.assertGreater(impact["expected_fraction"], 0.0)

    def test_brick_break_damage_exact_with_field_change_flag(self):
        impact = _impact("Brick Break", {"species": "Machamp", "level": 80, "types": ["Fighting"]})
        self.assertTrue(impact["available"])  # damage is exact (calc bypasses screens)
        self.assertEqual(impact["method"], "smogon_calc")
        # Screen removal is coarsely flagged as a field/side change.
        self.assertEqual(_field_flag("Brick Break"), 1.0)
        self.assertEqual(_field_flag("Psychic Fangs"), 1.0)

    def test_ordinary_move_unaffected(self):
        impact = _impact("Surf", {"species": "Blastoise", "level": 80, "types": ["Water"]})
        self.assertTrue(impact["available"])
        self.assertEqual(impact["method"], "smogon_calc")
        self.assertGreater(impact["expected_fraction"], 0.0)
        self.assertEqual(_field_flag("Surf"), 0.0)


if __name__ == "__main__":
    unittest.main()
