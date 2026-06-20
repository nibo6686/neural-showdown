"""legal-action-v7 batch 3: typed item-effect features."""

import hashlib
import json
import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM_V7,
    ACTION_FEATURE_DIM_V7_BATCH2,
    ACTION_FEATURE_DIM_V7_BATCH3,
    ACTION_FEATURE_NAMES_V7,
    ACTION_FEATURE_NAMES_V7_BATCH2,
    ACTION_FEATURE_NAMES_V7_BATCH3,
    SLICE10_ITEM_EFFECT_FEATURE_NAMES,
    build_action_feature_vector_v6,
    build_action_feature_vector_v7,
    slice8_typed_status_stat_feature_vector,
    slice9_typed_volatile_feature_vector,
)

_BATCH2_FP = "7f102fd8abc51bc6c776a1447bf27a15ec71352e3d6a9f9ba901d7f7eecc0252"


def _fp(names):
    payload = json.dumps(list(names), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _action(move, kind="move"):
    return {"kind": kind, "label": f"{kind}: {move}", "move": move}


def _private(item=None):
    return {
        "team": [
            {
                "species": "Annihilape",
                "level": 80,
                "types": ["Fighting", "Ghost"],
                "active": True,
                "item": item,
            }
        ]
    }


def _tactical(target_state="unknown", target_item=None):
    return {
        "own": {"active_item_state": "unknown", "active_item": None},
        "opponent": {
            "active_item_state": target_state,
            "active_item": target_item,
            "active_item_source": "protocol" if target_state != "unknown" else "unknown",
        },
    }


def _v7(move, *, target_state="unknown", target_item=None, user_item=None, kind="move"):
    return build_action_feature_vector_v7(
        _action(move, kind),
        _private(user_item),
        _tactical(target_state, target_item),
        None,
    )


def _val(vec, name):
    return float(vec[ACTION_FEATURE_NAMES_V7.index(name)])


class Batch2PrefixIntegrityTest(unittest.TestCase):
    def test_schema_and_full_fingerprint(self):
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH2, 375)
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH3, 388)
        self.assertEqual(len(SLICE10_ITEM_EFFECT_FEATURE_NAMES), 13)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7_BATCH2), _BATCH2_FP)
        self.assertEqual(
            _fp(ACTION_FEATURE_NAMES_V7_BATCH3),
            "d3f342710b001eded43f1ccee8228ce42d1fe616fb6f043593a3e8c3893cc91d",
        )
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:ACTION_FEATURE_DIM_V7_BATCH3], ACTION_FEATURE_NAMES_V7_BATCH3)

    def test_first_375_names_and_values_match_batch2(self):
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:375], ACTION_FEATURE_NAMES_V7_BATCH2)
        for move, kind in (("Knock Off", "move"), ("Bug Bite", "move"), ("Trick", "move"), ("Latias", "switch")):
            action = _action(move, kind)
            private = _private("Choice Scarf")
            tactical = _tactical("held", "Leftovers")
            current = build_action_feature_vector_v7(action, private, tactical, None)
            batch2 = np.concatenate(
                [
                    build_action_feature_vector_v6(action, private, tactical, None),
                    slice8_typed_status_stat_feature_vector(action),
                    slice9_typed_volatile_feature_vector(action),
                ]
            ).astype(np.float32)
            np.testing.assert_array_equal(current[:375], batch2, err_msg=move)


class ItemEffectFieldTest(unittest.TestCase):
    def test_ordinary_move_and_switch_are_zero(self):
        for move, kind in (("Surf", "move"), ("Earthquake", "move"), ("Latias", "switch")):
            vec = _v7(move, kind=kind)
            for name in SLICE10_ITEM_EFFECT_FEATURE_NAMES:
                self.assertEqual(_val(vec, name), 0.0, f"{move}:{name}")

    def test_knock_off_known_item_separates_damage_boost_and_removal(self):
        vec = _v7("Knock Off", target_state="held", target_item="Leftovers")
        self.assertEqual(_val(vec, "effect_target_item_removal_chance"), 1.0)
        self.assertEqual(_val(vec, "effect_target_item_removal_state_known"), 1.0)
        self.assertEqual(_val(vec, "effect_knock_off_damage_boost_applied"), 1.0)
        self.assertEqual(_val(vec, "effect_target_item_known"), 1.0)
        self.assertEqual(_val(vec, "effect_target_item_present"), 1.0)

    def test_knock_off_confirmed_absent_does_not_claim_removal_or_boost(self):
        vec = _v7("Knock Off", target_state="none")
        self.assertEqual(_val(vec, "effect_target_item_removal_chance"), 0.0)
        self.assertEqual(_val(vec, "effect_target_item_removal_state_known"), 1.0)
        self.assertEqual(_val(vec, "effect_knock_off_damage_boost_applied"), 0.0)
        self.assertEqual(_val(vec, "effect_target_item_known"), 1.0)
        self.assertEqual(_val(vec, "effect_target_item_unknown"), 0.0)

    def test_knock_off_unknown_is_honest(self):
        vec = _v7("Knock Off")
        self.assertEqual(_val(vec, "effect_target_item_removal_chance"), 0.0)
        self.assertEqual(_val(vec, "effect_target_item_removal_state_unknown"), 1.0)
        self.assertEqual(_val(vec, "effect_knock_off_damage_boost_applied"), 0.0)
        self.assertEqual(_val(vec, "effect_target_item_unknown"), 1.0)

    def test_bug_bite_and_pluck_only_eat_known_berry(self):
        for move in ("Bug Bite", "Pluck"):
            berry = _v7(move, target_state="held", target_item="Sitrus Berry")
            nonberry = _v7(move, target_state="held", target_item="Leftovers")
            unknown = _v7(move)
            self.assertEqual(_val(berry, "effect_target_berry_eaten_or_stolen"), 1.0, move)
            self.assertEqual(_val(nonberry, "effect_target_berry_eaten_or_stolen"), 0.0, move)
            self.assertEqual(_val(unknown, "effect_target_berry_eaten_or_stolen"), 0.0, move)

    def test_trick_and_switcheroo_mark_swap(self):
        for move in ("Trick", "Switcheroo"):
            vec = _v7(move, target_state="held", target_item="Leftovers", user_item="Choice Scarf")
            self.assertEqual(_val(vec, "effect_items_swapped"), 1.0, move)

    def test_power_herb_charge_move_marks_user_consumption(self):
        for move in ("Solar Beam", "Meteor Beam"):
            self.assertEqual(_val(_v7(move, user_item="Power Herb"), "effect_user_item_consumed"), 1.0, move)
            self.assertEqual(_val(_v7(move, user_item="Leftovers"), "effect_user_item_consumed"), 0.0, move)

    def test_item_suppression_and_catch_all(self):
        self.assertEqual(_val(_v7("Embargo"), "effect_target_item_suppressed"), 1.0)
        self.assertEqual(_val(_v7("Magic Room"), "effect_all_items_suppressed"), 1.0)
        self.assertEqual(_val(_v7("Fling"), "effect_item_other"), 1.0)


if __name__ == "__main__":
    unittest.main()
