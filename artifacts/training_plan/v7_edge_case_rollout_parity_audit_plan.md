# v7 Edge-Case and Rollout-Parity Audit Plan

## Purpose and scope

This plan audits the remaining mechanics boundary before any further
`legal-action-v7` implementation, rematerialization, or training.

Current schema:

- action schema: `legal-action-v7`, **452D**
- ordered-name fingerprint:
  `e3e39124cd24e3e27684306e3d401859083df65965e721eb3e5e8b89c48fcb4c`
- frozen prefixes: v6 331D; v7 batch 1 361D; batch 2 375D; batch 3 388D;
  batch 4 406D; batch 5 420D

Primary oracle inspected:

- bundled Pokémon Showdown `data/moves.ts`
- bundled Pokémon Showdown `data/conditions.ts`
- bundled Pokémon Showdown `data/abilities.ts`
- sim-core damage result (`move_type_resolved`, applied effectiveness)
- current tactical-state, impact, approximate branch, and exact replay-rollout
  code

No internet source was required: the local bundled Showdown source is the
authoritative implementation used by this project.

## Non-negotiable architecture boundary

Action features and rollout transitions answer different questions:

| Layer | Question | May use |
| --- | --- | --- |
| `legal-action-v7` | “What does this candidate imply if clicked now?” | current legal request, current public/reconstructed state, legal own private state, move metadata, honest uncertainty |
| impact calculation | “What immediate damage/hit result is supported now?” | current attacker/target/field inputs; fail closed when the current branch is unresolved |
| rollout/state transition | “What happens after both actions, residual order, switches, and future events resolve?” | explicit opponent-action branches or Showdown simulation |

An action vector may say “applies Salt Cure”, “starts Future Sight”, “pivots”,
or “has crash damage”. It must not claim the later residual amount, switch-in
ability result, opponent-selected action, or future target unless that result is
already fixed by current information.

## Executive risk summary

1. **Approximate rollout is not mechanics-parity rollout.** It uses heuristic
   hazard, status, recovery, pivot, and opponent-action scoring. Its switch
   hazard estimate simplifies Stealth Rock to 1/8 and Spikes to 1/8 per layer,
   rather than Showdown's full type/layer rules. It does not execute residual
   order or switch-in abilities.
2. **Residual identity is often represented, residual evolution is not.**
   v7 identifies toxic, burn, poison, Leech Seed, trap, Salt Cure catch-all,
   weather, terrain, and Future Sight, but does not itself advance counters,
   durations, or end-of-turn HP.
3. **Hard-fail prevention is fragmented.** Tactical redundancy flags cover
   selected known abilities/moves; the damage oracle covers some immediate
   immunities; v7 priority covers Psychic Terrain. There is no single
   Showdown-backed “candidate succeeds under current known blockers” surface.
4. **Random-call moves have no distribution contract.** Beat Up and Fickle Beam
   fail closed, but Sleep Talk, Metronome, Copycat, Nature Power, and older call
   moves require an explicit exact/distribution/unavailable policy.
5. **Switch sequencing is the largest rollout gap.** Hazards, Boots, pivot
   ordering, Regenerator/Natural Cure, Intimidate/Trace/Download, and weather
   setters belong to transition simulation. They should not be approximated by
   adding action columns for their resolved outcomes.
6. **NatDex widens state requirements.** Hidden Power IV typing, Natural Gift
   berry type/power/consumption, Pursuit interception, Baton Pass transfer,
   older random-call pools, and generation-specific conditions require format-
   scoped oracle tests rather than global move-id rules.
7. **Exact rollout can use information unavailable to live inference.** Seeded
   replay simulation is valid as an offline oracle, but its hidden teams/RNG
   must never be copied into current action features or treated as a live
   information source.

## Handling labels used below

- **AF represented** — current v7 describes the click-time implication.
- **AF needed** — a new typed action field/provenance field is justified.
- **Rollout** — Showdown transition/residual execution is the primary owner.
- **Both** — action intent plus transition parity are both required.
- **Exact** — current known branch can be calculated exactly.
- **Fail-closed** — current immediate impact is explicitly unavailable rather
  than wrong-exact.
