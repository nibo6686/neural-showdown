import { Field, Generations, Move as CalcMove, Pokemon as CalcPokemon, calculate } from '@smogon/calc';
import { Dex, toID } from 'pokemon-showdown';
import { moveTypeMultiplier } from './battle_helpers';

const gen = Generations.get(9);

export interface DamagePokemon {
  species: string;
  level?: number;
  item?: string | null;
  ability?: string | null;
  status?: string | null;
  tera_type?: string | null;
  teraType?: string | null;
  terastallized?: boolean;
  hp_fraction?: number | null;
  cur_hp?: number | null;
  max_hp?: number | null;
  stats?: Record<string, number>;
  evs?: Record<string, number>;
  ivs?: Record<string, number>;
  boosts?: Record<string, number>;
  moves?: string[];
}

export interface DamageField {
  weather?: string | null;
  terrain?: string | null;
  reflect?: boolean;
  light_screen?: boolean;
  aurora_veil?: boolean;
}

export interface DamageEstimateRequest {
  attacker: DamagePokemon;
  defender: DamagePokemon;
  move: string;
  use_tera?: boolean;
  field?: DamageField;
}

export interface DamageEstimate {
  damage_method: 'smogon_calc' | 'non_damaging_move';
  damage_rolls: number[];
  min_percent: number;
  max_percent: number;
  average_percent: number;
  ko_chance: number;
  immune: boolean;
  type_effectiveness: number | null;
  item_modifier: number;
  burn_attack_penalty: boolean;
  tera_damage_bonus: number;
  warnings: string[];
}

const STAT_KEYS = ['hp', 'atk', 'def', 'spa', 'spd', 'spe'] as const;

const BASE_SPECIES_ALIASES: Record<string, string> = {
  polteageistantique: 'Polteageist',
  sinisteaantique: 'Sinistea',
};

function calcSpecies(name?: string | null): any {
  if (!name) return undefined;
  const species = gen.species.get(toID(name));
  return species?.baseStats?.hp ? species : undefined;
}

export function canonicalSpeciesName(name: string): string {
  const original = String(name || '').trim();
  if (!original) {
    throw new Error('canonicalization_failed: empty species name');
  }

  const alias = BASE_SPECIES_ALIASES[toID(original)];
  if (alias && calcSpecies(alias)) {
    return calcSpecies(alias).name;
  }

  const exact = calcSpecies(original);
  if (exact) {
    return exact.name;
  }

  const showdownSpecies = Dex.species.get(original);
  if (showdownSpecies.exists && showdownSpecies.baseSpecies) {
    const base = calcSpecies(showdownSpecies.baseSpecies);
    if (base) {
      return base.name;
    }
  }

  const stripped = original.replace(/-(?:Totem|Starter|Original|Busted|Low-Key|Ocean|River|Marine|Archipelago|Icy-Snow|Polar|Tundra|Continental|Garden|Elegant|Meadow|Modern|Monsoon|Savanna|Sun|Jungle|Fancy|Pokeball)$/i, '');
  const strippedSpecies = calcSpecies(stripped);
  if (strippedSpecies) {
    return strippedSpecies.name;
  }

  throw new Error(
    `canonicalization_failed: unsupported species for Smogon calc original=${JSON.stringify(original)} id=${JSON.stringify(toID(original))}`
  );
}

function numbersFromDamage(damage: number | number[] | number[][]): number[] {
  if (typeof damage === 'number') {
    return [damage];
  }
  if (!Array.isArray(damage)) {
    return [];
  }
  return damage.flat(Number.POSITIVE_INFINITY).filter((value): value is number => typeof value === 'number');
}

function canonicalWeather(weather?: string | null): any {
  const id = toID(weather || '');
  if (id === 'raindance' || id === 'rain') return 'Rain';
  if (id === 'sunnyday' || id === 'sun') return 'Sun';
  if (id === 'sandstorm') return 'Sand';
  if (id === 'snow' || id === 'hail') return 'Snow';
  return undefined;
}

function canonicalTerrain(terrain?: string | null): any {
  const id = toID(terrain || '');
  if (id === 'electricterrain') return 'Electric';
  if (id === 'grassyterrain') return 'Grassy';
  if (id === 'mistyterrain') return 'Misty';
  if (id === 'psychicterrain') return 'Psychic';
  return undefined;
}

