# Feature vNext Slice 4 — Tera and Field Design

**Status:** implemented, diagnostic-only  
**New immutable version:** `live-private-belief-v6`  
**Dimension:** 2493  
**Prefix compatibility:** v2 115D → v3 217D → v4 765D → v5 2293D → v6 2493D

## Versioning decision

v5 remains immutable at 2293 dimensions. Slice 4 appends 200 explicitly named
fields. The live/default builder remains v2 and strict production checkpoint
validation does not accept v6.

## Tera representation

Per relative side, v6 represents:

- availability state: unknown, available, unavailable, or used;
- active state: unknown, inactive, or active;
- 18-way revealed/known Tera type;
- provenance: unknown, request, protocol, sim-core, or fallback;
- current Tera-action availability;
- whether current typing is the public Tera-current typing.

Own request state is exact. Opponent Tera type/state becomes exact only after
public `-terastallize` or equivalent public details. Unrevealed opponent Tera
type and availability remain unknown.

Base/current typing remains in the immutable v3 prefix. v6 therefore does not
replace typing: it adds Tera identity/state alongside the existing base/current
type fields.

## Field identity

Weather enum:

- unknown, none, rain, sun, sand, snow, hail, other.

Terrain enum:

- unknown, none, Electric, Grassy, Misty, Psychic.

Pseudo-weather uses explicit active/inactive/unknown state for:

- Trick Room;
- Gravity;
- Magic Room;
- Wonder Room.

Every active global effect also has public elapsed-turn availability and a
normalized elapsed value. These are protocol-history observations, not claimed
true remaining duration.

## Side conditions and hazards

Each relative side has active/inactive/unknown state plus public elapsed
evidence for:

- Reflect;
- Light Screen;
- Aurora Veil;
- Tailwind;
- Safeguard;
- Mist.

Hazards are represented separately:

- Stealth Rock active/inactive/unknown;
- Spikes exact public layer enum 0–3 or unknown;
- Toxic Spikes exact public layer enum 0–2 or unknown;
- Sticky Web active/inactive/unknown.

All fields are perspective-normalized. A physical p1 Reflect maps to
`own_reflect_*` for p1 and `opponent_reflect_*` for p2.

## Duration boundary

Showdown true state stores exact durations, including extensions from Light
Clay or Persistent. Ordinary protocol reliably supplies start/upkeep/end
evidence but does not always reveal the source's hidden duration modifier.

v6 therefore encodes:

- effect identity and active state;
- whether public elapsed evidence is available;
- normalized turns since the public start event.

It does not invent a precise remaining-turn value where one is not legally
known.

## Compatibility and scope

- v2/v3/v4/v5 names, dimensions, and ordering are unchanged.
- v5's complete ordered schema is the exact v6 prefix.
- No field-specific tactical recommendation rule was added.
- No dataset, checkpoint, live default, or production model changed.
