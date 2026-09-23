# Refactor Readiness Status

## Gate status

`READY_FOR_REFACTOR: YES`

This status is set by the documentation readiness gate after all requested documents exist, all work-item fields are present, cross-references validate, and the documentation diff is confirmed clean.

## Gate evidence

- All requested documentation files plus the replay-fixture policy document
  exist.
- `CTRL-001` through `SEARCH-001` are present in [WORK_ITEMS.md](WORK_ITEMS.md).
- Every work item has status, owner, dependencies, acceptance criteria, tests, and rollback.
- Referenced documentation targets exist and work-item IDs resolve.
- The top-level state-schema clarification and normative observable-state
  contract are tracked alongside the additive adapter; replay policy remains in
  the requested documentation tree.
- Baseline branch, tag, commit, and environment blockers are recorded below.

## Objective

Prepare a controlled refactor while keeping Showdown/sim-core as the authoritative mechanics engine. Separate authoritative state, player-observable state, beliefs, canonical actions, transitions, features, and search. Preserve raw protocol events, prevent future-information leakage, make seeded transitions reproducible, and make model/data/action/schema provenance explicit.

## Baseline

- Branch: `main`
- Baseline tag: `v1-live-eval-51-gc4477b6`
- Baseline commit: `c4477b6151885b35847da71110729867d9e48d5d`
- Production source changes in this session: additive observable-state,
  canonical-action, and seeded-transition adapters; legacy mechanics,
  raw-choice consumers, and default paths remain unchanged.
- Simulator replacement: prohibited in this phase

## Environment blockers

- The bare `python` and direct `pytest` commands are not on PATH; use `/Library/Developer/CommandLineTools/usr/bin/python3` and `python3 -m pytest`, or add `/Users/nbolger/Library/Python/3.9/bin` to PATH.
- Python packages are installed and importable from `/Users/nbolger/Library/Python/3.9/lib/python/site-packages`.
- Node/npm are available through `/Users/nbolger/.nvm/versions/node/v24.21.0/bin`; sim-core packages and compiled server are present.
- Remaining blockers are dependency reproducibility metadata and missing raw replay fixtures under `data/replays/raw/gen9randombattle`.

## Current readiness constraints

- Replay policy closeout and the additive STATE-001 shadow slice are complete;
  production refactoring and model integration remain out of scope.
- Production state/model refactoring begins only after `STATE-001` is reviewed.
- `STATE-001` review result: `ACCEPT` (2026-09-23).
- `ENV-001` result remains `BLOCKED_WITH_REMEDIATION`; contract acceptance is
  still pending the documented dependency policy and replay-fixture condition.
- ENV-001 Node validation: PASS (40/40 full sim-core tests, including five new
  observable-state tests; 11/11 focused state/env-manager tests). Python
  replay-independent validation is 131/131 passed. Replay-backed selection is
  marked and reports 1 skipped with the documented reason when the raw fixture
  directory has no `.log` files.
- The attempted whole-suite Python run was not used as readiness evidence: it
  contains pre-existing benchmark/checkpoint/replay-asset failures outside the
  focused validation set and was stopped. No replay data was downloaded and no
  packages were installed.
- Environment details and remediation steps: [ENVIRONMENT_VALIDATION.md](ENVIRONMENT_VALIDATION.md).
- `ACTION-001` result: `ACCEPT` (2026-09-23). Its canonical codec and opt-in
  ingress are additive; targeted/multi-active/pass/skip semantics remain
  explicitly outside v1.
- `FIXTURE-001` result: `ACCEPT` (2026-09-23); protocol-prefix golden corpus
  and cutoff/redaction assertions are complete.
- `FIXTURE-002` result: `ACCEPT` (2026-09-23); TypeScript/Python action-set
  parity corpus and structural mask/label assertions are complete.
- `TRANS-001` result: `ACCEPT` (2026-09-23). The seeded transition adapter is
  additive, uses server-managed opaque snapshot handles, validates branch
  lineage and joint actions atomically, and records deterministic event-bearing
  transition metadata. Legacy step/canonical paths remain unchanged.
- `BELIEF-001` result: `ACCEPT` (2026-09-23). A separate BeliefState v1
  contract and shadow-only TypeScript projector retain explicit provenance and
  lineage without changing accepted observation, action, transition, or
  belief-fork behavior.
