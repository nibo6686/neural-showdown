from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


def _to_id(value: Any) -> str:
    return "".join(character for character in str(value or "").lower() if character.isalnum())


def _grounded(mon: Dict[str, Any]) -> Optional[bool]:
    if "grounded" in mon:
        return bool(mon["grounded"])
    volatiles = {_to_id(value) for value in mon.get("volatiles", [])} if isinstance(mon.get("volatiles"), list) else set()
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


def _blocked_by_substitute(move: Dict[str, Any], target: Dict[str, Any]) -> bool:
    volatiles = {_to_id(value) for value in target.get("volatiles", [])} if isinstance(target.get("volatiles"), list) else set()
    has_substitute = bool(target.get("substitute")) or "substitute" in volatiles
    return bool(has_substitute and move.get("blocked_by_substitute"))


def apply_immediate_prevention(state: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the focused click-time prevention subset used by rollout parity.

    This helper only covers deterministic hard-fail checks whose required
    provenance is already present in the provided state. Reflection, redirection,
    and damage/effect execution remain outside this local transition.
    """
    result_state = deepcopy(state)
    attacker = result_state.get("attacker") if isinstance(result_state.get("attacker"), dict) else {}
    target = result_state.get("target") if isinstance(result_state.get("target"), dict) else {}
    move = action if isinstance(action, dict) else {}
    move_id = _to_id(move.get("id") or move.get("name"))
    terrain = _to_id(result_state.get("terrain"))
    priority = move.get("priority")

    if not move_id:
        return {"available": False, "reason": "move_identity_required", "prevented": None, "state": result_state}

    attacker_ability = _to_id(attacker.get("ability") or attacker.get("base_ability"))
    target_ability = _to_id(target.get("ability") or target.get("base_ability"))

    if bool(move.get("explosion_like")) and "damp" in {attacker_ability, target_ability}:
        return {"available": True, "reason": "damp_explosion_prevention", "prevented": True, "state": result_state}

    if terrain == "psychicterrain":
        if priority is None:
            return {"available": False, "reason": "priority_required_for_psychic_terrain", "prevented": None, "state": result_state}
        target_grounded = _grounded(target)
        if target_grounded is None:
            return {"available": False, "reason": "target_grounding_required_for_psychic_terrain", "prevented": None, "state": result_state}
        if int(priority) > 0 and target_grounded:
            return {"available": True, "reason": "psychic_terrain_priority_prevention", "prevented": True, "state": result_state}

    status = _to_id(move.get("status"))
    if status:
        target_grounded = _grounded(target)
        if target_grounded is None and terrain in {"mistyterrain", "electricterrain"}:
            return {"available": False, "reason": "target_grounding_required_for_terrain_status", "prevented": None, "state": result_state}
        if terrain == "mistyterrain" and target_grounded:
            return {"available": True, "reason": "misty_terrain_status_prevention", "prevented": True, "state": result_state}
        if terrain == "electricterrain" and status == "slp" and target_grounded:
            return {"available": True, "reason": "electric_terrain_sleep_prevention", "prevented": True, "state": result_state}

    if _blocked_by_substitute(move, target):
        return {"available": True, "reason": "substitute_target_prevention", "prevented": True, "state": result_state}

    return {"available": True, "reason": None, "prevented": False, "state": result_state}
