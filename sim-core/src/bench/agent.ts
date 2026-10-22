import {Dex} from 'pokemon-showdown';
import {RandomBaselineAgent} from '../baselines/random';
import {HeuristicBaselineAgent} from '../baselines/heuristic';
import {canonicalActionFromLegalAction, type CanonicalAction} from '../canonical_action';
import {estimateDamage, type DamagePokemon} from '../damage_calc';
import type {BattleView, ChoiceRequestView, PokemonView} from '../types';

export type BenchRequest = Omit<ChoiceRequestView, 'raw'> & {maybe_trapped?: true};
export interface Agent {
  choose(request: BenchRequest, view: BattleView, rng: () => number): CanonicalAction | Promise<CanonicalAction>;
}
export const agentNames = ['random', 'greedy', 'heuristic'] as const;
export type AgentName = typeof agentNames[number];

function damagePokemon(row: PokemonView): DamagePokemon {
  if (row.level === null && !row.details) throw new Error('Missing public Pokemon details');
  // Showdown getDetails omits L100 (sim/pokemon.ts); this is public protocol semantics.
  return {
    species: row.species, level: row.level ?? 100,
    // A neutral calculation hypothesis, never a claim that an unknown ability is absent.
    ability: row.ability_effectiveness !== 'suppressed' && row.ability_effectiveness !== 'unknown' && row.ability ? row.ability : 'No Ability',
    item: row.item && row.item !== 'has-item' ? row.item : null,
    status: row.status, hp_fraction: row.hp_ratio, stats: {...row.stats}, boosts: {...row.boosts},
    terastallized: row.terastallized, tera_type: row.tera_type,
  };
}

export function createAgent(name: AgentName): Agent {
  if (name === 'random') return {choose: (request, view, rng) => {
    const decision = new RandomBaselineAgent(rng).choose({player: request.player, request: {...request, raw: null}, view});
    return canonicalActionFromLegalAction(request, decision.action_index);
  }};
  if (name === 'heuristic') {
    const baseline = new HeuristicBaselineAgent();
    return {choose: (request, view) => {
      const decision = baseline.choose({player: request.player, request: {...request, raw: null}, view});
      return canonicalActionFromLegalAction(request, decision.action_index);
    }};
  }
  if (name !== 'greedy') throw new Error(`Unknown benchmark agent: ${name}`);
  return {choose: (request, view) => {
    const legal = request.legal_actions.actions.filter(action => action !== null);
    const moves = legal.filter(action => action.kind === 'move');
    if (!moves.length) {
      const selection = legal.find(action => action.kind === 'switch' || action.kind === 'revive');
      if (!selection) throw new Error('No non-Tera legal move or required selection');
      return canonicalActionFromLegalAction(request, selection.index);
    }
    const attacker = view.self_team[view.active.self ?? -1];
    const defender = view.opponent_team[view.active.opponent ?? -1];
    if (!attacker || !defender) throw new Error('Missing active public damage context');
    let best = moves[0], bestScore = -Infinity;
    for (const action of moves) {
      const move = Dex.moves.get(action.move!);
      const estimate = estimateDamage({attacker: damagePokemon(attacker), defender: damagePokemon(defender),
        move: action.move!, use_tera: false, field: {weather: view.field.weather, terrain: view.field.terrain,
          reflect: !!view.field.side_conditions.opponent.reflect,
          light_screen: !!view.field.side_conditions.opponent.lightscreen,
          aurora_veil: !!view.field.side_conditions.opponent.auroraveil}});
      const score = estimate.average_percent * (typeof move.accuracy === 'number' ? move.accuracy / 100 : 1);
      if (!Number.isFinite(score)) throw new Error('Non-finite damage estimate');
      if (score > bestScore) {best = action; bestScore = score;}
    }
    return canonicalActionFromLegalAction(request, best.index);
  }};
}
