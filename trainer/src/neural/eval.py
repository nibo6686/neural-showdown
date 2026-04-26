import argparse
import random
import time
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import torch

from .checkpoints import build_model_from_checkpoint, torch_load
from .config import load_config, resolve_path, resolve_process_spec
from .env_client import SimCoreClient, SimCoreProcessExitedError, SimCoreTimeoutError
from .featurize import featurize_battle
from .latency import summarize_rpc_events, summarize_samples, top_slowest_battles, write_json_report
from .logging_helper import format_summary, print_line_safe
from .metadata_helper import create_run_metadata
from .models.policy_value_mlp import PolicyValueMLP, masked_logits
from .runner import close_slots, initialize_slots, make_wait_hook, recover_active_slots, unwrap_batch_results, warmup_sim_core
from .runtime import EnvSlot, MINIMAL_STEP_OPTIONS, ProgressReporter, choose_timeout, load_runtime_options, make_battle_seed
from .trace import BattleTracer


def load_model(config: Dict[str, Any], device: torch.device) -> PolicyValueMLP:
    hidden_sizes = list(config.get("model", {}).get("hidden_sizes", [256, 256]))
    checkpoint_path = resolve_path(config, config["evaluation"]["checkpoint_path"])
    checkpoint = torch_load(checkpoint_path, device)
    model = build_model_from_checkpoint(checkpoint, default_hidden_sizes=hidden_sizes, device=device)
    model.eval()
    return model


def warmup_model(model: PolicyValueMLP, input_size: int, device: torch.device) -> None:
    inputs = torch.zeros((1, input_size), dtype=torch.float32, device=device)
    masks = torch.ones((1, 13), dtype=torch.float32, device=device)
    with torch.inference_mode():
        logits, _ = model(inputs)
        masked_logits(logits, masks)


def _create_client(command: Sequence[str], cwd: str) -> SimCoreClient:
    return SimCoreClient(command, cwd)


def _should_retry_slot(slot: EnvSlot, retry_limit: int) -> bool:
    return slot.retry_count <= retry_limit


def _log_recovery_diagnostic(operation: str, error: BaseException, diagnostic: Dict[str, Any], diagnostic_index: int) -> None:
    if not isinstance(error, SimCoreTimeoutError):
        return

    timeout_diag = diagnostic.get("timeout_error") if isinstance(diagnostic.get("timeout_error"), dict) else {}
    request = timeout_diag.get("timed_out_request") or diagnostic.get("last_request") or {}
    request_types = request.get("request_types") if isinstance(request, dict) else None
    request_type_text = "unknown"
    if isinstance(request_types, dict) and request_types:
        request_type_text = ",".join(f"{key}:{value}" for key, value in sorted(request_types.items()))
    elif isinstance(request, dict) and request.get("type"):
        request_type_text = str(request.get("type"))

    env_ids = request.get("env_ids") if isinstance(request, dict) else []
    env_text = ",".join(str(env_id) for env_id in env_ids[:8]) if isinstance(env_ids, list) else "unknown"
    slots = diagnostic.get("active_slots") if isinstance(diagnostic.get("active_slots"), list) else []
    slot_text = ",".join(
        f"b{slot.get('battle_number', int(slot.get('battle_index', -1)) + 1)}:{slot.get('env_id')}@s{slot.get('step_index')}r{slot.get('retry_count')}"
        for slot in slots[:8]
        if isinstance(slot, dict)
    )
    stderr_tail = diagnostic.get("recent_stderr") if isinstance(diagnostic.get("recent_stderr"), list) else []
    server_tail = " || ".join(str(line) for line in stderr_tail[-3:])

    print_line_safe(
        "eval timeout detail | "
        f"diag={diagnostic_index} | operation={operation} | "
        f"request={request.get('id') if isinstance(request, dict) else None} | "
        f"types={request_type_text} | envs={env_text or 'none'} | active={slot_text or 'none'} | "
        f"server_tail={server_tail or 'none'}"
    )


def _select_eval_action(request: Dict[str, Any], action_index: int, slot: EnvSlot) -> Dict[str, Any]:
    actions = request.get("legal_actions", {}).get("actions", [])
    selected = actions[action_index] if 0 <= action_index < len(actions) else None
    if selected is not None:
        return selected

    fallback = next((action for action in actions if action is not None), None)
    if fallback is None:
        fallback = {
            "index": 0,
            "kind": "move",
            "choice": "default",
            "label": "default",
            "move": None,
            "slot": None,
        }

    legal_count = sum(1 for action in actions if action is not None)
    print_line_safe(
        "eval action fallback | "
        f"battle={slot.battle_index + 1} | env={slot.env_id} | step={slot.step_index} | "
        f"selected={action_index} | legal_count={legal_count} | choice={fallback.get('choice')}"
    )
    return fallback


