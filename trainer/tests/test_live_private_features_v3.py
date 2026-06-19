import tempfile
import unittest
from pathlib import Path

import numpy as np

from neural.live_private_features import (
    FEATURE_DIM,
    FEATURE_DIM_V3,
    FEATURE_NAMES,
    FEATURE_NAMES_V3,
    FEATURE_VERSION,
    FEATURE_VERSION_V3,
    V3_SLICE1_FEATURE_NAMES,
    V3_STAGE_STATS,
    build_features_from_live_payload,
    validate_live_private_feature_metadata,
)
from neural.state_counterfactual_diagnostic import (
    SCENARIOS,
    Scenario,
    build_current_typing_diagnostic,
    build_protocol_log,
)


def _scenario(name):
    return next(item for item in SCENARIOS if item.name == name)


def _features(scenario, version, player="p1"):
    features, *_ = build_features_from_live_payload(
        log=build_protocol_log(scenario),
        room_id=f"v3-{scenario.name}-{player}",
        url="cf://v3",
        player=player,
        request_payload=None,
        legal_actions=[],
        feature_version=version,
    )
    return features


class LivePrivateFeaturesV3Test(unittest.TestCase):
    def test_v3_schema_is_stable_and_v2_is_unchanged(self):
        self.assertEqual(FEATURE_VERSION, "live-private-belief-v2")
        self.assertEqual(FEATURE_DIM, 115)
        self.assertEqual(len(FEATURE_NAMES), FEATURE_DIM)
        self.assertEqual(FEATURE_VERSION_V3, "live-private-belief-v3")
        self.assertEqual(FEATURE_DIM_V3, 217)
        self.assertEqual(len(FEATURE_NAMES_V3), FEATURE_DIM_V3)
        self.assertEqual(FEATURE_NAMES_V3[:FEATURE_DIM], FEATURE_NAMES)
        self.assertEqual(FEATURE_NAMES_V3[FEATURE_DIM:], V3_SLICE1_FEATURE_NAMES)

    def test_v2_checkpoint_metadata_remains_v2_only_and_v3_rejects_it(self):
        validate_live_private_feature_metadata(
            feature_version=FEATURE_VERSION,
            feature_dim=FEATURE_DIM,
            expected_version=FEATURE_VERSION,
        )
        with self.assertRaises(ValueError):
            validate_live_private_feature_metadata(
                feature_version=FEATURE_VERSION,
                feature_dim=FEATURE_DIM,
                expected_version=FEATURE_VERSION_V3,
            )

        from neural.live_eval_server import _validate_live_private_checkpoint

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metadata-only.pt"
            _validate_live_private_checkpoint(
                {"feature_version": FEATURE_VERSION, "input_size": FEATURE_DIM},
                path,
            )
            with self.assertRaises(ValueError):
                _validate_live_private_checkpoint(
                    {"feature_version": FEATURE_VERSION_V3, "input_size": FEATURE_DIM_V3},
                    path,
                )

    def test_spa_and_speed_drops_change_distinct_v3_stage_features(self):
        neutral = _features(_scenario("neutral"), FEATURE_VERSION_V3)
        spa = _features(_scenario("own_spa_-6"), FEATURE_VERSION_V3)
        speed = _features(_scenario("own_spe_-6"), FEATURE_VERSION_V3)

        spa_name = "own_active_spa_stage_norm"
        speed_name = "own_active_spe_stage_norm"
        self.assertEqual(float(spa[FEATURE_NAMES_V3.index(spa_name)]), -1.0)
        self.assertEqual(float(spa[FEATURE_NAMES_V3.index(speed_name)]), 0.0)
        self.assertEqual(float(speed[FEATURE_NAMES_V3.index(spa_name)]), 0.0)
        self.assertEqual(float(speed[FEATURE_NAMES_V3.index(speed_name)]), -1.0)
        self.assertFalse(np.allclose(spa, speed))

        stage_names = [
            name for name in V3_SLICE1_FEATURE_NAMES
            if name.startswith("own_active_") and name.endswith("_stage_norm")
        ]
        spa_changed = {
            name for name in stage_names
            if not np.isclose(spa[FEATURE_NAMES_V3.index(name)], neutral[FEATURE_NAMES_V3.index(name)])
        }
        speed_changed = {
            name for name in stage_names
            if not np.isclose(speed[FEATURE_NAMES_V3.index(name)], neutral[FEATURE_NAMES_V3.index(name)])
        }
        self.assertEqual(spa_changed, {spa_name})
        self.assertEqual(speed_changed, {speed_name})

    def test_v2_still_aliases_spa_and_speed_but_v3_does_not(self):
        spa_v2 = _features(_scenario("own_spa_-6"), FEATURE_VERSION)
        speed_v2 = _features(_scenario("own_spe_-6"), FEATURE_VERSION)
        np.testing.assert_allclose(spa_v2, speed_v2, atol=1e-7)

        spa_v3 = _features(_scenario("own_spa_-6"), FEATURE_VERSION_V3)
        speed_v3 = _features(_scenario("own_spe_-6"), FEATURE_VERSION_V3)
        self.assertFalse(np.allclose(spa_v3, speed_v3))

    def test_all_seven_own_stages_change(self):
        neutral = _features(_scenario("neutral"), FEATURE_VERSION_V3)
        all_down = _features(_scenario("own_all_-6"), FEATURE_VERSION_V3)
        changed = []
        for stat in V3_STAGE_STATS:
            name = f"own_active_{stat}_stage_norm"
            index = FEATURE_NAMES_V3.index(name)
            self.assertEqual(float(all_down[index]), -1.0)
            if not np.isclose(neutral[index], all_down[index]):
                changed.append(name)
        self.assertEqual(len(changed), 7)

    def test_opponent_def_drop_and_perspective_flip(self):
        scenario = _scenario("opp_def_-2")
        p1 = _features(scenario, FEATURE_VERSION_V3, player="p1")
        p2 = _features(scenario, FEATURE_VERSION_V3, player="p2")
        p1_opp = FEATURE_NAMES_V3.index("opponent_active_def_stage_norm")
        p2_own = FEATURE_NAMES_V3.index("own_active_def_stage_norm")
        self.assertAlmostEqual(float(p1[p1_opp]), -2.0 / 6.0)
        self.assertAlmostEqual(float(p2[p2_own]), -2.0 / 6.0)

        own_spa = _scenario("own_spa_-6")
        p1_own_state = _features(own_spa, FEATURE_VERSION_V3, player="p1")
        p2_opp_state = _features(own_spa, FEATURE_VERSION_V3, player="p2")
        self.assertEqual(
            float(p1_own_state[FEATURE_NAMES_V3.index("own_active_spa_stage_norm")]),
            float(p2_opp_state[FEATURE_NAMES_V3.index("opponent_active_spa_stage_norm")]),
        )

    def test_soak_preserves_base_type_and_changes_current_type(self):
        report = build_current_typing_diagnostic()
        self.assertEqual(report["v3_base_type_fire"], 1.0)
        self.assertEqual(report["v3_base_type_flying"], 1.0)
        self.assertEqual(report["v3_current_type_water"], 1.0)
        self.assertEqual(report["v3_current_type_fire"], 0.0)
        self.assertEqual(report["v3_current_source_protocol_typechange"], 1.0)
        changed_names = {row["name"] for row in report["v3_changes"]}
        self.assertIn("opponent_active_current_type_water", changed_names)
        self.assertIn("opponent_active_current_type_fire", changed_names)
        self.assertNotIn("opponent_active_base_type_fire", changed_names)
        self.assertNotIn("opponent_active_base_type_flying", changed_names)

    def test_unknown_type_source_is_explicit(self):
        unknown = Scenario("unknown", {}, {}, "none", "diagnostic", None, "diagnostic")
        features, debug, *_ = build_features_from_live_payload(
            log=["|start", "|turn|1"],
            room_id="v3-unknown",
            url="cf://unknown",
            player="p1",
            request_payload=None,
            legal_actions=[],
            feature_version=FEATURE_VERSION_V3,
        )
        self.assertEqual(debug["feature_version"], FEATURE_VERSION_V3)
        self.assertEqual(
            float(features[FEATURE_NAMES_V3.index("own_active_current_type_source_unknown")]),
            1.0,
        )


if __name__ == "__main__":
    unittest.main()
