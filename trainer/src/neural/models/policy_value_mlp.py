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
