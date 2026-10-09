import { revivalBattle } from './slot_consequence_fixtures';
import { assertPublicConsequenceTamperMatrix } from './public_consequence_test_helpers';
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
import { PUBLIC_STAGES_SCHEMA_VERSION, validateObservableProtocolPrefix, type ObservableBattleState } from '../src/observable_state';
import { assertRevivalSelection } from '../src/transition';
import type { PlayerID } from '../src/types';

const OPTIONS = { include_wait_requests: true, include_possible_roles: false };
const CONFIG = { battle_id: 'revival', format: 'gen9randombattle', seed: [1, 2, 3, 4] };
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;
/**
 * Pinned `turnLoop` pauses as soon as the faster Pawmot creates its revival
 * request. Rabsca's already-queued Revival Blessing resumes only after that
 * owner consumes the request, producing the opposite-side request in turn.
 */
function sequentialFixture() {
  const b = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const p1 = Teams.import(`Lead (Snorlax)
Ability: Immunity
- Explosion

Pawmot
- Revival Blessing
- Splash

Reserve (Blissey)
- Splash
`)!;
  const p2 = Teams.import(`Watcher (Giratina)
Ability: Pressure
- Splash

Bomb (Electrode)
Ability: Soundproof
- Explosion

Rabsca
- Revival Blessing
- Splash

Reserve (Blissey)
- Splash
`)!;
  b.setPlayer('p1', { team: p1 });
  b.setPlayer('p2', { team: p2 });
  b.makeChoices('move 1', 'move 1'); // p1 Lead faints.
  b.choose('p1', 'switch 2'); // Pawmot enters.
  b.makeChoices('move 2', 'switch 2'); // p2 Bomb enters.
  b.makeChoices('move 2', 'move 1'); // p2 Bomb faints.
  b.choose('p2', 'switch 3'); // Rabsca enters.
  // Pawmot is faster. Its self-switch pauses this turn before Rabsca's
  // already-queued Revival Blessing action runs.
  b.makeChoices('move 1', 'move 1');
  return b;
}

/** Imposter copies the generated Pawmot move slot before the same owner-only selection. */
function copiedFixture() {
  const b = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const p1 = Teams.import(`Lead (Snorlax)
Ability: Immunity
- Memento

Copy (Ditto)
Ability: Imposter
- Transform

Reserve (Blissey)
- Splash
`)!;
  const p2 = Teams.import(`Pawmot
- Revival Blessing
- Splash

Reserve (Blissey)
- Splash
`)!;
  b.setPlayer('p1', { team: p1 });
  b.setPlayer('p2', { team: p2 });
  b.makeChoices('move 1', 'move 2'); // Memento leaves a fainted owner bench target.
  b.choose('p1', 'switch 2'); // Imposter copies Pawmot's currently selected slots.
  b.makeChoices('move 1', 'move 2');
  return b;
}

