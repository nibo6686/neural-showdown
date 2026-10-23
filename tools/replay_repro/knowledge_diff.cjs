'use strict';
const {isDeepStrictEqual} = require('node:util');
const registry = require('../../docs/contracts/knowledge-coverage.json');
const {installedNativeProfile} = require('../../sim-core/dist/src/version_profile');
const {Teams} = require(installedNativeProfile().package_root);
const owners = ['p1', 'p2'], stats = ['atk', 'def', 'spa', 'spd', 'spe'];
const keyOf = row => [row.family, row.property, row.context, row.perspective].join('/');
const relevant = registry.rows.filter(r => r.status === 'adopted' || r.status === 'legitimately_unknown');

/** Offline read-only oracle. Simulator truth never enters projections or chosen actions. */
function createKnowledgeDiff(session) {
  const rows = Object.fromEntries(relevant.map(row => [keyOf(row), {checks: 0, unknown: 0, mismatches: 0}]));
  const examples = [], starting = {};
  const initial = session.environment.battleStream.battle;
  for (const owner of owners) {
    const evidence = session.readOriginalOwnerHolding(session.getOriginalOwnerHolding(owner), owner);
    starting[owner] = evidence.raw_team.map((raw, index) => {
      const set = Teams.unpack(Teams.pack([structuredClone(raw)]))[0];
      const species = initial.dex.species.get(set.species);
      const slots = session.readNativeObjectHolding(session.getNativeObjectHolding(owner), owner).original_slots;
      const nativeSet = initial[owner].pokemon[slots.indexOf(index + 1)].set;
      const calculated = initial.spreadModify(species.baseStats, nativeSet);
      return {roster_species: raw.species, starting_moves: raw.moves, item: raw.item || null, ability: raw.ability,
        submitted_nature: raw.nature ?? null, submitted_happiness: raw.happiness ?? null,
        shiny: raw.shiny ?? null, ball: raw.pokeball ?? null,
        starting_tera: set.teraType || species.types[0], level: set.level || 100,
        calculated_stats: Object.fromEntries(stats.map(stat => [stat, calculated[stat]])), hp_max: species.maxHP || calculated.hp};
    });
  }
  function mismatch(key, frame, fact, expected, reason) {
    rows[key].mismatches++;
    if (examples.length < 10) examples.push({row: key, owner: frame.owner, boundary: frame.step_index,
      subject: fact?.subject, projected: fact, expected, reason});
  }
  function compare(current, frames) {
    const battle = current.environment.battleStream.battle;
    for (const frame of frames) {
      const owner = frame.owner, projection = frame.knowledge.projection;
      const association = current.readNativeObjectHolding(current.getNativeObjectHolding(owner), owner);
      const roster = new Map(association.original_slots.map((slot, position) => [slot, battle[owner].pokemon[position]]));
      for (const row of relevant) {
        const key = keyOf(row), context = row.context === 'original' ? projection.starting : projection.current;
        const facts = context.filter(f => f.property === row.property && f.family === row.family
          && (row.perspective === 'own' ? f.owner === owner : f.owner !== owner));
        if (!facts.length) {
          if (row.status === 'adopted') mismatch(key, frame, null, null, 'adopted-row-missing');
          continue;
        }
        for (const fact of facts) {
          if (fact.state === 'unknown') {
            rows[key].unknown++;
            if (fact.value !== null) mismatch(key, frame, fact, null, 'fabricated-unknown-value');
            continue;
          }
          rows[key].checks++;
          if (row.status === 'legitimately_unknown') {mismatch(key, frame, fact, null, 'registry-unknown-value'); continue;}
          const slot = new RegExp(`^${owner}:roster:([1-6])$`).exec(fact.subject)?.[1];
          const actor = slot ? roster.get(Number(slot)) : undefined;
          let expected;
          if (row.property === 'roster_size') expected = starting[owner].length;
          else if (row.property === 'roster_order') expected = Number(slot);
          else if (row.context === 'original') expected = starting[owner][Number(slot) - 1]?.[row.property];
          else {
            if (!actor) {mismatch(key, frame, fact, null, 'foreign-or-unbound-subject'); continue;}
            const truth = {hp: actor.hp, fainted: actor.fainted, status: actor.status || null,
              ability: actor.ability || null, level: actor.level, gender: actor.gender || null,
              shiny: !!actor.set.shiny, ball: actor.pokeball, details: actor.details, hp_max: actor.maxhp,
              calculated_stats: Object.fromEntries(stats.map(stat => [stat, actor.baseStoredStats[stat]]))};
            expected = truth[row.property];
          }
          if (expected === undefined || !isDeepStrictEqual(fact.value?.data ?? null, expected)
            || (fact.state === 'known_absent') !== (expected === null)) mismatch(key, frame, fact, expected, 'truth-mismatch');
        }
      }
    }
  }
  return {compare, result: () => ({rows, checks: Object.values(rows).reduce((n, r) => n + r.checks, 0),
    mismatches: Object.values(rows).reduce((n, r) => n + r.mismatches, 0), examples})};
}
module.exports = {createKnowledgeDiff, keyOf};
