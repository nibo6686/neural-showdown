import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction, type CanonicalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { validateRawProtocolRecord } from '../src/observable_state';
import { createPipelineIntegrationSession, projectPipelineProtocolPrefix, type PipelineBoundary } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';

const PLAYERS = ['p1', 'p2'] as const;
const CASES = [
  { id: 'bloodmoon', name: 'Blood Moon', species: 'Ursaluna-Bloodmoon', alternate: 'Moonlight' },
  { id: 'gigatonhammer', name: 'Gigaton Hammer', species: 'Tinkaton', alternate: 'Play Rough' },
] as const;
type RepeatCase = typeof CASES[number];
type Session = Awaited<ReturnType<typeof createPipelineIntegrationSession>>;

function team(text: string) { return Teams.import(text)!; }
function other(player: PlayerID): PlayerID { return player === 'p1' ? 'p2' : 'p1'; }
function choices(actor: PlayerID, actorChoice: string, foeChoice: string): Record<PlayerID, string> {
  return actor === 'p1' ? { p1: actorChoice, p2: foeChoice } : { p1: foeChoice, p2: actorChoice };
}

function makeBattle(actor: PlayerID, repeat: RepeatCase): Battle {
  const repeated = team(`Moon (${repeat.species})
Ability: ${repeat.id === 'bloodmoon' ? "Mind's Eye" : 'Mold Breaker'}
Level: 1
- ${repeat.name}
- ${repeat.alternate}
- Calm Mind

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  // A level-100 Lumineon is faster than the controlled level-one generated
  // repeat-use holder and survives its first two bounded attacks. Its first
  // Encore fails before a last move exists; the second then overrides the
  // holder's deliberately queued alternate move.
  const encoer = team(`Encore (Lumineon)
Ability: Storm Drain
Level: 100
- Encore
- Splash

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  battle.setPlayer('p1', { name: 'One', team: actor === 'p1' ? repeated : encoer });
  battle.setPlayer('p2', { name: 'Two', team: actor === 'p2' ? repeated : encoer });
  return battle;
}

async function restoredSessions(serialized: Record<string, unknown>, suffix: string): Promise<[Session, Session]> {
  const reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {
      return this.resetFromSerialized(structuredClone(serialized), options);
    };
    return await Promise.all([0, 1].map((index) => createPipelineIntegrationSession({
      battle_id: `repeat-use-${suffix}-${index}`,
      format: 'gen9randombattle',
      seed: [1, 2, 3, 4],
      observation_schema_version: 'observable-battle-state/v2',
    }))) as [Session, Session];
  } finally {
    LocalBattleEnv.prototype.resetWithOptions = reset;
  }
}

function select(session: Session, player: PlayerID, choice: string): CanonicalAction {
  const request = session.boundary.perspectives[player].observation.request!;
  const action = request.legal_actions.actions.find((candidate) => candidate?.choice === choice);
  assert.ok(action, `${player} must own ${choice}`);
  return canonicalActionFromLegalAction(request, action.index);
}

async function step(session: Session, next: Record<PlayerID, string>) {
  return session.step({ p1: select(session, 'p1', next.p1), p2: select(session, 'p2', next.p2) });
}

function publish(bundle: unknown) {
  return spawnSync(process.env.PYTHON || 'python3', ['-m', 'neural.pipeline_record'], {
    input: JSON.stringify(bundle), encoding: 'utf8',
    env: { ...process.env, PYTHONPATH: path.resolve(__dirname, '../../../trainer/src') },
  });
}

function assertTwins(left: Awaited<ReturnType<typeof step>>, right: Awaited<ReturnType<typeof step>>) {
  assert.equal(left.transition_id, right.transition_id);
  assert.equal(left.boundary.state_fingerprint, right.boundary.state_fingerprint);
  for (const player of PLAYERS) assert.deepEqual(
    left.boundary.perspectives[player].observation.protocol_prefix,
    right.boundary.perspectives[player].observation.protocol_prefix,
  );
}

function assertPrivacy(boundary: PipelineBoundary, actor: PlayerID) {
  for (const player of PLAYERS) {
    const observation = boundary.perspectives[player].observation;
    assert.equal(observation.request?.player, player, 'only the owner receives a request');
    assert.ok(!observation.protocol_prefix.some((record) => record.startsWith('|request|') || record.startsWith('|split|')));
    const opposite = observation.view.opponent_team.find((pokemon) => pokemon.name === 'Moon');
    if (player !== actor) {
      assert.equal(opposite?.moves, undefined, 'opponent view cannot receive the holder request moves');
      assert.equal(opposite?.item, undefined, 'opponent view cannot receive an unrevealed item');
    }
  }
}

