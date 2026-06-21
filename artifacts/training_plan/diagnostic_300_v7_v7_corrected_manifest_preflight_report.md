# diagnostic_300 v7/v7 Corrected Manifest Preflight

## Scope

This task prepared the next clean `diagnostic_300` v7/v7 materialization by
replacing the unsupported custom 24-vs-24 replay. It did not run full feature
generation, create a dataset output directory, train, promote checkpoints,
change live defaults, change live bot behavior, change schema/fingerprints, or
implement `legal-action-v8`.

## Reconstruction checkpoint

- Commit: `6401b3fd1a51361b5c5f0a18c72f45ee704a6cae`
- Message: `checkpoint: replay state reconstruction blocker fixes`

## Original manifest finding

- Original manifest:
  `artifacts/training_plan/manifests/diagnostic_300_manifest.json`
- `gen9randombattle-2591563263` was present in the original manifest.
- Split: `train`
- Primary stratum: `long_close`
- Public protocol team sizes: `p1=24`, `p2=24`
- Old-manifest full preflight now rejects this entry via
  `team_sizes_fit_frozen_six_slot_schema = false`.

## Corrected manifest

- Corrected manifest:
  `artifacts/training_plan/manifests/diagnostic_300_v7_v7_corrected_manifest.json`
- Original manifest was not overwritten.
- Excluded replay: `gen9randombattle-2591563263`
- Replacement replay: `gen9randombattle-2591433931`
- Replacement split: `train`
- Replacement primary stratum: `long_close`
- Replacement public protocol team sizes: `p1=6`, `p2=6`
- Validation/test splits were left unchanged.

The replacement was chosen as the next deterministic unused `long_close`
candidate after applying the new explicit team-size guard. The first checked
candidate was the rejected 24-vs-24 replay; the next candidate,
`gen9randombattle-2591433931`, passed with six slots per side.

## Split counts

| Split | Count |
| --- | ---: |
| train | 210 |
| validation | 45 |
| test | 45 |

## Read-only validation results

Manifest validation passed:

- exactly 300 entries;
- 300 unique replay IDs;
- exact 210/45/45 split sizes;
- no cross-split duplicates;
- all entries are in the catalog;
- all paths exist;
- selected mechanic-flag total remains above the random baseline
  (`2086 >= 1633`);
- seed and catalog checksum remain recorded.

Full-manifest preflight passed for the corrected manifest with
`legal-action-v7`:

- manifest SHA-256:
  `ca9224de951d8b4846e0d89770437b17f85498def7bcddf92e8d2b1d00243f48`
- label manifest SHA-256:
  `c295bd16322215149d542ded9a179d970480af9150c8c3f67eb2778f53ff1d67`
- expected battles: 300
- split counts: train 210, validation 45, test 45
- unsupported team-size replays: none
- overwrite guard: `fresh_or_empty_output_dir`

The preflight used a non-created path
`artifacts/training_plan/datasets/_preflight_only_do_not_create`; `Test-Path`
confirmed it did not exist after validation.

## Data status and gate

The displayed-species knownness fix changes the replay materialized state, so
the old `artifacts/training_plan/datasets/diagnostic_300_v7_v7` artifact
remains stale and must not be used for training. Its 772 unmatched states and
near-global displayed-species-uncertain counts are immutable pre-fix audit
results.

The corrected manifest is ready for an explicitly approved clean v7/v7
rematerialization. Smoke training remains blocked until the replacement
artifact is materialized, audited, and accepted. Production/live use remains
closed.
