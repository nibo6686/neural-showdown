# Deterministic Rollout-Parity Harness Report

## Scope and result

A deterministic oracle-vs-local transition harness compares targeted Gen 9
state transitions against the bundled Pokemon Showdown engine.

Result after effective-context known-modifier wiring (batch 8):

- 52 deterministic cases
- 44 PASS
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
results. Batch 8 keeps that boundary and adds no v7 fields.

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
22. Future Sight damages the replacement occupying the original target slot
    when a complete landing-time resolver bundle (built for that occupant, with
    Showdown-derived exact landing damage) is present.
23. A duplicate Future Sight fails without overwriting the pending event.
24. Doom Desire shares the same timing and slot mechanism.
25. Doom Desire damages the replacement occupying the original target slot
    when target-specific landing damage is present.
26. Doom Desire damages the replacement occupying the original target slot
    when a complete landing-time resolver bundle is present.

Immediate prevention:

27. Psychic Terrain blocks a positive-priority move into a grounded target.
28. Psychic Terrain does not block a non-priority move.
29. Psychic Terrain does not block a positive-priority move into an airborne
    target.
30. Psychic Terrain does not block Grassy Glide when Grassy Terrain is absent.
31. Substitute blocks Leech Seed when substitute-blocking provenance is present.
32. Misty Terrain blocks a status move into a grounded target.
33. Electric Terrain blocks sleep into a grounded target.
34. Damp blocks Explosion when the target ability is represented.
35. Powder blocks a Fire move when the attacker volatile and Fire typing are
    represented.
36. Sucker Punch succeeds when the target action branch is represented as an
    attack.
37. Sucker Punch fails when the target action branch is represented as status.
38. Thunderclap succeeds when the target action branch is represented as an
    attack.
39. Thunderclap fails when the target action branch is represented as status.
40. Good as Gold blocks a status move when the target ability is known-active
    Good as Gold.
41. Magic Bounce reflects a reflectable move when the reflector ability is a
    known-active Magic Bounce and the reflection routing provenance (original
    source, reflector, destination side, reflected target, side-effect payload)
    is complete.
42. A known Mold Breaker-class attacker bypasses a known Good as Gold, so the
    status move lands.
43. A known Ability Shield on the Good as Gold holder protects it from the Mold
    Breaker bypass, so the status move is still blocked.
44. A known Safety Goggles blocks a powder-flagged move.

## Explicit parity gaps

The harness records Showdown outcomes but local transition availability is
false for:

- Future Sight replacement damage when target-specific landing damage is absent.
- Doom Desire replacement damage when target-specific landing damage is absent.
- Magic Bounce reflection when the reflection routing provenance is incomplete
  or the reflector ability is not a known-active Magic Bounce.
- Good as Gold status-move blocking when the target ability is unrevealed/unknown
  in the rollout state.
- Population Bomb exact sequential-hit execution.
- Population Bomb initial-miss stop-on-miss execution.
- Triple Axel exact power-ramp execution.
- Triple Axel initial-miss stop-on-miss execution.

The delayed queue stores move, scheduled/landing turns, source identity, target
side/slot, and damage provenance. As of batch 6 it resolves replacement-target
landing damage from either (a) target-specific damage keyed by the landing
occupant, or (b) a complete landing-time resolver bundle whose `target_snapshot`
identity matches the occupant and that carries a Showdown-derived exact
`landing_damage` with provenance. Showdown calculates against the current slot
occupant at landing time, so the two `*_replacement_damage_unavailable` cases —
which carry only the original target's damage — remain explicit GAP, and a
resolver bundle built for a different occupant fails closed
(`resolver_target_mismatch`). Original-target damage is never reused for a
replacement.

Binding is now PASS only for states carrying complete source/effect/duration
and divisor provenance. A bare `partiallytrapped` volatile still fails closed.

Magic Bounce now PASSes when the reflector ability is a known-active Magic
Bounce and the reflection routing provenance (original source, reflector,
destination side, reflected target, side-effect payload) is complete; it routes
through `validate_reflection_provenance` and fails closed when any of those are
missing, so the incomplete fixture remains an explicit GAP. Good as Gold now
PASSes when the target ability is known-active Good as Gold and the move is a
status move; a known-but-suppressed/ignored Good as Gold does not block, and an
unrevealed/unknown ability is never assumed (so the unknown-ability fixture
remains an explicit GAP rather than a guess that would risk a wrong-exact).

