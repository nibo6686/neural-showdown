# Architecture

The system is split across two runtimes:

- `sim-core` owns the authoritative local Pokemon Showdown battle simulation.
- `trainer` owns featurization, datasets, model code, and experiment orchestration.

Communication is newline-delimited JSON over stdio. The Python process is the parent and can:

- create and destroy battle environments
- reset an environment
- submit external choices
- ask `sim-core` for a baseline agent choice for a waiting side

The simulator never exposes hidden opponent information in `views.p1` or `views.p2`. Each player view is derived only from:

- that player's `|request|` payloads
- public battle log messages emitted on the player stream

The only state authority is the local Showdown simulator.

## Current refactor boundary

The versioned `ObservableBattleState`, `BeliefState`, `CanonicalAction`,
`SeededTransition`, and `dataset-record/v1` lineage contracts are accepted and
additive. Their current implementation status does not make the complete
feature/data/model pipeline ready: the checkpoint-free PIPELINE-001 path is
still an unaccepted candidate, FEATURE-001 has no accepted schema, and ENV-001
remains blocked. The pinned simulator coverage inventory documents state and
protocol projection gaps. See [PROJECT_STATUS.md](PROJECT_STATUS.md),
[`contracts/SIMULATOR_COVERAGE.md`](contracts/SIMULATOR_COVERAGE.md), and
[`contracts/PIPELINE_INTEGRATION.md`](contracts/PIPELINE_INTEGRATION.md).

The 2026-09-24 focused correction adds independent optional random-controller
seeds for reproducible test scenarios, source-backed move target/tag validation,
and pipeline stopping for unresolved protocol aliases. The change is not yet
covered by a separate semantic-digest review. PIPELINE-001 remains unaccepted;
PIPELINE-002 documents the future requirements for complete episode progression
through one-sided forced-switch, waiting, and requestless boundaries.

The lower diagram's `features(...) -> ModelInput` edge is a target architecture,
not an implemented or accepted interface. No new feature extraction, dataset
generation, or model training is authorized by this architecture description.

Research belief branches can fork the current battle through the pinned
Showdown `Battle.toJSON()` / `Battle.fromJSON()` state API. Before restoration,
the opponent's unrevealed set fields are replaced by deterministic Gen 9
randbats samples constrained only by the audited player's public view. This is
an opt-in research path; normal env reset and live recommender defaults are
unchanged.

The multi-particle research agent creates three independently seeded sanitized
forks, evaluates the same bounded root actions in each, and selects by mean
root score. Exact-seeded and single-particle modes remain separate and
unchanged.

## Validation boundary

The audited simulator dependencies are pinned in `sim-core/package.json`.
Changing Pokemon Showdown or `@smogon/calc` requires running:

```powershell
.\scripts\run_windows.ps1 -Action validate-sim-core -SimCoreMode native
```

Parity coverage is for seeded Gen 9 singles smoke tests. The 13-action codec
does not represent doubles or other multi-action formats. Exact public replay
reproduction is not supported because saved public logs omit seeds, complete
private teams, and private requests; only public-state reconstruction is
validated. Exact private-request stats are passed into damage calculation and
covered by regression tests.
