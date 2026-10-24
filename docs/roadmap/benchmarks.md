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

## Replay-born authoritative pilot (W1.1)

The owner kept W1.1 scoped after the pilot exposed W3's non-direct switch
restriction. The switch-authority fix is the immediate next slice, before W1.2.
**The full admitted-corpus born/K gate is deferred until that fix; this is a
500-replay pilot, not a full-corpus result or a representative pass-rate estimate.**
The selection is the first 500 admitted IDs in the existing manifest order.

Final outcomes: **227/500 complete (45.4%)**, **273 fail**, **0 timeouts/skips**.
The git-ignored local manifest is
`data/replays/corpus-2026-10-21/born-pilot-W1.1.jsonl`, one final outcome per ID.
It retains exact failure reasons and switch-source diagnostics. The first pilot
ran 811.70 s; rechecking its 290 failures after exact hard-lock mapping and source
diagnostics took 250.58 s, **1,062.27 s total**, using six local workers. The
recheck admitted 17 additional battles; the remaining three former mapping cases
now reach the W3 guard. No canonical action validator or switch guard was relaxed.

| Final failure | Battles | Follow-up evidence |
|---|---:|---|
| Unbound switch source | 247 | W3; exact kinds below |
| Observation Pokémon schema rejection | 16 | All contain Slow Start; `belief_state.ts` does not accept the optional `ability_effects` key. Example `2695483532`; W5/public observation schema triage. |
| Public health/request evidence disagreement | 7 | W4/W3 boundary triage; example `gen9randombattle-2695527325`; exact subjects retained per row. |
| Public ability/request evidence disagreement | 3 | W5; example `2695485074`. |

These failures precede K publication. They are not fabricated K facts, and no
adopted registry row was demoted. The other 26 failures also need resolution
before claiming the full ≥99% gate; fixing pivots alone does not establish it.

| First blocked transition source | Battles |
|---|---:|
| U-turn | 120 |
| Flip Turn | 51 |
| Volt Switch | 50 |
| Parting Shot | 14 |
| Shed Tail | 6 |
| Chilly Reception | 4 |
| Teleport | 2 |

Counts describe observed failing transitions, not every switch appearing later
in each replay. Other W3 families (drags, items, abilities, Baton Pass) remain
unmeasured by this first-failure pilot. The authority checks remain unchanged;
`switch_sources` is diagnostic only.

The K oracle performed **2,496,912 known-fact comparisons**, **0 mismatches**, over
**8,833 validated boundaries** and **55,938 matched public records**. Counts include
validated prefixes of failed replays. All 25 adopted rows have known checks;
unknowns remain unknown. Three registry-unknown opponent applications have no
projected values. This establishes only the measured prefixes, not whole-corpus
correctness. The focused oracle controls reject wrong known facts, fabricated
unknown values and known values where the registry requires unknown.

| Registry row (family/property/context/own) | Known checks | Unknown observations | Mismatches |
|---|---:|---:|---:|
| `K01/roster_species/original/own` | 105,996 | 0 | 0 |
| `K04/level/original/own` | 105,996 | 0 | 0 |
| `K04/level/current/own` | 104,736 | 1,260 | 0 |
| `K04/gender/current/own` | 104,736 | 1,260 | 0 |
| `K04/shiny/original/own` | 105,996 | 0 | 0 |
| `K04/shiny/current/own` | 104,736 | 1,260 | 0 |
| `K04/ball/original/own` | 105,996 | 0 | 0 |
| `K04/ball/current/own` | 104,736 | 1,260 | 0 |
| `K04/details/current/own` | 104,736 | 1,260 | 0 |
| `K01/roster_order/original/own` | 105,996 | 0 | 0 |
| `K01/roster_size/original/own` | 17,666 | 0 | 0 |
| `K02/starting_moves/original/own` | 105,996 | 0 | 0 |
| `K03/submitted_nature/original/own` | 105,996 | 0 | 0 |
| `K03/submitted_happiness/original/own` | 105,996 | 0 | 0 |
| `K04/starting_tera/original/own` | 105,996 | 0 | 0 |
| `K03/calculated_stats/original/own` | 105,996 | 0 | 0 |
| `K03/calculated_stats/current/own` | 104,736 | 1,260 | 0 |
| `K03/hp_max/original/own` | 105,996 | 0 | 0 |
| `K03/hp_max/current/own` | 79,337 | 26,659 | 0 |
| `K05/hp/current/own` | 104,736 | 1,260 | 0 |
| `K05/fainted/current/own` | 104,736 | 1,260 | 0 |
| `K05/status/current/own` | 79,337 | 26,659 | 0 |
| `K18/item/original/own` | 105,996 | 0 | 0 |
| `K19/ability/original/own` | 105,996 | 0 | 0 |
| `K19/ability/current/own` | 104,736 | 1,260 | 0 |

