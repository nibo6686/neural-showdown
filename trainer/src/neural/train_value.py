import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset, random_split

from .checkpoints import make_checkpoint_payload, save_checkpoint
from .config import load_config, resolve_path
from .logging_helper import format_summary, print_line_safe
from .models.policy_value_mlp import PolicyValueMLP


DEFAULT_DATASET_PATH = Path("data/value/gen9randombattle_value.npz")
DEFAULT_CHECKPOINT_PATH = Path("artifacts/checkpoints/gen9randombattle_value.pt")


def load_value_dataset(path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    with np.load(path) as data:
        states = data["states"].astype(np.float32)
        targets = data["value_targets"].astype(np.float32)
        final_results = data["final_results"].astype(np.float32) if "final_results" in data else targets
    return states, targets, final_results


def _build_dataloaders(
    states: np.ndarray,
    targets: np.ndarray,
    final_results: np.ndarray,
    *,
    train_split: float,
    batch_size: int,
    pin_memory: bool,
) -> Tuple[TensorDataset, TensorDataset, DataLoader, Optional[DataLoader]]:
    dataset = TensorDataset(torch.from_numpy(states), torch.from_numpy(targets), torch.from_numpy(final_results))
    train_size = max(1, int(len(dataset) * train_split))
    val_size = max(0, len(dataset) - train_size)
    if len(dataset) > 1 and val_size == 0:
        train_size = len(dataset) - 1
        val_size = 1
    generator = torch.Generator().manual_seed(12345)
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size], generator=generator)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, pin_memory=pin_memory)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, pin_memory=pin_memory) if val_size else None
    return train_dataset, val_dataset, train_loader, val_loader


def _evaluate_loss(model: PolicyValueMLP, loader: Optional[DataLoader], device: torch.device, pin_memory: bool) -> Optional[float]:
    if loader is None:
        return None
    model.eval()
    total_loss = 0.0
    total = 0
    with torch.inference_mode():
        for batch_inputs, batch_targets, _ in loader:
            batch_inputs = batch_inputs.to(device, non_blocking=pin_memory)
            batch_targets = batch_targets.to(device, non_blocking=pin_memory)
            _, values = model(batch_inputs)
            loss = F.mse_loss(values, batch_targets, reduction="sum")
            total_loss += float(loss.item())
            total += int(batch_targets.size(0))
    return total_loss / max(1, total)


def _predict_all(model: PolicyValueMLP, states: np.ndarray, device: torch.device, batch_size: int) -> np.ndarray:
    model.eval()
    preds = []
    with torch.inference_mode():
        for start in range(0, len(states), batch_size):
            batch = torch.from_numpy(states[start : start + batch_size]).to(device)
            _, values = model(batch)
            preds.append(values.cpu().numpy())
    return np.concatenate(preds, axis=0).astype(np.float32)


def _calibration_by_outcome(targets: np.ndarray, final_results: np.ndarray, predictions: np.ndarray) -> Dict[str, Dict[str, float]]:
    buckets = {
        "loss": final_results < 0,
        "tie": final_results == 0,
        "win": final_results > 0,
    }
    report: Dict[str, Dict[str, float]] = {}
    for name, mask in buckets.items():
        count = int(mask.sum())
        if count == 0:
            report[name] = {"count": 0}
            continue
        bucket_targets = targets[mask]
        bucket_predictions = predictions[mask]
        report[name] = {
            "count": count,
            "target_mean": float(bucket_targets.mean()),
            "prediction_mean": float(bucket_predictions.mean()),
            "mse": float(np.mean((bucket_predictions - bucket_targets) ** 2)),
        }
    return report


