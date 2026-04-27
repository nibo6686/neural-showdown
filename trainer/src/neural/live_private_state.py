import re
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .live_opponent_beliefs import load_randbats_index


_STATUS_TOKENS = ("brn", "par", "psn", "tox", "slp", "frz")


def _status_from_condition(condition: Optional[str]) -> Optional[str]:
    if not condition:
        return None
    text = str(condition)
    for token in _STATUS_TOKENS:
        if re.search(rf"(^|\s){token}($|\s)", text):
            return token
    return None


def _hp_fraction_from_condition(condition: Optional[str]) -> Optional[float]:
    if not condition:
        return None
    text = str(condition)
    if "fnt" in text:
        return 0.0

    percent = re.search(r"(\d+(?:\.\d+)?)%", text)
    if percent:
        return max(0.0, min(1.0, float(percent.group(1)) / 100.0))

    fraction = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", text)
    if fraction:
        denominator = float(fraction.group(2))
        if denominator > 0:
            return max(0.0, min(1.0, float(fraction.group(1)) / denominator))
    return None


def _species_from_details(details: Optional[str]) -> Optional[str]:
    if not details:
        return None
    return str(details).split(",", 1)[0].strip() or None


def _normalize_active_block(request_payload: Dict[str, Any]) -> Dict[str, Any]:
    active = request_payload.get("active")
    if isinstance(active, list) and active:
        first = active[0]
        if isinstance(first, dict):
            return first
    if isinstance(active, dict):
        return active
    return {}


def _normalize_side_block(request_payload: Dict[str, Any]) -> Dict[str, Any]:
    side = request_payload.get("side")
    if isinstance(side, dict):
        return side
    return {}


def _extract_active_moves(active_block: Dict[str, Any]) -> List[Dict[str, Any]]:
    moves = active_block.get("moves")
    if not isinstance(moves, list):
        return []

    result: List[Dict[str, Any]] = []
    for entry in moves:
        if not isinstance(entry, dict):
            continue
        disabled = bool(entry.get("disabled", False))
        result.append(
            {
                "id": entry.get("id"),
                "name": entry.get("move") or entry.get("name") or entry.get("id"),
                "pp": entry.get("pp"),
                "maxpp": entry.get("maxpp"),
                "target": entry.get("target"),
                "disabled": disabled,
                "selectable": not disabled,
                "can_tera": bool(entry.get("canTerastallize") or entry.get("can_terastallize") or False),
                "can_zmove": bool(entry.get("canZMove") or entry.get("can_zmove") or False),
                "can_maxmove": bool(entry.get("canMaxMove") or entry.get("can_maxmove") or False),
                "source": "request",
                "known_from_request": True,
                "inferred": False,
            }
        )
    return result


def _extract_team(side_block: Dict[str, Any]) -> List[Dict[str, Any]]:
    team = side_block.get("pokemon")
    if not isinstance(team, list):
        return []

    result: List[Dict[str, Any]] = []
    for mon in team:
        if not isinstance(mon, dict):
            continue
        condition = mon.get("condition")
        hp_fraction = _hp_fraction_from_condition(condition)
        details = mon.get("details")
        result.append(
            {
                "ident": mon.get("ident"),
                "species": _species_from_details(details),
                "details": details,
                "active": bool(mon.get("active", False)),
                "condition": condition,
                "hp_fraction": hp_fraction,
                "fainted": bool(mon.get("fainted", hp_fraction == 0.0 if hp_fraction is not None else False)),
                "status": _status_from_condition(condition),
                "moves": list(mon.get("moves")) if isinstance(mon.get("moves"), list) else [],
                "item": mon.get("item"),
                "ability": mon.get("ability"),
                "base_ability": mon.get("baseAbility") or mon.get("base_ability"),
                "tera_type": mon.get("teraType") or mon.get("tera_type"),
                "source": "request",
                "known_from_request": True,
                "inferred": False,
            }
        )
    return result


