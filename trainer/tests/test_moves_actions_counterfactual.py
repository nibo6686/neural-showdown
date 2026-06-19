import unittest

from neural.action_features import ACTION_FEATURE_DIM_V4, ACTION_FEATURE_VERSION_V4
from neural.live_private_features import FEATURE_DIM_V7, FEATURE_VERSION_V7
from neural.moves_actions_counterfactual_diagnostic import (
    evaluate_action_counterfactuals,
    evaluate_moves_actions_counterfactuals,
    evaluate_state_counterfactuals,
)


class MovesActionsCounterfactualTest(unittest.TestCase):
    def test_report_versions_and_dims(self):
        report = evaluate_moves_actions_counterfactuals()
        self.assertEqual(report["state_feature_version"], FEATURE_VERSION_V7)
        self.assertEqual(report["state_feature_dim"], FEATURE_DIM_V7)
        self.assertEqual(report["action_feature_version"], ACTION_FEATURE_VERSION_V4)
        self.assertEqual(report["action_feature_dim"], ACTION_FEATURE_DIM_V4)

    def test_every_state_counterfactual_changes_features(self):
        for name, changed in evaluate_state_counterfactuals().items():
            self.assertTrue(changed, f"state counterfactual {name} produced no change")

    def test_action_counterfactuals_capture_side_effects(self):
        action = evaluate_action_counterfactuals()
        draco = action["draco_vs_no_drawback_self_spa"]
        self.assertEqual(draco["draco_self_spa_delta"], -1.0)
        self.assertEqual(draco["psyshock_self_spa_delta"], 0.0)
        self.assertTrue(draco["changed"])

        curse = action["curse_vs_bulk_up_speed"]
        self.assertEqual(curse["curse_spe"], -0.5)
        self.assertEqual(curse["bulk_up_spe"], 0.0)
        self.assertEqual(curse["curse_atk"], curse["bulk_up_atk"])
        self.assertEqual(curse["curse_def"], curse["bulk_up_def"])

        for key in (
            "damaging_vs_status",
            "tera_move_vs_normal",
            "switch_vs_move",
            "disabled_vs_enabled",
        ):
            self.assertTrue(action[key], f"action counterfactual {key} produced no change")

        self.assertTrue(action["priority_vs_non_priority"]["changed"])
        self.assertEqual(action["recoil_vs_no_recoil"]["flare_blitz_recoil"], 1.0)
        self.assertEqual(action["recoil_vs_no_recoil"]["fire_punch_recoil"], 0.0)


if __name__ == "__main__":
    unittest.main()
