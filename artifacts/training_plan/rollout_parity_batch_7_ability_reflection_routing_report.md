# Rollout-Parity Batch 7 — Ability / Prevention / Reflection Routing

## Scope and result

Batch 7 implements design-group 2 (reflection routing) and group 3
(ability/status prevention routing) from
`state_provenance_schema_design_for_remaining_gaps.md`: narrow,
provenance-safe support for **Magic Bounce reflection** and **Good as Gold**
status-move blocking, gated on ability knownness/suppression and complete
routing provenance.

Deterministic harness after batch 7:

- 49 deterministic cases (was 47)
- **41 PASS** (was 39)
- **0 FAIL**
- **8 explicit GAP** (unchanged)

This is a focused rollout/provenance batch. No state schema was migrated, no
action schema changed, and `legal-action-v7` stays 552D /
`956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`. Scope stays
Gen 9 Random Battles.

## Exact ability/reflection routing contract

### Good as Gold (status-move block)

`resolve_status_move_ability_block(target, attacker, move)` returns a block only
when **all** hold:

- the move is a status move (`category == status`, or a status-condition move);
- the target effective ability is **KNOWN** and equals `goodasgold`;
- the ability is **not suppressed** (Gastro Acid / Core Enforcer / Neutralizing
  Gas) and **not ignored** by a Mold Breaker-class attacker.

Otherwise:

- not a status move, or candidate ability is not a *known* Good as Gold →
  returns `None` (caller falls through to other prevention logic, no behavior
  change);
- known-but-suppressed/ignored → returns a **non-blocking** result;
- **unknown/unrevealed** ability → never reaches a block here, because
  `effective_ability_from_state` only marks an ability `KNOWN` when
  `ability_known` is truthy and otherwise hides the raw identity. The
  unknown-ability scenario therefore stays an explicit fixture GAP, never a
  guess.

### Magic Bounce (reflection)

In `apply_immediate_prevention`, a move flagged `reflectable` against a
known-active Magic Bounce reflector is routed through
`validate_reflection_provenance`, which requires the original source, reflector,
destination side, reflected target, and side-effect payload, plus a known-active
reflector ability. On success it returns `available=True`, `reflected=True`,
`prevented=True`, and the `destination_side`. Any missing routing field, a
non-reflectable move, or a non-known/suppressed/ignored reflector ability →
fails closed (`available=False` → GAP). Reflection is modeled as a transition
event (source/target/destination/effect), not a simple no-op prevention.

### Knownness / suppression / bypass

`effective_ability_from_state(mon, attacker)` builds an `EffectiveAbility` with
explicit `knownness ∈ {known, inferred, unknown}`, `suppressed`, and `ignored`.
Rules enforced:

- unknown must **not** become "known not blocked" — an unrevealed ability has its
  identity hidden (`ability=None`) and never blocks/reflects;
- suppressed or ignored ability does not block/reflect;
- Mold Breaker-style bypass / suppression that is not represented in local state
  leaves the ability unknown-or-inactive, so resolution fails closed rather than
  exact-PASS.

## Files changed

- `trainer/src/neural/provenance_contracts.py` — added
  `effective_ability_from_state`, `_is_status_move`, and
  `resolve_status_move_ability_block`.
- `trainer/src/neural/prevention.py` — added the Magic Bounce reflection routing
  branch and the Good as Gold known-active status block; imports the new helpers.
- `trainer/src/neural/rollout_parity.py` — `_compare_immediate` now compares
  `reflected` and `blocked` alongside `prevented`.
- `sim-core/src/rollout_parity_oracle.ts` — added two supported fixtures
  (`good_as_gold_known_blocks_status`, `magic_bounce_reflects_stealth_rock`);
  kept `good_as_gold_status_gap` and `magic_bounce_reflection_gap` as the
  unknown/incomplete explicit-GAP representatives.
- `trainer/tests/test_state_provenance_no_leakage_contracts.py` — added
  `EffectiveAbilityProvenanceTest`, `GoodAsGoldResolverTest`, and
  `ImmediatePreventionAbilityReflectionTest` (43 tests total).
- `trainer/tests/test_rollout_parity_harness.py` — locked the two new PASS
  fixtures.
- `artifacts/training_plan/rollout_parity_harness_results.json` — regenerated
  (49 cases, 41/0/8).
- `artifacts/training_plan/rollout_parity_harness_report.md`,
  `artifacts/training_plan/state_provenance_schema_design_for_remaining_gaps.md`,
  `artifacts/training_plan/diagnostic_training_gate.md` — updated.

## Magic Bounce / Good as Gold GAP status

GAP count is **unchanged (8)**. Two new PASS fixtures cover the complete cases:

- `good_as_gold_known_blocks_status` — Gholdengo (Good as Gold, `ability_known`)
  blocks Amoonguss's Spore → PASS.
- `magic_bounce_reflects_stealth_rock` — Hatterene (Magic Bounce, `ability_known`)
  reflects Stealth Rock with complete routing → PASS.

The previously-GAP fixtures remain explicit GAP, representing the honest
under-determined cases:

- `good_as_gold_status_gap` — ability unrevealed/unknown in arbitrary rollout
  state.
- `magic_bounce_reflection_gap` — reflection routing provenance incomplete.

No GAP was closed by weakening correctness; 0 FAIL is preserved.

## No-leakage behavior verified

- **Unrevealed opponent ability is never surfaced as known.**
  `effective_ability_from_state` hides the identity unless `ability_known` is
  truthy; the unknown Good as Gold / Magic Bounce fixtures stay GAP.
- **Suppressed/ignored abilities do not block/reflect.**
- **Reflection payload stays transition data.** The reflected
  source/target/destination/effect live in rollout/transition provenance and are
  not flattened into any `legal-action-v7` or live/model-facing feature. No v7
  field changed.
- **Fail closed over wrong-exact.** Incomplete reflection routing returns
  unavailable; unknown ability does not become a block.

## Verification

- runtime preflight: `D:\Anaconda\envs\neuralgpu\python.exe`, Torch
  `2.5.1+cu121`, CUDA available `True`
- sim-core TypeScript build: PASS
- sim-core test suite: 35 PASS
- `test_state_provenance_no_leakage_contracts`: 43 PASS
- `test_rollout_parity_harness`: 17 PASS
- deterministic harness: 41 PASS / 0 FAIL / 8 GAP
- `python -m json.tool` on harness results: PASS
- `git diff --check`: clean (LF→CRLF warnings only)

## Remaining rollout GAPs

1. Future Sight replacement damage without target-specific landing damage.
2. Doom Desire replacement damage without target-specific landing damage.
3. Magic Bounce reflection with incomplete routing provenance.
4. Good as Gold blocking with an unrevealed/unknown ability.
5–8. Population Bomb / Triple Axel exact sequential-hit execution (4 fixtures) —
   design group 4 / batch E.

## What did NOT change

No training, dataset materialization, checkpoint promotion, checkpoint file,
live default, live bot behavior, action/state schema, or `legal-action-v7`
fingerprint. No NatDex/old-gen mechanics. Both the rollout-parity and overall
diagnostic training gates remain **closed**.
