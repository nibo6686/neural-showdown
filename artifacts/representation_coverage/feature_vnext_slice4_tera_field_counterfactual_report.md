# Slice 4 Tera/Field Counterfactual Report

**Version:** `live-private-belief-v6`  
**Dimension:** 2493  
**Method:** synthetic, protocol-faithful isolated mutations

## Tera results

| Comparison | Distinguishing proof |
| --- | --- |
| Own available vs unavailable | availability enum and Tera-action availability differ |
| Own Tera vs not Tera | active state, Tera type, current-type source and Tera-current flag differ |
| Own Fire vs Water Tera | Tera-type and current-type fields differ |
| Opponent revealed Tera vs not | opponent active/availability/type/provenance fields differ |
| Base/current vs Tera-current typing | base type remains stable while current type/source and Tera-current flag change |

The Fire-versus-Water fixture changes four identity fields:

- current Fire/Water type;
- active Fire/Water Tera type.

## Global field results

| Comparison | Distinguishing proof |
| --- | --- |
| None vs rain | weather enum and public elapsed evidence differ |
| Rain vs sun | explicit rain/sun enum positions differ |
| No terrain vs Electric Terrain | terrain enum and public elapsed evidence differ |
| Trick Room inactive vs active | dedicated state and elapsed fields differ |

Gravity, Magic Room and Wonder Room use the same dedicated state/elapsed
structure and are covered by focused tests.

## Side-condition results

Reflect, Light Screen and Tailwind have separate own/opponent state and elapsed
fields. Perspective checks prove that physical p1 conditions map to:

- `own_*` under p1;
- `opponent_*` under p2.

The same check passes for Stealth Rock.

## Hazard results

| Comparison | Distinguishing proof |
| --- | --- |
| One vs two Spikes layers | exact layer enum changes from 1 to 2 |
| One vs two Toxic Spikes layers | exact layer enum changes from 1 to 2 |
| Sticky Web inactive vs active | dedicated state enum changes |
| Own vs opponent Stealth Rock | relative side fields swap |

## Limitations

- Fixtures are synthetic public protocol transitions rather than full seeded
  move searches.
- Duration values are public elapsed evidence, not hidden exact remaining turns.
- Opponent unused Tera type/availability remains unknown.
- Weather state includes an `other` bucket for supported weather outside the
  named Gen 9 core set.
- This slice does not train or evaluate a v6 model.
