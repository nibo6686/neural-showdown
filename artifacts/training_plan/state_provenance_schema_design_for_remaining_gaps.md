# State / Provenance Schema Design for Remaining Rollout GAPs

## Scope and status

This is a **design/audit** deliverable. It specifies the state and provenance
needed to close the remaining honest rollout-parity GAPs and to support future
materialization safely. It does **not** implement a new state schema, does not
change `legal-action-v7` (frozen at 552D, fingerprint
`956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`), does not
materialize, train, promote, or change any live default or live bot behavior.

Active target stays Gen 9 Random Battles. NatDex/old-gen is treated as
infrastructure-aware only (format-scoped capability declarations), not
implemented here.

Anchors at time of writing:

- Rollout parity: **45 fixtures, 37 PASS / 0 FAIL / 8 GAP** (per
  `rollout_parity_harness_report.md`).
- Oracle: `sim-core/src/rollout_parity_oracle.ts`.
- Local transitions: `trainer/src/neural/delayed_damage.py`,
  `trainer/src/neural/end_of_turn.py`, `trainer/src/neural/prevention.py`,
  `trainer/src/neural/entry_hazards.py`.
- Comparison/report: `trainer/src/neural/rollout_parity.py`.
- Tests: `trainer/tests/test_rollout_parity_harness.py`.

The governing rule from the existing audits is unchanged: **an action vector may
declare intent ("schedules Future Sight", "pivots", "reflects status") but must
never claim a later residual amount, switch-in result, opponent-selected action,
or future target unless that result is already fixed by current public/inferable
information.** When the exact branch is not knowable, encode ranges,
probabilities, distributions, and provenance — and otherwise fail closed.

## Owner-layer vocabulary

Each proposed field is assigned exactly one primary owner layer:

| Owner | Meaning | Existing example |
| --- | --- | --- |
| live state extraction | reconstructed from public protocol + own legal request during live/replay extraction | grounded/types/item reconstruction |
| tactical state | derived per-decision tactical belief surface consumed downstream | confusion/seed volatiles, last-move counters |
| rollout state | the transition state the local kernels read/write | `combatants`, `delayed_attacks`, `active_slots`, `toxic_stage` |
| action features | click-time `legal-action-v7` candidate summary | `risk_*` batch-7 slice |
| search node | only known inside a two-ply / branch evaluation node, never a flat feature | hypothetical opponent action branch |
| oracle fixture only | exists only in seeded Showdown oracle fixtures, never returned as a model input | seeded PRNG, hidden team |

The split matters for no-leakage: a value owned by **oracle fixture only** or
**search node** must never be flattened into **action features** or **tactical
state**.

---

## Remaining rollout GAP table

The 8 current GAP fixtures collapse into four mechanic groups. Each row gives the
GAP reason, the exact missing state/provenance, the proposed representation, the
owner layer, the no-leakage concern, and the recommended implementation batch.

### GAP group 1 — Delayed attack landing resolver (Future Sight / Doom Desire)

Fixtures: *Future Sight replacement damage when target-specific landing damage is
absent*, *Doom Desire replacement damage when target-specific landing damage is
absent*.

| Aspect | Detail |
| --- | --- |
| Current GAP reason | `delayed_damage.py` requires a pre-supplied `damage_by_target[target_id]`. When the slot occupant at landing is a replacement with no entry in `damage_by_target`, `resolve_delayed_attacks` returns `available=False` (`landing_damage_missing_for:<id>`). It never recomputes damage and never reuses the original target's number. |
| Exact missing state/provenance | A **landing-time damage resolver** input bundle: (a) source identity/slot, move id/type/category/base power, source attacking stat + boosts *as recorded at schedule time*; (b) landing-time target identity/slot, defensive stats/boosts, types, item, ability, status, volatiles, current HP/max HP; (c) landing-time field: weather, terrain, screens on the target side, Gravity/room; (d) prevention/immunity context (type immunity, ability absorb, Protect/semi-invulnerable, substitute). |
| Proposed representation | Extend the queue entry already in `delayed_attacks[key]` with a `resolver_inputs` sub-dict carrying the schedule-time source snapshot, and resolve damage at landing against the **current** `active_slots[key]` occupant via the sim-core impact path (oracle) — not a stored scalar. Keep the existing `damage_by_target` fast path; add a second path `resolver_inputs` + `resolver_known: bool`. If neither target-specific damage nor a complete resolver bundle is present → fail closed (unchanged behavior). |
| Owner layer | rollout state (queue entry + resolver); oracle fixture only for the seeded landing damage check; action features only carry intent (`schedules delayed pressure`, already in v7 batch 7 `risk_delayed_pressure_scheduled` / `risk_future_damage_deferred_to_rollout`). |
| No-leakage concern | The replacement occupant and its private stats/item/ability may be **unrevealed** at schedule time. The resolver must consume only landing-time public/inferable state of whoever actually occupies the slot. Never store the original target's damage as the replacement's. Never read the seeded future occupant from the replay before it is public. |
| Recommended batch | **B** |

