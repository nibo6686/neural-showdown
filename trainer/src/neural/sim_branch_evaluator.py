from typing import Any, Dict, List, Optional, Sequence, Tuple
import json
import os
import numpy as np

from .approx_battle_state import build_approx_battle_state
from . import action_value_search
from .action_features import action_name as normalized_action_name
from .action_features import classify_action_category, load_move_metadata, to_id
from .damage_engine import estimate_action_damage
from .env_client import SimCoreClient, SimCoreError
from .live_private_features import build_live_private_feature_vector
from .value_features import select_trace_step, view_request_from_step


def _parse_seed_from_protocol(protocol_lines: Sequence[str]) -> Optional[Sequence[int]]:
    # Accept several seed encodings: trace-level keys or protocol lines.
    # protocol_lines may contain a line like ">start {..seed..}"
    if not protocol_lines:
        return None
    # If protocol_lines is actually a dict-like trace that contains seed fields, handle it earlier
    try:
        # try to handle when protocol_lines is actually a mapping
        if isinstance(protocol_lines, dict):
            payload = protocol_lines
            for key in ("seed", "start_seed", "battle_seed"):
                if key in payload:
                    seed = payload.get(key)
                    if isinstance(seed, list) and len(seed) == 4:
                        return [int(x) & 0xffff for x in seed]
                    if isinstance(seed, int) or (isinstance(seed, str) and str(seed).isdigit()):
                        s = int(seed)
                        return [s & 0xffff, s & 0xffff, s & 0xffff, s & 0xffff]
    except Exception:
        pass

    for line in protocol_lines:
        s = str(line).strip()
        # attempt to parse JSON payload after ">start "
        if s.startswith(">start "):
            try:
                payload = json.loads(s[len(">start "):])
                for key in ("seed", "start_seed", "battle_seed"):
                    if key in payload:
                        seed = payload.get(key)
                        if isinstance(seed, list) and len(seed) == 4:
                            return [int(x) & 0xffff for x in seed]
                        if isinstance(seed, int) or (isinstance(seed, str) and str(seed).isdigit()):
                            s0 = int(seed)
                            return [s0 & 0xffff, s0 & 0xffff, s0 & 0xffff, s0 & 0xffff]
                # backwards-compat: allow top-level 'seed' as list
                seed = payload.get("seed")
                if isinstance(seed, list) and len(seed) == 4:
                    return [int(x) & 0xffff for x in seed]
            except Exception:
                continue
    return None


def _offset_seed(seed: Sequence[int], delta: int) -> Sequence[int]:
    return [int((seed[0] + delta) & 0xffff), int((seed[1] + delta * 2) & 0xffff), int((seed[2] + delta * 3) & 0xffff), int((seed[3] + delta * 4) & 0xffff)]


def _action_index_to_choice(request: Optional[Dict[str, Any]], index: int) -> Optional[str]:
    if not request:
        return None
    legal = request.get("legal_actions") if isinstance(request.get("legal_actions"), dict) else {}
    actions = legal.get("actions") if isinstance(legal.get("actions"), list) else []
    if not (0 <= index < len(actions)):
        return None
    act = actions[index]
    if not isinstance(act, dict):
        return None
    return act.get("choice")


def _selected_rollout_mode(cfg: Dict[str, Any], has_seed: bool) -> str:
    mode = str(cfg.get("rollout_mode") or os.environ.get("NEURAL_ROLLOUT_MODE") or "auto").strip().lower()
    if mode in ("exact", "approximate"):
        return mode
    return "exact" if has_seed else "approximate"


def _move_metadata(move_name: str) -> Dict[str, Any]:
    metadata, _ = load_move_metadata()
    return metadata.get(to_id(move_name), {}) if move_name else {}


def _not_applicable_switch_damage() -> Dict[str, Any]:
    return {
        "damage_method": "not_applicable_switch",
        "damage_rolls": [],
        "estimated_damage_range": [None, None],
        "average_percent": None,
        "min_percent": None,
        "max_percent": None,
        "estimated_ko_chance": None,
        "ko_chance": None,
        "immune": None,
        "type_effectiveness": None,
        "item_modifier": None,
        "burn_attack_penalty": None,
        "tera_damage_bonus": None,
        "warnings": [],
    }


def _flat_damage_defaults_for_action(action: Dict[str, Any]) -> Dict[str, Any]:
    if classify_action_category(action) == "switch":
        return {
            "damage_method": "not_applicable_switch",
            "damage_rolls": [],
            "average_percent": None,
            "min_percent": None,
            "max_percent": None,
            "ko_chance": None,
            "immune": None,
            "type_effectiveness": None,
            "tera_damage_bonus": None,
        }
    return {
        "damage_method": None,
        "damage_rolls": [],
        "average_percent": None,
        "min_percent": None,
        "max_percent": None,
        "ko_chance": None,
        "immune": None,
        "type_effectiveness": None,
        "tera_damage_bonus": None,
    }


