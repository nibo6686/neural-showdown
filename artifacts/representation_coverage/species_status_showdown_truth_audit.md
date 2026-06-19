# Species and Status Showdown Truth Audit

**Upstream:** Pokémon Showdown 0.11.10

## Species and roster truth

`sim/pokemon.ts` stores:

- `baseSpecies`: original/permanent species identity;
- `species`: current species, including temporary Transform/form effects;
- `transformed`: whether Transform/Imposter copied another Pokémon;
- `illusion`: the Pokémon whose details are currently displayed;
- `details`: public-facing species/form/level/gender text;
- `position`, `isActive`, `fainted`, HP, and side membership.

`Side.pokemon` stores the roster. Active placement is determined by position
relative to `Side.active`; fainting is stored per Pokémon.

`transformInto` calls `setSpecies` for the target species, copies types, stored
stats, moves, boosts and ability as applicable, sets `transformed`, and emits
`|-transform|`. Switching clears temporary Transform state.

Illusion keeps true simulator identity in the Pokémon object while
`getFullDetails` and string rendering expose the illusion target. Public
`|replace|` announces the true details when Illusion ends. The protocol
explicitly warns that prior assumptions about the displayed Pokémon were wrong.

## Status truth

`Pokemon.status` stores the major-status ID. `Pokemon.statusState` stores the
effect state.

- Sleep uses private randomized `startTime`/`time`.
- Toxic poison uses private `stage`, reset on switch-in and incremented on
  residual damage.
- Burn, paralysis, regular poison and freeze have their own condition handlers.

Major status identity is public through switch/HP condition text and
`|-status|`/`|-curestatus|`. Exact internal sleep time and Toxic stage are not
ordinary public fields. Public observers can only derive elapsed evidence or
bounds from protocol history.

## Request and protocol boundary

- Own `side.pokemon` request data gives exact roster order, original details,
  active/fainted condition and major status.
- Opponent switches/reveals provide displayed species, placement, public HP,
  status and fainting.
- `|-transform|` publicly identifies the copied target/current species.
- `|replace|` publicly resolves Illusion.
- Unrevealed opponent bench identities remain hidden.

## sim-core before Slice 3

sim-core retained `species`, details, active/bench, fainted and status, but:

- had no separate base/current/displayed species;
- had no Transform handler or transformed flag;
- treated `replace` as an ordinary details update;
- had no species/status provenance;
- did not expose public status elapsed evidence.

## sim-core after Slice 3

`PokemonView` now exposes:

- base, current and displayed species;
- species provenance;
- transformed, displayed-uncertainty and Illusion-revealed flags;
- status provenance and public elapsed turns.

Transform and forme-change protocol update current species. Illusion replacement
reconciles the active roster entry while retaining the prior displayed species.

## Learned feature path

- v2 remains 115D and has only coarse species-known/status-count signals.
- v3 remains the immutable stat/type Slice 1 schema.
- v4 remains the immutable item/ability Slice 2 schema.
- v5 adds stable active and roster species identity, placement/life/provenance,
  major-status identity, and public sleep/toxic elapsed evidence.
- No hidden simulator species or status counters enter v5 exact fields.
