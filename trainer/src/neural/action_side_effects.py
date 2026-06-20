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
_TARGET_ITEM_REMOVAL_IDS = {"knockoff", "corrosivegas"}
_TARGET_BERRY_EAT_IDS = {"bugbite", "pluck"}
_ITEM_SWAP_IDS = {"trick", "switcheroo"}
_TARGET_ITEM_SUPPRESS_IDS = {"embargo"}
_ALL_ITEM_SUPPRESS_IDS = {"magicroom"}


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


_SELF_TARGET_IDS = {"self", "adjacentally", "adjacentallyorself", "allies", "allyside", "allyteam"}


def _extract_balanced(text: str, start: int) -> tuple[str, int]:
    """Extract a balanced ``{}``/``[]`` region beginning at ``start``."""
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char in "{[":
            depth += 1
        elif char in "]}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1], index + 1
    return text[start:], len(text)


def _split_nested_self(region: str) -> tuple[str, str]:
    """Split a secondary region into (target_part, self_part) text.

    ``self: {...}`` sub-blocks apply to the user; the remainder applies to the
    target. Returns concatenated text for each so simple substring checks decide
    which next-state flag a secondary effect populates.
    """
    self_parts: list[str] = []
    remainder = region
    while True:
        match = re.search(r"\bself\s*:\s*\{", remainder)
        if not match:
            break
        inner, end = _extract_object_block(remainder, match.end() - 1)
        self_parts.append(inner)
        remainder = remainder[: match.start()] + remainder[end:]
    return remainder, "".join(self_parts)


def _has_status_or_volatile(text: str) -> bool:
    return bool(re.search(r"\b(status|volatileStatus)\s*:", text))


def _secondary_inflicts(text: str) -> bool:
    """A secondary region that sets a status/volatile or runs an effect callback.

    Callback secondaries (e.g. Dire Claw / Tri Attack pick a random status in
    ``onHit``) carry no literal ``status:`` field, so detect the callback too.
    Scoped to secondary regions only, so ordinary top-level callbacks are ignored.
    """
    return _has_status_or_volatile(text) or bool(re.search(r"\bon[A-Z]\w*\s*\(", text))


@lru_cache(maxsize=1)
def _raw_next_state_effects() -> Dict[str, Dict[str, bool]]:
    """Parse moves.ts once for which side a move's status/volatile/stat effects hit.

    Produces coarse booleans (effect present, not its exact type/chance/magnitude)
    that fill the existing v6 next-state change flags so a move with a real
    secondary/status/volatile effect is no longer represented as a wrong-exact
    "no change". Self/own stat boosts that ``move_stat_deltas`` already covers are
    intentionally not duplicated here.
    """
    metadata, _ = load_move_metadata()
    for path in _move_data_candidates():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        effects: Dict[str, Dict[str, bool]] = {}
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
            target = str((metadata.get(move_id) or {}).get("target") or "").lower()
            self_targeting = target in _SELF_TARGET_IDS
            opp_status = opp_stat = own_status = own_stat = False

            work = block
            for key in ("secondaries", "secondary"):
                while True:
                    sm = re.search(r"\b" + key + r"\s*:\s*[\{\[]", work)
                    if not sm:
                        break
                    region, end = _extract_balanced(work, sm.end() - 1)
                    target_text, self_text = _split_nested_self(region)
                    opp_status = opp_status or _secondary_inflicts(target_text)
                    opp_stat = opp_stat or bool(re.search(r"\bboosts\s*:", target_text))
                    own_status = own_status or _has_status_or_volatile(self_text)
                    own_stat = own_stat or bool(re.search(r"\bboosts\s*:", self_text))
                    work = work[: sm.start()] + work[end:]

            # Primary self block (outside any secondary): user status/volatile.
            self_block = _self_block(work)
            if self_block and _has_status_or_volatile(self_block):
                own_status = True
            # Remove all self blocks before scanning for top-level status/volatile.
            scan = work
            while True:
                sm = re.search(r"\bself\s*:\s*\{", scan)
                if not sm:
                    break
                _, end = _extract_object_block(scan, sm.end() - 1)
                scan = scan[: sm.start()] + scan[end:]
            if _has_status_or_volatile(scan):
                if self_targeting:
                    own_status = True
                else:
                    opp_status = True

            effects[move_id] = {
                "opp_status_or_volatile": opp_status,
                "opp_stat_change": opp_stat,
                "own_status_or_volatile": own_status,
                "own_stat_change": own_stat,
            }
        return effects
    return {}


