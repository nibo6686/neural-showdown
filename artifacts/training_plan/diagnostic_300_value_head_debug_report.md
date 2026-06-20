# diagnostic_300 Value-Head Debug Report

## Purpose

Explain why the first frozen v7/v5 diagnostic model fit its value training
labels but performed worse than a constant baseline on held-out battles.

This was a read-only analysis of the existing dataset and checkpoints. No
optimizer was created, no checkpoint was changed, and no new training run was
launched. Test predictions were not recomputed; test numbers below are only
quoted from the existing first-run report.

## Inputs Inspected

- `configs\diagnostic_300_v7_v5.first.windows.json`
- `artifacts\training_plan\datasets\diagnostic_300_v7_v5\`
- `artifacts\diagnostic_training\diagnostic_300_v7_v5_first\model.best.pt`
- `artifacts\diagnostic_training\diagnostic_300_v7_v5_first\model.pt`
- `artifacts\diagnostic_training\diagnostic_300_v7_v5_first\training_report.json`
- `trainer\src\neural\train_vnext_diagnostic.py`
- `trainer\src\neural\models\vnext_diagnostic.py`
- all 300 manifest replay logs for label/perspective verification

## Commands Run

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
D:\Anaconda\envs\neuralgpu\python.exe -m unittest `
  trainer.tests.test_diagnose_vnext_value_head

D:\Anaconda\envs\neuralgpu\python.exe -m neural.diagnose_vnext_value_head `
  --config .\configs\diagnostic_300_v7_v5.first.windows.json `
  --checkpoint-dir .\artifacts\diagnostic_training\diagnostic_300_v7_v5_first
