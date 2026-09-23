import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import {
  canonicalActionFromLegalAction,
} from '../src/canonical_action';
import {
  EnvironmentManager,
  LocalBattleEnv,
} from '../src/env_manager';
import {
  OBSERVABLE_STATE_SCHEMA_VERSION,
  projectObservableBattleState,
  type ObservableBattleState,
} from '../src/observable_state';
import type { ChoiceRequestView, PlayerID, StepResult } from '../src/types';
import {
  SEEDED_TRANSITION_SCHEMA_VERSION,
  type SeededTransitionRequest,
} from '../src/transition';

const SEED = [101, 202, 303, 404] as const;
const OPTIONS = { view_players: ['p1', 'p2'] as PlayerID[], include_log_delta: true, include_possible_roles: false };
const transitionFixture = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../../../tests/fixtures/seeded_transition_v1.json'), 'utf8'),
) as { case: Record<string, unknown> };

function observationFor(result: StepResult, player: PlayerID): ObservableBattleState {
  const view = result.views[player];
  const request = result.requests[player];
  assert.ok(view);
  assert.ok(request);
  const rqid = request.rqid;
  const prefix = [`|turn|${view.turn}`];
  if (rqid !== null) prefix.push(`|request|${JSON.stringify({ rqid })}`);
  return projectObservableBattleState({
    schema_version: OBSERVABLE_STATE_SCHEMA_VERSION,
    source_kind: 'sim_core',
    battle_id: 'transition-fixture',
    perspective: player,
    snapshot_phase: request.force_switch ? 'forced_switch' : 'pre_decision',
    protocol_prefix: prefix,
    view,
    request,
  });
}

function actionFor(result: StepResult, player: PlayerID) {
  const request = result.requests[player] as ChoiceRequestView;
  return canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0]);
}

function transitionRequest(
  snapshot: ReturnType<LocalBattleEnv['captureSeededSnapshot']>,
  result: StepResult,
  actions: SeededTransitionRequest['actions'],
): SeededTransitionRequest {
  return {
    schema_version: SEEDED_TRANSITION_SCHEMA_VERSION,
    snapshot,
    observations: {
      p1: observationFor(result, 'p1'),
      p2: observationFor(result, 'p2'),
    },
    actions,
    step_index: 0,
  };
}

test('seeded snapshots have deterministic fingerprints and branch identities', async () => {
  const first = new LocalBattleEnv('transition-seed-a', 'gen9randombattle', [...SEED], { p1: { controller: 'external' }, p2: { controller: 'external' } });
  const second = new LocalBattleEnv('transition-seed-b', 'gen9randombattle', [...SEED], { p1: { controller: 'external' }, p2: { controller: 'external' } });
  try {
    await first.resetWithOptions(OPTIONS);
    await second.resetWithOptions(OPTIONS);
    const firstSnapshot = first.captureSeededSnapshot(null);
    const secondSnapshot = second.captureSeededSnapshot(null);
    assert.equal(firstSnapshot.state_fingerprint, secondSnapshot.state_fingerprint);
    assert.equal(firstSnapshot.branch_id, secondSnapshot.branch_id);
    assert.deepEqual(firstSnapshot.root_seed, SEED);
  } finally {
    await first.close();
    await second.close();
  }
});

test('mixed-invalid joint actions reject atomically before raw choice forwarding', async () => {
  const env = new LocalBattleEnv('transition-atomic', 'gen9randombattle', [...SEED], { p1: { controller: 'external' }, p2: { controller: 'external' } });
  try {
    const initial = await env.resetWithOptions(OPTIONS);
    const snapshot = env.captureSeededSnapshot(null);
    const actions = { p1: actionFor(initial, 'p1'), p2: actionFor(initial, 'p2') };
    const request = transitionRequest(snapshot, initial, { ...actions, p2: { ...actions.p2, rqid: 999 } });
    await assert.rejects(env.stepSeededTransition(request, OPTIONS), /request ID does not match/);
    const staleObservation = observationFor(initial, 'p1');
    const staleRequestId = (staleObservation.request?.rqid || 0) + 1;
    const staleObservationRequest = { ...staleObservation.request!, rqid: staleRequestId };
    const staleAction = canonicalActionFromLegalAction(
      staleObservationRequest,
      staleObservationRequest.legal_actions.available_indices[0],
    );
    await assert.rejects(
      env.stepSeededTransition({
        ...transitionRequest(snapshot, initial, actions),
        observations: { p1: { ...staleObservation, request: staleObservationRequest }, p2: observationFor(initial, 'p2') },
        actions: { p1: staleAction, p2: actions.p2 },
      }, OPTIONS),
      /request ID does not match/,
    );
    await assert.rejects(
      env.stepSeededTransition({
        ...transitionRequest({ ...snapshot, branch_id: 'branch-tampered' }, initial, actions),
      }, OPTIONS),
      /authoritative snapshot lineage/,
    );
    const after = env.captureSeededSnapshot(null);
    assert.equal(after.state_fingerprint, snapshot.state_fingerprint);
    assert.deepEqual(env.getRequest('p1')?.legal_actions.available_indices, initial.requests.p1?.legal_actions.available_indices);
    assert.deepEqual(env.getRequest('p2')?.legal_actions.available_indices, initial.requests.p2?.legal_actions.available_indices);
  } finally {
    await env.close();
  }
});