_STATUS_STRINGS = {"brn", "par", "psn", "tox", "slp", "frz"}
# Moves whose secondary status is chosen by an onHit callback (no literal status
# field), with an equal split of the secondary chance across the listed statuses.
_CALLBACK_STATUS_MOVES = {
    "triattack": (20, ("brn", "par", "frz")),
    "direclaw": (50, ("psn", "par", "slp")),
}


def _top_level_objects(text: str) -> list:
    """Return each top-level ``{...}`` object inside a region (handles arrays)."""
    objects = []
    index = 0
    length = len(text)
    while index < length:
        if text[index] == "{":
            obj, end = _extract_object_block(text, index)
            if obj:
                objects.append(obj)
                index = end
                continue
        index += 1
    return objects


def _status_keys_in(text: str) -> set:
    keys = set()
    for match in re.finditer(r"\bstatus\s*:\s*'([a-z]+)'", text):
        if match.group(1) in _STATUS_STRINGS:
            keys.add(match.group(1))
    for match in re.finditer(r"\bvolatileStatus\s*:\s*'([a-z]+)'", text):
        if match.group(1) == "confusion":
            keys.add("confusion")
    return keys


@lru_cache(maxsize=1)
def _raw_typed_effects() -> Dict[str, Dict[str, Any]]:
    """Parse moves.ts once for typed status chances and secondary stat boosts.

    Returns, per move id: ``target_status`` / ``self_status`` (key -> chance in
    [0,1]) and ``target_sec_boosts`` / ``self_sec_boosts`` ({stat: stage}, chance)
    for boosts that live inside ``secondary`` blocks (primary/self stat stages are
    taken from ``move_stat_deltas``). Chance-based effects keep their probability;
    nothing is rounded to a fake deterministic outcome.
    """
    metadata, _ = load_move_metadata()
    for path in _move_data_candidates():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        out: Dict[str, Dict[str, Any]] = {}
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
            target = str((metadata.get(move_id) or {}).get("target") or "").lower()
            self_targeting = target in _SELF_TARGET_IDS

            target_status: Dict[str, float] = {}
            self_status: Dict[str, float] = {}
            target_sec_boosts: Dict[str, int] = {}
            self_sec_boosts: Dict[str, int] = {}
            target_sec_chance = 0.0
            self_sec_chance = 0.0

            work = block
            for key in ("secondaries", "secondary"):
                while True:
                    sm = re.search(r"\b" + key + r"\s*:\s*[\{\[]", work)
                    if not sm:
                        break
                    region, end = _extract_balanced(work, sm.end() - 1)
                    for obj in _top_level_objects(region):
                        chance_match = re.search(r"\bchance\s*:\s*(\d+)", obj)
                        chance = (int(chance_match.group(1)) if chance_match else 100) / 100.0
                        target_text, self_text = _split_nested_self(obj)
                        for skey in _status_keys_in(target_text):
                            target_status[skey] = max(target_status.get(skey, 0.0), chance)
                        for skey in _status_keys_in(self_text):
                            self_status[skey] = max(self_status.get(skey, 0.0), chance)
                        tb = _boosts_in(target_text)
                        if tb:
                            target_sec_boosts.update(tb)
                            target_sec_chance = max(target_sec_chance, chance)
                        sb = _boosts_in(self_text)
                        if sb:
                            self_sec_boosts.update(sb)
                            self_sec_chance = max(self_sec_chance, chance)
                    work = work[: sm.start()] + work[end:]

            # Primary (non-secondary) boosts are guaranteed (chance 1.0); keep
            # them separate from secondary-self boosts so a 20%-secondary self
            # boost (Meteor Mash) is not mislabeled as guaranteed.
            prim_self_boosts: Dict[str, int] = {}
            prim_target_boosts: Dict[str, int] = {}
            primary_self = _self_block(work)
            if primary_self:
                for skey in _status_keys_in(primary_self):
                    self_status[skey] = 1.0
                prim_self_boosts.update(_boosts_in(primary_self))
            # selfBoost: { boosts: {...} } is a guaranteed (on-hit) self stat change.
            selfboost_match = re.search(r"\bselfBoost\s*:\s*\{", work)
            if selfboost_match:
                selfboost_block, _ = _extract_object_block(work, selfboost_match.end() - 1)
                prim_self_boosts.update(_boosts_in(selfboost_block))
            top_boosts = _top_level_boosts(work)
            is_status_move = str((metadata.get(move_id) or {}).get("category") or "").lower() == "status"
            if top_boosts:
                if self_targeting:
                    for stat, value in top_boosts.items():
                        prim_self_boosts[stat] = prim_self_boosts.get(stat, 0) + value
                elif is_status_move:
                    prim_target_boosts.update(top_boosts)

            # Top-level (primary) status/volatile after removing self blocks.
            scan = work
            while True:
                sm = re.search(r"\bself\s*:\s*\{", scan)
                if not sm:
                    break
                _, end = _extract_object_block(scan, sm.end() - 1)
                scan = scan[: sm.start()] + scan[end:]
            for skey in _status_keys_in(scan):
                if self_targeting:
                    self_status[skey] = 1.0
                else:
                    target_status[skey] = 1.0

            if move_id in _CALLBACK_STATUS_MOVES:
                pct, statuses = _CALLBACK_STATUS_MOVES[move_id]
                share = (pct / 100.0) / len(statuses)
                for skey in statuses:
                    target_status[skey] = max(target_status.get(skey, 0.0), share)

            out[move_id] = {
                "target_status": target_status,
                "self_status": self_status,
                "prim_target_boosts": prim_target_boosts,
                "prim_self_boosts": prim_self_boosts,
                "target_sec_boosts": target_sec_boosts,
                "self_sec_boosts": self_sec_boosts,
                "target_sec_chance": target_sec_chance,
                "self_sec_chance": self_sec_chance,
            }
        return out
    return {}


