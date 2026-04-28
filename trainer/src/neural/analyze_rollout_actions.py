import argparse
import json
from pathlib import Path
from typing import Any, Dict

from .parse_replay_logs import parse_protocol_log
from .sim_branch_evaluator import evaluate_actions
from .value_features import action_labels_from_request, select_trace_step, view_request_from_step
from .tactical_state import TacticalStateTracker
from .live_opponent_beliefs import build_opponent_beliefs
from .live_private_state import extract_private_side_state


def _species_types(species: Any) -> list[str]:
    try:
        from .tactical_state import _species_types as tactical_species_types

        return tactical_species_types(species)
    except Exception:
        return []


def _side_condition(side_state: Dict[str, Any]) -> str:
    hp = side_state.get("active_hp")
    max_hp = side_state.get("active_max_hp")
    status = side_state.get("active_status")
    if hp is not None and max_hp:
        condition = f"{int(float(hp))}/{int(float(max_hp))}"
    else:
        condition = "100/100"
    if status:
        condition = f"{condition} {status}"
    return condition


def _pokemon_for_view(species: str, side_state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "slot": 0,
        "ident": side_state.get("active_ident") or species,
        "name": species,
        "species": species,
        "details": f"{species}, L80",
        "active": True,
        "fainted": bool(side_state.get("active_fainted")),
        "hp_text": _side_condition(side_state).split(" ", 1)[0],
        "hp_ratio": side_state.get("active_hp_fraction") if side_state.get("active_hp_fraction") is not None else 1.0,
        "hp_fraction": side_state.get("active_hp_fraction") if side_state.get("active_hp_fraction") is not None else 1.0,
        "status": side_state.get("active_status"),
        "level": 80,
        "item": None,
        "ability": None,
        "base_ability": None,
        "moves": [],
        "revealed_moves": [],
        "types": _species_types(species),
        "tera_type": side_state.get("active_tera_type"),
        "terastallized": bool(side_state.get("tera_used")),
        "stats": {},
        "boosts": dict(side_state.get("boosts") or {}),
        "volatiles": list(side_state.get("volatiles") or []),
        "possible_roles": [],
        "possible_moves": [],
        "possible_abilities": [],
        "possible_tera_types": [],
    }


