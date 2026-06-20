from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from .provenance_contracts import delayed_landing_resolvable


_SUPPORTED_MOVES = {"futuresight", "doomdesire"}


def _to_id(value: Any) -> str:
    return "".join(character for character in str(value or "").lower() if character.isalnum())


def _slot_key(side: Any, slot: Any) -> str:
    return f"{str(side)}:{int(slot)}"


def schedule_delayed_attack(state: Dict[str, Any], attack: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(state)
    queue = result.setdefault("delayed_attacks", {})
    move = _to_id(attack.get("move"))
    if move not in _SUPPORTED_MOVES:
        return {"available": False, "scheduled": False, "reason": "unsupported_delayed_move", "state": result}
    if not isinstance(attack.get("scheduled_turn"), int):
        return {"available": False, "scheduled": False, "reason": "scheduled_turn_required", "state": result}
    if not isinstance(attack.get("target_slot"), int) or not attack.get("target_side"):
        return {"available": False, "scheduled": False, "reason": "target_side_and_slot_required", "state": result}
    damage_by_target = attack.get("damage_by_target")
    resolver_inputs = attack.get("resolver_inputs")
    has_target_specific = isinstance(damage_by_target, dict) and bool(attack.get("damage_provenance"))
    has_resolver = isinstance(resolver_inputs, dict) and bool(resolver_inputs)
    if not has_target_specific and not has_resolver:
        return {
            "available": False,
            "scheduled": False,
            "reason": "target_specific_damage_or_resolver_inputs_required",
            "state": result,
        }

    key = _slot_key(attack["target_side"], attack["target_slot"])
    if key in queue:
        return {
            "available": True,
            "scheduled": False,
            "reason": "target_slot_already_has_delayed_attack",
            "state": result,
        }

    scheduled_turn = int(attack["scheduled_turn"])
    queue[key] = {
        "move": move,
        "source_side": attack.get("source_side"),
        "source_pokemon_id": attack.get("source_pokemon_id"),
        "target_side": str(attack["target_side"]),
        "target_slot": int(attack["target_slot"]),
        "scheduled_turn": scheduled_turn,
        "landing_turn": scheduled_turn + 2,
        "damage_by_target": {str(name): int(value) for name, value in damage_by_target.items()} if has_target_specific else {},
        "damage_provenance": str(attack["damage_provenance"]) if has_target_specific else None,
        "resolver_inputs": deepcopy(resolver_inputs) if has_resolver else None,
    }
    return {"available": True, "scheduled": True, "reason": None, "state": result}


def resolve_delayed_attacks(state: Dict[str, Any], turn: int) -> Dict[str, Any]:
    result = deepcopy(state)
    queue = result.setdefault("delayed_attacks", {})
    active_slots = result.get("active_slots")
    if not isinstance(active_slots, dict):
        return {"available": False, "reason": "active_slots_required", "state": result, "events": []}

    events: List[Dict[str, Any]] = []
    for key, attack in list(queue.items()):
        if int(turn) < int(attack["landing_turn"]):
            continue
        target = active_slots.get(key)
        del queue[key]
        if not isinstance(target, dict) or int(target.get("hp", 0) or 0) <= 0:
            events.append({"effect": attack["move"], "target_slot": key, "result": "no_target"})
            continue
        target_id = str(target.get("pokemon_id") or "")
        if target_id and target_id == str(attack.get("source_pokemon_id") or ""):
            events.append({"effect": attack["move"], "target_slot": key, "result": "target_is_source"})
            continue
        resolution = delayed_landing_resolvable(attack, target_id)
        if not resolution["available"]:
            return {
                "available": False,
                "reason": f"{key}:{resolution['reason']}",
                "state": result,
                "events": events,
            }
        damage = resolution.get("damage")
        if damage is None:
            return {
                "available": False,
                "reason": f"{key}:resolver_inputs_present_without_exact_landing_damage",
                "state": result,
                "events": events,
            }
        damage = max(0, int(damage))
        dealt = min(int(target["hp"]), damage)
        target["hp"] = max(0, int(target["hp"]) - dealt)
        events.append(
            {
                "effect": attack["move"],
                "target_slot": key,
                "target_pokemon_id": target_id,
                "result": "hit",
                "damage": dealt,
                "damage_provenance": resolution.get("provenance"),
                "landing_mode": resolution.get("mode"),
            }
        )
    result["turn"] = int(turn)
    return {"available": True, "reason": None, "state": result, "events": events}


def run_delayed_timeline(initial_state: Dict[str, Any], timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    state = deepcopy(initial_state)
    snapshots: List[Dict[str, Any]] = []
    turn_events: List[List[Dict[str, Any]]] = []
    schedule_results: List[Dict[str, Any]] = []

    for step in timeline:
        turn = int(step["turn"])
        updates = step.get("active_slots")
        if isinstance(updates, dict):
            state.setdefault("active_slots", {}).update(deepcopy(updates))
        attack = step.get("schedule")
        if isinstance(attack, dict):
            scheduled = schedule_delayed_attack(state, attack)
            schedule_results.append(
                {"scheduled": scheduled["scheduled"], "reason": scheduled["reason"], "turn": turn}
            )
            if not scheduled["available"]:
                return {
                    **scheduled,
                    "snapshots": snapshots,
                    "turn_events": turn_events,
                    "schedule_results": schedule_results,
                }
            state = scheduled["state"]
        resolved = resolve_delayed_attacks(state, turn)
        if not resolved["available"]:
            return {
                **resolved,
                "snapshots": snapshots,
                "turn_events": turn_events,
                "schedule_results": schedule_results,
            }
        state = resolved["state"]
        snapshots.append(deepcopy(state))
        turn_events.append(list(resolved["events"]))

    return {
        "available": True,
        "reason": None,
        "state": state,
        "snapshots": snapshots,
        "turn_events": turn_events,
        "events": [event for events in turn_events for event in events],
        "schedule_results": schedule_results,
    }
