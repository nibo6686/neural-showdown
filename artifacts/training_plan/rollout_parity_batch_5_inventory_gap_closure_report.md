# Rollout Parity Batch 5 - Inventory-Driven Gap Closure

## Result

The deterministic harness now has **45 fixtures: 37 PASS / 0 FAIL / 8 GAP**.

Batch 5 used the source-driven Showdown mechanics inventory to add fixtures for
the top rollout-relevant edge cases and implemented only the cases whose local
state could represent the required provenance safely.

## Inventory targets resolved to PASS

- Binding residual is PASS when source side, source activity, source effect,
  remaining duration, and divisor provenance are present.
- Binding Band partial-trap residual is PASS when the Binding Band divisor is
  represented explicitly.
- Powder Fire-move prevention is PASS when the attacker has the Powder volatile
  and the move type is represented as Fire.
- Sucker Punch succeeds/fails correctly when the target action branch is
  explicitly represented as attacking or status.
- Thunderclap succeeds/fails correctly under the same explicit branch
  representation.
- Doom Desire replacement-target landing damage is PASS when target-specific
  landing damage for the replacement is provided.
- Future Sight replacement-target landing damage remains PASS under the same
  target-specific provenance contract from the prior batch.

## Remaining explicit GAP

- Future Sight replacement damage without target-specific damage remains GAP.
  Missing state: landing-time source stats/state, replacement target
  stats/types/ability/item, and field context or a safe oracle/local damage
  resolver input bundle. The helper refuses to reuse original-target damage.
- Doom Desire replacement damage without target-specific damage remains GAP for
  the same reason.
- Magic Bounce reflection remains GAP. Missing provenance: reflected action
  target, destination side, reflected side-effect application, and callback
  ownership.
- Good as Gold generalized blocking remains GAP. Missing provenance: reliable
  active ability, suppression/ignoring state, and broad status-move callback
  routing for arbitrary rollout states.
- Population Bomb exact sequential execution remains GAP. Missing provenance:
  per-hit accuracy branch/PRNG state, stop-on-miss execution, and per-hit damage
  trace.
- Triple Axel exact sequential execution remains GAP. Missing provenance:
  per-hit accuracy branch/PRNG state, stop-on-miss execution, per-hit
  base-power ramp, and per-hit damage trace.

## Tiny fixes made

- `trainer/src/neural/end_of_turn.py` now applies partial-trap residual only
  when complete source/effect/duration/divisor provenance is present. Bare
  `partiallytrapped` still fails closed.
- `trainer/src/neural/prevention.py` now handles Powder Fire-move prevention
  and branch-dependent Sucker Punch / Thunderclap prevention when the opponent
  action branch is explicit.
- `sim-core/src/rollout_parity_oracle.ts` adds deterministic Showdown fixtures
  for binding, Binding Band, Powder, Sucker Punch, Thunderclap, Doom Desire
  replacement landing, and sequential multi-hit cases.

## Future provenance work

The remaining gaps should become execution/provenance work rather than action
schema guesses:

- delayed-attack damage resolver inputs at landing time;
- reflected-action target/destination/effect provenance;
- generalized active ability and ability-suppression provenance;
- arbitrary status-move callback routing;
- per-hit PRNG/accuracy/damage traces for sequential multi-hit moves.

## NatDex and old-gen notes

No NatDex or old-generation mechanics were implemented. Future format-scoped
work should add separate fixtures for partial-trap duration/modifier behavior,
Powder availability and callback ordering, branch-move rules, multi-hit
accuracy semantics, ability callback lists, terrain behavior, and delayed
attack timing.

## Operations and gate

No materialization or training ran. No checkpoint was promoted. No schema,
fingerprint, live default, or live bot behavior changed. The rollout-parity and
diagnostic training gates remain **closed**.
