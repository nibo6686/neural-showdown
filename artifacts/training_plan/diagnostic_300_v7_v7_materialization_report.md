# diagnostic_300_v7_v7 Materialization Report

## Result

The explicitly approved small v7/v7 diagnostic baseline materialized and
validated successfully. This was a dataset-generation run only; no training,
checkpoint promotion, live-default change, or live-bot change occurred.

- Source commit:
  `63484055aad7b5d45102fa53e431fe682cc3bb45`
- Manifest:
  `artifacts/training_plan/manifests/diagnostic_300_manifest.json`
- Manifest SHA-256:
  `3399bf06c268f3eeb6cfabc8b6b102bde8a77e100f3e06c2ecc2f11a69d98185`
- Output:
  `artifacts/training_plan/datasets/diagnostic_300_v7_v7/`
- Dataset:
  `artifacts/training_plan/datasets/diagnostic_300_v7_v7/diagnostic_300_v7_v7.npz`
- Dataset SHA-256:
  `0f5267f642251e1a106c342b7b9128918c1eb7400af17ef501059670cb88f9bd`
- Runtime: 290.73 seconds with 6 workers.
- Storage: 10.42 MiB NPZ; 11.35 MiB top-level output files.

## Command

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
$env:NEURAL_SIM_CORE_CWD = (Resolve-Path .\sim-core)
$serverJs = (Resolve-Path .\sim-core\dist\src\server.js).Path
$env:NEURAL_SIM_CORE_COMMAND_JSON = ConvertTo-Json @('node', $serverJs) -Compress
& $py -m neural.benchmark_vnext_featuregen `
    --full-manifest `
    --manifest artifacts\training_plan\manifests\diagnostic_300_manifest.json `
    --output-dir artifacts\training_plan\datasets\diagnostic_300_v7_v7 `
    --action-feature-version legal-action-v7 `
    --workers 6
```

The full-manifest materializer is fixed to state
`live-private-belief-v7`; it has no `--state-feature-version` CLI option.
The generated metadata and NPZ independently confirm that state version.

## Schema validation

| Side | Version | Dimension | Ordered-name fingerprint |
| --- | --- | ---: | --- |
| State | `live-private-belief-v7` | 3208 | `0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf` |
| Action | `legal-action-v7` | 552 | `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7` |

The built-in and independent `validate_benchmark_arrays` passes covered action
and state dimensions/dtypes, embedded ordered names, fingerprints, candidate
indices, labels, manifest traceability, split isolation, unchanged live
defaults, and absence of action-value labels.

## Counts and splits

- Battles: 300 requested / 300 processed / 300 valid / 0 failed.
- Battle splits: 210 train / 45 validation / 45 test.
- State rows: 25,396
  - train 20,713
  - validation 2,255
  - test 2,428
- Action candidates: 189,957
  - move 73,836
  - move+Tera 42,034
  - switch 74,087
- Action-rank positives: 24,624.
- Matched/unmatched decisions: 24,624 / 772 (96.96% match rate).
- Positive kinds: 17,960 move / 426 move+Tera / 6,238 switch.
- State labels: 12,632 wins / 12,764 losses / 0 draws.
- Action-value labels: 0.
- Impact methods: 63,764 `smogon_calc`, 51,184 `non_damaging`,
  79,324 `unavailable`. Unavailable impact remains explicit/fail-closed.

## Resume and artifact safety

- All 300 per-battle `.pkl` shards remain under `_shards/`.
- The run started with `already_sharded=0`, printed per-battle progress, and can
  resume by skipping retained shards.
- No shard was deleted.
- The prior `diagnostic_300_v7_v6.npz` remains unchanged at SHA-256
  `599adb49f3fa1765ca1b5d1b9e8c753dc171ab9ff7a8398e65c90274cbc7f884`.
- Generated dataset/shard/audit/metadata artifacts remain unstaged.

## Warnings and gate

- Own-side reconstructed state retains the documented replay-training
  future-public-reveal assumption.
- The 772 unmatched action groups remain explicitly audited and excluded.
- v7 is only partially possible-threat-aware; the possible Unaware, Magic
  Bounce, Good as Gold, Levitate, Covert Cloak, Shield Dust, and Inner Focus
  limitations from `possible_mechanic_threat_awareness_audit.md` still apply.
- Rollout parity remains 51 PASS / 0 FAIL / 8 honest GAP.
- Materialization is complete. **Training, checkpoint promotion, and live use
  remain closed and require separate explicit approval.**
