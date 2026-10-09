import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { validateRawProtocolRecord } from '../src/observable_state';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import { PlayerStateExtractor } from '../src/state_extractor';
import type { PlayerID } from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;
function team(text: string) { return Teams.import(text)!; }
function choices(actor: PlayerID, actorChoice: string, foeChoice: string): Record<PlayerID, string> {
  return actor === 'p1' ? {p1: actorChoice, p2: foeChoice} : {p1: foeChoice, p2: actorChoice};
}
function battle(actor: PlayerID): Battle {
  const setter = team(`Setter (Skarmory)\nAbility: Sturdy\n- Spikes\n- Stealth Rock\n- Splash\n\nReserve (Eevee)\nAbility: Run Away\n- Splash\n`);
  const spinner = team(`Spinner (Forretress)\nAbility: Sturdy\n- Rapid Spin\n- Splash\n\nReserve (Eevee)\nAbility: Run Away\n- Splash\n`);
  const result = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  result.setPlayer('p1', {name: 'One', team: actor === 'p1' ? setter : spinner});
  result.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? setter : spinner});
  return result;
}

type SwitchInConsequence = {
  id: 'stealthrock' | 'stickyweb' | 'toxicspikes';
  move: 'Stealth Rock' | 'Sticky Web' | 'Toxic Spikes';
  layers: number;
  reserve: 'Charizard' | 'Eevee';
  status?: 'psn' | 'tox';
  stickyWeb?: boolean;
};

