# Resolved Action Impact Source Audit

**Date:** 2026-06-19  
**Scope:** Diagnostic `legal-action-v5`

## Existing source

`trainer/src/neural/damage_engine.py::estimate_action_damage` already routes
damage requests to the sim-core `@smogon/calc` implementation and returns
`damage_method`, min/max/average percent, KO chance, immunity, type
effectiveness, item modifier and exact-stat provenance.

The Slice 6 provider normalizes that result into fractions and explicit
availability/provenance fields. Exact Smogon calculation is reported only when
the node/sim-core calculation succeeds without fallback; otherwise the impact is
marked approximate.

## Mechanics coverage

- **Stats and stages:** attacker/defender stats, EVs, IVs and boosts are passed
  to the calculator. A controlled own SpA -2 case reduces special damage.
- **Screens:** opponent Reflect, Light Screen and Aurora Veil are mapped from
  `tactical_state.opponent.side_conditions`. A Light Screen counterfactual
  reduces special damage.
- **Weather and terrain:** both fields are mapped into the sim-core damage
  request and canonicalized into the Smogon field object. Their plumbing is
  supported; this slice's ten-case report directly exercises Light Screen rather
  than adding separate weather/terrain cases.
- **Accuracy:** static Showdown move metadata supplies known hit chance, including
  100% Psychic versus 70% Focus Blast.
- **Current typing and Tera:** normal current/Tera inputs affect resolved
  effectiveness. Diagnostic `types_override` supports explicit current-type
  replacement such as Soak.

## Current-type limitation

`types_override` is constructor-level so it survives calculator cloning. The
underlying deep merge replaces arrays by index, so a one-element override does
not safely erase the second type of a dual-type species. Diagnostics use
mono-type replacement or a full-length override. This limitation is why the
override remains opt-in and diagnostic-only.

## Separation from live behavior

The provider is not imported by the production dataset builders or ranker
training paths. `ACTION_FEATURE_VERSION` remains `legal-action-v3`; v5 is built
only by an explicit diagnostic call. Live damage requests never set
`types_override`. Existing live checkpoints and defaults are unchanged.
