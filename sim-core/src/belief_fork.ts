import { Battle, Dex, Teams, toID } from 'pokemon-showdown';
import type { BattleView, PlayerID } from './types';

type AnyRecord = Record<string, any>;

export interface BeliefForkMetadata {
  mode: 'randbats_belief';
  belief_seed: number[];
  sampled_sets: Array<{
    species: string;
    moves: string[];
    item: string | null;
    ability: string | null;
    tera_type: string | null;
    revealed: boolean;
    candidate_attempts: number;
  }>;
  candidate_count: number;
  constrained_fields: number;
  missing_randbats_data_count: number;
  impossible_belief_states: number;
  public_info_constraint_violations: number;
}

const HIDDEN_SET_KEYS = new Set([
  'set', 'moveSlots', 'baseMoveSlots', 'baseAbility', 'ability', 'abilityState',
  'item', 'itemState', 'teraType', 'canTerastallize', 'baseStoredStats',
  'storedStats', 'speed', 'maxhp', 'baseMaxhp', 'hpType', 'hpPower',
  'baseHpType', 'baseHpPower',
]);

function seedWithOffset(seed: number[], offset: number): [number, number, number, number] {
  const base = seed.length === 4 ? seed : [1, 2, 3, 4];
  return [
    (Number(base[0]) + offset * 101) & 0xffff,
    (Number(base[1]) + offset * 211) & 0xffff,
    (Number(base[2]) + offset * 307) & 0xffff,
    (Number(base[3]) + offset * 401) & 0xffff,
  ];
}

function publicItem(value: unknown): string | null {
  const text = typeof value === 'string' ? value.trim() : '';
  return text && text !== 'has-item' ? text : null;
}

function matchesReveal(set: AnyRecord, reveal: AnyRecord): boolean {
  const moves = new Set((set.moves || []).map((move: string) => toID(move)));
  if ((reveal.revealed_moves || []).some((move: string) => !moves.has(toID(move)))) return false;
  if (reveal.ability && toID(set.ability) !== toID(reveal.ability)) return false;
  const item = publicItem(reveal.item);
  if (item && toID(set.item) !== toID(item)) return false;
  if (reveal.terastallized && reveal.tera_type && toID(set.teraType) !== toID(reveal.tera_type)) return false;
  return true;
}

function sampleRevealedSet(
  format: string,
  reveal: AnyRecord,
  seed: number[],
  offset: number,
): { set: AnyRecord; attempts: number; impossible: boolean; missing: boolean } {
  let fallback: AnyRecord | null = null;
  let sampleSpecies = reveal.species;
  const species = Dex.species.get(reveal.species);
  const probe = Teams.getGenerator(format, seedWithOffset(seed, offset * 64) as any) as any;
  if (!probe.randomSets?.[toID(sampleSpecies)] && species.baseSpecies) {
    sampleSpecies = species.baseSpecies;
  }
  if (!probe.randomSets?.[toID(sampleSpecies)]) {
    const generated = Teams.generate(format, { seed: seedWithOffset(seed, offset * 64) });
    fallback = generated.find(set => toID(set.species) === toID(sampleSpecies)) || generated[0];
    return { set: fallback, attempts: 1, impossible: true, missing: true };
  }
  for (let attempt = 0; attempt < 64; attempt++) {
    const generator = Teams.getGenerator(format, seedWithOffset(seed, offset * 64 + attempt) as any);
    const set = (generator as any).randomSet(sampleSpecies, {}, false, false);
    set.species = reveal.species;
    fallback = set;
    if (matchesReveal(set, reveal)) return { set, attempts: attempt + 1, impossible: false, missing: false };
  }
  if (!fallback) throw new Error(`Unable to sample randbats set for ${reveal.species}`);
  const revealedMoves = (reveal.revealed_moves || []).map((move: string) => Dex.moves.get(move).name);
  fallback.moves = [...new Set([...revealedMoves, ...(fallback.moves || [])])].slice(0, 4);
  if (reveal.ability) fallback.ability = reveal.ability;
  const item = publicItem(reveal.item);
  if (item) fallback.item = item;
  if (reveal.terastallized && reveal.tera_type) fallback.teraType = reveal.tera_type;
  return { set: fallback, attempts: 64, impossible: true, missing: false };
}

function originalForReveal(originalPokemon: AnyRecord[], reveal: AnyRecord): AnyRecord | null {
  const species = toID(reveal.species);
  const active = originalPokemon.find(mon => mon.isActive && toID(mon.set?.species || mon.details) === species);
  if (active) return active;
  return originalPokemon.find(mon => toID(mon.set?.species || mon.details) === species) || null;
}

function applyPublicDynamicState(donor: AnyRecord, original: AnyRecord, reveal: AnyRecord): AnyRecord {
  const result = donor;
  for (const [key, value] of Object.entries(original)) {
    if (!HIDDEN_SET_KEYS.has(key)) result[key] = value;
  }
  result.position = original.position;
  result.isActive = original.isActive;
  result.fainted = !!reveal.fainted;
  result.status = reveal.status || '';
  result.boosts = { ...(reveal.boosts || {}) };
  result.volatiles = original.volatiles;
  const ratio = typeof reveal.hp_ratio === 'number' ? reveal.hp_ratio : (reveal.fainted ? 0 : 1);
  result.hp = reveal.fainted ? 0 : Math.max(1, Math.round(result.maxhp * ratio));
  if (reveal.ability) {
    result.baseAbility = toID(reveal.ability);
    result.ability = toID(reveal.ability);
    result.set.ability = reveal.ability;
    result.abilityState = { ...result.abilityState, id: toID(reveal.ability) };
  }
  const item = publicItem(reveal.item);
  if (item) {
    result.item = toID(item);
    result.set.item = item;
    result.itemState = { ...result.itemState, id: toID(item) };
  }
  if (reveal.terastallized && reveal.tera_type) {
    result.teraType = reveal.tera_type;
    result.set.teraType = reveal.tera_type;
    result.canTerastallize = null;
  }
  return result;
}

