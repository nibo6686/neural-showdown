# diagnostic_1000_v7_v7_post_ditto Materialization Report

The explicitly approved 1,000-battle v7/v7 action-rank diagnostic
materialization completed in a new output directory. No training, checkpoint
promotion, live/default change, schema change, v8 work, old-gen work, or push
occurred.

## Manifest

- Manifest:
  `artifacts/training_plan/manifests/diagnostic_1000_v7_v7_post_ditto_manifest.json`
- Manifest report:
  `artifacts/training_plan/manifests/diagnostic_1000_v7_v7_post_ditto_manifest_report.md`
- Manifest SHA-256:
  `d19727107fc88e03b1eecf12ad3538cb056ee699e4e1f2cfd743fce44e0b4c46`
- Manifest version: `diagnostic-1000-action-rank-manifest-v1`
- Source catalog checksum:
  `0ebbad4d9a0fa35e3e37f38d964b1d04fa77207870a66048221ec1461044b24e`
- Splits: 700 train / 150 validation / 150 test

The prior 1,000-battle manifest failed current preflight because it contained
one 24-vs-24 and one 8-vs-8 replay. The manifest generator now applies the
frozen six-slot protocol filter directly. The fresh deterministic selection
removed those two replays and added two eligible replacements:

- train: `gen9randombattle-2591563263` →
  `gen9randombattle-2591371798`;
- validation: `gen9randombattle-2589855735` →
  `gen9randombattle-2593791958`.

Deterministic split balancing moved 33 retained battles between splits while
preserving exact 700/150/150 battle-level isolation. Full preflight passed:
1,000 unique IDs, all paths present, no split overlap, no unsupported team
sizes, compatible labels/schema, and a fresh safe output path.

## Materialization command

The successful/resumed command was:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src).Path
$env:NEURAL_SIM_CORE_CWD = (Resolve-Path .\sim-core).Path
$serverJs = (Resolve-Path .\sim-core\dist\src\server.js).Path
$env:NEURAL_SIM_CORE_COMMAND_JSON = ConvertTo-Json @('node', $serverJs) -Compress
& $py -m neural.benchmark_vnext_featuregen --full-manifest `
  --manifest artifacts\training_plan\manifests\diagnostic_1000_v7_v7_post_ditto_manifest.json `
  --output-dir artifacts\training_plan\datasets\diagnostic_1000_v7_v7_post_ditto `
  --action-feature-version legal-action-v7 --workers 6
```

The first invocation without the documented sim-core environment stopped
before processing any battle. With sim-core configured, the first long-running
invocation retained 638 crash-safe shards before the shell time window ended.
The identical command resumed 638 completed / 362 pending shards and assembled
the final artifact. The generated report records 822.72 seconds for the final
resume/assembly invocation.

## Result

- Output directory:
  `artifacts/training_plan/datasets/diagnostic_1000_v7_v7_post_ditto`
- Dataset:
  `artifacts/training_plan/datasets/diagnostic_1000_v7_v7_post_ditto/diagnostic_1000_v7_v7_post_ditto.npz`
- Dataset SHA-256:
  `e8c3b4dde2d3eb59154563ce7595d07535507eaa2771c5faec424c81b393bf22`
- Dataset size: 33.59 MiB; total final output size: 35.66 MiB
- Shards retained: 1,000
- Battles: 1,000 requested / 1,000 processed / 1,000 valid / 0 failed
- Decision states: 80,644
- Action candidates: 617,687 (7.66 average/state)
- Candidate kinds: 239,960 move / 130,901 move-Tera / 246,826 switch
- State splits: 64,460 train / 7,855 validation / 8,329 test
- State-value labels: 40,278 wins / 40,366 losses / 0 draws
- Action-rank positives: 80,601
- Unchosen candidates: 537,086
- Matched / unmatched decisions: 80,601 / 43
- Match rate: 99.9467%
- Matched by kind: 58,199 move / 1,447 move-Tera / 20,955 switch
- Unmatched by kind: 24 move / 1 move-Tera / 18 switch
- Initial-deployment nondecisions: 2,000
- Action-value labels: 0

## Schema and validation

- State: `live-private-belief-v7`, 3208D,
  `0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf`
- Action: `legal-action-v7`, 552D,
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`
- On-disk dtype: float16
- Numeric arrays checked: 8; NaN/Inf arrays: 0
- Positive labels per state: 80,601 groups with one positive; 43 quarantined
  groups with zero positives; no malformed multi-positive group
- Embedded manifest checksum and source snapshot match the selected manifest
  exactly.
- All 18 built-in validation checks passed, including split isolation,
  candidate indices, exact schema metadata/fingerprints, embedded names,
  finite/valid labels, no duplicated state vectors, no action-value labels,
  and unchanged live defaults.

## Old-dataset integrity

All pre-existing `.npz` hashes were unchanged after materialization, including
the 300-battle post-Ditto artifact
(`64e1f6eee11f6a6ee0f91a47acf4bf0943a6eeb3f86c7299a46717fd420af07`)
and the prior 1,000-battle v7/v5 artifact
(`68813aca5b28dba4eba3e38849ccfc951bdcdbd6d32988572ce9e78b41e41aaa`).
No prior dataset was overwritten.

## Materialization decision

The materialization itself passed structurally and produced the requested
fresh v7/v7 artifact. The separate quality audit found a new fixable Magic
Bounce reconstruction/label category, so this exact artifact is retained as a
diagnostic and training remains blocked pending repair, rematerialization, and
re-audit.
