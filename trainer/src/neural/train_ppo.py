import argparse
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from torch.distributions import Categorical

from .checkpoints import (
    build_model_from_checkpoint,
    make_checkpoint_payload,
    save_checkpoint,
    torch_load,
    validate_checkpoint_compatible,
    write_report,
)
from .config import load_config, resolve_path, resolve_process_spec
from .env_client import SimCoreClient
from .featurize import GLOBAL_DIM, POKEMON_DIM, REQUEST_DIM, featurize_battle
from .logging_helper import format_summary, print_line_safe
from .models.policy_value_mlp import PolicyValueMLP, masked_logits
from .runtime import DEFAULT_TIMEOUTS_SEC, MINIMAL_STEP_OPTIONS, choose_timeout, load_runtime_options


INPUT_SIZE = GLOBAL_DIM + (6 * POKEMON_DIM) + (6 * POKEMON_DIM) + REQUEST_DIM


def _fallback_action(request: Dict[str, Any], action_index: int) -> Tuple[Dict[str, Any], int]:
    actions = request.get("legal_actions", {}).get("actions", [])
    action = actions[action_index] if 0 <= action_index < len(actions) else None
    if action is not None:
        return action, action_index
    fallback = next((candidate for candidate in actions if candidate is not None), None)
    if fallback is None:
        fallback = {"index": 0, "choice": "default", "kind": "move", "label": "default", "move": None, "slot": None}
    return fallback, int(fallback.get("index", 0))


def select_action(
    model: PolicyValueMLP,
    feature_vector: np.ndarray,
    legal_mask: np.ndarray,
    device: torch.device,
    *,
    deterministic: bool = False,
) -> Dict[str, Any]:
    inputs = torch.from_numpy(feature_vector).unsqueeze(0).to(device)
    masks = torch.from_numpy(legal_mask).unsqueeze(0).to(device)
    with torch.no_grad():
        logits, value = model(inputs)
        masked = masked_logits(logits, masks)
        dist = Categorical(logits=masked)
        action = masked.argmax(dim=-1) if deterministic else dist.sample()
        logprob = dist.log_prob(action)
    return {
        "action_index": int(action.item()),
        "logprob": float(logprob.item()),
        "value": float(value.item()),
    }


def discounted_terminal_returns(records: List[Dict[str, Any]], final_rewards: Dict[str, float], gamma: float) -> None:
    by_player: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        by_player.setdefault(str(record["player"]), []).append(record)
    for player, player_records in by_player.items():
        reward = float(final_rewards.get(player, 0.0))
        for offset, record in enumerate(reversed(player_records)):
            record["return"] = reward * (gamma ** offset)


