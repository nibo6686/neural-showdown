"""Targeted Draco Meteor vs Psyshock diagnostic (Part D).

Controlled sanity check, NOT a claim about the disputed live state. It builds a
synthetic position (a special attacker holding both Draco Meteor and Psyshock,
opponent Hariyama) and compares each candidate action across the scorers the live
recommender actually uses, so we can see *why* an immediate-damage move with a
drawback could be preferred over a seemingly better tactical move.

For each action it reports: real Smogon damage (when sim-core is reachable),
type effectiveness, whether the move drops the user's own stats, the live
approximate-rollout score (the component weighted 0.75 in live), and the
action-value-ranker score. It does not hardcode any type-chart rule.

Run::

    python -m neural.action_recommender_diagnostic            # JSON to stdout
    python -m neural.action_recommender_diagnostic --markdown  # also write report
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .action_side_effects import annotate_action_side_effects
from .sim_branch_evaluator import _approximate_action_value, _damage_diagnostics


# A realistic special attacker that carries both moves in gen9 randbats.
ATTACKER = {
    "species": "Latios",
    "types": ["Dragon", "Psychic"],
    "level": 80,
}
OPPONENT = {"species": "Hariyama", "types": ["Fighting"], "level": 80}
# Latios-plausible special moveset plus a switch target.
CANDIDATE_MOVES = ["Draco Meteor", "Psyshock", "Dragon Pulse", "Aura Sphere", "Flamethrower"]
SWITCH_TARGET = "Latias"


def _build_approx_state() -> Dict[str, Any]:
    active = {
        "species": ATTACKER["species"],
        "name": ATTACKER["species"],
        "active": True,
        "hp_fraction": 1.0,
        "level": ATTACKER["level"],
        "types": list(ATTACKER["types"]),
        "moves": list(CANDIDATE_MOVES),
        "active_moves": [
            {"id": move.lower().replace(" ", ""), "name": move, "pp": 5, "maxpp": 5, "known_from_request": True}
            for move in CANDIDATE_MOVES
        ],
    }
    bench = {
        "species": SWITCH_TARGET,
        "name": SWITCH_TARGET,
        "active": False,
        "hp_fraction": 1.0,
        "level": ATTACKER["level"],
        "moves": ["Recover"],
    }
    opponent_view = {
        "species": OPPONENT["species"],
        "name": OPPONENT["species"],
        "active": True,
        "hp_fraction": 1.0,
        "level": OPPONENT["level"],
        "types": list(OPPONENT["types"]),
    }
    private_state = {"player_side": "p1", "team": [active, bench], "active_species": ATTACKER["species"]}
    return {
        "private_state": private_state,
        "tactical_state": {"own": {}, "opponent": {}, "field_effects": []},
        "trace_step": {"p1_hp_ratio": 1.0, "opponent_types": list(OPPONENT["types"])},
        "view": {"opponent_team": [opponent_view], "self_team": [active, bench]},
        "request": None,
        "opponent_belief": {"opponents": []},
        "warnings": [],
    }


def _legal_actions() -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = [
        {"kind": "move", "label": f"move: {move}", "move": move, "index": index}
        for index, move in enumerate(CANDIDATE_MOVES)
    ]
    actions.append({"kind": "switch", "label": f"switch: {SWITCH_TARGET}", "index": 8})
    return actions


def build_diagnostic() -> Dict[str, Any]:
    approx_state = _build_approx_state()
    rows: List[Dict[str, Any]] = []
    for action in _legal_actions():
        damage = _damage_diagnostics(action, approx_state)
        approx_score, approx_warnings = _approximate_action_value(action, approx_state)
        side_effects = annotate_action_side_effects(action)
        rows.append(
            {
                "label": action["label"],
                "kind": action["kind"],
                "damage_method": damage.get("damage_method"),
                "average_percent": damage.get("average_percent"),
                "min_percent": damage.get("min_percent"),
                "max_percent": damage.get("max_percent"),
                "type_effectiveness": damage.get("type_effectiveness"),
                "ko_chance": damage.get("ko_chance"),
                "self_stat_drop": side_effects.get("self_stat_drop"),
                "has_drawback": side_effects.get("has_drawback"),
                "approx_rollout_score": float(approx_score),
                "approx_warnings": approx_warnings,
            }
        )

    ranked = sorted(rows, key=lambda row: row["approx_rollout_score"], reverse=True)
    chosen = ranked[0]["label"] if ranked else None

    ranker = _action_value_ranker_ranking()

    by_label = {row["label"]: row for row in rows}
    draco = by_label.get("move: Draco Meteor", {})
    psyshock = by_label.get("move: Psyshock", {})
    return {
        "fixture": {
            "attacker": ATTACKER,
            "opponent": OPPONENT,
            "candidate_moves": CANDIDATE_MOVES,
            "switch_target": SWITCH_TARGET,
        },
        "approx_rollout_chosen": chosen,
        "approx_rollout_ranking": [row["label"] for row in ranked],
        "action_value_ranker": ranker,
        "rows": rows,
        "finding": {
            "draco_average_percent": draco.get("average_percent"),
            "psyshock_average_percent": psyshock.get("average_percent"),
            "draco_type_effectiveness": draco.get("type_effectiveness"),
            "psyshock_type_effectiveness": psyshock.get("type_effectiveness"),
            "draco_self_stat_drop": draco.get("self_stat_drop"),
            "psyshock_self_stat_drop": psyshock.get("self_stat_drop"),
            "draco_approx_score": draco.get("approx_rollout_score"),
            "psyshock_approx_score": psyshock.get("approx_rollout_score"),
            "spa_drop_represented_in_score": False,
        },
    }


def _action_value_ranker_ranking() -> Dict[str, Any]:
    """Rank the same candidates with the live action-value ranker (no rollouts).

    Returns the ranker's ordering or an unavailable marker with a reason.
    """
    try:
        import torch

        from .live_action_recommender import recommend_actions, reset_action_ranker_cache
        from .live_private_features import FEATURE_DIM
    except Exception as exc:  # pragma: no cover - import guard
        return {"available": False, "reason": f"import_failed:{type(exc).__name__}:{exc}"}

    payload = type(
        "Payload",
        (),
        {"request": {}, "legal_actions": _legal_actions()},
    )()
    private_state = {
        "player_side": "p1",
        "active_moves": [
            {"id": move.lower().replace(" ", ""), "name": move, "pp": 5, "maxpp": 5, "known_from_request": True}
            for move in CANDIDATE_MOVES
        ],
        "team": [
            {"species": ATTACKER["species"], "active": True, "hp_fraction": 1.0},
            {"species": SWITCH_TARGET, "active": False, "hp_fraction": 1.0, "moves": ["Recover"]},
        ],
    }
    try:
        reset_action_ranker_cache()
        report = recommend_actions(
            payload=payload,
            private_state=private_state,
            opponent_belief={"opponents": []},
            trajectory={"turns": []},
            public_features=np.zeros(31, dtype=np.float32),
            live_features=np.zeros(FEATURE_DIM, dtype=np.float32),
            current_value=0.0,
            value_model=None,
            value_metadata={},
            policy_loader=lambda: (None, {"warning": "missing"}),
            device=torch.device("cpu"),
        )
        reset_action_ranker_cache()
    except Exception as exc:  # pragma: no cover - runtime guard
        return {"available": False, "reason": f"recommend_failed:{type(exc).__name__}:{exc}"}

    rows = report.get("all_action_estimates") or []
    ranking = [
        {"label": row.get("label"), "ranker_score": row.get("ranker_score"), "final_score": row.get("final_score")}
        for row in sorted(rows, key=lambda r: float(r.get("final_score") or 0.0), reverse=True)
    ]
    return {
        "available": report.get("action_ranker_loaded", False),
        "method": report.get("action_recommendation_method"),
        "chosen": report.get("top_action_by_final_score"),
        "ranking": ranking,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Draco Meteor vs Psyshock recommender diagnostic")
    parser.add_argument("--markdown", action="store_true", help="also write the markdown report")
    parser.add_argument(
        "--out",
        default="artifacts/action_recommendation/draco_vs_psyshock_diagnostic.json",
        help="JSON output path",
    )
    args = parser.parse_args(argv)

    diagnostic = build_diagnostic()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(diagnostic, indent=2, default=str), encoding="utf-8")
    print(json.dumps(diagnostic, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
