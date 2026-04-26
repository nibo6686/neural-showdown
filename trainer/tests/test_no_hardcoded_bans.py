import unittest

import numpy as np

from neural.train_bc import compute_awbc_sample_weights


class NoHardcodedBansTest(unittest.TestCase):
    def test_awbc_weighting_does_not_drop_examples(self):
        advantages = np.asarray([-3.0, -1.0, 0.0, 1.0, 3.0], dtype=np.float32)
        weights = compute_awbc_sample_weights(advantages, min_weight=0.1, max_weight=2.0)
        self.assertTrue(np.all(weights > 0.0))

    def test_training_weighting_has_no_type_matchup_inputs(self):
        import inspect
        import neural.train_bc as train_bc

        source = inspect.getsource(train_bc.compute_awbc_sample_weights)
        self.assertNotIn("Ghost", source)
        self.assertNotIn("Normal", source)
        self.assertNotIn("resisted", source)
        self.assertNotIn("super_effective", source)


if __name__ == "__main__":
    unittest.main()
