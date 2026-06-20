"""Exact sequential multi-hit execution-trace contract (Batch E).

Population Bomb / Triple Axel / Triple Kick-style moves use sequential accuracy
(stop-on-miss) and, for Triple Axel, a per-hit power ramp. They are NOT ordinary
fixed multi-hit moves. Exact rollout parity for them requires a complete per-hit
execution trace supplied as oracle/Showdown-fixture provenance — never inferred
from a hit chance, an expected-hit count, or an action-feature distribution
summary, and never exposed as a model-facing feature.

This module validates such a trace and replays it deterministically (honoring
stop-on-miss), failing closed when the trace is missing, incomplete, mismatched,
or is actually a distribution summary.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _to_id(value: Any) -> str:
    return "".join(character for character in str(value or "").lower() if character.isalnum())


def _unavailable(reason: str, **extra: Any) -> Dict[str, Any]:
    return {"available": False, "reason": reason, **extra}


def _available(**extra: Any) -> Dict[str, Any]:
    return {"available": True, "reason": None, **extra}


# A distribution/summary describes risk for action features; it is never an exact
# rollout execution trace.
_SUMMARY_KEYS = frozenset(
    {"multihit_min", "multihit_max", "multihit_expected", "expected_hits", "hit_chance"}
)


def validate_sequential_multihit_trace(trace: Any) -> Dict[str, Any]:
    """Completeness check for an exact per-hit execution trace.

    Required: ``move`` id, ordered ``hits`` records (each with ``index`` and
    ``hit``; landed hits carry ``damage``), explicit ``total_damage`` and
    ``hit_count``, and ``provenance``. A distribution summary is rejected.
    """
    if isinstance(trace, dict) and _SUMMARY_KEYS & set(trace):
        return _unavailable("summary_is_not_exact_trace")
    if not isinstance(trace, dict):
        return _unavailable("trace_mapping_required")
    move = _to_id(trace.get("move"))
    if not move:
        return _unavailable("move_id_required")
    hits = trace.get("hits")
    if not isinstance(hits, list) or not hits:
        return _unavailable("per_hit_records_required")
    for index, hit in enumerate(hits):
        if not isinstance(hit, dict):
            return _unavailable(f"hit[{index}]_mapping_required")
        if hit.get("index") != index:
            return _unavailable(f"hit[{index}]_index_mismatch")
        if "hit" not in hit:
            return _unavailable(f"hit[{index}]_missing:hit")
        if hit.get("hit") and "damage" not in hit:
            return _unavailable(f"hit[{index}]_missing:damage")
    if not isinstance(trace.get("total_damage"), int):
        return _unavailable("total_damage_required")
    if not isinstance(trace.get("hit_count"), int):
        return _unavailable("hit_count_required")
    if not trace.get("provenance"):
        return _unavailable("provenance_required")
    return _available(move=move)


def execute_sequential_multihit(
    trace: Any,
    *,
    expected_move: Optional[Any] = None,
    expected_source: Optional[Any] = None,
    expected_target: Optional[Any] = None,
) -> Dict[str, Any]:
    """Replay a per-hit trace with stop-on-miss and verify internal consistency.

    Returns total damage, landed hit count, whether a miss occurred, and the
    ordered per-hit base powers (for the Triple Axel ramp). Fails closed when the
    trace is invalid, the move/source/target disagrees with what is represented,
    or the replayed totals disagree with the trace's declared totals.
    """
    validated = validate_sequential_multihit_trace(trace)
    if not validated["available"]:
        return {**validated, "executed": False}

    move = validated["move"]
    if expected_move is not None and _to_id(expected_move) != move:
        return _unavailable("trace_move_mismatch", executed=False)
    if expected_source is not None and trace.get("source") and _to_id(expected_source) != _to_id(trace["source"]):
        return _unavailable("trace_source_mismatch", executed=False)
    if expected_target is not None and trace.get("target") and _to_id(expected_target) != _to_id(trace["target"]):
        return _unavailable("trace_target_mismatch", executed=False)

    stop_on_miss = bool(trace.get("stop_on_miss", True))
    total = 0
    hit_count = 0
    missed = False
    per_hit_power: List[int] = []
    for hit in trace["hits"]:
        if hit.get("hit"):
            total += max(0, int(hit["damage"]))
            hit_count += 1
            if "base_power" in hit:
                per_hit_power.append(int(hit["base_power"]))
        else:
            missed = True
            if stop_on_miss:
                break

    if total != int(trace["total_damage"]):
        return _unavailable(f"total_damage_inconsistent:{total}!={int(trace['total_damage'])}", executed=False)
    if hit_count != int(trace["hit_count"]):
        return _unavailable(f"hit_count_inconsistent:{hit_count}!={int(trace['hit_count'])}", executed=False)

    return _available(
        executed=True,
        move=move,
        total_damage=total,
        hit_count=hit_count,
        missed=missed,
        per_hit_power=per_hit_power,
    )
