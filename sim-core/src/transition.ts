import { createHash } from 'node:crypto';
import {
  canonicalActionToChoice,
  type CanonicalAction,
} from './canonical_action';
import { isObservableSchema, type ObservableBattleState } from './observable_state';
import type { ChoiceRequestView, PlayerID, StepResult } from './types';

export const SEEDED_TRANSITION_SCHEMA_VERSION = 'seeded-transition/v1' as const;
export const SEEDED_FORCED_SWITCH_SCHEMA_VERSION = 'seeded-forced-switch/v1' as const;
export const SEEDED_REVIVAL_SCHEMA_VERSION = 'seeded-revival/v1' as const;
export const SIMULATOR_REVISION = 'sim-core@0.1.0+pokemon-showdown@0.11.10' as const;
export type RootSeed = [number, number, number, number];

export interface SeededBattleSnapshot {
  schema_version: typeof SEEDED_TRANSITION_SCHEMA_VERSION;
  format: string;
  root_seed: RootSeed;
  state_fingerprint: string;
  parent_branch_id: string | null;
  transition_id: string | null;
  branch_id: string;
  simulator_state: Record<string, unknown>;
}

export interface SeededSnapshotRef {
  schema_version: typeof SEEDED_TRANSITION_SCHEMA_VERSION;
  snapshot_handle: string;
  format: string;
  root_seed: RootSeed;
  state_fingerprint: string;
  parent_branch_id: string | null;
  transition_id: string | null;
  branch_id: string;
}

export interface SeededTransitionRequest {
  schema_version: typeof SEEDED_TRANSITION_SCHEMA_VERSION;
  snapshot: SeededBattleSnapshot;
  observations: Record<PlayerID, ObservableBattleState>;
  actions: Record<PlayerID, CanonicalAction>;
  step_index: number;
}

export interface SeededTransitionWireRequest {
  schema_version: typeof SEEDED_TRANSITION_SCHEMA_VERSION;
  snapshot: SeededSnapshotRef;
  observations: Record<PlayerID, ObservableBattleState>;
  actions: Record<PlayerID, CanonicalAction>;
  step_index: number;
}

export interface SeededTransitionMetadata {
  schema_version: typeof SEEDED_TRANSITION_SCHEMA_VERSION;
  transition_id: string;
  parent_branch_id: string;
  branch_id: string;
  input_state_fingerprint: string;
  output_state_fingerprint: string;
  root_seed: RootSeed;
  action_ids: Record<PlayerID, string>;
  emitted_log_delta: string[];
  simulator_revision: typeof SIMULATOR_REVISION;
  step_index: number;
}

export interface SeededTransitionResult {
  metadata: SeededTransitionMetadata;
  step_result: StepResult;
  output_snapshot: SeededBattleSnapshot;
}

export interface ForcedSwitchRoles {
  acting_player: PlayerID;
  waiting_player: PlayerID;
}

export interface SeededForcedSwitchRequest extends ForcedSwitchRoles {
  schema_version: typeof SEEDED_FORCED_SWITCH_SCHEMA_VERSION | typeof SEEDED_REVIVAL_SCHEMA_VERSION;
  snapshot: SeededBattleSnapshot;
  observations: Record<PlayerID, ObservableBattleState>;
  actions: Partial<Record<PlayerID, CanonicalAction>>;
  step_index: number;
}

export interface SeededForcedSwitchMetadata extends Omit<SeededTransitionMetadata, 'schema_version' | 'action_ids'>, ForcedSwitchRoles {
  schema_version: typeof SEEDED_FORCED_SWITCH_SCHEMA_VERSION | typeof SEEDED_REVIVAL_SCHEMA_VERSION;
  action_ids: Partial<Record<PlayerID, string>>;
}

export interface SeededForcedSwitchResult extends Omit<SeededTransitionResult, 'metadata'> {
  metadata: SeededForcedSwitchMetadata;
}

export type PipelineTransitionMetadata = SeededTransitionMetadata | SeededForcedSwitchMetadata;

