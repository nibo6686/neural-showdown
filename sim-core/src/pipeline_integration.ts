import { canonicalActionFromLegalAction, serializeCanonicalAction, type CanonicalAction } from './canonical_action';
import { projectBeliefState, serializeBeliefState, type BeliefState } from './belief_state';
import { LocalBattleEnv } from './env_manager';
import {
  OBSERVABLE_STATE_SCHEMA_VERSION,
  projectStepResult,
  type ObservableBattleState,
} from './observable_state';
import {
  SEEDED_TRANSITION_SCHEMA_VERSION,
  toSeededSnapshotRef,
  type SeededBattleSnapshot,
  type SeededTransitionMetadata,
} from './transition';
import type { ChoiceRequestView, PlayerID, StepResult } from './types';
import { PLAYERS } from './types';

export const PIPELINE_INTEGRATION_SCHEMA_VERSION = 'pipeline-integration/v1' as const;
export const PIPELINE_BUNDLE_SCHEMA_VERSION = 'pipeline-linked-record/v1' as const;
export const PIPELINE_TRANSITION_REFERENCE_SCHEMA_VERSION = 'pipeline-transition-reference/v1' as const;
export const PIPELINE_PREFIX_POLICY_VERSION = 'sim-core-observable-prefix/v1' as const;

const OPTIONS = {
  view_players: [...PLAYERS],
  include_log_delta: true,
  include_possible_roles: false,
};

export type PipelineBoundaryKind =
  | 'joint_actionable'
  | 'one_sided_forced_switch'
  | 'one_sided_requestless'
  | 'waiting'
  | 'requestless'
  | 'terminal';

export interface PipelinePerspectiveState {
  observation: ObservableBattleState;
  belief: BeliefState;
}

export interface PipelineBoundary {
  schema_version: typeof PIPELINE_INTEGRATION_SCHEMA_VERSION;
  battle_id: string;
  step_index: number;
  kind: PipelineBoundaryKind;
  branch_id: string;
  state_fingerprint: string;
  perspectives: Record<PlayerID, PipelinePerspectiveState>;
}

export interface PipelineTransitionReference {
  schema_version: typeof PIPELINE_TRANSITION_REFERENCE_SCHEMA_VERSION;
  transition_id: string;
  parent_branch_id: string;
  branch_id: string;
  input_state_fingerprint: string;
  output_state_fingerprint: string;
  simulator_revision: string;
  step_index: number;
  action_id: string;
}

export interface PipelineLinkedRecordBundle {
  schema_version: typeof PIPELINE_BUNDLE_SCHEMA_VERSION;
  battle_id: string;
  source_ref: string;
  ruleset: string;
  perspective: PlayerID;
  input_observation: ObservableBattleState;
  input_belief: BeliefState;
  action: CanonicalAction;
  transition: PipelineTransitionReference;
  successor_observation: ObservableBattleState;
  successor_belief: BeliefState;
}

export interface PipelineStepResult {
  boundary: PipelineBoundary;
  transition_id: string;
  record_bundles: Record<PlayerID, PipelineLinkedRecordBundle>;
}

export interface PipelineIntegrationOptions {
  battle_id: string;
  format: string;
  seed: readonly number[];
}

export class PipelineIntegrationError extends Error {
  readonly code: string;

  constructor(code: string, detail: string) {
    super(`${code}: ${detail}`);
    this.code = code;
  }
}

function freeze<T>(value: T): T {
  if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
  Object.freeze(value);
  for (const child of Object.values(value as Record<string, unknown>)) freeze(child);
  return value;
}

/**
 * PIPELINE-001 v1 prefix projection: retain spectator protocol events, normalize
 * wall-clock timestamps, omit framing-only and ruleset-label records, and omit
 * private request payloads (the acting player's request remains in its
 * ObservableBattleState). The format field carries the ruleset label.
 */
