import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { importReplayPrefix, ReplayImportError } from '../src/replay_import';
import { PlayerStateExtractor } from '../src/state_extractor';
import type { PlayerID } from '../src/types';

const root = path.resolve(__dirname, '../../..');
const fixtures = path.join(root, 'trainer/tests/fixtures/perspective-replay');
const ledger = JSON.parse(fs.readFileSync(path.join(fixtures, 'expected-ledger.json'), 'utf8'));
const evidence: unknown[] = [];
const ctx = (perspective: PlayerID, format = 'gen9randombattle') => ({ env_id: 'prompt20-é-Ω', format, perspective, protocol_profile: 'historical10' as const });
function load(fixture: any): string[] {
  const filename = path.join(fixtures, fixture.filename);
  assert.equal(createHash('sha256').update(fs.readFileSync(filename)).digest('hex'), fixture.sha256);
  const env: NodeJS.ProcessEnv = { ...process.env, PYTHONPATH: path.join(root, 'trainer/src') };
  delete env.PYTHONUTF8; delete env.PYTHONIOENCODING;
  const code = `import os,sys,json
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
from neural import compare_action_rankers as loader
from neural import compare_replay_evals as replay_eval
from neural import build_live_private_value_dataset as private_dataset
from neural import build_replay_value_dataset as public_dataset
assert 'PYTHONUTF8' not in os.environ and 'PYTHONIOENCODING' not in os.environ
assert Path(loader.__file__).resolve()==Path(sys.argv[3]).resolve()
with ExitStack() as guards:
 for target,name in [(loader,'load_replay_trajectory'),(loader,'_load_ranker'),(loader,'torch_load'),(loader,'_score_with_ranker'),(loader,'ActionRankerMLP'),(loader.torch,'load'),(replay_eval.urllib.request,'urlopen'),(private_dataset,'build_live_private_value_dataset'),(public_dataset,'build_public_replay_value_dataset')]:
  guards.enter_context(patch.object(target,name,side_effect=AssertionError('forbidden '+name)))
 p=Path(sys.argv[1])
 records=loader._load_replay(str(p),replay_dir=p.parent,trajectories_path=p.parent/'unused',format_name=sys.argv[2])['protocol_log']
sys.stdout.buffer.write(json.dumps(records,ensure_ascii=False).encode('utf-8'))`;
  const child = spawnSync(process.env.PYTHON || 'D:\\Anaconda\\envs\\neuralgpu\\python.exe',
    ['-c', code, filename, fixture.format, path.join(root, 'trainer/src/neural/compare_action_rankers.py')], { env, timeout: 30000 });
  assert.equal(child.error, undefined);
  assert.equal(child.status, 0, child.stderr.toString('utf8'));
  const records = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(child.stdout));
  assert.equal(records.length, fixture.record_count);
  assert.ok(records[0].startsWith('|j|☆'));
  return records;
}
const actual = ledger.fixtures.map((fixture: any) => ({ fixture, records: load(fixture) }));
const id = (move: string) => move.toLowerCase().replace(/[^a-z0-9]/g, '');
const real = [
  { fixture: 0, reentry: 106, execution: 53, move: 'uturn', actor: 'p1a: Perrserker',
    switch: '|switch|p1a: Perrserker|Perrserker, L89, F|269/269',
    line: '|move|p1a: Perrserker|U-turn|p2a: Dondozo' },
  { fixture: 0, reentry: 243, execution: 128, move: 'uturn', actor: 'p1a: Perrserker',
    switch: '|switch|p1a: Perrserker|Perrserker, L89, F|225/269',
    line: '|move|p1a: Perrserker|U-turn|p2a: Cinccino' },
  { fixture: 1, reentry: 119, execution: 45, move: 'icebeam', actor: 'p1a: Kyurem',
    switch: '|switch|p1a: Kyurem|Kyurem|100/100',
    line: '|move|p1a: Kyurem|Ice Beam|p2a: Ting-Lu' },
];

