import { assertPublicItemsMatchEvidence, projectPublicItems } from './public_item';
import { assertPublicAbilityMatchesEvidence } from './public_ability';
import { assertPublicHealthMatchesEvidence, copyTerminalOwner, boundOwnedTarget } from './public_health';
import { opponentPublicBoosts, type PublicBoosts } from './public_boosts';
import { createHash } from 'node:crypto';
import { isCanonicalPlayerIdent, isCanonicalSideOnlyPlayerIdent, PROTOCOL_CONTRACT, RECOGNIZED_UNSUPPORTED_RAW_COMMANDS, SUPPORTED_RAW_COMMANDS } from './protocol_contract';
import { classifyEffectRecord } from './effect_inventory';
import { assertTypedStateMatchesPublicPrefix } from './typed_state_lifecycle';
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
    // A single final line delimiter belongs to transport framing. Do not
    // normalize any other bytes before protocol validation.
    const normalized = record.endsWith('\r\n')
      ? record.slice(0, -2)
      : record.endsWith('\n') || record.endsWith('\r')
        ? record.slice(0, -1)
        : record;
    if (!normalized) throw new ObservableStateError(`Protocol record ${index} is empty.`);
    if (normalized.includes('\n') || normalized.includes('\r')) {
      throw new ObservableStateError(`Protocol record ${index} contains an embedded protocol record separator.`);
    }
    validateRawProtocolRecord(normalized);
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
  if (!isCanonicalPlayerIdent(parts[index], true)) {
    throw new ObservableStateError(`Malformed raw ${command} record: invalid pokemon identifier.`);
  }
}

function requireRawPlayerReference(parts: string[], index: number, command: string): void {
  requireRawField(parts, index, command, 'pokemon identifier');
  if (!isCanonicalPlayerIdent(parts[index])) {
    throw new ObservableStateError(`Malformed raw ${command} record: invalid pokemon identifier.`);
  }
}

function requireRawHitCountTarget(parts: string[], index: number, command: string): void {
  requireRawPlayerReference(parts, index, command);
  const value = parts[index];
  const separator = PROTOCOL_CONTRACT.validation_rules.player_ident.separator;
  const prefix = value.slice(0, value.indexOf(separator));
  const side = prefix.slice(0, 2);
  const slot = prefix.slice(2);
  const rules = PROTOCOL_CONTRACT.validation_rules.hitcount;
  const role = slot === 'a' ? 'active' : slot === '' ? 'side-only' : undefined;
  if (!PROTOCOL_CONTRACT.validation_rules.player_ident.side_ids.includes(side)
    || !role || !rules.target_roles.includes(role)) {
    throw new ObservableStateError(`Malformed raw ${command} record: target must be a Gen 9 singles active or post-faint side-only ident.`);
  }
}

function requireRawHitCount(parts: string[], index: number, command: string): void {
  requireRawInteger(parts, index, command, 'hit count');
  if (!PROTOCOL_CONTRACT.validation_rules.hitcount.count_values.includes(Number(parts[index]))) {
    throw new ObservableStateError(`Malformed raw ${command} record: hit count is outside the pinned Gen 9 Random Battle domain.`);
  }
}

function requireRawSinglesAnimRoles(parts: string[], command: string): void {
  requireRawPlayerIdent(parts, 2, command);
  requireRawPlayerIdent(parts, 4, command);
  const actorSide = parts[2].slice(0, 3);
  const targetSide = parts[4].slice(0, 3);
  if (!/^p[12]a$/.test(actorSide) || !/^p[12]a$/.test(targetSide) || actorSide === targetSide) {
    throw new ObservableStateError(`Malformed raw ${command} record: source and target must be opposing Gen 9 singles active identifiers.`);
  }
}

function requireRawTarget(parts: string[], index: number, command: string): void {
  requireRawField(parts, index, command, 'target');
  if (parts[index] !== '-' && !isCanonicalPlayerIdent(parts[index], true)) {
    throw new ObservableStateError(`Malformed raw ${command} record: invalid target.`);
  }
}