Measured command (after building sim-core):

```powershell
node tools/replay_repro/index.cjs data/replays/corpus-2026-10-21 --born --kdiff --workers=6 --limit=500 --manifest=<temporary-pilot.jsonl>
```

The full run remains available through the same command without `--limit`;
set an outer timeout from a fresh pilot after the switch-authority fix. The
unchanged per-replay bound is 120 s; battles over 500 turns require
`NEURAL_LONG_TESTS=1`. No dataset writing, downloads or training occurred.

## Switch-source pilot and stopping dependency (W3.1)

W3.1 implements the brief's **Part A+C stopping point**, not the full born gate.
The final sample is the **first 200 admitted IDs in manifest order**, six workers,
`--born --kdiff`, 300,000 ms per replay. A larger 500-ID attempt was deliberately
stopped after a real drag established Part B's architectural stop condition;
only the fixed 200-ID sample is reported here. Rechecks use the final authority
path for every drag-containing replay, failed sample case, and W1.1 non-switch
case. Outcomes are in the git-ignored local
`data/replays/corpus-2026-10-21/born-pilot-W3.1.jsonl`; the manifest retains every
failure reason and source diagnostic. This sample is not a whole-corpus estimate.

| Measurement | Result |
|---|---:|
| Born complete | 184/200 (92.0%) |
| Remaining failures | 16 |
| Known K comparisons | 1,727,148 |
| K mismatches | 0 |
| Validated boundaries / matched public records | 6,145 / 38,594 |
| Timeouts / skips | 0 / 0 |

The delivered request ledger now admits a single-use canonical choice occurrence.
The native `Side.choose` action object survives through queue resolution into
`Battle.runAction`, then qualifies its exact `BattleActions.switchIn` writer.
Both owners pass all eight requested pivot families. Copied, foreign, replayed
and different-slot choices fail. No binding comes from public actor names,
species, slot values, or matching log text. Shed Tail/Baton Pass identity binding
does not extend their existing transfer semantics.

**Part B dependency.** Native `BattleActions.dragIn` selects a replacement via
`Battle.getRandomSwitchable` and calls `switchIn(..., null, true)` without an
owner choice. Qualifying that occurrence needs a new authenticated drag/action
hook, widening the existing B2 authority boundary. The brief requires stopping
there. Unqualified `drag` records now fail closed alongside `switch` records;
they previously escaped the switch-only guard. Owner-chosen item/ability
replacements use the same choice mechanism but were not separately corpus-gated.

All 15 drag failures have reason `switch-events/v1/unbound-switch-source` and
source `drag:unknown` (source labels are diagnostic only):
`2695483832`, `2695485629`, `2695485887`, `2695488683`, `2695494729`,
`2695500918`, `2695502167`, `2695506896`, `2695509429`, `2695514412`,
`2695515096`, `2695515250`, `2695515356`, `2695529769`, `2695531409`.
All IDs have prefix `gen9randombattle-`. Replay `2695509927` instead fails
`pipeline/v1/observable-projection-failed: Public health evidence mismatch: Revival bench outcome requires one inactive owner request with exact half HP and cleared status/faint`.
That newly reached W4 failure is not one of W1.1's seven percentage disagreements.

**Part C.** Both readers retain Slow Start presence and its immediate, same-actor
silent cleanup after faint; TS admits the optional `ability_effects` field
(Python already admitted it). The producer retains publicly cleared bench effects.
HP checks now follow the native operation order, `ceil(100 * HP / maxHP)`;
`168/300` publicly emits `56/100`, not the floating-point artifact `57/100`.
As One's exact adjacent component announcements preserve only an addressed owner
variant; later Grim/Chilling Neigh boost announcements must agree with that
variant. Public labels alone never identify a variant from species. Of the
original 26 non-switch failures, 23 complete, including all seven health and
all three ability cases; three Slow Start cases reach the drag dependency
(`2695488683`, `2695494729`, `2695550558`).

