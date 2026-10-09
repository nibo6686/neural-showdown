import assert from 'node:assert/strict';
import test from 'node:test';
import { Battle, Dex, Teams } from 'pokemon-showdown';
import { publicGasSources, abilityEffectiveness } from '../src/public_ability';
import { assertPublicHealthMatchesEvidence, projectPublicHealth } from '../src/public_health';
import { LocalBattleEnv } from '../src/env_manager';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { assertRehashedUnsupportedGasRecord, assertTerminalIdentityTamperMatrix } from './public_consequence_test_helpers';
import type { PlayerID } from '../src/types';
import { HeuristicBaselineAgent } from '../src/baselines/heuristic';

const source = '|switch|p1a: One|Snorlax, L80|100/100';
const writers = [
  ['damage', ['|-damage|p1a: One|42/100 brn']],
  ['heal', ['|-heal|p1a: One|86/100']],
  ['sethp', ['|-sethp|p1a: One|50/100|[from] move: Pain Split']],
  ['status', ['|-status|p1a: One|par']],
  ['cure', ['|-status|p1a: One|brn', '|-curestatus|p1a: One|brn']],
  ['faint', ['|-status|p1a: One|brn', '|-damage|p1a: One|0 fnt', '|faint|p1a: One']],
  ['order', ['|-damage|p1a: One|42/100 brn', '|-heal|p1a: One|100/100']],
  ['drag', ['|drag|p1a: Two|Eevee, L80|76/100 par']],
  ['replace', ['|replace|p1a: Actual|Zoroark, L80|100/100']],
  ['Wish', ['|-heal|p1a: One|100/100|[from] move: Wish|[wisher] Source']],
  ['Healing Wish', ['|-status|p1a: One|brn', '|-heal|p1a: One|100/100|[from] move: Healing Wish']],
  ['Revival', ['|-damage|p1a: One|0 fnt', '|faint|p1a: One', '|-heal|p1: One|50/100|[from] move: Revival Blessing']],
  ['Future Sight', ['|-damage|p1a: One|42/100']],
] as const;

for (const [writer, suffix] of writers) test(`public health ${writer}: last writer, omissions, false fields and wrong side`, () => {
  const prefix = [source, ...suffix];
  const health = projectPublicHealth(prefix);
  const self = Object.entries(health).map(([ident, facts]) => ({ident, ...facts}));
  const view = {self_team: self, opponent_team: []};
  assert.doesNotThrow(() => assertPublicHealthMatchesEvidence(prefix, 'p1', view, null));
  for (const row of self) for (const key of ['hp_text', 'hp_ratio', 'status', 'fainted', 'active']) {
    if (!(key in row)) continue;
    const omitted = structuredClone(view);
    delete (omitted.self_team.find((p) => p.ident === row.ident)! as Record<string, unknown>)[key];
    assert.throws(() => assertPublicHealthMatchesEvidence(prefix, 'p1', omitted, null), /Public health/);
  }
  assert.throws(() => assertPublicHealthMatchesEvidence(prefix, 'p1', {self_team: [], opponent_team: self}, null), /exactly one/);
  assert.throws(() => assertPublicHealthMatchesEvidence(prefix, 'p1', {}, null), /exactly one/);
});

test('Gas source replay tracks simultaneous sources and departure without requiring End', () => {
  const p1 = '|switch|p1a: GasOne|Weezing, L80|100/100';
  const p2 = '|switch|p2a: GasTwo|Weezing, L80|100/100';
  const prefix = [p1, '|-ability|p1a: GasOne|Neutralizing Gas', p2, '|-ability|p2a: GasTwo|Neutralizing Gas'];
  assert.equal(publicGasSources(prefix).size, 2);
  assert.deepEqual([...publicGasSources([...prefix, '|switch|p1a: Bench|Eevee, L80|100/100'])], ['p2: GasTwo']);
  assert.equal(publicGasSources([...prefix, '|faint|p1a: GasOne', '|-end|p2a: GasTwo|ability: Neutralizing Gas']).size, 0);
});

