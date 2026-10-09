"""Independent public-prefix projection for the simulator's typed volatile/side subset."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .protocol_contract import _is_player_ident
from .public_item import validate_public_items
from .public_health import validate_public_health, bound_owned_target
from .public_ability import validate_public_ability


_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST = _ROOT / "sim-core" / "simulator_coverage" / "pokemon-showdown-0.11.10-gen9randombattle.json"
with _MANIFEST.open(encoding="utf-8") as _source:
    _lifecycle = json.load(_source).get("public_typed_state_lifecycle", {})
if _lifecycle.get("schema_version") != "public-typed-state-lifecycle/v1":
    raise RuntimeError("Pinned public typed-state lifecycle contract is missing")
_ENTRIES = {(entry["family"], entry["id"]): entry for entry in _lifecycle["entries"]}
_COURT_CHANGE_IDS = tuple(_lifecycle["court_change_ids"])


def _effect_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _public_team_ident(value: str) -> str:
    match = re.fullmatch(r"(p[12])a: (.+)", value)
    return f"{match.group(1)}: {match.group(2)}" if match else value


def project_public_typed_state(prefix):
    """Replay normalized public events into only source-backed typed state."""
    volatiles = {}
    active = {}
    sides = {"p1": {}, "p2": {}}

    def get_volatiles(ident):
        return volatiles.setdefault(ident, set())

    def clear(ident):
        if ident:
            get_volatiles(ident).clear()

    def active_ident(value):
        match = re.fullmatch(r"(p[12])a: (.+)", value)
        return f"{match.group(1)}: {match.group(2)}" if match else None

    for line in prefix:
        if not isinstance(line, str) or not line.startswith("|"):
            continue
        parts = line.split("|")
        command = parts[1] if len(parts) > 1 else ""
        if command in ("switch", "drag"):
            ident = active_ident(parts[2] if len(parts) > 2 else "")
            if not ident:
                continue
            player = ident[:2]
            donor = active.get(player)
            donor_had_substitute = bool(donor and "substitute" in get_volatiles(donor))
            clear(donor)
            next_state = get_volatiles(ident)
            next_state.clear()
            shed_tail = command == "switch" and len(parts) == 6 and parts[5] == "[from] Shed Tail"
            if shed_tail and donor_had_substitute:
                next_state.add("substitute")
            active[player] = ident
            continue
        if command == "replace":
            ident = active_ident(parts[2] if len(parts) > 2 else "")
            if not ident:
                continue
            player = ident[:2]
            prior = active.get(player)
            if prior and prior != ident:
                volatiles[ident] = set(get_volatiles(prior))
                volatiles.pop(prior, None)
            active[player] = ident
            continue
        if command == "faint":
            ident = active_ident(parts[2] if len(parts) > 2 else "")
            if ident:
                clear(ident)
                if active.get(ident[:2]) == ident:
                    active.pop(ident[:2], None)
            continue
        if command in ("-start", "-end"):
            value = parts[3] if len(parts) > 3 else ""
            entry = _ENTRIES.get(("move_volatile", _effect_id(value)))
            if not entry or entry["disposition"] == "raw-only":
                continue
            if entry["disposition"] != "evidence-derived-typed":
                raise ValueError(f"Typed lifecycle evidence mismatch: unsupported-fail-closed volatile {entry['id']}.")
            ident = active_ident(parts[2] if len(parts) > 2 else "")
            if not ident or active.get(ident[:2]) != ident:
                raise ValueError(f"Typed lifecycle evidence mismatch: {command} targets a nonactive {entry['id']}.")
            state = get_volatiles(ident)
            effect = entry["id"]
            if command == "-start":
                if effect in state:
                    raise ValueError(f"Typed lifecycle evidence mismatch: duplicate {effect} start.")
                state.add(effect)
            else:
                if effect not in state:
                    raise ValueError(f"Typed lifecycle evidence mismatch: {effect} ends without a public start.")
                state.remove(effect)
            continue
        if command in ("-sidestart", "-sideend"):
            value = parts[3] if len(parts) > 3 else ""
            effect = _effect_id(re.sub(r"^move:\s*", "", value, flags=re.IGNORECASE))
            side = (parts[2] if len(parts) > 2 else "").split(":", 1)[0]
            entry = _ENTRIES.get(("side_condition", effect))
            if side not in sides or not entry:
                continue
            if entry["disposition"] == "raw-only":
                continue
            if entry["disposition"] != "evidence-derived-typed":
                raise ValueError(f"Typed lifecycle evidence mismatch: unsupported-fail-closed side condition {entry['id']}.")
            state = sides[side]
            prior = state.get(effect, 0)
            if command == "-sidestart":
                if entry["mode"] == "count":
                    value = prior + 1
                    if value > entry.get("cap", 1):
                        raise ValueError(f"Typed lifecycle evidence mismatch: {effect} exceeds its public layer cap.")
                    state[effect] = value
                else:
                    if prior:
                        raise ValueError(f"Typed lifecycle evidence mismatch: duplicate {effect} presence start.")
                    state[effect] = 1
            else:
                if not prior:
                    raise ValueError(f"Typed lifecycle evidence mismatch: {effect} ends without a public start.")
                state.pop(effect, None)
            continue
        if command == "-swapsideconditions":
            for effect in _COURT_CHANGE_IDS:
                p1 = sides["p1"].get(effect)
                p2 = sides["p2"].get(effect)
                if p1 is None:
                    sides["p2"].pop(effect, None)
                else:
                    sides["p2"][effect] = p1
                if p2 is None:
                    sides["p1"].pop(effect, None)
                else:
                    sides["p1"][effect] = p2

    return {
        "volatiles_by_ident": {ident: sorted(values) for ident, values in volatiles.items()},
        "side_conditions_by_player": sides,
    }


def _assert_no_private_slot_state(value, location="observation"):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in {"slotconditions", "slot_conditions", "slot_condition_state", "pending_slots"}:
                raise ValueError(f"Private simulator slot state is not publishable ({location}.{key})")
            _assert_no_private_slot_state(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_private_slot_state(child, f"{location}[{index}]")


def validate_public_typed_state(observation, label="observation", predecessor=None):
    """Reject typed values that are not derivable from the retained public prefix."""
    try:
        request = observation.get("request")
        if isinstance(request, dict) and request.get("player") != observation.get("perspective"):
            raise ValueError("request is not owned by its perspective")
        _assert_no_private_slot_state(observation, label)
        prefix = observation["protocol_prefix"]
        view = observation.get("view", {})
        perspective = observation.get("perspective")
        def validate_consequences():
            if observation.get("schema_version") in ("observable-battle-state/v1", "observable-battle-state/v2"):
                validate_public_health(observation, predecessor)
                validate_public_items(observation, predecessor)
                validate_public_ability(observation, predecessor)
        projected = project_public_typed_state(prefix)
        has_typed_view = any(key in view for key in ("self_team", "opponent_team", "field"))
        has_derived_state = (any(projected["volatiles_by_ident"].values())
                             or any(projected["side_conditions_by_player"].values()))
        if not has_typed_view:
            if has_derived_state:
                raise ValueError(
                    "Typed lifecycle evidence mismatch: view-less observation cannot represent "
                    "prefix-derived typed state"
                )
            validate_consequences()
            return
        if has_derived_state and perspective not in ("p1", "p2"):
            raise ValueError("Typed lifecycle evidence mismatch: derived typed state requires a valid perspective")
        bound_volatiles = {}
        for target, values in projected["volatiles_by_ident"].items():
            bound = bound_owned_target(observation, target, predecessor) if target[:2] == perspective else target
            if values or bound not in bound_volatiles:
                bound_volatiles[bound] = values
        projected["volatiles_by_ident"] = bound_volatiles
        expected_sides = ({"self": projected["side_conditions_by_player"]["p1"],
                           "opponent": projected["side_conditions_by_player"]["p2"]}
                          if perspective == "p1" else
                          {"self": projected["side_conditions_by_player"]["p2"],
                           "opponent": projected["side_conditions_by_player"]["p1"]})
        for team_name in ("self_team", "opponent_team"):
            if team_name not in view:
                continue
            if not isinstance(view[team_name], list):
                raise ValueError(f"Typed lifecycle evidence mismatch: {team_name} must be an array")
            for pokemon in view[team_name]:
                if "volatiles" not in pokemon:
                    continue
                ident = pokemon.get("ident", "")
                actual = pokemon.get("volatiles")
                expected = projected["volatiles_by_ident"].get(_public_team_ident(ident), [])
                if "volatiles" in pokemon and (not isinstance(actual, list) or sorted(actual) != expected):
                    raise ValueError(f"{team_name} {ident} volatile map disagrees with retained public prefix")
        for ident, values in projected["volatiles_by_ident"].items():
            if not values:
                continue
            side = ident[:2]
            expected_team = "self_team" if side == perspective else "opponent_team"
            rows = []
            for team_name in ("self_team", "opponent_team"):
                for pokemon in view.get(team_name, []):
                    row_ident = _public_team_ident(pokemon.get("ident", ""))
                    if _is_player_ident(row_ident) and row_ident == ident:
                        rows.append((team_name, pokemon))
            if (len(rows) != 1 or rows[0][0] != expected_team
                    or not isinstance(rows[0][1].get("volatiles"), list)):
                raise ValueError(
                    f"Typed lifecycle evidence mismatch: nonempty volatile state for {ident} "
                    f"requires exactly one canonical {expected_team} roster row"
                )
        for side in ("self", "opponent"):
            expected = expected_sides[side]
            field = view.get("field")
            field_sides = field.get("side_conditions") if isinstance(field, dict) else None
            actual = field_sides.get(side) if isinstance(field_sides, dict) else None
            if not expected and actual is None:
                continue
            if not isinstance(actual, dict):
                raise ValueError(
                    f"Typed lifecycle evidence mismatch: {side} side-condition state requires its field side_conditions map"
                )
            if {key: value for key, value in actual.items() if value != 0} != expected:
                raise ValueError(f"{side} side-condition map disagrees with retained public prefix")
        validate_consequences()
    except (KeyError, TypeError, ValueError) as exc:
        if "Typed lifecycle evidence mismatch" in str(exc):
            raise
        raise ValueError(f"Typed lifecycle evidence mismatch: {exc}") from exc
