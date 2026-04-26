import argparse
import gzip
import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .logging_helper import print_line_safe
from .parse_replay_logs import parse_replay_logs


DEFAULT_FORMAT = "gen9randombattle"
DEFAULT_TRAJECTORY_DIR = Path("data/replays/processed")
DEFAULT_OUTPUT_DIR = Path("data/value")
DEFAULT_REPORT_JSON = Path("artifacts/replays/value_dataset_report.json")
DEFAULT_REPORT_MD = Path("artifacts/replays/value_dataset_report.md")
FEATURE_VERSION = "public-replay-events-v1"
FEATURE_FORMAT_NOTE = (
    "Temporary replay-event feature format derived from public protocol logs; "
    "it does not match the sim-core 1179D trace feature vector yet."
)
FEATURE_NAMES = [
    "turn_norm",
    "p1_remaining_fraction",
    "p2_remaining_fraction",
    "remaining_fraction_diff_p1_minus_p2",
    "p1_active_hp_fraction",
    "p2_active_hp_fraction",
    "active_hp_diff_p1_minus_p2",
    "recent_damage_dealt_by_p1",
    "recent_damage_received_by_p1",
    "recent_damage_net_p1",
    "p1_faint_fraction",
    "p2_faint_fraction",
    "faint_fraction_diff_p2_minus_p1",
    "p1_tera_used",
    "p2_tera_used",
    "tera_diff_p1_minus_p2",
    "p1_status_fraction",
    "p2_status_fraction",
    "status_fraction_diff_p2_minus_p1",
    "p1_boost_sum_norm",
    "p2_boost_sum_norm",
    "boost_sum_diff_p1_minus_p2",
    "p1_move_count_norm",
    "p2_move_count_norm",
    "move_count_diff_p1_minus_p2",
    "p1_switch_count_norm",
    "p2_switch_count_norm",
    "switch_count_diff_p1_minus_p2",
    "turn_had_faint",
    "turn_had_tera",
    "turn_damage_volume",
]


