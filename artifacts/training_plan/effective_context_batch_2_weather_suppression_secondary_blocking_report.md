# Effective-Context Batch 2 — Weather Suppression & Secondary Blocking

## Scope and result

This batch adds narrow, Showdown-verified, no-leakage exact handling for **known
Cloud Nine / Air Lock weather suppression** and **known Neutralizing Gas ability
suppression**, plus a **Covert Cloak / Shield Dust** secondary-blocking contract
helper (unit-level; harness wiring deferred for lack of a local secondary-effect
phase). Exact context is used only when the modifier is known active or
fixture-provided as public transition provenance; unknown stays unknown.

Deterministic harness after this batch:

- 55 deterministic cases (was 52)
- **47 PASS** (was 44)
- **0 FAIL**
- **8 explicit GAP** (unchanged)

`legal-action-v7` stays 552D / `956da3d2…1bf39d7`. Scope stays Gen 9 Random
Battles. NatDex/old-gen not implemented.

## Exact Showdown behaviors verified (bundled source, not memory)

Source: `sim-core/node_modules/pokemon-showdown`.

- **Cloud Nine / Air Lock** (`data/abilities.ts`): both carry
  `suppressWeather: true`. `sim/field.ts`: `effectiveWeather()` returns `''` when
  `suppressingWeather()` is true; `suppressingWeather()` is true when an active,
  non-fainted mon with `suppressWeather` is on the field and not ability-ignored.
  Sandstorm chip runs via `onWeather` (`data/conditions.ts`), which only fires
  while weather is effective — so suppression removes the chip.
- **Neutralizing Gas** (`sim/pokemon.ts ignoringAbility`): an active Neutralizing
  Gas suppresses other abilities, **except** when the target holds Ability Shield
  or its own ability is Neutralizing Gas.
- **Good as Gold** is `breakable`, blocked via `onTryHit` for `Status` moves —
  suppressing it lets a status move land.
- **Covert Cloak** (item) / **Shield Dust** (ability) `onModifySecondaries`:
  filter secondaries, keeping only `effect.self` or `effect.dustproof`; so
  opponent-targeting secondaries are blocked. Shield Dust is `breakable` (Mold
  Breaker bypasses it); Covert Cloak is an item (not bypassed by Mold Breaker).

## Contracts / wiring added

Pure helpers in `provenance_contracts.py`:

- `neutralizing_gas_suppresses_target(target, neutralizing_gas_known)` — true only
  for a known active Neutralizing Gas, false under known Ability Shield or own
  Neutralizing Gas.
- `secondary_effect_blocked(target, attacker, secondary)` — tri-state: known
  Covert Cloak / known-active Shield Dust block a non-self, non-dustproof
  secondary; Shield Dust bypassed by a known Mold Breaker; fail closed when
  neither blocker is known.

Wiring:

- `end_of_turn.py` — the Sandstorm chip now reads
  `EffectiveWeatherContext(weather, weather_negator_known).effective_weather()`;
  a known negator suppresses the chip, an unknown negator does not.
- `prevention.py` — before the Good as Gold branch, a known active Neutralizing
  Gas (state flag `neutralizing_gas_known`) marks the target ability suppressed
  (honoring Ability Shield), so Good as Gold no longer blocks.

## New fixtures (all PASS vs real Showdown)

- `sandstorm_suppressed_by_cloud_nine` — Golduck (Cloud Nine) vs Tyranitar (Sand
  Stream): sandstorm is set but no chip on Golduck.
- `neutralizing_gas_suppresses_good_as_gold` — Gholdengo (Good as Gold) vs
  Weezing-Galar (Neutralizing Gas) Will-O-Wisp: Good as Gold suppressed, burn
  lands.
- `ability_shield_protects_good_as_gold_from_neutralizing_gas` — same, but
  Gholdengo holds Ability Shield: Good as Gold still blocks.

## Known vs unknown behavior verified

| Case | Known | Unknown |
| --- | --- | --- |
| Cloud Nine / Air Lock | known negator → Sandstorm chip suppressed (PASS) | unknown negator → chip applies (unit test) |
| Neutralizing Gas | known active → Good as Gold suppressed (PASS) | unknown / `False` → no suppression (unit test) |
| Ability Shield vs Neutralizing Gas | known shield → Good as Gold protected (PASS) | unrevealed shield → not assumed |
| Covert Cloak / Shield Dust | known → secondary blocked (unit test) | unknown → fail closed (unit test) |

## Which examples became PASS / which remain deferred

PASS this batch: Cloud Nine / Air Lock Sandstorm-chip suppression, Neutralizing
Gas suppression of Good as Gold, Ability Shield protection from Neutralizing Gas.

Deferred (documented):

- **Covert Cloak / Shield Dust secondary blocking** — the contract helper is
  implemented and unit-tested, but the local rollout has **no secondary-effect
  application phase** (`apply_immediate_prevention` is move-prevention only;
  `end_of_turn` is residual-only). Harness wiring needs a new secondary-effect
  transition carrying the move's `secondaries` payload (chance, target,
  `self`/`dustproof` flags); until that exists, harness coverage stays deferred
  rather than overclaimed.
- **Other Cloud Nine weather effects** (Weather Ball type/power, Solar Beam
  charge skip, Thunder/Hurricane accuracy, weather recovery) — not currently
  modeled in the rollout helpers, so only the weather-chip case is wired;
  the rest are documented as future work.
- **Neutralizing Gas suppression of Serene Grace / secondary chances and
  immunity abilities (Levitate, etc.)** — depends on the deferred secondary phase
  / immunity routing; left for a later batch.

## No-leakage behavior

- An unknown / possible Cloud Nine / Air Lock never suppresses weather; an
  unknown / possible Neutralizing Gas never suppresses abilities; an unrevealed
  Ability Shield is never assumed to protect.
- Suppression is applied only from explicit known-active provenance
  (`weather_negator_known`, `neutralizing_gas_known`), not from species defaults
  or hidden truth.
- No `legal-action-v7` field changed; oracle/transition values stay
  transition/fixture-only and are not exposed as model features.
- Fail-soft default: where exact handling is not safe (unknown), the path does
  not suppress/block; honest GAPs are preserved.

## Verification

- runtime preflight: `D:\Anaconda\envs\neuralgpu\python.exe`, Torch
  `2.5.1+cu121`, CUDA available `True`
- sim-core TypeScript build: PASS
- sim-core test suite: 35 PASS
- `test_public_information_belief_contracts`: 49 PASS
- `test_state_provenance_no_leakage_contracts`: 43 PASS
- `test_rollout_parity_harness`: 17 PASS
- deterministic harness: 47 PASS / 0 FAIL / 8 GAP
- `python -m json.tool` on harness results: PASS
- `git diff --check`: clean (LF→CRLF warnings only)

## What did NOT change

No training, dataset materialization, checkpoint promotion, checkpoint file,
live default, live bot behavior, action/state schema, or `legal-action-v7`
fingerprint; no live-extraction rewrite; no NatDex/old-gen mechanics. Both the
rollout-parity and overall diagnostic training gates remain **closed**.
