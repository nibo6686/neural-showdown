import json
import tempfile
import unittest
from pathlib import Path

from neural.action_value_search import LIMITATION_NOTE, evaluate_actions_from_trace
from test_value_dataset import write_tiny_trace


class ActionValueSearchTest(unittest.TestCase):
    def test_trace_interface_returns_action_estimates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "battle_0.json"
            write_tiny_trace(trace_path)
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            estimates = evaluate_actions_from_trace(trace, 0)
            self.assertGreaterEqual(len(estimates), 2)
            chosen = [estimate for estimate in estimates if estimate.visit_count == 1]
            self.assertEqual(len(chosen), 1)
            unvisited = [estimate for estimate in estimates if estimate.visit_count == 0]
            self.assertTrue(any(LIMITATION_NOTE in estimate.note for estimate in unvisited))


if __name__ == "__main__":
    unittest.main()