def _load_trajectories(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not path.exists():
        return records
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if isinstance(record, dict):
                records.append(record)
    return records


def result_from_winner_side(winner_side: Optional[str], perspective: str = "p1") -> Optional[float]:
    if winner_side is None:
        return None
    if winner_side == "tie":
        return 0.0
    if winner_side == perspective:
        return 1.0
    if winner_side in ("p1", "p2"):
        return -1.0
    return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        if math.isfinite(result):
            return result
    except (TypeError, ValueError):
        pass
    return default


def _clip(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _initial_state(trajectory: Dict[str, Any]) -> Dict[str, Any]:
    teamsize = trajectory.get("teamsize") if isinstance(trajectory.get("teamsize"), dict) else {}
    return {
        "teamsize": {
            "p1": int(teamsize.get("p1", 6) or 6),
            "p2": int(teamsize.get("p2", 6) or 6),
        },
        "active_hp": {"p1": 1.0, "p2": 1.0},
        "fainted_targets": {"p1": set(), "p2": set()},
        "status_targets": {"p1": set(), "p2": set()},
        "boost_sum": {"p1": 0, "p2": 0},
        "tera_used": {"p1": 0, "p2": 0},
        "move_counts": {"p1": 0, "p2": 0},
        "switch_counts": {"p1": 0, "p2": 0},
    }


def _new_recent() -> Dict[str, Any]:
    return {
        "damage_received": {"p1": 0.0, "p2": 0.0},
        "healing": {"p1": 0.0, "p2": 0.0},
        "had_faint": 0.0,
        "had_tera": 0.0,
    }


def _remaining_fraction(state: Dict[str, Any], side: str) -> float:
    team_size = max(1, int(state["teamsize"].get(side, 6) or 6))
    fainted = len(state["fainted_targets"][side])
    return _clip((team_size - fainted) / float(team_size), 0.0, 1.0)


def _count_fraction(state: Dict[str, Any], key: str, side: str) -> float:
    team_size = max(1, int(state["teamsize"].get(side, 6) or 6))
    return _clip(len(state[key][side]) / float(team_size), 0.0, 1.0)


def _target_key(event: Dict[str, Any]) -> str:
    return str(event.get("target") or event.get("actor") or event.get("side") or "unknown")


def _apply_event(state: Dict[str, Any], recent: Dict[str, Any], event: Dict[str, Any]) -> None:
    event_type = event.get("type")
    side = event.get("side")
    if side not in ("p1", "p2"):
        return

    if event_type == "move":
        state["move_counts"][side] += 1
        return
    if event_type == "switch":
        state["switch_counts"][side] += 1
        hp_fraction = event.get("hp_fraction")
        if hp_fraction is not None:
            state["active_hp"][side] = _clip(_safe_float(hp_fraction), 0.0, 1.0)
        status = event.get("status")
        if status:
            state["status_targets"][side].add(_target_key(event))
        return
    if event_type in ("damage", "heal"):
        hp_fraction = event.get("hp_fraction")
        if hp_fraction is None:
            return
        previous = _safe_float(state["active_hp"].get(side), 1.0)
        current = _clip(_safe_float(hp_fraction), 0.0, 1.0)
        if event_type == "damage":
            recent["damage_received"][side] += max(0.0, previous - current)
        else:
            recent["healing"][side] += max(0.0, current - previous)
        state["active_hp"][side] = current
        status = event.get("status")
        if status:
            state["status_targets"][side].add(_target_key(event))
        return
    if event_type == "faint":
        state["fainted_targets"][side].add(_target_key(event))
        state["active_hp"][side] = 0.0
        recent["had_faint"] = 1.0
        return
    if event_type == "status":
        state["status_targets"][side].add(_target_key(event))
        return
    if event_type == "boost":
        state["boost_sum"][side] += int(event.get("amount", 0) or 0)
        return
    if event_type == "unboost":
        state["boost_sum"][side] -= int(event.get("amount", 0) or 0)
        return
    if event_type == "tera":
        state["tera_used"][side] = 1
        recent["had_tera"] = 1.0


def _feature_vector(state: Dict[str, Any], recent: Dict[str, Any], turn: int) -> np.ndarray:
    p1_remaining = _remaining_fraction(state, "p1")
    p2_remaining = _remaining_fraction(state, "p2")
    p1_hp = _clip(_safe_float(state["active_hp"].get("p1"), 1.0), 0.0, 1.0)
    p2_hp = _clip(_safe_float(state["active_hp"].get("p2"), 1.0), 0.0, 1.0)
    p1_faint_fraction = 1.0 - p1_remaining
    p2_faint_fraction = 1.0 - p2_remaining
    p1_status = _count_fraction(state, "status_targets", "p1")
    p2_status = _count_fraction(state, "status_targets", "p2")
    p1_damage_received = _clip(float(recent["damage_received"]["p1"]), 0.0, 1.0)
    p2_damage_received = _clip(float(recent["damage_received"]["p2"]), 0.0, 1.0)
    p1_damage_dealt = p2_damage_received
    p1_moves = min(1.0, state["move_counts"]["p1"] / 100.0)
    p2_moves = min(1.0, state["move_counts"]["p2"] / 100.0)
    p1_switches = min(1.0, state["switch_counts"]["p1"] / 50.0)
    p2_switches = min(1.0, state["switch_counts"]["p2"] / 50.0)
    p1_boost = _clip(state["boost_sum"]["p1"] / 36.0)
    p2_boost = _clip(state["boost_sum"]["p2"] / 36.0)
    values = [
        min(1.0, max(0.0, float(turn) / 100.0)),
        p1_remaining,
        p2_remaining,
        p1_remaining - p2_remaining,
        p1_hp,
        p2_hp,
        p1_hp - p2_hp,
        p1_damage_dealt,
        p1_damage_received,
        p1_damage_dealt - p1_damage_received,
        p1_faint_fraction,
        p2_faint_fraction,
        p2_faint_fraction - p1_faint_fraction,
        float(state["tera_used"]["p1"]),
        float(state["tera_used"]["p2"]),
        float(state["tera_used"]["p1"] - state["tera_used"]["p2"]),
        p1_status,
        p2_status,
        p2_status - p1_status,
        p1_boost,
        p2_boost,
        p1_boost - p2_boost,
        p1_moves,
        p2_moves,
        p1_moves - p2_moves,
        p1_switches,
        p2_switches,
        p1_switches - p2_switches,
        float(recent["had_faint"]),
        float(recent["had_tera"]),
        _clip(p1_damage_received + p2_damage_received, 0.0, 1.0),
    ]
    return np.asarray(values, dtype=np.float32)


def examples_from_trajectory(trajectory: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    p1_result = result_from_winner_side(trajectory.get("winner_side"), perspective="p1")
    if p1_result is None:
        return [], "missing_or_unknown_winner"
    turns = trajectory.get("turns")
    if not isinstance(turns, list) or not turns:
        return [], "no_turn_events"

    state = _initial_state(trajectory)
    examples: List[Dict[str, Any]] = []
    for turn_record in sorted(turns, key=lambda item: int(item.get("turn", 0) or 0)):
        turn_number = int(turn_record.get("turn", 0) or 0)
        recent = _new_recent()
        events = turn_record.get("events") if isinstance(turn_record.get("events"), list) else []
        for event in events:
            if isinstance(event, dict):
                _apply_event(state, recent, event)
        features = _feature_vector(state, recent, turn_number)
        examples.append(
            {
                "state": features,
                "value_target": float(p1_result),
                "final_result": float(p1_result),
                "turn": turn_number,
                "replay_id": str(trajectory.get("replay_id") or ""),
                "format": str(trajectory.get("format") or ""),
                "metadata_json": json.dumps(
                    {
                        "replay_id": trajectory.get("replay_id"),
                        "format": trajectory.get("format"),
                        "turn": turn_number,
                        "winner": trajectory.get("winner"),
                        "winner_side": trajectory.get("winner_side"),
                        "feature_version": FEATURE_VERSION,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
        )
    return examples, None


def _ensure_trajectories(format_name: str, replay_dir: Path, trajectories_path: Path) -> None:
    if trajectories_path.exists():
        return
    if replay_dir.exists() and list(replay_dir.glob("*.log")):
        parse_replay_logs(format_name=format_name, replay_dir=replay_dir, output_path=trajectories_path)


def _stack_examples(examples: Sequence[Dict[str, Any]]) -> Dict[str, np.ndarray]:
    if not examples:
        raise ValueError("No public replay value examples were produced.")
    return {
        "states": np.asarray([example["state"] for example in examples], dtype=np.float32),
        "legal_masks": np.zeros((len(examples), 13), dtype=np.float32),
        "value_targets": np.asarray([example["value_target"] for example in examples], dtype=np.float32),
        "final_results": np.asarray([example["final_result"] for example in examples], dtype=np.float32),
        "turns": np.asarray([example["turn"] for example in examples], dtype=np.int64),
        "chosen_action_indices": np.full((len(examples),), -1, dtype=np.int64),
        "replay_ids": np.asarray([example["replay_id"] for example in examples]),
        "formats": np.asarray([example["format"] for example in examples]),
        "metadata_json": np.asarray([example["metadata_json"] for example in examples]),
    }


def build_public_replay_value_dataset(
    *,
    format_name: str = DEFAULT_FORMAT,
    replay_dir: Optional[Path] = None,
    trajectories_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    report_json_path: Path = DEFAULT_REPORT_JSON,
    report_md_path: Path = DEFAULT_REPORT_MD,
) -> Dict[str, Any]:
    selected_replay_dir = replay_dir or Path("data/replays/raw") / format_name
    selected_trajectories = trajectories_path or DEFAULT_TRAJECTORY_DIR / f"{format_name}_trajectories.jsonl.gz"
    selected_output = output_path or DEFAULT_OUTPUT_DIR / f"{format_name}_public_replay_value.npz"
    started_at = time.perf_counter()
    _ensure_trajectories(format_name, selected_replay_dir, selected_trajectories)
    trajectories = _load_trajectories(selected_trajectories)

    examples: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    p1_outcomes: Counter[str] = Counter()
    skip_reasons: Counter[str] = Counter()
    turn_counts: List[int] = []
    for trajectory in trajectories:
        winner_side = trajectory.get("winner_side")
        p1_result = result_from_winner_side(winner_side, perspective="p1")
        if p1_result is None:
            p1_outcomes["unknown"] += 1
        elif p1_result > 0:
            p1_outcomes["win"] += 1
        elif p1_result < 0:
            p1_outcomes["loss"] += 1
        else:
            p1_outcomes["tie"] += 1

        source_examples, skip_reason = examples_from_trajectory(trajectory)
        if skip_reason:
            skip_reasons[skip_reason] += 1
            skipped.append({"replay_id": trajectory.get("replay_id"), "reason": skip_reason})
            continue
        turn_count = len(trajectory.get("turns", []))
        turn_counts.append(turn_count)
        examples.extend(source_examples)

    arrays = _stack_examples(examples)
    selected_output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        selected_output,
        **arrays,
        feature_names=np.asarray(FEATURE_NAMES),
        feature_version=np.asarray(FEATURE_VERSION),
        feature_format_note=np.asarray(FEATURE_FORMAT_NOTE),
    )

    targets = arrays["value_targets"]

    # Calculate turn statistics
    turn_stats = {}
    if turn_counts:
        sorted_turns = sorted(turn_counts)
        turn_stats = {
            "min": int(min(turn_counts)),
            "max": int(max(turn_counts)),
            "median": int(sorted_turns[len(sorted_turns) // 2]),
            "mean": float(np.mean(turn_counts)),
        }

    report = {
        "format": format_name,
        "feature_format": FEATURE_FORMAT_NOTE,
        "feature_version": FEATURE_VERSION,
        "feature_dim": int(arrays["states"].shape[1]),
        "feature_names": FEATURE_NAMES,
        "replays": int(len(trajectories)),
        "parsed_battles": int(len(trajectories)),
        "examples": int(arrays["states"].shape[0]),
        "p1_outcomes": dict(p1_outcomes),
        "turn_statistics": turn_stats,
        "target_distribution": {
            "mean": float(targets.mean()),
            "std": float(targets.std()),
            "min": float(targets.min()),
            "max": float(targets.max()),
            "positive": int((targets > 0).sum()),
            "negative": int((targets < 0).sum()),
            "zero": int((targets == 0).sum()),
        },
        "skip_reasons": dict(skip_reasons),
        "skipped_failed_replays": skipped,
        "skipped_failed_count": int(len(skipped)),
        "replay_dir": str(selected_replay_dir),
        "trajectories_path": str(selected_trajectories),
        "output_path": str(selected_output),
        "wall_time_sec": time.perf_counter() - started_at,
    }
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md_path.write_text(_format_markdown_report(report), encoding="utf-8")
    print_line_safe(
        f"build-replay-value-dataset done | format={format_name} replays={len(trajectories)} "
        f"examples={arrays['states'].shape[0]} feature_dim={arrays['states'].shape[1]} output={selected_output}"
    )
    return report


def _format_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Public Replay Value Dataset Report",
        "",
        f"- Format: {report['format']}",
        f"- Replays: {report['replays']}",
        f"- Parsed battles: {report['parsed_battles']}",
        f"- Examples: {report['examples']}",
        f"- Feature dimension: {report['feature_dim']}",
        f"- Feature version: {report['feature_version']}",
        f"- Feature format: {report['feature_format']}",
        "",
        "## P1 Outcomes",
        "",
    ]
    for key in ("win", "loss", "tie", "unknown"):
        lines.append(f"- {key}: {report.get('p1_outcomes', {}).get(key, 0)}")

    # Turn statistics
    if report.get("turn_statistics"):
        turn_stats = report["turn_statistics"]
        lines.extend(
            [
                "",
                "## Turn Statistics",
                "",
                f"- Min: {turn_stats.get('min', 'N/A')}",
                f"- Max: {turn_stats.get('max', 'N/A')}",
                f"- Median: {turn_stats.get('median', 'N/A')}",
                f"- Mean: {turn_stats.get('mean', 'N/A'):.1f}",
            ]
        )

    dist = report["target_distribution"]
    lines.extend(
        [
            "",
            "## Targets",
            "",
            f"- Mean/std: {dist['mean']:.4f} / {dist['std']:.4f}",
            f"- Positive/negative/zero examples: {dist['positive']} / {dist['negative']} / {dist['zero']}",
        ]
    )

    # Skip reasons
    if report.get("skip_reasons"):
        lines.append("")
        lines.append("## Skip Reasons")
        lines.append("")
        for reason, count in sorted(report["skip_reasons"].items(), key=lambda x: -x[1]):
            lines.append(f"- {reason}: {count}")

    lines.extend(
        [
            "",
            f"Output: `{report['output_path']}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build event-derived value examples from public replay trajectories.")
    parser.add_argument("--format", default=DEFAULT_FORMAT, help="Pokemon Showdown format id.")
    parser.add_argument("--replay-dir", default=None, help="Raw replay directory used to auto-parse logs if needed.")
    parser.add_argument("--trajectories", default=None, help="Parsed replay trajectories JSONL.GZ path.")
    parser.add_argument("--output", default=None, help="Output NPZ path.")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON), help="Value dataset JSON report path.")
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD), help="Value dataset Markdown report path.")
    args = parser.parse_args()

    build_public_replay_value_dataset(
        format_name=args.format,
        replay_dir=Path(args.replay_dir) if args.replay_dir else None,
        trajectories_path=Path(args.trajectories) if args.trajectories else None,
        output_path=Path(args.output) if args.output else None,
        report_json_path=Path(args.report_json),
        report_md_path=Path(args.report_md),
    )


if __name__ == "__main__":
    main()
