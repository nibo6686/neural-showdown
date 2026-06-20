# Mechanics Repair Batch 1: Fixed-Damage, Multi-Hit, Dynamic Accuracy

## Scope

First targeted repair of the comprehensive Gen 9 Random Battles mechanics audit
(`gen9randbats_mechanics_completeness_audit.md`). Only three FAIL buckets were
addressed: fixed-damage moves, multi-hit moves, and dynamic-accuracy moves. The
principle is unchanged: every material move-impact mechanic must be either PASS or
explicitly INEXACT/fail-closed — never wrong-exact. The diagnostic
`resolve_action_impact` path is the only impact surface touched; live defaults
(`live-private-belief-v2` / `legal-action-v3`) are untouched.

## Decision rule applied

- **Route to oracle (PASS)** only where `@smogon/calc` resolves the exact value
  from already-represented state.
- **Fail closed (INEXACT)** — return the unavailable impact (`available=False`,
  `method=unavailable`, which the feature builder encodes as `impact_unknown=1` /
  `impact_method_unavailable=1`) — where the exact value depends on context the
  oracle does not resolve, rather than emit a wrong-exact value.

## Grounding probe

`@smogon/calc` was probed directly (Annihilape vs Cresselia) to decide route vs.
fail-close per move:

| Move | Oracle result | Decision |
| --- | --- | --- |
| Seismic Toss | fixed level damage, 26.1% (honors immunity) | route → PASS |
| Night Shade | fixed level damage, 26.1% | route → PASS |
| Super Fang / Ruination / Endeavor | returns 0% (HP-dependent unresolved) | fail closed |
| Mirror Coat | returns 0% (damage-taken unresolved) | fail closed |
| Bullet Seed / Rock Blast / … | per-hit rolls flattened (~5.6% per hit vs ~16.8% 3-hit total) | fail closed |
| Blizzard / Thunder | damage identical regardless of weather; accuracy from static metadata | weather-aware accuracy |

## Fixed-damage result

- **Seismic Toss, Night Shade → PASS.** Added to `FIXED_DAMAGE_ORACLE_MOVE_IDS`;
  excluded from the base-power-0 "non-damaging" short-circuit and routed to the
  oracle, which returns the exact level-based damage and zeroes it on type
  immunity. If the oracle ever falls back (non-`smogon_calc`), they fail closed.
- **Super Fang, Ruination, Endeavor (target-HP), Mirror Coat (damage-taken) →
  INEXACT.** `FIXED_DAMAGE_FAIL_CLOSED_MOVE_IDS` fail closed before the oracle
  (`fallback_reason=fixed_damage_target_context_unresolved`,
  `dynamic_dependency=target_hp` / `damage_taken`). Counter and Metal Burst are
  included for completeness though not in the current randbats pool.
- These six moves are also now classified as `damage` (not `unknown`) by
  `classify_action_category`, so the fail-closed ones correctly surface
  `impact_unknown=1` instead of looking like 0-damage status moves.

## Multi-hit result

- **Bullet Seed, Dragon Darts, Dual Wingbeat, Icicle Spear, Population Bomb, Rock
  Blast, Scale Shot, Surging Strikes, Tachyon Cutter, Tail Slap, Triple Axel →
  INEXACT.** `MULTI_HIT_MOVE_IDS` fail closed
  (`fallback_reason=multihit_total_unrepresented`, `dynamic_dependency=multihit`).
  The oracle reports per-hit rolls (flattened), which understates the multi-hit
  total ~2–10× and cannot express the 2–5 hit distribution / Loaded Dice / Skill
  Link in the single expected/min/max fields. Fail-closed is correct rather than
  wrong-exact. (A future batch could provide an exact summed total for
  fixed-hit-count moves; not attempted here.)

## Dynamic accuracy result

- **Blizzard, Thunder, Hurricane, Bleakwind Storm.** Hit chance is now computed
  from the protocol-observable `tactical_state.weather`:
  - Blizzard: 1.0 in snow/hail, else base (0.70).
  - Thunder / Hurricane / Bleakwind Storm: 1.0 in rain, 0.50 in harsh sun, else
    base (0.70).
  - No tactical state supplied → weather context unsupported → `accuracy_known=False`
    (fails closed; does not claim the clear-weather value as exact).
- The accuracy mechanic is repaired, so a low-accuracy move is no longer
  represented as equally reliable across weather. These four moves **remain FAIL**
  in the completeness audit because their secondary status/stat effect is still
  omitted from next-state impact (deferred to a later batch).

## Tests

New `trainer/tests/test_mechanics_repair_batch_1.py` (10 tests, all pass):
fixed-damage routed-to-oracle (Night Shade, Seismic Toss); ordinary control
(Close Combat) unaffected; target-HP and counter fixed-damage fail closed;
fail-closed fixed-damage surfaces `impact_unknown=1` in the v6 vector; multi-hit
moves fail closed and surface `impact_unknown=1`; Blizzard perfect-in-snow /
base-in-clear; Thunder rain vs sun; unsupported-weather accuracy fail-closed.

Regression: `test_action_features_v4/v5/v6`, `test_damage_engine` (41 passed);
`test_mechanics_audit`, `test_action_ranker`, `test_rollout_regression`
(22 passed). `git diff --check` clean.

## Schema and gate

No feature name, order, or dimension changed. v6 remains 331D and the v5 prefix is
unchanged — only move-id-keyed routing in `resolve_action_impact` and
`classify_action_category` (plus the new id sets in `action_features.py`) changed,
correcting feature **values** for the repaired moves. Existing v5/v6
data/checkpoints are still mechanically stale and must not be used.

Completeness audit: **121 PASS / 176 FAIL / 53 INEXACT → 123 PASS / 159 FAIL /
68 INEXACT**. The gate remains **closed**: the secondary/status, conditional/
delayed, dynamic type/STAB, and guaranteed-crit FAIL buckets remain. No training,
no diagnostic_300/1000 rematerialization, no checkpoint promotion, and no live
default change occurred.

## Next recommendation

Batch 2: the secondary status/stat/volatile next-state bucket (the largest
remaining FAIL set, ~121 moves) — including the four weather-accuracy moves that
remain FAIL only on their secondary effect — represented as next-state status/stat
deltas where deterministic, or fail-closed where probabilistic.