- **Approx-only** — only heuristic rollout logic exists; it is not parity.

---

## 1. Residual and end-of-turn effects

| Mechanic | Current handling | Gen 9 Randbats | NatDex/future | Owner | Required probe |
| --- | --- | --- | --- | --- | --- |
| Salt Cure | AF represented only as `effect_target_volatile_other`; immediate damage remains exact | Yes | Yes | Both; dedicated AF desirable | Apply to neutral vs Water/Steel; run 3 residual turns; switch/cure/faint ordering |
| Toxic poison | typed `tox` application; current state distinguishes `tox`; no v7 toxic counter transition | Yes | Yes | Both, mostly rollout | counter 1→2→3, switch reset semantics, Magic Guard, poison immunity |
| Regular poison | typed `psn`; residual not advanced by AF | Yes | Yes | Rollout after represented application | one-turn chip, Magic Guard, Poison Heal |
| Burn | typed `brn`; immediate physical burn penalty can enter damage; residual not advanced | Yes | Yes | Both | chip, Magic Guard, Heatproof if applicable, Facade/Guts interaction |
| Leech Seed | dedicated target AF; state tracks seeded volatile | Yes | Yes | Both | drain ordering, source faint/switch, target switch, Liquid Ooze, Magic Guard |
| Binding residual | typed trap chance; duration/source/item details absent | Yes | Yes | Both | 4/5-turn duration distribution, Grip Claw/Binding Band, source leaves field |
| Ghost Curse | not in typed volatile slice; impact special-cases current Curse form | Yes | Yes | Both; dedicated AF needed | Ghost/non-Ghost user, 1/2 HP cost, residual, switch removal |
| Weather chip | weather setup/type represented; no AF residual claim | Sand relevant; snow has no Gen 9 chip | Older hail/NatDex relevant | Rollout | sand immunity, old hail by format, weather ending before/after residual |
| Grassy Terrain healing | terrain setup represented | Yes | Yes | Rollout | grounded checks, Heal Block, terrain expiry order |
| Aqua Ring | generic self volatile catch-all if candidate exists | Not in current 350-move pool | Relevant | Both; dedicated AF if format enabled | residual heal, Heal Block, Baton Pass transfer |
| Ingrain | generic self volatile catch-all if candidate exists; grounding implications incompletely centralized | Not in current pool | Relevant | Both | healing, forced grounding, switch prevention, Baton Pass |
| Future Sight / Doom Desire | delayed-future AF + two-turn delay; immediate impact fail-closed | Future Sight yes | Both | Both, primarily rollout | slot targeting, target switch, Protect timing, source faint/switch, simultaneous KO |

### Residual conclusion

Do not add predicted residual HP totals to action features. Add dedicated action
identity/provenance only where the current catch-all loses a materially distinct
mechanic (recommended: Salt Cure, Ghost Curse, Aqua Ring, Ingrain). Use exact
Showdown rollout tests for HP progression and event ordering.

---

## 2. Random-call and random-outcome moves

| Move/family | Current handling | Current pool | Future relevance | Required policy |
| --- | --- | --- | --- | --- |
| Metronome | no called-move distribution field; metadata action looks non-damaging | No | NatDex/custom | distribution or explicit random-call unavailable |
| Sleep Talk | status/non-damaging candidate; called move outcome not represented | Yes | Yes | distribution over currently callable known own moves; exact branch in rollout |
| Assist | no distribution support | No | older/custom; often unavailable in modern NatDex rules | inspect format legality, then party-call distribution |
| Copycat | no called-last-move resolution | No | NatDex/custom | exact if last move and legality are known; otherwise fail closed |
| Mirror Move | no copied-opponent-move resolution | No | older/custom | exact only with tracked last targeted move |
| Nature Power | static status metadata would be misleading as resolved effect | No | NatDex | resolve called move from terrain/format through Showdown |
| Fickle Beam | immediate damage intentionally fail-closed (`random_power`) | Yes | Yes | probability distribution (normal/double) or remain fail-closed |
| Beat Up | immediate damage intentionally fail-closed (`party_attack_stats`) | Yes | Yes | party-member hit distribution and per-member Attack/status eligibility |

