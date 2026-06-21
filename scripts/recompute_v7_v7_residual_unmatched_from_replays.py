"""Read-only recomputation of the documented v7/v7 residual unmatched cases.

This harness makes the residual-unmatched analysis reproducible. It does **not**
run full materialization and does **not** modify any dataset files. It recomputes
the legal candidate list for each documented decision directly from the raw
replay logs under ``data/replays/raw/gen9randombattle/`` using the same API the
regression tests use:

* ``parse_protocol_log``
* ``_completed_teams_for_action_reconstruction``
* ``_trajectory_prefix_before_event``
* ``_context_for_prefix``
* ``_legal_actions_from_private_state``
* ``match_chosen_action``

The case list mirrors the "Remaining 8 Rows" table in
``artifacts/training_plan/residual_34_unmatched_case_triage_report.md``. After the
Ditto/Imposter Transform reconstruction fix, the Ditto case is expected to match
and 7 residual cases are expected to remain unmatched.

Usage::

    $env:PYTHONPATH = (Resolve-Path .\\trainer\\src)
    & $py scripts\\recompute_v7_v7_residual_unmatched_from_replays.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from neural.benchmark_vnext_featuregen import (
    _completed_teams_for_action_reconstruction,
    _context_for_prefix,
    _trajectory_prefix_before_event,
)
from neural.build_action_rank_dataset import _legal_actions_from_private_state
from neural.parse_replay_logs import parse_protocol_log
from neural.vnext_labels import chosen_action_label, match_chosen_action


DEFAULT_REPLAY_DIR = Path("data/replays/raw/gen9randombattle")

# Documented cases from residual_34_unmatched_case_triage_report.md.
# kind: "move" matches on the move name; "switch" matches on the target species.
# expected_matched reflects the post-Ditto-fix expectation.
CASES: List[Dict[str, Any]] = [
    {
        "replay": "gen9randombattle-2589571474", "turn": 20, "side": "p1",
        "kind": "move", "key": "Thunder Wave",
        "category": "transform_reconstruction_fixed", "expected_matched": True,
    },
    {
        "replay": "gen9randombattle-2591469202", "turn": 1, "side": "p2",
        "kind": "move", "key": "Sludge Bomb",
        "category": "no_leakage_illusion", "expected_matched": False,
    },
    {
        "replay": "gen9randombattle-2593348981", "turn": 1, "side": "p1",
        "kind": "move", "key": "Will-O-Wisp",
        "category": "no_leakage_illusion", "expected_matched": False,
    },
    {
        "replay": "gen9randombattle-2593348981", "turn": 6, "side": "p1",
        "kind": "move", "key": "Will-O-Wisp",
        "category": "no_leakage_illusion", "expected_matched": False,
    },
    {
        "replay": "gen9randombattle-2593348981", "turn": 18, "side": "p1",
        "kind": "move", "key": "Will-O-Wisp",
        "category": "no_leakage_illusion", "expected_matched": False,
    },
    {
        "replay": "gen9randombattle-2591404793", "turn": 21, "side": "p1",
        "kind": "switch", "key": "Houndstone",
        "category": "illusion_duplicate_artifact", "expected_matched": False,
    },
    {
        "replay": "gen9randombattle-2591404793", "turn": 23, "side": "p1",
        "kind": "switch", "key": "Houndstone",
        "category": "illusion_duplicate_artifact", "expected_matched": False,
    },
    {
        "replay": "gen9randombattle-2591404793", "turn": 25, "side": "p1",
        "kind": "switch", "key": "Houndstone",
        "category": "illusion_duplicate_artifact", "expected_matched": False,
    },
]


def _event_matches(event: Dict[str, Any], side: str, kind: str, key: str) -> bool:
    if event.get("side") != side or event.get("type") != kind:
        return False
    if kind == "move":
        return event.get("move") == key
    if kind == "switch":
        details = str(event.get("details") or "")
        return details.split(",", 1)[0].strip() == key
    return False


def recompute_case(case: Dict[str, Any], replay_dir: Path) -> Dict[str, Any]:
    replay_id = case["replay"]
    path = replay_dir / f"{replay_id}.log"
    trajectory = parse_protocol_log(
        path.read_text(encoding="utf-8").splitlines(),
        replay_id=replay_id,
        source_path=str(path),
    )
    completed = _completed_teams_for_action_reconstruction(trajectory)
    for turn in trajectory["turns"]:
        if int(turn["turn"]) != case["turn"]:
            continue
        events = turn.get("events", [])
        for event in events:
            if not _event_matches(event, case["side"], case["kind"], case["key"]):
                continue
            prefix = _trajectory_prefix_before_event(
                trajectory=trajectory, turn_number=case["turn"], event=event, turn_events=events,
            )
            _, private_state, _, _ = _context_for_prefix(
                trajectory=trajectory, prefix=prefix, side=case["side"],
                through_turn=case["turn"], completed_teams=completed, sets_path=None,
            )
            actions = _legal_actions_from_private_state(private_state, "")
            label = chosen_action_label(event, turn_events=events)
            matched = match_chosen_action(actions, label) is not None
            return {
                "replay": replay_id, "turn": case["turn"], "side": case["side"],
                "action": label, "category": case["category"],
                "matched": matched, "expected_matched": case["expected_matched"],
                "as_expected": matched == case["expected_matched"],
            }
    return {
        "replay": replay_id, "turn": case["turn"], "side": case["side"],
        "action": f"{case['kind']}: {case['key']}", "category": case["category"],
        "matched": None, "expected_matched": case["expected_matched"],
        "as_expected": False, "error": "decision_not_found",
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-dir", type=Path, default=DEFAULT_REPLAY_DIR)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    args = parser.parse_args(argv)

    rows = [recompute_case(case, args.replay_dir) for case in CASES]
    matched = sum(1 for row in rows if row.get("matched") is True)
    unmatched = sum(1 for row in rows if row.get("matched") is False)
    categories: Dict[str, int] = {}
    for row in rows:
        categories[row["category"]] = categories.get(row["category"], 0) + 1

    summary = {
        "total_cases": len(rows),
        "matched": matched,
        "unmatched": unmatched,
        "category_summary": categories,
        "all_as_expected": all(row.get("as_expected") for row in rows),
        "rows": rows,
    }

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["all_as_expected"] else 1

    print("v7/v7 residual unmatched recomputation (read-only, no materialization)")
    print(f"replay_dir: {args.replay_dir}")
    print("-" * 78)
    print(f"{'replay':<30}{'turn':>5}  {'side':<4}{'action':<22}{'category':<28}{'matched'}")
    for row in rows:
        print(
            f"{row['replay']:<30}{row['turn']:>5}  {row['side']:<4}"
            f"{str(row['action']):<22}{row['category']:<28}{row['matched']}"
        )
    print("-" * 78)
    print(f"total cases checked : {summary['total_cases']}")
    print(f"matched             : {matched}")
    print(f"unmatched           : {unmatched}")
    print(f"category summary    : {categories}")
    print(f"all as expected     : {summary['all_as_expected']}")
    return 0 if summary["all_as_expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
