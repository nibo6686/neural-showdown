import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { buildLegalActionSet } from '../src/action_codec';
import { LocalBattleEnv } from '../src/env_manager';
import { validateRawProtocolRecord } from '../src/observable_state';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix } from '../src/pipeline_integration';
import { PlayerStateExtractor } from '../src/state_extractor';
import type { PlayerID } from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;

function team(text: string) {
  return Teams.import(text)!;
}

/** A real pinned-engine fixture; only the team construction is synthetic. */
function spiritShackleBattle(actor: PlayerID, targetName = 'Lumineon', targetBench = true) {
  const shackler = team(`Warden (Decidueye)
Ability: Overgrow
- Spirit Shackle
- Splash

Reserve (Azumarill)
Ability: Huge Power
- Splash
`);
  const victim = team(`Target (${targetName})
Ability: Swift Swim
- Splash

${targetBench ? `
Reserve (Armarouge)
Ability: Flash Fire
- Splash
` : ''}`);
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? shackler : victim});
  battle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? shackler : victim});
  return battle;
}

/**
 * The source survives the first turn to create a live link. On the next turn,
 * the slower target's real Eruption KOs it, so the pinned faint lifecycle calls
 * clearVolatile rather than using a direct Pokemon.faint() test seam.
 */
function spiritShackleSourceFaintBattle(actor: PlayerID) {
  const shackler = team(`Warden (Decidueye)
Level: 1
Ability: Overgrow
- Spirit Shackle
- Splash

Reserve (Azumarill)
Ability: Huge Power
- Splash
`);
  const victim = team(`Target (Torkoal)
Level: 1
Ability: White Smoke
- Splash
- Eruption

Reserve (Armarouge)
Ability: Flash Fire
- Splash
`);
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? shackler : victim});
  battle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? shackler : victim});
  return battle;
}

function choices(actor: PlayerID, own: string, other = 'move 1'): Record<PlayerID, string> {
  return actor === 'p1' ? {p1: own, p2: other} : {p1: other, p2: own};
}

function side(battle: Battle, player: PlayerID) {
  return battle.sides[player === 'p1' ? 0 : 1];
}

function select(session: Awaited<ReturnType<typeof createPipelineIntegrationSession>>, player: PlayerID, choice: string) {
  const request = session.boundary.perspectives[player].observation.request!;
  const action = request.legal_actions.actions.find((candidate) => candidate?.choice === choice);
  assert.ok(action, `${player} must own ${choice}`);
  return canonicalActionFromLegalAction(request, action.index);
}

function validateInPython(bundle: unknown) {
  return spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(bundle), encoding: 'utf8',
    env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')},
  });
}

async function restoreSpiritShackleSession(actor: PlayerID, serialized: Record<string, unknown>) {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {
      return this.resetFromSerialized(structuredClone(serialized), options);
    };
    return await createPipelineIntegrationSession({
      battle_id: `spirit-shackle-${actor}`, format: 'gen9randombattle', seed: [1, 2, 3, 4],
      observation_schema_version: 'observable-battle-state/v2',
    });
  } finally {
    LocalBattleEnv.prototype.resetWithOptions = reset;
  }
}

