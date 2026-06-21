# v8 State / v7 Action Belief-Slice Materialization Smoke

## Purpose

Verify end-to-end featuregen / metadata / fingerprint plumbing for the first v8
state belief slice (`live-private-belief-v8`) with the frozen `legal-action-v7`
action schema, before any larger v8 dataset or training. Smoke only — no
training, no full/large rematerialization, no checkpoint, no live/default change.

## CLI support added

`benchmark_vnext_featuregen` previously hardcoded `live-private-belief-v7` state
features with no flag. A `--state-feature-version {live-private-belief-v7,
live-private-belief-v8}` option (default v7) was added and threaded through
`run_benchmark`, `_decision_features`, `benchmark_metadata`,
`validate_benchmark_arrays`, and the saved arrays. For v8, `_decision_features`
builds the opponent active-slot `OpponentSetBelief` from the public prefix
(`active_opponent_set_belief`) and passes it to the v8 feature path. The default
(v7) path is byte-identical to before; full-manifest materialization is
restricted to v7 in this task (v8 is smoke-only via the non-full path).

## Exact command

```
python -m neural.benchmark_vnext_featuregen \
  --manifest artifacts/training_plan/manifests/diagnostic_300_manifest.json \
  --output-dir artifacts/training_plan/datasets/tiny_v8_v7_belief_slice_smoke \
  --battles 10 \
  --action-feature-version legal-action-v7 \
  --state-feature-version live-private-belief-v8
```

(run through the established sim-core env: `NEURAL_SIM_CORE_CWD`,
`NEURAL_SIM_CORE_COMMAND_JSON` pointing at `sim-core/dist/src/server.js`.)

- Manifest: `artifacts/training_plan/manifests/diagnostic_300_manifest.json`
  (10-battle deterministic subset, seed 20260619).
- Output: `artifacts/training_plan/datasets/tiny_v8_v7_belief_slice_smoke/`
  (new directory; no prior dataset overwritten; generated artifacts unstaged).

## Schema identity (verified exact)

| | Version | Dim | Fingerprint |
|---|---|---:|---|
| State | `live-private-belief-v8` | 3229 | `8ac514415b0e35014b5fc741d54cd79599175c039bdbda0cf2309d5d4ef26053` |
| Action | `legal-action-v7` | 552 | `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7` |

- Embedded `state_feature_names` equals `FEATURE_NAMES_V8`; first 3208 names
  equal `FEATURE_NAMES_V7` (v7 prefix byte/name preserved); embedded-name
  fingerprint matches metadata.
- Live defaults recorded unchanged (`live-private-belief-v2` / `legal-action-v3`).

## Counts and validation

- Battles: 10 processed, **10 valid, 0 failed**.
- Decision states: 576; legal-action candidates: 4276; runtime ~53.6 s.
- Arrays: state `(576, 3229)` float16; action `(4276, 552)` float16; no NaN/Inf.
- `validate_benchmark_arrays`: **passed**, all 19 checks true, including
  `state_dim_3229`, `v7_prefix_preserved`, `metadata_records_requested_schema`,
  `metadata_records_name_fingerprints`, `embedded_names_match_schema_and_metadata`,
  `live_defaults_unchanged`, `action_value_labels_absent`, split integrity, and
  one-positive-per-rank-group.
- Label match (this 10-battle subset): matched 576 / unmatched 0 (match rate
  1.0). State-value labels ⊆ {-1, +1}.

## v8 belief feature activity

- v8 slice = 21 columns appended after the 3208 v7 columns.
- `has_meta_prior` = 1 for all 576 states (every opponent active slot had a prior
  in this sample; coverage is 100% on this manifest), so the explicit-unknown
  path (`has_meta_prior = 0`, `prior_other_mass = 1.0`) is exercised by the unit
  tests rather than this sample.
- `prior_other_mass` ranges 0.5–1.0 (0.5 default tail; 1.0 where evidence drove a
  contradiction/full-unknown collapse) — the slice reflects live belief state.
- All 21 v8 columns are active across the sample; all 576 rows carry nonzero v8
  values. Source-quality flags (factorized / coarse movepool / item unknown /
  uncalibrated) populate as expected for the role-data source.

## Action batch 7/8 activity (preserved)

- Batch-7 slice (cols 452–510): 32/59 columns active; 2364/4276 rows nonzero.
- Batch-8 slice (cols 511–551): 19/41 columns active; 800/4276 rows nonzero
  (forced-decision/secondary-chance fields are intentionally sparse).

## No-leakage / regression verification

- `test_v8_belief_feature_slice`, `test_meta_prior_belief_contracts`,
  `test_opponent_set_belief_replay_adapter`, `test_randbats_meta_prior_source`,
  `test_randbats_joint_set_posterior_fidelity`: **71 tests pass**.
- Public-prefix audit unchanged: 100% / 100% coverage, contradictions 0.12%.
- `recompute_magic_bounce_reflected_move_cases.py`: `all_passed=True`.
- `recompute_v7_v7_residual_unmatched_from_replays.py`: `all as expected=True`.
- `git diff --check`: clean.

## Conclusion

End-to-end v8 state featuregen, metadata, embedded names, and fingerprint
plumbing are correct with the frozen v7 action schema and a preserved v7 state
prefix. A **300-battle v8/v7 belief-slice materialization is now appropriate** as
the next gated step (reuse the frozen diagnostic_300 splits, new output dir),
followed by a read-only quality audit; that remains separately approval-gated and
was not run here. No training, full/large rematerialization, checkpoint
promotion, live/default change, v7 schema/fingerprint change, or candidate/action
v8 feature change occurred.
