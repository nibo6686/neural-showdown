import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import {isEngineSeed, copyEngineSeed} from '../src/engine_seed';
import {PipelineIntegrationSession} from '../src/pipeline_integration';
const root = path.resolve(__dirname, '../../..');
const {replaySession, replayAction, parseReplay} = require(path.join(root, 'tools/replay_repro/replay_session.cjs'));
const {createKnowledgeDiff} = require(path.join(root, 'tools/replay_repro/knowledge_diff.cjs'));
const fixture = (id: string) => JSON.parse(fs.readFileSync(path.join(root, 'sim-core/tests/fixtures/replay-repro/gen9randombattle-' + id + '.json'), 'utf8'));

test('native seed strings preserve their PRNG algorithm and malformed strings fail closed', async () => {
  for (const value of ['sodium,' + 'ab'.repeat(16), 'gen5,' + 'ab'.repeat(8), [1, 2, 3, 4]]) {
    assert.ok(isEngineSeed(value)); assert.deepEqual(copyEngineSeed(value), value);
  }
  for (const value of ['sodium,1', 'sodium,' + 'z'.repeat(32), 'gen5,abcd', '', [1, 2, 3], new Array(4), null]) assert.equal(isEngineSeed(value), false);
  await assert.rejects(PipelineIntegrationSession.create({battle_id: 'bad-seed', format: 'gen9randombattle', seed: 'sodium,1'}), /invalid-seed/);
});

test('replay-born exact fixture retains addressed K and canonical human choices through forced switches', {timeout: 60000}, async () => {
  const result = await replaySession(fixture('2699590659'), {kdiff: true});
  assert.equal(result.born, true); assert.equal(result.kdiff.mismatches, 0);
  assert.equal(Object.keys(result.kdiff.rows).filter(key => result.kdiff.rows[key].checks > 0).length, 25);
  assert.ok(result.decisions.some((frames: any[]) => frames.some(f => f.observation.request?.force_switch)));
  for (const frames of result.decisions) for (const frame of frames) {
    assert.equal(frame.observation.perspective, frame.owner);
    assert.equal(frame.knowledge.projection.owner, frame.owner);
    for (const fact of [...frame.knowledge.projection.starting, ...frame.knowledge.projection.current]) assert.equal(fact.owner, frame.owner);
    if (frame.action) {
      const request = frame.observation.request;
      assert.equal(frame.action.player, frame.owner);
      assert.equal(request.legal_actions.actions[frame.action.index].choice, frame.action.choice);
    }
    assert.equal('simulator_state' in frame, false);
  }
});

test('replay-born forfeit validates the exact prefix without inventing a decision or terminal action', {timeout: 20000}, async () => {
  const result = await replaySession(fixture('2699618521'), {kdiff: true});
  assert.equal(result.ending, 'forfeit'); assert.equal(result.boundaries, 1);
  assert.equal(result.kdiff.mismatches, 0);
  assert.ok(result.decisions[0].every((frame: any) => frame.action === null));
});

test('replay-born completes the source-qualified pivot fixture with zero K differences', {timeout: 60000}, async () => {
  const result = await replaySession(fixture('2699617940'), {collect: false, kdiff: true});
  assert.equal(result.born, true); assert.equal(result.kdiff.mismatches, 0);
});

test('replay-born rejects nonmapping human choices, forbidden inputs and tampered public logs', {timeout: 20000}, async () => {
  const replay = fixture('2699590659');
  await assert.rejects(replaySession({...replay, inputlog: replay.inputlog.replace('>p1 move knockoff', '>p1 move invalidmove')}), /non-mapping-choice/);
  await assert.rejects(replaySession({...replay, inputlog: replay.inputlog + '\n>eval 1'}), /unsupported-input-command/);
  await assert.rejects(replaySession({...replay, log: replay.log.replace('|turn|1', '|turn|999')}), /public-log-diverged/);
  assert.throws(() => replayAction(null, 'move 1'), /non-mapping-choice/);
});

