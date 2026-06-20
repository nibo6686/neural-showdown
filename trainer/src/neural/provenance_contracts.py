"""Minimal provenance/no-leakage helper contracts (Batch A).

These are small, dependency-light guardrails that enforce the rules in
`artifacts/training_plan/state_provenance_schema_design_for_remaining_gaps.md`
*before* the full state schema is implemented. They do not change
`legal-action-v7`, do not migrate any state schema, and do not execute rollout
mechanics. Their only job is to make hidden-information leakage and
stale-damage shortcuts fail loudly.

Return convention matches the existing rollout modules: validators return
``{"available": bool, "reason": Optional[str], ...}``. ``available=False`` means
"fail closed" — the exact result is not derivable from the supplied
public/inferable provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


def _to_id(value: Any) -> str:
    return "".join(character for character in str(value or "").lower() if character.isalnum())


def _unavailable(reason: str, **extra: Any) -> Dict[str, Any]:
    return {"available": False, "reason": reason, **extra}


def _available(**extra: Any) -> Dict[str, Any]:
    return {"available": True, "reason": None, **extra}


# Keys that would leak a hidden sampled future value into provenance. None of
# these may appear in any state/feature-facing provenance dict.
FORBIDDEN_HIDDEN_KEYS = frozenset(
    {
        "sampled_wake_turn",
        "hidden_time",
        "statusstate_time",
        "status_state_time",
        "time",
        "sampled_duration",
        "sampled_hit_count",
        "sampled_called_move",
        "seed",
        "prng",
    }
)


def assert_no_hidden_sampled_values(provenance: Dict[str, Any]) -> None:
    """Raise if a provenance dict carries a hidden sampled future value.

    This is the structural no-leakage guard: builders below never accept a
    sampled duration/hit-count/called-move, but downstream code that assembles
    feature-facing provenance can call this to prove nothing leaked.
    """
    forbidden = {_to_id(key) for key in FORBIDDEN_HIDDEN_KEYS}
    leaked = sorted(forbidden & {_to_id(key) for key in provenance})
    if leaked:
        raise ValueError(f"hidden_sampled_value_leak:{','.join(leaked)}")


# ---------------------------------------------------------------------------
# Contract 1: delayed attack landing — no stale-damage reuse.
# ---------------------------------------------------------------------------

# The complete landing-time resolver bundle (design group 1, batch B owner).
# Batch A only validates presence; it does not compute damage.
REQUIRED_RESOLVER_INPUT_KEYS = (
    "source_snapshot",
    "move_id",
    "move_type",
    "move_category",
    "move_base_power",
    "target_snapshot",
    "field_snapshot",
)


def _snapshot_identity(snapshot: Any) -> str:
    if not isinstance(snapshot, dict):
        return ""
    return _to_id(snapshot.get("id") or snapshot.get("pokemon_id"))


def delayed_landing_resolvable(attack: Dict[str, Any], occupant_id: Any) -> Dict[str, Any]:
    """Decide whether a delayed attack may resolve exact damage on the occupant.

    Fail closed unless one of these holds for *this* landing occupant:

    1. ``target_specific`` — ``damage_by_target`` carries damage keyed by the
       occupant identity, with damage provenance.
    2. ``resolver_exact`` — a complete landing-time resolver bundle whose
       ``target_snapshot`` identity matches the occupant *and* that carries an
       oracle/Showdown-derived ``landing_damage`` with ``damage_provenance``.

    A complete bundle without exact damage returns ``resolver_inputs_present``
    with ``damage=None`` (computation deferred; the caller must fail closed).

    Damage computed for the original target must never be reused for a
    replacement occupant: an occupant absent from ``damage_by_target`` with no
    matching resolver bundle is unavailable, and a resolver bundle built for a
    different occupant returns ``resolver_target_mismatch``.
    """
    occupant = _to_id(occupant_id)
    if not occupant:
        return _unavailable("occupant_identity_required")

    damage_by_target = attack.get("damage_by_target")
    if isinstance(damage_by_target, dict):
        keyed = {_to_id(key): value for key, value in damage_by_target.items()}
        if occupant in keyed and attack.get("damage_provenance"):
            return _available(
                mode="target_specific",
                damage=int(keyed[occupant]),
                provenance=str(attack.get("damage_provenance")),
            )

    resolver = attack.get("resolver_inputs")
    if isinstance(resolver, dict):
        missing = [key for key in REQUIRED_RESOLVER_INPUT_KEYS if not resolver.get(key)]
        if missing:
            return _unavailable("resolver_inputs_incomplete:" + ",".join(missing))
        # The bundle must have been built for the actual landing occupant.
        if _snapshot_identity(resolver.get("target_snapshot")) != occupant:
            return _unavailable("resolver_target_mismatch")
        landing_damage = resolver.get("landing_damage")
        if isinstance(landing_damage, int) and resolver.get("damage_provenance"):
            return _available(
                mode="resolver_exact",
                damage=int(landing_damage),
                provenance=str(resolver.get("damage_provenance")),
            )
        # Inputs present but exact damage is not computed locally yet.
        return _available(mode="resolver_inputs_present", damage=None, provenance=None)

    return _unavailable("replacement_landing_damage_unavailable")


# ---------------------------------------------------------------------------
# Contract 2: hidden-duration no-leakage for sleep / confusion.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SleepProvenance:
    from_rest: bool
    turns_elapsed: int
    remaining_min: int
    remaining_max: int
    can_wake_this_turn: bool
    must_wake_by_turn: bool
    hidden_duration_unknown: bool


@dataclass(frozen=True)
class ConfusionProvenance:
    turns_elapsed: int
    remaining_min: int
    remaining_max: int
    can_end_this_turn: bool
    hidden_duration_unknown: bool
    self_hit_chance: float


# Gen 9 ranges, documented in v7_uncertainty_counter_distribution_audit.md.
# Natural sleep is a hidden 1..3 acting-turn duration; Rest is fixed.
_NATURAL_SLEEP_MAX = 3
_REST_SLEEP_DURATION = 2
_CONFUSION_MAX = 5
_CONFUSION_SELF_HIT_CHANCE = 1.0 / 3.0


def natural_sleep_provenance(turns_elapsed: int) -> SleepProvenance:
    """Public-only natural sleep provenance.

    Takes only the publicly observable elapsed acting turns. There is no
    parameter for the sampled wake turn, so the hidden duration cannot be
    surfaced. Remaining is a legal range and ``hidden_duration_unknown`` is True.
    """
    elapsed = max(0, int(turns_elapsed))
    remaining_max = max(0, _NATURAL_SLEEP_MAX - elapsed)
    # After at least one acting turn asleep it may already be eligible to wake.
    remaining_min = 0 if elapsed >= 1 else 1
    remaining_min = min(remaining_min, remaining_max)
    return SleepProvenance(
        from_rest=False,
        turns_elapsed=elapsed,
        remaining_min=remaining_min,
        remaining_max=remaining_max,
        can_wake_this_turn=remaining_min == 0,
        must_wake_by_turn=remaining_max == 0,
        hidden_duration_unknown=True,
    )


def rest_sleep_provenance(turns_elapsed: int) -> SleepProvenance:
    """Fixed-duration Rest sleep provenance (no hidden duration)."""
    elapsed = max(0, int(turns_elapsed))
    remaining = max(0, _REST_SLEEP_DURATION - elapsed)
    return SleepProvenance(
        from_rest=True,
        turns_elapsed=elapsed,
        remaining_min=remaining,
        remaining_max=remaining,
        can_wake_this_turn=remaining == 0,
        must_wake_by_turn=remaining == 0,
        hidden_duration_unknown=False,
    )


def confusion_provenance(turns_elapsed: int, *, start_max: int = _CONFUSION_MAX) -> ConfusionProvenance:
    """Public-only confusion provenance with a legal remaining range.

    Like natural sleep, takes only elapsed turns; the sampled end turn is never
    a parameter, so it cannot leak. The 33% self-hit chance is a fixed public
    probability, not a sampled outcome.
    """
    elapsed = max(0, int(turns_elapsed))
    remaining_max = max(0, int(start_max) - elapsed)
    remaining_min = 0 if elapsed >= 1 else 1
    remaining_min = min(remaining_min, remaining_max)
    return ConfusionProvenance(
        turns_elapsed=elapsed,
        remaining_min=remaining_min,
        remaining_max=remaining_max,
        can_end_this_turn=remaining_min == 0,
        hidden_duration_unknown=True,
        self_hit_chance=_CONFUSION_SELF_HIT_CHANCE,
    )


# ---------------------------------------------------------------------------
# Contract 3: ability knownness / suppression.
# ---------------------------------------------------------------------------


class AbilityKnownness(str, Enum):
    KNOWN = "known"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EffectiveAbility:
    ability: Optional[str]
    knownness: AbilityKnownness
    suppressed: bool = False  # Gastro Acid / Core Enforcer / Neutralizing Gas
    ignored: bool = False  # Mold Breaker-class attacker bypass

    @property
    def is_active(self) -> bool:
        return not self.suppressed and not self.ignored


def status_move_blocked_by_ability(defender: EffectiveAbility, blocking_ability_id: Any) -> Dict[str, Any]:
    """Tri-state status-move block decision. Fail closed when the ability is unknown.

    An unrevealed defender ability is neither assumed to be the blocking ability
    nor assumed not to be: it returns ``available=False`` with ``blocked=None``.
    A suppressed/ignored ability does not block.
    """
    if defender.knownness == AbilityKnownness.UNKNOWN or not defender.ability:
        return _unavailable("defender_ability_unknown", blocked=None)
    if not defender.is_active:
        return _available(blocked=False, reason_detail="ability_suppressed_or_ignored")
    blocked = _to_id(defender.ability) == _to_id(blocking_ability_id)
    return _available(blocked=blocked)


# ---------------------------------------------------------------------------
# Contract 4: reflection routing provenance (Magic Bounce).
# ---------------------------------------------------------------------------

REQUIRED_REFLECTION_KEYS = (
    "original_source",
    "reflector",
    "destination_side",
    "reflected_target",
    "effect_payload",
)


def validate_reflection_provenance(reflection: Dict[str, Any]) -> Dict[str, Any]:
    """Reflection (Magic Bounce) needs full routing provenance or it fails closed.

    Requires the original source, the reflector, the destination side, the
    reflected target, and the side-effect payload; the move must be reflectable;
    and the reflector ability must be known (an unrevealed ability cannot be
    assumed to reflect).
    """
    if not isinstance(reflection, dict):
        return _unavailable("reflection_mapping_required")
    missing = [key for key in REQUIRED_REFLECTION_KEYS if not reflection.get(key)]
    if missing:
        return _unavailable("reflection_provenance_incomplete:" + ",".join(missing))
    if not reflection.get("reflectable"):
        return _unavailable("move_not_reflectable")

    reflector_ability = reflection.get("reflector_ability")
    if not isinstance(reflector_ability, EffectiveAbility):
        return _unavailable("reflector_ability_provenance_required")
    if reflector_ability.knownness == AbilityKnownness.UNKNOWN or not reflector_ability.ability:
        return _unavailable("reflector_ability_unknown")
    if not reflector_ability.is_active:
        return _unavailable("reflector_ability_suppressed_or_ignored")

    return _available(
        new_source=reflection["reflector"],
        new_target=reflection["original_source"],
        destination_side=reflection["destination_side"],
        effect=reflection["effect_payload"],
    )


# ---------------------------------------------------------------------------
# Contract 5: sequential multi-hit per-hit trace.
# ---------------------------------------------------------------------------

_REQUIRED_HIT_KEYS = ("accuracy_roll", "hit", "base_power", "damage")
# A distribution summary describes risk for action features; it is never an
# exact rollout execution trace.
_SUMMARY_KEYS = frozenset({"multihit_min", "multihit_max", "multihit_expected", "expected_hits"})


def validate_multihit_trace(trace: Any) -> Dict[str, Any]:
    """Exact sequential multi-hit rollout requires a per-hit execution trace.

    Each hit must carry its accuracy branch, hit/miss outcome, base power, and
    damage. A distribution summary (expected/min/max hits) is rejected: it is an
    action-feature summary, not an exact rollout trace.
    """
    if isinstance(trace, dict) and _SUMMARY_KEYS & set(trace):
        return _unavailable("summary_is_not_exact_trace")
    if not isinstance(trace, list) or not trace:
        return _unavailable("per_hit_trace_required")
    for index, hit in enumerate(trace):
        if not isinstance(hit, dict):
            return _unavailable(f"hit[{index}]_mapping_required")
        missing = [key for key in _REQUIRED_HIT_KEYS if key not in hit]
        if missing:
            return _unavailable(f"hit[{index}]_incomplete:" + ",".join(missing))
    return _available(hit_count=len(trace))
