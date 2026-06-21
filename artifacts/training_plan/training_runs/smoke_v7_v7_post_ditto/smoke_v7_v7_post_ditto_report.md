# v7/v7 Post-Ditto Smoke Training Report

The explicitly approved one-epoch smoke/plumbing run completed successfully on
CUDA with exit code 0. It used the post-Ditto diagnostic dataset and did not
promote a checkpoint or change live/default behavior.

## Inputs and outputs

- Config:
  `artifacts/training_plan/training_runs/smoke_v7_v7_post_ditto/smoke_v7_v7_post_ditto_config.json`
- Dataset:
  `artifacts/training_plan/datasets/diagnostic_300_v7_v7_post_ditto/diagnostic_300_v7_v7_post_ditto.npz`
- JSON report:
  `artifacts/training_plan/training_runs/smoke_v7_v7_post_ditto/smoke_v7_v7_post_ditto_report.json`
- Epoch checkpoint:
  `artifacts/training_plan/training_runs/smoke_v7_v7_post_ditto/smoke_v7_v7_post_ditto.pt`
- Best checkpoint:
  `artifacts/training_plan/training_runs/smoke_v7_v7_post_ditto/smoke_v7_v7_post_ditto.best.pt`

## Schema and dataset validation

- State: `live-private-belief-v7`, 3208D,
  `0a697b427d64c4487e7513ae8a35d76387af6824f6f4404f62bac218a5e36fbf`
- Action: `legal-action-v7`, 552D,
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`
- States/candidates: 25,235 / 197,449
- Included action groups: 25,232; unmatched reported: 3
- Battle splits: 210 train / 45 validation / 45 test
- Manifest catalog checksum:
  `0ebbad4d9a0fa35e3e37f38d964b1d04fa77207870a66048221ec1461044b24e`

## Result

- Epochs/global steps: 1 / 2,569
- Runtime: 30.13s
- Heads trained: state value and action rank; action value disabled
- Tiny overfit check: passed in 1 step
- Train value MSE: 1.295563
- Validation value MSE: 1.483368
- Validation action-rank NLL/top-1/top-3/MRR:
  1.383279 / 0.434146 / 0.838137 / 0.646129
- Test value MSE/sign accuracy: 1.478658 / 0.510297
- Test action-rank NLL/top-1/top-3/MRR:
  1.414682 / 0.410626 / 0.815486 / 0.629890

Both checkpoints record epoch 1, global step 2,569, the exact state/action
versions, dimensions, ordered-name fingerprints, manifest checksum, trained
heads, and `production_eligible: false`. All numeric report values, dataset
arrays, and checkpoint tensors were checked and contain no NaN or Inf.

## Gate decision

The smoke training **passed as a plumbing/schema/checkpoint test**. Its one-epoch
quality metrics are diagnostic only: the value head does not beat the constant
baseline, and neither checkpoint is approved for durable training, promotion,
live evaluation, or production use. Generated JSON/checkpoint files remain
unstaged.
