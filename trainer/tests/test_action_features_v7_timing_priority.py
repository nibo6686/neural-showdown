"""legal-action-v7 batch 4: typed priority and timing effects."""

import hashlib
import json
import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM_V7,
    ACTION_FEATURE_DIM_V7_BATCH3,
    ACTION_FEATURE_DIM_V7_BATCH4,
    ACTION_FEATURE_NAMES_V7,
    ACTION_FEATURE_NAMES_V7_BATCH3,
    ACTION_FEATURE_NAMES_V7_BATCH4,
    SLICE11_TIMING_PRIORITY_FEATURE_NAMES,
    build_action_feature_vector_v6,
    build_action_feature_vector_v7,
    slice10_typed_item_effect_feature_vector,
    slice8_typed_status_stat_feature_vector,
    slice9_typed_volatile_feature_vector,
)

_BATCH3_FP = "d3f342710b001eded43f1ccee8228ce42d1fe616fb6f043593a3e8c3893cc91d"
_FULL_FP = "bdf2439df649fcc0f1433482c8dc7a1ad7389b40be73c39884c27b45b81fb935"


def _fp(names):
    payload = json.dumps(list(names), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _action(move, kind="move"):
    return {"kind": kind, "label": f"{kind}: {move}", "move": move}


def _private(item=None, *, ability="Defiant", hp=1.0, types=None):
    return {
        "team": [
            {
                "species": "Annihilape",
                "level": 80,
                "types": types or ["Fighting", "Ghost"],
                "ability": ability,
                "hp_fraction": hp,
                "active": True,
                "item": item,
            }
        ]
    }


def _tactical(*, weather=None, terrain=None, own=None, opponent=None):
    return {
        "weather": weather,
        "terrain": terrain,
        "own": own or {},
        "opponent": opponent or {},
    }


def _v7(move, *, private=None, tactical=None, kind="move"):
    return build_action_feature_vector_v7(
        _action(move, kind),
        private if private is not None else _private(),
        tactical if tactical is not None else _tactical(),
        None,
    )


def _val(vec, name):
    return float(vec[ACTION_FEATURE_NAMES_V7.index(name)])


class Batch3PrefixIntegrityTest(unittest.TestCase):
    def test_schema_and_fingerprint(self):
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH3, 388)
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH4, 406)
        self.assertEqual(len(SLICE11_TIMING_PRIORITY_FEATURE_NAMES), 18)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7_BATCH3), _BATCH3_FP)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7_BATCH4), _FULL_FP)
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:ACTION_FEATURE_DIM_V7_BATCH4], ACTION_FEATURE_NAMES_V7_BATCH4)

    def test_first_388_names_and_values_match_batch3(self):
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:388], ACTION_FEATURE_NAMES_V7_BATCH3)
        fixtures = (
            ("Grassy Glide", _private(), _tactical(terrain="grassyterrain"), "move"),
            ("Solar Beam", _private("Power Herb"), _tactical(), "move"),
            ("Future Sight", _private(), _tactical(), "move"),
            ("Latias", _private(), _tactical(), "switch"),
        )
        for move, private, tactical, kind in fixtures:
            action = _action(move, kind)
            current = build_action_feature_vector_v7(action, private, tactical, None)
            batch3 = np.concatenate(
                [
                    build_action_feature_vector_v6(action, private, tactical, None),
                    slice8_typed_status_stat_feature_vector(action),
                    slice9_typed_volatile_feature_vector(action),
                    slice10_typed_item_effect_feature_vector(action, private, tactical),
                ]
            ).astype(np.float32)
            np.testing.assert_array_equal(current[:388], batch3, err_msg=move)


