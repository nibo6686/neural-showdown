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

- Revealed species appearances with a prior: 1600/1600 (100.00%).
- Unique revealed species/forms with a prior: 487/487 (100.00%).
- Public identity slots with missing priors: 0/1600.
- Slots ending with dominant unknown tail (`other_mass > 0.5`): 666/1600 (41.62%).

Missing species/forms:

- None.

Priors resolved via the explicit form-alias policy (`randbats-form-alias-v1`), public->base:

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
| ability_revealed | 299 | 301 | 99.34% |
| move_revealed | 3059 | 3059 | 100.00% |
| tera_type_revealed | 214 | 214 | 100.00% |

- Ability labels: 301; mean assigned probability including the fixed unknown tail: 0.4657; coarse log loss 0.9577.
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

- `leavanny:pickpocket`: 1
- `beartic:dryskin`: 1

### move_revealed

- None.

### tera_type_revealed

- None.

## Source-absent evidence (absorbed after the fix)

- `OpponentSetBelief.update` now records reveals for dimensions the
  role source does not model (items for Randbats; any reveal on a
  missing-species belief) as confirmed public facts with
  `source_covered = False`, leaving role/ability/move/Tera
  hypotheses and the unknown tail untouched.
- Source-absent ledger entries absorbed cleanly: 2208 (`{'item_revealed': 2207, 'ability_revealed': 1}`).
- Item evidence ledger entries: 2207; of these, item-driven contradictions: 0.
- Every item reveal is now absorbed rather than collapsing the
  posterior, so the prior 701 item-driven first collapses are gone.

## Copied/forme current-state evidence (recorded, non-contradicting)

- Trace copies, Imposter/Transform copied moves/abilities, Struggle,
  and forme-state abilities (As One, Tera Shell/Shift, Battle Bond,
  Embody Aspect) are flagged `current_state_only`: recorded in the
  ledger but never used as base-set evidence or contradiction.
- Current-state ledger entries: 59 (`{'ability_revealed': 40, 'move_revealed': 19}`).

## Posterior contradictions

- Slots reaching explicit prior contradiction: 2/1600 (0.12%).
- Contradicting evidence entries by kind: `{'ability_revealed': 2}`.
- All remaining contradictions are source-covered ability/move
  dimensions where the public reveal is incompatible with every
  declared hypothesis; real source/data mismatches stay explicit.

Remaining contradiction classification:

- `{'true_source_limitation': 2}`.
- `dynamic_or_copied_state`: Trace/Imposter (Ditto) and other copied
  abilities/moves shown as current state but not base-set facts.
- `composite_or_forme_ability`: identity/forme-tied abilities (As One,
  Embody Aspect, Tera Shell/Shift, Battle Bond) stored under the base
  forme key; partly an alias/form-normalization gap.
- `universal_move_noise`: Struggle, which is never a set move.
- `true_source_limitation`: the declared role sets genuinely omit the
  revealed ability/move.

### true_source_limitation

- `leavanny:ability_revealed:pickpocket`: 1
- `beartic:ability_revealed:dryskin`: 1

Top first-collapse details:

- `leavanny:ability_revealed:pickpocket:public_replay_named_ability`: 1
- `beartic:ability_revealed:dryskin:public_replay_named_ability`: 1

### ability_revealed

- `leavanny:pickpocket:public_replay_named_ability`: 1
- `beartic:dryskin:public_replay_named_ability`: 1

## Causality and invariance

- Prefix/suffix causality: 300/300 passed.
- Hidden-truth perturbation invariance: 300/300 passed.
- Illusion replacement segments observed: 1; failures: 0.
- Named reflected-move rows observed: 2; attribution/move-pollution failures: 0.

## Decision

Both non-source-data blockers are now fixed. The explicit form-alias
policy resolves cosmetic/forme public keys to their base prior (with
alias provenance recorded), and copied/forme current-state evidence
(Trace, Imposter/Transform, Struggle, forme abilities) is recorded
without contradicting the base prior. Items remain absorbed as
source-absent. Causality, hidden-truth invariance, Illusion, and
reflection checks all pass.

Any remaining contradictions are genuine source limitations (the role
data simply omits a real base-set ability/move). The source is now
clean enough for the first append-only v8 belief-feature slice,
provided every feature retains explicit source-quality/unknown
provenance and treats coarse support/unknown indicators as
uncalibrated. The fixed 0.5 tail, factorized role alternatives, absent
items, and declaration-rather-than-generated probabilities still make
this unsuitable as a sole calibrated production prior; the
generator-sampled snapshot remains the route to calibrated joint
probabilities.
