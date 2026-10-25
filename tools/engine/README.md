Build the simulator package on Windows (PowerShell 7, Node 24 and npm 11):

```powershell
./tools/engine/build_engine.ps1 -Commit b8f23c99629132611ba59e99480cb148ea8c5d3d
```

`-Checkout <path>` reuses a clean checkout at the exact commit, clearing its generated `dist` first. Otherwise the builder shallow-fetches that commit into a temporary directory. Each subprocess has a ten-minute timeout. It installs the upstream lock with scripts disabled, builds runtime JavaScript and declarations, and packs the simulator, data, library, formats and license into `vendor/` (`-OutputDirectory` overrides that destination). Server/client code and source maps are excluded. Raw gen9 sets support Trace checks; `moves.ts`, `items.ts` and `pokedex.ts` are runtime inputs to Python featurizers. Finite source-exclusion tests also require `data/abilities.ts`, `sim/pokemon.ts` and `data/random-battles/gen9/teams.ts`. The only runtime npm dependency is the upstream locked `ts-chacha20` version.

After changing the file dependency, run `npm install --ignore-scripts` and `npm ci --ignore-scripts` in `sim-core`, then `node tools/engine/generate_assets.cjs` at the repository root. The generator retains the reviewed finite protocol template/quarantines, derives the Trace ability domain from the installed engine, and writes commit-named lookup/protocol JSON. Update the code-owned SHA-256/SRI pins and native profile identities when re-pinning. Historical protocol and inactive inventory assets remain historical evidence, not newly validated semantic coverage.

`engine-files.json` inside the package hashes the exact installed file set. TypeScript and Python verify it, the lock entries, commit metadata and vendored tarball integrity; the common npm version string is insufficient.

`node tools/engine/generate_assets.cjs --check` recomputes both assets and requires identical bytes without rewriting them.

Generate the effect inventory from the full source checkout, using an unpacked
`pokemon-showdown@0.11.10` npm package as the historical comparison:

```powershell
./tools/engine/generate_effect_inventory.ps1 -Source engines/showdown-b8f23c99 -HistoricalSource <unpacked-package>
./tools/engine/generate_effect_inventory.ps1 -Source engines/showdown-b8f23c99 -HistoricalSource <unpacked-package> -Check
```

The generator checks the clean Git commit and historical source-tree hashes.
It compares declaring callbacks, emitters and shared lifecycle methods and records
exact source differences in the inventory. `effect_class_reviews.json` names
reviewed classes and exact before/after hashes; uncovered changes stay fail-closed.
New binding/ability/preparation hints retain raw evidence without private counters.
Repeat this step when re-pinning, then update both readers' inventory SHA-256 pins.
Restoring a command's historical grammar does not adopt a changed effect.

After the TypeScript build, reproduce the local probe with:

```powershell
node tools/replay_repro/index.cjs data/replays/probe-2026-10-16
node tools/replay_repro/index.cjs --extract data/replays/probe-2026-10-16
node tools/replay_repro/index.cjs --diff data/replays/probe-2026-10-16
```

Admission requires exact public reproduction on the pinned engine. The replay's
single server `>version` is retained as provenance and may differ from the local
commit. Only the input-command allowlist is accepted; `>eval` stays forbidden.
Forfeit/inactivity results compare the prefix before the server-only ending.
No replay download is performed.

Each replay gets an outcome, including divergence, invalid input, extraction
failures and public-state diffs; a rejected replay never aborts the batch.
`rom-*`, `impulse-*` and `smogtours-*` are skipped with a side-server reason.
Custom rules or a different format fall outside the native Gen 9 Random Battle
contract. Court Change remains an explicit W6 exclusion. Native Magician transfers retain
both receiver possession and named donor removal history. Other extraction failures retain their exact records and messages.
Acquisition summaries are not replay records.

`--extract` feeds both addressed streams to fresh simulation-only extractors.
After any rejected record, continued scanning is diagnostic only; that replay
cannot return an admitted view or dataset row. `--diff` settles both owner
streams and public fan-out at each input boundary and compares typed public
facts with a read-only simulator oracle. Raw-only lifecycles remain unprojected,
never assumed absent. Truth never enters the extractor.

For a measured pilot and the full local census:

```powershell
node tools/replay_repro/index.cjs data/replays/corpus-2026-10-21 --diff --limit=500 --manifest=<temporary-pilot.jsonl>
node tools/replay_repro/census.cjs data/replays/corpus-2026-10-21 --workers=2
```

