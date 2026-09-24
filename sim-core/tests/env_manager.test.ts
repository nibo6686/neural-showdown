import assert from 'node:assert/strict';
import test from 'node:test';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { EnvironmentManager, LocalBattleEnv } from '../src/env_manager';
import { classifyPipelineRequestState, projectPipelineProtocolPrefix, projectPipelineStepResult } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';
import { lifecycleBattle, lifecycleChoices, prepareLifecycle, LIFECYCLE_OPTIONS, LIFECYCLE_SEED } from './helpers/state_lifecycle';

const REPORT_REQUESTS = { include_wait_requests: true, include_possible_roles: false };

for (const actor of ['p1', 'p2'] as const) {
  for (const scenario of ['switch', 'drag', 'faint', 'shed-tail', 'failed-shed-tail'] as const) {
    test(`real ${scenario} lifecycle for ${actor} preserves typed state, prefix and privacy through restoration`, async () => {
      const battle = lifecycleBattle(actor);
      const env = new LocalBattleEnv('lifecycle-live', 'gen9randombattle', LIFECYCLE_SEED);
      const restored = new LocalBattleEnv('lifecycle-restored', 'gen9randombattle', LIFECYCLE_SEED);
      const other = actor === 'p1' ? 'p2' : 'p1';
      try {
        prepareLifecycle(battle, actor, scenario !== 'shed-tail');
        let result = await env.resetFromSerialized(battle.toJSON(), LIFECYCLE_OPTIONS);
        const prefix = [...result.log_delta];
        let observations = projectPipelineStepResult(result, 'lifecycle', projectPipelineProtocolPrefix(prefix));
        const initial = JSON.stringify(observations);
        const initialObservations = observations;
        const donorBefore = result.views[actor]!.self_team.find((p) => p.name === 'Donor')!;
        assert.equal(donorBefore.boosts.atk, 2);
        assert.ok(donorBefore.volatiles.includes('torment'));

        const advance = async (choices: Partial<Record<PlayerID, string>>) => {
          const before = observations;
          result = await env.stepWithOptions(choices, LIFECYCLE_OPTIONS);
          prefix.push(...result.log_delta);
          observations = projectPipelineStepResult(result, 'lifecycle', projectPipelineProtocolPrefix(prefix));
          for (const p of ['p1', 'p2'] as const) {
            assert.deepEqual(observations[p].protocol_prefix.slice(0, before[p].event_cursor), before[p].protocol_prefix);
            assert.ok(observations[p].protocol_prefix.every((line) => !line.startsWith('|request|')));
            assert.equal(observations[p].request?.player, p);
            for (const foe of observations[p].view.opponent_team) {
              assert.equal('boosts' in foe, false);
              assert.equal('stats' in foe, false);
              assert.equal('moves' in foe, false);
              assert.equal('item' in foe, false);
            }
          }
        };
        const assertCleared = (name: string) => {
          for (const p of ['p1', 'p2'] as const) {
            const team = p === actor ? result.views[p]!.self_team : result.views[p]!.opponent_team;
            const pokemon = team.find((entry) => entry.name === name)!;
            assert.deepEqual(pokemon.boosts, {});
            assert.deepEqual(pokemon.volatiles, []);
          }
        };
        if (scenario === 'shed-tail') {
          await advance(lifecycleChoices(actor, 'move 3'));
          assert.equal(result.requests[actor]?.force_switch, true);
          assert.equal(result.requests[other]?.wait, true);
          assert.ok(observations[actor].protocol_prefix.some((line) => line.includes('Substitute|[from] move: Shed Tail')));
          const snapshot = env.serializeBattle();
          const replay = await restored.resetFromSerialized(snapshot, LIFECYCLE_OPTIONS);
          const replayPrefix = [...replay.log_delta];
          assert.deepEqual(projectPipelineStepResult(replay, 'lifecycle', projectPipelineProtocolPrefix(replayPrefix)), observations);
          await advance({ [actor]: 'switch 2' });
          const replayNext = await restored.stepWithOptions({ [actor]: 'switch 2' }, LIFECYCLE_OPTIONS);
          replayPrefix.push(...replayNext.log_delta);
          assert.deepEqual(projectPipelineStepResult(replayNext, 'lifecycle', projectPipelineProtocolPrefix(replayPrefix)), observations);
          assert.equal(restored.captureSeededSnapshot().state_fingerprint, env.captureSeededSnapshot().state_fingerprint);
          assert.ok(observations[actor].protocol_prefix.some((line) => line.includes('|[from] Shed Tail')));
          assertCleared('Donor');
          for (const p of ['p1', 'p2'] as const) {
            const team = p === actor ? result.views[p]!.self_team : result.views[p]!.opponent_team;
            const receiver = team.find((entry) => entry.name === 'Receiver')!;
            assert.deepEqual(receiver.boosts, {});
            assert.deepEqual(receiver.volatiles, ['substitute']);
            assert.ok(receiver.active);
          }
          // The copy remains through the next ordinary move/request, not just switch emission.
          await advance(lifecycleChoices(actor, 'move 1'));
          assert.deepEqual(result.views[actor]!.self_team[0].volatiles, ['substitute']);
          await advance(lifecycleChoices(actor, 'switch 2'));
          assertCleared('Receiver'); assertCleared('Donor');
        } else {
          if (scenario === 'failed-shed-tail') {
            await advance(lifecycleChoices(actor, 'move 3'));
            assert.ok(result.log_delta.some((line) => line.includes('|-fail|') && line.includes('Shed Tail')));
            assert.equal(result.requests[actor]?.force_switch, false);
            assert.ok(result.views[actor]!.self_team[0].volatiles.includes('substitute'));
          }
          if (scenario === 'faint') {
            await advance(lifecycleChoices(actor, 'move 4'));
            assert.ok(result.log_delta.some((line) => line.startsWith(`|faint|${actor}`)));
            assertCleared('Donor');
            assert.ok(result.views[actor]!.self_team.find((p) => p.name === 'Donor')!.fainted);
            await advance({ [actor]: 'switch 2' });
          } else {
            await advance(scenario === 'drag'
              ? lifecycleChoices(actor, 'move 1', 'move 2')
              : lifecycleChoices(actor, 'switch 2'));
            if (scenario === 'drag') assert.ok(result.log_delta.some((line) => line.startsWith(`|drag|${actor}`)));
          }
          assertCleared('Donor'); assertCleared('Receiver');
          if (scenario !== 'faint') {
            await advance(lifecycleChoices(actor, 'switch 2'));
            assertCleared('Donor');
            assert.ok(result.views[actor]!.self_team[0].active);
            assert.equal(result.views[actor]!.self_team[0].name, 'Donor');
          }
        }
        assert.equal(JSON.stringify(initialObservations), initial);
      } finally {
        battle.destroy(); await env.close(); await restored.close();
      }
    });
  }
}

