"""Versioned, request-bound CanonicalAction v1 parity codec.

This module is shadow-only. It mirrors the current TypeScript LegalAction
mapping and does not submit choices to the simulator.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping, Optional


CANONICAL_ACTION_SCHEMA_VERSION = "canonical-action/v1"
_KINDS = {"move", "move_tera", "switch", "default"}
_CANONICAL_ACTION_KEYS = {
    "schema_version", "action_id", "source", "player", "rqid", "kind", "index",
    "move_slot", "switch_slot", "target", "choice",
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _fields(action: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": action.get("schema_version"),
        "source": action.get("source"),
        "player": action.get("player"),
        "rqid": action.get("rqid"),
        "kind": action.get("kind"),
        "index": action.get("index"),
        "move_slot": action.get("move_slot"),
        "switch_slot": action.get("switch_slot"),
        "target": action.get("target"),
        "choice": action.get("choice"),
    }


def _action_id(action: Mapping[str, Any]) -> str:
    return "act-" + hashlib.sha256(_json(_fields(action)).encode("utf-8")).hexdigest()


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_canonical_action(
    action: Mapping[str, Any],
    request: Mapping[str, Any],
    perspective: Optional[str] = None,
) -> None:
    perspective = request.get("player") if perspective is None else perspective
    if set(action) != _CANONICAL_ACTION_KEYS:
        raise ValueError("canonical action fields are not exact")
    if action.get("schema_version") != CANONICAL_ACTION_SCHEMA_VERSION:
        raise ValueError("unsupported canonical action schema")
    if action.get("source") != "request_legal_action":
        raise ValueError("unsupported canonical action source")
    if action.get("player") not in {"p1", "p2"} or action.get("player") != perspective or action.get("player") != request.get("player"):
        raise ValueError("canonical action player does not match perspective/request")
    if action.get("rqid") != request.get("rqid") or (action.get("rqid") is not None and not _is_int(action.get("rqid"))):
        raise ValueError("canonical action request ID does not match current request")
    index = action.get("index")
    if not _is_int(index) or not 0 <= index < 13:
        raise ValueError("canonical action index is invalid")
    if action.get("target") is not None:
        raise ValueError("canonical target semantics are unsupported in v1")
    legal = (request.get("legal_actions") or {}).get(str(index))
    if legal is None:
        legal = (request.get("legal_actions") or {}).get(index)
    if legal is None:
        raise ValueError("canonical action is not legal for current request")
    kind = action.get("kind")
    if request.get("force_switch") and kind != "switch" and not (kind == "default" and legal.get("choice") == "default"):
        raise ValueError("forced-switch requests accept switch actions or the legacy default fallback")
    if kind not in _KINDS:
        raise ValueError("unsupported canonical action kind")
    if kind == "default":
        if index != 0 or action.get("move_slot") is not None or action.get("switch_slot") is not None or action.get("choice") != "default":
            raise ValueError("canonical default fields are inconsistent")
    elif kind in {"move", "move_tera"}:
        slot = action.get("move_slot")
        expected = None if not _is_int(slot) else (slot - 1 if kind == "move" else slot + 3)
        if not _is_int(slot) or not 1 <= slot <= 4 or action.get("switch_slot") is not None or index != expected:
            raise ValueError("canonical move fields are inconsistent")
        if action.get("choice") != (f"move {slot}" if kind == "move" else f"move {slot} terastallize"):
            raise ValueError("canonical move choice is inconsistent")
    else:
        slot = action.get("switch_slot")
        if not _is_int(slot) or not 1 <= slot <= 6 or action.get("move_slot") is not None or action.get("choice") != f"switch {slot}":
            raise ValueError("canonical switch fields are inconsistent")
        if not 8 <= index <= 12:
            raise ValueError("canonical switch index is invalid")
    expected_kind = "move" if kind == "default" else kind
    if legal.get("kind") != expected_kind or legal.get("choice") != action.get("choice"):
        raise ValueError("canonical action does not match current legal action")
    if kind != "default" and legal.get("slot") != (action.get("move_slot") if kind in {"move", "move_tera"} else action.get("switch_slot")):
        raise ValueError("canonical action slot does not match current legal action")


def canonical_action_from_legal_action(
    legal_action: Mapping[str, Any],
    request: Mapping[str, Any],
    perspective: Optional[str] = None,
) -> Dict[str, Any]:
    action = {
        "schema_version": CANONICAL_ACTION_SCHEMA_VERSION,
        "action_id": None,
        "source": "request_legal_action",
        "player": request.get("player"),
        "rqid": request.get("rqid"),
        "kind": "default" if legal_action.get("choice") == "default" else legal_action.get("kind"),
        "index": legal_action.get("index"),
        "move_slot": legal_action.get("slot") if legal_action.get("kind") in {"move", "move_tera"} else None,
        "switch_slot": legal_action.get("slot") if legal_action.get("kind") == "switch" else None,
        "target": None,
        "choice": legal_action.get("choice"),
    }
    action["action_id"] = _action_id(action)
    validate_canonical_action(action, request, perspective)
    return action


def serialize_canonical_action(action: Mapping[str, Any], request: Mapping[str, Any], perspective: Optional[str] = None) -> str:
    validate_canonical_action(action, request, perspective)
    if action.get("action_id") != _action_id(action):
        raise ValueError("canonical action ID is invalid")
    ordered = {
        "schema_version": action["schema_version"],
        "action_id": action["action_id"],
        "source": action["source"],
        **{key: value for key, value in _fields(action).items() if key not in {"schema_version", "source"}},
    }
    return _json(ordered)


def deserialize_canonical_action(serialized: str, request: Mapping[str, Any], perspective: Optional[str] = None) -> Dict[str, Any]:
    try:
        action = json.loads(serialized)
    except json.JSONDecodeError as exc:
        raise ValueError("canonical action serialization is not valid JSON") from exc
    if not isinstance(action, dict):
        raise ValueError("canonical action must be a JSON object")
    if serialize_canonical_action(action, request, perspective) != serialized:
        raise ValueError("canonical action serialization is not deterministic")
    return action