function requireRawMoveTarget(parts: string[], index: number): void {
  requireRawField(parts, index, 'move', 'target');
  // Pokemon.toString() emits an active-position ident for active Pokemon and
  // a side ident for non-active Pokemon, including side-target move records.
  if (!isCanonicalPlayerIdent(parts[index])) {
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
  const pattern = signed ? /^(?:0|[1-9][0-9]*|-[1-9][0-9]*)$/ : /^(?:0|[1-9][0-9]*)$/;
  if (!pattern.test(parts[index]) || !Number.isSafeInteger(Number(parts[index]))) {
    throw new ObservableStateError(`Malformed raw ${command} record: ${label} must be a safe integer.`);
  }
}

function isRawHealthCondition(value: string): boolean {
  const rules = PROTOCOL_CONTRACT.validation_rules.health_condition;
  if (value === rules.fainted) return true;
  const match = /^([1-9][0-9]*)\/([1-9][0-9]*)(?: ([a-z]+))?$/.exec(value);
  if (!match) return false;
  const numerator = Number(match[1]);
  const denominator = Number(match[2]);
  if (!Number.isSafeInteger(numerator) || !Number.isSafeInteger(denominator) || numerator > denominator) return false;
  return match[3] === undefined || rules.statuses.includes(match[3]);
}

function requireRawHealthCondition(parts: string[], index: number, command: string): void {
  requireRawField(parts, index, command, 'condition');
  if (!isRawHealthCondition(parts[index])) throw new ObservableStateError(`Malformed raw ${command} record: invalid health condition.`);
}

function rawTagKind(tag: string): string {
  const separator = tag.indexOf(' ');
  return separator < 0 ? tag : tag.slice(0, separator);
}

function requireRawEventTags(
  parts: string[],
  start: number,
  command: string,
  rules: readonly string[],
  order: readonly string[],
  singletonKinds: readonly string[],
): void {
  const tags = parts.slice(start);
  const seenTags = new Set<string>();
  const seenKinds = new Set<string>();
  let previousOrder = -1;
  for (const tag of tags) {
    const accepted = rules.some((rule) => {
      if (rule === tag) return true;
      const space = rule.indexOf(' ');
      if (space < 0) return false;
      const prefix = `${rule.slice(0, space)} `;
      const value = tag.startsWith(prefix) ? tag.slice(prefix.length) : '';
      if (!value) return false;
      if (rule.slice(space + 1) === 'trimmed-nonempty-text') return value === value.trim();
      if (rule.slice(space + 1) === 'player-ident') return isCanonicalPlayerIdent(value);
      return false;
    });
    if (!accepted) throw new ObservableStateError(`Malformed raw ${command} record: invalid tag.`);
    const kind = rawTagKind(tag);
    if (singletonKinds.includes(kind) && seenKinds.has(kind)) {
      throw new ObservableStateError(`Malformed raw ${command} record: duplicate singleton tag kind.`);
    }
    if (seenTags.has(tag)) throw new ObservableStateError(`Malformed raw ${command} record: duplicate tag.`);
    seenTags.add(tag);
    seenKinds.add(kind);
    const index = order.indexOf(kind);
    if (index < previousOrder) {
      throw new ObservableStateError(`Malformed raw ${command} record: tags are out of source order.`);
    }
    previousOrder = index;
  }
}

function requireRawHealWisherDependency(parts: string[], command: string): void {
  const tags = parts.slice(4);
  if (!tags.some((tag) => rawTagKind(tag) === '[wisher]')) return;
  const dependency = PROTOCOL_CONTRACT.validation_rules.heal_wisher_dependency;
  if (tags.length !== dependency.required_tag_order.length
    || tags[0] !== dependency.required_from
    || tags.map(rawTagKind).some((kind, index) => kind !== dependency.required_tag_order[index])) {
    throw new ObservableStateError(`Malformed raw ${command} record: [wisher] requires its exact Wish source form.`);
  }
}

function requireRawHealingWishDependency(parts: string[], command: string): void {
  const tags = parts.slice(4);
  // The pinned base-data healing emitter in this name family is Healing Wish.
  // Keep ordinary heal provenance generic, but fail closed on a malformed
  // attempted Healing Wish form rather than publishing an invented move.
  if (!tags.some((tag) => tag.startsWith('[from] move: Healing'))) return;
  const dependency = PROTOCOL_CONTRACT.validation_rules.healing_wish_heal;
  if (parts.length !== 5
    || parts[4] !== dependency.required_from
    || !isCanonicalPlayerIdent(parts[2], true)
    || parts[3] !== dependency.health
    || dependency.required_tag_order.length !== 1) {
    throw new ObservableStateError(`Malformed raw ${command} record: Healing Wish requires its exact source form.`);
  }
}

function requireRawFutureSightDependency(parts: string[], command: string): void {
  const effect = parts[3] || '';
  // Keep general -start/-end grammar intact. Only the pinned Future Sight
  // name family is constrained here, because its source emits no tags or
  // private slot data on either public boundary record.
  // Treat any attempted spelling in this source family as Future Sight input.
  // Otherwise a leading space or extra separator could evade the exact check
  // and fall through to the generic raw start/end grammar.
  if (!/(?:future\s*sight)|(?:^\s*move[\s:]+future)/i.test(effect)) return;
  const dependency = PROTOCOL_CONTRACT.validation_rules.future_sight;
  if (command !== dependency.activation_command && command !== dependency.resolution_command) return;
  if (parts.length !== dependency.payload_fields + 3
    || effect !== dependency.effect
    || !isCanonicalPlayerIdent(parts[2], dependency.target_role === 'active')) {
    throw new ObservableStateError(`Malformed raw ${command} record: Future Sight requires its exact source form.`);
  }
}

function requireRawRepeatUseHint(parts: string[], command: string): void {
  const message = parts[2] ?? '';
  // Other reviewed public diagnostics remain raw-only. A source-family
  // spelling attempt cannot fall back to that generic diagnostic grammar.
  if (!/^\s*Some\s+effects\s+can\s+force\s+a\s+Pokemon\s+to\s+use\b/i.test(message)) return;
  const rule = PROTOCOL_CONTRACT.validation_rules.repeat_use_hint;
  if (parts.length !== rule.payload_fields + 2 || !rule.messages.includes(message)) {
    throw new ObservableStateError(`Malformed raw ${command} record: repeat-use hint requires its exact source form.`);
  }
}

function requireRawEntryHazard(parts: string[], command: string): void {
  if (!['-sidestart', '-sideend'].includes(command)) return;
  const rules = PROTOCOL_CONTRACT.validation_rules.entry_hazard;
  const effect = (parts[3] || '').replace(/^move:\s*/i, '').toLowerCase().replace(/[^a-z0-9]+/g, '');
  if (!Object.hasOwn(rules.layers, effect)) return;
  if (!isCanonicalSideOnlyPlayerIdent(parts[2])) {
    throw new ObservableStateError(`Malformed raw ${command} record: hazard side must be canonical.`);
  }
  const titles: Record<string, string> = {
    spikes: 'Spikes', toxicspikes: 'Toxic Spikes', stealthrock: 'Stealth Rock', stickyweb: 'Sticky Web',
  };
  if (command === '-sidestart') {
    if (parts.length !== 4 || parts[3] !== rules.start_forms[effect]) {
      throw new ObservableStateError(`Malformed raw ${command} record: unsupported entry-hazard start form.`);
    }
    return;
  }
  if (parts[3] !== titles[effect]) {
    // Toxic Spikes' absorbing-Poison path is the sole side-end spelling that
    // retains its move prefix; its [of] tag is the switching active Pokemon.
    if (!(effect === 'toxicspikes' && parts[3] === 'move: Toxic Spikes')) {
      throw new ObservableStateError(`Malformed raw ${command} record: unsupported entry-hazard end form.`);
    }
    if (parts.length !== 5 || !parts[4].startsWith('[of] ') || !isCanonicalPlayerIdent(parts[4].slice(5), true)) {
      throw new ObservableStateError(`Malformed raw ${command} record: malformed Toxic Spikes absorption.`);
    }
    return;
  }
  if (parts.length === 4) return; // Tidy Up removes every active hazard without provenance tags.
  if (parts.length !== 6 || !parts[4].startsWith('[from] move: ') || !parts[5].startsWith('[of] ')
    || !rules.removal_sources.includes(parts[4].slice('[from] move: '.length))
    || !isCanonicalPlayerIdent(parts[5].slice(5), true)) {
    throw new ObservableStateError(`Malformed raw ${command} record: unsupported entry-hazard removal form.`);
  }
}


function requireRawScreen(parts: string[], command: string): void {
  if (!['sidestart', '-sidestart', 'sideend', '-sideend'].includes(command)) return;
  const rules = PROTOCOL_CONTRACT.validation_rules.screen;
  const effect = (parts[3] || '').replace(/^move:\s*/i, '').toLowerCase().replace(/[^a-z0-9]+/g, '');
  const excluded = rules.excluded_forms.map(value => value.toLowerCase().replace(/[^a-z0-9]+/g, ''));
  if (!rules.ids.includes(effect)) {
    if (excluded.includes(effect)) throw new ObservableStateError(`Malformed raw ${command} record: unsupported generated screen form.`);
    return;
  }
  const expected = command === '-sidestart' ? rules.start_forms[effect]
    : command === '-sideend' ? rules.end_forms[effect] : undefined;
  if (!expected || parts.length !== 4 || parts[3] !== expected || !isCanonicalSideOnlyPlayerIdent(parts[2])) {
    throw new ObservableStateError(`Malformed raw ${command} record: unsupported screen source form.`);
  }
}

function requireRawCourtChange(parts: string[], command: string): void {
  const rules = PROTOCOL_CONTRACT.validation_rules.court_change;
  if (command === 'swapsideconditions') {
    throw new ObservableStateError('Malformed raw swapsideconditions record: Court Change emits only the pinned dash command.');
  }
  if (command === rules.command) {
    if (parts.length !== 2) {
      throw new ObservableStateError('Malformed raw -swapsideconditions record: Court Change has no participants, tags, or payload.');
    }
    return;
  }
  if (command !== rules.activation_command) return;
  const effect = parts[3] || '';
  // A spacing/reseparator attempt must not fall through to generic activation
  // grammar just because it is not the exact source spelling.
  if (!/court\s*change/i.test(effect)) return;
  if (parts.length !== 4 || effect !== rules.activation_effect || !isCanonicalPlayerIdent(parts[2], true) || !/^p[12]a: /.test(parts[2])) {
    throw new ObservableStateError('Malformed raw -activate record: Court Change requires an active source and its exact source form.');
  }
}

function requireRawWeather(parts: string[], command: string): void {
  if (command !== '-weather') return;
  const rules = PROTOCOL_CONTRACT.validation_rules.weather;
  const effect = parts[2] || '';
  // `none` is only emitted by Conditions.<weather>.onFieldEnd. A replacement
  // calls the new condition's FieldStart directly, so it must not manufacture
  // an intervening clear record.
  if (effect === 'none') {
    if (parts.length !== 3) throw new ObservableStateError('Malformed raw -weather record: clear has no tags.');
    return;
  }
  if (!rules.ids.includes(effect)) {
    throw new ObservableStateError('Malformed raw -weather record: unsupported generated weather.');
  }
  if (parts.length === 3 && rules.move_origins[effect]?.length) return; // direct generated move start
  if (parts.length === 4 && parts[3] === '[upkeep]') return;
  if (parts.length === 5 && parts[3].startsWith('[from] ability: ') && parts[4].startsWith('[of] ')) {
    const ability = parts[3].slice('[from] ability: '.length);
    const source = parts[4].slice('[of] '.length);
    if (rules.ability_origins[effect]?.includes(ability)
      && isCanonicalPlayerIdent(source, true) && /^p[12]a: /.test(source)) return;
  }
  throw new ObservableStateError('Malformed raw -weather record: unsupported source grammar.');
}

function requireRawTerrain(parts: string[], command: string): void {
  if (!['fieldstart', '-fieldstart', 'fieldend', '-fieldend', '-fieldactivate'].includes(command)) return;
  const rules = PROTOCOL_CONTRACT.validation_rules.terrain;
  const effect = parts[2] || '';
  const terrain = rules.ids.find((id) => rules.public_names[id] === effect);
  if (!terrain) {
    // Field pseudo-weather retains its separately reviewed grammar. An attempted
    // terrain spelling cannot bypass the finite generated terrain boundary.
    if (/terrain/i.test(effect)) throw new ObservableStateError(`Malformed raw ${command} record: unsupported generated terrain.`);
    return;
  }
  if (command === 'fieldstart' || command === 'fieldend' || command === '-fieldactivate') {
    throw new ObservableStateError(`Malformed raw ${command} record: terrain uses the pinned dash command.`);
  }
  if (command === '-fieldend') {
    if (parts.length !== 3) throw new ObservableStateError('Malformed raw -fieldend record: terrain clear has no tags.');
    return;
  }
  if (parts.length === 5 && parts[3].startsWith('[from] ability: ') && parts[4].startsWith('[of] ')) {
    const ability = parts[3].slice('[from] ability: '.length);
    const source = parts[4].slice('[of] '.length);
    if (rules.ability_origins[terrain]?.includes(ability)
      && isCanonicalPlayerIdent(source, true) && /^p[12]a: /.test(source)) return;
  }
  throw new ObservableStateError('Malformed raw -fieldstart record: unsupported terrain source grammar.');
}

function requireRawTrickRoom(parts: string[], command: string): void {
  if (!['fieldstart', '-fieldstart', 'fieldend', '-fieldend', '-fieldactivate'].includes(command)) return;
  const rules = PROTOCOL_CONTRACT.validation_rules.trick_room;
  if ((parts[2] || '').replace(/^move:\s*/i, '').toLowerCase().replace(/[^a-z0-9]+/g, '') !== 'trickroom') return;
  if ((parts[2] || '') !== rules.effect) {
    throw new ObservableStateError(`Malformed raw ${command} record: unsupported Trick Room effect spelling.`);
  }
  if (command === rules.end_command) {
    if (parts.length !== 3) throw new ObservableStateError('Malformed raw -fieldend record: Trick Room clear has no tags.');
    return;
  }
  if (command === rules.start_command && parts.length === 4 && parts[3].startsWith(`${rules.source_tag} `)) {
    const source = parts[3].slice(rules.source_tag.length + 1);
    if (isCanonicalPlayerIdent(source, true) && /^p[12]a: /.test(source)) return;
  }
  throw new ObservableStateError(`Malformed raw ${command} record: unsupported Trick Room source grammar.`);
}

function requireRawAutoTieWarning(parts: string[], command: string): void {
  if (parts.length !== 3) throw new ObservableStateError(`Malformed raw ${command} record.`);
  const rule = PROTOCOL_CONTRACT.validation_rules.bigerror;
  const match = /^You will auto-tie if the battle doesn't end in ([1-9][0-9]*) (turn|turns) \(on turn 1000\)\.$/.exec(parts[2]);
  if (!match) throw new ObservableStateError(`Malformed raw ${command} record: unsupported diagnostic.`);
  const turnsLeft = Number(match[1]);
  if (!Number.isSafeInteger(turnsLeft) || !rule.turns_left_values.includes(turnsLeft)
    || (turnsLeft === 1 ? match[2] !== 'turn' : match[2] !== 'turns')) {
    throw new ObservableStateError(`Malformed raw ${command} record: unsupported diagnostic.`);
  }
}

function hasOnlyFiniteJsonNumbers(value: unknown): boolean {
  if (typeof value === 'number') return Number.isFinite(value);
  if (Array.isArray(value)) return value.every(hasOnlyFiniteJsonNumbers);
  if (value !== null && typeof value === 'object') return Object.values(value).every(hasOnlyFiniteJsonNumbers);
  return true;
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
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed) || !hasOnlyFiniteJsonNumbers(parsed)) {
    throw new ObservableStateError('Malformed raw request record.');
  }
  const request = parsed as Record<string, unknown>;
  if (Object.hasOwn(request, 'rqid') && (typeof request.rqid !== 'number' || !Number.isSafeInteger(request.rqid))) {
    throw new ObservableStateError('Malformed raw request rqid.');
  }
  return request;
}