`--files=<path>` can select a JSON array of replay filenames for bounded batches.
The census defaults to two local worker threads, writes `admission.jsonl` in the input
directory and emits a summary with commit counts, exclusions, failure kinds,
rating quartiles, public comparison counts and total wall time. Each row
retains metadata, reproduction/extraction outcomes and a diff mismatch count
(null when no comparison ran). Normal exclusions do not make the command fail;
a fatal batch/worker error does. Check admission rate, every exclusion reason,
and zero diffs on admitted rows before using the corpus.

The baseline CLI writes only machine JSON by default. Updating the committed
scoreboard requires `node tools/bench/index.cjs --pairs=500 --publish`; an
alternate `--output=...` alone never publishes. Publishing preserves the
scoreboard's Corpus section.

For Node/Python full runs, create a temporary directory and set `NEURAL_TEST_OUTPUT_DIR`
for both runtimes. Run the Node target-fidelity LIVE producer before its Python
consumer; remove the directory in a `finally` block. Without this variable the
Python LIVE handoff test skips. `tools/test_fast.ps1` manages this automatically.

Find a generated witness on the pinned engine with
`node tools/engine/find_witness_seed.cjs --species=Jirachi --move=wish --max=5000`.
Optional `--ability`, `--item`, one-based `--slot`, `--start` and `--tail=a,b,c`
bound the predicate/search. The exported `findWitnessSeed(predicate, options)`
also accepts team predicates (and receives the seed as its second argument).
Native inventory regeneration includes the current local source digest, including
`OBSERVABLE_STATE.md`; its historical semantic-review digest remains separate.

## Authoritative replay sessions and the K differential

`tools/replay_repro/replay_session.cjs` exports `replaySession(replay, options)`.
It creates a real `PipelineIntegrationSession` from the native battle seed and
both player team seeds. The pinned engine generates and enrolls the teams;
creation uses neither a generation override nor an imported snapshot. Ordinary
pipeline transitions retain their existing held-candidate restore mechanism.
Native `sodium,<32 hex>` and `gen5,<16 hex>` seeds preserve their algorithm in
snapshot lineage; legacy four-number seeds keep their existing representation.
`player_generation` is an explicit pipeline creation option with each player's
name and generator seed. These inputs grant no identity or knowledge authority.

Each returned boundary has two addressed frames, each containing only that
owner's observation, K projection and chosen canonical action (null for waiting,
terminal or server-ended boundaries). `collect:false` avoids retaining frames;
`onBoundary(frames)` supports a local streaming consumer. A move ID from an input
log must resolve to exactly one current canonical action. A hard lock may resolve
to the sole canonical default only when its sole emitted move ID agrees.

The public oracle uses the reproduction tool's framing filter and exact native
split alternatives. If an uploaded replay selected secret HP rather than shared
HP, both records must be the alternatives of that same emitted split. Forfeits
and inactivity stop at the prefix before the server-only message; no artificial
terminal action is submitted. A divergent log fails the replay. Frames observed
through the callback are tentative until the final oracle check succeeds and
must not be published as an admitted episode before that result.

```powershell
node tools/replay_repro/index.cjs data/replays/corpus-2026-10-21 --born --kdiff --workers=6 --limit=500 --manifest=<temporary-pilot.jsonl>
node tools/replay_repro/census.cjs data/replays/corpus-2026-10-21 --born --kdiff --workers=6
```

The born census reads only admitted rows from `admission.jsonl` (`--admitted`
overrides this input); its separate default output is `born-admission.jsonl`.
`--files` selects filenames from that admitted set. Workers continue after replay
failures, retain exact reasons, and close when finished. `--replay-timeout-ms`
(default 120000) bounds each worker task. Replays over 500 turns are explicitly
skipped unless `NEURAL_LONG_TESTS=1`. Size an outer run deadline from the pilot.

`--kdiff` compares all adopted registry rows with read-only native truth at each
validated boundary. Original values use the enrolled original submission and
native stat calculation; current values use the owner-bound live roster and
native request-declared semantics (`baseStoredStats`, details, current ability,
HP, status and fainting). Unknowns are counted without asserting a value.
Known values where the registry requires unknown are mismatches. Truth stays
outside frames and action selection. Per-row checks, unknowns, mismatches and
bounded diagnostic examples include validated prefixes of failed replays; they
are not a claim that those episodes completed. No datasets are written.

