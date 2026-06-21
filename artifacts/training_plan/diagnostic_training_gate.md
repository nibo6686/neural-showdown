# Diagnostic Training Gate

## Gate before first training run

- [x] Final representation freeze audit completed.
- [x] Machine-readable schema manifest written and validated.
- [x] Replay profiler designed.
- [x] Replay profiler implemented and run against the existing pool.
- [x] Battle-level `diagnostic_300` manifest materialized and overlap-checked.
- [x] v7/v5 feature generation benchmarked on a small subset.
- [x] Slice counterfactual and schema-prefix tests pass.
- [x] Existing checkpoints and live defaults remain untouched.
- [x] Representation checkpoint committed before replay profiling.
- [x] Training labels are explicitly chosen and documented separately for state
  value, action rank and action value.
- [x] Train/validation/test assignment is fixed by battle before featurization.
- [x] Tiny-benchmark output metadata records schema versions, ordered-name fingerprints,
  manifest/profile versions, source commit, dtype and information boundary.
- [x] vNext state-value, action-rank and action-value label decisions documented.
- [x] Tiny-10 label extraction dry run completed with explicit unmatched-action reporting.
- [x] Full `diagnostic_300` v7/v5 feature materialization completed.
- [x] Full `diagnostic_300` state-value and action-rank label extraction completed.
- [x] Materialized dataset split/schema/label sanity checks pass.
- [x] First diagnostic training plan/config/command written.
- [x] Native v7/v5 diagnostic training entrypoint implemented.
- [x] Diagnostic `--validate-only` path tested on the full frozen artifact.
- [x] First diagnostic training plan/config/command reviewed.
- [x] User explicitly approved the first diagnostic training run.
- [x] First diagnostic training run completed and reported.
- [x] First diagnostic value-head debug pass completed.
- [x] First diagnostic training metrics and value-head debug reviewed for next-step approval.
- [x] Targeted value-only isolation experiment approved and completed.
- [x] Value-only isolation metrics reviewed for next-step approval.
- [x] Reduced-capacity regularized value-only experiment approved and completed.
- [ ] Reduced-capacity value-only metrics reviewed for next-step approval.
- [x] Legacy pipeline / contamination audit completed.
- [x] vNext checkpoint schema-fingerprint guardrails implemented and tested.
- [x] Action-rank head evaluated offline against baselines (validation split).
- [x] Larger action-rank diagnostic dataset plan + 1000-battle manifest built and validated.
- [x] vNext full-manifest materializer generalized (parallel, crash-safe, resumable) and tested.
- [x] `diagnostic_1000_action_rank_v7_v5` full feature materialization complete and validated.
- [x] Action-rank-only diagnostic training run on `diagnostic_1000_action_rank_v7_v5` complete and evaluated.
- [x] Offline-to-live inference readiness audit completed.
- [x] Opt-in vNext inference harness implemented (strict load, masking, Tera/switch serialization, fail-closed) and tested.
- [x] Opt-in vNext live-eval recommendation shadow mode implemented (`/evaluate-vnext-dry-run`, default off) and tested.
- [x] Browser overlay UI improved (collapsible/draggable pill, opt-in vNext shadow display, display-only).
- [x] Warm vNext shadow latency measured: ~48 ms warm (vs ~4.5 s cold one-time); usable for manual use.
- [ ] Slot-index/live-parity validated on real Showdown rooms with real extension packets.
- [x] Manual display-only vNext recommendation test plan written; execution remains pending.
- [x] First manual display-only run triaged; recommendation-quality failure and double-KO force-switch overlay bug documented.
- [x] Rage Fist dynamic-power/live-impact gap diagnosed with a controlled v5 impact comparison.
- [x] Rage Fist `times_attacked` impact correction implemented and focused-tested without changing the v5 schema.
- [x] Dynamic-move dependency audit written; Last Respects and boost-dependent impact plumbing remain open.
- [x] Showdown/sim-core-backed dynamic move mechanics fidelity harness run; v6 reaches 12 PASS / 0 FAIL / 0 NEEDS_VERIFICATION.
- [x] v5 dynamic mechanics repair/versioning plan written.
- [x] First v5-safe repair batch completed: Last Respects, live boost scaling, and type-aware Curse.
- [x] Second v5-safe repair batch completed: HP-, speed-, and weight-variable-power moves.
- [x] Weather/Terrain Pulse and Body Press/Foul Play verification cases resolved as PASS.
- [x] `legal-action-v6` repeat-chain requirements written for Rollout/Fury Cutter.
- [x] Append-only `legal-action-v6` repeat-chain schema implemented (331D; v5 prefix unchanged).
- [x] Rollout/Fury Cutter exact chain mechanics pass; unknown chain state fails closed.
- [x] Tiny one-battle v7/v6 diagnostic materialization completed and validated.
- [x] Exhaustive bundled Gen 9 Random Battles move-pool audit completed: 350 moves.
- [x] Mechanics-repair batch 1 (fixed-damage, multi-hit, dynamic accuracy) completed: FAIL 176 → 159.
- [x] Mechanics-repair batch 2 (secondary/status/stat/volatile next-state) completed: FAIL 159 → 39.
- [x] Mechanics-repair batch 3 (dynamic type/STAB, charge/delay timing) completed: FAIL 39 → 27.
- [x] Mechanics-repair batch 4 (conditional execution/success, turn/history power) completed: FAIL 27 → 9.
- [x] Mechanics-repair batch 5 (final 9: crit/Freeze-Dry/Photon Geyser + fail-closes) completed: FAIL 9 → 0.
- [x] Gen 9 Random Battles mechanics completeness has no wrong-exact FAIL entries.
- [x] Dynamic mechanics FAIL set resolved or versioned into a proposed action v6 before further training.
- [x] Post-FAIL=0 training-readiness review written (`v7_v6_training_readiness_review.md`).
- [x] Small v7/v6 diagnostic_300 rematerialization completed and report proven (`diagnostic_300_v7_v6_materialization_report.md`): schema/fingerprint validated, mechanics-clean impact path, match rate 96.96%, exact-vs-INEXACT share, Tera/switch counts, no stale-checkpoint reuse.
- [x] `legal-action-v7` typed-effect schema design written (`legal_action_v7_typed_effect_schema_design.md`); design only, not implemented/approved.
- [x] `legal-action-v7` batch 1 implemented (`legal_action_v7_batch_1_status_stat_implementation.md`): schema shell (361D, append-only, v6 prefix + fingerprint preserved) + typed status/stat fields; no rematerialization/training.
- [x] `legal-action-v7` batch 2 implemented (`legal_action_v7_batch_2_volatile_implementation.md`): typed volatile slice appended (now 375D; 361D batch-1 prefix + fingerprint preserved); no rematerialization/training.
- [x] `legal-action-v7` batch 3 implemented (`legal_action_v7_batch_3_item_effects_implementation.md`): typed item-effect slice appended (now 388D; full 375D batch-2 prefix preserved); no rematerialization/training.
- [x] `legal-action-v7` batch 4 implemented (`legal_action_v7_batch_4_timing_priority_implementation.md`): typed timing/priority slice appended (now 406D; full 388D batch-3 prefix preserved); no rematerialization/training.
- [x] `legal-action-v7` batch 5 implemented (`legal_action_v7_batch_5_hp_side_effects_implementation.md`): typed HP-side-effect slice appended (now 420D; full 406D batch-4 prefix preserved); no rematerialization/training.
- [x] `legal-action-v7` batch 6 implemented (`legal_action_v7_batch_6_field_side_effects_implementation.md`): typed field/side-effect slice appended (now 452D; full 420D batch-5 prefix preserved); no rematerialization/training.
- [x] v7 edge-case and rollout-parity audit plan written (`v7_edge_case_rollout_parity_audit_plan.md`), including Gen 9 Randbats/National Dex scope and the action-feature versus transition boundary; no code, materialization, or training.
- [x] `legal-action-v7` batch 7 implemented (511D; action-risk/probability and provenance summaries; batch-6 prefix preserved).
- [x] `legal-action-v7` batch 8 implemented (552D; forced-decision/secondary-chance fields; batch-7 prefix preserved; full fingerprint `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`).
- [x] v7/v7 materialization readiness review written (`v7_v7_materialization_readiness_review.md`).
- [x] Full-manifest materializer minimally wired and tested for `legal-action-v7` (including inherited v6 repeat-chain impact behavior, 552D metadata, and exact fingerprint validation).
- [x] Skilled-player public-belief calibration contracts added: species-singleton ability inference, ambiguous-set preservation, exact own-side knowledge, Illusion guard, conservative item evidence, and speed range/exact separation.
- [x] Possible mechanic-threat awareness audited (`possible_mechanic_threat_awareness_audit.md`): v7 is partial; absorb threats are explicit, while Unaware/Magic Bounce/Good as Gold/Levitate/secondary-blocker possibility flags remain future-v8 work.
- [x] Small diagnostic v7/v7 materialization explicitly approved, completed, and validated (`diagnostic_300_v7_v7_materialization_report.md`): 300/300 valid battles, 25,396 states, 189,957 candidates, 210/45/45 battle splits, 552D v7 action fingerprint validated, 300 resumable shards retained.
- [x] `diagnostic_300_v7_v7` read-only dataset quality audit completed (`diagnostic_300_v7_v7_dataset_quality_audit.md`): structurally valid, but smoke training blocked on replay-state/materializer reconstruction quality.
- [x] Primary replay-state/materializer blockers fixed and regression-tested (`replay_state_reconstruction_blocker_fix_report.md`): custom team sizes above six now fail eligibility/preflight, and ordinary displayed species are public-known rather than globally Illusion-uncertain.
- [x] Rejected 24-member train replay replaced in the corrected manifest; fresh preflight and approved v7/v7 rematerializations completed.
- [x] Fresh post-Ditto v7/v7 replacement artifact passes the dataset-quality audit before smoke training.
- [x] Explicitly approved one-epoch post-Ditto v7/v7 smoke/plumbing training completed and reported with exact checkpoint metadata and finite outputs.
- [x] Fresh 1,000-battle v7/v7 manifest regenerated with current six-slot eligibility filters and exact 700/150/150 battle splits.
- [x] Approved `diagnostic_1000_v7_v7_post_ditto` materialization completed: 1,000/1,000 valid, 80,644 states, 617,687 candidates, exact v7/v7 metadata, all 18 structural checks passed.
- [x] Fix newly surfaced Magic Bounce reflected-move label/moveset contamination with targeted replay-backed reproduction and regression tests.
- [x] Explicitly approve and run a fresh 1,000-battle v7/v7 rematerialization after the Magic Bounce fix, then pass re-audit before rank-only training.
- [x] Separately approve and complete the 1,000-battle post-Magic-Bounce v7/v7 rank-only diagnostic training run.
- [x] Selected post-Magic-Bounce v7/v7 rank-only checkpoint evaluated offline
  on the full test split with strict inference loading, incompatible
  schema/dimension/fingerprint rejection probes, baselines, and mistake slices.
