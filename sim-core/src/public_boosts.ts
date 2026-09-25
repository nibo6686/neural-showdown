// Public-prefix-only evidence. Null is unknown; zero requires a public baseline.
export const PUBLIC_BOOST_KEYS = ['atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion'] as const;
export type PublicBoosts = Record<(typeof PUBLIC_BOOST_KEYS)[number], number | null>;
const filled = (value: number | null): PublicBoosts => Object.fromEntries(PUBLIC_BOOST_KEYS.map(k => [k, value])) as PublicBoosts;
export function publicBoostEvidence(prefix: readonly string[]): Map<string, PublicBoosts> {
  const roster = new Map<string, PublicBoosts>();
  const active: Record<string, { key: string; stages: PublicBoosts; prior?: PublicBoosts }> = {};
  const key = (ident: string) => ident.replace(/^(p[12])[a-f]:/, '$1:');
  const side = (ident: string) => /^(p[12])[a-f]:/.exec(ident)?.[1];
  for (const line of prefix) {
    const p = line.split('|');
    const rawCommand = p[1];
    const cmd = ['boost', 'unboost', 'setboost', 'clearboost', 'clearallboost', 'clearnegativeboost', 'clearpositiveboost', 'copyboost', 'swapboost', 'invertboost', 'transform'].includes(rawCommand) ? `-${rawCommand}` : rawCommand;
    if (cmd === 'gametype' && p[2] !== 'singles') throw new Error('Unsupported public boost evidence: non-singles');
    // Validate even when the recipient cannot be routed to a player. Unresolved
    // roster identity is valid; missing or malformed protocol identity is not.
    if (cmd === '-copyboost' && (p.length !== 5 || p[4] !== '[from] move: Psych Up'
      || ![p[2], p[3]].every(id => typeof id === 'string' && /^p[12][a-z]:\s*[^|]+$/.test(id.trim())))) {
      throw new Error('Unsupported or malformed public boost copy evidence');
    }
    if (cmd === '-invertboost' && (p.length !== 4 || p[3] !== '[from] move: Topsy-Turvy'
      || !/^p[12][a-z]:\s*[^|]+$/.test((p[2] || '').trim()))) {
      throw new Error('Unsupported or malformed public stage inversion evidence');
    }
    const id = p[2] || ''; const player = side(id);
    if (['-swapboost'].includes(cmd)
      || (cmd === 'move' && p[3] === 'Baton Pass')) throw new Error(`Unsupported public boost evidence: ${cmd}`);
    if (cmd === '-clearallboost') { for (const entry of Object.values(active)) { entry.stages = filled(0); roster.set(entry.key, { ...entry.stages }); } }
    if (!player) continue;
    let entry = active[player];
    if (cmd === 'switch' || cmd === 'drag') {
      if (entry) roster.set(entry.key, filled(0));
      const prior = roster.get(key(id));
      active[player] = entry = { key: key(id), stages: filled(0), ...(prior ? { prior: { ...prior } } : {}) };
    } else if (cmd === 'replace' && entry) {
      if (entry.key !== key(id)) {
        if (entry.prior) roster.set(entry.key, entry.prior); else roster.delete(entry.key);
        entry.key = key(id); delete entry.prior;
      }
    } else if (cmd === 'faint' || cmd === '-clearboost') {
      if (!entry) active[player] = entry = { key: key(id), stages: filled(null) };
      entry.stages = filled(0);
    }
    else if (cmd === '-clearnegativeboost' || cmd === '-clearpositiveboost') {
      if (!entry) active[player] = entry = { key: key(id), stages: filled(null) };
      for (const stat of PUBLIC_BOOST_KEYS) {
        const stage = entry.stages[stat];
        if (stage !== null && (cmd === '-clearpositiveboost' ? stage > 0 : stage < 0)) entry.stages[stat] = 0;
      }
    }
    else if (cmd === '-invertboost') {
      if (!entry) active[player] = entry = { key: key(id), stages: filled(null) };
      entry.stages = Object.fromEntries(PUBLIC_BOOST_KEYS.map(stat => {
        const value = entry!.stages[stat];
        return [stat, value === null || value === 0 ? value : -value];
      })) as PublicBoosts;
    }
    else if (cmd === '-copyboost') {
      if (!entry) active[player] = entry = { key: key(id), stages: filled(null) };
      entry.stages = { ...(active[side(p[3]) || '']?.stages || filled(null)) };
    }
    else if (entry && cmd === '-transform') entry.stages = { ...(active[side(p[3] || '') || '']?.stages || filled(null)) };
    else if (['-boost', '-unboost', '-setboost'].includes(cmd)) {
      if (!entry) active[player] = entry = { key: key(id), stages: filled(null) };
      const stat = p[3] as keyof PublicBoosts; const amount = Number(p[4]);
      if (!/^-?\d+$/.test(p[4] || '') || (cmd !== '-setboost' && amount < 0) || !PUBLIC_BOOST_KEYS.includes(stat) || !Number.isInteger(amount) || Math.abs(amount) > (cmd === '-setboost' ? 6 : 12)) throw new Error('Malformed public boost evidence');
      if (cmd === '-setboost') entry.stages[stat] = amount;
      else if (entry.stages[stat] !== null) entry.stages[stat] = Math.max(-6, Math.min(6, entry.stages[stat]! + (cmd === '-unboost' ? -amount : amount)));
    }
    // Flush active entries too: clearallboost changes every active map.
    for (const current of Object.values(active)) roster.set(current.key, { ...current.stages });
  }
  return roster;
}
export function opponentPublicBoosts(prefix: readonly string[], ident: string): PublicBoosts {
  return { ...(publicBoostEvidence(prefix).get(ident.replace(/^(p[12])[a-f]:/, '$1:')) || filled(null)) };
}