export function assertForcedSwitchRoles(roles: ForcedSwitchRoles): void {
  if (!['p1', 'p2'].includes(roles.acting_player) || !['p1', 'p2'].includes(roles.waiting_player)
    || roles.acting_player === roles.waiting_player) throw new Error('Forced-switch roles must identify distinct p1/p2 players.');
}

/** Read only the acting player's simulator-provided request, never hidden counters. */
export function assertOrdinaryForcedSwitch(request: ChoiceRequestView): void {
  if (!request.force_switch || request.wait || request.team_preview) throw new Error('An ordinary forced-switch request is required.');
  const raw = request.raw as { side?: { pokemon?: { reviving?: boolean }[] } } | null;
  if (raw?.side?.pokemon?.some((pokemon) => pokemon.reviving)) {
    throw new Error('seeded-forced-switch/v1/unsupported-revival-blessing');
  }
}

/** Only a live singles reviver and one or more fainted, non-active targets. */
export function assertRevivalSelection(request: Pick<ChoiceRequestView, 'force_switch' | 'wait' | 'team_preview' | 'side' | 'legal_actions'>): void {
  const revivers = request.side.filter(p => p.reviving === true);
  const targets = request.side.filter(p => !p.active && /(?:^| )fnt$/.test(p.condition));
  if (!request.force_switch || request.wait || request.team_preview || request.side.length > 6
    || revivers.length !== 1 || !revivers[0].active || /(?:^| )fnt$/.test(revivers[0].condition)
    || request.side.filter(p => p.active).length !== 1 || !targets.length
    || request.side.some((p, index) => p.slot !== index + 1)
    || request.legal_actions.actions.length !== 13 || request.legal_actions.mask.length !== 13
    || request.legal_actions.mask.filter(Boolean).length !== targets.length
    || request.legal_actions.actions.filter(Boolean).length !== targets.length
    || request.legal_actions.available_indices.length !== targets.length) {
    throw new Error('seeded-revival/v1/unsupported-request');
  }
  for (const [offset, target] of targets.entries()) {
    const action = request.legal_actions.actions[8 + offset];
    if (target.slot !== request.side.indexOf(target) + 1 || !request.legal_actions.mask[8 + offset]
      || action?.kind !== 'revive' || action.slot !== target.slot || action.choice !== `switch ${target.slot}`
      || request.legal_actions.available_indices[offset] !== 8 + offset) throw new Error('seeded-revival/v1/unsupported-request');
  }
}

export interface SeededTransitionPublicResult {
  metadata: SeededTransitionMetadata;
  step_result: StepResult;
  output_snapshot: SeededSnapshotRef;
}

function canonicalSimulatorState(simulatorState: Record<string, unknown>): Record<string, unknown> {
  const normalized = structuredClone(simulatorState);
  if (Array.isArray(normalized.log)) {
    normalized.log = normalized.log.map((record) => (
      typeof record === 'string' && /^\|t:\|\d+$/.test(record) ? '|t:|<timestamp>' : record
    ));
  }
  return normalized;
}

