import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .env_client import SimCoreClient
from .runtime import EnvSlot, MINIMAL_STEP_OPTIONS, ProgressReporter, RuntimeOptions, choose_timeout, describe_pending


def unwrap_batch_results(responses: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for response in responses:
        if not response.get("ok"):
            error = response.get("error", {})
            raise RuntimeError(error.get("message", "Unknown batched sim-core error."))
        result = response.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("Batched sim-core response is missing a dict result payload.")
        results.append(result)
    return results


def make_wait_hook(reporter: ProgressReporter, active_slots: Sequence[EnvSlot], operation: str) -> Callable[[Dict[str, Any], float], None]:
    def _hook(_payload: Dict[str, Any], _elapsed: float) -> None:
        reporter.maybe_heartbeat(active_slots, describe_pending(operation, active_slots))

    return _hook


def warmup_sim_core(
    client: SimCoreClient,
    runtime: RuntimeOptions,
    *,
    format_name: str,
) -> None:
    env_id = client.create_env(
        format_name=format_name,
        players={"p1": {"controller": "external"}, "p2": {"controller": "random"}},
        timeout_sec=choose_timeout(runtime, "create_env"),
    )
    try:
        result = client.reset(
            env_id,
            options=MINIMAL_STEP_OPTIONS,
            timeout_sec=choose_timeout(runtime, "reset"),
        )
        if not result["terminated"]:
            request = result["requests"].get("p1")
            if request is not None:
                actions = request["legal_actions"]["actions"]
                choice = next((action["choice"] for action in actions if action), "default")
                client.step(
                    env_id,
                    {"p1": choice},
                    options=MINIMAL_STEP_OPTIONS,
                    timeout_sec=choose_timeout(runtime, "step"),
                )
    finally:
        client.close_env(env_id, timeout_sec=choose_timeout(runtime, "close_env"))
        client.take_latency_events(env_id)


def initialize_slots(
    client: SimCoreClient,
    slots: Sequence[EnvSlot],
    *,
    runtime: RuntimeOptions,
    format_name: str,
    players: Dict[str, Dict[str, str]],
    response_options: Dict[str, Any],
    reporter: ProgressReporter,
    operation_name: str,
) -> None:
    if not slots:
        return

    create_requests = [
        {
            "type": "create_env",
            "format": format_name,
            "seed": list(slot.seed),
            "players": players,
        }
        for slot in slots
    ]
    create_results = unwrap_batch_results(
        client.batch_request(
            create_requests,
            timeout_sec=choose_timeout(runtime, "create_env"),
            on_wait=make_wait_hook(reporter, slots, f"{operation_name}-create"),
        )
    )
    for slot, result in zip(slots, create_results):
        slot.env_id = str(result["env_id"])

    reset_requests = [
        {
            "type": "reset",
            "env_id": slot.env_id,
            "options": response_options,
        }
        for slot in slots
    ]
    reset_results = unwrap_batch_results(
        client.batch_request(
            reset_requests,
            timeout_sec=choose_timeout(runtime, "reset"),
            on_wait=make_wait_hook(reporter, slots, f"{operation_name}-reset"),
        )
    )
    for slot, result in zip(slots, reset_results):
        slot.started_at = time.perf_counter()
        slot.last_result = result
        slot.step_index = 0
        slot.pending_episode_records = []


def close_slots(
    client: SimCoreClient,
    slots: Sequence[EnvSlot],
    *,
    runtime: RuntimeOptions,
    reporter: ProgressReporter,
    operation_name: str,
) -> None:
    if not slots:
        return
    close_requests = [{"type": "close_env", "env_id": slot.env_id} for slot in slots if slot.env_id]
    if not close_requests:
        return
    unwrap_batch_results(
        client.batch_request(
            close_requests,
            timeout_sec=choose_timeout(runtime, "close_env"),
            on_wait=make_wait_hook(reporter, slots, f"{operation_name}-close"),
        )
    )
    # Important: drain latency events for these closed environments to prevent memory leak
    for slot in slots:
        if slot.env_id:
            client.take_latency_events(slot.env_id)


def recover_active_slots(
    client: SimCoreClient,
    active_slots: Sequence[EnvSlot],
    *,
    reason: str,
    error: Optional[BaseException] = None,
) -> Tuple[List[EnvSlot], Dict[str, Any]]:
    diagnostics = client.snapshot_diagnostics()
    diagnostics["reason"] = reason
    timeout_diagnostics = getattr(error, "diagnostics", None)
    if isinstance(timeout_diagnostics, dict) and timeout_diagnostics:
        diagnostics["timeout_error"] = timeout_diagnostics
    diagnostics["active_slots"] = [
        _slot_diagnostics(slot)
        for slot in active_slots
    ]

    client.close()

    retryable: List[EnvSlot] = []
    for slot in active_slots:
        slot.retry_count += 1
        slot.restart()
        retryable.append(slot)

    return retryable, diagnostics


def _slot_diagnostics(slot: EnvSlot) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "battle_index": slot.battle_index,
        "battle_number": slot.battle_index + 1,
        "seed": list(slot.seed),
        "retry_count": slot.retry_count,
        "env_id": slot.env_id,
        "step_index": slot.step_index,
        "wall_time_sec": round(time.perf_counter() - slot.started_at, 3),
    }
    if slot.last_result is not None:
        summary["last_result"] = _summarize_step_result(slot.last_result)
    return summary


