import { abilityEffectiveness, publicGasSources, publicTraceAbilities, publicRevealedAbilities, preservesOwnedAbilityForForm } from './public_ability';
import {projectPublicOwnedItemHistory, ambiguousOwnedItemTargets} from './public_item';
import { Dex, toID } from 'pokemon-showdown';
import { isCanonicalPlayerIdent, PROTOCOL_CONTRACT, RECOGNIZED_UNSUPPORTED_RAW_COMMANDS, SUPPORTED_RAW_COMMANDS } from './protocol_contract';
import { classifyEffectRecord } from './effect_inventory';
import { ObservableStateError, validateRawProtocolRecord } from './observable_state';
import { normalizeRequest } from './action_codec';
import type {CanonicalAction} from './canonical_action';
import { PUBLIC_TYPED_STATE_LIFECYCLE, typedStateLifecycleEntry } from './typed_state_lifecycle';
import {
  createEmptyBattleView,
  type BattleView,
  type ChoiceRequestView,
  type PlayerID,
  type PokemonView,
  type Winner,
} from './types';
import {
  clonePokemon,
  normalizeEffectId,
  parseCondition,
  parseDetails,
  parseIdent,
  resolveTypes,
  splitProtocolLine,
  upsertUnique,
} from './battle_helpers';

/** `getPlayerStreams` removes the split marker before it reaches its owner. */
export function isOwnerPrivateHealingWishHeal(line: string, owner: PlayerID): boolean {
  const parts = splitProtocolLine(line);
  if (parts.length !== 5 || parts[1] !== '-heal'
    || parts[4] !== '[from] move: Healing Wish'
    || !isCanonicalPlayerIdent(parts[2], true)
    || !parts[2].startsWith(`${owner}a:`)) return false;
  return /^([1-9][0-9]*)\/\1$/.test(parts[3] || '');
}

function isPublicHealingWishHeal(line: string): boolean {
  const parts = splitProtocolLine(line);
  return parts.length === 5 && parts[1] === '-heal'
    && parts[3] === '100/100' && parts[4] === '[from] move: Healing Wish';
}

function createPokemonView(slot: number, ident = '', details = ''): PokemonView {
  const parsedDetails = parseDetails(details);
  const parsedCondition = parseCondition('');

  return {
    slot,
    ident,
    name: parseIdent(ident).name || parsedDetails.species,
    species: parsedDetails.species,
    base_species: parsedDetails.species || null,
    current_species: parsedDetails.species || null,
    displayed_species: parsedDetails.species || null,
    species_source: parsedDetails.species ? 'protocol' : 'unknown',
    transformed: false,
    displayed_species_uncertain: false,
    illusion_revealed: false,
    details,
    active: false,
    fainted: parsedCondition.fainted,
    hp_text: parsedCondition.hpText,
    hp_ratio: parsedCondition.hpRatio,
    status: parsedCondition.status,
    status_source: 'unknown',
    status_started_turn: null,
    status_turns_public: null,
    gender: parsedDetails.gender,
    level: parsedDetails.level,
    item: null,
    last_item: null,
    item_state: 'unknown',
    item_suppressed: false,
    ability: null,
    base_ability: null,
    ability_state: 'unknown',
    ability_suppressed: false,
    moves: [],
    revealed_moves: [],
    types: resolveTypes(parsedDetails.species, parsedDetails.teraType, false),
    tera_type: parsedDetails.teraType,
    terastallized: false,
    stats: {},
    boosts: {},
    volatiles: [],
    possible_roles: [],
    possible_moves: [],
    possible_abilities: [],
    possible_tera_types: [],
  };
}

export class PlayerStateExtractor {
  readonly envId: string;
  readonly player: PlayerID;
  readonly opponent: PlayerID;
  readonly format: string;

  private view: BattleView;
  private currentRequest: ChoiceRequestView | null;
  // Public positions are appearances, not confirmed roster names. Requests never
  // mutate this protocol state, so replay with only the latest request is equivalent.
  private readonly publicActive: Partial<Record<PlayerID, {
    pokemon: PokemonView;
    prior?: PokemonView;
  }>> = {};
  // Protocol-derived ordinary typing belongs to the active appearance, not its
  // displayed roster alias. Replay reconstructs this map without private state.
  private readonly publicTypeChanges = new WeakMap<PokemonView, string[]>();
  private readonly publicAddedTypes = new WeakMap<PokemonView, string>();
  private ownRequestData: any = null;
  private ownedItemHistoryCache: {key: string; history: ReturnType<typeof projectPublicOwnedItemHistory>} | null = null;
  private submittedSwitch: {ident: string; cursor: number; action: CanonicalAction; force_switch: boolean} | null = null;

  /** The caller validates the canonical action against the live owned request first. */
  recordSubmittedSwitch(action: CanonicalAction | null, forceSwitch = false): void {
    const ident = action && this.ownRequestData?.side?.pokemon[action.switch_slot! - 1]?.ident;
    this.submittedSwitch = ident ? {ident, cursor: this.publicAbilityPrefix.length, action: structuredClone(action!), force_switch: forceSwitch} : null;
  }
  getSubmittedSwitch(): {action: CanonicalAction; cursor: number; force_switch: boolean} | null {
    return this.submittedSwitch && this.view.terminated ? {action: structuredClone(this.submittedSwitch.action), cursor: this.submittedSwitch.cursor, force_switch: this.submittedSwitch.force_switch} : null;
  }
  restoreSubmittedSwitch(value: {action: CanonicalAction; cursor: number; force_switch: boolean}): void {
    const ident = this.ownRequestData?.side?.pokemon[value.action.switch_slot! - 1]?.ident;
    this.submittedSwitch = {ident, action: structuredClone(value.action), cursor: value.cursor, force_switch: value.force_switch};
  }

  private defensiveTypes(pokemon: PokemonView | undefined, species: string, teraType: string | null, terastallized: boolean): string[] {
    if (terastallized && teraType && teraType !== 'Stellar') return [teraType];
    const publicTypes = pokemon && this.publicTypeChanges.get(pokemon);
    const ordinary = publicTypes ? [...publicTypes] : resolveTypes(species, teraType, terastallized);
    const added = pokemon && this.publicAddedTypes.get(pokemon);
    return added ? [...new Set([...ordinary, added])] : ordinary;
  }

  constructor(envId: string, format: string, player: PlayerID) {
    this.envId = envId;
    this.player = player;
    this.opponent = player === 'p1' ? 'p2' : 'p1';
    this.format = format;
    this.view = createEmptyBattleView(envId, format, player);
    this.currentRequest = null;
  }

