import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import path from 'node:path';
import test from 'node:test';
import { canonicalActionFromLegalAction, type CanonicalAction } from '../src/canonical_action';
import { projectBeliefState, serializeBeliefState, validateObservableBattleState } from '../src/belief_state';
import { LocalBattleEnv } from '../src/env_manager';
import type { ObservableBattleState } from '../src/observable_state';
import {
  assertPipelineTransitionSupported,
  classifyPipelineBoundary,
  classifyPipelineRequestState,
  type PipelineBoundary,
  type PipelineRequestState,
  createPipelineIntegrationSession,
  PipelineIntegrationError,
  projectPipelineProtocolPrefix,
  projectPipelineStepResult,
} from '../src/pipeline_integration';
import type { ChoiceRequestView, PlayerID } from '../src/types';
import { toSeededSnapshotRef } from '../src/transition';
import { PROTOCOL_CONTRACT } from '../src/protocol_contract';

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

function assertPythonRejectsWithoutPublication(bundle: unknown, label: string, reason?: RegExp): void {
  const rejected = validateInPython(bundle);
  assert.equal(rejected.status, 2, `${label}: ${rejected.stderr}`);
  assert.equal(rejected.stdout, '', `${label}: Python must not publish a record`);
  if (reason) assert.match(rejected.stderr, reason, `${label}: ${rejected.stderr}`);
}

function typeScriptCanonical(value: unknown): string {
  if (value === null || typeof value === 'boolean' || typeof value === 'number' || typeof value === 'string') {
    const serialized = JSON.stringify(value);
    if (serialized === undefined) throw new Error('identity value is not JSON serializable');
    return serialized;
  }
  if (Array.isArray(value)) return `[${value.map(typeScriptCanonical).join(',')}]`;
  if (typeof value === 'object') {
    const object = value as Record<string, unknown>;
    return `{${Object.keys(object).sort().map((key) => `${JSON.stringify(key)}:${typeScriptCanonical(object[key])}`).join(',')}}`;
  }
  throw new Error('identity value is not JSON serializable');
}

function typeScriptDigest(value: unknown): string {
  return createHash('sha256').update(typeScriptCanonical(value), 'utf8').digest('hex');
}

/** Recompute successor identities after a change that leaves its prefix valid. */
function rehashSuccessorObservationAndBelief(candidate: Record<string, any>): Record<string, any> {
  const observation = candidate.successor_observation as Record<string, any>;
  const priorObservationId = observation.observation_id;
  observation.observation_id = `obs-${typeScriptDigest(Object.fromEntries(
    Object.entries(observation).filter(([key]) => key !== 'observation_id' && key !== 'protocol_prefix'),
  ))}`;

  const belief = candidate.successor_belief as Record<string, any>;
  const observationReference = {
    schema_version: observation.schema_version,
    observation_id: observation.observation_id,
    source_kind: observation.source_kind,
    event_cursor: observation.event_cursor,
    protocol_prefix_hash: observation.protocol_prefix_hash,
    snapshot_phase: observation.snapshot_phase,
  };
  const updateReference = (reference: Record<string, any>) => {
    if (reference.observation_id === priorObservationId) Object.assign(reference, observationReference);
  };
  updateReference(belief.observation);
  for (const reference of belief.observation_history) updateReference(reference);
  for (const transition of belief.transition_history) {
    if (transition.output_observation_id === priorObservationId) transition.output_observation_id = observation.observation_id;
  }
  belief.transition_lineage.output_observation_id = observation.observation_id;
  belief.belief_id = `belief-${typeScriptDigest(Object.fromEntries(
    Object.entries(belief).filter(([key]) => key !== 'belief_id'),
  ))}`;
  return candidate;
}

/** Recompute the nested v2 identities after a public-stage mutation. */
function rehashedSuccessorPublicStage(bundle: unknown): unknown {
  const candidate = structuredClone(bundle) as Record<string, any>;
  const activeOpponent = candidate.successor_observation.view.opponent_team
    .find((pokemon: Record<string, unknown>) => pokemon.active);
  assert.ok(activeOpponent?.public_boosts);
  const priorStage = activeOpponent.public_boosts.atk;
  activeOpponent.public_boosts.atk = priorStage === 6 ? 5 : priorStage + 1;
  return rehashSuccessorObservationAndBelief(candidate);
}

