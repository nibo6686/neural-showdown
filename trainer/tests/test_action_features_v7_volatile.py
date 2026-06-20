"""legal-action-v7 batch 2: typed volatile effect features.

Asserts the batch-1 prefix is preserved (first 361 names + values), volatile
fields carry oracle-derived chances (flinch as probability, guaranteed volatiles
1.0), confusion stays in the batch-1 status slice, and ordinary moves/switches are
zero. Diagnostic only; live defaults untouched.
"""

import hashlib
import json
import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM_V7,
    ACTION_FEATURE_DIM_V7_BATCH1,
    ACTION_FEATURE_DIM_V7_BATCH2,
    ACTION_FEATURE_NAMES_V7,
    ACTION_FEATURE_NAMES_V7_BATCH1,
    ACTION_FEATURE_NAMES_V7_BATCH2,
    SLICE9_VOLATILE_FEATURE_NAMES,
    build_action_feature_vector_v7,
)

_PRIVATE = {"team": [{"species": "Annihilape", "level": 80, "types": ["Fighting", "Ghost"], "active": True}]}


def _fp(names):
    return hashlib.sha256(json.dumps(list(names), ensure_ascii=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _action(move, kind="move"):
    return {"kind": kind, "label": f"{kind}: {move}", "move": move}


def _v7(move, kind="move", attacker=None):
    priv = {"team": [{**(attacker or {"species": "Annihilape", "level": 80}), "active": True}]}
    return build_action_feature_vector_v7(_action(move, kind), priv, {}, None)


def _val(vec, name):
    return float(vec[ACTION_FEATURE_NAMES_V7.index(name)])


class Batch1PrefixIntegrityTest(unittest.TestCase):
    def test_full_v7_dim_and_fingerprint(self):
        self.assertGreater(ACTION_FEATURE_DIM_V7, 375)
        self.assertEqual(len(SLICE9_VOLATILE_FEATURE_NAMES), 14)
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH2, 375)
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:ACTION_FEATURE_DIM_V7_BATCH2], ACTION_FEATURE_NAMES_V7_BATCH2)
        self.assertEqual(
            _fp(ACTION_FEATURE_NAMES_V7[:ACTION_FEATURE_DIM_V7_BATCH2]),
            "7f102fd8abc51bc6c776a1447bf27a15ec71352e3d6a9f9ba901d7f7eecc0252",
        )

    def test_first_361_names_match_batch1(self):
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:ACTION_FEATURE_DIM_V7_BATCH1], ACTION_FEATURE_NAMES_V7_BATCH1)
        self.assertEqual(
            _fp(ACTION_FEATURE_NAMES_V7[:ACTION_FEATURE_DIM_V7_BATCH1]),
            "85225a44776b6fc6e44b9900432acb253bacf3339a276d60febbd70eac4fd77f",
        )

    def test_first_361_values_match_batch1_prefix(self):
        # The volatile slice must not perturb any batch-1 (or v6) value.
        from neural.action_features import build_action_feature_vector_v6, slice8_typed_status_stat_feature_vector
        for move, kind in [("Iron Head", "move"), ("Will-O-Wisp", "move"), ("Substitute", "move"), ("Latias", "switch")]:
            action = _action(move, kind)
            v7 = build_action_feature_vector_v7(action, _PRIVATE, {}, None)
            v6 = build_action_feature_vector_v6(action, _PRIVATE, {}, None)
            slice8 = slice8_typed_status_stat_feature_vector(action)
            batch1 = np.concatenate([v6, slice8])
            np.testing.assert_array_equal(v7[:ACTION_FEATURE_DIM_V7_BATCH1], batch1)


class VolatileFieldTest(unittest.TestCase):
    def test_ordinary_move_has_zero_volatile_fields(self):
        for move in ("Surf", "Earthquake", "Close Combat"):
            vec = _v7(move, attacker={"species": "Blastoise", "level": 80})
            for name in SLICE9_VOLATILE_FEATURE_NAMES:
                self.assertEqual(_val(vec, name), 0.0, f"{move}:{name}")

    def test_switch_has_zero_volatile_fields(self):
        vec = _v7("Latias", "switch")
        for name in SLICE9_VOLATILE_FEATURE_NAMES:
            self.assertEqual(_val(vec, name), 0.0, name)

    def test_guaranteed_flinch_fake_out(self):
        self.assertEqual(_val(_v7("Fake Out"), "effect_target_flinch_chance"), 1.0)

    def test_secondary_flinch_is_probability(self):
        for move in ("Air Slash", "Iron Head"):
            flinch = _val(_v7(move), "effect_target_flinch_chance")
            self.assertAlmostEqual(flinch, 0.30, places=4)
            self.assertNotEqual(flinch, 1.0)

    def test_confusion_modeled_in_batch1_status_slice(self):
        # Confusion stays in the batch-1 status slice (not duplicated as a volatile).
        self.assertEqual(_val(_v7("Confuse Ray"), "effect_target_status_confusion_chance"), 1.0)
        self.assertAlmostEqual(_val(_v7("Hurricane"), "effect_target_status_confusion_chance"), 0.30, places=4)

    def test_leech_seed_and_yawn(self):
        self.assertEqual(_val(_v7("Leech Seed"), "effect_target_leech_seed"), 1.0)
        self.assertEqual(_val(_v7("Yawn"), "effect_target_yawn"), 1.0)

    def test_taunt_encore_disable(self):
        self.assertEqual(_val(_v7("Taunt"), "effect_target_taunt"), 1.0)
        self.assertEqual(_val(_v7("Encore"), "effect_target_encore"), 1.0)
        self.assertEqual(_val(_v7("Disable"), "effect_target_disable"), 1.0)

    def test_trap_and_heal_block(self):
        self.assertEqual(_val(_v7("Magma Storm"), "effect_target_trap_chance"), 1.0)
        self.assertEqual(_val(_v7("Psychic Noise"), "effect_target_heal_block"), 1.0)

    def test_self_substitute(self):
        self.assertEqual(_val(_v7("Substitute"), "effect_self_substitute"), 1.0)
        self.assertEqual(_val(_v7("Shed Tail"), "effect_self_substitute"), 1.0)

    def test_self_protect(self):
        self.assertEqual(_val(_v7("Protect"), "effect_self_protect"), 1.0)

    def test_self_destiny_bond_and_magnet_rise(self):
        self.assertEqual(_val(_v7("Destiny Bond"), "effect_self_destiny_bond"), 1.0)
        self.assertEqual(_val(_v7("Magnet Rise"), "effect_self_magnet_rise"), 1.0)

    def test_volatile_other_catch_all(self):
        self.assertEqual(_val(_v7("Salt Cure"), "effect_target_volatile_other"), 1.0)
        self.assertEqual(_val(_v7("No Retreat"), "effect_self_volatile_other"), 1.0)


if __name__ == "__main__":
    unittest.main()
