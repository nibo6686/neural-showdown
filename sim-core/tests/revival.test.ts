import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { normalizeRequest } from '../src/action_codec';
import { canonicalActionFromLegalAction, serializeCanonicalAction, deserializeCanonicalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { createPipelineIntegrationSession, classifyPipelineRequestState, projectPipelineProtocolPrefix, projectPipelineStepResult } from '../src/pipeline_integration';
import { continuePipelineEpisode } from '../src/pipeline_episode';
import { validateObservableProtocolPrefix } from '../src/observable_state';
import { assertRevivalSelection } from '../src/transition';
import type { PlayerID } from '../src/types';

const OPTIONS = { include_wait_requests: true, include_possible_roles: false };
const CONFIG = { battle_id: 'revival', format: 'gen9randombattle', seed: [1, 2, 3, 4] };
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;
function fixture(actor: PlayerID, healer = 'Pawmot') {
  const b = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const own = Teams.import(`First (Snorlax)
Ability: Immunity
- Explosion
- Splash

Second (Electrode)
Ability: Soundproof
- Explosion

Healer (${healer})
- Revival Blessing
- Splash

Healthy (Blissey)
- Splash
`)!;
  const other = Teams.import(`Watcher (Giratina)
Ability: Pressure
- Splash
- Will-O-Wisp

Reserve (Blissey)
- Splash
`)!;
  b.setPlayer('p1', { team: actor === 'p1' ? own : other });
  b.setPlayer('p2', { team: actor === 'p2' ? own : other });
  const turn = (a: string, o = 'move 1') => b.makeChoices(...(actor === 'p1' ? [a, o] : [o, a]) as [string, string]);
  turn('move 2', 'move 2'); // Public burn must be cleared by revival, including opponent view.
  turn('move 1'); b.choose(actor, 'switch 2');
  turn('move 1'); b.choose(actor, 'switch 3');
  turn('move 1');
  return b;
}
async function sessionsFrom(serialized: any, count = 2): Promise<Session[]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (o) { return this.resetFromSerialized(serialized, o); };
    const result: Session[] = [];
    for (let i = 0; i < count; i++) result.push(await createPipelineIntegrationSession(CONFIG));
    return result;
  } finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
}
function select(s: Session, actor: PlayerID, slot = 2) {
  const r = s.boundary.perspectives[actor].observation.request!;
  const a = r.legal_actions.actions.find(a => a?.slot === slot && a.kind === 'revive')!;
  assert.ok(a); return canonicalActionFromLegalAction(r, a.index);
}
function python(bundle: unknown) {
  return spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(bundle), encoding: 'utf8', env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
  });
}
for (const actor of ['p1', 'p2'] as const) {
  test(`real ${actor} revival preserves slots, privacy, restoration, actor records and resumed play`, async () => {
    const battle = fixture(actor); const serialized = structuredClone(battle.toJSON());
    const waiting = actor === 'p1' ? 'p2' : 'p1';
    assert.equal(battle.choose(actor, 'switch 4'), false); // Source rejects healthy target.
    assert.equal(battle.choose(actor, 'switch 2'), true);
    assert.equal(battle[actor].pokemon.find(p => p.name === 'First')!.status, '');
    battle.destroy();
    const [s, twin] = await sessionsFrom(serialized);
    const direct = new LocalBattleEnv('revival-direct', CONFIG.format, CONFIG.seed);
    try {
      const initial = await direct.resetFromSerialized(serialized, OPTIONS);
      const prefix = [...initial.log_delta];
      const before = s.boundary; const frozen = JSON.stringify(before);
      assert.equal(before.kind, 'one_sided_revival');
      assert.equal(classifyPipelineRequestState(before.perspectives[actor].observation), 'revival_selection');
      const req = before.perspectives[actor].observation.request!;
      assert.deepEqual(req.side.map(p => p.ident.split(': ')[1]), ['Healer', 'First', 'Second', 'Healthy']);
      assert.equal(req.side[0].reviving, true);
      for (const p of ['p1', 'p2'] as const) {
        const view = before.perspectives[p].observation.view;
        if (p !== actor) assert.equal(view.opponent_team.find(p => p.name === 'First')!.status, 'brn');
      }
      assert.deepEqual(req.legal_actions.actions.filter(Boolean).map(a => [a!.kind, a!.slot, a!.index]), [['revive', 2, 8], ['revive', 3, 9]]);
      assert.ok(!JSON.stringify(before.perspectives[waiting]).includes('reviving'));
      const action = select(s, actor);
      assert.equal(action.schema_version, 'canonical-revival/v1');
      assert.deepEqual(deserializeCanonicalAction(serializeCanonicalAction(action, req), req), action);
      const reordered = structuredClone(req);
      // Even if null rqid, legal index and wire slot recur, changed target ownership rejects.
      reordered.side[1].ident = 'p1: Different teammate';
      assert.throws(() => serializeCanonicalAction(action, reordered), /fingerprint is stale/);
      await assert.rejects(s.stepRevival({ ...action, switch_slot: 4, choice: 'switch 4' }), /Canonical/);
      await assert.rejects(s.stepRevival({ ...action, rqid: 123 }), /request ID/);
      assert.equal(s.boundary, before);
      // Candidate failure after a real simulator mutation still cannot publish/commit.
      const original = LocalBattleEnv.prototype.stepSeededForcedSwitch;
      try {
        LocalBattleEnv.prototype.stepSeededForcedSwitch = async function (r, o) { await original.call(this, r, o); throw new Error('injected candidate failure'); };
        await assert.rejects(s.stepRevival(action), /injected candidate failure/);
        assert.equal(s.boundary, before); assert.equal(JSON.stringify(before), frozen);
      } finally { LocalBattleEnv.prototype.stepSeededForcedSwitch = original; }
      const result = await s.stepRevival(action);
      const repeated = await twin.stepRevival(select(twin, actor));
      assert.deepEqual(result, repeated);
      assert.deepEqual(Object.keys(result.record_bundles), [actor]);
      assert.equal(result.record_bundles[actor]!.schema_version, 'pipeline-revival-record/v1');
      assert.equal(result.record_bundles[actor]!.transition.schema_version, 'pipeline-revival-reference/v1');
      const next = await direct.stepWithOptions({ [actor]: 'switch 2' }, OPTIONS); prefix.push(...next.log_delta);
      const projected = projectPipelineStepResult(next, CONFIG.battle_id, projectPipelineProtocolPrefix(prefix));
      for (const p of ['p1', 'p2'] as const) {
        const state = result.boundary.perspectives[p];
        assert.deepEqual(state.observation, projected[p]);
        assert.equal(state.belief.parent_belief_id, before.perspectives[p].belief.belief_id);
        assert.equal(state.belief.transition_lineage!.transition_id, result.transition_id);
        const team = p === actor ? state.observation.view.self_team : state.observation.view.opponent_team;
        const healed = team.find(p => p.name === 'First')!;
        assert.equal(healed.fainted, false); assert.equal(healed.status, null); assert.ok(healed.hp_ratio! > 0);
        assert.equal(team.find(p => p.name === 'Healer')!.active, true);
        assert.deepEqual(state.observation.protocol_prefix.slice(0, before.perspectives[p].observation.event_cursor), before.perspectives[p].observation.protocol_prefix);
      }
      assert.equal(JSON.stringify(before), frozen);
      const validated = python(result.record_bundles[actor]); assert.equal(validated.status, 0, validated.stderr);
      assert.equal(python(repeated.record_bundles[actor]).stdout, validated.stdout);
      const bad = structuredClone(result.record_bundles[actor]!); bad.schema_version = 'pipeline-forced-switch-record/v1';
      assert.notEqual(python(bad).status, 0);
      assert.equal(result.boundary.kind, 'joint_actionable');
      await assert.rejects(s.stepRevival(action), /unsupported-forced-switch-boundary/);
      assert.equal((await s.step()).transition_id, (await twin.step()).transition_id);
      // Restoring successor state reproduces both typed perspectives.
      const restored = new LocalBattleEnv('revival-restored', CONFIG.format, CONFIG.seed);
      try {
        const restoredResult = await restored.resetFromSerialized(direct.captureSeededSnapshot(null).simulator_state, OPTIONS);
        const restoredViews = projectPipelineStepResult(restoredResult, CONFIG.battle_id, projectPipelineProtocolPrefix(prefix));
        assert.deepEqual(restoredViews, projected);
      } finally { await restored.close(); }
    } finally { await s.close(); await twin.close(); await direct.close(); }
  });
  test(`runner progresses ${actor} Rabsca revival with committed-only records`, async () => {
    const b = fixture(actor, 'Rabsca'); const serialized = b.toJSON(); b.destroy();
    const [s] = await sessionsFrom(serialized, 1);
    const result = await continuePipelineEpisode(s, { limits: { max_transitions: 2 }, policy_id: 'revival-second-target/v1',
      action_order: observation => [...observation.request!.legal_actions.available_indices].reverse() });
    assert.equal(result.status, 'truncated'); assert.equal(result.counts.committed_transitions, 2);
    assert.equal(result.records[actor][0].schema_version, 'pipeline-revival-record/v1');
    assert.equal(result.records[actor][0].action.switch_slot, 3);
    assert.equal(result.records[actor][0].successor_observation.view.self_team.find(p => p.name === 'Second')!.fainted, false);
    assert.equal(result.records[actor].length, 2);
    assert.equal(result.records[actor === 'p1' ? 'p2' : 'p1'].length, 1);
    assert.equal(result.faithful_complete_episode, false);
  });
}
test('revival bench-heal grammar requires exact source evidence', () => {
  validateObservableProtocolPrefix(['|-heal|p1: First|50/100|[from] move: Revival Blessing'], 'p1');
  for (const line of ['|-heal|p1: First|50/100', '|-heal|p1: First|50/100|[from] move: Recover', '|-heal|p3: First|50/100|[from] move: Revival Blessing']) {
    assert.throws(() => validateObservableProtocolPrefix([line], 'p1'), /invalid pokemon/);
  }
});

