from __future__ import annotations

from copy import deepcopy
from math import floor
from typing import Any, Dict, List, Tuple


_SAND_IMMUNE_TYPES = {"rock", "ground", "steel"}
_SAND_IMMUNE_ABILITIES = {
    "magicguard",
    "overcoat",
    "sandforce",
    "sandrush",
    "sandveil",
}


def _to_id(value: Any) -> str:
    return "".join(character for character in str(value or "").lower() if character.isalnum())


def _fraction_damage(max_hp: int, divisor: int) -> int:
    return max(1, floor(max_hp / divisor))


def _damage(mon: Dict[str, Any], amount: int) -> int:
    dealt = min(max(0, int(mon["hp"])), max(0, int(amount)))
    mon["hp"] = max(0, int(mon["hp"]) - dealt)
    return dealt


def _heal(mon: Dict[str, Any], amount: int) -> int:
    healed = min(max(0, int(mon["max_hp"]) - int(mon["hp"])), max(0, int(amount)))
    mon["hp"] = min(int(mon["max_hp"]), int(mon["hp"]) + healed)
    return healed


def _grounded_state(mon: Dict[str, Any]) -> bool | None:
    raw_volatiles = mon.get("volatiles")
    if isinstance(raw_volatiles, dict):
        volatiles = {_to_id(value) for value in raw_volatiles.keys()}
    elif isinstance(raw_volatiles, list):
        volatiles = {_to_id(value) for value in raw_volatiles}
    else:
        volatiles = set()
    item = _to_id(mon.get("item"))
    ability = _to_id(mon.get("ability") or mon.get("base_ability"))
    types = {_to_id(value) for value in mon.get("types", [])} if isinstance(mon.get("types"), list) else set()

    if {"smackdown", "ingrain"} & volatiles or item == "ironball":
        return True
    if {"magnetrise", "telekinesis"} & volatiles or item == "airballoon":
        return False
    if "flying" in types or ability == "levitate":
        return False
    if types:
        return True
    return None


def _validate_mon(side: str, mon: Dict[str, Any]) -> str | None:
    if not isinstance(mon.get("hp"), int) or not isinstance(mon.get("max_hp"), int):
        return f"{side}:integer_hp_and_max_hp_required"
    if int(mon["max_hp"]) <= 0 or not 0 <= int(mon["hp"]) <= int(mon["max_hp"]):
        return f"{side}:invalid_hp_bounds"
    if not bool(mon.get("residual_modifiers_known")):
        return f"{side}:residual_modifier_provenance_unknown"
    return None