  private publicAbilityPrefix: string[] = [];

  consumeChunk(chunk: string): void {
    for (const rawLine of chunk.split('\n')) {
      const line = rawLine.replace(/\r$/, '');
      if (line === '') {
        continue;
      }
      // The owner-private branch holds exact HP. It is deliberately omitted:
      // the spectator's paired public 100/100 record is routed below.
      if (isOwnerPrivateHealingWishHeal(line, this.player)) continue;
      if (line.startsWith('|')) {
        const command = line.split('|')[1];
        if (command && (SUPPORTED_RAW_COMMANDS.has(command) || RECOGNIZED_UNSUPPORTED_RAW_COMMANDS.has(command))) {
          validateRawProtocolRecord(line);
        }
      } else if (/^\s*\|/.test(line)) {
        // Detect a protocol record with leading whitespace without repairing
        // it; the validator must see and reject the original line.
        validateRawProtocolRecord(line);
      }
      if (line.startsWith('|') && !line.startsWith('|request|')) this.publicAbilityPrefix.push(line);
      this.consumeLine(line);
    }
  }

  /** Route the one public Healing Wish result from the spectator stream. */
  consumePublicHealingWishRecord(line: string): void {
    if (!isPublicHealingWishHeal(line)) return;
    validateRawProtocolRecord(line);
    this.consumeLine(line);
  }

  getView(): BattleView {
    const selfTeam = this.ownRequestData ? this.selfFromRequest(this.ownRequestData) : this.view.self_team;
    const gasPresent = publicGasSources(this.publicAbilityPrefix).size > 0;
    const applyEffectiveness = (pokemon: PokemonView, owned: boolean): PokemonView => {
      const effective = abilityEffectiveness(pokemon, gasPresent, pokemon.item, owned || !!pokemon.item && pokemon.item !== 'has-item');
      const clone = this.cloneWithStatusEvidence(pokemon);
      clone.ability_effectiveness = effective;
      // Existing owner field is supported by the addressed request. Opponent
      // effectiveness stays unknown if an unrevealed Shield could exempt it.
      if (owned && effective !== 'unknown') {
        clone.ability_suppressed = effective === 'suppressed' && pokemon.active;
        if (clone.ability_suppressed) clone.ability_state = 'suppressed';
      }
      return clone;
    };
    const selfActive = selfTeam.findIndex((pokemon) => pokemon.active);
    return {
      ...this.view,
      names: { ...this.view.names },
      team_size: { ...this.view.team_size },
      active: { ...this.view.active, self: selfActive < 0 ? null : selfActive },
      field: {
        weather: this.view.field.weather,
        terrain: this.view.field.terrain,
        pseudo_weather: [...this.view.field.pseudo_weather],
        side_conditions: {
          self: { ...this.view.field.side_conditions.self },
          opponent: { ...this.view.field.side_conditions.opponent },
        },
      },
      self_team: selfTeam.map((pokemon) => applyEffectiveness(pokemon, true)),
      opponent_team: this.view.opponent_team.map((pokemon) => applyEffectiveness(pokemon, false)),
    };
  }

  getRequest(): ChoiceRequestView | null {
    return this.currentRequest ? {
      ...this.currentRequest,
      side: this.currentRequest.side.map((pokemon) => ({ ...pokemon, stats: { ...pokemon.stats }, moves: [...pokemon.moves] })),
      active: this.currentRequest.active ? {
        ...this.currentRequest.active,
        moves: this.currentRequest.active.moves.map((move) => ({ ...move })),
      } : null,
      legal_actions: {
        mask: [...this.currentRequest.legal_actions.mask],
        actions: this.currentRequest.legal_actions.actions.map((action) => (action ? { ...action } : null)),
        available_indices: [...this.currentRequest.legal_actions.available_indices],
      },
    } : null;
  }

  /**
   * The last addressed side request is private restoration evidence. It never
   * appears in a public protocol prefix or becomes a pending choice by itself.
   */
  getOwnRequestData(): unknown | null {
    return this.ownRequestData ? structuredClone(this.ownRequestData) : null;
  }

  restoreOwnRequestData(rawRequest: unknown): void {
    this.ownRequestData = structuredClone(rawRequest);
  }

  private consumeLine(line: string): void {
    if (!line.startsWith('|')) {
      return;
    }

    const parts = splitProtocolLine(line);
    const command = parts[1] || '';

    switch (command) {
      case 'request':
        this.handleRequest(line.slice('|request|'.length));
        break;
      case 'player':
        this.handlePlayer(parts);
        break;
      case 'teamsize':
        this.handleTeamSize(parts);
        break;
      case 'gen':
        this.view.gen = Number.parseInt(parts[2] || '0', 10) || null;
        break;
      case 'turn':
        this.view.turn = Number.parseInt(parts[2] || '0', 10) || this.view.turn;
        break;
      case 'poke':
        this.handlePreview(parts);
        break;
      case 'switch':
      case 'drag':
        this.handleSwitch(parts);
        break;
      case 'replace':
        this.handleReplace(parts);
        break;
      case 'detailschange':
        this.handleDetailsChange(parts);
        break;
      case '-formechange':
        this.handleFormeChange(parts);
        break;
      case '-invertboost':
        this.handleInvertBoosts(parts);
        break;
      case '-copyboost':
        this.handleCopyBoosts(parts);
        break;
      case '-transform':
        this.handleTransform(parts);
        break;
      case 'move':
        this.handleMove(parts);
        break;
      case 'faint':
        this.handleFaint(parts);
        break;
      case '-damage':
      case '-heal':
      case '-sethp':
        this.handleHp(parts);
        break;
      case '-status':
      case '-curestatus':
        this.handleStatus(parts);
        break;
      case '-boost':
      case '-unboost':
      case '-setboost':
        this.handleBoost(parts);
        break;
      case '-clearboost':
      case '-clearnegativeboost':
      case '-clearpositiveboost':
        this.handleClearBoosts(parts);
        break;
      case '-clearallboost':
        this.handleClearAllBoosts();
        break;
      case '-start':
      case '-end':
        this.handleVolatile(parts);
        break;
      case '-weather':
        this.handleWeather(parts);
        break;
      case '-fieldstart':
      case '-fieldend':
        this.handlePseudoWeather(parts);
        break;
      case '-sidestart':
      case '-sideend':
        this.handleSideCondition(parts);
        break;
      case '-swapsideconditions':
        this.handleSwapSideConditions();
        break;
      case '-item':
      case '-enditem':
        this.handleItem(parts);
        break;
      case '-ability':
        this.handleAbility(parts);
        break;
      case '-endability':
        this.handleEndAbility(parts);
        break;
      case '-terastallize':
        this.handleTerastallize(parts);
        break;
      case 'win':
        this.handleWinner(parts[2] || null);
        break;
      case 'tie':
        this.handleWinner('tie');
        break;
      default:
        break;
    }
  }

