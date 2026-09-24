import type { BaselineContext, BaselineDecision } from '../types';

export function createSeededRandom(seed: number): () => number {
  if (!Number.isSafeInteger(seed) || seed < 0 || seed > 0xffffffff) {
    throw new Error('Random controller seed must be an unsigned 32-bit integer.');
  }

  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 0x100000000;
  };
}

export class RandomBaselineAgent {
  constructor(private readonly random: () => number = () => Math.random()) {}

  choose(context: BaselineContext): BaselineDecision {
    const indices = context.request.legal_actions.available_indices;
    if (!indices.length) {
      return {
        choice: 'default',
        action_index: -1,
        score: 0,
        reason: 'no-legal-actions',
      };
    }

    const sampledIndex = indices[Math.floor(this.random() * indices.length)];
    const action = context.request.legal_actions.actions[sampledIndex];
    if (!action) {
      return {
        choice: 'default',
        action_index: -1,
        score: 0,
        reason: 'missing-action',
      };
    }

    return {
      choice: action.choice,
      action_index: sampledIndex,
      score: 0,
      reason: 'uniform-random',
    };
  }
}
