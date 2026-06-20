# Deterministic Rollout-Parity Harness Report

## Scope and result

A deterministic oracle-vs-local transition harness compares targeted Gen 9
state transitions against the bundled Pokemon Showdown engine.

Result after rollout parity batch 5:

- 45 deterministic cases
- 37 PASS
- 0 FAIL
- 8 explicit GAP

`FAIL` means the local transition returned a supported result that disagreed
with Showdown. `GAP` means the local approximate rollout does not implement the
transition and says so explicitly. Gaps are not counted as parity.

No training, dataset materialization, checkpoint promotion, battle play, schema
change, fingerprint change, live-default change, or production-path change was
performed.

## Entrypoints

- Showdown oracle: `sim-core/src/rollout_parity_oracle.ts`
- local comparison/report CLI: `trainer/src/neural/rollout_parity.py`
- local entry-hazard transition: `trainer/src/neural/entry_hazards.py`
- local residual transition: `trainer/src/neural/end_of_turn.py`
- delayed-damage queue: `trainer/src/neural/delayed_damage.py`
- immediate prevention helper: `trainer/src/neural/prevention.py`
- regression tests: `trainer/tests/test_rollout_parity_harness.py`
- captured deterministic result:
  `artifacts/training_plan/rollout_parity_harness_results.json`

Run on this Windows project setup:

```powershell
cd sim-core
npm run build

cd ..
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
& $py -m neural.rollout_parity --output artifacts\training_plan\rollout_parity_harness_results.json
& $py -m unittest trainer.tests.test_rollout_parity_harness
```

## Phase boundary

The harness distinguishes:

- `immediate`: move resolution and deterministic prevention callbacks;
- `end_of_turn`: residual damage/healing;
- `switch_entry`: entry hazards and entry stat/status changes;
- `delayed_future`: scheduled Future Sight / Doom Desire effects;
- `sequential_multihit`: exact per-hit multi-hit execution fixtures.

Click-time `legal-action-v7` features are not treated as rollout transition
results. Batch 5 keeps that boundary and adds no v7 fields.

## Passing parity coverage

Switch/entry:

1. Stealth Rock uses Rock type effectiveness.
2. One layer of Spikes damages a grounded target by approximately one eighth.
3. Spikes does not damage a Flying target.
4. Toxic Spikes marks a grounded target for poison.
5. Sticky Web marks a grounded target for a Speed drop.
6. Heavy-Duty Boots prevents the tested hazard damage/status/stat effects.

Residual/end-of-turn:

7. Toxic increments stages 1->2->3.
8. Regular poison applies `floor(max HP / 8)`.
9. Burn applies `floor(max HP / 16)`.
10. Leech Seed damages from target max HP and heals the source by actual
    damage dealt.
11. Salt Cure applies `floor(max HP / 8)` to an ordinary target.
12. Salt Cure applies `floor(max HP / 4)` to Water.
13. Salt Cure applies `floor(max HP / 4)` to Steel.
14. Binding residual applies `floor(max HP / 8)` when source, duration, and
    divisor provenance are explicitly represented.
15. Binding Band residual applies `floor(max HP / 6)` when the Binding
    Band-derived divisor is explicitly represented.
16. Ordinary Sandstorm chip applies `floor(max HP / 16)` to non-immune targets.
17. Grassy Terrain heals a grounded damaged target by `floor(max HP / 16)`.
18. Grassy Terrain does not heal an airborne target.
19. A state with no residual effects remains unchanged.

Delayed damage:

20. Future Sight schedules without immediate damage and lands at the correct
    later turn.
21. Future Sight damages the replacement occupying the original target slot
    when target-specific landing damage is present.
22. A duplicate Future Sight fails without overwriting the pending event.
23. Doom Desire shares the same timing and slot mechanism.
24. Doom Desire damages the replacement occupying the original target slot
    when target-specific landing damage is present.

Immediate prevention:

