import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;
const SEED = [1, 2, 3, 4];
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;

function choices(actor: PlayerID, actorChoice: string, foeChoice: string): Record<PlayerID, string> {
  return actor === 'p1' ? {p1: actorChoice, p2: foeChoice} : {p1: foeChoice, p2: actorChoice};
}

function battle(actor: PlayerID, tera = 'Flying', species = 'Articuno'): Battle {
  const rooster = Teams.import(`Target (${species})
Ability: Pressure
Tera Type: ${tera}
- Roost
- Splash
- Explosion

Reserve (Eevee)
Ability: Run Away
- Splash
`)!;
const foe = Teams.import(`Foe (Golem)
Ability: Sturdy
- Swift
- Earthquake
- Splash

Reserve (Eevee)
Ability: Run Away
- Splash
`)!;
  const result = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  result.setPlayer('p1', {name: 'One', team: actor === 'p1' ? rooster : foe});
  result.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? rooster : foe});
  return result;
}

/**
 * The generated Ditto row has both Imposter and Transform. Articuno acts before
 * the slower U-turn pivot; the forced replacement puts Ditto's Imposter
 * `transformInto` call between Roost's `onType` and the residual expiry.
 */
function imposterBattle(actor: PlayerID): Battle {
const target = Teams.import(`Target (Articuno)
Ability: Pressure
- Roost
- Whirlwind
- Explosion
- Splash

Mask (Zoroark)
Ability: Illusion
- Splash

Warden (Tyranitar)
Ability: Sand Stream
- Stone Edge
- Splash
`)!;
  const copier = Teams.import(`Pivot (Scizor)
Ability: Technician
- U-turn
- Swift
- Splash

Copy (Ditto)
Ability: Imposter
- Transform

Reserve (Eevee)
Ability: Run Away
- Splash
`)!;
  const result = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  result.setPlayer('p1', {name: 'One', team: actor === 'p1' ? copier : target});
  result.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? copier : target});
  return result;
}

async function sessions(serialized: Record<string, unknown>, actor: PlayerID, suffix: string): Promise<[Session, Session]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {
      return this.resetFromSerialized(structuredClone(serialized), options);
    };
    return await Promise.all([0, 1].map(() => createPipelineIntegrationSession({
      battle_id: `roost-${actor}-${suffix}`, format: 'gen9randombattle', seed: SEED,
      observation_schema_version: 'observable-battle-state/v2',
    }))) as [Session, Session];
  } finally {
    LocalBattleEnv.prototype.resetWithOptions = reset;
  }
}

function select(session: Session, player: PlayerID, choice: string) {
  const request = session.boundary.perspectives[player].observation.request!;
  const action = request.legal_actions.actions.find(candidate => candidate?.choice === choice);
  assert.ok(action, `${player} must own ${choice}`);
  return canonicalActionFromLegalAction(request, action.index);
}