test('current behavior: literal real executions and reentries lose flat revelations for both owners', () => {
  for (const example of real) {
    const { fixture, records } = actual[example.fixture];
    assert.equal(records[example.execution], example.line);
    assert.equal(records[example.reentry], example.switch);
    for (const owner of ['p1','p2'] as PlayerID[]) {
      const team = owner === 'p1' ? 'self_team' : 'opponent_team';
      const beforeExecution = importReplayPrefix(records, example.execution, ctx(owner, fixture.format));
      const afterExecution = importReplayPrefix(records, example.execution + 1, ctx(owner, fixture.format));
      assert.ok(!beforeExecution.view[team].find(p => p.active)!.revealed_moves.map(id).includes(example.move));
      assert.ok(afterExecution.view[team].find(p => p.active)!.revealed_moves.map(id).includes(example.move));
      const before = importReplayPrefix(records, example.reentry, ctx(owner, fixture.format));
      const after = importReplayPrefix(records, example.reentry + 1, ctx(owner, fixture.format));
      // Text lookup characterizes the existing flat view, never certifies a carrier.
      const prior = before.view[team].find(p => p.ident === example.actor)!;
      const current = after.view[team].find(p => p.active)!;
      assert.ok(prior.revealed_moves.map(id).includes(example.move));
      assert.deepEqual(current.revealed_moves, []);
      assert.equal(current.ident, example.actor);
      assert.equal(before.view.turn, after.view.turn);
      assert.equal(after.source_to_routed[example.reentry], after.protocol_prefix.length - 1);
      assert.equal(after.routed_to_source.at(-1), example.reentry);
      assert.ok(after.protocol_prefix.includes(example.line));
      assert.deepEqual(importReplayPrefix(records, example.reentry + 1, ctx(owner, fixture.format)), after);
      const changedSuffix = [...records.slice(0, example.reentry + 1), '|move|p2a: Future|Secret|p1a: Future',
        '|win|future', '|unknown|future', 42 as any];
      assert.deepEqual(importReplayPrefix(changedSuffix, example.reentry + 1, ctx(owner, fixture.format)), after);
      evidence.push({ layer: 'current-behavior', fixture: fixture.key, owner, execution_index: example.execution,
        execution_cursors: [example.execution, example.execution + 1], reentry_index: example.reentry,
        reentry_cursors: [example.reentry, example.reentry + 1], literal_execution: example.line,
        literal_reentry: example.switch, before_revealed: prior.revealed_moves, after_revealed: current.revealed_moves,
        raw_history_retained: true, chronological_carrier_relation: 'unproved',
        requirement: 'retain appearance-qualified historical execution; do not blindly merge into current appearance' });
    }
  }
});

type Event = { index: number; side: PlayerID; kind: 'switch' | 'move' | 'replace' | 'transform' | 'wait';
  text: string; move?: string; mode?: 'direct' | 'called' | 'acquired' };
type HeldBinding = { origin: string; owner: PlayerID; cursor: number; appearance: string;
  roster: string; basis: 'addressed-request'; prefix: readonly string[]; moves: readonly string[] };