### Random-call test contract

Every call/random move must be classified into exactly one machine-readable
mode:

1. `exact_called_move` — current state fixes the called move.
2. `finite_distribution` — enumerate outcomes and probabilities.
3. `rollout_random_branch` — Showdown samples during rollout.
4. `unavailable_fail_closed` — action ranker sees explicit uncertainty.

No call move may silently inherit its wrapper's `category=Status`, zero damage,
or one sampled result as if deterministic.

---

## 3. Dynamic type and special effectiveness

Current immediate damage uses sim-core's **resolved move type**, not stale static
metadata, for Weather Ball, Terrain Pulse, Judgment, Ivy Cudgel, Raging Bull,
Revelation Dance, Aura Wheel, and Tera Blast. Freeze-Dry's special
Water effectiveness is explicitly corrected in sim-core. Photon Geyser's
category/stat selection is tested. Tera Starstorm remains fail-closed for
Stellar effectiveness/STAB.

| Mechanic | Current status | Gen 9 pool | NatDex/future action |
| --- | --- | --- | --- |
| Weather Ball | resolved type/effectiveness exact when weather state is known | Yes | add strong-weather suppression probes |
| Terrain Pulse | resolved type/power uses terrain and grounding | Yes | retain grounded/airborne parity tests |
| Tera Blast | resolved Tera type supported | Yes | test Stellar/Tera state separately |
| Revelation Dance | resolved from user current type | Yes | test post-typechange and Tera |
| Judgment | resolved from held Plate | Yes | test item suppression/removal |
| Ivy Cudgel | resolved mask-dependent type | Yes | test each mask and item suppression |
| Raging Bull | resolved form type; screen removal now typed | Yes | test all Paldean Tauros forms |
| Freeze-Dry | special Water effectiveness exact | Yes | retain Water dual-type cases |
| Tera Starstorm | fail-closed for Stellar | Yes | needs Stellar-native oracle output |
| Aura Wheel | resolved form type | Yes | test form provenance |
| Hidden Power | generic/typed definitions exist locally; current pipeline does not expose IV-derived type contract | No | required before NatDex |
| Natural Gift | berry-dependent type/power plus item consumption not implemented | No | required before NatDex |

### Dynamic-type probes

- Assert `move_type_resolved`, STAB, type effectiveness, and damage all agree.
- Perturb only the relevant item/form/terrain/weather/current type and require
  the resolved result to change.
- Add a guard that static metadata type is never substituted when sim-core
  returned a different resolved type.
- Scope Hidden Power and Natural Gift behavior by generation/format.

---

## 4. Conditional branch-dependent damage and execution

| Move/family | Current handling | Correct owner |
| --- | --- | --- |
| Sucker Punch / Thunderclap | fail-closed: hidden opponent action | opponent-action rollout branch; intentionally INEXACT in rank-only AF |
| Focus Punch | fail-closed: whether user is hit before acting | rollout/action-order branch |
| Fake Out / First Impression | fail-closed: first-active-turn state not plumbed into impact | AF condition can be exact if switch-in turn provenance is added; rollout verifies |
| Payback | fail-closed: same-turn order | rollout |
| Avalanche | fail-closed: user hit earlier this turn | rollout |
| Lash Out | fail-closed: stat drop earlier this turn | rollout |
| Stomping Tantrum / Temper Flare | fail-closed: prior move failure history | current-state/history AF plus rollout |
| Counter / Mirror Coat / Metal Burst | fail-closed: damage received this turn | rollout; exact after incoming-damage branch |
| Photon Geyser | exact current category/stat selection | AF/impact already covered |
| Beat Up | fail-closed | party-state distribution, then rollout |
| Pursuit | not in Gen 9 pool; no interception branch | NatDex rollout/search branch |

Recommended action fields are provenance/condition fields, not guessed damage:

- `execution_condition_kind`
- `execution_condition_known`
- `first_active_turn_known/value`
- `prior_move_failed_known/value`
- `same_turn_opponent_action_required`
- `incoming_damage_branch_required`

The damage result should remain unavailable until the relevant branch is fixed.

