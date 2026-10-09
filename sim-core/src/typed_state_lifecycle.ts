import fs from 'node:fs';
import path from 'node:path';
import type { PlayerID, PokemonView } from './types';
import { isCanonicalPlayerIdent } from './protocol_contract';

export type TypedStateDisposition =
  | 'evidence-derived-typed'
  | 'raw-only'
  | 'source-proven-unreachable'
  | 'unsupported-fail-closed';

interface LifecycleEntry {
  id: string;
  family: 'move_volatile' | 'side_condition';
  disposition: TypedStateDisposition;
  mode: string;
  cap?: number;
  equivalence_class: string;
}

interface LifecycleContract {
  schema_version: 'public-typed-state-lifecycle/v1';
  court_change_ids: string[];
  entries: LifecycleEntry[];
}

function loadLifecycleContract(): LifecycleContract {
  let directory = __dirname;
  for (let depth = 0; depth < 8; depth += 1) {
    const candidate = path.join(directory, 'simulator_coverage', 'pokemon-showdown-0.11.10-gen9randombattle.json');
    if (fs.existsSync(candidate)) {
      const manifest = JSON.parse(fs.readFileSync(candidate, 'utf8')) as { public_typed_state_lifecycle?: LifecycleContract };
      if (manifest.public_typed_state_lifecycle?.schema_version === 'public-typed-state-lifecycle/v1') {
        return manifest.public_typed_state_lifecycle;
      }
    }
    const parent = path.dirname(directory);
    if (parent === directory) break;
    directory = parent;
  }
  throw new Error('Pinned public typed-state lifecycle contract was not found.');
}

export const PUBLIC_TYPED_STATE_LIFECYCLE = loadLifecycleContract();
const lifecycleEntries = new Map(PUBLIC_TYPED_STATE_LIFECYCLE.entries.map((entry) => [`${entry.family}:${entry.id}`, entry]));

export function typedStateLifecycleEntry(family: LifecycleEntry['family'], id: string): LifecycleEntry | undefined {
  return lifecycleEntries.get(`${family}:${id}`);
}

export interface ProjectedPublicTypedState {
  volatiles_by_ident: Record<string, string[]>;
  side_conditions_by_player: Record<PlayerID, Record<string, number>>;
}

