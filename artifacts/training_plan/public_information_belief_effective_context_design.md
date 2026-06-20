# Public-Information Belief & Effective-Context Design

## Purpose and status

This is a **design + small-guardrail** deliverable. It specifies a
public-information belief layer and an effective-context layer so the model
receives the *same category of information a skilled Showdown player has* —
known species, possible abilities/items, speed ranges, and revealed/inferred
public facts — and **never the hidden truth before it is revealed**.

It does **not** rewrite live extraction, does not change `legal-action-v7`
(stays 552D / `956da3d2…1bf39d7`), does not migrate any state schema, and does
not train, materialize, promote, or change live defaults/behavior. Scope stays
Gen 9 Random Battles; NatDex/old-gen is out of scope.

Concrete output of this pass: pure, torch-free belief/effective-context
contracts in `trainer/src/neural/provenance_contracts.py` plus
`trainer/tests/test_public_information_belief_contracts.py` (25 tests). They
codify the rules and back the no-leakage tests; they are not wired into live
extraction here.

## How revealed information enters state today (grounding)

Inspected modules: `tactical_state.py`, `live_eval_server.py`,
`vnext_live_shadow.py`, `resolved_action_impact.py`, `action_features.py`,
`provenance_contracts.py`. The existing pipeline **already separates revealed
from possible**, which this design formalizes rather than replaces:

- **Revealed/known** is set only on public events: `item_known` /
  `ability_known` flags, `active_base_ability` / `active_current_ability`,
  `known_abilities` (per side), and `revealed_moves_by_species` (appended as
  moves are observed). `item_known` flips true after an item is revealed/used;
  ability is recorded from `-ability`/activation events.
- **Possible/belief** lives under `opponent_belief` →
  `opponents[].{revealed, inferred.abilities, top_candidates[].abilities}` — the
  species/team-generation candidate sets a skilled player can enumerate.
- A **known-vs-possible** distinction already exists in action features
  (`target_known_or_possible_ability_absorbs_move_type`,
  `..._blocks_move_effect`, `own/opp_possible_absorb_ability_known`).
- `resolved_action_impact.py` already fails closed on speed-dependent power when
  speed inputs are not known (`variable_power_speed_unknown`).

The gap this design closes is a *single, explicit contract* for the
known/possible/inferred/hidden split and for **effective** (post-suppression)
mechanics, with no-leakage tests — instead of those concepts being implicit and
scattered.

## 1. Public-information belief design

For each Pokemon the belief distinguishes four tiers per attribute:

| Tier | Meaning | Allowed as model input? |
| --- | --- | --- |
| known | publicly revealed/activated, or own-private legal request | yes |
| possible | enumerable from species/format/team-gen | yes (as a set/range) |
| inferred | narrowed by public evidence (e.g. one candidate left, observed move order) | yes (flagged inferred) |
| hidden | the true unrevealed value | **never** |

### Ability — `PublicAbilityBelief`

Fields: `species_known`, `possible_abilities` (species/format list),
`revealed_ability`, `inferred_ability`, `knownness ∈ {known, inferred,
unknown}`. `effective_ability` returns an `EffectiveAbility` that carries a
concrete id only when `KNOWN` (revealed) or `INFERRED`; an unknown belief
resolves to `ability=None, UNKNOWN`. Listing `possible_abilities` never selects
one as truth.

### Item — `PublicItemBelief`

Fields: `possible_items`, `revealed_item`, `state ∈ {known, inferred, unknown,
removed, consumed}`. `has_active_item` returns `True` only for a known/inferred
present item, `False` for removed/consumed, and **`None` for unknown** (cannot
claim presence or absence).

### Speed — `PublicSpeedBelief`

Fields: `possible_speed_min`, `possible_speed_max`, `known_exact`. Built from
species base speed + level + the legal nature/EV/IV/item/boost envelope as a
**range**; `known_exact` is set only when speed is publicly inferable (observed
move order, or explicit public state). `is_exact` is false for range-only
beliefs. Exact hidden speed is never surfaced otherwise.

### Species/form/level, moves, status/volatiles/side conditions

