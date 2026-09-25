"""Shared Showdown protocol allowlist and cross-runtime raw-record grammar."""
import json
import re
from pathlib import Path


_CONTRACT = json.loads(Path(__file__).with_name("protocol_contract.json").read_text(encoding="utf-8"))
SUPPORTED_COMMANDS = frozenset(_CONTRACT["supported_commands"])
RECOGNIZED_UNSUPPORTED = {item["token"]: item for item in _CONTRACT["recognized_unsupported_commands"]}
RECORD_FIXTURES = tuple(_CONTRACT["record_fixtures"])
REJECTION_FIXTURES = tuple(_CONTRACT["rejection_fixtures"])
_JS_TRIM = "\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
_IDENT = re.compile(r"p[12][a-z]:\s*[^|]+")
_PLAYER_IDENT = re.compile(r"p[12](?:[a-f])?:\s*[^|]+")


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


def _ident(parts, index, command):
    _field(parts, index, command, "pokemon identifier")
    if not _IDENT.fullmatch(parts[index].strip(_JS_TRIM)):
        _malformed(command, "invalid pokemon identifier")


def _player_ident(parts, index, command):
    _field(parts, index, command, "pokemon identifier")
    if not _PLAYER_IDENT.fullmatch(parts[index].strip(_JS_TRIM)):
        _malformed(command, "invalid pokemon identifier")


def _target(parts, index, command):
    _field(parts, index, command, "target")
    if parts[index] != "-" and not _PLAYER_IDENT.fullmatch(parts[index].strip(_JS_TRIM)):
        _malformed(command, "invalid target")


def _player(parts, index, command):
    _field(parts, index, command, "player")
    if parts[index] not in ("p1", "p2"):
        _malformed(command, "invalid player")


def _integer(parts, index, command, label, signed=False):
    _field(parts, index, command, label)
    pattern = r"-?\d+" if signed else r"\d+"
    if not re.fullmatch(pattern, parts[index]) or abs(int(parts[index])) > 9007199254740991:
        _malformed(command, f"{label} must be a safe integer")


def _request(parts, command):
    payload = "|".join(parts[2:])
    if not payload:
        _malformed(command)
    try:
        value = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        _malformed(command)
    if not isinstance(value, dict):
        _malformed(command)
    rqid = value.get("rqid")
    if rqid is not None and (type(rqid) is not int and not (type(rqid) is float and rqid.is_integer())):
        _malformed(command, "invalid request rqid")
    if rqid is not None and abs(rqid) > 9007199254740991:
        _malformed(command, "invalid request rqid")


def _move_target(parts, index, command):
    _field(parts, index, command, "target")
    if not _PLAYER_IDENT.fullmatch(parts[index].strip(_JS_TRIM)):
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
        at_least(4); ident(); _field(parts, 3, command, "effect")
    elif command == "cant":
        at_least(4); ident(); _field(parts, 3, command, "reason")
        if len(parts) > 4: _field(parts, 4, command, "move")
    elif command == "-hitcount":
        at_least(4); ident(); _integer(parts, 3, command, "hit count")
    elif command == "faint":
        if len(parts) != 3: _malformed(command)
        ident()
    elif command in ("switch", "drag", "detailschange"):
        at_least(5); ident(); _field(parts, 3, command, "details"); _field(parts, 4, command, "condition")
    elif command == "replace":
        if len(parts) not in (4, 5): _malformed(command)
        ident(); _field(parts, 3, command, "details")
        if len(parts) == 5 and not re.fullmatch(r"(?:0 fnt|\d+(?:/[1-9]\d*)?(?: (?:brn|par|slp|psn|tox|frz))?)", parts[4]):
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
        ident(); _player_ident(parts, 4, command)
    elif command == "-hint":
        at_least(3); _field(parts, 2, command, "message")
    elif command == "poke":
        at_least(4); _player(parts, 2, command); _field(parts, 3, command, "details")
    elif command in ("formechange", "-formechange"):
        at_least(4); ident(); _field(parts, 3, command, "species")
    elif command in ("transform", "-transform"):
        at_least(4); ident(); _field(parts, 3, command, "target")
    elif command in ("damage", "-damage", "heal", "-heal", "sethp", "-sethp"):
        at_least(4)
        revival_bench = command == "-heal" and len(parts) == 5 and parts[4] == "[from] move: Revival Blessing" and bool(re.fullmatch(r"p[12]:\s*[^|]+", parts[2]))
        if not revival_bench: ident()
        _field(parts, 3, command, "condition")
    elif command in ("status", "-status", "curestatus", "-curestatus"):
        at_least(4); ident(); _field(parts, 3, command, "status")
    elif command in ("boost", "-boost", "unboost", "-unboost", "setboost", "-setboost"):
        at_least(5); ident(); _field(parts, 3, command, "stat")
        _integer(parts, 4, command, "amount", signed=command in ("setboost", "-setboost"))
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
        if len(parts) != 3: _malformed(command)
        ident()
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
    parts = record.split("|")
    command = parts[1] if len(parts) > 1 else ""
    if command in RECOGNIZED_UNSUPPORTED:
        kind = RECOGNIZED_UNSUPPORTED[command]["kind"]
        raise ProtocolRecordError(kind, command, f"unsupported raw protocol event: {command}")
    if command not in SUPPORTED_COMMANDS:
        raise ProtocolRecordError("unknown", command, f"unsupported raw protocol event: {command or '<empty>'}")
    _shape(parts, command)
