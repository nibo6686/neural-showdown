"""legal-action-v7 batch 1: typed status + stat-delta effect features.

Asserts append-only integrity (byte-identical 331D v6 prefix + fingerprint),
v7 dim/name/fingerprint stability, the checkpoint guard rejecting v6<->v7 mixing,
and that typed status/stat fields carry oracle-derived probabilities and signed
stage deltas (not fake deterministic outcomes). Diagnostic only; live defaults
untouched.
"""

import hashlib
import json
import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM_V6,
    ACTION_FEATURE_DIM_V7,
    ACTION_FEATURE_DIM_V7_BATCH1,
    ACTION_FEATURE_NAMES_V6,
    ACTION_FEATURE_NAMES_V7,
    ACTION_FEATURE_NAMES_V7_BATCH1,
    ACTION_FEATURE_VERSION_V6,
    ACTION_FEATURE_VERSION_V7,
    SLICE10_ITEM_EFFECT_FEATURE_NAMES,
    SLICE11_TIMING_PRIORITY_FEATURE_NAMES,
    SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES,
    SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES,
    SLICE14_ACTION_RISK_FEATURE_NAMES,
    SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES,
    SLICE8_STATUS_STAT_FEATURE_NAMES,
    SLICE9_VOLATILE_FEATURE_NAMES,
    build_action_feature_vector_v6,
    build_action_feature_vector_v7,
)
from neural.train_vnext_diagnostic import validate_vnext_checkpoint_metadata

_V6_FINGERPRINT = "ac8fb3d36e29a3a2ed6795f790c34d0a6f1330f6d6ef2262ab4722c58373f049"
_PRIVATE = {"team": [{"species": "Annihilape", "level": 80, "types": ["Fighting", "Ghost"], "active": True}]}


def _fp(names):
    return hashlib.sha256(json.dumps(list(names), ensure_ascii=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _action(move, kind="move"):
    return {"kind": kind, "label": f"{kind}: {move}", "move": move}


def _v7(move, kind="move"):
    return build_action_feature_vector_v7(_action(move, kind), _PRIVATE, {}, None)


def _idx(name):
    return ACTION_FEATURE_NAMES_V7.index(name)


def _val(vec, name):
    return float(vec[_idx(name)])


class SchemaIntegrityTest(unittest.TestCase):
    def test_v7_dim_and_slice_size(self):
        self.assertEqual(
            ACTION_FEATURE_DIM_V7,
            ACTION_FEATURE_DIM_V6
            + len(SLICE8_STATUS_STAT_FEATURE_NAMES)
            + len(SLICE9_VOLATILE_FEATURE_NAMES)
            + len(SLICE10_ITEM_EFFECT_FEATURE_NAMES)
            + len(SLICE11_TIMING_PRIORITY_FEATURE_NAMES)
            + len(SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES)
            + len(SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES)
            + len(SLICE14_ACTION_RISK_FEATURE_NAMES)
            + len(SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES),
        )
        self.assertEqual(ACTION_FEATURE_DIM_V7, len(ACTION_FEATURE_NAMES_V7))
        self.assertEqual(ACTION_FEATURE_DIM_V6, 331)
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH1, 361)
        self.assertEqual(len(SLICE8_STATUS_STAT_FEATURE_NAMES), 30)

    def test_v6_prefix_names_and_fingerprint_unchanged(self):
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:ACTION_FEATURE_DIM_V6], ACTION_FEATURE_NAMES_V6)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7[:ACTION_FEATURE_DIM_V6]), _V6_FINGERPRINT)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V6), _V6_FINGERPRINT)

    def test_v7_batch1_prefix_fingerprint_stable(self):
        # The frozen 361D v7 batch-1 prefix (v6 + typed status/stat) must stay
        # byte-identical as later batches append; this is the published batch-1 fp.
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:ACTION_FEATURE_DIM_V7_BATCH1], ACTION_FEATURE_NAMES_V7_BATCH1)
        self.assertEqual(
            _fp(ACTION_FEATURE_NAMES_V7[:ACTION_FEATURE_DIM_V7_BATCH1]),
            "85225a44776b6fc6e44b9900432acb253bacf3339a276d60febbd70eac4fd77f",
        )

    def test_v7_vector_prefix_equals_v6(self):
        for move, kind in [("Thunderbolt", "move"), ("Swords Dance", "move"), ("Surf", "move"), ("Latias", "switch")]:
            action = _action(move, kind)
            v6 = build_action_feature_vector_v6(action, _PRIVATE, {}, None)
            v7 = build_action_feature_vector_v7(action, _PRIVATE, {}, None)
            self.assertEqual(v7.shape[0], ACTION_FEATURE_DIM_V7, move)
            np.testing.assert_array_equal(v7[:ACTION_FEATURE_DIM_V6], v6)

    def test_v7_preserves_v6_rollout_repeat_chain_prefix(self):
        tactical = {
            "history_complete": True,
            "own": {
                "repeat_chain": {
                    "move": "rollout",
                    "successful_count": 2,
                    "multiplier": 4.0,
                    "known": True,
                    "exact": True,
                    "provenance": "protocol_complete",
                    "reset_observed": False,
                    "defense_curl_active": False,
                    "defense_curl_known": True,
                    "forced_continuation_active": True,
                }
            },
            "opponent": {},
        }
        action = _action("Rollout")
        v6 = build_action_feature_vector_v6(action, _PRIVATE, tactical, None)
        v7 = build_action_feature_vector_v7(action, _PRIVATE, tactical, None)
        np.testing.assert_array_equal(v7[:ACTION_FEATURE_DIM_V6], v6)
        by_name = dict(zip(ACTION_FEATURE_NAMES_V6, v6))
        self.assertEqual(by_name["repeat_chain_is_rollout"], 1.0)
        self.assertGreater(by_name["repeat_chain_count_norm"], 0.0)


