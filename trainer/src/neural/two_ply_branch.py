"""Bounded deterministic two-ply sim-core branch search.

The first Showdown transition applies the audited action and a bounded current
opponent reply. When another audited-side request is available, a bounded own
follow-up is stepped against one deterministic heuristic opponent reply. Leaves
use the material/HP scorer unless the simulator reports a terminal outcome.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from .env_client import SimCoreClient, SimCoreError, SimCoreTimeoutError
from .one_turn_branch import (
    DEFAULT_RESULT_OPTIONS,
    ScoreFn,
    _legal_action_list,
    _terminal_score,
    evaluate_action_branches,
    make_material_score_fn,
)


@dataclass(frozen=True)
class TwoPlyConfig:
    max_root_actions: int = 6
    max_opponent_actions: int = 3
    max_followup_actions: int = 3
    max_decision_time_sec: float = 10.0
    risk_lambda: float = 0.0
    objective: str = "risk_adjusted_score"
    create_timeout: float = 30.0
    step_timeout: float = 30.0
    format_name: str = "gen9randombattle"
    belief_mode: bool = False


def derive_belief_particle_seed(base_seed: Sequence[int], particle_index: int) -> List[int]:
    """Derive a stable particle seed while preserving particle zero exactly."""
    base = [int(base_seed[i]) if i < len(base_seed) else i + 1 for i in range(4)]
    index = max(0, int(particle_index))
    offsets = (1009, 2027, 3041, 4051)
    return [(base[i] + index * offsets[i]) & 0xFFFF for i in range(4)]


def _ordered_actions(
    request: Optional[Mapping[str, Any]],
    preferred_index: Optional[int],
    limit: int,
) -> List[Dict[str, Any]]:
    actions = _legal_action_list(request)
    actions.sort(
        key=lambda action: (
            0 if preferred_index is not None and action.get("index") == preferred_index else 1,
            0 if str(action.get("kind") or "").startswith("move") else 1,
            int(action.get("index", 99)),
        )
    )
    return actions[: max(1, int(limit))]


def _create_replayed_env(
    client: SimCoreClient,
    seed: Sequence[int],
    history: Sequence[Mapping[str, str]],
    config: TwoPlyConfig,
    options: Mapping[str, Any],
) -> Tuple[str, Dict[str, Any], List[str], Optional[Dict[str, Any]]]:
    env_id = client.create_env(
        config.format_name,
        list(seed),
        {"p1": {"controller": "external"}, "p2": {"controller": "external"}},
        timeout_sec=config.create_timeout,
    )
    protocol: List[str] = []
    try:
        result = client.reset(env_id, dict(options), timeout_sec=config.step_timeout)
        protocol.extend(result.get("log_delta") or [])
        for entry in history:
            if result.get("terminated"):
                raise SimCoreError("history replay terminated early")
            result = client.step(env_id, dict(entry), dict(options), timeout_sec=config.step_timeout)
            protocol.extend(result.get("log_delta") or [])
        if result.get("terminated"):
            raise SimCoreError("history replay terminated early")
        return env_id, result, protocol, None
    except Exception:
        try:
            client.close_env(env_id, timeout_sec=config.create_timeout)
        except Exception:
            pass
        raise


def _create_branch_env(
    client: SimCoreClient,
    seed: Sequence[int],
    history: Sequence[Mapping[str, str]],
    config: TwoPlyConfig,
    options: Mapping[str, Any],
    *,
    source_env_id: Optional[str],
    player_side: str,
    belief_seed: Optional[Sequence[int]],
) -> Tuple[str, Dict[str, Any], List[str], Optional[Dict[str, Any]]]:
    if not config.belief_mode:
        return _create_replayed_env(client, seed, history, config, options)
    if not source_env_id or belief_seed is None:
        raise SimCoreError("belief mode requires source_env_id and belief_seed")
    fork = client.fork_belief_env(
        source_env_id,
        player_side,
        belief_seed,
        dict(options),
        timeout_sec=config.step_timeout,
    )
    env_id = fork.get("env_id")
    result = fork.get("result")
    if not isinstance(env_id, str) or not isinstance(result, Mapping):
        raise SimCoreError("belief fork returned an invalid response")
    return env_id, dict(result), list(result.get("log_delta") or []), dict(fork.get("belief") or {})


def _close_env(client: SimCoreClient, env_id: Optional[str], timeout: float) -> None:
    if env_id is None:
        return
    try:
        client.close_env(env_id, timeout_sec=timeout)
    except Exception:
        pass


def _heuristic_index(client: SimCoreClient, env_id: str, side: str, timeout: float) -> Optional[int]:
    try:
        decision = client.agent_action(env_id, side, "heuristic", timeout_sec=timeout)
        index = decision.get("action_index")
        return int(index) if isinstance(index, int) else None
    except SimCoreError:
        return None


def _score_result(
    protocol: Sequence[str],
    result: Mapping[str, Any],
    player_side: str,
    score_fn: ScoreFn,
) -> Tuple[float, str]:
    if result.get("terminated"):
        return _terminal_score(result, player_side), "terminal"
    return float(score_fn(protocol, result, player_side)), "material"


def _one_turn_fallback(
    *,
    client: SimCoreClient,
    seed: Sequence[int],
    history: Sequence[Mapping[str, str]],
    player_side: str,
    player_request: Mapping[str, Any],
    opponent_request: Optional[Mapping[str, Any]],
    score_fn: ScoreFn,
    config: TwoPlyConfig,
    options: Mapping[str, Any],
    reason: str,
) -> Dict[str, Any]:
    from .one_turn_branch import BranchConfig

    report = evaluate_action_branches(
        client=client,
        seed=seed,
        history=history,
        player_side=player_side,
        player_request=player_request,
        opponent_request=opponent_request,
        score_fn=score_fn,
        config=BranchConfig(
            max_opponent_actions=config.max_opponent_actions,
            risk_lambda=config.risk_lambda,
            objective=config.objective,
            create_timeout=config.create_timeout,
            step_timeout=config.step_timeout,
            format_name=config.format_name,
        ),
        result_options=options,
    )
    report.update(
        {
            "search": "two_ply_fallback_one_turn",
            "unsupported_reason": reason,
            "leaf_count": sum(int(row.get("branch_count", 0)) for row in report.get("actions", [])),
            "timeout_count": 0,
            "fallback_to_one_turn": True,
            "max_root_actions": config.max_root_actions,
            "max_followup_actions": config.max_followup_actions,
        }
    )
    return report


def evaluate_two_ply_branches(
    *,
    client: SimCoreClient,
    seed: Sequence[int],
    history: Sequence[Mapping[str, str]],
    player_side: str,
    player_request: Mapping[str, Any],
    opponent_request: Optional[Mapping[str, Any]],
    score_fn: Optional[ScoreFn] = None,
    config: Optional[TwoPlyConfig] = None,
    legal_action_indices: Optional[Sequence[int]] = None,
    root_action_indices: Optional[Sequence[int]] = None,
    result_options: Optional[Mapping[str, Any]] = None,
    source_env_id: Optional[str] = None,
    belief_seed: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    config = config or TwoPlyConfig()
    score_fn = score_fn or make_material_score_fn()
    options = dict(result_options or DEFAULT_RESULT_OPTIONS)
    opponent_side = "p2" if player_side == "p1" else "p1"
    started = time.perf_counter()
    deadline = started + max(0.01, config.max_decision_time_sec)

    if player_request.get("force_switch") and not config.belief_mode:
        return _one_turn_fallback(
            client=client,
            seed=seed,
            history=history,
            player_side=player_side,
            player_request=player_request,
            opponent_request=opponent_request,
            score_fn=score_fn,
            config=config,
            options=options,
            reason="root_forced_switch",
        )

    preferred_root: Optional[int] = None
    preferred_opponent: Optional[int] = None
    setup_env: Optional[str] = None
    setup_errors: List[str] = []
    belief_metadata: Optional[Dict[str, Any]] = None
    try:
        setup_env, setup_result, _, belief_metadata = _create_branch_env(
            client,
            seed,
            history,
            config,
            options,
            source_env_id=source_env_id,
            player_side=player_side,
            belief_seed=belief_seed,
        )
        preferred_root = _heuristic_index(client, setup_env, player_side, config.step_timeout)
        preferred_opponent = _heuristic_index(client, setup_env, opponent_side, config.step_timeout)
    except SimCoreError as exc:
        setup_errors.append(f"heuristic_ordering_failed:{type(exc).__name__}:{exc}")
    finally:
        _close_env(client, setup_env, config.create_timeout)

    if root_action_indices is not None:
        by_index = {
            int(action.get("index", -1)): action
            for action in _legal_action_list(player_request)
        }
        root_actions = [
            by_index[int(index)]
            for index in root_action_indices
            if int(index) in by_index
        ]
    else:
        root_actions = _ordered_actions(player_request, preferred_root, config.max_root_actions)
    if legal_action_indices is not None:
        wanted = {int(index) for index in legal_action_indices}
        root_actions = [action for action in root_actions if int(action.get("index", -1)) in wanted]
    effective_opponent_request = opponent_request
    if config.belief_mode and "setup_result" in locals():
        sampled_requests = setup_result.get("requests") or {}
        effective_opponent_request = sampled_requests.get(opponent_side)
    opponent_actions = _ordered_actions(effective_opponent_request, preferred_opponent, config.max_opponent_actions)
    if not opponent_actions:
        opponent_actions = [None]  # type: ignore[list-item]

    action_rows: List[Dict[str, Any]] = []
    transition_count = 0
    leaf_count = 0
    branch_errors = 0
    timeout_count = 0
    capped_leaf_count = 0
    deadline_hit = False
    branch_error_reasons: List[str] = []

    for action in root_actions:
        response_rows: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        root_choice = action.get("choice")
        if not root_choice:
            branch_errors += 1
            errors.append({"reason": "missing_root_choice"})
            continue

        for opponent_action in opponent_actions:
            if time.perf_counter() >= deadline:
                deadline_hit = True
                errors.append({"reason": "decision_deadline_before_root"})
                break
            root_choices = {player_side: str(root_choice)}
            if isinstance(opponent_action, Mapping) and opponent_action.get("choice"):
                root_choices[opponent_side] = str(opponent_action["choice"])

            root_env: Optional[str] = None
            try:
                root_env, _, protocol, _ = _create_branch_env(
                    client,
                    seed,
                    history,
                    config,
                    options,
                    source_env_id=source_env_id,
                    player_side=player_side,
                    belief_seed=belief_seed,
                )
                root_result = client.step(
                    root_env, root_choices, dict(options), timeout_sec=config.step_timeout
                )
                protocol.extend(root_result.get("log_delta") or [])
                transition_count += 1
                if root_result.get("terminated"):
                    score, method = _score_result(protocol, root_result, player_side, score_fn)
                    response_rows.append(
                        {
                            "opponent_action": opponent_action.get("label") if isinstance(opponent_action, Mapping) else None,
                            "score": score,
                            "method": method,
                            "terminal": True,
                            "winner": root_result.get("winner"),
                            "followup_count": 0,
                            "followups": [],
                        }
                    )
                    leaf_count += 1
                    continue

                next_requests = root_result.get("requests") or {}
                next_player_request = next_requests.get(player_side)
                if not isinstance(next_player_request, Mapping) or not _legal_action_list(next_player_request):
                    score, method = _score_result(protocol, root_result, player_side, score_fn)
                    response_rows.append(
                        {
                            "opponent_action": opponent_action.get("label") if isinstance(opponent_action, Mapping) else None,
                            "score": score,
                            "method": f"{method}_no_followup_request",
                            "terminal": False,
                            "winner": None,
                            "followup_count": 0,
                            "followups": [],
                        }
                    )
                    leaf_count += 1
                    continue

                preferred_followup = _heuristic_index(client, root_env, player_side, config.step_timeout)
                next_opponent_request = next_requests.get(opponent_side)
                next_opponent_index = (
                    _heuristic_index(client, root_env, opponent_side, config.step_timeout)
                    if isinstance(next_opponent_request, Mapping)
                    and _legal_action_list(next_opponent_request)
                    else None
                )
                followups = _ordered_actions(
                    next_player_request, preferred_followup, config.max_followup_actions
                )
                next_opponent_actions = _ordered_actions(
                    next_opponent_request, next_opponent_index, 1
                )
                next_opponent_action = next_opponent_actions[0] if next_opponent_actions else None

                followup_rows: List[Dict[str, Any]] = []
                for followup in followups:
                    if time.perf_counter() >= deadline:
                        deadline_hit = True
                        capped_leaf_count += 1
                        score, method = _score_result(protocol, root_result, player_side, score_fn)
                        followup_rows.append(
                            {
                                "index": followup.get("index"),
                                "label": followup.get("label"),
                                "score": score,
                                "method": f"{method}_deadline_fallback",
                                "terminal": False,
                                "winner": None,
                            }
                        )
                        leaf_count += 1
                        continue

                    leaf_env: Optional[str] = None
                    try:
                        leaf_env, _, leaf_protocol, _ = _create_branch_env(
                            client,
                            seed,
                            history,
                            config,
                            options,
                            source_env_id=source_env_id,
                            player_side=player_side,
                            belief_seed=belief_seed,
                        )
                        replayed_root = client.step(
                            leaf_env, root_choices, dict(options), timeout_sec=config.step_timeout
                        )
                        leaf_protocol.extend(replayed_root.get("log_delta") or [])
                        if replayed_root.get("terminated"):
                            leaf_result = replayed_root
                        else:
                            leaf_choices = {player_side: str(followup.get("choice"))}
                            if isinstance(next_opponent_action, Mapping) and next_opponent_action.get("choice"):
                                leaf_choices[opponent_side] = str(next_opponent_action["choice"])
                            leaf_result = client.step(
                                leaf_env, leaf_choices, dict(options), timeout_sec=config.step_timeout
                            )
                            leaf_protocol.extend(leaf_result.get("log_delta") or [])
                            transition_count += 1
                        score, method = _score_result(
                            leaf_protocol, leaf_result, player_side, score_fn
                        )
                        followup_rows.append(
                            {
                                "index": followup.get("index"),
                                "label": followup.get("label"),
                                "score": score,
                                "method": method,
                                "terminal": bool(leaf_result.get("terminated")),
                                "winner": leaf_result.get("winner"),
                            }
                        )
                        leaf_count += 1
                    except SimCoreTimeoutError as exc:
                        timeout_count += 1
                        branch_errors += 1
                        branch_error_reasons.append(f"followup_timeout:{exc}")
                        errors.append({"reason": f"followup_timeout:{exc}", "index": followup.get("index")})
                    except SimCoreError as exc:
                        branch_errors += 1
                        branch_error_reasons.append(f"followup_error:{type(exc).__name__}:{exc}")
                        errors.append(
                            {
                                "reason": f"followup_error:{type(exc).__name__}:{exc}",
                                "index": followup.get("index"),
                            }
                        )
                    finally:
                        _close_env(client, leaf_env, config.create_timeout)

                if followup_rows:
                    best_followup = max(followup_rows, key=lambda row: float(row["score"]))
                    response_rows.append(
                        {
                            "opponent_action": opponent_action.get("label") if isinstance(opponent_action, Mapping) else None,
                            "score": float(best_followup["score"]),
                            "method": "best_followup",
                            "terminal": bool(best_followup["terminal"]),
                            "winner": best_followup.get("winner"),
                            "followup_count": len(followup_rows),
                            "selected_followup": best_followup,
                            "followups": followup_rows,
                        }
                    )
            except SimCoreTimeoutError as exc:
                timeout_count += 1
                branch_errors += 1
                branch_error_reasons.append(f"root_timeout:{exc}")
                errors.append({"reason": f"root_timeout:{exc}"})
            except SimCoreError as exc:
                branch_errors += 1
                branch_error_reasons.append(f"root_error:{type(exc).__name__}:{exc}")
                errors.append({"reason": f"root_error:{type(exc).__name__}:{exc}"})
            finally:
                _close_env(client, root_env, config.create_timeout)

        scores = [float(row["score"]) for row in response_rows]
        mean_score = float(np.mean(scores)) if scores else None
        std_score = float(np.std(scores)) if scores else None
        action_rows.append(
            {
                "index": int(action.get("index", -1)),
                "label": str(action.get("label") or action.get("choice") or "unknown"),
                "kind": str(action.get("kind") or "unknown"),
                "choice": root_choice,
                "response_count": len(response_rows),
                "leaf_count": sum(
                    max(1, int(row.get("followup_count", 0))) for row in response_rows
                ),
                "mean_score": mean_score,
                "worst_score": float(np.min(scores)) if scores else None,
                "best_score": float(np.max(scores)) if scores else None,
                "std_score": std_score,
                "risk_adjusted_score": (
                    mean_score - config.risk_lambda * std_score
                    if mean_score is not None and std_score is not None
                    else mean_score
                ),
                "responses": response_rows,
                "errors": errors,
            }
        )

    def _objective(row: Mapping[str, Any]) -> float:
        value = row.get(config.objective)
        return float(value) if value is not None else float("-inf")

    ranked = sorted(action_rows, key=lambda row: (_objective(row), -int(row["index"])), reverse=True)
    if deadline_hit:
        timeout_count += 1
    return {
        "search": "two_ply_belief" if config.belief_mode else "two_ply",
        "player_side": player_side,
        "format": config.format_name,
        "objective": config.objective,
        "risk_lambda": config.risk_lambda,
        "max_root_actions": config.max_root_actions,
        "max_opponent_actions": config.max_opponent_actions,
        "max_followup_actions": config.max_followup_actions,
        "actions": ranked,
        "selected": ranked[0] if ranked and _objective(ranked[0]) != float("-inf") else None,
        "branch_count": transition_count,
        "leaf_count": leaf_count,
        "branch_errors": branch_errors,
        "branch_error_reasons": branch_error_reasons[:20],
        "timeout_count": timeout_count,
        "capped_leaf_count": capped_leaf_count,
        "damage_fallbacks": 0,
        "fallback_to_one_turn": capped_leaf_count > 0,
        "setup_errors": setup_errors,
        "belief": belief_metadata,
        "belief_samples": 1 if belief_metadata else 0,
        "belief_impossible_states": int((belief_metadata or {}).get("impossible_belief_states", 0) or 0),
        "belief_missing_data_count": int((belief_metadata or {}).get("missing_randbats_data_count", 0) or 0),
        "belief_constraint_violations": int((belief_metadata or {}).get("public_info_constraint_violations", 0) or 0),
        "latency_ms": (time.perf_counter() - started) * 1000.0,
    }


def aggregate_belief_particle_reports(
    reports: Sequence[Mapping[str, Any]],
    *,
    particle_count: int,
) -> Dict[str, Any]:
    """Aggregate like-for-like root action scores from deterministic particles."""
    action_maps = [
        {
            int(row.get("index", -1)): row
            for row in report.get("actions", [])
            if isinstance(row, Mapping)
        }
        for report in reports
    ]
    common_indices = (
        sorted(set.intersection(*(set(rows) for rows in action_maps)))
        if action_maps
        else []
    )
    actions: List[Dict[str, Any]] = []
    for index in common_indices:
        particle_rows = [rows[index] for rows in action_maps]
        scores = [float(row["mean_score"]) for row in particle_rows if row.get("mean_score") is not None]
        if len(scores) != particle_count:
            continue
        template = particle_rows[0]
        mean_score = float(np.mean(scores))
        std_score = float(np.std(scores))
        actions.append(
            {
                "index": index,
                "label": template.get("label"),
                "kind": template.get("kind"),
                "choice": template.get("choice"),
                "particle_count": particle_count,
                "particle_scores": scores,
                "mean_score": mean_score,
                "worst_score": float(np.min(scores)),
                "best_score": float(np.max(scores)),
                "std_score": std_score,
                "risk_adjusted_score": mean_score,
                "particle_actions": particle_rows,
            }
        )
    ranked = sorted(
        actions,
        key=lambda row: (float(row["mean_score"]), -int(row["index"])),
        reverse=True,
    )
    particle_selected_indices = [
        int(selected["index"])
        for report in reports
        for selected in [report.get("selected")]
        if isinstance(selected, Mapping) and selected.get("index") is not None
    ]
    return {
        "actions": ranked,
        "selected": ranked[0] if ranked else None,
        "particle_selected_indices": particle_selected_indices,
        "particle_selected_action_count": len(set(particle_selected_indices)),
        "particle_disagreement": len(set(particle_selected_indices)) > 1,
    }


def evaluate_belief_particle_branches(
    *,
    client: SimCoreClient,
    seed: Sequence[int],
    history: Sequence[Mapping[str, str]],
    player_side: str,
    player_request: Mapping[str, Any],
    score_fn: Optional[ScoreFn] = None,
    config: Optional[TwoPlyConfig] = None,
    source_env_id: str,
    base_belief_seed: Sequence[int],
    particle_count: int = 3,
    result_options: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    config = config or TwoPlyConfig(belief_mode=True)
    if not config.belief_mode:
        raise ValueError("belief particle search requires belief_mode=True")
    if particle_count not in {1, 3, 5}:
        raise ValueError("particle_count must be one of 1, 3, or 5")

    started = time.perf_counter()
    deadline = started + max(0.01, config.max_decision_time_sec)
    preferred_root = _heuristic_index(client, source_env_id, player_side, config.step_timeout)
    root_actions = _ordered_actions(player_request, preferred_root, config.max_root_actions)
    root_indices = [int(action.get("index", -1)) for action in root_actions]
    particle_reports: List[Dict[str, Any]] = []
    particle_errors: List[str] = []
    particle_seeds = [
        derive_belief_particle_seed(base_belief_seed, index)
        for index in range(particle_count)
    ]

    for index, particle_seed in enumerate(particle_seeds):
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            particle_errors.append(f"particle_{index}:decision_deadline")
            break
        try:
            report = evaluate_two_ply_branches(
                client=client,
                seed=seed,
                history=history,
                player_side=player_side,
                player_request=player_request,
                opponent_request=None,
                score_fn=score_fn,
                config=replace(
                    config,
                    max_root_actions=max(config.max_root_actions, len(root_indices)),
                    max_decision_time_sec=remaining,
                ),
                root_action_indices=root_indices,
                result_options=result_options,
                source_env_id=source_env_id,
                belief_seed=particle_seed,
            )
            particle_reports.append(report)
            if report.get("setup_errors"):
                particle_errors.extend(
                    f"particle_{index}:{error}" for error in report.get("setup_errors", [])
                )
        except (SimCoreError, ValueError) as exc:
            particle_errors.append(f"particle_{index}:{type(exc).__name__}:{exc}")

    aggregated = aggregate_belief_particle_reports(
        particle_reports,
        particle_count=particle_count,
    )
    beliefs = [
        report.get("belief")
        for report in particle_reports
        if isinstance(report.get("belief"), Mapping)
    ]
    branch_error_reasons = [
        str(reason)
        for report in particle_reports
        for reason in report.get("branch_error_reasons", [])
    ]
    return {
        "search": "two_ply_belief_particles",
        "player_side": player_side,
        "format": config.format_name,
        "objective": "particle_mean_score",
        "particle_count": particle_count,
        "completed_particle_count": len(particle_reports),
        "particle_seeds": particle_seeds,
        "particle_reports": particle_reports,
        "actions": aggregated["actions"],
        "selected": aggregated["selected"],
        "particle_selected_indices": aggregated["particle_selected_indices"],
        "particle_selected_action_count": aggregated["particle_selected_action_count"],
        "particle_disagreement": aggregated["particle_disagreement"],
        "belief_sample_errors": len(particle_errors),
        "belief_sample_error_reasons": particle_errors[:20],
        "branch_count": sum(int(report.get("branch_count", 0) or 0) for report in particle_reports),
        "leaf_count": sum(int(report.get("leaf_count", 0) or 0) for report in particle_reports),
        "branch_errors": sum(int(report.get("branch_errors", 0) or 0) for report in particle_reports),
        "branch_error_reasons": branch_error_reasons[:20],
        "timeout_count": sum(int(report.get("timeout_count", 0) or 0) for report in particle_reports),
        "capped_leaf_count": sum(int(report.get("capped_leaf_count", 0) or 0) for report in particle_reports),
        "damage_fallbacks": sum(int(report.get("damage_fallbacks", 0) or 0) for report in particle_reports),
        "fallback_to_one_turn": any(bool(report.get("fallback_to_one_turn")) for report in particle_reports),
        "belief": beliefs,
        "belief_samples": len(beliefs),
        "belief_impossible_states": sum(
            int(report.get("belief_impossible_states", 0) or 0) for report in particle_reports
        ),
        "belief_missing_data_count": sum(
            int(report.get("belief_missing_data_count", 0) or 0) for report in particle_reports
        ),
        "belief_constraint_violations": sum(
            int(report.get("belief_constraint_violations", 0) or 0) for report in particle_reports
        ),
        "latency_ms": (time.perf_counter() - started) * 1000.0,
    }
