# Gen 9 Random Battles Mechanics Completeness Audit

## Scope and Decision Rule

- Source: `sim-core\node_modules\pokemon-showdown\data\random-battles\gen9\sets.json` (507 species/form entries).
- Unique move pool audited: **350**.
- Schema: `legal-action-v6`, 331D.
- Oracle: bundled Pokémon Showdown move definitions and sim-core/@smogon calc; the focused counterfactual suite remains 12 PASS / 0 FAIL.
- PASS means all material behavior used by current v6 impact fields is represented correctly.
- INEXACT means the limitation is explicit through unknown/fail-closed fields or coarse effect annotation.
- FAIL means v6 emits an exact-looking value/absence that can be mechanically wrong.
- NOT_RELEVANT is reserved for behavior outside every current v6 action-impact field.

## Summary

- PASS: **138**
- FAIL: **0**
- INEXACT: **212**
- NOT_RELEVANT: **0**

After mechanics-repair batches 1-5 the exhaustive move-pool audit has **zero wrong-exact (FAIL) entries**: every material move-impact mechanic is either PASS or explicitly INEXACT/fail-closed. The gate remains closed pending the separate training-readiness review, not on mechanics fidelity.

Mechanics-repair batch 1 (`mechanics_repair_batch_1_fixed_multihit_accuracy.md`) cleared the fixed-damage and multi-hit wrong-exact buckets and made dynamic accuracy honest: Seismic Toss and Night Shade route level-based fixed damage to the oracle (PASS); Super Fang, Ruination, Endeavor, Mirror Coat and all multi-hit moves fail closed (impact_unknown) → INEXACT.

Mechanics-repair batch 2 (`mechanics_repair_batch_2_secondary_effects.md`) cleared the secondary/status/stat/volatile wrong-exact bucket (FAIL 159 → 39). A coarse presence detector now fills the existing next-state change flags (`next_opp_status_change`, `next_own_status_change`, `next_opp_stat_change`, `next_own_stat_change`) so a move with a real secondary status/stat/volatile effect is no longer encoded as a wrong-exact "no change"; the exact status type, chance and magnitude remain unrepresented, so these moves are INEXACT, not PASS. The four weather-accuracy moves now leave FAIL on this same basis. Item-swap, copy and random-call status moves (Trick, Switcheroo, Transform, Sleep Talk) are coarsely flagged as non-damaging actions and noted as needing typed v7 fields.

Mechanics-repair batch 3 (`mechanics_repair_batch_3_dynamic_type_charge.md`) handled dynamic type/STAB and charge/delay timing (FAIL 39 → 27). sim-core now returns the resolved (post-`calculate`) move type, so impact type-effectiveness and STAB use the actual dynamic type: Weather Ball, Terrain Pulse, Judgment, Ivy Cudgel, Raging Bull, Revelation Dance, Aura Wheel and Tera Blast become PASS. Tera Starstorm fails closed (Stellar STAB/effectiveness are not representable). Two-turn charge / delayed moves no longer emit on-hit damage as immediate: Solar Beam (sun/Power Herb) and Meteor Beam (Power Herb) are exact only when they fire this turn and otherwise fail closed; Future Sight always fails closed; Beak Blast is PASS because its damage is same-turn.

Mechanics-repair batch 4 (`mechanics_repair_batch_4_conditional_execution_history_power.md`) handled conditional execution/success and turn/history-conditional power (FAIL 27 → 9). Moves whose success or power depends on the opponent's same-turn action, the first-active turn, the user's form, the target's item, within-turn order, or unplumbed prior-move-failure history now fail closed (impact_unknown) instead of claiming damage: Fake Out, First Impression, Sucker Punch, Thunderclap, Focus Punch, Double Shock, Hyperspace Fury, Poltergeist, Payback, Avalanche, Lash Out, Stomping Tantrum, Temper Flare. Fusion Bolt / Fusion Flare and Pollen Puff are PASS because their doubling / ally-heal branch cannot occur in singles. Brick Break / Psychic Fangs keep their exact (screen-bypassing) damage and coarsely flag the conditional screen removal as a field/side change.