def train_value_model(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    checkpoint_path: Path = DEFAULT_CHECKPOINT_PATH,
    hidden_sizes: Sequence[int] = (256, 256),
    epochs: int = 8,
    batch_size: int = 128,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
    train_split: float = 0.9,
    grad_clip_norm: float = 1.0,
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    states, targets, final_results = load_value_dataset(dataset_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pin_memory = device.type == "cuda"
    train_dataset, val_dataset, train_loader, val_loader = _build_dataloaders(
        states,
        targets,
        final_results,
        train_split=train_split,
        batch_size=batch_size,
        pin_memory=pin_memory,
    )
    model = PolicyValueMLP(input_size=int(states.shape[1]), hidden_sizes=list(hidden_sizes)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    print_line_safe(
        f"train-value start device={device.type} examples={len(states)} train={len(train_dataset)} "
        f"val={len(val_dataset)} feature_dim={states.shape[1]} epochs={epochs}"
    )

    history = []
    global_step = 0
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        total = 0
        for batch_inputs, batch_targets, _ in train_loader:
            batch_inputs = batch_inputs.to(device, non_blocking=pin_memory)
            batch_targets = batch_targets.to(device, non_blocking=pin_memory)
            _, values = model(batch_inputs)
            loss = F.mse_loss(values, batch_targets)
            optimizer.zero_grad()
            loss.backward()
            if grad_clip_norm > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip_norm)
            optimizer.step()
            running_loss += float(loss.item()) * int(batch_targets.size(0))
            total += int(batch_targets.size(0))
            global_step += 1

        train_loss = running_loss / max(1, total)
        val_loss = _evaluate_loss(model, val_loader, device, pin_memory)
        epoch_report = {
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "global_step": global_step,
        }
        history.append(epoch_report)
        val_text = f" val_loss={val_loss:.4f}" if val_loss is not None else ""
        print_line_safe(f"train-value epoch={epoch + 1} train_loss={train_loss:.4f}{val_text}")

    predictions = _predict_all(model, states, device, batch_size=max(1, batch_size))
    calibration = _calibration_by_outcome(targets, final_results, predictions)
    checkpoint_payload = make_checkpoint_payload(
        model=model,
        optimizer=optimizer,
        input_size=int(states.shape[1]),
        hidden_sizes=list(hidden_sizes),
        action_size=13,
        epoch=len(history),
        global_step=global_step,
        training_history=history,
        config_path=str(config_path or "<cli>"),
        best_score=-(history[-1]["val_loss"] if history and history[-1]["val_loss"] is not None else history[-1]["train_loss"]),
        extra={
            "training_kind": "value",
            "dataset_path": str(dataset_path),
            "target_space": "p1_final_result_minus1_to_1",
        },
    )
    save_checkpoint(checkpoint_path, checkpoint_payload)

    report = {
        "checkpoint": str(checkpoint_path),
        "dataset_path": str(dataset_path),
        "num_examples": int(len(states)),
        "feature_dim": int(states.shape[1]),
        "device": device.type,
        "config_path": str(config_path or "<cli>"),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "epochs": int(epochs),
        "batch_size": int(batch_size),
        "train_size": int(len(train_dataset)),
        "val_size": int(len(val_dataset)),
        "target_mean": float(targets.mean()),
        "target_std": float(targets.std()),
        "prediction_mean": float(predictions.mean()),
        "prediction_std": float(predictions.std()),
        "train_loss": float(history[-1]["train_loss"]) if history else None,
        "validation_loss": history[-1]["val_loss"] if history else None,
        "calibration_by_outcome": calibration,
        "training_history": history,
    }
    json_path = checkpoint_path.with_suffix(".train.json")
    md_path = checkpoint_path.with_suffix(".train.md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_format_markdown_report(report), encoding="utf-8")

    print_line_safe(f"train-value | checkpoint={checkpoint_path}")
    print_line_safe(f"train-value | report={json_path}")
    print_line_safe(
        format_summary(
            "train-value",
            {
                "examples": report["num_examples"],
                "train_loss": f"{report['train_loss']:.4f}" if report["train_loss"] is not None else "n/a",
                "val_loss": f"{report['validation_loss']:.4f}" if report["validation_loss"] is not None else "n/a",
                "checkpoint": str(checkpoint_path),
            },
        )
    )
    return report


def _format_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Value Training Report",
        "",
        f"- Examples: {report['num_examples']}",
        f"- Feature dimension: {report['feature_dim']}",
        f"- Device: {report['device']}",
        f"- Train loss: {report['train_loss']:.6f}",
        f"- Validation loss: {report['validation_loss']:.6f}" if report["validation_loss"] is not None else "- Validation loss: n/a",
        f"- Target mean/std: {report['target_mean']:.4f} / {report['target_std']:.4f}",
        f"- Prediction mean/std: {report['prediction_mean']:.4f} / {report['prediction_std']:.4f}",
        "",
        "## Calibration By Outcome",
        "",
    ]
    for bucket, details in report.get("calibration_by_outcome", {}).items():
        if not details.get("count"):
            lines.append(f"- {bucket}: 0 examples")
            continue
        lines.append(
            f"- {bucket}: n={details['count']} target={details['target_mean']:.4f} "
            f"pred={details['prediction_mean']:.4f} mse={details['mse']:.6f}"
        )
    lines.extend(["", f"Checkpoint: `{report['checkpoint']}`", ""])
    return "\n".join(lines)


def _resolve_from_config(config_path: Optional[str], dataset_path: Optional[str], checkpoint_path: Optional[str]) -> Tuple[Path, Path, Dict[str, Any], Optional[str]]:
    if not config_path:
        return (
            Path(dataset_path or DEFAULT_DATASET_PATH),
            Path(checkpoint_path or DEFAULT_CHECKPOINT_PATH),
            {},
            None,
        )
    config = load_config(config_path)
    value_cfg = config.get("value_training", {})
    training_cfg = config.get("training", {})
    resolved_dataset = Path(dataset_path) if dataset_path else resolve_path(config, value_cfg.get("dataset_path", "../data/value/gen9randombattle_value.npz"))
    resolved_checkpoint = Path(checkpoint_path) if checkpoint_path else resolve_path(config, value_cfg.get("checkpoint_path", "../artifacts/checkpoints/gen9randombattle_value.pt"))
    merged = dict(training_cfg)
    merged.update(value_cfg)
    return resolved_dataset, resolved_checkpoint, merged, config.get("_config_path")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the value head on battle-state outcome targets.")
    parser.add_argument("--dataset-path", default=None, help="Value dataset NPZ path.")
    parser.add_argument("--checkpoint-path", default=None, help="Output checkpoint path.")
    parser.add_argument("--config", default=None, help="Optional config with value_training settings.")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    args = parser.parse_args()

    dataset_path, checkpoint_path, cfg, resolved_config_path = _resolve_from_config(
        args.config,
        args.dataset_path,
        args.checkpoint_path,
    )
    train_value_model(
        dataset_path=dataset_path,
        checkpoint_path=checkpoint_path,
        hidden_sizes=list(cfg.get("hidden_sizes", [256, 256])),
        epochs=int(args.epochs if args.epochs is not None else cfg.get("epochs", 8)),
        batch_size=int(args.batch_size if args.batch_size is not None else cfg.get("batch_size", 128)),
        learning_rate=float(args.learning_rate if args.learning_rate is not None else cfg.get("learning_rate", 1e-3)),
        weight_decay=float(cfg.get("weight_decay", 1e-4)),
        train_split=float(cfg.get("train_split", 0.9)),
        grad_clip_norm=float(cfg.get("grad_clip_norm", 1.0)),
        config_path=resolved_config_path,
    )


if __name__ == "__main__":
    main()
