import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

from .checkpoints import make_checkpoint_payload, save_checkpoint
from .live_private_features import FEATURE_VERSION
from .logging_helper import format_summary, print_line_safe
from .models.policy_value_mlp import PolicyValueMLP


DEFAULT_DATASET_PATH = Path("data/value/gen9randombattle_live_private_value_v2.npz")
DEFAULT_CHECKPOINT_PATH = Path("artifacts/checkpoints/gen9randombattle_live_private_value_v2.pt")


def _decode_source_kinds(data: Any, n: int) -> np.ndarray:
    if "source_kinds" in data:
        return data["source_kinds"].astype(str)
    if "source_kind_codes" in data and "source_kind_names" in data:
        names = data["source_kind_names"].astype(str)
        codes = data["source_kind_codes"].astype(np.int64)
        return np.asarray([names[int(code)] if 0 <= int(code) < len(names) else "unknown" for code in codes])
    return np.asarray(["unknown"] * n)


def load_live_private_value_dataset(path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, str, Any, np.ndarray]:
    with np.load(path, allow_pickle=True) as data:
        states = data["states"].astype(np.float32)
        targets = data["value_targets"].astype(np.float32)
        final_results = data["final_results"].astype(np.float32) if "final_results" in data else targets
        source_kinds = _decode_source_kinds(data, len(states))
        missing_private = data["missing_private_state"].astype(np.float32) if "missing_private_state" in data else np.zeros(len(states), dtype=np.float32)
        feature_version = str(data["feature_version"]) if "feature_version" in data else FEATURE_VERSION
        if "tactical_flags" in data and "tactical_flag_names" in data:
            tactical_data = data["tactical_flags"].astype(np.uint8)
            tactical_names = data["tactical_flag_names"].astype(str)
        else:
            tactical_data = data["tactical_json"].astype(str) if "tactical_json" in data else np.asarray(["{}"] * len(states))
            tactical_names = np.asarray([], dtype=str)
    return states, targets, final_results, source_kinds.astype(str), missing_private, feature_version, tactical_data, tactical_names


def _split_indices(n: int, train_split: float) -> Tuple[np.ndarray, np.ndarray]:
    indices = np.arange(n, dtype=np.int64)
    rng = np.random.RandomState(12345)
    rng.shuffle(indices)
    train_size = max(1, int(n * train_split))
    if n > 1 and train_size >= n:
        train_size = n - 1
    return indices[:train_size], indices[train_size:]


def _loader(states: np.ndarray, targets: np.ndarray, final_results: np.ndarray, indices: np.ndarray, batch_size: int, pin_memory: bool, shuffle: bool) -> DataLoader:
    dataset = TensorDataset(
        torch.from_numpy(states[indices]),
        torch.from_numpy(targets[indices]),
        torch.from_numpy(final_results[indices]),
    )
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, pin_memory=pin_memory)


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


def _predict(model: PolicyValueMLP, states: np.ndarray, device: torch.device, batch_size: int) -> np.ndarray:
    model.eval()
    preds = []
    with torch.inference_mode():
        for start in range(0, len(states), batch_size):
            batch = torch.from_numpy(states[start : start + batch_size]).to(device)
            _, values = model(batch)
            preds.append(values.detach().cpu().numpy())
    return np.concatenate(preds).astype(np.float32)


def _constant_baseline_loss(targets: np.ndarray) -> float:
    mean = float(targets.mean()) if len(targets) else 0.0
    return float(np.mean((targets - mean) ** 2)) if len(targets) else 0.0


def _calibration_table(targets: np.ndarray, predictions: np.ndarray, bins: int = 5) -> Dict[str, Any]:
    edges = np.linspace(-1.0, 1.0, bins + 1)
    rows = []
    for start, end in zip(edges[:-1], edges[1:]):
        mask = (predictions >= start) & (predictions <= end if end == edges[-1] else predictions < end)
        if not mask.any():
            rows.append({"range": [float(start), float(end)], "count": 0})
            continue
        rows.append(
            {
                "range": [float(start), float(end)],
                "count": int(mask.sum()),
                "prediction_mean": float(predictions[mask].mean()),
                "target_mean": float(targets[mask].mean()),
                "mse": float(np.mean((predictions[mask] - targets[mask]) ** 2)),
            }
        )
    return {"bins": rows}


