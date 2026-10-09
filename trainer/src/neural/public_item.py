"""Ordered public item possession; missing target is unknown, None is absent."""
import re
from .public_health import bound_owned_target, terminal_owner


def _ident(value):
    return re.sub(r"^(p[12])a: ", r"\1: ", value)


def project_public_items(prefix):
    items, active, prior = {}, {}, {}
    for line in prefix:
        parts = line.split("|")
        if len(parts) < 3:
            continue
        command, target = parts[1], _ident(parts[2])
        if not re.match(r"^p[12]: .+", target):
            continue
        side = target[:2]
        if command in ("switch", "drag"):
            prior[side] = (target, target in items, items.get(target))
            active[side] = target
            items.pop(target, None)
        elif command == "replace":
            appearance = active.get(side)
            if appearance and appearance != target:
                if appearance in items:
                    items[target] = items[appearance]
                else:
                    items.pop(target, None)
                saved = prior.get(side)
                if saved and saved[0] == appearance and saved[1]:
                    items[appearance] = saved[2]
                else:
                    items.pop(appearance, None)
            active[side] = target
        elif command in ("-item", "item"):
            items[target] = re.sub(r"[^a-z0-9]", "", parts[3].lower())
        elif command in ("-enditem", "enditem"):
            items[target] = None
    return items


def ambiguous_owned_item_targets(prefix, perspective, owners):
    ambiguous = set()
    if not any(row.get("ability") == "illusion" or row.get("base_ability") == "illusion" for row in owners):
        return ambiguous
    appearance, writer, revealed = None, False, False
    for line in prefix:
        parts = line.split("|")
        if len(parts) < 3: continue
        target = _ident(parts[2])
        if target[:2] != perspective: continue
        if parts[1] in ("switch", "drag"):
            if appearance and writer and not revealed: ambiguous.add(appearance)
            appearance, writer, revealed = target, False, False
        elif parts[1] == "replace":
            appearance, revealed = target, True
        elif parts[1] in ("-item", "item", "-enditem", "enditem") and target == appearance:
            writer = True
    return ambiguous