export function buildBeliefSnapshot(
  serialized: AnyRecord,
  perspectiveView: BattleView,
  perspective: PlayerID,
  format: string,
  beliefSeed: number[],
): { snapshot: AnyRecord; metadata: BeliefForkMetadata } {
  const snapshot = structuredClone(serialized);
  const opponent: PlayerID = perspective === 'p1' ? 'p2' : 'p1';
  const opponentIndex = opponent === 'p1' ? 0 : 1;
  const side = snapshot.sides[opponentIndex];
  const originalPokemon: AnyRecord[] = side.pokemon;
  const reveals = perspectiveView.opponent_team.map(mon => ({ ...mon }));
  const sampledByPosition = new Map<number, { set: AnyRecord; reveal: AnyRecord | null; attempts: number }>();
  const usedSpecies = new Set<string>();
  let impossible = 0;
  let missingData = 0;
  let constrainedFields = 0;

  for (const [index, reveal] of reveals.entries()) {
    constrainedFields += (reveal.revealed_moves?.length || 0)
      + Number(!!reveal.ability) + Number(!!publicItem(reveal.item))
      + Number(!!(reveal.terastallized && reveal.tera_type));
    const sampled = sampleRevealedSet(format, reveal, beliefSeed, index + 1);
    impossible += Number(sampled.impossible);
    missingData += Number(sampled.missing);
    usedSpecies.add(toID(sampled.set.species));
    const original = originalForReveal(originalPokemon, reveal);
    const position = original?.position ?? [...Array(originalPokemon.length).keys()]
      .find(pos => !sampledByPosition.has(pos)) ?? index;
    sampledByPosition.set(position, { set: sampled.set, reveal, attempts: sampled.attempts });
  }

  for (let attempt = 0; sampledByPosition.size < originalPokemon.length && attempt < 128; attempt++) {
    const generated = Teams.generate(format, { seed: seedWithOffset(beliefSeed, 1000 + attempt) });
    for (const set of generated) {
      if (sampledByPosition.size >= originalPokemon.length) break;
      if (usedSpecies.has(toID(set.species))) continue;
      const position = [...Array(originalPokemon.length).keys()].find(pos => !sampledByPosition.has(pos));
      if (position === undefined) break;
      sampledByPosition.set(position, { set, reveal: null, attempts: 1 });
      usedSpecies.add(toID(set.species));
    }
  }
  if (sampledByPosition.size !== originalPokemon.length) {
    throw new Error(`Unable to fill sampled opponent team (${sampledByPosition.size}/${originalPokemon.length})`);
  }

  const sampledTeam = [...sampledByPosition.entries()]
    .sort(([a], [b]) => a - b)
    .map(([, entry]) => entry.set);
  const filler = Teams.generate(format, { seed: seedWithOffset(beliefSeed, 9000) });
  const donorOptions: AnyRecord = {
    formatid: format,
    seed: seedWithOffset(beliefSeed, 9100) as any,
    p1: { name: 'Belief-P1', team: Teams.pack((opponent === 'p1' ? sampledTeam : filler) as any) },
    p2: { name: 'Belief-P2', team: Teams.pack((opponent === 'p2' ? sampledTeam : filler) as any) },
  };
  const donor = new Battle(donorOptions as any).toJSON() as AnyRecord;
  const donorPokemon: AnyRecord[] = donor.sides[opponentIndex].pokemon;

  const newPokemon = donorPokemon.map((mon, position) => {
    const entry = sampledByPosition.get(position)!;
    if (!entry.reveal) {
      mon.position = position;
      mon.isActive = false;
      return mon;
    }
    const original = originalForReveal(originalPokemon, entry.reveal);
    return original ? applyPublicDynamicState(mon, original, entry.reveal) : mon;
  });

  side.pokemon = newPokemon;
  side.pokemonLeft = newPokemon.filter(mon => !mon.fainted).length;
  side.totalFainted = newPokemon.filter(mon => mon.fainted).length;
  snapshot.sentLogPos = 0;
  snapshot.sentEnd = false;

  const sampledSets = [...sampledByPosition.entries()]
    .sort(([a], [b]) => a - b)
    .map(([, entry]) => ({
      species: entry.set.species,
      moves: [...(entry.set.moves || [])],
      item: entry.set.item || null,
      ability: entry.set.ability || null,
      tera_type: entry.set.teraType || null,
      revealed: !!entry.reveal,
      candidate_attempts: entry.attempts,
    }));

  return {
    snapshot,
    metadata: {
      mode: 'randbats_belief',
      belief_seed: [...beliefSeed],
      sampled_sets: sampledSets,
      candidate_count: sampledSets.reduce((sum, set) => sum + set.candidate_attempts, 0),
      constrained_fields: constrainedFields,
      missing_randbats_data_count: missingData,
      impossible_belief_states: impossible,
      public_info_constraint_violations: 0,
    },
  };
}