function selectForced(session: Session, player: PlayerID, choice: string) {
  const request = session.boundary.perspectives[player].observation.request!;
  const action = request.legal_actions.actions.find(candidate => candidate?.choice === choice);
  assert.ok(action, `${player} must own forced ${choice}`);
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

function assertRawOnlyRoost(boundary: Session['boundary'], actor: PlayerID) {
  const record = `|-singleturn|${actor}a: Target|move: Roost`;
  for (const player of PLAYERS) {
    const observation = boundary.perspectives[player].observation;
    assert.ok(observation.protocol_prefix.includes(record));
    const team = player === actor ? observation.view.self_team : observation.view.opponent_team;
    assert.deepEqual(team.find(pokemon => pokemon.active)!.types, ['Ice', 'Flying']);
    assert.ok(!team.find(pokemon => pokemon.active)!.volatiles.includes('roost'));
    assert.ok(!JSON.stringify(observation).includes('typeWas'));
  }
}

for (const actor of PLAYERS) {
  test(`Roost ${actor}: pinned one-turn Flying removal is raw-only and expires before the next request`, async () => {
    const direct = battle(actor);
    const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, 'ordinary');
    try {
      // Roost cannot apply at full HP. First establish the ordinary public
      // damage state, then use Roost ahead of the slower Earthquake.
      const damage = choices(actor, 'move 2', 'move 1');
      direct.makeChoices(damage.p1, damage.p2);
      const damaged = await step(session, damage);
      const damagedTwin = await step(twin, damage);
      assert.equal(damaged.transition_id, damagedTwin.transition_id);
      const first = choices(actor, 'move 1', 'move 2');
      direct.makeChoices(first.p1, first.p2);
      const result = await step(session, first);
      const twinResult = await step(twin, first);
      assert.equal(result.transition_id, twinResult.transition_id);
      assert.equal(result.boundary.state_fingerprint, twinResult.boundary.state_fingerprint);
      assert.ok(direct.log.includes(`|-singleturn|${actor}a: Target|move: Roost`));
      assert.ok(direct.log.some(record => record.startsWith(`|-damage|${actor}a: Target|`)), 'Ground damage proves Flying was removed during the turn');
      assert.deepEqual(direct[actor].active[0].getTypes(), ['Ice', 'Flying']);
      assertRawOnlyRoost(result.boundary, actor);
      for (const player of PLAYERS) {
        const published = python(result.record_bundles[player]);
        assert.equal(published.status, 0, published.stderr);
      }

      const continuation = choices(actor, 'move 2', 'move 1');
      const next = await step(session, continuation);
      const nextTwin = await step(twin, continuation);
      assert.equal(next.transition_id, nextTwin.transition_id);
      assert.equal(next.boundary.state_fingerprint, nextTwin.boundary.state_fingerprint);
      assert.ok(next.record_bundles[actor].input_observation.protocol_prefix.includes(`|-singleturn|${actor}a: Target|move: Roost`));
    } finally {
      direct.destroy(); await session.close(); await twin.close();
    }
  });
}

