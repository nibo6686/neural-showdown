# Feature vNext Slice 6 — Resolved Action Impact Design

**Date:** 2026-06-19  
**Status:** Implemented, diagnostic-only

## Schema

`legal-action-v5` is an append-only 318D diagnostic schema:

- dimensions 0–268 are the unchanged 269D `legal-action-v4` vector;
- dimensions 269–317 are 49 Slice 6 resolved-impact fields;
- `legal-action-v3` remains the 165D live/default action schema.

The saved implementation therefore resolves to 318D, despite an earlier handoff
note that said 320D. Tests derive the dimension from the finalized ordered field
list and verify that the complete v4 vector is the exact v5 prefix.

## Resolved impact fields

For damaging moves, v5 can consume a normalized impact record containing:

- expected, minimum and maximum target-HP damage fractions;
- damage-range width, KO chance and a two-hit-KO proxy;
- hit chance and whether accuracy metadata is known;
- immunity, resistance, super-effectiveness and normalized type effectiveness;
- STAB and whether STAB could be determined;
- an explicit non-critical-roll marker.

Damage values come from the existing `estimate_action_damage` path. Feature
generation never launches the damage calculator itself; callers must explicitly
supply an impact record.

## Provenance and availability

The schema includes one-hot methods for `smogon_calc`, `approximate`,
`belief_fallback`, `non_damaging` and `unavailable`, plus flags for current-type,
Tera, stat-stage, item/ability and field use. Exact attacker/defender-stat flags,
target-known/inferred flags and `impact_unknown` prevent zero from silently
meaning either immunity, a status move or missing computation.

## Non-damaging, switch and unavailable actions

- Status/non-damaging moves are available known-zero impacts with
  `impact_method_non_damaging=1`.
- Switches are non-damaging and use explicit unavailable impact provenance;
  they are not marked as unknown damage.
- A damaging action with no supplied impact has
  `impact_method_unavailable=1`, `impact_unknown=1` and zero-valued damage fields.

## Immediate versus future state

An immediate estimate supplies expected opponent HP loss and
`next_state_source_immediate_estimate`. Authoritative own-HP, status, field,
terminal and other future-state outcomes require an explicit seeded branch
record. Static v4 consequence fields still describe effects such as Draco
Meteor's self SpA drop, but resolved damage is not a full future-position value.

## Current typing limitation

The sim-core damage request has an additive, opt-in `types_override` used by
diagnostics for public current-type changes such as Soak. It is reliable when the
override fully covers the base-type array; replacing a dual type with a one-type
array is unsafe because `@smogon/calc` deep-merges arrays by index. The
counterfactual therefore uses a mono-type target. Tera-current typing is also
tested through the normal Tera/current-type inputs.

No live path sets `types_override`, and no live default, dataset, checkpoint or
scoring rule changed.
