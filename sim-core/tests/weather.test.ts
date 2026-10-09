import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { validateRawProtocolRecord } from '../src/observable_state';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;
function team(text: string) { return Teams.import(text)!; }
function choices(actor: PlayerID, actorChoice: string, foeChoice: string): Record<PlayerID, string> {
  return actor === 'p1' ? {p1: actorChoice, p2: foeChoice} : {p1: foeChoice, p2: actorChoice};
}

// Ninetales/Drought, Golduck/Cloud Nine, Rain Dance, and the reserve switch
// are each generated Gen 9 Random Battle candidates. The fixture deliberately
// checks only public weather records: source/duration live in Field.weatherState.
function weatherBattle(actor: PlayerID): Battle {
  const weather = team(`Sun (Ninetales)
Ability: Drought
- Rain Dance
- Splash

Cloud (Golduck)
Ability: Cloud Nine
- Splash
`);
  const foe = team(`Foe (Eevee)
Ability: Run Away
- Splash

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  const result = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  result.setPlayer('p1', {name: 'One', team: actor === 'p1' ? weather : foe});
  result.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? weather : foe});
  return result;
}

async function sessions(serialized: Record<string, unknown>, actor: PlayerID): Promise<[Session, Session]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(structuredClone(serialized), options); };
    return await Promise.all([0, 1].map(() => createPipelineIntegrationSession({
      battle_id: `weather-${actor}`, format: 'gen9randombattle', seed: [1, 2, 3, 4],
      observation_schema_version: 'observable-battle-state/v2',
    }))) as [Session, Session];
  } finally { LocalBattleEnv.prototype.resetWithOptions = reset; }
}
function select(session: Session, player: PlayerID, choice: string) {
  const request = session.boundary.perspectives[player].observation.request!;
  const action = request.legal_actions.actions.find(candidate => candidate?.choice === choice);
  assert.ok(action, `${player} must own ${choice}`);
  return canonicalActionFromLegalAction(request, action.index);
}
async function step(session: Session, next: Record<PlayerID, string>) {
  return session.step({p1: select(session, 'p1', next.p1), p2: select(session, 'p2', next.p2)});
}
function python(bundle: unknown) {
  return spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(bundle), encoding: 'utf8',
    env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')},
  });
}
function assertPublicOnly(boundary: Awaited<ReturnType<typeof step>>['boundary']) {
  for (const player of PLAYERS) {
    const observation = boundary.perspectives[player].observation;
    const serialized = JSON.stringify(observation);
    assert.ok(!serialized.includes('weatherState') && !serialized.includes('sourceSlot') && !serialized.includes('duration'));
    assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|') || record.startsWith('|split|')));
  }
}

test('pinned weather emitters retain only the exact generated public lifecycle forms', () => {
  const abilities = [
    ['Pelipper', 'Drizzle', 'RainDance'], ['Ninetales', 'Drought', 'SunnyDay'],
    ['Tyranitar', 'Sand Stream', 'Sandstorm'], ['Abomasnow', 'Snow Warning', 'Snowscape'],
    ['Koraidon', 'Orichalcum Pulse', 'SunnyDay'],
  ] as const;
  for (const [species, ability, weather] of abilities) {
    const direct = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    direct.setPlayer('p1', {name: 'One', team: team(`Setter (${species})\nAbility: ${ability}\n- Splash\n`)});
    direct.setPlayer('p2', {name: 'Two', team: team('Foe (Eevee)\nAbility: Run Away\n- Splash\n')});
    try {
      assert.ok(direct.log.includes(`|-weather|${weather}|[from] ability: ${ability}|[of] p1a: Setter`));
    } finally { direct.destroy(); }
  }
  const direct = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  direct.setPlayer('p1', {name: 'One', team: team(`Mover (Ludicolo)\nAbility: Swift Swim\n- Rain Dance\n- Sunny Day\n- Snowscape\n- Splash\n`)});
  direct.setPlayer('p2', {name: 'Two', team: team('Foe (Eevee)\nAbility: Run Away\n- Splash\n')});
  try {
    direct.makeChoices('move 1', 'move 1');
    assert.ok(direct.log.includes('|-weather|RainDance'));
    assert.ok(direct.log.includes('|-weather|RainDance|[upkeep]'));
    for (let turn = 0; turn < 4; turn += 1) direct.makeChoices('move 4', 'move 1');
    assert.ok(direct.log.includes('|-weather|none'), 'duration expiry emits the only public clear record');
    direct.makeChoices('move 2', 'move 1');
    assert.ok(direct.log.includes('|-weather|SunnyDay'));
    direct.makeChoices('move 3', 'move 1');
    assert.ok(direct.log.includes('|-weather|Snowscape'));
    assert.equal(direct.field.weather, 'snowscape');
  } finally { direct.destroy(); }
});

for (const actor of PLAYERS) {
  test(`weather ${actor}: set, replace, suppress, restore, and publish only public weather`, async () => {
    const direct = weatherBattle(actor);
    const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor);
    let restored: Session | undefined;
    try {
      const opening = `|-weather|SunnyDay|[from] ability: Drought|[of] ${actor}a: Sun`;
      assert.ok(direct.log.includes(opening));
      for (const player of PLAYERS) {
        assert.equal(session.boundary.perspectives[player].observation.view.field.weather, 'sunnyday');
        assert.ok(session.boundary.perspectives[player].observation.protocol_prefix.includes(opening));
      }

      const rain = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(rain.p1, rain.p2);
      const rained = await step(session, rain);
      const rainedTwin = await step(twin, rain);
      assert.equal(rained.transition_id, rainedTwin.transition_id);
      assert.equal(rained.boundary.state_fingerprint, rainedTwin.boundary.state_fingerprint);
      assert.equal(direct.field.weather, 'raindance');
      for (const player of PLAYERS) {
        const observation = rained.boundary.perspectives[player].observation;
        assert.equal(observation.view.field.weather, 'raindance');
        assert.ok(observation.protocol_prefix.includes('|-weather|RainDance'));
        assert.ok(observation.protocol_prefix.includes('|-weather|RainDance|[upkeep]'));
      }
      assertPublicOnly(rained.boundary);

      const snapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
      [restored] = await sessions(snapshot, actor);
      assert.equal(restored.boundary.state_fingerprint, rained.boundary.state_fingerprint);
      const suppress = choices(actor, 'switch 2', 'move 1');
      direct.makeChoices(suppress.p1, suppress.p2);
      const suppressed = await step(session, suppress);
      const suppressedTwin = await step(twin, suppress);
      const suppressedRestored = await step(restored, suppress);
      assert.equal(suppressed.transition_id, suppressedTwin.transition_id);
      assert.equal(suppressed.boundary.state_fingerprint, suppressedTwin.boundary.state_fingerprint);
      assert.equal(suppressed.boundary.state_fingerprint, suppressedRestored.boundary.state_fingerprint);
      assert.equal(direct.field.weather, 'raindance');
      assert.equal(direct.field.effectiveWeather(), '');
      const reveal = `|-ability|${actor}a: Cloud|Cloud Nine`;
      for (const player of PLAYERS) {
        const observation = suppressed.boundary.perspectives[player].observation;
        assert.equal(observation.view.field.weather, 'raindance', 'suppression is not a public removal');
        assert.ok(observation.protocol_prefix.includes(reveal));
        assert.ok(!observation.protocol_prefix.includes('|-weather|none'));
        assert.equal(python(suppressed.record_bundles[player]).status, 0);
      }
      assertPublicOnly(suppressed.boundary);

      const frozen = JSON.stringify(session.boundary);
      const stale = {p1: select(session, 'p1', choices(actor, 'move 1', 'move 1').p1), p2: select(session, 'p2', choices(actor, 'move 1', 'move 1').p2)};
      await assert.rejects(session.step({...stale, [actor]: {...stale[actor], rqid: 999}}), /request ID does not match/);
      assert.equal(JSON.stringify(session.boundary), frozen);
      await restored.close(); restored = undefined;
    } finally { direct.destroy(); await session.close(); await twin.close(); if (restored) await restored.close(); }
  });
}

test('weather clear is not fabricated at terminal and the exact source family rejects before extraction', () => {
  const terminal = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  terminal.setPlayer('p1', {name: 'One', team: team('Sun (Ninetales)\nLevel: 1\nAbility: Drought\n- Splash\n')});
  terminal.setPlayer('p2', {name: 'Two', team: team('Bomb (Snorlax)\nLevel: 100\nAbility: Thick Fat\n- Explosion\n')});
  try {
    terminal.makeChoices('move 1', 'move 1');
    assert.equal(terminal.ended, true);
    assert.equal(terminal.field.weather, 'sunnyday');
    assert.ok(!terminal.log.includes('|-weather|none'), 'terminal does not invent a FieldEnd weather clear');
  } finally { terminal.destroy(); }

  const valid = [
    '|-weather|RainDance', '|-weather|SunnyDay|[upkeep]', '|-weather|Sandstorm|[from] ability: Sand Stream|[of] p2a: Setter',
    '|-weather|Snowscape|[from] ability: Snow Warning|[of] p1a: Setter', '|-weather|none',
  ];
  const invalid = [
    '|-weather|Hail', '|-weather|Sandstorm', '|-weather|raindance', '|-weather|RainDance|[from] ability: Drought|[of] p1a: Setter',
    '|-weather|SunnyDay|[from] ability: Drought|[of] p1: Setter', '|-weather|RainDance|[upkeep]|[of] p1a: Setter',
    '|-weather|Sandstorm|[from] ability: Sand Stream|[of] p1b: Setter',
    '|-weather|SunnyDay|[of] p1a: Setter|[from] ability: Drought',
    '|-weather|SunnyDay|[from] ability: Drought|[of] p1a: Setter|[upkeep]',
    '|-weather|none|[upkeep]', '|-weather| RainDance',
  ];
  for (const record of valid) assert.doesNotThrow(() => validateRawProtocolRecord(record));
  for (const record of invalid) assert.throws(() => validateRawProtocolRecord(record));
});
