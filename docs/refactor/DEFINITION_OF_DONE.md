# Definition Of Done

A refactor work item is complete only when:

- its contract and provenance fields are documented;
- acceptance tests and golden fixtures exist;
- raw protocol lineage is retained;
- no future event can enter an earlier observation;
- public, acting-player-private, belief, and simulator-only fields are separated;
- action identity and slot numbering round-trip across runtimes;
- seeded transitions reproduce identical results;
- model and dataset schema fingerprints are validated fail-closed;
- battle/replay lineage survives dataset expansion and splitting;
- rollback is documented and exercised where runtime behavior changes;
- required validation commands and environment prerequisites are recorded;
- no unrelated source or documentation changes are present in the diff.

## Pipeline and model readiness gates

Acceptance of a lower-level contract does not imply that the end-to-end data or
model pipeline is ready. Before generating a new refactored dataset, require:

- SIM-COVERAGE state and protocol gaps have explicit dispositions and drift
  checks fail closed;
- PIPELINE-001 has a separate, scoped acceptance review, including a natural
  post-preflight simulator rejection test and exact state/lineage preservation.
  The natural case must arise from a real supported-format simulator rule;
  injected failures remain separately labeled and do not substitute for it;
- complete-episode collection has an explicit progression contract for
  one-sided forced switches, waiting, and requestless states. No action is
  synthesized for a side without a current legal request. Every partial
  episode is either completed or retained with an explicit stop/truncation
  reason, boundary kind, and last committed cursor; it is not silently dropped
  or labeled terminal;
- FEATURE-001 defines one versioned contract shared by collection and inference,
  with privacy, temporal cutoff, masks, knownness, fingerprints, and migration
  behavior;
- target, reward, horizon, discount, terminal/tie/truncation, and behavior/target
  policy choices are explicit;
- data validation covers duplicate identity, broken lineage, invalid actions,
  impossible transitions, grouped splits, temporal leakage, distribution, and
  privacy;
- ENV-001 reproducibility blockers are resolved or explicitly accepted by a
  reviewer for a narrowly scoped first experiment. Missing optional replay
  fixtures do not block the first simulator-only milestone, but replay-specific
  claims still require them;
- training configuration and runtime input/output manifests agree exactly.

Checkpoint availability is not part of readiness for the new model; existing
checkpoints are abandoned for this approach and non-blocking. Readiness never
follows from document existence or a green unit suite alone. See
[`../PROJECT_STATUS.md`](../PROJECT_STATUS.md).