Mechanics-repair batch 5 (`mechanics_repair_batch_5_final_failures.md`) cleared the final wrong-exact bucket (FAIL 9 → 0). PASS: Flower Trick / Wicked Blow (the calc bakes the guaranteed crit into the rolls, so the impact reports crit_included=True), Freeze-Dry (sim-core now reflects its special 2x-vs-Water effectiveness in type-effectiveness and damage), Photon Geyser (the calc selects the higher attacking stat and matching physical/special category — verified exact). INEXACT, fail-closed because the damage itself is wrong-exact: Beat Up (per-ally-Attack damage returns 0 from the calc) and Fickle Beam (random double-power branch). INEXACT with damage kept exact (only an unrepresented next-state effect remains, documented for a v7 typed field): Knock Off (target item removal), Bug Bite (stolen berry), Grassy Glide (terrain-conditional +1 priority). No schema name/order/dim changed; v6 remains 331D.

## Mechanic Bucket Counts

| Bucket | PASS | FAIL | INEXACT | NOT_RELEVANT |
| --- | ---: | ---: | ---: | ---: |
| dynamic accuracy | 0 | 0 | 4 | 0 |
| dynamic base power or damage | 20 | 0 | 25 | 0 |
| forced move or execution constraint | 0 | 0 | 19 | 0 |
| hp dependent or hp cost | 3 | 0 | 20 | 0 |
| item dependent | 1 | 0 | 5 | 0 |
| multi turn or repeat chain | 2 | 0 | 2 | 0 |
| nonstandard stat source | 4 | 0 | 0 | 0 |
| ordinary damage | 62 | 0 | 3 | 0 |
| priority | 11 | 0 | 15 | 0 |
| recoil drain crash or self damage | 0 | 0 | 36 | 0 |
| side effect | 35 | 0 | 153 | 0 |
| speed or weight | 4 | 0 | 0 | 0 |
| status dependent or inflicting | 2 | 0 | 22 | 0 |
| type dependent | 7 | 0 | 2 | 0 |
| weather or terrain | 3 | 0 | 4 | 0 |

## Material Blockers

- Wrong-exact moves: None

- Explicitly inexact moves: Air Slash, Apple Acid, Aurora Veil, Avalanche, Beat Up, Belly Drum, Bite, Bitter Blade, Bitter Malice, Bleakwind Storm, Blizzard, Blue Flare, Body Slam, Bolt Strike, Brave Bird, Brick Break, Bug Bite, Bug Buzz, Bullet Seed, Chilly Reception, Circle Throw, Clangorous Soul, Court Change, Crunch, Curse, Dark Pulse, Defog, Destiny Bond, Dire Claw, Disable, Discharge, Double Shock, Double-Edge, Dragon Darts, Dragon Tail, Drain Punch, Draining Kiss, Dual Wingbeat, Dynamic Punch, Earth Power, Encore, Endeavor, Energy Ball, Explosion, Fake Out, Fickle Beam, Fiery Dance, Fiery Wrath, Fillet Away, Fire Blast, Fire Fang, Fire Punch, First Impression, Flamethrower, Flare Blitz, Flash Cannon, Flip Turn, Focus Blast, Focus Punch, Freezing Glare, Future Sight, Giga Drain, Glare, Grassy Glide, Grav Apple, Gunk Shot, Haze, Head Smash, Headbutt, Heal Bell, Healing Wish, Heat Wave, High Jump Kick, Horn Leech, Hurricane, Hyperspace Fury, Hypnosis, Ice Beam, Ice Fang, Ice Punch, Icicle Crash, Icicle Spear, Iron Head, Iron Tail, Knock Off, Lash Out, Lava Plume, Leech Life, Leech Seed, Light Screen, Liquidation, Lumina Crash, Lunge, Luster Purge, Magma Storm, Magnet Rise, Malignant Chain, Matcha Gotcha, Meteor Beam, Meteor Mash, Milk Drink, Mirror Coat, Moonblast, Moonlight, Morning Sun, Mortal Spin, Mud Shot, Muddy Water, Mystical Fire, No Retreat, Nuzzle, Pain Split, Parting Shot, Payback, Play Rough, Poison Fang, Poison Jab, Poltergeist, Population Bomb, Pounce, Protect, Psychic, Psychic Fangs, Psychic Noise, Pyro Ball, Rain Dance, Razor Shell, Recover, Reflect, Relic Song, Rest, Revival Blessing, Roar, Rock Blast, Rock Slide, Rock Tomb, Roost, Ruination, Sacred Fire, Salt Cure, Scald, Scale Shot, Scorching Sands, Seed Flare, Shadow Ball, Shed Tail, Shell Side Arm, Shore Up, Slack Off, Sleep Powder, Sleep Talk, Sludge Bomb, Sludge Wave, Snowscape, Soft-Boiled, Solar Beam, Sparkling Aria, Spikes, Spirit Break, Spore, Stealth Rock, Steam Eruption, Sticky Web, Stomping Tantrum, Strange Steam, Strength Sap, Stun Spore, Substitute, Sucker Punch, Sunny Day, Super Fang, Supercell Slam, Surging Strikes, Switcheroo, Synthesis, Tachyon Cutter, Tail Slap, Tailwind, Take Heart, Taunt, Teleport, Temper Flare, Tera Starstorm, Thunder, Thunder Punch, Thunder Wave, Thunderbolt, Thunderclap, Tidy Up, Toxic, Toxic Spikes, Transform, Tri Attack, Trick, Trick Room, Triple Arrows, Triple Axel, U-turn, Volt Switch, Volt Tackle, Water Pulse, Waterfall, Wave Crash, Whirlpool, Whirlwind, Wild Charge, Will-O-Wisp, Wish, Wood Hammer, Yawn, Zen Headbutt, Zing Zap