- [x] Source-agnostic v8 meta-prior/opponent-set belief representation designed
  (joint prior/posterior contract, Randbats/Smogon/replay/fixture sources,
  compact state/action projections, and no-leakage test plan); not implemented.
- [x] v8 source-neutral meta-prior/posterior contracts and fixture source
  implemented with future-prefix, hidden-truth perturbation, contradiction,
  unknown-tail, and safe protocol-evidence tests.
- [x] v8 contracts wired into a diagnostic-only public-replay-prefix belief
  construction path with real Magic Bounce/Illusion/item fixtures and no
  state/action feature changes.
- [x] Existing checked-in Gen 9 Randbats role/movepool data wrapped behind a
  deterministic pinned `MetaPriorSource`, with factorized quality, source
  SHA-256, explicit incompleteness warnings, and unknown tail mass.
- [ ] Pinned Randbats generator prior snapshot built and calibration/convergence
  audited before any v8 materialization.
- [ ] Tiny rank-only training on fresh v7/v6 diagnostic_300 approved (plumbing/behavior comparison, exact-vs-INEXACT breakdowns).
- [ ] Durable `legal-action-v7` training approved beyond the completed one-epoch smoke.
- [ ] Mechanically stale v5 Rage Fist data/checkpoint disposition approved before further training.
- [ ] Controlled manual private-match recommendation test plan approved.
- [ ] Value-label quality audit approved.
- [ ] Larger-dataset value learning approved.
- [ ] Live action-ranker loader schema-assert hardening (separate, approval-gated).
- [ ] Any checkpoint approved for production/live use.

Do not launch the full 15k rebuild until diagnostic 300, small 1000 and medium
5000 benchmarks justify it.

## First-model success criteria

The first diagnostic model must:

- load only v7 state and/or v5 action features with exact metadata validation;
- pass stat/type/item/ability/species/status/Tera/field/move/constraint/action
  sensitivity checks;
- improve or at least match the appropriate old-model held-out calibration
  baseline, with uncertainty reported for the small sample;
- avoid regressions on immunity, unavailable-action, switch, Draco, perspective
  and privacy sanity cases;
- record replay count, decision/example count, build time, output size, epoch
  time, peak GPU memory, dtype, batch size and seed;
- remain non-production and use new artifact paths.

## Decision

The full `diagnostic_300` materialization passed: 300/300 battles produced
25,396 v7 state rows and 189,957 v5 action-candidate rows with exact 210/45/45
battle splits, no duplicated state vectors, and no action-value labels. State
labels are limited to +1/-1. Action-rank extraction matched 24,624 decisions;
772 unmatched groups and 600 initial-deployment non-decisions are explicitly
audited and excluded from action-rank positives.

The first diagnostic training plan/config/command and native-layout entrypoint
are implemented. Full-artifact `--validate-only` passed with exact v7/v5
schemas and fingerprints, 210/45/45 battle splits, 25,396 state rows, 24,624
matched action groups, zero malformed candidate groups, zero action-value
labels, correct model output shapes, finite no-grad losses, and zero optimizer
steps.

The single approved diagnostic run completed on CUDA for 10 epochs and 3,120
optimizer steps. The mandatory tiny-subset overfit check passed for both heads.
Action ranking generalized above simple baselines (test top-1 43.57%, top-3
83.02%), while state value overfit badly and failed to beat the constant
validation/test baseline (test MSE 1.4523 versus approximately 1.0).

The read-only value-head debug found correct labels/perspective for all 300
battles, no cross-split duplicates, and no class or side imbalance. The failure
is most consistent with memorization of only 210 independent training battles,
saturated tanh/MSE predictions, and shared-encoder interference from 231
rank-only steps per epoch (74% of updates). The value head is not approved to
continue unchanged.

The single value-only isolation run removed all rank gradients and used exactly
81 value-only optimizer steps per epoch. It early-stopped after epoch 3 and
selected epoch 1 by validation value MSE. Removing rank interference improved
best validation MSE from 1.2921 to 1.1321 and test MSE from 1.4523 to 1.0524,
while test sign accuracy rose from 55.64% to 61.78% and saturation fell
substantially.

The isolated value head still failed to beat the approximately 1.0 constant
MSE baseline and overfit rapidly after epoch 1. This confirms rank interference
was real but not sufficient to explain the failure.

The single approved reduced-capacity regularized value-only run cut the model
from 218,786 to 63,170 parameters (state encoder [64]→[16]), added dropout 0.3
and weight decay 0.01, and kept the dataset, labels, splits, seed, optimizer,
learning rate, value target, and tanh/MSE design fixed. It early-stopped at
epoch 3 and selected epoch 1 by validation value MSE. For the first time the
value head beat the constant baseline: validation MSE 0.9478 and test MSE
0.9453 (both ~5% under ~1.0), test sign accuracy 63.14%, and zero saturated
predictions (test `|pred|>=0.95` fell from 4.90% to 0.00%). This confirms
over-capacity memorization on only 210 independent training battles as the
dominant failure mode.

The margin remains small and the head still overfits after one epoch, so the
achievable signal on this split is thin. Per the standing decision rule,
further single-config tuning on `diagnostic_300` stops here; meaningful
value-head progress requires more independent battles. Moving value learning to
a larger diagnostic dataset and all production/live promotion remain **closed**
pending explicit approval. No checkpoint is approved for live use.

A legacy pipeline / contamination audit (`legacy_pipeline_audit.md`) then
confirmed vNext training is not contaminated by old schema-less checkpoints
(it builds fresh models, has no checkpoint load/resume path, and writes to a
separate output directory), and that the old v2/v3 live defaults are
intentional. Its primary gap — checkpoints recorded schema version + dims but
not feature-name fingerprints — is now closed: vNext checkpoints embed
`state_feature_names_sha256` / `action_feature_names_sha256` plus schema
names/dims, and a strict `validate_vnext_checkpoint_metadata` guard rejects any
name/dim/fingerprint mismatch while flagging fingerprint-less legacy checkpoints
explicitly (9 new tests). No old checkpoints were rewritten and no live defaults
changed. The weaker live action-ranker loader is documented and deferred to a
separate approval-gated task. The gate remains **closed**.

An offline action-rank evaluation (`diagnostic_300_action_rank_offline_eval.md`)
then scored the first checkpoint's rank head on the **validation** split (2,254
groups; test split not newly touched). It beats every simple baseline — top-1
0.4556 vs 0.3909 best heuristic (`max_expected_damage`) and 0.3882
(`type_prior_move`), top-3 0.8656 vs 0.7276 — and reaches 30.2% top-1 on
switches and 34.6% on non-damaging choices where damage heuristics score ~0,
confirming it learns decision preferences beyond damage/type priors. Weak spots:
Tera moves (1.7% of positives) and occasional switch-over-attack confusion. The
head is promising enough to justify designing a larger, Tera/switch-rebalanced
action-rank diagnostic dataset/run, which remains **closed** pending explicit
approval. No training, tuning, or promotion occurred.

The larger action-rank dataset plan (`diagnostic_1000_action_rank_dataset_plan.md`)
and its battle-level manifest (`manifests/diagnostic_1000_action_rank_manifest.json`,
1000 battles, 700/150/150, PASS) are now built and validated from the existing
14,255-battle eligible pool — no new replays. Enrichment lifts switch decision
volume ~49% (20,756 vs 13,956) while holding the switch share of decisions at
the natural ~24% (0.237 vs 0.252) and adds modest Tera-action coverage (+16%),
so the sample is enriched without distortion. Full feature materialization was
**not** run: it would take ~2h and additionally requires generalizing the
`benchmark_vnext_featuregen` full-manifest preflight (currently hardcoded to 300
entries / 210-45-45 / the diagnostic_300 output path). Materialization and all
training/promotion remain **closed** pending explicit approval. No training,
checkpoint, or live-default change occurred.

The full-manifest materializer was then generalized (preflight derives expected
battle/split counts from the manifest; added a cross-manifest overwrite guard)
and re-architected to be parallel, crash-safe, and resumable (per-battle shards;
`ProcessPoolExecutor`). `diagnostic_1000_action_rank_v7_v5` materialized in
**409 s** with 6 workers: **1000/1000 battles valid, 0 failed**, 80,899 states,
606,770 candidates, 79,525 action-rank positives (one per group), match rate
98.30%, splits 700/150/150 with no split crossing, schema/fingerprints matching
frozen v7/v5, action-value labels 0. Independent re-validation of the `.npz`
passed every Part D check. Tera positives 426→1,440 and switch positives
6,238→20,864 grew ~3.3–3.4× without distorting the action mix. Training and
live/production promotion remain **closed** pending an explicit action-rank-only
training plan/config and approval; no training, checkpoint, or live-default
change occurred.

The single approved **action-rank-only** run then completed on CUDA (11 epochs,
10,890 rank-only steps, ~458 s; state-value and action-value disabled,
`optimizer_step_source=rank_batches_only`, value head untrained). Selected by
validation rank NLL (best epoch 8). It beat every offline baseline on the
validation split (top-1 0.4626 vs 0.3820 max-damage / 0.3802 type-prior; top-3
0.8576 vs 0.7303; MRR 0.6658), and matched on test (touched once: top-1 0.4608,
top-3 0.8504, NLL 1.3252). It learns beyond damage heuristics (switch top-1
0.255, non-damaging 0.305 where damage heuristics score ~0). Known weak spot:
Tera top-1 0.178 (under-values the Tera commitment). No checkpoint promoted, no
live defaults changed; live/private-match/production promotion remains
**closed**.

An offline-to-live inference readiness audit (`vnext_live_inference_readiness_audit.md`)
then confirmed the v7/v5 checkpoint loads under strict schema/fingerprint
validation and that a controlled scorer reproduces the offline evaluator
bit-for-bit (validation top-1 0.46258 == evaluator), with model scoring <1 ms/
decision. But the **current live path is not v7/v5-ready**: it loads ActionRankerMLP
with v2 state / v3 action features (pad/truncate), generates **no Tera candidates**,
and does not build v7 state or v5 candidate features (no per-candidate
resolve_action_impact). Blockers before private-match testing: a new opt-in vNext
inference path (v7 state + v5 candidates incl. Tera, masking, fail-closed
fallback, candidate→choice serializer) and an end-to-end live latency measurement.
No private matches were run; no live defaults/checkpoints changed; gate remains
**closed**.

