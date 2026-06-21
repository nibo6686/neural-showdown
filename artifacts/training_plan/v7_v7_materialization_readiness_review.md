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

Post-corrected addendum: the approved corrected v7/v7 dataset later exposed
519 residual missing-candidate skips. The targeted source fix documented in
`missing_candidate_reconstruction_fix_report.md` resolves the clean
reconstruction paths in code and tests without changing `legal-action-v7`;
the follow-up `residual_34_unmatched_case_triage_report.md` reduces the
source-level replay-prefix residual to 8 no-leakage/unsupported rows. The old
materialized artifact remains stale until a future explicitly approved
rematerialization.

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

## Residual triage + Transform/Imposter fix update

The residual-34 triage fixed 26 of the 34 source-level replay-prefix residuals
and was checkpointed at `5ad748b78670d565056b9273c72e1d3ad0c4337e`. The
follow-up residual-8 verification then found one of the remaining rows still
fixable: `gen9randombattle-2589571474` turn 20 p1 `move: Thunder Wave` was a
Ditto/Imposter Transform reconstruction bug (copied moves merged across Transform
stints, plus a future `Leaf Blade` pulled from a later stint). It is now fixed
with stint-scoped Transform reconstruction
(`transform_imposter_reconstruction_fix_report.md`); `legal-action-v7` is
unchanged (552D / `956da3d2…1bf39d7`).

The expected residual unmatched count after a future approved rematerialization
is now **7** (4 pre-reveal Illusion move cases + 3 unsupported Illusion duplicate
switch artifacts), down from 8. The remaining 7 are bounded Illusion/public-replay
ambiguity, not live-play limitations: live play knows its own true side from the
Showdown request. `scripts/recompute_v7_v7_residual_unmatched_from_replays.py`
makes this reproducible read-only (1 matched, 7 unmatched, all-as-expected).

Full v7/v7 rematerialization is ready for explicit approval; smoke training
remains blocked until the fresh artifact is materialized and re-audited. No
training, rematerialization, checkpoint promotion, live-default/live-bot change,
schema change, or push occurred.

## Zoroark/Illusion actor-private reconstruction update

The 7 remaining Illusion residuals were then audited from the acting player's
perspective (`illusion_zoroark_actor_private_reconstruction_report.md`). All 7 are
the Zoroark user's own decision rows, so the true Zoroark/Zoroark-Hisui identity
is an own-side fact. Six are now fixed by actor-private reconstruction of stints
that self-confirm via a later `replace`: three move de-disguises
(`gen9randombattle-2591469202` t1; `gen9randombattle-2593348981` t6, t18) and three
duplicate-Illusion switch relabels to the true `switch: Zoroark`
(`gen9randombattle-2591404793` t21/t23/t25). One row
(`gen9randombattle-2593348981` t1) is quarantined: its "Avalugg" stint switched
out before any reveal and is publicly indistinguishable from the real Avalugg, an
irreducible public-replay attribution limitation.

The opponent's pre-reveal belief is unchanged (true species never leaks); the
post-action impossible-displayed-species contradiction signal is deferred to
future `legal-action-v8` threat-awareness work (no schema change here).
`legal-action-v7` stays 552D / `956da3d2…1bf39d7`; no state dim changed.

The expected residual unmatched count after a future approved rematerialization is
now **1** (down from 7). The residual recomputation harness reports 8 cases, 7
matched, 1 unmatched, all-as-expected. Full v7/v7 rematerialization is ready for
explicit approval; smoke training remains blocked pending the fresh artifact and
re-audit. No training, rematerialization, checkpoint promotion,
live-default/live-bot change, schema/v8 change, or push occurred.

## Post-Illusion rematerialization completed

The approved post-Illusion v7/v7 rematerialization ran (source
`4cde8bd15ff71021d57e582d8eb808da1f11bbad`) into
`artifacts/training_plan/datasets/diagnostic_300_v7_v7_post_illusion`. Result:
300/300 valid, 0 failed, 25,235 states, 197,429 candidates, 210/45/45 splits, 300
shards, `live-private-belief-v7` 3208D + `legal-action-v7` 552D /
`956da3d2…1bf39d7`, all validation passed, live defaults unchanged. Match rate
**99.94% (25,220 / 15)**, up from the corrected 97.94% (519 unmatched). See
`diagnostic_300_v7_v7_post_illusion_materialization_report.md` and
`diagnostic_300_v7_v7_post_illusion_dataset_quality_audit.md`.

All documented reconstruction fixes are confirmed present in the artifact. The 15
remaining residuals are all `move`-kind explicit skips: 3 irreducible
non-self-confirming Illusion stints, 11 from a newly-surfaced **fixable Ditto
re-transform-into-same-species bug** in `_active_transform_copied_moves` (stint
anchor collides on identical re-transform `raw`), and 1 Struggle PP-exhaustion
skip. The earlier "expected 1" applied only to the 8 documented rows. A tiny
smoke/plumbing run is acceptable on this artifact if approved; durable training
should wait for the Ditto re-transform fix and another rematerialization. Old
datasets were not overwritten. No training, checkpoint promotion,
live-default/live-bot change, schema/v8 change, or push occurred.

