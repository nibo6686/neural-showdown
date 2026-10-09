import { Dex, toID } from 'pokemon-showdown';
import {PROTOCOL_CONTRACT} from './protocol_contract';
import type { PokemonView } from './types';
import { terminalOwnedRequests, terminalOwnedAbilitySuffix } from './public_health';

/** Reviewed permanent replacement writers; a generic form/reveal pair supplies no base. */
function replacementBaseWriter(species: string): string | null {
  return ({terapagosstellar: 'teraformzero', ogerpontealtera: 'embodyaspectteal',
    ogerponwellspringtera: 'embodyaspectwellspring', ogerponhearthflametera: 'embodyaspecthearthflame',
    ogerponcornerstonetera: 'embodyaspectcornerstone'} as Record<string, string>)[toID(species.split(',')[0])] || null;
}

/** Replay supported public reveals; Trace [of] remains raw source identity. */
export function publicRevealedAbilities(prefix: readonly string[]) {
  const facts: Record<string, {ability: string | null; base: string | null; state: 'known' | 'changed' | 'unknown'; copied: boolean; cleared: boolean; invalidated: 'transform' | 'form' | null; baseWriter: string | null}> = {};
  const active: Record<string, string> = {};
  const clear = (target: string) => {
    const row = facts[target];
    if (!row) return;
    row.ability = row.base; row.state = row.base ? 'known' : 'unknown'; row.cleared = true;
  };
  for (const line of prefix) {
    const parts = line.split('|');
    const target = (parts[2] || '').replace(/^(p[12])a: /, '$1: '), side = target.slice(0, 2);
    if (parts[1] === 'switch' || parts[1] === 'drag') {
      clear(active[side]); clear(target); active[side] = target;
    } else if (parts[1] === 'faint') clear(target);
    else if (parts[1] === 'replace') {
      // A replacement changes the carrier identity; do not graft old copy facts.
      delete facts[active[side]]; active[side] = target;
    } else if (['detailschange', '-formechange', '-transform'].includes(parts[1])) {
      // Retain the unknown-current obligation; Transform reveals no target ability.
      const row = facts[target] ||= {ability: null, base: null, state: 'unknown', copied: false, cleared: false, invalidated: null, baseWriter: null};
      if (parts[1] === 'detailschange' && preservesOwnedAbilityForForm(parts[3], row.ability, row.base)) continue;
      row.ability = null; row.state = 'unknown'; row.cleared = false;
      row.invalidated = parts[1] === '-transform' ? 'transform' : 'form';
      row.baseWriter = parts[1] === 'detailschange' ? replacementBaseWriter(parts[3]) : null;
      if (row.invalidated === 'form') {row.base = null; row.copied = false;}
    } else if (['-ability', 'ability'].includes(parts[1])) {
      const domains = PROTOCOL_CONTRACT.validation_rules.ability.payload_domains;
      const template = parts[1] === 'ability' && parts.length === 4 ? 'bare_reveal'
        : parts[1] === '-ability' && parts.length === 4 ? 'dash_reveal'
        : parts[1] === '-ability' && parts.length === 5 && parts[4] === 'boost' ? 'dash_boost'
        : parts[1] === '-ability' && parts.length === 6 && parts[4] === '[from] ability: Trace' ? 'dash_trace_copy' : null;
      if (!template || !domains[template].includes(parts[3])) continue;

      const row = facts[target] ||= {ability: null, base: null, state: 'unknown', copied: false, cleared: false, invalidated: null, baseWriter: null};
      const changed = parts.slice(4).some((tag) => tag.startsWith('[from]'));
      if (!changed && !row.base && !row.copied && row.invalidated !== 'transform'
        && (row.invalidated !== 'form' || row.baseWriter === toID(parts[3]))) row.base = toID(parts[3]);
      row.ability = toID(parts[3]); row.state = changed ? 'changed' : 'known'; row.cleared = false;
      row.copied ||= parts[4] === '[from] ability: Trace';
    }
  }
  return facts;
}

export function publicTraceAbilities(prefix: readonly string[]) {
  return Object.fromEntries(Object.entries(publicRevealedAbilities(prefix)).filter(([, row]) => row.copied));
}

/** Pinned permanent branches that preserve an already addressed owner ability pair. */
export function preservesOwnedAbilityForForm(species: string, ability: unknown, base: unknown): boolean {
  const preserved: Record<string, string> = {mimikyubusted: 'disguise', eiscue: 'iceface', eiscuenoice: 'iceface', palafinhero: 'zerotohero'};
  const expected = preserved[toID(species.split(',')[0])];
  return !!expected && ability === expected && base === expected;
}

