# Deterministic Rollout-Parity Harness Report

## Scope and result

A small deterministic oracle-vs-local transition harness compares targeted state
transitions against the bundled Pokemon Showdown engine.

Result after remaining-gap triage batch 4:

- 33 deterministic cases
- 29 PASS
- 0 FAIL
- 4 explicit GAP

`FAIL` means the local transition returned a supported result that disagreed
with Showdown. `GAP` means the local approximate rollout does not implement the
transition and says so explicitly. Gaps are not counted as parity.

No training, dataset materialization, checkpoint promotion, battle play, schema
change, fingerprint change, live-default change, or production-path change was
performed.

## Entrypoints

- Showdown oracle: `sim-core/src/rollout_parity_oracle.ts`
- local comparison/report CLI: `trainer/src/neural/rollout_parity.py`
- dependency-free local entry-hazard transition:
  `trainer/src/neural/entry_hazards.py`
- dependency-free local residual transition:
  `trainer/src/neural/end_of_turn.py`
- dependency-free delayed-damage queue:
  `trainer/src/neural/delayed_damage.py`
- dependency-free immediate prevention helper:
  `trainer/src/neural/prevention.py`
- regression tests: `trainer/tests/test_rollout_parity_harness.py`
- captured deterministic result:
  `artifacts/training_plan/rollout_parity_harness_results.json`

Run:

```powershell
cd sim-core
npm run build

cd ..\trainer
$env:PYTHONPATH = "src"
python -m neural.rollout_parity --output ..\artifacts\training_plan\rollout_parity_harness_results.json
python -m unittest tests.test_rollout_parity_harness -v
```

The harness fixture record includes the starting state, chosen actions,
Showdown outcome, local outcome or explicit unavailability reason, phase, and
field-level diff.

## Oracle

The oracle is the project-bundled `pokemon-showdown` `Battle` implementation,
running `gen9customgame` with fixed four-word PRNG seeds and explicit packed
teams. It does not use replay labels, replay-future information, or hidden
future state. Integer HP rounding is tolerated only when comparing local
fractional hazard formulas with Showdown's integer HP events.

## Phase boundary

The harness distinguishes:

- `immediate`: move resolution and prevention callbacks;
- `end_of_turn`: residual damage/healing;
- `switch_entry`: entry hazards and entry stat/status changes;
- `delayed_future`: scheduled effects such as Future Sight.

Click-time `legal-action-v7` features are not treated as rollout transition
results. Batch 4 keeps that boundary: Grassy Terrain healing is end-of-turn
transition behavior, not a new action field.

## Passing parity cases

Switch/entry:

1. Stealth Rock uses Rock type effectiveness.
2. One layer of Spikes damages a grounded target by approximately one eighth.
3. Spikes does not damage a Flying target.
4. Toxic Spikes marks a grounded target for poison.
5. Sticky Web marks a grounded target for a Speed drop.
6. Heavy-Duty Boots prevents the tested hazard damage/status/stat effects.

Residual/end-of-turn:

7. Toxic increments stages 1->2->3 and applies `floor(max HP / 16) * stage`.
8. Regular poison applies `floor(max HP / 8)`.
9. Burn applies `floor(max HP / 16)`.
10. Leech Seed damages from target max HP and heals the source by actual
    damage dealt, capped by source missing HP.
11. Salt Cure applies `floor(max HP / 8)` to an ordinary target.
12. Salt Cure applies `floor(max HP / 4)` to Water.
13. Salt Cure applies `floor(max HP / 4)` to Steel.
14. Ordinary Sandstorm chip applies `floor(max HP / 16)` to the two
    non-immune fixture targets.
15. Grassy Terrain heals a grounded damaged target by `floor(max HP / 16)`.
16. Grassy Terrain does not heal an airborne target.
17. A state with no residual effects remains unchanged.

Delayed damage:

