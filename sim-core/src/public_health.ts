import { publicTeamIdent as ident } from './typed_state_lifecycle';
import {serializeCanonicalAction, type CanonicalAction} from './canonical_action';
/** Health consequences established by public records and the addressed owner's request. */
export type Row = Record<string, unknown>;
type Health = {hp_text?: string; hp_ratio?: number; fainted?: boolean; status?: string | null; active?: boolean};

function condition(value: string): Health {
  const [hp, status] = value.split(' ');
  const [numerator, denominator] = hp.split('/').map(Number);
  return {hp_text: hp, hp_ratio: status === 'fnt' ? 0 : numerator / denominator,
    fainted: status === 'fnt', status: status && status !== 'fnt' ? status : null};
}

export function projectPublicHealth(prefix: readonly string[]): Record<string, Health> {
  const health: Record<string, Health> = {};
  const active: Record<string, string> = {};
  const appearancePrior: Record<string, Health | undefined> = {};
  for (const line of prefix) {
    const parts = line.split('|');
    const command = parts[1];
    const target = ident(parts[2] || '');
    if (!/^p[12]: .+/.test(target)) continue;
    if (command === 'switch' || command === 'drag') {
      const outgoing = active[target.slice(0, 2)];
      if (outgoing && health[outgoing]) health[outgoing].active = false;
      active[target.slice(0, 2)] = target;
      appearancePrior[target.slice(0, 2)] = health[target] && {...health[target]};
    }
    if (command === 'replace') {
      const side = target.slice(0, 2);
      const prior = active[side];
      if (prior && prior !== target) {
        health[target] = {...health[prior]};
        if (appearancePrior[side]) health[prior] = appearancePrior[side]!;
        else delete health[prior];
      }
      active[side] = target;
    }
    const state = health[target] ||= {};
    if (command === 'switch' || command === 'drag' || command === 'replace') state.active = true;
    const healthField = ['switch', 'drag', 'replace', 'detailschange', '-detailschange'].includes(command) ? 4
      : ['-damage', '-heal', '-sethp', 'damage', 'heal', 'sethp'].includes(command) ? 3 : null;
    if (healthField !== null && parts[healthField]) {
      const next = condition(parts[healthField]);
      // Zero-HP damage precedes faintMessages, which performs the status clear.
      if (next.fainted && ['-damage', '-sethp', 'damage', 'sethp'].includes(command)) delete (next as Health).status;
      Object.assign(state, next);
    }
    if (command === '-status' || command === 'status') state.status = parts[3];
    if (command === '-curestatus' || command === 'curestatus') state.status = null;
    if (command === 'faint') Object.assign(state, {hp_text: '0', hp_ratio: 0, fainted: true, status: null, active: false});
  }
  return Object.fromEntries(Object.entries(health).filter(([, state]) => Object.keys(state).length));
}

