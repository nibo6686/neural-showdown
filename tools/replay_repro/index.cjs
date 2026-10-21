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

async function extractReplay(replay) {
  // Reproduction validates the engine pin, input command allowlist and public log.
  const reproduction = await reproduceReplay(replay);
  if (!reproduction.full_match) throw new Error('Replay reproduction diverged: '+replay.id);
  const {LocalBattleEnv} = require(path.join(root,'sim-core/dist/src/env_manager.js'));
  const {PlayerStateExtractor} = require(path.join(root,'sim-core/dist/src/state_extractor.js'));
  const {NATIVE11_CONTEXT} = require(path.join(root,'sim-core/dist/src/version_profile.js'));
  const env = LocalBattleEnv.createSimulationOnly({id:replay.id,format:'gen9randombattle'});
  const trackers = Object.fromEntries(['p1','p2'].map(owner=>[owner,new PlayerStateExtractor(replay.id,'gen9randombattle',owner,NATIVE11_CONTEXT)]));
  const failures = [], records = {p1:0,p2:0};
  const input = replay.inputlog.split(/\r?\n/).filter(line=>!line.startsWith('>version ')&&!line.startsWith('>chat ')).join('\n');
  const consume = (owner,chunk,publicHealingWish=false)=> {
      for(const record of chunk.split('\n')) {
        if(!record)continue;
        if(!publicHealingWish)records[owner]++;
        try {
          if(publicHealingWish)trackers[owner].consumePublicHealingWishRecord(record);
          else trackers[owner].consumeChunk(record);
        }
        catch(error) {
          const parts=record.split('|'), command=parts[1]||'';
          const effect=['-start','-end','-sidestart','-sideend'].includes(command)?parts[3]:['-weather','-fieldstart','-fieldend'].includes(command)?parts[2]:'';
          const rawID=(effect||'').toLowerCase().replace(/[^a-z0-9]/g,'');
          const special=NATIVE11_CONTEXT.inventory.effect_discovery.special_values.some(e=>e.id===rawID&&e.commands.includes(command));
          failures.push({owner,command,effect_id:special?rawID:(effect||'').replace(/^(?:move|ability|item):\s*/i,'').toLowerCase().replace(/[^a-z0-9]/g,''),record,name:error.name,message:error.message});
        }
      }
  };
  try {
    // Match LocalBattleEnv.listenSpectator's exact public Healing Wish seam.
    await env.replaySimulation(input,consume,chunk=> {
      for(const owner of ['p1','p2'])consume(owner,chunk,true);
    });
  } finally { await env.close(); }
  // A failed record invalidates that perspective's state; continued scanning is
  // diagnostic only and never returns a partially accepted view or dataset row.
  return {id:replay.id,records,failures};
}

async function main(directory, extract=false) {
  if (!directory) throw new Error('Usage: node tools/replay_repro/index.cjs <replay-directory>');
  let count = 0, matches = 0, failed=0; const groups=new Map();
  for (const name of fs.readdirSync(directory).sort()) {
    if (!name.endsWith('.json') || name.startsWith('impulse-')) continue;
    const replay = JSON.parse(fs.readFileSync(path.join(directory, name), 'utf8'));
    // The probe directory also contains acquisition summaries, not replay records.
    if (!Object.hasOwn(replay, 'inputlog') && !Object.hasOwn(replay, 'log')) continue;
    const result = extract ? await extractReplay(replay) : await reproduceReplay(replay);
    count++; if (extract ? !result.failures.length : result.full_match) matches++;
    if(extract) for(const failure of result.failures) {
      failed++;
      const key=JSON.stringify([failure.command,failure.effect_id,failure.message]);
      const group=groups.get(key)||{command:failure.command,effect_id:failure.effect_id,message:failure.message,records:0,replays:new Set()};
      group.records++;group.replays.add(replay.id);groups.set(key,group);
    }
    if(!extract)console.log(JSON.stringify(result));
  }
  if (!count) throw new Error('No replay records found');
  console.log(JSON.stringify(extract?{replays:count,extracted_without_failures:matches,failed_records:failed,
    failures:[...groups.values()].map(g=>({...g,replays:[...g.replays]}))}:{replays: count, exact_matches: matches}));
  if (matches !== count) process.exitCode = 1;
}
module.exports = {reproduceReplay,extractReplay};
if (require.main === module) main(process.argv.slice(2).find(a=>a!=='--extract'),process.argv.includes('--extract')).catch(error => { console.error(error); process.exitCode = 1; });