The **opt-in vNext inference harness** (`vnext_inference.py`, default off; gated by
`NEURAL_VNEXT_INFERENCE` and never imported by the default v2/v3 live path) is now
implemented and tested (10 focused tests). It loads `VNextDiagnosticMLP` under
strict schema/fingerprint validation (PASS, fingerprints validated), reproduces
the offline evaluator bit-for-bit (validation top-1 0.4625833), masks
unavailable candidates before scoring, serializes move / `move <slot> terastallize`
/ switch choices (Tera distinct), and **fails closed** to `"default"` on missing
checkpoint, schema/fingerprint mismatch, no/all-unavailable candidates, or
serialization failure (no pad/truncate). Model scoring latency ~0.97 ms/decision
(p95 2.43 ms; excludes live feature gen). Remaining before a private-match dry run:
live v7/v5 feature + Tera/switch candidate generation, slot reconciliation, and
end-to-end latency. No battles run, no live defaults/checkpoints changed; gate
remains **closed**.

The Rage Fist correction is now implemented and documented in
`rage_fist_times_attacked_fix_report.md`. Complete protocol histories track
per-species successful attack hits and pass `times_attacked` into sim-core;
Rage Fist now scales from 29.45% average at 0 hits to 58.29% at 1 and 87.58% at
2 in the controlled Annihilape/Cresselia fixture. Unknown history fails closed.
The v5 schema remains 318D with identical names/order, but existing materialized
v5 data and checkpoints are mechanically stale for Rage Fist impact. The
companion `dynamic_move_dependency_audit.md` identifies Last Respects and
boost-dependent move plumbing as known open gaps. No data was rematerialized,
no model trained/promoted, and the gate remains **closed**.

The mechanics fidelity gate (`dynamic_move_mechanics_fidelity_audit.md`) uses
the shared sim-core/Showdown-backed impact path and representative
counterfactuals across battle-history, repeat-use, boost, HP, status, item,
field, stat-source, speed/weight, Curse, and accuracy dependencies. Two v5-safe
repair batches now fix Last Respects, live boost plumbing, type-aware Curse,
Reversal/Flail, Gyro Ball/Electro Ball, Grass Knot/Low Kick, and Heavy Slam/Heat
Crash using existing fields. Weather Ball/Terrain Pulse pass a
grounded-versus-airborne field check, and Body Press/Foul Play pass exact-stat
and boost-source checks. The append-only `legal-action-v6` implementation adds
13 repeat-chain context/provenance fields after the unchanged 318D v5 prefix
(331D total; fingerprint
`ac8fb3d36e29a3a2ed6795f790c34d0a6f1330f6d6ef2262ab4722c58373f049`).
Rollout/Fury Cutter now use exact protocol-derived prior-success counts and
fail closed when chain state is unknown. The audit is **12 PASS / 0 FAIL / 0
NEEDS_VERIFICATION**. A one-battle tiny v7/v6 materialization produced 52 state
rows and 337 action candidates with schema validation PASS and no training.
The v5 schema remains 318D and unchanged, but all existing v5 data/checkpoints
remain mechanically stale. Full-scale rematerialization and training remain
blocked; the gate remains **closed** pending review and separate approval.

The comprehensive Gen 9 Random Battles mechanics audit
(`gen9randbats_mechanics_completeness_audit.md`) then enumerated all **350**
unique moves across the bundled 507 species/form set entries. Result:
**121 PASS / 176 FAIL / 53 INEXACT / 0 NOT_RELEVANT**. The earlier 12/0
counterfactual suite remains useful but is not a completeness gate. Wrong-exact
blockers include fixed-damage and multi-hit moves, dynamic accuracy,
history/turn-conditional and delayed damage, dynamic type/STAB, guaranteed
critical metadata, and omitted secondary/status transitions. No schema changed,
no training ran, and no diagnostic_300/1000 materialization occurred. The gate
remains **closed** until all material entries are PASS or explicitly
INEXACT/fail-closed.

The **opt-in live recommendation shadow mode**
(`vnext_live_eval_server_shadow_mode_report.md`) is now implemented: a new
`POST /evaluate-vnext-dry-run` route (gated by `NEURAL_VNEXT_INFERENCE`, default
off, lazy-imported; default `/evaluate` untouched) reconstructs the real
extension payload into v7 state (3208D) + v5 candidates (incl. `move_tera` when
Tera is legal) via the existing `build_features_from_live_payload` and the
training candidate/impact generators, scores with `VNextActionRanker`, and returns
a display-only recommendation + diagnostics. On a sanitized fixture it produced
4 move + 4 move_tera + 2 switch candidates, schema PASS, and a valid `move 2`
choice; it fails closed to `"default"` (no candidates, missing fields, dim/schema
mismatch, serialization failure). Cold latency is dominated by sim-core impact
resolution (~2.9 s for 10 candidates); warm-client end-to-end latency is still
unmeasured. No command was sent to Showdown, no battle played, no browser state or
live default changed (8 focused tests). Gate remains **closed**.

A concise manual display-only recommendation plan is now written in
`manual_vnext_recommendation_test_plan.md`. It covers opt-in launch, overlay use,
normal/Tera/switch decisions, optional force-switch coverage, per-decision
recording, stop rules, and success criteria. Execution and approval remain
pending; no commands are auto-submitted and the gate remains **closed**.

The first manual display-only run is documented in
`manual_vnext_recommendation_test_observations.md` and did **not** meet the
recommendation-quality criteria: Tera and switching were rarely selected, a
forced switch chose the first option, and boosted Rage Fist was badly
under-valued versus Cresselia. Code inspection found that live v5 impact
resolution supplies Rage Fist to the damage calculator at its static 50 BP
without accumulated hit-count state, while the relevant damage-event count is
not represented for move actions. The simultaneous double-KO overlay ordering
bug was fixed so our live `forceSwitch` request takes priority over opponent
replacement waiting. Full-scale training and promotion remain blocked; the
gate remains **closed**.

The focused Rage Fist diagnostic (`rage_fist_impact_diagnostic.md`) confirmed a
live/training feature-semantic bug. Before the subsequent correction, v5 impact
resolved Rage Fist at its static 50 BP (~29.45% average in the controlled
Annihilape/Cresselia fixture) and did not change after a recorded hit; correct
one-hit power is 100 BP (~58.29%). Gunk Shot was ~23.43% with its 80% accuracy
represented separately.
Because even the bugged features favor Rage Fist on damage, accuracy, STAB, and
type effectiveness, the manual Gunk Shot choice also points to ranker
imitation/state-interaction weakness. Further training is blocked until a
schema-aware dynamic-power correction is designed and validated; the gate
remains **closed**.

Mechanics-repair batch 1 (`mechanics_repair_batch_1_fixed_multihit_accuracy.md`)
then cleared the highest-impact fixed-damage and multi-hit wrong-exact buckets
and made dynamic accuracy honest, moving the completeness audit from
121 PASS / 176 FAIL / 53 INEXACT to **123 PASS / 159 FAIL / 68 INEXACT**.
Seismic Toss and Night Shade route level-based fixed damage through the oracle
(PASS); Super Fang, Ruination, Endeavor, Mirror Coat and the 11 multi-hit moves
fail closed (`impact_unknown`) → INEXACT instead of wrong-exact; weather-dependent
accuracy (Blizzard, Thunder, Hurricane, Bleakwind Storm) is computed from the
observable weather and fails closed without weather context. Only move-id-keyed
routing in `resolve_action_impact` / `classify_action_category` changed; no
feature name, order, or dim changed and v6 stays 331D. No data was rematerialized,
no model trained or promoted, and no live default changed.

Mechanics-repair batch 2 (`mechanics_repair_batch_2_secondary_effects.md`) then
cleared the largest remaining FAIL group — secondary/status/stat/volatile
next-state — moving the completeness audit from 123 PASS / 159 FAIL / 68 INEXACT
to **123 PASS / 39 FAIL / 188 INEXACT**. A coarse, metadata-derived presence
detector (`move_next_state_effects`) fills the existing v6 next-state change flags
(`next_opp_status_change`, `next_own_status_change`, `next_opp_stat_change`,
`next_own_stat_change`) so a move with a real secondary/primary status, volatile,
or stat effect is no longer encoded as a wrong-exact "no change". Exact status
type, chance, and magnitude stay unrepresented, so these 120 moves (including the
four weather-accuracy moves) become INEXACT, not PASS; item-swap/copy/random-call
status moves are flagged as non-damaging and recorded as needing typed v7 fields.
Only feature **values** changed in `slice6_resolved_impact_feature_vector` plus
the new detector and the audit reclassification; no feature name, order, or dim
changed and v6 stays 331D. No data was rematerialized, no model trained or
promoted, and no live default changed.

Mechanics-repair batch 3 (`mechanics_repair_batch_3_dynamic_type_charge.md`) then
handled dynamic type/STAB and charge/delay timing, moving the completeness audit
from 123 PASS / 39 FAIL / 188 INEXACT to **131 PASS / 27 FAIL / 192 INEXACT**.
sim-core now returns the resolved (post-`calculate`) move type, so impact
type-effectiveness and STAB use the actual dynamic type — Weather Ball, Terrain
Pulse, Judgment, Ivy Cudgel, Raging Bull, Revelation Dance, Aura Wheel and Tera
Blast become PASS. Tera Starstorm fails closed (Stellar STAB/effectiveness not
representable). Two-turn charge / delayed moves no longer emit on-hit damage as
immediate: Solar Beam (sun/Power Herb) and Meteor Beam (Power Herb) are exact only
when they fire this turn and otherwise fail closed; Future Sight always fails
closed; Beak Blast is PASS (same-turn damage). sim-core's `DamageEstimate` gained
a `move_type_resolved` output, but no action-feature name, order, or dim changed
and v6 stays 331D; no v7 fields were added (a delayed-damage/charge-state pair and
a Stellar encoding are proposed for a future v7). No data was rematerialized, no
model trained or promoted, and no live default changed.

Mechanics-repair batch 4 (`mechanics_repair_batch_4_conditional_execution_history_power.md`)
then handled conditional execution/success and turn/history-conditional power,
moving the completeness audit from 131 PASS / 27 FAIL / 192 INEXACT to
**134 PASS / 9 FAIL / 207 INEXACT**. Moves whose success or power depends on the
opponent's same-turn action, the first-active turn, the user's form, the target's
item, within-turn order, or unplumbed prior-move-failure history now fail closed
(`impact_unknown`) instead of claiming damage (Fake Out, First Impression, Sucker
Punch, Thunderclap, Focus Punch, Double Shock, Hyperspace Fury, Poltergeist,
Payback, Avalanche, Lash Out, Stomping Tantrum, Temper Flare). Fusion Bolt /
Fusion Flare and Pollen Puff are PASS (their doubling / ally-heal branch cannot
occur in singles); Brick Break / Psychic Fangs keep exact screen-bypassing damage
and coarsely flag the screen removal via the existing `next_field_or_side_change`
field. No v6 schema field was added (a conditional-execution flag and turn-order /
prior-failure oracle plumbing are proposed for a future v7); only impact values
plus new move-id sets and the audit reclassification changed; v6 stays 331D. No
data was rematerialized, no model trained or promoted, and no live default
changed.

