"""Independent public and addressed-request health consequence validation."""
import math
import re


def _ident(value):
    return re.sub(r"^(p[12])a: ", r"\1: ", value)


def _condition(value):
    parts = value.split(" ")
    hp = parts[0]
    status = parts[1] if len(parts) > 1 else None
    numerator, denominator = (hp.split("/") + [None])[:2]
    return {"hp_text": hp, "hp_ratio": 0 if status == "fnt" else float(numerator) / float(denominator),
            "fainted": status == "fnt", "status": status if status != "fnt" else None}


def project_public_health(prefix):
    health, active, appearance_prior = {}, {}, {}
    for line in prefix:
        parts = line.split("|")
        command = parts[1] if len(parts) > 1 else ""
        target = _ident(parts[2] if len(parts) > 2 else "")
        if not re.fullmatch(r"p[12]: .+", target):
            continue
        side = target[:2]
        if command in ("switch", "drag"):
            outgoing = active.get(side)
            if outgoing in health:
                health[outgoing]["active"] = False
            active[side] = target
            appearance_prior[side] = dict(health[target]) if target in health else None
        if command == "replace":
            prior = active.get(side)
            if prior and prior != target:
                health[target] = dict(health.get(prior, {}))
                if appearance_prior.get(side) is not None:
                    health[prior] = appearance_prior[side]
                else:
                    health.pop(prior, None)
            active[side] = target
        state = health.setdefault(target, {})
        if command in ("switch", "drag", "replace"):
            state["active"] = True
        field = (4 if command in ("switch", "drag", "replace", "detailschange", "-detailschange")
                 else 3 if command in ("-damage", "-heal", "-sethp", "damage", "heal", "sethp") else None)
        if field is not None and len(parts) > field and parts[field]:
            next_state = _condition(parts[field])
            if next_state["fainted"] and command in ("-damage", "-sethp", "damage", "sethp"):
                next_state.pop("status")
            state.update(next_state)
        if command in ("-status", "status"):
            state["status"] = parts[3]
        if command in ("-curestatus", "curestatus"):
            state["status"] = None
        if command == "faint":
            state.update(hp_text="0", hp_ratio=0, fainted=True, status=None, active=False)
    return {ident: state for ident, state in health.items() if state}


def owned_appearance(prefix, perspective):
    appearance = None
    for line in prefix:
        parts = line.split("|")
        if len(parts) > 2 and parts[1] in ("switch", "drag", "replace") and parts[2].startswith(str(perspective) + "a: "):
            appearance = _ident(parts[2])
    return appearance


def terminal_owner(predecessor, successor):
    """Internal: predecessor semantics and the enclosing joins must be validated first."""
    def fail(message):
        raise ValueError("Public health evidence mismatch: " + message)
    if predecessor is None or successor.get("request") is not None or successor.get("view", {}).get("terminated") is not True:
        return None
    prefix, next_prefix = predecessor["protocol_prefix"], successor["protocol_prefix"]
    perspective = predecessor["perspective"]
    owners = (predecessor.get("request") or {}).get("side", [])
    active = [row for row in owners if row.get("active")]
    appearance = owned_appearance(prefix, perspective)
    if (predecessor.get("battle_id") != successor.get("battle_id") or predecessor.get("schema_version") != successor.get("schema_version")
            or perspective != successor.get("perspective") or not appearance or len(active) != 1
            or len(next_prefix) < len(prefix) or next_prefix[:len(prefix)] != prefix):
        fail("terminal predecessor authority is discontinuous")
    actual = _ident(active[0]["ident"])
    if not actual.startswith(perspective + ": "):
        fail("terminal predecessor owner is foreign")
    def roster(view):
        if not isinstance(view.get("self_team"), list): fail("terminal owned roster must be an array")
        return [[row.get(key) for key in ("slot", "ident", "name", "base_species")] for row in view.get("self_team", [])]
    if roster(predecessor["view"]) != roster(successor["view"]):
        fail("terminal owned roster identity/order changed")
    suffix = next_prefix[len(prefix):]
    switches = [line for line in suffix if line.split("|")[1] in ("switch", "drag") and line.split("|")[2].startswith(perspective + "a: ")]
    if switches:
        final_appearance = owned_appearance(next_prefix, perspective)
        revealed = any(line.startswith("|replace|" + perspective + "a: ") for line in suffix)
        no_illusion = all(isinstance(row.get("ability"), str) and row["ability"] and row["ability"] != "illusion" and isinstance(row.get("base_ability"), str) and row["base_ability"] and row["base_ability"] != "illusion" for row in owners)
        if len(switches) != 1 or not final_appearance or sum(_ident(row["ident"]) == final_appearance for row in owners) != 1:
            fail("terminal switched appearance lacks sufficient owned identity authority")
        action = getattr(predecessor, "terminal_action", None)
        incoming = next((row for row in owners if row.get("slot") == action.get("switch_slot")), None) if action and action.get("kind") == "switch" and switches[0].startswith("|switch|") else None
        if not revealed and incoming:
            actual = _ident(incoming["ident"])
            if actual != final_appearance and incoming.get("ability") != "illusion":
                fail("terminal switch appearance disagrees with submitted owned action")
        else:
            if not revealed and not no_illusion:
                fail("terminal switched appearance lacks sufficient owned identity authority")
            actual = final_appearance
        if incoming and revealed and _ident(incoming["ident"]) != final_appearance:
            fail("terminal revealed switch disagrees with submitted owned action")
        appearance = final_appearance
    for line in suffix:
        parts = line.split("|")
        if len(parts) < 3 or not parts[2].startswith(perspective + "a: "):
            continue
        if parts[1] == "replace" and _ident(parts[2]) != actual:
            fail("terminal replacement disagrees with predecessor owner")
    return appearance, actual


