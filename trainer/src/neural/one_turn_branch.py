"""Deterministic one-turn sim-core branch evaluation (Gen 9 singles only).

This evaluates a candidate player action by forking the current battle through
deterministic replay-from-seed, applying the action against a bounded set of
opponent actions, advancing the simulator exactly one step, and scoring the
resulting state with the existing live-private value model.

It never mutates the live/original environment (each branch uses a fresh
``env_id``) and performs no approximate/heuristic damage estimation, so it cannot
emit a heuristic damage fallback. Results are deterministic for a fixed seed,
choice history, and action set.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

import numpy as np

from .action_features import classify_action_category
from .env_client import SimCoreClient, SimCoreError


ScoreFn = Callable[[Sequence[str], Mapping[str, Any], str], float]

DEFAULT_RESULT_OPTIONS: Dict[str, Any] = {
    "view_players": ["p1", "p2"],
    "include_log_delta": True,
    "include_possible_roles": False,
}


@dataclass(frozen=True)
class BranchConfig:
    max_opponent_actions: int = 3
    risk_lambda: float = 0.0
    opponent_ordering: str = "legal"  # "legal" | "moves_first"
    objective: str = "risk_adjusted_score"  # ranking key on each action row
    create_timeout: float = 30.0
    step_timeout: float = 30.0
    format_name: str = "gen9randombattle"


def _legal_action_list(request: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(request, Mapping):
        return []
    legal = request.get("legal_actions")
    if not isinstance(legal, Mapping):
        return []
    actions = legal.get("actions")
    if not isinstance(actions, list):
        return []
    return [dict(action) for action in actions if isinstance(action, Mapping)]


def _opponent_candidates(
    opponent_request: Optional[Mapping[str, Any]],
    config: BranchConfig,
) -> List[Optional[Dict[str, Any]]]:
    actions = _legal_action_list(opponent_request)
    if not actions:
        # Opponent has no actionable request this turn (e.g. the audited side is
        # in a forced switch). Represent as a single no-opponent-action branch.
        return [None]
    if config.opponent_ordering == "moves_first":
        actions = sorted(
            actions,
            key=lambda action: 0 if str(action.get("kind") or "").startswith("move") else 1,
        )
    limit = max(1, int(config.max_opponent_actions))
    return list(actions[:limit])


def _terminal_score(result: Mapping[str, Any], player_side: str) -> float:
    winner = result.get("winner")
    if winner == player_side:
        return 1.0
    if winner in ("p1", "p2"):
        return -1.0
    return 0.0


def _fork_and_step(
    client: SimCoreClient,
    seed: Sequence[int],
    history: Sequence[Mapping[str, str]],
    branch_choices: Mapping[str, str],
    config: BranchConfig,
    result_options: Mapping[str, Any],
):
    """Fork a fresh env, replay history to the current state, then step once.

    Returns ``(step_result, protocol_log, error)``. ``step_result`` is ``None``
    when the branch could not be evaluated, and ``error`` then names the reason.
    """
    env_id: Optional[str] = None
    protocol: List[str] = []
    try:
        env_id = client.create_env(
            config.format_name,
            list(seed),
            {"p1": {"controller": "external"}, "p2": {"controller": "external"}},
            timeout_sec=config.create_timeout,
        )
        result = client.reset(env_id, dict(result_options), timeout_sec=config.step_timeout)
        protocol.extend(result.get("log_delta") or [])
        for entry in history:
            if result.get("terminated"):
                return None, protocol, "history_replay_terminated_early"
            result = client.step(env_id, dict(entry), dict(result_options), timeout_sec=config.step_timeout)
            protocol.extend(result.get("log_delta") or [])
        if result.get("terminated"):
            return None, protocol, "history_replay_terminated_early"
        result = client.step(env_id, dict(branch_choices), dict(result_options), timeout_sec=config.step_timeout)
        protocol.extend(result.get("log_delta") or [])
        return result, protocol, None
    except SimCoreError as exc:
        return None, protocol, f"sim_core_error:{type(exc).__name__}:{exc}"
    finally:
        if env_id is not None:
            try:
                client.close_env(env_id, timeout_sec=config.create_timeout)
            except Exception:
                pass


def evaluate_action_branches(
    *,
    client: SimCoreClient,
    seed: Sequence[int],
    history: Sequence[Mapping[str, str]],
    player_side: str,
    player_request: Mapping[str, Any],
    opponent_request: Optional[Mapping[str, Any]],
    score_fn: ScoreFn,
    config: Optional[BranchConfig] = None,
    legal_action_indices: Optional[Sequence[int]] = None,
    result_options: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate one-turn branches for the audited player's legal actions.

    ``score_fn(protocol_log, step_result, player_side)`` scores a non-terminal
    resulting state from the audited player's perspective in ``[-1, 1]``.
    Terminal branches use the actual win/loss/tie outcome.
    """
    config = config or BranchConfig()
    options = dict(result_options or DEFAULT_RESULT_OPTIONS)
    opponent_side = "p2" if player_side == "p1" else "p1"
    started = time.perf_counter()

    player_actions = _legal_action_list(player_request)
    if legal_action_indices is not None:
        want = {int(index) for index in legal_action_indices}
        player_actions = [a for a in player_actions if int(a.get("index", -1)) in want]
    opponent_actions = _opponent_candidates(opponent_request, config)
    opponent_labels = [o.get("label") if o else None for o in opponent_actions]

    action_rows: List[Dict[str, Any]] = []
    total_branches = 0
    total_errors = 0

    for action in player_actions:
        action_started = time.perf_counter()
        player_choice = action.get("choice")
        scores: List[float] = []
        branch_rows: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        terminal_count = 0

        if not player_choice:
            errors.append({"reason": "missing_choice", "index": action.get("index")})
        else:
            for opponent in opponent_actions:
                branch_choices: Dict[str, str] = {player_side: str(player_choice)}
                if opponent is not None and opponent.get("choice"):
                    branch_choices[opponent_side] = str(opponent.get("choice"))
                result, protocol, error = _fork_and_step(
                    client, seed, history, branch_choices, config, options
                )
                total_branches += 1
                if error is not None or not isinstance(result, Mapping):
                    total_errors += 1
                    errors.append(
                        {"reason": error or "no_result", "opponent": opponent.get("label") if opponent else None}
                    )
                    continue
                if result.get("terminated"):
                    score = _terminal_score(result, player_side)
                    method = "terminal"
                    terminal_count += 1
                else:
                    try:
                        score = float(score_fn(protocol, result, player_side))
                        method = "state_score"
                    except Exception as exc:  # pragma: no cover - scorer guard
                        total_errors += 1
                        errors.append(
                            {
                                "reason": f"score_failed:{type(exc).__name__}:{exc}",
                                "opponent": opponent.get("label") if opponent else None,
                            }
                        )
                        continue
                scores.append(score)
                branch_rows.append(
                    {
                        "opponent_action": opponent.get("label") if opponent else None,
                        "score": score,
                        "terminal": bool(result.get("terminated")),
                        "winner": result.get("winner"),
                        "turn": int((result.get("info") or {}).get("turn") or 0),
                        "method": method,
                    }
                )

        mean_score = float(np.mean(scores)) if scores else None
        worst_score = float(np.min(scores)) if scores else None
        best_score = float(np.max(scores)) if scores else None
        std_score = float(np.std(scores)) if scores else None
        risk_adjusted = (
            mean_score - config.risk_lambda * std_score
            if mean_score is not None and std_score is not None
            else mean_score
        )
        action_rows.append(
            {
                "index": int(action.get("index", -1)),
                "label": str(action.get("label") or action.get("choice") or "unknown"),
                "kind": str(action.get("kind") or "unknown"),
                "action_category": classify_action_category(action),
                "choice": player_choice,
                "branch_count": len(scores),
                "mean_score": mean_score,
                "worst_score": worst_score,
                "best_score": best_score,
                "std_score": std_score,
                "risk_adjusted_score": risk_adjusted,
                "terminal_branches": terminal_count,
                "opponent_actions_considered": opponent_labels,
                "branches": branch_rows,
                "errors": errors,
                "latency_ms": (time.perf_counter() - action_started) * 1000.0,
                "damage_fallbacks": 0,
            }
        )

    def _objective(row: Mapping[str, Any]) -> float:
        value = row.get(config.objective)
        return float(value) if value is not None else float("-inf")

    ranked = sorted(action_rows, key=_objective, reverse=True)
    return {
        "player_side": player_side,
        "format": config.format_name,
        "max_opponent_actions": config.max_opponent_actions,
        "objective": config.objective,
        "risk_lambda": config.risk_lambda,
        "opponent_actions_considered": opponent_labels,
        "actions": ranked,
        "branch_count": total_branches,
        "branch_errors": total_errors,
        "damage_fallbacks": 0,
        "latency_ms": (time.perf_counter() - started) * 1000.0,
        "selected": ranked[0] if ranked else None,
    }


