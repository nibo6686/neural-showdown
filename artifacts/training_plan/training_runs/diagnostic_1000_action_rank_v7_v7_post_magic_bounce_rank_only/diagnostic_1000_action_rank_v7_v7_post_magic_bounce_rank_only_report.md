# 1,000-Battle v7/v7 Post-Magic-Bounce Rank-Only Training Report

The explicitly approved non-production rank-only diagnostic run completed
successfully on CUDA with exit code 0. It used the clean post-Magic-Bounce
1,000-battle dataset. State value and action value were disabled; only grouped
action-rank imitation updated the model.

No checkpoint was promoted, and no live default or live bot behavior changed.

## Inputs and outputs

- Source HEAD:
  `34760480f2b68ff0095096483118f43ed1936843`
- Config:
  `configs/diagnostic_1000_action_rank_v7_v7_post_ditto.rank_only.windows.json`
- Dataset:
  `artifacts/training_plan/datasets/diagnostic_1000_v7_v7_post_magic_bounce/diagnostic_1000_v7_v7_post_magic_bounce.npz`
- Console log:
  `artifacts/training_plan/training_runs/diagnostic_1000_action_rank_v7_v7_post_magic_bounce_rank_only/train.log`
- Generated JSON report:
  `artifacts/diagnostic_training/diagnostic_1000_action_rank_v7_v7_post_magic_bounce_rank_only/training_report.json`
- Final-epoch checkpoint:
  `artifacts/diagnostic_training/diagnostic_1000_action_rank_v7_v7_post_magic_bounce_rank_only/model.pt`
- Selected best checkpoint:
  `artifacts/diagnostic_training/diagnostic_1000_action_rank_v7_v7_post_magic_bounce_rank_only/model.best.pt`

Generated checkpoints, JSON reports, and logs remain unstaged.

## Dataset and schema validation

- Battles: 1,000, split 700 train / 150 validation / 150 test
- States/candidates: 80,635 / 617,555
- Included matched rank groups: 80,594
- Matched groups by split: 64,416 train / 7,851 validation / 8,327 test
- Quarantined unmatched actions reported: 41
- Initial-deployment nondecisions reported: 2,000
- State: `live-private-belief-v7`, 3208D,
  `0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf`
- Action: `legal-action-v7`, 552D,
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`
- Manifest catalog checksum:
  `0ebbad4d9a0fa35e3e37f38d964b1d04fa77207870a66048221ec1461044b24e`

The 41 unmatched groups are the audited public-replay Illusion ambiguity set.
No Magic Bounce residual category is present in the training artifact.

## Training result

- Device: CUDA
- Heads trained: action rank only
- Optimizer steps: rank batches only
- Model parameters: 226,274
- Runtime: 375.94 seconds
- Epochs/global steps: 10 / 10,070
- Early stopping: triggered after epochs 8-10 failed to improve the epoch-7
  validation rank NLL
- Tiny overfit check: passed in 250 steps
  - train rank NLL: 0.278328
  - train rank top-1: 0.968750
- Test split evaluations: exactly 1, after model selection

### Selected epoch 7 validation metrics

- Rank NLL: 1.175278
- Top-1: 0.515985
- Top-3: 0.888422
- MRR: 0.705594

### Held-out test metrics

- Rank NLL: 1.181397
- Top-1: 0.507626
- Top-3: 0.886274
- MRR: 0.700131

Validation NLL improved monotonically through epoch 7. The final three epochs
did not beat epoch 7, so `model.best.pt` is the correct selected checkpoint;
`model.pt` is retained only as the final epoch-10 checkpoint.

## Comparison with the prior 1,000-battle v7/v5 rank-only diagnostic

The earlier v7/v5 test result was NLL/top-1/top-3
1.3252 / 0.4608 / 0.8504. The new v7/v7 result is
1.181397 / 0.507626 / 0.886274:

- NLL improves by 0.1438;
- top-1 improves by 0.0468 absolute;
- top-3 improves by 0.0359 absolute.

This comparison supports the repaired typed-effect v7 action representation
and clean data path as a stronger diagnostic baseline. It is not by itself a
promotion decision because the action schema and reconstruction path changed
together, and production-oriented threat-awareness/live-parity gates remain
open.

## Checkpoint audit

Both checkpoint payloads contain:

- exact state/action schema versions, dimensions, and ordered-name
  fingerprints;
- the manifest catalog checksum;
- `heads_trained = {state_value: false, action_rank: true,
  action_value: false}`;
- checkpoint selection by `validation_action_rank_nll`;
- `production_eligible: false`.

`model.best.pt` records epoch 7 / global step 7,049.
`model.pt` records epoch 10 / global step 10,070.
All 10 model tensors in each checkpoint are finite.

SHA-256:

- `model.best.pt`:
  `4cecef1cd1f2dd37507f877d7177895d3da27300c4f40f88dce4bdaec0a06f0e`
- `model.pt`:
  `0a1a1f24d4949c5daf6e9a810332e5fe7e4024b05ef8adc7ae0ab39274b85819`

## Gate decision

The approved rank-only diagnostic training run **passes** its data-loading,
schema, optimization, overfit, early-stopping, checkpoint-selection, and
held-out evaluation gates. `model.best.pt` is the selected offline diagnostic
checkpoint.

This does not authorize checkpoint promotion, browser/live shadow use,
production use, autonomous play, or any live/default behavior change. Those
remain separately approval-gated and require the documented offline slice,
inference parity, live packet/slot mapping, latency, and threat-awareness
reviews.
