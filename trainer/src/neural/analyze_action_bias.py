import argparse
import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch

from .models.action_ranker import ActionRankerMLP
from .train_action_ranker import (
    DEFAULT_BIAS_REPORT,
    DEFAULT_CHECKPOINT_PATH,
    DEFAULT_DATASET_PATH,
    DEFAULT_POLICY_CHECKPOINT,
    _format_bias_report,
    _group_slices,
    _load_policy_model,
    _old_policy_accuracy,
    _score_groups,
    _slot1_baseline,
)


def analyze_action_bias(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    checkpoint_path: Path = DEFAULT_CHECKPOINT_PATH,
    policy_checkpoint_path: Path = DEFAULT_POLICY_CHECKPOINT,
    report_path: Path = DEFAULT_BIAS_REPORT,
    max_eval_groups: int = 50000,
) -> Dict[str, Any]:
    with np.load(dataset_path, allow_pickle=True) as data:
        states = data["state_features"].astype(np.float32)
        actions = data["action_features"].astype(np.float32)
        labels = data["labels"].astype(np.int8)
        group_ids = data["group_ids"].astype(np.int64)
        action_indices = data["action_indices"].astype(np.int64)
        action_kinds = data["action_kinds"].astype(str)
        turns = data["turns"].astype(np.int64)
    group_slices = _group_slices(group_ids)
    selected_groups = np.arange(len(group_slices), dtype=np.int64)
    if max_eval_groups and len(selected_groups) > max_eval_groups:
        rng = np.random.RandomState(6789)
        rng.shuffle(selected_groups)
        selected_groups = selected_groups[:max_eval_groups]
    chosen_slots = []
    for start, end in group_slices:
        chosen = np.where(labels[start:end] == 1)[0]
        if len(chosen) == 1:
            chosen_slots.append(int(action_indices[start + int(chosen[0])]))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model = ActionRankerMLP(
        input_size=int(checkpoint["input_size"]),
        hidden_sizes=list(checkpoint.get("hidden_sizes", [256, 128])),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"], strict=False)
    features = np.concatenate([states, actions], axis=1).astype(np.float32)
    metrics = _score_groups(model, features, labels, action_indices, action_kinds, turns, group_slices, selected_groups, device)
    policy_model, policy_meta = _load_policy_model(policy_checkpoint_path, device)
    report = {
        "dataset_path": str(dataset_path),
        "checkpoint": str(checkpoint_path),
        "decisions": int(len(group_slices)),
        "evaluated_decisions": int(len(selected_groups)),
        "rows": int(len(labels)),
        "action_slot_distribution_in_training_labels": {
            str(slot): int(count) for slot, count in zip(*np.unique(np.asarray(chosen_slots), return_counts=True))
        },
        "recommendation_distribution_by_slot": metrics["recommendation_distribution_by_slot"],
        "recommendation_move_slot_1_rate": metrics["recommendation_move_slot_1_rate"],
        "move_slot_1_baseline_accuracy": _slot1_baseline(labels, action_indices, group_slices, selected_groups),
        "old_policy_top1_accuracy": _old_policy_accuracy(
            policy_model,
            policy_meta,
            states,
            labels,
            action_indices,
            group_slices,
            selected_groups,
            device,
        ),
        "top1_accuracy": metrics["top1_accuracy"],
        "top3_accuracy": metrics["top3_accuracy"],
        "mean_reciprocal_rank": metrics["mean_reciprocal_rank"],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_format_bias_report(report), encoding="utf-8")
    report_path.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        "analyze-action-bias done | "
        f"decisions={report['decisions']} "
        f"slot1_baseline={report['move_slot_1_baseline_accuracy']:.3f} "
        f"old_policy={report['old_policy_top1_accuracy'] if report['old_policy_top1_accuracy'] is not None else 'n/a'} "
        f"ranker_top1={report['top1_accuracy']:.3f} report={report_path}"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze fixed-slot action bias and action-ranker recommendations.")
    parser.add_argument("--dataset-path", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--checkpoint-path", default=str(DEFAULT_CHECKPOINT_PATH))
    parser.add_argument("--policy-checkpoint", default=str(DEFAULT_POLICY_CHECKPOINT))
    parser.add_argument("--report", default=str(DEFAULT_BIAS_REPORT))
    parser.add_argument("--max-eval-groups", type=int, default=50000)
    args = parser.parse_args()
    analyze_action_bias(
        dataset_path=Path(args.dataset_path),
        checkpoint_path=Path(args.checkpoint_path),
        policy_checkpoint_path=Path(args.policy_checkpoint),
        report_path=Path(args.report),
        max_eval_groups=args.max_eval_groups,
    )


if __name__ == "__main__":
    main()
