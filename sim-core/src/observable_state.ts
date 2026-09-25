import { opponentPublicBoosts, type PublicBoosts } from './public_boosts';
import { createHash } from 'node:crypto';
import { RECOGNIZED_UNSUPPORTED_RAW_COMMANDS, SUPPORTED_RAW_COMMANDS } from './protocol_contract';
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
export const PUBLIC_STAGES_SCHEMA_VERSION = 'observable-battle-state/v2' as const;
export type ObservableSchemaVersion = typeof OBSERVABLE_STATE_SCHEMA_VERSION | typeof PUBLIC_STAGES_SCHEMA_VERSION;
export function isObservableSchema(value: unknown): value is ObservableSchemaVersion {
  return value === OBSERVABLE_STATE_SCHEMA_VERSION || value === PUBLIC_STAGES_SCHEMA_VERSION;
}

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
  public_boosts?: PublicBoosts;
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
  reviving?: true;
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
  schema_version: ObservableSchemaVersion;
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
  // Unselected opponent fields are omitted. V2 stages are reconstructed separately
  // from public evidence; the only item signal here is its public presence marker.
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
    if (normalized.includes('\n')) {
      throw new ObservableStateError(`Protocol record ${index} contains an embedded protocol record separator.`);
    }
    return normalized;
  });
}

function requireRawField(parts: string[], index: number, command: string, label = 'field'): void {
  if (typeof parts[index] !== 'string' || !parts[index].trim()) {
    throw new ObservableStateError(`Malformed raw ${command} record: ${label} is required.`);
  }
}

function requireRawPlayerIdent(parts: string[], index: number, command: string): void {
  requireRawField(parts, index, command, 'pokemon identifier');
  if (!/^p[12][a-z]:\s*[^|]+$/.test(parts[index].trim())) {
    throw new ObservableStateError(`Malformed raw ${command} record: invalid pokemon identifier.`);
  }
}

function requireRawTarget(parts: string[], index: number, command: string): void {
  requireRawField(parts, index, command, 'target');
  if (parts[index] !== '-' && !/^p[12][a-z]:\s*[^|]+$/.test(parts[index].trim())) {
    throw new ObservableStateError(`Malformed raw ${command} record: invalid target.`);
  }
}

function requireRawMoveTarget(parts: string[], index: number): void {
  requireRawField(parts, index, 'move', 'target');
  // Pokemon.toString() emits an active-position ident for active Pokemon and
  // a side ident for non-active Pokemon, including side-target move records.
  if (!/^p[12](?:[a-f])?:\s*[^|]+$/.test(parts[index].trim())) {
    throw new ObservableStateError('Malformed raw move record: invalid target.');
  }
}

function requireRawMoveNullTarget(parts: string[], index: number): void {
  // BattleActions.useMoveInner interpolates a null target into the move line,
  // includes optional source tags, then adds [notarget] before returning.
  const tags = parts.slice(index + 1);
  const sourceTags = tags.slice(0, -1);
  const isFromTag = (tag: string) => /^\[from\]\s+.+$/.test(tag);
  const isAnimTag = (tag: string) => /^\[anim\].+$/.test(tag);
  const validSourceTagOrder = sourceTags.length <= 1
    ? sourceTags.every((tag) => isFromTag(tag) || isAnimTag(tag))
    : sourceTags.length === 2 && isAnimTag(sourceTags[0]) && isFromTag(sourceTags[1]);
  if (
    parts[index] !== 'null'
    || tags.at(-1) !== '[notarget]'
    || tags.filter((tag) => tag === '[notarget]').length !== 1
    || !validSourceTagOrder
  ) {
    throw new ObservableStateError('Malformed raw move record: invalid target.');
  }
}

function isSupportedRawMoveTag(tag: string): boolean {
  return tag === '[still]' || tag === '[miss]' || tag === '[notarget]' || tag === '[zeffect]'
    || /^\[from\]\s+.+$/.test(tag)
    || /^\[anim\].+$/.test(tag)
    || /^\[spread\]\s+p[12][a-f](?:,p[12][a-f])+$/.test(tag);
}

function requireRawMoveTags(parts: string[]): void {
  const tags = parts.slice(5);
  if (tags.filter((tag) => tag === '[notarget]').length > 1
    || (tags.includes('[notarget]') && tags.at(-1) !== '[notarget]')) {
    throw new ObservableStateError('Malformed raw move record: invalid tag.');
  }
  for (const tag of tags) {
    if (!isSupportedRawMoveTag(tag)) {
      throw new ObservableStateError('Malformed raw move record: invalid tag.');
    }
  }
}

