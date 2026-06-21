"""First append-only v8 belief feature slice.

This slice is a *pure function* of an ``OpponentSetBelief`` snapshot for the
public opponent active slot.  It exposes compact source-quality and belief
summary features only -- no candidate-specific threat features yet, no hardcoded
strategy, and no hidden-truth/future-reveal inputs (the belief is already a pure
function of the public prefix + pinned prior).

Missing prior / source-absent state is represented explicitly: ``has_meta_prior``
is 0 and ``prior_other_mass`` is 1.0 rather than silent zeros, so downstream
consumers can tell "the source did not know" from "the value is zero".
"""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

from .opponent_set_belief import OpponentSetBelief


V8_BELIEF_FEATURE_VERSION = "live-private-belief-v8"

V8_BELIEF_FEATURE_NAMES: List[str] = [
    "opponent_belief_has_meta_prior",
    "opponent_belief_prior_alias_used",
    "opponent_belief_prior_other_mass",
    "opponent_belief_prior_contradiction",
    "opponent_belief_confirmed_fact_count_norm",
    "opponent_belief_ruled_out_fact_count_norm",
    "opponent_belief_current_state_only_fact_count_norm",
    "opponent_belief_source_absent_fact_count_norm",
    "opponent_belief_support_size_norm",
    "opponent_belief_possible_ability_count_norm",
    "opponent_belief_possible_move_count_norm",
    "opponent_belief_possible_tera_count_norm",
    "opponent_belief_ability_max_posterior",
    "opponent_belief_ability_entropy_norm",
    "opponent_belief_confirmed_ability_known",
    "opponent_belief_confirmed_item_known",
    "opponent_belief_confirmed_tera_known",
    "opponent_belief_quality_factorized",
    "opponent_belief_quality_coarse_movepool_support",
    "opponent_belief_quality_item_unknown",
    "opponent_belief_quality_uncalibrated_probabilities",
]
V8_BELIEF_FEATURE_DIM = len(V8_BELIEF_FEATURE_NAMES)


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return low
    if not math.isfinite(number):
        return low
    return max(low, min(high, number))


def _count_norm(count: int, denominator: int) -> float:
    return _clip(float(count) / float(max(1, denominator)))


def _log_count_norm(count: int) -> float:
    return _clip(math.log1p(max(0, count)) / math.log(101.0))


def _ability_posterior(belief: OpponentSetBelief):
    """Coarse ability posterior over represented hypotheses plus the tail.

    Returns ``(max_posterior, normalized_entropy)`` where the entropy is taken
    over the represented ability masses plus the unknown tail and normalized by
    ``log(num_categories)``.  These are uncalibrated declaration weights, not
    generator frequencies; the quality flags advertise that.
    """
    ability_mass = {}
    for hypothesis in belief.hypotheses:
        if hypothesis.ability:
            ability_mass[hypothesis.ability] = (
                ability_mass.get(hypothesis.ability, 0.0) + hypothesis.probability
            )
    categories = list(ability_mass.values())
    if belief.other_mass > 0.0:
        categories.append(belief.other_mass)
    total = sum(categories)
    if total <= 0.0 or len(categories) == 0:
        return 0.0, 0.0
    probs = [value / total for value in categories if value > 0.0]
    max_posterior = max(probs)
    if len(probs) < 2:
        return max_posterior, 0.0
    entropy = -sum(p * math.log(p) for p in probs)
    return max_posterior, _clip(entropy / math.log(len(probs)))


def v8_belief_slice_feature_vector(belief: Optional[OpponentSetBelief]) -> np.ndarray:
    """Compute the v8 belief slice for one opponent active slot belief.

    ``belief is None`` (no public opponent slot) yields explicit-unknown values.
    """
    if belief is None or not belief.source_available:
        values = [0.0] * V8_BELIEF_FEATURE_DIM
        # Explicit unknown: no prior, full tail mass.
        values[V8_BELIEF_FEATURE_NAMES.index("opponent_belief_prior_other_mass")] = 1.0
        if belief is not None:
            # A constructed-but-empty belief still carries contradiction/quality.
            values[3] = float(bool(belief.prior_contradiction))
        return np.asarray(values, dtype=np.float32)

    confirmed = belief.confirmed
    ruled_out = belief.ruled_out
    confirmed_count = (
        len(confirmed.moves)
        + int(bool(confirmed.ability))
        + int(bool(confirmed.item))
        + int(bool(confirmed.tera_type))
    )
    ruled_out_count = (
        len(ruled_out.abilities)
        + len(ruled_out.items)
        + len(ruled_out.moves)
        + len(ruled_out.tera_types)
    )
    current_state_only_count = sum(
        1 for row in belief.evidence_ledger if row.current_state_only
    )
    source_absent_count = sum(
        1 for row in belief.evidence_ledger if not row.source_covered
    )
    max_posterior, ability_entropy = _ability_posterior(belief)
    warnings = set(belief.prior_coverage_warnings)

    values = [
        1.0,  # has_meta_prior
        float(bool(belief.prior_source_key)),  # prior_alias_used
        _clip(belief.other_mass),  # prior_other_mass
        float(bool(belief.prior_contradiction)),
        _count_norm(confirmed_count, 10),
        _count_norm(ruled_out_count, 20),
        _count_norm(current_state_only_count, 10),
        _count_norm(source_absent_count, 10),
        _log_count_norm(len(belief.hypotheses)),
        _count_norm(len(belief.possible_abilities), 6),
        _count_norm(len(belief.possible_moves), 24),
        _count_norm(len(belief.possible_tera_types), 18),
        _clip(max_posterior),
        _clip(ability_entropy),
        float(bool(confirmed.ability)),
        float(bool(confirmed.item)),
        float(bool(confirmed.tera_type)),
        float(belief.prior_joint_quality == "factorized"),
        float("movepool_is_not_an_exact_four_move_set" in warnings),
        float("items_absent_from_existing_role_data" in warnings),
        float(
            belief.prior_joint_quality == "factorized"
            or "role_weights_unavailable_equal_weight_assumption" in warnings
        ),
    ]
    vector = np.asarray(values, dtype=np.float32)
    if vector.shape[0] != V8_BELIEF_FEATURE_DIM:
        raise ValueError(
            f"v8 belief slice size mismatch: got {vector.shape[0]}, "
            f"expected {V8_BELIEF_FEATURE_DIM}."
        )
    return vector
