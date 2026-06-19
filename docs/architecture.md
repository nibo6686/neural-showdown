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
