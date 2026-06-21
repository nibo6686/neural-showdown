# v8 Meta-Prior Opponent Set Belief Design

## Status and decision

This document designs a source-agnostic, public, time-causal opponent-set belief
system for a future v8 representation. It does **not** implement v8, change the
frozen v7 state/action schemas or fingerprints, materialize data, train,
promote a checkpoint, or change live defaults.

The central contract is:

> Preserve a probability distribution over legal hidden sets, update it only
> from information available to the acting player at the decision prefix, and
> expose compact semantic probabilities—not a guessed hidden set—to the model.

The strategic consequence remains learned. The representation may say that an
opponent has a 35% posterior probability of an active Magic Bounce-like
interaction and that the current candidate is reflectable. It must not encode
“do not click hazards” or “species X counters setup.”

## Executive recommendation

Use three separated layers:

1. `MetaPriorSource`: immutable, versioned pre-battle prior snapshots from a
   Randbats generator, Smogon usage snapshot, replay empirical corpus, or test
   fixture.
2. `OpponentSetBelief`: a posterior over **joint set hypotheses**, conditioned
   only on public evidence through the current decision prefix.
3. `FeatureEncoder`: a compact state summary plus candidate-specific
   sensitivity probabilities.

For Gen 9 Random Battles, generate priors by deterministic offline sampling of
Pokemon Showdown's actual set generator. Do not treat the current `sets.json`
role/movepool declarations as an exact joint set distribution. Pin the
Showdown package/source version, relevant data checksums, sampler version,
sample seed schedule, and format ID.

For standard formats, ingest a pinned Smogon usage-statistics snapshot as the
primary prior. Preserve its date/month, rating cutoff, format, source URL/file
checksum, sample size where available, and whether the supplied statistics are
joint or marginal. Replay-derived statistics may supplement coverage, but must
be separately identified and must not silently overwrite the Smogon prior.

The existing 1,000-battle v7 result is already the needed frozen comparison.
Implement and validate v8 meta-priors before the next durable or substantially
larger rank-training run. Another larger v7 run is useful only as an explicitly
chosen scale-control experiment, not as the preferred next representation step.

## 1. What v7 currently represents

### Existing opponent prior

`trainer/src/neural/live_opponent_beliefs.py` currently:

- loads Gen 9 Randbats `sets.json`;
- normalizes species entries into candidate role/set records;
- gathers revealed moves, ability, item, Tera type, status, and faint state from
  the public trajectory/protocol;
- filters candidates against revealed moves/ability/item/Tera;
- emits up to five `top_candidates`;
- emits marginal distributions for abilities, items, and Tera types.

This is a real multi-candidate belief object. v7 is therefore not globally
equivalent to choosing one hidden set.

### Existing state features

`opponent_belief_feature_vector` in
`trainer/src/neural/live_private_features.py` selects the publicly active
opponent when possible and emits only 14 coarse fields:

- active species known;
- revealed move count;
- candidate count and top-candidate entropy;
- union count of top-candidate moves;
- possible ability and Tera-type counts;
- revealed item/ability/Tera flags;
- fainted/remaining estimates;
- filter-relaxed and known-opponent counts.

The 3208D v7 state also carries public species/form identity, revealed move
slots, known item/ability identity and provenance, current boosts, Tera state,
field state, constraints, and Illusion guards. It does not carry calibrated
identity probabilities for specific hidden moves, items, abilities, Tera
types, or roles.

### Existing action sensitivity

The clearest correct v7 pattern is
`target_known_or_possible_ability_absorbs_move_type`: the candidate action can
see whether known or possible belief abilities include a type-absorb family.
Exact rollout still does not assume that the hidden ability is present.

Other possible-threat interactions are incomplete:

- possible Magic Bounce, Good as Gold, Unaware, Levitate, Covert Cloak, Shield
  Dust, and Inner Focus are not consistently surfaced;
