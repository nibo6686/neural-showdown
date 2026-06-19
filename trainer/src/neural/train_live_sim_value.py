"""Train a bounded (tanh) value head on the live/sim-core value dataset.

This is a targeted fix for the train/serve skew documented in
``value_model_diagnostics.md``: the model is trained on the SAME live/sim-core
feature distribution it will be scored on, with a bounded output in ``[-1, 1]``.
It does not overwrite any production checkpoint.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

from .live_private_features import FEATURE_DIM, FEATURE_VERSION
from .models.value_mlp import BoundedValueMLP


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_PATH = REPO_ROOT / "data" / "value" / "gen9randombattle_live_sim_value_v1.npz"
DEFAULT_CHECKPOINT_PATH = REPO_ROOT / "artifacts" / "checkpoints" / "gen9randombattle_live_sim_value_v1.pt"
DEFAULT_REPORT_PATH = REPO_ROOT / "artifacts" / "agent_audit" / "live_sim_value_training_report.md"
LABEL_DEFINITION = "discounted_terminal_return(perspective_final_result, turns_to_end, gamma); bounded [-1,1]"


def _split_indices(n: int, train_split: float) -> Tuple[np.ndarray, np.ndarray]:
    indices = np.arange(n, dtype=np.int64)
    rng = np.random.RandomState(12345)
    rng.shuffle(indices)
    train_size = max(1, int(n * train_split))
    if n > 1 and train_size >= n:
        train_size = n - 1
    return indices[:train_size], indices[train_size:]


def _predict(model: BoundedValueMLP, states: np.ndarray, device: torch.device, batch_size: int) -> np.ndarray:
    model.eval()
    preds = []
    with torch.inference_mode():
        for start in range(0, len(states), batch_size):
            batch = torch.from_numpy(states[start : start + batch_size]).to(device)
            preds.append(model(batch).detach().cpu().numpy())
    return np.concatenate(preds).astype(np.float32) if preds else np.zeros(0, dtype=np.float32)


def train(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    checkpoint_path: Path = DEFAULT_CHECKPOINT_PATH,
    hidden_sizes: Sequence[int] = (256, 256),
    epochs: int = 30,
    batch_size: int = 128,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
    train_split: float = 0.9,
) -> Dict[str, Any]:
    with np.load(dataset_path, allow_pickle=True) as data:
        states = data["states"].astype(np.float32)
        targets = data["value_targets"].astype(np.float32)
        finals = data["final_results"].astype(np.float32) if "final_results" in data else targets
        feature_version = str(data["feature_version"]) if "feature_version" in data else FEATURE_VERSION

    if feature_version != FEATURE_VERSION:
        raise ValueError(f"Dataset feature_version={feature_version!r}; expected {FEATURE_VERSION!r}.")
    if states.shape[1] != FEATURE_DIM:
        raise ValueError(f"Dataset feature_dim={states.shape[1]}; expected {FEATURE_DIM}.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pin = device.type == "cuda"
    train_idx, val_idx = _split_indices(len(states), train_split)
    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(states[train_idx]), torch.from_numpy(targets[train_idx])),
        batch_size=batch_size,
        shuffle=True,
        pin_memory=pin,
    )

    model = BoundedValueMLP(input_size=int(states.shape[1]), hidden_sizes=list(hidden_sizes)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    history = []
    for epoch in range(epochs):
        model.train()
        running, total = 0.0, 0
        for batch_inputs, batch_targets in train_loader:
            batch_inputs = batch_inputs.to(device, non_blocking=pin)
            batch_targets = batch_targets.to(device, non_blocking=pin)
            preds = model(batch_inputs)
            loss = F.smooth_l1_loss(preds, batch_targets)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            running += float(loss.item()) * int(batch_targets.size(0))
            total += int(batch_targets.size(0))
        history.append({"epoch": epoch + 1, "train_huber": running / max(1, total)})

    predictions = _predict(model, states, device, max(1, batch_size))
    val_targets = targets[val_idx] if len(val_idx) else targets
    val_preds = predictions[val_idx] if len(val_idx) else predictions
    val_finals = finals[val_idx] if len(val_idx) else finals
    val_mse = float(np.mean((val_preds - val_targets) ** 2)) if len(val_targets) else None
    constant_baseline = float(np.mean((val_targets - val_targets.mean()) ** 2)) if len(val_targets) else None
    non_tie = val_finals != 0
    sign_acc = float(((val_preds[non_tie] > 0) == (val_finals[non_tie] > 0)).mean()) if non_tie.any() else None

    payload = {
        "model_state_dict": model.state_dict(),
        "model_type": "live-sim-bounded-value",
        "feature_version": feature_version,
        "feature_dim": int(states.shape[1]),
        "input_size": int(states.shape[1]),
        "hidden_sizes": list(hidden_sizes),
        "bounded_output": True,
        "output_activation": "tanh",
        "label_definition": LABEL_DEFINITION,
        "dataset_path": str(dataset_path),
        "training_command": "python -m neural.train_live_sim_value",
        "epochs": int(epochs),
        "batch_size": int(batch_size),
        "learning_rate": float(learning_rate),
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "training_history": history,
    }
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, checkpoint_path)

    report = {
        "checkpoint": str(checkpoint_path),
        "dataset_path": str(dataset_path),
        "device": device.type,
        "num_examples": int(len(states)),
        "train_size": int(len(train_idx)),
        "val_size": int(len(val_idx)),
        "feature_version": feature_version,
        "feature_dim": int(states.shape[1]),
        "bounded_output": True,
        "epochs": int(epochs),
        "final_train_huber": float(history[-1]["train_huber"]) if history else None,
        "val_mse": val_mse,
        "constant_baseline_mse": constant_baseline,
        "improvement_over_baseline_pct": (
            (constant_baseline - val_mse) / constant_baseline * 100.0
            if val_mse is not None and constant_baseline and constant_baseline > 0
            else None
        ),
        "val_sign_accuracy": sign_acc,
        "prediction_mean": float(predictions.mean()),
        "prediction_std": float(predictions.std()),
        "prediction_min": float(predictions.min()),
        "prediction_max": float(predictions.max()),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return report


def _format_md(report: Dict[str, Any]) -> str:
    def fmt(x):
        return f"{x:.4f}" if isinstance(x, float) else str(x)

    lines = [
        "# Live/Sim Bounded Value Training Report (Part C)",
        "",
        f"Generated: {report['timestamp']}",
        f"Checkpoint: `{report['checkpoint']}`",
        f"Dataset: `{report['dataset_path']}`",
        "",
        "## Model",
        "",
        "- Type: live-sim-bounded-value (tanh output, MLP)",
        f"- Feature version / dim: {report['feature_version']} / {report['feature_dim']}",
        "- Bounded output: true (tanh, labels in [-1,1])",
        f"- Device: {report['device']}, epochs: {report['epochs']}",
        f"- Examples (train/val): {report['num_examples']} ({report['train_size']}/{report['val_size']})",
        "",
        "## Metrics",
        "",
        f"- Final train Huber: {fmt(report['final_train_huber'])}",
        f"- Validation MSE: {fmt(report['val_mse'])}",
        f"- Constant-baseline MSE: {fmt(report['constant_baseline_mse'])}",
        f"- Improvement over baseline: {fmt(report['improvement_over_baseline_pct'])}%",
        f"- Validation sign accuracy: {fmt(report['val_sign_accuracy'])}",
        f"- Prediction mean/std: {fmt(report['prediction_mean'])} / {fmt(report['prediction_std'])}",
        f"- Prediction min/max: {fmt(report['prediction_min'])} / {fmt(report['prediction_max'])}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a bounded live/sim value head.")
    parser.add_argument("--dataset-path", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--checkpoint-path", type=Path, default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()

    report = train(
        dataset_path=args.dataset_path,
        checkpoint_path=args.checkpoint_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
    )
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(_format_md(report), encoding="utf-8")
    print(json.dumps({"checkpoint": report["checkpoint"], "val_mse": report["val_mse"], "sign_acc": report["val_sign_accuracy"]}))


if __name__ == "__main__":
    main()
