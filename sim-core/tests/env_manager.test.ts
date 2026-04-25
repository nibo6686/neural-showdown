import assert from 'node:assert/strict';
import test from 'node:test';
import { EnvironmentManager } from '../src/env_manager';

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
