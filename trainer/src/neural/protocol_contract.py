"""Shared Showdown protocol allowlist and cross-runtime raw-record grammar."""
import json
import math
import re
from pathlib import Path


class ProtocolContractError(ValueError):
    """Raised when the shared protocol contract is missing or invalid."""


_EXPECTED_RULES = {
    "integer": {"lexeme": "ascii-decimal", "leading_zeroes": "reject", "safe_limit": 9007199254740991},
    "request": {
        "root": "object", "rqid_presence": "optional", "rqid_type": "safe-integer", "rqid_null": "reject",
        "rqid_boolean": "reject", "non_finite_numbers": "reject", "other_properties": "transient-private",
    },
    "health_condition": {
        "fainted": "0 fnt", "ratio": "positive-safe-integer-pair", "numerator_limit": "at-most-denominator",
        "statuses": ["brn", "par", "slp", "psn", "tox", "frz"],
    },
    "major_status": {
        "ids": ["brn", "par", "slp", "psn", "tox", "frz"],
        "active_target": "canonical-singles-active",
        "bare_commands": [],
        "apply_forms": [
            {"tags": []},
            {"tags": ["[from] move: Rest"], "statuses": ["slp"]},
            {"tags": ["[from] item: Flame Orb"], "statuses": ["brn"]},
            {"tags": ["[from] item: Toxic Orb"], "statuses": ["tox"]},
            {"tags": ["[from] ability: Effect Spore", "[of] opposing-active"], "statuses": ["slp", "par", "psn"]},
            {"tags": ["[from] ability: Flame Body", "[of] opposing-active"], "statuses": ["brn"]},
            {"tags": ["[from] ability: Static", "[of] opposing-active"], "statuses": ["par"]},
            {"tags": ["[from] ability: Toxic Chain", "[of] opposing-active"], "statuses": ["tox"]},
            {"tags": ["[from] ability: Poison Touch", "[of] opposing-active"], "statuses": ["psn"]},
            {"tags": ["[from] move: Sleep Powder"], "statuses": ["slp"]},
            {"tags": ["[from] move: Hypnosis"], "statuses": ["slp"]},
            {"tags": ["[from] move: Spore"], "statuses": ["slp"]},
        ],
        "cure_forms": [
            {"tags": ["[msg]"]},
            {"tags": ["[from] ability: Natural Cure"]},
            {"tags": ["[from] move: Flare Blitz"], "statuses": ["frz"]},
            {"tags": ["[from] move: Fusion Flare"], "statuses": ["frz"]},
            {"tags": ["[from] move: Pyro Ball"], "statuses": ["frz"]},
            {"tags": ["[from] move: Sacred Fire"], "statuses": ["frz"]},
            {"tags": ["[from] move: Scald"], "statuses": ["frz"]},
            {"tags": ["[from] move: Scorching Sands"], "statuses": ["frz"]},
            {"tags": ["[from] move: Hydro Steam"], "statuses": ["frz"]},
            {"tags": ["[from] move: Matcha Gotcha"], "statuses": ["frz"]},
            {"tags": ["[from] move: Steam Eruption"], "statuses": ["frz"]},
        ],
    },
    "player_ident": {
        "side_ids": ["p1", "p2"], "slots": ["", "a", "b", "c", "d", "e", "f"],
        "separator": ": ", "name": "trimmed-nonempty-text",
    },
    "hitcount": {
        "target_roles": ["active", "side-only"],
        "count_values": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    },
    "switch_drag": {"optional_tag": "[from] trimmed-nonempty-text"},
    "entry_hazard": {
        "layers": {"spikes": 3, "toxicspikes": 2, "stealthrock": 1, "stickyweb": 1},
        "start_forms": {"spikes": "Spikes", "toxicspikes": "move: Toxic Spikes", "stealthrock": "move: Stealth Rock", "stickyweb": "move: Sticky Web"},
        "removal_sources": ["Rapid Spin", "Mortal Spin", "Defog"],
    },
    "screen": {
        "ids": ["reflect", "lightscreen", "auroraveil"],
        "start_forms": {"reflect": "Reflect", "lightscreen": "move: Light Screen", "auroraveil": "move: Aurora Veil"},
        "end_forms": {"reflect": "Reflect", "lightscreen": "move: Light Screen", "auroraveil": "move: Aurora Veil"},
        "excluded_forms": ["Safeguard", "Mist"],
    },
    "court_change": {
        "command": "-swapsideconditions",
        "activation_command": "-activate",
        "activation_effect": "move: Court Change",
        "transferred_ids": ["mist", "lightscreen", "reflect", "spikes", "safeguard", "tailwind", "toxicspikes", "stealthrock", "waterpledge", "firepledge", "grasspledge", "stickyweb", "auroraveil", "luckychant"],
        "excluded_ids": ["gmaxsteelsurge", "gmaxcannonade", "gmaxvinelash", "gmaxwildfire", "gmaxvolcalith"],
    },
    "weather": {
        "ids": ["RainDance", "SunnyDay", "Sandstorm", "Snowscape"],
        "ability_origins": {
            "RainDance": ["Drizzle"],
            "SunnyDay": ["Drought", "Orichalcum Pulse"],
            "Sandstorm": ["Sand Stream"],
            "Snowscape": ["Snow Warning"],
        },
        "move_origins": {
            "RainDance": ["Rain Dance"],
            "SunnyDay": ["Sunny Day"],
            "Snowscape": ["Snowscape", "Chilly Reception"],
        },
    },
    "terrain": {
        "ids": ["electricterrain", "grassyterrain", "psychicterrain"],
        "public_names": {
            "electricterrain": "move: Electric Terrain",
            "grassyterrain": "move: Grassy Terrain",
            "psychicterrain": "move: Psychic Terrain",
        },
        "ability_origins": {
            "electricterrain": ["Electric Surge", "Hadron Engine"],
            "grassyterrain": ["Grassy Surge", "Seed Sower"],
            "psychicterrain": ["Psychic Surge"],
        },
    },
    "trick_room": {
        "effect": "move: Trick Room",
        "start_command": "-fieldstart",
        "end_command": "-fieldend",
        "source_tag": "[of]",
        "source_role": "active",
    },
    "boost_event": {
        "stats": ["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"],
        "delta_min": 0, "delta_max": 12, "set_min": -6, "set_max": 6,
        "tags": ["[from] trimmed-nonempty-text", "[silent]", "[zeffect]"],
        "tag_order": ["[from]", "[silent]", "[zeffect]"],
    },
    "health_event_tags": {
        "damage": ["[from] trimmed-nonempty-text", "[of] player-ident", "[silent]", "[partiallytrapped]"],
        "heal": ["[from] trimmed-nonempty-text", "[of] player-ident", "[silent]", "[zeffect]", "[wisher] trimmed-nonempty-text"],
        "sethp": ["[from] trimmed-nonempty-text", "[silent]"],
    },
    "health_event_tag_order": {
        "damage": ["[from]", "[of]", "[partiallytrapped]", "[silent]"],
        "heal": ["[from]", "[of]", "[wisher]", "[zeffect]", "[silent]"],
        "sethp": ["[from]", "[silent]"],
    },
    "event_tag_cardinality": {
        "damage": ["[from]", "[of]", "[silent]", "[partiallytrapped]"],
        "heal": ["[from]", "[of]", "[silent]", "[zeffect]", "[wisher]"],
        "sethp": ["[from]", "[silent]"],
        "boost": ["[from]", "[silent]", "[zeffect]"],
    },
    "heal_wisher_dependency": {
        "required_from": "[from] move: Wish",
        "required_tag_order": ["[from]", "[wisher]"],
    },
    "healing_wish_heal": {
        "required_from": "[from] move: Healing Wish",
        "required_tag_order": ["[from]"],
        "target_role": "active",
        "health": "100/100",
    },
    "future_sight": {
        "effect": "move: Future Sight", "activation_command": "-start", "resolution_command": "-end",
        "target_role": "active", "payload_fields": 1,
    },
    "repeat_use_hint": {
        "messages": [
            "Some effects can force a Pokemon to use Blood Moon again in a row.",
            "Some effects can force a Pokemon to use Gigaton Hammer again in a row.",
        ],
        "payload_fields": 1,
    },
    "item": {
        "payloads": [
            "Aguav Berry", "Adamant Crystal", "Air Balloon", "Assault Vest", "Binding Band", "Blunder Policy", "Booster Energy", "Chesto Berry", "Choice Band", "Choice Scarf", "Choice Specs", "Clear Amulet", "Cornerstone Mask", "Custap Berry", "Draco Plate", "Dread Plate", "Earth Plate", "Eviolite", "Figy Berry", "Fist Plate", "Flame Orb", "Flame Plate", "Focus Sash", "Griseous Core", "Heavy-Duty Boots", "Hearthflame Mask", "Iapapa Berry", "Icicle Plate", "Iron Plate", "Leppa Berry", "Leftovers", "Light Ball", "Light Clay", "Loaded Dice", "Lum Berry", "Lustrous Globe", "Lustrous Orb", "Mago Berry", "Magnet", "Meadow Plate", "Mind Plate", "Mystic Water", "Passho Berry", "Pixie Plate", "Power Herb", "Rindo Berry", "Rocky Helmet", "Salac Berry", "Scope Lens", "Silk Scarf", "Silver Powder", "Sky Plate", "Soul Dew", "Splash Plate", "Spooky Plate", "Sitrus Berry", "Stone Plate", "Throat Spray", "Toxic Orb", "Toxic Plate", "Weakness Policy", "Wellspring Mask", "White Herb", "Wide Lens", "Wiki Berry", "Zap Plate",
        ],
        "active_target": "canonical-singles-active",
        "dash_item_forms": [
            {"tags": [], "payloads": ["Air Balloon"]},
            {"tags": ["[from] ability: Frisk", "[of] opposing-active"]},
            {"tags": ["[from] move: Trick"]},
            {"tags": ["[from] move: Switcheroo"]},
            {"tags": ["[from] move: Recycle"], "payloads": ["White Herb"]},
        ],
        "dash_enditem_forms": [
            {"tags": [], "payloads": ["Air Balloon", "Booster Energy", "Focus Sash", "Power Herb", "Throat Spray", "Weakness Policy", "White Herb"]}, {"tags": ["[eat]"], "payloads": [
                "Aguav Berry", "Chesto Berry", "Custap Berry", "Figy Berry", "Iapapa Berry", "Leppa Berry",
                "Lum Berry", "Mago Berry", "Passho Berry", "Rindo Berry", "Salac Berry", "Sitrus Berry", "Wiki Berry",
            ]},
            {"tags": ["[from] move: Knock Off", "[of] opposing-active"]},
            {"tags": ["[silent]", "[from] move: Trick"]},
            {"tags": ["[silent]", "[from] move: Switcheroo"]},
        ],
        "bare_commands": ["item", "enditem"],
        "bare_tags": [],
    },
    "ability": {
        "dash_templates": ["reveal", "boost", "trace-copy"],
        "bare_templates": ["reveal"],
        "trace_source_tag": "[from] ability: Trace",
        "trace_of_tag": "[of] ",
        "trace_actor_role": "active",
        "trace_source_role": "opposing-active",
        "payload_domains": {
            "dash_reveal": ["Air Lock", "As One", "Beads of Ruin", "Cloud Nine", "Comatose", "Gooey", "Mirror Armor", "Mold Breaker", "Pressure", "Sturdy", "Sword of Ruin", "Tablets of Ruin", "Tangling Hair", "Teraform Zero", "Teravolt", "Turboblaze", "Unnerve", "Vessel of Ruin"],
            "dash_boost": ["Anger Shell", "Battle Bond", "Berserk", "Chilling Neigh", "Competitive", "Dauntless Shield", "Defiant", "Download", "Embody Aspect (Cornerstone)", "Embody Aspect (Hearthflame)", "Embody Aspect (Teal)", "Embody Aspect (Wellspring)", "Gooey", "Grim Neigh", "Gulp Missile", "Intimidate", "Intrepid Sword", "Justified", "Lightning Rod", "Mirror Armor", "Motor Drive", "Moxie", "Rattled", "Sap Sipper", "Soul-Heart", "Speed Boost", "Stamina", "Storm Drain", "Tangling Hair", "Thermal Exchange", "Water Compaction", "Weak Armor", "Well-Baked Body", "Wind Rider"],
            "dash_trace_copy": ["Adaptability", "Aftermath", "Air Lock", "Analytic", "Anger Shell", "Arena Trap", "Aroma Veil", "Bad Dreams", "Beads of Ruin", "Berserk", "Big Pecks", "Blaze", "Bulletproof", "Cheek Pouch", "Chilling Neigh", "Chlorophyll", "Clear Body", "Cloud Nine", "Competitive", "Compound Eyes", "Contrary", "Corrosion", "Cud Chew", "Cursed Body", "Cute Charm", "Damp", "Dancer", "Dauntless Shield", "Defiant", "Download", "Dragon's Maw", "Drizzle", "Drought", "Dry Skin", "Early Bird", "Earth Eater", "Effect Spore", "Electric Surge", "Electromorphosis", "Filter", "Flame Body", "Flash Fire", "Flower Veil", "Fluffy", "Frisk", "Full Metal Body", "Fur Coat", "Galvanize", "Good as Gold", "Gooey", "Grassy Surge", "Grim Neigh", "Gulp Missile", "Guts", "Hadron Engine", "Harvest", "Heatproof", "Heavy Metal", "Huge Power", "Hustle", "Hydration", "Ice Body", "Ice Scales", "Infiltrator", "Inner Focus", "Insomnia", "Intimidate", "Intrepid Sword", "Iron Fist", "Justified", "Keen Eye", "Leaf Guard", "Levitate", "Libero", "Light Metal", "Lightning Rod", "Limber", "Liquid Ooze", "Liquid Voice", "Magic Bounce", "Magic Guard", "Magician", "Magnet Pull", "Mega Launcher", "Mind's Eye", "Mirror Armor", "Mold Breaker", "Motor Drive", "Moxie", "Multiscale", "Mycelium Might", "Natural Cure", "No Guard", "Oblivious", "Orichalcum Pulse", "Overcoat", "Overgrow", "Own Tempo", "Pickpocket", "Pixilate", "Poison Heal", "Poison Touch", "Power Spot", "Prankster", "Pressure", "Prism Armor", "Protean", "Psychic Surge", "Punk Rock", "Pure Power", "Purifying Salt", "Queenly Majesty", "Quick Feet", "Rattled", "Reckless", "Regenerator", "Rock Head", "Rocky Payload", "Rough Skin", "Sand Force", "Sand Rush", "Sand Stream", "Sap Sipper", "Scrappy", "Seed Sower", "Serene Grace", "Shadow Shield", "Shadow Tag", "Sharpness", "Shed Skin", "Sheer Force", "Shell Armor", "Shield Dust", "Skill Link", "Slow Start", "Slush Rush", "Sniper", "Snow Warning", "Solid Rock", "Soul-Heart", "Soundproof", "Speed Boost", "Stakeout", "Stamina", "Static", "Steely Spirit", "Sticky Hold", "Storm Drain", "Strong Jaw", "Sturdy", "Supreme Overlord", "Surge Surfer", "Swarm", "Swift Swim", "Sword of Ruin", "Synchronize", "Tablets of Ruin", "Tangling Hair", "Technician", "Teravolt", "Thermal Exchange", "Thick Fat", "Tinted Lens", "Torrent", "Tough Claws", "Toxic Boost", "Toxic Chain", "Toxic Debris", "Transistor", "Triage", "Truant", "Turboblaze", "Unaware", "Unburden", "Unnerve", "Unseen Fist", "Vessel of Ruin", "Vital Spirit", "Volt Absorb", "Water Absorb", "Water Bubble", "Water Compaction", "Water Veil", "Weak Armor", "Well-Baked Body", "Wind Rider"],
            "bare_reveal": ["Air Lock", "As One", "Beads of Ruin", "Cloud Nine", "Comatose", "Gooey", "Mirror Armor", "Mold Breaker", "Pressure", "Sturdy", "Sword of Ruin", "Tablets of Ruin", "Tangling Hair", "Teraform Zero", "Teravolt", "Turboblaze", "Unnerve", "Vessel of Ruin"],
        },
        "source_evidence": {
            "dash_reveal": "data/random-battles/gen9/sets.json candidate abilities plus generated permanent form defaults intersect literal data/abilities.ts -ability emitters",
            "dash_boost": "data/random-battles/gen9/sets.json generated callbacks plus permanent form defaults reaching sim/battle.ts Battle#boost, enumerated by emitted effect.name rather than holder ability name",
            "dash_trace_copy": "data/random-battles/gen9/sets.json candidate abilities filtered by Abilities.trace.onUpdate notrace guard",
            "bare_reveal": "B02 compatibility spelling restricted to the same finite public reveal domain",
        },
    },
    "detailschange": {"condition": "optional-health-condition"},
    "trapped_activation": {"token": "-activate", "target_role": "active", "effect": "trapped", "payload_fields": 2},
    "singleturn": {
        "untagged_effects": [
            "move: Protect", "move: Beak Blast", "Crafty Shield", "move: Electrify", "move: Endure",
            "move: Focus Punch", "move: Follow Me", "Protect", "move: Magic Coat", "Mat Block",
            "Max Guard", "Powder", "Quick Guard", "move: Rage Powder", "move: Roost", "move: Shell Trap",
            "Snatch", "move: Spotlight", "Wide Guard",
        ],
        "tagged_forms": [
            {"effect": "move: Follow Me", "tag": "[zeffect]", "tag_value": "none"},
            # Helping Hand receives its source as the acting Pokemon, whose
            # Pokemon.toString() form includes an active slot.
            {"effect": "Helping Hand", "tag": "[of]", "tag_value": "player-ident", "ident_role": "active"},
        ],
    },
    "singlemove": {"forms": [["Destiny Bond"], ["Glaive Rush", "[silent]"], ["Grudge"], ["Rage"]]},
    "anim": {
        "forms": [["Spectral Thief"], ["Solar Beam"], ["Meteor Beam"], ["Dragon Darts"]],
        "actor_role": "active", "target_role": "active",
    },
    "tier": {"payload_fields": 1, "label": "nonempty-text"},
    "bigerror": {
        "auto_tie": "You will auto-tie if the battle doesn't end in <N> turn(s) (on turn 1000).",
        "turns_left_values": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500],
    },
}
_ROOT_KEYS = {
    "schema_version", "simulator", "source_basis", "framing_only_records", "supported_commands", "recognized_unsupported_commands",
    "record_fixtures", "rejection_fixtures", "disposition_rules", "validation_rules", "valid_record_controls",
}
_SIMULATOR = {"package": "pokemon-showdown", "version": "0.11.10", "format": "gen9randombattle", "mod": "gen9", "game_type": "singles"}
_DISPOSITION_KEYS = {"supported", "recognized_unsupported", "malformed_supported", "unknown", "privacy"}
_CLASSIFICATIONS = {"raw-only", "represented", "represented (bounded Topsy-Turvy)"}
_UNSUPPORTED_KINDS = {"unresolved_alias", "internal_alias", "unsupported_stop"}
_REJECTION_KINDS = {"malformed", "unknown", *_UNSUPPORTED_KINDS}


