"""Opt-in per-action explanation traces for the live recommender (Part B).

Produces one record per legal action describing every scoring component the live
recommender had available, plus damage and side-effect annotations. Components
that did not run are reported as ``{"available": false, "reason": ...}`` rather
than silently omitted, so a trace always shows *why* a number is missing.

Sanitization: records contain only public/scoring fields (action labels, scores,
damage percentages, side-effect flags, checkpoint paths). They never include the
raw Showdown ``request`` payload, the private team list, PP/item secrets, or
feature vectors. See ``action_trace_runbook.md``.

Enabled by ``NEURAL_ACTION_TRACE=1``. When ``NEURAL_ACTION_TRACE_PATH`` is set,
the live server appends a JSONL line per ``/evaluate`` call.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .action_side_effects import annotate_action_side_effects


def action_trace_enabled() -> bool:
    return os.environ.get("NEURAL_ACTION_TRACE", "").strip().lower() in {"1", "true", "yes", "on"}


def _available(value: Any, **extra: Any) -> Dict[str, Any]:
    record = {"available": value is not None, "value": value}
    if value is None:
        record["reason"] = extra.pop("reason", "value_is_none")
    record.update(extra)
    return record


def _unavailable(reason: str, **extra: Any) -> Dict[str, Any]:
    record = {"available": False, "value": None, "reason": reason}
    record.update(extra)
    return record


# These branch scorers are separate seeded research tools (one_turn_branch,
# two_ply_branch, belief particles). The live recommender does not invoke them
# because live battles have no PRNG seed / exact-opponent reconstruction.
_LIVE_BRANCH_UNAVAILABLE = "not_invoked_by_live_recommender: requires seeded sim-core branch search (no live seed)"


def _damage_record(row: Mapping[str, Any]) -> Dict[str, Any]:
    method = row.get("damage_method")
    if method is None:
        return _unavailable("no_damage_estimate_for_action")
    return {
        "available": True,
        "damage_method": method,
        "average_percent": row.get("average_percent"),
        "min_percent": row.get("min_percent"),
        "max_percent": row.get("max_percent"),
        "ko_chance": row.get("ko_chance"),
        "type_effectiveness": row.get("type_effectiveness"),
        "immune": row.get("immune"),
        "used_exact_attacker_stats": bool(row.get("used_exact_attacker_stats")),
        "used_exact_defender_stats": bool(row.get("used_exact_defender_stats")),
        "fallback_reason": row.get("fallback_reason"),
    }


def _rollout_record(row: Mapping[str, Any], rollout_mode: Optional[str]) -> Dict[str, Any]:
    expected = row.get("expected_value")
    if expected is None:
        reason = row.get("rollout_unavailable_reason") or "no_rollout_expected_value"
        return _unavailable(
            str(reason),
            rollout_mode=row.get("rollout_mode") or rollout_mode,
            approximate_state=row.get("approximate_state"),
            details=row.get("rollout_unavailable_details"),
        )
    return {
        "available": True,
        "value": expected,
        "rollout_mode": row.get("rollout_mode") or rollout_mode,
        "approximate_state": row.get("approximate_state"),
        "std_value": row.get("std_value"),
        "rollout_count": row.get("rollout_count"),
        "method": row.get("method"),
    }


def build_action_trace_record(
    row: Mapping[str, Any],
    *,
    chosen_label: Optional[str],
    rollout_mode: Optional[str],
) -> Dict[str, Any]:
    label = str(row.get("label") or "")
    name = label.split(":", 1)[1].strip() if ":" in label else label
    ranker_score = row.get("ranker_score")
    policy_prob = row.get("policy_prob")
    return {
        "action_index": row.get("index"),
        "choice": row.get("choice"),  # Showdown command if the candidate carried one
        "label": label,
        "name": name,
        "kind": row.get("kind"),
        "action_category": row.get("action_category"),
        "legal": not bool(row.get("disabled")),
        "chosen": bool(chosen_label is not None and label == chosen_label),
        "final_score": row.get("final_score"),
        "ranks": {
            "final_rank": row.get("final_rank"),
            "ranker_only_rank": row.get("ranker_only_rank"),
            "rollout_only_rank": row.get("rollout_only_rank"),
        },
        "damage": _damage_record(row),
        "side_effects": annotate_action_side_effects(dict(row)),
        "scorers": {
            "rollout": _rollout_record(row, rollout_mode),
            "action_value_ranker": _available(
                ranker_score,
                reason="ranker_unavailable_or_disabled",
                method=row.get("method"),
            ),
            "policy_prior": _available(policy_prob, reason="policy_checkpoint_missing_or_disabled"),
            "switch_proxy_value": _available(row.get("estimated_value"), reason="not_a_switch_or_value_model_unavailable"),
            "material_one_turn": _unavailable(_LIVE_BRANCH_UNAVAILABLE),
            "one_turn_branch": _unavailable(_LIVE_BRANCH_UNAVAILABLE),
            "two_ply_exact": _unavailable(_LIVE_BRANCH_UNAVAILABLE),
            "belief_branch": _unavailable(_LIVE_BRANCH_UNAVAILABLE),
        },
        "score_components": dict(row.get("score_components") or {}),
        "warnings": list(row.get("approximation_warnings") or ([] if not row.get("note") else [row.get("note")])),
        "fallbacks": {
            "damage_fallback_reason": row.get("fallback_reason"),
            "rollout_unavailable_reason": row.get("rollout_unavailable_reason"),
        },
    }


def build_action_trace(
    *,
    rows: Sequence[Mapping[str, Any]],
    chosen_label: Optional[str],
    recommendation_method: str,
    rollout_mode: Optional[str],
    rollout_weight: float,
    ranker_weight: float,
    policy_weight: float,
    metadata: Mapping[str, Any],
) -> Dict[str, Any]:
    """Assemble the trace bundle attached to the recommender report."""
    records = [
        build_action_trace_record(row, chosen_label=chosen_label, rollout_mode=rollout_mode)
        for row in rows
    ]
    return {
        "schema_version": "action-trace-v1",
        "recommendation_method": recommendation_method,
        "chosen_label": chosen_label,
        "weights": {
            "rollout_weight": rollout_weight,
            "ranker_weight": ranker_weight,
            "policy_weight": policy_weight,
        },
        "rollout_mode": rollout_mode,
        "metadata": dict(metadata),
        "records": records,
    }


def write_action_trace_jsonl(
    bundle: Mapping[str, Any],
    *,
    room_id: Optional[str],
    player: Optional[str],
    turn: Optional[int],
    url: Optional[str] = None,
) -> Optional[str]:
    """Append one sanitized JSONL line for a captured state. Returns the path or None.

    Writes only when ``NEURAL_ACTION_TRACE_PATH`` is set. Includes room/turn/player
    identifiers so a disputed state can be located, but no private payload.
    """
    path = os.environ.get("NEURAL_ACTION_TRACE_PATH", "").strip()
    if not path:
        return None
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "room_id": room_id,
        "player": player,
        "turn": turn,
        "url": url,
        **{key: value for key, value in bundle.items()},
    }
    try:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
        return str(out)
    except Exception:  # pragma: no cover - tracing must never break /evaluate
        return None