def move_typed_effects(move_name: str) -> Dict[str, Any]:
    """Typed status chances and stat-stage deltas for a move (legal-action-v7).

    Combines primary stat stages (`move_stat_deltas`, chance 1.0) with
    secondary-block stat boosts (with their secondary chance), and typed status
    chances. Diagnostics only; oracle = bundled moves.ts.
    """
    move_id = to_id(move_name)
    raw = _raw_typed_effects().get(move_id, {}) if move_id else {}

    def _stat_side(primary: Dict[str, int], sec_boosts: Dict[str, int], sec_chance: float):
        # Primary (guaranteed) boosts define the side at chance 1.0; otherwise a
        # secondary boost defines it at its secondary chance.
        if primary:
            stages = dict(primary)
            for stat, value in sec_boosts.items():
                stages.setdefault(stat, value)
            return {"stages": stages, "chance": 1.0}
        if sec_boosts:
            return {"stages": dict(sec_boosts), "chance": sec_chance}
        return {"stages": {}, "chance": 0.0}

    return {
        "target_status": dict(raw.get("target_status") or {}),
        "self_status": dict(raw.get("self_status") or {}),
        "target_stat": _stat_side(raw.get("prim_target_boosts") or {}, raw.get("target_sec_boosts") or {}, raw.get("target_sec_chance") or 0.0),
        "self_stat": _stat_side(raw.get("prim_self_boosts") or {}, raw.get("self_sec_boosts") or {}, raw.get("self_sec_chance") or 0.0),
    }


# legal-action-v7 batch 2: typed volatile effects. Maps each Showdown
# volatileStatus string to its exact v7 field. Confusion is already modeled in the
# batch-1 status slice; curse/lockedmove/mustrecharge/roost/glaiverush are handled
# elsewhere or deferred, so they are excluded here (see implementation doc).
_VOLATILE_FIELD = {
    "flinch": "effect_target_flinch_chance",
    "partiallytrapped": "effect_target_trap_chance",
    "taunt": "effect_target_taunt",
    "encore": "effect_target_encore",
    "disable": "effect_target_disable",
    "leechseed": "effect_target_leech_seed",
    "yawn": "effect_target_yawn",
    "healblock": "effect_target_heal_block",
    "substitute": "effect_self_substitute",
    "protect": "effect_self_protect",
    "detect": "effect_self_protect",
    "spikyshield": "effect_self_protect",
    "banefulbunker": "effect_self_protect",
    "kingsshield": "effect_self_protect",
    "silktrap": "effect_self_protect",
    "burningbulwark": "effect_self_protect",
    "obstruct": "effect_self_protect",
    "maxguard": "effect_self_protect",
    "destinybond": "effect_self_destiny_bond",
    "magnetrise": "effect_self_magnet_rise",
}
_VOLATILE_EXCLUDE = {"confusion", "lockedmove", "mustrecharge", "curse", "roost", "glaiverush"}