- `DATA-001` result: `ACCEPT` (2026-09-23). An additive `dataset-record/v1`
  envelope records battle/replay identity, source/private provenance,
  observation and feature cursors, schema fingerprints, deterministic identity,
  and battle/replay-disjoint split membership. Existing feature vectors, model
  inputs, checkpoints, legacy source labels, and consumers remain unchanged.
- The orchestrator is the only writer of aggregate status files.

## Current prepared item

`STATE-001` has an accepted shadow slice, `ACTION-001` has an accepted
request-bound canonical-action slice, FIXTURE-001/FIXTURE-002 have accepted
golden corpora, `TRANS-001` has an accepted additive seeded-transition slice,
and `BELIEF-001` has an accepted separate belief-state contract and projector;
`DATA-001` has an accepted additive dataset-lineage envelope and builder
metadata slice; and `SEARCH-001` has an accepted documentation-only account of
current rollout/search semantics. Search does not yet consume the accepted
observation/action/belief/transition contracts. Any integration must be defined
as a separate scoped work item.
The normative schemas are in
[`../contracts/OBSERVABLE_STATE.md`](../contracts/OBSERVABLE_STATE.md) and
[`../contracts/CANONICAL_ACTION.md`](../contracts/CANONICAL_ACTION.md). The
adapters are `sim-core/src/observable_state.ts` and
`sim-core/src/canonical_action.ts`; focused tests are in
`sim-core/tests/observable_state.test.ts`,
`sim-core/tests/canonical_action.test.ts`,
`sim-core/tests/transition.test.ts`, and
`trainer/tests/test_canonical_action.py`. Existing feature vectors, model
inputs, checkpoints, live defaults, search, and legacy raw-choice submission
remain unchanged.

## TRANS-001 acceptance — 2026-09-23

- Separate read-only acceptance review: `ACCEPT`; no blocking findings.
- `npm test --prefix sim-core`: 59/59 passed.
- Focused transition suite: 4/4 passed.
- Relevant Python replay-independent suite: 135 passed.
- `tests/fixtures/seeded_transition_v1.json` records deterministic input,
  action, transition, branch, output, and ordered non-empty event evidence;
  tests preserve raw runtime timestamps while normalizing them only for identity.
- RPC boundary evidence: `capture_seeded_snapshot` returns an opaque handle;
  `step_seeded_transition` rejects raw simulator snapshots and returns only
  snapshot references. Revision and branch lineage are server-validated.
- `git diff --check`: passed. No replay data, network acquisition, package
  installation, search/retraining work, or ENV-001 change was performed.
- Rollback: remove the transition module, fixture/tests, contract, and additive
  RPC/method while retaining legacy `step`, `step_canonical`, restore, and
  belief-fork behavior.

## ACTION-001 acceptance — 2026-09-23

- Separate read-only acceptance review: `ACCEPT`; no remaining required changes.
- Shared fixture corpus: `tests/fixtures/canonical_action_v1.json`.
- TypeScript/Python schema: versioned `canonical-action/v1`, request-bound
  player/rqid/provenance, deterministic SHA-256 action IDs, exact field
  validation, and fail-closed legal-action matching.
- Additive ingress: `step_canonical` validates against the pending request and
  forwards through the existing raw choice path; legacy `step` remains the
  unchanged default path.
- `npm test --prefix sim-core`: 53/53 passed.
- Relevant Python action/inference/parity set: 20 passed, 2 documented skips.
- `git diff --check`: passed.
- Rollback: remove the canonical-action modules, fixture/tests, and additive
  ingress; retain the TypeScript legacy action codec and raw-choice path.

## Fixture acceptance — 2026-09-23

- FIXTURE-001 separate review verdict: `ACCEPT`.
- FIXTURE-002 separate review verdict: `ACCEPT`.
- `npm test --prefix sim-core`: 55/55 passed.
- Relevant Python replay-independent suite: 135 passed.
- FIXTURE-001 focused fixture test: 2/2 passed.
- FIXTURE-002 focused TypeScript/Python tests: 4/4 and 4/4 passed.
- No replay data, network acquisition, transition execution, or ENV-001 change
  was performed for fixture acceptance.

## STATE-001 remediation acceptance — 2026-09-23

