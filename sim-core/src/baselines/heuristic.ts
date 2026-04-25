import fs from 'node:fs';
import path from 'node:path';
import { Generations, Move as CalcMove, Pokemon as CalcPokemon, calculate } from '@smogon/calc';
import { Dex, toID } from 'pokemon-showdown';
import { moveTypeMultiplier, parseCondition, resolveTypes, upsertUnique } from '../battle_helpers';
import type { BaselineContext, BaselineDecision, LegalAction, PokemonView } from '../types';

interface RandomBattleRole {
  role: string;
  movepool: string[];
  abilities: string[];
  teraTypes: string[];
}

interface RandomBattleSpeciesData {
  level: number;
  sets: RandomBattleRole[];
}

type RandomBattleData = Record<string, RandomBattleSpeciesData>;

const gen = Generations.get(9);

function averageDamage(result: number | number[]): number {
  if (typeof result === 'number') {
    return result;
  }
  if (!Array.isArray(result) || !result.length) {
    return 0;
  }
  return result.reduce((sum, value) => sum + value, 0) / result.length;
}

function normalizedMovePower(moveName: string, hpRatio: number | null): number {
  const move = Dex.moves.get(moveName);
  if (!move.exists) {
    return 0;
  }

  if (move.id === 'eruption' || move.id === 'waterspout') {
    return move.basePower * Math.max(0.1, hpRatio ?? 1);
  }

  return move.basePower || 0;
}

function normalizeStatScore(value: number | undefined): number {
  return value ? value / 100 : 1;
}

function chooseBest<T>(items: T[], scorer: (item: T) => number): { item: T; score: number } | null {
  let best: { item: T; score: number } | null = null;
  for (const item of items) {
    const score = scorer(item);
    if (!best || score > best.score) {
      best = { item, score };
    }
  }
  return best;
}

class RandomBattlePriors {
  private readonly data: RandomBattleData;

  constructor() {
    const packageRoot = path.dirname(require.resolve('pokemon-showdown/package.json'));
    const dataPath = path.join(packageRoot, 'data', 'random-battles', 'gen9', 'sets.json');
    this.data = JSON.parse(fs.readFileSync(dataPath, 'utf8')) as RandomBattleData;
  }

  getHypotheses(pokemon: PokemonView): RandomBattleRole[] {
    const entry = this.data[toID(pokemon.species)];
    if (!entry?.sets?.length) {
      return [];
    }

    return entry.sets.filter((set) => {
      const abilityOk = !pokemon.ability || set.abilities.some((ability) => toID(ability) === toID(pokemon.ability));
      const movesOk = pokemon.revealed_moves.every((move) => set.movepool.some((candidate) => toID(candidate) === toID(move)));
      return abilityOk && movesOk;
    });
  }

  getLevel(species: string): number {
    return this.data[toID(species)]?.level || 80;
  }
}

export class HeuristicBaselineAgent {
  private readonly priors: RandomBattlePriors;

  constructor() {
    this.priors = new RandomBattlePriors();
  }

  choose(context: BaselineContext): BaselineDecision {
    const actions = context.request.legal_actions.actions.filter((action): action is LegalAction => !!action);
    if (!actions.length) {
      return {
        choice: 'default',
        action_index: -1,
        score: 0,
        reason: 'no-legal-actions',
      };
    }

    const selfActive = context.view.self_team[context.view.active.self ?? -1];
    const opponentActive = context.view.opponent_team[context.view.active.opponent ?? -1];

    if (!selfActive || !opponentActive) {
      const fallback = actions[0];
      return {
        choice: fallback.choice,
        action_index: fallback.index,
        score: 0,
        reason: 'missing-active-state',
      };
    }

    const moveActions = actions.filter((action) => action.kind === 'move' || action.kind === 'move_tera');
    const switchActions = actions.filter((action) => action.kind === 'switch');

    const bestMove = chooseBest(moveActions, (action) => this.scoreMoveAction(action, selfActive, opponentActive, context.view.field.side_conditions.opponent));
    const bestSwitch = chooseBest(switchActions, (action) => this.scoreSwitchAction(action, context.view, opponentActive));

    const stayScore = bestMove?.score ?? -Infinity;
    const switchScore = bestSwitch?.score ?? -Infinity;
    const currentDefensiveScore = this.scoreDefensiveProfile(selfActive, opponentActive);

    if (
      bestSwitch &&
      (stayScore < 55 || currentDefensiveScore < -40 || (selfActive.hp_ratio ?? 1) < 0.35) &&
      switchScore > stayScore + 10
    ) {
      return {
        choice: bestSwitch.item.choice,
        action_index: bestSwitch.item.index,
        score: bestSwitch.score,
        reason: 'defensive-pivot',
      };
    }

    if (bestMove) {
      return {
        choice: bestMove.item.choice,
        action_index: bestMove.item.index,
        score: bestMove.score,
        reason: 'best-move',
      };
    }

    if (bestSwitch) {
      return {
        choice: bestSwitch.item.choice,
        action_index: bestSwitch.item.index,
        score: bestSwitch.score,
        reason: 'fallback-switch',
      };
    }

    const fallback = actions[0];
    return {
      choice: fallback.choice,
      action_index: fallback.index,
      score: 0,
      reason: 'fallback-first-legal',
    };
  }

