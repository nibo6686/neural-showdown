# vNext Feature Generation Tiny-10 Benchmark

- Command: `.\scripts\run_windows.ps1 -Action benchmark-vnext-featuregen -SimCoreMode native`
- Battles: 10 valid / 0 failed
- Decision states: 576
- Legal action candidates: 4,299
- Average legal actions/state: 7.46
- Runtime: 45.98s total; 4.60s/battle; 79.83ms/state; 10.70ms/candidate
- Dataset size: 0.23 MiB compressed
- Dense state/action payload: 6.13 MiB
- Peak Python tracemalloc heap: 19.75 MiB
- State: `live-private-belief-v7`, 3208D
- Action: `legal-action-v5`, 318D
- Dtype/layout: float16; one state row per decision; separate candidate action rows linked by candidate_state_indices
- State duplicated per candidate: False
- Split state counts: {'test': 160, 'train': 231, 'validation': 185}
- Impact methods: {'non_damaging': 915, 'unavailable': 1935, 'smogon_calc': 1449}

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
- [x] `state_value_labels_valid`
- [x] `action_rank_labels_valid`
- [x] `action_value_labels_absent`

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
- Action-rank groups with unmatched replay actions are excluded; inspect the reported match rate before training.

- Schema bug found: **no**
- Ready for full `diagnostic_300` feature materialization: **yes**
- Training gate: **closed**; labels, full materialization, training command, and materialized-feature sanity checks remain outstanding.
