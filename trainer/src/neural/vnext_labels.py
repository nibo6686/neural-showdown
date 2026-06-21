import re
from typing import Any, Dict, Optional, Sequence


LABEL_VERSION = "vnext-diagnostic-labels-v1"
STATE_VALUE_TARGET = "terminal_outcome_from_state_owner"
ACTION_RANK_TARGET = "replay_chosen_action_one_hot"
ACTION_VALUE_STATUS = "not_generated"


def state_value_label(winner_side: Optional[str], perspective_side: str) -> Optional[float]:
    if perspective_side not in ("p1", "p2"):
        raise ValueError(f"Unsupported perspective side: {perspective_side!r}")
    if winner_side == perspective_side:
        return 1.0
    if winner_side in ("p1", "p2"):
        return -1.0
    # Ties and unknown/incomplete outcomes are excluded from v1.
    return None


def _species_from_text(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value)
    if ": " in text:
        text = text.split(": ", 1)[1]
    return text.split(",", 1)[0].strip() or None


def chosen_action_label(
    event: Dict[str, Any],
    *,
    turn_events: Sequence[Dict[str, Any]] = (),
) -> Optional[str]:
    event_type = str(event.get("type") or "")
    side = event.get("side")
    if event_type == "move" and event.get("move"):
        tera_used_now = any(
            isinstance(candidate, dict)
            and candidate.get("type") == "tera"
            and candidate.get("side") == side
            for candidate in turn_events
        )
        prefix = "move_tera" if tera_used_now else "move"
        return f"{prefix}: {event['move']}"
    if event_type == "switch":
        species = _species_from_text(event.get("details") or event.get("actor"))
        return f"switch: {species}" if species else None
    return None


def _normalized_action_parts(value: Any) -> tuple:
    text = " ".join(str(value or "").split()).lower()
    if ":" not in text:
        return text, ""
    kind, name = text.split(":", 1)
    normalized_name = re.sub(r"[^a-z0-9]+", "", name)
    return kind.strip(), normalized_name


def _roster_alias_id(value: Any) -> str:
    species_id = re.sub(r"[^a-z0-9]+", "", str(value or "").lower())
    if species_id in {"terapagosterastal", "terapagosstellar"}:
        return "terapagos"
    if species_id == "palafinhero":
        return "palafin"
    if species_id.startswith("ogerpon") and species_id.endswith("tera"):
        return species_id[: -len("tera")]
    if species_id in {"polteageistantique", "sinisteaantique"}:
        return species_id.replace("antique", "")
    if species_id in {"eiscuenoice", "mimikyubusted", "miniorcore", "zygardecomplete"}:
        return {
            "eiscuenoice": "eiscue",
            "mimikyubusted": "mimikyu",
            "miniorcore": "minior",
            "zygardecomplete": "zygarde",
        }[species_id]
    return species_id


def match_chosen_action(actions: Sequence[Dict[str, Any]], chosen_label: str) -> Optional[int]:
    target_kind, target_name = _normalized_action_parts(chosen_label)
    target_alias = _roster_alias_id(target_name) if target_kind == "switch" else target_name
    for index, action in enumerate(actions):
        kind = str(action.get("kind") or "").lower()
        label_kind, label_name = _normalized_action_parts(action.get("label"))
        action_name = re.sub(
            r"[^a-z0-9]+",
            "",
            str(action.get("move") or action.get("species") or label_name).lower(),
        )
        effective_kind = kind or label_kind
        comparable_name = _roster_alias_id(action_name) if target_kind == "switch" else action_name
        if effective_kind == target_kind and comparable_name == target_alias:
            return index
    return None
