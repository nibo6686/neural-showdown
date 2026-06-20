# Showdown Mechanics Edge-Case Inventory

## Scope

This inventory was generated from the local bundled Pokemon Showdown source and local `sim-core` wrappers. It is an audit artifact only: no schema, live default, checkpoint, dataset, materialization, or training path changed.

- Source files scanned: **155**
- Hook/field occurrences found: **6473**
- Inventory mechanics entries: **75**
- Current action schema: `legal-action-v7` batch 8, 552D
- Current v7 fingerprint: `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`
- Rollout parity baseline: 33 fixtures, 29 PASS / 0 FAIL / 4 GAP

## High-Risk Categories

- dynamic base power / damage: 14 entries
- dynamic type / effectiveness: 9 entries
- ability-triggered prevention/modification: 7 entries
- branch-dependent execution: 7 entries
- no-leakage/public-information concerns: 7 entries
- multi-hit and sequential-hit behavior: 5 entries
- random-call and callable-pool behavior: 5 entries
- residual and end-of-turn effects: 5 entries

The highest-risk Gen 9 gaps cluster around state/provenance and rollout/search, not additional action labels. Sleep/Rest counters, confusion counters, Future Sight landing damage, binding provenance, Magic Bounce reflection, Good as Gold routing, counter-style damage, and item-triggered switch branches all need public-state provenance or branch evaluation before they can be safely resolved.

## Top 20 Recommended Next Actions

