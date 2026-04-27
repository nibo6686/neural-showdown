import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F

from .action_features import ACTION_FEATURE_DIM, ACTION_FEATURE_NAMES, ACTION_FEATURE_VERSION
from .checkpoints import save_checkpoint, torch_load
from .logging_helper import format_summary, print_line_safe
from .models.action_ranker import ActionRankerMLP
from .models.policy_value_mlp import PolicyValueMLP


DEFAULT_DATASET_PATH = Path("data/policy/gen9randombattle_action_rank_v2.npz")
DEFAULT_CHECKPOINT_PATH = Path("artifacts/checkpoints/gen9randombattle_action_ranker_v2.pt")
DEFAULT_POLICY_CHECKPOINT = Path("artifacts/checkpoints/gen9randombattle_replay_policy.pt")
DEFAULT_BIAS_REPORT = Path("artifacts/analysis/action_bias_report.md")


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _group_slices(group_ids: np.ndarray) -> List[Tuple[int, int]]:
    slices = []
    start = 0
    while start < len(group_ids):
        end = start + 1
        while end < len(group_ids) and group_ids[end] == group_ids[start]:
            end += 1
        slices.append((start, end))
        start = end
    return slices


def _split_group_indices(n: int, train_split: float) -> Tuple[np.ndarray, np.ndarray]:
    indices = np.arange(n, dtype=np.int64)
    rng = np.random.RandomState(12345)
    rng.shuffle(indices)
    split = max(1, int(n * train_split))
    if split >= n and n > 1:
        split = n - 1
    return indices[:split], indices[split:]


def _load_policy_model(path: Path, device: torch.device) -> Tuple[Optional[PolicyValueMLP], Optional[Dict[str, Any]]]:
    if not path.exists():
        return None, None
    checkpoint = torch_load(path, device)
    input_size = int(checkpoint.get("input_size", 31))
    hidden_sizes = list(checkpoint.get("hidden_sizes", [128, 128]))
    action_size = int(checkpoint.get("action_size", 13))
    state = checkpoint.get("model_state_dict") or checkpoint.get("state_dict") or checkpoint.get("model") or checkpoint
    model = PolicyValueMLP(input_size=input_size, hidden_sizes=hidden_sizes, action_size=action_size).to(device)
    model.load_state_dict(state, strict=False)
    model.eval()
    return model, checkpoint


def _batch_group_loss(
    model: ActionRankerMLP,
    inputs: torch.Tensor,
    labels: torch.Tensor,
    ranges: Sequence[Tuple[int, int]],
) -> torch.Tensor:
    scores = model(inputs)
    losses = []
    for start, end in ranges:
        group_scores = scores[start:end].unsqueeze(0)
        chosen = torch.nonzero(labels[start:end] > 0.5, as_tuple=False)
        if chosen.numel() == 0:
            continue
        losses.append(F.cross_entropy(group_scores, chosen[0:1, 0].long()))
    if not losses:
        return scores.sum() * 0.0
    return torch.stack(losses).mean()


def _score_groups(
    model: ActionRankerMLP,
    features: np.ndarray,
    labels: np.ndarray,
    action_indices: np.ndarray,
    action_kinds: np.ndarray,
    turns: np.ndarray,
    group_slices: Sequence[Tuple[int, int]],
    selected_groups: Sequence[int],
    device: torch.device,
) -> Dict[str, Any]:
    model.eval()
    top1 = top3 = reciprocal = nll = 0.0
    kind_counts: Dict[str, List[int]] = {}
    turn_buckets: Dict[str, List[int]] = {}
    rec_slots = []
    with torch.inference_mode():
        for group_index in selected_groups:
            start, end = group_slices[int(group_index)]
            x = torch.from_numpy(features[start:end].astype(np.float32)).to(device)
            scores = model(x).detach().cpu().numpy()
            group_labels = labels[start:end]
            positives = np.where(group_labels == 1)[0]
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
    return {
        "top1_accuracy": top1 / total,
        "top3_accuracy": top3 / total,
        "mean_reciprocal_rank": reciprocal / total,
        "chosen_action_nll": nll / total,
        "accuracy_by_action_kind": {kind: good / max(1, count) for kind, (good, count) in kind_counts.items()},
        "accuracy_by_turn_bucket": {bucket: good / max(1, count) for bucket, (good, count) in turn_buckets.items()},
        "recommendation_distribution_by_slot": {str(slot): int(count) for slot, count in zip(*np.unique(np.asarray(rec_slots), return_counts=True))} if rec_slots else {},
        "recommendation_move_slot_1_rate": float(np.mean(np.asarray(rec_slots) == 0)) if rec_slots else 0.0,
    }


