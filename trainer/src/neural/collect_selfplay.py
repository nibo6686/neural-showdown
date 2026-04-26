import argparse
import gzip
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch

from .checkpoints import build_model_from_checkpoint, torch_load
from .config import load_config, resolve_path, resolve_process_spec
from .env_client import SimCoreClient
from .featurize import featurize_battle
from .logging_helper import format_summary, print_line_safe
from .models.policy_value_mlp import PolicyValueMLP
from .opponent_pool import OpponentPool, OpponentSpec
from .runtime import MINIMAL_STEP_OPTIONS, choose_timeout, load_runtime_options, make_battle_seed
from .train_ppo import _fallback_action, select_action


DEFAULT_OUTPUT_PATH = Path("data/selfplay/gen9randombattle_selfplay.jsonl.gz")
DEFAULT_REPORT_JSON_PATH = Path("artifacts/selfplay/selfplay_report.json")
DEFAULT_REPORT_MD_PATH = Path("artifacts/selfplay/selfplay_report.md")


def _load_model(path: Path, device: torch.device) -> PolicyValueMLP:
    checkpoint = torch_load(path, device)
    model = build_model_from_checkpoint(checkpoint, default_hidden_sizes=[256, 256], device=device)
    model.eval()
    return model


def _checkpoint_from_config(config: Dict[str, Any]) -> Optional[Path]:
    selfplay_cfg = config.get("selfplay", {})
    candidate = selfplay_cfg.get("policy_checkpoint_path") or config.get("training", {}).get("checkpoint_path")
    if not candidate:
        return None
    return resolve_path(config, candidate)


def _baseline_action(client: SimCoreClient, env_id: str, player: str, agent: str, runtime: Any) -> Tuple[str, int, str]:
    decision = client.agent_action(env_id, player, agent, timeout_sec=choose_timeout(runtime, "agent_action"))
    return str(decision["choice"]), int(decision.get("action_index", -1)), str(decision.get("label", decision["choice"]))


def _model_action(
    model: PolicyValueMLP,
    view: Dict[str, Any],
    request: Dict[str, Any],
    device: torch.device,
) -> Tuple[str, int, str]:
    features = featurize_battle(view, request)
    decision = select_action(model, features.flat, features.legal_mask, device, deterministic=False)
    action, action_index = _fallback_action(request, int(decision["action_index"]))
    return str(action["choice"]), int(action_index), str(action.get("label", action["choice"]))


