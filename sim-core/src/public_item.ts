import { publicTeamIdent as ident } from './typed_state_lifecycle';
import { ownedAppearance as ownedAppearanceForItems, boundOwnedTarget, terminalOwnedItems, terminalOwnedItemHistory, terminalOwnedRequests, type Row } from './public_health';

/** null = established absence; empty name = presence only; missing key = unknown. */
export function projectPublicItems(prefix: readonly string[]): Record<string, string | null> {
  const items: Record<string, string | null> = {};
  const active: Record<string, string> = {};
  const prior: Record<string, {target: string; item: string | null | undefined}> = {};
  for (const line of prefix) {
    const parts = line.split('|');
    const command = parts[1], target = ident(parts[2] || ''), side = target.slice(0, 2);
    if (!/^p[12]: .+/.test(target)) continue;
    if (command === 'switch' || command === 'drag') {
      prior[side] = {target, item: items[target]};
      active[side] = target;
      // A public appearance can be an unrevealed imposter of this teammate.
      delete items[target];
    } else if (command === 'replace') {
      const appearance = active[side];
      if (appearance && appearance !== target) {
        if (items[appearance] === undefined) delete items[target]; else items[target] = items[appearance];
        const saved = prior[side];
        if (saved?.target === appearance && saved.item !== undefined) items[appearance] = saved.item;
        else delete items[appearance];
      }
      active[side] = target;
    } else if (command === '-item' || command === 'item') {
      items[target] = parts[3].toLowerCase().replace(/[^a-z0-9]/g, '');
    } else if (command === '-enditem' || command === 'enditem') {
      items[target] = null;
    }
  }
  return items;
}

/** A departed, unrevealed appearance cannot identify an old owned carrier if Illusion remains possible. */
export function ambiguousOwnedItemTargets(prefix: readonly string[], perspective: string, owners: Row[]): Set<string> {
  const ambiguous = new Set<string>();
  if (!owners.some((row) => row.ability === 'illusion' || row.base_ability === 'illusion')) return ambiguous;
  let appearance: string | undefined, writer = false, revealed = false;
  for (const line of prefix) {
    const parts = line.split('|'), target = ident(parts[2] || '');
    if (target.slice(0, 2) !== perspective) continue;
    if (['switch', 'drag'].includes(parts[1])) {
      if (appearance && writer && !revealed) ambiguous.add(appearance);
      appearance = target; writer = false; revealed = false;
    } else if (parts[1] === 'replace') {
      appearance = target; revealed = true;
    } else if (['-item', 'item', '-enditem', 'enditem'].includes(parts[1]) && target === appearance) writer = true;
  }
  return ambiguous;
}

