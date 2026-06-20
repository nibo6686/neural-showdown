import unittest

import numpy as np

from neural.diagnose_vnext_value_head import (
    _class_metrics,
    _metrics,
    _phase_metrics,
)


class VNextValueHeadDiagnosticTest(unittest.TestCase):
    def test_metrics_include_baselines_and_saturation(self):
        targets = np.asarray([1.0, -1.0, 1.0, -1.0], dtype=np.float32)
        predictions = np.asarray([0.95, -0.5, -0.99, 0.25], dtype=np.float32)
        report = _metrics(targets, predictions)
        self.assertEqual(report["count"], 4)
        self.assertAlmostEqual(report["constant_zero_baseline_mse"], 1.0)
        self.assertEqual(report["sign_accuracy"], 0.5)
        self.assertEqual(report["prediction_abs_ge_0_95_rate"], 0.5)

    def test_class_and_phase_metrics_partition_rows(self):
        targets = np.asarray([1.0, -1.0, 1.0, -1.0], dtype=np.float32)
        predictions = np.asarray([0.5, -0.5, -0.5, 0.5], dtype=np.float32)
        turns = np.asarray([2, 8, 16, 20], dtype=np.int64)
        classes = _class_metrics(targets, predictions)
        phases = _phase_metrics(turns, targets, predictions)
        self.assertEqual(classes["win"]["count"], 2)
        self.assertEqual(classes["loss"]["count"], 2)
        self.assertEqual(phases["early_turn_1_5"]["count"], 1)
        self.assertEqual(phases["mid_turn_6_15"]["count"], 1)
        self.assertEqual(phases["late_turn_16_plus"]["count"], 2)


if __name__ == "__main__":
    unittest.main()
