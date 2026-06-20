# Possible Mechanic-Threat Awareness Audit

## Scope and verdict

This audit asks whether the frozen `legal-action-v7` / `live-private-belief-v7`
representation makes skilled-player responses to *possible* hidden mechanics
learnable without treating those mechanics as exact rollout truth.

**Verdict: partially represented; sufficient for an explicitly approved small
diagnostic v7/v7 materialization, but not a complete possible-threat schema.**

The existing state/action join can learn several interactions indirectly from
active species identity, current boosts, action category, and typed effects.
It also has one strong explicit possible-threat path for type-absorb abilities.
However, v7 does not expose calibrated action-conditioned possibility flags for
Unaware, Magic Bounce, Good as Gold, Levitate, Covert Cloak, Shield Dust, or
Inner Focus. Fields named `*_possible` in the secondary slice currently become
one only from a concrete known target item/ability.

This is not a wrong-exact or leakage defect and does not change rollout parity
(51 PASS / 0 FAIL / 8 honest GAP). It is a representation-completeness gap for
generalizing threat-aware policy. Do not change frozen v7; add an append-only
future `legal-action-v8` threat slice before treating a model as comprehensively
threat-aware.

## What v7 already represents

### Setup and boost-dependent actions

- Base action fields include `flag_setup` and `class_setup`.
- Typed v7 fields encode exact self/target stat-stage deltas and their chances.
- `live-private-belief-v7` carries current own and opponent stat stages.
- The rank model concatenates state and action embeddings, so a species identity,
  current boosts, and a setup/damaging action can interact in the rank head.

This makes “Dondozo-shaped opponent + boosted attacker + setup/damage action”
learnable from data, but the reason “possible Unaware” is not explicit.

### Species, own facts, and Illusion

- State v5 carries hashed active base/current/displayed species and roster
  species.
- It separately carries `displayed_species_uncertain` and
  `illusion_revealed`; Illusion is a guard, not a global assumption that every
  species is false.
- Own request-derived ability/item/moves/Tera are exact known facts.
- State tracks base/current ability, ability state/source, and suppression, so
  public ability changes are representable. Mega-style form/ability changes are
  a format-adapter concern, not a reason to make ordinary Gen 9 Randbats species
  permanently uncertain.

The skilled-player calibration contract also recognizes a reliable singleton
species/format ability set as deterministic public inference (Gholdengo → Good
as Gold), while disabling that collapse under unresolved Illusion. Full
propagation of that contract through live extraction remains deferred.

### Known/effective mechanics

- Known Good as Gold and Magic Bounce can set the existing tactical
  `target_known_or_possible_ability_blocks_move_effect` bit. Despite its name,
  the current blocker implementation reads known tactical abilities only.
- Known Good as Gold, Neutralizing Gas, Mold Breaker bypass, Ability Shield,
  Magic Bounce routing, Safety Goggles, Covert Cloak, and Shield Dust have
  fail-closed provenance/effective-context contracts.
- Exact rollout does not assume an ambiguous hidden ability/item.

### Possible absorb abilities

The tactical action field
`target_known_or_possible_ability_absorbs_move_type` explicitly reads both:

- known target abilities; and
- possible/revealed/inferred abilities from opponent set belief.

It covers Water Absorb/Dry Skin/Storm Drain, Volt Absorb/Motor Drive/Lightning
Rod, Flash Fire, and Sap Sipper families. This is the clearest existing example
of the correct action-selection distinction: possible risk is model-facing,
while exact execution remains fail-closed.

## Missing or incomplete possible-threat awareness

| Threat | Known/effective representation | Possible-threat representation | Audit |
| --- | --- | --- | --- |
| Unaware | May affect a damage-calculator input when a concrete ability is supplied; no dedicated feature | None | Missing explicit setup/boost interaction |
| Magic Bounce | Known tactical blocker + exact routing contract when provenance is complete | No belief-set action flag | Missing |
| Good as Gold | Known blocker; singleton public-inference contract exists | No action flag consuming singleton/possible belief | Missing explicit wiring; species hash is indirect |
| Water/Volt Absorb, Flash Fire, Sap Sipper | Known and possible combined action risk bit | Yes | Covered, but known vs possible are conflated |
| Levitate | Known grounding/hazard helpers in selected paths | Not included in the possible absorb type map | Missing Ground-move threat |
| Covert Cloak | Known target item zeros represented secondary chance | No possible-item identity flag | Missing |
| Shield Dust | Known target ability zeros represented secondary chance | No possible-ability identity flag | Missing |
| Inner Focus | No dedicated flinch-blocking action feature | None | Missing |