function effectId(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function activeIdent(value: string): { player: PlayerID; ident: string } | null {
  const match = /^(p[12])a: (.+)$/.exec(value);
  return match ? { player: match[1] as PlayerID, ident: `${match[1]}: ${match[2]}` } : null;
}

export function publicTeamIdent(value: string): string {
  return activeIdent(value)?.ident || value;
}

/** Replay the exact normalized public prefix into the typed subset approved by the lifecycle atlas. */
export function projectPublicTypedState(prefix: readonly string[]): ProjectedPublicTypedState {
  const volatiles = new Map<string, Set<string>>();
  const active: Partial<Record<PlayerID, string>> = {};
  const sides: Record<PlayerID, Record<string, number>> = { p1: {}, p2: {} };
  const getVolatiles = (ident: string) => {
    let state = volatiles.get(ident);
    if (!state) { state = new Set<string>(); volatiles.set(ident, state); }
    return state;
  };
  const clear = (ident: string | undefined) => { if (ident) getVolatiles(ident).clear(); };

  for (const line of prefix) {
    if (!line.startsWith('|')) continue;
    const parts = line.split('|');
    const command = parts[1] || '';
    if (command === 'switch' || command === 'drag') {
      const incoming = activeIdent(parts[2] || '');
      if (!incoming) continue;
      const donor = active[incoming.player];
      const donorHadSubstitute = !!donor && getVolatiles(donor).has('substitute');
      clear(donor);
      const next = getVolatiles(incoming.ident);
      next.clear();
      const shedTail = command === 'switch' && parts.length === 6 && parts[5] === '[from] Shed Tail';
      if (shedTail && donorHadSubstitute) next.add('substitute');
      active[incoming.player] = incoming.ident;
      continue;
    }
    if (command === 'replace') {
      const next = activeIdent(parts[2] || '');
      if (!next) continue;
      const prior = active[next.player];
      if (prior && prior !== next.ident) {
        const state = getVolatiles(prior);
        volatiles.set(next.ident, new Set(state));
        volatiles.delete(prior);
      }
      active[next.player] = next.ident;
      continue;
    }
    if (command === 'faint') {
      const target = activeIdent(parts[2] || '');
      if (!target) continue;
      clear(target.ident);
      if (active[target.player] === target.ident) delete active[target.player];
      continue;
    }
    if (command === '-start' || command === '-end') {
      const entry = typedStateLifecycleEntry('move_volatile', effectId(parts[3] || ''));
      if (!entry || entry.disposition === 'raw-only') continue;
      if (entry.disposition !== 'evidence-derived-typed') {
        throw new Error(`Typed lifecycle evidence mismatch: unsupported-fail-closed volatile ${entry.id}.`);
      }
      const target = activeIdent(parts[2] || '');
      if (!target || active[target.player] !== target.ident) {
        throw new Error(`Typed lifecycle evidence mismatch: ${command} targets a nonactive ${entry.id}.`);
      }
      const state = getVolatiles(target.ident);
      if (command === '-start') {
        if (state.has(entry.id)) throw new Error(`Typed lifecycle evidence mismatch: duplicate ${entry.id} start.`);
        state.add(entry.id);
      } else {
        if (!state.has(entry.id)) throw new Error(`Typed lifecycle evidence mismatch: ${entry.id} ends without a public start.`);
        state.delete(entry.id);
      }
      continue;
    }
    if (command === '-sidestart' || command === '-sideend') {
      const sideToken = (parts[2] || '').split(':', 1)[0];
      if (sideToken !== 'p1' && sideToken !== 'p2') continue;
      const id = effectId((parts[3] || '').replace(/^move:\s*/i, ''));
      const entry = typedStateLifecycleEntry('side_condition', id);
      if (!entry || entry.disposition === 'raw-only') continue;
      if (entry.disposition !== 'evidence-derived-typed') {
        throw new Error(`Typed lifecycle evidence mismatch: unsupported-fail-closed side condition ${entry.id}.`);
      }
      const state = sides[sideToken];
      const prior = state[id] || 0;
      if (command === '-sidestart') {
        if (entry.mode === 'count') {
          const next = prior + 1;
          if (next > (entry.cap || 1)) throw new Error(`Typed lifecycle evidence mismatch: ${id} exceeds its public layer cap.`);
          state[id] = next;
        } else {
          if (prior) throw new Error(`Typed lifecycle evidence mismatch: duplicate ${id} presence start.`);
          state[id] = 1;
        }
      } else {
        if (!prior) throw new Error(`Typed lifecycle evidence mismatch: ${id} ends without a public start.`);
        delete state[id];
      }
      continue;
    }
    if (command === '-swapsideconditions') {
      for (const id of PUBLIC_TYPED_STATE_LIFECYCLE.court_change_ids) {
        const p1 = sides.p1[id];
        const p2 = sides.p2[id];
        if (p1 === undefined) delete sides.p2[id]; else sides.p2[id] = p1;
        if (p2 === undefined) delete sides.p1[id]; else sides.p1[id] = p2;
      }
    }
  }
  return {
    volatiles_by_ident: Object.fromEntries([...volatiles].map(([ident, values]) => [ident, [...values].sort()])),
    side_conditions_by_player: sides,
  };
}

export function assertTypedStateMatchesPublicPrefix(
  prefix: readonly string[],
  perspective: PlayerID,
  view: Partial<{ self_team: readonly Pick<PokemonView, 'ident' | 'volatiles'>[]; opponent_team: readonly Pick<PokemonView, 'ident' | 'volatiles'>[];
    field: { side_conditions: { self: Record<string, number>; opponent: Record<string, number> } } }>,
  bindOwned: (target: string) => string = (target) => target,
): void {
  for (const team of [view.self_team, view.opponent_team]) {
    if (team !== undefined && !Array.isArray(team)) throw new Error('Typed lifecycle evidence mismatch: roster containers must be arrays.');
  }
  const projected = projectPublicTypedState(prefix);
  const boundVolatiles: Record<string, string[]> = {};
  for (const [target, values] of Object.entries(projected.volatiles_by_ident)) {
    const bound = target.slice(0, 2) === perspective ? bindOwned(target) : target;
    if (values.length || !boundVolatiles[bound]) boundVolatiles[bound] = values;
  }
  projected.volatiles_by_ident = boundVolatiles;
  const hasDerivedState = Object.values(projected.volatiles_by_ident).some((values) => values.length > 0)
    || Object.values(projected.side_conditions_by_player).some((values) => Object.keys(values).length > 0);
  if (hasDerivedState && perspective !== 'p1' && perspective !== 'p2') {
    throw new Error('Typed lifecycle evidence mismatch: derived typed state requires a valid perspective.');
  }
  const expectedSide = perspective === 'p1'
    ? { self: projected.side_conditions_by_player.p1, opponent: projected.side_conditions_by_player.p2 }
    : { self: projected.side_conditions_by_player.p2, opponent: projected.side_conditions_by_player.p1 };
  for (const [label, team] of [['self', view.self_team], ['opponent', view.opponent_team]] as const) {
    if (!team) continue;
    for (const pokemon of team) {
      const expected = projected.volatiles_by_ident[publicTeamIdent(pokemon.ident)] || [];
      if (pokemon.volatiles !== undefined && JSON.stringify([...pokemon.volatiles].sort()) !== JSON.stringify(expected)) {
        throw new Error(`Typed lifecycle evidence mismatch: ${label} ${pokemon.ident} volatile map disagrees with retained public prefix.`);
      }
    }
  }
  for (const [ident, values] of Object.entries(projected.volatiles_by_ident)) {
    if (!values.length) continue;
    const side = ident.slice(0, 2) as PlayerID;
    const expectedTeam = side === perspective ? 'self_team' : 'opponent_team';
    const rows = [
      ...(view.self_team || []).map((pokemon) => ({ team: 'self_team', pokemon })),
      ...(view.opponent_team || []).map((pokemon) => ({ team: 'opponent_team', pokemon })),
    ].filter(({ pokemon }) => isCanonicalPlayerIdent(publicTeamIdent(pokemon.ident))
      && publicTeamIdent(pokemon.ident) === ident);
    if (rows.length !== 1 || rows[0].team !== expectedTeam || !rows[0].pokemon.volatiles) {
      throw new Error(`Typed lifecycle evidence mismatch: nonempty volatile state for ${ident} requires exactly one canonical ${expectedTeam} roster row.`);
    }
  }
  for (const side of ['self', 'opponent'] as const) {
    const expected = Object.fromEntries(Object.entries(expectedSide[side]).sort(([a], [b]) => a.localeCompare(b)));
    const actualMap = view.field?.side_conditions?.[side];
    if (!Object.keys(expected).length && actualMap === undefined) continue;
    if (Object.keys(expected).length && actualMap === undefined) {
      throw new Error(`Typed lifecycle evidence mismatch: ${side} side-condition state requires its field side_conditions map.`);
    }
    const actual = Object.fromEntries(Object.entries(actualMap || {}).filter(([, value]) => value !== 0).sort(([a], [b]) => a.localeCompare(b)));
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      throw new Error(`Typed lifecycle evidence mismatch: ${side} side-condition map disagrees with retained public prefix.`);
    }
  }
}