18. Future Sight schedules without immediate damage and lands at the end of
    the correct later turn.
19. Future Sight damages the replacement occupying the original target slot
    when target-specific landing damage is present.
20. A duplicate Future Sight fails without overwriting the pending event.
21. Doom Desire shares the same timing and slot mechanism.

Immediate prevention:

22. Psychic Terrain blocks a positive-priority move into a grounded target.
23. Psychic Terrain does not block a non-priority move.
24. Psychic Terrain does not block a positive-priority move into an airborne
    target when the target's airborne state is represented.
25. Psychic Terrain does not block Grassy Glide in the fixture where Grassy
    Terrain is absent and the move is not priority.
26. Substitute blocks Leech Seed when the target substitute and move's
    substitute-blocking provenance are represented.
27. Misty Terrain blocks a status move into a grounded target.
28. Electric Terrain blocks sleep into a grounded target.
29. Damp blocks Explosion when the target ability is represented.

## Explicit parity gaps

The harness records Showdown outcomes but local transition availability is
false for:

- Binding/partial trapping.
- Future Sight replacement damage when exact landing-damage provenance for the
  new slot occupant is absent.
- Magic Bounce reflection.
- Good as Gold status-move blocking in arbitrary rollout states.

Binding remains a GAP because the current tactical state exposes only
`partiallytrapped`; exact execution also needs source activity, source effect,
remaining duration, and the Binding Band-derived divisor.

The delayed queue stores move, scheduled/landing turns, source identity, target
side/slot, and damage provenance. It requires target-specific landing damage.
Showdown calculates against the current slot occupant at landing time, so
reusing damage calculated for the original target would be wrong. Current
approximate state does not yet provide a general delayed-damage resolver with
the source's required stats/state, the replacement's exact stats/types, and
landing-time field/ability/item context.

Magic Bounce remains a GAP because it is reflection, not a simple no-op
prevention. Correct rollout needs reflected action target/side-condition
provenance and side-effect application. Good as Gold is kept as a GAP outside
the controlled fixture because arbitrary rollout states do not yet guarantee
ability provenance and broad status-move callback routing.

The residual helper fails closed when integer HP/max HP, toxic stage,
residual-modifier provenance, or Grassy Terrain grounding is missing. The
prevention helper fails closed when priority, target grounding, move status
kind, substitute-blocking provenance, or represented ability state is missing.

## Focused fixes

Batch 4 adds Grassy Terrain residual healing to `trainer/src/neural/end_of_turn.py`.
It supports only states where terrain, exact HP/max HP, residual provenance, and
grounding can be reconstructed from represented types, ability, item, and
volatiles. It also verifies the airborne no-heal branch.

No action schema, v7 field, fingerprint, live default, materialized dataset, or
checkpoint changed.

## NatDex implications

The harness uses explicit teams, actions, phase labels, and a Showdown-backed
oracle rather than replay-specific Gen 9 labels, so additional format-scoped
fixtures can reuse the same comparison contract. NatDex support is not
implemented here.

The current terrain, prevention, residual, and delayed-damage fixtures are Gen
9-scoped. National Dex or older-generation support must use explicit
format-scoped fixtures for terrain availability, residual order, priority,
ability lists, callback ordering, and Future Sight/Doom Desire semantics.

## Verification

- sim-core TypeScript build: PASS
- sim-core test suite: 35 PASS
- focused rollout-parity Python tests: 15 PASS
- deterministic harness: 29 PASS / 0 FAIL / 4 GAP
- `git diff --check`: PASS

## Gate decision

The rollout-parity and diagnostic training gates remain **closed**. Core
isolated Gen 9 entry hazards, residual arithmetic, Grassy Terrain healing,
delayed queue timing/slot semantics, and selected prevention callbacks now have
parity coverage, but general landing-damage generation, state
adaptation/provenance, binding, reflection callbacks, broad ability callbacks,
and broader switch sequencing remain incomplete.
