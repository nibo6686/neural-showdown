import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
import torch

from .models.vnext_diagnostic import VNextDiagnosticMLP
from .parse_replay_logs import parse_protocol_log
from .train_vnext_diagnostic import (
    build_diagnostic_model,
    load_and_validate_diagnostic_config,
    load_diagnostic_dataset,
)


def _load_model(
    config: Dict[str, Any],
    checkpoint_path: Path,
    device: torch.device,
) -> Tuple[VNextDiagnosticMLP, Dict[str, Any]]:
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Diagnostic checkpoint does not exist: {checkpoint_path}")
    try:
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    except TypeError:
        checkpoint = torch.load(checkpoint_path, map_location=device)
    model = build_diagnostic_model(config).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, checkpoint


def _predict(
    model: VNextDiagnosticMLP,
    states: np.ndarray,
    indices: np.ndarray,
    device: torch.device,
    batch_size: int = 512,
) -> np.ndarray:
    predictions = []
    with torch.no_grad():
        for start in range(0, len(indices), batch_size):
            batch_indices = indices[start : start + batch_size]
            inputs = torch.from_numpy(states[batch_indices].astype(np.float32)).to(device)
            values = model.value_from_embedding(model.encode_states(inputs))
            predictions.append(values.cpu().numpy())
    return np.concatenate(predictions).astype(np.float32)


def _metrics(targets: np.ndarray, predictions: np.ndarray) -> Dict[str, Any]:
    errors = predictions - targets
    mean_target = float(targets.mean())
    return {
        "count": int(len(targets)),
        "target_mean": mean_target,
        "target_wins": int((targets > 0).sum()),
        "target_losses": int((targets < 0).sum()),
        "mse": float(np.mean(errors ** 2)),
        "constant_mean_baseline_mse": float(np.mean((targets - mean_target) ** 2)),
        "constant_zero_baseline_mse": float(np.mean(targets ** 2)),
        "sign_accuracy": float(np.mean((predictions > 0) == (targets > 0))),
        "prediction_mean": float(predictions.mean()),
        "prediction_std": float(predictions.std()),
        "prediction_min": float(predictions.min()),
        "prediction_max": float(predictions.max()),
        "prediction_abs_ge_0_90_rate": float(np.mean(np.abs(predictions) >= 0.90)),
        "prediction_abs_ge_0_95_rate": float(np.mean(np.abs(predictions) >= 0.95)),
        "prediction_abs_ge_0_99_rate": float(np.mean(np.abs(predictions) >= 0.99)),
    }


def _class_metrics(targets: np.ndarray, predictions: np.ndarray) -> Dict[str, Any]:
    result = {}
    for name, mask in (("win", targets > 0), ("loss", targets < 0)):
        class_targets = targets[mask]
        class_predictions = predictions[mask]
        result[name] = {
            "count": int(mask.sum()),
            "mse": float(np.mean((class_predictions - class_targets) ** 2)),
            "sign_accuracy": float(
                np.mean((class_predictions > 0) == (class_targets > 0))
            ),
            "prediction_mean": float(class_predictions.mean()),
            "prediction_std": float(class_predictions.std()),
        }
    return result


def _phase_metrics(
    turns: np.ndarray,
    targets: np.ndarray,
    predictions: np.ndarray,
) -> Dict[str, Any]:
    phases = {
        "early_turn_1_5": turns <= 5,
        "mid_turn_6_15": (turns >= 6) & (turns <= 15),
        "late_turn_16_plus": turns >= 16,
    }
    return {
        name: _metrics(targets[mask], predictions[mask])
        for name, mask in phases.items()
        if mask.any()
    }


def _battle_metrics(
    replay_ids: np.ndarray,
    targets: np.ndarray,
    predictions: np.ndarray,
) -> Dict[str, Any]:
    rows = []
    total_squared_error = float(np.sum((predictions - targets) ** 2))
    for replay_id in sorted(set(replay_ids.tolist())):
        mask = replay_ids == replay_id
        metrics = _metrics(targets[mask], predictions[mask])
        squared_error_sum = float(
            np.sum((predictions[mask] - targets[mask]) ** 2)
        )
        rows.append(
            {
                "replay_id": replay_id,
                **metrics,
                "squared_error_sum": squared_error_sum,
            }
        )
    rows.sort(key=lambda row: row["mse"], reverse=True)
    mse_values = np.asarray([row["mse"] for row in rows], dtype=np.float64)
    error_sorted = sorted(rows, key=lambda row: row["squared_error_sum"], reverse=True)
    return {
        "battle_count": len(rows),
        "median_battle_mse": float(np.median(mse_values)),
        "p90_battle_mse": float(np.quantile(mse_values, 0.90)),
        "max_battle_mse": float(mse_values.max()),
        "top_5_battle_error_share": float(
            sum(row["squared_error_sum"] for row in error_sorted[:5])
            / max(total_squared_error, 1e-12)
        ),
        "top_10_battle_error_share": float(
            sum(row["squared_error_sum"] for row in error_sorted[:10])
            / max(total_squared_error, 1e-12)
        ),
        "worst_10_battles": rows[:10],
    }


