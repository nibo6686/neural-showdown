# Agent Audit Recommendations

## 1. Keep approximate rollouts disabled in live defaults

Damage plumbing is clean and latency is now acceptable, but the rollout value
itself is still an approximate scoring proxy rather than an exact Showdown
transition. The final 20-battle smoke scored 4-16 against heuristic. Do not
change live weights or defaults yet.

## 2. Do not retrain the action-value ranker solely for this fix

The current action-value dataset is not damage- or rollout-derived. Its targets
come from live-private value deltas and final results, so the exact-stat damage
repair does not invalidate it. Keep the dataset and checkpoint.

Retrain later only after a new, explicitly versioned target improves switch and
endgame supervision or after trustworthy simulator-transition rollout labels
exist.

## 3. Keep the current live recommender default unchanged

The action-value ranker remains the best provisional learned-model component,
but it has not beaten the heuristic baseline. Clean rollout damage removes one
correctness blocker; it does not establish that rollout-weighted action
selection is stronger.

## 4. Next task: replace approximate score sampling with real one-turn branches

Use the current live sim-core environment state to clone or branch each legal
action against a bounded opponent-action set, then evaluate the resulting
state. Preserve the clean damage counters and require:

- zero heuristic damage fallbacks;
- zero rollout timeouts in a 20-battle smoke;
- deterministic results under fixed seeds;
- materially better paired performance than the current 20% rollout result;
- no public/private information leakage.

Only after that gate should rollout-derived labels or production rollout
weights be considered.

## Performance configuration

Continue using six process workers on the current 8-core machine. Each worker
owns one sim-core process and reuses it for damage RPCs. PyTorch inference uses
the RTX 2060 SUPER; Showdown mechanics remain CPU-bound.

Validation command:

```powershell
.\scripts\run_windows.ps1 -Action agent-audit -SimCoreMode native
```

## 5. Value-model autopsy outcome (2026-06-18)

See `value_model_inventory.md`, `value_model_diagnostics.md`,
`state_scorer_design.md`, and `state_scorer_audit_report.md`.

- **Deprecate the live-private value model as a one-turn branch scorer.** It is
  not a usable branch scorer: on sim-core branch states it collapses to ~+1 for
  *both* sides (train/serve feature skew). It is *not* sign-inverted or on the
  wrong checkpoint — it works on its native replay feature path. Keep it only as a
  diagnostic via `NEURAL_BRANCH_SCORER=value`.
- **Do not retrain it blindly.** A retrain only helps if trained/calibrated on the
  *live/sim-core* feature distribution (not reconstructed-replay states), with a
  bounded head (e.g. `tanh`) and a verified perspective flip. Required data: live
  sim-core trajectories labeled with perspective-correct outcomes (and ideally
  discounted returns), built through `build_features_from_live_payload` so train
  and serve match.
- **Adopt the simple exact-state material/HP scorer as the default research
  scorer for branch audits.** Paired audit: material/HP 45% vs heuristic 50%,
  beating the value-model scorer (0%), the action-value ranker (10%), and the
  approximate rollout (~40%). The richer "improved" state scorer regressed to 30%
  (passive, longer games), so the plain `(own_hp − opp_hp)/6` is the default;
  `NEURAL_BRANCH_SCORER=state` remains opt-in but is not recommended.
- **Action-value ranker:** its labels are value-deltas from the live-private value
  model, computed on the reconstructed-replay path where that model still
  discriminates, so they are not corrupted by the branch-state collapse. Do not
  retrain it solely for this finding; retrain only alongside a fixed/calibrated
  value head or a new explicitly-versioned target.
- **Keep disabled in live defaults:** approximate rollouts, one-turn branch
  evaluation, the value-model branch scorer, and any rollout-weighted action
  selection. Branch evaluation also relies on exact-opponent reconstruction
  (valid only in seeded research), so it is an upper bound and not live-ready.
  Live recommender weights/checkpoints unchanged.

## 6. Live/sim value head — train/serve skew fix outcome (2026-06-18)