for (const actor of PLAYERS) {
  for (const repeat of CASES) {
    test(`CE-05 repeat-use ${repeat.id} ${actor}: Encore override leaves the next owned request authoritative`, async () => {
      const direct = makeBattle(actor, repeat);
      const [session, twin] = await restoredSessions(structuredClone(direct.toJSON()) as Record<string, unknown>, `${actor}-${repeat.id}`);
      const foe = other(actor);
      const hint = `|-hint|Some effects can force a Pokemon to use ${repeat.name} again in a row.`;
      try {
        // Normal repeat-use restriction comes from the owner request. The first
        // Encore has no target lastMove and fails, leaving the repeat move
        // disabled and the alternate action legal.
        const first = choices(actor, 'move 1', 'move 1');
        const preRestrictionRepeat = select(session, actor, 'move 1');
        direct.makeChoices(first.p1, first.p2);
        const restricted = await step(session, first);
        assertTwins(restricted, await step(twin, first));
        const request = restricted.boundary.perspectives[actor].observation.request!;
        assert.equal(request.active?.moves[0]?.id, repeat.id);
        assert.equal(request.active?.moves[0]?.disabled, true);
        assert.equal(request.active?.moves[1]?.disabled, false);
        assert.ok(!restricted.boundary.perspectives[actor].observation.protocol_prefix.includes(hint));
        assertPrivacy(restricted.boundary, actor);

        // The actual canonical repeat action from before DisableMove is now
        // stale. It must stop before a candidate is restored or committed.
        const before = JSON.stringify(session.boundary);
        await assert.rejects(() => session.step({
          [actor]: preRestrictionRepeat,
          [foe]: select(session, foe, 'move 2'),
        } as Record<PlayerID, CanonicalAction>));
        assert.equal(JSON.stringify(session.boundary), before, 'rejected retry must preserve the committed boundary');

        // Faster Encore reaches OverrideAction before runMove. It rewrites the
        // queued alternate action to the prior cantusetwice move, which emits
        // only the exact post-use raw hint. The following owner request is
        // Struggle; the hint itself does not create the action mask.
        const encore = choices(actor, 'move 2', 'move 1');
        direct.makeChoices(encore.p1, encore.p2);
        const forced = await step(session, encore);
        assertTwins(forced, await step(twin, encore));
        for (const player of PLAYERS) {
          const observation = forced.boundary.perspectives[player].observation;
          assert.ok(observation.protocol_prefix.includes(hint));
          assert.equal(publish(forced.record_bundles[player]).status, 0);
        }
        const forcedRequest = forced.boundary.perspectives[actor].observation.request!;
        assert.deepEqual(forcedRequest.active?.moves.map((move) => [move.id, move.disabled]), [['struggle', false]]);
        assert.ok(forcedRequest.legal_actions.available_indices.some((index) =>
          forcedRequest.legal_actions.actions[index]?.choice === 'move 1'),
        `Struggle must be an owned legal action: ${JSON.stringify(forcedRequest.legal_actions)}`);
        assertPrivacy(forced.boundary, actor);

        // Restored v2 candidates consume the source-provided Struggle request
        // identically. This continuation is the actual transition-bundle
        // publication proof after the repeat-use boundary.
        const struggle = choices(actor, 'move 1', 'move 2');
        direct.makeChoices(struggle.p1, struggle.p2);
        const continued = await step(session, struggle);
        assertTwins(continued, await step(twin, struggle));
        for (const player of PLAYERS) assert.equal(publish(continued.record_bundles[player]).status, 0);
        assertPrivacy(continued.boundary, actor);
      } finally {
        direct.destroy();
        await session.close();
        await twin.close();
      }
    });
  }
}

test('CE-05 repeat-use hints are exact raw-only evidence before projection', () => {
  const valid = [
    '|-hint|Some effects can force a Pokemon to use Blood Moon again in a row.',
    '|-hint|Some effects can force a Pokemon to use Gigaton Hammer again in a row.',
  ];
  for (const record of valid) {
    assert.doesNotThrow(() => validateRawProtocolRecord(record));
    assert.deepEqual(projectPipelineProtocolPrefix([record]), [record]);
  }
  for (const malformed of [
    '|-hint|Some effects can force a Pokemon to use Blood Moon again in a row.|extra',
    '|-hint|Some effects can force a Pokemon to use Blood Moon again in a row. ',
    '|-hint|Some effects can force a Pokemon to use bloodmoon again in a row.',
    '|-hint|Some effects can force a Pokemon to use Thunderbolt again in a row.',
    '|-hint| Some effects can force a Pokemon to use Gigaton Hammer again in a row.',
  ]) {
    assert.throws(() => validateRawProtocolRecord(malformed), /repeat-use hint requires its exact source form/);
    assert.throws(() => projectPipelineProtocolPrefix([malformed]), /unsupported-observable-protocol/);
  }
});
