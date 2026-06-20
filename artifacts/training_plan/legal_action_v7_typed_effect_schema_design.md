# legal-action-v7: Typed Action-Effect Schema (Design)

Design only. No schema is implemented, no data materialized, no training run, no
live default changed by this document. It proposes how to convert the high-value
v6 **INEXACT** mechanics into typed, Showdown/sim-core-backed action features.

## Goal and principle

v6 is the stable, zero-wrong-exact baseline (331D, 138 PASS / 0 FAIL / 212
INEXACT). Most of those INEXACT entries are honest *coarse* annotations
(`impact_unknown=1`, boolean next-state change flags) or fail-closed values. v7
replaces the coarse signals with **typed exact** ones wherever Showdown's move data
makes the effect deterministic from already-represented state, and represents
genuinely-uncertain effects as **explicit distributions**, never fake single
values.

Rules carried from the project:
- Oracle = bundled Pokémon Showdown move data + sim-core/@smogon calc. No invented values.
- No vague booleans where exact typed info can be extracted (chance, stat stage, status type, hit count, fractions).
- Append-only: the 331D v6 prefix stays **byte-identical**; v7 = v6 + a new typed-effect slice (SLICE8).
- Uncertain-by-nature effects (opponent's hidden same-turn action) stay INEXACT even in v7, flagged as distributions/`*_partial`, not faked.

## Versioning / append-only layout

```
ACTION_FEATURE_NAMES_V7 = ACTION_FEATURE_NAMES_V6 (331, unchanged) + SLICE8_TYPED_EFFECT_NAMES
ACTION_FEATURE_VERSION_V7 = "legal-action-v7"
```

- The first 331 columns of every v7 vector MUST equal the v6 builder output for the
  same action (prefix preservation; verified in tests).
- v6 (`legal-action-v6`, 331D, fingerprint `ac8fb3d3…73f049`) is untouched and
  remains the stable baseline. v5 stays frozen/stale.

### Fingerprint strategy

- `action_feature_names_sha256` = SHA-256 over the full ordered v7 name list.
- Guard asserts the v6 prefix fingerprint is still `ac8fb3d3…73f049` (recompute
  SHA-256 of the first 331 names and compare) — proves no reordering/insertion in
  the prefix.
- A v6 checkpoint must NOT load as v7 and vice-versa: the existing
  `validate_vnext_checkpoint_metadata` guard already rejects on
  name/dim/fingerprint mismatch; v7 adds its own `legal-action-v7` + dim +
  fingerprint and a flagged rejection of fingerprint-less legacy checkpoints.

## SLICE8 typed-effect fields (proposed)

Grouped by category, with provisional names, counts, encodings, and ranges. All
scalars are clamped to the stated range; chances ∈ [0,1]; stat stages normalized
by /6 to [-1,1]; fractions ∈ [0,1] of the relevant HP base.

### A. Typed status — per-type chance (14)
Per-type **chance** scalars so multi-outcome status (Tri Attack, Dire Claw) is a
distribution, not a one-hot.
- target: `effect_target_status_brn/par/psn/tox/slp/frz/confusion_chance` (7)
- self: `effect_self_status_brn/par/psn/tox/slp/frz/confusion_chance` (7) — e.g. Rest = self slp 1.0

### B. Typed stat deltas (16)
Signed magnitude per stat + an application chance, for target and self.
- target: `effect_target_boost_atk/def/spa/spd/spe/accuracy/evasion_stage` (7, /6 signed) + `effect_target_stat_chance` (1)
- self: `effect_self_boost_atk/def/spa/spd/spe/accuracy/evasion_stage` (7, /6 signed) + `effect_self_stat_chance` (1)

### C. Volatile effects (13)
- target: `effect_target_flinch_chance` (1, scalar), `effect_target_trap` (1), `effect_target_taunt` (1), `effect_target_encore` (1), `effect_target_disable` (1), `effect_target_leech_seed` (1), `effect_target_yawn` (1), `effect_target_volatile_other` (1)
- self: `effect_self_substitute` (1), `effect_self_protect` (1), `effect_self_magnet_rise` (1), `effect_self_destiny_bond` (1), `effect_self_volatile_other` (1)

### D. Item effects (6)
- `effect_removes_target_item` (1, Knock Off / Thief / Bug Bite)
- `effect_knockoff_bonus_applied` (1, the 1.5x when a removable item is present)
- `effect_target_item_known` (1, provenance: known vs randbats-inferred)
- `effect_swaps_items` (1, Trick / Switcheroo)
- `effect_consumes_target_berry` (1, Bug Bite / Pluck)
- `effect_user_item_consumed` (1, e.g. Power Herb / gained berry)

### E. Priority / timing (8)
- `effect_priority_effective_stage` (1, resolved priority /5 signed, incl. terrain/ability conditions)
- `effect_priority_conditional` (1, priority depends on context — Grassy Glide, Gale Wings)
- `effect_two_turn_charge` (1, move charges by nature)
- `effect_charges_this_turn` (1, resolved: charging this turn → no damage this turn)
- `effect_fires_this_turn` (1, resolved: lands this turn — sun/Power Herb/none)
- `effect_delayed_future` (1, Future Sight-style)
- `effect_delay_turns` (1, /3)
- `effect_timing_partial` (1, timing depends on unknown context)

### F. Recoil / drain / heal / self-damage (5)
- `effect_recoil_fraction` (1, of damage dealt)
- `effect_drain_fraction` (1, of damage dealt)
- `effect_self_heal_fraction` (1, of max HP — Recover/Roost/Wish/Slack Off)
- `effect_self_damage_fraction` (1, of max HP — Belly Drum/Substitute/Curse-ghost/Mind Blown)
- `effect_crash_on_miss` (1, High Jump Kick / Jump Kick)

### G. Hazards / screens / weather / terrain / field-side (22)
- hazards set: `effect_set_stealth_rock/spikes/toxic_spikes/sticky_web` (4)
- hazard control: `effect_remove_hazards_self_side` (1), `effect_remove_hazards_foe_side` (1), `effect_court_change` (1)
- screens: `effect_set_reflect` (1), `effect_set_light_screen` (1), `effect_set_aurora_veil` (1), `effect_break_screens` (1, Brick Break / Psychic Fangs / Defog)
- weather: `effect_set_weather_rain/sun/sand/snow` (4)
- terrain: `effect_set_terrain_electric/grassy/misty/psychic` (4)
- field: `effect_set_trick_room` (1), `effect_set_tailwind` (1), `effect_set_field_other` (1)

### H. Forced switch / pivot (2)
- `effect_self_pivot` (1, U-turn / Volt Switch / Flip Turn / Parting Shot / Teleport / Chilly Reception)
- `effect_force_target_switch` (1, Roar / Whirlwind / Dragon Tail / Circle Throw)

### I. Multi-outcome power / multi-hit / crit (8)
- `effect_min_hits` (1, /5), `effect_max_hits` (1, /10), `effect_expected_hits` (1, /10) — typed multi-hit distribution (Skill Link / Loaded Dice shift expected/min)
- `effect_power_alt_multiplier` (1, e.g. 2.0 normalized /3 for Fickle Beam) + `effect_power_alt_chance` (1)
- `effect_guaranteed_crit` (1, Wicked Blow / Flower Trick — already crit-baked in v6 damage, now typed)
- `effect_special_effectiveness_override` (1, Freeze-Dry vs Water and similar)
- `effect_multioutcome_partial` (1, distribution not fully resolvable)

### J. Conditional execution / success (7)
- `effect_may_fail` (1)
- `effect_fail_condition_first_turn` (1, Fake Out / First Impression)
- `effect_fail_condition_opponent_action` (1, Sucker Punch / Thunderclap / Focus Punch)
- `effect_fail_condition_target_item` (1, Poltergeist)
- `effect_fail_condition_user_form` (1, Hyperspace Fury / Double Shock)
- `effect_fail_condition_prior_move` (1, Stomping Tantrum / Temper Flare power; Last Resort)
- `effect_success_chance_known` (1, success probability is computable vs hidden)

### K. Provenance / exactness meta (3)
- `effect_v7_exact` (1, every effect above resolved exactly from known state)
- `effect_v7_partial` (1, ≥1 effect depends on inferred/hidden context — still typed, not coarse)
- `effect_v7_distribution` (1, ≥1 effect is a genuine distribution, e.g. random power / multi-status / multi-hit)

### Dimension estimate

A 14 + B 16 + C 13 + D 6 + E 8 + F 5 + G 22 + H 2 + I 8 + J 7 + K 3 = **~104 new
fields**. **legal-action-v7 ≈ 331 + 104 = ~435D** (estimate; the exact count is
fixed at implementation and frozen with its fingerprint). Plan for ~95-110 to
absorb minor naming adjustments.

## INEXACT → v7 mapping and which moves become PASS

| Current INEXACT category (v6) | v7 fields | Becomes PASS? |
| --- | --- | --- |
| Secondary status (Thunderbolt, Scald, Ice Beam, Sludge Bomb, Nuzzle, …) and primary status (Will-O-Wisp, Thunder Wave, Toxic, Spore, Glare, Hypnosis) | A | **PASS** — typed status + chance |
| Secondary stat drops (Crunch, Earth Power, Lunge) and primary foe stat moves; self drops already PASS via v6 | B | **PASS** — typed stat stage + chance |
| Volatiles: flinch (Iron Head), Taunt, Encore, Disable, Leech Seed, trap (Magma Storm/Whirlpool), Substitute, Protect, Magnet Rise, Destiny Bond | C | **PASS** (flinch as chance) |
| Knock Off item removal + 1.5x; Bug Bite berry; Trick/Switcheroo | D | **PASS** when item known; **partial** (typed + `effect_target_item_known=0`) when inferred |
| Grassy Glide terrain priority | E (`effect_priority_effective_stage`, `effect_priority_conditional`) | **PASS** |
| Charge moves (Solar Beam, Meteor Beam) | E charge/fires flags + the v6 damage | **PASS** when sun/Power Herb known; otherwise typed `charges_this_turn` (exact, no damage this turn) |
| Future Sight delayed | E (`effect_delayed_future`, `effect_delay_turns`) | **PASS** (typed delayed, not fake immediate) |
| Recoil/drain/heal/self-damage (Brave Bird, Flare Blitz, Wood Hammer, Giga Drain, Drain Punch, Recover, Roost, Wish, Belly Drum) | F | **PASS** — typed fractions |
| Hazards/screens/weather/terrain/field (Stealth Rock, Spikes, Reflect, Light Screen, Rain Dance, Trick Room, Tailwind, Defog, Rapid Spin, Court Change, Brick Break/Psychic Fangs screen break) | G | **PASS** |
| Pivots / forced switch (U-turn, Volt Switch, Roar, Dragon Tail) | H | **PASS** (effect typed; exact post-switch identity still external → see deferred) |
| Multi-hit (Bullet Seed, Rock Blast, Surging Strikes, Tachyon Cutter, …) | I min/max/expected hits + per-hit damage from oracle | **PASS** for fixed-count; **distribution** for 2–5 (typed, honest) |
| Random power (Fickle Beam) | I (`effect_power_alt_*`) | **PASS as distribution** |
| Guaranteed crit (already exact damage in v6) / Freeze-Dry (already exact) | I typed flags | already PASS; v7 adds explicit typing |
| First-turn conditional (Fake Out, First Impression) | J (`fail_condition_first_turn`) + reconstructed first-active-turn state | **PASS** when first-active turn is reconstructed; else typed `may_fail` |

Estimated effect of v7: the bulk of the 212 INEXACT entries (the secondary/status/
stat/volatile/recoil/heal/hazard/screen/weather/terrain/multi-hit/charge families,
roughly 150–180 moves) move to **PASS**; the remainder stay INEXACT as explicit
distributions or `*_partial` (see deferred).

## Intentionally deferred (stay INEXACT even in v7)

- **Opponent hidden same-turn action** — Sucker Punch / Thunderclap / Focus Punch
  success; Payback / Avalanche / Lash Out power depend on the opponent's
  simultaneous, hidden choice. v7 types the *condition* (`may_fail` +
  `fail_condition_opponent_action`, or a power distribution) but the outcome is
  irreducibly uncertain at decision time. Deferred because no oracle can know the
  hidden choice.
- **Beat Up** — needs every healthy ally's Attack; computable but party-wide and
  low-value; deferred to a follow-up unless cheap to plumb.
- **Counter / Mirror Coat / Metal Burst** — depend on damage taken this turn
  (hidden). Stay distribution/partial.
- **Stellar typing (Tera Starstorm)** — Terapagos-only, effectively absent from the
  pool; deferred (special STAB/effectiveness).
- **Sleep Talk / random move call**, **multi-turn lock end-state (Outrage/Petal
  Dance)**, **Transform copy** — random/derived move identity; typed as
  `may_fail`/distribution, exact resolution deferred.
- **Post-switch identity for pivots/force-switch** — the *effect* is typed, but the
  resulting Pokémon identity is a separate state-side concern, not an action field.

## Validation tests required before any v7 rematerialization

1. **Prefix integrity** — first 331 v7 names == v6 names byte-for-byte; SHA-256 of
   the prefix == `ac8fb3d3…73f049`; v3/v4/v5/v6 remain exact prefixes where applicable.
2. **Dim/fingerprint** — `len(ACTION_FEATURE_NAMES_V7) == ACTION_FEATURE_DIM_V7`;
   recorded `legal-action-v7` + dim + fingerprint; checkpoint guard rejects v6↔v7.
3. **Per-category oracle cross-checks** (one+ representative move each):
   status type/chance, stat stage/chance, flinch/trap/taunt/encore/disable/leech,
   Knock Off removal + 1.5x + provenance, Trick swap, Bug Bite berry, Grassy Glide
   effective priority, Solar Beam/Meteor Beam charge timing (sun/Power Herb/none),
   Future Sight delay, recoil/drain/heal/self-damage fractions, every hazard/screen/
   weather/terrain setter, multi-hit min/max/expected, Fickle Beam distribution,
   guaranteed crit, Freeze-Dry override.
4. **Range/consistency invariants** — chances ∈ [0,1]; stat stages ∈ [-1,1];
   fractions ∈ [0,1]; `min_hits ≤ expected_hits ≤ max_hits`;
   `charges_this_turn` XOR `fires_this_turn` for charge moves; `v7_exact` ⇒ no
   `*_partial`/`*_distribution` set.
5. **Ordinary-move null check** — a plain move (Surf, Earthquake) has all SLICE8
   effect fields at their neutral defaults (0 / no-effect) except `v7_exact=1`.
6. **Completeness re-audit** — run the audit generator with a v7 classifier and
   record the new PASS / FAIL / INEXACT counts and the per-move reclassification;
   FAIL must remain 0.
7. **Tiny v7 smoke materialization** — 1 battle, schema-validates (dim,
   fingerprints, no NaN), no training.

## "Model receives exactly this and nothing else" verification plan

- **Name↔dim↔fingerprint identity**: assert `dim == len(names)` and
  `fingerprint == sha256(names)`; the dataset embeds the ordered names and the
  loader asserts the live schema equals the embedded names.
- **Decode round-trip**: build a candidate vector, decode every column by name into
  a typed dict, and assert a 1:1 mapping — no unnamed columns, no NaN/inf, every
  value within its documented range.
- **No-leakage assertion**: exact fields (`v7_exact` set) must derive only from
  state already present in v7 state + v6 action features (no opponent hidden choice,
  no future reveal). Hidden/uncertain context may appear ONLY in `*_partial` /
  `*_distribution` / chance fields. A test feeds a known fixture and asserts exact
  fields don't change when hidden opponent info is perturbed.
- **Prefix-equality test**: for a sample of actions, the first 331 columns of the
  v7 vector equal `build_action_feature_vector_v6(...)` exactly.
- **Pool-wide property test**: for every move in the bundled randbats pool, the
  SLICE8 vector matches the Showdown oracle for that move's category (the §3 checks
  applied exhaustively, not just representatives).
- **Provenance audit**: count candidates with `v7_exact` vs `v7_partial` vs
  `v7_distribution`, broken down by move/Tera/switch, so the exact-vs-typed-uncertain
  share is explicit before any training — mirroring the v6 exact-vs-INEXACT report.

## Status

Design only. v6 remains the stable zero-FAIL baseline; nothing was implemented,
materialized, trained, promoted, or changed live. v7 is **not approved** for
implementation or rematerialization — that is a separate, explicitly-gated step
after this design is reviewed. The training gate stays **closed**.