for (const actor of PLAYERS) {
  test(`Spirit Shackle ${actor}: public raw evidence, owner-only request truth, release, restoration, and publication`, async () => {
    const battle = spiritShackleBattle(actor);
    const serialized = structuredClone(battle.toJSON());
    let session: Awaited<ReturnType<typeof createPipelineIntegrationSession>> | undefined;
    let restoredTwin: Awaited<ReturnType<typeof createPipelineIntegrationSession>> | undefined;
    try {
      session = await restoreSpiritShackleSession(actor, serialized);
      restoredTwin = await restoreSpiritShackleSession(actor, serialized);
    } finally {
      battle.destroy();
    }
    try {
      assert.deepEqual(session.boundary, restoredTwin.boundary, 'independent pinned restores must begin at the same v2 boundary');
      const target = actor === 'p1' ? 'p2' : 'p1';
      const staleTargetSwitch = select(session, target, 'switch 2');
      const turn = choices(actor, 'move 1');
      const trapped = await session.step({p1: select(session, 'p1', turn.p1), p2: select(session, 'p2', turn.p2)});
      const twinTrapped = await restoredTwin.step({
        p1: select(restoredTwin, 'p1', turn.p1), p2: select(restoredTwin, 'p2', turn.p2),
      });
      assert.equal(trapped.transition_id, twinTrapped.transition_id, 'identical restored trap actions must retain transition identity');
      assert.deepEqual(trapped.record_bundles, twinTrapped.record_bundles, 'identical restored trap actions must publish identical bundles');
      assert.deepEqual(trapped.boundary, twinTrapped.boundary, 'identical restored trap actions must reach the same boundary');
      const targetRequest = trapped.boundary.perspectives[target].observation.request!;
      const sourceRequest = trapped.boundary.perspectives[actor].observation.request!;
      assert.equal(targetRequest.trapped, true);
      assert.equal(targetRequest.active?.trapped, true);
      assert.equal(targetRequest.active?.can_switch, false);
      assert.equal(targetRequest.legal_actions.actions.slice(8).some(Boolean), false);
      assert.equal(sourceRequest.active?.can_switch, true);
      assert.ok(sourceRequest.legal_actions.actions.slice(8).some(Boolean));
      for (const player of PLAYERS) {
        const observation = trapped.boundary.perspectives[player].observation;
        const bundle = trapped.record_bundles[player];
        assert.ok(bundle, `${player} must receive its published transition record`);
        assert.equal(bundle.input_observation.schema_version, 'observable-battle-state/v2');
        assert.equal(bundle.successor_observation.schema_version, 'observable-battle-state/v2');
        assert.equal(bundle.input_observation.request?.player, player);
        assert.equal(bundle.successor_observation.request?.player, player);
        assert.equal(bundle.transition.transition_id, trapped.transition_id);
        assert.ok(observation.protocol_prefix.includes(`|-activate|${target}a: Target|trapped`));
        assert.ok(!observation.protocol_prefix.some((record) => record === `|-start|${target}a: Target|trapped`));
        assert.ok(observation.protocol_prefix.every((record) => !record.startsWith('|request|')));
        for (const pokemon of [...observation.view.self_team, ...observation.view.opponent_team]) {
          assert.ok(!pokemon.volatiles.includes('trapped'));
          assert.ok(!pokemon.volatiles.includes('trapper'));
        }
        assert.ok(!JSON.stringify(bundle).includes('trapper'));
        assert.ok(!JSON.stringify(bundle).includes('|request|'));
      }
      for (const player of PLAYERS) assert.equal(validateInPython(trapped.record_bundles[player]).status, 0);

      const prior = session.boundary;
      await assert.rejects(session.step({
        p1: target === 'p1' ? staleTargetSwitch : select(session, 'p1', 'move 1'),
        p2: target === 'p2' ? staleTargetSwitch : select(session, 'p2', 'move 1'),
      }), /Canonical action index is not legal/);
      assert.equal(session.boundary, prior, 'a stale trapped target switch must retain the trapped request boundary');

      const releasedTurn = choices(actor, 'switch 2');
      const released = await session.step({p1: select(session, 'p1', releasedTurn.p1), p2: select(session, 'p2', releasedTurn.p2)});
      const twinReleased = await restoredTwin.step({
        p1: select(restoredTwin, 'p1', releasedTurn.p1), p2: select(restoredTwin, 'p2', releasedTurn.p2),
      });
      assert.equal(released.transition_id, twinReleased.transition_id, 'identical restored release actions must retain transition identity');
      assert.deepEqual(released.record_bundles, twinReleased.record_bundles, 'identical restored release actions must publish identical bundles');
      assert.deepEqual(released.boundary, twinReleased.boundary, 'identical restored release actions must reach the same boundary');
      const restored = released.boundary.perspectives[target].observation.request!;
      assert.equal(restored.trapped, false);
      assert.equal(restored.active?.trapped, false);
      assert.equal(restored.active?.can_switch, true);
      assert.ok(restored.legal_actions.actions.slice(8).some(Boolean));
      for (const player of PLAYERS) {
        const bundle = released.record_bundles[player];
        assert.ok(bundle, `${player} must receive the restored v2 transition record`);
        assert.equal(bundle.successor_observation.schema_version, 'observable-battle-state/v2');
        assert.equal(bundle.successor_observation.request?.player, player);
        assert.equal(bundle.transition.transition_id, released.transition_id);
        const trappedBundle = trapped.record_bundles[player];
        assert.ok(trappedBundle, `${player} must retain the prior published transition record`);
        assert.equal(bundle.transition.input_state_fingerprint, trappedBundle.transition.output_state_fingerprint);
        assert.ok(!JSON.stringify(bundle).includes('trapper'));
        assert.ok(!JSON.stringify(bundle).includes('|request|'));
        assert.equal(validateInPython(bundle).status, 0);
      }

      const replacementTurn = choices(target, 'switch 2');
      const replacement = await session.step({
        p1: select(session, 'p1', replacementTurn.p1),
        p2: select(session, 'p2', replacementTurn.p2),
      });
      for (const player of PLAYERS) {
        const bundle = replacement.record_bundles[player];
        assert.ok(bundle, `${player} must publish the target replacement transition`);
        assert.ok(bundle.successor_observation.protocol_prefix.some((record) => record.startsWith(`|switch|${target}a: Reserve|`)));
        assert.equal(bundle.successor_observation.request?.player, player);
        assert.ok(!JSON.stringify(bundle).includes('trapper'));
        assert.equal(validateInPython(bundle).status, 0);
      }
    } finally {
      await session?.close();
      await restoredTwin?.close();
    }
  });
}

