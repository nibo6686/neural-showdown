import { Dex, toID } from 'pokemon-showdown';
import type { PlayerID, PokemonView } from './types';

export function splitProtocolLine(line: string): string[] {
  return line.split('|');
}

export function parseIdent(ident: string): { player: PlayerID | null; name: string } {
  const [rawPlayer, rawName] = ident.split(':', 2);
  const player = rawPlayer?.trim()?.slice(0, 2);

  if (player !== 'p1' && player !== 'p2') {
    return { player: null, name: ident.trim() };
  }

  return {
    player,
    name: (rawName || rawPlayer || '').trim(),
  };
}

export function normalizeEffectId(effect: string): string {
  return toID((effect || '').replace(/^[^:]+:\s*/i, ''));
}

export function parseDetails(details: string): {
  species: string;
  level: number | null;
  gender: string | null;
  teraType: string | null;
} {
  const parts = details.split(',').map((part) => part.trim()).filter(Boolean);
  const species = parts[0] || 'Unknown';
  let level: number | null = null;
  let gender: string | null = null;
  let teraType: string | null = null;

  for (const part of parts.slice(1)) {
    if (/^L\d+$/i.test(part)) {
      level = Number.parseInt(part.slice(1), 10);
    } else if (part === 'M' || part === 'F') {
      gender = part;
    } else if (part.startsWith('tera:')) {
      teraType = part.split(':', 2)[1] || null;
    }
  }

  return { species, level, gender, teraType };
}

export function parseCondition(condition: string): {
  hpText: string | null;
  hpRatio: number | null;
  status: string | null;
  fainted: boolean;
} {
  const trimmed = (condition || '').trim();

  if (!trimmed) {
    return { hpText: null, hpRatio: null, status: null, fainted: false };
  }

  const pieces = trimmed.split(' ').filter(Boolean);
  const hpText = pieces[0] || null;
  const status = pieces[1] && pieces[1] !== 'fnt' ? pieces[1] : null;
  const fainted = pieces.includes('fnt') || trimmed === '0 fnt';

  if (!hpText || fainted) {
    return { hpText, hpRatio: fainted ? 0 : null, status, fainted };
  }

  if (!hpText.includes('/')) {
    return { hpText, hpRatio: null, status, fainted };
  }

  const [numText, denText] = hpText.split('/', 2);
  const num = Number.parseFloat(numText);
  const den = Number.parseFloat(denText);

  if (!Number.isFinite(num) || !Number.isFinite(den) || den <= 0) {
    return { hpText, hpRatio: null, status, fainted };
  }

  return {
    hpText,
    hpRatio: Math.max(0, Math.min(1, num / den)),
    status,
    fainted,
  };
}

export function isFainted(condition: string): boolean {
  return parseCondition(condition).fainted;
}

export function moveTypeMultiplier(moveType: string, defenderTypes: string[]): number {
  if (!moveType || !defenderTypes.length) {
    return 1;
  }

  if (!Dex.getImmunity(moveType, defenderTypes)) {
    return 0;
  }

  const stage = Dex.getEffectiveness(moveType, defenderTypes);
  return 2 ** stage;
}

export function upsertUnique(values: string[], value: string): string[] {
  if (!value) {
    return values;
  }

  return values.includes(value) ? values : [...values, value];
}

export function resolveTypes(species: string, teraType: string | null, terastallized: boolean): string[] {
  if (terastallized && teraType) {
    return [teraType];
  }

  const speciesData = Dex.species.get(species);
  return speciesData.exists ? [...speciesData.types] : [];
}

export function clonePokemon(pokemon: PokemonView): PokemonView {
  return {
    ...pokemon,
    moves: [...pokemon.moves],
    revealed_moves: [...pokemon.revealed_moves],
    types: [...pokemon.types],
    stats: { ...pokemon.stats },
    boosts: { ...pokemon.boosts },
    volatiles: [...pokemon.volatiles],
    possible_roles: [...pokemon.possible_roles],
    possible_moves: [...pokemon.possible_moves],
    possible_abilities: [...pokemon.possible_abilities],
    possible_tera_types: [...pokemon.possible_tera_types],
  };
}
