"""PIPELINE-001 linked-record and episode-evidence validators plus JSON bridge.

This module validates perspective-specific integration records and the additive
two-perspective episode evidence envelope. It does not select features or labels
and never accepts simulator state or a raw transition log. The CLI preserves
single-bundle DATA-001 mode, validates evidence-only envelopes without emitting
rows, and validates full results or compact sweeps before emitting actor-only
DATA-001 rows.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from typing import Any, Dict, Mapping, Optional, Sequence

from neural.canonical_action import validate_canonical_action
from neural.public_boosts import validate_public_boosts
from neural.protocol_contract import ProtocolRecordError, validate_protocol_record
from neural.ts_identity import canonical, digest as ts_digest, verify_belief, verify_bundle_identities, verify_observation
from neural.typed_state import validate_public_typed_state
from neural.dataset_lineage import (
    DATASET_RECORD_SCHEMA,
    DatasetLineageError,
    DEFAULT_SPLIT_SEED,
    deterministic_split_for_battle,
    feature_schema_fingerprint,
    make_record,
    prefix_hash,
    validate_record_prefix,
    validate_record,
)


PIPELINE_BUNDLE_SCHEMA = "pipeline-linked-record/v1"
PIPELINE_TRANSITION_SCHEMA = "pipeline-transition-reference/v1"
REVIVAL_BUNDLE_SCHEMA = "pipeline-revival-record/v1"
REVIVAL_TRANSITION_SCHEMA = "pipeline-revival-reference/v1"
EPISODE_EVIDENCE_SCHEMA = "pipeline-episode-evidence/v2"
LEGACY_EPISODE_EVIDENCE_SCHEMA = "pipeline-episode-evidence/v1"
EPISODE_PUBLICATION_SWEEP_SCHEMA = "pipeline-episode-publication-sweep/v1"
EPISODE_ORIGIN_SCHEMA = "pipeline-episode-origin/v1"
EPISODE_CLOSURE_SCHEMA = "pipeline-episode-closure/v1"
FORCED_SWITCH_BUNDLE_SCHEMA = "pipeline-forced-switch-record/v1"
FORCED_SWITCH_TRANSITION_SCHEMA = "pipeline-forced-switch-reference/v1"
EPISODE_TRANSITION_SCHEMAS = {
    PIPELINE_TRANSITION_SCHEMA, FORCED_SWITCH_TRANSITION_SCHEMA, REVIVAL_TRANSITION_SCHEMA,
}
SIMULATOR_REVISION = "sim-core@0.1.0+pokemon-showdown@0.11.10"
_ID_RE = {
    "observation": re.compile(r"^obs-[0-9a-f]{64}$"),
    "belief": re.compile(r"^belief-[0-9a-f]{64}$"),
    "action": re.compile(r"^act-[0-9a-f]{64}$"),
    "transition": re.compile(r"^transition-[0-9a-f]{64}$"),
}
_BUNDLE_KEYS = {
    "schema_version", "battle_id", "source_ref", "ruleset", "perspective",
    "input_observation", "input_belief", "action", "transition",
    "successor_observation", "successor_belief",
}
_TRANSITION_KEYS = {
    "schema_version", "transition_id", "parent_branch_id", "branch_id",
    "input_state_fingerprint", "output_state_fingerprint", "simulator_revision",
    "step_index", "action_id",
}
_EPISODE_KEYS_V1 = {
    "schema_version", "run_id", "battle_id", "ruleset", "source_ref", "origin", "commits", "evidence_id",
}
_EPISODE_KEYS_V2 = _EPISODE_KEYS_V1 | {"closure"}
_EPISODE_BOUNDARY_KEYS = {"step_index", "kind", "branch_id", "state_fingerprint", "perspectives"}
_EPISODE_OBSERVATION_KEYS = {
    "schema_version", "source_kind", "battle_id", "perspective", "event_cursor", "observation_id",
    "protocol_prefix_hash", "snapshot_phase", "other_phase", "request", "decision_availability",
    "protocol_prefix", "view",
}
_EPISODE_VIEW_KEYS = {
    "format", "gen", "turn", "player", "opponent", "terminated", "winner", "names", "team_size",
    "active", "field", "self_team", "opponent_team",
}
_EPISODE_TRANSITION_KEYS = {
    "schema_version", "transition_id", "parent_branch_id", "branch_id", "input_state_fingerprint",
    "output_state_fingerprint", "simulator_revision", "step_index",
}
_BELIEF_STATE_KEYS = {
    "schema_version", "belief_id", "information_regime", "battle_id", "perspective", "observation",
    "observation_history", "source_protocol_prefix", "parent_belief_id", "simulator_snapshot",
    "simulator_snapshot_history", "transition_lineage", "transition_history", "candidates", "evidence",
    "unresolved", "contradictions",
}
_BELIEF_ARRAY_KEYS = {
    "observation_history", "simulator_snapshot_history", "transition_history", "candidates",
    "evidence", "unresolved", "contradictions",
}
_EPISODE_RESULT_METADATA_KEYS = {
    "schema_version", "run_id", "battle_id", "ruleset", "policy_id", "limits", "status", "stop",
    "counts", "initial_boundary", "final_boundary", "transition_ids", "faithful_complete_episode",
}
_FORBIDDEN_KEYS = frozenset({
    "simulator_state", "rng_seed", "root_seed", "emitted_log_delta", "raw_log_delta",
    "raw_request", "private_team", "opponent_private", "future_events", "omniscient",
})
_EPISODE_FORBIDDEN_KEYS = _FORBIDDEN_KEYS | frozenset({
    "simulator_snapshot", "simulator_state", "seed", "rng_seed", "root_seed", "opponent_request",
    "private_team", "opponent_private", "hidden_roster", "hidden_set", "omniscient",
})
class PipelineRecordError(ValueError):
    """Raised when a pipeline record's cross-object joins cannot be proven."""

    def __init__(self, message: str, diagnostic: Optional[Mapping[str, Any]] = None):
        super().__init__(message)
        self.diagnostic = dict(diagnostic) if diagnostic is not None else None


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PipelineRecordError(f"{label} must be an object")
    return value


