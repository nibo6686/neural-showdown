"""Read-only audit for vNext diagnostic unmatched action rows.

The materializer records two related audit streams:

* ``decision_skip_audit.jsonl`` is authoritative for labels excluded from the
  final action-rank dataset.
* ``materialization_report.json["unmatched_action_audit"]`` also keeps legacy
  rows that were fixed by later exact-prefix reconstruction.

This helper reports both, but all "residual" counts are based on
``decision_skip_audit.jsonl`` rows whose reason is
``chosen_action_unmatched_for_action_rank``.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _raw_command(row: Dict[str, Any]) -> str:
    return str(row.get("raw_replay_command") or "")


def _raw_kind(raw: str) -> str:
    parts = raw.split("|")
    return parts[1] if len(parts) > 1 else ""


def _active_species(raw: str) -> str:
    parts = raw.split("|")
    if len(parts) <= 2:
        return ""
    ident = parts[2]
    return ident.split(": ", 1)[1] if ": " in ident else ident


def _move_name(raw: str) -> str:
    parts = raw.split("|")
    return parts[3] if len(parts) > 3 and _raw_kind(raw) == "move" else ""


def _switch_species(raw: str) -> str:
    parts = raw.split("|")
    if len(parts) > 3 and _raw_kind(raw) in {"switch", "drag"}:
        return parts[3].split(",", 1)[0]
    return ""


def _parsed_action_type(row: Dict[str, Any]) -> str:
    parsed = str(row.get("parsed_command") or "")
    return parsed.split(":", 1)[0] if ":" in parsed else parsed


def _candidate_class(row: Dict[str, Any]) -> str:
    candidates = [str(item) for item in row.get("candidates") or []]
    has_move = any(item.startswith("move") for item in candidates)
    has_switch = any(item.startswith("switch") for item in candidates)
    if not candidates:
        return "no_candidates"
    if has_move and has_switch:
        return "move_and_switch_candidates"
    if has_move:
        return "move_only_candidates"
    if has_switch:
        return "switch_only_candidates"
    return "other_candidates"


def _turn_bucket(turn: int) -> str:
    if turn <= 10:
        return "early_1_10"
    if turn <= 40:
        return "mid_11_40"
    return "late_41_plus"


def _counter_dict(counter: Counter) -> Dict[str, int]:
    return {str(key): int(value) for key, value in counter.items()}


def _top(counter: Counter, n: int) -> List[Dict[str, Any]]:
    return [{"key": key, "count": int(value)} for key, value in counter.most_common(n)]


def _sample(rows: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    fields = ("replay_id", "turn", "side", "detail", "parsed_command", "raw_replay_command", "candidates")
    return [{field: row.get(field) for field in fields if field in row} for row in rows[:n]]


def audit_dataset(dataset_dir: Path, *, top_n: int = 20) -> Dict[str, Any]:
    report = _load_json(dataset_dir / "materialization_report.json")
    selected_splits = report.get("selected_splits") or {}
    skip_rows = [
        row
        for row in _jsonl(dataset_dir / "decision_skip_audit.jsonl")
        if row.get("reason") == "chosen_action_unmatched_for_action_rank"
    ]
    legacy_rows = report.get("unmatched_action_audit") or []

    split_counter = Counter(str(selected_splits.get(row.get("replay_id"), "unknown")) for row in skip_rows)
    detail_counter = Counter(str(row.get("detail") or "") for row in skip_rows)
    action_counter = Counter(_parsed_action_type(row) for row in skip_rows)
    raw_kind_counter = Counter(_raw_kind(_raw_command(row)) for row in skip_rows)
    candidate_class_counter = Counter((str(row.get("detail") or ""), _candidate_class(row)) for row in skip_rows)
    turn_bucket_counter = Counter(_turn_bucket(int(row.get("turn") or 0)) for row in skip_rows)
    replay_counter = Counter(str(row.get("replay_id") or "") for row in skip_rows)
    split_detail_counter = Counter(
        (str(selected_splits.get(row.get("replay_id"), "unknown")), str(row.get("detail") or ""))
        for row in skip_rows
    )
    exact_candidate_count = sum(
        str(row.get("parsed_command") or "") in [str(item) for item in row.get("candidates") or []]
        for row in skip_rows
    )

    move_rows = [row for row in skip_rows if row.get("detail") == "move_missing_from_reconstructed_active_moves"]
    switch_rows = [row for row in skip_rows if row.get("detail") == "switch_target_missing_from_pre_action_legal_roster"]

    legacy_replacement = [
        row for row in legacy_rows if row.get("replay_id") == "gen9randombattle-2591433931"
    ]
    legacy_replacement_counter = Counter(
        (
            str(row.get("after_fix_matched")),
            str(row.get("after_fix_reason")),
            str(row.get("fix_classification")),
        )
        for row in legacy_replacement
    )

    return {
        "dataset_dir": str(dataset_dir),
        "dataset_npz": str(next(dataset_dir.glob("*.npz"), "")),
        "total_decision_states": int(report.get("decision_states", 0) or 0),
        "matched_count": int(report.get("chosen_action_matched_count", 0) or 0),
        "unmatched_count": len(skip_rows),
        "reported_unmatched_count": int(report.get("chosen_action_unmatched_count", 0) or 0),
        "match_rate": float(report.get("chosen_action_match_rate", 0.0) or 0.0),
        "split_distribution": _counter_dict(split_counter),
        "detail_distribution": _counter_dict(detail_counter),
        "action_type_distribution": _counter_dict(action_counter),
        "raw_command_distribution": _counter_dict(raw_kind_counter),
        "turn_bucket_distribution": _counter_dict(turn_bucket_counter),
        "candidate_class_by_detail": _counter_dict(candidate_class_counter),
        "split_detail_distribution": _counter_dict(split_detail_counter),
        "exact_parsed_action_present_in_candidates": int(exact_candidate_count),
        "top_replays": _top(replay_counter, top_n),
        "top_missing_moves": _top(Counter(_move_name(_raw_command(row)) for row in move_rows), top_n),
        "top_move_species": _top(Counter(_active_species(_raw_command(row)) for row in move_rows), top_n),
        "top_species_move_pairs": _top(
            Counter((_active_species(_raw_command(row)), _move_name(_raw_command(row))) for row in move_rows),
            top_n,
        ),
        "top_switch_targets": _top(
            Counter((_switch_species(_raw_command(row)), _raw_kind(_raw_command(row))) for row in switch_rows),
            top_n,
        ),
        "mechanic_markers": {
            "pivot_or_from_switch_rows": sum("[from]" in _raw_command(row) for row in skip_rows),
            "pivot_named_rows": sum(
                "[from]" in _raw_command(row)
                and any(name in _raw_command(row) for name in ("Flip Turn", "U-turn", "Volt Switch", "Chilly Reception"))
                for row in skip_rows
            ),
            "drag_rows": sum("|drag|" in _raw_command(row) for row in skip_rows),
            "raw_tera_marker_rows": sum("tera:" in _raw_command(row) or "|-terastallize|" in _raw_command(row) for row in skip_rows),
            "struggle_rows": sum("Struggle" in _raw_command(row) for row in skip_rows),
            "illusion_marker_rows": sum("Illusion" in _raw_command(row) or "Zoroark" in _raw_command(row) for row in skip_rows),
        },
        "replacement_replay": {
            "replay_id": "gen9randombattle-2591433931",
            "residual_unmatched_count": int(replay_counter.get("gen9randombattle-2591433931", 0)),
            "legacy_audit_rows": len(legacy_replacement),
            "legacy_audit_classification": _counter_dict(legacy_replacement_counter),
            "residual_samples": _sample(
                [row for row in skip_rows if row.get("replay_id") == "gen9randombattle-2591433931"],
                5,
            ),
        },
        "samples": {
            "move_missing": _sample(move_rows, 8),
            "switch_target_missing": _sample(switch_rows, 8),
            "switch_only_move_commands": _sample(
                [row for row in move_rows if _candidate_class(row) == "switch_only_candidates"],
                8,
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset_dir",
        nargs="?",
        default="artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected",
        type=Path,
    )
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(audit_dataset(args.dataset_dir, top_n=args.top), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
