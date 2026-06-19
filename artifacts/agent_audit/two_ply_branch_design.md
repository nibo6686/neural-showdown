# Bounded Two-Ply Branch Search — Design

Audit date: 2026-06-18  
Scope: deterministic seeded Gen 9 singles research only.

## Existing one-turn flow

`neural.one_turn_branch.evaluate_action_branches` evaluates every bounded
`(player action A, opponent action B)` pair by creating a fresh sim-core env,
resetting it from the battle seed, replaying the recorded choice history, and
stepping the real Showdown simulator once. Terminal outcomes score as `+1/-1/0`;
otherwise the default research scorer is remaining-HP differential from the
post-step legal view. The live/original env is never stepped.

## Proposed bounded two-ply flow

Pokemon turns are simultaneous, so A and B form the first real sim step. A
second own action C requires an opponent choice on that next request as well.
The bounded search therefore uses:

1. Rank and cap legal root actions A (all legal unless more than the root cap).
2. Rank and cap the opponent's current legal replies B.
3. Fork/replay the current state and step `(A, B)`.
4. If terminal, score the true result.
5. If the audited player receives another actionable request, rank and cap its
   follow-up actions C.
6. Select the opponent's next-turn action deterministically with the existing
   heuristic agent and step `(C, heuristic reply)` in a fresh replayed fork.
7. Score terminal leaves by true result and non-terminal leaves with the
   material/HP scorer.
8. For each B, keep the best C leaf (our choice). Aggregate those response
   values for A by mean, while also reporting worst, best, standard deviation,
   and `mean - risk_lambda * std`.

This is intentionally not a full depth-two minimax tree: the second opponent
choice is one deterministic heuristic reply rather than another N-way branch.
That keeps the research question focused and bounds the cost.

## Forking and replay

sim-core has no mid-battle clone API. Every root or leaf branch therefore:

- creates a separate external-vs-external env with the same four-word seed;
- resets it;
- replays the exact recorded choice history;
- applies the branch choices;
- closes the fork in `finally`.

The original battle env is never mutated. Same seed, history, actions, and
configuration produce the same result.

## Action bounds

- Root actions: heuristic-preferred first, then deterministic legal order;
  evaluator default cap 6.
- Opponent B actions: heuristic-preferred first, then deterministic legal order;
  default cap 3.
- Own C actions: heuristic-preferred first, then deterministic legal order;
  evaluator default cap 3.
- Opponent's second-turn reply: one deterministic heuristic action.

The heuristic is used only for action ordering/bounding. All state transitions
and leaf HP values come from the real sim-core.

## Leaf scoring and aggregation

- Terminal win/loss/tie overrides every state scorer with `+1/-1/0`.
- Non-terminal leaves use the existing material scorer:
  `(own remaining HP - opponent remaining HP) / 6`, clipped to `[-1, 1]`.
- For each opponent response B, choose the highest-scoring legal C leaf.
- Default root value: mean over bounded B responses.
- Also record worst case, best case, standard deviation, and risk-adjusted
  score. The audit default uses `risk_lambda=0`, so selection is by mean.

## Caps, errors, and unsupported states

The evaluator records transition count, leaf count, branch errors, timeout
count, damage fallbacks, latency, and cap/fallback use. A per-decision deadline
prevents runaway replay cost. If it is reached after `(A, B)`, that real
one-turn successor is scored directly with material as a capped fallback leaf.
Errors are attached to their action and do not crash the battle.

Root forced-switch requests are explicitly unsupported by the two-ply policy
and fall back to the existing one-turn material evaluator. Forced switches
reached after `(A, B)` are legal follow-up requests and are searched normally.

## Latency risk

Without caps, work grows roughly as:

`root_actions * opponent_N * (1 + followup_M)` replayed transitions.

Replay cost also grows with battle length because every fork replays from turn
zero. The initial 6/3/3 smoke permits at most 72 transition branches per
decision. If that is too slow, the audit agent is capped to 3 root actions,
opponent N=3, follow-up M=2, and an eight-second decision budget before the
20-battle run. The audit must measure average and p95 decision latency,
branches, leaves, errors, and timeouts before recommending further depth.

## Hidden-information caveat

Seed replay regenerates the opponent's exact hidden team and set. The scorer
reads only the audited player's legal view, but simulated outcomes still encode
ground-truth hidden information. Results are therefore an optimistic
exact-seeded research upper bound, not a live-play estimate. The agent remains
opt-in and live defaults remain unchanged.