def _contract_error(detail):
    raise ProtocolContractError(f"Invalid shared protocol contract: {detail}.")


def _is_object(value):
    return isinstance(value, dict)


def _exact_keys(value, required, optional, label):
    missing = set(required) - set(value)
    extra = set(value) - set(required) - set(optional)
    if missing or extra:
        _contract_error(f"{label} keys (missing: {','.join(sorted(missing)) or 'none'}; unsupported: {','.join(sorted(extra)) or 'none'})")


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        _contract_error(f"{label} must be nonempty text")


def _text_array(value, label, nonempty=True):
    if not isinstance(value, list) or (nonempty and not value) or any(not isinstance(item, str) or not item.strip() for item in value):
        _contract_error(f"{label} must be {'a nonempty ' if nonempty else 'an '}array of nonempty strings")


def _same_json(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(_same_json(a, b) for a, b in zip(left, right))
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same_json(left[key], right[key]) for key in left)
    return left == right


def _command_token(value, label):
    if not isinstance(value, str) or not (value == "t:" or re.fullmatch(r"-?[a-z][a-z0-9]*", value)):
        _contract_error(f"{label} is not a supported protocol token")


def _record_token(record, label):
    if not isinstance(record, str) or not record.startswith("|") or "\n" in record or "\r" in record:
        _contract_error(f"{label} must be one protocol record")
    parts = record.split("|")
    return parts[1] if len(parts) > 1 else ""


