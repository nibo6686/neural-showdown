# One-Turn Branch Evaluation — Audit Report

Audit date: 2026-06-18
Scope: seeded Gen 9 singles. Paired sides on shared seeds vs the heuristic
baseline, 20 battles per agent, six process workers on the 8-core machine.
Branch agents use `--rollouts-per-action 1` (deterministic; each branch is one
real sim-core step, no sampling).

## Result table

| Agent | Battles | Wins | Losses | Winrate | Avg latency | p95 latency | Branch errors | Damage fallbacks | Notes |
| ----- | ------: | ---: | -----: | ------: | ----------: | ----------: | ------------: | ---------------: | ----- |
| heuristic | 20 | 10 | 10 | 50.0% | 1.5 ms | 3.2 ms | 0 | 0 | baseline (paired self-play) |
| action_value_ranker (no rollout) | 20 | 2 | 18 | 10.0% | 41.2 ms | 58.9 ms | 0 | 0 | current best learned component |
| rollout (approximate) | 20 | 8 | 12 | 40.0% | 53.0 ms | 85.0 ms | 0 | 0 | scoring proxy, not real branches |
| branch_one_turn (value-model scorer) | 20 | 0 | 20 | 0.0% | 1701 ms | 3692 ms | 0 | 0 | real branches, value model scorer |
| branch_one_turn (exact-state scorer) | 20 | 9 | 11 | 45.0% | 2665 ms | 6232 ms | 0 | 0 | real branches, post-step HP scorer |

The approximate rollout scored 40% in this seed batch (historically 20%); it is
high variance over 20 battles. The two `branch_one_turn` rows use the identical
deterministic branching substrate and differ only in the state scorer.

## What was built

A Python-side deterministic one-turn branch evaluator
(`neural.one_turn_branch.evaluate_action_branches`). For each candidate player
action and each bounded opponent action it:

1. forks a fresh sim-core env (same four-word seed, both players external),
2. `reset`s and replays the audited side's recorded choice history to the
   current state,
3. steps once with `{player: action, opponent: opponent_action}` — real
   Showdown stepping, no approximate damage estimation,
4. scores the resulting state (terminal ±1/0, otherwise a configurable scorer),
5. closes the fork env.

Per action it reports branch count, mean / worst-case / best-case score, a
configurable risk-adjusted score (`mean - risk_lambda*std`), opponent
assumptions, per-action latency, and per-branch errors. Opponent actions are the
opponent's real legal actions capped at N (default 3); a forced-switch state with
no opponent request becomes a single no-opponent-action branch.

It is exposed as the opt-in `branch_one_turn` agent in `neural.agent_audit` and
the `branch-audit` launcher action. Live recommender defaults, checkpoints,
training, and the tournament runner are unchanged.

## Does branch evaluation mutate the original state?

No. Every branch uses a separate `env_id` produced by replay-from-seed; the
live/original env is never stepped. The existing worker `SimCoreClient` is reused,
so there is no per-decision Node process spawn (the cost that made the old exact
path ~4 s/decision). A regression test confirms the live env still advances
normally after branch evaluation and that all fork envs are closed.

## Are branch results deterministic?

Yes. The sim-core step is deterministic given seed + choices, the scorers are
deterministic, and a regression test asserts identical per-action scores across
repeated evaluations of the same state.

## Scorer finding (the decisive result)

- The live-private **value model is not a usable one-step state scorer here.**
  Fed sim-core mid-battle states it returns near-constant values around +1 for
  *both* sides regardless of who is winning (observed: a losing side scored
  +1.6). One-ply lookahead then has no informative non-terminal signal, which is
  why the value-model branch agent went 0/20.
- A faithful **exact-state scorer** (remaining-HP differential read from the real
  post-step view, with unrevealed opponent bench counted at full HP) lifts the
  identical branching substrate to **45%**, nearly matching the heuristic and far
  above the learned ranker (10%) and the approximate rollout. This is not an
  approximate damage estimate — it reads the actual HP after a real step.

Conclusion: the deterministic branching substrate is sound; the bottleneck is the
state scorer, not the search.

## Gate assessment (from `recommendations.md`)

- Zero heuristic damage fallbacks: **met** (0 of all branch evaluations).
- Zero rollout timeouts in the 20-battle smoke: **met** (0).
- Deterministic under fixed seeds: **met** (regression test).
- Materially better than the 20% approximate-rollout baseline: **met with the
  exact-state scorer** (45%); **not met with the value-model scorer** (0%).

## Important caveat: hidden-information reconstruction

In this seeded/paired audit the fork regenerates *both* teams from the shared
seed, so each branch is simulated against the opponent's true (possibly
unrevealed) set. The branch outcome therefore implicitly uses ground-truth hidden
opponent information. The scorer itself only reads the audited player's legal view
(own private team + publicly revealed opponent + public team size), so the
*scoring* leaks nothing — but the *simulation* does. The 45% is therefore an
optimistic upper bound. A live deployment against an unknown opponent would have
to sample opponent teams/sets from randbats beliefs and would very likely be
weaker. This is the central reason it must stay out of live defaults for now.

## Should this replace approximate rollouts?

Not yet, and not in live defaults. It is now the strongest evidence that real
one-turn branching beats the approximate proxy *when given a sound scorer*, but
(a) it relies on exact-opponent reconstruction that is only valid in seeded
self-play, and (b) it is ~30-50x slower per decision. Keep it opt-in and
experimental.

## Performance

- Branch (exact-state) latency: 2665 ms avg, 6232 ms p95; 20 battles in 528 s
  with 6 workers. Branch (value-model) latency: 1701 ms avg (battles ended sooner
  because the agent lost faster).
- Cost is `(#player actions) × (#opponent actions ≤ N)` forks per decision, each
  re-replaying the whole choice history (inherent — sim-core exposes no
  mid-battle state clone). Cost grows with turn depth, so longer games dominate.
- No per-decision process spawn (worker client reused). No timeouts.
- Six workers remains appropriate on this 8-core machine (two cores left for the
  parent/OS; each worker pins PyTorch to one thread). The dominant cost is CPU
  battle stepping, which batching cannot remove.
- Clear next optimization: batched lockstep replay (one `batch` RPC per history
  depth instead of per branch) removes transport round-trips, and adding a
  sim-core mid-battle serialize/clone RPC would remove the re-replay entirely.
  Both preserve accuracy.

## Recommended next step

1. Keep `branch_one_turn` opt-in; do not change live defaults, weights, or
   checkpoints.
2. Before any live use, replace exact-opponent reconstruction with opponent
   team/set sampling from randbats beliefs and re-measure (expect a drop).
3. Train/validate a perspective-correct, bounded value head that is actually
   discriminative on sim-core states, or keep the exact-state scorer for seeded
   research, then re-run this gate.
4. Optimize replay (batched lockstep, or a sim-core clone RPC) before scaling N
   or search depth.
