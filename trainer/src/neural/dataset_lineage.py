"""DATA-001 dataset-record lineage and split guardrails.

This module is an additive envelope for existing examples.  It does not alter
feature vectors, checkpoints, model defaults, or legacy dataset files.  A
consumer can require the envelope before training/evaluation and fail closed
when identity, provenance, schema, privacy, or split evidence is ambiguous.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


DATASET_RECORD_SCHEMA = "dataset-record/v1"
DEFAULT_SPLIT_SEED = 20260923
SOURCE_KINDS = frozenset({"sim_core", "replay", "live"})
PERSPECTIVES = frozenset({"p1", "p2"})
SPLITS = frozenset({"train", "validation", "test"})
PRIVATE_PROVENANCE = frozenset({"none", "acting_player_request", "reconstructed_public_prefix", "local_trace_private"})
FEATURE_INPUT_ELIGIBILITY = frozenset({"public_only", "acting_player_private", "simulator_only"})
SCHEMA_FINGERPRINT_KEYS = ("observation", "belief", "transition", "feature")
PUBLIC_INPUT_FORBIDDEN_FIELDS = frozenset(
    {
        "raw_request",
        "private_team",
        "opponent_private",
        "belief_candidates",
        "simulator_state",
        "rng_seed",
        "future_events",
    }
)

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = {
    "observation_id": re.compile(r"^obs-[0-9a-f]{64}$"),
    "action_id": re.compile(r"^act-[0-9a-f]{64}$"),
    "belief_id": re.compile(r"^belief-[0-9a-f]{64}$"),
    "transition_id": re.compile(r"^transition-[0-9a-f]{64}$"),
}


class DatasetLineageError(ValueError):
    """Raised when a dataset record cannot be proven safe to consume."""


def canonical_json(value: Any) -> str:
    """Return deterministic UTF-8 JSON used by IDs and serialized metadata."""

    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def prefix_hash(protocol_prefix: Sequence[str]) -> str:
    """Hash the exact ordered source prefix used for an example boundary."""

    if any(not isinstance(line, str) for line in protocol_prefix):
        raise DatasetLineageError("protocol prefix must contain only strings")
    return _sha256(list(protocol_prefix))


def feature_schema_fingerprint(version: str, feature_names: Sequence[str]) -> str:
    """Bind a feature version to its ordered feature-name list."""

    if not isinstance(version, str) or not version.strip() or any(not isinstance(name, str) for name in feature_names):
        raise DatasetLineageError("feature schema metadata is malformed")
    return f"{version}:{_sha256(list(feature_names))}"


def record_from_source_prefix(
    *,
    battle_id: str,
    replay_id: str,
    source_kind: str,
    source_ref: str,
    ruleset: str,
    parser_version: str,
    perspective: str,
    protocol_prefix: Sequence[str],
    private_data_provenance: str,
    feature_input_eligibility: str,
    schema_fingerprints: Mapping[str, Optional[str]],
    split_seed: int = DEFAULT_SPLIT_SEED,
    split: Optional[str] = None,
    observation_id: Optional[str] = None,
    action_id: Optional[str] = None,
    belief_id: Optional[str] = None,
    transition_id: Optional[str] = None,
    input_fields: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Build an envelope from an exact parser/simulator prefix."""

    cursor = len(protocol_prefix)
    payload: Dict[str, Any] = {
        "battle_id": battle_id,
        "replay_id": replay_id,
        "source_kind": source_kind,
        "source_ref": source_ref,
        "ruleset": ruleset,
        "parser_version": parser_version,
        "perspective": perspective,
        "observation_cursor": cursor,
        "feature_cursor": cursor,
        "observation_prefix_hash": prefix_hash(protocol_prefix),
        "observation_id": observation_id,
        "action_id": action_id,
        "belief_id": belief_id,
        "transition_id": transition_id,
        "private_data_provenance": private_data_provenance,
        "feature_input_eligibility": feature_input_eligibility,
        "schema_fingerprints": dict(schema_fingerprints),
        "split": split or deterministic_split_for_battle(battle_id, split_seed),
        "split_seed": split_seed,
        "split_key": battle_id,
    }
    if input_fields is not None:
        payload["input_fields"] = list(input_fields)
    return make_record(**payload)


def _require_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DatasetLineageError(f"{key} is required")
    return value


def _require_non_negative_int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DatasetLineageError(f"{key} must be a non-negative integer")
    return value