---

## 5. Field/ability hard-fail and prevention

Current tactical redundancy flags cover selected known Good as Gold,
Soundproof, Bulletproof, absorb abilities, Prankster-vs-Dark, existing status,
and obvious type immunity. These lists are curated, not a complete Showdown
event pipeline.

| Case | Current status | Relevance | Required work |
| --- | --- | --- | --- |
| Desolate Land blocks Water | weather identity represented; exact hard-fail parity not directly regression-tested | NatDex/future | sim-core immediate success probe |
| Primordial Sea blocks Fire | same | NatDex/future | sim-core immediate success probe |
| Psychic Terrain blocks priority | v7 typed when target grounding is provable | Gen 9 | broaden grounding and ability-block probes |
| Misty/Electric Terrain status prevention | terrain represented; status application prevention not typed/exact centrally | Gen 9 | candidate success field + rollout tests |
| Good as Gold | selected status moves flagged when ability is known | Gen 9 | replace move-name allowlist with Showdown reflectable/status behavior |
| Queenly Majesty / Dazzling / Armor Tail | not represented in v7 priority blocker | Gen 9/future | typed priority-prevention source |
| Damp | no intrinsic candidate hard-fail field | Gen 9/future | explosion/self-destruct prevention probe |
| Powder | move/volatile and Fire-move trigger interaction not represented | future/NatDex | both AF and rollout |
| Soundproof | selected move-name list only | Gen 9 | use Showdown `sound` flag |
| Bulletproof | selected move-name list only | Gen 9 | use Showdown `bullet` flag |
| Magic Bounce | broad `status` block approximation; reflection target/result not modeled | Gen 9 | reflected-action rollout branch |
| Magic Guard | intrinsic recoil/residual prevention not applied to v7 HP fields | Gen 9 | current-known prevention provenance + rollout |
| Substitute | presence represented; bypass/contact/status/secondary interactions incomplete | Gen 9 | Showdown flag-driven target-validity tests |

### Prevention rule

Add a single Showdown-backed candidate-execution diagnostic before expanding
more hardcoded blocker lists:

- `execution_supported`
- `execution_blocked_known`
- `execution_block_source`
- `execution_reflected`
- `execution_uncertain`

This should describe known click-time prevention. Reflected or redirected
effects still require rollout to resolve the new target/result.

---

## 6. Switch, entry, exit, and pivot effects

| Mechanic | Current handling | Owner |
| --- | --- | --- |
| Hazard entry | state/action awareness exists; approximate rollout uses simplified damage | rollout |
| Heavy-Duty Boots | approximate switch diagnostic suppresses hazards when own item is known | both state provenance and rollout |
| Regenerator | not applied by approximate switch transition | rollout |
| Natural Cure | not applied by approximate switch transition | rollout |
| Intimidate | not executed by approximate switch transition | rollout |
| Trace / Download | not executed by approximate switch transition | rollout |
| Drizzle/Drought/Sand Stream/Snow Warning | weather ability source tracked only after protocol events; not predicted by approximate switch | rollout |
| U-turn / Volt Switch / Flip Turn | pivot intent represented; exact selected replacement and entry sequence absent from AF | both, primarily rollout/live branch |
| Parting Shot | pivot + stat effect represented separately; replacement sequence absent | both |
| Teleport / Chilly Reception | pivot intent; Chilly Reception weather setup is a callback case requiring verification | both |
| Baton Pass | absent from Gen 9 pool; volatile/stat transfer not modeled | NatDex rollout |
| Pursuit interception | absent from Gen 9; unsupported | NatDex rollout/search |

### Switch parity sequence to test

For each relevant switch/pivot, compare exact Showdown logs and reconstructed
state after:

1. move damage/status/stat effect;
2. forced/user-selected replacement;
3. switch-out abilities (Regenerator/Natural Cure);
4. hazards and Boots;
5. switch-in abilities (Intimidate, Trace, Download, weather/terrain);
6. resulting field, HP, status, boosts, item, and legal request.

Live recommendation branch logic must represent the need for a replacement
choice after pivots. The action vector must not choose or assume that replacement.