- several `*_possible` names require a concrete known item/ability;
- known and possible absorb risk are conflated into one bit;
- the model sees belief counts/entropy but not the probability that a relevant
  mechanic is present.

### Single-most-likely shortcuts

There is no universal “pick top set” operation in v7 feature generation.
However, there are two important approximations:

1. `damage_engine._opponent_view_mon` fills a missing ability, item, or Tera
   type from the **first entry of the corresponding marginal distribution**.
   This independently chooses top marginals, which may not form a legal joint
   set and can turn uncertainty into false exactness for candidate evaluation.
2. The belief feature entropy and move-union summaries inspect only the stored
   top five candidates. Tail mass and joint correlations outside that top-k are
   not represented.

The future v8 path should not pass a top candidate or independently selected
top marginals into exact damage/prevention logic. Exact mechanics use only
confirmed/deterministically inferred facts. Policy features consume posterior
probabilities. Search may sample complete joint hypotheses as node-local state.

## 2. Core data abstractions

### `MetaPriorSource`

Conceptual interface:

```text
MetaPriorSource.metadata() -> MetaPriorMetadata
MetaPriorSource.prior_for(format_id, species_form_key, context) -> SetPrior
```

Required metadata:

```text
source_kind:
  randbats_generator | smogon_usage | replay_empirical | fixture
prior_schema_version
source_version
source_sha256
generated_at_utc
effective_from / effective_through
format_id
generation_or_import_config
sample_count
species_key_policy
mechanics_catalog_version
```

`source_version` is source-specific:

- Randbats: Pokemon Showdown package/git version plus random-battle generator
  and data checksums.
- Smogon: usage month, format, rating cutoff, source artifact identity, and
  checksum.
- Replay empirical: frozen manifest checksum, collection window, eligibility
  rules, and parser version.
- Fixture: fixture name/version and checked-in payload checksum.

`SetPrior` should preserve joint hypotheses:

```text
species_form_key
hypotheses:
  - hypothesis_id
    probability
    ability
    item
    moves
    tera_type
    roles
    optional public stat/spread class
other_mass
support_size
joint_quality: exact | sampled | reconstructed | factorized
coverage_warnings
```

The atomic ability/item/move/Tera marginals are derived views, not the
authoritative storage. Joint hypotheses preserve facts such as “Choice Scarf
occurs with this move combination” and prevent combining unrelated top
marginals into an impossible set.

`other_mass` is mandatory when the source is truncated or incomplete. Unknown
tail mass must not be renormalized away and presented as complete knowledge.

### `OpponentSetBelief`

One belief exists per public opponent identity/roster slot where identity is
reliable. It contains:

```text
prior_identity
species_identity_state:
  known | displayed_uncertain | unknown
posterior hypotheses and probabilities
confirmed facts
ruled_out facts
revealed moves
public evidence ledger
other_mass
posterior entropy / effective support size
contradiction state
last_public_event_index
```

The posterior starts from `SetPrior` and applies evidence in protocol order.
Every update records:

- evidence kind;
- public event index/turn;
- affected attribute;
- hard filter or conservative likelihood rule;
- support/mass before and after;
- contradiction/fallback outcome.

The belief object never stores the actual hidden opponent set. A simulator or
test may hold hidden truth elsewhere, but the feature-facing belief must be a
pure function of:

```text
(pinned prior snapshot, format rules, public prefix, acting-side own request)
```

### Contradictions and incomplete sources

Current v7 filtering relaxes an impossible reveal filter and warns. v8 should
make this explicit:

- confirmed public facts always remain confirmed;
- incompatible hypotheses receive zero mass;
- if no hypothesis remains, set `prior_contradiction = true`;
- move remaining probability to `other_mass = 1` rather than restoring
  contradicted candidates;
- continue exposing confirmed facts while all unrevealed attributes become
  unknown.

This behavior separates “source snapshot did not cover reality” from “the
public reveal did not happen.”

## 3. Minimal posterior update model