def validate_protocol_contract(value):
    if not _is_object(value):
        _contract_error("root must be an object")
    _exact_keys(value, _ROOT_KEYS, set(), "root")
    if value["schema_version"] != "showdown-protocol-contract/v2":
        _contract_error("unsupported schema_version")
    if not _is_object(value["simulator"]):
        _contract_error("simulator must be an object")
    _exact_keys(value["simulator"], set(_SIMULATOR), set(), "simulator")
    if not _same_json(value["simulator"], _SIMULATOR):
        _contract_error("simulator provenance must match pokemon-showdown@0.11.10 gen9randombattle singles")
    _text_array(value["source_basis"], "source_basis")
    framing = value["framing_only_records"]
    if not isinstance(framing, list) or len(framing) != 1 or not _is_object(framing[0]):
        _contract_error("framing_only_records must define the single pinned separator record")
    _exact_keys(framing[0], {"record", "disposition", "evidence"}, set(), "framing_only_records[0]")
    if framing[0] != {
        "record": "|", "disposition": "validate then filter from public prefixes",
        "evidence": "pinned sim/battle.ts:1451,2754,2881 emits empty separator records",
    }:
        _contract_error("framing_only_records contains an unsupported or unproven record")
    if not _is_object(value["validation_rules"]) or not _same_json(value["validation_rules"], _EXPECTED_RULES):
        _contract_error("validation_rules contains unsupported or inconsistent definitions")
    if not _is_object(value["disposition_rules"]):
        _contract_error("disposition_rules must be an object")
    _exact_keys(value["disposition_rules"], _DISPOSITION_KEYS, set(), "disposition_rules")
    for key, rule in value["disposition_rules"].items():
        _text(rule, f"disposition_rules.{key}")

    supported = value["supported_commands"]
    if not isinstance(supported, list) or not supported:
        _contract_error("supported_commands must be a nonempty array")
    for index, token in enumerate(supported):
        _command_token(token, f"supported_commands[{index}]")
    supported_set = set(supported)
    if len(supported_set) != len(supported):
        _contract_error("supported_commands contains duplicate tokens")

    if not isinstance(value["recognized_unsupported_commands"], list):
        _contract_error("recognized_unsupported_commands must be an array")
    unsupported = {}
    for index, entry in enumerate(value["recognized_unsupported_commands"]):
        label = f"recognized_unsupported_commands[{index}]"
        if not _is_object(entry):
            _contract_error(f"{label} must be an object")
        _exact_keys(entry, {"token", "kind", "reason"}, {"source"}, label)
        _command_token(entry["token"], f"{label}.token")
        if not isinstance(entry["kind"], str) or entry["kind"] not in _UNSUPPORTED_KINDS:
            _contract_error(f"{label}.kind is unsupported")
        _text(entry["reason"], f"{label}.reason")
        if "source" in entry:
            _text(entry["source"], f"{label}.source")
        if entry["token"] in supported_set:
            _contract_error(f"token {entry['token']} has conflicting supported/unsupported entries")
        if entry["token"] in unsupported:
            _contract_error(f"duplicate recognized-unsupported token {entry['token']}")
        unsupported[entry["token"]] = entry["kind"]
    if "-singlemove" not in supported:
        _contract_error("-singlemove must have exact raw-evidence support")

    if not isinstance(value["record_fixtures"], list):
        _contract_error("record_fixtures must be an array")
    fixture_tokens = set()
    for index, fixture in enumerate(value["record_fixtures"]):
        label = f"record_fixtures[{index}]"
        if not _is_object(fixture):
            _contract_error(f"{label} must be an object")
        _exact_keys(fixture, {"token", "record", "inventory_classification", "grammar_summary", "evidence", "inventory_grammar", "fixture_reference"}, {"pinned_emitter_sources", "pinned_dynamic_emitter_source"}, label)
        _command_token(fixture["token"], f"{label}.token")
        if _record_token(fixture["record"], f"{label}.record") != fixture["token"]:
            _contract_error(f"{label}.token does not match its record token")
        if fixture["token"] not in supported_set:
            _contract_error(f"{label}.token is not in supported_commands")
        if fixture["token"] in fixture_tokens:
            _contract_error(f"duplicate record fixture for {fixture['token']}")
        fixture_tokens.add(fixture["token"])
        if not isinstance(fixture["inventory_classification"], str) or fixture["inventory_classification"] not in _CLASSIFICATIONS:
            _contract_error(f"{label}.inventory_classification is unsupported")
        for key in ("grammar_summary", "evidence", "fixture_reference"):
            _text(fixture[key], f"{label}.{key}")
        grammar = fixture["inventory_grammar"]
        if not _is_object(grammar):
            _contract_error(f"{label}.inventory_grammar must be an object")
        _exact_keys(grammar, {"required", "optional", "shape"}, set(), f"{label}.inventory_grammar")
        for key, item in grammar.items():
            _text(item, f"{label}.inventory_grammar.{key}")
        if "pinned_emitter_sources" in fixture:
            _text_array(fixture["pinned_emitter_sources"], f"{label}.pinned_emitter_sources")
        if "pinned_dynamic_emitter_source" in fixture:
            _text(fixture["pinned_dynamic_emitter_source"], f"{label}.pinned_dynamic_emitter_source")
    if fixture_tokens != supported_set:
        _contract_error("record_fixtures must contain exactly one fixture per supported token")

    controls = value["valid_record_controls"]
    if not isinstance(controls, list) or not controls:
        _contract_error("valid_record_controls must be a nonempty array")
    for index, control in enumerate(controls):
        label = f"valid_record_controls[{index}]"
        if not _is_object(control):
            _contract_error(f"{label} must be an object")
        _exact_keys(control, {"token", "record", "evidence", "reconstruction_scope"}, set(), label)
        _command_token(control["token"], f"{label}.token")
        if control["token"] not in supported_set or _record_token(control["record"], f"{label}.record") != control["token"]:
            _contract_error(f"{label} has inconsistent command and record tokens")
        _text(control["evidence"], f"{label}.evidence")
        _text(control["reconstruction_scope"], f"{label}.reconstruction_scope")

    if not isinstance(value["rejection_fixtures"], list):
        _contract_error("rejection_fixtures must be an array")
    for index, fixture in enumerate(value["rejection_fixtures"]):
        label = f"rejection_fixtures[{index}]"
        if not _is_object(fixture):
            _contract_error(f"{label} must be an object")
        _exact_keys(fixture, {"record", "kind"}, set(), label)
        if not isinstance(fixture["record"], str) or fixture["kind"] not in _REJECTION_KINDS:
            _contract_error(f"{label} has an unsupported rejection definition")
        token = _record_token(fixture["record"], f"{label}.record") if fixture["record"].startswith("|") else None
        if token is None and fixture["kind"] != "malformed":
            _contract_error(f"{label}.record must be a protocol record for its rejection kind")
        if fixture["kind"] == "malformed" and token is not None and token not in supported_set:
            _contract_error(f"{label} marks an unsupported token as malformed")
        if fixture["kind"] == "unknown" and token is not None and (token in supported_set or token in unsupported):
            _contract_error(f"{label} marks a classified token unknown")
        if fixture["kind"] in _UNSUPPORTED_KINDS and (token is None or unsupported.get(token) != fixture["kind"]):
            _contract_error(f"{label} does not match its recognized-unsupported disposition")
    return value