function requireRawAbilityEvent(parts: string[], command: string): void {
  const rule = PROTOCOL_CONTRACT.validation_rules.ability;
  if (parts.length < 4) throw new ObservableStateError(`Malformed raw ${command} record.`);
  requireRawPlayerIdent(parts, 2, command);
  requireRawField(parts, 3, command, 'ability');
  if (parts[3] !== parts[3].trim()) {
    throw new ObservableStateError(`Malformed raw ${command} record: invalid ability.`);
  }
  const requirePayload = (domain: keyof typeof rule.payload_domains): void => {
    if (!rule.payload_domains[domain].includes(parts[3])) {
      throw new ObservableStateError(`Malformed raw ${command} record: ability payload is outside the ${domain} source-proven domain.`);
    }
  };
  if (parts.length === 4) {
    requirePayload(command === 'ability' ? 'bare_reveal' : 'dash_reveal');
    return;
  }
  if (command === 'ability') {
    throw new ObservableStateError('Malformed raw ability record: compatibility alias has only the plain reveal template.');
  }
  if (parts.length === 5 && parts[4] === 'boost') {
    requirePayload('dash_boost');
    return;
  }
  if (parts.length === 6 && parts[4] === rule.trace_source_tag
      && parts[5].startsWith(rule.trace_of_tag)) {
    const actor = parts[2];
    const source = parts[5].slice(rule.trace_of_tag.length);
    if (!isCanonicalPlayerIdent(source, true) || actor.slice(0, 2) === source.slice(0, 2)) {
      throw new ObservableStateError(`Malformed raw ${command} record: Trace source must be an opposing active ident.`);
    }
    requirePayload('dash_trace_copy');
    return;
  }
  throw new ObservableStateError(`Malformed raw ${command} record: unsupported ability provenance.`);
}

