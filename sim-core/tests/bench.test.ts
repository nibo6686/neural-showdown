import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import {LocalBattleEnv} from '../src/env_manager';
import {createAgent} from '../src/bench/agent';
import {BenchRunError, decisionInputs, runMatchup, summarize} from '../src/bench/runner';
import {canonicalActionFromLegalAction} from '../src/canonical_action';
import {withBornTeams} from './helpers/born_session';

const seeds: number[][] = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../../tools/bench/seeds.json'), 'utf8')).seeds;

test('bench: three paired seeds reproduce byte-identical random/heuristic game records', {timeout: 30000}, async () => {
  const first = await runMatchup('random', 'heuristic', seeds.slice(0, 3));
  const second = await runMatchup('random', 'heuristic', seeds.slice(0, 3));
  assert.equal(first.length, 6);
  assert.equal(JSON.stringify(first.map(g => g.record)), JSON.stringify(second.map(g => g.record)));
  for (const game of first) {
    assert.equal(game.record.illegal_choices, 0); assert.equal(game.record.rejected_choices, 0);
    assert.deepEqual(game.record.errors, []); assert.ok(game.timing.wall_time_ms > 0);
  }
  for (let i = 0; i < 6; i += 2) {
    assert.deepEqual(first[i].record.seed, first[i + 1].record.seed);
    assert.equal(first[i].record.agents.p1, first[i + 1].record.agents.p2);
  }
});

test('bench: illegal agent action fails the run rather than being retried or counted as a loss', async () => {
  await assert.rejects(runMatchup('random', 'heuristic', seeds.slice(0, 1), undefined, () => ({choose(request) {
    return {...canonicalActionFromLegalAction(request, request.legal_actions.available_indices[0]), index: 999};
  }})), error => {
    assert.ok(error instanceof BenchRunError);
    assert.equal(error.game.record.illegal_choices, 1);
    assert.equal(error.game.record.winner, null);
    assert.equal(error.game.record.errors.length, 1);
    return true;
  });
});

test('bench: runtime failures retain their cause and fail the run without becoming outcomes', async () => {
  await assert.rejects(runMatchup('random', 'heuristic', seeds.slice(0, 1), undefined, () => ({choose() {
    throw new Error('agent transport failed', {cause: new Error('disconnected')});
  }})), error => {
    assert.ok(error instanceof BenchRunError);
    assert.deepEqual(error.game.record.errors, ['agent transport failed: disconnected']);
    assert.equal(error.game.record.winner, null);
    assert.equal(error.game.record.illegal_choices, 0);
    return true;
  });
});

test('bench: agents receive only addressed request and perspective; foreign private mutations are invariant', async () => {
  const env = LocalBattleEnv.createSimulationOnly({id: 'bench-privacy', format: 'gen9randombattle', seed: seeds[0]});
  try {
    const state = await env.resetWithOptions({view_players: ['p1', 'p2']});
    const before = decisionInputs(state, 'p1');
    assert.ok(!('raw' in before[0]));
    const mutated = structuredClone(state);
    mutated.requests.p2!.raw = {secret: 'foreign-private-marker'};
    mutated.requests.p2!.side[0].item = 'foreign-private-marker';
    mutated.views.p2!.self_team[0].stats.atk = 999999;
    const after = decisionInputs(mutated, 'p1');
    assert.deepEqual(after, before);
    assert.ok(!JSON.stringify(after).includes('foreign-private-marker'));
    for (const name of ['random', 'greedy', 'heuristic'] as const) {
      const agent = createAgent(name);
      assert.deepEqual(await agent.choose(...before, () => 0.25), await agent.choose(...after, () => 0.25));
    }
    assert.ok(Object.isFrozen(before[0].side)); assert.ok(Object.isFrozen(before[1].self_team));
  } finally {await env.close();}
});

test('bench: Wilson reference bounds and tie-as-non-win accounting', () => {
  const games = Array.from({length: 100}, (_, i) => ({record: {game_id: String(i), seed: seeds[0], agents: {p1: 'a', p2: 'b'},
    side: 'p1' as const, winner: i < 50 ? 'p1' as const : i < 90 ? 'p2' as const : 'tie' as const,
    turns: 20, turn_limit_tie: false, illegal_choices: 0, rejected_choices: 0, errors: []}, timing: {game_id: String(i), wall_time_ms: 100}}));
  const summary = summarize(games);
  assert.equal(summary.win_rate, 0.5); assert.equal(summary.ties, 10); assert.equal(summary.losses, 40);
  assert.ok(Math.abs(summary.wilson_95[0] - 0.40383) < 0.00001);
  assert.ok(Math.abs(summary.wilson_95[1] - 0.59617) < 0.00001);
  assert.equal(summary.games_per_second, 10);
});

test('bench: uncertain own trapping removes speculative switches without changing native request authority', async () => {
  const env = LocalBattleEnv.createSimulationOnly({id: 'bench-maybe-trapped', format: 'gen9randombattle', seed: seeds[0]});
  try {
    const state = await env.resetWithOptions({view_players: ['p1', 'p2']});
    const request = state.requests.p1!;
    assert.ok(request.legal_actions.actions.some(a => a?.kind === 'switch'));
    (request.raw as any).active[0].maybeTrapped = true;
    const original = structuredClone(request);
    const [projected] = decisionInputs(state, 'p1');
    assert.equal(projected.maybe_trapped, true);
    assert.ok(!projected.legal_actions.actions.some(a => a?.kind === 'switch'));
    assert.deepEqual(projected.legal_actions.actions.filter(a => a?.kind === 'move'), request.legal_actions.actions.filter(a => a?.kind === 'move'));
    assert.deepEqual(request, original);
    request.force_switch = true;
    assert.ok(decisionInputs(state, 'p1')[0].legal_actions.actions.some(a => a?.kind === 'switch'));
  } finally {await env.close();}
});

test('bench: greedy ranks expected damage, never Terastallizes, and uses public implicit L100 details', async () => {
  const env = LocalBattleEnv.createSimulationOnly({id: 'bench-greedy', format: 'gen9randombattle', seed: seeds[0]});
  try {
    const state = await withBornTeams({
      p1: 'Magmortar\nLevel: 80\nAbility: Flame Body\n- Inferno\n- Flamethrower\n- Splash\n\nReserve (Magikarp)\n- Splash',
      p2: 'Scizor\nAbility: Swarm\n- Splash',
    }, () => env.resetWithOptions({view_players: ['p1', 'p2']}));
    const [request, view] = decisionInputs(state, 'p1');
    assert.equal(view.opponent_team[0].level, null);
    const action = await createAgent('greedy').choose(request, view, () => 0);
    assert.equal(action.choice, 'move 2'); // 90 * 100% beats Inferno's 100 * 50%.
    assert.equal(action.kind, 'move');
  } finally {await env.close();}
});

test('bench: advertised trapping seed completes without speculative rejections', {timeout: 10000}, async () => {
  const games = await runMatchup('greedy', 'random', seeds.slice(97, 98));
  assert.ok(games.every(g => g.record.rejected_choices === 0 && g.record.errors.length === 0));
});
