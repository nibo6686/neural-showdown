import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix, projectPipelineStepResult } from '../src/pipeline_integration';
import { SEEDED_FORCED_SWITCH_SCHEMA_VERSION, validateSeededForcedSwitchRequest, type SeededForcedSwitchRequest } from '../src/transition';
import type { PlayerID } from '../src/types';
import { lifecycleBattle, lifecycleChoices, prepareLifecycle, LIFECYCLE_SEED } from './helpers/state_lifecycle';

const OPTIONS = { include_wait_requests: true, include_possible_roles: false };
const KO_SEED = [101, 202, 303, 404];
const PIVOT_SEED = [11, 202, 303, 404];
const scenarios = [
  { name: 'ko', seed: KO_SEED, actor: 'p2' as const },
  { name: 'pivot', seed: PIVOT_SEED, actor: 'p1' as const },
];

for (const actor of ['p1', 'p2'] as const) {
  test(`real Shed Tail ${actor} matches uninterrupted state and publishes repeatable actor records and both beliefs`, async () => {
    const battle = lifecycleBattle(actor);
    prepareLifecycle(battle, actor, false);
    const serialized = battle.toJSON();
    const config = { battle_id: `shed-tail-${actor}`, format: 'gen9randombattle', seed: LIFECYCLE_SEED };
    const direct = new LocalBattleEnv('shed-tail-direct', config.format, config.seed);
    const reset = LocalBattleEnv.prototype.resetWithOptions;
    const sessions: Session[] = [];
    try {
      // Fixture seam only: all execution, serialization, protocol and publication
      // after setup use the unmodified simulator/environment/session paths.
      LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(serialized, options); };
      sessions.push(await createPipelineIntegrationSession(config));
      sessions.push(await createPipelineIntegrationSession(config));
    } finally {
      LocalBattleEnv.prototype.resetWithOptions = reset;
      battle.destroy();
    }
    try {
      const [session, twin] = sessions;
      const select = (s: Session, p: PlayerID, choice: string) => {
        const request = s.boundary.perspectives[p].observation.request!;
        const action = request.legal_actions.actions.find((a) => a?.choice === choice)!;
        assert.ok(action); return canonicalActionFromLegalAction(request, action.index);
      };
      const start = await direct.resetFromSerialized(serialized, OPTIONS);
      const prefix = [...start.log_delta];
      const choices = lifecycleChoices(actor, 'move 3');
      for (const s of sessions) await s.step({ p1: select(s, 'p1', choices.p1), p2: select(s, 'p2', choices.p2) });
      const pending = await direct.stepWithOptions(choices, OPTIONS); prefix.push(...pending.log_delta);
      const pendingObservations = projectPipelineStepResult(pending, config.battle_id, projectPipelineProtocolPrefix(prefix));
      const prior = session.boundary;
      for (const p of ['p1', 'p2'] as const) assert.deepEqual(prior.perspectives[p].observation, pendingObservations[p]);
      const committed = await session.stepForcedSwitch(select(session, actor, 'switch 2'));
      const repeated = await twin.stepForcedSwitch(select(twin, actor, 'switch 2'));
      const next = await direct.stepWithOptions({ [actor]: 'switch 2' }, OPTIONS); prefix.push(...next.log_delta);
      const observations = projectPipelineStepResult(next, config.battle_id, projectPipelineProtocolPrefix(prefix));
      assert.deepEqual(committed.record_bundles, repeated.record_bundles);
      assert.deepEqual(Object.keys(committed.record_bundles), [actor]);
      assert.equal(committed.transition_id, repeated.transition_id);
      for (const p of ['p1', 'p2'] as const) {
        const state = committed.boundary.perspectives[p];
        assert.deepEqual(state.observation, observations[p]);
        assert.deepEqual(state.belief, repeated.boundary.perspectives[p].belief);
        assert.equal(state.belief.observation.observation_id, observations[p].observation_id);
        assert.equal(state.belief.observation.event_cursor, observations[p].event_cursor);
        assert.equal(state.belief.parent_belief_id, prior.perspectives[p].belief.belief_id);
        assert.equal(state.belief.transition_lineage?.transition_id, committed.transition_id);
        assert.deepEqual(state.observation.protocol_prefix.slice(0, prior.perspectives[p].observation.event_cursor), prior.perspectives[p].observation.protocol_prefix);
        const team = p === actor ? state.observation.view.self_team : state.observation.view.opponent_team;
        assert.deepEqual(team.find((pokemon) => pokemon.name === 'Receiver')!.volatiles, ['substitute']);
        assert.deepEqual(team.find((pokemon) => pokemon.name === 'Donor')!.volatiles, []);
        assert.ok(state.observation.protocol_prefix.every((line) => !line.includes('|request|')));
      }
      assert.equal(validateInPython(committed.record_bundles[actor]).status, 0);
      // Re-enter the accepted joint path; restored candidates must retain the copy.
      const resumed = await session.step();
      const resumedTwin = await twin.step();
      assert.equal(resumed.transition_id, resumedTwin.transition_id);
      assert.deepEqual(resumed.boundary.perspectives[actor].observation.view.self_team[0].volatiles, ['substitute']);
    } finally {
      await direct.close();
      for (const session of sessions) await session.close();
    }
  });
}

