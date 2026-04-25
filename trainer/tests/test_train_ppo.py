import unittest

import numpy as np
import torch

from neural.models.policy_value_mlp import PolicyValueMLP
from neural.train_ppo import discounted_terminal_returns, ppo_update


class PpoTrainingTest(unittest.TestCase):
    def test_discounted_terminal_returns_by_player(self):
        records = [
            {"player": "p1"},
            {"player": "p2"},
            {"player": "p1"},
        ]
        discounted_terminal_returns(records, {"p1": 1.0, "p2": -1.0}, 0.5)
        self.assertEqual(records[0]["return"], 0.5)
        self.assertEqual(records[1]["return"], -1.0)
        self.assertEqual(records[2]["return"], 1.0)

    def test_ppo_update_accepts_rollout_shapes(self):
        model = PolicyValueMLP(input_size=5, hidden_sizes=[8])
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        records = []
        for index in range(4):
            mask = np.ones(13, dtype=np.float32)
            records.append(
                {
                    "state": np.full(5, float(index), dtype=np.float32),
                    "mask": mask,
                    "action": index % 13,
                    "old_logprob": -1.0,
                    "value": 0.0,
                    "return": 1.0 if index % 2 == 0 else -1.0,
                }
            )
        report = ppo_update(model, optimizer, records, torch.device("cpu"), epochs=1)
        self.assertEqual(report["records"], 4)
        self.assertEqual(report["epochs"], 1)
        self.assertEqual(len(report["history"]), 1)


if __name__ == "__main__":
    unittest.main()
