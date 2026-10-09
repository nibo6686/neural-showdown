"""Owned ability effectiveness from public Gas witnesses and addressed-request exemptions."""
import json
from pathlib import Path
import re
from .public_health import terminal_owner
from .protocol_contract import VALIDATION_RULES

_MANIFEST = Path(__file__).resolve().parents[3] / "sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json"
with _MANIFEST.open(encoding="utf-8") as _source:
    _contract = json.load(_source)["public_ability_effectiveness"]
_CANTSUPPRESS = frozenset(_contract["cantsuppress"])
_NOTRANSFORM = frozenset(_contract["notransform"])
_REPLACEMENT_BASE_WRITERS = {"terapagosstellar": "teraformzero", "ogerpontealtera": "embodyaspectteal",
                            "ogerponwellspringtera": "embodyaspectwellspring", "ogerponhearthflametera": "embodyaspecthearthflame",
                            "ogerponcornerstonetera": "embodyaspectcornerstone"}


def _id(value):
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _ident(value):
    return re.sub(r"^(p[12])a: ", r"\1: ", value)


def public_gas_sources(prefix):
    sources, active = set(), {}
    for line in prefix:
        parts = line.split("|")
        if len(parts) < 3:
            continue
        command, target = parts[1], _ident(parts[2])
        side = target[:2]
        effect = parts[3] if len(parts) > 3 else None
        if command in ("switch", "drag"):
            sources.discard(active.get(side))
            active[side] = target
        elif (command in ("faint", "-transform", "-endability")
              or command == "-end" and effect == "ability: Neutralizing Gas"
              or command == "-start" and _id(effect) == "gastroacid"):
            sources.discard(target)
        elif command == "-ability":
            if _id(effect) == "neutralizinggas":
                sources.add(target)
            else:
                sources.discard(target)
    return sources


def _local_suppression(prefix):
    suppressed, active = set(), {}
    for line in prefix:
        parts = line.split("|")
        if len(parts) < 3:
            continue
        command, target = parts[1], _ident(parts[2])
        side = target[:2]
        if command in ("switch", "drag"):
            suppressed.discard(active.get(side)); suppressed.discard(target); active[side] = target
        elif command in ("faint", "-ability", "-transform", "-formechange"):
            suppressed.discard(target)
        elif command == "-endability" and len(parts) == 3:
            suppressed.add(target)
    return suppressed


def public_revealed_abilities(prefix):
    """Supported public reveal names; the opposing Trace [of] stays raw."""
    facts, active = {}, {}
    def clear(target):
        row = facts.get(target)
        if row is None: return
        row.update(ability=row["base"], state="known" if row["base"] else "unknown", cleared=True)
    for line in prefix:
        parts = line.split("|")
        if len(parts) < 3: continue
        command, target = parts[1], _ident(parts[2])
        side = target[:2]
        if command in ("switch", "drag"):
            clear(active.get(side)); clear(target); active[side] = target
        elif command == "faint": clear(target)
        elif command == "replace":
            facts.pop(active.get(side), None); active[side] = target
        elif command in ("detailschange", "-formechange", "-transform"):
            row = facts.setdefault(target, dict(ability=None, base=None, state="unknown", copied=False, cleared=False, invalidated=None, base_writer=None))
            if command == "detailschange" and preserves_owned_ability_for_form(parts[3], row["ability"], row["base"]): continue
            row.update(ability=None, state="unknown", cleared=False, invalidated="transform" if command == "-transform" else "form")
            row["base_writer"] = _REPLACEMENT_BASE_WRITERS.get(_id(parts[3].split(",")[0])) if command == "detailschange" else None
            if row["invalidated"] == "form": row.update(base=None, copied=False)
        elif command in ("-ability", "ability"):
            template = ("bare_reveal" if command == "ability" and len(parts) == 4
                        else "dash_reveal" if command == "-ability" and len(parts) == 4
                        else "dash_boost" if command == "-ability" and len(parts) == 5 and parts[4] == "boost"
                        else "dash_trace_copy" if command == "-ability" and len(parts) == 6 and parts[4] == "[from] ability: Trace" else None)
            if template is None or parts[3] not in VALIDATION_RULES["ability"]["payload_domains"][template]: continue
            row = facts.setdefault(target, dict(ability=None, base=None, state="unknown", copied=False, cleared=False, invalidated=None, base_writer=None))
            changed = any(tag.startswith("[from]") for tag in parts[4:])
            if (not changed and not row["base"] and not row["copied"] and row["invalidated"] != "transform"
                    and (row["invalidated"] != "form" or row["base_writer"] == _id(parts[3]))): row["base"] = _id(parts[3])
            row.update(ability=_id(parts[3]), state="changed" if changed else "known", cleared=False)
            row["copied"] |= len(parts) > 4 and parts[4] == "[from] ability: Trace"
    return facts