def _row_fingerprints(states: np.ndarray, decimals: Optional[int]) -> list[str]:
    values = states if decimals is None else np.round(states.astype(np.float32), decimals)
    return [
        hashlib.blake2b(np.ascontiguousarray(row).tobytes(), digest_size=16).hexdigest()
        for row in values
    ]


def _duplicate_audit(
    states: np.ndarray,
    replay_ids: np.ndarray,
    splits: np.ndarray,
    targets: np.ndarray,
) -> Dict[str, Any]:
    def summarize(fingerprints: list[str]) -> Dict[str, Any]:
        groups: Dict[str, list[int]] = defaultdict(list)
        for index, fingerprint in enumerate(fingerprints):
            groups[fingerprint].append(index)
        duplicates = [indices for indices in groups.values() if len(indices) > 1]
        duplicate_rows = sum(len(indices) for indices in duplicates)
        cross_battle = [
            indices
            for indices in duplicates
            if len(set(replay_ids[indices].tolist())) > 1
        ]
        cross_split = [
            indices
            for indices in duplicates
            if len(set(splits[indices].tolist())) > 1
        ]
        conflicting = [
            indices
            for indices in duplicates
            if len(set(float(value) for value in targets[indices])) > 1
        ]
        return {
            "duplicate_group_count": int(len(duplicates)),
            "rows_in_duplicate_groups": int(duplicate_rows),
            "duplicate_row_rate": float(duplicate_rows / max(1, len(states))),
            "cross_battle_duplicate_group_count": int(len(cross_battle)),
            "cross_split_duplicate_group_count": int(len(cross_split)),
            "conflicting_label_duplicate_group_count": int(len(conflicting)),
        }

    return {
        "exact_float16": summarize(_row_fingerprints(states, None)),
        "rounded_2_decimal_coarse_proxy": summarize(
            _row_fingerprints(states, 2)
        ),
    }