// An independent design canary over literal examples, not a parser/validator or authority registry.
function model(events: readonly Event[], cursor: number, viewer: PlayerID, held: readonly HeldBinding[] = []) {
  const appearances: { subject: string; side: PlayerID; index: number; display: string; replaced: boolean; transformed: boolean }[] = [];
  const active: Partial<Record<PlayerID, string>> = {};
  const counts = { p1: 0, p2: 0 };
  const executions: { index: number; appearance: string; move: string; context: string; carrier: string | null }[] = [];
  let waiting = false;
  const selected = events.filter(e => e.index < cursor);
  for (const event of selected) {
    if (event.kind === 'switch') {
      const subject = `${event.side}:appearance:${++counts[event.side]}`;
      appearances.push({ subject, side: event.side, index: event.index, display: event.text, replaced: false, transformed: false });
      active[event.side] = subject;
    } else if (event.kind === 'wait') waiting = true;
    else {
      const appearance = appearances.find(a => a.subject === active[event.side]);
      assert.ok(appearance, 'Literal example requires a preceding appearance.');
      if (event.kind === 'replace') { appearance.replaced = true; appearance.display = event.text; }
      if (event.kind === 'transform') appearance.transformed = true;
      if (event.kind === 'move') executions.push({ index: event.index, appearance: appearance.subject,
        move: event.move!, context: appearance.transformed ? 'transformed' : event.mode || 'direct', carrier: null });
    }
  }
  const admitted = held.filter(binding => binding.origin === 'prompt20-model' && binding.owner === viewer
    && binding.cursor <= cursor && binding.basis === 'addressed-request'
    && JSON.stringify(binding.prefix) === JSON.stringify(events.filter(e => e.index < binding.cursor).map(e => e.text))
    && appearances.some(a => a.subject === binding.appearance && a.side === viewer && a.index < binding.cursor));
  assert.ok(admitted.every(b => b.roster.startsWith(`${viewer}:roster:`)), 'Foreign roster binding.');
  for (const binding of admitted) assert.ok(!admitted.some(other => other.appearance === binding.appearance
    && other.roster !== binding.roster), 'Conflicting held crosswalk.');
  for (const execution of executions) {
    const binding = admitted.find(b => b.appearance === execution.appearance);
    if (binding && execution.index + 1 >= binding.cursor) execution.carrier = binding.roster;
  }
  const latest = admitted.at(-1);
  const request = latest && latest.cursor === cursor && latest.appearance === active[viewer] && !waiting
    ? { owner: viewer, moves: [...latest.moves], freshness: 'fresh-addressed-fixture' } : null;
  return { appearances, active, executions, roster_knowledge: admitted.map(b => ({ appearance: b.appearance, roster: b.roster })),
    current_move_inventory: request, executable: null, starting_originals: null, PP: null, legal_actions: null };
}
const event = (index: number, kind: Event['kind'], text: string, move?: string, mode?: Event['mode']): Event =>
  ({ index, side: 'p1', kind, text, move, mode });

test('model requirements: duplicate species/name/position never bind a fresh carrier; execution history survives', () => {
  const rows = [event(0,'switch','|switch|p1a: Twin|Pikachu, L80|100/100'),
    event(1,'move','|move|p1a: Twin|Thunderbolt|p2a: Target','Thunderbolt'),
    event(2,'switch','|switch|p1a: Other|Eevee, L80|100/100'),
    event(3,'switch','|switch|p1a: Twin|Pikachu, L80|100/100'),
    event(4,'move','|move|p1a: Twin|Thunderbolt|p2a: Target','Thunderbolt')];
  for (const owner of ['p1','p2'] as PlayerID[]) {
    const before = model(rows, 3, owner), after = model(rows, 4, owner), repeated = model(rows, 5, owner);
    assert.deepEqual(after.executions, [{ index: 1, appearance: 'p1:appearance:1', move: 'Thunderbolt', context: 'direct', carrier: null }]);
    assert.equal(after.active.p1, 'p1:appearance:3');
    assert.deepEqual(before.executions, after.executions);
    assert.equal(repeated.executions.length, 2);
    assert.deepEqual(repeated.executions.map(e => e.index), [1,4]);
    assert.deepEqual(repeated.executions.map(e => e.appearance), ['p1:appearance:1','p1:appearance:3']);
    assert.deepEqual(model([...rows,event(5,'move','future','Secret')],4,owner), after);
    assert.equal(after.executable, null); assert.equal(after.starting_originals, null);
  }
  evidence.push({ layer: 'model-requirements', case: 'duplicates/unknown-carrier', events: rows, result: model(rows,4,'p1'), authority: 'none' });
});

