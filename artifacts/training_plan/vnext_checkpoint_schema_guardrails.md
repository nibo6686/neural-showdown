# vNext Checkpoint Schema Guardrails

Implements the primary schema-safety gap identified in
`legacy_pipeline_audit.md`: vNext checkpoints recorded schema version + dims but
not feature-name fingerprints, so version+dim match did not prove identical
feature ordering. No models were trained, no live defaults changed, no
checkpoints promoted, and no existing checkpoints were rewritten.

## What Changed

`trainer/src/neural/train_vnext_diagnostic.py`:

- **`build_vnext_checkpoint_metadata(dataset)`** — returns the schema-identity
  block embedded in every newly saved vNext checkpoint:
  - `state_feature_version`, `action_feature_version`
  - `state_dim`, `action_dim`
  - `state_feature_names_sha256`, `action_feature_names_sha256` (ordered
    feature-name fingerprints, taken from the validated dataset)
  - `manifest_catalog_checksum` (dataset/config identifier already available)
- The training checkpoint payload now merges this block instead of hardcoding
  only version + dim. Fingerprints are derived from the same validated
  `dataset.validation` the loader already computes, so they cannot drift from
  the dataset they were trained on.
- **`validate_vnext_checkpoint_metadata(checkpoint, ...)`** — strict reusable
  validator for future vNext model loading. It:
  - requires and matches `state_feature_version` / `action_feature_version`;
  - requires and matches `state_dim` / `action_dim`;
  - matches fingerprints **when an expected value is supplied**;
  - raises a clear `ValueError` on any name/dim/fingerprint mismatch;
  - reports missing fingerprints as `"missing_legacy"` (never silently
    "equivalent"), and rejects them outright when `require_fingerprints=True`.

The validator returns a status dict (`state_fingerprint_status`,
`action_fingerprint_status`, `fingerprints_complete`) so callers can distinguish
`validated` / `present_unverified` / `missing_legacy` explicitly.

## Tests Added

`trainer/tests/test_train_vnext_diagnostic.py` (new `VNextCheckpointSchemaGuardrailTest`):

- built metadata includes state/action fingerprints;
- a freshly trained checkpoint payload on disk includes the fingerprints;
- matching metadata passes (both fingerprints `validated`);
- wrong state schema fails; wrong action schema fails;
- wrong state dimension fails; wrong action dimension fails;
- a reordered feature-name fingerprint fails;
- missing fingerprints are reported as `missing_legacy` (not equivalent) and are
  rejected when `require_fingerprints=True`.

Full file: 20 tests pass.

## Scope Honored

- No external checkpoint load/resume path was added to vNext training — it still
  builds a fresh model. The validator is a standalone guard for future loaders.
- Old diagnostic checkpoints (without fingerprints) are not rewritten; they
  validate on schema name/dim and are flagged `missing_legacy` for fingerprints.

## Live Action-Ranker Loader — Risk Documented, Not Changed

`live_action_recommender.load_action_ranker_once` loads with
`load_state_dict(..., strict=False)` and **no `feature_version` assertion**, and
the recommender pads/truncates feature vectors to the checkpoint's declared
dims. This is weaker than the live value loader, which hard-fails on version
mismatch. Tightening it touches the live inference path and the intentional
`legal-action-v3` default, so it is **not changed here**.

Recommended (separate, approval-gated task): add a `feature_version` assertion to
the action-ranker loader for parity with the value loader, or expose a status
field and a strict opt-in mode rather than a hard behavior change.

## Gate

Training/live-promotion gate remains **CLOSED**.
