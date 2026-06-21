import math
import re
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path
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
    "outrage",
    "rollout",
    "iceball",
    "thrash",
    "petaldance",
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
    "safeguard",
    "mist",
]

# Slice-5 constraint volatiles tracked in a SEPARATE set so the immutable v2-v6
# `volatiles` list (and every feature vector that reads it) stays byte-identical.
# Taunt/Torment/Encore/Substitute remain in TRACKED_VOLATILES; these three are
# additive move-constraint volatiles surfaced only via `constraint_volatiles`.
CONSTRAINT_ONLY_VOLATILES = ["disable", "healblock", "imprison"]

TRACKED_WEATHERS = ["raindance", "sunnyday", "sandstorm", "snow", "hail"]
TRACKED_TERRAINS = ["electricterrain", "grassyterrain", "mistyterrain", "psychicterrain"]
TRACKED_FIELD_EFFECTS = ["trickroom", "gravity", "magicroom", "wonderroom"]

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


def _tera_type_from_details(details: Any) -> Optional[str]:
    match = re.search(r"(?:^|,\s*)tera:([^,]+)", str(details or ""), flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


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


def _parse_condition(condition: Any) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[str], bool]:
    text = str(condition or "")
    fainted = "fnt" in text.lower()
    status = None
    for token in ("brn", "par", "psn", "tox", "slp", "frz"):
        if re.search(rf"(^|\s){token}($|\s)", text):
            status = token
            break
    match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", text)
    if match:
        hp = float(match.group(1))
        max_hp = float(match.group(2))
        fraction = hp / max_hp if max_hp > 0 else None
        return hp, max_hp, _clip(fraction) if fraction is not None else None, status, fainted or hp <= 0
    percent = re.search(r"(\d+(?:\.\d+)?)%", text)
    if percent:
        hp = float(percent.group(1))
        return hp, 100.0, _clip(hp / 100.0), status, fainted or hp <= 0
    return None, None, 0.0 if fainted else None, status, fainted


@lru_cache(maxsize=1)
def _species_type_index() -> Dict[str, List[str]]:
    root = Path(__file__).resolve().parents[3]
    candidates = [
        root / "sim-core" / "node_modules" / "pokemon-showdown" / "data" / "pokedex.ts",
        Path("sim-core/node_modules/pokemon-showdown/data/pokedex.ts"),
    ]
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        result: Dict[str, List[str]] = {}
        pattern = re.compile(r"\n\s*([a-z0-9]+)\s*:\s*\{")
        position = 0
        while True:
            match = pattern.search(text, position)
            if not match:
                break
            depth = 0
            end = match.end() - 1
            for index in range(end, len(text)):
                if text[index] == "{":
                    depth += 1
                elif text[index] == "}":
                    depth -= 1
                    if depth == 0:
                        end = index + 1
                        break
            block = text[match.end() - 1 : end]
            position = end
            types_match = re.search(r"\btypes\s*:\s*\[([^\]]+)\]", block)
            if types_match:
                result[match.group(1)] = re.findall(r'"([^"]+)"', types_match.group(1))
        return result
    return {}


def _species_types(species: Any) -> List[str]:
    return list(_species_type_index().get(to_id(species), []))