Mechanics-repair batch 5 (`mechanics_repair_batch_5_final_failures.md`) then
cleared the final 9 FAILs, moving the completeness audit to
**138 PASS / 0 FAIL / 212 INEXACT** — zero wrong-exact. PASS: Flower Trick /
Wicked Blow (guaranteed crit baked into the calc rolls; `crit_included=True`),
Freeze-Dry (sim-core reflects its special 2x-vs-Water effectiveness), Photon
Geyser (calc selects the higher attacking stat/category, verified exact).
Fail-closed because their damage is wrong-exact: Beat Up (calc returns 0) and
Fickle Beam (random double power). Kept exact damage with an unrepresented
next-state effect documented for v7: Knock Off (item removal), Bug Bite (stolen
berry), Grassy Glide (terrain +1 priority). The representative fidelity suite
stays 12 PASS / 0 FAIL. No action feature name/order/dim changed (v6 stays 331D);
sim-core's `DamageEstimate` gained the Freeze-Dry effectiveness override but no
action-feature schema field; no v7 fields were implemented. No data was
rematerialized, no model trained or promoted, and no live default changed.

**The mechanics-fidelity gate criterion (no wrong-exact FAIL) is now met.** The
gate nonetheless remains **closed** on the separate, approval-gated
training-readiness items below (stale v5/v6 data/checkpoint disposition,
value-label quality audit, larger-dataset value learning, live-loader hardening,
production checkpoint approval), which are unrelated to mechanics fidelity.

The post-FAIL=0 training-readiness review (`v7_v6_training_readiness_review.md`)
records the disposition and next steps. Decision: mechanics fidelity is ready, but
**training is not approved** — every materialized v5/v6 dataset and the v7/v5
rank-only checkpoint are stale for action-impact fidelity and provide no valid
baseline on the repaired pipeline, and the tiny v7/v6 materialization is only a
schema smoke artifact. Recommended next step (closed, pending approval): a small
**v7/v6 diagnostic_300 rematerialization** reusing the frozen 210/45/45 splits,
whose report must prove schema/fingerprint validation, a mechanics-clean impact
path, action match rate, the exact-vs-INEXACT candidate share, Tera/switch
candidate counts, and no stale-checkpoint reuse. Only after that passes, a tiny
rank-only training run on the fresh v7/v6 diagnostic_300 (plumbing/behavior
comparison only, no promotable checkpoint), with metrics broken down by
exact-impact, INEXACT, Tera, switch, non-damaging/status, and dynamic-mechanic
moves. Recommended INEXACT policy: keep INEXACT candidates with `impact_unknown=1`
and the coarse next-state flags intact and always report exact-vs-INEXACT
breakdowns; do not downweight or filter by default (those stay diagnostic-only
experiments). Value learning, live-default changes, and any production/live
promotion remain separately **closed**.

The recommended small rematerialization is now done
(`diagnostic_300_v7_v6_materialization_report.md`): the frozen `diagnostic_300`
split (210/45/45) was regenerated on the FAIL=0 impact path into the new
`artifacts/training_plan/datasets/diagnostic_300_v7_v6/` directory —
`live-private-belief-v7` (3208D, fingerprint `0a697b42…e36fbf`) +
`legal-action-v6` (331D, fingerprint `ac8fb3d3…73f049`, matching the frozen
schema). 300/300 battles valid, 25,396 states, 189,957 candidates, match rate
**96.96%** (24,624/772, identical to v5), all 18 validation checks passed, live
defaults recorded unchanged. Candidate mix: 38.9% move / 22.1% Tera / 39.0%
switch; among damaging-move candidates 94.2% resolve exactly and 5.8% are
fail-closed INEXACT (2.0% of all candidates), with `impact_unknown`/coarse flags
preserved per the INEXACT policy. The stale `diagnostic_300_v7_v5` dataset and the
v7/v5 rank-only checkpoint remain not-for-conclusions. **No training was run, no
checkpoint promoted, no live default changed, and no diagnostic_1000/full-scale
materialization occurred.** The gate stays **closed**; the next step (tiny
rank-only training on this fresh dataset with exact-vs-INEXACT/Tera/switch/
non-damaging/dynamic-mechanic breakdowns) remains approval-gated.

The deterministic rollout-parity harness
(`rollout_parity_harness_report.md`) now compares 18 fixed-seed bundled-Showdown
fixtures with local approximate transitions across immediate, end-of-turn,
switch-entry, and delayed-future phases. Result: **6 PASS / 0 FAIL / 12 explicit
GAP**. Showdown-confirmed focused fixes make Stealth Rock type-aware and Spikes
use the correct 1/8, 1/6, 1/4 layer fractions; Sticky Web entry Speed-drop
diagnostics are now exposed. Residual evolution, Future Sight queues,
weather/terrain residuals, and prevention callbacks remain explicit local gaps,
not guessed action-feature outcomes. No materialization, training, checkpoint
promotion, battle play, schema/default change, or live-path change occurred.
The rollout-parity and overall diagnostic training gates remain **closed**.

Rollout-parity batch 1 (`rollout_parity_batch_1_residuals_report.md`) adds a
focused Gen 9 end-of-turn kernel and expands the deterministic harness to 22
fixtures: **15 PASS / 0 FAIL / 7 explicit GAP**. Toxic ramping, regular poison,
burn, Leech Seed drain/heal, Salt Cure on normal/Water/Steel targets, ordinary
Sandstorm chip, and no-residual stability now match bundled Showdown fixtures.
Binding remains unavailable because current state lacks source activity/source
effect/duration/Binding Band divisor; exact opponent max HP, explicit Toxic
stage, Salt Cure current-state identity, and modifier provenance also remain
state-adapter requirements. No action schema/fingerprint, live default,
materialization, training, checkpoint, or promotion changed. Both gates remain
**closed**.

Rollout-parity batch 2 (`rollout_parity_batch_2_delayed_damage_report.md`) adds a
focused Future Sight/Doom Desire queue and expands the harness to **26 fixtures:
19 PASS / 0 FAIL / 7 explicit GAP**. Fixed-seed Showdown fixtures now verify no
immediate hit, the correct landing turn, target-slot behavior across a switch,
duplicate scheduling failure without overwrite, and Doom Desire's shared
mechanism. Resolution fails closed when the current slot occupant lacks exact
target-specific landing-damage provenance; approximate state still lacks a
general scheduled-attack damage resolver and full source/target/field
provenance. No action schema/fingerprint, live default, materialization,
training, checkpoint, or promotion changed. Both gates remain **closed**.

Rollout-parity batch 3
(`rollout_parity_batch_3_prevention_callbacks_report.md`) adds a focused
immediate-prevention helper and expands the harness to **32 fixtures: 27 PASS /
0 FAIL / 5 explicit GAP**. New PASS coverage includes Psychic Terrain priority
prevention plus non-priority/airborne non-blocking controls, Substitute blocking
Leech Seed, Misty Terrain status prevention, Electric Terrain sleep prevention,
and Damp blocking Explosion when the required local provenance is represented.
Magic Bounce reflection and broader Good as Gold status callback routing remain
explicit GAP because local rollout still lacks reflected-action/side-effect
provenance and generalized ability/status callback routing. No action
schema/fingerprint, live default, materialization, training, checkpoint, or
promotion changed. Both gates remain **closed**.

Rollout-parity batch 4
(`rollout_parity_batch_4_gap_triage_report.md`) triages the five remaining GAPs
and expands the harness to **33 fixtures: 29 PASS / 0 FAIL / 4 explicit GAP**.
Grassy Terrain healing is now PASS for represented grounded targets, with a
paired airborne no-heal PASS fixture and fail-closed behavior when grounding is
missing. Binding, Future Sight replacement damage without target-specific
landing damage, Magic Bounce reflection, and generalized Good as Gold status
blocking remain explicit GAPs with provenance requirements documented for
future execution/v7 work. No action schema/fingerprint, live default,
materialization, training, checkpoint, or promotion changed. Both gates remain
**closed**.

The v7 uncertainty/counter/distribution audit
(`v7_uncertainty_counter_distribution_audit.md`) was written before batch 7
implementation. It defines no-leakage representation requirements for sleep and
Rest counters, confusion counters, hit/miss/crit risk, branch-dependent moves,
random-call callable pools, multi-hit distributions, and residual/delayed
pressure. Recommended next work is an append-only v7 batch 7
action-risk/probability slice plus separate state-schema provenance for counters
and pending effects, with no-leakage tests before any materialization or
training. No action schema/fingerprint, live default, materialization, training,
checkpoint, or promotion changed. Both gates remain **closed**.

`legal-action-v7` batch 7
(`legal_action_v7_batch_7_action_risk_probability_implementation.md`) appends a
59-field action-risk/probability/provenance slice after the frozen 452D batch-6
prefix, producing a 511D schema with fingerprint
`c03b2dd345f47dae0bffefc2a0d2b5731ee7d1eb8f2bf4cabc8d415d183149f5`. The first
452 names and values preserve the batch-6 fingerprint
`e3e39124cd24e3e27684306e3d401859083df65965e721eb3e5e8b89c48fcb4c`. New fields
cover hit/miss/crit summaries, branch-dependent pressure, random-call/callable
pools, multi-hit distributions, and delayed/residual pressure. Sleep/confusion
counters and pending-effect provenance remain deferred to state-schema/rollout
work. No materialization, training, checkpoint, promotion, live default, or live
path changed. Both gates remain **closed**.

`legal-action-v7` batch 8
(`legal_action_v7_batch_8_forced_decision_secondary_chance_implementation.md`)
appends a 41-field forced-decision/replacement/item-trigger/secondary-chance
slice after the frozen 511D batch-7 prefix, producing a 552D schema with
fingerprint `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`.
The first 511 names and values preserve the batch-7 fingerprint
`c03b2dd345f47dae0bffefc2a0d2b5731ee7d1eb8f2bf4cabc8d415d183149f5`. New fields
cover self-pivot follow-up replacement decisions, self-KO/sacrifice replacement
pressure, phazing, known Eject Button/Eject Pack/Red Card switch triggers, and
base-vs-modified secondary chances including Serene Grace, Shield Dust, Covert
Cloak, and Sheer Force provenance. NatDex/old-generation behavior remains
documented but unimplemented. No materialization, training, checkpoint,
promotion, live default, or live path changed. Both gates remain **closed**.

The source-driven Showdown mechanics edge-case inventory
(`showdown_mechanics_edge_case_inventory.json` and
`showdown_mechanics_edge_case_inventory_report.md`) now scans the local bundled
Pokemon Showdown source, mod overrides, `sim/dex-moves.ts`, and local sim-core
wrappers. It records **155 source files**, **6,473 hook/field occurrences**, and
**75 classified mechanics entries**, with the top next actions split across
rollout parity batch 5, state-schema/provenance design, v7 batch 9,
format-scoped adapters, and deferred NatDex/old-gen backlog. This was an
inventory/report task only: no schema, code path, materialization, training,
checkpoint, promotion, live default, or live path changed. Both gates remain
**closed**.