def _type_effectiveness(move_type: Optional[str], target_types: Sequence[str]) -> float:
    if not move_type or not target_types:
        return 0.0
    chart = {
        ("Normal", "Rock"): -0.35,
        ("Normal", "Ghost"): -1.0,
        ("Fire", "Fire"): -0.35,
        ("Fire", "Water"): -0.35,
        ("Fire", "Grass"): 0.45,
        ("Fire", "Ice"): 0.45,
        ("Fire", "Bug"): 0.45,
        ("Fire", "Steel"): 0.45,
        ("Fire", "Fairy"): 0.25,
        ("Water", "Fire"): 0.45,
        ("Water", "Water"): -0.35,
        ("Water", "Grass"): -0.35,
        ("Water", "Ground"): 0.45,
        ("Water", "Rock"): 0.35,
        ("Grass", "Fire"): -0.35,
        ("Grass", "Water"): 0.45,
        ("Grass", "Grass"): -0.35,
        ("Grass", "Ground"): 0.45,
        ("Grass", "Rock"): 0.35,
        ("Electric", "Water"): 0.45,
        ("Electric", "Grass"): -0.35,
        ("Electric", "Flying"): 0.45,
        ("Psychic", "Fighting"): 0.45,
        ("Psychic", "Poison"): 0.45,
        ("Psychic", "Dark"): -1.0,
        ("Dragon", "Dragon"): 0.45,
        ("Dark", "Ghost"): 0.45,
        ("Dark", "Dark"): -0.35,
        ("Dark", "Psychic"): 0.45,
        ("Steel", "Normal"): 0.25,
        ("Steel", "Flying"): 0.25,
        ("Steel", "Rock"): 0.45,
        ("Steel", "Fairy"): 0.45,
        ("Steel", "Ice"): 0.45,
        ("Ground", "Electric"): 0.45,
        ("Ground", "Flying"): -1.0,
        ("Ground", "Fire"): 0.35,
    }
    best = 0.0
    for target_type in target_types:
        best = max(best, chart.get((move_type, target_type), 0.0))
    return best


def _type_multiplier(move_type: Optional[str], target_types: Sequence[str]) -> float:
    if not move_type:
        return 1.0
    chart = {
        ("Electric", "Flying"): 2.0,
        ("Electric", "Water"): 2.0,
        ("Electric", "Ground"): 0.0,
        ("Fire", "Grass"): 2.0,
        ("Fire", "Water"): 0.5,
        ("Water", "Fire"): 2.0,
        ("Water", "Water"): 0.5,
        ("Grass", "Water"): 2.0,
        ("Grass", "Fire"): 0.5,
        ("Dragon", "Fairy"): 0.0,
        ("Poison", "Steel"): 0.0,
        ("Normal", "Ghost"): 0.0,
        ("Fighting", "Ghost"): 0.0,
        ("Psychic", "Dark"): 0.0,
        ("Ground", "Flying"): 0.0,
    }
    multiplier = 1.0
    for target_type in target_types:
        multiplier *= chart.get((str(move_type), str(target_type)), 1.0)
    return float(multiplier)


def _active_private_mon(private_state: Dict[str, Any]) -> Dict[str, Any]:
    team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
    for mon in team:
        if isinstance(mon, dict) and mon.get("active"):
            return mon
    return team[0] if team and isinstance(team[0], dict) else {}


def _opponent_view_mon(approx_state: Dict[str, Any]) -> Dict[str, Any]:
    view = approx_state.get("view") if isinstance(approx_state.get("view"), dict) else {}
    team = view.get("opponent_team") if isinstance(view.get("opponent_team"), list) else []
    return team[0] if team and isinstance(team[0], dict) else {}


def _switch_target_private_mon(action: Dict[str, Any], private_state: Dict[str, Any]) -> Dict[str, Any]:
    label = str(action.get("label") or "").split(":", 1)[-1].strip().lower()
    for mon in private_state.get("team", []) if isinstance(private_state.get("team"), list) else []:
        if isinstance(mon, dict) and label and label == str(mon.get("species") or "").lower():
            return mon
    return {}


def _hazard_switch_diagnostics(action: Dict[str, Any], approx_state: Dict[str, Any]) -> Dict[str, Any]:
    private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
    tactical_state = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
    hazards = (tactical_state.get("own") or {}).get("side_conditions") if isinstance(tactical_state.get("own"), dict) else {}
    target = _switch_target_private_mon(action, private_state)
    item_id = to_id(target.get("item"))
    boots = item_id == "heavydutyboots"
    hp = float(target.get("hp_fraction") if target.get("hp_fraction") is not None else 1.0)
    damage = 0.0
    poison_risk = False
    grounded = True
    types = {str(t).lower() for t in target.get("types", [])} if isinstance(target.get("types"), list) else set()
    if "flying" in types or to_id(target.get("ability") or target.get("base_ability")) == "levitate":
        grounded = False
    if not boots and isinstance(hazards, dict):
        if int(hazards.get("stealthrock", 0) or 0):
            damage += 0.125
        damage += 0.125 * int(hazards.get("spikes", 0) or 0)
        if grounded and int(hazards.get("toxicspikes", 0) or 0):
            poison_risk = True
    if boots:
        damage = 0.0
        poison_risk = False
    return {
        "boots_prevent_hazards": bool(boots and any(int(v or 0) > 0 for v in (hazards or {}).values())),
        "grounded": grounded,
        "switch_hazard_damage": float(min(1.0, damage)),
        "toxic_spikes_poison_risk": poison_risk,
        "faint_on_entry_risk": bool(damage >= hp and hp > 0.0),
    }


