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
  classifyPipelineRequestState,
  type PipelineRequestState,
  createPipelineIntegrationSession,
  PipelineIntegrationError,
  projectPipelineProtocolPrefix,
  projectPipelineStepResult,
} from '../src/pipeline_integration';
import type { ChoiceRequestView, PlayerID } from '../src/types';
import { toSeededSnapshotRef } from '../src/transition';

const SEED = [101, 202, 303, 404] as const;
const TERMINAL_CONTROLLER_SEEDS = { p1: 0x51a7, p2: 0xc0de } as const;

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

test('a naturally hidden Arena Trap rejection preserves the committed pipeline lineage', async () => {
  const options = {
    format: 'gen9randombattle',
    // Teams.generate receives p1 seed [57, 123, 235, 347] and p2 seed
    // [75, 159, 289, 419] after LocalBattleEnv's documented seed offsets.
    // These pinned teams include p1 Dugtrio/Arena Trap and p2 Tinkaton/Steel.
    seed: [46, 101, 202, 303] as const,
  };
  const session = await createPipelineIntegrationSession({ battle_id: 'pipeline-natural-reject-v1', ...options });
  const control = await createPipelineIntegrationSession({ battle_id: 'pipeline-natural-reject-v1', ...options });
  try {
    const choose = (boundary: typeof session.boundary, player: PlayerID, predicate: (choice: string) => boolean) => {
      const request = boundary.perspectives[player].observation.request;
      assert.ok(request);
      const action = request.legal_actions.actions.find((candidate) => candidate && predicate(candidate.choice));
      assert.ok(action, `missing legal action for ${player}`);
      return canonicalActionFromLegalAction(request, action.index);
    };

    const advanceToTrap = async (target: typeof session) => {
      const initial = target.boundary;
      const actions = {
        p1: choose(initial, 'p1', (choice) => choice === 'switch 3'),
        p2: choose(initial, 'p2', (choice) => choice === 'switch 6'),
      };
      return target.step(actions);
    };

    const [trapped, controlTrapped] = await Promise.all([advanceToTrap(session), advanceToTrap(control)]);
    assert.equal(trapped.boundary.state_fingerprint, controlTrapped.boundary.state_fingerprint);
    assert.equal(trapped.boundary.perspectives.p1.observation.view.self_team.find((mon) => mon.active)?.species, 'Dugtrio');
    assert.equal(trapped.boundary.perspectives.p2.observation.view.self_team.find((mon) => mon.active)?.species, 'Tinkaton');

    const committed = session.boundary;
    const committedLineage = ['p1', 'p2'].map((player) => {
      const view = committed.perspectives[player as PlayerID];
      return {
        observation_id: view.observation.observation_id,
        belief_id: view.belief.belief_id,
        event_cursor: view.observation.event_cursor,
      };
    });
    const attemptedSwitch = choose(committed, 'p2', (choice) => choice === 'switch 2');
    const validP1 = choose(committed, 'p1', (choice) => choice.startsWith('move '));
    await assert.rejects(
      session.step({ p1: validP1, p2: attemptedSwitch }),
      (error: Error) => error instanceof PipelineIntegrationError
        && error.code === 'pipeline/v1/rejected-action'
        && /p2 choice was rejected by the simulator/.test(error.message),
    );

    assert.equal(session.boundary, committed);
    assert.equal(session.boundary.step_index, committed.step_index);
    assert.equal(session.boundary.branch_id, committed.branch_id);
    assert.equal(session.boundary.state_fingerprint, committed.state_fingerprint);
    assert.deepEqual(['p1', 'p2'].map((player) => {
      const view = session.boundary.perspectives[player as PlayerID];
      return {
        observation_id: view.observation.observation_id,
        belief_id: view.belief.belief_id,
        event_cursor: view.observation.event_cursor,
      };
    }), committedLineage);

    const continueWithMoves = async (target: typeof session) => {
      const boundary = target.boundary;
      return target.step({
        p1: choose(boundary, 'p1', (choice) => choice.startsWith('move ')),
        p2: choose(boundary, 'p2', (choice) => choice.startsWith('move ')),
      });
    };
    const [afterReject, controlNext] = await Promise.all([continueWithMoves(session), continueWithMoves(control)]);
    assert.equal(afterReject.boundary.state_fingerprint, controlNext.boundary.state_fingerprint);
    for (const player of ['p1', 'p2'] as const) {
      assert.equal(
        afterReject.boundary.perspectives[player].observation.observation_id,
        controlNext.boundary.perspectives[player].observation.observation_id,
      );
    }
  } finally {
    await session.close();
    await control.close();
  }
});