def load_trace(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in (".json", ".jsonl"):
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {"protocol_log": []}
        except Exception:
            # fallback to raw log parsing
            return parse_protocol_log(text.splitlines())
    return parse_protocol_log(text.splitlines())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-path", required=True)
    parser.add_argument("--side", default="p1")
    parser.add_argument("--step-index", type=int, default=0)
    parser.add_argument("--turn", type=int, default=None, help="Battle turn (preferred over step-index for protocol-prefix fallback)")
    parser.add_argument("--rollout-mode", choices=("auto", "exact", "approximate"), default="auto")
    args = parser.parse_args()
    path = Path(args.replay_path)
    if not path.exists():
        raise SystemExit(f"Replay path not found: {path}")
    trace = load_trace(path)

    # Try to select an explicit decision step from the trace.
    try:
        step, _, _ = select_trace_step(trace, args.step_index)
        _, request = view_request_from_step(trace, step)
        legal_actions = action_labels_from_request(request)
        if not legal_actions and isinstance(step.get("legal_actions"), list):
            legal_actions = [action for action in step.get("legal_actions") if isinstance(action, dict)]

        payload = {"trace": trace}
        results = evaluate_actions(
            payload,
            args.side,
            legal_actions,
            "uniform",
            {"rollouts_per_action": 8, "rollout_mode": args.rollout_mode},
        )
    except ValueError:
        # No decision steps present in this public replay. If approximate mode requested,
        # attempt to construct a lightweight pseudo-step using the protocol prefix
        # and randbats reconstruction helpers. Otherwise fail clearly.
        if args.rollout_mode != "approximate":
            raise SystemExit("Trace does not contain any decision steps and exact mode was requested.")

        protocol = trace.get("protocol_log") if isinstance(trace.get("protocol_log"), list) else []
        # Prefer --turn over --step-index for protocol-prefix fallback
        requested_turn = int(args.turn) if args.turn is not None else int(args.step_index or 0)
        if requested_turn <= 0:
            requested_turn = 1

        # Build protocol prefix up to requested_turn using TacticalStateTracker to locate turns
        tracker = TacticalStateTracker()
        prefix_lines = []
        for line in protocol:
            prefix_lines.append(line)
            tracker.consume_line(line)
            if tracker.turn >= requested_turn:
                break

        # Derive active species and tactical hints from tracker
        side_p1 = tracker.sides.get("p1", {})
        side_p2 = tracker.sides.get("p2", {})
        active_p1 = side_p1.get("active_species")
        active_p2 = side_p2.get("active_species")
        inferred_active = active_p1 if args.side == "p1" else active_p2
        
        # Extract status and side conditions from tactical state
        active_ident_p1 = side_p1.get("active")
        active_ident_p2 = side_p2.get("active")
        p1_status = None
        p2_status = None
        p1_side_conditions = {}
        p2_side_conditions = {}
        
        if active_ident_p1 and isinstance(side_p1.get("volatiles_by_ident"), dict):
            # volatiles_by_ident[ident] is a set of volatile effect IDs
            active_volatiles_p1 = side_p1.get("volatiles_by_ident", {}).get(active_ident_p1, set())
        if active_ident_p2 and isinstance(side_p2.get("volatiles_by_ident"), dict):
            active_volatiles_p2 = side_p2.get("volatiles_by_ident", {}).get(active_ident_p2, set())
        
        # Extract side conditions (hazards, screens)
        if isinstance(side_p1.get("side_conditions"), dict):
            p1_side_conditions = dict(side_p1.get("side_conditions"))
        if isinstance(side_p2.get("side_conditions"), dict):
            p2_side_conditions = dict(side_p2.get("side_conditions"))
        
        # Try to infer status from protocol events: scan all lines to find most recent status application
        # Status persists across turns unless cured, so we track the most recent |-status| for each side
        for line in prefix_lines:
            if "|p1a:" in line and "|-status" in line:
                if "par" in line.lower():
                    p1_status = "par"
                elif "brn" in line.lower():
                    p1_status = "brn"
                elif "psn" in line.lower():
                    p1_status = "psn"
                elif "slp" in line.lower():
                    p1_status = "slp"
                elif "frz" in line.lower():
                    p1_status = "frz"
            if "|p2a:" in line and "|-status" in line:
                if "par" in line.lower():
                    p2_status = "par"
                elif "brn" in line.lower():
                    p2_status = "brn"
                elif "psn" in line.lower():
                    p2_status = "psn"
                elif "slp" in line.lower():
                    p2_status = "slp"
                elif "frz" in line.lower():
                    p2_status = "frz"
        
        # Also check for status cures: |-curestatus|
        for line in prefix_lines:
            if "|p1a:" in line and "|-curestatus" in line:
                p1_status = None
            if "|p2a:" in line and "|-curestatus" in line:
                p2_status = None

        # Build opponent beliefs and private-side inference using existing helpers
        opponent_belief = build_opponent_beliefs(protocol_log=list(prefix_lines), trajectory=trace, player_side=args.side)
        private_side = extract_private_side_state(request_payload=None, legal_actions=[], player_hint=args.side, active_species_hint=inferred_active)

        # Construct reconstructed legal actions: revealed active moves first, then randbats-inferred
        legal_actions = []
        revealed_moves = private_side.get("active_moves") or []
        for idx, mv in enumerate(revealed_moves):
            name = str(mv.get("name") or mv.get("move") or mv.get("id") or "unknown")
            inferred = bool(mv.get("inferred") or mv.get("source") == "randbats")
            legal_actions.append({
                "index": idx,
                "label": f"move:{name}",
                "choice": name,
                "kind": "move",
                "slot": mv.get("slot") or (idx + 1),
                "move": name,
                "source": "randbats_inferred" if inferred else "revealed",
                "confidence": float(mv.get("confidence", 1.0)) if mv.get("confidence") is not None else (0.5 if inferred else 1.0),
            })

        # Add switch candidates from reconstructed team
        team = private_side.get("team") or []
        for sidx, mon in enumerate(team):
            species = mon.get("species") or mon.get("ident") or "unknown"
            legal_actions.append({
                "index": 8 + sidx,
                "label": f"switch:{species}",
                "choice": f"switch {sidx+1}",
                "kind": "switch",
                "slot": mon.get("slot") or (sidx + 1),
                "species": species,
                "source": "hindsight_reconstructed_team" if mon.get("source") in ("request", "team") or bool(trace.get("p1") or trace.get("p2")) else "reconstructed",
                "confidence": 0.6 if mon.get("inferred_from_randbats") else 1.0,
            })

        diagnostics = {
            "protocol_prefix_source": "protocol_prefix_randbats_approx",
            "requested_turn": requested_turn,
            "active_matchup": f"{active_p1} vs {active_p2}" if active_p1 and active_p2 else "unknown",
            "p1_active_species": active_p1,
            "p2_active_species": active_p2,
            "p1_status": p1_status,
            "p2_status": p2_status,
            "p1_side_conditions": p1_side_conditions,
            "p2_side_conditions": p2_side_conditions,
            "revealed_active_moves": [m.get("name") for m in revealed_moves],
            "randbats_candidate_count": sum(int(o.get("candidate_count", 0)) for o in (opponent_belief.get("opponents") or [])),
            "hindsight_reconstructed_team": bool(team and any(m.get("source") not in ("request",) for m in team)),
        }

        if not legal_actions:
            # Can't derive legal actions: report rollout_unavailable
            results = [
                {
                    "label": "none",
                    "method": "rollout_unavailable",
                    "rollout_mode": "approximate",
                    "approximate_state": True,
                    "rollout_unavailable_reason": "legal_actions_unavailable_from_public_replay",
                    "rollout_unavailable_details": diagnostics,
                }
            ]
        else:
            # Build a pseudo-trace with a single pseudo-step so existing approx builder can use it
            pseudo_step = {
                "turn": requested_turn,
                "protocol_prefix": list(prefix_lines),
                "source": "protocol_prefix_randbats_approx",
                "player_side": args.side,
                "p1_hp_ratio": 1.0,
                "p2_hp_ratio": 1.0,
                "p1_boosts": {},
                "p2_boosts": {},
                "p1_status": p1_status,
                "p2_status": p2_status,
                "opponent_status": p2_status if args.side == "p1" else p1_status,
            }
            trace_copy = dict(trace)
            own_state = side_p1 if args.side == "p1" else side_p2
            opp_state = side_p2 if args.side == "p1" else side_p1
            own_species = active_p1 if args.side == "p1" else active_p2
            opp_species = active_p2 if args.side == "p1" else active_p1
            request_moves = [
                {
                    "move": str(action.get("move") or action.get("label") or "").split(":", 1)[-1].strip(),
                    "id": str(action.get("move") or action.get("label") or "").split(":", 1)[-1].strip().replace(" ", "").lower(),
                    "pp": 1,
                    "maxpp": 1,
                    "disabled": False,
                }
                for action in legal_actions
                if str(action.get("kind") or "").startswith("move")
            ]
            pseudo_step["view"] = {
                "format": str(trace.get("format") or "gen9randombattle"),
                "gen": 9,
                "turn": requested_turn,
                "player": args.side,
                "opponent": "p1" if args.side == "p2" else "p2",
                "active": {"self": 0, "opponent": 0},
                "self_team": [_pokemon_for_view(own_species or "Unknown", own_state)],
                "opponent_team": [_pokemon_for_view(opp_species or "Unknown", opp_state)],
                "field": {"weather": None, "terrain": None, "pseudo_weather": [], "side_conditions": {"self": {}, "opponent": {}}},
            }
            pseudo_step["request"] = {
                "player": args.side,
                "side": {
                    "id": args.side,
                    "pokemon": [
                        {
                            "ident": own_state.get("active_ident") or f"{args.side}: {own_species}",
                            "details": f"{own_species or 'Unknown'}, L80",
                            "condition": _side_condition(own_state),
                            "active": True,
                            "stats": {},
                            "moves": [move["move"] for move in request_moves],
                        }
                    ],
                },
                "active": [{"moves": request_moves, "canTerastallize": False, "trapped": False}],
                "legal_actions": {
                    "actions": [
                        {
                            "index": int(action.get("index", index)),
                            "kind": action.get("kind"),
                            "label": action.get("label"),
                            "choice": action.get("choice"),
                            "move": action.get("move"),
                            "slot": action.get("slot"),
                        }
                        for index, action in enumerate(legal_actions)
                    ]
                },
            }
            trace_copy["turns"] = [{"turn": requested_turn, "steps": [pseudo_step]}]
            trace_copy["protocol_log"] = list(prefix_lines)

            payload = {"trace": trace_copy}
            results = evaluate_actions(
                payload,
                args.side,
                legal_actions,
                "uniform",
                {"rollouts_per_action": 8, "rollout_mode": "approximate"},
            )
            # Attach our diagnostics to each result
            for r in results:
                r.setdefault("approximation_diagnostics", {}).update(diagnostics)
    if args.rollout_mode == "exact" and any(result.get("rollout_unavailable_reason") == "exact_replay_unavailable" for result in results):
        raise SystemExit(
            "Exact replay branching unavailable: public replay lacks seed/private state. Use --rollout-mode approximate for decision analysis."
        )

    # Print a human-friendly summary and JSON payload
    try:
        primary = results[0] if isinstance(results, list) and results else None
    except Exception:
        primary = None

    # Extract diagnostics from first result if available
    diag = {}
    if isinstance(results, list) and results and isinstance(results[0], dict):
        diag = results[0].get("approximation_diagnostics", {})
    
    summary = {
        "turn": int(args.turn) if args.turn is not None else int(args.step_index or 0),
        "side": args.side,
        "method": primary.get("method") if isinstance(primary, dict) else None,
        "approximate": any(bool(r.get("approximate_state")) for r in (results or [])),
        "active_matchup": diag.get("active_matchup"),
        "p1_status": diag.get("p1_status"),
        "p2_status": diag.get("p2_status"),
    }
    print("SUMMARY:")
    print(json.dumps(summary, indent=2))
    print("ACTIVE_MATCHUP:")
    print(json.dumps({"p1": diag.get("p1_active_species"), "p2": diag.get("p2_active_species"), "p1_status": diag.get("p1_status"), "p2_status": diag.get("p2_status")}, indent=2))
    print("RECONSTRUCTED_LEGAL_ACTIONS:")
    try:
        for la in legal_actions:
            print(json.dumps(la, default=str))
    except Exception:
        pass
    print("RESULTS:")
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
