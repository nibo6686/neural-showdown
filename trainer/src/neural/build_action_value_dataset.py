import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

from .action_features import ACTION_FEATURE_DIM, ACTION_FEATURE_NAMES, ACTION_FEATURE_VERSION
from .build_action_rank_dataset import _decision_rows
from .build_live_private_value_dataset import (
    _reconstructed_completed_private_teams,
    _reconstructed_private_state_for_side,
    _trajectory_prefix_for_training,
)
from .build_replay_value_dataset import DEFAULT_FORMAT, _ensure_trajectories, _load_trajectories, result_from_winner_side
from .checkpoints import torch_load
from .live_opponent_beliefs import build_opponent_beliefs
from .live_private_features import FEATURE_DIM, FEATURE_NAMES, FEATURE_VERSION, build_live_private_feature_vector, public_feature_vector_from_trajectory
from .logging_helper import format_summary, print_line_safe
from .models.policy_value_mlp import PolicyValueMLP
from .tactical_state import TACTICAL_ACTION_FEATURE_NAMES, build_tactical_state, tactical_report_from_state


DEFAULT_OUTPUT_PATH = Path("data/policy/gen9randombattle_action_value_rank_v2.npz")
DEFAULT_REPORT_JSON = Path("artifacts/analysis/action_value_dataset_report.json")
DEFAULT_REPORT_MD = Path("artifacts/analysis/action_value_dataset_report.md")
DEFAULT_REPLAY_DIR = Path("data/replays/raw/gen9randombattle")
DEFAULT_TRAJECTORIES = Path("data/replays/processed/gen9randombattle_trajectories.jsonl.gz")
DEFAULT_VALUE_CHECKPOINT = Path("artifacts/checkpoints/gen9randombattle_live_private_value_v2.pt")


