# Rollout-Parity Batch 8 — Exact Sequential Multi-Hit Execution Traces

## Scope and result

This batch (Batch E in the state-provenance plan) adds a narrow, provenance-safe
exact execution-trace path for sequential multi-hit moves — Population Bomb,
Triple Axel (and Triple Kick-style ramps) — which use sequential accuracy
(stop-on-miss) and, for Triple Axel, a per-hit power ramp. They are **not**
ordinary fixed multi-hit moves. An exact rollout PASS requires a complete per-hit
execution trace supplied as Showdown-fixture provenance; an expected-hit
summary / distribution is never treated as an exact trace, and the trace is never
exposed as a model feature.

Deterministic harness after this batch:

- 59 deterministic cases (was 55)
- **51 PASS** (was 47)
- **0 FAIL**
- **8 explicit GAP** (unchanged)

This is rollout-parity only. `legal-action-v7` stays 552D / `956da3d2…1bf39d7`;
the batch-7 action features already summarize multi-hit risk and are unchanged.
Scope stays Gen 9 Random Battles. No PRNG simulator was added — this is
oracle-trace-driven exact replay parity.

## Exact sequential multi-hit trace contract

`trainer/src/neural/multihit_trace.py`:

- `validate_sequential_multihit_trace(trace)` requires: `move` id; ordered `hits`
  records (each with the correct `index` and a `hit` boolean; landed hits carry
  `damage`; ramp moves carry per-hit `base_power`); explicit `total_damage` and
  `hit_count`; and `provenance`. A distribution summary (`multihit_*`,
  `expected_hits`, `hit_chance`) is rejected with `summary_is_not_exact_trace`.
- `execute_sequential_multihit(trace, expected_move/source/target)` replays the
  trace **in order, stopping at the first miss** (`stop_on_miss`, default true),
  summing landed damage, counting landed hits, recording the ordered per-hit base
  powers, and flagging whether a miss occurred. It fails closed when the trace is
  invalid, the move/source/target disagrees with what is represented, or the
  replayed totals disagree with the trace's declared `total_damage` / `hit_count`.

`rollout_parity.py` gains a `sequential_multihit` phase handler that runs the
local replay and compares `hit_count`, `missed`, `final_hp`
(`starting_hp - total_damage`), and the Triple Axel `per_hit_power_ramp` against
the independently log-derived oracle values.

## New fixtures (all PASS vs real Showdown)

Built from deterministic fixed-seed Showdown logs (`multihitTrace` extracts the
per-hit damage sequence, hit count, miss flag, and ramp):

- `population_bomb_exact_trace` — Maushold Population Bomb vs Blissey: exact
  per-hit replay matches hit count and total damage.
- `population_bomb_stop_on_miss_trace` — fixed-seed miss: stop-on-miss honored.
- `triple_axel_exact_power_ramp_trace` — Weavile Triple Axel vs Snorlax: exact
  replay including the 20/40/60 base-power ramp.
- `triple_axel_stop_on_miss_trace` — fixed-seed miss: stop-on-miss honored.

The four original summary-only fixtures (`population_bomb_sequential_hits_gap`,
`population_bomb_initial_miss_stops_gap`, `triple_axel_power_ramp_gap`,
`triple_axel_initial_miss_stops_gap`) **remain explicit GAP**: they carry only an
expected/aggregate summary with no per-hit execution trace.

## Population Bomb / Triple Axel GAP status

GAP count is **unchanged (8)**. The four trace-backed fixtures are new PASS; the
four summary-only fixtures stay GAP. No GAP was closed by weakening correctness —
exact PASS requires a complete per-hit trace, and a summary is explicitly
refused.

## No-leakage behavior verified

- **Summaries are not traces.** `execute_sequential_multihit` rejects any
  distribution / expected-hit / hit-chance summary
  (`test_distribution_summary_is_rejected`).
- **No inference from hit chance.** The replay only sums explicit per-hit records;
  it never derives outcomes from accuracy or expected hits.
- **Fixture-only provenance.** The per-hit trace lives in the oracle fixture /
  transition provenance (`provenance: bundled_showdown_fixture`); it is not a
  `legal-action-v7` field and is never returned as a model-facing feature.
- **Fail closed.** Missing, incomplete, internally inconsistent, or
  move/source/target-mismatched traces fail closed (GAP), preserving 0 FAIL.
- **Stop-on-miss is exact.** A post-miss record is never counted
  (`test_stop_on_miss_is_honored`).

## Verification

- runtime preflight: `D:\Anaconda\envs\neuralgpu\python.exe`, Torch
  `2.5.1+cu121`, CUDA available `True`
- sim-core TypeScript build: PASS
- sim-core test suite: 35 PASS
- `test_state_provenance_no_leakage_contracts` (incl. multihit execution): 52 PASS
- `test_public_information_belief_contracts`: 49 PASS
- `test_rollout_parity_harness`: 18 PASS
- deterministic harness: 51 PASS / 0 FAIL / 8 GAP
- `python -m json.tool` on harness results: PASS
- `git diff --check`: clean (LF→CRLF warnings only)

## Remaining rollout GAPs (8)

1. Future Sight replacement damage without target-specific landing damage.
2. Doom Desire replacement damage without target-specific landing damage.
3. Magic Bounce reflection with incomplete routing provenance.
4. Good as Gold blocking with an unrevealed/unknown ability.
5–8. Population Bomb / Triple Axel sequential execution when only an expected-hit
   summary (no per-hit trace) is available.

## What did NOT change

No training, dataset materialization, checkpoint promotion, checkpoint file,
live default, live bot behavior, action/state schema, or `legal-action-v7`
fingerprint; no live-extraction rewrite; no NatDex/old-gen mechanics; no broad
PRNG simulation. Both the rollout-parity and overall diagnostic training gates
remain **closed**.