Rollout-parity batch 5
(`rollout_parity_batch_5_inventory_gap_closure_report.md`) expands the
deterministic harness to **45 fixtures: 37 PASS / 0 FAIL / 8 explicit GAP**.
New PASS coverage includes binding residual with complete source/effect/duration
and divisor provenance, Binding Band divisor behavior, Powder Fire-move
prevention, Sucker Punch and Thunderclap explicit branch handling, and Doom
Desire replacement-target landing damage when target-specific damage is
provided. Future Sight/Doom Desire without replacement-specific damage, Magic
Bounce reflection, generalized Good as Gold blocking, and exact Population Bomb
/ Triple Axel per-hit execution remain explicit GAPs. No schema/fingerprint,
live default, live bot behavior, materialization, training, checkpoint, or
promotion changed. Both gates remain **closed**.

The state/provenance design for the remaining GAPs
(`state_provenance_schema_design_for_remaining_gaps.md`) specifies the state and
provenance needed to close the 8 honest GAPs and to support future
materialization safely. It groups the GAPs into four mechanics (delayed landing
resolver, reflection routing, ability/status prevention routing, exact
sequential multi-hit) plus forward-looking status counters/ranges,
damage-received memory, and last-move/callable-pool provenance, with a per-GAP
table (missing provenance, proposed representation, owner layer, no-leakage
concern, batch) and an owner-layer vocabulary (live state extraction, tactical
state, rollout state, action features, search node, oracle fixture only). The
recommended order is batch A (no-leakage tests + provenance helpers), B (delayed
landing resolver), C (ability/prevention/reflection routing), D (status
counters/damage memory), E (exact multi-hit traces). Binding rules keep
sampled/hidden values out of features and preserve fail-closed/0-FAIL over GAP
reduction. This was a design/audit pass only: no `legal-action-v7` schema/dim/
fingerprint change (stays 552D), no state schema implemented, no materialization,
training, checkpoint promotion, live default, or live-path change. Both gates
remain **closed**.

Batch A (no-leakage tests + minimal provenance helper contracts) is now
implemented as an isolated guardrail layer ahead of the full state schema:
`trainer/src/neural/provenance_contracts.py` (small, torch-free, no simulator
rewrite) plus `trainer/tests/test_state_provenance_no_leakage_contracts.py`
(23 tests). It enforces five contracts: (1) delayed-landing resolvability fails
closed and never reuses the original target's damage for a replacement occupant
— verified against the production `resolve_delayed_attacks`; (2) natural
sleep/confusion expose only a public range with `hidden_duration_unknown` while
Rest is fixed-duration, and a structural guard rejects any leaked sampled wake
turn; (3) ability knownness is tri-state (known/inferred/unknown) with
suppressed/ignored handling, so an unrevealed ability is never assumed to be (or
not be) Good as Gold; (4) Magic Bounce reflection fails closed without complete
source/reflector/destination/target/effect provenance and a known reflector
ability; (5) exact sequential multi-hit refuses a missing per-hit trace and
rejects a distribution summary as an exact trace. No GAP was closed (still
8 GAP), no `legal-action-v7`/state/action schema changed, no materialization,
training, checkpoint promotion, live default, or live-path change occurred.
Both gates remain **closed**.

The approved `diagnostic_300_v7_v7` baseline materialization completed from
source commit `63484055aad7b5d45102fa53e431fe682cc3bb45` in 290.73 seconds
with 6 workers: **300/300 valid battles, 0 failed**, 25,396 state rows and
189,957 action candidates. Battle splits are exactly 210/45/45 with no split
crossing. Built-in and independent validation passed for
`live-private-belief-v7` 3208D and `legal-action-v7` 552D /
`956da3d2…1bf39d7`, embedded names/fingerprints, float16 layout, manifest
traceability, candidate indices, state/action-rank labels, unchanged live
defaults, and zero action-value labels. Action matching is 24,624 / 25,396
(96.96%); 772 unmatched groups remain explicitly audited/excluded. All 300
per-battle shards remain for resume. The previous v7/v6 NPZ hash is unchanged.
Generated dataset artifacts remain unstaged. This completes only the approved
diagnostic materialization; no training, checkpoint promotion, live-default,
live-bot, action/state schema, or v8 change occurred. The possible-threat
limitations and 8 honest rollout GAPs remain. Both training and production/live
gates remain **closed**.

Rollout-parity batch 6 (`rollout_parity_batch_6_delayed_landing_resolver_report.md`)
implements design group 1 (delayed landing resolver) and expands the harness to
**47 fixtures: 39 PASS / 0 FAIL / 8 explicit GAP**. A landing-time
resolver-bundle provenance path lets Future Sight / Doom Desire resolve a
replacement occupant's exact damage only when a complete bundle (source/move/
occupant-matched `target_snapshot`/field + a Showdown-derived exact
`landing_damage`) is present; the decision is centralized in
`provenance_contracts.delayed_landing_resolvable`, which never reuses
original-target damage and rejects a bundle built for a different occupant
(`resolver_target_mismatch`). Two new PASS fixtures
(`future_sight_resolver_bundle_replacement`,
`doom_desire_resolver_bundle_replacement`) were added; the two
`*_replacement_damage_unavailable` cases **stay GAP** (they carry only
original-target damage), so GAP count is unchanged and no GAP was closed by
weakening correctness. Oracle-derived `landing_damage` stays fixture/queue-only
and is never flattened into action/state features. Tests: sim-core build + 35
sim-core tests, 28 no-leakage contract tests, 17 harness tests, JSON valid,
`git diff --check` clean. No `legal-action-v7`/state/action schema change (v7
stays 552D), no materialization, training, checkpoint promotion/file, live
default, or live bot behavior change; no NatDex/old-gen mechanics. Both gates
remain **closed**.

Rollout-parity batch 7 (`rollout_parity_batch_7_ability_reflection_routing_report.md`)
implements design groups 2 (reflection routing) and 3 (ability/status prevention
routing) and expands the harness to **49 fixtures: 41 PASS / 0 FAIL / 8 explicit
GAP**. `provenance_contracts.py` gained `effective_ability_from_state`
(tri-state knownness + suppressed/ignored; hides unrevealed ability identity) and
`resolve_status_move_ability_block`; `prevention.py` adds a known-active Good as
Gold status block and Magic Bounce reflection routing through
`validate_reflection_provenance` (complete → `reflected=True` + destination side;
incomplete/unknown/suppressed/ignored → fail closed), and `_compare_immediate`
now checks `reflected`/`blocked`. Two new PASS fixtures
(`good_as_gold_known_blocks_status`, `magic_bounce_reflects_stealth_rock`) were
added; the unknown/incomplete `good_as_gold_status_gap` and
`magic_bounce_reflection_gap` **stay GAP**, so GAP count is unchanged and no GAP
was closed by weakening correctness. Unrevealed abilities and reflection payloads
stay transition/fixture-only and are never flattened into action/state features.
Tests: sim-core build + 35 sim-core tests, 43 no-leakage contract tests, 17
harness tests, JSON valid, `git diff --check` clean. No `legal-action-v7`/state/
action schema change (v7 stays 552D), no materialization, training, checkpoint
promotion/file, live default, or live bot behavior change; no NatDex/old-gen
mechanics. Both gates remain **closed**.

The public-information belief & effective-context design
(`public_information_belief_effective_context_design.md`) adds a contract+test
guardrail layer so the model receives the same *category* of information a
skilled Showdown player has (known species, possible abilities/items, speed
ranges, revealed/inferred public info) but never hidden truth before it is
revealed. It grounds in the existing extraction (which already separates
revealed `known_abilities`/`item_known`/`revealed_moves_by_species` from
`opponent_belief` possibility candidates) and formalizes the
known/possible/inferred/hidden split plus effective mechanics. New pure,
torch-free helpers in `provenance_contracts.py`: `PublicAbilityBelief`,
`PublicItemBelief`, `PublicSpeedBelief`, `EffectiveAbilityContext`,
`EffectiveItemContext` + `item_blocks`, `EffectiveWeatherContext` — all applying
suppression/bypass/blocking (Mold Breaker, Neutralizing Gas, Gastro Acid,
Ability Shield, Cloud Nine/Air Lock, Heavy-Duty Boots, Safety Goggles, Covert
Cloak, Magic Room) only when known active and failing closed on unknown. Backed
by `test_public_information_belief_contracts.py` (25 tests); existing 43
no-leakage contract tests still pass. This is a design/guardrail pass only: no
live-extraction rewrite, no `legal-action-v7`/state/action schema change, no
materialization, training, checkpoint promotion/file, live default, or live bot
behavior change; no NatDex/old-gen mechanics. Both gates remain **closed**.

Effective-context known-modifier wiring
(`effective_context_known_modifier_wiring_report.md`) then wired a first narrow
slice of these contracts into prevention, verified against bundled Showdown, and
expanded the harness to **52 fixtures: 44 PASS / 0 FAIL / 8 explicit GAP**. A
known Mold Breaker / Teravolt / Turboblaze source bypasses a known Good as Gold
unless the holder has a known Ability Shield (`source_ignores_target_abilities`,
`_holds_known_item`; matches `sim/battle.ts suppressingAbility`), and a known
Safety Goggles blocks a powder move (`item_belief_from_state` + `item_blocks`).
Three new PASS fixtures (`good_as_gold_bypassed_by_known_mold_breaker`,
`ability_shield_protects_good_as_gold_from_mold_breaker`,
`safety_goggles_blocks_powder_move`); GAP count unchanged, 0 FAIL preserved.
Heavy-Duty Boots (hazards) and Safety Goggles (weather chip) were already
represented; Cloud Nine / Air Lock, Neutralizing Gas harness coverage, and
Covert Cloak / Shield Dust secondary blocking remain deferred (unit-tested at the
contract level). Unknown ability/item is never assumed (no leakage of hidden
truth). Tests: sim-core build + 35 sim-core tests, 36 belief tests, 43 no-leakage
contract tests, 17 harness tests, JSON valid, `git diff --check` clean. No
`legal-action-v7`/state/action schema change (v7 stays 552D), no live-extraction
rewrite, no materialization, training, checkpoint promotion/file, live default,
or live bot behavior change; no NatDex/old-gen mechanics. Both gates remain
**closed**.