export function assertPublicItemsMatchEvidence(prefix: readonly string[], perspective: string, view: Row, request: Row | null): void {
  const fail = (message: string): never => { throw new Error(`Public item evidence mismatch: ${message}`); };
  const rows = ['self_team', 'opponent_team'].flatMap((team) => {
    if (view[team] !== undefined && !Array.isArray(view[team])) fail(`${team} must be an array`);
    return ((view[team] as Row[]) || []).map((row) => ({team, row}));
  });
  const facts = projectPublicItems(prefix);
  const dispositions = projectPublicItemDispositions(prefix);
  let magicRoom = false;
  for (const line of prefix) { const parts = line.split('|'); if (parts[2]?.toLowerCase().replace(/[^a-z0-9]/g, '') === 'movemagicroom' || parts[2]?.toLowerCase().replace(/[^a-z0-9]/g, '') === 'magicroom') { if (parts[1] === '-fieldstart') magicRoom = true; if (parts[1] === '-fieldend') magicRoom = false; } }
  const owners = (request?.side as Row[] | undefined) || [];
  const historyOwners = owners.length ? owners : terminalOwnedRequests(view) || [];
  const ambiguous = ambiguousOwnedItemTargets(prefix, perspective, historyOwners);
  const ownedHistory = Object.fromEntries(Object.entries(projectPublicOwnedItemHistory(prefix, perspective, (target) => boundOwnedTarget(prefix, perspective, view, request, target), historyOwners)).filter(([target]) => target.slice(0, 2) === perspective)
    .map(([target, state]) => [target, state]));
  for (const {team, row} of rows) if (team === 'self_team') {
    const history = ownedHistory[ident(String(row.ident))];
    if (row.last_item && row.last_item !== history?.last_item) fail('owned last item has no matching retained public writer');
    if (['consumed', 'removed'].includes(String(row.item_state)) && row.item_state !== history?.item_state) fail('owned disposition has no matching retained public writer');
  }
  for (const [target, history] of Object.entries(ownedHistory)) {
    const matching = rows.filter(({team, row}) => team === 'self_team' && ident(String(row.ident)) === target);
    if (matching.length !== 1 || matching[0].row.last_item !== history.last_item
      || matching[0].row.item === null && matching[0].row.item_state !== history.item_state) fail('owned retained item history is omitted or disagrees with public writer');
  }
  for (const [target, item] of Object.entries(facts)) {
    const team = target.slice(0, 2) === perspective ? 'self_team' : 'opponent_team';
    if (team === 'self_team' && ambiguous.has(target) && target !== ownedAppearanceForItems(prefix, perspective)) continue;
    const bound = team === 'self_team' ? boundOwnedTarget(prefix, perspective, view, request, target) : target;
    const matching = rows.filter(({row}) => typeof row?.ident === 'string' && ident(row.ident) === bound);
    if (matching.length !== 1 || matching[0].team !== team) fail(`${target} requires exactly one ${team} row`);
    const row = matching[0].row;
    if (team === 'opponent_team') {
      if (item === null ? 'item' in row : row.item !== 'has-item') fail(`${target} public presence disagrees with ordered item evidence`);
    } else {
      const owner = owners.find((entry) => 'item' in entry && ident(String(entry.ident)) === bound);
      const expected = owner ? owner.item || null : item;
      if (expected === null ? row.item !== null : expected ? row.item !== expected : !row.item) fail(`${target} owned item disagrees with evidence`);
      if (owner && (item === null ? !!owner.item : !owner.item || item && owner.item !== item)) fail(`${target} request/public item disagree`);
    }
  }
  for (const [target, state] of Object.entries(dispositions)) if (target.slice(0, 2) === perspective && (!ambiguous.has(target) || target === ownedAppearanceForItems(prefix, perspective))) {
    const bound = boundOwnedTarget(prefix, perspective, view, request, target);
    const row = rows.find(({team, row}) => team === 'self_team' && ident(String(row.ident)) === bound)?.row;
    if (!row || row.item_state !== state.item_state || state.last_item !== undefined && row.last_item !== state.last_item) fail(`${target} owned disposition/last item disagrees with public writer`);
    if (row?.item_suppressed !== magicRoom) fail(`${target} owned item suppression disagrees with public Magic Room evidence`);
  }
  for (const {team, row} of rows) if (team === 'self_team' && 'item_suppressed' in row && row.item_suppressed !== magicRoom) fail('owned item suppression disagrees with public Magic Room evidence');
  for (const {team, row} of rows) if (team === 'opponent_team' && 'item' in row && row.item !== 'has-item') fail('opponent item field may only publish an evidenced presence marker');
  for (const {team, row} of rows) if (team === 'opponent_team' && row.item === 'has-item'
    && (facts[ident(String(row.ident))] === undefined || facts[ident(String(row.ident))] === null)) fail('opponent presence has no eligible public item witness');
  const terminalItems = terminalOwnedItems(view);
  const terminalHistory = terminalOwnedItemHistory(view);
  if (terminalHistory) for (const [target, history] of Object.entries(terminalHistory)) {
    const matching = rows.filter(({team, row}) => team === 'self_team' && ident(String(row?.ident)) === target);
    if (matching.length !== 1 || matching[0].row.last_item !== history.last_item || matching[0].row.item_state !== history.item_state) fail(`terminal owned item history disagrees with committed predecessor and public writers: ${target} ${matching[0]?.row.item_state}/${matching[0]?.row.last_item} expected ${history.item_state}/${history.last_item}`);
  }
  if (terminalItems) for (const [target, item] of Object.entries(terminalItems)) {
    const matching = rows.filter(({team, row}) => team === 'self_team' && ident(String(row?.ident)) === target);
    if (matching.length !== 1 || matching[0].row.item !== item) fail(`terminal owned item disagrees with committed predecessor and public writers: ${target} ${matching[0]?.row.item} expected ${item}`);
  }
  for (const owner of owners.filter((entry) => 'item' in entry)) {
    const matching = rows.filter(({team, row}) => team === 'self_team' && ident(String(row?.ident)) === ident(String(owner.ident)));
    if (matching.length !== 1 || matching[0].row.item !== (owner.item || null)) fail('owned item requires exactly one matching addressed-request row');
    if (owner.item && matching[0].row.item_state !== 'held') fail('owned held item requires held disposition');
    if (!owner.item && matching[0].row.item_state === 'held') fail('owned absent item cannot assert held disposition');
    if (matching[0].row.item_suppressed !== magicRoom) fail('owned item suppression requires public Magic Room evidence');
  }
}

