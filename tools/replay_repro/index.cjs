'use strict';
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const {installedNativeProfile} = require(path.join(root, 'sim-core/dist/src/version_profile.js'));
const runtime = installedNativeProfile();
const {BattleStream} = require(runtime.package_root);
const ignored = new Set(['t:', 'j', 'J', 'l', 'L', 'n', 'N', 'c', 'c:', 'raw', 'html', 'uhtml',
  'uhtmlchange', 'inactive', 'inactiveoff', 'player', 'gametype', 'gen', 'tier', 'rated', 'rule',
  'teampreview', 'seed', 'timer', 'debug', 'request', 'error', 'sideupdate', 'badge', '']);
const keep = line => line.startsWith('|') && !ignored.has(line.split('|')[1]);

async function reproduceReplay(replay) {
  if (!replay || typeof replay.id !== 'string' || !replay.id || typeof replay.inputlog !== 'string' || typeof replay.log !== 'string') throw new Error('Invalid replay: id, inputlog and log required');
  const input = replay.inputlog.split(/\r?\n/);
  const commands = new Set(['>version', '>chat', '>start', '>player', '>p1', '>p2', '>reseed', '>forcewin', '>forcelose', '>forcetie']);
  for (const line of input) {
    if (line && !commands.has(line.split(' ')[0])) throw new Error('Unsupported replay input command');
  }
  const versions = input.filter(line => line.startsWith('>version '));
  const version = versions[0]?.slice(9);
  if (versions.length !== 1 || version !== runtime.engine_commit) throw new Error('Replay engine version mismatch');
  if (!input.some(line => line.startsWith('>start ')) || !input.some(line => line.startsWith('>player p1 ')) || !input.some(line => line.startsWith('>player p2 '))) throw new Error('Incomplete replay input');
  const publicLines = replay.log.split(/\r?\n/);
  const endingAt = publicLines.findIndex(line => /^\|-message\|.*(?: forfeited\.| lost due to inactivity\.)$/.test(line));
  const ending = endingAt < 0 ? 'normal' : publicLines[endingAt].includes('forfeited.') ? 'forfeit' : 'inactivity';
  const expected = (endingAt < 0 ? publicLines : publicLines.slice(0, endingAt)).filter(keep);
  if (!expected.length || !expected.includes('|start')) throw new Error('Empty or incomplete public battle log');
  const stream = new BattleStream({noCatch: true, keepAlive: true});
  const updates = [];
  // Collect only simulator update frames; request/error frames never become battle evidence.
  const consume = (async () => { for await (const chunk of stream) {
    if (chunk.startsWith('update\n')) updates.push(...chunk.slice(7).split('\n'));
    else if (chunk.includes('|error|')) throw new Error('Simulator rejected replay input: ' + chunk);
  } })();
  try {
    await stream.write(input.filter(line => !line.startsWith('>version ') && !line.startsWith('>chat ')).join('\n'));
  } finally {
    await stream.writeEnd();
    await consume;
  }
  const actual = [];
  for (let i = 0; i < updates.length; i++) {
    if (updates[i].startsWith('|split|')) {
      if (i + 2 >= updates.length) throw new Error('Incomplete split update');
      const alternatives = [updates[++i], updates[++i]];
      if (alternatives.some(keep)) actual.push(alternatives);
    } else if (keep(updates[i])) actual.push([updates[i]]);
  }
  if (endingAt >= 0) actual.splice(expected.length);
  let matched = 0, turn = 0;
  while (matched < expected.length && actual[matched]?.includes(expected[matched])) {
    if (expected[matched].startsWith('|turn|')) turn = Number(expected[matched].slice(6));
    matched++;
  }
  const fullMatch = matched === expected.length && actual.length === expected.length;
  const differingTurn = /^\|turn\|(\d+)$/.exec(expected[matched] || '');
  return {id: replay.id, version, rating: replay.rating ?? null, ending, matched_prefix_length: matched,
    full_match: fullMatch, divergence_turn: fullMatch ? null : differingTurn ? Number(differingTurn[1]) : turn,
    sim: fullMatch ? null : actual[matched] ?? null, public: fullMatch ? null : expected[matched] ?? null};
}

async function main(directory) {
  if (!directory) throw new Error('Usage: node tools/replay_repro/index.cjs <replay-directory>');
  let count = 0, matches = 0;
  for (const name of fs.readdirSync(directory).sort()) {
    if (!name.endsWith('.json') || name.startsWith('impulse-')) continue;
    const replay = JSON.parse(fs.readFileSync(path.join(directory, name), 'utf8'));
    // The probe directory also contains acquisition summaries, not replay records.
    if (!Object.hasOwn(replay, 'inputlog') && !Object.hasOwn(replay, 'log')) continue;
    const result = await reproduceReplay(replay);
    count++; if (result.full_match) matches++;
    console.log(JSON.stringify(result));
  }
  if (!count) throw new Error('No replay records found');
  console.log(JSON.stringify({replays: count, exact_matches: matches}));
  if (matches !== count) process.exitCode = 1;
}
module.exports = {reproduceReplay};
if (require.main === module) main(process.argv[2]).catch(error => { console.error(error); process.exitCode = 1; });
