"""Move side-effect annotations for action explanation traces (diagnostics only).

These are *explanatory* fields. They are NOT used to ban actions or override any
score. The live recommender's selection logic is unchanged; this module only
surfaces what a move does so action traces can explain a decision (e.g. that
Draco Meteor lowers the user's Special Attack by two stages).

Detection parses the bundled Pokemon Showdown ``moves.ts`` (the same source the
action featurizer already reads) for the structural fields that matter:

* ``self: { boosts: { spa: -2 } }``  → self stat drop (Draco Meteor / Overheat)
* ``self: { boosts: { def: -1 } }``  → defensive drop (Close Combat / Superpower)
* ``recoil: [...]``                  → recoil
* ``flags: { recharge: 1 }``         → recharge turn (Hyper Beam)
* ``self: { volatileStatus: 'lockedmove' }`` → lock-in (Outrage / Petal Dance)
* ``selfSwitch`` / pivot moves       → switch move (U-turn / Volt Switch)
* ``heal`` / ``drain``               → heals user
* positive self/own ``boosts``       → setup / boosts user
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, Optional

from .action_features import (
    _extract_object_block,
    _move_data_candidates,
    load_move_metadata,
    to_id,
)

_BOOST_STATS = ("atk", "def", "spa", "spd", "spe", "accuracy", "evasion")
_PIVOT_IDS = {"uturn", "voltswitch", "flipturn", "partingshot", "chillyreception", "teleport"}


def _self_block(block: str) -> Optional[str]:
    match = re.search(r"\bself\s*:\s*\{", block)
    if not match:
        return None
    inner, _ = _extract_object_block(block, match.end() - 1)
    return inner or None


def _boosts_in(block: str) -> Dict[str, int]:
    match = re.search(r"\bboosts\s*:\s*\{([^}]*)\}", block, re.DOTALL)
    if not match:
        return {}
    out: Dict[str, int] = {}
    for stat in _BOOST_STATS:
        stat_match = re.search(rf"\b{stat}\s*:\s*(-?\d+)", match.group(1))
        if stat_match:
            out[stat] = int(stat_match.group(1))
    return out


@lru_cache(maxsize=1)
def _raw_self_effects() -> Dict[str, Dict[str, Any]]:
    """Parse moves.ts once for the self-effect fields not exposed by the featurizer."""
    for path in _move_data_candidates():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        effects: Dict[str, Dict[str, Any]] = {}
        pattern = re.compile(r"\n\s*([a-z0-9]+)\s*:\s*\{")
        position = 0
        while True:
            match = pattern.search(text, position)
            if not match:
                break
            move_id = match.group(1)
            block, position = _extract_object_block(text, match.end() - 1)
            if not block:
                continue
            self_block = _self_block(block)
            self_boosts = _boosts_in(self_block) if self_block else {}
            effects[move_id] = {
                "self_boosts": self_boosts,
                "recoil": bool(re.search(r"\brecoil\s*:", block)),
                "has_crash_damage": bool(re.search(r"\bhasCrashDamage\s*:\s*true", block)),
                "recharge": bool(self_block and "mustrecharge" in self_block)
                or bool(re.search(r"\brecharge\s*:\s*1", block)),
                "locks_user": bool(self_block and "lockedmove" in self_block),
                "self_switch": bool(re.search(r"\bselfSwitch\s*:", block)),
            }
        return effects
    return {}


def _stats_in_object(inner: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for stat in _BOOST_STATS:
        match = re.search(rf"\b{stat}\s*:\s*(-?\d+)", inner)
        if match:
            out[stat] = int(match.group(1))
    return out


def _top_level_boosts(block: str) -> Dict[str, int]:
    """Boosts declared as a direct property of the move object (depth 1).

    These apply to the move's *target* (the user for self-targeting setup moves
    like Bulk Up / Swords Dance, the foe for Growl / Leer). Boosts nested inside
    ``self``/``secondary`` blocks are deeper and excluded here.
    """
    depth = 0
    index = 0
    length = len(block)
    while index < length:
        char = block[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif depth == 1 and block.startswith("boosts", index) and (index == 0 or not block[index - 1].isalnum()):
            after = index + len("boosts")
            rest = block[after:].lstrip()
            if rest.startswith(":"):
                brace = block.find("{", after)
                if brace != -1:
                    inner, _ = _extract_object_block(block, brace)
                    return _stats_in_object(inner)
        index += 1
    return {}


def _self_boosts_all(block: str) -> Dict[str, int]:
    """Boosts that always apply to the user: ``self: {boosts}`` (Draco Meteor /
    Close Combat) and the dynamically-assigned ``move.self = {boosts}`` (Curse)."""
    out: Dict[str, int] = {}
    for match in re.finditer(r"\bself\s*[:=]\s*\{", block):
        inner, _ = _extract_object_block(block, match.end() - 1)
        if inner:
            out.update(_boosts_in(inner))
    return out


def move_stat_deltas(move_name: str) -> Dict[str, Dict[str, int]]:
    """Net per-stat boost/drop a move applies to the user and to the target.

    Diagnostics only; no move-specific rule. Parses moves.ts structurally so
    future training can see, e.g., Draco Meteor's self SpA drop or Curse's mixed
    self boosts/drop vs Bulk Up's.
    """
    move_id = to_id(move_name)
    metadata, _ = load_move_metadata()
    meta = metadata.get(move_id, {}) if move_id else {}
    target = str(meta.get("target") or "").lower()
    is_status = str(meta.get("category") or "").lower() == "status"

    block = ""
    for path in _move_data_candidates():
        if path.exists():
            text = path.read_text(encoding="utf-8")
            match = re.search(r"\n\s*" + re.escape(move_id) + r"\s*:\s*\{", text)
            if match:
                block, _ = _extract_object_block(text, match.end() - 1)
            break

    self_delta = dict(_self_boosts_all(block)) if block else {}
    target_delta: Dict[str, int] = {}
    top = _top_level_boosts(block) if block else {}
    if top:
        # Top-level boosts apply to the user when the move targets self, else the foe.
        if target in {"self", "adjacentally", "allies", "allyside"}:
            for stat, value in top.items():
                self_delta[stat] = self_delta.get(stat, 0) + value
        elif is_status:
            target_delta.update(top)
    return {"self": self_delta, "target": target_delta}


def move_side_effects(move_name: str) -> Dict[str, Any]:
    """Return explanatory side-effect annotations for a move (diagnostics only).

    Always returns the full key set so traces never silently omit a field. When
    move data is missing, numeric/boolean fields are zero/false and
    ``data_available`` is false.
    """
    move_id = to_id(move_name)
    metadata, _ = load_move_metadata()
    meta = metadata.get(move_id, {}) if move_id else {}
    raw = _raw_self_effects().get(move_id, {}) if move_id else {}
    data_available = bool(meta) or bool(raw)

    self_boosts = raw.get("self_boosts") or {}
    self_stat_drops = {stat: value for stat, value in self_boosts.items() if value < 0}
    self_stat_boosts = {stat: value for stat, value in self_boosts.items() if value > 0}
    category = str(meta.get("category") or "").lower()
    is_status = category == "status"
    # A setup move boosts the *user*; for status moves the top-level ``boosts``
    # applies to the user (e.g. Swords Dance), so reuse the featurizer's flag.
    boosts_user = bool(self_stat_boosts) or bool(meta.get("has_boosts") and is_status)

    return {
        "move_id": move_id,
        "data_available": data_available,
        "self_stat_drop": self_stat_drops or None,
        "self_stat_boost": self_stat_boosts or None,
        "recoil": bool(raw.get("recoil") or raw.get("has_crash_damage")),
        "recharge": bool(raw.get("recharge")),
        "locks_user": bool(raw.get("locks_user")),
        "heals_user": bool(meta.get("has_heal") or meta.get("has_drain")),
        "boosts_user": bool(boosts_user),
        "status_move": bool(is_status),
        "switch_move": bool(raw.get("self_switch") or move_id in _PIVOT_IDS),
        "priority": int(float(meta.get("priority", 0.0) or 0.0)),
        "setup_move": bool(meta.get("has_boosts") and is_status),
        "has_drawback": bool(self_stat_drops or raw.get("recoil") or raw.get("has_crash_damage") or raw.get("recharge") or raw.get("locks_user")),
    }


def annotate_action_side_effects(action: Dict[str, Any]) -> Dict[str, Any]:
    """Side-effect annotation for a legal-action dict. Switches return a switch marker."""
    kind = str(action.get("kind") or "").lower()
    if kind == "switch":
        return {
            "move_id": None,
            "data_available": True,
            "self_stat_drop": None,
            "self_stat_boost": None,
            "recoil": False,
            "recharge": False,
            "locks_user": False,
            "heals_user": False,
            "boosts_user": False,
            "status_move": False,
            "switch_move": True,
            "priority": 0,
            "setup_move": False,
            "has_drawback": False,
        }
    label = str(action.get("label") or action.get("move") or action.get("name") or "")
    name = label.split(":", 1)[1].strip() if ":" in label else label.strip()
    return move_side_effects(name)
