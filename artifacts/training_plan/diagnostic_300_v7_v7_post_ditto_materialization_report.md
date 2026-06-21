# diagnostic_300_v7_v7_post_ditto Materialization Report

Fresh, explicitly approved v7/v7 materialization run after the full reconstruction
fix chain (missing-candidate, residual-34 triage, Ditto/Imposter Transform,
actor-private Zoroark/Illusion, and Ditto re-transform-into-same-species). No
training, checkpoint promotion, live-default change, live-bot change, push,
`legal-action-v8`, or old-gen work occurred.

- Source commit: `01f14d6c04097b757f7a0435bc4eb3bf039ab768`
  (`checkpoint: ditto retransform same species fix`)
- Command:
  `python -m neural.benchmark_vnext_featuregen --full-manifest --manifest artifacts\training_plan\manifests\diagnostic_300_v7_v7_corrected_manifest.json --output-dir artifacts\training_plan\datasets\diagnostic_300_v7_v7_post_ditto --workers 6 --action-feature-version legal-action-v7`
- Manifest: `diagnostic_300_v7_v7_corrected_manifest.json` (`diagnostic-300-manifest-v1`)
- Runtime: 230.5s, 6 workers
- Storage: 11.14 MiB total; 10.53 MiB dataset

## Counts

- Battles processed: 300 (300 valid / 0 failed)
- Decision states: 25,235
- Action candidates: 197,449
- Average candidates/state: 7.82
- Action-rank positives (matched): 25,232
- Unchosen candidates: 172,217
- **Matched / unmatched decisions: 25,232 / 3 (match rate 99.99%)**
- Matched by kind: move 18,552 / move_tera 431 / switch 6,249
- Unmatched by kind: move 3 / move_tera 0 / switch 0
- Skip reasons: `{no_action_label: 0, unknown_or_draw_outcome: 0, chosen_action_unmatched_for_action_rank: 3, initial_deployment_nondecision: 600}`
- State-value distribution: `{wins: 12549, losses: 12686, draws: 0}`
- Action-value labels: 0
- Battle splits: `{train: 210, validation: 45, test: 45}`
- State splits: `{train: 20552, validation: 2255, test: 2428}`

## Schema / fingerprint

- State: `live-private-belief-v7`, **3208D**
- Action: `legal-action-v7`, **552D**
- Action ordered-name fingerprint:
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7` (exact)
- Live defaults recorded unchanged: state `live-private-belief-v2`, action `legal-action-v3`
- `.npz`: `state_features (25235, 3208) float16`, `action_features (197449, 552) float16`
- 300 per-battle shards retained under `_shards/` (resume-safe; `already_sharded=0 pending=300` this run)
- Action/state feature name vectors byte-identical to `diagnostic_300_v7_v7_post_illusion` (schema unchanged; v6 prefix names identical)

## Validation (all 18 checks passed)

`state_dim_3208`, `action_dim_matches_schema`, `state_dtype_float16`,
`action_dtype_float16`, `candidate_state_indices_valid`, `no_battle_crosses_splits`,
`all_examples_trace_to_manifest`, `all_selected_battles_represented`,
`state_splits_match_manifest`, `metadata_records_requested_schema`,
`metadata_records_name_fingerprints`, `embedded_names_match_schema_and_metadata`,
`metadata_records_manifest_profile_source`, `live_defaults_unchanged`,
`state_not_duplicated_per_candidate`, `state_value_labels_valid`,
`action_rank_labels_valid`, `action_value_labels_absent`.

## Files produced

- `diagnostic_300_v7_v7_post_ditto.npz`
- `feature_metadata.json`
- `decision_skip_audit.jsonl`
- `materialization_report.json`
- `diagnostic_300_v7_v7_post_ditto_materialization_report.md`
- `source_manifest_snapshot.json`
- `_shards/` (300 shards)

## Notes

- Generated dataset artifacts are unstaged per repo policy.
- Older datasets (`diagnostic_300_v7_v7`, `diagnostic_300_v7_v7_corrected`,
  `diagnostic_300_v7_v7_post_illusion`, `diagnostic_300_v7_v6`,
  `diagnostic_300_v7_v5`, `diagnostic_1000_action_rank_v7_v5`) were not
  overwritten; their `.npz` sha256 prefixes are byte-identical to the pre-run
  snapshot.
- The 3 residual unmatched rows are the expected irreducible non-self-confirming
  Illusion stints; see `diagnostic_300_v7_v7_post_ditto_dataset_quality_audit.md`.
- Training gate remains **closed**: this is a materialization-only task.
