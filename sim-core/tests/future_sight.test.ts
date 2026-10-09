import { futureSightBattle } from './slot_consequence_fixtures';
import { assertPublicConsequenceTamperMatrix } from './public_consequence_test_helpers';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { validateRawProtocolRecord } from '../src/observable_state';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix, type PipelineBoundary } from '../src/pipeline_integration';
import { PlayerStateExtractor } from '../src/state_extractor';
import type { PlayerID } from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;

function team(text: string) { return Teams.import(text)!; }
function other(actor: PlayerID): PlayerID { return actor === 'p1' ? 'p2' : 'p1'; }
function choices(actor: PlayerID, actorChoice: string, foeChoice: string): Record<PlayerID, string> {
  return actor === 'p1' ? {p1: actorChoice, p2: foeChoice} : {p1: foeChoice, p2: actorChoice};
}

async function sessions(serialized: Record<string, unknown>, actor: PlayerID, suffix: string): Promise<[Session, Session]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {
      return this.resetFromSerialized(structuredClone(serialized), options);
    };
    return await Promise.all([0, 1].map((index) => createPipelineIntegrationSession({
      battle_id: `future-sight-${actor}-${suffix}-${index}`,
      format: 'gen9randombattle', seed: [1, 2, 3, 4], observation_schema_version: 'observable-battle-state/v2',
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

function python(bundle: unknown) {
  return spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(bundle), encoding: 'utf8',
    env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')},
  });
}

function assertPrivateSlotState(boundary: PipelineBoundary) {
  for (const player of PLAYERS) {
    const observation = boundary.perspectives[player].observation;
    const serialized = JSON.stringify(observation);
    assert.ok(!serialized.includes('slotConditions') && !serialized.includes('endingTurn')
      && !serialized.includes('targetSlot') && !serialized.includes('moveData'));
    assert.ok([...observation.view.self_team, ...observation.view.opponent_team]
      .every((pokemon) => !pokemon.volatiles.includes('futuresight') && !pokemon.volatiles.includes('futuremove')));
    assert.ok(!observation.protocol_prefix.some((record) => record.startsWith('|request|') || record.startsWith('|split|')));
  }
}

function assertTwins(left: Awaited<ReturnType<typeof step>>, right: Awaited<ReturnType<typeof step>>) {
  assert.equal(left.transition_id, right.transition_id);
  assert.equal(left.boundary.state_fingerprint, right.boundary.state_fingerprint);
  for (const player of PLAYERS) assert.deepEqual(
    left.boundary.perspectives[player].observation.protocol_prefix,
    right.boundary.perspectives[player].observation.protocol_prefix,
  );
}

for (const actor of PLAYERS) {
  test(`Future Sight ${actor}: drag changes the public slot occupant and delayed damage uses only public evidence`, async () => {
    const direct = futureSightBattle(actor, 'drag');
    const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, 'drag');
    try {
      const activate = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(activate.p1, activate.p2);
      const pending = await step(session, activate);
      assertTwins(pending, await step(twin, activate));
      const start = `|-start|${actor}a: Seer|move: Future Sight`;
      assert.ok(direct.log.includes(start));
      for (const player of PLAYERS) assert.ok(pending.boundary.perspectives[player].observation.protocol_prefix.includes(start));
      assertPrivateSlotState(pending.boundary);

      const dragged = choices(actor, 'move 2', 'move 1');
      direct.makeChoices(dragged.p1, dragged.p2);
      assertTwins(await step(session, dragged), await step(twin, dragged));
      const target = other(actor);
      assert.ok(direct.log.some((record) => record.startsWith(`|drag|${target}a: Reserve|`)));

      const resolve = choices(actor, 'move 3', 'move 1');
      direct.makeChoices(resolve.p1, resolve.p2);
      const result = await step(session, resolve);
      assertTwins(result, await step(twin, resolve));
      const end = `|-end|${target}a: Reserve|move: Future Sight`;
      const damage = new RegExp(`^\\|-damage\\|${target}a: Reserve\\|(?:[1-9][0-9]*\\/[1-9][0-9]*|0 fnt)$`);
      assert.ok(direct.log.includes(end));
      assert.ok(direct.log.some((record) => damage.test(record)));
      const privateDamage = direct.log.find((record) => record.startsWith(`|-damage|${target}a: Reserve|`) && !record.endsWith('/100'));
      assert.ok(privateDamage, 'the engine split contains an owner-private exact HP branch');
      for (const player of PLAYERS) {
        const observation = result.boundary.perspectives[player].observation;
        assert.ok(observation.protocol_prefix.includes(end));
        assert.ok(observation.protocol_prefix.some((record) => damage.test(record)));
        assert.ok(!observation.protocol_prefix.includes(privateDamage));
        const visible = player === target ? observation.view.self_team : observation.view.opponent_team;
        assert.ok((visible.find((pokemon) => pokemon.name === 'Reserve')?.hp_ratio ?? 1) < 1);
        assertPublicConsequenceTamperMatrix(result.record_bundles[player], 'Reserve');
      const published = python(result.record_bundles[player]);
        assert.equal(published.status, 0, published.stderr);
      }
      assertPrivateSlotState(result.boundary);
    } finally {
      direct.destroy(); await session.close(); await twin.close();
    }
  });

  test(`Future Sight ${actor}: a fainted source still resolves against the living target slot`, async () => {
    const direct = futureSightBattle(actor, 'source-faint');
    const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, 'source-faint');
    try {
      const activate = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(activate.p1, activate.p2);
      assertTwins(await step(session, activate), await step(twin, activate));
      const sourceFaint = choices(actor, 'move 3', 'move 2');
      direct.makeChoices(sourceFaint.p1, sourceFaint.p2);
      const forced = await step(session, sourceFaint);
      const forcedTwin = await step(twin, sourceFaint);
      assert.equal(forced.boundary.kind, 'one_sided_forced_switch');
      assert.equal(forced.transition_id, forcedTwin.transition_id);
      direct.choose(actor, 'switch 2');
      const replacement = await session.stepForcedSwitch(select(session, actor, 'switch 2'));
      const replacementTwin = await twin.stepForcedSwitch(select(twin, actor, 'switch 2'));
      assert.equal(replacement.transition_id, replacementTwin.transition_id);
      const resolve = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(resolve.p1, resolve.p2);
      const result = await step(session, resolve);
      assertTwins(result, await step(twin, resolve));
      const target = other(actor);
      assert.ok(direct.log.includes(`|-end|${target}a: Target|move: Future Sight`));
      assert.ok(direct.log.some((record) => record.startsWith(`|-damage|${target}a: Target|`)));
      const privateDamage = direct.log.find((record) => record.startsWith(`|-damage|${target}a: Target|`) && !record.endsWith('/100'));
      assert.ok(privateDamage);
      for (const player of PLAYERS) {
        assert.equal(python(result.record_bundles[player]).status, 0);
        assert.ok(!result.boundary.perspectives[player].observation.protocol_prefix.includes(privateDamage));
      }
      assertPrivateSlotState(result.boundary);
    } finally {
      direct.destroy(); await session.close(); await twin.close();
    }
  });

  test(`Future Sight ${actor}: source switching preserves a private pending condition through restored continuation`, async () => {
    const direct = futureSightBattle(actor, 'switch');
    const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, 'switch');
    try {
      const activate = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(activate.p1, activate.p2);
      assertTwins(await step(session, activate), await step(twin, activate));
      const switched = choices(actor, 'switch 2', 'move 1');
      direct.makeChoices(switched.p1, switched.p2);
      assertTwins(await step(session, switched), await step(twin, switched));
      const resolve = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(resolve.p1, resolve.p2);
      const result = await step(session, resolve);
      assertTwins(result, await step(twin, resolve));
      const target = other(actor);
      assert.ok(direct.log.includes(`|-end|${target}a: Target|move: Future Sight`));
      assert.ok(direct.log.some((record) => record.startsWith(`|-damage|${target}a: Target|`)));
      const privateDamage = direct.log.find((record) => record.startsWith(`|-damage|${target}a: Target|`) && !record.endsWith('/100'));
      assert.ok(privateDamage);
      for (const player of PLAYERS) {
        assert.equal(python(result.record_bundles[player]).status, 0);
        assert.ok(!result.boundary.perspectives[player].observation.protocol_prefix.includes(privateDamage));
      }
      assertPrivateSlotState(result.boundary);
    } finally {
      direct.destroy(); await session.close(); await twin.close();
    }
  });

  for (const mode of ['faint', 'terminal'] as const) {
    test(`Future Sight ${actor}: ${mode} before residual emits no invented completion`, async () => {
      const direct = futureSightBattle(actor, mode);
      const [session, twin] = await sessions(structuredClone(direct.toJSON()) as Record<string, unknown>, actor, mode);
      try {
        const activate = choices(actor, 'move 1', 'move 1');
        direct.makeChoices(activate.p1, activate.p2);
        assertTwins(await step(session, activate), await step(twin, activate));
        const first = choices(actor, 'move 3', 'move 1');
        direct.makeChoices(first.p1, first.p2);
        assertTwins(await step(session, first), await step(twin, first));
        const finish = choices(actor, 'move 3', 'move 2');
        direct.makeChoices(finish.p1, finish.p2);
        const result = await step(session, finish);
        assertTwins(result, await step(twin, finish));
        const target = other(actor);
        assert.ok(!direct.log.some((record) => record === `|-end|${target}a: Target|move: Future Sight`));
        assert.ok(!direct.log.some((record) => record.startsWith(`|-damage|${target}a: Target|`)));
        assertPrivateSlotState(result.boundary);
        if (mode === 'terminal') assert.equal(result.boundary.kind, 'terminal');
      } finally {
        direct.destroy(); await session.close(); await twin.close();
      }
    });
  }
}