1. **Future Sight delayed slot damage** (`future-sight`) -> rollout parity batch 5 [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Scheduling parity exists; replacement damage must use landing target state, not original stale damage.
2. **Binding/partial trapping duration and source** (`residual-format-partiallytrapped-0`) -> rollout parity batch 5 [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Needs source activity/effect, duration, and Binding Band divisor.
3. **Good as Gold status move blocking** (`switch-prevention-goodasgold`) -> rollout parity batch 5 [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Needs reliable ability provenance and generalized status callback routing.
4. **Magic Bounce reflection** (`switch-prevention-magicbounce`) -> rollout parity batch 5 [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Needs reflected action target and side-effect provenance.
5. **Confusion duration/range and self-hit branch** (`confusion-counter`) -> state-schema/provenance design [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Confusion duration is hidden; current action features do not expose elapsed/range or 33% self-hit branch state.
6. **Beat Up party-member damage** (`dynamic-damage-beatup`) -> state-schema/provenance design [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Depends on party composition and per-ally Attack stats; current impact fails closed.
7. **Bide stored damage release** (`dynamic-damage-bide`) -> state-schema/provenance design [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Depends on damage accumulated over prior turns.
8. **Counter received physical damage** (`dynamic-damage-counter`) -> state-schema/provenance design [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Depends on same-turn/last damage source and amount.
9. **Metal Burst received damage** (`dynamic-damage-metalburst`) -> state-schema/provenance design [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Depends on same-turn damage and move order.
10. **Mirror Coat received special damage** (`dynamic-damage-mirrorcoat`) -> state-schema/provenance design [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Depends on same-turn/last damage source and amount.
11. **live state extraction provenance** (`local-wrapper-state_extractor`) -> state-schema/provenance design [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Many gaps are not action features; they require reliable public/private state extraction.
12. **Rest fixed sleep provenance** (`rest-fixed-sleep`) -> state-schema/provenance design [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Rest overwrites sleep duration; model needs public Rest provenance separate from natural hidden duration.
13. **Natural sleep counter/range** (`sleep-natural-counter`) -> state-schema/provenance design [high]
   Needs: state/provenance feature, rollout parity fixture. Reason: Showdown samples hidden sleep duration; features must expose public elapsed/range, not sampled future wake turn.
14. **Sheer Force secondary removal and power boost** (`secondary-sheerforce`) -> v7 batch 9 [high]
   Needs: v7 action feature, rollout parity fixture. Reason: Need ensure damage estimates include Sheer Force power and no secondary side effects.
15. **Powder Fire-move prevention** (`branch-powder`) -> rollout parity batch 5 [medium]
   Needs: state/provenance feature, rollout parity fixture. Reason: Needs volatile prevention callback routing for Fire moves.
16. **Sucker Punch target-action branch** (`branch-suckerpunch`) -> rollout parity batch 5 [medium]
   Needs: rollout parity fixture, future search/branch evaluation. Reason: Feature marks pressure but search/rollout still needs branch evaluation.
17. **Thunderclap target-action branch** (`branch-thunderclap`) -> rollout parity batch 5 [medium]
   Needs: rollout parity fixture, future search/branch evaluation. Reason: Same target-action condition as Sucker Punch with priority context.
18. **Population Bomb sequential multiaccuracy** (`call-multihit-populationbomb`) -> rollout parity batch 5 [medium]
   Needs: rollout parity fixture. Reason: Features summarize expected hit count but rollout needs distribution fixture.
19. **Triple Axel sequential hit power ramp** (`call-multihit-tripleaxel`) -> rollout parity batch 5 [medium]
   Needs: rollout parity fixture. Reason: Needs fixture for miss-stop and per-hit power ramp.
20. **Doom Desire delayed slot damage** (`doom-desire`) -> rollout parity batch 5 [medium]
   Needs: state/provenance feature, rollout parity fixture. Reason: Shares Future Sight queue and target-slot semantics; landing damage provenance still missing generally.

## Gen 9 vs NatDex / Old-Gen Split

- Gen 9 high/medium relevance: 63 entries
- NatDex/future-format high/medium relevance: 75 entries
- Old-gen high/medium relevance: 36 entries

Current implementation work should stay Gen 9 Random Battles scoped. Pursuit, Assist, Natural Gift, Hidden Power, old-gen partial trapping, old-gen recharge, old-gen Explosion, and old-gen crit quirks are explicitly deferred to format-scoped adapters or NatDex/old-gen backlog.

## Inventory By Category

### ability-triggered prevention/modification
- **Good as Gold status move blocking** (`switch-prevention-goodasgold`) [high] - sim-core/node_modules/pokemon-showdown/data/abilities.ts:1571; hook `onTryHit`; v7 `partial/no; known rollout GAP`; rollout `no`; next `rollout parity batch 5`. Needs reliable ability provenance and generalized status callback routing.
- **Magic Bounce reflection** (`switch-prevention-magicbounce`) [high] - sim-core/node_modules/pokemon-showdown/data/abilities.ts:2380; hook `onTryHit`; v7 `partial/no; known rollout GAP`; rollout `no`; next `rollout parity batch 5`. Needs reflected action target and side-effect provenance.
- **Bulletproof bullet-move immunity** (`switch-prevention-bulletproof`) [medium] - sim-core/node_modules/pokemon-showdown/data/abilities.ts:474; hook `onTryHit`; v7 `partial; coarse blocker exists`; rollout `partial`; next `rollout parity batch 5`. Needs generalized flag-based prevention fixtures.
- **Soundproof sound-move immunity** (`switch-prevention-soundproof`) [medium] - sim-core/node_modules/pokemon-showdown/data/abilities.ts:4350; hook `onTryHit`; v7 `partial; coarse blocker exists`; rollout `partial`; next `rollout parity batch 5`. Needs generalized flag-based prevention fixtures beyond coarse tactical blocker.
- **Damp Explosion prevention** (`switch-prevention-damp`) [low] - sim-core/node_modules/pokemon-showdown/data/abilities.ts:809; hook `onAnyTryMove`; v7 `partial; prevention helper covers represented state`; rollout `partial`; next `no action now`. Existing parity passes Damp Explosion; keep regression.
- **Misty/Electric Terrain status prevention** (`terrain-status-prevention`) [low] - sim-core/node_modules/pokemon-showdown/data/mods/gen9ssb/conditions.ts:2556; hook `onSetStatus / terrain condition`; v7 `partial; status action effects exist, prevention is rollout`; rollout `yes`; next `no action now`. Current parity passes selected terrain prevention; keep expanding only if new callbacks appear.
- **Psychic Terrain priority prevention** (`priority-psychic-terrain`) [low] - sim-core/node_modules/pokemon-showdown/data/mods/gen9ssb/conditions.ts:2552; hook `onTryHit / terrain condition`; v7 `yes; priority/timing and branch risk fields`; rollout `yes`; next `no action now`. Already has fixed fixtures for grounded priority prevention; keep as regression coverage.

### accuracy / priority / target validity
- **Powder Fire-move prevention** (`branch-powder`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:3074; hook `onTry / onTryHit / condition`; v7 `partial; volatile pressure only`; rollout `no`; next `rollout parity batch 5`. Needs volatile prevention callback routing for Fire moves.
- **Primordial Sea / Desolate Land weather prevention** (`weather-primordial-sea`) [medium] - sim-core/node_modules/pokemon-showdown/data/abilities.ts:925; hook `onSetWeather / onTryMove`; v7 `partial; weather fields exist but primal weather prevention/attack nullification is not fully modeled`; rollout `no`; next `rollout parity batch 5`. Harsh weather can block Fire/Water moves and weather replacement; needs field provenance in rollout/search.
- **Misty/Electric Terrain status prevention** (`terrain-status-prevention`) [low] - sim-core/node_modules/pokemon-showdown/data/mods/gen9ssb/conditions.ts:2556; hook `onSetStatus / terrain condition`; v7 `partial; status action effects exist, prevention is rollout`; rollout `yes`; next `no action now`. Current parity passes selected terrain prevention; keep expanding only if new callbacks appear.
- **Psychic Terrain priority prevention** (`priority-psychic-terrain`) [low] - sim-core/node_modules/pokemon-showdown/data/mods/gen9ssb/conditions.ts:2552; hook `onTryHit / terrain condition`; v7 `yes; priority/timing and branch risk fields`; rollout `yes`; next `no action now`. Already has fixed fixtures for grounded priority prevention; keep as regression coverage.

### branch-dependent execution
- **Confusion duration/range and self-hit branch** (`confusion-counter`) [high] - sim-core/node_modules/pokemon-showdown/data/conditions.ts:163; hook `onBeforeMove / random duration`; v7 `partial; confusion chance exists, current counter/range is missing`; rollout `no`; next `state-schema/provenance design`. Confusion duration is hidden; current action features do not expose elapsed/range or 33% self-hit branch state.
- **Fake Out first-active-turn condition** (`branch-fakeout`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:5272; hook `onTry / onTryHit / condition`; v7 `yes; active-turn branch`; rollout `no`; next `state-schema/provenance design`. Needs active-turn counter/provenance to resolve exact legality/success.
- **First Impression first-active-turn condition** (`branch-firstimpression`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:5670; hook `onTry / onTryHit / condition`; v7 `yes; active-turn branch`; rollout `no`; next `state-schema/provenance design`. Same first-active-turn provenance need as Fake Out.
- **Focus Punch lost-focus branch** (`branch-focuspunch`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:6211; hook `onTry / onTryHit / condition`; v7 `partial; opponent-action pressure only`; rollout `no`; next `state-schema/provenance design`. Needs within-turn damage/lost-focus provenance.
- **Sucker Punch target-action branch** (`branch-suckerpunch`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:19105; hook `onTry / onTryHit / condition`; v7 `yes; branch pressure fields`; rollout `no`; next `rollout parity batch 5`. Feature marks pressure but search/rollout still needs branch evaluation.
- **Thunderclap target-action branch** (`branch-thunderclap`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:20256; hook `onTry / onTryHit / condition`; v7 `yes; branch pressure fields`; rollout `no`; next `rollout parity batch 5`. Same target-action condition as Sucker Punch with priority context.
- **Pursuit target-switch old/NatDex behavior** (`branch-pursuit`) [low] - sim-core/node_modules/pokemon-showdown/data/moves.ts:14888; hook `onTry / onTryHit / condition`; v7 `partial; batch 7 marks future-format pressure`; rollout `no`; next `deferred NatDex/old-gen backlog`. Absent from current Gen 9 Randbats but important for NatDex/old-gen adapters.

### crit chance and crit rules
- **Guaranteed crit moves** (`secondary-flowertrick`) [low] - sim-core/node_modules/pokemon-showdown/data/moves.ts:6087; hook `willCrit / critRatio`; v7 `yes; guaranteed_crit`; rollout `no`; next `no action now`. Batch 7 distinguishes guaranteed from ordinary crit.
- **Old-gen crit quirks** (`residual-format-focusenergy-6`) [low] - sim-core/node_modules/pokemon-showdown/data/mods/gen1/scripts.ts:8; hook `onModifyCritRatio / gen mods`; v7 `no; current crit fields Gen 9 scoped`; rollout `no`; next `deferred NatDex/old-gen backlog`. Old-gen crit stages and Focus Energy quirks are not current target.

### delayed damage/future effects
- **Future Sight delayed slot damage** (`future-sight`) [high] - sim-core/node_modules/pokemon-showdown/data/moves.ts:6615; hook `flags.futuremove / onTry`; v7 `partial; action delayed pressure exists, landing damage remains rollout/state`; rollout `partial`; next `rollout parity batch 5`. Scheduling parity exists; replacement damage must use landing target state, not original stale damage.
- **Doom Desire delayed slot damage** (`doom-desire`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:3982; hook `flags.futuremove / onTry`; v7 `partial; same as Future Sight`; rollout `partial`; next `rollout parity batch 5`. Shares Future Sight queue and target-slot semantics; landing damage provenance still missing generally.

### dynamic base power / damage
- **Beat Up party-member damage** (`dynamic-damage-beatup`) [high] - sim-core/node_modules/pokemon-showdown/data/moves.ts:1192; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `state-schema/provenance design`. Depends on party composition and per-ally Attack stats; current impact fails closed.
- **Bide stored damage release** (`dynamic-damage-bide`) [high] - sim-core/node_modules/pokemon-showdown/data/moves.ts:1309; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `state-schema/provenance design`. Depends on damage accumulated over prior turns.
- **Counter received physical damage** (`dynamic-damage-counter`) [high] - sim-core/node_modules/pokemon-showdown/data/moves.ts:347; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `state-schema/provenance design`. Depends on same-turn/last damage source and amount.
- **Metal Burst received damage** (`dynamic-damage-metalburst`) [high] - sim-core/node_modules/pokemon-showdown/data/moves.ts:12069; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `state-schema/provenance design`. Depends on same-turn damage and move order.
- **Mirror Coat received special damage** (`dynamic-damage-mirrorcoat`) [high] - sim-core/node_modules/pokemon-showdown/data/moves.ts:12420; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `state-schema/provenance design`. Depends on same-turn/last damage source and amount.
- **Electro Ball speed-ratio power** (`dynamic-damage-electroball`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:4753; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `v7 batch 9`. Depends on speed ratio and current modifiers.
- **Fickle Beam random double power** (`dynamic-damage-ficklebeam`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:5410; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `v7 batch 9`. Random power branch should be distribution/provenance, not deterministic damage.
- **Grass Knot / Low Kick weight power** (`dynamic-damage-grassknot`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:7812; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `v7 batch 9`. Depends on target weight and possibly form/known species.
- **Gyro Ball speed-ratio power** (`dynamic-damage-gyroball`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:8333; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `v7 batch 9`. Depends on speed stats, boosts, items and field.
- **Heavy Slam / Heat Crash weight-ratio power** (`dynamic-damage-heavyslam`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:8829; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `v7 batch 9`. Depends on both weights and target state.
- **Last Respects fainted-ally power** (`dynamic-damage-lastrespects`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:10462; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `v7 batch 9`. Depends on allied faint count and battle history provenance.
- **Rage Fist times-hit power** (`dynamic-damage-ragefist`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:15116; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `v7 batch 9`. Requires public times-attacked history to avoid stale 50 BP damage.
- **Reversal / Flail HP power** (`dynamic-damage-reversal`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:15637; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `v7 batch 9`. Depends on exact current user HP bracket.
- **Stored Power / Power Trip boost count power** (`dynamic-damage-storedpower`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:18804; hook `basePowerCallback / damageCallback / onHit`; v7 `partial; many fail closed or use exact context where available`; rollout `no`; next `v7 batch 9`. Depends on current positive boosts and exact boost state.

### dynamic type / effectiveness
- **Primordial Sea / Desolate Land weather prevention** (`weather-primordial-sea`) [medium] - sim-core/node_modules/pokemon-showdown/data/abilities.ts:925; hook `onSetWeather / onTryMove`; v7 `partial; weather fields exist but primal weather prevention/attack nullification is not fully modeled`; rollout `no`; next `rollout parity batch 5`. Harsh weather can block Fire/Water moves and weather replacement; needs field provenance in rollout/search.
- **Salt Cure residual normal/Water/Steel** (`salt-cure`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:16213; hook `volatileStatus / condition.onResidual`; v7 `partial; residual pressure exists, exact current-state residual is rollout`; rollout `yes`; next `state-schema/provenance design`. Parity passes for represented state; broader adapters need source/effect identity and current target typing.
- **Tera Blast current Tera type/category** (`dynamic-type-terablast`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:19950; hook `onModifyType / onEffectiveness / overrideOffensiveStat`; v7 `partial; exact impact handles some cases, schema lacks some provenance`; rollout `partial`; next `v7 batch 9`. Source contains generation- and state-sensitive type/effectiveness behavior that should stay Showdown-format scoped.
- **Terrain Pulse grounded type/power** (`dynamic-type-terrainpulse`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:20013; hook `onModifyType / onEffectiveness / overrideOffensiveStat`; v7 `partial; exact impact handles some cases, schema lacks some provenance`; rollout `partial`; next `rollout parity batch 5`. Source contains generation- and state-sensitive type/effectiveness behavior that should stay Showdown-format scoped.
- **Weather Ball type/power** (`dynamic-type-weatherball`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:21498; hook `onModifyType / onEffectiveness / overrideOffensiveStat`; v7 `partial; exact impact handles some cases, schema lacks some provenance`; rollout `partial`; next `rollout parity batch 5`. Source contains generation- and state-sensitive type/effectiveness behavior that should stay Showdown-format scoped.
- **Freeze-Dry Water effectiveness override** (`dynamic-type-freezedry`) [low] - sim-core/node_modules/pokemon-showdown/data/moves.ts:6373; hook `onModifyType / onEffectiveness / overrideOffensiveStat`; v7 `partial; exact impact handles some cases, schema lacks some provenance`; rollout `partial`; next `no action now`. Source contains generation- and state-sensitive type/effectiveness behavior that should stay Showdown-format scoped.
- **Hidden Power type generation/formats** (`dynamic-type-hiddenpower`) [low] - sim-core/node_modules/pokemon-showdown/data/moves.ts:8927; hook `onModifyType / onEffectiveness / overrideOffensiveStat`; v7 `partial; exact impact handles some cases, schema lacks some provenance`; rollout `partial`; next `deferred NatDex/old-gen backlog`. Source contains generation- and state-sensitive type/effectiveness behavior that should stay Showdown-format scoped.
- **Natural Gift berry type/power** (`dynamic-type-naturalgift`) [low] - sim-core/node_modules/pokemon-showdown/data/moves.ts:13012; hook `onModifyType / onEffectiveness / overrideOffensiveStat`; v7 `partial; exact impact handles some cases, schema lacks some provenance`; rollout `partial`; next `deferred NatDex/old-gen backlog`. Source contains generation- and state-sensitive type/effectiveness behavior that should stay Showdown-format scoped.
- **Photon Geyser offensive stat/category override** (`dynamic-type-photongeyser`) [low] - sim-core/node_modules/pokemon-showdown/data/moves.ts:13809; hook `onModifyType / onEffectiveness / overrideOffensiveStat`; v7 `partial; exact impact handles some cases, schema lacks some provenance`; rollout `partial`; next `no action now`. Source contains generation- and state-sensitive type/effectiveness behavior that should stay Showdown-format scoped.

### format/generation overrides
- **Feint Gen 9 Protect-breaking behavior** (`branch-feint`) [low] - sim-core/node_modules/pokemon-showdown/data/moves.ts:5362; hook `onTry / onTryHit / condition`; v7 `yes; not treated as old-gen branch`; rollout `no`; next `format-scoped adapter`. Current Gen 9 behavior differs from older assumptions; keep format-scoped.
- **Old-gen Explosion defense/crit/self-KO quirks** (`residual-format-explosion-3`) [low] - sim-core/node_modules/pokemon-showdown/data/mods/gen1/moves.ts:307; hook `selfdestruct / gen mods`; v7 `yes for Gen 9 self-KO; old-gen quirks deferred`; rollout `partial`; next `deferred NatDex/old-gen backlog`. Gen 1-4 Explosion and crit behavior are future-format notes only.
- **Old-gen partial trapping lock behavior** (`residual-format-partiallytrapped-5`) [low] - sim-core/node_modules/pokemon-showdown/data/mods/gen1/conditions.ts:186; hook `onBeforeMove / residual`; v7 `no; current binding only pressure`; rollout `no`; next `deferred NatDex/old-gen backlog`. Old-gen partial trapping differs radically and should stay format-scoped.
- **Old-gen recharge quirks** (`residual-format-hyperbeam-4`) [low] - sim-core/node_modules/pokemon-showdown/data/mods/gen1/scripts.ts:135; hook `mustrecharge / gen mods`; v7 `partial; recharge timing fields exist for current gen`; rollout `no`; next `deferred NatDex/old-gen backlog`. Old-gen recharge behavior belongs in generation adapter, not current Gen 9 schema.

### item-triggered effects
- **Eject Button hit-triggered switch** (`switch-prevention-ejectbutton`) [medium] - sim-core/node_modules/pokemon-showdown/data/items.ts:1543; hook `onAfterMoveSecondary`; v7 `yes when known item`; rollout `partial`; next `rollout parity batch 5`. Needs branch fixture for item-triggered switch after damage.
- **Eject Pack stat-drop switch** (`switch-prevention-ejectpack`) [medium] - sim-core/node_modules/pokemon-showdown/data/items.ts:1568; hook `onAfterBoost`; v7 `yes when known item`; rollout `partial`; next `rollout parity batch 5`. Needs stat-drop trigger and suppression provenance.
- **Red Card forced target switch** (`switch-prevention-redcard`) [medium] - sim-core/node_modules/pokemon-showdown/data/items.ts:4746; hook `onAfterMoveSecondary`; v7 `yes when known item`; rollout `partial`; next `rollout parity batch 5`. Needs forced random replacement branch fixture.

### multi-hit and sequential-hit behavior
- **Loaded Dice multi-hit modification** (`multihit-loadeddice`) [medium] - sim-core/node_modules/pokemon-showdown/data/items.ts:3155; hook `onModifyMove`; v7 `yes when known item`; rollout `no`; next `rollout parity batch 5`. Changes 2-5 and Population Bomb hit distribution when item known.
- **Population Bomb sequential multiaccuracy** (`call-multihit-populationbomb`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:14103; hook `multihit / multiaccuracy / onHit`; v7 `yes; batch 7 sequential distribution`; rollout `no`; next `rollout parity batch 5`. Features summarize expected hit count but rollout needs distribution fixture.
- **Skill Link max-hit guarantee** (`multihit-skilllink`) [medium] - sim-core/node_modules/pokemon-showdown/data/abilities.ts:4211; hook `onModifyMove`; v7 `yes when known ability`; rollout `no`; next `rollout parity batch 5`. Forces max hits and removes multiaccuracy when ability known.
- **Triple Axel sequential hit power ramp** (`call-multihit-tripleaxel`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:20785; hook `multihit / multiaccuracy / onHit`; v7 `yes; batch 7 sequential and per-hit power fields`; rollout `no`; next `rollout parity batch 5`. Needs fixture for miss-stop and per-hit power ramp.
- **2-5 hit distribution** (`call-multihit-bulletseed`) [low] - sim-core/node_modules/pokemon-showdown/data/moves.ts:2072; hook `multihit / multiaccuracy / onHit`; v7 `yes; batch 7 distribution`; rollout `no`; next `rollout parity batch 5`. Feature has distribution summary; exact rollout can stay future unless decision impact needs it.

### no-leakage/public-information concerns
- **Confusion duration/range and self-hit branch** (`confusion-counter`) [high] - sim-core/node_modules/pokemon-showdown/data/conditions.ts:163; hook `onBeforeMove / random duration`; v7 `partial; confusion chance exists, current counter/range is missing`; rollout `no`; next `state-schema/provenance design`. Confusion duration is hidden; current action features do not expose elapsed/range or 33% self-hit branch state.
- **Future Sight delayed slot damage** (`future-sight`) [high] - sim-core/node_modules/pokemon-showdown/data/moves.ts:6615; hook `flags.futuremove / onTry`; v7 `partial; action delayed pressure exists, landing damage remains rollout/state`; rollout `partial`; next `rollout parity batch 5`. Scheduling parity exists; replacement damage must use landing target state, not original stale damage.
- **Natural sleep counter/range** (`sleep-natural-counter`) [high] - sim-core/node_modules/pokemon-showdown/data/conditions.ts:47; hook `onBeforeMove / random duration`; v7 `no; action features can cause sleep but current-state counter/range is not in action v7`; rollout `no`; next `state-schema/provenance design`. Showdown samples hidden sleep duration; features must expose public elapsed/range, not sampled future wake turn.
- **Rest fixed sleep provenance** (`rest-fixed-sleep`) [high] - sim-core/node_modules/pokemon-showdown/data/moves.ts:351; hook `onHit / statusState.time`; v7 `partial; move sleep effect exists but Rest-vs-natural sleep provenance is state-level`; rollout `no`; next `state-schema/provenance design`. Rest overwrites sleep duration; model needs public Rest provenance separate from natural hidden duration.
- **live state extraction provenance** (`local-wrapper-state_extractor`) [high] - sim-core/src/state_extractor.ts:1; hook `local sim-core wrapper`; v7 `not directly`; rollout `partial`; next `state-schema/provenance design`. Many gaps are not action features; they require reliable public/private state extraction.
- **rollout parity oracle fixtures** (`local-wrapper-rollout_parity_oracle`) [medium] - sim-core/src/rollout_parity_oracle.ts:1; hook `local sim-core wrapper`; v7 `not directly`; rollout `partial`; next `rollout parity batch 5`. Local fixtures should expand only where represented state/provenance is available.
- **sim-core damage calculator wrapper** (`local-wrapper-damage_calc`) [medium] - sim-core/src/damage_calc.ts:1; hook `local sim-core wrapper`; v7 `not directly`; rollout `partial`; next `v7 batch 9`. Wrapper can omit dynamic callbacks unless explicitly plumbed; keep audit tests tied to Showdown source.

### random-call and callable-pool behavior
- **Copycat last-move callable** (`call-multihit-copycat`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:639; hook `multihit / multiaccuracy / onHit`; v7 `partial; dependency flag only`; rollout `no`; next `state-schema/provenance design`. Requires reliable last-move provenance and format exclusions.
- **Metronome format callable pool** (`call-multihit-metronome`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:29; hook `multihit / multiaccuracy / onHit`; v7 `yes; batch 7 pool summary`; rollout `no`; next `format-scoped adapter`. Pool must remain format-scoped and not leak sampled called move.
- **Sleep Talk current move callable pool** (`call-multihit-sleeptalk`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:639; hook `multihit / multiaccuracy / onHit`; v7 `yes when current moves known`; rollout `no`; next `state-schema/provenance design`. Needs sleep-state and known move-slot provenance; do not sample future called move.
- **Assist party callable pool** (`call-multihit-assist`) [low] - sim-core/node_modules/pokemon-showdown/data/moves.ts:630; hook `multihit / multiaccuracy / onHit`; v7 `partial; batch 7 marks party/format dependency`; rollout `no`; next `deferred NatDex/old-gen backlog`. Absent from current Gen 9 Randbats but important for NatDex/Assist-abuse teams.
- **Mirror Move target last move** (`call-multihit-mirrormove`) [low] - sim-core/node_modules/pokemon-showdown/data/moves.ts:12465; hook `multihit / multiaccuracy / onHit`; v7 `partial; dependency flag only`; rollout `no`; next `deferred NatDex/old-gen backlog`. Mostly future-format; needs target last-move provenance.

### residual and end-of-turn effects
- **Binding/partial trapping duration and source** (`residual-format-partiallytrapped-0`) [high] - sim-core/node_modules/pokemon-showdown/data/conditions.ts:223; hook `onResidual`; v7 `partial; binding pressure only`; rollout `no; known GAP`; next `rollout parity batch 5`. Needs source activity/effect, duration, and Binding Band divisor.
- **Salt Cure residual normal/Water/Steel** (`salt-cure`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:16213; hook `volatileStatus / condition.onResidual`; v7 `partial; residual pressure exists, exact current-state residual is rollout`; rollout `yes`; next `state-schema/provenance design`. Parity passes for represented state; broader adapters need source/effect identity and current target typing.
- **Toxic ramping** (`toxic-ramp`) [medium] - sim-core/node_modules/pokemon-showdown/data/conditions.ts:139; hook `onResidual`; v7 `partial; action status chance exists, current toxic stage is state/rollout`; rollout `yes`; next `state-schema/provenance design`. Rollout batch 1 covers fixture parity when toxic stage is available; adapter still needs robust stage provenance.
- **Grassy Terrain end-of-turn healing** (`residual-format-grassyterrain-2`) [low] - sim-core/node_modules/pokemon-showdown/data/mods/gen9ssb/conditions.ts:2554; hook `onResidual`; v7 `partial; rollout not action schema`; rollout `yes`; next `no action now`. Batch 4 rollout parity covers grounded and airborne no-heal fixtures.
- **Sandstorm residual** (`residual-format-sandstorm-1`) [low] - sim-core/node_modules/pokemon-showdown/data/conditions.ts:624; hook `onResidual`; v7 `partial; rollout not action schema`; rollout `yes`; next `no action now`. Fixture already passes ordinary sandstorm chip for represented state.

### secondary effects and secondary modifiers
- **Sheer Force secondary removal and power boost** (`secondary-sheerforce`) [high] - sim-core/node_modules/pokemon-showdown/data/abilities.ts:148; hook `onBasePower / hasSheerForceBoost`; v7 `partial; batch 8 marks secondary removal, damage power interaction needs audit`; rollout `no`; next `v7 batch 9`. Need ensure damage estimates include Sheer Force power and no secondary side effects.
- **Covert Cloak secondary blocking** (`secondary-covertcloak`) [medium] - sim-core/node_modules/pokemon-showdown/data/items.ts:1147; hook `onModifySecondaries`; v7 `yes when known target item`; rollout `no`; next `rollout parity batch 5`. Feature provenance exists; transition tests should verify blocking.
- **Serene Grace secondary chance modifier** (`secondary-serenegrace`) [medium] - sim-core/node_modules/pokemon-showdown/data/abilities.ts:4042; hook `onModifyMove`; v7 `yes; batch 8 modifier fields`; rollout `no`; next `rollout parity batch 5`. Features now expose modified chance; rollout/search still should verify outcome provenance.
- **Shield Dust secondary blocking** (`secondary-shielddust`) [medium] - sim-core/node_modules/pokemon-showdown/data/abilities.ts:3278; hook `onModifySecondaries`; v7 `yes when known target ability`; rollout `no`; next `rollout parity batch 5`. Feature provenance exists; transition tests should verify blocking.

### status and volatile counters
- **Confusion duration/range and self-hit branch** (`confusion-counter`) [high] - sim-core/node_modules/pokemon-showdown/data/conditions.ts:163; hook `onBeforeMove / random duration`; v7 `partial; confusion chance exists, current counter/range is missing`; rollout `no`; next `state-schema/provenance design`. Confusion duration is hidden; current action features do not expose elapsed/range or 33% self-hit branch state.
- **Natural sleep counter/range** (`sleep-natural-counter`) [high] - sim-core/node_modules/pokemon-showdown/data/conditions.ts:47; hook `onBeforeMove / random duration`; v7 `no; action features can cause sleep but current-state counter/range is not in action v7`; rollout `no`; next `state-schema/provenance design`. Showdown samples hidden sleep duration; features must expose public elapsed/range, not sampled future wake turn.
- **Rest fixed sleep provenance** (`rest-fixed-sleep`) [high] - sim-core/node_modules/pokemon-showdown/data/moves.ts:351; hook `onHit / statusState.time`; v7 `partial; move sleep effect exists but Rest-vs-natural sleep provenance is state-level`; rollout `no`; next `state-schema/provenance design`. Rest overwrites sleep duration; model needs public Rest provenance separate from natural hidden duration.
- **Toxic ramping** (`toxic-ramp`) [medium] - sim-core/node_modules/pokemon-showdown/data/conditions.ts:139; hook `onResidual`; v7 `partial; action status chance exists, current toxic stage is state/rollout`; rollout `yes`; next `state-schema/provenance design`. Rollout batch 1 covers fixture parity when toxic stage is available; adapter still needs robust stage provenance.

### switch / drag / pivot / forced replacement
- **Phazing forced target switch** (`switch-prevention-roar`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:11587; hook `forceSwitch / drag`; v7 `yes; batch 8`; rollout `partial`; next `rollout parity batch 5`. Features pressure; rollout/search must model random replacement branch.
- **Self-KO sacrifice replacement** (`switch-prevention-memento`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:12032; hook `selfdestruct`; v7 `yes; batch 8`; rollout `partial`; next `rollout parity batch 5`. Needs transition/replacement fixture for sacrifice tempo.
- **Self-pivot follow-up replacement** (`switch-prevention-uturn`) [medium] - sim-core/node_modules/pokemon-showdown/data/moves.ts:20974; hook `selfSwitch`; v7 `yes; batch 8`; rollout `partial`; next `state-schema/provenance design`. Action label remains U-turn; replacement is later forced decision.

## Source Scan Summary

Top hook occurrence counts:
- `flags`: 2066
- `secondary`: 1205
- `condition`: 444
- `onHit`: 391
- `volatileStatus`: 287
- `onBasePower`: 207
- `onPrepareHit`: 200
- `onTryHit`: 178
- `onFaint`: 164
- `onSwitchOut`: 159
- `onModifyMove`: 147
- `secondaries`: 141
- `onResidual`: 132
- `critRatio`: 112
- `multihit`: 107
- `onTry`: 86
- `onBeforeMove`: 76
- `onSwitchIn`: 67
- `onModifyType`: 43
- `onDisableMove`: 36

The full per-file hook counts and machine-readable classifications are in `showdown_mechanics_edge_case_inventory.json`.
