# Rollout Damage Plumbing Report

## Verdict

Autonomous approximate-rollout damage diagnostics now use Smogon Calc without
heuristic damage fallback in the 20-battle smoke. This fixes the damage
trustworthiness problem, but approximate rollouts remain diagnostic proxies,
not exact Showdown state transitions, so they are not yet suitable as production
training labels.

## Root cause

Two issues combined:

1. sim-core's shaped request exposes `side` as a Pokémon list. The live private
   state converter only accepted Showdown's raw `{side: {pokemon: [...]}}` form.
   Autonomous rollouts therefore lost the attacker's species, level, item,
   ability, moves, tera type, and exact stats before calling the damage engine.
2. Approximate diagnostics started a new Node process for every damage call.
   Direct and RPC damage tests passed, but autonomous audits were both slow and
   dependent on the malformed converted state.

The fallback originated in `neural.sim_branch_evaluator._damage_diagnostics`
after `neural.damage_engine.estimate_action_damage` received the incomplete
approximate state. The Smogon calculator itself was not the root cause.

## State now supplied

- Attacker: private species, visible random-battle level, item, ability, moves,
  tera state, status, boosts, current/max HP, and exact request stats.
- Defender: public species, visible level and HP/status/boosts, revealed
  ability/item/tera where known, plus top randbats item/ability/tera inference
  when private information is unavailable.
- Field: weather, terrain, Reflect, Light Screen, and Aurora Veil.
- Diagnostics: `damage_method`, exact-stat flags, `fallback_reason`,
  `rollout_damage_source`, and `rollout_damage_input`.

Unknown defender private stats remain inferred by Smogon Calc. They are not
misreported as exact.

## Before and after

| Metric | Before | After |
|---|---:|---:|
| Audit size | 4 battles | 20 battles |
| Heuristic fallback-marked decisions/calls | 69 decisions | 0 of 1,695 calls |
| Smogon Calc calls | not counted | 977 |
| Non-damaging diagnostics | not counted | 718 |
| Damage fallback rate | present | 0.0% |
| Rollout timeouts | not counted | 0 |
| Average decision latency | 4,146 ms | 51.2 ms |
| p95 decision latency | not counted | 77.7 ms |
| Battles per second | 0.033 | 1.19 |

The final smoke finished 20 battles in 16.77 seconds with six workers. It
recorded 4 wins and 16 losses against heuristic; clean damage does not make the
current approximate rollout policy stronger than the heuristic baseline.

The 20 generic selection fallbacks are one per battle at the initial request,
where sim-core returns no protocol delta yet and no approximate rollout state is
constructed. They are not damage fallbacks.

## Tests added

- Shaped private request lists preserve exact attacker stats through approximate
  rollout diagnostics.
- RPC failures expose a concrete fallback reason and source.
- Agent-audit summaries count total, Smogon, heuristic, reason, timeout,
  average-latency, and p95-latency metrics.
- Autonomous audit selection correctly records a clean Smogon/non-damaging mix
  as zero heuristic damage fallbacks.

## Files changed

- `trainer/src/neural/live_private_state.py`
- `trainer/src/neural/damage_engine.py`
- `trainer/src/neural/sim_branch_evaluator.py`
- `trainer/src/neural/live_action_recommender.py`
- `trainer/src/neural/agent_audit.py`
- `trainer/tests/test_damage_engine.py`
- `trainer/tests/test_agent_audit.py`
- `scripts/run_windows.ps1`
- `artifacts/agent_audit/recommendations.md`

## Dataset and checkpoint audit

`data/policy/gen9randombattle_action_value_rank_v2.npz` was generated on
April 28, 2026 and uses `live-private-belief-v2` state features and
`legal-action-v3` action features. Its chosen-action targets come from
before/after live-private value estimates plus final battle results; they are
not rollout-damage labels.

`artifacts/checkpoints/gen9randombattle_action_value_ranker_v2.pt` was trained
from that dataset on April 28, 2026. Neither artifact is stale because of the
exact-stat or rollout-damage fix. Keep both. No production retraining is
required for correctness.

No persistent rollout-derived training dataset was found. Any future dataset
whose labels use approximate rollout scores should be versioned and rebuilt
after the remaining rollout transition/state model is made trustworthy.

## Trust boundary

Damage diagnostics are now trustworthy enough for live evaluation and
diagnostic comparisons when their source fields are inspected. Approximate
rollout values are still heuristic one-step proxies with sampled opponent action
categories, not exact simulator branches. Keep them out of production labels
and live defaults for now.