test('unresolved protocol aliases stop pipeline projection while known raw-only records remain distinct', async () => {
  const env = new LocalBattleEnv('pipeline-protocol-boundary', 'gen9randombattle', [...SEED]);
  try {
    const result = await env.resetWithOptions({ view_players: ['p1', 'p2'], include_log_delta: true, include_possible_roles: false });
    const basePrefix = projectPipelineProtocolPrefix(result.log_delta);
    const aliases = ['clearstatus', '-clearstatus', 'nothing'];
    for (const alias of aliases) {
      const line = `|${alias}|audit`;
      assert.throws(
        () => projectPipelineProtocolPrefix([...result.log_delta, line]),
        (error: Error) => error instanceof PipelineIntegrationError
          && error.code === 'pipeline/v1/unresolved-protocol-alias'
          && error.diagnostic.record_command === alias
          && error.diagnostic.record_index === result.log_delta.length,
      );
      assert.throws(
        () => projectPipelineStepResult(result, 'pipeline-protocol-boundary', [...basePrefix, line]),
        (error: Error) => error instanceof PipelineIntegrationError
          && error.code === 'pipeline/v1/unresolved-protocol-alias'
          && error.diagnostic.record_command === alias
          && error.diagnostic.record_index === basePrefix.length,
      );
    }

    for (const rawOnlyRecord of ['|-message|known raw-only diagnostic', '|-fieldactivate|Delta Stream', '|-nothing']) {
      const prefix = projectPipelineProtocolPrefix([...result.log_delta, rawOnlyRecord]);
      const states = projectPipelineStepResult(result, 'pipeline-protocol-boundary', prefix);
      assert.equal(states.p1.protocol_prefix.at(-1), rawOnlyRecord);
      assert.equal(states.p2.protocol_prefix.at(-1), rawOnlyRecord);
    }
  } finally {
    await env.close();
  }
});

test('an unresolved alias cannot replace a committed pipeline boundary or lineage', async () => {
  const session = await createPipelineIntegrationSession({ battle_id: 'pipeline-alias-atomicity-v1', format: 'gen9randombattle', seed: SEED });
  const committed = session.boundary;
  const committedLineage = {
    step_index: committed.step_index,
    branch_id: committed.branch_id,
    state_fingerprint: committed.state_fingerprint,
    perspectives: Object.fromEntries(['p1', 'p2'].map((player) => {
      const state = committed.perspectives[player as PlayerID];
      return [player, {
        observation_id: state.observation.observation_id,
        belief_id: state.belief.belief_id,
        event_cursor: state.observation.event_cursor,
      }];
    })),
  };
  const originalStepSeededTransition = LocalBattleEnv.prototype.stepSeededTransition;
  try {
    LocalBattleEnv.prototype.stepSeededTransition = async function (request, options) {
      const result = await originalStepSeededTransition.call(this, request, options);
      return {
        ...result,
        metadata: {
          ...result.metadata,
          emitted_log_delta: [...result.metadata.emitted_log_delta, '|clearstatus|legacy-token'],
        },
      };
    };
    await assert.rejects(session.step(), (error: Error) => error instanceof PipelineIntegrationError
      && error.code === 'pipeline/v1/unresolved-protocol-alias'
      && error.diagnostic.record_command === 'clearstatus');
    LocalBattleEnv.prototype.stepSeededTransition = originalStepSeededTransition;
    assert.equal(session.boundary, committed);
    assert.deepEqual({
      step_index: session.boundary.step_index,
      branch_id: session.boundary.branch_id,
      state_fingerprint: session.boundary.state_fingerprint,
      perspectives: Object.fromEntries(['p1', 'p2'].map((player) => {
        const state = session.boundary.perspectives[player as PlayerID];
        return [player, {
          observation_id: state.observation.observation_id,
          belief_id: state.belief.belief_id,
          event_cursor: state.observation.event_cursor,
        }];
      })),
    }, committedLineage);
    const control = await createPipelineIntegrationSession({
      battle_id: 'pipeline-alias-atomicity-v1',
      format: 'gen9randombattle',
      seed: SEED,
    });
    try {
      assert.equal(control.boundary.state_fingerprint, committed.state_fingerprint);
      const [next, controlNext] = await Promise.all([session.step(), control.step()]);
      assert.equal(next.boundary.step_index, committed.step_index + 1);
      assert.equal(next.boundary.state_fingerprint, controlNext.boundary.state_fingerprint);
      assert.equal(
        next.boundary.perspectives.p1.observation.observation_id,
        controlNext.boundary.perspectives.p1.observation.observation_id,
      );
      assert.equal(
        next.boundary.perspectives.p2.observation.observation_id,
        controlNext.boundary.perspectives.p2.observation.observation_id,
      );
    } finally {
      await control.close();
    }
  } finally {
    LocalBattleEnv.prototype.stepSeededTransition = originalStepSeededTransition;
    await session.close();
  }
});