- Separate read-only acceptance review: `ACCEPT`; no remaining gaps identified.
- `npm test --prefix sim-core`: 48/48 passed.
- `node --test sim-core/dist/tests/observable_state.test.js`: 13/13 passed.
- Replay-independent Python contract tests: 131/131 passed.
- Replay-marked selection: 1 skipped, 5 deselected because the documented raw fixture directory is absent.
- `git diff --check`: passed.
- The remediation remains additive and shadow-only. No mechanics, feature vectors, checkpoints, search, live defaults, replay data, packages, servers, or network workflows were changed or started.

## BELIEF-001 acceptance — 2026-09-23

- Separate read-only acceptance review: `ACCEPT`; no remaining blocking
  findings. The review exercised imported-parent validation, sanitized and
  internally consistent observation prefixes, requestless availability,
  transition metadata types, initial simulator-truth history, and observation-
  only child serialization.
- Contract and fixture: `docs/contracts/BELIEF_STATE.md` and
  `tests/fixtures/belief_state_v1.json` define belief-state/v1 without
  unsupported probability or confidence fields.
- Focused BELIEF tests: 9/9 passed.
- `npm test --prefix sim-core`: 68/68 passed, including the accepted
  STATE-001, ACTION-001, FIXTURE-001/FIXTURE-002, and TRANS-001 regressions.
- Scoped Python suites: 194 passed, 10 skipped, and 7 failed in
  `test_live_private_value.py` while loading the existing action-ranker
  checkpoint (`_pickle.UnpicklingError: invalid load key, 'v'`). The BELIEF
  slice is TypeScript-only; no checkpoint was changed.
- Fixture JSON parsing and `git diff --check`: passed.
- ENV-001 remains independently blocked by its recorded dependency-policy and
  replay-fixture issues.
- Rollback: remove only the BeliefState module, fixture/tests, contract, and
  documentation links; preserve all accepted work items and existing research
  forks.

## DATA-001 acceptance — 2026-09-23

- Separate read-only acceptance review verdict: `ACCEPT`; the reviewer
  confirmed prefix validation, replay-ID split isolation, collection validation
  before writes, accepted-contract compatibility, and no unrelated scope.
- Contract: `docs/contracts/DATASET_LINEAGE.md` defines `dataset-record/v1`
  with deterministic identity, source/private provenance, schema fingerprints,
  observation/feature cursors, exact prefix hash verification, and
  battle/replay-disjoint split membership.
- Fixture: `tests/fixtures/dataset_lineage_v1.json` is synthetic and covers
  valid records, malformed/unsupported schemas, future cursors, prefix-hash
  mismatch, privacy contradictions, duplicate identities, battle/replay split
  collisions, and source-specific metrics.
- Implementation: `trainer/src/neural/dataset_lineage.py` plus additive
  lineage metadata and pre-write collection validation in the public replay
  value/policy and live-private value builders. Existing feature vectors and
  legacy source labels remain unchanged.
- Validation: focused DATA/replay/private selection 21/21 passed;
  `npm test --prefix sim-core` 68/68 passed; `git diff --check` passed. The
  known checkpoint-loading baseline remains separate: 194 passed, 10 skipped,
  and 7 existing failures in `test_live_private_value.py`.
- No replay acquisition, training, live evaluation, checkpoint modification,
  search redesign, package installation, or ENV-001 change was performed.
- Rollback: remove the additive contract/module/fixture/tests and builder
  lineage metadata/validation; preserve legacy datasets and consumers.

## SEARCH-001 acceptance — 2026-09-23

- Separate read-only acceptance review verdict: `ACCEPT`.
- `docs/contracts/SEARCH_SEMANTICS.md` records current trace scoring,
  replay-seeded exact rollouts, approximate scoring, one-turn branches, and
  two-ply/belief branches, including their distinct enumeration, RNG, state
  construction, and evaluation contexts.
- It explicitly documents that existing search does not consume the accepted
  ObservableBattleState, CanonicalAction, BeliefState, or SeededTransition
  contracts. Search-level exact-prefix future-event isolation, canonical
  action validation, and shared node lineage remain unresolved constraints;
  no behavior guarantee is claimed for them.
- `npm test --prefix sim-core`: 68 passed, 0 failed.
- Focused Python search suites: 19 passed, 10 skipped.
- `git diff --check`: passed.
- No runtime changes, checkpoint changes, training, live evaluation, replay
  acquisition, or ENV-001 changes were made.
- Follow-on search integration requires a separate scoped work item; the
  current SEARCH-001 rollback is documentation-only.
