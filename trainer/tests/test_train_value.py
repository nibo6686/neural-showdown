import tempfile
import unittest
from pathlib import Path

import numpy as np

from neural.train_value import train_value_model


class TrainValueSmokeTest(unittest.TestCase):
    def test_train_value_tiny_dataset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            dataset_path = root / "value.npz"
            checkpoint_path = root / "value.pt"
            np.savez(
                dataset_path,
                states=np.random.RandomState(1).randn(8, 5).astype(np.float32),
                legal_masks=np.ones((8, 13), dtype=np.float32),
                value_targets=np.asarray([1, -1, 1, -1, 0, 1, -1, 0], dtype=np.float32),
                final_results=np.asarray([1, -1, 1, -1, 0, 1, -1, 0], dtype=np.float32),
                discounted_returns=np.asarray([1, -1, 1, -1, 0, 1, -1, 0], dtype=np.float32),
            )
            report = train_value_model(
                dataset_path=dataset_path,
                checkpoint_path=checkpoint_path,
                hidden_sizes=[8],
                epochs=1,
                batch_size=4,
            )
            self.assertTrue(checkpoint_path.exists())
            self.assertTrue(checkpoint_path.with_suffix(".train.json").exists())
            self.assertEqual(report["num_examples"], 8)
            self.assertIn("train_loss", report)


if __name__ == "__main__":
    unittest.main()
