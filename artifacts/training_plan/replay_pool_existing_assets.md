# Existing Replay Pool Assets

- Replay pool: `data/replays/raw/gen9randombattle`
- Assets observed before profiling: 15,001 protocol `.log` files, 15,001 replay
  `.json` files, and `metadata.jsonl`.
- Downloader: `trainer/src/neural/replay_fetch.py`
- Protocol parser: `trainer/src/neural/parse_replay_logs.py`
- Existing public dataset builders:
  `build_replay_value_dataset.py` and `build_replay_policy_dataset.py`
- Existing live-private/action builders consume parsed replay trajectories but
  are intentionally not used by the lightweight profiler.

## Available fields

The `.log` files contain the public protocol log, including format/tier,
players, winner, turn commands, public battle events, and therefore mechanic
evidence and turn counts. Replay JSON files contain an embedded public `log`,
an `inputlog` with submitted move/switch commands when available, upload time,
format ID, player names, and sometimes rating. `metadata.jsonl` records replay
ID, source URLs, file paths, format, upload time, player names, rating, download
time, and asset availability.

Rating is generally a replay-level search/API value rather than a reliable
per-player Elo pair. The profiler preserves any positive per-player ratings
found in `inputlog`, but treats absent/zero values as unavailable.

The established convention is one `<replay_id>.log` plus one
`<replay_id>.json` under the format directory, with one JSON object per line in
`metadata.jsonl`. Processed trajectories are normally written as compressed
JSONL under `data/replays/processed`; the profiler instead writes a compact
battle catalog under `artifacts/training_plan` and does not generate features.