def _damage_diagnostics(action: Dict[str, Any], approx_state: Dict[str, Any]) -> Dict[str, Any]:
    action_category = classify_action_category(action)
    if action_category == "switch":
        return _not_applicable_switch_damage()

    calc_exception: Optional[Exception] = None
    try:
        estimate = estimate_action_damage(action=action, approx_state=approx_state)
        min_percent = float(estimate.get("min_percent") or 0.0)
        max_percent = float(estimate.get("max_percent") or 0.0)
        type_effectiveness = estimate.get("type_effectiveness")
        return {
            "damage_method": estimate.get("damage_method"),
            "damage_rolls": list(estimate.get("damage_rolls") or []),
            "estimated_damage_range": [min_percent / 100.0, max_percent / 100.0],
            "average_percent": float(estimate.get("average_percent") or 0.0),
            "min_percent": min_percent,
            "max_percent": max_percent,
            "estimated_ko_chance": float(estimate.get("ko_chance") or 0.0),
            "ko_chance": float(estimate.get("ko_chance") or 0.0),
            "immune": bool(estimate.get("immune")),
            "type_effectiveness": float(type_effectiveness) if type_effectiveness is not None else None,
            "item_modifier": float(estimate.get("item_modifier") or 1.0),
            "burn_attack_penalty": bool(estimate.get("burn_attack_penalty")),
            "tera_damage_bonus": float(estimate.get("tera_damage_bonus") or 0.0),
            "warnings": list(estimate.get("warnings") or []),
        }
    except Exception as exc:
        calc_exception = exc

    kind = str(action.get("kind") or "")
    action_name = normalized_action_name(action)
    move_meta = _move_metadata(action_name)
    move_type = str(move_meta.get("type") or "") or None
    category = str(move_meta.get("category") or "")
    base_power = float(move_meta.get("base_power", 0.0) or 0.0)
    private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
    own = _active_private_mon(private_state)
    opp = _opponent_view_mon(approx_state)
    target_types = [str(value) for value in opp.get("types", [])] if isinstance(opp.get("types"), list) else []
    if not target_types:
        target_types = []
    type_eff = _type_multiplier(move_type, target_types)
    item_modifier = 1.3 if to_id(own.get("item")) == "lifeorb" and base_power > 0 else 1.0
    tactical_state = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
    tactical_own = tactical_state.get("own") if isinstance(tactical_state.get("own"), dict) else {}
    burned = str(own.get("status") or tactical_own.get("active_status") or "").lower() == "brn"
    burn_penalty = bool(burned and str(category).lower() == "physical" and base_power > 0)
    burn_modifier = 0.5 if burn_penalty else 1.0
    tera_bonus = 1.0
    if kind == "move_tera" and str(action.get("tera_type") or private_state.get("active_tera_type") or "").lower() == str(move_type or "").lower():
        tera_bonus = 1.5
    raw_damage = (base_power / 100.0) * type_eff * item_modifier * burn_modifier * tera_bonus
    if str(category).lower() == "status" or base_power <= 0:
        raw_damage = 0.0
    min_damage = max(0.0, raw_damage * 0.85)
    max_damage = max(0.0, raw_damage)
    if to_id(opp.get("item")) == "focussash" and float(opp.get("hp_fraction") or 1.0) >= 1.0 and max_damage >= 1.0:
        max_damage = 0.99
        min_damage = min(min_damage, max_damage)
    target_hp = float(opp.get("hp_fraction") if opp.get("hp_fraction") is not None else 1.0)
    return {
        "damage_method": "non_damaging_move" if str(category).lower() == "status" or base_power <= 0 else "heuristic_fallback",
        "estimated_damage_range": [float(min_damage), float(max_damage)],
        "average_percent": float((min_damage + max_damage) * 50.0),
        "min_percent": float(min_damage * 100.0),
        "max_percent": float(max_damage * 100.0),
        "estimated_ko_chance": 1.0 if max_damage >= target_hp and target_hp > 0.0 else 0.0,
        "ko_chance": 1.0 if max_damage >= target_hp and target_hp > 0.0 else 0.0,
        "immune": False if str(category).lower() == "status" or base_power <= 0 else bool(type_eff == 0.0),
        "type_effectiveness": None if str(category).lower() == "status" or base_power <= 0 else type_eff,
        "item_modifier": item_modifier,
        "burn_attack_penalty": burn_penalty,
        "tera_damage_bonus": float(max(0.0, raw_damage - raw_damage / tera_bonus) * 100.0) if tera_bonus > 1.0 and base_power > 0 else 0.0,
        "warnings": [
            "smogon_calc_failed:"
            f"{type(calc_exception).__name__}:{calc_exception}; "
            f"input_summary={json.dumps({'action': action, 'approx_state_keys': sorted(approx_state.keys())}, sort_keys=True, default=str)}"
        ] if calc_exception is not None else [],
    }


def _speed_diagnostics(action: Dict[str, Any], approx_state: Dict[str, Any]) -> Dict[str, Any]:
    move_meta = _move_metadata(normalized_action_name(action))
    priority = int(move_meta.get("priority", 0) or 0)
    private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
    own_speed = float((_active_private_mon(private_state).get("stats") or {}).get("spe", 0) or 0)
    opp_speed = float((_opponent_view_mon(approx_state).get("stats") or {}).get("spe", 0) or 0)
    tactical_state = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
    trick_room = "trickroom" in set(tactical_state.get("field_effects") or [])
    if priority > 0:
        likely = True
    elif trick_room:
        likely = own_speed <= opp_speed if opp_speed else True
    else:
        likely = own_speed >= opp_speed if opp_speed else False
    return {
        "move_priority": priority,
        "own_speed": own_speed,
        "opponent_speed": opp_speed,
        "trick_room_active": bool(trick_room),
        "likely_moves_first": bool(likely),
    }


def _action_diagnostics(action: Dict[str, Any], approx_state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "damage": _damage_diagnostics(action, approx_state),
        "speed_order": _speed_diagnostics(action, approx_state),
        "switch_hazards": _hazard_switch_diagnostics(action, approx_state) if str(action.get("kind")) == "switch" else {},
        "restrictions": {},
    }


def _empty_diagnostics() -> Dict[str, Any]:
    return {
        "damage": {},
        "speed_order": {},
        "switch_hazards": {},
        "restrictions": {},
    }


