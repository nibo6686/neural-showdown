from .version_profile import reader_context, assert_reader_input, HISTORICAL10_CONTEXT
"""Bounded field truth from an already grammar/inventory-validated public prefix."""

import math
from collections.abc import Mapping

from .protocol_contract import VALIDATION_RULES


def _finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def validate_public_field(observation, label="observation", *, reader_rules=HISTORICAL10_CONTEXT):
    reader_context(reader_rules)
    weather, terrain, trick_room = None, None, False
    has_writer = False
    rules = reader_context(reader_rules).protocol["validation_rules"]

    def fail(detail):
        raise ValueError(f"Public field evidence mismatch: {detail}")

    for line in observation["protocol_prefix"]:
        parts = line.split("|")
        command = parts[1] if len(parts) > 1 else ""
        value = parts[2] if len(parts) > 2 else ""
        if command == "-weather":
            has_writer = True
            if value == "none":
                if weather in (None, "none"):
                    fail("weather ends without a public start")
                weather = "none"
            else:
                if value not in rules["weather"]["ids"]:
                    fail("unsupported weather writer")
                effect = value.lower()
                if len(parts) > 3 and parts[3] == "[upkeep]":
                    if weather != effect:
                        fail("weather upkeep disagrees with its public start")
                else:
                    weather = effect
        elif command in ("-fieldstart", "-fieldend"):
            effect = next((effect for effect in rules["terrain"]["ids"]
                           if rules["terrain"]["public_names"][effect] == value), None)
            if effect is not None:
                has_writer = True
                if command == "-fieldstart":
                    terrain = effect
                else:
                    if terrain != effect:
                        fail("terrain ends without its current public start")
                    terrain = None
            elif value == rules["trick_room"]["effect"]:
                has_writer = True
                start = command == rules["trick_room"]["start_command"]
                if start == trick_room:
                    fail("Trick Room writer disagrees with its public lifecycle")
                trick_room = start

    view = observation.get("view")
    if not isinstance(view, Mapping) or "field" not in view:
        if has_writer:
            fail("field writers require a field view, including after a public clear")
        return  # Existing genuinely sparse legacy observations have no field evidence.
    field = view["field"]
    keys = {"weather", "terrain", "pseudo_weather", "side_conditions"}
    if not isinstance(field, Mapping):
        raise ValueError(f"{label} field must be an object")
    if set(field) != keys:
        raise ValueError(f"{label} field fields are not exact; missing={sorted(keys - set(field))}, unexpected={sorted(set(field) - keys)}")
    if any(field[key] is not None and not isinstance(field[key], str) for key in ("weather", "terrain")):
        raise ValueError(f"{label} field weather/terrain must be strings or null")
    pseudo = field["pseudo_weather"]
    if not isinstance(pseudo, list) or any(not isinstance(value, str) for value in pseudo):
        raise ValueError(f"{label} field pseudo_weather must be a string array")
    sides = field["side_conditions"]
    if not isinstance(sides, Mapping) or set(sides) != {"self", "opponent"}:
        raise ValueError(f"{label} side conditions fields are not exact")
    for side in sides.values():
        if not isinstance(side, Mapping) or any(not isinstance(key, str) or not _finite_number(value)
                                                for key, value in side.items()):
            raise ValueError(f"{label} side conditions must be finite number maps")
    if field["weather"] != weather:
        fail("weather disagrees with retained public prefix")
    if field["terrain"] != terrain:
        fail("terrain disagrees with retained public prefix")
    if ("trickroom" in pseudo) != trick_room:
        fail("Trick Room membership disagrees with retained public prefix")
