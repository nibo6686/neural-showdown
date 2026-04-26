import unittest

import numpy as np

from neural.train_bc import compute_awbc_sample_weights


class AwbcWeightsTest(unittest.TestCase):
    def test_sample_weights_are_positive_and_clipped(self):
        advantages = np.asarray([-10.0, 0.0, 10.0], dtype=np.float32)
        weights = compute_awbc_sample_weights(advantages, beta=2.0, min_weight=0.2, max_weight=1.5)
        self.assertEqual(weights.shape, (3,))
        self.assertGreaterEqual(float(weights.min()), 0.2)
        self.assertLessEqual(float(weights.max()), 1.5)
        self.assertGreater(float(weights[-1]), float(weights[0]))


if __name__ == "__main__":
    unittest.main()