function validateInPython(bundle: unknown) {
  return spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(bundle), encoding: 'utf8',
    env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
  });
}

type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;
function switchAction(session: Session, actor: PlayerID) {
  const request = session.boundary.perspectives[actor].observation.request!;
  return canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0]);
}
async function arrange(session: Session, name: string) {
  if (name === 'pivot') {
    const p1 = session.boundary.perspectives.p1.observation.request!;
    const p2 = session.boundary.perspectives.p2.observation.request!;
    const pivot = p1.legal_actions.actions.find((a) => a?.choice === 'move 4')!;
    assert.equal(pivot.move, 'U-turn');
    const switchIn = p2.legal_actions.actions.find((a) => a?.choice === 'switch 2')!;
    await session.step({ p1: canonicalActionFromLegalAction(p1, pivot.index), p2: canonicalActionFromLegalAction(p2, switchIn.index) });
  } else {
    for (let i = 0; i < 20 && session.boundary.kind === 'joint_actionable'; i++) await session.step();
  }
  assert.equal(session.boundary.kind, 'one_sided_forced_switch');
}

for (const scenario of scenarios) {
  test(`real ${scenario.name} forced switch publishes one deterministic actor record and both successor beliefs`, async () => {
    const config = { battle_id: `forced-${scenario.name}`, format: 'gen9randombattle', seed: scenario.seed };
    const session = await createPipelineIntegrationSession(config);
    const twin = await createPipelineIntegrationSession(config);
    try {
      await arrange(session, scenario.name);
      await arrange(twin, scenario.name);
      const actor = scenario.actor;
      const waiting = actor === 'p1' ? 'p2' : 'p1';
      const before = session.boundary;
      assert.equal(before.perspectives[actor].observation.request?.force_switch, true);
      assert.equal(before.perspectives[waiting].observation.request?.wait, true);
      if (scenario.name === 'ko') assert.ok(before.perspectives[actor].observation.protocol_prefix.some((line) => line.startsWith('|faint|')));
      // Legacy entry point still fails closed; waiting players never get a fabricated action.
      await assert.rejects(session.step(), /unsupported-one-sided-forced-switch/);
      const action = switchAction(session, actor);
      await assert.rejects(session.stepForcedSwitch({ ...action, player: waiting }), /unsupported-forced-switch-boundary/);
      await assert.rejects(session.stepForcedSwitch({ ...action, rqid: 999 }), /request ID does not match/);
      await assert.rejects(session.stepForcedSwitch({ ...action, kind: 'default' }), /Canonical|switch/);
      assert.equal(session.boundary, before);
      const result = await session.stepForcedSwitch(action);
      const repeated = await twin.stepForcedSwitch(switchAction(twin, actor));
      assert.equal(result.acting_player, actor);
      assert.equal(result.waiting_player, waiting);
      assert.deepEqual(Object.keys(result.record_bundles), [actor]);
      assert.equal(result.record_bundles[waiting], undefined);
      assert.equal(result.transition_id, repeated.transition_id);
      assert.equal(result.boundary.branch_id, repeated.boundary.branch_id);
      assert.equal(result.boundary.state_fingerprint, repeated.boundary.state_fingerprint);
      assert.equal(result.boundary.step_index, before.step_index + 1);
      for (const player of ['p1', 'p2'] as const) {
        const state = result.boundary.perspectives[player];
        const prior = before.perspectives[player];
        assert.equal(state.observation.observation_id, repeated.boundary.perspectives[player].observation.observation_id);
        assert.equal(state.belief.belief_id, repeated.boundary.perspectives[player].belief.belief_id);
        assert.equal(state.belief.parent_belief_id, prior.belief.belief_id);
        assert.equal(state.belief.transition_lineage?.transition_id, result.transition_id);
        assert.equal(state.belief.transition_lineage?.input_observation_id, prior.observation.observation_id);
        assert.equal(state.belief.transition_lineage?.output_observation_id, state.observation.observation_id);
        assert.deepEqual(state.observation.protocol_prefix.slice(0, prior.observation.event_cursor), prior.observation.protocol_prefix);
        assert.ok(state.observation.event_cursor > prior.observation.event_cursor);
        assert.ok(state.observation.protocol_prefix.every((line) => !line.startsWith('|request|')));
        assert.equal(state.observation.request?.player, player);
      }
      const bundle = result.record_bundles[actor]!;
      assert.equal(bundle.schema_version, 'pipeline-forced-switch-record/v1');
      assert.equal(bundle.transition.schema_version, 'pipeline-forced-switch-reference/v1');
      assert.equal(bundle.transition.acting_player, actor);
      assert.equal(bundle.transition.waiting_player, waiting);
      assert.equal(bundle.perspective, actor);
      const python = validateInPython(bundle);
      assert.equal(python.status, 0, python.stderr);
      const record = JSON.parse(python.stdout);
      assert.equal(record.perspective, actor);
      assert.equal(record.action_id, action.action_id);
      assert.equal(record.transition_id, result.transition_id);
      assert.equal(record.schema_fingerprints.transition, SEEDED_FORCED_SWITCH_SCHEMA_VERSION);
      const twinPython = validateInPython(repeated.record_bundles[actor]);
      assert.equal(twinPython.status, 0, twinPython.stderr);
      assert.equal(JSON.parse(twinPython.stdout).record_id, record.record_id);
      const injectedPrivate = { ...bundle, waiting_observation: before.perspectives[waiting].observation };
      assert.notEqual(validateInPython(injectedPrivate).status, 0);
      assert.notEqual(validateInPython({ ...bundle, transition: { ...bundle.transition, acting_player: waiting } }).status, 0);
      assert.equal(result.boundary.kind, 'joint_actionable');
      const continued = await session.step();
      const twinContinued = await twin.step();
      assert.equal(continued.transition_id, twinContinued.transition_id);
      for (const player of ['p1', 'p2'] as const) {
        assert.equal(continued.record_bundles[player].schema_version, 'pipeline-linked-record/v1');
        const validated = validateInPython(continued.record_bundles[player]);
        assert.equal(validated.status, 0, validated.stderr);
      }
    } finally {
      await session.close();
      await twin.close();
    }
  });
}