  private scoreMoveAction(
    action: LegalAction,
    attacker: PokemonView,
    defender: PokemonView,
    opponentSideConditions: Record<string, number>,
  ): number {
    const move = Dex.moves.get(action.move || '');
    if (!move.exists) {
      return -1;
    }

    if (move.category === 'Status') {
      return this.scoreStatusMove(move.name, attacker, defender, opponentSideConditions);
    }

    const moveType = move.type;
    const attackerTypes = action.kind === 'move_tera' && attacker.tera_type
      ? [attacker.tera_type]
      : resolveTypes(attacker.species, attacker.tera_type, attacker.terastallized);
    const defenderTypes = defender.types.length
      ? defender.types
      : resolveTypes(defender.species, defender.tera_type, defender.terastallized);

    const typeMultiplier = moveTypeMultiplier(moveType, defenderTypes);
    if (typeMultiplier === 0) {
      return -100;
    }

    const stab = attackerTypes.includes(moveType) ? (action.kind === 'move_tera' ? 2 : 1.5) : 1;
    const accuracy = typeof move.accuracy === 'number' ? move.accuracy / 100 : 1;
    const power = normalizedMovePower(move.name, attacker.hp_ratio);
    const offensiveStat = move.category === 'Physical'
      ? normalizeStatScore(attacker.stats.atk)
      : normalizeStatScore(attacker.stats.spa);
    const defensiveStat = move.category === 'Physical'
      ? normalizeStatScore(defender.stats.def)
      : normalizeStatScore(defender.stats.spd);

    const baseScore = power * accuracy * stab * typeMultiplier * (offensiveStat / Math.max(0.6, defensiveStat));
    const damageShare = this.estimateDamageShare(attacker, defender, move.name, action.kind === 'move_tera');
    const koBonus = defender.hp_ratio !== null && damageShare >= defender.hp_ratio ? 80 : 0;
    const chipBonus = defender.hp_ratio !== null ? (damageShare / Math.max(0.1, defender.hp_ratio)) * 20 : 0;
    const priorityBonus = (move.priority || 0) > 0 && (defender.hp_ratio ?? 1) < 0.35 ? 18 : 0;

    return baseScore + koBonus + chipBonus + priorityBonus;
  }

  private scoreStatusMove(
    moveName: string,
    attacker: PokemonView,
    defender: PokemonView,
    opponentSideConditions: Record<string, number>,
  ): number {
    const moveId = toID(moveName);
    const hpRatio = attacker.hp_ratio ?? 1;

    if (['recover', 'roost', 'slackoff', 'softboiled', 'moonlight', 'morningsun', 'strengthsap', 'synthesis'].includes(moveId)) {
      return hpRatio < 0.5 ? 85 : 25;
    }

    if (['stealthrock', 'spikes', 'toxicspikes', 'stickyweb'].includes(moveId)) {
      return opponentSideConditions[moveId] ? 10 : 70;
    }

    if (['swordsdance', 'dragondance', 'nastyplot', 'calmmind', 'bulkup', 'quiverdance', 'agility', 'rockpolish', 'curse'].includes(moveId)) {
      return hpRatio > 0.65 ? 75 : 35;
    }

    if (['toxic', 'willowisp', 'thunderwave', 'spore', 'sleeppowder', 'glare'].includes(moveId)) {
      return defender.status ? 20 : 72;
    }

    if (['uturn', 'voltswitch', 'flipturn', 'partingshot', 'teleport', 'chillyreception'].includes(moveId)) {
      return 68;
    }

    if (moveId === 'protect') {
      return hpRatio < 0.25 ? 52 : 28;
    }

    return 24;
  }

  private scoreSwitchAction(action: LegalAction, view: BaselineContext['view'], opponentActive: PokemonView): number {
    const candidate = view.self_team.find((pokemon) => pokemon.slot === action.slot);
    if (!candidate) {
      return -Infinity;
    }

    const defensive = this.scoreDefensiveProfile(candidate, opponentActive);
    const offensive = this.scoreOffensiveProfile(candidate, opponentActive);
    const hpBonus = (candidate.hp_ratio ?? 1) * 35;
    const statusPenalty = candidate.status ? 15 : 0;

    return defensive + offensive * 0.4 + hpBonus - statusPenalty - 20;
  }

