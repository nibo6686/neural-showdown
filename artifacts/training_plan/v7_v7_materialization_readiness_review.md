# v7/v7 Materialization Readiness Review

## Purpose

Decide whether the project is ready to **plan** a small v7/v7 diagnostic
materialization (state `live-private-belief-v7` + action `legal-action-v7`).
This is a docs/tests/gate review only. **Nothing was materialized, trained,
promoted, or changed in live defaults.**

## Readiness verdict

**Conditionally ready** for a small v7/v7 *diagnostic* materialization, but
**not runnable from the current materializer CLI yet**.

The schema is frozen and fingerprint-tested, mechanics fidelity is FAIL-free,
rollout parity is FAIL-free with only honest GAPs, the no-leakage contracts are
in place, and the generalized full-manifest path is
parallel/crash-safe/resumable with built-in validation. However,
`benchmark_vnext_featuregen.py` currently imports and exposes only
`legal-action-v5` / `legal-action-v6`; its CLI rejects `legal-action-v7`, and
its repeat-chain impact switch is currently enabled only for v6. Therefore the
remaining conditions are:

1. make the minimal materializer-only v7 wiring change and test it without
   materializing a dataset,
2. pass the pre-materialization test gate below,
3. obtain explicit user approval to materialize (hard constraint), and
4. produce a validation report while retaining intermediate shards.

Training, checkpoint promotion, and any live-default change remain **separately
blocked** regardless of this materialization.

## Current schema / dim / fingerprint

