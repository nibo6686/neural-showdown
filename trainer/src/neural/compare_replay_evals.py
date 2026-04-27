import argparse
import gzip
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import torch

from .build_live_private_value_dataset import (
    _reconstructed_completed_private_teams,
    _reconstructed_private_state_for_side,
    _trajectory_prefix_for_training,
)
from .build_replay_value_dataset import DEFAULT_FORMAT
from .checkpoints import torch_load
from .live_opponent_beliefs import build_opponent_beliefs
from .live_private_features import (
    FEATURE_DIM,
    FEATURE_VERSION,
    build_live_private_feature_vector,
    infer_opponent_active_species,
    public_feature_vector_from_trajectory,
)
from .logging_helper import format_summary, print_line_safe
from .models.policy_value_mlp import PolicyValueMLP
from .parse_replay_logs import parse_protocol_log


DEFAULT_OLD_CHECKPOINT = Path("artifacts/checkpoints/gen9randombattle_replay_value.pt")
DEFAULT_NEW_CHECKPOINT = Path("artifacts/checkpoints/gen9randombattle_live_private_value_v2.pt")
DEFAULT_REPLAY_DIR = Path("data/replays/raw/gen9randombattle")
DEFAULT_TRAJECTORIES = Path("data/replays/processed/gen9randombattle_trajectories.jsonl.gz")
DEFAULT_OUTPUT_DIR = Path("artifacts/replays")