/** The queued opposing Memento ends the battle after the consumed revival request. */
function terminalFixture() {
  const b = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const p1 = Teams.import(`Lead (Snorlax)
Ability: Immunity
- Memento

Pawmot
- Revival Blessing
- Splash
`)!;
  const p2 = Teams.import(`Terminus (Snorlax)
Ability: Immunity
- Splash
- Memento
`)!;
  b.setPlayer('p1', { team: p1 });
  b.setPlayer('p2', { team: p2 });
  b.makeChoices('move 1', 'move 1'); // p1 Lead faints, p2 stays alive.
  b.choose('p1', 'switch 2');
  b.makeChoices('move 1', 'move 2'); // Pawmot pauses before queued p2 Memento.
  return b;
}
async function sessionsFrom(serialized: any, count = 2, v2 = false): Promise<Session[]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (o) { return this.resetFromSerialized(serialized, o); };
    const result: Session[] = [];
    for (let i = 0; i < count; i++) {
      result.push(await createPipelineIntegrationSession({
        ...CONFIG,
        ...(v2 ? { observation_schema_version: 'observable-battle-state/v2' as const } : {}),
      }));
    }
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
    const battle = revivalBattle(actor); const serialized = structuredClone(battle.toJSON());
    const waiting = actor === 'p1' ? 'p2' : 'p1';
    assert.equal(battle.choose(actor, 'switch 4'), false); // Source rejects healthy target.
    assert.equal(battle.choose(actor, 'switch 2'), true);
    assert.equal(battle[actor].pokemon.find(p => p.name === 'First')!.status, '');
    battle.destroy();
    const [s, twin] = await sessionsFrom(serialized, 2, true);
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
        // The preceding public faint boundary clears a major status. Revival
        // may restore HP, but has no status to restore from typed public state.
        if (p !== actor) assert.equal(view.opponent_team.find(p => p.name === 'First')!.status, null);
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
      const projected = projectPipelineStepResult(
        next, CONFIG.battle_id, projectPipelineProtocolPrefix(prefix), 'observable-battle-state/v2',
      );
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
      assertPublicConsequenceTamperMatrix(result.record_bundles[actor], 'First');
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
        const restoredViews = projectPipelineStepResult(
          restoredResult, CONFIG.battle_id, projectPipelineProtocolPrefix(prefix), 'observable-battle-state/v2',
        );
        assert.deepEqual(restoredViews, projected);
      } finally { await restored.close(); }
    } finally { await s.close(); await twin.close(); await direct.close(); }
  });
  test(`runner progresses ${actor} Rabsca revival with committed-only records`, async () => {
    const b = revivalBattle(actor, 'Rabsca'); const serialized = b.toJSON(); b.destroy();
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
  const b = revivalBattle('p1'); const data = structuredClone(b.toJSON()); b.destroy();
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
  const b = revivalBattle('p1');
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

test('source-shaped Imposter copy reaches the same bounded owner-only revival selection', async () => {
  const battle = copiedFixture();
  const serialized = structuredClone(battle.toJSON());
  battle.destroy();
  const [session, twin] = await sessionsFrom(serialized, 2, true);
  try {
    const before = session.boundary;
    assert.equal(before.kind, 'one_sided_revival');
    assert.equal(classifyPipelineRequestState(before.perspectives.p1.observation), 'revival_selection');
    assert.equal(classifyPipelineRequestState(before.perspectives.p2.observation), 'waiting');
    const request = before.perspectives.p1.observation.request!;
    assert.ok(request.side[0].reviving);
    assert.deepEqual(request.legal_actions.actions.filter(Boolean).map(action => [action!.kind, action!.slot]), [['revive', 2]]);
    const result = await session.stepRevival(select(session, 'p1'));
    const repeated = await twin.stepRevival(select(twin, 'p1'));
    assert.deepEqual(result, repeated);
    assert.equal(result.record_bundles.p1!.successor_observation.schema_version, 'observable-battle-state/v2');
    assert.equal(python(result.record_bundles.p1).status, 0);
    assert.equal(result.boundary.kind, 'joint_actionable');
  } finally {
    await session.close();
    await twin.close();
  }
});

test('queued opposing terminal action ends after a consumed revival selection without a fabricated request', async () => {
  const battle = terminalFixture();
  const serialized = structuredClone(battle.toJSON());
  battle.destroy();
  const [session, twin] = await sessionsFrom(serialized, 2, true);
  try {
    assert.equal(session.boundary.kind, 'one_sided_revival');
    const result = await session.stepRevival(select(session, 'p1'));
    const repeated = await twin.stepRevival(select(twin, 'p1'));
    assert.deepEqual(result, repeated);
    assert.equal(result.boundary.kind, 'terminal');
    for (const player of ['p1', 'p2'] as const) {
      assert.equal(result.boundary.perspectives[player].observation.view.terminated, true);
      assert.equal(result.boundary.perspectives[player].observation.request, null);
    }
    assert.equal(python(result.record_bundles.p1).status, 0);
  } finally {
    await session.close();
    await twin.close();
  }
});

test('CE-06B retains terminal evidence after one-sided progression with actor-only publication', async () => {
  const battle = terminalFixture();
  const serialized = structuredClone(battle.toJSON());
  battle.destroy();
  const originalReset = LocalBattleEnv.prototype.resetWithOptions;
  LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(serialized, options ?? OPTIONS); };
  let session: Session | undefined;
  try {
    session = await createPipelineIntegrationSession({ ...CONFIG, observation_schema_version: PUBLIC_STAGES_SCHEMA_VERSION });
  } finally {
    LocalBattleEnv.prototype.resetWithOptions = originalReset;
  }
  const result = await continuePipelineEpisode(session!);
  assert.equal(result.status, 'completed');
  assert.equal(result.evidence_envelope?.commits.length, 1);
  assert.deepEqual(result.evidence_envelope?.commits[0].actors, ['p1']);
  assert.equal(result.records.p1.length, 1);
  assert.equal(result.records.p2.length, 0, 'waiting side has no synthetic terminal decision row');
  assert.equal(result.evidence_envelope?.closure?.complete_capture, false, 'resumed source fixture has no predecessor to the initial requests');
  assert.equal(result.evidence_envelope?.closure?.origin_coverage, 'segment_only');
  assert.equal(result.evidence_envelope?.closure?.terminal?.outcome, 'win');
  for (const player of ['p1', 'p2'] as const) {
    const terminalObservation: ObservableBattleState = result.evidence_envelope!.commits[0].boundary.perspectives[player] as ObservableBattleState;
    assert.equal(terminalObservation.view.terminated, true);
    assert.equal(terminalObservation.request, null);
  }
  const publication = python(result);
  assert.equal(publication.status, 0, publication.stderr);
  assert.equal(JSON.parse(publication.stdout).length, 1);
});

test('real sequential opposite-side revival selections remain private, replayable, and resume ordinary play', async () => {
  const battle = sequentialFixture();
  const serialized = structuredClone(battle.toJSON());
  battle.destroy();
  const [session, twin] = await sessionsFrom(serialized, 2, true);
  try {
    const first = session.boundary;
    assert.equal(first.kind, 'one_sided_revival');
    assert.equal(classifyPipelineRequestState(first.perspectives.p1.observation), 'revival_selection');
    assert.equal(classifyPipelineRequestState(first.perspectives.p2.observation), 'waiting');
    assert.ok(first.perspectives.p1.observation.request!.side.some(p => p.reviving));
    assert.ok(!JSON.stringify(first.perspectives.p2.observation).includes('reviving'));
    assert.equal(first.perspectives.p2.observation.request!.player, 'p2');
    assert.ok(first.perspectives.p2.observation.request!.side.every(p => p.ident.startsWith('p2: ')));

    const firstAction = select(session, 'p1');
    await assert.rejects(session.stepRevival({ ...firstAction, player: 'p2' }), /unsupported-forced-switch-boundary/);
    assert.equal(session.boundary, first); // rejected candidate does not consume p1's request
    const firstResult = await session.stepRevival(firstAction);
    const firstTwin = await twin.stepRevival(select(twin, 'p1'));
    assert.deepEqual(firstResult, firstTwin);
    assert.equal(firstResult.boundary.kind, 'one_sided_revival');
    assert.deepEqual(Object.keys(firstResult.record_bundles), ['p1']);
    assert.equal(firstResult.record_bundles.p1!.successor_observation.schema_version, 'observable-battle-state/v2');
    assert.equal(python(firstResult.record_bundles.p1).status, 0);

    const second = session.boundary;
    assert.equal(classifyPipelineRequestState(second.perspectives.p1.observation), 'waiting');
    assert.equal(classifyPipelineRequestState(second.perspectives.p2.observation), 'revival_selection');
    assert.ok(second.perspectives.p2.observation.request!.side.some(p => p.reviving));
    assert.ok(!JSON.stringify(second.perspectives.p1.observation).includes('reviving'));
    assert.equal(second.perspectives.p1.observation.request!.player, 'p1');
    assert.ok(second.perspectives.p1.observation.request!.side.every(p => p.ident.startsWith('p1: ')));
    const secondAction = select(session, 'p2', 3);
    const secondResult = await session.stepRevival(secondAction);
    const secondTwin = await twin.stepRevival(select(twin, 'p2', 3));
    assert.deepEqual(secondResult, secondTwin);
    assert.deepEqual(Object.keys(secondResult.record_bundles), ['p2']);
    assert.equal(secondResult.record_bundles.p2!.successor_observation.schema_version, 'observable-battle-state/v2');
    assert.equal(python(secondResult.record_bundles.p2).status, 0);
    assert.equal(secondResult.boundary.kind, 'joint_actionable');

    // A serialized simulator after the consumed p1 request restores directly
    // into the p2-only selection and reaches the same committed successor.
    const afterFirst = sequentialFixture();
    assert.equal(afterFirst.choose('p1', 'switch 2'), true);
    const afterFirstSerialized = structuredClone(afterFirst.toJSON());
    afterFirst.destroy();
    const [restoredAfterFirst, restoredTwinAfterFirst] = await sessionsFrom(afterFirstSerialized, 2, true);
    try {
      assert.equal(classifyPipelineRequestState(restoredAfterFirst.boundary.perspectives.p1.observation), 'waiting');
      assert.equal(classifyPipelineRequestState(restoredAfterFirst.boundary.perspectives.p2.observation), 'revival_selection');
      const restoredSecond = await restoredAfterFirst.stepRevival(select(restoredAfterFirst, 'p2', 3));
      const restoredTwinSecond = await restoredTwinAfterFirst.stepRevival(select(restoredTwinAfterFirst, 'p2', 3));
      assert.deepEqual(restoredSecond, restoredTwinSecond);
      // Snapshot restoration begins a new lineage, but consumes the same p2
      // request into the same public successor state and canonical action.
      assert.deepEqual(restoredSecond.record_bundles.p2!.action, secondResult.record_bundles.p2!.action);
      for (const player of ['p1', 'p2'] as const) {
        assert.deepEqual(
          restoredSecond.boundary.perspectives[player].observation,
          secondResult.boundary.perspectives[player].observation,
        );
      }
    } finally {
      await restoredAfterFirst.close();
      await restoredTwinAfterFirst.close();
    }
    for (const player of ['p1', 'p2'] as const) {
      const view = secondResult.boundary.perspectives[player].observation.view;
      const own = view.self_team.find(mon => mon.name === (player === 'p1' ? 'Lead' : 'Bomb'))!;
      assert.equal(own.fainted, false);
      assert.equal(own.status, null);
      assert.ok(own.hp_ratio! > 0);
    }
    // The next ordinary joint request has no revived selection fields, and an
    // independently restored twin consumes the same request with the same ID.
    for (const player of ['p1', 'p2'] as const) {
      assert.equal(classifyPipelineRequestState(secondResult.boundary.perspectives[player].observation), 'actionable');
      assert.ok(!JSON.stringify(secondResult.boundary.perspectives[player].observation).includes('reviving'));
    }
    const ordinary = await session.step();
    const ordinaryTwin = await twin.step();
    assert.equal(ordinary.transition_id, ordinaryTwin.transition_id);
    assert.deepEqual(ordinary, ordinaryTwin);
  } finally {
    await session.close();
    await twin.close();
  }
});