  private handleRequest(rawJson: string): void {
    const rawRequest = JSON.parse(rawJson);
    this.currentRequest = normalizeRequest(this.player, rawRequest);
    if (Array.isArray(rawRequest?.side?.pokemon)) {this.ownRequestData = rawRequest; this.submittedSwitch = null;}
  }

  private selfFromRequest(rawRequest: any): PokemonView[] {
    const requestSide = Array.isArray(rawRequest?.side?.pokemon) ? rawRequest.side.pokemon : [];
    const terminalTrace = this.view.terminated ? publicTraceAbilities(this.publicAbilityPrefix) : {};
    const submitted = this.view.terminated && this.submittedSwitch
      && this.publicAbilityPrefix.slice(this.submittedSwitch.cursor).filter((line) => line.startsWith(`|switch|${this.player}a: `)).length === 1
      && !this.publicAbilityPrefix.slice(this.submittedSwitch.cursor).some((line) => line.startsWith(`|drag|${this.player}a: `))
      ? this.submittedSwitch.ident : null;
    const activeOwner = requestSide.find((pokemon: any) => submitted ? pokemon?.ident === submitted : pokemon?.active);
    const appearance = this.publicActive[this.player]?.pokemon;
    const currentAppearance = appearance && parseIdent(appearance.ident);
    const appearanceName = currentAppearance && `${currentAppearance.player}: ${currentAppearance.name}`;
    const ownedName = activeOwner && parseIdent(activeOwner.ident);
    const historyKey = `${this.publicAbilityPrefix.length}:${appearanceName}:${ownedName?.player}:${ownedName?.name}`;
    if (this.ownedItemHistoryCache?.key !== historyKey) this.ownedItemHistoryCache = {key: historyKey,
      history: projectPublicOwnedItemHistory(this.publicAbilityPrefix, this.player, (target) => target === appearanceName && ownedName ? `${ownedName.player}: ${ownedName.name}` : target, requestSide.map((row: any) => ({ability: toID(row.ability || ''), base_ability: toID(row.baseAbility || '')})))};
    const ambiguous = ambiguousOwnedItemTargets(this.publicAbilityPrefix, this.player, requestSide.map((row: any) => ({ability: toID(row.ability || ''), base_ability: toID(row.baseAbility || '')})));
    const itemHistory = this.ownedItemHistoryCache.history;
    const terminalVisibleOwner = this.view.terminated && currentAppearance && (appearance?.illusion_revealed
      || requestSide.every((pokemon: any) => pokemon?.ability && pokemon?.baseAbility && toID(pokemon.ability) !== 'illusion' && toID(pokemon.baseAbility) !== 'illusion'));

    return requestSide.map((pokemon: any, index: number) => {
      const slot = index + 1;
      // Showdown swaps party positions on switch. A request slot is not a stable
      // identity, and copying its former occupant can lose a transferred effect.
      const ident = parseIdent(pokemon?.ident || '');
      const named = this.view.self_team.find((entry) => {
        const prior = parseIdent(entry.ident);
        return ident.player === prior.player && ident.name !== '' && ident.name === prior.name;
      });
      // Only the addressed player's request can bind an unrevealed appearance
      // to a real roster member. Never apply its evidence to the bench disguise.
      const appearance = this.publicActive[this.player]?.pokemon;
      const ownedActive = submitted ? pokemon?.ident === submitted : terminalVisibleOwner ? ident.name === currentAppearance.name : !!pokemon?.active;
      const previous = ownedActive ? appearance || named
        : named && named !== appearance && (this.view.terminated || !named.displayed_species_uncertain) ? named : undefined;
      const knownHistory = itemHistory[`${ident.player}: ${ident.name}`];
      const uncertainHistory = !knownHistory && ambiguous.size > 0 && (ambiguous.has(`${ident.player}: ${ident.name}`)
        || toID(pokemon?.ability || '') === 'illusion' || toID(pokemon?.baseAbility || '') === 'illusion');
      const parsedDetails = parseDetails(pokemon?.details || '');
      const parsedCondition = parseCondition(pokemon?.condition || '');
      const restoredTrace = terminalTrace[`${ident.player}: ${ident.name}`]?.cleared;
      const replacedForm = this.view.terminated && previous && previous.base_species !== parsedDetails.species
        && !preservesOwnedAbilityForForm(previous.base_species || '', pokemon?.ability, pokemon?.baseAbility);
      const restoredAbility = this.view.terminated && (restoredTrace || previous?.fainted || pokemon?.active && previous && !previous.active);
      const terminalAbility = replacedForm ? previous?.ability || null : restoredAbility ? pokemon?.baseAbility || null : pokemon?.ability || previous?.ability || null;
      const terminalBase = replacedForm ? previous?.base_ability || null : pokemon?.baseAbility || previous?.base_ability || null;
      // A terminal battle has no following request. In that case the most
      // recent own request can still describe a live Terastallized Pokemon,
      // while the public faint record has already reset its active Tera form.
      // Keep the known Tera type as historical evidence, but let the public
      // faint state win for the live flag and displayed typing.
      const terastallized = !parsedCondition.fainted && !previous?.fainted && !!pokemon?.terastallized;
      const teraType = pokemon?.teraType || parsedDetails.teraType || previous?.tera_type || null;

      return {
        slot,
        ident: pokemon?.ident || previous?.ident || '',
        name: parseIdent(pokemon?.ident || previous?.ident || '').name || parsedDetails.species,
        species: parsedDetails.species || previous?.species || 'Unknown',
        base_species: parsedDetails.species || previous?.base_species || previous?.species || null,
        current_species: previous?.transformed
          ? previous.current_species
          : parsedDetails.species || previous?.current_species || previous?.species || null,
        displayed_species: previous && (previous.transformed || ownedActive)
          ? previous.displayed_species
          : parsedDetails.species || previous?.displayed_species || previous?.species || null,
        species_source: 'request',
        transformed: previous?.transformed || false,
        displayed_species_uncertain: false,
        illusion_revealed: previous?.illusion_revealed || false,
        details: pokemon?.details || previous?.details || '',
        active: ownedActive && !previous?.fainted,
        fainted: this.view.terminated && previous ? previous.fainted : parsedCondition.fainted || !!previous?.fainted,
        hp_text: previous?.fainted || this.view.terminated ? previous?.hp_text ?? parsedCondition.hpText : parsedCondition.hpText,
        hp_ratio: previous?.fainted || this.view.terminated ? previous?.hp_ratio ?? parsedCondition.hpRatio : parsedCondition.hpRatio,
        status: this.view.terminated && previous ? previous.status : parsedCondition.status,
        status_source: 'request',
        status_started_turn: parsedCondition.status
          ? previous?.status === parsedCondition.status ? previous.status_started_turn : this.view.turn
          : null,
        status_turns_public: null,
        gender: parsedDetails.gender,
        level: parsedDetails.level,
        item: uncertainHistory && !ownedActive ? pokemon?.item || null : this.view.terminated && previous && ['held', 'consumed', 'removed'].includes(previous.item_state) ? previous.item : pokemon?.item || previous?.item || null,
        last_item: uncertainHistory ? null : previous?.last_item || knownHistory?.last_item || null,
        item_state: uncertainHistory ? pokemon?.item ? 'held' : 'unknown' : this.view.terminated && previous && ['held', 'consumed', 'removed'].includes(previous.item_state) ? previous.item_state : pokemon?.item ? 'held' : knownHistory?.item_state || previous?.item_state || 'none',
        item_suppressed: this.view.field.pseudo_weather.includes('magicroom'),
        ability: terminalAbility,
        base_ability: terminalBase,
        ability_state: previous?.ability_suppressed
          ? 'suppressed'
          : replacedForm ? terminalAbility ? 'known' : 'unknown' : pokemon?.ability || pokemon?.baseAbility ? 'known' : previous?.ability_state || 'none',
        ability_suppressed: previous?.ability_suppressed || false,
        moves: Array.isArray(pokemon?.moves) ? [...pokemon.moves] : previous?.moves || [],
        revealed_moves: Array.isArray(pokemon?.moves)
          ? [...pokemon.moves]
          : previous?.revealed_moves || [],
        types: this.defensiveTypes(previous, parsedDetails.species || previous?.species || 'Unknown', teraType, terastallized),
        tera_type: teraType,
        terastallized,
        stats: {
          ...(previous?.stats || {}),
          ...(pokemon?.stats || {}),
        },
        boosts: previous?.boosts ? { ...previous.boosts } : {},
        volatiles: previous?.volatiles ? [...previous.volatiles] : [],
        possible_roles: previous?.possible_roles ? [...previous.possible_roles] : [],
        possible_moves: previous?.possible_moves ? [...previous.possible_moves] : [],
        possible_abilities: previous?.possible_abilities ? [...previous.possible_abilities] : [],
        possible_tera_types: previous?.possible_tera_types ? [...previous.possible_tera_types] : [],
      };
    });
  }

