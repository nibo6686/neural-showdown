import {copyEngineSeed, isEngineSeed, type EngineSeed, type PlayerGenerationInputs} from './engine_seed';
import { isDeepStrictEqual } from 'node:util';
import { OwnedRequestHealthHost } from './owned_request_health';
import { NativeOwnerKnowledgeController, type OwnerKnowledgeHandle, type OwnerKnowledgeRead } from './native_owner_knowledge';
import { SwitchEventHost, type SwitchEventHandle, type SwitchEventHistory } from './owner_identity_events';
import { installedNativeProfile, type NativeRuntimeProfile } from './version_profile';
import { readerContext, runtimeData, assertReaderInput, HISTORICAL10_CONTEXT, type ReaderContext } from './version_profile';
import { assertHistoricalReaderInput } from './version_profile';
import { NativeBirthEnrollment, NativeObjectAssociation, type NativeBirthHandle, type NativeBirthEvidence, type NativeObjectHandle, type NativeObjectEvidence } from './owner_identity_crosswalk';
import { RequestDeliveryLedger, type RequestDeliveryHandle, type RequestDeliveryHistory, type RequestDeliveryBoundary } from './request_delivery_ledger';
import { OriginalOwnerCreation, type OriginalOwnerHandle, type OriginalOwnerEvidence } from './original_owner_provider';
import { carryTerminalOwner, withTerminalOwner } from './public_health';
import { canonicalActionFromLegalAction, serializeCanonicalAction, type CanonicalAction, type CanonicalActionRequestContext } from './canonical_action';
import { OwnedDecisionInputController, assertCanonicalContextEqual, sanitizeOwnedDecisionInputError, type OwnedActionOrderCallback, type OwnedDecisionFrame, type OwnedDecisionOrder } from './owned_decision_input';
import { projectBeliefState, serializeBeliefState, validateObservableBattleState, type BeliefState } from './belief_state';
import { LocalBattleEnv, assertAuthoritativeEnvironment } from './env_manager';
import { rejectSimulationOnlyPayload } from './simulation_authority';
import type { SettlingOptions } from './settling';
import {
  OBSERVABLE_STATE_SCHEMA_VERSION, isObservableSchema, type ObservableSchemaVersion,
  projectStepResult,
  validateRawProtocolRecord,
  type ObservableBattleState,
} from './observable_state';
import {
  SEEDED_TRANSITION_SCHEMA_VERSION,
  SEEDED_FORCED_SWITCH_SCHEMA_VERSION,
  SEEDED_REVIVAL_SCHEMA_VERSION, SIMULATOR_REVISION,
  assertRevivalSelection,
  assertOrdinaryForcedSwitch,
  type ForcedSwitchRoles,
  type PipelineTransitionMetadata,
  toSeededSnapshotRef,
  type SeededBattleSnapshot,
} from './transition';
import type { ChoiceRequestView, PlayerID, StepResult } from './types';
import { PLAYERS } from './types';
import { RECOGNIZED_UNSUPPORTED_RAW_COMMANDS } from './protocol_contract';

export const PIPELINE_INTEGRATION_SCHEMA_VERSION = 'pipeline-integration/v1' as const;
export const PIPELINE_BUNDLE_SCHEMA_VERSION = 'pipeline-linked-record/v1' as const;
export const PIPELINE_TRANSITION_REFERENCE_SCHEMA_VERSION = 'pipeline-transition-reference/v1' as const;
export const PIPELINE_FORCED_SWITCH_BUNDLE_VERSION = 'pipeline-forced-switch-record/v1' as const;
export const PIPELINE_FORCED_SWITCH_REFERENCE_VERSION = 'pipeline-forced-switch-reference/v1' as const;
export const PIPELINE_REVIVAL_BUNDLE_VERSION = 'pipeline-revival-record/v1' as const;
export const PIPELINE_REVIVAL_REFERENCE_VERSION = 'pipeline-revival-reference/v1' as const;
export const PIPELINE_PREFIX_POLICY_VERSION = 'sim-core-observable-prefix/v1' as const;

const OPTIONS = {
  view_players: [...PLAYERS],
  include_log_delta: true,
  include_possible_roles: false,
  include_wait_requests: true,
};

export type PipelineRequestState =
  | 'actionable'
  | 'revival_selection'
  | 'forced_switch'
  | 'waiting'
  | 'requestless'
  | 'terminal'
  | 'no_legal_actions';

export type PipelineBoundaryKind =
  | 'joint_actionable'
  | 'one_sided_revival'
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

export interface PipelineForcedSwitchReference extends Omit<PipelineTransitionReference, 'schema_version'>, ForcedSwitchRoles {
  schema_version: typeof PIPELINE_FORCED_SWITCH_REFERENCE_VERSION | typeof PIPELINE_REVIVAL_REFERENCE_VERSION;
}

export interface PipelineForcedSwitchRecordBundle extends Omit<PipelineLinkedRecordBundle, 'schema_version' | 'transition'> {
  schema_version: typeof PIPELINE_FORCED_SWITCH_BUNDLE_VERSION | typeof PIPELINE_REVIVAL_BUNDLE_VERSION;
  transition: PipelineForcedSwitchReference;
}

export interface PipelineForcedSwitchStepResult extends ForcedSwitchRoles {
  boundary: PipelineBoundary;
  transition_id: string;
  record_bundles: Partial<Record<PlayerID, PipelineForcedSwitchRecordBundle>>;
}

export interface PipelineIntegrationOptions {
  /** Privileged local recipient registration only; not an RPC option or owner-string grant. */
  knowledge_recipients?: Readonly<Record<PlayerID, object>>;
  observation_schema_version?: ObservableSchemaVersion;
  settling?: SettlingOptions;
  battle_id: string;
  format: string;
  seed: readonly number[] | string;
  player_generation?: PlayerGenerationInputs;
}

function canonicalActionContext(request: Pick<ChoiceRequestView, 'player' | 'rqid' | 'force_switch' | 'legal_actions' | 'side'>): CanonicalActionRequestContext {
  return freeze(structuredClone({
    player: request.player,
    rqid: request.rqid,
    force_switch: request.force_switch,
    legal_actions: request.legal_actions,
    side: request.side,
  }));
}

function ownedDecisionError(code: string): Error { return new Error(`owned-decision-input/v1/${code}`); }

export interface PipelineDiagnostic {
  schema_version: 'pipeline-diagnostic/v1';
  code: string;
  detail: string;
  record_index?: number;
  record_command?: string;
}

export interface PipelineDiagnosticContext {
  record_index?: number;
  record_command?: string;
}

export class PipelineIntegrationError extends Error {
  readonly code: string;
  readonly diagnostic: PipelineDiagnostic;

