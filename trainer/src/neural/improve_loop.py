import argparse
import copy
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .build_dataset import collect_dataset_run, merge_shards, write_records_jsonl, write_shard
from .checkpoints import copy_checkpoint, write_report
from .config import load_config, resolve_path
from .eval import run_evaluation
from .logging_helper import format_summary, print_line_safe
from .train_bc import train_behavior_cloning
from .train_ppo import train_ppo


DEFAULT_IMPROVEMENT = {
    "cycles": 20,
    "collect_battles_per_cycle": 128,
    "bc_epochs_per_cycle": 2,
    "ppo_episodes_per_cycle": 64,
    "ppo_epochs_per_cycle": 3,
    "ppo_opponent": "random",
    "eval_battles_per_cycle": 100,
    "eval_opponents": ["random", "heuristic"],
    "promotion_metric": "win_rate",
    "keep_last_checkpoints": 5,
    "state_path": "../artifacts/improve/state.json",
    "work_dir": "../artifacts/improve",
    "cumulative_shard_path": "../data/shards/improve/cumulative.npz",
}


def load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "current_cycle": 0,
            "best_score": None,
            "best_checkpoint": None,
            "cycle_shards": [],
            "history": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def rotate_checkpoints(directory: Path, keep: int) -> None:
    if keep <= 0 or not directory.exists():
        return
    checkpoints = sorted(directory.glob("cycle_*.pt"), key=lambda path: path.stat().st_mtime, reverse=True)
    for stale in checkpoints[keep:]:
        stale.unlink(missing_ok=True)


def improvement_options(config: Dict[str, Any]) -> Dict[str, Any]:
    options = dict(DEFAULT_IMPROVEMENT)
    options.update(config.get("improvement", {}))
    return options


def _cycle_config(config: Dict[str, Any], cycle: int, options: Dict[str, Any]) -> Dict[str, Any]:
    cycle_cfg = copy.deepcopy(config)
    cycle_cfg["profile"] = f"{config.get('profile', 'full')}-improve-cycle-{cycle}"
    work_dir = resolve_path(config, options["work_dir"])
    cycle_cfg.setdefault("dataset", {})
    cycle_cfg["dataset"]["num_battles"] = int(options["collect_battles_per_cycle"])
    cycle_cfg["dataset"]["source"] = "improve_loop"
    cycle_cfg["dataset"]["output_path"] = str(work_dir / "raw" / f"cycle_{cycle:04d}.jsonl.gz")
    cycle_cfg["dataset"]["shard_path"] = str(work_dir / "shards" / f"cycle_{cycle:04d}.npz")
    cycle_cfg["dataset"]["latency_output_path"] = str(work_dir / "latency" / f"cycle_{cycle:04d}_dataset.json")
    return cycle_cfg


def _train_config(config: Dict[str, Any], shard_path: Path, options: Dict[str, Any]) -> Dict[str, Any]:
    train_cfg = copy.deepcopy(config)
    train_cfg.setdefault("dataset", {})
    train_cfg.setdefault("training", {})
    train_cfg["dataset"]["shard_path"] = str(shard_path)
    train_cfg["training"]["resume"] = True
    train_cfg["training"]["epochs"] = int(options["bc_epochs_per_cycle"])
    return train_cfg