test('per-player request states distinguish waiting from absence and retain explicit execution guards', async () => {
  const session = await createPipelineIntegrationSession({ battle_id: 'pipeline-boundary-v1', format: 'gen9randombattle', seed: SEED });
  try {
    const asState = (player: PlayerID, kind: PipelineRequestState): ObservableBattleState => {
      const state = structuredClone(session.boundary.perspectives[player].observation);
      if (kind === 'terminal') state.view.terminated = true;
      if (kind === 'forced_switch') state.request!.force_switch = true;
      if (kind === 'requestless') state.request = null;
      if (kind === 'waiting' || kind === 'no_legal_actions') {
        state.request!.wait = kind === 'waiting';
        state.request!.legal_actions = {
          mask: state.request!.legal_actions.mask.map(() => false),
          actions: state.request!.legal_actions.actions.map(() => null),
          available_indices: [],
        };
      }
      if (kind === 'waiting' || kind === 'requestless' || kind === 'no_legal_actions') {
        state.decision_availability = {
          available: false, reason: kind, legal_action_indices: kind === 'no_legal_actions' ? [] : null,
        };
      }
      assert.equal(classifyPipelineRequestState(state), kind);
      return state;
    };
    const cases = [
      ['actionable', 'actionable', 'joint_actionable', null],
      ['forced_switch', 'forced_switch', 'joint_actionable', null],
      ['forced_switch', 'waiting', 'one_sided_forced_switch', 'unsupported-one-sided-forced-switch'],
      ['forced_switch', 'requestless', 'one_sided_forced_switch', 'unsupported-one-sided-forced-switch'],
      ['actionable', 'requestless', 'one_sided_requestless', 'unsupported-one-sided-requestless'],
      ['actionable', 'waiting', 'waiting', 'unsupported-waiting-boundary'],
      ['waiting', 'waiting', 'waiting', 'unsupported-waiting-boundary'],
      ['waiting', 'requestless', 'waiting', 'unsupported-waiting-boundary'],
      ['requestless', 'requestless', 'requestless', 'unsupported-requestless-boundary'],
      ['terminal', 'actionable', 'terminal', 'terminal-boundary'],
      ['terminal', 'waiting', 'terminal', 'terminal-boundary'],
      ['terminal', 'no_legal_actions', 'terminal', 'terminal-boundary'],
    ] as const;
    for (const [left, right, kind, code] of cases) {
      for (const [p1, p2] of [[left, right], [right, left]]) {
        const classified = classifyPipelineBoundary({ p1: asState('p1', p1), p2: asState('p2', p2) });
        assert.equal(classified, kind);
        if (code) assert.throws(() => assertPipelineTransitionSupported(classified), new RegExp(`pipeline/v1/${code}`));
        else assert.doesNotThrow(() => assertPipelineTransitionSupported(classified));
      }
    }
    for (const player of ['p1', 'p2'] as const) {
      const states = { p1: asState('p1', 'actionable'), p2: asState('p2', 'actionable') };
      states[player] = asState(player, 'no_legal_actions');
      assert.throws(() => classifyPipelineBoundary(states),
        (error: Error) => error instanceof PipelineIntegrationError && error.code === 'pipeline/v1/no-legal-actions');
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
      const step = await session.step();
      if (step.boundary.kind !== 'joint_actionable') {
        for (const player of ['p1', 'p2'] as const) {
          const validated = validateInPython(step.record_bundles[player]);
          assert.equal(validated.status, 0, validated.stderr);
        }
      }
      committedTransitions += 1;
    }
    assert.equal(session.boundary.kind, 'one_sided_forced_switch');
    assert.ok(committedTransitions > 0);
    const boundary = session.boundary;
    const states = ['p1', 'p2'].map((player) => classifyPipelineRequestState(boundary.perspectives[player as PlayerID].observation));
    assert.deepEqual(states.sort(), ['forced_switch', 'waiting']);
    for (const player of ['p1', 'p2'] as const) {
      const observation = boundary.perspectives[player].observation;
      assert.equal(observation.request?.player, player);
      assert.ok(observation.protocol_prefix.every((line) => !line.startsWith('|request|')));
      if (observation.request?.wait) {
        assert.equal(observation.decision_availability.reason, 'waiting');
        assert.deepEqual(observation.request.legal_actions.available_indices, []);
      }
    }
    await assert.rejects(session.step(), (error: Error) => error instanceof PipelineIntegrationError
      && error.code === 'pipeline/v1/unsupported-one-sided-forced-switch');
    assert.equal(session.boundary, boundary);
  } finally {
    await session.close();
  }
});

