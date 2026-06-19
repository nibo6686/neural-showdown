# Live-Eval Calibration Report (Part C)

**Date:** 2026-06-18
**States:** 1406 (24 seeded games; 672 win / 734 loss outcomes, perspective-correct)
**Source:** `live_eval_calibration_states.jsonl` /
`live_eval_calibration_metrics.json`

Win-probability for all metrics uses the same mapping `/evaluate` applies:
`prob = clamp((score + 1)/2, 0, 1)`, win label = 1 if the side won. Brier and AUC
exclude ties (none here). Perspective-flip pairs compare the same physical state
scored from both sides; a consistent scorer is anti-symmetric, so
`mean|score_p1 + score_p2| ≈ 0` and `corr(score_p1, −score_p2) ≈ 1`.

## Headline table

| Scorer | Sign acc | Brier | AUC | Mean winning score | Mean losing score | Perspective sanity | Notes |
| ------ | -------: | ----: | --: | -----------------: | ----------------: | ------------------ | ----- |
| **material/HP** | 0.816 | 0.155 | 0.931 | +0.276 | −0.233 | **excellent** (\|Σ\|=0.08, corr=0.95) | simple, anti-symmetric by construction, never saturates (0.3% \|s\|>0.9) |
| **live_sim_value** | **0.936** | **0.066** | **0.987** | +0.583 | −0.668 | **good** (\|Σ\|=0.14, corr=0.93) | best discrimination + calibration; bounded tanh; some saturation (28.5%) |
| **old_live_private** (`/evaluate` default) | 0.558 | 0.395 | 0.654 | **+1.308** | **+0.853** | **broken** (\|Σ\|=2.09, corr=0.06) | collapsed: positive for wins *and* losses; 73.7% saturated; perspective not anti-symmetric |

Brier reference: a no-skill constant 0.5 predictor scores 0.25. **The `/evaluate`
default (0.395) is worse than no-skill.** Both research scorers beat it decisively.

## Reliability (predicted win-prob vs empirical)

**old_live_private** — catastrophic overconfidence:

| Bin | n | pred | empirical |
| --- | ---: | ---: | ---: |
| [0.0,0.5) | 112 | — | 0.00 |
| [0.5,0.6) | 32 | 0.55 | 0.00 |
| [0.6,0.7) | 39 | 0.66 | 0.18 |
| [0.7,0.8) | 74 | 0.75 | 0.50 |
| [0.8,0.9) | 90 | 0.86 | 0.44 |
| **[0.9,1.0]** | **1059** | **0.99** | **0.555** |

It assigns ~0.99 win-prob to **1059 of 1406** states whose true win rate is only
0.555. After the unbounded value (~+1.07 mean) is mapped through `(v+1)/2` and
clamped, almost everything reads as a near-certain win.

**live_sim_value** — monotonic, near-diagonal:

| Bin | n | pred | empirical |
| --- | ---: | ---: | ---: |
| [0.0,0.1) | 324 | 0.03 | 0.00 |
| [0.3,0.4) | 89 | 0.35 | 0.21 |
| [0.4,0.5) | 135 | 0.45 | 0.40 |
| [0.5,0.6) | 58 | 0.55 | 0.93 |
| [0.7,0.8) | 83 | 0.75 | 0.99 |
| [0.9,1.0] | 263 | 0.97 | 1.00 |

Slightly under-confident around 0.5–0.6, otherwise well-ordered and usable as a
displayed win-probability with a light optional recalibration.

## Diagnostic readouts

- **Perspective flip sanity:** material `mean|Σ|=0.08`, live_sim `0.14`,
  old `2.09`. The old head is **not** anti-symmetric — scoring the same state from
  p1 vs p2 does not negate, so `/evaluate`'s `value → p1_win_prob` mapping is unsafe
  for p2 (and noisy for p1). Confirms the perspective concern from the inventory.
- **Terminal separation (≤2 turns to end):** material +0.40/−0.41,
  live_sim **+0.92/−0.94**, old **+1.30/+0.37** (loss still positive). Only the
  research scorers separate terminal wins from losses.
- **Monotonicity with material (Spearman):** live_sim 0.82 (tracks material),
  old 0.28 (largely decoupled from the HP differential).
- **Collapse/saturation:** fraction `|score|>0.9` — material 0.3%, live_sim 28.5%,
  **old 73.7%**. The old head is pinned near its rails.
- **Mean score (bias):** material +0.01 (unbiased), live_sim −0.07, **old +1.07**
  (heavy positive bias — the literal collapse).

## Verdict

- **`/evaluate` current-state scores are NOT trustworthy today.** The default
  `old_live_private` head is collapsed, ~chance on sign, worse-than-no-skill on
  Brier, heavily overconfident, and perspective-inconsistent. This directly
  explains the user's observation that live battle-state evaluations "looked poor."
- **`live_sim_value`** is the best-calibrated *state estimator* (Brier 0.066,
  AUC 0.987, clean terminal separation) and is a drop-in on the existing live
  feature path.
- **`material/HP`** is the most robust, perspective-exact, never-saturating
  baseline and remains the trusted branch-leaf scorer (consistent with prior branch
  audits where it won action selection 45% vs live_sim 15% vs old-value 0%).

See `live_eval_scoring_inventory.md` (Part A) for paths,
`action_impact_calibration_report.md` (Part F) for the action-selection
consequence, and `live_extension_sanity.md` (Part D) for the live-payload view.
