"""State counterfactual sensitivity audit (Parts B / C / D).

Research question: if two battle states are identical except for one controlled
public variable (a stat stage), do the scorers evaluate them in the expected
order? This tests whether the scorers/models *see and use* stat-stage information,
without any move-specific or type-chart rule.

Each scenario mutates exactly one thing relative to a fixed neutral base state (a
special-attacker active vs a single opponent, both at full HP). For each scenario
two equivalent representations are built so every scorer can be evaluated on the
same controlled change:

* a sim-core-style ``views`` payload with per-mon ``boosts`` — for the view-based
  ``material`` and ``state`` branch-leaf scorers;
* a protocol log with ``-boost`` / ``-unboost`` lines, featurized through the live
  serving path — for the feature/model scorers (``live_sim_value``, the old
  ``live_private`` value head, and the action-value ranker's state half).

The states are **synthetic** (hand-built, not produced by a real move) on purpose:
the goal is scorer sensitivity to a single isolated variable, not move realism.
The Draco/Psyshock *simulator-derived* transition is a separate report (Part E).

No training. Inference only with existing checkpoints. Live defaults unchanged.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

BASE_OWN_SPECIES = "Latios"  # special attacker; SpA is its offensive stat
BASE_OPP_SPECIES = "Hariyama"


@dataclass(frozen=True)
class Scenario:
    name: str
    own_boosts: Dict[str, int]
    opp_boosts: Dict[str, int]
    changed_fields: str
    expected: str  # human-readable expected ordering vs neutral
    expected_sign: Optional[int]  # +1 better, -1 worse, 0 ~equal, None diagnostic
    category: str  # "clear" | "nuanced" | "diagnostic"


SCENARIOS: List[Scenario] = [
    Scenario("neutral", {}, {}, "none (baseline)", "baseline", 0, "clear"),
    Scenario("own_spa_-2", {"spa": -2}, {}, "own active SpA -2",
             "<= neutral for a special attacker (Draco-like cost)", -1, "nuanced"),
    Scenario("own_spa_-6", {"spa": -6}, {}, "own active SpA -6",
             "worse than neutral for a special attacker", -1, "clear"),
    Scenario("own_all_-6", {"atk": -6, "def": -6, "spa": -6, "spd": -6, "spe": -6, "accuracy": -6, "evasion": -6}, {},
             "own active all stats -6", "clearly worse than neutral", -1, "clear"),
    Scenario("own_curse_like", {"atk": 1, "def": 1, "spe": -1}, {},
             "own Atk+1 / Def+1 / Spe-1 (Curse-like)",
             "net positive; should not be auto-worse than Bulk-Up-like only for the Speed drop",
             None, "diagnostic"),
    Scenario("own_bulkup_like", {"atk": 1, "def": 1}, {},
             "own Atk+1 / Def+1 (Bulk-Up-like)", ">= neutral (useful setup)", 1, "nuanced"),
    Scenario("opp_def_-2", {}, {"def": -2}, "opponent active Def -2",
             "better than neutral if relevant", 1, "nuanced"),
    Scenario("opp_spd_-2", {}, {"spd": -2}, "opponent active SpD -2",
             "better than neutral for a special attacker", 1, "nuanced"),
    Scenario("own_spe_-6", {"spe": -6}, {}, "own active Spe -6 only",
             "interpret cautiously; not necessarily catastrophic unless speed matters", None, "diagnostic"),
]


def _boost_lines(side_ident: str, boosts: Dict[str, int]) -> List[str]:
    lines: List[str] = []
    for stat, stages in boosts.items():
        if stages == 0:
            continue
        command = "-boost" if stages > 0 else "-unboost"
        lines.append(f"|{command}|{side_ident}|{stat}|{abs(int(stages))}")
    return lines


def build_protocol_log(scenario: Scenario) -> List[str]:
    own = f"p1a: {BASE_OWN_SPECIES}"
    opp = f"p2a: {BASE_OPP_SPECIES}"
    return [
        "|start",
        f"|switch|{own}|{BASE_OWN_SPECIES}, L80|100/100",
        f"|switch|{opp}|{BASE_OPP_SPECIES}, L80|100/100",
        *_boost_lines(own, scenario.own_boosts),
        *_boost_lines(opp, scenario.opp_boosts),
        "|turn|1",
    ]


def build_view_step_result(scenario: Scenario, *, perspective: str = "p1") -> Dict[str, Any]:
    """A sim-core-style step_result with one revealed mon per side at full HP.

    Boosts are placed on the active mons. From p1's perspective ``own`` is self;
    when perspective is p2 the same physical boosts are mirrored so the *same
    physical state* is scored from the other side (perspective sanity).
    """
    own_boosts = scenario.own_boosts if perspective == "p1" else scenario.opp_boosts
    opp_boosts = scenario.opp_boosts if perspective == "p1" else scenario.own_boosts
    own_species = BASE_OWN_SPECIES if perspective == "p1" else BASE_OPP_SPECIES
    opp_species = BASE_OPP_SPECIES if perspective == "p1" else BASE_OWN_SPECIES

    def _team(active_species: str, active_boosts: Dict[str, int]) -> List[Dict[str, Any]]:
        # Balanced 6v6 at full HP so material/alive terms sit at neutral and the
        # only varying input is the active mon's boosts (the controlled variable).
        team = [{"active": True, "species": active_species, "hp_ratio": 1.0, "boosts": dict(active_boosts), "fainted": False}]
        for i in range(5):
            team.append({"active": False, "species": f"Bench{i+1}", "hp_ratio": 1.0, "boosts": {}, "fainted": False})
        return team

    view = {
        "self_team": _team(own_species, own_boosts),
        "opponent_team": _team(opp_species, opp_boosts),
        "team_size": {"p1": 6, "p2": 6},
        "field": {"side_conditions": {"self": {}, "opponent": {}}},
    }
    return {"views": {perspective: view}, "requests": {perspective: None}}


# ----------------------------- scorers -----------------------------

_MODELS: Dict[str, Any] = {}


def _load_models():
    if _MODELS:
        return _MODELS
    import torch

    from .live_eval_server import (
        DEVICE,
        load_live_sim_value_model_once,
        load_value_model_once,
    )
    from .live_action_recommender import load_action_ranker_once
    from .action_features import ACTION_FEATURE_DIM, build_action_feature_vector

    _MODELS["torch"] = torch
    _MODELS["device"] = DEVICE
    _MODELS["ACTION_FEATURE_DIM"] = ACTION_FEATURE_DIM
    _MODELS["build_action_feature_vector"] = build_action_feature_vector
    try:
        _MODELS["live_sim"] = load_live_sim_value_model_once()
    except Exception as exc:  # pragma: no cover - missing checkpoint guard
        _MODELS["live_sim"] = (None, {"error": f"{type(exc).__name__}: {exc}"})
    try:
        _MODELS["old_value"] = load_value_model_once()
    except Exception as exc:  # pragma: no cover
        _MODELS["old_value"] = (None, {"error": f"{type(exc).__name__}: {exc}"})
    try:
        _MODELS["ranker"] = load_action_ranker_once(device=DEVICE)
    except Exception as exc:  # pragma: no cover
        _MODELS["ranker"] = (None, {"error": f"{type(exc).__name__}: {exc}"})
    return _MODELS


def _model_value(output: Any) -> float:
    if isinstance(output, tuple):
        tensor = output[1]
    elif isinstance(output, dict):
        tensor = output.get("value") or output.get("values")
    else:
        tensor = output
    return float(tensor.squeeze().detach().cpu().item())


def _score_feature_models(features: np.ndarray) -> Dict[str, Any]:
    models = _load_models()
    torch = models["torch"]
    device = models["device"]
    out: Dict[str, Any] = {}

    live_sim_model, live_sim_meta = models["live_sim"]
    if live_sim_model is not None:
        x = torch.tensor(np.asarray(features, np.float32), device=device).unsqueeze(0)
        with torch.no_grad():
            v = float(live_sim_model(x).squeeze().detach().cpu().item())
        out["live_sim_value"] = {"score": v, "win_prob": max(0.0, min(1.0, (v + 1.0) / 2.0)), "bounded": True}
    else:
        out["live_sim_value"] = {"unavailable": live_sim_meta.get("error")}

    old_model, old_meta = models["old_value"]
    if old_model is not None and not old_meta.get("error"):
        feat = np.asarray(features, np.float32)
        input_size = int(old_meta.get("input_size", feat.shape[0]))
        if feat.shape[0] != input_size:
            feat = feat[:input_size] if feat.shape[0] > input_size else np.pad(feat, (0, input_size - feat.shape[0]))
        x = torch.tensor(feat, device=device).unsqueeze(0)
        with torch.no_grad():
            v = _model_value(old_model(x))
        out["old_live_private"] = {"score": v, "win_prob": max(0.0, min(1.0, (v + 1.0) / 2.0)), "bounded": False}
    else:
        out["old_live_private"] = {"unavailable": (old_meta or {}).get("error") or "unavailable"}
    return out


def _score_ranker(features: np.ndarray) -> Dict[str, Any]:
    models = _load_models()
    torch = models["torch"]
    device = models["device"]
    ranker_model, ranker_meta = models["ranker"]
    if ranker_model is None:
        return {"unavailable": (ranker_meta or {}).get("warning") or (ranker_meta or {}).get("error") or "unavailable"}
    build_action_feature_vector = models["build_action_feature_vector"]
    action_dim = int(ranker_meta.get("action_dim", models["ACTION_FEATURE_DIM"]))
    state_dim = int(ranker_meta.get("state_dim", features.shape[0]))
    # Hold the action fixed (a generic special move) so only the STATE varies.
    action = {"kind": "move", "label": "move: Dragon Pulse", "index": 0}
    private = {"active_moves": [{"id": "dragonpulse", "name": "Dragon Pulse", "pp": 5, "maxpp": 5}],
               "team": [{"species": BASE_OWN_SPECIES, "active": True, "hp_fraction": 1.0}]}
    action_features = build_action_feature_vector(action, private).astype(np.float32)
    if action_features.shape[0] != action_dim:
        action_features = action_features[:action_dim] if action_features.shape[0] > action_dim else np.pad(action_features, (0, action_dim - action_features.shape[0]))
    state_part = np.asarray(features, np.float32)
    if state_part.shape[0] != state_dim:
        state_part = state_part[:state_dim] if state_part.shape[0] > state_dim else np.pad(state_part, (0, state_dim - state_part.shape[0]))
    x = torch.from_numpy(np.concatenate([state_part, action_features]).astype(np.float32)).to(device).unsqueeze(0)
    with torch.no_grad():
        score = float(ranker_model(x).squeeze().detach().cpu().item())
    return {"score": score, "fixed_action": action["label"], "note": "state varied, action held fixed"}


def _features_for(scenario: Scenario, *, feature_version: Optional[str] = None) -> np.ndarray:
    from .live_private_features import FEATURE_VERSION, build_features_from_live_payload

    features, _, _, _, _ = build_features_from_live_payload(
        log=build_protocol_log(scenario),
        room_id="counterfactual",
        url="cf://state",
        player="p1",
        request_payload=None,
        legal_actions=[],
        feature_version=feature_version or FEATURE_VERSION,
    )
    return features


def _changed_features(
    features: np.ndarray,
    neutral: np.ndarray,
    feature_names: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    from .live_private_features import FEATURE_NAMES

    names = feature_names or FEATURE_NAMES
    idx = np.where(~np.isclose(features, neutral, atol=1e-6))[0]
    return [
        {"name": names[i], "neutral": round(float(neutral[i]), 4), "value": round(float(features[i]), 4)}
        for i in idx
    ]


def build_current_typing_diagnostic() -> Dict[str, Any]:
    from .live_private_features import (
        FEATURE_NAMES,
        FEATURE_NAMES_V3,
        FEATURE_VERSION,
        FEATURE_VERSION_V3,
        build_features_from_live_payload,
    )

    base_log = [
        "|start",
        "|switch|p1a: Exeggutor|Exeggutor-Alola, L89|100/100",
        "|switch|p2a: Charizard|Charizard, L80|100/100",
        "|turn|1",
    ]
    soaked_log = [
        *base_log[:-1],
        "|-start|p2a: Charizard|typechange|Water|[from] move: Soak",
        "|turn|1",
    ]

    def _build(log: List[str], version: str):
        return build_features_from_live_payload(
            log=log,
            room_id="counterfactual-soak",
            url="cf://soak",
            player="p1",
            request_payload=None,
            legal_actions=[],
            feature_version=version,
        )

    base_v2, _, _, _, _ = _build(base_log, FEATURE_VERSION)
    soaked_v2, _, _, _, _ = _build(soaked_log, FEATURE_VERSION)
    base_v3, base_debug, _, _, _ = _build(base_log, FEATURE_VERSION_V3)
    soaked_v3, soaked_debug, _, _, _ = _build(soaked_log, FEATURE_VERSION_V3)
    return {
        "synthetic": True,
        "mutation": "opponent Charizard current types Fire/Flying -> Water via public typechange/Soak protocol",
        "v2_changes": _changed_features(soaked_v2, base_v2, FEATURE_NAMES),
        "v3_changes": _changed_features(soaked_v3, base_v3, FEATURE_NAMES_V3),
        "v3_base_type_fire": float(soaked_v3[FEATURE_NAMES_V3.index("opponent_active_base_type_fire")]),
        "v3_base_type_flying": float(soaked_v3[FEATURE_NAMES_V3.index("opponent_active_base_type_flying")]),
        "v3_current_type_water": float(soaked_v3[FEATURE_NAMES_V3.index("opponent_active_current_type_water")]),
        "v3_current_type_fire": float(soaked_v3[FEATURE_NAMES_V3.index("opponent_active_current_type_fire")]),
        "v3_current_source_protocol_typechange": float(
            soaked_v3[FEATURE_NAMES_V3.index("opponent_active_current_type_source_protocol_typechange")]
        ),
        "base_tactical_snapshot": base_debug.get("tactical_snapshot"),
        "soaked_tactical_snapshot": soaked_debug.get("tactical_snapshot"),
    }


def evaluate() -> Dict[str, Any]:
    from .live_private_features import FEATURE_NAMES_V3, FEATURE_VERSION_V3
    from .one_turn_branch import make_material_score_fn, make_state_score_fn

    material = make_material_score_fn()
    state = make_state_score_fn()

    neutral_features = _features_for(SCENARIOS[0])
    neutral_v3_features = _features_for(SCENARIOS[0], feature_version=FEATURE_VERSION_V3)
    rows: List[Dict[str, Any]] = []
    for scenario in SCENARIOS:
        view_step = build_view_step_result(scenario, perspective="p1")
        features = _features_for(scenario)
        v3_features = _features_for(scenario, feature_version=FEATURE_VERSION_V3)
        row: Dict[str, Any] = {
            "scenario": scenario.name,
            "changed_fields": scenario.changed_fields,
            "own_boosts": scenario.own_boosts,
            "opp_boosts": scenario.opp_boosts,
            "expected": scenario.expected,
            "expected_sign": scenario.expected_sign,
            "category": scenario.category,
            "perspective": "p1",
            "synthetic": True,
            "scores": {
                "material": {"score": round(float(material([], view_step, "p1")), 6)},
                "state": {"score": round(float(state([], view_step, "p1")), 6)},
                **_score_feature_models(features),
                "action_value_ranker": _score_ranker(features),
            },
            "feature_changes_vs_neutral": _changed_features(features, neutral_features),
            "v3_feature_changes_vs_neutral": _changed_features(
                v3_features,
                neutral_v3_features,
                FEATURE_NAMES_V3,
            ),
        }
        rows.append(row)

    # Perspective sanity: score the SAME physical state from p1 and p2 for two scenarios.
    flip: List[Dict[str, Any]] = []
    for scenario in (SCENARIOS[0], SCENARIOS[2]):  # neutral and own_spa_-6
        p1_state = build_view_step_result(scenario, perspective="p1")
        p2_state = build_view_step_result(scenario, perspective="p2")
        flip.append(
            {
                "scenario": scenario.name,
                "material_p1": round(float(material([], p1_state, "p1")), 6),
                "material_p2": round(float(material([], p2_state, "p2")), 6),
                "state_p1": round(float(state([], p1_state, "p1")), 6),
                "state_p2": round(float(state([], p2_state, "p2")), 6),
            }
        )

    return {
        "rows": rows,
        "perspective_flip": flip,
        "current_typing": build_current_typing_diagnostic(),
        "base": {"own": BASE_OWN_SPECIES, "opp": BASE_OPP_SPECIES},
    }


def _active_boosts(step_result: Dict[str, Any], side: str) -> Dict[str, int]:
    view = (step_result.get("views") or {}).get(side) or {}
    active = next((m for m in (view.get("self_team") or []) if isinstance(m, dict) and m.get("active")), {})
    return {k: int(v) for k, v in (active.get("boosts") or {}).items() if int(v) != 0}


def _opp_active_hp(step_result: Dict[str, Any], side: str) -> Optional[float]:
    view = (step_result.get("views") or {}).get(side) or {}
    active = next((m for m in (view.get("opponent_team") or []) if isinstance(m, dict) and m.get("active")), {})
    hp = active.get("hp_ratio")
    return float(hp) if hp is not None else None


def _active_mon(step_result: Dict[str, Any], side: str, team_key: str) -> Dict[str, Any]:
    view = (step_result.get("views") or {}).get(side) or {}
    return next(
        (m for m in (view.get(team_key) or []) if isinstance(m, dict) and m.get("active")),
        {},
    )


def _canonical_protocol(step_result: Dict[str, Any], side: str = "p1") -> List[str]:
    """Build a live-style public snapshot from a simulator-derived view.

    sim-core's player view is authoritative for the resulting HP and boosts. A
    compact canonical log lets the serving featurizer score that state without
    depending on the spectator log-delta delivery timing.
    """
    own_side = side
    opp_side = "p2" if side == "p1" else "p1"
    own = _active_mon(step_result, side, "self_team")
    opp = _active_mon(step_result, side, "opponent_team")

    def _species(mon: Dict[str, Any], fallback: str) -> str:
        return str(mon.get("species") or mon.get("name") or fallback)

    def _condition(mon: Dict[str, Any]) -> str:
        hp = mon.get("hp_ratio")
        try:
            return f"{max(0, min(100, round(float(hp) * 100)))}/100"
        except (TypeError, ValueError):
            return "100/100"

    own_species = _species(own, BASE_OWN_SPECIES)
    opp_species = _species(opp, BASE_OPP_SPECIES)
    own_ident = f"{own_side}a: {own.get('name') or own_species}"
    opp_ident = f"{opp_side}a: {opp.get('name') or opp_species}"
    lines = [
        "|start",
        f"|switch|{own_ident}|{own_species}|{_condition(own)}",
        f"|switch|{opp_ident}|{opp_species}|{_condition(opp)}",
    ]
    lines.extend(_boost_lines(own_ident, _active_boosts(step_result, side)))
    opp_boosts = {
        key: int(value)
        for key, value in (opp.get("boosts") or {}).items()
        if int(value) != 0
    }
    lines.extend(_boost_lines(opp_ident, opp_boosts))
    lines.append(f"|turn|{int(((step_result.get('info') or {}).get('turn') or 1))}")
    return lines


def _without_active_boosts(step_result: Dict[str, Any], side: str = "p1") -> Dict[str, Any]:
    result = copy.deepcopy(step_result)
    active = _active_mon(result, side, "self_team")
    active["boosts"] = {}
    return result


def _choice_for(request: Dict[str, Any], needle: str) -> Optional[str]:
    legal = (request or {}).get("legal_actions") or {}
    for action in legal.get("actions") or []:
        if not isinstance(action, dict):
            continue
        label = str(action.get("label") or "")
        if needle.lower() in label.lower() and not label.lower().startswith("move_tera"):
            return action.get("choice")
    return None


def build_transition_diagnostic(
    seed_index: int = 1,
    drop_move: str = "Draco Meteor",
    clean_move: str = "Flamethrower",
) -> Dict[str, Any]:
    """Simulator-derived transition: step a self-stat-drop move vs a clean move.

    Forks the same seeded pre-state, steps each candidate (with a fixed opponent
    default reply), and confirms whether the post-state actually contains the
    drop, then scores pre/post with material, state, and live_sim_value.
    """
    import json
    import os

    from .env_client import SimCoreClient
    from .runtime import make_battle_seed
    from .one_turn_branch import make_material_score_fn, make_state_score_fn, make_live_sim_value_score_fn
    from .action_side_effects import move_side_effects

    cmd = json.loads(os.environ["NEURAL_SIM_CORE_COMMAND_JSON"])
    cwd = os.environ["NEURAL_SIM_CORE_CWD"]
    opts = {"view_players": ["p1", "p2"], "include_log_delta": True}
    material = make_material_score_fn()
    state = make_state_score_fn()
    try:
        live_sim = make_live_sim_value_score_fn()
        live_sim_available = True
    except Exception as exc:  # pragma: no cover - checkpoint guard
        live_sim = None
        live_sim_available = False
        live_sim_error = f"{type(exc).__name__}: {exc}"
    seed = list(make_battle_seed(seed_index))

    def _score(step_result: Dict[str, Any]) -> Dict[str, Any]:
        protocol = _canonical_protocol(step_result, "p1")
        scores = {
            "material": round(float(material(protocol, step_result, "p1")), 6),
            "state": round(float(state(protocol, step_result, "p1")), 6),
        }
        if live_sim is not None:
            scores["live_sim_value"] = round(float(live_sim(protocol, step_result, "p1")), 6)
        else:
            scores["live_sim_value"] = None
        return scores

    def _fork_and_step(choice: str) -> Dict[str, Any]:
        env = client.create_env("gen9randombattle", seed, {"p1": {"controller": "external"}, "p2": {"controller": "external"}}, timeout_sec=30)
        try:
            r = client.reset(env, opts, timeout_sec=60)
            r = client.step(env, {"p1": choice, "p2": "default"}, opts, timeout_sec=60)
            return {
                "scores": _score(r),
                "own_active_boosts": _active_boosts(r, "p1"),
                "own_active_species": _active_mon(r, "p1", "self_team").get("species"),
                "own_active_hp": _active_mon(r, "p1", "self_team").get("hp_ratio"),
                "opp_active_species": _active_mon(r, "p1", "opponent_team").get("species"),
                "opp_active_hp": _opp_active_hp(r, "p1"),
                "terminated": bool(r.get("terminated")),
                "_step_result": r,
            }
        finally:
            try:
                client.close_env(env, timeout_sec=10)
            except Exception:
                pass

    result: Dict[str, Any] = {
        "seed_index": seed_index,
        "drop_move": drop_move,
        "clean_move": clean_move,
        "live_sim_available": live_sim_available,
    }
    if not live_sim_available:
        result["live_sim_error"] = live_sim_error

    with SimCoreClient(cmd, cwd) as client:
        env = client.create_env("gen9randombattle", seed, {"p1": {"controller": "external"}, "p2": {"controller": "external"}}, timeout_sec=30)
        try:
            pre = client.reset(env, opts, timeout_sec=60)
            p1_request = (pre.get("requests") or {}).get("p1") or {}
            drop_choice = _choice_for(p1_request, drop_move)
            clean_choice = _choice_for(p1_request, clean_move)
            result["pre_state"] = {
                "scores": _score(pre),
                "own_active_boosts": _active_boosts(pre, "p1"),
                "own_active_species": _active_mon(pre, "p1", "self_team").get("species"),
                "own_active_hp": _active_mon(pre, "p1", "self_team").get("hp_ratio"),
                "opp_active_species": _active_mon(pre, "p1", "opponent_team").get("species"),
                "opp_active_hp": _opp_active_hp(pre, "p1"),
                "drop_choice": drop_choice,
                "clean_choice": clean_choice,
            }
        finally:
            try:
                client.close_env(env, timeout_sec=10)
            except Exception:
                pass

        if not drop_choice:
            result["error"] = f"{drop_move} not legal at seed {seed_index} turn 0"
            return result
        result["drop_side_effects"] = move_side_effects(drop_move)
        result["clean_side_effects"] = move_side_effects(clean_move)
        result["post_drop"] = _fork_and_step(drop_choice)
        drop_without_stage = _without_active_boosts(result["post_drop"].pop("_step_result"))
        result["post_drop_without_stage"] = {
            "scores": _score(drop_without_stage),
            "own_active_boosts": _active_boosts(drop_without_stage, "p1"),
            "note": "same simulator-derived HP/state with only the active boosts cleared",
        }
        if clean_choice:
            result["post_clean"] = _fork_and_step(clean_choice)
            result["post_clean"].pop("_step_result", None)

    # Deltas
    pre_scores = result["pre_state"]["scores"]
    drop_scores = result["post_drop"]["scores"]
    result["deltas"] = {
        "drop": {k: (None if drop_scores.get(k) is None or pre_scores.get(k) is None else round(drop_scores[k] - pre_scores[k], 6)) for k in pre_scores},
        "drop_opp_hp_dealt": (None if result["post_drop"]["opp_active_hp"] is None or result["pre_state"]["opp_active_hp"] is None
                              else round(result["pre_state"]["opp_active_hp"] - result["post_drop"]["opp_active_hp"], 6)),
        "drop_post_has_spa_drop": result["post_drop"]["own_active_boosts"].get("spa", 0) < 0,
        "isolated_drop_stage_effect": {
            k: (
                None
                if drop_scores.get(k) is None
                or result["post_drop_without_stage"]["scores"].get(k) is None
                else round(drop_scores[k] - result["post_drop_without_stage"]["scores"][k], 6)
            )
            for k in pre_scores
        },
    }
    if "post_clean" in result:
        clean_scores = result["post_clean"]["scores"]
        result["deltas"]["clean"] = {k: (None if clean_scores.get(k) is None or pre_scores.get(k) is None else round(clean_scores[k] - pre_scores[k], 6)) for k in pre_scores}
        result["deltas"]["clean_opp_hp_dealt"] = (None if result["post_clean"]["opp_active_hp"] is None or result["pre_state"]["opp_active_hp"] is None
                                                  else round(result["pre_state"]["opp_active_hp"] - result["post_clean"]["opp_active_hp"], 6))
        result["deltas"]["clean_post_has_spa_drop"] = result["post_clean"]["own_active_boosts"].get("spa", 0) < 0
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="State counterfactual sensitivity audit")
    parser.add_argument("--out", default="artifacts/action_recommendation/state_counterfactual_scores.jsonl")
    args = parser.parse_args(argv)
    report = evaluate()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for row in report["rows"]:
            handle.write(json.dumps(row, default=str) + "\n")
        handle.write(json.dumps({"perspective_flip": report["perspective_flip"]}, default=str) + "\n")
        handle.write(json.dumps({"current_typing": report["current_typing"]}, default=str) + "\n")
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
