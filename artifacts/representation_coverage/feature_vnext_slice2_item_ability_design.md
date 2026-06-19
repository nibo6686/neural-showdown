# Feature vNext Slice 2 — Item and Ability Design

**Status:** implemented, diagnostic-only  
**New immutable version:** `live-private-belief-v4`  
**Dimension:** 765  
**Prefix compatibility:** v2 115D → v3 217D → v4 765D

## Versioning decision

Slice 1's v3 dimension remains immutable. Slice 2 creates v4 rather than resizing
v3. The existing live builder still defaults to v2, current checkpoint paths are
unchanged, and strict live metadata validation rejects v4.

## Stable identity encoding

Items and abilities use two independent deterministic SHA-256 bucket families,
32 buckets each. Every known identity activates exactly one `a` bucket and one
`b` bucket. Python's randomized `hash()` is not used.

Encoded identities, separately for own/opponent:

- current item;
- last known item;
- base ability;
- current ability.

This adds 64 fields per identity. Two bucket families substantially reduce
single-bucket collisions while keeping the slice smaller than full one-hot
vocabularies for every Showdown item and ability. Collisions remain possible,
so a future learned embedding/vocabulary migration may be preferable after
frequency analysis.

## Item lifecycle fields

Per side:

- current item identity hash;
- last item identity hash;
- state enum: `unknown`, `held`, `none`, `removed`, `consumed`;
- source enum: `unknown`, `request`, `protocol`;
- `item_suppressed`.

Semantics:

- `unknown`: no legal exact/revealed information;
- `none`: own private request confirms no held item;
- `held`: request or public protocol confirms an item;
- `removed`: public `-enditem` with a source such as Knock Off;
- `consumed`: public `[eat]`, gem use, or self-ending item event;
- suppression: public Magic Room currently disables held-item effects.

Heavy-Duty Boots is represented through the stable current/last item identity
buckets, not through a strategic Boots rule.

## Ability lifecycle fields

Per side:

- base ability identity hash;
- current ability identity hash;
- state enum: `unknown`, `known`, `changed`, `none`, `suppressed`;
- source enum: `unknown`, `request`, `protocol`;
- `ability_suppressed`.

Public `-ability` without a change source establishes a revealed/base ability.
A sourced `-ability` transition preserves base identity and changes current
identity. Public `-endability` marks the current ability suppressed while
retaining its identity. Neutralizing Gas remains representable by current
ability identity; this slice does not add an ability-specific tactical rule.

## Information boundary

- Own request data is exact and source-tagged `request`.
- Opponent identities enter exact slots only after public protocol reveal.
- Unrevealed opponent item/ability remains `unknown`; hidden simulator truth is
  never read.
- Belief distributions remain separate and are not promoted to exact identity.

## Compatibility

- v2 constants, dimension and behavior remain unchanged.
- v3 remains 217D and retains Slice 1 behavior.
- v4's first 217 fields are exactly v3.
- diagnostics opt in with `feature_version="live-private-belief-v4"`.
- no live default or checkpoint was changed.