for (const actor of PLAYERS) {
  test(`Spirit Shackle ${actor}: source faint clears the linked trap through the pinned lifecycle`, async () => {
    const target = actor === 'p1' ? 'p2' : 'p1';
    const direct = spiritShackleSourceFaintBattle(actor);
    const serialized = structuredClone(direct.toJSON());
    let session: Awaited<ReturnType<typeof createPipelineIntegrationSession>> | undefined;
    let twin: Awaited<ReturnType<typeof createPipelineIntegrationSession>> | undefined;
    try {
      // Establish a live link, then use the target's real attack to faint the
      // source. This is deliberately not a direct faint/volatile mutation.
      const linkTurn = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(linkTurn.p1, linkTurn.p2);
      const sourcePokemon = side(direct, actor).active[0]!;
      const targetPokemon = side(direct, target).active[0]!;
      assert.ok(sourcePokemon.volatiles.trapper, 'the surviving source must own the link before it faints');
      assert.ok(targetPokemon.volatiles.trapped, 'the live target with a bench must be trapped before the source faints');
      const sourceFaintTurn = choices(actor, 'move 2', 'move 2');
      direct.makeChoices(sourceFaintTurn.p1, sourceFaintTurn.p2);
      assert.ok(sourcePokemon.fainted, 'Eruption must faint the linked source through normal battle resolution');
      assert.ok(!targetPokemon.fainted, 'the target must remain active after the source faints');
      assert.ok(!sourcePokemon.volatiles.trapper, 'source clearVolatile must remove trapper on faint');
      assert.ok(!targetPokemon.volatiles.trapped, 'source clearVolatile must unlink the target trap on faint');

      session = await restoreSpiritShackleSession(actor, serialized);
      twin = await restoreSpiritShackleSession(actor, serialized);
    } finally {
      direct.destroy();
    }
    try {
      const staleTargetSwitch = select(session, target, 'switch 2');
      const linkTurn = choices(actor, 'move 1', 'move 1');
      const linked = await session.step({p1: select(session, 'p1', linkTurn.p1), p2: select(session, 'p2', linkTurn.p2)});
      const linkedTwin = await twin.step({p1: select(twin, 'p1', linkTurn.p1), p2: select(twin, 'p2', linkTurn.p2)});
      assert.equal(linked.transition_id, linkedTwin.transition_id);
      assert.deepEqual(linked.record_bundles, linkedTwin.record_bundles);
      assert.deepEqual(linked.boundary, linkedTwin.boundary);
      const trappedRequest = linked.boundary.perspectives[target].observation.request!;
      assert.equal(trappedRequest.trapped, true);
      assert.equal(trappedRequest.active?.can_switch, false);
      assert.equal(trappedRequest.legal_actions.actions.slice(8).some(Boolean), false);

      const linkedBoundary = session.boundary;
      await assert.rejects(session.step({
        p1: target === 'p1' ? staleTargetSwitch : select(session, 'p1', 'move 2'),
        p2: target === 'p2' ? staleTargetSwitch : select(session, 'p2', 'move 2'),
      }), /Canonical action index is not legal/);
      assert.equal(session.boundary, linkedBoundary, 'the stale trapped switch must reject before source faint');

      const sourceFaintTurn = choices(actor, 'move 2', 'move 2');
      const fainted = await session.step({p1: select(session, 'p1', sourceFaintTurn.p1), p2: select(session, 'p2', sourceFaintTurn.p2)});
      const faintedTwin = await twin.step({p1: select(twin, 'p1', sourceFaintTurn.p1), p2: select(twin, 'p2', sourceFaintTurn.p2)});
      assert.equal(fainted.transition_id, faintedTwin.transition_id, 'independent restores must reproduce the source-faint transition ID');
      assert.deepEqual(fainted.record_bundles, faintedTwin.record_bundles, 'independent restores must reproduce source-faint bundles');
      assert.deepEqual(fainted.boundary, faintedTwin.boundary, 'independent restores must reproduce the source-faint boundary');
      assert.equal(fainted.boundary.kind, 'one_sided_forced_switch');
      const targetWaitingRequest = fainted.boundary.perspectives[target].observation.request!;
      assert.equal(targetWaitingRequest.wait, true, 'only the fainted source owner may act at the forced-switch boundary');
      assert.equal(targetWaitingRequest.trapped, false, 'the waiting target request must not retain a trap after source clearVolatile');
      assert.ok(fainted.boundary.perspectives[target].observation.protocol_prefix.some((record) => record.startsWith(`|faint|${actor}a: Warden`)));
      for (const player of PLAYERS) {
        const bundle = fainted.record_bundles[player];
        assert.ok(bundle, `${player} must receive the source-faint publication`);
        assert.equal(validateInPython(bundle).status, 0);
        assert.ok(!JSON.stringify(bundle).includes('trapper'));
        assert.ok(!JSON.stringify(bundle).includes('|request|'));
        for (const pokemon of [...fainted.boundary.perspectives[player].observation.view.self_team, ...fainted.boundary.perspectives[player].observation.view.opponent_team]) {
          assert.ok(!pokemon.volatiles.includes('trapped'));
          assert.ok(!pokemon.volatiles.includes('trapper'));
        }
      }

      const replacement = await session.stepForcedSwitch(select(session, actor, 'switch 2'));
      const replacementTwin = await twin.stepForcedSwitch(select(twin, actor, 'switch 2'));
      assert.equal(replacement.transition_id, replacementTwin.transition_id, 'independent restores must reproduce the replacement transition ID');
      assert.deepEqual(replacement.record_bundles, replacementTwin.record_bundles, 'independent restores must reproduce replacement bundles');
      assert.deepEqual(replacement.boundary, replacementTwin.boundary, 'independent restores must reproduce the replacement boundary');
      assert.equal(replacement.boundary.kind, 'joint_actionable');
      const restoredTargetRequest = replacement.boundary.perspectives[target].observation.request!;
      assert.equal(restoredTargetRequest.wait, false);
      assert.equal(restoredTargetRequest.trapped, false);
      assert.equal(restoredTargetRequest.active?.trapped, false);
      assert.equal(restoredTargetRequest.active?.can_switch, true);
      assert.ok(restoredTargetRequest.legal_actions.actions.slice(8).some(Boolean), 'the next target-owner request alone restores legal switching');
      const replacementBundle = replacement.record_bundles[actor]!;
      assert.equal(validateInPython(replacementBundle).status, 0);
      assert.ok(!JSON.stringify(replacementBundle).includes('trapper'));
      assert.ok(!JSON.stringify(replacementBundle).includes('|request|'));
    } finally {
      await session?.close();
      await twin?.close();
    }
  });
}