test('a seeded random-controller terminal trace is repeatable and projects both perspectives', async () => {
  const runTerminalScenario = async () => {
    const env = new LocalBattleEnv('pipeline-terminal-smoke', 'gen9randombattle', [...SEED], {
      p1: { controller: 'random', random_seed: TERMINAL_CONTROLLER_SEEDS.p1 },
      p2: { controller: 'random', random_seed: TERMINAL_CONTROLLER_SEEDS.p2 },
    });
    try {
      const result = await env.resetWithOptions({ view_players: ['p1', 'p2'], include_log_delta: true, include_possible_roles: false, include_wait_requests: true });
      assert.equal(result.terminated, true);
      assert.deepEqual(result.requests, { p1: null, p2: null });
      const protocolPrefix = projectPipelineProtocolPrefix(result.log_delta);
      const snapshot = env.captureSeededSnapshot(null);
      const snapshotRef = toSeededSnapshotRef(snapshot, 'pipeline-terminal-smoke');
      const restored = new LocalBattleEnv('pipeline-terminal-restore', 'gen9randombattle', [...SEED]);
      try {
        const replay = await restored.resetFromSerialized(snapshot.simulator_state, { include_wait_requests: true });
        assert.equal(replay.terminated, true);
        assert.equal(replay.winner, result.winner);
        assert.deepEqual(replay.requests, { p1: null, p2: null });
      } finally {
        await restored.close();
      }
      const observations: Record<PlayerID, ObservableBattleState> = projectPipelineStepResult(
        result,
        'pipeline-terminal-smoke',
        protocolPrefix,
      );
      assert.equal(classifyPipelineBoundary(observations), 'terminal');
      for (const player of ['p1', 'p2'] as const) {
        const belief = projectBeliefState({ observation: observations[player], simulator_snapshot: snapshotRef });
        assert.equal(belief.observation.observation_id, observations[player].observation_id);
        assert.ok(serializeBeliefState(belief).length > 0);
        assert.equal(observations[player].view.terminated, true);
        assert.equal(classifyPipelineRequestState(observations[player]), 'terminal');
        assert.equal(observations[player].perspective, player);
      }
      return { protocolPrefix, winner: result.winner };
    } finally {
      await env.close();
    }
  };

  // Simulator seed [101, 202, 303, 404] controls Showdown mechanics/team RNG;
  // controller seeds 0x51a7/0xc0de control independent p1/p2 action streams.
  const first = await runTerminalScenario();
  const replay = await runTerminalScenario();
  assert.deepEqual(replay.protocolPrefix, first.protocolPrefix);
  assert.equal(replay.winner, first.winner);
  assert.throws(() => assertPipelineTransitionSupported('terminal'), /pipeline\/v1\/terminal-boundary/);
});
