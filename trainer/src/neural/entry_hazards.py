from __future__ import annotations

from typing import Any, Dict


_ROCK_EFFECTIVENESS = {
    "bug": 2.0,
    "fighting": 0.5,
    "fire": 2.0,
    "flying": 2.0,
    "ground": 0.5,
    "ice": 2.0,
    "steel": 0.5,
}
_SPIKES_DAMAGE_BY_LAYER = {1: 1.0 / 8.0, 2: 1.0 / 6.0, 3: 1.0 / 4.0}


def _to_id(value: Any) -> str:
    return "".join(character for character in str(value or "").lower() if character.isalnum())


def hazard_switch_transition(target: Dict[str, Any], hazards: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the deterministic entry-hazard subset used by approximate rollout.

    Ability suppression, Gravity, Iron Ball, and Poison-type Toxic Spikes
    absorption are intentionally outside this small local transition.
    """
    item_id = _to_id(target.get("item"))
    boots = item_id == "heavydutyboots"
    hp = float(target.get("hp_fraction") if target.get("hp_fraction") is not None else 1.0)
    types = {str(value).lower() for value in target.get("types", [])} if isinstance(target.get("types"), list) else set()
    ability_id = _to_id(target.get("ability") or target.get("base_ability"))
    grounded = "flying" not in types and ability_id != "levitate"
    damage = 0.0
    poison_risk = False
    speed_drop = False

    if not boots:
        if int(hazards.get("stealthrock", 0) or 0):
            rock_effectiveness = 1.0
            for pokemon_type in types:
                rock_effectiveness *= _ROCK_EFFECTIVENESS.get(pokemon_type, 1.0)
            damage += 0.125 * rock_effectiveness
        if grounded:
            spike_layers = max(0, min(3, int(hazards.get("spikes", 0) or 0)))
            damage += _SPIKES_DAMAGE_BY_LAYER.get(spike_layers, 0.0)
            poison_risk = int(hazards.get("toxicspikes", 0) or 0) > 0
            speed_drop = int(hazards.get("stickyweb", 0) or 0) > 0

    return {
        "boots_prevent_hazards": bool(boots and any(int(value or 0) > 0 for value in hazards.values())),
        "grounded": grounded,
        "switch_hazard_damage": float(min(1.0, damage)),
        "toxic_spikes_poison_risk": bool(poison_risk),
        "sticky_web_speed_drop": bool(speed_drop),
        "faint_on_entry_risk": bool(damage >= hp and hp > 0.0),
    }
