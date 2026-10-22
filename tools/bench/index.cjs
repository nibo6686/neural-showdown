const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {performance} = require('node:perf_hooks');
const {runMatchup, summarize, BenchRunError} = require('../../sim-core/dist/src/bench/runner');
const {NATIVE_ENGINE_COMMIT: ENGINE_COMMIT} = require('../../sim-core/dist/src/version_profile');
const root = path.resolve(__dirname, '../..');
const args = Object.fromEntries(process.argv.slice(2).map(arg => {
  const match = /^--(pairs|output|matchup)=(.+)$/.exec(arg);
  if (!match) throw new Error(`Unknown argument: ${arg}`);
  return [match[1], match[2]];
}));
const seedBytes = fs.readFileSync(path.join(__dirname, 'seeds.json'));
const allSeeds = JSON.parse(seedBytes).seeds;
if (!Array.isArray(allSeeds) || allSeeds.some(s => !Array.isArray(s) || s.length !== 4 || s.some(n => !Number.isInteger(n) || n < 0 || n > 65535)) || new Set(allSeeds.map(s => JSON.stringify(s))).size !== allSeeds.length) throw new Error('Invalid or duplicate committed seeds');
const pairs = Number(args.pairs ?? 500);
if (!Number.isInteger(pairs) || pairs < 1 || pairs > allSeeds.length) throw new Error('Invalid pair count');
const matchups = args.matchup ? [args.matchup.split('-')] : [['greedy', 'random'], ['heuristic', 'random'], ['greedy', 'heuristic']];
for (const [a, b, extra] of matchups) if (extra || !['random', 'greedy', 'heuristic'].includes(a) || !['random', 'greedy', 'heuristic'].includes(b) || a === b) throw new Error('Invalid matchup');
const output = path.resolve(root, args.output ?? `tools/bench/results/${new Intl.DateTimeFormat('en-CA', {timeZone: 'America/Chicago'}).format(new Date())}.json`);
const result = {schema_version: 'baseline-benchmark/v1', engine_commit: ENGINE_COMMIT,
  seed_list_sha256: createHash('sha256').update(seedBytes).digest('hex'), pairs_per_matchup: pairs,
  command: `node tools/bench/index.cjs ${process.argv.slice(2).join(' ')}`.trim(),
  assumptions: {heuristic: 'Unmodified existing heuristic with public species/set priors; no benchmark tuning.', greedy: 'Neutral unknown ability/item; calculator neutral nature, zero EVs and 31 IVs for unobserved stats. These are scoring hypotheses, not revealed facts. Accuracy-weighted mean damage; first legal action breaks ties.',
    intervals: 'Wilson 95% Bernoulli win probability; ties are non-wins. Paired games are dependent; interval is descriptive, not a paired-inference claim.',
    legality: 'All agents exclude voluntary switches when the addressed raw request signals maybeTrapped; no opponent ability inspection. Engine rejection is never retried or erased.',
    timing: 'Nondeterministic timings join deterministic records by game_id.'}, matchups: [], errors: []};
const started = performance.now();
function save() {fs.mkdirSync(path.dirname(output), {recursive: true}); fs.writeFileSync(output, JSON.stringify(result) + '\n');}
function report() {
  const percent = value => (value * 100).toFixed(2) + '%';
  const rows = result.matchups.map(m => `| ${m.agents[0]} | ${m.agents[1]} | ${m.wins} / ${m.losses} / ${m.ties} | ${percent(m.win_rate)} (${percent(m.wilson_95[0])}–${percent(m.wilson_95[1])}) | ${m.mean_turns.toFixed(2)} | ${m.games_per_second.toFixed(2)} |`);
  const capped = result.matchups.flatMap(m => m.records).filter(r => r.turn_limit_tie).length;
  const text = ['# Baseline capability scoreboard', '',
    `Engine: \`${result.engine_commit}\`. Format: Gen 9 Random Battle. ${pairs} seed pairs per matchup; every seed is played with agents on both teams.`, '',
    '| Agent A | Agent B | A wins / losses / ties | A win rate (Wilson 95% CI) | Mean turns | Games/s |',
    '|---|---|---|---|---|---|', ...rows, '',
    `Total wall time: ${result.wall_time_seconds.toFixed(2)} seconds. Illegal choices: 0; rejected choices: 0; errors: 0. Turn-limit flagged ties: ${capped}.`, '',
    'Exact command (after building sim-core):', '', '```powershell', result.command, '```', '',
    `Seed list: \`tools/bench/seeds.json\` (first ${pairs} entries); SHA-256 \`${result.seed_list_sha256}\`.`, '',
    `Machine results: [${path.basename(output)}](../../${path.relative(root, output).replaceAll('\\', '/')}). Deterministic records and wall-clock timings are separate arrays joined by game_id.`, '',
    'Random and heuristic adapt the existing baselines. Greedy maximizes accuracy-weighted mean calculator damage, never Terastallizes, and selects the first legal reserve only when required. Calculator guesses for unknown stats/items/abilities are explicit neutral scoring hypotheses, never added to observations. Public details without an L token mean level 100 in the pinned engine.', '',
    result.assumptions.legality, '', result.assumptions.intervals, '',
    'No model/search tuning. This measures playing strength independently of knowledge coverage. Legacy Python checkpoints need a subprocess/legacy-feature adapter and parity validation (estimate: 1–2 engineering days); deferred.', ''].join('\n');
  fs.writeFileSync(path.join(root, 'docs/roadmap/benchmarks.md'), text);
}
save();
(async () => {
  try {
    for (const [a, b] of matchups) {
      let count = 0;
      const games = await runMatchup(a, b, allSeeds.slice(0, pairs), () => {
        if (++count % 100 === 0) console.log(`${a} vs ${b}: ${count}/${pairs * 2}`);
      });
      const summary = summarize(games);
      result.matchups.push({agents: [a, b], ...summary, records: games.map(g => g.record), timings: games.map(g => g.timing)});
      console.log(JSON.stringify({agents: [a, b], ...summary})); save();
    }
  } catch (error) {
    console.error(error.message);
    result.errors.push(error.message);
    if (error instanceof BenchRunError) result.failed_game = error.game;
    process.exitCode = 1;
  } finally {result.wall_time_seconds = (performance.now() - started) / 1000; save();
    if (!result.errors.length && result.matchups.length === 3) report();
  }
})();