test('model requirements: Illusion replacement keeps execution with the imposter appearance, restoration separate', () => {
  const rows = [event(0,'switch','|switch|p1a: Mask|Pikachu, L80|100/100'),
    event(1,'move','|move|p1a: Mask|Thunderbolt|p2a: Target','Thunderbolt'),
    event(2,'switch','|switch|p1a: Other|Eevee, L80|100/100'),
    event(3,'switch','|switch|p1a: Mask|Pikachu, L80|100/100'),
    event(4,'move','|move|p1a: Mask|Night Daze|p2a: Target','Night Daze'),
    event(5,'replace','|replace|p1a: Fox|Zoroark, L80|100/100'),
    event(6,'switch','|switch|p1a: Mask|Pikachu, L80|100/100')];
  for (const owner of ['p1','p2'] as PlayerID[]) {
    const proof = model(rows,6,owner);
    assert.deepEqual(proof.executions.map(e => [e.appearance,e.move,e.carrier]),
      [['p1:appearance:1','Thunderbolt',null],['p1:appearance:3','Night Daze',null]]);
    assert.equal(proof.appearances[2].replaced,true);
    const restored = model(rows,7,owner);
    assert.equal(restored.active.p1,'p1:appearance:4');
    assert.deepEqual(restored.executions,proof.executions);
    assert.equal(restored.starting_originals,null);
  }
  evidence.push({ layer: 'model-requirements', case: 'illusion/replace/restoration', events: rows, result: model(rows,7,'p1'), authority: 'replace discloses this stint, not a roster crosswalk' });
});

test('current behavior: fresh duplicate display, Illusion replacement and later restoration keep separate move arrays', () => {
  const rows = ['|switch|p1a: Mask|Pikachu, L80|100/100',
    '|move|p1a: Mask|Thunderbolt|p2a: Target','|switch|p1a: Other|Eevee, L80|100/100',
    '|switch|p1a: Mask|Pikachu, L80|100/100','|move|p1a: Mask|Night Daze|p2a: Target',
    '|replace|p1a: Fox|Zoroark, L80|100/100','|switch|p1a: Mask|Pikachu, L80|100/100'];
  for (const owner of ['p1','p2'] as PlayerID[]) {
    const team = owner === 'p1' ? 'self_team' : 'opponent_team';
    assert.deepEqual(importReplayPrefix(rows,4,ctx(owner)).view[team].find(p => p.active)!.revealed_moves,[]);
    const replaced = importReplayPrefix(rows,6,ctx(owner)).view[team];
    assert.ok(replaced.find(p => p.ident === 'p1a: Mask')!.revealed_moves.map(id).includes('thunderbolt'));
    assert.deepEqual(replaced.find(p => p.active)!.revealed_moves.map(id),['nightdaze']);
    const restored = importReplayPrefix(rows,7,ctx(owner)).view[team];
    assert.deepEqual(restored.find(p => p.active)!.revealed_moves,[]);
    assert.deepEqual(restored.find(p => p.ident === 'p1a: Fox')!.revealed_moves.map(id),['nightdaze']);
    evidence.push({layer:'current-behavior',case:'illusion/duplicate/restoration',owner,events:rows,
      requirement:'Display arrays are not immutable carrier proof; history remains separate.'});
  }
});

