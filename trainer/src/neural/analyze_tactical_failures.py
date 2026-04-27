import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from .action_features import ACTION_FEATURE_DIM, build_action_feature_vector
from .build_action_rank_dataset import _legal_actions_from_private_state
from .build_live_private_value_dataset import _reconstructed_completed_private_teams, _reconstructed_private_state_for_side, _trajectory_prefix_for_training
from .build_replay_value_dataset import DEFAULT_FORMAT
from .compare_replay_evals import load_replay_trajectory
from .live_opponent_beliefs import build_opponent_beliefs
from .live_private_features import FEATURE_DIM, build_live_private_feature_vector, public_feature_vector_from_trajectory
from .logging_helper import format_summary, print_line_safe
from .models.action_ranker import ActionRankerMLP
from .tactical_state import TacticalStateTracker, build_tactical_state
from .train_action_ranker import DEFAULT_CHECKPOINT_PATH
from .checkpoints import torch_load


DEFAULT_OUTPUT_DIR = Path("artifacts/replays")
DEFAULT_REPLAY_DIR = Path("data/replays/raw/gen9randombattle")
DEFAULT_TRAJECTORIES = Path("data/replays/processed/gen9randombattle_trajectories.jsonl.gz")


def _load_ranker(path: Path, device: torch.device) -> tuple[Optional[ActionRankerMLP], Dict[str, Any]]:
    if not path.exists():
        return None, {"warning": f"ranker checkpoint missing: {path}"}
    checkpoint = torch_load(path, device)
    model = ActionRankerMLP(
        input_size=int(checkpoint.get("input_size", FEATURE_DIM + ACTION_FEATURE_DIM)),
        hidden_sizes=list(checkpoint.get("hidden_sizes", [256, 128])),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"], strict=False)
    model.eval()
    return model, {**checkpoint, "path": str(path)}


def _score_actions(
    *,
    trajectory: Dict[str, Any],
    side: str,
    turn_number: int,
    completed_teams: Dict[str, Dict[str, Dict[str, Any]]],
    ranker: Optional[ActionRankerMLP],
    ranker_meta: Dict[str, Any],
    device: torch.device,
    chosen_label: Optional[str],
) -> Dict[str, Any]:
    if ranker is None:
        return {"top_action": None, "chosen_action_score": None, "ranker_warning": ranker_meta.get("warning")}
    context_turn = max(0, int(turn_number) - 1)
    prefix = _trajectory_prefix_for_training(trajectory, context_turn)
    public_features, _ = public_feature_vector_from_trajectory(prefix, perspective_side=side)
    private_state = _reconstructed_private_state_for_side(
        trajectory,
        side=side,
        through_turn=context_turn,
        completed_teams=completed_teams,
    )
    tactical_state = build_tactical_state(prefix.get("protocol_log", []), perspective_side=side)
    private_state["tactical_state"] = tactical_state
    opponent_belief = build_opponent_beliefs(
        protocol_log=prefix.get("protocol_log", []),
        trajectory=prefix,
        player_side=side,
    )
    state_features, _ = build_live_private_feature_vector(
        public_features=public_features,
        private_state=private_state,
        opponent_belief=opponent_belief,
        trajectory=prefix,
        player_side=side,
        tactical_state=tactical_state,
    )
    actions = _legal_actions_from_private_state(private_state, chosen_label or "move: unknown")
    state_dim = int(ranker_meta.get("state_dim", state_features.shape[0]))
    action_dim = int(ranker_meta.get("action_dim", ACTION_FEATURE_DIM))
    state_part = state_features[:state_dim] if len(state_features) >= state_dim else np.pad(state_features, (0, state_dim - len(state_features)))
    rows = []
    with torch.inference_mode():
        for action in actions:
            action_features = build_action_feature_vector(action, private_state, tactical_state=tactical_state)
            action_part = action_features[:action_dim] if len(action_features) >= action_dim else np.pad(action_features, (0, action_dim - len(action_features)))
            x = torch.from_numpy(np.concatenate([state_part, action_part]).astype(np.float32)).to(device).unsqueeze(0)
            score = float(ranker(x).squeeze().detach().cpu().item())
            rows.append({"label": str(action.get("label") or ""), "index": int(action.get("index", 0) or 0), "score": score})
    rows.sort(key=lambda item: item["score"], reverse=True)
    chosen_score = None
    if chosen_label:
        normalized = chosen_label.lower().replace(":", ": ")
        for row in rows:
            if row["label"].lower().replace(":", ": ") == normalized:
                chosen_score = row["score"]
                break
    return {
        "top_action": rows[0] if rows else None,
        "chosen_action_score": chosen_score,
        "ranked_actions": rows[:5],
    }


def _chosen_label_for_result(event: Dict[str, Any]) -> Optional[str]:
    move = event.get("move")
    return f"move: {move}" if move else None


def analyze_tactical_failures(
    *,
    replay: str,
    side: str = "p1",
    replay_dir: Path = DEFAULT_REPLAY_DIR,
    trajectories_path: Path = DEFAULT_TRAJECTORIES,
    format_name: str = DEFAULT_FORMAT,
    ranker_checkpoint: Path = DEFAULT_CHECKPOINT_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Any]:
    try:
        trajectory = load_replay_trajectory(
            replay,
            replay_dir=replay_dir,
            trajectories_path=trajectories_path,
            format_name=format_name,
        )
    except FileNotFoundError as exc:
        replay_id = str(Path(replay).stem)
        report = {
            "replay_id": replay_id,
            "side": side,
            "ranker_checkpoint": str(ranker_checkpoint),
            "ranker_loaded": False,
            "failed_move_count": 0,
            "healed_target_count": 0,
            "repeated_failed_chain_count": 0,
            "failures": [],
            "repeated_failed_chains": [],
            "healed_target_events": [],
            "v2_ranker_lowered_bad_action": False,
            "error": str(exc),
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{replay_id}_tactical_failures_{side}.json"
        md_path = output_dir / f"{replay_id}_tactical_failures_{side}.md"
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        md_path.write_text(_format_markdown(report), encoding="utf-8")
        print_line_safe(f"analyze-tactical-failures warning | {exc}")
        print_line_safe(f"analyze-tactical-failures | replay={replay_id} side={side} report={json_path}")
        return report
    replay_id = str(trajectory.get("replay_id") or replay)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ranker, ranker_meta = _load_ranker(ranker_checkpoint, device)
    completed_teams = _reconstructed_completed_private_teams(trajectory)
    tracker = TacticalStateTracker()
    failures: List[Dict[str, Any]] = []
    repeated_chains: List[Dict[str, Any]] = []
    healed_target: List[Dict[str, Any]] = []
    previous_recent_len = 0

    for line in trajectory.get("protocol_log", []):
        tracker.consume_line(str(line))
        snapshot = tracker.snapshot(perspective_side=side)
        recent = snapshot.get("recent_events", [])
        new_events = recent[previous_recent_len:] if len(recent) >= previous_recent_len else recent
        previous_recent_len = len(recent)
        for event in new_events:
            if event.get("side") != side:
                continue
            if event.get("result") not in {"failed", "immune", "protected", "missed", "healed_target"}:
                continue
            chosen_label = _chosen_label_for_result(event)
            score_report = _score_actions(
                trajectory=trajectory,
                side=side,
                turn_number=int(event.get("turn", 0) or 0),
                completed_teams=completed_teams,
                ranker=ranker,
                ranker_meta=ranker_meta,
                device=device,
                chosen_label=chosen_label,
            )
            row = {
                "turn": int(event.get("turn", 0) or 0),
                "side": event.get("side"),
                "move": event.get("move"),
                "target": event.get("target"),
                "result": event.get("result"),
                "raw_context": str(line),
                **score_report,
            }
            failures.append(row)
            if event.get("result") == "healed_target":
                healed_target.append(row)
            own_chain = (snapshot.get("own") or {}).get("same_move_chain") or {}
            if int(own_chain.get("failed_count", 0) or 0) > 1:
                repeated_chains.append(
                    {
                        "turn": int(event.get("turn", 0) or 0),
                        "move": own_chain.get("move"),
                        "same_move_count": int(own_chain.get("count", 0) or 0),
                        "same_move_failed_count": int(own_chain.get("failed_count", 0) or 0),
                    }
                )

    report = {
        "replay_id": replay_id,
        "side": side,
        "ranker_checkpoint": str(ranker_checkpoint),
        "ranker_loaded": ranker is not None,
        "failed_move_count": len(failures),
        "healed_target_count": len(healed_target),
        "repeated_failed_chain_count": len(repeated_chains),
        "failures": failures,
        "repeated_failed_chains": repeated_chains,
        "healed_target_events": healed_target,
        "v2_ranker_lowered_bad_action": any(
            row.get("top_action") and row.get("chosen_action_score") is not None and row["chosen_action_score"] < row["top_action"]["score"]
            for row in failures
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{replay_id}_tactical_failures_{side}.json"
    md_path = output_dir / f"{replay_id}_tactical_failures_{side}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_format_markdown(report), encoding="utf-8")
    print_line_safe(f"analyze-tactical-failures | replay={replay_id} side={side} report={json_path}")
    print_line_safe(
        format_summary(
            "analyze-tactical-failures",
            {
                "failures": report["failed_move_count"],
                "healed": report["healed_target_count"],
                "chains": report["repeated_failed_chain_count"],
                "ranker_loaded": report["ranker_loaded"],
            },
        )
    )
    return report


def _format_markdown(report: Dict[str, Any]) -> str:
    lines = [
        f"# Tactical Failure Analysis: {report['replay_id']}",
        "",
        f"- Side: `{report['side']}`",
        f"- Ranker loaded: {report['ranker_loaded']}",
        f"- Failed/non-productive moves: {report['failed_move_count']}",
        f"- Healed-target events: {report['healed_target_count']}",
        f"- Repeated failed chains: {report['repeated_failed_chain_count']}",
        f"- V2 ranker lowered at least one bad action: {report['v2_ranker_lowered_bad_action']}",
        "",
    ]
    if report.get("error"):
        lines.extend(["## Error", "", str(report["error"]), ""])
    lines.extend(["## Failures", ""])
    for row in report.get("failures", []):
        top = row.get("top_action") or {}
        lines.append(
            f"- T{row['turn']:02d} {row.get('move')} -> {row.get('target')} result={row.get('result')} "
            f"chosen_score={row.get('chosen_action_score')} top={top.get('label')} top_score={top.get('score')}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze tactical failure events in one replay.")
    parser.add_argument("--replay", "--replay-id", dest="replay", required=True)
    parser.add_argument("--side", choices=["p1", "p2"], default="p1")
    parser.add_argument("--replay-dir", default=str(DEFAULT_REPLAY_DIR))
    parser.add_argument("--trajectories", default=str(DEFAULT_TRAJECTORIES))
    parser.add_argument("--format", default=DEFAULT_FORMAT)
    parser.add_argument("--ranker-checkpoint", default=str(DEFAULT_CHECKPOINT_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    analyze_tactical_failures(
        replay=args.replay,
        side=args.side,
        replay_dir=Path(args.replay_dir),
        trajectories_path=Path(args.trajectories),
        format_name=args.format,
        ranker_checkpoint=Path(args.ranker_checkpoint),
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