def load_protocol_contract(path=None):
    path = Path(path) if path is not None else Path(__file__).with_name("protocol_contract.json")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProtocolContractError(f"Unable to load shared protocol contract at {path}: {exc}") from exc
    return validate_protocol_contract(value)


_CONTRACT = load_protocol_contract()
SUPPORTED_COMMANDS = frozenset(_CONTRACT["supported_commands"])
RECOGNIZED_UNSUPPORTED = {item["token"]: item for item in _CONTRACT["recognized_unsupported_commands"]}
RECORD_FIXTURES = tuple(_CONTRACT["record_fixtures"])
REJECTION_FIXTURES = tuple(_CONTRACT["rejection_fixtures"])
VALID_RECORD_CONTROLS = tuple(_CONTRACT["valid_record_controls"])
VALIDATION_RULES = _CONTRACT["validation_rules"]
_JS_TRIM = "\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"


def _load_effect_inventory():
    path = Path(__file__).resolve().parents[3] / "sim-core" / "simulator_coverage" / "pokemon-showdown-0.11.10-gen9randombattle.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProtocolContractError(f"Unable to load simulator effect inventory at {path}: {exc}") from exc
    discovery = manifest.get("effect_discovery", {})
    if discovery.get("schema_version") != "simulator-effect-inventory/v1":
        raise ProtocolContractError("Simulator effect inventory schema is missing or unsupported")
    entries = {}
    for entry in [*manifest.get("condition_inventory", []), *discovery.get("additional_entries", [])]:
        identifier = entry.get("id")
        if not isinstance(identifier, str) or identifier in entries:
            raise ProtocolContractError("Simulator effect inventory has a missing or duplicate identifier")
        if entry.get("classification") not in {"represented", "raw-only", "explicitly unsupported", "unknown", "silently omitted"}:
            raise ProtocolContractError(f"Simulator effect inventory has an invalid disposition for {identifier}")
        entries[identifier] = entry
    return entries, discovery


_EFFECT_INVENTORY, _EFFECT_DISCOVERY = _load_effect_inventory()