The batch-8 fields
`secondary_chance_blocked_by_shield_dust_possible` and
`secondary_chance_blocked_by_covert_cloak_possible` are misleadingly broad:
their builders require a concrete target ability/item. Unknown/possible set
belief does not activate them.

The state belief vector exposes candidate entropy and possible-ability count,
but not a stable identity bitset for specific possible abilities/items. Species
hashes can support species-specific learning in the current format, yet they do
not generalize cleanly when format set tables, forms, or ability pools change.

## Explicit examples

### Dondozo / Unaware / setup boosts

Swords Dance and other setup moves are explicit, current attack/special-attack
stages are in state, and Dondozo identity is hashed. A diagnostic ranker can
learn the interaction statistically. There is no
`target_possible_unaware`/`boost_value_may_be_ignored` signal, so the policy
must rediscover a mechanic-table fact from species-correlated examples.

### Espeon or Hatterene / Magic Bounce / hazards

Hazards and status moves are explicit action classes. Known Magic Bounce can
set a blocker bit, but an ambiguous possible Magic Bounce set does not. Exact
rollout correctly refuses to reflect without known ability and complete
routing. The missing piece is action-risk representation, not exact rollout.

### Gholdengo / Good as Gold

Reliable Gholdengo species identity plus a singleton format ability set is
deterministic public inference. Current state species identity allows indirect
learning, and the pure belief contract produces inferred Good as Gold. The
materialized v7 action vector does not yet consume that inferred identity as a
specific status-block threat bit.

### Water Absorb / Water move

Covered explicitly: opponent candidate abilities can activate
`target_known_or_possible_ability_absorbs_move_type` for a Water action. Exact
damage still must not assume which ambiguous ability is true.

### Covert Cloak / Fake Out or Iron Head

The move's base flinch chance is explicit and a known Covert Cloak zeros the
modified chance. A possible Covert Cloak is not surfaced. One Iron Head
non-flinch remains non-evidence, correctly. Deterministic/protocol item evidence
may promote the item to inferred/known through the calibration contract.

### Zoroark / Illusion

State distinguishes displayed species uncertainty from revealed true species.
Species-derived deterministic ability collapse is disabled only while that
uncertainty is marked. This is the correct guard model; normal displayed species
do not become permanently uncertain.

## Recommended minimal next batch

Use a future append-only **`legal-action-v8` possible-threat slice**, reading the
existing public opponent belief and tactical state. Do not weaken exact rollout
or overwrite known/effective fields.

Recommended field groups:

1. Provenance tier:
   - target threat set available;
   - target identity Illusion-guarded;
   - threat known / inferred-public / possible.
2. Ability applicability:
   - possible Unaware;
   - action is setup or currently boost-dependent;
   - possible Magic Bounce + action reflectable;
   - possible Good as Gold + opponent-targeting status action;
   - possible Levitate + Ground action;
   - split absorb threat into known versus possible.
3. Secondary blockers:
   - possible Covert Cloak;
   - possible Shield Dust;
   - possible Inner Focus;
   - action has blockable flinch/status/stat-drop secondary.
4. Modifier guardrails:
   - suppression/bypass/Ability Shield known-effective flags;
   - no concrete hidden ability/item identity;
   - Illusion uncertainty prevents species-singleton promotion.

An alternative state-v8 identity bitset would be reusable across actions, but
the smallest safe batch is action-conditioned v8 because the materializer
already passes public opponent belief into each candidate builder. It directly
answers “does this possible mechanic matter for this click?” and avoids a broad
state-schema migration.

## Materialization recommendation

Do **not** block an explicitly approved `diagnostic_300_v7_v7` materialization:
it remains useful as a frozen diagnostic baseline, and the gaps above are
honest omissions rather than wrong-exact features. The report and dataset
metadata should describe v7 as *partially possible-threat-aware*.

Do not approve threat-aware production claims or further training on the premise
that v7 fully represents these mechanics. If the next intended dataset is meant
to be the durable schema for strategic threat-aware training rather than a
small diagnostic baseline, implement and freeze the proposed v8 slice first.

No dataset, schema, checkpoint, live default, or live behavior changed in this
audit.
