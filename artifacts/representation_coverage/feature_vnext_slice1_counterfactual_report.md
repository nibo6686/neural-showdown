# Feature vNext Slice 1 Counterfactual Report

**Version compared:** v2 (115D) versus v3 (217D)  
**Status:** diagnostic-only

## Stat-stage identity

| State | v2 coarse own boost | v3 own SpA | v3 own Speed | v3 opponent Def |
| --- | ---: | ---: | ---: | ---: |
| neutral | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| own SpA -6 | -0.1667 | **-1.0000** | 0.0000 | 0.0000 |
| own Speed -6 | -0.1667 | 0.0000 | **-1.0000** | 0.0000 |
| own all seven stages -6 | -1.0000 | -1.0000 | -1.0000 | 0.0000 |
| opponent Def -2 | 0.0000 | 0.0000 | 0.0000 | **-0.3333** |

Under v2, own SpA -6 and Speed -6 remain identical full vectors. Under v3:

- SpA -6 changes only `own_active_spa_stage_norm` among own stage fields.
- Speed -6 changes only `own_active_spe_stage_norm`.
- all-stats -6 changes all seven own stage fields, including accuracy/evasion.
- opponent Def -2 changes `opponent_active_def_stage_norm`.

Therefore SpA -6 and Speed -6 are no longer aliased.

## Perspective normalization

For the same physical state with p1 at SpA -6:

| Perspective | own SpA stage | opponent SpA stage |
| --- | ---: | ---: |
| p1 | -1.0000 | 0.0000 |
| p2 | 0.0000 | -1.0000 |

The stage remains attached to the physical Pokémon and moves between relative
own/opponent slots correctly.

## Current typing identity

Synthetic public protocol fixture:

```text
Charizard base types: Fire/Flying
|-start|p2a: Charizard|typechange|Water|[from] move: Soak
```

v2 changes: **none**.

v3 changes:

- `opponent_active_current_type_fire`: 1 → 0
- `opponent_active_current_type_flying`: 1 → 0
- `opponent_active_current_type_water`: 0 → 1
- current-type source: `species` → `protocol_typechange`

The base-type fields remain Fire/Flying. This proves current typing is encoded
separately from original/base typing and that the Soak state does not silently
fall back to stale Charizard typing.

## Conclusion

Slice 1 closes the two targeted representation gaps:

- seven per-stat stages preserve identity and perspective;
- active current typing preserves public type changes and Tera typing with
  explicit provenance.

It does not make existing learned models better because no v3 model has been
trained or selected. Full retraining remains blocked on the other major slices.
