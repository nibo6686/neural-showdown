import type { BaselineContext, BaselineDecision } from '../types';

export class RandomBaselineAgent {
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

    const sampledIndex = indices[Math.floor(Math.random() * indices.length)];
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
