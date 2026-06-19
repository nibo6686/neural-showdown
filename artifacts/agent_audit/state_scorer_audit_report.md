# One-Turn Branch Scorer Audit (Part E)

Audit date: 2026-06-18
Scope: seeded Gen 9 singles, 20 paired battles vs the heuristic baseline, six
workers, `--rollouts-per-action 1` (deterministic; one real sim-core step per
branch). Branch agents use opponent N=3. Runs A and B share seeds
(`make_battle_seed(index//2)`), so branch scorers are compared on identical games.

## Results

| Agent/scorer | Battles | Wins | Losses | Winrate | Avg latency | p95 latency | Branch errors | Damage fallbacks | Notes |
| ------------ | ------: | ---: | -----: | ------: | ----------: | ----------: | ------------: | ---------------: | ----- |
| heuristic | 20 | 10 | 10 | 50.0% | 1.6 ms | 3.1 ms | 0 | 0 | baseline (paired self-play) |
| action_value_ranker | 20 | 2 | 18 | 10.0% | 30.9 ms | 50.6 ms | 0 | 0 | learned ranker, no rollout |
| branch_one_turn — material/HP scorer | 20 | 9 | 11 | **45.0%** | 2189 ms | 4768 ms | 0 | 0 | `(own_hp − opp_hp)/6`, real post-step HP |
| branch_one_turn — improved state scorer | 20 | 6 | 14 | 30.0% | 4346 ms | 9829 ms | 0 | 0 | HP + alive/active/status/boost/hazard |
| rollout (approximate) | 20 | 8 | 12 | 40.0% | 53 ms | 85 ms | 0 | 0 | reference from prior batch (`one_turn_branch_report.md`) |
| branch_one_turn — live-private value scorer | 20 | 0 | 20 | 0.0% | 1701 ms | 3692 ms | 0 | 0 | reference; value model collapses on sim-core states |

All branch runs: 0 branch errors, 0 damage fallbacks, 0 rollout timeouts, 0
errors/timeouts.

## Reading the result

- The **simple HP-differential scorer is the best branch scorer** at 45%, nearly
  matching the heuristic (50%) and far above the learned ranker (10%) and the
  value-model scorer (0%).
- The **"improved" state scorer regressed to 30%** on the same seeds and made
  games much longer (avg 50.7 vs 37.0 turns) and slower (4346 ms vs 2189 ms avg).
  The extra tie-breaker terms (active-HP, status, boosts, hazards, alive-count)
  bias toward HP-preserving, switch-heavy, passive play that prolongs games
  without converting to wins. Pure net-damage pressure aligns better with
  winning. Simplicity won; the added terms were kept as an opt-in
  (`NEURAL_BRANCH_SCORER=state`) but are not recommended.
- The value-model scorer (0%) is the collapse documented in
  `value_model_diagnostics.md` — kept only as a diagnostic.

## Performance note

Latency scales with game length because every branch re-replays the full choice
history from the seed (sim-core exposes no mid-battle clone). The material scorer
is both stronger and ~2× faster than the improved scorer here precisely because
it ends games sooner. The clear next optimization remains batched lockstep replay
or a sim-core clone RPC (both accuracy-preserving).

## Caveat (unchanged)

In this seeded/paired audit the fork regenerates the opponent's true team from the
shared seed, so each branch is simulated against ground-truth hidden info. The
scorer reads only the audited player's legal view, but the simulated outcome
encodes hidden info, so these winrates are an optimistic upper bound and not a
live-play estimate. Keep branch evaluation out of live defaults.
