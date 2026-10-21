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

The command emits one JSON result per replay plus exact-match totals, excludes `impulse-*` and acquisition summaries, and fails on mismatches, invalid input, or a foreign engine version. Forfeit/inactivity results compare the prefix before the server-only ending message. No replay download is performed.

`--extract` reproduces each input in a fresh simulation-only environment and
feeds the full addressed streams to both owner extractors. It groups failures
by command, effect ID and message, and exits nonzero for any failure. Continued
scanning after rejection is diagnostic only: no partially accepted view or
dataset row is returned. Unrelated grammar failures remain visible.

`--diff` settles both owner streams and the public fan-out after each input command,
then compares both views at pending decision boundaries with read-only simulator
truth. It checks typed public side layers, field effects, Substitute, public
boost/status evidence, exact owned HP and rounded opposing HP. Raw-only volatile
lifecycles and internal rule pseudo-weather remain outside typed projection;
they are not treated as absent. Truth never enters the extractor. The summary
lists excluded unclean replays and mismatches by fact/effect ID. A mismatch or
zero completed comparisons exits nonzero. No additional replay download is needed.

For Node/Python full runs, create a temporary directory and set `NEURAL_TEST_OUTPUT_DIR`
for both runtimes. Run the Node target-fidelity LIVE producer before its Python
consumer; remove the directory in a `finally` block. Without this variable the
Python LIVE handoff test skips. `tools/test_fast.ps1` manages this automatically.
