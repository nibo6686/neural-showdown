import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence


WaitHook = Callable[[Dict[str, Any], float], None]


class SimCoreError(RuntimeError):
    pass


class SimCoreProcessExitedError(SimCoreError):
    pass


class SimCoreTimeoutError(SimCoreError):
    def __init__(
        self,
        message: str,
        payload: Dict[str, Any],
        elapsed_sec: float,
        stderr_lines: List[str],
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.payload = payload
        self.elapsed_sec = elapsed_sec
        self.stderr_lines = stderr_lines
        self.diagnostics = diagnostics or {}


class SimCoreClient:
    def __init__(self, command: Sequence[str], cwd: str) -> None:
        env = dict(os.environ)
        env.setdefault("SIM_CORE_TRACE_RPC", "1")
        env.setdefault("SIM_CORE_TRACE_SLOW_MS", "5000")
        self._process = subprocess.Popen(
            list(command),
            cwd=str(Path(cwd)),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self._send_lock = threading.Lock()
        self._pending_lock = threading.Lock()
        self._stderr_lines: List[str] = []
        self._open_envs: List[str] = []
        self._latency_events: List[Dict[str, Any]] = []
        self._recent_latency_events: List[Dict[str, Any]] = []
        self._pending: Dict[str, "queue.Queue[Dict[str, Any]]"] = {}
        self._request_counter = 0
        self._response_counter = 0
        self._orphan_response_count = 0
        self._last_request: Optional[Dict[str, Any]] = None
        self._last_response: Optional[Dict[str, Any]] = None
        self._last_request_at: Optional[float] = None
        self._last_response_at: Optional[float] = None
        self._last_orphan_response: Optional[Dict[str, Any]] = None
        self._closing = False

        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def close(self) -> None:
        self._closing = True
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._notify_process_exit("sim-core client closed.")

    def __enter__(self) -> "SimCoreClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def ping(self, timeout_sec: Optional[float] = None, on_wait: Optional[WaitHook] = None) -> Dict[str, Any]:
        return self._request({"id": self._next_id("ping"), "type": "ping"}, timeout_sec=timeout_sec, on_wait=on_wait)

    def create_env(
        self,
        format_name: str = "gen9randombattle",
        seed: Optional[Iterable[int]] = None,
        players: Optional[Dict[str, Dict[str, str]]] = None,
        timeout_sec: Optional[float] = None,
        on_wait: Optional[WaitHook] = None,
    ) -> str:
        result = self._request(
            {
                "id": self._next_id("create"),
                "type": "create_env",
                "format": format_name,
                "seed": list(seed) if seed is not None else None,
                "players": players,
            },
            timeout_sec=timeout_sec,
            on_wait=on_wait,
        )
        env_id = result["env_id"]
        if env_id not in self._open_envs:
            self._open_envs.append(env_id)
        return env_id

    def reset(
        self,
        env_id: str,
        options: Optional[Dict[str, Any]] = None,
        timeout_sec: Optional[float] = None,
        on_wait: Optional[WaitHook] = None,
    ) -> Dict[str, Any]:
        payload = {"id": self._next_id("reset"), "type": "reset", "env_id": env_id}
        if options:
            payload["options"] = options
        return self._request(payload, timeout_sec=timeout_sec, on_wait=on_wait)

    def step(
        self,
        env_id: str,
        choices: Dict[str, str],
        options: Optional[Dict[str, Any]] = None,
        timeout_sec: Optional[float] = None,
        on_wait: Optional[WaitHook] = None,
    ) -> Dict[str, Any]:
        payload = {
            "id": self._next_id("step"),
            "type": "step",
            "env_id": env_id,
            "choices": choices,
        }
        if options:
            payload["options"] = options
        return self._request(payload, timeout_sec=timeout_sec, on_wait=on_wait)

    def close_env(
        self,
        env_id: str,
        timeout_sec: Optional[float] = None,
        on_wait: Optional[WaitHook] = None,
    ) -> Dict[str, Any]:
        result = self._request(
            {"id": self._next_id("close"), "type": "close_env", "env_id": env_id},
            timeout_sec=timeout_sec,
            on_wait=on_wait,
        )
        if env_id in self._open_envs:
            self._open_envs.remove(env_id)
        return result

    def agent_action(
        self,
        env_id: str,
        player: str,
        agent: str,
        timeout_sec: Optional[float] = None,
        on_wait: Optional[WaitHook] = None,
    ) -> Dict[str, Any]:
        return self._request(
            {
                "id": self._next_id("agent"),
                "type": "agent_action",
                "env_id": env_id,
                "player": player,
                "agent": agent,
            },
            timeout_sec=timeout_sec,
            on_wait=on_wait,
        )

    def batch_request(
        self,
        requests: Sequence[Dict[str, Any]],
        timeout_sec: Optional[float] = None,
        on_wait: Optional[WaitHook] = None,
    ) -> List[Dict[str, Any]]:
        normalized_requests: List[Dict[str, Any]] = []
        for request in requests:
            item = dict(request)
            item.setdefault("id", self._next_id(str(item.get("type", "request"))))
            normalized_requests.append(item)

        payload = {
            "id": self._next_id("batch"),
            "type": "batch",
            "requests": normalized_requests,
        }
        result = self._request(payload, timeout_sec=timeout_sec, on_wait=on_wait)
        responses = result.get("responses")
        if not isinstance(responses, list):
            raise SimCoreError("sim-core batch response is missing result.responses.")
        self._apply_batch_env_updates(responses)
        return responses

    def take_latency_events(self, env_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if env_id is None:
            events = list(self._latency_events)
            self._latency_events.clear()
            return events

        matching: List[Dict[str, Any]] = []
        remaining: List[Dict[str, Any]] = []
        for event in self._latency_events:
            if event.get("env_id") == env_id:
                matching.append(event)
            else:
                remaining.append(event)
        self._latency_events = remaining
        return matching

    def snapshot_diagnostics(self) -> Dict[str, Any]:
        now = time.perf_counter()
        return {
            "last_request": dict(self._last_request) if self._last_request else None,
            "last_response": dict(self._last_response) if self._last_response else None,
            "last_request_age_sec": round(now - self._last_request_at, 3) if self._last_request_at else None,
            "last_response_age_sec": round(now - self._last_response_at, 3) if self._last_response_at else None,
            "last_orphan_response": dict(self._last_orphan_response) if self._last_orphan_response else None,
            "recent_stderr": list(self._stderr_lines[-80:]),
            "recent_rpc_events": list(self._recent_latency_events[-50:]),
            "open_envs": list(self._open_envs),
            "process_alive": self._process.poll() is None,
            "process_pid": self._process.pid,
            "request_count": self._request_counter,
            "response_count": self._response_counter,
            "orphan_response_count": self._orphan_response_count,
            "pending_request_ids": self._pending_request_ids(),
            "latency_event_backlog": len(self._latency_events),
        }

    def _request(self, payload: Dict[str, Any], timeout_sec: Optional[float], on_wait: Optional[WaitHook]) -> Dict[str, Any]:
        if self._process.stdin is None:
            raise SimCoreError("sim-core process stdin is unavailable.")
        if self._process.poll() is not None:
            raise SimCoreProcessExitedError(self._format_exit_message())

        response_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        request_id = str(payload["id"])
        with self._pending_lock:
            self._pending[request_id] = response_queue

        message = json.dumps(payload)
        started_at = time.perf_counter()
        self._last_request = self._summarize_payload(payload)
        self._last_request_at = started_at
        try:
            with self._send_lock:
                self._process.stdin.write(message + "\n")
                self._process.stdin.flush()

            response = self._wait_for_response(response_queue, payload, started_at, timeout_sec, on_wait)
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)

        round_trip_ms = (time.perf_counter() - started_at) * 1000.0
        self._last_response = self._summarize_response(response)
        self._last_response_at = time.perf_counter()
        self._record_latency(payload, response, round_trip_ms)

        if not response.get("ok"):
            error = response.get("error", {})
            raise SimCoreError(error.get("message", "Unknown sim-core error."))

        self._apply_single_env_updates(payload, response.get("result"))
        return response.get("result")

    def _wait_for_response(
        self,
        response_queue: "queue.Queue[Dict[str, Any]]",
        payload: Dict[str, Any],
        started_at: float,
        timeout_sec: Optional[float],
        on_wait: Optional[WaitHook],
    ) -> Dict[str, Any]:
        deadline = started_at + timeout_sec if timeout_sec is not None else None
        while True:
            now = time.perf_counter()
            wait_timeout = 1.0
            if deadline is not None:
                remaining = deadline - now
                if remaining <= 0:
                    diagnostics = self._build_timeout_diagnostics(payload, started_at, timeout_sec)
                    raise SimCoreTimeoutError(
                        self._format_timeout_message(payload, timeout_sec, diagnostics),
                        payload,
                        time.perf_counter() - started_at,
                        list(self._stderr_lines[-80:]),
                        diagnostics,
                    )
                wait_timeout = min(wait_timeout, remaining)

            try:
                response = response_queue.get(timeout=wait_timeout)
            except queue.Empty:
                if on_wait is not None:
                    on_wait(payload, time.perf_counter() - started_at)
                continue

            if response.get("_process_exit"):
                raise SimCoreProcessExitedError(self._format_exit_message())
            return response

    def _read_stdout(self) -> None:
        if self._process.stdout is None:
            return
        for raw_line in self._process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                response = json.loads(line)
            except json.JSONDecodeError:
                self._stderr_lines.append(f"[stdout-json-error] {line}")
                self._trim_stderr()
                continue

            self._response_counter += 1
            request_id = str(response.get("id"))
            with self._pending_lock:
                response_queue = self._pending.get(request_id)
            if response_queue is not None:
                response_queue.put(response)
            else:
                self._orphan_response_count += 1
                self._last_orphan_response = self._summarize_response(response)

        if not self._closing:
            self._notify_process_exit("sim-core stdout closed unexpectedly.")

    def _read_stderr(self) -> None:
        if self._process.stderr is None:
            return
        for line in self._process.stderr:
            self._stderr_lines.append(line.rstrip())
            self._trim_stderr()

    def _trim_stderr(self) -> None:
        if len(self._stderr_lines) > 200:
            self._stderr_lines = self._stderr_lines[-200:]

    def _notify_process_exit(self, message: str) -> None:
        sentinel = {"_process_exit": True, "message": message}
        with self._pending_lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for response_queue in pending:
            response_queue.put(dict(sentinel))

    def _format_exit_message(self) -> str:
        stderr = "\n".join(self._stderr_lines[-20:])
        if stderr:
            return f"sim-core process exited early.\n{stderr}"
        return "sim-core process exited early."

    def _next_id(self, prefix: str) -> str:
        self._request_counter += 1
        return f"{prefix}:{self._request_counter}"

    def _pending_request_ids(self) -> List[str]:
        with self._pending_lock:
            return sorted(self._pending.keys())

    def _build_timeout_diagnostics(
        self,
        payload: Dict[str, Any],
        started_at: float,
        timeout_sec: Optional[float],
    ) -> Dict[str, Any]:
        diagnostics = self.snapshot_diagnostics()
        diagnostics.update(
            {
                "timeout_sec": timeout_sec,
                "elapsed_sec": round(time.perf_counter() - started_at, 3),
                "timed_out_request": self._summarize_payload(payload),
            }
        )
        return diagnostics

    def _format_timeout_message(
        self,
        payload: Dict[str, Any],
        timeout_sec: Optional[float],
        diagnostics: Dict[str, Any],
    ) -> str:
        timeout_label = f"{timeout_sec:.1f}s" if timeout_sec is not None else "unknown timeout"
        summary = diagnostics.get("timed_out_request") or self._summarize_payload(payload)
        parts = [
            f"sim-core request timed out after {timeout_label}",
            f"type={summary.get('type')}",
            f"id={summary.get('id')}",
        ]
        if summary.get("request_count") is not None:
            parts.append(f"subrequests={summary.get('request_count')}")
        if summary.get("request_types"):
            request_types = ",".join(f"{key}:{value}" for key, value in sorted(summary["request_types"].items()))
            parts.append(f"request_types={request_types}")
        if summary.get("env_ids"):
            parts.append(f"envs={','.join(summary['env_ids'])}")
        return " ".join(parts) + "."

    def _summarize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "id": payload.get("id"),
            "type": payload.get("type"),
        }
        request_type = payload.get("type")
        if request_type == "batch":
            requests = payload.get("requests")
            if isinstance(requests, list):
                type_counts: Dict[str, int] = {}
                env_ids: List[str] = []
                samples: List[Dict[str, Any]] = []
                for request in requests:
                    if not isinstance(request, dict):
                        continue
                    sub_type = str(request.get("type", "unknown"))
                    type_counts[sub_type] = type_counts.get(sub_type, 0) + 1
                    env_id = request.get("env_id")
                    if isinstance(env_id, str) and env_id not in env_ids:
                        env_ids.append(env_id)
                    if len(samples) < 8:
                        samples.append(self._summarize_single_request(request))
                summary.update(
                    {
                        "request_count": len(requests),
                        "request_types": type_counts,
                        "env_ids": env_ids,
                        "sample_requests": samples,
                    }
                )
            return summary

        summary.update(self._summarize_single_request(payload))
        return summary

    def _summarize_single_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "id": request.get("id"),
            "type": request.get("type"),
        }
        env_id = request.get("env_id")
        if isinstance(env_id, str):
            summary["env_id"] = env_id
        if request.get("type") == "create_env":
            summary["format"] = request.get("format")
            if request.get("seed") is not None:
                summary["seed"] = request.get("seed")
        if request.get("type") == "step":
            choices = request.get("choices")
            if isinstance(choices, dict):
                summary["choices"] = {str(key): str(value) for key, value in choices.items()}
        if request.get("type") == "agent_action":
            summary["player"] = request.get("player")
            summary["agent"] = request.get("agent")
        return summary

    def _summarize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "id": response.get("id"),
            "ok": bool(response.get("ok")),
            "meta": response.get("meta"),
        }
        if not response.get("ok"):
            error = response.get("error")
            if isinstance(error, dict):
                summary["error"] = {"message": error.get("message")}
            return summary

        result = response.get("result")
        if isinstance(result, dict):
            if "responses" in result and isinstance(result.get("responses"), list):
                responses = result["responses"]
                type_counts: Dict[str, int] = {}
                env_ids: List[str] = []
                error_count = 0
                samples: List[Dict[str, Any]] = []
                for child in responses:
                    if not isinstance(child, dict):
                        continue
                    child_meta = child.get("meta") or {}
                    request_type = str(child_meta.get("request_type", "unknown"))
                    type_counts[request_type] = type_counts.get(request_type, 0) + 1
                    env_id = child_meta.get("env_id")
                    if isinstance(env_id, str) and env_id not in env_ids:
                        env_ids.append(env_id)
                    if not child.get("ok"):
                        error_count += 1
                    if len(samples) < 8:
                        samples.append(self._summarize_child_response(child))
                summary["result"] = {
                    "response_count": len(responses),
                    "ok_count": len(responses) - error_count,
                    "error_count": error_count,
                    "request_types": type_counts,
                    "env_ids": env_ids,
                    "sample_responses": samples,
                }
            else:
                summary["result"] = self._summarize_result(result)
        else:
            summary["result_type"] = type(result).__name__
        return summary

    def _summarize_child_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        meta = response.get("meta") or {}
        summary: Dict[str, Any] = {
            "id": response.get("id"),
            "ok": bool(response.get("ok")),
            "request_type": meta.get("request_type"),
            "env_id": meta.get("env_id"),
            "queue_wait_ms": meta.get("queue_wait_ms"),
            "server_elapsed_ms": meta.get("server_elapsed_ms"),
        }
        if response.get("ok"):
            result = response.get("result")
            if isinstance(result, dict):
                summary["result"] = self._summarize_result(result)
        else:
            error = response.get("error")
            if isinstance(error, dict):
                summary["error"] = {"message": error.get("message")}
        return summary

    def _summarize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
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
                    legal_actions = request.get("legal_actions") or {}
                    actions = legal_actions.get("actions")
                    request_summary[str(player)] = {
                        "wait": request.get("wait"),
                        "team_preview": request.get("team_preview"),
                        "force_switch": request.get("force_switch"),
                        "legal_action_count": sum(1 for action in actions if action) if isinstance(actions, list) else None,
                    }
            summary["requests"] = request_summary
        return summary

    def _apply_single_env_updates(self, payload: Dict[str, Any], result: Any) -> None:
        request_type = payload.get("type")
        if request_type == "create_env" and isinstance(result, dict):
            env_id = result.get("env_id")
            if isinstance(env_id, str) and env_id not in self._open_envs:
                self._open_envs.append(env_id)
        if request_type == "close_env":
            env_id = payload.get("env_id")
            if isinstance(env_id, str) and env_id in self._open_envs:
                self._open_envs.remove(env_id)

    def _apply_batch_env_updates(self, responses: Sequence[Dict[str, Any]]) -> None:
        for response in responses:
            if not response.get("ok"):
                continue
            result = response.get("result")
            meta = response.get("meta", {})
            request_type = meta.get("request_type")
            if request_type == "create_env" and isinstance(result, dict):
                env_id = result.get("env_id")
                if isinstance(env_id, str) and env_id not in self._open_envs:
                    self._open_envs.append(env_id)
            if request_type == "close_env":
                env_id = meta.get("env_id")
                if isinstance(env_id, str) and env_id in self._open_envs:
                    self._open_envs.remove(env_id)

    def _record_latency(self, payload: Dict[str, Any], response: Dict[str, Any], round_trip_ms: float) -> None:
        meta = response.get("meta") or {}
        result = response.get("result")
        if payload.get("type") == "batch" and isinstance(result, dict):
            responses = result.get("responses", [])
            if isinstance(responses, list):
                self._record_batch_latency(responses, meta, round_trip_ms)
                return

        env_id = payload.get("env_id")
        if payload.get("type") == "create_env" and isinstance(result, dict):
            env_id = result.get("env_id", env_id)
        self._append_latency_event(
            request_id=payload.get("id"),
            request_type=payload.get("type"),
            env_id=env_id,
            ok=bool(response.get("ok")),
            round_trip_ms=round_trip_ms,
            meta=meta,
        )

    def _record_batch_latency(self, responses: Sequence[Dict[str, Any]], batch_meta: Dict[str, Any], round_trip_ms: float) -> None:
        if not responses:
            return
        batch_server_ms = batch_meta.get("server_elapsed_ms")
        batch_queue_ms = batch_meta.get("queue_wait_ms")
        batch_transport_ms = None
        if isinstance(batch_server_ms, (int, float)):
            batch_transport_ms = round_trip_ms - float(batch_server_ms)
            if isinstance(batch_queue_ms, (int, float)):
                batch_transport_ms -= float(batch_queue_ms)
            batch_transport_ms = max(0.0, batch_transport_ms)

        distributed_transport_ms = None
        if batch_transport_ms is not None:
            distributed_transport_ms = batch_transport_ms / max(1, len(responses))

        for response in responses:
            meta = response.get("meta") or {}
            self._append_latency_event(
                request_id=response.get("id"),
                request_type=meta.get("request_type"),
                env_id=meta.get("env_id"),
                ok=bool(response.get("ok")),
                round_trip_ms=float(meta.get("server_elapsed_ms", 0.0))
                + float(meta.get("queue_wait_ms", 0.0))
                + float(distributed_transport_ms or 0.0),
                meta=meta,
                transport_override_ms=distributed_transport_ms,
            )

    def _append_latency_event(
        self,
        *,
        request_id: Any,
        request_type: Any,
        env_id: Any,
        ok: bool,
        round_trip_ms: float,
        meta: Dict[str, Any],
        transport_override_ms: Optional[float] = None,
    ) -> None:
        server_elapsed_ms = meta.get("server_elapsed_ms")
        queue_wait_ms = meta.get("queue_wait_ms")
        transport_overhead_ms = transport_override_ms
        if transport_overhead_ms is None and isinstance(server_elapsed_ms, (int, float)):
            transport_overhead_ms = round_trip_ms - float(server_elapsed_ms)
            if isinstance(queue_wait_ms, (int, float)):
                transport_overhead_ms -= float(queue_wait_ms)
            transport_overhead_ms = max(0.0, transport_overhead_ms)

        event = {
            "request_id": request_id,
            "request_type": request_type,
            "env_id": env_id,
            "ok": ok,
            "round_trip_ms": float(round_trip_ms),
            "queue_wait_ms": float(queue_wait_ms) if isinstance(queue_wait_ms, (int, float)) else None,
            "server_elapsed_ms": float(server_elapsed_ms) if isinstance(server_elapsed_ms, (int, float)) else None,
            "transport_overhead_ms": float(transport_overhead_ms) if transport_overhead_ms is not None else None,
        }
        self._latency_events.append(event)
        self._recent_latency_events.append(dict(event))
        if len(self._recent_latency_events) > 200:
            self._recent_latency_events = self._recent_latency_events[-200:]
        if len(self._latency_events) > 20000:
            self._latency_events = self._latency_events[-20000:]
