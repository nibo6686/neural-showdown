from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from .provenance_contracts import (
    AbilityKnownness,
    EffectiveItemContext,
    effective_ability_from_state,
    item_belief_from_state,
    item_blocks,
    neutralizing_gas_suppresses_target,
    resolve_status_move_ability_block,
    validate_reflection_provenance,
)


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


def _volatile_ids(mon: Dict[str, Any]) -> set[str]:
    raw = mon.get("volatiles")
    if isinstance(raw, dict):
        return {_to_id(value) for value in raw.keys()}
    if isinstance(raw, list):
        return {_to_id(value) for value in raw}
    return set()


def _opponent_action_category(state: Dict[str, Any]) -> Optional[str]:
    if state.get("opponent_action_category") is not None:
        return _to_id(state.get("opponent_action_category"))
    target_action = state.get("target_action")
    if isinstance(target_action, dict):
        if target_action.get("category") is not None:
            return _to_id(target_action.get("category"))
        if target_action.get("damaging") is not None:
            return "physical" if bool(target_action.get("damaging")) else "status"
    return None


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
    move_type = _to_id(move.get("type"))

    if bool(move.get("explosion_like")) and "damp" in {attacker_ability, target_ability}:
        return {"available": True, "reason": "damp_explosion_prevention", "prevented": True, "state": result_state}

    # Magic Bounce reflection: only routes when the reflector ability is a known,
    # active Magic Bounce and the reflection provenance is complete. Otherwise the
    # caller's fixture stays an explicit GAP; a partial bundle fails closed here.
    if bool(move.get("reflectable")):
        reflector = effective_ability_from_state(target, attacker)
        if reflector.knownness == AbilityKnownness.KNOWN and reflector.ability == "magicbounce":
            reflection = dict(result_state.get("reflection") or {})
            reflection.setdefault("reflectable", True)
            reflection["reflector_ability"] = reflector
            validated = validate_reflection_provenance(reflection)
            if not validated["available"]:
                return {
                    "available": False,
                    "reason": validated["reason"],
                    "prevented": None,
                    "reflected": None,
                    "state": result_state,
                }
            return {
                "available": True,
                "reason": "magic_bounce_reflection",
                "prevented": True,
                "reflected": True,
                "destination_side": validated["destination_side"],
                "state": result_state,
            }

    # A known active Neutralizing Gas suppresses the target ability (e.g. Good as
    # Gold no longer blocks), unless a known Ability Shield protects it.
    if neutralizing_gas_suppresses_target(target, bool(result_state.get("neutralizing_gas_known"))):
        target = {**target, "ability_suppressed": True}

    # Good as Gold: a known-active Good as Gold blocks an opponent status move.
    good_as_gold = resolve_status_move_ability_block(target, attacker, move)
    if good_as_gold is not None and good_as_gold["prevented"]:
        return {
            "available": True,
            "reason": good_as_gold["reason"],
            "prevented": True,
            "blocked": True,
            "state": result_state,
        }

    if "powder" in _volatile_ids(attacker):
        if not move_type:
            return {"available": False, "reason": "move_type_required_for_powder", "prevented": None, "state": result_state}
        if move_type == "fire":
            return {"available": True, "reason": "powder_fire_move_prevention", "prevented": True, "state": result_state}

    # Safety Goggles blocks a powder-flagged move when the target's item is known
    # (bundled Showdown: Safety Goggles `onTryHit` blocks `move.flags['powder']`).
    # An unknown item is never assumed to be Safety Goggles, so it does not block.
    if bool(move.get("powder")):
        goggles = item_blocks(EffectiveItemContext(belief=item_belief_from_state(target)), "safetygoggles")
        if goggles["available"] and goggles["blocks"]:
            return {"available": True, "reason": "safety_goggles_powder_prevention", "prevented": True, "state": result_state}

    if bool(move.get("requires_target_attack")) or move_id in {"suckerpunch", "thunderclap"}:
        category = _opponent_action_category(result_state)
        if category is None:
            return {"available": False, "reason": "opponent_action_branch_required", "prevented": None, "state": result_state}
        if category not in {"physical", "special"}:
            return {"available": True, "reason": "target_not_attacking_branch_prevention", "prevented": True, "state": result_state}

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