test('runner explicitly truncates an unsupported live revival variant before attempting', async () => {
  const b = fixture('p1'); const data = structuredClone(b.toJSON()); b.destroy();
  const [session] = await sessionsFrom(data, 1);
  const getRequest = LocalBattleEnv.prototype.getRequest;
  try {
    LocalBattleEnv.prototype.getRequest = function (p) {
      const request = getRequest.call(this, p);
      if (request?.side.some(p => p.reviving)) request.side[0].condition = '0 fnt';
      return request;
    };
    const result = await continuePipelineEpisode(session);
    assert.equal(result.status, 'truncated');
    assert.equal(result.stop.code, 'episode/v1/unsupported-revival-blessing');
    assert.equal(result.counts.attempts, 0);
    assert.deepEqual(result.records, { p1: [], p2: [] });
  } finally { LocalBattleEnv.prototype.getRequest = getRequest; await session.close(); }
});

test('unsupported revival variants have no fabricated actions and fail scope validation', () => {
  const b = fixture('p1');
  try {
    const raw = structuredClone(b.p1.activeRequest);
    for (const change of [(r: any) => { r.forceSwitch = [true, true]; }, (r: any) => { r.side.pokemon[0].condition = '0 fnt'; }]) {
      const variant = structuredClone(raw); change(variant);
      const req = normalizeRequest('p1', variant);
      assert.deepEqual(req.legal_actions.available_indices, []);
      assert.throws(() => assertRevivalSelection(req), /unsupported-request/);
    }
  } finally { b.destroy(); }
});
