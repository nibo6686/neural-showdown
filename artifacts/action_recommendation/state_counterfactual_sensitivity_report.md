# State Counterfactual Sensitivity Report

**Date:** 2026-06-19  
**Fixture:** balanced synthetic 6v6, full HP, Latios active versus Hariyama. Each
row differs from neutral only in the listed active stat stages.

## Scores

| Counterfactual | Material | State scorer | live_sim_value | Old live-private | Action-value ranker |
| --- | ---: | ---: | ---: | ---: | ---: |
| neutral | 0.000 | 0.000 | -0.8101 | 0.9318 | -0.5517 |
| own SpA -2 | 0.000 | -0.060 | -0.8027 | 0.8761 | -0.5727 |
| own SpA -6 | 0.000 | -0.180 | -0.7995 | 0.7973 | -0.6439 |
| own all stats -6 | 0.000 | -0.900 | -0.6695 | 0.9536 | 0.5974 |
| Curse-like: Atk +1 / Def +1 / Spe -1 | 0.000 | 0.030 | -0.8138 | 0.9518 | -0.5221 |
| Bulk Up-like: Atk +1 / Def +1 | 0.000 | 0.060 | -0.8171 | 0.9722 | -0.4925 |
| opponent Def -2 | 0.000 | 0.060 | -0.8386 | 0.9689 | -0.6239 |
| opponent SpD -2 | 0.000 | 0.060 | -0.8386 | 0.9689 | -0.6239 |
| own Speed -6 | 0.000 | -0.180 | -0.7995 | 0.7973 | -0.6439 |

Higher is better for the audited player.

## Expected-order checks

| Check | Material | State scorer | live_sim_value | Old live-private | Ranker |
| --- | --- | --- | --- | --- | --- |
| own all -6 worse than neutral | insensitive by design | **pass** | **fail: scored much better** | fail | **fail: large inversion** |
| opponent defensive drop better than neutral | insensitive by design | **pass** | fail | pass | fail |
| own SpA -6 worse than neutral | insensitive by design | **pass** | fail | pass | pass |
| Bulk Up-like at least neutral | insensitive by design | **pass** | fail | pass | pass |
| Curse-like not reduced to “Speed drop bad” | insensitive | positive | slight negative | positive | positive |

The deterministic state scorer is correctly ordered on the clear tests. It reads
per-stat fields from the sim view, but currently sums stages with one common weight,
so it still values SpA -6 and Speed -6 identically.

`live_sim_value` is sensitive, but its controlled ordering is wrong: all stats -6
raises its score by about 0.141, and an opponent defensive drop lowers its score.
The ranker is mixed and has the strongest inversion: own all -6 raises the fixed
action score by about 1.149.

## Feature sensitivity

- Material/HP features and score do not change when HP is fixed. This is intentional.
- The 37D tactical vector is identical for neutral, SpA -6, and all stats -6.
- The full 115D live vector changes only through the public coarse boost fields:
  `p1_boost_sum_norm`, `p2_boost_sum_norm`, and
  `boost_sum_diff_p1_minus_p2`.
- Per-stat identity is absent. Own SpA -6 and own Speed -6 produce identical model
  inputs and identical outputs. Opponent Def -2 and SpD -2 are also identical.
- The public boost-difference feature flips sign when the same physical state is
  featurized from p1 and p2. The view-based material/state scorers are
  perspective-antisymmetric on the synthetic check (`-0.18` versus `+0.18`).

## Sensitivity summary

| Scorer | Sees stages? | Preserves stat identity? | Controlled behavior |
| --- | --- | --- | --- |
| Material/HP | no | no | intentionally insensitive |
| View state scorer | yes, directly from `view.boosts` | fields are available, but scorer sums them uniformly | sensitive and correctly signed on clear checks |
| live_sim_value | coarse summed stages only | **no** | sensitive but wrong-direction/mixed |
| Old live-private value | coarse summed stages only | **no** | sensitive but mixed |
| Action-value ranker state half | coarse summed stages only | **no** | sensitive but mixed; severe all-stats inversion |

## Conclusion

The problem is **both missing information and poor learned use**:

1. Per-stat identity is missing from model/ranker inputs, so the learned paths
   cannot know that SpA -2 matters differently from Speed -2.
2. Even the available coarse summed signal is used unreliably by
   `live_sim_value` and the action ranker.

No move-specific or type-specific rule is warranted. The next model revision
should add versioned own/opponent per-stat public boost features and explicit
action side-effect fields, then retrain only diagnostic candidates and require
this audit to pass before any learned branch leaf is considered for live use.
