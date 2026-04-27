import math
import re
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


TACTICAL_FEATURE_VERSION = "tactical-state-v1"

TRACKED_VOLATILES = [
    "leechseed",
    "substitute",
    "taunt",
    "encore",
    "torment",
    "confusion",
    "perishsong",
    "protect",
    "trapped",
    "partiallytrapped",
]

TRACKED_SIDE_CONDITIONS = [
    "stealthrock",
    "spikes",
    "toxicspikes",
    "stickyweb",
    "reflect",
    "lightscreen",
    "auroraveil",
    "tailwind",
]

TRACKED_WEATHERS = ["raindance", "sunnyday", "sandstorm", "snow"]
TRACKED_TERRAINS = ["electricterrain", "grassyterrain", "mistyterrain", "psychicterrain"]
TRACKED_FIELD_EFFECTS = ["trickroom"]

ABSORB_ABILITIES_BY_TYPE = {
    "Water": {"dryskin", "waterabsorb", "stormdrain", "desolateland"},
    "Fire": {"flashfire", "primordialsea"},
    "Electric": {"voltabsorb", "motordrive", "lightningrod"},
    "Grass": {"sapsipper"},
}

BLOCKING_ABILITIES_BY_MOVE = {
    "goodasgold": {"status"},
    "magicbounce": {"status"},
    "soundproof": {"sound"},
    "bulletproof": {"bullet"},
    "overcoat": {"powder"},
}

TACTICAL_STATE_FEATURE_NAMES = [
    "own_active_volatile_count_norm",
    "opp_active_volatile_count_norm",
    "own_active_seeded",
    "opp_active_seeded",
    "own_active_substitute",
    "opp_active_substitute",
    "own_active_taunted",
    "opp_active_taunted",
    "own_active_encored",
    "opp_active_encored",
    "own_hazard_layers_norm",
    "opp_hazard_layers_norm",
    "own_stealthrock",
    "opp_stealthrock",
    "own_spikes_layers_norm",
    "opp_spikes_layers_norm",
    "own_toxicspikes_layers_norm",
    "opp_toxicspikes_layers_norm",
    "own_stickyweb",
    "opp_stickyweb",
    "own_screen_count_norm",
    "opp_screen_count_norm",
    "weather_active",
    "terrain_active",
    "trickroom_active",
    "recent_failed_move_count_norm",
    "recent_immune_move_count_norm",
    "recent_healed_target_count_norm",
    "recent_missed_move_count_norm",
    "recent_protected_move_count_norm",
    "recent_target_fainted_count_norm",
    "repeat_action_count_norm",
    "same_move_failed_chain_norm",
    "last_move_failed",
    "last_move_healed_target",
    "own_possible_absorb_ability_known",
    "opp_possible_absorb_ability_known",
]

TACTICAL_ACTION_FEATURE_NAMES = [
    "move_id_bucket_00",
    "move_id_bucket_01",
    "move_id_bucket_02",
    "move_id_bucket_03",
    "move_id_bucket_04",
    "move_id_bucket_05",
    "move_id_bucket_06",
    "move_id_bucket_07",
    "move_id_flag_leechseed",
    "move_id_flag_protect",
    "move_id_flag_substitute",
    "move_id_flag_taunt",
    "move_id_flag_encore",
    "move_id_flag_swordsdance",
    "move_id_flag_nastyplot",
    "move_id_flag_calmmind",
    "move_id_flag_stealthrock",
    "move_id_flag_spikes",
    "move_id_flag_toxicspikes",
    "move_id_flag_rapidspin",
    "move_id_flag_defog",
    "move_id_flag_recovery",
    "move_id_flag_pivot",
    "target_already_seeded",
    "side_already_has_stealth_rock",
    "side_already_has_spikes",
    "side_already_has_toxic_spikes",
    "side_already_has_sticky_web",
    "screen_already_active",
    "active_has_substitute",
    "opponent_has_substitute",
    "move_failed_last_time_used",
    "move_failed_recently",
    "move_immune_recently",
    "move_healed_target_recently",
    "move_protected_recently",
    "move_missed_recently",
    "repeated_same_move_count_norm",
    "same_move_same_target_failed_before",
    "target_known_or_possible_ability_absorbs_move_type",
    "target_known_or_possible_ability_blocks_move_effect",
    "switch_own_hazards_norm",
    "switch_target_hazard_vulnerability",
    "switch_current_active_trapped",
    "switch_current_active_encored",
    "switch_current_active_taunted",
    "switch_current_active_seeded",
    "switch_current_active_repeated_damage_norm",
]