def _summarize_step_result(result: Dict[str, Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for key in ("env_id", "terminated", "winner"):
        if key in result:
            summary[key] = result.get(key)

    info = result.get("info")
    if isinstance(info, dict):
        summary["turn"] = info.get("turn")
        summary["format"] = info.get("format")

    requests = result.get("requests")
    if isinstance(requests, dict):
        request_summary: Dict[str, Any] = {}
        for player, request in requests.items():
            if isinstance(request, dict):
                request_summary[str(player)] = _summarize_choice_request(request)
            elif request is None:
                request_summary[str(player)] = None
        summary["requests"] = request_summary

    views = result.get("views")
    if isinstance(views, dict):
        view_summary: Dict[str, Any] = {}
        for player, view in views.items():
            if isinstance(view, dict):
                view_summary[str(player)] = _summarize_battle_view(view)
        summary["views"] = view_summary

    return summary


def _summarize_choice_request(request: Dict[str, Any]) -> Dict[str, Any]:
    legal_actions = request.get("legal_actions") or {}
    actions = legal_actions.get("actions")
    return {
        "wait": request.get("wait"),
        "team_preview": request.get("team_preview"),
        "force_switch": request.get("force_switch"),
        "rqid": request.get("rqid"),
        "legal_action_count": sum(1 for action in actions if action) if isinstance(actions, list) else None,
    }


def _summarize_battle_view(view: Dict[str, Any]) -> Dict[str, Any]:
    field = view.get("field") if isinstance(view.get("field"), dict) else {}
    summary: Dict[str, Any] = {
        "turn": view.get("turn"),
        "winner": view.get("winner"),
        "terminated": view.get("terminated"),
    }
    if isinstance(field, dict):
        summary["weather"] = field.get("weather")
        summary["terrain"] = field.get("terrain")

    self_team = view.get("self_team")
    if isinstance(self_team, list):
        active_names = []
        for pokemon in self_team:
            if isinstance(pokemon, dict) and pokemon.get("active"):
                active_names.append(pokemon.get("species") or pokemon.get("ident"))
        summary["self_active"] = active_names

    opponent_team = view.get("opponent_team")
    if isinstance(opponent_team, list):
        active_names = []
        for pokemon in opponent_team:
            if isinstance(pokemon, dict) and pokemon.get("active"):
                active_names.append(pokemon.get("species") or pokemon.get("ident"))
        summary["opponent_active"] = active_names

    return summary