test('Spirit Shackle links clear on target faint, drag, and replacement', () => {
  for (const departure of ['faint', 'drag'] as const) {
    const battle = spiritShackleBattle('p1');
    try {
      battle.makeChoices('move 1', 'move 1');
      const target = side(battle, 'p2').active[0]!;
      const source = side(battle, 'p1').active[0]!;
      assert.ok(source.volatiles.trapper);
      assert.ok(target.volatiles.trapped);
      if (departure === 'faint') {
        target.faint();
        battle.faintMessages();
        assert.equal(battle.actions.switchIn(side(battle, 'p2').pokemon[1]!, 0), true);
      } else {
        assert.equal(battle.actions.dragIn(side(battle, 'p2'), 0), true);
      }
      assert.ok(!source.volatiles.trapper, `${departure} must unlink the source`);
      assert.ok(!target.volatiles.trapped, `${departure} must clear the target`);
      assert.ok(battle.log.some((record) => record.startsWith(`|${departure}|p2a:`)));
      assert.equal(side(battle, 'p2').active[0]!.name, 'Reserve');
    } finally {
      battle.destroy();
    }
  }
});

test('Spirit Shackle Ghost immunity and terminal faint do not retain a link', () => {
  const ghost = spiritShackleBattle('p1', 'Gengar');
  try {
    ghost.makeChoices('move 1', 'move 1');
    const target = side(ghost, 'p2').active[0]!;
    assert.ok(!target.volatiles.trapped);
    assert.ok(!side(ghost, 'p1').active[0]!.volatiles.trapper);
    assert.ok(buildLegalActionSet(side(ghost, 'p2').activeRequest).actions.slice(8).some(Boolean));
    assert.ok(!ghost.log.some((record) => record === '|-activate|p2a: Target|trapped'));
  } finally {
    ghost.destroy();
  }

  const terminal = spiritShackleBattle('p1', 'Lumineon', false);
  try {
    side(terminal, 'p2').active[0]!.hp = 1;
    terminal.makeChoices('move 1', 'move 1');
    assert.equal(terminal.ended, true);
    assert.ok(terminal.log.some((record) => record.startsWith('|faint|p2a: Target')));
    assert.ok(!side(terminal, 'p1').active[0]!.volatiles.trapper);
  } finally {
    terminal.destroy();
  }
});

