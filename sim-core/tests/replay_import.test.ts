import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { importReplayPrefix, importReplayPrefixWithMoveHistory, ReplayImportError } from '../src/replay_import';
import { projectObservableBattleState, validateRawProtocolRecord } from '../src/observable_state';
import type { PlayerID } from '../src/types';
import { PlayerStateExtractor } from '../src/state_extractor';

const root = path.resolve(__dirname, '../../..');
const fixtures = path.join(root, 'trainer/tests/fixtures/perspective-replay');
const ledger = JSON.parse(fs.readFileSync(path.join(fixtures, 'expected-ledger.json'), 'utf8'));
const evidence: unknown[] = [];
const historyEvidence: unknown[] = [];
const python = process.env.PYTHON || 'D:\\Anaconda\\envs\\neuralgpu\\python.exe';
function pythonCall(code: string, args: string[] = [], input?: unknown) {
  const env: NodeJS.ProcessEnv = { ...process.env, PYTHONPATH: path.join(root, 'trainer/src') };
  delete env.PYTHONUTF8; delete env.PYTHONIOENCODING;
  const child = spawnSync(python, ['-c', code, ...args], {
    env, input: input === undefined ? undefined : Buffer.from(JSON.stringify(input), 'utf8'), timeout: 30000,
  });
  assert.equal(child.error, undefined);
  assert.equal(child.status, 0, child.stderr?.toString('utf8'));
  return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(child.stdout));
}
function load(fixture: any): string[] {
  const filename = path.join(fixtures, fixture.filename);
  assert.equal(createHash('sha256').update(fs.readFileSync(filename)).digest('hex'), fixture.sha256);
  const result = pythonCall(`import sys,os,json
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
from neural import compare_action_rankers as loader
from neural import compare_replay_evals as replay_eval
from neural import build_live_private_value_dataset as private_dataset
from neural import build_replay_value_dataset as public_dataset
assert 'PYTHONUTF8' not in os.environ and 'PYTHONIOENCODING' not in os.environ
assert Path(loader.__file__).resolve() == Path(sys.argv[3]).resolve()
with ExitStack() as guards:
 for target,name in [(loader,'load_replay_trajectory'),(loader,'_load_ranker'),(loader,'torch_load'),(loader,'_score_with_ranker'),(loader,'ActionRankerMLP'),(loader.torch,'load'),(replay_eval.urllib.request,'urlopen'),(private_dataset,'build_live_private_value_dataset'),(public_dataset,'build_public_replay_value_dataset')]:
  guards.enter_context(patch.object(target,name,side_effect=AssertionError('forbidden local-import side effect: '+name)))
 p=Path(sys.argv[1])
 value=loader._load_replay(str(p),replay_dir=p.parent,trajectories_path=p.parent/'unused',format_name=sys.argv[2])
sys.stdout.buffer.write(json.dumps(value['protocol_log'],ensure_ascii=False).encode('utf-8'))`,
    [filename, fixture.format, path.join(root, 'trainer/src/neural/compare_action_rankers.py')]);
  assert.equal(result.length, fixture.record_count);
  assert.ok(result[0].startsWith('|j|☆'));
  return result;
}
const actual = ledger.fixtures.map((fixture: any) => ({ fixture, records: load(fixture) }));
function context(owner: PlayerID = 'p1', format = 'gen9randombattle') {
  return { env_id: 'prompt19-é-Ω', format, perspective: owner, protocol_profile: 'historical10' as const };
}
function reject(records: unknown, cursor: unknown, index: number | null, stage = 'admission', ctx = context()) {
  assert.throws(() => importReplayPrefix(records as string[], cursor as number, ctx), (error: unknown) => {
    assert.ok(error instanceof ReplayImportError);
    assert.equal(error.source_index, index);
    assert.equal(error.stage, stage);
    for (const key of ['view', 'protocol_prefix', 'source_rows', 'source_to_routed']) assert.ok(!(key in error));
    evidence.push({ stage: 'indexed-rejection', perspective: ctx.perspective, format: ctx.format,
      source_cursor: cursor, error_stage: error.stage, source_index: error.source_index, record: error.record, error: error.message });
    return true;
  });
}
function project(records: string[], cursor: number, owner: PlayerID, format = 'gen9randombattle') {
  const trace = importReplayPrefix(records, cursor, context(owner, format));
  const observation = projectObservableBattleState({ schema_version: 'observable-battle-state/v2', source_kind: 'replay',
    battle_id: 'prompt19-é-Ω', perspective: owner, snapshot_phase: 'replay-header-check',
    protocol_prefix: trace.protocol_prefix, view: trace.view, request: null });
  assert.deepEqual(observation.protocol_prefix, trace.protocol_prefix);
  assert.equal(observation.event_cursor, trace.protocol_prefix.length);
  const validated = pythonCall(`import sys,os,json
from neural.pipeline_json_wire import load_json
from neural.ts_identity import verify_observation
from neural.pipeline_record import _prefix
from neural.typed_state import validate_public_typed_state
assert 'PYTHONUTF8' not in os.environ and 'PYTHONIOENCODING' not in os.environ
o=load_json(sys.stdin)
assert 'é-Ω' in o['battle_id']
verify_observation(o,'prompt19')
_prefix(o,'prompt19')
validate_public_typed_state(o,'prompt19')
sys.stdout.buffer.write(json.dumps({'ok':True,'owner':o['perspective'],'cursor':o['event_cursor']}).encode('utf-8'))`, [], observation);
  evidence.push({ stage: 'projector/python', format, owner, source_cursor: cursor,
    event_cursor: observation.event_cursor, validated });
  return { trace, observation };
}

