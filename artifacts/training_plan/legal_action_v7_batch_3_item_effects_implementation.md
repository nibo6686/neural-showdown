# legal-action-v7 Batch 3: Typed Item Effects Implementation

Appends an item-effect slice after the frozen 375D v7 batch-2 prefix. No
training, dataset materialization, checkpoint promotion, or live-default change
was performed.

## Schema

- Added `SLICE10_ITEM_EFFECT_FEATURE_NAMES` with 13 fields.
- `legal-action-v7` is now **388D**.
- Ordered-name fingerprint:
  `d3f342710b001eded43f1ccee8228ce42d1fe616fb6f043593a3e8c3893cc91d`.
- The first 375 names and values remain byte-identical to batch 2; their
  fingerprint remains
  `7f102fd8abc51bc6c776a1447bf27a15ec71352e3d6a9f9ba901d7f7eecc0252`.
- The v6 331D and batch-1 361D prefixes remain unchanged.

## Fields

- `effect_target_item_removal_chance`
- `effect_target_item_removal_state_known`
- `effect_target_item_removal_state_unknown`
- `effect_knock_off_damage_boost_applied`
- `effect_target_item_known`
- `effect_target_item_unknown`
- `effect_target_item_present`
- `effect_target_berry_eaten_or_stolen`
- `effect_items_swapped`
- `effect_user_item_consumed`
- `effect_target_item_suppressed`
- `effect_all_items_suppressed`
- `effect_item_other`

The target provenance fields are emitted only for item-relevant moves. A known
held item, confirmed absence (`none`/`removed`/`consumed`), and unknown state are
distinct. Unknown never pretends that removal or Knock Off's 1.5x modifier
applies.

## Oracle and semantics

Move families and charge flags come from bundled Showdown `moves.ts`; berry
identity comes from `items.ts` `isBerry: true`; current item identity/state comes
from the existing private and tactical battle snapshots.

- Knock Off: current-turn damage boost and next-state removal are separate.
- Bug Bite / Pluck: berry eat/steal is set only for a known held berry.
- Trick / Switcheroo: item swap is typed separately.
- Solar Beam / Meteor Beam with a currently held Power Herb: user consumption.
- Embargo: target item suppression.
- Magic Room: all-active-item suppression.
- Other Showdown item-manipulating callbacks (for example Fling) use the catch-all
  until a dedicated field is designed.

Existing exact damage is untouched. In particular, Knock Off and Bug Bite retain
their existing exact impact fields; the appended slice adds their next-state
item semantics.

## Representative tests

Surf, Earthquake, and switch actions are all-zero; Knock Off with Leftovers,
confirmed no item, and unknown item; Bug Bite / Pluck with Sitrus Berry,
Leftovers, and unknown item; Trick / Switcheroo; Power Herb Solar Beam / Meteor
Beam; Embargo; Magic Room; and Fling catch-all.

Focused v7 suite: **40 passed**.

## INEXACT categories now modeled

- Knock Off target-item removal and known-item damage-modifier provenance.
- Bug Bite / Pluck target berry consumption/steal.
- Trick / Switcheroo item exchange.
- Power Herb consumption for metadata-marked charge moves.
- Embargo / Magic Room item suppression.

The mechanics audit is not reclassified in this batch; its v7-aware classifier
remains separate work.

## Deferred item mechanics

- Sticky Hold and per-item `TakeItem` immunity can make removal/swap fail.
- Thief/Covet-style transfer, Fling, Incinerate, Bestow, Recycle, and similar
  callbacks remain in `effect_item_other` when detected.
- White Herb and ordinary berry consumption depend on resulting stat/HP/status
  branches and are deferred until those branch conditions are represented.
- Symbiosis, Pickpocket/Magician and other ability-driven transfers are deferred.

## Gate status

The gate remains **closed**. v7 batch 3 is diagnostic/shadow-only; no fresh v7
artifact exists and no training or promotion is approved.