def _effect_id(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _classify_effect_record(command, value):
    if command in ("-start", "-end"):
        family, allowed_categories = "move_volatile", {"move_volatile"}
    elif command == "-weather":
        family, allowed_categories = "weather", {"weather"}
    elif command in ("-fieldstart", "-fieldend"):
        family, allowed_categories = "field", {"pseudo_weather", "terrain"}
    elif command in ("-sidestart", "-sideend"):
        family, allowed_categories = "side_condition", {"side_condition"}
    else:
        return "represented"

    identifier = _effect_id(value)
    special = next((item for item in _EFFECT_DISCOVERY.get("special_values", [])
                    if command in item.get("commands", []) and item.get("id") == identifier), None)
    if special:
        return special["classification"]
    prefix = re.match(r"^(?:move|ability|item):\s*", value, re.IGNORECASE)
    if prefix:
        identifier = _effect_id(value[prefix.end():])
    entry = _EFFECT_INVENTORY.get(identifier)
    diagnostic = f"simulator-coverage/v1/unclassified-effect-value command={command} family={family} value={value}"
    if entry is None:
        raise ProtocolRecordError("unknown", command, diagnostic + " disposition=unknown",
                                  code="simulator-coverage/v1/unclassified-effect-value", family=family,
                                  value=value, disposition="unknown")
    if entry["classification"] == "raw-only":
        return "raw-only"
    if entry["classification"] != "represented":
        raise ProtocolRecordError("unsupported_stop", command, diagnostic + f" disposition={entry['classification']}",
                                  code="simulator-coverage/v1/unclassified-effect-value", family=family,
                                  value=value, disposition=entry["classification"])
    if entry.get("category") not in allowed_categories:
        disposition = f"family-mismatch:{entry.get('category')}"
        raise ProtocolRecordError("unsupported_stop", command, diagnostic + f" disposition={disposition}",
                                  code="simulator-coverage/v1/unclassified-effect-value", family=family,
                                  value=value, disposition=disposition)
    return "represented"
class ProtocolRecordError(ValueError):
    def __init__(self, kind, command, message, *, code=None, family=None, value=None, disposition=None):
        super().__init__(message)
        self.kind = kind
        self.command = command
        self.code = code
        self.family = family
        self.value = value
        self.disposition = disposition


def _malformed(command, detail=""):
    suffix = f": {detail}" if detail else "."
    raise ProtocolRecordError("malformed", command, f"Malformed raw {command} record{suffix}")


def _field(parts, index, command, label="field"):
    if index >= len(parts) or not parts[index].strip(_JS_TRIM):
        _malformed(command, f"{label} is required")


def _is_player_ident(value, active_required=False):
    if not isinstance(value, str) or value != value.strip(_JS_TRIM) or "|" in value:
        return False
    rules = VALIDATION_RULES["player_ident"]
    separator = rules["separator"]
    prefix, found, name = value.partition(separator)
    if not found or not name or name != name.strip(_JS_TRIM):
        return False
    side, slot = prefix[:2], prefix[2:]
    return side in rules["side_ids"] and slot in rules["slots"] and (not active_required or bool(slot))


def _is_side_only_player_ident(value):
    rules = VALIDATION_RULES["player_ident"]
    return _is_player_ident(value) and any(value.startswith(side + rules["separator"]) for side in rules["side_ids"])


def _hitcount_target(parts, index, command):
    _field(parts, index, command, "pokemon identifier")
    value = parts[index]
    if not _is_player_ident(value):
        _malformed(command, "invalid pokemon identifier")
    separator = VALIDATION_RULES["player_ident"]["separator"]
    prefix = value.partition(separator)[0]
    side, slot = prefix[:2], prefix[2:]
    role = "active" if slot == "a" else "side-only" if slot == "" else None
    if side not in VALIDATION_RULES["player_ident"]["side_ids"] or role not in VALIDATION_RULES["hitcount"]["target_roles"]:
        _malformed(command, "target must be a Gen 9 singles active or post-faint side-only ident")


def _hitcount(parts, index, command):
    _integer(parts, index, command, "hit count")
    if int(parts[index]) not in VALIDATION_RULES["hitcount"]["count_values"]:
        _malformed(command, "hit count is outside the pinned Gen 9 Random Battle domain")


def _ident(parts, index, command):
    _field(parts, index, command, "pokemon identifier")
    if not _is_player_ident(parts[index], active_required=True):
        _malformed(command, "invalid pokemon identifier")


def _target(parts, index, command):
    _field(parts, index, command, "target")
    if parts[index] != "-" and not _is_player_ident(parts[index], active_required=True):
        _malformed(command, "invalid target")


def _player(parts, index, command):
    _field(parts, index, command, "player")
    if parts[index] not in ("p1", "p2"):
        _malformed(command, "invalid player")


def _integer(parts, index, command, label, signed=False):
    _field(parts, index, command, label)
    pattern = r"(?:0|[1-9][0-9]*|-[1-9][0-9]*)" if signed else r"(?:0|[1-9][0-9]*)"
    if not re.fullmatch(pattern, parts[index]) or abs(int(parts[index])) > VALIDATION_RULES["integer"]["safe_limit"]:
        _malformed(command, f"{label} must be a safe integer")


def _valid_health_condition(value):
    rules = VALIDATION_RULES["health_condition"]
    if value == rules["fainted"]:
        return True
    match = re.fullmatch(r"([1-9][0-9]*)/([1-9][0-9]*)(?: ([a-z]+))?", value)
    if not match:
        return False
    numerator, denominator = map(int, match.group(1, 2))
    limit = VALIDATION_RULES["integer"]["safe_limit"]
    return numerator <= denominator and numerator <= limit and denominator <= limit and (match.group(3) is None or match.group(3) in rules["statuses"])


def _health_condition(parts, index, command):
    _field(parts, index, command, "condition")
    if not _valid_health_condition(parts[index]):
        _malformed(command, "invalid health condition")


def _tag_kind(tag):
    return tag.split(" ", 1)[0]


def _event_tags(parts, start, command, rules, order, singleton_kinds):
    tags = parts[start:]
    seen_tags = set()
    seen_kinds = set()
    previous_order = -1
    for tag in tags:
        valid = False
        for rule in rules:
            if tag == rule:
                valid = True
                break
            prefix, separator, kind = rule.partition(" ")
            if not separator or not tag.startswith(prefix + " "):
                continue
            value = tag[len(prefix) + 1:]
            if not value or value != value.strip(_JS_TRIM):
                continue
            if kind == "trimmed-nonempty-text" or (kind == "player-ident" and _is_player_ident(value)):
                valid = True
                break
        if not valid:
            _malformed(command, "invalid tag")
        kind = _tag_kind(tag)
        if kind in singleton_kinds and kind in seen_kinds:
            _malformed(command, "duplicate singleton tag kind")
        if tag in seen_tags:
            _malformed(command, "duplicate tag")
        seen_tags.add(tag)
        seen_kinds.add(kind)
        index = order.index(kind)
        if index < previous_order:
            _malformed(command, "tags are out of source order")
        previous_order = index


def _heal_wisher_dependency(parts, command):
    tags = parts[4:]
    if not any(_tag_kind(tag) == "[wisher]" for tag in tags):
        return
    dependency = VALIDATION_RULES["heal_wisher_dependency"]
    if (len(tags) != len(dependency["required_tag_order"])
            or tags[0] != dependency["required_from"]
            or [_tag_kind(tag) for tag in tags] != dependency["required_tag_order"]):
        _malformed(command, "[wisher] requires its exact Wish source form")


def _healing_wish_dependency(parts, command):
    tags = parts[4:]
    # The pinned base-data healing emitter in this name family is Healing Wish.
    # Ordinary heals retain their existing grammar; malformed attempted Healing
    # Wish provenance cannot cross the public publication boundary.
    if not any(tag.startswith("[from] move: Healing") for tag in tags):
        return
    dependency = VALIDATION_RULES["healing_wish_heal"]
    if (len(parts) != 5
            or parts[4] != dependency["required_from"]
            or not _is_player_ident(parts[2], active_required=True)
            or parts[3] != dependency["health"]
            or dependency["required_tag_order"] != ["[from]"]):
        _malformed(command, "Healing Wish requires its exact source form")


def _future_sight_dependency(parts, command):
    effect = parts[3] if len(parts) > 3 else ""
    # The generic start/end grammar stays available for its existing raw-only
    # families. Pinned Future Sight emits neither tags nor private slot state.
    # Match source-family spelling attempts before exact comparison so leading
    # whitespace or an extra separator cannot fall through to generic start/end.
    if not (re.search(r"future\s*sight", effect, re.IGNORECASE)
            or re.match(r"^\s*move[\s:]+future", effect, re.IGNORECASE)):
        return
    dependency = VALIDATION_RULES["future_sight"]
    if command not in (dependency["activation_command"], dependency["resolution_command"]):
        return
    if (len(parts) != dependency["payload_fields"] + 3
            or effect != dependency["effect"]
            or not _is_player_ident(parts[2], active_required=dependency["target_role"] == "active")):
        _malformed(command, "Future Sight requires its exact source form")


def _repeat_use_hint_dependency(parts, command):
    message = parts[2] if len(parts) > 2 else ""
    if not re.match(r"^\s*Some\s+effects\s+can\s+force\s+a\s+Pokemon\s+to\s+use\b", message, re.IGNORECASE):
        return
    dependency = VALIDATION_RULES["repeat_use_hint"]
    if len(parts) != dependency["payload_fields"] + 2 or message not in dependency["messages"]:
        _malformed(command, "repeat-use hint requires its exact source form")


def _entry_hazard(parts, command):
    if command not in ("-sidestart", "-sideend"):
        return
    rules = VALIDATION_RULES["entry_hazard"]
    effect_value = parts[3] if len(parts) > 3 else ""
    effect = _effect_id(re.sub(r"^move:\s*", "", effect_value, flags=re.IGNORECASE))
    if effect not in rules["layers"]:
        return
    if not _is_side_only_player_ident(parts[2]):
        _malformed(command, "hazard side must be canonical")
    titles = {"spikes": "Spikes", "toxicspikes": "Toxic Spikes", "stealthrock": "Stealth Rock", "stickyweb": "Sticky Web"}
    if command == "-sidestart":
        if len(parts) != 4 or parts[3] != rules["start_forms"][effect]:
            _malformed(command, "unsupported entry-hazard start form")
        return
    if parts[3] != titles[effect]:
        if not (effect == "toxicspikes" and parts[3] == "move: Toxic Spikes" and len(parts) == 5
                and parts[4].startswith("[of] ") and _is_player_ident(parts[4][5:], active_required=True)):
            _malformed(command, "unsupported entry-hazard end form")
        return
    if len(parts) == 4:
        return
    if (len(parts) != 6 or not parts[4].startswith("[from] move: ") or not parts[5].startswith("[of] ")
            or parts[4][13:] not in rules["removal_sources"] or not _is_player_ident(parts[5][5:], active_required=True)):
        _malformed(command, "unsupported entry-hazard removal form")



def _screen_record(parts, command):
    if command not in ("sidestart", "-sidestart", "sideend", "-sideend"):
        return
    rules = VALIDATION_RULES["screen"]
    effect_value = parts[3] if len(parts) > 3 else ""
    effect = _effect_id(re.sub(r"^move:\s*", "", effect_value, flags=re.IGNORECASE))
    if effect not in rules["ids"]:
        if effect in (_effect_id(value) for value in rules["excluded_forms"]):
            _malformed(command, "unsupported generated screen form")
        return
    expected = (rules["start_forms"].get(effect) if command == "-sidestart"
                else rules["end_forms"].get(effect) if command == "-sideend" else None)
    if (not expected or len(parts) != 4 or parts[3] != expected
            or not _is_side_only_player_ident(parts[2])):
        _malformed(command, "unsupported screen source form")


def _court_change_record(parts, command):
    rules = VALIDATION_RULES["court_change"]
    if command == "swapsideconditions":
        _malformed(command, "Court Change emits only the pinned dash command")
    if command == rules["command"]:
        if len(parts) != 2:
            _malformed(command, "Court Change has no participants, tags, or payload")
        return True
    if command != rules["activation_command"]:
        return False
    effect = parts[3] if len(parts) > 3 else ""
    if not re.search(r"court\s*change", effect, re.IGNORECASE):
        return False
    if (len(parts) != 4 or effect != rules["activation_effect"]
            or not _is_player_ident(parts[2], active_required=True)
            or not re.match(r"^p[12]a: ", parts[2])):
        _malformed(command, "Court Change requires an active source and its exact source form")
    return False


def _weather_record(parts, command):
    if command != "-weather":
        return
    rules = VALIDATION_RULES["weather"]
    effect = parts[2] if len(parts) > 2 else ""
    if effect == "none":
        if len(parts) != 3:
            _malformed(command, "clear has no tags")
        return
    if effect not in rules["ids"]:
        _malformed(command, "unsupported generated weather")
    if len(parts) == 3 and rules["move_origins"].get(effect):
        return
    if len(parts) == 4 and parts[3] == "[upkeep]":
        return
    if len(parts) == 5 and parts[3].startswith("[from] ability: ") and parts[4].startswith("[of] "):
        ability, source = parts[3][16:], parts[4][5:]
        if (ability in rules["ability_origins"].get(effect, [])
                and _is_player_ident(source, active_required=True) and re.match(r"^p[12]a: ", source)):
            return
    _malformed(command, "unsupported source grammar")

def _terrain_record(parts, command):
    if command not in ("fieldstart", "-fieldstart", "fieldend", "-fieldend", "-fieldactivate"):
        return
    rules = VALIDATION_RULES["terrain"]
    effect = parts[2] if len(parts) > 2 else ""
    terrain_id = next((identifier for identifier, name in rules["public_names"].items() if name == effect), None)
    if terrain_id is None:
        # Existing pseudo-weather field records retain their own grammar. Any
        # terrain-name spelling attempt is fail-closed below rather than using
        # that generic family as an escape hatch.
        if re.search(r"terrain", effect, re.IGNORECASE):
            _malformed(command, "unsupported generated terrain")
        return
    if command in ("fieldstart", "fieldend", "-fieldactivate"):
        _malformed(command, "terrain uses the pinned dash command")
    if command == "-fieldend":
        if len(parts) != 3:
            _malformed(command, "terrain clear has no tags")
        return
    if (len(parts) == 5 and parts[3].startswith("[from] ability: ") and parts[4].startswith("[of] ")):
        ability, source = parts[3][16:], parts[4][5:]
        if (ability in rules["ability_origins"][terrain_id]
                and _is_player_ident(source, active_required=True) and re.match(r"^p[12]a: ", source)):
            return
    _malformed(command, "unsupported terrain source grammar")


def _trick_room_record(parts, command):
    if command not in ("fieldstart", "-fieldstart", "fieldend", "-fieldend", "-fieldactivate"):
        return
    rules = VALIDATION_RULES["trick_room"]
    effect = parts[2] if len(parts) > 2 else ""
    if _effect_id(re.sub(r"^move:\s*", "", effect, flags=re.IGNORECASE)) != "trickroom":
        return
    if effect != rules["effect"]:
        _malformed(command, "unsupported Trick Room effect spelling")
    if command == rules["end_command"]:
        if len(parts) != 3:
            _malformed(command, "Trick Room clear has no tags")
        return
    if command == rules["start_command"] and len(parts) == 4 and parts[3].startswith(rules["source_tag"] + " "):
        source = parts[3][len(rules["source_tag"]) + 1:]
        if _is_player_ident(source, active_required=True) and re.match(r"^p[12]a: ", source):
            return
    _malformed(command, "unsupported Trick Room source grammar")


def _ability_event(parts, command):
    rules = VALIDATION_RULES["ability"]
    if len(parts) < 4:
        _malformed(command)
    _ident(parts, 2, command)
    _field(parts, 3, command, "ability")
    if parts[3] != parts[3].strip(_JS_TRIM):
        _malformed(command, "invalid ability")
    def require_payload(domain):
        if parts[3] not in rules["payload_domains"][domain]:
            _malformed(command, f"ability payload is outside the {domain} source-proven domain")

    if len(parts) == 4:
        require_payload("bare_reveal" if command == "ability" else "dash_reveal")
        return
    if command == "ability":
        _malformed(command, "compatibility alias has only the plain reveal template")
    if len(parts) == 5 and parts[4] == "boost":
        require_payload("dash_boost")
        return
    if (len(parts) == 6 and parts[4] == rules["trace_source_tag"]
            and parts[5].startswith(rules["trace_of_tag"])):
        source = parts[5][len(rules["trace_of_tag"]):]
        if (not _is_player_ident(source, active_required=True)
                or parts[2][:2] == source[:2]):
            _malformed(command, "Trace source must be an opposing active ident")
        require_payload("dash_trace_copy")
        return
    _malformed(command, "unsupported ability provenance")


def _item_event(parts, command):
    rules = VALIDATION_RULES["item"]
    if len(parts) < 4:
        _malformed(command)
    actor = parts[2]
    if not _is_player_ident(actor, active_required=True) or not re.match(r"^p[12]a: ", actor):
        _malformed(command, "target must be a Gen 9 singles active ident")
    item = parts[3]
    if item != item.strip(_JS_TRIM) or item not in rules["payloads"]:
        _malformed(command, "item payload is outside the generated source domain")
    tags = parts[4:]
    if command in rules["bare_commands"]:
        if tags:
            _malformed(command, "compatibility form has no tags")
        return
    forms = rules["dash_item_forms"] if command == "-item" else rules["dash_enditem_forms"]
    matching = None
    for form in forms:
        expected = form["tags"]
        if len(expected) == len(tags) and all(
            tag == actual or tag == "[of] opposing-active"
            for tag, actual in zip(expected, tags)
        ):
            matching = form
            break
    if matching is None or ("payloads" in matching and item not in matching["payloads"]):
        _malformed(command, "unsupported item source grammar")
    if "[of] opposing-active" in matching["tags"]:
        tag = tags[matching["tags"].index("[of] opposing-active")]
        prefix = "[of] "
        source = tag[len(prefix):] if tag.startswith(prefix) else ""
        if (not _is_player_ident(source, active_required=True) or not re.match(r"^p[12]a: ", source)
                or source[:2] == actor[:2]):
            _malformed(command, "source must be an opposing Gen 9 singles active ident")


def _major_status_event(parts, command):
    rules = VALIDATION_RULES["major_status"]
    if len(parts) < 4:
        _malformed(command)
    target = parts[2]
    if not _is_player_ident(target, active_required=True) or not re.match(r"^p[12]a: ", target):
        _malformed(command, "target must be a Gen 9 singles active ident")
    status = parts[3]
    if status not in rules["ids"]:
        _malformed(command, "unsupported major status")
    tags = parts[4:]
    if command in rules["bare_commands"]:
        if tags:
            _malformed(command, "compatibility form has no tags")
        return
    forms = rules["apply_forms"] if command == "-status" else rules["cure_forms"]
    matching = None
    for form in forms:
        expected = form["tags"]
        if len(expected) == len(tags) and all(
            tag == actual or tag == "[of] opposing-active"
            for tag, actual in zip(expected, tags)
        ):
            matching = form
            break
    if matching is None or ("statuses" in matching and status not in matching["statuses"]):
        _malformed(command, "unsupported major-status source grammar")
    if "[of] opposing-active" in matching["tags"]:
        tag = tags[matching["tags"].index("[of] opposing-active")]
        source = tag[len("[of] "):] if tag.startswith("[of] ") else ""
        if (not _is_player_ident(source, active_required=True) or not re.match(r"^p[12]a: ", source)
                or source[:2] == target[:2]):
            _malformed(command, "source must be an opposing Gen 9 singles active ident")


def _auto_tie_warning(parts, command):
    if len(parts) != 3:
        _malformed(command)
    match = re.fullmatch(r"You will auto-tie if the battle doesn't end in ([1-9][0-9]*) (turn|turns) \(on turn 1000\)\.", parts[2])
    if match is None:
        _malformed(command, "unsupported diagnostic")
    turns_left = int(match.group(1))
    if (turns_left not in VALIDATION_RULES["bigerror"]["turns_left_values"]
            or (turns_left == 1 and match.group(2) != "turn")
            or (turns_left != 1 and match.group(2) != "turns")):
        _malformed(command, "unsupported diagnostic")


def _request_constant(token):
    raise ValueError(f"non-standard JSON number {token}")


def _finite_json_tree(value):
    if isinstance(value, float) and not math.isfinite(value):
        return False
    if isinstance(value, dict):
        return all(_finite_json_tree(child) for child in value.values())
    if isinstance(value, list):
        return all(_finite_json_tree(child) for child in value)
    return True


def _request(parts, command):
    payload = "|".join(parts[2:])
    if not payload:
        _malformed(command)
    try:
        value = json.loads(payload, parse_constant=_request_constant)
    except (json.JSONDecodeError, TypeError, ValueError):
        _malformed(command)
    if not isinstance(value, dict) or not _finite_json_tree(value):
        _malformed(command)
    if "rqid" in value:
        rqid = value["rqid"]
        if type(rqid) not in (int, float) or (isinstance(rqid, float) and (not math.isfinite(rqid) or not rqid.is_integer())):
            _malformed(command, "invalid request rqid")
        if abs(rqid) > VALIDATION_RULES["integer"]["safe_limit"]:
            _malformed(command, "invalid request rqid")


def _move_target(parts, index, command):
    _field(parts, index, command, "target")
    if not _is_player_ident(parts[index]):
        _malformed(command, "invalid target")


def _move_null_target(parts, index, command):
    tags = parts[index + 1:]
    source_tags = tags[:-1]
    is_from = lambda tag: bool(re.fullmatch(r"\[from\]\s+.+", tag))
    is_anim = lambda tag: bool(re.fullmatch(r"\[anim\].+", tag))
    order_ok = (len(source_tags) <= 1 and all(is_from(tag) or is_anim(tag) for tag in source_tags)) or (
        len(source_tags) == 2 and is_anim(source_tags[0]) and is_from(source_tags[1])
    )
    if parts[index] != "null" or not tags or tags[-1] != "[notarget]" or tags.count("[notarget]") != 1 or not order_ok:
        _malformed(command, "invalid target")


def _move_tag(tag):
    return tag in ("[still]", "[miss]", "[notarget]", "[zeffect]") or bool(
        re.fullmatch(r"\[from\]\s+.+", tag)
        or re.fullmatch(r"\[anim\].+", tag)
        or re.fullmatch(r"\[spread\]\s+p[12][a-f](?:,p[12][a-f])+", tag)
    )


def _shape(parts, command):
    def at_least(size):
        if len(parts) < size:
            _malformed(command)

    def ident(index=2):
        _ident(parts, index, command)

    if _court_change_record(parts, command):
        return

    if command in {
        "clearallboost", "-clearallboost",
        "teampreview", "clearpoke", "done", "upkeep", "start", "end", "-nothing",
    }:
        if not (len(parts) == 2 or (len(parts) == 3 and parts[2] == "")):
            _malformed(command)
        return
    if command == "tie":
        if not (len(parts) == 2 or (len(parts) == 3 and parts[2] == "")):
            _malformed(command)
    elif command in ("gen", "turn"):
        if len(parts) != 3:
            _malformed(command)
        _integer(parts, 2, command, "value")
    elif command == "player":
        if len(parts) < 4:
            _malformed(command)
        _player(parts, 2, command); _field(parts, 3, command, "name")
    elif command == "teamsize":
        if len(parts) != 4:
            _malformed(command)
        _player(parts, 2, command); _integer(parts, 3, command, "team size")
    elif command == "request":
        at_least(3); _request(parts, command)
    elif command == "move":
        at_least(4); ident()
        _field(parts, 3, command, "move")
        if len(parts) > 4 and parts[4] != "":
            if parts[4] == "null": _move_null_target(parts, 4, command)
            else: _move_target(parts, 4, command)
        tags = parts[5:]
        if tags.count("[notarget]") > 1 or ("[notarget]" in tags and tags[-1] != "[notarget]") or any(not _move_tag(tag) for tag in tags):
            _malformed(command, "invalid tag")
    elif command == "-singlemove":
        ident()
        if not re.match(r"^p[12]a: ", parts[2]):
            _malformed(command, "target must be a Gen 9 singles active ident")
        if parts[3:] not in VALIDATION_RULES["singlemove"]["forms"]:
            _malformed(command, "unsupported effect/tag combination")
    elif command == "-singleturn":
        if len(parts) not in (4, 5): _malformed(command)
        ident(); _field(parts, 3, command, "effect")
        if len(parts) == 5:
            tag = parts[4]
            effect = parts[3]
            matching_form = next((form for form in VALIDATION_RULES["singleturn"]["tagged_forms"]
                if form["effect"] == effect and (
                    tag == form["tag"] if form["tag_value"] == "none"
                    else tag.startswith(form["tag"] + " ")
                )), None)
            if matching_form is None:
                _malformed(command, "unsupported single-turn effect/tag combination")
            if matching_form["tag_value"] == "player-ident":
                source_ident = tag[len(matching_form["tag"]) + 1:]
                if not _is_player_ident(source_ident, active_required=matching_form.get("ident_role") == "active"):
                    _malformed(command, "invalid single-turn source ident")
        elif parts[3] not in VALIDATION_RULES["singleturn"]["untagged_effects"]:
            _malformed(command, "unsupported untagged effect")
    elif command == "cant":
        at_least(4); ident(); _field(parts, 3, command, "reason")
        if len(parts) > 4: _field(parts, 4, command, "move")
    elif command == "-hitcount":
        if len(parts) != 4: _malformed(command)
        _hitcount_target(parts, 2, command); _hitcount(parts, 3, command)
    elif command == "faint":
        if len(parts) != 3: _malformed(command)
        ident()
    elif command in ("switch", "drag"):
        if len(parts) not in (5, 6): _malformed(command)
        ident(); _field(parts, 3, command, "details"); _health_condition(parts, 4, command)
        if len(parts) == 6:
            rule = VALIDATION_RULES["switch_drag"]["optional_tag"]
            tag_prefix = rule.split(" ", 1)[0] + " "
            source_name = parts[5][len(tag_prefix):]
            if not parts[5].startswith(tag_prefix) or not source_name or source_name != source_name.strip(_JS_TRIM):
                _malformed(command, "invalid source tag")
        if len(parts) > 6: _malformed(command)
    elif command == "detailschange":
        if len(parts) not in (4, 5): _malformed(command)
        ident(); _field(parts, 3, command, "details")
        if len(parts) == 5: _health_condition(parts, 4, command)
    elif command == "replace":
        if len(parts) not in (4, 5): _malformed(command)
        ident(); _field(parts, 3, command, "details")
        if len(parts) == 5 and not _valid_health_condition(parts[4]):
            _malformed(command, "invalid replace condition")
    elif command == "-invertboost":
        if len(parts) != 4 or parts[3] != "[from] move: Topsy-Turvy":
            _malformed(command, "unsupported inversion grammar")
        ident()
    elif command == "-copyboost":
        if len(parts) != 5 or parts[4] != "[from] move: Psych Up":
            _malformed(command, "unsupported copy grammar")
        ident(); _ident(parts, 3, command)
    elif command == "-anim":
        if len(parts) != 5 or [parts[3]] not in VALIDATION_RULES["anim"]["forms"]:
            _malformed(command, "unsupported animation grammar")
        ident(); _ident(parts, 4, command)
        actor_side, target_side = parts[2].split(": ", 1)[0], parts[4].split(": ", 1)[0]
        if actor_side not in ("p1a", "p2a") or target_side not in ("p1a", "p2a") or actor_side == target_side:
            _malformed(command, "source and target must be opposing Gen 9 singles active identifiers")
    elif command == "-hint":
        at_least(3); _field(parts, 2, command, "message"); _repeat_use_hint_dependency(parts, command)
    elif command == "poke":
        at_least(4); _player(parts, 2, command); _field(parts, 3, command, "details")
    elif command in ("formechange", "-formechange"):
        at_least(4); ident(); _field(parts, 3, command, "species")
    elif command == "transform":
        at_least(4); ident(); _field(parts, 3, command, "target")
    elif command == "-transform":
        at_least(4); ident(); _ident(parts, 3, command)
    elif command in ("damage", "-damage", "heal", "-heal", "sethp", "-sethp"):
        at_least(4)
        revival_bench = command == "-heal" and len(parts) == 5 and parts[4] == "[from] move: Revival Blessing" and _is_side_only_player_ident(parts[2])
        if not revival_bench: ident()
        _health_condition(parts, 3, command)
        tag_group = command.removeprefix("-")
        _event_tags(parts, 4, command, VALIDATION_RULES["health_event_tags"][tag_group],
                    VALIDATION_RULES["health_event_tag_order"][tag_group],
                    VALIDATION_RULES["event_tag_cardinality"][tag_group])
        if command == "-heal":
            _heal_wisher_dependency(parts, command)
            _healing_wish_dependency(parts, command)
    elif command in ("status", "-status", "curestatus", "-curestatus"):
        _major_status_event(parts, command)
    elif command in ("boost", "-boost", "unboost", "-unboost", "setboost", "-setboost"):
        at_least(5); ident(); _field(parts, 3, command, "stat")
        if parts[3] not in VALIDATION_RULES["boost_event"]["stats"]:
            _malformed(command, "invalid stat")
        _integer(parts, 4, command, "amount", signed=command in ("setboost", "-setboost"))
        amount = int(parts[4])
        rules = VALIDATION_RULES["boost_event"]
        minimum, maximum = ((rules["set_min"], rules["set_max"]) if command in ("setboost", "-setboost") else (rules["delta_min"], rules["delta_max"]))
        if not minimum <= amount <= maximum:
            _malformed(command, "amount is outside the supported stage range")
        _event_tags(parts, 5, command, rules["tags"], rules["tag_order"],
                    VALIDATION_RULES["event_tag_cardinality"]["boost"])
    elif command in ("clearboost", "-clearboost"):
        if len(parts) != 3: _malformed(command)
        ident()
    elif command in ("clearnegativeboost", "-clearnegativeboost"):
        if len(parts) < 3 or len(parts) > 4 or (len(parts) == 4 and parts[3] not in ("[silent]", "[zeffect]")): _malformed(command)
        ident()
    elif command in ("clearpositiveboost", "-clearpositiveboost"):
        if len(parts) != 5: _malformed(command)
        ident(); _ident(parts, 3, command); _field(parts, 4, command, "effect")
    elif command in ("start", "-start", "end", "-end"):
        at_least(4); ident(); _field(parts, 3, command, "effect")
        if command in ("-start", "-end"):
            _future_sight_dependency(parts, command)
    elif command in ("weather", "-weather", "fieldstart", "-fieldstart", "fieldend", "-fieldend", "-fieldactivate"):
        at_least(3); _field(parts, 2, command, "effect")
        _weather_record(parts, command)
        _terrain_record(parts, command)
        _trick_room_record(parts, command)
    elif command == "-message":
        at_least(3); _field(parts, 2, command, "message")
    elif command in ("activate", "-activate"):
        at_least(4); ident(); _field(parts, 3, command, "effect")
        _court_change_record(parts, command)
        trapped = VALIDATION_RULES["trapped_activation"]
        if command == trapped["token"] and parts[3].strip(_JS_TRIM) == trapped["effect"]:
            if parts[3] != trapped["effect"] or len(parts) != trapped["payload_fields"] + 2:
                _malformed(command, "trapped activation must use the exact source grammar")
    elif command in ("sidestart", "-sidestart", "sideend", "-sideend"):
        at_least(4)
        if not re.match(r"^p[12](?::|$)", parts[2]): _malformed(command)
        _field(parts, 3, command, "condition")
        _entry_hazard(parts, command)
        _screen_record(parts, command)
    elif command in ("item", "-item", "enditem", "-enditem"):
        _item_event(parts, command)
    elif command in ("ability", "-ability"):
        _ability_event(parts, command)
    elif command == "tier":
        if len(parts) != VALIDATION_RULES["tier"]["payload_fields"] + 2: _malformed(command)
        _field(parts, 2, command, "format label")
    elif command in ("terastallize", "-terastallize"):
        at_least(4); ident(); _field(parts, 3, command, "type")
    elif command == "win":
        if len(parts) != 3: _malformed(command)
        _field(parts, 2, command, "winner")
    elif command in ("block", "-block"):
        at_least(4); ident(); _field(parts, 3, command, "effect")
    elif command in ("miss", "-miss"):
        at_least(4); ident(2); ident(3)
    elif command in ("hitcount", "-hitcount"):
        at_least(4); ident(); _integer(parts, 3, command, "count")
    elif command in ("crit", "-crit", "supereffective", "-supereffective", "resisted", "-resisted", "immune", "-immune", "mustrecharge", "-mustrecharge"):
        if len(parts) < 3: _malformed(command)
        ident()
    elif command in ("fail", "-fail"):
        at_least(3); ident()
        if len(parts) > 3: _field(parts, 3, command, "action")
    elif command in ("prepare", "-prepare"):
        at_least(4); ident(); _field(parts, 3, command, "move")
        if len(parts) > 4: _target(parts, 4, command)
    elif command in ("inactive", "inactiveoff"):
        at_least(3); _field(parts, 2, command, "message")
    elif command == "rated":
        if len(parts) > 3 or (len(parts) == 3 and not parts[2].strip(_JS_TRIM)): _malformed(command)
    elif command == "t:":
        if len(parts) != 3: _malformed(command)
        _integer(parts, 2, command, "timestamp")
    elif command in ("c", "chat"):
        at_least(4); _field(parts, 2, command, "user"); _field(parts, 3, command, "message")
    elif command in ("error", "gametype", "rule", "message"):
        at_least(3); _field(parts, 2, command, "payload")
    elif command == "bigerror":
        _auto_tie_warning(parts, command)
    elif len(parts) < 3 or any(not part.strip(_JS_TRIM) for part in parts[2:]):
        _malformed(command)


def validate_protocol_record(record):
    """Validate one exact public protocol line before routing or publication."""
    if not isinstance(record, str) or not record.startswith("|") or "\n" in record or "\r" in record:
        raise ProtocolRecordError("malformed", "", "Malformed raw protocol record")
    if record == _CONTRACT["framing_only_records"][0]["record"]:
        return
    parts = record.split("|")
    command = parts[1] if len(parts) > 1 else ""
    if command in RECOGNIZED_UNSUPPORTED:
        kind = RECOGNIZED_UNSUPPORTED[command]["kind"]
        raise ProtocolRecordError(kind, command, f"unsupported raw protocol event: {command}")
    if command not in SUPPORTED_COMMANDS:
        raise ProtocolRecordError("unknown", command, f"unsupported raw protocol event: {command or '<empty>'}")
    _shape(parts, command)
    if command in ("-start", "-end"):
        _classify_effect_record(command, parts[3])
    elif command in ("-weather", "-fieldstart", "-fieldend"):
        _classify_effect_record(command, parts[2])
    elif command in ("-sidestart", "-sideend"):
        _classify_effect_record(command, parts[3])