test('Gas respects pinned exemption precedence and preserves unknown opponent exemption', () => {
  const row = {active: true, fainted: false, ability: 'intimidate', transformed: false, ability_suppressed: false};
  assert.equal(abilityEffectiveness(row, true, null, true), 'suppressed');
  assert.equal(abilityEffectiveness(row, true, null, false), 'unknown');
  assert.equal(abilityEffectiveness(row, true, 'abilityshield', true), 'active');
  assert.equal(abilityEffectiveness({...row, ability_suppressed: true}, true, 'abilityshield', true), 'suppressed');
  assert.equal(abilityEffectiveness({...row, ability: 'iceface', ability_suppressed: true}, true, null, true), 'active');
  assert.equal(abilityEffectiveness({...row, ability: 'neutralizinggas'}, true, null, true), 'active');
  assert.equal(abilityEffectiveness({...row, ability: 'neutralizinggas', transformed: true}, true, null, true), 'suppressed');
  assert.equal(abilityEffectiveness({...row, ability: null}, true, null, true), 'unknown');
});

async function sessionFor(battle: Battle, id: string) {
  const snapshot = structuredClone(battle.toJSON());
  const original = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(structuredClone(snapshot), options); };
    return await createPipelineIntegrationSession({battle_id: id, format: 'gen9randombattle', seed: [1,2,3,4], observation_schema_version: 'observable-battle-state/v2'});
  } finally { LocalBattleEnv.prototype.resetWithOptions = original; }
}
function select(session: Awaited<ReturnType<typeof sessionFor>>, player: PlayerID, choice: string) {
  const request = session.boundary.perspectives[player].observation.request!;
  const action = request.legal_actions.actions.find((entry) => entry?.choice === choice)!;
  assert.ok(action);
  return canonicalActionFromLegalAction(request, action.index);
}

for (const actor of ['p1', 'p2'] as const) for (const mode of ['departure', 'faint', 'illusion'] as const) {
  test(`constructed pinned Gas ${actor} ${mode}: name, effective state, restoration and unsupported publication`, async () => {
    const own = Teams.import(`Lead (Eevee)\nAbility: Run Away\n- Splash\n\nGas (Weezing)\n${mode === 'faint' ? 'Level: 1\n' : ''}Ability: Neutralizing Gas\n- Splash`)!;
    const foe = mode === 'illusion' ? Teams.import('Actual (Zoroark)\nAbility: Illusion\n- Splash\n\nDisguise (Snorlax)\nAbility: Immunity\n- Splash')!
      : Teams.import('Foe (Arcanine)\nAbility: Intimidate\n- Splash\n- Earthquake')!;
    const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    battle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? own : foe});
    battle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? own : foe});
    const snapshot = structuredClone(battle.toJSON());
    const restored = Battle.fromJSON(structuredClone(snapshot));
    const session = await sessionFor(battle, `gas-${actor}-${mode}`);
    try {
      const other = actor === 'p1' ? 'p2' : 'p1';
      const idle = await session.step({p1: select(session, 'p1', 'move 1'), p2: select(session, 'p2', 'move 1')});
      const choices = {[actor]: 'switch 2', [other]: mode === 'faint' ? 'move 2' : 'move 1'};
      battle.makeChoices(choices.p1, choices.p2);
      restored.makeChoices(choices.p1, choices.p2);
      assert.deepEqual(battle.toJSON(), restored.toJSON(), 'actual private engine restoration is deterministic');
      const prefix = battle.log;
      const gasRecord = `|-ability|${actor}a: Gas|Neutralizing Gas`;
      assert.ok(prefix.includes(gasRecord));
      assert.equal(battle[other].active[0].ability, mode === 'illusion' ? 'illusion' : 'intimidate', 'Gas retains known names');
      if (mode !== 'faint') {
        assert.equal(battle[other].active[0].ignoringAbility(), true);
        assert.equal(publicGasSources(prefix).size, 1);
        if (mode === 'illusion') assert.ok(prefix.some((line) => line.startsWith(`|replace|${other}a: Actual|`)));
      } else {
        assert.equal(publicGasSources(prefix).size, 0);
        assert.ok(prefix.includes(`|-end|${actor}a: Gas|ability: Neutralizing Gas`));
        assert.equal(battle[other].active[0].ignoringAbility(), false);
      }
      const before = JSON.stringify(session.boundary);
      await assert.rejects(session.step({p1: select(session, 'p1', choices.p1), p2: select(session, 'p2', choices.p2)}), /settling\/v1\/simulator-error/);
      assert.equal(JSON.stringify(session.boundary), before, 'unsupported Gas never commits');
      for (const player of ['p1', 'p2'] as const) assertRehashedUnsupportedGasRecord(idle.record_bundles[player], gasRecord);
      if (mode === 'departure') {
        const leave = {[actor]: 'switch 2', [other]: 'move 1'};
        battle.makeChoices(leave.p1, leave.p2);
        restored.makeChoices(leave.p1, leave.p2);
        assert.deepEqual(battle.toJSON(), restored.toJSON());
        assert.equal(publicGasSources(battle.log).size, 0);
        assert.equal(battle[other].active[0].ignoringAbility(), false);
      }
    } finally { battle.destroy(); restored.destroy(); await session.close(); }
  });
}

