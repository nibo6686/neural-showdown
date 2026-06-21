# Randbats Meta-Prior Public-Prefix Audit

## Scope

- Command: `python scripts/audit_randbats_meta_prior_public_prefixes.py --manifest artifacts\training_plan\manifests\diagnostic_1000_v7_v7_post_ditto_manifest.json --prior-source data\random-battles\gen9\sets.json --split test --limit 1000`
- Manifest split: `test`
- Battles scanned: 150
- Prior source: `data/random-battles/gen9/sets.json`
- Prior SHA-256: `7dc75740d17755d921c473fca68b3022f6f37a2af387d3cd9c94432bd646eaef`
- Information boundary: prior plus public protocol prefix only; later
  reveals are evaluation labels, never earlier-belief inputs.

## Coverage

- Revealed species appearances with a prior: 1562/1600 (97.62%).
- Unique revealed species/forms with a prior: 463/487 (95.07%).
- Public identity slots with missing priors: 38/1600.
- Slots ending with dominant unknown tail (`other_mass > 0.5`): 1072/1600 (67.00%).

Missing species/forms:

- `palafinhero`: 4 appearances
- `polteageistantique`: 4 appearances
- `sinistchamasterpiece`: 3 appearances
- `florgesorange`: 3 appearances
- `pikachusinnoh`: 2 appearances
- `miniorindigo`: 2 appearances
- `miniorviolet`: 2 appearances
- `dudunsparcethreesegment`: 2 appearances
- `sawsbuckwinter`: 1 appearances
- `pikachupartner`: 1 appearances
- `vivillonhighplains`: 1 appearances
- `ogerponcornerstonetera`: 1 appearances
- `sawsbucksummer`: 1 appearances
- `pikachualola`: 1 appearances
- `vivillonmarine`: 1 appearances
- `vivillonriver`: 1 appearances
- `magearnaoriginal`: 1 appearances
- `vivillonarchipelago`: 1 appearances
- `mimikyubusted`: 1 appearances
- `vivillonelegant`: 1 appearances
- `pikachukalos`: 1 appearances
- `zarudedada`: 1 appearances
- `alcremiematchacream`: 1 appearances
- `pikachuunova`: 1 appearances

Likely alias/form-key gaps (not silently remapped):

- `palafinhero->palafin`: 4 public slots
- `polteageistantique->polteageist`: 4 public slots
- `sinistchamasterpiece->sinistcha`: 3 public slots
- `florgesorange->florges`: 3 public slots
- `pikachusinnoh->pikachu`: 2 public slots
- `miniorindigo->minior`: 2 public slots
- `miniorviolet->minior`: 2 public slots
- `dudunsparcethreesegment->dudunsparce`: 2 public slots
- `sawsbuckwinter->sawsbuck`: 1 public slots
- `pikachupartner->pikachu`: 1 public slots
- `vivillonhighplains->vivillon`: 1 public slots
- `ogerponcornerstonetera->ogerponcornerstone`: 1 public slots
- `sawsbucksummer->sawsbuck`: 1 public slots
- `pikachualola->pikachu`: 1 public slots
- `vivillonmarine->vivillon`: 1 public slots
- `vivillonriver->vivillon`: 1 public slots
- `magearnaoriginal->magearna`: 1 public slots
- `vivillonarchipelago->vivillon`: 1 public slots
- `mimikyubusted->mimikyu`: 1 public slots
- `vivillonelegant->vivillon`: 1 public slots
- `pikachukalos->pikachu`: 1 public slots
- `zarudedada->zarude`: 1 public slots
- `alcremiematchacream->alcremie`: 1 public slots
- `pikachuunova->pikachu`: 1 public slots

## Public reveal support

| Evidence | Supported | Total | Support |
|---|---:|---:|---:|
| ability_revealed | 306 | 337 | 90.80% |
| move_revealed | 2984 | 3071 | 97.17% |
| tera_type_revealed | 205 | 214 | 95.79% |

- Ability labels: 324; mean assigned probability including the fixed unknown tail: 0.4439; coarse log loss 2.2680.
- These are factorized declaration weights, not calibrated generator
  frequencies. The probability values should not be treated as
  production calibration.
- Ability-label evaluation treats a Trace protocol row as public
  evidence for Trace, not as base-set evidence for the copied
  ability. The current replay belief adapter still records the
  displayed copied ability too; those collapses remain visible below
  as adapter-semantics failures.

Top unsupported public labels:

### ability_revealed

- `palafinhero:zerotohero:missing_prior`: 4
- `ogerponcornerstone:embodyaspectcornerstone`: 2
- `terapagos:terashell`: 2
- `miniorindigo:shieldsdown:missing_prior`: 2
- `miniorviolet:shieldsdown:missing_prior`: 2
- `calyrexice:asone`: 2
- `calyrexice:unnerve`: 2
- `polteageistantique:cursedbody:missing_prior`: 2
- `calyrexshadow:asone`: 1
- `calyrexshadow:unnerve`: 1

### move_revealed

