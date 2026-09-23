import { createHash } from 'node:crypto';
import type {
  BattleView,
  ChoiceRequestView,
  FieldView,
  LegalAction,
  LegalActionSet,
  PlayerID,
  PokemonView,
  RequestActiveView,
  RequestMoveView,
  RequestSidePokemonView,
  StepResult,
  Winner,
} from './types';

export const OBSERVABLE_STATE_SCHEMA_VERSION = 'observable-battle-state/v1' as const;

export type ObservableSourceKind = 'sim_core' | 'replay' | 'live';
export type ObservableSnapshotPhase =
  | 'pre_decision'
  | 'post_resolution'
  | 'forced_switch'
  | 'terminal'
  | 'other';

export class ObservableStateError extends Error {}
export class ObservableStateContradictionError extends ObservableStateError {}

export interface ObservablePokemonView {
  slot: number;
  ident: string;
  name: string;
  species: string;
  base_species: string | null;
  current_species: string | null;
  displayed_species: string | null;
  species_source: PokemonView['species_source'];
  transformed: boolean;
  displayed_species_uncertain: boolean;
  illusion_revealed: boolean;
  details: string;
  active: boolean;
  fainted: boolean;
  hp_text: string | null;
  hp_ratio: number | null;
  status: string | null;
  status_source: PokemonView['status_source'];
  status_started_turn: number | null;
  status_turns_public: number | null;
  gender: string | null;
  level: number | null;
  item?: string | null;
  last_item?: string | null;
  item_state?: PokemonView['item_state'];
  item_suppressed?: boolean;
  ability?: string | null;
  base_ability?: string | null;
  ability_state?: PokemonView['ability_state'];
  ability_suppressed?: boolean;
  moves?: string[];
  revealed_moves?: string[];
  types: string[];
  tera_type?: string | null;
  terastallized: boolean;
  stats?: Record<string, number>;
  boosts?: Record<string, number>;
  volatiles: string[];
}

export interface ObservableFieldView {
  weather: string | null;
  terrain: string | null;
  pseudo_weather: string[];
  side_conditions: {
    self: Record<string, number>;
    opponent: Record<string, number>;
  };
}

export interface ObservableBattleView {
  format: string;
  gen: number | null;
  turn: number;
  player: PlayerID;
  opponent: PlayerID;
  terminated: boolean;
  winner: Winner;
  names: Record<PlayerID, string | null>;
  team_size: Record<PlayerID, number>;
  active: { self: number | null; opponent: number | null };
  field: ObservableFieldView;
  self_team: ObservablePokemonView[];
  opponent_team: ObservablePokemonView[];
}

export interface ObservableRequestMoveView {
  slot: number;
  move: string;
  id: string;
  pp: number;
  maxpp: number;
  target: string;
  disabled: boolean;
  type: string | null;
  category: string | null;
  base_power: number;
  accuracy: number | null;
}

export interface ObservableRequestSidePokemonView {
  slot: number;
  ident: string;
  details: string;
  condition: string;
  active: boolean;
  moves: string[];
  stats: Record<string, number>;
  base_ability: string | null;
  ability: string | null;
  item: string | null;
  tera_type: string | null;
  terastallized: boolean;
}

export interface ObservableRequestActiveView {
  moves: ObservableRequestMoveView[];
  can_terastallize: boolean;
  tera_type: string | null;
  trapped: boolean;
  can_switch: boolean;
}

export interface ObservableChoiceRequestView {
  player: PlayerID;
  wait: boolean;
  team_preview: boolean;
  force_switch: boolean;
  trapped: boolean;
  rqid: number | null;
  active: ObservableRequestActiveView | null;
  side: ObservableRequestSidePokemonView[];
  legal_actions: LegalActionSet;
}

export interface ObservableDecisionAvailability {
  available: boolean;
  reason: 'request' | 'requestless' | 'waiting' | 'terminal' | 'no_legal_actions';
  legal_action_indices: number[] | null;
}