function requireRawPlayer(parts: string[], index: number, command: string): void {
  requireRawField(parts, index, command, 'player');
  if (parts[index] !== 'p1' && parts[index] !== 'p2') {
    throw new ObservableStateError(`Malformed raw ${command} record: invalid player.`);
  }
}

function requireRawInteger(parts: string[], index: number, command: string, label: string, signed = false): void {
  requireRawField(parts, index, command, label);
  if (!(signed ? /^-?\d+$/ : /^\d+$/).test(parts[index]) || !Number.isSafeInteger(Number(parts[index]))) {
    throw new ObservableStateError(`Malformed raw ${command} record: ${label} must be a safe integer.`);
  }
}

function parseRawRequestPayload(parts: string[]): Record<string, unknown> {
  const payload = parts.slice(2).join('|');
  if (!payload) throw new ObservableStateError('Malformed raw request record.');
  let parsed: unknown;
  try {
    parsed = JSON.parse(payload);
  } catch {
    throw new ObservableStateError('Malformed raw request record.');
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new ObservableStateError('Malformed raw request record.');
  }
  const request = parsed as Record<string, unknown>;
  if (request.rqid !== undefined && (!Number.isSafeInteger(request.rqid) || typeof request.rqid !== 'number')) {
    throw new ObservableStateError('Malformed raw request rqid.');
  }
  return request;
}