25. Psychic Terrain blocks a positive-priority move into a grounded target.
26. Psychic Terrain does not block a non-priority move.
27. Psychic Terrain does not block a positive-priority move into an airborne
    target.
28. Psychic Terrain does not block Grassy Glide when Grassy Terrain is absent.
29. Substitute blocks Leech Seed when substitute-blocking provenance is present.
30. Misty Terrain blocks a status move into a grounded target.
31. Electric Terrain blocks sleep into a grounded target.
32. Damp blocks Explosion when the target ability is represented.
33. Powder blocks a Fire move when the attacker volatile and Fire typing are
    represented.
34. Sucker Punch succeeds when the target action branch is represented as an
    attack.
35. Sucker Punch fails when the target action branch is represented as status.
36. Thunderclap succeeds when the target action branch is represented as an
    attack.
37. Thunderclap fails when the target action branch is represented as status.

## Explicit parity gaps

The harness records Showdown outcomes but local transition availability is
false for:

- Future Sight replacement damage when target-specific landing damage is absent.
- Doom Desire replacement damage when target-specific landing damage is absent.
- Magic Bounce reflection.
- Good as Gold status-move blocking in arbitrary rollout states.
- Population Bomb exact sequential-hit execution.
- Population Bomb initial-miss stop-on-miss execution.
- Triple Axel exact power-ramp execution.
- Triple Axel initial-miss stop-on-miss execution.

The delayed queue stores move, scheduled/landing turns, source identity, target
side/slot, and damage provenance. It requires target-specific landing damage.
Showdown calculates against the current slot occupant at landing time, so
reusing original-target damage for a replacement remains an explicit GAP.

Binding is now PASS only for states carrying complete source/effect/duration
and divisor provenance. A bare `partiallytrapped` volatile still fails closed.

Magic Bounce remains a GAP because it is reflection, not a simple no-op
prevention. Correct rollout needs reflected action target, destination side,
and side-effect application provenance. Good as Gold remains a GAP because
arbitrary rollout states still need reliable active ability provenance,
ability suppression/ignoring state, and broader status-move callback routing.

Population Bomb and Triple Axel remain GAP because exact parity needs per-hit
accuracy branches, PRNG provenance, stop-on-miss execution, and per-hit damage
or base-power provenance. The v7 action features can summarize risk, but that
is not exact rollout execution.

## Focused fixes in batch 5

- Added binding residual support that fails closed unless source activity,
  source effect, remaining duration, and divisor provenance are present.
- Added Binding Band divisor coverage using explicit divisor provenance.
- Added Powder Fire-move prevention when the attacker volatile and Fire move
  type are represented.
- Added Sucker Punch and Thunderclap branch handling for explicit target
  attacking/status branches.
- Added Doom Desire replacement-target landing parity when target-specific
  damage is present.
- Added Showdown-backed sequential multi-hit fixtures and kept them explicit
  GAP where local exact execution state is missing.

## NatDex implications

This harness remains Gen 9 custom-game scoped. NatDex or older-generation
coverage must be added through explicit format-scoped fixtures for trapping
duration/modifier behavior, Powder availability/callback order, branch-move
rules, multi-hit accuracy semantics, ability callback lists, terrain behavior,
and Future Sight / Doom Desire timing. No NatDex or old-generation mechanics
were implemented in this batch.

## Verification

- runtime preflight: `D:\Anaconda\envs\neuralgpu\python.exe`, Torch
  `2.5.1+cu121`, CUDA available `True`
- sim-core TypeScript build: PASS
- sim-core test suite: 35 PASS
- focused rollout-parity Python tests: 17 PASS
- deterministic harness: 37 PASS / 0 FAIL / 8 GAP

## Gate decision

The rollout-parity and diagnostic training gates remain **closed**. More
inventory-driven edge cases now have deterministic PASS coverage, but exact
scheduled damage generation, reflection callbacks, broad ability callbacks,
per-hit execution, and broader provenance/adaptation remain incomplete.
