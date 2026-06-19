"""Live-eval state-scorer calibration audit (Parts B / C / F).

Plays seeded sim-core games, captures per-turn snapshots (protocol log, per-side
``requests`` and ``views``), and scores every actionable state with each available
state scorer:

- ``material``           : (own_hp - opp_hp)/6 from the player's legal view
- ``live_sim_value``     : bounded tanh head trained on the serving distribution
- ``old_live_private``   : the unbounded value head that ``/evaluate`` uses today

Each state is labeled with the perspective-correct final outcome (+1 win / -1 loss
/ 0 tie). Writes a JSONL dataset and computes calibration metrics (sign accuracy,
Brier, AUC, correlation, reliability bins, perspective-flip sanity, terminal
separation, monotonicity-with-material, collapse/saturation).

No training. Inference only with existing checkpoints. Seeded and deterministic.
Scope: seeded Gen 9 Random Battle singles. Features never contain exact hidden
opponent state.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from .build_live_sim_value_dataset import _actionable, _make_client
from .build_replay_value_dataset import result_from_winner_side
from .one_turn_branch import (
    make_live_sim_value_score_fn,
    make_material_score_fn,
    make_value_score_fn,
)
from .runtime import make_battle_seed

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STATES_PATH = REPO_ROOT / "artifacts" / "live_eval_calibration" / "live_eval_calibration_states.jsonl"

RESULT_OPTIONS = {"view_players": ["p1", "p2"], "include_log_delta": True, "include_possible_roles": False}


def _play_game_capture(client, seed, controllers) -> Tuple[List[Dict[str, Any]], Optional[str], int]:
    """Play one seeded game; capture per-turn protocol, requests, AND views."""
    env_id = client.create_env(
        "gen9randombattle",
        list(seed),
        {"p1": {"controller": "external"}, "p2": {"controller": "external"}},
        timeout_sec=30,
    )
    snapshots: List[Dict[str, Any]] = []
    protocol: List[str] = []
    result = client.reset(env_id, RESULT_OPTIONS, timeout_sec=60)
    protocol.extend(result.get("log_delta") or [])
    try:
        while not result.get("terminated"):
            requests = result.get("requests") or {}
            views = result.get("views") or {}
            turn = int((result.get("info") or {}).get("turn") or 0)
            snapshots.append(
                {
                    "protocol": list(protocol),
                    "requests": {s: (dict(r) if isinstance(r, Mapping) else None) for s, r in requests.items()},
                    "views": {s: (dict(v) if isinstance(v, Mapping) else None) for s, v in views.items()},
                    "turn": turn,
                }
            )
            choices: Dict[str, str] = {}
            for side in ("p1", "p2"):
                if _actionable(requests.get(side)):
                    decision = client.agent_action(env_id, side, controllers[side], timeout_sec=20)
                    choices[side] = str(decision.get("choice") or "default")
            if not choices:
                break
            result = client.step(env_id, choices, RESULT_OPTIONS, timeout_sec=60)
            protocol.extend(result.get("log_delta") or [])
        winner = result.get("winner")
        final_turn = int((result.get("info") or {}).get("turn") or 0)
        return snapshots, winner, final_turn
    finally:
        try:
            client.close_env(env_id, timeout_sec=10)
        except Exception:
            pass


def _alive(team: Sequence[Any]) -> int:
    return sum(1 for m in team if isinstance(m, Mapping) and not m.get("fainted"))


def _team_hp(team: Sequence[Any]) -> float:
    total = 0.0
    for m in team:
        if not isinstance(m, Mapping) or m.get("fainted"):
            continue
        hp = m.get("hp_ratio")
        try:
            total += max(0.0, min(1.0, float(hp if hp is not None else 1.0)))
        except (TypeError, ValueError):
            total += 1.0
    return total


def _summarize(view: Mapping[str, Any], side: str) -> Dict[str, Any]:
    opp_side = "p2" if side == "p1" else "p1"
    own = view.get("self_team") or []
    opp_rev = view.get("opponent_team") or []
    team_size = view.get("team_size") if isinstance(view.get("team_size"), Mapping) else {}
    opp_total = int(team_size.get(opp_side, 6) or 6)
    own_active = next((m for m in own if isinstance(m, Mapping) and m.get("active")), None)
    own_status = [m.get("status") for m in own if isinstance(m, Mapping) and m.get("status")]
    hazards = view.get("hazards") if isinstance(view.get("hazards"), Mapping) else {}
    return {
        "own_hp": round(_team_hp(own), 3),
        "opp_hp_revealed": round(_team_hp(opp_rev), 3),
        "own_alive": _alive(own),
        "opp_alive_revealed": _alive(opp_rev),
        "opp_team_size": opp_total,
        "own_active_hp": round(float(own_active.get("hp_ratio") or 0.0), 3) if own_active else None,
        "own_active_status": (own_active.get("status") if own_active else None) or None,
        "own_status_count": len(own_status),
        "hazards": {k: v for k, v in hazards.items() if v},
    }


def _tags(summary: Mapping[str, Any], turn: int, turns_to_end: int, outcome: float) -> List[str]:
    tags: List[str] = []
    own, opp = summary["own_hp"], summary["opp_hp_revealed"] + max(0, summary["opp_team_size"] - summary["opp_alive_revealed"])
    diff = own - opp
    if turn <= 3:
        tags.append("early")
    if turns_to_end <= 2:
        tags.append("near_terminal")
    if diff >= 1.5:
        tags.append("winning")
    if diff <= -1.5:
        tags.append("losing")
    if summary["own_alive"] - summary["opp_alive_revealed"] >= 1:
        tags.append("material_ahead")
    if summary["own_alive"] < summary["opp_alive_revealed"]:
        tags.append("material_behind")
    if (summary["own_active_hp"] or 1.0) <= 0.25:
        tags.append("low_hp_active")
    if summary["own_status_count"] > 0:
        tags.append("own_status")
    if summary["hazards"]:
        tags.append("hazards")
    return tags


def collect(num_games: int, start_index: int, states_path: Path) -> Dict[str, Any]:
    client = _make_client()
    material = make_material_score_fn()
    live_sim = make_live_sim_value_score_fn()
    old_value = make_value_score_fn()
    scorers = {"material": material, "live_sim_value": live_sim, "old_live_private": old_value}

    rows: List[Dict[str, Any]] = []
    flip_pairs: Dict[str, List[Tuple[float, float]]] = defaultdict(list)  # scorer -> [(p1_score, p2_score)]
    skipped: Counter[str] = Counter()
    controller_counts: Counter[str] = Counter()
    games_used = 0
    started = time.perf_counter()

    try:
        for game in range(num_games):
            seed = make_battle_seed(start_index + game)
            controllers = (
                {"p1": "heuristic", "p2": "heuristic"}
                if game % 2 == 0
                else {"p1": "heuristic", "p2": "random"}
            )
            controller_counts["/".join(sorted(set(controllers.values())))] += 1
            try:
                snapshots, winner, final_turn = _play_game_capture(client, seed, controllers)
            except Exception as exc:
                skipped[f"game_error:{type(exc).__name__}"] += 1
                continue
            if winner not in ("p1", "p2", "tie"):
                skipped["no_winner_game"] += 1
                continue
            games_used += 1
            for snap in snapshots:
                step_result = {"requests": snap["requests"], "views": snap["views"]}
                per_side_scores: Dict[str, Dict[str, float]] = {}
                for side in ("p1", "p2"):
                    request = snap["requests"].get(side)
                    view = snap["views"].get(side)
                    if not _actionable(request) or not isinstance(view, Mapping):
                        skipped["non_actionable_or_no_view"] += 1
                        continue
                    outcome = result_from_winner_side(winner, perspective=side)
                    if outcome is None:
                        skipped["no_perspective_result"] += 1
                        continue
                    scores: Dict[str, float] = {}
                    for name, fn in scorers.items():
                        try:
                            scores[name] = float(fn(snap["protocol"], step_result, side))
                        except Exception as exc:
                            skipped[f"score_error:{name}:{type(exc).__name__}"] += 1
                            scores[name] = float("nan")
                    per_side_scores[side] = scores
                    summary = _summarize(view, side)
                    turns_to_end = max(0, int(final_turn) - int(snap["turn"]))
                    rows.append(
                        {
                            "game": game,
                            "seed": list(seed),
                            "turn": int(snap["turn"]),
                            "turns_to_end": turns_to_end,
                            "side": side,
                            "final_winner": winner,
                            "outcome": float(outcome),
                            "tags": _tags(summary, int(snap["turn"]), turns_to_end, float(outcome)),
                            "scores": scores,
                            "summary": summary,
                        }
                    )
                # perspective-flip pairs: same physical state scored from both sides
                if "p1" in per_side_scores and "p2" in per_side_scores:
                    for name in scorers:
                        a, b = per_side_scores["p1"][name], per_side_scores["p2"][name]
                        if not (math.isnan(a) or math.isnan(b)):
                            flip_pairs[name].append((a, b))
    finally:
        client.close()

    states_path.parent.mkdir(parents=True, exist_ok=True)
    with states_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")

    metrics = compute_metrics(rows, flip_pairs)
    return {
        "states_path": str(states_path),
        "num_games_requested": num_games,
        "num_games_used": games_used,
        "num_states": len(rows),
        "controller_matchups": dict(controller_counts),
        "skipped": dict(skipped),
        "wall_time_sec": time.perf_counter() - started,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "metrics": metrics,
        "rows": rows,
    }


# --------------------------- metrics ---------------------------

def _auc(scores: np.ndarray, labels: np.ndarray) -> Optional[float]:
    """AUC via rank statistic. labels in {0,1}."""
    pos = labels == 1
    neg = labels == 0
    n_pos, n_neg = int(pos.sum()), int(neg.sum())
    if n_pos == 0 or n_neg == 0:
        return None
    order = scores.argsort()
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, len(scores) + 1)
    # average ranks for ties
    _, inv, counts = np.unique(scores, return_inverse=True, return_counts=True)
    sum_ranks = np.zeros(len(counts))
    np.add.at(sum_ranks, inv, ranks)
    avg = sum_ranks / counts
    ranks = avg[inv]
    auc = (ranks[pos].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def _pearson(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    if len(a) < 2 or a.std() == 0 or b.std() == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _spearman(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    if len(a) < 2:
        return None
    ar = np.argsort(np.argsort(a)).astype(np.float64)
    br = np.argsort(np.argsort(b)).astype(np.float64)
    return _pearson(ar, br)


def _reliability(prob: np.ndarray, win: np.ndarray, bins: int = 10) -> List[Dict[str, Any]]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    table = []
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (prob >= lo) & (prob < hi if i < bins - 1 else prob <= hi)
        n = int(mask.sum())
        if n == 0:
            table.append({"bin": f"[{lo:.1f},{hi:.1f})", "n": 0, "pred": None, "empirical": None})
        else:
            table.append(
                {
                    "bin": f"[{lo:.1f},{hi:.1f})",
                    "n": n,
                    "pred": round(float(prob[mask].mean()), 3),
                    "empirical": round(float(win[mask].mean()), 3),
                }
            )
    return table


def compute_metrics(rows: List[Dict[str, Any]], flip_pairs: Mapping[str, List[Tuple[float, float]]]) -> Dict[str, Any]:
    seen: Dict[str, None] = {}
    for r in rows:
        for k in r["scores"]:
            seen.setdefault(k, None)
    scorer_names = list(seen)
    out: Dict[str, Any] = {"per_scorer": {}, "n_states": len(rows)}
    outcomes = np.array([r["outcome"] for r in rows], dtype=np.float64)
    material_scores = np.array([r["scores"].get("material", np.nan) for r in rows], dtype=np.float64)

    for name in scorer_names:
        s = np.array([r["scores"].get(name, np.nan) for r in rows], dtype=np.float64)
        valid = ~np.isnan(s)
        sv, ov = s[valid], outcomes[valid]
        nontie = ov != 0
        sign_acc = float((np.sign(sv[nontie]) == np.sign(ov[nontie])).mean()) if nontie.any() else None
        win = (ov > 0).astype(np.float64)
        prob = np.clip((sv + 1.0) / 2.0, 0.0, 1.0)
        brier = float(np.mean((prob[nontie] - win[nontie]) ** 2)) if nontie.any() else None
        auc = _auc(sv[nontie], win[nontie]) if nontie.any() else None
        corr = _pearson(sv, ov)
        mat_v = material_scores[valid]  # material aligned to this scorer's valid subspace
        mat_ok = ~np.isnan(mat_v)
        mono = _spearman(sv[mat_ok], mat_v[mat_ok]) if mat_ok.any() else None
        flips = flip_pairs.get(name, [])
        if flips:
            fa = np.array([p[0] for p in flips])
            fb = np.array([p[1] for p in flips])
            flip_sum_abs = float(np.mean(np.abs(fa + fb)))  # ~0 if perfectly anti-symmetric
            flip_corr = _pearson(fa, -fb)
        else:
            flip_sum_abs, flip_corr = None, None
        near_full = np.array([("near_terminal" in r["tags"]) for r in rows], dtype=bool)
        near = near_full[valid]
        term_win = sv[np.logical_and(near, ov > 0)]
        term_loss = sv[np.logical_and(near, ov < 0)]
        out["per_scorer"][name] = {
            "n_valid": int(valid.sum()),
            "sign_accuracy": None if sign_acc is None else round(sign_acc, 4),
            "brier": None if brier is None else round(brier, 4),
            "auc": None if auc is None else round(auc, 4),
            "corr_with_outcome": None if corr is None else round(corr, 4),
            "spearman_with_material": None if mono is None else round(mono, 4),
            "mean_winning_score": round(float(sv[ov > 0].mean()), 4) if (ov > 0).any() else None,
            "mean_losing_score": round(float(sv[ov < 0].mean()), 4) if (ov < 0).any() else None,
            "mean_score": round(float(sv.mean()), 4),
            "std_score": round(float(sv.std()), 4),
            "frac_saturated_gt_0p9": round(float((np.abs(sv) > 0.9).mean()), 4),
            "perspective_flip_mean_abs_sum": None if flip_sum_abs is None else round(flip_sum_abs, 4),
            "perspective_flip_corr": None if flip_corr is None else round(flip_corr, 4),
            "near_terminal_mean_win": round(float(term_win.mean()), 4) if term_win.size else None,
            "near_terminal_mean_loss": round(float(term_loss.mean()), 4) if term_loss.size else None,
            "reliability": _reliability(prob[nontie], win[nontie]) if nontie.any() else [],
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Live-eval state-scorer calibration audit.")
    parser.add_argument("--num-games", type=int, default=24)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--states-path", type=Path, default=DEFAULT_STATES_PATH)
    parser.add_argument("--metrics-path", type=Path, default=None)
    args = parser.parse_args()

    report = collect(args.num_games, args.start_index, args.states_path)
    report.pop("rows", None)
    metrics_path = args.metrics_path or args.states_path.with_name("live_eval_calibration_metrics.json")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"states": report["num_states"], "games_used": report["num_games_used"], "metrics_path": str(metrics_path)}))


if __name__ == "__main__":
    main()