See `live_sim_value_dataset_design.md`, `live_sim_value_dataset_report.md`,
`live_sim_value_training_report.md`, `live_sim_value_diagnostics.md`, and
`live_sim_value_branch_audit_report.md`. New artifacts:
`data/value/gen9randombattle_live_sim_value_v1.npz`,
`artifacts/checkpoints/gen9randombattle_live_sim_value_v1.pt` (bounded `tanh`,
`live-sim-bounded-value`, feature `live-private-belief-v2`/115D). Opt-in scorer:
`NEURAL_BRANCH_SCORER=live_sim_value`.

- **Did live/sim training fix the train/serve skew? Yes.** A bounded head trained
  on the serving distribution (2053 states from 40 seeded games, built through
  `build_features_from_live_payload`) no longer collapses: validation sign
  accuracy 86.4%, perspectives flip, terminal states separated (≈ ±0.96..0.99),
  early states near neutral.
- **Should the old live-private value model remain deprecated for branch scoring?
  Yes.** It still collapses on the serving path; use the new head if a value-based
  scorer is wanted, and keep the old one as `value` diagnostic only.
- **Should material remain the default branch research scorer? Yes.** Paired audit
  (same seeds): material 45% vs new live_sim_value 15% vs old value 0% vs ranker
  10% vs heuristic 50%. The calibrated value head beats the broken one but does
  not approach material; value-estimate lookahead turns passive (51 turns vs 37).
- **Should the new live/sim value scorer be used for future audits? As a
  diagnostic/research option, yes; as the default, no.** It is the correct value
  baseline now that the skew is fixed, but it is not competitive with material for
  one-turn branch selection.
- **Action-value ranker:** unchanged guidance — do not retrain solely for this.
- **Keep live defaults unchanged.** Nothing here promotes a learned scorer to
  live; production checkpoints were not overwritten.

Next best task: the bottleneck is now branch *search depth/quality*, not the value
estimator. Either (a) deepen beyond one ply (2-ply minimax with the material
scorer at the leaves, bounded N) to test whether real lookahead beats the 45%
one-ply material result, or (b) replace exact-opponent reconstruction with
randbats-belief opponent sampling to get a live-realistic (non-upper-bound)
measurement before any live consideration.

## 7. Randbats-belief two-ply outcome (2026-06-18)

See `randbats_belief_branch_design.md` and
`randbats_belief_branch_report.md`.

- Exact seeded two-ply remains the upper-bound research mode: 60%.
- Public-information randbats-belief two-ply scored 30%, below one-turn
  material (45%) and heuristic (50%).
- The corrected belief run had zero branch errors, timeouts, caps, public-state
  constraint violations, and damage fallbacks. The loss is belief/search
  quality, not plumbing.
- Keep belief mode as the preferred live-realistic diagnostic, but do not
  promote it as the strongest research agent or change live defaults.
- Next task: aggregate a small deterministic ensemble of sampled opponent
  states per decision instead of selecting against one belief particle.

## 8. Three-particle belief outcome (2026-06-19)

See `belief_particles_design.md` and `belief_particles_report.md`.

- Three deterministic belief particles scored 30% (6-14), exactly matching the
  single-particle result and remaining below one-turn material (45%) and
  heuristic (50%).
- The ensemble was mechanically clean: 2136 samples over 712 decisions, with
  zero belief errors, public-information violations, branch errors, timeouts,
  caps, and damage fallbacks.
- Average latency increased from 769 ms to 2469 ms (3.21×). Particle branches
  and leaves also increased by about 2.97×.
- Particles disagreed on their preferred action in 17.4% of decisions, and four
  paired battle outcomes changed, but the changes canceled to the same 6-14
  record.
- Keep exact two-ply as the upper bound. Keep single-particle belief as the
  cheaper live-realistic baseline and three-particle belief as an uncertainty
  diagnostic. Do not change live defaults.
- Next task: calibrate or weight particles with public damage, speed-order,
  reveal, and team-composition evidence before increasing particle count.
