import os
import unittest

import numpy as np

from neural.one_turn_branch import make_material_score_fn, make_state_score_fn
from neural.live_private_features import FEATURE_NAMES, build_features_from_live_payload
from neural.state_counterfactual_diagnostic import (
    SCENARIOS,
    Scenario,
    _features_for,
    build_protocol_log,
    build_transition_diagnostic,
    build_view_step_result,
)


def _scenario(name):
    return next(item for item in SCENARIOS if item.name == name)


class StateCounterfactualDiagnosticTest(unittest.TestCase):
    def test_generator_changes_only_active_boosts(self):
        neutral = build_view_step_result(_scenario("neutral"))
        changed = build_view_step_result(_scenario("own_spa_-2"))
        neutral_active = neutral["views"]["p1"]["self_team"][0]
        changed_active = changed["views"]["p1"]["self_team"][0]

        self.assertEqual(neutral_active["boosts"], {})
        self.assertEqual(changed_active["boosts"], {"spa": -2})
        neutral_active["boosts"] = changed_active["boosts"]
        self.assertEqual(neutral, changed)

    def test_material_is_intentionally_boost_insensitive(self):
        score = make_material_score_fn()
        neutral = score([], build_view_step_result(_scenario("neutral")), "p1")
        all_down = score([], build_view_step_result(_scenario("own_all_-6")), "p1")
        self.assertEqual(neutral, all_down)

    def test_state_scorer_penalizes_all_stats_down_and_flips_perspective(self):
        score = make_state_score_fn()
        scenario = _scenario("own_all_-6")
        p1 = score([], build_view_step_result(scenario, perspective="p1"), "p1")
        p2 = score([], build_view_step_result(scenario, perspective="p2"), "p2")
        self.assertLess(p1, 0.0)
        self.assertGreater(p2, 0.0)
        self.assertAlmostEqual(p1, -p2, places=6)

    def test_live_features_change_for_boosts_but_lose_stat_identity(self):
        neutral = _features_for(_scenario("neutral"))
        spa_down = _features_for(_scenario("own_spa_-2"))
        spe_down = _features_for(
            Scenario(
                "own_spe_-2",
                {"spe": -2},
                {},
                "own active Spe -2",
                "diagnostic",
                None,
                "diagnostic",
            )
        )
        self.assertFalse(np.allclose(neutral, spa_down))
        np.testing.assert_allclose(spa_down, spe_down, atol=1e-7)

        opp_def = _features_for(_scenario("opp_def_-2"))
        opp_spd = _features_for(_scenario("opp_spd_-2"))
        np.testing.assert_allclose(opp_def, opp_spd, atol=1e-7)

    def test_public_boost_features_flip_with_player_perspective(self):
        log = build_protocol_log(_scenario("own_spa_-6"))
        p1, *_ = build_features_from_live_payload(
            log=log,
            room_id="counterfactual-p1",
            url="cf://p1",
            player="p1",
            request_payload=None,
            legal_actions=[],
        )
        p2, *_ = build_features_from_live_payload(
            log=log,
            room_id="counterfactual-p2",
            url="cf://p2",
            player="p2",
            request_payload=None,
            legal_actions=[],
        )
        diff = FEATURE_NAMES.index("boost_sum_diff_p1_minus_p2")
        self.assertAlmostEqual(float(p1[diff]), -float(p2[diff]), places=7)

    def test_draco_transition_contains_spa_drop_when_sim_core_is_available(self):
        if not os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON"):
            self.skipTest("sim-core command is not configured")
        result = build_transition_diagnostic()
        self.assertNotIn("error", result)
        self.assertEqual(result["post_drop"]["own_active_boosts"].get("spa"), -2)
        self.assertTrue(result["deltas"]["drop_post_has_spa_drop"])
        self.assertEqual(result["deltas"]["isolated_drop_stage_effect"]["material"], 0.0)
        self.assertLess(result["deltas"]["isolated_drop_stage_effect"]["state"], 0.0)


if __name__ == "__main__":
    unittest.main()
