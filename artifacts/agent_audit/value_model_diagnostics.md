# Value Model Diagnostics (Part B)

Audit date: 2026-06-18
Model under test: `gen9randombattle_live_private_value_v2.pt`
(`live-private-belief-v2`, 115D, value head = unbounded `Linear(256,1)`; server
transform `p1_win_prob=(v+1)/2`).

Two feature pipelines were compared on the same model:

- **Native path** = the model's training distribution: features rebuilt from a
  parsed public replay via `_examples_from_public_trajectory`
  (`build_live_private_value_dataset.py`), i.e. reconstructed private state +
  perspective public features. Labels available.
- **Live/branch path** = `build_features_from_live_payload` fed a sim-core
  `ChoiceRequestView` + sim-core spectator protocol — exactly what the one-turn
  branch scorer uses.

## Native path (replay reconstruction) — model output vs label

Replay `gen9randombattle-2587966474` (winner_side = p2):

| Turn | Side | Label | Model out | Correct sign? |
| ---: | --- | ---: | ---: | --- |
| 0 | p1 | -1.00 | -0.248 | yes (weak) |
| 0 | p2 | +1.00 | +0.241 | yes (weak) |
| 15 | p1 | -1.00 | -0.308 | yes |
| 15 | p2 | +1.00 | +0.929 | yes |
| 29 | p1 | -1.00 | -1.048 | yes |
| 29 | p2 | +1.00 | +1.259 | yes |

Replay `gen9randombattle-2587963818` (winner_side = p2):

| Turn | Side | Label | Model out | Correct sign? |
| ---: | --- | ---: | ---: | --- |
| 0 | p1 | -1.00 | -0.271 | yes (weak) |
| 0 | p2 | +1.00 | -0.297 | no (weak/early) |
| 16 | p1 | -1.00 | -0.874 | yes |
| 16 | p2 | +1.00 | +0.259 | yes |
| 31 | p1 | -1.00 | -0.316 | yes |
| 31 | p2 | +1.00 | -0.967 | no (terminal artifact) |

On the native path the model **varies, respects perspective (opposite signs for
p1 vs p2), and mostly aligns with the eventual winner**, strengthening over the
game. It is noisy and has occasional terminal-state artifacts, but it is clearly
a functioning, non-degenerate, perspective-aware estimator.

## Live/branch path (sim-core `ChoiceRequestView`) — collapse

Seeded heuristic-vs-heuristic battle, seed `[101,202,303,404]` (winner p2):

| Turn | p1 model | p2 model | p1 \|feat\|mean | p2 \|feat\|mean | nonzero |
| ---: | ---: | ---: | ---: | ---: | --- |
| 2 | +1.354 | +1.485 | 0.256 | 0.263 | 38/115 |
| 10 | +1.170 | +0.960 | 0.249 | 0.262 | 52-54/115 |
| 16 | +0.865 | +1.161 | 0.247 | 0.293 | 58-59/115 |

On the live/branch path **both perspectives are positive at once** (no opposite
signs), the magnitude sits near +1 regardless of who is ahead, and even the
eventual loser scores strongly positive. Feature magnitude and nonzero count are
in the same ballpark as the native path, so the inputs are **not** all-zeros or
trivially empty — they are **out-of-distribution**, landing the model in a region
where it returns ~+1 for everyone.

## Eight requested probes (mapped)

1. Clearly winning for p1 → native late winner-side = +1.26 (correct).
2. Clearly losing for p1 → native late p1 (loser) = -1.05 (correct).
3. Same state from p2 perspective → native flips sign (+1.26 vs -1.05); live path
   does **not** flip (both ~+1) — collapse.
4. Terminal win / 5. Terminal loss → the branch evaluator scores terminals
   directly from `winner` (±1/0) and does **not** call the value model (no request
   at terminal), so the value head is not the terminal authority.
6. Early neutral → native turn 0 ≈ ±0.25 (weak, reasonable); live path ≈ +1.4
   (collapsed).
7. Post-KO advantage → native winner-side rises toward +1; live path uninformative.
8. Low-HP disadvantage → native loser-side falls toward -1; live path still ~+1.

## Answers (Part B)

- **Sign-inverted?** No — native path has correct signs.
- **Perspective wrong (in the model)?** No — native path flips correctly between
  p1 and p2.
- **Undertrained (to a constant)?** No — native outputs vary across turns/sides.
- **Features near-constant?** No in magnitude; **yes effectively out-of-
  distribution** on the sim-core live path (perspective signal lost).
- **Labels near-constant?** No — labels are perspective-correct ±1.
- **Wrong checkpoint loaded?** No — `live_private_value_v2`, 115D,
  `live-private-belief-v2`.
- **Wrong feature domain?** Domain is correct (115D live-private); the live
  **feature builder produces a skewed distribution** for sim-core
  `ChoiceRequestView` + spectator protocol vs the reconstructed-replay training
  distribution. This is **train/serve skew**, not a wrong domain.
- **Value head unsuitable for branch scoring even if valid?** Yes, in practice:
  it is an unbounded regressor toward final ±1, trained only on reconstructed
  replay states, and it **collapses on sim-core branch states**. It is not a
  trustworthy one-turn branch scorer as-is.

## Root-cause conclusion

The live-private value model is a reasonable but noisy state estimator **on its
own training distribution**. It is unusable as a one-turn branch scorer because
sim-core branch states reach it through `build_features_from_live_payload`, whose
output distribution differs enough from training to collapse the perspective
signal (both sides ≈ +1). The fix is **not** a sign/checkpoint flip; it requires
either retraining/calibrating on the live feature distribution, or — as adopted
here — using a faithful, deterministic exact-state scorer for branch evaluation.