The first v8 implementation should use deterministic hard conditioning where
the protocol establishes a fact. Do not begin with an elaborate Bayesian
damage/speed inference engine.

For hypothesis \(h\), prior mass \(P(h)\), and public evidence \(e\):

```text
P(h | e) proportional to P(h) * compatibility(h, e)
```

For the initial version, `compatibility` is normally 0 or 1. Confirmed facts
may also override a missing/incorrect source through the contradiction path.

### Safe initial evidence

| Public evidence | Initial update |
| --- | --- |
| Opponent used move | Keep hypotheses containing that move; append revealed move |
| Explicit ability reveal/activation | Confirm ability; keep matching hypotheses |
| Explicit item reveal/activation | Confirm item; keep matching hypotheses |
| Item consumed/removed/tricked | Record public item and current item state |
| Tera event/type | Confirm Tera type; keep matching hypotheses |
| Public forme/species change | Move to the correct species/form prior or mark identity transition |
| Magic Bounce reflection with explicit provenance | Confirm/reinforce Magic Bounce for the reflector |
| Explicit Good as Gold prevention/activation | Confirm Good as Gold |
| Ability-attributed immunity/absorb event | Confirm the named ability |
| Public suppression/change event | Track effective state without rewriting base prior identity |

Protocol attribution matters. A generic `-immune`, failed status move, miss, or
absence of a secondary effect is not enough to identify a hidden ability/item.

### Switching evidence

Initially:

- ordinary voluntary switching does **not** change hidden-set probabilities;
- forced switching/phazing updates only public dynamic state;
- a switch/drag/replacement may identify species/form/roster placement;
- a switch event must not be treated as evidence for “defensive role,” Choice
  item, coverage, or a strategic counter.

This avoids baking replay-player strategy into the representation.

### Evidence deferred initially

Avoid these in the first implementation:

- damage-roll inference for item, ability, spread, or Tera;
- speed-order inference beyond already deterministic/public constraints;
- PP inference beyond publicly observed move use and exact own-side request;
- non-activation inference from optional/probabilistic abilities;
- one or a few missing flinches/secondaries as Covert Cloak, Shield Dust, or
  Inner Focus evidence;
- switching-choice likelihoods;
- teammate/team-archetype likelihood updates;
- future reveals used to repair an earlier replay prefix;
- replay parser truth fields, packed teams, simulator objects, or original
  hidden requests unavailable to the acting player;
- outcome-conditioned or label-conditioned priors.

Damage and speed evidence can be added later only with an explicit interval
likelihood model, public-input proof, and counterfactual leakage tests.

## 4. Randbats prior generation

### Recommended source

Use the actual Pokemon Showdown Random Battles generator through sim-core (or a
small offline Node exporter using the same installed package). Prefer:

```text
Teams.getGenerator(format, seed).randomSet(species, ...)
```

over treating `sets.json` declarations as completed sets.

The existing `sim-core/src/belief_fork.ts` proves the generator can sample a
complete species set while respecting public move/ability/item/Tera
constraints. Its hidden-truth perturbation test is a useful starting
no-leakage pattern. v8 prior generation should move this sampling offline into
a pinned snapshot rather than sampling ad hoc during feature encoding.

### Sampling procedure

For every legal species/form in a pinned format:

1. sample complete sets over a deterministic, documented seed schedule;
2. canonicalize ability, item, sorted move set, Tera type, and semantic roles;
3. count identical joint hypotheses;
4. normalize probabilities;
5. retain hypotheses covering a configured cumulative mass (for example
   99.5%) and record the remainder as `other_mass`;
6. report convergence for the required semantic marginals;
7. fail the snapshot build on missing species, malformed probabilities, or
   generator/data checksum drift.

Use adaptive sampling rather than declaring one universal count sufficient.
A practical initial target is at least 20,000 samples per species, continuing
until high-impact semantic probabilities change by less than a documented
tolerance across successive blocks. Rare-tail coverage and Monte Carlo error
must be reported. The exact threshold belongs in the future snapshot-builder
plan, not hardcoded into the feature schema.