def run_evaluation(config: Dict[str, Any]) -> Dict[str, Any]:
    config_path_str = config.get("_config_path", "<dict>")
    command, cwd = resolve_process_spec(config)
    eval_cfg = config["evaluation"]
    runtime = load_runtime_options(config, default_num_envs=1)
    num_battles = int(eval_cfg.get("num_battles", 100))
    opponent = eval_cfg.get("opponent", "random")
    format_name = eval_cfg.get("format", "gen9randombattle")
    output_path = resolve_path(config, eval_cfg.get("output_path", "../artifacts/eval/eval.json"))
    latency_output_path = resolve_path(
        config,
        eval_cfg.get("latency_output_path", "../artifacts/latency/eval_latency.json"),
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(config, device)
    warmup_model(model, int(getattr(model, "_input_size")), device)

    reporter = ProgressReporter("eval", runtime.profile, num_battles, runtime.num_envs, runtime.heartbeat_interval_sec)
    wins = 0
    losses = 0
    ties = 0
    total_steps = 0
    inference_latencies: List[float] = []
    batch_inference_latencies: List[float] = []
    all_rpc_events: List[Dict[str, Any]] = []
    battle_profiles: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []
    completed_battles = 0
    timeouts = 0
    next_battle_index = 0
    next_slot_id = 0
    active_slots: List[EnvSlot] = []
    use_cuda = device.type == "cuda"

    # Initialize tracing if enabled
    tracing_cfg = config.get("tracing", {})
    trace_enabled = tracing_cfg.get("enabled", False)
    trace_sample_rate = float(tracing_cfg.get("trace_sample_rate", 1.0))
    trace_max_battles = int(tracing_cfg.get("trace_max_battles", 20))
    tracer: Optional[BattleTracer] = None
    traced_battles = 0
    slot_trace_data: Dict[int, List[Dict[str, Any]]] = {}  # Track trace steps per slot_id
    if trace_enabled:
        trace_output_dir = tracing_cfg.get("output_dir")
        if trace_output_dir is None:
            trace_output_dir = str(resolve_path(config, "../artifacts/battles"))
        tracer = BattleTracer(trace_output_dir, run_name=runtime.profile)

    players = {"p1": {"controller": "external"}, "p2": {"controller": opponent}}

    client = _create_client(command, cwd)
    try:
        warmup_sim_core(client, runtime, format_name=format_name)
        reporter.start(
            f"opponent={opponent} timeout(step/reset)={int(choose_timeout(runtime, 'step'))}s/{int(choose_timeout(runtime, 'reset'))}s"
        )
        run_started = time.perf_counter()
        batch_count = 0  # Track batches for periodic drain

        while completed_battles < num_battles or active_slots:
            # Emergency drain if latency events accumulate too much (memory leak safeguard)
            if len(client._latency_events) > 1000:
                print_line_safe(f"eval | emergency drain: {len(client._latency_events)} events")
                all_rpc_events.extend(client.take_latency_events())

            while completed_battles + len(active_slots) < num_battles and len(active_slots) < runtime.num_envs:
                active_slots.append(
                    EnvSlot(
                        slot_id=next_slot_id,
                        battle_index=next_battle_index,
                        seed=make_battle_seed(next_battle_index),
                    )
                )
                next_battle_index += 1
                next_slot_id += 1

            uninitialized_slots = [slot for slot in active_slots if slot.env_id is None]
            if uninitialized_slots:
                try:
                    initialize_slots(
                        client,
                        uninitialized_slots,
                        runtime=runtime,
                        format_name=format_name,
                        players=players,
                        response_options=MINIMAL_STEP_OPTIONS,
                        reporter=reporter,
                        operation_name="eval",
                    )
                except (SimCoreTimeoutError, SimCoreProcessExitedError, RuntimeError) as error:
                    if isinstance(error, SimCoreTimeoutError):
                        timeouts += 1
                    recovered_slots, diagnostic = recover_active_slots(
                        client,
                        active_slots,
                        reason=f"initialize:{error}",
                        error=error,
                    )
                    diagnostics.append(diagnostic)
                    _log_recovery_diagnostic("initialize", error, diagnostic, len(diagnostics))
                    retryable: List[EnvSlot] = []
                    for slot in recovered_slots:
                        if _should_retry_slot(slot, runtime.retry_attempts_per_battle):
                            reporter.retry(slot, str(error))
                            retryable.append(slot)
                        else:
                            reporter.failed(slot, str(error))
                    active_slots = retryable
                    client = _create_client(command, cwd)
                    warmup_sim_core(client, runtime, format_name=format_name)
                    continue

            ready_slots = [slot for slot in active_slots if slot.last_result is not None and not slot.last_result["terminated"]]
            if ready_slots:
                try:
                    features = []
                    requests = []
                    for slot in ready_slots:
                        request = slot.last_result["requests"].get("p1")
                        view = slot.last_result["views"].get("p1")
                        if request is None or view is None:
                            raise RuntimeError(f"Missing p1 request/view for battle {slot.battle_index + 1}.")
                        features.append(featurize_battle(view, request))
                        requests.append(request)

                    state_batch = np.stack([feature.flat for feature in features], axis=0)
                    mask_batch = np.stack([feature.legal_mask for feature in features], axis=0)

                    inference_started = time.perf_counter()
                    inputs = torch.from_numpy(state_batch)
                    masks = torch.from_numpy(mask_batch)
                    if use_cuda:
                        inputs = inputs.pin_memory().to(device, non_blocking=True)
                        masks = masks.pin_memory().to(device, non_blocking=True)
                    else:
                        inputs = inputs.to(device)
                        masks = masks.to(device)

                    with torch.inference_mode():
                        logits, values = model(inputs)
                        chosen = masked_logits(logits, masks).argmax(dim=-1)

                    # Store logits and masks for trace collection later
                    logits_for_trace = logits.cpu().numpy()
                    masks_for_trace = masks.cpu().numpy()

                    inference_ms = (time.perf_counter() - inference_started) * 1000.0
                    batch_inference_latencies.append(inference_ms)
                    per_decision_ms = inference_ms / max(1, len(ready_slots))
                    inference_latencies.extend([per_decision_ms] * len(ready_slots))

                    step_requests = []
                    slot_to_request_index = {}  # Map slot to index in requests/chosen for later
                    for req_idx, (slot, request, action_index) in enumerate(zip(ready_slots, requests, chosen.cpu().tolist())):
                        action = _select_eval_action(request, int(action_index), slot)
                        step_requests.append(
                            {
                                "type": "step",
                                "env_id": slot.env_id,
                                "choices": {"p1": action["choice"]},
                                "options": MINIMAL_STEP_OPTIONS,
                            }
                        )
                        slot_to_request_index[slot.slot_id] = (req_idx, action, action_index)

                    step_results = unwrap_batch_results(
                        client.batch_request(
                            step_requests,
                            timeout_sec=choose_timeout(runtime, "step"),
                            on_wait=make_wait_hook(reporter, ready_slots, "step"),
                        )
                    )
                    for slot, result in zip(ready_slots, step_results):
                        # Collect trace data after step execution
                        if tracer is not None and slot.slot_id in slot_to_request_index:
                            if slot.slot_id not in slot_trace_data:
                                slot_trace_data[slot.slot_id] = []

                            req_idx, action, action_index = slot_to_request_index[slot.slot_id]
                            request = requests[req_idx]

                            # Get the view AFTER the step (current result)
                            view_after = result["views"].get("p1", {})
                            active_idx = view_after.get("active", {}).get("self", 0) or 0
                            opponent_idx = view_after.get("active", {}).get("opponent", 0) or 0
                            self_team = view_after.get("self_team", [])
                            opponent_team = view_after.get("opponent_team", [])

                            p1_pokemon = self_team[active_idx] if active_idx < len(self_team) else {}
                            p2_pokemon = opponent_team[opponent_idx] if opponent_idx < len(opponent_team) else {}

                            # Capture full legal actions
                            legal_action_objs = []
                            if "legal_actions" in request and "actions" in request["legal_actions"]:
                                for action_obj in request["legal_actions"]["actions"]:
                                    if action_obj:
                                        legal_action_objs.append({
                                            "index": action_obj.get("index"),
                                            "kind": action_obj.get("kind", "unknown"),
                                            "label": action_obj.get("label", "?"),
                                            "choice": action_obj.get("choice", "?"),
                                            "move": action_obj.get("move"),
                                        })

                            # Capture model logits (top-5)
                            logits_np = logits_for_trace[req_idx]  # 1D array of 13 logits
                            mask_np = masks_for_trace[req_idx]     # 1D array of 13 mask values
                            masked_logits_vals = np.where(mask_np > 0.5, logits_np, -1e9)
                            top_k_indices = np.argsort(-masked_logits_vals)[:5]
                            top_k_logits = logits_np[top_k_indices]
                            top_k_probs = np.exp(top_k_logits - np.max(top_k_logits))
                            top_k_probs = top_k_probs / np.sum(top_k_probs)

                            trace_step = {
                                "turn": view_after.get("turn", 0),
                                "step_index": slot.step_index,
                                "p1_species": p1_pokemon.get("name", "Unknown"),
                                "p1_hp_ratio": p1_pokemon.get("hp_ratio", 0),
                                "p1_status": p1_pokemon.get("status"),
                                "p1_boosts": p1_pokemon.get("boosts", {}),
                                "p2_species": p2_pokemon.get("name", "Unknown"),
                                "p2_hp_ratio": p2_pokemon.get("hp_ratio", 0),
                                "p2_status": p2_pokemon.get("status"),
                                "legal_actions": legal_action_objs,
                                "legal_actions_count": len(legal_action_objs),
                                "chosen_action_index": int(action_index),
                                "chosen_action_label": action.get("label", "?"),
                                "chosen_action_choice": action.get("choice", "?"),
                                "chosen_action_probability": float(top_k_probs[0]) if len(top_k_probs) > 0 else 0.0,
                                "model_top_k": [
                                    {
                                        "index": int(idx),
                                        "logit": float(logits_np[idx]),
                                        "probability": float(top_k_probs[i]),
                                    }
                                    for i, idx in enumerate(top_k_indices)
                                ],
                                "protocol_log": result.get("log_delta", []),
                            }
                            slot_trace_data[slot.slot_id].append(trace_step)

                        slot.last_result = result
                        slot.step_index += 1
                    total_steps += len(ready_slots)

                    # Drain latency events after successful batch to prevent accumulation
                    for slot in ready_slots:
                        all_rpc_events.extend(client.take_latency_events(slot.env_id))
                except (SimCoreTimeoutError, SimCoreProcessExitedError, RuntimeError) as error:
                    if isinstance(error, SimCoreTimeoutError):
                        timeouts += 1
                    recovered_slots, diagnostic = recover_active_slots(
                        client,
                        active_slots,
                        reason=f"step:{error}",
                        error=error,
                    )
                    diagnostics.append(diagnostic)
                    _log_recovery_diagnostic("step", error, diagnostic, len(diagnostics))
                    retryable = []
                    for slot in recovered_slots:
                        if _should_retry_slot(slot, runtime.retry_attempts_per_battle):
                            reporter.retry(slot, str(error))
                            retryable.append(slot)
                        else:
                            reporter.failed(slot, str(error))
                    active_slots = retryable
                    client = _create_client(command, cwd)
                    warmup_sim_core(client, runtime, format_name=format_name)
                    continue

            terminated_slots = [slot for slot in active_slots if slot.last_result is not None and slot.last_result["terminated"]]
            if terminated_slots:
                try:
                    close_slots(
                        client,
                        terminated_slots,
                        runtime=runtime,
                        reporter=reporter,
                        operation_name="eval",
                    )
                except (SimCoreTimeoutError, SimCoreProcessExitedError, RuntimeError) as error:
                    if isinstance(error, SimCoreTimeoutError):
                        timeouts += 1
                    recovered_slots, diagnostic = recover_active_slots(
                        client,
                        active_slots,
                        reason=f"close:{error}",
                        error=error,
                    )
                    diagnostics.append(diagnostic)
                    _log_recovery_diagnostic("close", error, diagnostic, len(diagnostics))
                    retryable = []
                    for slot in recovered_slots:
                        if _should_retry_slot(slot, runtime.retry_attempts_per_battle):
                            reporter.retry(slot, str(error))
                            retryable.append(slot)
                        else:
                            reporter.failed(slot, str(error))
                    active_slots = retryable
                    client = _create_client(command, cwd)
                    warmup_sim_core(client, runtime, format_name=format_name)
                    continue

                for slot in terminated_slots:
                    winner = slot.last_result["winner"]
                    if winner == "p1":
                        wins += 1
                    elif winner == "p2":
                        losses += 1
                    else:
                        ties += 1

                    # Finalize trace if tracing enabled and should trace this battle
                    if tracer is not None and traced_battles < trace_max_battles and random.random() < trace_sample_rate:
                        tracer.start_battle(slot.battle_index, slot.env_id, format_name)

                        # Directly populate the battle trace with all collected steps
                        trace_steps = slot_trace_data.get(slot.slot_id, [])
                        if trace_steps:
                            # Group steps by turn
                            turns_dict = {}
                            for step in trace_steps:
                                turn_num = step.get("turn", 0)
                                if turn_num not in turns_dict:
                                    turns_dict[turn_num] = {"turn": turn_num, "steps": []}
                                turns_dict[turn_num]["steps"].append(step)

                            # Store turns in order
                            tracer.current_battle["turns"] = [turns_dict[t] for t in sorted(turns_dict.keys())]
                            tracer.current_battle["total_turns"] = len(turns_dict)

                            # Collect all protocol logs
                            all_protocol_lines = []
                            for step in trace_steps:
                                all_protocol_lines.extend(step.get("protocol_log", []))
                            tracer.current_battle["protocol_log"] = all_protocol_lines

                        tracer.finalize_battle(winner, diagnostics=[])
                        traced_battles += 1

                        # Clean up trace data
                        if slot.slot_id in slot_trace_data:
                            del slot_trace_data[slot.slot_id]

                    battle_events = client.take_latency_events(slot.env_id)
                    all_rpc_events.extend(battle_events)
                    battle_profiles.append(
                        {
                            "battle_index": slot.battle_index + 1,
                            "env_id": slot.env_id,
                            "winner": winner,
                            "steps": slot.step_index,
                            "wall_time_ms": (time.perf_counter() - slot.started_at) * 1000.0,
                            "rpc": summarize_rpc_events(battle_events),
                        }
                    )

                    completed_battles += 1
                    reporter.completed(
                        completed_battles,
                        active_slots=max(0, len(active_slots) - len(terminated_slots)),
                        extra={"wins": wins, "losses": losses, "ties": ties},
                    )

                active_slots = [slot for slot in active_slots if slot not in terminated_slots]

        report = {
            "profile": runtime.profile,
            "num_envs": runtime.num_envs,
            "num_battles": num_battles,
            "successful_battles": completed_battles,
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "win_rate": wins / max(1, completed_battles),
            "avg_steps": total_steps / max(1, completed_battles),
            "avg_latency_ms": sum(inference_latencies) / max(1, len(inference_latencies)),
            "latency": {
                "wall_time_ms": (time.perf_counter() - run_started) * 1000.0,
                "model_inference_ms": summarize_samples(inference_latencies),
                "batch_inference_ms": summarize_samples(batch_inference_latencies),
                "rpc": summarize_rpc_events(all_rpc_events),
                "slowest_battles": top_slowest_battles(battle_profiles),
                "battle_profiles": battle_profiles,
            },
            "timeouts": timeouts,
            "retries": reporter.retries,
            "failed_attempts": reporter.failed_attempts,
            "heartbeat_count": reporter.heartbeats,
            "diagnostics": diagnostics,
        }

        # Add metadata to report
        metadata = create_run_metadata(
            config_path_str,
            config.get("profile", "full"),
        )
        report.update(metadata)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_report(output_path, report)
        print_line_safe(f"eval | wrote report to {output_path}")

        write_json_report(
            latency_output_path,
            {
                "phase": "evaluation",
                "profile": runtime.profile,
                "num_envs": runtime.num_envs,
                "num_battles": num_battles,
                "successful_battles": completed_battles,
                "win_rate": report["win_rate"],
                "timeouts": timeouts,
                "retries": reporter.retries,
                "failed_attempts": reporter.failed_attempts,
                "heartbeat_count": reporter.heartbeats,
                "latency": report["latency"],
                "diagnostics": diagnostics,
            },
        )
        print_line_safe(f"eval | wrote latency report to {latency_output_path}")

        # Final single-line summary (NOT multi-line JSON)
        summary_data = {
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "win_rate": report["win_rate"],
            "avg_steps": report["avg_steps"],
            "retries": reporter.retries,
            "timeouts": timeouts,
            "report": str(output_path),
        }
        summary_line = format_summary("eval", summary_data)
        print_line_safe(summary_line)

        # Drain any remaining latency events before closing to prevent memory leak
        remaining_events = client.take_latency_events()
        if remaining_events:
            all_rpc_events.extend(remaining_events)

        # Add trace info to report if tracing was enabled
        if tracer is not None:
            trace_dir = tracer.base_dir
            report["traces"] = str(trace_dir)
            report["traces_written"] = traced_battles
            print_line_safe(f"eval | traces={trace_dir}")

        reporter.done(f"latency={latency_output_path}")
        return report
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a trained policy against a sim-core baseline.")
    parser.add_argument("--config", required=True, help="Path to the experiment config.")
    args = parser.parse_args()

    config = load_config(args.config)
    run_evaluation(config)


if __name__ == "__main__":
    main()