test('current behavior: unchanged stint retains execution; called and transformed executions enter flat own moves', () => {
  const rows = ['|switch|p1a: Ditto|Ditto, L80|100/100',
    '|switch|p2a: Garchomp|Garchomp, L80|100/100',
    '|move|p1a: Ditto|Transform|p2a: Garchomp', '|-transform|p1a: Ditto|p2a: Garchomp',
    '|move|p1a: Ditto|Earthquake|p2a: Garchomp', '|turn|1',
    '|switch|p1a: Bench|Pikachu, L80|100/100',
    '|switch|p1a: Ditto|Ditto, L80|100/100',
    '|move|p1a: Ditto|Thunderbolt|p2a: Garchomp|[from] move: Sleep Talk'];
  for (const owner of ['p1','p2'] as PlayerID[]) {
    const team = owner === 'p1' ? 'self_team' : 'opponent_team';
    const at3 = importReplayPrefix(rows,3,ctx(owner)), at4 = importReplayPrefix(rows,4,ctx(owner));
    assert.deepEqual(at3.view[team][0].revealed_moves,at4.view[team][0].revealed_moves);
    const transformed = importReplayPrefix(rows,6,ctx(owner)).view[team][0];
    assert.equal(transformed.transformed,true);
    assert.deepEqual(transformed.revealed_moves.map(id),['transform','earthquake']);
    const reset = importReplayPrefix(rows,8,ctx(owner)).view[team][0];
    assert.equal(reset.transformed,false); assert.deepEqual(reset.revealed_moves,[]);
    const called = importReplayPrefix(rows,9,ctx(owner)).view[team][0];
    assert.deepEqual(called.revealed_moves.map(id),['thunderbolt']);
    if (owner === 'p1') assert.deepEqual(called.moves,['thunderbolt']);
    evidence.push({layer:'current-behavior',case:'unchanged/transform/called',owner,
      events:rows,called_moves:called.moves,called_revealed:called.revealed_moves,
      requirement:'Execution is not selectability or original membership; unchanged-stint retention alone is source-proved.'});
  }
});

test('model requirements: unchanged public appearance, Transform/called/acquired moves do not become originals or legal actions', () => {
  const rows = [event(0,'switch','|switch|p1a: Ditto|Ditto, L80|100/100'),
    event(1,'move','|move|p1a: Ditto|Transform|p2a: Target','Transform'),
    event(2,'transform','|-transform|p1a: Ditto|p2a: Target'),
    event(3,'move','|move|p1a: Ditto|Earthquake|p2a: Target','Earthquake'),
    event(4,'switch','|switch|p1a: Bench|Pikachu, L80|100/100'),
    event(5,'switch','|switch|p1a: Ditto|Ditto, L80|100/100'),
    event(6,'move','|move|p1a: Ditto|Thunderbolt|p2a: Target|[from] move: Sleep Talk','Thunderbolt','called'),
    event(7,'move','|move|p1a: Ditto|Ice Beam|p2a: Target','Ice Beam','acquired')];
  for (const owner of ['p1','p2'] as PlayerID[]) {
    const unchanged = model(rows,2,owner), transformed = model(rows,4,owner), restored = model(rows,8,owner);
    assert.equal(unchanged.active.p1, 'p1:appearance:1');
    assert.deepEqual(transformed.executions.map(e => e.context),['direct','transformed']);
    assert.deepEqual(restored.executions.map(e => e.context),['direct','transformed','called','acquired']);
    assert.equal(restored.appearances[2].transformed,false);
    assert.equal(restored.PP,null); assert.equal(restored.legal_actions,null);
    assert.equal(restored.executable,null); assert.equal(restored.starting_originals,null);
    assert.deepEqual(model(rows,4,owner),transformed);
    assert.ok(transformed.executions.every(e => e.carrier === null));
  }
  evidence.push({ layer: 'model-requirements', case: 'transform/called/acquired', events: rows, result: model(rows,8,'p1'),
    note: 'Acquired mode is independently stipulated; a bare move line alone cannot reveal acquisition. Current selectability/originals stay unknown.' });
});