function validateRawRecordShape(parts: string[], command: string): void {
  const requireAtLeast = (length: number): void => {
    if (parts.length < length) throw new ObservableStateError(`Malformed raw ${command} record.`);
  };
  const requireIdent = (index = 2): void => requireRawPlayerIdent(parts, index, command);
  const noPayload = new Set([
    'clearallboost', '-clearallboost', 'swapsideconditions', '-swapsideconditions',
    'teampreview', 'clearpoke', 'done', 'upkeep', 'start', 'end', '-nothing',
  ]);

  if (noPayload.has(command)) {
    if (!(parts.length === 2 || (parts.length === 3 && parts[2] === ''))) {
      throw new ObservableStateError(`Malformed raw ${command} record.`);
    }
    return;
  }

  switch (command) {
    case 'tie':
      if (!(parts.length === 2 || (parts.length === 3 && parts[2] === ''))) {
        throw new ObservableStateError(`Malformed raw ${command} record.`);
      }
      return;
    case 'gen':
    case 'turn':
      parseIntegerRecord(parts, command);
      return;
    case 'player':
      if (parts.length < 4) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireRawPlayer(parts, 2, command);
      requireRawField(parts, 3, command, 'name');
      return;
    case 'teamsize':
      if (parts.length !== 4) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireRawPlayer(parts, 2, command);
      requireRawInteger(parts, 3, command, 'team size');
      return;
    case 'request':
      requireAtLeast(3);
      parseRawRequestPayload(parts);
      return;
    case 'move':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'move');
      // Showdown may omit the target or clear it for [still]. Tags are separate
      // fields: [notarget] is metadata and is never a target identifier.
      if (parts.length > 4 && parts[4] !== '') {
        if (parts[4] === 'null') requireRawMoveNullTarget(parts, 4);
        else requireRawMoveTarget(parts, 4);
      }
      requireRawMoveTags(parts);
      return;
    case '-singleturn':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'effect');
      return;
    case 'cant':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'reason');
      if (parts.length > 4) requireRawField(parts, 4, command, 'move');
      return;
    case '-hitcount':
      requireAtLeast(4);
      requireIdent();
      requireRawInteger(parts, 3, command, 'hit count');
      return;
    case 'faint':
      if (parts.length !== 3) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireIdent();
      return;
    case 'switch':
    case 'drag':
    case 'detailschange':
      requireAtLeast(5);
      requireIdent();
      requireRawField(parts, 3, command, 'details');
      requireRawField(parts, 4, command, 'condition');
      return;
    case 'replace':
      // Illusion.onEnd emits ident + details only. Legacy HP-bearing records
      // remain valid, but arbitrary trailing fields/conditions are not accepted.
      if (parts.length !== 4 && parts.length !== 5) throw new ObservableStateError('Malformed raw replace record.');
      requireIdent();
      requireRawField(parts, 3, command, 'details');
      if (parts.length === 5 && !/^(?:0 fnt|\d+(?:\/[1-9]\d*)?(?: (?:brn|par|slp|psn|tox|frz))?)$/.test(parts[4])) {
        throw new ObservableStateError('Malformed raw replace condition.');
      }
      return;
    case '-invertboost':
      if (parts.length !== 4 || parts[3] !== '[from] move: Topsy-Turvy') {
        throw new ObservableStateError(`Unsupported raw ${command} record.`);
      }
      requireIdent();
      return;
    case '-copyboost':
      if (parts.length !== 5 || parts[4] !== '[from] move: Psych Up') {
        throw new ObservableStateError(`Unsupported raw ${command} record.`);
      }
      requireIdent();
      requireRawPlayerIdent(parts, 3, command);
      return;
    case '-anim':
      // Spectral Thief announces animation after its separate stage events.
      if (parts.length !== 5 || parts[3] !== 'Spectral Thief') {
        throw new ObservableStateError(`Unsupported raw ${command} record.`);
      }
      requireIdent();
      requireRawPlayerIdent(parts, 4, command);
      return;
    case '-hint':
      // Public Illusion Level Mod explanation emitted by Battle.hint. No typed
      // state is inferred from prose; retain the original record in the prefix.
      requireAtLeast(3);
      requireRawField(parts, 2, command, 'message');
      return;
    case 'poke':
      requireAtLeast(4);
      requireRawPlayer(parts, 2, command);
      requireRawField(parts, 3, command, 'details');
      return;
    case 'formechange':
    case '-formechange':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'species');
      return;
    case 'transform':
    case '-transform':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'target');
      return;
    case 'damage':
    case '-damage':
    case 'heal':
    case '-heal':
    case 'sethp':
    case '-sethp':
      requireAtLeast(4);
      // Revival publicly heals a benched Pokémon using p1:/p2:, not an active position.
      if (!(command === '-heal' && parts.length === 5
        && parts[4] === '[from] move: Revival Blessing'
        && /^p[12]:\s*[^|]+$/.test(parts[2]))) requireIdent();
      requireRawField(parts, 3, command, 'condition');
      return;
    case 'status':
    case '-status':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'status');
      return;
    case 'curestatus':
    case '-curestatus':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'status');
      return;
    case 'boost':
    case '-boost':
    case 'unboost':
    case '-unboost':
    case 'setboost':
    case '-setboost':
      requireAtLeast(5);
      requireIdent();
      requireRawField(parts, 3, command, 'stat');
      requireRawInteger(parts, 4, command, 'amount', command === 'setboost' || command === '-setboost');
      return;
    case 'clearboost':
    case '-clearboost':
      if (parts.length !== 3) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireIdent();
      return;
    case 'clearnegativeboost':
    case '-clearnegativeboost':
      if (parts.length < 3 || parts.length > 4 || (parts.length === 4 && !['[silent]', '[zeffect]'].includes(parts[3]))) {
        throw new ObservableStateError(`Malformed raw ${command} record.`);
      }
      requireIdent();
      return;
    case 'clearpositiveboost':
    case '-clearpositiveboost':
      requireAtLeast(5);
      requireIdent();
      requireRawPlayerIdent(parts, 3, command);
      requireRawField(parts, 4, command, 'effect');
      return;
    case 'start':
    case '-start':
    case 'end':
    case '-end':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'effect');
      return;
    case 'weather':
    case '-weather':
    case 'fieldstart':
    case '-fieldstart':
    case 'fieldend':
    case '-fieldend':
    case '-fieldactivate':
      requireAtLeast(3);
      requireRawField(parts, 2, command, 'effect');
      return;
    case 'message':
    case '-message':
      requireAtLeast(3);
      requireRawField(parts, 2, command, 'message');
      return;
    case 'activate':
    case '-activate':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'effect');
      return;
    case 'sidestart':
    case '-sidestart':
    case 'sideend':
    case '-sideend':
      requireAtLeast(4);
      if (!/^p[12](?::|$)/.test(parts[2])) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireRawField(parts, 3, command, 'condition');
      return;
    case 'item':
    case '-item':
    case 'enditem':
    case '-enditem':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'item');
      return;
    case 'ability':
    case '-ability':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'ability');
      return;
    case 'endability':
    case '-endability':
      if (parts.length !== 3) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireIdent();
      return;
    case 'terastallize':
    case '-terastallize':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'type');
      return;
    case 'win':
      if (parts.length !== 3) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireRawField(parts, 2, command, 'winner');
      return;
    case 'block':
    case '-block':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'effect');
      return;
    case 'miss':
    case '-miss':
      requireAtLeast(4);
      requireIdent(2);
      requireIdent(3);
      return;
    case 'hitcount':
    case '-hitcount':
      requireAtLeast(4);
      requireIdent();
      requireRawInteger(parts, 3, command, 'count');
      return;
    case 'crit':
    case '-crit':
    case 'supereffective':
    case '-supereffective':
    case 'resisted':
    case '-resisted':
    case 'immune':
    case '-immune':
    case 'mustrecharge':
    case '-mustrecharge':
      if (parts.length < 3) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireIdent();
      return;
    case 'fail':
    case '-fail':
      requireAtLeast(3);
      requireIdent();
      if (parts.length > 3) requireRawField(parts, 3, command, 'action');
      return;
    case 'prepare':
    case '-prepare':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'move');
      if (parts.length > 4) requireRawTarget(parts, 4, command);
      return;
    case 'inactive':
      requireAtLeast(3);
      requireRawField(parts, 2, command, 'message');
      return;
    case 'inactiveoff':
      requireAtLeast(3);
      requireRawField(parts, 2, command, 'message');
      return;
    case 'rated':
      if (parts.length > 3 || (parts.length === 3 && !parts[2].trim())) {
        throw new ObservableStateError(`Malformed raw ${command} record.`);
      }
      return;
    case 't:':
      if (parts.length !== 3) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireRawInteger(parts, 2, command, 'timestamp');
      return;
    case 'c':
    case 'chat':
      requireAtLeast(4);
      requireRawField(parts, 2, command, 'user');
      requireRawField(parts, 3, command, 'message');
      return;
    case 'error':
    case 'gametype':
    case 'rule':
      requireAtLeast(3);
      requireRawField(parts, 2, command, 'payload');
      return;
    default:
      if (parts.length < 3 || parts.slice(2).some((field) => !field.trim())) {
        throw new ObservableStateError(`Malformed raw ${command} record.`);
      }
  }
}

