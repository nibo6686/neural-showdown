import argparse
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset, random_split

from .checkpoints import (
    build_model_from_checkpoint,
    make_checkpoint_payload,
    save_checkpoint,
    torch_load,
    validate_checkpoint_compatible,
    write_report,
)
from .config import load_config, resolve_path
from .logging_helper import format_summary, print_line_safe
from .metadata_helper import create_run_metadata
from .models.policy_value_mlp import PolicyValueMLP, masked_logits


def load_shard(path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with np.load(path) as data:
        return data["states"], data["legal_masks"], data["actions"], data["returns"]


def _build_dataloaders(
    states: np.ndarray,
    legal_masks: np.ndarray,
    actions: np.ndarray,
    returns: np.ndarray,
    *,
    train_split: float,
    batch_size: int,
    pin_memory: bool,
) -> Tuple[TensorDataset, TensorDataset, Optional[DataLoader], Optional[DataLoader]]:
    inputs = torch.from_numpy(states)
    masks = torch.from_numpy(legal_masks)
    action_targets = torch.from_numpy(actions)
    return_targets = torch.from_numpy(returns)

    dataset = TensorDataset(inputs, masks, action_targets, return_targets)
    train_size = max(1, int(len(dataset) * train_split))
    val_size = max(0, len(dataset) - train_size)
    generator = torch.Generator().manual_seed(12345)
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size], generator=generator)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, pin_memory=pin_memory)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, pin_memory=pin_memory) if val_size else None
    return train_dataset, val_dataset, train_loader, val_loader


def _score_epoch(epoch_data: Dict[str, Any]) -> float:
    if "val_acc" in epoch_data:
        return float(epoch_data["val_acc"])
    return -float(epoch_data.get("train_loss", 0.0))


