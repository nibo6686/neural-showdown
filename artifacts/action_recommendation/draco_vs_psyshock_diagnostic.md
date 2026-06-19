# Draco Meteor vs Psyshock — Targeted Recommender Diagnostic (Part D)

**Date:** 2026-06-18
**Fixture:** synthetic Latios (Dragon/Psychic) holding Draco Meteor + Psyshock +
Dragon Pulse + Aura Sphere + Flamethrower, with a Latias switch, facing Hariyama
(Fighting). Damage via `@smogon/calc` through sim-core (`smogon_calc`, not heuristic).
**Reproduce:** `python -m neural.action_recommender_diagnostic`
(`trainer/src/neural/action_recommender_diagnostic.py`); JSON snapshot at
`draco_vs_psyshock_diagnostic.json`.

> This is a controlled sanity check, **not** a reconstruction of the disputed live
> state. The live state may have had switch-prediction, hidden-info, item/ability,
> or positioning considerations this fixture omits. The goal is to see *which scoring
> component* could prefer a drawback move, and *why*.

## Per-action comparison

| Action | Damage method | Avg % | Type eff | Self-stat drop | Approx-rollout score (live wt 0.75) | Action-value-ranker score (live wt 0.20) |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| **Draco Meteor** | smogon_calc | 67.7 | 1.0 (neutral) | **−2 SpA** | 3.267 | **−2.426 (rank 1)** |
| **Psyshock** | smogon_calc | **83.8** | **2.0 (super-eff.)** | none | **3.611 (rank 1)** | −3.601 (rank 4) |
| Dragon Pulse | smogon_calc | 33.8 | 1.0 | none | 2.075 | −2.604 |
| Aura Sphere | smogon_calc | 28.0 | 1.0 | none | 1.566 | −3.761 |
| Flamethrower | smogon_calc | 15.7 | 1.0 | none | 1.298 | −2.500 |
| switch: Latias | n/a | — | — | — | −0.100 | −3.988 |

## What this shows

**The two learned/heuristic components disagree, and the disagreement is the bug.**

1. **Approximate rollout (live weight 0.75)** picks **Psyshock** here, because in
   this fixture Psyshock is super-effective and does *more* immediate damage
   (83.8% vs 67.7%). This scorer ranks by immediate damage. It contains **no term
   for Draco Meteor's −2 SpA self-drop** — it lands on the better move only because
   the better move also happens to hit harder this turn. In any state where the
   drawback move's raw damage estimate edges the alternative (different attacker,
   higher-Def or Psychic-resistant target, item/ability, a non-super-effective
   Psyshock), this same scorer would prefer the drawback move.

2. **Action-value ranker (live weight 0.20)** picks **Draco Meteor** and pushes
   **Psyshock down to rank 4**. This is the component that reproduces the user's
   disputed preference. The ranker scores from `build_action_feature_vector`, whose
   schema (`legal-action-v3`, 165D) encodes move type, category, **base power**,
   accuracy, priority, PP, and the flags `status/setup/recovery/pivot/hazard/
   protect` — but has **no feature for a self-stat drop, recoil, recharge, or
   lock-in**. Draco Meteor (base power 130) outscores Psyshock (base power 80) on
   the base-power feature, and nothing in the schema lets the model learn that
   Draco halves its own Special Attack. The ranker cannot represent the drawback,
   so it prefers the bigger nominal move.

3. **No scorer used by the live recommender evaluates the *future* position.** A
   Stockfish-style evaluator would notice that after Draco Meteor the attacker's
   Special Attack is at −2, so its *next* attack is roughly halved — a worse future
   position than after Psyshock. The live recommender has no such lookahead: the
   approximate rollout adds noise to a current-state proxy, and the ranker is a
   one-shot action score. The seeded one-turn/two-ply/belief branch tools *do*
   evaluate resulting states (and a 2-ply material search would see the halved
   follow-up damage), but they are not wired into live recommendation.

## Diagnosis

The disputed Draco-over-Psyshock preference is **not** an immediate-damage bug in
isolation and **not** a type-chart gap. It is the combination of:

- **side-effect blindness** — neither the action-feature schema (ranker) nor the
  approximate scorer represents self-stat drops / recoil / recharge / lock-in; and
- **no future-state evaluation** — the live recommender never scores the position
  that *results* from an action, which is where a drawback shows up.

The side-effect annotations added in `action_side_effects.py` (Part F) correctly
flag `Draco Meteor → {spa: -2}` and `has_drawback: true`; they are surfaced in the
action trace (Part B) as a diagnostic but, per the task constraints, are **not**
wired into action selection. `spa_drop_represented_in_score = false` in the JSON
snapshot records that the drawback is invisible to every component that currently
ranks actions.
