import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
import torch

from .build_replay_value_dataset import FEATURE_NAMES as PUBLIC_FEATURE_NAMES
from .checkpoints import torch_load
from .logging_helper import format_summary, print_line_safe
from .models.policy_value_mlp import PolicyValueMLP


DEFAULT_PUBLIC_DATASET = Path("data/value/gen9randombattle_public_replay_value.npz")
DEFAULT_LIVE_DATASET = Path("data/value/gen9randombattle_live_private_value.npz")
DEFAULT_OLD_CHECKPOINT = Path("artifacts/checkpoints/gen9randombattle_replay_value.pt")
DEFAULT_NEW_CHECKPOINT = Path("artifacts/checkpoints/gen9randombattle_live_private_value.pt")
DEFAULT_REPORT_JSON = Path("artifacts/compare/value_model_comparison.json")
DEFAULT_REPORT_MD = Path("artifacts/compare/value_model_comparison.md")


def _checkpoint_state(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    return checkpoint.get("model_state_dict") or checkpoint.get("state_dict") or checkpoint.get("model") or checkpoint


def _load_model(path: Path, *, input_size: Optional[int], device: torch.device) -> Tuple[PolicyValueMLP, Dict[str, Any]]:
    checkpoint = torch_load(path, device)
    state_dict = _checkpoint_state(checkpoint)
    resolved_input_size = int(checkpoint.get("input_size") or input_size or 31)
    hidden_sizes = list(
        checkpoint.get("hidden_sizes")
        or checkpoint.get("model_config", {}).get("hidden_sizes", [])
        or checkpoint.get("config", {}).get("hidden_sizes", [])
        or [128, 128]
    )
    action_size = int(checkpoint.get("action_size", 13))
    model = PolicyValueMLP(input_size=resolved_input_size, hidden_sizes=hidden_sizes, action_size=action_size).to(device)
    model.load_state_dict(state_dict, strict=False)
    model.eval()
    return model, checkpoint


def _predict(model: PolicyValueMLP, states: np.ndarray, device: torch.device, batch_size: int = 512) -> np.ndarray:
    preds = []
    with torch.inference_mode():
        for start in range(0, len(states), batch_size):
            batch = torch.from_numpy(states[start : start + batch_size].astype(np.float32)).to(device)
            _, values = model(batch)
            preds.append(values.detach().cpu().numpy())
    return np.concatenate(preds).astype(np.float32)


def _split_indices(n: int) -> np.ndarray:
    indices = np.arange(n, dtype=np.int64)
    rng = np.random.RandomState(12345)
    rng.shuffle(indices)
    size = max(1, int(n * 0.1))
    return indices[:size]


def _constant_loss(targets: np.ndarray) -> float:
    return float(np.mean((targets - float(targets.mean())) ** 2)) if len(targets) else 0.0


def _calibration(predictions: np.ndarray, targets: np.ndarray) -> Dict[str, Any]:
    bins = []
    edges = np.linspace(-1.0, 1.0, 6)
    for start, end in zip(edges[:-1], edges[1:]):
        mask = (predictions >= start) & (predictions <= end if end == edges[-1] else predictions < end)
        if not mask.any():
            bins.append({"range": [float(start), float(end)], "count": 0})
            continue
        bins.append(
            {
                "range": [float(start), float(end)],
                "count": int(mask.sum()),
                "prediction_mean": float(predictions[mask].mean()),
                "target_mean": float(targets[mask].mean()),
            }
        )
    return {"bins": bins}


def _metrics(predictions: np.ndarray, targets: np.ndarray, final_results: np.ndarray) -> Dict[str, Any]:
    loss = float(np.mean((predictions - targets) ** 2))
    baseline = _constant_loss(targets)
    non_tie = final_results != 0
    sign_accuracy = None
    if non_tie.any():
        sign_accuracy = float(((predictions[non_tie] > 0) == (final_results[non_tie] > 0)).mean())
    return {
        "validation_loss": loss,
        "constant_baseline_loss": baseline,
        "improvement_over_baseline_pct": ((baseline - loss) / baseline * 100.0) if baseline > 0 else None,
        "win_loss_sign_accuracy": sign_accuracy,
        "prediction_distribution": {
            "mean": float(predictions.mean()),
            "std": float(predictions.std()),
            "min": float(predictions.min()),
            "max": float(predictions.max()),
        },
        "prediction_mean_on_wins": float(predictions[final_results > 0].mean()) if (final_results > 0).any() else None,
        "prediction_mean_on_losses": float(predictions[final_results < 0].mean()) if (final_results < 0).any() else None,
        "calibration": _calibration(predictions, targets),
    }


def _load_public_dataset(path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with np.load(path, allow_pickle=True) as data:
        states = data["states"].astype(np.float32)
        targets = data["value_targets"].astype(np.float32)
        final_results = data["final_results"].astype(np.float32) if "final_results" in data else targets
    indices = _split_indices(len(states))
    return states[indices], targets[indices], final_results[indices], np.asarray(["public_replay"] * len(indices))


def _load_live_dataset(path: Path, source_filter: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with np.load(path, allow_pickle=True) as data:
        states = data["states"].astype(np.float32)
        targets = data["value_targets"].astype(np.float32)
        final_results = data["final_results"].astype(np.float32) if "final_results" in data else targets
        source_kinds = data["source_kinds"].astype(str) if "source_kinds" in data else np.asarray(["live_private"] * len(states))
    if source_filter:
        if source_filter == "public_replay":
            mask = np.char.startswith(source_kinds.astype(str), "public_replay")
        else:
            mask = source_kinds == source_filter
        states, targets, final_results, source_kinds = states[mask], targets[mask], final_results[mask], source_kinds[mask]
    indices = _split_indices(len(states))
    return states[indices], targets[indices], final_results[indices], source_kinds[indices]


def _disagreements(
    old_predictions: np.ndarray,
    new_predictions: np.ndarray,
    targets: np.ndarray,
    source_kinds: np.ndarray,
    limit: int = 10,
) -> Sequence[Dict[str, Any]]:
    deltas = np.abs(new_predictions - old_predictions)
    ranked = np.argsort(-deltas)[:limit]
    return [
        {
            "row": int(index),
            "source_kind": str(source_kinds[index]),
            "old_prediction": float(old_predictions[index]),
            "new_prediction": float(new_predictions[index]),
            "target": float(targets[index]),
            "absolute_delta": float(deltas[index]),
        }
        for index in ranked
    ]


def compare_value_models(
    *,
    public_dataset_path: Path = DEFAULT_PUBLIC_DATASET,
    live_dataset_path: Path = DEFAULT_LIVE_DATASET,
    old_checkpoint_path: Path = DEFAULT_OLD_CHECKPOINT,
    new_checkpoint_path: Path = DEFAULT_NEW_CHECKPOINT,
    report_json_path: Path = DEFAULT_REPORT_JSON,
    report_md_path: Path = DEFAULT_REPORT_MD,
) -> Dict[str, Any]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    old_model, old_checkpoint = _load_model(old_checkpoint_path, input_size=len(PUBLIC_FEATURE_NAMES), device=device)
    new_model, new_checkpoint = _load_model(new_checkpoint_path, input_size=None, device=device)

    comparisons: Dict[str, Any] = {}
    disagreement_rows = []

    if live_dataset_path.exists():
        live_states, live_targets, live_results, live_sources = _load_live_dataset(live_dataset_path, "public_replay")
        if len(live_states):
            old_preds = _predict(old_model, live_states[:, : len(PUBLIC_FEATURE_NAMES)], device)
            new_preds = _predict(new_model, live_states, device)
            comparisons["heldout_public_replay_augmented"] = {
                "old_31d": _metrics(old_preds, live_targets, live_results),
                "new_live_private_belief": _metrics(new_preds, live_targets, live_results),
            }
            disagreement_rows.extend(_disagreements(old_preds, new_preds, live_targets, live_sources))
    elif public_dataset_path.exists():
        states, targets, final_results, _ = _load_public_dataset(public_dataset_path)
        old_preds = _predict(old_model, states[:, : len(PUBLIC_FEATURE_NAMES)], device)
        comparisons["heldout_public_replay"] = {"old_31d": _metrics(old_preds, targets, final_results)}

    if live_dataset_path.exists():
        private_states, private_targets, private_results, private_sources = _load_live_dataset(live_dataset_path, "local_trace_private")
        if len(private_states):
            old_private_preds = _predict(old_model, private_states[:, : len(PUBLIC_FEATURE_NAMES)], device)
            new_private_preds = _predict(new_model, private_states, device)
            comparisons["heldout_local_trace_private"] = {
                "old_31d": _metrics(old_private_preds, private_targets, private_results),
                "new_live_private_belief": _metrics(new_private_preds, private_targets, private_results),
            }
            disagreement_rows.extend(_disagreements(old_private_preds, new_private_preds, private_targets, private_sources))

    report = {
        "device": device.type,
        "old_checkpoint": str(old_checkpoint_path),
        "new_checkpoint": str(new_checkpoint_path),
        "old_feature_dim": int(old_checkpoint.get("input_size", len(PUBLIC_FEATURE_NAMES))),
        "new_feature_dim": int(new_checkpoint.get("input_size", 0)),
        "new_feature_version": str(new_checkpoint.get("feature_version", "")),
        "comparisons": comparisons,
        "strong_disagreements": sorted(disagreement_rows, key=lambda row: row["absolute_delta"], reverse=True)[:10],
    }
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.write_text(_format_markdown_report(report), encoding="utf-8")
    print_line_safe(f"compare-value-models | report={report_json_path}")
    print_line_safe(format_summary("compare-value-models", {"sections": len(comparisons), "output": str(report_json_path)}))
    return report


def _metric_line(label: str, metrics: Dict[str, Any]) -> str:
    improvement = metrics.get("improvement_over_baseline_pct")
    improvement_text = f"{improvement:.1f}%" if improvement is not None else "n/a"
    sign = metrics.get("win_loss_sign_accuracy")
    sign_text = f"{sign:.1%}" if sign is not None else "n/a"
    return (
        f"- {label}: val_loss={metrics['validation_loss']:.6f} "
        f"baseline={metrics['constant_baseline_loss']:.6f} improvement={improvement_text} sign_acc={sign_text}"
    )


def _format_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Value Model Comparison",
        "",
        f"- Old checkpoint: `{report['old_checkpoint']}`",
        f"- New checkpoint: `{report['new_checkpoint']}`",
        f"- Old feature dimension: {report['old_feature_dim']}",
        f"- New feature dimension: {report['new_feature_dim']}",
        f"- New feature version: {report['new_feature_version']}",
        "",
    ]
    for section, models in report.get("comparisons", {}).items():
        lines.extend([f"## {section}", ""])
        for name, metrics in models.items():
            lines.append(_metric_line(name, metrics))
        lines.append("")
    if report.get("strong_disagreements"):
        lines.extend(["## Strong Disagreements", ""])
        for row in report["strong_disagreements"][:10]:
            lines.append(
                f"- {row['source_kind']} row={row['row']} old={row['old_prediction']:.3f} "
                f"new={row['new_prediction']:.3f} target={row['target']:.1f} delta={row['absolute_delta']:.3f}"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare 31D replay and live-private-belief value models.")
    parser.add_argument("--public-dataset", default=str(DEFAULT_PUBLIC_DATASET))
    parser.add_argument("--live-dataset", default=str(DEFAULT_LIVE_DATASET))
    parser.add_argument("--old-checkpoint", default=str(DEFAULT_OLD_CHECKPOINT))
    parser.add_argument("--new-checkpoint", default=str(DEFAULT_NEW_CHECKPOINT))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    args = parser.parse_args()
    compare_value_models(
        public_dataset_path=Path(args.public_dataset),
        live_dataset_path=Path(args.live_dataset),
        old_checkpoint_path=Path(args.old_checkpoint),
        new_checkpoint_path=Path(args.new_checkpoint),
        report_json_path=Path(args.report_json),
        report_md_path=Path(args.report_md),
    )


if __name__ == "__main__":
    main()
