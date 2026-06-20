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
from typing import Any, Dict, List, Optional, Tuple


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


def effective_ability_from_state(mon: Dict[str, Any], attacker: Optional[Dict[str, Any]] = None) -> EffectiveAbility:
    """Build an ``EffectiveAbility`` from dict state with explicit provenance.

    No-leakage: an ability is treated as ``KNOWN`` only when ``ability_known`` is
    truthy. An unknown ability does not surface its raw identity (set to None),
    so downstream code cannot use an unrevealed ability as if it were public.
    ``ability_suppressed`` (Gastro Acid / Core Enforcer / Neutralizing Gas) and a
    Mold Breaker-class attacker's ``ability_ignoring`` mark the ability inactive.
    """
    if not isinstance(mon, dict):
        return EffectiveAbility(ability=None, knownness=AbilityKnownness.UNKNOWN)
    ability = _to_id(mon.get("ability") or mon.get("base_ability")) or None
    known_flag = mon.get("ability_known")
    if known_flag is None:
        knownness = AbilityKnownness.UNKNOWN
    elif _to_id(known_flag) == "inferred":
        knownness = AbilityKnownness.INFERRED
    elif bool(known_flag):
        knownness = AbilityKnownness.KNOWN
    else:
        knownness = AbilityKnownness.UNKNOWN
    suppressed = bool(mon.get("ability_suppressed"))
    ignored = bool(attacker.get("ability_ignoring")) if isinstance(attacker, dict) else False
    if knownness == AbilityKnownness.UNKNOWN:
        ability = None
    return EffectiveAbility(ability=ability, knownness=knownness, suppressed=suppressed, ignored=ignored)


def _is_status_move(move: Dict[str, Any]) -> bool:
    category = _to_id(move.get("category"))
    if category:
        return category == "status"
    return bool(move.get("is_status_move")) or bool(move.get("status"))


# Mold Breaker / Teravolt / Turboblaze set ``move.ignoreAbility`` and bypass
# ``breakable`` abilities (e.g. Good as Gold) per bundled Showdown
# `sim/battle.ts suppressingAbility` / the `breakable` flag.
_MOLD_BREAKER_ABILITIES = frozenset({"moldbreaker", "teravolt", "turboblaze"})


def _holds_known_item(mon: Any, item_id: Any) -> bool:
    """True only when ``mon`` is *known* to hold ``item_id`` (not a guess)."""
    if not isinstance(mon, dict):
        return False
    if not mon.get("item_known"):
        return False
    if mon.get("item_removed") or mon.get("item_consumed"):
        return False
    return _to_id(mon.get("item")) == _to_id(item_id)


def source_ignores_target_abilities(attacker: Optional[Dict[str, Any]]) -> bool:
    """True only when the attacker's ability is a KNOWN Mold Breaker-class ability.

    An unknown attacker ability is never assumed to bypass: a hidden ability stays
    hidden, so the common case (no bypass) holds until the ability is revealed.
    """
    if not isinstance(attacker, dict):
        return False
    effective = effective_ability_from_state(attacker)
    return effective.knownness == AbilityKnownness.KNOWN and effective.ability in _MOLD_BREAKER_ABILITIES


