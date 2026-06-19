# State Counterfactual Feature Inventory (Part A)

**Date:** 2026-06-19
**Question:** before changing any scoring, do the scorers/models actually *see* the
public state variables (especially stat stages) that should make a drawback move
worse? Inspected: `live_private_features.py` (the `live-private-belief-v2` builder,
115D), `tactical_state.py`, `build_replay_value_dataset.py` (31D public block),
`one_turn_branch.py` (material/state scorers), `action_features.py` (ranker action
schema). All claims below are confirmed empirically (probes re-run, not inferred).

## Feature vector composition (`live-private-belief-v2`, 115D)

`public(31) + private(33) + opponent_belief(14) + tactical(37)`. The value model,
the `live_sim_value` head, the old `live_private_value` head, and the action-value
ranker's *state* half all consume this vector.

## Headline finding

**Stat stages are tracked but almost entirely dropped before any model sees them.**

- `tactical_state.py` *tracks* exact per-stat boosts (`_handle_boost`, snapshot
  `own.boosts` / `opponent.boosts`), but `tactical_state_feature_vector` (the 37D
  block) encodes **zero** boost features. Probe: neutral vs own `spa:-6` vs
  own all-stats `-6` → **byte-identical 37D vectors** (max abs diff 0.0).
- The only stat-stage signal that reaches a model is in the **public 31D block**:
  `p1_boost_sum_norm`, `p2_boost_sum_norm`, `boost_sum_diff_p1_minus_p2` — a single
  **signed sum over all stats** per side (`Σ stages / 36`, clipped to [-1, 1]).
- End-to-end probe through `build_features_from_live_payload` (full 115D):
  - own SpA `-2` → only `p1_boost_sum_norm` and `boost_sum_diff` change (−0.0556).
  - own Atk `+2` → the **same two features** change (+0.0556).
  - opp Def `-2` → `p2_boost_sum_norm` (−0.0556) and `boost_sum_diff` (+0.0556).

So the model receives a coarse, **stat-agnostic, summed** boost magnitude. It
**cannot distinguish which stat changed**: a special attacker's SpA−2 and its
Spe−2 are the identical input. Per-stat identity — exactly what makes Draco
Meteor's SpA drop matter for a special attacker — is **not present** in any feature.

## Answers

| Question | Answer |
| --- | --- |
| Active **own** stat stages in features? | **Partial.** Only as one signed sum-over-stats (`p1_boost_sum_norm`, `boost_sum_diff`). No per-stat values. Per-stat tactical boosts are tracked then discarded. |
| Active **opponent** stat stages? | **Partial**, same coarse summed form (`p2_boost_sum_norm`, `boost_sum_diff`). |
| **Bench** stat stages? | **No.** Boosts reset on switch; only the active total is summed. |
| **Status** conditions? | **Yes (coarse).** Public `p1/p2_status_fraction` + diff (fraction of team statused); private per-mon `status`; tactical `active_status`. No per-status-type feature in the value vector. |
| **Hazards**? | **Yes (well covered).** Tactical block: stealthrock, spikes layers, toxicspikes layers, stickyweb, screen counts, own/opp hazard-layer norms (12 features). |
| **Volatiles**? | **Partial.** Tactical features: leechseed, substitute, taunt, encore + own/opp volatile counts. `TRACKED_VOLATILES` also records confusion/torment/perishsong/lock-moves but those get **no dedicated feature**. |
| Choice-lock / recharge / confusion / substitute represented? | **substitute: yes** (feature). **confusion / recharge / choice-lock: no** dedicated feature (recharge/lock not even tracked as volatiles). |
| Action-value **ranker action** schema includes move side effects? | **No.** `legal-action-v3` (165D) has base power / type / category / accuracy / flags (status/setup/recovery/pivot/hazard/protect) but **no self-stat-drop / recoil / recharge / lock-in** feature (confirmed last session, `action_side_effects.py` exists only as a diagnostic). |
| Does **material/HP** scorer ignore stat stages by design? | **Yes.** `make_material_score_fn` reads only HP fractions. In the balanced full-HP probe, neutral / SpA−2 / SpA−6 / all−6 all score **0.0** (identical). Intentional. |
| Does **live_sim_value** receive stat-stage features? | **Only the coarse summed boost** (2–3 of 115 features move for any single-stat change). No per-stat signal. |
| Does the **state scorer** (opt-in branch leaf) see stat stages? | **Yes, per-stat.** `make_state_score_fn` reads `view.boosts` directly from the sim-core post-step view (not the feature vector). Probe: neutral 0.2167, own SpA−2 0.1567, own SpA−6 0.0367, own all−6 −0.6833, opp Def−2 0.2767 — correctly ordered (weight `boost`=0.03/stage). |
| Does sim-core expose boosts at all? | **Yes.** `view.self_team[i].boosts` / `opponent_team[i].boosts` exist on every mon (empty until a boost event). A real seed-1 Draco transition now exposes `spa:-2` on the active user. The audit also found and fixed an ident merge bug (`p1: Name` vs `p1a: Name`) that had placed the boost on a duplicate inactive entry. |
| Does `/evaluate` expose enough debug to confirm this? | **Yes.** `debug.tactical_snapshot.own.boosts` carries the raw per-stat boosts, and `debug.feature_values_preview` / the new `debug.action_trace` show the scored inputs. The mismatch (boosts in snapshot, absent from features) is directly observable. |

## Interpretation

The disputed Draco>Psyshock decision is, at the value/model level, a **missing-
information** problem, not (only) a poor-learning problem:

- The **simulator** records Draco Meteor's −2 SpA in the post-step view.
- The **material scorer** ignores it by design (HP only).
- The **state scorer** would see it (per-stat, from the view) but is opt-in and not
  used by the live recommender.
- The **value / live_sim_value / action-value-ranker** path sees at most a coarse
  *summed* boost magnitude with no per-stat identity — so even a well-trained model
  on this feature set could not learn that SpA−2 specifically hurts a special
  attacker. The information needed for that judgement is absent from the features.

This is testable with controlled counterfactuals (Part B–D) rather than move rules.
