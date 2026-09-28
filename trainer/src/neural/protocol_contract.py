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
    "player_ident": {
        "side_ids": ["p1", "p2"], "slots": ["", "a", "b", "c", "d", "e", "f"],
        "separator": ": ", "name": "trimmed-nonempty-text",
    },
    "switch_drag": {"optional_tag": "[from] trimmed-nonempty-text"},
    "boost_event": {
        "stats": ["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"],
        "delta_min": 0, "delta_max": 12, "set_min": -6, "set_max": 6,
        "tags": ["[from] trimmed-nonempty-text", "[silent]", "[zeffect]"],
    },
    "health_event_tags": {
        "damage": ["[from] trimmed-nonempty-text", "[of] player-ident", "[silent]", "[partiallytrapped]"],
        "heal": ["[from] trimmed-nonempty-text", "[of] player-ident", "[silent]", "[zeffect]", "[wisher] trimmed-nonempty-text"],
        "sethp": ["[from] trimmed-nonempty-text", "[silent]"],
    },
    "detailschange": {"condition": "optional-health-condition"},
    "endability": {"forms": ["target-only", "move-source"], "move_source_tag": "[from] move: "},
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
    "tier": {"payload_fields": 1, "label": "nonempty-text"},
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
    if unsupported.get("-singlemove") != "unsupported_stop":
        _contract_error("-singlemove must remain a recognized unsupported stop")

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
class ProtocolRecordError(ValueError):
    def __init__(self, kind, command, message):
        super().__init__(message)
        self.kind = kind
        self.command = command


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


def _event_tags(parts, start, command, rules):
    tags = parts[start:]
    if len(set(tags)) != len(tags):
        _malformed(command, "duplicate tag")
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

    if command in {
        "clearallboost", "-clearallboost", "swapsideconditions", "-swapsideconditions",
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
        at_least(4); ident(); _integer(parts, 3, command, "hit count")
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
        if len(parts) != 5 or parts[3] != "Spectral Thief":
            _malformed(command, "unsupported animation grammar")
        ident(); _ident(parts, 4, command)
    elif command == "-hint":
        at_least(3); _field(parts, 2, command, "message")
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
        _event_tags(parts, 4, command, VALIDATION_RULES["health_event_tags"][tag_group])
    elif command in ("status", "-status", "curestatus", "-curestatus"):
        at_least(4); ident(); _field(parts, 3, command, "status")
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
        _event_tags(parts, 5, command, rules["tags"])
    elif command in ("clearboost", "-clearboost"):
        if len(parts) != 3: _malformed(command)
        ident()
    elif command in ("clearnegativeboost", "-clearnegativeboost"):
        if len(parts) < 3 or len(parts) > 4 or (len(parts) == 4 and parts[3] not in ("[silent]", "[zeffect]")): _malformed(command)
        ident()
    elif command in ("clearpositiveboost", "-clearpositiveboost"):
        at_least(5); ident(); _ident(parts, 3, command); _field(parts, 4, command, "effect")
    elif command in ("start", "-start", "end", "-end"):
        at_least(4); ident(); _field(parts, 3, command, "effect")
    elif command in ("weather", "-weather", "fieldstart", "-fieldstart", "fieldend", "-fieldend", "-fieldactivate"):
        at_least(3); _field(parts, 2, command, "effect")
    elif command == "-message":
        at_least(3); _field(parts, 2, command, "message")
    elif command in ("activate", "-activate"):
        at_least(4); ident(); _field(parts, 3, command, "effect")
    elif command in ("sidestart", "-sidestart", "sideend", "-sideend"):
        at_least(4)
        if not re.match(r"^p[12](?::|$)", parts[2]): _malformed(command)
        _field(parts, 3, command, "condition")
    elif command in ("item", "-item", "enditem", "-enditem"):
        at_least(4); ident(); _field(parts, 3, command, "item")
    elif command in ("ability", "-ability"):
        at_least(4); ident(); _field(parts, 3, command, "ability")
    elif command in ("endability", "-endability"):
        if command == "-endability" and len(parts) == 5:
            ident(); _field(parts, 3, command, "old ability")
            move_name = parts[4][len(VALIDATION_RULES["endability"]["move_source_tag"]):]
            if not parts[4].startswith(VALIDATION_RULES["endability"]["move_source_tag"]) or not move_name or move_name != move_name.strip(_JS_TRIM):
                _malformed(command, "invalid move-source tag")
            return
        if len(parts) != 3: _malformed(command)
        ident()
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
