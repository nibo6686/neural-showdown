# State Schema

Each `StepResult` contains:

- `views`: `{p1, p2}` player-legal `BattleView`s
- `requests`: normalized `ChoiceRequestView`s or `null`
- `rewards`: sparse terminal rewards
- `terminated`: whether the battle ended
- `winner`: `p1`, `p2`, `tie`, or `null`
- `log_delta`: public spectator log lines since the previous snapshot

`STATE-001` adds a separate shadow-only `ObservableBattleState` projection in
`sim-core/src/observable_state.ts`. It does not change this existing extraction
schema or any consumer. The normative versioned contract, visibility rules,
prefix cursor/hash semantics, request boundaries, and source mapping are in
[`docs/contracts/OBSERVABLE_STATE.md`](contracts/OBSERVABLE_STATE.md).

`BELIEF-001` defines a separate, perspective-owned `BeliefState` in
`sim-core/src/belief_state.ts`. It stores candidates, evidence provenance,
uncertainty, and optional transition lineage; it is never serialized as part of
`ObservableBattleState`. Its normative schema and fail-closed lineage rules are
in [`docs/contracts/BELIEF_STATE.md`](contracts/BELIEF_STATE.md).

In particular, `log_delta` is a delta and is not itself an event cursor. An
observable-state caller must provide the canonical protocol prefix through the
observation boundary so that cursor units count normalized protocol records and
the prefix hash can audit future-information boundaries. Raw `|request|` JSON is
validated as private input evidence and replaced in the observable prefix by a
canonical request-ID-only record; private team data and moves are never retained
or hashed there.

`BattleView` includes:

- format, gen, turn, player ids, names
- active self and opponent slot indices
- field weather / terrain / pseudo-weather
- side conditions for self and opponent
- self team array with exact information from the latest request
- opponent team array containing only publicly revealed information

`ChoiceRequestView` includes:

- `wait`, `teamPreview`, `forceSwitch`, `trapped`, `rqid`
- the active move list when available
- side team snapshot from the latest request
- `legal_actions` with fixed-size action mask and concrete Showdown choices
