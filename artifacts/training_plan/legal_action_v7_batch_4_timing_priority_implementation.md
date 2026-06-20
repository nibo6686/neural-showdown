# legal-action-v7 Batch 4: Typed Timing and Priority Implementation

Appends typed priority, charge, recharge, lock, and delayed-damage fields after
the frozen 388D batch-3 prefix. No training, materialization, checkpoint
promotion, or live-default change was performed.

## Schema

- Added `SLICE11_TIMING_PRIORITY_FEATURE_NAMES` with 18 fields.
- `legal-action-v7` is now **406D**.
- Ordered-name fingerprint:
  `bdf2439df649fcc0f1433482c8dc7a1ad7389b40be73c39884c27b45b81fb935`.
- The first 388 names and values remain byte-identical to batch 3; fingerprint:
  `d3f342710b001eded43f1ccee8228ce42d1fe616fb6f043593a3e8c3893cc91d`.
- The 331D v6, 361D batch-1, and 375D batch-2 prefixes remain unchanged.

## Fields

- `effect_base_priority_norm`
- `effect_effective_priority_norm`
- `effect_priority_condition_known`
- `effect_priority_boosted_by_terrain`
- `effect_priority_boosted_by_ability`
- `effect_priority_blocked`
- `effect_priority_conditional`
- `effect_requires_charge_turn`
- `effect_charges_this_turn`
- `effect_attacks_this_turn`
- `effect_charge_skipped_by_weather`
- `effect_charge_skipped_by_item`
- `effect_user_must_recharge_next_turn`
- `effect_user_locked_into_move`
- `effect_delayed_future_damage`
- `effect_delayed_damage_turns_norm`
- `effect_timing_unknown`
- `effect_timing_other`

Priority is signed and normalized by `/7`. Delayed turns are normalized by `/3`;
Future Sight / Doom Desire therefore encode two turns as `2/3`.

## Oracle and state resolution

Static move priority, flags, category, type, recharge, locked-move, charge, and
future-move semantics come from bundled Showdown `moves.ts`. Future-move delay is
grounded in Showdown's `futuremove` condition. Dynamic resolution uses current
reconstructed weather, terrain, item, HP, types, ability, and volatile state.

- Grassy Glide gains +1 only in Grassy Terrain when the user is provably
  grounded. Unknown grounding is conditional, not assumed.
- Known ability modifiers are represented: Prankster status +1, Triage healing
  +3, and Gale Wings Flying +1 at full HP.
- Psychic Terrain priority blocking is marked when the target is provably
  grounded; unknown grounding remains conditional.
- Solar Beam / Solar Blade attack immediately in sun or with Power Herb.
- Other charge moves attack immediately with Power Herb; otherwise they charge.
- Future Sight / Doom Desire are delayed future damage and never immediate
  current-turn attacks.
- Hyper Beam-style recharge and Outrage-style `lockedmove` are typed separately.

Ordinary moves have no special timing flags; only their base/effective priority
values are populated.

## Representative tests

Surf, Quick Attack, Grassy Glide in and outside Grassy Terrain, Solar Beam in
clear weather and sun, Meteor Beam with Power Herb, Future Sight, Hyper Beam,
Outrage, Psychic Terrain blocking, unknown Grassy Glide grounding, and switch
prefix preservation.

Focused v7 suite: **52 passed**.

## INEXACT categories now modeled

- Grassy Glide terrain-conditional priority.
- Charge-turn versus current-turn attack timing.
- Solar weather skip and Power Herb skip provenance.
- Hyper Beam-style recharge.
- Outrage-style move lock.
- Future Sight / Doom Desire delayed future damage and known delay.
- Selected ability-driven priority and Psychic Terrain blocking.

The completeness-audit classifier is not reclassified in this batch.

## Deferred timing mechanics

- Already-in-progress two-turn moves require move-specific volatile provenance;
  a generic `twoturnmove` observation is insufficient.
- Same-turn opponent-action gates such as Sucker Punch / Thunderclap remain
  conditional-execution work.
- Fake Out / First Impression first-active-turn legality, Payback/Avalanche
  within-turn ordering, and Stomping Tantrum/Temper Flare prior-failure state
  remain deferred.
- Quick Claw / Custap Berry and other probabilistic item activation are deferred.
- Prankster's Dark-target immunity and richer redirection/order interactions are
  deferred.

## Gate status

The gate remains **closed**. Batch 4 is diagnostic/shadow-only and has not been
materialized, trained, or promoted.
