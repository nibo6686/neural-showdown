# First diagnostic_300 Training Plan

## Purpose

Train the smallest useful non-production model on the frozen
`diagnostic_300_v7_v5` artifact to detect loader, split, label, grouping, loss,
checkpoint, and metric wiring errors.

This run is not intended to establish playing strength, replace a live model,
change defaults, tune a production architecture, create action-value targets,
or justify a larger replay rebuild.

**Training has not been run.**

## Dataset Contract

- Dataset:
  `artifacts\training_plan\datasets\diagnostic_300_v7_v5\diagnostic_300_v7_v5.npz`
- Metadata:
  `artifacts\training_plan\datasets\diagnostic_300_v7_v5\feature_metadata.json`
- State schema: `live-private-belief-v7`, 3208D
- Action schema: `legal-action-v5`, 318D
- On-disk dtype: float16; cast batches to float32 for the first diagnostic run
- Layout: one state row per decision plus separate candidate/action rows linked
  by `candidate_state_indices`; state vectors must not be duplicated
- Fixed battle splits: 210 train / 45 validation / 45 test
- State rows: 20,713 train / 2,255 validation / 2,428 test
- Matched action-rank groups: 19,944 train / 2,254 validation / 2,426 test

The loader must verify schema versions, dimensions, ordered-name fingerprints,
manifest checksum, candidate index bounds, one split per battle, and exactly
one positive in every included action-rank group before creating a model.

The current `train_value` and `train_action_ranker` entrypoints must not be used
directly. They expect older array layouts and create random row/group splits,
which would discard the frozen battle-level split and, for action rank, require
duplicating state rows.

## Training Objective

Use one small multitask model:

- State encoder: `3208 -> 64`, ReLU.
- Value head: `64 -> 1`, tanh output.
- Action encoder: `318 -> 32`, ReLU.
- Rank head: concatenate the 64D state embedding and 32D action embedding,
  then `96 -> 32 -> 1` with ReLU.
- Approximate parameter count: 218,786.
- No dropout and no mixed precision for this first wiring run.

State value uses all valid state rows. The target is acting-side terminal
outcome: win `+1`, loss `-1`. Use mean squared error with weight `1.0`.

Action rank uses only candidates whose `candidate_state_indices` identify a
matched decision group with exactly one positive in `action_rank_labels`. Use
grouped cross-entropy over legal candidates with weight `1.0`. Unchosen legal
candidates remain alternatives within the softmax; they are not independent
negative or “bad action” labels.

The 772 unmatched groups and 600 initial-deployment non-decisions are already
absent from action candidate groups or explicitly audited. The loader must
ignore any group without exactly one positive and report it as an error against
the frozen artifact. There is no action-value/Q-value head or loss.

## Proposed Configuration

Configuration:
`configs\diagnostic_300_v7_v5.first.windows.json`

- Seed: `20260619`
- Optimizer: AdamW
- Learning rate: `1e-3`
- Weight decay: `1e-4`
- Gradient clipping: `1.0`
- Value batch: 256 states
- Rank batch: 64 decision groups
- Maximum epochs: 10
- Save every epoch
- Stop when neither validation value MSE nor validation action-rank NLL
  improves for two epochs
- Select using validation only; evaluate the test split once after selection
- Output:
  `artifacts\diagnostic_training\diagnostic_300_v7_v5_first\`

The test split must not affect architecture, stopping, checkpoint selection, or
threshold changes.

## Mandatory Preflight and Overfit Checks

Before optimization, validate the complete dataset/metadata contract and print
split row/group counts. Abort before creating an output checkpoint on any
mismatch.

Then overfit a deterministic training subset of 128 state rows and 64 matched
action groups. Within 2,000 steps, require:

- value training MSE at or below `0.02`;
- action-rank training top-1 at or above `95%`;
- finite losses, gradients, scores, and predictions.

Failure means a likely loader, grouping, target, or optimization bug; do not
continue to the full diagnostic run.

## Metrics and Expected Signals

Log each epoch:

- value train/validation MSE, sign accuracy, prediction mean/std, win/loss
  calibration, and constant-prediction baseline;
- action-rank train/validation grouped NLL, top-1, top-3, MRR, candidates per
  group, accuracy by action kind and turn bucket, and recommendation slot
  distribution;
- both loss weights, learning rate, gradient norm, epoch time, peak GPU memory,
  seed, split counts, schema versions, dimensions, and checkpoint path.

Validation value labels are essentially balanced: the constant-mean MSE is
approximately `1.0`. Validation action baselines are approximately `16.8%`
for uniform random legal choice and `30.9%` for always selecting action slot
zero.

The first run is a useful success if preflight and overfit checks pass, losses
remain finite, validation value MSE improves below the constant baseline, and
validation action top-1 exceeds the slot-zero baseline without a degenerate
recommendation distribution. Failure to beat these baselines is not proof that
the schemas are wrong, but it blocks scaling and requires inspection.

Run the existing stat/type/item/ability/species/status/Tera/field/move,
constraint, immunity, unavailable-action, switch, Draco, perspective, and
privacy sanity cases against the selected checkpoint before considering any
larger run.

## Proposed Commands

The currently available config syntax/path check is:

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
@'
from neural.config import load_config, resolve_path

config = load_config(r".\configs\diagnostic_300_v7_v5.first.windows.json")
for key in ("path", "metadata_path", "materialization_report_path"):
    path = resolve_path(config, config["dataset"][key])
    assert path.is_file(), path
print("diagnostic config syntax and input paths: OK")
'@ | D:\Anaconda\envs\neuralgpu\python.exe -
```

This check does not create a model or launch training.

The intended read-only validation command is:

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
D:\Anaconda\envs\neuralgpu\python.exe -m neural.train_vnext_diagnostic `
  --config .\configs\diagnostic_300_v7_v5.first.windows.json `
  --validate-only
```

The intended first training command, only after review and explicit approval,
is:

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
D:\Anaconda\envs\neuralgpu\python.exe -m neural.train_vnext_diagnostic `
  --config .\configs\diagnostic_300_v7_v5.first.windows.json
```

`neural.train_vnext_diagnostic` is implemented. Its `--validate-only` path
loads and validates the complete native-layout artifact, instantiates the model,
and runs no-grad value/rank forward and loss checks without creating an
optimizer, checkpoint, report directory, or training step.

The real-artifact validation passed with 25,396 states, 189,957 candidates,
24,624 matched action groups, zero zero-positive candidate groups, zero
action-value labels, exact 210/45/45 battle splits, and the expected
218,786-parameter model. Training was not launched.

## Risks and Limitations

- Terminal outcomes are noisy supervision for early-game states.
- Public replay reconstruction uses the documented own-side future-public-reveal
  assumption.
- Unmatched action decisions reduce imitation coverage by 772 groups.
- The shared encoder can cause objective interference; this run measures that
  wiring rather than resolving it.
- The sample is too small for confident playing-strength conclusions.
- Passing offline metrics does not make the checkpoint production eligible.

## Approval Gate

The plan/config/command and native-layout entrypoint are implemented, but
training remains unlaunched and the gate remains closed. The user must review
the validation results and explicitly approve the first diagnostic run.
