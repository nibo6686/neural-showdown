# Diagnostic 300 v8 State / v7 Action Belief-Slice Materialization

## Result

The frozen `diagnostic_300_manifest.json` was attempted in full with
`live-private-belief-v8` state features and `legal-action-v7` action features.
The artifact contains 299 valid battles and one expected manifest
incompatibility: `gen9randombattle-2591563263` declares 24-vs-24 teams and
cannot fit the frozen six-slot schema. No replacement battle was sampled.

The supplied command initially exposed a subset-selection bug: requesting all
300 entries tried to resample 100 battles per split even though the frozen
manifest is 210/45/45. `select_manifest_subset` now preserves every manifest
entry when the requested size equals the manifest size. During the first audit,
supported belief updates were also found to drop prior-quality provenance; that
was fixed and the artifact was rematerialized from scratch.

## Exact successful command

```powershell
$py='D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
$env:NEURAL_SIM_CORE_CWD=(Resolve-Path .\sim-core).Path
$serverJs=(Resolve-Path .\sim-core\dist\src\server.js).Path
$env:NEURAL_SIM_CORE_COMMAND_JSON=ConvertTo-Json @('node',$serverJs) -Compress
& $py -m neural.benchmark_vnext_featuregen `
  --manifest artifacts\training_plan\manifests\diagnostic_300_manifest.json `
  --output-dir artifacts\training_plan\datasets\diagnostic_300_v8_v7_belief_slice `
  --battles 300 `
  --action-feature-version legal-action-v7 `
  --state-feature-version live-private-belief-v8
```

## Artifact

- Output directory:
  `artifacts/training_plan/datasets/diagnostic_300_v8_v7_belief_slice/`
- NPZ:
  `artifacts/training_plan/datasets/diagnostic_300_v8_v7_belief_slice/vnext_features_tiny_10.npz`
  (the filename is legacy non-full-path naming; the report records 300 requested).
- Runtime: 3,074.95 seconds.
- Battles: 300 attempted, 299 valid, 1 failed.
- Decision states: 25,020.
- Legal-action candidates: 194,967.
- Retained replay IDs: 299.
- State split rows: train 20,339; validation 2,254; test 2,427.

## Schema identity and validation

| Component | Version | Dim | Ordered-name fingerprint |
| --- | --- | ---: | --- |
| State | `live-private-belief-v8` | 3229 | `8ac514415b0e35014b5fc741d54cd79599175c039bdbda0cf2309d5d4ef26053` |
| Action | `legal-action-v7` | 552 | `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7` |

All 19 `validate_benchmark_arrays` checks passed. The first 3,208 embedded v8
state names equal `FEATURE_NAMES_V7`; the frozen v7 fingerprint remains
`0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf`.
State and action arrays are float16 and contain no NaN or infinity. Live defaults
remain `live-private-belief-v2` / `legal-action-v3`.

## Labels

- Matched decisions: 25,017.
- Unmatched decisions: 3.
- Match rate: 99.9880%.
- Unmatched kind/reason: 3 move rows,
  `move_missing_from_reconstructed_active_moves`.
- The rows are the established non-self-confirming Illusion ambiguity floor:
  `gen9randombattle-2593348981` turns 1–2 (`Will-O-Wisp`, `Poltergeist`) and
  `gen9randombattle-2593283718` turn 3 (`Hyper Voice`).
- No new v8-caused label or matcher category appeared.

## Scope confirmation

No training, 1,000-battle v8 materialization, checkpoint promotion, live/default
change, candidate/action-v8 work, Randbats regeneration/sampling, Smogon
ingestion, or old-dataset overwrite occurred.