test('same seed produces the same initial self team state', async () => {
  const manager = new EnvironmentManager();
  const seed = [1, 2, 3, 4];

  const env1 = manager.createEnv('gen9randombattle', seed, {
    p1: { controller: 'external' },
    p2: { controller: 'external' },
  }).env_id;
  const env2 = manager.createEnv('gen9randombattle', seed, {
    p1: { controller: 'external' },
    p2: { controller: 'external' },
  }).env_id;

  try {
    const reset1 = await manager.resetEnv(env1);
    const reset2 = await manager.resetEnv(env2);
    assert.ok(reset1.views.p1);
    assert.ok(reset2.views.p1);
    const team1 = reset1.views.p1.self_team.map((pokemon) => pokemon.species);
    const team2 = reset2.views.p1.self_team.map((pokemon) => pokemon.species);
    assert.deepEqual(team1, team2);
  } finally {
    await manager.closeAll();
  }
});

test('random vs random battles terminate without external input', async () => {
  const manager = new EnvironmentManager();
  const envId = manager.createEnv('gen9randombattle', [5, 6, 7, 8], {
    p1: { controller: 'random' },
    p2: { controller: 'random' },
  }).env_id;

  try {
    const result = await manager.resetEnv(envId);
    assert.equal(result.terminated, true);
    assert.ok(result.winner === 'p1' || result.winner === 'p2' || result.winner === 'tie');
  } finally {
    await manager.closeAll();
  }
});

test('response shaping can return only p1 without log delta or possible roles', async () => {
  const manager = new EnvironmentManager();
  const envId = manager.createEnv('gen9randombattle', [9, 10, 11, 12], {
    p1: { controller: 'external' },
    p2: { controller: 'random' },
  }).env_id;

  try {
    const result = await manager.resetEnv(envId, {
      view_players: ['p1'],
      include_log_delta: false,
      include_possible_roles: false,
    });
    assert.ok(result.views.p1);
    assert.equal(result.views.p2, undefined);
    assert.ok(result.requests.p1 !== undefined);
    assert.equal(result.requests.p2, undefined);
    assert.equal(result.log_delta.length, 0);
    assert.ok(result.views.p1?.opponent_team.every((pokemon) => pokemon.possible_roles.length === 0));
  } finally {
    await manager.closeAll();
  }
});

