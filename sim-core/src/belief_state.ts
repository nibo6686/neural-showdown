import { createHash } from 'node:crypto';
import {
  OBSERVABLE_STATE_SCHEMA_VERSION,
  validateObservableProtocolPrefix,
  type ObservableBattleState,
} from './observable_state';
import {
  SEEDED_TRANSITION_SCHEMA_VERSION,
  SEEDED_FORCED_SWITCH_SCHEMA_VERSION,
  assertForcedSwitchRoles,
  type SeededSnapshotRef,
  type PipelineTransitionMetadata,
} from './transition';
import type { PlayerID } from './types';

export const BELIEF_STATE_SCHEMA_VERSION = 'belief-state/v1' as const;

export type BeliefCategory = 'role' | 'move' | 'ability' | 'item' | 'tera_type';
export type BeliefAssertion = 'supports' | 'refutes';
export type BeliefInformationRegime = 'player' | 'simulator_research';
export type BeliefDisposition = 'possible' | 'supported' | 'ruled_out' | 'contradictory';

export class BeliefStateError extends Error {}
export class BeliefStateContradictionError extends BeliefStateError {}

export interface BeliefObservationReference {
  schema_version: typeof OBSERVABLE_STATE_SCHEMA_VERSION;
  observation_id: string;
  source_kind: ObservableBattleState['source_kind'];
  event_cursor: number;
  protocol_prefix_hash: string;
  snapshot_phase: ObservableBattleState['snapshot_phase'];
}

export interface BeliefSimulatorSnapshotLineage {
  branch_id: string;
  transition_id: string | null;
  state_fingerprint: string;
  parent_branch_id: string | null;
}

export interface BeliefTransitionLineage {
  transition_id: string;
  parent_branch_id: string;
  branch_id: string;
  input_state_fingerprint: string;
  output_state_fingerprint: string;
  simulator_revision: string;
  step_index: number;
  input_observation_id: string;
  output_observation_id: string;
}

export type BeliefEvidenceProvenance =
  | {
    kind: 'direct_observed';
    observation_id: string;
    event_cursor: number;
    event_index: number;
    record: string;
    record_hash: string;
  }
  | {
    kind: 'derived';
    observation_id: string;
    event_cursor: number;
    derivation_id: string;
    derivation_version: string;
    input_evidence_ids: string[];
  }
  | {
    kind: 'prior_knowledge';
    source_id: string;
    source_version: string;
    source_digest: string;
  }
  | {
    kind: 'simulator_only_truth';
    transition_id: string;
    simulator_revision: string;
  };

export interface BeliefEvidenceInput {
  perspective: PlayerID;
  category: BeliefCategory;
  subject_key: string;
  value: string;
  assertion: BeliefAssertion;
  provenance: BeliefEvidenceProvenance;
}

export interface BeliefEvidence extends BeliefEvidenceInput {
  evidence_id: string;
}

export interface BeliefCandidateInput {
  category: BeliefCategory;
  subject_key: string;
  value: string;
}

export interface BeliefCandidate extends BeliefCandidateInput {
  candidate_id: string;
  disposition: BeliefDisposition;
  evidence_ids: string[];
}

export type BeliefUnknownReason =
  | 'no_evidence'
  | 'unsupported_prior_dimension'
  | 'prior_unavailable'
  | 'contradictory_evidence';

export interface BeliefUnknownInput {
  category: BeliefCategory;
  subject_key: string;
  reason: BeliefUnknownReason;
}

export interface BeliefUnknown extends BeliefUnknownInput {}

export interface BeliefContradiction {
  candidate_id: string;
  evidence_ids: string[];
}

export interface BeliefState {
  schema_version: typeof BELIEF_STATE_SCHEMA_VERSION;
  belief_id: string;
  information_regime: BeliefInformationRegime;
  battle_id: string;
  perspective: PlayerID;
  observation: BeliefObservationReference;
  observation_history: BeliefObservationReference[];
  source_protocol_prefix: string[];
  parent_belief_id: string | null;
  simulator_snapshot: BeliefSimulatorSnapshotLineage | null;
  simulator_snapshot_history: BeliefSimulatorSnapshotLineage[];
  transition_lineage: BeliefTransitionLineage | null;
  transition_history: BeliefTransitionLineage[];
  candidates: BeliefCandidate[];
  evidence: BeliefEvidence[];
  unresolved: BeliefUnknown[];
  contradictions: BeliefContradiction[];
}

export interface BeliefTransitionInput {
  metadata: PipelineTransitionMetadata;
  input_observation_id: string;
  output_observation_id: string;
  output_snapshot: SeededSnapshotRef;
}

export interface BeliefStateInput {
  schema_version?: string;
  information_regime?: BeliefInformationRegime;
  observation: ObservableBattleState;
  parent?: BeliefState | null;
  simulator_snapshot?: SeededSnapshotRef | null;
  transition?: BeliefTransitionInput | null;
  candidates?: readonly BeliefCandidateInput[];
  evidence?: readonly BeliefEvidenceInput[];
  unresolved?: readonly BeliefUnknownInput[];
}

type BeliefStatePayload = Omit<BeliefState, 'belief_id'>;