test('actual decoded loader retains direct-validator red headers; adapter admits literal maps for both owners', () => {
  const maps = [
    [2,3,4,5,6,9,10,11,12,14,15,16,17,18,19],
    [2,3,4,5,6,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,34,35,36,37,38,39],
  ];
  for (const [i, { fixture, records }] of actual.entries()) {
    const direct = new PlayerStateExtractor('prompt19-before', fixture.format, 'p1');
    let firstFailure = -1;
    for (let index = 0; index < records.length; index++) {
      try { direct.consumeChunk(records[index]); }
      catch { firstFailure = index; break; }
    }
    assert.equal(firstFailure, 8);
    evidence.push({ stage: 'unchanged-extractor-red', fixture: fixture.key, source_index: firstFailure, record: records[firstFailure] });
    for (const index of [0,1,8]) {
      assert.throws(() => validateRawProtocolRecord(records[index]));
      evidence.push({ stage: 'unchanged-direct-validator-red', fixture: fixture.key, source_index: index, record: records[index] });
    }
    for (const owner of ['p1','p2'] as PlayerID[]) {
      const cursor = i === 0 ? 20 : 40;
      const { trace } = project(records, cursor, owner, fixture.format);
      assert.deepEqual(trace.routed_to_source, maps[i]);
      assert.deepEqual(trace.source_to_routed, i === 0
        ? [null,null,0,1,2,3,4,null,null,5,6,7,8,null,9,10,11,12,13,14]
        : [null,null,0,1,2,3,4,null,null,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,null,29,30,31,32,33,34]);
      assert.deepEqual(trace.source_rows.map(row => row.record), records.slice(0, cursor));
      assert.equal(trace.view.names.p1, 'hasklne');
      assert.equal(trace.view.names.p2, i === 0 ? 'kaiser_me' : 'loob');
      assert.equal(trace.view.self_team.find(p => p.active)!.hp_ratio, 1);
      assert.equal(trace.view.opponent_team.find(p => p.active)!.hp_ratio, 1);
      evidence.push({ stage: 'literal-maps-green', fixture: fixture.key, owner, source_cursor: cursor,
        source_to_routed: trace.source_to_routed, routed_to_source: trace.routed_to_source });
    }
  }
});