// Each setter/move pair is a direct generated Gen 9 Random Battle root:
// Skarmory's support rows contain Stealth Rock, while Ariados has both Sticky
// Web and Toxic Spikes. The later switch is performed by the real pipeline.
function consequenceBattle(actor: PlayerID, scenario: SwitchInConsequence): Battle {
  const setterSpecies = scenario.move === 'Stealth Rock' ? 'Skarmory' : 'Ariados';
  const setter = team(`Setter (${setterSpecies})\nAbility: ${setterSpecies === 'Skarmory' ? 'Sturdy' : 'Insomnia'}\n- ${scenario.move}\n- Splash\n`);
  const target = team(`Lead (Eevee)\nAbility: Run Away\n- Splash\n\nReserve (${scenario.reserve})\nAbility: ${scenario.reserve === 'Charizard' ? 'Blaze' : 'Run Away'}\n- Splash\n`);
  const result = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  result.setPlayer('p1', {name: 'One', team: actor === 'p1' ? setter : target});
  result.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? setter : target});
  const setup = choices(actor, 'move 1', 'move 1');
  for (let index = 0; index < scenario.layers; index += 1) result.makeChoices(setup.p1, setup.p2);
  return result;
}
async function sessions(serialized: Record<string, unknown>, actor: PlayerID): Promise<[Session, Session]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(structuredClone(serialized), options); };
    return await Promise.all([0, 1].map(() => createPipelineIntegrationSession({
      battle_id: `hazard-${actor}`, format: 'gen9randombattle', seed: [1, 2, 3, 4], observation_schema_version: 'observable-battle-state/v2',
    }))) as [Session, Session];
  } finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
}
function select(session: Session, player: PlayerID, choice: string) {
  const request = session.boundary.perspectives[player].observation.request!;
  const action = request.legal_actions.actions.find(item => item?.choice === choice);
  assert.ok(action, `${player} must own ${choice}`);
  return canonicalActionFromLegalAction(request, action.index);
}
async function step(session: Session, choices_: Record<PlayerID, string>) {
  return session.step({p1: select(session, 'p1', choices_.p1), p2: select(session, 'p2', choices_.p2)});
}
function python(bundle: unknown) {
  return spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {input: JSON.stringify(bundle), encoding: 'utf8', env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')}});
}

// The cap witnesses use pinned Battle mechanics directly. The later v2 test
// consumes the same public protocol through the real pipeline.
test('pinned entry-hazard caps, duplicate failures, removal, and switch-in consequences', () => {
  const direct = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  direct.setPlayer('p1', {name: 'One', team: team(`Setter (Skarmory)\nAbility: Sturdy\n- Spikes\n- Stealth Rock\n- Splash\n\nPoison (Muk)\nAbility: Stench\n- Splash\n`)});
  direct.setPlayer('p2', {name: 'Two', team: team(`Layer (Ariados)\nAbility: Insomnia\n- Toxic Spikes\n- Sticky Web\n- Splash\n\nSpinner (Forretress)\nAbility: Sturdy\n- Rapid Spin\n- Splash\n`)});
  try {
    for (let index = 0; index < 3; index += 1) direct.makeChoices('move 1', 'move 1');
    assert.equal(direct.sides[1].sideConditions.spikes.layers, 3);
    const spikeStarts = direct.log.filter(line => line === '|-sidestart|p2: Two|Spikes').length;
    direct.makeChoices('move 1', 'move 1');
    assert.equal(direct.log.filter(line => line === '|-sidestart|p2: Two|Spikes').length, spikeStarts, 'fourth Spikes emits no start');
    assert.equal(direct.sides[0].sideConditions.toxicspikes.layers, 2);
    assert.equal(direct.log.filter(line => line === '|-sidestart|p1: One|move: Toxic Spikes').length, 2);
    direct.makeChoices('move 2', 'move 2');
    assert.ok(direct.sides[1].sideConditions.stealthrock);
    assert.ok(direct.sides[0].sideConditions.stickyweb);
    direct.makeChoices('move 2', 'move 2');
    assert.equal(direct.log.filter(line => line === '|-sidestart|p2: Two|move: Stealth Rock').length, 1);
    assert.equal(direct.log.filter(line => line === '|-sidestart|p1: One|move: Sticky Web').length, 1);
    direct.makeChoices('move 3', 'switch 2');
    assert.ok(direct.log.some(line => line.startsWith('|-damage|p2a: Spinner|') && line.includes('[from] Spikes')));
    direct.makeChoices('move 3', 'move 1');
    for (const hazard of ['Spikes', 'Stealth Rock']) assert.ok(direct.log.some(line => line === `|-sideend|p2: Two|${hazard}|[from] move: Rapid Spin|[of] p2a: Spinner`));
    assert.equal(direct.sides[1].sideConditions.spikes, undefined);
    assert.equal(direct.sides[1].sideConditions.stealthrock, undefined);
    direct.makeChoices('switch 2', 'move 2');
    assert.ok(direct.log.some(line => line === '|-sideend|p1: One|move: Toxic Spikes|[of] p1a: Poison'));
    assert.equal(direct.sides[0].sideConditions.toxicspikes, undefined);
  } finally { direct.destroy(); }
});

test('pinned Mortal Spin, Defog, and Tidy Up retain their distinct public removal forms', () => {
  const removers = [
    {name: 'Mortal Spin', expected: '[from] move: Mortal Spin|[of] p2a: Remover'},
    {name: 'Defog', expected: '[from] move: Defog|[of] p2a: Remover'},
    {name: 'Tidy Up', expected: ''},
  ];
  for (const {name, expected} of removers) {
    const direct = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    direct.setPlayer('p1', {name: 'One', team: team(`Setter (Quagsire)
Ability: Unaware
- Spikes
- Splash
`)});
    direct.setPlayer('p2', {name: 'Two', team: team(`Remover (${name === 'Tidy Up' ? 'Maushold' : 'Glimmora'})
Ability: Sturdy
- ${name}
- Splash
`)});
    try {
      direct.makeChoices('move 1', 'move 2');
      direct.makeChoices('move 2', 'move 1');
      const suffix = expected ? `|${expected}` : '';
      assert.ok(direct.log.some(line => line === `|-sideend|p2: Two|Spikes${suffix}`), name);
      assert.equal(direct.sides[1].sideConditions.spikes, undefined);
    } finally { direct.destroy(); }
  }
});

for (const actor of PLAYERS) {
  test(`entry hazards ${actor}: public v2 layers, Rapid Spin clear, restoration, rollback, and publication`, async () => {
    const direct = battle(actor);
    const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor);
    const target = actor === 'p1' ? 'p2' : 'p1';
    try {
      const start = choices(actor, 'move 1', 'move 2');
      direct.makeChoices(start.p1, start.p2);
      const result = await step(session, start); const twinResult = await step(twin, start);
      assert.equal(result.transition_id, twinResult.transition_id);
      assert.equal(result.boundary.state_fingerprint, twinResult.boundary.state_fingerprint);
      for (const player of PLAYERS) {
        const observation = result.boundary.perspectives[player].observation;
        const side = player === target ? observation.view.field.side_conditions.self : observation.view.field.side_conditions.opponent;
        assert.equal(side.spikes, 1);
        assert.ok(observation.protocol_prefix.includes(`|-sidestart|${target}: ${target === 'p1' ? 'One' : 'Two'}|Spikes`));
        assert.ok(!JSON.stringify(observation).includes('sourceSlot'));
        assert.ok(!JSON.stringify(observation).includes('sideConditions'));
        assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|')));
      }
      const snapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
      const [restored] = await sessions(snapshot, actor);
      assert.equal(restored.boundary.state_fingerprint, result.boundary.state_fingerprint);
      const frozen = JSON.stringify(session.boundary);
      const stale = {p1: select(session, 'p1', choices(actor, 'move 2', 'move 1').p1), p2: select(session, 'p2', choices(actor, 'move 2', 'move 1').p2)};
      await assert.rejects(session.step({...stale, [actor]: {...stale[actor], rqid: 999}}), /request ID does not match/);
      assert.equal(JSON.stringify(session.boundary), frozen);
      const clear = choices(actor, 'move 2', 'move 1');
      direct.makeChoices(clear.p1, clear.p2);
      const cleared = await step(session, clear); const clearedTwin = await step(twin, clear); const clearedRestored = await step(restored, clear);
      assert.equal(cleared.transition_id, clearedTwin.transition_id);
      assert.equal(cleared.boundary.state_fingerprint, clearedRestored.boundary.state_fingerprint);
      for (const player of PLAYERS) {
        const observation = cleared.boundary.perspectives[player].observation;
        const side = player === target ? observation.view.field.side_conditions.self : observation.view.field.side_conditions.opponent;
        assert.equal(side.spikes, undefined);
        assert.ok(observation.protocol_prefix.some(record => record === `|-sideend|${target}: ${target === 'p1' ? 'One' : 'Two'}|Spikes|[from] move: Rapid Spin|[of] ${target}a: Spinner`));
        for (const bundle of Object.values(cleared.record_bundles)) assert.equal(python(bundle).status, 0);
      }
      await restored.close();
    } finally { direct.destroy(); await session.close(); await twin.close(); }
  });
}