function boundedStatTable(values?: Record<string, number>): Record<string, number> | undefined {
  if (!values) return undefined;
  const result: Record<string, number> = {};
  for (const stat of STAT_KEYS) {
    const value = values[stat];
    if (value !== undefined && value !== null && Number.isFinite(Number(value))) {
      result[stat] = Number(value);
    }
  }
  return Object.keys(result).length ? result : undefined;
}

function isNonDamagingMove(moveName: string): boolean {
  const move = Dex.moves.get(moveName);
  if (move.exists && move.category === 'Status') {
    return true;
  }
  return new Set([
    'sleeppowder',
    'quiverdance',
    'toxic',
    'spikes',
    'toxicspikes',
    'stealthrock',
    'recover',
    'protect',
    'detect',
    'substitute',
    'willowisp',
    'thunderwave',
    'roost',
    'synthesis',
    'shoreup',
    'milkdrink',
    'softboiled',
    'wish',
    'calmmind',
    'swordsdance',
    'nastyplot',
    'dragondance',
    'shellsmash',
    'stickyweb',
  ]).has(toID(moveName));
}

function nonDamagingEstimate(): DamageEstimate {
  return {
    damage_method: 'non_damaging_move',
    damage_rolls: [],
    min_percent: 0,
    max_percent: 0,
    average_percent: 0,
    ko_chance: 0,
    immune: false,
    type_effectiveness: null,
    item_modifier: 1.0,
    burn_attack_penalty: false,
    tera_damage_bonus: 0,
    warnings: [],
  };
}

function damageInputSummary(request: DamageEstimateRequest, canonicalAttacker?: string, canonicalDefender?: string): string {
  return JSON.stringify({
    attacker_species: request.attacker?.species,
    defender_species: request.defender?.species,
    canonical_attacker_species: canonicalAttacker,
    canonical_defender_species: canonicalDefender,
    move: request.move,
    attacker: {
      level: request.attacker?.level,
      item: request.attacker?.item,
      ability: request.attacker?.ability,
      status: request.attacker?.status,
      tera_type: request.attacker?.tera_type || request.attacker?.teraType,
      terastallized: request.attacker?.terastallized,
      hp_fraction: request.attacker?.hp_fraction,
      cur_hp: request.attacker?.cur_hp,
      max_hp: request.attacker?.max_hp,
      stats_keys: request.attacker?.stats ? Object.keys(request.attacker.stats).sort() : [],
      evs_keys: request.attacker?.evs ? Object.keys(request.attacker.evs).sort() : [],
      ivs_keys: request.attacker?.ivs ? Object.keys(request.attacker.ivs).sort() : [],
      boosts: request.attacker?.boosts || {},
    },
    defender: {
      level: request.defender?.level,
      item: request.defender?.item,
      ability: request.defender?.ability,
      status: request.defender?.status,
      tera_type: request.defender?.tera_type || request.defender?.teraType,
      terastallized: request.defender?.terastallized,
      hp_fraction: request.defender?.hp_fraction,
      cur_hp: request.defender?.cur_hp,
      max_hp: request.defender?.max_hp,
      stats_keys: request.defender?.stats ? Object.keys(request.defender.stats).sort() : [],
      evs_keys: request.defender?.evs ? Object.keys(request.defender.evs).sort() : [],
      ivs_keys: request.defender?.ivs ? Object.keys(request.defender.ivs).sort() : [],
      boosts: request.defender?.boosts || {},
    },
    field: request.field || {},
    use_tera: Boolean(request.use_tera),
  });
}

function buildPokemon(pokemon: DamagePokemon, useTera: boolean): InstanceType<typeof CalcPokemon> {
  const teraType = useTera || pokemon.terastallized ? (pokemon.tera_type || pokemon.teraType || undefined) : undefined;
  const canonicalSpecies = canonicalSpeciesName(pokemon.species);
  const result = new CalcPokemon(gen, canonicalSpecies, {
    name: pokemon.species as any,
    level: Number(pokemon.level || 80),
    item: pokemon.item || undefined,
    ability: pokemon.ability || undefined,
    status: (pokemon.status || undefined) as any,
    teraType: teraType as any,
    evs: boundedStatTable(pokemon.evs) as any,
    ivs: boundedStatTable(pokemon.ivs) as any,
    boosts: { ...(pokemon.boosts || {}) } as any,
    moves: [...(pokemon.moves || [])],
  });
  if (pokemon.cur_hp !== undefined && pokemon.cur_hp !== null) {
    (result as any).originalCurHP = Math.max(1, Math.min(Number(pokemon.cur_hp), Number((result as any).rawStats?.hp || 1)));
  } else if (pokemon.hp_fraction !== undefined && pokemon.hp_fraction !== null) {
    (result as any).originalCurHP = Math.max(1, Math.round(Number((result as any).rawStats?.hp || 1) * Number(pokemon.hp_fraction)));
  }
  return result;
}

