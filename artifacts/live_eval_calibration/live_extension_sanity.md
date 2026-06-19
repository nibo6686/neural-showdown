# Live Extension Sanity (Part D)

**Date:** 2026-06-18

## What live-eval logs exist

The only persisted server logs are:

- `artifacts/live_eval_server.log` — **186 bytes**, two access lines:
  `INFO: 127.0.0.1 - "POST /evaluate HTTP/1.1" 200 OK`. No request or response
  bodies.
- `artifacts/live_eval_server.err.log` — empty.

**There are no captured `/evaluate` request/response payloads**, so the specific
boards where the user felt the eval "looked bad" cannot be replayed directly. Two
responses: (1) explain the bad-looking scores from the calibration audit, which is
conclusive on its own; (2) add an opt-in logger so future live states are
captured for calibration (done below).

## Why the live battle-state eval looked bad (grounded in Part C)

The cause is not subtle and does not need the original boards. `/evaluate` scores
the current state with the **default `old_live_private` value head**, which the
1406-state calibration audit shows is **collapsed and overconfident**:

- It outputs a **positive** score for both winning **and** losing states
  (mean +1.31 vs +0.85), so after the `(value+1)/2` map it reports a
  **near-certain win for almost everything**: 1059 / 1406 states map to ≈0.99
  win-prob while the true win rate there is 0.555.
- Sign accuracy is **0.558** (≈ coin flip) and Brier **0.395** (worse than the
  no-skill 0.25). It cannot tell a won position from a lost one.
- It is **not perspective-anti-symmetric** (flip |Σ|=2.09), and `/evaluate` writes
  the current player's value straight into `p1_win_prob`, so a p2 user would see an
  inverted/garbled probability.

So the user's observation is expected: a typical mid-game board renders as ~90–100%
for the player regardless of whether the board is actually good or bad, and the
number barely moves with the action chosen.

**Error classification:** this is primarily a **scorer-weakness + calibration**
failure (a collapsed value head mapped through a naive linear-to-probability
transform), compounded by a **latent perspective bug** in the `value → p1_win_prob`
line. It is **not** a hidden-information/belief problem and **not** a UI
misinterpretation. The belief/feature path itself is fine — `material` and the
bounded `live_sim_value` head, fed the *same* live features, are well-calibrated.

## Illustrative board (from the calibration set, not the extension)

A representative `near_terminal`, `losing` state (side is behind, ≤2 turns from a
loss):

| Scorer | Score | Implied win-prob | Plausible? |
| --- | ---: | ---: | --- |
| material/HP | −0.41 | 0.30 | yes — losing |
| live_sim_value | −0.94 | 0.03 | yes — near-certain loss |
| old_live_private (`/evaluate`) | **+0.37** | **0.69** | **no — says winning while losing** |

This is the exact shape of "the eval looks wrong": the displayed number is high and
optimistic on a board that is actually lost.

## Fix surfaced for future live use (opt-in)

Two opt-in server additions (default behavior unchanged):

1. **Calibrated state eval.** Set `NEURAL_EVAL_STATE_SCORER=live_sim_value` and
   `/evaluate` adds a `state_eval` block scored by the bounded, calibrated head with
   correct p1/p2 perspective orientation:

   ```json
   "state_eval": {
     "scorer": "live_sim_value",
     "value": 0.148,
     "player_side": "p1",
     "player_win_prob": 0.574,
     "p1_win_prob": 0.574,
     "p2_win_prob": 0.426,
     "checkpoint_path": ".../gen9randombattle_live_sim_value_v1.pt"
   }
   ```

   The default `value` / `p1_win_prob` fields are preserved for comparison.

2. **Sanitized live-eval logging.** Set `NEURAL_EVAL_LOG_PATH=...jsonl` to append one
   record per `/evaluate`. It captures only scoring-relevant public fields (room id,
   player, log length, default value/p1_win_prob, `state_eval`, feature version,
   top action labels/scores, damage-engine status). It **does not** persist the
   private team or the `request` payload, so future live boards can be audited for
   calibration without leaking the user's hidden information.

   ```powershell
   $env:NEURAL_EVAL_LOG_PATH = ".\artifacts\live_eval_calibration\live_requests.jsonl"
   $env:NEURAL_EVAL_STATE_SCORER = "live_sim_value"
   .\scripts\run_windows.ps1 -Action live-eval -SimCoreMode native
   ```

   After a few real battles, run the calibration metrics over the captured
   `state_eval`/outcome pairs to confirm the live distribution matches the seeded-sim
   findings.
