import argparse
import gzip
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from .config import load_config, resolve_path, resolve_process_spec
from .env_client import SimCoreClient, SimCoreProcessExitedError, SimCoreTimeoutError
from .featurize import featurize_battle
from .latency import summarize_rpc_events, summarize_samples, top_slowest_battles, write_json_report
from .logging_helper import format_summary, print_line_safe, write_json_summary
from .metadata_helper import create_run_metadata
from .runner import close_slots, initialize_slots, make_wait_hook, recover_active_slots, unwrap_batch_results, warmup_sim_core
from .runtime import EnvSlot, MINIMAL_STEP_OPTIONS, ProgressReporter, choose_timeout, load_runtime_options, make_battle_seed


def write_shard(records: List[Dict[str, Any]], shard_path: Path) -> Dict[str, Any]:
    states = []
    masks = []
    actions = []
    returns = []
    featurize_latencies: List[float] = []
    started_at = time.perf_counter()
    for record in records:
        feature_started = time.perf_counter()
        features = featurize_battle(record["view"], record["request"])
        featurize_latencies.append((time.perf_counter() - feature_started) * 1000.0)
        states.append(features.flat)
        masks.append(features.legal_mask)
        actions.append(record["action_index"])
        returns.append(record["return"])

    shard_path.parent.mkdir(parents=True, exist_ok=True)
    save_started = time.perf_counter()
    np.savez(
        shard_path,
        states=np.asarray(states, dtype=np.float32),
        legal_masks=np.asarray(masks, dtype=np.float32),
        actions=np.asarray(actions, dtype=np.int64),
        returns=np.asarray(returns, dtype=np.float32),
    )
    save_ms = (time.perf_counter() - save_started) * 1000.0
    total_ms = (time.perf_counter() - started_at) * 1000.0
    return {
        "records": len(records),
        "featurize_ms": summarize_samples(featurize_latencies),
        "save_ms": save_ms,
        "total_ms": total_ms,
    }