  private handlePlayer(parts: string[]): void {
    const side = parts[2];
    if (side !== 'p1' && side !== 'p2') {
      return;
    }
    this.view.names[side] = parts[3] || null;
  }

  private handleTeamSize(parts: string[]): void {
    const side = parts[2];
    if (side !== 'p1' && side !== 'p2') {
      return;
    }
    this.view.team_size[side] = Number.parseInt(parts[3] || '0', 10) || this.view.team_size[side];
  }

  private handlePreview(parts: string[]): void {
    const side = parts[2];
    if (side !== 'p1' && side !== 'p2') {
      return;
    }

    const team = side === this.player ? this.view.self_team : this.view.opponent_team;
    const slot = team.length + 1;
    const pokemon = createPokemonView(slot, '', parts[3] || '');
    if (parts[4] === 'item') {
      pokemon.item = 'has-item';
    }
    team.push(pokemon);
  }

  private handleSwitch(parts: string[]): void {
    const ident = parts[2] || '';
    const details = parts[3] || '';
    const condition = parts[4] || '';
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player) {
      return;
    }

    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const outgoing = this.publicActive[parsedIdent.player]?.pokemon;
    // switchIn emits the actual switch cause, including after snapshot replay.
    // copyVolatileFrom(..., 'shedtail') copies Substitute only, never boosts.
    // The pinned switchIn path emits precisely `[from] Shed Tail`.
    // Generic switch tags are retained as raw evidence, but must not create
    // typed Substitute state by resemblance to this source-specific transfer.
    const shedTail = parts[1] === 'switch' && parts.length === 6
      && parts[5] === '[from] Shed Tail';
    const transferSubstitute = shedTail && outgoing && !outgoing.fainted
      && outgoing.volatiles.includes('substitute');
    const oldLength = team.length;
    const prior = this.findOrCreatePokemon(team, ident, details, false);
    const priorIndex = team.indexOf(prior);
    const parsedDetails = parseDetails(details);
    const parsedCondition = parseCondition(condition);

    for (const member of team) {
      if (member === outgoing) this.clearSwitchState(member);
      member.active = false;
    }
    // Preserve the earlier roster entry separately in case this is its imposter.
    // A fresh appearance must not inherit that teammate's move/item evidence.
    const pokemon = createPokemonView(prior.slot, ident, details);
    if (prior.item === 'has-item') pokemon.item = 'has-item';
    // clearVolatile restores the simulator's current ability to baseAbility
    // before every switch-in. Carry only a value already revealed by prior
    // public ability evidence; preview/species/request data never supplies it.
    if (prior.base_ability) {
      pokemon.base_ability = prior.base_ability;
      pokemon.ability = prior.base_ability;
      pokemon.ability_state = 'known';
      pokemon.possible_abilities = [...prior.possible_abilities];
    }
    if (parsedDetails.species === 'Eternatus-Eternamax' && prior.volatiles.includes('dynamax')) {
      pokemon.volatiles = ['dynamax'];
    }
    team[priorIndex] = pokemon;
    if (transferSubstitute) pokemon.volatiles = upsertUnique(pokemon.volatiles, 'substitute');
    this.publicActive[parsedIdent.player] = { pokemon,
      ...(priorIndex < oldLength ? { prior: clonePokemon(prior) } : {}) };

