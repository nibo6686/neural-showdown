# First diagnostic_300 Training Run Report

## Purpose and Scope

This was the single approved non-production diagnostic run for the frozen
`diagnostic_300_v7_v5` dataset. Its purpose was to verify native-layout loading,
fixed battle splits, multitask forward/backward wiring, grouped action-rank
loss, state-value loss, mandatory overfit behavior, metric reporting, and
checkpoint writing.

No hyperparameter tuning, repeated experiment, larger dataset, live-default
change, checkpoint promotion, or playing-strength evaluation was performed.

## Dataset and Configuration

- Config: `configs\diagnostic_300_v7_v5.first.windows.json`
- Dataset:
  `artifacts\training_plan\datasets\diagnostic_300_v7_v5\diagnostic_300_v7_v5.npz`
- Battle splits: 210 train / 45 validation / 45 test
- State rows: 20,713 train / 2,255 validation / 2,428 test
- Matched action groups: 19,944 train / 2,254 validation / 2,426 test
- State schema: `live-private-belief-v7`, 3208D
- Action schema: `legal-action-v5`, 318D
- Model: 218,786-parameter shared-state multitask MLP
- State target: acting-side terminal outcome, `+1/-1`
- Action target: grouped replay-action imitation
- Action-value/Q-value target: absent

## Validation Before Training

The required `--validate-only` command passed immediately:

- exact schema versions, dimensions, and ordered-name fingerprints;
- exact 210/45/45 battle split counts with no leakage;
- 25,396 states and 189,957 action candidates;
- 24,624 included one-positive action groups;
- zero malformed or zero-positive candidate groups;
- zero action-value labels;
- correct value and rank output shapes;
- finite no-grad smoke losses;
- optimizer created: no; optimizer steps: 0.

## Training Command

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
D:\Anaconda\envs\neuralgpu\python.exe -m neural.train_vnext_diagnostic `
  --config .\configs\diagnostic_300_v7_v5.first.windows.json
```

The command was launched once.

## Runtime and Outputs

- Device: CUDA
- Epochs completed: 10 / 10
- Optimizer steps: 3,120
- Reported training runtime: 124.33 seconds
- End-to-end command wall time: approximately 136 seconds
- Output directory:
  `artifacts\diagnostic_training\diagnostic_300_v7_v5_first\`
- Latest checkpoint: `model.pt`, epoch 10
- Best validation checkpoint: `model.best.pt`, epoch 8
- Test split: evaluated once after validation selection, as configured
- Production eligible: no

Files produced:

- `model.pt`
- `model.best.pt`
- `training_report.json`
- `training_report.md`

All reported losses and metrics were finite.

## Mandatory Overfit Check

The deterministic tiny-subset check passed after 200 steps:

- State examples: 128
- Action groups: 64
- Value train MSE: 0.000178
- Action-rank train NLL: 0.3788
- Action-rank train top-1: 95.31%

This is strong evidence that the loader, labels, grouped loss, gradients, and
both model heads are wired sufficiently to fit a small controlled subset.

## Epoch Metrics

| Epoch | Value train MSE | Value validation MSE | Value validation sign accuracy | Rank train NLL | Rank validation NLL | Rank validation top-1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.3844 | 1.2921 | 54.55% | 1.6339 | 1.4814 | 37.71% |
| 2 | 0.0950 | 1.4782 | 53.75% | 1.4892 | 1.3945 | 41.97% |
| 3 | 0.0419 | 1.6283 | 51.57% | 1.4154 | 1.3290 | 44.99% |
| 4 | 0.0338 | 1.4078 | 56.81% | 1.3800 | 1.3130 | 45.61% |
| 5 | 0.0131 | 1.4401 | 56.59% | 1.3572 | 1.3202 | 45.83% |
| 6 | 0.0091 | 1.4623 | 56.41% | 1.3397 | 1.2998 | 45.39% |
| 7 | 0.0080 | 1.4637 | 56.27% | 1.3186 | 1.2813 | 46.41% |
| 8 | 0.0065 | 1.4728 | 56.23% | 1.3049 | 1.2785 | 45.56% |
| 9 | 0.0052 | 1.5097 | 54.59% | 1.2906 | 1.2984 | 45.92% |
| 10 | 0.0046 | 1.5094 | 54.77% | 1.2786 | 1.2905 | 45.96% |

The best checkpoint was written at epoch 8, when validation action-rank NLL
reached its minimum. The best value validation MSE occurred at epoch 1.

## Held-Out Test Metrics

The test split was touched once after model selection:

- State-value MSE: 1.4523
- State-value sign accuracy: 55.64%
- State-value constant baseline MSE: approximately 1.0000
- Action-rank NLL: 1.3511
- Action-rank top-1: 43.57%
- Action-rank top-3: 83.02%
- Action-rank MRR: 0.6452

The action-rank test top-1 exceeded the documented slot-zero test baseline of
32.07% and the random-choice baseline of approximately 16.78%.

## Interpretation

The run **passed as a training-wiring sanity check with a material value-head
warning**:

- validation, loading, split isolation, forward/backward computation, grouped
  imitation loss, metric reporting, output writing, and checkpoint writing all
  worked;
- the mandatory overfit check passed for both heads;
- the action-rank head showed useful held-out learning above simple baselines;
- the state-value head strongly fit training data but failed to beat the
  constant validation/test baseline, indicating severe overfit, objective
  difficulty, shared-encoder interference, or a remaining value-specific
  generalization issue.

The checkpoint is diagnostic only and must not be promoted or used as a live
default.

## Limitations and Warnings

- Terminal outcomes are noisy targets for early battle states.
- This is one small run with no hyperparameter search or uncertainty estimate.
- The shared encoder may allow the two objectives to interfere.
- Validation checkpoint selection was driven by continued action-rank NLL
  improvement even while value validation remained poor.
- Existing feature-reconstruction assumptions and unmatched-action coverage
  limitations remain unchanged.

## Recommended Next Task

Review these metrics and perform a targeted value-head sanity/debug design
before approving another experiment. The next design should isolate whether the
failure comes from the terminal-outcome target, battle-correlated examples,
shared-encoder interference, or value-model capacity/regularization. Do not
promote this checkpoint.
