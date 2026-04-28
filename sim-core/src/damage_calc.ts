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
  damage_method: 'smogon_calc';
  damage_rolls: number[];
  min_percent: number;
  max_percent: number;
  average_percent: number;
  ko_chance: number;
  immune: boolean;
  type_effectiveness: number;
  item_modifier: number;
  burn_attack_penalty: boolean;
  tera_damage_bonus: number;
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

function buildPokemon(pokemon: DamagePokemon, useTera: boolean): InstanceType<typeof CalcPokemon> {
  const teraType = useTera || pokemon.terastallized ? (pokemon.tera_type || pokemon.teraType || undefined) : undefined;
  const maxHp = Math.max(1, Number(pokemon.max_hp || pokemon.stats?.hp || 100));
  const curHp = pokemon.cur_hp !== undefined && pokemon.cur_hp !== null
    ? Number(pokemon.cur_hp)
    : pokemon.hp_fraction !== undefined && pokemon.hp_fraction !== null
      ? Math.max(1, Math.round(maxHp * Number(pokemon.hp_fraction)))
      : undefined;
  const result = new CalcPokemon(gen, pokemon.species, {
    level: Number(pokemon.level || 80),
    item: pokemon.item || undefined,
    ability: pokemon.ability || undefined,
    status: (pokemon.status || undefined) as any,
    teraType: teraType as any,
    boosts: { ...(pokemon.boosts || {}) } as any,
    moves: [...(pokemon.moves || [])],
    curHP: curHp,
  });
  if (pokemon.stats) {
    (result as any).rawStats = { ...(result as any).rawStats, ...pokemon.stats };
    (result as any).stats = { ...(result as any).stats, ...pokemon.stats };
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
  };
}
