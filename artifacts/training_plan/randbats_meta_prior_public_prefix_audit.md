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
- Slots ending with dominant unknown tail (`other_mass > 0.5`): 709/1600 (44.31%).

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

## Source-absent evidence (absorbed after the fix)

- `OpponentSetBelief.update` now records reveals for dimensions the
  role source does not model (items for Randbats; any reveal on a
  missing-species belief) as confirmed public facts with
  `source_covered = False`, leaving role/ability/move/Tera
  hypotheses and the unknown tail untouched.
- Source-absent ledger entries absorbed cleanly: 2517 (`{'item_revealed': 2207, 'move_revealed': 266, 'ability_revealed': 35, 'tera_type_revealed': 9}`).
- Item evidence ledger entries: 2207; of these, item-driven contradictions: 0.
- Every item reveal is now absorbed rather than collapsing the
  posterior, so the prior 701 item-driven first collapses are gone.

## Posterior contradictions

- Slots reaching explicit prior contradiction: 28/1600 (1.75%).
- Contradicting evidence entries by kind: `{'ability_revealed': 22, 'move_revealed': 6}`.
- All remaining contradictions are source-covered ability/move
  dimensions where the public reveal is incompatible with every
  declared hypothesis; real source/data mismatches stay explicit.

Remaining contradiction classification:

- `{'composite_or_forme_ability': 9, 'dynamic_or_copied_state': 16, 'true_source_limitation': 2, 'universal_move_noise': 1}`.
- `dynamic_or_copied_state`: Trace/Imposter (Ditto) and other copied
  abilities/moves shown as current state but not base-set facts.
- `composite_or_forme_ability`: identity/forme-tied abilities (As One,
  Embody Aspect, Tera Shell/Shift, Battle Bond) stored under the base
  forme key; partly an alias/form-normalization gap.
- `universal_move_noise`: Struggle, which is never a set move.
- `true_source_limitation`: the declared role sets genuinely omit the
  revealed ability/move.

### composite_or_forme_ability

- `ogerponcornerstone:ability_revealed:embodyaspectcornerstone`: 2
- `terapagos:ability_revealed:terashell`: 2
- `calyrexice:ability_revealed:asone`: 2
- `calyrexshadow:ability_revealed:asone`: 1
- `greninja:ability_revealed:battlebond`: 1
- `ogerpon:ability_revealed:embodyaspectteal`: 1

### dynamic_or_copied_state

- `bellossom:ability_revealed:trace`: 1
- `farigiraf:ability_revealed:trace`: 1
- `gardevoir:ability_revealed:sapsipper`: 1
- `glalie:ability_revealed:trace`: 1
- `gardevoir:ability_revealed:innerfocus`: 1
- `ditto:move_revealed:bodypress`: 1
- `ditto:move_revealed:closecombat`: 1
- `ditto:move_revealed:toxic`: 1
- `ditto:move_revealed:roar`: 1
- `phione:ability_revealed:trace`: 1

### true_source_limitation

- `leavanny:ability_revealed:pickpocket`: 1
- `beartic:ability_revealed:dryskin`: 1

### universal_move_noise

- `dragalge:move_revealed:struggle`: 1

Top first-collapse details:

- `ogerponcornerstone:ability_revealed:embodyaspectcornerstone:public_replay_ability`: 2
- `terapagos:ability_revealed:terashell:public_replay_activation`: 2
- `calyrexice:ability_revealed:asone:public_replay_ability`: 2
- `bellossom:ability_revealed:trace:public_replay_named_ability`: 1
- `farigiraf:ability_revealed:trace:public_replay_named_ability`: 1
- `gardevoir:ability_revealed:sapsipper:public_replay_ability`: 1
- `calyrexshadow:ability_revealed:asone:public_replay_ability`: 1
- `greninja:ability_revealed:battlebond:public_replay_ability`: 1
- `glalie:ability_revealed:trace:public_replay_named_ability`: 1
- `gardevoir:ability_revealed:innerfocus:public_replay_ability`: 1
- `ogerpon:ability_revealed:embodyaspectteal:public_replay_ability`: 1
- `ditto:move_revealed:bodypress:public_replay_move`: 1
- `ditto:move_revealed:closecombat:public_replay_move`: 1
- `ditto:move_revealed:toxic:public_replay_move`: 1
- `leavanny:ability_revealed:pickpocket:public_replay_named_ability`: 1

### ability_revealed

- `ogerponcornerstone:embodyaspectcornerstone:public_replay_ability`: 2
- `terapagos:terashell:public_replay_activation`: 2
- `calyrexice:asone:public_replay_ability`: 2
- `bellossom:trace:public_replay_named_ability`: 1
- `farigiraf:trace:public_replay_named_ability`: 1
- `gardevoir:sapsipper:public_replay_ability`: 1
- `calyrexshadow:asone:public_replay_ability`: 1
- `greninja:battlebond:public_replay_ability`: 1
- `glalie:trace:public_replay_named_ability`: 1
- `gardevoir:innerfocus:public_replay_ability`: 1

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

After the source-absent evidence fix the end-to-end contradiction
rate is small and fully explained: every remaining contradiction is
a source-covered ability/move incompatibility, dominated by dynamic
copied-state (Trace/Imposter) and forme-tied abilities. Items no
longer collapse the posterior. Causality, hidden-truth invariance,
Illusion, and reflection checks all pass.

This makes the source clean enough for first append-only v8
belief-feature wiring **only if** every feature retains explicit
unknown/quality provenance and treats coarse support/unknown
indicators as uncalibrated. The fixed 0.5 tail, factorized role
alternatives, absent items, and declaration-rather-than-generated
probabilities still make this unsuitable as a sole calibrated
production prior; the generator-sampled snapshot remains the route to
calibrated joint probabilities.

Remaining non-blocking follow-ups (classify, do not strategy-hardcode):

1. Explicit public species/forme alias policy for missing-prior forms
   (Palafin-Hero, Polteagist-Antique, Ogerpon/Minior/Vivillon/Pikachu
   cosmetic forms) and forme-key abilities (As One vs As One-Glastrier,
   Tera Shell vs Tera Shift).
2. Dynamic ability / Transform-Imposter semantics that separate
   current copied state (Trace/Imposter displayed ability, Ditto copied
   moves) from base hidden-set facts, so copied state is not recorded
   as base-set evidence or a contradiction.

Both are bounded by the classification above; neither requires the
generator snapshot. They can be implemented and tested before or
alongside the first v8 feature slice as long as features expose source
quality and unknown mass.
