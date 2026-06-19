# Trusted State-Scorer Recommendation (Part E)

**Date:** 2026-06-18

## Decision

Adopt a **role-split**, not a single scorer — the audit shows the best *estimator*
and the best *action selector* are different models:

| Job | Trusted scorer | Why |
| --- | --- | --- |
| 1. Current battle-state evaluation (`/evaluate` display) | **live_sim_value (bounded), opt-in** | best calibration: Brier 0.066, AUC 0.987, sign 0.936, clean terminal separation |
| 2. Action-impact / branch-leaf scoring | **material/HP** | best one-step action-impact (45% branch winrate); perspective-exact; never saturates |
| 3. Branch-search leaf scoring (research) | **material/HP** | unchanged; remains the default research scorer |
| 4. Future public-evidence belief calibration | **material/HP** foundation (see Part G) | trusted, cheap, perspective-exact leaf during belief work |

This is **option 2 + option 5 from the brief** (calibrate via a better-calibrated
bounded head for display, expose it with metadata), while **not** changing the
default action recommender (option 1 retained for the live default). No large
rewrite, no retrain — the bounded `live_sim_value_v1` head already exists and is
well-calibrated; the audit just established that it should be the one shown.

## What was implemented

> **Update (2026-06-18, user-authorized):** the user directed the live server to
> "use the best option available" and not retain the collapsed score in the UI. The
> calibrated head was therefore **promoted to the `/evaluate` default**, overriding the
> earlier "keep opt-in until live confirmation" stance.

In `trainer/src/neural/live_eval_server.py`:

1. **Calibrated state eval is now the default.** `/evaluate` computes the displayed
   `value` / `p1_win_prob` / `p2_win_prob` from the bounded `live_sim_value` head with
   **correct p1/p2 perspective orientation** (fixes the latent bug where the current
   player's value was written straight into `p1_win_prob`). Because the overlay reads
   `p1_win_prob` directly, the on-screen number is now the calibrated one with no
   overlay change. The response adds `state_scorer`, a `state_eval` block, and retains
   the old head's reading as `legacy_value` / `legacy_p1_win_prob` for diagnostics.
   - `NEURAL_EVAL_STATE_SCORER=old_live_private` (or `legacy`) forces the old behavior.
   - If the bounded checkpoint is missing/unloadable, `/evaluate` falls back to the
     legacy mapping automatically (never breaks).
2. **Action recommendation is unchanged.** `recommend_actions` still receives the old
   value head (`current_value=legacy_value`, `value_model=model`); only the displayed
   current-state win-prob changed.
3. **Sanitized live-eval logging.** `NEURAL_EVAL_LOG_PATH=...jsonl` appends one record
   per `/evaluate` with scoring-relevant public fields only (no private team/request),
   so future live boards can be audited for calibration without leaking hidden info.

All covered by tests (`trainer/tests/test_live_eval_calibration.py`).

## Explicitly NOT done (per scope)

- Did **not** change the live recommender default or weights.
- Did **not** make `live_sim_value` the *default* `/evaluate` value (kept opt-in until
  confirmed on real live data via the new logging).
- Did **not** retrain or overwrite any checkpoint.
- Did **not** delete or modify the old value head (kept as labeled diagnostic).

## Why not just promote live_sim_value as the default now

It is clearly better than the collapsed default, but: (a) the brief says do not change
live defaults yet; (b) the calibration evidence is on seeded heuristic/random sim
games — the new sanitized logging should confirm the same calibration on real ladder
boards before flipping the default. The opt-in path lets the user A/B it immediately.

## Suggested next confirmation step

Run a few real battles with `NEURAL_EVAL_STATE_SCORER=live_sim_value` and
`NEURAL_EVAL_LOG_PATH` set, then re-run the calibration metrics over the captured
`state_eval` vs eventual outcome. If live calibration matches the seeded findings,
promote `live_sim_value` (perspective-correct) to the `/evaluate` default.