    pokemon.ident = ident;
    pokemon.name = parsedIdent.name || parsedDetails.species;
    pokemon.species = parsedDetails.species;
    pokemon.base_species = parsedDetails.species || pokemon.base_species;
    pokemon.current_species = parsedDetails.species || pokemon.current_species;
    pokemon.displayed_species = parsedDetails.species || pokemon.displayed_species;
    pokemon.species_source = 'protocol';
    pokemon.transformed = false;
    pokemon.displayed_species_uncertain = true;
    pokemon.illusion_revealed = false;
    pokemon.details = details;
    pokemon.active = true;
    pokemon.fainted = parsedCondition.fainted;
    pokemon.hp_text = parsedCondition.hpText;
    pokemon.hp_ratio = parsedCondition.hpRatio;
    pokemon.status = parsedCondition.status;
    pokemon.status_source = 'protocol';
    pokemon.status_started_turn = parsedCondition.status ? this.view.turn : null;
    pokemon.gender = parsedDetails.gender;
    pokemon.level = parsedDetails.level;
    // getFullDetails() publishes `tera:TYPE` only while the current appearance
    // is Terastallized. This is public state of that appearance, including an
    // Illusion display, and must not be inferred from the displaced roster entry.
    pokemon.tera_type = parsedDetails.teraType || pokemon.tera_type;
    pokemon.terastallized = !!parsedDetails.teraType;
    pokemon.types = resolveTypes(pokemon.species, pokemon.tera_type, pokemon.terastallized);
    pokemon.item_suppressed = this.view.field.pseudo_weather.includes('magicroom');
    this.updateActiveIndices();
  }

  private clearSwitchState(pokemon: PokemonView): void {
    // clearVolatile calls setSpecies(baseSpecies), resetting ordinary types while
    // preserving active Tera until faintMessages explicitly removes that flag.
    if (pokemon.transformed) {
      // Transform changes the appearance, not the original roster species.
      pokemon.species = pokemon.base_species || pokemon.species;
      pokemon.current_species = pokemon.species;
      pokemon.displayed_species = pokemon.species;
      pokemon.transformed = false;
    }
    const hadReplacement = this.publicTypeChanges.delete(pokemon);
    const hadAdded = this.publicAddedTypes.delete(pokemon);
    if (hadReplacement || hadAdded) {
      pokemon.types = resolveTypes(pokemon.species, pokemon.tera_type, pokemon.terastallized);
    }
    pokemon.boosts = {};
    // Pinned Pokemon.clearVolatile restores the live ability to baseAbility on
    // switch and faint. Restore only an already public base value; an
    // unrevealed base remains unknown rather than being derived from species,
    // set, request, or simulator state.
    if (pokemon.base_ability) {
      pokemon.ability = pokemon.base_ability;
      pokemon.ability_state = 'known';
    } else {
      pokemon.ability = null;
      pokemon.ability_state = 'unknown';
    }
    pokemon.ability_suppressed = false;
    // Pinned Pokemon.clearVolatile retains only Eternamax's Dynamax. Do not
    // erase permanent status, item/reveal evidence, or other nonvolatile fields.
    pokemon.volatiles = pokemon.volatiles.filter((effect) =>
      effect === 'dynamax' && pokemon.current_species === 'Eternatus-Eternamax');
  }

  private handleDetailsChange(parts: string[]): void {
    const ident = parts[2] || '';
    const details = parts[3] || '';
    const condition = parts[4] || '';
    const team = parseIdent(ident).player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, details);
    const parsedDetails = parseDetails(details);
    const parsedCondition = parseCondition(condition);

    pokemon.ident = ident || pokemon.ident;
    pokemon.name = parseIdent(ident).name || pokemon.name;
    const speciesChanged = !!parsedDetails.species && parsedDetails.species !== pokemon.current_species;
    pokemon.species = parsedDetails.species || pokemon.species;
    pokemon.base_species = parsedDetails.species || pokemon.base_species;
    pokemon.current_species = parsedDetails.species || pokemon.current_species;
    pokemon.displayed_species = parsedDetails.species || pokemon.displayed_species;
    pokemon.species_source = 'protocol';
    pokemon.details = details || pokemon.details;
    pokemon.level = parsedDetails.level ?? pokemon.level;
    pokemon.gender = parsedDetails.gender ?? pokemon.gender;
    if (parts.length > 4) {
      pokemon.hp_text = parsedCondition.hpText ?? pokemon.hp_text;
      pokemon.hp_ratio = parsedCondition.hpRatio ?? pokemon.hp_ratio;
      // A condition-bearing public record includes the current major status
      // when one exists. Its absence is therefore positive clear evidence,
      // unlike an omitted condition field on the record itself.
      if (pokemon.status !== parsedCondition.status) {
        pokemon.status_started_turn = parsedCondition.status ? this.view.turn : null;
      }
      pokemon.status = parsedCondition.status;
      pokemon.status_source = 'protocol';
      pokemon.fainted = parsedCondition.fainted;
    }
    pokemon.tera_type = parsedDetails.teraType || pokemon.tera_type;
    if (speciesChanged && !preservesOwnedAbilityForForm(details, pokemon.ability, pokemon.base_ability)) {
      // A form record is not ability evidence. Pinned formeChange can replace
      // the live ability silently, so retain no earlier current value across a
      // changed public identity until a later public ability record confirms it.
      pokemon.ability = null;
      pokemon.base_ability = null;
      pokemon.ability_state = 'unknown';
      pokemon.ability_suppressed = false;
    }
    this.publicTypeChanges.delete(pokemon);
    this.publicAddedTypes.delete(pokemon);
    pokemon.types = resolveTypes(pokemon.species, pokemon.tera_type, pokemon.terastallized);
  }

  private handleReplace(parts: string[]): void {
    const ident = parts[2] || '';
    const details = parts[3] || '';
    const team = parseIdent(ident).player === this.player ? this.view.self_team : this.view.opponent_team;
    const player = parseIdent(ident).player;
    const appearance = player ? this.publicActive[player] : undefined;
    const pokemon = appearance?.pokemon || this.findOrCreatePokemon(team, ident, details);
    const index = team.indexOf(pokemon);
    const confirmed = team.find((entry) => entry !== pokemon && parseIdent(entry.ident).name === parseIdent(ident).name);
    if (appearance?.prior && parseIdent(appearance.prior.ident).name !== parseIdent(ident).name) {
      team[index] = appearance.prior;
      if (!confirmed) { pokemon.slot = team.length + 1; team.push(pokemon); }
    } else if (confirmed) {
      team.splice(index, 1);
    }
    if (confirmed) {
      pokemon.slot = confirmed.slot;
      pokemon.revealed_moves = [...new Set([...confirmed.revealed_moves, ...pokemon.revealed_moves])];
      pokemon.item ??= confirmed.item;
      pokemon.ability ??= confirmed.ability;
      team[team.indexOf(confirmed)] = pokemon;
    }
    const displayed = pokemon.displayed_species || pokemon.current_species || pokemon.species;
    const parsedDetails = parseDetails(details);
    const parsedCondition = parseCondition(parts[4] || '');
    pokemon.ident = ident || pokemon.ident;
    pokemon.name = parseIdent(ident).name || pokemon.name;
    pokemon.species = parsedDetails.species || pokemon.species;
    pokemon.details = details || pokemon.details;
    pokemon.hp_text = parsedCondition.hpText ?? pokemon.hp_text;
    pokemon.hp_ratio = parsedCondition.hpRatio ?? pokemon.hp_ratio;
    // `getHealth()` includes the current major status in every emitted HP
    // condition. Do not preserve an earlier status when this public condition
    // has none: that would turn a known clear into stale typed state.
    if (pokemon.status !== parsedCondition.status) {
      pokemon.status_started_turn = parsedCondition.status ? this.view.turn : null;
      pokemon.status_turns_public = null;
    }
    pokemon.status = parsedCondition.status;
    pokemon.status_source = 'protocol';
    pokemon.base_species = pokemon.species;
    pokemon.current_species = pokemon.species;
    pokemon.displayed_species = displayed;
    pokemon.species_source = 'protocol';
    pokemon.transformed = false;
    pokemon.displayed_species_uncertain = false;
    pokemon.illusion_revealed = true;
    pokemon.types = this.defensiveTypes(pokemon, pokemon.species, pokemon.tera_type, pokemon.terastallized);
    if (player) this.publicActive[player] = { pokemon };
    this.updateActiveIndices();
  }

  private handleFormeChange(parts: string[]): void {
    const ident = parts[2] || '';
    const species = parts[3] || '';
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player || !species) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, species);
    pokemon.species = species;
    pokemon.current_species = species;
    pokemon.displayed_species = species;
    pokemon.species_source = 'protocol';
    // The source form record precedes (and may have no) public ability
    // confirmation. Do not project the prior form's ability into this form.
    pokemon.ability = null;
    pokemon.base_ability = null;
    pokemon.ability_state = 'unknown';
    pokemon.ability_suppressed = false;
    this.publicTypeChanges.delete(pokemon);
    this.publicAddedTypes.delete(pokemon);
    pokemon.types = resolveTypes(species, pokemon.tera_type, pokemon.terastallized);
  }

  private handleInvertBoosts(parts: string[]): void {
    if (parts.length !== 4 || parts[3] !== '[from] move: Topsy-Turvy'
      || !isCanonicalPlayerIdent(parts[2], true)) return;
    const player = parseIdent(parts[2]).player;
    if (!player) return;
    const team = player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, parts[2], '');
    pokemon.boosts = Object.fromEntries(Object.entries(pokemon.boosts).map(([stat, value]) =>
      [stat, value === 0 ? 0 : -value]));
  }

  private handleCopyBoosts(parts: string[]): void {
    if (parts.length !== 5 || parts[4] !== '[from] move: Psych Up') return;
    if (!isCanonicalPlayerIdent(parts[2], true) || !isCanonicalPlayerIdent(parts[3], true)) return;
    const recipientIdent = parseIdent(parts[2]);
    const donorIdent = parseIdent(parts[3]);
    if (!recipientIdent.player || !donorIdent.player) return;
    const recipientTeam = recipientIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const donorTeam = donorIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const recipient = this.findOrCreatePokemon(recipientTeam, parts[2], '');
    const donor = donorTeam.find(p => p.active) || donorTeam.find(p => p.ident === parts[3]);
    // First protocol identifier receives the second's public stages at this instant.
    // Replace, never merge; absent sparse evidence stays absent (v2 tracks null).
    recipient.boosts = { ...donor?.boosts };
  }

  private handleTransform(parts: string[]): void {
    const ident = parts[2] || '';
    const targetIdent = parts[3] || '';
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const targetParsed = parseIdent(targetIdent);
    const targetTeam = targetParsed.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');
    const target = targetTeam.find((entry) => entry.active) || targetTeam.find((entry) => entry.ident === targetIdent);
    const currentSpecies = target?.current_species || target?.species || targetParsed.name || null;
    if (!currentSpecies) {
      return;
    }
    pokemon.current_species = currentSpecies;
    pokemon.displayed_species = currentSpecies;
    pokemon.species = currentSpecies;
    pokemon.species_source = 'protocol';
    pokemon.transformed = true;
    // transformInto silently installs the target's current ability after the
    // public -transform record. That target value can be hidden, so the
    // transform event cannot retain the caller's prior ability as live truth.
    // Keep the caller's independently revealed base ability for a later
    // clearVolatile restoration, but make its transformed current ability
    // unknown until a public ability record establishes it.
    pokemon.ability = null;
    pokemon.ability_state = 'unknown';
    pokemon.ability_suppressed = false;
    // Transform assigns every stage, rather than applying boost deltas. A fresh
    // public map also removes stale caller stages (absent entries mean zero).
    pokemon.boosts = { ...target?.boosts };
    // Transform copies ordinary types (ignoring target Tera) and the added slot
    // at this instant. Copy only public evidence and never alias either map.
    const ordinary = target && this.publicTypeChanges.get(target);
    this.publicTypeChanges.set(pokemon, ordinary ? [...ordinary] : resolveTypes(currentSpecies, null, false));
    const added = target && this.publicAddedTypes.get(target);
    if (added) this.publicAddedTypes.set(pokemon, added);
    else this.publicAddedTypes.delete(pokemon);
    pokemon.types = this.defensiveTypes(pokemon, currentSpecies, pokemon.tera_type, pokemon.terastallized);
  }

  private handleMove(parts: string[]): void {
    const ident = parts[2] || '';
    const move = parts[3] || '';
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');
    pokemon.revealed_moves = upsertUnique(pokemon.revealed_moves, parsedIdent.player === this.player ? toID(move) : move);
    pokemon.possible_moves = upsertUnique(pokemon.possible_moves, move);
    if (parsedIdent.player === this.player && !pokemon.moves.includes(toID(move))) {
      pokemon.moves.push(toID(move));
    }
  }

  private handleFaint(parts: string[]): void {
    const ident = parts[2] || '';
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');
    this.clearSwitchState(pokemon);
    // Battle.faintMessages clears volatile state and then deletes
    // `terastallized`; the configured teraType remains known. Resolve the
    // displayed base types only after clearing the public active-Tera flag.
    // For an unrevealed Illusion this intentionally uses the appearance, not
    // the hidden roster identity.
    pokemon.terastallized = false;
    pokemon.types = resolveTypes(pokemon.species, pokemon.tera_type, false);
    pokemon.fainted = true;
    pokemon.active = false;
    pokemon.hp_ratio = 0;
    pokemon.hp_text = '0';
    // `Battle.checkFainted` replaces the internal status with `fnt`; no major
    // status survives a public faint boundary.
    pokemon.status = null;
    pokemon.status_source = 'protocol';
    pokemon.status_started_turn = null;
    pokemon.status_turns_public = null;
    this.updateActiveIndices();
  }

  private handleHp(parts: string[]): void {
    const ident = parts[2] || '';
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player) {
      return;
    }
    const condition = parts[3] || '';
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');
    const parsedCondition = parseCondition(condition);
    pokemon.hp_text = parsedCondition.hpText;
    pokemon.hp_ratio = parsedCondition.hpRatio;
    // `getHealth()` includes the current major status for a live Pokémon. A
    // statusless live condition is public clear evidence. `0 fnt` instead
    // precedes the separate public `faint` record, which closes the status
    // lifecycle without prematurely clearing it here.
    if (!parsedCondition.fainted) {
      if (pokemon.status !== parsedCondition.status) {
        pokemon.status_started_turn = parsedCondition.status ? this.view.turn : null;
        pokemon.status_turns_public = null;
      }
      pokemon.status = parsedCondition.status;
      pokemon.status_source = 'protocol';
    }
    const isRevivalBlessing = parts[1] === '-heal' && parts.includes('[from] move: Revival Blessing');
    const isHealingWish = parts[1] === '-heal' && parts.length === 5
      && parts[4] === '[from] move: Healing Wish';
    if (isRevivalBlessing && /^p[12]: /.test(ident)) {
      // The pinned bench heal names the actual revived roster member. It closes
      // the earlier appearance uncertainty so requestless terminal extraction
      // retains this public revival rather than its stale fainted request.
      pokemon.displayed_species_uncertain = false;
    }
    if (isRevivalBlessing || isHealingWish) {
      // Pinned emitters clear status before their exact public -heal record.
      // Healing Wish is active-target only; Revival Blessing stays separately
      // bounded to its existing bench-selection protocol.
      pokemon.status = parsedCondition.status;
      pokemon.status_source = 'protocol';
      pokemon.status_started_turn = null;
      pokemon.status_turns_public = null;
    }
    pokemon.fainted = parsedCondition.fainted;
  }

  private handleStatus(parts: string[]): void {
    const ident = parts[2] || '';
    const status = parts[3] || '';
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');
    if (parts[1] === '-curestatus') {
      pokemon.status = null;
      pokemon.status_started_turn = null;
    } else {
      pokemon.status = status || null;
      pokemon.status_started_turn = status ? this.view.turn : null;
    }
    pokemon.status_source = 'protocol';
  }

  private handleBoost(parts: string[]): void {
    const ident = parts[2] || '';
    const stat = normalizeEffectId(parts[3] || '');
    const amount = Number.parseInt(parts[4] || '0', 10) || 0;
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player || !stat) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');
    const current = pokemon.boosts[stat] || 0;
    if (parts[1] === '-unboost') {
      pokemon.boosts[stat] = current - amount;
    } else if (parts[1] === '-setboost') {
      pokemon.boosts[stat] = amount;
    } else {
      pokemon.boosts[stat] = current + amount;
    }
  }

  private handleClearBoosts(parts: string[]): void {
    const ident = parts[2] || '';
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');
    if (parts[1] === '-clearboost') {
      pokemon.boosts = {};
    } else {
      const positive = parts[1] === '-clearpositiveboost';
      pokemon.boosts = Object.fromEntries(Object.entries(pokemon.boosts).map(([stat, stage]) =>
        [stat, (positive ? stage > 0 : stage < 0) ? 0 : stage]));
    }
  }

  private handleClearAllBoosts(): void {
    for (const team of [this.view.self_team, this.view.opponent_team]) {
      for (const pokemon of team) {
        pokemon.boosts = {};
      }
    }
  }

  private handleVolatile(parts: string[]): void {
    const ident = parts[2] || '';
    if (classifyEffectRecord(parts[1] || '', parts[3] || '') === 'raw-only') return;
    const effect = normalizeEffectId(parts[3] || '');
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player || !effect) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');

    if (effect === 'typechange' || effect === 'typeadd') {
      if (parts[1] === '-end') {
        if (effect === 'typechange') this.publicTypeChanges.delete(pokemon);
        this.publicAddedTypes.delete(pokemon);
      } else if (effect === 'typechange') {
        const changedTypes = (parts[4] || '').split('/').map(value => value.trim()).filter(Boolean);
        this.publicTypeChanges.set(pokemon, changedTypes.slice(0, 2));
        // Pokemon.setType replaces ordinary types and removes any added type.
        this.publicAddedTypes.delete(pokemon);
      } else {
        // Pokemon.addType has one replaceable slot, not an accumulating list.
        const added = (parts[4] || '').trim();
        if (added) this.publicAddedTypes.set(pokemon, added);
      }
      pokemon.types = this.defensiveTypes(pokemon, pokemon.species, pokemon.tera_type, pokemon.terastallized);
      return;
    }

    if (parts[1] === '-end') {
      pokemon.volatiles = pokemon.volatiles.filter((volatile) => volatile !== effect);
    } else {
      pokemon.volatiles = upsertUnique(pokemon.volatiles, effect);
    }
  }

  private handleWeather(parts: string[]): void {
    if (classifyEffectRecord(parts[1] || '', parts[2] || '') === 'raw-only') return;
    const weather = normalizeEffectId(parts[2] || '');
    this.view.field.weather = weather || null;
  }

  private handlePseudoWeather(parts: string[]): void {
    if (classifyEffectRecord(parts[1] || '', parts[2] || '') === 'raw-only') return;
    const effect = normalizeEffectId(parts[2] || '');
    if (!effect) {
      return;
    }

    if (parts[1] === '-fieldend') {
      this.view.field.pseudo_weather = this.view.field.pseudo_weather.filter((entry) => entry !== effect);
    } else {
      this.view.field.pseudo_weather = upsertUnique(this.view.field.pseudo_weather, effect);
      if (effect === 'electricterrain' || effect === 'grassyterrain' || effect === 'mistyterrain' || effect === 'psychicterrain') {
        this.view.field.terrain = effect;
      }
    }

    if (parts[1] === '-fieldend' && this.view.field.terrain === effect) {
      this.view.field.terrain = null;
    }
    if (effect === 'magicroom') {
      const suppressed = parts[1] !== '-fieldend';
      for (const team of [this.view.self_team, this.view.opponent_team]) {
        for (const pokemon of team) {
          pokemon.item_suppressed = suppressed;
        }
      }
    }
  }

  private handleSideCondition(parts: string[]): void {
    const side = (parts[2] || '').split(':', 1)[0];
    if (classifyEffectRecord(parts[1] || '', parts[3] || '') === 'raw-only') return;
    const effect = normalizeEffectId(parts[3] || '');
    if ((side !== 'p1' && side !== 'p2') || !effect) {
      return;
    }

    const target = side === this.player ? this.view.field.side_conditions.self : this.view.field.side_conditions.opponent;
    const lifecycle = typedStateLifecycleEntry('side_condition', effect);
    if (!lifecycle || lifecycle.disposition !== 'evidence-derived-typed') return;
    if (parts[1] === '-sideend') {
      delete target[effect];
    } else {
      const next = (target[effect] || 0) + 1;
      if (next > (lifecycle.cap || 1)) {
        throw new ObservableStateError(`Malformed raw -sidestart record: ${effect} exceeds its pinned layer cap.`);
      }
      if (lifecycle.mode !== 'count' && next > 1) {
        throw new ObservableStateError(`Malformed raw -sidestart record: duplicate ${effect} presence start.`);
      }
      target[effect] = lifecycle.mode === 'count' ? next : 1;
    }
  }

  private handleSwapSideConditions(): void {
    // Court Change moves a finite source list, not every public map entry.
    // Preserve the exact existing count (hazards) or presence value (screens)
    // and leave all non-Court field data where it was.
    const self = this.view.field.side_conditions.self;
    const opponent = this.view.field.side_conditions.opponent;
    for (const effect of PUBLIC_TYPED_STATE_LIFECYCLE.court_change_ids) {
      const selfValue = self[effect];
      const opponentValue = opponent[effect];
      if (opponentValue === undefined) delete self[effect]; else self[effect] = opponentValue;
      if (selfValue === undefined) delete opponent[effect]; else opponent[effect] = selfValue;
    }
  }

  private handleItem(parts: string[]): void {
    const ident = parts[2] || '';
    const item = normalizeEffectId(parts[3] || '');
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');
    if (parts[1] === '-enditem') {
      const tags = parts.slice(4).map((value) => value.toLowerCase());
      // Air Balloon pops directly in data/items.ts and is therefore removed.
      // The other finite tagless forms are non-Gem Pokemon.useItem() roots and
      // consume the public item. No source or callback state is projected.
      const consumed = tags.some((value) => value.includes('[eat]') || value.includes('[from] gem'))
        || (tags.length === 0 && item !== 'airballoon');
      pokemon.last_item = item || pokemon.item;
      pokemon.item = null;
      pokemon.item_state = consumed ? 'consumed' : 'removed';
    } else {
      pokemon.item = item || pokemon.item;
      pokemon.item_state = 'held';
    }
  }

  private handleAbility(parts: string[]): void {
    const ident = parts[2] || '';
    const ability = normalizeEffectId(parts[3] || '');
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');
    const changed = parts.slice(4).some((value) => value.toLowerCase().startsWith('[from]'));
    if (!pokemon.base_ability && !changed) {
      pokemon.base_ability = publicRevealedAbilities(this.publicAbilityPrefix)[ident.replace(/^(p[12])a: /, '$1: ')]?.base || null;
    }
    pokemon.ability = ability || pokemon.ability;
    pokemon.ability_state = changed ? 'changed' : 'known';
    pokemon.ability_suppressed = false;
    pokemon.possible_abilities = upsertUnique(pokemon.possible_abilities, ability);
  }

  private handleEndAbility(parts: string[]): void {
    const ident = parts[2] || '';
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');
    if (parts.length === 5) {
      // A move-source record says the old ability ended during a change; the
      // target-only form below is the supported public suppression signal.
      pokemon.ability = null;
      pokemon.ability_state = 'unknown';
      pokemon.ability_suppressed = false;
      return;
    }
    pokemon.ability_state = 'suppressed';
    pokemon.ability_suppressed = true;
  }

  private handleTerastallize(parts: string[]): void {
    const ident = parts[2] || '';
    const teraType = parts[3] || null;
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');
    // Terastallization clears addedType even when Stellar keeps ordinary types.
    this.publicAddedTypes.delete(pokemon);
    pokemon.terastallized = true;
    pokemon.tera_type = teraType;
    pokemon.types = this.defensiveTypes(pokemon, pokemon.species, teraType, true);
  }

  private handleWinner(name: string | null): void {
    const winner = this.resolveWinner(name);
    this.view.terminated = true;
    this.view.winner = winner;
  }

  private resolveWinner(name: string | null): Winner {
    if (name === 'tie') {
      return 'tie';
    }
    if (name && this.view.names.p1 === name) {
      return 'p1';
    }
    if (name && this.view.names.p2 === name) {
      return 'p2';
    }
    return null;
  }

  private findOrCreatePokemon(team: PokemonView[], ident: string, details: string, usePosition = true): PokemonView {
    const parsedIdent = parseIdent(ident);
    const parsedDetails = parseDetails(details);
    if (usePosition && parsedIdent.player && /^p[12][a-f]:/.test(ident)) {
      const appearance = this.publicActive[parsedIdent.player];
      if (appearance) return appearance.pokemon;
    }

    let found = team.find((pokemon) => ident && pokemon.ident === ident);
    if (found) {
      return found;
    }

    found = team.find((pokemon) => {
      const existing = parseIdent(pokemon.ident);
      return (
        parsedIdent.player !== null &&
        existing.player === parsedIdent.player &&
        parsedIdent.name !== '' &&
        existing.name === parsedIdent.name
      );
    });
    if (found) {
      return found;
    }

    found = team.find((pokemon) => (
      parsedDetails.species &&
      pokemon.species === parsedDetails.species &&
      (!pokemon.ident || pokemon.name === parsedIdent.name)
    ));
    if (found) {
      return found;
    }

    const pokemon = createPokemonView(team.length + 1, ident, details);
    const speciesData = Dex.species.get(pokemon.species);
    if (speciesData.exists) {
      pokemon.types = [...speciesData.types];
    }
    team.push(pokemon);
    return pokemon;
  }

  private updateActiveIndices(): void {
    const selfIndex = this.view.self_team.findIndex((pokemon) => pokemon.active);
    const opponentIndex = this.view.opponent_team.findIndex((pokemon) => pokemon.active);
    this.view.active.self = selfIndex >= 0 ? selfIndex : null;
    this.view.active.opponent = opponentIndex >= 0 ? opponentIndex : null;
  }

  private cloneWithStatusEvidence(pokemon: PokemonView): PokemonView {
    const cloned = clonePokemon(pokemon);
    cloned.status_turns_public = (
      cloned.status && cloned.status_started_turn !== null
        ? Math.max(0, this.view.turn - cloned.status_started_turn)
        : null
    );
    return cloned;
  }
}