test('metadata-only boundaries, native rated, duplicate positions and mutation safety', () => {
  const metadata = ['|j|☆é😀', '|rated|', '|tier|[Gen 9] Random Battle', '|'];
  const before = [...metadata];
  for (const owner of ['p1','p2'] as PlayerID[]) {
    const empty = project(metadata, 0, owner);
    for (let cursor = 1; cursor <= metadata.length; cursor++) {
      const result = project(metadata, cursor, owner);
      assert.deepEqual(result.observation, empty.observation);
      assert.deepEqual(result.trace.view, empty.trace.view);
      assert.equal(result.trace.source_cursor, cursor);
      assert.deepEqual(result.trace.source_to_routed, Array(cursor).fill(null));
    }
  }
  assert.deepEqual(metadata, before);
  const duplicate = ['|', '|rated', '|turn|1', '|turn|1', '|', '|rated|Rated'];
  const trace = importReplayPrefix(duplicate, duplicate.length, context());
  assert.deepEqual(trace.routed_to_source, [1,2,3,5]);
  assert.deepEqual(trace.source_to_routed, [null,0,1,2,null,3]);
  assert.deepEqual(importReplayPrefix(duplicate, duplicate.length, context()), trace);
  assert.throws(() => (trace.source_rows[0] as any).record = 'changed', TypeError);
  assert.throws(() => (trace.routed_to_source as number[]).push(99), TypeError);
  assert.throws(() => trace.view.names.p1 = 'changed', TypeError);
  duplicate[2] = '|turn|2';
  assert.equal(trace.protocol_prefix[1], '|turn|1');
});