test('K oracle detects fabricated known and registry-unknown values while retaining honest unknowns', {timeout: 20000}, async () => {
  const {start, players} = parseReplay(fixture('2699618521')), recipients = {p1: {}, p2: {}};
  const session = await PipelineIntegrationSession.create({battle_id: 'oracle-controls', format: start.formatid,
    seed: start.seed, player_generation: players, knowledge_recipients: recipients});
  const frames = () => (['p1', 'p2'] as const).map(owner => ({owner, step_index: 0,
    knowledge: structuredClone(session.readOwnerKnowledge(session.getOwnerKnowledgeHandle(recipients[owner]), recipients[owner]))}));
  try {
    const clean = createKnowledgeDiff(session); clean.compare(session, frames()); assert.equal(clean.result().mismatches, 0);
    const unknown = frames(), hp = unknown[0].knowledge.projection.current.find((f: any) => f.property === 'hp');
    hp.state = 'unknown'; hp.value = null;
    const honest = createKnowledgeDiff(session); honest.compare(session, unknown); assert.equal(honest.result().mismatches, 0);
    hp.value = {type: 'integer', data: 1};
    const fabricated = createKnowledgeDiff(session); fabricated.compare(session, unknown); assert.equal(fabricated.result().mismatches, 1);
    const wrong = frames(); wrong[0].knowledge.projection.current.find((f: any) => f.property === 'hp').value.data++;
    const mismatch = createKnowledgeDiff(session); mismatch.compare(session, wrong); assert.equal(mismatch.result().mismatches, 1);
    const foreign = frames(); foreign[0].knowledge.projection.current.push({owner: 'p2', subject: 'p2:roster:1', family: 'K04',
      property: 'ball', state: 'known', value: {type: 'text', data: 'pokeball'}});
    const hidden = createKnowledgeDiff(session); hidden.compare(session, foreign); assert.equal(hidden.result().mismatches, 1);
  } finally {await session.close();}
});

test('born census workers record a divergent replay and continue with admitted fixtures', {timeout: 60000}, async () => {
  const os = await import('node:os'), {execFile} = await import('node:child_process'), {promisify} = await import('node:util');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'neural-born-census-'));
  const replay = fixture('2699618521');
  try {
    const entries = [replay, {...replay, id: 'gen9randombattle-tampered', log: replay.log.replace('|start', '|start|bad')}];
    for (const entry of entries) fs.writeFileSync(path.join(directory, entry.id + '.json'), JSON.stringify(entry));
    fs.writeFileSync(path.join(directory, 'admission.jsonl'), entries.map(entry => JSON.stringify({id: entry.id, admitted: true, turns: 0})).join('\n') + '\n');
    const result = await promisify(execFile)(process.execPath, ['tools/replay_repro/index.cjs', directory, '--born', '--kdiff', '--workers=2', '--update-admission'], {cwd: root, timeout: 50000});
    const summary = JSON.parse(result.stdout.trim());
    assert.equal(summary.replays, 2); assert.equal(summary.born, 1); assert.equal(summary.kdiff.mismatches, 0);
    assert.equal(summary.failures['replay/public-log-diverged'], 1);
    const rows = fs.readFileSync(path.join(directory, 'born-admission.jsonl'), 'utf8').trim().split('\n').map(line => JSON.parse(line));
    assert.equal(rows.length, 2); assert.equal(new Set(rows.map(row => row.id)).size, 2);
    assert.ok(rows.find(row => !row.born).reason);
    const admission = fs.readFileSync(path.join(directory,'admission.jsonl'),'utf8').trim().split('\n').map(line => JSON.parse(line));
    assert.equal(admission[0].born_session.complete,true);
    assert.equal(admission[0].born_session.kdiff_mismatches,0);
    assert.equal(admission[1].born_session.complete,false);
    assert.match(admission[1].born_session.reason,/public-log-diverged/);
    assert.ok(admission.every(row => row.admitted === true));
    const retained = fs.readFileSync(path.join(directory,'born-admission.jsonl'),'utf8');
    const resumed = await promisify(execFile)(process.execPath, ['tools/replay_repro/index.cjs', directory, '--born', '--kdiff', '--workers=2','--resume','--update-admission'], {cwd:root,timeout:10000});
    assert.equal(JSON.parse(resumed.stdout).replays,2);
    assert.equal(fs.readFileSync(path.join(directory,'born-admission.jsonl'),'utf8'),retained);
    const {writeBornAdmission} = require(path.join(root,'tools/replay_repro/born_census.cjs'));
    const originalAdmission = fs.readFileSync(path.join(directory,'admission.jsonl'),'utf8');
    assert.throws(() => writeBornAdmission(path.join(directory,'admission.jsonl'),[{id:'foreign',born:true}]),/Invalid born admission/);
    assert.equal(fs.readFileSync(path.join(directory,'admission.jsonl'),'utf8'),originalAdmission);
    fs.writeFileSync(path.join(directory,'admission.jsonl'),entries.map(entry => JSON.stringify({id:entry.id,admitted:true,turns:0})).join('\n')+'\n');
    writeBornAdmission(path.join(directory,'admission.jsonl'),[{id:entries[0].id,born:true}]);
    const partial = fs.readFileSync(path.join(directory,'admission.jsonl'),'utf8').trim().split('\n').map(line => JSON.parse(line));
    assert.equal(partial[0].born_session.kdiff_mismatches,null,'unmeasured is not zero');
    assert.equal('born_session' in partial[1],false,'unprocessed is not failed');
  } finally {fs.rmSync(directory, {recursive: true, force: true});}
});
