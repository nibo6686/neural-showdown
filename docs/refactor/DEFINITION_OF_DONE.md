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