class CheckpointGuardTest(unittest.TestCase):
    def _meta(self, version, dim, fp):
        return {
            "state_feature_version": "live-private-belief-v7",
            "state_dim": 3208,
            "action_feature_version": version,
            "action_dim": dim,
            "action_feature_names_sha256": fp,
        }

    def test_v6_checkpoint_rejected_as_v7(self):
        v6_meta = self._meta(ACTION_FEATURE_VERSION_V6, ACTION_FEATURE_DIM_V6, _V6_FINGERPRINT)
        with self.assertRaises(ValueError):
            validate_vnext_checkpoint_metadata(
                v6_meta,
                expected_action_version=ACTION_FEATURE_VERSION_V7,
                expected_action_dim=ACTION_FEATURE_DIM_V7,
                expected_action_feature_names_sha256=_fp(ACTION_FEATURE_NAMES_V7),
            )

    def test_v7_checkpoint_rejected_as_v6(self):
        v7_meta = self._meta(ACTION_FEATURE_VERSION_V7, ACTION_FEATURE_DIM_V7, _fp(ACTION_FEATURE_NAMES_V7))
        with self.assertRaises(ValueError):
            validate_vnext_checkpoint_metadata(
                v7_meta,
                expected_action_version=ACTION_FEATURE_VERSION_V6,
                expected_action_dim=ACTION_FEATURE_DIM_V6,
                expected_action_feature_names_sha256=_V6_FINGERPRINT,
            )


class TypedEffectTest(unittest.TestCase):
    def test_ordinary_damaging_move_has_zero_typed_fields(self):
        vec = _v7("Surf")
        for name in SLICE8_STATUS_STAT_FEATURE_NAMES:
            self.assertEqual(_val(vec, name), 0.0, name)

    def test_switch_has_zero_typed_fields(self):
        vec = _v7("Latias", "switch")
        for name in SLICE8_STATUS_STAT_FEATURE_NAMES:
            self.assertEqual(_val(vec, name), 0.0, name)

    def test_guaranteed_status_move(self):
        vec = _v7("Will-O-Wisp")
        self.assertEqual(_val(vec, "effect_target_status_brn_chance"), 1.0)
        self.assertEqual(_val(vec, "effect_target_status_par_chance"), 0.0)

    def test_secondary_status_is_probability_not_one(self):
        vec = _v7("Thunderbolt")  # 10% paralysis
        par = _val(vec, "effect_target_status_par_chance")
        self.assertAlmostEqual(par, 0.10, places=4)
        self.assertNotEqual(par, 1.0)

    def test_secondary_status_scald_burn(self):
        self.assertAlmostEqual(_val(_v7("Scald"), "effect_target_status_brn_chance"), 0.30, places=4)

    def test_target_stat_drop_secondary(self):
        vec = _v7("Crunch")  # 20% Def drop
        self.assertAlmostEqual(_val(vec, "effect_target_boost_def_stage"), -1.0 / 6.0, places=4)
        self.assertAlmostEqual(_val(vec, "effect_target_stat_chance"), 0.20, places=4)

    def test_self_boost_move(self):
        vec = _v7("Swords Dance")  # +2 Atk, guaranteed
        self.assertAlmostEqual(_val(vec, "effect_self_boost_atk_stage"), 2.0 / 6.0, places=4)
        self.assertEqual(_val(vec, "effect_self_stat_chance"), 1.0)

    def test_secondary_self_boost_keeps_secondary_chance(self):
        # Meteor Mash's self Atk+1 is a 20% secondary, not guaranteed.
        vec = _v7("Meteor Mash")
        self.assertAlmostEqual(_val(vec, "effect_self_boost_atk_stage"), 1.0 / 6.0, places=4)
        self.assertAlmostEqual(_val(vec, "effect_self_stat_chance"), 0.20, places=4)

    def test_multi_outcome_status_distribution(self):
        # Tri Attack: 20% split across burn/par/freeze -> ~6.67% each, not a single 1.0.
        vec = _v7("Tri Attack")
        for key in ("brn", "par", "frz"):
            self.assertAlmostEqual(_val(vec, f"effect_target_status_{key}_chance"), 0.20 / 3.0, places=3)


if __name__ == "__main__":
    unittest.main()
