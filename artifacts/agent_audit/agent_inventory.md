# Agent Inventory

Audit date: 2026-06-18

## Runtime and validated scope

- CPU: Intel Core i7-9700, 8 physical cores / 8 logical processors.
- GPU: NVIDIA GeForce RTX 2060 SUPER; PyTorch CUDA is available.
- Pokemon Showdown battle mechanics are CPU-bound JavaScript. CUDA accelerates model inference only.
- Seeded Gen 9 singles is the validated simulator scope.
- Strict live-eval healthcheck: PASS.
- Default value checkpoint: `gen9randombattle_live_private_value_v2.pt`.
- Default action checkpoint: `gen9randombattle_action_value_ranker_v2.pt`.

## Checkpoints

| Checkpoint | Size | Modified | Type | Feature version | Input | State | Action |
| --- | ---: | --- | --- | --- | ---: | ---: | ---: |
| `gen9randombattle_bc.pt` | 4,423,398 | 2026-04-25T16:31:19 | policy/value MLP | legacy/local | 1163 | - | 13 |
| `gen9randombattle_replay_policy.pt` | 93,524 | 2026-04-26T14:12:42 | policy/value MLP | legacy/local | 31 | - | 13 |
| `gen9randombattle_replay_value.pt` | 914,204 | 2026-04-26T17:53:04 | policy/value MLP | legacy/local | 31 | - | 13 |
| `gen9randombattle_live_private_value_v2.pt` | 1,172,586 | 2026-04-28T15:02:29 | live-private-belief-value | live-private-belief-v2 | 115 | - | 13 |
| `gen9randombattle_action_ranker.pt` | 829,522 | 2026-04-26T23:46:02 | action-ranker | legacy/local | 134 | 78 | 56 |
| `gen9randombattle_action_ranker_v2.pt` | 1,272,486 | 2026-04-28T15:47:29 | action-ranker | legacy/local | 280 | 115 | 165 |
| `gen9randombattle_action_value_ranker_v2.pt` | 1,273,934 | 2026-04-28T17:35:48 | action-value-ranker | live-private-belief-v2 | 280 | 115 | 165 |
| `gen9randombattle_value.pt` | 4,440,522 | 2026-04-26T11:57:54 | policy/value MLP | legacy/local | 1179 | - | 13 |

## Compatibility

- Current live-private dimension: 115.
- Current action feature dimension: 165; current ranker input: 280.
- `action_ranker_v2` and `action_value_ranker_v2` match current dimensions.
- Legacy `gen9randombattle_action_ranker.pt` is stale (`78 + 56 = 134`) and is not a valid current live default.
- Behavior-cloning checkpoints use the current local simulator feature dimension, 1163.

## Supported recommendation methods

- random and heuristic sim-core baselines
- behavior-cloning fixed 13-action policy
- replay-policy prior
- current action ranker and action-value ranker
- approximate rollout-only and ranker-plus-rollout scoring
- current default: live-private value + action-value ranker + replay policy + approximate rollout

A live-private value model by itself is not a complete action-selection agent: it scores the current state, while most move actions do not have exact successor states. It was therefore audited as a component through replay value comparisons, not misrepresented as a standalone policy.
