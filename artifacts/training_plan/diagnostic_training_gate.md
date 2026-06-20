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
- [ ] `legal-action-v7` later batches (conditional execution/history and remaining typed effects) implemented.
- [ ] Tiny rank-only training on fresh v7/v6 diagnostic_300 approved (plumbing/behavior comparison, exact-vs-INEXACT breakdowns).
- [ ] `legal-action-v7` rematerialization + training approved (after the typed-effect slices are complete and re-audited).
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