/** Existing flat disposition fields only; suppression is the extractor's public Magic Room flag. */
export function projectPublicItemDispositions(prefix: readonly string[]): Record<string, {item_state: string; last_item?: string}> {
  const states: Record<string, {item_state: string; last_item?: string}> = {};
  const active: Record<string, string> = {}, prior: Record<string, {item_state: string; last_item?: string} | undefined> = {};
  for (const line of prefix) {
    const parts = line.split('|'), target = ident(parts[2] || ''), side = target.slice(0, 2);
    if (!/^p[12]: .+/.test(target)) continue;
    if (parts[1] === 'switch' || parts[1] === 'drag') {
      prior[side] = states[target]; active[side] = target; delete states[target];
    } else if (parts[1] === 'replace') {
      const appearance = active[side];
      if (appearance && appearance !== target) {
        if (states[appearance]) states[target] = states[appearance]; else delete states[target];
        if (prior[side]) states[appearance] = prior[side]!; else delete states[appearance];
      }
      active[side] = target;
    } else if (['-item', 'item', '-enditem', 'enditem'].includes(parts[1])) {
      const item = parts[3].toLowerCase().replace(/[^a-z0-9]/g, '');
      const end = parts[1] === '-enditem' || parts[1] === 'enditem';
      const consumed = parts.slice(4).some((tag) => tag.includes('[eat]') || tag.includes('[from] gem'))
        || parts.length === 4 && item !== 'airballoon';
      states[target] = {...states[target], item_state: end ? consumed ? 'consumed' : 'removed' : 'held', ...(end ? {last_item: item} : {})};
    }
  }
  return states;
}

/** Historical end-item assertions do not infer current possession after a fresh appearance. */
function replayPublicItemHistory(prefix: readonly string[], ambiguousCarriers = false) {
  const history: Record<string, {item_state: string; last_item: string}> = {};
  const active: Record<string, string> = {}, touched: Record<string, boolean> = {}, prior: Record<string, typeof history[string] | undefined> = {};
  const revealed: Record<string, boolean> = {};
  if (!prefix.some((line) => line.startsWith('|-enditem|') || line.startsWith('|enditem|'))) return {history, active, touched, prior};
  for (const line of prefix) {
    const parts = line.split('|'), target = ident(parts[2] || ''), side = target.slice(0, 2);
    if (!/^p[12]: .+/.test(target)) continue;
    if (['switch', 'drag'].includes(parts[1])) {
      const departed = active[side];
      if (ambiguousCarriers && departed && touched[side] && !revealed[side]) {
        if (prior[side]) history[departed] = prior[side]!; else delete history[departed];
      }
      active[side] = target; prior[side] = history[target]; touched[side] = false; revealed[side] = false;
    }
    else if (parts[1] === 'replace') {
      const appearance = active[side];
      if (touched[side] && appearance && appearance !== target) {
        history[target] = history[appearance];
        if (prior[side]) history[appearance] = prior[side]!; else delete history[appearance];
      }
      active[side] = target; touched[side] = false; revealed[side] = true;
    } else if (['-enditem', 'enditem'].includes(parts[1])) {
      const item = parts[3].toLowerCase().replace(/[^a-z0-9]/g, '');
      const consumed = parts.slice(4).some((tag) => tag.includes('[eat]') || tag.includes('[from] gem')) || parts.length === 4 && item !== 'airballoon';
      history[target] = {item_state: consumed ? 'consumed' : 'removed', last_item: item};
      if (active[side] === target) touched[side] = true;
    }
  }
  return {history, active, touched, prior};
}

export function projectPublicItemHistory(prefix: readonly string[]): Record<string, {item_state: string; last_item: string}> {
  return replayPublicItemHistory(prefix).history;
}

export function projectPublicOwnedItemHistory(prefix: readonly string[], perspective: string, bindOwned: (target: string) => string, owners: Row[] = []): Record<string, {item_state: string; last_item: string}> {
  const {history, active, touched, prior} = replayPublicItemHistory(prefix, owners.some((row) => row.ability === 'illusion' || row.base_ability === 'illusion'));
  const appearance = active[perspective], actual = touched[perspective] && appearance && bindOwned(appearance);
  if (touched[perspective] && actual && actual !== appearance) {
    history[actual] = history[appearance];
    if (prior[perspective]) history[appearance] = prior[perspective]!; else delete history[appearance];
  }
  return history;
}