W1.1 preserves the W3 non-direct switch authority guard. Its failures include
source diagnostics such as `effect-switch:uturn`; source-kind battle counts are
nonexclusive when one failed transition contains multiple kinds. The full born/K
corpus gate resumes after the owner-requested switch-authority follow-up, before
W1.2. The 500-replay pilot and remaining blockers are recorded in the scoreboard.

## Durable corpus jobs (R1)

Use the supervisor for long born/K runs. Commit the code and build an isolated
worktree first; do not edit, install, build or check it out while the job runs.
All corpus paths must point at the main tree's data directory, since ignored
replays are not copied into a worktree. Include `--owner-moves` for W1.2's new
move/PP differential rows.

```powershell
node tools/replay_repro/supervise.cjs C:/Users/cloud/Downloads/neural/final/data/replays/corpus-2026-10-21 --born --kdiff --owner-moves --workers=5 --worker-memory-mb=1024 --replay-timeout-ms=300000 --update-admission --admitted=C:/Users/cloud/Downloads/neural/final/data/replays/corpus-2026-10-21/admission.jsonl --manifest=C:/Users/cloud/Downloads/neural/final/data/replays/corpus-2026-10-21/born-R1.jsonl
```

The supervisor and child use BelowNormal priority. Unexpected census exits
restart with ID-based resume and exponential backoff (1 s to 60 s), at most 20
automatic restarts. A live `.supervisor.lock` prevents a second writer. An
operator relaunch must add `--resume`; changing the commit, corpus manifest or
selection/configuration is rejected without replacing the original status.
The manifest identity includes every input row/field except `born_session`,
which is the derived checkpoint this run updates. Worktree location is not code
identity. Ordinary extraction census jobs can also be supervised; supply
`--corpus-manifest=<immutable-input-manifest>` and retain their `.part-N` journals
for resume. Status/summary JSON never changes replay shard assignment.

Journal lines are written by one persistent shared handle and fsynced before
commit/checkpoint/dispatch. Resume truncates only an incomplete last line; a
malformed complete line or duplicate/foreign born outcome rejects. Journal,
checkpoint and atomic status/summary writes retry EBUSY/EPERM/EACCES with capped
backoff, remaining paused and retrying beyond 60 seconds. `blocked-write` in the
status identifies the resource. Other worker completions queue without starting
more work. A genuine per-replay deadline must expire on two attempts before a
`replay-time-limit` outcome becomes final. A heartbeat gap or wall/monotonic jump
interrupts in-flight work and reruns it without recording a failure. Infrastructure
worker errors restart the census rather than becoming replay failures.

The Windows helper holds `ES_CONTINUOUS | ES_SYSTEM_REQUIRED` while the supervisor
lives, then releases it on exit. Its PID is recorded in status and it follows the
original process object so PID reuse cannot keep it alive. No power settings,
registry entries or power plans change. The display may turn off; closing the lid
or choosing manual Sleep still suspends the machine. On wake, interrupted work
resumes through the supervisor/worker interruption logic.

**Readers/watchdogs:** prefer `born-R1.run.json`, updated at least every 15 seconds
with PID, child/helper PIDs, heartbeat, status, restart count, committed outcome
counts and K counts. `complete` means the scan finished, not that every replay
passed; inspect its summary/failure totals. Admission `born_session` rows may
still describe an older run until this run has processed those IDs. Never infer
current progress from those rows. Inspecting status through Node uses libuv's
read/write/delete sharing:

```powershell
node -e "console.log(require('node:fs').readFileSync(process.argv[1],'utf8'))" C:/Users/cloud/Downloads/neural/final/data/replays/corpus-2026-10-21/born-R1.run.json
```

If a watchdog must read the active journal or status through .NET, explicitly
open `FileAccess.Read` with `FileShare.ReadWrite -bor FileShare.Delete`, dispose
promptly, and accept a partial final journal line while the writer is active.
Do not use ordinary `Get-Content`, exclusive handles, editors that lock the file,
or a whole-journal poll. A blocked status-file replacement itself retries until
the reader releases it. A successful job saves `born-R1.summary.json`; retain
`born-W3.2.jsonl` as history from different code. Gate results belong in a later
results-only commit, not an amendment to the implementation.
