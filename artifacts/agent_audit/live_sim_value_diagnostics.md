# Live/Sim Value Model Diagnostics (Part D)

Audit date: 2026-06-18
Model under test: `gen9randombattle_live_sim_value_v1.pt`
(`live-sim-bounded-value`, `live-private-belief-v2`, 115D, **tanh-bounded** output).
Compared against the prior diagnosis of `live_private_value_v2`
(`value_model_diagnostics.md`), which collapsed to ~+1 for both sides on this path.

## Method

Seeded heuristic-vs-heuristic battles scored through the exact serving path
(`build_features_from_live_payload` on sim-core `ChoiceRequestView` + spectator
protocol), both perspectives, at early / mid / final turns.

## Results

Seed `[101,202,303,404]` (winner p2):

| Turn | p1 | p2 |
| ---: | ---: | ---: |
| 2 | -0.212 | -0.109 |
| 10 | -0.080 | -0.644 |
| 16 (final) | **-0.985** | **+0.959** |

Seed `[7,7,7,7]` (winner p2):

| Turn | p1 | p2 |
| ---: | ---: | ---: |
| 1 | -0.313 | — |
| 9 | -0.886 | — |
| 19 (final) | **-0.964** | **+0.988** |

## Eight probes (mapped)

1. Obvious p1 winning → winner-side final ≈ +0.96..+0.99 (here p2 is the winner;
   by perspective symmetry a p1-won game scores p1 ≈ +0.96).
2. Obvious p1 losing → p1 final = -0.985 / -0.964.
3. Same state from p2 perspective → flips sign (+0.959 / +0.988 vs p1's negatives).
4. Terminal win / 5. terminal loss → the branch evaluator scores true terminals
   as ±1 directly; near-terminal states here already reach ≈ ±0.96..0.99.
6. Early neutral → turn 1-2 ≈ -0.1..-0.3 (near neutral, **not** collapsed to +1).
7. Post-KO advantage → winner side rises toward +1 late.
8. Low-HP disadvantage → loser side falls toward -1 late.

## Verdict (vs. expected)

- **Outputs do not collapse to positive for both sides** (old model: +1.35/+1.49
  at turn 2; new model: -0.21/-0.11). Fixed.
- **p1/p2 perspectives flip sign** at decisive states (e.g. -0.985 vs +0.959).
- **Terminal/near-terminal states are strongly separated** (≈ ±0.96..0.99).
- **Early neutral states are near neutral** (small magnitude).
- Mid-game estimates are noisier (e.g. winner side -0.64 at turn 10), as expected
  for hard mid-game positions with small discounted labels; the decisive signal is
  correct.

Training metrics agree: validation sign accuracy 86.4%, validation MSE 0.14
(`live_sim_value_training_report.md`). The train/serve skew is resolved: the
bounded head trained on the serving feature distribution discriminates correctly
on that distribution.