def train_behavior_cloning(
    config: Dict[str, Any],
    *,
    epochs_override: Optional[int] = None,
    checkpoint_path_override: Optional[Path] = None,
    shard_path_override: Optional[Path] = None,
) -> Dict[str, Any]:
    config_path_str = config.get("_config_path", "<dict>")
    training_cfg = config["training"]
    dataset_path = shard_path_override or resolve_path(config, config["dataset"]["shard_path"])
    checkpoint_path = checkpoint_path_override or resolve_path(config, training_cfg["checkpoint_path"])
    best_checkpoint_path = resolve_path(
        config,
        training_cfg.get("best_checkpoint_path", str(checkpoint_path.with_suffix(".best.pt"))),
    )
    batch_size = int(training_cfg.get("batch_size", 64))
    epochs = int(epochs_override if epochs_override is not None else training_cfg.get("epochs", 8))
    hidden_sizes = list(training_cfg.get("hidden_sizes", [256, 256]))
    learning_rate = float(training_cfg.get("learning_rate", 1e-3))
    weight_decay = float(training_cfg.get("weight_decay", 1e-4))
    train_split = float(training_cfg.get("train_split", 0.9))
    resume = bool(training_cfg.get("resume", False))
    grad_clip_norm = float(training_cfg.get("grad_clip_norm", 1.0))
    early_stopping_patience = int(training_cfg.get("early_stopping_patience", 0))
    save_timestamped = bool(training_cfg.get("save_timestamped", True))

    states, legal_masks, actions, returns = load_shard(dataset_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pin_memory = device.type == "cuda"
    train_dataset, val_dataset, train_loader, val_loader = _build_dataloaders(
        states,
        legal_masks,
        actions,
        returns,
        train_split=train_split,
        batch_size=batch_size,
        pin_memory=pin_memory,
    )

    model: PolicyValueMLP
    start_epoch = 0
    global_step = 0
    training_history = []
    best_score: Optional[float] = None
    optimizer_state = None
    resumed = False

    if resume and checkpoint_path.exists():
        checkpoint = torch_load(checkpoint_path, device)
        validate_checkpoint_compatible(
            checkpoint,
            input_size=int(states.shape[1]),
            hidden_sizes=hidden_sizes,
            action_size=13,
        )
        model = build_model_from_checkpoint(checkpoint, default_hidden_sizes=hidden_sizes, device=device)
        optimizer_state = checkpoint.get("optimizer_state_dict")
        start_epoch = int(checkpoint.get("epoch", 0))
        global_step = int(checkpoint.get("global_step", 0))
        training_history = list(checkpoint.get("training_history", []))
        best_score = checkpoint.get("best_score")
        resumed = True
    else:
        model = PolicyValueMLP(input_size=int(states.shape[1]), hidden_sizes=hidden_sizes).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    if optimizer_state:
        optimizer.load_state_dict(optimizer_state)

    print_line_safe(
        f"train start profile={config.get('profile', 'full')} device={device.type} "
        f"dataset={len(train_dataset) + len(val_dataset)} train={len(train_dataset)} val={len(val_dataset)} "
        f"batch_size={batch_size} epochs={epochs} resume={resumed} start_epoch={start_epoch}"
    )

    best_without_improvement = 0
    run_history = []
    for local_epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for batch_inputs, batch_masks, batch_actions, batch_returns in train_loader:
            batch_inputs = batch_inputs.to(device, non_blocking=pin_memory)
            batch_masks = batch_masks.to(device, non_blocking=pin_memory)
            batch_actions = batch_actions.to(device, non_blocking=pin_memory)
            batch_returns = batch_returns.to(device, non_blocking=pin_memory)

            logits, values = model(batch_inputs)
            masked = masked_logits(logits, batch_masks)
            policy_loss = F.cross_entropy(masked, batch_actions)
            value_loss = F.mse_loss(values, batch_returns)
            loss = policy_loss + 0.5 * value_loss

            optimizer.zero_grad()
            loss.backward()
            if grad_clip_norm > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip_norm)
            optimizer.step()
            global_step += 1
            running_loss += float(loss.item()) * batch_inputs.size(0)

        completed_epoch = start_epoch + local_epoch + 1
        epoch_loss = running_loss / max(1, len(train_dataset))
        epoch_data: Dict[str, Any] = {
            "epoch": completed_epoch,
            "local_epoch": local_epoch + 1,
            "train_loss": epoch_loss,
            "global_step": global_step,
        }
        print_line_safe(f"epoch={completed_epoch} train_loss={epoch_loss:.4f}")

        if val_loader is not None:
            model.eval()
            correct = 0
            total = 0
            with torch.inference_mode():
                for batch_inputs, batch_masks, batch_actions, _ in val_loader:
                    batch_inputs = batch_inputs.to(device, non_blocking=pin_memory)
                    batch_masks = batch_masks.to(device, non_blocking=pin_memory)
                    batch_actions = batch_actions.to(device, non_blocking=pin_memory)
                    logits, _ = model(batch_inputs)
                    preds = masked_logits(logits, batch_masks).argmax(dim=-1)
                    correct += int((preds == batch_actions).sum().item())
                    total += int(batch_actions.size(0))
            if total:
                val_acc = correct / total
                epoch_data["val_acc"] = val_acc
                print_line_safe(f"epoch={completed_epoch} val_acc={val_acc:.3f}")

        epoch_score = _score_epoch(epoch_data)
        improved = best_score is None or epoch_score > float(best_score)
        if improved:
            best_score = epoch_score
            best_without_improvement = 0
        else:
            best_without_improvement += 1

        training_history.append(epoch_data)
        run_history.append(epoch_data)

        checkpoint_payload = make_checkpoint_payload(
            model=model,
            optimizer=optimizer,
            input_size=int(states.shape[1]),
            hidden_sizes=hidden_sizes,
            action_size=13,
            epoch=completed_epoch,
            global_step=global_step,
            training_history=training_history,
            config_path=str(config_path_str),
            best_score=best_score,
            extra={"training_kind": "behavior_cloning", "dataset_path": str(dataset_path)},
        )
        save_checkpoint(checkpoint_path, checkpoint_payload)
        if improved:
            save_checkpoint(best_checkpoint_path, checkpoint_payload)

        if early_stopping_patience > 0 and best_without_improvement >= early_stopping_patience:
            print_line_safe(f"train early_stop | epoch={completed_epoch} patience={early_stopping_patience}")
            break

    if save_timestamped and checkpoint_path.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        timestamped_path = checkpoint_path.with_name(f"{checkpoint_path.stem}.{stamp}{checkpoint_path.suffix}")
        shutil.copy2(checkpoint_path, timestamped_path)
    else:
        timestamped_path = None

    metadata = create_run_metadata(
        config_path_str,
        config.get("profile", "full"),
        dataset_size=int(len(train_dataset) + len(val_dataset)),
        train_size=int(len(train_dataset)),
        val_size=int(len(val_dataset)),
    )

    report_path = checkpoint_path.with_suffix(".train.json")
    train_report: Dict[str, Any] = {
        "checkpoint": str(checkpoint_path),
        "best_checkpoint": str(best_checkpoint_path),
        "timestamped_checkpoint": str(timestamped_path) if timestamped_path else None,
        "dataset_path": str(dataset_path),
        "dataset_size": int(len(train_dataset) + len(val_dataset)),
        "train_size": int(len(train_dataset)),
        "val_size": int(len(val_dataset)),
        "batch_size": batch_size,
        "epochs_requested": epochs,
        "epochs_completed": len(run_history),
        "start_epoch": start_epoch,
        "end_epoch": start_epoch + len(run_history),
        "global_step": global_step,
        "device": device.type,
        "resumed": resumed,
        "best_score": best_score,
        "training_history": training_history,
        "run_history": run_history,
    }
    train_report.update(metadata)
    write_report(report_path, train_report)

    print_line_safe(f"train | checkpoint={checkpoint_path}")
    print_line_safe(f"train | best_checkpoint={best_checkpoint_path}")
    print_line_safe(f"train | report={report_path}")
    print_line_safe(
        format_summary(
            "train",
            {
                "epochs": len(run_history),
                "device": device.type,
                "checkpoint": str(checkpoint_path),
            },
        )
    )
    return train_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Behavior cloning training for the Gen 9 Random Battles policy.")
    parser.add_argument("--config", required=True, help="Path to the experiment config.")
    args = parser.parse_args()
    config = load_config(args.config)
    train_behavior_cloning(config)


if __name__ == "__main__":
    main()
