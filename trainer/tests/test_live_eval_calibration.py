"""Tests for the live-eval calibration audit and the opt-in calibrated /evaluate.

Covers:
- metric helpers (_auc / _pearson / compute_metrics) on synthetic data with known
  properties;
- the bounded live/sim calibrated state-eval helper, including perspective
  orientation (p2 flips relative to p1);
- the /evaluate opt-in: default response carries state_eval=None, and a populated
  dict only when NEURAL_EVAL_STATE_SCORER=live_sim_value.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from neural import live_eval_server
from neural.live_eval_server import EvalRequest, evaluate_with_model, reset_model_caches
from neural.live_private_features import FEATURE_DIM, FEATURE_VERSION
from neural.models.policy_value_mlp import PolicyValueMLP
from neural.models.value_mlp import BoundedValueMLP
from neural import live_eval_calibration as calib


def _save_policy_checkpoint(path: Path, input_size: int) -> None:
    model = PolicyValueMLP(input_size=input_size, hidden_sizes=[4], action_size=13)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_size": input_size,
            "hidden_sizes": [4],
            "action_size": 13,
            "feature_version": FEATURE_VERSION if input_size == FEATURE_DIM else "public-replay-events-v1",
        },
        path,
    )


def _save_bounded_checkpoint(path: Path) -> None:
    model = BoundedValueMLP(input_size=FEATURE_DIM, hidden_sizes=[8])
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "feature_dim": FEATURE_DIM,
            "feature_version": FEATURE_VERSION,
            "hidden_sizes": [8],
            "bounded_output": True,
            "model_type": "live-sim-bounded-value",
        },
        path,
    )


class CalibrationMetricTest(unittest.TestCase):
    def test_auc_perfect_and_random(self):
        scores = np.array([0.1, 0.2, 0.8, 0.9])
        labels = np.array([0, 0, 1, 1])
        self.assertAlmostEqual(calib._auc(scores, labels), 1.0, places=6)
        # reversed labels => AUC 0
        self.assertAlmostEqual(calib._auc(scores, labels[::-1]), 0.0, places=6)

    def test_auc_undefined_single_class(self):
        self.assertIsNone(calib._auc(np.array([0.1, 0.2]), np.array([1, 1])))

    def test_pearson_and_spearman(self):
        a = np.array([0.0, 1.0, 2.0, 3.0])
        self.assertAlmostEqual(calib._pearson(a, 2 * a + 1), 1.0, places=6)
        self.assertAlmostEqual(calib._spearman(a, a ** 3), 1.0, places=6)

    def test_compute_metrics_separates_good_and_collapsed_scorer(self):
        # good scorer == outcome; collapsed scorer == +1 constant.
        rows = []
        for i in range(20):
            outcome = 1.0 if i % 2 == 0 else -1.0
            good = 0.8 * outcome
            rows.append(
                {
                    "outcome": outcome,
                    "tags": ["near_terminal"] if i < 4 else [],
                    "scores": {"good": good, "collapsed": 1.0, "material": good},
                }
            )
        # perspective-flip pairs: good anti-symmetric, collapsed not.
        flips = {
            "good": [(0.5, -0.5), (0.8, -0.8)],
            "collapsed": [(1.0, 1.0), (1.0, 1.0)],
            "material": [(0.5, -0.5)],
        }
        m = calib.compute_metrics(rows, flips)["per_scorer"]
        self.assertGreater(m["good"]["sign_accuracy"], 0.99)
        self.assertLess(m["good"]["brier"], 0.05)
        # collapsed: constant +1 => mean winning and losing score both +1.
        self.assertEqual(m["collapsed"]["mean_winning_score"], 1.0)
        self.assertEqual(m["collapsed"]["mean_losing_score"], 1.0)
        # perspective sanity: good ~0, collapsed ~2.
        self.assertLess(m["good"]["perspective_flip_mean_abs_sum"], 1e-6)
        self.assertAlmostEqual(m["collapsed"]["perspective_flip_mean_abs_sum"], 2.0, places=6)


class CalibratedStateEvalTest(unittest.TestCase):
    def setUp(self):
        reset_model_caches()

    def tearDown(self):
        reset_model_caches()
        os.environ.pop("NEURAL_EVAL_STATE_SCORER", None)

    def test_perspective_orientation_flips_for_p2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = Path(tmp) / "live_sim.pt"
            _save_bounded_checkpoint(ckpt)
            with patch("neural.live_eval_server.LIVE_SIM_VALUE_MODEL_PATH", ckpt):
                reset_model_caches()
                features = np.random.RandomState(0).randn(FEATURE_DIM).astype(np.float32)
                p1 = live_eval_server._calibrated_state_eval(features, "p1")
                reset_model_caches()
                p2 = live_eval_server._calibrated_state_eval(features, "p2")
        self.assertTrue(-1.0 <= p1["value"] <= 1.0)
        self.assertEqual(p1["scorer"], "live_sim_value")
        # same features, same player_win_prob, but p1 orientation flips for p2.
        self.assertAlmostEqual(p1["player_win_prob"], p2["player_win_prob"], places=6)
        self.assertAlmostEqual(p1["p1_win_prob"], 1.0 - p2["p1_win_prob"], places=6)


class EvaluateOptInTest(unittest.TestCase):
    def setUp(self):
        reset_model_caches()

    def tearDown(self):
        reset_model_caches()
        os.environ.pop("NEURAL_EVAL_STATE_SCORER", None)

    def _payload(self) -> EvalRequest:
        return EvalRequest(
            room_id="battle-test",
            url="https://play.pokemonshowdown.com/battle-test",
            player="p1",
            log=[
                "|player|p1|Alice",
                "|player|p2|Bob",
                "|turn|1",
                "|switch|p2a: Charizard|Charizard, L80, M|100/100",
                "|move|p1a: Pikachu|Thunderbolt|p2a: Charizard",
            ],
            request={
                "side": {
                    "id": "p1",
                    "pokemon": [
                        {"ident": "p1: Pikachu", "details": "Pikachu, L80", "condition": "100/100", "active": True},
                        {"ident": "p1: Bulbasaur", "details": "Bulbasaur, L80", "condition": "100/100", "active": False},
                    ],
                },
                "active": [{"moves": [{"move": "Thunderbolt", "pp": 10, "maxpp": 15, "disabled": False}]}],
            },
            legal_actions=[{"kind": "move", "label": "Thunderbolt", "index": 0}],
        )

    def _patched(self, tmp: str):
        old = Path(tmp) / "old.pt"
        new = Path(tmp) / "new.pt"
        v2 = Path(tmp) / "v2.pt"
        policy = Path(tmp) / "missing_policy.pt"
        bounded = Path(tmp) / "live_sim.pt"
        _save_policy_checkpoint(old, 31)
        _save_policy_checkpoint(new, FEATURE_DIM)
        _save_policy_checkpoint(v2, FEATURE_DIM)
        _save_bounded_checkpoint(bounded)
        return patch.multiple(
            "neural.live_eval_server",
            OLD_VALUE_MODEL_PATH=old,
            LIVE_PRIVATE_VALUE_MODEL_V2_PATH=v2,
            LIVE_PRIVATE_VALUE_MODEL_PATH=new,
            REPLAY_POLICY_MODEL_PATH=policy,
            LIVE_SIM_VALUE_MODEL_PATH=bounded,
        )

    def test_calibrated_scorer_is_default(self):
        os.environ.pop("NEURAL_EVAL_STATE_SCORER", None)
        with tempfile.TemporaryDirectory() as tmp, self._patched(tmp):
            reset_model_caches()
            response = evaluate_with_model(self._payload())
        # The displayed value/win prob now come from the bounded calibrated head.
        self.assertEqual(response["state_scorer"], "live_sim_value")
        se = response["state_eval"]
        self.assertIsInstance(se, dict)
        self.assertEqual(se["scorer"], "live_sim_value")
        self.assertTrue(se["bounded_output"])
        self.assertTrue(-1.0 <= response["value"] <= 1.0)
        self.assertEqual(response["value"], se["value"])
        self.assertEqual(response["p1_win_prob"], se["p1_win_prob"])
        # the legacy (collapsed) head value is retained for diagnostics, not display.
        self.assertIn("legacy_value", response)
        self.assertIn("legacy_p1_win_prob", response)

    def test_legacy_scorer_can_be_forced(self):
        os.environ["NEURAL_EVAL_STATE_SCORER"] = "old_live_private"
        with tempfile.TemporaryDirectory() as tmp, self._patched(tmp):
            reset_model_caches()
            response = evaluate_with_model(self._payload())
        self.assertEqual(response["state_scorer"], "old_live_private")
        self.assertIsNone(response["state_eval"])
        # forced legacy: displayed prob equals the legacy mapping.
        self.assertEqual(response["p1_win_prob"], response["legacy_p1_win_prob"])
        self.assertEqual(response["value"], response["legacy_value"])


class SanitizedEvalLogTest(unittest.TestCase):
    def test_record_omits_private_request_and_keeps_scores(self):
        payload = EvalRequest(
            room_id="battle-xyz",
            url="https://play.pokemonshowdown.com/battle-xyz",
            player="p1",
            log=["|turn|1", "|move|p1a: Pikachu|Thunderbolt|p2a: Charizard"],
            request={"side": {"id": "p1", "pokemon": [{"ident": "p1: SecretMon", "details": "Garchomp, L80"}]}},
        )
        response = {
            "value": 0.4,
            "p1_win_prob": 0.7,
            "state_eval": {"scorer": "live_sim_value", "p1_win_prob": 0.62},
            "feature_version": FEATURE_VERSION,
            "model_type": "live-private-belief-value",
            "top_actions": [{"label": "move: Thunderbolt", "score": 0.9, "extra": "x"}],
            "debug_summary": {"damage_engine_status": "ok"},
        }
        record = live_eval_server._sanitized_eval_log_record(payload, response)
        blob = repr(record)
        self.assertNotIn("SecretMon", blob)
        self.assertNotIn("Garchomp", blob)
        self.assertEqual(record["room_id"], "battle-xyz")
        self.assertEqual(record["value"], 0.4)
        self.assertEqual(record["state_eval"]["scorer"], "live_sim_value")
        self.assertEqual(record["top_actions"][0]["label"], "move: Thunderbolt")
        self.assertNotIn("request", record)


if __name__ == "__main__":
    unittest.main()