def to_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _side_from_ident(ident: Any) -> Optional[str]:
    match = re.match(r"^(p[12])", str(ident or "").strip())
    return match.group(1) if match else None


def _species_from_ident(ident: Any) -> Optional[str]:
    text = str(ident or "")
    if ": " in text:
        text = text.split(": ", 1)[1]
    species = text.split(",", 1)[0].strip()
    return species or None


def _split(line: str) -> List[str]:
    return str(line).strip().split("|") if str(line).strip().startswith("|") else []


def _effect_id(value: Any) -> str:
    text = str(value or "")
    if ":" in text:
        text = text.split(":", 1)[1]
    return to_id(text)


def _clip(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return low
    if not math.isfinite(number):
        return low
    return max(low, min(high, number))


def _move_type(move_id: str) -> Optional[str]:
    try:
        from .action_features import load_move_metadata

        meta, _ = load_move_metadata()
        move_type = meta.get(to_id(move_id), {}).get("type")
        return str(move_type) if move_type else None
    except Exception:
        return None


def _move_flags(move_id: str) -> List[str]:
    try:
        from .action_features import load_move_metadata

        meta, _ = load_move_metadata()
        raw = meta.get(to_id(move_id), {}).get("flags", [])
        return [to_id(flag) for flag in raw] if isinstance(raw, list) else []
    except Exception:
        return []


def _is_recovery_move(move_id: str) -> bool:
    return to_id(move_id) in {
        "recover",
        "roost",
        "synthesis",
        "slackoff",
        "softboiled",
        "morningsun",
        "moonlight",
        "rest",
        "shoreup",
        "milkdrink",
        "strengthsap",
    }


def _is_pivot_move(move_id: str) -> bool:
    return to_id(move_id) in {"uturn", "voltswitch", "flipturn", "partingshot", "chillyreception", "teleport"}


def _empty_side_state() -> Dict[str, Any]:
    return {
        "active": None,
        "active_species": None,
        "volatiles_by_ident": defaultdict(set),
        "side_conditions": defaultdict(int),
        "known_abilities": {},
        "damage_events_recent": 0,
    }


def _new_move_result() -> Dict[str, int]:
    return {
        "failed": 0,
        "immune": 0,
        "protected": 0,
        "resisted": 0,
        "super_effective": 0,
        "healed_target": 0,
        "missed": 0,
        "target_fainted": 0,
    }


class TacticalStateTracker:
    def __init__(self, recent_window: int = 8) -> None:
        self.turn = 0
        self.sides = {"p1": _empty_side_state(), "p2": _empty_side_state()}
        self.weather: Optional[str] = None
        self.terrain: Optional[str] = None
        self.field_effects: set[str] = set()
        self.last_move_by_side: Dict[str, Optional[Dict[str, Any]]] = {"p1": None, "p2": None}
        self.last_move_any: Optional[Dict[str, Any]] = None
        self.move_results: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(_new_move_result)
        self.failed_pairs: set[Tuple[str, str, str]] = set()
        self.recent_events: Deque[Dict[str, Any]] = deque(maxlen=recent_window)
        self.same_move_chain: Dict[str, Dict[str, Any]] = {
            "p1": {"move": None, "count": 0, "failed_count": 0},
            "p2": {"move": None, "count": 0, "failed_count": 0},
        }
        self.last_result_by_side: Dict[str, Dict[str, int]] = {"p1": _new_move_result(), "p2": _new_move_result()}

    def consume(self, lines: Iterable[str]) -> "TacticalStateTracker":
        for raw_line in lines:
            self.consume_line(str(raw_line))
        return self

    def consume_line(self, raw_line: str) -> None:
        parts = _split(raw_line)
        if len(parts) < 2:
            return
        command = parts[1]
        if command == "turn":
            try:
                self.turn = int(parts[2])
            except (IndexError, ValueError):
                pass
            self.last_result_by_side = {"p1": _new_move_result(), "p2": _new_move_result()}
            return
        if command in ("switch", "drag") and len(parts) >= 4:
            self._handle_switch(parts)
            return
        if command == "move" and len(parts) >= 4:
            self._handle_move(parts)
            return
        if command in ("-start", "-end") and len(parts) >= 4:
            self._handle_volatile(parts)
            return
        if command in ("-sidestart", "-sideend") and len(parts) >= 4:
            self._handle_side_condition(parts)
            return
        if command == "-weather" and len(parts) >= 3:
            self.weather = _effect_id(parts[2]) or None
            return
        if command in ("-fieldstart", "-fieldend") and len(parts) >= 3:
            self._handle_field(parts)
            return
        if command == "-ability" and len(parts) >= 4:
            self._remember_ability(parts[2], parts[3])
            return
        if command in ("-fail", "-immune", "-miss", "-resisted", "-supereffective", "-activate", "-heal", "-damage", "faint"):
            self._handle_result(command, parts)

    def _handle_switch(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        self.sides[side]["active"] = parts[2]
        self.sides[side]["active_species"] = _species_from_ident(parts[3] if len(parts) > 3 else parts[2])
        self.sides[side]["volatiles_by_ident"][parts[2]].clear()

    def _handle_move(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        move_id = to_id(parts[3])
        target = parts[4] if len(parts) > 4 else None
        record = {"side": side, "move": move_id, "target": target, "turn": self.turn}
        self.last_move_by_side[side] = record
        self.last_move_any = record
        chain = self.same_move_chain[side]
        if chain.get("move") == move_id:
            chain["count"] = int(chain.get("count", 0)) + 1
        else:
            chain.update({"move": move_id, "count": 1, "failed_count": 0})

    def _handle_volatile(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        effect = _effect_id(parts[3])
        if side not in self.sides or not effect:
            return
        if not self.sides[side].get("active"):
            self.sides[side]["active"] = parts[2]
            self.sides[side]["active_species"] = _species_from_ident(parts[2])
        if effect in {"protect", "detect", "spikyshield", "kingsshield", "banefulbunker", "silktrap", "burningbulwark"}:
            effect = "protect"
        elif effect in {"partiallytrapped", "bind", "wrap", "firespin", "whirlpool", "sand Tomb"}:
            effect = "partiallytrapped"
        if effect not in TRACKED_VOLATILES:
            return
        volatiles = self.sides[side]["volatiles_by_ident"][parts[2]]
        if parts[1] == "-end":
            volatiles.discard(effect)
        else:
            volatiles.add(effect)

    def _handle_side_condition(self, parts: Sequence[str]) -> None:
        side = parts[2] if parts[2] in self.sides else None
        effect = _effect_id(parts[3])
        if side not in self.sides or effect not in TRACKED_SIDE_CONDITIONS:
            return
        conditions = self.sides[side]["side_conditions"]
        if parts[1] == "-sideend":
            conditions.pop(effect, None)
        elif effect in {"spikes", "toxicspikes"}:
            max_layers = 3 if effect == "spikes" else 2
            conditions[effect] = min(max_layers, int(conditions.get(effect, 0)) + 1)
        else:
            conditions[effect] = 1

    def _handle_field(self, parts: Sequence[str]) -> None:
        effect = _effect_id(parts[2])
        if not effect:
            return
        if effect in TRACKED_TERRAINS:
            self.terrain = None if parts[1] == "-fieldend" else effect
        if effect in TRACKED_FIELD_EFFECTS:
            if parts[1] == "-fieldend":
                self.field_effects.discard(effect)
            else:
                self.field_effects.add(effect)

    def _remember_ability(self, ident: Any, ability: Any) -> None:
        side = _side_from_ident(ident)
        if side in self.sides:
            self.sides[side]["known_abilities"][str(ident)] = to_id(ability)

    def _matching_last_move(self, target: Any, move_hint: Optional[str] = None) -> Optional[Dict[str, Any]]:
        target_text = str(target or "")
        move_id = to_id(move_hint)
        candidates = [record for record in self.last_move_by_side.values() if record]
        if move_id:
            candidates = [record for record in candidates if record.get("move") == move_id]
        for record in reversed(candidates):
            if target_text and str(record.get("target") or "") == target_text:
                return record
        return candidates[-1] if candidates else self.last_move_any

    def _mark_result(self, record: Optional[Dict[str, Any]], key: str, target: Any = None) -> None:
        if not record:
            return
        side = str(record.get("side") or "")
        move_id = str(record.get("move") or "")
        if side not in self.sides or not move_id:
            return
        self.move_results[(side, move_id)][key] += 1
        self.last_result_by_side[side][key] += 1
        event = {"side": side, "move": move_id, "result": key, "turn": self.turn, "target": target or record.get("target")}
        self.recent_events.append(event)
        if key in {"failed", "immune", "protected"}:
            self.failed_pairs.add((side, move_id, str(target or record.get("target") or "")))
            chain = self.same_move_chain[side]
            if chain.get("move") == move_id:
                chain["failed_count"] = int(chain.get("failed_count", 0)) + 1

    def _handle_result(self, command: str, parts: Sequence[str]) -> None:
        target = parts[2] if len(parts) > 2 else None
        move_hint = None
        for part in parts[3:]:
            if str(part).startswith("move:"):
                move_hint = part
                break
        record = self._matching_last_move(target, move_hint)
        if command == "-fail":
            text = "|".join(str(part).lower() for part in parts)
            self._mark_result(record, "protected" if "protect" in text else "failed", target)
        elif command == "-immune":
            self._mark_result(record, "immune", target)
            for part in parts[3:]:
                if "ability:" in str(part).lower():
                    self._remember_ability(target, str(part).split("ability:", 1)[1])
        elif command == "-miss":
            self._mark_result(record, "missed", target)
        elif command == "-resisted":
            self._mark_result(record, "resisted", target)
        elif command == "-supereffective":
            self._mark_result(record, "super_effective", target)
        elif command == "faint":
            self._mark_result(record, "target_fainted", target)
        elif command == "-activate":
            text = "|".join(str(part).lower() for part in parts)
            if "protect" in text:
                self._mark_result(record, "protected", target)
        elif command == "-heal":
            text = "|".join(str(part).lower() for part in parts)
            if "ability:" in text:
                ability = text.split("ability:", 1)[1].split("|", 1)[0]
                self._remember_ability(target, ability)
                move_type = _move_type(str(record.get("move") if record else "")) if record else None
                ability_id = to_id(ability)
                if move_type and ability_id in ABSORB_ABILITIES_BY_TYPE.get(move_type, set()):
                    self._mark_result(record, "healed_target", target)
        elif command == "-damage":
            side = _side_from_ident(target)
            if side in self.sides:
                self.sides[side]["damage_events_recent"] += 1

    def snapshot(self, perspective_side: str = "p1") -> Dict[str, Any]:
        own = perspective_side if perspective_side in ("p1", "p2") else "p1"
        opp = "p2" if own == "p1" else "p1"
        return {
            "feature_version": TACTICAL_FEATURE_VERSION,
            "turn": self.turn,
            "perspective_side": own,
            "own": self._side_snapshot(own),
            "opponent": self._side_snapshot(opp),
            "weather": self.weather,
            "terrain": self.terrain,
            "field_effects": sorted(self.field_effects),
            "recent_events": list(self.recent_events),
            "move_results": {f"{side}:{move}": dict(results) for (side, move), results in self.move_results.items()},
            "same_move_chain": {side: dict(value) for side, value in self.same_move_chain.items()},
            "last_result_by_side": {side: dict(value) for side, value in self.last_result_by_side.items()},
            "failed_pairs": [list(item) for item in sorted(self.failed_pairs)],
        }

    def _side_snapshot(self, side: str) -> Dict[str, Any]:
        state = self.sides[side]
        active = state.get("active")
        volatiles = sorted(state["volatiles_by_ident"].get(active, set())) if active else []
        return {
            "side": side,
            "active": active,
            "active_species": state.get("active_species"),
            "volatiles": volatiles,
            "side_conditions": dict(state["side_conditions"]),
            "known_abilities": dict(state["known_abilities"]),
            "same_move_chain": dict(self.same_move_chain[side]),
            "last_result": dict(self.last_result_by_side[side]),
            "damage_events_recent": int(state.get("damage_events_recent", 0)),
        }


def build_tactical_state(
    protocol_log: Iterable[str],
    *,
    perspective_side: str = "p1",
    through_turn: Optional[int] = None,
) -> Dict[str, Any]:
    lines: List[str] = []
    current_turn = 0
    for raw in protocol_log:
        text = str(raw)
        parts = _split(text)
        if len(parts) >= 3 and parts[1] == "turn":
            try:
                current_turn = int(parts[2])
            except ValueError:
                current_turn = through_turn or current_turn
        if through_turn is not None and current_turn > through_turn:
            break
        lines.append(text)
    return TacticalStateTracker().consume(lines).snapshot(perspective_side=perspective_side)


def _side_condition(side: Dict[str, Any], name: str) -> int:
    conditions = side.get("side_conditions") if isinstance(side.get("side_conditions"), dict) else {}
    return int(conditions.get(name, 0) or 0)


def _volatile(side: Dict[str, Any], name: str) -> bool:
    volatiles = side.get("volatiles") if isinstance(side.get("volatiles"), list) else []
    return name in {to_id(item) for item in volatiles}


def tactical_state_feature_vector(tactical_state: Optional[Dict[str, Any]]) -> np.ndarray:
    state = tactical_state if isinstance(tactical_state, dict) else {}
    own = state.get("own") if isinstance(state.get("own"), dict) else {}
    opp = state.get("opponent") if isinstance(state.get("opponent"), dict) else {}
    recent = state.get("recent_events") if isinstance(state.get("recent_events"), list) else []
    own_conditions = own.get("side_conditions") if isinstance(own.get("side_conditions"), dict) else {}
    opp_conditions = opp.get("side_conditions") if isinstance(opp.get("side_conditions"), dict) else {}
    own_hazards = _side_condition(own, "stealthrock") + _side_condition(own, "spikes") + _side_condition(own, "toxicspikes") + _side_condition(own, "stickyweb")
    opp_hazards = _side_condition(opp, "stealthrock") + _side_condition(opp, "spikes") + _side_condition(opp, "toxicspikes") + _side_condition(opp, "stickyweb")
    own_screens = sum(1 for name in ("reflect", "lightscreen", "auroraveil") if own_conditions.get(name))
    opp_screens = sum(1 for name in ("reflect", "lightscreen", "auroraveil") if opp_conditions.get(name))

    def recent_count(result: str) -> float:
        return _clip(sum(1 for event in recent if event.get("result") == result) / 4.0)

    own_chain = own.get("same_move_chain") if isinstance(own.get("same_move_chain"), dict) else {}
    last = own.get("last_result") if isinstance(own.get("last_result"), dict) else {}
    values = [
        _clip(len(own.get("volatiles", [])) / 10.0),
        _clip(len(opp.get("volatiles", [])) / 10.0),
        float(_volatile(own, "leechseed")),
        float(_volatile(opp, "leechseed")),
        float(_volatile(own, "substitute")),
        float(_volatile(opp, "substitute")),
        float(_volatile(own, "taunt")),
        float(_volatile(opp, "taunt")),
        float(_volatile(own, "encore")),
        float(_volatile(opp, "encore")),
        _clip(own_hazards / 7.0),
        _clip(opp_hazards / 7.0),
        float(bool(own_conditions.get("stealthrock"))),
        float(bool(opp_conditions.get("stealthrock"))),
        _clip(_side_condition(own, "spikes") / 3.0),
        _clip(_side_condition(opp, "spikes") / 3.0),
        _clip(_side_condition(own, "toxicspikes") / 2.0),
        _clip(_side_condition(opp, "toxicspikes") / 2.0),
        float(bool(own_conditions.get("stickyweb"))),
        float(bool(opp_conditions.get("stickyweb"))),
        _clip(own_screens / 3.0),
        _clip(opp_screens / 3.0),
        float(bool(state.get("weather"))),
        float(bool(state.get("terrain"))),
        float("trickroom" in set(state.get("field_effects", []))),
        recent_count("failed"),
        recent_count("immune"),
        recent_count("healed_target"),
        recent_count("missed"),
        recent_count("protected"),
        recent_count("target_fainted"),
        _clip(float(own_chain.get("count", 0) or 0) / 4.0),
        _clip(float(own_chain.get("failed_count", 0) or 0) / 4.0),
        float(bool(last.get("failed") or last.get("immune") or last.get("protected"))),
        float(bool(last.get("healed_target"))),
        float(_side_has_absorb_ability(own)),
        float(_side_has_absorb_ability(opp)),
    ]
    return np.asarray(values, dtype=np.float32)


def _side_has_absorb_ability(side: Dict[str, Any]) -> bool:
    abilities = side.get("known_abilities") if isinstance(side.get("known_abilities"), dict) else {}
    absorb = set().union(*ABSORB_ABILITIES_BY_TYPE.values())
    return any(to_id(value) in absorb for value in abilities.values())


def _recent_result_for_move(state: Dict[str, Any], side: str, move_id: str, result: str) -> bool:
    key = f"{side}:{move_id}"
    move_results = state.get("move_results") if isinstance(state.get("move_results"), dict) else {}
    results = move_results.get(key) if isinstance(move_results.get(key), dict) else {}
    return bool(results.get(result, 0))


def _target_absorbs_move_type(state: Dict[str, Any], move_type: Optional[str], target_side_key: str) -> bool:
    if not move_type:
        return False
    target = state.get(target_side_key) if isinstance(state.get(target_side_key), dict) else {}
    abilities = target.get("known_abilities") if isinstance(target.get("known_abilities"), dict) else {}
    known = {to_id(value) for value in abilities.values()}
    return bool(known & ABSORB_ABILITIES_BY_TYPE.get(move_type, set()))


def _belief_possible_absorbs_move_type(private_state: Dict[str, Any], move_type: Optional[str]) -> bool:
    if not move_type:
        return False
    absorb = ABSORB_ABILITIES_BY_TYPE.get(move_type, set())
    belief = private_state.get("opponent_belief") if isinstance(private_state.get("opponent_belief"), dict) else {}
    opponents = belief.get("opponents") if isinstance(belief.get("opponents"), list) else []
    for opponent in opponents:
        if not isinstance(opponent, dict):
            continue
        revealed = opponent.get("revealed") if isinstance(opponent.get("revealed"), dict) else {}
        if to_id(revealed.get("ability")) in absorb:
            return True
        inferred = opponent.get("inferred") if isinstance(opponent.get("inferred"), dict) else {}
        for entry in inferred.get("abilities", []) if isinstance(inferred.get("abilities"), list) else []:
            value = entry.get("value") if isinstance(entry, dict) else entry
            if to_id(value) in absorb:
                return True
        for candidate in opponent.get("top_candidates", []) if isinstance(opponent.get("top_candidates"), list) else []:
            if not isinstance(candidate, dict):
                continue
            abilities = candidate.get("abilities") if isinstance(candidate.get("abilities"), list) else []
            if any(to_id(ability) in absorb for ability in abilities):
                return True
    return False


def _target_blocks_move_effect(move_id: str, state: Dict[str, Any], target_side_key: str) -> bool:
    target = state.get(target_side_key) if isinstance(state.get(target_side_key), dict) else {}
    abilities = {to_id(value) for value in (target.get("known_abilities") or {}).values()} if isinstance(target.get("known_abilities"), dict) else set()
    flags = set(_move_flags(move_id))
    for ability, blocked in BLOCKING_ABILITIES_BY_MOVE.items():
        if ability not in abilities:
            continue
        if "status" in blocked:
            try:
                from .action_features import load_move_metadata

                meta, _ = load_move_metadata()
                if str(meta.get(move_id, {}).get("category", "")).lower() == "status":
                    return True
            except Exception:
                pass
        if blocked & flags:
            return True
    return False


def tactical_action_feature_vector(
    action: Dict[str, Any],
    *,
    private_state: Optional[Dict[str, Any]] = None,
    tactical_state: Optional[Dict[str, Any]] = None,
    move_id: Optional[str] = None,
    move_type: Optional[str] = None,
) -> np.ndarray:
    state = tactical_state if isinstance(tactical_state, dict) else {}
    private = private_state if isinstance(private_state, dict) else {}
    kind = str(action.get("kind") or "").lower()
    action_move = to_id(move_id or action.get("move") or action.get("label") or action.get("name"))
    if action_move.startswith("move"):
        action_move = to_id(str(action.get("label") or "").split(":", 1)[-1])
    own_side = str(state.get("perspective_side") or private.get("player_side") or "p1")
    opp_side = "p2" if own_side == "p1" else "p1"
    own = state.get("own") if isinstance(state.get("own"), dict) else {}
    opp = state.get("opponent") if isinstance(state.get("opponent"), dict) else {}
    target_conditions = opp.get("side_conditions") if isinstance(opp.get("side_conditions"), dict) else {}
    own_conditions = own.get("side_conditions") if isinstance(own.get("side_conditions"), dict) else {}
    own_chain = own.get("same_move_chain") if isinstance(own.get("same_move_chain"), dict) else {}
    failed_pairs = {
        (str(item[0]), str(item[1]), str(item[2]))
        for item in state.get("failed_pairs", [])
        if isinstance(item, list) and len(item) >= 3
    }
    bucket = sum(ord(ch) for ch in action_move) % 8 if action_move else -1
    move_flags = [
        float(kind.startswith("move") and bucket == index)
        for index in range(8)
    ]
    exact = {
        "leechseed": action_move == "leechseed",
        "protect": action_move in {"protect", "detect", "spikyshield", "kingsshield", "banefulbunker", "silktrap", "burningbulwark"},
        "substitute": action_move == "substitute",
        "taunt": action_move == "taunt",
        "encore": action_move == "encore",
        "swordsdance": action_move == "swordsdance",
        "nastyplot": action_move == "nastyplot",
        "calmmind": action_move == "calmmind",
        "stealthrock": action_move == "stealthrock",
        "spikes": action_move == "spikes",
        "toxicspikes": action_move == "toxicspikes",
        "rapidspin": action_move == "rapidspin",
        "defog": action_move == "defog",
        "recovery": _is_recovery_move(action_move),
        "pivot": _is_pivot_move(action_move),
    }
    target_ref = str((own.get("same_move_chain") or {}).get("target") or "")
    move_type = move_type or _move_type(action_move)
    values = [
        *move_flags,
        *(float(exact[name]) for name in [
            "leechseed",
            "protect",
            "substitute",
            "taunt",
            "encore",
            "swordsdance",
            "nastyplot",
            "calmmind",
            "stealthrock",
            "spikes",
            "toxicspikes",
            "rapidspin",
            "defog",
            "recovery",
            "pivot",
        ]),
        float(kind.startswith("move") and exact["leechseed"] and _volatile(opp, "leechseed")),
        float(kind.startswith("move") and action_move == "stealthrock" and bool(target_conditions.get("stealthrock"))),
        float(kind.startswith("move") and action_move == "spikes" and int(target_conditions.get("spikes", 0) or 0) > 0),
        float(kind.startswith("move") and action_move == "toxicspikes" and int(target_conditions.get("toxicspikes", 0) or 0) > 0),
        float(kind.startswith("move") and action_move == "stickyweb" and bool(target_conditions.get("stickyweb"))),
        float(kind.startswith("move") and action_move in {"reflect", "lightscreen", "auroraveil"} and bool(own_conditions.get(action_move))),
        float(_volatile(own, "substitute")),
        float(_volatile(opp, "substitute")),
        float(kind.startswith("move") and own_chain.get("move") == action_move and bool(own.get("last_result", {}).get("failed"))),
        float(kind.startswith("move") and _recent_result_for_move(state, own_side, action_move, "failed")),
        float(kind.startswith("move") and _recent_result_for_move(state, own_side, action_move, "immune")),
        float(kind.startswith("move") and _recent_result_for_move(state, own_side, action_move, "healed_target")),
        float(kind.startswith("move") and _recent_result_for_move(state, own_side, action_move, "protected")),
        float(kind.startswith("move") and _recent_result_for_move(state, own_side, action_move, "missed")),
        _clip(float(own_chain.get("count", 0) or 0) / 4.0) if own_chain.get("move") == action_move else 0.0,
        float(any(side == own_side and move == action_move and (not target_ref or target == target_ref) for side, move, target in failed_pairs)),
        float(kind.startswith("move") and (_target_absorbs_move_type(state, move_type, "opponent") or _belief_possible_absorbs_move_type(private, move_type))),
        float(kind.startswith("move") and _target_blocks_move_effect(action_move, state, "opponent")),
        _clip((int(own_conditions.get("stealthrock", 0) or 0) + int(own_conditions.get("spikes", 0) or 0) + int(own_conditions.get("toxicspikes", 0) or 0) + int(own_conditions.get("stickyweb", 0) or 0)) / 7.0) if kind == "switch" else 0.0,
        _switch_hazard_vulnerability(action, private) if kind == "switch" else 0.0,
        float(kind == "switch" and _volatile(own, "trapped")),
        float(kind == "switch" and _volatile(own, "encore")),
        float(kind == "switch" and _volatile(own, "taunt")),
        float(kind == "switch" and _volatile(own, "leechseed")),
        _clip(float(own.get("damage_events_recent", 0) or 0) / 4.0) if kind == "switch" else 0.0,
    ]
    return np.asarray(values, dtype=np.float32)


def _switch_hazard_vulnerability(action: Dict[str, Any], private_state: Dict[str, Any]) -> float:
    label = str(action.get("label") or "").split(":", 1)[-1].strip().lower()
    team = private_state.get("team") if isinstance(private_state.get("team"), list) else []
    for mon in team:
        if not isinstance(mon, dict):
            continue
        species = str(mon.get("species") or mon.get("details") or "").lower()
        if label and label not in species:
            continue
        types = [str(value).lower() for value in mon.get("types", [])] if isinstance(mon.get("types"), list) else []
        vulnerable = 1.0
        if "flying" in types or str(mon.get("ability") or mon.get("base_ability") or "").lower() == "levitate":
            vulnerable -= 0.35
        if "poison" in types:
            vulnerable -= 0.15
        if str(mon.get("item") or "").lower().replace("-", "") == "heavydutyboots":
            vulnerable = 0.0
        return _clip(vulnerable)
    return 0.5


def tactical_report_from_state(tactical_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    state = tactical_state if isinstance(tactical_state, dict) else {}
    recent = state.get("recent_events") if isinstance(state.get("recent_events"), list) else []
    return {
        "has_repeated_failed_move": bool((state.get("own") or {}).get("same_move_chain", {}).get("failed_count", 0)),
        "target_already_seeded": bool(_volatile(state.get("opponent") or {}, "leechseed")),
        "move_healed_target": any(event.get("result") == "healed_target" for event in recent),
        "own_active_seeded": bool(_volatile(state.get("own") or {}, "leechseed")),
        "opp_active_seeded": bool(_volatile(state.get("opponent") or {}, "leechseed")),
        "own_active_substitute": bool(_volatile(state.get("own") or {}, "substitute")),
        "opp_active_substitute": bool(_volatile(state.get("opponent") or {}, "substitute")),
        "recent_failed_count": sum(1 for event in recent if event.get("result") in {"failed", "immune", "protected"}),
        "recent_healed_target_count": sum(1 for event in recent if event.get("result") == "healed_target"),
        "recent_events": recent,
    }
