# vNext Feature Generation Tiny-10 Benchmark

- Command: `.\scripts\run_windows.ps1 -Action benchmark-vnext-featuregen -SimCoreMode native`
- Battles: 10 valid / 0 failed
- Decision states: 596
- Legal action candidates: 3,319
- Average legal actions/state: 5.57
- Runtime: 21.19s total; 2.12s/battle; 35.55ms/state; 6.38ms/candidate
- Dataset size: 0.21 MiB compressed
- Dense state/action payload: 5.66 MiB
- Peak Python tracemalloc heap: 18.07 MiB
- State: `live-private-belief-v7`, 3208D
- Action: `legal-action-v5`, 318D
- Dtype/layout: float16; one state row per decision; separate candidate action rows linked by candidate_state_indices
- State duplicated per candidate: False
- Split state counts: {'test': 166, 'train': 239, 'validation': 191}
- Impact methods: {'smogon_calc': 753, 'non_damaging': 507, 'unavailable': 2059}

## Validation

- [x] `state_dim_3208`
- [x] `action_dim_318`
- [x] `state_dtype_float16`
- [x] `action_dtype_float16`
- [x] `candidate_state_indices_valid`
- [x] `no_battle_crosses_splits`
- [x] `all_examples_trace_to_manifest`
- [x] `metadata_records_v7_v5`
- [x] `metadata_records_name_fingerprints`
- [x] `metadata_records_manifest_profile_source`
- [x] `live_defaults_unchanged`
- [x] `state_not_duplicated_per_candidate`

## Files Produced

- `artifacts\training_plan\benchmarks\vnext_featuregen_tiny_10\subset_manifest.json`
- `artifacts\training_plan\benchmarks\vnext_featuregen_tiny_10\vnext_features_tiny_10.npz`
- `artifacts\training_plan\benchmarks\vnext_featuregen_tiny_10\feature_metadata.json`
- `artifacts\training_plan\benchmarks\vnext_featuregen_tiny_10\benchmark_report.json`
- `artifacts\training_plan\benchmarks\vnext_featuregen_tiny_10_report.md`

## Warnings and Decision

- Peak memory is Python tracemalloc heap only; it excludes sim-core and NumPy native allocations.
- Own-side reconstructed state follows the existing replay-training future-public-reveal assumption.
- This is a 10-battle feasibility benchmark, not the full diagnostic_300 materialization.

- Schema bug found: **no**
- Ready for full `diagnostic_300` feature materialization: **yes**
- Training gate: **closed**; labels, full materialization, training command, and materialized-feature sanity checks remain outstanding.