test('current behavior: pinned Mimic is unsupported; admitted Sketch activation does not distinguish acquisition in flat moves', () => {
  const prefix = ['|switch|p1a: Artist|Smeargle, L80|100/100',
    '|switch|p2a: Target|Pikachu, L80|100/100',
    '|move|p2a: Target|Thunderbolt|p1a: Artist', '|move|p1a: Artist|Sketch|p2a: Target'];
  const acquisition = '|-activate|p1a: Artist|move: Sketch|Thunderbolt';
  const rows = [...prefix,acquisition,'|move|p1a: Artist|Thunderbolt|p2a: Target',
    '|switch|p1a: Bench|Pikachu, L80|100/100',
    '|switch|p1a: Artist|Smeargle, L80|100/100'];
  for (const owner of ['p1','p2'] as PlayerID[]) {
    const team = owner === 'p1' ? 'self_team' : 'opponent_team';
    const acquired = importReplayPrefix(rows,6,ctx(owner)).view[team][0];
    assert.deepEqual(acquired.revealed_moves.map(id),['sketch','thunderbolt']);
    assert.deepEqual(importReplayPrefix(rows,8,ctx(owner)).view[team][0].revealed_moves,[]);
    const mimic = [...prefix.slice(0,3),'|move|p1a: Artist|Mimic|p2a: Target',
      '|-start|p1a: Artist|Mimic|Thunderbolt'];
    assert.throws(() => importReplayPrefix(mimic,5,ctx(owner)), (error: unknown) => {
      assert.ok(error instanceof ReplayImportError); assert.equal(error.source_index,4); return true;
    });
    evidence.push({layer:'current-behavior',case:'mimic/sketch',owner,source_backing:
      'pinned moves.ts Mimic12280-12293 temporary moveSlots; Sketch17198-17202 current/base slots',
      admitted_sketch_record:acquisition,mimic_rejection_index:4,
      acquired_revealed:acquired.revealed_moves,requirement:'Acquisition history persists without becoming starting-original membership; unsupported Mimic writer stays blocked.'});
  }
});

test('model requirements: held addressed crosswalk permits owner retention, never opposite-owner or replay private leakage', () => {
  const rows = [event(0,'switch','|switch|p1a: Twin|Pikachu, L80|100/100'),
    event(1,'move','|move|p1a: Twin|Thunderbolt|p2a: Target','Thunderbolt'),
    event(2,'switch','|switch|p1a: Other|Eevee, L80|100/100'),
    event(3,'switch','|switch|p1a: Twin|Pikachu, L80|100/100'),
    event(4,'move','|move|p1a: Twin|Thunderbolt|p2a: Target','Thunderbolt')];
  const binding = (appearance: string, cursor: number): HeldBinding => ({ origin:'prompt20-model', owner:'p1',
    cursor,appearance,roster:'p1:roster:1',basis:'addressed-request',prefix:rows.filter(e => e.index < cursor).map(e => e.text),moves:['Thunderbolt'] });
  const held = [binding('p1:appearance:1',1),binding('p1:appearance:3',4)];
  const owner = model(rows,4,'p1',held), opponent = model(rows,4,'p2',held);
  assert.equal(owner.executions[0].carrier,'p1:roster:1');
  assert.equal(owner.roster_knowledge[1].roster,'p1:roster:1');
  assert.deepEqual(owner.current_move_inventory,{ owner:'p1',moves:['Thunderbolt'],freshness:'fresh-addressed-fixture' });
  assert.equal(owner.executable,null);
  assert.equal(model(rows,5,'p1',held).current_move_inventory,null);
  assert.equal(opponent.executions[0].carrier,null);
  assert.deepEqual(opponent.roster_knowledge,[]); assert.equal(opponent.current_move_inventory,null);
  assert.deepEqual(model(rows,3,'p1',[held[1]]).roster_knowledge,[]);
  assert.deepEqual(model(rows,4,'p1',[{ ...held[0],origin:'foreign' }]).roster_knowledge,[]);
  assert.deepEqual(model(rows,4,'p1',[{ ...held[0],prefix:['wrong-prefix'] }]).roster_knowledge,[]);
  assert.throws(() => model(rows,4,'p1',[{...held[0],roster:'p2:roster:1'}]));
  assert.throws(() => model(rows,4,'p1',[held[0],{...held[0],roster:'p1:roster:2'}]));
  assert.equal(owner.starting_originals,null);
  const mirror = rows.map(e => ({ ...e,side:'p2' as PlayerID,
    text:e.text.replaceAll('p1a:','p2a:').replaceAll('p2a: Target','p1a: Target') }));
  const mirrorHeld: HeldBinding[] = held.map(b => ({...b,owner:'p2',appearance:b.appearance.replace('p1:','p2:'),
    roster:'p2:roster:2',prefix:mirror.filter(e => e.index < b.cursor).map(e => e.text)}));
  assert.equal(model(mirror,4,'p2',mirrorHeld).executions[0].carrier,'p2:roster:2');
  assert.equal(model(mirror,4,'p1',mirrorHeld).executions[0].carrier,null);
  assert.deepEqual(model(mirror,4,'p1',mirrorHeld).roster_knowledge,[]);
  evidence.push({ layer:'model-requirements',case:'held-owner-crosswalk',events:rows,held_fixture_bindings:held,
    owner,opponent,note:'Held registry is a stipulated independent model input, not an implemented source provider, trusted request or original-possession certificate.' });
});