def make_value_score_fn(device: Any = None) -> ScoreFn:
    """Build a scorer that scores a state with the live-private value model.

    Returns a value in ``[-1, 1]`` from ``player_side``'s perspective, matching
    the perspective the live-private value model is trained on.
    """
    import torch

    from .live_eval_server import INPUT_SIZE, _value_features_for_model, load_value_model_once
    from .live_private_features import build_features_from_live_payload

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _score(log: Sequence[str], step_result: Mapping[str, Any], player_side: str) -> float:
        request_view = (step_result.get("requests") or {}).get(player_side)
        model, metadata = load_value_model_once()
        live_features, _, _, _, _ = build_features_from_live_payload(
            log=list(log),
            room_id="branch",
            url="branch://one-turn",
            player=player_side,
            request_payload=dict(request_view) if isinstance(request_view, Mapping) else None,
            legal_actions=[],
        )
        features = _value_features_for_model(
            model_metadata=metadata,
            public_features=np.zeros(INPUT_SIZE, dtype=np.float32),
            live_features=live_features,
        )
        x = torch.tensor(features, dtype=torch.float32, device=device).unsqueeze(0)
        with torch.no_grad():
            output = model(x)
        if isinstance(output, tuple):
            value_tensor = output[1]
        elif isinstance(output, dict):
            value_tensor = output.get("value") or output.get("values")
        else:
            value_tensor = output
        return float(value_tensor.squeeze().detach().cpu().item())

    return _score


