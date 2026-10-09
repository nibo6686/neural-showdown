import { healingWishBattle } from './slot_consequence_fixtures';
import { assertPublicConsequenceTamperMatrix } from './public_consequence_test_helpers';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { createPipelineIntegrationSession, type PipelineBoundary } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;
const OPTIONS = { include_wait_requests: true, include_possible_roles: false };
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;

function team(text: string) {
  return Teams.import(text)!;
}

function choices(actor: PlayerID, sourceChoice: string, foeChoice: string): Record<PlayerID, string> {
  return actor === 'p1' ? {p1: sourceChoice, p2: foeChoice} : {p1: foeChoice, p2: sourceChoice};
}

function noReplacementBattle(actor: PlayerID): Battle {
  const wisherOnly = team(`Wisher (Gardevoir)
Ability: Synchronize
- Healing Wish
- Splash
`);
  const foe = team(`Foe (Sableye)
Ability: Prankster
- Splash

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? wisherOnly : foe});
  battle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? wisherOnly : foe});
  return battle;
}

async function restoredSessions(serialized: Record<string, unknown>, actor: PlayerID, suffix: string): Promise<[Session, Session]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {
      return this.resetFromSerialized(structuredClone(serialized), options);
    };
    return await Promise.all([0, 1].map(async (index) => createPipelineIntegrationSession({
      battle_id: `healing-wish-${actor}-${suffix}-${index}`, format: 'gen9randombattle', seed: [1, 2, 3, 4],
      observation_schema_version: 'observable-battle-state/v2',
    }))) as [Session, Session];
  } finally {
    LocalBattleEnv.prototype.resetWithOptions = reset;
  }
}

function select(session: Session, player: PlayerID, choice: string) {
  const request = session.boundary.perspectives[player].observation.request!;
  const action = request.legal_actions.actions.find((candidate) => candidate?.choice === choice);
  assert.ok(action, `${player} must own ${choice}`);
  return canonicalActionFromLegalAction(request, action.index);
}

async function step(session: Session, next: Record<PlayerID, string>) {
  return session.step({p1: select(session, 'p1', next.p1), p2: select(session, 'p2', next.p2)});
}

function validateInPython(bundle: unknown) {
  return spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(bundle), encoding: 'utf8',
    env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')},
  });
}

function assertNoPublicPendingSlot(boundary: PipelineBoundary) {
  for (const player of PLAYERS) {
    const observation = boundary.perspectives[player].observation;
    const serialized = JSON.stringify(observation);
    // A public move name may remain in the protocol prefix or request. The
    // private slot condition and its EffectState fields may not.
    assert.ok(!serialized.includes('slotConditions') && !serialized.includes('sourceSlot')
      && !serialized.includes('"duration"'), 'private slot condition must not enter public observation');
    assert.ok([...observation.view.self_team, ...observation.view.opponent_team]
      .every((pokemon) => !pokemon.volatiles.includes('healingwish')));
  }
}

for (const actor of PLAYERS) {
  test(`Healing Wish ${actor}: replacement restores public HP/status without projecting private slot state`, async () => {
    const direct = healingWishBattle(actor, true);
    const [session, twin] = await restoredSessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, 'restore');
    try {
      const activation = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(activation.p1, activation.p2);
      const pending = await step(session, activation);
      const pendingTwin = await step(twin, activation);
      assert.equal(pending.boundary.kind, 'one_sided_forced_switch');
      assert.equal(pending.transition_id, pendingTwin.transition_id);
      assert.equal(pending.boundary.state_fingerprint, pendingTwin.boundary.state_fingerprint);
      assert.ok(direct[actor].slotConditions[0].healingwish, 'pending condition belongs only to the simulator slot');
      assertNoPublicPendingSlot(pending.boundary);

      direct.choose(actor, 'switch 2');
      const resolved = await session.stepForcedSwitch(select(session, actor, 'switch 2'));
      const resolvedTwin = await twin.stepForcedSwitch(select(twin, actor, 'switch 2'));
      assert.equal(resolved.transition_id, resolvedTwin.transition_id);
      assert.equal(resolved.boundary.state_fingerprint, resolvedTwin.boundary.state_fingerprint);
      const publicHeal = new RegExp(`^\\|-heal\\|${actor}a: Recipient\\|100/100\\|\\[from\\] move: Healing Wish$`);
      assert.ok(direct.log.some((record) => publicHeal.test(record)));
      assert.ok(!direct.log.some((record) => record.startsWith(`|-curestatus|${actor}a: Recipient`)));
      for (const player of PLAYERS) {
        const observation = resolved.boundary.perspectives[player].observation;
        assert.ok(observation.protocol_prefix.some((record) => publicHeal.test(record)));
        assert.ok(!observation.protocol_prefix.some((record) => record.startsWith(`|-curestatus|${actor}a: Recipient`)));
        const visibleTeam = player === actor ? observation.view.self_team : observation.view.opponent_team;
        const recipient = visibleTeam.find((pokemon) => pokemon.name === 'Recipient');
        assert.equal(recipient?.hp_ratio, 1);
        assert.equal(recipient?.status, null);
      }
      const published = validateInPython(resolved.record_bundles[actor]);
      assert.equal(published.status, 0, published.stderr);
      assertNoPublicPendingSlot(resolved.boundary);

      const continuation = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(continuation.p1, continuation.p2);
      const next = await step(session, continuation);
      const nextTwin = await step(twin, continuation);
      assert.equal(next.transition_id, nextTwin.transition_id, 'restored v2 twins continue deterministically');
      assert.equal(next.boundary.state_fingerprint, nextTwin.boundary.state_fingerprint);
      // The replacement selection publishes only the actor by design. Its
      // immediate joint continuation carries the resolved public evidence as
      // the input boundary for both actual v2 Python bundles.
      for (const player of PLAYERS) {
        const bundle = next.record_bundles[player];
        assert.ok(bundle.input_observation.protocol_prefix.some((record) => publicHeal.test(record)));
        const serialized = JSON.stringify(bundle.input_observation);
        assert.ok(!serialized.includes('slotConditions') && !serialized.includes('sourceSlot')
          && !serialized.includes('"duration"'));
        assert.ok([...bundle.input_observation.view.self_team, ...bundle.input_observation.view.opponent_team]
          .every((pokemon) => !pokemon.volatiles.includes('healingwish')));
        assertPublicConsequenceTamperMatrix(bundle, 'Recipient');
        const published = validateInPython(bundle);
        assert.equal(published.status, 0, published.stderr);
      }
    } finally {
      direct.destroy();
      await session.close();
      await twin.close();
    }
  });

  test(`Healing Wish ${actor}: healthy replacement keeps the private condition without a fabricated public result`, async () => {
    const direct = healingWishBattle(actor, false);
    const [session, twin] = await restoredSessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, 'healthy');
    try {
      const activation = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(activation.p1, activation.p2);
      await step(session, activation);
      await step(twin, activation);
      direct.choose(actor, 'switch 2');
      const resolved = await session.stepForcedSwitch(select(session, actor, 'switch 2'));
      const resolvedTwin = await twin.stepForcedSwitch(select(twin, actor, 'switch 2'));
      assert.equal(resolved.transition_id, resolvedTwin.transition_id);
      const publicHeal = new RegExp(`^\\|-heal\\|${actor}a: Recipient\\|.*\\|\\[from\\] move: Healing Wish$`);
      assert.ok(!direct.log.some((record) => publicHeal.test(record)));
      assert.ok(direct[actor].slotConditions[0].healingwish, 'pinned onSwap retains an inapplicable condition');
      for (const player of PLAYERS) {
        assert.ok(!resolved.boundary.perspectives[player].observation.protocol_prefix.some((record) => publicHeal.test(record)));
      }
      const published = validateInPython(resolved.record_bundles[actor]);
      assert.equal(published.status, 0, published.stderr);
      assertNoPublicPendingSlot(resolved.boundary);
    } finally {
      direct.destroy();
      await session.close();
      await twin.close();
    }
  });

  test(`Healing Wish ${actor}: terminal before replacement has no public healing completion`, async () => {
    const direct = healingWishBattle(actor, true, true);
    const [session, twin] = await restoredSessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, 'terminal');
    try {
      const finish = choices(actor, 'move 1', 'move 3');
      direct.makeChoices(finish.p1, finish.p2);
      const result = await step(session, finish);
      const resultTwin = await step(twin, finish);
      assert.equal(result.boundary.kind, 'terminal');
      assert.equal(result.transition_id, resultTwin.transition_id);
      const publicHeal = new RegExp(`^\\|-heal\\|${actor}a: Recipient\\|.*\\|\\[from\\] move: Healing Wish$`);
      assert.ok(!direct.log.some((record) => publicHeal.test(record)));
      for (const player of PLAYERS) {
        assert.ok(!result.boundary.perspectives[player].observation.protocol_prefix.some((record) => publicHeal.test(record)));
        const published = validateInPython(result.record_bundles[player]);
        assert.equal(published.status, 0, published.stderr);
      }
      assertNoPublicPendingSlot(result.boundary);
    } finally {
      direct.destroy();
      await session.close();
      await twin.close();
    }
  });

  test(`Healing Wish ${actor}: source cancels before creating a slot condition when no replacement exists`, async () => {
    const direct = noReplacementBattle(actor);
    const [session, twin] = await restoredSessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, 'cancel');
    try {
      const attempted = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(attempted.p1, attempted.p2);
      const result = await step(session, attempted);
      const resultTwin = await step(twin, attempted);
      assert.equal(result.transition_id, resultTwin.transition_id);
      assert.ok(direct.log.some((record) => record === `|-fail|${actor}a: Wisher`));
      assert.ok(!direct[actor].slotConditions[0].healingwish);
      for (const player of PLAYERS) {
        const prefix = result.boundary.perspectives[player].observation.protocol_prefix;
        assert.ok(prefix.some((record) => record === `|-fail|${actor}a: Wisher`));
        assert.ok(!prefix.some((record) => record.includes('[from] move: Healing Wish')));
        const published = validateInPython(result.record_bundles[player]);
        assert.equal(published.status, 0, published.stderr);
      }
      assertNoPublicPendingSlot(result.boundary);
    } finally {
      direct.destroy();
      await session.close();
      await twin.close();
    }
  });
}
