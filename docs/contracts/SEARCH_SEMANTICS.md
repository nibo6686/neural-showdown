# Current Rollout and Search Semantics

Status: SEARCH-001 documentation slice (2026-09-23).

This document records the current implementation. It does not define a new
search API or claim that the accepted state, action, belief, or seeded-transition
contracts are already consumed by search.

## Input and integration boundary

The legacy rollout wrapper is
`trainer/src/neural/sim_branch_evaluator.py:evaluate_actions`. It accepts a
trace/trajectory, player side, caller-provided legal-action dictionaries, and a
rollout configuration. It selects the latest trace step by default, reads a
four-word seed from trace metadata or a `>start` record when available, and
chooses `exact` or `approximate` (`auto` means exact when a seed is found,
approximate otherwise). Exact mode can still fall back to trace scoring or
report unavailable when replay setup fails.

The separate `one_turn_branch` and `two_ply_branch` APIs take a seed, ordered
choice history, request objects, and a sim-core client. Two-ply belief mode also
requires a source environment and belief-fork seed. The word “belief” here means
the existing simulator hidden-state fork; it is not a `BeliefState` search
consumer.

Current search does not take `ObservableBattleState`, `CanonicalAction`,
`BeliefState`, or `SeededTransition` as its input contract. Those accepted
interfaces are additive and remain outside existing search call sites. In
particular, the `seeded_transition_v1.json` fixture validates the separate
TRANS-001 boundary; it is not a search branch fixture and is not executed by
these legacy evaluators.

## Modes and branch construction

| Path | Action enumeration | RNG and state construction | Evaluation context |
|---|---|---|---|
| Exact replay rollout (`sim_branch_evaluator`) | Uses the supplied player actions and maps their indices to the replayed request choices. Takes the first bounded opponent legal actions (`max_opponent_actions`). Repeats each pair `rollouts_per_action` times. | Creates a fresh sim-core environment and replays the trace prefix for each sample. The base seed is offset deterministically per sample. This reconstructs from seed and history; it does not clone the current environment or use a TRANS-001 snapshot handle. | Uses the new step's log delta/omniscient records with `view` and request derived from the selected trace step and the trace's earlier steps. It does not score the returned branch observation as a new feature context. |
| Approximate rollout (`sim_branch_evaluator`) | Uses the supplied player actions. Samples abstract opponent categories (`attack`, `switch`, `status`, `setup`, `protect`) with configured count/weights; these are not legal Showdown choices. | Builds an approximate state from trace-derived view/request, private request state, public protocol context, and opponent beliefs. It samples scalar noise; it does not apply simulator transitions or create successor battle states. Its RNG seed uses Python `hash((replay_id, step_index, player_side))`, so results are not guaranteed to match across processes with different hash randomization. | Computes existing heuristic action diagnostics and features from the reconstructed approximate state. `top_resulting_states` are sampled score summaries, not materialized battle states. |
| One-turn exact branch (`one_turn_branch`) | Enumerates the current player's request legal actions and a bounded prefix of opponent request legal actions; an empty opponent action set is one no-op branch. | Each branch creates a fresh environment, resets it from the supplied seed, replays the supplied history, then performs one legacy `step`. It does not mutate the caller's environment. | Terminal results use winner/tie score. Nonterminal results use the supplied scorer on the emitted protocol and step result. |
| Two-ply / belief two-ply (`two_ply_branch`) | Bounds root, opponent, and follow-up actions. Ordering first prefers a simulator heuristic action, then moves, then request index. A follow-up opponent heuristic choice is selected rather than fully enumerated. | Non-belief branches replay into fresh environments. Belief branches call `fork_belief_env`, which samples/rewrites hidden simulator state. Particle seeds are derived by fixed per-word offsets from the base belief seed; particle zero retains the base seed. This is a simulator fork, not BeliefState propagation or an exact seeded transition. | Terminal leaves use actual winner/tie score; nonterminal leaves use the supplied scorer. Missing follow-up requests and deadline caps are scored at the preceding state. Non-belief root forced-switch requests use the one-turn fallback. |

These are distinct implementations, not values of one shared mode enum. The
legacy trace evaluator in `action_value_search.py` is another path: it scores
the observed chosen action from trace continuation and does not itself simulate
alternate actions.

## State, belief, action, and transition lineage