test('current behavior: replay rejects private requests; correct and adversarially misdelivered legacy request controls', () => {
  assert.throws(() => importReplayPrefix(['|request|{}'],1,ctx('p1')));
  assert.throws(() => importReplayPrefix(['|request|{}'],1,ctx('p2')));
  const extractor = new PlayerStateExtractor('prompt20-request-control','gen9randombattle','p1');
  const request = { rqid:1, side:{ id:'p1',pokemon:[{ident:'p1: Twin',details:'Pikachu, L80',condition:'100/100',active:true,moves:['thunderbolt']}] },
    active:[{moves:[{move:'Thunderbolt',id:'thunderbolt',pp:0,maxpp:24,target:'normal',disabled:true}]}] };
  extractor.consumeChunk('|request|'+JSON.stringify(request));
  assert.equal((extractor.getOwnRequestData() as any).active[0].moves[0].pp,0);
  assert.equal((extractor.getOwnRequestData() as any).active[0].moves[0].disabled,true);
  assert.deepEqual(extractor.getView().self_team[0].moves,['thunderbolt']);
  assert.deepEqual(extractor.getView().opponent_team,[]);
  const foreign = new PlayerStateExtractor('prompt20-request-control','gen9randombattle','p2');
  foreign.consumeChunk('|request|'+JSON.stringify(request));
  assert.equal(foreign.getView().self_team[0].ident,'p1: Twin');
  evidence.push({layer:'current-behavior',case:'legacy-extractor-adversarial-request-misdelivery',
    delivered_side:'p1',extractor_owner:'p2',accepted_foreign_ident:foreign.getView().self_team[0].ident,
    requirement:'Trusted addressed-delivery binder must reject foreign owner before use; replay adapter already rejects all requests.'});
});

test('model requirements: an owner-only retrospective starting example cannot relabel public current history', () => {
  const rows = [event(0,'switch','|switch|p1a: Twin|Pikachu, L80|100/100'),
    event(1,'move','|move|p1a: Twin|Thunderbolt|p2a: Target','Thunderbolt')];
  // Independently stipulated complete original-possession proof, not inferred from execution.
  const startingFixture = {owner:'p1',policy:'public-replay-owner-starting/v1',subject:'p1:roster:1',
    starting_moves:['Thunderbolt'],observed_at:10,held_certificate:'fixture-only-complete-source-scan',
    starting_crosswalk:[{appearance:'p1:appearance:1',roster:'p1:roster:1'}]};
  for (const viewer of ['p1','p2'] as PlayerID[]) {
    const current = model(rows,2,viewer);
    const starting = viewer === 'p1' ? startingFixture : null;
    assert.equal(current.executions[0].carrier,null);
    assert.equal(current.executable,null); assert.equal(current.starting_originals,null);
    assert.ok(!JSON.stringify(current).includes(startingFixture.held_certificate));
    if (viewer === 'p2') assert.equal(starting,null);
    evidence.push({layer:'independent-example',case:'starting/current-separation',viewer,current,starting,
      note:'A stipulated privileged proof demonstrates layer separation only; no certificate verifier or source authority is implemented.'});
  }
});

test.after(() => {
  if (process.env.PROMPT20_REPORT) fs.writeFileSync(process.env.PROMPT20_REPORT,
    JSON.stringify({ scope:'design model and current behavior only; no runtime semantics adoption',evidence },null,2)+'\n','utf8');
});