def apply_end_of_turn(state: Dict[str, Any]) -> Dict[str, Any]:
    """Apply the focused Gen 9 singles residual subset in Showdown order.

    Supported here: ordinary sandstorm chip, Grassy Terrain healing, Leech Seed
    (order 8), poison/burn/toxic (order 9), and Salt Cure (order 13). Partial
    trapping stays outside this helper until source activity and bound-divisor
    provenance are present.
    """
    result = deepcopy(state)
    combatants = result.get("combatants")
    if not isinstance(combatants, dict) or not combatants:
        return {"available": False, "reason": "combatants_required", "state": result, "events": []}

    for side, mon in combatants.items():
        if not isinstance(mon, dict):
            return {"available": False, "reason": f"{side}:combatant_mapping_required", "state": result, "events": []}
        invalid = _validate_mon(str(side), mon)
        if invalid:
            return {"available": False, "reason": invalid, "state": result, "events": []}

    events: List[Dict[str, Any]] = []
    unsupported: List[str] = []

    # Field residual order 1: ordinary sandstorm chip.
    if _to_id(result.get("weather")) == "sandstorm":
        for side, mon in combatants.items():
            if int(mon["hp"]) <= 0:
                continue
            types = {_to_id(value) for value in mon.get("types", [])} if isinstance(mon.get("types"), list) else set()
            ability = _to_id(mon.get("ability"))
            item = _to_id(mon.get("item"))
            if types & _SAND_IMMUNE_TYPES or ability in _SAND_IMMUNE_ABILITIES or item == "safetygoggles":
                continue
            dealt = _damage(mon, _fraction_damage(int(mon["max_hp"]), 16))
            events.append({"effect": "sandstorm", "target": side, "damage": dealt})

    # Terrain residual healing: Grassy Terrain heals grounded active Pokemon.
    if _to_id(result.get("terrain")) == "grassyterrain":
        for side, mon in combatants.items():
            if int(mon["hp"]) <= 0 or int(mon["hp"]) >= int(mon["max_hp"]):
                continue
            grounded = _grounded_state(mon)
            if grounded is None:
                unsupported.append(f"{side}:grassy_terrain_grounding_required")
                continue
            if not grounded:
                continue
            raw_volatiles = mon.get("volatiles")
            volatile_ids = {_to_id(value) for value in raw_volatiles.keys()} if isinstance(raw_volatiles, dict) else set()
            if "healblock" in volatile_ids:
                unsupported.append(f"{side}:grassy_terrain_heal_modifier")
                continue
            healed = _heal(mon, _fraction_damage(int(mon["max_hp"]), 16))
            if healed:
                events.append({"effect": "grassyterrain", "target": side, "healing": healed})

    # Residual order 8: Leech Seed.
    for side, mon in combatants.items():
        volatile = mon.get("volatiles") if isinstance(mon.get("volatiles"), dict) else {}
        seed = volatile.get("leechseed")
        if not seed or int(mon["hp"]) <= 0:
            continue
        source_side = seed.get("source") if isinstance(seed, dict) else None
        source = combatants.get(source_side)
        if not isinstance(source, dict):
            unsupported.append(f"{side}:leech_seed_source_missing")
            continue
        if int(source["hp"]) <= 0:
            continue
        if _to_id(mon.get("ability")) in {"magicguard", "liquidooze"}:
            unsupported.append(f"{side}:leech_seed_target_modifier")
            continue
        if _to_id(source.get("item")) == "bigroot":
            unsupported.append(f"{source_side}:leech_seed_big_root")
            continue
        dealt = _damage(mon, _fraction_damage(int(mon["max_hp"]), 8))
        healed = _heal(source, dealt)
        events.append({"effect": "leechseed", "target": side, "source": source_side, "damage": dealt, "healing": healed})

    # Residual order 9: major-status residuals.
    for side, mon in combatants.items():
        if int(mon["hp"]) <= 0:
            continue
        status = _to_id(mon.get("status"))
        ability = _to_id(mon.get("ability"))
        if status in {"psn", "tox"} and ability in {"magicguard", "poisonheal"}:
            unsupported.append(f"{side}:{status}_ability_modifier")
            continue
        if status == "brn" and ability in {"magicguard", "heatproof"}:
            unsupported.append(f"{side}:burn_ability_modifier")
            continue
        damage = 0
        if status == "psn":
            damage = _fraction_damage(int(mon["max_hp"]), 8)
        elif status == "brn":
            damage = _fraction_damage(int(mon["max_hp"]), 16)
        elif status == "tox":
            if not isinstance(mon.get("toxic_stage"), int):
                unsupported.append(f"{side}:toxic_stage_required")
                continue
            mon["toxic_stage"] = min(15, max(0, int(mon["toxic_stage"])) + 1)
            damage = _fraction_damage(int(mon["max_hp"]), 16) * int(mon["toxic_stage"])
        if damage:
            dealt = _damage(mon, damage)
            events.append({"effect": status, "target": side, "damage": dealt, "toxic_stage": mon.get("toxic_stage")})

    # Residual order 13: Salt Cure. Binding is deliberately not inferred from a bare
    # partiallytrapped flag because Showdown also needs source activity and the
    # Binding Band-derived divisor.
    for side, mon in combatants.items():
        if int(mon["hp"]) <= 0:
            continue
        volatile = mon.get("volatiles") if isinstance(mon.get("volatiles"), dict) else {}
        if volatile.get("partiallytrapped"):
            unsupported.append(f"{side}:partial_trap_source_activity_and_divisor_required")
        if not volatile.get("saltcure"):
            continue
        if _to_id(mon.get("ability")) == "magicguard":
            unsupported.append(f"{side}:salt_cure_magic_guard")
            continue
        types = {_to_id(value) for value in mon.get("types", [])} if isinstance(mon.get("types"), list) else set()
        divisor = 4 if types & {"water", "steel"} else 8
        dealt = _damage(mon, _fraction_damage(int(mon["max_hp"]), divisor))
        events.append({"effect": "saltcure", "target": side, "damage": dealt, "divisor": divisor})

    if unsupported:
        return {
            "available": False,
            "reason": ";".join(unsupported),
            "state": result,
            "events": events,
        }
    return {"available": True, "reason": None, "state": result, "events": events}


def apply_end_of_turns(state: Dict[str, Any], turns: int) -> Dict[str, Any]:
    current = deepcopy(state)
    snapshots: List[Dict[str, Any]] = []
    all_events: List[List[Dict[str, Any]]] = []
    for _ in range(max(0, int(turns))):
        transition = apply_end_of_turn(current)
        if not transition["available"]:
            return {**transition, "snapshots": snapshots, "turn_events": all_events}
        current = transition["state"]
        snapshots.append(deepcopy(current))
        all_events.append(list(transition["events"]))
    return {
        "available": True,
        "reason": None,
        "state": current,
        "events": [event for turn_events in all_events for event in turn_events],
        "snapshots": snapshots,
        "turn_events": all_events,
    }