DEFAULT_LIVE_SIM_VALUE_CHECKPOINT = "artifacts/checkpoints/gen9randombattle_live_sim_value_v1.pt"


def make_live_sim_value_score_fn(checkpoint_path: Optional[str] = None, device: Any = None) -> ScoreFn:
    """Bounded live/sim value scorer trained on the serving feature distribution.

    Loads `BoundedValueMLP` (tanh output in [-1,1]) and scores a branch state via
    the same `build_features_from_live_payload` path used at serving time. Fails
    loudly on feature-version / dimension mismatch.
    """
    import os

    import torch

    from .live_private_features import FEATURE_DIM, FEATURE_VERSION, build_features_from_live_payload
    from .models.value_mlp import BoundedValueMLP

    path = checkpoint_path or os.environ.get("NEURAL_LIVE_SIM_VALUE_CHECKPOINT") or DEFAULT_LIVE_SIM_VALUE_CHECKPOINT
    if not os.path.exists(path):
        raise FileNotFoundError(f"live_sim_value checkpoint not found: {path}")
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    checkpoint = torch.load(path, map_location=device, weights_only=False)
    ckpt_version = str(checkpoint.get("feature_version"))
    ckpt_dim = int(checkpoint.get("feature_dim") or checkpoint.get("input_size") or 0)
    if ckpt_version != FEATURE_VERSION:
        raise ValueError(
            f"live_sim_value checkpoint feature_version={ckpt_version!r}; expected {FEATURE_VERSION!r}."
        )
    if ckpt_dim != FEATURE_DIM:
        raise ValueError(
            f"live_sim_value checkpoint feature_dim={ckpt_dim}; expected {FEATURE_DIM}."
        )
    if not bool(checkpoint.get("bounded_output")):
        raise ValueError("live_sim_value checkpoint is not marked bounded_output=true.")

    model = BoundedValueMLP(input_size=ckpt_dim, hidden_sizes=list(checkpoint.get("hidden_sizes", [256, 256]))).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    metadata = {
        "path": path,
        "model_type": str(checkpoint.get("model_type")),
        "feature_version": ckpt_version,
        "feature_dim": ckpt_dim,
        "bounded_output": True,
    }

    def _score(log: Sequence[str], step_result: Mapping[str, Any], player_side: str) -> float:
        request_view = (step_result.get("requests") or {}).get(player_side)
        features, _, _, _, _ = build_features_from_live_payload(
            log=list(log),
            room_id="branch",
            url="branch://live-sim-value",
            player=player_side,
            request_payload=dict(request_view) if isinstance(request_view, Mapping) else None,
            legal_actions=[],
        )
        x = torch.tensor(np.asarray(features, np.float32), device=device).unsqueeze(0)
        with torch.no_grad():
            return float(model(x).squeeze().detach().cpu().item())

    _score.metadata = metadata  # type: ignore[attr-defined]
    return _score