def validate_public_items(observation, predecessor=None):
    def fail(message):
        raise ValueError("Public item evidence mismatch: " + message)
    view, perspective = observation.get("view", {}), observation.get("perspective")
    request = observation.get("request")
    owners = request.get("side", []) if isinstance(request, dict) else []
    rows = []
    for team in ("self_team", "opponent_team"):
        roster = view.get(team, [])
        if not isinstance(roster, list):
            fail(team + " must be an array")
        rows.extend((team, row) for row in roster)
    dispositions = project_public_item_dispositions(observation["protocol_prefix"])
    magic_room = False
    for line in observation["protocol_prefix"]:
        parts = line.split("|")
        if len(parts) > 2 and re.sub(r"[^a-z0-9]", "", parts[2].lower()) in ("magicroom", "movemagicroom"):
            if parts[1] == "-fieldstart": magic_room = True
            if parts[1] == "-fieldend": magic_room = False
    facts = project_public_items(observation["protocol_prefix"])
    from .public_health import owned_appearance
    appearance = owned_appearance(observation["protocol_prefix"], perspective)
    history_owners = owners or (predecessor.get("request") or {}).get("side", []) if terminal_owner(predecessor, observation) else owners
    ambiguous = ambiguous_owned_item_targets(observation["protocol_prefix"], perspective, history_owners)
    owned_history = {target: state for target, state in project_public_owned_item_history(observation, predecessor).items() if target[:2] == perspective}
    for team, row in rows:
        if team != "self_team":
            continue
        history = owned_history.get(_ident(row.get("ident", "")), {})
        if row.get("last_item") and row["last_item"] != history.get("last_item"):
            fail("owned last item has no matching retained public writer")
        if row.get("item_state") in ("consumed", "removed") and row["item_state"] != history.get("item_state"):
            fail("owned disposition has no matching retained public writer")
    for target, history in owned_history.items():
        matching = [row for team, row in rows if team == "self_team" and _ident(row.get("ident", "")) == target]
        if (len(matching) != 1 or matching[0].get("last_item") != history["last_item"]
                or matching[0].get("item", object()) is None and matching[0].get("item_state") != history["item_state"]):
            fail("owned retained item history is omitted or disagrees with public writer")
    for target, item in facts.items():
        team = "self_team" if target[:2] == perspective else "opponent_team"
        if team == "self_team" and target in ambiguous and target != appearance: continue
        bound = bound_owned_target(observation, target, predecessor) if team == "self_team" else target
        matching = [(side, row) for side, row in rows if _ident(row.get("ident", "")) == bound]
        if len(matching) != 1 or matching[0][0] != team:
            fail(target + " requires exactly one " + team + " row")
        row = matching[0][1]
        if team == "opponent_team":
            if ("item" in row if item is None else row.get("item") != "has-item"):
                fail(target + " public presence disagrees with ordered item evidence")
        else:
            owner = next((entry for entry in owners if "item" in entry and _ident(entry.get("ident", "")) == bound), None)
            expected = owner.get("item") or None if owner is not None else item
            if (row.get("item", object()) is not None if expected is None else
                    row.get("item") != expected if expected else not row.get("item")):
                fail(target + " owned item disagrees with evidence")
            if owner is not None and (bool(owner.get("item")) if item is None else
                                      not owner.get("item") or bool(item and owner["item"] != item)):
                fail(target + " request/public item disagree")
    for target, state in dispositions.items():
        if target[:2] != perspective or target in ambiguous and target != appearance:
            continue
        bound = bound_owned_target(observation, target, predecessor)
        row = next((row for team, row in rows if team == "self_team" and _ident(row.get("ident", "")) == bound), None)
        if row is None or row.get("item_state") != state["item_state"] or "last_item" in state and row.get("last_item") != state["last_item"]:
            fail(target + " owned disposition/last item disagrees with public writer")
        if row.get("item_suppressed") is not magic_room:
            fail(target + " owned item suppression disagrees with public Magic Room evidence")
    for team, row in rows:
        if team == "self_team" and "item_suppressed" in row and row["item_suppressed"] is not magic_room:
            fail("owned item suppression disagrees with public Magic Room evidence")
    for team, row in rows:
        if team == "opponent_team" and "item" in row and row["item"] != "has-item":
            fail("opponent item field may only publish an evidenced presence marker")
        if team == "opponent_team" and row.get("item") == "has-item" and facts.get(_ident(row.get("ident", ""))) is None:
            fail("opponent presence has no eligible public item witness")
    authority = terminal_owner(predecessor, observation)
    if authority:
        expected_items = {_ident(row["ident"]): row.get("item") or None for row in predecessor["request"]["side"] if "item" in row}
        expected_history = {_ident(row["ident"]): {"last_item": row["last_item"], "item_state": row["item_state"]}
            for row in predecessor["view"]["self_team"] if row.get("last_item") and "item_state" in row}
        from .public_health import owned_appearance
        current_appearance = owned_appearance(predecessor["protocol_prefix"], perspective)
        current_actual = _ident(next(row["ident"] for row in predecessor["request"]["side"] if row.get("active")))
        for line in observation["protocol_prefix"][len(predecessor["protocol_prefix"]):]:
            parts = line.split("|")
            if len(parts) < 3:
                continue
            target = _ident(parts[2])
            if parts[1] in ("switch", "drag", "replace") and target[:2] == perspective:
                current_appearance = target; current_actual = authority[1]
            bound = current_actual if target == current_appearance else target
            if bound[:2] == perspective:
                if parts[1] in ("-item", "item"):
                    expected_items[bound] = re.sub(r"[^a-z0-9]", "", parts[3].lower())
                    if bound in expected_history: expected_history[bound]["item_state"] = "held"
                if parts[1] in ("-enditem", "enditem"):
                    expected_items[bound] = None
                    expected_history[bound] = project_public_item_dispositions([line])[target]
        for target, history in expected_history.items():
            matching = [row for team, row in rows if team == "self_team" and _ident(row.get("ident", "")) == target]
            if len(matching) != 1 or any(matching[0].get(key, object()) != value for key, value in history.items()):
                fail("terminal owned item history disagrees with committed predecessor and public writers")
        for target, item in expected_items.items():
            matching = [row for team, row in rows if team == "self_team" and _ident(row.get("ident", "")) == target]
            if len(matching) != 1 or matching[0].get("item", object()) != item:
                fail("terminal owned item disagrees with committed predecessor and public writers")
    for owner in owners:
        if "item" not in owner:
            continue
        matching = [row for team, row in rows if team == "self_team" and _ident(row.get("ident", "")) == _ident(owner["ident"])]
        if len(matching) != 1 or matching[0].get("item", object()) != (owner.get("item") or None):
            fail("owned item requires exactly one matching addressed-request row")
        if owner.get("item") and matching[0].get("item_state") != "held":
            fail("owned held item requires held disposition")
        if not owner.get("item") and matching[0].get("item_state") == "held":
            fail("owned absent item cannot assert held disposition")
        if matching[0].get("item_suppressed") is not magic_room:
            fail("owned item suppression requires public Magic Room evidence")


