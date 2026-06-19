# diagnostic_300 v7/v5 Materialization Report

- Command: `.\scripts\run_windows.ps1 -Action materialize-diagnostic-300 -SimCoreMode native`
- Runtime: 2165.09s
- Storage size: 13.96 MiB total; 9.18 MiB dataset
- Battles processed: 300 (300 valid / 0 failed)
- State count: 25,396
- Action candidate count: 189,957
- Average candidates/state: 7.48
- State-label distribution: {'wins': 12632, 'losses': 12764, 'draws': 0}
- Action-rank positives: 24,624
- Unchosen candidates: 165,333
- Matched / unmatched decisions: 24,624 / 772
- Skip reasons: {'no_action_label': 0, 'unknown_or_draw_outcome': 0, 'chosen_action_unmatched_for_action_rank': 772, 'initial_deployment_nondecision': 600}
- Battle split counts: {'train': 210, 'validation': 45, 'test': 45}
- State split counts: {'train': 20713, 'validation': 2255, 'test': 2428}
- Dtype/layout: float16; one state row per decision; separate candidate action rows linked by candidate_state_indices
- Duplicated state vectors: False
- State schema: `live-private-belief-v7`, 3208D
- Action schema: `legal-action-v5`, 318D
- Action-value labels: 0

## Files Produced

- `artifacts\training_plan\datasets\diagnostic_300_v7_v5\source_manifest_snapshot.json`
- `artifacts\training_plan\datasets\diagnostic_300_v7_v5\diagnostic_300_v7_v5.npz`
- `artifacts\training_plan\datasets\diagnostic_300_v7_v5\feature_metadata.json`
- `artifacts\training_plan\datasets\diagnostic_300_v7_v5\decision_skip_audit.jsonl`
- `artifacts\training_plan\datasets\diagnostic_300_v7_v5\materialization_report.json`
- `artifacts\training_plan\datasets\diagnostic_300_v7_v5\diagnostic_300_materialization_report.md`

## Validation

- [x] `state_dim_3208`
- [x] `action_dim_318`
- [x] `state_dtype_float16`
- [x] `action_dtype_float16`
- [x] `candidate_state_indices_valid`
- [x] `no_battle_crosses_splits`
- [x] `all_examples_trace_to_manifest`
- [x] `all_selected_battles_represented`
- [x] `state_splits_match_manifest`
- [x] `metadata_records_v7_v5`
- [x] `metadata_records_name_fingerprints`
- [x] `embedded_names_match_schema_and_metadata`
- [x] `metadata_records_manifest_profile_source`
- [x] `live_defaults_unchanged`
- [x] `state_not_duplicated_per_candidate`
- [x] `state_value_labels_valid`
- [x] `action_rank_labels_valid`
- [x] `action_value_labels_absent`

## Warnings and Limitations

- Peak memory is Python tracemalloc heap only; it excludes sim-core and NumPy native allocations.
- Own-side reconstructed state follows the existing replay-training future-public-reveal assumption.
- Action-rank groups with unmatched replay actions are excluded; inspect the reported match rate before training.

- Ready for first diagnostic training command design: **yes**
- Training gate: **closed** pending written plan/config/command, sanity-check review, and explicit user approval.