### Team-generation context

Species-local `randomSet` sampling is the minimal v8 prior. Randbats team
generation can create correlations from team composition and duplicate-role
constraints. Preserve extension points for `context` (revealed teammates,
team-generation rules), but defer team-conditional reweighting until the
species-local system passes leakage and calibration tests. Never inspect the
actual hidden bench to recover those correlations.

### Version identity

The Randbats snapshot identity should include:

- format ID;
- Pokemon Showdown package/git version;
- checksums for the set generator source and relevant random-battle data;
- Dex/data generation;
- exporter code version;
- seed schedule and sample/convergence configuration;
- output snapshot checksum.

Changing any item produces a new prior version and requires explicit dataset
metadata/fingerprint review.

## 5. Non-Randbats prior sources

### Smogon usage statistics

Recommended primary source for standard ladder formats:

- pin one monthly usage/moveset snapshot;
- identify exact format and generation;
- record rating cutoff (for example 1695/1825-style buckets where available);
- store snapshot date and source checksum;
- retain usage sample counts and uncertainty where the source provides them;
- normalize species/forms with an explicit alias policy.

Smogon artifacts commonly provide useful ability, item, move, spread, and
Tera marginals but not a complete joint set distribution. The importer must
set `joint_quality = factorized` or `reconstructed`; it must not claim exact
joint sets. A future reconstruction may use available co-occurrence tables or
maximum-entropy sampling, but the approximation and tail mass stay visible.

The feature encoder mostly consumes semantic posterior marginals, so a
factorized source remains useful. Exact rollout and joint search must not treat
factorized combinations as confirmed legal sets.

### Replay-derived empirical source

Replay statistics can:

- cover formats or dates lacking official statistics;
- estimate move-category/role frequencies;
- calibrate a Smogon or generator snapshot;
- provide a distribution-shift evaluation.

Risks are selection bias, incomplete set revelation, player-skill mixture, and
future-reveal leakage. Build only from a frozen corpus with battle-level
provenance. Fully revealed sets may support joint hypotheses; partially
revealed sets require censored-data handling and must not be filled from hidden
simulator truth.

Do not silently pool replay empirical counts with Smogon counts. Use a declared
mixture:

```text
P = alpha * P_smogon + (1 - alpha) * P_replay
```

with source identities, `alpha`, and smoothing policy in metadata.

### Fixtures

Fixtures implement the same interface and may specify tiny exact hypothesis
sets. They are the reference source for unit tests involving:

- known 70/30 ability alternatives;
- correlated item/move hypotheses;
- contradiction/tail behavior;
- Illusion identity ambiguity;
- stale/missing prior fallback.

### Freshness and fallback

Freshness is policy metadata, not an untracked runtime guess.

- Training/materialization pins a prior snapshot that was available no later
  than the replay timestamp. A future usage snapshot may not featurize an older
  decision.
- Live evaluation pins an explicitly configured snapshot and reports its age.
- Format mismatch is a hard unavailable result.
- Missing species/source yields `other_mass = 1`, `source_available = false`;
  public reveals still populate confirmed facts.
- A stale source may be allowed for diagnostic use with `source_stale = true`
  and documented maximum age. Production-directed use should fail closed or
  require explicit stale-source acceptance.
- Never fall back from a missing format-specific source to a different format's
  statistics.

## 6. Compact v8 feature design

The internal posterior can be rich. The model-facing representation should be
small and semantic.

### State-level belief features

Recommended append-only state-v8 slice: approximately 24–32 fields for the
currently active opponent.

Provenance/quality:

- prior available;
- source kind one-hot (Randbats / Smogon / replay / fixture-or-other);
- source stale;
- prior contradiction;
- other/tail mass;
- posterior entropy;
- effective support size (log-normalized);
- public species reliable;
- Illusion/displayed-species guard active;
- revealed move fraction.