def _checkpoint_state(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    return checkpoint.get("model_state_dict") or checkpoint.get("state_dict") or checkpoint.get("model") or checkpoint


def _load_model(path: Path, device: torch.device) -> Tuple[PolicyValueMLP, Dict[str, Any]]:
    checkpoint = torch_load(path, device)
    input_size = int(checkpoint.get("input_size", 31))
    hidden_sizes = list(
        checkpoint.get("hidden_sizes")
        or checkpoint.get("model_config", {}).get("hidden_sizes", [])
        or checkpoint.get("config", {}).get("hidden_sizes", [])
        or [128, 128]
    )
    action_size = int(checkpoint.get("action_size", 13))
    model = PolicyValueMLP(input_size=input_size, hidden_sizes=hidden_sizes, action_size=action_size).to(device)
    model.load_state_dict(_checkpoint_state(checkpoint), strict=False)
    model.eval()
    return model, checkpoint


def _predict_value(model: PolicyValueMLP, features: np.ndarray, device: torch.device) -> float:
    x = torch.tensor(features.astype(np.float32), dtype=torch.float32, device=device).unsqueeze(0)
    with torch.inference_mode():
        output = model(x)
    value_tensor = output[1] if isinstance(output, tuple) else output.get("value") if isinstance(output, dict) else output
    return float(value_tensor.squeeze().detach().cpu().item())


def _iter_trajectories(path: Path) -> Iterable[Dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _load_replay_json_log(path: Path) -> Optional[List[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key in ("log", "logs", "protocol_log"):
        value = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(value, list):
            return [str(line) for line in value]
        if isinstance(value, str):
            return value.splitlines()
    return None


def load_replay_trajectory(
    replay: str,
    *,
    replay_dir: Path = DEFAULT_REPLAY_DIR,
    trajectories_path: Path = DEFAULT_TRAJECTORIES,
    format_name: str = DEFAULT_FORMAT,
) -> Dict[str, Any]:
    path = Path(replay)
    if path.exists():
        if path.suffix == ".log":
            log_lines = path.read_text(encoding="utf-8").splitlines()
            return parse_protocol_log(log_lines, replay_id=path.stem, format_name=format_name, source_path=str(path))
        if path.suffix == ".json":
            log_lines = _load_replay_json_log(path)
            if log_lines is not None:
                return parse_protocol_log(log_lines, replay_id=path.stem, format_name=format_name, source_path=str(path))
            return json.loads(path.read_text(encoding="utf-8"))

    replay_id = replay
    raw_log = replay_dir / f"{replay_id}.log"
    if raw_log.exists():
        log_lines = raw_log.read_text(encoding="utf-8").splitlines()
        return parse_protocol_log(log_lines, replay_id=replay_id, format_name=format_name, source_path=str(raw_log))

    if trajectories_path.exists():
        for trajectory in _iter_trajectories(trajectories_path):
            if str(trajectory.get("replay_id")) == replay_id:
                return trajectory
    if replay_id.startswith("gen") and "/" not in replay_id and "\\" not in replay_id:
        url = f"https://replay.pokemonshowdown.com/{replay_id}.log"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "neural-showdown-analysis/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = response.read().decode("utf-8", errors="replace")
            replay_dir.mkdir(parents=True, exist_ok=True)
            raw_log.write_text(payload, encoding="utf-8")
            return parse_protocol_log(payload.splitlines(), replay_id=replay_id, format_name=format_name, source_path=url)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise FileNotFoundError(f"Could not find replay id/path: {replay}; remote fetch failed: {exc}") from exc
    raise FileNotFoundError(f"Could not find replay id/path: {replay}")


def _action_label(event: Dict[str, Any]) -> str:
    if event.get("type") == "move":
        return f"move: {event.get('move')}"
    if event.get("type") == "switch":
        species = str(event.get("details") or event.get("actor") or "").split(",", 1)[0]
        return f"switch: {species}"
    return str(event.get("type") or "unknown")


def _species_from_text(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value)
    if ": " in text:
        text = text.split(": ", 1)[1]
    return text.split(",", 1)[0].strip() or None


def _event_own_active(event: Dict[str, Any], fallback: Optional[str]) -> Optional[str]:
    if event.get("type") == "move":
        return _species_from_text(event.get("actor")) or fallback
    if event.get("type") == "switch":
        return _species_from_text(event.get("details") or event.get("actor")) or fallback
    return fallback


def _event_opponent_active(event: Dict[str, Any], fallback: Optional[str]) -> Optional[str]:
    if event.get("type") == "move":
        return _species_from_text(event.get("target")) or fallback
    return fallback


def _side_value_to_p1(value: float, side: str) -> float:
    return value if side == "p1" else -value


def _win_prob(value: float) -> float:
    return max(0.0, min(1.0, (value + 1.0) / 2.0))


def compare_replay_evals(
    *,
    replay: str,
    side: str = "p1",
    old_checkpoint: Path = DEFAULT_OLD_CHECKPOINT,
    new_checkpoint: Path = DEFAULT_NEW_CHECKPOINT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    replay_dir: Path = DEFAULT_REPLAY_DIR,
    trajectories_path: Path = DEFAULT_TRAJECTORIES,
    format_name: str = DEFAULT_FORMAT,
) -> Dict[str, Any]:
    if side not in ("p1", "p2"):
        raise ValueError("--side must be p1 or p2")

    trajectory = load_replay_trajectory(
        replay,
        replay_dir=replay_dir,
        trajectories_path=trajectories_path,
        format_name=format_name,
    )
    replay_id = str(trajectory.get("replay_id") or Path(replay).stem)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    old_model, old_meta = _load_model(old_checkpoint, device)
    new_model, new_meta = _load_model(new_checkpoint, device)
    if int(new_meta.get("input_size", FEATURE_DIM)) != FEATURE_DIM:
        raise ValueError(f"New checkpoint must be {FEATURE_DIM}D live-private features.")

    completed_teams = _reconstructed_completed_private_teams(trajectory)
    rows: List[Dict[str, Any]] = []
    deltas: List[float] = []

    turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    for turn_record in sorted(turns, key=lambda item: int(item.get("turn", 0) or 0)):
        turn_number = int(turn_record.get("turn", 0) or 0)
        prefix = _trajectory_prefix_for_training(trajectory, turn_number)
        public_features, _ = public_feature_vector_from_trajectory(prefix, perspective_side=side)
        private_state = _reconstructed_private_state_for_side(
            trajectory,
            side=side,
            through_turn=turn_number,
            completed_teams=completed_teams,
        )
        opponent_belief = build_opponent_beliefs(
            protocol_log=prefix.get("protocol_log", []),
            trajectory=prefix,
            player_side=side,
        )
        live_features, _ = build_live_private_feature_vector(
            public_features=public_features,
            private_state=private_state,
            opponent_belief=opponent_belief,
            trajectory=prefix,
            player_side=side,
        )
        old_side_value = _predict_value(old_model, public_features, device)
        new_side_value = _predict_value(new_model, live_features, device)
        old_p1_value = _side_value_to_p1(old_side_value, side)
        new_p1_value = _side_value_to_p1(new_side_value, side)
        delta = new_p1_value - old_p1_value

        own_active = private_state.get("active_species")
        opponent_active = infer_opponent_active_species(prefix, side)
        events = turn_record.get("events") if isinstance(turn_record.get("events"), list) else []
        side_actions = [
            event
            for event in events
            if isinstance(event, dict) and event.get("side") == side and event.get("type") in ("move", "switch")
        ]
        if not side_actions:
            side_actions = [{}]

        for event in side_actions:
            row = {
                "turn": turn_number,
                "side": side,
                "old_p1_value": old_p1_value,
                "old_p1_win_prob": _win_prob(old_p1_value),
                "new_p1_value": new_p1_value,
                "new_p1_win_prob": _win_prob(new_p1_value),
                "delta": delta,
                "absolute_delta": abs(delta),
                "actual_action": _action_label(event) if event else None,
                "own_active": _event_own_active(event, own_active),
                "opponent_active": _event_opponent_active(event, opponent_active),
                "winner_side": trajectory.get("winner_side"),
                "large_disagreement": abs(delta) >= 0.5,
            }
            rows.append(row)
            deltas.append(abs(delta))

    winner_side = trajectory.get("winner_side")
    winner_p1_sign = 1 if winner_side == "p1" else -1 if winner_side == "p2" else 0
    old_align = sum(1 for row in rows if winner_p1_sign and (row["old_p1_value"] > 0) == (winner_p1_sign > 0))
    new_align = sum(1 for row in rows if winner_p1_sign and (row["new_p1_value"] > 0) == (winner_p1_sign > 0))
    most = sorted(rows, key=lambda item: item["absolute_delta"], reverse=True)[:10]
    final_row = rows[-1] if rows else {}
    report = {
        "replay_id": replay_id,
        "side": side,
        "winner_side": winner_side,
        "old_checkpoint": str(old_checkpoint),
        "new_checkpoint": str(new_checkpoint),
        "new_feature_version": FEATURE_VERSION,
        "turn_action_count": len(rows),
        "average_absolute_difference": float(np.mean(deltas)) if deltas else 0.0,
        "old_sign_align_count": old_align,
        "new_sign_align_count": new_align,
        "better_sign_alignment": "new" if new_align > old_align else "old" if old_align > new_align else "tie",
        "old_final_turn_confidence": final_row.get("old_p1_win_prob"),
        "new_final_turn_confidence": final_row.get("new_p1_win_prob"),
        "largest_disagreements": most,
        "rows": rows,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{replay_id}_model_comparison.json"
    md_path = output_dir / f"{replay_id}_model_comparison.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_format_markdown(report), encoding="utf-8")
    print_line_safe(f"compare-replay-evals | replay={replay_id} side={side} report={json_path}")
    print_line_safe(
        format_summary(
            "compare-replay-evals",
            {
                "turn_actions": len(rows),
                "avg_abs_delta": f"{report['average_absolute_difference']:.3f}",
                "better_sign": report["better_sign_alignment"],
                "json": str(json_path),
            },
        )
    )
    return report


def _format_markdown(report: Dict[str, Any]) -> str:
    lines = [
        f"# Replay Model Comparison: {report['replay_id']}",
        "",
        f"- Side perspective: `{report['side']}`",
        f"- Winner: `{report['winner_side']}`",
        f"- Old checkpoint: `{report['old_checkpoint']}`",
        f"- New checkpoint: `{report['new_checkpoint']}`",
        f"- Average absolute difference: {report['average_absolute_difference']:.3f}",
        f"- Better sign alignment: {report['better_sign_alignment']}",
        f"- Old/new final-turn p1 win probability: {report.get('old_final_turn_confidence', 0):.3f} / {report.get('new_final_turn_confidence', 0):.3f}",
        "",
        "## Largest Disagreements",
        "",
    ]
    for row in report.get("largest_disagreements", []):
        lines.append(
            f"- Turn {row['turn']} {row.get('actual_action')}: old={row['old_p1_value']:+.3f} "
            f"new={row['new_p1_value']:+.3f} delta={row['delta']:+.3f} "
            f"own={row.get('own_active')} opp={row.get('opponent_active')}"
        )
    lines.extend(["", "## Turn-by-Turn", ""])
    for row in report.get("rows", []):
        lines.append(
            f"- T{row['turn']:02d} {row.get('actual_action')}: old_wp={row['old_p1_win_prob']:.3f} "
            f"new_wp={row['new_p1_win_prob']:.3f} delta={row['delta']:+.3f}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare old 31D and new 78D value evals on one saved replay.")
    parser.add_argument("--replay", "--replay-id", dest="replay", required=True)
    parser.add_argument("--side", choices=["p1", "p2"], default="p1")
    parser.add_argument("--old-checkpoint", default=str(DEFAULT_OLD_CHECKPOINT))
    parser.add_argument("--new-checkpoint", default=str(DEFAULT_NEW_CHECKPOINT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--replay-dir", default=str(DEFAULT_REPLAY_DIR))
    parser.add_argument("--trajectories", default=str(DEFAULT_TRAJECTORIES))
    parser.add_argument("--format", default=DEFAULT_FORMAT)
    args = parser.parse_args()
    compare_replay_evals(
        replay=args.replay,
        side=args.side,
        old_checkpoint=Path(args.old_checkpoint),
        new_checkpoint=Path(args.new_checkpoint),
        output_dir=Path(args.output_dir),
        replay_dir=Path(args.replay_dir),
        trajectories_path=Path(args.trajectories),
        format_name=args.format,
    )


if __name__ == "__main__":
    main()