test('Future Sight source records are exact raw evidence and public damage alone changes typed HP', () => {
  const start = '|-start|p1a: Seer|move: Future Sight';
  const end = '|-end|p2a: Target|move: Future Sight';
  const damage = '|-damage|p2a: Target|50/100';
  assert.doesNotThrow(() => validateRawProtocolRecord(start));
  assert.doesNotThrow(() => validateRawProtocolRecord(end));
  assert.deepEqual(projectPipelineProtocolPrefix([start, end, damage]), [start, end, damage]);
  const extractor = new PlayerStateExtractor('future-sight-public-only', 'gen9randombattle', 'p1');
  extractor.consumeChunk('|switch|p2a: Target|Snorlax, L80|100/100');
  extractor.consumeChunk(`${start}\n${end}`);
  assert.equal(extractor.getView().opponent_team[0]?.hp_ratio, 1);
  assert.deepEqual(extractor.getView().opponent_team[0]?.volatiles, []);
  extractor.consumeChunk(damage);
  assert.equal(extractor.getView().opponent_team[0]?.hp_ratio, 0.5);

  for (const malformed of [
    '|-start|p1: Seer|move: Future Sight',
    '|-start|p1a: Seer|move: Future Sight|[silent]',
    '|-end|p2a: Target|move: Future Sigh',
    '|-end|p2: Target|move: Future Sight',
    '|-end|p2a: Target|move: Future Sight|[from] move: Future Sight',
    '|-start|p1a: Seer|move:  Future Sight',
    '|-start|p1a: Seer|move : Future Sight',
    '|-end|p2a: Target| move: Future Sight',
  ]) {
    assert.throws(() => validateRawProtocolRecord(malformed));
    assert.throws(() => projectPipelineProtocolPrefix([malformed]), /unsupported-observable-protocol/);
  }
  // An ordinary damage record remains generic: Future Sight does not invent a
  // delayed-damage provenance model where the pinned emitter has no tag.
  assert.doesNotThrow(() => validateRawProtocolRecord('|-damage|p2a: Target|50/100|[from] move: Tackle'));
});
