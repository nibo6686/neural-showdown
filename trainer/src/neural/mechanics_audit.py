import argparse
import json
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

from .action_features import ACTION_FEATURE_DIM, ACTION_FEATURE_VERSION
from .live_private_features import FEATURE_DIM, FEATURE_VERSION
from .logging_helper import print_line_safe


CATEGORIES = {
    "restrictions": [
        "test_disabled_zero_pp_trapped_and_force_switch_are_respected",
        "test_disabled_and_zero_pp_moves_are_not_recommended",
        "test_taunt_encore_choice_and_locked_move_are_exposed_as_restrictions",
    ],
    "speed/order": ["test_priority_and_trick_room_speed_diagnostics"],
    "damage": ["test_damage_diagnostics_rank_effective_ko_and_burn_penalty", "test_tera_boosted_ko_can_outrank_non_tera"],
    "abilities": ["test_ability_based_blockers_are_flagged", "test_prankster_status_into_dark_is_blocked"],
    "items": ["test_focus_sash_eviolite_life_orb_and_leftovers_are_represented"],
    "hazards/switches": ["test_hazard_switch_diagnostics_cover_boots_grounding_and_faint_risk"],
    "field durations": ["test_field_duration_snapshots_track_start_end_and_remaining"],
    "PP": ["test_public_pp_is_inferred_not_exact"],
    "opponent set consistency": ["test_opponent_belief_filters_and_relaxes_with_warning"],
    "Tera": ["test_tera_boosted_ko_can_outrank_non_tera"],
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _iter_tests(suite: unittest.TestSuite) -> List[unittest.case.TestCase]:
    tests: List[unittest.case.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            tests.extend(_iter_tests(item))
        else:
            tests.append(item)
    return tests


def run_audit() -> Dict[str, Any]:
    root = _repo_root()
    loader = unittest.TestLoader()
    suite = loader.discover(str(root / "trainer" / "tests"), pattern="test_mechanics_audit.py")
    tests = _iter_tests(suite)
    started = time.time()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    elapsed = time.time() - started
    failed_names = {failure[0]._testMethodName for failure in [*result.failures, *result.errors]}
    all_names = {test._testMethodName for test in tests}
    categories = {}
    for category, names in CATEGORIES.items():
        category_names = set(names)
        categories[category] = {
            "tests": sorted(category_names),
            "covered": bool(category_names & all_names),
            "passed": not bool(category_names & failed_names),
        }
    return {
        "ok": result.wasSuccessful(),
        "tests_run": int(result.testsRun),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "elapsed_sec": round(elapsed, 3),
        "categories": categories,
        "feature_dimensions": {
            "live_private_feature_version": FEATURE_VERSION,
            "live_private_feature_dim": FEATURE_DIM,
            "action_feature_version": ACTION_FEATURE_VERSION,
            "action_feature_dim": ACTION_FEATURE_DIM,
        },
        "notes": [
            "No datasets were rebuilt.",
            "No checkpoints were trained.",
            "Approximate evaluator diagnostics are sanity estimates; exact rollouts still depend on sim-core when configured.",
        ],
    }


def write_reports(report: Dict[str, Any], output_dir: Path) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "mechanics_audit.json"
    md_path = output_dir / "mechanics_audit.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Mechanics Audit",
        "",
        f"- Status: {'PASS' if report.get('ok') else 'FAIL'}",
        f"- Tests run: {report.get('tests_run')}",
        f"- Failures: {report.get('failures')}",
        f"- Errors: {report.get('errors')}",
        f"- Elapsed seconds: {report.get('elapsed_sec')}",
        "",
        "## Categories",
        "",
    ]
    for category, details in report.get("categories", {}).items():
        mark = "PASS" if details.get("passed") else "FAIL"
        lines.append(f"- {category}: {mark} ({len(details.get('tests', []))} targeted tests)")
    lines.extend(
        [
            "",
            "## Feature Dimensions",
            "",
            f"- Live private: {report['feature_dimensions']['live_private_feature_version']} dim={report['feature_dimensions']['live_private_feature_dim']}",
            f"- Action: {report['feature_dimensions']['action_feature_version']} dim={report['feature_dimensions']['action_feature_dim']}",
            "",
            "## Notes",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in report.get("notes", []))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run targeted battle-mechanics audit tests and write reports.")
    parser.add_argument("--output-dir", default="artifacts/analysis")
    args = parser.parse_args()
    report = run_audit()
    paths = write_reports(report, Path(args.output_dir))
    print_line_safe(f"mechanics-audit done | ok={report['ok']} tests={report['tests_run']} json={paths['json']} md={paths['md']}")
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
