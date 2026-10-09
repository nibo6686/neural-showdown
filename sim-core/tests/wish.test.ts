import { wishBattle } from './wish_fixture';
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
import type { PlayerID } from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;
const OPTIONS = { include_wait_requests: true, include_possible_roles: false };

function choices(actor: PlayerID, sourceChoice: string, foeChoice: string): Record<PlayerID, string> {
  return actor === 'p1' ? {p1: sourceChoice, p2: foeChoice} : {p1: foeChoice, p2: sourceChoice};
}

function select(session: Awaited<ReturnType<typeof createPipelineIntegrationSession>>, player: PlayerID, choice: string) {
  const request = session.boundary.perspectives[player].observation.request!;
  const action = request.legal_actions.actions.find((candidate) => candidate?.choice === choice);
  assert.ok(action, `${player} must own ${choice}`);
  return canonicalActionFromLegalAction(request, action.index);
}

async function step(
  session: Awaited<ReturnType<typeof createPipelineIntegrationSession>>,
  next: Record<PlayerID, string>,
) {
  return session.step({p1: select(session, 'p1', next.p1), p2: select(session, 'p2', next.p2)});
}

async function restoredSession(actor: PlayerID, mode: Parameters<typeof wishBattle>[1]) {
  const direct = wishBattle(actor, mode);
  const serialized = structuredClone(direct.toJSON()) as Record<string, unknown>;
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {
      return this.resetFromSerialized(structuredClone(serialized), options);
    };
    const session = await createPipelineIntegrationSession({
      battle_id: `wish-${mode}-${actor}`, format: 'gen9randombattle', seed: [1, 2, 3, 4],
      observation_schema_version: 'observable-battle-state/v2',
    });
    return {direct, session};
  } finally {
    LocalBattleEnv.prototype.resetWithOptions = reset;
  }
}

function validateInPython(bundle: unknown) {
  return spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(bundle), encoding: 'utf8',
    env: {...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src')},
  });
}

function allPublicPokemon(result: {boundary: PipelineBoundary}, player: PlayerID) {
  const view = result.boundary.perspectives[player].observation.view;
  return [...view.self_team, ...view.opponent_team];
}

function assertNoTypedWish(result: {boundary: PipelineBoundary}) {
  for (const player of PLAYERS) {
    assert.ok(allPublicPokemon(result, player).every((pokemon) => !pokemon.volatiles.includes('wish')),
      'a private slot condition must not be fabricated as a public volatile');
  }
}

// This proves direct Gen 9 Random Battle membership separately from the small
// source-lifecycle teams below.
test('Wish has a pinned Gen 9 Random Battle generated-set witness', () => {
  const source = Teams.generate('gen9randombattle', {seed: [2, 2, 3, 4]})[3];
  assert.equal(source.species, 'Jirachi');
  assert.ok(source.moves.includes('wish'));
});

