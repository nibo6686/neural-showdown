import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F

from .action_features import ACTION_FEATURE_DIM, ACTION_FEATURE_NAMES, ACTION_FEATURE_VERSION
from .build_action_value_dataset import DEFAULT_OUTPUT_PATH as DEFAULT_DATASET_PATH
from .checkpoints import save_checkpoint, torch_load
from .live_private_features import FEATURE_VERSION
from .logging_helper import format_summary, print_line_safe
from .models.action_ranker import ActionRankerMLP
from .train_action_ranker import _group_slices, _split_group_indices


DEFAULT_CHECKPOINT_PATH = Path("artifacts/checkpoints/gen9randombattle_action_value_ranker_v2.pt")
DEFAULT_INIT_CHECKPOINT = Path("artifacts/checkpoints/gen9randombattle_action_ranker_v2.pt")


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _load_init_checkpoint(path: Optional[Path], device: torch.device, input_size: int) -> Optional[Dict[str, Any]]:
    if path is None or not path.exists():
        return None
    checkpoint = torch_load(path, device)
    if int(checkpoint.get("input_size", input_size)) != int(input_size):
        print_line_safe(f"train-action-value-ranker init skipped | input_size mismatch checkpoint={path}")
        return None
    return checkpoint


def _load_resume_checkpoint(path: Optional[Path], device: torch.device, input_size: int) -> Optional[Dict[str, Any]]:
    if path is None:
        return None
    if not path.exists():
        print_line_safe(f"train-action-value-ranker resume skipped | checkpoint not found: {path}")
        return None
    checkpoint = torch_load(path, device)
    checkpoint_input = int(checkpoint.get("input_size", input_size))
    if checkpoint_input != int(input_size):
        raise ValueError(
            f"Resume checkpoint input_size={checkpoint_input} does not match current input_size={input_size}."
        )
    return checkpoint


def _batch_advantage_loss(
    model: ActionRankerMLP,
    inputs: torch.Tensor,
    labels: torch.Tensor,
    target_scores: torch.Tensor,
    sample_weights: torch.Tensor,
    rank_directions: torch.Tensor,
    ranges: Sequence[Tuple[int, int]],
    regression_weight: float,
) -> torch.Tensor:
    scores = model(inputs)
    losses = []
    for start, end in ranges:
        group_scores = scores[start:end]
        local_labels = labels[start:end]
        chosen = torch.nonzero(local_labels > 0.5, as_tuple=False)
        if chosen.numel() == 0:
            continue
        chosen_idx = int(chosen[0, 0].item())
        row = start + chosen_idx
        weight = torch.clamp(sample_weights[row], min=0.0)
        direction = int(rank_directions[row].detach().cpu().item())
        if direction > 0:
            rank_loss = F.cross_entropy(group_scores.unsqueeze(0), torch.tensor([chosen_idx], device=inputs.device))
        elif direction < 0 and (end - start) > 1:
            probs = torch.softmax(group_scores, dim=0)
            rank_loss = -torch.log(torch.clamp(1.0 - probs[chosen_idx], min=1e-6))
        else:
            probs = torch.softmax(group_scores, dim=0)
            rank_loss = -torch.log(torch.clamp(probs[chosen_idx], min=1e-6)) * 0.1
        value_loss = F.smooth_l1_loss(group_scores[chosen_idx], target_scores[row])
        losses.append(weight * (rank_loss + float(regression_weight) * value_loss))
    if not losses:
        return scores.sum() * 0.0
    return torch.stack(losses).mean()


