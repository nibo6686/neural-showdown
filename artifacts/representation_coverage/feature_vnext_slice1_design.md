# Feature vNext Slice 1 Design

**Status:** implemented, diagnostic-only  
**New version:** `live-private-belief-v3`  
**Dimension:** 217  
**Backward-compatible default:** `live-private-belief-v2`, 115 dimensions

## Scope

Slice 1 addresses only:

1. perspective-normalized seven-stat stages;
2. active base/current typing identity and typing provenance.

It does not address item/ability/status/move identity, weather/terrain identity,
action consequences, lock states or switch-target representation.

## Compatibility model

The v2 constants, ordered names, dimension and default builder behavior remain
unchanged. v3 is an explicit opt-in:

```python
build_features_from_live_payload(
    ...,
    feature_version="live-private-belief-v3",
)
```

The first 115 v3 fields are exactly the ordered v2 fields. Slice 1 appends 102
new fields. Existing checkpoints and live defaults continue to request v2.
Strict live checkpoint validation therefore still rejects v3 checkpoints, and
the v3 metadata validator rejects v2 metadata when v3 is explicitly expected.

## Seven stat stages

Fourteen fields are appended:

- `own_active_{atk,def,spa,spd,spe,accuracy,evasion}_stage_norm`
- `opponent_active_{atk,def,spa,spd,spe,accuracy,evasion}_stage_norm`

Each is clipped to `[-1, 1]` and encoded as:

```text
stage / 6.0
```

“Own” and “opponent” are relative to the requested player perspective. A
physical p1 SpA drop therefore occupies `own_active_spa_stage_norm` for p1 and
`opponent_active_spa_stage_norm` for p2.

The upstream source is public Showdown boost protocol tracked in tactical state.
Unknown/no observed stage is zero, which is mechanically neutral; unlike typing,
there is no separate unknown stage because public boosts begin at known zero and
reset on switch.

## Base and current typing

For each side, v3 appends:

- 18-way base-type multi-hot;
- 18-way current-type multi-hot;
- base-type source one-hot;
- current-type source one-hot.

Base type and current type have separate names:

- `own_active_base_type_fire`
- `own_active_current_type_water`
- corresponding opponent fields.

Current types are authoritative when supplied by:

1. `protocol_tera`
2. `protocol_typechange`
3. exact own request `types`, when available
4. bundled Showdown `data/pokedex.ts` species fallback
5. explicit `unknown`

Base-type sources are:

- `request`
- `species`
- `unknown`

Source masks are included in the vector, so missing type information is never
silently encoded as a guessed base type without provenance. The species fallback
comes from the installed Pokémon Showdown 0.11.10 data rather than a hand-written
type table.

## Extraction changes

- Tactical state now tracks `active_base_types`, `active_current_types`,
  `base_type_source` and `current_type_source`.
- Public `typechange`/`typeadd` protocol events update current typing.
- Terastallization updates current typing and provenance.
- Switching resets current typing to the revealed species base typing.
- sim-core `PokemonView.types` now updates on public `typechange`/`typeadd`
  events, allowing view-based diagnostics to observe Soak-like changes.

## Metadata

The feature schema now exposes:

- `v3_feature_version`
- `v3_feature_dim`
- `v3_feature_names`
- `v3_slice1_feature_names`

No checkpoint path or production configuration changed.
