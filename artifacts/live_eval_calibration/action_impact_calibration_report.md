# Action-Impact Calibration Report (Part F)

**Date:** 2026-06-18

Action-impact = how much a scorer's value changes between the current state and the
state resulting from a candidate action; branch search selects the action whose
resulting-state leaf score is best. So **current-state calibration directly drives
action selection**: if the scorer can't rank states, it can't rank actions.

## How current-state miscalibration distorts action impact

From the 1406-state calibration audit (`live_eval_calibration_report.md`):

| Property | material | live_sim_value | old_live_private |
| --- | ---: | ---: | ---: |
| Sign accuracy (state) | 0.816 | 0.936 | **0.558** |
| Saturation (\|score\|>0.9) | 0.3% | 28.5% | **73.7%** |
| Corr with outcome | 0.713 | 0.872 | **0.325** |

**Two distortion mechanisms for `old_live_private`:**

1. **Saturation crushes the delta.** With 73.7% of states pinned near ±1 (and a
   mean of +1.07), most candidate resulting states map to ≈ the same saturated
   value. The *difference* between two actions' resulting states — the impact
   signal — collapses toward zero, so action ranking is dominated by floating-point
   noise rather than tactics.
2. **Movement is noise, not signal.** A turn-to-turn discriminability proxy
   (consecutive same-side states) shows `old_live_private` actually *moves more*
   (mean |Δ|=0.244) than `material` (0.056) or `live_sim_value` (0.104) — but its
   correlation with the true outcome is only 0.33. Large, outcome-uncorrelated
   movement means its action-impact deltas point in arbitrary directions.

`material` and `live_sim_value` produce smaller deltas that *track* the outcome
(corr 0.71 / 0.87), so their action-impact rankings are meaningful.

## Measured action-selection consequence (existing branch audit, identical scorers)

The branch audit (`live_sim_value_branch_audit_report.md`, 20 paired seeded games
vs heuristic, same leaf scorers as here) is the direct end-to-end measurement of
action-impact quality:

| Leaf scorer | Branch winrate vs heuristic | Interpretation |
| --- | ---: | --- |
| material/HP | **45%** | best one-step action-impact signal |
| live_sim_value | 15% | calibrated estimator, but value-lookahead turns passive |
| old_live_private (value) | **0%** | collapsed → action-impact deltas meaningless |
| action_value_ranker | 10% | learned ranker, not a state value |
| heuristic | 50% | baseline |

The 0% for the old value head is the action-selection face of the same collapse
seen in current-state calibration: a scorer that labels every state ≈+1 cannot
prefer the action that improves the position.

## Why the best *estimator* is not the best *action selector*

`live_sim_value` is the best-calibrated current-state estimator (Brier 0.066) yet
selects worse actions than plain `material` (15% vs 45%). A value estimate hovers
near neutral mid-game, so one-step lookahead under-rewards pressing damage and plays
passively (51 vs 37 turns) — consistent with the earlier "improved state scorer"
finding. The exact post-step HP differential is a sharper one-ply impact signal even
though it is a cruder absolute estimator.

## Recommendations for action-impact work

- **Branch-leaf scoring / action-impact:** keep **material/HP** as the trusted
  scorer. It has the cleanest action-impact signal and is perspective-exact.
- **Current-state display / win-prob:** prefer the calibrated **live_sim_value**
  head (opt-in `NEURAL_EVAL_STATE_SCORER=live_sim_value`), not the collapsed default.
  These are *different jobs*: estimate vs one-step selection.
- **Do not** use `old_live_private` for either current-state display or
  action-impact. Keep it only as a labeled diagnostic.
- Live recommender defaults remain unchanged pending a live-data confirmation pass
  via the new sanitized logging.
