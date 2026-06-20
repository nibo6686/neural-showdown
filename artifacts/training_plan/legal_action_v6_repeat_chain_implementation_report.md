# legal-action-v6 Repeat-Chain Implementation Report

## Outcome

`legal-action-v6` is implemented as an append-only extension of the unchanged
318D `legal-action-v5` prefix. It adds 13 repeat-chain context/provenance fields,
for a total dimension of **331D**.

- Ordered-name fingerprint:
  `ac8fb3d36e29a3a2ed6795f790c34d0a6f1330f6d6ef2262ab4722c58373f049`
- Live defaults remain `live-private-belief-v2` / `legal-action-v3`.
- No checkpoint was promoted and no training ran.

## Appended Fields

1. `repeat_chain_is_rollout`
2. `repeat_chain_is_fury_cutter`
3. `repeat_chain_count_norm`
4. `repeat_chain_multiplier_norm`
5. `repeat_chain_state_known`
6. `repeat_chain_state_exact`
7. `repeat_chain_provenance_protocol_complete`
8. `repeat_chain_provenance_inferred_lower_bound`
9. `repeat_chain_provenance_unknown`
10. `repeat_chain_reset_observed`
11. `rollout_defense_curl_active`
12. `rollout_defense_curl_known`
13. `rollout_forced_continuation_active`

The global known/exact/provenance fields also establish whether forced
continuation is known, avoiding another redundant field.

## Mechanics Path

Protocol-complete tactical reconstruction tracks consecutive successful
Rollout/Fury Cutter uses and resets on miss, failure, immunity, protection,
switch, faint, or an intervening move. Rollout additionally retains Defense
Curl and forced-continuation state.

The v6 impact path passes exact prior-success count to sim-core:

- Rollout: `30 × 2^count`, capped at the fifth-turn multiplier, doubled by
  Defense Curl.
- Fury Cutter: `40 × 2^count`, capped at 160 BP.

If repeat-chain state is unavailable or non-exact, v6 impact fails closed with
`repeat_chain_state_unknown`. Unknown is never treated as an exact zero count.
Non-repeat moves preserve the exact v5 prefix and receive a zeroed v6 suffix.

The mechanics audit now reports **12 PASS / 0 FAIL / 0 NEEDS_VERIFICATION**.

## Explicit Tooling Selection

The feature materializer accepts:

```powershell
--action-feature-version legal-action-v6
```

v5 remains the default. Diagnostic dataset/config validation accepts v6 only
with its 331D schema and fingerprint. Strict checkpoint validation rejects a
318D `legal-action-v5` checkpoint when v6 is requested.

## Tiny Diagnostic Materialization

Only one manifest battle was materialized:

- Output:
  `artifacts/training_plan/datasets/tiny_v7_v6_repeat_chain/`
- Battles: 1 valid / 0 failed
- v7 states: 52 × 3208D
- v6 candidates: 337 × 331D
- Chosen-action match rate: 100%
- Validation: PASS
- Runtime: approximately 5.7 seconds on the final rerun
- Training launched: no

The controlled mechanics audit supplies the Rollout/Fury Cutter counterfactual;
the selected tiny replay validates the real replay materialization/schema path.

## Compatibility and Gate

v5 remains exactly 318D with unchanged ordered fields. Existing v5
datasets/checkpoints remain mechanically stale for all corrected dynamic
mechanics and cannot represent repeat-chain provenance.

The training gate stays closed. A larger v7/v6 rematerialization and any
training require separate approval after reviewing the tiny artifact and stale
v5 disposition.