def _ppo_config(config: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    ppo_cfg = copy.deepcopy(config)
    ppo_cfg.setdefault("ppo", {})
    ppo_cfg["ppo"]["episodes"] = int(options["ppo_episodes_per_cycle"])
    ppo_cfg["ppo"]["epochs"] = int(options["ppo_epochs_per_cycle"])
    ppo_cfg["ppo"]["opponent"] = str(options.get("ppo_opponent", "random"))
    ppo_cfg["ppo"]["checkpoint_path"] = ppo_cfg.get("training", {}).get("checkpoint_path", "../artifacts/checkpoints/gen9randombattle_bc.pt")
    ppo_cfg["ppo"]["output_checkpoint_path"] = ppo_cfg["ppo"]["checkpoint_path"]
    return ppo_cfg


def _eval_config(config: Dict[str, Any], cycle: int, opponent: str, num_battles: int, options: Dict[str, Any]) -> Dict[str, Any]:
    eval_cfg = copy.deepcopy(config)
    checkpoint_path = eval_cfg.get("training", {}).get("checkpoint_path", "../artifacts/checkpoints/gen9randombattle_bc.pt")
    work_dir = resolve_path(config, options["work_dir"])
    eval_cfg.setdefault("evaluation", {})
    eval_cfg["evaluation"]["num_battles"] = int(num_battles)
    eval_cfg["evaluation"]["format"] = eval_cfg["evaluation"].get("format", "gen9randombattle")
    eval_cfg["evaluation"]["checkpoint_path"] = checkpoint_path
    eval_cfg["evaluation"]["opponent"] = opponent
    eval_cfg["evaluation"]["output_path"] = str(work_dir / "eval" / f"cycle_{cycle:04d}_{opponent}.json")
    eval_cfg["evaluation"]["latency_output_path"] = str(work_dir / "latency" / f"cycle_{cycle:04d}_{opponent}_eval.json")
    return eval_cfg


def _score_evals(eval_reports: Dict[str, Dict[str, Any]]) -> float:
    if not eval_reports:
        return 0.0
    return sum(float(report.get("win_rate", 0.0)) for report in eval_reports.values()) / len(eval_reports)


def run_improvement_loop(config: Dict[str, Any]) -> Dict[str, Any]:
    options = improvement_options(config)
    state_path = resolve_path(config, options["state_path"])
    work_dir = resolve_path(config, options["work_dir"])
    state = load_state(state_path)
    checkpoint_path = resolve_path(config, config.get("training", {}).get("checkpoint_path", "../artifacts/checkpoints/gen9randombattle_bc.pt"))
    best_checkpoint_path = resolve_path(
        config,
        config.get("training", {}).get("best_checkpoint_path", str(checkpoint_path.with_suffix(".best.pt"))),
    )
    cycle_checkpoint_dir = work_dir / "checkpoints"
    total_cycles = int(options["cycles"])
    start_cycle = int(state.get("current_cycle", 0)) + 1

    print_line_safe(
        f"improve start cycles={total_cycles} start_cycle={start_cycle} "
        f"checkpoint={checkpoint_path} best={best_checkpoint_path}"
    )

    for cycle in range(start_cycle, total_cycles + 1):
        print_line_safe(f"improve cycle start | cycle={cycle}/{total_cycles}")
        cycle_cfg = _cycle_config(config, cycle, options)
        records, dataset_report = collect_dataset_run(cycle_cfg)
        raw_path = Path(cycle_cfg["dataset"]["output_path"])
        shard_path = Path(cycle_cfg["dataset"]["shard_path"])
        write_records_jsonl(records, raw_path)
        shard_report = write_shard(records, shard_path)

        cycle_shards = [Path(path) for path in state.get("cycle_shards", []) if Path(path).exists()]
        cycle_shards.append(shard_path)
        cumulative_shard_path = resolve_path(config, options["cumulative_shard_path"])
        merge_report = merge_shards(cycle_shards, cumulative_shard_path)

        train_report = train_behavior_cloning(
            _train_config(config, cumulative_shard_path, options),
            epochs_override=int(options["bc_epochs_per_cycle"]),
        )

        ppo_report: Optional[Dict[str, Any]] = None
        if int(options.get("ppo_episodes_per_cycle", 0)) > 0:
            ppo_report = train_ppo(
                _ppo_config(config, options),
                episodes_override=int(options["ppo_episodes_per_cycle"]),
                epochs_override=int(options["ppo_epochs_per_cycle"]),
            )

        eval_reports: Dict[str, Dict[str, Any]] = {}
        for opponent in options.get("eval_opponents", ["random", "heuristic"]):
            eval_reports[str(opponent)] = run_evaluation(
                _eval_config(config, cycle, str(opponent), int(options["eval_battles_per_cycle"]), options)
            )

        score = _score_evals(eval_reports)
        previous_best = state.get("best_score")
        promoted = previous_best is None or score > float(previous_best)
        if promoted and checkpoint_path.exists():
            copy_checkpoint(checkpoint_path, best_checkpoint_path)

        cycle_checkpoint_path = cycle_checkpoint_dir / f"cycle_{cycle:04d}.pt"
        if checkpoint_path.exists():
            cycle_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(checkpoint_path, cycle_checkpoint_path)
            rotate_checkpoints(cycle_checkpoint_dir, int(options["keep_last_checkpoints"]))

        cycle_summary = {
            "cycle": cycle,
            "dataset": dataset_report,
            "shard": shard_report,
            "merge": merge_report,
            "train": train_report,
            "ppo": ppo_report,
            "eval": {
                opponent: {
                    "wins": report.get("wins"),
                    "losses": report.get("losses"),
                    "ties": report.get("ties"),
                    "win_rate": report.get("win_rate"),
                }
                for opponent, report in eval_reports.items()
            },
            "score": score,
            "promoted": promoted,
            "checkpoint": str(checkpoint_path),
            "best_checkpoint": str(best_checkpoint_path),
        }
        state["current_cycle"] = cycle
        state["cycle_shards"] = [str(path) for path in cycle_shards]
        state["latest_checkpoint"] = str(checkpoint_path)
        if promoted:
            state["best_score"] = score
            state["best_checkpoint"] = str(best_checkpoint_path)
        state.setdefault("history", []).append(cycle_summary)
        save_state(state_path, state)
        write_report(work_dir / "reports" / f"cycle_{cycle:04d}.json", cycle_summary)
        print_line_safe(
            format_summary(
                "improve",
                {
                    "cycle": cycle,
                    "score": score,
                    "promoted": promoted,
                    "checkpoint": str(checkpoint_path),
                },
            )
        )

    print_line_safe(f"improve done | state={state_path} best={state.get('best_checkpoint')}")
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuous improvement loop for BC + PPO training.")
    parser.add_argument("--config", required=True, help="Path to the base dataset/training config.")
    args = parser.parse_args()
    config = load_config(args.config)
    run_improvement_loop(config)


if __name__ == "__main__":
    main()
