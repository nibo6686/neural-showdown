from typing import Sequence

import torch
from torch import nn


class ActionRankerMLP(nn.Module):
    def __init__(self, input_size: int, hidden_sizes: Sequence[int] = (256, 128)) -> None:
        super().__init__()
        layers = []
        last_size = int(input_size)
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(last_size, int(hidden_size)))
            layers.append(nn.ReLU())
            last_size = int(hidden_size)
        layers.append(nn.Linear(last_size, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.net(inputs).squeeze(-1)