**Remaining gate.** The full 29,404 replay run is deferred until drag authority
is reviewed and implemented. The unchanged episode tests now reach native outcomes:
`real episode completes repeatably...` expects 55 transitions but gets 44;
`v2 evidence retains both owners...` and `resumed terminal closure...` expect a
positive faithful claim that the native11 profile still forbids, even with
`complete_capture: true`. The native winner is also p2 rather than the fixture's
p1. These assertions were not rewritten. Additional focused results and the fast gate are recorded in
the W3.1 report. No >=99% acceptance claim is made.

## Drag authority and born gate (W3.2)

The approved native `BattleActions.dragIn` wrapper opens a synchronous frame for
this battle's side and position. Only its one associated native incoming object
may produce a drag writer. Nested/foreign frames, overrides, absent or duplicate
entries, wrong side/position and unassociated actors reject; failed drags bind
nothing. No actor is chosen from public values. Red Card's exact native
`-enditem ... [of] opposing-active` form and payload were added to the finite
native contract in both readers. Scanning all admitted logs found no Eject Button,
Eject Pack, Emergency Exit or Wimp Out announcements, so their optional fixture
requirement did not activate; owner-request authority remains W3.1's mechanism.

Revival replay `2695509927` completes with **0 K mismatches / 75 boundaries**.
Its revived bench was valid at terminal but there was no current request.
The corrected validator uses only the authenticated terminal predecessor,
requires exact retained half HP, and rejects absent/foreign authority or a
changed exact value even when the public percentage is unchanged.

Episode expectation changes (validators remain unchanged):

- Direct completion: 55 transitions → 44, from pinned b8f23c99 behavior.
- v2 terminal winner: p1 → p2; wrong-winner mutation: p2 → p1.
- Completed native faithful claims (v2, resumed closure and shared assertion):
  true/complete-capture-derived → false; complete_capture remains true.
- v1 envelope control: historical10 → native11 reader, because an envelope
  schema version does not change its engine's provenance.
- Gap/reorder controls: fixed early indices → a joint-boundary run, preserving
  their lineage rejection checks after native11's early selection boundary.

Pilot: **20/20 complete**, **0 K mismatches / 173,906 checks**, 621 boundaries,
3,915 matched records, no skips/timeouts; **59.21 s with six workers**. The full
29,404-battle gate is pending. The pilot rate suggests roughly 24 hours, not an
acceptance estimate. Runtime logs and final outcomes remain under
`data/replays/corpus-2026-10-21/`.

After committing W3.2, resume from the isolated worktree at BelowNormal priority:

```powershell
Set-Location C:/dev/neural-born-W3.2
node tools/replay_repro/index.cjs C:/Users/cloud/Downloads/neural/final/data/replays/corpus-2026-10-21 --born --kdiff --workers=5 --worker-memory-mb=1024 --replay-timeout-ms=300000 --update-admission --resume --admitted=C:/Users/cloud/Downloads/neural/final/data/replays/corpus-2026-10-21/admission.jsonl --manifest=C:/Users/cloud/Downloads/neural/final/data/replays/corpus-2026-10-21/born-W3.2.jsonl
```

The journal records every per-battle failure reason and K result. `admission.jsonl`
receives `born_session` checkpoints every 250 outcomes and on orderly exit:
`complete` is the actual born result, `kdiff_mismatches` is a count or null when
unmeasured, and failure/skip reasons are retained. Unprocessed entries are not
assigned false completion or zero mismatches. Track B may select entries with
`born_session.complete === true` and `born_session.kdiff_mismatches === 0`.
`--resume` reuses completed journal rows, validates membership/uniqueness and K
availability for passed cases, and processes remaining entries; use it only with
the same built code and corpus. It does not waive any replay or K validation.
The full run has a 72-hour outer limit, five-minute per-replay limits and a
1 GiB old-generation heap cap per worker. Failures remain visible in the gate.

**Full result:** pending; results will go in a follow-up commit. The existing
journal is resumed, never silently restarted, from `C:/dev/neural-born-W3.2` at
the W3.2 code commit. Five workers run at BelowNormal priority. Do not modify or
rebuild that worktree while active. Development and builds may continue in the
main tree. Operational state/progress/summary remain `born-W3.2.run.json`,
`born-W3.2.progress.log`, and `born-W3.2.summary.json` in the main corpus directory.
No >=99% or full-corpus zero-mismatch claim yet.