export function projectPipelineProtocolPrefix(records: readonly string[]): string[] {
  const projected: string[] = [];
  for (const raw of records) {
    const line = raw.replace(/\r\n?/g, '\n').trim();
    if (!line || line === '|') continue;
    if (!line.startsWith('|')) {
      throw new PipelineIntegrationError('pipeline/v1/unsupported-protocol-record', 'spectator output contained a non-protocol line');
    }
    if (line.startsWith('|request|')) continue;
    if (line.startsWith('|tier|')) continue;
    projected.push(line.replace(/^\|t:\|\d+$/, '|t:|0'));
  }
  return projected;
}

export function classifyPipelineBoundary(
  observations: Record<PlayerID, ObservableBattleState>,
): PipelineBoundaryKind {
  if (observations.p1.view.terminated || observations.p2.view.terminated) return 'terminal';
  const p1 = observations.p1.decision_availability.available;
  const p2 = observations.p2.decision_availability.available;
  if (p1 && p2) return 'joint_actionable';
  if (p1 !== p2) {
    const actionable = p1 ? observations.p1 : observations.p2;
    return actionable.request?.force_switch ? 'one_sided_forced_switch' : 'one_sided_requestless';
  }
  if (observations.p1.decision_availability.reason === 'waiting'
    || observations.p2.decision_availability.reason === 'waiting') return 'waiting';
  return 'requestless';
}

export function projectPipelineStepResult(
  result: StepResult,
  battleId: string,
  protocolPrefix: string[],
): Record<PlayerID, ObservableBattleState> {
  try {
    const states = {} as Record<PlayerID, ObservableBattleState>;
    for (const player of PLAYERS) {
      states[player] = projectStepResult({
        schema_version: OBSERVABLE_STATE_SCHEMA_VERSION,
        source_kind: 'sim_core',
        battle_id: battleId,
        perspective: player,
        snapshot_phase: phaseFor(result, player),
        protocol_prefix: protocolPrefix,
        step_result: result,
      });
    }
    return states;
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'observable projection failed';
    const code = detail.startsWith('Unsupported raw protocol event:') || detail.startsWith('Malformed raw ')
      ? 'pipeline/v1/unsupported-observable-protocol'
      : 'pipeline/v1/observable-projection-failed';
    throw new PipelineIntegrationError(code, detail);
  }
}

export function assertPipelineTransitionSupported(kind: PipelineBoundaryKind): void {
  if (kind === 'joint_actionable') return;
  const codes: Record<Exclude<PipelineBoundaryKind, 'joint_actionable'>, string> = {
    one_sided_forced_switch: 'pipeline/v1/unsupported-one-sided-forced-switch',
    one_sided_requestless: 'pipeline/v1/unsupported-one-sided-requestless',
    waiting: 'pipeline/v1/unsupported-waiting-boundary',
    requestless: 'pipeline/v1/unsupported-requestless-boundary',
    terminal: 'pipeline/v1/terminal-boundary',
  };
  throw new PipelineIntegrationError(codes[kind], 'no joint transition is defined for this boundary');
}

function phaseFor(result: StepResult, player: PlayerID): string {
  const view = result.views[player];
  const request = result.requests[player] ?? null;
  if (view?.terminated) return 'terminal';
  if (request?.force_switch) return 'forced_switch';
  if (request) return 'pre_decision';
  return 'post_resolution';
}

function transitionReference(metadata: SeededTransitionMetadata, actionId: string): PipelineTransitionReference {
  return {
    schema_version: PIPELINE_TRANSITION_REFERENCE_SCHEMA_VERSION,
    transition_id: metadata.transition_id,
    parent_branch_id: metadata.parent_branch_id,
    branch_id: metadata.branch_id,
    input_state_fingerprint: metadata.input_state_fingerprint,
    output_state_fingerprint: metadata.output_state_fingerprint,
    simulator_revision: metadata.simulator_revision,
    step_index: metadata.step_index,
    action_id: actionId,
  };
}

