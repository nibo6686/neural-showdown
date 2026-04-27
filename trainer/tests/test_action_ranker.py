import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from neural.action_features import ACTION_FEATURE_DIM, build_action_feature_vector
from neural.build_action_rank_dataset import build_action_rank_dataset
from neural.live_action_recommender import recommend_actions, reset_action_ranker_cache
from neural.live_private_features import FEATURE_DIM
from neural.models.action_ranker import ActionRankerMLP
from neural.train_action_ranker import train_action_ranker


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "replay_sample.log"


class ActionFeatureTest(unittest.TestCase):
    def test_move_action_features_differ_by_move_metadata(self):
        private_state = {
            "active_moves": [
                {"id": "flipturn", "name": "Flip Turn", "pp": 10, "maxpp": 20, "known_from_request": True},
                {"id": "knockoff", "name": "Knock Off", "pp": 20, "maxpp": 20, "known_from_request": True},
                {"id": "surf", "name": "Surf", "pp": 8, "maxpp": 15, "known_from_request": True},
                {"id": "icebeam", "name": "Ice Beam", "pp": 10, "maxpp": 10, "known_from_request": True},
            ]
        }
        vectors = [
            build_action_feature_vector({"kind": "move", "label": f"move: {name}", "index": index}, private_state)
            for index, name in enumerate(["Flip Turn", "Knock Off", "Surf", "Ice Beam"])
        ]
        self.assertTrue(all(vector.shape[0] == ACTION_FEATURE_DIM for vector in vectors))
        for left in range(len(vectors)):
            for right in range(left + 1, len(vectors)):
                self.assertFalse(np.allclose(vectors[left], vectors[right]))

    def test_switch_action_features_differ_by_target(self):
        private_state = {
            "team": [
                {"species": "Glimmora", "active": True, "hp_fraction": 0.2},
                {"species": "Latias", "active": False, "hp_fraction": 1.0, "item": "Leftovers", "moves": ["Recover"]},
                {"species": "Regice", "active": False, "hp_fraction": 0.4, "status": "par", "moves": ["Ice Beam", "Thunderbolt"]},
            ]
        }
        latias = build_action_feature_vector({"kind": "switch", "label": "switch: Latias", "index": 4}, private_state)
        regice = build_action_feature_vector({"kind": "switch", "label": "switch: Regice", "index": 5}, private_state)
        self.assertEqual(latias.shape[0], ACTION_FEATURE_DIM)
        self.assertFalse(np.allclose(latias, regice))


class ActionRankDatasetTrainTest(unittest.TestCase):
    def test_build_action_rank_dataset_groups_and_one_positive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw = root / "raw"
            raw.mkdir()
            (raw / "fixture.log").write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            output = root / "rank.npz"
            report = build_action_rank_dataset(
                replay_dir=raw,
                trajectories_path=root / "trajectories.jsonl.gz",
                output_path=output,
                report_json_path=root / "report.json",
                report_md_path=root / "report.md",
            )
            self.assertTrue(output.exists())
            self.assertGreater(report["decisions"], 0)
            with np.load(output, allow_pickle=True) as data:
                groups = data["group_ids"]
                labels = data["labels"]
                for group in np.unique(groups):
                    self.assertEqual(int(labels[groups == group].sum()), 1)

    def test_action_ranker_smoke_training_on_tiny_synthetic_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dataset = root / "tiny.npz"
            checkpoint = root / "ranker.pt"
            rng = np.random.RandomState(9)
            states = rng.randn(6, FEATURE_DIM).astype(np.float32)
            actions = rng.randn(6, ACTION_FEATURE_DIM).astype(np.float32)
            labels = np.asarray([1, 0, 0, 0, 1, 0], dtype=np.int8)
            group_ids = np.asarray([0, 0, 0, 1, 1, 1], dtype=np.int64)
            np.savez(
                dataset,
                state_features=states,
                action_features=actions,
                labels=labels,
                group_ids=group_ids,
                turns=np.asarray([1, 1, 1, 2, 2, 2], dtype=np.int16),
                action_indices=np.asarray([0, 1, 4, 0, 4, 5], dtype=np.int16),
                action_kinds=np.asarray(["move", "move", "switch", "move", "switch", "switch"]),
                action_labels=np.asarray(["move: A", "move: B", "switch: C", "move: D", "switch: E", "switch: F"]),
                source_ids=np.asarray(["fixture"] * 6),
            )
            report = train_action_ranker(
                dataset_path=dataset,
                checkpoint_path=checkpoint,
                policy_checkpoint_path=root / "missing-policy.pt",
                epochs=1,
                groups_per_batch=1,
            )
            self.assertTrue(checkpoint.exists())
            self.assertEqual(report["decisions"], 2)

    def test_live_recommender_uses_action_ranker_checkpoint_if_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            checkpoint = root / "ranker.pt"
            model = ActionRankerMLP(input_size=FEATURE_DIM + ACTION_FEATURE_DIM, hidden_sizes=[4])
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "input_size": FEATURE_DIM + ACTION_FEATURE_DIM,
                    "state_dim": FEATURE_DIM,
                    "action_dim": ACTION_FEATURE_DIM,
                    "hidden_sizes": [4],
                    "model_type": "action-ranker",
                },
                checkpoint,
            )
            payload = type(
                "Payload",
                (),
                {
                    "request": {},
                    "legal_actions": [
                        {"kind": "move", "label": "Knock Off", "index": 0},
                        {"kind": "move", "label": "Surf", "index": 1},
                    ],
                },
            )()
            reset_action_ranker_cache()
            with patch("neural.live_action_recommender.DEFAULT_ACTION_RANKER_PATH", checkpoint):
                report = recommend_actions(
                    payload=payload,
                    private_state={
                        "active_moves": [
                            {"id": "knockoff", "name": "Knock Off", "pp": 10, "maxpp": 10},
                            {"id": "surf", "name": "Surf", "pp": 10, "maxpp": 10},
                        ],
                        "team": [{"species": "Glimmora", "active": True, "hp_fraction": 1.0}],
                    },
                    opponent_belief={"opponents": []},
                    trajectory={"turns": []},
                    public_features=np.zeros(31, dtype=np.float32),
                    live_features=np.zeros(FEATURE_DIM, dtype=np.float32),
                    current_value=0.0,
                    value_model=None,
                    value_metadata={},
                    policy_loader=lambda: (None, {"warning": "missing"}),
                    device=torch.device("cpu"),
                )
            reset_action_ranker_cache()
        self.assertTrue(report["action_ranker_loaded"])
        self.assertEqual(report["action_recommendation_method"], "action_ranker")
        self.assertTrue(all(action["method"] == "action_ranker" for action in report["top_actions"]))
        self.assertTrue(all(action["ranker_score"] is not None for action in report["top_actions"]))


if __name__ == "__main__":
    unittest.main()
