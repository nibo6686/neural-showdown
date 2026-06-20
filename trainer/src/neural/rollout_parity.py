from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .delayed_damage import run_delayed_timeline
from .end_of_turn import apply_end_of_turns
from .entry_hazards import hazard_switch_transition
from .prevention import apply_immediate_prevention


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_oracle_cases(repo_root: Path | None = None) -> Dict[str, Any]:
    root = repo_root or _repo_root()
    runner = root / "sim-core" / "dist" / "src" / "rollout_parity_oracle.js"
    if not runner.exists():
        raise FileNotFoundError(f"Build sim-core first; missing oracle runner: {runner}")
    completed = subprocess.run(
        ["node", str(runner)],
        cwd=root / "sim-core",
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(completed.stdout)


def _compare_switch_entry(case: Dict[str, Any]) -> Dict[str, Any]:
    local_input = case["local_input"]
    local = hazard_switch_transition(local_input["target"], local_input["hazards"])
    oracle = case["oracle"]
    diffs: List[Dict[str, Any]] = []

    expected_damage = float(oracle["hp_fraction_lost"])
    actual_damage = float(local["switch_hazard_damage"])
    if abs(expected_damage - actual_damage) > 0.005:
        diffs.append({"field": "hp_fraction_lost", "oracle": expected_damage, "local": actual_damage})

    expected_poison = oracle.get("status") in {"psn", "tox"}
    if expected_poison != bool(local["toxic_spikes_poison_risk"]):
        diffs.append(
            {
                "field": "toxic_spikes_poison",
                "oracle": expected_poison,
                "local": bool(local["toxic_spikes_poison_risk"]),
            }
        )

    expected_web = int(oracle.get("speed_stage") or 0) < 0
    if expected_web != bool(local["sticky_web_speed_drop"]):
        diffs.append(
            {
                "field": "sticky_web_speed_drop",
                "oracle": expected_web,
                "local": bool(local["sticky_web_speed_drop"]),
            }
        )

    return {"status": "PASS" if not diffs else "FAIL", "local": local, "diff": diffs}


def _compare_end_of_turn(case: Dict[str, Any]) -> Dict[str, Any]:
    local_input = case["local_input"]
    local = apply_end_of_turns(local_input["state"], int(local_input.get("turns", 1)))
    if not local["available"]:
        return {
            "status": "GAP",
            "local": local,
            "diff": [{"field": "transition", "oracle": case.get("oracle"), "local": local.get("reason")}],
        }

    oracle = case["oracle"]
    diffs: List[Dict[str, Any]] = []
    snapshots = local.get("snapshots", [])
    expected_snapshots = oracle.get("snapshots", [])
    if len(snapshots) != len(expected_snapshots):
        diffs.append({"field": "snapshot_count", "oracle": len(expected_snapshots), "local": len(snapshots)})
    for index, expected in enumerate(expected_snapshots):
        if index >= len(snapshots):
            break
        actual_combatants = snapshots[index].get("combatants", {})
        for side, expected_mon in expected.get("combatants", {}).items():
            actual_mon = actual_combatants.get(side, {})
            for field in ("hp", "toxic_stage"):
                if field in expected_mon and actual_mon.get(field) != expected_mon[field]:
                    diffs.append(
                        {
                            "field": f"snapshots[{index}].{side}.{field}",
                            "oracle": expected_mon[field],
                            "local": actual_mon.get(field),
                        }
                    )
    return {"status": "PASS" if not diffs else "FAIL", "local": local, "diff": diffs}


def _compare_delayed_future(case: Dict[str, Any]) -> Dict[str, Any]:
    local_input = case["local_input"]
    local = run_delayed_timeline(local_input["state"], local_input["timeline"])
    if not local["available"]:
        return {
            "status": "GAP",
            "local": local,
            "diff": [{"field": "transition", "oracle": case.get("oracle"), "local": local.get("reason")}],
        }
    oracle = case["oracle"]
    diffs: List[Dict[str, Any]] = []
    expected_snapshots = oracle.get("snapshots", [])
    snapshots = local.get("snapshots", [])
    if len(expected_snapshots) != len(snapshots):
        diffs.append({"field": "snapshot_count", "oracle": len(expected_snapshots), "local": len(snapshots)})
    for index, expected in enumerate(expected_snapshots):
        if index >= len(snapshots):
            break
        actual_slots = snapshots[index].get("active_slots", {})
        for slot, expected_target in expected.get("active_slots", {}).items():
            actual_target = actual_slots.get(slot, {})
            for field in ("pokemon_id", "hp"):
                if field in expected_target and actual_target.get(field) != expected_target[field]:
                    diffs.append(
                        {
                            "field": f"snapshots[{index}].active_slots.{slot}.{field}",
                            "oracle": expected_target[field],
                            "local": actual_target.get(field),
                        }
                    )
    expected_schedule = oracle.get("schedule_results")
    if expected_schedule is not None:
        actual_schedule = [bool(value.get("scheduled")) for value in local.get("schedule_results", [])]
        if actual_schedule != expected_schedule:
            diffs.append({"field": "schedule_results", "oracle": expected_schedule, "local": actual_schedule})
    return {"status": "PASS" if not diffs else "FAIL", "local": local, "diff": diffs}


def _compare_immediate(case: Dict[str, Any]) -> Dict[str, Any]:
    local_input = case["local_input"]
    local = apply_immediate_prevention(local_input["state"], local_input["action"])
    if not local["available"]:
        return {
            "status": "GAP",
            "local": local,
            "diff": [{"field": "transition", "oracle": case.get("oracle"), "local": local.get("reason")}],
        }

    oracle = case["oracle"]
    diffs: List[Dict[str, Any]] = []
    if "prevented" in oracle and bool(oracle["prevented"]) != bool(local["prevented"]):
        diffs.append({"field": "prevented", "oracle": bool(oracle["prevented"]), "local": bool(local["prevented"])})
    return {"status": "PASS" if not diffs else "FAIL", "local": local, "diff": diffs}


def compare_case(case: Dict[str, Any]) -> Dict[str, Any]:
    if case.get("local_support") == "supported" and case.get("phase") == "switch_entry":
        comparison = _compare_switch_entry(case)
    elif case.get("local_support") == "supported" and case.get("phase") == "end_of_turn":
        comparison = _compare_end_of_turn(case)
    elif case.get("local_support") == "supported" and case.get("phase") == "delayed_future":
        comparison = _compare_delayed_future(case)
    elif case.get("local_support") == "supported" and case.get("phase") == "immediate":
        comparison = _compare_immediate(case)
    else:
        comparison = {
            "status": "GAP",
            "local": {"available": False, "reason": case.get("gap_reason")},
            "diff": [{"field": "transition", "oracle": case.get("oracle"), "local": "unavailable"}],
        }
    return {
        "id": case["id"],
        "phase": case["phase"],
        "starting_state": case["starting_state"],
        "chosen_actions": case["chosen_actions"],
        "oracle": case["oracle"],
        **comparison,
    }


def run_harness(repo_root: Path | None = None) -> Dict[str, Any]:
    payload = load_oracle_cases(repo_root)
    cases = [compare_case(case) for case in payload["cases"]]
    counts = {name: sum(case["status"] == name for case in cases) for name in ("PASS", "FAIL", "GAP")}
    return {"oracle_source": payload["oracle"], "summary": counts, "cases": cases}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare deterministic Showdown outcomes with local approximate transitions.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_harness()
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{rendered}\n", encoding="utf-8")
    print(rendered)
    return 1 if report["summary"]["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
