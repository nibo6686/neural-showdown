import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence


DEFAULT_TIMEOUTS_SEC = {
    "create_env": 15.0,
    "reset": 45.0,
    "step": 20.0,
    "agent_action": 10.0,
    "close_env": 5.0,
    "ping": 5.0,
    "batch": 45.0,
}

MINIMAL_STEP_OPTIONS = {
    "view_players": ["p1"],
    "include_log_delta": True,
    "include_possible_roles": False,
}


@dataclass
class RuntimeOptions:
    profile: str
    num_envs: int
    heartbeat_interval_sec: float
    retry_attempts_per_battle: int
    timeouts_sec: Dict[str, float]


@dataclass
class EnvSlot:
    slot_id: int
    battle_index: int
    seed: List[int]
    retry_count: int = 0
    env_id: Optional[str] = None
    step_index: int = 0
    started_at: float = field(default_factory=time.perf_counter)
    last_result: Optional[Dict[str, Any]] = None
    pending_episode_records: List[Dict[str, Any]] = field(default_factory=list)

    def restart(self) -> None:
        self.env_id = None
        self.step_index = 0
        self.started_at = time.perf_counter()
        self.last_result = None
        self.pending_episode_records = []


def load_runtime_options(config: Dict[str, Any], default_num_envs: int = 1) -> RuntimeOptions:
    runtime = config.get("runtime", {})
    configured_timeouts = runtime.get("timeouts_sec", {})
    timeouts = dict(DEFAULT_TIMEOUTS_SEC)
    for key, value in configured_timeouts.items():
        timeouts[str(key)] = float(value)

    return RuntimeOptions(
        profile=str(config.get("profile", "full")),
        num_envs=max(1, int(runtime.get("num_envs", default_num_envs))),
        heartbeat_interval_sec=float(runtime.get("heartbeat_interval_sec", 15.0)),
        retry_attempts_per_battle=max(0, int(runtime.get("retry_attempts_per_battle", 2))),
        timeouts_sec=timeouts,
    )


def make_battle_seed(battle_index: int) -> List[int]:
    base = battle_index + 1
    return [
        (0x1234 + (base * 97)) & 0xFFFF,
        (0x2345 + (base * 193)) & 0xFFFF,
        (0x3456 + (base * 389)) & 0xFFFF,
        (0x4567 + (base * 769)) & 0xFFFF,
    ]


def format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class ProgressReporter:
    def __init__(self, phase: str, profile: str, target_battles: int, num_envs: int, heartbeat_interval_sec: float) -> None:
        self.phase = phase
        self.profile = profile
        self.target_battles = target_battles
        self.num_envs = num_envs
        self.heartbeat_interval_sec = heartbeat_interval_sec
        self.started_at = time.perf_counter()
        self.last_completion_at = self.started_at
        self.last_heartbeat_at = self.started_at
        self.heartbeats = 0
        self.retries = 0
        self.failed_attempts = 0

    def start(self, detail: str) -> None:
        print(f"{self.phase} start profile={self.profile} target={self.target_battles} envs={self.num_envs} {detail}")

    def completed(
        self,
        completed_battles: int,
        *,
        active_slots: int,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        now = time.perf_counter()
        self.last_completion_at = now
        parts = [
            f"{self.phase} {completed_battles}/{self.target_battles} battles",
            f"active={active_slots}",
        ]
        if extra:
            for key, value in extra.items():
                parts.append(f"{key}={value}")
        elapsed = now - self.started_at
        avg_battle_sec = elapsed / max(1, completed_battles)
        eta = avg_battle_sec * max(0, self.target_battles - completed_battles)
        parts.append(f"avg={avg_battle_sec:.1f}s/battle")
        parts.append(f"eta={format_duration(eta)}")
        parts.append(f"retries={self.retries}")
        print(" | ".join(parts))

    def retry(self, slot: EnvSlot, reason: str) -> None:
        self.retries += 1
        print(
            f"{self.phase} retry | battle={slot.battle_index + 1} | seed={slot.seed} | attempt={slot.retry_count} | reason={reason}"
        )

    def failed(self, slot: EnvSlot, reason: str) -> None:
        self.failed_attempts += 1
        print(
            f"{self.phase} failed | battle={slot.battle_index + 1} | seed={slot.seed} | attempts={slot.retry_count} | reason={reason}"
        )

    def maybe_heartbeat(self, active_slots: Sequence[EnvSlot], pending_label: str) -> None:
        now = time.perf_counter()
        if now - self.last_completion_at < self.heartbeat_interval_sec:
            return
        if now - self.last_heartbeat_at < self.heartbeat_interval_sec:
            return

        active_count = len(active_slots)
        detail = "idle"
        if active_slots:
            slot = active_slots[0]
            env_fragment = f"env={slot.env_id}" if slot.env_id else f"seed={slot.seed}"
            detail = f"pending={pending_label} {env_fragment} battle={slot.battle_index + 1} step={slot.step_index}"
        print(
            f"{self.phase} heartbeat | no completed battle for {int(now - self.last_completion_at)}s | active={active_count} | {detail}"
        )
        self.last_heartbeat_at = now
        self.heartbeats += 1

    def done(self, detail: str) -> None:
        wall = format_duration(time.perf_counter() - self.started_at)
        print(f"{self.phase} done | wall={wall} | retries={self.retries} | failed_attempts={self.failed_attempts} | {detail}")


def describe_pending(operation: str, slots: Sequence[EnvSlot]) -> str:
    if not slots:
        return operation
    slot = slots[0]
    if slot.env_id:
        return f"{operation} env={slot.env_id} battle={slot.battle_index + 1} step={slot.step_index}"
    return f"{operation} battle={slot.battle_index + 1} step={slot.step_index}"


def choose_timeout(runtime: RuntimeOptions, request_type: str) -> float:
    return float(runtime.timeouts_sec.get(request_type, DEFAULT_TIMEOUTS_SEC.get(request_type, 30.0)))
