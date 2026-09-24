# Dataset Lineage and Battle-Level Split Contract

Status: DATA-001 accepted (2026-09-23); additive lineage contract. New feature
schema and model-pipeline acceptance remain separate gates.

## Scope

`dataset-record/v1` is a lineage envelope for existing examples. It is a
consumer-side guardrail: it does not alter feature vectors, checkpoints, live
defaults, simulator mechanics, or legacy dataset files. A dataset consumer may
require and validate the envelope before training or evaluation.

The deterministic synthetic corpus is
[`tests/fixtures/dataset_lineage_v1.json`](../../tests/fixtures/dataset_lineage_v1.json).
It is not downloaded replay data and does not claim to represent a real match.

## Required record fields

Each record contains:

- `schema_version`: exactly `dataset-record/v1`;
- `record_id`: `datarec-` plus SHA-256 of the stable identity payload;
- `battle_id` and `replay_id`;
- `source_kind`: existing `sim_core`, `replay`, or `live` source kinds;
- `source_ref`, `ruleset`, and `parser_version`;
- `perspective`, `observation_cursor`, and `feature_cursor`;
- `observation_prefix_hash`: SHA-256 of the exact source prefix used for the
  observation boundary;
- optional `observation_id`, `action_id`, `belief_id`, and `transition_id`,
  validated against the accepted v1 ID formats when present;
- `private_data_provenance` and `feature_input_eligibility`;
- the exact `schema_fingerprints` keys `observation`, `belief`, `transition`,
  and `feature` (unsupported lineage is represented by `null`);
- `split`, `split_seed`, and `split_key`, where `split_key` must equal
  `battle_id`.

`feature_cursor` is the furthest source event used to construct model input.
It must not exceed `observation_cursor`. This is the record-level future-event
leakage boundary. A missing or malformed boundary fails closed.

Consumers that have the source prefix must call the prefix validator as well:
the supplied ordered prefix must have exactly `observation_cursor` records and
its canonical SHA-256 must equal `observation_prefix_hash`. A hash-shaped value
without the matching prefix is not treated as verified lineage.

The stable record identity excludes mutable metrics and split metadata, so the
same battle observation cannot be silently duplicated with a different split
or evaluation result. Duplicate record IDs are rejected, as are battle or
replay identities that cross splits.

## Privacy and lineage rules

`private_data_provenance=none` requires `public_only` input eligibility.
Private provenance cannot be labeled `public_only`. Optional input-field
annotations reject raw requests, private team data, opponent-private data,
belief candidates, simulator state, RNG seeds, and future events from a
public-only input.

Belief and transition fields are optional because current replay-derived
records do not all have canonical belief or seeded-transition joins. When a
join exists, its accepted versioned ID is retained; the DATA-001 validator
does not invent missing belief or transition evidence.

## Split and metrics behavior

`deterministic_split_for_battle` uses only the battle identity and recorded
seed. `validate_records` enforces battle- and replay-disjoint membership. The
public replay value/policy and live-private builders validate the complete
record collection before writing their output; a failed collection is not
serialized as a new DATA-001 artifact.
`source_metric_report` reports metrics separately by source kind and preserves
the source split list; it does not combine replay, live, and simulator regimes
into one unqualified number.

Unsupported schemas, malformed records, stale or contradictory identity,
future feature cursors, privacy contradictions, duplicate identities, and
cross-split contamination fail closed. Existing legacy datasets remain
read-only until a future migration supplies complete envelopes.

## Explicit limitations and rollback

V1 does not add calibration, confidence, acquisition APIs, replay fetching,
training, model-input transformations, or a new dataset storage format. It does
not attest that a caller-supplied observation ID came from the simulator; it
only validates the deterministic envelope and accepted ID shape. Canonical
ObservableBattleState, CanonicalAction, BeliefState, and SeededTransition
contracts remain authoritative for their own fields.

Rollback removes the additive dataset-lineage module, fixture, tests, and this
contract. Existing dataset files and consumers remain unchanged.