Effective-context batch 2
(`effective_context_batch_2_weather_suppression_secondary_blocking_report.md`)
then wired known Cloud Nine / Air Lock weather suppression and known Neutralizing
Gas ability suppression, verified against bundled Showdown, expanding the harness
to **55 fixtures: 47 PASS / 0 FAIL / 8 explicit GAP**. The Sandstorm chip in
`end_of_turn` is gated through `EffectiveWeatherContext` on a
`weather_negator_known` flag (matches `Field.effectiveWeather` /
`suppressingWeather`); a known active Neutralizing Gas suppresses Good as Gold in
`apply_immediate_prevention` (`neutralizing_gas_suppresses_target`) unless a known
Ability Shield protects (matches `Pokemon.ignoringAbility`). Three new PASS
fixtures (`sandstorm_suppressed_by_cloud_nine`,
`neutralizing_gas_suppresses_good_as_gold`,
`ability_shield_protects_good_as_gold_from_neutralizing_gas`); GAP unchanged,
0 FAIL preserved. A `secondary_effect_blocked` contract (Covert Cloak / Shield
Dust) is added and unit-tested but harness-deferred — the local rollout has no
secondary-effect application phase, documented as the missing routing. Unknown
negator/gas/item is never assumed. Tests: sim-core build + 35 sim-core tests, 49
belief tests, 43 no-leakage contract tests, 17 harness tests, JSON valid,
`git diff --check` clean. No `legal-action-v7`/state/action schema change (v7
stays 552D), no live-extraction rewrite, no materialization, training, checkpoint
promotion/file, live default, or live bot behavior change; no NatDex/old-gen
mechanics. Both gates remain **closed**.

Rollout-parity batch 8 / Batch E
(`rollout_parity_batch_8_sequential_multihit_trace_report.md`) implements the
exact sequential multi-hit design group as an oracle-trace-driven exact replay
and expands the harness to **59 fixtures: 51 PASS / 0 FAIL / 8 explicit GAP**. A
new `multihit_trace.py` (`validate_sequential_multihit_trace`,
`execute_sequential_multihit`) replays a complete per-hit trace with stop-on-miss
and consistency checks and refuses a distribution/expected-hit summary;
`rollout_parity.py` gains a `sequential_multihit` phase handler. Four new PASS
fixtures (Population Bomb / Triple Axel exact + stop-on-miss, built from real
Showdown logs, incl. the 20/40/60 Triple Axel ramp); the four summary-only `*_gap`
fixtures **stay GAP**, so GAP count is unchanged and no GAP was closed by
weakening correctness. The per-hit trace is fixture-only transition provenance,
never a model feature; no PRNG simulator was added. With this, all four original
remaining-GAP design groups (delayed landing resolver, reflection routing,
ability/status prevention, exact multi-hit) have a provenance-safe exact path; the
remaining 8 GAP fixtures are the honest under-determined cases. Tests: sim-core
build + 35 sim-core tests, 52 state-provenance + multihit contract tests, 49
belief tests, 18 harness tests, JSON valid, `git diff --check` clean. No
`legal-action-v7`/state/action schema change (v7 stays 552D), no live-extraction
rewrite, no materialization, training, checkpoint promotion/file, live default,
or live bot behavior change; no NatDex/old-gen mechanics. Both gates remain
**closed**.

The v7/v7 materialization readiness review
(`v7_v7_materialization_readiness_review.md`) finds the project **ready for an
explicitly approved** small v7/v7 diagnostic materialization (state
`live-private-belief-v7` 3208D + action `legal-action-v7` 552D /
`956da3d2…1bf39d7`): the schema is frozen and fingerprint-tested, mechanics are
FAIL-free (138 PASS / 0 FAIL / 212 INEXACT, zero wrong-exact), rollout parity is
**59 fixtures: 51 PASS / 0 FAIL / 8 GAP** with only honest fail-closed GAPs, the
no-leakage and public-belief/effective-context contracts are in place, and the
generalized materializer is parallel/crash-safe/resumable. Its CLI now accepts
v7, records and validates the 552D exact fingerprint, and shares v6 repeat-chain
impact handling without changing v5. Focused temp/in-memory tests cover mocked
full-manifest CLI dispatch, metadata/array guardrails, unknown-version
rejection, and the byte-identical v6 Rollout prefix inside v7. The materializer
has no `--validate-only` CLI flag; use its read-only preflight function before
approval.
Proposed (not run): a `diagnostic_300_v7_v7` dataset on the same frozen
210/45/45 manifest/splits, written to a new output dir with `--full-manifest`
and retained per-battle shards. Training, checkpoint promotion, and any
live-default change remain separately **blocked**. No schema, dataset,
materialization, training, checkpoint, or live-default change occurred. A
fresh green preflight/test gate and explicit approval remain required. Both
gates remain **closed**.

The possible mechanic-threat awareness audit finds v7 sufficient for an
explicitly approved small diagnostic baseline, but not a complete threat-aware
training schema. Existing state/action features expose setup/stat deltas,
current boosts, species/Illusion identity, exact own facts, known effective
mechanics, and an explicit known-or-possible absorb-ability risk bit. Possible
Unaware, Magic Bounce, Good as Gold, Levitate, Covert Cloak, Shield Dust, and
Inner Focus are missing or only indirectly species-learnable; batch-8
`*_possible` secondary-blocker fields currently require known target state. A
future append-only `legal-action-v8` action-conditioned threat slice is
recommended before durable threat-aware training. The v7/v7 diagnostic
materialization verdict remains approval-gated and unchanged, with the explicit
limitation that v7 is only partially possible-threat-aware. No schema, dataset,
materialization, training, checkpoint, live default, or live behavior changed.
Both gates remain **closed**.

Pre-materialization skilled-player information calibration is complete at the
pure contract/test layer. A reliable singleton species/format ability set now
becomes deterministic public inference (Gholdengo → Good as Gold); ambiguous
sets stay unknown/possible, and unresolved Illusion blocks species-derived
collapse. Own legal-request ability/item/moves/Tera are exact known facts.
Explicit item reveals are known, deterministic deductions may be inferred, one
probabilistic non-flinch does not infer Covert Cloak, and speed ranges never
surface exact hidden speed. Existing Neutralizing Gas, Mold Breaker, Ability
Shield, and Safety Goggles effective-context behavior is preserved. The
readiness verdict is unchanged; no materialization, training, checkpoint, live
default, live bot, state schema, or `legal-action-v7` change occurred. Both
gates remain **closed**.

The read-only `diagnostic_300_v7_v7` dataset quality audit confirms a sound
archive and frozen schema: 25,396 finite 3208D state rows, 189,957 finite 552D
candidate rows, exact `956da3d2…1bf39d7` action fingerprint, exact 210/45/45
battle splits, internally consistent candidate indices/labels, and a
byte-identical v6 prefix. It remains useful for schema, prefix, distribution,
and feature-coverage diagnostics. It is **not approved for smoke training**:
772 states have no matched action (96.96% match), 769 of those are in train,
one replay contributes 253 after roster reconstruction diverges, no forced
switches are represented, and ordinary opponent species are marked uncertain
in 25,381 / 25,396 states. Exact-own/public-belief calibration is therefore
largely contract-level in this replay materialization path, while possible
Unaware/Magic Bounce/Good as Gold/Levitate/secondary-blocker gaps remain.
Fix and integration-test replay-state/materializer reconstruction before any
approved rematerialization or training; do not add v8 first because it would
not repair these data-quality defects. No dataset was changed, no training ran,
and no checkpoint/live/schema setting changed. Training and production/live
gates remain **closed**.

The primary reconstruction blocker fix identified
`gen9randombattle-2591563263` as a custom 24-vs-24 battle that slipped into the
standard six-slot manifest. Its shard has 253 unmatched states because later
team members cannot be represented. Replay profiling now makes explicit team
sizes above six ineligible, full preflight rejects them, and per-battle
materialization fails clearly if preflight is bypassed. Ordinary switch/drag
events now keep their public displayed species known instead of activating the
Illusion guard globally; explicit guards still block singleton ability
collapse, ordinary Gholdengo can infer Good as Gold, and ambiguous sets remain
unknown. The old dataset and manifest are stale for training: retain the
artifact, replace the unsupported train replay, and rematerialize only after
explicit approval. Subtracting the custom replay leaves 519 old-artifact
matcher limitations to remeasure. No training, rematerialization, checkpoint,
live, schema, or v8 change occurred. Both gates remain **closed**.

The corrected manifest preflight replaced that train replay with
`gen9randombattle-2591433931` in
`artifacts/training_plan/manifests/diagnostic_300_v7_v7_corrected_manifest.json`.
The original manifest was not overwritten, validation/test splits were left
unchanged, split counts remain 210/45/45, and read-only full preflight passes
with zero unsupported team-size replays. The old `diagnostic_300_v7_v7`
dataset remains stale and prohibited for training because it was materialized
before the team-size and displayed-species knownness fixes. A clean v7/v7
rematerialization is now ready for explicit approval, followed by a new quality
audit before smoke training. No full materialization, training, checkpoint,
live, schema, or v8 change occurred. Both gates remain **closed**.

The explicitly approved corrected v7/v7 rematerialization completed in
`artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected` with 300/300
valid battles, 0 failures, exact 210/45/45 battle splits, 25,235 states,
191,667 candidates, 300 retained shards, and the frozen 552D action fingerprint
`956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`. The
quality audit (`diagnostic_300_v7_v7_corrected_dataset_quality_audit.md`) shows
24,716 matched / 519 unmatched decisions (97.94%), removes the unsupported
24-vs-24 replay cluster, and reduces displayed-species uncertainty from
25,381 stale states to 0 corrected states. The stale
`diagnostic_300_v7_v7` artifact was not overwritten and remains prohibited for
training. No training, checkpoint promotion, live-default/live-bot change,
schema change, push, or v8 work occurred. Corrected materialization is complete;
smoke training remains pending a separate explicit gate decision. Production
and live gates remain **closed**.

The residual unmatched-state audit
(`diagnostic_300_v7_v7_corrected_unmatched_state_audit.md`) explains all 519
remaining skipped labels as missing-candidate cases: 486 missing reconstructed
active moves and 33 missing switch targets, with zero exact parsed actions
already present in the candidate list. The skips are concentrated in train
(516 train / 1 validation / 2 test). Replacement replay
`gen9randombattle-2591433931` contributes zero residual unmatched labels; its
21 broader legacy-audit rows were 19 fixed rows plus 2 intentional initial
deployments. This makes an explicitly approved tiny smoke training run
acceptable as plumbing/overfit sanity only, not as a durable quality baseline.
Before larger training, fix the remaining move-list and roster/form alias
reconstruction gaps and rematerialize only with explicit approval. Production
and live gates remain **closed**.

The missing-candidate reconstruction source fix
(`missing_candidate_reconstruction_fix_report.md`) is now complete. It keeps the
552D `legal-action-v7` schema and fingerprint unchanged, prevents `Struggle`
from displacing real active moves, merges safe battle-form roster aliases,
matches switch labels by roster identity, and preserves no-leakage/Illusion
guards. A lightweight replay-prefix audit over the old 519 skipped rows now
naturally matches 485 and leaves 34 ambiguous/no-leakage residuals. The
materialized `diagnostic_300_v7_v7_corrected` dataset was not rematerialized,
so it remains stale with respect to this source fix; smoke training remains
blocked until a future explicitly approved rematerialization and audit.