def _reject_private_payload(value: Any, label: str) -> None:
    if isinstance(value, Mapping):
        forbidden = sorted(_FORBIDDEN_KEYS.intersection(value))
        if forbidden:
            raise PipelineRecordError(f"{label} contains private or raw simulator data: {','.join(forbidden)}")
        for key, child in value.items():
            _reject_private_payload(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_private_payload(child, f"{label}[{index}]")


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        unexpected = sorted(set(value) - expected)
        missing = sorted(expected - set(value))
        if unexpected and any(key in unexpected for key in ("simulator_state", "emitted_log_delta", "root_seed")):
            raise PipelineRecordError(f"{label} contains private or raw simulator data")
        raise PipelineRecordError(f"{label} fields are not exact; missing={missing}, unexpected={unexpected}")


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PipelineRecordError(f"{label} must be a non-empty string")
    return value


def _identifier(value: Any, kind: str, label: str) -> str:
    if not isinstance(value, str) or not _ID_RE[kind].fullmatch(value):
        raise PipelineRecordError(f"{label} is malformed")
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise PipelineRecordError(f"{label} is malformed")
    return value


def _safe_request_rqid(value: Any) -> bool:
    if type(value) is int:
        return abs(value) <= 9007199254740991
    return (type(value) is float and math.isfinite(value)
            and value.is_integer() and abs(value) <= 9007199254740991)


def _prefix(observation: Mapping[str, Any], label: str) -> Sequence[str]:
    prefix = observation.get("protocol_prefix")
    if not isinstance(prefix, list) or any(not isinstance(line, str) or not line or line.strip() != line for line in prefix):
        raise PipelineRecordError(f"{label} protocol prefix is malformed")
    if isinstance(observation.get("event_cursor"), bool) or observation.get("event_cursor") != len(prefix):
        raise PipelineRecordError(f"{label} event cursor does not match its protocol prefix")
    retained_rqid = None
    has_retained_rqid = False
    for record_index, line in enumerate(prefix):
        try:
            validate_protocol_record(line)
        except ProtocolRecordError as exc:
            if exc.kind == "unresolved_alias":
                detail = f'{label} protocol prefix has unresolved alias "{exc.command}" at record {record_index}'
                raise PipelineRecordError(
                    detail,
                    {
                        "schema_version": "pipeline-diagnostic/v1",
                        "code": "pipeline/v1/unresolved-protocol-alias",
                        "detail": detail,
                        "record_index": record_index,
                        "record_command": exc.command,
                    },
                ) from exc
            raise PipelineRecordError(f"{label} {exc}") from exc
        command = line.split("|", 2)[1]
        if command in {"error", "split"}:
            raise PipelineRecordError(f"{label} protocol prefix contains private {command} evidence")
        if line.startswith("|request|"):
            request_text = line[len("|request|"):]
            try:
                request_payload = json.loads(request_text)
            except json.JSONDecodeError as exc:
                raise PipelineRecordError(f"{label} protocol prefix contains a raw request") from exc
            if not isinstance(request_payload, dict) or set(request_payload) - {"rqid"}:
                raise PipelineRecordError(f"{label} protocol prefix contains a private request")
            try:
                canonical_request = canonical(request_payload)
            except (TypeError, ValueError) as exc:
                raise PipelineRecordError(f"{label} protocol prefix contains a noncanonical request") from exc
            if canonical_request != request_text:
                raise PipelineRecordError(f"{label} protocol prefix contains a noncanonical request")
            if "rqid" in request_payload:
                retained_rqid = request_payload["rqid"]
                has_retained_rqid = True
        if line.startswith("|tier|"):
            raise PipelineRecordError(f"{label} protocol prefix contains filtered ruleset metadata")
        if line == "|":
            raise PipelineRecordError(f"{label} protocol prefix contains filtered framing metadata")
    associated_request = observation.get("request")
    if associated_request is not None and not isinstance(associated_request, Mapping):
        raise PipelineRecordError(f"{label} request must be an object or null")
    if has_retained_rqid:
        if not isinstance(associated_request, Mapping):
            raise PipelineRecordError(f"{label} protocol request rqid has no associated request object")
        associated_rqid = associated_request.get("rqid")
        if (not _safe_request_rqid(retained_rqid) or not _safe_request_rqid(associated_rqid)
                or retained_rqid != associated_rqid):
            raise PipelineRecordError(f"{label} protocol request rqid disagrees with its associated request")
    # ObservableState hashes strings with JavaScript's literal-Unicode JSON.
    # DATA-001 separately uses ensure_ascii=True; these are distinct hashes.
    ts_hash = hashlib.sha256(
        json.dumps(list(prefix), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if observation.get("protocol_prefix_hash") != ts_hash:
        raise PipelineRecordError(f"{label} observable prefix hash is invalid")
    return prefix


def _request_for_action(observation: Mapping[str, Any], perspective: str) -> Mapping[str, Any]:
    request = observation.get("request")
    if not isinstance(request, Mapping) or request.get("player") != perspective or request.get("wait") is True:
        raise PipelineRecordError("input observation does not contain the acting player's actionable request")
    legal_set = request.get("legal_actions")
    if not isinstance(legal_set, Mapping):
        raise PipelineRecordError("input request legal actions are malformed")
    actions = legal_set.get("actions")
    mask = legal_set.get("mask")
    if not isinstance(actions, list) or not isinstance(mask, list) or len(actions) != 13 or len(mask) != 13:
        raise PipelineRecordError("input request legal action arrays are malformed")
    legal: Dict[str, Any] = {}
    for index, enabled in enumerate(mask):
        if enabled is True and isinstance(actions[index], Mapping):
            legal[str(index)] = actions[index]
        elif enabled is not False or actions[index] is not None:
            raise PipelineRecordError("input request legal action mask is inconsistent")
    return {
        "player": perspective,
        "rqid": request.get("rqid"),
        "force_switch": request.get("force_switch"),
        "legal_actions": legal,
        "side": request.get("side"),
    }


def _reject_episode_private_payload(value: Any, label: str) -> None:
    if isinstance(value, Mapping):
        forbidden = sorted(_EPISODE_FORBIDDEN_KEYS.intersection(value))
        if forbidden:
            raise PipelineRecordError(f"{label} contains private episode data: {','.join(forbidden)}")
        for key, child in value.items():
            _reject_episode_private_payload(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_episode_private_payload(child, f"{label}[{index}]")


def _episode_request_state(observation: Mapping[str, Any]) -> str:
    view = observation["view"]
    request = observation.get("request")
    if view.get("terminated") is True:
        return "terminal"
    if request is None:
        return "requestless"
    if request.get("wait") is True:
        return "waiting"
    if any(isinstance(pokemon, Mapping) and pokemon.get("reviving") is True for pokemon in request.get("side", [])):
        return "revival_selection"
    legal = request.get("legal_actions", {})
    if observation["decision_availability"].get("available") is not True or not legal.get("available_indices"):
        return "no_legal_actions"
    return "forced_switch" if request.get("force_switch") is True else "actionable"


def _episode_boundary_kind(perspectives: Mapping[str, Mapping[str, Any]]) -> str:
    states = {player: _episode_request_state(perspectives[player]) for player in ("p1", "p2")}
    if all(state == "terminal" for state in states.values()):
        return "terminal"
    if "terminal" in states.values():
        raise PipelineRecordError("episode boundary has only one terminal perspective")
    if "no_legal_actions" in states.values():
        raise PipelineRecordError("episode boundary has a nonwaiting request without legal actions")
    if "revival_selection" in states.values():
        return "one_sided_revival"
    p1 = states["p1"] in {"actionable", "forced_switch"}
    p2 = states["p2"] in {"actionable", "forced_switch"}
    if p1 and p2:
        return "joint_actionable"
    if p1 != p2:
        actor = states["p1"] if p1 else states["p2"]
        if actor == "forced_switch":
            return "one_sided_forced_switch"
        return "waiting" if (states["p2"] if p1 else states["p1"]) == "waiting" else "one_sided_requestless"
    return "waiting" if "waiting" in states.values() else "requestless"


def _validate_episode_observation(observation: Any, player: str, battle_id: str, label: str, predecessor=None) -> Mapping[str, Any]:
    observation = _object(observation, label)
    _exact_keys(observation, _EPISODE_OBSERVATION_KEYS, label)
    if (observation.get("schema_version") != "observable-battle-state/v2"
            or observation.get("source_kind") != "sim_core"
            or observation.get("battle_id") != battle_id
            or observation.get("perspective") != player):
        raise PipelineRecordError(f"{label} must be the simulator's v2 {player} observation")
    try:
        verify_observation(observation, label)
    except (KeyError, TypeError, ValueError) as exc:
        raise PipelineRecordError(f"{label} identity is invalid: {exc}") from exc
    if (not isinstance(observation.get("event_cursor"), int) or isinstance(observation.get("event_cursor"), bool)
            or observation["event_cursor"] != len(observation.get("protocol_prefix", []))):
        raise PipelineRecordError(f"{label} cursor does not equal its public prefix length")
    _prefix(observation, label)
    try:
        validate_public_typed_state(observation, label, predecessor)
    except ValueError as exc:
        raise PipelineRecordError(str(exc)) from exc
    view = _object(observation.get("view"), f"{label} view")
    _exact_keys(view, _EPISODE_VIEW_KEYS, f"{label} view")
    if (view.get("player") != player or view.get("opponent") != ("p2" if player == "p1" else "p1")
            or view.get("terminated") not in (True, False) or not isinstance(view.get("format"), str)):
        raise PipelineRecordError(f"{label} view perspective is invalid")
    for key in ("self_team", "opponent_team"):
        if not isinstance(view.get(key), list):
            raise PipelineRecordError(f"{label} {key} must be an array")
        for pokemon in view[key]:
            pokemon = _object(pokemon, f"{label} {key} member")
            base = {
                "slot", "ident", "name", "species", "base_species", "current_species", "displayed_species",
                "species_source", "transformed", "displayed_species_uncertain", "illusion_revealed", "details",
                "active", "fainted", "hp_text", "hp_ratio", "status", "status_source", "status_started_turn",
                "status_turns_public", "gender", "level", "types", "terastallized", "volatiles",
            }
            self_only = {
                "item", "last_item", "item_state", "item_suppressed", "ability", "base_ability",
                "ability_state", "ability_suppressed", "moves", "revealed_moves", "tera_type", "stats", "boosts",
            }
            if key == "self_team":
                if set(pokemon) != base | self_only:
                    raise PipelineRecordError(f"{label} self roster fields are incomplete or unexpected")
            else:
                allowed = base | {"item", "public_boosts"}
                if not base <= set(pokemon) or set(pokemon) - allowed:
                    raise PipelineRecordError(f"{label} opponent roster contains private or unexpected fields")
                if pokemon.get("item") not in (None, "has-item"):
                    raise PipelineRecordError(f"{label} opponent roster contains a private item")
    field = _object(view.get("field"), f"{label} field")
    _exact_keys(field, {"weather", "terrain", "pseudo_weather", "side_conditions"}, f"{label} field")
    sides = _object(field.get("side_conditions"), f"{label} side conditions")
    _exact_keys(sides, {"self", "opponent"}, f"{label} side conditions")
    names = _object(view.get("names"), f"{label} names")
    sizes = _object(view.get("team_size"), f"{label} team sizes")
    _exact_keys(names, {"p1", "p2"}, f"{label} names")
    _exact_keys(sizes, {"p1", "p2"}, f"{label} team sizes")
    availability = _object(observation.get("decision_availability"), f"{label} availability")
    _exact_keys(availability, {"available", "reason", "legal_action_indices"}, f"{label} availability")
    request = observation.get("request")
    if request is not None:
        request = _object(request, f"{label} request")
        _exact_keys(request, {"player", "wait", "team_preview", "force_switch", "trapped", "rqid", "active", "side", "legal_actions"}, f"{label} request")
        if request.get("player") != player or not isinstance(request.get("side"), list):
            raise PipelineRecordError(f"{label} request is not owned by its perspective")
        legal = _object(request.get("legal_actions"), f"{label} legal actions")
        _exact_keys(legal, {"mask", "actions", "available_indices"}, f"{label} legal actions")
        if not all(isinstance(legal.get(key), list) for key in ("mask", "actions", "available_indices")):
            raise PipelineRecordError(f"{label} legal actions are malformed")
    try:
        validate_public_boosts(observation)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise PipelineRecordError(f"{label} public v2 view is invalid: {exc}") from exc
    return observation


class _ActionBoundPredecessor(dict):
    """Validation-local authority, never a serialized observation field."""
    def __init__(self, predecessor, action):
        super().__init__(predecessor)
        self.terminal_action = action


def _validate_episode_boundary(value: Any, battle_id: str, label: str, predecessor=None, actions=None) -> Mapping[str, Any]:
    boundary = _object(value, label)
    _exact_keys(boundary, _EPISODE_BOUNDARY_KEYS, label)
    if (isinstance(boundary.get("step_index"), bool) or not isinstance(boundary.get("step_index"), int)
            or boundary["step_index"] < 0 or boundary.get("kind") not in {
                "joint_actionable", "one_sided_revival", "one_sided_forced_switch", "one_sided_requestless",
                "waiting", "requestless", "terminal",
            }
            or not isinstance(boundary.get("branch_id"), str) or not boundary["branch_id"].strip()
            or not isinstance(boundary.get("state_fingerprint"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", boundary["state_fingerprint"])):
        raise PipelineRecordError(f"{label} metadata is invalid")
    perspectives = _object(boundary.get("perspectives"), f"{label} perspectives")
    _exact_keys(perspectives, {"p1", "p2"}, f"{label} perspectives")
    if predecessor:
        for player in ("p1", "p2"):
            old_request = predecessor["perspectives"][player].get("request") or {}
            request = _object(perspectives[player], f"{label} {player}").get("request") or {}
            if old_request.get("side") and request.get("wait") is True and request.get("side") == []:
                raise PipelineRecordError("Public item evidence mismatch: waiting request omits previously established owned roster authority")
    observations = {
        player: _validate_episode_observation(perspectives[player], player, battle_id, f"{label} {player}",
            _ActionBoundPredecessor(predecessor["perspectives"][player], actions[player]) if actions and player in actions
            else predecessor["perspectives"][player] if predecessor else None)
        for player in ("p1", "p2")
    }
    if observations["p1"]["protocol_prefix"] != observations["p2"]["protocol_prefix"]:
        raise PipelineRecordError(f"{label} public prefixes disagree between perspectives")
    if boundary["kind"] != _episode_boundary_kind(observations):
        raise PipelineRecordError(f"{label} kind disagrees with its perspective observations")
    return boundary


def _episode_original_initial_requests(boundary: Mapping[str, Any]) -> bool:
    return boundary.get("step_index") == 0 and boundary.get("kind") == "joint_actionable" and all(
        boundary["perspectives"][player].get("view", {}).get("terminated") is False
        and isinstance(boundary["perspectives"][player].get("request"), Mapping)
        and boundary["perspectives"][player]["request"].get("player") == player
        and boundary["perspectives"][player]["request"].get("wait") is False
        for player in ("p1", "p2")
    )


def _episode_terminal_evidence(boundary: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    if boundary.get("kind") != "terminal":
        return None
    p1 = boundary["perspectives"]["p1"]
    p2 = boundary["perspectives"]["p2"]
    view1, view2 = p1["view"], p2["view"]
    winner = view1.get("winner")
    if (view1.get("terminated") is not True or view2.get("terminated") is not True
            or p1.get("request") is not None or p2.get("request") is not None
            or p1.get("snapshot_phase") != "terminal" or p2.get("snapshot_phase") != "terminal"
            or p1.get("decision_availability", {}).get("reason") != "terminal"
            or p2.get("decision_availability", {}).get("reason") != "terminal"
            or winner != view2.get("winner") or winner not in {"p1", "p2", "tie"}):
        raise PipelineRecordError("episode terminal perspectives disagree or retain a request")
    expected_record = "|tie" if winner == "tie" else f"|win|{view1.get('names', {}).get(winner) or ''}"
    if (winner == "tie" and p1["protocol_prefix"][-1:] != ["|tie"]
            or winner != "tie" and (not expected_record.endswith("|") and p1["protocol_prefix"][-1:] != [expected_record])):
        raise PipelineRecordError("episode terminal outcome has no matching final public record")
    if winner != "tie" and expected_record.endswith("|"):
        raise PipelineRecordError("episode terminal winner name is missing")
    return {
        "schema_version": "pipeline-terminal-evidence/v1",
        "outcome": "tie" if winner == "tie" else "win",
        "winner": winner,
        "final_boundary": {
            "step_index": boundary["step_index"],
            "branch_id": boundary["branch_id"],
            "state_fingerprint": boundary["state_fingerprint"],
            "perspectives": {
                player: {
                    "observation_id": boundary["perspectives"][player]["observation_id"],
                    "event_cursor": boundary["perspectives"][player]["event_cursor"],
                    "protocol_prefix_hash": boundary["perspectives"][player]["protocol_prefix_hash"],
                }
                for player in ("p1", "p2")
            },
        },
    }


def _expected_episode_actors(boundary: Mapping[str, Any]) -> list[str]:
    states = {player: _episode_request_state(boundary["perspectives"][player]) for player in ("p1", "p2")}
    if boundary["kind"] == "joint_actionable" and all(state in {"actionable", "forced_switch"} for state in states.values()):
        return ["p1", "p2"]
    if boundary["kind"] == "one_sided_forced_switch":
        actors = [player for player, state in states.items() if state == "forced_switch"]
        if len(actors) == 1 and states["p2" if actors[0] == "p1" else "p1"] == "waiting":
            return actors
    if boundary["kind"] == "one_sided_revival":
        actors = [player for player, state in states.items() if state == "revival_selection"]
        if len(actors) == 1 and states["p2" if actors[0] == "p1" else "p1"] == "waiting":
            return actors
    raise PipelineRecordError("episode commit does not begin at a supported actor boundary")


def validate_pipeline_episode_evidence(envelope: Mapping[str, Any], _depth: int = 0, *, _records=None, _compact=False) -> Dict[str, Any]:
    """Validate the two-perspective committed-boundary chain without producing DATA rows."""
    if _depth > 64:
        raise PipelineRecordError("episode predecessor chain is too deep")
    envelope = _object(envelope, "episode evidence")
    _reject_episode_private_payload(envelope, "episode evidence")
    legacy = envelope.get("schema_version") == LEGACY_EPISODE_EVIDENCE_SCHEMA
    _exact_keys(envelope, _EPISODE_KEYS_V1 if legacy else _EPISODE_KEYS_V2, "episode evidence")
    if ((not legacy and envelope.get("schema_version") != EPISODE_EVIDENCE_SCHEMA)
            or not isinstance(envelope.get("run_id"), str) or not re.fullmatch(r"episode-[0-9a-f]{64}", envelope["run_id"])
            or not isinstance(envelope.get("battle_id"), str) or not envelope["battle_id"].strip()
            or not isinstance(envelope.get("ruleset"), str) or not envelope["ruleset"].strip()
            or envelope.get("source_ref") != f"sim-core://{envelope.get('battle_id')}"
            or not isinstance(envelope.get("commits"), list)):
        raise PipelineRecordError("episode evidence metadata is invalid")
    origin = _object(envelope.get("origin"), "episode evidence origin")
    _exact_keys(origin, {"schema_version", "origin_id", "kind", "boundary"}, "episode evidence origin")
    if (origin.get("schema_version") != EPISODE_ORIGIN_SCHEMA
            or origin.get("kind") not in {"fresh_episode", "continuation_segment"}
            or not isinstance(origin.get("origin_id"), str)
            or not re.fullmatch(r"episode-origin-[0-9a-f]{64}", origin["origin_id"])):
        raise PipelineRecordError("episode evidence origin metadata is invalid")
    # Validate a continuation's committed predecessor before using any owner authority.
    validated_prior = None
    predecessor_value = (envelope.get("closure") or {}).get("predecessor") if not legacy else None
    if predecessor_value is not None:
        validated_prior = validate_pipeline_episode_evidence(_object(predecessor_value, "episode predecessor"), _depth + 1)
        if (origin.get("kind") != "continuation_segment" or predecessor_value.get("battle_id") != envelope.get("battle_id")
                or predecessor_value.get("ruleset") != envelope.get("ruleset") or predecessor_value.get("source_ref") != envelope.get("source_ref")
                or validated_prior["final_boundary"] != origin.get("boundary")):
            raise PipelineRecordError("episode predecessor does not join the current segment origin")
    origin_boundary = _validate_episode_boundary(origin.get("boundary"), envelope["battle_id"], "episode origin boundary",
        validated_prior["owner_predecessor_boundary"] if validated_prior else None)
    partial = {key: value for key, value in envelope.items() if key != "evidence_id"}
    if envelope.get("evidence_id") != f"episode-evidence-{ts_digest(partial)}":
        raise PipelineRecordError("episode evidence content identity mismatch")
    origin_identity = {
        "schema_version": EPISODE_ORIGIN_SCHEMA,
        "run_id": envelope["run_id"],
        "battle_id": envelope["battle_id"],
        "ruleset": envelope["ruleset"],
        "source_ref": envelope["source_ref"],
        "kind": origin["kind"],
        "boundary": origin_boundary,
    }
    if origin["origin_id"] != f"episode-origin-{ts_digest(origin_identity)}":
        raise PipelineRecordError("episode evidence origin commitment mismatch")

    previous = origin_boundary
    owner_predecessor_boundary = validated_prior["owner_predecessor_boundary"] if validated_prior else None
    transitions: set[str] = set()
    commit_ids: list[str] = []
    actor_by_transition: dict[str, list[str]] = {}
    record_indices = {"p1": 0, "p2": 0}
    if _records is not None:
        _records = _object(_records, "episode actor records")
        _exact_keys(_records, {"p1", "p2"}, "episode actor records")
        if any(not isinstance(_records[player], list) for player in ("p1", "p2")):
            raise PipelineRecordError("episode actor records must be arrays")
    for index, commit_value in enumerate(envelope["commits"]):
        commit = _object(commit_value, f"episode commit {index}")
        _exact_keys(commit, {"origin_id", "transition", "actors", "boundary"}, f"episode commit {index}")
        if commit.get("origin_id") != origin["origin_id"]:
            raise PipelineRecordError(f"episode commit {index} has a forged origin")
        transition = _object(commit.get("transition"), f"episode commit {index} transition")
        _exact_keys(transition, _EPISODE_TRANSITION_KEYS, f"episode commit {index} transition")
        if (transition.get("schema_version") not in EPISODE_TRANSITION_SCHEMAS
                or not isinstance(transition.get("transition_id"), str)
                or not _ID_RE["transition"].fullmatch(transition["transition_id"])
                or not isinstance(transition.get("parent_branch_id"), str)
                or not isinstance(transition.get("branch_id"), str)
                or not isinstance(transition.get("input_state_fingerprint"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", transition["input_state_fingerprint"])
                or not isinstance(transition.get("output_state_fingerprint"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", transition["output_state_fingerprint"])
                or transition.get("simulator_revision") != SIMULATOR_REVISION
                or isinstance(transition.get("step_index"), bool) or not isinstance(transition.get("step_index"), int)):
            raise PipelineRecordError(f"episode commit {index} transition is malformed")
        actors = commit.get("actors")
        expected = _expected_episode_actors(previous)
        if not isinstance(actors, list) or actors != expected:
            raise PipelineRecordError(f"episode commit {index} actors disagree with owned requests")
        expected_transition_schema = PIPELINE_TRANSITION_SCHEMA if len(expected) == 2 else (
            REVIVAL_TRANSITION_SCHEMA if previous["kind"] == "one_sided_revival" else FORCED_SWITCH_TRANSITION_SCHEMA
        )
        if transition.get("schema_version") != expected_transition_schema:
            raise PipelineRecordError(f"episode commit {index} transition schema disagrees with its request boundary")
        raw_next = _object(commit.get("boundary"), f"episode commit {index} boundary")
        if (raw_next.get("step_index") != previous["step_index"] + 1
                or transition["step_index"] != previous["step_index"]
                or transition["parent_branch_id"] != previous["branch_id"]
                or transition["branch_id"] != raw_next.get("branch_id")
                or transition["input_state_fingerprint"] != previous["state_fingerprint"]
                or transition["output_state_fingerprint"] != raw_next.get("state_fingerprint")):
            raise PipelineRecordError(f"episode commit {index} has a gap, reorder, or transition mismatch")
        actions = {}
        if _records is not None:
            for player in expected:
                cursor = record_indices[player]
                if cursor >= len(_records[player]): raise PipelineRecordError("episode actor row is missing")
                row = _object(_records[player][cursor], "episode terminal action row")
                record_indices[player] += 1
                if _compact:
                    _exact_keys(row, {"transition_id", "action", "input_belief_id", "successor_belief_id"}, "episode terminal action row")
                    if row.get("transition_id") != transition["transition_id"]:
                        raise PipelineRecordError("episode actor rows are missing, duplicated, or reordered")
                else:
                    _exact_keys(row, _BUNDLE_KEYS, "episode terminal action row")
                    reference = _object(row.get("transition"), "episode terminal action transition")
                    if (row.get("battle_id") != envelope["battle_id"] or row.get("source_ref") != envelope["source_ref"]
                            or row.get("ruleset") != envelope["ruleset"] or row.get("perspective") != player
                            or row.get("input_observation") != previous["perspectives"][player]
                            or row.get("successor_observation") != raw_next.get("perspectives", {}).get(player)
                            or any(reference.get(key) != transition[key] for key in _EPISODE_TRANSITION_KEYS)
                            or reference.get("action_id") != row.get("action", {}).get("action_id")):
                        raise PipelineRecordError("episode actor action does not join the retained transition boundaries")
                    if len(expected) == 1 and (reference.get("acting_player") != player or reference.get("waiting_player") != ("p2" if player == "p1" else "p1")):
                        raise PipelineRecordError("episode actor action has inconsistent waiting roles")
                action = _object(row.get("action"), "episode terminal owned action")
                try: validate_canonical_action(action, _request_for_action(previous["perspectives"][player], player), player)
                except (TypeError, ValueError) as exc: raise PipelineRecordError(f"canonical action validation failed: {exc}") from exc
                actions[player] = action
        owner_predecessor_boundary = previous
        next_boundary = _validate_episode_boundary(commit.get("boundary"), envelope["battle_id"], f"episode commit {index} boundary", previous, actions)
        if transition["transition_id"] in transitions:
            raise PipelineRecordError("episode contains a duplicate committed transition")
        transitions.add(transition["transition_id"])
        if (next_boundary["step_index"] != previous["step_index"] + 1
                or transition["step_index"] != previous["step_index"]
                or transition["parent_branch_id"] != previous["branch_id"]
                or transition["branch_id"] != next_boundary["branch_id"]
                or transition["input_state_fingerprint"] != previous["state_fingerprint"]
                or transition["output_state_fingerprint"] != next_boundary["state_fingerprint"]):
            raise PipelineRecordError(f"episode commit {index} has a gap, reorder, or transition mismatch")
        for player in ("p1", "p2"):
            before = previous["perspectives"][player]["protocol_prefix"]
            after = next_boundary["perspectives"][player]["protocol_prefix"]
            if len(after) < len(before) or after[:len(before)] != before:
                raise PipelineRecordError(f"episode commit {index} {player} public prefix was mutated")
        commit_ids.append(transition["transition_id"])
        actor_by_transition[transition["transition_id"]] = actors
        previous = next_boundary

    if _records is not None and any(record_indices[player] != len(_records[player]) for player in ("p1", "p2")):
        raise PipelineRecordError("episode actor rows are missing, duplicated, or reordered")

    origin_coverage = "segment_only"
    complete_capture = False
    terminal = None
    if legacy and origin["kind"] == "fresh_episode":
        origin_coverage = ("original_initial_requests" if _episode_original_initial_requests(origin_boundary)
                           else ("terminal_only" if _episode_terminal_evidence(origin_boundary) else "segment_only"))
    if not legacy:
        closure = _object(envelope.get("closure"), "episode evidence closure")
        _exact_keys(closure, {"schema_version", "origin_coverage", "predecessor", "terminal", "complete_capture"}, "episode evidence closure")
        if (closure.get("schema_version") != EPISODE_CLOSURE_SCHEMA
                or closure.get("origin_coverage") not in {"original_initial_requests", "segment_only", "terminal_only"}
                or type(closure.get("complete_capture")) is not bool):
            raise PipelineRecordError("episode evidence closure metadata is invalid")
        terminal = _episode_terminal_evidence(previous)
        supplied_terminal = closure.get("terminal")
        if terminal is None:
            if supplied_terminal is not None:
                raise PipelineRecordError("episode terminal evidence has no terminal final boundary")
        else:
            supplied_terminal = _object(supplied_terminal, "episode terminal evidence")
            _exact_keys(supplied_terminal, {"schema_version", "outcome", "winner", "final_boundary"}, "episode terminal evidence")
            if supplied_terminal != terminal:
                raise PipelineRecordError("episode terminal evidence does not join its final boundary")

        predecessor_value = closure.get("predecessor")
        if origin["kind"] == "fresh_episode":
            if predecessor_value is not None:
                raise PipelineRecordError("fresh episode cannot have a predecessor")
            origin_coverage = ("original_initial_requests" if _episode_original_initial_requests(origin_boundary)
                               else ("terminal_only" if _episode_terminal_evidence(origin_boundary) else "segment_only"))
        elif predecessor_value is None:
            origin_coverage = "segment_only"
        else:
            predecessor = _object(predecessor_value, "episode predecessor")
            prior = validated_prior if validated_prior is not None else validate_pipeline_episode_evidence(predecessor, _depth + 1)
            if (predecessor.get("battle_id") != envelope.get("battle_id")
                    or predecessor.get("ruleset") != envelope.get("ruleset")
                    or predecessor.get("source_ref") != envelope.get("source_ref")
                    or prior["final_boundary"]["kind"] == "terminal"
                    or prior["final_boundary"] != origin_boundary):
                raise PipelineRecordError("episode predecessor does not join the current segment origin")
            origin_coverage = prior["origin_coverage"]
        if closure.get("origin_coverage") != origin_coverage:
            raise PipelineRecordError("episode origin coverage does not follow its predecessor chain")
        complete_capture = origin_coverage == "original_initial_requests" and terminal is not None
        if closure.get("complete_capture") is not complete_capture:
            raise PipelineRecordError("episode complete-capture claim disagrees with origin and terminal evidence")
    return {
        "origin_boundary": origin_boundary,
        "owner_predecessor_boundary": owner_predecessor_boundary,
        "final_boundary": previous,
        "transition_ids": commit_ids,
        "actors": actor_by_transition,
        "evidence_id": envelope["evidence_id"],
        "origin_coverage": origin_coverage,
        "terminal": terminal,
        "complete_capture": complete_capture,
    }


def _validate_episode_summary(summary_value: Any, boundary: Mapping[str, Any], label: str) -> None:
    summary = _object(summary_value, label)
    _exact_keys(summary, {"step_index", "kind", "branch_id", "state_fingerprint", "perspectives"}, label)
    if any(summary.get(key) != boundary.get(key) for key in ("step_index", "kind", "branch_id", "state_fingerprint")):
        raise PipelineRecordError(f"{label} does not identify its evidence boundary")
    perspectives = _object(summary.get("perspectives"), f"{label} perspectives")
    _exact_keys(perspectives, {"p1", "p2"}, f"{label} perspectives")
    for player in ("p1", "p2"):
        actual = _object(perspectives[player], f"{label} {player}")
        observation = boundary["perspectives"][player]
        if (actual.get("observation_id") != observation.get("observation_id")
                or actual.get("event_cursor") != observation.get("event_cursor")
                or actual.get("request_state") != _episode_request_state(observation)
                or actual.get("winner") != observation["view"].get("winner")
                or not isinstance(actual.get("belief_id"), str)
                or not re.fullmatch(r"belief-[0-9a-f]{64}", actual["belief_id"])):
            raise PipelineRecordError(f"{label} {player} summary does not match its evidence observation")


def validate_pipeline_episode_result(result_value: Mapping[str, Any]) -> list[Dict[str, Any]]:
    """Validate all commits and actor records before returning any DATA-001 rows."""
    result = _object(result_value, "pipeline episode result")
    expected_keys = {
        "schema_version", "run_id", "battle_id", "ruleset", "policy_id", "limits", "status", "stop",
        "counts", "initial_boundary", "final_boundary", "transition_ids", "records", "evidence_envelope",
        "faithful_complete_episode",
    }
    _exact_keys(result, expected_keys, "pipeline episode result")
    if result.get("schema_version") != "pipeline-episode/v1" or type(result.get("faithful_complete_episode")) is not bool:
        raise PipelineRecordError("episode result schema or faithful-complete flag is invalid")
    envelope = _object(result.get("evidence_envelope"), "episode evidence envelope")
    evidence = validate_pipeline_episode_evidence(envelope, _records=result.get("records"))
    transition_ids = _validate_pipeline_episode_result_metadata(result, envelope, evidence)
    records = _object(result.get("records"), "episode actor records")
    _exact_keys(records, {"p1", "p2"}, "episode actor records")
    data_rows: list[Dict[str, Any]] = []
    rows_by_player: dict[str, list[Mapping[str, Any]]] = {"p1": [], "p2": []}
    for player in ("p1", "p2"):
        if not isinstance(records[player], list):
            raise PipelineRecordError(f"episode {player} records must be an array")
        for bundle_value in records[player]:
            bundle = _object(bundle_value, f"episode {player} actor record")
            if bundle.get("perspective") != player:
                raise PipelineRecordError("episode actor record is assigned to the wrong player")
            data_rows.append(validate_pipeline_bundle(bundle))
            rows_by_player[player].append(bundle)
    for player in ("p1", "p2"):
        actual_ids = [row["transition"]["transition_id"] for row in rows_by_player[player]]
        expected_ids = [transition_id for transition_id in transition_ids
                        if player in evidence["actors"][transition_id]]
        if actual_ids != expected_ids:
            raise PipelineRecordError(f"episode {player} actor rows are missing, duplicated, or reordered")
    for transition_id in transition_ids:
        actors = evidence["actors"][transition_id]
        for player in actors:
            row = next((item for item in rows_by_player[player] if item["transition"]["transition_id"] == transition_id), None)
            commit_index = transition_ids.index(transition_id)
            before = envelope["origin"]["boundary"] if commit_index == 0 else envelope["commits"][commit_index - 1]["boundary"]
            after = envelope["commits"][commit_index]["boundary"]
            if (row is None or row["input_observation"] != before["perspectives"][player]
                    or row["successor_observation"] != after["perspectives"][player]):
                raise PipelineRecordError("episode actor bundle does not join the retained perspective boundaries")
            source_transition = row["transition"]
            evidence_transition = envelope["commits"][commit_index]["transition"]
            if any(source_transition.get(key) != evidence_transition.get(key) for key in _EPISODE_TRANSITION_KEYS):
                raise PipelineRecordError("episode actor bundle transition disagrees with retained commit")
    expected_rows = sum(len(actors) for actors in evidence["actors"].values())
    if len(data_rows) != expected_rows:
        raise PipelineRecordError("episode emitted a decision row for a waiting player or omitted an actor row")
    return data_rows


def _validate_pipeline_episode_result_metadata(
    result: Mapping[str, Any], envelope: Mapping[str, Any], evidence: Mapping[str, Any],
) -> list[str]:
    """Validate compact and full-result metadata against the same envelope contract."""

    if result.get("schema_version") != "pipeline-episode/v1" or type(result.get("faithful_complete_episode")) is not bool:
        raise PipelineRecordError("episode result schema or faithful-complete flag is invalid")
    status = result.get("status")
    stop = _object(result.get("stop"), "episode stop")
    if (status not in {"completed", "truncated", "failed"}
            or not isinstance(stop.get("code"), str) or not isinstance(stop.get("reason"), str)):
        raise PipelineRecordError("episode status or stop record is malformed")
    stop_statuses = {
        "terminal": "completed",
        **dict.fromkeys(("transition-budget", "attempt-budget", "rejection-limit", "action-exhausted", "cancelled",
                         "unsupported-format", "unsupported-boundary", "unsupported-revival-blessing", "unsupported-protocol"), "truncated"),
        **dict.fromkeys(("invalid-options", "execution-failed", "settling-failed", "cleanup-failed", "evidence-invalid"), "failed"),
    }
    if stop_statuses.get(str(stop.get("code")).removeprefix("episode/v1/")) != status or not stop["code"].startswith("episode/v1/"):
        raise PipelineRecordError("episode stop classification disagrees with its status or is unsupported")
    limits = result.get("limits")
    limit_fields = {"max_transitions", "max_attempts", "max_rejections_per_boundary"}
    if (not isinstance(limits, Mapping) or set(limits) != limit_fields
            or any(type(limits[key]) is not int or not 1 <= limits[key] <= 9007199254740991 for key in limit_fields)):
        raise PipelineRecordError("episode limits schema requires exactly three positive JavaScript-safe integer budgets")
    revival_causes = {"seeded-revival/v1/unsupported-request", "seeded-forced-switch/v1/unsupported-revival-blessing"}
    if stop["code"] == "episode/v1/unsupported-revival-blessing" and stop.get("cause_code") not in revival_causes:
        raise PipelineRecordError("episode Revival stop requires a recognized safe cause")
    cause_index = stop.get("cause_record_index")
    if cause_index is not None and (type(cause_index) is not int or cause_index < 0):
        raise PipelineRecordError("episode stop classification has an invalid cause record index")
    if envelope.get("schema_version") == EPISODE_EVIDENCE_SCHEMA:
        is_terminal = evidence["terminal"] is not None
        if ((status == "completed") != (stop.get("code") == "episode/v1/terminal")
                or (status == "completed" and not is_terminal)
                or (status == "truncated" and is_terminal)):
            raise PipelineRecordError("episode result status disagrees with terminal evidence")
    if (result.get("run_id") != envelope.get("run_id") or result.get("battle_id") != envelope.get("battle_id")
            or result.get("ruleset") != envelope.get("ruleset")):
        raise PipelineRecordError("episode result and evidence identity disagree")
    initial = result.get("initial_boundary")
    final = result.get("final_boundary")
    if initial is None or final is None:
        raise PipelineRecordError("episode result omitted a boundary with available evidence")
    _validate_episode_summary(initial, evidence["origin_boundary"], "episode initial summary")
    _validate_episode_summary(final, evidence["final_boundary"], "episode final summary")
    run_identity = {
        "schema": "pipeline-episode/v1", "battle_id": result["battle_id"], "format": result["ruleset"],
        "policy": result["policy_id"], "limits": result["limits"], "initial_boundary": initial,
    }
    run_digest = hashlib.sha256(json.dumps(run_identity, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    if result["run_id"] != f"episode-{run_digest}":
        raise PipelineRecordError("episode run identity does not bind the supplied origin")
    transition_ids = result.get("transition_ids")
    if transition_ids != evidence["transition_ids"]:
        raise PipelineRecordError("episode result transition list disagrees with evidence commits")
    counts = _object(result.get("counts"), "episode counts")
    counter_fields = {"attempts", "committed_transitions", "rejected_candidates", "rejections_at_final_boundary"}
    if set(counts) != counter_fields or any(type(counts[key]) is not int or counts[key] < 0 for key in counter_fields):
        raise PipelineRecordError("episode counter fields must be nonnegative integers")
    if counts["committed_transitions"] != len(transition_ids):
        raise PipelineRecordError("episode committed transition count disagrees with evidence")
    accounted = counts["committed_transitions"] + counts["rejected_candidates"]
    # A nonrecoverable candidate can consume one attempt without committing or being a retryable rejection.
    if not accounted <= counts["attempts"] <= accounted + 1 or counts["rejections_at_final_boundary"] > counts["rejected_candidates"]:
        raise PipelineRecordError("episode counter accounting disagrees with committed/rejected work")
    attempted_guard_stop = stop["code"] == "episode/v1/unsupported-protocol" or (
        stop["code"] == "episode/v1/unsupported-revival-blessing" and stop.get("cause_code") in revival_causes
    )
    if (status == "completed" or (status == "truncated" and not attempted_guard_stop)) and counts["attempts"] != accounted:
        raise PipelineRecordError("episode counter contains an unaccounted attempt at a clean stop")
    if result["faithful_complete_episode"] and not (
        result["ruleset"] == "gen9randombattle" and status == "completed"
        and stop["code"] == "episode/v1/terminal" and envelope.get("schema_version") == EPISODE_EVIDENCE_SCHEMA
        and evidence["complete_capture"] is True and evidence["terminal"] is not None
    ):
        raise PipelineRecordError("episode faithful claim is not supported by complete successful v2 capture")
    if isinstance(limits, Mapping):
        bounded = (("attempts", "max_attempts"), ("committed_transitions", "max_transitions"),
                   ("rejections_at_final_boundary", "max_rejections_per_boundary"))
        if any(type(limits.get(limit)) is not int or limits[limit] <= 0 or counts[counter] > limits[limit]
               for counter, limit in bounded):
            raise PipelineRecordError("episode counter exceeds its declared execution limit")
        stopped_at = {"episode/v1/transition-budget": bounded[1], "episode/v1/attempt-budget": bounded[0],
                      "episode/v1/rejection-limit": bounded[2]}.get(stop["code"])
        if stopped_at and counts[stopped_at[0]] != limits[stopped_at[1]]:
            raise PipelineRecordError("episode counter does not establish its declared budget stop")
    return transition_ids


def _validated_episode_publication_context(envelope: Mapping[str, Any]) -> Dict[str, Any]:
    """Index prefixes and boundary identities already checked by the envelope validator."""

    observations: dict[str, Mapping[str, Any]] = {}
    observation_objects: dict[str, set[int]] = {}
    observation_references: dict[str, Dict[str, Any]] = {}
    prefixes: dict[str, Sequence[str]] = {}
    data_prefix_hashes: dict[str, str] = {}
    canonical_prefix_bytes: dict[str, bytes] = {}
    serialized_prefixes: dict[tuple[str, int], bytes] = {}

    def add_boundary(boundary: Mapping[str, Any]) -> None:
        for player in ("p1", "p2"):
            observation = boundary["perspectives"][player]
            observation_id = observation["observation_id"]
            prefix = observation["protocol_prefix"]
            existing = observations.get(observation_id)
            if existing is not None and (
                    existing["protocol_prefix_hash"] != observation["protocol_prefix_hash"]
                    or existing["event_cursor"] != observation["event_cursor"]
                    or existing["protocol_prefix"] != prefix):
                raise PipelineRecordError("episode observation identity joins different validated prefixes")
            if existing is None:
                observations[observation_id] = observation
                prefixes[observation_id] = prefix
                data_prefix_hashes[observation_id] = prefix_hash(prefix)
                prefix_key = (observation["protocol_prefix_hash"], len(prefix))
                if prefix_key not in serialized_prefixes:
                    serialized_prefixes[prefix_key] = canonical(prefix).encode("utf-8")
                canonical_prefix_bytes[observation_id] = serialized_prefixes[prefix_key]
                observation_references[observation_id] = {
                    key: observation[key] for key in (
                        "schema_version", "observation_id", "source_kind", "event_cursor",
                        "protocol_prefix_hash", "snapshot_phase",
                    )
                }
            observation_objects.setdefault(observation_id, set()).add(id(observation))

    def visit(current: Mapping[str, Any]) -> None:
        closure = current.get("closure")
        predecessor = closure.get("predecessor") if isinstance(closure, Mapping) else None
        if isinstance(predecessor, Mapping):
            visit(predecessor)
        add_boundary(current["origin"]["boundary"])
        for commit in current["commits"]:
            add_boundary(commit["boundary"])

    visit(envelope)
    return {
        "observations_by_id": observations,
        "observation_objects_by_id": observation_objects,
        "observation_references_by_id": observation_references,
        "prefixes_by_observation_id": prefixes,
        "data_prefix_hashes_by_observation_id": data_prefix_hashes,
        "canonical_prefix_bytes_by_observation_id": canonical_prefix_bytes,
        "beliefs_by_id": {},
    }


def _reject_sweep_private_payload(value: Any, label: str) -> None:
    forbidden = _FORBIDDEN_KEYS | frozenset({
        "opponent_request", "hidden_roster", "hidden_set", "seed",
    })
    if isinstance(value, Mapping):
        leaked = sorted(forbidden.intersection(value))
        if leaked:
            raise PipelineRecordError(f"{label} contains private or raw simulator data: {','.join(leaked)}")
        for key, child in value.items():
            _reject_sweep_private_payload(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sweep_private_payload(child, f"{label}[{index}]")


def _validate_record_prefix_with_digest(
    record: Mapping[str, Any], protocol_prefix: Sequence[str], validated_digest: str,
) -> None:
    """Apply DATA-001 boundary checks using a digest cached from its joined envelope observation."""

    normalized = validate_record(record)
    if len(protocol_prefix) != normalized["observation_cursor"]:
        raise DatasetLineageError("protocol prefix length does not match observation cursor")
    if validated_digest != normalized["observation_prefix_hash"]:
        raise DatasetLineageError("protocol prefix hash does not match observation boundary")


def validate_pipeline_episode_publication_sweep(sweep_value: Mapping[str, Any]) -> list[Dict[str, Any]]:
    """Validate every segment actor row against one validated envelope, then return rows atomically."""

    sweep = _object(sweep_value, "pipeline episode publication sweep")
    _reject_sweep_private_payload(sweep, "pipeline episode publication sweep")
    _exact_keys(sweep, {"schema_version", "result", "evidence_envelope", "records", "beliefs"}, "pipeline episode publication sweep")
    if sweep.get("schema_version") != EPISODE_PUBLICATION_SWEEP_SCHEMA:
        raise PipelineRecordError("unsupported episode publication sweep schema")
    result = _object(sweep.get("result"), "episode publication sweep result metadata")
    _exact_keys(result, _EPISODE_RESULT_METADATA_KEYS, "episode publication sweep result metadata")
    envelope = _object(sweep.get("evidence_envelope"), "episode publication sweep evidence")
    evidence = validate_pipeline_episode_evidence(envelope, _records=sweep.get("records"), _compact=True)
    transition_ids = _validate_pipeline_episode_result_metadata(result, envelope, evidence)
    if not evidence["complete_capture"]:
        raise PipelineRecordError("episode publication sweep requires a validated original-to-terminal chain")
    context = _validated_episode_publication_context(envelope)

    compact_beliefs = sweep.get("beliefs")
    if not isinstance(compact_beliefs, list):
        raise PipelineRecordError("episode publication sweep beliefs must be an array")
    for index, compact_value in enumerate(compact_beliefs):
        compact = _object(compact_value, f"episode publication sweep belief {index}")
        _reject_sweep_private_payload(compact, f"episode publication sweep belief {index}")
        _exact_keys(compact, {"belief_id", "base_belief_id", "fields", "arrays"}, f"episode publication sweep belief {index}")
        belief_id = _identifier(compact.get("belief_id"), "belief", f"episode publication sweep belief {index} ID")
        if belief_id in context["beliefs_by_id"]:
            raise PipelineRecordError("episode publication sweep contains a duplicate belief identity")
        fields = _object(compact.get("fields"), f"episode publication sweep belief {index} fields")
        _exact_keys(fields, _BELIEF_STATE_KEYS - _BELIEF_ARRAY_KEYS - {"belief_id", "source_protocol_prefix"}, f"episode publication sweep belief {index} fields")
        encoded_arrays = _object(compact.get("arrays"), f"episode publication sweep belief {index} arrays")
        _exact_keys(encoded_arrays, _BELIEF_ARRAY_KEYS, f"episode publication sweep belief {index} arrays")
        parent_id = compact.get("base_belief_id")
        parent = None
        if parent_id is not None:
            parent_id = _identifier(parent_id, "belief", f"episode publication sweep belief {index} base ID")
            if parent_id != fields.get("parent_belief_id"):
                raise PipelineRecordError("episode publication sweep belief delta does not match its parent identity")
            parent = context["beliefs_by_id"].get(parent_id)
            if parent is None:
                raise PipelineRecordError("episode publication sweep belief delta precedes its parent")
        belief = dict(fields)
        belief["belief_id"] = belief_id
        for field in _BELIEF_ARRAY_KEYS:
            encoded = _object(encoded_arrays[field], f"episode publication sweep belief {index} {field}")
            mode = encoded.get("mode")
            if mode == "full":
                _exact_keys(encoded, {"mode", "items"}, f"episode publication sweep belief {index} {field}")
                items = encoded.get("items")
                if not isinstance(items, list):
                    raise PipelineRecordError(f"episode publication sweep belief {index} {field} items must be an array")
                belief[field] = items
            elif mode == "append":
                _exact_keys(encoded, {"mode", "items"}, f"episode publication sweep belief {index} {field}")
                items = encoded.get("items")
                prior_items = parent.get(field) if parent is not None else None
                if not isinstance(items, list) or not isinstance(prior_items, list):
                    raise PipelineRecordError(f"episode publication sweep belief {index} {field} delta has no parent array")
                belief[field] = [*prior_items, *items]
            else:
                raise PipelineRecordError(f"episode publication sweep belief {index} {field} encoding is unsupported")
        reference = _object(belief.get("observation"), f"episode publication sweep belief {index} observation")
        observation_id = reference.get("observation_id")
        observation = context["observations_by_id"].get(observation_id)
        if observation is None:
            raise PipelineRecordError("episode publication sweep belief does not join a retained boundary")
        belief["source_protocol_prefix"] = context["prefixes_by_observation_id"][observation_id]
        _exact_keys(belief, _BELIEF_STATE_KEYS, f"episode publication sweep belief {index}")
        try:
            verify_belief(
                belief, observation, f"episode publication sweep belief {index}",
                validated_observation_references=context["observation_references_by_id"],
                canonical_source_prefix=context["canonical_prefix_bytes_by_observation_id"][observation_id],
            )
        except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
            raise PipelineRecordError(f"Invalid episode publication belief identity: {exc}") from exc
        context["beliefs_by_id"][belief_id] = belief

    records = _object(sweep.get("records"), "episode publication sweep actor records")
    _exact_keys(records, {"p1", "p2"}, "episode publication sweep actor records")
    rows_by_player: dict[str, list[Any]] = {"p1": [], "p2": []}
    expected_by_player: dict[str, list[tuple[int, Mapping[str, Any]]]] = {"p1": [], "p2": []}
    for commit_index, (transition_id, commit) in enumerate(zip(transition_ids, envelope["commits"])):
        if commit["transition"]["transition_id"] != transition_id:
            raise PipelineRecordError("episode publication transition list disagrees with its evidence commits")
        for player in commit["actors"]:
            expected_by_player[player].append((commit_index, commit))

    data_rows: list[Dict[str, Any]] = []
    used_beliefs: set[str] = set()
    for player in ("p1", "p2"):
        compact_rows = records[player]
        if not isinstance(compact_rows, list):
            raise PipelineRecordError(f"episode publication sweep {player} records must be an array")
        expected_rows = expected_by_player[player]
        if len(compact_rows) != len(expected_rows):
            raise PipelineRecordError(f"episode publication sweep {player} actor rows are missing or include a waiting player")
        rows_by_player[player] = compact_rows
        for compact_index, (row_value, (commit_index, commit)) in enumerate(zip(compact_rows, expected_rows)):
            row = _object(row_value, f"episode publication sweep {player} row {compact_index}")
            _exact_keys(row, {"transition_id", "action", "input_belief_id", "successor_belief_id"}, f"episode publication sweep {player} row {compact_index}")
            if row.get("transition_id") != commit["transition"]["transition_id"]:
                raise PipelineRecordError(f"episode publication sweep {player} rows are missing, duplicated, or reordered")
            action = _object(row.get("action"), f"episode publication sweep {player} action")
            input_belief_id = _identifier(row.get("input_belief_id"), "belief", "episode publication input belief ID")
            successor_belief_id = _identifier(row.get("successor_belief_id"), "belief", "episode publication successor belief ID")
            if input_belief_id not in context["beliefs_by_id"] or successor_belief_id not in context["beliefs_by_id"]:
                raise PipelineRecordError("episode publication sweep row references a missing belief")
            used_beliefs.update((input_belief_id, successor_belief_id))

            before = envelope["origin"]["boundary"] if commit_index == 0 else envelope["commits"][commit_index - 1]["boundary"]
            after = commit["boundary"]
            action_transition = dict(commit["transition"])
            action_transition["action_id"] = action.get("action_id")
            transition_schema = action_transition["schema_version"]
            if transition_schema in {FORCED_SWITCH_TRANSITION_SCHEMA, REVIVAL_TRANSITION_SCHEMA}:
                action_transition["acting_player"] = player
                action_transition["waiting_player"] = "p2" if player == "p1" else "p1"
            bundle_schema = (
                REVIVAL_BUNDLE_SCHEMA if transition_schema == REVIVAL_TRANSITION_SCHEMA else
                FORCED_SWITCH_BUNDLE_SCHEMA if transition_schema == FORCED_SWITCH_TRANSITION_SCHEMA else
                PIPELINE_BUNDLE_SCHEMA
            )
            bundle = {
                "schema_version": bundle_schema,
                "battle_id": envelope["battle_id"],
                "source_ref": envelope["source_ref"],
                "ruleset": envelope["ruleset"],
                "perspective": player,
                "input_observation": before["perspectives"][player],
                "input_belief": context["beliefs_by_id"][input_belief_id],
                "action": action,
                "transition": action_transition,
                "successor_observation": after["perspectives"][player],
                "successor_belief": context["beliefs_by_id"][successor_belief_id],
            }
            data_rows.append(_validate_pipeline_bundle(bundle, trusted_context=context))

    if used_beliefs != set(context["beliefs_by_id"]):
        raise PipelineRecordError("episode publication sweep contains an unused belief")
    expected_count = sum(len(actors) for actors in evidence["actors"].values())
    if len(data_rows) != expected_count:
        raise PipelineRecordError("episode publication sweep did not produce exactly one DATA-001 row per actor")
    return data_rows


def validate_pipeline_bundle(bundle: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate exact per-perspective joins and create a DATA-001 record."""
    return _validate_pipeline_bundle(bundle)


def _validate_pipeline_bundle(bundle: Mapping[str, Any], trusted_context: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Validate exact per-perspective joins and create a DATA-001 record."""

    _object(bundle, "pipeline bundle")
    _reject_private_payload(bundle, "pipeline bundle")
    _exact_keys(bundle, _BUNDLE_KEYS, "pipeline bundle")
    revival = bundle.get("schema_version") == REVIVAL_BUNDLE_SCHEMA
    forced_switch = revival or bundle.get("schema_version") == FORCED_SWITCH_BUNDLE_SCHEMA
    if bundle.get("schema_version") not in {PIPELINE_BUNDLE_SCHEMA, FORCED_SWITCH_BUNDLE_SCHEMA, REVIVAL_BUNDLE_SCHEMA}:
        raise PipelineRecordError("unsupported pipeline bundle schema")
    battle_id = _nonempty(bundle.get("battle_id"), "battle_id")
    perspective = bundle.get("perspective")
    if perspective not in {"p1", "p2"}:
        raise PipelineRecordError("unsupported perspective")
    source_ref = _nonempty(bundle.get("source_ref"), "source_ref")
    if source_ref != f"sim-core://{battle_id}":
        raise PipelineRecordError("source_ref does not identify this simulator episode")
    ruleset = _nonempty(bundle.get("ruleset"), "ruleset")

    input_observation = _object(bundle.get("input_observation"), "input observation")
    input_belief = _object(bundle.get("input_belief"), "input belief")
    action = _object(bundle.get("action"), "canonical action")
    transition = _object(bundle.get("transition"), "transition reference")
    successor_observation = _object(bundle.get("successor_observation"), "successor observation")
    successor_belief = _object(bundle.get("successor_belief"), "successor belief")
    for observation in (input_observation, successor_observation):
        if observation.get("view", {}).get("format") is not None and observation["view"]["format"] != ruleset:
            raise PipelineRecordError("ruleset disagrees with the linked observation format")
    _exact_keys(transition, _TRANSITION_KEYS | ({"acting_player", "waiting_player"} if forced_switch else set()), "transition reference")
    expected_transition_schema = REVIVAL_TRANSITION_SCHEMA if revival else (FORCED_SWITCH_TRANSITION_SCHEMA if forced_switch else PIPELINE_TRANSITION_SCHEMA)
    if transition.get("schema_version") != expected_transition_schema:
        raise PipelineRecordError("unsupported transition reference schema")
    if forced_switch:
        if (transition.get("acting_player") != perspective
                or transition.get("waiting_player") != ("p2" if perspective == "p1" else "p1")):
            raise PipelineRecordError("forced-switch record must belong only to the acting player with a distinct waiting player")
        actor_request = _object(input_observation.get("request"), "forced-switch request")
        if (ruleset != "gen9randombattle" or actor_request.get("force_switch") is not True
                or actor_request.get("wait") is not False or actor_request.get("team_preview") is not False
                or input_observation.get("snapshot_phase") != "forced_switch"
                or _object(input_observation.get("view"), "input view").get("terminated") is not False
                or action.get("kind") != ("revive" if revival else "switch")):
            raise PipelineRecordError("forced-switch bundle requires an ordinary actionable forced-switch input")

    request_side = _object(input_observation.get("request"), "input request").get("side", [])
    if not isinstance(request_side, list):
        raise PipelineRecordError("input request side must be a list")
    if revival and any(not isinstance(p, Mapping) or not isinstance(p.get("condition"), str)
                       or not isinstance(p.get("active"), bool)
                       or ("reviving" in p and p["reviving"] is not True) for p in request_side):
        raise PipelineRecordError("revival request roster is malformed")
    revivers = [p for p in request_side if isinstance(p, Mapping) and p.get("reviving") is True]
    if revival:
        targets = [p for p in request_side if isinstance(p, Mapping) and p.get("active") is False and str(p.get("condition", "")).endswith(" fnt")]
        if (len(revivers) != 1 or revivers[0].get("active") is not True
                or str(revivers[0].get("condition", "")).endswith(" fnt")
                or len(request_side) > 6 or not targets
                or sum(p.get("active") is True for p in request_side if isinstance(p, Mapping)) != 1):
            raise PipelineRecordError("unsupported revival request")
        legal = _object(input_observation["request"].get("legal_actions"), "revival legal actions")
        if (any(not isinstance(p, Mapping) or p.get("slot") != i + 1 for i, p in enumerate(request_side))
                or legal.get("available_indices") != list(range(8, 8 + len(targets)))):
            raise PipelineRecordError("revival request slots or indices are inconsistent")
        actions = legal.get("actions")
        mask = legal.get("mask")
        if (not isinstance(actions, list) or len(actions) != 13
                or not isinstance(mask, list) or len(mask) != 13
                or mask != [8 <= i < 8 + len(targets) for i in range(13)]
                or any(entry is not None for i, entry in enumerate(actions) if not mask[i])):
            raise PipelineRecordError("revival legal action mask is inconsistent")
        for offset, target in enumerate(targets):
            entry = legal.get("actions", [])[8 + offset]
            if (not isinstance(entry, Mapping) or entry.get("kind") != "revive"
                    or entry.get("slot") != target.get("slot") or entry.get("choice") != f"switch {target.get('slot')}"):
                raise PipelineRecordError("revival legal action does not match fainted target")
        index = action.get("index")
        if not isinstance(index, int) or not 0 <= index - 8 < len(targets):
            raise PipelineRecordError("revival target index is invalid")
        target = targets[index - 8]
        if target.get("slot") != request_side.index(target) + 1 or action.get("switch_slot") != target.get("slot"):
            raise PipelineRecordError("revival target must match a fainted request slot")
    elif revivers or action.get("kind") == "revive":
        raise PipelineRecordError("revival requires the versioned revival record contract")

    for label, observation in (("input observation", input_observation), ("successor observation", successor_observation)):
        if observation.get("schema_version") not in ("observable-battle-state/v1", "observable-battle-state/v2"):
            raise PipelineRecordError(f"{label} schema is unsupported")
        if observation.get("source_kind") != "sim_core" or observation.get("battle_id") != battle_id:
            raise PipelineRecordError(f"{label} source or battle identity disagrees")
        if observation.get("perspective") != perspective:
            raise PipelineRecordError(f"{label} perspective disagrees with record")
        _identifier(observation.get("observation_id"), "observation", f"{label} ID")
    if input_observation['schema_version'] != successor_observation['schema_version']:
        raise PipelineRecordError('Mixed observation schemas require independent regeneration')
    if trusted_context is None:
        input_prefix = _prefix(input_observation, "input observation")
        successor_prefix = _prefix(successor_observation, "successor observation")
    else:
        for label, observation in (("input observation", input_observation), ("successor observation", successor_observation)):
            observation_id = observation["observation_id"]
            if id(observation) not in trusted_context["observation_objects_by_id"].get(observation_id, set()):
                raise PipelineRecordError(f"{label} is not the exact validated episode boundary")
        input_prefix = trusted_context["prefixes_by_observation_id"][input_observation["observation_id"]]
        successor_prefix = trusted_context["prefixes_by_observation_id"][successor_observation["observation_id"]]
    if (trusted_context is None
            and (len(successor_prefix) < len(input_prefix) or list(successor_prefix[:len(input_prefix)]) != list(input_prefix))):
        raise PipelineRecordError("successor protocol prefix is not an exact extension")

    input_availability = _object(input_observation.get("decision_availability"), "input decision availability")
    if input_availability.get("available") is not True:
        raise PipelineRecordError("input observation is not actionable")
    if input_belief.get("schema_version") != "belief-state/v1" or input_belief.get("information_regime") != "player":
        raise PipelineRecordError("input belief must use the player information regime")
    if input_belief.get("battle_id") != battle_id or input_belief.get("perspective") != perspective:
        raise PipelineRecordError("input belief battle or perspective disagrees")
    input_belief_id = _identifier(input_belief.get("belief_id"), "belief", "input belief ID")
    input_belief_observation = _object(input_belief.get("observation"), "input belief observation reference")
    if input_belief_observation.get("observation_id") != input_observation.get("observation_id"):
        raise PipelineRecordError("input belief does not reference the input observation")
    if (input_belief.get("source_protocol_prefix") is not input_prefix
            if trusted_context is not None else input_belief.get("source_protocol_prefix") != list(input_prefix)):
        raise PipelineRecordError("input belief protocol prefix does not match input observation")
    input_snapshot = _object(input_belief.get("simulator_snapshot"), "input belief snapshot lineage")
    if input_snapshot.get("branch_id") != transition.get("parent_branch_id"):
        raise PipelineRecordError("transition parent branch does not match input belief snapshot")
    if input_snapshot.get("state_fingerprint") != transition.get("input_state_fingerprint"):
        raise PipelineRecordError("transition input fingerprint does not match input belief snapshot")

    if successor_belief.get("schema_version") != "belief-state/v1" or successor_belief.get("information_regime") != "player":
        raise PipelineRecordError("successor belief must use the player information regime")
    if successor_belief.get("battle_id") != battle_id or successor_belief.get("perspective") != perspective:
        raise PipelineRecordError("successor belief battle or perspective disagrees")
    successor_belief_id = _identifier(successor_belief.get("belief_id"), "belief", "successor belief ID")
    if successor_belief.get("parent_belief_id") != input_belief_id:
        raise PipelineRecordError("successor belief parent does not match input belief")
    successor_belief_observation = _object(successor_belief.get("observation"), "successor belief observation reference")
    if successor_belief_observation.get("observation_id") != successor_observation.get("observation_id"):
        raise PipelineRecordError("successor belief does not reference the successor observation")
    if (successor_belief.get("source_protocol_prefix") is not successor_prefix
            if trusted_context is not None else successor_belief.get("source_protocol_prefix") != list(successor_prefix)):
        raise PipelineRecordError("successor belief protocol prefix does not match successor observation")

    transition_id = _identifier(transition.get("transition_id"), "transition", "transition ID")
    action_id = _identifier(action.get("action_id"), "action", "canonical action ID")
    if transition.get("action_id") != action_id:
        raise PipelineRecordError("transition action does not match canonical action")
    if transition.get("simulator_revision") != SIMULATOR_REVISION:
        raise PipelineRecordError("simulator revision is unsupported")
    if isinstance(transition.get("step_index"), bool) or not isinstance(transition.get("step_index"), int) or transition["step_index"] < 0:
        raise PipelineRecordError("transition step index is invalid")
    for key in ("parent_branch_id", "branch_id"):
        _nonempty(transition.get(key), f"transition {key}")
    for key in ("input_state_fingerprint", "output_state_fingerprint"):
        _digest(transition.get(key), f"transition {key}")

    lineage = _object(successor_belief.get("transition_lineage"), "successor belief transition lineage")
    expected_lineage = {
        "transition_id": transition_id,
        "parent_branch_id": transition["parent_branch_id"],
        "branch_id": transition["branch_id"],
        "input_state_fingerprint": transition["input_state_fingerprint"],
        "output_state_fingerprint": transition["output_state_fingerprint"],
        "input_observation_id": input_observation["observation_id"],
        "output_observation_id": successor_observation["observation_id"],
        "simulator_revision": transition["simulator_revision"],
        "step_index": transition["step_index"],
    }
    if any(lineage.get(key) != value for key, value in expected_lineage.items()):
        raise PipelineRecordError("successor belief transition lineage does not match the transition")
    output_snapshot = _object(successor_belief.get("simulator_snapshot"), "successor belief snapshot lineage")
    if (output_snapshot.get("branch_id") != transition["branch_id"]
            or output_snapshot.get("transition_id") != transition_id
            or output_snapshot.get("parent_branch_id") != transition["parent_branch_id"]
            or output_snapshot.get("state_fingerprint") != transition["output_state_fingerprint"]):
        raise PipelineRecordError("successor belief snapshot does not match transition output")

    try:
        if trusted_context is None:
            verify_bundle_identities(bundle)
        else:
            verify_bundle_identities(
                bundle,
                validated_observations=trusted_context["observation_objects_by_id"],
                validated_beliefs=trusted_context["beliefs_by_id"],
            )
    except (ValueError, KeyError, TypeError, IndexError, OverflowError) as exc:
        raise PipelineRecordError('Invalid content identity: ' + str(exc)) from exc

    request = _request_for_action(input_observation, perspective)
    try:
        validate_canonical_action(action, request, perspective)
    except (TypeError, ValueError) as exc:
        raise PipelineRecordError(f"canonical action validation failed: {exc}") from exc

    if trusted_context is None:
        for observation in (input_observation, successor_observation):
            try:
                validate_public_typed_state(observation, predecessor=_ActionBoundPredecessor(input_observation, action) if observation is successor_observation else None)
            except ValueError as exc:
                raise PipelineRecordError(str(exc)) from exc
            if observation['schema_version'] == 'observable-battle-state/v2':
                try:
                    validate_public_boosts(observation)
                except (ValueError, KeyError, TypeError, IndexError) as exc:
                    raise PipelineRecordError('Invalid public-stage evidence: ' + str(exc)) from exc
            elif any('public_boosts' in p for p in observation.get('view', {}).get('opponent_team', [])):
                raise PipelineRecordError('Version-one observations cannot contain public_boosts')

    # Python DATA-001 and TypeScript ObservableState intentionally use
    # different canonical JSON escaping for non-ASCII prefixes. The record
    # stores DATA-001's hash; the TS observation hash is validated separately.
    record = make_record(
        battle_id=battle_id,
        replay_id=f"sim:{battle_id}",
        source_kind="sim_core",
        source_ref=source_ref,
        ruleset=ruleset,
        parser_version=SIMULATOR_REVISION,
        perspective=perspective,
        observation_cursor=len(input_prefix),
        feature_cursor=0,
        observation_prefix_hash=(
            prefix_hash(input_prefix) if trusted_context is None
            else trusted_context["data_prefix_hashes_by_observation_id"][input_observation["observation_id"]]
        ),
        observation_id=input_observation["observation_id"],
        action_id=action_id,
        belief_id=input_belief_id,
        transition_id=transition_id,
        private_data_provenance="acting_player_request",
        feature_input_eligibility="acting_player_private",
        schema_fingerprints={
            "observation": input_observation["schema_version"],
            "belief": "belief-state/v1",
            "transition": "seeded-revival/v1" if revival else ("seeded-forced-switch/v1" if forced_switch else "seeded-transition/v1"),
            "feature": feature_schema_fingerprint("features-not-produced/v1", []),
        },
        split_seed=DEFAULT_SPLIT_SEED,
        split=deterministic_split_for_battle(battle_id, DEFAULT_SPLIT_SEED),
        split_key=battle_id,
        input_fields=[],
    )
    if trusted_context is None:
        validate_record_prefix(record, input_prefix)
    else:
        _validate_record_prefix_with_digest(
            record, input_prefix,
            trusted_context["data_prefix_hashes_by_observation_id"][input_observation["observation_id"]],
        )
    if record["schema_version"] != DATASET_RECORD_SCHEMA:
        raise PipelineRecordError("constructed record schema is unsupported")
    return record


def main() -> int:
    """Validate one actor bundle, evidence envelope, full result, or bulk sweep."""

    try:
        # Node writes UTF-8 JSON to this bridge.  Reading the underlying bytes lets
        # json detect UTF-8 itself instead of using Windows' locale text encoding.
        input_stream = getattr(sys.stdin, "buffer", sys.stdin)
        bundle = json.load(input_stream)
        if isinstance(bundle, Mapping) and bundle.get("schema_version") in {EPISODE_EVIDENCE_SCHEMA, LEGACY_EPISODE_EVIDENCE_SCHEMA}:
            evidence = validate_pipeline_episode_evidence(bundle)
            output: Any = {
                "schema_version": "pipeline-episode-evidence-validation/v1",
                "evidence_id": evidence["evidence_id"],
                "committed_transitions": len(evidence["transition_ids"]),
            }
        elif isinstance(bundle, Mapping) and bundle.get("schema_version") == "pipeline-episode/v1":
            output = validate_pipeline_episode_result(bundle)
        elif isinstance(bundle, Mapping) and bundle.get("schema_version") == EPISODE_PUBLICATION_SWEEP_SCHEMA:
            output = validate_pipeline_episode_publication_sweep(bundle)
        else:
            output = validate_pipeline_bundle(bundle)
        sys.stdout.write(json.dumps(output, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n")
        return 0
    except (json.JSONDecodeError, DatasetLineageError, PipelineRecordError, TypeError, ValueError) as exc:
        diagnostic = getattr(exc, "diagnostic", None)
        if diagnostic is not None:
            sys.stderr.write(json.dumps({
                "error": "pipeline-record validation failed",
                "diagnostic": diagnostic,
            }, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n")
        else:
            sys.stderr.write(f"pipeline-record validation failed: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