def _normalize_legal_actions(legal_actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for action in legal_actions:
        if not isinstance(action, dict):
            continue
        normalized.append(
            {
                "kind": action.get("kind"),
                "label": action.get("label"),
                "slot": action.get("slot"),
                "disabled": bool(action.get("disabled", False)),
            }
        )
    return normalized


def _infer_player_side(side_block: Dict[str, Any], player_hint: Optional[str]) -> Optional[str]:
    side_id = side_block.get("id") or side_block.get("sideid") or side_block.get("side")
    if isinstance(side_id, str) and side_id in ("p1", "p2"):
        return side_id

    if isinstance(player_hint, str) and player_hint in ("p1", "p2"):
        return player_hint

    return None


def _species_key(species: str) -> str:
    return re.sub(r"[^a-z0-9]", "", species.lower())


def _weighted_distribution(candidates: Sequence[Dict[str, Any]], field: str) -> List[Dict[str, Any]]:
    weights: Counter[str] = Counter()
    total_weight = 0.0
    for candidate in candidates:
        weight = float(candidate.get("weight", 1.0) or 1.0)
        values = candidate.get(field)
        if isinstance(values, list):
            value_list = [str(value) for value in values if str(value)]
        elif values:
            value_list = [str(values)]
        else:
            value_list = []
        if not value_list:
            continue
        share = weight / float(len(value_list))
        for value in value_list:
            weights[value] += share
            total_weight += share
    if total_weight <= 0:
        return []
    return [
        {"value": value, "confidence": float(weight) / total_weight, "source": "randbats"}
        for value, weight in weights.most_common()
    ]


def _randbats_inference_for_species(species: Optional[str], sets_path: Optional[str]) -> Tuple[Dict[str, Any], List[str]]:
    if not species:
        return {}, ["own_active_species_unknown"]
    index, source_path, warnings = load_randbats_index(sets_path=sets_path)
    candidates = index.get(_species_key(species), [])
    if not candidates:
        return (
            {
                "species": species,
                "source": source_path,
                "candidate_count": 0,
                "possible_moves": [],
                "possible_items": [],
                "possible_abilities": [],
                "possible_tera_types": [],
            },
            [*warnings, f"no_randbats_candidates:{species}"],
        )
    return (
        {
            "species": species,
            "source": source_path,
            "candidate_count": len(candidates),
            "possible_moves": _weighted_distribution(candidates, "moves"),
            "possible_items": _weighted_distribution(candidates, "items"),
            "possible_abilities": _weighted_distribution(candidates, "abilities"),
            "possible_tera_types": _weighted_distribution(candidates, "tera_types"),
        },
        list(warnings),
    )


def _apply_randbats_fallback(
    *,
    team: List[Dict[str, Any]],
    active_moves: List[Dict[str, Any]],
    active_species: Optional[str],
    sets_path: Optional[str],
) -> Dict[str, Any]:
    inference, warnings = _randbats_inference_for_species(active_species, sets_path)
    used = bool(inference.get("candidate_count", 0) and active_species)

    if used and not team:
        team.append(
            {
                "ident": active_species,
                "species": active_species,
                "details": active_species,
                "active": True,
                "condition": None,
                "hp_fraction": None,
                "fainted": False,
                "status": None,
                "moves": [],
                "item": None,
                "ability": None,
                "base_ability": None,
                "tera_type": None,
                "source": "randbats",
                "known_from_request": False,
                "inferred": True,
            }
        )

    active_mon = next((mon for mon in team if mon.get("active")), team[0] if team else None)
    if used and isinstance(active_mon, dict):
        active_mon.setdefault("possible_moves", inference.get("possible_moves", []))
        active_mon.setdefault("possible_items", inference.get("possible_items", []))
        active_mon.setdefault("possible_abilities", inference.get("possible_abilities", []))
        active_mon.setdefault("possible_tera_types", inference.get("possible_tera_types", []))
        active_mon["inferred_from_randbats"] = True

    if used and not active_moves:
        active_moves.extend(
            {
                "id": str(move["value"]).lower().replace(" ", ""),
                "name": move["value"],
                "pp": None,
                "maxpp": None,
                "target": None,
                "disabled": False,
                "selectable": True,
                "can_tera": False,
                "can_zmove": False,
                "can_maxmove": False,
                "source": "randbats",
                "known_from_request": False,
                "inferred": True,
                "confidence": float(move.get("confidence", 0.0) or 0.0),
            }
            for move in inference.get("possible_moves", [])
        )

    return {
        "used": used,
        "inference": inference,
        "warnings": warnings,
    }


def extract_private_side_state(
    *,
    request_payload: Optional[Dict[str, Any]],
    legal_actions: List[Dict[str, Any]],
    player_hint: Optional[str] = None,
    active_species_hint: Optional[str] = None,
    sets_path: Optional[str] = None,
) -> Dict[str, Any]:
    request_data = request_payload if isinstance(request_payload, dict) else {}
    side_block = _normalize_side_block(request_data)
    active_block = _normalize_active_block(request_data)

    team = _extract_team(side_block)
    active_moves = _extract_active_moves(active_block)

    active_species = None
    for mon in team:
        if mon.get("active"):
            active_species = mon.get("species")
            break
    if not active_species:
        active_species = active_species_hint

    randbats_fallback = {"used": False, "inference": {}, "warnings": []}
    if active_species and (not team or not active_moves):
        randbats_fallback = _apply_randbats_fallback(
            team=team,
            active_moves=active_moves,
            active_species=active_species,
            sets_path=sets_path,
        )

    force_switch_raw = request_data.get("forceSwitch")
    if isinstance(force_switch_raw, list):
        force_switch = any(bool(v) for v in force_switch_raw)
    else:
        force_switch = bool(force_switch_raw)

    known_from_request = bool(team or active_moves)
    inferred_from_randbats = bool(randbats_fallback.get("used"))
    unknown = []
    if not team:
        unknown.append("own_team")
    if not active_moves:
        unknown.append("own_active_moves")

    return {
        "player_side": _infer_player_side(side_block, player_hint),
        "active_species": active_species,
        "team": team,
        "active_moves": active_moves,
        "force_switch": force_switch,
        "wait": bool(request_data.get("wait", False)),
        "team_preview": bool(request_data.get("teamPreview", request_data.get("team_preview", False))),
        "trapped": bool(request_data.get("trapped", False)),
        "legal_actions": _normalize_legal_actions(legal_actions),
        "known_from_request": known_from_request,
        "inferred_from_randbats": inferred_from_randbats,
        "randbats_inference": randbats_fallback.get("inference", {}),
        "source_warnings": randbats_fallback.get("warnings", []),
        "unknown": unknown,
    }
