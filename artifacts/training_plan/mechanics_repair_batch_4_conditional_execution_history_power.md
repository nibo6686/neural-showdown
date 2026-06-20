# Mechanics Repair Batch 4: Conditional Execution/Success and Turn/History Power

## Scope

Fourth targeted repair of the comprehensive Gen 9 Random Battles mechanics audit.
This batch handles two remaining wrong-exact buckets: conditional move
execution/success (8 moves) plus conditional-utility moves (3), and
turn/history-conditional power (7) — 18 moves total. The rule: repair to PASS when
the reconstructed state is enough for exact Showdown behavior; otherwise mark
INEXACT/fail-closed. Do not encode "deals this damage" when the move may fail or
its power may double. Prefer INEXACT. No live defaults, training, rematerialization,
or checkpoint promotion. v6 stays 331D; no v6 schema field was added.

## The wrong-exact bugs

These moves emitted exact on-hit damage even though they can fail or change power
based on information the impact does not have:

- **Conditional execution/success** — Fake Out / First Impression (only the
  first active turn), Sucker Punch / Thunderclap / Focus Punch (depend on the
  opponent's same-turn action), Double Shock / Hyperspace Fury (user form +
  self-effect), Poltergeist (target must hold an item).
- **Turn/history power** — Payback / Avalanche / Lash Out (same-turn order / hit /
  stat-drop), Stomping Tantrum / Temper Flare (doubled if the user's previous
  move failed), Fusion Bolt / Fusion Flare (doubled by a partner's same-turn
  fusion move).
- **Conditional utility** — Brick Break / Psychic Fangs (break/bypass screens),
  Pollen Puff (damages a foe, heals an ally).

## INEXACT / fail-closed fallbacks (13)

`resolve_action_impact` now fails closed (`available=False` → `impact_unknown=1`)
for these, with a per-move `dynamic_dependency` label
(`CONDITIONAL_FAIL_CLOSED_MOVE_DEPENDENCY`):

- Opponent same-turn action (`opponent_action`): Sucker Punch, Thunderclap, Focus
  Punch — success depends on the opponent's hidden selected move.
- First active turn (`first_active_turn`): Fake Out, First Impression — fail after
  the first turn out.
- User form / self-effect (`user_type_and_self_effect`, `user_form_and_self_effect`):
  Double Shock (needs Electric typing, loses it after), Hyperspace Fury
  (Hoopa-Unbound only, self Def drop).
- Target item presence (`target_item_presence`): Poltergeist — fails if the
  target has no item.
- Same-turn order/hit/stat (`same_turn_order`, `same_turn_hit`,
  `same_turn_stat_drop`): Payback, Avalanche, Lash Out — power doubling depends on
  within-turn information not available at decision time.
- Prior-move-failure (`prior_move_failure`): Stomping Tantrum, Temper Flare —
  doubling depends on whether the user's previous move failed; that history is
  not plumbed to the oracle as a base-power override, so base power would be
  wrong-exact when it should double → fail closed.

## Exact fixes (PASS, 3)

- **Fusion Bolt, Fusion Flare** — the partner-fusion same-turn doubling requires a
  second active Pokémon, which cannot happen in singles, so base power is exact.
  These flow to the oracle unchanged.
- **Pollen Puff** — in singles the only legal target is the foe, so it always
  deals its exact damage (the ally-heal branch cannot occur).

## INEXACT via coarse field flag (2)

- **Brick Break, Psychic Fangs** — their damage is exact: probed against a target
  with Reflect up, the calc correctly does **not** reduce them (screen-bypass),
  while an ordinary move (Close Combat) is halved. So the damage stays. Their
  remaining effect is the conditional removal of the target's screens, now
  coarsely flagged via the existing `next_field_or_side_change` field
  (`SCREEN_BREAK_ON_HIT_MOVE_IDS`) — INEXACT, not wrong-exact.

## Result

- FAIL **27 → 9**; PASS **131 → 134**; INEXACT **192 → 207**.
- Conditional execution/success: 8 moves leave FAIL → all INEXACT.
- Turn/history power: 7 moves leave FAIL → Fusion Bolt/Flare PASS, the other 5
  INEXACT.
- Conditional utility: 3 moves leave FAIL → Pollen Puff PASS, Brick Break /
  Psychic Fangs INEXACT.

## v6 changed? / v7 proposal

No v6 schema field was added — v6 remains 331D and the v5 prefix is unchanged.
Only impact **values** changed (new fail-closes; `next_field_or_side_change` set
for the two screen-break moves) plus the new move-id sets and the audit
reclassification. The fixes that would let some of these reach PASS need typed v7
fields and are **documented, not implemented**:

- a **conditional-execution flag** (e.g. `impact_may_fail` + a condition class:
  opponent-action / first-turn / target-item) so Fake Out / Sucker Punch / etc.
  could carry their conditional damage instead of failing closed; and
- **turn-order / prior-move-failure** inputs plumbed to the oracle as a base-power
  override (mirroring Rage Fist / Last Respects) so Payback / Avalanche / Lash Out /
  Stomping Tantrum / Temper Flare could be exact when the reconstructed history
  supports it.

## Tests

New `trainer/tests/test_mechanics_repair_batch_4.py` (8 tests, all pass):
first-turn moves fail closed (Fake Out, First Impression), opponent-action moves
fail closed (Sucker Punch, Thunderclap, Focus Punch), Poltergeist target-item
dependency, same-turn/prior-failure power fail closed (Payback, Avalanche, Lash
Out, Stomping Tantrum, Temper Flare), Fusion Bolt exact in singles, Pollen Puff
damages in singles, Brick Break exact damage + field-change flag, ordinary Surf
unaffected.

Regression: action-features v4/v5/v6, batch-1/2/3, damage_engine, action_ranker,
mechanics_audit (93 passed); generator audit test (10 passed). `git diff --check`
clean. (No sim-core change this batch; the jest suite is unaffected.)

## Schema and gate

No action feature name, order, or dimension changed; v6 remains 331D. Existing
v5/v6 data/checkpoints remain mechanically stale.

The gate remains **closed**: 9 wrong-exact FAILs remain — callback-dependent
damage/type (Beat Up, Photon Geyser), guaranteed-crit metadata (Flower Trick,
Wicked Blow), special type-effectiveness (Freeze-Dry), random base power (Fickle
Beam), terrain-dependent priority (Grassy Glide), target item removal (Knock Off),
and berry consumption (Bug Bite). No training, no diagnostic_300/1000
rematerialization, no checkpoint promotion, and no live-default change occurred.

## Next recommendation

Batch 5 (final cleanup of the 9): guaranteed crit (Flower Trick, Wicked Blow) —
route through the calc's crit option for exact damage → PASS; Freeze-Dry — special
effectiveness vs Water, fixable via a small effectiveness override → PASS or
INEXACT; Grassy Glide — terrain-dependent priority, set from known terrain → PASS;
Fickle Beam (random power), Knock Off (item removal) and Bug Bite (berry) →
coarse-flag/INEXACT; Beat Up / Photon Geyser (callback damage/type) → verify
against the oracle, else INEXACT. Reaching zero wrong-exact FAIL would let the
mechanics gate's "no wrong-exact" criterion flip, after which the broader training
readiness review (value-label quality, larger datasets) can be revisited — still
separately approval-gated.