/** Replay only a suffix after independently established owned current/base authority. */
export function ownedAbilityAfterSuffix(owner: Record<string, unknown>, suffix: readonly string[]) {
  let ability = String(owner.ability || '') || null, base = String(owner.base_ability || '') || null;
  let baseWriter: string | null = null;
  let active = !!owner.active;
  const target = String(owner.ident).replace(/^(p[12])a: /, '$1: ');
  for (const line of suffix) {
    const parts = line.split('|'), addressed = (parts[2] || '').replace(/^(p[12])a: /, '$1: ');
    if (['switch', 'drag'].includes(parts[1]) && addressed.slice(0, 2) === target.slice(0, 2)) {
      if (active || addressed === target) ability = base;
      active = addressed === target;
    }
    if (addressed !== target) continue;
    if (parts[1] === 'faint') {ability = base; active = false;}
    else if (parts[1] === '-transform') {ability = null; baseWriter = null;}
    else if (parts[1] === 'detailschange' && !preservesOwnedAbilityForForm(parts[3], ability, base)) {
      ability = null; base = null; baseWriter = replacementBaseWriter(parts[3]);
    }
    else if (['-ability', 'ability'].includes(parts[1])) {
      ability = toID(parts[3]);
      if (!base && baseWriter === ability && !parts.slice(4).some((tag) => tag.startsWith('[from]'))) base = ability;
    }
  }
  return {ability, base_ability: base, ability_state: ability ? 'known' : 'unknown'};
}

/** Public Gas witnesses; no species lookup or hidden ability inference. */
export function publicGasSources(prefix: readonly string[]): Set<string> {
  const sources = new Set<string>();
  const active: Record<string, string> = {};
  for (const record of prefix) {
    const parts = record.split('|');
    const target = (parts[2] || '').replace(/^(p[12])a: /, '$1: ');
    const side = target.slice(0, 2);
    if (parts[1] === 'switch' || parts[1] === 'drag') {
      if (active[side]) sources.delete(active[side]);
      active[side] = target;
    } else if (parts[1] === 'faint' || parts[1] === '-transform' || parts[1] === '-endability'
      || parts[1] === '-end' && parts[3] === 'ability: Neutralizing Gas') {
      sources.delete(target);
    } else if (parts[1] === '-start' && toID(parts[3]) === 'gastroacid') {
      sources.delete(target);
    } else if (parts[1] === '-ability') {
      if (toID(parts[3]) === 'neutralizinggas') sources.add(target);
      else sources.delete(target);
    }
  }
  return sources;
}

/** Names remain facts when effectiveness is suppressed or cannot be established. */
export function abilityEffectiveness(pokemon: Pick<PokemonView, 'active' | 'fainted' | 'ability' | 'transformed' | 'ability_suppressed'>,
  gasPresent: boolean, item: string | null, itemKnown: boolean): 'active' | 'suppressed' | 'unknown' {
  if (!pokemon.ability) return 'unknown';
  const ability = Dex.abilities.get(pokemon.ability);
  if (!pokemon.active || pokemon.fainted || pokemon.transformed && ability.flags.notransform) return 'suppressed';
  if (ability.flags.cantsuppress) return 'active';
  if (pokemon.ability_suppressed) return 'suppressed';
  if (!gasPresent || toID(pokemon.ability) === 'neutralizinggas') return 'active';
  if (!itemKnown) return 'unknown';
  return toID(item) === 'abilityshield' ? 'active' : 'suppressed';
}

export function publicLocalAbilitySuppression(prefix: readonly string[]): Set<string> {
  const suppressed = new Set<string>();
  const active: Record<string, string> = {};
  for (const line of prefix) {
    const parts = line.split('|');
    const target = (parts[2] || '').replace(/^(p[12])a: /, '$1: ');
    const side = target.slice(0, 2);
    if (parts[1] === 'switch' || parts[1] === 'drag') {
      suppressed.delete(active[side]); suppressed.delete(target); active[side] = target;
    } else if (parts[1] === 'faint' || parts[1] === '-ability' || parts[1] === '-transform' || parts[1] === '-formechange') {
      suppressed.delete(target);
    } else if (parts[1] === '-endability' && parts.length === 3) suppressed.add(target);
  }
  return suppressed;
}