for (const actor of PLAYERS) {
  test(`Wish ${actor}: pending public evidence resolves on the switched-in recipient and restores deterministically`, async () => {
    const {direct, session} = await restoredSession(actor, 'heal');
    let twin: Awaited<ReturnType<typeof createPipelineIntegrationSession>> | undefined;
    try {
      const snapshot = structuredClone(direct.toJSON()) as Record<string, unknown>;
      const reset = LocalBattleEnv.prototype.resetWithOptions;
      try {
        LocalBattleEnv.prototype.resetWithOptions = function (options) {
          return this.resetFromSerialized(structuredClone(snapshot), options);
        };
        twin = await createPipelineIntegrationSession({
          battle_id: `wish-heal-twin-${actor}`, format: 'gen9randombattle', seed: [1, 2, 3, 4],
          observation_schema_version: 'observable-battle-state/v2',
        });
      } finally {
        LocalBattleEnv.prototype.resetWithOptions = reset;
      }
      const pendingChoices = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(pendingChoices.p1, pendingChoices.p2);
      const pending = await step(session, pendingChoices);
      const pendingTwin = await step(twin, pendingChoices);
      assert.equal(pending.transition_id, pendingTwin.transition_id,
        'independently restored candidates must preserve the private pending slot');
      assert.equal(pending.boundary.state_fingerprint, pendingTwin.boundary.state_fingerprint);
      for (const player of PLAYERS) assert.deepEqual(
        pending.boundary.perspectives[player].observation.protocol_prefix,
        pendingTwin.boundary.perspectives[player].observation.protocol_prefix,
      );
      const moveRecord = `|move|${actor}a: Wisher|Wish|${actor}a: Wisher`;
      assert.ok(direct.log.includes(moveRecord));
      assert.doesNotThrow(() => validateRawProtocolRecord(moveRecord));
      assert.deepEqual(projectPipelineProtocolPrefix([moveRecord]), [moveRecord]);
      for (const player of PLAYERS) {
        const observation = pending.boundary.perspectives[player].observation;
        assert.ok(observation.protocol_prefix.includes(moveRecord));
        assert.ok(!observation.protocol_prefix.some((record) => record.startsWith('|request|') || record.startsWith('|split|')));
        assert.equal(observation.request?.player, player);
        assert.equal(validateInPython(pending.record_bundles[player]).status, 0);
      }
      assertNoTypedWish(pending);

      // Stealth Rock makes the new slot occupant visibly need the delayed heal.
      // The source is now benched; the wisher tag must remain the actual source,
      // while the target is the public current occupant of that slot.
      const resolveChoices = choices(actor, 'switch 2', 'move 2');
      direct.makeChoices(resolveChoices.p1, resolveChoices.p2);
      const resolved = await step(session, resolveChoices);
      const resolvedTwin = await step(twin, resolveChoices);
      assert.equal(resolved.transition_id, resolvedTwin.transition_id);
      assert.equal(resolved.boundary.state_fingerprint, resolvedTwin.boundary.state_fingerprint);
      const publicHeal = new RegExp(`^\\|-heal\\|${actor}a: Recipient\\|[^|]+\\|\\[from\\] move: Wish\\|\\[wisher\\] Wisher$`);
      assert.ok(direct.log.some((record) => publicHeal.test(record)), 'pinned Wish must emit recipient HP and original wisher evidence');
      for (const player of PLAYERS) {
        const observation = resolved.boundary.perspectives[player].observation;
        assert.ok(observation.protocol_prefix.some((record) => publicHeal.test(record)));
        const team = player === actor ? observation.view.self_team : observation.view.opponent_team;
        assert.equal(team.find((pokemon) => pokemon.name === 'Recipient')?.hp_ratio, 1);
        assertPublicConsequenceTamperMatrix(resolved.record_bundles[player], 'Recipient');
        assert.equal(validateInPython(resolved.record_bundles[player]).status, 0);
      }
      assertNoTypedWish(resolved);
    } finally {
      direct.destroy();
      await session.close();
      await twin?.close();
    }
  });

  test(`Wish ${actor}: drag chooses the public current slot occupant without fabricating a timer`, async () => {
    const {direct, session} = await restoredSession(actor, 'drag');
    try {
      const pendingChoices = choices(actor, 'move 1', 'move 1');
      direct.makeChoices(pendingChoices.p1, pendingChoices.p2);
      await step(session, pendingChoices);
      const dragChoices = choices(actor, 'move 2', 'move 4');
      direct.makeChoices(dragChoices.p1, dragChoices.p2);
      const resolved = await step(session, dragChoices);
      const drag = `|drag|${actor}a: Reserve|Eevee, `;
      const heal = new RegExp(`^\\|-heal\\|${actor}a: Reserve\\|[^|]+\\|\\[from\\] move: Wish\\|\\[wisher\\] Wisher$`);
      assert.ok(direct.log.some((record) => record.startsWith(drag)));
      assert.ok(direct.log.some((record) => heal.test(record)));
      for (const player of PLAYERS) {
        const prefix = resolved.boundary.perspectives[player].observation.protocol_prefix;
        assert.ok(prefix.some((record) => record.startsWith(drag)));
        assert.ok(prefix.some((record) => heal.test(record)));
        assert.equal(validateInPython(resolved.record_bundles[player]).status, 0);
      }
      assertNoTypedWish(resolved);
    } finally {
      direct.destroy();
      await session.close();
    }
  });

  for (const mode of ['source-faint', 'recipient-faint', 'terminal'] as const) {
    test(`Wish ${actor}: ${mode} removes a pending consequence without an invented public result`, async () => {
      const {direct, session} = await restoredSession(actor, mode);
      try {
        // Source-faint and recipient-faint need the foe's Splash on turn one;
        // terminal retains its Explosion for turn two.
        const pendingChoices = choices(actor, 'move 1', mode === 'terminal' ? 'move 1' : 'move 2');
        direct.makeChoices(pendingChoices.p1, pendingChoices.p2);
        await step(session, pendingChoices);
        const finishing = mode === 'recipient-faint'
          ? choices(actor, 'switch 2', 'move 3')
          : choices(actor, 'move 2', mode === 'terminal' ? 'move 2' : 'move 3');
        direct.makeChoices(finishing.p1, finishing.p2);
        const result = await step(session, finishing);
        const wishHeal = new RegExp(`^\\|-heal\\|${actor}a: .*\\|[^|]+\\|\\[from\\] move: Wish\\|\\[wisher\\] Wisher$`);
        assert.ok(!direct.log.some((record) => wishHeal.test(record)));
        for (const player of PLAYERS) {
          const prefix = result.boundary.perspectives[player].observation.protocol_prefix;
          assert.ok(!prefix.some((record) => wishHeal.test(record)));
          assert.equal(validateInPython(result.record_bundles[player]).status, 0);
        }
        assertNoTypedWish(result);
        if (mode === 'terminal') {
          assert.equal(result.boundary.kind, 'terminal');
        } else {
          assert.equal(result.boundary.kind, 'one_sided_forced_switch');
          const before = session.boundary;
          const stale = select(session, actor, 'switch 2');
          await assert.rejects(session.stepForcedSwitch({...stale, rqid: 999}), /request ID does not match/);
          assert.equal(session.boundary, before, 'a rejected replacement must keep the cleared consequence boundary');
          const replacement = await session.stepForcedSwitch(stale);
          assert.equal(validateInPython(replacement.record_bundles[actor]).status, 0);
          assertNoTypedWish(replacement);
        }
      } finally {
        direct.destroy();
        await session.close();
      }
    });
  }
}
