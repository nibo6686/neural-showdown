# v5 Dynamic Mechanics Repair and Versioning Plan

## Decision Rule

- **v5-safe:** correct values in existing damage, next-state, or stat-delta fields
  without adding/reordering names.
- **v6-required:** the model needs a new context/provenance/uncertainty signal
  that existing fields cannot express honestly.
- **fail closed:** required state is unknown and treating it as zero/base power
  would claim false precision.

## Repair Matrix

| Priority | Failed mechanic | Showdown dependency | Current failure | Repair approach | Version | Tests | Old v5 status |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | Last Respects | `side.totalFainted` | Static 50 BP; count ignored | Pass known own faint count to sim-core; override BP to `50 + 50×count`; fail closed on incomplete history | **v5-safe — fixed** | 0 vs 3 fainted; live tactical reconstruction; unknown history | Stale |
| 1 | Stored Power / Power Trip | Current positive user boost stages | v7 retains boosts but damage payload dropped them | Merge known tactical boosts into attacker payload; fail closed when boost stages are unknown | **v5-safe — fixed** | direct and live-like boosts; unknown stages | Stale |
| 1 | Curse Ghost/non-Ghost | Current user typing | Static parsed non-Ghost stat deltas used for both forms | Condition existing stat-delta fields on current type; Ghost uses existing own-HP and opponent-status-change fields; fail closed if type unknown | **v5-safe — fixed** | Ghost vs non-Ghost vectors and impact | Stale |
| 2 | Reversal / Flail | Current/max HP | Static metadata BP=0 was misclassified as non-damaging before oracle | Route known variable-power damaging moves to sim-core; fail closed if HP or oracle result is unavailable | **v5-safe — fixed** | High/low HP; unknown HP; fixed-power control | Stale |
| 2 | Gyro Ball / Electro Ball | Both current Speed values/stages | BP=0 shortcut bypassed oracle | Route to sim-core with exact/inferred stats and known tactical boosts; retain exact-stat provenance; fail closed if context/oracle is unavailable | **v5-safe — fixed** | Both speed-ratio directions; exact-stat inputs | Stale |
| 2 | Grass Knot / Low Kick / Heavy Slam / Heat Crash | Canonical species weights and weight ratio | BP=0 shortcut bypassed oracle | Route known species/formes to sim-core; use canonical weights; fail closed for missing species or oracle failure | **v5-safe — fixed** | Equal-bulk light/heavy targets; target-weight and user/target-ratio directions | Stale |
| 3 | Rollout / Fury Cutter | Exact consecutive successful-use volatile state, interruption/reset semantics | Same-move chain is not equivalent; base damage is treated as exact | Track Showdown-equivalent per-Pokémon chain state and its provenance. Until then, fail closed rather than use base damage | **v6 recommended** | success/miss/switch/reset/Defense Curl sequences; unknown-history cases | Stale/unreliable |

## Why Rollout/Fury Cutter Should Be v6

Existing v5 impact fields can hold corrected damage, but the model cannot see
whether the value came from an exact active volatile chain, an inferred lower
bound, or unknown history. The chain also has reset and success semantics not
captured by the generic same-move count. Add explicit exactness/provenance (and,
if useful, normalized chain multiplier) in a proposed `legal-action-v6` rather
than silently changing v5 again.

## Repairs Implemented

The first batch implemented Last Respects, live Stored Power/Power Trip boost
scaling, and type-aware Curse. The second batch routes Reversal/Flail and all
listed speed/weight variable-power moves around the zero-metadata-BP shortcut
and into the existing Showdown/sim-core oracle. Unknown required state and
oracle failures fail closed for these repaired zero-metadata moves.

Weather Ball/Terrain Pulse now pass a grounded-versus-airborne field check.
Body Press/Foul Play pass exact-stat and live boost-source counterfactuals.
The mechanics audit is now **11 PASS / 1 FAIL / 0 NEEDS_VERIFICATION**.

No feature name, order, or dimension changed. v5 remains 318D.

## Training and Data Decision

Existing v5 datasets/checkpoints are stale for Rage Fist and every repaired
mechanic because their resolved-impact values were generated before these
corrections. Do not train or promote. Rollout/Fury Cutter remain mechanically
unreliable in v5 and require the explicit v6 context/provenance design in
`legal_action_v6_repeat_chain_requirements.md`. After that design is approved,
run only a tiny diagnostic rematerialization before considering a larger rebuild.