def _approximate_action_value(action: Dict[str, Any], approx_state: Dict[str, Any]) -> Tuple[float, List[str]]:
    warnings: List[str] = []
    if bool(action.get("disabled")):
        return -10.0, ["disabled_action"]

    private_state = approx_state.get("private_state") if isinstance(approx_state.get("private_state"), dict) else {}
    tactical_state = approx_state.get("tactical_state") if isinstance(approx_state.get("tactical_state"), dict) else {}
    trace_step = approx_state.get("trace_step") if isinstance(approx_state.get("trace_step"), dict) else {}
    view = approx_state.get("view") if isinstance(approx_state.get("view"), dict) else {}
    request = approx_state.get("request") if isinstance(approx_state.get("request"), dict) else None

    action_name = normalized_action_name(action)
    kind = str(action.get("kind") or "")
    move_meta = _move_metadata(action_name)
    move_type = str(move_meta.get("type") or "") or None
    category = str(move_meta.get("category") or "")
    base_power = float(move_meta.get("base_power", 0.0) or 0.0)
    accuracy = float(move_meta.get("accuracy", 100.0) or 100.0)
    target_types: List[str] = []
    if isinstance(view.get("opponent_team"), list) and view.get("opponent_team"):
        first_opp = view.get("opponent_team")[0]
        if isinstance(first_opp, dict) and isinstance(first_opp.get("types"), list):
            target_types = [str(value) for value in first_opp.get("types") if str(value)]
    if not target_types and isinstance(trace_step.get("opponent_types"), list):
        target_types = [str(value) for value in trace_step.get("opponent_types") if str(value)]

    score = 0.0
    if kind in {"move", "move_tera"}:
        damage_diag = _damage_diagnostics(action, approx_state)
        warnings.extend([str(value) for value in damage_diag.get("warnings", []) if str(value)])
        score += base_power / 120.0
        score += (accuracy - 80.0) / 200.0
        score += _type_effectiveness(move_type, target_types)
        score += float(damage_diag.get("average_percent") or 0.0) / 35.0
        score += float(damage_diag.get("estimated_ko_chance") or 0.0) * 1.2
        if damage_diag.get("immune"):
            score -= 2.5
        if kind == "move_tera":
            score += 0.75 + float(damage_diag.get("tera_damage_bonus") or 0.0) / 50.0
        if category.lower() == "status":
            score -= 0.05
        if bool(move_meta.get("has_boosts")) or to_id(action_name) in {"swordsdance", "nastypot", "calmmind", "bulkup", "dragondance", "quiverdance"}:
            boosts = trace_step.get("p1_boosts") or trace_step.get("boosts") or {}
            attack_stage = int(boosts.get("atk", 0) or 0)
            special_stage = int(boosts.get("spa", 0) or 0)
            defense_stage = max(attack_stage, special_stage)
            if defense_stage >= 6:
                score -= 1.2
                warnings.append("setup_at_cap")
            else:
                score += 0.2
        if any(token in to_id(action_name) for token in ("willowisp", "burn", "sleeppowder", "spore", "toxic", "thunderwave", "stunspore")):
            opp_status = str(trace_step.get("p2_status") or trace_step.get("opponent_status") or "").lower()
            move_id = to_id(action_name)
            
            # Check for specific status move vs existing status no-ops
            if opp_status:
                # Already has status condition
                is_same_status = (
                    (move_id == "thunderwave" and opp_status == "par") or
                    (move_id in {"willowisp", "burn"} and opp_status == "brn") or
                    (move_id in {"toxic", "poison"} and opp_status in {"psn", "tox"}) or
                    (move_id in {"sleeppowder", "spore", "slp"} and opp_status == "slp") or
                    (move_id == "stunspore" and opp_status == "par")
                )
                if is_same_status:
                    # Same status type: strong no-op penalty
                    score -= 1.5
                    warnings.append("status_into_existing_status")
                else:
                    # Different status: immunity or lower priority
                    score -= 1.2
                    warnings.append("status_on_already_statused_target")
            else:
                score += 0.15
        if bool(move_meta.get("has_recovery")) or to_id(action_name) in {"recover", "roost", "synthesis", "slackoff", "softboiled", "rest"}:
            hp_ratio = float(trace_step.get("p1_hp_ratio") or 1.0)
            score += 0.25 if hp_ratio <= 0.5 else -0.15
        if bool(move_meta.get("has_side_condition")) or to_id(action_name) in {"spikes", "stealthrock", "toxicspikes", "stickyweb"}:
            self_conditions = (tactical_state.get("own") or {}).get("side_conditions") if isinstance(tactical_state.get("own"), dict) else {}
            if isinstance(self_conditions, dict) and any(int(self_conditions.get(name, 0) or 0) > 0 for name in ("stealthrock", "spikes", "toxicspikes", "stickyweb")):
                score -= 0.6
                warnings.append("hazard_already_present")
            else:
                score += 0.1
        if bool(move_meta.get("has_self_switch")) or to_id(action_name) in {"uturn", "voltswitch", "flipturn", "partingshot", "teleport"}:
            score += 0.1
        if move_type in {"Fire", "Water", "Grass", "Electric", "Psychic", "Dark", "Dragon", "Steel", "Ground"} and not target_types:
            warnings.append("target_type_unknown")
        own_volatiles = set((tactical_state.get("own") or {}).get("volatiles") or []) if isinstance(tactical_state.get("own"), dict) else set()
        if category.lower() == "status" and "taunt" in own_volatiles:
            score -= 1.0
            warnings.append("taunt_blocks_status")
        if "encore" in own_volatiles:
            warnings.append("encore_active")
        locked = own_volatiles & {"outrage", "rollout", "iceball", "thrash", "petaldance"}
        if locked:
            warnings.append("locked_move_active")
    elif kind == "switch":
        hp_ratio = float(trace_step.get("p1_hp_ratio") or 1.0)
        score -= 0.1
        if hp_ratio <= 0.35:
            score += 0.35
        if bool((tactical_state.get("own") or {}).get("volatiles")):
            score += 0.05
        if bool((tactical_state.get("own") or {}).get("side_conditions")):
            self_hazards = (tactical_state.get("own") or {}).get("side_conditions")
            if isinstance(self_hazards, dict) and any(int(self_hazards.get(name, 0) or 0) > 0 for name in ("stealthrock", "spikes", "toxicspikes", "stickyweb")):
                score -= 0.35
                warnings.append("switch_through_hazards")
        opp_known = (approx_state.get("opponent_belief") or {}).get("opponents") if isinstance(approx_state.get("opponent_belief"), dict) else []
        if opp_known:
            score -= 0.05
    else:
        score -= 0.2

    # Tactical context gives status/pivot/boost moves more shape than raw move metadata alone.
    if kind == "move":
        tactical_bonus = 0.0
        own_state = tactical_state.get("own") if isinstance(tactical_state.get("own"), dict) else {}
        opp_state = tactical_state.get("opponent") if isinstance(tactical_state.get("opponent"), dict) else {}
        if to_id(action_name) in {"willowisp", "toxic", "sleeppowder", "thunderwave", "spore"}:
            if any(int(value or 0) > 0 for value in (opp_state.get("side_conditions") or {}).values()):
                tactical_bonus -= 0.3
        if to_id(action_name) in {"protect", "detect", "spikyshield", "kingsshield", "banefulbunker"}:
            tactical_bonus += 0.1 if float(trace_step.get("p1_hp_ratio") or 1.0) <= 0.5 else -0.1
        if to_id(action_name) in {"swordsdance", "nastyplot", "calmmind", "bulkup", "dragondance", "quiverdance"}:
            tactical_bonus += 0.2 if float(trace_step.get("p1_hp_ratio") or 1.0) > 0.5 else -0.1
        if to_id(action_name) in {"recover", "roost", "synthesis", "slackoff", "softboiled", "rest"}:
            tactical_bonus += 0.15 if float(trace_step.get("p1_hp_ratio") or 1.0) <= 0.5 else -0.05
        if to_id(action_name) in {"uturn", "voltswitch", "flipturn", "partingshot", "teleport"}:
            tactical_bonus += 0.1 if float(trace_step.get("p1_hp_ratio") or 1.0) <= 0.4 else 0.0
        score += tactical_bonus

    return score, warnings