## Per-Move Classification

| Move | Category | Mechanic buckets | Status | Reason |
| --- | --- | --- | --- | --- |
| Accelerock | Physical | priority | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Acid Armor | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Acrobatics | Physical | dynamic_base_power_or_damage, item_dependent | **PASS** | Showdown/sim-core oracle receives the required represented state |
| Aeroblast | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Agility | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Air Slash | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Alluring Voice | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Apple Acid | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Aqua Cutter | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Aqua Jet | Physical | priority | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Aqua Step | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Armor Cannon | Special | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Astral Barrage | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Aura Sphere | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Aura Wheel | Physical | type_dependent | **PASS** | dynamic move type resolved from state via sim-core result.move.type for type-effectiveness and STAB (batch 3) |
| Aurora Veil | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Avalanche | Physical | dynamic_base_power_or_damage, priority | **INEXACT** | turn/history-conditional power depends on same-turn order/hit/stat-drop or prior-move-failure not plumbed to the oracle; fails closed (batch 4) |
| Beak Blast | Physical | priority | **PASS** | same-turn damage is exact; -3 priority charge with reactive contact-burn is out of v6 impact scope (batch 3) |
| Beat Up | Physical | dynamic_base_power_or_damage | **INEXACT** | per-ally-Attack damage is not resolvable by the calc (returns 0); fails closed (batch 5) |
| Behemoth Blade | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Belly Drum | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Bite | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Bitter Blade | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Bitter Malice | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Bleakwind Storm | Special | dynamic_accuracy, side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Blizzard | Special | dynamic_accuracy, side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Blood Moon | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Blue Flare | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Body Press | Physical | nonstandard_stat_source | **PASS** | Showdown/sim-core oracle receives the required represented state |
| Body Slam | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Bolt Strike | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Boomburst | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Brave Bird | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Brick Break | Physical | ordinary_damage | **INEXACT** | damage is exact (calc bypasses screens); the conditional screen removal is coarsely flagged as a field/side change (batch 4) |
| Bug Bite | Physical | item_dependent | **INEXACT** | damage is exact; the stolen-berry consumption effect is unrepresented (needs v7 item-delta) (batch 5) |
| Bug Buzz | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Bulk Up | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Bullet Punch | Physical | priority | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Bullet Seed | Physical | dynamic_base_power_or_damage | **INEXACT** | multi-hit total/distribution fails closed (impact_unknown) in batch 1 |
| Calm Mind | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Ceaseless Edge | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Chilly Reception | Status | forced_move_or_execution_constraint, side_effect, weather_or_terrain | **INEXACT** | switch/force-switch effect is marked without exact resulting state |
| Circle Throw | Physical | forced_move_or_execution_constraint, priority | **INEXACT** | damage is resolved and switching is flagged, but resulting state is not exact |
| Clanging Scales | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Clangorous Soul | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Clear Smog | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Close Combat | Physical | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Coil | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Collision Course | Physical | dynamic_base_power_or_damage | **PASS** | Showdown/sim-core oracle receives the required represented state |
| Cosmic Power | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Court Change | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Crabhammer | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Crunch | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Curse | Status | side_effect, status_dependent_or_inflicting, type_dependent | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Dark Pulse | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Dazzling Gleam | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Defog | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Destiny Bond | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Diamond Storm | Physical | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Dire Claw | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Disable | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Discharge | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Double Shock | Physical | forced_move_or_execution_constraint | **INEXACT** | move-success depends on opponent action / first-active turn / form / target item; fails closed rather than assume it hits (batch 4) |
| Double-Edge | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Draco Meteor | Special | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Dragon Ascent | Physical | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Dragon Claw | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Dragon Dance | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Dragon Darts | Physical | dynamic_base_power_or_damage | **INEXACT** | multi-hit total/distribution fails closed (impact_unknown) in batch 1 |
| Dragon Energy | Special | dynamic_base_power_or_damage, hp_dependent_or_hp_cost | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| Dragon Pulse | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Dragon Tail | Physical | forced_move_or_execution_constraint, priority | **INEXACT** | damage is resolved and switching is flagged, but resulting state is not exact |
| Drain Punch | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Draining Kiss | Special | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Drill Run | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Dual Wingbeat | Physical | dynamic_base_power_or_damage | **INEXACT** | multi-hit total/distribution fails closed (impact_unknown) in batch 1 |
| Dynamax Cannon | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Dynamic Punch | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Earth Power | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Earthquake | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Electro Drift | Special | dynamic_base_power_or_damage | **PASS** | Showdown/sim-core oracle receives the required represented state |
| Encore | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Endeavor | Physical | dynamic_base_power_or_damage | **INEXACT** | fixed-damage target/counter context fails closed (impact_unknown) in batch 1 |
| Energy Ball | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Eruption | Special | dynamic_base_power_or_damage, hp_dependent_or_hp_cost | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| Esper Wing | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Expanding Force | Special | dynamic_base_power_or_damage, weather_or_terrain | **PASS** | Showdown/sim-core oracle receives the required represented state |
| Explosion | Physical | recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Extreme Speed | Physical | priority | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Facade | Physical | dynamic_base_power_or_damage, status_dependent_or_inflicting | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| Fake Out | Physical | forced_move_or_execution_constraint, priority, side_effect | **INEXACT** | move-success depends on opponent action / first-active turn / form / target item; fails closed rather than assume it hits (batch 4) |
| Fickle Beam | Special | dynamic_base_power_or_damage | **INEXACT** | random double-power branch is not represented; fails closed rather than emit one exact value (batch 5) |
| Fiery Dance | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Fiery Wrath | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Fillet Away | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Fire Blast | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Fire Fang | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Fire Punch | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| First Impression | Physical | forced_move_or_execution_constraint, priority | **INEXACT** | move-success depends on opponent action / first-active turn / form / target item; fails closed rather than assume it hits (batch 4) |
| Flame Charge | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Flamethrower | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Flare Blitz | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Flash Cannon | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Fleur Cannon | Special | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Flip Turn | Physical | forced_move_or_execution_constraint | **INEXACT** | damage is resolved and switching is flagged, but resulting state is not exact |
| Flower Trick | Physical | ordinary_damage | **PASS** | guaranteed crit is baked into the calc damage rolls; impact reports crit_included=True (batch 5) |
| Focus Blast | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Focus Punch | Physical | forced_move_or_execution_constraint, priority | **INEXACT** | move-success depends on opponent action / first-active turn / form / target item; fails closed rather than assume it hits (batch 4) |
| Foul Play | Physical | nonstandard_stat_source | **PASS** | Showdown/sim-core oracle receives the required represented state |
| Freeze-Dry | Special | side_effect | **PASS** | Freeze-Dry's special Water effectiveness is now reflected in sim-core type-effectiveness and damage (batch 5) |
| Freezing Glare | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Fusion Bolt | Physical | dynamic_base_power_or_damage | **PASS** | singles: the partner-fusion same-turn power doubling cannot occur, so base power is exact (batch 4) |
| Fusion Flare | Special | dynamic_base_power_or_damage | **PASS** | singles: the partner-fusion same-turn power doubling cannot occur, so base power is exact (batch 4) |
| Future Sight | Special | ordinary_damage | **INEXACT** | two-turn charge/delayed damage: exact only with sun/Power Herb, fails closed otherwise so immediate timing is not assumed (batch 3) |
| Giga Drain | Special | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Giga Impact | Physical | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Gigaton Hammer | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Glacial Lance | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Glaive Rush | Physical | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Glare | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Grass Knot | Special | dynamic_base_power_or_damage, speed_or_weight | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| Grassy Glide | Physical | priority | **INEXACT** | damage is exact; the terrain-conditional +1 priority modifier is not represented in the static priority feature (needs v7) (batch 5) |
| Grav Apple | Physical | dynamic_base_power_or_damage, side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Gunk Shot | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Haze | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Head Smash | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Headbutt | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Headlong Rush | Physical | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Heal Bell | Status | side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Healing Wish | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Heat Crash | Physical | dynamic_base_power_or_damage, speed_or_weight | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| Heat Wave | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Heavy Slam | Physical | dynamic_base_power_or_damage, speed_or_weight | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| Hex | Special | dynamic_base_power_or_damage, status_dependent_or_inflicting | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| High Horsepower | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| High Jump Kick | Physical | recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Horn Leech | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Hurricane | Special | dynamic_accuracy, side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Hydro Pump | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Hydro Steam | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Hyper Voice | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Hyperspace Fury | Physical | forced_move_or_execution_constraint, side_effect | **INEXACT** | move-success depends on opponent action / first-active turn / form / target item; fails closed rather than assume it hits (batch 4) |
| Hypnosis | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Ice Beam | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Ice Fang | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Ice Hammer | Physical | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Ice Punch | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Ice Shard | Physical | priority | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Ice Spinner | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Icicle Crash | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Icicle Spear | Physical | dynamic_base_power_or_damage | **INEXACT** | multi-hit total/distribution fails closed (impact_unknown) in batch 1 |
| Iron Defense | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Iron Head | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Iron Tail | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Ivy Cudgel | Physical | type_dependent | **PASS** | dynamic move type resolved from state via sim-core result.move.type for type-effectiveness and STAB (batch 3) |
| Jet Punch | Physical | priority | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Judgment | Special | type_dependent | **PASS** | dynamic move type resolved from state via sim-core result.move.type for type-effectiveness and STAB (batch 3) |
| Knock Off | Physical | dynamic_base_power_or_damage, item_dependent | **INEXACT** | damage (incl. item 1.5x scaling) is exact; the target item removal next-state is unrepresented (needs v7 item-delta) (batch 5) |
| Kowtow Cleave | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Lash Out | Physical | dynamic_base_power_or_damage | **INEXACT** | turn/history-conditional power depends on same-turn order/hit/stat-drop or prior-move-failure not plumbed to the oracle; fails closed (batch 4) |
| Lava Plume | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Leaf Blade | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Leaf Storm | Special | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Leech Life | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Leech Seed | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Light Screen | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Liquidation | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Low Kick | Physical | dynamic_base_power_or_damage, speed_or_weight | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| Lumina Crash | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Lunge | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Luster Purge | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Mach Punch | Physical | priority | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Magma Storm | Special | status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Magnet Rise | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Make It Rain | Special | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Malignant Chain | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Matcha Gotcha | Special | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Megahorn | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Meteor Beam | Special | multi_turn_or_repeat_chain | **INEXACT** | two-turn charge/delayed damage: exact only with sun/Power Herb, fails closed otherwise so immediate timing is not assumed (batch 3) |
| Meteor Mash | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Mighty Cleave | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Milk Drink | Status | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Mirror Coat | Special | dynamic_base_power_or_damage, priority | **INEXACT** | fixed-damage target/counter context fails closed (impact_unknown) in batch 1 |
| Moonblast | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Moongeist Beam | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Moonlight | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Morning Sun | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Mortal Spin | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Mud Shot | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Muddy Water | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Mystical Fire | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Nasty Plot | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Night Shade | Special | ordinary_damage | **PASS** | fixed level-based damage routed to the oracle (batch 1); honors type immunity |
| Night Slash | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| No Retreat | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Nuzzle | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Origin Pulse | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Outrage | Physical | multi_turn_or_repeat_chain, side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Overdrive | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Overheat | Special | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Pain Split | Status | side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Parting Shot | Status | forced_move_or_execution_constraint, side_effect | **INEXACT** | switch/force-switch effect is marked without exact resulting state |
| Payback | Physical | dynamic_base_power_or_damage | **INEXACT** | turn/history-conditional power depends on same-turn order/hit/stat-drop or prior-move-failure not plumbed to the oracle; fails closed (batch 4) |
| Petal Blizzard | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Petal Dance | Special | multi_turn_or_repeat_chain, side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Photon Geyser | Special | ordinary_damage | **PASS** | calc selects the higher attacking stat and matching category (verified physical/special); damage is exact (batch 5) |
| Play Rough | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Poison Fang | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Poison Jab | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Pollen Puff | Special | ordinary_damage | **PASS** | singles: Pollen Puff always damages the foe (no ally-heal branch); damage is exact (batch 4) |
| Poltergeist | Physical | forced_move_or_execution_constraint, item_dependent | **INEXACT** | move-success depends on opponent action / first-active turn / form / target item; fails closed rather than assume it hits (batch 4) |
| Population Bomb | Physical | dynamic_base_power_or_damage | **INEXACT** | multi-hit total/distribution fails closed (impact_unknown) in batch 1 |
| Pounce | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Power Gem | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Power Trip | Physical | dynamic_base_power_or_damage | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| Power Whip | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Precipice Blades | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Protect | Status | priority, side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Psyblade | Physical | dynamic_base_power_or_damage, weather_or_terrain | **PASS** | Showdown/sim-core oracle receives the required represented state |
| Psychic | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Psychic Fangs | Physical | ordinary_damage | **INEXACT** | damage is exact (calc bypasses screens); the conditional screen removal is coarsely flagged as a field/side change (batch 4) |
| Psychic Noise | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Psycho Boost | Special | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Psycho Cut | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Psyshock | Special | nonstandard_stat_source | **PASS** | Showdown/sim-core oracle receives the required represented state |
| Psystrike | Special | nonstandard_stat_source | **PASS** | Showdown/sim-core oracle receives the required represented state |
| Pyro Ball | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Quick Attack | Physical | priority | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Quiver Dance | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Rage Fist | Physical | dynamic_base_power_or_damage | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| Raging Bull | Physical | type_dependent | **PASS** | dynamic move type resolved from state via sim-core result.move.type for type-effectiveness and STAB (batch 3) |
| Rain Dance | Status | side_effect, weather_or_terrain | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Rapid Spin | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Razor Shell | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Recover | Status | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Reflect | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Relic Song | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Rest | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Revelation Dance | Special | type_dependent | **PASS** | dynamic move type resolved from state via sim-core result.move.type for type-effectiveness and STAB (batch 3) |
| Revival Blessing | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Roar | Status | forced_move_or_execution_constraint, priority, side_effect | **INEXACT** | switch/force-switch effect is marked without exact resulting state |
| Rock Blast | Physical | dynamic_base_power_or_damage | **INEXACT** | multi-hit total/distribution fails closed (impact_unknown) in batch 1 |
| Rock Polish | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Rock Slide | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Rock Tomb | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Roost | Status | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Ruination | Special | dynamic_base_power_or_damage | **INEXACT** | fixed-damage target/counter context fails closed (impact_unknown) in batch 1 |
| Sacred Fire | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Sacred Sword | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Salt Cure | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Scald | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Scale Shot | Physical | dynamic_base_power_or_damage | **INEXACT** | multi-hit total/distribution fails closed (impact_unknown) in batch 1 |
| Scorching Sands | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Secret Sword | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Seed Bomb | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Seed Flare | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Seismic Toss | Physical | ordinary_damage | **PASS** | fixed level-based damage routed to the oracle (batch 1); honors type immunity |
| Shadow Ball | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Shadow Claw | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Shadow Sneak | Physical | priority | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Shed Tail | Status | forced_move_or_execution_constraint, side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Shell Side Arm | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Shell Smash | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Shift Gear | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Shore Up | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Slack Off | Status | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Sleep Powder | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Sleep Talk | Status | side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Sludge Bomb | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Sludge Wave | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Snowscape | Status | side_effect, weather_or_terrain | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Soft-Boiled | Status | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Solar Beam | Special | dynamic_base_power_or_damage, multi_turn_or_repeat_chain | **INEXACT** | two-turn charge/delayed damage: exact only with sun/Power Herb, fails closed otherwise so immediate timing is not assumed (batch 3) |
| Spacial Rend | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Sparkling Aria | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Spikes | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Spirit Break | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Spirit Shackle | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Spore | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Stealth Rock | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Steam Eruption | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Sticky Web | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Stomping Tantrum | Physical | dynamic_base_power_or_damage | **INEXACT** | turn/history-conditional power depends on same-turn order/hit/stat-drop or prior-move-failure not plumbed to the oracle; fails closed (batch 4) |
| Stone Axe | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Stone Edge | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Stored Power | Special | dynamic_base_power_or_damage | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| Strange Steam | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Strength Sap | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Stun Spore | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Substitute | Status | recoil_drain_crash_or_self_damage, side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Sucker Punch | Physical | forced_move_or_execution_constraint, priority | **INEXACT** | move-success depends on opponent action / first-active turn / form / target item; fails closed rather than assume it hits (batch 4) |
| Sunny Day | Status | side_effect, weather_or_terrain | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Sunsteel Strike | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Super Fang | Physical | dynamic_base_power_or_damage | **INEXACT** | fixed-damage target/counter context fails closed (impact_unknown) in batch 1 |
| Supercell Slam | Physical | recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Superpower | Physical | side_effect | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Surf | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Surging Strikes | Physical | dynamic_base_power_or_damage | **INEXACT** | multi-hit total/distribution fails closed (impact_unknown) in batch 1 |
| Switcheroo | Status | item_dependent, side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Swords Dance | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Synthesis | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Tachyon Cutter | Special | dynamic_base_power_or_damage | **INEXACT** | multi-hit total/distribution fails closed (impact_unknown) in batch 1 |
| Tail Glow | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Tail Slap | Physical | dynamic_base_power_or_damage | **INEXACT** | multi-hit total/distribution fails closed (impact_unknown) in batch 1 |
| Tailwind | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Take Heart | Status | side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Taunt | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Teleport | Status | forced_move_or_execution_constraint, priority, side_effect | **INEXACT** | switch/force-switch effect is marked without exact resulting state |
| Temper Flare | Physical | dynamic_base_power_or_damage | **INEXACT** | turn/history-conditional power depends on same-turn order/hit/stat-drop or prior-move-failure not plumbed to the oracle; fails closed (batch 4) |
| Tera Blast | Special | dynamic_base_power_or_damage, type_dependent | **PASS** | dynamic move type resolved from state via sim-core result.move.type for type-effectiveness and STAB (batch 3) |
| Tera Starstorm | Special | type_dependent | **INEXACT** | Stellar-type STAB/effectiveness not representable by the standard type chart; fails closed (batch 3) |
| Throat Chop | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Thunder | Special | dynamic_accuracy, side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Thunder Punch | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Thunder Wave | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Thunderbolt | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Thunderclap | Special | forced_move_or_execution_constraint, priority | **INEXACT** | move-success depends on opponent action / first-active turn / form / target item; fails closed rather than assume it hits (batch 4) |
| Tidy Up | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Torch Song | Special | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Toxic | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Toxic Spikes | Status | side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Trailblaze | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Transform | Status | side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Tri Attack | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Trick | Status | item_dependent, side_effect | **INEXACT** | non-damaging status transition coarsely flagged (action_non_damaging + next-state change fields, batch 2); item-swap/copy/random-call effects need typed v7 fields |
| Trick Room | Status | priority, side_effect | **INEXACT** | field/side change is marked, but exact layers/duration/success are not resolved |
| Triple Arrows | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Triple Axel | Physical | dynamic_base_power_or_damage | **INEXACT** | multi-hit total/distribution fails closed (impact_unknown) in batch 1 |
| U-turn | Physical | forced_move_or_execution_constraint | **INEXACT** | damage is resolved and switching is flagged, but resulting state is not exact |
| Vacuum Wave | Special | priority | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Victory Dance | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| Volt Switch | Special | forced_move_or_execution_constraint | **INEXACT** | damage is resolved and switching is flagged, but resulting state is not exact |
| Volt Tackle | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Water Pulse | Special | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Water Spout | Special | dynamic_base_power_or_damage, hp_dependent_or_hp_cost | **PASS** | required dynamic dependency is explicitly supplied to Showdown/sim-core |
| Waterfall | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Wave Crash | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Weather Ball | Special | type_dependent, weather_or_terrain | **PASS** | dynamic move type resolved from state via sim-core result.move.type for type-effectiveness and STAB (batch 3) |
| Whirlpool | Special | status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Whirlwind | Status | forced_move_or_execution_constraint, priority, side_effect | **INEXACT** | switch/force-switch effect is marked without exact resulting state |
| Wicked Blow | Physical | ordinary_damage | **PASS** | guaranteed crit is baked into the calc damage rolls; impact reports crit_included=True (batch 5) |
| Wild Charge | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Will-O-Wisp | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Wish | Status | recoil_drain_crash_or_self_damage, side_effect | **INEXACT** | healing is annotated but exact own-HP delta remains unknown |
| Wood Hammer | Physical | hp_dependent_or_hp_cost, recoil_drain_crash_or_self_damage | **INEXACT** | damage is resolved and drawback/heal is flagged, but exact own-HP delta is unknown |
| Work Up | Status | side_effect | **PASS** | deterministic stat/type-dependent effect is represented by existing v6 fields |
| X-Scissor | Physical | ordinary_damage | **PASS** | ordinary conditional-on-hit damage and static accuracy resolve through sim-core |
| Yawn | Status | side_effect, status_dependent_or_inflicting | **INEXACT** | target status/volatile coarsely flagged via next-state change fields (batch 2); exact status type not represented |
| Zen Headbutt | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |
| Zing Zap | Physical | side_effect | **INEXACT** | secondary status/stat/volatile effect coarsely flagged via next-state change fields (batch 2); exact type/chance/magnitude not represented |

## Schema and Gate

No schema field was added or reordered by this audit. v6 remains 331D and the v5 prefix remains unchanged.

Batches 1-5 reduced the wrong-exact set to **zero FAIL**: every material move-impact mechanic is now either PASS or explicitly INEXACT/fail-closed (impact_unknown / coarse next-state annotation). The completeness audit's no-wrong-exact criterion is therefore met. The gate nonetheless remains **closed** pending the separately approval-gated training-readiness review (stale v5/v6 data/checkpoint disposition, value-label quality audit, larger-dataset value learning). Training, rematerialization, checkpoint promotion, and live-default changes must not proceed without that explicit approval. The 212 INEXACT moves rely on fail-closed/coarse encodings; raising any of them to PASS requires the documented v7 typed-effect/timing/item fields, which were not implemented.
