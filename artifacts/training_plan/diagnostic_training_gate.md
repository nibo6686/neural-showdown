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
- [ ] First diagnostic training plan/config/command reviewed.
- [ ] User explicitly approved launching diagnostic training.

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

The training gate remains **closed** until the plan and validation results are
reviewed with the user and the user explicitly approves launching training.
