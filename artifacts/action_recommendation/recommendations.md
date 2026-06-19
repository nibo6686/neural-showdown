# Action Recommendation — Recommendations

**Date:** 2026-06-19  
**Evidence:** feature inventory, controlled counterfactual scores, real
Draco/Flamethrower simulator transition, prior calibration and branch audits.

## vNext Slice 1 status

Diagnostic-only `live-private-belief-v3` now preserves seven per-stat stages and
separate base/current typing with provenance. SpA -6 and Speed -6 are distinct,
and public Soak/type-change state is represented. Existing live/value/ranker
checkpoints remain on v2; no live default changed.

Diagnostic-only `live-private-belief-v4` now adds current/last item identity,
unknown/none/removed/consumed/suppressed item state, and base/current/
changed/suppressed ability state. It is not used by live models.

## vNext Slice 5 status

Diagnostic-only `live-private-belief-v7` (3208D) and `legal-action-v4` (269D)
now represent move identity, exact own PP, disabled/recharge/two-turn/Encore/
inferred-Choice lock constraints, and — on the action side — signed self/target
per-stat deltas, recoil, drain, recharge, lock-in, pivot and classification.
**Draco Meteor's self Special-Attack drop is now an explicit action field**
(`self_stat_delta_spa = −1.0` vs Psyshock `0.0`); Curse and Bulk Up differ in
`self_stat_delta_spe` while sharing Atk/Def. See
`draco_action_feature_vnext_report.md`. No live default, dataset or checkpoint
changed; no v7 / legal-action-v4 model exists.

## vNext Slice 6 status

Diagnostic-only `legal-action-v5` (318D) preserves the exact 269D v4 prefix and
adds resolved expected/min/max damage, KO chance, hit chance,
effectiveness/immunity, STAB and exact/approximate/unavailable provenance.
Non-damaging moves are known-zero; switches and missing damaging estimates are
explicitly distinguished. Current typing/Tera, stat stages and supported field
state affect the diagnostic estimate. No live default, dataset or checkpoint
changed.

## Answers

- **Does the model/scorer receive stat-stage information?** Material/HP does not,
  by design. The deterministic view state scorer reads `view.boosts`. Learned
  live/value/ranker paths receive only a coarse summed public boost signal.
- **Is per-stat identity preserved?** **No** in the 115D learned feature vector.
  SpA -6 and Speed -6 are identical inputs; opponent Def -2 and SpD -2 are
  identical inputs. Exact fields are tracked in tactical state and sim views but
  dropped before model inference.
- **Does live_sim_value react correctly?** Not reliably. It penalized the coarse
  drop in the real Draco post-state by `-0.0127`, but in the balanced audit it
  scored own all-stats -6 substantially *better* and opponent defensive drops
  *worse*. Sensitivity exists; controlled ordering fails.
- **Does material ignore stages?** Yes, intentionally, whenever HP is unchanged.
- **Did Draco's real post-state include SpA -2?** Yes. A sim-core ident-merging
  defect initially hid it on a duplicate inactive entry; that defect is now fixed
  and regression-tested.
- **Did any scorer understand the post-state as worse?** Holding all post-action HP
  fixed, the view state scorer applied `-0.0600` and `live_sim_value` applied
  `-0.0127`; material applied zero. The learned response is not trustworthy across
  the broader counterfactual suite.
- **Is this missing information, poor learned use, or both?** **Both.** Per-stat
  identity and action side effects are missing, while the available coarse signal
  is learned inconsistently.
- **Should ranker features include side effects/per-stat boosts?** Yes, in a new
  versioned schema: self/target per-stat stage changes, recoil, recharge, lock-in,
  and other general move consequences. These are features, not move bans.
- **Should live/sim value features include per-stat public boosts?** Yes: own and
  opponent active `atk/def/spa/spd/spe` stages, perspective-normalized.
- **Should side-effect annotations remain diagnostic only?** Yes until the new
  schema is trained and passes sensitivity/action-impact gates. Do not hand-add a
  Draco penalty to live scoring.
- **Should branch leaves use a learned value model now?** No. A learned leaf should
  be eligible only after it passes this counterfactual ordering audit and the
  existing paired branch audit.

## Recommended next task

Create a versioned feature revision for diagnostic training:

1. ~~Add perspective-normalized own/opponent per-stat active boost fields and
   current typing.~~ Implemented in diagnostic v3 Slice 1.
2. ~~Add general side-effect fields to action features (self/target stat changes,
   recoil, recharge, lock-in), without move-specific rules.~~ Implemented in
   diagnostic `legal-action-v4` Slice 5.
3. ~~Add resolved action damage/range, KO, accuracy, effectiveness and
   provenance.~~ Implemented in diagnostic `legal-action-v5` Slice 6.
4. Run a final representation-freeze audit and replay-pool profiling design.
5. Build a small diagnostic dataset, then run small/medium non-production
   training benchmarks before any full replay rebuild.
6. Re-run this exact counterfactual suite, requiring clear-order checks and
   per-stat distinction to pass.
7. Only then compare the candidate as a branch leaf in paired seeded games.

Do not change live defaults, overwrite production checkpoints, or add type-chart
or move-name hardcoding during this task.
