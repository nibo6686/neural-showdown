import hashlib
import json
import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM_V5,
    ACTION_FEATURE_DIM_V6,
    ACTION_FEATURE_NAMES_V5,
    ACTION_FEATURE_NAMES_V6,
    ACTION_FEATURE_VERSION_V5,
    ACTION_FEATURE_VERSION_V6,
    build_action_feature_vector_v5,
    build_action_feature_vector_v6,
)
from neural.resolved_action_impact import resolve_action_impact
from neural.resolved_action_impact_diagnostic import _action, _approx
from neural.tactical_state import build_tactical_state
from neural.train_vnext_diagnostic import validate_vnext_checkpoint_metadata


def _fingerprint(names):
    payload = json.dumps(list(names), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _repeat_state(move, count, *, known=True, exact=True):
    return {
        "history_complete": known,
        "own": {
            "repeat_chain": {
                "move": move,
                "successful_count": count,
                "multiplier": float(2 ** count),
                "known": known,
                "exact": exact,
                "provenance": "protocol_complete" if exact else "unknown",
                "reset_observed": False,
                "defense_curl_active": False,
                "defense_curl_known": known,
                "forced_continuation_active": move == "rollout" and count > 0,
            }
        },
        "opponent": {},
    }


class LegalActionV6RepeatChainTest(unittest.TestCase):
    def _impact(self, move, tactical):
        approx = _approx(
            {"species": "Donphan" if move == "Rollout" else "Scizor", "level": 80},
            {"species": "Mew", "level": 80, "hp_fraction": 1.0},
        )
        approx["tactical_state"] = tactical
        return resolve_action_impact(_action(move), approx, enable_repeat_chain=True)

    def test_schema_is_append_only_and_stable(self):
        self.assertEqual(ACTION_FEATURE_VERSION_V5, "legal-action-v5")
        self.assertEqual(ACTION_FEATURE_DIM_V5, 318)
        self.assertEqual(ACTION_FEATURE_VERSION_V6, "legal-action-v6")
        self.assertEqual(ACTION_FEATURE_DIM_V6, 331)
        self.assertEqual(ACTION_FEATURE_NAMES_V6[:ACTION_FEATURE_DIM_V5], ACTION_FEATURE_NAMES_V5)
        self.assertEqual(len(set(ACTION_FEATURE_NAMES_V6)), ACTION_FEATURE_DIM_V6)
        self.assertEqual(
            _fingerprint(ACTION_FEATURE_NAMES_V6),
            "ac8fb3d36e29a3a2ed6795f790c34d0a6f1330f6d6ef2262ab4722c58373f049",
        )

    def test_rollout_and_fury_cutter_scale_with_exact_chain(self):
        for move, move_id in (("Rollout", "rollout"), ("Fury Cutter", "furycutter")):
            base = self._impact(move, _repeat_state(None, 0))
            chained = self._impact(move, _repeat_state(move_id, 1))
            self.assertEqual(base["method"], "smogon_calc")
            self.assertEqual(chained["method"], "smogon_calc")
            self.assertGreater(chained["expected_fraction"], base["expected_fraction"] * 1.8)

    def test_unknown_chain_fails_closed_and_is_not_exact(self):
        tactical = _repeat_state(None, 0, known=False, exact=False)
        impact = self._impact("Rollout", tactical)
        self.assertFalse(impact["available"])
        self.assertEqual(impact["fallback_reason"], "repeat_chain_state_unknown")
        vector = build_action_feature_vector_v6(
            _action("Rollout"),
            {"team": [{"species": "Donphan", "active": True}]},
            tactical,
            impact,
        )
        by_name = dict(zip(ACTION_FEATURE_NAMES_V6, vector))
        self.assertEqual(by_name["repeat_chain_state_known"], 0.0)
        self.assertEqual(by_name["repeat_chain_state_exact"], 0.0)
        self.assertEqual(by_name["repeat_chain_provenance_unknown"], 1.0)
        self.assertEqual(by_name["repeat_chain_count_norm"], 0.0)

    def test_non_repeat_move_preserves_v5_prefix_and_zero_append(self):
        action = _action("Earthquake")
        tactical = _repeat_state("rollout", 2)
        approx = _approx(
            {"species": "Donphan", "level": 80},
            {"species": "Mew", "level": 80, "hp_fraction": 1.0},
        )
        approx["tactical_state"] = tactical
        impact = resolve_action_impact(action, approx, enable_repeat_chain=True)
        v5 = build_action_feature_vector_v5(action, approx["private_state"], tactical, impact)
        v6 = build_action_feature_vector_v6(action, approx["private_state"], tactical, impact)
        self.assertTrue(np.array_equal(v6[:ACTION_FEATURE_DIM_V5], v5))
        self.assertTrue(np.array_equal(v6[ACTION_FEATURE_DIM_V5:], np.zeros(13, dtype=np.float32)))

    def test_protocol_tracker_reconstructs_success_and_reset(self):
        active = build_tactical_state(
            [
                "|start",
                "|switch|p1a: Donphan|Donphan, L80|100/100",
                "|switch|p2a: Mew|Mew, L80|100/100",
                "|turn|1",
                "|move|p1a: Donphan|Rollout|p2a: Mew",
                "|-damage|p2a: Mew|90/100",
                "|turn|2",
            ],
            perspective_side="p1",
        )
        chain = active["own"]["repeat_chain"]
        self.assertTrue(chain["known"])
        self.assertTrue(chain["exact"])
        self.assertEqual(chain["move"], "rollout")
        self.assertEqual(chain["successful_count"], 1)
        self.assertTrue(chain["forced_continuation_active"])

        reset = build_tactical_state(
            [
                "|start",
                "|switch|p1a: Scizor|Scizor, L80|100/100",
                "|switch|p2a: Mew|Mew, L80|100/100",
                "|turn|1",
                "|move|p1a: Scizor|Fury Cutter|p2a: Mew",
                "|-miss|p1a: Scizor|p2a: Mew",
                "|turn|2",
            ],
            perspective_side="p1",
        )
        self.assertIsNone(reset["own"]["repeat_chain"]["move"])
        self.assertEqual(reset["own"]["repeat_chain"]["successful_count"], 0)
        self.assertTrue(reset["own"]["repeat_chain"]["reset_observed"])

    def test_v5_checkpoint_is_rejected_as_v6(self):
        checkpoint = {
            "state_feature_version": "live-private-belief-v7",
            "action_feature_version": "legal-action-v5",
            "state_dim": 3208,
            "action_dim": 318,
        }
        with self.assertRaisesRegex(ValueError, "action schema mismatch"):
            validate_vnext_checkpoint_metadata(
                checkpoint,
                expected_action_version=ACTION_FEATURE_VERSION_V6,
                expected_action_dim=ACTION_FEATURE_DIM_V6,
            )


if __name__ == "__main__":
    unittest.main()