---

## 7. Accuracy, immunity, and target validity

| Case | Current status | Gap/test |
| --- | --- | --- |
| Base and weather-dependent accuracy | represented; rain/sun/snow probes exist | retain |
| Gravity | field state/setup represented | verify accuracy multiplier, Ground-vs-Flying, and move-disable rules |
| No Guard | ability can reach Showdown damage calc, but no focused parity test | user/target No Guard, semi-invulnerable exceptions |
| Lock-On / Mind Reader | volatile may be generic catch-all; next-hit guarantee not typed | dedicated state/action provenance plus rollout |
| Fly/Dig/Dive/Bounce/Phantom Force | charge timing represented generically; target semi-invulnerability is not | rollout target-validity matrix |
| Protect-like moves | candidate protect identity represented | opponent move branch, bypass, consecutive success probability |
| Type immunities | damage oracle and selected tactical flags | ability/item/field bypass matrix |
| Grounded/airborne | partial helper handles type, Levitate, Balloon, Iron Ball, selected volatiles | add Gravity, Roost, Thousand Arrows, Ring Target, ability suppression |
| Type-changing effects | public current type is tracked and used by impact | add Soak/Trick-or-Treat/Forest's Curse/Burn Up/Double Shock sequence tests |

Protect and semi-invulnerable interactions should not be encoded as an
unconditional hit/miss action feature because they depend on the opponent's
same-turn action and move flags.

---

## 8. No-leakage and exact-input audit

### Existing safeguards

- Every v7 batch asserts ordered-name fingerprints and frozen prefix equality.
- Checkpoint metadata validation rejects name/dimension/fingerprint mismatch.
- Materialization builds an exact pre-action event prefix and stops before the
  current decision's Tera event.
- State reconstruction uses public protocol prefixes plus legal own request data.
- v7 typed slices are built from move metadata and current reconstructed state,
  not post-turn state.

### Required tests before v7 materialization

1. **Full schema decode round-trip**
   - build representative candidates;
   - decode all 452 values by ordered name;
   - re-encode and require exact float-array equality;
   - assert unique names and expected slice boundaries/fingerprint.
2. **Hidden-opponent perturbation**
   - hold the public protocol and legal request fixed;
   - perturb unrevealed opponent item/ability/moves/team in a shadow object;
   - require all state/action fields to remain identical unless the information
     is represented as a belief distribution derived from legal public evidence.
3. **Own-private legality**
   - own request item, ability, stats, moves, and bench may change own-private
     fields;
   - opponent request/private team must never be consumed.
4. **Future-prefix isolation**
   - append future turns, revealed moves, winner, and opponent chosen action to
     the source replay;
   - build the same pre-action prefix;
   - require current state/action vectors to be identical.
5. **Candidate symmetry**
   - changing which legal action was actually chosen must not change any
     candidate vector at that decision.
6. **Opponent-action isolation**
   - Sucker Punch/Thunderclap/Focus Punch vectors may say “branch required”;
   - they must not change based on the hidden action later observed.
7. **Rollout-oracle isolation**
   - seeded exact rollout may use hidden simulator state internally;
   - no hidden simulator fields may be returned as model input features;
   - approximate/live mode must remain usable without replay seed.
8. **Label separation**
   - winner, rank label, chosen-action index, future HP/status, and continuation
     value must be absent from feature-builder inputs and serialized features.

---

## Explicit regression tests to add

### Gen 9 Randbats — action feature/impact

- Salt Cure dedicated identity versus generic volatile.
- Ghost Curse versus non-Ghost Curse.
- Sleep Talk explicit random-call/unavailable mode.
- Fickle Beam and Beat Up remain fail-closed.
- Future Sight delayed-not-immediate plus slot condition intent.
- Misty/Electric Terrain status prevention.
- Good as Gold using Showdown status/reflectability rather than a move allowlist.
- Queenly Majesty/Dazzling/Armor Tail versus positive priority.
- Soundproof and Bulletproof from move flags.
- Magic Guard versus recoil/self-damage/residual provenance.
- Substitute bypass/non-bypass move flags.
- Gravity and No Guard accuracy/grounding.
- Protect/bypass flags without assuming opponent Protect.
- type-change sequence affects resolved damage type/effectiveness.

