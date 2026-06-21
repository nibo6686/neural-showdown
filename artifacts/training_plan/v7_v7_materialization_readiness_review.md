# v7/v7 Materialization Readiness Review

## Purpose

Decide whether the project is ready to **plan** a small v7/v7 diagnostic
materialization (state `live-private-belief-v7` + action `legal-action-v7`).
This is a docs/tests/gate review only. **Nothing was materialized, trained,
promoted, or changed in live defaults.**

## Readiness verdict

**Ready for an explicitly approved small v7/v7 diagnostic materialization.**

The schema is frozen and fingerprint-tested, mechanics fidelity is FAIL-free,
rollout parity is FAIL-free with only honest GAPs, the no-leakage contracts are
in place, and the generalized full-manifest path is
parallel/crash-safe/resumable with built-in validation. The materializer CLI now
accepts `legal-action-v7`, records and validates its 552D schema and exact
ordered-name fingerprint, and enables the same repeat-chain impact path for v7
that remains enabled for v6. The remaining conditions are procedural:

1. pass the pre-materialization test gate immediately before the run,
2. obtain explicit user approval to materialize (hard constraint), and
3. produce a validation report while retaining intermediate shards.

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
- Standalone no-leakage contracts + public-belief contracts:
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
Randbats-relevant knowns: exact own-side request facts; reliable
species/format-singleton ability inference (Gholdengo → Good as Gold);
ambiguous ability/item possibility sets; Illusion identity uncertainty; speed
ranges versus public exact speed; revealed/inferred public info; and known-active
modifiers (Mold Breaker, Neutralizing Gas, Cloud Nine/Air Lock, Ability Shield,
Safety Goggles, Heavy-Duty Boots). Item evidence remains conservative: explicit
reveals are known, deterministic deductions may be inferred, and one failed
probabilistic flinch does not infer Covert Cloak.
Covert Cloak / Shield Dust secondary blocking and several Cloud Nine weather
sub-effects are documented-deferred (no local secondary-effect phase); these are
rollout-exactness items, not blockers for click-time v7 candidate
materialization. NatDex/old-gen stays out of scope. Sufficient for the current
scope.

This calibration does not change the readiness verdict: the project remains
ready for an explicitly approved small diagnostic materialization, subject to
the same fresh test/preflight gate. Full Illusion-aware live extraction remains
a separately approved integration task; the pure contract already prevents
species-derived collapse when identity uncertainty is marked.

The possible mechanic-threat awareness audit
(`possible_mechanic_threat_awareness_audit.md`) further qualifies this verdict:
v7 is **partially possible-threat-aware**, not complete. Setup/stat deltas,
current boosts, species identity, and action classes make Unaware-like
interactions indirectly learnable; type-absorb abilities already have an
explicit known-or-possible action-risk field. Possible Unaware, Magic Bounce,
Good as Gold, Levitate, Covert Cloak, Shield Dust, and Inner Focus are not
consistently surfaced as action-conditioned possibility flags. Some batch-8
fields named `*_possible` currently require a concrete known target
ability/item.

This does not block the small diagnostic baseline because no wrong-exact claim
is made and exact rollout remains fail-closed. The dataset/report must not be
described as comprehensively threat-aware. A future append-only
`legal-action-v8` possible-threat slice is recommended before durable
threat-aware training; if the next dataset is intended as that durable training
schema rather than a diagnostic baseline, delay it until v8 is designed and
frozen.

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

The materializer wiring verification covers item 6 without writing a real
dataset: CLI dispatch is mocked, metadata/array validation is in memory, and the
existing assembly smoke uses only a temporary directory. The read-only v7 preflight
also passed all checks with manifest SHA-256
`3399bf06c268f3eeb6cfabc8b6b102bde8a77e100f3e06c2ecc2f11a69d98185`;
rerun it immediately before any approved materialization.

## Proposed materialization plan (DO NOT RUN — approval-gated)

After explicit approval, the smallest meaningful step is a **`diagnostic_300`
v7/v7** dataset that mirrors the
existing `diagnostic_300_v7_v6` but swaps the action schema v6→v7 (the v7 action
vector is append-only over the same frozen 331D v6 prefix, so this is a strictly
richer drop-in on the same mechanics-clean impact path and the same frozen
manifest/splits).

- Manifest (reuse, frozen): `artifacts/training_plan/manifests/diagnostic_300_manifest.json`
  (`diagnostic-300-manifest-v1`, seed `20260619`, 210/45/45).
- Entrypoint:
  `trainer/src/neural/benchmark_vnext_featuregen.py` (parallel, crash-safe,
  resumable via per-battle `_shards/`, validates on assembly).
- New output dir (no overwrite): `artifacts/training_plan/datasets/diagnostic_300_v7_v7/`.
- Proposed command (illustrative; **not executed**):

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

