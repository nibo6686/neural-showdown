"""legal-action-v7 batch 6: typed field and side effects."""

import hashlib
import json
import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM_V7,
    ACTION_FEATURE_DIM_V7_BATCH5,
    ACTION_FEATURE_DIM_V7_BATCH6,
    ACTION_FEATURE_NAMES_V7,
    ACTION_FEATURE_NAMES_V7_BATCH5,
    ACTION_FEATURE_NAMES_V7_BATCH6,
    SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES,
    build_action_feature_vector_v6,
    build_action_feature_vector_v7,
    slice10_typed_item_effect_feature_vector,
    slice11_typed_timing_priority_feature_vector,
    slice12_typed_hp_side_effect_feature_vector,
    slice8_typed_status_stat_feature_vector,
    slice9_typed_volatile_feature_vector,
)

_BATCH5_FP = "05f27e8d093bcafb4d9f2f09aa2a75a003bbf985861076aec035a7f90a2fc856"
_BATCH6_FP = "e3e39124cd24e3e27684306e3d401859083df65965e721eb3e5e8b89c48fcb4c"


def _fp(names):
    payload = json.dumps(list(names), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _action(move, kind="move"):
    return {"kind": kind, "label": f"{kind}: {move}", "move": move}


def _private():
    return {"team": [{"species": "Mew", "level": 80, "types": ["Psychic"], "active": True}]}


def _tactical(*, weather=None):
    return {"weather": weather, "terrain": None, "own": {}, "opponent": {}}


def _v7(move, *, tactical=None, kind="move"):
    return build_action_feature_vector_v7(
        _action(move, kind),
        _private(),
        tactical if tactical is not None else _tactical(),
        None,
    )


def _val(vec, name):
    return float(vec[ACTION_FEATURE_NAMES_V7.index(name)])


class Batch5PrefixIntegrityTest(unittest.TestCase):
    def test_schema_and_fingerprint(self):
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH5, 420)
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH6, 452)
        self.assertEqual(ACTION_FEATURE_DIM_V7, 552)
        self.assertEqual(len(SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES), 32)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7_BATCH5), _BATCH5_FP)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7_BATCH6), _BATCH6_FP)
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:452], ACTION_FEATURE_NAMES_V7_BATCH6)

    def test_first_420_names_and_values_match_batch5(self):
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:420], ACTION_FEATURE_NAMES_V7_BATCH5)
        fixtures = (
            ("Stealth Rock", _tactical(), "move"),
            ("Defog", _tactical(), "move"),
            ("Brick Break", _tactical(), "move"),
            ("Sunny Day", _tactical(), "move"),
            ("Latias", _tactical(), "switch"),
        )
        private = _private()
        for move, tactical, kind in fixtures:
            action = _action(move, kind)
            current = build_action_feature_vector_v7(action, private, tactical, None)
            batch5 = np.concatenate(
                [
                    build_action_feature_vector_v6(action, private, tactical, None),
                    slice8_typed_status_stat_feature_vector(action),
                    slice9_typed_volatile_feature_vector(action),
                    slice10_typed_item_effect_feature_vector(action, private, tactical),
                    slice11_typed_timing_priority_feature_vector(action, private, tactical),
                    slice12_typed_hp_side_effect_feature_vector(action, private, tactical),
                ]
            ).astype(np.float32)
            np.testing.assert_array_equal(current[:420], batch5, err_msg=move)