## Ditto re-transform fix completed (residual 15 → expected 3)

The Ditto/Imposter re-transform-into-same-species bug is now fixed
(`ditto_retransform_same_species_fix_report.md`): `_active_transform_copied_moves`
anchors the current stint by event object identity instead of `raw` string. On
replay-prefix recomputation the 11 Ditto rows (Sacred Fire/Energy Ball/Outrage)
now match, and the single `Struggle` row also matches (the corrected stint surfaces
the replay-observed Struggle, represented by the existing schema-safe exhaustion
fallback). The `Thunder Wave` Transform case and Illusion fixes are preserved. The
residual recomputation harness covers all 22 post-Illusion residuals: 19 matched /
3 unmatched, all-as-expected. The **expected residual after a future approved
rematerialization is now 3** (the irreducible non-self-confirming Illusion stints).
This is a source/test/report change; the checked-in
`diagnostic_300_v7_v7_post_illusion` dataset is unchanged until a future explicitly
approved rematerialization applies the fix. `legal-action-v7` stays 552D /
`956da3d2…1bf39d7`; no state dim changed. No training, rematerialization,
checkpoint promotion, live-default/live-bot change, schema/v8 change, or push
occurred.

## Post-Ditto rematerialization completed (residual 15 → 3)

The approved post-Ditto v7/v7 rematerialization ran (source
`01f14d6c04097b757f7a0435bc4eb3bf039ab768`) into
`artifacts/training_plan/datasets/diagnostic_300_v7_v7_post_ditto`. Result: 300/300
valid, 0 failed, 230.5s, 25,235 states, 197,449 candidates, 210/45/45 splits, 300
shards, `live-private-belief-v7` 3208D + `legal-action-v7` 552D /
`956da3d2…1bf39d7`, all 18 validation checks passed, live defaults unchanged. Match
rate **99.99% (25,232 / 3)**, up from post-Illusion 99.94% (15 unmatched). See
`diagnostic_300_v7_v7_post_ditto_materialization_report.md` and
`diagnostic_300_v7_v7_post_ditto_dataset_quality_audit.md`.

All reconstruction fixes are confirmed present in the artifact (11 Ditto
re-transform rows, Struggle, prior Thunder Wave Transform with Leaf Blade absent,
actor-private Zoroark/Illusion). The only 3 remaining residuals are the irreducible
non-self-confirming Illusion stints — explicit quarantined skips. Schema/feature
names byte-identical to post_illusion; old datasets not overwritten. This is the
cleanest v7/v7 artifact to date and the recommended baseline for a first tiny
smoke/plumbing training run if explicitly approved. No training, checkpoint
promotion, live-default/live-bot change, schema/v8 change, or push occurred.

## Post-Ditto smoke training completed

The explicitly approved one-epoch smoke/plumbing run completed on CUDA with
exit code 0 using
`training_runs/smoke_v7_v7_post_ditto/smoke_v7_v7_post_ditto_config.json` and
the post-Ditto `.npz`. It trained the state-value and action-rank heads for
2,569 steps and passed its tiny overfit check. Train value MSE was 1.295563.
Validation value MSE was 1.483368; validation rank NLL/top-1/top-3 were
1.383279 / 0.434146 / 0.838137. Test value MSE was 1.478658; test rank
NLL/top-1/top-3 were 1.414682 / 0.410626 / 0.815486.

Both generated checkpoints record exact `live-private-belief-v7` 3208D and
`legal-action-v7` 552D versions, dimensions, ordered-name fingerprints, and
manifest checksum, with `production_eligible: false`. Numeric report values,
dataset arrays, and checkpoint tensors are finite. The smoke therefore passes
the intended plumbing/schema/checkpoint gate, but the one-epoch quality metrics
do not authorize durable training or promotion; the value head does not beat
the constant baseline. Checkpoint promotion, live/default changes, and
production remain closed. See
`training_runs/smoke_v7_v7_post_ditto/smoke_v7_v7_post_ditto_report.md`.

## 1,000-battle post-Ditto materialization and audit

The approved larger v7/v7 materialization completed in
`datasets/diagnostic_1000_v7_v7_post_ditto` with 1,000/1,000 valid battles,
80,644 states, 617,687 candidates, 700/150/150 battle splits, exact frozen
v7/v7 schema/fingerprints, and all 18 structural checks passing. The manifest
generator now enforces the six-slot protocol limit directly; the stale 24-vs-24
and 8-vs-8 selections were replaced before materialization. Old datasets were
not overwritten.

The quality audit reports 80,601 matched / 43 unmatched (99.9467%). Forty-one
rows are explicit quarantined Illusion/public-replay ambiguities. Two rows
surface a fixable Magic Bounce category: reflected Defog becomes false Hatterene
moveset evidence and crowds out Psychic, and reflected Will-O-Wisp is treated as
an actor-selected move. Since reflected-move contamination can also introduce
illegal unchosen candidates, this artifact is not approved for rank-only
training. Fix, regression-test, rematerialize under explicit approval, and
re-audit first. No training, promotion, live/default, schema, or v8 change
occurred.
