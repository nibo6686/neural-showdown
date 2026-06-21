# v8 Belief Feature Slice Report (first slice)

## Scope

First append-only v8 belief feature slice: compact source-quality and belief
summary features for the public opponent active slot, derived purely from
`OpponentSetBelief`. No candidate/action v8 features, no calibrated generator
snapshot, no training, no full rematerialization, no live-default change. v7
state/action schemas and fingerprints are untouched.

## Schema identity

| Schema | Version | Dim | Fingerprint (state names sha256) |
|---|---|---:|---|
| v7 (frozen, unchanged) | `live-private-belief-v7` | 3208 | `0a697b42…e36fbf` |
| v8 (new) | `live-private-belief-v8` | 3229 | `8ac51441…26053` |

v8 = v7 (first 3208 names/order/values identical) + a 21-field append-only
slice. Append-only and v7-frozen are asserted by tests.

Full v8 fingerprint:
`8ac514415b0e35014b5fc741d54cd79599175c039bdbda0cf2309d5d4ef26053`.

## v8 slice features (21, opponent active slot)

Provenance / source quality (explicit, because the prior is an uncalibrated
role-data source, not a generator snapshot):

- `opponent_belief_has_meta_prior`
- `opponent_belief_prior_alias_used`
- `opponent_belief_prior_other_mass`
- `opponent_belief_prior_contradiction`
- `opponent_belief_quality_factorized`
- `opponent_belief_quality_coarse_movepool_support`
- `opponent_belief_quality_item_unknown`
- `opponent_belief_quality_uncalibrated_probabilities`

Belief summary (counts normalized; uncalibrated coarse signals):

- `opponent_belief_confirmed_fact_count_norm`
- `opponent_belief_ruled_out_fact_count_norm`
- `opponent_belief_current_state_only_fact_count_norm`
- `opponent_belief_source_absent_fact_count_norm`
- `opponent_belief_support_size_norm`
- `opponent_belief_possible_ability_count_norm`
- `opponent_belief_possible_move_count_norm`
- `opponent_belief_possible_tera_count_norm`
- `opponent_belief_ability_max_posterior`
- `opponent_belief_ability_entropy_norm`
- `opponent_belief_confirmed_ability_known`
- `opponent_belief_confirmed_item_known`
- `opponent_belief_confirmed_tera_known`

Candidate/action v8 threat features are intentionally **deferred to the next
slice** (the role source has no calibrated per-candidate threat probabilities;
adding them needs a parallel `legal-action-v8` and is out of scope for this first
slice).

## Design / no-leakage properties

- The slice is a pure function of `OpponentSetBelief`, which is itself a pure
  function of `(pinned prior, public protocol prefix, alias policy)` — no hidden
  opponent truth and no future reveals.
- Missing prior / no active slot → explicit unknown: `has_meta_prior = 0` and
  `prior_other_mass = 1.0` (not silent zeros).
- Source-absent reveals (items) increment `source_absent_fact_count_norm` and set
  `confirmed_item_known` without contradiction.
- Copied/forme current-state evidence (Trace, Imposter/Transform, Struggle, As
  One/Tera Shell/Battle Bond/Embody Aspect) increments
  `current_state_only_fact_count_norm`, never base counts or contradiction.
- True source limitations (e.g. `leavanny:pickpocket`) keep
  `prior_contradiction = 1`, staying visible.
- `OpponentSetBelief` gained `prior_joint_quality` / `prior_coverage_warnings`
  provenance (append-only) so the quality flags are derived from the prior's own
  declared warnings, not a hardcoded adapter string.

## Wiring

- `trainer/src/neural/v8_belief_features.py`: slice names + pure slice function.
- `live_private_features.py`: `FEATURE_VERSION_V8` / `FEATURE_NAMES_V8` /
  `FEATURE_DIM_V8`, a v8 branch in `build_live_private_feature_vector(...,
  opponent_set_belief=...)`, `active_opponent_set_belief(...)` helper (lazy prior
  load), v8 schema export, and v8-only belief computation in
  `build_features_from_live_payload`. The v7 path never loads the prior.
- `scripts/print_v8_belief_features.py`: read-only diagnostic printer.

## Tests

`trainer/tests/test_v8_belief_feature_slice.py` (14 tests): v7 dim/fingerprint
frozen; v8 append-only; v8 names stable/ordered; schema export; explicit-unknown
for missing/None belief; source-quality flags present; alias flag; confirmed/
ruled-out counts; source-absent item handling; true-source-limitation
contradiction visible; hidden-truth perturbation invariance; future-reveal
truncation invariance; copied-state does not inflate base counts.

## Status / next step

The first v8 state belief slice is implemented, append-only, and no-leakage
tested; the public-prefix audit is unchanged (0.12% contradictions, 100%
coverage). A **tiny, approval-gated v8 materialization smoke** (reusing an
existing small split, e.g. diagnostic_300, with `live-private-belief-v8`) is now
the appropriate next step to confirm end-to-end featuregen/metadata/fingerprint
plumbing before designing the candidate/action v8 slice. No training,
full-rematerialization, checkpoint promotion, or live-default change occurred.
