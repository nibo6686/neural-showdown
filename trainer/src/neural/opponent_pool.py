import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class OpponentSpec:
    name: str
    type: str
    weight: float = 1.0
    checkpoint: Optional[str] = None


class OpponentPool:
    def __init__(self, opponents: Sequence[OpponentSpec], *, rng: Optional[random.Random] = None) -> None:
        usable = [opponent for opponent in opponents if opponent.weight > 0]
        if not usable:
            raise ValueError("OpponentPool requires at least one opponent with positive weight.")
        self.opponents = list(usable)
        self.rng = rng or random.Random()

    @classmethod
    def from_config(cls, config: Dict[str, Any], *, rng: Optional[random.Random] = None) -> "OpponentPool":
        pool_cfg = config.get("opponents", {}).get("pool")
        if not pool_cfg:
            pool_cfg = [
                {"name": "random", "type": "random", "weight": 0.5},
                {"name": "heuristic", "type": "heuristic", "weight": 0.5},
            ]
        return cls([opponent_spec_from_dict(item) for item in pool_cfg], rng=rng)

    def sample(self) -> OpponentSpec:
        total = sum(opponent.weight for opponent in self.opponents)
        pick = self.rng.random() * total
        cursor = 0.0
        for opponent in self.opponents:
            cursor += opponent.weight
            if pick <= cursor:
                return opponent
        return self.opponents[-1]


def opponent_spec_from_dict(payload: Dict[str, Any]) -> OpponentSpec:
    opponent_type = str(payload.get("type", payload.get("controller", "random")))
    checkpoint = payload.get("checkpoint")
    return OpponentSpec(
        name=str(payload.get("name", opponent_type)),
        type=opponent_type,
        weight=float(payload.get("weight", 1.0)),
        checkpoint=str(checkpoint) if checkpoint else None,
    )


def filter_available_checkpoint_opponents(opponents: Sequence[OpponentSpec], *, base_dir: Optional[Path] = None) -> List[OpponentSpec]:
    available: List[OpponentSpec] = []
    for opponent in opponents:
        if opponent.type != "checkpoint":
            available.append(opponent)
            continue
        if not opponent.checkpoint:
            continue
        checkpoint_path = Path(opponent.checkpoint)
        if base_dir is not None and not checkpoint_path.is_absolute():
            checkpoint_path = base_dir / checkpoint_path
        if checkpoint_path.exists():
            available.append(opponent)
    return available