- `palafinhero:jetpunch:missing_prior`: 3
- `florgesorange:moonblast:missing_prior`: 3
- `florgesorange:calmmind:missing_prior`: 3
- `polteageistantique:shellsmash:missing_prior`: 3
- `polteageistantique:storedpower:missing_prior`: 3
- `sinistchamasterpiece:shadowball:missing_prior`: 2
- `miniorindigo:shellsmash:missing_prior`: 2
- `miniorindigo:acrobatics:missing_prior`: 2
- `florgesorange:terablast:missing_prior`: 2
- `miniorviolet:shellsmash:missing_prior`: 2

### tera_type_revealed

- `florgesorange:ground:missing_prior`: 2
- `polteageistantique:fighting:missing_prior`: 2
- `dudunsparcethreesegment:ghost:missing_prior`: 1
- `pikachusinnoh:water:missing_prior`: 1
- `florgesorange:steel:missing_prior`: 1
- `miniorviolet:ground:missing_prior`: 1
- `pikachuunova:water:missing_prior`: 1

## Posterior contradictions

- Slots reaching explicit prior contradiction: 724/1600 (45.25%).
- Contradicting evidence entries by kind: `{'item_revealed': 701, 'ability_revealed': 17, 'move_revealed': 6}`.
- Item contradictions are expected source limitations because the
  checked-in role data contains no items. Move contradictions can
  also arise when successive public moves span declarations that the
  coarse role expansion keeps separate.
- The contradiction rate is therefore an end-to-end result, not a
  pure source-data score: unknown-tail conditioning currently marks
  absent item hypotheses as contradiction, and copied/transformed
  public abilities or moves can be mistaken for base-set evidence.

Top first-collapse details:

- `dachsbun:item_revealed:leftovers:public_replay_named_item`: 7
- `garganacl:item_revealed:leftovers:public_replay_named_item`: 6
- `camerupt:item_revealed:leftovers:public_replay_named_item`: 6
- `palossand:item_revealed:leftovers:public_replay_named_item`: 6
- `dondozo:item_revealed:leftovers:public_replay_named_item`: 5
- `electivire:item_revealed:lifeorb:public_replay_named_item`: 5
- `screamtail:item_revealed:leftovers:public_replay_named_item`: 5
- `exeggutor:item_revealed:sitrusberry:public_replay_item`: 5
- `deoxysattack:item_revealed:lifeorb:public_replay_named_item`: 5
- `banette:item_revealed:lifeorb:public_replay_named_item`: 5
- `meganium:item_revealed:leftovers:public_replay_named_item`: 5
- `sylveon:item_revealed:leftovers:public_replay_named_item`: 5
- `misdreavus:item_revealed:eviolite:public_replay_item`: 4
- `chimecho:item_revealed:leftovers:public_replay_named_item`: 4
- `wigglytuff:item_revealed:leftovers:public_replay_named_item`: 4

### ability_revealed

- `ogerponcornerstone:embodyaspectcornerstone:public_replay_ability`: 2
- `terapagos:terashell:public_replay_activation`: 2
- `calyrexice:asone:public_replay_ability`: 2
- `gardevoir:sapsipper:public_replay_ability`: 1
- `calyrexshadow:asone:public_replay_ability`: 1
- `gardevoir:innerfocus:public_replay_ability`: 1
- `ogerpon:embodyaspectteal:public_replay_ability`: 1
- `leavanny:pickpocket:public_replay_named_ability`: 1
- `gardevoir:hydration:public_replay_ability`: 1
- `ditto:drought:public_replay_named_ability`: 1

### item_revealed

- `dachsbun:leftovers:public_replay_named_item`: 7
- `garganacl:leftovers:public_replay_named_item`: 6
- `camerupt:leftovers:public_replay_named_item`: 6
- `palossand:leftovers:public_replay_named_item`: 6
- `dondozo:leftovers:public_replay_named_item`: 5
- `electivire:lifeorb:public_replay_named_item`: 5
- `screamtail:leftovers:public_replay_named_item`: 5
- `exeggutor:sitrusberry:public_replay_item`: 5
- `deoxysattack:lifeorb:public_replay_named_item`: 5
- `banette:lifeorb:public_replay_named_item`: 5

### move_revealed

- `ditto:bodypress:public_replay_move`: 1
- `ditto:closecombat:public_replay_move`: 1
- `ditto:toxic:public_replay_move`: 1
- `ditto:roar:public_replay_move`: 1
- `ditto:machpunch:public_replay_move`: 1
- `dragalge:struggle:public_replay_move`: 1

## Causality and invariance

- Prefix/suffix causality: 300/300 passed.
- Hidden-truth perturbation invariance: 300/300 passed.
- Illusion replacement segments observed: 1; failures: 0.
- Named reflected-move rows observed: 2; attribution/move-pollution failures: 0.

## Decision

The source is sufficient for continued offline posterior plumbing,
coverage diagnostics, and append-only feature design experiments only
if every feature retains explicit unknown/quality provenance. It is
not sufficient as the sole calibrated first-v8 production prior:
the fixed 0.5 tail, absent items, factorized role alternatives, and
declaration rather than generated-set probabilities create material
posterior collapse and calibration limits.

Before any feature wiring, repair explicit form aliases, unknown-tail
conditioning, and copied/dynamic ability and Transform evidence
semantics, then rerun this audit. After that, decide whether coarse
support/unknown indicators are sufficient for an initial experiment
or whether the generator-sampled snapshot is required first.