### GAP group 2 — Reflection / callback routing (Magic Bounce)

Fixture: *Magic Bounce reflection*.

| Aspect | Detail |
| --- | --- |
| Current GAP reason | `apply_immediate_prevention` only models hard-fail no-ops (prevented true/false). Magic Bounce is not a no-op: it **reflects** a status/hazard move back at the original source. There is no representation of the reflected action's new target, destination side, or the side-effect to apply there. |
| Exact missing state/provenance | The reflectable-move classification (`flags.reflectable`), the **original source** identity/side/slot (becomes the new target), the **reflector** identity (becomes the new source), the destination side for side-effects (hazards bounce to the originator's side), and the side-effect payload (status/hazard/stat) to re-apply. Plus reflector ability provenance: known / inferred / unknown (Magic Bounce, or Prankster-routed). |
| Proposed representation | Model reflection as a **transition event**, not an action-feature outcome: a `reflection` result from a routing helper that returns `{reflected: bool, new_source, new_target, destination_side, effect}` and then re-enters the normal application path with swapped source/target. Add a `reflectable` provenance bit on the move and an `ability_known` tri-state on the potential reflector. Fail closed when reflectability or reflector ability is unknown. |
| Owner layer | rollout state (routing + re-application); action features carry only "this move is reflectable / may be bounced" intent, never the resolved bounced damage/effect. |
| No-leakage concern | Reflector ability may be unrevealed → do not assume Magic Bounce for an opponent whose ability is hidden; encode `ability_known=unknown` and fail closed rather than reflecting. Do not leak the reflected effect's resolution into the pre-action candidate vector. |
| Recommended batch | **C** |

### GAP group 3 — Ability / status prevention routing (Good as Gold)

Fixture: *Good as Gold status-move blocking in arbitrary rollout states*.

| Aspect | Detail |
| --- | --- |
| Current GAP reason | Good as Gold blocks all status moves from the opponent, but only when the defender's ability is reliably known. The local path has no generalized ability/status callback routing and no ability-suppression state (Mold Breaker, Neutralizing Gas, Gastro Acid, Core Enforcer), so it cannot decide blocking in arbitrary rollout states. |
| Exact missing state/provenance | Per-mon **effective ability** = (base/revealed ability, `ability_known` tri-state, suppression state). Suppression inputs: `ability_suppressed` (Gastro Acid / Core Enforcer), `ability_ignored_this_action` (Mold Breaker-class attacker), `neutralizing_gas_active` (field). Move classification: `category == status`, `flags.reflectable` (interaction with group 2), target side. |
| Proposed representation | A `resolve_effective_ability(mon, attacker, field)` helper returning `{ability, known, suppressed, ignored}`; a status-block check keyed on the effective ability set (`goodasgold`, plus the existing curated absorb/soundproof/bulletproof lists migrated to flag-driven checks over time). Status move into a defender with effective `goodasgold` and `known=True` → blocked; `known=unknown` → fail closed. |
| Owner layer | tactical state (effective-ability belief, suppression flags) + rollout state (the block decision); action features may carry a known click-time blocker (`execution_blocked_known` family proposed in the v7 audit) but never infer a hidden ability. |
| No-leakage concern | Unrevealed defender ability must not be assumed to be Good as Gold (or assumed *not* to be). Encode `ability_known=unknown`; the block stays fail-closed. Suppression that is only visible in the seeded sim must not be read unless it became public. |
| Recommended batch | **C** |

### GAP group 4 — Exact sequential multi-hit execution (Population Bomb / Triple Axel)

Fixtures: *Population Bomb exact sequential-hit execution*, *Population Bomb
initial-miss stop-on-miss execution*, *Triple Axel exact power-ramp execution*,
*Triple Axel initial-miss stop-on-miss execution*.

| Aspect | Detail |
| --- | --- |
| Current GAP reason | These moves use `multiaccuracy` (each hit re-rolls accuracy and **stops on first miss**) and, for Triple Axel, per-hit power ramp via `basePowerCallback` (20/40/60). The local rollout has no per-hit accuracy branch, no stop-on-miss execution, no per-hit damage/power trace, and no PRNG provenance; the v7 action slice can only *summarize* risk (`risk_multihit_*`), which is not exact rollout execution. |
| Exact missing state/provenance | Per-hit ordered execution inputs: `multihit_count` (or min/max array), `multiaccuracy` flag, per-hit accuracy, `basePowerCallback` power ramp sequence, `stops_on_miss`, per-hit contact event, and Loaded Dice / Skill Link modifiers (`loaded_dice` removes multiaccuracy and floors hit count; `skill_link` sets array moves to max). For exact parity the **seeded PRNG / accuracy roll sequence** must come from the oracle fixture. |
| Proposed representation | An `oracle fixture only` per-hit trace `hits: [{accuracy_roll, hit: bool, base_power, damage, contact}]` produced by the seeded sim-core run; a local `execute_sequential_multihit(state, move, hit_trace)` that replays the trace deterministically with stop-on-miss. Without a hit trace, local rollout fails closed and the candidate keeps only the v7 distribution summary. Define the **fail-closed local behavior** explicitly: when no per-hit trace is available, do not emit a single collapsed damage; report GAP / `impact_unknown` and rely on the action-feature distribution. |
| Owner layer | oracle fixture only (the seeded per-hit trace and PRNG) + rollout state (deterministic replay of the trace); action features keep the existing v7 batch-7 distribution summary only. |
| No-leakage concern | The sampled hit count and per-hit accuracy rolls are hidden until execution — they live **only** in the seeded oracle fixture and the replay trace, never in a pre-action candidate feature. v7 multihit fields must remain distribution summaries (min/max/expected), never the sampled count. |
| Recommended batch | **E** |

---

## Forward-looking state/provenance (safe future materialization)

These are not all current rollout-parity GAP fixtures, but the handoff lists them
as required state/provenance to support future materialization safely and to
close the broader honest-uncertainty surface. They reuse the same no-leakage
contract.

### Status counters and ranges (Rest / natural sleep / confusion / Toxic)

| Mechanic | Missing state/provenance | Proposed representation | Owner | No-leakage |
| --- | --- | --- | --- | --- |
| Rest sleep | fixed-duration provenance distinct from natural sleep | `sleep_from_rest: bool`, `sleep_remaining_min/max` (both 2 in Gen 9 after the acting turn), `sleep_can_wake_this_turn`, `sleep_must_wake_by_turn` | tactical state + rollout state | Rest duration is public (fixed); safe to encode exactly |
| Natural sleep | elapsed turns + legal remaining range, not the sampled wake turn | `sleep_turns_elapsed`, `sleep_remaining_min/max` (1..3 − elapsed), `sleep_hidden_duration_unknown: True` | tactical state | **Never** store Showdown's sampled `statusState.time`; two seeds with the same public history must yield identical vectors |
| Confusion | elapsed + legal range + self-hit pressure | `confusion_turns_elapsed`, `confusion_remaining_min/max`, `confusion_can_end_this_turn`, `confusion_self_hit_chance` (0.33) | tactical state + search node | Never store sampled `volatiles.confusion.time` |
| Toxic | public elapsed stage already plumbed | reuse existing `toxic_stage` (rollout) + expose `toxic_stage_known` provenance | rollout state | stage is public once poisoned; safe |

Search may branch over end-now vs continue using the public range; it must not
read the sampled hidden end turn.

### Damage-received memory (Counter / Mirror Coat / Metal Burst / Bide)

| Aspect | Detail |
| --- | --- |
| Missing state/provenance | `last_damage_taken` = {amount, category (physical/special/other), source side/slot, same-turn order index}, plus `damage_taken_this_turn` accumulation for Bide, and `damaged_by_target_this_turn: bool`. Public vs hidden: the *fact* and amount of damage taken is public from the protocol; the opponent's same-turn move choice that triggers the branch is not. |
| Proposed representation | A tactical-state `damage_memory` dict refreshed per turn from the protocol; a `branch_condition_kind` (`incoming_damage`) reused from the v7 conditional-execution provenance proposal. Counter/Mirror Coat/Metal Burst damage stays **fail-closed** until the incoming-damage branch is fixed (i.e. inside a search node or after the opponent action is public). |
| Owner layer | tactical state (the memory) + search node (the branch resolution); action features carry `incoming_damage_branch_required` intent only. |
| No-leakage concern | Do not encode the opponent's replay-future move into the pre-action candidate. The damage amount, once dealt, is public and may be encoded; the *future* counter-trigger may not. |
| Recommended batch | **D** |

### Last-move / callable-pool provenance (Copycat / Mirror Move / Sleep Talk / Metronome)

| Aspect | Detail |
| --- | --- |
| Missing state/provenance | `last_move_used` / `last_move_successful` (public `lastMove`), targeting info, callable-pool membership (`flags.metronome` for Metronome; known own move slots minus `nosleeptalk`/charge for Sleep Talk; public `lastMove` for Copycat; party-move dependency for Assist), and `callable_pool_known` / `callable_distribution_unknown`. Format-scoped: Metronome/Assist/Nature Power are NatDex/custom, not strict Gen 9. |
| Proposed representation | Reuse the v7 batch-7 `risk_callable_*` action summary for click-time; add tactical-state `last_move` provenance and a `callable_pool` descriptor (known set + dependency flags). Rollout branches over the callable distribution only when the pool is public; otherwise `callable_distribution_unknown=True` and fail closed. |
| Owner layer | tactical state (last-move + pool provenance) + action features (summary) + search node (distribution branch); the actually-sampled called move is oracle fixture only. |
| No-leakage concern | Never encode the move Metronome/Sleep Talk/Assist will sample before it is revealed. Party-move-dependent pools must not leak unrevealed bench moves of the opponent. |
| Recommended batch | **C** (provenance) / **E** (exact called-move execution) |

---

## Recommended implementation sequence

This ordering front-loads the no-leakage safety net and the highest-value
deterministic resolver, and defers the PRNG-dependent multi-hit traces last.

### Batch A — no-leakage tests and state-provenance helpers (foundation)

- Add the no-leakage test scaffolding (see rules below) **before** any new state
  field is materialized: seed-invariance, future-prefix isolation, hidden-opponent
  perturbation, candidate symmetry, and rollout-oracle isolation.
- Add small provenance helpers with tri-state knownness (`known` /
  `inferred` / `unknown`) and the owner-layer tagging convention. No schema
  change, no materialization.
- Verify: focused unit tests pass; harness count unchanged (37 PASS / 8 GAP).

### Batch B — delayed landing resolver provenance (GAP group 1)

- Extend the `delayed_attacks` queue entry with `resolver_inputs` + `resolver_known`
  and a landing-time resolver that scores against the current slot occupant via
  the oracle. Keep the existing `damage_by_target` fast path and fail-closed
  default.
- Add Future Sight / Doom Desire replacement-without-target-specific-damage
  fixtures.
- Verify: the two delayed-future GAP fixtures move to PASS or stay explicit GAP
  with a more precise reason; **0 FAIL** preserved.

### Batch C — ability / prevention / reflection routing (GAP groups 2 & 3)

- Add `resolve_effective_ability` (suppression-aware) and a status-block check;
  add a `reflection` routing helper that returns the bounced source/target/effect
  and re-enters the application path.
- Add Good as Gold (known/unknown ability) and Magic Bounce reflection fixtures.
- Verify: Good as Gold and Magic Bounce GAP fixtures resolve or stay explicit GAP
  with sharper reasons; **0 FAIL** preserved; no unrevealed-ability assumptions.

### Batch D — status counters / ranges and damage-received memory

- Add tactical-state sleep/confusion/Toxic range provenance and the
  `damage_memory` surface. Pair every counter with its `*_known` /
  `*_hidden_duration_unknown` flag.
- Add Rest-vs-natural-sleep, confusion-range, and Counter/Mirror Coat fixtures.
- Verify: seed-invariance no-leakage tests pass for sleep/confusion; branch moves
  stay fail-closed outside search nodes.

### Batch E — exact sequential multi-hit traces (GAP group 4)

- Add the oracle-fixture per-hit trace and `execute_sequential_multihit` replay
  with stop-on-miss; define the fail-closed local behavior when no trace exists.
- Add Population Bomb / Triple Axel exact and initial-miss fixtures.
- Verify: the four multi-hit GAP fixtures resolve via seeded traces; v7 multihit
  summaries remain distribution-only; sampled counts never appear in features.

Sequencing rationale: A is a prerequisite safety gate; B reuses the
already-built delayed queue and yields the cleanest deterministic win; C and D
share the tri-state ability/branch provenance machinery; E is last because it
depends on seeded PRNG provenance that only the oracle can supply.

---

## No-leakage rules (binding for every batch)

1. **Seed invariance.** Two oracle seeds with identical public history but
   different sampled hidden durations / hit counts / called moves must produce
   **byte-identical** state and action feature vectors. (sleep, confusion,
   multi-hit, callable moves.)
2. **Future-prefix isolation.** Appending future turns, revealed moves, the
   winner, or the opponent's chosen action to a replay must not change any
   pre-action state/candidate vector built at the earlier decision.
3. **Hidden-opponent perturbation.** Perturbing an unrevealed opponent
   item/ability/move/bench in a shadow object must not change any field unless it
   is represented as a belief derived from legal public evidence. Specifically,
   an unrevealed defender ability is `known=unknown` — never assumed to be (or
   not to be) Good as Gold / Magic Bounce.
4. **Owner-layer containment.** Values owned by **oracle fixture only** (seeded
   PRNG, per-hit trace, sampled durations, landing-time hidden occupant) or
   **search node** (hypothetical opponent branch) must never be flattened into
   **action features** or **tactical state**.
5. **No stale reuse.** The delayed-landing resolver must never reuse the original
   target's damage for a replacement occupant; it recomputes against the current
   slot occupant or fails closed.
6. **Fail closed over wrong-exact.** When a required branch/provenance is absent,
   the local transition reports explicit GAP / `impact_unknown` (preserving
   **0 FAIL**); it never emits a guessed exact result. 0 FAIL outranks reducing
   GAP count.
7. **Label separation.** Winner, rank label, chosen-action index, future
   HP/status, and continuation value remain absent from feature-builder inputs and
   serialized features.

---

## What did NOT change

- No `legal-action-v7` schema/dim/fingerprint change (stays 552D /
  `956da3d2…1bf39d7`).
- No state schema implemented; this is design only.
- No dataset materialization, no training, no checkpoint promotion.
- No live default, live bot behavior, or live-path change.
- NatDex/old-gen remains documented (format-scoped) but unimplemented.

Both the rollout-parity gate and the overall diagnostic training gate remain
**closed**. Implementation of batches B–E is approval-gated and out of scope for
this design pass.

## Addendum — Batch A implemented (guardrails only)

Batch A is now implemented as an isolated guardrail layer, ahead of any state
schema. It adds `trainer/src/neural/provenance_contracts.py` (small, torch-free
pure functions / frozen dataclasses; no simulator rewrite, no schema migration)
and `trainer/tests/test_state_provenance_no_leakage_contracts.py` (23 tests). The
helpers realize the contracts above as fail-closed validators:

- `delayed_landing_resolvable` — target-specific or complete-resolver-bundle, else
  unavailable; never reuses original-target damage (also verified against the
  production `resolve_delayed_attacks`).
- `natural_sleep_provenance` / `rest_sleep_provenance` / `confusion_provenance` plus
  `assert_no_hidden_sampled_values` — public range + `hidden_duration_unknown` for
  natural sleep/confusion, fixed duration for Rest, and a structural guard that
  rejects any leaked sampled wake turn (`FORBIDDEN_HIDDEN_KEYS`).
- `EffectiveAbility` / `AbilityKnownness` / `status_move_blocked_by_ability` —
  tri-state knownness with suppressed/ignored handling; unknown ability fails
  closed (`blocked=None`).
- `validate_reflection_provenance` — requires full routing provenance + known
  reflector ability, else fail closed.
- `validate_multihit_trace` — requires a per-hit accuracy/damage trace and rejects
  a distribution summary as an exact trace.

Batch A closes **no** rollout GAP (still 8 GAP) and changes no schema; it only
prevents the leakage/stale-damage shortcuts that batches B–E must respect.

## Addendum — Batch B implemented (delayed landing resolver)

GAP group 1 (delayed landing resolver) is now implemented; see
`rollout_parity_batch_6_delayed_landing_resolver_report.md`. The
`delayed_landing_resolvable` helper gained the `resolver_exact` /
`resolver_inputs_present` / `resolver_target_mismatch` outcomes, and
`delayed_damage.py` schedules from and resolves a complete landing-time resolver
bundle whose `target_snapshot` matches the actual occupant and that carries a
Showdown-derived exact `landing_damage`. Two PASS fixtures were added
(`future_sight_resolver_bundle_replacement`,
`doom_desire_resolver_bundle_replacement`); harness is now **47 cases,
39 PASS / 0 FAIL / 8 GAP**. The two `*_replacement_damage_unavailable` cases
**stay GAP** (they carry only original-target damage), so no GAP was closed by
weakening correctness. Oracle-derived `landing_damage` stays fixture/queue-only
and is never flattened into action/state features. No schema migration, no
`legal-action-v7` change. Batches C–E remain approval-gated.

## Addendum — Batch C implemented (ability/prevention/reflection routing)

GAP groups 2 (reflection routing) and 3 (ability/status prevention routing) are
now implemented; see `rollout_parity_batch_7_ability_reflection_routing_report.md`.
`provenance_contracts.py` gained `effective_ability_from_state` (tri-state
knownness + suppressed/ignored, hides unrevealed ability identity) and
`resolve_status_move_ability_block` (known-active Good as Gold blocks status
moves; suppressed/ignored does not; unknown falls through, never a guess).
`prevention.py` routes Magic Bounce reflectable moves through
`validate_reflection_provenance` (complete routing → `reflected=True` +
destination side; incomplete → fail closed) and applies the Good as Gold block;
`_compare_immediate` now checks `reflected`/`blocked`. Two PASS fixtures were
added (`good_as_gold_known_blocks_status`, `magic_bounce_reflects_stealth_rock`)
and the unknown/incomplete `good_as_gold_status_gap` / `magic_bounce_reflection_gap`
**stay GAP**; harness is now **49 cases, 41 PASS / 0 FAIL / 8 GAP**. Unrevealed
abilities and reflection payloads stay transition/fixture-only and are never
flattened into action/state features. No schema migration, no `legal-action-v7`
change. Batches D–E remain approval-gated.

## Addendum — public-information belief & effective-context guardrails

A public-information belief layer and effective-context layer are now designed
(`public_information_belief_effective_context_design.md`) with pure, torch-free
guardrail contracts added to `provenance_contracts.py`: `PublicAbilityBelief`,
`PublicItemBelief`, `PublicSpeedBelief` (known/possible/inferred/hidden tiers,
exact speed only when public), and `EffectiveAbilityContext`,
`EffectiveItemContext` + `item_blocks`, `EffectiveWeatherContext` (ability
suppression/bypass with Ability Shield, item effects incl. Heavy-Duty Boots /
Safety Goggles / Covert Cloak / Magic Room, Cloud Nine / Air Lock weather
suppression). All apply suppression/bypass/blocking only when the relevant
effect is *known active* and fail closed on unknown — extending the same
no-leakage invariant used by the Good as Gold / Magic Bounce routing in batch C.
Backed by `test_public_information_belief_contracts.py` (25 tests). This is a
contract+test guardrail only: no live-extraction rewrite, no `legal-action-v7`/
state/action schema change, no materialization/training/promotion/live-default
change. Both gates remain **closed**.