Species/form/level are typically known from the protocol; `revealed_moves` is
the appended public set; public status, volatiles, hazards, screens, weather,
and terrain are observable. These reuse the existing `tactical_state`
representation — the belief layer adds the per-attribute knownness tier, not new
raw fields.

## 2. Effective-context design

Effective context separates *raw known state* from *active mechanics*.

### Ability suppression / bypass — `EffectiveAbilityContext`

Wraps a `PublicAbilityBelief` with `neutralizing_gas_known`,
`gastro_acid_known`, `source_ignores_abilities_known` (Mold Breaker / Teravolt /
Turboblaze), and `ability_shield_known`. `resolve()` returns an
`EffectiveAbility` where suppression/ignore apply **only when the modifier is
itself known active**, and **Ability Shield blocks suppression and ignore**.
Suppressing an *unknown* ability does not turn it into a known one.

### Item effects — `EffectiveItemContext` + `item_blocks`

Wraps a `PublicItemBelief` with `magic_room_known`. `item_effect_active(item)`
is tri-state: `True` (known item present, not suppressed), `False`
(removed/consumed/Magic Room/known-other-item), `None` (unknown → cannot claim).
`item_blocks(context, item_id)` fails closed (`available=False`) on unknown.
Covers Heavy-Duty Boots (hazard damage), Safety Goggles (powder / weather chip),
Covert Cloak (secondary effects), Ability Shield, Eject Button / Red Card /
Loaded Dice (the contract is the same known/unknown/removed gate).

### Weather suppression — `EffectiveWeatherContext`

`weather` (exists) vs `weather_effects_active` (Cloud Nine / Air Lock negate
when `weather_negator_known`). `effective_weather()` returns the weather only
when its effects are active. This feeds weather chip, weather-dependent
accuracy, and weather-boosted damage so they are not claimed when negated.

### Secondary-effect blocking and hazard blocking

