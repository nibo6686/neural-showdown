# legal-action-v7 Batch 6: Typed Field and Side Effects Implementation

Appends typed hazards, screens, weather, terrain, room, and side-condition
effects after the frozen 420D batch-5 prefix. No training, materialization,
checkpoint promotion, or live-default change was performed.

## Schema

- Added `SLICE13_FIELD_SIDE_EFFECT_FEATURE_NAMES` with 32 fields.
- `legal-action-v7` is now **452D**.
- Ordered-name fingerprint:
  `e3e39124cd24e3e27684306e3d401859083df65965e721eb3e5e8b89c48fcb4c`.
- The first 420 names and values remain byte-identical to batch 5; fingerprint:
  `05f27e8d093bcafb4d9f2f09aa2a75a003bbf985861076aec035a7f90a2fc856`.
- All earlier v6/v7 prefixes remain unchanged.

## Fields

Hazard setup:

- `effect_target_side_stealth_rock_setup`
- `effect_target_side_spikes_setup`
- `effect_target_side_toxic_spikes_setup`
- `effect_target_side_sticky_web_setup`

Removal and screens:

- `effect_user_side_hazards_removed`
- `effect_target_side_hazards_removed`
- `effect_user_side_reflect_setup`
- `effect_user_side_light_screen_setup`
- `effect_user_side_aurora_veil_setup`
- `effect_target_side_screens_removed`
- `effect_terrain_removed`
- `effect_side_conditions_swapped`

Weather and terrain:

- `effect_weather_sun_set`, `effect_weather_rain_set`
- `effect_weather_sand_set`, `effect_weather_snow_set`
- `effect_terrain_grassy_set`, `effect_terrain_electric_set`
- `effect_terrain_psychic_set`, `effect_terrain_misty_set`

Rooms/global field:

- `effect_trick_room_set`, `effect_magic_room_set`
- `effect_wonder_room_set`, `effect_gravity_set`

Other user-side conditions:

- `effect_user_side_tailwind_setup`
- `effect_user_side_safeguard_setup`
- `effect_user_side_mist_setup`
- `effect_user_side_lucky_chant_setup`

Provenance:

- `effect_field_side_condition_known`
- `effect_field_side_effect_blocked`
- `effect_field_side_effect_conditional`
- `effect_field_side_other`

## Oracle and side semantics

Showdown `sideCondition`, `weather`, `terrain`, and `pseudoWeather` literals are
parsed directly from bundled `moves.ts`. Callback removals are mapped from their
Showdown behavior:

- Rapid Spin / Mortal Spin: user-side hazard removal.
- Defog: user- and target-side hazards, target screens, and terrain removal.
- Tidy Up: hazards on both sides.
- Brick Break / Psychic Fangs / Raging Bull: target screen removal.
- Court Change: side-condition swap, not fake hazard removal.

Aurora Veil is explicitly conditional and is marked blocked outside snow/hail
when current reconstructed weather is available. Damaging moves retain their
existing exact damage fields; field/side effects are appended separately.

## Representative tests

Stealth Rock, Spikes, Toxic Spikes, Sticky Web, Defog, Rapid Spin, Mortal Spin,
Reflect, Light Screen, Aurora Veil in snow/clear weather, Brick Break, Psychic
Fangs, Sunny Day, Rain Dance, Sandstorm, Snowscape, all four terrains, Trick
Room, Magic Room, Wonder Room, Gravity, Tailwind, Safeguard, Mist, Lucky Chant,
Court Change, Surf, Earthquake, and switch actions.

Focused v7 suite: **76 passed**.

## INEXACT categories now modeled

- Typed hazard setup and side-aware hazard removal.
- Typed screen setup and damaging screen removal.
- Explicit weather and terrain types.
- Trick/Magic/Wonder Room and Gravity.
- Tailwind, Safeguard, Mist, and Lucky Chant.
- Defog terrain clearing and Court Change swapping.
- Aurora Veil's weather requirement.

The completeness-audit classifier is not reclassified in this batch.

## Deferred field/side mechanics

- Hazard layer caps and already-active screen/side-condition restart behavior
  can be added from current side-condition counts in a later state-conditioned
  refinement.
- Defog failure/success can also depend on its evasion-drop branch and target
  interaction; typed removal intent is exact, while per-condition availability
  is not expanded into separate fields.
- G-Max hazards/residual side conditions, pledge combinations, and niche
  generation-specific effects remain in the catch-all.
- Room toggling/removal when the same room is already active is not yet separated
  from room activation.
- Weather/terrain setters from abilities, items, and Max moves are outside this
  intrinsic legal-move slice.

## Gate status

The gate remains **closed**. Batch 6 is diagnostic/shadow-only and has not been
materialized, trained, or promoted.