for (const actor of PLAYERS) {
  test(`Roost ${actor}: generated Ditto Imposter copies the source-private Roost type without publishing it`, async () => {
    const direct = imposterBattle(actor);
    const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, 'imposter');
    const target = actor === 'p1' ? 'p2' : 'p1';
    let restored: Session | undefined;
    let restoredTwin: Session | undefined;
    let faintRestored: Session | undefined;
    let faintRestoredTwin: Session | undefined;
    let postFaintRestored: Session | undefined;
    let postFaintRestoredTwin: Session | undefined;
    try {
      // Damage first: a full-HP Roost fails and does not create the active
      // condition required by transformInto's private `typeWas` branch.
      const damage = choices(actor, 'move 2', 'move 4');
      direct.makeChoices(damage.p1, damage.p2);
      const damaged = await step(session, damage);
      const damagedTwin = await step(twin, damage);
      assert.equal(damaged.transition_id, damagedTwin.transition_id);

      // Articuno's Roost runs before the slower U-turn. U-turn pauses for the
      // pivot replacement before residual, leaving the source condition live.
      const pivot = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(pivot.p1, pivot.p2);
      const consumedRequestSnapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
      const beforeReplacement = await step(session, pivot);
      const beforeReplacementTwin = await step(twin, pivot);
      assert.equal(beforeReplacement.transition_id, beforeReplacementTwin.transition_id);
      assert.equal(beforeReplacement.boundary.kind, 'one_sided_forced_switch');
      assert.equal(beforeReplacement.boundary.perspectives[actor].observation.request?.force_switch, true);
      assert.equal(beforeReplacement.boundary.perspectives[target].observation.request?.wait, true);
      for (const player of PLAYERS) {
        const observation = beforeReplacement.boundary.perspectives[player].observation;
        const publicTarget = player === target ? observation.view.self_team : observation.view.opponent_team;
        assert.deepEqual(publicTarget.find(pokemon => pokemon.active)!.types, ['Ice', 'Flying']);
        assert.ok(observation.protocol_prefix.includes(`|-singleturn|${target}a: Target|move: Roost`));
        assert.ok(!JSON.stringify(observation).includes('typeWas'));
        assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|')));
      }
      assert.ok(!JSON.stringify(beforeReplacement.boundary.perspectives[actor].observation).includes('Zoroark'));

      // A serialized source snapshot at the consumed-request boundary restores
      // the same public views and the same one-sided selection without exposing
      // the simulator-only Roost condition.
      [restored, restoredTwin] = await sessions(consumedRequestSnapshot, actor, 'imposter');
      assert.equal(restored.boundary.state_fingerprint, beforeReplacement.boundary.state_fingerprint);
      assert.equal(restored.boundary.kind, beforeReplacement.boundary.kind);
      for (const player of PLAYERS) {
        assert.deepEqual(restored.boundary.perspectives[player].observation.view, beforeReplacement.boundary.perspectives[player].observation.view);
        assert.deepEqual(restored.boundary.perspectives[player].observation.request, beforeReplacement.boundary.perspectives[player].observation.request);
      }

      // A stale or wrong-player forced choice cannot consume the live request.
      const frozen = JSON.stringify(session.boundary);
      await assert.rejects(session.stepForcedSwitch({...selectForced(session, actor, 'switch 2'), player: target}), /unsupported-forced-switch-boundary/);
      await assert.rejects(session.stepForcedSwitch({...selectForced(session, actor, 'switch 2'), rqid: 999}), /request ID does not match/);
      assert.equal(JSON.stringify(session.boundary), frozen);

      direct.choose(actor, 'switch 2');
      const copied = await session.stepForcedSwitch(selectForced(session, actor, 'switch 2'));
      const copiedTwin = await twin.stepForcedSwitch(selectForced(twin, actor, 'switch 2'));
      const copiedRestored = await restored.stepForcedSwitch(selectForced(restored, actor, 'switch 2'));
      const copiedRestoredTwin = await restoredTwin.stepForcedSwitch(selectForced(restoredTwin, actor, 'switch 2'));
      assert.equal(copied.transition_id, copiedTwin.transition_id);
      assert.equal(copiedRestored.transition_id, copiedRestoredTwin.transition_id);
      assert.equal(copied.boundary.state_fingerprint, copiedTwin.boundary.state_fingerprint);
      assert.equal(copied.boundary.state_fingerprint, copiedRestored.boundary.state_fingerprint);
      assert.equal(copied.boundary.kind, 'joint_actionable');
      assert.deepEqual(Object.keys(copied.record_bundles), [actor]);
      const transform = `|-transform|${actor}a: Copy|${target}a: Target|[from] ability: Imposter`;
      assert.ok(direct.log.includes(transform), direct.log.join('\n'));
      // `transformInto` uses the target's typeWas (Ice/Flying), rather than
      // its one-turn current Ice type. Residual then removes Roost before the
      // successor request, leaving both publicly established defensive types.
      assert.deepEqual(direct[actor].active[0].getTypes(), ['Ice', 'Flying']);
      assert.deepEqual(direct[target].active[0].getTypes(), ['Ice', 'Flying']);
      for (const player of PLAYERS) {
        const observation = copied.boundary.perspectives[player].observation;
        const own = player === actor ? observation.view.self_team : observation.view.opponent_team;
        const foe = player === target ? observation.view.self_team : observation.view.opponent_team;
        assert.deepEqual(own.find(pokemon => pokemon.active)!.types, ['Ice', 'Flying']);
        assert.deepEqual(foe.find(pokemon => pokemon.active)!.types, ['Ice', 'Flying']);
        assert.ok(observation.protocol_prefix.includes(transform));
        assert.ok(!JSON.stringify(observation).includes('typeWas'));
        assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|')));
        assert.equal(python(copied.record_bundles[actor]).status, 0);
      }
      assert.ok(!JSON.stringify(copied.boundary.perspectives[actor].observation).includes('Zoroark'));

      // A faint cannot interleave with the U-turn replacement: BattleActions
      // completes the switch-in (and Imposter's onSwitchIn) before the residual
      // queue expires Roost. The first source-shaped opportunity to faint Copy
      // is the following joint request. This witnesses cleanup after the exact
      // transformInto branch rather than projecting its private `typeWas`.
      const postTransformSnapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
      [faintRestored, faintRestoredTwin] = await sessions(postTransformSnapshot, actor, 'imposter-faint');
      assert.equal(faintRestored.boundary.state_fingerprint, copied.boundary.state_fingerprint);
      assert.equal(faintRestored.boundary.kind, copied.boundary.kind);

      const frozenBeforeFaint = JSON.stringify(session.boundary);
      const stale = {
        p1: select(session, 'p1', choices(actor, 'move 4', 'move 3').p1),
        p2: select(session, 'p2', choices(actor, 'move 4', 'move 3').p2),
      };
      await assert.rejects(session.step({...stale, [actor]: {...stale[actor], rqid: 999}}), /request ID does not match/);
      assert.equal(JSON.stringify(session.boundary), frozenBeforeFaint);

      // The original target leaves first, retaining the transformed Ditto's
      // public Ice/Flying form while avoiding any source identity projection.
      const sourceLeaves = choices(actor, 'move 4', 'switch 3');
      direct.makeChoices(sourceLeaves.p1, sourceLeaves.p2);
      const afterSourceLeaves = await step(session, sourceLeaves);
      const afterSourceLeavesTwin = await step(twin, sourceLeaves);
      const afterSourceLeavesRestored = await step(faintRestored, sourceLeaves);
      const afterSourceLeavesRestoredTwin = await step(faintRestoredTwin, sourceLeaves);
      assert.equal(afterSourceLeaves.transition_id, afterSourceLeavesTwin.transition_id);
      assert.equal(afterSourceLeavesRestored.transition_id, afterSourceLeavesRestoredTwin.transition_id);
      assert.equal(afterSourceLeaves.boundary.state_fingerprint, afterSourceLeavesRestored.boundary.state_fingerprint);
      for (const player of PLAYERS) {
        const observation = afterSourceLeaves.boundary.perspectives[player].observation;
        const team = player === actor ? observation.view.self_team : observation.view.opponent_team;
        const copy = team.find(pokemon => pokemon.name === 'Copy')!;
        assert.equal(copy.active, true);
        assert.equal(copy.transformed, true);
        assert.deepEqual(copy.types, ['Ice', 'Flying']);
        assert.ok(!JSON.stringify(observation).includes('typeWas'));
      }

      // The switched-in Rock attacker now faints the already transformed
      // Ditto. This is the first source-valid faint opportunity after the
      // replacement/residual ordering above.
      const faintChoices = choices(actor, 'move 4', 'move 1');
      direct.makeChoices(faintChoices.p1, faintChoices.p2);
      const postFaintSnapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
      const fainted = await step(session, faintChoices);
      const faintedTwin = await step(twin, faintChoices);
      const faintedRestored = await step(faintRestored, faintChoices);
      const faintedRestoredTwin = await step(faintRestoredTwin, faintChoices);
      assert.equal(fainted.transition_id, faintedTwin.transition_id);
      assert.equal(faintedRestored.transition_id, faintedRestoredTwin.transition_id);
      assert.equal(fainted.boundary.state_fingerprint, faintedTwin.boundary.state_fingerprint);
      assert.equal(fainted.boundary.state_fingerprint, faintedRestored.boundary.state_fingerprint);
      assert.equal(fainted.boundary.kind, 'one_sided_forced_switch');
      for (const player of PLAYERS) {
        const observation = fainted.boundary.perspectives[player].observation;
        const team = player === actor ? observation.view.self_team : observation.view.opponent_team;
        const copy = team.find(pokemon => pokemon.name === 'Copy')!;
        assert.equal(copy.active, false);
        assert.equal(copy.fainted, true);
        assert.equal(copy.transformed, false);
        assert.deepEqual(copy.types, ['Normal']);
        assert.ok(observation.protocol_prefix.includes(`|faint|${actor}a: Copy`));
        assert.ok(!JSON.stringify(observation).includes('typeWas'));
        assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|')));
        assert.equal(python(fainted.record_bundles[player]).status, 0);
      }

      // Restore the exact post-faint forced request before it is consumed and
      // reject a stale candidate. A real replacement then continues both
      // lineages from matching boundaries without retaining copied typing.
      [postFaintRestored, postFaintRestoredTwin] = await sessions(postFaintSnapshot, actor, 'imposter-faint-replacement');
      assert.equal(postFaintRestored.boundary.state_fingerprint, fainted.boundary.state_fingerprint);
      const frozenAfterFaint = JSON.stringify(session.boundary);
      await assert.rejects(session.stepForcedSwitch({...selectForced(session, actor, 'switch 3'), rqid: 999}), /request ID does not match/);
      assert.equal(JSON.stringify(session.boundary), frozenAfterFaint);
      direct.choose(actor, 'switch 3');
      const replacement = await session.stepForcedSwitch(selectForced(session, actor, 'switch 3'));
      const replacementTwin = await twin.stepForcedSwitch(selectForced(twin, actor, 'switch 3'));
      const replacementRestored = await postFaintRestored.stepForcedSwitch(selectForced(postFaintRestored, actor, 'switch 3'));
      const replacementRestoredTwin = await postFaintRestoredTwin.stepForcedSwitch(selectForced(postFaintRestoredTwin, actor, 'switch 3'));
      assert.equal(replacement.transition_id, replacementTwin.transition_id);
      assert.equal(replacementRestored.transition_id, replacementRestoredTwin.transition_id);
      assert.equal(replacement.boundary.state_fingerprint, replacementRestored.boundary.state_fingerprint);
      assert.deepEqual(Object.keys(replacement.record_bundles), [actor]);
      assert.equal(python(replacement.record_bundles[actor]).status, 0);

      // The restored source state also exercises ordinary switch cleanup. It
      // cannot retain copied Transform or temporary Roost type state once Copy
      // leaves the active slot.
      const switched = await step(restored, choices(actor, 'switch 3', 'move 1'));
      for (const player of PLAYERS) {
        const team = player === actor ? switched.boundary.perspectives[player].observation.view.self_team
          : switched.boundary.perspectives[player].observation.view.opponent_team;
        const copy = team.find(pokemon => pokemon.name === 'Copy')!;
        assert.equal(copy.active, false);
        assert.equal(copy.transformed, false);
        assert.deepEqual(copy.types, ['Normal']);
        assert.equal(python(switched.record_bundles[player]).status, 0);
      }

      // Whirlwind reaches the pinned drag cleanup without revealing the
      // private Roost condition or retaining Transform on the dragged Copy.
      const dragged = await step(restoredTwin, choices(actor, 'move 4', 'move 2'));
      for (const player of PLAYERS) {
        const team = player === actor ? dragged.boundary.perspectives[player].observation.view.self_team
          : dragged.boundary.perspectives[player].observation.view.opponent_team;
        const copy = team.find(pokemon => pokemon.name === 'Copy')!;
        assert.equal(copy.active, false);
        assert.equal(copy.transformed, false);
        assert.deepEqual(copy.types, ['Normal']);
        assert.ok(!JSON.stringify(dragged.boundary.perspectives[player].observation).includes('typeWas'));
      }

      // The selection runner restores the pre-consumption snapshot internally.
      // Its twin identity and ordinary continuation after the post-faint
      // replacement prove deterministic replay.
      const continuation = choices(actor, 'move 1', 'move 2');
      const next = await step(session, continuation);
      const nextTwin = await step(twin, continuation);
      assert.equal(next.transition_id, nextTwin.transition_id);
      assert.equal(next.boundary.state_fingerprint, nextTwin.boundary.state_fingerprint);
      for (const player of PLAYERS) {
        const team = player === actor ? next.boundary.perspectives[player].observation.view.self_team
          : next.boundary.perspectives[player].observation.view.opponent_team;
        const copy = team.find(pokemon => pokemon.name === 'Copy')!;
        assert.equal(copy.active, false);
        assert.equal(copy.transformed, false);
        assert.deepEqual(copy.types, ['Normal']);
        assert.equal(python(next.record_bundles[player]).status, 0);
      }
    } finally {
      direct.destroy(); await session.close(); await twin.close(); await restored?.close(); await restoredTwin?.close();
      await faintRestored?.close(); await faintRestoredTwin?.close();
      await postFaintRestored?.close(); await postFaintRestoredTwin?.close();
    }
  });
}