def _score_groups(
    model: ActionRankerMLP,
    inputs: np.ndarray,
    labels: np.ndarray,
    advantages: np.ndarray,
    target_scores: np.ndarray,
    action_indices: np.ndarray,
    action_kinds: np.ndarray,
    turns: np.ndarray,
    group_slices: Sequence[Tuple[int, int]],
    selected_groups: Sequence[int],
    device: torch.device,
) -> Dict[str, Any]:
    model.eval()
    top1 = top3 = reciprocal = nll = 0.0
    chosen_scores = []
    positive_scores = []
    negative_scores = []
    positive_count = negative_count = near_zero_count = 0
    kind_counts: Dict[str, List[int]] = {}
    turn_buckets: Dict[str, List[int]] = {}
    rec_slots = []
    with torch.inference_mode():
        for group_index in selected_groups:
            start, end = group_slices[int(group_index)]
            x = torch.from_numpy(inputs[start:end].astype(np.float32)).to(device)
            scores = model(x).detach().cpu().numpy()
            positives = np.where(labels[start:end] == 1)[0]
            if len(positives) != 1:
                continue
            chosen = int(positives[0])
            order = np.argsort(-scores)
            rank = int(np.where(order == chosen)[0][0]) + 1
            probs = torch.softmax(torch.from_numpy(scores.astype(np.float32)), dim=0).numpy()
            top1 += float(order[0] == chosen)
            top3 += float(chosen in set(order[:3]))
            reciprocal += 1.0 / float(rank)
            nll += -float(np.log(max(1e-8, probs[chosen])))
            chosen_score = float(scores[chosen])
            chosen_scores.append(chosen_score)
            chosen_adv = float(advantages[start + chosen])
            if chosen_adv > 0.03:
                positive_scores.append(chosen_score)
                positive_count += 1
            elif chosen_adv < -0.03:
                negative_scores.append(chosen_score)
                negative_count += 1
            else:
                near_zero_count += 1
            rec_slots.append(int(action_indices[start + int(order[0])]))
            kind = str(action_kinds[start + chosen])
            kind_counts.setdefault(kind, [0, 0])
            kind_counts[kind][0] += int(order[0] == chosen)
            kind_counts[kind][1] += 1
            turn = int(turns[start + chosen])
            bucket = "early" if turn <= 5 else "mid" if turn <= 15 else "late"
            turn_buckets.setdefault(bucket, [0, 0])
            turn_buckets[bucket][0] += int(order[0] == chosen)
            turn_buckets[bucket][1] += 1
    total = max(1, len(selected_groups))
    chosen_mask = labels == 1
    target_pred_corr = None
    if int(chosen_mask.sum()) > 1 and chosen_scores:
        selected_chosen_rows = []
        for group_index in selected_groups:
            start, end = group_slices[int(group_index)]
            positives = np.where(labels[start:end] == 1)[0]
            if len(positives) == 1:
                selected_chosen_rows.append(start + int(positives[0]))
        if len(selected_chosen_rows) > 1:
            target_subset = target_scores[np.asarray(selected_chosen_rows, dtype=np.int64)]
            pred_subset = np.asarray(chosen_scores, dtype=np.float32)
            if float(np.std(target_subset)) > 1e-8 and float(np.std(pred_subset)) > 1e-8:
                target_pred_corr = float(np.corrcoef(target_subset, pred_subset)[0, 1])
    return {
        "top1_accuracy": top1 / total,
        "top3_accuracy": top3 / total,
        "mean_reciprocal_rank": reciprocal / total,
        "chosen_action_nll": nll / total,
        "average_predicted_score_positive_delta": float(np.mean(positive_scores)) if positive_scores else None,
        "average_predicted_score_negative_delta": float(np.mean(negative_scores)) if negative_scores else None,
        "positive_delta_chosen_count": int(positive_count),
        "negative_delta_chosen_count": int(negative_count),
        "near_zero_delta_chosen_count": int(near_zero_count),
        "target_score_prediction_correlation": target_pred_corr,
        "accuracy_by_action_kind": {kind: good / max(1, count) for kind, (good, count) in kind_counts.items()},
        "accuracy_by_turn_bucket": {bucket: good / max(1, count) for bucket, (good, count) in turn_buckets.items()},
        "recommendation_distribution_by_slot": {str(slot): int(count) for slot, count in zip(*np.unique(np.asarray(rec_slots), return_counts=True))} if rec_slots else {},
        "recommendation_move_slot_1_rate": float(np.mean(np.asarray(rec_slots) == 0)) if rec_slots else 0.0,
    }