```

Only train and validation states were scored by the debug command.

## Checkpoints Evaluated

- `model.best.pt`: epoch 8, step 2,496. This checkpoint was selected because
  action-rank validation NLL improved, not because value validation improved.
- `model.pt`: epoch 10, step 3,120.

The value head's best recorded validation MSE was at epoch 1 (`1.2921`), but no
epoch-1 checkpoint was retained. Even that result was worse than the validation
constant-mean baseline (`0.99999`), so checkpoint selection is an aggravating
factor rather than the root cause.

## Train/Validation Metrics

| Checkpoint | Split | MSE | Constant baseline | Sign accuracy | Prediction mean/std | `abs(pred) >= 0.95` |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| epoch 8 best | train | 0.0132 | 1.0000 | 99.97% | -0.040 / 0.951 | 72.87% |
| epoch 8 best | validation | 1.4728 | 1.0000 | 56.23% | -0.022 / 0.816 | 43.24% |
| epoch 10 latest | train | 0.0108 | 1.0000 | 99.99% | -0.031 / 0.960 | 79.40% |
| epoch 10 latest | validation | 1.5094 | 1.0000 | 54.77% | -0.027 / 0.817 | 43.81% |

For the epoch-8 checkpoint, validation predictions ranged from `-0.99998` to
`+0.99998`; 23.99% had absolute value at least `0.99`. The model is not merely
slightly miscalibrated. It makes many highly confident predictions on unseen
battles and is wrong often enough that MSE exceeds the neutral baseline.

The existing first-run report recorded test MSE `1.4523` and sign accuracy
`55.64%`. The test split was not scored again during this debug pass.

## Target and Class Breakdown

Targets are balanced:

- Train: 10,293 wins / 10,420 losses; mean `-0.0061`.
- Validation: 1,124 wins / 1,131 losses; mean `-0.0031`.

Epoch-8 validation:

| Target | Count | MSE | Sign accuracy | Prediction mean/std |
| --- | ---: | ---: | ---: | ---: |
| win `+1` | 1,124 | 1.4850 | 55.16% | 0.075 / 0.793 |
| loss `-1` | 1,131 | 1.4607 | 57.29% | -0.119 / 0.827 |

Both classes fail similarly. There is no evidence that one label class is
inverted, missing, or driving the problem alone.

## Game-Phase Breakdown

Epoch-8 validation:

| Phase | States | MSE | Sign accuracy | `abs(pred) >= 0.95` |
| --- | ---: | ---: | ---: | ---: |
| Turns 1-5 | 484 | 1.4630 | 55.37% | 36.78% |
| Turns 6-15 | 852 | 1.3945 | 57.98% | 40.49% |
| Turns 16+ | 919 | 1.5506 | 55.06% | 49.18% |

Later states are not rescued by being closer to the terminal outcome. They are
more saturated and have the worst MSE, which is consistent with confident
battle memorization rather than a simple lack of early-game signal.

## Battle-Level Error

For epoch 8 on the 45 validation battles:

- Median battle MSE: `1.1918`
- 90th-percentile battle MSE: `3.3316`
- Maximum battle MSE: `3.8868`
- Top five battles contribute 38.1% of total squared error
- Top ten battles contribute 61.8% of total squared error

The five worst battles had zero sign accuracy, showing that some battles are
almost completely predicted in the wrong direction. However, the median battle
also performs worse than the constant baseline, so the failure is widespread
and not explained by only a few corrupted/pathological replays.

## Label and Perspective Audit

The original replay winner was reparsed for every manifest battle and compared
with every stored acting-side label:

- Battles checked: 300
- Battles with both p1 and p2 states represented: 300
- p1-only or p2-only battles: 0
- Unknown winners: 0
- Within-side label inconsistencies: 0
- Acting-side perspective mismatches: 0

For every checked state, the winner's acting side has `+1` and the loser's
acting side has `-1`. Label perspective is correct and is not the observed
failure source.

Train and validation side representation is also balanced:

- Train: 10,225 p1 / 10,488 p2 states
- Validation: 1,134 p1 / 1,121 p2 states

## Duplicate and Correlation Audit

Across train plus validation:

- Exact float16 duplicate groups: 9, covering 20 states (0.087% of rows)
- Cross-battle duplicate groups: 0
- Cross-split duplicate groups: 0
- Duplicate groups with conflicting labels: 0
- A coarse two-decimal fingerprint produced the same counts

Duplicate or near-duplicate leakage is therefore not a plausible explanation.

Battle-level correlation is a much stronger concern. The apparent 20,713
training rows come from only 210 independent battles. All states from one
battle share the same terminal outcome per acting side and strongly related
teams, identities, and trajectories. The model reaches nearly 100% train sign
accuracy, including 99.87% on turns 1-5, which is implausibly strong evidence of
battle/team memorization rather than transferable state-value estimation.

## Shared-Trunk and Loss Analysis

The configured value and rank loss weights are both `1.0`, but their update
frequency is not balanced:

- Value batches per epoch: 81
- Rank batches per epoch: 312
- Joint value/rank steps: 81
- Rank-only steps: 231
- Rank-only share of optimizer steps: 74.04%

Rank-only steps still update the shared state encoder. Thus equal scalar loss
weights do not mean equal influence on the shared representation. The action
head can continue moving the encoder after all value batches in an epoch. This
is a credible source of interference and explains why the retained checkpoint
tracks rank improvement while value validation remains poor.

The tanh output plus MSE against exact `-1/+1` targets also encourages saturated
training predictions. A confidently wrong near-opposite prediction contributes
close to the maximum squared error of 4. This amplifies validation damage once
the model memorizes training battles, but it does not indicate a label-wiring
bug.

## Likely Cause Ranking

1. **Small effective sample size and battle-level memorization — high
   confidence.** There are only 210 independent training battles, while the
   model has 218,786 parameters and nearly perfectly classifies training states.
2. **Overconfident tanh/MSE behavior — high confidence as an amplifier.**
   Validation predictions are heavily saturated, causing large penalties for
   confident wrong battles.
3. **Shared-encoder action-rank dominance/interference — medium-high
   confidence.** Seventy-four percent of updates are rank-only, and checkpoint
   retention follows either-head improvement.
4. **Terminal-outcome objective noise — medium confidence.** Every state in a
   battle receives the terminal result; early states and tactically ambiguous
   positions therefore have noisy supervision, although late-state results are
   also poor here.
5. **Label/perspective or split wiring bug — low confidence.** Direct audits
   found no mismatches, leakage, class imbalance, or duplicate conflict.

## Conclusion

This does **not** look like a state-label perspective bug or a dataset split
bug. It is most consistent with severe small-battle overfitting, highly
saturated value predictions, and likely shared-trunk interference from the
much more frequent rank updates.

The value head is **not safe to continue with as-is** for another combined
experiment or for any live use.

## Recommended Next Experiment

Design exactly one value-only isolation run on the same frozen train/validation
splits:

- use the same 3208D state input and small 64D encoder/value head;
- disable the action-rank objective entirely so every optimizer step is
  value-driven;
- select and stop only on validation value MSE;
- retain all other data, seed, target, and initial optimizer settings.

This single change isolates shared-head interference and checkpoint-selection
effects. If value-only validation still fails near epoch 1, the next decision
should focus on battle-balanced regularization or the terminal-outcome
objective—not on the action head.

No new training run was launched during this debug pass.
