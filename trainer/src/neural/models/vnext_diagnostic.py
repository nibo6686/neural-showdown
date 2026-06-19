from typing import Sequence, Tuple

import torch
from torch import nn


def _mlp(input_size: int, hidden_sizes: Sequence[int], dropout: float) -> Tuple[nn.Module, int]:
    layers = []
    last_size = int(input_size)
    for hidden_size in hidden_sizes:
        layers.append(nn.Linear(last_size, int(hidden_size)))
        layers.append(nn.ReLU())
        if dropout > 0:
            layers.append(nn.Dropout(float(dropout)))
        last_size = int(hidden_size)
    return (nn.Sequential(*layers) if layers else nn.Identity()), last_size


class VNextDiagnosticMLP(nn.Module):
    """Small multitask model for frozen v7 state and v5 action features."""

    def __init__(
        self,
        *,
        state_dim: int,
        action_dim: int,
        state_encoder_hidden_sizes: Sequence[int],
        action_encoder_hidden_sizes: Sequence[int],
        rank_head_hidden_sizes: Sequence[int],
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.state_encoder, state_embedding_dim = _mlp(
            state_dim, state_encoder_hidden_sizes, dropout
        )
        self.action_encoder, action_embedding_dim = _mlp(
            action_dim, action_encoder_hidden_sizes, dropout
        )
        self.value_head = nn.Linear(state_embedding_dim, 1)
        rank_trunk, rank_embedding_dim = _mlp(
            state_embedding_dim + action_embedding_dim,
            rank_head_hidden_sizes,
            dropout,
        )
        self.rank_trunk = rank_trunk
        self.rank_head = nn.Linear(rank_embedding_dim, 1)

    def encode_states(self, state_features: torch.Tensor) -> torch.Tensor:
        return self.state_encoder(state_features)

    def value_from_embedding(self, state_embedding: torch.Tensor) -> torch.Tensor:
        return torch.tanh(self.value_head(state_embedding).squeeze(-1))

    def rank_from_embeddings(
        self,
        state_embedding: torch.Tensor,
        action_features: torch.Tensor,
    ) -> torch.Tensor:
        action_embedding = self.action_encoder(action_features)
        combined = torch.cat([state_embedding, action_embedding], dim=-1)
        return self.rank_head(self.rank_trunk(combined)).squeeze(-1)

    def forward(
        self,
        state_features: torch.Tensor,
        action_features: torch.Tensor,
        candidate_state_indices: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        state_embedding = self.encode_states(state_features)
        values = self.value_from_embedding(state_embedding)
        candidate_embeddings = state_embedding[candidate_state_indices.long()]
        rank_scores = self.rank_from_embeddings(candidate_embeddings, action_features)
        return values, rank_scores