### Gen 9 Randbats — rollout/state transition

- toxic ramp over three residual turns and switch reset.
- burn/poison/Salt Cure/Leech Seed/binding residual order.
- sand chip and Grassy Terrain healing.
- Future Sight source/target switching and landing turn.
- Rapid Spin/Mortal Spin removal only after successful hit.
- Defog both-side removal and terrain clearing.
- pivot replacement request and entry ordering.
- hazards with exact Stealth Rock type effectiveness and Spikes layers.
- Boots, Regenerator, Natural Cure, Intimidate, Trace, Download, and weather
  setter switch sequences.
- simultaneous KO, residual KO, and forced-switch request ordering.

### NatDex/future-format

- Hidden Power IV/type round-trip.
- Natural Gift berry type/power/consumption.
- Pursuit switch interception and double power.
- Baton Pass boost/volatile transfer allowlist.
- Assist/Copycat/Mirror Move/Nature Power legality and call pools.
- old hail residual by generation.
- generation-specific toxic counter and Defog behavior.

---

## Cases requiring direct Showdown source inspection

Before implementation, inspect and cite the exact callbacks/conditions for:

1. `conditions.ts`: `tox`, `partiallytrapped`, `futuremove`, weather and terrain
   residual ordering.
2. `moves.ts`: Salt Cure, Leech Seed, Curse, Aqua Ring, Ingrain, Future Sight,
   Sleep Talk, Metronome, Copycat, Nature Power, Beat Up, Fickle Beam.
3. `moves.ts` plus `battle-actions.ts`: Hidden Power, Natural Gift, Pursuit,
   Counter/Mirror Coat/Metal Burst, semi-invulnerable moves, Protect bypass.
4. `abilities.ts`: Desolate Land, Primordial Sea, Good as Gold, priority-blocking
   abilities, Damp, Soundproof, Bulletproof, Magic Bounce, Magic Guard, No Guard.
5. switch event ordering for Regenerator, Natural Cure, Intimidate, Trace,
   Download, and weather/terrain setters.
6. format/mod files for NatDex legality and generation overrides; do not infer
   NatDex behavior solely from the base Gen 9 move object.

---

## Recommended implementation order

### 1. Rollout-parity harness before another broad schema slice

Build a small, deterministic Showdown event-sequence harness that snapshots:

- pre-action state;
- immediate post-action state;
- end-of-turn state;
- post-switch/entry state;
- emitted protocol events and legal requests.

Cover residual, delayed damage, and switch sequencing first. This is test-only
infrastructure; it should not train or materialize data.

### 2. v7 batch 7 — execution/prevention and branch provenance

Recommended next action-feature batch:

- execution condition kind/known/unknown;
- current known blocker and source;
- reflected/redirected possibility;
- random-call mode;
- branch-required flags for opponent action, incoming damage, order, first-active
  turn, and prior failure;
- dedicated residual-identity fields for Salt Cure and Ghost Curse (Aqua Ring /
  Ingrain only if enabled formats require them).

Do not include predicted residual totals or guessed branch damage.

### 3. Exact switch/entry transition parity

Replace heuristic switch consequences in parity-sensitive evaluation with
Showdown transitions. Keep approximate rollout explicitly labeled and never use
it as a mechanics oracle.

### 4. NatDex format adapter

Add format-scoped mechanics capability declarations and tests for Hidden Power,
Natural Gift, Pursuit, Baton Pass, older call moves, and generation overrides.
Do not add these as unconditional Gen 9 move-id rules.

### 5. Re-run the mechanics classifier against v7

Only after the new tests exist, teach the audit classifier which former INEXACT
cases are now typed. A typed click-time field alone must not upgrade a mechanic
whose transition remains untested.

## Gate decision

The v7 representation is substantially richer, but rollout parity is not yet
demonstrated for residual order, switch sequencing, random-call distributions,
or complete prevention semantics. Therefore:

- no v7 materialization;
- no training;
- no checkpoint promotion;
- no live-default change.

The gate remains **closed**.
