# Baseline capability scoreboard

**Provisional, reduced-prefix baseline.** The requested 500-pair run failed at
`greedy-random-162-p2`, seed `[27929,33919,24444,49760]`, turn 21:
`LocalBattleEnv` rejected an engine-produced animation with
`Malformed raw -anim record: unsupported animation grammar`. The failed
attempt is retained in [2026-10-21-500-blocked.json](../../tools/bench/results/2026-10-21-500-blocked.json).
The table uses the first 100 committed seeds, chosen after that infrastructure
failure, and is not validation of the 500-pair target. No seeds within this
prefix were removed. Native grammar repair is a separate follow-up; no validator
was weakened. Re-run all 500 pairs after that repair.

Engine: `b8f23c99629132611ba59e99480cb148ea8c5d3d`. Format: Gen 9 Random Battle. 100 seed pairs per matchup; every seed is played with agents on both teams.

| Agent A | Agent B | A wins / losses / ties | A win rate (Wilson 95% CI) | Mean turns | Games/s |
|---|---|---|---|---|---|
| greedy | random | 199 / 1 / 0 | 99.50% (97.22%–99.91%) | 25.02 | 3.47 |
| heuristic | random | 198 / 2 / 0 | 99.00% (96.43%–99.73%) | 22.81 | 3.66 |
| greedy | heuristic | 87 / 113 / 0 | 43.50% (36.82%–50.43%) | 18.23 | 3.24 |

Total wall time: 174.63 seconds. Illegal choices: 0; rejected choices: 0; errors: 0. Turn-limit flagged ties: 0.

Exact command (after building sim-core):

```powershell
node sim-core/node_modules/typescript/bin/tsc -p sim-core/tsconfig.json
node tools/bench/index.cjs --pairs=100 --output=tools/bench/results/2026-10-21.json
```

Seed list: `tools/bench/seeds.json` (first 100 entries); SHA-256 `1b986bee16a4b3dcee42855c22bf8cbaed67f65dd003a1c3d86148034408291c`.

Machine results: [2026-10-21.json](../../tools/bench/results/2026-10-21.json). Deterministic records and wall-clock timings are separate arrays joined by game_id.

Random and heuristic adapt the existing baselines. Greedy maximizes accuracy-weighted mean calculator damage, never Terastallizes, and selects the first legal reserve only when required. Calculator guesses for unknown stats/items/abilities are explicit neutral scoring hypotheses, never added to observations. Public details without an L token mean level 100 in the pinned engine.

All agents exclude voluntary switches when the addressed raw request signals maybeTrapped; no opponent ability inspection. Engine rejection is never retried or erased.

Wilson 95% Bernoulli win probability; ties are non-wins. Paired games are dependent; interval is descriptive, not a paired-inference claim.

No model/search tuning. This measures playing strength independently of knowledge coverage. Legacy Python checkpoints need a subprocess/legacy-feature adapter and parity validation (estimate: 1–2 engineering days); deferred.
