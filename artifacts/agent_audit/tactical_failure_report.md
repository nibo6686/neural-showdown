# Tactical Failure Report

This report uses protocol-event proxies plus the existing tactical-slice comparison tooling. Event counts are indicators, not proof that each event caused the loss.

## Loss protocol proxies

| Agent | Losses | Switches | Tera in losses | Immunity events | Resisted events | Hazard damage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| behavior_cloning | 16 | 99 | 16 | 18 | 98 | 0 |
| action_value_ranker | 18 | 202 | 14 | 18 | 95 | 3 |
| random | 19 | 304 | 19 | 17 | 87 | 3 |

## Existing tactical slices across three replay checks

- `switch_into_ko_heavy_damage`: 31 flagged decisions
- `repeated_failed_moves`: 20 flagged decisions
- `setup_into_immediate_death`: 12 flagged decisions
- `ability_punished_moves`: 4 flagged decisions

## Main failure modes

- **Switch scoring remains weak.** Offline validation accuracy is materially lower for switches than moves, and `switch_into_ko_heavy_damage` is the largest replay slice.
- **Win-condition preservation/endgame planning is weak.** Learned autonomous agents lose substantially to the heuristic despite reasonable imitation metrics.
- **Setup timing and repeated moves remain visible.** `setup_into_immediate_death` and `repeated_failed_moves` recur in replay slices.
- **Approximate opponent/state knowledge is a rollout problem.** Replay diagnostics frequently report `target_type_unknown`; live rollouts use inferred opponent policies and can score impossible or poorly calibrated branches.
- **Damage fallback contaminates rollout evaluation.** The autonomous rollout variants repeatedly used heuristic damage fallback, so rollout scores are not yet a clean test of Showdown-backed search.
- **No evidence of systemic illegal-action failures** appeared in completed audit battles.