function sanitizeProtocolPrefix(prefix: readonly string[]): string[] {
  return prefix.map((record) => {
    const parts = record.split('|');
    if (parts[1] !== 'request') return record;
    const request = parseRawRequestPayload(parts);
    const sanitized = request.rqid === undefined ? {} : { rqid: request.rqid };
    return `|request|${canonicalize(sanitized)}`;
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
  if (!isObservableSchema(input.schema_version)) {
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
  const expectedOpponent = input.perspective === 'p1' ? 'p2' : 'p1';
  if (input.view.opponent !== expectedOpponent) {
    throw new ObservableStateContradictionError('BattleView opponent must be the complement of perspective.');
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
  terminal_kind?: 'win' | 'tie';
  winner_token?: string;
  request_rqid?: number;
};

/** Validate one supported record before any event-specific state routing. */
export function validateRawProtocolRecord(record: string): void {
  if (!record.startsWith('|')) throw new ObservableStateError('Malformed raw protocol record.');
  const parts = record.split('|');
  const command = parts[1];
  if (!command || (!SUPPORTED_RAW_COMMANDS.has(command) && !RECOGNIZED_UNSUPPORTED_RAW_COMMANDS.has(command))) {
    throw new ObservableStateError(`Unsupported raw protocol event: ${command || '<empty>'}.`);
  }
  if (RECOGNIZED_UNSUPPORTED_RAW_COMMANDS.has(command)) {
    throw new ObservableStateError(`Unsupported raw protocol event: ${command}.`);
  }
  validateRawRecordShape(parts, command);
}

function parseIntegerRecord(parts: string[], label: string): number {
  if (parts.length !== 3 || !/^\d+$/.test(parts[2]) || !Number.isSafeInteger(Number(parts[2]))) {
    throw new ObservableStateError(`Malformed raw ${label} record.`);
  }
  return Number(parts[2]);
}

function parseRawEvidence(prefix: readonly string[], perspective: PlayerID): RawEvidence {
  const evidence: RawEvidence = { names: {}, team_size: {} };
  for (const record of prefix) {
    validateRawProtocolRecord(record);
    const parts = record.split('|');
    const command = parts[1];
    if (command === 'gen') {
      const value = parseIntegerRecord(parts, 'gen');
      if (evidence.gen !== undefined && evidence.gen !== value) throw new ObservableStateContradictionError('Raw gen records disagree.');
      evidence.gen = value;
    } else if (command === 'turn') {
      const value = parseIntegerRecord(parts, 'turn');
      // Turn records are ordered state observations. A later turn supersedes
      // an earlier one; the full prefix remains available for cursor/hash
      // integrity and is never deduplicated.
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
      if (evidence.terminal_kind === 'tie') {
        throw new ObservableStateContradictionError('Raw terminal records disagree.');
      }
      if (evidence.winner_token !== undefined && evidence.winner_token !== parts[2]) {
        throw new ObservableStateContradictionError('Raw terminal records disagree.');
      }
      evidence.terminal_kind = 'win';
      evidence.winner_token = parts[2];
    } else if (command === 'tie') {
      if (evidence.terminal_kind === 'win') {
        throw new ObservableStateContradictionError('Raw terminal records disagree.');
      }
      if (evidence.winner_token !== undefined && evidence.winner_token !== 'tie') {
        throw new ObservableStateContradictionError('Raw terminal records disagree.');
      }
      evidence.terminal_kind = 'tie';
      evidence.winner_token = 'tie';
    } else if (command === 'request') {
      const rawRequest = parseRawRequestPayload(parts);
      const side = rawRequest.side;
      if (side !== undefined && (!side || typeof side !== 'object' || Array.isArray(side))) {
        throw new ObservableStateError('Malformed raw request side.');
      }
      const sideId = side && typeof side === 'object' ? (side as { id?: unknown }).id : undefined;
      if (sideId !== undefined && sideId !== perspective) {
        throw new ObservableStateContradictionError('Raw request player disagrees with perspective.');
      }
      if (rawRequest.player !== undefined && rawRequest.player !== perspective) {
        throw new ObservableStateContradictionError('Raw request player disagrees with perspective.');
      }
      const rqid = rawRequest.rqid;
      if (rqid !== undefined) {
        evidence.request_rqid = rqid as number;
      }
    }
  }
  if (evidence.terminal_kind === 'tie') {
    evidence.winner = 'tie';
  } else if (evidence.winner_token === 'p1' || evidence.winner_token === 'p2') {
    evidence.winner = evidence.winner_token;
  } else if (evidence.winner_token && evidence.names.p1 === evidence.winner_token) {
    evidence.winner = 'p1';
  } else if (evidence.winner_token && evidence.names.p2 === evidence.winner_token) {
    evidence.winner = 'p2';
  }
  return evidence;
}

function validateRawEvidence(
  prefix: readonly string[],
  view: BattleView,
  request: ChoiceRequestView | null,
  perspective: PlayerID,
): void {
  const evidence = parseRawEvidence(prefix, perspective);
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
  if (evidence.terminal_kind !== undefined && !view.terminated) {
    throw new ObservableStateContradictionError('Raw terminal evidence requires a terminated BattleView.');
  }
  if (evidence.request_rqid !== undefined && request && request.rqid !== evidence.request_rqid) {
    throw new ObservableStateContradictionError('Raw evidence disagrees with request.rqid.');
  }
}

/** Revalidates serialized observable prefixes at consumer boundaries. */
export function validateObservableProtocolPrefix(
  prefix: readonly string[],
  perspective: PlayerID,
  view?: Pick<ObservableBattleView, 'gen' | 'turn' | 'names' | 'team_size' | 'winner' | 'terminated'>,
  request?: Pick<ObservableChoiceRequestView, 'rqid'> | null,
): void {
  const normalized = normalizeProtocolPrefix(prefix);
  if (normalized.some((record, index) => record !== prefix[index])) {
    throw new ObservableStateError('Observable protocol prefix must already be normalized.');
  }
  for (const record of normalized) {
    if (!record.startsWith('|request|')) continue;
    const parts = record.split('|');
    const rawRequest = parseRawRequestPayload(parts);
    if (Object.keys(rawRequest).some((key) => key !== 'rqid')
      || canonicalize(rawRequest) !== parts.slice(2).join('|')) {
      throw new ObservableStateError('Observable request prefix record is not sanitized.');
    }
  }
  const evidence = parseRawEvidence(normalized, perspective);
  if (!view) return;
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
  if (evidence.terminal_kind !== undefined && !view.terminated) {
    throw new ObservableStateContradictionError('Raw terminal evidence requires a terminated view.');
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
  const rawProtocolPrefix = normalizeProtocolPrefix(input.protocol_prefix);
  validateRawEvidence(rawProtocolPrefix, input.view, input.request, input.perspective);
  const protocolPrefix = sanitizeProtocolPrefix(rawProtocolPrefix);
  const view = cloneView(input.view);
  if (input.schema_version === PUBLIC_STAGES_SCHEMA_VERSION) {
    for (const pokemon of view.opponent_team) pokemon.public_boosts = opponentPublicBoosts(protocolPrefix, pokemon.ident);
  }
  const request = input.request ? cloneRequest(input.request) : null;
  const decision_availability = decisionAvailability(input.view, input.request);
  const protocol_prefix_hash = sha256(protocolPrefix);
  const identity = {
    schema_version: input.schema_version as ObservableSchemaVersion,
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
