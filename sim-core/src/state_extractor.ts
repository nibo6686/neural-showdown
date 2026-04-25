import { Dex, toID } from 'pokemon-showdown';
import { normalizeRequest } from './action_codec';
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

function createPokemonView(slot: number, ident = '', details = ''): PokemonView {
  const parsedDetails = parseDetails(details);
  const parsedCondition = parseCondition('');

  return {
    slot,
    ident,
    name: parseIdent(ident).name || parsedDetails.species,
    species: parsedDetails.species,
    details,
    active: false,
    fainted: parsedCondition.fainted,
    hp_text: parsedCondition.hpText,
    hp_ratio: parsedCondition.hpRatio,
    status: parsedCondition.status,
    gender: parsedDetails.gender,
    level: parsedDetails.level,
    item: null,
    ability: null,
    base_ability: null,
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

  constructor(envId: string, format: string, player: PlayerID) {
    this.envId = envId;
    this.player = player;
    this.opponent = player === 'p1' ? 'p2' : 'p1';
    this.format = format;
    this.view = createEmptyBattleView(envId, format, player);
    this.currentRequest = null;
  }

  consumeChunk(chunk: string): void {
    for (const rawLine of chunk.split('\n')) {
      const line = rawLine.trim();
      if (!line) {
        continue;
      }
      this.consumeLine(line);
    }
  }

  getView(): BattleView {
    return {
      ...this.view,
      names: { ...this.view.names },
      team_size: { ...this.view.team_size },
      active: { ...this.view.active },
      field: {
        weather: this.view.field.weather,
        terrain: this.view.field.terrain,
        pseudo_weather: [...this.view.field.pseudo_weather],
        side_conditions: {
          self: { ...this.view.field.side_conditions.self },
          opponent: { ...this.view.field.side_conditions.opponent },
        },
      },
      self_team: this.view.self_team.map((pokemon) => clonePokemon(pokemon)),
      opponent_team: this.view.opponent_team.map((pokemon) => clonePokemon(pokemon)),
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
      case 'detailschange':
        this.handleDetailsChange(parts);
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
    this.syncSelfFromRequest(rawRequest);
  }

  private syncSelfFromRequest(rawRequest: any): void {
    const requestSide = Array.isArray(rawRequest?.side?.pokemon) ? rawRequest.side.pokemon : [];
    const previousBySlot = new Map<number, PokemonView>(this.view.self_team.map((pokemon) => [pokemon.slot, pokemon]));

    this.view.self_team = requestSide.map((pokemon: any, index: number) => {
      const slot = index + 1;
      const previous = previousBySlot.get(slot);
      const parsedDetails = parseDetails(pokemon?.details || '');
      const parsedCondition = parseCondition(pokemon?.condition || '');
      const terastallized = !!pokemon?.terastallized;
      const teraType = pokemon?.teraType || parsedDetails.teraType || previous?.tera_type || null;

      return {
        slot,
        ident: pokemon?.ident || previous?.ident || '',
        name: parseIdent(pokemon?.ident || previous?.ident || '').name || parsedDetails.species,
        species: parsedDetails.species || previous?.species || 'Unknown',
        details: pokemon?.details || previous?.details || '',
        active: !!pokemon?.active,
        fainted: parsedCondition.fainted,
        hp_text: parsedCondition.hpText,
        hp_ratio: parsedCondition.hpRatio,
        status: parsedCondition.status,
        gender: parsedDetails.gender,
        level: parsedDetails.level,
        item: pokemon?.item || previous?.item || null,
        ability: pokemon?.ability || previous?.ability || null,
        base_ability: pokemon?.baseAbility || previous?.base_ability || null,
        moves: Array.isArray(pokemon?.moves) ? [...pokemon.moves] : previous?.moves || [],
        revealed_moves: Array.isArray(pokemon?.moves)
          ? [...pokemon.moves]
          : previous?.revealed_moves || [],
        types: resolveTypes(parsedDetails.species || previous?.species || 'Unknown', teraType, terastallized),
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

    this.updateActiveIndices();
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
    const pokemon = this.findOrCreatePokemon(team, ident, details);
    const parsedDetails = parseDetails(details);
    const parsedCondition = parseCondition(condition);

    for (const member of team) {
      member.active = false;
    }

    pokemon.ident = ident;
    pokemon.name = parsedIdent.name || parsedDetails.species;
    pokemon.species = parsedDetails.species;
    pokemon.details = details;
    pokemon.active = true;
    pokemon.fainted = parsedCondition.fainted;
    pokemon.hp_text = parsedCondition.hpText;
    pokemon.hp_ratio = parsedCondition.hpRatio;
    pokemon.status = parsedCondition.status;
    pokemon.gender = parsedDetails.gender;
    pokemon.level = parsedDetails.level;
    pokemon.tera_type = parsedDetails.teraType || pokemon.tera_type;
    pokemon.types = resolveTypes(pokemon.species, pokemon.tera_type, pokemon.terastallized);
    this.updateActiveIndices();
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
    pokemon.species = parsedDetails.species || pokemon.species;
    pokemon.details = details || pokemon.details;
    pokemon.level = parsedDetails.level ?? pokemon.level;
    pokemon.gender = parsedDetails.gender ?? pokemon.gender;
    pokemon.hp_text = parsedCondition.hpText ?? pokemon.hp_text;
    pokemon.hp_ratio = parsedCondition.hpRatio ?? pokemon.hp_ratio;
    pokemon.status = parsedCondition.status ?? pokemon.status;
    pokemon.fainted = parsedCondition.fainted;
    pokemon.tera_type = parsedDetails.teraType || pokemon.tera_type;
    pokemon.types = resolveTypes(pokemon.species, pokemon.tera_type, pokemon.terastallized);
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
    pokemon.revealed_moves = upsertUnique(pokemon.revealed_moves, move);
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
    pokemon.fainted = true;
    pokemon.active = false;
    pokemon.hp_ratio = 0;
    pokemon.hp_text = '0';
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
    pokemon.status = parsedCondition.status ?? pokemon.status;
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
    } else {
      pokemon.status = status || null;
    }
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
    pokemon.boosts = {};
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
    const effect = normalizeEffectId(parts[3] || '');
    const parsedIdent = parseIdent(ident);
    if (!parsedIdent.player || !effect) {
      return;
    }
    const team = parsedIdent.player === this.player ? this.view.self_team : this.view.opponent_team;
    const pokemon = this.findOrCreatePokemon(team, ident, '');

    if (parts[1] === '-end') {
      pokemon.volatiles = pokemon.volatiles.filter((volatile) => volatile !== effect);
    } else {
      pokemon.volatiles = upsertUnique(pokemon.volatiles, effect);
    }
  }

  private handleWeather(parts: string[]): void {
    const weather = normalizeEffectId(parts[2] || '');
    this.view.field.weather = weather || null;
  }

  private handlePseudoWeather(parts: string[]): void {
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
  }

  private handleSideCondition(parts: string[]): void {
    const side = parts[2];
    const effect = normalizeEffectId(parts[3] || '');
    if ((side !== 'p1' && side !== 'p2') || !effect) {
      return;
    }

    const target = side === this.player ? this.view.field.side_conditions.self : this.view.field.side_conditions.opponent;
    if (parts[1] === '-sideend') {
      delete target[effect];
    } else {
      target[effect] = (target[effect] || 0) + 1;
    }
  }

  private handleSwapSideConditions(): void {
    const currentSelf = { ...this.view.field.side_conditions.self };
    this.view.field.side_conditions.self = { ...this.view.field.side_conditions.opponent };
    this.view.field.side_conditions.opponent = currentSelf;
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
    pokemon.item = parts[1] === '-enditem' ? null : item || pokemon.item;
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
    pokemon.ability = ability || pokemon.ability;
    pokemon.possible_abilities = upsertUnique(pokemon.possible_abilities, ability);
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
    pokemon.terastallized = true;
    pokemon.tera_type = teraType;
    pokemon.types = resolveTypes(pokemon.species, teraType, true);
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

  private findOrCreatePokemon(team: PokemonView[], ident: string, details: string): PokemonView {
    const parsedIdent = parseIdent(ident);
    const parsedDetails = parseDetails(details);

    let found = team.find((pokemon) => ident && pokemon.ident === ident);
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
}
