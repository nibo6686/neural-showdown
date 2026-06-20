# legal-action-v7 Materializer Wiring Report

## Result

The full-manifest materializer now accepts `--action-feature-version
legal-action-v7` without changing the v7 schema or running materialization.

- Action schema: `legal-action-v7`, 552D.
- Ordered-name fingerprint:
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`.
- v7 uses the same repeat-chain impact enablement as v6; v5 remains disabled.
- Metadata and assembled-array validation resolve through the existing
  `action_feature_schema` guardrails.
- Unknown CLI action versions remain rejected by `argparse`.

## Tests

Focused tests cover:

- mocked full-manifest CLI dispatch accepting v7 without running a job;
- exact v7 version/dimension/fingerprint metadata;
- in-memory 552D assembled-array validation;
- v6/v7 shared repeat-chain enablement;
- byte-identical v6 Rollout repeat-chain prefix inside v7; and
- continued rejection of an unknown action version.

No repository dataset directory was created. No dataset was materialized,
trained, promoted, or connected to live defaults.