def _team_entry(species: str, *, ident: Optional[str] = None, active: bool = False) -> Dict[str, Any]:
    return {
        "species": species,
        "base_species": species,
        "current_species": species,
        "displayed_species": species,
        "species_source": "protocol",
        "transformed": False,
        "displayed_species_uncertain": False,
        "illusion_revealed": False,
        "ident": ident,
        "active": active,
        "hp_fraction": None,
        "status": None,
        "status_source": "unknown",
        "status_started_turn": None,
        "fainted": False,
        "item": None,
        "last_item": None,
        "item_state": "unknown",
        "item_source": "unknown",
        "ability": None,
        "base_ability": None,
        "ability_state": "unknown",
        "ability_source": "unknown",
        "ability_suppressed": False,
        "tera_type": None,
        "terastallized": False,
        "times_attacked": 0,
        "times_attacked_known": False,
    }


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
        "active_ident": None,
        "active_species": None,
        "active_base_species": None,
        "active_current_species": None,
        "active_displayed_species": None,
        "active_species_source": "unknown",
        "active_transformed": False,
        "active_displayed_species_uncertain": False,
        "active_illusion_revealed": False,
        "active_hp": None,
        "active_max_hp": None,
        "active_hp_fraction": None,
        "active_status": None,
        "active_status_source": "unknown",
        "active_status_started_turn": None,
        "active_fainted": False,
        "active_base_types": [],
        "active_current_types": [],
        "base_type_source": "unknown",
        "current_type_source": "unknown",
        "active_item": None,
        "active_last_item": None,
        "active_item_state": "unknown",
        "active_item_source": "unknown",
        "active_item_suppressed": False,
        "active_base_ability": None,
        "active_current_ability": None,
        "active_ability_state": "unknown",
        "active_ability_source": "unknown",
        "active_ability_suppressed": False,
        "boosts": defaultdict(int),
        "boosts_known": False,
        "volatiles_by_ident": defaultdict(set),
        "constraint_volatiles_by_ident": defaultdict(set),
        "side_conditions": defaultdict(int),
        "side_condition_started": {},
        "known_abilities": {},
        "known_team_by_species": {},
        "fainted_species": set(),
        "total_team_size": 0,
        "revealed_moves_by_species": defaultdict(list),
        "last_move_by_species": {},
        "move_use_counts_by_species": defaultdict(lambda: defaultdict(int)),
        "inferred_pp_by_species_move": defaultdict(dict),
        "exact_pp_by_species_move": defaultdict(dict),
        "item_known": False,
        "ability_known": False,
        "tera_type_known": False,
        "tera_used": False,
        "active_tera_type": None,
        "active_terastallized": False,
        "tera_source": "unknown",
        "tera_availability_state": "unknown",
        "tera_action_available": False,
        "can_tera": False,
        "damage_events_recent": 0,
        "active_times_attacked": 0,
        "active_times_attacked_known": False,
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
        self.field_started: Dict[str, int] = {}
        self.weather_started: Optional[int] = None
        self.terrain_started: Optional[int] = None
        self.same_move_chain: Dict[str, Dict[str, Any]] = {
            "p1": {"move": None, "count": 0, "failed_count": 0},
            "p2": {"move": None, "count": 0, "failed_count": 0},
        }
        self.repeat_chain: Dict[str, Dict[str, Any]] = {
            "p1": self._new_repeat_chain(),
            "p2": self._new_repeat_chain(),
        }
        self.pending_repeat_move: Dict[str, Optional[Dict[str, Any]]] = {"p1": None, "p2": None}
        self.defense_curl_active: Dict[str, bool] = {"p1": False, "p2": False}
        self.last_result_by_side: Dict[str, Dict[str, int]] = {"p1": _new_move_result(), "p2": _new_move_result()}
        self.history_complete = False

    @staticmethod
    def _new_repeat_chain() -> Dict[str, Any]:
        return {
            "move": None,
            "successful_count": 0,
            "known": False,
            "exact": False,
            "provenance": "unknown",
            "reset_observed": False,
        }

    def _reset_repeat_chain(self, side: str, *, observed: bool) -> None:
        previous = self.repeat_chain[side]
        known = bool(self.history_complete)
        self.repeat_chain[side] = {
            "move": None,
            "successful_count": 0,
            "known": known,
            "exact": known,
            "provenance": "protocol_complete" if known else "unknown",
            "reset_observed": bool(observed),
        }
        self.pending_repeat_move[side] = None

    def _finalize_pending_repeat(self, side: str) -> None:
        pending = self.pending_repeat_move.get(side)
        if not pending:
            return
        move_id = str(pending.get("move") or "")
        failed = bool(pending.get("failed"))
        chain = self.repeat_chain[side]
        if failed:
            self._reset_repeat_chain(side, observed=True)
            return
        prior = int(chain.get("successful_count", 0) or 0) if chain.get("move") == move_id else 0
        successful_count = prior + 1
        # The Rollout volatile ends after its fifth successful turn.
        if move_id == "rollout" and successful_count >= 5:
            self._reset_repeat_chain(side, observed=True)
            return
        self.repeat_chain[side] = {
            "move": move_id,
            "successful_count": successful_count,
            "known": bool(self.history_complete),
            "exact": bool(self.history_complete),
            "provenance": "protocol_complete" if self.history_complete else "unknown",
            "reset_observed": False,
        }
        self.pending_repeat_move[side] = None

    def consume(self, lines: Iterable[str]) -> "TacticalStateTracker":
        for raw_line in lines:
            self.consume_line(str(raw_line))
        return self

    def consume_line(self, raw_line: str) -> None:
        parts = _split(raw_line)
        if len(parts) < 2:
            return
        command = parts[1]
        if command == "start":
            self.history_complete = True
            for state in self.sides.values():
                state["boosts_known"] = True
            for side in ("p1", "p2"):
                self.repeat_chain[side].update(
                    {"known": True, "exact": True, "provenance": "protocol_complete"}
                )
            return
        if command == "turn":
            for side in ("p1", "p2"):
                self._finalize_pending_repeat(side)
            try:
                self.turn = int(parts[2])
            except (IndexError, ValueError):
                pass
            self.last_result_by_side = {"p1": _new_move_result(), "p2": _new_move_result()}
            return
        if command == "teamsize" and len(parts) >= 4:
            side = parts[2]
            if side in self.sides:
                try:
                    self.sides[side]["total_team_size"] = int(parts[3])
                except ValueError:
                    pass
            return
        if command in ("switch", "drag") and len(parts) >= 4:
            self._handle_switch(parts)
            return
        if command == "replace" and len(parts) >= 4:
            self._handle_replace(parts)
            return
        if command == "-transform" and len(parts) >= 4:
            self._handle_transform(parts)
            return
        if command == "-formechange" and len(parts) >= 4:
            self._handle_forme_change(parts)
            return
        if command == "move" and len(parts) >= 4:
            self._handle_move(parts)
            return
        if command in ("-start", "-end") and len(parts) >= 4:
            if _effect_id(parts[3]) in {"typechange", "typeadd"}:
                self._handle_type_change(parts)
                return
            self._handle_volatile(parts)
            return
        if command in ("-sidestart", "-sideend") and len(parts) >= 4:
            self._handle_side_condition(parts)
            return
        if command == "-weather" and len(parts) >= 3:
            effect = _effect_id(parts[2])
            is_upkeep = any("[upkeep]" in str(value).lower() for value in parts[3:])
            if effect and (effect != self.weather or not is_upkeep):
                self.weather_started = self.turn
            elif not effect:
                self.weather_started = None
            self.weather = effect or None
            return
        if command in ("-status", "-curestatus") and len(parts) >= 4:
            self._handle_status(parts)
            return
        if command in ("-boost", "-unboost", "-setboost", "-clearboost") and len(parts) >= 3:
            self._handle_boost(command, parts)
            return
        if command == "-terastallize" and len(parts) >= 4:
            self._handle_tera(parts)
            return
        if command in ("-item", "-enditem") and len(parts) >= 4:
            self._handle_item(parts)
            return
        if command in ("-fieldstart", "-fieldend") and len(parts) >= 3:
            self._handle_field(parts)
            return
        if command == "-ability" and len(parts) >= 4:
            self._handle_ability(parts)
            return
        if command == "-endability" and len(parts) >= 3:
            self._handle_end_ability(parts)
            return
        if command in ("-fail", "-immune", "-miss", "-resisted", "-supereffective", "-activate", "-heal", "-damage", "faint"):
            self._handle_result(command, parts)

    def _handle_switch(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        self._reset_repeat_chain(side, observed=True)
        self.defense_curl_active[side] = False
        state = self.sides[side]
        ident = str(parts[2])
        species = _species_from_ident(parts[3] if len(parts) > 3 else parts[2])
        details_tera_type = _tera_type_from_details(parts[3] if len(parts) > 3 else None)
        hp, max_hp, hp_fraction, status, fainted = _parse_condition(parts[4] if len(parts) > 4 else None)
        state["active"] = ident
        state["active_ident"] = ident
        state["active_species"] = species
        state["active_base_species"] = species
        state["active_current_species"] = species
        state["active_displayed_species"] = species
        state["active_species_source"] = "protocol"
        state["active_transformed"] = False
        state["active_displayed_species_uncertain"] = False
        state["active_illusion_revealed"] = False
        state["active_hp"] = hp
        state["active_max_hp"] = max_hp
        state["active_hp_fraction"] = hp_fraction
        state["active_status"] = status
        state["active_status_source"] = "protocol"
        state["active_status_started_turn"] = self.turn if status else None
        state["active_fainted"] = fainted
        base_types = _species_types(species)
        state["active_base_types"] = list(base_types)
        state["active_current_types"] = list(base_types)
        state["base_type_source"] = "species" if base_types else "unknown"
        state["current_type_source"] = "species" if base_types else "unknown"
        entry = state["known_team_by_species"].get(species, {}) if species else {}
        active_tera_type = details_tera_type or entry.get("tera_type")
        active_terastallized = bool(details_tera_type or entry.get("terastallized"))
        state["active_tera_type"] = active_tera_type
        state["active_terastallized"] = active_terastallized
        if active_terastallized:
            state["tera_used"] = True
            state["tera_type_known"] = bool(active_tera_type)
            state["tera_source"] = "protocol"
            state["tera_availability_state"] = "used"
            state["active_current_types"] = [active_tera_type] if active_tera_type else list(base_types)
            state["current_type_source"] = "protocol_tera" if active_tera_type else state["current_type_source"]
        state["active_item"] = entry.get("item")
        state["active_last_item"] = entry.get("last_item")
        state["active_item_state"] = entry.get("item_state", "unknown")
        state["active_item_source"] = entry.get("item_source", "unknown")
        state["active_item_suppressed"] = "magicroom" in self.field_effects
        state["active_base_ability"] = entry.get("base_ability")
        state["active_current_ability"] = entry.get("ability")
        state["active_ability_state"] = entry.get("ability_state", "unknown")
        state["active_ability_source"] = entry.get("ability_source", "unknown")
        state["active_ability_suppressed"] = False
        state["active_times_attacked"] = int(entry.get("times_attacked", 0) or 0)
        state["active_times_attacked_known"] = bool(entry.get("times_attacked_known") or self.history_complete)
        state["boosts"] = defaultdict(int)
        state["boosts_known"] = True
        state["volatiles_by_ident"][ident].clear()
        state["constraint_volatiles_by_ident"][ident].clear()
        if species:
            entry = state["known_team_by_species"].setdefault(species, _team_entry(species, ident=ident))
            entry.update(
                {
                    "ident": ident,
                    "species": species,
                    "base_species": species,
                    "current_species": species,
                    "displayed_species": species,
                    "species_source": "protocol",
                    "active": True,
                    "transformed": False,
                    "displayed_species_uncertain": False,
                    "illusion_revealed": False,
                    "hp_fraction": hp_fraction,
                    "status": status,
                    "status_source": "protocol",
                    "status_started_turn": self.turn if status else None,
                    "fainted": fainted,
                    "tera_type": active_tera_type,
                    "terastallized": active_terastallized,
                    "times_attacked": int(entry.get("times_attacked", 0) or 0),
                    "times_attacked_known": bool(entry.get("times_attacked_known") or self.history_complete),
                }
            )
            state["active_times_attacked"] = int(entry["times_attacked"])
            state["active_times_attacked_known"] = bool(entry["times_attacked_known"])
            for other_species, other in state["known_team_by_species"].items():
                if other_species != species:
                    other["active"] = False
            if fainted:
                state["fainted_species"].add(species)
            state["total_team_size"] = max(int(state.get("total_team_size", 0) or 0), len(state["known_team_by_species"]))

    def _handle_replace(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        state = self.sides[side]
        true_species = _species_from_ident(parts[3])
        if not true_species:
            return
        displayed_species = state.get("active_displayed_species") or state.get("active_species")
        old_entry = state["known_team_by_species"].pop(displayed_species, None) if displayed_species else None
        entry = state["known_team_by_species"].setdefault(
            true_species,
            old_entry or _team_entry(true_species, ident=str(parts[2]), active=True),
        )
        entry.update(
            {
                "species": true_species,
                "base_species": true_species,
                "current_species": true_species,
                "displayed_species": displayed_species or true_species,
                "species_source": "protocol",
                "ident": str(parts[2]),
                "active": True,
                "transformed": False,
                "displayed_species_uncertain": False,
                "illusion_revealed": True,
            }
        )
        state["active_species"] = true_species
        state["active_base_species"] = true_species
        state["active_current_species"] = true_species
        state["active_displayed_species"] = displayed_species or true_species
        state["active_species_source"] = "protocol"
        state["active_transformed"] = False
        state["active_displayed_species_uncertain"] = False
        state["active_illusion_revealed"] = True

    def _handle_transform(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        state = self.sides[side]
        target_side = _side_from_ident(parts[3])
        target_species = (
            self.sides[target_side].get("active_current_species")
            if target_side in self.sides
            else _species_from_ident(parts[3])
        )
        if not target_species:
            return
        state["active_current_species"] = target_species
        state["active_species"] = target_species
        state["active_displayed_species"] = target_species
        state["active_species_source"] = "protocol"
        state["active_transformed"] = True
        base_species = state.get("active_base_species")
        if base_species:
            entry = state["known_team_by_species"].get(base_species)
            if entry:
                entry["current_species"] = target_species
                entry["displayed_species"] = target_species
                entry["transformed"] = True

    def _handle_forme_change(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        state = self.sides[side]
        species = _species_from_ident(parts[3])
        if not species:
            return
        state["active_current_species"] = species
        state["active_species"] = species
        state["active_displayed_species"] = species
        state["active_species_source"] = "protocol"
        base_species = state.get("active_base_species")
        if base_species:
            entry = state["known_team_by_species"].get(base_species)
            if entry:
                entry["current_species"] = species
                entry["displayed_species"] = species

    def _handle_move(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        move_id = to_id(parts[3])
        move_name = str(parts[3])
        target = parts[4] if len(parts) > 4 else None
        record = {"side": side, "move": move_id, "target": target, "turn": self.turn}
        self.last_move_by_side[side] = record
        self.last_move_any = record
        species = (
            self.sides[side].get("active_base_species")
            or self.sides[side].get("active_species")
            or _species_from_ident(parts[2])
        )
        if species:
            revealed = self.sides[side]["revealed_moves_by_species"][species]
            if move_name not in revealed:
                revealed.append(move_name)
            self.sides[side]["last_move_by_species"][species] = move_name
            self.sides[side]["move_use_counts_by_species"][species][move_id] += 1
            uses = int(self.sides[side]["move_use_counts_by_species"][species][move_id])
            self.sides[side]["inferred_pp_by_species_move"][species][move_id] = {
                "observed_uses": uses,
                "provenance": "inferred_from_public_usage",
            }
        chain = self.same_move_chain[side]
        if chain.get("move") == move_id:
            chain["count"] = int(chain.get("count", 0)) + 1
        else:
            chain.update({"move": move_id, "count": 1, "failed_count": 0})
        self._finalize_pending_repeat(side)
        if move_id in {"rollout", "furycutter"}:
            current = self.repeat_chain[side]
            if current.get("move") not in {None, move_id}:
                self._reset_repeat_chain(side, observed=True)
            self.pending_repeat_move[side] = {"move": move_id, "failed": False}
        else:
            self._reset_repeat_chain(side, observed=True)

    def _handle_volatile(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        effect = _effect_id(parts[3])
        if side not in self.sides or not effect:
            return
        if effect == "defensecurl":
            self.defense_curl_active[side] = parts[1] != "-end"
            return
        if not self.sides[side].get("active"):
            self.sides[side]["active"] = parts[2]
            self.sides[side]["active_species"] = _species_from_ident(parts[2])
        if effect in {"protect", "detect", "spikyshield", "kingsshield", "banefulbunker", "silktrap", "burningbulwark"}:
            effect = "protect"
        elif effect in {"partiallytrapped", "bind", "wrap", "firespin", "whirlpool", "sand Tomb"}:
            effect = "partiallytrapped"
        if effect in CONSTRAINT_ONLY_VOLATILES:
            cvol = self.sides[side]["constraint_volatiles_by_ident"][parts[2]]
            if parts[1] == "-end":
                cvol.discard(effect)
            else:
                cvol.add(effect)
            return
        if effect not in TRACKED_VOLATILES:
            return
        volatiles = self.sides[side]["volatiles_by_ident"][parts[2]]
        if parts[1] == "-end":
            volatiles.discard(effect)
        else:
            volatiles.add(effect)

    def _handle_type_change(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        effect = _effect_id(parts[3])
        if side not in self.sides or effect not in {"typechange", "typeadd"}:
            return
        state = self.sides[side]
        if parts[1] == "-end":
            state["active_current_types"] = list(state.get("active_base_types") or [])
            state["current_type_source"] = state.get("base_type_source") or "unknown"
            return
        raw_types = str(parts[4] if len(parts) > 4 else "")
        types = [value.strip() for value in raw_types.split("/") if value.strip()]
        if not types:
            return
        if effect == "typechange":
            state["active_current_types"] = types[:2]
        else:
            current = list(state.get("active_current_types") or state.get("active_base_types") or [])
            for type_name in types:
                if type_name not in current:
                    current.append(type_name)
            state["active_current_types"] = current[:2]
        state["current_type_source"] = "protocol_typechange"

    def _handle_side_condition(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2]) if len(parts) > 2 else None
        effect = _effect_id(parts[3]) if len(parts) > 3 else None
        if side not in self.sides or not effect or effect not in TRACKED_SIDE_CONDITIONS:
            return
        conditions = self.sides[side]["side_conditions"]
        if parts[1] == "-sideend":
            conditions.pop(effect, None)
            self.sides[side]["side_condition_started"].pop(effect, None)
        elif effect in {"spikes", "toxicspikes"}:
            max_layers = 3 if effect == "spikes" else 2
            conditions[effect] = min(max_layers, int(conditions.get(effect, 0)) + 1)
            self.sides[side]["side_condition_started"].setdefault(effect, self.turn)
        else:
            conditions[effect] = 1
            self.sides[side]["side_condition_started"].setdefault(effect, self.turn)

    def _handle_field(self, parts: Sequence[str]) -> None:
        effect = _effect_id(parts[2])
        if not effect:
            return
        if effect in TRACKED_TERRAINS:
            if parts[1] == "-fieldend":
                self.terrain = None
                self.terrain_started = None
            else:
                self.terrain = effect
                self.terrain_started = self.turn
        if effect in TRACKED_FIELD_EFFECTS:
            if parts[1] == "-fieldend":
                self.field_effects.discard(effect)
                self.field_started.pop(effect, None)
            else:
                self.field_effects.add(effect)
                self.field_started.setdefault(effect, self.turn)
        if effect == "magicroom":
            suppressed = parts[1] != "-fieldend"
            for state in self.sides.values():
                state["active_item_suppressed"] = suppressed

    def _handle_status(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        status = None if parts[1] == "-curestatus" else str(parts[3]).lower()
        state = self.sides[side]
        state["active_status"] = status
        state["active_status_source"] = "protocol"
        state["active_status_started_turn"] = self.turn if status else None
        species = state.get("active_base_species") or state.get("active_species") or _species_from_ident(parts[2])
        if species:
            entry = state["known_team_by_species"].setdefault(species, _team_entry(species, ident=str(parts[2])))
            entry["status"] = status
            entry["status_source"] = "protocol"
            entry["status_started_turn"] = self.turn if status else None

    def _handle_boost(self, command: str, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        if command == "-clearboost":
            self.sides[side]["boosts"] = defaultdict(int)
            self.sides[side]["boosts_known"] = True
            return
        if len(parts) < 5:
            return
        stat = to_id(parts[3])
        try:
            amount = int(float(parts[4]))
        except ValueError:
            amount = 0
        boosts = self.sides[side]["boosts"]
        if command == "-setboost":
            boosts[stat] = max(-6, min(6, amount))
            self.sides[side]["boosts_known"] = True
        elif command == "-unboost":
            boosts[stat] = max(-6, int(boosts.get(stat, 0) or 0) - amount)
        else:
            before = int(boosts.get(stat, 0) or 0)
            boosts[stat] = max(-6, min(6, before + amount))

    def _handle_tera(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        tera_type = str(parts[3])
        state = self.sides[side]
        state["tera_used"] = True
        state["active_tera_type"] = tera_type
        state["active_terastallized"] = True
        state["tera_type_known"] = True
        state["tera_source"] = "protocol"
        state["tera_availability_state"] = "used"
        state["tera_action_available"] = False
        state["can_tera"] = False
        state["active_current_types"] = [tera_type] if tera_type else []
        state["current_type_source"] = "protocol_tera" if tera_type else "unknown"
        species = state.get("active_base_species") or state.get("active_species") or _species_from_ident(parts[2])
        if species:
            entry = state["known_team_by_species"].setdefault(species, _team_entry(species, ident=str(parts[2])))
            entry["tera_type"] = tera_type
            entry["terastallized"] = True

    def _handle_item(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        state = self.sides[side]
        item = str(parts[3])
        item_id = to_id(item)
        species = state.get("active_base_species") or state.get("active_species") or _species_from_ident(parts[2])
        entry = state["known_team_by_species"].setdefault(
            species, _team_entry(species, ident=str(parts[2]))
        ) if species else None
        if parts[1] == "-item":
            state["active_item"] = item_id
            state["active_item_state"] = "held"
            state["active_item_source"] = "protocol"
            state["item_known"] = True
            if entry is not None:
                entry.update({"item": item_id, "item_state": "held", "item_source": "protocol"})
            return

        tags = [str(value).lower() for value in parts[4:]]
        consumed = any("[eat]" in value or "[from] gem" in value for value in tags) or not tags
        item_state = "consumed" if consumed else "removed"
        state["active_last_item"] = item_id
        state["active_item"] = None
        state["active_item_state"] = item_state
        state["active_item_source"] = "protocol"
        state["item_known"] = True
        if entry is not None:
            entry.update(
                {
                    "item": None,
                    "last_item": item_id,
                    "item_state": item_state,
                    "item_source": "protocol",
                }
            )

    def _handle_ability(self, parts: Sequence[str]) -> None:
        ident = parts[2]
        side = _side_from_ident(ident)
        if side not in self.sides:
            return
        state = self.sides[side]
        ability = str(parts[3])
        ability_id = to_id(ability)
        changed = any(str(value).lower().startswith("[from]") for value in parts[4:])
        if not state.get("active_base_ability") and not changed:
            state["active_base_ability"] = ability_id
        state["active_current_ability"] = ability_id
        state["active_ability_state"] = "changed" if changed else "known"
        state["active_ability_source"] = "protocol"
        state["active_ability_suppressed"] = False
        self._remember_ability(ident, ability)
        species = state.get("active_base_species") or state.get("active_species") or _species_from_ident(ident)
        if species:
            entry = state["known_team_by_species"].setdefault(
                species, _team_entry(species, ident=str(ident))
            )
            if not entry.get("base_ability") and not changed:
                entry["base_ability"] = ability_id
            entry.update(
                {
                    "ability": ability_id,
                    "ability_state": "changed" if changed else "known",
                    "ability_source": "protocol",
                    "ability_suppressed": False,
                }
            )

    def _handle_end_ability(self, parts: Sequence[str]) -> None:
        side = _side_from_ident(parts[2])
        if side not in self.sides:
            return
        state = self.sides[side]
        state["active_ability_state"] = "suppressed"
        state["active_ability_source"] = "protocol"
        state["active_ability_suppressed"] = True
        species = state.get("active_base_species") or state.get("active_species") or _species_from_ident(parts[2])
        if species:
            entry = state["known_team_by_species"].setdefault(
                species, _team_entry(species, ident=str(parts[2]))
            )
            entry["ability_state"] = "suppressed"
            entry["ability_source"] = "protocol"
            entry["ability_suppressed"] = True

    def _remember_ability(self, ident: Any, ability: Any) -> None:
        side = _side_from_ident(ident)
        if side in self.sides:
            ability_id = to_id(ability)
            self.sides[side]["known_abilities"][str(ident)] = ability_id
            species = (
                self.sides[side].get("active_base_species")
                or self.sides[side].get("active_species")
                or _species_from_ident(ident)
            )
            if species:
                entry = self.sides[side]["known_team_by_species"].setdefault(species, _team_entry(species, ident=str(ident)))
                entry["ability"] = ability
                self.sides[side]["ability_known"] = True

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
        if key in {"failed", "immune", "protected", "missed"}:
            pending = self.pending_repeat_move.get(side)
            if pending and pending.get("move") == move_id:
                pending["failed"] = True
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
            side = _side_from_ident(target)
            if side in self.sides:
                species = (
                    self.sides[side].get("active_base_species")
                    or self.sides[side].get("active_species")
                    or _species_from_ident(target)
                )
                self.sides[side]["active_fainted"] = True
                self.sides[side]["active_hp"] = 0.0
                self.sides[side]["active_hp_fraction"] = 0.0
                if species:
                    self.sides[side]["fainted_species"].add(species)
                    entry = self.sides[side]["known_team_by_species"].setdefault(species, _team_entry(species, ident=str(target)))
                    entry["fainted"] = True
                    entry["hp_fraction"] = 0.0
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
                self._reset_repeat_chain(side, observed=True)
                self.defense_curl_active[side] = False
                self.sides[side]["damage_events_recent"] += 1
                hp, max_hp, hp_fraction, status, fainted = _parse_condition(parts[3] if len(parts) > 3 else None)
                state = self.sides[side]
                if hp is not None:
                    state["active_hp"] = hp
                if max_hp is not None:
                    state["active_max_hp"] = max_hp
                if hp_fraction is not None:
                    state["active_hp_fraction"] = hp_fraction
                if status:
                    state["active_status"] = status
                state["active_fainted"] = bool(fainted)
                species = state.get("active_base_species") or state.get("active_species") or _species_from_ident(target)
                if species:
                    entry = state["known_team_by_species"].setdefault(species, _team_entry(species, ident=str(target)))
                    direct_move_damage = bool(
                        record
                        and record.get("side") != side
                        and str(record.get("target") or "") == str(target or "")
                        and not any(str(value).lower().startswith("[from]") for value in parts[4:])
                    )
                    if direct_move_damage:
                        entry["times_attacked"] = int(entry.get("times_attacked", 0) or 0) + 1
                        entry["times_attacked_known"] = bool(
                            entry.get("times_attacked_known") or self.history_complete
                        )
                        state["active_times_attacked"] = int(entry["times_attacked"])
                        state["active_times_attacked_known"] = bool(entry["times_attacked_known"])
                    if hp_fraction is not None:
                        entry["hp_fraction"] = hp_fraction
                    if status:
                        entry["status"] = status
                    entry["fainted"] = bool(fainted)
                    if fainted:
                        state["fainted_species"].add(species)

    def snapshot(self, perspective_side: str = "p1") -> Dict[str, Any]:
        own = perspective_side if perspective_side in ("p1", "p2") else "p1"
        opp = "p2" if own == "p1" else "p1"
        return {
            "feature_version": TACTICAL_FEATURE_VERSION,
            "history_complete": bool(self.history_complete),
            "turn": self.turn,
            "perspective_side": own,
            "own": self._side_snapshot(own),
            "opponent": self._side_snapshot(opp),
            "weather": self.weather,
            "terrain": self.terrain,
            "field_effects": sorted(self.field_effects),
            "field": {"weather": self.weather, "terrain": self.terrain, "effects": sorted(self.field_effects)},
            "field_durations": self._field_durations(),
            "recent": list(self.recent_events),
            "warnings": self._warnings(),
            "recent_events": list(self.recent_events),
            "move_results": {f"{side}:{move}": dict(results) for (side, move), results in self.move_results.items()},
            "same_move_chain": {side: dict(value) for side, value in self.same_move_chain.items()},
            "repeat_chain": {side: self._repeat_chain_snapshot(side) for side in ("p1", "p2")},
            "last_result_by_side": {side: dict(value) for side, value in self.last_result_by_side.items()},
            "failed_pairs": [list(item) for item in sorted(self.failed_pairs)],
        }

    def snapshot_for_side(self, side: str) -> Dict[str, Any]:
        return self.snapshot(perspective_side=side)

    def _field_durations(self) -> Dict[str, Any]:
        durations = {}
        for effect in sorted(self.field_effects):
            started = int(self.field_started.get(effect, self.turn) or 0)
            durations[effect] = {
                "effect": effect,
                "started_turn": started,
                "turns_since_started": max(0, int(self.turn) - started),
            }
        if self.weather:
            started = int(self.weather_started if self.weather_started is not None else self.turn)
            durations["weather"] = {
                "effect": self.weather,
                "started_turn": started,
                "turns_since_started": max(0, int(self.turn) - started),
            }
        if self.terrain:
            started = int(self.terrain_started if self.terrain_started is not None else self.turn)
            durations["terrain"] = {
                "effect": self.terrain,
                "started_turn": started,
                "turns_since_started": max(0, int(self.turn) - started),
            }
        return durations

    def _warnings(self) -> List[str]:
        warnings = []
        for side, state in self.sides.items():
            for stat, value in (state.get("boosts") or {}).items():
                if int(value or 0) >= 6:
                    warnings.append(f"boost_capped:{side}:{stat}")
        return warnings

    def _repeat_chain_snapshot(self, side: str) -> Dict[str, Any]:
        chain = dict(self.repeat_chain[side])
        move_id = str(chain.get("move") or "")
        count = int(chain.get("successful_count", 0) or 0)
        multiplier = (
            float(2 ** min(count, 4))
            if move_id == "rollout"
            else float(2 ** min(count, 2))
            if move_id == "furycutter"
            else 1.0
        )
        defense_curl = bool(self.defense_curl_active[side])
        if move_id == "rollout" and defense_curl:
            multiplier *= 2.0
        chain.update(
            {
                "multiplier": multiplier,
                "defense_curl_active": defense_curl,
                "defense_curl_known": bool(self.history_complete),
                "forced_continuation_active": bool(move_id == "rollout" and 0 < count < 5),
                "forced_continuation_known": bool(self.history_complete),
            }
        )
        return chain

    def _side_snapshot(self, side: str) -> Dict[str, Any]:
        state = self.sides[side]
        active = state.get("active")
        volatiles = sorted(state["volatiles_by_ident"].get(active, set())) if active else []
        constraint_volatiles = (
            sorted(state["constraint_volatiles_by_ident"].get(active, set())) if active else []
        )
        known_team = []
        for value in state["known_team_by_species"].values():
            entry = dict(value)
            entry["status_turns_public"] = (
                max(0, int(self.turn) - int(entry["status_started_turn"]))
                if entry.get("status") and entry.get("status_started_turn") is not None
                else None
            )
            known_team.append(entry)
        total_team_size = max(int(state.get("total_team_size", 0) or 0), len(known_team))
        remaining = sum(1 for mon in known_team if not mon.get("fainted"))
        side_durations = {}
        for effect, started in (state.get("side_condition_started") or {}).items():
            side_durations[effect] = {
                "effect": effect,
                "started_turn": int(started),
                "turns_since_started": max(0, int(self.turn) - int(started)),
            }
        revealed = {species: list(moves) for species, moves in state["revealed_moves_by_species"].items()}
        move_counts = {species: dict(counts) for species, counts in state["move_use_counts_by_species"].items()}
        inferred_pp = {species: dict(moves) for species, moves in state["inferred_pp_by_species_move"].items()}
        exact_pp = {species: dict(moves) for species, moves in state["exact_pp_by_species_move"].items()}
        for mon in known_team:
            species = mon.get("species")
            if species:
                revealed.setdefault(species, [])
                move_counts.setdefault(species, {})
                inferred_pp.setdefault(species, {})
                exact_pp.setdefault(species, {})
        return {
            "side": side,
            "active": active,
            "active_ident": state.get("active_ident") or active,
            "active_species": state.get("active_species"),
            "active_base_species": state.get("active_base_species"),
            "active_current_species": state.get("active_current_species"),
            "active_displayed_species": state.get("active_displayed_species"),
            "active_species_source": state.get("active_species_source") or "unknown",
            "active_transformed": bool(state.get("active_transformed")),
            "active_displayed_species_uncertain": bool(state.get("active_displayed_species_uncertain")),
            "active_illusion_revealed": bool(state.get("active_illusion_revealed")),
            "active_hp": state.get("active_hp"),
            "active_max_hp": state.get("active_max_hp"),
            "active_hp_fraction": state.get("active_hp_fraction"),
            "active_status": state.get("active_status"),
            "status": state.get("active_status"),
            "active_status_source": state.get("active_status_source") or "unknown",
            "active_status_turns_public": (
                max(0, int(self.turn) - int(state["active_status_started_turn"]))
                if state.get("active_status") and state.get("active_status_started_turn") is not None
                else None
            ),
            "active_fainted": bool(state.get("active_fainted")),
            "active_base_types": list(state.get("active_base_types") or []),
            "active_current_types": list(state.get("active_current_types") or []),
            "base_type_source": state.get("base_type_source") or "unknown",
            "current_type_source": state.get("current_type_source") or "unknown",
            "active_item": state.get("active_item"),
            "active_last_item": state.get("active_last_item"),
            "active_item_state": state.get("active_item_state") or "unknown",
            "active_item_source": state.get("active_item_source") or "unknown",
            "active_item_suppressed": bool(state.get("active_item_suppressed")),
            "active_base_ability": state.get("active_base_ability"),
            "active_current_ability": state.get("active_current_ability"),
            "active_ability_state": state.get("active_ability_state") or "unknown",
            "active_ability_source": state.get("active_ability_source") or "unknown",
            "active_ability_suppressed": bool(state.get("active_ability_suppressed")),
            "active_times_attacked": int(state.get("active_times_attacked", 0) or 0),
            "active_times_attacked_known": bool(state.get("active_times_attacked_known")),
            "boosts": dict(state.get("boosts") or {}),
            "boosts_known": bool(state.get("boosts_known")),
            "volatiles": volatiles,
            "constraint_volatiles": constraint_volatiles,
            "side_conditions": dict(state["side_conditions"]),
            "side_condition_durations": side_durations,
            "known_abilities": dict(state["known_abilities"]),
            "known_team": known_team,
            "fainted_species": sorted(state.get("fainted_species") or []),
            "remaining_known_count": remaining,
            "total_team_size": total_team_size,
            "unknown_unrevealed_count": max(0, total_team_size - len(known_team)),
            "revealed_moves_by_species": revealed,
            "last_move_by_species": dict(state["last_move_by_species"]),
            "move_use_counts_by_species": move_counts,
            "inferred_pp_by_species_move": inferred_pp,
            "exact_pp_by_species_move": exact_pp,
            "item_known": bool(state.get("item_known")),
            "ability_known": bool(state.get("ability_known") or state.get("known_abilities")),
            "tera_type_known": bool(state.get("tera_type_known")),
            "tera_used": bool(state.get("tera_used")),
            "active_tera_type": state.get("active_tera_type"),
            "active_terastallized": bool(state.get("active_terastallized")),
            "tera_source": state.get("tera_source") or "unknown",
            "tera_availability_state": state.get("tera_availability_state") or "unknown",
            "tera_action_available": bool(state.get("tera_action_available")),
            "can_tera": bool(state.get("can_tera")),
            "same_move_chain": dict(self.same_move_chain[side]),
            "repeat_chain": self._repeat_chain_snapshot(side),
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


def _private_move_key(move):
    return str(move.get("id") or move.get("name") or "").replace(" ", "").lower()

def snapshot_with_private_state(snapshot, private_state):
    """Overlay exact live request/private-side data onto a tactical snapshot.

    This keeps live_private_features importing from tactical_state while preserving
    public/replay snapshot fields.
    """
    import copy

    merged = copy.deepcopy(snapshot) if isinstance(snapshot, dict) else {}
    ps = private_state or {}
    if isinstance(ps, dict) and isinstance(ps.get("private_state"), dict):
        ps = ps["private_state"]

    own = merged.setdefault("own", {})
    team = ps.get("team") or []
    active = next((m for m in team if m.get("active")), None)
    active_is_private = bool(
        active
        and (
            active.get("known_from_request")
            or active.get("source") == "request"
            or (not active.get("inferred") and active.get("source") != "randbats")
        )
    )

    if ps.get("active_species"):
        own["active_species"] = ps.get("active_species")
    elif active:
        own["active_species"] = active.get("species")
    if active_is_private:
        request_species = active.get("species")
        own["active_base_species"] = request_species or own.get("active_base_species")
        if not own.get("active_transformed"):
            own["active_current_species"] = request_species or own.get("active_current_species")
            own["active_displayed_species"] = request_species or own.get("active_displayed_species")
        own["active_species_source"] = "request"
        own["active_displayed_species_uncertain"] = False
    if own.get("active_species") and not own.get("active_base_types"):
        species_types = _species_types(own.get("active_species"))
        if species_types:
            own["active_base_types"] = list(species_types)
            own["base_type_source"] = "species"
            if own.get("current_type_source") in {None, "", "unknown"}:
                own["active_current_types"] = list(species_types)
                own["current_type_source"] = "species"

    if active:
        own["active_ident"] = active.get("ident", own.get("active_ident"))
        own["active_hp_fraction"] = active.get("hp_fraction", own.get("active_hp_fraction"))
        own["active_fainted"] = bool(active.get("fainted", own.get("active_fainted", False)))
        own["item_known"] = bool(active.get("item") or own.get("item_known"))
        own["ability_known"] = bool(active.get("ability") or active.get("base_ability") or own.get("ability_known"))
        if active_is_private:
            own["active_tera_type"] = active.get("tera_type", own.get("active_tera_type"))
            own["active_terastallized"] = bool(
                active.get("terastallized", own.get("active_terastallized", False))
            )
            own["tera_type_known"] = bool(active.get("tera_type") or own.get("tera_type_known"))
            prior_status = own.get("active_status")
            own["active_status"] = active.get("status")
            own["status"] = own.get("active_status")
            own["active_status_source"] = "request"
            if own.get("active_status") != prior_status:
                own["active_status_turns_public"] = None
            own["active_item"] = to_id(active.get("item")) or None
            own["active_last_item"] = to_id(active.get("last_item")) or own.get("active_last_item")
            if own.get("active_item_state") not in {"removed", "consumed"}:
                own["active_item_state"] = (
                    str(active.get("item_state"))
                    if active.get("item_state")
                    else "held" if active.get("item") else "none"
                )
                own["active_item_source"] = "request"
            own["active_base_ability"] = to_id(active.get("base_ability")) or None
            own["active_current_ability"] = to_id(active.get("ability") or active.get("base_ability")) or None
            if not own.get("active_ability_suppressed"):
                own["active_ability_state"] = (
                    str(active.get("ability_state"))
                    if active.get("ability_state")
                    else "known" if own["active_current_ability"] else "none"
                )
                own["active_ability_source"] = "request"
        private_types = [str(value) for value in (active.get("types") or []) if str(value)]
        if private_types:
            own["active_base_types"] = list(private_types[:2])
            own["base_type_source"] = "request"
            if own.get("current_type_source") not in {"protocol_typechange", "protocol_tera"}:
                own["active_current_types"] = list(private_types[:2])
                own["current_type_source"] = "request"
        if own.get("active_terastallized") and own.get("active_tera_type"):
            own["active_current_types"] = [str(own["active_tera_type"])]
            own["current_type_source"] = "protocol_tera"

    known_team = []
    for mon in team:
        if not (
            mon.get("known_from_request")
            or mon.get("source") == "request"
            or (not mon.get("inferred") and mon.get("source") != "randbats")
        ):
            continue
        species = mon.get("species")
        if not species:
            continue
        known_team.append(
            {
                "species": species,
                "base_species": species,
                "current_species": species,
                "displayed_species": species,
                "species_source": "request",
                "transformed": False,
                "displayed_species_uncertain": False,
                "illusion_revealed": False,
                "ident": mon.get("ident"),
                "active": bool(mon.get("active")),
                "hp_fraction": mon.get("hp_fraction"),
                "status": mon.get("status"),
                "status_source": "request",
                "status_started_turn": None,
                "fainted": bool(mon.get("fainted")),
                "item": mon.get("item"),
                "last_item": mon.get("last_item"),
                "item_state": mon.get("item_state") or ("held" if mon.get("item") else "none"),
                "ability": mon.get("ability") or mon.get("base_ability"),
                "base_ability": mon.get("base_ability"),
                "ability_state": mon.get("ability_state") or (
                    "known" if mon.get("ability") or mon.get("base_ability") else "none"
                ),
                "tera_type": mon.get("tera_type"),
                "terastallized": bool(mon.get("terastallized")),
            }
        )
    if known_team:
        own["known_team"] = known_team
    else:
        own.setdefault("known_team", [])
    own["fainted_species"] = [m["species"] for m in own.get("known_team", []) if m.get("fainted")]
    own["remaining_known_count"] = len([m for m in own.get("known_team", []) if m.get("species") and not m.get("fainted")])
    own["total_team_size"] = max(int(own.get("total_team_size") or 0), len(own.get("known_team") or []))
    own["unknown_unrevealed_count"] = max(0, int(own.get("total_team_size") or 0) - len(own.get("known_team") or []))

    revealed = own.setdefault("revealed_moves_by_species", {})
    exact_pp = own.setdefault("exact_pp_by_species_move", {})

    for mon in team:
        sp = mon.get("species")
        if not sp:
            continue
        moves = mon.get("moves") or []
        if moves:
            revealed[sp] = list(moves)

    active_species = own.get("active_species")
    if active_species:
        exact_pp.setdefault(active_species, {})
        for mv in ps.get("active_moves") or []:
            key = _private_move_key(mv)
            if not key:
                continue
            exact_pp[active_species][key] = {
                "pp": mv.get("pp"),
                "maxpp": mv.get("maxpp"),
                "provenance": "exact_private_request",
            }

    # Slice 5: surface the ordered own active-move slots (with request disabled/PP
    # flags) and forced-action constraints so the v7 move/constraint slice can read
    # them straight off the snapshot. Additive keys; v2-v6 slices never read them.
    own["active_moves"] = [dict(mv) for mv in (ps.get("active_moves") or []) if isinstance(mv, dict)]
    own["force_switch"] = bool(ps.get("force_switch"))
    own["wait"] = bool(ps.get("wait"))
    own["trapped"] = bool(ps.get("trapped"))

    own["pp_provenance"] = "exact_private_request" if exact_pp else own.get("pp_provenance", "unknown")
    own.setdefault("inferred_pp_by_species_move", {})
    own.setdefault("move_use_counts_by_species", {})
    own.setdefault("last_move_by_species", {})
    own.setdefault("item_known", False)
    own.setdefault("ability_known", False)
    own.setdefault("tera_type_known", False)
    if ps.get("known_from_request"):
        own["tera_used"] = bool(ps.get("tera_used", own.get("tera_used", False)))
        own["can_tera"] = bool(ps.get("can_tera", ps.get("canTerastallize", own.get("can_tera", False))))
        own["tera_action_available"] = bool(ps.get("can_tera", ps.get("canTerastallize", False)))
        if own["tera_used"]:
            own["tera_availability_state"] = "used"
        else:
            own["tera_availability_state"] = "available" if own["can_tera"] else "unavailable"
        own["tera_source"] = "request"

    for side_name in ("own", "opponent"):
        side = merged.setdefault(side_name, {})
        for key, default in {
            "active_status": None,
            "status": None,
            "active_status_source": "unknown",
            "active_status_turns_public": None,
            "volatiles": [],
            "constraint_volatiles": [],
            "active_moves": [],
            "force_switch": False,
            "wait": False,
            "trapped": False,
            "active_base_species": None,
            "active_current_species": None,
            "active_displayed_species": None,
            "active_species_source": "unknown",
            "active_transformed": False,
            "active_displayed_species_uncertain": False,
            "active_illusion_revealed": False,
            "known_team": [],
            "fainted_species": [],
            "revealed_moves_by_species": {},
            "last_move_by_species": {},
            "move_use_counts_by_species": {},
            "inferred_pp_by_species_move": {},
            "exact_pp_by_species_move": {},
            "item_known": False,
            "ability_known": False,
            "tera_type_known": False,
            "tera_used": False,
            "active_tera_type": None,
            "active_terastallized": False,
            "tera_source": "unknown",
            "tera_availability_state": "unknown",
            "tera_action_available": False,
            "can_tera": False,
            "active_base_types": [],
            "active_current_types": [],
            "base_type_source": "unknown",
            "current_type_source": "unknown",
            "active_item": None,
            "active_last_item": None,
            "active_item_state": "unknown",
            "active_item_source": "unknown",
            "active_item_suppressed": False,
            "active_base_ability": None,
            "active_current_ability": None,
            "active_ability_state": "unknown",
            "active_ability_source": "unknown",
            "active_ability_suppressed": False,
        }.items():
            side.setdefault(key, default)
        side["status"] = side.get("active_status")
    merged.setdefault("field_durations", {})
    merged.setdefault("recent", merged.get("recent_events", []))
    merged.setdefault("warnings", [])

    return merged


def _norm_action_name(action):
    if not isinstance(action, dict):
        return ""
    raw = (
        action.get("move")
        or action.get("move_name")
        or action.get("name")
        or action.get("label")
        or action.get("choice")
        or ""
    )
    raw = str(raw)
    if raw.lower().startswith("move:"):
        raw = raw.split(":", 1)[1]
    return raw.strip()

def _norm_id(value):
    return str(value or "").replace(" ", "").replace("-", "").replace("'", "").lower()

def _snapshot_sides(snapshot, actor_side=None):
    if not isinstance(snapshot, dict):
        return {}, {}

    if "own" in snapshot or "opponent" in snapshot:
        return snapshot.get("own", {}) or {}, snapshot.get("opponent", {}) or {}

    side = actor_side or snapshot.get("side") or "p1"
    opp = "p2" if side == "p1" else "p1"
    return snapshot.get(side, {}) or {}, snapshot.get(opp, {}) or {}

def _boost_value(side_state, stat):
    boosts = side_state.get("boosts") or side_state.get("active_boosts") or {}
    try:
        return int(boosts.get(stat, 0))
    except Exception:
        return 0

def tactical_action_flags(*args, **kwargs):
    """Return symbolic tactical flags for an action in a tactical snapshot.

    This compatibility API is used by tests, analyzers, and action scoring. It is
    intentionally conservative: it flags clear no-op / blocked cases without
    banning actions globally.
    """
    action = kwargs.get("action")
    snapshot = kwargs.get("snapshot") or kwargs.get("state") or kwargs.get("tactical_state")
    actor_side = kwargs.get("side") or kwargs.get("actor_side") or kwargs.get("player_side")

    # Accept common positional orders:
    #   tactical_action_flags(action, snapshot, side)
    #   tactical_action_flags(snapshot, action, side)
    if args:
        if isinstance(args[0], dict) and (
            "label" in args[0] or "kind" in args[0] or "move" in args[0] or "choice" in args[0]
        ):
            action = action or args[0]
            if len(args) > 1:
                snapshot = snapshot or args[1]
        else:
            snapshot = snapshot or args[0]
            if len(args) > 1:
                action = action or args[1]
        if len(args) > 2 and actor_side is None:
            actor_side = args[2]

    action = action or {}
    own, opp = _snapshot_sides(snapshot or {}, actor_side=actor_side)

    flags = []
    move_name = _norm_action_name(action)
    move_id = _norm_id(move_name)
    label = str(action.get("label", ""))
    private = kwargs.get("private_state") if isinstance(kwargs.get("private_state"), dict) else {}

    kind = str(action.get("kind") or "").lower()
    if not kind:
        kind = "move" if label.lower().startswith("move:") or move_name else "unknown"

    warnings = action.get("warnings") or action.get("approximation_warnings") or []
    for w in warnings:
        if isinstance(w, str) and w not in flags:
            flags.append(w)

    if action.get("disabled"):
        flags.append("disabled_action")

    try:
        if action.get("pp") is not None and int(action.get("pp")) <= 0:
            flags.append("exhausted_pp")
    except Exception:
        pass

    if kind != "move":
        return list(dict.fromkeys(flags))

    # Status into already-statused target.
    status_moves = {
        "thunderwave": "par",
        "willowisp": "brn",
        "toxic": "tox",
        "spore": "slp",
        "sleeppowder": "slp",
        "hypnosis": "slp",
        "stunspore": "par",
        "glare": "par",
    }
    target_status = (
        opp.get("active_status")
        or opp.get("status")
        or opp.get("condition_status")
        or ""
    )
    if move_id in status_moves and target_status:
        flags.append("status_into_existing_status")

    # Redundant hazards at max / already active.
    opp_side_conditions = opp.get("side_conditions") or {}
    if move_id == "toxicspikes" and int(opp_side_conditions.get("toxicspikes", 0) or 0) >= 2:
        flags.append("redundant_hazard_max_layers")
    if move_id == "spikes" and int(opp_side_conditions.get("spikes", 0) or 0) >= 3:
        flags.append("redundant_hazard_max_layers")
    if move_id == "stealthrock" and int(opp_side_conditions.get("stealthrock", 0) or 0) >= 1:
        flags.append("redundant_hazard_max_layers")
    if move_id == "stickyweb" and int(opp_side_conditions.get("stickyweb", 0) or 0) >= 1:
        flags.append("redundant_hazard_max_layers")

    # Setup at cap.
    setup_stats = {
        "swordsdance": ["atk"],
        "bulkup": ["atk", "def"],
        "dragondance": ["atk", "spe"],
        "calmmind": ["spa", "spd"],
        "irondefense": ["def"],
        "nastyplot": ["spa"],
        "agility": ["spe"],
        "amnesia": ["spd"],
        "coil": ["atk", "def", "accuracy"],
        "curse": ["atk", "def"],
    }
    if move_id in setup_stats and all(_boost_value(own, stat) >= 6 for stat in setup_stats[move_id]):
        flags.append("setup_at_cap")

    # Common known type immunities if action/test supplies type info.
    move_type = _norm_id(action.get("type") or action.get("move_type") or kwargs.get("move_type") or _move_type(move_id))
    target_types = [
        _norm_id(t) for t in (
            opp.get("active_types")
            or opp.get("types")
            or opp.get("target_types")
            or action.get("target_types")
            or _species_types(opp.get("active_species"))
            or []
        )
    ]
    if move_type == "dragon" and "fairy" in target_types:
        flags.append("known_immunity")
    if move_type == "poison" and "steel" in target_types:
        flags.append("known_immunity")
    if move_type == "psychic" and "dark" in target_types:
        flags.append("known_immunity")
    if move_type == "ground" and "flying" in target_types:
        flags.append("known_immunity")
    if move_type == "electric" and "ground" in target_types:
        flags.append("known_immunity")
    if move_type == "normal" and "ghost" in target_types:
        flags.append("known_immunity")
    if move_type == "fighting" and "ghost" in target_types:
        flags.append("known_immunity")

    move_results = snapshot.get("move_results") if isinstance(snapshot, dict) and isinstance(snapshot.get("move_results"), dict) else {}
    perspective_side = str((snapshot or {}).get("perspective_side") or actor_side or private.get("player_side") or "p1")
    result_counts = move_results.get(f"{perspective_side}:{move_id}") if isinstance(move_results.get(f"{perspective_side}:{move_id}"), dict) else {}
    if int(result_counts.get("immune", 0) or 0) > 0:
        flags.append("known_immunity")
        flags.append("repeated_immune_move")

    ability_ids = {to_id(value) for value in (opp.get("known_abilities") or {}).values()} if isinstance(opp.get("known_abilities"), dict) else set()
    blocked = False
    if kwargs.get("move_type") and any(ability in ABSORB_ABILITIES_BY_TYPE.get(str(kwargs.get("move_type")), set()) for ability in ability_ids):
        blocked = True
    if "goodasgold" in ability_ids and move_id in {"thunderwave", "toxic", "willowisp", "spore", "sleeppowder", "stunspore", "taunt", "encore"}:
        blocked = True
    if "soundproof" in ability_ids and move_id in {"hypervoice", "boomburst", "clangingscales", "clangoroussoul", "torchsong"}:
        blocked = True
    if "bulletproof" in ability_ids and move_id in {"shadowball", "aurasphere", "sludgebomb", "focusblast", "energyball"}:
        blocked = True
    if blocked:
        flags.append("known_immunity_or_blocked")

    own_abilities = set()
    for mon in private.get("team", []) if isinstance(private.get("team"), list) else []:
        if isinstance(mon, dict) and mon.get("active"):
            own_abilities.add(to_id(mon.get("ability") or mon.get("base_ability")))
    if "prankster" in own_abilities and move_id in {"thunderwave", "toxic", "willowisp", "stunspore", "taunt", "encore", "spore", "sleeppowder"}:
        if "dark" in target_types:
            flags.append("prankster_status_blocked_by_dark")

    return list(dict.fromkeys(flags))
