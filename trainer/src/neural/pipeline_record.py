"""PIPELINE-001 linked-record validator and one-shot JSON bridge.

This module validates one perspective-specific integration record. It does not
select features or labels and never accepts simulator state or a raw transition
log. Use ``python -m neural.pipeline_record`` for the finite stdin/stdout
bridge used by sim-core integration tests and collectors.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from typing import Any, Dict, Mapping, Optional, Sequence

from neural.canonical_action import validate_canonical_action
from neural.dataset_lineage import (
    DATASET_RECORD_SCHEMA,
    DatasetLineageError,
    DEFAULT_SPLIT_SEED,
    deterministic_split_for_battle,
    feature_schema_fingerprint,
    make_record,
    prefix_hash,
    validate_record_prefix,
)


PIPELINE_BUNDLE_SCHEMA = "pipeline-linked-record/v1"
PIPELINE_TRANSITION_SCHEMA = "pipeline-transition-reference/v1"
FORCED_SWITCH_BUNDLE_SCHEMA = "pipeline-forced-switch-record/v1"
FORCED_SWITCH_TRANSITION_SCHEMA = "pipeline-forced-switch-reference/v1"
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
_FORBIDDEN_KEYS = frozenset({
    "simulator_state", "rng_seed", "root_seed", "emitted_log_delta", "raw_log_delta",
    "raw_request", "private_team", "opponent_private", "future_events", "omniscient",
})
_UNRESOLVED_PROTOCOL_ALIASES = frozenset({"clearstatus", "-clearstatus", "nothing"})


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


def _prefix(observation: Mapping[str, Any], label: str) -> Sequence[str]:
    prefix = observation.get("protocol_prefix")
    if not isinstance(prefix, list) or any(not isinstance(line, str) or not line or line.strip() != line for line in prefix):
        raise PipelineRecordError(f"{label} protocol prefix is malformed")
    if isinstance(observation.get("event_cursor"), bool) or observation.get("event_cursor") != len(prefix):
        raise PipelineRecordError(f"{label} event cursor does not match its protocol prefix")
    for record_index, line in enumerate(prefix):
        if line.startswith("|"):
            command = line[1:].split("|", 1)[0]
            if command in _UNRESOLVED_PROTOCOL_ALIASES:
                detail = f'{label} protocol prefix has unresolved alias "{command}" at record {record_index}'
                raise PipelineRecordError(
                    detail,
                    {
                        "schema_version": "pipeline-diagnostic/v1",
                        "code": "pipeline/v1/unresolved-protocol-alias",
                        "detail": detail,
                        "record_index": record_index,
                        "record_command": command,
                    },
                )
        if line.startswith("|request|"):
            try:
                request_payload = json.loads(line[len("|request|"):])
            except json.JSONDecodeError as exc:
                raise PipelineRecordError(f"{label} protocol prefix contains a raw request") from exc
            if not isinstance(request_payload, dict) or set(request_payload) - {"rqid"}:
                raise PipelineRecordError(f"{label} protocol prefix contains a private request")
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
    }


def validate_pipeline_bundle(bundle: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate exact per-perspective joins and create a DATA-001 record."""

    _object(bundle, "pipeline bundle")
    _reject_private_payload(bundle, "pipeline bundle")
    _exact_keys(bundle, _BUNDLE_KEYS, "pipeline bundle")
    forced_switch = bundle.get("schema_version") == FORCED_SWITCH_BUNDLE_SCHEMA
    if bundle.get("schema_version") not in {PIPELINE_BUNDLE_SCHEMA, FORCED_SWITCH_BUNDLE_SCHEMA}:
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
    _exact_keys(transition, _TRANSITION_KEYS | ({"acting_player", "waiting_player"} if forced_switch else set()), "transition reference")
    expected_transition_schema = FORCED_SWITCH_TRANSITION_SCHEMA if forced_switch else PIPELINE_TRANSITION_SCHEMA
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
                or action.get("kind") != "switch"):
            raise PipelineRecordError("forced-switch bundle requires an ordinary actionable forced-switch input")

    for label, observation in (("input observation", input_observation), ("successor observation", successor_observation)):
        if observation.get("schema_version") != "observable-battle-state/v1":
            raise PipelineRecordError(f"{label} schema is unsupported")
        if observation.get("source_kind") != "sim_core" or observation.get("battle_id") != battle_id:
            raise PipelineRecordError(f"{label} source or battle identity disagrees")
        if observation.get("perspective") != perspective:
            raise PipelineRecordError(f"{label} perspective disagrees with record")
        _identifier(observation.get("observation_id"), "observation", f"{label} ID")
    input_prefix = _prefix(input_observation, "input observation")
    successor_prefix = _prefix(successor_observation, "successor observation")
    if len(successor_prefix) < len(input_prefix) or list(successor_prefix[:len(input_prefix)]) != list(input_prefix):
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
    if input_belief.get("source_protocol_prefix") != list(input_prefix):
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
    if successor_belief.get("source_protocol_prefix") != list(successor_prefix):
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

    request = _request_for_action(input_observation, perspective)
    try:
        validate_canonical_action(action, request, perspective)
    except (TypeError, ValueError) as exc:
        raise PipelineRecordError(f"canonical action validation failed: {exc}") from exc

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
        observation_prefix_hash=prefix_hash(input_prefix),
        observation_id=input_observation["observation_id"],
        action_id=action_id,
        belief_id=input_belief_id,
        transition_id=transition_id,
        private_data_provenance="acting_player_request",
        feature_input_eligibility="acting_player_private",
        schema_fingerprints={
            "observation": "observable-battle-state/v1",
            "belief": "belief-state/v1",
            "transition": "seeded-forced-switch/v1" if forced_switch else "seeded-transition/v1",
            "feature": feature_schema_fingerprint("features-not-produced/v1", []),
        },
        split_seed=DEFAULT_SPLIT_SEED,
        split=deterministic_split_for_battle(battle_id, DEFAULT_SPLIT_SEED),
        split_key=battle_id,
        input_fields=[],
    )
    validate_record_prefix(record, input_prefix)
    if record["schema_version"] != DATASET_RECORD_SCHEMA:
        raise PipelineRecordError("constructed record schema is unsupported")
    return record


def main() -> int:
    """Validate exactly one JSON bundle from stdin; emit its DATA-001 record."""

    try:
        bundle = json.load(sys.stdin)
        record = validate_pipeline_bundle(bundle)
        sys.stdout.write(json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n")
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
