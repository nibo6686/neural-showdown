from typing import Sequence, Tuple

import torch
from torch import nn


def masked_logits(logits: torch.Tensor, legal_mask: torch.Tensor) -> torch.Tensor:
    mask = legal_mask.to(dtype=torch.bool)
    masked = logits.masked_fill(~mask, -1.0e9)
    invalid_rows = mask.sum(dim=-1) == 0
    if invalid_rows.any():
        masked[invalid_rows] = logits[invalid_rows]
    return masked


class PolicyValueMLP(nn.Module):
    """Multi-layer perceptron for policy and value outputs from battle state features.

    This model is input-size agnostic and supports multiple feature domains:

    - 31D public replay features: Event-derived from protocol logs (move/switch/damage/status).
      Used by: build_replay_value_dataset.py, build_replay_policy_dataset.py
      Trained by: train_replay_value.py (separate model checkpoint)

    - 1179D local sim-core features: Full battle state from running Showdown simulator.
      Includes active Pokemon HP, team states, moves revealed, boosts, abilities, stats.
      Used by: build_value_dataset.py (local traces), behavior cloning, PPO
      Trained by: train_value.py (separate model checkpoint)

    The shared trunk architecture allows both domains to benefit from the same hidden
    representations. Model instances are separate by feature dimension (stored in different
    checkpoint files), enabling independent training while preserving transfer learning potential.

    Args:
        input_size: Feature vector dimension. Typically 31 (public replays) or 1179 (sim-core).
        hidden_sizes: Sequence of hidden layer dimensions. Empty tuple = linear model.
        action_size: Number of legal actions. Default 13 for Showdown battles.
    """
    def __init__(self, input_size: int, hidden_sizes: Sequence[int], action_size: int = 13) -> None:
        super().__init__()
        layers = []
        last_size = input_size
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(last_size, hidden_size))
            layers.append(nn.ReLU())
            last_size = hidden_size
        self.trunk = nn.Sequential(*layers) if layers else nn.Identity()
        self.policy_head = nn.Linear(last_size, action_size)
        self.value_head = nn.Linear(last_size, 1)

    def forward(self, inputs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        hidden = self.trunk(inputs)
        logits = self.policy_head(hidden)
        values = self.value_head(hidden).squeeze(-1)
        return logits, values