export function assertPublicAbilityMatchesEvidence(prefix: readonly string[], view: Record<string, unknown>, request: Record<string, unknown> | null, perspective = String(view.player || '')): void {
  const gasPresent = publicGasSources(prefix).size > 0;
  const locallySuppressed = publicLocalAbilitySuppression(prefix);
  const owners = request && Array.isArray(request.side) ? request.side as Record<string, unknown>[] : [];
  const terminalOwners = terminalOwnedRequests(view) || [];
  for (const [target, fact] of Object.entries(publicRevealedAbilities(prefix))) {
    if (!['p1', 'p2'].includes(perspective)) throw new Error('Public ability evidence mismatch: reveal requires a perspective.');
    // Opponent ability names/states are excluded by both public schemas.
    if (!target.startsWith(`${perspective}: `)) {
      const opponents = Array.isArray(view.opponent_team) ? view.opponent_team : [];
      if (opponents.some((row) => row && typeof row.ident === 'string'
        && row.ident.replace(/^(p[12])a: /, '$1: ') === target
        && ['ability', 'base_ability', 'ability_state', 'ability_suppressed'].some((key) => key in row))) {
        throw new Error('Public ability evidence mismatch: opponent ability fields are excluded from the public schema.');
      }
      continue;
    }
    const roster = view.self_team;
    const rows = Array.isArray(roster) ? roster.filter((row) => row && typeof row.ident === 'string'
      && row.ident.replace(/^(p[12])a: /, '$1: ') === target) : [];
    if (rows.length !== 1) throw new Error('Public ability evidence mismatch: reveal requires exactly one correctly sided recipient.');
    const row = rows[0] as Record<string, unknown>;
    const owner = owners.find((entry) => entry.ident === target);
    const priorOwner = terminalOwners.find((entry) => entry.ident === target);
    const terminalFact = priorOwner && (priorOwner.ability || priorOwner.base_ability) && terminalOwnedAbilitySuffix(view) ? ownedAbilityAfterSuffix(priorOwner, terminalOwnedAbilitySuffix(view)!) : null;
    const ability = terminalFact ? terminalFact.ability : owner?.ability || (fact.cleared && priorOwner ? priorOwner.base_ability : fact.ability) || null;
    if (!fact.cleared && fact.ability && owner?.ability && owner.ability !== fact.ability) throw new Error('Public ability evidence mismatch: public reveal contradicts addressed ability.');
    const states = terminalFact ? [terminalFact.ability_state] : owner?.ability ? ['known'] : ability ? ['known', fact.state] : [fact.state];
    if (ability) states.push('suppressed');
    if (row.ability !== ability || !states.includes(String(row.ability_state))) throw new Error('Public ability evidence mismatch: reveal name/state disagrees with ordered public copy or cleanup.');
    if (fact.invalidated) {
      const base = terminalFact ? terminalFact.base_ability : owner?.base_ability || fact.base || null;
      if (row.base_ability !== base || !ability && row.ability_suppressed !== false) {
        throw new Error('Public ability evidence mismatch: invalidated current/base requires eligible authority.');
      }
    }
  }
  if ((view.opponent_team as Record<string, unknown>[] || []).some((row) =>
    ['ability', 'base_ability', 'ability_state', 'ability_suppressed'].some((key) => key in row))) {
    throw new Error('Public ability evidence mismatch: opponent ability fields are excluded from the public schema.');
  }
  for (const value of (view.self_team as Record<string, unknown>[] || [])) {
    const row = value as unknown as PokemonView;
    const target = row.ident.replace(/^(p[12])a: /, '$1: ');
    const owner = owners.find((entry) => entry.ident === target);
    const priorOwner = terminalOwners.find((entry) => entry.ident === target);
    if (priorOwner && (priorOwner.ability || priorOwner.base_ability)) {
      const fact = ownedAbilityAfterSuffix(priorOwner, terminalOwnedAbilitySuffix(view) || []);
      if (row.ability !== fact.ability || row.base_ability !== fact.base_ability || (row.ability_state !== fact.ability_state && row.ability_state !== 'suppressed') || !('ability_suppressed' in row) || !fact.ability && row.ability_suppressed !== false) {
        throw new Error('Public ability evidence mismatch: terminal current/base/state disagrees with validated owner and ordered suffix.');
      }
    }
    if (owner && (owner.base_ability && row.base_ability !== owner.base_ability
      || owner.ability && row.ability_state !== 'known' && row.ability_state !== 'suppressed')) {
      throw new Error('Public ability evidence mismatch: owned base/state disagrees with addressed request.');
    }
    const ability = owner?.ability ? String(owner.ability) : row.ability;
    if (owner && row.item !== (owner.item || null)) throw new Error('Public ability evidence mismatch: owned item exemption disagrees with addressed request.');
    if (owner?.ability && row.ability !== ability) throw new Error('Public ability evidence mismatch: owned ability name disagrees with addressed request.');
    const effectiveness = abilityEffectiveness({...row, ability, ability_suppressed: locallySuppressed.has(target)}, gasPresent,
      owner ? String(owner.item || '') || null : row.item, true);
    const suppressed = row.active && effectiveness === 'suppressed';
    if (effectiveness !== 'unknown' && (row.ability_suppressed !== suppressed
      || suppressed && row.ability_state !== 'suppressed' || !suppressed && row.ability_state === 'suppressed')) {
      throw new Error('Public ability evidence mismatch: owned suppression disagrees with public Gas/local evidence and owned exemptions.');
    }
  }
}
