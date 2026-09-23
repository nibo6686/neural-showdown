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
- The only existing top-level documentation change is the requested link and
  cursor clarification in `docs/state-schema.md`; the normative contract and
  replay policy remain in the requested documentation tree.
- Baseline branch, tag, commit, and environment blockers are recorded below.

## Objective

Prepare a controlled refactor while keeping Showdown/sim-core as the authoritative mechanics engine. Separate authoritative state, player-observable state, beliefs, canonical actions, transitions, features, and search. Preserve raw protocol events, prevent future-information leakage, make seeded transitions reproducible, and make model/data/action/schema provenance explicit.

## Baseline

- Branch: `main`
- Baseline tag: `v1-live-eval-51-gc4477b6`
- Baseline commit: `c4477b6151885b35847da71110729867d9e48d5d`
- Production source changes in this session: one additive, shadow-only
  `sim-core/src/observable_state.ts` adapter; existing mechanics and consumers
  are unchanged.
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
- `STATE-001` review result: `ACCEPT WITH REQUIRED CHANGES`.
- `ENV-001` result remains `BLOCKED_WITH_REMEDIATION`; contract acceptance is
  still pending the documented dependency policy and replay-fixture condition.
- ENV-001 Node validation: PASS (40/40 full sim-core tests, including five new
  observable-state tests; 11/11 focused state/env-manager tests). Python
  replay-independent validation is 131/131 passed. Replay-backed selection is
  marked and reports 2 skipped with the documented reason when the raw fixture
  directory has no `.log` files.
- The attempted whole-suite Python run was not used as readiness evidence: it
  contains pre-existing benchmark/checkpoint/replay-asset failures outside the
  focused validation set and was stopped. No replay data was downloaded and no
  packages were installed.
- Environment details and remediation steps: [ENVIRONMENT_VALIDATION.md](ENVIRONMENT_VALIDATION.md).
- `ACTION-001` must not begin until `STATE-001` is accepted.
- The orchestrator is the only writer of aggregate status files.

## Current prepared item

`STATE-001` has a review-pending shadow slice. The normative schema is in
[`../contracts/OBSERVABLE_STATE.md`](../contracts/OBSERVABLE_STATE.md), the
adapter is `sim-core/src/observable_state.ts`, and focused tests are in
`sim-core/tests/observable_state.test.ts`. Existing feature vectors, model
inputs, checkpoints, live defaults, and search remain unchanged.
