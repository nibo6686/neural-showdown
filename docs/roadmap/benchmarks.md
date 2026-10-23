# Baseline capability scoreboard

Engine: `b8f23c99629132611ba59e99480cb148ea8c5d3d`. Format: Gen 9 Random Battle. 500 seed pairs per matchup; every seed is played with agents on both teams.

| Agent A | Agent B | A wins / losses / ties | A win rate (Wilson 95% CI) | Mean turns | Games/s |
|---|---|---|---|---|---|
| greedy | random | 980 / 20 / 0 | 98.00% (96.93%–98.70%) | 24.59 | 3.21 |
| heuristic | random | 988 / 12 / 0 | 98.80% (97.91%–99.31%) | 22.93 | 3.32 |
| greedy | heuristic | 448 / 552 / 0 | 44.80% (41.74%–47.90%) | 17.87 | 3.61 |

Total wall time: 893.65 seconds. Illegal choices: 0; rejected choices: 0; errors: 0. Turn-limit flagged ties: 0.

Exact command (after building sim-core):

```powershell
node tools/bench/index.cjs --pairs=500 --output=tools/bench/results/2026-10-21-500.json --publish
```

Seed list: `tools/bench/seeds.json` (first 500 entries); SHA-256 `1b986bee16a4b3dcee42855c22bf8cbaed67f65dd003a1c3d86148034408291c`.

Machine results: [2026-10-21-500.json](../../tools/bench/results/2026-10-21-500.json). Deterministic records and wall-clock timings are separate arrays joined by game_id.

Random and heuristic adapt the existing baselines. Greedy maximizes accuracy-weighted mean calculator damage, never Terastallizes, and selects the first legal reserve only when required. Calculator guesses for unknown stats/items/abilities are explicit neutral scoring hypotheses, never added to observations. Public details without an L token mean level 100 in the pinned engine.

All agents exclude voluntary switches when the addressed raw request signals maybeTrapped; no opponent ability inspection. Engine rejection is never retried or erased.

Wilson 95% Bernoulli win probability; ties are non-wins. Paired games are dependent; interval is descriptive, not a paired-inference claim.

No model/search tuning. This measures playing strength independently of knowledge coverage. Legacy Python checkpoints need a subprocess/legacy-feature adapter and parity validation (estimate: 1–2 engineering days); deferred.

## Corpus

The git-ignored manifest `data/replays/corpus-2026-10-21/admission.jsonl` contains one outcome for each of **29,999 replays**, including **29,666 main-server battles**. **29,404 main-server battles are admitted (99.12%)**, each with exact reproduction, clean extraction and **zero public-state diffs**. No download or training was performed.

Main-server reproduction: **29,620 exact**, **44 divergent**, **2 rejected simulator inputs**. Server commits remain provenance. Custom-rule formats and Court Change are excluded from admission. Magician now has a finite, source-qualified public item-transfer implementation.

| Server commit | Replays | Admitted | Excluded |
|---|---:|---:|---:|
| `51ad80fa5b264a28416b0d78667519a97ba2d2ee` | 672 | 669 | 3 |
| `7332b60e22b9e8194bb53549549eba241d73cc9a` | 2,196 | 2,168 | 28 |
| `942cda71d14bf0618bd57991708a2e2734b6daba` | 10,738 | 10,667 | 71 |
| `b8f23c99629132611ba59e99480cb148ea8c5d3d` | 14,902 | 14,772 | 130 |
| `de1cf598c73dfedafff02be52375a62c94ed9ed0` | 1,158 | 1,128 | 30 |

| Main-server exclusion reason | Battles |
|---|---:|
| Custom rules outside the native format contract | 154 |
| Court Change (W6 quarantine) | 62 |
| Reproduction divergence | 44 |
| Simulator rejected input | 2 |

There are **333 other-server replays**: **325** rom/impulse/smogtours records are skipped by prefix; the remaining **8** are rejected (one forbidden input command and seven simulator input rejections). All excluded rows retain a reason and any diagnostic error. Four custom-rule replays are already counted under reproduction divergence, so the custom-rule input total is 158.

| Failure kind | Battles | Disposition |
|---|---:|---|
| Public reproduction diverged | 44 | Excluded; first differing record retained |
| Invalid Sableye move `secretsword` | 1 | Simulator input rejected |
| Move supplied where switch response required | 1 | Simulator input rejected |
| Hit count 11 outside the ordinary domain | 1 | Custom 24-team Shared Power; excluded |
| Unknown Doom Desire start/end lifecycle | 1 | Custom CAP format; excluded |

The custom-rule rows retain diagnostic extraction failures observed before the format exclusion was applied. No admitted row has a grammar failure or mismatch. The census performed **123,589,157** public comparisons; these cover the existing typed public contract. Raw-only lifecycles remain unprojected, and no broader native fidelity scope is promoted.

| Admitted rating metadata | Count/value |
|---|---:|
| Reported numerical rating | 25,284 |
| Missing rating (unknown) | 4,120 |
| Minimum / Q1 / median / Q3 / maximum | 1,000 / 1,294 / 1,626 / 2,043 / 2,481 |