/**
 * Item names become public only at the small set of Gen 9 Random Battle
 * protocol boundaries documented in CE-04F1.  Do not repair a spelling or
 * accept an arbitrary provenance suffix: both would turn a fabricated item
 * disclosure into typed public state.
 */
function requireRawItemEvent(parts: string[], command: string): void {
  const rule = PROTOCOL_CONTRACT.validation_rules.item as {
    payloads: string[];
    active_target: string;
    dash_item_forms: Array<{tags: string[]; payloads?: string[]}>;
    dash_enditem_forms: Array<{tags: string[]; payloads?: string[]}>;
    bare_commands: string[];
    bare_tags: string[];
  };
  if (parts.length < 4) throw new ObservableStateError(`Malformed raw ${command} record.`);
  const actor = parts[2];
  if (!isCanonicalPlayerIdent(actor, true) || !/^p[12]a: /.test(actor)) {
    throw new ObservableStateError(`Malformed raw ${command} record: target must be a Gen 9 singles active ident.`);
  }
  const item = parts[3];
  if (item !== item.trim() || !rule.payloads.includes(item)) {
    throw new ObservableStateError(`Malformed raw ${command} record: item payload is outside the generated source domain.`);
  }
  const tags = parts.slice(4);
  if (rule.bare_commands.includes(command)) {
    if (tags.length !== 0) throw new ObservableStateError(`Malformed raw ${command} record: compatibility form has no tags.`);
    return;
  }
  const forms = command === '-item' ? rule.dash_item_forms : rule.dash_enditem_forms;
  const match = forms.find((form) => form.tags.length === tags.length
    && form.tags.every((tag, index) => tag === tags[index] || tag === '[of] opposing-active'));
  if (!match || (match.payloads && !match.payloads.includes(item))) {
    throw new ObservableStateError(`Malformed raw ${command} record: unsupported item source grammar.`);
  }
  const ofIndex = match.tags.indexOf('[of] opposing-active');
  if (ofIndex >= 0) {
    const source = tags[ofIndex];
    const prefix = '[of] ';
    const ident = source.startsWith(prefix) ? source.slice(prefix.length) : '';
    if (!isCanonicalPlayerIdent(ident, true) || !/^p[12]a: /.test(ident) || ident.slice(0, 2) === actor.slice(0, 2)) {
      throw new ObservableStateError(`Malformed raw ${command} record: source must be an opposing Gen 9 singles active ident.`);
    }
  }
}

