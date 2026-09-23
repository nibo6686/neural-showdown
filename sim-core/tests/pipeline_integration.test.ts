import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { canonicalActionFromLegalAction, type CanonicalAction } from '../src/canonical_action';
import { projectBeliefState, serializeBeliefState } from '../src/belief_state';
import { LocalBattleEnv } from '../src/env_manager';
import type { ObservableBattleState } from '../src/observable_state';
import {
  assertPipelineTransitionSupported,
  classifyPipelineBoundary,
  createPipelineIntegrationSession,
  PipelineIntegrationError,
  projectPipelineProtocolPrefix,
  projectPipelineStepResult,
} from '../src/pipeline_integration';
import type { ChoiceRequestView, PlayerID } from '../src/types';
import { toSeededSnapshotRef } from '../src/transition';

const SEED = [101, 202, 303, 404] as const;

function validateInPython(bundle: unknown) {
  const trainerSource = path.resolve(__dirname, '../../../trainer/src');
  const python = spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    cwd: path.resolve(__dirname, '../../..'),
    env: { ...process.env, PYTHONPATH: trainerSource },
    input: JSON.stringify(bundle),
    encoding: 'utf8',
  });
  return python;
}

function runFreshSimulatorProcess() {
  const modulePath = path.resolve(__dirname, '../src/pipeline_integration.js');
  const trainerSource = path.resolve(__dirname, '../../../trainer/src');
  const repositoryRoot = path.resolve(__dirname, '../../..');
  const childScript = [
    "const { spawnSync } = require('node:child_process');",
    `const api = require(${JSON.stringify(modulePath)});`,
    `const trainerSource = ${JSON.stringify(trainerSource)};`,
    `const repositoryRoot = ${JSON.stringify(repositoryRoot)};`,
    "(async () => {",
    "  const session = await api.createPipelineIntegrationSession({ battle_id: 'pipeline-smoke-v1', format: 'gen9randombattle', seed: [101,202,303,404] });",
    "  try {",
    "    const result = await session.step();",
    "    const records = {};",
    "    for (const player of ['p1','p2']) {",
    "      const checked = spawnSync(process.env.PYTHON || 'python3', ['-m','neural.pipeline_record'], { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: trainerSource }, input: JSON.stringify(result.record_bundles[player]), encoding: 'utf8' });",
    "      if (checked.status !== 0) throw new Error(checked.stderr || 'Python record validation failed');",
    "      records[player] = JSON.parse(checked.stdout).record_id;",
    "    }",
    "    process.stdout.write(JSON.stringify({ transition_id: result.transition_id, branch_id: result.boundary.branch_id, state_fingerprint: result.boundary.state_fingerprint, step_index: result.boundary.step_index, perspectives: Object.fromEntries(['p1','p2'].map((p) => [p, { observation_id: result.boundary.perspectives[p].observation.observation_id, belief_id: result.boundary.perspectives[p].belief.belief_id, action_id: result.record_bundles[p].action.action_id, record_id: records[p] }])) }));",
    "  } finally { await session.close(); }",
    "})().catch((error) => { process.stderr.write(error.stack || error.message); process.exitCode = 1; });",
  ].join('\n');
  return spawnSync(process.execPath, ['-e', childScript], {
    cwd: path.resolve(__dirname, '..'),
    env: { ...process.env, PYTHONPATH: trainerSource },
    encoding: 'utf8',
    maxBuffer: 1024 * 1024,
  });
}

function actionPair(session: Awaited<ReturnType<typeof createPipelineIntegrationSession>>): Record<PlayerID, CanonicalAction> {
  const actions = {} as Record<PlayerID, CanonicalAction>;
  for (const player of ['p1', 'p2'] as const) {
    const state = session.boundary.perspectives[player];
    const request = state.observation.request;
    assert.ok(request);
    assert.ok(state.observation.decision_availability.available);
    const currentRequest = request as unknown as ChoiceRequestView;
    actions[player] = canonicalActionFromLegalAction(
      currentRequest,
      currentRequest.legal_actions.available_indices[0],
    );
  }
  return actions;
}

