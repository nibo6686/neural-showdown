from typing import Sequence

import torch
from torch import nn


class BoundedValueMLP(nn.Module):
    """Value-only MLP with a tanh-bounded scalar output in ``[-1, 1]``.

    Built for the live/sim-core value head that scores one-turn branch states on
    the serving feature distribution. The tanh is baked into ``forward`` so both
    training and inference produce bounded outputs directly.
    """

    def __init__(self, input_size: int, hidden_sizes: Sequence[int] = (256, 256)) -> None:
        super().__init__()
        layers = []
        last_size = input_size
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(last_size, hidden_size))
            layers.append(nn.ReLU())
            last_size = hidden_size
        self.trunk = nn.Sequential(*layers) if layers else nn.Identity()
        self.value_head = nn.Linear(last_size, 1)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        hidden = self.trunk(inputs)
        return torch.tanh(self.value_head(hidden).squeeze(-1))