def _approximate_decision_rollout(
    trace: Dict[str, Any],
    step_index: int,
    player_side: str,
    legal_actions: List[Dict[str, Any]],
    *,
    rollout_config: Dict[str, Any],
    value_fn: Optional[callable],
) -> List[Dict[str, Any]]:
    approx_state = build_approx_battle_state(trace, player_side=player_side, legal_actions=legal_actions, step_index=step_index)
    sampled_seed_count = max(1, int(rollout_config.get("rollouts_per_action", 8)))
    rng = np.random.default_rng(abs(hash((trace.get("replay_id"), step_index, player_side))) & 0xFFFFFFFF)
    results: List[Dict[str, Any]] = []

    current_value = None
    try:
        current_value = value_fn(
            approx_state.get("view") or {},
            approx_state.get("request") if isinstance(approx_state.get("request"), dict) else None,
            approx_state.get("protocol_prefix") or [],
            approx_state.get("trace_step") and [approx_state.get("trace_step")] or [],
            approx_state.get("trace_step") or {},
        ) if value_fn is not None else None
    except Exception:
        current_value = None

    opponent_choices = ["attack", "switch", "status", "setup", "protect"]
    opponent_weights = np.asarray([0.42, 0.2, 0.12, 0.1, 0.16], dtype=np.float32)
    opponent_weights = opponent_weights / float(np.sum(opponent_weights))
    opponent_limit = int(rollout_config.get("max_opponent_actions", 3))
    considered_opponents = opponent_choices[: max(1, min(opponent_limit, len(opponent_choices)))]

    for action in legal_actions:
        base_score, approx_warnings = _approximate_action_value(action, approx_state)
        diagnostics = _action_diagnostics(action, approx_state)
        samples: List[float] = []
        top_resulting_states: List[Dict[str, Any]] = []
        for rollout_index in range(sampled_seed_count):
            sampled_opp = rng.choice(opponent_choices, p=opponent_weights)
            noise_scale = 0.12
            if str(action.get("kind")) == "move":
                move_name = normalized_action_name(action)
                move_meta = _move_metadata(move_name)
                accuracy = float(move_meta.get("accuracy", 100.0) or 100.0)
                noise_scale = max(0.05, 0.35 * (1.0 - min(1.0, accuracy / 100.0)))
            sample_value = float(current_value or 0.0) + base_score + float(rng.normal(0.0, noise_scale))
            if sampled_opp in {"attack", "setup"} and str(action.get("kind")) == "switch":
                sample_value -= 0.2
            elif sampled_opp == "switch" and str(action.get("kind")) == "move":
                sample_value += 0.05
            elif sampled_opp == "protect" and to_id(normalized_action_name(action)) in {"swordsdance", "nastyplot", "calmmind"}:
                sample_value -= 0.1
            samples.append(sample_value)
            if len(top_resulting_states) < 3:
                top_resulting_states.append({"rollout_index": rollout_index, "opponent_action": sampled_opp, "value": sample_value})

        label = str(action.get("label") or action.get("choice") or "unknown")
        mean_value = float(np.mean(samples)) if samples else None
        std_value = float(np.std(samples)) if samples else None
        min_value = float(np.min(samples)) if samples else None
        max_value = float(np.max(samples)) if samples else None
        damage_info = diagnostics.get("damage") if isinstance(diagnostics.get("damage"), dict) else {}
        results.append(
            {
                "label": label,
                "action_category": classify_action_category(action),
                "method": "approx_sim_rollout",
                "rollout_mode": "approximate",
                "approximate_state": True,
                "expected_value": mean_value,
                "std_value": std_value,
                "min_value": min_value,
                "max_value": max_value,
                "rollout_count": len(samples),
                "opponent_actions_considered": considered_opponents,
                "top_resulting_states": top_resulting_states,
                "probability_weighted": True,
                "ranker_score": None,
                "policy_prob": None,
                "final_score": mean_value,
                "note": "; ".join(sorted(set(approx_warnings + approx_state.get("warnings", [])))),
                "approximation_warnings": sorted(set(approx_warnings + approx_state.get("warnings", []))),
                "rollout_unavailable_reason": None,
                "rollout_unavailable_details": None,
                "current_value": current_value,
                "diagnostics": diagnostics,
                "damage_method": damage_info.get("damage_method"),
                "damage_rolls": damage_info.get("damage_rolls", []),
                "average_percent": damage_info.get("average_percent"),
                "min_percent": damage_info.get("min_percent"),
                "max_percent": damage_info.get("max_percent"),
                "ko_chance": damage_info.get("ko_chance"),
                "immune": damage_info.get("immune"),
                "type_effectiveness": damage_info.get("type_effectiveness"),
                "tera_damage_bonus": damage_info.get("tera_damage_bonus"),
            }
        )

    return sorted(results, key=lambda item: item.get("final_score", float("-inf")), reverse=True)