test('PIPELINE-001 links two real transitions for both perspectives and validates records in fresh Python processes', async () => {
  const primary = await createPipelineIntegrationSession({ battle_id: 'pipeline-smoke-v1', format: 'gen9randombattle', seed: SEED });
  const mirror = await createPipelineIntegrationSession({ battle_id: 'pipeline-smoke-v1', format: 'gen9randombattle', seed: SEED });
  try {
    assert.equal(primary.boundary.kind, 'joint_actionable');
    assert.equal(primary.boundary.step_index, 0);
    for (const player of ['p1', 'p2'] as const) {
      assert.equal(primary.boundary.perspectives[player].observation.perspective, player);
      assert.equal(primary.boundary.perspectives[player].belief.observation.observation_id,
        primary.boundary.perspectives[player].observation.observation_id);
    }

    const first = await primary.step();
    const mirrorFirst = await mirror.step();
    assert.equal(first.transition_id, mirrorFirst.transition_id);
    assert.equal(first.boundary.state_fingerprint, mirrorFirst.boundary.state_fingerprint);
    assert.equal(first.boundary.branch_id, mirrorFirst.boundary.branch_id);
    assert.equal(first.boundary.step_index, 1);
    const localRecordIds = {} as Record<PlayerID, string>;
    for (const player of ['p1', 'p2'] as const) {
      const before = primary.boundary.perspectives[player];
      const twin = mirrorFirst.boundary.perspectives[player];
      assert.equal(before.observation.observation_id, twin.observation.observation_id);
      assert.equal(before.belief.belief_id, twin.belief.belief_id);
      assert.equal(before.belief.parent_belief_id, first.record_bundles[player].input_belief.belief_id);
      assert.equal(before.belief.transition_lineage?.input_observation_id,
        first.record_bundles[player].input_observation.observation_id);
      assert.equal(before.belief.transition_lineage?.output_observation_id, before.observation.observation_id);
      assert.equal(before.belief.simulator_snapshot?.branch_id, first.boundary.branch_id);
      const predecessorPrefix = first.record_bundles[player].input_observation.protocol_prefix;
      assert.deepEqual(before.observation.protocol_prefix.slice(0, predecessorPrefix.length), predecessorPrefix);

      const validated = validateInPython(first.record_bundles[player]);
      assert.equal(validated.status, 0, validated.stderr);
      const record = JSON.parse(validated.stdout);
      assert.equal(record.schema_version, 'dataset-record/v1');
      assert.equal(record.perspective, player);
      assert.equal(record.observation_id, first.record_bundles[player].input_observation.observation_id);
      assert.equal(record.action_id, first.record_bundles[player].action.action_id);
      assert.equal(record.transition_id, first.transition_id);
      assert.deepEqual(record.input_fields, []);
      assert.match(record.schema_fingerprints.feature, /^features-not-produced\/v1:/);
      localRecordIds[player] = record.record_id;
    }

    const freshProcess = runFreshSimulatorProcess();
    assert.equal(freshProcess.status, 0, freshProcess.stderr);
    const fresh = JSON.parse(freshProcess.stdout);
    assert.equal(fresh.transition_id, first.transition_id);
    assert.equal(fresh.branch_id, first.boundary.branch_id);
    assert.equal(fresh.state_fingerprint, first.boundary.state_fingerprint);
    for (const player of ['p1', 'p2'] as const) {
      assert.equal(fresh.perspectives[player].observation_id, first.boundary.perspectives[player].observation.observation_id);
      assert.equal(fresh.perspectives[player].belief_id, first.boundary.perspectives[player].belief.belief_id);
      assert.equal(fresh.perspectives[player].action_id, first.record_bundles[player].action.action_id);
      assert.equal(fresh.perspectives[player].record_id, localRecordIds[player]);
    }

    const second = await primary.step();
    const mirrorSecond = await mirror.step();
    assert.equal(second.transition_id, mirrorSecond.transition_id);
    assert.equal(second.boundary.step_index, 2);
    for (const player of ['p1', 'p2'] as const) {
      const before = second.record_bundles[player].input_observation;
      const after = second.boundary.perspectives[player].observation;
      assert.ok(after.event_cursor >= before.event_cursor);
      assert.deepEqual(after.protocol_prefix.slice(0, before.protocol_prefix.length), before.protocol_prefix);
      assert.equal(second.boundary.perspectives[player].belief.parent_belief_id,
        second.record_bundles[player].input_belief.belief_id);
      assert.equal(second.boundary.perspectives[player].belief.transition_history.length, 2);
    }

    const corrupt = structuredClone(second.record_bundles.p1);
    corrupt.successor_belief.simulator_snapshot!.state_fingerprint = '0'.repeat(64);
    const rejected = validateInPython(corrupt);
    assert.equal(rejected.status, 2);
    assert.match(rejected.stderr, /successor belief snapshot does not match transition output/);

    const rawState = structuredClone(second.record_bundles.p1);
    (rawState.transition as unknown as Record<string, unknown>).simulator_state = {};
    const privacyRejected = validateInPython(rawState);
    assert.equal(privacyRejected.status, 2);
    assert.match(privacyRejected.stderr, /private or raw simulator data/);
  } finally {
    await primary.close();
    await mirror.close();
  }
});