Population Bomb and Triple Axel remain GAP because exact parity needs per-hit
accuracy branches, PRNG provenance, stop-on-miss execution, and per-hit damage
or base-power provenance. The v7 action features can summarize risk, but that
is not exact rollout execution.

## Focused fixes in batch 8 (effective-context known modifiers)

- Added a known Mold Breaker / Teravolt / Turboblaze bypass of the breakable Good
  as Gold (`source_ignores_target_abilities`), with a known Ability Shield on the
  holder protecting it — verified against bundled Showdown `sim/battle.ts`
  `suppressingAbility` (bypass requires `!target.hasItem('Ability Shield')`).
- Added a Safety Goggles powder-move block in `apply_immediate_prevention`
  (`item_belief_from_state` + `item_blocks`), gated on a *known* item; an unknown
  item is never assumed to be Safety Goggles and does not block.
- Already represented and unchanged: Heavy-Duty Boots hazard prevention
  (`heavy_duty_boots_prevents_hazards` PASS) and Safety Goggles weather chip
  immunity (sandstorm immune-set in `end_of_turn`).
- Deferred (documented, not wired here): Cloud Nine / Air Lock weather
  suppression in residuals, Neutralizing Gas harness coverage, and Covert Cloak /
  Shield Dust secondary-effect blocking — covered at the belief-contract unit
  level; harness wiring needs a clean oracle setup or secondary-effect routing
  not yet represented.

## Focused fixes in batch 7

- Added a known-active Good as Gold status-move block in
  `apply_immediate_prevention`, routed through ability knownness/suppression
  provenance (`effective_ability_from_state` +
  `resolve_status_move_ability_block`). It blocks only when the target ability is
  known-active Good as Gold; suppressed/ignored does not block; unknown/unrevealed
  is never assumed.
- Added Magic Bounce reflection routing: a reflectable move against a known-active
  Magic Bounce reflector is validated by `validate_reflection_provenance` and
  resolves with `reflected=True` and a destination side; incomplete routing fails
  closed (GAP).
- Extended the immediate comparison to check `reflected` and `blocked` alongside
  `prevented`.
- Added two PASS fixtures (`good_as_gold_known_blocks_status`,
  `magic_bounce_reflects_stealth_rock`) and kept the unknown/incomplete
  `good_as_gold_status_gap` and `magic_bounce_reflection_gap` as explicit GAP.
- Powder, Sucker Punch, and Thunderclap branch handling from batch 5 still PASS.

### Prior batch 6 fixes

- Added a landing-time resolver-bundle provenance path so Future Sight and Doom
  Desire can resolve replacement-target damage when a complete bundle (source
  snapshot, move identity/type/category/base power, occupant-matched
  `target_snapshot`, field snapshot, and a Showdown-derived exact
  `landing_damage` with provenance) is present.
- Centralized the landing-damage decision in
  `provenance_contracts.delayed_landing_resolvable`, which never reuses
  original-target damage and rejects a bundle built for a different occupant
  with `resolver_target_mismatch`.
- Allowed `schedule_delayed_attack` to schedule from either target-specific
  damage or a resolver bundle; resolution still fails closed when a bundle has
  inputs but no exact `landing_damage`.
- Added two Showdown-backed resolver-bundle replacement fixtures
  (`future_sight_resolver_bundle_replacement`,
  `doom_desire_resolver_bundle_replacement`) as PASS and kept the two
  `*_replacement_damage_unavailable` cases explicit GAP.

### Prior batch 5 fixes

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
- state-provenance no-leakage contract tests: 43 PASS
- public-information belief / effective-context tests: 36 PASS
- deterministic harness: 44 PASS / 0 FAIL / 8 GAP

## Gate decision

The rollout-parity and diagnostic training gates remain **closed**. More
inventory-driven edge cases now have deterministic PASS coverage, but exact
scheduled damage generation, reflection callbacks, broad ability callbacks,
per-hit execution, and broader provenance/adaptation remain incomplete.