function simulatorChoiceErrors(environment: LocalBattleEnv): string[] {
  const diagnostics = environment.diagnostics() as {
    last_error?: unknown;
    players?: Record<PlayerID, { last_choice_error?: unknown }>;
  };
  const errors = PLAYERS.flatMap((player) => {
    const error = diagnostics.players?.[player]?.last_choice_error;
    return error ? [`${player} choice was rejected by the simulator`] : [];
  });
  if (diagnostics.last_error) errors.push('simulator reported an environment error');
  return errors;
}

function snapshotsForBeliefs(snapshot: SeededBattleSnapshot, battleId: string) {
  return toSeededSnapshotRef(snapshot, `pipeline:${battleId}:${snapshot.branch_id}`);
}

export class PipelineIntegrationSession {
  readonly battle_id: string;
  readonly format: string;
  private readonly seed: number[];
  private environment: LocalBattleEnv;
  private snapshot: SeededBattleSnapshot | null;
  private rawPrefix: string[];
  private currentBoundaryValue: PipelineBoundary | null;
  private closed: boolean;

  private constructor(options: PipelineIntegrationOptions) {
    if (!options.battle_id.trim()) throw new PipelineIntegrationError('pipeline/v1/invalid-battle-id', 'battle_id must not be empty');
    if (!options.format.trim()) throw new PipelineIntegrationError('pipeline/v1/invalid-ruleset', 'format must not be empty');
    if (options.seed.length !== 4 || options.seed.some((value) => !Number.isSafeInteger(value))) {
      throw new PipelineIntegrationError('pipeline/v1/invalid-seed', 'seed must contain four safe integers');
    }
    this.battle_id = options.battle_id;
    this.format = options.format;
    this.seed = [...options.seed];
    this.environment = this.newEnvironment('initial');
    this.snapshot = null;
    this.rawPrefix = [];
    this.currentBoundaryValue = null;
    this.closed = false;
  }

  static async create(options: PipelineIntegrationOptions): Promise<PipelineIntegrationSession> {
    const session = new PipelineIntegrationSession(options);
    try {
      const initial = await session.environment.resetWithOptions(OPTIONS);
      session.rawPrefix = [...initial.log_delta];
      session.snapshot = session.environment.captureSeededSnapshot(null);
      session.currentBoundaryValue = session.buildInitialBoundary(initial, session.snapshot);
      return session;
    } catch (error) {
      await session.environment.close();
      throw error;
    }
  }

  get boundary(): PipelineBoundary {
    this.ensureOpen();
    if (!this.currentBoundaryValue) throw new PipelineIntegrationError('pipeline/v1/not-initialized', 'initial boundary is missing');
    return this.currentBoundaryValue;
  }

