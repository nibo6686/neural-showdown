# Live/Sim Value Branch Audit (Part F)

Audit date: 2026-06-18
Scope: seeded Gen 9 singles, 20 paired battles vs the heuristic baseline, six
workers, `--rollouts-per-action 1`, branch opponent N=3. Runs share seeds
(`make_battle_seed(index//2)`), so branch scorers are compared on identical games.

## Results

| Agent/scorer | Battles | Wins | Losses | Winrate | Avg latency | p95 latency | Branch errors | Damage fallbacks | Notes |
| ------------ | ------: | ---: | -----: | ------: | ----------: | ----------: | ------------: | ---------------: | ----- |
| heuristic | 20 | 10 | 10 | 50.0% | 1.4 ms | 2.8 ms | 0 | 0 | baseline (paired self-play) |
| action_value_ranker | 20 | 2 | 18 | 10.0% | 23.7 ms | 27.9 ms | 0 | 0 | learned ranker, no rollout |
| branch_one_turn — material/HP | 20 | 9 | 11 | **45.0%** | 1941 ms | 4246 ms | 0 | 0 | `(own_hp − opp_hp)/6`, real post-step HP |
| branch_one_turn — **live_sim_value (new)** | 20 | 3 | 17 | **15.0%** | 2648 ms | 5393 ms | 0 | 0 | bounded tanh head, trained on serving distribution |
| branch_one_turn — live_private_value (old) | 20 | 0 | 20 | 0.0% | 1701 ms | 3692 ms | 0 | 0 | reference; collapsed scorer (diagnostic only) |

All runs: 0 branch errors, 0 damage fallbacks, 0 rollout timeouts, 0 errors.

## Reading the result

- **The new live/sim value scorer beats the deprecated live-private value scorer
  (15% vs 0%).** The targeted train/serve-skew fix worked: the bounded head trained
  on the serving feature distribution no longer collapses (diagnostics: sign
  accuracy 86.4%, perspectives flip, terminal states separated). Success criterion
  "must beat the old value scorer" — **met.**
- **It does not approach the material scorer (15% vs 45%).** Success criterion
  "should at least approach material" — **not met.** Even a calibrated value head
  is a noisier one-step branch signal than the direct HP differential: mid-game
  value estimates hover near neutral, so the lookahead does not reward pressing
  damage and play turns passive (avg 51.1 turns, like the earlier "improved" state
  scorer's failure mode) vs material's 37.0.
- **Material stays the default research scorer.** It is not promoted away; the new
  scorer is opt-in (`NEURAL_BRANCH_SCORER=live_sim_value`).

## Interpretation

Fixing the value model's train/serve skew was necessary and is now done — the
value head is trustworthy as an *estimator* on the serving distribution. But a
value-estimate is still not the best *branch-selection* signal for one-turn
lookahead; the exact post-step HP differential is. This mirrors the earlier
finding that the richer hand-written state scorer underperformed plain material.

## Caveat (unchanged)

Branch evaluation still forks the exact seeded opponent, so winrates are an
optimistic upper bound and not a live-play estimate. Live defaults unchanged.
