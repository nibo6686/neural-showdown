import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import torch

from .models.policy_value_mlp import PolicyValueMLP


def torch_load(path: Path, device: torch.device) -> Dict[str, Any]:
    try:
        return torch.load(path, map_location=device, weights_only=False)
    except TypeError:
        return torch.load(path, map_location=device)


def build_model_from_checkpoint(
    checkpoint: Dict[str, Any],
    *,
    default_hidden_sizes: Sequence[int],
    device: torch.device,
) -> PolicyValueMLP:
    hidden_sizes = list(checkpoint.get("hidden_sizes", default_hidden_sizes))
    model = PolicyValueMLP(
        input_size=int(checkpoint["input_size"]),
        hidden_sizes=hidden_sizes,
        action_size=int(checkpoint.get("action_size", 13)),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    setattr(model, "_input_size", int(checkpoint["input_size"]))
    return model


def validate_checkpoint_compatible(
    checkpoint: Dict[str, Any],
    *,
    input_size: int,
    hidden_sizes: Sequence[int],
    action_size: int = 13,
) -> None:
    checkpoint_input = int(checkpoint.get("input_size", -1))
    checkpoint_hidden = list(checkpoint.get("hidden_sizes", []))
    checkpoint_action = int(checkpoint.get("action_size", -1))
    if checkpoint_input != int(input_size):
        raise ValueError(f"Checkpoint input_size={checkpoint_input} is incompatible with dataset input_size={input_size}.")
    if checkpoint_hidden and checkpoint_hidden != list(hidden_sizes):
        raise ValueError(f"Checkpoint hidden_sizes={checkpoint_hidden} is incompatible with config hidden_sizes={list(hidden_sizes)}.")
    if checkpoint_action != int(action_size):
        raise ValueError(f"Checkpoint action_size={checkpoint_action} is incompatible with action_size={action_size}.")


def make_checkpoint_payload(
    *,
    model: PolicyValueMLP,
    optimizer: Optional[torch.optim.Optimizer],
    input_size: int,
    hidden_sizes: Sequence[int],
    action_size: int,
    epoch: int,
    global_step: int,
    training_history: Sequence[Dict[str, Any]],
    config_path: str,
    best_score: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict() if optimizer is not None else None,
        "input_size": int(input_size),
        "hidden_sizes": list(hidden_sizes),
        "action_size": int(action_size),
        "epoch": int(epoch),
        "global_step": int(global_step),
        "training_history": list(training_history),
        "config_path": config_path,
        "best_score": best_score,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if extra:
        payload.update(extra)
    return payload


def save_checkpoint(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)


def copy_checkpoint(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def write_report(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