/**
 * Public major-status records are state evidence, so their sparse protocol
 * grammar is closed before the extractor can alter a typed status field.
 * Pinned Gen 9 sources use only dashed command tokens; bare aliases stop.
 */
function requireRawMajorStatusEvent(parts: string[], command: string): void {
  const rule = PROTOCOL_CONTRACT.validation_rules.major_status;
  if (parts.length < 4) throw new ObservableStateError(`Malformed raw ${command} record.`);
  const target = parts[2];
  if (!isCanonicalPlayerIdent(target, true) || !/^p[12]a: /.test(target)) {
    throw new ObservableStateError(`Malformed raw ${command} record: target must be a Gen 9 singles active ident.`);
  }
  const status = parts[3];
  if (!rule.ids.includes(status)) {
    throw new ObservableStateError(`Malformed raw ${command} record: unsupported major status.`);
  }
  const tags = parts.slice(4);
  if (rule.bare_commands.includes(command)) {
    if (tags.length !== 0) throw new ObservableStateError(`Malformed raw ${command} record: compatibility form has no tags.`);
    return;
  }
  const forms = command === '-status' ? rule.apply_forms : rule.cure_forms;
  const match = forms.find((form) => form.tags.length === tags.length
    && form.tags.every((tag, index) => tag === tags[index] || tag === '[of] opposing-active'));
  if (!match || (match.statuses && !match.statuses.includes(status))) {
    throw new ObservableStateError(`Malformed raw ${command} record: unsupported major-status source grammar.`);
  }
  const ofIndex = match.tags.indexOf('[of] opposing-active');
  if (ofIndex >= 0) {
    const tag = tags[ofIndex];
    const source = tag.startsWith('[of] ') ? tag.slice('[of] '.length) : '';
    if (!isCanonicalPlayerIdent(source, true) || !/^p[12]a: /.test(source) || source.slice(0, 2) === target.slice(0, 2)) {
      throw new ObservableStateError(`Malformed raw ${command} record: source must be an opposing Gen 9 singles active ident.`);
    }
  }
}