export interface ObservableBattleState {
  schema_version: typeof OBSERVABLE_STATE_SCHEMA_VERSION;
  source_kind: ObservableSourceKind;
  battle_id: string;
  perspective: PlayerID;
  event_cursor: number;
  observation_id: string;
  protocol_prefix_hash: string;
  snapshot_phase: ObservableSnapshotPhase;
  other_phase: string | null;
  request: ObservableChoiceRequestView | null;
  decision_availability: ObservableDecisionAvailability;
  protocol_prefix: string[];
  view: ObservableBattleView;
}

export interface ObservableStateInput {
  schema_version: string;
  source_kind: ObservableSourceKind;
  battle_id: string;
  perspective: PlayerID;
  snapshot_phase: string;
  protocol_prefix: readonly string[];
  view: BattleView;
  request: ChoiceRequestView | null;
  other_phase?: string | null;
  contradictions?: readonly string[];
}

export interface ObservableStepResultInput extends Omit<ObservableStateInput, 'view' | 'request'> {
  step_result: StepResult;
}

function cloneRecord(record: Record<string, number>): Record<string, number> {
  return { ...record };
}

function clonePokemon(pokemon: PokemonView, visibility: 'self' | 'opponent'): ObservablePokemonView {
  const publicFields: ObservablePokemonView = {
    slot: pokemon.slot,
    ident: pokemon.ident,
    name: pokemon.name,
    species: pokemon.species,
    base_species: pokemon.base_species,
    current_species: pokemon.current_species,
    displayed_species: pokemon.displayed_species,
    species_source: pokemon.species_source,
    transformed: pokemon.transformed,
    displayed_species_uncertain: pokemon.displayed_species_uncertain,
    illusion_revealed: pokemon.illusion_revealed,
    details: pokemon.details,
    active: pokemon.active,
    fainted: pokemon.fainted,
    hp_text: pokemon.hp_text,
    hp_ratio: pokemon.hp_ratio,
    status: pokemon.status,
    status_source: pokemon.status_source,
    status_started_turn: pokemon.status_started_turn,
    status_turns_public: pokemon.status_turns_public,
    gender: pokemon.gender,
    level: pokemon.level,
    types: [...pokemon.types],
    terastallized: pokemon.terastallized,
    volatiles: [...pokemon.volatiles],
  };
  if (visibility === 'self') {
    return {
      ...publicFields,
      item: pokemon.item,
      last_item: pokemon.last_item,
      item_state: pokemon.item_state,
      item_suppressed: pokemon.item_suppressed,
      ability: pokemon.ability,
      base_ability: pokemon.base_ability,
      ability_state: pokemon.ability_state,
      ability_suppressed: pokemon.ability_suppressed,
      moves: [...pokemon.moves],
      revealed_moves: [...pokemon.revealed_moves],
      tera_type: pokemon.tera_type,
      stats: cloneRecord(pokemon.stats),
      boosts: cloneRecord(pokemon.boosts),
    };
  }
  // Opponent-private fields are omitted, rather than copied as nulls. The only
  // item signal crossing this boundary is the already-public presence marker.
  if (pokemon.item === 'has-item') return { ...publicFields, item: 'has-item' };
  return publicFields;
}

function cloneField(field: FieldView): ObservableFieldView {
  return {
    weather: field.weather,
    terrain: field.terrain,
    pseudo_weather: [...field.pseudo_weather],
    side_conditions: {
      self: cloneRecord(field.side_conditions.self),
      opponent: cloneRecord(field.side_conditions.opponent),
    },
  };
}

function cloneView(view: BattleView): ObservableBattleView {
  return {
    format: view.format,
    gen: view.gen,
    turn: view.turn,
    player: view.player,
    opponent: view.opponent,
    terminated: view.terminated,
    winner: view.winner,
    names: { ...view.names },
    team_size: { ...view.team_size },
    active: { ...view.active },
    field: cloneField(view.field),
    self_team: view.self_team.map((pokemon) => clonePokemon(pokemon, 'self')),
    opponent_team: view.opponent_team.map((pokemon) => clonePokemon(pokemon, 'opponent')),
  };
}

function cloneMove(move: RequestMoveView): ObservableRequestMoveView {
  return { ...move };
}

function cloneRequestSidePokemon(pokemon: RequestSidePokemonView): ObservableRequestSidePokemonView {
  return {
    ...pokemon,
    moves: [...pokemon.moves],
    stats: { ...pokemon.stats },
  };
}

