# SeededTransition Contract

Status: TRANS-001 accepted (2026-09-23).

## Boundary

The simulator remains authoritative for mechanics and mutable battle state. A
transition consumes a complete pair of request-bound `CanonicalAction` values
at the simulator boundary and returns the existing `StepResult` plus explicit
transition metadata. `ObservableBattleState` is the caller-visible, sanitized
input used for request/action validation; it never contains the simulator's
serialized `Battle` object.

```text
ObservableBattleState[p1,p2] + CanonicalAction[p1,p2]
  + server-managed SeededSnapshotRef
    -> LocalBattleEnv / Showdown BattleStream
      -> StepResult + SeededTransitionMetadata + output snapshot
```

The boundary is additive and opt-in through `step_seeded_transition`. Existing
`step`, `step_canonical`, controllers, search, replay, live defaults, and
belief forks remain unchanged. Belief forks are not exact transition branches:
they intentionally rewrite hidden state and remain separate.

## Snapshot and identity

The simulator-only `SeededBattleSnapshot` v1 contains the format, four-word root
seed, canonical SHA-256 simulator-state fingerprint, parent branch ID, derived
branch ID, transition lineage, and `Battle.toJSON()` state. The RPC boundary
exposes only an opaque server-managed `SeededSnapshotRef`; raw serialized state
never crosses the ObservableBattleState, feature, or RPC response boundary.

Fingerprints recursively sort object keys and preserve array order. Runtime
wall-clock protocol records matching `|t:|<integer>` are normalized to
`|t:|<timestamp>` for identity; raw logs remain unchanged in emitted output.
Branch IDs and transition IDs are deterministic hashes of schema, parent
identity, state fingerprints, root seed, ordered action IDs, the server-derived
simulator revision, and step index. Snapshot lineage is checked against its
derived branch ID before execution.

## Validation and execution

The transition request must contain exactly p1 and p2 observations/actions,
both actionable current requests, a non-negative step index, and a
server-resolved snapshot whose fingerprint, lineage, and root seed match the
live simulator. Every action is validated against its observation and then
against the live request before any raw choice is forwarded. Mixed-validity,
stale, unavailable, wait/team-preview, forced-invalid, or request-inconsistent
joint actions fail atomically with no state or log advance.

After all preflights pass, the existing canonical-to-choice/raw stream path is
used. Metadata retains parent/child branch IDs, input/output fingerprints,
root seed, ordered action IDs, simulator revision, step index, and ordered
emitted `log_delta`. The output snapshot is simulator-only and is never
embedded in the observable response by default.

## Determinism and rollback

Identical serialized snapshots, root seeds, server-derived simulator revision, step index, and
complete joint actions must produce identical transition IDs, branch IDs,
output fingerprints, action IDs, and emitted log deltas under the installed
sim-core runtime. The golden case is
[`tests/fixtures/seeded_transition_v1.json`](../../tests/fixtures/seeded_transition_v1.json).

Rollback removes the transition module, fixture/tests, contract, and additive
RPC/method while retaining legacy `step`, `step_canonical`, snapshot restore,
and belief-fork behavior. No search redesign, model retraining, or ENV-001
change is part of this slice.