The residual-34 triage
(`residual_34_unmatched_case_triage_report.md`) then audited those 34 rows
directly and fixed all safe Category A cases: stale-fainted Revival Blessing
switch targets and public Illusion `replace` / active-stint identity handling.
The source-level lightweight audit now matches 511 of the old 519 residual rows
and leaves 8 rows: 5 no-leakage move cases and 3 unsupported Illusion duplicate
switch artifacts. Source is ready for an explicitly approved rematerialization,
but smoke training remains blocked until the fresh artifact is materialized and
passes audit. Production and live gates remain **closed**.

The Transform/Imposter reconstruction fix
(`transform_imposter_reconstruction_fix_report.md`) then resolved the one
residual the residual-8 verification found still fixable:
`gen9randombattle-2589571474` turn 20 p1 `move: Thunder Wave`. It was a real
Ditto/Imposter reconstruction bug — copied moves were merged across three
Transform stints and a future `Leaf Blade` was pulled from a later Virizion
stint, displacing `Thunder Wave`. `-transform` is now parsed as a typed event,
the completed-team builder no longer attributes copied moves to the base species,
and a stint-scoped helper reconstructs the current Transform stint's copied
moveset (own-side future-reveal applies within a stint, never across stints).
`Thunder Wave` now matches without adding a fifth move; the Ho-Oh stint stays
stint-scoped; Ditto's global moveset is no longer backfilled with copied opponent
moves. `legal-action-v7` is unchanged (552D / `956da3d2…1bf39d7`). A new
read-only harness, `scripts/recompute_v7_v7_residual_unmatched_from_replays.py`,
makes the residual analysis reproducible and now reports 1 matched (Ditto) and 7
unmatched. The expected residual count after a future approved rematerialization
is therefore **7**, not 8 (4 pre-reveal Illusion move cases + 3 unsupported
Illusion duplicate switch artifacts); the never-revealed-Zoroark public-replay
ambiguity is an irreducible public-replay limitation, not a live-play one.
Rematerialization is still required before smoke training. No training,
rematerialization, checkpoint promotion, live-default/live-bot change, schema/v8
change, or push occurred. Production and live gates remain **closed**.

The Zoroark/Illusion actor-private reconstruction
(`illusion_zoroark_actor_private_reconstruction_report.md`) then fixed 6 of the 7
remaining Illusion residuals by reconstructing the acting Zoroark user's own true
identity, which is an own-side fact the actor knew at decision time. A stint that
self-confirms via a later `replace` (reveal before the next switch for that side)
is reconstructed as its true species: own move decisions de-disguise the active
(`gen9randombattle-2591469202` t1 `Sludge Bomb`; `gen9randombattle-2593348981` t6
and t18 `Will-O-Wisp`), and own duplicate-Illusion switch decisions are relabeled
from the displayed `switch: Houndstone` to the true `switch: Zoroark`
(`gen9randombattle-2591404793` t21/t23/t25), an already-legal bench candidate with
no switch-to-active-displayed-species candidate added. One row is quarantined:
`gen9randombattle-2593348981` t1 `Will-O-Wisp`, whose "Avalugg" stint switched out
before any reveal and is publicly indistinguishable from the player's real
Avalugg — an irreducible public-replay attribution limitation, not leakage. The
opponent's pre-reveal belief never receives the true species; the impossible
displayed-species contradiction/suspicion signal is documented as future
`legal-action-v8` threat-awareness work (no schema change). `legal-action-v7`
stays 552D / `956da3d2…1bf39d7` and no state dim changed. The residual
recomputation harness now reports 8 cases, 7 matched, 1 unmatched
(`{transform_reconstruction_fixed: 1, actor_private_illusion_fixed: 6,
unsupported_or_quarantined: 1}`, all-as-expected). The expected residual count
after a future approved rematerialization is therefore **1**. Rematerialization
is still required before smoke training. No training, rematerialization,
checkpoint promotion, live-default/live-bot change, schema/v8/old-gen change, or
push occurred. Production and live gates remain **closed**.

The explicitly approved **post-Illusion v7/v7 rematerialization** then ran from
source commit `4cde8bd15ff71021d57e582d8eb808da1f11bbad` into
`artifacts/training_plan/datasets/diagnostic_300_v7_v7_post_illusion`
(`diagnostic_300_v7_v7_post_illusion_materialization_report.md`): 300/300 valid
battles, 0 failed, 291s, 25,235 states, 197,429 candidates, exact 210/45/45
splits, 300 retained shards, `live-private-belief-v7` 3208D +
`legal-action-v7` 552D / `956da3d2…1bf39d7`, all 18 validation checks passed, live
defaults unchanged, 0 action-value labels, displayed-species uncertainty 0/25,235.
Match rate rose from the corrected 97.94% (519 unmatched) to **99.94% (15
unmatched)** — all `move`-kind explicit skips, no wrong labels. The quality audit
(`diagnostic_300_v7_v7_post_illusion_dataset_quality_audit.md`) confirms every
documented fix landed in the artifact (Ditto `Thunder Wave`; actor-private
`Sludge Bomb` and `Will-O-Wisp` t6/t18; duplicate Houndstone→`Zoroark` switches
t21/t23/t25 all matched) and categorizes the 15 residuals: **3 irreducible
non-self-confirming Illusion stints** (the documented quarantined Avalugg row, its
same-stint Poltergeist companion, and one new instance — Gumshoos/Zoroark-Hisui in
`gen9randombattle-2593283718` t3), **11 from a newly-surfaced fixable Ditto/Imposter
re-transform-into-same-species bug** (Sacred Fire, Energy Ball, Outrage; the stint
anchor in `_active_transform_copied_moves` collides on identical re-transform
`raw`), and **1 Struggle PP-exhaustion** explicit skip. The expected "1" applied
only to the 8 documented rows; the full materialization surfaces the additional
Ditto/Illusion patterns. Old datasets were not overwritten (byte-identical
`.npz`). A tiny smoke/plumbing run is acceptable on this artifact if approved
(0.06% excluded rows inject no error); durable training should wait for the
category-B Ditto re-transform fix + another rematerialization. `legal-action-v7`
stays 552D / `956da3d2…1bf39d7`; no state dim changed. No training, checkpoint
promotion, live-default/live-bot change, schema/v8/old-gen change, or push
occurred. This supersedes `diagnostic_300_v7_v7_corrected` for quality purposes.
Production and live gates remain **closed**.

The Ditto/Imposter re-transform-into-same-species fix
(`ditto_retransform_same_species_fix_report.md`) then resolved 12 of the 15
post-Illusion residuals in source. `_active_transform_copied_moves` now anchors the
current Transform stint by event object identity instead of `raw` string (identical
`-transform` markers on re-transform into the same species had bound it to the
earliest occurrence and stopped at the intervening switch). The 11 Ditto rows
(Sacred Fire x3, Energy Ball x4, Outrage x4) now match, with no cross-stint merge
(the re-transform Entei stint copies `Sacred Fire` but not the earlier stint's
`Stone Edge`), Ditto's global moveset still not backfilled, and the prior
`gen9randombattle-2589571474` `Thunder Wave` case (with `Leaf Blade` still absent)
preserved. The single `Struggle` row (`smogtours-gen9randombattle-929481` t65) is
also resolved: with the corrected stint the active's replay-observed `Struggle` is
surfaced and the existing exhaustion fallback emits a schema-safe `move: Struggle`
candidate (a deterministic forced action; no illegal candidate, no schema change).
The residual recomputation harness now covers all 22 post-Illusion residuals and
reports 19 matched / 3 unmatched, `all_as_expected = True`. The **expected residual
count after a future approved rematerialization is now 3** — the irreducible
non-self-confirming Illusion stints. This is a source/test/report change verified by
replay-prefix recomputation; the checked-in `diagnostic_300_v7_v7_post_illusion`
dataset is unchanged (still 15) until a future explicitly approved
rematerialization. `legal-action-v7` stays 552D /
`956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`; no state dim
changed. No training, rematerialization, checkpoint promotion,
live-default/live-bot change, schema/v8/old-gen change, or push occurred. Production
and live gates remain **closed**.

The explicitly approved **post-Ditto v7/v7 rematerialization** then ran from source
commit `01f14d6c04097b757f7a0435bc4eb3bf039ab768` into
`artifacts/training_plan/datasets/diagnostic_300_v7_v7_post_ditto`
(`diagnostic_300_v7_v7_post_ditto_materialization_report.md`): 300/300 valid
battles, 0 failed, 230.5s, 25,235 states, 197,449 candidates, exact 210/45/45
splits, 300 retained shards, `live-private-belief-v7` 3208D + `legal-action-v7`
552D / `956da3d2…1bf39d7`, all 18 validation checks passed, live defaults
unchanged, displayed-species uncertainty 0/25,235. Match rate rose from the
post-Illusion 99.94% (15 unmatched) to **99.99% (3 unmatched)** — exactly the
expected residual. The quality audit
(`diagnostic_300_v7_v7_post_ditto_dataset_quality_audit.md`) confirms every fix
landed in the artifact: the 11 Ditto re-transform rows (Sacred Fire/Energy
Ball/Outrage) matched, the Struggle row matched, the prior Thunder Wave Transform
case matched (Leaf Blade still absent), and the actor-private Zoroark/Illusion move
and duplicate-Houndstone-switch cases matched. The **only 3 remaining residuals**
are the irreducible non-self-confirming Illusion stints
(`gen9randombattle-2593348981` t1 `Will-O-Wisp` and t2 `Poltergeist`;
`gen9randombattle-2593283718` t3 `Hyper Voice`) — explicit quarantined skips, no
wrong labels. Action/state feature name vectors are byte-identical to
`diagnostic_300_v7_v7_post_illusion` (schema unchanged; v6 prefix names identical).
Old datasets were not overwritten (byte-identical `.npz`). This is the cleanest
v7/v7 artifact to date and the recommended baseline for a first tiny
smoke/plumbing training run if explicitly approved. `legal-action-v7` stays 552D /
`956da3d2…1bf39d7`; no state dim changed. No training, checkpoint promotion,
live-default/live-bot change, schema/v8/old-gen change, or push occurred. This
supersedes `diagnostic_300_v7_v7_post_illusion` for quality purposes. Production and
live gates remain **closed**.

