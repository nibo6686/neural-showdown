# Tera and Field Showdown Truth Audit

**Upstream:** Pokémon Showdown 0.11.10

## Tera truth

`sim/pokemon.ts` stores:

- `canTerastallize`: current simulator legality/type or false/null;
- `teraType`: configured Tera type;
- `terastallized`: the type after Tera is used.

Gen 9 switch request data includes own `teraType` and `terastallized`.
Move-request data exposes `canTerastallize` when the current Pokémon can use the
side's remaining Tera action.

Public `|-terastallize|POKEMON|TYPE` reveals the user and type. Updated details
also carry `tera:TYPE`. Before use, the opponent's Tera type is hidden.

Tera is consumed per side, but ordinary opponent availability is not an exact
private field before public use. Slice 4 keeps it unknown until legally known.

## Field truth

`sim/field.ts` stores:

- `weather` and `weatherState`;
- `terrain` and `terrainState`;
- `pseudoWeather`, keyed by effect ID.

Effect states can contain exact simulator duration and source information.
Weather and terrain are publicly announced. Pseudo-weather uses public
field-start/end protocol.

Relevant pseudo-weather includes Trick Room, Gravity, Magic Room and Wonder
Room.

## Side-condition truth

`Side.sideConditions` stores named `EffectState` records. Relevant public
conditions include:

- Reflect, Light Screen and Aurora Veil;
- Tailwind;
- Stealth Rock, Spikes, Toxic Spikes and Sticky Web;
- Safeguard and Mist.

Spikes and Toxic Spikes use public restart events/layer progression. Other
conditions are active until public side-end removal.

## Duration observability

True `EffectState.duration` is authoritative inside the simulator. Durations may
depend on held items or abilities:

- Reflect/screens may last 5 or 8 turns through Light Clay;
- Tailwind and room effects can be extended by Persistent;
- weather/terrain may be extended by hidden held items.

Public protocol gives start, upkeep and end events. It supports public elapsed
turn tracking, but exact remaining turns are not always legally known before
the effect ends. Slice 4 consequently records elapsed evidence rather than
leaking true internal duration.

## sim-core before Slice 4

sim-core already exposed:

- own request Tera type/action availability;
- public `terastallized`, Tera type and current types;
- weather and terrain identity;
- all announced pseudo-weather names;
- perspective-normalized named side-condition maps and hazard layers.

It did not expose field duration evidence. The Python tactical tracker also
omitted Gravity, Wonder Room, Safeguard and Mist, and did not reliably restore a
public Terastallized state after switching.

## Slice 4 extraction changes

- tactical tracking now includes Gravity, Wonder Room, Safeguard and Mist;
- hail is retained separately from Gen 9 snow;
- Tera state/type/provenance is restored from public switch details/history;
- exact request Tera state cannot be overwritten by randbats fallback;
- weather upkeep no longer resets the public start turn;
- terrain and named field/side effects expose public elapsed evidence.

## Learned feature path

- v2 remains live at 115D and collapses weather/terrain/screens substantially.
- v3/v4/v5 remain immutable diagnostic prefixes.
- v6 explicitly represents Tera identity/state, weather, terrain, rooms,
  screens, Tailwind, Safeguard/Mist and hazard layers.
- No hidden opponent Tera type or true internal field duration enters v6.