Broad posterior role probabilities:

- offensive setup;
- defensive setup;
- recovery;
- hazard setting;
- hazard removal;
- pivoting;
- phazing/Haze;
- speed control/priority;
- protection;
- disruptive status/Encore/Taunt.

Broad hidden resource probabilities:

- Choice-item class;
- Heavy-Duty Boots;
- passive recovery item;
- one-time activation item;
- Tera-type entropy and maximum Tera-type probability.

Keep exact revealed identity in the existing state fields. Do not add top-k
ability/item/move identity hashes merely to recreate species/set lookup inside
the network.

### Candidate-action sensitivity features

Recommended append-only action-v8 slice: approximately 20–28 fields. Each risk
probability is computed from the posterior and current candidate mechanics.

Applicability bits:

- candidate targets opponent;
- status/reflectable;
- boost-dependent damage;
- Ground-type;
- has blockable secondary/flinch/stat drop;
- is setup;
- is Tera;
- is switch.

Posterior interaction probabilities:

- status prevented by Good as Gold;
- action reflected by Magic Bounce;
- boosts ignored by Unaware;
- Ground action invalidated by Levitate/Ground-immunity family;
- move type absorbed by ability;
- secondary blocked by Covert Cloak/Shield Dust;
- priority/flinch interaction blocked by relevant ability/terrain;
- setup answered by phazing/Haze/Clear Smog/Encore probability;
- candidate resisted or immune after possible Tera;
- candidate becomes super-effective after possible Tera;
- switch target exposed to plausible super-effective coverage;
- opponent priority-move probability against this low-HP action;
- opponent recovery/protection probability where tactically relevant.

For each interaction family, include:

- posterior probability;
- `confirmed_or_deterministic` bit where applicable;
- `probability_available` bit.

Known effective suppression/bypass (Mold Breaker, Neutralizing Gas, Ability
Shield, Magic Room, terrain) adjusts applicability using public facts. It does
not alter the underlying base-set posterior.

### Why not a huge top-k vector

A fixed top-k identity vector:

- loses tail mass;
- is unstable when metagames change;
- binds the schema to source-specific names;
- duplicates species hashes;
- encourages memorizing “species means counter” instead of learning mechanic
  interactions.

Semantic probabilities are smaller, cross-format, and directly aligned with
candidate sensitivity. Atomic posterior identities remain available for
auditing and search without becoming schema dimensions.

## 7. Feature/rollout/search separation

| Consumer | Allowed use |
| --- | --- |
| State encoder | Compact uncertainty, role, source-quality, and resource marginals |
| Action encoder | Candidate-sensitive posterior interaction probabilities |
| Exact impact/rollout | Confirmed or deterministic-public facts only; otherwise unknown/fail closed |
| Belief search | Sample a complete joint hypothesis per particle/node; keep it node-local |
| Debug/reporting | Full posterior, evidence ledger, source identity, tail mass |

The damage engine must stop filling exact hidden fields from the first marginal
entry for the v8 path. If expected damage under belief is desired, compute an
explicit probability-weighted expectation over joint hypotheses and label it
as belief expectation—not exact damage.

## 8. No-leakage test plan

### Source and time tests

1. Prior snapshot effective date is not after the battle/decision timestamp.
2. Format mismatch is rejected.
3. Source/version/checksum changes alter dataset metadata and fingerprint.
4. Missing/stale source behavior is explicit and deterministic.

### Prefix causality

5. Featurizing turn `t` from the full replay equals featurizing the physically
   truncated replay through the pre-action prefix at `t`.
6. Appending future move/ability/item/Tera reveals does not change earlier
   beliefs or features.
7. Evidence ledger event indices never exceed the decision prefix.

### Hidden-truth perturbation

8. Replace actual hidden opponent ability/item/moves/Tera/spread with arbitrary
   values while preserving public prefix and prior; belief/features remain
   byte-identical.
