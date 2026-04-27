import argparse
import html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

from .action_features import ACTION_FEATURE_DIM, ACTION_FEATURE_NAMES, build_action_feature_vector
from .build_action_rank_dataset import _action_label_from_event, _chosen_index, _legal_actions_from_private_state
from .build_live_private_value_dataset import _reconstructed_completed_private_teams, _reconstructed_private_state_for_side, _trajectory_prefix_for_training
from .build_replay_value_dataset import DEFAULT_FORMAT
from .checkpoints import torch_load
from .compare_replay_evals import DEFAULT_REPLAY_DIR, DEFAULT_TRAJECTORIES, load_replay_trajectory
from .live_opponent_beliefs import build_opponent_beliefs
from .live_private_features import FEATURE_DIM, build_live_private_feature_vector, public_feature_vector_from_trajectory
from .logging_helper import format_summary, print_line_safe
from .models.action_ranker import ActionRankerMLP
from .parse_replay_logs import parse_protocol_log
from .tactical_state import build_tactical_state


DEFAULT_OUTPUT_DIR = Path("artifacts/replays")
DEFAULT_V1_RANKER = Path("artifacts/checkpoints/gen9randombattle_action_ranker.pt")
DEFAULT_V2_RANKER = Path("artifacts/checkpoints/gen9randombattle_action_ranker_v2.pt")
DEFAULT_VALUE_RANKER = Path("artifacts/checkpoints/gen9randombattle_action_value_ranker_v2.pt")