def _label_perspective_audit(
    dataset_path: Path,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    with np.load(dataset_path, allow_pickle=False) as loaded:
        replay_ids = loaded["state_replay_ids"].astype(str)
        sides = loaded["state_sides"].astype(str)
        targets = loaded["state_value_targets"].astype(np.float32)
    manifest_path = Path(str(metadata["source_manifest_path"]))
    if not manifest_path.is_absolute():
        manifest_path = Path.cwd() / manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = {
        str(entry["replay_id"]): entry for entry in manifest.get("entries", [])
    }
    mismatches = []
    unknown_winners = []
    side_label_inconsistencies = []
    both_sides = p1_only = p2_only = 0
    for replay_id in sorted(set(replay_ids.tolist())):
        indices = np.flatnonzero(replay_ids == replay_id)
        battle_sides = set(sides[indices].tolist())
        if battle_sides == {"p1", "p2"}:
            both_sides += 1
        elif battle_sides == {"p1"}:
            p1_only += 1
        elif battle_sides == {"p2"}:
            p2_only += 1
        entry = entries.get(replay_id)
        if entry is None:
            mismatches.append({"replay_id": replay_id, "reason": "missing_manifest_entry"})
            continue
        replay_path = Path(str(entry["path"]))
        trajectory = parse_protocol_log(
            replay_path.read_text(encoding="utf-8", errors="replace").splitlines(),
            replay_id=replay_id,
            format_name="gen9randombattle",
            source_path=str(replay_path),
        )
        winner = trajectory.get("winner_side")
        if winner not in ("p1", "p2"):
            unknown_winners.append(replay_id)
            continue
        for side in battle_sides:
            side_targets = set(
                float(value) for value in targets[indices][sides[indices] == side]
            )
            expected = 1.0 if side == winner else -1.0
            if len(side_targets) != 1:
                side_label_inconsistencies.append(
                    {
                        "replay_id": replay_id,
                        "side": side,
                        "targets": sorted(side_targets),
                    }
                )
            if side_targets != {expected}:
                mismatches.append(
                    {
                        "replay_id": replay_id,
                        "side": side,
                        "winner_side": winner,
                        "expected": expected,
                        "actual": sorted(side_targets),
                    }
                )
    return {
        "battles_checked": int(len(set(replay_ids.tolist()))),
        "both_player_sides_represented": both_sides,
        "p1_only_battles": p1_only,
        "p2_only_battles": p2_only,
        "unknown_winner_battles": len(unknown_winners),
        "side_label_inconsistency_count": len(side_label_inconsistencies),
        "perspective_mismatch_count": len(mismatches),
        "sample_mismatches": mismatches[:10],
        "passed": not mismatches and not unknown_winners and not side_label_inconsistencies,
    }


def run_debug(
    config_path: Path,
    checkpoint_dir: Path,
) -> Dict[str, Any]:
    config = load_and_validate_diagnostic_config(config_path)
    dataset = load_diagnostic_dataset(config)
    dataset_path = Path(config["_resolved_dataset_path"])
    with np.load(dataset_path, allow_pickle=False) as loaded:
        state_sides = loaded["state_sides"].astype(str)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoints = {}
    for checkpoint_name in ("model.best.pt", "model.pt"):
        model, checkpoint = _load_model(
            config, checkpoint_dir / checkpoint_name, device
        )
        checkpoint_report = {
            "epoch": int(checkpoint.get("epoch", -1)),
            "global_step": int(checkpoint.get("global_step", -1)),
            "splits": {},
        }
        for split in ("train", "validation"):
            indices = dataset.split_state_indices[split]
            predictions = _predict(
                model, dataset.state_features, indices, device
            )
            targets = dataset.state_value_targets[indices]
            checkpoint_report["splits"][split] = {
                "overall": _metrics(targets, predictions),
                "by_target_class": _class_metrics(targets, predictions),
                "by_phase": _phase_metrics(
                    dataset.state_turns[indices], targets, predictions
                ),
                "by_battle": _battle_metrics(
                    dataset.state_replay_ids[indices],
                    targets,
                    predictions,
                ),
                "side_counts": {
                    "p1": int((state_sides[indices] == "p1").sum()),
                    "p2": int((state_sides[indices] == "p2").sum()),
                },
            }
        checkpoints[checkpoint_name] = checkpoint_report

    training_cfg = config["training"]
    value_batches = math.ceil(
        len(dataset.split_state_indices["train"])
        / int(training_cfg["value_batch_size"])
    )
    rank_batches = math.ceil(
        len(dataset.split_group_state_indices["train"])
        / int(training_cfg["rank_groups_per_batch"])
    )
    shared_update_audit = {
        "value_batches_per_epoch": value_batches,
        "rank_batches_per_epoch": rank_batches,
        "joint_value_and_rank_steps_per_epoch": min(value_batches, rank_batches),
        "rank_only_steps_per_epoch": max(0, rank_batches - value_batches),
        "rank_only_step_rate": float(
            max(0, rank_batches - value_batches) / max(value_batches, rank_batches)
        ),
        "configured_value_loss_weight": float(
            config["objectives"]["state_value"]["loss_weight"]
        ),
        "configured_rank_loss_weight": float(
            config["objectives"]["action_rank"]["loss_weight"]
        ),
    }
    train_validation_indices = np.concatenate(
        [
            dataset.split_state_indices["train"],
            dataset.split_state_indices["validation"],
        ]
    )
    return {
        "device": device.type,
        "config_path": str(config_path.resolve()),
        "checkpoint_dir": str(checkpoint_dir.resolve()),
        "checkpoints": checkpoints,
        "shared_update_audit": shared_update_audit,
        "duplicate_audit_train_validation": _duplicate_audit(
            dataset.state_features[train_validation_indices],
            dataset.state_replay_ids[train_validation_indices],
            dataset.state_splits[train_validation_indices],
            dataset.state_value_targets[train_validation_indices],
        ),
        "label_perspective_audit": _label_perspective_audit(
            dataset_path, dataset.metadata
        ),
        "test_split_recomputed": False,
    }


def main(argv: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    parser = argparse.ArgumentParser(
        description="Read-only train/validation diagnostics for the vNext value head."
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint-dir", required=True)
    args = parser.parse_args(argv)
    report = run_debug(Path(args.config), Path(args.checkpoint_dir))
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    main()