function cloneActive(active: RequestActiveView): ObservableRequestActiveView {
  return { ...active, moves: active.moves.map(cloneMove) };
}

function cloneLegalActions(legalActions: LegalActionSet): LegalActionSet {
  return {
    mask: [...legalActions.mask],
    actions: legalActions.actions.map((action: LegalAction | null) => action ? { ...action } : null),
    available_indices: [...legalActions.available_indices],
  };
}

function cloneRequest(request: ChoiceRequestView): ObservableChoiceRequestView {
  return {
    player: request.player,
    wait: request.wait,
    team_preview: request.team_preview,
    force_switch: request.force_switch,
    trapped: request.trapped,
    rqid: request.rqid,
    active: request.active ? cloneActive(request.active) : null,
    side: request.side.map(cloneRequestSidePokemon),
    legal_actions: cloneLegalActions(request.legal_actions),
  };
}

function canonicalize(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value as Record<string, unknown>).sort().map((key) => `${JSON.stringify(key)}:${canonicalize((value as Record<string, unknown>)[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function sha256(value: unknown): string {
  return createHash('sha256').update(canonicalize(value), 'utf8').digest('hex');
}

function normalizeProtocolPrefix(prefix: readonly string[]): string[] {
  if (!Array.isArray(prefix)) throw new ObservableStateError('protocol_prefix must be an array of raw records.');
  return prefix.map((record, index) => {
    if (typeof record !== 'string') {
      throw new ObservableStateError(`Protocol record ${index} is not a string.`);
    }
    const normalized = record.replace(/\r\n?/g, '\n').trim();
    if (!normalized) throw new ObservableStateError(`Protocol record ${index} is empty.`);
    return normalized;
  });
}

const SUPPORTED_PHASES = new Set(['pre_decision', 'post_resolution', 'forced_switch', 'terminal']);

function normalizePhase(input: ObservableStateInput): { snapshot_phase: ObservableSnapshotPhase; other_phase: string | null } {
  if (typeof input.snapshot_phase !== 'string') {
    throw new ObservableStateError(`Malformed snapshot phase: ${String(input.snapshot_phase)}`);
  }
  const token = input.snapshot_phase;
  if (!token || token.trim() !== token || !/^[A-Za-z][A-Za-z0-9_.-]*$/.test(token)) {
    throw new ObservableStateError(`Malformed snapshot phase: ${JSON.stringify(token)}`);
  }
  if (SUPPORTED_PHASES.has(token)) {
    if (input.other_phase !== undefined && input.other_phase !== null) {
      throw new ObservableStateContradictionError('other_phase is only valid for an unsupported phase token.');
    }
    return { snapshot_phase: token as ObservableSnapshotPhase, other_phase: null };
  }
  if (input.other_phase !== undefined && input.other_phase !== null && input.other_phase !== token) {
    throw new ObservableStateContradictionError('other_phase must retain the original unsupported phase token.');
  }
  return { snapshot_phase: 'other', other_phase: token };
}

function assertInput(input: ObservableStateInput): { snapshot_phase: ObservableSnapshotPhase; other_phase: string | null } {
  if (input.schema_version !== OBSERVABLE_STATE_SCHEMA_VERSION) {
    throw new ObservableStateError(`Unsupported observable state schema: ${input.schema_version}`);
  }
  if (input.perspective !== 'p1' && input.perspective !== 'p2') {
    throw new ObservableStateError(`Unsupported perspective: ${String(input.perspective)}`);
  }
  if (!input.battle_id.trim()) throw new ObservableStateError('battle_id must not be empty.');
  if (!['sim_core', 'replay', 'live'].includes(input.source_kind)) {
    throw new ObservableStateError(`Unsupported source_kind: ${String(input.source_kind)}`);
  }
  const phase = normalizePhase(input);
  if (input.view.player !== input.perspective) {
    throw new ObservableStateContradictionError('BattleView player does not match perspective.');
  }
  if (input.request && input.request.player !== input.perspective) {
    throw new ObservableStateContradictionError('ChoiceRequestView player does not match perspective.');
  }
  if (input.request && input.request.player !== input.view.player) {
    throw new ObservableStateContradictionError('ChoiceRequestView player does not match BattleView player.');
  }
  if (phase.snapshot_phase === 'terminal' && !input.view.terminated) {
    throw new ObservableStateContradictionError('terminal snapshot requires a terminated BattleView.');
  }
  if (phase.snapshot_phase === 'forced_switch' && !input.request?.force_switch) {
    throw new ObservableStateContradictionError('forced_switch snapshot requires a force-switch request.');
  }
  if (input.contradictions?.length) {
    throw new ObservableStateContradictionError(`Observable state contradiction: ${input.contradictions.join('; ')}`);
  }
  return phase;
}

function decisionAvailability(view: BattleView, request: ChoiceRequestView | null): ObservableDecisionAvailability {
  if (view.terminated) return { available: false, reason: 'terminal', legal_action_indices: null };
  if (!request) return { available: false, reason: 'requestless', legal_action_indices: null };
  if (request.wait) return { available: false, reason: 'waiting', legal_action_indices: null };
  const indices = [...request.legal_actions.available_indices];
  for (const index of indices) {
    if (!Number.isInteger(index) || index < 0 || index >= request.legal_actions.mask.length || !request.legal_actions.mask[index]) {
      throw new ObservableStateContradictionError('legal action index is inconsistent with the request mask.');
    }
  }
  if (!indices.length) return { available: false, reason: 'no_legal_actions', legal_action_indices: [] };
  return { available: true, reason: 'request', legal_action_indices: indices };
}

type RawEvidence = {
  gen?: number;
  turn?: number;
  names: Partial<Record<PlayerID, string>>;
  team_size: Partial<Record<PlayerID, number>>;
  winner?: Winner;
  winner_token?: string;
  request_rqid?: number;
};

// This is intentionally a protocol-record allowlist, not a permissive parser.
// Unknown records are rejected so an adapter caller cannot smuggle unvalidated
// evidence through the observable boundary.
const SUPPORTED_RAW_COMMANDS = new Set([
  'ability', '-ability', 'block', '-block', 'boost', '-boost', 'clearallboost', '-clearallboost',
  'clearnegativeboost', '-clearnegativeboost', 'clearpositiveboost', '-clearpositiveboost',
  'curestatus', '-curestatus', 'damage', '-damage', 'drag', 'end', '-end', 'endability',
  '-endability', 'enditem', '-enditem', 'faint', 'fieldend', '-fieldend', 'fieldstart',
  '-fieldstart', 'formechange', '-formechange', 'gen', 'heal', '-heal', 'hitcount',
  'immune', '-immune', 'item', '-item', 'miss', '-miss', 'move', 'nothing', '-nothing',
  'player', 'poke', 'replace', 'request', 'resisted', '-resisted', 'rule', 'sidestart',
  '-sidestart', 'sideend', '-sideend', 'start', '-start', 'status', '-status', 'switch',
  'teamsize', 'terastallize', '-terastallize', 'turn', 'unboost', '-unboost', 'upkeep',
  'weather', '-weather', 'win', 'tie', 'transform', '-transform', 'setboost', '-setboost',
  'sethp', '-sethp', 'swapsideconditions', '-swapsideconditions', 'crit', '-crit',
  'supereffective', '-supereffective', 'fail', '-fail', 'activate', '-activate', 'prepare',
  '-prepare', 'mustrecharge', '-mustrecharge', 'clearboost', '-clearboost', 'clearstatus',
  '-clearstatus', 'c', 'chat', 'error', 'gametype', 'rated',
  'teampreview', 'clearpoke', 'done', 'inactive', 'inactiveoff', 't:',
]);

function parseIntegerRecord(parts: string[], label: string): number {
  if (parts.length !== 3 || !/^\d+$/.test(parts[2])) {
    throw new ObservableStateError(`Malformed raw ${label} record.`);
  }
  return Number(parts[2]);
}

function parseRawEvidence(prefix: readonly string[]): RawEvidence {
  const evidence: RawEvidence = { names: {}, team_size: {} };
  for (const record of prefix) {
    if (!record.startsWith('|')) throw new ObservableStateError('Malformed raw protocol record.');
    const parts = record.split('|');
    const command = parts[1];
    if (!command || !SUPPORTED_RAW_COMMANDS.has(command)) {
      throw new ObservableStateError(`Unsupported raw protocol event: ${command || '<empty>'}.`);
    }
    if (command === 'gen') {
      const value = parseIntegerRecord(parts, 'gen');
      if (evidence.gen !== undefined && evidence.gen !== value) throw new ObservableStateContradictionError('Raw gen records disagree.');
      evidence.gen = value;
    } else if (command === 'turn') {
      const value = parseIntegerRecord(parts, 'turn');
      if (evidence.turn !== undefined && evidence.turn !== value) throw new ObservableStateContradictionError('Raw turn records disagree.');
      evidence.turn = value;
    }
    else if (command === 'player') {
      if (parts.length < 4 || (parts[2] !== 'p1' && parts[2] !== 'p2') || !parts[3]) {
        throw new ObservableStateError('Malformed raw player record.');
      }
      const player = parts[2] as PlayerID;
      if (evidence.names[player] !== undefined && evidence.names[player] !== parts[3]) {
        throw new ObservableStateContradictionError(`Raw player records disagree for ${player}.`);
      }
      evidence.names[player] = parts[3];
    } else if (command === 'teamsize') {
      if (parts.length !== 4 || (parts[2] !== 'p1' && parts[2] !== 'p2') || !/^\d+$/.test(parts[3])) {
        throw new ObservableStateError('Malformed raw teamsize record.');
      }
      const player = parts[2] as PlayerID;
      const value = Number(parts[3]);
      if (evidence.team_size[player] !== undefined && evidence.team_size[player] !== value) {
        throw new ObservableStateContradictionError(`Raw teamsize records disagree for ${player}.`);
      }
      evidence.team_size[player] = value;
    } else if (command === 'win') {
      if (parts.length !== 3 || !parts[2]) throw new ObservableStateError('Malformed raw win record.');
      if (evidence.winner === 'tie' && parts[2] !== 'tie') {
        throw new ObservableStateContradictionError('Raw terminal records disagree.');
      }
      if (evidence.winner_token !== undefined && evidence.winner_token !== parts[2]) {
        throw new ObservableStateContradictionError('Raw win records disagree.');
      }
      evidence.winner_token = parts[2];
    } else if (command === 'tie') {
      if (parts.length !== 2) throw new ObservableStateError('Malformed raw tie record.');
      if (evidence.winner !== undefined && evidence.winner !== 'tie') {
        throw new ObservableStateContradictionError('Raw terminal records disagree.');
      }
      evidence.winner = 'tie';
    } else if (command === 'request') {
      const payload = parts.slice(2).join('|');
      if (!payload) throw new ObservableStateError('Malformed raw request record.');
      let parsed: unknown;
      try {
        parsed = JSON.parse(payload);
      } catch {
        throw new ObservableStateError('Malformed raw request record.');
      }
      if (!parsed || typeof parsed !== 'object') throw new ObservableStateError('Malformed raw request record.');
      const rqid = (parsed as { rqid?: unknown }).rqid;
      if (rqid !== undefined) {
        if (typeof rqid !== 'number' || !Number.isInteger(rqid)) {
          throw new ObservableStateError('Malformed raw request rqid.');
        }
        evidence.request_rqid = rqid;
      }
    }
  }
  if (evidence.winner_token === 'p1' || evidence.winner_token === 'p2' || evidence.winner_token === 'tie') {
    evidence.winner = evidence.winner_token;
  } else if (evidence.winner_token && evidence.names.p1 === evidence.winner_token) {
    evidence.winner = 'p1';
  } else if (evidence.winner_token && evidence.names.p2 === evidence.winner_token) {
    evidence.winner = 'p2';
  }
  return evidence;
}

function validateRawEvidence(prefix: readonly string[], view: BattleView, request: ChoiceRequestView | null): void {
  const evidence = parseRawEvidence(prefix);
  if (evidence.gen !== undefined && view.gen !== evidence.gen) {
    throw new ObservableStateContradictionError('Raw evidence disagrees with view.gen.');
  }
  if (evidence.turn !== undefined && view.turn !== evidence.turn) {
    throw new ObservableStateContradictionError('Raw evidence disagrees with view.turn.');
  }
  for (const player of ['p1', 'p2'] as const) {
    if (evidence.names[player] !== undefined && view.names[player] !== evidence.names[player]) {
      throw new ObservableStateContradictionError(`Raw evidence disagrees with view.names.${player}.`);
    }
    if (evidence.team_size[player] !== undefined && view.team_size[player] !== evidence.team_size[player]) {
      throw new ObservableStateContradictionError(`Raw evidence disagrees with view.team_size.${player}.`);
    }
  }
  if (evidence.winner !== undefined && view.winner !== evidence.winner) {
    throw new ObservableStateContradictionError('Raw evidence disagrees with view.winner.');
  }
  if (evidence.request_rqid !== undefined && request && request.rqid !== evidence.request_rqid) {
    throw new ObservableStateContradictionError('Raw evidence disagrees with request.rqid.');
  }
}

function deepFreeze<T>(value: T): T {
  if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
  Object.freeze(value);
  for (const child of Object.values(value as Record<string, unknown>)) deepFreeze(child);
  return value;
}

export function projectObservableBattleState(input: ObservableStateInput): ObservableBattleState {
  const phase = assertInput(input);
  const protocolPrefix = normalizeProtocolPrefix(input.protocol_prefix);
  validateRawEvidence(protocolPrefix, input.view, input.request);
  const view = cloneView(input.view);
  const request = input.request ? cloneRequest(input.request) : null;
  const decision_availability = decisionAvailability(input.view, input.request);
  const protocol_prefix_hash = sha256(protocolPrefix);
  const identity = {
    schema_version: OBSERVABLE_STATE_SCHEMA_VERSION,
    source_kind: input.source_kind,
    battle_id: input.battle_id,
    perspective: input.perspective,
    event_cursor: protocolPrefix.length,
    protocol_prefix_hash,
    snapshot_phase: phase.snapshot_phase,
    other_phase: phase.other_phase,
    request,
    decision_availability,
    view,
  };
  return deepFreeze({
    ...identity,
    observation_id: `obs-${sha256(identity)}`,
    protocol_prefix: protocolPrefix,
  });
}

export function projectStepResult(input: ObservableStepResultInput): ObservableBattleState {
  const view = input.step_result.views[input.perspective];
  if (!view) throw new ObservableStateError(`StepResult has no view for ${input.perspective}.`);
  const request = input.step_result.requests[input.perspective] ?? null;
  if (
    view.terminated !== input.step_result.terminated
    || view.winner !== input.step_result.winner
    || view.turn !== input.step_result.info.turn
    || view.format !== input.step_result.info.format
  ) {
    throw new ObservableStateContradictionError('StepResult metadata disagrees with BattleView.');
  }
  return projectObservableBattleState({
    ...input,
    view,
    request,
  });
}

export class ObservableStateProjector {
  private readonly lastByObservationKey = new Map<string, { cursor: number; hash: string; prefix: string[] }>();

  project(input: ObservableStateInput): ObservableBattleState {
    const state = projectObservableBattleState(input);
    const key = `${state.battle_id}:${state.perspective}`;
    const previous = this.lastByObservationKey.get(key);
    if (previous && state.event_cursor < previous.cursor) {
      throw new ObservableStateError(`event cursor moved backwards for ${key}.`);
    }
    if (previous) {
      const exactPrefix = previous.prefix.every((record, index) => state.protocol_prefix[index] === record);
      if (!exactPrefix) {
        throw new ObservableStateError(`protocol prefix is not an exact extension for ${key}.`);
      }
      if (state.event_cursor === previous.cursor && state.protocol_prefix_hash !== previous.hash) {
        throw new ObservableStateError(`protocol prefix changed at the same event cursor for ${key}.`);
      }
    }
    this.lastByObservationKey.set(key, {
      cursor: state.event_cursor,
      hash: state.protocol_prefix_hash,
      prefix: [...state.protocol_prefix],
    });
    return state;
  }
}