Exact replay branches have seed/history inputs and fresh environment IDs, but
do not emit the accepted transition IDs, parent/child branch IDs, snapshot
fingerprints, or action IDs. The seeded transition contract's authoritative
snapshot and fail-closed joint-action validation are not used by these paths.
There is no stable search-node identity shared across these evaluators: exact
branches are reconstructed environments, approximate samples are scalar
summaries, and belief branches are identified only through simulator fork and
particle metadata.

Belief branches expose the existing fork metadata and particle seed lineage.
They do not import, extend, or serialize BeliefState v1. BeliefState's
perspective, observation-prefix, and transition-history validation therefore
does not automatically validate search branches.

Search candidates remain legacy action dictionaries/request indices. The
current path does not require CanonicalAction IDs or revalidate every caller
action against a request identity before mapping it. Missing choices and failed
steps are recorded as branch errors in the branch evaluators, but the legacy
replay wrapper can use a `default` choice when an index cannot be mapped. Do
not describe stale or invalid actions as fail-closed at the legacy search
boundary. Fail-closed validation is established by the additive canonical
action and seeded-transition APIs only.

## Determinism, terminal states, and forced switches

For exact replay/branch paths, fixed seeds, ordered histories/actions,
sim-core version, and configuration determine the branch inputs. Exact rollout
uses deterministic seed offsets; two-ply belief particles use deterministic
seed derivation. Wall-clock deadlines can truncate two-ply work, and failures
can remove branches, so a deadline-limited report need not contain the same
number of leaves under different runtime load.

Approximate rollout uses process-randomized Python `hash()` to seed NumPy and
does not provide a cross-process fixed-seed guarantee. Its name and reported
sample count do not imply simulator transitions.

One- and two-ply branch evaluators explicitly score terminal results from the
winner. The legacy exact rollout wrapper does not use that terminal override;
it tries its value function on trace-derived context. Two-ply search detects a
nonterminal state with no next player request and scores that state without a
follow-up. Root forced-switch requests take the one-turn fallback in ordinary
two-ply mode. Belief two-ply does not take that specific fallback branch.

## Feature context, privacy, and future-event limits

Approximate state construction calls `trajectory_prefix` at the selected
trace-step turn and derives its view/request from that selected step. It uses
the acting side's request/private state plus public protocol-derived tactical
state and opponent beliefs; it does not consume a sanitized
ObservableBattleState. The protocol cutoff is turn-based, not the exact record
cursor required by ObservableBattleState. Records later in the same turn may
therefore remain in the approximate protocol context. Exact replay scoring
likewise combines branch output records with the selected trace step's
view/request context, rather than constructing an observation for the branch
output. Belief forks deliberately contain sampled simulator-only hidden state;
they must not be interpreted as player-observable state.

Accordingly, current search does **not** establish the accepted
ObservableBattleState guarantee that every node is bound to an exact sanitized
protocol prefix. The accepted observable-state fixture proves prefix isolation
for that adapter, and BeliefState rejects future/stale evidence, but neither
test makes the legacy search paths consume those contracts. Search-level
future-event isolation and request/action lineage remain open integration
constraints; this documentation slice does not claim they are solved.

The existing feature builders, feature vectors, checkpoints, and model inputs
remain unchanged. Search calls existing scorers/feature builders. The
vNext v7/v5 feature path and its checkpoint are not wired into these live
search paths.

## Evidence references

- `trainer/tests/test_sim_rollout.py`: exact seeded wrapper success, exact
  missing-seed fallback, and approximate mode selection.
- `trainer/tests/test_two_ply_branch.py`: fixed-input branch repeatability,
  forced-switch fallback, belief-particle behavior, and terminal scoring.
- `trainer/tests/test_belief_branch.py`: seeded simulator belief forks and
  distinct particle seeds.
- `sim-core/tests/observable_state_fixture.test.ts`: exact observable-prefix
  extension and exclusion of later events at an earlier prefix.
- `sim-core/tests/transition.test.ts`: deterministic seeded snapshot/transition
  identity, atomic invalid-action rejection, and replay-equivalent transitions.
- `sim-core/tests/belief_state.test.ts`: observation/transition lineage and
  rejection of future, stale, mismatched, or cross-perspective evidence.
- `tests/fixtures/seeded_transition_v1.json`: accepted TRANS-001 fixture; it is
  referenced for the separate transition contract, not as proof of current
  search integration.

No production behavior, accepted contract, feature vector, checkpoint, live
default, or search call site is changed by SEARCH-001.
