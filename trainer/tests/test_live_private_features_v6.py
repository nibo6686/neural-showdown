import tempfile
import unittest
from pathlib import Path

import numpy as np

from neural.live_private_features import (
    FEATURE_DIM,
    FEATURE_DIM_V3,
    FEATURE_DIM_V4,
    FEATURE_DIM_V5,
    FEATURE_DIM_V6,
    FEATURE_NAMES,
    FEATURE_NAMES_V3,
    FEATURE_NAMES_V4,
    FEATURE_NAMES_V5,
    FEATURE_NAMES_V6,
    FEATURE_VERSION,
    FEATURE_VERSION_V6,
    V6_SLICE4_FEATURE_NAMES,
    validate_live_private_feature_metadata,
)
from neural.tera_field_counterfactual_diagnostic import (
    BASE_LOG,
    _features,
    _request,
    evaluate_tera_field_counterfactuals,
)


def _value(features, name):
    return float(features[FEATURE_NAMES_V6.index(name)])


class LivePrivateFeaturesV6Test(unittest.TestCase):
    def test_v6_is_immutable_extension_and_older_versions_are_unchanged(self):
        self.assertEqual(FEATURE_VERSION, "live-private-belief-v2")
        self.assertEqual(FEATURE_DIM, 115)
        self.assertEqual(FEATURE_DIM_V3, 217)
        self.assertEqual(FEATURE_DIM_V4, 765)
        self.assertEqual(FEATURE_DIM_V5, 2293)
        self.assertEqual(FEATURE_VERSION_V6, "live-private-belief-v6")
        self.assertEqual(FEATURE_DIM_V6, 2493)
        self.assertEqual(FEATURE_NAMES_V3[:FEATURE_DIM], FEATURE_NAMES)
        self.assertEqual(FEATURE_NAMES_V4[:FEATURE_DIM_V3], FEATURE_NAMES_V3)
        self.assertEqual(FEATURE_NAMES_V5[:FEATURE_DIM_V4], FEATURE_NAMES_V4)
        self.assertEqual(FEATURE_NAMES_V6[:FEATURE_DIM_V5], FEATURE_NAMES_V5)
        self.assertEqual(FEATURE_NAMES_V6[FEATURE_DIM_V5:], V6_SLICE4_FEATURE_NAMES)

    def test_metadata_is_strict_and_live_default_remains_v2(self):
        validate_live_private_feature_metadata(
            feature_version=FEATURE_VERSION_V6,
            feature_dim=FEATURE_DIM_V6,
            expected_version=FEATURE_VERSION_V6,
        )
        with self.assertRaises(ValueError):
            validate_live_private_feature_metadata(
                feature_version=FEATURE_VERSION,
                feature_dim=FEATURE_DIM,
                expected_version=FEATURE_VERSION_V6,
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
                    {"feature_version": FEATURE_VERSION_V6, "input_size": FEATURE_DIM_V6},
                    path,
                )

    def test_tera_availability_state_and_type_are_represented(self):
        available = _features(request=_request(can_tera="Fire"))
        unavailable = _features(request=_request(can_tera=None))
        self.assertEqual(_value(available, "own_tera_availability_available"), 1.0)
        self.assertEqual(_value(available, "own_tera_action_available"), 1.0)
        self.assertEqual(_value(unavailable, "own_tera_availability_unavailable"), 1.0)
        self.assertFalse(np.allclose(available, unavailable))

        fire = _features(log=[*BASE_LOG, "|-terastallize|p1a: Charizard|Fire"])
        water = _features(log=[*BASE_LOG, "|-terastallize|p1a: Charizard|Water"])
        self.assertEqual(_value(fire, "own_active_tera_state_active"), 1.0)
        self.assertEqual(_value(fire, "own_active_tera_type_fire"), 1.0)
        self.assertEqual(_value(water, "own_active_tera_type_water"), 1.0)
        self.assertEqual(_value(fire, "own_current_type_is_tera"), 1.0)
        self.assertFalse(np.allclose(fire, water))

    def test_opponent_revealed_tera_and_base_current_type_split(self):
        neutral = _features()
        tera = _features(log=[*BASE_LOG, "|-terastallize|p2a: Blastoise|Fire"])
        self.assertEqual(_value(tera, "opponent_active_tera_state_active"), 1.0)
        self.assertEqual(_value(tera, "opponent_active_tera_type_fire"), 1.0)
        self.assertEqual(_value(tera, "opponent_current_type_is_tera"), 1.0)
        self.assertFalse(np.allclose(neutral, tera))
        self.assertEqual(_value(tera, "opponent_active_base_type_water"), 1.0)
        self.assertEqual(_value(tera, "opponent_active_current_type_fire"), 1.0)

    def test_weather_terrain_and_rooms_are_explicit(self):
        neutral = _features()
        rain = _features(log=[*BASE_LOG, "|-weather|RainDance"])
        sun = _features(log=[*BASE_LOG, "|-weather|SunnyDay"])
        electric = _features(log=[*BASE_LOG, "|-fieldstart|move: Electric Terrain"])
        trick = _features(log=[*BASE_LOG, "|-fieldstart|move: Trick Room"])
        gravity = _features(log=[*BASE_LOG, "|-fieldstart|move: Gravity"])
        magic = _features(log=[*BASE_LOG, "|-fieldstart|move: Magic Room"])
        wonder = _features(log=[*BASE_LOG, "|-fieldstart|move: Wonder Room"])
        self.assertEqual(_value(neutral, "weather_state_none"), 1.0)
        self.assertEqual(_value(rain, "weather_state_rain"), 1.0)
        self.assertEqual(_value(sun, "weather_state_sun"), 1.0)
        self.assertEqual(_value(electric, "terrain_state_electric"), 1.0)
        self.assertEqual(_value(trick, "trickroom_state_active"), 1.0)
        self.assertEqual(_value(gravity, "gravity_state_active"), 1.0)
        self.assertEqual(_value(magic, "magicroom_state_active"), 1.0)
        self.assertEqual(_value(wonder, "wonderroom_state_active"), 1.0)
        self.assertFalse(np.allclose(rain, sun))

    def test_tera_state_restores_from_public_switch_details(self):
        restored = _features(
            log=[
                *BASE_LOG,
                "|-terastallize|p1a: Charizard|Fire",
                "|switch|p1a: Pikachu|Pikachu, L80|100/100",
                "|switch|p1a: Charizard|Charizard, L80, M, tera:Fire|100/100",
            ]
        )
        self.assertEqual(_value(restored, "own_active_tera_state_active"), 1.0)
        self.assertEqual(_value(restored, "own_active_tera_type_fire"), 1.0)
        self.assertEqual(_value(restored, "own_tera_availability_used"), 1.0)

    def test_screens_tailwind_and_hazards_flip_with_perspective(self):
        log = [
            *BASE_LOG,
            "|-sidestart|p1: Player|move: Reflect",
            "|-sidestart|p1: Player|move: Light Screen",
            "|-sidestart|p1: Player|move: Tailwind",
            "|-sidestart|p1: Player|move: Stealth Rock",
        ]
        p1 = _features(log=log, player="p1")
        p2 = _features(log=log, player="p2")
        for condition in ("reflect", "lightscreen", "tailwind"):
            self.assertEqual(_value(p1, f"own_{condition}_state_active"), 1.0)
            self.assertEqual(_value(p2, f"opponent_{condition}_state_active"), 1.0)
        self.assertEqual(_value(p1, "own_stealthrock_state_active"), 1.0)
        self.assertEqual(_value(p2, "opponent_stealthrock_state_active"), 1.0)

        safeguard = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Safeguard"])
        mist = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Mist"])
        self.assertEqual(_value(safeguard, "own_safeguard_state_active"), 1.0)
        self.assertEqual(_value(mist, "own_mist_state_active"), 1.0)

    def test_hazard_layers_and_sticky_web_are_distinct(self):
        one_spike = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Spikes"])
        two_spikes = _features(
            log=[
                *BASE_LOG,
                "|-sidestart|p1: Player|move: Spikes",
                "|-sidestart|p1: Player|move: Spikes",
            ]
        )
        one_toxic = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Toxic Spikes"])
        two_toxic = _features(
            log=[
                *BASE_LOG,
                "|-sidestart|p1: Player|move: Toxic Spikes",
                "|-sidestart|p1: Player|move: Toxic Spikes",
            ]
        )
        sticky = _features(log=[*BASE_LOG, "|-sidestart|p1: Player|move: Sticky Web"])
        self.assertEqual(_value(one_spike, "own_spikes_layers_1"), 1.0)
        self.assertEqual(_value(two_spikes, "own_spikes_layers_2"), 1.0)
        self.assertEqual(_value(one_toxic, "own_toxicspikes_layers_1"), 1.0)
        self.assertEqual(_value(two_toxic, "own_toxicspikes_layers_2"), 1.0)
        self.assertEqual(_value(sticky, "own_stickyweb_state_active"), 1.0)
        self.assertFalse(np.allclose(one_spike, two_spikes))
        self.assertFalse(np.allclose(one_toxic, two_toxic))

    def test_counterfactual_report_contains_all_required_distinctions(self):
        report = evaluate_tera_field_counterfactuals()
        self.assertEqual(report["feature_version"], FEATURE_VERSION_V6)
        self.assertEqual(report["feature_dim"], FEATURE_DIM_V6)
        for changed in report["comparisons"].values():
            self.assertTrue(changed)


if __name__ == "__main__":
    unittest.main()