test('post-execution rejection and malformed projection discard forced-switch candidates completely', async () => {
  const config = { battle_id: 'forced-rollback', format: 'gen9randombattle', seed: KO_SEED };
  const session = await createPipelineIntegrationSession(config);
  const control = await createPipelineIntegrationSession(config);
  const original = LocalBattleEnv.prototype.stepSeededForcedSwitch;
  const diagnostics = LocalBattleEnv.prototype.diagnostics;
  try {
    await arrange(session, 'ko');
    await arrange(control, 'ko');
    const before = session.boundary;
    const serialized = JSON.stringify(before);
    LocalBattleEnv.prototype.diagnostics = function () {
      const base = diagnostics.call(this) as { players: Record<PlayerID, object> };
      return { ...base, players: { ...base.players, p2: { ...base.players.p2, last_choice_error: 'injected after execution' } } };
    };
    await assert.rejects(session.stepForcedSwitch(switchAction(session, 'p2')), /rejected-action/);
    LocalBattleEnv.prototype.diagnostics = diagnostics;
    assert.equal(session.boundary, before);
    assert.equal(JSON.stringify(session.boundary), serialized);
    LocalBattleEnv.prototype.stepSeededForcedSwitch = async function (request, options) {
      const result = await original.call(this, request, options);
      result.metadata.emitted_log_delta.push('|nothing|');
      return result;
    };
    await assert.rejects(session.stepForcedSwitch(switchAction(session, 'p2')), /unresolved-protocol-alias/);
    LocalBattleEnv.prototype.stepSeededForcedSwitch = original;
    assert.equal(session.boundary, before);
    assert.equal(JSON.stringify(session.boundary), serialized);
    LocalBattleEnv.prototype.stepSeededForcedSwitch = async function (request, options) {
      const result = await original.call(this, request, options);
      result.metadata.action_ids[request.waiting_player] = 'act-' + '0'.repeat(64);
      return result;
    };
    await assert.rejects(session.stepForcedSwitch(switchAction(session, 'p2')), /Forced-switch action_ids/);
    LocalBattleEnv.prototype.stepSeededForcedSwitch = original;
    assert.equal(session.boundary, before);
    assert.equal(JSON.stringify(session.boundary), serialized);
    const result = await session.stepForcedSwitch(switchAction(session, 'p2'));
    const expected = await control.stepForcedSwitch(switchAction(control, 'p2'));
    assert.equal(result.transition_id, expected.transition_id);
    assert.deepEqual(result.record_bundles, expected.record_bundles);
  } finally {
    LocalBattleEnv.prototype.stepSeededForcedSwitch = original;
    LocalBattleEnv.prototype.diagnostics = diagnostics;
    await session.close();
    await control.close();
  }
});