def ppo_update(
    model: PolicyValueMLP,
    optimizer: torch.optim.Optimizer,
    rollout_records: Sequence[Dict[str, Any]],
    device: torch.device,
    *,
    epochs: int,
    clip_range: float = 0.2,
    value_coef: float = 0.5,
    entropy_coef: float = 0.01,
    grad_clip_norm: float = 1.0,
) -> Dict[str, Any]:
    if not rollout_records:
        raise RuntimeError("No PPO rollouts were collected.")

    states = torch.from_numpy(np.asarray([record["state"] for record in rollout_records], dtype=np.float32)).to(device)
    masks = torch.from_numpy(np.asarray([record["mask"] for record in rollout_records], dtype=np.float32)).to(device)
    actions = torch.from_numpy(np.asarray([record["action"] for record in rollout_records], dtype=np.int64)).to(device)
    old_logprobs = torch.from_numpy(np.asarray([record["old_logprob"] for record in rollout_records], dtype=np.float32)).to(device)
    returns = torch.from_numpy(np.asarray([record["return"] for record in rollout_records], dtype=np.float32)).to(device)
    baseline_values = torch.from_numpy(np.asarray([record["value"] for record in rollout_records], dtype=np.float32)).to(device)
    advantages = returns - baseline_values
    if advantages.numel() > 1:
        advantages = (advantages - advantages.mean()) / (advantages.std(unbiased=False) + 1e-8)

    history = []
    for epoch in range(epochs):
        model.train()
        logits, values = model(states)
        masked = masked_logits(logits, masks)
        dist = Categorical(logits=masked)
        logprobs = dist.log_prob(actions)
        ratios = torch.exp(logprobs - old_logprobs)
        clipped = torch.clamp(ratios, 1.0 - clip_range, 1.0 + clip_range) * advantages
        policy_loss = -torch.minimum(ratios * advantages, clipped).mean()
        value_loss = F.mse_loss(values, returns)
        entropy = dist.entropy().mean()
        loss = policy_loss + value_coef * value_loss - entropy_coef * entropy

        optimizer.zero_grad()
        loss.backward()
        if grad_clip_norm > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip_norm)
        optimizer.step()

        epoch_data = {
            "epoch": epoch + 1,
            "loss": float(loss.item()),
            "policy_loss": float(policy_loss.item()),
            "value_loss": float(value_loss.item()),
            "entropy": float(entropy.item()),
        }
        history.append(epoch_data)
        print_line_safe(
            f"ppo_epoch={epoch + 1} loss={epoch_data['loss']:.4f} "
            f"policy={epoch_data['policy_loss']:.4f} value={epoch_data['value_loss']:.4f} entropy={epoch_data['entropy']:.4f}"
        )

    return {
        "records": len(rollout_records),
        "epochs": epochs,
        "history": history,
    }


def _load_or_create_model(
    config: Dict[str, Any],
    checkpoint_path: Path,
    device: torch.device,
    *,
    hidden_sizes: Sequence[int],
) -> Tuple[PolicyValueMLP, Dict[str, Any]]:
    if checkpoint_path.exists():
        checkpoint = torch_load(checkpoint_path, device)
        validate_checkpoint_compatible(checkpoint, input_size=INPUT_SIZE, hidden_sizes=hidden_sizes, action_size=13)
        model = build_model_from_checkpoint(checkpoint, default_hidden_sizes=hidden_sizes, device=device)
        return model, checkpoint
    model = PolicyValueMLP(input_size=INPUT_SIZE, hidden_sizes=hidden_sizes).to(device)
    return model, {}