def _load_ranker(path: Path, device: torch.device) -> Tuple[Optional[ActionRankerMLP], Dict[str, Any]]:
    if not path.exists():
        return None, {"path": str(path), "loaded": False, "warning": f"ranker checkpoint missing: {path}"}
    checkpoint = torch_load(path, device)
    model = ActionRankerMLP(
        input_size=int(checkpoint.get("input_size", FEATURE_DIM + ACTION_FEATURE_DIM)),
        hidden_sizes=list(checkpoint.get("hidden_sizes", [256, 128])),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"], strict=False)
    model.eval()
    return model, {**checkpoint, "path": str(path), "loaded": True}


def _load_replay(replay: str, *, replay_dir: Path, trajectories_path: Path, format_name: str) -> Dict[str, Any]:
    path = Path(replay)
    if path.exists() and path.suffix.lower() in {".html", ".htm"}:
        text = html.unescape(path.read_text(encoding="utf-8", errors="replace"))
        protocol_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
        if protocol_lines:
            return parse_protocol_log(protocol_lines, replay_id=path.stem, format_name=format_name, source_path=str(path))
    return load_replay_trajectory(
        replay,
        replay_dir=replay_dir,
        trajectories_path=trajectories_path,
        format_name=format_name,
    )


def _score_with_ranker(
    *,
    model: Optional[ActionRankerMLP],
    meta: Dict[str, Any],
    state_features: np.ndarray,
    action_features: Sequence[np.ndarray],
    device: torch.device,
) -> List[Optional[float]]:
    if model is None:
        return [None for _ in action_features]
    state_dim = int(meta.get("state_dim", state_features.shape[0]))
    action_dim = int(meta.get("action_dim", ACTION_FEATURE_DIM))
    state_part = state_features[:state_dim] if len(state_features) >= state_dim else np.pad(state_features, (0, state_dim - len(state_features)))
    rows = []
    with torch.inference_mode():
        for action_feature in action_features:
            action_part = action_feature[:action_dim] if len(action_feature) >= action_dim else np.pad(action_feature, (0, action_dim - len(action_feature)))
            x = torch.from_numpy(np.concatenate([state_part, action_part]).astype(np.float32)).to(device).unsqueeze(0)
            rows.append(float(model(x).squeeze().detach().cpu().item()))
    return rows


def _fixed_policy_scores(actions: Sequence[Dict[str, Any]]) -> List[float]:
    scores = []
    for action in actions:
        index = int(action.get("index", 99) or 99)
        disabled = bool(action.get("disabled", False))
        scores.append(float(-1000.0 if disabled else -index))
    return scores


def _rank_report(scores: Sequence[Optional[float]], actions: Sequence[Dict[str, Any]], chosen_ordinal: int) -> Dict[str, Any]:
    if not scores or any(score is None for score in scores):
        return {"loaded": False, "top_action": None, "chosen_score": None, "chosen_rank": None}
    numeric = np.asarray([float(score) for score in scores], dtype=np.float32)
    order = np.argsort(-numeric)
    chosen_rank = int(np.where(order == chosen_ordinal)[0][0]) + 1
    top_index = int(order[0])
    return {
        "loaded": True,
        "top_action": {
            "label": str(actions[top_index].get("label") or ""),
            "index": int(actions[top_index].get("index", 0) or 0),
            "score": float(numeric[top_index]),
        },
        "chosen_score": float(numeric[chosen_ordinal]),
        "chosen_rank": chosen_rank,
        "top3_contains_chosen": bool(chosen_ordinal in set(int(i) for i in order[:3])),
    }


def _action_slice_tags(action: Dict[str, Any], features: np.ndarray) -> List[str]:
    name_to_index = {name: idx for idx, name in enumerate(ACTION_FEATURE_NAMES)}

    def enabled(name: str) -> bool:
        idx = name_to_index.get(name)
        return idx is not None and idx < len(features) and float(features[idx]) > 0.5

    tags = []
    if enabled("move_failed_recently") or enabled("move_failed_last_time_used") or enabled("same_move_same_target_failed_before"):
        tags.append("repeated_failed_moves")
    if enabled("move_healed_target_recently"):
        tags.append("move_healed_target")
    if enabled("target_known_or_possible_ability_absorbs_move_type") or enabled("target_known_or_possible_ability_blocks_move_effect"):
        tags.append("ability_punished_moves")
    if str(action.get("kind")) == "switch" and (enabled("switch_target_hazard_vulnerability") or enabled("switch_own_hazards_norm")):
        tags.append("switch_into_ko_heavy_damage")
    if enabled("flag_setup") or enabled("move_id_flag_swordsdance") or enabled("move_id_flag_nastyplot") or enabled("move_id_flag_calmmind"):
        tags.append("setup_into_immediate_death")
    return tags


def compare_action_rankers(
    *,
    replay: str,
    side: str = "p1",
    replay_dir: Path = DEFAULT_REPLAY_DIR,
    trajectories_path: Path = DEFAULT_TRAJECTORIES,
    format_name: str = DEFAULT_FORMAT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    v1_ranker: Path = DEFAULT_V1_RANKER,
    v2_ranker: Path = DEFAULT_V2_RANKER,
    value_ranker: Path = DEFAULT_VALUE_RANKER,
) -> Dict[str, Any]:
    if side not in ("p1", "p2"):
        raise ValueError("--side must be p1 or p2")
    trajectory = _load_replay(replay, replay_dir=replay_dir, trajectories_path=trajectories_path, format_name=format_name)
    replay_id = str(trajectory.get("replay_id") or Path(replay).stem)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    v1_model, v1_meta = _load_ranker(v1_ranker, device)
    v2_model, v2_meta = _load_ranker(v2_ranker, device)
    value_model, value_meta = _load_ranker(value_ranker, device)
    completed_teams = _reconstructed_completed_private_teams(trajectory)

    rows: List[Dict[str, Any]] = []
    slice_summary: Dict[str, Dict[str, int]] = {}
    methods = {
        "old_fixed_policy": {"loaded": True, "path": None},
        "v1_action_ranker": {"loaded": v1_model is not None, "path": str(v1_ranker)},
        "v2_action_ranker": {"loaded": v2_model is not None, "path": str(v2_ranker)},
        "action_value_ranker": {"loaded": value_model is not None, "path": str(value_ranker)},
    }

    turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    for turn_record in sorted(turns, key=lambda item: int(item.get("turn", 0) or 0)):
        turn_number = int(turn_record.get("turn", 0) or 0)
        events = turn_record.get("events") if isinstance(turn_record.get("events"), list) else []
        for event in events:
            if not isinstance(event, dict) or event.get("side") != side or event.get("type") not in ("move", "switch"):
                continue
            chosen_label = _action_label_from_event(event)
            if not chosen_label:
                continue
            context_turn = max(0, turn_number - 1)
            prefix = _trajectory_prefix_for_training(trajectory, context_turn)
            public_features, _ = public_feature_vector_from_trajectory(prefix, perspective_side=side)
            private_state = _reconstructed_private_state_for_side(
                trajectory,
                side=side,
                through_turn=context_turn,
                completed_teams=completed_teams,
            )
            opponent_belief = build_opponent_beliefs(
                protocol_log=prefix.get("protocol_log", []),
                trajectory=prefix,
                player_side=side,
            )
            tactical_state = build_tactical_state(prefix.get("protocol_log", []), perspective_side=side)
            private_state["opponent_belief"] = opponent_belief
            private_state["tactical_state"] = tactical_state
            state_features, _ = build_live_private_feature_vector(
                public_features=public_features,
                private_state=private_state,
                opponent_belief=opponent_belief,
                trajectory=prefix,
                player_side=side,
                tactical_state=tactical_state,
            )
            actions = _legal_actions_from_private_state(private_state, chosen_label)
            chosen_ordinal = _chosen_index(actions, chosen_label)
            if chosen_ordinal is None or not actions:
                continue
            action_features = [build_action_feature_vector(action, private_state, tactical_state=tactical_state) for action in actions]
            score_sets = {
                "old_fixed_policy": _fixed_policy_scores(actions),
                "v1_action_ranker": _score_with_ranker(model=v1_model, meta=v1_meta, state_features=state_features, action_features=action_features, device=device),
                "v2_action_ranker": _score_with_ranker(model=v2_model, meta=v2_meta, state_features=state_features, action_features=action_features, device=device),
                "action_value_ranker": _score_with_ranker(model=value_model, meta=value_meta, state_features=state_features, action_features=action_features, device=device),
            }
            ranked = {name: _rank_report(scores, actions, chosen_ordinal) for name, scores in score_sets.items()}
            chosen_tags = _action_slice_tags(actions[chosen_ordinal], np.asarray(action_features[chosen_ordinal]))
            for tag in chosen_tags:
                entry = slice_summary.setdefault(tag, {"count": 0, "value_lower_than_v2": 0, "value_ranked_below_top": 0})
                entry["count"] += 1
                value_score = ranked["action_value_ranker"].get("chosen_score")
                v2_score = ranked["v2_action_ranker"].get("chosen_score")
                if value_score is not None and v2_score is not None and float(value_score) < float(v2_score):
                    entry["value_lower_than_v2"] += 1
                top = ranked["action_value_ranker"].get("top_action") or {}
                if value_score is not None and top.get("score") is not None and float(value_score) < float(top["score"]):
                    entry["value_ranked_below_top"] += 1
            rows.append(
                {
                    "turn": turn_number,
                    "side": side,
                    "chosen_action": chosen_label,
                    "chosen_action_tags": chosen_tags,
                    "rankers": ranked,
                    "top_actions_by_ranker": {name: detail.get("top_action") for name, detail in ranked.items()},
                    "all_actions": [
                        {
                            "label": str(action.get("label") or ""),
                            "index": int(action.get("index", 0) or 0),
                            "kind": str(action.get("kind") or ""),
                            "tags": _action_slice_tags(action, np.asarray(features)),
                            "scores": {name: scores[idx] for name, scores in score_sets.items()},
                        }
                        for idx, (action, features) in enumerate(zip(actions, action_features))
                    ],
                }
            )

    aggregate: Dict[str, Dict[str, Any]] = {}
    for name in methods:
        loaded_rows = [row for row in rows if row["rankers"][name].get("loaded")]
        aggregate[name] = {
            "loaded": bool(methods[name]["loaded"]),
            "path": methods[name]["path"],
            "top1_imitation_accuracy": float(np.mean([row["rankers"][name]["chosen_rank"] == 1 for row in loaded_rows])) if loaded_rows else None,
            "top3_imitation_accuracy": float(np.mean([row["rankers"][name].get("top3_contains_chosen", False) for row in loaded_rows])) if loaded_rows else None,
            "mean_chosen_rank": float(np.mean([row["rankers"][name]["chosen_rank"] for row in loaded_rows])) if loaded_rows else None,
        }

    report = {
        "replay_id": replay_id,
        "side": side,
        "format": format_name,
        "winner_side": trajectory.get("winner_side"),
        "rankers": methods,
        "aggregate": aggregate,
        "tactical_slice_metrics": slice_summary,
        "decision_count": len(rows),
        "rows": rows,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{replay_id}_action_ranker_comparison_{side}.json"
    md_path = output_dir / f"{replay_id}_action_ranker_comparison_{side}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_format_markdown(report), encoding="utf-8")
    print_line_safe(f"compare-action-rankers | replay={replay_id} side={side} report={json_path}")
    print_line_safe(
        format_summary(
            "compare-action-rankers",
            {
                "decisions": len(rows),
                "value_loaded": methods["action_value_ranker"]["loaded"],
                "json": str(json_path),
            },
        )
    )
    return report


def _format_markdown(report: Dict[str, Any]) -> str:
    lines = [
        f"# Action Ranker Comparison: {report['replay_id']}",
        "",
        f"- Side: `{report['side']}`",
        f"- Winner: `{report.get('winner_side')}`",
        f"- Decisions: {report['decision_count']}",
        "",
        "## Aggregate",
        "",
    ]
    for name, details in report.get("aggregate", {}).items():
        top1 = details.get("top1_imitation_accuracy")
        top3 = details.get("top3_imitation_accuracy")
        rank = details.get("mean_chosen_rank")
        lines.append(
            f"- {name}: loaded={details.get('loaded')} top1={top1:.3f} top3={top3:.3f} mean_rank={rank:.2f}"
            if top1 is not None and top3 is not None and rank is not None
            else f"- {name}: loaded={details.get('loaded')}"
        )
    lines.extend(["", "## Tactical Slices", ""])
    for name, details in sorted(report.get("tactical_slice_metrics", {}).items()):
        count = int(details.get("count", 0))
        lines.append(
            f"- {name}: n={count} value_lower_than_v2={details.get('value_lower_than_v2', 0)} "
            f"value_ranked_below_top={details.get('value_ranked_below_top', 0)}"
        )
    lines.extend(["", "## Decisions", ""])
    for row in report.get("rows", []):
        value = row["rankers"].get("action_value_ranker", {})
        v2 = row["rankers"].get("v2_action_ranker", {})
        lines.append(
            f"- T{row['turn']:02d} {row['chosen_action']} tags={','.join(row.get('chosen_action_tags') or []) or 'none'} "
            f"v2_rank={v2.get('chosen_rank')} value_rank={value.get('chosen_rank')} "
            f"v2_score={v2.get('chosen_score')} value_score={value.get('chosen_score')}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare fixed, v1, v2, and value-delta action rankers on one replay.")
    parser.add_argument("--replay", "--replay-id", "--replay-path", dest="replay", required=True)
    parser.add_argument("--side", choices=["p1", "p2"], default="p1")
    parser.add_argument("--replay-dir", default=str(DEFAULT_REPLAY_DIR))
    parser.add_argument("--trajectories", default=str(DEFAULT_TRAJECTORIES))
    parser.add_argument("--format", default=DEFAULT_FORMAT)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--v1-ranker", default=str(DEFAULT_V1_RANKER))
    parser.add_argument("--v2-ranker", default=str(DEFAULT_V2_RANKER))
    parser.add_argument("--value-ranker", default=str(DEFAULT_VALUE_RANKER))
    args = parser.parse_args()
    compare_action_rankers(
        replay=args.replay,
        side=args.side,
        replay_dir=Path(args.replay_dir),
        trajectories_path=Path(args.trajectories),
        format_name=args.format,
        output_dir=Path(args.output_dir),
        v1_ranker=Path(args.v1_ranker),
        v2_ranker=Path(args.v2_ranker),
        value_ranker=Path(args.value_ranker),
    )


if __name__ == "__main__":
    main()
