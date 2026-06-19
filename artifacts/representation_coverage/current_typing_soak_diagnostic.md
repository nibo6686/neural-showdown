# Current Typing / Soak Diagnostic

**Method:** synthetic, protocol-faithful type-change fixture  
**Reason for fallback:** a bounded seeded random-battle Soak user was not required
to validate the representation path; the Showdown public `typechange` event is
the authoritative observable transition and isolates typing from damage/status.

Fixture:

```text
|switch|p2a: Charizard|Charizard, L80|100/100
|-start|p2a: Charizard|typechange|Water|[from] move: Soak
```

## Results

- **Does Showdown expose the change?** Yes. `SIM-PROTOCOL.md` defines public
  `typechange` volatile events, and Showdown move data emits them for Soak-like
  mechanics.
- **Does sim-core track current type?** Yes after Slice 1. The extractor updates
  `PokemonView.types` to `["Water"]` while retaining species `Charizard`.
- **Does tactical/live extraction track it?** Yes.
  `active_base_types=["Fire","Flying"]`,
  `active_current_types=["Water"]`, with source
  `protocol_typechange`.
- **Does v3 encode it?** Yes. Base Fire/Flying remain set, current Water becomes
  set, current Fire/Flying clear, and the source mask changes.
- **Does v2 encode it?** No. The tested v2 vector is unchanged.
- **Does v3 silently use stale base typing?** No. Base and current type fields are
  separate and provenance is explicit.

## Unknown and inferred behavior

- Exact own request types are used with source `request` if provided.
- Revealed species types use Pokémon Showdown `data/pokedex.ts` with source
  `species`.
- Public type-change and Tera events override current typing with their own source.
- If none of those sources is available, all type bits remain zero and the
  corresponding `source_unknown` field is one.
- Hidden opponent original information is not read from simulator truth; only
  public protocol/species data is used.