def _tactical_slice_metrics(
    model: ActionRankerMLP,
    inputs: np.ndarray,
    labels: np.ndarray,
    advantages: np.ndarray,
    target_scores: np.ndarray,
    group_slices: Sequence[Tuple[int, int]],
    selected_groups: Sequence[int],
    actions: np.ndarray,
    action_indices: np.ndarray,
    action_kinds: np.ndarray,
    turns: np.ndarray,
    device: torch.device,
) -> Dict[str, Dict[str, Any]]:
    name_to_index = {name: idx for idx, name in enumerate(ACTION_FEATURE_NAMES)}
    slice_defs = {
        "repeated_failed_moves": ["move_failed_recently", "move_failed_last_time_used", "same_move_same_target_failed_before"],
        "move_healed_target": ["move_healed_target_recently", "target_known_or_possible_ability_absorbs_move_type"],
        "ability_punished_moves": [
            "target_known_or_possible_ability_absorbs_move_type",
            "target_known_or_possible_ability_blocks_move_effect",
        ],
        "switch_into_ko_heavy_damage": ["switch_own_hazards_norm", "switch_target_hazard_vulnerability"],
        "setup_into_immediate_death": ["flag_setup", "move_id_flag_swordsdance", "move_id_flag_nastyplot", "move_id_flag_calmmind"],
    }
    report: Dict[str, Dict[str, Any]] = {}
    for name, feature_names in slice_defs.items():
        columns = [name_to_index[item] for item in feature_names if item in name_to_index and name_to_index[item] < actions.shape[1]]
        groups = []
        for group_index in selected_groups:
            start, end = group_slices[int(group_index)]
            if columns and bool((actions[start:end, columns] > 0.5).any()):
                groups.append(int(group_index))
        if not groups:
            report[name] = {"count": 0}
            continue
        scored = _score_groups(
            model,
            inputs,
            labels,
            advantages,
            target_scores,
            action_indices,
            action_kinds,
            turns,
            group_slices,
            groups,
            device,
        )
        report[name] = {"count": int(len(groups)), **scored}
    return report