- Action: `legal-action-v7`, **552D**, ordered-name fingerprint
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`
  (asserted in `test_action_features_v7_forced_decision_secondary_chance.py`:
  `ACTION_FEATURE_DIM_V7 == 552` and `_FULL_FP` match).
- State: `live-private-belief-v7`, **3208D** (unchanged; same as the existing
  `diagnostic_300_v7_v6` dataset).
- v7 is append-only over frozen per-batch prefixes (v6 331D → batch-1 361D →
  … → batch-7 511D → batch-8 552D); each prefix fingerprint is preserved and
  tested.

## Rollout parity status

- 59 deterministic fixtures
- **51 PASS / 0 FAIL / 8 GAP**
- captured in `rollout_parity_harness_results.json`; `test_rollout_parity_harness`
  asserts `FAIL == 0`.

## Remaining GAPs — all honest under-determined cases (non-blocking)

| GAP fixtures | Why GAP | Blocking? |
| --- | --- | --- |
| `future_sight_replacement_damage_unavailable` | replacement target lacks target-specific landing damage; reusing original-target damage would be wrong-exact | No — resolver-bundle exact path PASSes when complete |
| `doom_desire_replacement_damage_unavailable` | same target-specific landing-damage limitation | No — resolver-bundle exact path PASSes when complete |
| `magic_bounce_reflection_gap` | reflected source/destination/target/effect routing is incomplete | No — complete routing path PASSes |
| `good_as_gold_status_gap` | target ability is unknown and must not be assumed | No — known-active path PASSes; guessing would leak |
| `population_bomb_sequential_hits_gap` | summary exists but no exact per-hit trace | No — complete trace path PASSes |
| `population_bomb_initial_miss_stops_gap` | summary cannot prove exact stop-on-miss execution | No — complete trace path PASSes |
| `triple_axel_power_ramp_gap` | summary cannot prove per-hit power/damage sequence | No — complete trace path PASSes |
| `triple_axel_initial_miss_stops_gap` | summary cannot prove stop-on-miss/power-ramp execution | No — complete trace path PASSes |

Each GAP has a provenance-safe exact PASS path when the required public/fixture
provenance is present; the GAP is the deliberate fail-closed branch. None is a
wrong-exact FAIL. **0 FAIL outranks reducing GAP count**, so these are acceptable
for a diagnostic materialization (they affect rollout-time exactness, not the
click-time `legal-action-v7` candidate vectors that get materialized).

## No FAIL / wrong-exact mechanics

- Gen 9 Randbats mechanics completeness audit: **138 PASS / 0 FAIL / 212 INEXACT**
  — zero wrong-exact (INEXACT carries `impact_unknown` + coarse next-state flags,
  by policy, never a wrong number).
- Source-driven Showdown edge-case inventory: 155 source files scanned.
- Rollout parity: 0 FAIL.

There are **no remaining known FAIL/wrong-exact mechanics**.

## No-leakage status (sufficient for materialization)

- Per-batch v7 prefix + ordered-name fingerprint assertions (schema can't drift
  silently).
- Checkpoint metadata validator rejects name/dim/fingerprint mismatch (for the
  training side, when that is later approved).
- Materialization builds an exact pre-action protocol prefix and stops before the
  current decision's Tera event; state is reconstructed from public protocol +
  legal own request only.
- Standalone no-leakage contracts (52 tests) + public-belief contracts (49 tests):
  delayed-landing no stale reuse, hidden sleep/confusion durations never
  surfaced, ability/item knownness tri-state (unrevealed never assumed), Mold
  Breaker / Neutralizing Gas / Cloud Nine / Ability Shield / Safety Goggles only
  applied when known active, and multi-hit summaries never treated as exact
  traces (oracle traces stay fixture-only).

This is sufficient for a diagnostic materialization. The seed-invariance /
future-prefix / hidden-opponent perturbation *integration* tests over the real
feature builder remain recommended before any *training* (see below), not before
a diagnostic materialization that only writes features + the existing label
extraction.

## Public-belief / effective-context status (sufficient for Gen 9 Randbats scope)

The public-information belief and effective-context contracts cover the Gen 9
Randbats-relevant knowns: possible abilities/items, speed ranges, revealed/
inferred public info, and known-active modifiers (Mold Breaker, Neutralizing
Gas, Cloud Nine/Air Lock, Ability Shield, Safety Goggles, Heavy-Duty Boots).
Covert Cloak / Shield Dust secondary blocking and several Cloud Nine weather
sub-effects are documented-deferred (no local secondary-effect phase); these are
rollout-exactness items, not blockers for click-time v7 candidate
materialization. NatDex/old-gen stays out of scope. Sufficient for the current
scope.

## Action-feature prefix/fingerprint guardrails (sufficient)

- 552D and the full fingerprint are asserted in the v7 tests.
- Every v7 batch test asserts its frozen prefix fingerprint and slice boundary.
- The materializer records `action_feature_version`, `action_feature_dim`, and
  `action_feature_names_sha256` into the dataset metadata and re-validates on
  assembly. Sufficient.

## Required pre-materialization tests and wiring gate

Run green immediately before any approved materialization:

1. The focused v7 action modules:
   `test_action_features_v7`,
   `test_action_features_v7_action_risk_probability`, and
   `test_action_features_v7_forced_decision_secondary_chance` — schema dim 552
   and full fingerprint `956da3d2…1bf39d7` assert.
2. `python -m unittest trainer.tests.test_rollout_parity_harness` — `FAIL == 0`.
3. `python -m unittest trainer.tests.test_state_provenance_no_leakage_contracts`
   and `trainer.tests.test_public_information_belief_contracts`.
4. `npm test` in `sim-core` (mechanics/impact path).
5. `python -m json.tool` on `rollout_parity_harness_results.json`.
6. Materializer tests proving that v7 is accepted end-to-end, produces 552D
   action rows with the exact fingerprint, retains the v6 repeat-chain impact
   behavior inherited by v7, validates assembled metadata/arrays, and leaves
   v5/v6 behavior unchanged.
7. A read-only invocation of `_validate_full_preflight` on the frozen
   `diagnostic_300_manifest.json`, confirming 300 battles, the 210/45/45 split,
   no overlap, all replay paths present, safe new output directory, and v7 schema
   compatibility. The materializer has **no `--validate-only` CLI flag**; do not
   claim otherwise.

The review verification covered 1–3 and 5. The current read-only v7 preflight
also passed all checks with manifest SHA-256
`3399bf06c268f3eeb6cfabc8b6b102bde8a77e100f3e06c2ecc2f11a69d98185`;
rerun it after the materializer wiring change. Item 6 remains the technical
blocker before approval to materialize.

## Proposed materialization plan (DO NOT RUN — approval-gated)

After the materializer blocker above is fixed and approved, the smallest
meaningful step is a **`diagnostic_300` v7/v7** dataset that mirrors the
existing `diagnostic_300_v7_v6` but swaps the action schema v6→v7 (the v7 action
vector is append-only over the same frozen 331D v6 prefix, so this is a strictly
richer drop-in on the same mechanics-clean impact path and the same frozen
manifest/splits).

- Manifest (reuse, frozen): `artifacts/training_plan/manifests/diagnostic_300_manifest.json`
  (`diagnostic-300-manifest-v1`, seed `20260619`, 210/45/45).
- Entrypoint after minimal v7 wiring:
  `trainer/src/neural/benchmark_vnext_featuregen.py` (parallel, crash-safe,
  resumable via per-battle `_shards/`, validates on assembly).
- New output dir (no overwrite): `artifacts/training_plan/datasets/diagnostic_300_v7_v7/`.
- Proposed command after that wiring is tested (illustrative; **not executed**):

  ```powershell
  $py = 'D:\Anaconda\envs\neuralgpu\python.exe'
  $env:PYTHONPATH = (Resolve-Path .\trainer\src)
  $env:NEURAL_SIM_CORE_CWD = (Resolve-Path .\sim-core)
  $serverJs = (Resolve-Path .\sim-core\dist\src\server.js).Path
  $env:NEURAL_SIM_CORE_COMMAND_JSON = ConvertTo-Json @('node', $serverJs) -Compress
  & $py -m neural.benchmark_vnext_featuregen `
      --full-manifest `
      --manifest artifacts\training_plan\manifests\diagnostic_300_manifest.json `
      --output-dir artifacts\training_plan\datasets\diagnostic_300_v7_v7 `
      --action-feature-version legal-action-v7 `
      --workers 6
  ```

