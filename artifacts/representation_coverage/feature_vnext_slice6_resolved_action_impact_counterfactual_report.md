# Slice 6 Resolved Action Impact Counterfactual Report

**Date:** 2026-06-19  
**Schema:** `legal-action-v5`, 318D; exact 269D v4 prefix  
**Result:** 10/10 controlled comparisons changed the intended feature set

| Counterfactual | Passing evidence |
| --- | --- |
| Damaging vs non-damaging | Psychic has positive expected damage; Calm Mind has known-zero damage and `impact_method_non_damaging=1`. |
| Immune vs non-immune | Earthquake into Flying is immune with zero expected damage. |
| Resisted vs super-effective | Psychic distinguishes Steel/Psychic resistance from Fighting weakness. |
| Soak/current type | Thunderbolt into mono-Normal Eevee changes from 0.552 expected fraction to clipped 1.0 after diagnostic pure-Water override. |
| Tera/current type | Surf changes from super-effective into Charizard to resisted into current pure-Water typing. |
| Stat stage | Psychic expected damage falls from 0.428 to 0.215 after own SpA -2. |
| Light Screen | Psychic expected damage falls from 0.428 to 0.213 through opponent `side_conditions`. |
| Draco versus no-drawback analog | Draco exposes 0.617 immediate expected damage and exact v4 `self_stat_delta_spa=-1.0`; Psyshock has 0.399 and zero self-SpA delta. |
| Switch action | Switch is non-damaging, explicitly unavailable for damage, and retains the v4 switch command/target fields. |
| Accuracy | Psychic exposes 1.0 hit chance; Focus Blast exposes 0.7. |

The Soak case intentionally uses a mono-type target because the calculator's
array deep merge cannot reliably replace a dual-type array with a one-type
override. These are representation counterfactuals, not tactical preference
rules. They do not train a model or change live scoring.