test('stale and simulator-rejected candidates leave the committed boundary unchanged', async () => {
  const session = await createPipelineIntegrationSession({ battle_id: 'pipeline-reject-v1', format: 'gen9randombattle', seed: SEED });
  const initialBoundary = session.boundary;
  try {
    const actions = actionPair(session);
    const stale = { ...actions.p1, rqid: (actions.p1.rqid ?? 0) + 10 };
    await assert.rejects(session.step({ p1: stale, p2: actions.p2 }), /request ID does not match/);
    assert.equal(session.boundary, initialBoundary);

    const invalid = { ...actions.p1, index: 13, action_id: 'act-' + '0'.repeat(64) };
    await assert.rejects(session.step({ p1: invalid, p2: actions.p2 }), /Canonical action index is invalid/);
    assert.equal(session.boundary.state_fingerprint, initialBoundary.state_fingerprint);

    const originalDiagnostics = LocalBattleEnv.prototype.diagnostics;
    LocalBattleEnv.prototype.diagnostics = function diagnosticsWithInjectedRejection() {
      const base = originalDiagnostics.call(this) as Record<string, unknown>;
      if (!this.id.includes('pipeline-step-')) return base;
      const players = base.players as Record<PlayerID, Record<string, unknown>>;
      return {
        ...base,
        players: { ...players, p1: { ...players.p1, last_choice_error: { message: 'injected postflight rejection' } } },
      };
    };
    try {
      await assert.rejects(session.step(), (error: Error) => error instanceof PipelineIntegrationError
        && error.code === 'pipeline/v1/rejected-action');
      assert.equal(session.boundary, initialBoundary);
    } finally {
      LocalBattleEnv.prototype.diagnostics = originalDiagnostics;
    }
    const accepted = await session.step();
    assert.equal(accepted.boundary.step_index, 1);
  } finally {
    await session.close();
  }
});