@lru_cache(maxsize=1)
def _raw_volatile_effects() -> Dict[str, Dict[str, float]]:
    """Parse moves.ts once for typed volatile effects (chance per v7 field).

    Secondary volatiles (flinch) carry their secondary chance; primary volatiles
    are guaranteed on hit (1.0). Volatiles without a dedicated field fall into a
    side-appropriate ``*_volatile_other`` catch-all (e.g. Salt Cure, No Retreat).
    """
    metadata, _ = load_move_metadata()
    for path in _move_data_candidates():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        out: Dict[str, Dict[str, float]] = {}
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
            self_targeting = str((metadata.get(move_id) or {}).get("target") or "").lower() in _SELF_TARGET_IDS
            fields: Dict[str, float] = {}

            def _record(vol: str, chance: float) -> None:
                if vol in _VOLATILE_EXCLUDE:
                    return
                field = _VOLATILE_FIELD.get(vol)
                if field is None:
                    field = "effect_self_volatile_other" if self_targeting else "effect_target_volatile_other"
                fields[field] = max(fields.get(field, 0.0), chance)

            work = block
            for key in ("secondaries", "secondary"):
                while True:
                    sm = re.search(r"\b" + key + r"\s*:\s*[\{\[]", work)
                    if not sm:
                        break
                    region, end = _extract_balanced(work, sm.end() - 1)
                    for obj in _top_level_objects(region):
                        chance_match = re.search(r"\bchance\s*:\s*(\d+)", obj)
                        chance = (int(chance_match.group(1)) if chance_match else 100) / 100.0
                        for vm in re.finditer(r"\bvolatileStatus\s*:\s*'([a-z]+)'", obj):
                            _record(vm.group(1), chance)
                    work = work[: sm.start()] + work[end:]

            # Primary (non-secondary) volatiles are guaranteed on hit.
            for vm in re.finditer(r"\bvolatileStatus\s*:\s*'([a-z]+)'", work):
                _record(vm.group(1), 1.0)

            if fields:
                out[move_id] = fields
        return out
    return {}


def move_volatile_effects(move_name: str) -> Dict[str, float]:
    """Typed volatile effect chances for a move, keyed by v7 field name."""
    return dict(_raw_volatile_effects().get(to_id(move_name), {}))


@lru_cache(maxsize=1)
def _berry_item_ids() -> set:
    """Berry ids from Showdown items.ts, used instead of name guessing."""
    for moves_path in _move_data_candidates():
        path = moves_path.with_name("items.ts")
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        berries = set()
        pattern = re.compile(r"\n\s*([a-z0-9]+)\s*:\s*\{")
        position = 0
        while True:
            match = pattern.search(text, position)
            if not match:
                break
            item_id = match.group(1)
            block, position = _extract_object_block(text, match.end() - 1)
            if block and re.search(r"\bisBerry\s*:\s*true", block):
                berries.add(item_id)
        return berries
    return set()


def item_is_berry(item_name: str) -> bool:
    return to_id(item_name) in _berry_item_ids()


@lru_cache(maxsize=1)
def _moves_with_item_callbacks() -> set:
    """Move ids whose Showdown source directly manipulates an item."""
    for path in _move_data_candidates():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        out = set()
        pattern = re.compile(r"\n\s*([a-z0-9]+)\s*:\s*\{")
        position = 0
        while True:
            match = pattern.search(text, position)
            if not match:
                break
            move_id = match.group(1)
            block, position = _extract_object_block(text, match.end() - 1)
            if block and re.search(
                r"\b(?:takeItem|setItem|useItem|eatItem|EatItem)\s*\(",
                block,
            ):
                out.add(move_id)
        return out
    return set()


