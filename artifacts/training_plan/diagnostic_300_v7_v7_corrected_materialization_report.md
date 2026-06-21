# diagnostic_300 v7/v7 Corrected Materialization Report

## Scope and command

Materialization was explicitly approved for this task. No training, checkpoint
promotion, live-default change, live-bot change, schema change, push, or
`legal-action-v8` work occurred.

Successful command, after setting the README-documented Python path and
sim-core worker environment:

```powershell
& $py -m neural.benchmark_vnext_featuregen --full-manifest `
  --manifest artifacts\training_plan\manifests\diagnostic_300_v7_v7_corrected_manifest.json `
  --output-dir artifacts\training_plan\datasets\diagnostic_300_v7_v7_corrected `
  --action-feature-version legal-action-v7 --workers 6
```

The initial direct invocation without `NEURAL_SIM_CORE_COMMAND_JSON` /
`NEURAL_SIM_CORE_CWD` failed before any battle shards completed. A second
environment attempt failed before shards because the sim-core path was
serialized as an object rather than a string. The successful run used plain
string sim-core paths and resumed the same corrected output directory.

## Outputs

- Output directory:
  `artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected`
- NPZ:
  `artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected/diagnostic_300_v7_v7_corrected.npz`
- Metadata:
  `artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected/feature_metadata.json`
- JSON report:
  `artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected/materialization_report.json`
- Generated dataset-local markdown report:
  `artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected/diagnostic_300_v7_v7_corrected_materialization_report.md`
- Decision skip audit:
  `artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected/decision_skip_audit.jsonl`
- Resumable shards:
  `artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected/_shards`

## Materialization result

- Battles requested / processed / valid / failed: 300 / 300 / 300 / 0
- Runtime: 344.7 seconds
- Workers: 6
- Split battle counts: train 210, validation 45, test 45
- Split state counts: train 20,552, validation 2,255, test 2,428
- Decision states: 25,235
- Legal-action candidates: 191,667
- Average legal actions per state: 7.5953
- Dataset size: 10.42 MB
- Validation: PASS
- Shards retained: 300 `.pkl` files

## Schema and fingerprint

| Side | Version | Dimension | Ordered-name fingerprint |
| --- | --- | ---: | --- |
| State | `live-private-belief-v7` | 3208 | `0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf` |
| Action | `legal-action-v7` | 552 | `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7` |

The NPZ embeds the expected state/action names and versions. State and action
arrays are finite float16, state vectors are not duplicated per candidate, and
the first 331 action names remain byte-identical to `legal-action-v6`.

## Preflight and metadata validation

Full-manifest preflight passed:

- exact 300 expected battles;
- exact 210/45/45 split counts;
- all paths exist;
- unique replay IDs;
- no split overlap;
- label manifest valid;
- schema dimensions requested;
- output directory safe to write;
- unsupported team-size replays: none.

Dataset validation passed every recorded check, including schema dimensions,
float16 dtypes, valid rank labels, absent action-value labels, candidate index
validity, embedded names matching schema/metadata, unchanged live defaults,
manifest traceability, no split crossing, and state splits matching the
manifest.

## Old stale dataset

The stale directory
`artifacts/training_plan/datasets/diagnostic_300_v7_v7` still exists and was
not overwritten. Its directory `LastWriteTime` remained
`2026-06-20 17:46:52`; the corrected directory was written separately at
`2026-06-20 18:35:20`.

The old artifact remains a pre-fix audit artifact and must not be used for
training.

## Label summary

- Matched decisions: 24,716
- Unmatched decisions: 519
- Match rate: 97.94%
- Skip reasons:
  - `chosen_action_unmatched_for_action_rank`: 519
  - `initial_deployment_nondecision`: 600
  - `no_action_label`: 0
  - `unknown_or_draw_outcome`: 0
- Matched by kind:
  - move: 18,073
  - move_tera: 427
  - switch: 6,216
- Unmatched by kind:
  - move: 482
  - move_tera: 4
  - switch: 33

The unsupported 24-vs-24 replay `gen9randombattle-2591563263` is absent from
the corrected manifest and selected replay IDs. It contributes zero unmatched
entries to the corrected audit.

## Feature activity

- Opponent displayed-species uncertainty: 0 / 25,235 states.
- Batch 7 action-risk/probability slice: 50 active features, 608,209 nonzero
  entries across the slice.
- Batch 8 forced-decision/secondary-chance slice: 25 active features, 119,430
  nonzero entries across the slice.

## Gate status

The corrected dataset is structurally valid and materially improves the known
blockers. It is ready for read-only review and quality-gate decision making,
but smoke training remains blocked until this corrected quality audit is
accepted. Production/live gates remain closed.
