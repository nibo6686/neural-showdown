# Diagnostic Training Gate

## Gate before first training run

- [x] Final representation freeze audit completed.
- [x] Machine-readable schema manifest written and validated.
- [x] Replay profiler designed.
- [x] Replay profiler implemented and run against the existing pool.
- [x] Battle-level `diagnostic_300` manifest materialized and overlap-checked.
- [ ] v7/v5 feature generation benchmarked on a small subset.
- [x] Slice counterfactual and schema-prefix tests pass.
- [x] Existing checkpoints and live defaults remain untouched.
- [x] Representation checkpoint committed before replay profiling.
- [ ] Training labels are explicitly chosen and documented separately for state
  value, action rank and action value.
- [ ] Train/validation/test assignment is fixed by battle before featurization.
- [ ] Output metadata records schema versions, ordered-name fingerprints,
  manifest/profile versions, source commit, dtype and information boundary.

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

The schema freeze is sufficient to proceed with profiler implementation and
`diagnostic_300` creation. The training gate itself remains closed until the
unchecked prerequisites above are completed.
