# legal-action-v7 Batch 5: Typed HP Side Effects Implementation

Appends typed recoil, drain, healing, HP-cost, fixed self-damage, and crash
effects after the frozen 406D batch-4 prefix. No training, materialization,
checkpoint promotion, or live-default change was performed.

## Schema

- Added `SLICE12_HP_SIDE_EFFECT_FEATURE_NAMES` with 14 fields.
- `legal-action-v7` is now **420D**.
- Ordered-name fingerprint:
  `05f27e8d093bcafb4d9f2f09aa2a75a003bbf985861076aec035a7f90a2fc856`.
- The first 406 names and values remain byte-identical to batch 4; fingerprint:
  `bdf2439df649fcc0f1433482c8dc7a1ad7389b40be73c39884c27b45b81fb935`.
- The 331D v6, 361D batch-1, 375D batch-2, and 388D batch-3 prefixes remain
  unchanged.

## Fields

- `effect_recoil_damage_fraction`
- `effect_recoil_max_hp_fraction`
- `effect_drain_damage_fraction`
- `effect_user_heal_max_hp_fraction`
- `effect_target_heal_max_hp_fraction`
- `effect_self_damage_max_hp_fraction`
- `effect_hp_cost_max_hp_fraction`
- `effect_crash_damage_max_hp_fraction`
- `effect_hp_condition_known`
- `effect_healing_blocked`
- `effect_hp_cost_blocked`
- `effect_hp_effect_conditional`
- `effect_hp_effect_amount_unknown`
- `effect_hp_effect_other`

All fractions are natural `[0,1]` values and are separate from current-turn
damage.

## Oracle and state resolution

Direct `recoil`, `drain`, and `heal` arrays are parsed from bundled Showdown
`moves.ts`. Callback-only mechanics are grounded in their Showdown source:

- Steel Beam / Mind Blown / Chloroblast: 1/2 max-HP self-damage.
- Substitute: 1/4 max-HP cost; Belly Drum: 1/2 max-HP cost.
- High Jump Kick / Jump Kick: 1/2 max-HP crash damage on failure.
- Struggle: 1/4 max-HP recoil.
- Moonlight / Morning Sun / Synthesis: 1/2 normally, 0.667 in sun, 1/4 in
  adverse weather.
- Shore Up: 1/2 normally, 0.667 in sand.
- Heal Pulse: 1/2 target max HP, 3/4 with Mega Launcher.
- Floral Healing: 1/2 target max HP, 0.667 in Grassy Terrain.
- Strength Sap: healing amount is explicitly unknown because it depends on the
  target's resolved Attack stat.

Current reconstructed HP detects insufficient Substitute/Belly Drum cost.
`healblock` on the relevant side marks healing blocked. Exact move damage is not
changed or fail-closed by this slice.

## Representative tests

Flare Blitz, Brave Bird, Wood Hammer, Head Smash, Drain Punch, Giga Drain,
Bitter Blade, Recover, Roost, Slack Off, Moonlight in sun/rain, Strength Sap,
Substitute, Belly Drum, Steel Beam, Mind Blown, Chloroblast, High Jump Kick,
Heal Pulse, Surf, Earthquake, and switch actions.

Focused v7 suite: **64 passed**.

## INEXACT categories now modeled

- Damage-relative recoil and drain fractions.
- Fixed max-HP recovery and weather/terrain/ability-dependent recovery.
- Fixed max-HP self-damage.
- Substitute/Belly Drum HP costs and known insufficient-HP failure.
- High Jump Kick-style crash damage.
- Heal Block suppression.
- Strength Sap's dynamic heal provenance without inventing a fraction.

The completeness-audit classifier is not reclassified in this batch.

## Deferred HP-side-effect mechanics

- Strength Sap's exact amount requires the target's resolved Attack stat.
- Wish, Healing Wish, and Lunar Dance involve delayed/team-slot healing and stay
  in the catch-all for a future delayed/team-transition slice.
- Pain Split, Endeavor-like HP equalization, Final Gambit, and other
  target/current-HP formulas need dedicated typed transitions.
- Recoil prevention/modification from Magic Guard, Rock Head, Reckless, and
  ability suppression is not yet represented in this slice.
- Shell Bell, Leftovers, berries, and other item/ability-triggered post-move
  healing remain separate from intrinsic move effects.

## Gate status

The gate remains **closed**. Batch 5 is diagnostic/shadow-only and has not been
materialized, trained, or promoted.