test('Gas and Shield are not authored Gen9 random-set/selector candidates', () => {
  const fs = require('node:fs'); const path = require('node:path');
  const root = path.dirname(require.resolve('pokemon-showdown/package.json'));
  const sets = JSON.parse(fs.readFileSync(path.join(root, 'data/random-battles/gen9/sets.json'), 'utf8'));
  assert.ok(!Object.values(sets).some((species: any) => species.sets.some((set: any) => set.abilities.some((a: string) => Dex.abilities.get(a).id === 'neutralizinggas'))));
  assert.ok(!fs.readFileSync(path.join(root, 'data/random-battles/gen9/teams.ts'), 'utf8').includes('Ability Shield'));
});

test('constructed two Gas sources restore deterministically and last departure alone ends global suppression', () => {
  const team = Teams.import('Gas (Weezing)\nAbility: Neutralizing Gas\n- Splash\n\nBench (Arcanine)\nAbility: Intimidate\n- Splash')!;
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team}); battle.setPlayer('p2', {name: 'Two', team});
  const restored = Battle.fromJSON(structuredClone(battle.toJSON()));
  try {
    assert.equal(publicGasSources(battle.log).size, 2);
    battle.makeChoices('switch 2', 'move 1'); restored.makeChoices('switch 2', 'move 1');
    assert.equal(publicGasSources(battle.log).size, 1);
    assert.equal(battle.p1.active[0].ability, 'intimidate');
    assert.equal(battle.p1.active[0].ignoringAbility(), true);
    assert.ok(!battle.log.includes('|-end|p1a: Gas|ability: Neutralizing Gas'));
    battle.makeChoices('move 1', 'switch 2'); restored.makeChoices('move 1', 'switch 2');
    assert.equal(publicGasSources(battle.log).size, 0);
    assert.equal(battle.p1.active[0].ignoringAbility(), false);
    assert.deepEqual(battle.toJSON(), restored.toJSON());
  } finally { battle.destroy(); restored.destroy(); }
});

for (const target of [
  {text: 'Foe (Arcanine) @ Ability Shield\nAbility: Intimidate\n- Splash', effective: true},
  {text: 'Foe (Eiscue)\nAbility: Ice Face\n- Splash', effective: true},
  {text: 'Foe (Regigigas)\nAbility: Slow Start\n- Splash', effective: false},
]) test(`constructed Gas exemption/silent-End source: ${target.text.split('\n')[0]}`, () => {
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: Teams.import('Lead (Eevee)\nAbility: Run Away\n- Splash\n\nGas (Weezing)\nAbility: Neutralizing Gas\n- Splash')!});
  battle.setPlayer('p2', {name: 'Two', team: Teams.import(target.text)!});
  try {
    battle.makeChoices('switch 2', 'move 1');
    assert.equal(!battle.p2.active[0].ignoringAbility(), target.effective);
    if (target.text.includes('Slow Start')) assert.ok(battle.log.includes('|-end|p2a: Foe|Slow Start|[silent]'));
    battle.makeChoices('switch 2', 'move 1');
    assert.equal(battle.p2.active[0].ignoringAbility(), false);
    if (target.text.includes('Slow Start')) assert.equal(battle.log.filter((line) => line.startsWith('|-start|p2a: Foe|ability: Slow Start')).length, 2);
  } finally { battle.destroy(); }
});