for (const actor of PLAYERS) {
  test(`Roost ${actor}: pre-expiry Sandstorm faint clears an active-Roost Imposter copy without publishing private state`, async () => {
    const direct = imposterBattle(actor);
    const target = actor === 'p1' ? 'p2' : 'p1';
    // A source-valid residual KO needs a pre-damaged Ditto. This fixture supplies
    // that public-HP precondition, then has the real Sand Stream residual call
    // faintMessages between transformInto and Roost's order-25 duration end.
    direct[actor].pokemon[1].hp = 1;
    const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, 'imposter-residual-ko');
    let restored: Session | undefined;
    let restoredTwin: Session | undefined;
    let postFaintRestored: Session | undefined;
    let postFaintRestoredTwin: Session | undefined;
    try {
      // Sand Stream is a generated Tyranitar root. It establishes the
      // source-backed order-1 field residual while Articuno remains off field.
      const sand = choices(actor, 'move 3', 'switch 3');
      direct.makeChoices(sand.p1, sand.p2);
      const sandResult = await step(session, sand);
      const sandTwin = await step(twin, sand);
      assert.equal(sandResult.transition_id, sandTwin.transition_id);
      assert.ok(direct.log.includes('|-weather|Sandstorm|[from] ability: Sand Stream|[of] ' + `${target}a: Warden`));

      // Articuno returns and takes public damage so that Roost can establish its
      // one-turn private condition on the following turn.
      const damageTarget = choices(actor, 'move 2', 'switch 3');
      direct.makeChoices(damageTarget.p1, damageTarget.p2);
      const damaged = await step(session, damageTarget);
      const damagedTwin = await step(twin, damageTarget);
      assert.equal(damaged.transition_id, damagedTwin.transition_id);

      // Roost begins before slower U-turn. The forced Ditto replacement is the
      // only live transformInto boundary; it is still before residual.
      const pivot = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(pivot.p1, pivot.p2);
      const replacementSnapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
      const beforeReplacement = await step(session, pivot);
      const beforeReplacementTwin = await step(twin, pivot);
      assert.equal(beforeReplacement.transition_id, beforeReplacementTwin.transition_id);
      assert.equal(beforeReplacement.boundary.kind, 'one_sided_forced_switch');
      for (const player of PLAYERS) {
        const observation = beforeReplacement.boundary.perspectives[player].observation;
        const targetTeam = player === target ? observation.view.self_team : observation.view.opponent_team;
        assert.deepEqual(targetTeam.find(pokemon => pokemon.active)!.types, ['Ice', 'Flying']);
        assert.ok(observation.protocol_prefix.includes(`|-singleturn|${target}a: Target|move: Roost`));
        assert.ok(!JSON.stringify(observation).includes('typeWas'));
        if (player === actor) assert.ok(!JSON.stringify(observation).includes('Zoroark'));
        assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|')));
      }

      [restored, restoredTwin] = await sessions(replacementSnapshot, actor, 'imposter-residual-ko-restored');
      assert.equal(restored.boundary.state_fingerprint, beforeReplacement.boundary.state_fingerprint);
      const frozen = JSON.stringify(session.boundary);
      await assert.rejects(session.stepForcedSwitch({...selectForced(session, actor, 'switch 2'), rqid: 999}), /request ID does not match/);
      assert.equal(JSON.stringify(session.boundary), frozen);

      // Sandstorm is residual order 1. Its source handler emits upkeep and its
      // Weather callback faints the one-HP transformed Ditto before Roost's
      // duration handler at order 25. Poison/toxic are also order 9 and have
      // the same faintMessages-before-Roost lifecycle result.
      direct.choose(actor, 'switch 2');
      const fainted = await session.stepForcedSwitch(selectForced(session, actor, 'switch 2'));
      const faintedTwin = await twin.stepForcedSwitch(selectForced(twin, actor, 'switch 2'));
      const faintedRestored = await restored.stepForcedSwitch(selectForced(restored, actor, 'switch 2'));
      const faintedRestoredTwin = await restoredTwin.stepForcedSwitch(selectForced(restoredTwin, actor, 'switch 2'));
      assert.equal(fainted.transition_id, faintedTwin.transition_id);
      assert.equal(faintedRestored.transition_id, faintedRestoredTwin.transition_id);
      assert.equal(fainted.boundary.state_fingerprint, faintedTwin.boundary.state_fingerprint);
      assert.equal(fainted.boundary.state_fingerprint, faintedRestored.boundary.state_fingerprint);
      assert.equal(fainted.boundary.kind, 'one_sided_forced_switch');
      const transform = `|-transform|${actor}a: Copy|${target}a: Target|[from] ability: Imposter`;
      const upkeep = '|-weather|Sandstorm|[upkeep]';
      const faint = `|faint|${actor}a: Copy`;
      assert.ok(direct.log.includes(transform));
      assert.ok(direct.log.includes(upkeep));
      assert.ok(direct.log.includes(faint));
      assert.ok(direct.log.indexOf(transform) < direct.log.lastIndexOf(upkeep));
      assert.ok(direct.log.lastIndexOf(upkeep) < direct.log.indexOf(faint));
      assert.deepEqual(direct[target].active[0].getTypes(), ['Ice', 'Flying']);
      for (const player of PLAYERS) {
        const observation = fainted.boundary.perspectives[player].observation;
        const copyTeam = player === actor ? observation.view.self_team : observation.view.opponent_team;
        const targetTeam = player === target ? observation.view.self_team : observation.view.opponent_team;
        const copy = copyTeam.find(pokemon => pokemon.name === 'Copy')!;
        assert.equal(copy.active, false);
        assert.equal(copy.fainted, true);
        assert.equal(copy.transformed, false);
        assert.deepEqual(copy.types, ['Normal']);
        assert.deepEqual(targetTeam.find(pokemon => pokemon.active)!.types, ['Ice', 'Flying']);
        assert.ok(observation.protocol_prefix.includes(faint));
        assert.ok(!JSON.stringify(observation).includes('typeWas'));
        if (player === actor) assert.ok(!JSON.stringify(observation).includes('Zoroark'));
        assert.ok(!observation.protocol_prefix.some(record => record.startsWith('|request|')));
      }
      for (const bundle of Object.values(fainted.record_bundles)) {
        const published = python(bundle);
        assert.equal(published.status, 0, published.stderr);
        assert.ok(!published.stdout.includes('typeWas'));
        assert.ok(!published.stdout.includes('Zoroark'));
      }

      // Restore the actual post-faint owner-only replacement boundary, reject a
      // stale candidate, and continue both lineages after the residual KO.
      const postFaintSnapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
      [postFaintRestored, postFaintRestoredTwin] = await sessions(postFaintSnapshot, actor, 'imposter-residual-ko-post-faint');
      assert.equal(postFaintRestored.boundary.state_fingerprint, fainted.boundary.state_fingerprint);
      const frozenFaint = JSON.stringify(session.boundary);
      await assert.rejects(session.stepForcedSwitch({...selectForced(session, actor, 'switch 3'), rqid: 999}), /request ID does not match/);
      assert.equal(JSON.stringify(session.boundary), frozenFaint);
      direct.choose(actor, 'switch 3');
      const replacement = await session.stepForcedSwitch(selectForced(session, actor, 'switch 3'));
      const replacementTwin = await twin.stepForcedSwitch(selectForced(twin, actor, 'switch 3'));
      const replacementRestored = await postFaintRestored.stepForcedSwitch(selectForced(postFaintRestored, actor, 'switch 3'));
      const replacementRestoredTwin = await postFaintRestoredTwin.stepForcedSwitch(selectForced(postFaintRestoredTwin, actor, 'switch 3'));
      assert.equal(replacement.transition_id, replacementTwin.transition_id);
      assert.equal(replacementRestored.transition_id, replacementRestoredTwin.transition_id);
      assert.equal(replacement.boundary.state_fingerprint, replacementRestored.boundary.state_fingerprint);
      for (const bundle of Object.values(replacement.record_bundles)) {
        assert.equal(python(bundle).status, 0);
      }
      const continuation = choices(actor, 'move 1', 'move 4');
      const next = await step(session, continuation);
      const nextTwin = await step(twin, continuation);
      assert.equal(next.transition_id, nextTwin.transition_id);
      assert.equal(next.boundary.state_fingerprint, nextTwin.boundary.state_fingerprint);
    } finally {
      direct.destroy(); await session.close(); await twin.close();
      await restored?.close(); await restoredTwin?.close();
      await postFaintRestored?.close(); await postFaintRestoredTwin?.close();
    }
  });
}

