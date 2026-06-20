# diagnostic_300 Reduced-Capacity Regularized Value-Only Training Report

## Purpose and Scope

Run exactly one reduced-capacity, regularized value-only experiment on the
frozen `diagnostic_300_v7_v5` split to determine whether the prior value-head
failure was driven mainly by over-capacity memorization on only 210 independent
training battles.

The dataset, labels, battle splits, seed, optimizer family (AdamW), learning
rate, value batch size, tanh value output, and MSE value loss match the prior
value-only run. Only model capacity and regularization changed. Action rank and
action value were disabled. No dataset/label/split/schema/target change, no
hyperparameter search, no repeated run, no checkpoint promotion, and no
live-default change occurred.

## Config and Commands

Config: `configs\diagnostic_300_v7_v5.value_only_small_reg.windows.json`

Validate-only:

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
D:\Anaconda\envs\neuralgpu\python.exe -m neural.train_vnext_diagnostic `
  --config .\configs\diagnostic_300_v7_v5.value_only_small_reg.windows.json `
  --validate-only
```

Training (launched once):

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
D:\Anaconda\envs\neuralgpu\python.exe -m neural.train_vnext_diagnostic `
  --config .\configs\diagnostic_300_v7_v5.value_only_small_reg.windows.json
```

No code changes were required: `model.dropout` and `training.weight_decay` were
already plumbed through the entrypoint.

## Validate-Only Result

Validation passed before training:

- dataset, schema dimensions, and ordered-name fingerprints matched;
- battle split integrity remained 210 train / 45 validation / 45 test;
- state labels were only `-1/+1`; action-value labels were absent (0);
- action rank was disabled with loss weight zero;
- the no-grad value output/loss path was finite (smoke value loss `0.9595`);
- rank candidates, rank loss, and rank gradient contribution were zero;
- optimizer created: no; optimizer steps: zero;
- parameter count: **63,170** (reduced from the prior **218,786**).

## Runtime, Device, and Outputs

- Device: CUDA
- Epochs completed: 3 (early stopped after two non-improving epochs)
- Main optimizer steps: 243 (81 value batches per epoch, value-only)
- Reported training-loop runtime: 2.62 seconds
- Output directory:
  `artifacts\diagnostic_training\diagnostic_300_v7_v5_value_only_small_reg\`
- Best checkpoint: `model.best.pt`, epoch 1, step 81
- Latest checkpoint: `model.pt`, epoch 3, step 243
- Checkpoint selection: validation value MSE only
- Test split evaluations: exactly one, after restoring the selected weights
- Production eligible: no

## Model Parameter Count and Regularization

| Setting | Prior value-only | This run |
| --- | ---: | ---: |
| Total parameters | 218,786 | **63,170** |
| State encoder hidden | [64] | **[16]** |
| Value-relevant params (state encoder + value head) | 205,441 | **~51,361** |
| Dropout | 0.0 | **0.3** |
| Weight decay | 0.0001 | **0.01** |

The action encoder ([32]) and rank head ([32]) sizes were left unchanged; they
are not trained in the value-only objective and only pad the total count.

## Objective Isolation

- State value trained: yes
- Action rank trained: no; rank metrics not computed
- Action-value/Q-value target used: no
- Optimizer parameters: state encoder and value head only
- Optimizer step source: value batches only

## Mandatory Overfit Check

Passed after 25 steps on 128 examples (eval, dropout off):

- Value train MSE: `0.005223`
- Action groups: 0; action-rank loss not evaluated

## Train and Validation Metrics by Epoch

Full-split post-epoch metrics:

| Epoch | Steps | Train MSE | Train sign | Train `\|pred\|>=0.95` | Val MSE | Val sign | Val `\|pred\|>=0.95` |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 81 | 0.2784 | 92.80% | 0.48% | **0.9478** | 60.98% | 0.04% |
| 2 | 162 | 0.1292 | 97.19% | 13.75% | 1.0974 | 58.05% | 0.58% |
| 3 | 243 | 0.0744 | 98.68% | 30.56% | 1.2209 | 55.39% | 2.79% |

Constant-mean validation baseline `0.99999`; constant-zero baseline `1.0`.

Epoch 1 was selected. Its validation MSE (`0.9478`) is **5.2% below** the
constant baseline — the first value-head configuration to beat it. Training
past epoch 1 again reduced train error while worsening validation error and
slowly raising saturation, but far more slowly than prior runs.

At the selected epoch (validation):

- prediction mean/std: `-0.018 / 0.498`
- prediction min/max: `-0.904 / +0.954`
- `\|pred\|>=0.90`: 0.71%; `\|pred\|>=0.95`: 0.04%; `\|pred\|>=0.99`: 0.00%

## Final Test Metrics

Test split touched exactly once after selecting/restoring the epoch-1
checkpoint:

- Test MSE: **0.9453**
- Test sign accuracy: **63.14%**
- Constant-mean baseline MSE: `~1.0`; constant-zero baseline MSE: `1.0`
- Prediction mean/std: `0.024 / 0.489`
- Prediction min/max: `-0.895 / +0.919`
- `\|pred\|>=0.90`: 0.21%; `\|pred\|>=0.95`: 0.00%; `\|pred\|>=0.99`: 0.00%

The selected model beat the test MSE baseline by ~5.5% with no saturated
predictions.

## Comparison With the Prior Value-Only Run

| Metric | Prior value-only | Small + regularized | Change |
| --- | ---: | ---: | ---: |
| Total parameters | 218,786 | 63,170 | -71% |
| Best validation MSE | 1.1321 | **0.9478** | 16.3% lower |
| Test MSE | 1.0524 | **0.9453** | 10.2% lower |
| Test sign accuracy | 61.78% | **63.14%** | +1.36 pts |
| Test prediction std | 0.587 | 0.489 | less extreme |
| Test `\|pred\|>=0.95` | 4.90% | **0.00%** | saturation removed |
| Best checkpoint epoch | 1 | 1 | same |

## Interpretation: Did Generalization Improve Enough to Continue?

Yes, marginally. Reducing the value-relevant capacity ~4x and adding dropout
plus stronger weight decay moved the value head from *failing to beat* the
constant baseline to *modestly beating* it on both validation (0.9478) and test
(0.9453), eliminated extreme-prediction saturation, and slowed the post-epoch-1
overfitting that dominated earlier runs.

This confirms the prior diagnosis: over-capacity memorization on only 210
independent training battles was the dominant remaining failure mode, with
shared-head rank interference a real but secondary contributor.

However, the win is small (~5% under baseline) and the head still overfits
after a single epoch — the effective training signal from 210 battles is thin.
The value head is usable as a weak above-baseline signal but is not yet a
calibrated regressor and remains unsuitable for live use.

## Recommended Next Task

Stop further single-config capacity/regularization tuning on `diagnostic_300`:
the over-capacity hypothesis is confirmed and the achievable margin on 210
training battles is small. Per the standing decision rule, the next value-head
progress requires more independent battles, not more tuning of this split.
Recommend pausing value-head work and seeking explicit approval to move value
learning to a larger diagnostic dataset (e.g. the planned 1000/5000 benchmarks),
keeping the same v7/v5 schemas, value target, and frozen-split discipline. Until
then, the action-rank head — which already generalizes well — remains the more
productive track toward private-match testing. No checkpoint is promotion-ready.