test('Spirit Shackle raw evidence stays link-free and accepts only the pinned activation grammar', () => {
  const exact = '|-activate|p2a: Target|trapped';
  for (const record of [exact]) {
    assert.doesNotThrow(() => validateRawProtocolRecord(record));
    assert.deepEqual(projectPipelineProtocolPrefix([record]), [record]);
    for (const perspective of PLAYERS) {
      const extractor = new PlayerStateExtractor('spirit-shackle-raw', 'gen9randombattle', perspective);
      extractor.consumeChunk('|switch|p1a: Warden|Decidueye, L80|100/100\n|switch|p2a: Target|Lumineon, L80|100/100');
      const before = extractor.getView();
      extractor.consumeChunk(record);
      assert.deepEqual(extractor.getView(), before);
    }
  }
  for (const malformed of [
    '|-activate|p2a: Target|trapped|[of] p1a: Warden',
    '|-activate|p2a: Target|trapped|[from] move: Spirit Shackle',
    '|-activate|p2a: Target|trapped|source',
    '|-activate|p2a: Target |trapped',
    '|-activate|p2a: Target|trapped ',
    '|-activate|p2: Target|trapped',
  ]) {
    assert.throws(() => validateRawProtocolRecord(malformed));
    assert.throws(() => projectPipelineProtocolPrefix([malformed]));
  }

  const request = {active: [{moves: [{move: 'Splash', id: 'splash', pp: 1, maxpp: 40}], trapped: true}], side: {pokemon: [
    {active: true, condition: '100/100'}, {active: false, condition: '100/100', details: 'Armarouge'},
  ]}};
  assert.equal(buildLegalActionSet(request).actions.slice(8).some(Boolean), false);
});
