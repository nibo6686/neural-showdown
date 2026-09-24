# System Map

## Current boundary

```text
Showdown BattleStream / Battle.toJSON
        │
        ▼
sim-core authoritative state
        ├── player BattleView / ChoiceRequestView
        ├── spectator log delta
        └── NDJSON RPC
                │
                ▼
trainer Python
        ├── replay parser / raw protocol trajectory
        ├── live private request reconstruction
        ├── tactical state and beliefs
        ├── feature builders
        └── models / rollouts / search
```

## Target boundary

```text
AuthoritativeSimulatorState
  ├─ observe(state, perspective) -> ObservableBattleState
  ├─ legal_actions(observation) -> CanonicalActionSet
  └─ transition(ObservableBattleState, CanonicalAction[p1,p2], SeededSnapshotRef)
       -> StepResult + SeededTransitionMetadata

ObservableBattleState + raw event prefix
  └─ update_belief(...) -> BeliefState

Observation + BeliefState + CanonicalAction
  └─ features(...) -> ModelInput -> Model/Search
```

Existing adjacent documentation: [docs/architecture.md](../architecture.md) and [docs/state-schema.md](../state-schema.md). This map does not supersede them until implementation work is approved.

## Current status

The accepted lower-level contracts are implemented as additive boundaries.
The diagram above showing `features(...) -> ModelInput` is still a target
design only: PIPELINE-001 remains unaccepted, FEATURE-001 is unresolved, and
the runtime does not consume these interfaces for new-model inference. The
current simulator state/protocol inventory is
[`../contracts/SIMULATOR_COVERAGE.md`](../contracts/SIMULATOR_COVERAGE.md).
Current readiness gates are summarized in [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md).