function buildField(field?: DamageField): InstanceType<typeof Field> {
  return new Field({
    weather: canonicalWeather(field?.weather),
    terrain: canonicalTerrain(field?.terrain),
    defenderSide: {
      isReflect: Boolean(field?.reflect),
      isLightScreen: Boolean(field?.light_screen),
      isAuroraVeil: Boolean(field?.aurora_veil),
    },
  } as any);
}

function average(values: number[]): number {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function estimateOnce(request: DamageEstimateRequest, useTera: boolean): { rolls: number[]; maxHp: number; typeEffectiveness: number } {
  const attacker = buildPokemon(request.attacker, useTera);
  const defender = buildPokemon(request.defender, Boolean(request.defender.terastallized));
  const move = new CalcMove(gen, request.move);
  const field = buildField(request.field);
  const result = calculate(gen, attacker, defender, move, field);
  const rolls = numbersFromDamage(result.damage as any);
  const defenderMaxHp = Number((defender as any).rawStats?.hp || request.defender.max_hp || request.defender.stats?.hp || 100);
  const defenderTypes = (defender.teraType && defender.teraType !== 'Stellar') ? [defender.teraType] : [...defender.types];
  return {
    rolls,
    maxHp: Math.max(1, defenderMaxHp),
    typeEffectiveness: moveTypeMultiplier(move.type, defenderTypes),
  };
}

export function estimateDamage(request: DamageEstimateRequest): DamageEstimate {
  if (isNonDamagingMove(request.move)) {
    return nonDamagingEstimate();
  }

  let canonicalAttacker: string | undefined;
  let canonicalDefender: string | undefined;
  try {
    canonicalAttacker = canonicalSpeciesName(request.attacker.species);
    canonicalDefender = canonicalSpeciesName(request.defender.species);
    const current = estimateOnce(request, Boolean(request.use_tera));
    const rolls = current.rolls;
    const maxHp = current.maxHp;
    const percents = rolls.map((roll) => (roll / maxHp) * 100);
    const defenderHp = request.defender.cur_hp !== undefined && request.defender.cur_hp !== null
      ? Number(request.defender.cur_hp)
      : Math.max(1, Math.round(maxHp * Number(request.defender.hp_fraction ?? 1)));
    const koRolls = rolls.filter((roll) => roll >= defenderHp).length;
    const withoutTera = request.use_tera ? estimateOnce(request, false) : current;
    return {
      damage_method: 'smogon_calc',
      damage_rolls: rolls,
      min_percent: percents.length ? Math.min(...percents) : 0,
      max_percent: percents.length ? Math.max(...percents) : 0,
      average_percent: average(percents),
      ko_chance: rolls.length ? koRolls / rolls.length : 0,
      immune: current.typeEffectiveness === 0 || rolls.every((roll) => roll === 0),
      type_effectiveness: current.typeEffectiveness,
      item_modifier: toID(request.attacker.item || '') === 'lifeorb' ? 1.3 : 1.0,
      burn_attack_penalty: toID(request.attacker.status || '') === 'brn' && Dex.moves.get(request.move).category === 'Physical',
      tera_damage_bonus: request.use_tera ? average(current.rolls) - average(withoutTera.rolls) : 0,
      warnings: [],
    };
  } catch (error) {
    const exception = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
    const stack = error instanceof Error && error.stack ? error.stack : exception;
    throw new Error(
      `smogon_calc_failed: attacker_species=${JSON.stringify(request.attacker?.species)} ` +
      `defender_species=${JSON.stringify(request.defender?.species)} ` +
      `canonical_attacker_species=${JSON.stringify(canonicalAttacker)} ` +
      `canonical_defender_species=${JSON.stringify(canonicalDefender)} ` +
      `move=${JSON.stringify(request.move)} exception=${JSON.stringify(exception)} ` +
      `stack=${JSON.stringify(stack)} input_summary=${damageInputSummary(request, canonicalAttacker, canonicalDefender)}`
    );
  }
}