def _write_jsonl_gz(path: Path, episodes: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for episode in episodes:
            handle.write(json.dumps(episode) + "\n")


def _opponent_players(opponent: OpponentSpec) -> Dict[str, Dict[str, str]]:
    if opponent.type in {"random", "heuristic"}:
        return {"p1": {"controller": "external"}, "p2": {"controller": opponent.type}}
    return {"p1": {"controller": "external"}, "p2": {"controller": "external"}}


def collect_selfplay(config: Dict[str, Any]) -> Dict[str, Any]:
    command, cwd = resolve_process_spec(config)
    runtime = load_runtime_options(config, default_num_envs=1)
    selfplay_cfg = config.get("selfplay", {})
    format_name = selfplay_cfg.get("format", config.get("dataset", {}).get("format", "gen9randombattle"))
    num_battles = int(selfplay_cfg.get("num_battles", 4 if config.get("profile") == "dev" else 32))
    output_path = resolve_path(config, selfplay_cfg.get("output_path", "../data/selfplay/gen9randombattle_selfplay.jsonl.gz"))
    report_json_path = resolve_path(config, selfplay_cfg.get("report_json_path", "../artifacts/selfplay/selfplay_report.json"))
    report_md_path = resolve_path(config, selfplay_cfg.get("report_md_path", "../artifacts/selfplay/selfplay_report.md"))
    fallback_agent = str(selfplay_cfg.get("fallback_agent", "random"))
    response_options = dict(MINIMAL_STEP_OPTIONS)
    response_options["view_players"] = ["p1", "p2"]
    response_options["include_log_delta"] = True

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    policy_checkpoint = _checkpoint_from_config(config)
    p1_model: Optional[PolicyValueMLP] = None
    p1_policy_name = fallback_agent
    if policy_checkpoint and policy_checkpoint.exists():
        p1_model = _load_model(policy_checkpoint, device)
        p1_policy_name = str(policy_checkpoint)

    pool = OpponentPool.from_config(config)
    checkpoint_model_cache: Dict[str, PolicyValueMLP] = {}
    episodes: List[Dict[str, Any]] = []
    wins = losses = ties = 0
    started_at = time.perf_counter()

    print_line_safe(
        f"selfplay start profile={config.get('profile', 'full')} battles={num_battles} "
        f"p1_policy={p1_policy_name} device={device.type}"
    )
    with SimCoreClient(command, cwd) as client:
        for battle_index in range(num_battles):
            opponent = pool.sample()
            players = _opponent_players(opponent)
            env_id = client.create_env(
                format_name=format_name,
                seed=make_battle_seed(battle_index),
                players=players,
                timeout_sec=choose_timeout(runtime, "create_env"),
            )
            episode_steps: List[Dict[str, Any]] = []
            protocol_log: List[str] = []
            try:
                result = client.reset(env_id, options=response_options, timeout_sec=choose_timeout(runtime, "reset"))
                while not result["terminated"]:
                    choices: Dict[str, str] = {}
                    pending_records: List[Dict[str, Any]] = []

                    p1_request = result["requests"].get("p1")
                    p1_view = result["views"].get("p1")
                    if p1_request and p1_view:
                        if p1_model is not None:
                            choice, action_index, label = _model_action(p1_model, p1_view, p1_request, device)
                            policy_type = "checkpoint"
                        else:
                            choice, action_index, label = _baseline_action(client, env_id, "p1", fallback_agent, runtime)
                            policy_type = fallback_agent
                        choices["p1"] = choice
                        pending_records.append(
                            {
                                "player": "p1",
                                "policy_type": policy_type,
                                "view": p1_view,
                                "request": p1_request,
                                "choice": choice,
                                "action_index": action_index,
                                "chosen_action_label": label,
                                "step_index": len(episode_steps),
                            }
                        )

                    p2_request = result["requests"].get("p2")
                    p2_view = result["views"].get("p2")
                    if opponent.type == "checkpoint" and p2_request and p2_view and opponent.checkpoint:
                        checkpoint_path = resolve_path(config, opponent.checkpoint)
                        cache_key = str(checkpoint_path)
                        if cache_key not in checkpoint_model_cache:
                            checkpoint_model_cache[cache_key] = _load_model(checkpoint_path, device)
                        choice, action_index, label = _model_action(checkpoint_model_cache[cache_key], p2_view, p2_request, device)
                        choices["p2"] = choice
                        pending_records.append(
                            {
                                "player": "p2",
                                "policy_type": "checkpoint",
                                "opponent_name": opponent.name,
                                "view": p2_view,
                                "request": p2_request,
                                "choice": choice,
                                "action_index": action_index,
                                "chosen_action_label": label,
                                "step_index": len(episode_steps),
                            }
                        )

                    if not choices:
                        raise RuntimeError("No pending external choices during self-play collection.")

                    result = client.step(env_id, choices, options=response_options, timeout_sec=choose_timeout(runtime, "step"))
                    log_delta = [str(line) for line in result.get("log_delta", [])]
                    protocol_log.extend(log_delta)
                    for record in pending_records:
                        record["protocol_log"] = log_delta
                        record["turn"] = int(result.get("info", {}).get("turn", 0) or 0)
                        episode_steps.append(record)

                winner = result.get("winner")
                if winner == "p1":
                    wins += 1
                elif winner == "p2":
                    losses += 1
                else:
                    ties += 1
                episodes.append(
                    {
                        "source": "selfplay",
                        "battle_index": battle_index,
                        "format": format_name,
                        "seed": make_battle_seed(battle_index),
                        "p1_policy": p1_policy_name,
                        "opponent": {"name": opponent.name, "type": opponent.type, "checkpoint": opponent.checkpoint},
                        "winner": winner,
                        "final_result": 1.0 if winner == "p1" else -1.0 if winner == "p2" else 0.0,
                        "steps": episode_steps,
                        "protocol_log": protocol_log,
                    }
                )
            finally:
                client.close_env(env_id, timeout_sec=choose_timeout(runtime, "close_env"))
                client.take_latency_events(env_id)

            print_line_safe(
                f"selfplay {battle_index + 1}/{num_battles} winner={episodes[-1]['winner']} "
                f"opponent={opponent.name} steps={len(episodes[-1]['steps'])}"
            )

    _write_jsonl_gz(output_path, episodes)
    report = {
        "output_path": str(output_path),
        "num_battles": num_battles,
        "episodes": len(episodes),
        "steps": sum(len(episode["steps"]) for episode in episodes),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / max(1, len(episodes)),
        "p1_policy": p1_policy_name,
        "used_fallback_policy": p1_model is None,
        "wall_time_ms": (time.perf_counter() - started_at) * 1000.0,
    }
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md_path.write_text(_format_markdown_report(report), encoding="utf-8")
    print_line_safe(f"selfplay | wrote episodes to {output_path}")
    print_line_safe(f"selfplay | report={report_json_path}")
    print_line_safe(format_summary("selfplay", {"battles": len(episodes), "steps": report["steps"], "win_rate": f"{report['win_rate']:.3f}"}))
    return report


def _format_markdown_report(report: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Self-Play Collection Report",
            "",
            f"- Battles: {report['episodes']}",
            f"- Steps: {report['steps']}",
            f"- Wins/losses/ties: {report['wins']} / {report['losses']} / {report['ties']}",
            f"- Win rate: {report['win_rate']:.3f}",
            f"- P1 policy: {report['p1_policy']}",
            f"- Used fallback policy: {report['used_fallback_policy']}",
            "",
            f"Output: `{report['output_path']}`",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect model self-play or model-vs-pool episodes.")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    collect_selfplay(load_config(args.config))


if __name__ == "__main__":
    main()