def write_records_jsonl(records: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output_path, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def merge_shards(shard_paths: Sequence[Path], output_path: Path) -> Dict[str, Any]:
    arrays: Dict[str, List[np.ndarray]] = {"states": [], "legal_masks": [], "actions": [], "returns": []}
    for shard_path in shard_paths:
        if not shard_path.exists():
            continue
        with np.load(shard_path) as data:
            for key in arrays:
                arrays[key].append(data[key])

    if not arrays["states"]:
        raise ValueError("No shard data was available to merge.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged = {key: np.concatenate(values, axis=0) for key, values in arrays.items()}
    np.savez(output_path, **merged)
    return {
        "output_path": str(output_path),
        "source_shards": [str(path) for path in shard_paths if path.exists()],
        "records": int(merged["states"].shape[0]),
    }


def collect_dataset(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    records, _ = collect_dataset_run(config)
    return records


def _create_client(command: Sequence[str], cwd: str) -> SimCoreClient:
    return SimCoreClient(command, cwd)


def _should_retry_slot(slot: EnvSlot, retry_limit: int) -> bool:
    return slot.retry_count <= retry_limit


def collect_dataset_run(config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    command, cwd = resolve_process_spec(config)
    dataset_cfg = config.get("dataset", {})
    runtime = load_runtime_options(config, default_num_envs=1)
    num_battles = int(dataset_cfg.get("num_battles", 32))
    format_name = dataset_cfg.get("format", "gen9randombattle")
    record_player = dataset_cfg.get("record_player", "p1")
    matchup = dataset_cfg.get("controller_matchup", {"p1": "heuristic", "p2": "random"})
    record_agent = matchup.get(record_player, "heuristic")
    other_player = "p2" if record_player == "p1" else "p1"
    other_agent = matchup.get(other_player, "random")

    players = {
        record_player: {"controller": "external"},
        other_player: {"controller": other_agent},
    }
    source_name = dataset_cfg.get("source", "sim-core")

    reporter = ProgressReporter("dataset", runtime.profile, num_battles, runtime.num_envs, runtime.heartbeat_interval_sec)
    records: List[Dict[str, Any]] = []
    battle_profiles: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []
    all_rpc_events: List[Dict[str, Any]] = []
    completed_battles = 0
    timeouts = 0
    next_battle_index = 0
    next_slot_id = 0
    active_slots: List[EnvSlot] = []

    client = _create_client(command, cwd)
    try:
        warmup_sim_core(client, runtime, format_name=format_name)
        reporter.start(
            f"timeout(step/reset)={int(choose_timeout(runtime, 'step'))}s/{int(choose_timeout(runtime, 'reset'))}s"
        )
        run_started = time.perf_counter()

        while completed_battles < num_battles or active_slots:
            # Emergency drain if latency events accumulate too much (memory leak safeguard)
            if len(client._latency_events) > 1000:
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
                        operation_name="dataset",
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
                    agent_results = unwrap_batch_results(
                        client.batch_request(
                            [
                                {
                                    "type": "agent_action",
                                    "env_id": slot.env_id,
                                    "player": record_player,
                                    "agent": record_agent,
                                }
                                for slot in ready_slots
                            ],
                            timeout_sec=choose_timeout(runtime, "agent_action"),
                            on_wait=make_wait_hook(reporter, ready_slots, "agent_action"),
                        )
                    )

                    step_requests = []
                    for slot, decision in zip(ready_slots, agent_results):
                        request = slot.last_result["requests"].get(record_player)
                        if request is None:
                            raise RuntimeError(
                                f"No actionable request for {record_player} in battle {slot.battle_index}."
                            )
                        slot.pending_episode_records.append(
                            {
                                "battle_index": slot.battle_index,
                                "step_index": slot.step_index,
                                "player": record_player,
                                "source": source_name,
                                "record_agent": record_agent,
                                "opponent_agent": other_agent,
                                "controller_matchup": dict(matchup),
                                "view": slot.last_result["views"][record_player],
                                "request": request,
                                "choice": decision["choice"],
                                "action_index": int(decision["action_index"]),
                            }
                        )
                        step_requests.append(
                            {
                                "type": "step",
                                "env_id": slot.env_id,
                                "choices": {record_player: decision["choice"]},
                                "options": MINIMAL_STEP_OPTIONS,
                            }
                        )

                    step_results = unwrap_batch_results(
                        client.batch_request(
                            step_requests,
                            timeout_sec=choose_timeout(runtime, "step"),
                            on_wait=make_wait_hook(reporter, ready_slots, "step"),
                        )
                    )
                    for slot, result in zip(ready_slots, step_results):
                        slot.last_result = result
                        slot.step_index += 1
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
                        operation_name="dataset",
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
                    final_return = float(slot.last_result["rewards"][record_player])
                    for record in slot.pending_episode_records:
                        record["return"] = final_return
                    records.extend(slot.pending_episode_records)

                    battle_events = client.take_latency_events(slot.env_id)
                    all_rpc_events.extend(battle_events)
                    battle_profiles.append(
                        {
                            "battle_index": slot.battle_index + 1,
                            "env_id": slot.env_id,
                            "winner": slot.last_result["winner"],
                            "steps": slot.step_index,
                            "labeled_decisions": len(slot.pending_episode_records),
                            "wall_time_ms": (time.perf_counter() - slot.started_at) * 1000.0,
                            "rpc": summarize_rpc_events(battle_events),
                        }
                    )

                    completed_battles += 1
                    reporter.completed(
                        completed_battles,
                        active_slots=max(0, len(active_slots) - len(terminated_slots)),
                        extra={"labels": len(records)},
                    )

                active_slots = [slot for slot in active_slots if slot not in terminated_slots]

        report = {
            "phase": "dataset_build",
            "profile": runtime.profile,
            "num_envs": runtime.num_envs,
            "num_battles": num_battles,
            "successful_battles": completed_battles,
            "num_records": len(records),
            "timeouts": timeouts,
            "retries": reporter.retries,
            "failed_attempts": reporter.failed_attempts,
            "heartbeat_count": reporter.heartbeats,
            "wall_time_ms": (time.perf_counter() - run_started) * 1000.0,
            "rpc": summarize_rpc_events(all_rpc_events),
            "slowest_battles": top_slowest_battles(battle_profiles),
            "battle_profiles": battle_profiles,
            "diagnostics": diagnostics,
        }
        # Drain any remaining latency events before closing to prevent memory leak
        remaining_events = client.take_latency_events()
        if remaining_events:
            all_rpc_events.extend(remaining_events)
            report["rpc"] = summarize_rpc_events(all_rpc_events)
        return records, report
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect heuristic-labeled battle data and build an .npz shard.")
    parser.add_argument("--config", required=True, help="Path to the experiment config.")
    args = parser.parse_args()

    config = load_config(args.config)
    config_path_str = config.get("_config_path", args.config)
    dataset_cfg = config.get("dataset", {})
    output_path = resolve_path(config, dataset_cfg.get("output_path", "../data/raw/dataset.jsonl.gz"))
    shard_path = resolve_path(config, dataset_cfg.get("shard_path", "../data/shards/dataset.npz"))
    latency_output_path = resolve_path(
        config,
        dataset_cfg.get("latency_output_path", "../artifacts/latency/dataset_latency.json"),
    )

    records, latency_report = collect_dataset_run(config)

    write_records_jsonl(records, output_path)

    shard_metrics = write_shard(records, shard_path)
    latency_report["shard_write"] = shard_metrics

    # Add metadata to latency report
    metadata = create_run_metadata(
        config_path_str,
        config.get("profile", "full"),
        dataset_size=len(records),
    )
    latency_report.update(metadata)

    write_json_report(latency_output_path, latency_report)

    # Print single-line summaries for each file
    print_line_safe(f"dataset | wrote={len(records)} decisions to {output_path}")
    print_line_safe(f"dataset | wrote shard to {shard_path}")
    print_line_safe(f"dataset | wrote latency report to {latency_output_path}")

    # Final single-line summary
    summary_data = {
        "battles": latency_report["successful_battles"],
        "labels": len(records),
        "retries": latency_report.get("retries", 0),
        "timeouts": latency_report.get("timeouts", 0),
        "report": str(latency_output_path),
    }
    summary_line = format_summary("dataset", summary_data)
    print_line_safe(summary_line)


if __name__ == "__main__":
    main()
