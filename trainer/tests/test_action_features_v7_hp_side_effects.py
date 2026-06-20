"""legal-action-v7 batch 5: typed HP side effects."""

import hashlib
import json
import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM_V7,
    ACTION_FEATURE_DIM_V7_BATCH4,
    ACTION_FEATURE_DIM_V7_BATCH5,
    ACTION_FEATURE_NAMES_V7,
    ACTION_FEATURE_NAMES_V7_BATCH4,
    ACTION_FEATURE_NAMES_V7_BATCH5,
    SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES,
    build_action_feature_vector_v6,
    build_action_feature_vector_v7,
    slice10_typed_item_effect_feature_vector,
    slice11_typed_timing_priority_feature_vector,
    slice8_typed_status_stat_feature_vector,
    slice9_typed_volatile_feature_vector,
)

_BATCH4_FP = "bdf2439df649fcc0f1433482c8dc7a1ad7389b40be73c39884c27b45b81fb935"
_FULL_FP = "05f27e8d093bcafb4d9f2f09aa2a75a003bbf985861076aec035a7f90a2fc856"


def _fp(names):
    payload = json.dumps(list(names), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _action(move, kind="move"):
    return {"kind": kind, "label": f"{kind}: {move}", "move": move}


def _private(*, hp=1.0, ability="Synchronize"):
    return {
        "team": [
            {
                "species": "Mew",
                "level": 80,
                "types": ["Psychic"],
                "ability": ability,
                "hp_fraction": hp,
                "active": True,
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


def _v7(move, *, hp=1.0, ability="Synchronize", tactical=None, kind="move"):
    return build_action_feature_vector_v7(
        _action(move, kind),
        _private(hp=hp, ability=ability),
        tactical if tactical is not None else _tactical(),
        None,
    )


def _val(vec, name):
    return float(vec[ACTION_FEATURE_NAMES_V7.index(name)])


class Batch4PrefixIntegrityTest(unittest.TestCase):
    def test_schema_and_fingerprint(self):
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH4, 406)
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH5, 420)
        self.assertEqual(len(SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES), 14)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7_BATCH4), _BATCH4_FP)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7_BATCH5), _FULL_FP)
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:ACTION_FEATURE_DIM_V7_BATCH5], ACTION_FEATURE_NAMES_V7_BATCH5)

    def test_first_406_names_and_values_match_batch4(self):
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:406], ACTION_FEATURE_NAMES_V7_BATCH4)
        fixtures = (
            ("Flare Blitz", _private(), _tactical(), "move"),
            ("Recover", _private(hp=0.5), _tactical(), "move"),
            ("Substitute", _private(hp=1.0), _tactical(), "move"),
            ("Latias", _private(), _tactical(), "switch"),
        )
        for move, private, tactical, kind in fixtures:
            action = _action(move, kind)
            current = build_action_feature_vector_v7(action, private, tactical, None)
            batch4 = np.concatenate(
                [
                    build_action_feature_vector_v6(action, private, tactical, None),
                    slice8_typed_status_stat_feature_vector(action),
                    slice9_typed_volatile_feature_vector(action),
                    slice10_typed_item_effect_feature_vector(action, private, tactical),
                    slice11_typed_timing_priority_feature_vector(action, private, tactical),
                ]
            ).astype(np.float32)
            np.testing.assert_array_equal(current[:406], batch4, err_msg=move)


class HPSideEffectFieldTest(unittest.TestCase):
    def test_ordinary_move_and_switch_are_zero(self):
        for move, kind in (("Surf", "move"), ("Earthquake", "move"), ("Latias", "switch")):
            vec = _v7(move, kind=kind)
            for name in SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES:
                self.assertEqual(_val(vec, name), 0.0, f"{move}:{name}")

    def test_standard_and_high_recoil_fractions(self):
        for move in ("Flare Blitz", "Brave Bird", "Wood Hammer"):
            self.assertAlmostEqual(_val(_v7(move), "effect_recoil_damage_fraction"), 0.33, places=5, msg=move)
        self.assertEqual(_val(_v7("Head Smash"), "effect_recoil_damage_fraction"), 0.5)

    def test_drain_fractions(self):
        for move in ("Drain Punch", "Giga Drain", "Bitter Blade"):
            self.assertEqual(_val(_v7(move), "effect_drain_damage_fraction"), 0.5, move)

    def test_direct_and_weather_healing(self):
        for move in ("Recover", "Roost", "Slack Off"):
            self.assertEqual(_val(_v7(move), "effect_user_heal_max_hp_fraction"), 0.5, move)
        self.assertEqual(
            _val(_v7("Moonlight", tactical=_tactical(weather="SunnyDay")), "effect_user_heal_max_hp_fraction"),
            np.float32(0.667),
        )
        self.assertEqual(
            _val(_v7("Moonlight", tactical=_tactical(weather="RainDance")), "effect_user_heal_max_hp_fraction"),
            0.25,
        )

    def test_strength_sap_amount_is_honestly_unknown(self):
        vec = _v7("Strength Sap")
        self.assertEqual(_val(vec, "effect_user_heal_max_hp_fraction"), 0.0)
        self.assertEqual(_val(vec, "effect_hp_effect_conditional"), 1.0)
        self.assertEqual(_val(vec, "effect_hp_effect_amount_unknown"), 1.0)

    def test_hp_cost_and_insufficient_hp(self):
        substitute = _v7("Substitute", hp=1.0)
        blocked_sub = _v7("Substitute", hp=0.25)
        belly = _v7("Belly Drum", hp=1.0)
        self.assertEqual(_val(substitute, "effect_hp_cost_max_hp_fraction"), 0.25)
        self.assertEqual(_val(blocked_sub, "effect_hp_cost_blocked"), 1.0)
        self.assertEqual(_val(belly, "effect_hp_cost_max_hp_fraction"), 0.5)

    def test_fixed_self_damage(self):
        for move in ("Steel Beam", "Mind Blown", "Chloroblast"):
            self.assertEqual(_val(_v7(move), "effect_self_damage_max_hp_fraction"), 0.5, move)

    def test_crash_damage_is_separate_and_conditional(self):
        vec = _v7("High Jump Kick")
        self.assertEqual(_val(vec, "effect_crash_damage_max_hp_fraction"), 0.5)
        self.assertEqual(_val(vec, "effect_self_damage_max_hp_fraction"), 0.0)
        self.assertEqual(_val(vec, "effect_hp_effect_conditional"), 1.0)

    def test_heal_block_is_detected(self):
        vec = _v7(
            "Recover",
            tactical=_tactical(own={"constraint_volatiles": ["healblock"]}),
        )
        self.assertEqual(_val(vec, "effect_healing_blocked"), 1.0)

    def test_target_healing(self):
        normal = _v7("Heal Pulse", ability="Synchronize")
        boosted = _v7("Heal Pulse", ability="Mega Launcher")
        self.assertEqual(_val(normal, "effect_target_heal_max_hp_fraction"), 0.5)
        self.assertEqual(_val(boosted, "effect_target_heal_max_hp_fraction"), 0.75)


if __name__ == "__main__":
    unittest.main()