def collect_ppo_rollouts(
    config: Dict[str, Any],
    model: PolicyValueMLP,
    device: torch.device,
    *,
    episodes: int,
    opponent: str,
    opponent_model: Optional[PolicyValueMLP] = None,
    gamma: float = 0.99,
) -> Dict[str, Any]:
    command, cwd = resolve_process_spec(config)
    runtime = load_runtime_options(config, default_num_envs=1)
    ppo_cfg = config.get("ppo", {})
    format_name = ppo_cfg.get("format", config.get("evaluation", {}).get("format", "gen9randombattle"))
    external_opponent = opponent in {"self", "checkpoint"}
    response_options = dict(MINIMAL_STEP_OPTIONS)
    if external_opponent:
        response_options["view_players"] = ["p1", "p2"]

    players = {
        "p1": {"controller": "external"},
        "p2": {"controller": "external" if external_opponent else opponent},
    }
    rollout_records: List[Dict[str, Any]] = []
    wins = 0
    losses = 0
    ties = 0

    with SimCoreClient(command, cwd) as client:
        for episode in range(episodes):
            env_id = client.create_env(
                format_name=format_name,
                players=players,
                timeout_sec=choose_timeout(runtime, "create_env"),
            )
            episode_records: List[Dict[str, Any]] = []
            try:
                result = client.reset(env_id, options=response_options, timeout_sec=choose_timeout(runtime, "reset"))
                while not result["terminated"]:
                    choices: Dict[str, str] = {}
                    for player in ["p1", "p2"]:
                        request = result["requests"].get(player)
                        view = result["views"].get(player)
                        if request is None or view is None:
                            continue
                        acting_model = model
                        collect_player = player == "p1"
                        if player == "p2":
                            if opponent == "checkpoint" and opponent_model is not None:
                                acting_model = opponent_model
                            elif opponent == "self":
                                acting_model = model
                                collect_player = True
                            else:
                                continue
                        features = featurize_battle(view, request)
                        decision = select_action(acting_model, features.flat, features.legal_mask, device)
                        action, action_index = _fallback_action(request, int(decision["action_index"]))
                        choices[player] = str(action["choice"])
                        if collect_player:
                            episode_records.append(
                                {
                                    "episode": episode + 1,
                                    "player": player,
                                    "state": features.flat,
                                    "mask": features.legal_mask,
                                    "action": action_index,
                                    "old_logprob": decision["logprob"],
                                    "value": decision["value"],
                                }
                            )
                    if not choices:
                        raise RuntimeError("No actionable player request was available during PPO rollout.")
                    result = client.step(
                        env_id,
                        choices,
                        options=response_options,
                        timeout_sec=choose_timeout(runtime, "step"),
                    )

                winner = result["winner"]
                if winner == "p1":
                    wins += 1
                elif winner == "p2":
                    losses += 1
                else:
                    ties += 1
                final_rewards = {
                    "p1": float(result["rewards"].get("p1", 0.0)),
                    "p2": float(result["rewards"].get("p2", 0.0)),
                }
                discounted_terminal_returns(episode_records, final_rewards, gamma)
                rollout_records.extend(episode_records)
            finally:
                client.close_env(env_id, timeout_sec=choose_timeout(runtime, "close_env"))
                client.take_latency_events(env_id)

            if (episode + 1) % max(1, int(ppo_cfg.get("progress_interval", 10))) == 0:
                print_line_safe(
                    f"ppo collect | episode={episode + 1}/{episodes} records={len(rollout_records)} "
                    f"wins={wins} losses={losses} ties={ties}"
                )

    return {
        "records": rollout_records,
        "episodes": episodes,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / max(1, episodes),
    }


