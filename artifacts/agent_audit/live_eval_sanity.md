# Live/Replay Evaluation Sanity

| Replay | Actions | Avg value delta | Better sign alignment | V2 ranker top-1 | Action-value top-1 |
| --- | ---: | ---: | --- | ---: | ---: |
| 2587963818 | 34 | 0.384 | new | 81.8% | 84.8% |
| 2587966474 | 35 | 0.186 | tie | 68.6% | 68.6% |
| 2587967313 | 128 | 0.274 | new | 67.5% | 41.7% |

## Damage checks

- Exact-stat validation used attacker stats: `True`.
- Exact-stat validation used defender stats: `True`.
- Exact-stat damage method: `smogon_calc`.
- Standalone turn-10 rollout diagnostics for all three replays returned `smogon_calc` for damaging actions and no heuristic fallback.
- Autonomous live rollout battles did show frequent heuristic fallback. This difference indicates that some live battle snapshots lack enough clean species/state data for the strict calc path even though curated replay states succeed.

## Interpretation

- Live-private value sign alignment was better on two replay checks and tied on one.
- Action-value ranker improvements are not uniform: it beat v2 on one replay, tied on one, and regressed on the long replay.
- Exact-stat support works when private stats are supplied.
- The no-fallback requirement is satisfied for curated replay diagnostics but not for continuous autonomous rollout use.