def bound_owned_target(observation, target, predecessor=None):
    request = observation.get("request")
    owners = request.get("side", []) if isinstance(request, dict) else []
    appearance = owned_appearance(observation["protocol_prefix"], observation.get("perspective"))
    active = next((row for row in owners if row.get("active")), None)
    if target == appearance and active is not None:
        actual = _ident(active["ident"])
        if actual != appearance and (active.get("ability") != "illusion"
                or sum(_ident(row.get("ident", "")) == appearance for row in owners) != 1):
            raise ValueError("Public health evidence mismatch: owned appearance lacks legitimate Illusion roster authority")
        return actual
    authority = terminal_owner(predecessor, observation)
    return authority[1] if authority and target == authority[0] and appearance == authority[0] else target


def validate_public_health(observation, predecessor=None):
    def fail(message):
        raise ValueError("Public health evidence mismatch: " + message)

    projected = project_public_health(observation["protocol_prefix"])
    view = observation.get("view", {})
    request = observation.get("request")
    owners = request.get("side", []) if isinstance(request, dict) else []
    appearance = None
    for line in observation["protocol_prefix"]:
        parts = line.split("|")
        if len(parts) > 2 and parts[1] in ("switch", "drag", "replace") and parts[2].startswith(str(observation.get("perspective")) + "a: "):
            appearance = _ident(parts[2])
    owner_active = next((entry for entry in owners if entry.get("active")), None)
    rows = []
    for team in ("self_team", "opponent_team"):
        roster = view.get(team, [])
        if not isinstance(roster, list):
            fail(f"{team} must be an array")
        rows.extend((team, row) for row in roster)
    self_rows = [row for team, row in rows if team == "self_team"]
    if owners and (len(self_rows) != len(owners) or any(_ident(self_rows[index].get("ident", "")) != _ident(owner["ident"]) for index, owner in enumerate(owners))):
        fail("owned roster identity/order disagrees with addressed request")
    for target, public_state in projected.items():
        team = "self_team" if target[:2] == observation.get("perspective") else "opponent_team"
        bound_target = bound_owned_target(observation, target, predecessor) if team == "self_team" else target
        matching = [(side, row) for side, row in rows if _ident(row.get("ident", "")) == bound_target]
        if len(matching) != 1 or matching[0][0] != team:
            fail(f"{target} requires exactly one {team} row")
        row = matching[0][1]
        owner = next((entry for entry in owners if _ident(entry.get("ident", "")) == bound_target), None) if team == "self_team" else None
        owner_public_precision = (owner is None and team == "self_team" and isinstance(row.get("hp_text"), str)
                                  and "/" in row["hp_text"] and "/100" in public_state.get("hp_text", ""))
        expected = {**_condition(owner["condition"]), "active": bool(owner["active"] and not _condition(owner["condition"])["fainted"])} if owner is not None else public_state
        for key, value in expected.items():
            if owner_public_precision and key in ("hp_text", "hp_ratio"):
                continue
            if key not in row or row[key] != value:
                fail(f"{target} {key} disagrees with {'owner request' if owner is not None else 'public prefix'}")
        if owner_public_precision:
            exact = _condition(row["hp_text"])["hp_ratio"]
            percentage = 0 if exact == 0 else min(99 if exact < 1 else 100, math.ceil(exact * 100))
            if row.get("hp_ratio") != exact or percentage / 100 != public_state["hp_ratio"]:
                fail(f"{target} owner/public HP disagree")
        if owner is not None and target == appearance and "hp_ratio" in public_state and "/100" in public_state.get("hp_text", ""):
            exact = expected["hp_ratio"]
            percentage = 0 if exact == 0 else min(99 if exact < 1 else 100, math.ceil(exact * 100))
            if percentage / 100 != public_state["hp_ratio"]:
                fail(f"{target} request/public HP disagree")
        if owner is not None and target == appearance and "fainted" in public_state and public_state["fainted"] != expected["fainted"]:
            fail(f"{target} request/public faint disagree")
        if owner is not None and target == appearance and owner.get("active") and "status" in public_state and public_state["status"] != expected["status"]:
            fail(f"{target} request/public status disagree")
    for owner in owners:
        target = _ident(owner["ident"])
        matching = [row for team, row in rows if team == "self_team" and _ident(row.get("ident", "")) == target]
        if len(matching) != 1:
            fail(f"{target} owner request requires exactly one self_team row")
        for key, value in {**_condition(owner["condition"]), "active": bool(owner["active"] and not _condition(owner["condition"])["fainted"])}.items():
            if key not in matching[0] or matching[0][key] != value:
                fail(f"{target} {key} disagrees with owner request")