def _outcome_metrics(targets: np.ndarray, final_results: np.ndarray, predictions: np.ndarray) -> Dict[str, Dict[str, Any]]:
    report: Dict[str, Dict[str, Any]] = {}
    for name, mask in {"loss": final_results < 0, "tie": final_results == 0, "win": final_results > 0}.items():
        count = int(mask.sum())
        if count == 0:
            report[name] = {"count": 0}
            continue
        bucket_targets = targets[mask]
        bucket_predictions = predictions[mask]
        non_tie = bucket_targets != 0
        sign_accuracy = None
        if non_tie.any():
            sign_accuracy = float(((bucket_predictions[non_tie] > 0) == (bucket_targets[non_tie] > 0)).mean())
        report[name] = {
            "count": count,
            "target_mean": float(bucket_targets.mean()),
            "prediction_mean": float(bucket_predictions.mean()),
            "prediction_std": float(bucket_predictions.std()),
            "mse": float(np.mean((bucket_predictions - bucket_targets) ** 2)),
            "sign_accuracy": sign_accuracy,
        }
    return report


def _source_metrics(
    targets: np.ndarray,
    final_results: np.ndarray,
    predictions: np.ndarray,
    source_kinds: np.ndarray,
    indices: np.ndarray,
) -> Dict[str, Dict[str, Any]]:
    report: Dict[str, Dict[str, Any]] = {}
    for source in sorted(set(source_kinds[indices].tolist())):
        mask = source_kinds[indices] == source
        source_indices = indices[mask]
        if len(source_indices) == 0:
            continue
        source_targets = targets[source_indices]
        source_predictions = predictions[source_indices]
        source_results = final_results[source_indices]
        non_tie = source_results != 0
        sign_accuracy = None
        if non_tie.any():
            sign_accuracy = float(((source_predictions[non_tie] > 0) == (source_results[non_tie] > 0)).mean())
        baseline = _constant_baseline_loss(source_targets)
        loss = float(np.mean((source_predictions - source_targets) ** 2))
        report[source] = {
            "count": int(len(source_indices)),
            "validation_loss": loss,
            "constant_baseline_loss": baseline,
            "improvement_over_baseline_pct": ((baseline - loss) / baseline * 100.0) if baseline > 0 else None,
            "sign_accuracy": sign_accuracy,
            "prediction_mean": float(source_predictions.mean()),
            "target_mean": float(source_targets.mean()),
        }
    return report


def _tactical_slice_metrics(
    targets: np.ndarray,
    predictions: np.ndarray,
    tactical_data: Any,
    tactical_names: np.ndarray,
    indices: np.ndarray,
) -> Dict[str, Dict[str, Any]]:
    import json

    slices = {
        "repeated_failed_move_examples": ("has_repeated_failed_move", "same_move_failed_chain_norm", "last_move_failed"),
        "already_seeded_target_examples": ("target_already_seeded", "opp_active_seeded"),
        "move_healed_target_examples": ("move_healed_target", "recent_healed_target_count_norm", "last_move_healed_target"),
        "own_seeded_examples": ("own_active_seeded",),
        "opponent_substitute_examples": ("opp_active_substitute",),
    }
    flag_columns = {str(name): idx for idx, name in enumerate(tactical_names.tolist())} if len(tactical_names) else {}
    parsed = None
    if not flag_columns:
        parsed = []
        for raw in tactical_data:
            try:
                parsed.append(json.loads(str(raw)))
            except json.JSONDecodeError:
                parsed.append({})
    report: Dict[str, Dict[str, Any]] = {}
    for name, keys in slices.items():
        columns = [flag_columns[key] for key in keys if key in flag_columns]
        if columns:
            selected = np.asarray(
                [
                    idx
                    for idx in indices
                    if any(bool(tactical_data[int(idx), column]) for column in columns)
                ],
                dtype=np.int64,
            )
        else:
            parsed_rows = parsed or []
            selected = np.asarray(
                [
                    idx
                    for idx in indices
                    if 0 <= int(idx) < len(parsed_rows) and any(bool(parsed_rows[int(idx)].get(key)) for key in keys)
                ],
                dtype=np.int64,
            )
        if len(selected) == 0:
            report[name] = {"count": 0}
            continue
        diff = predictions[selected] - targets[selected]
        report[name] = {
            "count": int(len(selected)),
            "mse": float(np.mean(diff ** 2)),
            "target_mean": float(targets[selected].mean()),
            "prediction_mean": float(predictions[selected].mean()),
        }
    return report


