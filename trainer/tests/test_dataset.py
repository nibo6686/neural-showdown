import tempfile
import unittest
from pathlib import Path

import numpy as np

from neural.build_dataset import write_shard
from neural.build_dataset import merge_shards


class DatasetRoundTripTest(unittest.TestCase):
    def test_write_shard_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            shard_path = Path(tmpdir) / "dataset.npz"
            records = [
                {
                    "view": {
                        "env_id": "env-1",
                        "format": "gen9randombattle",
                        "gen": 9,
                        "turn": 1,
                        "player": "p1",
                        "opponent": "p2",
                        "terminated": False,
                        "winner": None,
                        "names": {"p1": "A", "p2": "B"},
                        "team_size": {"p1": 6, "p2": 6},
                        "active": {"self": None, "opponent": None},
                        "field": {"weather": None, "terrain": None, "pseudo_weather": [], "side_conditions": {"self": {}, "opponent": {}}},
                        "self_team": [],
                        "opponent_team": [],
                    },
                    "request": None,
                    "action_index": 0,
                    "return": 1.0,
                }
            ]
            write_shard(records, shard_path)
            with np.load(shard_path) as data:
                self.assertEqual(data["actions"].shape, (1,))
                self.assertEqual(data["returns"].shape, (1,))
                self.assertEqual(float(data["returns"][0]), 1.0)

    def test_merge_shards_concatenates_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir) / "first.npz"
            second = Path(tmpdir) / "second.npz"
            output = Path(tmpdir) / "merged.npz"
            for path, action in [(first, 1), (second, 2)]:
                np.savez(
                    path,
                    states=np.zeros((1, 3), dtype=np.float32),
                    legal_masks=np.ones((1, 13), dtype=np.float32),
                    actions=np.asarray([action], dtype=np.int64),
                    returns=np.asarray([1.0], dtype=np.float32),
                )
            report = merge_shards([first, second], output)
            self.assertEqual(report["records"], 2)
            with np.load(output) as data:
                self.assertEqual(data["states"].shape, (2, 3))
                self.assertEqual(data["actions"].tolist(), [1, 2])


if __name__ == "__main__":
    unittest.main()