The explicitly approved **post-Ditto v7/v7 smoke/plumbing training run** then
completed on CUDA with exit code 0 from
`training_runs/smoke_v7_v7_post_ditto/smoke_v7_v7_post_ditto_config.json`.
It used the post-Ditto `.npz` above with exact `live-private-belief-v7` 3208D
and `legal-action-v7` 552D metadata/fingerprints, trained state-value and
action-rank heads for one epoch (2,569 steps), and passed the tiny overfit
check. Train value MSE was 1.295563. Validation value MSE was 1.483368;
validation rank NLL/top-1/top-3 were 1.383279 / 0.434146 / 0.838137. Test value
MSE was 1.478658; test rank NLL/top-1/top-3 were
1.414682 / 0.410626 / 0.815486. Both generated checkpoints contain the exact
schema versions, 3208/552 dimensions, ordered-name fingerprints, manifest
checksum, epoch/global-step metadata, and `production_eligible: false`; all
report values, dataset arrays, and checkpoint tensors are finite. See
`training_runs/smoke_v7_v7_post_ditto/smoke_v7_v7_post_ditto_report.md`.
This closes only the tiny smoke/plumbing gate. The value metric does not beat
the constant baseline, so durable training, checkpoint promotion, live use,
and production remain **closed**. No live/default behavior changed.

The approved **1,000-battle post-Ditto v7/v7 materialization** then completed
from `manifests/diagnostic_1000_v7_v7_post_ditto_manifest.json` into
`datasets/diagnostic_1000_v7_v7_post_ditto`: 1,000/1,000 valid battles,
80,644 states, 617,687 candidates, exact 700/150/150 battle splits,
`live-private-belief-v7` 3208D plus `legal-action-v7` 552D /
`956da3d2…1bf39d7`, 1,000 retained shards, and all 18 structural validation
checks passed. The fresh manifest excludes the stale 24-vs-24 and 8-vs-8
replays; old datasets remain byte-identical. Match quality is 80,601 matched /
43 unmatched (99.9467%). Semantic audit classifies 41 as explicitly
quarantined non-self-confirming Illusion/public-replay ambiguity and two as a
new fixable Magic Bounce category: reflected Defog contaminates Hatterene's
moveset and crowds out Psychic, while reflected Will-O-Wisp is parsed as an
actor decision. See
`diagnostic_1000_v7_v7_post_ditto_materialization_report.md` and
`diagnostic_1000_v7_v7_post_ditto_dataset_quality_audit.md`.
Structural materialization passed, but rank-only training remains **closed**
pending the Magic Bounce fix, regression tests, approved rematerialization, and
re-audit. No training, promotion, live/default, schema, or v8 change occurred.

The **Magic Bounce reflected-move attribution fix** then passed targeted
recomputation on the two audited battles
(`magic_bounce_reflected_move_attribution_fix_report.md`). Protocol move rows
with explicit `[from] ability: Magic Bounce` provenance no longer become
actor-selected labels or reflector moveset evidence. This removes reflected
Defog from Hatterene's reconstructed moves, restores the later Psychic
candidate/match, and makes reflected Will-O-Wisp a nondecision. Focused
materialization/label, v7 action-feature, public-belief, no-leakage,
prevention/rollout, trainer, and manifest tests pass. The existing 1,000-battle
artifact was not rematerialized and remains stale at 43 unmatched; expected
future residual count is **41** quarantined Illusion rows. Rank-only training
remains **closed** pending explicit rematerialization approval and re-audit.
No training, full rematerialization, promotion, live/default, schema, or v8
change occurred.

The explicitly approved **post-Magic-Bounce 1,000-battle v7/v7
rematerialization** then completed from source commit
`4cba668d28491cf3aaf3b171660c47f113a57edc` into
`datasets/diagnostic_1000_v7_v7_post_magic_bounce`: 1,000/1,000 valid battles,
80,635 states, 617,555 candidates, exact 700/150/150 battle splits,
`live-private-belief-v7` 3208D plus `legal-action-v7` 552D /
`956da3d2…1bf39d7`, 1,000 retained shards, and all 18 validation checks passed.
Independent inspection found finite arrays, 80,594 groups with exactly one
positive, and 41 explicitly quarantined zero-positive groups. All nine explicit
Magic Bounce reflection rows are now nondecisions; reflected Defog no longer
pollutes Hatterene's moveset and later Psychic matches, while reflected
Will-O-Wisp produces no actor label. The residual set is exactly the previously
classified 41-row public-replay Illusion ambiguity floor, with no new category.
See `diagnostic_1000_v7_v7_post_magic_bounce_materialization_report.md` and
`diagnostic_1000_v7_v7_post_magic_bounce_dataset_quality_audit.md`.

The dataset-quality gate for a separately approved rank-only diagnostic is now
**open**. Training itself remains **closed** pending a read-only
`--validate-only` check and separate explicit user approval. No training,
checkpoint, promotion, live/default, schema, v8, old-gen, or push occurred.

The separately approved **1,000-battle post-Magic-Bounce v7/v7 rank-only
diagnostic run** then completed on CUDA with exit code 0. It trained only the
action-rank head for 10 epochs / 10,070 rank-only optimizer steps and
early-stopped after three non-improving epochs, selecting epoch 7 by validation
rank NLL. The tiny overfit check passed (top-1 0.96875). Selected validation
NLL/top-1/top-3/MRR were
1.175278 / 0.515985 / 0.888422 / 0.705594. The test split was evaluated once
after selection: 1.181397 / 0.507626 / 0.886274 / 0.700131.

Both generated checkpoints contain the exact v7/v7 versions, 3208/552
dimensions, ordered-name fingerprints, manifest checksum, rank-only trained
head flags, and `production_eligible: false`; all checkpoint tensors are
finite. `model.best.pt` is epoch 7 / step 7,049, while `model.pt` is the
retained final epoch 10 / step 10,070 checkpoint. See
`training_runs/diagnostic_1000_action_rank_v7_v7_post_magic_bounce_rank_only/diagnostic_1000_action_rank_v7_v7_post_magic_bounce_rank_only_report.md`.

This closes the approved offline rank-only training gate only. Checkpoint
promotion, browser/live shadow testing, production use, live/default changes,
and v8 disposition remain separately closed.

The selected checkpoint offline evaluation then passed strict loading and
reproduced the 8,327-group test metrics exactly:
NLL/top-1/top-3/MRR
`1.181397 / 0.507626 / 0.886274 / 0.700131`. In-memory negative probes confirmed
hard rejection of wrong state/action schemas, dimensions, and ordered-name
fingerprints. The model beats max expected damage by 12.7 top-1 points and the
best heuristic by 15.7 top-3 points. Strong slices include forced switches
(61.2% / 99.3% top-1/top-3) and the revenge-kill proxy
(74.6% / 97.4%); weaknesses remain voluntary switches
(31.6% / 73.9%), chosen Tera moves (24.8% / 58.9%), more-than-12-candidate
turns (36.8% / 76.9%), and the small prevention-interaction slice
(41.2% / 76.5%). See
`diagnostic_1000_v7_v7_rank_only_offline_eval_report.md`.

This supports a separately approved larger non-production rank experiment and
targeted v8 threat-awareness work. It does not authorize promotion, production,
browser/live shadow, or live/default changes; real-packet slot parity and v8
disposition remain open.

The source-agnostic v8 meta-prior design is now complete
(`v8_meta_prior_opponent_set_belief_design.md`). It proposes immutable,
versioned prior sources; a time-causal posterior over joint set hypotheses; and
compact semantic state plus candidate-sensitivity features. Randbats priors
should come from deterministic offline sampling of the pinned Showdown set
generator. Standard-format priors should use pinned Smogon usage snapshots with
explicit factorized/joint-quality and freshness metadata. Public reveals may
condition the posterior; hidden truth, future reveals, strategic switch-choice
inference, and initial damage/speed inference are prohibited.

This is design only. v7 schemas/fingerprints and live defaults are unchanged.
The existing 1,000-battle v7 baseline is sufficient comparison evidence, so v8
meta-prior implementation/audit should precede the next durable or substantially
larger rank run. Implementation, materialization, training, promotion, and live
use remain separately closed.

The source-neutral contract batch is now implemented in `meta_prior.py` and
`opponent_set_belief.py`, with a fixture source and 14 focused tests. It
preserves joint set hypotheses, applies only explicit public move/ability/item/
Tera evidence in ordered prefixes, records confirmed and ruled-out support,
retains unknown tail mass, and falls back to tail-only state on missing or
contradictory priors. Hidden truth is not accepted by the API; perturbation and
future-prefix tests pass. Generic immunity, damage, speed, and switching remain
non-evidence.

This closes only the pure contract/test gate. No v8 feature/schema wiring,
Randbats/Smogon ingestion, materialization, training, checkpoint, live-default,
or live-behavior change occurred. The next gate is a diagnostic-only adapter
from existing public parsed prefixes into these contracts, followed separately
by a pinned Randbats prior snapshot builder.

The diagnostic replay-prefix adapter gate is now complete. The adapter consumes
only the public `protocol_log` retained by the existing replay parser, truncates
causally by line or turn, and updates fixture-backed beliefs for known public
opponent identity segments. It handles explicit move, ability, item, Tera,
named prevention/reflection/immunity, and Poltergeist item-reveal rows. Generic
switching, damage, immunity, and move order do not become set evidence.

Replay-backed tests cover reflected Defog/Psychic
(`gen9randombattle-2589608300`), reflected Will-O-Wisp plus Tera labeling
(`gen9randombattle-2594129364`), Illusion `replace` ambiguity, and ordinary
ability/item/move reveals (`gen9randombattle-2593348981`). Illusion creates a
new public identity segment instead of rewriting the earlier displayed-species
belief. Tests also prove future-line truncation, hidden-truth perturbation
invariance, correct reflection ownership, and explicit unknown-tail fallback.

No Randbats source discovery, scraping, regeneration, sampling, or ingestion
was attempted. No v8 feature/schema, v7 fingerprint, materialization, training,
checkpoint, live/default, or browser behavior changed. The next separate gate
is a pinned prior-source adapter using already established repository Randbats
set provenance, followed by posterior calibration; it remains unimplemented
and requires a separate task.

The pinned existing-data adapter is now complete. It reuses the old shortcut's
loader and selected source `data/random-battles/gen9/sets.json` without
scraping, rediscovery, regeneration, or generator sampling. The exact raw
source SHA-256 is
`7dc75740d17755d921c473fca68b3022f6f37a2af387d3cd9c94432bd646eaef`;
the adapter version is `randbats-role-data-adapter-v1`.

Because the source contains role/movepool declarations but no items, exact
four-move generated sets, or empirical role weights, emitted priors are marked
`factorized`, role and ability/Tera alternatives are expanded uniformly, and
`other_mass = 0.5` remains explicit under an unvalidated adapter policy.
`sample_count = 0` prevents this source from masquerading as a sampled
generator snapshot. Tests cover Dondozo, Hatterene, Great Tusk, missing data,
determinism, format mismatch, and replay/context hidden-truth perturbations.

This completes only the existing-data source adapter. The separate
generator-sampled snapshot and convergence/calibration gate remains open. No
v8 feature/schema, v7 fingerprint, materialization, training, checkpoint,
live/default, browser, or strategic behavior changed.