def move_item_effects(move_name: str) -> Dict[str, bool]:
    """Typed item semantics grounded in bundled Showdown move metadata.

    The named families correspond to Showdown callbacks (`takeItem`, `stealeat`,
    item exchange), Embargo's volatile, Magic Room's pseudo-weather, and the
    metadata `charge` flag consumed by Power Herb.
    """
    move_id = to_id(move_name)
    metadata, _ = load_move_metadata()
    meta = metadata.get(move_id, {}) if move_id else {}
    flags = set(meta.get("flags") or [])
    typed = (
        move_id in _TARGET_ITEM_REMOVAL_IDS
        or move_id in _TARGET_BERRY_EAT_IDS
        or move_id in _ITEM_SWAP_IDS
        or move_id in _TARGET_ITEM_SUPPRESS_IDS
        or move_id in _ALL_ITEM_SUPPRESS_IDS
        or "charge" in flags
    )
    return {
        "removes_target_item": move_id in _TARGET_ITEM_REMOVAL_IDS,
        "eats_target_berry": move_id in _TARGET_BERRY_EAT_IDS,
        "swaps_items": move_id in _ITEM_SWAP_IDS,
        "knock_off": move_id == "knockoff",
        "suppresses_target_item": move_id in _TARGET_ITEM_SUPPRESS_IDS,
        "suppresses_all_items": move_id in _ALL_ITEM_SUPPRESS_IDS,
        "charge_move": "charge" in flags,
        "item_other": move_id in _moves_with_item_callbacks() and not typed,
    }


def move_timing_effects(move_name: str) -> Dict[str, Any]:
    """Static timing/priority semantics from bundled Showdown move metadata."""
    move_id = to_id(move_name)
    metadata, _ = load_move_metadata()
    meta = metadata.get(move_id, {}) if move_id else {}
    raw = _raw_self_effects().get(move_id, {}) if move_id else {}
    flags = set(meta.get("flags") or [])
    future = "futuremove" in flags
    recognized = bool(
        meta
        and (
            "charge" in flags
            or future
            or raw.get("recharge")
            or raw.get("locks_user")
            or move_id == "grassyglide"
        )
    )
    return {
        "base_priority": int(float(meta.get("priority", 0.0) or 0.0)),
        "category": str(meta.get("category") or "").lower(),
        "type": meta.get("type"),
        "heal_flag": "heal" in flags,
        "requires_charge": "charge" in flags,
        "must_recharge": bool(raw.get("recharge")),
        "locks_user": bool(raw.get("locks_user")),
        "delayed_future_damage": future,
        # Gen 8+ Future Sight / Doom Desire land two turns after use.
        "delayed_turns": 2 if future else 0,
        "timing_other": bool(meta) and not recognized and bool(
            {"cantusetwice", "futuremove"} & flags
        ),
    }


def _fraction_in(block: str, field: str) -> float:
    match = re.search(
        rf"\b{re.escape(field)}\s*:\s*\[\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\]",
        block,
    )
    if not match:
        return 0.0
    denominator = float(match.group(2))
    return float(match.group(1)) / denominator if denominator else 0.0


@lru_cache(maxsize=1)
def _raw_hp_side_effects() -> Dict[str, Dict[str, Any]]:
    """Exact static HP fractions parsed from bundled Showdown moves.ts."""
    metadata, _ = load_move_metadata()
    for path in _move_data_candidates():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        out: Dict[str, Dict[str, Any]] = {}
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
            meta = metadata.get(move_id) or {}
            target = str(meta.get("target") or "").lower()
            heal = _fraction_in(block, "heal")
            recoil = _fraction_in(block, "recoil")
            drain = _fraction_in(block, "drain")
            fields: Dict[str, Any] = {
                "recoil_damage_fraction": recoil,
                "recoil_max_hp_fraction": 0.0,
                "drain_damage_fraction": drain,
                "user_heal_max_hp_fraction": heal if target == "self" else 0.0,
                "target_heal_max_hp_fraction": heal if heal and target != "self" else 0.0,
                "self_damage_max_hp_fraction": 0.0,
                "hp_cost_max_hp_fraction": 0.0,
                "crash_damage_max_hp_fraction": 0.5 if re.search(r"\bhasCrashDamage\s*:\s*true", block) else 0.0,
                "conditional": False,
                "amount_unknown": False,
                "hp_effect_other": False,
            }

            if re.search(r"\bmindBlownRecoil\s*:\s*true", block) or move_id == "chloroblast":
                fields["self_damage_max_hp_fraction"] = 0.5
            if re.search(r"\bstruggleRecoil\s*:\s*true", block):
                fields["recoil_max_hp_fraction"] = 0.25
            if move_id == "substitute":
                fields["hp_cost_max_hp_fraction"] = 0.25
            elif move_id == "bellydrum":
                fields["hp_cost_max_hp_fraction"] = 0.5

            if move_id in {"moonlight", "morningsun", "synthesis", "shoreup", "healpulse", "floralhealing"}:
                fields["conditional"] = True
            if fields["crash_damage_max_hp_fraction"]:
                fields["conditional"] = True
            if move_id == "strengthsap":
                fields["conditional"] = True
                fields["amount_unknown"] = True
            if move_id in {"wish", "healingwish", "lunardance"}:
                fields["hp_effect_other"] = True

            if any(bool(value) for value in fields.values()):
                out[move_id] = fields
        return out
    return {}


