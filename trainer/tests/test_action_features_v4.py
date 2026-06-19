import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM,
    ACTION_FEATURE_DIM_V4,
    ACTION_FEATURE_NAMES,
    ACTION_FEATURE_NAMES_V4,
    ACTION_FEATURE_VERSION,
    ACTION_FEATURE_VERSION_V4,
    SLICE5_ACTION_FEATURE_NAMES,
    build_action_feature_vector,
    build_action_feature_vector_v4,
)
from neural.action_side_effects import move_stat_deltas


def _move(name, kind="move", **extra):
    action = {"kind": kind, "label": f"{kind}: {name}", "move": name}
    action.update(extra)
    return action


def _v4(name, kind="move", private=None, **extra):
    return build_action_feature_vector_v4(_move(name, kind, **extra), private or {"team": []}, {})


def _val(vec, name):
    return float(vec[ACTION_FEATURE_NAMES_V4.index(name)])


class LegalActionV4Test(unittest.TestCase):
    def test_v3_unchanged_and_v4_is_immutable_prefix_extension(self):
        self.assertEqual(ACTION_FEATURE_VERSION, "legal-action-v3")
        self.assertEqual(ACTION_FEATURE_VERSION_V4, "legal-action-v4")
        self.assertEqual(ACTION_FEATURE_DIM_V4, ACTION_FEATURE_DIM + len(SLICE5_ACTION_FEATURE_NAMES))
        self.assertEqual(ACTION_FEATURE_NAMES_V4[:ACTION_FEATURE_DIM], ACTION_FEATURE_NAMES)
        self.assertEqual(ACTION_FEATURE_NAMES_V4[ACTION_FEATURE_DIM:], SLICE5_ACTION_FEATURE_NAMES)
        self.assertEqual(len(set(ACTION_FEATURE_NAMES_V4)), len(ACTION_FEATURE_NAMES_V4))
        # v3 builder output is the exact prefix of v4.
        v3 = build_action_feature_vector(_move("Flamethrower"), {"team": []}, {})
        v4 = _v4("Flamethrower")
        self.assertTrue(np.allclose(v4[:ACTION_FEATURE_DIM], v3))

    def test_draco_meteor_self_spa_drop_is_represented(self):
        draco = _v4("Draco Meteor")
        psyshock = _v4("Psyshock")
        self.assertEqual(_val(draco, "self_stat_delta_spa"), -1.0)
        self.assertEqual(_val(psyshock, "self_stat_delta_spa"), 0.0)
        self.assertEqual(_val(draco, "self_has_stat_drop"), 1.0)
        self.assertFalse(np.allclose(draco, psyshock))
        # Parser-level proof too.
        self.assertEqual(move_stat_deltas("Draco Meteor")["self"].get("spa"), -2)

    def test_curse_and_bulk_up_differ_in_speed_but_share_atk_def(self):
        curse = _v4("Curse")
        bulk = _v4("Bulk Up")
        self.assertNotEqual(_val(curse, "self_stat_delta_spe"), _val(bulk, "self_stat_delta_spe"))
        self.assertEqual(_val(curse, "self_stat_delta_spe"), -0.5)
        self.assertEqual(_val(bulk, "self_stat_delta_spe"), 0.0)
        self.assertEqual(_val(curse, "self_stat_delta_atk"), _val(bulk, "self_stat_delta_atk"))
        self.assertEqual(_val(curse, "self_stat_delta_def"), _val(bulk, "self_stat_delta_def"))
        self.assertEqual(_val(curse, "self_stat_delta_atk"), 0.5)

    def test_command_identity_tera_and_switch(self):
        tera = _v4("Flamethrower", kind="move_tera", is_tera_action=True)
        normal = _v4("Flamethrower")
        self.assertEqual(_val(tera, "cmd_tera_move"), 1.0)
        self.assertEqual(_val(normal, "cmd_move"), 1.0)
        self.assertFalse(np.allclose(tera, normal))

        switch = _v4("Pikachu", kind="switch", index=9, private={"team": [{"species": "Pikachu", "active": False}]})
        move = _v4("Flamethrower")
        self.assertEqual(_val(switch, "cmd_switch"), 1.0)
        self.assertEqual(_val(switch, "switch_target_known"), 1.0)
        self.assertFalse(np.allclose(switch, move))

    def test_recoil_priority_and_status_classification(self):
        flare = _v4("Flare Blitz")
        punch = _v4("Fire Punch")
        self.assertEqual(_val(flare, "effect_recoil"), 1.0)
        self.assertEqual(_val(punch, "effect_recoil"), 0.0)

        extreme = _v4("Extreme Speed")
        tackle = _v4("Tackle")
        self.assertGreater(_val(extreme, "effect_priority_norm"), _val(tackle, "effect_priority_norm"))

        status = _v4("Will-O-Wisp")
        damage = _v4("Flamethrower")
        self.assertEqual(_val(status, "class_status"), 1.0)
        self.assertEqual(_val(damage, "class_damage"), 1.0)


if __name__ == "__main__":
    unittest.main()