**Runtime:** the measured 500-replay pilot took **141.71 s**. The full census elapsed **2,941.75 s**, including resource-limit restarts and 21 Magician rechecks; **3,083.46 s (51.39 min)** including the pilot. Worker stages used 6, 2 and 6 local threads. The benchmark ran concurrently for much of this period.

Fresh full-census command (after building sim-core):

```powershell
node tools/replay_repro/census.cjs data/replays/corpus-2026-10-21 --workers=6
```

Blocked benchmark runs remain as history: [animation](../../tools/bench/results/2026-10-21-500-blocked.json), [Bug Bite](../../tools/bench/results/2026-10-21-500-bug-bite-blocked.json), and [Magician](../../tools/bench/results/2026-10-21-500-magician-blocked.json).

### Source-qualified grammar

All citations below refer to pinned engine commit
`b8f23c99629132611ba59e99480cb148ea8c5d3d`, under
`engines/showdown-b8f23c99/`. Literal examples come from this corpus. TypeScript
and Python have positive cases and nearby malformed rejection controls.

| Family | Literal example | Emitter and bounded consequence |
|---|---|---|
| Pickpocket removal | `\|-enditem\|p2a: Sableye\|Leftovers\|[silent]\|[from] ability: Pickpocket\|[of] p2a: Sableye` | `data/abilities.ts:3254`: donor names itself; its item becomes removed. |
| Pickpocket receipt | `\|-item\|p2a: Weavile\|Assault Vest\|[from] ability: Pickpocket\|[of] p1a: Dewgong` | `data/abilities.ts:3255`: receiver holds the item; donor must be opposing active. |
| Bench cure | `\|-curestatus\|p2: Probopass\|par\|[msg]` | `sim/pokemon.ts:1676` and `:531`: side-only ident selects the named reserve, never the current active. Only source-emitted msg/silent tags. |
| Animation miss | `\|-anim\|p1a: Glimmora\|Meteor Beam\|p2a: Vikavolt\|[miss]` | `data/items.ts:4780`, `sim/battle-actions.ts:636` and `sim/battle.ts:3121`: exact optional miss tag; remains raw presentation. |
| Animation without target | `\|-anim\|p1a: Glimmora\|Meteor Beam\|p2: Basculin\|[notarget]` | `data/items.ts:4780`, `sim/battle-actions.ts:515`, `sim/pokemon.ts:531`: opposing side-only target with exact notarget tag. |
| Sleep source | `\|-status\|p1a: Scream Tail\|slp\|[from] move: Relic Song` | `data/conditions.ts:54`: finite sleep-source move domain derived from pinned move data; only sleep status. |
| Team preview | `\|teampreview\|8` | `sim/battle.ts:1400`, `sim/dex-formats.ts:359`: canonical integer team count bounded at 24, including replay custom rules. |
| Berry stolen and eaten | `\|-enditem\|p1a: Golem\|Custap Berry\|[from] stealeat\|[move] Bug Bite\|[of] p2a: Scyther` | `data/moves.ts:1923` / `:13451`: generated Bug Bite/Pluck labels, berry payloads and opposing active source; donor item removed. |
| Boost ability | `\|-ability\|p2a: Obliteryx\|Opportunist\|boost` | `sim/battle.ts:2073`, `data/abilities.ts:3077`: boost ability domain derives from standard Gen 9 callbacks that invoke boost. |
| Illusion replacement | `\|replace\|p2a: Zoroark\|Zoroark-Hisui, L80, F` | `data/abilities.ts:2082`: omitted health preserves already public status. An explicit condition without a status still clears it. |
| Court Change (excluded) | `\|-swapsideconditions` and `\|-activate\|p1a: Cinderace\|move: Court Change` | `data/moves.ts:3093`: W6 lifecycle retargeting remains quarantined. |
| Magician transfer | `\|-item\|p1a: Hoopa\|Choice Scarf\|[from] ability: Magician\|[of] p2a: Porygon-Z` | `data/abilities.ts:2492`: receiver gains the announced item; named opposing donor loses it and retains removal history. Active and fainted side-only donors are covered; replay-compat stays quarantined. |

The census also found `|-hitcount|p2: Terapagos|11` in replay
`gen9randombattle-2698336707`. Its input format is
`gen9randombattle@@@max team size = 24,camomons,shared power`.
`sim/battle-actions.ts:861` and `:975` emit the move's dynamic hit count; custom
team size can extend Beat Up beyond the ordinary Random Battle domain. Such
custom-rule replays are excluded as `custom-rules`; the ordinary hit-count
validator remains bounded at 10 in both languages.

Replay `gen9randombattle-2699893123` uses
`gen9randombattle@@@Same Type Clause,cap` and emits
`|-start|p1a: Equilibra|Doom Desire` and
`|-end|p2a: Jumbao|move: Doom Desire` (`data/moves.ts:3872`,
`data/conditions.ts:403`). It is also excluded as `custom-rules`. The native
unclassified-effect rejection remains covered in TypeScript and Python.