def project_public_item_dispositions(prefix):
    states, active, prior = {}, {}, {}
    for line in prefix:
        parts = line.split("|")
        if len(parts) < 3: continue
        command, target = parts[1], _ident(parts[2])
        if not re.match(r"^p[12]: .+", target): continue
        side = target[:2]
        if command in ("switch", "drag"):
            prior[side] = states.get(target)
            active[side] = target
            states.pop(target, None)
        elif command == "replace":
            appearance = active.get(side)
            if appearance and appearance != target:
                if appearance in states: states[target] = states[appearance]
                else: states.pop(target, None)
                if prior.get(side) is not None: states[appearance] = prior[side]
                else: states.pop(appearance, None)
            active[side] = target
        elif command in ("-item", "item", "-enditem", "enditem"):
            item = re.sub(r"[^a-z0-9]", "", parts[3].lower())
            end = command in ("-enditem", "enditem")
            consumed = any("[eat]" in tag or "[from] gem" in tag for tag in parts[4:]) or len(parts) == 4 and item != "airballoon"
            states[target] = {**states.get(target, {}), "item_state": ("consumed" if consumed else "removed") if end else "held"}
            if end: states[target]["last_item"] = item
    return states


def _replay_public_item_history(prefix, ambiguous_carriers=False):
    """Historical end-item assertions never infer current possession after a switch."""
    history, active, touched, prior, revealed = {}, {}, {}, {}, {}
    if not any(line.startswith(("|-enditem|", "|enditem|")) for line in prefix):
        return history, active, touched, prior
    for line in prefix:
        parts = line.split("|")
        if len(parts) < 3:
            continue
        target = _ident(parts[2]); side = target[:2]
        if not re.match(r"^p[12]: .+", target):
            continue
        if parts[1] in ("switch", "drag"):
            departed = active.get(side)
            if ambiguous_carriers and departed and touched.get(side) and not revealed.get(side):
                if prior.get(side): history[departed] = prior[side]
                else: history.pop(departed, None)
            active[side] = target; prior[side] = history.get(target); touched[side] = False; revealed[side] = False
        elif parts[1] == "replace":
            appearance = active.get(side)
            if touched.get(side) and appearance and appearance != target:
                history[target] = history[appearance]
                if prior.get(side): history[appearance] = prior[side]
                else: history.pop(appearance, None)
            active[side] = target; touched[side] = False; revealed[side] = True
        elif parts[1] in ("-enditem", "enditem"):
            item = re.sub(r"[^a-z0-9]", "", parts[3].lower())
            consumed = any("[eat]" in tag or "[from] gem" in tag for tag in parts[4:]) or len(parts) == 4 and item != "airballoon"
            history[target] = {"item_state": "consumed" if consumed else "removed", "last_item": item}
            if active.get(side) == target: touched[side] = True
    return history, active, touched, prior


def project_public_item_history(prefix):
    return _replay_public_item_history(prefix)[0]


def project_public_owned_item_history(observation, predecessor=None):
    perspective = observation.get("perspective")
    request = observation.get("request")
    owners = request.get("side", []) if isinstance(request, dict) else []
    history_owners = owners or (predecessor.get("request") or {}).get("side", []) if terminal_owner(predecessor, observation) else owners
    history, active, touched, prior = _replay_public_item_history(observation["protocol_prefix"],
        any(row.get("ability") == "illusion" or row.get("base_ability") == "illusion" for row in history_owners))
    appearance = active.get(perspective)
    actual = bound_owned_target(observation, appearance, predecessor) if appearance and touched.get(perspective) else None
    if touched.get(perspective) and actual and actual != appearance:
        history[actual] = history[appearance]
        if prior.get(perspective): history[appearance] = prior[perspective]
        else: history.pop(appearance, None)
    return history