test('serialized seeded snapshots replay identical canonical joint transitions', async () => {
  const source = new LocalBattleEnv('transition-source', 'gen9randombattle', [...SEED], { p1: { controller: 'external' }, p2: { controller: 'external' } });
  const restored = new LocalBattleEnv('transition-restored', 'gen9randombattle', [...SEED], { p1: { controller: 'external' }, p2: { controller: 'external' } });
  try {
    const sourceInitial = await source.resetWithOptions(OPTIONS);
    const serialized = source.serializeBattle();
    const restoredInitial = await restored.resetFromSerialized(serialized, OPTIONS);
    const sourceSnapshot = source.captureSeededSnapshot(null);
    const restoredSnapshot = restored.captureSeededSnapshot(null);
    assert.equal(sourceSnapshot.state_fingerprint, restoredSnapshot.state_fingerprint);
    const actions = { p1: actionFor(sourceInitial, 'p1'), p2: actionFor(sourceInitial, 'p2') };
    const sourceTransition = await source.stepSeededTransition(transitionRequest(sourceSnapshot, sourceInitial, actions), OPTIONS);
    const restoredTransition = await restored.stepSeededTransition(transitionRequest(restoredSnapshot, restoredInitial, actions), OPTIONS);
    const expected = transitionFixture.case;
    assert.deepEqual(sourceSnapshot.root_seed, [101, 202, 303, 404]);
    assert.equal(sourceSnapshot.state_fingerprint, expected.input_state_fingerprint);
    assert.equal(sourceSnapshot.branch_id, expected.parent_branch_id);
    assert.deepEqual(sourceTransition.metadata.action_ids, expected.action_ids);
    assert.equal(sourceTransition.metadata.transition_id, expected.transition_id);
    assert.equal(sourceTransition.metadata.branch_id, expected.branch_id);
    assert.equal(sourceTransition.metadata.output_state_fingerprint, expected.output_state_fingerprint);
    assert.ok(sourceTransition.metadata.emitted_log_delta.length > 0);
    assert.match(sourceTransition.metadata.emitted_log_delta[1], /^\|t:\|\d+$/);
    const normalizedLogDelta = sourceTransition.metadata.emitted_log_delta.map((line) => (
      /^\|t:\|\d+$/.test(line) ? '|t:|<timestamp>' : line
    ));
    assert.deepEqual(normalizedLogDelta, expected.emitted_log_delta);
    assert.equal(sourceTransition.step_result.info.turn, expected.step_turn);
    assert.deepEqual({ p1: sourceTransition.step_result.requests.p1?.rqid ?? null, p2: sourceTransition.step_result.requests.p2?.rqid ?? null }, expected.output_request_rqids);
    assert.equal(sourceTransition.metadata.transition_id, restoredTransition.metadata.transition_id);
    assert.equal(sourceTransition.metadata.branch_id, restoredTransition.metadata.branch_id);
    assert.equal(sourceTransition.metadata.output_state_fingerprint, restoredTransition.metadata.output_state_fingerprint);
    assert.deepEqual(sourceTransition.metadata.action_ids, restoredTransition.metadata.action_ids);
    assert.ok(restoredTransition.metadata.emitted_log_delta.length > 0);
    assert.deepEqual(
      restoredTransition.metadata.emitted_log_delta.map((line) => /^\|t:\|\d+$/.test(line) ? '|t:|<timestamp>' : line),
      expected.emitted_log_delta,
    );
  } finally {
    await source.close();
    await restored.close();
  }
});

test('manager transition boundary exposes opaque snapshot handles only', async () => {
  const manager = new EnvironmentManager();
  const { env_id } = manager.createEnv('gen9randombattle', [...SEED], {
    p1: { controller: 'external' },
    p2: { controller: 'external' },
  });
  try {
    const initial = await manager.resetEnv(env_id, OPTIONS);
    const snapshot = manager.captureSeededSnapshotEnv(env_id);
    assert.equal('simulator_state' in snapshot, false);
    const actions = { p1: actionFor(initial, 'p1'), p2: actionFor(initial, 'p2') };
    const result = await manager.stepSeededTransitionEnv(env_id, {
      schema_version: SEEDED_TRANSITION_SCHEMA_VERSION,
      snapshot,
      observations: {
        p1: observationFor(initial, 'p1'),
        p2: observationFor(initial, 'p2'),
      },
      actions,
      step_index: 0,
    }, OPTIONS);
    assert.equal('simulator_state' in result.output_snapshot, false);
    assert.match(result.output_snapshot.snapshot_handle, /^snapshot-\d+$/);
    assert.equal(result.metadata.simulator_revision, 'sim-core@0.1.0+pokemon-showdown@0.11.10');
  } finally {
    await manager.closeAll();
  }
});