function validateRawRecordShape(parts: string[], command: string): void {
  const requireAtLeast = (length: number): void => {
    if (parts.length < length) throw new ObservableStateError(`Malformed raw ${command} record.`);
  };
  const requireIdent = (index = 2): void => requireRawPlayerIdent(parts, index, command);
  requireRawCourtChange(parts, command);
  if (command === PROTOCOL_CONTRACT.validation_rules.court_change.command) return;
  const noPayload = new Set([
    'clearallboost', '-clearallboost',
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
    case '-singlemove':
      requireIdent();
      if (!/^p[12]a: /.test(parts[2])) {
        throw new ObservableStateError(`Malformed raw ${command} record: target must be a Gen 9 singles active ident.`);
      }
      if (!PROTOCOL_CONTRACT.validation_rules.singlemove.forms.some((form) =>
        parts.length === form.length + 3 && form.every((field, index) => parts[index + 3] === field))) {
        throw new ObservableStateError(`Malformed raw ${command} record: unsupported effect/tag combination.`);
      }
      return;
    case '-singleturn':
      if (parts.length !== 4 && parts.length !== 5) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireIdent();
      requireRawField(parts, 3, command, 'effect');
      const rules = PROTOCOL_CONTRACT.validation_rules.singleturn;
      if (parts.length === 5) {
        const effect = parts[3];
        const tag = parts[4];
        const matchingForm = rules.tagged_forms.find((form) => form.effect === effect
          && (form.tag_value === 'none' ? tag === form.tag : tag.startsWith(`${form.tag} `)));
        if (!matchingForm) throw new ObservableStateError(`Malformed raw ${command} record: unsupported effect/tag combination.`);
        if (matchingForm.tag_value === 'player-ident') {
          const sourceIdent = tag.slice(matchingForm.tag.length + 1);
          if (!isCanonicalPlayerIdent(sourceIdent, matchingForm.ident_role === 'active')) {
            throw new ObservableStateError(`Malformed raw ${command} record: invalid single-turn source ident.`);
          }
        }
      } else if (!rules.untagged_effects.includes(parts[3])) {
        throw new ObservableStateError(`Malformed raw ${command} record: unsupported untagged effect.`);
      }
      return;
    case 'cant':
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'reason');
      if (parts.length > 4) requireRawField(parts, 4, command, 'move');
      return;
    case '-hitcount':
      if (parts.length !== 4) throw new ObservableStateError(`Malformed raw ${command} record.`);
      // BattleActions emits after faintMessages; a final multi-hit KO has lost
      // its active slot and is consequently rendered as `p1: Name`.
      requireRawHitCountTarget(parts, 2, command);
      requireRawHitCount(parts, 3, command);
      return;
    case 'faint':
      if (parts.length !== 3) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireIdent();
      return;
    case 'switch':
    case 'drag':
      if (parts.length !== 5 && parts.length !== 6) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireIdent();
      requireRawField(parts, 3, command, 'details');
      requireRawHealthCondition(parts, 4, command);
      if (parts.length === 6) {
        const rule = PROTOCOL_CONTRACT.validation_rules.switch_drag.optional_tag;
        const tagPrefix = `${rule.slice(0, rule.indexOf(' '))} `;
        const sourceName = parts[5].slice(tagPrefix.length);
        if (!parts[5].startsWith(tagPrefix) || !sourceName || sourceName !== sourceName.trim()) {
          throw new ObservableStateError(`Malformed raw ${command} record: invalid source tag.`);
        }
      }
      if (parts.length > 6) throw new ObservableStateError(`Malformed raw ${command} record.`);
      return;
    case 'detailschange':
      if (parts.length !== 4 && parts.length !== 5) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireIdent();
      requireRawField(parts, 3, command, 'details');
      if (parts.length === 5) requireRawHealthCondition(parts, 4, command);
      return;
    case 'replace':
      // Illusion.onEnd emits ident + details only. Legacy HP-bearing records
      // remain valid, but arbitrary trailing fields/conditions are not accepted.
      if (parts.length !== 4 && parts.length !== 5) throw new ObservableStateError('Malformed raw replace record.');
      requireIdent();
      requireRawField(parts, 3, command, 'details');
      if (parts.length === 5 && !isRawHealthCondition(parts[4])) {
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
      // These source-emitted public records carry no typed mechanics. Keep
      // their exact bounded label grammar separate from move-record grammar.
      if (parts.length !== 5
        || !PROTOCOL_CONTRACT.validation_rules.anim.forms.some(([label]) => parts[3] === label)) {
        throw new ObservableStateError(`Malformed raw ${command} record: unsupported animation grammar.`);
      }
      requireRawSinglesAnimRoles(parts, command);
      return;
    case '-hint':
      // Public diagnostics remain raw-only. The repeat-use source family has a
      // finite generated payload domain and must be exact.
      requireAtLeast(3);
      requireRawField(parts, 2, command, 'message');
      requireRawRepeatUseHint(parts, command);
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
      requireAtLeast(4);
      requireIdent();
      requireRawField(parts, 3, command, 'target');
      return;
    case '-transform':
      requireAtLeast(4);
      requireIdent();
      requireRawPlayerIdent(parts, 3, command);
      return;
    case 'damage':
    case '-damage':
    case 'heal':
    case '-heal':
    case 'sethp':
    case '-sethp':
      requireAtLeast(4);
      // Revival publicly heals a benched Pokémon using p1:/p2:, not an active position.
      const revivalBlessingBench = command === '-heal' && parts.length === 5
        && parts[4] === '[from] move: Revival Blessing' && isCanonicalSideOnlyPlayerIdent(parts[2]);
      if (!revivalBlessingBench) requireIdent();
      requireRawHealthCondition(parts, 3, command);
      const tagGroup = command.replace(/^-/, '') as 'damage' | 'heal' | 'sethp';
      requireRawEventTags(
        parts,
        4,
        command,
        PROTOCOL_CONTRACT.validation_rules.health_event_tags[tagGroup],
        PROTOCOL_CONTRACT.validation_rules.health_event_tag_order[tagGroup],
        PROTOCOL_CONTRACT.validation_rules.event_tag_cardinality[tagGroup],
      );
      if (command === '-heal') {
        requireRawHealWisherDependency(parts, command);
        requireRawHealingWishDependency(parts, command);
      }
      return;
    case 'status':
    case '-status':
      requireRawMajorStatusEvent(parts, command);
      return;
    case 'curestatus':
    case '-curestatus':
      requireRawMajorStatusEvent(parts, command);
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
      if (!PROTOCOL_CONTRACT.validation_rules.boost_event.stats.includes(parts[3])) {
        throw new ObservableStateError(`Malformed raw ${command} record: invalid stat.`);
      }
      requireRawInteger(parts, 4, command, 'amount', command === 'setboost' || command === '-setboost');
      {
        const rules = PROTOCOL_CONTRACT.validation_rules.boost_event;
        const amount = Number(parts[4]);
        const [minimum, maximum] = command === 'setboost' || command === '-setboost'
          ? [rules.set_min, rules.set_max]
          : [rules.delta_min, rules.delta_max];
        if (amount < minimum || amount > maximum) throw new ObservableStateError(`Malformed raw ${command} record: amount is outside the supported stage range.`);
      }
      requireRawEventTags(
        parts,
        5,
        command,
        PROTOCOL_CONTRACT.validation_rules.boost_event.tags,
        PROTOCOL_CONTRACT.validation_rules.boost_event.tag_order,
        PROTOCOL_CONTRACT.validation_rules.event_tag_cardinality.boost,
      );
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
      if (parts.length !== 5) throw new ObservableStateError(`Malformed raw ${command} record.`);
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
      if (command === '-start' || command === '-end') requireRawFutureSightDependency(parts, command);
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
      requireRawWeather(parts, command);
      requireRawTerrain(parts, command);
      requireRawTrickRoom(parts, command);
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
      const trapped = PROTOCOL_CONTRACT.validation_rules.trapped_activation;
      if (command === trapped.token && parts[3].trim() === trapped.effect
        && (parts[3] !== trapped.effect || parts.length !== trapped.payload_fields + 2)) {
        throw new ObservableStateError(`Malformed raw ${command} record: trapped activation must use the exact source grammar.`);
      }
      requireRawCourtChange(parts, command);
      return;
    case 'sidestart':
    case '-sidestart':
    case 'sideend':
    case '-sideend':
      requireAtLeast(4);
      if (!/^p[12](?::|$)/.test(parts[2])) throw new ObservableStateError(`Malformed raw ${command} record.`);
      requireRawField(parts, 3, command, 'condition');
      requireRawEntryHazard(parts, command);
      requireRawScreen(parts, command);
      return;
    case 'ability':
    case '-ability':
      requireRawAbilityEvent(parts, command);
      return;
    case 'item':
    case '-item':
    case 'enditem':
    case '-enditem':
      requireRawItemEvent(parts, command);
      return;
    case 'tier':
      if (parts.length !== PROTOCOL_CONTRACT.validation_rules.tier.payload_fields + 2) {
        throw new ObservableStateError(`Malformed raw ${command} record.`);
      }
      requireRawField(parts, 2, command, 'format label');
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
    case 'bigerror':
      requireRawAutoTieWarning(parts, command);
      return;
    default:
      if (parts.length < 3 || parts.slice(2).some((field) => !field.trim())) {
        throw new ObservableStateError(`Malformed raw ${command} record.`);
      }
  }
}

function sanitizeProtocolPrefix(prefix: readonly string[]): string[] {
  const sanitized: string[] = [];
  for (const record of prefix) {
    const parts = record.split('|');
    if (record === PROTOCOL_CONTRACT.framing_only_records[0].record || parts[1] === 'tier') continue;
    if (parts[1] !== 'request') {
      sanitized.push(record);
      continue;
    }
    const request = parseRawRequestPayload(parts);
    const publicRequest = Object.hasOwn(request, 'rqid') ? { rqid: request.rqid } : {};
    sanitized.push(`|request|${canonicalize(publicRequest)}`);
  }
  return sanitized;
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
  assertNoPrivateSlotState(input);
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

function assertNoPrivateSlotState(value: unknown, location = 'observable input'): void {
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    if (['slotconditions', 'slot_conditions', 'slot_condition_state', 'pending_slots'].includes(key.toLowerCase())) {
      throw new ObservableStateError(`Private simulator slot state is not publishable (${location}.${key}).`);
    }
    assertNoPrivateSlotState(child, `${location}.${key}`);
  }
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
  if (!record.startsWith('|') || record.includes('\n') || record.includes('\r')) throw new ObservableStateError('Malformed raw protocol record.');
  if (record === PROTOCOL_CONTRACT.framing_only_records[0].record) return;
  const parts = record.split('|');
  const command = parts[1];
  if (!command || (!SUPPORTED_RAW_COMMANDS.has(command) && !RECOGNIZED_UNSUPPORTED_RAW_COMMANDS.has(command))) {
    throw new ObservableStateError(`Unsupported raw protocol event: ${command || '<empty>'}.`);
  }
  if (RECOGNIZED_UNSUPPORTED_RAW_COMMANDS.has(command)) {
    throw new ObservableStateError(`Unsupported raw protocol event: ${command}.`);
  }
  validateRawRecordShape(parts, command);
  const effectField = ['-start', '-end'].includes(command) ? 3
    : ['-weather', '-fieldstart', '-fieldend'].includes(command) ? 2
      : ['-sidestart', '-sideend'].includes(command) ? 3 : -1;
  if (effectField >= 0) classifyEffectRecord(command, parts[effectField] || '');
}

function parseIntegerRecord(parts: string[], label: string): number {
  if (parts.length !== 3 || !/^(?:0|[1-9][0-9]*)$/.test(parts[2]) || !Number.isSafeInteger(Number(parts[2]))) {
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
  const publicItems = projectPublicItems(protocolPrefix);
  for (const pokemon of view.opponent_team) {
    const target = pokemon.ident?.replace(/^(p[12])a: /, '$1: ');
    if (target && publicItems[target] !== undefined && publicItems[target] !== null) pokemon.item = 'has-item';
    else delete pokemon.item;
  }
  copyTerminalOwner(input.view as unknown as Record<string, unknown>, view as unknown as Record<string, unknown>);
  assertTypedStateMatchesPublicPrefix(protocolPrefix, input.perspective, view, (target) => boundOwnedTarget(protocolPrefix, input.perspective, view as unknown as Record<string, unknown>, input.request as unknown as Record<string, unknown> | null, target));
  assertPublicHealthMatchesEvidence(protocolPrefix, input.perspective, view as unknown as Record<string, unknown>, input.request as unknown as Record<string, unknown> | null);
  assertPublicItemsMatchEvidence(protocolPrefix, input.perspective, view as unknown as Record<string, unknown>, input.request as unknown as Record<string, unknown> | null);
  assertPublicAbilityMatchesEvidence(protocolPrefix, view as unknown as Record<string, unknown>, input.request as unknown as Record<string, unknown> | null, input.perspective);
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