function rehashedSuccessorTypedLifecycleTamper(bundle: unknown, kind: 'volatile' | 'side-condition' | 'presence'): unknown {
  const candidate = structuredClone(bundle) as Record<string, any>;
  const view = candidate.successor_observation.view;
  if (kind === 'volatile') {
    const active = [...view.self_team, ...view.opponent_team].find((pokemon: Record<string, unknown>) => pokemon.active);
    assert.ok(active);
    active.volatiles = active.volatiles.includes('substitute')
      ? active.volatiles.filter((effect: string) => effect !== 'substitute')
      : [...active.volatiles, 'substitute'];
  } else {
    const self = view.field.side_conditions.self;
    if (kind === 'side-condition') self.spikes = self.spikes === 1 ? 2 : 1;
    else if (self.reflect === 1) delete self.reflect;
    else self.reflect = 1;
  }
  return rehashSuccessorObservationAndBelief(candidate);
}

function rehashedSuccessorMissingVolatileRosterRow(bundle: unknown, removeRow: boolean): Record<string, any> {
  const candidate = structuredClone(bundle) as Record<string, any>;
  const observation = candidate.successor_observation as Record<string, any>;
  const team = observation.view.self_team as Array<Record<string, any>>;
  const active = team.find((pokemon) => pokemon.active);
  assert.ok(active);
  const rosterIdent = active.ident as string;
  const protocolIdent = rosterIdent.replace(/^(p[12]): /, '$1a: ');
  observation.protocol_prefix.push(`|-start|${protocolIdent}|Substitute`);
  observation.event_cursor = observation.protocol_prefix.length;
  active.volatiles = [...new Set([...(active.volatiles as string[]), 'substitute'])];
  if (removeRow) observation.view.self_team = team.filter((pokemon) => pokemon !== active);
  observation.protocol_prefix_hash = typeScriptDigest(observation.protocol_prefix);
  candidate.successor_belief.source_protocol_prefix = structuredClone(observation.protocol_prefix);
  return rehashSuccessorObservationAndBelief(candidate);
}

type PartialProjectionCase = 'volatile-roster' | 'volatile-team' | 'side-field' | 'side-container'
  | 'side-self' | 'side-opponent' | 'side-wrong-compartment';