test('one-sided, waiting, requestless, and terminal observations classify and fail with explicit v1 codes', async () => {
  const session = await createPipelineIntegrationSession({ battle_id: 'pipeline-boundary-v1', format: 'gen9randombattle', seed: SEED });
  try {
    const states = {
      p1: structuredClone(session.boundary.perspectives.p1.observation),
      p2: structuredClone(session.boundary.perspectives.p2.observation),
    };
    const forced = structuredClone(states);
    forced.p1.request!.force_switch = true;
    forced.p2.decision_availability = { available: false, reason: 'requestless', legal_action_indices: null };

    const waiting = structuredClone(states);
    waiting.p1.decision_availability = { available: false, reason: 'waiting', legal_action_indices: null };
    waiting.p2.decision_availability = { available: false, reason: 'waiting', legal_action_indices: null };

    const requestless = structuredClone(states);
    requestless.p1.decision_availability = { available: false, reason: 'requestless', legal_action_indices: null };
    requestless.p2.decision_availability = { available: false, reason: 'requestless', legal_action_indices: null };

    const terminal = structuredClone(states);
    terminal.p1.view.terminated = true;

    const cases = [
      [classifyPipelineBoundary(forced), 'one_sided_forced_switch', 'unsupported-one-sided-forced-switch'],
      [classifyPipelineBoundary({ ...forced, p1: { ...forced.p1, request: { ...forced.p1.request!, force_switch: false } } }), 'one_sided_requestless', 'unsupported-one-sided-requestless'],
      [classifyPipelineBoundary(waiting), 'waiting', 'unsupported-waiting-boundary'],
      [classifyPipelineBoundary(requestless), 'requestless', 'unsupported-requestless-boundary'],
      [classifyPipelineBoundary(terminal), 'terminal', 'terminal-boundary'],
    ] as const;
    for (const [classified, kind, code] of cases) {
      assert.equal(classified, kind);
      assert.throws(() => assertPipelineTransitionSupported(classified), new RegExp(`pipeline/v1/${code}`));
    }
  } finally {
    await session.close();
  }
});

test('a real forced-switch boundary is checkpoint-free and requires an explicit future protocol', async () => {
  const session = await createPipelineIntegrationSession({ battle_id: 'pipeline-real-forced-v1', format: 'gen9randombattle', seed: SEED });
  try {
    let committedTransitions = 0;
    while (session.boundary.kind === 'joint_actionable' && committedTransitions < 20) {
      await session.step();
      committedTransitions += 1;
    }
    assert.equal(session.boundary.kind, 'one_sided_forced_switch');
    assert.ok(committedTransitions > 0);
    const boundary = session.boundary;
    await assert.rejects(session.step(), (error: Error) => error instanceof PipelineIntegrationError
      && error.code === 'pipeline/v1/unsupported-one-sided-forced-switch');
    assert.equal(session.boundary, boundary);
  } finally {
    await session.close();
  }
});

test('a real terminal result projects terminal beliefs or fails on unsupported protocol evidence with a versioned error', async () => {
  const env = new LocalBattleEnv('pipeline-terminal-smoke', 'gen9randombattle', [...SEED], {
    p1: { controller: 'random' },
    p2: { controller: 'random' },
  });
  try {
    const result = await env.resetWithOptions({ view_players: ['p1', 'p2'], include_log_delta: true, include_possible_roles: false });
    assert.equal(result.terminated, true);
    const protocolPrefix = projectPipelineProtocolPrefix(result.log_delta);
    const snapshot = env.captureSeededSnapshot(null);
    const snapshotRef = toSeededSnapshotRef(snapshot, 'pipeline-terminal-smoke');
    assert.throws(
      () => projectPipelineStepResult(result, 'pipeline-terminal-smoke', ['|-singleturn|p1a: Pikachu']),
      (error: Error) => error instanceof PipelineIntegrationError
        && error.code === 'pipeline/v1/unsupported-observable-protocol',
    );
    let observations: Record<PlayerID, ObservableBattleState>;
    try {
      observations = projectPipelineStepResult(result, 'pipeline-terminal-smoke', protocolPrefix);
    } catch (error) {
      assert.ok(error instanceof PipelineIntegrationError);
      assert.equal(error.code, 'pipeline/v1/unsupported-observable-protocol');
      assert.match(error.message, /Unsupported raw protocol event:|Malformed raw /);
      return;
    }
    assert.equal(classifyPipelineBoundary(observations), 'terminal');
    for (const player of ['p1', 'p2'] as const) {
      const belief = projectBeliefState({ observation: observations[player], simulator_snapshot: snapshotRef });
      assert.equal(belief.observation.observation_id, observations[player].observation_id);
      assert.ok(serializeBeliefState(belief).length > 0);
    }
    assert.throws(() => assertPipelineTransitionSupported('terminal'), /pipeline\/v1\/terminal-boundary/);
  } finally {
    await env.close();
  }
});
