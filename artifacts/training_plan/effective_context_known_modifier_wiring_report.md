# Effective-Context Known-Modifier Wiring

## Scope and result

This batch wires the public-belief / effective-context contracts into the
narrow rollout/prevention surface for **known/effective** modifiers, using exact
handling only when the modifier is known active (or fixture-provided as public
transition provenance) and failing closed / not-claiming when unknown. It is not
a schema migration and not a broad simulator rewrite.

Deterministic harness after this batch:

- 52 deterministic cases (was 49)
- **44 PASS** (was 41)
- **0 FAIL**
- **8 explicit GAP** (unchanged)

`legal-action-v7` stays 552D / `956da3d2…1bf39d7`. Scope stays Gen 9 Random
Battles. NatDex/old-gen not implemented.

## Mechanics verified against bundled Showdown (not memory)

Source: `sim-core/node_modules/pokemon-showdown`.

- **Good as Gold** (`data/abilities.ts`): blocks opponent `Status` moves via
  `onTryHit`; `flags: { breakable: 1 }`.
- **Mold Breaker / Teravolt / Turboblaze**: set `move.ignoreAbility`; the engine
  (`sim/battle.ts`) suppresses a `breakable` ability when
  `suppressingAbility(target)` is true.
- **`suppressingAbility`** (`sim/battle.ts`): true only when an active move has
  `ignoreAbility` **and `!target.hasItem('Ability Shield')`** — so Ability Shield
  protects Good as Gold from the bypass.
- **`ignoringAbility`** (`sim/pokemon.ts`): Gastro Acid / active Neutralizing Gas
  suppress an ability, but **Ability Shield or own Neutralizing Gas** prevent it
  — matching `EffectiveAbilityContext`.
- **`ignoringItem`** (`sim/pokemon.ts`): items ignored under Magic Room / Klutz /
  Embargo / knocked-off — matching `EffectiveItemContext.magic_room_known`.
- **Safety Goggles** (`data/items.ts`): `onTryHit` blocks `move.flags['powder']`
  (target ≠ source, target not powder-immune); `onImmunity` blocks
  sandstorm/hail/powder.

## Effective-context contracts / wiring added

Helpers (pure, torch-free) in `provenance_contracts.py`:

- `source_ignores_target_abilities(attacker)` — true only for a **KNOWN** Mold
  Breaker-class ability; an unknown attacker ability is never assumed to bypass.
- `_holds_known_item(mon, item_id)` — true only when the item is *known* (not
  removed/consumed/guessed).
- `item_belief_from_state(mon)` — builds a `PublicItemBelief` with explicit
  knownness; unrevealed items stay unknown.
- `resolve_status_move_ability_block` extended: a known Mold Breaker-class source
  bypasses a known Good as Gold **unless** the target holds a known Ability
  Shield.

Wiring in `prevention.py`:

- The Good as Gold branch now honours the Mold Breaker bypass / Ability Shield
  protection (through the helper above).
- A new Safety Goggles branch blocks a powder-flagged move when the target's item
  is *known* Safety Goggles (`item_belief_from_state` + `item_blocks`); an unknown
  item does not block (no guess), and the existing Powder / Sucker Punch /
  Thunderclap / Magic Bounce / Good as Gold paths are unchanged.

## New fixtures (all PASS vs real Showdown)

- `good_as_gold_bypassed_by_known_mold_breaker` — Gholdengo (Good as Gold) vs
  Haxorus (Mold Breaker) Thunder Wave → not blocked (paralysis lands).
- `ability_shield_protects_good_as_gold_from_mold_breaker` — same, but Gholdengo
  holds Ability Shield → still blocked.
- `safety_goggles_blocks_powder_move` — Snorlax (Safety Goggles) vs Amoonguss
  Spore → blocked by the item.

## Known vs unknown behavior verified

| Case | Known | Unknown |
| --- | --- | --- |
| Mold Breaker bypass | known Mold Breaker source → Good as Gold bypassed (PASS) | unknown attacker ability → not assumed to bypass (Good as Gold still blocks) |
| Ability Shield protection | known Ability Shield → protects (PASS) | unrevealed Ability Shield → not assumed → bypass applies |
| Safety Goggles powder block | known Safety Goggles → blocks (PASS) | unrevealed item → does not block, no guess |
| Good as Gold base block | known Good as Gold → blocks (batch 7) | unknown ability → explicit GAP (unchanged) |

## Which examples became PASS / which remain deferred

PASS this batch: Mold Breaker bypass of Good as Gold, Ability Shield protection,
Safety Goggles powder block.

Already represented (unchanged): Heavy-Duty Boots hazard prevention
(`heavy_duty_boots_prevents_hazards` PASS), Safety Goggles weather-chip immunity
(`end_of_turn` sandstorm immune-set).

Deferred (documented; unit-tested at the belief-contract level, not harness):

- **Cloud Nine / Air Lock weather suppression** in residual/weather logic — the
  contract (`EffectiveWeatherContext`) exists and is unit-tested; wiring into
  `end_of_turn` needs a known-negator state flag and a clean oracle setup.
- **Neutralizing Gas / Gastro Acid** ability suppression at the harness level —
  modeled and unit-tested via `EffectiveAbilityContext`; a clean singles oracle
  setup is needed.
- **Covert Cloak / Shield Dust** secondary-effect blocking — local secondary
  routing is not represented cleanly enough to claim exact PASS; left deferred
  rather than overclaimed.

## No-leakage behavior

- Unrevealed opponent ability is never assumed to be Mold Breaker (bypass needs a
  *known* ability); unrevealed item is never assumed to be Ability Shield / Safety
  Goggles (`item_known` gate). Removed/consumed items grant no effect.
- Exact modifiers are applied only when known active; the hidden item/ability
  truth is not used as a model feature or an exact rollout assumption.
- No `legal-action-v7` field changed; oracle/transition values stay
  transition/fixture-only.
- Fail-soft default: where exact handling is not safe (unknown), the path does
  not block/bypass and does not guess; honest GAPs are preserved.

## Verification

- runtime preflight: `D:\Anaconda\envs\neuralgpu\python.exe`, Torch
  `2.5.1+cu121`, CUDA available `True`
- sim-core TypeScript build: PASS
- sim-core test suite: 35 PASS
- `test_public_information_belief_contracts`: 36 PASS
- `test_state_provenance_no_leakage_contracts`: 43 PASS
- `test_rollout_parity_harness`: 17 PASS
- deterministic harness: 44 PASS / 0 FAIL / 8 GAP
- `python -m json.tool` on harness results: PASS
- `git diff --check`: clean (LF→CRLF warnings only)

## What did NOT change

No training, dataset materialization, checkpoint promotion, checkpoint file,
live default, live bot behavior, action/state schema, or `legal-action-v7`
fingerprint; no live-extraction rewrite; no NatDex/old-gen mechanics. Both the
rollout-parity and overall diagnostic training gates remain **closed**.
