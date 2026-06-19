# Pre-Training Gate Status

**Date:** 2026-06-19

`live-private-belief-v7` and `legal-action-v5` are ready for disposable,
non-production diagnostic dataset work **after this Git checkpoint is committed
and pushed**.

Full production reindexing/retraining remains blocked by:

- combined effective-order and normalized raw-stat gaps;
- richer switch-candidate representation;
- compact public-belief content rather than counts alone;
- authoritative full-transition consequences;
- feature-build/storage measurements and small/medium benchmark evidence.

Training is not the next step. After the checkpoint, implement the lightweight
replay-pool profiler and generate the battle-level `diagnostic_300` manifest.
Then benchmark v7/v5 feature generation, define labels and verify battle-level
train/validation/test separation. Do not begin full dataset materialization or
training until those gates pass.