def _tactical_ranker_slices(
    model: ActionRankerMLP,
    features: np.ndarray,
    labels: np.ndarray,
    group_slices: Sequence[Tuple[int, int]],
    selected_groups: Sequence[int],
    actions: np.ndarray,
    device: torch.device,
) -> Dict[str, Dict[str, Any]]:
    name_to_index = {name: idx for idx, name in enumerate(ACTION_FEATURE_NAMES)}
    slice_defs = {
        "repeated_failed_move_examples": ["move_failed_recently", "move_failed_last_time_used"],
        "already_seeded_target_examples": ["target_already_seeded"],
        "move_healed_target_examples": ["move_healed_target_recently", "target_known_or_possible_ability_absorbs_move_type"],
        "status_setup_protect_redundant_examples": [
            "screen_already_active",
            "side_already_has_stealth_rock",
            "side_already_has_spikes",
            "move_id_flag_protect",
        ],
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
        scored = _score_groups(model, features, labels, np.zeros(len(labels)), np.asarray(["slice"] * len(labels)), np.zeros(len(labels)), group_slices, groups, device)
        report[name] = {"count": int(len(groups)), **scored}
    return report


def _slot1_baseline(labels: np.ndarray, action_indices: np.ndarray, group_slices: Sequence[Tuple[int, int]], selected_groups: Sequence[int]) -> float:
    correct = 0
    total = 0
    for group_index in selected_groups:
        start, end = group_slices[int(group_index)]
        slot1 = np.where(action_indices[start:end] == 0)[0]
        if len(slot1) == 0:
            continue
        chosen = np.where(labels[start:end] == 1)[0]
        if len(chosen) != 1:
            continue
        correct += int(int(slot1[0]) == int(chosen[0]))
        total += 1
    return correct / max(1, total)


def _old_policy_accuracy(
    policy_model: Optional[PolicyValueMLP],
    policy_meta: Optional[Dict[str, Any]],
    states: np.ndarray,
    labels: np.ndarray,
    action_indices: np.ndarray,
    group_slices: Sequence[Tuple[int, int]],
    selected_groups: Sequence[int],
    device: torch.device,
) -> Optional[float]:
    if policy_model is None or policy_meta is None:
        return None
    input_size = int(policy_meta.get("input_size", 31))
    correct = 0
    total = 0
    with torch.inference_mode():
        for group_index in selected_groups:
            start, end = group_slices[int(group_index)]
            state = states[start].astype(np.float32)
            x = torch.from_numpy(state[:input_size]).unsqueeze(0).to(device)
            logits, _ = policy_model(x)
            probs = torch.softmax(logits.squeeze(0), dim=0).detach().cpu().numpy()
            legal_indices = action_indices[start:end]
            legal_scores = np.asarray([probs[index] if 0 <= int(index) < len(probs) else -1.0 for index in legal_indices])
            pred = int(np.argmax(legal_scores))
            chosen = np.where(labels[start:end] == 1)[0]
            if len(chosen) != 1:
                continue
            correct += int(pred == int(chosen[0]))
            total += 1
    return correct / max(1, total)


def _best_metrics_from_history(history: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    best: Dict[str, Any] = {}
    for item in history:
        score = item.get("top1_accuracy")
        if score is None:
            continue
        if not best or float(score) > float(best.get("top1_accuracy", float("-inf"))):
            best = dict(item)
    return best


def _load_resume_checkpoint(
    *,
    path: Optional[Path],
    device: torch.device,
    expected_input_size: int,
) -> Optional[Dict[str, Any]]:
    if path is None:
        return None
    if not path.exists():
        print_line_safe(f"train-action-ranker resume skipped | checkpoint not found: {path}")
        return None
    checkpoint = torch_load(path, device)
    checkpoint_input = int(checkpoint.get("input_size", expected_input_size))
    if checkpoint_input != int(expected_input_size):
        raise ValueError(
            f"Resume checkpoint input_size={checkpoint_input} does not match current input_size={expected_input_size}."
        )
    return checkpoint


def _save_action_ranker_artifacts(
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
    checkpoint_payload = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "input_size": int(input_size),
        "state_dim": int(state_dim),
        "action_dim": int(action_dim),
        "hidden_sizes": list(hidden_sizes),
        "action_feature_version": ACTION_FEATURE_VERSION,
        "model_type": "action-ranker",
        "epoch": int(report.get("cumulative_epochs", 0)),
        "global_step": int(global_step),
        "training_history": list(report.get("training_history", [])),
        "best_validation_metrics": report.get("best_validation_metrics", {}),
        "latest_validation_metrics": report.get("latest_validation_metrics", {}),
        "saved_at": _timestamp(),
    }
    save_checkpoint(checkpoint_path, checkpoint_payload)
    json_path = checkpoint_path.with_suffix(".train.json")
    md_path = checkpoint_path.with_suffix(".train.md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_format_markdown(report), encoding="utf-8")
    DEFAULT_BIAS_REPORT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_BIAS_REPORT.write_text(_format_bias_report(report), encoding="utf-8")


def train_action_ranker(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    checkpoint_path: Path = DEFAULT_CHECKPOINT_PATH,
    policy_checkpoint_path: Path = DEFAULT_POLICY_CHECKPOINT,
    hidden_sizes: Sequence[int] = (256, 128),
    epochs: int = 1,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
    train_split: float = 0.9,
    groups_per_batch: int = 128,
    max_train_groups: Optional[int] = 100000,
    max_val_groups: Optional[int] = 25000,
    resume_checkpoint_path: Optional[Path] = None,
    save_every_epochs: int = 1,
    train_forever: bool = False,
) -> Dict[str, Any]:
    with np.load(dataset_path, allow_pickle=True) as data:
        states = data["state_features"].astype(np.float32)
        actions = data["action_features"].astype(np.float32)
        labels = data["labels"].astype(np.float32)
        group_ids = data["group_ids"].astype(np.int64)
        action_indices = data["action_indices"].astype(np.int64)
        action_kinds = data["action_kinds"].astype(str)
        turns = data["turns"].astype(np.int64)
        state_feature_version = str(data["state_feature_version"]) if "state_feature_version" in data else "unknown"
        action_feature_version = str(data["action_feature_version"]) if "action_feature_version" in data else ACTION_FEATURE_VERSION

    inputs = np.concatenate([states, actions], axis=1).astype(np.float32)
    group_slices = _group_slices(group_ids)
    train_groups, val_groups = _split_group_indices(len(group_slices), train_split)
    if max_train_groups is not None and len(train_groups) > max_train_groups:
        train_groups = train_groups[:max_train_groups]
    if max_val_groups is not None and len(val_groups) > max_val_groups:
        val_groups = val_groups[:max_val_groups]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    resume_checkpoint = _load_resume_checkpoint(
        path=resume_checkpoint_path,
        device=device,
        expected_input_size=int(inputs.shape[1]),
    )
    if resume_checkpoint is not None:
        hidden_sizes = list(resume_checkpoint.get("hidden_sizes", hidden_sizes))
    model = ActionRankerMLP(input_size=inputs.shape[1], hidden_sizes=hidden_sizes).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    history: List[Dict[str, Any]] = []
    start_epoch = 0
    global_step = 0
    best_validation_metrics: Dict[str, Any] = {}
    if resume_checkpoint is not None:
        model.load_state_dict(resume_checkpoint["model_state_dict"], strict=False)
        optimizer_state = resume_checkpoint.get("optimizer_state_dict")
        if optimizer_state:
            try:
                optimizer.load_state_dict(optimizer_state)
            except ValueError as exc:
                print_line_safe(f"train-action-ranker resume warning | optimizer_state_ignored={exc}")
        history = [dict(item) for item in resume_checkpoint.get("training_history", []) if isinstance(item, dict)]
        start_epoch = int(resume_checkpoint.get("epoch", len(history)) or len(history))
        global_step = int(resume_checkpoint.get("global_step", 0) or 0)
        best_validation_metrics = dict(
            resume_checkpoint.get("best_validation_metrics") or _best_metrics_from_history(history)
        )
    rng = np.random.RandomState(222)

    print_line_safe(
        f"train-action-ranker start device={device.type} rows={len(inputs)} decisions={len(group_slices)} "
        f"train_groups={len(train_groups)} val_groups={len(val_groups)} input_dim={inputs.shape[1]} "
        f"start_epoch={start_epoch} epochs={'forever' if train_forever else epochs}"
    )
    latest_metrics: Dict[str, Any] = {}
    interrupted = False
    completed_this_run = 0

    def make_report() -> Dict[str, Any]:
        policy_model, policy_meta = _load_policy_model(policy_checkpoint_path, device)
        final_metrics = latest_metrics or _score_groups(
            model,
            inputs,
            labels,
            action_indices,
            action_kinds,
            turns,
            group_slices,
            val_groups,
            device,
        )
        slot1 = _slot1_baseline(labels.astype(np.int8), action_indices, group_slices, val_groups)
        old_policy = _old_policy_accuracy(
            policy_model,
            policy_meta,
            states,
            labels.astype(np.int8),
            action_indices,
            group_slices,
            val_groups,
            device,
        )
        return {
            "checkpoint": str(checkpoint_path),
            "dataset_path": str(dataset_path),
            "rows": int(len(inputs)),
            "decisions": int(len(group_slices)),
            "state_dim": int(states.shape[1]),
            "action_dim": int(actions.shape[1]),
            "input_dim": int(inputs.shape[1]),
            "action_feature_version": ACTION_FEATURE_VERSION,
            "dataset_state_feature_version": state_feature_version,
            "dataset_action_feature_version": action_feature_version,
            "device": device.type,
            "epochs_requested": int(epochs),
            "epochs_this_run": int(completed_this_run),
            "cumulative_epochs": int(start_epoch + completed_this_run),
            "start_epoch": int(start_epoch),
            "train_forever": bool(train_forever),
            "interrupted": bool(interrupted),
            "hidden_sizes": list(hidden_sizes),
            "train_groups_used": int(len(train_groups)),
            "val_groups_used": int(len(val_groups)),
            "max_train_groups": max_train_groups,
            "max_val_groups": max_val_groups,
            "top1_accuracy": final_metrics["top1_accuracy"],
            "top3_accuracy": final_metrics["top3_accuracy"],
            "mean_reciprocal_rank": final_metrics["mean_reciprocal_rank"],
            "chosen_action_nll": final_metrics["chosen_action_nll"],
            "move_slot_1_baseline_accuracy": slot1,
            "old_policy_top1_accuracy": old_policy,
            "improvement_over_move_slot_1_baseline": final_metrics["top1_accuracy"] - slot1,
            "accuracy_by_action_kind": final_metrics["accuracy_by_action_kind"],
            "accuracy_by_turn_bucket": final_metrics["accuracy_by_turn_bucket"],
            "recommendation_distribution_by_slot": final_metrics["recommendation_distribution_by_slot"],
            "recommendation_move_slot_1_rate": final_metrics["recommendation_move_slot_1_rate"],
            "latest_validation_metrics": final_metrics,
            "tactical_slice_metrics": _tactical_ranker_slices(
                model,
                inputs,
                labels,
                group_slices,
                val_groups,
                actions,
                device,
            ),
            "best_validation_metrics": best_validation_metrics or _best_metrics_from_history(history),
            "training_history": history,
            "global_step": int(global_step),
            "resume_checkpoint": str(resume_checkpoint_path) if resume_checkpoint_path else None,
            "timestamp": _timestamp(),
        }

    try:
        while train_forever or completed_this_run < int(epochs):
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
                batch_y = torch.from_numpy(labels[row_indices]).to(device)
                loss = _batch_group_loss(model, batch_x, batch_y, local_ranges)
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                losses.append(float(loss.item()))
                global_step += 1
            latest_metrics = _score_groups(model, inputs, labels, action_indices, action_kinds, turns, group_slices, val_groups, device)
            epoch_report = {
                "epoch": cumulative_epoch,
                "run_epoch": completed_this_run + 1,
                "train_loss": float(np.mean(losses)) if losses else 0.0,
                **latest_metrics,
            }
            history.append(epoch_report)
            if not best_validation_metrics or latest_metrics["top1_accuracy"] > float(best_validation_metrics.get("top1_accuracy", -1.0)):
                best_validation_metrics = dict(epoch_report)
            completed_this_run += 1
            print_line_safe(
                f"train-action-ranker epoch={cumulative_epoch} loss={epoch_report['train_loss']:.4f} "
                f"top1={latest_metrics['top1_accuracy']:.3f} top3={latest_metrics['top3_accuracy']:.3f} "
                f"mrr={latest_metrics['mean_reciprocal_rank']:.3f}"
            )
            if save_every_epochs > 0 and completed_this_run % int(save_every_epochs) == 0:
                _save_action_ranker_artifacts(
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
        print_line_safe("train-action-ranker interrupted | saving latest checkpoint")

    report = make_report()
    _save_action_ranker_artifacts(
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
            "train-action-ranker",
            {
                "decisions": report["decisions"],
                "cumulative_epochs": report["cumulative_epochs"],
                "top1": f"{report['top1_accuracy']:.3f}",
                "top3": f"{report['top3_accuracy']:.3f}",
                "slot1_baseline": f"{report['move_slot_1_baseline_accuracy']:.3f}",
                "checkpoint": str(checkpoint_path),
            },
        )
    )
    return report


def _format_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Action Ranker Training Report",
        "",
        f"- Rows: {report['rows']}",
        f"- Decisions: {report['decisions']}",
        f"- Input dimension: {report['input_dim']}",
        f"- Cumulative epochs: {report.get('cumulative_epochs', report.get('epochs', 0))}",
        f"- Epochs this run: {report.get('epochs_this_run', report.get('epochs', 0))}",
        f"- Top-1 accuracy: {report['top1_accuracy']:.3f}",
        f"- Top-3 accuracy: {report['top3_accuracy']:.3f}",
        f"- MRR: {report['mean_reciprocal_rank']:.3f}",
        f"- NLL: {report['chosen_action_nll']:.3f}",
        f"- Move-slot-1 baseline: {report['move_slot_1_baseline_accuracy']:.3f}",
        f"- Old policy top-1: {report['old_policy_top1_accuracy'] if report['old_policy_top1_accuracy'] is not None else 'n/a'}",
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
            f"top3={details['top3_accuracy']:.3f} mrr={details['mean_reciprocal_rank']:.3f}"
        )
    lines.extend(["", f"Checkpoint: `{report['checkpoint']}`", ""])
    return "\n".join(lines)


def _format_bias_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Action Bias Report",
        "",
        f"- Model recommendation move slot 1 rate: {report['recommendation_move_slot_1_rate']:.1%}",
        f"- Always-pick-move-1 baseline top-1 accuracy: {report['move_slot_1_baseline_accuracy']:.3f}",
        f"- Old policy model top-1 accuracy: {report['old_policy_top1_accuracy'] if report['old_policy_top1_accuracy'] is not None else 'n/a'}",
        f"- New action ranker top-1 accuracy: {report['top1_accuracy']:.3f}",
        f"- New action ranker top-3 accuracy: {report['top3_accuracy']:.3f}",
        "",
        "## Recommendation Distribution By Slot",
        "",
    ]
    for slot, count in sorted(report.get("recommendation_distribution_by_slot", {}).items(), key=lambda item: int(item[0])):
        lines.append(f"- {slot}: {count}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train grouped action-conditioned legal-action ranker.")
    parser.add_argument("--dataset-path", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--checkpoint-path", default=str(DEFAULT_CHECKPOINT_PATH))
    parser.add_argument("--policy-checkpoint", default=str(DEFAULT_POLICY_CHECKPOINT))
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=128, help="Groups per optimization batch.")
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--max-train-groups", type=int, default=100000)
    parser.add_argument("--max-val-groups", type=int, default=25000)
    parser.add_argument("--resume-checkpoint", default=None)
    parser.add_argument("--save-every-epochs", type=int, default=1)
    parser.add_argument("--train-forever", action="store_true")
    args = parser.parse_args()
    max_train_groups = None if args.max_train_groups is not None and args.max_train_groups <= 0 else args.max_train_groups
    max_val_groups = None if args.max_val_groups is not None and args.max_val_groups <= 0 else args.max_val_groups
    train_action_ranker(
        dataset_path=Path(args.dataset_path),
        checkpoint_path=Path(args.checkpoint_path),
        policy_checkpoint_path=Path(args.policy_checkpoint),
        epochs=args.epochs,
        groups_per_batch=args.batch_size,
        learning_rate=args.learning_rate,
        max_train_groups=max_train_groups,
        max_val_groups=max_val_groups,
        resume_checkpoint_path=Path(args.resume_checkpoint) if args.resume_checkpoint else None,
        save_every_epochs=args.save_every_epochs,
        train_forever=args.train_forever,
    )


if __name__ == "__main__":
    main()