def _team_hp(team: Sequence[Any]) -> float:
    total = 0.0
    for mon in team:
        if not isinstance(mon, Mapping) or mon.get("fainted"):
            continue
        hp = mon.get("hp_ratio")
        try:
            total += max(0.0, min(1.0, float(hp if hp is not None else 1.0)))
        except (TypeError, ValueError):
            total += 1.0
    return total


def make_material_score_fn() -> ScoreFn:
    """Score the real post-step state by remaining-HP differential in ``[-1, 1]``.

    This reads the actual HP after a real sim-core step (not an approximate
    damage estimate). Hidden opponent bench members are counted at full HP using
    the known team size, so the differential reflects damage dealt/taken and
    faints caused by the branch.
    """

    def _score(log: Sequence[str], step_result: Mapping[str, Any], player_side: str) -> float:
        opponent_side = "p2" if player_side == "p1" else "p1"
        view = (step_result.get("views") or {}).get(player_side)
        if not isinstance(view, Mapping):
            return 0.0
        own_hp = _team_hp(view.get("self_team") or [])
        revealed_opponent = view.get("opponent_team") or []
        opp_hp = _team_hp(revealed_opponent)
        team_size = view.get("team_size") if isinstance(view.get("team_size"), Mapping) else {}
        opp_total = int(team_size.get(opponent_side, 6) or 6)
        hidden = max(0, opp_total - len(revealed_opponent))
        opp_hp += float(hidden)  # unrevealed bench assumed at full HP
        return float(max(-1.0, min(1.0, (own_hp - opp_hp) / 6.0)))

    return _score


# Improved exact-state scorer weights. Kept small and explainable; HP differential
# dominates, the rest are light tie-breakers. All read only the player's own
# legal view (own private team + publicly revealed opponent + public team size).
DEFAULT_STATE_SCORE_WEIGHTS: Dict[str, float] = {
    "hp": 1.0,
    "alive": 0.30,
    "active_hp": 0.25,
    "status": 0.08,
    "boost": 0.03,
    "hazard": 0.05,
}
_STATUS_WEIGHT = {"slp": 1.0, "frz": 1.0, "tox": 0.7, "par": 0.6, "brn": 0.5, "psn": 0.4}
_HAZARD_WEIGHT = {"stealthrock": 1.0, "spikes": 0.5, "toxicspikes": 0.5, "stickyweb": 0.4}
_BOOST_STATS = ("atk", "def", "spa", "spd", "spe")


def _hp_fraction(mon: Mapping[str, Any]) -> float:
    hp = mon.get("hp_ratio")
    try:
        return max(0.0, min(1.0, float(hp if hp is not None else 1.0)))
    except (TypeError, ValueError):
        return 1.0


def _alive_mons(team: Sequence[Any]) -> List[Mapping[str, Any]]:
    out: List[Mapping[str, Any]] = []
    for mon in team:
        if not isinstance(mon, Mapping) or mon.get("fainted"):
            continue
        if _hp_fraction(mon) <= 0.0:
            continue
        out.append(mon)
    return out