def _checkpoint_state(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    return checkpoint.get("model_state_dict") or checkpoint.get("state_dict") or checkpoint.get("model") or checkpoint


def _load_value_model(path: Path, device: torch.device) -> Tuple[PolicyValueMLP, Dict[str, Any]]:
    checkpoint = torch_load(path, device)
    input_size = int(checkpoint.get("input_size", FEATURE_DIM))
    hidden_sizes = list(
        checkpoint.get("hidden_sizes")
        or checkpoint.get("model_config", {}).get("hidden_sizes", [])
        or checkpoint.get("config", {}).get("hidden_sizes", [])
        or [256, 256]
    )
    action_size = int(checkpoint.get("action_size", 13))
    model = PolicyValueMLP(input_size=input_size, hidden_sizes=hidden_sizes, action_size=action_size).to(device)
    model.load_state_dict(_checkpoint_state(checkpoint), strict=False)
    model.eval()
    return model, checkpoint


def _predict_value(model: PolicyValueMLP, features: np.ndarray, device: torch.device) -> float:
    x = torch.tensor(features.astype(np.float32), dtype=torch.float32, device=device).unsqueeze(0)
    with torch.inference_mode():
        _, values = model(x)
    return float(values.squeeze().detach().cpu().item())


def _state_features_for_turn(
    *,
    trajectory: Dict[str, Any],
    side: str,
    through_turn: int,
    completed_teams: Dict[str, Dict[str, Dict[str, Any]]],
    sets_path: Optional[str],
) -> Tuple[np.ndarray, Dict[str, Any]]:
    prefix = _trajectory_prefix_for_training(trajectory, max(0, int(through_turn)))
    public_features, _ = public_feature_vector_from_trajectory(prefix, perspective_side=side)
    private_state = _reconstructed_private_state_for_side(
        trajectory,
        side=side,
        through_turn=max(0, int(through_turn)),
        completed_teams=completed_teams,
    )
    opponent_belief = build_opponent_beliefs(
        protocol_log=prefix.get("protocol_log", []),
        trajectory=prefix,
        player_side=side,
        sets_path=sets_path,
    )
    tactical_state = build_tactical_state(prefix.get("protocol_log", []), perspective_side=side)
    private_state["opponent_belief"] = opponent_belief
    private_state["tactical_state"] = tactical_state
    features, _ = build_live_private_feature_vector(
        public_features=public_features,
        private_state=private_state,
        opponent_belief=opponent_belief,
        trajectory=prefix,
        player_side=side,
        tactical_state=tactical_state,
    )
    return features, tactical_report_from_state(tactical_state)


def _sample_weight(advantage: float, target_score: float, near_zero: float) -> float:
    magnitude = max(abs(float(advantage)), 0.25 * abs(float(target_score)))
    if magnitude < near_zero:
        return 0.05
    if advantage > 0:
        return float(min(5.0, 0.5 + 4.0 * magnitude))
    return float(min(2.0, 0.15 + 2.0 * magnitude))


def _rank_direction(advantage: float, near_zero: float) -> int:
    if advantage > near_zero:
        return 1
    if advantage < -near_zero:
        return -1
    return 0


def _distribution(values: Sequence[float]) -> Dict[str, Any]:
    if not values:
        return {"count": 0}
    arr = np.asarray(values, dtype=np.float32)
    return {
        "count": int(arr.size),
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "min": float(arr.min()),
        "p05": float(np.quantile(arr, 0.05)),
        "p25": float(np.quantile(arr, 0.25)),
        "median": float(np.quantile(arr, 0.50)),
        "p75": float(np.quantile(arr, 0.75)),
        "p95": float(np.quantile(arr, 0.95)),
        "max": float(arr.max()),
    }


def build_action_value_dataset(
    *,
    format_name: str = DEFAULT_FORMAT,
    replay_dir: Path = DEFAULT_REPLAY_DIR,
    trajectories_path: Path = DEFAULT_TRAJECTORIES,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    report_json_path: Path = DEFAULT_REPORT_JSON,
    report_md_path: Path = DEFAULT_REPORT_MD,
    value_checkpoint_path: Path = DEFAULT_VALUE_CHECKPOINT,
    sets_path: Optional[str] = None,
    final_result_weight: float = 0.25,
    near_zero: float = 0.03,
    max_decisions: Optional[int] = None,
) -> Dict[str, Any]:
    started = time.perf_counter()
    _ensure_trajectories(format_name, replay_dir, trajectories_path)
    trajectories = _load_trajectories(trajectories_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    value_model, value_meta = _load_value_model(value_checkpoint_path, device)
    if int(value_meta.get("input_size", FEATURE_DIM)) != FEATURE_DIM:
        raise ValueError(f"Value checkpoint must use {FEATURE_DIM}D live-private features.")

    state_rows: List[np.ndarray] = []
    action_rows: List[np.ndarray] = []
    labels: List[int] = []
    observed: List[int] = []
    group_ids: List[int] = []
    turns: List[int] = []
    action_indices: List[int] = []
    action_kinds: List[str] = []
    action_labels: List[str] = []
    source_ids: List[str] = []
    value_before_rows: List[float] = []
    value_after_rows: List[float] = []
    advantages: List[float] = []
    target_scores: List[float] = []
    final_results: List[float] = []
    sample_weights: List[float] = []
    rank_directions: List[int] = []
    tactical_json: List[str] = []

    chosen_advantages: List[float] = []
    chosen_target_scores: List[float] = []
    chosen_kind_counts: Counter[str] = Counter()
    tactical_counts: Counter[str] = Counter()
    skipped = Counter()
    decision_id = 0

    for trajectory in trajectories:
        completed_teams = _reconstructed_completed_private_teams(trajectory)
        turns_payload = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
        if result_from_winner_side(trajectory.get("winner_side"), perspective="p1") is None:
            skipped["missing_winner"] += 1
            continue
        for turn_record in sorted(turns_payload, key=lambda item: int(item.get("turn", 0) or 0)):
            turn_number = int(turn_record.get("turn", 0) or 0)
            events = turn_record.get("events") if isinstance(turn_record.get("events"), list) else []
            for event in events:
                if not isinstance(event, dict) or event.get("type") not in ("move", "switch"):
                    continue
                side = event.get("side")
                if side not in ("p1", "p2"):
                    continue
                final_result = result_from_winner_side(trajectory.get("winner_side"), perspective=side)
                if final_result is None:
                    skipped["missing_side_result"] += 1
                    continue
                decision = _decision_rows(
                    trajectory=trajectory,
                    side=side,
                    turn_number=turn_number,
                    event=event,
                    completed_teams=completed_teams,
                    decision_id=decision_id,
                    sets_path=sets_path,
                )
                if not decision or sum(decision["labels"]) != 1:
                    skipped["unmatched_chosen_action"] += 1
                    continue

                before_features = np.asarray(decision["state_features"], dtype=np.float32)
                after_features, after_tactical = _state_features_for_turn(
                    trajectory=trajectory,
                    side=side,
                    through_turn=turn_number,
                    completed_teams=completed_teams,
                    sets_path=sets_path,
                )
                value_before = _predict_value(value_model, before_features, device)
                value_after = _predict_value(value_model, after_features, device)
                advantage = float(value_after - value_before)
                target_score = float(advantage + final_result_weight * float(final_result))
                direction = _rank_direction(advantage, near_zero)
                weight = _sample_weight(advantage, target_score, near_zero)
                tactical_report = dict(decision.get("tactical") or {})
                for key, value in after_tactical.items():
                    tactical_report.setdefault(f"after_{key}", value)
                for key, value in tactical_report.items():
                    if isinstance(value, bool) and value:
                        tactical_counts[key] += 1

                chosen_advantages.append(advantage)
                chosen_target_scores.append(target_score)
                chosen_kind = decision["chosen_label"].split(":", 1)[0].strip().lower()
                chosen_kind_counts[chosen_kind] += 1

                tactical_raw = json.dumps(tactical_report, sort_keys=True, separators=(",", ":"))
                for action, action_feature, label in zip(decision["actions"], decision["action_features"], decision["labels"]):
                    is_chosen = int(label) == 1
                    state_rows.append(before_features)
                    action_rows.append(action_feature)
                    labels.append(int(label))
                    observed.append(1 if is_chosen else 0)
                    group_ids.append(decision_id)
                    turns.append(int(turn_number))
                    action_indices.append(int(action.get("index", 0) or 0))
                    action_kinds.append(str(action.get("kind") or ""))
                    action_labels.append(str(action.get("label") or ""))
                    source_ids.append(str(trajectory.get("replay_id") or ""))
                    value_before_rows.append(value_before if is_chosen else 0.0)
                    value_after_rows.append(value_after if is_chosen else 0.0)
                    advantages.append(advantage if is_chosen else 0.0)
                    target_scores.append(target_score if is_chosen else 0.0)
                    final_results.append(float(final_result) if is_chosen else 0.0)
                    sample_weights.append(weight if is_chosen else 0.0)
                    rank_directions.append(direction if is_chosen else 0)
                    tactical_json.append(tactical_raw)

                decision_id += 1
                if max_decisions is not None and decision_id >= max_decisions:
                    break
            if max_decisions is not None and decision_id >= max_decisions:
                break
        if max_decisions is not None and decision_id >= max_decisions:
            break

    if not labels:
        raise ValueError("No action-value ranking examples were produced.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_path,
        state_features=np.asarray(state_rows, dtype=np.float16),
        action_features=np.asarray(action_rows, dtype=np.float16),
        labels=np.asarray(labels, dtype=np.int8),
        observed=np.asarray(observed, dtype=np.int8),
        group_ids=np.asarray(group_ids, dtype=np.int64),
        turns=np.asarray(turns, dtype=np.int16),
        action_indices=np.asarray(action_indices, dtype=np.int16),
        action_kinds=np.asarray(action_kinds, dtype=object),
        action_labels=np.asarray(action_labels, dtype=object),
        source_ids=np.asarray(source_ids, dtype=object),
        value_before=np.asarray(value_before_rows, dtype=np.float32),
        value_after=np.asarray(value_after_rows, dtype=np.float32),
        advantages=np.asarray(advantages, dtype=np.float32),
        target_scores=np.asarray(target_scores, dtype=np.float32),
        final_results=np.asarray(final_results, dtype=np.float32),
        sample_weights=np.asarray(sample_weights, dtype=np.float32),
        rank_directions=np.asarray(rank_directions, dtype=np.int8),
        tactical_json=np.asarray(tactical_json, dtype=object),
        state_feature_version=np.asarray(FEATURE_VERSION),
        state_feature_names=np.asarray(FEATURE_NAMES),
        action_feature_version=np.asarray(ACTION_FEATURE_VERSION),
        action_feature_names=np.asarray(ACTION_FEATURE_NAMES),
        tactical_action_feature_names=np.asarray(TACTICAL_ACTION_FEATURE_NAMES),
        value_checkpoint=np.asarray(str(value_checkpoint_path)),
        final_result_weight=np.asarray(float(final_result_weight), dtype=np.float32),
        near_zero=np.asarray(float(near_zero), dtype=np.float32),
    )

    advantages_arr = np.asarray(chosen_advantages, dtype=np.float32)
    decisions = int(decision_id)
    report = {
        "output_path": str(output_path),
        "format": format_name,
        "value_checkpoint": str(value_checkpoint_path),
        "decisions": decisions,
        "legal_action_candidates": int(len(labels)),
        "state_feature_version": FEATURE_VERSION,
        "state_dim": FEATURE_DIM,
        "action_feature_version": ACTION_FEATURE_VERSION,
        "action_dim": ACTION_FEATURE_DIM,
        "final_result_weight": float(final_result_weight),
        "near_zero": float(near_zero),
        "value_delta_distribution": _distribution(chosen_advantages),
        "target_score_distribution": _distribution(chosen_target_scores),
        "percent_chosen_actions_with_negative_delta": float(100.0 * (advantages_arr < -near_zero).mean()) if len(advantages_arr) else 0.0,
        "percent_chosen_actions_with_positive_delta": float(100.0 * (advantages_arr > near_zero).mean()) if len(advantages_arr) else 0.0,
        "percent_chosen_actions_near_zero_delta": float(100.0 * (np.abs(advantages_arr) <= near_zero).mean()) if len(advantages_arr) else 0.0,
        "chosen_action_distribution_by_kind": dict(chosen_kind_counts),
        "tactical_slice_rates": {
            "repeated_failed_moves": float(100.0 * tactical_counts.get("has_repeated_failed_move", 0) / max(1, decisions)),
            "move_healed_target": float(100.0 * tactical_counts.get("move_healed_target", 0) / max(1, decisions)),
            "ability_punished_moves": float(100.0 * tactical_counts.get("move_healed_target", 0) / max(1, decisions)),
            "target_already_seeded": float(100.0 * tactical_counts.get("target_already_seeded", 0) / max(1, decisions)),
        },
        "skipped": dict(skipped),
        "device": device.type,
        "wall_time_sec": time.perf_counter() - started,
    }
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md_path.write_text(_format_markdown(report), encoding="utf-8")
    print_line_safe(
        format_summary(
            "build-action-value-dataset",
            {
                "decisions": decisions,
                "candidates": len(labels),
                "neg_delta": f"{report['percent_chosen_actions_with_negative_delta']:.1f}%",
                "output": str(output_path),
            },
        )
    )
    return report


def _format_markdown(report: Dict[str, Any]) -> str:
    delta = report.get("value_delta_distribution", {})
    lines = [
        "# Action Value Dataset Report",
        "",
        f"- Decisions: {report['decisions']}",
        f"- Legal action candidates: {report['legal_action_candidates']}",
        f"- State/action dims: {report['state_dim']} / {report['action_dim']}",
        f"- Value checkpoint: `{report['value_checkpoint']}`",
        f"- Negative value-delta chosen actions: {report['percent_chosen_actions_with_negative_delta']:.1f}%",
        f"- Positive value-delta chosen actions: {report['percent_chosen_actions_with_positive_delta']:.1f}%",
        f"- Value delta mean/std: {delta.get('mean', 0.0):+.4f} / {delta.get('std', 0.0):.4f}",
        f"- Value delta p05/median/p95: {delta.get('p05', 0.0):+.4f} / {delta.get('median', 0.0):+.4f} / {delta.get('p95', 0.0):+.4f}",
        "",
        "## Tactical Slice Rates",
        "",
    ]
    for key, value in sorted(report.get("tactical_slice_rates", {}).items()):
        lines.append(f"- {key}: {value:.1f}%")
    lines.extend(["", f"Output: `{report['output_path']}`", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build value-delta grouped legal-action ranking examples.")
    parser.add_argument("--format", default=DEFAULT_FORMAT)
    parser.add_argument("--replay-dir", default=str(DEFAULT_REPLAY_DIR))
    parser.add_argument("--trajectories", default=str(DEFAULT_TRAJECTORIES))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("--value-checkpoint", default=str(DEFAULT_VALUE_CHECKPOINT))
    parser.add_argument("--sets-path", default=None)
    parser.add_argument("--final-result-weight", type=float, default=0.25)
    parser.add_argument("--near-zero", type=float, default=0.03)
    parser.add_argument("--max-decisions", type=int, default=None)
    args = parser.parse_args()
    build_action_value_dataset(
        format_name=args.format,
        replay_dir=Path(args.replay_dir),
        trajectories_path=Path(args.trajectories),
        output_path=Path(args.output),
        report_json_path=Path(args.report_json),
        report_md_path=Path(args.report_md),
        value_checkpoint_path=Path(args.value_checkpoint),
        sets_path=args.sets_path,
        final_result_weight=args.final_result_weight,
        near_zero=args.near_zero,
        max_decisions=args.max_decisions,
    )


if __name__ == "__main__":
    main()
