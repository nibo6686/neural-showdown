import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .build_replay_value_dataset import (
    DEFAULT_FORMAT,
    _ensure_trajectories,
    _load_trajectories,
    _safe_float,
    result_from_winner_side,
)
from .live_opponent_beliefs import build_opponent_beliefs
from .live_private_features import (
    FEATURE_DIM,
    FEATURE_NAMES,
    FEATURE_VERSION,
    build_live_private_feature_vector,
    public_feature_vector_from_trajectory,
    trajectory_prefix,
)
from .logging_helper import format_summary, print_line_safe
from .tactical_state import (
    TACTICAL_STATE_FEATURE_NAMES,
    build_tactical_state,
    tactical_report_from_state,
)
from .value_features import (
    discounted_terminal_return,
    final_result_from_winner,
    flatten_trace_steps,
    load_trace,
    view_request_from_step,
)


DEFAULT_OUTPUT_PATH = Path("data/value/gen9randombattle_live_private_value_v2.npz")
DEFAULT_REPORT_JSON_PATH = Path("artifacts/analysis/live_private_value_dataset_report.json")
DEFAULT_REPORT_MD_PATH = Path("artifacts/analysis/live_private_value_dataset_report.md")
DEFAULT_TRACE_DIR = Path("artifacts/battles/dev")


def _metadata_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _species_from_text(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value)
    if ": " in text:
        text = text.split(": ", 1)[1]
    return text.split(",", 1)[0].strip() or None


def _species_from_event(event: Dict[str, Any]) -> Optional[str]:
    if event.get("type") in ("switch", "replace"):
        return _species_from_text(event.get("details") or event.get("actor"))
    return _species_from_text(event.get("actor") or event.get("target"))


def _replay_roster_alias_id(species: Any) -> str:
    species_id = re.sub(r"[^a-z0-9]+", "", str(species or "").lower())
    if species_id in {"terapagosterastal", "terapagosstellar"}:
        return "terapagos"
    if species_id == "palafinhero":
        return "palafin"
    if species_id.startswith("ogerpon") and species_id.endswith("tera"):
        return species_id[: -len("tera")]
    if species_id in {"polteageistantique", "sinisteaantique"}:
        return species_id.replace("antique", "")
    if species_id in {"eiscuenoice", "mimikyubusted", "miniorcore", "zygardecomplete"}:
        return {
            "eiscuenoice": "eiscue",
            "mimikyubusted": "mimikyu",
            "miniorcore": "minior",
            "zygardecomplete": "zygarde",
        }[species_id]
    return species_id


def _canonical_species_from_completed_team(completed_team: Dict[str, Dict[str, Any]], species: str) -> str:
    alias_id = _replay_roster_alias_id(species)
    for existing in completed_team:
        if _replay_roster_alias_id(existing) == alias_id:
            return existing
    return species


def _merge_public_species_state(current_state: Dict[str, Dict[str, Any]], species: str, state: Dict[str, Any]) -> None:
    slot = current_state.setdefault(species, {"hp_fraction": 1.0, "fainted": False, "active": False})
    if state.get("active"):
        slot["active"] = True
    if "hp_fraction" in state:
        slot["hp_fraction"] = state.get("hp_fraction")
    if state.get("fainted"):
        slot["fainted"] = True


def _request_like_move_names(moves: Any) -> List[str]:
    move_names = sorted(str(move) for move in moves if str(move or "").strip())
    non_struggle = [move for move in move_names if re.sub(r"[^a-z0-9]+", "", move.lower()) != "struggle"]
    return (non_struggle or move_names)[:4]


def _protocol_prefix_until_turn(protocol_log: Sequence[str], through_turn: int) -> List[str]:
    result: List[str] = []
    current_turn = 0
    for line in protocol_log:
        text = str(line)
        if text.startswith("|turn|"):
            parts = text.split("|")
            try:
                current_turn = int(parts[2])
            except (IndexError, ValueError):
                current_turn = through_turn
            if current_turn > through_turn:
                break
        if current_turn <= through_turn:
            result.append(text)
    return result


def _trajectory_prefix_for_training(trajectory: Dict[str, Any], through_turn: int) -> Dict[str, Any]:
    prefix = trajectory_prefix(trajectory, through_turn)
    protocol_log = trajectory.get("protocol_log") if isinstance(trajectory.get("protocol_log"), list) else []
    prefix["protocol_log"] = _protocol_prefix_until_turn(protocol_log, through_turn)
    return prefix