test('invalid external choices return the pending request instead of hanging', async () => {
  const manager = new EnvironmentManager();
  const envId = manager.createEnv('gen9randombattle', [21, 22, 23, 24], {
    p1: { controller: 'external' },
    p2: { controller: 'random' },
  }).env_id;

  try {
    const initial = await manager.resetEnv(envId, {
      view_players: ['p1'],
      include_log_delta: false,
      include_possible_roles: false,
    });
    assert.ok(initial.requests.p1);

    const result = await Promise.race([
      manager.stepEnv(
        envId,
        { p1: 'move 99' },
        {
          view_players: ['p1'],
          include_log_delta: false,
          include_possible_roles: false,
        },
      ),
      new Promise<never>((_resolve, reject) => setTimeout(() => reject(new Error('step timed out')), 1000)),
    ]);

    assert.equal(result.terminated, false);
    assert.ok(result.requests.p1);
    assert.deepEqual(result.requests.p1?.legal_actions.available_indices, initial.requests.p1?.legal_actions.available_indices);
    const diagnostics = manager.describeEnv(envId);
    assert.match(JSON.stringify(diagnostics), /Invalid choice|Unavailable choice/);
  } finally {
    await manager.closeAll();
  }
});

test('canonical submissions reject stale actions before raw choice forwarding', async () => {
  const manager = new EnvironmentManager();
  const envId = manager.createEnv('gen9randombattle', [31, 32, 33, 34], {
    p1: { controller: 'external' },
    p2: { controller: 'random' },
  }).env_id;

  try {
    const initial = await manager.resetEnv(envId, {
      view_players: ['p1'],
      include_log_delta: false,
      include_possible_roles: false,
    });
    const request = initial.requests.p1;
    assert.ok(request);
    const action = canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0]);
    await assert.rejects(
      manager.stepCanonicalEnv(envId, { p1: { ...action, rqid: 999 } }),
      /request ID does not match/,
    );
    const result = await manager.stepCanonicalEnv(envId, { p1: action }, {
      view_players: ['p1'],
      include_log_delta: false,
      include_possible_roles: false,
    });
    assert.ok(result.views.p1);
  } finally {
    await manager.closeAll();
  }
});

test('real forced-switch waits are opt-in, private, non-actionable and preserved by restoration', async () => {
  const env = new LocalBattleEnv('wait-report', 'gen9randombattle', [101, 202, 303, 404]);
  const restored = new LocalBattleEnv('wait-restore', 'gen9randombattle', [101, 202, 303, 404]);
  try {
    let result = await env.resetWithOptions(REPORT_REQUESTS);
    const log = [...result.log_delta];
    for (let step = 0; step < 20 && !result.requests.p1?.wait && !result.requests.p2?.wait; step++) {
      const p1 = env.getRequest('p1');
      const p2 = env.getRequest('p2');
      assert.ok(p1 && p2);
      result = await env.stepWithCanonicalOptions({
        p1: canonicalActionFromLegalAction(p1, p1.legal_actions.available_indices[0]),
        p2: canonicalActionFromLegalAction(p2, p2.legal_actions.available_indices[0]),
      }, REPORT_REQUESTS);
      log.push(...result.log_delta);
    }
    const waiting: PlayerID = result.requests.p1?.wait ? 'p1' : 'p2';
    const acting: PlayerID = waiting === 'p1' ? 'p2' : 'p1';
    assert.equal(result.requests[waiting]?.wait, true);
    assert.equal(result.requests[acting]?.force_switch, true);
    assert.deepEqual(result.requests[waiting]?.legal_actions.available_indices, []);
    assert.ok(result.requests[waiting]?.legal_actions.mask.every((value) => !value));
    assert.ok(result.requests[waiting]?.legal_actions.actions.every((value) => value === null));
    assert.equal(env.getRequest(waiting), null);
    await assert.rejects(env.stepWithOptions({ [waiting]: 'default' }, REPORT_REQUESTS), /does not have a pending request/);

    const snapshot = env.captureSeededSnapshot();
    const replay = await restored.resetFromSerialized(snapshot.simulator_state, REPORT_REQUESTS);
    assert.equal(restored.captureSeededSnapshot().state_fingerprint, snapshot.state_fingerprint);
    assert.deepEqual(replay.requests, result.requests);
    assert.equal(restored.getRequest(waiting), null);
    const originalStates = projectPipelineStepResult(result, 'wait-battle', projectPipelineProtocolPrefix(log));
    const restoredStates = projectPipelineStepResult(replay, 'wait-battle', projectPipelineProtocolPrefix(replay.log_delta));
    for (const player of ['p1', 'p2'] as const) {
      const state = originalStates[player];
      const twin = restoredStates[player];
      assert.equal(classifyPipelineRequestState(state), player === waiting ? 'waiting' : 'forced_switch');
      assert.equal(classifyPipelineRequestState(twin), classifyPipelineRequestState(state));
      assert.equal(state.request?.player, player);
      assert.deepEqual(twin.request, state.request);
      assert.equal(twin.snapshot_phase, state.snapshot_phase);
      assert.equal(twin.event_cursor, state.event_cursor);
      assert.deepEqual(twin.protocol_prefix, state.protocol_prefix);
      assert.ok(state.protocol_prefix.every((line) => !line.startsWith('|request|')));
    }
    assert.equal(originalStates[waiting].snapshot_phase, 'post_resolution');
    assert.equal(originalStates[waiting].decision_availability.available, false);

    const ownOnly = await env.stepWithOptions({}, { ...REPORT_REQUESTS, view_players: [waiting] });
    assert.deepEqual(Object.keys(ownOnly.requests), [waiting]);
    assert.deepEqual(Object.keys(ownOnly.views), [waiting]);
    assert.equal(ownOnly.requests[waiting]?.player, waiting);
    // Mutating a returned request cannot alter a later report or pending choice.
    ownOnly.requests[waiting]!.wait = false;
    const stillWaiting = await env.stepWithOptions({}, REPORT_REQUESTS);
    assert.equal(stillWaiting.requests[waiting]?.wait, true);
    const legacy = await env.stepWithOptions({});
    assert.equal(legacy.requests[waiting], null);
    assert.deepEqual(legacy.requests[acting], result.requests[acting]);
    assert.equal(env.captureSeededSnapshot().state_fingerprint, snapshot.state_fingerprint);
  } finally {
    await env.close();
    await restored.close();
  }
});

