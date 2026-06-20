# Rollout Parity Batch 1 — Residuals

## Result

The deterministic harness moved from **6 PASS / 0 FAIL / 12 GAP** across 18
fixtures to **15 PASS / 0 FAIL / 7 GAP** across 22 fixtures.

New PASS cases:

- Toxic stages 1, 2, and 3 over three turns.
- Regular poison.
- Burn.
- Leech Seed target damage and source healing.
- Salt Cure against ordinary, Water, and Steel targets.
- Ordinary Sandstorm chip.
- No-residual state unchanged.

Binding remains an explicit GAP.

## Implementation

`trainer/src/neural/end_of_turn.py` is a focused, dependency-free Gen 9 singles
transition kernel. It accepts explicit combatants with integer HP/max HP,
status, types, item, ability, volatile details, and modifier provenance.

Supported order:

1. weather field residual;
2. Leech Seed, residual order 8;
3. burn/poison/toxic, residual order 9;
4. Salt Cure, residual order 13.

The transition uses Showdown-style integer floors, caps healing at max HP,
floors HP at zero, and skips later effects after a faint. Toxic stage is
incremented before its damage.

## Fail-closed boundaries

The helper returns unavailable instead of claiming parity when it lacks:

- integer HP and true max HP;
- explicit Toxic stage;
- known relevant ability/item modifier provenance;
- Leech Seed source side;
- partial-trap source activity, source effect, duration, or bound divisor.

Modifier-sensitive variants such as Magic Guard, Poison Heal, Heatproof,
Liquid Ooze, Big Root, and Binding Band are not guessed.

The controlled Salt Cure fixtures supply the active `saltcure` volatile
directly. The current tactical snapshot does not yet retain Salt Cure as a
dedicated active residual effect, so wiring the kernel into arbitrary live
states still needs that state field. Public opponent HP may also be reported on
a percentage scale rather than with true max HP, which is insufficient for
integer-rounding parity.

## Architecture boundary

This batch changes rollout transition behavior only. It does not add residual
HP predictions to `legal-action-v7`, change any schema/fingerprint, or alter
live defaults.

## NatDex

The helper is explicitly Gen 9-scoped. NatDex or older-generation fixtures must
select their generation because burn, poison, trapping, weather, and residual
ordering/divisors can differ. No NatDex-specific mechanic was implemented.

## Operations

No dataset was materialized. No training ran. No checkpoint was promoted. No
live/default path changed. The rollout-parity and diagnostic training gates
remain **closed**.
