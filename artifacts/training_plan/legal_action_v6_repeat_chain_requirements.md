# legal-action-v6 Repeat-Chain Requirements

Status: **approved and implemented** as an append-only 331D schema. See
`legal_action_v6_repeat_chain_implementation_report.md` for the frozen field
list, fingerprint, tests, and tiny materialization result.

## Why v5 Is Insufficient

Rollout and Fury Cutter depend on Showdown per-Pokémon volatile state for
consecutive successful uses. The existing v7 reconstruction has generic
same-move history, but that is not equivalent to the live volatile:

- misses, immunity, Protect-like failures, switching, and intervening moves can
  reset or prevent chain advancement;
- Rollout has Defense Curl interaction and forced continuation semantics;
- Fury Cutter and Rollout have different caps and progression rules;
- a truncated replay/live history may provide only a lower bound, not an exact
  chain count.

v5 can store a resolved damage value, but it cannot tell the ranker whether that
value came from exact Showdown-equivalent state, an inferred lower bound, or an
unknown chain. Silently correcting the value would therefore change semantics
without exposing provenance.

## Proposed v6 Context and Provenance

Add explicit action context after the unchanged v5 prefix:

- repeat-chain move identity/match flag;
- exact successful-chain count or normalized current multiplier;
- chain-count-known flag;
- provenance enum: protocol-complete, reconstructed-exact, inferred-lower-bound,
  or unknown;
- reset/interruption observed flag;
- Rollout Defense Curl active/known flags;
- Rollout forced-continuation active/known flags.

The exact field set should be frozen only after verifying Showdown's volatile
lifetimes and sim-core input contract. Do not overload generic
`move_times_used`.

## Unknown-State Behavior

- v5 should continue to classify Rollout/Fury Cutter impact as mechanically
  inexact and must not claim base-power damage as exact.
- v6 should preserve candidates but mark chain context unknown; resolved impact
  should fail closed or use an explicitly inexact/lower-bound method.
- Unknown must never be encoded as an exact zero-chain count.
- Live and offline reconstruction must produce the same provenance for the same
  complete packet/history.

## Tests Required Before v6 Training

- first, second, and capped consecutive successful hits for each move;
- miss, immunity, Protect-like failure, intervening move, switch-out, faint, and
  battle-history truncation reset cases;
- Rollout with and without Defense Curl;
- Rollout forced-continuation state;
- exact versus inferred-lower-bound versus unknown provenance;
- live shadow and offline/materialization feature parity;
- schema dimension, ordered-name fingerprint, v5-prefix integrity, checkpoint
  rejection, and fail-closed tests.

## Gate Decision

The narrow schema and focused tests are approved. Full rematerialization and
training remain closed pending separate approval. Do not rematerialize full v5
data as a substitute: existing v5 datasets/checkpoints are already stale for
repaired mechanics and still cannot represent repeat-chain provenance.
