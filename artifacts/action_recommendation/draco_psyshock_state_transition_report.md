# Draco Meteor State-Transition Sensitivity

**Date:** 2026-06-19  
**Seed:** `make_battle_seed(1)`, turn 0  
**Fixture:** Alolan Exeggutor versus Hydrapple  
**Comparison:** Draco Meteor versus Flamethrower. Psyshock was not available on
this seeded user's moveset, so Flamethrower is the clean no-drawback special-move
analog.

## Simulator transition

| Action | Opponent HP lost | User HP after | Post boosts | Material delta | State delta | live_sim_value delta |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Draco Meteor | 86% | 92.0% | **SpA -2** | +0.1301 | +0.2652 | +0.1664 |
| Flamethrower | 16% | 92.0% | none | +0.0134 | +0.0335 | +0.0229 |

The raw post-Draco state is better than the pre-state because 86% immediate damage
dominates the drawback. That does not answer whether a scorer understood the
drop, so the diagnostic also scored the exact same simulator-derived post-state
with only the active boost map cleared:

| Scorer | Draco post-state | Same HP/state, no SpA drop | Isolated SpA -2 effect |
| --- | ---: | ---: | ---: |
| Material/HP | 0.1301 | 0.1301 | **0.0000** |
| View state scorer | 0.2652 | 0.3252 | **-0.0600** |
| live_sim_value | 0.0852 | 0.0978 | **-0.0127** |

Thus:

- sim-core really does apply and expose Draco Meteor's **SpA -2**;
- material ignores it, as designed;
- the view state scorer penalizes it directly;
- `live_sim_value` penalizes the available coarse boost signal in this particular
  post-state, but the balanced counterfactual audit shows that its response is not
  reliable or correctly ordered in general;
- neither learned scorer can know that the changed stat is specifically Special
  Attack, because the live feature vector preserves only the summed stage signal.

## Extractor defect found and fixed

The first transition run exposed a sim-core view bug: request team idents use
`p1: Name`, while battle events use `p1a: Name`. The extractor treated these as
different Pokémon, put `spa: -2` on a duplicate inactive entry, and caused material
scoring to count a phantom seventh team member. `state_extractor.ts` now merges
idents by parsed player/name, with a regression test. After the fix the active
Alolan Exeggutor correctly carries `{"spa": -2}` and the team remains size six.

## Recommender rank limitation

This transition audit evaluates resulting states, not the synthetic live payload
used by the earlier Draco-versus-Psyshock recommender diagnostic. A directly
comparable current blended recommender rank was therefore not recorded here.
The earlier controlled action diagnostic remains the ranker evidence: its
action-value ranker preferred Draco Meteor because the action schema lacks
self-stat-drop fields.

## Interpretation

This does not establish that Draco Meteor is a bad action. It establishes that the
future state contains the drawback and that only some scorers respond to it. The
learned path has both an information bottleneck (no per-stat identity) and a
calibration/use problem (wrong ordering on controlled balanced states).
