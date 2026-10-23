'use strict';
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const {installedNativeProfile} = require(path.join(root, 'sim-core/dist/src/version_profile.js'));
const runtime = installedNativeProfile();
const {BattleStream} = require(runtime.package_root);
const {keep} = require('./public_log.cjs');

async function reproduceReplay(replay) {
  if (!replay || typeof replay.id !== 'string' || !replay.id || typeof replay.inputlog !== 'string' || typeof replay.log !== 'string') throw new Error('Invalid replay: id, inputlog and log required');
  const input = replay.inputlog.split(/\r?\n/);
  const commands = new Set(['>version', '>chat', '>start', '>player', '>p1', '>p2', '>reseed', '>forcewin', '>forcelose', '>forcetie']);
  for (const line of input) {
    if (line && !commands.has(line.split(' ')[0])) throw new Error('Unsupported replay input command');
  }
  const versions = input.filter(line => line.split(' ')[0] === '>version');
  const version = versions[0]?.slice(9);
  if (versions.length !== 1 || !/^[a-f0-9]{40}$/.test(version || '')) throw new Error('Replay engine version mismatch');
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

async function extractReplay(replay, {diff=false}={}) {
  // Exact public reproduction admits a replay; its server commit remains provenance.
  const reproduction = await reproduceReplay(replay);
  if (!reproduction.full_match) throw new Error('Replay reproduction diverged: '+replay.id);
  return extractReproducedReplay(replay,{diff});
}

// Private seam: only the two reproduction-gated callers enter here.
async function extractReproducedReplay(replay,{diff}) {
  const {LocalBattleEnv} = require(path.join(root,'sim-core/dist/src/env_manager.js'));
  const {PlayerStateExtractor} = require(path.join(root,'sim-core/dist/src/state_extractor.js'));
  const {NATIVE11_CONTEXT} = require(path.join(root,'sim-core/dist/src/version_profile.js'));
  const env = LocalBattleEnv.createSimulationOnly({id:replay.id,format:'gen9randombattle'});
  const trackers = Object.fromEntries(['p1','p2'].map(owner=>[owner,new PlayerStateExtractor(replay.id,'gen9randombattle',owner,NATIVE11_CONTEXT)]));
  const failures = [], records = {p1:0,p2:0};
  const prefixes={p1:[],p2:[]},mismatches=[];let checks=0,boundaries=0;
  const {compareReplayPublicState}=require(path.join(root,'sim-core/dist/src/replay_public_diff.js'));
  const input = replay.inputlog.split(/\r?\n/).filter(line=>!line.startsWith('>version ')&&!line.startsWith('>chat ')).join('\n');
  const consume = (owner,chunk,publicHealingWish=false)=> {
      for(const record of chunk.split('\n')) {
        if(!record)continue;
        if(!publicHealingWish)records[owner]++;
        try {
          if(publicHealingWish)trackers[owner].consumePublicHealingWishRecord(record);
          else trackers[owner].consumeChunk(record);
          if(!publicHealingWish || /^\|-heal\|[^|]+\|100\/100\|\[from\] move: Healing Wish$/.test(record))prefixes[owner].push(record);
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
    },diff ? battle=> {
      if(failures.length)return;
      boundaries++;
      for(const owner of ['p1','p2']) {
        try {const result=compareReplayPublicState(battle,trackers[owner].getView(),prefixes[owner]);checks+=result.checks;mismatches.push(...result.mismatches);}
        catch(error){mismatches.push({owner,turn:battle.turn,fact:'public-prefix',effect_id:'',message:error.message});}
      }
    }:undefined);
  } finally { await env.close(); }
  // A failed record invalidates that perspective's state; continued scanning is
  // diagnostic only and never returns a partially accepted view or dataset row.
  return {id:replay.id,records,failures,...(diff?{boundaries,checks,mismatches}: {})};
}

async function admitReplay(replay, {extract=false, diff=false}={}) {
  replay = replay && typeof replay === 'object' ? replay : {};
  const inputlog=typeof replay.inputlog==='string'?replay.inputlog:'', log=typeof replay.log==='string'?replay.log:'';
  const row = {id: replay.id ?? null, server_commit: inputlog.split(/\r?\n/).find(l=>l.startsWith('>version '))?.slice(9) ?? null,
    rating: replay.rating ?? null, uploadtime: replay.uploadtime ?? null, turns: replay.turns ?? (log ? Math.max(0,...[...log.matchAll(/^\|turn\|(\d+)$/gm)].map(m=>Number(m[1]))) : null),
    winner: log.split(/\r?\n/).find(l=>l.startsWith('|win|'))?.slice(5) ?? null,
    ending: null, format_id: null, reproduction: 'not-run', extraction: 'not-run', diff_mismatch_count: null, admitted: false};
  if (/^(rom|impulse|smogtours)-/.test(replay.id)) return {...row, reason:'side-server'};
  try {
    const reproduction = await reproduceReplay(replay);
    row.ending = /^\|tie$/m.test(replay.log) ? 'tie' : reproduction.ending;
    row.reproduction = reproduction.full_match ? 'exact' : 'diverged';
    if (!reproduction.full_match) return {...row, reason:'reproduction-diverged', divergence:reproduction};
    const starts=inputlog.split(/\r?\n/).filter(line=>line.startsWith('>start '));
    if(starts.length!==1)throw new Error('Replay must have exactly one start command');
    row.format_id=JSON.parse(starts[0].slice(7)).formatid ?? null;
    if(row.format_id !== 'gen9randombattle')return {...row,reason:typeof row.format_id==='string'&&row.format_id.startsWith('gen9randombattle@@@')?'custom-rules':'format-out-of-scope'};

    if (/^\|(?:-swapsideconditions(?:\||$)|-activate\|[^\n]*\|move: Court Change(?:\||$))/m.test(replay.log)) return {...row,reason:'court-change'};
    if (extract) {
      const result = await extractReproducedReplay(replay,{diff});
      row.extraction = result.failures.length ? 'failed' : 'clean';
      row.failure_kinds = [...new Set(result.failures.map(f=>f.command+': '+f.message))];
      row.failures = result.failures;
      if (result.failures.length) return {...row,reason:'extraction-failed'};
      if (diff) {
        row.diff_mismatch_count = result.mismatches.length;
        row.checks = result.checks;
        row.boundaries = result.boundaries;
        if(result.mismatches.length) return {...row,reason:'diff-mismatch',mismatches:result.mismatches};
      }
    }
    row.admitted = true;
    return row;
  } catch(error) {return {...row,reproduction:row.reproduction==='not-run'?'failed':row.reproduction,reason:'failed',error:error.message};}
}

async function main(directory, extract=false, diff=false, {limit,manifest,shardIndex=0,shardCount=1,quiet=false,files}={}) {
  if (!directory) throw new Error('Usage: node tools/replay_repro/index.cjs <replay-directory> [--extract] [--diff] [--limit=N] [--manifest=path]');
  const started = performance.now(), summary = {replays:0,admitted:0,by_commit:Object.create(null),exclusions:{},failure_kinds:{},diff_mismatches:0,checks:0};
  if (manifest) fs.writeFileSync(manifest,'');
  const selected=files?new Set(files):null;
  let fileIndex=0;
  for (const name of fs.readdirSync(directory).sort()) {
    if (!name.endsWith('.json') || selected && !selected.has(name)) continue;
    if (fileIndex++ % shardCount !== shardIndex) continue;
    let replay;
    try {replay=JSON.parse(fs.readFileSync(path.join(directory,name),'utf8'));}
    catch(error) {const row={id:path.basename(name,'.json'),admitted:false,reason:'invalid-json',error:error.message};if(manifest)fs.appendFileSync(manifest,JSON.stringify(row)+'\n');summary.replays++;summary.exclusions['invalid-json']=(summary.exclusions['invalid-json']||0)+1;continue;}
    if (!replay || typeof replay !== 'object') replay={id:path.basename(name,'.json'),inputlog:null,log:null};
    if (!Object.hasOwn(replay,'inputlog') && !Object.hasOwn(replay,'log')) continue;
    replay.id ??= path.basename(name,'.json');
    if (limit && summary.replays >= limit) break;
    const row=await admitReplay(replay,{extract,diff});
    summary.replays++; if(row.admitted)summary.admitted++;
    const commit=row.server_commit ?? 'unknown';
    const group=summary.by_commit[commit] ||= {replays:0,admitted:0};group.replays++;if(row.admitted)group.admitted++;
    if(row.reason)summary.exclusions[row.reason]=(summary.exclusions[row.reason]||0)+1;
    for(const kind of row.failure_kinds||[])summary.failure_kinds[kind]=(summary.failure_kinds[kind]||0)+1;
    summary.diff_mismatches+=row.diff_mismatch_count||0;summary.checks+=row.checks||0;
    if(manifest)fs.appendFileSync(manifest,JSON.stringify(row)+'\n');
    else console.log(JSON.stringify(row));
    if(summary.replays%500===0)console.error(`Processed ${summary.replays}; admitted ${summary.admitted}`);
  }
  if(!summary.replays)throw new Error('No replay records found');
  summary.wall_time_seconds=(performance.now()-started)/1000;
  if(!quiet)console.log(JSON.stringify(summary));
  return summary;
}
module.exports = {reproduceReplay,extractReplay,admitReplay,main};
if (require.main === module && process.argv.includes('--born')) {
  require('./born_census.cjs').runBornCensus(process.argv.slice(2)).catch(error=>{console.error(error);process.exitCode=1;});
} else if (require.main === module) {
  const args=process.argv.slice(2), option=name=>args.find(a=>a.startsWith('--'+name+'='))?.slice(name.length+3);
  main(args.find(a=>!a.startsWith('--')),args.includes('--extract')||args.includes('--diff'),args.includes('--diff'),
    {limit:option('limit')?Number(option('limit')):undefined,manifest:option('manifest')}).catch(error=>{console.error(error);process.exitCode=1;});
}