The current checkout accepts the v7 action version. Omitting `--full-manifest`
would incorrectly run the tiny benchmark path rather than the 300-battle
materialization.

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
- **No materialization** until the required tests and read-only preflight pass
  immediately before the approved run.
- **No `legal-action-v7` schema change** (stays 552D / `956da3d2…`).
- **No NatDex/old-gen** mechanics.

## Gate status

Both the rollout-parity and overall diagnostic training gates remain **closed**.
This review changes no schema, dataset, checkpoint, or live default.

## Post-materialization dataset-quality update

The approved materialization completed successfully, but the subsequent
read-only quality audit changes readiness for the next step:

- the artifact is structurally valid and remains suitable for schema,
  materializer, prefix, and feature-distribution diagnostics;
- it is **not ready for tiny smoke training**;
- 772 / 25,396 states have no matched action, with 769 in train and 253 from one
  replay after reconstructed roster/moves diverge;
- forced-switch coverage is zero;
- `opponent_active_displayed_species_uncertain` is active in 25,381 / 25,396
  states, so the intended Illusion-scoped species inference and skilled-player
  public-belief calibration did not reach this materialized path as intended.

The next gate is to fix and integration-test replay-state/materializer roster,
move/form continuity, and displayed-species uncertainty handling. Any
rematerialization still requires explicit approval. Smoke training remains
blocked, and implementing `legal-action-v8` first is not recommended because it
would not repair the v7 dataset-state defects. The frozen v7 schema remains
552D with fingerprint
`956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`.

## Reconstruction blocker fix update

The two primary blockers are fixed in source and regression-tested:

- `gen9randombattle-2591563263` is a custom 24-vs-24 replay. Profiler
  eligibility, full preflight, and per-battle materialization now reject
  explicit team sizes above the frozen six-slot schema.
- Ordinary switch/drag events no longer mark public displayed species
  uncertain. The bit remains an explicit Illusion/true-species guard.

The existing artifact and source manifest are stale for training. Retain the
dataset as a before-fix diagnostic, but replace the unsupported train replay,
pass fresh read-only preflight/tests, obtain explicit approval, rematerialize
v7/v7, and repeat the quality audit. The old artifact has 519 residual
mismatches after subtracting the 253 custom-replay mismatches; the replacement
artifact must be measured rather than assumed clean.

Materialization readiness is **blocked on manifest replacement and fresh
approval**. Training remains blocked on the replacement artifact's quality
audit. No schema or fingerprint changed.

## Corrected manifest preflight update

Manifest replacement is prepared in
`artifacts/training_plan/manifests/diagnostic_300_v7_v7_corrected_manifest.json`.
It excludes `gen9randombattle-2591563263` and replaces it with the eligible
train-split `long_close` replay `gen9randombattle-2591433931`, whose public
team sizes are p1=6 and p2=6. The original manifest remains unchanged, the
validation/test splits remain unchanged, and split counts remain 210/45/45.

Read-only manifest validation and full preflight pass with `legal-action-v7`:
all entries are unique and present, all paths exist, selected mechanic coverage
remains above the random baseline, and there are zero unsupported team-size
replays. The old `diagnostic_300_v7_v7` artifact remains stale for training
because it predates the reconstruction fixes. Full v7/v7 rematerialization is
now ready for explicit approval; smoke training remains blocked pending the
fresh artifact and quality audit.

## Corrected materialization update

The corrected v7/v7 materialization was explicitly approved and completed in
`artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected`. It processed
300/300 valid battles with 0 failures, retained 300 shards, preserved 210/45/45
battle splits, produced 25,235 states and 191,667 candidates, and validated
`live-private-belief-v7` 3208D plus `legal-action-v7` 552D with fingerprint
`956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`.

The corrected quality audit reports 24,716 matched / 519 unmatched decisions
(97.94%), zero unsupported team-size replays, no selected
`gen9randombattle-2591563263`, and 0 displayed-species-uncertain states. The
old stale dataset remains untouched and superseded for training. Readiness for
materialization is complete; smoke training remains a separate explicit
approval gate after accepting the corrected audit.

## Residual unmatched-state audit update

The 519 residual unmatched labels are now audited. They are all missing-candidate
cases, not candidate-label mismatches: 486 are missing reconstructed active
moves and 33 are missing switch targets. The distribution is 516 train, 1
validation, and 2 test. The replacement replay `gen9randombattle-2591433931`
has zero residual unmatched labels; its 21 broader legacy-audit rows were fixed
or intentionally skipped initial deployments.

The corrected dataset is acceptable for an explicitly approved tiny smoke
training run as a plumbing/overfit sanity check only. It is not yet a durable
training-quality baseline; larger training should wait for move-list and
roster/form alias reconstruction fixes followed by approval-gated
rematerialization.