def resolve_status_move_ability_block(
    target: Dict[str, Any], attacker: Optional[Dict[str, Any]], move: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Good as Gold: a known-active Good as Gold blocks an opponent status move.

    Returns ``None`` when not applicable — the move is not a status move, or the
    candidate blocker is not a *known* Good as Gold — so callers fall through to
    other prevention logic without changing behavior. When the known ability is
    Good as Gold but suppressed/ignored, it returns a non-blocking result. An
    unknown/unrevealed ability never reaches a block here (it is not KNOWN), so
    the unrevealed-ability case stays an explicit fixture GAP rather than a guess.

    A KNOWN Mold Breaker-class attacker bypasses Good as Gold, unless the target
    holds a KNOWN Ability Shield (verified vs bundled Showdown
    `suppressingAbility`: bypass requires ``!target.hasItem('Ability Shield')``).
    """
    if not _is_status_move(move):
        return None
    defender = effective_ability_from_state(target, attacker)
    if source_ignores_target_abilities(attacker) and not _holds_known_item(target, "abilityshield"):
        defender = EffectiveAbility(
            ability=defender.ability,
            knownness=defender.knownness,
            suppressed=defender.suppressed,
            ignored=True,
        )
    if defender.knownness != AbilityKnownness.KNOWN or defender.ability != "goodasgold":
        return None
    decision = status_move_blocked_by_ability(defender, "goodasgold")
    blocked = bool(decision.get("blocked"))
    return {
        "prevented": blocked,
        "blocked": blocked,
        "reason": "good_as_gold_status_block" if blocked else "good_as_gold_suppressed_or_ignored",
    }


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


# ===========================================================================
# Public-information belief + effective-context contracts.
#
# These guard the rule that the model receives the same *category* of
# information a skilled Showdown player has (known species, possible
# abilities/items, speed ranges, revealed/inferred public info) but never the
# hidden truth before it is revealed. They are pure, torch-free helpers; they
# do not wire into live extraction (that stays unchanged) — they codify the
# contract and back the no-leakage tests.
# ===========================================================================


def _id_tuple(values: Any) -> Tuple[str, ...]:
    if not isinstance(values, (list, tuple, set)):
        return ()
    seen: Dict[str, None] = {}
    for value in values:
        identifier = _to_id(value)
        if identifier:
            seen.setdefault(identifier, None)
    return tuple(seen)


# --- Public ability belief -------------------------------------------------


@dataclass(frozen=True)
class PublicAbilityBelief:
    """Public/inferable belief about a Pokemon's ability.

    ``possible_abilities`` is the species/format ability list — public knowledge
    a skilled player has. The *hidden true* ability is never stored here; it
    becomes ``revealed_ability`` only after a public activation/protocol event,
    or ``inferred_ability`` only when narrowed by public evidence.
    """

    species_known: bool
    possible_abilities: Tuple[str, ...]
    revealed_ability: Optional[str]
    inferred_ability: Optional[str]
    knownness: AbilityKnownness

    @property
    def effective_ability(self) -> EffectiveAbility:
        if self.knownness == AbilityKnownness.KNOWN and self.revealed_ability:
            return EffectiveAbility(ability=self.revealed_ability, knownness=AbilityKnownness.KNOWN)
        if self.knownness == AbilityKnownness.INFERRED and self.inferred_ability:
            return EffectiveAbility(ability=self.inferred_ability, knownness=AbilityKnownness.INFERRED)
        return EffectiveAbility(ability=None, knownness=AbilityKnownness.UNKNOWN)


def public_ability_belief(
    species_known: bool,
    possible_abilities: Any,
    *,
    revealed_ability: Any = None,
    inferred_ability: Any = None,
) -> PublicAbilityBelief:
    """Build a `PublicAbilityBelief`. Revealed wins over inferred over unknown.

    Listing ``possible_abilities`` never selects one as truth; only an explicit
    revealed/inferred public signal sets a concrete ability.
    """
    possible = _id_tuple(possible_abilities)
    revealed = _to_id(revealed_ability) or None
    inferred = _to_id(inferred_ability) or None
    if revealed:
        return PublicAbilityBelief(bool(species_known), possible, revealed, None, AbilityKnownness.KNOWN)
    if inferred:
        return PublicAbilityBelief(bool(species_known), possible, None, inferred, AbilityKnownness.INFERRED)
    return PublicAbilityBelief(bool(species_known), possible, None, None, AbilityKnownness.UNKNOWN)


# --- Public item belief ----------------------------------------------------


class ItemState(str, Enum):
    KNOWN = "known"
    INFERRED = "inferred"
    UNKNOWN = "unknown"
    REMOVED = "removed"  # Knock Off / Trick / Thief / Magician
    CONSUMED = "consumed"  # berry / gem / one-time item used


@dataclass(frozen=True)
class PublicItemBelief:
    """Public/inferable belief about a held item.

    ``possible_items`` may be listed when format/team-generation constrains it.
    A hidden item is never surfaced as ``revealed_item`` until a public event.
    """

    possible_items: Tuple[str, ...]
    revealed_item: Optional[str]
    state: ItemState

    @property
    def has_active_item(self) -> Optional[bool]:
        if self.state in (ItemState.REMOVED, ItemState.CONSUMED):
            return False
        if self.state in (ItemState.KNOWN, ItemState.INFERRED) and self.revealed_item:
            return True
        return None  # unknown: cannot claim presence or absence


def public_item_belief(
    possible_items: Any,
    *,
    revealed_item: Any = None,
    state: Optional[ItemState] = None,
) -> PublicItemBelief:
    possible = _id_tuple(possible_items)
    revealed = _to_id(revealed_item) or None
    if state in (ItemState.REMOVED, ItemState.CONSUMED):
        return PublicItemBelief(possible, revealed, state)
    if revealed:
        return PublicItemBelief(possible, revealed, state or ItemState.KNOWN)
    return PublicItemBelief(possible, None, state or ItemState.UNKNOWN)


# --- Public speed belief ---------------------------------------------------


@dataclass(frozen=True)
class PublicSpeedBelief:
    """Public speed belief: a legal min/max range, exact only when public.

    The exact speed (from hidden EV/IV/nature/item) is never surfaced unless it
    is publicly inferable — e.g. from observed move order or an explicit public
    state — in which case the caller sets ``known_exact``.
    """

    possible_speed_min: int
    possible_speed_max: int
    known_exact: Optional[int]

    @property
    def is_exact(self) -> bool:
        return self.known_exact is not None


def speed_belief_range(possible_speed_min: int, possible_speed_max: int) -> PublicSpeedBelief:
    low = max(0, int(possible_speed_min))
    high = max(low, int(possible_speed_max))
    return PublicSpeedBelief(low, high, None)


def speed_belief_exact(value: int) -> PublicSpeedBelief:
    exact = max(0, int(value))
    return PublicSpeedBelief(exact, exact, exact)


# --- Effective ability context ---------------------------------------------


@dataclass(frozen=True)
class EffectiveAbilityContext:
    """Resolve a public ability belief into its *effective* mechanical state.

    Suppression/bypass flags must only be set ``True`` when that effect is itself
    *known active* (Neutralizing Gas / Gastro Acid on the field, a Mold
    Breaker-class attacker). Ability Shield blocks suppression and ignore.
    """

    belief: PublicAbilityBelief
    neutralizing_gas_known: bool = False
    gastro_acid_known: bool = False
    source_ignores_abilities_known: bool = False  # Mold Breaker / Teravolt / Turboblaze
    ability_shield_known: bool = False

    def resolve(self) -> EffectiveAbility:
        base = self.belief.effective_ability
        if self.ability_shield_known:
            return base
        suppressed = self.neutralizing_gas_known or self.gastro_acid_known
        ignored = self.source_ignores_abilities_known
        return EffectiveAbility(
            ability=base.ability,
            knownness=base.knownness,
            suppressed=suppressed,
            ignored=ignored,
        )


# --- Effective item context ------------------------------------------------


@dataclass(frozen=True)
class EffectiveItemContext:
    """Resolve whether a specific item effect is active for a held-item belief.

    Magic Room suppresses item effects globally (when known active)."""

    belief: PublicItemBelief
    magic_room_known: bool = False

    def item_effect_active(self, item_id: Any) -> Optional[bool]:
        target = _to_id(item_id)
        if self.magic_room_known:
            return False
        active = self.belief.has_active_item
        if active is None:
            return None  # unknown item: cannot claim the effect
        if not active:
            return False  # removed/consumed
        return _to_id(self.belief.revealed_item) == target


def item_blocks(context: EffectiveItemContext, blocking_item_id: Any) -> Dict[str, Any]:
    """Tri-state item-block decision. Fail closed when the item is unknown.

    Used for Heavy-Duty Boots (hazards), Safety Goggles (powder/weather chip),
    Covert Cloak (secondary effects), Ability Shield (ability suppression), etc.
    """
    active = context.item_effect_active(blocking_item_id)
    if active is None:
        return _unavailable("item_unknown", blocks=None)
    return _available(blocks=bool(active))


def item_belief_from_state(mon: Any) -> PublicItemBelief:
    """Build a `PublicItemBelief` from dict state with explicit knownness.

    No-leakage: an item is treated as known only when ``item_known`` is truthy.
    Removed/consumed map to those states; otherwise possible items may be listed
    but the held item stays unknown."""
    if not isinstance(mon, dict):
        return public_item_belief([])
    item = mon.get("item")
    if mon.get("item_removed"):
        return public_item_belief([], revealed_item=item, state=ItemState.REMOVED)
    if mon.get("item_consumed"):
        return public_item_belief([], revealed_item=item, state=ItemState.CONSUMED)
    if mon.get("item_known") and item:
        return public_item_belief([item], revealed_item=item, state=ItemState.KNOWN)
    return public_item_belief(mon.get("possible_items") or [])


# --- Effective weather context ---------------------------------------------


@dataclass(frozen=True)
class EffectiveWeatherContext:
    """Weather *exists* versus weather *effects active*.

    Cloud Nine / Air Lock negate weather effects, but only when that ability is
    itself known active."""

    weather: Optional[str]
    weather_negator_known: bool = False  # Cloud Nine / Air Lock known active

    @property
    def weather_effects_active(self) -> bool:
        return bool(_to_id(self.weather)) and not self.weather_negator_known

    def effective_weather(self) -> Optional[str]:
        if not self.weather_effects_active:
            return None
        return _to_id(self.weather) or None
