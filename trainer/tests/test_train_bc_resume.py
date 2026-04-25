import tempfile
import unittest
from pathlib import Path

import numpy as np

from neural.train_bc import train_behavior_cloning


def _write_npz(path: Path, input_size: int = 5) -> None:
    states = np.random.default_rng(123).normal(size=(8, input_size)).astype(np.float32)
    masks = np.ones((8, 13), dtype=np.float32)
    actions = np.arange(8, dtype=np.int64) % 13
    returns = np.linspace(-1.0, 1.0, 8, dtype=np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, states=states, legal_masks=masks, actions=actions, returns=returns)


def _config(tmpdir: str, shard_name: str = "data.npz") -> dict:
    root = Path(tmpdir)
    return {
        "_config_path": str(root / "config.json"),
        "profile": "test",
        "dataset": {"shard_path": shard_name},
        "training": {
            "batch_size": 4,
            "epochs": 1,
            "hidden_sizes": [8],
            "learning_rate": 0.001,
            "weight_decay": 0.0,
            "train_split": 0.75,
            "resume": True,
            "save_timestamped": False,
            "checkpoint_path": "model.pt",
            "best_checkpoint_path": "model.best.pt",
        },
    }


class BehaviorCloningResumeTest(unittest.TestCase):
    def test_resume_continues_epoch_and_global_step(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_npz(Path(tmpdir) / "data.npz")
            config = _config(tmpdir)
            first = train_behavior_cloning(config)
            second = train_behavior_cloning(config)
            self.assertFalse(first["resumed"])
            self.assertTrue(second["resumed"])
            self.assertEqual(first["end_epoch"], 1)
            self.assertEqual(second["start_epoch"], 1)
            self.assertEqual(second["end_epoch"], 2)
            self.assertGreater(second["global_step"], first["global_step"])

    def test_incompatible_checkpoint_fails_clearly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_npz(Path(tmpdir) / "data.npz", input_size=5)
            config = _config(tmpdir)
            train_behavior_cloning(config)
            _write_npz(Path(tmpdir) / "other.npz", input_size=6)
            bad_config = _config(tmpdir, shard_name="other.npz")
            with self.assertRaisesRegex(ValueError, "input_size"):
                train_behavior_cloning(bad_config)


if __name__ == "__main__":
    unittest.main()
