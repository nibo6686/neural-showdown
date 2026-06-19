import assert from 'node:assert/strict';
import test from 'node:test';
import { buildBeliefSnapshot } from '../src/belief_fork';
import { LocalBattleEnv } from '../src/env_manager';
import type { StepResultOptions } from '../src/types';

const OPTIONS: StepResultOptions = {
  view_players: ['p1', 'p2'],
  include_log_delta: true,
  include_possible_roles: false,
};

test('belief sampling is deterministic and independent of true hidden bench sets', async () => {
  const env = new LocalBattleEnv('belief-source', 'gen9randombattle', [101, 202, 303, 404], {
    p1: { controller: 'external' },
    p2: { controller: 'external' },
  });
  try {
    const result = await env.resetWithOptions(OPTIONS);
    const view = result.views.p1!;
    const serialized = env.serializeBattle() as any;
    const altered = structuredClone(serialized);
    const hidden = altered.sides[1].pokemon.find((mon: any) => !mon.isActive);
    hidden.set.moves = ['Splash'];
    hidden.set.item = 'Choice Band';
    hidden.set.ability = 'Truant';
    hidden.moveSlots = [];
    hidden.item = 'choiceband';
    hidden.ability = 'truant';

    for (const seed of [[9, 8, 7, 6], [1018, 2035, 3048, 4057], [2027, 4062, 6089, 8108]]) {
      const first = buildBeliefSnapshot(serialized, view, 'p1', 'gen9randombattle', seed);
      const second = buildBeliefSnapshot(altered, view, 'p1', 'gen9randombattle', seed);
      assert.deepEqual(first.metadata.sampled_sets, second.metadata.sampled_sets);
      assert.notEqual(first.metadata.sampled_sets.find(set => !set.revealed)?.moves.join(','), 'Splash');
    }

    const first = buildBeliefSnapshot(serialized, view, 'p1', 'gen9randombattle', [9, 8, 7, 6]);
    const different = buildBeliefSnapshot(serialized, view, 'p1', 'gen9randombattle', [9, 8, 7, 7]);
    assert.notDeepEqual(first.metadata.sampled_sets, different.metadata.sampled_sets);
  } finally {
    await env.close();
  }
});

test('belief sampling preserves publicly revealed opponent moves', async () => {
  const env = new LocalBattleEnv('belief-reveal', 'gen9randombattle', [101, 202, 303, 404], {
    p1: { controller: 'external' },
    p2: { controller: 'external' },
  });
  try {
    let result = await env.resetWithOptions(OPTIONS);
    const p1 = env.getAgentAction('p1', 'heuristic').choice;
    const p2 = env.getAgentAction('p2', 'heuristic').choice;
    result = await env.stepWithOptions({ p1, p2 }, OPTIONS);
    const view = result.views.p1!;
    const revealed = view.opponent_team.find(mon => mon.revealed_moves.length);
    assert.ok(revealed);

    const built = buildBeliefSnapshot(
      env.serializeBattle() as any,
      view,
      'p1',
      'gen9randombattle',
      [3, 4, 5, 6],
    );
    const sampled = built.metadata.sampled_sets.find(set => set.species === revealed.species);
    assert.ok(sampled);
    for (const move of revealed.revealed_moves) {
      assert.ok(sampled.moves.some(candidate => candidate.toLowerCase().replaceAll(' ', '') === move.toLowerCase().replaceAll(' ', '')));
    }
  } finally {
    await env.close();
  }
});

test('belief sampling preserves synthetic public item ability and tera constraints', async () => {
  const env = new LocalBattleEnv('belief-fields', 'gen9randombattle', [101, 202, 303, 404], {
    p1: { controller: 'external' },
    p2: { controller: 'external' },
  });
  try {
    const result = await env.resetWithOptions(OPTIONS);
    const view = structuredClone(result.views.p1!);
    const mon = view.opponent_team[0];
    mon.ability = 'Clear Body';
    mon.item = 'Leftovers';
    mon.terastallized = true;
    mon.tera_type = 'Fighting';
    for (const seed of [[9, 8, 7, 6], [1018, 2035, 3048, 4057], [2027, 4062, 6089, 8108]]) {
      const built = buildBeliefSnapshot(
        env.serializeBattle() as any,
        view,
        'p1',
        'gen9randombattle',
        seed,
      );
      const sampled = built.metadata.sampled_sets.find(set => set.species === mon.species);
      assert.equal(sampled?.ability, 'Clear Body');
      assert.equal(sampled?.item, 'Leftovers');
      assert.equal(sampled?.tera_type, 'Fighting');
    }
  } finally {
    await env.close();
  }
});