def _timestamp_copy(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    stamped = path.with_name(f"{path.stem}.{time.strftime('%Y%m%d-%H%M%S')}{path.suffix}")
    shutil.copy2(path, stamped)
    return str(stamped)


def train_live_private_value_model(
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
) -> Dict[str, Any]:
    states, targets, final_results, source_kinds, missing_private, feature_version, tactical_data, tactical_names = load_live_private_value_dataset(dataset_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pin_memory = device.type == "cuda"
    train_indices, val_indices = _split_indices(len(states), train_split)
    train_loader = _loader(states, targets, final_results, train_indices, batch_size, pin_memory, True)
    val_loader = _loader(states, targets, final_results, val_indices, batch_size, pin_memory, False) if len(val_indices) else None

    model = PolicyValueMLP(input_size=int(states.shape[1]), hidden_sizes=list(hidden_sizes), action_size=13).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    print_line_safe(
        f"train-live-private-value start device={device.type} examples={len(states)} "
        f"train={len(train_indices)} val={len(val_indices)} feature_dim={states.shape[1]} epochs={epochs}"
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
        history.append({"epoch": epoch + 1, "train_loss": train_loss, "val_loss": val_loss, "global_step": global_step})
        print_line_safe(
            f"train-live-private-value epoch={epoch + 1} train_loss={train_loss:.4f}"
            + (f" val_loss={val_loss:.4f}" if val_loss is not None else "")
        )

    predictions = _predict(model, states, device, max(1, batch_size))
    val_predictions = predictions[val_indices] if len(val_indices) else predictions
    val_targets = targets[val_indices] if len(val_indices) else targets
    val_results = final_results[val_indices] if len(val_indices) else final_results
    constant_baseline = _constant_baseline_loss(val_targets)
    validation_loss = float(np.mean((val_predictions - val_targets) ** 2)) if len(val_targets) else None
    improvement = ((constant_baseline - validation_loss) / constant_baseline * 100.0) if validation_loss is not None and constant_baseline > 0 else None

    checkpoint_payload = make_checkpoint_payload(
        model=model,
        optimizer=optimizer,
        input_size=int(states.shape[1]),
        hidden_sizes=list(hidden_sizes),
        action_size=13,
        epoch=len(history),
        global_step=global_step,
        training_history=history,
        config_path="<cli>",
        best_score=-(validation_loss if validation_loss is not None else history[-1]["train_loss"]),
        extra={
            "training_kind": "live_private_value",
            "model_type": "live-private-belief-value",
            "dataset_path": str(dataset_path),
            "feature_version": feature_version,
            "target_space": "p1_final_result_minus1_to_1",
        },
    )
    save_checkpoint(checkpoint_path, checkpoint_payload)
    timestamped_checkpoint = _timestamp_copy(checkpoint_path)

    report = {
        "checkpoint": str(checkpoint_path),
        "timestamped_checkpoint": timestamped_checkpoint,
        "dataset_path": str(dataset_path),
        "num_examples": int(len(states)),
        "feature_version": feature_version,
        "feature_dim": int(states.shape[1]),
        "device": device.type,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "epochs": int(epochs),
        "batch_size": int(batch_size),
        "train_size": int(len(train_indices)),
        "val_size": int(len(val_indices)),
        "missing_private_state_percentage": float(100.0 * missing_private.mean()) if len(missing_private) else 0.0,
        "target_mean": float(targets.mean()),
        "target_std": float(targets.std()),
        "prediction_mean": float(predictions.mean()),
        "prediction_std": float(predictions.std()),
        "train_loss": float(history[-1]["train_loss"]) if history else None,
        "validation_loss": validation_loss,
        "constant_baseline_loss": constant_baseline,
        "improvement_over_baseline_pct": improvement,
        "outcome_metrics": _outcome_metrics(val_targets, val_results, val_predictions),
        "calibration_table": _calibration_table(val_targets, val_predictions),
        "source_specific_validation": _source_metrics(targets, final_results, predictions, source_kinds, val_indices if len(val_indices) else np.arange(len(states))),
        "tactical_slice_metrics": _tactical_slice_metrics(
            targets,
            predictions,
            tactical_data,
            tactical_names,
            val_indices if len(val_indices) else np.arange(len(states)),
        ),
        "training_history": history,
    }
    json_path = checkpoint_path.with_suffix(".train.json")
    md_path = checkpoint_path.with_suffix(".train.md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_format_markdown_report(report), encoding="utf-8")
    timestamped_json = _timestamp_copy(json_path)
    timestamped_md = _timestamp_copy(md_path)
    report["timestamped_reports"] = [path for path in (timestamped_json, timestamped_md) if path]
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print_line_safe(f"train-live-private-value | checkpoint={checkpoint_path}")
    print_line_safe(f"train-live-private-value | report={json_path}")
    print_line_safe(
        format_summary(
            "train-live-private-value",
            {
                "examples": report["num_examples"],
                "feature_dim": report["feature_dim"],
                "train_loss": f"{report['train_loss']:.4f}" if report["train_loss"] is not None else "n/a",
                "val_loss": f"{report['validation_loss']:.4f}" if report["validation_loss"] is not None else "n/a",
                "checkpoint": str(checkpoint_path),
            },
        )
    )
    return report


def _format_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Live Private Value Training Report",
        "",
        f"- Examples: {report['num_examples']}",
        f"- Feature version: {report['feature_version']}",
        f"- Feature dimension: {report['feature_dim']}",
        f"- Device: {report['device']}",
        f"- Missing private state: {report['missing_private_state_percentage']:.1f}%",
        "",
        "## Loss Metrics",
        "",
        f"- Train loss: {report['train_loss']:.6f}",
        f"- Validation loss: {report['validation_loss']:.6f}" if report["validation_loss"] is not None else "- Validation loss: n/a",
        f"- Constant baseline loss: {report['constant_baseline_loss']:.6f}",
    ]
    if report.get("improvement_over_baseline_pct") is not None:
        lines.append(f"- Improvement over baseline: {report['improvement_over_baseline_pct']:.1f}%")
    lines.extend(["", "## Source-Specific Validation", ""])
    for source, details in report.get("source_specific_validation", {}).items():
        improvement = details.get("improvement_over_baseline_pct")
        improvement_text = f"{improvement:.1f}%" if improvement is not None else "n/a"
        sign = details.get("sign_accuracy")
        sign_text = f"{sign:.1%}" if sign is not None else "n/a"
        lines.append(
            f"- {source}: n={details['count']} val_loss={details['validation_loss']:.6f} "
            f"baseline={details['constant_baseline_loss']:.6f} improvement={improvement_text} sign_acc={sign_text}"
        )
    lines.extend(["", "## Tactical Validation Slices", ""])
    for name, details in report.get("tactical_slice_metrics", {}).items():
        if not details.get("count"):
            lines.append(f"- {name}: 0 examples")
            continue
        lines.append(
            f"- {name}: n={details['count']} mse={details['mse']:.6f} "
            f"target={details['target_mean']:.4f} pred={details['prediction_mean']:.4f}"
        )
    lines.extend(["", "## Outcomes", ""])
    for bucket, details in report.get("outcome_metrics", {}).items():
        if not details.get("count"):
            lines.append(f"- {bucket}: 0 examples")
            continue
        sign = details.get("sign_accuracy")
        sign_text = f"{sign:.1%}" if sign is not None else "n/a"
        lines.append(
            f"- {bucket}: n={details['count']} target={details['target_mean']:.4f} "
            f"pred={details['prediction_mean']:.4f} mse={details['mse']:.6f} sign_acc={sign_text}"
        )
    lines.extend(["", f"Checkpoint: `{report['checkpoint']}`", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train value model on live-private-belief features.")
    parser.add_argument("--dataset-path", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--checkpoint-path", default=str(DEFAULT_CHECKPOINT_PATH))
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    args = parser.parse_args()

    train_live_private_value_model(
        dataset_path=Path(args.dataset_path),
        checkpoint_path=Path(args.checkpoint_path),
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
    )


if __name__ == "__main__":
    main()
