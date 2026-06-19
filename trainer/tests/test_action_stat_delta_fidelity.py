"""Exact per-stat stage-delta fidelity for action features.

It is not enough that a self-lowering move sets ``self_has_stat_drop = 1``; the
exact per-stat magnitude and sign must survive into the feature vector. The
normalization is documented and asserted: ``normalized_delta = raw_stage_delta / 2``
(clipped to [-1, 1]), so a two-stage drop -> -1.0 and a one-stage drop -> -0.5 are
distinct.
"""

import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM,
    ACTION_FEATURE_NAMES_V4,
    ACTION_STATS,
    build_action_feature_vector,
    build_action_feature_vector_v4,
)
from neural.action_side_effects import move_stat_deltas

NORMALIZER = 2.0  # normalized_delta = raw_stage_delta / 2, clipped to [-1, 1]


def _move(name):
    return {"kind": "move", "label": f"move: {name}", "move": name}


def _v4(name):
    return build_action_feature_vector_v4(_move(name), {"team": []}, {})


def _self_delta(vec, stat):
    return float(vec[ACTION_FEATURE_NAMES_V4.index(f"self_stat_delta_{stat}")])


def _nonzero_self_stats(vec):
    return {stat: _self_delta(vec, stat) for stat in ACTION_STATS if _self_delta(vec, stat)}


class ActionStatDeltaFidelityTest(unittest.TestCase):
    def test_raw_parser_exact_per_stat_deltas(self):
        # Raw moves.ts-parsed self deltas must match exactly, stat-for-stat.
        self.assertEqual(move_stat_deltas("Draco Meteor")["self"], {"spa": -2})
        self.assertEqual(move_stat_deltas("Overheat")["self"], {"spa": -2})
        self.assertEqual(move_stat_deltas("Leaf Storm")["self"], {"spa": -2})
        self.assertEqual(move_stat_deltas("Close Combat")["self"], {"def": -1, "spd": -1})
        self.assertEqual(move_stat_deltas("Superpower")["self"], {"atk": -1, "def": -1})
        self.assertEqual(move_stat_deltas("Bulk Up")["self"], {"atk": 1, "def": 1})
        # Curse: static parsing resolves the non-Ghost case (the only case with a
        # stat change). Ghost Curse instead sacrifices HP and has no stat delta;
        # the user's typing is not statically knowable, so the parser returns the
        # non-Ghost {+Atk, +Def, -Spe}. Documented conditional behavior.
        self.assertEqual(move_stat_deltas("Curse")["self"], {"atk": 1, "def": 1, "spe": -1})

    def test_draco_meteor_full_proof(self):
        raw = move_stat_deltas("Draco Meteor")["self"]
        draco = _v4("Draco Meteor")

        # (1) parser returns exactly {"spa": -2}
        self.assertEqual(raw, {"spa": -2})

        # (2) the vector writes the Special Attack delta field ...
        self.assertNotEqual(_self_delta(draco, "spa"), 0.0)
        # ... and (5) no other self stat-delta field is nonzero.
        self.assertEqual(set(_nonzero_self_stats(draco)), {"spa"})

        # (3) the value corresponds to TWO stages, not one.
        self.assertEqual(_self_delta(draco, "spa"), raw["spa"] / NORMALIZER)  # -2/2
        self.assertEqual(_self_delta(draco, "spa"), -1.0)
        self.assertNotEqual(_self_delta(draco, "spa"), -0.5)  # a single stage would be -0.5

        # (4) self_has_stat_drop = 1
        self.assertEqual(float(draco[ACTION_FEATURE_NAMES_V4.index("self_has_stat_drop")]), 1.0)

        # no spurious opponent delta either
        for stat in ACTION_STATS:
            self.assertEqual(
                float(draco[ACTION_FEATURE_NAMES_V4.index(f"opponent_stat_delta_{stat}")]), 0.0
            )

    def test_two_stage_vs_one_stage_are_distinct(self):
        # Draco's -2 -> -1.0; Curse's -1 Speed -> -0.5. The magnitudes differ, so
        # one- and two-stage drops are not aliased.
        draco = _v4("Draco Meteor")
        curse = _v4("Curse")
        self.assertEqual(_self_delta(draco, "spa"), -1.0)
        self.assertEqual(_self_delta(curse, "spe"), -0.5)

    def test_close_combat_and_superpower_write_exact_fields(self):
        cc = _v4("Close Combat")
        self.assertEqual(_nonzero_self_stats(cc), {"def": -0.5, "spd": -0.5})
        sp = _v4("Superpower")
        self.assertEqual(_nonzero_self_stats(sp), {"atk": -0.5, "def": -0.5})

    def test_curse_vs_bulk_up_preserve_each_stat(self):
        curse = _v4("Curse")
        bulk = _v4("Bulk Up")
        self.assertEqual(_nonzero_self_stats(curse), {"atk": 0.5, "def": 0.5, "spe": -0.5})
        self.assertEqual(_nonzero_self_stats(bulk), {"atk": 0.5, "def": 0.5})

    def test_v3_unchanged_and_v4_preserves_it_as_prefix(self):
        # legal-action-v3 has no self stat-delta field at all; it is the exact,
        # byte-identical prefix of legal-action-v4. Any future legal-action-v5 that
        # extends v4 therefore preserves this exact information by construction.
        self.assertNotIn("self_stat_delta_spa", ACTION_FEATURE_NAMES_V4[:ACTION_FEATURE_DIM])
        v3 = build_action_feature_vector(_move("Draco Meteor"), {"team": []}, {})
        v4 = _v4("Draco Meteor")
        self.assertTrue(np.allclose(v4[:ACTION_FEATURE_DIM], v3))


if __name__ == "__main__":
    unittest.main()