  private scoreDefensiveProfile(candidate: PokemonView, opponentActive: PokemonView): number {
    const candidateTypes = candidate.types.length
      ? candidate.types
      : resolveTypes(candidate.species, candidate.tera_type, candidate.terastallized);

    const opponentAttackTypes = new Set<string>();
    for (const moveName of opponentActive.revealed_moves) {
      const move = Dex.moves.get(moveName);
      if (move.exists && move.category !== 'Status') {
        opponentAttackTypes.add(move.type);
      }
    }

    if (!opponentAttackTypes.size) {
      for (const typeName of opponentActive.types) {
        opponentAttackTypes.add(typeName);
      }
    }

    for (const set of this.priors.getHypotheses(opponentActive)) {
      for (const moveName of set.movepool) {
        const move = Dex.moves.get(moveName);
        if (move.exists && move.category !== 'Status') {
          opponentAttackTypes.add(move.type);
        }
      }
    }

    let score = 0;
    for (const moveType of opponentAttackTypes) {
      const multiplier = moveTypeMultiplier(moveType, candidateTypes);
      if (multiplier === 0) {
        score += 90;
      } else if (multiplier < 1) {
        score += 45 / multiplier;
      } else if (multiplier > 1) {
        score -= 55 * multiplier;
      }
    }

    return score;
  }

  private scoreOffensiveProfile(candidate: PokemonView, opponentActive: PokemonView): number {
    const damagingMoves = candidate.revealed_moves.length ? candidate.revealed_moves : candidate.moves;
    if (!damagingMoves.length) {
      return 0;
    }

    const opponentTypes = opponentActive.types.length
      ? opponentActive.types
      : resolveTypes(opponentActive.species, opponentActive.tera_type, opponentActive.terastallized);

    let best = 0;
    for (const moveName of damagingMoves) {
      const move = Dex.moves.get(moveName);
      if (!move.exists || move.category === 'Status') {
        continue;
      }
      const attackerTypes = candidate.types.length
        ? candidate.types
        : resolveTypes(candidate.species, candidate.tera_type, candidate.terastallized);
      const stab = attackerTypes.includes(move.type) ? 1.5 : 1;
      const power = normalizedMovePower(move.name, candidate.hp_ratio);
      const multiplier = moveTypeMultiplier(move.type, opponentTypes);
      best = Math.max(best, power * stab * multiplier);
    }
    return best / 6;
  }

  private estimateDamageShare(attacker: PokemonView, defender: PokemonView, moveName: string, usingTera: boolean): number {
    try {
      const attackerPokemon = this.buildCalcPokemon(attacker, usingTera);
      const defenderPokemon = this.buildCalcPokemon(defender, false);
      const result = calculate(gen, attackerPokemon, defenderPokemon, new CalcMove(gen, moveName));
      const damage = averageDamage(result.damage as number | number[]);
      const defenderHp = (defenderPokemon as any).rawStats?.hp || 100;
      return Math.max(0, Math.min(1.5, damage / Math.max(1, defenderHp)));
    } catch {
      return 0;
    }
  }

  private buildCalcPokemon(pokemon: PokemonView, usingTera: boolean): InstanceType<typeof CalcPokemon> {
    const hpInfo = parseCondition(pokemon.hp_text || '');
    const teraType = usingTera ? pokemon.tera_type : pokemon.terastallized ? pokemon.tera_type : undefined;
    const stats = pokemon.stats;
    const hypotheses = this.priors.getHypotheses(pokemon);
    const possibleAbility = pokemon.ability
      || hypotheses.flatMap((set) => set.abilities)[0]
      || undefined;
    const possibleTeraTypes = hypotheses.flatMap((set) => set.teraTypes).filter(Boolean);

    const calcPokemon = new CalcPokemon(gen, pokemon.species, {
      level: pokemon.level || this.priors.getLevel(pokemon.species),
      ability: possibleAbility,
      item: pokemon.item || undefined,
      teraType: (teraType || possibleTeraTypes[0]) as any,
      moves: pokemon.revealed_moves.length ? [...pokemon.revealed_moves] : [...pokemon.moves],
      boosts: { ...(pokemon.boosts || {}) },
      status: (pokemon.status || undefined) as any,
      curHP: hpInfo.hpRatio !== null ? Math.max(1, Math.round(((stats.hp || 100) || 100) * hpInfo.hpRatio)) : undefined,
    });

    return calcPokemon;
  }

  getPossibleRoles(pokemon: PokemonView): string[] {
    const roles = this.priors.getHypotheses(pokemon).map((set) => set.role);
    return roles.reduce<string[]>((all, role) => upsertUnique(all, role), []);
  }
}
