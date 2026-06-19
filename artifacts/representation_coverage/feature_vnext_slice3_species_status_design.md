# Feature vNext Slice 3 — Species, Roster, and Status Design

**Status:** implemented, diagnostic-only  
**New immutable version:** `live-private-belief-v5`  
**Dimension:** 2293  
**Prefix compatibility:** v2 115D → v3 217D → v4 765D → v5 2293D

## Versioning decision

v4 remains immutable at 765 dimensions. Slice 3 creates v5 and appends 1528
ordered fields. The builder still defaults to v2, strict live startup still
accepts only the production v2 contract, and no checkpoint or dataset changed.

## Stable species encoding

Species identities use the same deterministic dual SHA-256 encoding as Slice 2:
32 buckets in family A and 32 in family B. Python's randomized `hash()` is not
used.

Separate active identities are encoded for each relative side:

- base/original species;
- current species, including public Transform or forme changes;
- displayed species, retained across an Illusion `replace` reveal.

Every known identity activates one bucket in each family. Collisions are
possible, so the provenance and known/unknown masks are part of the schema.

## Roster layout

Each side has six ordered roster slots. Every slot contains:

- dual species identity hashes;
- species state: unknown or known;
- placement: unknown, active, or bench;
- life state: unknown, alive, or fainted;
- species provenance;
- major-status identity and provenance.

Own slots use exact request order. Opponent slots use public reveal order and
are padded with explicit unknown slots. Hidden opponent species are never
filled from simulator truth or randbats guesses.

Species provenance values are:

- `unknown`
- `request`
- `protocol`
- `sim_core`
- `species_fallback`

The final two values reserve explicit contracts for view-based diagnostics and
Dex-backed fallback without conflating them with exact request/protocol truth.

## Transform and Illusion

Transform preserves base/original identity while updating current and displayed
identity and setting `transformed`.

Before an opponent identity is confirmed, protocol-displayed identity carries
`displayed_species_uncertain`. On `replace`, the tracker retains the prior
displayed species, updates base/current species to the revealed species, clears
uncertainty, and sets `illusion_revealed`.

This is a public-evidence representation, not an attempt to infer hidden
Illusion users.

## Major status

Active and per-roster-slot status enums distinguish:

- unknown;
- confirmed none;
- burn (`brn`);
- paralysis (`par`);
- sleep (`slp`);
- regular poison (`psn`);
- toxic poison (`tox`);
- freeze (`frz`);
- fainted.

Status provenance is `unknown`, `request`, `protocol`, `sim_core`, or
`inferred`.

For active sleep and toxic poison, v5 includes availability and normalized
public elapsed-turn evidence. It does not expose Showdown's hidden random sleep
timer or internal Toxic stage.

## Information boundary

- Own request roster/status is exact and source-tagged `request`.
- Opponent active/bench identity enters exact fields only through public
  protocol.
- Unknown opponent roster slots remain explicit unknowns.
- Randbats fallback may support older belief features but is not promoted to
  exact v5 species or status slots.
- No species-specific or status-specific tactical rule was added.