test('invalid cursor, selected input, metadata grammar, controls and private transport fail atomically', () => {
  for (const cursor of [-1, 2, .5, true, false, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) reject(['|'], cursor, null, 'input');
  for (const input of [null, {}, 'not an array']) reject(input, 0, null, 'input');
  reject(['|', 7], 2, 1);
  for (const record of ['|j|☆', '|j|☆ name', '|j|☆name ', '|j|☆name|extra', '|j|+name', '|j|@name',
    '|join|☆name', '|J|☆name', '|j|☆name\t', '|j|☆name\u0085', '|j|☆name\u2028',
    '|turn|1\n|win|name', '|tier|', '|unknown|x', '|request|{}', '|split|p1', '|raw|rating HTML', '|l|name', '|player|p2|']) {
    reject(['|rated|', record], 2, 1);
  }
  for (const start of ['|start', '|start|']) {
    reject([start, '|j|☆name'], 2, 1);
    reject([start, '|rated|'], 2, 1);
  }
  assert.throws(() => importReplayPrefix([], 0, { ...context(), perspective: 'p3' as PlayerID }), ReplayImportError);
  assert.throws(() => importReplayPrefix([], 0, { ...context(), format: '' }), ReplayImportError);
  assert.equal(importReplayPrefix([7 as any], 0, context()).protocol_prefix.length, 0);
  const contradiction = ['|player|p1|Alice', '|player|p1|Bob', '|turn|1'];
  for (const record of contradiction) validateRawProtocolRecord(record);
  reject(contradiction, 3, 1, 'prefix');
  reject(['|gen|0', '|turn|1'], 2, 0, 'prefix');
  reject(['|turn|1', '|turn|0', '|rated'], 3, 1, 'prefix');
});

test('existing public Healing Wish seam preserves public HP for both owners', () => {
  const prefix = ['|switch|p1a: Skuntank|Skuntank, L80|50/100',
    '|-heal|p1a: Skuntank|100/100|[from] move: Healing Wish'];
  for (const owner of ['p1','p2'] as PlayerID[]) {
    const view = importReplayPrefix(prefix, prefix.length, context(owner)).view;
    const team = owner === 'p1' ? view.self_team : view.opponent_team;
    assert.equal(team.find(p => p.active)!.hp_ratio, 1);
  }
});

test('actual same-turn HP boundaries and suffix invariance for both perspectives', () => {
  for (const { fixture, records } of actual) {
    const damageIndex = fixture.key === 'random' ? 27 : 47;
    const side = fixture.key === 'random' ? 'p1' : 'p2';
    const afterHP = fixture.key === 'random' ? 163/310 : .32;
    for (const owner of ['p1','p2'] as PlayerID[]) {
      const before = project(records, damageIndex, owner, fixture.format);
      const after = project(records, damageIndex + 1, owner, fixture.format);
      const team = owner === side ? 'self_team' : 'opponent_team';
      assert.equal(before.trace.view[team].find(p => p.active)!.hp_ratio, 1);
      assert.equal(after.trace.view[team].find(p => p.active)!.hp_ratio, afterHP);
      assert.equal(before.trace.view.turn, after.trace.view.turn);
      assert.equal(after.trace.routed_to_source.at(-1), damageIndex);
      const suffix = [...records.slice(0, damageIndex + 1), '|j|☆future', '|turn|99', '|win|future', '|unknown|future', 42 as any];
      assert.deepEqual(importReplayPrefix(suffix, damageIndex + 1, context(owner, fixture.format)), after.trace);
      evidence.push({ stage: 'same-turn-green', fixture: fixture.key, owner, index: damageIndex,
        before: 1, after: afterHP, turn: after.trace.view.turn });
    }
  }
});

test('Random winner reaches actual projection/Python checks; rating suffix and OU mechanics retain original rejection indices', () => {
  const random = actual[0], ou = actual[1];
  assert.equal(random.records[367], '|win|hasklne');
  for (const owner of ['p1','p2'] as PlayerID[]) {
    const winner = project(random.records, 368, owner);
    assert.equal(winner.trace.view.winner, 'p1');
    assert.equal(winner.trace.view.terminated, true);
    reject(random.records, 370, 368, 'admission', context(owner));
    assert.doesNotThrow(() => importReplayPrefix(ou.records, 173, context(owner, ou.fixture.format)));
    reject(ou.records, 305, 173, 'admission', context(owner, ou.fixture.format));
  }
  for (const index of [173,266,295,301,302,303,304]) {
    assert.throws(() => validateRawProtocolRecord(ou.records[index]));
    evidence.push({ stage: 'retained-OU-blocker', source_index: index, record: ou.records[index] });
  }
  evidence.push({ stage: 'retained-random-raw', source_index: 368, record: random.records[368] });
});

test('companion retains literal real execution appearances across reentry without changing replay or projected IDs', () => {
  const cases = [
    {fixture:0,execution:53,reentry:106,appearance:'p1:appearance:2',start:49,end:58,newAppearance:'p1:appearance:5',
      move:'U-turn',record:'|move|p1a: Perrserker|U-turn|p2a: Dondozo'},
    {fixture:0,execution:128,reentry:243,appearance:'p1:appearance:5',start:106,end:132,newAppearance:'p1:appearance:10',
      move:'U-turn',record:'|move|p1a: Perrserker|U-turn|p2a: Cinccino'},
    {fixture:1,execution:45,reentry:119,appearance:'p1:appearance:1',start:38,end:58,newAppearance:'p1:appearance:5',
      move:'Ice Beam',record:'|move|p1a: Kyurem|Ice Beam|p2a: Ting-Lu'},
  ];
  for (const example of cases) {
    const {fixture,records} = actual[example.fixture];
    const histories: unknown[] = [];
    for (const owner of ['p1','p2'] as PlayerID[]) {
      const before = importReplayPrefix(records,example.reentry,context(owner,fixture.format));
      assert.ok(!('public_move_history' in before));
      assert.ok(!('public_move_history' in before.view));
      const early = importReplayPrefixWithMoveHistory(records,example.execution,context(owner,fixture.format));
      assert.ok(!early.public_move_history.executions.some(e => e.source_index === example.execution));
      const witnessed = importReplayPrefixWithMoveHistory(records,example.execution+1,context(owner,fixture.format));
      assert.equal(witnessed.public_move_history.appearances.find(a => a.subject === example.appearance)!.end_source_index,null);
      const receipt = {appearance:example.appearance,source_index:example.execution,observed_at:example.execution+1,
        record:example.record,move:example.move,origin_tags:[],context_witnesses:[],origin_status:'unannotated'};
      assert.deepEqual(witnessed.public_move_history.executions.find(e => e.source_index === example.execution),receipt);
      const prior = importReplayPrefixWithMoveHistory(records,example.reentry,context(owner,fixture.format));
      const companion = importReplayPrefixWithMoveHistory(records,example.reentry+1,context(owner,fixture.format));
      assert.deepEqual(prior.replay,before);
      assert.deepEqual(companion.public_move_history.executions.find(e => e.source_index === example.execution),receipt);
      assert.deepEqual(companion.public_move_history.appearances.find(a => a.subject === example.appearance),
        {subject:example.appearance,side:'p1',start_source_index:example.start,end_source_index:example.end,disclosure_source_indices:[],carrier:null});
      assert.equal(companion.public_move_history.appearances.find(a => a.start_source_index === example.reentry)!.subject,example.newAppearance);
      assert.equal(prior.replay.view.turn,companion.replay.view.turn);
      const {trace,observation} = project(records,example.reentry+1,owner,fixture.format);
      assert.deepEqual(companion.replay,trace);
      const projected = projectObservableBattleState({schema_version:'observable-battle-state/v2',source_kind:'replay',
        battle_id:'prompt19-é-Ω',perspective:owner,snapshot_phase:'replay-header-check',
        protocol_prefix:companion.replay.protocol_prefix,view:companion.replay.view,request:null});
      assert.deepEqual(projected,observation);
      const team = owner === 'p1' ? companion.replay.view.self_team : companion.replay.view.opponent_team;
      assert.deepEqual(team.find(p => p.active)!.revealed_moves,[]);
      const guarded = new Proxy(records,{get(target,key,receiver) {
        if (typeof key === 'string' && /^\d+$/.test(key) && Number(key) >= example.reentry+1) throw new Error('Future source read');
        return Reflect.get(target,key,receiver);
      }});
      assert.deepEqual(importReplayPrefixWithMoveHistory(guarded,example.reentry+1,context(owner,fixture.format)),companion);
      assert.deepEqual(importReplayPrefixWithMoveHistory([...records.slice(0,example.reentry+1),
        '|move|p2a: Future|Secret|p1a: Future','|unknown|future',42 as any],example.reentry+1,context(owner,fixture.format)),companion);
      histories.push(companion.public_move_history);
      historyEvidence.push({fixture:fixture.key,owner,source_cursor:example.reentry+1,receipt,
        appearance:companion.public_move_history.appearances.find(a => a.subject === example.appearance),
        replay_equals_original:true,projected_ids_and_hashes_identical:true,
        observation_id:observation.observation_id,active_revealed:[],history_issues:companion.public_move_history.issues});
    }
    assert.deepEqual(histories[0],histories[1]);
  }
  for (const owner of ['p1','p2'] as PlayerID[]) {
    const history = importReplayPrefixWithMoveHistory(actual[0].records,244,context(owner)).public_move_history;
    assert.deepEqual(history.executions.filter(e => e.source_index === 53 || e.source_index === 128)
      .map(e => [e.source_index,e.observed_at,e.appearance,e.move]),
      [[53,54,'p1:appearance:2','U-turn'],[128,129,'p1:appearance:5','U-turn']]);
    historyEvidence.push({fixture:'random',owner,source_cursor:244,coexisting_receipts:[53,128]});
  }
});

test('companion winner closes appearances and preserves original full-input rejection stages/indices', () => {
  for (const owner of ['p1','p2'] as PlayerID[]) {
    const {trace,observation} = project(actual[0].records,368,owner);
    const companion = importReplayPrefixWithMoveHistory(actual[0].records,368,context(owner));
    assert.deepEqual(companion.replay,trace);
    assert.ok(companion.public_move_history.appearances.every(a => a.end_source_index !== null));
    assert.ok(companion.public_move_history.appearances.some(a => a.end_source_index === 367));
    for (const [i,index] of [[0,368],[1,173]]) {
      const {fixture,records} = actual[i];
      assert.throws(() => importReplayPrefixWithMoveHistory(records,records.length,context(owner,fixture.format)),(error: unknown) => {
        assert.ok(error instanceof ReplayImportError); assert.equal(error.source_index,index); assert.equal(error.stage,'admission');
        assert.ok(!('replay' in error)); assert.ok(!('public_move_history' in error)); return true;
      });
    }
    historyEvidence.push({fixture:'random',owner,source_cursor:368,closure_index:367,
      replay_equals_original:true,observation_id:observation.observation_id});
  }
});

test.after(() => {
  if (process.env.PROMPT19_REPORT) fs.writeFileSync(process.env.PROMPT19_REPORT,
    JSON.stringify({ scope: 'header import only; completeness/source authority unverified', evidence }, null, 2) + '\n', 'utf8');
  if (process.env.PROMPT21_REPORT) fs.writeFileSync(process.env.PROMPT21_REPORT,
    JSON.stringify({scope:'untrusted public appearance history; carrier/current/original completeness unverified',historyEvidence},null,2)+'\n','utf8');
});