test('submitted requests stay absent through restoration while the other player can still choose', async () => {
  for (const submitted of ['p1', 'p2'] as const) {
    const pending = submitted === 'p1' ? 'p2' : 'p1';
    const env = new LocalBattleEnv(`consumed-${submitted}`, 'gen9randombattle', [101, 202, 303, 404]);
    const restored = new LocalBattleEnv(`consumed-restore-${submitted}`, 'gen9randombattle', [101, 202, 303, 404]);
    try {
      const initial = await env.resetWithOptions(REPORT_REQUESTS);
      const request = initial.requests[submitted]!;
      const firstAction = canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0]);
      const afterChoice = await env.stepWithCanonicalOptions({ [submitted]: firstAction }, REPORT_REQUESTS);
      assert.equal(afterChoice.requests[submitted], null);
      assert.ok(afterChoice.requests[pending]);
      const snapshot = env.captureSeededSnapshot();
      const replay = await restored.resetFromSerialized(snapshot.simulator_state, REPORT_REQUESTS);
      assert.deepEqual(replay.requests, afterChoice.requests);
      // Restoration replays public history before the latest private request;
      // compare private facts, not the extractor's last-writer source labels.
      const privateFacts = (result: typeof replay) => result.views[submitted]?.self_team.map((pokemon) => ({
        species: pokemon.species, stats: pokemon.stats, moves: pokemon.moves,
        item: pokemon.item, ability: pokemon.ability, tera_type: pokemon.tera_type,
      }));
      assert.deepEqual(privateFacts(replay), privateFacts(afterChoice));
      assert.equal(restored.getRequest(submitted), null);
      assert.equal(restored.captureSeededSnapshot().state_fingerprint, snapshot.state_fingerprint);
      const states = projectPipelineStepResult(replay, 'consumed-battle', projectPipelineProtocolPrefix(replay.log_delta));
      assert.equal(classifyPipelineRequestState(states[submitted]), 'requestless');
      assert.equal(classifyPipelineRequestState(states[pending]), 'actionable');
      const remaining = afterChoice.requests[pending]!;
      const secondAction = canonicalActionFromLegalAction(remaining, remaining.legal_actions.available_indices[0]);
      const next = await env.stepWithCanonicalOptions({ [pending]: secondAction }, REPORT_REQUESTS);
      const restoredNext = await restored.stepWithCanonicalOptions({ [pending]: secondAction }, REPORT_REQUESTS);
      assert.deepEqual(restoredNext.requests, next.requests);
      assert.equal(restored.captureSeededSnapshot().state_fingerprint, env.captureSeededSnapshot().state_fingerprint);
    } finally {
      await env.close();
      await restored.close();
    }
  }
});