const BELIEF_CATEGORIES = new Set<BeliefCategory>(['role', 'move', 'ability', 'item', 'tera_type']);
const UNKNOWN_REASONS = new Set<BeliefUnknownReason>([
  'no_evidence', 'unsupported_prior_dimension', 'prior_unavailable', 'contradictory_evidence',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function exactKeys(value: Record<string, unknown>, keys: readonly string[], label: string): void {
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    throw new BeliefStateError(`${label} fields are not exact.`);
  }
}

function canonicalize(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(',')}]`;
  if (isRecord(value)) {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalize(value[key])}`).join(',')}}`;
  }
  const serialized = JSON.stringify(value);
  if (serialized === undefined) throw new BeliefStateError('Belief serialization contains an unsupported value.');
  return serialized;
}

function sha256(value: unknown): string {
  return createHash('sha256').update(canonicalize(value), 'utf8').digest('hex');
}

function recordSha256(record: string): string {
  return createHash('sha256').update(record, 'utf8').digest('hex');
}

function deepFreeze<T>(value: T): T {
  if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
  Object.freeze(value);
  for (const child of Object.values(value as Record<string, unknown>)) deepFreeze(child);
  return value;
}

function normalizedString(value: unknown, label: string): string {
  if (typeof value !== 'string') throw new BeliefStateError(`${label} must be a string.`);
  const normalized = value.normalize('NFC').trim();
  if (!normalized) throw new BeliefStateError(`${label} must not be empty.`);
  return normalized;
}

function isPlayer(value: unknown): value is PlayerID {
  return value === 'p1' || value === 'p2';
}

function isSafeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value);
}

function compareText(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function assertDigest(value: unknown, label: string): asserts value is string {
  if (typeof value !== 'string' || !/^[a-f0-9]{64}$/.test(value)) {
    throw new BeliefStateError(`${label} must be a lowercase SHA-256 digest.`);
  }
}

function assertNonEmptyString(value: unknown, label: string): asserts value is string {
  if (typeof value !== 'string' || value.normalize('NFC').trim() !== value || !value) {
    throw new BeliefStateError(`${label} must be a normalized non-empty string.`);
  }
}

function assertBoolean(value: unknown, label: string): void {
  if (typeof value !== 'boolean') throw new BeliefStateError(`${label} must be a boolean.`);
}

function assertNullableString(value: unknown, label: string): void {
  if (value !== null && typeof value !== 'string') throw new BeliefStateError(`${label} must be a string or null.`);
}

function assertNumberRecord(value: unknown, label: string): void {
  if (!isRecord(value) || Object.values(value).some((item) => typeof item !== 'number' || !Number.isFinite(item))) {
    throw new BeliefStateError(`${label} must contain only finite numeric values.`);
  }
}

function assertStringArray(value: unknown, label: string): void {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) {
    throw new BeliefStateError(`${label} must be an array of strings.`);
  }
}

function assertSanitizedProtocolPrefix(prefix: unknown, label: string): asserts prefix is string[] {
  if (!Array.isArray(prefix)) throw new BeliefStateError(`${label} must be an array.`);
  for (const [index, record] of prefix.entries()) {
    if (typeof record !== 'string' || !record || record.trim() !== record || /[\r\n]/.test(record)) {
      throw new BeliefStateError(`${label} contains a malformed record at index ${index}.`);
    }
    if (record.startsWith('|request|')) {
      const payload = record.slice('|request|'.length);
      let request: unknown;
      try {
        request = JSON.parse(payload);
      } catch {
        throw new BeliefStateError(`${label} contains an unsanitized request record.`);
      }
      if (!isRecord(request) || Object.keys(request).some((key) => key !== 'rqid')
        || (request.rqid !== undefined && !isSafeInteger(request.rqid))
        || canonicalize(request) !== payload) {
        throw new BeliefStateError(`${label} contains an unsanitized request record.`);
      }
    }
  }
}

function assertObservablePokemon(value: unknown, visibility: 'self' | 'opponent'): void {
  if (!isRecord(value)) throw new BeliefStateError('Observation Pokémon view must be an object.');
  const base = [
    'slot', 'ident', 'name', 'species', 'base_species', 'current_species', 'displayed_species',
    'species_source', 'transformed', 'displayed_species_uncertain', 'illusion_revealed', 'details',
    'active', 'fainted', 'hp_text', 'hp_ratio', 'status', 'status_source', 'status_started_turn',
    'status_turns_public', 'gender', 'level', 'types', 'terastallized', 'volatiles',
  ];
  const selfOnly = [
    'last_item', 'item_state', 'item_suppressed', 'ability', 'base_ability', 'ability_state',
    'ability_suppressed', 'moves', 'revealed_moves', 'tera_type', 'stats', 'boosts',
  ];
  const optional = visibility === 'self' ? ['item', ...selfOnly] : ['item'];
  const allowed = [...base, ...optional];
  if (base.some((key) => !(key in value)) || Object.keys(value).some((key) => !allowed.includes(key))) {
    throw new BeliefStateError('Observation Pokémon view does not match the supported public schema.');
  }
  if (visibility === 'self' && optional.some((key) => !(key in value))) {
    throw new BeliefStateError('Self Pokémon view is incomplete.');
  }
  if (visibility === 'opponent' && value.item !== undefined && value.item !== 'has-item') {
    throw new BeliefStateError('Opponent Pokémon view contains a private item value.');
  }
  for (const key of ['ident', 'name', 'species', 'details']) assertNullableString(value[key], `Pokémon ${key}`);
  for (const key of ['base_species', 'current_species', 'displayed_species', 'hp_text', 'status', 'gender']) {
    assertNullableString(value[key], `Pokémon ${key}`);
  }
  for (const key of ['transformed', 'displayed_species_uncertain', 'illusion_revealed', 'active', 'fainted', 'terastallized']) {
    assertBoolean(value[key], `Pokémon ${key}`);
  }
  if (!isSafeInteger(value.slot) || (value.hp_ratio !== null && typeof value.hp_ratio !== 'number')
    || (value.level !== null && !isSafeInteger(value.level))) {
    throw new BeliefStateError('Observation Pokémon numeric fields are malformed.');
  }
  for (const key of ['status_started_turn', 'status_turns_public']) {
    if (value[key] !== null && !isSafeInteger(value[key])) throw new BeliefStateError(`Pokémon ${key} is malformed.`);
  }
  assertStringArray(value.types, 'Pokémon types');
  assertStringArray(value.volatiles, 'Pokémon volatiles');
  if (visibility === 'self') {
    for (const key of ['item', 'last_item', 'ability', 'base_ability', 'tera_type']) assertNullableString(value[key], `Pokémon ${key}`);
    for (const key of ['item_suppressed', 'ability_suppressed']) assertBoolean(value[key], `Pokémon ${key}`);
    for (const key of ['moves', 'revealed_moves']) assertStringArray(value[key], `Pokémon ${key}`);
    for (const key of ['stats', 'boosts']) assertNumberRecord(value[key], `Pokémon ${key}`);
  }
}

function assertObservableRequest(request: unknown, perspective: PlayerID): void {
  if (request === null) return;
  if (!isRecord(request)) throw new BeliefStateError('Observation request must be an object or null.');
  exactKeys(request, [
    'player', 'wait', 'team_preview', 'force_switch', 'trapped', 'rqid', 'active', 'side', 'legal_actions',
  ], 'Observation request');
  if (request.player !== perspective || !isSafeInteger(request.rqid) && request.rqid !== null) {
    throw new BeliefStateError('Observation request perspective or rqid is invalid.');
  }
  for (const key of ['wait', 'team_preview', 'force_switch', 'trapped']) assertBoolean(request[key], `Request ${key}`);
  if (!Array.isArray(request.side) || !isRecord(request.legal_actions)) {
    throw new BeliefStateError('Observation request side or legal actions are malformed.');
  }
  exactKeys(request.legal_actions, ['mask', 'actions', 'available_indices'], 'Observation legal actions');
  const legal = request.legal_actions;
  if (!Array.isArray(legal.mask) || legal.mask.some((item) => typeof item !== 'boolean')
    || !Array.isArray(legal.actions) || legal.actions.length !== legal.mask.length
    || !Array.isArray(legal.available_indices) || legal.available_indices.some((item) => !isSafeInteger(item))) {
    throw new BeliefStateError('Observation legal actions are malformed.');
  }
  for (const action of legal.actions) {
    if (action === null) continue;
    if (!isRecord(action)) throw new BeliefStateError('Observation legal action is malformed.');
    const allowed = ['index', 'kind', 'choice', 'label', 'move', 'slot'];
    const required = ['index', 'kind', 'choice', 'label'];
    if (required.some((key) => !(key in action)) || Object.keys(action).some((key) => !allowed.includes(key))) {
      throw new BeliefStateError('Observation legal action fields are malformed.');
    }
  }
  for (const pokemon of request.side) {
    if (!isRecord(pokemon)) throw new BeliefStateError('Observation request side Pokémon is malformed.');
    exactKeys(pokemon, [
      'slot', 'ident', 'details', 'condition', 'active', 'moves', 'stats', 'base_ability', 'ability',
      'item', 'tera_type', 'terastallized',
    ], 'Observation request side Pokémon');
    assertStringArray(pokemon.moves, 'Request Pokémon moves');
    assertNumberRecord(pokemon.stats, 'Request Pokémon stats');
  }
  if (request.active !== null) {
    if (!isRecord(request.active)) throw new BeliefStateError('Observation active request is malformed.');
    exactKeys(request.active, ['moves', 'can_terastallize', 'tera_type', 'trapped', 'can_switch'], 'Observation active request');
    if (!Array.isArray(request.active.moves)) throw new BeliefStateError('Observation active request moves are malformed.');
  }
}

function observationReference(observation: ObservableBattleState): BeliefObservationReference {
  return {
    schema_version: observation.schema_version,
    observation_id: observation.observation_id,
    source_kind: observation.source_kind,
    event_cursor: observation.event_cursor,
    protocol_prefix_hash: observation.protocol_prefix_hash,
    snapshot_phase: observation.snapshot_phase,
  };
}

function assertObservation(observation: ObservableBattleState): void {
  if (!isRecord(observation) || observation.schema_version !== OBSERVABLE_STATE_SCHEMA_VERSION) {
    throw new BeliefStateError('Unsupported observable schema for BeliefState.');
  }
  exactKeys(observation, [
    'schema_version', 'source_kind', 'battle_id', 'perspective', 'event_cursor', 'observation_id',
    'protocol_prefix_hash', 'snapshot_phase', 'other_phase', 'request', 'decision_availability',
    'protocol_prefix', 'view',
  ], 'Observable state');
  if (!isPlayer(observation.perspective) || observation.view?.player !== observation.perspective) {
    throw new BeliefStateError('Observation perspective does not match its view.');
  }
  if (typeof observation.source_kind !== 'string' || !['sim_core', 'replay', 'live'].includes(observation.source_kind)
    || typeof observation.battle_id !== 'string' || !observation.battle_id.trim()
    || !['pre_decision', 'post_resolution', 'forced_switch', 'terminal', 'other'].includes(observation.snapshot_phase)
    || (observation.other_phase !== null && typeof observation.other_phase !== 'string')) {
    throw new BeliefStateError('Observation source, battle, or phase metadata is invalid.');
  }
  if (!Array.isArray(observation.protocol_prefix) || !isSafeInteger(observation.event_cursor)
    || observation.event_cursor < 0 || observation.event_cursor !== observation.protocol_prefix.length
    ) {
    throw new BeliefStateError('Observation cursor must equal its normalized protocol prefix length.');
  }
  assertSanitizedProtocolPrefix(observation.protocol_prefix, 'Observation protocol prefix');
  validateObservableProtocolPrefix(observation.protocol_prefix, observation.perspective, observation.view, observation.request);
  assertDigest(observation.protocol_prefix_hash, 'Observation protocol_prefix_hash');
  if (sha256(observation.protocol_prefix) !== observation.protocol_prefix_hash) {
    throw new BeliefStateError('Observation protocol prefix hash is invalid.');
  }
  if (!isRecord(observation.view)) throw new BeliefStateError('Observation view must be an object.');
  exactKeys(observation.view, [
    'format', 'gen', 'turn', 'player', 'opponent', 'terminated', 'winner', 'names', 'team_size',
    'active', 'field', 'self_team', 'opponent_team',
  ], 'Observation battle view');
  const view = observation.view;
  const expectedOpponent: PlayerID = observation.perspective === 'p1' ? 'p2' : 'p1';
  if (view.player !== observation.perspective || view.opponent !== expectedOpponent
    || typeof view.format !== 'string' || !view.format.trim()
    || !isSafeInteger(view.turn) || view.turn < 0
    || (view.gen !== null && !isSafeInteger(view.gen))) {
    throw new BeliefStateError('Observation battle view metadata is invalid.');
  }
  assertBoolean(view.terminated, 'Observation terminated');
  if (view.winner !== null && view.winner !== 'tie' && !isPlayer(view.winner)) {
    throw new BeliefStateError('Observation winner is invalid.');
  }
  for (const key of ['names', 'team_size']) {
    if (!isRecord(view[key])) throw new BeliefStateError(`Observation ${key} must be an object.`);
    exactKeys(view[key], ['p1', 'p2'], `Observation ${key}`);
  }
  if (Object.values(view.names).some((name) => name !== null && typeof name !== 'string')
    || Object.values(view.team_size).some((size) => !isSafeInteger(size))) {
    throw new BeliefStateError('Observation names or team sizes are invalid.');
  }
  if (!isRecord(view.active)) throw new BeliefStateError('Observation active slots must be an object.');
  exactKeys(view.active, ['self', 'opponent'], 'Observation active slots');
  if (Object.values(view.active).some((slot) => slot !== null && !isSafeInteger(slot))) {
    throw new BeliefStateError('Observation active slots are invalid.');
  }
  if (!isRecord(view.field)) throw new BeliefStateError('Observation field must be an object.');
  exactKeys(view.field, ['weather', 'terrain', 'pseudo_weather', 'side_conditions'], 'Observation field');
  assertNullableString(view.field.weather, 'Observation weather');
  assertNullableString(view.field.terrain, 'Observation terrain');
  assertStringArray(view.field.pseudo_weather, 'Observation pseudo weather');
  if (!isRecord(view.field.side_conditions)) throw new BeliefStateError('Observation side conditions are malformed.');
  exactKeys(view.field.side_conditions, ['self', 'opponent'], 'Observation side conditions');
  assertNumberRecord(view.field.side_conditions.self, 'Observation self side conditions');
  assertNumberRecord(view.field.side_conditions.opponent, 'Observation opponent side conditions');
  if (!Array.isArray(view.self_team) || !Array.isArray(view.opponent_team)) {
    throw new BeliefStateError('Observation teams must be arrays.');
  }
  view.self_team.forEach((pokemon) => assertObservablePokemon(pokemon, 'self'));
  view.opponent_team.forEach((pokemon) => assertObservablePokemon(pokemon, 'opponent'));
  assertObservableRequest(observation.request, observation.perspective);
  if (!isRecord(observation.decision_availability)) throw new BeliefStateError('Observation decision availability is malformed.');
  exactKeys(observation.decision_availability, ['available', 'reason', 'legal_action_indices'], 'Observation decision availability');
  assertBoolean(observation.decision_availability.available, 'Observation decision availability');
  const availability = observation.decision_availability;
  if (!['request', 'requestless', 'waiting', 'terminal', 'no_legal_actions'].includes(availability.reason)
    || (availability.legal_action_indices !== null && (!Array.isArray(availability.legal_action_indices)
      || availability.legal_action_indices.some((index) => !isSafeInteger(index))))) {
    throw new BeliefStateError('Observation decision availability values are invalid.');
  }
  let expectedAvailability: ObservableBattleState['decision_availability'];
  if (view.terminated) {
    expectedAvailability = { available: false, reason: 'terminal', legal_action_indices: null };
  } else if (observation.request === null) {
    expectedAvailability = { available: false, reason: 'requestless', legal_action_indices: null };
  } else if (observation.request.wait) {
    expectedAvailability = { available: false, reason: 'waiting', legal_action_indices: null };
  } else {
    const indices = [...observation.request.legal_actions.available_indices];
    for (const index of indices) {
      if (index < 0 || index >= observation.request.legal_actions.mask.length
        || observation.request.legal_actions.mask[index] !== true) {
        throw new BeliefStateError('Observation legal action index is inconsistent with its request mask.');
      }
    }
    expectedAvailability = indices.length
      ? { available: true, reason: 'request', legal_action_indices: indices }
      : { available: false, reason: 'no_legal_actions', legal_action_indices: [] };
  }
  if (canonicalize(availability) !== canonicalize(expectedAvailability)) {
    throw new BeliefStateError('Observation decision availability disagrees with its request or view.');
  }
  if (availability.reason === 'terminal' && !view.terminated) {
    throw new BeliefStateError('Terminal availability requires a terminated view.');
  }
  if (observation.snapshot_phase === 'terminal' && !view.terminated) {
    throw new BeliefStateError('Terminal snapshot requires a terminated view.');
  }
  if (observation.snapshot_phase === 'forced_switch'
    && (!isRecord(observation.request) || observation.request.force_switch !== true)) {
    throw new BeliefStateError('Forced-switch snapshot requires a force-switch request.');
  }
  if (typeof observation.observation_id !== 'string' || !/^obs-[a-f0-9]{64}$/.test(observation.observation_id)) {
    throw new BeliefStateError('Observation ID is invalid.');
  }
  const { observation_id: _observationId, protocol_prefix: _prefix, ...identity } = observation;
  if (`obs-${sha256(identity)}` !== observation.observation_id) {
    throw new BeliefStateError('Observation identity is invalid.');
  }
}

function candidateKey(candidate: BeliefCandidateInput): string {
  return canonicalize([candidate.category, candidate.subject_key, candidate.value]);
}

function candidateId(candidate: BeliefCandidateInput): string {
  return `hyp-${sha256([candidate.category, candidate.subject_key, candidate.value])}`;
}

function evidenceId(evidence: BeliefEvidenceInput): string {
  return `evidence-${sha256(evidence)}`;
}

function normalizeCandidate(candidate: BeliefCandidateInput): BeliefCandidateInput {
  if (!isRecord(candidate)) throw new BeliefStateError('Belief candidate must be an object.');
  exactKeys(candidate as Record<string, unknown>, ['category', 'subject_key', 'value'], 'Belief candidate');
  if (!BELIEF_CATEGORIES.has(candidate.category)) throw new BeliefStateError('Unsupported belief candidate category.');
  return {
    category: candidate.category,
    subject_key: normalizedString(candidate.subject_key, 'Candidate subject_key'),
    value: normalizedString(candidate.value, 'Candidate value'),
  };
}

function normalizeProvenance(
  provenance: BeliefEvidenceProvenance,
  observation: ObservableBattleState,
  informationRegime: BeliefInformationRegime,
  transition: BeliefTransitionLineage | null,
  simulatorSnapshot: BeliefSimulatorSnapshotLineage | null,
): BeliefEvidenceProvenance {
  if (!isRecord(provenance) || typeof provenance.kind !== 'string') {
    throw new BeliefStateError('Belief evidence provenance is malformed.');
  }
  if (provenance.kind === 'direct_observed') {
    exactKeys(provenance, ['kind', 'observation_id', 'event_cursor', 'event_index', 'record', 'record_hash'], 'Direct evidence provenance');
    if (provenance.observation_id !== observation.observation_id || provenance.event_cursor !== observation.event_cursor) {
      throw new BeliefStateError('Direct evidence observation does not match base observation.');
    }
    if (!isSafeInteger(provenance.event_index) || provenance.event_index < 0 || provenance.event_index >= observation.event_cursor) {
      throw new BeliefStateError('Direct evidence event_index must be before event_cursor.');
    }
    const record = normalizedString(provenance.record, 'Direct evidence record');
    if (record.startsWith('|request|') || record !== observation.protocol_prefix[provenance.event_index]) {
      throw new BeliefStateError('Direct evidence record does not match a public base-observation record.');
    }
    assertDigest(provenance.record_hash, 'Direct evidence record_hash');
    if (recordSha256(record) !== provenance.record_hash) throw new BeliefStateError('Direct evidence record hash is invalid.');
    return {
      kind: 'direct_observed',
      observation_id: observation.observation_id,
      event_cursor: observation.event_cursor,
      event_index: provenance.event_index,
      record,
      record_hash: provenance.record_hash,
    };
  }
  if (provenance.kind === 'derived') {
    exactKeys(provenance, ['kind', 'observation_id', 'event_cursor', 'derivation_id', 'derivation_version', 'input_evidence_ids'], 'Derived evidence provenance');
    if (provenance.observation_id !== observation.observation_id || provenance.event_cursor !== observation.event_cursor) {
      throw new BeliefStateError('Derived evidence observation does not match base observation.');
    }
    if (!Array.isArray(provenance.input_evidence_ids)
      || provenance.input_evidence_ids.some((id) => typeof id !== 'string' || !id.trim())) {
      throw new BeliefStateError('Derived evidence input_evidence_ids must be non-empty strings.');
    }
    return {
      kind: 'derived',
      observation_id: observation.observation_id,
      event_cursor: observation.event_cursor,
      derivation_id: normalizedString(provenance.derivation_id, 'Derivation ID'),
      derivation_version: normalizedString(provenance.derivation_version, 'Derivation version'),
      input_evidence_ids: [...new Set(provenance.input_evidence_ids as string[])].sort(),
    };
  }
  if (provenance.kind === 'prior_knowledge') {
    exactKeys(provenance, ['kind', 'source_id', 'source_version', 'source_digest'], 'Prior evidence provenance');
    assertDigest(provenance.source_digest, 'Prior source digest');
    return {
      kind: 'prior_knowledge',
      source_id: normalizedString(provenance.source_id, 'Prior source ID'),
      source_version: normalizedString(provenance.source_version, 'Prior source version'),
      source_digest: provenance.source_digest,
    };
  }
  if (provenance.kind === 'simulator_only_truth') {
    exactKeys(provenance, ['kind', 'transition_id', 'simulator_revision'], 'Simulator-only evidence provenance');
    if (informationRegime !== 'simulator_research') {
      throw new BeliefStateError('Simulator-only truth requires simulator_research information_regime.');
    }
    const transitionId = normalizedString(provenance.transition_id, 'Simulator-only transition ID');
    const simulatorRevision = normalizedString(provenance.simulator_revision, 'Simulator-only simulator revision');
    if (simulatorSnapshot?.transition_id !== transitionId) {
      throw new BeliefStateError('Simulator-only truth transition does not match simulator snapshot lineage.');
    }
    if (transition && transition.simulator_revision !== simulatorRevision) {
      throw new BeliefStateError('Simulator-only truth revision does not match transition lineage.');
    }
    return { kind: 'simulator_only_truth', transition_id: transitionId, simulator_revision: simulatorRevision };
  }
  throw new BeliefStateError('Unsupported belief evidence provenance kind.');
}

function normalizeEvidence(
  evidence: BeliefEvidenceInput,
  observation: ObservableBattleState,
  informationRegime: BeliefInformationRegime,
  transition: BeliefTransitionLineage | null,
  simulatorSnapshot: BeliefSimulatorSnapshotLineage | null,
): BeliefEvidence {
  if (!isRecord(evidence)) throw new BeliefStateError('Belief evidence must be an object.');
  exactKeys(evidence as Record<string, unknown>, ['perspective', 'category', 'subject_key', 'value', 'assertion', 'provenance'], 'Belief evidence');
  if (!isPlayer(evidence.perspective) || evidence.perspective !== observation.perspective) {
    throw new BeliefStateError('Belief evidence perspective does not match base observation.');
  }
  if (!BELIEF_CATEGORIES.has(evidence.category)) throw new BeliefStateError('Unsupported belief evidence category.');
  if (evidence.assertion !== 'supports' && evidence.assertion !== 'refutes') {
    throw new BeliefStateError('Belief evidence assertion must be supports or refutes.');
  }
  const normalized: BeliefEvidenceInput = {
    perspective: evidence.perspective,
    category: evidence.category,
    subject_key: normalizedString(evidence.subject_key, 'Evidence subject_key'),
    value: normalizedString(evidence.value, 'Evidence value'),
    assertion: evidence.assertion,
    provenance: normalizeProvenance(evidence.provenance, observation, informationRegime, transition, simulatorSnapshot),
  };
  return { ...normalized, evidence_id: evidenceId(normalized) };
}

function normalizeUnknown(unknown: BeliefUnknownInput): BeliefUnknown {
  if (!isRecord(unknown)) throw new BeliefStateError('Unresolved belief entry must be an object.');
  exactKeys(unknown as Record<string, unknown>, ['category', 'subject_key', 'reason'], 'Unresolved belief entry');
  if (!BELIEF_CATEGORIES.has(unknown.category) || !UNKNOWN_REASONS.has(unknown.reason)) {
    throw new BeliefStateError('Unsupported unresolved belief category or reason.');
  }
  return {
    category: unknown.category,
    subject_key: normalizedString(unknown.subject_key, 'Unresolved subject_key'),
    reason: unknown.reason,
  };
}

function normalizeSnapshot(snapshot: SeededSnapshotRef, observation: ObservableBattleState): BeliefSimulatorSnapshotLineage {
  if (!isRecord(snapshot) || snapshot.schema_version !== SEEDED_TRANSITION_SCHEMA_VERSION) {
    throw new BeliefStateError('Unsupported simulator snapshot schema for BeliefState.');
  }
  exactKeys(snapshot, [
    'schema_version', 'snapshot_handle', 'format', 'root_seed', 'state_fingerprint',
    'parent_branch_id', 'transition_id', 'branch_id',
  ], 'Simulator snapshot');
  if (snapshot.format !== observation.view.format) throw new BeliefStateError('Simulator snapshot format does not match observation.');
  if (typeof snapshot.snapshot_handle !== 'string' || !snapshot.snapshot_handle.trim()
    || !Array.isArray(snapshot.root_seed) || snapshot.root_seed.length !== 4
    || snapshot.root_seed.some((seed) => !isSafeInteger(seed))) {
    throw new BeliefStateError('Simulator snapshot handle or root seed is invalid.');
  }
  if (typeof snapshot.branch_id !== 'string' || !snapshot.branch_id.trim()) throw new BeliefStateError('Simulator snapshot branch_id is invalid.');
  if (snapshot.parent_branch_id !== null && (typeof snapshot.parent_branch_id !== 'string' || !snapshot.parent_branch_id.trim())) {
    throw new BeliefStateError('Simulator snapshot parent_branch_id is invalid.');
  }
  if (snapshot.transition_id !== null && (typeof snapshot.transition_id !== 'string' || !snapshot.transition_id.trim())) {
    throw new BeliefStateError('Simulator snapshot transition_id is invalid.');
  }
  assertDigest(snapshot.state_fingerprint, 'Simulator snapshot state_fingerprint');
  return {
    branch_id: snapshot.branch_id,
    transition_id: snapshot.transition_id,
    state_fingerprint: snapshot.state_fingerprint,
    parent_branch_id: snapshot.parent_branch_id,
  };
}

function normalizeTransition(
  transition: BeliefTransitionInput,
  observation: ObservableBattleState,
  parent: BeliefState | null,
): { lineage: BeliefTransitionLineage; snapshot: BeliefSimulatorSnapshotLineage } {
  if (!parent) throw new BeliefStateError('A transition-linked belief requires a parent belief.');
  if (!isRecord(transition)) throw new BeliefStateError('Belief transition input is malformed.');
  exactKeys(transition, ['metadata', 'input_observation_id', 'output_observation_id', 'output_snapshot'], 'Belief transition input');
  if (!isRecord(transition.metadata)) throw new BeliefStateError('Seeded transition metadata is malformed.');
  const metadata = transition.metadata as unknown as PipelineTransitionMetadata;
  exactKeys(metadata as unknown as Record<string, unknown>, [
    'schema_version', 'transition_id', 'parent_branch_id', 'branch_id', 'input_state_fingerprint',
    'output_state_fingerprint', 'root_seed', 'action_ids', 'emitted_log_delta', 'simulator_revision', 'step_index',
    ...(metadata.schema_version === SEEDED_FORCED_SWITCH_SCHEMA_VERSION ? ['acting_player', 'waiting_player'] : []),
  ], 'Seeded transition metadata');
  if (metadata.schema_version !== SEEDED_TRANSITION_SCHEMA_VERSION && metadata.schema_version !== SEEDED_FORCED_SWITCH_SCHEMA_VERSION) {
    throw new BeliefStateError('Unsupported seeded transition schema for BeliefState.');
  }
  if (typeof transition.input_observation_id !== 'string' || !/^obs-[a-f0-9]{64}$/.test(transition.input_observation_id)
    || typeof transition.output_observation_id !== 'string' || !/^obs-[a-f0-9]{64}$/.test(transition.output_observation_id)) {
    throw new BeliefStateError('Transition observation IDs are malformed.');
  }
  for (const [key, value] of Object.entries({
    transition_id: metadata.transition_id,
    parent_branch_id: metadata.parent_branch_id,
    branch_id: metadata.branch_id,
    simulator_revision: metadata.simulator_revision,
  })) assertNonEmptyString(value, `Seeded transition ${key}`);
  if (!Array.isArray(metadata.root_seed) || metadata.root_seed.length !== 4
    || metadata.root_seed.some((seed) => !isSafeInteger(seed))) {
    throw new BeliefStateError('Seeded transition root_seed is malformed.');
  }
  if (!isRecord(metadata.action_ids)) throw new BeliefStateError('Seeded transition action_ids are malformed.');
  if (metadata.schema_version === SEEDED_FORCED_SWITCH_SCHEMA_VERSION) {
    assertForcedSwitchRoles(metadata);
    exactKeys(metadata.action_ids, [metadata.acting_player], 'Forced-switch action_ids');
    assertNonEmptyString(metadata.action_ids[metadata.acting_player], 'Forced-switch actor action ID');
  } else {
    exactKeys(metadata.action_ids, ['p1', 'p2'], 'Seeded transition action_ids');
    assertNonEmptyString(metadata.action_ids.p1, 'Seeded transition p1 action ID');
    assertNonEmptyString(metadata.action_ids.p2, 'Seeded transition p2 action ID');
  }
  if (!Array.isArray(metadata.emitted_log_delta) || metadata.emitted_log_delta.some((record) => typeof record !== 'string')) {
    throw new BeliefStateError('Seeded transition emitted_log_delta is malformed.');
  }
  if (transition.input_observation_id !== parent.observation.observation_id) {
    throw new BeliefStateError('Transition input observation does not match parent belief.');
  }
  if (transition.output_observation_id !== observation.observation_id) {
    throw new BeliefStateError('Transition output observation does not match base observation.');
  }
  if (!parent.simulator_snapshot) throw new BeliefStateError('Parent belief has no simulator snapshot lineage.');
  if (metadata.parent_branch_id !== parent.simulator_snapshot.branch_id) {
    throw new BeliefStateError('Transition parent branch does not match parent belief snapshot.');
  }
  if (metadata.input_state_fingerprint !== parent.simulator_snapshot.state_fingerprint) {
    throw new BeliefStateError('Transition input fingerprint does not match parent belief snapshot.');
  }
  if (!isSafeInteger(metadata.step_index) || metadata.step_index < 0) {
    throw new BeliefStateError('Seeded transition lineage is incomplete.');
  }
  assertDigest(metadata.input_state_fingerprint, 'Transition input fingerprint');
  assertDigest(metadata.output_state_fingerprint, 'Transition output fingerprint');
  if (parent.transition_lineage) {
    if (metadata.simulator_revision !== parent.transition_lineage.simulator_revision
      || metadata.step_index <= parent.transition_lineage.step_index) {
      throw new BeliefStateError('Transition revision or step index is stale.');
    }
  }
  const snapshot = normalizeSnapshot(transition.output_snapshot, observation);
  if (snapshot.transition_id !== metadata.transition_id || snapshot.branch_id !== metadata.branch_id
    || snapshot.parent_branch_id !== metadata.parent_branch_id
    || snapshot.state_fingerprint !== metadata.output_state_fingerprint) {
    throw new BeliefStateError('Transition output snapshot does not match transition metadata.');
  }
  return {
    lineage: {
      transition_id: metadata.transition_id,
      parent_branch_id: metadata.parent_branch_id,
      branch_id: metadata.branch_id,
      input_state_fingerprint: metadata.input_state_fingerprint,
      output_state_fingerprint: metadata.output_state_fingerprint,
      simulator_revision: metadata.simulator_revision,
      step_index: metadata.step_index,
      input_observation_id: transition.input_observation_id,
      output_observation_id: transition.output_observation_id,
    },
    snapshot,
  };
}

function assertParentEvidence(entry: unknown, parent: BeliefState): BeliefEvidence {
  if (!isRecord(entry)) throw new BeliefStateError('Parent evidence must be an object.');
  exactKeys(entry, ['perspective', 'category', 'subject_key', 'value', 'assertion', 'provenance', 'evidence_id'], 'Parent evidence');
  if (!isPlayer(entry.perspective) || entry.perspective !== parent.perspective
    || !BELIEF_CATEGORIES.has(entry.category as BeliefCategory)
    || (entry.assertion !== 'supports' && entry.assertion !== 'refutes')) {
    throw new BeliefStateError('Parent evidence perspective, category, or assertion is invalid.');
  }
  const subjectKey = normalizedString(entry.subject_key, 'Parent evidence subject_key');
  const value = normalizedString(entry.value, 'Parent evidence value');
  const provenance = entry.provenance;
  if (!isRecord(provenance) || typeof provenance.kind !== 'string') {
    throw new BeliefStateError('Parent evidence provenance is malformed.');
  }
  let normalizedProvenance: BeliefEvidenceProvenance;
  if (provenance.kind === 'direct_observed') {
    exactKeys(provenance, ['kind', 'observation_id', 'event_cursor', 'event_index', 'record', 'record_hash'], 'Parent direct evidence provenance');
    if (typeof provenance.observation_id !== 'string' || !/^obs-[a-f0-9]{64}$/.test(provenance.observation_id)
      || !isSafeInteger(provenance.event_cursor) || provenance.event_cursor < 1
      || provenance.event_cursor > parent.observation.event_cursor
      || !isSafeInteger(provenance.event_index) || provenance.event_index < 0
      || provenance.event_index >= provenance.event_cursor) {
      throw new BeliefStateError('Parent direct evidence observation or cursor is invalid.');
    }
    if (!parent.observation_history.some((reference) => (
      reference.observation_id === provenance.observation_id && reference.event_cursor === provenance.event_cursor
    ))) throw new BeliefStateError('Parent direct evidence is not bound to its observation history.');
    const record = normalizedString(provenance.record, 'Parent direct evidence record');
    if (record.startsWith('|request|') || parent.source_protocol_prefix[provenance.event_index] !== record) {
      throw new BeliefStateError('Parent direct evidence record is not in its public source prefix.');
    }
    assertDigest(provenance.record_hash, 'Parent direct evidence record_hash');
    if (recordSha256(record) !== provenance.record_hash) throw new BeliefStateError('Parent direct evidence record hash is invalid.');
    normalizedProvenance = {
      kind: 'direct_observed', observation_id: provenance.observation_id,
      event_cursor: provenance.event_cursor, event_index: provenance.event_index,
      record, record_hash: provenance.record_hash,
    };
  } else if (provenance.kind === 'derived') {
    exactKeys(provenance, ['kind', 'observation_id', 'event_cursor', 'derivation_id', 'derivation_version', 'input_evidence_ids'], 'Parent derived evidence provenance');
    if (typeof provenance.observation_id !== 'string' || !/^obs-[a-f0-9]{64}$/.test(provenance.observation_id)
      || !isSafeInteger(provenance.event_cursor) || provenance.event_cursor < 0
      || provenance.event_cursor > parent.observation.event_cursor
      || !Array.isArray(provenance.input_evidence_ids)
      || provenance.input_evidence_ids.some((id) => typeof id !== 'string' || !id.trim())) {
      throw new BeliefStateError('Parent derived evidence observation or inputs are invalid.');
    }
    if (!parent.observation_history.some((reference) => (
      reference.observation_id === provenance.observation_id && reference.event_cursor === provenance.event_cursor
    ))) throw new BeliefStateError('Parent derived evidence is not bound to its observation history.');
    normalizedProvenance = {
      kind: 'derived', observation_id: provenance.observation_id, event_cursor: provenance.event_cursor,
      derivation_id: normalizedString(provenance.derivation_id, 'Parent derivation ID'),
      derivation_version: normalizedString(provenance.derivation_version, 'Parent derivation version'),
      input_evidence_ids: [...new Set(provenance.input_evidence_ids as string[])].sort(),
    };
  } else if (provenance.kind === 'prior_knowledge') {
    exactKeys(provenance, ['kind', 'source_id', 'source_version', 'source_digest'], 'Parent prior evidence provenance');
    assertDigest(provenance.source_digest, 'Parent prior source digest');
    normalizedProvenance = {
      kind: 'prior_knowledge', source_id: normalizedString(provenance.source_id, 'Parent prior source ID'),
      source_version: normalizedString(provenance.source_version, 'Parent prior source version'),
      source_digest: provenance.source_digest,
    };
  } else if (provenance.kind === 'simulator_only_truth') {
    exactKeys(provenance, ['kind', 'transition_id', 'simulator_revision'], 'Parent simulator-only evidence provenance');
    if (parent.information_regime !== 'simulator_research') {
      throw new BeliefStateError('Parent simulator-only truth requires simulator_research information_regime.');
    }
    if (!parent.simulator_snapshot) throw new BeliefStateError('Parent simulator-only truth requires simulator snapshot lineage.');
    const transitionId = normalizedString(provenance.transition_id, 'Parent truth transition ID');
    const simulatorRevision = normalizedString(provenance.simulator_revision, 'Parent truth simulator revision');
    const linkedTransition = parent.transition_history.find((entry) => (
      entry.transition_id === transitionId && entry.simulator_revision === simulatorRevision
    ));
    const linkedSnapshot = parent.simulator_snapshot_history.find((entry) => entry.transition_id === transitionId);
    if (!linkedSnapshot || (parent.transition_history.some((entry) => entry.transition_id === transitionId) && !linkedTransition)) {
      throw new BeliefStateError('Parent simulator-only truth does not match transition lineage.');
    }
    normalizedProvenance = {
      kind: 'simulator_only_truth', transition_id: transitionId, simulator_revision: simulatorRevision,
    };
  } else {
    throw new BeliefStateError('Unsupported parent evidence provenance kind.');
  }
  const normalized: BeliefEvidenceInput = {
    perspective: entry.perspective,
    category: entry.category as BeliefCategory,
    subject_key: subjectKey,
    value,
    assertion: entry.assertion,
    provenance: normalizedProvenance,
  };
  const expectedId = evidenceId(normalized);
  if (entry.evidence_id !== expectedId) throw new BeliefStateError('Parent evidence identity is invalid.');
  return { ...normalized, evidence_id: expectedId };
}

function assertParent(parent: BeliefState): void {
  if (!isRecord(parent) || parent.schema_version !== BELIEF_STATE_SCHEMA_VERSION) {
    throw new BeliefStateError('Unsupported parent belief schema.');
  }
  exactKeys(parent, [
    'schema_version', 'belief_id', 'information_regime', 'battle_id', 'perspective', 'observation',
    'observation_history', 'source_protocol_prefix', 'parent_belief_id', 'simulator_snapshot',
    'simulator_snapshot_history', 'transition_lineage',
    'transition_history',
    'candidates', 'evidence', 'unresolved', 'contradictions',
  ], 'Parent belief');
  if (parent.information_regime !== 'player' && parent.information_regime !== 'simulator_research') {
    throw new BeliefStateError('Parent belief information_regime is invalid.');
  }
  assertNonEmptyString(parent.battle_id, 'Parent belief battle_id');
  if (!isPlayer(parent.perspective)) throw new BeliefStateError('Parent belief perspective is invalid.');
  if (!isRecord(parent.observation)) throw new BeliefStateError('Parent belief observation reference is malformed.');
  exactKeys(parent.observation, [
    'schema_version', 'observation_id', 'source_kind', 'event_cursor', 'protocol_prefix_hash', 'snapshot_phase',
  ], 'Parent observation reference');
  if (parent.observation.schema_version !== OBSERVABLE_STATE_SCHEMA_VERSION
    || typeof parent.observation.observation_id !== 'string' || !/^obs-[a-f0-9]{64}$/.test(parent.observation.observation_id)
    || !['sim_core', 'replay', 'live'].includes(parent.observation.source_kind)
    || !isSafeInteger(parent.observation.event_cursor) || parent.observation.event_cursor < 0
    || !['pre_decision', 'post_resolution', 'forced_switch', 'terminal', 'other'].includes(parent.observation.snapshot_phase)) {
    throw new BeliefStateError('Parent observation reference is invalid.');
  }
  assertDigest(parent.observation.protocol_prefix_hash, 'Parent observation protocol_prefix_hash');
  assertSanitizedProtocolPrefix(parent.source_protocol_prefix, 'Parent source protocol prefix');
  validateObservableProtocolPrefix(parent.source_protocol_prefix, parent.perspective);
  if (parent.observation.event_cursor !== parent.source_protocol_prefix.length
    || sha256(parent.source_protocol_prefix) !== parent.observation.protocol_prefix_hash) {
    throw new BeliefStateError('Parent belief observation prefix is invalid.');
  }
  if (!Array.isArray(parent.observation_history) || parent.observation_history.length === 0) {
    throw new BeliefStateError('Parent observation history is missing.');
  }
  let previousCursor = -1;
  const observationIds = new Set<string>();
  for (const reference of parent.observation_history) {
    if (!isRecord(reference)) throw new BeliefStateError('Parent observation history entry is malformed.');
    exactKeys(reference, [
      'schema_version', 'observation_id', 'source_kind', 'event_cursor', 'protocol_prefix_hash', 'snapshot_phase',
    ], 'Parent observation history entry');
    if (reference.schema_version !== OBSERVABLE_STATE_SCHEMA_VERSION
      || typeof reference.observation_id !== 'string' || !/^obs-[a-f0-9]{64}$/.test(reference.observation_id)
      || !['sim_core', 'replay', 'live'].includes(reference.source_kind)
      || !isSafeInteger(reference.event_cursor) || reference.event_cursor < previousCursor
      || reference.event_cursor > parent.source_protocol_prefix.length
      || !['pre_decision', 'post_resolution', 'forced_switch', 'terminal', 'other'].includes(reference.snapshot_phase)
      || observationIds.has(reference.observation_id)) {
      throw new BeliefStateError('Parent observation history entry is invalid.');
    }
    assertDigest(reference.protocol_prefix_hash, 'Parent historical protocol_prefix_hash');
    if (sha256(parent.source_protocol_prefix.slice(0, reference.event_cursor)) !== reference.protocol_prefix_hash) {
      throw new BeliefStateError('Parent historical observation prefix hash is invalid.');
    }
    observationIds.add(reference.observation_id);
    previousCursor = reference.event_cursor;
  }
  if (canonicalize(parent.observation_history[parent.observation_history.length - 1]) !== canonicalize(parent.observation)) {
    throw new BeliefStateError('Parent current observation is not the last observation-history entry.');
  }
  if (parent.parent_belief_id !== null
    && (typeof parent.parent_belief_id !== 'string' || !/^belief-[a-f0-9]{64}$/.test(parent.parent_belief_id))) {
    throw new BeliefStateError('Parent belief parent_belief_id is invalid.');
  }
  if (parent.simulator_snapshot !== null) {
    if (!isRecord(parent.simulator_snapshot)) throw new BeliefStateError('Parent simulator snapshot lineage is malformed.');
    exactKeys(parent.simulator_snapshot, ['branch_id', 'transition_id', 'state_fingerprint', 'parent_branch_id'], 'Parent simulator snapshot lineage');
    assertNonEmptyString(parent.simulator_snapshot.branch_id, 'Parent simulator branch_id');
    if (parent.simulator_snapshot.transition_id !== null) assertNonEmptyString(parent.simulator_snapshot.transition_id, 'Parent simulator transition_id');
    if (parent.simulator_snapshot.parent_branch_id !== null) assertNonEmptyString(parent.simulator_snapshot.parent_branch_id, 'Parent simulator parent_branch_id');
    assertDigest(parent.simulator_snapshot.state_fingerprint, 'Parent simulator state_fingerprint');
  }
  if (!Array.isArray(parent.simulator_snapshot_history)) throw new BeliefStateError('Parent simulator snapshot history is malformed.');
  for (const snapshot of parent.simulator_snapshot_history) {
    if (!isRecord(snapshot)) throw new BeliefStateError('Parent simulator snapshot history entry is malformed.');
    exactKeys(snapshot, ['branch_id', 'transition_id', 'state_fingerprint', 'parent_branch_id'], 'Parent simulator snapshot history entry');
    assertNonEmptyString(snapshot.branch_id, 'Parent snapshot history branch_id');
    if (snapshot.transition_id !== null) assertNonEmptyString(snapshot.transition_id, 'Parent snapshot history transition_id');
    if (snapshot.parent_branch_id !== null) assertNonEmptyString(snapshot.parent_branch_id, 'Parent snapshot history parent_branch_id');
    assertDigest(snapshot.state_fingerprint, 'Parent snapshot history state_fingerprint');
  }
  if ((parent.simulator_snapshot_history.length === 0) !== (parent.simulator_snapshot === null)
    || (parent.simulator_snapshot_history.length > 0
      && canonicalize(parent.simulator_snapshot_history[parent.simulator_snapshot_history.length - 1]) !== canonicalize(parent.simulator_snapshot))) {
    throw new BeliefStateError('Parent simulator snapshot is not the last snapshot-history entry.');
  }
  if (parent.transition_lineage !== null) {
    if (!isRecord(parent.transition_lineage)) throw new BeliefStateError('Parent transition lineage is malformed.');
    exactKeys(parent.transition_lineage, [
      'transition_id', 'parent_branch_id', 'branch_id', 'input_state_fingerprint', 'output_state_fingerprint',
      'simulator_revision', 'step_index', 'input_observation_id', 'output_observation_id',
    ], 'Parent transition lineage');
    for (const key of ['transition_id', 'parent_branch_id', 'branch_id', 'simulator_revision']) {
      assertNonEmptyString(parent.transition_lineage[key as keyof BeliefTransitionLineage], `Parent transition ${key}`);
    }
    assertDigest(parent.transition_lineage.input_state_fingerprint, 'Parent transition input fingerprint');
    assertDigest(parent.transition_lineage.output_state_fingerprint, 'Parent transition output fingerprint');
    if (!isSafeInteger(parent.transition_lineage.step_index) || parent.transition_lineage.step_index < 0
      || typeof parent.transition_lineage.input_observation_id !== 'string' || !observationIds.has(parent.transition_lineage.input_observation_id)
      || typeof parent.transition_lineage.output_observation_id !== 'string' || !observationIds.has(parent.transition_lineage.output_observation_id)
      || !parent.simulator_snapshot
      || parent.simulator_snapshot.transition_id !== parent.transition_lineage.transition_id
      || parent.simulator_snapshot.branch_id !== parent.transition_lineage.branch_id
      || parent.simulator_snapshot.parent_branch_id !== parent.transition_lineage.parent_branch_id
      || parent.simulator_snapshot.state_fingerprint !== parent.transition_lineage.output_state_fingerprint) {
      throw new BeliefStateError('Parent transition lineage does not match its observation and snapshot.');
    }
  }
  if (!Array.isArray(parent.transition_history)) throw new BeliefStateError('Parent transition history is malformed.');
  let previousTransition: BeliefTransitionLineage | null = null;
  const transitionIds = new Set<string>();
  for (const entry of parent.transition_history) {
    if (!isRecord(entry)) throw new BeliefStateError('Parent transition history entry is malformed.');
    exactKeys(entry, [
      'transition_id', 'parent_branch_id', 'branch_id', 'input_state_fingerprint', 'output_state_fingerprint',
      'simulator_revision', 'step_index', 'input_observation_id', 'output_observation_id',
    ], 'Parent transition history entry');
    for (const key of ['transition_id', 'parent_branch_id', 'branch_id', 'simulator_revision']) {
      assertNonEmptyString(entry[key], `Parent transition history ${key}`);
    }
    assertDigest(entry.input_state_fingerprint, 'Parent transition history input fingerprint');
    assertDigest(entry.output_state_fingerprint, 'Parent transition history output fingerprint');
    if (!isSafeInteger(entry.step_index) || entry.step_index < 0
      || typeof entry.input_observation_id !== 'string' || !observationIds.has(entry.input_observation_id)
      || typeof entry.output_observation_id !== 'string' || !observationIds.has(entry.output_observation_id)
      || transitionIds.has(entry.transition_id)) {
      throw new BeliefStateError('Parent transition history entry is invalid.');
    }
    if (previousTransition && (entry.parent_branch_id !== previousTransition.branch_id
      || entry.simulator_revision !== previousTransition.simulator_revision
      || entry.step_index <= previousTransition.step_index)) {
      throw new BeliefStateError('Parent transition history is stale or disconnected.');
    }
    transitionIds.add(entry.transition_id);
    previousTransition = entry as unknown as BeliefTransitionLineage;
  }
  if ((parent.transition_history.length === 0) !== (parent.transition_lineage === null)
    || (parent.transition_history.length > 0
      && canonicalize(parent.transition_history[parent.transition_history.length - 1]) !== canonicalize(parent.transition_lineage))) {
    throw new BeliefStateError('Parent current transition is not the last transition-history entry.');
  }
  if (parent.transition_history.length > 0
    && parent.simulator_snapshot_history.length !== parent.transition_history.length + 1) {
    throw new BeliefStateError('Parent simulator snapshot history does not cover its transition history.');
  }
  for (const [index, transition] of parent.transition_history.entries()) {
    const previousSnapshot = parent.simulator_snapshot_history[index];
    const outputSnapshot = parent.simulator_snapshot_history[index + 1];
    if (!previousSnapshot || !outputSnapshot
      || transition.parent_branch_id !== previousSnapshot.branch_id
      || transition.input_state_fingerprint !== previousSnapshot.state_fingerprint
      || transition.transition_id !== outputSnapshot.transition_id
      || transition.branch_id !== outputSnapshot.branch_id
      || transition.parent_branch_id !== outputSnapshot.parent_branch_id
      || transition.output_state_fingerprint !== outputSnapshot.state_fingerprint) {
      throw new BeliefStateError('Parent transition history does not match simulator snapshot history.');
    }
  }
  if (!Array.isArray(parent.candidates) || !Array.isArray(parent.evidence)
    || !Array.isArray(parent.unresolved) || !Array.isArray(parent.contradictions)) {
    throw new BeliefStateError('Parent belief collections are malformed.');
  }
  const evidence = parent.evidence.map((entry) => assertParentEvidence(entry, parent));
  const evidenceIds = new Set(evidence.map((entry) => entry.evidence_id));
  for (const entry of evidence) {
    if (entry.provenance.kind === 'derived'
      && entry.provenance.input_evidence_ids.some((id) => !evidenceIds.has(id))) {
      throw new BeliefStateError('Parent derived evidence references missing evidence IDs.');
    }
  }
  const normalizedCandidates = parent.candidates.map((candidate) => {
    if (!isRecord(candidate)) throw new BeliefStateError('Parent belief candidate is malformed.');
    exactKeys(candidate, ['category', 'subject_key', 'value', 'candidate_id', 'disposition', 'evidence_ids'], 'Parent belief candidate');
    const normalized = normalizeCandidate({ category: candidate.category as BeliefCategory, subject_key: candidate.subject_key as string, value: candidate.value as string });
    if (candidate.candidate_id !== candidateId(normalized)
      || !['possible', 'supported', 'ruled_out', 'contradictory'].includes(candidate.disposition as string)
      || !Array.isArray(candidate.evidence_ids) || candidate.evidence_ids.some((id) => typeof id !== 'string')) {
      throw new BeliefStateError('Parent belief candidate identity or disposition is invalid.');
    }
    return normalized;
  });
  const unresolved = parent.unresolved.map(normalizeUnknown);
  const expected = sortBeliefData(normalizedCandidates.map((candidate) => ({
    ...candidate,
    candidate_id: candidateId(candidate),
    disposition: 'possible',
    evidence_ids: [],
  })), evidence, unresolved);
  if (canonicalize(expected.candidates) !== canonicalize(parent.candidates)
    || canonicalize(expected.evidence) !== canonicalize(parent.evidence)
    || canonicalize(expected.unresolved) !== canonicalize(parent.unresolved)
    || canonicalize(expected.contradictions) !== canonicalize(parent.contradictions)) {
    throw new BeliefStateError('Parent belief derived fields are inconsistent with its evidence.');
  }
  const { belief_id, ...payload } = parent;
  if (typeof belief_id !== 'string' || `belief-${sha256(payload)}` !== belief_id) {
    throw new BeliefStateError('Parent belief identity is invalid or stale.');
  }
}

function assertExactPrefix(parentPrefix: readonly string[], childPrefix: readonly string[]): void {
  if (parentPrefix.length > childPrefix.length
    || parentPrefix.some((record, index) => childPrefix[index] !== record)) {
    throw new BeliefStateError('Child observation is not an exact prefix extension of parent belief.');
  }
}

function sameSnapshot(left: BeliefSimulatorSnapshotLineage, right: BeliefSimulatorSnapshotLineage): boolean {
  return left.branch_id === right.branch_id
    && left.transition_id === right.transition_id
    && left.state_fingerprint === right.state_fingerprint
    && left.parent_branch_id === right.parent_branch_id;
}

function sortBeliefData(
  candidates: BeliefCandidate[],
  evidence: BeliefEvidence[],
  unresolved: BeliefUnknown[],
): { candidates: BeliefCandidate[]; evidence: BeliefEvidence[]; unresolved: BeliefUnknown[]; contradictions: BeliefContradiction[] } {
  const orderedEvidence = [...evidence].sort((a, b) => compareText(a.evidence_id, b.evidence_id));
  const orderedCandidates = [...candidates].map((candidate) => {
    const matched = orderedEvidence.filter((entry) => (
      entry.category === candidate.category
      && entry.subject_key === candidate.subject_key
      && entry.value === candidate.value
    ));
    const supports = matched.some((entry) => entry.assertion === 'supports');
    const refutes = matched.some((entry) => entry.assertion === 'refutes');
    const disposition: BeliefDisposition = supports && refutes
      ? 'contradictory'
      : supports ? 'supported' : refutes ? 'ruled_out' : 'possible';
    return {
      ...candidate,
      disposition,
      evidence_ids: matched.map((entry) => entry.evidence_id).sort(),
    };
  }).sort((a, b) => compareText(a.category, b.category)
    || compareText(a.subject_key, b.subject_key)
    || compareText(a.value, b.value)
    || compareText(a.candidate_id, b.candidate_id));
  const unknownMap = new Map(unresolved.map((entry) => [canonicalize(entry), entry]));
  const orderedUnknowns = [...unknownMap.values()].sort((a, b) => compareText(a.category, b.category)
    || compareText(a.subject_key, b.subject_key)
    || compareText(a.reason, b.reason));
  const contradictions = orderedCandidates
    .filter((candidate) => candidate.disposition === 'contradictory')
    .map((candidate) => ({ candidate_id: candidate.candidate_id, evidence_ids: [...candidate.evidence_ids] }))
    .sort((a, b) => compareText(a.candidate_id, b.candidate_id));
  return {
    candidates: orderedCandidates,
    evidence: orderedEvidence,
    unresolved: orderedUnknowns,
    contradictions,
  };
}

export function projectBeliefState(input: BeliefStateInput): BeliefState {
  if (input.schema_version !== undefined && input.schema_version !== BELIEF_STATE_SCHEMA_VERSION) {
    throw new BeliefStateError('Unsupported belief schema.');
  }
  assertObservation(input.observation);
  const parent = input.parent ?? null;
  const informationRegime = input.information_regime ?? parent?.information_regime ?? 'player';
  if (informationRegime !== 'player' && informationRegime !== 'simulator_research') {
    throw new BeliefStateError('Unsupported belief information_regime.');
  }
  if (parent) {
    assertParent(parent);
    if (input.information_regime !== undefined && input.information_regime !== parent.information_regime) {
      throw new BeliefStateError('Child belief information_regime must match parent belief.');
    }
    if (parent.battle_id !== input.observation.battle_id || parent.perspective !== input.observation.perspective) {
      throw new BeliefStateError('Parent belief battle and perspective must match base observation.');
    }
    if (input.observation.event_cursor < parent.observation.event_cursor) {
      throw new BeliefStateError('Observation cursor is stale relative to parent belief.');
    }
    assertExactPrefix(parent.source_protocol_prefix, input.observation.protocol_prefix);
  }

  let transitionLineage: BeliefTransitionLineage | null = parent?.transition_lineage ?? null;
  let simulatorSnapshot: BeliefSimulatorSnapshotLineage | null = parent?.simulator_snapshot ?? null;
  if (input.transition) {
    const linked = normalizeTransition(input.transition, input.observation, parent);
    transitionLineage = linked.lineage;
    simulatorSnapshot = linked.snapshot;
  } else if (input.simulator_snapshot) {
    const suppliedSnapshot = normalizeSnapshot(input.simulator_snapshot, input.observation);
    if (parent?.simulator_snapshot && !sameSnapshot(parent.simulator_snapshot, suppliedSnapshot)) {
      throw new BeliefStateError('Simulator snapshot changed without a linked transition.');
    }
    simulatorSnapshot = suppliedSnapshot;
  }

  const rawCandidates = [
    ...(parent?.candidates.map(({ category, subject_key, value }) => ({ category, subject_key, value })) ?? []),
    ...(input.candidates ?? []),
  ].map(normalizeCandidate);
  const candidateMap = new Map<string, BeliefCandidateInput>();
  for (const candidate of rawCandidates) candidateMap.set(candidateKey(candidate), candidate);

  const normalizedNewEvidence = (input.evidence ?? []).map((entry) => normalizeEvidence(
    entry, input.observation, informationRegime, transitionLineage, simulatorSnapshot,
  ));
  const evidenceMap = new Map<string, BeliefEvidence>();
  for (const entry of [...(parent?.evidence ?? []), ...normalizedNewEvidence]) {
    const existing = evidenceMap.get(entry.evidence_id);
    if (existing && canonicalize(existing) !== canonicalize(entry)) {
      throw new BeliefStateError('Duplicate evidence ID has unequal content.');
    }
    evidenceMap.set(entry.evidence_id, entry);
  }
  const evidence = [...evidenceMap.values()];
  const evidenceIds = new Set(evidence.map((entry) => entry.evidence_id));
  for (const entry of normalizedNewEvidence) {
    if (entry.provenance.kind === 'derived'
      && entry.provenance.input_evidence_ids.some((id) => !evidenceIds.has(id))) {
      throw new BeliefStateError('Derived evidence references missing evidence IDs.');
    }
  }

  for (const entry of evidence) {
    candidateMap.set(candidateKey(entry), {
      category: entry.category,
      subject_key: entry.subject_key,
      value: entry.value,
    });
  }
  const candidates: BeliefCandidate[] = [...candidateMap.values()].map((candidate) => ({
    ...candidate,
    candidate_id: candidateId(candidate),
    disposition: 'possible',
    evidence_ids: [],
  }));
  const unresolved = [
    ...(parent?.unresolved ?? []),
    ...((input.unresolved ?? []).map(normalizeUnknown)),
  ];
  const sorted = sortBeliefData(candidates, evidence, unresolved);
  const payload: BeliefStatePayload = {
    schema_version: BELIEF_STATE_SCHEMA_VERSION,
    information_regime: informationRegime,
    battle_id: input.observation.battle_id,
    perspective: input.observation.perspective,
    observation: observationReference(input.observation),
    observation_history: [
      ...(parent?.observation_history ?? []),
    ].filter((reference, index, references) => references.findIndex((item) => item.observation_id === reference.observation_id) === index)
      .concat(parent?.observation.observation_id === input.observation.observation_id
        ? []
        : [observationReference(input.observation)]),
    source_protocol_prefix: [...input.observation.protocol_prefix],
    parent_belief_id: parent?.belief_id ?? null,
    simulator_snapshot: simulatorSnapshot ? { ...simulatorSnapshot } : null,
    simulator_snapshot_history: [
      ...(parent?.simulator_snapshot_history ?? []),
      ...(input.transition && simulatorSnapshot
        ? [{ ...simulatorSnapshot }]
        : !parent?.simulator_snapshot && simulatorSnapshot ? [{ ...simulatorSnapshot }] : []),
    ],
    transition_lineage: transitionLineage ? { ...transitionLineage } : null,
    transition_history: [
      ...(parent?.transition_history ?? []),
      ...(input.transition && transitionLineage && !parent?.transition_history.some((entry) => entry.transition_id === transitionLineage?.transition_id)
        ? [{ ...transitionLineage }]
        : []),
    ],
    candidates: sorted.candidates,
    evidence: sorted.evidence,
    unresolved: sorted.unresolved,
    contradictions: sorted.contradictions,
  };
  return deepFreeze({ ...payload, belief_id: `belief-${sha256(payload)}` });
}

export function serializeBeliefState(state: BeliefState): string {
  assertParent(state);
  const { belief_id: _beliefId, ...payload } = state;
  if (`belief-${sha256(payload)}` !== state.belief_id) throw new BeliefStateError('BeliefState identity is invalid.');
  return canonicalize(state);
}