function rehashedSuccessorPartialTypedProjection(bundle: unknown, omission: PartialProjectionCase): Record<string, any> {
  const candidate = structuredClone(bundle) as Record<string, any>;
  const observation = candidate.successor_observation as Record<string, any>;
  const view = observation.view as Record<string, any>;
  const team = view.self_team as Array<Record<string, any>>;
  const active = team.find((pokemon) => pokemon.active);
  assert.ok(active);
  if (omission === 'volatile-roster' || omission === 'volatile-team') {
    const protocolIdent = (active.ident as string).replace(/^(p[12]): /, '$1a: ');
    observation.protocol_prefix.push(`|-start|${protocolIdent}|Substitute`);
    active.volatiles = [...new Set([...(active.volatiles as string[]), 'substitute'])];
    if (omission === 'volatile-roster') view.self_team = team.filter((pokemon) => pokemon !== active);
    else delete view.self_team;
  } else {
    observation.protocol_prefix.push('|-sidestart|p1: One|Spikes');
    const field = view.field as Record<string, any>;
    const sides = field.side_conditions as Record<string, any>;
    if (omission === 'side-opponent') {
      observation.protocol_prefix.push('|-sidestart|p2: Two|Reflect');
      sides.opponent.reflect = 1;
      delete sides.opponent;
    } else {
      sides.self.spikes = 1;
      if (omission === 'side-field') delete view.field;
      else if (omission === 'side-container') delete field.side_conditions;
      else if (omission === 'side-self') delete sides.self;
      else {
        delete sides.self.spikes;
        sides.opponent.spikes = 1;
      }
    }
  }
  observation.event_cursor = observation.protocol_prefix.length;
  observation.protocol_prefix_hash = typeScriptDigest(observation.protocol_prefix);
  candidate.successor_belief.source_protocol_prefix = structuredClone(observation.protocol_prefix);
  return rehashSuccessorObservationAndBelief(candidate);
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

function committedBoundaryShape(boundary: PipelineBoundary) {
  return {
    state_fingerprint: boundary.state_fingerprint,
    step_index: boundary.step_index,
    branch_id: boundary.branch_id,
    perspectives: Object.fromEntries(['p1', 'p2'].map((player) => {
      const perspective = boundary.perspectives[player as PlayerID];
      return [player, {
        observation_id: perspective.observation.observation_id,
        belief_id: perspective.belief.belief_id,
        cursor: perspective.observation.event_cursor,
        active: structuredClone(perspective.observation.view.active),
        parent_belief_id: perspective.belief.parent_belief_id,
        transition_lineage: structuredClone(perspective.belief.transition_lineage),
      }];
    })),
  };
}

function assertV2PerspectiveBoundary(boundary: PipelineBoundary): void {
  for (const player of ['p1', 'p2'] as const) {
    const observation = boundary.perspectives[player].observation;
    assert.equal(observation.schema_version, 'observable-battle-state/v2');
    assert.equal(observation.perspective, player);
    assert.equal(observation.request?.player, player);
    assert.ok(observation.request?.legal_actions.available_indices.length);
    assert.ok(observation.protocol_prefix.every((record) => !record.startsWith('|request|')));
  }
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

    const committedBoundaryBeforeLifecycleTamper = structuredClone(primary.boundary);
    for (const kind of ['volatile', 'side-condition', 'presence'] as const) {
      const candidate = rehashedSuccessorTypedLifecycleTamper(first.record_bundles.p1, kind) as Record<string, any>;
      assert.doesNotThrow(() => serializeBeliefState(candidate.successor_belief), `${kind} candidate identities are internally consistent`);
      assert.throws(() => validateObservableBattleState(candidate.successor_observation), /Typed lifecycle evidence mismatch/);
      assertPythonRejectsWithoutPublication(candidate, `fully rehashed false typed ${kind}`, /Typed lifecycle evidence mismatch/);
      assert.deepEqual(primary.boundary, committedBoundaryBeforeLifecycleTamper, `${kind} rejection preserves the committed boundary`);
    }

    const validSubstituteRow = rehashedSuccessorMissingVolatileRosterRow(first.record_bundles.p1, false);
    assert.doesNotThrow(() => validateObservableBattleState(validSubstituteRow.successor_observation));
    const visibleSubstitutePublication = validateInPython(validSubstituteRow);
    assert.equal(visibleSubstitutePublication.status, 0, `a visible Substitute row remains publishable: ${visibleSubstitutePublication.stderr}`);
    const missingSubstituteRow = rehashedSuccessorMissingVolatileRosterRow(first.record_bundles.p1, true);
    assert.throws(() => validateObservableBattleState(missingSubstituteRow.successor_observation), /exactly one canonical self_team roster row|owned roster identity\/order disagrees/);
    assertPythonRejectsWithoutPublication(missingSubstituteRow, 'fully rehashed omitted Substitute roster row', /exactly one canonical self_team roster row|owned roster identity\/order disagrees/);
    assert.deepEqual(primary.boundary, committedBoundaryBeforeLifecycleTamper, 'missing-row rejection preserves the committed boundary');

    for (const omission of [
      'volatile-roster', 'volatile-team', 'side-field', 'side-container', 'side-self', 'side-opponent',
      'side-wrong-compartment',
    ] as const) {
      const partial = rehashedSuccessorPartialTypedProjection(first.record_bundles.p1, omission);
      assert.throws(() => validateObservableBattleState(partial.successor_observation),
        /Typed lifecycle evidence mismatch/, `${omission} must not erase prefix-derived typed state`);
      assertPythonRejectsWithoutPublication(partial, `fully rehashed partial projection ${omission}`,
        /Typed lifecycle evidence mismatch/);
      assert.deepEqual(primary.boundary, committedBoundaryBeforeLifecycleTamper,
        `${omission} rejection preserves the committed TypeScript boundary`);
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

test('v2 joint transitions restore deterministic candidates and retain committed lineage after rejection', async () => {
  const options = {
    battle_id: 'pipeline-v2-joint-transition-v1',
    format: 'gen9randombattle',
    seed: SEED,
    observation_schema_version: 'observable-battle-state/v2' as const,
  };
  const primary = await createPipelineIntegrationSession(options);
  const control = await createPipelineIntegrationSession(options);
  const originalResetFromSerialized = LocalBattleEnv.prototype.resetFromSerialized;
  const originalStepSeededTransition = LocalBattleEnv.prototype.stepSeededTransition;
  const originalDiagnostics = LocalBattleEnv.prototype.diagnostics;
  const restoredSnapshots: string[] = [];
  const emittedDeltas: string[][] = [];
  try {
    assert.equal(primary.boundary.kind, 'joint_actionable');
    assert.equal(control.boundary.kind, 'joint_actionable');
    assertV2PerspectiveBoundary(primary.boundary);
    assertV2PerspectiveBoundary(control.boundary);
    assert.notDeepEqual(
      primary.boundary.perspectives.p1.observation.request,
      primary.boundary.perspectives.p2.observation.request,
    );

    LocalBattleEnv.prototype.resetFromSerialized = async function recordCandidateRestore(serialized, stepOptions) {
      if (this.id.includes('pipeline-step-0')) restoredSnapshots.push(JSON.stringify(serialized));
      return originalResetFromSerialized.call(this, serialized, stepOptions);
    };
    LocalBattleEnv.prototype.stepSeededTransition = async function recordCandidateDelta(request, stepOptions) {
      const result = await originalStepSeededTransition.call(this, request, stepOptions);
      if (this.id.includes('pipeline-step-0')) emittedDeltas.push([...result.metadata.emitted_log_delta]);
      return result;
    };

    const actions = actionPair(primary);
    const committed = committedBoundaryShape(primary.boundary);
    const stale = { ...actions.p1, rqid: (actions.p1.rqid ?? 0) + 1 };
    await assert.rejects(primary.step({ p1: stale, p2: actions.p2 }), /request ID does not match/);
    assert.deepEqual(committedBoundaryShape(primary.boundary), committed);

    const malformed = { ...actions.p1, index: 13, action_id: `act-${'0'.repeat(64)}` };
    await assert.rejects(primary.step({ p1: malformed, p2: actions.p2 }), /Canonical action index is invalid/);
    assert.deepEqual(committedBoundaryShape(primary.boundary), committed);

    const candidateEnvironmentId = `${options.battle_id}-pipeline-step-0`;
    let injectedCandidateFailure: 'choice' | 'environment' | null = null;
    LocalBattleEnv.prototype.diagnostics = function diagnosticsWithCandidateRejection() {
      const diagnostics = originalDiagnostics.call(this) as Record<string, unknown>;
      if (this.id !== candidateEnvironmentId || !injectedCandidateFailure) return diagnostics;
      if (injectedCandidateFailure === 'environment') {
        return { ...diagnostics, last_error: { message: 'injected environment error' } };
      }
      const players = diagnostics.players as Record<PlayerID, Record<string, unknown>>;
      return {
        ...diagnostics,
        players: { ...players, p1: { ...players.p1, last_choice_error: { message: 'injected rejection' } } },
      };
    };
    try {
      injectedCandidateFailure = 'choice';
      await assert.rejects(
        primary.step(actions),
        (error: Error) => error instanceof PipelineIntegrationError && error.code === 'pipeline/v1/rejected-action',
      );
      assert.deepEqual(committedBoundaryShape(primary.boundary), committed);

      injectedCandidateFailure = 'environment';
      await assert.rejects(primary.step(actions), (error: Error) => {
        assert.ok(error instanceof PipelineIntegrationError);
        assert.equal(error.code, 'pipeline/v1/rejected-action');
        assert.match(error.message, /simulator reported an environment error/);
        return true;
      });
      assert.deepEqual(committedBoundaryShape(primary.boundary), committed);
    } finally {
      injectedCandidateFailure = null;
      LocalBattleEnv.prototype.diagnostics = originalDiagnostics;
    }

    const primaryResult = await primary.step(actions);
    const controlResult = await control.step(actions);
    assertV2PerspectiveBoundary(primaryResult.boundary);
    assertV2PerspectiveBoundary(controlResult.boundary);
    assert.equal(primaryResult.transition_id, controlResult.transition_id);
    assert.equal(primaryResult.boundary.branch_id, controlResult.boundary.branch_id);
    assert.equal(primaryResult.boundary.state_fingerprint, controlResult.boundary.state_fingerprint);
    assert.equal(primaryResult.boundary.step_index, controlResult.boundary.step_index);
    assert.equal(primaryResult.boundary.step_index, committed.step_index + 1);
    assert.ok(restoredSnapshots.length >= 3);
    assert.ok(restoredSnapshots.every((snapshot) => snapshot === restoredSnapshots[0]));

    const normalizeDelta = (records: string[]) => records.map((record) => (
      /^\|t:\|\d+$/.test(record) ? '|t:|0' : record
    ));
    assert.ok(emittedDeltas.length >= 3);
    assert.deepEqual(
      normalizeDelta(emittedDeltas[emittedDeltas.length - 2]),
      normalizeDelta(emittedDeltas[emittedDeltas.length - 1]),
    );
    const records = {} as Record<PlayerID, Record<string, any>>;
    for (const player of ['p1', 'p2'] as const) {
      const primaryBundle = primaryResult.record_bundles[player];
      const controlBundle = controlResult.record_bundles[player];
      assert.equal(primaryBundle.action.action_id, actions[player].action_id);
      assert.equal(primaryBundle.action.action_id, controlBundle.action.action_id);
      assert.equal(primaryBundle.transition.transition_id, controlBundle.transition.transition_id);
      assert.equal(primaryBundle.transition.branch_id, controlBundle.transition.branch_id);
      assert.equal(primaryBundle.transition.output_state_fingerprint, controlBundle.transition.output_state_fingerprint);
      assert.equal(
        primaryResult.boundary.perspectives[player].observation.event_cursor,
        controlResult.boundary.perspectives[player].observation.event_cursor,
      );
      assert.equal(
        primaryResult.boundary.perspectives[player].observation.observation_id,
        controlResult.boundary.perspectives[player].observation.observation_id,
      );
      assert.equal(
        primaryResult.boundary.perspectives[player].belief.belief_id,
        controlResult.boundary.perspectives[player].belief.belief_id,
      );

      assert.equal(primaryBundle.input_observation.schema_version, 'observable-battle-state/v2');
      assert.equal(primaryBundle.successor_observation.schema_version, 'observable-battle-state/v2');
      assert.equal(primaryBundle.input_belief.observation.observation_id, primaryBundle.input_observation.observation_id);
      assert.equal(primaryBundle.successor_belief.observation.observation_id, primaryBundle.successor_observation.observation_id);
      assert.equal(primaryBundle.successor_belief.parent_belief_id, primaryBundle.input_belief.belief_id);
      assert.equal(primaryBundle.successor_belief.transition_lineage?.transition_id, primaryBundle.transition.transition_id);
      assert.equal(primaryBundle.successor_belief.transition_lineage?.parent_branch_id, primaryBundle.transition.parent_branch_id);
      assert.equal(primaryBundle.successor_belief.transition_lineage?.branch_id, primaryBundle.transition.branch_id);
      assert.equal(primaryBundle.successor_belief.transition_lineage?.input_observation_id, primaryBundle.input_observation.observation_id);
      assert.equal(primaryBundle.successor_belief.transition_lineage?.output_observation_id, primaryBundle.successor_observation.observation_id);
      assert.equal(primaryBundle.successor_belief.simulator_snapshot?.state_fingerprint, primaryBundle.transition.output_state_fingerprint);
      assert.deepEqual(
        primaryBundle.successor_observation.protocol_prefix.slice(0, primaryBundle.input_observation.event_cursor),
        primaryBundle.input_observation.protocol_prefix,
      );

      const checked = validateInPython(primaryBundle);
      assert.equal(checked.status, 0, checked.stderr);
      assert.notEqual(checked.stdout, '');
      const record = JSON.parse(checked.stdout) as Record<string, any>;
      records[player] = record;
      assert.equal(record.schema_fingerprints.observation, 'observable-battle-state/v2');
      assert.equal(record.perspective, player);
      assert.equal(record.observation_id, primaryBundle.input_observation.observation_id);
      assert.equal(record.belief_id, primaryBundle.input_belief.belief_id);
      assert.equal(record.action_id, primaryBundle.action.action_id);
      assert.equal(record.transition_id, primaryBundle.transition.transition_id);
      assert.equal(record.observation_cursor, primaryBundle.input_observation.event_cursor);
      assert.deepEqual(record.input_fields, []);
      assert.equal(record.private_data_provenance, 'acting_player_request');
      assert.equal(record.feature_input_eligibility, 'acting_player_private');
      assert.deepEqual(Object.keys(record).sort(), [
        'action_id', 'battle_id', 'belief_id', 'feature_cursor', 'feature_input_eligibility', 'input_fields',
        'observation_cursor', 'observation_id', 'observation_prefix_hash', 'parser_version', 'perspective',
        'private_data_provenance', 'record_id', 'replay_id', 'ruleset', 'schema_fingerprints', 'schema_version',
        'source_kind', 'source_ref', 'split', 'split_key', 'split_seed', 'transition_id',
      ]);
      assert.doesNotMatch(JSON.stringify(record), /raw_request|simulator_state|rng_seed|root_seed|private_team|opponent_private|future_events|omniscient|successor_observation/);

      const fresh = validateInPython(controlBundle);
      assert.equal(fresh.status, 0, fresh.stderr);
      assert.deepEqual(JSON.parse(fresh.stdout), record);
    }

    for (const player of ['p1', 'p2'] as const) {
      const bundle = primaryResult.record_bundles[player];
      const other = player === 'p1' ? 'p2' : 'p1';
      const mixedVersions = structuredClone(bundle) as Record<string, any>;
      mixedVersions.successor_observation.schema_version = 'observable-battle-state/v1';
      const wrongPerspective = structuredClone(bundle) as Record<string, any>;
      wrongPerspective.perspective = other;
      const brokenObservationReference = structuredClone(bundle) as Record<string, any>;
      brokenObservationReference.successor_belief.observation.observation_id = bundle.input_observation.observation_id;
      const brokenTransitionReference = structuredClone(bundle) as Record<string, any>;
      brokenTransitionReference.successor_belief.transition_lineage.transition_id = `transition-${'0'.repeat(64)}`;
      let nonExtension = structuredClone(bundle) as Record<string, any>;
      nonExtension.successor_observation.protocol_prefix[0] = '|turn|999';
      nonExtension.successor_observation.protocol_prefix_hash = typeScriptDigest(nonExtension.successor_observation.protocol_prefix);
      nonExtension = rehashSuccessorObservationAndBelief(nonExtension);
      const privatePayload = structuredClone(bundle) as Record<string, any>;
      privatePayload.raw_request = { side: { pokemon: [] } };
      const malformedIdentity = structuredClone(bundle) as Record<string, any>;
      malformedIdentity.action.action_id = 'act-malformed';
      for (const [label, candidate, reason] of [
        ['rehashed-public-stage', rehashedSuccessorPublicStage(bundle), /Invalid public-stage evidence/],
        ['mixed-observation-versions', mixedVersions, /Mixed observation schemas/],
        ['wrong-perspective', wrongPerspective, /perspective disagrees with record/],
        ['broken-observation-reference', brokenObservationReference, /successor belief does not reference/],
        ['broken-transition-reference', brokenTransitionReference, /transition lineage does not match/],
        ['non-extension-successor-prefix', nonExtension, /not an exact extension/],
        ['forbidden-private-payload', privatePayload, /private or raw simulator data/],
        ['malformed-identity', malformedIdentity, /canonical action ID is malformed/],
      ] as const) {
        assertPythonRejectsWithoutPublication(candidate, `${player}/${label}`, reason);
      }
    }
    assert.notEqual(records.p1.record_id, records.p2.record_id);
  } finally {
    LocalBattleEnv.prototype.resetFromSerialized = originalResetFromSerialized;
    LocalBattleEnv.prototype.stepSeededTransition = originalStepSeededTransition;
    LocalBattleEnv.prototype.diagnostics = originalDiagnostics;
    await primary.close();
    await control.close();
  }
});

test('v2 voluntary switch-plus-switch remains a joint request pair with deterministic publication', async () => {
  const options = {
    battle_id: 'pipeline-v2-voluntary-switch-pair-v1',
    format: 'gen9randombattle',
    seed: SEED,
    observation_schema_version: 'observable-battle-state/v2' as const,
  };
  const stepOptions = { view_players: ['p1', 'p2'] as PlayerID[], include_log_delta: true, include_possible_roles: false, include_wait_requests: true };
  const direct = new LocalBattleEnv('pipeline-v2-voluntary-switch-pair-direct', options.format, [...options.seed]);
  let session: Awaited<ReturnType<typeof createPipelineIntegrationSession>> | null = null;
  let twin: Awaited<ReturnType<typeof createPipelineIntegrationSession>> | null = null;
  let beforeRestored: LocalBattleEnv | null = null;
  let afterRestored: LocalBattleEnv | null = null;
  try {
    const directInitial = await direct.resetWithOptions(stepOptions);
    const prefix = [...directInitial.log_delta];
    const serializedBefore = structuredClone(direct.captureSeededSnapshot(null).simulator_state);
    beforeRestored = new LocalBattleEnv('pipeline-v2-voluntary-switch-pair-before', options.format, [...options.seed]);
    const beforeReplay = await beforeRestored.resetFromSerialized(serializedBefore, stepOptions);
    const projectedBefore = projectPipelineStepResult(
      directInitial, options.battle_id, projectPipelineProtocolPrefix(prefix), options.observation_schema_version,
    );
    assert.deepEqual(
      projectPipelineStepResult(beforeReplay, options.battle_id, projectPipelineProtocolPrefix(prefix), options.observation_schema_version),
      projectedBefore,
    );
    assert.equal(beforeRestored.captureSeededSnapshot(null).state_fingerprint, direct.captureSeededSnapshot(null).state_fingerprint);

    const reset = LocalBattleEnv.prototype.resetWithOptions;
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (requestOptions) {
        return this.resetFromSerialized(structuredClone(serializedBefore), requestOptions);
      };
      session = await createPipelineIntegrationSession(options);
      twin = await createPipelineIntegrationSession(options);
    } finally {
      LocalBattleEnv.prototype.resetWithOptions = reset;
    }
    const selectSwitch = (target: NonNullable<typeof session>, player: PlayerID) => {
      const request = target.boundary.perspectives[player].observation.request!;
      const action = request.legal_actions.actions.find((candidate) => candidate?.kind === 'switch');
      assert.ok(action, `${player} must have an owner-authorized voluntary switch`);
      return canonicalActionFromLegalAction(request, action.index);
    };
    assert.ok(session && twin);
    assert.deepEqual(
      Object.fromEntries(['p1', 'p2'].map((player) => [player, session!.boundary.perspectives[player as PlayerID].observation])),
      projectedBefore,
      'the pipeline starts from the same serialized request boundary',
    );
    const actions = { p1: selectSwitch(session, 'p1'), p2: selectSwitch(session, 'p2') };
    const before = committedBoundaryShape(session.boundary);
    assert.equal(session.boundary.kind, 'joint_actionable');
    assert.equal(actions.p1.kind, 'switch');
    assert.equal(actions.p2.kind, 'switch');
    assert.equal(session.boundary.perspectives.p1.observation.request?.force_switch, false);
    assert.equal(session.boundary.perspectives.p2.observation.request?.force_switch, false);
    assert.notDeepEqual(
      session.boundary.perspectives.p1.observation.request,
      session.boundary.perspectives.p2.observation.request,
      'each perspective retains only its own request',
    );

    await assert.rejects(
      session.step({ p1: { ...actions.p1, rqid: (actions.p1.rqid ?? 0) + 1 }, p2: actions.p2 }),
      /request ID does not match/,
    );
    assert.deepEqual(committedBoundaryShape(session.boundary), before);

    const result = await session.step(actions);
    const repeated = await twin.step({ p1: selectSwitch(twin, 'p1'), p2: selectSwitch(twin, 'p2') });
    const directResult = await direct.stepWithOptions({ p1: actions.p1.choice, p2: actions.p2.choice }, stepOptions);
    prefix.push(...directResult.log_delta);
    const projectedAfter = projectPipelineStepResult(
      directResult, options.battle_id, projectPipelineProtocolPrefix(prefix), options.observation_schema_version,
    );
    assert.deepEqual(
      Object.fromEntries(['p1', 'p2'].map((player) => [player, result.boundary.perspectives[player as PlayerID].observation])),
      projectedAfter,
    );
    const serializedAfter = structuredClone(direct.captureSeededSnapshot(null).simulator_state);
    afterRestored = new LocalBattleEnv('pipeline-v2-voluntary-switch-pair-after', options.format, [...options.seed]);
    const afterReplay = await afterRestored.resetFromSerialized(serializedAfter, stepOptions);
    assert.deepEqual(
      projectPipelineStepResult(afterReplay, options.battle_id, projectPipelineProtocolPrefix(prefix), options.observation_schema_version),
      projectedAfter,
    );
    assert.equal(afterRestored.captureSeededSnapshot(null).state_fingerprint, direct.captureSeededSnapshot(null).state_fingerprint);
    assert.equal(result.transition_id, repeated.transition_id);
    assert.equal(result.boundary.branch_id, repeated.boundary.branch_id);
    assert.equal(result.boundary.state_fingerprint, repeated.boundary.state_fingerprint);
    assert.equal(result.boundary.step_index, before.step_index + 1);
    assertV2PerspectiveBoundary(result.boundary);
    for (const player of ['p1', 'p2'] as const) {
      const bundle = result.record_bundles[player];
      assert.equal(bundle.action.kind, 'switch');
      assert.equal(bundle.transition.transition_id, result.transition_id);
      assert.equal(bundle.successor_belief.transition_lineage?.transition_id, result.transition_id);
      assert.equal(bundle.successor_observation.event_cursor, result.boundary.perspectives[player].observation.event_cursor);
      assert.equal(bundle.successor_observation.observation_id, repeated.boundary.perspectives[player].observation.observation_id);
      assert.equal(validateInPython(bundle).status, 0);
      assert.ok(!JSON.stringify(bundle).includes('|request|'));
    }
  } finally {
    await session?.close();
    await twin?.close();
    await beforeRestored?.close();
    await afterRestored?.close();
    await direct.close();
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
    assert.deepEqual(projectPipelineProtocolPrefix(['|gen|9\n', '|', '|turn|1\r\n']), ['|gen|9', '|turn|1']);
    for (const emptySegment of ['', '\n', '\r\n']) {
      assert.throws(
        () => projectPipelineProtocolPrefix(['|gen|9', emptySegment, '|turn|1']),
        (error: Error) => error instanceof PipelineIntegrationError
          && error.code === 'pipeline/v1/unsupported-protocol-record',
      );
    }
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

    const directProjection = projectPipelineStepResult(result, 'pipeline-protocol-boundary', [
      ...basePrefix, '|request|{"private":true}', '|tier|[Gen 9] Random Battle', '|',
    ]);
    for (const player of ['p1', 'p2'] as const) {
      assert.ok(!directProjection[player].protocol_prefix.some((line) => line.startsWith('|tier|') || line === '|'));
      assert.ok(directProjection[player].protocol_prefix.includes('|request|{}'));
      assert.ok(!directProjection[player].protocol_prefix.some((line) => line.includes('private')));
    }
    for (const record of ['|request|not-json', '|tier|']) {
      assert.throws(() => projectPipelineStepResult(result, 'pipeline-protocol-boundary', [...basePrefix, record]),
        (error: Error) => error instanceof PipelineIntegrationError
          && error.code === 'pipeline/v1/unsupported-observable-protocol');
    }
  } finally {
    await env.close();
  }
});

test('rejected protocol candidates preserve committed state, lineage and the next transition', async () => {
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
        active_slots: { ...state.observation.view.active },
      }];
    })),
  };
  const originalStepSeededTransition = LocalBattleEnv.prototype.stepSeededTransition;
  let injectedRecord = '|clearstatus|legacy-token';
  try {
    LocalBattleEnv.prototype.stepSeededTransition = async function (request, options) {
      const result = await originalStepSeededTransition.call(this, request, options);
      return {
        ...result,
        metadata: {
          ...result.metadata,
          emitted_log_delta: [...result.metadata.emitted_log_delta, injectedRecord],
        },
      };
    };
    for (const testCase of [
      { record: '', code: 'pipeline/v1/unsupported-protocol-record' },
      { record: '\n', code: 'pipeline/v1/unsupported-protocol-record' },
      { record: '|clearstatus|legacy-token', code: 'pipeline/v1/unresolved-protocol-alias' },
      { record: '|futuremechanic|opaque', code: 'pipeline/v1/unsupported-observable-protocol' },
      ...PROTOCOL_CONTRACT.rejection_fixtures.filter((fixture) => fixture.record.startsWith('|-singlemove'))
        .map(({ record }) => ({ record, code: 'pipeline/v1/unsupported-observable-protocol' })),
      { record: '|-singleturn|p1a: Pikachu|Future Mechanic', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-singleturn|p1a: Pikachu|move: Follow Me|[of] p2a: Eevee', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-singleturn|p1a: Pikachu|Helping Hand|[of] p2a:Eevee', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-singleturn|p1a: Pikachu|Helping Hand|[of] p1: Eevee', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-singleturn|p1a: Pikachu|Helping Hand|[of] p2: Eevee', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-singleturn|p1a: Pikachu|Helping Hand|[of] p: Eevee', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-singleturn|p1a: Pikachu|Helping Hand|[of]', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-singleturn|p1a: Pikachu|Helping Hand|[of] Eevee', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-singleturn|p1a: Pikachu|Helping Hand|[of] p2a: Eevee ', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-boost|bad ident|atk|1', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|faint|p1a: Pikachu ', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-clearboost|p1a: Pikachu ', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-endability|p1a: Pikachu ', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-transform|p1a: Ditto|p2a: Gengar ', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-transform|p1a: Ditto|p2a:\tGengar', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-heal|p1:Eevee|50/100|[from] move: Revival Blessing', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|request|not-json', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|request|{"rqid":null}', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|tier|', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-damage|p1a: Pikachu|garbage', code: 'pipeline/v1/unsupported-observable-protocol' },
      { record: '|-boost|p1a: Pikachu|banana|1000', code: 'pipeline/v1/unsupported-observable-protocol' },
    ]) {
      injectedRecord = testCase.record;
      await assert.rejects(session.step(), (error: Error) => error instanceof PipelineIntegrationError
        && error.code === testCase.code);
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
            active_slots: { ...state.observation.view.active },
          }];
        })),
      }, committedLineage);
    }
    LocalBattleEnv.prototype.stepSeededTransition = originalStepSeededTransition;
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