def evaluate_actions(
    current_payload: Any,
    player_side: str,
    legal_actions: List[Dict[str, Any]],
    opponent_policy: str = "uniform",
    rollout_config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    cfg = rollout_config or {}
    rollouts_per_action = int(cfg.get("rollouts_per_action", 4))

    trace = None
    step_index = 0
    if isinstance(current_payload, dict):
        trace = current_payload.get("trace") or current_payload.get("trajectory")
        if trace and isinstance(trace, dict) and trace.get("turns"):
            step_index = len(trace.get("turns")) - 1
    else:
        trace = getattr(current_payload, "trace", None) or getattr(current_payload, "trajectory", None)

    if trace is None:
        return []

    value_checkpoint = cfg.get("value_checkpoint")
    value_fn = action_value_search._load_value_fn(value_checkpoint) if value_checkpoint else None

    protocol = trace.get("protocol_log") if isinstance(trace, dict) else None
    # Accept seed from the trace dict itself or from protocol lines
    base_seed = _parse_seed_from_protocol(trace if isinstance(trace, dict) else {}) or _parse_seed_from_protocol(protocol or [])
    rollout_mode = _selected_rollout_mode(cfg, bool(base_seed))

    if rollout_mode == "approximate":
        return _approximate_decision_rollout(
            trace,
            step_index,
            player_side,
            legal_actions,
            rollout_config=cfg,
            value_fn=value_fn,
        )

    sim_command = os.environ.get("NEURAL_SIM_CORE_COMMAND_JSON")
    sim_cwd = os.environ.get("NEURAL_SIM_CORE_CWD")
    if not (sim_command and sim_cwd):
        if rollout_mode == "exact":
            return _trace_fallback(trace, step_index, value_fn, reason="exact_replay_unavailable", details={"message": "sim-core is not configured."}, legal_actions=legal_actions)
        return _approximate_decision_rollout(trace, step_index, player_side, legal_actions, rollout_config=cfg, value_fn=value_fn)
    if not base_seed:
        if rollout_mode == "exact":
            return _trace_fallback(trace, step_index, value_fn, reason="exact_replay_unavailable", details={"message": "trace has no replay seed."}, legal_actions=legal_actions)
        return _approximate_decision_rollout(trace, step_index, player_side, legal_actions, rollout_config=cfg, value_fn=value_fn)

    # try to start client
    try:
        command = json.loads(sim_command)
        client = SimCoreClient(command, sim_cwd)
    except Exception:
        if rollout_mode == "exact":
            return _trace_fallback(trace, step_index, value_fn, reason="exact_replay_unavailable", details={"message": "failed to start sim-core client."}, legal_actions=legal_actions)
        return _approximate_decision_rollout(trace, step_index, player_side, legal_actions, rollout_config=cfg, value_fn=value_fn)

    def _replay_to_step(env_seed: Sequence[int], target_step_idx: int) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Replay the trace up to target_step_idx using env_seed.

        Returns (env_id, last_step_result, diagnostics).
        """
        try:
            env_id = client.create_env(format_name=trace.get("format") or "gen9randombattle", seed=list(env_seed), players={"p1": {"controller": "external"}, "p2": {"controller": "external"}})
            step_res = client.reset(env_id)
            steps_flat = []
            for t in trace.get("turns", []) or []:
                for s in t.get("steps", []) or []:
                    steps_flat.append(s)

            for idx, s in enumerate(steps_flat):
                if idx >= target_step_idx:
                    break
                p1_choice_idx = int(s.get("chosen_action_index") if s.get("chosen_action_index") is not None else s.get("action_index") or -1)
                p2_choice_idx = int(s.get("opponent_chosen_action_index") if s.get("opponent_chosen_action_index") is not None else -1)
                reqs = step_res.get("requests") or {}
                p1_req = reqs.get("p1")
                p2_req = reqs.get("p2")
                p1_choice = _action_index_to_choice(p1_req, p1_choice_idx) if p1_choice_idx is not None and p1_choice_idx >= 0 else None
                p2_choice = _action_index_to_choice(p2_req, p2_choice_idx) if p2_choice_idx is not None and p2_choice_idx >= 0 else None
                choices = {"p1": p1_choice or "default", "p2": p2_choice or "default"}
                try:
                    step_res = client.step(env_id, choices)
                except SimCoreError as e:
                    client_diag_fn = getattr(client, "snapshot_diagnostics", None)
                    diag = {
                        "failed_at_step_index": idx,
                        "attempted_choices": choices,
                        "step_from_trace": s,
                        "client_diagnostics": client_diag_fn() if callable(client_diag_fn) else None,
                        "error": str(e),
                    }
                    return None, None, diag

            client_diag_fn = getattr(client, "snapshot_diagnostics", None)
            return env_id, step_res, {"client_diagnostics": client_diag_fn() if callable(client_diag_fn) else None, "replayed_steps": target_step_idx}
        except SimCoreError as e:
            client_diag_fn = getattr(client, "snapshot_diagnostics", None)
            return None, None, {"client_error": str(e), "client_diagnostics": client_diag_fn() if callable(client_diag_fn) else None}

    # prepare flattened steps and target index
    steps_flat = []
    for t in trace.get("turns", []) or []:
        for s in t.get("steps", []) or []:
            steps_flat.append(s)
    target_step_idx = min(int(step_index), max(0, len(steps_flat) - 1))

    env_id_ref, step_res_ref, env_diag_ref = _replay_to_step(base_seed, target_step_idx)
    if not env_id_ref or not isinstance(step_res_ref, dict) or step_res_ref.get("terminated"):
        try:
            if env_id_ref:
                client.close_env(env_id_ref)
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass
        details = {"reason": "replay_to_state_failed", "env_diag": env_diag_ref}
        if rollout_mode == "exact":
            return _trace_fallback(trace, step_index, value_fn, reason="exact_replay_unavailable", details=details, legal_actions=legal_actions)
        return _approximate_decision_rollout(trace, step_index, player_side, legal_actions, rollout_config=cfg, value_fn=value_fn)

    opponent_req = (step_res_ref.get("requests") or {}).get("p2") if player_side == "p1" else (step_res_ref.get("requests") or {}).get("p1")
    opp_actions = []
    if opponent_req and isinstance(opponent_req.get("legal_actions"), dict):
        for a in (opponent_req.get("legal_actions") or {}).get("actions") or []:
            if isinstance(a, dict):
                opp_actions.append(a)
    if not opp_actions:
        try:
            client.close_env(env_id_ref)
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass
        details = {"reason": "replay_to_state_failed", "env_diag": env_diag_ref, "p2_requests": (step_res_ref.get("requests") or {}).get("p2") if isinstance(step_res_ref, dict) else None}
        if rollout_mode == "exact":
            return _trace_fallback(trace, step_index, value_fn, reason="exact_replay_unavailable", details=details, legal_actions=legal_actions)
        return _approximate_decision_rollout(trace, step_index, player_side, legal_actions, rollout_config=cfg, value_fn=value_fn)

    selected_opps = opp_actions[: int(cfg.get("max_opponent_actions", 3))]

    results: List[Dict[str, Any]] = []
    for action in (legal_actions or []):
        label = str(action.get("label") or action.get("choice") or "unknown")
        action_index = int(action.get("index") or 0)
        player_req = (step_res_ref.get("requests") or {}).get("p1") if player_side == "p1" else (step_res_ref.get("requests") or {}).get("p2")
        player_choice = _action_index_to_choice(player_req, action_index) or "default"

        values: List[float] = []
        details: Dict[str, Any] = {
            "label": label,
            "action_category": classify_action_category(action),
            "method": "exact_sim_rollout",
            "rollout_mode": "exact",
            "approximate_state": False,
            "rollout_count": 0,
            "opponent_actions_considered": [a.get("label") for a in selected_opps],
            "diagnostics": _empty_diagnostics(),
            **_flat_damage_defaults_for_action(action),
        }

        rollout_delta = 1
        for opp in selected_opps:
            opp_idx = int(opp.get("index") if opp.get("index") is not None else 0)
            opp_choice_template = opp.get("choice") or "default"
            for r in range(rollouts_per_action):
                seed = _offset_seed(base_seed, rollout_delta)
                rollout_delta += 1
                env_id, step_res, env_diag = _replay_to_step(seed, target_step_idx)
                if not env_id or not isinstance(step_res, dict):
                    # capture diag info about why this replay failed for this seed
                    details.setdefault("replay_attempts", []).append({"seed": seed, "diag": env_diag})
                    continue
                reqs = step_res.get("requests") or {}
                p_req = reqs.get("p1") if player_side == "p1" else reqs.get("p2")
                o_req = reqs.get("p2") if player_side == "p1" else reqs.get("p1")
                p_choice = _action_index_to_choice(p_req, action_index) or player_choice
                o_choice = _action_index_to_choice(o_req, opp_idx) or opp_choice_template
                try:
                    res = client.step(env_id, {"p1": p_choice, "p2": o_choice})
                except SimCoreError as e:
                    details["rollout_unavailable_reason"] = "forced_action_failed"
                    details.setdefault("replay_attempts", []).append({"seed": seed, "attempted_choices": {"p1": p_choice, "p2": o_choice}, "error": str(e), "client_diag": client.snapshot_diagnostics()})
                    try:
                        client.close_env(env_id)
                    except Exception:
                        pass
                    continue

                try:
                    view, request = view_request_from_step(trace, steps_flat[target_step_idx])
                    protocol = res.get("log_delta") or res.get("omniscient") or []
                    # Prefer calling the value_fn directly with the view/request/protocol
                    if value_fn is not None:
                        try:
                            val = value_fn(view, request, protocol if isinstance(protocol, list) else [], steps_flat[:target_step_idx], steps_flat[target_step_idx])
                        except Exception:
                            details["rollout_unavailable_reason"] = "value_feature_build_failed"
                            val = None
                    else:
                        val = None
                except Exception:
                    details["rollout_unavailable_reason"] = "value_feature_build_failed"
                    val = None

                if val is not None:
                    values.append(float(val))
                details["rollout_count"] += 1
                try:
                    client.close_env(env_id)
                except Exception:
                    pass

        if values:
            details.update({"expected_value": float(np.mean(values)), "std_value": float(np.std(values)), "min_value": float(np.min(values)), "max_value": float(np.max(values))})
        else:
            if details.get("rollout_count", 0) > 0:
                # rollouts were attempted but no value could be produced (e.g., feature build failed).
                details.setdefault("expected_value", None)
                details.setdefault("std_value", None)
                details.setdefault("min_value", None)
                details.setdefault("max_value", None)
                # keep method as exact_sim_rollout but include the unavailable reason
            else:
                fallback = _trace_fallback(trace, step_index, value_fn, reason=details.get("rollout_unavailable_reason"), legal_actions=[action])
                match = next((r for r in fallback if r.get("label") == label), None)
                if match:
                    details.update({"expected_value": match.get("expected_value"), "std_value": match.get("std_value"), "min_value": match.get("min_value"), "max_value": match.get("max_value"), "method": match.get("method") or "transition_proxy"})

        results.append(details)

    try:
        client.close_env(env_id_ref)
    except Exception:
        pass
    try:
        client.close()
    except Exception:
        pass
    return results


def _trace_fallback(
    trace: Dict[str, Any],
    step_index: int,
    value_fn: Optional[callable],
    reason: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    legal_actions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        estimates = action_value_search.evaluate_actions_from_trace(trace, step_index, value_fn=value_fn)
    except Exception as exc:
        # If trace-based evaluator fails, return a rollout_unavailable result per legal action if provided
        exc_info = {"type": type(exc).__name__, "message": str(exc)}
        if legal_actions:
            for a in legal_actions:
                label = str(a.get("label") or a.get("choice") or f"action:{a.get('index',0)}")
                item: Dict[str, Any] = {
                    "label": label,
                    "action_category": classify_action_category(a),
                    "method": "rollout_unavailable",
                    "expected_value": None,
                    "std_value": None,
                    "min_value": None,
                    "max_value": None,
                    "rollout_count": 0,
                    "opponent_actions_considered": [],
                    "top_resulting_states": [],
                    "probability_weighted": False,
                    "ranker_score": None,
                    "policy_prob": None,
                    "final_score": None,
                    "note": None,
                    "diagnostics": _empty_diagnostics(),
                    **_flat_damage_defaults_for_action(a),
                    "rollout_unavailable_reason": reason or "trace_evaluation_failed",
                    "rollout_unavailable_details": {**(details or {}), "exception": exc_info},
                }
                out.append(item)
            return out
        # If no legal actions provided, produce a single generic item
        item: Dict[str, Any] = {
            "label": "unknown",
            "action_category": "unknown",
            "method": "rollout_unavailable",
            "expected_value": None,
            "std_value": None,
            "min_value": None,
            "max_value": None,
            "rollout_count": 0,
            "opponent_actions_considered": [],
            "top_resulting_states": [],
            "probability_weighted": False,
            "ranker_score": None,
            "policy_prob": None,
            "final_score": None,
            "note": None,
            "diagnostics": _empty_diagnostics(),
            "damage_method": None,
            "damage_rolls": [],
            "average_percent": None,
            "min_percent": None,
            "max_percent": None,
            "ko_chance": None,
            "immune": None,
            "type_effectiveness": None,
            "tera_damage_bonus": None,
            "rollout_unavailable_reason": reason or "trace_evaluation_failed",
            "rollout_unavailable_details": {**(details or {}), "exception": exc_info},
        }
        return [item]

    # If no estimates were produced, synthesize rollout_unavailable entries when legal_actions provided
    if not estimates:
        if legal_actions:
            exc_info = {"type": "no_estimates", "message": "trace evaluator returned no action estimates"}
            for a in legal_actions:
                label = str(a.get("label") or a.get("choice") or f"action:{a.get('index',0)}")
                item: Dict[str, Any] = {
                    "label": label,
                    "action_category": classify_action_category(a),
                    "method": "rollout_unavailable",
                    "expected_value": None,
                    "std_value": None,
                    "min_value": None,
                    "max_value": None,
                    "rollout_count": 0,
                    "opponent_actions_considered": [],
                    "top_resulting_states": [],
                    "probability_weighted": False,
                    "ranker_score": None,
                    "policy_prob": None,
                    "final_score": None,
                    "note": None,
                    "diagnostics": _empty_diagnostics(),
                    **_flat_damage_defaults_for_action(a),
                    "rollout_unavailable_reason": reason or "no_trace_estimates",
                    "rollout_unavailable_details": {**(details or {}), "exception": exc_info},
                }
                out.append(item)
            return out
        return out

    for est in estimates:
        src = (est.source or "").lower()
        if src.startswith("trace") or src.startswith("trace_chosen"):
            method = "trace_continuation"
        elif src in ("value_prior_only", "value_prior", "unvisited"):
            method = "transition_proxy"
        else:
            method = src or "trace_continuation"
        item: Dict[str, Any] = {
            "label": est.action_label,
            "action_category": classify_action_category({"label": est.action_label}),
            "method": method,
            "expected_value": est.mean_value,
            "std_value": est.std_value,
            "min_value": None,
            "max_value": None,
            "rollout_count": est.visit_count or 0,
            "opponent_actions_considered": [],
            "top_resulting_states": [],
            "probability_weighted": False,
            "ranker_score": None,
            "policy_prob": est.policy_prior,
            "final_score": est.combined_score,
            "note": est.note,
            "diagnostics": _empty_diagnostics(),
            **_flat_damage_defaults_for_action({"label": est.action_label}),
        }
        if reason:
            item["rollout_unavailable_reason"] = reason
        if details:
            item["rollout_unavailable_details"] = details
        out.append(item)
    return out