def train_ppo(config: Dict[str, Any], *, episodes_override: Optional[int] = None, epochs_override: Optional[int] = None) -> Dict[str, Any]:
    config_path_str = config.get("_config_path", "<dict>")
    training_cfg = config.get("training", {})
    ppo_cfg = config.get("ppo", {})
    hidden_sizes = list(training_cfg.get("hidden_sizes", ppo_cfg.get("hidden_sizes", [256, 256])))
    checkpoint_path = resolve_path(config, ppo_cfg.get("checkpoint_path", training_cfg.get("checkpoint_path", "../artifacts/checkpoints/gen9randombattle_bc.pt")))
    output_checkpoint_path = resolve_path(config, ppo_cfg.get("output_checkpoint_path", str(checkpoint_path)))
    best_checkpoint_path = resolve_path(config, training_cfg.get("best_checkpoint_path", str(checkpoint_path.with_suffix(".best.pt"))))
    opponent = str(ppo_cfg.get("opponent", "random"))
    episodes = int(episodes_override if episodes_override is not None else ppo_cfg.get("episodes", 16))
    epochs = int(epochs_override if epochs_override is not None else ppo_cfg.get("epochs", 3))
    gamma = float(ppo_cfg.get("gamma", 0.99))
    learning_rate = float(ppo_cfg.get("learning_rate", 3e-4))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model, source_checkpoint = _load_or_create_model(config, checkpoint_path, device, hidden_sizes=hidden_sizes)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=float(ppo_cfg.get("weight_decay", 0.0)))
    if source_checkpoint.get("optimizer_state_dict") and bool(ppo_cfg.get("resume_optimizer", False)):
        optimizer.load_state_dict(source_checkpoint["optimizer_state_dict"])

    opponent_model = None
    if opponent == "checkpoint":
        opponent_checkpoint_path = resolve_path(config, ppo_cfg.get("opponent_checkpoint_path", str(best_checkpoint_path)))
        if not opponent_checkpoint_path.exists():
            raise FileNotFoundError(f"Opponent checkpoint does not exist: {opponent_checkpoint_path}")
        opponent_checkpoint = torch_load(opponent_checkpoint_path, device)
        opponent_model = build_model_from_checkpoint(opponent_checkpoint, default_hidden_sizes=hidden_sizes, device=device)
        opponent_model.eval()

    print_line_safe(f"ppo start episodes={episodes} epochs={epochs} opponent={opponent} checkpoint={checkpoint_path}")
    started_at = time.perf_counter()
    rollout = collect_ppo_rollouts(
        config,
        model,
        device,
        episodes=episodes,
        opponent=opponent,
        opponent_model=opponent_model,
        gamma=gamma,
    )
    update_report = ppo_update(
        model,
        optimizer,
        rollout["records"],
        device,
        epochs=epochs,
        clip_range=float(ppo_cfg.get("clip_range", 0.2)),
        value_coef=float(ppo_cfg.get("value_coef", 0.5)),
        entropy_coef=float(ppo_cfg.get("entropy_coef", 0.01)),
        grad_clip_norm=float(ppo_cfg.get("grad_clip_norm", 1.0)),
    )

    previous_history = list(source_checkpoint.get("ppo_history", []))
    ppo_entry = {
        "episodes": episodes,
        "epochs": epochs,
        "opponent": opponent,
        "win_rate": rollout["win_rate"],
        "records": update_report["records"],
        "history": update_report["history"],
    }
    ppo_history = previous_history + [ppo_entry]
    global_step = int(source_checkpoint.get("global_step", 0)) + update_report["records"]
    checkpoint_payload = make_checkpoint_payload(
        model=model,
        optimizer=optimizer,
        input_size=INPUT_SIZE,
        hidden_sizes=hidden_sizes,
        action_size=13,
        epoch=int(source_checkpoint.get("epoch", 0)),
        global_step=global_step,
        training_history=source_checkpoint.get("training_history", []),
        config_path=str(config_path_str),
        best_score=source_checkpoint.get("best_score"),
        extra={
            "training_kind": "ppo",
            "ppo_history": ppo_history,
            "source_checkpoint": str(checkpoint_path),
        },
    )
    save_checkpoint(output_checkpoint_path, checkpoint_payload)

    report_path = output_checkpoint_path.with_suffix(".ppo.json")
    report = {
        "checkpoint": str(output_checkpoint_path),
        "source_checkpoint": str(checkpoint_path),
        "episodes": episodes,
        "epochs": epochs,
        "opponent": opponent,
        "rollout": {key: value for key, value in rollout.items() if key != "records"},
        "update": update_report,
        "wall_time_ms": (time.perf_counter() - started_at) * 1000.0,
        "device": device.type,
    }
    write_report(report_path, report)
    print_line_safe(f"ppo | checkpoint={output_checkpoint_path}")
    print_line_safe(f"ppo | report={report_path}")
    print_line_safe(format_summary("ppo", {"wins": rollout["wins"], "losses": rollout["losses"], "ties": rollout["ties"], "win_rate": rollout["win_rate"], "checkpoint": str(output_checkpoint_path)}))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="PPO fine-tuning loop for model-vs-baseline and self-play.")
    parser.add_argument("--config", required=True, help="Path to the experiment config.")
    parser.add_argument("--episodes", type=int, default=None, help="Number of episodes to collect.")
    parser.add_argument("--epochs", type=int, default=None, help="Number of PPO optimization epochs.")
    args = parser.parse_args()

    config = load_config(args.config)
    train_ppo(config, episodes_override=args.episodes, epochs_override=args.epochs)


if __name__ == "__main__":
    main()
