"""Run an evaluation-only V1 agent tournament against simple baselines.

This module deliberately reuses the live evaluator recommendation path for the
learned agent and sim-core's legal action request for every agent. It does not
train models, rebuild datasets, or alter feature dimensions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .env_client import SimCoreClient
from .live_eval_server import (
    EvalRequest,
    LegalAction as LiveLegalAction,
    evaluate_with_model,
    reset_model_caches,
)
from .runtime import DEFAULT_TIMEOUTS_SEC, make_battle_seed


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ANALYSIS_DIR = REPO_ROOT / "artifacts" / "analysis"
DEFAULT_JSON_PATH = DEFAULT_ANALYSIS_DIR / "v1_agent_tournament_results.json"
DEFAULT_CSV_PATH = DEFAULT_ANALYSIS_DIR / "v1_agent_tournament_results.csv"
DEFAULT_MD_PATH = DEFAULT_ANALYSIS_DIR / "v1_agent_tournament_summary.md"
SUPPORTED_AGENTS = {"learned", "random", "heuristic"}
RESULT_OPTIONS = {
    "view_players": ["p1", "p2"],
    "include_log_delta": True,
    "include_possible_roles": False,
}


@dataclass
class Decision:
    choice: str
    index: Optional[int] = None
    label: str = ""
    kind: str = ""
    method: str = ""
    used_fallback: bool = False
    fallback_reason: str = ""


@dataclass
class AgentCounters:
    decisions: int = 0
    latency_ms_total: float = 0.0
    invalid_action_fallbacks: int = 0
    forced_switch_decisions: int = 0
    tera_uses: int = 0

    @property
    def avg_latency_ms(self) -> float:
        if self.decisions <= 0:
            return 0.0
        return self.latency_ms_total / self.decisions


@dataclass
class BattleContext:
    env_id: str
    battle_id: int
    p1_agent: str
    p2_agent: str
    protocol_log: List[str] = field(default_factory=list)
    counters: Dict[str, AgentCounters] = field(
        default_factory=lambda: {"p1": AgentCounters(), "p2": AgentCounters()}
    )


def _parse_agents(raw: str) -> List[str]:
    agents = [part.strip().lower() for part in raw.split(",") if part.strip()]
    unknown = sorted(set(agents) - SUPPORTED_AGENTS)
    if unknown:
        raise ValueError(f"Unsupported agent(s): {', '.join(unknown)}")
    if not agents:
        raise ValueError("At least one agent must be selected.")
    return agents


def _timeout(name: str) -> float:
    return float(DEFAULT_TIMEOUTS_SEC.get(name, 30.0))


def _build_matchups(agents: Sequence[str], include_learned_selfplay: bool) -> List[Tuple[str, str]]:
    selected = set(agents)
    matchups: List[Tuple[str, str]] = []
    if "learned" in selected and "random" in selected:
        matchups.extend([("learned", "random"), ("random", "learned")])
    if "learned" in selected and "heuristic" in selected:
        matchups.extend([("learned", "heuristic"), ("heuristic", "learned")])
    if include_learned_selfplay and "learned" in selected:
        matchups.append(("learned", "learned"))
    if not matchups:
        raise ValueError(
            "No supported matchups requested. Include learned plus random and/or heuristic."
        )
    return matchups


def _seed_for_battle(seed_offset: int, battle_index: int) -> List[int]:
    return make_battle_seed(seed_offset + battle_index)


def _legal_actions_from_request(request: Optional[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    if not isinstance(request, Mapping):
        return []
    legal = request.get("legal_actions")
    if not isinstance(legal, Mapping):
        return []
    actions = legal.get("actions")
    if not isinstance(actions, list):
        return []
    return [action for action in actions if isinstance(action, Mapping)]


def _action_by_index(request: Mapping[str, Any]) -> Dict[int, Mapping[str, Any]]:
    by_index: Dict[int, Mapping[str, Any]] = {}
    for action in _legal_actions_from_request(request):
        index = action.get("index")
        if isinstance(index, int):
            by_index[index] = action
    return by_index


def _fallback_decision(request: Optional[Mapping[str, Any]], reason: str) -> Decision:
    actions = _legal_actions_from_request(request)
    if actions:
        action = actions[0]
        return _decision_from_action(action, method="fallback", used_fallback=True, reason=reason)
    return Decision(
        choice="default",
        label="default",
        kind="default",
        method="fallback",
        used_fallback=True,
        fallback_reason=reason,
    )


def _decision_from_action(
    action: Mapping[str, Any],
    *,
    method: str,
    used_fallback: bool = False,
    reason: str = "",
) -> Decision:
    choice = str(action.get("choice") or action.get("label") or "default")
    return Decision(
        choice=choice,
        index=action.get("index") if isinstance(action.get("index"), int) else None,
        label=str(action.get("label") or choice),
        kind=str(action.get("kind") or ""),
        method=method,
        used_fallback=used_fallback,
        fallback_reason=reason,
    )


def _is_force_switch_request(request: Optional[Mapping[str, Any]]) -> bool:
    if not isinstance(request, Mapping):
        return False
    force_switch = request.get("force_switch")
    if isinstance(force_switch, bool):
        return force_switch
    if isinstance(force_switch, list):
        return any(bool(value) for value in force_switch)
    raw_force_switch = request.get("forceSwitch")
    if isinstance(raw_force_switch, bool):
        return raw_force_switch
    if isinstance(raw_force_switch, list):
        return any(bool(value) for value in raw_force_switch)
    return False


def _uses_tera(decision: Decision) -> bool:
    choice = decision.choice.lower()
    return decision.kind == "move_tera" or "terastallize" in choice or "tera" in decision.label.lower()


def _append_log_delta(protocol_log: List[str], result: Mapping[str, Any]) -> None:
    delta = result.get("log_delta")
    if isinstance(delta, list):
        protocol_log.extend(str(line) for line in delta)


def _count_invalid_choice_lines(result: Mapping[str, Any]) -> int:
    delta = result.get("log_delta")
    if not isinstance(delta, list):
        return 0
    count = 0
    for line in delta:
        text = str(line).lower()
        if "invalid choice" in text or "unavailable choice" in text:
            count += 1
    return count


def _choose_random(request: Mapping[str, Any], rng: random.Random) -> Decision:
    actions = _legal_actions_from_request(request)
    if not actions:
        return _fallback_decision(request, "no legal actions in request")
    return _decision_from_action(rng.choice(actions), method="random")


def _choose_heuristic(
    client: SimCoreClient,
    env_id: str,
    player: str,
    request: Mapping[str, Any],
) -> Decision:
    try:
        raw = client.agent_action(env_id, player, "heuristic", timeout_sec=_timeout("agent_action"))
    except Exception as exc:  # pragma: no cover - defensive path for external server failures
        return _fallback_decision(request, f"heuristic RPC failed: {exc}")
    if not isinstance(raw, Mapping):
        return _fallback_decision(request, "heuristic RPC returned non-object")
    action = raw.get("action")
    if isinstance(action, Mapping) and action.get("choice"):
        return _decision_from_action(action, method="heuristic")
    action_index = raw.get("action_index")
    if isinstance(action_index, int):
        action_by_index = _action_by_index(request)
        if action_index in action_by_index:
            return _decision_from_action(action_by_index[action_index], method="heuristic")
    if raw.get("choice"):
        return Decision(
            choice=str(raw["choice"]),
            index=action_index if isinstance(action_index, int) else None,
            label=str(raw.get("reason") or raw["choice"]),
            kind="",
            method="heuristic",
        )
    return _fallback_decision(request, "heuristic RPC returned no action")


def _live_legal_actions(request: Mapping[str, Any]) -> List[LiveLegalAction]:
    payload: List[LiveLegalAction] = []
    for action in _legal_actions_from_request(request):
        index = action.get("index")
        if not isinstance(index, int):
            continue
        payload.append(
            LiveLegalAction(
                kind=str(action.get("kind") or ""),
                label=str(action.get("label") or action.get("choice") or f"action:{index}"),
                slot=action.get("slot") if isinstance(action.get("slot"), int) else None,
                index=index,
                disabled=False,
            )
        )
    return payload


def _choose_learned(
    context: BattleContext,
    player: str,
    request: Mapping[str, Any],
) -> Decision:
    legal_by_index = _action_by_index(request)
    if not legal_by_index:
        return _fallback_decision(request, "no legal actions in request")
    payload = EvalRequest(
        room_id=f"v1-tournament-{context.battle_id}",
        url=f"sim-core://{context.env_id}",
        player=player,
        log=list(context.protocol_log),
        request=dict(request),
        legal_actions=_live_legal_actions(request),
    )
    try:
        report = evaluate_with_model(payload)
    except Exception as exc:  # pragma: no cover - defensive path for model/load failures
        return _fallback_decision(request, f"learned evaluator failed: {exc}")
    if isinstance(report, Mapping):
        candidates = report.get("top_actions") or (report.get("debug") or {}).get("all_action_estimates") or []
    else:
        candidates = getattr(report, "actions", [])
    for action in candidates:
        if isinstance(action, Mapping):
            index = action.get("index")
            disabled = bool(action.get("disabled"))
        else:
            index = getattr(action, "index", None)
            disabled = bool(getattr(action, "disabled", False))
        if isinstance(index, int) and index in legal_by_index and not disabled:
            return _decision_from_action(legal_by_index[index], method="learned")
    return _fallback_decision(request, "learned evaluator returned no current legal action")


def _choose_action(
    *,
    agent: str,
    player: str,
    request: Mapping[str, Any],
    context: BattleContext,
    client: SimCoreClient,
    rng: random.Random,
) -> Decision:
    if agent == "learned":
        return _choose_learned(context, player, request)
    if agent == "heuristic":
        return _choose_heuristic(client, context.env_id, player, request)
    return _choose_random(request, rng)


def _player_agent(context: BattleContext, player: str) -> str:
    return context.p1_agent if player == "p1" else context.p2_agent


def _average_latency_by_agent(context: BattleContext) -> Dict[str, float]:
    totals: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for player in ("p1", "p2"):
        agent = _player_agent(context, player)
        counters = context.counters[player]
        totals[agent] = totals.get(agent, 0.0) + counters.latency_ms_total
        counts[agent] = counts.get(agent, 0) + counters.decisions
    return {
        agent: (totals[agent] / counts[agent] if counts[agent] else 0.0)
        for agent in sorted(totals)
    }


def _counter_field_by_agent(context: BattleContext, field_name: str) -> Dict[str, int]:
    values: Dict[str, int] = {}
    for player in ("p1", "p2"):
        agent = _player_agent(context, player)
        values[agent] = values.get(agent, 0) + int(getattr(context.counters[player], field_name))
    return values


def _winner_reason(winner: Optional[str]) -> str:
    if winner in {"p1", "p2"}:
        return f"winner:{winner}"
    return "tie_or_unresolved"


def _learned_result(p1_agent: str, p2_agent: str, winner: Optional[str]) -> Optional[str]:
    learned_players = [side for side, agent in (("p1", p1_agent), ("p2", p2_agent)) if agent == "learned"]
    if len(learned_players) != 1:
        return None
    if winner == learned_players[0]:
        return "win"
    if winner in {"p1", "p2"}:
        return "loss"
    return "tie"


def _run_one_battle(
    *,
    client: SimCoreClient,
    format_name: str,
    p1_agent: str,
    p2_agent: str,
    battle_index: int,
    seed: Sequence[int],
    max_turns: int,
) -> Dict[str, Any]:
    env_id = client.create_env(
        format_name=format_name,
        seed=list(seed),
        players={"p1": {"controller": "external"}, "p2": {"controller": "external"}},
        timeout_sec=_timeout("create_env"),
    )
    context = BattleContext(env_id=env_id, battle_id=battle_index, p1_agent=p1_agent, p2_agent=p2_agent)
    rng_seed = "|".join(str(part) for part in [*seed, battle_index, p1_agent, p2_agent])
    rng = random.Random(rng_seed)
    started = time.perf_counter()
    winner: Optional[str] = None
    terminated = False
    turns = 0
    notes: List[str] = []
    final_result: Mapping[str, Any] = {}
    try:
        result = client.reset(env_id, RESULT_OPTIONS, timeout_sec=_timeout("reset"))
        final_result = result
        _append_log_delta(context.protocol_log, result)
        while not bool(result.get("terminated")):
            info = result.get("info")
            if isinstance(info, Mapping) and isinstance(info.get("turn"), int):
                turns = max(turns, int(info["turn"]))
            if turns > max_turns:
                notes.append(f"max_turns_exceeded:{max_turns}")
                break
            requests = result.get("requests")
            if not isinstance(requests, Mapping):
                notes.append("no request map returned")
                break
            choices: Dict[str, str] = {}
            decision_players = [
                player
                for player in ("p1", "p2")
                if isinstance(requests.get(player), Mapping)
            ]
            if not decision_players:
                notes.append("no pending external decision")
                break
            for player in decision_players:
                request = requests[player]
                agent = _player_agent(context, player)
                counters = context.counters[player]
                if _is_force_switch_request(request):
                    counters.forced_switch_decisions += 1
                before = time.perf_counter()
                decision = _choose_action(
                    agent=agent,
                    player=player,
                    request=request,
                    context=context,
                    client=client,
                    rng=rng,
                )
                elapsed_ms = (time.perf_counter() - before) * 1000.0
                counters.decisions += 1
                counters.latency_ms_total += elapsed_ms
                if decision.used_fallback:
                    counters.invalid_action_fallbacks += 1
                    if decision.fallback_reason:
                        notes.append(f"{player}:{agent}:{decision.fallback_reason}")
                if _uses_tera(decision):
                    counters.tera_uses += 1
                choices[player] = decision.choice
            result = client.step(
                env_id,
                choices,
                RESULT_OPTIONS,
                timeout_sec=_timeout("step"),
            )
            final_result = result
            _append_log_delta(context.protocol_log, result)
            invalid_lines = _count_invalid_choice_lines(result)
            if invalid_lines:
                notes.append(f"sim_core_invalid_choice_lines:{invalid_lines}")
                for player in decision_players:
                    context.counters[player].invalid_action_fallbacks += invalid_lines
        terminated = bool(final_result.get("terminated"))
        raw_winner = final_result.get("winner")
        winner = raw_winner if raw_winner in {"p1", "p2"} else None
        info = final_result.get("info")
        if isinstance(info, Mapping) and isinstance(info.get("turn"), int):
            turns = max(turns, int(info["turn"]))
    finally:
        try:
            client.close_env(env_id, timeout_sec=_timeout("close_env"))
        except Exception as exc:  # pragma: no cover - cleanup best effort
            notes.append(f"close_failed:{exc}")
    wall_time_sec = time.perf_counter() - started
    return {
        "matchup": f"{p1_agent}_p1_vs_{p2_agent}_p2",
        "battle_index": battle_index,
        "seed": list(seed),
        "format": format_name,
        "p1_agent": p1_agent,
        "p2_agent": p2_agent,
        "winner": winner,
        "learned_result": _learned_result(p1_agent, p2_agent, winner),
        "turns": turns,
        "terminated": terminated,
        "wall_time_sec": wall_time_sec,
        "decision_counts": {player: context.counters[player].decisions for player in ("p1", "p2")},
        "avg_decision_latency_ms_by_player": {
            player: context.counters[player].avg_latency_ms for player in ("p1", "p2")
        },
        "avg_decision_latency_ms_by_agent": _average_latency_by_agent(context),
        "invalid_action_fallbacks_by_player": {
            player: context.counters[player].invalid_action_fallbacks for player in ("p1", "p2")
        },
        "invalid_action_fallbacks_by_agent": _counter_field_by_agent(context, "invalid_action_fallbacks"),
        "forced_switch_decisions_by_player": {
            player: context.counters[player].forced_switch_decisions for player in ("p1", "p2")
        },
        "forced_switch_decisions_by_agent": _counter_field_by_agent(context, "forced_switch_decisions"),
        "tera_uses_by_player": {
            player: context.counters[player].tera_uses for player in ("p1", "p2")
        },
        "tera_uses_by_agent": _counter_field_by_agent(context, "tera_uses"),
        "result_reason": _winner_reason(winner),
        "notes": notes,
        "final_log_tail": context.protocol_log[-12:],
    }


def _ci95(p: float, n: int) -> float:
    if n <= 0:
        return 0.0
    return 1.96 * math.sqrt(p * (1.0 - p) / n)


def _mean(values: Iterable[float]) -> float:
    values_list = list(values)
    if not values_list:
        return 0.0
    return sum(values_list) / len(values_list)


def _summarize(results: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    by_matchup: Dict[str, List[Mapping[str, Any]]] = {}
    for row in results:
        by_matchup.setdefault(str(row["matchup"]), []).append(row)
    for matchup, rows in sorted(by_matchup.items()):
        learned_rows = [row for row in rows if row.get("learned_result") is not None]
        learned_wins = sum(1 for row in learned_rows if row.get("learned_result") == "win")
        learned_losses = sum(1 for row in learned_rows if row.get("learned_result") == "loss")
        learned_ties = sum(1 for row in learned_rows if row.get("learned_result") == "tie")
        n = len(learned_rows)
        win_rate = learned_wins / n if n else None
        avg_agent_latencies = [
            value
            for row in rows
            for value in (row.get("avg_decision_latency_ms_by_agent") or {}).values()
            if isinstance(value, (int, float))
        ]
        summaries.append(
            {
                "matchup": matchup,
                "battles": len(rows),
                "learned_wins": learned_wins,
                "learned_losses": learned_losses,
                "learned_ties": learned_ties,
                "learned_win_rate": win_rate,
                "learned_win_rate_ci95": _ci95(win_rate, n) if win_rate is not None else None,
                "avg_turns": _mean(float(row.get("turns") or 0) for row in rows),
                "avg_wall_time_sec": _mean(float(row.get("wall_time_sec") or 0.0) for row in rows),
                "avg_decision_latency_ms": _mean(avg_agent_latencies),
                "invalid_action_fallbacks": sum(
                    sum(int(v) for v in (row.get("invalid_action_fallbacks_by_agent") or {}).values())
                    for row in rows
                ),
                "forced_switch_decisions": sum(
                    sum(int(v) for v in (row.get("forced_switch_decisions_by_agent") or {}).values())
                    for row in rows
                ),
                "tera_uses": sum(
                    sum(int(v) for v in (row.get("tera_uses_by_agent") or {}).values())
                    for row in rows
                ),
                "notes": "; ".join(
                    note
                    for row in rows
                    for note in (row.get("notes") or [])
                ),
            }
        )
    return summaries


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, results: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "matchup",
        "battle_index",
        "seed",
        "format",
        "p1_agent",
        "p2_agent",
        "winner",
        "learned_result",
        "turns",
        "terminated",
        "wall_time_sec",
        "avg_decision_latency_ms_by_agent",
        "invalid_action_fallbacks_by_agent",
        "forced_switch_decisions_by_agent",
        "tera_uses_by_agent",
        "result_reason",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    key: (
                        json.dumps(row.get(key), sort_keys=True)
                        if isinstance(row.get(key), (dict, list))
                        else row.get(key)
                    )
                    for key in fieldnames
                }
            )


def _format_rate(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100.0:.1f}%"


def _write_markdown(path: Path, metadata: Mapping[str, Any], summary: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# V1 Agent Tournament Summary",
        "",
        f"- Format: `{metadata['format']}`",
        f"- Battles per matchup: `{metadata['battles_per_matchup']}`",
        f"- Sim-core mode: `{metadata['sim_core_mode']}`",
        f"- Rollout mode: `{metadata['rollout_mode']}`",
        f"- Rollouts per action: `{metadata['rollouts_per_action']}`",
        f"- Generated at: `{metadata['generated_at']}`",
        "",
        "| Matchup | Battles | Learned win rate | 95% CI | Avg turns | Avg latency | Notes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary:
        ci = row.get("learned_win_rate_ci95")
        ci_text = "n/a" if ci is None else f"+/- {float(ci) * 100.0:.1f}%"
        notes = str(row.get("notes") or "")
        if not notes and row.get("invalid_action_fallbacks"):
            notes = f"{row['invalid_action_fallbacks']} fallback(s)"
        lines.append(
            "| {matchup} | {battles} | {rate} | {ci} | {turns:.1f} | {latency:.1f} ms | {notes} |".format(
                matchup=row["matchup"],
                battles=row["battles"],
                rate=_format_rate(row.get("learned_win_rate")),
                ci=ci_text,
                turns=float(row.get("avg_turns") or 0.0),
                latency=float(row.get("avg_decision_latency_ms") or 0.0),
                notes=notes.replace("|", "\\|"),
            )
        )
    lines.extend(
        [
            "",
            "Notes:",
            "- Results are generated from autonomous sim-core battles with both players externally controlled.",
            "- Learned decisions call the existing live evaluator recommendation path and pick the top final-ranked current legal action.",
            "- Random and heuristic decisions are constrained by the same sim-core legal action set as learned decisions.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_outputs(
    *,
    json_path: Path,
    csv_path: Path,
    md_path: Path,
    metadata: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
) -> None:
    summary = _summarize(results)
    payload = {
        "metadata": metadata,
        "summary": summary,
        "battle_results": list(results),
    }
    _write_json(json_path, payload)
    _write_csv(csv_path, results)
    _write_markdown(md_path, metadata, summary)


def _set_env(name: str, value: Optional[str], old_values: Dict[str, Optional[str]]) -> None:
    old_values.setdefault(name, os.environ.get(name))
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


def _configure_environment(args: argparse.Namespace) -> Dict[str, Optional[str]]:
    old_values: Dict[str, Optional[str]] = {}
    if args.sim_core_mode == "native":
        command = json.dumps([args.node_exe, "dist/src/server.js"])
        _set_env("NEURAL_SIM_CORE_COMMAND_JSON", command, old_values)
        _set_env("NEURAL_SIM_CORE_CWD", str(Path(args.sim_core_cwd).resolve()), old_values)
    elif args.sim_core_mode == "env":
        pass
    else:
        raise ValueError(f"Unsupported sim-core mode: {args.sim_core_mode}")
    _set_env("NEURAL_ROLLOUT_MODE", args.rollout_mode, old_values)
    _set_env("NEURAL_ROLLOUTS_PER_ACTION", str(args.rollouts_per_action), old_values)
    return old_values


def _client_command_cwd(args: argparse.Namespace) -> Tuple[List[str], str]:
    if args.sim_core_mode == "native":
        return [args.node_exe, "dist/src/server.js"], str(Path(args.sim_core_cwd).resolve())
    raw_command = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")
    if not raw_command:
        raise ValueError("NEURAL_SIM_CORE_COMMAND_JSON must be set when --sim-core-mode env is used.")
    command = json.loads(raw_command)
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        raise ValueError("NEURAL_SIM_CORE_COMMAND_JSON must decode to a JSON string array.")
    cwd = os.environ.get("NEURAL_SIM_CORE_CWD") or str(Path(args.sim_core_cwd).resolve())
    return list(command), cwd


def _restore_environment(old_values: Mapping[str, Optional[str]]) -> None:
    for name, value in old_values.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", default="gen9randombattle", dest="format_name")
    parser.add_argument("--battles", type=int, default=50, help="Battles per matchup.")
    parser.add_argument("--agents", default="learned,random,heuristic")
    parser.add_argument("--include-learned-selfplay", action="store_true")
    parser.add_argument("--sim-core-mode", choices=["native", "env"], default="native")
    parser.add_argument("--node-exe", default="node")
    parser.add_argument("--sim-core-cwd", default=str(REPO_ROOT / "sim-core"))
    parser.add_argument("--rollout-mode", default="approximate")
    parser.add_argument("--rollouts-per-action", type=int, default=8)
    parser.add_argument("--flush-every", type=int, default=1, help="Write partial JSON/CSV/Markdown outputs every N battles.")
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--max-turns", type=int, default=1000)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--csv-out", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_PATH)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.battles <= 0:
        parser.error("--battles must be positive")
    if args.flush_every <= 0:
        parser.error("--flush-every must be positive")
    agents = _parse_agents(args.agents)
    matchups = _build_matchups(agents, args.include_learned_selfplay)
    old_env = _configure_environment(args)
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    reset_model_caches()
    results: List[Dict[str, Any]] = []
    total_battles = len(matchups) * args.battles
    metadata = {
        "format": args.format_name,
        "battles_per_matchup": args.battles,
        "agents": agents,
        "matchups": [f"{p1}_p1_vs_{p2}_p2" for p1, p2 in matchups],
        "seed_offset": args.seed_offset,
        "sim_core_mode": args.sim_core_mode,
        "sim_core_cwd": str(Path(args.sim_core_cwd).resolve()),
        "rollout_mode": args.rollout_mode,
        "rollouts_per_action": args.rollouts_per_action,
        "generated_at": generated_at,
        "evaluation_only": True,
        "completed_battles": 0,
        "total_requested_battles": total_battles,
        "interrupted": False,
    }
    run_started = time.perf_counter()
    try:
        command, cwd = _client_command_cwd(args)
        with SimCoreClient(command, cwd) as client:
            battle_id = 0
            for p1_agent, p2_agent in matchups:
                for local_index in range(args.battles):
                    seed = _seed_for_battle(args.seed_offset, local_index)
                    print(
                        f"[tournament] {battle_id + 1}/{total_battles} {p1_agent} p1 vs {p2_agent} p2 "
                        f"battle {local_index + 1}/{args.battles} seed={seed}",
                        flush=True,
                    )
                    results.append(
                        _run_one_battle(
                            client=client,
                            format_name=args.format_name,
                            p1_agent=p1_agent,
                            p2_agent=p2_agent,
                            battle_index=battle_id,
                            seed=seed,
                            max_turns=args.max_turns,
                        )
                    )
                    battle_id += 1
                    metadata["completed_battles"] = len(results)
                    elapsed = time.perf_counter() - run_started
                    avg_sec = elapsed / max(1, len(results))
                    remaining = max(0, total_battles - len(results))
                    eta_sec = remaining * avg_sec
                    print(
                        f"[tournament] completed {len(results)}/{total_battles}; "
                        f"avg={avg_sec:.1f}s/battle eta={eta_sec / 60.0:.1f}m",
                        flush=True,
                    )
                    if len(results) % args.flush_every == 0:
                        _write_outputs(
                            json_path=args.json_out,
                            csv_path=args.csv_out,
                            md_path=args.md_out,
                            metadata=metadata,
                            results=results,
                        )
                        print("[tournament] partial outputs flushed", flush=True)
    except KeyboardInterrupt:
        metadata["interrupted"] = True
        print("[tournament] interrupted; writing partial outputs", flush=True)
    finally:
        _restore_environment(old_env)
    metadata["completed_battles"] = len(results)
    _write_outputs(
        json_path=args.json_out,
        csv_path=args.csv_out,
        md_path=args.md_out,
        metadata=metadata,
        results=results,
    )
    print(f"[tournament] wrote {args.json_out}", flush=True)
    print(f"[tournament] wrote {args.csv_out}", flush=True)
    print(f"[tournament] wrote {args.md_out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