def _reconstructed_completed_private_teams(trajectory: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    teams: Dict[str, Dict[str, Dict[str, Any]]] = {"p1": {}, "p2": {}}
    turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    for turn in turns:
        events = turn.get("events") if isinstance(turn, dict) and isinstance(turn.get("events"), list) else []
        for event in events:
            if not isinstance(event, dict):
                continue
            side = event.get("side")
            if side not in ("p1", "p2"):
                continue
            species = _species_from_event(event)
            if not species:
                continue
            slot = teams[side].setdefault(
                species,
                {
                    "species": species,
                    "moves": set(),
                    "item": None,
                    "ability": None,
                    "tera_type": None,
                },
            )
            if event.get("type") == "move" and event.get("move"):
                slot["moves"].add(str(event["move"]))
            if event.get("type") == "tera" and event.get("tera_type"):
                slot["tera_type"] = str(event["tera_type"])

    protocol_log = trajectory.get("protocol_log") if isinstance(trajectory.get("protocol_log"), list) else []
    for line in protocol_log:
        if not isinstance(line, str) or not line.startswith("|-"):
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        tag = parts[1]
        if tag not in ("-ability", "-item", "-enditem", "-terastallize"):
            continue
        side = parts[2][:2]
        if side not in ("p1", "p2"):
            continue
        species = _species_from_text(parts[2])
        if not species:
            continue
        slot = teams[side].setdefault(
            species,
            {"species": species, "moves": set(), "item": None, "ability": None, "tera_type": None},
        )
        if tag == "-ability":
            slot["ability"] = parts[3]
        elif tag in ("-item", "-enditem"):
            slot["item"] = parts[3]
        elif tag == "-terastallize":
            slot["tera_type"] = parts[3]
    return teams


def _side_public_state_at_turn(trajectory: Dict[str, Any], side: str, through_turn: int) -> Dict[str, Dict[str, Any]]:
    state: Dict[str, Dict[str, Any]] = {}
    active_species: Optional[str] = None
    turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    for turn in sorted(turns, key=lambda item: int(item.get("turn", 0) or 0)):
        turn_number = int(turn.get("turn", 0) or 0)
        if turn_number > through_turn:
            break
        events = turn.get("events") if isinstance(turn.get("events"), list) else []
        for event in events:
            if not isinstance(event, dict) or event.get("side") != side:
                continue
            species = _species_from_event(event)
            if not species:
                continue
            slot = state.setdefault(species, {"hp_fraction": 1.0, "fainted": False, "active": False})
            if event.get("type") in ("switch", "replace"):
                for existing in state.values():
                    existing["active"] = False
                active_species = species
                slot["active"] = True
                if event.get("hp_fraction") is not None:
                    slot["hp_fraction"] = max(0.0, min(1.0, _safe_float(event.get("hp_fraction"), 1.0)))
                slot["fainted"] = False
            elif event.get("type") in ("damage", "heal") and event.get("hp_fraction") is not None:
                hp_fraction = max(0.0, min(1.0, _safe_float(event.get("hp_fraction"), 1.0)))
                slot["hp_fraction"] = hp_fraction
                if event.get("type") == "heal" and hp_fraction > 0.0:
                    slot["fainted"] = False
            elif event.get("type") == "faint":
                slot["hp_fraction"] = 0.0
                slot["fainted"] = True
                if active_species == species:
                    slot["active"] = True
    return state


def _ordered_events(trajectory: Dict[str, Any]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for turn in sorted(trajectory.get("turns", []), key=lambda row: int(row.get("turn", 0) or 0)):
        if not isinstance(turn, dict):
            continue
        for event in turn.get("events", []):
            if isinstance(event, dict):
                events.append(event)
    return events


def _active_transform_copied_moves(
    prefix: Dict[str, Any],
    full_trajectory: Optional[Dict[str, Any]],
    side: str,
) -> Optional[set]:
    """Reconstruct the copied moveset of a currently-transformed active.

    Transform/Imposter copies the target's moveset, which the transforming player
    legitimately sees in their own request. The copied set is scoped to the
    current Transform stint: it resets on the actor's switch and on each new
    Transform, and never merges moves from a different stint. Within the current
    stint the own-side future-public-reveal assumption applies (moves revealed
    later in the same stint are part of the same copied request), but later
    Transform stints are excluded.

    Returns the copied move set when the active is currently transformed, else
    ``None``.
    """
    anchor_event: Optional[Dict[str, Any]] = None
    target_species: Optional[str] = None
    for event in _ordered_events(prefix):
        if event.get("side") != side:
            continue
        etype = event.get("type")
        if etype == "switch":
            anchor_event = None
            target_species = None
        elif etype == "transform":
            anchor_event = event
            target_species = _species_from_text(event.get("target"))
    if anchor_event is None:
        return None

    # Anchor the current stint by event identity, not by raw string: re-transforming
    # into the same species produces identical `raw` markers, so a string match would
    # bind to the earliest occurrence and stop at an intervening switch.
    copied: set = set()
    opponent_active: Dict[str, Optional[str]] = {"p1": None, "p2": None}
    in_stint = False
    for event in _ordered_events(full_trajectory or prefix):
        event_side = event.get("side")
        etype = event.get("type")
        if etype in ("switch", "replace"):
            species = _species_from_text(event.get("details") or event.get("actor"))
            if event_side in ("p1", "p2") and species:
                opponent_active[event_side] = species
        if not in_stint:
            if event is anchor_event:
                in_stint = True
            continue
        if event_side == side and etype in ("switch", "faint"):
            break
        if event_side == side and etype == "transform" and event is not anchor_event:
            break
        if etype == "move" and event.get("move"):
            move = str(event["move"])
            if event_side == side:
                copied.add(move)
            elif target_species and opponent_active.get(event_side) == target_species:
                copied.add(move)
    copied.discard("Transform")
    return copied


def _illusion_true_species_for_stint(
    full_trajectory: Optional[Dict[str, Any]],
    side: str,
    anchor_event: Dict[str, Any],
) -> Optional[str]:
    """Return the true Illusion species for an active stint that self-confirms.

    A stint starts when ``anchor_event`` (a switch) brings an entity into the
    active slot. If a later ``replace`` for ``side`` reveals a different species
    before the next ``switch`` for ``side``, that entity was an Illusion and the
    revealed species is its true identity. Otherwise the stint is not
    self-confirming and ``None`` is returned. Detection uses only the replay's
    own reveal — never a chosen-action guess or HP heuristic.
    """
    if full_trajectory is None or anchor_event.get("type") != "switch":
        return None
    apparent = _species_from_text(anchor_event.get("details") or anchor_event.get("actor"))
    started = False
    for event in _ordered_events(full_trajectory):
        if not started:
            if event is anchor_event:
                started = True
            continue
        if event.get("side") != side:
            continue
        etype = event.get("type")
        if etype == "switch":
            return None
        if etype == "replace":
            revealed = _species_from_text(event.get("details") or event.get("actor"))
            if revealed and revealed != apparent:
                return revealed
            return None
    return None


def _own_side_illusion_true_active(
    prefix: Dict[str, Any],
    full_trajectory: Optional[Dict[str, Any]],
    side: str,
) -> Optional[str]:
    """True species of the own-side active when it is a pre-reveal Illusion.

    The active entity is anchored by the most recent switch/replace for ``side``
    in the causal prefix. If that entity is still displayed under its disguise
    (anchor is a switch) but self-confirms as an Illusion later in the full
    trajectory, the actor privately knew the true species at decision time.
    Returns ``None`` once the reveal has already happened publicly (anchor is a
    replace) or when the stint is not self-confirming.
    """
    anchor = None
    for event in _ordered_events(prefix):
        if event.get("side") == side and event.get("type") in ("switch", "replace"):
            anchor = event
    if anchor is None:
        return None
    return _illusion_true_species_for_stint(full_trajectory, side, anchor)


def actor_private_switch_relabel(
    label: Optional[str],
    full_trajectory: Optional[Dict[str, Any]],
    side: str,
    event: Dict[str, Any],
) -> Optional[str]:
    """Relabel an own-side switch action to the true Illusion species.

    When the switched-in entity self-confirms as an Illusion (a later ``replace``
    in its stint), the acting player knew they were switching in their true
    Zoroark/Zoroark-Hisui, so the displayed-species label is mapped to the true
    species. The mapped label only matches an already-legal own-side switch
    candidate; no new candidate is created.
    """
    if not label or not label.startswith("switch:") or event.get("type") != "switch":
        return label
    true_species = _illusion_true_species_for_stint(full_trajectory, side, event)
    return f"switch: {true_species}" if true_species else label


def _reconstructed_private_state_for_side(
    trajectory: Dict[str, Any],
    *,
    side: str,
    through_turn: int,
    completed_teams: Dict[str, Dict[str, Dict[str, Any]]],
    full_trajectory: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    completed_team = completed_teams.get(side, {})
    raw_current_state = _side_public_state_at_turn(trajectory, side, through_turn)
    current_state: Dict[str, Dict[str, Any]] = {}
    for species, state in raw_current_state.items():
        canonical_species = _canonical_species_from_completed_team(completed_team, species)
        _merge_public_species_state(current_state, canonical_species, state)
    # Actor-private Illusion de-disguise: when the own-side active is a pre-reveal
    # Illusion that self-confirms later, the acting player privately knew the true
    # species. Move the active entry from the displayed species to the true one so
    # its true moves become legal candidates. Opponent belief is built separately
    # from the causal prefix and is unaffected.
    illusion_true = _own_side_illusion_true_active(trajectory, full_trajectory, side)
    if illusion_true and illusion_true in completed_team:
        apparent = next((sp for sp, st in current_state.items() if st.get("active")), None)
        if apparent and _replay_roster_alias_id(apparent) != _replay_roster_alias_id(illusion_true):
            moved = current_state.pop(apparent)
            target = current_state.setdefault(
                illusion_true, {"hp_fraction": 1.0, "fainted": False, "active": False}
            )
            target["active"] = True
            target["hp_fraction"] = moved.get("hp_fraction", 1.0)
            if moved.get("fainted"):
                target["fainted"] = True

    species_order = list(completed_team.keys())
    for species in current_state:
        if species not in completed_team:
            completed_team[species] = {"species": species, "moves": set(), "item": None, "ability": None, "tera_type": None}
            species_order.append(species)

    team: List[Dict[str, Any]] = []
    active_species = None
    for species in species_order[:6]:
        complete = completed_team.get(species, {})
        current = current_state.get(species, {})
        active = bool(current.get("active", False))
        if active:
            active_species = species
        team.append(
            {
                "ident": f"{side}: {species}",
                "species": species,
                "details": species,
                "active": active,
                "hp_fraction": float(current.get("hp_fraction", 1.0)),
                "fainted": bool(current.get("fainted", False)),
                "moves": sorted(list(complete.get("moves", set()))),
                "item": complete.get("item"),
                "ability": complete.get("ability"),
                "base_ability": complete.get("ability"),
                "tera_type": complete.get("tera_type"),
            }
        )

    active_moves = []
    active_complete_moves = set()
    transform_moves = _active_transform_copied_moves(trajectory, full_trajectory, side) if active_species else None
    if transform_moves is not None:
        active_complete_moves = set(transform_moves)
    elif active_species and active_species in completed_team:
        raw_moves = completed_team[active_species].get("moves", set())
        active_complete_moves = set(raw_moves) if isinstance(raw_moves, set) else set()
    if active_species:
        for move in _request_like_move_names(active_complete_moves):
            active_moves.append(
                {
                    "id": move.lower().replace(" ", ""),
                    "name": move,
                    "pp": 1,
                    "maxpp": 1,
                    "disabled": False,
                    "can_tera": False,
                }
            )

    legal_actions = [{"kind": "move", "label": move["name"], "disabled": False} for move in active_moves]
    legal_actions.extend(
        {
            "kind": "switch",
            "label": str(mon["species"]),
            "disabled": False,
        }
        for mon in team
        if not mon.get("active") and not mon.get("fainted")
    )
    return {
        "player_side": side,
        "active_species": active_species,
        "team": team,
        "active_moves": active_moves,
        "force_switch": False,
        "wait": False,
        "trapped": False,
        "legal_actions": legal_actions[:13],
        "can_tera": False,
        "struggle_available": any(
            re.sub(r"[^a-z0-9]+", "", str(move).lower()) == "struggle"
            for move in active_complete_moves
        ),
    }


def _legal_actions_from_step(step: Dict[str, Any], request: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if isinstance(request, dict):
        legal = request.get("legal_actions")
        if isinstance(legal, dict) and isinstance(legal.get("actions"), list):
            return [action for action in legal["actions"] if isinstance(action, dict)]
        if isinstance(legal, list):
            return [action for action in legal if isinstance(action, dict)]
    raw = step.get("legal_actions")
    return [action for action in raw if isinstance(action, dict)] if isinstance(raw, list) else []


def _moves_from_request_or_actions(request: Optional[Dict[str, Any]], legal_actions: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if isinstance(request, dict):
        active = request.get("active")
        active_block = active if isinstance(active, dict) else (active[0] if isinstance(active, list) and active else {})
        active_can_tera = bool(active_block.get("can_terastallize") or active_block.get("canTerastallize")) if isinstance(active_block, dict) else False
        moves = active_block.get("moves") if isinstance(active_block, dict) else None
        if isinstance(moves, list):
            result = []
            for move in moves:
                if not isinstance(move, dict):
                    continue
                result.append(
                    {
                        "id": move.get("id"),
                        "name": move.get("move") or move.get("name") or move.get("id"),
                        "pp": move.get("pp", 1),
                        "maxpp": move.get("maxpp", 1),
                        "disabled": bool(move.get("disabled", False)),
                        "can_tera": active_can_tera or bool(move.get("can_tera") or move.get("canTerastallize")),
                    }
                )
            if result:
                return result

    moves = []
    seen = set()
    for action in legal_actions:
        kind = str(action.get("kind") or "")
        if not kind.startswith("move"):
            continue
        name = str(action.get("move") or action.get("label") or "")
        if name.startswith("move:"):
            name = name.split(":", 1)[1]
        if name.startswith("move_tera:"):
            name = name.split(":", 1)[1]
        if not name or name in seen:
            continue
        seen.add(name)
        moves.append(
            {
                "id": name.lower().replace(" ", ""),
                "name": name,
                "pp": 1,
                "maxpp": 1,
                "disabled": bool(action.get("disabled", False)),
                "can_tera": "tera" in kind,
            }
        )
    return moves[:4]


def _trace_private_state(trace: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
    view, request = view_request_from_step(trace, step)
    legal_actions = _legal_actions_from_step(step, request)
    own_team = view.get("self_team") if isinstance(view, dict) and isinstance(view.get("self_team"), list) else []
    active_index = 0
    if isinstance(view, dict) and isinstance(view.get("active"), dict):
        try:
            active_index = int(view["active"].get("self", 0) or 0)
        except (TypeError, ValueError):
            active_index = 0

    team = []
    for index, mon in enumerate(own_team[:6]):
        if not isinstance(mon, dict):
            continue
        hp_fraction = mon.get("hp_fraction", mon.get("hp_ratio"))
        team.append(
            {
                "ident": mon.get("ident") or mon.get("species"),
                "species": mon.get("species") or mon.get("name") or mon.get("ident"),
                "active": bool(mon.get("active", index == active_index)),
                "hp_fraction": float(hp_fraction if hp_fraction is not None else 1.0),
                "fainted": bool(mon.get("fainted", False)),
                "moves": list(mon.get("moves", [])) if isinstance(mon.get("moves"), list) else [],
                "item": mon.get("item"),
                "ability": mon.get("ability"),
                "base_ability": mon.get("base_ability") or mon.get("baseAbility"),
                "tera_type": mon.get("tera_type") or mon.get("teraType"),
                "terastallized": bool(mon.get("terastallized", False)),
            }
        )

    request_dict = request if isinstance(request, dict) else {}
    raw_active = request_dict.get("active")
    active_request = raw_active if isinstance(raw_active, dict) else (raw_active[0] if isinstance(raw_active, list) and raw_active and isinstance(raw_active[0], dict) else {})
    force_switch = bool(request_dict.get("force_switch") or request_dict.get("forceSwitch"))
    tera_used = any(bool(mon.get("terastallized")) for mon in team)
    raw_can_tera = active_request.get("can_terastallize") or active_request.get("canTerastallize")
    active_tera_type = raw_can_tera if isinstance(raw_can_tera, str) else None
    if not active_tera_type and 0 <= active_index < len(team):
        active_tera_type = team[active_index].get("tera_type")
    return {
        "player_side": request_dict.get("player") if request_dict.get("player") in ("p1", "p2") else "p1",
        "active_species": team[active_index].get("species") if 0 <= active_index < len(team) else None,
        "team": team,
        "active_moves": _moves_from_request_or_actions(request, legal_actions),
        "force_switch": force_switch,
        "wait": bool(request_dict.get("wait", False)),
        "trapped": bool(request_dict.get("trapped") or active_request.get("trapped")),
        "legal_actions": legal_actions,
        "can_tera": bool(raw_can_tera and not tera_used and not force_switch),
        "active_tera_type": active_tera_type,
        "tera_used": tera_used,
    }


def _protocol_history_from_steps(steps: Sequence[Dict[str, Any]], end_index: int) -> List[str]:
    lines: List[str] = []
    for step in steps[: end_index + 1]:
        raw = step.get("protocol_log")
        if isinstance(raw, list):
            lines.extend(str(line) for line in raw)
    return lines


def _examples_from_public_trajectory(
    trajectory: Dict[str, Any],
    *,
    sets_path: Optional[str],
    include_debug_fields: bool = False,
) -> List[Dict[str, Any]]:
    if result_from_winner_side(trajectory.get("winner_side"), perspective="p1") is None:
        return []
    turns = trajectory.get("turns") if isinstance(trajectory.get("turns"), list) else []
    completed_teams = _reconstructed_completed_private_teams(trajectory)
    examples: List[Dict[str, Any]] = []
    for turn_record in sorted(turns, key=lambda item: int(item.get("turn", 0) or 0)):
        turn_number = int(turn_record.get("turn", 0) or 0)
        prefix = _trajectory_prefix_for_training(trajectory, turn_number)
        for side in ("p1", "p2"):
            result = result_from_winner_side(trajectory.get("winner_side"), perspective=side)
            if result is None:
                continue
            public_features, _ = public_feature_vector_from_trajectory(prefix, perspective_side=side)
            private_state = _reconstructed_private_state_for_side(
                trajectory,
                side=side,
                through_turn=turn_number,
                completed_teams=completed_teams,
            )
            belief = build_opponent_beliefs(
                protocol_log=prefix.get("protocol_log", []),
                trajectory=prefix,
                player_side=side,
                sets_path=sets_path,
            )
            tactical_state = build_tactical_state(prefix.get("protocol_log", []), perspective_side=side)
            private_state["tactical_state"] = tactical_state
            features, _ = build_live_private_feature_vector(
                public_features=public_features,
                private_state=private_state,
                opponent_belief=belief,
                trajectory=prefix,
                player_side=side,
                tactical_state=tactical_state,
            )
            tactical_report = tactical_report_from_state(tactical_state)
            example = {
                "state": features,
                "value_target": float(result),
                "final_result": float(result),
                "turn": turn_number,
                "source_kind": "public_replay_private_reconstructed",
                "source_id": str(trajectory.get("replay_id") or ""),
                "missing_private_state": 0.0,
                "tactical": tactical_report,
            }
            if include_debug_fields:
                example["metadata_json"] = _metadata_json(
                        {
                            "source_kind": "public_replay_private_reconstructed",
                            "replay_id": trajectory.get("replay_id"),
                            "perspective": side,
                            "turn": turn_number,
                            "feature_version": FEATURE_VERSION,
                            "own_team_reconstructed_count": len(private_state.get("team", [])),
                            "tactical": tactical_report,
                        }
                    )
            examples.append(example)
    return examples


def _examples_from_trace_path(
    path: Path,
    *,
    gamma: float,
    sets_path: Optional[str],
    include_debug_fields: bool = False,
) -> List[Dict[str, Any]]:
    trace = load_trace(path)
    steps = flatten_trace_steps(trace)
    final_result = final_result_from_winner(trace.get("winner"))
    examples: List[Dict[str, Any]] = []
    for ordinal, step in enumerate(steps):
        protocol_history = _protocol_history_from_steps(steps, ordinal)
        trajectory = {
            "replay_id": path.stem,
            "format": trace.get("format", DEFAULT_FORMAT),
            "teamsize": {"p1": 6, "p2": 6},
            "turns": [],
            "protocol_log": protocol_history,
        }
        if protocol_history:
            from .parse_replay_logs import parse_protocol_log

            trajectory = parse_protocol_log(
                protocol_history,
                replay_id=path.stem,
                format_name=str(trace.get("format") or DEFAULT_FORMAT),
                source_path=str(path),
                metadata={"source": "local_trace"},
            )
        public_features, _ = public_feature_vector_from_trajectory(trajectory)
        private_state = _trace_private_state(trace, step)
        belief = build_opponent_beliefs(
            protocol_log=protocol_history,
            trajectory=trajectory,
            player_side="p1",
            sets_path=sets_path,
        )
        tactical_state = build_tactical_state(protocol_history, perspective_side="p1")
        private_state["tactical_state"] = tactical_state
        features, _ = build_live_private_feature_vector(
            public_features=public_features,
            private_state=private_state,
            opponent_belief=belief,
            trajectory=trajectory,
            player_side="p1",
            tactical_state=tactical_state,
        )
        tactical_report = tactical_report_from_state(tactical_state)
        steps_to_terminal = max(0, len(steps) - ordinal - 1)
        example = {
            "state": features,
            "value_target": discounted_terminal_return(final_result, steps_to_terminal, gamma),
            "final_result": float(final_result),
            "turn": int(step.get("turn", 0) or 0),
            "source_kind": "local_trace_private",
            "source_id": str(path),
            "missing_private_state": 0.0,
            "tactical": tactical_report,
        }
        if include_debug_fields:
            example["metadata_json"] = _metadata_json(
                    {
                        "source_kind": "local_trace_private",
                        "trace": str(path),
                        "step_index": int(step.get("step_index", ordinal) or 0),
                        "turn": int(step.get("turn", 0) or 0),
                        "feature_version": FEATURE_VERSION,
                        "tactical": tactical_report,
                    }
                )
        examples.append(example)
    return examples


def _iter_trace_paths(trace_dirs: Sequence[Path], trace_paths: Sequence[Path]) -> List[Path]:
    paths: List[Path] = []
    for trace_dir in trace_dirs:
        if trace_dir.exists():
            paths.extend(sorted(trace_dir.glob("battle_*.json")))
    for trace_path in trace_paths:
        if trace_path.exists():
            paths.append(trace_path)
    seen = set()
    result = []
    for path in paths:
        resolved = str(path.resolve())
        if resolved not in seen:
            result.append(path)
            seen.add(resolved)
    return result


def _source_kind_encoding(examples: Sequence[Dict[str, Any]]) -> Dict[str, np.ndarray]:
    names = sorted({str(example["source_kind"]) for example in examples})
    name_to_code = {name: index for index, name in enumerate(names)}
    return {
        "source_kind_names": np.asarray(names),
        "source_kind_codes": np.asarray([name_to_code[str(example["source_kind"])] for example in examples], dtype=np.int8),
    }


def _tactical_flag_arrays(examples: Sequence[Dict[str, Any]]) -> Dict[str, np.ndarray]:
    names = list(
        dict.fromkeys(
            [
                *TACTICAL_STATE_FEATURE_NAMES,
                "has_repeated_failed_move",
                "target_already_seeded",
                "move_healed_target",
                "recent_failed_count",
                "recent_healed_target_count",
            ]
        )
    )
    flags = np.zeros((len(examples), len(names)), dtype=np.uint8)
    for row, example in enumerate(examples):
        tactical = example.get("tactical") or {}
        for column, name in enumerate(names):
            flags[row, column] = 1 if bool(tactical.get(name)) else 0
    return {
        "tactical_flag_names": np.asarray(names),
        "tactical_flags": flags,
    }


def _stack_examples(examples: Sequence[Dict[str, Any]], *, include_debug_fields: bool = False) -> Dict[str, np.ndarray]:
    if not examples:
        raise ValueError("No live-private value examples were produced.")
    arrays = {
        "states": np.asarray([example["state"] for example in examples], dtype=np.float32),
        "value_targets": np.asarray([example["value_target"] for example in examples], dtype=np.float32),
        "final_results": np.asarray([example["final_result"] for example in examples], dtype=np.float32),
        "turns": np.asarray([example["turn"] for example in examples], dtype=np.int16),
        "missing_private_state": np.asarray([example["missing_private_state"] for example in examples], dtype=np.float32),
    }
    arrays.update(_source_kind_encoding(examples))
    arrays.update(_tactical_flag_arrays(examples))
    if include_debug_fields:
        arrays.update(
            {
                "legal_masks": np.zeros((len(examples), 13), dtype=np.float32),
                "source_kinds": np.asarray([example["source_kind"] for example in examples]),
                "source_ids": np.asarray([example["source_id"] for example in examples]),
                "metadata_json": np.asarray([example.get("metadata_json", "") for example in examples]),
                "tactical_json": np.asarray([_metadata_json(example.get("tactical", {})) for example in examples]),
            }
        )
    return arrays


def _tactical_dataset_metrics(examples: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    total = max(1, len(examples))

    def rate(key: str) -> float:
        return 100.0 * sum(1 for example in examples if bool((example.get("tactical") or {}).get(key))) / total

    return {
        "tactical_feature_count": int(len(TACTICAL_STATE_FEATURE_NAMES)),
        "percent_examples_with_repeated_failed_moves": rate("has_repeated_failed_move"),
        "percent_examples_with_target_already_seeded": rate("target_already_seeded"),
        "percent_examples_with_move_healed_target": rate("move_healed_target"),
        "percent_examples_with_own_active_seeded": rate("own_active_seeded"),
        "percent_examples_with_opp_active_seeded": rate("opp_active_seeded"),
        "percent_examples_with_own_active_substitute": rate("own_active_substitute"),
        "percent_examples_with_opp_active_substitute": rate("opp_active_substitute"),
    }


def build_live_private_value_dataset(
    *,
    format_name: str = DEFAULT_FORMAT,
    replay_dir: Optional[Path] = None,
    trajectories_path: Optional[Path] = None,
    trace_dirs: Sequence[Path] = (DEFAULT_TRACE_DIR,),
    trace_paths: Sequence[Path] = (),
    output_path: Path = DEFAULT_OUTPUT_PATH,
    report_json_path: Path = DEFAULT_REPORT_JSON_PATH,
    report_md_path: Path = DEFAULT_REPORT_MD_PATH,
    gamma: float = 1.0,
    sets_path: Optional[str] = None,
    include_debug_fields: bool = False,
    compressed: bool = True,
) -> Dict[str, Any]:
    started_at = time.perf_counter()
    selected_replay_dir = replay_dir or Path("data/replays/raw") / format_name
    selected_trajectories = trajectories_path or Path("data/replays/processed") / f"{format_name}_trajectories.jsonl.gz"
    _ensure_trajectories(format_name, selected_replay_dir, selected_trajectories)

    examples: List[Dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    trajectories = _load_trajectories(selected_trajectories)
    for trajectory in trajectories:
        source_examples = _examples_from_public_trajectory(
            trajectory,
            sets_path=sets_path,
            include_debug_fields=include_debug_fields,
        )
        examples.extend(source_examples)
        source_counts["public_replay_private_reconstructed"] += len(source_examples)

    trace_files = _iter_trace_paths(trace_dirs, trace_paths)
    trace_failures: List[Dict[str, str]] = []
    for path in trace_files:
        try:
            source_examples = _examples_from_trace_path(
                path,
                gamma=gamma,
                sets_path=sets_path,
                include_debug_fields=include_debug_fields,
            )
            examples.extend(source_examples)
            source_counts["local_trace_private"] += len(source_examples)
        except Exception as exc:
            trace_failures.append({"path": str(path), "reason": str(exc)})

    arrays = _stack_examples(examples, include_debug_fields=include_debug_fields)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_npz = np.savez_compressed if compressed else np.savez
    save_npz(
        output_path,
        **arrays,
        feature_version=np.asarray(FEATURE_VERSION),
        feature_names=np.asarray(FEATURE_NAMES),
        gamma=np.asarray(float(gamma), dtype=np.float32),
    )

    final_results = arrays["final_results"]
    targets = arrays["value_targets"]
    missing_private = arrays["missing_private_state"]
    report = {
        "output_path": str(output_path),
        "feature_version": FEATURE_VERSION,
        "feature_dim": FEATURE_DIM,
        "feature_names": FEATURE_NAMES,
        **_tactical_dataset_metrics(examples),
        "examples": int(arrays["states"].shape[0]),
        "examples_from_public_replays": int(
            source_counts.get("public_replay_private_reconstructed", 0)
            + source_counts.get("public_replay_augmented", 0)
        ),
        "examples_from_local_traces": int(source_counts.get("local_trace_private", 0)),
        "source_breakdown": dict(source_counts),
        "missing_private_state_percentage": float(100.0 * missing_private.mean()) if len(missing_private) else 0.0,
        "outcome_distribution": {
            "wins": int((final_results > 0).sum()),
            "losses": int((final_results < 0).sum()),
            "ties": int((final_results == 0).sum()),
        },
        "target_distribution": {
            "mean": float(targets.mean()),
            "std": float(targets.std()),
            "min": float(targets.min()),
            "max": float(targets.max()),
        },
        "format": format_name,
        "replay_dir": str(selected_replay_dir),
        "trajectories_path": str(selected_trajectories),
        "raw_replay_logs": int(len(list(selected_replay_dir.glob("*.log"))) if selected_replay_dir.exists() else 0),
        "parsed_replays": int(len(trajectories)),
        "trace_dirs": [str(path) for path in trace_dirs],
        "trace_files": [str(path) for path in trace_files],
        "trace_failures": trace_failures,
        "gamma": float(gamma),
        "compressed": bool(compressed),
        "include_debug_fields": bool(include_debug_fields),
        "output_size_mb": float(output_path.stat().st_size / (1024 * 1024)) if output_path.exists() else None,
        "wall_time_sec": time.perf_counter() - started_at,
    }
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.write_text(_format_markdown_report(report), encoding="utf-8")
    print_line_safe(
        f"build-live-private-value-dataset done | examples={report['examples']} "
        f"public={report['examples_from_public_replays']} private={report['examples_from_local_traces']} "
        f"feature_dim={FEATURE_DIM} output={output_path}"
    )
    return report


def _format_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Live Private Value Dataset Report",
        "",
        f"- Examples: {report['examples']}",
        f"- Public replay augmented examples: {report['examples_from_public_replays']}",
        f"- Local trace/private examples: {report['examples_from_local_traces']}",
        f"- Feature version: {report['feature_version']}",
        f"- Feature dimension: {report['feature_dim']}",
        f"- Tactical feature count: {report.get('tactical_feature_count', 0)}",
        f"- Missing private state: {report['missing_private_state_percentage']:.1f}%",
        f"- Target mean/std: {report['target_distribution']['mean']:.4f} / {report['target_distribution']['std']:.4f}",
        f"- Repeated failed move examples: {report.get('percent_examples_with_repeated_failed_moves', 0.0):.1f}%",
        f"- Target already seeded examples: {report.get('percent_examples_with_target_already_seeded', 0.0):.1f}%",
        f"- Move healed target examples: {report.get('percent_examples_with_move_healed_target', 0.0):.1f}%",
        "",
        "## Outcomes",
        "",
    ]
    for key, value in report.get("outcome_distribution", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Sources", ""])
    for key, value in report.get("source_breakdown", {}).items():
        lines.append(f"- {key}: {value}")
    if report.get("trace_failures"):
        lines.extend(["", "## Trace Failures", ""])
        for failure in report["trace_failures"][:10]:
            lines.append(f"- `{failure['path']}`: {failure['reason']}")
    lines.extend(["", f"Output: `{report['output_path']}`", ""])
    return "\n".join(lines)


def _parse_paths(values: Optional[Sequence[str]]) -> List[Path]:
    return [Path(value) for value in values or [] if value]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build live-private-belief value features from public replays and traces.")
    parser.add_argument("--format", default=DEFAULT_FORMAT)
    parser.add_argument("--replay-dir", default=None)
    parser.add_argument("--trajectories", default=None)
    parser.add_argument("--trace-dir", action="append", default=[])
    parser.add_argument("--trace-path", action="append", default=[])
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON_PATH))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD_PATH))
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--sets-path", default=None)
    parser.add_argument("--include-debug-fields", action="store_true")
    parser.add_argument("--uncompressed", action="store_true")
    args = parser.parse_args()

    trace_dirs = _parse_paths(args.trace_dir) or [DEFAULT_TRACE_DIR]
    report = build_live_private_value_dataset(
        format_name=args.format,
        replay_dir=Path(args.replay_dir) if args.replay_dir else None,
        trajectories_path=Path(args.trajectories) if args.trajectories else None,
        trace_dirs=trace_dirs,
        trace_paths=_parse_paths(args.trace_path),
        output_path=Path(args.output),
        report_json_path=Path(args.report_json),
        report_md_path=Path(args.report_md),
        gamma=args.gamma,
        sets_path=args.sets_path,
        include_debug_fields=args.include_debug_fields,
        compressed=not args.uncompressed,
    )
    print_line_safe(
        format_summary(
            "live-private-value-dataset",
            {
                "examples": report["examples"],
                "feature_dim": report["feature_dim"],
                "missing_private_pct": f"{report['missing_private_state_percentage']:.1f}",
                "output": report["output_path"],
            },
        )
    )


if __name__ == "__main__":
    main()
