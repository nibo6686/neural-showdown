# Mechanics Repair Batch 2: Secondary / Status / Stat / Volatile Next-State

## Scope

Second targeted repair of the comprehensive Gen 9 Random Battles mechanics audit.
This batch addresses the largest remaining FAIL group: secondary, primary status,
volatile, and stat next-state effects. The principle is unchanged: the goal is
zero wrong-exact impact, not a perfect model of every effect. Where v6 cannot
represent an effect exactly, the move is marked INEXACT (coarse annotation), not
PASS. Only the diagnostic impact/feature surface is touched; live defaults
(`live-private-belief-v2` / `legal-action-v3`) are untouched.

## The wrong-exact bug

For a damaging move with a secondary effect (e.g. Thunderbolt's 10% paralysis,
Crunch's 20% Defense drop, Iron Head's 30% flinch), and for primary
status/volatile moves (Will-O-Wisp, Thunder Wave, Taunt, Leech Seed, trapping),
the v6 next-state change flags were left at 0. A 0 in `next_opp_status_change`
reads as "this action causes no opponent status change", which is mechanically
wrong. The audit counted 120 such FAILs:

- 86 damaging moves with a material secondary status/stat/volatile,
- 22 moves with a deterministic target status/volatile,
- 12 non-damaging status transitions.

## Repair

A coarse, metadata-derived presence detector (`move_next_state_effects` in
`action_side_effects.py`) parses the bundled `moves.ts` once and reports four
booleans per move:

- `opp_status_or_volatile` — the foe gets a status/volatile (incl. callback
  secondaries such as Dire Claw / Tri Attack, detected via the secondary's effect
  callback), or a trapping volatile (Magma Storm / Whirlpool).
- `opp_stat_change` — the foe gets a secondary stat change (Crunch, Earth Power).
- `own_status_or_volatile` — the user gets a status/volatile (Substitute, Magnet
  Rise, Destiny Bond, No Retreat, Protect).
- `own_stat_change` — the user gets a secondary stat change (Meteor Mash, Charge
  Beam, Fiery Dance).

Self-vs-target placement uses the move's `target` field for primary effects and
nested `self: {...}` separation inside secondary blocks. These booleans are
OR-combined into the **existing** v6 next-state change flags
(`next_own_stat_change`, `next_opp_stat_change`, `next_own_status_change`,
`next_opp_status_change`) in `slice6_resolved_impact_feature_vector`. The
guaranteed self/primary stat deltas already supplied by `move_stat_deltas`
(Close Combat, Draco Meteor) are unchanged.

## Result

- FAIL **159 → 39**; PASS **123** (unchanged); INEXACT **68 → 188**.
- All 120 secondary/status/volatile FAILs become **INEXACT**: the effect is now
  honestly flagged as present, but the exact status type (par vs brn vs slp),
  chance (10% vs 100%), and magnitude are not represented, so they are coarse
  annotations, not PASS.
- The four weather-accuracy moves (Blizzard, Thunder, Hurricane, Bleakwind Storm)
  now leave FAIL on this same basis: batch 1 made their accuracy honest, batch 2
  flags their omitted secondary.

## Repaired vs INEXACT (and v7-deferred)

- **Coarsely repaired → INEXACT:** damaging secondaries (status/stat/volatile),
  primary target status (Will-O-Wisp, Thunder Wave, Toxic, Spore, Glare, ...),
  target volatiles (Taunt, Encore, Disable, Yawn, Leech Seed, trapping), and self
  volatiles (Substitute, Magnet Rise, Destiny Bond, No Retreat, Protect).
- **v7-deferred (flagged only as non-damaging, INEXACT):** item-swap (Trick,
  Switcheroo), copy (Transform), random-call (Sleep Talk), and HP/team transitions
  (Pain Split, Healing Wish, Revival Blessing) have no v6 field for their effect.
  They carry `action_non_damaging=1` plus the move identity, so they are not
  wrong-exact, but a faithful representation needs **typed v7 effect fields**
  (status type, secondary chance, item delta, volatile id). No v6/v7 field was
  added in this batch.

## v7 proposal (documented, not implemented)

To raise these moves from INEXACT toward PASS, a future `legal-action-v7` would
add typed, append-only fields after the frozen v6 prefix: secondary status type
+ chance, target/self volatile id + duration class, secondary stat id + stage,
and an item-transition flag. This is recorded here only; no schema change was made.

## Tests

New `trainer/tests/test_mechanics_repair_batch_2.py` (10 tests, all pass):
status secondary (Thunderbolt), stat-drop secondary (Crunch), self-boost secondary
(Meteor Mash), flinch volatile (Iron Head), primary status + non-damaging
(Will-O-Wisp), weather-accuracy move now flagged (Blizzard), ordinary moves
unaffected (Surf/Earthquake/Close Combat/Dragon Pulse), v7-deferred coarse flag
(Trick). Two pool-wide consistency tests assert every batch-2 INEXACT move carries
an honest coarse signal and every damaging-secondary move sets a next-state change
flag (no INEXACT claim without a backing feature).

Regression: `test_action_features_v4/v5/v6`, `test_mechanics_repair_batch_1`,
`test_action_ranker`, `test_mechanics_audit` (62 passed); generator audit test
(8 passed). `git diff --check` clean.

## Schema and gate

No feature name, order, or dimension changed. v6 remains 331D and the v5 prefix is
unchanged — only feature **values** for secondary/status/volatile moves changed
(0 → 1 on the relevant next-state flags), plus the move-id-independent detector and
the audit generator reclassification. Existing v5/v6 data/checkpoints remain
mechanically stale and must not be used.

The gate remains **closed**: 39 wrong-exact FAILs remain (dynamic type/STAB,
conditional move-success/execution, turn/history power, charge/delay timing,
guaranteed-crit metadata, special type-effectiveness, terrain-priority, random
power, target item removal/berry). No training, no diagnostic_300/1000
rematerialization, no checkpoint promotion, and no live-default change occurred.

## Next recommendation

Batch 3: the remaining 39 FAILs split into damage-correctness groups
(dynamic type/STAB 8, turn/history power 7, charge/delay 4, random power 1,
special effectiveness 1, guaranteed crit 2) and execution/conditional groups
(move-success 8, conditional 3, terrain-priority 1, item removal/berry 2).
Start with dynamic type/STAB and charge/delay (route exact where the oracle
supports it, else fail closed) since those most directly distort damage ranking.
