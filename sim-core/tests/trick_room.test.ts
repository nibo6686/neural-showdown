import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { validateObservableProtocolPrefix, validateRawProtocolRecord } from '../src/observable_state';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;
const team = (text: string) => Teams.import(text)!;
const choices = (actor: PlayerID, actorChoice: string, foeChoice: string): Record<PlayerID, string> =>
  actor === 'p1' ? {p1: actorChoice, p2: foeChoice} : {p1: foeChoice, p2: actorChoice};

// Slowbro-Galar's generated Wallbreaker set includes Trick Room. The custom
// teams make the public lifecycle deterministic without exposing Field state.
function trickRoomBattle(actor: PlayerID): Battle {
  const room = team(`Room (Slowbro-Galar)
Level: 80
Ability: Regenerator
- Trick Room
- Tackle
- Splash

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  const fast = team(`Fast (Jolteon)
Level: 80
Ability: Volt Absorb
- Tackle
- Splash

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  const result = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  result.setPlayer('p1', {name: 'One', team: actor === 'p1' ? room : fast});
  result.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? room : fast});
  return result;
}

async function sessions(serialized: Record<string, unknown>, actor: PlayerID): Promise<[Session, Session]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(structuredClone(serialized), options); };
    return await Promise.all([0, 1].map(() => createPipelineIntegrationSession({
      battle_id: `trick-room-${actor}`, format: 'gen9randombattle', seed: [1, 2, 3, 4],
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
    assert.ok(!serialized.includes('pseudoWeather') && !serialized.includes('sourceSlot') && !serialized.includes('duration'));
    assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|') || record.startsWith('|split|')));
  }
}

// Moves.trickroom.condition emits the one start form. Reusing it calls
// onFieldRestart, which removes the existing state and emits only FieldEnd.
test('pinned Trick Room condition emits generated start, reapplication clear, expiry, switch, and terminal forms', () => {
  const direct = trickRoomBattle('p1');
  try {
    direct.makeChoices('move 1', 'move 2');
    assert.ok(direct.log.includes('|-fieldstart|move: Trick Room|[of] p1a: Room'));
    assert.ok(direct.field.getPseudoWeather('trickroom'));
    direct.makeChoices('move 1', 'move 2');
    assert.ok(direct.log.includes('|-fieldend|move: Trick Room'));
    assert.equal(direct.field.getPseudoWeather('trickroom'), null);
  } finally { direct.destroy(); }

  const switcher = trickRoomBattle('p1');
  try {
    switcher.makeChoices('move 1', 'move 2');
    switcher.makeChoices('switch 2', 'move 2');
    assert.ok(switcher.field.getPseudoWeather('trickroom'), 'source departure does not clear field pseudo-weather');
    assert.equal(switcher.log.filter(record => record === '|-fieldend|move: Trick Room').length, 0);
  } finally { switcher.destroy(); }

  const expiry = trickRoomBattle('p1');
  try {
    expiry.makeChoices('move 1', 'move 2');
    for (let turn = 0; turn < 4; turn += 1) expiry.makeChoices('move 2', 'move 2');
    assert.equal(expiry.field.getPseudoWeather('trickroom'), null);
    assert.ok(expiry.log.includes('|-fieldend|move: Trick Room'), 'duration expiry emits the tagless FieldEnd form');
  } finally { expiry.destroy(); }

  const terminal = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  terminal.setPlayer('p1', {name: 'One', team: team('Room (Slowbro-Galar)\nLevel: 1\nAbility: Regenerator\n- Trick Room\n- Splash\n')});
  terminal.setPlayer('p2', {name: 'Two', team: team('Bomb (Snorlax)\nLevel: 100\nAbility: Thick Fat\n- Explosion\n- Splash\n')});
  try {
    terminal.makeChoices('move 1', 'move 2');
    terminal.makeChoices('move 2', 'move 1');
    assert.equal(terminal.ended, true);
    assert.ok(terminal.field.getPseudoWeather('trickroom'));
    assert.ok(!terminal.log.includes('|-fieldend|move: Trick Room'), 'terminal does not fabricate a field clear');
  } finally { terminal.destroy(); }
});

for (const actor of PLAYERS) {
  test(`Trick Room ${actor}: public state, source-backed order, restore, rollback, and publish`, async () => {
    const direct = trickRoomBattle(actor);
    const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor);
    let restored: Session | undefined;
    try {
      const setChoice = choices(actor, 'move 1', 'move 2');
      direct.makeChoices(setChoice.p1, setChoice.p2);
      const started = await step(session, setChoice);
      const startedTwin = await step(twin, setChoice);
      assert.equal(started.transition_id, startedTwin.transition_id);
      assert.equal(started.boundary.state_fingerprint, startedTwin.boundary.state_fingerprint);
      const start = `|-fieldstart|move: Trick Room|[of] ${actor}a: Room`;
      for (const player of PLAYERS) {
        const observation = started.boundary.perspectives[player].observation;
        assert.ok(observation.view.field.pseudo_weather.includes('trickroom'));
        assert.ok(observation.protocol_prefix.includes(start));
        assert.equal(python(started.record_bundles[player]).status, 0);
      }
      assertPublicOnly(started.boundary);

      const snapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
      [restored] = await sessions(snapshot, actor);
      assert.equal(restored.boundary.state_fingerprint, started.boundary.state_fingerprint);
      const orderedChoice = choices(actor, 'move 2', 'move 1');
      direct.makeChoices(orderedChoice.p1, orderedChoice.p2);
      const ordered = await step(session, orderedChoice);
      const orderedTwin = await step(twin, orderedChoice);
      const orderedRestored = await step(restored, orderedChoice);
      assert.equal(ordered.transition_id, orderedTwin.transition_id);
      assert.equal(ordered.boundary.state_fingerprint, orderedTwin.boundary.state_fingerprint);
      assert.equal(ordered.boundary.state_fingerprint, orderedRestored.boundary.state_fingerprint);
      const actorMove = `|move|${actor}a: Room|Tackle|`;
      const foe = actor === 'p1' ? 'p2' : 'p1';
      const foeMove = `|move|${foe}a: Fast|Tackle|`;
      for (const player of PLAYERS) {
        const prefix = ordered.boundary.perspectives[player].observation.protocol_prefix;
        assert.ok(prefix.findIndex(record => record.startsWith(actorMove)) < prefix.findIndex(record => record.startsWith(foeMove)),
          'the simulator emits the slower Room user first while Trick Room is active');
        assert.equal(python(ordered.record_bundles[player]).status, 0);
      }

      const clearChoice = choices(actor, 'move 1', 'move 2');
      direct.makeChoices(clearChoice.p1, clearChoice.p2);
      const cleared = await step(session, clearChoice);
      const clearedTwin = await step(twin, clearChoice);
      const clearedRestored = await step(restored, clearChoice);
      assert.equal(cleared.transition_id, clearedTwin.transition_id);
      assert.equal(cleared.boundary.state_fingerprint, clearedTwin.boundary.state_fingerprint);
      assert.equal(cleared.boundary.state_fingerprint, clearedRestored.boundary.state_fingerprint);
      for (const player of PLAYERS) {
        const observation = cleared.boundary.perspectives[player].observation;
        assert.ok(!observation.view.field.pseudo_weather.includes('trickroom'));
        assert.ok(observation.protocol_prefix.includes('|-fieldend|move: Trick Room'));
        assert.equal(observation.protocol_prefix.filter(record => record === start).length, 1,
          'reapplication clears instead of manufacturing a replacement start');
        assert.equal(python(cleared.record_bundles[player]).status, 0);
      }
      assertPublicOnly(cleared.boundary);

      const frozen = JSON.stringify(session.boundary);
      const stale = {p1: select(session, 'p1', clearChoice.p1), p2: select(session, 'p2', clearChoice.p2)};
      await assert.rejects(session.step({...stale, [actor]: {...stale[actor], rqid: 999}}), /request ID does not match/);
      assert.equal(JSON.stringify(session.boundary), frozen);
      await restored.close(); restored = undefined;
    } finally { direct.destroy(); await session.close(); await twin.close(); if (restored) await restored.close(); }
  });
}

test('Trick Room accepts only source-shaped public field forms before projection', () => {
  const valid = [
    '|-fieldstart|move: Trick Room|[of] p1a: Room',
    '|-fieldend|move: Trick Room',
  ];
  const invalid = [
    '|-fieldstart|move: Trick Room', '|fieldstart|move: Trick Room|[of] p1a: Room', '|-fieldactivate|move: Trick Room',
    '|-fieldstart|move: Trick Room|[of] p1: Room', '|-fieldstart|move: Trick Room|[of] p1b: Room',
    '|-fieldstart|move: Trick Room|[persistent]|[of] p1a: Room', '|-fieldstart|move: Trick Room|[of] p1a: Room|[persistent]',
    '|-fieldend|move: Trick Room|[of] p1a: Room', '|-fieldstart|move:  Trick Room|[of] p1a: Room',
  ];
  for (const record of valid) {
    assert.doesNotThrow(() => validateRawProtocolRecord(record));
    assert.doesNotThrow(() => validateObservableProtocolPrefix([record], 'p1'));
    assert.deepEqual(projectPipelineProtocolPrefix([record]), [record]);
  }
  for (const record of invalid) {
    assert.throws(() => validateRawProtocolRecord(record));
    assert.throws(() => validateObservableProtocolPrefix([record], 'p1'));
    assert.throws(() => projectPipelineProtocolPrefix([record]), /unsupported-observable-protocol/);
  }
});