for (const actor of PLAYERS) {
  test(`Roost ${actor}: Terastallized Flying user retains its public Tera type without a temporary type projection`, async () => {
    const direct = battle(actor, 'Flying', 'Empoleon');
    const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, 'tera');
    try {
      const damage = choices(actor, 'move 2', 'move 1');
      direct.makeChoices(damage.p1, damage.p2);
      await step(session, damage); await step(twin, damage);
      const roost = choices(actor, 'move 1 terastallize', 'move 2');
      direct.makeChoices(roost.p1, roost.p2);
      const result = await step(session, roost);
      const twinResult = await step(twin, roost);
      assert.equal(result.transition_id, twinResult.transition_id);
      const singleturn = `|-singleturn|${actor}a: Target|move: Roost`;
      const hint = '|-hint|If a Terastallized Pokemon uses Roost, it remains Flying-type.';
      assert.ok(direct.log.includes(hint));
      assert.ok(!direct.log.includes(singleturn));
      assert.deepEqual(direct[actor].active[0].getTypes(), ['Flying']);
      for (const player of PLAYERS) {
        const observation = result.boundary.perspectives[player].observation;
        const team = player === actor ? observation.view.self_team : observation.view.opponent_team;
        assert.deepEqual(team.find(pokemon => pokemon.active)!.types, ['Flying']);
        assert.ok(observation.protocol_prefix.includes(hint));
        assert.ok(!observation.protocol_prefix.includes(singleturn));
        assert.ok(!JSON.stringify(observation).includes('typeWas'));
        const published = python(result.record_bundles[player]);
        assert.equal(published.status, 0, published.stderr);
      }
    } finally {
      direct.destroy(); await session.close(); await twin.close();
    }
  });
}