def public_trace_abilities(prefix):
    return {target: row for target, row in public_revealed_abilities(prefix).items() if row["copied"]}


def preserves_owned_ability_for_form(species, ability, base):
    preserved = {"mimikyubusted": "disguise", "eiscue": "iceface", "eiscuenoice": "iceface", "palafinhero": "zerotohero"}
    expected = preserved.get(_id(species.split(",")[0]))
    return bool(expected) and ability == expected and base == expected


def owned_ability_after_suffix(owner, suffix):
    ability, base = owner.get("ability") or None, owner.get("base_ability") or None
    base_writer = None
    target = _ident(owner["ident"])
    active = bool(owner.get("active"))
    for line in suffix:
        parts = line.split("|")
        if len(parts) < 3: continue
        command, addressed = parts[1], _ident(parts[2])
        if command in ("switch", "drag") and addressed[:2] == target[:2]:
            if active or addressed == target: ability = base
            active = addressed == target
        if addressed != target: continue
        if command == "faint": ability, active = base, False
        elif command == "-transform": ability, base_writer = None, None
        elif command == "detailschange" and not preserves_owned_ability_for_form(parts[3], ability, base):
            ability, base = None, None
            base_writer = _REPLACEMENT_BASE_WRITERS.get(_id(parts[3].split(",")[0]))
        elif command in ("-ability", "ability"):
            ability = _id(parts[3])
            if not base and base_writer == ability and not any(tag.startswith("[from]") for tag in parts[4:]): base = ability
    return dict(ability=ability, base_ability=base, ability_state="known" if ability else "unknown")