class FieldSideEffectFieldTest(unittest.TestCase):
    def test_ordinary_move_and_switch_are_zero(self):
        for move, kind in (("Surf", "move"), ("Earthquake", "move"), ("Latias", "switch")):
            vec = _v7(move, kind=kind)
            for name in SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES:
                self.assertEqual(_val(vec, name), 0.0, f"{move}:{name}")

    def test_hazard_setup_is_typed(self):
        cases = {
            "Stealth Rock": "effect_target_side_stealth_rock_setup",
            "Spikes": "effect_target_side_spikes_setup",
            "Toxic Spikes": "effect_target_side_toxic_spikes_setup",
            "Sticky Web": "effect_target_side_sticky_web_setup",
        }
        for move, field in cases.items():
            self.assertEqual(_val(_v7(move), field), 1.0, move)

    def test_hazard_removal_side_is_typed(self):
        for move in ("Rapid Spin", "Mortal Spin"):
            vec = _v7(move)
            self.assertEqual(_val(vec, "effect_user_side_hazards_removed"), 1.0, move)
            self.assertEqual(_val(vec, "effect_target_side_hazards_removed"), 0.0, move)
        defog = _v7("Defog")
        self.assertEqual(_val(defog, "effect_user_side_hazards_removed"), 1.0)
        self.assertEqual(_val(defog, "effect_target_side_hazards_removed"), 1.0)
        self.assertEqual(_val(defog, "effect_terrain_removed"), 1.0)

    def test_screen_setup_and_removal_are_separate(self):
        setups = {
            "Reflect": "effect_user_side_reflect_setup",
            "Light Screen": "effect_user_side_light_screen_setup",
            "Aurora Veil": "effect_user_side_aurora_veil_setup",
        }
        for move, field in setups.items():
            self.assertEqual(_val(_v7(move, tactical=_tactical(weather="Snowscape")), field), 1.0, move)
        for move in ("Brick Break", "Psychic Fangs"):
            vec = _v7(move)
            self.assertEqual(_val(vec, "effect_target_side_screens_removed"), 1.0, move)
            self.assertEqual(_val(vec, "effect_user_side_reflect_setup"), 0.0, move)

    def test_aurora_veil_condition_is_honest(self):
        snow = _v7("Aurora Veil", tactical=_tactical(weather="Snowscape"))
        clear = _v7("Aurora Veil", tactical=_tactical())
        self.assertEqual(_val(snow, "effect_field_side_effect_blocked"), 0.0)
        self.assertEqual(_val(clear, "effect_field_side_effect_blocked"), 1.0)
        self.assertEqual(_val(clear, "effect_field_side_condition_known"), 1.0)
        self.assertEqual(_val(clear, "effect_field_side_effect_conditional"), 1.0)

    def test_weather_types(self):
        cases = {
            "Sunny Day": "effect_weather_sun_set",
            "Rain Dance": "effect_weather_rain_set",
            "Sandstorm": "effect_weather_sand_set",
            "Snowscape": "effect_weather_snow_set",
        }
        for move, field in cases.items():
            self.assertEqual(_val(_v7(move), field), 1.0, move)

    def test_terrain_types(self):
        cases = {
            "Grassy Terrain": "effect_terrain_grassy_set",
            "Electric Terrain": "effect_terrain_electric_set",
            "Psychic Terrain": "effect_terrain_psychic_set",
            "Misty Terrain": "effect_terrain_misty_set",
        }
        for move, field in cases.items():
            self.assertEqual(_val(_v7(move), field), 1.0, move)

    def test_room_and_global_field_types(self):
        cases = {
            "Trick Room": "effect_trick_room_set",
            "Magic Room": "effect_magic_room_set",
            "Wonder Room": "effect_wonder_room_set",
            "Gravity": "effect_gravity_set",
        }
        for move, field in cases.items():
            self.assertEqual(_val(_v7(move), field), 1.0, move)

    def test_other_user_side_conditions(self):
        cases = {
            "Tailwind": "effect_user_side_tailwind_setup",
            "Safeguard": "effect_user_side_safeguard_setup",
            "Mist": "effect_user_side_mist_setup",
            "Lucky Chant": "effect_user_side_lucky_chant_setup",
        }
        for move, field in cases.items():
            self.assertEqual(_val(_v7(move), field), 1.0, move)

    def test_court_change_is_swap_not_removal(self):
        vec = _v7("Court Change")
        self.assertEqual(_val(vec, "effect_side_conditions_swapped"), 1.0)
        self.assertEqual(_val(vec, "effect_user_side_hazards_removed"), 0.0)
        self.assertEqual(_val(vec, "effect_target_side_hazards_removed"), 0.0)


if __name__ == "__main__":
    unittest.main()
