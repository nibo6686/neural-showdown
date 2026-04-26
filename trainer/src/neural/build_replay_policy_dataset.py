import argparse
import gzip
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .action_mapper import TrajectoryActionMapper
from .build_replay_value_dataset import (
    FEATURE_NAMES,
    FEATURE_VERSION,
    _apply_event,
    _ensure_trajectories,
    _feature_vector,
    _initial_state,
    _load_trajectories,
    _new_recent,
    result_from_winner_side,
)
from .logging_helper import print_line_safe


DEFAULT_FORMAT = "gen9randombattle"
DEFAULT_OUTPUT_DIR = Path("data/replays/processed")
DEFAULT_REPORT_JSON = Path("artifacts/replays/policy_dataset_report.json")
DEFAULT_REPORT_MD = Path("artifacts/replays/policy_dataset_report.md")


def _rating_from_trajectory(trajectory: Dict[str, Any]) -> Optional[Any]:
    metadata = trajectory.get("metadata")
    if isinstance(metadata, dict):
        return metadata.get("rating")
    return None


def _action_label(event: Dict[str, Any]) -> str:
    if event.get("type") == "move":
        return f"move:{event.get('move')}"
    if event.get("type") == "switch":
        return f"switch:{event.get('details')}"
    return str(event.get("type") or "unknown")