def move_hp_side_effects(move_name: str) -> Dict[str, Any]:
    """Typed HP side effects for one move; absent effects return an all-zero map."""
    return dict(_raw_hp_side_effects().get(to_id(move_name), {}))


def _literal_field(block: str, field: str) -> Optional[str]:
    match = re.search(rf"\b{re.escape(field)}\s*:\s*['\"]([^'\"]+)['\"]", block)
    return match.group(1) if match else None


@lru_cache(maxsize=1)
def _raw_field_side_effects() -> Dict[str, Dict[str, Any]]:
    """Typed field/side semantics parsed from bundled Showdown moves.ts."""
    for path in _move_data_candidates():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        out: Dict[str, Dict[str, Any]] = {}
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
            side = to_id(_literal_field(block, "sideCondition"))
            weather = to_id(_literal_field(block, "weather"))
            terrain = to_id(_literal_field(block, "terrain"))
            pseudo = to_id(_literal_field(block, "pseudoWeather"))
            fields: Dict[str, Any] = {
                "target_stealthrock": side == "stealthrock",
                "target_spikes": side == "spikes",
                "target_toxicspikes": side == "toxicspikes",
                "target_stickyweb": side == "stickyweb",
                "remove_user_hazards": move_id in {"rapidspin", "mortalspin"},
                "remove_target_hazards": False,
                "user_reflect": side == "reflect",
                "user_lightscreen": side == "lightscreen",
                "user_auroraveil": side == "auroraveil",
                "remove_target_screens": move_id in {"brickbreak", "psychicfangs", "ragingbull"},
                "weather_sun": weather == "sunnyday",
                "weather_rain": weather == "raindance",
                "weather_sand": weather == "sandstorm",
                "weather_snow": weather in {"snow", "snowscape", "hail"},
                "terrain_grassy": terrain == "grassyterrain",
                "terrain_electric": terrain == "electricterrain",
                "terrain_psychic": terrain == "psychicterrain",
                "terrain_misty": terrain == "mistyterrain",
                "trickroom": pseudo == "trickroom",
                "magicroom": pseudo == "magicroom",
                "wonderroom": pseudo == "wonderroom",
                "gravity": pseudo == "gravity",
                "user_tailwind": side == "tailwind",
                "user_safeguard": side == "safeguard",
                "user_mist": side == "mist",
                "user_luckychant": side == "luckychant",
                "remove_terrain": False,
                "swap_side_conditions": move_id == "courtchange",
                "conditional": move_id == "auroraveil",
                "field_side_other": False,
            }

            if move_id == "defog":
                fields["remove_user_hazards"] = True
                fields["remove_target_hazards"] = True
                fields["remove_target_screens"] = True
                fields["remove_terrain"] = True
            elif move_id == "tidyup":
                fields["remove_user_hazards"] = True
                fields["remove_target_hazards"] = True

            recognized_literals = {
                "stealthrock", "spikes", "toxicspikes", "stickyweb",
                "reflect", "lightscreen", "auroraveil", "tailwind",
                "safeguard", "mist", "luckychant",
            }
            if side and side not in recognized_literals:
                fields["field_side_other"] = True
            if pseudo and pseudo not in {"trickroom", "magicroom", "wonderroom", "gravity"}:
                fields["field_side_other"] = True

            if any(bool(value) for value in fields.values()):
                out[move_id] = fields
        return out
    return {}


def move_field_side_effects(move_name: str) -> Dict[str, Any]:
    """Typed hazards/screens/weather/terrain/room effects for one move."""
    return dict(_raw_field_side_effects().get(to_id(move_name), {}))


def move_next_state_effects(move_name: str) -> Dict[str, bool]:
    """Coarse next-state effect presence for a move (diagnostics only).

    Booleans only — they say an effect on a side occurs, not its exact type,
    chance, or magnitude. Used to fill the existing v6 next-state change flags.
    """
    effect = _raw_next_state_effects().get(to_id(move_name))
    if effect is None:
        return {
            "opp_status_or_volatile": False,
            "opp_stat_change": False,
            "own_status_or_volatile": False,
            "own_stat_change": False,
        }
    return dict(effect)


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