test('Gas cannot enter the bounded ability graph through six form defaults or copy/transfer cycles', () => {
  const defaults = ['terashell', 'teraformzero', 'embodyaspectteal', 'embodyaspecthearthflame', 'embodyaspectwellspring', 'embodyaspectcornerstone'];
  assert.ok(defaults.every((ability) => Dex.abilities.get(ability).exists && ability !== 'neutralizinggas'));
  const gas = Dex.abilities.get('neutralizinggas');
  for (const flag of ['notrace', 'notransform', 'noentrain', 'failroleplay', 'failskillswap', 'noreceiver']) assert.ok(gas.flags[flag as keyof typeof gas.flags]);
  const fs = require('node:fs'); const path = require('node:path');
  const root = path.dirname(require.resolve('pokemon-showdown/package.json'));
  for (const file of ['data/moves.ts', 'data/abilities.ts', 'sim/pokemon.ts']) {
    assert.ok(!/setAbility\(['"]neutralizinggas['"]/.test(fs.readFileSync(path.join(root, file), 'utf8')));
  }
});

test('requestless public appearance binding cannot be redirected by a forged active row', () => {
  const prefix = ['|switch|p1a: Carrier|Snorlax, L80|100/100'];
  const forged = {self_team: [{ident: 'p1: Other', active: true, hp_text: '100/100', hp_ratio: 1, status: null, fainted: false}], opponent_team: []};
  assert.throws(() => assertPublicHealthMatchesEvidence(prefix, 'p1', forged, null), /exactly one/);
});

test('effectiveness-dependent calculator consumers cannot reinstall a species default through cloning', () => {
  const agent = new HeuristicBaselineAgent();
  const row = {species: 'Arcanine', ability: 'Intimidate', hp_text: '100/100', hp_ratio: 1,
    stats: {}, boosts: {}, types: ['Fire'], moves: ['Flamethrower'], revealed_moves: [], status: null};
  for (const ability_effectiveness of ['suppressed', 'unknown']) {
    const calculated = (agent as any).buildCalcPokemon({...row, ability_effectiveness}, false);
    assert.equal(calculated.ability, 'No Ability');
    assert.equal(calculated.clone().ability, 'No Ability');
    assert.equal(row.ability, 'Intimidate', 'the known name is retained');
  }
  assert.equal((agent as any).buildCalcPokemon({...row, ability_effectiveness: 'active'}, false).ability, 'Intimidate');
});

test('living terminal Illusion has an authored generated ability and damaging-move root', () => {
  const fs = require('node:fs'); const path = require('node:path');
  const root = path.dirname(require.resolve('pokemon-showdown/package.json'));
  const sets = JSON.parse(fs.readFileSync(path.join(root, 'data/random-battles/gen9/sets.json'), 'utf8'));
  assert.ok(sets.zoroark.sets.some((set: any) => set.abilities.includes('Illusion') && set.movepool.includes('Dark Pulse')));
  assert.equal(Dex.moves.get('darkpulse').category, 'Special');
  assert.ok(Dex.moves.get('darkpulse').basePower > 0);
});

for (const actor of ['p1', 'p2'] as const) test(`live Illusion ${actor} terminal source retains validated predecessor owner identity`, async () => {
  const own = Teams.import('Actual (Zoroark)\nAbility: Illusion\n- Dark Pulse\n\nDisguise (Snorlax)\nAbility: Immunity\n- Splash')!;
  const foe = Teams.import('Foe (Eevee)\nLevel: 1\nAbility: Run Away\n- Splash')!;
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? own : foe});
  battle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? own : foe});
  const restored = Battle.fromJSON(structuredClone(battle.toJSON()));
  const session = await sessionFor(battle, `illusion-terminal-${actor}`);
  try {
    const input = session.boundary.perspectives[actor].observation;
    assert.equal(input.request!.side.find((p) => p.active)!.ident, `${actor}: Actual`);
    assert.ok(input.protocol_prefix.some((line) => line.startsWith(`|switch|${actor}a: Disguise|`)));
    battle.makeChoices('move 1', 'move 1'); restored.makeChoices('move 1', 'move 1');
    assert.equal(battle.ended, true);
    assert.deepEqual(battle.toJSON(), restored.toJSON());
    assert.ok(!battle.log.some((line) => line.startsWith(`|replace|${actor}a: Actual|`)));
    assert.ok(battle.log.some((line) => line.startsWith('|win|')));
    const result = await session.step({p1: select(session, 'p1', 'move 1'), p2: select(session, 'p2', 'move 1')});
    assert.equal(session.boundary.kind, 'terminal');
    const bundle = result.record_bundles[actor];
    assert.equal(bundle.successor_observation.request, null);
    assert.equal(bundle.successor_observation.view.self_team.find((row) => row.active)?.ident, `${actor}: Actual`);
    const other = actor === 'p1' ? 'p2' : 'p1';
    assert.equal(result.record_bundles[other].successor_observation.view.opponent_team.find((row) => row.active)?.ident, `${actor}a: Disguise`);
    assertTerminalIdentityTamperMatrix(bundle);
  } finally { battle.destroy(); restored.destroy(); await session.close(); }
});
