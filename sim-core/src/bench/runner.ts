import {performance} from 'node:perf_hooks';
import {LocalBattleEnv} from '../env_manager';
import {createSeededRandom} from '../baselines/random';
import {canonicalActionToChoice, type CanonicalAction} from '../canonical_action';
import {createAgent, type Agent, type AgentName, type BenchRequest} from './agent';
import type {BattleView, PlayerID, StepResult} from '../types';

export interface GameRecord {
  game_id: string; seed: number[]; agents: Record<PlayerID, string>; side: PlayerID;
  winner: PlayerID | 'tie' | null; turns: number; turn_limit_tie: boolean;
  illegal_choices: number; rejected_choices: number; errors: string[];
}
export interface GameResult {record: GameRecord; timing: {game_id: string; wall_time_ms: number}}

function freeze<T>(value: T): T {
  if (value && typeof value === 'object') {Object.freeze(value); for (const child of Object.values(value)) freeze(child);}
  return value;
}
export function decisionInputs(state: StepResult, owner: PlayerID): [BenchRequest, BattleView] {
  const request = state.requests[owner], view = state.views[owner];
  if (!request || request.wait || !view || view.player !== owner || request.player !== owner) throw new Error('Missing addressed decision');
  const {raw: _raw, ...addressed} = request;
  const projected: BenchRequest = structuredClone(addressed);
  // maybeTrapped advertises a speculative switch, not a guarantee of acceptance.
  // Use only this owner's signal; never inspect the foe's actual ability.
  if ((request.raw as {active?: Array<{maybeTrapped?: boolean}>})?.active?.[0]?.maybeTrapped === true && !request.force_switch) {
    projected.maybe_trapped = true;
    for (const action of projected.legal_actions.actions) if (action?.kind === 'switch') {
      projected.legal_actions.actions[action.index] = null;
      projected.legal_actions.mask[action.index] = false;
    }
    projected.legal_actions.available_indices = projected.legal_actions.available_indices.filter(i => projected.legal_actions.mask[i]);
  }
  return freeze([projected, structuredClone(view)]) as [BenchRequest, BattleView];
}

export async function playGame(seed: readonly number[], names: Record<PlayerID, string>, side: PlayerID,
  agents: Record<PlayerID, Agent>, gameId: string): Promise<GameResult> {
  const start = performance.now();
  const record: GameRecord = {game_id: gameId, seed: [...seed], agents: {...names}, side, winner: null, turns: 0,
    turn_limit_tie: false, illegal_choices: 0, rejected_choices: 0, errors: []};
  const env = LocalBattleEnv.createSimulationOnly({id: gameId, format: 'gen9randombattle', seed: [...seed], controllers: {p1: {controller: 'external'}, p2: {controller: 'external'}}});
  // Policy randomness follows each team across the side-swapped pair, independently of engine RNG.
  const policySeed = seed.reduce((hash, word) => Math.imul(hash ^ word, 16777619) >>> 0, 2166136261);
  const rng = {p1: createSeededRandom((policySeed ^ 0x12345678) >>> 0), p2: createSeededRandom((policySeed ^ 0x76543210) >>> 0)};
  const options = {view_players: ['p1', 'p2'] as PlayerID[], include_log_delta: false, include_possible_roles: false};
  try {
    let state = await env.resetWithOptions(options);
    let decisions = 0;
    while (!state.terminated) {
      record.turns = state.info.turn;
      if (state.info.turn > 1000) {record.winner = 'tie'; record.turn_limit_tie = true; break;}
      if (++decisions > 10000) throw new Error('Decision boundary limit exceeded');
      const actions: Partial<Record<PlayerID, CanonicalAction>> = {};
      for (const owner of ['p1', 'p2'] as const) {
        if (!state.requests[owner] || state.requests[owner]!.wait) continue;
        const [request, view] = decisionInputs(state, owner);
        const action = await agents[owner].choose(request, view, rng[owner]);
        try {canonicalActionToChoice(action, request);}
        catch (error) {record.illegal_choices++; throw error;}
        actions[owner] = action;
      }
      if (!Object.keys(actions).length) throw new Error('No actionable request before terminal');
      state = await env.stepWithCanonicalOptions(actions, options);
      const diagnostics = env.diagnostics().players as Record<PlayerID, {last_choice_error: unknown}>;
      record.rejected_choices = (['p1', 'p2'] as const).filter(owner => diagnostics[owner].last_choice_error !== null).length;
      if (record.rejected_choices) throw new Error('Simulator rejected an advertised legal choice');
      record.turns = state.info.turn;
      if (state.terminated) record.winner = state.winner;
    }
    if (record.turns > 1000) {record.winner = 'tie'; record.turn_limit_tie = true;}
    if (record.winner === null) throw new Error('Terminal game has no winner or tie');
  } catch (error) {
    record.errors.push(error instanceof Error ? error.message + (error.cause instanceof Error ? ': ' + error.cause.message : '') : String(error));
  }
  finally {try {await env.close();} catch (error) {record.errors.push(String(error));}}
  return {record, timing: {game_id: gameId, wall_time_ms: performance.now() - start}};
}

export class BenchRunError extends Error {
  constructor(readonly game: GameResult) {super(`Benchmark failed: ${game.record.game_id}: ${game.record.errors.join('; ')}`);}
}
export async function runMatchup(a: AgentName, b: AgentName, seeds: readonly (readonly number[])[],
  onGame?: (game: GameResult) => void, agentFactory: (name: AgentName) => Agent = createAgent): Promise<GameResult[]> {
  const games: GameResult[] = [];
  for (const [i, seed] of seeds.entries()) for (const side of ['p1', 'p2'] as const) {
    const names: Record<PlayerID, AgentName> = {p1: side === 'p1' ? a : b, p2: side === 'p2' ? a : b};
    const game = await playGame(seed, names, side, {p1: agentFactory(names.p1), p2: agentFactory(names.p2)}, `${a}-${b}-${i}-${side}`);
    games.push(game); onGame?.(game);
    if (game.record.errors.length || game.record.illegal_choices || game.record.rejected_choices) throw new BenchRunError(game);
  }
  return games;
}

export function summarize(games: readonly GameResult[]) {
  const n = games.length;
  if (!n) throw new Error('Cannot summarize zero games');
  const wins = games.filter(({record: r}) => r.winner === r.side).length;
  const ties = games.filter(({record: r}) => r.winner === 'tie').length;
  const losses = n - wins - ties;
  // A tie is a non-win; Wilson covers the Bernoulli probability of winning a game.
  const z = 1.959963984540054, p = wins / n, denominator = 1 + z * z / n;
  const center = (p + z * z / (2 * n)) / denominator;
  const radius = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator;
  const wall = games.reduce((total, game) => total + game.timing.wall_time_ms, 0);
  return {games: n, wins, losses, ties, win_rate: p, wilson_95: [Math.max(0, center - radius), Math.min(1, center + radius)],
    mean_turns: games.reduce((total, game) => total + game.record.turns, 0) / n, games_per_second: n * 1000 / wall};
}
