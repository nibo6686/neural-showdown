# Item/Ability Showdown Truth Audit

**Upstream:** Pokémon Showdown 0.11.10

## True simulator state

`sim/pokemon.ts` stores:

- `item`, `itemState`, `lastItem`, `usedItemThisTurn`;
- `itemState.knockedOff` for mechanics that permanently prevent resetting an item;
- `baseAbility`, `ability`, `abilityState`;
- ability effectiveness through `ignoringAbility()`, including Gastro Acid and
  active Neutralizing Gas;
- item effectiveness through `ignoringItem()`.

Consumption (`eatItem`/`useItem`) copies `item` to `lastItem`, clears current
item and emits `-enditem`. Removal uses `takeItem`; Knock Off and similar moves
announce public removal through `-enditem`.

Ability changes use `setAbility`, preserving `baseAbility` while replacing
`ability`. Gastro Acid suppression is represented as a volatile/internal
`ignoringAbility()` state and announced publicly with `-endability`.

## Public/private observability

- Own request `side.pokemon` exposes exact current item, base ability and current
  ability.
- Opponent item/ability is hidden until revealed by public protocol or inferred
  through beliefs.
- `-item` reveals/changes a held item.
- `-enditem ... [eat]` exposes consumption.
- sourced `-enditem`, including Knock Off, exposes removal.
- `-ability` exposes a current/replaced ability.
- `-endability` exposes direct ability suppression.
- Neutralizing Gas is publicly announced as an active ability, but this slice
  does not synthesize per-Pokémon suppression beyond explicit public state.

## sim-core before Slice 2

sim-core retained current `item`, `ability` and `base_ability`, but:

- discarded last item and removal/consumption cause;
- represented unknown and confirmed no item as `null`;
- did not handle `-endability`;
- did not expose changed/suppressed ability state;
- did not expose item suppression.

## sim-core after Slice 2

`PokemonView` now includes:

- `last_item`;
- `item_state` (`unknown/held/none/removed/consumed`);
- `item_suppressed`;
- `ability_state` (`unknown/known/changed/none/suppressed`);
- `ability_suppressed`.

Public Magic Room updates item suppression, sourced ability changes retain base
ability, and `-endability` preserves identity while marking suppression.

## Learned feature path

- v2 still has only item/ability knownness counts.
- v3 remains Slice 1 only.
- v4 adds perspective-relative stable identity hashes and lifecycle/source enums.
- No opponent hidden truth is inserted into exact v4 fields.
