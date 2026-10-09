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

// These species/abilities/moves are present in pinned gen9 random-battle sets.
// The fixture retains only emitted field records; Field.terrainState stores its
// duration/source and never crosses an observation or publication boundary.
function terrainBattle(actor: PlayerID): Battle {
  const setter = team(`Pin (Pincurchin)
Ability: Electric Surge
- Splash

Grass (Rillaboom)
Ability: Grassy Surge
- Splash
`);
  const clearer = team(`Clearer (Azumarill)
Ability: Huge Power
- Ice Spinner
- Splash

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  const result = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  result.setPlayer('p1', {name: 'One', team: actor === 'p1' ? setter : clearer});
  result.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? setter : clearer});
  return result;
}

async function sessions(serialized: Record<string, unknown>, actor: PlayerID): Promise<[Session, Session]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(structuredClone(serialized), options); };
    return await Promise.all([0, 1].map(() => createPipelineIntegrationSession({
      battle_id: `terrain-${actor}`, format: 'gen9randombattle', seed: [1, 2, 3, 4],
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
    assert.ok(!serialized.includes('terrainState') && !serialized.includes('sourceSlot') && !serialized.includes('duration'));
    assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|') || record.startsWith('|split|')));
  }
}

// Every operative generated terrain setter reaches the same FieldStart template
// with its own finite source ability. Misty Terrain has no generated M/A/I root.
test('pinned terrain emitters expose only the finite generated fieldstart templates', () => {
  const starters = [
    ['Pincurchin', 'Electric Surge', 'Electric Terrain'],
    ['Rillaboom', 'Grassy Surge', 'Grassy Terrain'],
    ['Indeedee', 'Psychic Surge', 'Psychic Terrain'],
    ['Miraidon', 'Hadron Engine', 'Electric Terrain'],
  ] as const;
  for (const [species, ability, terrain] of starters) {
    const direct = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    direct.setPlayer('p1', {name: 'One', team: team(`Setter (${species})\nAbility: ${ability}\n- Splash\n`)});
    direct.setPlayer('p2', {name: 'Two', team: team('Foe (Eevee)\nAbility: Run Away\n- Splash\n')});
    try {
      assert.ok(direct.log.includes(`|-fieldstart|move: ${terrain}|[from] ability: ${ability}|[of] p1a: Setter`));
    } finally { direct.destroy(); }
  }

  const seedSower = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  seedSower.setPlayer('p1', {name: 'One', team: team('Olive (Arboliva)\nAbility: Seed Sower\n- Splash\n')});
  seedSower.setPlayer('p2', {name: 'Two', team: team('Foe (Eevee)\nAbility: Run Away\n- Tackle\n')});
  try {
    seedSower.makeChoices('move 1', 'move 1');
    assert.ok(seedSower.log.includes('|-fieldstart|move: Grassy Terrain|[from] ability: Seed Sower|[of] p1a: Olive'));
  } finally { seedSower.destroy(); }

  const clear = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  clear.setPlayer('p1', {name: 'One', team: team('Pin (Pincurchin)\nAbility: Electric Surge\n- Splash\n')});
  clear.setPlayer('p2', {name: 'Two', team: team('Clearer (Azumarill)\nAbility: Huge Power\n- Ice Spinner\n')});
  try {
    clear.makeChoices('move 1', 'move 1');
    assert.ok(clear.log.includes('|-fieldend|move: Electric Terrain'));
    assert.equal(clear.field.terrain, '');
  } finally { clear.destroy(); }
});

for (const actor of PLAYERS) {
  test(`terrain ${actor}: replace, clear, restore, and publish the public ID only`, async () => {
    const direct = terrainBattle(actor);
    const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor);
    let restored: Session | undefined;
    try {
      const electric = `|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] ${actor}a: Pin`;
      for (const player of PLAYERS) {
        assert.equal(session.boundary.perspectives[player].observation.view.field.terrain, 'electricterrain');
        assert.ok(session.boundary.perspectives[player].observation.protocol_prefix.includes(electric));
      }

      const replace = choices(actor, 'switch 2', 'move 2');
      direct.makeChoices(replace.p1, replace.p2);
      const grassy = await step(session, replace);
      const grassyTwin = await step(twin, replace);
      assert.equal(grassy.transition_id, grassyTwin.transition_id);
      assert.equal(grassy.boundary.state_fingerprint, grassyTwin.boundary.state_fingerprint);
      const grass = `|-fieldstart|move: Grassy Terrain|[from] ability: Grassy Surge|[of] ${actor}a: Grass`;
      for (const player of PLAYERS) {
        const observation = grassy.boundary.perspectives[player].observation;
        assert.equal(observation.view.field.terrain, 'grassyterrain');
        assert.ok(observation.protocol_prefix.includes(grass));
        assert.ok(!observation.protocol_prefix.includes('|-fieldend|move: Electric Terrain'), 'replacement has no fabricated interim clear');
        assert.equal(python(grassy.record_bundles[player]).status, 0);
      }
      assertPublicOnly(grassy.boundary);

      const snapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
      [restored] = await sessions(snapshot, actor);
      assert.equal(restored.boundary.state_fingerprint, grassy.boundary.state_fingerprint);
      const clear = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(clear.p1, clear.p2);
      const cleared = await step(session, clear);
      const clearedTwin = await step(twin, clear);
      const clearedRestored = await step(restored, clear);
      assert.equal(cleared.transition_id, clearedTwin.transition_id);
      assert.equal(cleared.boundary.state_fingerprint, clearedTwin.boundary.state_fingerprint);
      assert.equal(cleared.boundary.state_fingerprint, clearedRestored.boundary.state_fingerprint);
      assert.equal(direct.field.terrain, '');
      for (const player of PLAYERS) {
        const observation = cleared.boundary.perspectives[player].observation;
        assert.equal(observation.view.field.terrain, null);
        assert.ok(observation.protocol_prefix.includes('|-fieldend|move: Grassy Terrain'));
        assert.equal(python(cleared.record_bundles[player]).status, 0);
      }
      assertPublicOnly(cleared.boundary);

      const frozen = JSON.stringify(session.boundary);
      const stale = {p1: select(session, 'p1', clear.p1), p2: select(session, 'p2', clear.p2)};
      await assert.rejects(session.step({...stale, [actor]: {...stale[actor], rqid: 999}}), /request ID does not match/);
      assert.equal(JSON.stringify(session.boundary), frozen);
      await restored.close(); restored = undefined;
    } finally { direct.destroy(); await session.close(); await twin.close(); if (restored) await restored.close(); }
  });
}

test('terrain expiry/terminal do not fabricate source, duration, or clear records', () => {
  const expiry = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  expiry.setPlayer('p1', {name: 'One', team: team('Pin (Pincurchin)\nAbility: Electric Surge\n- Splash\n')});
  expiry.setPlayer('p2', {name: 'Two', team: team('Foe (Eevee)\nAbility: Run Away\n- Splash\n')});
  try {
    for (let turn = 0; turn < 5; turn += 1) expiry.makeChoices('move 1', 'move 1');
    assert.equal(expiry.field.terrain, '');
    assert.ok(expiry.log.includes('|-fieldend|move: Electric Terrain'), 'terrain expiry emits the exact FieldEnd record');
  } finally { expiry.destroy(); }

  const terminal = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  terminal.setPlayer('p1', {name: 'One', team: team('Pin (Pincurchin)\nLevel: 1\nAbility: Electric Surge\n- Splash\n')});
  terminal.setPlayer('p2', {name: 'Two', team: team('Bomb (Snorlax)\nLevel: 100\nAbility: Thick Fat\n- Explosion\n')});
  try {
    terminal.makeChoices('move 1', 'move 1');
    assert.equal(terminal.ended, true);
    assert.equal(terminal.field.terrain, 'electricterrain');
    assert.ok(!terminal.log.includes('|-fieldend|move: Electric Terrain'), 'terminal does not invoke FieldEnd');
  } finally { terminal.destroy(); }

  const valid = [
    '|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pin',
    '|-fieldstart|move: Electric Terrain|[from] ability: Hadron Engine|[of] p2a: Miraidon',
    '|-fieldstart|move: Grassy Terrain|[from] ability: Seed Sower|[of] p1a: Olive',
    '|-fieldstart|move: Psychic Terrain|[from] ability: Psychic Surge|[of] p2a: Indeedee',
    '|-fieldend|move: Electric Terrain', '|-fieldend|move: Grassy Terrain', '|-fieldend|move: Psychic Terrain',
  ];
  const invalid = [
    '|-fieldstart|move: Electric Terrain', '|fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pin', '|-fieldactivate|move: Electric Terrain',
    '|-fieldstart|move: Misty Terrain|[from] ability: Misty Surge|[of] p1a: Weezing',
    '|-fieldstart|move: Grassy Terrain|[from] ability: Electric Surge|[of] p1a: Pin',
    '|-fieldstart|move: Electric Terrain|[of] p1a: Pin|[from] ability: Electric Surge',
    '|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1: Pin',
    '|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1b: Pin',
    '|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pin|[upkeep]',
    '|-fieldend|move: Grassy Terrain|[from] move: Ice Spinner',
    '|-fieldstart|move:  Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pin',
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
