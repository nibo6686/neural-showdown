# Rollout-Parity Batch 6 — Delayed Landing Resolver Provenance

## Scope and result

Batch 6 implements the design-group-1 work from
`state_provenance_schema_design_for_remaining_gaps.md`: a landing-time
**resolver-bundle provenance path** for Future Sight / Doom Desire so that a
replacement occupant's exact landing damage can resolve only under complete,
occupant-matched provenance — never by reusing the original target's damage.

Deterministic harness after batch 6:

- 47 deterministic cases (was 45)
- **39 PASS** (was 37)
- **0 FAIL**
- **8 explicit GAP** (unchanged)

This is a narrow rollout/state-provenance implementation. No state schema was
migrated, no action schema changed, and `legal-action-v7` stays 552D /
`956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`.

## Exact delayed-landing resolver contract

A delayed attack landing resolves exact damage on the current slot occupant only
if one of the following holds for *that* occupant:

1. **`target_specific`** — `damage_by_target` carries damage keyed by the
   landing occupant identity, with `damage_provenance`.
2. **`resolver_exact`** — a complete landing-time resolver bundle is present,
   with all of:
   - `source_snapshot` (source identity/side),
   - `move_id`, `move_type`, `move_category`, `move_base_power`,
   - `target_snapshot` whose identity **matches the actual landing occupant**,
   - `field_snapshot` (weather/terrain/screens),
   - a Showdown/oracle-derived exact `landing_damage` with `damage_provenance`.

Otherwise the resolution fails closed:

- occupant absent from `damage_by_target` and no resolver bundle →
  `replacement_landing_damage_unavailable`;
- resolver bundle missing required inputs → `resolver_inputs_incomplete:<keys>`;
- resolver bundle built for a different occupant → `resolver_target_mismatch`;
- resolver inputs present but no exact `landing_damage` →
  `resolver_inputs_present_without_exact_landing_damage`.

The decision is centralized in
`provenance_contracts.delayed_landing_resolvable(attack, occupant_id)`, which
`delayed_damage.resolve_delayed_attacks` now calls. There is a single
landing-damage decision surface; the production queue cannot invent or reuse
damage outside it.

## Files changed

- `trainer/src/neural/provenance_contracts.py` — extended
  `delayed_landing_resolvable` with the `resolver_exact` /
  `resolver_inputs_present` / `resolver_target_mismatch` outcomes and a
  `_snapshot_identity` helper; the helper now also returns `provenance`.
- `trainer/src/neural/delayed_damage.py` — `schedule_delayed_attack` accepts a
  resolver bundle as an alternative to target-specific damage and stores
  `resolver_inputs`; `resolve_delayed_attacks` delegates the landing-damage
  decision to the helper and fails closed when no exact damage is derivable.
- `sim-core/src/rollout_parity_oracle.ts` — added a `delayedResolverInput`
  builder and two PASS fixtures
  (`future_sight_resolver_bundle_replacement`,
  `doom_desire_resolver_bundle_replacement`).
- `trainer/tests/test_state_provenance_no_leakage_contracts.py` — new
  `DelayedResolverBundleTest` (matching-occupant exact resolution, mismatch
  fail-closed, deferred-without-exact-damage, plus two integration tests against
  the production queue); updated one Batch A assertion for the centralized
  reason string.
- `trainer/tests/test_rollout_parity_harness.py` — locked the two new PASS
  fixtures and updated the centralized fail-closed reason string.
- `artifacts/training_plan/rollout_parity_harness_results.json` — regenerated
  (47 cases, 39/0/8).
- `artifacts/training_plan/rollout_parity_harness_report.md`,
  `artifacts/training_plan/state_provenance_schema_design_for_remaining_gaps.md`,
  `artifacts/training_plan/diagnostic_training_gate.md` — updated.

## Future Sight / Doom Desire GAP status

The two replacement-without-replacement-specific-damage cases
(`future_sight_replacement_damage_unavailable`,
`doom_desire_replacement_damage_unavailable`) **remain GAP**. They carry only the
original target's damage (`{machamp: ...}`) while the landing occupant is the
replacement (Blissey); reusing that number would be wrong, so they fail closed.
GAP count did not change.

The two new resolver-bundle fixtures move to PASS because they supply a complete
landing-time bundle built for the actual replacement occupant, with the
Showdown-derived exact replacement damage. So Future Sight / Doom Desire now PASS
under **both** accepted provenance forms, while the genuinely underdetermined
cases stay honest GAPs. 0 FAIL is preserved; no GAP was closed by weakening
correctness.

## No-leakage behavior

- **No stale reuse.** Original-target damage is never applied to a replacement.
  Verified by `resolver_target_mismatch` (helper + production queue) and by the
  unchanged `*_replacement_damage_unavailable` GAPs.
- **Occupant-matched only.** A resolver bundle resolves exact damage only when
  `target_snapshot` identity equals the landing occupant.
- **Oracle-derived exact damage stays fixture-only.** `landing_damage` is a
  Showdown-derived value carried in the oracle fixture / delayed queue; it is not
  flattened into any `legal-action-v7` or live/model-facing feature. v7 still
  carries only delayed-pressure intent (`risk_delayed_pressure_scheduled`,
  `risk_future_damage_deferred_to_rollout`).
- **Fail closed over wrong-exact.** A bundle with inputs but no exact
  `landing_damage` does not guess; it reports unavailable.

## Verification

- runtime preflight: `D:\Anaconda\envs\neuralgpu\python.exe`, Torch
  `2.5.1+cu121`, CUDA available `True`
- sim-core TypeScript build: PASS
- sim-core test suite: 35 PASS
- `test_state_provenance_no_leakage_contracts`: 28 PASS
- `test_rollout_parity_harness`: 17 PASS
- deterministic harness: 39 PASS / 0 FAIL / 8 GAP
- `python -m json.tool` on harness results: PASS
- `git diff --check`: clean (LF→CRLF warnings only)

## What did NOT change

No training, dataset materialization, checkpoint promotion, checkpoint file,
live default, live bot behavior, action/state schema, or `legal-action-v7`
fingerprint. No NatDex/old-gen mechanics. Both the rollout-parity and overall
diagnostic training gates remain **closed**.
