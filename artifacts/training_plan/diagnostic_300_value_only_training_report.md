# diagnostic_300 Value-Only Isolation Training Report

## Purpose and Scope

Run exactly one controlled value-only experiment on the frozen
`diagnostic_300_v7_v5` dataset to determine whether the state-value head can
generalize when action-rank updates are removed from the shared encoder.

The dataset, battle splits, seed, state encoder shape, tanh value output,
optimizer family, learning rate, weight decay, batch size, and maximum epoch
count match the first multitask diagnostic run. Action rank and action value
were disabled. No hyperparameter search, repeated run, checkpoint promotion,
live-default change, larger dataset, or model-strength evaluation occurred.

## Config and Commands

Config:

`configs\diagnostic_300_v7_v5.value_only.windows.json`

Validation:

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
D:\Anaconda\envs\neuralgpu\python.exe -m neural.train_vnext_diagnostic `
  --config .\configs\diagnostic_300_v7_v5.value_only.windows.json `
  --validate-only
```

Training:

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
D:\Anaconda\envs\neuralgpu\python.exe -m neural.train_vnext_diagnostic `
  --config .\configs\diagnostic_300_v7_v5.value_only.windows.json
```

The training command was launched once.

## Validate-Only Result

Validation passed before training:

- dataset, schema dimensions, and ordered-name fingerprints matched;
- battle split integrity remained 210 train / 45 validation / 45 test;
- state labels were only `-1/+1`;
- action-value labels were absent;
- action rank was disabled with loss weight zero;
- the no-grad value output/loss path was finite;
- rank candidates, rank loss, and rank gradient contribution were zero;
- optimizer created: no; optimizer steps: zero.

## Runtime and Outputs

- Device: CUDA
- Epochs completed: 3 (early stopped after two non-improving epochs)
- Main optimizer steps: 243, exactly 81 value batches per epoch
- Reported training-loop runtime: 4.29 seconds
- End-to-end command wall time: approximately 11.1 seconds
- Output directory:
  `artifacts\diagnostic_training\diagnostic_300_v7_v5_value_only\`
- Best checkpoint: `model.best.pt`, epoch 1, step 81
- Latest checkpoint: `model.pt`, epoch 3, step 243
- Checkpoint selection: validation value MSE only
- Test split evaluations: exactly one, after restoring selected weights
- Production eligible: no

Files produced:

- `model.pt`
- `model.best.pt`
- `training_report.json`
- `training_report.md`

## Objective Isolation

- State value trained: yes
- Action rank trained: no
- Action-rank metrics computed during training/test: no
- Action-value/Q-value target used: no
- Optimizer parameters: state encoder and value head only
- Optimizer step source: value batches only

## Mandatory Overfit Check

The value-only tiny-subset check passed after 25 steps:

- State examples: 128
- Value train MSE: 0.000309
- Action groups: 0
- Action-rank loss: not evaluated

## Train and Validation Metrics

The table uses full-split post-epoch metrics.

| Epoch | Steps | Train MSE | Train sign accuracy | Train `abs(pred) >= 0.95` | Validation MSE | Validation sign accuracy | Validation `abs(pred) >= 0.95` |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 81 | 0.1252 | 97.28% | 21.84% | 1.1321 | 56.90% | 4.66% |
| 2 | 162 | 0.0458 | 99.37% | 48.16% | 1.2740 | 57.21% | 14.55% |
| 3 | 243 | 0.0224 | 99.77% | 62.53% | 1.3688 | 57.38% | 26.08% |

The constant-mean validation baseline is `0.99999`; the constant-zero baseline
is `1.0`. Epoch 1 was selected, but its validation MSE remained 13.2% worse than
the baseline. Continued training rapidly reduced train error while worsening
validation error and increasing saturation.

At the selected epoch:

- Validation prediction mean/std: `0.113 / 0.582`
- Validation prediction min/max: `-0.987 / +0.997`
- Validation `abs(pred) >= 0.90`: 11.13%
- Validation `abs(pred) >= 0.95`: 4.66%
- Validation `abs(pred) >= 0.99`: 0.18%

## Final Test Metrics

The test split was touched exactly once after selecting and restoring the
epoch-1 checkpoint:

- Test MSE: `1.0524`
- Test sign accuracy: `61.78%`
- Constant-mean baseline MSE: approximately `1.0`
- Constant-zero baseline MSE: `1.0`
- Prediction mean/std: `0.092 / 0.587`
- Prediction min/max: `-0.987 / +0.996`
- `abs(pred) >= 0.90`: 9.93%
- `abs(pred) >= 0.95`: 4.90%
- `abs(pred) >= 0.99`: 0.37%

The selected model still failed to beat the test MSE baseline, although its
sign accuracy was above chance.

## Comparison With the Multitask Run

| Metric | Multitask | Value-only | Change |
| --- | ---: | ---: | ---: |
| Best validation MSE | 1.2921 | 1.1321 | 12.4% lower |
| Test MSE | 1.4523 | 1.0524 | 27.5% lower |
| Test sign accuracy | 55.64% | 61.78% | +6.14 points |
| Test prediction std | 0.801 | 0.587 | less extreme |
| Test `abs(pred) >= 0.95` | not recorded in first report | 4.90% | n/a |
| Best checkpoint epoch | value best at 1, retained multitask at 8 | 1 | value-selected |

Removing rank updates materially improved value generalization and reduced
overconfidence. This confirms shared-trunk rank interference and checkpoint
selection were real contributors.

However, value-only training still overfit after one epoch and never beat the
constant MSE baseline. Rank interference was therefore not the root cause by
itself. The remaining failure is consistent with only 210 independent training
battles, high-capacity identity/team memorization, and noisy terminal-outcome
targets.

## Interpretation

The value head shows some transferable sign signal under isolation, but it is
not yet viable as a calibrated value regressor on `diagnostic_300`. It should
not continue unchanged and neither checkpoint is suitable for live use.

This controlled run narrows the next decision:

- shared-head interference is real but secondary;
- the dominant remaining problem is small-battle overfitting/capacity relative
  to the effective sample size;
- tanh/MSE saturation grows rapidly after epoch 1, but the selected epoch still
  misses the baseline.

## Recommended Next Task

Review the multitask and value-only results and choose one controlled
regularization/capacity experiment. The cleanest next experiment is a
reduced-capacity value-only model with battle-balanced sampling or weighting,
while retaining the same frozen split and selecting solely by validation value
MSE. Do not promote either diagnostic checkpoint.
