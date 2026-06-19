# Slice 3 Species/Status Counterfactual Report

**Version:** `live-private-belief-v5`  
**Dimension:** 2293  
**Method:** synthetic, protocol-faithful isolated mutations

## Species and roster results

| Comparison | v5 proof |
| --- | --- |
| Own Pikachu vs Raichu | Base/current/displayed active hashes and roster-slot hashes differ |
| Opponent Charizard vs Dragonite | Opponent active and roster identity hashes differ |
| Ditto before/after Transform | Base Ditto hashes remain; current/displayed hashes change to Garchomp; `transformed=1` |
| Unknown vs known opponent active | Active identity hashes, source and roster known/unknown masks differ |
| Own bench Blissey vs Garchomp | Only slot-2 species hash families differ within Slice 3 |
| Revealed opponent bench Charizard vs Dragonite | Public roster slot-1 species hashes differ |
| Same roster, active slot 1 vs slot 2 | Placement enums move between `active` and `bench` |

The known/unknown opponent fixture leaves all unrevealed slots on explicit
`species_state_unknown`; no belief candidate is inserted into exact species
hashes.

## Major-status results

| Comparison | Distinguishing v5 fields |
| --- | --- |
| Burn vs none | `active_status_none` → `active_status_brn`, mirrored in roster status |
| Paralysis vs burn | `brn` → `par` active and roster enums |
| Sleep vs paralysis | `par` → `slp` plus public sleep elapsed availability/value |
| Regular poison vs toxic | `psn` → `tox` plus public Toxic elapsed availability/value |
| Freeze vs none | `none` → `frz` active and roster enums |
| Unknown status vs confirmed none | `unknown` and `none` masks differ |

All six major non-empty status identities activate distinct enum positions.
Fainted is a separate state and is not collapsed into status none.

## Perspective sanity

The same physical p1 roster maps as follows:

| Physical state | p1 perspective | p2 perspective |
| --- | --- | --- |
| Burned Pikachu becomes bench | own roster slot 1, burn | opponent roster slot 1, burn |
| Blissey becomes active | own roster slot 2, active | opponent roster slot 2, active |

The species/status meaning is unchanged; only relative side placement moves.

## Limitations

- Fixtures are synthetic protocol transitions designed to isolate feature
  representation.
- Dual species hashes can theoretically collide.
- Opponent reveal order is used as the public roster slot order when exact team
  order is unavailable.
- `displayed_species_uncertain` is conservative until request truth or an
  Illusion reveal resolves it.
- Sleep/Toxic fields encode public elapsed evidence, not hidden internal timers.
- No v5 model was trained or evaluated.