Secondary blocking = Shield Dust (ability; via `EffectiveAbilityContext`) or
Covert Cloak (item; via `item_blocks`). Hazard blocking = Heavy-Duty Boots (item;
via `item_blocks`). Status blocking = Good as Gold (already wired in batch 7 via
`resolve_status_move_ability_block`, which this layer's knownness rules match).

### Important examples mapped to contracts

| Mechanic | Contract / flag |
| --- | --- |
| Mold Breaker / Teravolt / Turboblaze | `EffectiveAbilityContext.source_ignores_abilities_known` |
| Neutralizing Gas | `EffectiveAbilityContext.neutralizing_gas_known` |
| Gastro Acid / Core Enforcer | `EffectiveAbilityContext.gastro_acid_known` |
| Ability Shield | `EffectiveAbilityContext.ability_shield_known` (blocks suppress/ignore) |
| Cloud Nine / Air Lock | `EffectiveWeatherContext.weather_negator_known` |
| Safety Goggles | `item_blocks(ctx, "safetygoggles")` |
| Covert Cloak / Shield Dust | `item_blocks(ctx, "covertcloak")` / Shield Dust via ability ctx |
| Heavy-Duty Boots | `item_blocks(ctx, "heavydutyboots")` |
| Magic Room | `EffectiveItemContext.magic_room_known` |
| Good as Gold | batch-7 `resolve_status_move_ability_block` (known-active only) |
| Magic Bounce | batch-7 `validate_reflection_provenance` (known-active + routing) |

## 3. No-leakage rules and test plan

Binding rules:

1. **Unrevealed ability stays unknown** — never copied from species default or a
   single possible candidate. (`test_unrevealed_ability_stays_unknown_not_species_default`)
2. **Possible sets may be listed without selecting truth.**
   (`test_possible_abilities_listed_without_selecting_truth`)
3. **Revealed becomes known only after a public event.**
   (`test_revealed_ability_becomes_known`, `test_revealed_item_becomes_known`)
4. **Unknown item stays unknown even when it would matter**; `item_blocks` fails
   closed. (`test_unknown_item_stays_unknown`, `test_unknown_item_fails_closed`)
5. **Removed/consumed items grant no effect.**
6. **Suppression/bypass apply only when known active**; Ability Shield blocks
   them; suppressing an unknown ability does not make it known.
   (`EffectiveAbilityContextTest`)
7. **Cloud Nine / Air Lock suppress weather only when known.**
8. **Speed is a range; exact is leaked only when public/inferable.**
   (`PublicSpeedBeliefTest`)
9. **Possible-but-unrevealed opponent ability/item must not be treated as
   known** — the unifying invariant behind 1–8.

Test coverage delivered: 25 tests in
`test_public_information_belief_contracts.py`, plus the existing 43 in
`test_state_provenance_no_leakage_contracts.py` (ability knownness, Good as
Gold, Magic Bounce). Future no-leakage tests to add when wiring into live
extraction: seed-invariance over hidden ability/item/speed; future-prefix
isolation; hidden-opponent perturbation invariance.

## 4. Where this plugs in

| Layer | Role of belief/effective-context |
| --- | --- |
| live state extraction | populate `PublicAbilityBelief` / `PublicItemBelief` / `PublicSpeedBelief` from protocol revealed events + own legal request + species/format possibility tables; never read hidden opponent truth |
| tactical state | carry the knownness tier alongside existing `known_abilities` / `item_known` / `opponent_belief`; expose effective-context flags (negator/suppression/bypass) when known |
| rollout state | consume `effective_ability` / `effective_weather` / `item_effect_active` so transitions act on *effective* mechanics and fail closed on unknown |
| action features | may encode known/possible/inferred tiers and effective flags as belief features; must not encode the hidden true value (consistent with the existing known-or-possible features) |
| search node | may branch over possible abilities/items/speed within a node; branch values stay node-local and are never flattened into a candidate vector |

Recommended sequencing: keep this as a contract+test guardrail now; wire it into
live extraction and tactical state in a later, separately-approved batch, with
the seed-invariance/perturbation no-leakage tests added before any
materialization.

## Addendum — known-modifier wiring landed

A first narrow wiring of these contracts is now implemented; see
`effective_context_known_modifier_wiring_report.md`. Verified against bundled
Showdown and added to `prevention.py` / `provenance_contracts.py`: a known Mold
Breaker / Teravolt / Turboblaze source bypasses a known Good as Gold unless the
holder has a known Ability Shield (`source_ignores_target_abilities`,
`_holds_known_item`), and a known Safety Goggles blocks a powder move
(`item_belief_from_state` + `item_blocks`). Three new PASS fixtures; harness now
52 cases, 44 PASS / 0 FAIL / 8 GAP. Heavy-Duty Boots (hazards) and Safety
Goggles (weather chip) were already represented. Cloud Nine / Air Lock weather
suppression, Neutralizing Gas harness coverage, and Covert Cloak / Shield Dust
secondary blocking remain **deferred** (unit-tested at the contract level,
harness wiring needs clean oracle setup / secondary routing). Unknown
ability/item is never assumed; no `legal-action-v7`/state schema change.

## Addendum — effective-context batch 2 landed

A second wiring slice is implemented; see
`effective_context_batch_2_weather_suppression_secondary_blocking_report.md`.
Verified against bundled Showdown: known Cloud Nine / Air Lock suppresses the
Sandstorm chip (`end_of_turn` via `EffectiveWeatherContext` +
`weather_negator_known`), and known active Neutralizing Gas suppresses Good as
Gold unless Ability Shield protects (`prevention.py` via
`neutralizing_gas_suppresses_target`). A `secondary_effect_blocked` contract for
Covert Cloak / Shield Dust is added and unit-tested but **not** wired to a
rollout transition (no local secondary-effect phase) — harness secondary
blocking stays deferred. Three new PASS fixtures; harness now 55 cases,
47 PASS / 0 FAIL / 8 GAP. Unknown negator/gas/item is never assumed; no
`legal-action-v7`/state schema change.

## 5. What did NOT change

No live extraction rewrite, no `legal-action-v7`/state/action schema change, no
materialization, training, checkpoint promotion/file, live-default, or
live-behavior change; no NatDex/old-gen. Both the rollout-parity and overall
diagnostic training gates remain **closed**.
