import tempfile
import unittest
from pathlib import Path

from neural.analyze_state import analyze_state
from neural.checkpoints import make_checkpoint_payload, save_checkpoint
from neural.models.policy_value_mlp import PolicyValueMLP
from neural.value_features import VALUE_FEATURE_DIM
from test_value_dataset import write_tiny_trace


class AnalyzeStateSmokeTest(unittest.TestCase):
    def test_analyze_state_outputs_value_and_actions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace_path = root / "battle_0.json"
            checkpoint_path = root / "value.pt"
            write_tiny_trace(trace_path)
            model = PolicyValueMLP(input_size=VALUE_FEATURE_DIM, hidden_sizes=[8])
            payload = make_checkpoint_payload(
                model=model,
                optimizer=None,
                input_size=VALUE_FEATURE_DIM,
                hidden_sizes=[8],
                action_size=13,
                epoch=0,
                global_step=0,
                training_history=[],
                config_path="<test>",
                extra={"training_kind": "value"},
            )
            save_checkpoint(checkpoint_path, payload)
            output = analyze_state(trace_path=trace_path, step_index=0, value_checkpoint=checkpoint_path)
            self.assertIn("state value", output)
            self.assertIn("Pikachu", output)
            self.assertIn("top legal actions", output)


if __name__ == "__main__":
    unittest.main()
