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