9. Change simulator PRNG/hidden team seed while holding public prefix and prior
   snapshot fixed; belief/features remain identical.
10. Original hidden request/packed team objects are absent from all
    feature-builder inputs.

### Distribution correctness

11. Fixture posterior normalizes including `other_mass`.
12. Revealed moves filter joint hypotheses but preserve item/move correlation.
13. Ability/item/Tera reveal collapses only the relevant compatible support.
14. Impossible reveal enters contradiction/tail mode; contradicted candidates
    are not restored.
15. Independently likely marginals that form no legal set are never emitted as
    one joint hypothesis.

### Evidence safety

16. Generic immunity/failure without named provenance does not confirm an
    ability.
17. One non-flinch/non-secondary does not infer a blocker.
18. Voluntary switch choice does not update role/item/move probabilities.
19. Forced switch updates public dynamic state only.
20. Damage/speed changes do not update belief in the initial implementation.

### Identity/Illusion

21. Reliable ordinary species selects its prior.
22. Unresolved displayed-species ambiguity prevents species-prior collapse.
23. Opponent belief never receives actor-private true Illusion identity.
24. Public `replace`/reveal starts the true-species prior only from the reveal
    point forward.

### Feature sensitivity and separation

25. Raising possible Magic Bounce mass changes only applicable reflectable
    candidate features, not unrelated attacks.
26. Raising possible Unaware mass changes boost-dependent/setup sensitivity,
    not an unboosted fixed-damage action.
27. Possible Levitate changes Ground-action sensitivity, not Water actions.
28. Possible Covert Cloak/Shield Dust changes blockable-secondary sensitivity,
    not primary damage.
29. Posterior probability changes never make exact rollout claim a hidden
    blocker.
30. State/action v7 prefixes and fingerprints remain byte-identical.

### Calibration tests

31. Randbats snapshot sampler is deterministic for a fixed source/seed schedule.
32. Required semantic marginals meet convergence tolerance.
33. Held-out public reveals have finite log loss/Brier score under the prior.
34. Smogon/replay source reports calibration separately by source, date, and
    format; no blended metric hides a poor source.

## 9. Implementation sequencing for a future task

This design does not authorize implementation. A future approved implementation
should be split:

1. Define source-neutral dataclasses/interfaces and fixture source.
2. Build offline Randbats snapshot exporter with checksum/convergence report.
3. Implement pure posterior update engine and leakage tests.
4. Add Smogon importer and explicit factorized-quality metadata.
5. Add compact state/action feature design with exact v7 prefix preservation.
6. Run counterfactual feature tests and source calibration audit.
7. Freeze v8 names/dimensions/fingerprints.
8. Only then seek approval for a tiny materialization and audit.

Do not combine source ingestion, posterior inference, feature-schema freezing,
materialization, and training in one change.

## 10. Training-order decision

The project already has a clean v7/v7 1,000-battle baseline:

`1.181397 / 0.507626 / 0.886274 / 0.700131`
NLL/top-1/top-3/MRR.

It establishes that v7 learns useful rank preferences and quantifies the weak
prevention/Tera/switch/high-candidate slices. Therefore:

- **v8 meta-priors should precede the next durable or substantially larger
  rank-training run**;
- one larger v7 run remains scientifically valid only as a deliberate
  scale-control baseline with no claim of comprehensive threat awareness;
- do not delay the separate value-dataset program on v8, because value data
  quality and rank belief representation are independent tracks;
- live/production remain blocked regardless.

## Explicit non-goals

- No hardcoded strategic labels such as counter/fake/good switch.
- No hidden-set oracle.
- No future-reveal repair of earlier states.
- No exact mechanics from posterior probability alone.
- No v7 schema/fingerprint edits.
- No schema-wide atomic identity vocabulary tied to one metagame snapshot.
- No materialization, training, promotion, or live-default change in this task.
