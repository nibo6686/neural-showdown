# vNext Feature Generation Tiny-10 Benchmark

- Command: `python -m neural.benchmark_vnext_featuregen --manifest artifacts\training_plan\manifests\diagnostic_300_manifest.json --output-dir artifacts\training_plan\datasets\diagnostic_300_v8_v7_belief_slice --battles 300 --action-feature-version legal-action-v7 --state-feature-version live-private-belief-v8`
- Battles: 299 valid / 1 failed
- Decision states: 25,020
- Legal action candidates: 194,967
- Average legal actions/state: 7.79
- Runtime: 3074.95s total; 10.25s/battle; 122.90ms/state; 15.77ms/candidate
- Dataset size: 10.63 MiB compressed
- Dense state/action payload: 359.37 MiB
- Peak Python tracemalloc heap: 776.95 MiB
- State: `live-private-belief-v8`, 3229D
- Action: `legal-action-v7`, 552D
- Dtype/layout: float16; one state row per decision; separate candidate action rows linked by candidate_state_indices
- State duplicated per candidate: False
- Split state counts: {'test': 2427, 'train': 20339, 'validation': 2254}
- Impact methods: {'smogon_calc': 63136, 'unavailable': 78381, 'non_damaging': 53484}

## Validation

- [x] `state_dim_3229`
- [x] `action_dim_matches_schema`
- [x] `state_dtype_float16`
- [x] `action_dtype_float16`
- [x] `candidate_state_indices_valid`
- [x] `no_battle_crosses_splits`
- [x] `all_examples_trace_to_manifest`
- [x] `all_selected_battles_represented`
- [x] `state_splits_match_manifest`
- [x] `metadata_records_requested_schema`
- [x] `metadata_records_name_fingerprints`
- [x] `embedded_names_match_schema_and_metadata`
- [x] `v7_prefix_preserved`
- [x] `metadata_records_manifest_profile_source`
- [x] `live_defaults_unchanged`
- [x] `state_not_duplicated_per_candidate`
- [x] `state_value_labels_valid`
- [x] `action_rank_labels_valid`
- [x] `action_value_labels_absent`

## Files Produced

- `artifacts\training_plan\datasets\diagnostic_300_v8_v7_belief_slice\subset_manifest.json`
- `artifacts\training_plan\datasets\diagnostic_300_v8_v7_belief_slice\vnext_features_tiny_10.npz`
- `artifacts\training_plan\datasets\diagnostic_300_v8_v7_belief_slice\feature_metadata.json`
- `artifacts\training_plan\datasets\diagnostic_300_v8_v7_belief_slice\decision_skip_audit.jsonl`
- `artifacts\training_plan\datasets\diagnostic_300_v8_v7_belief_slice\benchmark_report.json`
- `artifacts\training_plan\datasets\vnext_featuregen_tiny_10_report.md`

## Warnings and Decision

- Peak memory is Python tracemalloc heap only; it excludes sim-core and NumPy native allocations.
- Own-side reconstructed state follows the existing replay-training future-public-reveal assumption.
- Action-rank groups with unmatched replay actions are excluded; inspect the reported match rate before training.
- This is a 10-battle feasibility benchmark, not the full diagnostic_300 materialization.

- Schema bug found: **no**
- Ready for full `diagnostic_300` feature materialization: **no**
- Training gate: **closed**; labels, full materialization, training command, and materialized-feature sanity checks remain outstanding.