def validate_public_ability(observation, predecessor=None):
    view = observation.get("view", {})
    request = observation.get("request")
    owners = request.get("side", []) if isinstance(request, dict) else []
    prior_owners = (predecessor.get("request") or {}).get("side", []) if terminal_owner(predecessor, observation) else []
    perspective = observation.get("perspective")
    for target, fact in public_revealed_abilities(observation["protocol_prefix"]).items():
        if perspective not in ("p1", "p2"):
            raise ValueError("Public ability evidence mismatch: reveal requires a perspective")
        if not target.startswith(perspective + ": "):
            opponents = view.get("opponent_team", [])
            if isinstance(opponents, list) and any(isinstance(row, dict) and _ident(row.get("ident", "")) == target
                    and any(key in row for key in ("ability", "base_ability", "ability_state", "ability_suppressed")) for row in opponents):
                raise ValueError("Public ability evidence mismatch: opponent ability fields are excluded from the public schema")
            continue
        roster = view.get("self_team")
        rows = [row for row in roster if isinstance(row, dict) and isinstance(row.get("ident"), str)
                and _ident(row["ident"]) == target] if isinstance(roster, list) else []
        if len(rows) != 1:
            raise ValueError("Public ability evidence mismatch: reveal requires exactly one correctly sided recipient")
        row = rows[0]
        owner = next((entry for entry in owners if entry.get("ident") == target), None)
        prior_owner = next((entry for entry in prior_owners if entry.get("ident") == target), None)
        ability = ((owner or {}).get("ability") or ((prior_owner or {}).get("base_ability")
                   if fact["cleared"] and prior_owner else fact["ability"])) or None
        if not fact["cleared"] and fact["ability"] and (owner or {}).get("ability") and owner["ability"] != fact["ability"]:
            raise ValueError("Public ability evidence mismatch: public reveal contradicts addressed ability")
        terminal_fact = owned_ability_after_suffix(prior_owner, observation["protocol_prefix"][len(predecessor["protocol_prefix"]):]) if prior_owner and (prior_owner.get("ability") or prior_owner.get("base_ability")) else None
        if terminal_fact is not None: ability = terminal_fact["ability"]
        states = {terminal_fact["ability_state"]} if terminal_fact is not None else {"known"} if owner and owner.get("ability") else {"known", fact["state"]} if ability else {fact["state"]}
        if ability: states.add("suppressed")
        if row.get("ability") != ability or "ability" not in row or row.get("ability_state") not in states:
            raise ValueError("Public ability evidence mismatch: reveal name/state disagrees with ordered public copy or cleanup")
        if fact["invalidated"]:
            base = terminal_fact["base_ability"] if terminal_fact is not None else (owner or {}).get("base_ability") or fact["base"] or None
            if "base_ability" not in row or row["base_ability"] != base or not ability and row.get("ability_suppressed") is not False:
                raise ValueError("Public ability evidence mismatch: invalidated current/base requires eligible authority")
    if any(any(key in row for key in ("ability", "base_ability", "ability_state", "ability_suppressed"))
           for row in view.get("opponent_team", [])):
        raise ValueError("Public ability evidence mismatch: opponent ability fields are excluded from the public schema")
    gas_present = bool(public_gas_sources(observation["protocol_prefix"]))
    local = _local_suppression(observation["protocol_prefix"])
    for row in view.get("self_team", []):
        target = _ident(row["ident"])
        owner = next((entry for entry in owners if entry.get("ident") == target), None)
        prior_owner = next((entry for entry in prior_owners if entry.get("ident") == target), None)
        if prior_owner and (prior_owner.get("ability") or prior_owner.get("base_ability")):
            fact = owned_ability_after_suffix(prior_owner, observation["protocol_prefix"][len(predecessor["protocol_prefix"]):])
            if (any(key not in row or row[key] != value for key, value in fact.items() if key != "ability_state")
                    or row.get("ability_state") not in (fact["ability_state"], "suppressed")
                    or "ability_suppressed" not in row or fact["ability"] is None and row["ability_suppressed"] is not False):
                raise ValueError("Public ability evidence mismatch: terminal current/base/state disagrees with validated owner and ordered suffix")
        if owner is not None and (owner.get("base_ability") and row.get("base_ability") != owner["base_ability"]
                or owner.get("ability") and row.get("ability_state") not in ("known", "suppressed")):
            raise ValueError("Public ability evidence mismatch: owned base/state disagrees with addressed request")
        ability = owner.get("ability") if owner is not None and owner.get("ability") else row.get("ability")
        if owner is not None and owner.get("ability") and row.get("item") != (owner.get("item") or None):
            raise ValueError("Public ability evidence mismatch: owned item exemption disagrees with addressed request")
        if owner is not None and owner.get("ability") and row.get("ability") != ability:
            raise ValueError("Public ability evidence mismatch: owned ability name disagrees with addressed request")
        if not ability:
            continue
        if "ability_suppressed" not in row:
            raise ValueError("Public ability evidence mismatch: known owned ability requires suppression field")
        ability_id = _id(ability)
        if not row.get("active") or row.get("fainted") or row.get("transformed") and ability_id in _NOTRANSFORM:
            effectiveness = "suppressed"
        elif ability_id in _CANTSUPPRESS:
            effectiveness = "active"
        elif target in local:
            effectiveness = "suppressed"
        elif not gas_present or ability_id == "neutralizinggas":
            effectiveness = "active"
        else:
            item = owner.get("item") if owner is not None else row.get("item")
            effectiveness = "active" if _id(item) == "abilityshield" else "suppressed"
        suppressed = bool(row.get("active") and effectiveness == "suppressed")
        if (row["ability_suppressed"] != suppressed
                or suppressed and row.get("ability_state") != "suppressed"
                or not suppressed and row.get("ability_state") == "suppressed"):
            raise ValueError("Public ability evidence mismatch: owned suppression disagrees with public Gas/local evidence and owned exemptions")
