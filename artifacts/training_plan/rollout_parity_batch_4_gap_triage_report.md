# Rollout Parity Batch 4 - Remaining Gap Triage

## Result

The deterministic harness now has **33 fixtures: 29 PASS / 0 FAIL / 4 GAP**.

One previous GAP became PASS:

- Grassy Terrain healing now passes for a grounded damaged target.

An additional fixture verifies the paired no-op branch:

- Grassy Terrain does not heal an airborne Charizard target.

## Five-gap disposition

1. Binding residual: **still GAP**.

   Current state exposes only `partiallytrapped`. Exact Gen 9 residual damage
   also needs source activity, source effect identity, remaining duration, and
   Binding Band-derived divisor provenance. This belongs in future rollout
   execution/provenance work rather than a guessed residual.

2. Grassy Terrain healing: **PASS now**.

   The local residual state can safely represent terrain identity, integer
   HP/max HP, residual-modifier provenance, and grounding for the controlled
   fixtures. The helper heals grounded damaged Pokemon by `floor(max HP / 16)`
   and skips airborne targets. It fails closed if grounding cannot be
   reconstructed.

3. Future Sight replacement damage without target-specific landing damage:
   **still GAP**.

   The queue/timing/slot behavior is already PASS when target-specific landing
   damage is supplied. The remaining GAP intentionally refuses to reuse
   original-target damage for a replacement. General support needs landing-time
   source stats/state, target stats/types/ability/item, and field context, or a
   safe oracle call that receives all of that provenance.

4. Magic Bounce reflection: **still GAP**.

   Showdown reflects eligible moves, so this is not a simple prevented/no-op
   bit. Local rollout needs reflected action target, destination side, and
   side-effect application provenance. This belongs in future execution
   provenance work.

5. Good as Gold generalized status blocking: **still GAP**.

   The controlled oracle fixture shows the block, but arbitrary local rollout
   states do not yet guarantee reliable active ability provenance, ability
   suppression/ignoring state, or broad status-move callback routing. This
   belongs in future prevention/execution provenance work.

## Implementation

`trainer/src/neural/end_of_turn.py` now supports Grassy Terrain residual
healing in the focused Gen 9 singles residual kernel. Grounding is reconstructed
from represented types, ability, item, and volatiles. The helper returns
unavailable instead of guessing when grounding is missing.

`sim-core/src/rollout_parity_oracle.ts` adds deterministic Showdown-backed
Grassy Terrain fixtures for grounded healing and airborne no-heal behavior.

`trainer/tests/test_rollout_parity_harness.py` asserts the new PASS fixtures
and the fail-closed missing-grounding case.

## v7 batch 7 provenance candidates

The remaining gaps point to execution/provenance fields or adapter state rather
than action-feature scoring alone:

- partial-trapping source/effect/duration/item-modifier provenance;
- scheduled delayed-attack source snapshot and landing-time target/field damage
  resolver inputs;
- reflected-action target/destination side and side-effect provenance for Magic
  Bounce-style callbacks;
- reliable active ability provenance, suppression/ignoring state, and
  status-move callback routing for Good as Gold-style prevention;
- general grounding provenance for residual terrain effects outside controlled
  fixtures.

## NatDex

This batch is Gen 9 custom-game scoped. NatDex or older-generation coverage
needs explicit format-scoped fixtures for terrain residual availability/order,
Future Sight/Doom Desire semantics, trapping duration/modifier behavior, and
ability callback rules.

## Operations and gate

No materialization or training ran. No checkpoint was promoted. No schema,
fingerprint, live default, or production path changed. The rollout-parity and
diagnostic training gates remain **closed**.