def _active_mon(team: Sequence[Any]) -> Optional[Mapping[str, Any]]:
    for mon in team:
        if isinstance(mon, Mapping) and mon.get("active") and not mon.get("fainted"):
            return mon
    return None


def _status_penalty(team: Sequence[Any]) -> float:
    total = 0.0
    for mon in team:
        if isinstance(mon, Mapping):
            total += _STATUS_WEIGHT.get(str(mon.get("status") or "").lower(), 0.0)
    return total


def _boost_sum(mon: Optional[Mapping[str, Any]]) -> float:
    if not isinstance(mon, Mapping):
        return 0.0
    boosts = mon.get("boosts") if isinstance(mon.get("boosts"), Mapping) else {}
    total = 0.0
    for stat in _BOOST_STATS:
        try:
            total += max(-6.0, min(6.0, float(boosts.get(stat, 0) or 0)))
        except (TypeError, ValueError):
            continue
    return total


def _hazard_cost(side_conditions: Mapping[str, Any]) -> float:
    if not isinstance(side_conditions, Mapping):
        return 0.0
    total = 0.0
    for name, weight in _HAZARD_WEIGHT.items():
        try:
            total += weight * max(0.0, float(side_conditions.get(name, 0) or 0))
        except (TypeError, ValueError):
            continue
    return total


def make_state_score_fn(weights: Optional[Mapping[str, float]] = None) -> ScoreFn:
    """Improved deterministic exact-state scorer in ``[-1, 1]``.

    Combines real post-step HP differential (dominant) with remaining-Pokemon
    count, the active matchup HP, status, active boosts, and entry hazards. Reads
    only the player's own legal view, so it leaks no hidden information (the fork
    simulation may use exact opponent data in seeded research mode; the scorer
    itself does not). Unrevealed opponent bench members are counted as alive at
    full HP using the public team size.
    """
    w = dict(DEFAULT_STATE_SCORE_WEIGHTS)
    if weights:
        w.update(weights)

    def _score(log: Sequence[str], step_result: Mapping[str, Any], player_side: str) -> float:
        opponent_side = "p2" if player_side == "p1" else "p1"
        view = (step_result.get("views") or {}).get(player_side)
        if not isinstance(view, Mapping):
            return 0.0
        own_team = view.get("self_team") or []
        revealed_opp = view.get("opponent_team") or []
        team_size = view.get("team_size") if isinstance(view.get("team_size"), Mapping) else {}
        opp_total = int(team_size.get(opponent_side, 6) or 6)
        hidden = max(0, opp_total - len(revealed_opp))

        own_alive = _alive_mons(own_team)
        opp_alive = _alive_mons(revealed_opp)
        own_hp = sum(_hp_fraction(mon) for mon in own_alive)
        opp_hp = sum(_hp_fraction(mon) for mon in opp_alive) + float(hidden)
        own_count = len(own_alive)
        opp_count = len(opp_alive) + hidden

        own_active = _active_mon(own_team)
        opp_active = _active_mon(revealed_opp)
        own_active_hp = _hp_fraction(own_active) if own_active else 0.0
        opp_active_hp = _hp_fraction(opp_active) if opp_active else 1.0

        field = view.get("field") if isinstance(view.get("field"), Mapping) else {}
        side_conditions = field.get("side_conditions") if isinstance(field.get("side_conditions"), Mapping) else {}

        hp_term = (own_hp - opp_hp) / 6.0
        alive_term = (own_count - opp_count) / 6.0
        active_hp_term = own_active_hp - opp_active_hp
        status_term = (_status_penalty(opp_alive) - _status_penalty(own_alive)) / 6.0
        boost_term = _boost_sum(own_active) - _boost_sum(opp_active)
        hazard_term = _hazard_cost(side_conditions.get("opponent") or {}) - _hazard_cost(side_conditions.get("self") or {})

        total = (
            w["hp"] * hp_term
            + w["alive"] * alive_term
            + w["active_hp"] * active_hp_term
            + w["status"] * status_term
            + w["boost"] * boost_term
            + w["hazard"] * hazard_term
        )
        return float(max(-1.0, min(1.0, total)))

    return _score
