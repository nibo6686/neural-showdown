import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from neural.train_vnext_diagnostic import (
    EXPECTED_ACTION_DIM,
    EXPECTED_STATE_DIM,
    build_diagnostic_model,
    build_vnext_checkpoint_metadata,
    load_and_validate_diagnostic_config,
    load_diagnostic_dataset,
)
from neural.evaluate_vnext_action_rank import evaluate as offline_evaluate
from neural import vnext_inference as vinf

from test_train_vnext_diagnostic import _write_fixture


def _build_checkpoint(root: Path, *, with_fingerprints: bool = True):
    config_path = _write_fixture(root)
    config = load_and_validate_diagnostic_config(config_path)
    dataset = load_diagnostic_dataset(config)
    model = build_diagnostic_model(config)
    payload = {"model_state_dict": model.state_dict(), "model_config": config["model"]}
    if with_fingerprints:
        payload.update(build_vnext_checkpoint_metadata(dataset))
    else:
        payload.update(
            {
                "state_feature_version": "live-private-belief-v7",
                "action_feature_version": "legal-action-v5",
                "state_dim": EXPECTED_STATE_DIM,
                "action_dim": EXPECTED_ACTION_DIM,
            }
        )
    checkpoint_path = root / "model.pt"
    torch.save(payload, checkpoint_path)
    return config_path, checkpoint_path, dataset


def _zeros_action():
    return np.zeros(EXPECTED_ACTION_DIM, dtype=np.float32)