const SWITCH_IN_CONSEQUENCES: readonly SwitchInConsequence[] = [
  {id: 'stealthrock', move: 'Stealth Rock', layers: 1, reserve: 'Charizard'},
  {id: 'stickyweb', move: 'Sticky Web', layers: 1, reserve: 'Eevee', stickyWeb: true},
  {id: 'toxicspikes', move: 'Toxic Spikes', layers: 1, reserve: 'Eevee', status: 'psn'},
  {id: 'toxicspikes', move: 'Toxic Spikes', layers: 2, reserve: 'Eevee', status: 'tox'},
];

for (const actor of PLAYERS) {
  for (const scenario of SWITCH_IN_CONSEQUENCES) {
    test(`entry hazards ${actor}: ${scenario.move} switch-in consequence is public, restorable, and publishable`, async () => {
      const direct = consequenceBattle(actor, scenario);
      const snapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
      const [session, twin] = await sessions(snapshot, actor);
      const target = actor === 'p1' ? 'p2' : 'p1';
      const transition = choices(actor, 'move 2', 'switch 2');
      try {
        direct.makeChoices(transition.p1, transition.p2);
        const result = await step(session, transition);
        const twinResult = await step(twin, transition);
        const [restored] = await sessions(snapshot, actor);
        const restoredResult = await step(restored, transition);
        assert.equal(result.transition_id, twinResult.transition_id);
        assert.equal(result.transition_id, restoredResult.transition_id);
        assert.equal(result.boundary.state_fingerprint, twinResult.boundary.state_fingerprint);
        assert.equal(result.boundary.state_fingerprint, restoredResult.boundary.state_fingerprint);

        const sideName = target === 'p1' ? 'One' : 'Two';
        for (const player of PLAYERS) {
          const observation = result.boundary.perspectives[player].observation;
          const targetTeam = player === target ? observation.view.self_team : observation.view.opponent_team;
          const reserve = targetTeam.find(pokemon => pokemon.active);
          assert.ok(reserve, `${player} sees the switched-in reserve`);
          const side = player === target ? observation.view.field.side_conditions.self : observation.view.field.side_conditions.opponent;
          assert.equal(side[scenario.id], scenario.layers);
          assert.ok(!JSON.stringify(observation).includes('sourceSlot'));
          assert.ok(!JSON.stringify(observation).includes('sideConditions'));
          assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|')));

          if (scenario.id === 'stealthrock') {
            const damage = observation.protocol_prefix.find(record => record.startsWith(`|-damage|${target}a: Reserve|`) && record.endsWith('|[from] Stealth Rock'));
            assert.ok(damage, 'Stealth Rock emits source-shaped public damage');
            assert.equal(damage.split('|').length, 5, 'Stealth Rock damage has no extra tags');
            assert.ok((reserve.hp_ratio ?? 1) < 1, 'public HP reflects Stealth Rock damage');
          }
          if (scenario.stickyWeb) {
            assert.ok(observation.protocol_prefix.includes(`|-activate|${target}a: Reserve|move: Sticky Web`));
            assert.ok(observation.protocol_prefix.includes(`|-unboost|${target}a: Reserve|spe|1`));
            if (player === target) assert.equal(reserve.boosts?.spe, -1);
            else assert.equal(reserve.public_boosts?.spe, -1);
          }
          if (scenario.status) {
            assert.equal(reserve.status, scenario.status);
            assert.ok(observation.protocol_prefix.includes(`|-status|${target}a: Reserve|${scenario.status}`));
          }
        }

        for (const bundle of Object.values(result.record_bundles)) assert.equal(python(bundle).status, 0);
        const frozen = JSON.stringify(session.boundary);
        const stale = {p1: select(session, 'p1', transition.p1), p2: select(session, 'p2', transition.p2)};
        await assert.rejects(session.step({...stale, [target]: {...stale[target], rqid: 999}}), /request ID does not match/);
        assert.equal(JSON.stringify(session.boundary), frozen);
        await restored.close();
      } finally { direct.destroy(); await session.close(); await twin.close(); }
    });
  }
}

test('entry-hazard protocol forms reject before extractor mutation', () => {
  const invalid = [
    '|-sidestart|p1: One|move: Spikes', '|-sidestart|p1a: One|Spikes',
    '|-sideend|p1: One|Spikes|[from] move: Court Change|[of] p1a: One',
    '|-sideend|p1: One|Stealth Rock|[from] move: Rapid Spin|[of] p1: One',
    '|-sidestart|p1: One|Spikes|[from] move: Spikes',
  ];
  for (const record of invalid) assert.throws(() => validateRawProtocolRecord(record));
  const extractor = new PlayerStateExtractor('hazard-cap', 'gen9randombattle', 'p1');
  extractor.consumeChunk(['|-sidestart|p1: One|Spikes', '|-sidestart|p1: One|Spikes', '|-sidestart|p1: One|Spikes'].join('\n'));
  const before = JSON.stringify(extractor.getView());
  assert.throws(() => extractor.consumeChunk('|-sidestart|p1: One|Spikes'));
  assert.equal(JSON.stringify(extractor.getView()), before);
});