def examples_from_policy_trajectory(trajectory: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    winner_side = trajectory.get("winner_side")
    turns = trajectory.get("turns")
    if winner_side is None or not isinstance(turns, list):
        return [], None

    state = _initial_state(trajectory)
    mapper = TrajectoryActionMapper()
    examples: List[Dict[str, Any]] = []
    rating = _rating_from_trajectory(trajectory)
    players = trajectory.get("players") if isinstance(trajectory.get("players"), dict) else {}

    for turn_record in sorted(turns, key=lambda item: int(item.get("turn", 0) or 0)):
        turn_number = int(turn_record.get("turn", 0) or 0)
        recent = _new_recent()
        events = turn_record.get("events") if isinstance(turn_record.get("events"), list) else []

        # First pass: track state and collect actions
        mapper.track_events_in_turn(events)

        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = event.get("type")
            side = event.get("side")
            if event_type in ("move", "switch") and side in ("p1", "p2"):
                result = result_from_winner_side(winner_side, perspective=side)
                context = _feature_vector(state, recent, turn_number)
                action_label = _action_label(event)

                actor_str = None
                if event_type == "move":
                    actor_str = event.get("actor")

                mapping_result = mapper.map_action(action_label, side, actor_str=actor_str)

                example = {
                    "source": "public_pokemon_showdown_replay",
                    "replay_id": trajectory.get("replay_id"),
                    "format": trajectory.get("format"),
                    "turn": turn_number,
                    "perspective": side,
                    "player": players.get(side),
                    "selected_action_label": action_label,
                    "action_type": event_type,
                    "actor": event.get("actor"),
                    "target": event.get("target"),
                    "details": event.get("details"),
                    "raw": event.get("raw"),
                    "mapped_action_index": mapping_result.get("mapped_slot_index"),
                    "mapped_to_fixed_head": mapping_result.get("mapped", False),
                    "mapping_confidence": mapping_result.get("confidence", 0.0),
                    "mapping_type": mapping_result.get("mapping_type"),
                    "mapping_failure_reason": mapping_result.get("failure_reason"),
                    "final_result": result,
                    "rating": rating,
                    "public_context": {
                        "feature_version": FEATURE_VERSION,
                        "feature_names": FEATURE_NAMES,
                        "feature_values": context.astype(float).tolist(),
                    },
                }
                examples.append(example)
            _apply_event(state, recent, event)

    return examples, None


def build_public_replay_policy_dataset(
    *,
    format_name: str = DEFAULT_FORMAT,
    replay_dir: Optional[Path] = None,
    trajectories_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    report_json_path: Path = DEFAULT_REPORT_JSON,
    report_md_path: Path = DEFAULT_REPORT_MD,
) -> Dict[str, Any]:
    selected_replay_dir = replay_dir or Path("data/replays/raw") / format_name
    selected_trajectories = trajectories_path or DEFAULT_OUTPUT_DIR / f"{format_name}_trajectories.jsonl.gz"
    selected_output = output_path or DEFAULT_OUTPUT_DIR / f"{format_name}_public_policy.jsonl.gz"
    started_at = time.perf_counter()
    _ensure_trajectories(format_name, selected_replay_dir, selected_trajectories)
    trajectories = _load_trajectories(selected_trajectories)
    selected_output.parent.mkdir(parents=True, exist_ok=True)

    action_counts: Counter[str] = Counter()
    perspective_counts: Counter[str] = Counter()
    mapping_type_counts: Counter[str] = Counter()
    failure_reasons: Counter[str] = Counter()
    skipped: List[Dict[str, Any]] = []
    total_examples = 0
    mapped_examples = 0

    with gzip.open(selected_output, "wt", encoding="utf-8") as handle:
        for trajectory in trajectories:
            source_examples, _ = examples_from_policy_trajectory(trajectory)
            if not source_examples:
                skipped.append({"replay_id": trajectory.get("replay_id"), "reason": "no_policy_actions_or_missing_winner"})
                continue
            for example in source_examples:
                handle.write(json.dumps(example, sort_keys=True) + "\n")
                total_examples += 1
                action_counts[str(example.get("action_type"))] += 1
                perspective_counts[str(example.get("perspective"))] += 1

                # Track mapping statistics
                if example.get("mapped_to_fixed_head", False):
                    mapped_examples += 1
                    mapping_type_counts["mapped"] = mapping_type_counts.get("mapped", 0) + 1
                    map_type = example.get("mapping_type")
                    if map_type:
                        mapping_type_counts[map_type] = mapping_type_counts.get(map_type, 0) + 1
                else:
                    mapping_type_counts["unmapped"] = mapping_type_counts.get("unmapped", 0) + 1
                    reason = example.get("mapping_failure_reason", "unknown_reason")
                    failure_reasons[reason] += 1

    mapped_pct = (100.0 * mapped_examples / total_examples) if total_examples > 0 else 0.0
    report = {
        "format": format_name,
        "trajectories_path": str(selected_trajectories),
        "output_path": str(selected_output),
        "replays": int(len(trajectories)),
        "examples": int(total_examples),
        "action_counts": dict(action_counts),
        "perspective_counts": dict(perspective_counts),
        "mapped_examples": int(mapped_examples),
        "unmapped_examples": int(total_examples - mapped_examples),
        "mapped_action_percentage": float(mapped_pct),
        "mapping_type_counts": dict(mapping_type_counts),
        "mapping_failure_reasons": dict(failure_reasons),
        "mapping_status": f"{mapped_pct:.1f}% of actions mapped to fixed 13-action head",
        "skipped_failed_replays": skipped,
        "skipped_failed_count": int(len(skipped)),
        "wall_time_sec": time.perf_counter() - started_at,
    }
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md_path.write_text(_format_markdown_report(report), encoding="utf-8")
    print_line_safe(
        f"build-replay-policy-dataset done | format={format_name} replays={len(trajectories)} "
        f"examples={total_examples} mapped_pct={mapped_pct:.1f} output={selected_output}"
    )
    return report


def _format_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Public Replay Policy Dataset Report",
        "",
        f"- Format: {report['format']}",
        f"- Replays: {report['replays']}",
        f"- Examples: {report['examples']}",
        f"- Mapped actions: {report['mapped_action_percentage']:.1f}%",
        f"- Mapping status: {report['mapping_status']}",
        "",
        "## Actions",
        "",
    ]
    for key, value in sorted(report.get("action_counts", {}).items()):
        lines.append(f"- {key}: {value}")

    # Mapping type breakdown
    if report.get("mapping_type_counts"):
        lines.extend(["", "## Mapping Types", ""])
        for map_type, count in sorted(report["mapping_type_counts"].items(), key=lambda x: -x[1]):
            lines.append(f"- {map_type}: {count}")

    # Mapping failure reasons
    if report.get("mapping_failure_reasons"):
        lines.extend(["", "## Mapping Failure Reasons", ""])
        for reason, count in sorted(report["mapping_failure_reasons"].items(), key=lambda x: -x[1])[:10]:
            lines.append(f"- {reason}: {count}")

    lines.extend(["", f"Output: `{report['output_path']}`", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build public replay policy/action examples from parsed trajectories.")
    parser.add_argument("--format", default=DEFAULT_FORMAT, help="Pokemon Showdown format id.")
    parser.add_argument("--replay-dir", default=None, help="Raw replay directory used to auto-parse logs if needed.")
    parser.add_argument("--trajectories", default=None, help="Parsed replay trajectories JSONL.GZ path.")
    parser.add_argument("--output", default=None, help="Output policy JSONL.GZ path.")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON), help="Policy dataset JSON report path.")
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD), help="Policy dataset Markdown report path.")
    args = parser.parse_args()

    build_public_replay_policy_dataset(
        format_name=args.format,
        replay_dir=Path(args.replay_dir) if args.replay_dir else None,
        trajectories_path=Path(args.trajectories) if args.trajectories else None,
        output_path=Path(args.output) if args.output else None,
        report_json_path=Path(args.report_json),
        report_md_path=Path(args.report_md),
    )


if __name__ == "__main__":
    main()