The current checkout rejects this command because v7 is not yet an allowed
materializer action version. Omitting `--full-manifest` would incorrectly run
the tiny benchmark path rather than the 300-battle materialization.

Plan requirements:

- **Visible progress**: per-battle shard logging (already emitted:
  `already_sharded=… pending=… workers=…`).
- **Resumability**: per-battle sha1 shards; re-run resumes; missing shard raises
  rather than silently truncating.
- **Validation report**: emit a `diagnostic_300_v7_v7_materialization_report.md`
  proving schema/fingerprint (v7 state 3208D + v7 action 552D `956da3d2…`),
  210/45/45 split with no split crossing, battle/state/candidate counts, action
  match rate, exact-vs-INEXACT candidate share, Tera/switch counts, and no
  stale-checkpoint reuse — mirroring the v7/v6 report.
- **No deletion** of intermediate shards or the prior `diagnostic_300_v7_v6`
  dataset unless separately approved.
- Stage nothing generated (datasets/shards/logs stay unstaged per repo policy).

## Explicitly blocked (regardless of this review)

- **No training** of any kind.
- **No checkpoint promotion** and no production/live use of any checkpoint.
- **No live-default change** — state stays `live-private-belief-v2`, action stays
  `legal-action-v3`; vNext stays diagnostic/shadow only.
- **No materialization** until explicitly approved.
- **No materialization** until the v7 materializer wiring/tests and read-only
  preflight pass.
- **No `legal-action-v7` schema change** (stays 552D / `956da3d2…`).
- **No NatDex/old-gen** mechanics.

## Gate status

Both the rollout-parity and overall diagnostic training gates remain **closed**.
This review changes no schema, dataset, checkpoint, or live default.
