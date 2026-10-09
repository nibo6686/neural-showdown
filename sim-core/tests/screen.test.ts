import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { validateObservableProtocolPrefix, validateRawProtocolRecord } from '../src/observable_state';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;
type Screen = { id: 'reflect' | 'lightscreen' | 'auroraveil'; move: 'Reflect' | 'Light Screen' | 'Aurora Veil'; emitted: 'Reflect' | 'move: Light Screen' | 'move: Aurora Veil' };
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;
const SCREENS: readonly Screen[] = [
  {id: 'reflect', move: 'Reflect', emitted: 'Reflect'},
  {id: 'lightscreen', move: 'Light Screen', emitted: 'move: Light Screen'},
  {id: 'auroraveil', move: 'Aurora Veil', emitted: 'move: Aurora Veil'},
];
const team = (text: string) => Teams.import(text)!;
const choices = (actor: PlayerID, actorChoice: string, foeChoice: string): Record<PlayerID, string> =>
  actor === 'p1' ? {p1: actorChoice, p2: foeChoice} : {p1: foeChoice, p2: actorChoice};

// The three screen moves are direct retained Gen 9 Random Battle candidates:
// Meowstic supplies Reflect/Light Screen and Ninetales-Alola supplies Aurora
// Veil plus the Snow Warning condition that permits it. Mew supplies generated
// Psychic Fangs. Teams are constrained only to make those pinned paths
// deterministic; all public evidence still comes from the engine.
function screenSetter(screen: Screen) {
  if (screen.id === 'auroraveil') return team(`Setter (Ninetales-Alola)\nAbility: Snow Warning\n- Aurora Veil\n- Splash\n\nReserve (Eevee)\nAbility: Run Away\n- Splash\n`);
  return team(`Setter (Meowstic)\nAbility: Prankster\n- ${screen.move}\n- Splash\n\nReserve (Eevee)\nAbility: Run Away\n- Splash\n`);
}
function screenBattle(actor: PlayerID, screen: Screen): Battle {
  const setter = screenSetter(screen);
  const clearer = team(`Clearer (Mew)\nAbility: Synchronize\n- Psychic Fangs\n- Splash\n\nReserve (Eevee)\nAbility: Run Away\n- Splash\n`);
  const result = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  result.setPlayer('p1', {name: 'One', team: actor === 'p1' ? setter : clearer});
  result.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? setter : clearer});
  return result;
}
async function sessions(serialized: Record<string, unknown>, actor: PlayerID, screen: Screen): Promise<[Session, Session]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(structuredClone(serialized), options); };
    return await Promise.all([0, 1].map(() => createPipelineIntegrationSession({
      battle_id: `screen-${screen.id}-${actor}`, format: 'gen9randombattle', seed: [1, 2, 3, 4], observation_schema_version: 'observable-battle-state/v2',
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
    input: JSON.stringify(bundle), encoding: 'utf8', env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')},
  });
}

// Side.addSideCondition suppresses duplicate SideStart. Side.removeSideCondition
// invokes the same side condition's SideEnd on natural expiry and every
// source-backed removal with this public shape, so no source/timer/cause tag is public on the screen end record.
test('pinned screens are nonstacking, expire, and use a shared tagless end grammar', () => {
  for (const screen of SCREENS) {
    const direct = screenBattle('p1', screen);
    try {
      direct.makeChoices('move 1', 'move 2');
      const start = `|-sidestart|p1: One|${screen.emitted}`;
      assert.equal(direct.log.filter(record => record === start).length, 1, screen.id);
      assert.ok(direct.sides[0].sideConditions[screen.id]);
      direct.makeChoices('move 1', 'move 2');
      assert.equal(direct.log.filter(record => record === start).length, 1, `${screen.id} duplicate has no restart`);
      for (let turn = 0; turn < 6; turn += 1) direct.makeChoices('move 2', 'move 2');
      assert.ok(direct.log.includes(`|-sideend|p1: One|${screen.emitted}`), `${screen.id} natural end`);
      assert.equal(direct.sides[0].sideConditions[screen.id], undefined);
    } finally { direct.destroy(); }
  }
});

test('pinned Defog, Brick Break, and Raging Bull remove screens with the same public end', () => {
  const removers = [
    {species: 'Corviknight', move: 'Defog'}, {species: 'Scizor', move: 'Brick Break'},
{species: 'Tauros-Paldea-Aqua', move: 'Raging Bull'},
  ];
  for (const remover of removers) {
    const direct = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    direct.setPlayer('p1', {name: 'One', team: screenSetter(SCREENS[0])});
    direct.setPlayer('p2', {name: 'Two', team: team(`Clearer (${remover.species})\nAbility: Pressure\n- ${remover.move}\n- Splash\n`)});
    try {
      direct.makeChoices('move 1', 'move 2');
      direct.makeChoices('move 2', 'move 1');
      assert.ok(direct.log.includes('|-sideend|p1: One|Reflect'), remover.move);
      assert.equal(direct.sides[0].sideConditions.reflect, undefined);
    } finally { direct.destroy(); }
  }
});

// Psychic Fangs is a retained Gen 9 Random Battle move (for example on Mew).
// Its onTryHit removes all three screen conditions before damage, which calls
// each condition's ordinary tagless SideEnd callback.
test('pinned Psychic Fangs removes every screen through its ordinary public SideEnd', () => {
  for (const screen of SCREENS) {
    const direct = screenBattle('p1', screen);
    try {
      direct.makeChoices('move 1', 'move 2');
      direct.makeChoices('move 2', 'move 1');
      assert.ok(direct.log.includes(`|-sideend|p1: One|${screen.emitted}`), screen.id);
      assert.equal(direct.sides[0].sideConditions[screen.id], undefined, screen.id);
    } finally { direct.destroy(); }
  }
});

for (const actor of PLAYERS) {
  for (const screen of SCREENS) {
    test(`screen ${screen.id} ${actor}: v2 public state, restore, rollback, and publication`, async () => {
      const direct = screenBattle(actor, screen);
      const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, screen);
      const target = actor;
      const targetName = target === 'p1' ? 'One' : 'Two';
      let restored: Session | undefined;
      try {
        const start = choices(actor, 'move 1', 'move 2');
        direct.makeChoices(start.p1, start.p2);
        const result = await step(session, start); const twinResult = await step(twin, start);
        assert.equal(result.transition_id, twinResult.transition_id);
        assert.equal(result.boundary.state_fingerprint, twinResult.boundary.state_fingerprint);
        for (const player of PLAYERS) {
          const observation = result.boundary.perspectives[player].observation;
          const side = player === target ? observation.view.field.side_conditions.self : observation.view.field.side_conditions.opponent;
          assert.equal(side[screen.id], 1);
          assert.ok(observation.protocol_prefix.includes(`|-sidestart|${target}: ${targetName}|${screen.emitted}`));
          const serialized = JSON.stringify(observation);
          assert.ok(!serialized.includes('sideConditions') && !serialized.includes('sourceSlot') && !serialized.includes('duration'));
          assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|') || record.startsWith('|split|')));
          assert.equal(python(result.record_bundles[player]).status, 0);
        }
        const snapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
        [restored] = await sessions(snapshot, actor, screen);
        assert.equal(restored.boundary.state_fingerprint, result.boundary.state_fingerprint);

        const frozen = JSON.stringify(session.boundary);
        const stale = {p1: select(session, 'p1', start.p1), p2: select(session, 'p2', start.p2)};
        await assert.rejects(session.step({...stale, [actor]: {...stale[actor], rqid: 999}}), /request ID does not match/);
        assert.equal(JSON.stringify(session.boundary), frozen);

        const clear = choices(actor, 'move 2', 'move 1');
        direct.makeChoices(clear.p1, clear.p2);
        const cleared = await step(session, clear); const clearedTwin = await step(twin, clear); const restoredCleared = await step(restored, clear);
        assert.equal(cleared.transition_id, clearedTwin.transition_id);
        // Restored sessions retain their independent parent lineage; the public
        // successor fingerprint is the deterministic continuation invariant.
        assert.equal(cleared.boundary.state_fingerprint, restoredCleared.boundary.state_fingerprint);
        for (const player of PLAYERS) {
          const observation = cleared.boundary.perspectives[player].observation;
          const side = player === target ? observation.view.field.side_conditions.self : observation.view.field.side_conditions.opponent;
          assert.equal(side[screen.id], undefined);
          assert.ok(observation.protocol_prefix.includes(`|-sideend|${target}: ${targetName}|${screen.emitted}`));
          assert.equal(python(cleared.record_bundles[player]).status, 0);
        }
      } finally {
        direct.destroy(); await session.close(); await twin.close(); if (restored) await restored.close();
      }
    });
  }
}

test('screen source grammar rejects malformed forms before projection', () => {
  const valid = ['|-sidestart|p1: One|Reflect', '|-sidestart|p2: Two|move: Light Screen', '|-sideend|p1: One|move: Aurora Veil'];
  const invalid = [
    '|-sidestart|p1a: One|Reflect', '|-sidestart|p1: One|move: Reflect', '|-sidestart|p1: One| Light Screen',
    '|-sidestart|p1: One|Safeguard', '|-sidestart|p1: One|Reflect|[from] move: Reflect',
    '|-sideend|p2: Two|move: Light Screen|[from] move: Defog', '|-sideend|p2: Two|Aurora Veil',
    '|sidestart|p1: One|Reflect', '|-sideend|p1: One|Reflect|extra', '|-sidestart|p1: One|Reflect ',
  ];
  for (const record of valid) validateRawProtocolRecord(record);
  for (const record of invalid) assert.throws(() => validateRawProtocolRecord(record), record);
  for (const player of PLAYERS) assert.throws(() => validateObservableProtocolPrefix(invalid, player));
});
