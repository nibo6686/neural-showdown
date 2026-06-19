# One-Turn Branch Evaluation — Design Note (Part A)

Audit date: 2026-06-18
Scope: seeded Gen 9 singles only. This note inventories the existing
rollout/action-diagnostic path and specifies the smallest clean interface for
deterministic one-turn sim-core branch evaluation.

## Where approximate rollout scoring currently happens

- `neural.sim_branch_evaluator.evaluate_actions` is the single entry point used
  by the live recommender. It chooses between:
  - `_approximate_decision_rollout` — heuristic per-action scoring plus Gaussian
    noise and sampled opponent *categories* (`attack/switch/status/setup/protect`).
    This is a scoring proxy; it never steps the simulator.
  - the "exact" path — replays a stored **trace** (turn/step records with
    `chosen_action_index`) from a four-word seed by creating a fresh env,
    `reset`, and replaying recorded choices with `_replay_to_step`, then forces
    one player action against bounded opponent actions and scores the resulting
    state with the value model.
- `neural.live_action_recommender.recommend_actions` builds a synthetic
  single-step trace (`_trace_payload_for_branch_evaluation`) and calls
  `evaluate_actions`. In live/autonomous use there is no seed in the synthetic
  trace, so it always lands in `_approximate_decision_rollout`.
- `neural.analyze_rollout_actions` is a CLI wrapper around the same
  `evaluate_actions` for saved replay traces.

Conclusion: the only code today that actually steps sim-core for branching is the
trace-replay "exact" path, and it is reachable only for stored local traces that
carry a seed plus recorded action indices. Live autonomous decisions never reach
it.

## How candidate actions are generated

- Legal actions come from the authoritative Showdown `|request|`, normalized by
  sim-core into `legal_actions.actions[i]` with `index`, `kind`, `label`, and the
  concrete `choice` string. `live_action_recommender.legal_action_candidates`
  reconstructs the same set from a live payload when needed.

## How opponent policy is represented

- Approximate path: five hard-coded opponent *categories* with fixed weights,
  capped by `max_opponent_actions` (default 3).
- Exact trace path: the opponent's real legal actions from the replayed env's
  `requests`, capped at `max_opponent_actions` (default 3, first-N order).

## How current battle state is serialized

- A `StepResult` carries per-player `views` (public + own private team) and
  `requests` (sim-core `ChoiceRequestView`: `side` as a Pokémon list, `active`,
  `legal_actions`, plus `raw`), `log_delta` (public spectator protocol), plus
  `terminated`/`winner`/`info.turn`.
- The live value model consumes a protocol `log` plus the player's request view
  via `live_private_features.build_features_from_live_payload`. The agent audit
  already feeds sim-core `ChoiceRequestView` dicts straight into this path
  (`_learned_choice` → `evaluate_with_model`), so the same request view is a
  valid value-model input after a branch step.

## Can sim-core clone/fork a battle safely?

- No native clone. `LocalBattleEnv` wraps a live `BattleStream` and per-player
  async streams. There is no RPC to serialize/deserialize mid-battle state, and
  `create_env`/`reset` only accept a format + four-word seed (teams are
  regenerated deterministically from the seed).
- The supported, already-proven way to reach an arbitrary state is
  **deterministic replay-from-seed**: create a fresh env with the same seed and
  both players external, `reset`, then replay the exact sequence of submitted
  choices. Same seed + same choices ⇒ identical state (verified by existing
  exact-rollout tests and the seed/team determinism tests).

## Are deterministic seeds controllable?

- Yes. `create_env` accepts four integer seed words; teams derive from the env
  seed (offsets +11/+29) and the battle PRNG is seeded from it. The agent audit
  already drives battles from explicit `make_battle_seed(...)` values.

## Can branch evaluation run without mutating the live/original environment?

- Yes, via replay-from-seed into a **separate** `env_id`. The original env is
  never stepped. Reusing the existing worker `SimCoreClient` (one Node process,
  serialized request queue) avoids the per-decision process spawn that made the
  old exact path cost ~4 s/decision.

## Design for the new path

A Python-side helper (`neural.one_turn_branch.evaluate_action_branches`) that:

1. Takes the audited side's recorded **choice history** for the current battle,
   the env seed, the format, and a live `SimCoreClient`.
2. For each candidate player action and each bounded opponent action:
   - forks a fresh env (same seed, both external), `reset`, replays the choice
     history to the current state, then steps once with
     `{player: action, opponent: opp_action}` — real sim-core stepping, no
     approximate damage scoring;
   - scores the resulting state with the existing live-private value model from
     the audited side's perspective, or a terminal ±1/0 if the branch ended;
   - closes the fork env.
3. Aggregates per action: branch count, mean / worst-case / best-case score, a
   configurable risk-adjusted score (`mean - risk_lambda * std`), opponent
   assumptions, per-branch latency, and any branch errors.

Opponent bounding (config `max_opponent_actions`, default 3): the opponent's real
legal actions from the live opponent request, capped at N (first-N order, with a
`moves_first` option). When the opponent has no actionable request (e.g. the
audited side is in a forced switch), a single no-opponent-action branch is used.

Scoring is deterministic: the simulator step is deterministic given seed +
choices, and the value model runs in eval mode. No heuristic damage estimation is
used anywhere inside branch evaluation, so it cannot emit a damage fallback.

Integration: a new opt-in agent (`branch_one_turn`) in `neural.agent_audit`,
selected by max risk-adjusted score. Live recommender defaults, checkpoints,
training, and the tournament runner are left unchanged.

Performance: cost is `(#player actions) × (#opponent actions ≤ N)` forks, each
re-replaying the history (inherent — there is no state clone). The worker client
is reused so there is no per-decision Node spawn. Default N is kept small (3) and
latency/branch counts are measured and reported in the audit.