const terminalOwners = new WeakMap<Row, {prefix: readonly string[]; abilitySuffix: readonly string[]; perspective: string; appearance: string; actual: string; roster: string; owners: Row[]; items: Record<string, string | null>; history: Record<string, {last_item: unknown; item_state: unknown}>}>();
const rosterIdentity = (rows: unknown) => {
  if (!Array.isArray(rows)) fail('terminal owned roster must be an array');
  return JSON.stringify(rows.map((row) => ['slot', 'ident', 'name', 'base_species'].map((key) => row[key])));
};
export function ownedAppearance(prefix: readonly string[], perspective: string): string | null {
  let appearance: string | null = null;
  for (const line of prefix) {
    const parts = line.split('|');
    if (['switch', 'drag', 'replace'].includes(parts[1]) && parts[2]?.startsWith(`${perspective}a: `)) appearance = ident(parts[2]);
  }
  return appearance;
}
/** Internal context: callers must first validate predecessor semantics and transition joins. */
export interface TerminalOwnerContinuity {
  predecessor: Row;
  before: {step_index: number; branch_id: string; state_fingerprint: string};
  transition: {step_index: number; parent_branch_id: string; branch_id: string; input_state_fingerprint: string; output_state_fingerprint: string};
  after: {step_index: number; branch_id: string; state_fingerprint: string};
  action?: CanonicalAction;
}
export function carryTerminalOwner(context: TerminalOwnerContinuity, successor: Row): void {
  const {predecessor, before, transition, after} = context;
  if (transition.step_index !== before.step_index || after.step_index !== before.step_index + 1
    || transition.parent_branch_id !== before.branch_id || transition.branch_id !== after.branch_id
    || transition.input_state_fingerprint !== before.state_fingerprint || transition.output_state_fingerprint !== after.state_fingerprint) fail('terminal transition continuity is invalid');
  const view = successor.view as Row;
  if (successor.request !== null || view.terminated !== true) return;
  const prefix = predecessor.protocol_prefix as string[];
  const next = successor.protocol_prefix as string[];
  const perspective = predecessor.perspective as string;
  const owners = (predecessor.request as Row | null)?.side as Row[] | undefined;
  const active = owners?.filter((row) => row.active);
  const appearance = ownedAppearance(prefix, perspective);
  if (predecessor.battle_id !== successor.battle_id || predecessor.schema_version !== successor.schema_version
    || perspective !== successor.perspective || !appearance || active?.length !== 1
    || next.length < prefix.length || prefix.some((line, index) => next[index] !== line)) fail('terminal predecessor authority is discontinuous');
  let actual = ident(String(active[0].ident));
  const predecessorActual = actual;
  if (!actual.startsWith(`${perspective}: `)) fail('terminal predecessor owner is foreign');
  const roster = rosterIdentity((predecessor.view as Row).self_team);
  if (rosterIdentity(view.self_team) !== roster) fail('terminal owned roster identity/order changed');
  const suffix = next.slice(prefix.length);
  const ownSwitches = suffix.filter((line) => ['switch', 'drag'].includes(line.split('|')[1]) && line.split('|')[2]?.startsWith(`${perspective}a: `));
  let terminalAppearance = appearance;
  if (ownSwitches.length) {
    const finalAppearance = ownedAppearance(next, perspective);
    const revealed = suffix.some((line) => line.startsWith(`|replace|${perspective}a: `));
    const noIllusion = owners!.every((row) => typeof row.ability === 'string' && row.ability && row.ability !== 'illusion'
      && typeof row.base_ability === 'string' && row.base_ability && row.base_ability !== 'illusion');
    if (ownSwitches.length !== 1 || !finalAppearance
      || owners!.filter((row) => ident(String(row.ident)) === finalAppearance).length !== 1) fail('terminal switched appearance lacks sufficient owned identity authority');
    if (context.action) {
      const request = predecessor.request as any;
      serializeCanonicalAction(context.action, request, perspective as 'p1' | 'p2');
    }
    const incoming = context.action?.kind === 'switch' && ownSwitches[0].startsWith(`|switch|`)
      ? owners!.find((row) => row.slot === context.action!.switch_slot) : undefined;
    if (!revealed && incoming) {
      actual = ident(String(incoming.ident));
      if (actual !== finalAppearance && incoming.ability !== 'illusion') fail('terminal switch appearance disagrees with submitted owned action');
    } else {
      if (!revealed && !noIllusion) fail('terminal switched appearance lacks sufficient owned identity authority');
      actual = finalAppearance;
    }
    if (incoming && revealed && ident(String(incoming.ident)) !== finalAppearance) fail('terminal revealed switch disagrees with submitted owned action');
    terminalAppearance = finalAppearance;
  }
  for (const line of suffix) {
    const parts = line.split('|');
    if (parts[1] === 'replace' && parts[2]?.startsWith(`${perspective}a: `) && ident(parts[2]) !== actual) fail('terminal replacement disagrees with predecessor owner');
  }
  const items = Object.fromEntries(owners!.filter((row) => 'item' in row).map((row) => [ident(String(row.ident)), row.item ? String(row.item) : null]));
  const history = Object.fromEntries(((predecessor.view as Row).self_team as Row[]).filter((row) => !!row.last_item && 'item_state' in row)
    .map((row) => [ident(String(row.ident)), {last_item: row.last_item, item_state: row.item_state}]));
  let currentAppearance = appearance;
  let currentActual = predecessorActual;
  for (const line of suffix) {
    const parts = line.split('|');
    const target = ident(parts[2] || '');
    if (['switch', 'drag', 'replace'].includes(parts[1]) && target.slice(0, 2) === perspective) {currentAppearance = target; currentActual = actual;}
    const bound = target === currentAppearance ? currentActual : target;
    if (bound.slice(0, 2) === perspective) {
      if (['-item', 'item'].includes(parts[1])) {items[bound] = parts[3].toLowerCase().replace(/[^a-z0-9]/g, ''); if (history[bound]) history[bound].item_state = 'held';}
      if (['-enditem', 'enditem'].includes(parts[1])) {
        items[bound] = null;
        const item = parts[3].toLowerCase().replace(/[^a-z0-9]/g, '');
        const consumed = parts.slice(4).some((tag) => tag.includes('[eat]') || tag.includes('[from] gem')) || parts.length === 4 && item !== 'airballoon';
        history[bound] = {last_item: item, item_state: consumed ? 'consumed' : 'removed'};
      }
    }
  }
  terminalOwners.set(view, {prefix: [...next], abilitySuffix: [...suffix], perspective, appearance: terminalAppearance, actual, roster, owners: structuredClone(owners!), items, history});
}
export function withTerminalOwner<T>(context: TerminalOwnerContinuity, successor: Row, validate: () => T): T {
  const view = successor.view as Row;
  const previous = terminalOwners.get(view);
  try {
    carryTerminalOwner(context, successor);
    return validate();
  } finally {
    if (previous) terminalOwners.set(view, previous); else terminalOwners.delete(view);
  }
}
export function copyTerminalOwner(source: Row, target: Row): void {
  const authority = terminalOwners.get(source);
  if (authority) {
    if (authority.roster !== rosterIdentity(source.self_team) || authority.roster !== rosterIdentity(target.self_team)) fail('terminal owner authority was mutated');
    terminalOwners.set(target, authority);
  }
}
export function terminalOwnedItems(view: Row): Record<string, string | null> | undefined { return terminalOwners.get(view)?.items; }
export function terminalOwnedAbilitySuffix(view: Row) {return terminalOwners.get(view)?.abilitySuffix;}
export function terminalOwnedRequests(view: Row) {return terminalOwners.get(view)?.owners;}
export function terminalOwnedItemHistory(view: Row) {return terminalOwners.get(view)?.history;}
export function boundOwnedTarget(prefix: readonly string[], perspective: string, view: Row, request: Row | null, target: string): string {
  const appearance = ownedAppearance(prefix, perspective);
  const active = (request?.side as Row[] | undefined)?.find((row) => row.active);
  if (target === appearance && active) {
    const actual = ident(String(active.ident));
    if (actual !== appearance && (active.ability !== 'illusion'
      || (request?.side as Row[]).filter((row) => ident(String(row.ident)) === appearance).length !== 1)) fail('owned appearance lacks legitimate Illusion roster authority');
    return actual;
  }
  const authority = terminalOwners.get(view);
  if (authority) {
    if (authority.perspective !== perspective || JSON.stringify(authority.prefix) !== JSON.stringify(prefix)
      || authority.roster !== rosterIdentity(view.self_team)) fail('terminal owner authority was mutated');
    if (target === authority.appearance && appearance === authority.appearance) return authority.actual;
  }
  return target;
}

