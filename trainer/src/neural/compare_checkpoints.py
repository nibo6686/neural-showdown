import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import load_config, resolve_path
from .eval import run_evaluation
from .logging_helper import format_summary, print_line_safe


DEFAULT_OUTPUT_JSON = "../artifacts/compare/checkpoint_comparison.json"
DEFAULT_OUTPUT_MD = "../artifacts/compare/checkpoint_comparison.md"


def _candidate_checkpoints(config: Dict[str, Any]) -> List[Dict[str, str]]:
    compare_cfg = config.get("compare", {})
    configured = compare_cfg.get("checkpoints")
    if configured:
        return [{"name": str(item["name"]), "path": str(item["path"])} for item in configured]

    training = config.get("training", {})
    profile = str(config.get("profile", ""))
    awbc_path = (
        "../artifacts/checkpoints/gen9randombattle_bc.awbc.dev.pt"
        if profile.startswith("dev")
        else "../artifacts/checkpoints/gen9randombattle_bc.awbc.pt"
    )
    candidates = [
        {"name": "baseline_bc", "path": training.get("checkpoint_path", "../artifacts/checkpoints/gen9randombattle_bc.pt")},
        {"name": "best_bc", "path": training.get("best_checkpoint_path", "../artifacts/checkpoints/gen9randombattle_bc.best.pt")},
        {"name": "value", "path": "../artifacts/checkpoints/gen9randombattle_value.pt"},
        {"name": "awbc", "path": awbc_path},
    ]
    return [candidate for candidate in candidates if candidate.get("path")]


def compare_checkpoints(config: Dict[str, Any]) -> Dict[str, Any]:
    compare_cfg = config.get("compare", {})
    opponents = list(compare_cfg.get("opponents", ["random", "heuristic"]))
    num_battles = int(compare_cfg.get("num_battles", 4 if config.get("profile") == "dev" else 32))
    output_json = resolve_path(config, compare_cfg.get("output_path", DEFAULT_OUTPUT_JSON))
    output_md = resolve_path(config, compare_cfg.get("markdown_path", DEFAULT_OUTPUT_MD))
    rows: List[Dict[str, Any]] = []

    for candidate in _candidate_checkpoints(config):
        checkpoint_path = resolve_path(config, candidate["path"])
        if not checkpoint_path.exists():
            rows.append({"name": candidate["name"], "checkpoint": str(checkpoint_path), "skipped": True, "reason": "missing"})
            continue
        if candidate["name"] == "value":
            rows.append(
                {
                    "name": candidate["name"],
                    "checkpoint": str(checkpoint_path),
                    "skipped": True,
                    "reason": "value-only checkpoint is not a policy battle agent",
                }
            )
            continue
        for opponent in opponents:
            eval_cfg = copy.deepcopy(config)
            eval_cfg.setdefault("evaluation", {})
            eval_cfg["evaluation"]["checkpoint_path"] = str(checkpoint_path)
            eval_cfg["evaluation"]["opponent"] = str(opponent)
            eval_cfg["evaluation"]["num_battles"] = num_battles
            eval_cfg["evaluation"]["format"] = eval_cfg["evaluation"].get("format", "gen9randombattle")
            eval_cfg["evaluation"]["output_path"] = str(output_json.parent / f"{candidate['name']}_vs_{opponent}.eval.json")
            eval_cfg["evaluation"]["latency_output_path"] = str(output_json.parent / f"{candidate['name']}_vs_{opponent}.latency.json")
            print_line_safe(f"compare | checkpoint={candidate['name']} opponent={opponent} battles={num_battles}")
            eval_report = run_evaluation(eval_cfg)
            rows.append(
                {
                    "name": candidate["name"],
                    "checkpoint": str(checkpoint_path),
                    "opponent": opponent,
                    "win_rate": eval_report.get("win_rate"),
                    "wins": eval_report.get("wins"),
                    "losses": eval_report.get("losses"),
                    "ties": eval_report.get("ties"),
                    "average_turns": eval_report.get("avg_steps"),
                    "first_turn_tera_rate": None,
                    "voluntary_switch_rate": None,
                    "repeated_action_rate": None,
                    "average_model_entropy": None,
                    "value_prediction_average_on_wins": None,
                    "value_prediction_average_on_losses": None,
                    "calibration_metrics": None,
                    "skipped": False,
                }
            )

    report = {
        "num_battles_per_matchup": num_battles,
        "opponents": opponents,
        "results": rows,
        "note": "Behavior metrics that require per-decision traces are reported as null until comparison tracing is enabled.",
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    output_md.write_text(_format_markdown(report), encoding="utf-8")
    print_line_safe(f"compare | report={output_json}")
    print_line_safe(format_summary("compare", {"rows": len(rows), "report": str(output_json)}))
    return report


def _format_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Checkpoint Comparison",
        "",
        f"Battles per matchup: {report['num_battles_per_matchup']}",
        "",
        "| Checkpoint | Opponent | Win Rate | W-L-T | Notes |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in report.get("results", []):
        if row.get("skipped"):
            lines.append(f"| {row['name']} | - | - | - | skipped: {row.get('reason')} |")
            continue
        lines.append(
            f"| {row['name']} | {row['opponent']} | {row['win_rate']:.3f} | "
            f"{row['wins']}-{row['losses']}-{row['ties']} | avg turns {row['average_turns']:.2f} |"
        )
    lines.extend(["", report.get("note", ""), ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare checkpoints over stable eval matchups.")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    compare_checkpoints(load_config(args.config))


if __name__ == "__main__":
    main()
