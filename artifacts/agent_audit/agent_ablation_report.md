# Agent Ablation Report

All agents used paired sides on shared seeds against the heuristic baseline. Non-rollout agents received 20 battles each. Rollout variants received four battles each because measured latency was roughly 4–5 seconds per decision; their winrates are directional only.

| Agent | Battles | Wins | Losses | Draws/Timeouts | Winrate | Avg turns | Avg latency | Fallbacks | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| random | 20 | 1 | 19 | 0 | 5.0% | 26.9 | 0.0 ms | 0 | none |
| heuristic | 20 | 10 | 10 | 0 | 50.0% | 26.8 | 2.0 ms | 0 | none |
| behavior_cloning | 20 | 4 | 16 | 0 | 20.0% | 18.8 | 5.7 ms | 0 | none |
| replay_policy | 20 | 0 | 20 | 0 | 0.0% | 23.8 | 20.8 ms | 0 | none |
| action_ranker | 20 | 0 | 20 | 0 | 0.0% | 26.2 | 38.0 ms | 0 | none |
| action_value_ranker | 20 | 2 | 18 | 0 | 10.0% | 21.4 | 28.1 ms | 0 | none |
| rollout | 4 | 0 | 4 | 0 | 0.0% | 18.2 | 4145.6 ms | 4 | 69 damage fallbacks |
| ranker_rollout | 4 | 2 | 2 | 0 | 50.0% | 19.0 | 4225.1 ms | 0 | 72 damage fallbacks |
| default | 4 | 1 | 3 | 0 | 25.0% | 18.2 | 4960.9 ms | 0 | 69 damage fallbacks |

## Answers

1. **Best by measured winrate:** heuristic (50%, as expected in paired heuristic self-play). The highest learned non-rollout agent was behavior cloning at 20%. Ranker+rollout also measured 50%, but only over four battles and is not statistically comparable.
2. **Most stable:** heuristic. It completed all battles with no fallbacks and about 2 ms decision latency.
3. **Action-value versus older current-schema ranker:** action-value ranker won 10% versus action-ranker v2 at 0% in autonomous battles. Replay imitation was mixed: action-value was better on replay 2587963818, tied on 2587966474, and worse on the long replay 2587967313.
4. **Rollouts:** no reliable winrate benefit was established. They increased latency by roughly two orders of magnitude and produced frequent heuristic damage fallback in autonomous live states.
5. **Live-private value:** replay sign alignment improved on two of three checked replays and tied on one, so it is useful as a state estimator. The audit did not prove that its current coupling improves action selection.
6. **Tradeoff:** rankers cost about 28–38 ms per decision; approximate rollouts cost about 4,100–5,000 ms.
7. **Fallback dependence:** non-rollout agents had no damage fallback. Rollout agents did—69 to 72 fallback-marked decisions in four battles.
8. **Current default:** not supported as the best production default by this audit. It was slower than ranker-only and had pervasive damage fallback; its four-battle winrate was 25%.

These samples are intentionally bounded first-pass evidence, not publication-grade confidence intervals.
