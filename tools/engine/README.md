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