class VNextInferenceTest(unittest.TestCase):
    def test_load_with_strict_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path, checkpoint_path, _ = _build_checkpoint(Path(tmpdir))
            ranker = vinf.VNextActionRanker.load(config_path, checkpoint_path)
        self.assertEqual(ranker.state_dim, EXPECTED_STATE_DIM)
        self.assertEqual(ranker.action_dim, EXPECTED_ACTION_DIM)
        self.assertEqual(ranker.metadata["schema_validation"]["status"], "PASS")
        self.assertTrue(ranker.metadata["schema_validation"]["fingerprints_complete"])

    def test_missing_fingerprint_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path, checkpoint_path, _ = _build_checkpoint(
                Path(tmpdir), with_fingerprints=False
            )
            with self.assertRaisesRegex(ValueError, "missing required fingerprint"):
                vinf.VNextActionRanker.load(config_path, checkpoint_path)
            result = vinf.safe_load(config_path, checkpoint_path)
        self.assertFalse(result["ok"])
        self.assertIn("missing required fingerprint", result["reason"])

    def test_missing_checkpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _write_fixture(Path(tmpdir))
            result = vinf.safe_load(config_path, Path(tmpdir) / "nope.pt")
        self.assertFalse(result["ok"])
        self.assertIsNone(result["ranker"])

    def test_score_shape_and_determinism(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path, checkpoint_path, dataset = _build_checkpoint(Path(tmpdir))
            ranker = vinf.VNextActionRanker.load(config_path, checkpoint_path)
            state_index = int(dataset.split_group_state_indices["validation"][0])
            candidates = vinf.dataset_group_candidates(dataset, state_index)
            state_vector = dataset.state_features[state_index].astype(np.float32)
            scores_a = ranker.score(state_vector, candidates)
            scores_b = ranker.score(state_vector, candidates)
        self.assertEqual(scores_a.shape, (len(candidates),))
        self.assertTrue(np.allclose(scores_a, scores_b))

    def test_offline_evaluator_parity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path, checkpoint_path, dataset = _build_checkpoint(Path(tmpdir))
            ranker = vinf.VNextActionRanker.load(config_path, checkpoint_path)
            harness_top1 = vinf.top1_over_split(ranker, dataset, "validation")
            offline = offline_evaluate(config_path, checkpoint_path, split="validation", example_count=0)
        self.assertAlmostEqual(harness_top1, offline["model"]["top1"], places=9)

    def test_no_pad_or_truncate_in_source(self):
        source = Path(vinf.__file__).read_text(encoding="utf-8")
        self.assertNotIn("np.pad", source)
        # Wrong-sized action features are a hard error, not silently reshaped.
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path, checkpoint_path, dataset = _build_checkpoint(Path(tmpdir))
            ranker = vinf.VNextActionRanker.load(config_path, checkpoint_path)
            state_vector = dataset.state_features[
                int(dataset.split_group_state_indices["validation"][0])
            ].astype(np.float32)
            bad = [{"action_features": np.zeros(EXPECTED_ACTION_DIM - 1, dtype=np.float32), "kind": "move"}]
            with self.assertRaisesRegex(ValueError, "does not pad or truncate"):
                ranker.score(state_vector, bad)

    def test_unavailable_candidate_never_selected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path, checkpoint_path, dataset = _build_checkpoint(Path(tmpdir))
            ranker = vinf.VNextActionRanker.load(config_path, checkpoint_path)
            state_vector = dataset.state_features[
                int(dataset.split_group_state_indices["validation"][0])
            ].astype(np.float32)
            candidates = [
                {"action_features": _zeros_action(), "kind": "switch", "switch_slot": 3, "available": False, "label": "blocked"},
                {"action_features": _zeros_action(), "kind": "move", "move_slot": 1, "available": True, "label": "ok1"},
                {"action_features": _zeros_action(), "kind": "move", "move_slot": 2, "disabled": True, "label": "disabled"},
            ]
            result = ranker.recommend(state_vector, candidates)
        self.assertTrue(result["ok"])
        self.assertEqual(result["selected"]["label"], "ok1")
        self.assertEqual(result["choice"], "move 1")
        # Only the single available candidate is ranked.
        self.assertEqual(len(result["ranked"]), 1)

    def test_command_serialization(self):
        self.assertEqual(vinf.serialize_candidate_command({"kind": "move", "move_slot": 3}), "move 3")
        self.assertEqual(
            vinf.serialize_candidate_command({"kind": "move_tera", "move_slot": 1}),
            "move 1 terastallize",
        )
        self.assertEqual(
            vinf.serialize_candidate_command({"kind": "move", "move_slot": 2, "is_tera": True}),
            "move 2 terastallize",
        )
        self.assertEqual(vinf.serialize_candidate_command({"kind": "switch", "switch_slot": 5}), "switch 5")
        # Tera command must differ from the plain move command.
        self.assertNotEqual(
            vinf.serialize_candidate_command({"kind": "move", "move_slot": 1}),
            vinf.serialize_candidate_command({"kind": "move_tera", "move_slot": 1}),
        )
        # Invalid slots fail closed.
        self.assertIsNone(vinf.serialize_candidate_command({"kind": "move", "move_slot": 0}))
        self.assertIsNone(vinf.serialize_candidate_command({"kind": "switch", "switch_slot": 9}))
        self.assertIsNone(vinf.serialize_candidate_command({"kind": "unknown", "move_slot": 1}))

    def test_fallback_no_candidates_and_all_unavailable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path, checkpoint_path, dataset = _build_checkpoint(Path(tmpdir))
            ranker = vinf.VNextActionRanker.load(config_path, checkpoint_path)
            state_vector = dataset.state_features[
                int(dataset.split_group_state_indices["validation"][0])
            ].astype(np.float32)
            empty = ranker.recommend(state_vector, [])
            all_unavail = ranker.recommend(
                state_vector,
                [{"action_features": _zeros_action(), "kind": "move", "move_slot": 1, "available": False}],
            )
            bad_command = ranker.recommend(
                state_vector,
                [{"action_features": _zeros_action(), "kind": "move", "move_slot": 99}],
            )
        for result, reason in (
            (empty, "no_legal_candidates"),
            (all_unavail, "all_candidates_unavailable"),
            (bad_command, "command_serialization_failed"),
        ):
            self.assertFalse(result["ok"])
            self.assertEqual(result["choice"], vinf.SAFE_FALLBACK_CHOICE)
            self.assertEqual(result["reason"], reason)

    def test_default_live_path_does_not_reference_harness(self):
        root = Path(vinf.__file__).resolve().parents[3]
        # The legacy recommender must stay entirely free of vNext.
        recommender = (root / "trainer/src/neural/live_action_recommender.py").read_text(encoding="utf-8")
        self.assertNotIn("vnext_inference", recommender)
        self.assertNotIn("vnext_live_shadow", recommender)
        # In the live server, vNext is opt-in only: not imported at module top
        # level and not referenced by the default evaluate path (the opt-in route
        # imports it lazily). Everything before the dry-run route must be vNext-free.
        server = (root / "trainer/src/neural/live_eval_server.py").read_text(encoding="utf-8")
        default_path = server.split("def evaluate_vnext_dry_run", 1)[0]
        self.assertNotIn("vnext_inference", default_path)
        self.assertNotIn("vnext_live_shadow", default_path)


if __name__ == "__main__":
    unittest.main()