function canonicalize(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value as Record<string, unknown>).sort().map((key) => `${JSON.stringify(key)}:${canonicalize((value as Record<string, unknown>)[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function digest(value: unknown): string {
  return createHash('sha256').update(canonicalize(value), 'utf8').digest('hex');
}

function assertSeed(seed: readonly number[]): asserts seed is RootSeed {
  if (seed.length !== 4 || seed.some((value) => !Number.isSafeInteger(value))) {
    throw new Error('Seeded transition root_seed must contain four safe integers.');
  }
}

function deriveBranchId(
  parentBranchId: string | null,
  rootSeed: RootSeed,
  stateFingerprint: string,
  transitionId: string | null,
): string {
  return `branch-${digest({
    schema_version: SEEDED_TRANSITION_SCHEMA_VERSION,
    parent_branch_id: parentBranchId,
    root_seed: [...rootSeed],
    state_fingerprint: stateFingerprint,
    transition_id: transitionId,
  })}`;
}

function assertSnapshot(snapshot: SeededBattleSnapshot): void {
  if (snapshot.schema_version !== SEEDED_TRANSITION_SCHEMA_VERSION) throw new Error('Unsupported seeded transition schema.');
  if (!snapshot.format.trim()) throw new Error('Seeded transition snapshot format must not be empty.');
  assertSeed(snapshot.root_seed);
  if (!/^[a-f0-9]{64}$/.test(snapshot.state_fingerprint)) throw new Error('Seeded transition state fingerprint is invalid.');
  if (!snapshot.branch_id.trim()) throw new Error('Seeded transition branch_id must not be empty.');
  if (snapshot.transition_id !== null && !snapshot.transition_id.trim()) {
    throw new Error('Seeded transition transition_id must be null or non-empty.');
  }
  if (!snapshot.simulator_state || typeof snapshot.simulator_state !== 'object' || Array.isArray(snapshot.simulator_state)) {
    throw new Error('Seeded transition simulator_state must be an object.');
  }
  if (fingerprintSimulatorState(snapshot.simulator_state) !== snapshot.state_fingerprint) {
    throw new Error('Seeded transition snapshot fingerprint does not match simulator_state.');
  }
  if (snapshot.branch_id !== deriveBranchId(snapshot.parent_branch_id, snapshot.root_seed, snapshot.state_fingerprint, snapshot.transition_id)) {
    throw new Error('Seeded transition branch_id does not match authoritative snapshot lineage.');
  }
}

export function fingerprintSimulatorState(simulatorState: Record<string, unknown>): string {
  return digest(canonicalSimulatorState(simulatorState));
}

export function createSeededBattleSnapshot(
  format: string,
  rootSeed: readonly number[],
  simulatorState: Record<string, unknown>,
  parentBranchId: string | null,
  transitionId: string | null = null,
): SeededBattleSnapshot {
  assertSeed(rootSeed);
  const state_fingerprint = fingerprintSimulatorState(simulatorState);
  const branch_id = deriveBranchId(parentBranchId, [...rootSeed], state_fingerprint, transitionId);
  return {
    schema_version: SEEDED_TRANSITION_SCHEMA_VERSION,
    format,
    root_seed: [...rootSeed],
    state_fingerprint,
    parent_branch_id: parentBranchId,
    transition_id: transitionId,
    branch_id,
    simulator_state: structuredClone(simulatorState),
  };
}

export function toSeededSnapshotRef(snapshot: SeededBattleSnapshot, snapshotHandle: string): SeededSnapshotRef {
  assertSnapshot(snapshot);
  if (!snapshotHandle.trim()) throw new Error('Seeded transition snapshot handle must not be empty.');
  return {
    schema_version: snapshot.schema_version,
    snapshot_handle: snapshotHandle,
    format: snapshot.format,
    root_seed: [...snapshot.root_seed],
    state_fingerprint: snapshot.state_fingerprint,
    parent_branch_id: snapshot.parent_branch_id,
    transition_id: snapshot.transition_id,
    branch_id: snapshot.branch_id,
  };
}

function exactPlayers(record: Record<PlayerID, unknown>, label: string): void {
  const keys = Object.keys(record).sort();
  if (keys.length !== 2 || keys[0] !== 'p1' || keys[1] !== 'p2') {
    throw new Error(`Seeded transition ${label} must contain exactly p1 and p2.`);
  }
}

export function validateSeededTransitionRequest(request: SeededTransitionRequest): void {
  if (!request.observations || !isObservableSchema(request.observations.p1?.schema_version)
    || request.observations.p1.schema_version !== request.observations.p2?.schema_version) throw new Error('Unsupported or mixed observation schemas.');
  if (request.schema_version !== SEEDED_TRANSITION_SCHEMA_VERSION) throw new Error('Unsupported seeded transition schema.');
  assertSnapshot(request.snapshot);
  if (!Number.isSafeInteger(request.step_index) || request.step_index < 0) throw new Error('Seeded transition step_index is invalid.');
  exactPlayers(request.observations, 'observations');
  exactPlayers(request.actions, 'actions');
  for (const player of ['p1', 'p2'] as const) {
    const observation = request.observations[player];
    const action = request.actions[player];
    if (action.kind === 'revive' || observation.request?.side.some(p => p.reviving)) throw new Error('Revival requires seeded-revival/v1.');
    if (observation.perspective !== player || observation.request?.player !== player) {
      throw new Error(`Seeded transition observation perspective mismatch for ${player}.`);
    }
    if (!observation.request || !observation.decision_availability.available) {
      throw new Error(`Seeded transition ${player} request is not actionable.`);
    }
    if (!observation.decision_availability.legal_action_indices?.includes(action.index)) {
      throw new Error(`Seeded transition action is unavailable for ${player}.`);
    }
    canonicalActionToChoice(action, {
      player,
      rqid: observation.request.rqid,
      force_switch: observation.request.force_switch,
      legal_actions: observation.request.legal_actions, side: observation.request.side,
    });
  }
}

export function buildSeededTransitionResult(
  request: SeededTransitionRequest,
  outputSnapshot: SeededBattleSnapshot,
  stepResult: StepResult,
): SeededTransitionResult {
  validateSeededTransitionRequest(request);
  const action_ids = { p1: request.actions.p1.action_id, p2: request.actions.p2.action_id };
  const transition_id = `transition-${digest({
    schema_version: request.schema_version,
    parent_branch_id: request.snapshot.branch_id,
    input_state_fingerprint: request.snapshot.state_fingerprint,
    output_state_fingerprint: outputSnapshot.state_fingerprint,
    root_seed: request.snapshot.root_seed,
    action_ids,
    simulator_revision: SIMULATOR_REVISION,
    step_index: request.step_index,
  })}`;
  const branch_id = deriveBranchId(
    request.snapshot.branch_id,
    request.snapshot.root_seed,
    outputSnapshot.state_fingerprint,
    transition_id,
  );
  const metadata: SeededTransitionMetadata = {
    schema_version: SEEDED_TRANSITION_SCHEMA_VERSION,
    transition_id,
    parent_branch_id: request.snapshot.branch_id,
    branch_id,
    input_state_fingerprint: request.snapshot.state_fingerprint,
    output_state_fingerprint: outputSnapshot.state_fingerprint,
    root_seed: [...request.snapshot.root_seed],
    action_ids,
    emitted_log_delta: [...stepResult.log_delta],
    simulator_revision: SIMULATOR_REVISION,
    step_index: request.step_index,
  };
  const authoritativeOutputSnapshot = {
    ...outputSnapshot,
    transition_id,
    branch_id: deriveBranchId(outputSnapshot.parent_branch_id, outputSnapshot.root_seed, outputSnapshot.state_fingerprint, transition_id),
  };
  if (authoritativeOutputSnapshot.branch_id !== branch_id) {
    throw new Error('Seeded transition branch lineage derivation is inconsistent.');
  }
  return { metadata, step_result: stepResult, output_snapshot: authoritativeOutputSnapshot };
}

export function toSeededTransitionPublicResult(
  result: SeededTransitionResult,
  snapshotHandle: string,
): SeededTransitionPublicResult {
  return {
    metadata: result.metadata,
    step_result: result.step_result,
    output_snapshot: toSeededSnapshotRef(result.output_snapshot, snapshotHandle),
  };
}

export function validateSeededForcedSwitchRequest(request: SeededForcedSwitchRequest): void {
  if (!request.observations || !isObservableSchema(request.observations.p1?.schema_version)
    || request.observations.p1.schema_version !== request.observations.p2?.schema_version) throw new Error('Unsupported or mixed observation schemas.');
  if (request.schema_version !== SEEDED_FORCED_SWITCH_SCHEMA_VERSION && request.schema_version !== SEEDED_REVIVAL_SCHEMA_VERSION) throw new Error('Unsupported forced-switch transition schema.');
  if (Object.keys(request).sort().join(',') !== 'acting_player,actions,observations,schema_version,snapshot,step_index,waiting_player') {
    throw new Error('Forced-switch transition fields are not exact.');
  }
  assertSnapshot(request.snapshot);
  assertForcedSwitchRoles(request);
  if (request.snapshot.format !== 'gen9randombattle') throw new Error('Forced-switch transition only supports gen9randombattle.');
  if (!Number.isSafeInteger(request.step_index) || request.step_index < 0) throw new Error('Forced-switch step_index is invalid.');
  exactPlayers(request.observations, 'observations');
  if (Object.keys(request.actions).join(',') !== request.acting_player) throw new Error('Forced-switch actions must contain only the acting player.');
  const actor = request.observations[request.acting_player];
  const waiting = request.observations[request.waiting_player];
  for (const player of ['p1', 'p2'] as const) {
    const observation = request.observations[player];
    if (observation.perspective !== player || observation.request?.player !== player
      || observation.view.player !== player || observation.source_kind !== 'sim_core'
      || observation.view.terminated || observation.view.format !== request.snapshot.format) {
      throw new Error('Forced-switch observation does not match its live perspective/format.');
    }
  }
  if (actor.battle_id !== waiting.battle_id) throw new Error('Forced-switch observations belong to different battles.');
  if (!actor.request?.force_switch || actor.request.wait || actor.request.team_preview
    || !actor.decision_availability.available || actor.decision_availability.reason !== 'request'
    || actor.snapshot_phase !== 'forced_switch') {
    throw new Error('Forced-switch actor observation must have an actionable forced-switch request.');
  }
  if (!waiting.request?.wait || waiting.request.force_switch || waiting.request.team_preview
    || waiting.decision_availability.available || waiting.decision_availability.reason !== 'waiting'
    || waiting.snapshot_phase !== 'post_resolution'
    || waiting.request.legal_actions.available_indices.length
    || waiting.request.legal_actions.mask.some(Boolean) || waiting.request.legal_actions.actions.some(Boolean)) {
    throw new Error('Forced-switch partner must have a genuine wait request without actions.');
  }
  const revival = actor.request.side.some(p => p.reviving);
  if (revival !== (request.schema_version === SEEDED_REVIVAL_SCHEMA_VERSION)) throw new Error('Revival transition schema does not match request.');
  if (revival) assertRevivalSelection(actor.request);
  const action = request.actions[request.acting_player]!;
  if (action.kind !== (request.schema_version === SEEDED_REVIVAL_SCHEMA_VERSION ? 'revive' : 'switch') || !actor.decision_availability.legal_action_indices?.includes(action.index)) {
    throw new Error('Forced-switch action must be an available switch.');
  }
  canonicalActionToChoice(action, {
    player: request.acting_player, rqid: actor.request.rqid,
    force_switch: true, legal_actions: actor.request.legal_actions, side: actor.request.side,
  });
}

export function buildSeededForcedSwitchResult(
  request: SeededForcedSwitchRequest,
  outputSnapshot: SeededBattleSnapshot,
  stepResult: StepResult,
): SeededForcedSwitchResult {
  validateSeededForcedSwitchRequest(request);
  assertSnapshot(outputSnapshot);
  if (outputSnapshot.parent_branch_id !== request.snapshot.branch_id
    || outputSnapshot.format !== request.snapshot.format
    || canonicalize(outputSnapshot.root_seed) !== canonicalize(request.snapshot.root_seed)) {
    throw new Error('Forced-switch output snapshot lineage is inconsistent.');
  }
  const identity = {
    schema_version: request.schema_version,
    acting_player: request.acting_player,
    waiting_player: request.waiting_player,
    parent_branch_id: request.snapshot.branch_id,
    input_state_fingerprint: request.snapshot.state_fingerprint,
    output_state_fingerprint: outputSnapshot.state_fingerprint,
    root_seed: [...request.snapshot.root_seed] as RootSeed,
    action_ids: { [request.acting_player]: request.actions[request.acting_player]!.action_id },
    simulator_revision: SIMULATOR_REVISION,
    step_index: request.step_index,
  };
  const transition_id = `transition-${digest(identity)}`;
  const output = createSeededBattleSnapshot(outputSnapshot.format, outputSnapshot.root_seed,
    outputSnapshot.simulator_state, request.snapshot.branch_id, transition_id);
  return {
    metadata: { ...identity, transition_id, branch_id: output.branch_id, emitted_log_delta: [...stepResult.log_delta] },
    step_result: stepResult,
    output_snapshot: output,
  };
}
