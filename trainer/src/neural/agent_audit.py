from __future__ import annotations

import argparse
import json
import os
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import torch

from .checkpoints import build_model_from_checkpoint, torch_load
from .damage_engine import set_default_damage_client
from .env_client import SimCoreClient
from .featurize import featurize_battle
from .live_eval_server import EvalRequest, LegalAction, evaluate_with_model, reset_model_caches
from .models.policy_value_mlp import masked_logits
from .one_turn_branch import (
    BranchConfig,
    evaluate_action_branches,
    make_live_sim_value_score_fn,
    make_material_score_fn,
    make_state_score_fn,
    make_value_score_fn,
)
from .runtime import make_battle_seed
from .two_ply_branch import (
    TwoPlyConfig,
    evaluate_belief_particle_branches,
    evaluate_two_ply_branches,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKPOINT_DIR = REPO_ROOT / "artifacts" / "checkpoints"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "agent_audit"
SIM_CORE_DIR = REPO_ROOT / "sim-core"
AGENTS = (
    "random",
    "heuristic",
    "behavior_cloning",
    "replay_policy",
    "action_ranker",
    "action_value_ranker",
    "rollout",
    "ranker_rollout",
    "default",
    "branch_one_turn",
    "branch_two_ply_material",
    "branch_two_ply_belief_material",
    "branch_two_ply_belief3_material",
)
ROLLOUT_AGENTS = {"rollout", "ranker_rollout", "default"}
RESULT_OPTIONS = {
    "view_players": ["p1", "p2"],
    "include_log_delta": True,
    "include_possible_roles": False,
}


@dataclass(frozen=True)
class AgentSpec:
    name: str
    ranker_path: Optional[str] = None
    rollout_mode: str = "off"
    rollout_weight: float = 0.0
    ranker_weight: float = 1.0
    policy_weight: float = 0.0
    branch_one_turn: bool = False
    branch_two_ply: bool = False
    branch_belief: bool = False
    belief_particles: int = 1
    max_root_actions: int = 6
    max_opponent_actions: int = 3
    max_followup_actions: int = 3


SPECS = {
    "random": AgentSpec("random"),
    "heuristic": AgentSpec("heuristic"),
    "behavior_cloning": AgentSpec("behavior_cloning"),
    "replay_policy": AgentSpec(
        "replay_policy",
        ranker_path=str(CHECKPOINT_DIR / "__disabled_ranker__.pt"),
    ),
    "action_ranker": AgentSpec(
        "action_ranker",
        ranker_path=str(CHECKPOINT_DIR / "gen9randombattle_action_ranker_v2.pt"),
    ),
    "action_value_ranker": AgentSpec(
        "action_value_ranker",
        ranker_path=str(CHECKPOINT_DIR / "gen9randombattle_action_value_ranker_v2.pt"),
    ),
    "rollout": AgentSpec(
        "rollout",
        ranker_path=str(CHECKPOINT_DIR / "__disabled_ranker__.pt"),
        rollout_mode="approximate",
        rollout_weight=1.0,
    ),
    "ranker_rollout": AgentSpec(
        "ranker_rollout",
        ranker_path=str(CHECKPOINT_DIR / "gen9randombattle_action_value_ranker_v2.pt"),
        rollout_mode="approximate",
        rollout_weight=0.8,
        ranker_weight=0.2,
    ),
    "default": AgentSpec(
        "default",
        ranker_path=str(CHECKPOINT_DIR / "gen9randombattle_action_value_ranker_v2.pt"),
        rollout_mode="approximate",
        rollout_weight=0.75,
        ranker_weight=0.20,
        policy_weight=0.05,
    ),
    "branch_one_turn": AgentSpec(
        "branch_one_turn",
        branch_one_turn=True,
        max_opponent_actions=3,
    ),
    "branch_two_ply_material": AgentSpec(
        "branch_two_ply_material",
        branch_two_ply=True,
        max_root_actions=3,
        max_opponent_actions=3,
        max_followup_actions=2,
    ),
    "branch_two_ply_belief_material": AgentSpec(
        "branch_two_ply_belief_material",
        branch_two_ply=True,
        branch_belief=True,
        max_root_actions=3,
        max_opponent_actions=3,
        max_followup_actions=2,
    ),
    "branch_two_ply_belief3_material": AgentSpec(
        "branch_two_ply_belief3_material",
        branch_two_ply=True,
        branch_belief=True,
        belief_particles=3,
        max_root_actions=3,
        max_opponent_actions=3,
        max_followup_actions=2,
    ),
}

_worker_spec: Optional[AgentSpec] = None
_worker_client: Optional[SimCoreClient] = None
_bc_model: Optional[torch.nn.Module] = None
_bc_device = torch.device("cpu")
_branch_score_fn = None
_branch_config: Optional[BranchConfig] = None
_two_ply_config: Optional[TwoPlyConfig] = None


def _configure_worker(spec: AgentSpec, rollouts_per_action: int) -> None:
    global _worker_spec, _worker_client, _bc_model, _bc_device
    global _branch_score_fn, _branch_config, _two_ply_config
    _worker_spec = spec
    torch.set_num_threads(1)
    os.environ["NEURAL_SIM_CORE_COMMAND_JSON"] = json.dumps(["node", "dist/src/server.js"])
    os.environ["NEURAL_SIM_CORE_CWD"] = str(SIM_CORE_DIR)
    os.environ["NEURAL_ROLLOUT_MODE"] = spec.rollout_mode
    os.environ["NEURAL_ROLLOUTS_PER_ACTION"] = str(rollouts_per_action)
    os.environ["NEURAL_ROLLOUT_WEIGHT"] = str(spec.rollout_weight)
    os.environ["NEURAL_RANKER_WEIGHT"] = str(spec.ranker_weight)
    os.environ["NEURAL_POLICY_WEIGHT"] = str(spec.policy_weight)
    if spec.ranker_path:
        os.environ["NEURAL_ACTION_RANKER_CHECKPOINT"] = spec.ranker_path
    else:
        os.environ.pop("NEURAL_ACTION_RANKER_CHECKPOINT", None)
    reset_model_caches()
    _worker_client = SimCoreClient(["node", "dist/src/server.js"], str(SIM_CORE_DIR))
    set_default_damage_client(_worker_client)
    if spec.name == "behavior_cloning":
        _bc_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint = torch_load(CHECKPOINT_DIR / "gen9randombattle_bc.pt", _bc_device)
        _bc_model = build_model_from_checkpoint(checkpoint, default_hidden_sizes=[256, 256], device=_bc_device)
        _bc_model.eval()
    if spec.branch_one_turn or spec.branch_two_ply:
        os.environ["NEURAL_ROLLOUT_MODE"] = "off"
        if spec.branch_one_turn:
            _branch_config = BranchConfig(max_opponent_actions=spec.max_opponent_actions)
        if spec.branch_two_ply:
            _two_ply_config = TwoPlyConfig(
                max_root_actions=spec.max_root_actions,
                max_opponent_actions=spec.max_opponent_actions,
                max_followup_actions=spec.max_followup_actions,
                max_decision_time_sec=float(os.environ.get("NEURAL_TWO_PLY_MAX_DECISION_SEC", "8")),
                belief_mode=spec.branch_belief,
            )
        # The simple HP-differential "material" scorer empirically beats the richer
        # "state" scorer (45% vs 30% in the paired audit), so it is the default.
        scorer = os.environ.get("NEURAL_BRANCH_SCORER", "material").strip().lower()
        if scorer == "value":
            _branch_score_fn = make_value_score_fn()
        elif scorer == "live_sim_value":
            _branch_score_fn = make_live_sim_value_score_fn()
        elif scorer == "state":
            _branch_score_fn = make_state_score_fn()
        else:
            _branch_score_fn = make_material_score_fn()


def _legal_actions(request: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    legal = request.get("legal_actions") if isinstance(request.get("legal_actions"), Mapping) else {}
    actions = legal.get("actions") if isinstance(legal.get("actions"), list) else []
    return [action for action in actions if isinstance(action, Mapping)]


def _choice_by_index(request: Mapping[str, Any], index: int) -> Optional[Mapping[str, Any]]:
    return next((action for action in _legal_actions(request) if action.get("index") == index), None)


def _live_actions(request: Mapping[str, Any]) -> List[LegalAction]:
    return [
        LegalAction(
            kind=str(action.get("kind") or ""),
            label=str(action.get("label") or action.get("choice") or ""),
            slot=action.get("slot") if isinstance(action.get("slot"), int) else None,
            index=action.get("index") if isinstance(action.get("index"), int) else None,
            disabled=False,
        )
        for action in _legal_actions(request)
    ]


def _baseline_choice(
    agent: str,
    env_id: str,
    player: str,
    request: Mapping[str, Any],
    rng: random.Random,
) -> Tuple[str, Dict[str, Any]]:
    assert _worker_client is not None
    if agent == "random":
        actions = _legal_actions(request)
        action = rng.choice(actions) if actions else {"choice": "default"}
        return str(action.get("choice") or "default"), {"method": "random"}
    decision = _worker_client.agent_action(env_id, player, "heuristic", timeout_sec=20)
    return str(decision.get("choice") or "default"), {"method": "heuristic"}


def _bc_choice(view: Mapping[str, Any], request: Mapping[str, Any]) -> Tuple[str, Dict[str, Any]]:
    assert _bc_model is not None
    features = featurize_battle(dict(view), dict(request))
    x = torch.from_numpy(features.flat).to(_bc_device).unsqueeze(0)
    mask = torch.from_numpy(features.legal_mask).to(_bc_device).unsqueeze(0)
    with torch.inference_mode():
        logits, _ = _bc_model(x)
        index = int(masked_logits(logits, mask).argmax(dim=-1).item())
    action = _choice_by_index(request, index)
    if action is None:
        actions = _legal_actions(request)
        action = actions[0] if actions else {"choice": "default", "index": 0}
    return str(action.get("choice") or "default"), {
        "method": "behavior_cloning",
        "index": action.get("index"),
    }


def _learned_choice(
    spec: AgentSpec,
    env_id: str,
    player: str,
    request: Mapping[str, Any],
    protocol_log: Sequence[str],
) -> Tuple[str, Dict[str, Any]]:
    payload = EvalRequest(
        room_id=f"audit-{env_id}",
        url=f"sim-core://{env_id}",
        player=player,
        log=list(protocol_log),
        request=dict(request),
        legal_actions=_live_actions(request),
    )
    report = evaluate_with_model(payload)
    estimates = [
        row for row in (report.get("debug") or {}).get("all_action_estimates", [])
        if isinstance(row, Mapping) and not row.get("disabled")
    ]
    if spec.name == "replay_policy":
        field = "policy_prob"
    elif spec.name in {"action_ranker", "action_value_ranker"}:
        field = "ranker_score"
    elif spec.name == "rollout":
        field = "expected_value"
    else:
        field = "final_score"
    ranked = [row for row in estimates if row.get(field) is not None]
    selected = max(ranked, key=lambda row: float(row.get(field) or 0.0)) if ranked else None
    action = _choice_by_index(request, int(selected.get("index", -1))) if selected else None
    if action is None:
        actions = _legal_actions(request)
        action = actions[0] if actions else {"choice": "default", "index": 0}
    damage_methods = {
        str(row.get("damage_method"))
        for row in estimates
        if row.get("damage_method") is not None
    }
    damage_rows = [
        row
        for row in estimates
        if row.get("damage_method") not in {None, "not_applicable_switch"}
    ]
    fallback_reasons = Counter(
        str(row.get("fallback_reason") or "unspecified")
        for row in damage_rows
        if row.get("damage_method") == "heuristic_fallback"
    )
    rollout_unavailable = sum(1 for row in estimates if row.get("rollout_unavailable_reason"))
    rollout_timeouts = sum(
        1
        for row in estimates
        if "timeout" in str(row.get("rollout_unavailable_reason") or row.get("fallback_reason") or "").lower()
    )
    return str(action.get("choice") or "default"), {
        "method": report.get("action_recommendation_method"),
        "selected_field": field,
        "index": action.get("index"),
        "fallback": bool(report.get("fallback_reason") or not ranked),
        "damage_fallback": "heuristic_fallback" in damage_methods,
        "damage_calls": len(damage_rows),
        "smogon_calc_calls": sum(row.get("damage_method") == "smogon_calc" for row in damage_rows),
        "heuristic_fallback_calls": sum(row.get("damage_method") == "heuristic_fallback" for row in damage_rows),
        "damage_fallback_reasons": dict(fallback_reasons),
        "rollout_unavailable": rollout_unavailable > 0,
        "rollout_timeout_count": rollout_timeouts,
        "ranker_path": report.get("action_ranker_path"),
        "value_path": report.get("checkpoint_path"),
        "warning": report.get("warning"),
    }


def _branch_choice(
    env_id: str,
    player: str,
    request: Mapping[str, Any],
    requests: Mapping[str, Any],
    seed: Sequence[int],
    history: Sequence[Mapping[str, str]],
) -> Tuple[str, Dict[str, Any]]:
    assert _worker_client is not None and _branch_score_fn is not None and _worker_spec is not None
    opponent = "p2" if player == "p1" else "p1"
    if _worker_spec.branch_two_ply:
        assert _two_ply_config is not None
        side_offset = 17 if player == "p1" else 31
        belief_seed = [
            (int(seed[i]) + side_offset + len(history) * (i + 3) * 97) & 0xFFFF
            for i in range(4)
        ]
        if _worker_spec.branch_belief and _worker_spec.belief_particles > 1:
            report = evaluate_belief_particle_branches(
                client=_worker_client,
                seed=list(seed),
                history=list(history),
                player_side=player,
                player_request=request,
                score_fn=_branch_score_fn,
                config=_two_ply_config,
                source_env_id=env_id,
                base_belief_seed=belief_seed,
                particle_count=_worker_spec.belief_particles,
            )
            method = "branch_two_ply_belief3_material"
        else:
            report = evaluate_two_ply_branches(
                client=_worker_client,
                seed=list(seed),
                history=list(history),
                player_side=player,
                player_request=request,
                opponent_request=requests.get(opponent) if isinstance(requests, Mapping) else None,
                score_fn=_branch_score_fn,
                config=_two_ply_config,
                source_env_id=env_id if _worker_spec.branch_belief else None,
                belief_seed=belief_seed if _worker_spec.branch_belief else None,
            )
            method = (
                "branch_two_ply_belief_material"
                if _worker_spec.branch_belief
                else "branch_two_ply_material"
            )
    else:
        assert _branch_config is not None
        report = evaluate_action_branches(
            client=_worker_client,
            seed=list(seed),
            history=list(history),
            player_side=player,
            player_request=request,
            opponent_request=requests.get(opponent) if isinstance(requests, Mapping) else None,
            score_fn=_branch_score_fn,
            config=_branch_config,
        )
        method = "branch_one_turn"
    selected = report.get("selected")
    if isinstance(selected, Mapping) and selected.get("choice"):
        choice = str(selected.get("choice"))
    else:
        actions = _legal_actions(request)
        choice = str(actions[0].get("choice") or "default") if actions else "default"
    return choice, {
        "method": method,
        "index": selected.get("index") if isinstance(selected, Mapping) else None,
        "fallback": not isinstance(selected, Mapping),
        "damage_fallback": False,
        "damage_calls": 0,
        "smogon_calc_calls": 0,
        "heuristic_fallback_calls": 0,
        "damage_fallback_reasons": {},
        "rollout_unavailable": bool(not isinstance(selected, Mapping)),
        "rollout_timeout_count": 0,
        "branch_count": int(report.get("branch_count", 0) or 0),
        "leaf_count": int(report.get("leaf_count", 0) or 0),
        "branch_errors": int(report.get("branch_errors", 0) or 0),
        "branch_timeout_count": int(report.get("timeout_count", 0) or 0),
        "branch_capped_count": int(report.get("capped_leaf_count", 0) or 0),
        "belief_samples": int(report.get("belief_samples", 0) or 0),
        "belief_impossible_states": int(report.get("belief_impossible_states", 0) or 0),
        "belief_missing_data_count": int(report.get("belief_missing_data_count", 0) or 0),
        "belief_constraint_violations": int(report.get("belief_constraint_violations", 0) or 0),
        "belief_sample_errors": int(report.get("belief_sample_errors", 0) or 0),
        "particle_count": int(report.get("particle_count", report.get("belief_samples", 0)) or 0),
        "particle_disagreement": bool(report.get("particle_disagreement")),
        "particle_action_scores": [
            {
                "index": row.get("index"),
                "mean_score": row.get("mean_score"),
                "std_score": row.get("std_score"),
                "worst_score": row.get("worst_score"),
                "best_score": row.get("best_score"),
                "particle_scores": row.get("particle_scores"),
            }
            for row in report.get("actions", [])
            if isinstance(row, Mapping)
        ],
        "warning": (
            "; ".join(
                str(reason)
                for reason in (
                    list(report.get("belief_sample_error_reasons", []))
                    + list(report.get("branch_error_reasons", []))
                )[:3]
            )
            if report.get("branch_errors") or report.get("belief_sample_errors")
            else None
        ),
    }


def _choose(
    agent: str,
    env_id: str,
    player: str,
    view: Mapping[str, Any],
    request: Mapping[str, Any],
    protocol_log: Sequence[str],
    rng: random.Random,
) -> Tuple[str, Dict[str, Any]]:
    assert _worker_spec is not None
    if agent in {"random", "heuristic"}:
        return _baseline_choice(agent, env_id, player, request, rng)
    if agent == "behavior_cloning":
        return _bc_choice(view, request)
    return _learned_choice(_worker_spec, env_id, player, request, protocol_log)


def _run_battle(task: Tuple[int, Sequence[int], str]) -> Dict[str, Any]:
    assert _worker_client is not None and _worker_spec is not None
    battle_index, seed, audit_side = task
    env_id = _worker_client.create_env(
        "gen9randombattle",
        seed,
        {"p1": {"controller": "external"}, "p2": {"controller": "external"}},
        timeout_sec=30,
    )
    agents = {audit_side: _worker_spec.name, "p2" if audit_side == "p1" else "p1": "heuristic"}
    protocol_log: List[str] = []
    choice_history: List[Dict[str, str]] = []
    decisions = Counter()
    methods = Counter()
    audit_latencies: List[float] = []
    fallback_count = 0
    damage_fallback_count = 0
    damage_call_count = 0
    smogon_calc_count = 0
    heuristic_fallback_call_count = 0
    damage_fallback_reasons: Counter[str] = Counter()
    rollout_unavailable_count = 0
    rollout_timeout_count = 0
    branch_count = 0
    leaf_count = 0
    branch_error_count = 0
    branch_timeout_count = 0
    branch_capped_count = 0
    belief_samples = 0
    belief_impossible_states = 0
    belief_missing_data_count = 0
    belief_constraint_violations = 0
    belief_sample_errors = 0
    particle_decisions = 0
    particle_disagreement_count = 0
    audit_action_indices: List[Optional[int]] = []
    particle_decision_reports: List[Dict[str, Any]] = []
    notes: List[str] = []
    rng = random.Random(f"{list(seed)}:{audit_side}:{_worker_spec.name}")
    started = time.perf_counter()
    result: Dict[str, Any] = {}
    try:
        result = _worker_client.reset(env_id, RESULT_OPTIONS, timeout_sec=60)
        protocol_log.extend(result.get("log_delta") or [])
        while not result.get("terminated"):
            requests = result.get("requests") or {}
            views = result.get("views") or {}
            choices: Dict[str, str] = {}
            for player in ("p1", "p2"):
                request = requests.get(player)
                view = views.get(player)
                if not isinstance(request, Mapping) or not isinstance(view, Mapping):
                    continue
                before = time.perf_counter()
                if agents[player] in {
                    "branch_one_turn",
                    "branch_two_ply_material",
                    "branch_two_ply_belief_material",
                    "branch_two_ply_belief3_material",
                }:
                    choice, debug = _branch_choice(env_id, player, request, requests, seed, choice_history)
                else:
                    choice, debug = _choose(agents[player], env_id, player, view, request, protocol_log, rng)
                elapsed_ms = (time.perf_counter() - before) * 1000.0
                if agents[player] == _worker_spec.name:
                    audit_latencies.append(elapsed_ms)
                decisions[agents[player]] += 1
                methods[str(debug.get("method") or "unknown")] += 1
                fallback_count += int(bool(debug.get("fallback")))
                damage_fallback_count += int(bool(debug.get("damage_fallback")))
                damage_call_count += int(debug.get("damage_calls", 0) or 0)
                smogon_calc_count += int(debug.get("smogon_calc_calls", 0) or 0)
                heuristic_fallback_call_count += int(debug.get("heuristic_fallback_calls", 0) or 0)
                damage_fallback_reasons.update(debug.get("damage_fallback_reasons") or {})
                rollout_unavailable_count += int(bool(debug.get("rollout_unavailable")))
                rollout_timeout_count += int(debug.get("rollout_timeout_count", 0) or 0)
                branch_count += int(debug.get("branch_count", 0) or 0)
                leaf_count += int(debug.get("leaf_count", 0) or 0)
                branch_error_count += int(debug.get("branch_errors", 0) or 0)
                branch_timeout_count += int(debug.get("branch_timeout_count", 0) or 0)
                branch_capped_count += int(debug.get("branch_capped_count", 0) or 0)
                belief_samples += int(debug.get("belief_samples", 0) or 0)
                belief_impossible_states += int(debug.get("belief_impossible_states", 0) or 0)
                belief_missing_data_count += int(debug.get("belief_missing_data_count", 0) or 0)
                belief_constraint_violations += int(debug.get("belief_constraint_violations", 0) or 0)
                belief_sample_errors += int(debug.get("belief_sample_errors", 0) or 0)
                if int(debug.get("particle_count", 0) or 0) > 1:
                    particle_decisions += 1
                    particle_disagreement_count += int(bool(debug.get("particle_disagreement")))
                if agents[player] == _worker_spec.name:
                    audit_action_indices.append(
                        int(debug["index"]) if debug.get("index") is not None else None
                    )
                    if int(debug.get("particle_count", 0) or 0) > 1:
                        particle_decision_reports.append(
                            {
                                "turn": int((result.get("info") or {}).get("turn") or 0),
                                "side": player,
                                "selected_index": debug.get("index"),
                                "particle_count": int(debug.get("particle_count", 0) or 0),
                                "particle_disagreement": bool(debug.get("particle_disagreement")),
                                "belief_sample_errors": int(debug.get("belief_sample_errors", 0) or 0),
                                "public_info_violations": int(
                                    debug.get("belief_constraint_violations", 0) or 0
                                ),
                                "branch_count": int(debug.get("branch_count", 0) or 0),
                                "leaf_count": int(debug.get("leaf_count", 0) or 0),
                                "latency_ms": elapsed_ms,
                                "damage_fallbacks": int(bool(debug.get("damage_fallback"))),
                                "actions": debug.get("particle_action_scores") or [],
                            }
                        )
                if debug.get("warning"):
                    notes.append(str(debug["warning"]))
                choices[player] = choice
            if not choices:
                notes.append("no_actionable_request")
                break
            result = _worker_client.step(env_id, choices, RESULT_OPTIONS, timeout_sec=60)
            protocol_log.extend(result.get("log_delta") or [])
            choice_history.append(dict(choices))
        winner = result.get("winner")
        audit_result = "win" if winner == audit_side else "loss" if winner in {"p1", "p2"} else "draw"
        return {
            "agent": _worker_spec.name,
            "opponent": "heuristic",
            "battle_index": battle_index,
            "seed": list(seed),
            "audit_side": audit_side,
            "winner": winner,
            "result": audit_result,
            "turns": int((result.get("info") or {}).get("turn") or 0),
            "wall_time_sec": time.perf_counter() - started,
            "audit_decisions": decisions[_worker_spec.name],
            "avg_decision_latency_ms": (
                sum(audit_latencies) / len(audit_latencies) if audit_latencies else 0.0
            ),
            "decision_latencies_ms": audit_latencies,
            "fallback_count": fallback_count,
            "damage_fallback_count": damage_fallback_count,
            "damage_call_count": damage_call_count,
            "smogon_calc_count": smogon_calc_count,
            "heuristic_fallback_call_count": heuristic_fallback_call_count,
            "damage_fallback_reasons": dict(damage_fallback_reasons),
            "rollout_unavailable_count": rollout_unavailable_count,
            "rollout_timeout_count": rollout_timeout_count,
            "branch_count": branch_count,
            "leaf_count": leaf_count,
            "branch_error_count": branch_error_count,
            "branch_timeout_count": branch_timeout_count,
            "branch_capped_count": branch_capped_count,
            "belief_samples": belief_samples,
            "belief_impossible_states": belief_impossible_states,
            "belief_missing_data_count": belief_missing_data_count,
            "belief_constraint_violations": belief_constraint_violations,
            "belief_sample_errors": belief_sample_errors,
            "particle_decisions": particle_decisions,
            "particle_disagreement_count": particle_disagreement_count,
            "audit_action_indices": audit_action_indices,
            "particle_decisions_report": particle_decision_reports,
            "methods": dict(methods),
            "notes": sorted(set(notes)),
            "log": protocol_log,
        }
    except Exception as exc:
        return {
            "agent": _worker_spec.name,
            "opponent": "heuristic",
            "battle_index": battle_index,
            "seed": list(seed),
            "audit_side": audit_side,
            "winner": None,
            "result": "timeout_or_error",
            "turns": int((result.get("info") or {}).get("turn") or 0),
            "wall_time_sec": time.perf_counter() - started,
            "audit_decisions": decisions[_worker_spec.name],
            "avg_decision_latency_ms": sum(audit_latencies) / len(audit_latencies) if audit_latencies else 0.0,
            "decision_latencies_ms": audit_latencies,
            "fallback_count": fallback_count,
            "damage_fallback_count": damage_fallback_count,
            "damage_call_count": damage_call_count,
            "smogon_calc_count": smogon_calc_count,
            "heuristic_fallback_call_count": heuristic_fallback_call_count,
            "damage_fallback_reasons": dict(damage_fallback_reasons),
            "rollout_unavailable_count": rollout_unavailable_count,
            "rollout_timeout_count": rollout_timeout_count,
            "branch_count": branch_count,
            "leaf_count": leaf_count,
            "branch_error_count": branch_error_count,
            "branch_timeout_count": branch_timeout_count,
            "branch_capped_count": branch_capped_count,
            "belief_samples": belief_samples,
            "belief_impossible_states": belief_impossible_states,
            "belief_missing_data_count": belief_missing_data_count,
            "belief_constraint_violations": belief_constraint_violations,
            "belief_sample_errors": belief_sample_errors,
            "particle_decisions": particle_decisions,
            "particle_disagreement_count": particle_disagreement_count,
            "audit_action_indices": audit_action_indices,
            "particle_decisions_report": particle_decision_reports,
            "methods": dict(methods),
            "notes": [f"{type(exc).__name__}: {exc}"],
            "log": protocol_log,
        }
    finally:
        try:
            _worker_client.close_env(env_id, timeout_sec=10)
        except Exception:
            pass


def _summary(agent: str, rows: Sequence[Mapping[str, Any]], wall_time_sec: float, workers: int) -> Dict[str, Any]:
    wins = sum(row.get("result") == "win" for row in rows)
    losses = sum(row.get("result") == "loss" for row in rows)
    draws = sum(row.get("result") == "draw" for row in rows)
    failures = sum(row.get("result") == "timeout_or_error" for row in rows)
    completed = wins + losses + draws
    method_counts = Counter()
    for row in rows:
        method_counts.update(row.get("methods") or {})
    damage_fallback_reasons = Counter()
    decision_latencies: List[float] = []
    for row in rows:
        damage_fallback_reasons.update(row.get("damage_fallback_reasons") or {})
        decision_latencies.extend(float(value) for value in row.get("decision_latencies_ms") or [])
    damage_calls = sum(int(row.get("damage_call_count", 0)) for row in rows)
    heuristic_fallback_calls = sum(int(row.get("heuristic_fallback_call_count", 0)) for row in rows)
    audit_decisions = sum(int(row.get("audit_decisions", 0)) for row in rows)
    return {
        "agent": agent,
        "battles": len(rows),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "timeouts_or_errors": failures,
        "winrate": wins / completed if completed else 0.0,
        "avg_turns": float(np.mean([row.get("turns", 0) for row in rows])) if rows else 0.0,
        "avg_decision_latency_ms": float(np.mean(decision_latencies)) if decision_latencies else 0.0,
        "p95_decision_latency_ms": float(np.percentile(decision_latencies, 95)) if decision_latencies else 0.0,
        "fallbacks": sum(int(row.get("fallback_count", 0)) for row in rows),
        "damage_fallbacks": sum(int(row.get("damage_fallback_count", 0)) for row in rows),
        "total_damage_calls": damage_calls,
        "smogon_calc_calls": sum(int(row.get("smogon_calc_count", 0)) for row in rows),
        "heuristic_fallback_calls": heuristic_fallback_calls,
        "damage_fallback_rate": heuristic_fallback_calls / damage_calls if damage_calls else 0.0,
        "top_damage_fallback_reasons": dict(damage_fallback_reasons.most_common(5)),
        "rollout_unavailable": sum(int(row.get("rollout_unavailable_count", 0)) for row in rows),
        "rollout_timeout_count": sum(int(row.get("rollout_timeout_count", 0)) for row in rows),
        "avg_branches_per_decision": (
            sum(int(row.get("branch_count", 0)) for row in rows) / audit_decisions
            if audit_decisions else 0.0
        ),
        "avg_leaves_per_decision": (
            sum(int(row.get("leaf_count", 0)) for row in rows) / audit_decisions
            if audit_decisions else 0.0
        ),
        "branch_error_count": sum(int(row.get("branch_error_count", 0)) for row in rows),
        "branch_timeout_count": sum(int(row.get("branch_timeout_count", 0)) for row in rows),
        "branch_capped_count": sum(int(row.get("branch_capped_count", 0)) for row in rows),
        "belief_samples": sum(int(row.get("belief_samples", 0)) for row in rows),
        "belief_impossible_states": sum(int(row.get("belief_impossible_states", 0)) for row in rows),
        "belief_missing_data_count": sum(int(row.get("belief_missing_data_count", 0)) for row in rows),
        "belief_constraint_violations": sum(int(row.get("belief_constraint_violations", 0)) for row in rows),
        "belief_sample_errors": sum(int(row.get("belief_sample_errors", 0)) for row in rows),
        "particle_count": SPECS[agent].belief_particles if SPECS[agent].branch_belief else 0,
        "particle_decisions": sum(int(row.get("particle_decisions", 0)) for row in rows),
        "particle_disagreement_count": sum(
            int(row.get("particle_disagreement_count", 0)) for row in rows
        ),
        "particle_disagreement_rate": (
            sum(int(row.get("particle_disagreement_count", 0)) for row in rows)
            / sum(int(row.get("particle_decisions", 0)) for row in rows)
            if sum(int(row.get("particle_decisions", 0)) for row in rows)
            else 0.0
        ),
        "method_counts": dict(method_counts),
        "wall_time_sec": wall_time_sec,
        "battles_per_sec": len(rows) / wall_time_sec if wall_time_sec > 0 else 0.0,
        "workers": workers,
    }


def run_agent(agent: str, battles: int, workers: int, rollouts_per_action: int) -> Dict[str, Any]:
    spec = SPECS[agent]
    tasks = [
        (index, make_battle_seed(index // 2), "p1" if index % 2 == 0 else "p2")
        for index in range(battles)
    ]
    started = time.perf_counter()
    rows: List[Dict[str, Any]] = []
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_configure_worker,
        initargs=(spec, rollouts_per_action),
    ) as pool:
        futures = [pool.submit(_run_battle, task) for task in tasks]
        for completed, future in enumerate(as_completed(futures), start=1):
            rows.append(future.result())
            print(f"agent-audit {agent} {completed}/{battles}", flush=True)
    rows.sort(key=lambda row: int(row["battle_index"]))
    wall = time.perf_counter() - started
    return {"summary": _summary(agent, rows, wall, workers), "battles": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run paired-seed multicore agent ablations against the heuristic baseline.")
    parser.add_argument("--agents", default=",".join(AGENTS))
    parser.add_argument("--battles", type=int, default=20, help="Battles per agent; even values pair both sides.")
    parser.add_argument("--workers", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 2)))
    parser.add_argument("--rollouts-per-action", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR / "runs")
    args = parser.parse_args()
    selected = [name.strip() for name in args.agents.split(",") if name.strip()]
    unknown = sorted(set(selected) - set(AGENTS))
    if unknown:
        parser.error(f"unknown agents: {', '.join(unknown)}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    combined = []
    for agent in selected:
        effective_workers = min(args.workers, args.battles)
        result = run_agent(agent, args.battles, effective_workers, args.rollouts_per_action)
        combined.append(result["summary"])
        (args.output_dir / f"{agent}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    payload = {
        "machine": {
            "cpu_count": os.cpu_count(),
            "workers": args.workers,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "battles_per_agent": args.battles,
        "rollouts_per_action": args.rollouts_per_action,
        "summaries": combined,
    }
    (args.output_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output_dir / "summary.json"), "agents": selected}), flush=True)


if __name__ == "__main__":
    main()