  async step(actions?: Record<PlayerID, CanonicalAction>): Promise<PipelineStepResult> {
    this.ensureOpen();
    const inputBoundary = this.boundary;
    assertPipelineTransitionSupported(inputBoundary.kind);
    const inputSnapshot = this.snapshot;
    if (!inputSnapshot) throw new PipelineIntegrationError('pipeline/v1/not-initialized', 'current simulator snapshot is missing');

    const canonicalActions: Record<PlayerID, CanonicalAction> = { p1: undefined as never, p2: undefined as never };
    const liveRequests: Record<PlayerID, ChoiceRequestView> = { p1: undefined as never, p2: undefined as never };
    for (const player of PLAYERS) {
      const request = this.environment.getRequest(player);
      if (!request || request.wait || request.team_preview) {
        throw new PipelineIntegrationError('pipeline/v1/request-boundary-changed', `no actionable live request for ${player}`);
      }
      liveRequests[player] = request;
      const action = actions?.[player]
        ?? canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0]);
      serializeCanonicalAction(action, {
        player,
        rqid: request.rqid,
        force_switch: request.force_switch,
        legal_actions: request.legal_actions,
      });
      canonicalActions[player] = action;
      const observation = inputBoundary.perspectives[player].observation;
      if (observation.request?.rqid !== request.rqid || observation.perspective !== player) {
        throw new PipelineIntegrationError('pipeline/v1/stale-observation', `observable request for ${player} is stale`);
      }
    }
    if (actions && (Object.keys(actions).sort().join(',') !== 'p1,p2')) {
      throw new PipelineIntegrationError('pipeline/v1/joint-action-required', 'canonical actions must contain exactly p1 and p2');
    }

    const candidate = this.newEnvironment(`step-${inputBoundary.step_index}`);
    try {
      await candidate.resetFromSerialized(inputSnapshot.simulator_state, OPTIONS);
      const candidateSnapshot = candidate.captureSeededSnapshot(null);
      if (candidateSnapshot.state_fingerprint !== inputSnapshot.state_fingerprint
        || candidateSnapshot.format !== inputSnapshot.format
        || JSON.stringify(candidateSnapshot.root_seed) !== JSON.stringify(inputSnapshot.root_seed)) {
        throw new PipelineIntegrationError('pipeline/v1/restore-mismatch', 'restored candidate does not match authoritative input snapshot');
      }
      for (const player of PLAYERS) {
        const restoredRequest = candidate.getRequest(player);
        if (!restoredRequest || restoredRequest.rqid !== liveRequests[player].rqid) {
          throw new PipelineIntegrationError('pipeline/v1/restore-request-mismatch', `restored request for ${player} does not match input`);
        }
      }

      const transitionResult = await candidate.stepSeededTransition({
        schema_version: SEEDED_TRANSITION_SCHEMA_VERSION,
        snapshot: inputSnapshot,
        observations: {
          p1: inputBoundary.perspectives.p1.observation,
          p2: inputBoundary.perspectives.p2.observation,
        },
        actions: canonicalActions,
        step_index: inputBoundary.step_index,
      }, OPTIONS);
      const choiceErrors = simulatorChoiceErrors(candidate);
      if (choiceErrors.length) {
        throw new PipelineIntegrationError('pipeline/v1/rejected-action', choiceErrors.join('; '));
      }

      const nextRawPrefix = [...this.rawPrefix, ...transitionResult.metadata.emitted_log_delta];
      const projectedPrefix = projectPipelineProtocolPrefix(nextRawPrefix);
      const nextObservations = this.projectObservations(transitionResult.step_result, projectedPrefix);
      for (const player of PLAYERS) {
        const previous = inputBoundary.perspectives[player].observation.protocol_prefix;
        const next = nextObservations[player].protocol_prefix;
        if (next.length < previous.length || previous.some((line, index) => next[index] !== line)) {
          throw new PipelineIntegrationError('pipeline/v1/prefix-lineage-failure', `successor prefix for ${player} is not an exact extension`);
        }
      }
      const outputSnapshotRef = snapshotsForBeliefs(transitionResult.output_snapshot, this.battle_id);
      const nextBeliefs = {
        p1: projectBeliefState({
          observation: nextObservations.p1,
          parent: inputBoundary.perspectives.p1.belief,
          transition: {
            metadata: transitionResult.metadata,
            input_observation_id: inputBoundary.perspectives.p1.observation.observation_id,
            output_observation_id: nextObservations.p1.observation_id,
            output_snapshot: outputSnapshotRef,
          },
        }),
        p2: projectBeliefState({
          observation: nextObservations.p2,
          parent: inputBoundary.perspectives.p2.belief,
          transition: {
            metadata: transitionResult.metadata,
            input_observation_id: inputBoundary.perspectives.p2.observation.observation_id,
            output_observation_id: nextObservations.p2.observation_id,
            output_snapshot: outputSnapshotRef,
          },
        }),
      };
      serializeBeliefState(nextBeliefs.p1);
      serializeBeliefState(nextBeliefs.p2);
      const nextBoundary = freeze({
        schema_version: PIPELINE_INTEGRATION_SCHEMA_VERSION,
        battle_id: this.battle_id,
        step_index: inputBoundary.step_index + 1,
        kind: classifyPipelineBoundary(nextObservations),
        branch_id: transitionResult.metadata.branch_id,
        state_fingerprint: transitionResult.metadata.output_state_fingerprint,
        perspectives: {
          p1: { observation: nextObservations.p1, belief: nextBeliefs.p1 },
          p2: { observation: nextObservations.p2, belief: nextBeliefs.p2 },
        },
      } satisfies PipelineBoundary);

      const bundles = {} as Record<PlayerID, PipelineLinkedRecordBundle>;
      for (const player of PLAYERS) {
        bundles[player] = freeze({
          schema_version: PIPELINE_BUNDLE_SCHEMA_VERSION,
          battle_id: this.battle_id,
          source_ref: `sim-core://${this.battle_id}`,
          ruleset: this.format,
          perspective: player,
          input_observation: inputBoundary.perspectives[player].observation,
          input_belief: inputBoundary.perspectives[player].belief,
          action: canonicalActions[player],
          transition: transitionReference(transitionResult.metadata, canonicalActions[player].action_id),
          successor_observation: nextObservations[player],
          successor_belief: nextBeliefs[player],
        } satisfies PipelineLinkedRecordBundle);
      }

      const previousEnvironment = this.environment;
      this.environment = candidate;
      this.rawPrefix = nextRawPrefix;
      this.snapshot = transitionResult.output_snapshot;
      this.currentBoundaryValue = nextBoundary;
      await previousEnvironment.close();
      return { boundary: nextBoundary, transition_id: transitionResult.metadata.transition_id, record_bundles: bundles };
    } catch (error) {
      await candidate.close();
      throw error;
    }
  }

  async close(): Promise<void> {
    if (this.closed) return;
    this.closed = true;
    await this.environment.close();
  }

  private buildInitialBoundary(result: StepResult, snapshot: SeededBattleSnapshot): PipelineBoundary {
    const observations = this.projectObservations(result, projectPipelineProtocolPrefix(this.rawPrefix));
    const snapshotRef = snapshotsForBeliefs(snapshot, this.battle_id);
    const beliefs = {
      p1: projectBeliefState({ observation: observations.p1, simulator_snapshot: snapshotRef }),
      p2: projectBeliefState({ observation: observations.p2, simulator_snapshot: snapshotRef }),
    };
    serializeBeliefState(beliefs.p1);
    serializeBeliefState(beliefs.p2);
    return freeze({
      schema_version: PIPELINE_INTEGRATION_SCHEMA_VERSION,
      battle_id: this.battle_id,
      step_index: 0,
      kind: classifyPipelineBoundary(observations),
      branch_id: snapshot.branch_id,
      state_fingerprint: snapshot.state_fingerprint,
      perspectives: {
        p1: { observation: observations.p1, belief: beliefs.p1 },
        p2: { observation: observations.p2, belief: beliefs.p2 },
      },
    } satisfies PipelineBoundary);
  }

  private projectObservations(result: StepResult, protocolPrefix: string[]): Record<PlayerID, ObservableBattleState> {
    return projectPipelineStepResult(result, this.battle_id, protocolPrefix);
  }

  private newEnvironment(suffix: string): LocalBattleEnv {
    return new LocalBattleEnv(
      `${this.battle_id}-pipeline-${suffix}`,
      this.format,
      this.seed,
      { p1: { controller: 'external' }, p2: { controller: 'external' } },
    );
  }

  private ensureOpen(): void {
    if (this.closed) throw new PipelineIntegrationError('pipeline/v1/closed', 'integration session is closed');
  }
}

export async function createPipelineIntegrationSession(options: PipelineIntegrationOptions): Promise<PipelineIntegrationSession> {
  return PipelineIntegrationSession.create(options);
}