test('versioned preflight rejects malformed roles, waiting actions, stale requests and Revival Blessing before writes', async () => {
  const env = new LocalBattleEnv('forced-preflight', 'gen9randombattle', KO_SEED);
  try {
    let result = await env.resetWithOptions(OPTIONS);
    const log = [...result.log_delta];
    for (let i = 0; i < 20 && !result.requests.p1?.wait && !result.requests.p2?.wait; i++) {
      const actions = Object.fromEntries((['p1', 'p2'] as const).map((p) => {
        const r = result.requests[p]!;
        return [p, canonicalActionFromLegalAction(r, r.legal_actions.available_indices[0])];
      }));
      result = await env.stepWithCanonicalOptions(actions, OPTIONS);
      log.push(...result.log_delta);
    }
    const actor = 'p2';
    const r = result.requests[actor]!;
    const action = canonicalActionFromLegalAction(r, r.legal_actions.available_indices[0]);
    const snapshot = env.captureSeededSnapshot();
    const request: SeededForcedSwitchRequest = {
      schema_version: SEEDED_FORCED_SWITCH_SCHEMA_VERSION, snapshot,
      observations: projectPipelineStepResult(result, 'forced-preflight', projectPipelineProtocolPrefix(log)),
      actions: { [actor]: action }, acting_player: actor, waiting_player: 'p1', step_index: 4,
    };
    const invalid: SeededForcedSwitchRequest[] = [
      { ...request, waiting_player: actor },
      { ...request, actions: { p1: action, p2: action } },
      { ...request, actions: {} },
      { ...request, step_index: -1 },
      { ...request, observations: { ...request.observations, p1: { ...request.observations.p1, request: null } } },
      { ...request, snapshot: { ...snapshot, state_fingerprint: '0'.repeat(64) } },
    ];
    for (const bad of invalid) await assert.rejects(env.stepSeededForcedSwitch(bad, OPTIONS));
    // Same null-rqid boundary but a changed legal mask must fail against the live request.
    const stale = structuredClone(request);
    const extraIndex = stale.observations.p2.request!.legal_actions.available_indices.find((i) => i !== action.index)!;
    stale.observations.p2.request!.legal_actions.actions[extraIndex] = null;
    stale.observations.p2.request!.legal_actions.mask[extraIndex] = false;
    stale.observations.p2.request!.legal_actions.available_indices = stale.observations.p2.request!.legal_actions.available_indices.filter((i) => i !== extraIndex);
    await assert.rejects(env.stepSeededForcedSwitch(stale, OPTIONS), /live request mismatch/);
    assert.equal(env.captureSeededSnapshot().state_fingerprint, snapshot.state_fingerprint);
    // Source-shaped synthetic reviving flag; not presented as a natural revival regression.
    const originalGet = env.getRequest.bind(env);
    env.getRequest = (player) => {
      const live = originalGet(player);
      if (player === actor && live) live.raw = { side: { pokemon: [{ reviving: true }] } };
      return live;
    };
    await assert.rejects(env.stepSeededForcedSwitch(request, OPTIONS), /unsupported-revival-blessing/);
    env.getRequest = originalGet;
    assert.equal(env.captureSeededSnapshot().state_fingerprint, snapshot.state_fingerprint);
    assert.doesNotThrow(() => validateSeededForcedSwitchRequest(request));
    const accepted = await env.stepSeededForcedSwitch(request, OPTIONS);
    assert.deepEqual(Object.keys(accepted.metadata.action_ids), [actor]);
    assert.equal(accepted.metadata.schema_version, SEEDED_FORCED_SWITCH_SCHEMA_VERSION);
    assert.equal(accepted.metadata.parent_branch_id, snapshot.branch_id);
    assert.equal(accepted.output_snapshot.transition_id, accepted.metadata.transition_id);
    assert.equal(accepted.output_snapshot.branch_id, accepted.metadata.branch_id);
  } finally {
    await env.close();
  }
});

test('post-commit disposal failure does not masquerade as forced-switch rejection and is retried on close', async () => {
  const session = await createPipelineIntegrationSession({ battle_id: 'forced-cleanup', format: 'gen9randombattle', seed: KO_SEED });
  const original = LocalBattleEnv.prototype.close;
  let failed: LocalBattleEnv | null = null;
  let retried = false;
  try {
    await arrange(session, 'ko');
    LocalBattleEnv.prototype.close = async function () {
      if (!failed) {
        failed = this;
        throw new Error('injected disposal failure');
      }
      if (this === failed) retried = true;
      return original.call(this);
    };
    const result = await session.stepForcedSwitch(switchAction(session, 'p2'));
    assert.ok(failed);
    assert.equal(session.boundary, result.boundary);
    assert.deepEqual(Object.keys(result.record_bundles), ['p2']);
    await session.close();
    assert.equal(retried, true);
  } finally {
    LocalBattleEnv.prototype.close = original;
    await session.close();
    if (failed) await original.call(failed);
  }
});