  constructor(code: string, detail: string, context: PipelineDiagnosticContext = {}) {
    super(`${code}: ${detail}`);
    this.code = code;
    this.diagnostic = {
      schema_version: 'pipeline-diagnostic/v1',
      code,
      detail,
      ...(context.record_index === undefined ? {} : { record_index: context.record_index }),
      ...(context.record_command === undefined ? {} : { record_command: context.record_command }),
    };
  }
}

const UNRESOLVED_PROTOCOL_ALIASES = new Set([...RECOGNIZED_UNSUPPORTED_RAW_COMMANDS.values()]
  .filter((entry) => entry.kind === 'unresolved_alias')
  .map((entry) => entry.token));

function assertNoUnresolvedProtocolAlias(record: string, recordIndex: number): void {
  if (!record.startsWith('|')) return;
  const command = record.slice(1).split('|', 1)[0];
  if (!UNRESOLVED_PROTOCOL_ALIASES.has(command)) return;
  throw new PipelineIntegrationError(
    'pipeline/v1/unresolved-protocol-alias',
    `unresolved protocol alias "${command}" cannot enter a published boundary`,
    { record_index: recordIndex, record_command: command },
  );
}

function assertPublicPipelineRecord(record: string, recordIndex: number): void {
  const command = record.slice(1).split('|', 1)[0];
  if (command === 'error' || command === 'split') {
    throw new PipelineIntegrationError(
      'pipeline/v1/private-protocol-record',
      `private ${command} evidence cannot enter a published boundary`,
      { record_index: recordIndex, record_command: command },
    );
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
export function projectPipelineProtocolPrefix(records: readonly string[], rulesContext: ReaderContext = HISTORICAL10_CONTEXT): string[] {
  return projectProtocolPositions(records, rulesContext).prefix;
}
function projectProtocolPositions(records: readonly string[], rulesContext: ReaderContext) {
  readerContext(rulesContext);
  const projected: string[] = [];
  const positions: Array<number | null> = [];
  for (const [recordIndex, raw] of records.entries()) {
    // Strip only a transport line delimiter; the protocol record itself must
    // reach validation byte-for-byte so malformed fields cannot be repaired.
    const line = raw.endsWith('\r\n')
      ? raw.slice(0, -2)
      : raw.endsWith('\n') || raw.endsWith('\r')
        ? raw.slice(0, -1)
        : raw;
    if (!line.startsWith('|')) {
      throw new PipelineIntegrationError('pipeline/v1/unsupported-protocol-record', 'spectator output contained a non-protocol line');
    }
    assertPublicPipelineRecord(line, recordIndex);
    assertNoUnresolvedProtocolAlias(line, recordIndex);
    try {
      validateRawProtocolRecord(line, rulesContext);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'protocol record validation failed';
      throw new PipelineIntegrationError(
        'pipeline/v1/unsupported-observable-protocol',
        detail,
        { record_index: recordIndex, record_command: line.slice(1).split('|', 1)[0] },
      );
    }
    positions.push(null);
    if (line === '|') continue;
    if (line.startsWith('|request|')) continue;
    if (line.startsWith('|tier|')) continue;
    positions[recordIndex] = projected.length;
    projected.push(line.replace(/^\|t:\|[0-9]+$/, '|t:|0'));
  }
  return { prefix: projected, positions };
}

/** Classify only this perspective's request; never inspect the opponent's request. */
export function classifyPipelineRequestState(observation: ObservableBattleState): PipelineRequestState {
  if (observation.view.terminated) return 'terminal';
  if (!observation.request) return 'requestless';
  if (observation.request.wait) return 'waiting';
  if (observation.request.side.some(p => p.reviving)) return 'revival_selection';
  if (!observation.decision_availability.available
    || !observation.request.legal_actions.available_indices.length) return 'no_legal_actions';
  return observation.request.force_switch ? 'forced_switch' : 'actionable';
}

export function classifyPipelineBoundary(
  observations: Record<PlayerID, ObservableBattleState>,
): PipelineBoundaryKind {
  const states = {
    p1: classifyPipelineRequestState(observations.p1),
    p2: classifyPipelineRequestState(observations.p2),
  };
  if (states.p1 === 'terminal' || states.p2 === 'terminal') return 'terminal';
  for (const player of PLAYERS) {
    if (states[player] === 'no_legal_actions') {
      throw new PipelineIntegrationError('pipeline/v1/no-legal-actions', `${player} has a non-waiting request without available legal actions`);
    }
  }
  if (states.p1 === 'revival_selection' || states.p2 === 'revival_selection') return 'one_sided_revival';
  const p1 = states.p1 === 'actionable' || states.p1 === 'forced_switch';
  const p2 = states.p2 === 'actionable' || states.p2 === 'forced_switch';
  if (p1 && p2) return 'joint_actionable';
  if (p1 !== p2) {
    const actionable = p1 ? states.p1 : states.p2;
    if (actionable === 'forced_switch') return 'one_sided_forced_switch';
    return (p1 ? states.p2 : states.p1) === 'waiting' ? 'waiting' : 'one_sided_requestless';
  }
  if (states.p1 === 'waiting' || states.p2 === 'waiting') return 'waiting';
  return 'requestless';
}

export function projectPipelineStepResult(
  result: StepResult,
  battleId: string,
  protocolPrefix: string[],
  observationSchema: ObservableSchemaVersion = OBSERVABLE_STATE_SCHEMA_VERSION, rulesContext: ReaderContext = HISTORICAL10_CONTEXT
): Record<PlayerID, ObservableBattleState> {
  readerContext(rulesContext);
  for (const [recordIndex, record] of protocolPrefix.entries()) {
    assertNoUnresolvedProtocolAlias(record, recordIndex);
  }
  try {
    const states = {} as Record<PlayerID, ObservableBattleState>;
    for (const player of PLAYERS) {
      states[player] = projectStepResult({
        schema_version: observationSchema,
        source_kind: 'sim_core',
        battle_id: battleId,
        perspective: player,
        snapshot_phase: phaseFor(result, player),
        protocol_prefix: protocolPrefix,
        step_result: result,
      }, rulesContext);
    }
    return states;
  } catch (error) {
    if (error instanceof PipelineIntegrationError) throw error;
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
    one_sided_revival: 'pipeline/v1/unsupported-one-sided-revival',
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
  if (request?.wait) return 'post_resolution';
  if (request?.force_switch) return 'forced_switch';
  if (request) return 'pre_decision';
  return 'post_resolution';
}

function transitionReference(metadata: PipelineTransitionMetadata, actionId: string): PipelineTransitionReference {
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
  private readonly rulesContext: ReaderContext;
  readonly #runtimeProfile: NativeRuntimeProfile;

  readonly battle_id: string;
  readonly format: string;
  readonly #originalCreation: OriginalOwnerCreation;
  readonly #nativeBirth: NativeBirthEnrollment;
  readonly #objectAssociation: NativeObjectAssociation;
  readonly #switchEvents: SwitchEventHost;
  readonly #requestHealth: OwnedRequestHealthHost | undefined;
  readonly #ownerKnowledge: NativeOwnerKnowledgeController | undefined;
  readonly #deliveryLedger = new RequestDeliveryLedger();
  readonly #ownedDecisionInputs = new OwnedDecisionInputController();
  readonly #ownedDecisionOccurrence = Object.freeze(Object.create(null)) as object;
  #ownedDecisionBatch: ReadonlyMap<PlayerID, OwnedDecisionFrame> | null = null;
  #selectionActive = false;
  #selectionPoisoned = false;
  #deliveryEnabled = false;
  private readonly seed: EngineSeed;
  private readonly playerGeneration?: PlayerGenerationInputs;
  private environment: LocalBattleEnv;
  private snapshot: SeededBattleSnapshot | null;
  private rawPrefix: string[];
  private currentBoundaryValue: PipelineBoundary | null;
  private closed: boolean;
  private readonly settlingOptions: SettlingOptions;
  private readonly observationSchema: ObservableSchemaVersion;
  private readonly retiredEnvironments = new Set<LocalBattleEnv>();

  private constructor(options: PipelineIntegrationOptions) {
    this.#runtimeProfile = installedNativeProfile();
    this.rulesContext = this.#runtimeProfile.reader;
    const version = options.observation_schema_version ?? OBSERVABLE_STATE_SCHEMA_VERSION;
    if (!isObservableSchema(version)) throw new Error('Unsupported observation schema');
    this.observationSchema = version;
    if (!options.battle_id.trim()) throw new PipelineIntegrationError('pipeline/v1/invalid-battle-id', 'battle_id must not be empty');
    if (!options.format.trim()) throw new PipelineIntegrationError('pipeline/v1/invalid-ruleset', 'format must not be empty');
    if (!isEngineSeed(options.seed)) {
      throw new PipelineIntegrationError('pipeline/v1/invalid-seed', 'seed must contain four safe integers or a canonical native PRNG string');
    }
    this.battle_id = options.battle_id;
    this.format = options.format;
    this.seed = copyEngineSeed(options.seed);
    if (options.player_generation !== undefined) {
      if (!options.player_generation || Object.keys(options.player_generation).sort().join(',') !== 'p1,p2') throw new Error('Invalid player generation inputs');
      for (const owner of PLAYERS) {
        const row = options.player_generation[owner];
        if (!row || Object.keys(row).sort().join(',') !== 'name,seed'
          || typeof row.name !== 'string' || !row.name || !isEngineSeed(row.seed)) throw new Error('Invalid player generation inputs');
      }
      this.playerGeneration = structuredClone(options.player_generation);
    }
    this.settlingOptions = { ...options.settling };
    this.#originalCreation = new OriginalOwnerCreation({ battle_id: this.battle_id, format: this.format, simulator_revision: this.rulesContext.profile.revision });
    this.#ownerKnowledge = options.knowledge_recipients
      ? new NativeOwnerKnowledgeController(this.#originalCreation, this.#runtimeProfile, options.knowledge_recipients) : undefined;
    this.#nativeBirth = new NativeBirthEnrollment(this.#originalCreation);
    this.#objectAssociation = new NativeObjectAssociation(this.#nativeBirth);
    this.#switchEvents = new SwitchEventHost(this.#nativeBirth, this.#objectAssociation);
    this.#requestHealth = options.knowledge_recipients ? new OwnedRequestHealthHost(this.#nativeBirth, this.#objectAssociation) : undefined;
    this.environment = this.newEnvironment('initial');
    this.snapshot = null;
    this.rawPrefix = [];
    this.currentBoundaryValue = null;
    this.closed = false;
  }

  static async create(options: PipelineIntegrationOptions): Promise<PipelineIntegrationSession> {
    const session = new PipelineIntegrationSession(options);
    try {
      assertAuthoritativeEnvironment(session.environment);
      const initial = await session.environment.resetWithOptions(OPTIONS);
      rejectSimulationOnlyPayload(initial);
      session.rawPrefix = [...initial.log_delta];
      const snapshot = session.environment.captureSeededSnapshot(null);
      const boundary = session.buildInitialBoundary(initial, snapshot);
      // Original enrollment remains tentative inside the unpublished session.
      if (session.#originalCreation.activate()) {
        session.#nativeBirth.prepareActivation();
        const delivery = session.#deliveryLedger.prepare(session.environment, initial, boundary, null);
        const association = session.#objectAssociation.prepareInitial(session.environment, boundary, snapshot);
        const events = session.#switchEvents.prepare(session.environment, boundary, snapshot, projectProtocolPositions(session.rawPrefix, session.rulesContext), null);
        const health = session.#requestHealth?.prepare(session.environment, boundary, session.#deliveryLedger, delivery);
        const knowledge = session.#ownerKnowledge?.prepare(session.environment, boundary, null, session.#requestHealth, health);
        session.#deliveryLedger.preflight(delivery);
        session.#objectAssociation.preflight(association);
        session.#switchEvents.preflight(events);
        if (health) session.#requestHealth!.preflight(health);
        if (knowledge) session.#ownerKnowledge!.preflight(knowledge);
        // No validation/allocation/await/user callback from here to publication.
        session.#nativeBirth.installActivation();
        session.#deliveryLedger.installReady();
        session.#objectAssociation.installReady();
        session.#switchEvents.installReady();
        if (health) session.#requestHealth!.installReady();
        if (knowledge) session.#ownerKnowledge!.installReady();
        session.snapshot = snapshot; session.currentBoundaryValue = boundary; session.#deliveryEnabled = true;
      } else {
        session.#requestHealth?.revoke(); session.#ownerKnowledge?.revoke();
        session.#deliveryLedger.revoke(); session.#nativeBirth.revoke(); session.#switchEvents.revoke();
        session.snapshot = snapshot; session.currentBoundaryValue = boundary;
      }
      return session;
    } catch (error) {
      session.#requestHealth?.revoke(); session.#ownerKnowledge?.revoke();
      session.#deliveryLedger.revoke();
      session.#originalCreation.revoke();
      session.#nativeBirth.revoke();
      session.#switchEvents.revoke();
      session.#objectAssociation.revoke();
      await session.environment.close();
      throw error;
    }
  }

  /** Privileged process-local owner access, outside observation and wire APIs. */
  getOriginalOwnerHolding(owner: PlayerID): OriginalOwnerHandle {
    assertAuthoritativeEnvironment(this.environment);
    return this.#originalCreation.holding(owner);
  }

  getNativeBirthHolding(owner: PlayerID): NativeBirthHandle {
    this.ensureOpen();
    return this.#nativeBirth.holding(owner);
  }

  readNativeBirthHolding(handle: NativeBirthHandle, owner: PlayerID): NativeBirthEvidence {
    this.ensureOpen();
    return this.#nativeBirth.read(handle, owner);
  }

  getOwnerKnowledgeHandle(recipient: object): OwnerKnowledgeHandle {
    this.ensureOpen(); if (!this.#ownerKnowledge) throw new Error('native-owner-knowledge/v1/not-adopted');
    return this.#ownerKnowledge.handle(recipient);
  }
  readOwnerKnowledge(handle: OwnerKnowledgeHandle, recipient: object): OwnerKnowledgeRead {
    this.ensureOpen(); if (!this.#ownerKnowledge) throw new Error('native-owner-knowledge/v1/not-adopted');
    return this.#ownerKnowledge.read(handle, recipient);
  }

  getSwitchEventHolding(owner: PlayerID): SwitchEventHandle { this.ensureOpen(); return this.#switchEvents.holding(owner); }
  readSwitchEventHolding(handle: SwitchEventHandle, owner: PlayerID): SwitchEventHistory {
    this.ensureOpen(); return this.#switchEvents.read(handle, owner);
  }

  getNativeObjectHolding(owner: PlayerID): NativeObjectHandle {
    this.ensureOpen(); return this.#objectAssociation.holding(owner);
  }

  readNativeObjectHolding(handle: NativeObjectHandle, owner: PlayerID): NativeObjectEvidence {
    this.ensureOpen(); return this.#objectAssociation.read(handle, owner);
  }

  getRequestDeliveryHandle(owner: PlayerID): RequestDeliveryHandle {
    this.ensureOpen();
    return this.#deliveryLedger.handle(owner);
  }

  readRequestDeliveryHistory(handle: RequestDeliveryHandle, owner: PlayerID, expected?: RequestDeliveryBoundary): RequestDeliveryHistory {
    this.ensureOpen();
    return this.#deliveryLedger.read(handle, owner, expected);
  }

  readOriginalOwnerHolding(handle: OriginalOwnerHandle, owner: PlayerID, packed?: string): OriginalOwnerEvidence {
    assertAuthoritativeEnvironment(this.environment);
    return this.#originalCreation.read(handle, owner, packed);
  }

  /** Runs one synchronous, owner-addressed callback and returns its opaque order. */
  withOwnedDecisionInput(recipient: object, callback: OwnedActionOrderCallback): OwnedDecisionOrder {
    if (this.#selectionActive) {
      this.#selectionPoisoned = true;
      this.#ownedDecisionInputs.invalidate();
      this.#ownedDecisionBatch = null;
      throw ownedDecisionError('reentrant-call');
    }
    this.ensureOpen();
    this.#selectionActive = true;
    this.#selectionPoisoned = false;
    try {
      const boundary = this.boundary;
      const knowledgeController = this.#ownerKnowledge;
      if (!knowledgeController) throw ownedDecisionError('unsupported-frame');
      const handle = knowledgeController.handle(recipient);
      const knowledge = knowledgeController.read(handle, recipient);
      const owner = knowledge.projection.owner as PlayerID;
      if (!PLAYERS.includes(owner)) throw ownedDecisionError('unsupported-frame');
      const observation = boundary.perspectives[owner].observation;
      const request = observation.request;
      if (!request) throw ownedDecisionError('unsupported-frame');
      const context = canonicalActionContext(request);
      const legalIndices = Object.freeze([...request.legal_actions.available_indices].sort((a, b) => a - b));
      const ledgerHandle = this.#deliveryLedger.handle(owner);
      const history = this.#deliveryLedger.read(ledgerHandle, owner);
      const deliveryBoundary = history.boundaries.at(-1);
      const currentDelivery = deliveryBoundary?.current;
      const selectedReceipt = deliveryBoundary?.selected;
      if (!deliveryBoundary || !currentDelivery || !selectedReceipt) throw ownedDecisionError('unsupported-frame');
      const frame: OwnedDecisionFrame = Object.freeze({
        owner, recipient, knowledge_handle: handle, knowledge, observation,
        environment: this.environment, boundary, session_occurrence: deliveryBoundary.session_occurrence,
        delivery_boundary: deliveryBoundary, current_delivery: currentDelivery, selected_receipt: selectedReceipt,
        action_context: context, legal_indices: legalIndices,
      });
      const validate = () => this.recheckOwnedDecisionFrame(frame, ledgerHandle);
      return this.#ownedDecisionInputs.issue(frame, callback, validate);
    } catch (error) {
      this.#ownedDecisionInputs.invalidate();
      this.#ownedDecisionBatch = null;
      const safeError = sanitizeOwnedDecisionInputError(error);
      if (safeError) throw safeError;
      throw ownedDecisionError('unsupported-frame');
    } finally {
      this.#selectionActive = false;
    }
  }

  /** Rechecks authentic orders together; step() consumes this authorization synchronously. */
  assertOwnedDecisionBatch(orders: readonly OwnedDecisionOrder[]): void {
    if (this.#selectionActive) {
      this.#selectionPoisoned = true;
      throw ownedDecisionError('reentrant-call');
    }
    this.ensureOpen();
    this.#ownedDecisionBatch = null;
    try {
      const boundary = this.boundary;
      const actors = this.ownedDecisionActors(boundary);
      const frames = this.#ownedDecisionInputs.assertBatch(orders, actors, frame => {
        const handle = this.#deliveryLedger.handle(frame.owner);
        this.recheckOwnedDecisionFrame(frame, handle);
      });
      this.#ownedDecisionBatch = new Map(frames);
    } catch (error) {
      const safeError = sanitizeOwnedDecisionInputError(error);
      if (safeError) throw safeError;
      throw ownedDecisionError('stale-or-unsupported-frame');
    }
  }

  private ownedDecisionActors(boundary: PipelineBoundary): PlayerID[] {
    if (boundary.kind === 'joint_actionable') return [...PLAYERS];
    if (boundary.kind === 'one_sided_forced_switch' || boundary.kind === 'one_sided_revival') {
      const expected = boundary.kind === 'one_sided_revival' ? 'revival_selection' : 'forced_switch';
      const actor = PLAYERS.find(owner => classifyPipelineRequestState(boundary.perspectives[owner].observation) === expected);
      if (actor && classifyPipelineRequestState(boundary.perspectives[actor === 'p1' ? 'p2' : 'p1'].observation) === 'waiting') return [actor];
    }
    throw ownedDecisionError('unsupported-frame');
  }

  private recheckOwnedDecisionFrame(frame: OwnedDecisionFrame, ledgerHandle: RequestDeliveryHandle): void {
    const fail = () => { throw ownedDecisionError(this.closed ? 'revoked' : 'stale-or-unsupported-frame'); };
    if (this.closed || this.#selectionPoisoned || this.currentBoundaryValue !== frame.boundary
      || this.environment !== frame.environment || frame.session_occurrence !== (frame.delivery_boundary as RequestDeliveryBoundary).session_occurrence
      || frame.observation !== this.currentBoundaryValue?.perspectives[frame.owner].observation) fail();
    const knowledgeController = this.#ownerKnowledge;
    if (!knowledgeController) throw ownedDecisionError('stale-or-unsupported-frame');
    let handle!: OwnerKnowledgeHandle;
    let read!: OwnerKnowledgeRead;
    try {
      handle = knowledgeController.handle(frame.recipient);
      read = knowledgeController.read(handle, frame.recipient);
    } catch { fail(); }
    if (handle !== frame.knowledge_handle || read !== frame.knowledge
      || read.projection.owner !== frame.owner
      || read.binding.observation_id !== frame.observation.observation_id
      || read.binding.prefix_cursor !== frame.observation.event_cursor
      || read.projection.boundary !== frame.boundary.step_index) fail();
    const row = frame.delivery_boundary;
    let history: RequestDeliveryHistory;
    try { history = this.#deliveryLedger.read(ledgerHandle, frame.owner, row); } catch { fail(); }
    const current = row.current;
    const selected = row.selected;
    if (!current || !selected) throw ownedDecisionError('stale-or-unsupported-frame');
    if (history!.boundaries.at(-1) !== row || row.session_occurrence !== frame.session_occurrence
      || row.observation_id !== frame.observation.observation_id || row.branch_id !== frame.boundary.branch_id
      || row.step_index !== frame.boundary.step_index || row.boundary_cursor !== frame.observation.event_cursor
      || !isDeepStrictEqual(row.prefix, frame.observation.protocol_prefix)
      || current !== frame.current_delivery || selected !== frame.selected_receipt
      || current.source !== selected || !row.trace.includes(selected)
      || !history!.deliveries.includes(current) || current.session_occurrence !== row.session_occurrence) fail();
    const descriptor = read.projection.request;
    const requestState = classifyPipelineRequestState(frame.observation);
    const descriptorOk = descriptor?.schema === 'owned-active-options/v1'
      && read.binding.request_adaptation === 'owned_health/v1'
      && read.binding.request_descriptor === 'owned-active-options/v1'
      && descriptor.sequence === current.sequence && descriptor.cursor === row.boundary_cursor
      && ((descriptor.state === 'ordinary_pp' && read.binding.request_state === 'move' && requestState === 'actionable')
        || (descriptor.state === 'forced_switch' && read.binding.request_state === 'forced_switch' && requestState === 'forced_switch')
        || (descriptor.state === 'revival_selection' && read.binding.request_state === 'revival_selection' && requestState === 'revival_selection'));
    const observationRequest = frame.observation.request;
    if (!descriptorOk || !observationRequest || observationRequest.player !== frame.owner
      || observationRequest.wait || observationRequest.team_preview || !frame.legal_indices.length
      || !isDeepStrictEqual(frame.legal_indices, [...observationRequest.legal_actions.available_indices].sort((a, b) => a - b))) fail();
    let fresh: ChoiceRequestView | null = null;
    try { fresh = this.environment.getRequest(frame.owner); } catch { fail(); }
    if (!fresh || fresh.player !== frame.owner || fresh.wait || fresh.team_preview) {
      throw ownedDecisionError('stale-or-unsupported-frame');
    }
    try { assertCanonicalContextEqual(frame.action_context, canonicalActionContext(fresh)); } catch { fail(); }
  }

  private consumeOwnedDecisionBatch(actions: Partial<Record<PlayerID, CanonicalAction>> | undefined, actors: readonly PlayerID[]): void {
    const batch = this.#ownedDecisionBatch;
    this.#ownedDecisionBatch = null;
    if (!batch) return;
    if (!actions || Object.keys(actions).sort().join(',') !== [...actors].sort().join(',')
      || batch.size !== actors.length || actors.some(owner => !batch.has(owner))) throw ownedDecisionError('invalid-batch');
    try {
      for (const owner of actors) {
        const frame = batch.get(owner)!;
        const handle = this.#deliveryLedger.handle(owner);
        this.recheckOwnedDecisionFrame(frame, handle);
        const action = actions[owner];
        if (!action || !frame.legal_indices.includes(action.index)) throw ownedDecisionError('invalid-batch');
      }
      this.#ownedDecisionInputs.invalidate();
    } catch (error) {
      this.#ownedDecisionInputs.invalidate();
      const safeError = sanitizeOwnedDecisionInputError(error);
      if (safeError) throw safeError;
      throw ownedDecisionError('stale-or-unsupported-frame');
    }
  }

  get boundary(): PipelineBoundary {
    this.ensureOpen();
    if (!this.currentBoundaryValue) throw new PipelineIntegrationError('pipeline/v1/not-initialized', 'initial boundary is missing');
    return this.currentBoundaryValue;
  }

  /** Validate supported addressed requests before episode selection. */
  assertSupportedSelectionRequests(): void {
    this.ensureOpen();
    for (const player of PLAYERS) {
      const request = this.environment.getRequest(player);
      if (request?.side.some(p => p.reviving)) {
        if (this.boundary.kind !== 'one_sided_revival'
          || classifyPipelineRequestState(this.boundary.perspectives[player === 'p1' ? 'p2' : 'p1'].observation) !== 'waiting') {
          throw new Error('seeded-revival/v1/unsupported-request');
        }
        assertRevivalSelection(request);
      } else if (request?.force_switch) assertOrdinaryForcedSwitch(request);
    }
  }

  async step(actions?: Record<PlayerID, CanonicalAction>): Promise<PipelineStepResult> {
    this.rejectReentrantSelection();
    this.ensureOpen();
    assertPipelineTransitionSupported(this.boundary.kind);
    this.consumeOwnedDecisionBatch(actions, PLAYERS);
    return this.executeTransition(actions) as Promise<PipelineStepResult>;
  }

  async stepForcedSwitch(action: CanonicalAction): Promise<PipelineForcedSwitchStepResult> {
    this.rejectReentrantSelection();
    if (action.kind !== 'switch') throw new Error('Forced switch requires a switch action.');
    return this.stepSelection(action);
  }

  private async stepSelection(action: CanonicalAction): Promise<PipelineForcedSwitchStepResult> {
    this.rejectReentrantSelection();
    this.ensureOpen();
    const acting_player = action.player;
    if (acting_player !== 'p1' && acting_player !== 'p2') throw new PipelineIntegrationError('pipeline/v1/invalid-forced-switch-role', 'invalid acting player');
    const waiting_player = acting_player === 'p1' ? 'p2' : 'p1';
    const revival = action.kind === 'revive';
    if (classifyPipelineRequestState(this.boundary.perspectives[acting_player].observation) !== (revival ? 'revival_selection' : 'forced_switch')
      || classifyPipelineRequestState(this.boundary.perspectives[waiting_player].observation) !== 'waiting') {
      throw new PipelineIntegrationError('pipeline/v1/unsupported-forced-switch-boundary', 'requires one forced-switch player and one waiting player');
    }
    const live = this.environment.getRequest(acting_player);
    if (!live) throw new PipelineIntegrationError('pipeline/v1/request-boundary-changed', 'forced-switch actor has no pending request');
    if (revival) assertRevivalSelection(live);
    else assertOrdinaryForcedSwitch(live);
    this.consumeOwnedDecisionBatch({ [acting_player]: action }, [acting_player]);
    return this.executeTransition({ [acting_player]: action }, { acting_player, waiting_player }) as Promise<PipelineForcedSwitchStepResult>;
  }

  async stepRevival(action: CanonicalAction): Promise<PipelineForcedSwitchStepResult> {
    this.rejectReentrantSelection();
    if (action.kind !== 'revive') throw new Error('Revival selection requires a revive action.');
    return this.stepSelection(action);
  }

  private rejectReentrantSelection(): void {
    if (!this.#selectionActive) return;
    this.#selectionPoisoned = true;
    throw ownedDecisionError('reentrant-call');
  }

  private async executeTransition(
    actions?: Partial<Record<PlayerID, CanonicalAction>>,
    roles?: ForcedSwitchRoles,
  ): Promise<PipelineStepResult | PipelineForcedSwitchStepResult> {
    const inputBoundary = this.boundary;
    const revival = !!roles && actions?.[roles.acting_player]?.kind === 'revive';
    const actors = roles ? [roles.acting_player] : PLAYERS;
    const inputSnapshot = this.snapshot;
    if (!inputSnapshot) throw new PipelineIntegrationError('pipeline/v1/not-initialized', 'current simulator snapshot is missing');

    const canonicalActions: Record<PlayerID, CanonicalAction> = { p1: undefined as never, p2: undefined as never };
    const liveRequests: Record<PlayerID, ChoiceRequestView> = { p1: undefined as never, p2: undefined as never };
    for (const player of actors) {
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
        legal_actions: request.legal_actions, side: request.side,
      });
      canonicalActions[player] = action;
      const observation = inputBoundary.perspectives[player].observation;
      if (observation.request?.rqid !== request.rqid || observation.perspective !== player) {
        throw new PipelineIntegrationError('pipeline/v1/stale-observation', `observable request for ${player} is stale`);
      }
    }
    if (actions && (Object.keys(actions).sort().join(',') !== [...actors].sort().join(','))) {
      throw new PipelineIntegrationError('pipeline/v1/joint-action-required', 'canonical actions must match the acting players');
    }

    const candidate = this.newEnvironment(`step-${inputBoundary.step_index}`);
    let delivery: object | undefined;
    try {
      const associationTicket = this.#deliveryEnabled ? this.#objectAssociation.prepareRestore(candidate, inputBoundary, inputSnapshot) : undefined;
      if (associationTicket) this.#objectAssociation.assertRestoreAdmission(candidate, inputSnapshot.simulator_state, associationTicket);
      const restored = await candidate.resetFromSerialized(inputSnapshot.simulator_state, OPTIONS, associationTicket);
      const restoration = this.#deliveryEnabled ? this.#deliveryLedger.restored(candidate, restored, inputBoundary) : undefined;
      const candidateSnapshot = candidate.captureSeededSnapshot(null);
      if (candidateSnapshot.state_fingerprint !== inputSnapshot.state_fingerprint
        || candidateSnapshot.format !== inputSnapshot.format
        || JSON.stringify(candidateSnapshot.root_seed) !== JSON.stringify(inputSnapshot.root_seed)) {
        throw new PipelineIntegrationError('pipeline/v1/restore-mismatch', 'restored candidate does not match authoritative input snapshot');
      }
      for (const player of actors) {
        const restoredRequest = candidate.getRequest(player);
        if (!restoredRequest || restoredRequest.rqid !== liveRequests[player].rqid) {
          throw new PipelineIntegrationError('pipeline/v1/restore-request-mismatch', `restored request for ${player} does not match input`);
        }
      }

      const common = {
        snapshot: inputSnapshot,
        observations: {
          p1: inputBoundary.perspectives.p1.observation,
          p2: inputBoundary.perspectives.p2.observation,
        },
        step_index: inputBoundary.step_index,
      };
      const transitionResult = roles
        ? await candidate.stepSeededForcedSwitch({
          ...common, ...roles, schema_version: revival ? SEEDED_REVIVAL_SCHEMA_VERSION : SEEDED_FORCED_SWITCH_SCHEMA_VERSION,
          actions: { [roles.acting_player]: canonicalActions[roles.acting_player] },
        }, OPTIONS)
        : await candidate.stepSeededTransition({
          ...common, schema_version: SEEDED_TRANSITION_SCHEMA_VERSION, actions: canonicalActions,
        }, OPTIONS);
      const choiceErrors = simulatorChoiceErrors(candidate);
      if (choiceErrors.length) {
        throw new PipelineIntegrationError('pipeline/v1/rejected-action', choiceErrors.join('; '));
      }

      const nextRawPrefix = [...this.rawPrefix, ...transitionResult.metadata.emitted_log_delta];
      const projectedPrefix = projectPipelineProtocolPrefix(nextRawPrefix, this.rulesContext);
      for (const player of PLAYERS) {
        carryTerminalOwner({
          predecessor: inputBoundary.perspectives[player].observation as unknown as Record<string, unknown>, before: inputBoundary,
          transition: transitionResult.metadata,
          action: canonicalActions[player],
          after: {step_index: inputBoundary.step_index + 1, branch_id: transitionResult.metadata.branch_id, state_fingerprint: transitionResult.metadata.output_state_fingerprint},
        }, {schema_version: this.observationSchema, battle_id: this.battle_id, perspective: player,
          request: transitionResult.step_result.requests[player] ?? null, protocol_prefix: projectedPrefix,
          view: transitionResult.step_result.views[player]});
      }
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
        }, this.rulesContext),
        p2: projectBeliefState({
          observation: nextObservations.p2,
          parent: inputBoundary.perspectives.p2.belief,
          transition: {
            metadata: transitionResult.metadata,
            input_observation_id: inputBoundary.perspectives.p2.observation.observation_id,
            output_observation_id: nextObservations.p2.observation_id,
            output_snapshot: outputSnapshotRef,
          },
        }, this.rulesContext),
      };
      serializeBeliefState(nextBeliefs.p1, this.rulesContext);
      serializeBeliefState(nextBeliefs.p2, this.rulesContext);
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

      const bundles: Partial<Record<PlayerID, PipelineLinkedRecordBundle | PipelineForcedSwitchRecordBundle>> = {};
      for (const player of actors) {
        bundles[player] = freeze({
          schema_version: roles ? (revival ? PIPELINE_REVIVAL_BUNDLE_VERSION : PIPELINE_FORCED_SWITCH_BUNDLE_VERSION) : PIPELINE_BUNDLE_SCHEMA_VERSION,
          battle_id: this.battle_id,
          source_ref: `sim-core://${this.battle_id}`,
          ruleset: this.format,
          perspective: player,
          input_observation: inputBoundary.perspectives[player].observation,
          input_belief: inputBoundary.perspectives[player].belief,
          action: canonicalActions[player],
          transition: roles ? {
            ...transitionReference(transitionResult.metadata, canonicalActions[player].action_id),
            ...roles, schema_version: revival ? PIPELINE_REVIVAL_REFERENCE_VERSION : PIPELINE_FORCED_SWITCH_REFERENCE_VERSION,
          } : transitionReference(transitionResult.metadata, canonicalActions[player].action_id),
          successor_observation: nextObservations[player],
          successor_belief: nextBeliefs[player],
        } as PipelineLinkedRecordBundle | PipelineForcedSwitchRecordBundle);
        validatePipelineEpisodeRecordBundle(bundles[player]!, this.rulesContext);
      }

      delivery = this.#deliveryEnabled
        ? this.#deliveryLedger.prepare(candidate, transitionResult.step_result, nextBoundary, inputBoundary, restoration) : undefined;
      const association = associationTicket ? this.#objectAssociation.prepareCommit(candidate, nextBoundary, transitionResult.output_snapshot, associationTicket) : undefined;
      const events = this.#deliveryEnabled ? this.#switchEvents.prepare(candidate, nextBoundary, transitionResult.output_snapshot,
        projectProtocolPositions(nextRawPrefix, this.rulesContext), inputBoundary) : undefined;
      const health = delivery ? this.#requestHealth?.prepare(candidate, nextBoundary, this.#deliveryLedger, delivery) : undefined;
      const knowledge = this.#ownerKnowledge?.prepare(candidate, nextBoundary, inputBoundary, this.#requestHealth, health);
      if (delivery) this.#deliveryLedger.preflight(delivery);
      if (association) this.#objectAssociation.preflight(association);
      if (events) this.#switchEvents.preflight(events);
      if (health) this.#requestHealth!.preflight(health);
      if (knowledge) this.#ownerKnowledge!.preflight(knowledge);
      const previousEnvironment = this.environment;
      const result = { ...roles, boundary: nextBoundary, transition_id: transitionResult.metadata.transition_id, record_bundles: bundles } as PipelineStepResult | PipelineForcedSwitchStepResult;
      // Retirement allocation also precedes the irreversible assignment section.
      this.retiredEnvironments.add(previousEnvironment);
      this.#ownedDecisionInputs.invalidate(); this.#ownedDecisionBatch = null;
      if (delivery) this.#deliveryLedger.installReady();
      if (association) this.#objectAssociation.installReady();
      if (events) this.#switchEvents.installReady();
      if (health) this.#requestHealth!.installReady();
      if (knowledge) this.#ownerKnowledge!.installReady();
      this.environment = candidate; this.rawPrefix = nextRawPrefix;
      this.snapshot = transitionResult.output_snapshot; this.currentBoundaryValue = nextBoundary;
      try {
        await previousEnvironment.close();
        this.retiredEnvironments.delete(previousEnvironment);
      } catch {
        // Retried explicitly when the session is closed.
      }
      return result;
    } catch (error) {
      this.#requestHealth?.release(candidate); this.#ownerKnowledge?.discard(candidate);
      if (delivery) this.#deliveryLedger.discard(delivery);
      this.#switchEvents.release(candidate);
      this.#objectAssociation.discard(candidate);
      await candidate.close();
      throw error;
    }
  }

  async close(): Promise<void> {
    if (this.closed) return;
    this.closed = true;
    this.#ownedDecisionInputs.revoke(); this.#ownedDecisionBatch = null;
    this.#requestHealth?.revoke(); this.#ownerKnowledge?.revoke();
    this.#deliveryLedger.revoke();
    this.#originalCreation.revoke();
    this.#nativeBirth.revoke();
    this.#switchEvents.revoke();
    this.#objectAssociation.revoke();
    await this.environment.close();
    for (const retired of this.retiredEnvironments) {
      await retired.close();
      this.retiredEnvironments.delete(retired);
    }
  }

  private buildInitialBoundary(result: StepResult, snapshot: SeededBattleSnapshot): PipelineBoundary {
    const observations = this.projectObservations(result, projectPipelineProtocolPrefix(this.rawPrefix, this.rulesContext));
    const snapshotRef = snapshotsForBeliefs(snapshot, this.battle_id);
    const beliefs = {
      p1: projectBeliefState({ observation: observations.p1, simulator_snapshot: snapshotRef }, this.rulesContext),
      p2: projectBeliefState({ observation: observations.p2, simulator_snapshot: snapshotRef }, this.rulesContext),
    };
    serializeBeliefState(beliefs.p1, this.rulesContext);
    serializeBeliefState(beliefs.p2, this.rulesContext);
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
    return projectPipelineStepResult(result, this.battle_id, protocolPrefix, this.observationSchema, this.rulesContext);
  }

  private newEnvironment(suffix: string): LocalBattleEnv {
    return new LocalBattleEnv(
      `${this.battle_id}-pipeline-${suffix}`,
      this.format,
      this.seed,
      { p1: { controller: 'external' }, p2: { controller: 'external' } },
      this.settlingOptions,
      suffix === 'initial' ? this.#originalCreation : undefined,
      suffix === 'initial' ? this.#nativeBirth : undefined,
      this.#objectAssociation,
      this.#runtimeProfile,
      this.#switchEvents, this.#requestHealth, this.playerGeneration,
    );
  }

  getReaderContext(): ReaderContext { return this.rulesContext; }

  private ensureOpen(): void {
    assertAuthoritativeEnvironment(this.environment);
    if (this.closed) throw new PipelineIntegrationError('pipeline/v1/closed', 'integration session is closed');
  }
}

export async function createPipelineIntegrationSession(options: PipelineIntegrationOptions): Promise<PipelineIntegrationSession> {
  return PipelineIntegrationSession.create(options);
}

/** Ordinary publication validates the whole owned action and transition before terminal alias authority. */
export function validatePipelineLinkedRecordBundle(bundle: PipelineLinkedRecordBundle, rulesContext: ReaderContext = HISTORICAL10_CONTEXT): void {
  readerContext(rulesContext);
  assertReaderInput(bundle, rulesContext);
  if (bundle.schema_version !== PIPELINE_BUNDLE_SCHEMA_VERSION) throw new Error('Linked record schema is invalid');
  validatePipelineEpisodeRecordBundle(bundle, rulesContext);
}

/** Reuse the accepted action/belief/terminal joins for every episode actor kind. */
export function validatePipelineEpisodeRecordBundle(bundle: PipelineLinkedRecordBundle | PipelineForcedSwitchRecordBundle, rulesContext: ReaderContext = HISTORICAL10_CONTEXT): void {
  rejectSimulationOnlyPayload(bundle);
  readerContext(rulesContext);
  assertReaderInput(bundle, rulesContext);
  const schemas = {
    [PIPELINE_BUNDLE_SCHEMA_VERSION]: PIPELINE_TRANSITION_REFERENCE_SCHEMA_VERSION,
    [PIPELINE_FORCED_SWITCH_BUNDLE_VERSION]: PIPELINE_FORCED_SWITCH_REFERENCE_VERSION,
    [PIPELINE_REVIVAL_BUNDLE_VERSION]: PIPELINE_REVIVAL_REFERENCE_VERSION,
  };
  const oneSided = bundle.schema_version !== PIPELINE_BUNDLE_SCHEMA_VERSION;
  const before = bundle.input_observation, after = bundle.successor_observation;
  const expectedKeys = ['schema_version', 'battle_id', 'source_ref', 'ruleset', 'perspective', 'input_observation', 'input_belief', 'action', 'transition', 'successor_observation', 'successor_belief'];
  if (Object.keys(bundle).sort().join('|') !== expectedKeys.sort().join('|') || !Object.hasOwn(schemas, bundle.schema_version)
    || bundle.source_ref !== `sim-core://${bundle.battle_id}` || before.source_kind !== 'sim_core' || after.source_kind !== 'sim_core'
    || bundle.ruleset !== before.view.format || bundle.ruleset !== after.view.format || before.schema_version !== after.schema_version
    || !before.decision_availability.available || bundle.transition.schema_version !== schemas[bundle.schema_version]
    || bundle.transition.simulator_revision !== readerContext(rulesContext).profile.revision || !/^transition-[a-f0-9]{64}$/.test(bundle.transition.transition_id)
    || !/^[a-f0-9]{64}$/.test(bundle.transition.input_state_fingerprint) || !/^[a-f0-9]{64}$/.test(bundle.transition.output_state_fingerprint)
    || !bundle.transition.parent_branch_id.trim() || !bundle.transition.branch_id.trim()
    || Object.keys(bundle.transition).sort().join('|') !== ['schema_version', 'transition_id', 'parent_branch_id', 'branch_id', 'input_state_fingerprint', 'output_state_fingerprint', 'simulator_revision', 'step_index', 'action_id', ...(oneSided ? ['acting_player', 'waiting_player'] : [])].sort().join('|')) throw new Error('Linked record source/schema/action transition metadata is invalid');
  if (oneSided) {
    const roles = bundle.transition as PipelineForcedSwitchReference;
    if (roles.acting_player !== bundle.perspective || roles.waiting_player !== (bundle.perspective === 'p1' ? 'p2' : 'p1')
      || classifyPipelineRequestState(before) !== (bundle.schema_version === PIPELINE_REVIVAL_BUNDLE_VERSION ? 'revival_selection' : 'forced_switch')) throw new Error('Episode actor request/role mismatch');
  }
  validateObservableBattleState(before, rulesContext);
  serializeBeliefState(bundle.input_belief, rulesContext);
  const transition = bundle.transition;
  const input = bundle.input_belief.simulator_snapshot, output = bundle.successor_belief.simulator_snapshot;
  const lineage = bundle.successor_belief.transition_lineage;
  if (!before.request || bundle.perspective !== before.perspective || bundle.perspective !== after.perspective
    || bundle.battle_id !== before.battle_id || bundle.battle_id !== after.battle_id
    || bundle.input_belief.observation.observation_id !== before.observation_id
    || bundle.successor_belief.observation.observation_id !== after.observation_id
    || bundle.successor_belief.parent_belief_id !== bundle.input_belief.belief_id
    || bundle.input_belief.battle_id !== bundle.battle_id || bundle.successor_belief.battle_id !== bundle.battle_id
    || bundle.input_belief.perspective !== bundle.perspective || bundle.successor_belief.perspective !== bundle.perspective
    || bundle.input_belief.transition_lineage && bundle.input_belief.transition_lineage.step_index + 1 !== transition.step_index
    || !input || !output || !lineage || input.branch_id !== transition.parent_branch_id
    || input.state_fingerprint !== transition.input_state_fingerprint || output.branch_id !== transition.branch_id
    || output.state_fingerprint !== transition.output_state_fingerprint || output.transition_id !== transition.transition_id
    || output.parent_branch_id !== transition.parent_branch_id || lineage.transition_id !== transition.transition_id
    || lineage.input_observation_id !== before.observation_id || lineage.output_observation_id !== after.observation_id
    || lineage.parent_branch_id !== transition.parent_branch_id || lineage.branch_id !== transition.branch_id
    || lineage.input_state_fingerprint !== transition.input_state_fingerprint || lineage.output_state_fingerprint !== transition.output_state_fingerprint
    || lineage.step_index !== transition.step_index || lineage.simulator_revision !== transition.simulator_revision
    || !Number.isSafeInteger(transition.step_index) || transition.step_index < 0) throw new Error('Linked record terminal authority requires validated observation/action/transition joins');
  serializeCanonicalAction(bundle.action, {player: bundle.perspective, rqid: before.request.rqid,
    force_switch: before.request.force_switch, legal_actions: before.request.legal_actions, side: before.request.side});
  if (transition.action_id !== bundle.action.action_id) throw new Error('Linked record action/transition mismatch');
  withTerminalOwner({predecessor: before as unknown as Record<string, unknown>,
    action: bundle.action,
    before: {step_index: transition.step_index, branch_id: input.branch_id, state_fingerprint: input.state_fingerprint}, transition,
    after: {step_index: transition.step_index + 1, branch_id: output.branch_id, state_fingerprint: output.state_fingerprint}},
    after as unknown as Record<string, unknown>, () => {
      validateObservableBattleState(after, rulesContext);
      serializeBeliefState(bundle.successor_belief, rulesContext);
    });
}

export function validateHistoricalPipelineLinkedRecordBundle(bundle: PipelineLinkedRecordBundle): void {
  const rulesContext = HISTORICAL10_CONTEXT;
  validatePipelineLinkedRecordBundle(bundle, rulesContext);
}
export function validateHistoricalPipelineEpisodeRecordBundle(bundle: PipelineLinkedRecordBundle | PipelineForcedSwitchRecordBundle): void {
  const rulesContext = HISTORICAL10_CONTEXT;
  validatePipelineEpisodeRecordBundle(bundle, rulesContext);
}
