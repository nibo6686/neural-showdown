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
  └─ transition(state, joint_action, rng) -> TransitionResult

ObservableBattleState + raw event prefix
  └─ update_belief(...) -> BeliefState

Observation + BeliefState + CanonicalAction
  └─ features(...) -> ModelInput -> Model/Search
```

Existing adjacent documentation: [docs/architecture.md](../architecture.md) and [docs/state-schema.md](../state-schema.md). This map does not supersede them until implementation work is approved.