def _save_artifacts(
    *,
    model: ActionRankerMLP,
    optimizer: torch.optim.Optimizer,
    checkpoint_path: Path,
    report: Dict[str, Any],
    input_size: int,
    state_dim: int,
    action_dim: int,
    hidden_sizes: Sequence[int],
    global_step: int,
) -> None:
    payload = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "input_size": int(input_size),
        "state_dim": int(state_dim),
        "action_dim": int(action_dim),
        "hidden_sizes": list(hidden_sizes),
        "state_feature_version": FEATURE_VERSION,
        "action_feature_version": ACTION_FEATURE_VERSION,
        "model_type": "action-value-ranker",
        "response_method": "action_value_ranker",
        "epoch": int(report.get("cumulative_epochs", 0)),
        "global_step": int(global_step),
        "training_history": list(report.get("training_history", [])),
        "best_validation_metrics": report.get("best_validation_metrics", {}),
        "latest_validation_metrics": report.get("latest_validation_metrics", {}),
        "saved_at": _timestamp(),
    }
    save_checkpoint(checkpoint_path, payload)
    checkpoint_path.with_suffix(".train.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    checkpoint_path.with_suffix(".train.md").write_text(_format_markdown(report), encoding="utf-8")


def train_action_value_ranker(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    checkpoint_path: Path = DEFAULT_CHECKPOINT_PATH,
    init_checkpoint_path: Optional[Path] = DEFAULT_INIT_CHECKPOINT,
    hidden_sizes: Sequence[int] = (256, 128),
    epochs: int = 2,
    learning_rate: float = 5e-4,
    weight_decay: float = 1e-4,
    train_split: float = 0.9,
    groups_per_batch: int = 128,
    max_train_groups: Optional[int] = 100000,
    max_val_groups: Optional[int] = 25000,
    regression_weight: float = 0.25,
    resume_checkpoint_path: Optional[Path] = None,
    save_every_epochs: int = 1,
) -> Dict[str, Any]:
    with np.load(dataset_path, allow_pickle=True) as data:
        states = data["state_features"].astype(np.float32)
        actions = data["action_features"].astype(np.float32)
        labels = data["labels"].astype(np.float32)
        group_ids = data["group_ids"].astype(np.int64)
        advantages = data["advantages"].astype(np.float32)
        target_scores = data["target_scores"].astype(np.float32)
        sample_weights = data["sample_weights"].astype(np.float32)
        rank_directions = data["rank_directions"].astype(np.int64)
        action_indices = data["action_indices"].astype(np.int64)
        action_kinds = data["action_kinds"].astype(str)
        turns = data["turns"].astype(np.int64)
        dataset_state_feature_version = str(data["state_feature_version"]) if "state_feature_version" in data else "unknown"
        dataset_action_feature_version = str(data["action_feature_version"]) if "action_feature_version" in data else ACTION_FEATURE_VERSION

    inputs = np.concatenate([states, actions], axis=1).astype(np.float32)
    group_slices = _group_slices(group_ids)
    train_groups, val_groups = _split_group_indices(len(group_slices), train_split)
    if max_train_groups is not None and len(train_groups) > max_train_groups:
        train_groups = train_groups[:max_train_groups]
    if max_val_groups is not None and len(val_groups) > max_val_groups:
        val_groups = val_groups[:max_val_groups]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    resume_checkpoint = _load_resume_checkpoint(resume_checkpoint_path, device, int(inputs.shape[1]))
    init_checkpoint = None if resume_checkpoint is not None else _load_init_checkpoint(init_checkpoint_path, device, int(inputs.shape[1]))
    if resume_checkpoint is not None:
        hidden_sizes = list(resume_checkpoint.get("hidden_sizes", hidden_sizes))
    if init_checkpoint is not None:
        hidden_sizes = list(init_checkpoint.get("hidden_sizes", hidden_sizes))
    model = ActionRankerMLP(input_size=int(inputs.shape[1]), hidden_sizes=hidden_sizes).to(device)
    if resume_checkpoint is not None:
        model.load_state_dict(resume_checkpoint["model_state_dict"], strict=False)
    elif init_checkpoint is not None:
        model.load_state_dict(init_checkpoint["model_state_dict"], strict=False)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    if resume_checkpoint is not None:
        optimizer_state = resume_checkpoint.get("optimizer_state_dict")
        if optimizer_state:
            try:
                optimizer.load_state_dict(optimizer_state)
            except ValueError as exc:
                print_line_safe(f"train-action-value-ranker resume warning | optimizer_state_ignored={exc}")

    rng = np.random.RandomState(333)
    history: List[Dict[str, Any]] = (
        [dict(item) for item in resume_checkpoint.get("training_history", []) if isinstance(item, dict)]
        if resume_checkpoint is not None
        else []
    )
    start_epoch = int(resume_checkpoint.get("epoch", len(history)) or len(history)) if resume_checkpoint is not None else 0
    best_validation_metrics: Dict[str, Any] = (
        dict(resume_checkpoint.get("best_validation_metrics") or {}) if resume_checkpoint is not None else {}
    )
    latest_metrics: Dict[str, Any] = (
        dict(resume_checkpoint.get("latest_validation_metrics") or {}) if resume_checkpoint is not None else {}
    )
    global_step = int(resume_checkpoint.get("global_step", 0) or 0) if resume_checkpoint is not None else 0
    completed_this_run = 0
    interrupted = False

    print_line_safe(
        f"train-action-value-ranker start device={device.type} rows={len(inputs)} decisions={len(group_slices)} "
        f"train_groups={len(train_groups)} val_groups={len(val_groups)} input_dim={inputs.shape[1]} epochs={epochs} "
        f"start_epoch={start_epoch} init={init_checkpoint_path if init_checkpoint is not None else 'none'} "
        f"resume={resume_checkpoint_path if resume_checkpoint is not None else 'none'}"
    )

    def make_report() -> Dict[str, Any]:
        final_metrics = latest_metrics or _score_groups(
            model,
            inputs,
            labels,
            advantages,
            target_scores,
            action_indices,
            action_kinds,
            turns,
            group_slices,
            val_groups,
            device,
        )
        chosen_mask = labels > 0.5
        chosen_advantages = advantages[chosen_mask]
        return {
            "checkpoint": str(checkpoint_path),
            "dataset_path": str(dataset_path),
            "init_checkpoint": str(init_checkpoint_path) if init_checkpoint is not None else None,
            "rows": int(len(inputs)),
            "decisions": int(len(group_slices)),
            "state_dim": int(states.shape[1]),
            "action_dim": int(actions.shape[1]),
            "input_dim": int(inputs.shape[1]),
            "dataset_state_feature_version": dataset_state_feature_version,
            "dataset_action_feature_version": dataset_action_feature_version,
            "device": device.type,
            "epochs_requested": int(epochs),
            "epochs_this_run": int(completed_this_run),
            "cumulative_epochs": int(start_epoch + completed_this_run),
            "start_epoch": int(start_epoch),
            "interrupted": bool(interrupted),
            "hidden_sizes": list(hidden_sizes),
            "train_groups_used": int(len(train_groups)),
            "val_groups_used": int(len(val_groups)),
            "max_train_groups": max_train_groups,
            "max_val_groups": max_val_groups,
            "regression_weight": float(regression_weight),
            "percent_chosen_actions_with_negative_delta": float(100.0 * (chosen_advantages < -0.03).mean()) if len(chosen_advantages) else 0.0,
            **final_metrics,
            "latest_validation_metrics": final_metrics,
            "tactical_slice_metrics": _tactical_slice_metrics(
                model,
                inputs,
                labels,
                advantages,
                target_scores,
                group_slices,
                val_groups,
                actions,
                action_indices,
                action_kinds,
                turns,
                device,
            ),
            "best_validation_metrics": best_validation_metrics,
            "training_history": history,
            "global_step": int(global_step),
            "resume_checkpoint": str(resume_checkpoint_path) if resume_checkpoint_path else None,
            "timestamp": _timestamp(),
        }

    try:
        for epoch in range(epochs):
            cumulative_epoch = start_epoch + completed_this_run + 1
            model.train()
            order = train_groups.copy()
            rng.shuffle(order)
            losses = []
            for batch_start in range(0, len(order), groups_per_batch):
                batch_groups = order[batch_start : batch_start + groups_per_batch]
                starts_ends = [group_slices[int(group)] for group in batch_groups]
                row_parts = [np.arange(start, end, dtype=np.int64) for start, end in starts_ends]
                row_indices = np.concatenate(row_parts) if row_parts else np.asarray([], dtype=np.int64)
                local_ranges = []
                cursor = 0
                for part in row_parts:
                    local_ranges.append((cursor, cursor + len(part)))
                    cursor += len(part)
                batch_x = torch.from_numpy(inputs[row_indices]).to(device)
                batch_labels = torch.from_numpy(labels[row_indices]).to(device)
                batch_targets = torch.from_numpy(target_scores[row_indices]).to(device)
                batch_weights = torch.from_numpy(sample_weights[row_indices]).to(device)
                batch_directions = torch.from_numpy(rank_directions[row_indices]).to(device)
                loss = _batch_advantage_loss(
                    model,
                    batch_x,
                    batch_labels,
                    batch_targets,
                    batch_weights,
                    batch_directions,
                    local_ranges,
                    regression_weight,
                )
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                losses.append(float(loss.item()))
                global_step += 1
            latest_metrics = _score_groups(
                model,
                inputs,
                labels,
                advantages,
                target_scores,
                action_indices,
                action_kinds,
                turns,
                group_slices,
                val_groups,
                device,
            )
            epoch_report = {
                "epoch": cumulative_epoch,
                "run_epoch": completed_this_run + 1,
                "train_loss": float(np.mean(losses)) if losses else 0.0,
                **latest_metrics,
            }
            history.append(epoch_report)
            if not best_validation_metrics:
                best_validation_metrics = dict(epoch_report)
            else:
                best_gap = float(best_validation_metrics.get("average_predicted_score_positive_delta") or 0.0) - float(
                    best_validation_metrics.get("average_predicted_score_negative_delta") or 0.0
                )
                gap = float((latest_metrics.get("average_predicted_score_positive_delta") or 0.0) - (latest_metrics.get("average_predicted_score_negative_delta") or 0.0))
                if gap > best_gap:
                    best_validation_metrics = dict(epoch_report)
            completed_this_run += 1
            print_line_safe(
                f"train-action-value-ranker epoch={cumulative_epoch} loss={epoch_report['train_loss']:.4f} "
                f"top1={latest_metrics['top1_accuracy']:.3f} top3={latest_metrics['top3_accuracy']:.3f} "
                f"pos_score={latest_metrics.get('average_predicted_score_positive_delta')} "
                f"neg_score={latest_metrics.get('average_predicted_score_negative_delta')}"
            )
            if save_every_epochs > 0 and completed_this_run % int(save_every_epochs) == 0:
                _save_artifacts(
                    model=model,
                    optimizer=optimizer,
                    checkpoint_path=checkpoint_path,
                    report=make_report(),
                    input_size=int(inputs.shape[1]),
                    state_dim=int(states.shape[1]),
                    action_dim=int(actions.shape[1]),
                    hidden_sizes=hidden_sizes,
                    global_step=global_step,
                )
    except KeyboardInterrupt:
        interrupted = True
        print_line_safe("train-action-value-ranker interrupted | saving latest checkpoint")

    report = make_report()
    _save_artifacts(
        model=model,
        optimizer=optimizer,
        checkpoint_path=checkpoint_path,
        report=report,
        input_size=int(inputs.shape[1]),
        state_dim=int(states.shape[1]),
        action_dim=int(actions.shape[1]),
        hidden_sizes=hidden_sizes,
        global_step=global_step,
    )
    print_line_safe(
        format_summary(
            "train-action-value-ranker",
            {
                "decisions": report["decisions"],
                "top1": f"{report['top1_accuracy']:.3f}",
                "top3": f"{report['top3_accuracy']:.3f}",
                "checkpoint": str(checkpoint_path),
            },
        )
    )
    return report


def _format_markdown(report: Dict[str, Any]) -> str:
    pos = report.get("average_predicted_score_positive_delta")
    neg = report.get("average_predicted_score_negative_delta")
    lines = [
        "# Action Value Ranker Training Report",
        "",
        f"- Rows: {report['rows']}",
        f"- Decisions: {report['decisions']}",
        f"- Input dimension: {report['input_dim']}",
        f"- Epochs: {report['cumulative_epochs']}",
        f"- Top-1 imitation accuracy: {report['top1_accuracy']:.3f}",
        f"- Top-3 imitation accuracy: {report['top3_accuracy']:.3f}",
        f"- Positive-delta average score: {pos:.4f}" if pos is not None else "- Positive-delta average score: n/a",
        f"- Negative-delta average score: {neg:.4f}" if neg is not None else "- Negative-delta average score: n/a",
        f"- Negative value-delta chosen actions: {report['percent_chosen_actions_with_negative_delta']:.1f}%",
        "",
        "## Tactical Validation Slices",
        "",
    ]
    for name, details in report.get("tactical_slice_metrics", {}).items():
        if not details.get("count"):
            lines.append(f"- {name}: 0 groups")
            continue
        lines.append(
            f"- {name}: n={details['count']} top1={details['top1_accuracy']:.3f} "
            f"top3={details['top3_accuracy']:.3f} pos_score={details.get('average_predicted_score_positive_delta')} "
            f"neg_score={details.get('average_predicted_score_negative_delta')}"
        )
    lines.extend(["", f"Checkpoint: `{report['checkpoint']}`", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train an advantage/value-delta action ranker.")
    parser.add_argument("--dataset-path", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--checkpoint-path", default=str(DEFAULT_CHECKPOINT_PATH))
    parser.add_argument("--init-checkpoint", default=str(DEFAULT_INIT_CHECKPOINT))
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=5e-4)
    parser.add_argument("--max-train-groups", type=int, default=100000)
    parser.add_argument("--max-val-groups", type=int, default=25000)
    parser.add_argument("--regression-weight", type=float, default=0.25)
    parser.add_argument("--resume-checkpoint", default=None)
    parser.add_argument("--save-every-epochs", type=int, default=1)
    args = parser.parse_args()
    train_action_value_ranker(
        dataset_path=Path(args.dataset_path),
        checkpoint_path=Path(args.checkpoint_path),
        init_checkpoint_path=Path(args.init_checkpoint) if args.init_checkpoint else None,
        epochs=args.epochs,
        groups_per_batch=args.batch_size,
        learning_rate=args.learning_rate,
        max_train_groups=None if args.max_train_groups <= 0 else args.max_train_groups,
        max_val_groups=None if args.max_val_groups <= 0 else args.max_val_groups,
        regression_weight=args.regression_weight,
        resume_checkpoint_path=Path(args.resume_checkpoint) if args.resume_checkpoint else None,
        save_every_epochs=args.save_every_epochs,
    )


if __name__ == "__main__":
    main()