class TimingPriorityFieldTest(unittest.TestCase):
    def test_ordinary_move_has_no_special_timing_flags(self):
        vec = _v7("Surf")
        special = [
            name
            for name in SLICE11_TIMING_PRIORITY_FEATURE_NAMES
            if name not in {"effect_base_priority_norm", "effect_effective_priority_norm"}
        ]
        for name in special:
            self.assertEqual(_val(vec, name), 0.0, name)

    def test_static_priority_is_typed(self):
        vec = _v7("Quick Attack")
        self.assertAlmostEqual(_val(vec, "effect_base_priority_norm"), 1.0 / 7.0, places=5)
        self.assertAlmostEqual(_val(vec, "effect_effective_priority_norm"), 1.0 / 7.0, places=5)

    def test_grassy_glide_priority_in_and_out_of_terrain(self):
        grassy = _v7("Grassy Glide", tactical=_tactical(terrain="grassyterrain"))
        clear = _v7("Grassy Glide", tactical=_tactical())
        self.assertAlmostEqual(_val(grassy, "effect_effective_priority_norm"), 1.0 / 7.0, places=5)
        self.assertEqual(_val(grassy, "effect_priority_boosted_by_terrain"), 1.0)
        self.assertEqual(_val(grassy, "effect_priority_condition_known"), 1.0)
        self.assertEqual(_val(clear, "effect_effective_priority_norm"), 0.0)
        self.assertEqual(_val(clear, "effect_priority_boosted_by_terrain"), 0.0)
        self.assertEqual(_val(clear, "effect_priority_condition_known"), 1.0)

    def test_solar_beam_normal_charges_without_attacking(self):
        vec = _v7("Solar Beam")
        self.assertEqual(_val(vec, "effect_requires_charge_turn"), 1.0)
        self.assertEqual(_val(vec, "effect_charges_this_turn"), 1.0)
        self.assertEqual(_val(vec, "effect_attacks_this_turn"), 0.0)
        self.assertEqual(_val(vec, "effect_charge_skipped_by_weather"), 0.0)

    def test_solar_beam_sun_skips_charge_and_attacks(self):
        vec = _v7("Solar Beam", tactical=_tactical(weather="SunnyDay"))
        self.assertEqual(_val(vec, "effect_requires_charge_turn"), 1.0)
        self.assertEqual(_val(vec, "effect_charges_this_turn"), 0.0)
        self.assertEqual(_val(vec, "effect_attacks_this_turn"), 1.0)
        self.assertEqual(_val(vec, "effect_charge_skipped_by_weather"), 1.0)

    def test_meteor_beam_power_herb_skips_charge(self):
        vec = _v7("Meteor Beam", private=_private("Power Herb"))
        self.assertEqual(_val(vec, "effect_charges_this_turn"), 0.0)
        self.assertEqual(_val(vec, "effect_attacks_this_turn"), 1.0)
        self.assertEqual(_val(vec, "effect_charge_skipped_by_item"), 1.0)
        self.assertEqual(_val(vec, "effect_user_item_consumed"), 1.0)

    def test_future_sight_is_delayed_not_immediate(self):
        vec = _v7("Future Sight")
        self.assertEqual(_val(vec, "effect_delayed_future_damage"), 1.0)
        self.assertAlmostEqual(_val(vec, "effect_delayed_damage_turns_norm"), 2.0 / 3.0, places=5)
        self.assertEqual(_val(vec, "effect_attacks_this_turn"), 0.0)
        self.assertEqual(_val(vec, "effect_charges_this_turn"), 0.0)

    def test_recharge_and_locked_move(self):
        self.assertEqual(_val(_v7("Hyper Beam"), "effect_user_must_recharge_next_turn"), 1.0)
        self.assertEqual(_val(_v7("Outrage"), "effect_user_locked_into_move"), 1.0)

    def test_psychic_terrain_priority_block_when_target_grounded(self):
        vec = _v7(
            "Quick Attack",
            tactical=_tactical(
                terrain="psychicterrain",
                opponent={"active_current_types": ["Psychic"]},
            ),
        )
        self.assertEqual(_val(vec, "effect_priority_blocked"), 1.0)
        self.assertEqual(_val(vec, "effect_priority_condition_known"), 1.0)

    def test_unknown_grounding_is_conditional_not_invented(self):
        vec = _v7(
            "Grassy Glide",
            private={"team": []},
            tactical=_tactical(terrain="grassyterrain"),
        )
        self.assertEqual(_val(vec, "effect_priority_boosted_by_terrain"), 0.0)
        self.assertEqual(_val(vec, "effect_priority_condition_known"), 0.0)
        self.assertEqual(_val(vec, "effect_priority_conditional"), 1.0)


if __name__ == "__main__":
    unittest.main()