def _validate_digest(value: Any, key: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise DatasetLineageError(f"{key} must be a lowercase SHA-256 digest")


def _identity_payload(record: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": record["schema_version"],
        "battle_id": record["battle_id"],
        "replay_id": record["replay_id"],
        "source_kind": record["source_kind"],
        "perspective": record["perspective"],
        "observation_cursor": record["observation_cursor"],
        "observation_prefix_hash": record["observation_prefix_hash"],
        "observation_id": record["observation_id"],
        "action_id": record["action_id"],
        "belief_id": record["belief_id"],
        "transition_id": record["transition_id"],
    }


def expected_record_id(record: Mapping[str, Any]) -> str:
    """Compute the stable identity for a validated record, excluding mutable metadata."""

    return f"datarec-{_sha256(_identity_payload(record))}"


def validate_record_prefix(record: Mapping[str, Any], protocol_prefix: Sequence[str]) -> None:
    """Verify that the supplied source prefix matches the recorded boundary/hash."""

    normalized = validate_record(record)
    if len(protocol_prefix) != normalized["observation_cursor"]:
        raise DatasetLineageError("protocol prefix length does not match observation cursor")
    if prefix_hash(protocol_prefix) != normalized["observation_prefix_hash"]:
        raise DatasetLineageError("protocol prefix hash does not match observation boundary")


def _validate_id(value: Any, key: str) -> None:
    if value is not None and (not isinstance(value, str) or not _ID_RE[key].fullmatch(value)):
        raise DatasetLineageError(f"{key} has an unsupported identity format")


def validate_record(record: Mapping[str, Any], *, require_record_id: bool = True) -> Dict[str, Any]:
    """Validate and return a normalized DATA-001 record.

    The validator intentionally requires the source boundary and feature cutoff
    separately.  ``feature_cursor`` may never exceed ``observation_cursor``;
    this is the fail-closed future-information check.
    """

    if not isinstance(record, Mapping):
        raise DatasetLineageError("dataset record must be an object")
    schema_version = record.get("schema_version")
    if schema_version != DATASET_RECORD_SCHEMA:
        raise DatasetLineageError(f"unsupported dataset record schema: {schema_version!r}")

    normalized: Dict[str, Any] = {
        "schema_version": schema_version,
        "record_id": record.get("record_id"),
        "battle_id": _require_string(record, "battle_id"),
        "replay_id": _require_string(record, "replay_id"),
        "source_kind": _require_string(record, "source_kind"),
        "source_ref": _require_string(record, "source_ref"),
        "ruleset": _require_string(record, "ruleset"),
        "parser_version": _require_string(record, "parser_version"),
        "perspective": _require_string(record, "perspective"),
        "observation_cursor": _require_non_negative_int(record, "observation_cursor"),
        "feature_cursor": _require_non_negative_int(record, "feature_cursor"),
        "observation_prefix_hash": record.get("observation_prefix_hash"),
        "observation_id": record.get("observation_id"),
        "action_id": record.get("action_id"),
        "belief_id": record.get("belief_id"),
        "transition_id": record.get("transition_id"),
        "private_data_provenance": _require_string(record, "private_data_provenance"),
        "feature_input_eligibility": _require_string(record, "feature_input_eligibility"),
        "schema_fingerprints": record.get("schema_fingerprints"),
        "split": _require_string(record, "split"),
        "split_seed": _require_non_negative_int(record, "split_seed"),
        "split_key": record.get("split_key"),
    }

    if normalized["source_kind"] not in SOURCE_KINDS:
        raise DatasetLineageError("unsupported source_kind")
    if normalized["perspective"] not in PERSPECTIVES:
        raise DatasetLineageError("unsupported perspective")
    if normalized["split"] not in SPLITS:
        raise DatasetLineageError("unsupported split")
    if normalized["private_data_provenance"] not in PRIVATE_PROVENANCE:
        raise DatasetLineageError("unsupported private_data_provenance")
    if normalized["feature_input_eligibility"] not in FEATURE_INPUT_ELIGIBILITY:
        raise DatasetLineageError("unsupported feature_input_eligibility")
    if normalized["feature_cursor"] > normalized["observation_cursor"]:
        raise DatasetLineageError("feature cursor is after observation cursor")
    if normalized["split_key"] != normalized["battle_id"]:
        raise DatasetLineageError("split_key must equal battle_id")
    _validate_digest(normalized["observation_prefix_hash"], "observation_prefix_hash")

    fingerprints = normalized["schema_fingerprints"]
    if not isinstance(fingerprints, Mapping) or set(fingerprints) != set(SCHEMA_FINGERPRINT_KEYS):
        raise DatasetLineageError("schema_fingerprints must contain the exact supported keys")
    for key in SCHEMA_FINGERPRINT_KEYS:
        value = fingerprints[key]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise DatasetLineageError(f"schema_fingerprints.{key} must be a string or null")
    if not fingerprints["observation"] or not fingerprints["feature"]:
        raise DatasetLineageError("observation and feature schema fingerprints are required")

    if normalized["private_data_provenance"] == "none" and normalized["feature_input_eligibility"] != "public_only":
        raise DatasetLineageError("private-free records must be public_only")
    if normalized["private_data_provenance"] != "none" and normalized["feature_input_eligibility"] == "public_only":
        raise DatasetLineageError("private provenance cannot enter a public_only input")

    for key in ("observation_id", "action_id", "belief_id", "transition_id"):
        _validate_id(normalized[key], key)
    input_fields = record.get("input_fields")
    if input_fields is not None:
        if not isinstance(input_fields, list) or any(not isinstance(item, str) for item in input_fields):
            raise DatasetLineageError("input_fields must be a list of strings")
        if normalized["feature_input_eligibility"] == "public_only":
            leaked = sorted(set(input_fields) & PUBLIC_INPUT_FORBIDDEN_FIELDS)
            if leaked:
                raise DatasetLineageError(f"private fields in public input: {','.join(leaked)}")
        normalized["input_fields"] = list(input_fields)

    if require_record_id:
        record_id = normalized["record_id"]
        if not isinstance(record_id, str) or not re.fullmatch(r"datarec-[0-9a-f]{64}", record_id):
            raise DatasetLineageError("record_id is missing or malformed")
        if record_id != expected_record_id(normalized):
            raise DatasetLineageError("record_id does not match deterministic identity")
    return normalized


def make_record(**fields: Any) -> Dict[str, Any]:
    """Build a record and derive its ID after validating all lineage fields."""

    payload = dict(fields)
    payload.setdefault("schema_version", DATASET_RECORD_SCHEMA)
    payload.setdefault("observation_id", None)
    payload.setdefault("action_id", None)
    payload.setdefault("belief_id", None)
    payload.setdefault("transition_id", None)
    payload.setdefault("split_key", payload.get("battle_id"))
    payload["record_id"] = None
    normalized = validate_record(payload, require_record_id=False)
    normalized["record_id"] = expected_record_id(normalized)
    return normalized


def deterministic_split_for_battle(
    battle_id: str,
    split_seed: int,
    *,
    proportions: Optional[Mapping[str, float]] = None,
) -> str:
    """Assign one battle to one split using only stable battle identity and seed."""

    if not isinstance(battle_id, str) or not battle_id.strip():
        raise DatasetLineageError("battle_id is required for split assignment")
    if isinstance(split_seed, bool) or not isinstance(split_seed, int) or split_seed < 0:
        raise DatasetLineageError("split_seed must be a non-negative integer")
    ordered = list((proportions or {"train": 0.8, "validation": 0.1, "test": 0.1}).items())
    if {name for name, _ in ordered} != SPLITS or any(weight <= 0 for _, weight in ordered):
        raise DatasetLineageError("proportions must define positive train/validation/test weights")
    total = sum(float(weight) for _, weight in ordered)
    point = int(hashlib.sha256(f"{split_seed}:{battle_id}".encode("utf-8")).hexdigest(), 16) / float(1 << 256)
    cumulative = 0.0
    for name, weight in ordered:
        cumulative += float(weight) / total
        if point < cumulative:
            return name
    return ordered[-1][0]


def validate_records(records: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Validate records and reject duplicate identities or cross-split battles."""

    normalized: List[Dict[str, Any]] = []
    seen_ids = set()
    battle_splits: Dict[str, str] = {}
    replay_splits: Dict[str, str] = {}
    for record in records:
        item = validate_record(record)
        if item["record_id"] in seen_ids:
            raise DatasetLineageError(f"duplicate record identity: {item['record_id']}")
        seen_ids.add(item["record_id"])
        for key, mapping in (("battle_id", battle_splits), ("replay_id", replay_splits)):
            identity = item[key]
            prior = mapping.get(identity)
            if prior is not None and prior != item["split"]:
                raise DatasetLineageError(f"{key} crosses dataset splits: {identity}")
            mapping[identity] = item["split"]
        normalized.append(item)
    return normalized


def source_metric_report(
    records: Sequence[Mapping[str, Any]],
    metrics_by_record: Mapping[str, Mapping[str, float]],
) -> Dict[str, Any]:
    """Summarize supplied metrics without pooling source regimes together."""

    normalized = validate_records(records)
    grouped: Dict[str, List[Mapping[str, float]]] = defaultdict(list)
    for record in normalized:
        metrics = metrics_by_record.get(record["record_id"])
        if metrics is None:
            raise DatasetLineageError(f"missing metrics for record: {record['record_id']}")
        if any(not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in metrics.values()):
            raise DatasetLineageError("source metrics must be finite numbers")
        grouped[record["source_kind"]].append(metrics)

    report: Dict[str, Any] = {"sources": {}, "record_count": len(normalized)}
    for source_kind in sorted(grouped):
        rows = grouped[source_kind]
        metric_names = sorted({name for row in rows for name in row})
        report["sources"][source_kind] = {
            "record_count": len(rows),
            "splits": sorted({record["split"] for record in normalized if record["source_kind"] == source_kind}),
            "metrics": {
                name: sum(float(row[name]) for row in rows if name in row) / max(1, sum(name in row for row in rows))
                for name in metric_names
            },
        }
    return report