function fail(message: string): never { throw new Error(`Public health evidence mismatch: ${message}`); }

export function assertPublicHealthMatchesEvidence(prefix: readonly string[], perspective: string,
  view: Row, request: Row | null): void {
  const projected = projectPublicHealth(prefix);
  const requestRows = request && Array.isArray(request.side) ? request.side as Row[] : [];
  let ownedAppearance: string | null = null;
  for (const line of prefix) {
    const parts = line.split('|');
    if (['switch', 'drag', 'replace'].includes(parts[1]) && parts[2]?.startsWith(`${perspective}a: `)) ownedAppearance = ident(parts[2]);
  }
  const ownerActive = requestRows.find((entry) => entry.active);
  const rows = ['self_team', 'opponent_team'].flatMap((team) => {
    const roster = view[team];
    if (roster !== undefined && !Array.isArray(roster)) fail(`${team} must be an array`);
    return (roster as Row[] || []).map((row) => ({team, row}));
  });
  if (requestRows.length && (rows.filter(({team}) => team === 'self_team').length !== requestRows.length
    || requestRows.some((owner, index) => ident(String((view.self_team as Row[])[index]?.ident)) !== ident(String(owner.ident))))) fail('owned roster identity/order disagrees with addressed request');
  for (const [target, publicState] of Object.entries(projected)) {
    const expectedTeam = target.slice(0, 2) === perspective ? 'self_team' : 'opponent_team';
    // The owner request binds an unrevealed Illusion appearance to the real
    // active roster member; the opposing public roster keeps that appearance.
    const boundTarget = expectedTeam === 'self_team' ? boundOwnedTarget(prefix, perspective, view, request, target) : target;
    const matching = rows.filter(({row}) => typeof row.ident === 'string' && ident(row.ident) === boundTarget);
    if (matching.length !== 1 || matching[0].team !== expectedTeam) fail(`${target} requires exactly one ${expectedTeam} row`);
    const row = matching[0].row;
    const owner = expectedTeam === 'self_team' ? requestRows.find((entry) => ident(String(entry.ident)) === boundTarget) : undefined;
    const ownerPublicPrecision = !owner && expectedTeam === 'self_team' && typeof row.hp_text === 'string'
      && row.hp_text.includes('/') && publicState.hp_text?.includes('/100');
    const expected = owner ? {...condition(String(owner.condition)), active: !!owner.active && !condition(String(owner.condition)).fainted} : publicState;
    for (const key of ['hp_text', 'hp_ratio', 'fainted', 'status', 'active'] as const) {
      if (expected[key] === undefined || ownerPublicPrecision && (key === 'hp_text' || key === 'hp_ratio')) continue;
      if (row[key] !== expected[key]) fail(`${target} ${key} disagrees with ${owner ? 'owner request' : 'public prefix'}`);
    }
    if (ownerPublicPrecision) {
      const exact = condition(String(row.hp_text)).hp_ratio!;
      const percentage = exact === 0 ? 0 : Math.min(exact < 1 ? 99 : 100, Math.ceil(exact * 100));
      if (row.hp_ratio !== exact || percentage / 100 !== publicState.hp_ratio) fail(`${target} owner/public HP disagree`);
    }
    // Request exact health and spectator percentages must describe the same current result.
    if (owner && target === ownedAppearance && publicState.hp_ratio !== undefined && publicState.hp_text?.includes('/100')) {
      const exact = expected.hp_ratio!;
      const percentage = exact === 0 ? 0 : Math.min(exact < 1 ? 99 : 100, Math.ceil(exact * 100));
      if (percentage / 100 !== publicState.hp_ratio) fail(`${target} request/public HP disagree`);
    }
    if (owner && target === ownedAppearance && publicState.fainted !== undefined && publicState.fainted !== expected.fainted) fail(`${target} request/public faint disagree`);
    // A current request may establish a silent bench cure; active public status must agree.
    if (owner?.active && target === ownedAppearance && publicState.status !== undefined && publicState.status !== expected.status) fail(`${target} request/public status disagree`);
  }
  for (const owner of requestRows) {
    const target = ident(String(owner.ident));
    const matching = rows.filter(({team, row}) => team === 'self_team' && typeof row.ident === 'string' && ident(row.ident) === target);
    if (matching.length !== 1) fail(`${target} owner request requires exactly one self_team row`);
    const expected = {...condition(String(owner.condition)), active: !!owner.active && !condition(String(owner.condition)).fainted};
    for (const key of ['hp_text', 'hp_ratio', 'fainted', 'status', 'active'] as const) {
      if (matching[0].row[key] !== expected[key]) fail(`${target} ${key} disagrees with owner request`);
    }
  }
}
