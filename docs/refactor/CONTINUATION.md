# Refactor Continuation Checkpoint

Date: 2026-09-23

## Completed

- STATE-001 remediation implemented and accepted by a separate read-only review.
- Observable prefix extension, terminal contradictions, event-shape validation,
  perspective complement checks, and request redaction/hash isolation are
  covered by focused regressions.
- STATE-001 and its acceptance evidence are recorded in `STATUS.md`,
  `WORK_ITEMS.md`, and `docs/codex_review_state.md`.
- ACTION-001, FIXTURE-001, and FIXTURE-002 were subsequently accepted;
  TRANS-001 is now implemented and accepted by a separate read-only review.
- BELIEF-001 contract and additive implementation are in place, with one
  deterministic fixture and focused regressions. The first separate review
  returned `ACCEPT WITH REQUIRED CHANGES`; its parent-import, raw-request,
  transition-type, and coverage findings were remediated. Follow-up reviews
  drove protocol-shape and raw/view consistency checks, observation and
  simulator snapshot histories, and exact requestless decision-availability
  validation. The final separate read-only review returned `ACCEPT`; status,
  decision, and review records are updated below.

## Files changed

- `sim-core/src/observable_state.ts`
- `sim-core/tests/observable_state.test.ts`
- `docs/contracts/OBSERVABLE_STATE.md`
- `docs/state-schema.md`
- `docs/refactor/STATUS.md`
- `docs/refactor/WORK_ITEMS.md`
- `docs/refactor/DECISIONS.md`
- `docs/codex_review_state.md`
- `sim-core/src/canonical_action.ts`
- `sim-core/src/transition.ts`
- `sim-core/src/env_manager.ts`
- `sim-core/src/server.ts`
- `sim-core/tests/transition.test.ts`
- `tests/fixtures/canonical_action_v1.json`
- `tests/fixtures/observable_state_v1.json`
- `tests/fixtures/seeded_transition_v1.json`
- `docs/contracts/CANONICAL_ACTION.md`
- `docs/contracts/SEEDED_TRANSITION.md`
- `sim-core/src/belief_state.ts`
- `sim-core/tests/belief_state.test.ts`
- `tests/fixtures/belief_state_v1.json`
- `docs/contracts/BELIEF_STATE.md`
- `docs/contracts/DATASET_LINEAGE.md`
- `trainer/src/neural/dataset_lineage.py`
- `trainer/src/neural/build_replay_value_dataset.py`
- `trainer/src/neural/build_replay_policy_dataset.py`
- `trainer/src/neural/build_live_private_value_dataset.py`
- `trainer/tests/test_dataset_lineage.py`
- `tests/fixtures/dataset_lineage_v1.json`
- `docs/contracts/SEARCH_SEMANTICS.md`
- `docs/state-schema.md`
- `docs/refactor/CONTINUATION.md`

## Validation

- `npm test --prefix sim-core`: 68 passed, including 9 focused BELIEF tests.
- Focused TRANS-001 tests: 4 passed.
- Scoped Python suites: 194 passed, 10 skipped, 7 failed because the existing
  action-ranker checkpoint artifact cannot be loaded (`invalid load key, 'v'`)
  in `test_live_private_value.py`; no checkpoint was modified.
- Replay-marked parity selection: 1 skipped, 5 deselected; raw fixtures are
  absent by policy.
- `git diff --check` and BELIEF fixture JSON parsing: passed.
- DATA/replay/private focused selection: 21 passed, 21 deselected.
- `npm test --prefix sim-core`: 68 passed, 0 failed.
- DATA-001 separate read-only acceptance review: `ACCEPT`.
- SEARCH-001 separate read-only acceptance review: `ACCEPT`.
- SEARCH-001 validation: `npm test --prefix sim-core` 68/68 passed; focused
  Python search suites 19 passed, 10 skipped; `git diff --check` passed.

## Open blockers

- ENV-001 remains blocked by undeclared/ungated Python dependency policy and
  absent optional raw replay fixtures.
- The scoped Python run reports seven existing checkpoint-load failures in
  `test_live_private_value.py`; they remain outside this TypeScript-only
  BELIEF slice and no checkpoint was modified.
- DATA-001 leaves the same ENV-001 blockers unchanged: undeclared/ungated
  Python dependency policy and absent optional raw replay fixtures.

## Next action

SEARCH-001 is accepted and recorded as a documentation-only description of
current exact, approximate, and belief-enabled search behavior. Existing search
does not consume the accepted observation/action/belief/transition contracts;
exact-prefix future-event isolation, canonical-action validation, and stable
shared node lineage remain follow-on constraints for a separately scoped item.
No search behavior, features, checkpoints, or live defaults changed. ENV-001
remains separate and blocked.

## Current continuation — 2026-09-24

This checkpoint supersedes the SEARCH-001 next-action note above.

- Accepted through SEARCH-001: STATE-001, ACTION-001, FIXTURE-001/002,
  TRANS-001, BELIEF-001, DATA-001, and SEARCH-001.
- ENV-001 remains blocked; current evidence and remediation are in
  [`ENVIRONMENT_VALIDATION.md`](ENVIRONMENT_VALIDATION.md).
- SIM-COVERAGE-001 has a versioned manifest/checker and focused validation, but
  leaves explicit protocol and lifecycle gaps. It is not blanket simulator
  completeness or PIPELINE/FEATURE acceptance.
- PIPELINE-001 is an implementation candidate with checkpoint-free transition,
  both-perspective, successor-lineage, deterministic-identity, Python
  validation, and rejected-candidate evidence. Natural simulator rejection is
  not yet covered, so the item remains unaccepted.
- FEATURE-001 remains unresolved: there is no accepted feature schema, target,
  reward/horizon, or model input/output contract. No bulk extractor or new
  dataset is authorized before that work is reviewed.
- Existing model checkpoints are abandoned for the new approach and
  non-blocking. No new model has been trained and the real `/evaluate` route is
  not verified for a refactored model.

Next: disposition SIM-COVERAGE gaps, complete a focused PIPELINE-001 acceptance
slice including a naturally occurring simulator rejection, then design and
review FEATURE-001. Resolve ENV-001 before claiming reproducible dataset
generation or training readiness. See [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md).

## Current continuation — 2026-09-24 protocol-correction update

This note supersedes the prior 2026-09-24 next-step sequence above. It records
the current authorized work, but it is not an acceptance verdict.

### Repository and completed fixes

- Branch `refactor/state-001-observable-state`; HEAD remains
  `b9b3eb06d362963bb1fa2da21d7c471a84df262c`. The worktree contains substantial
  pre-existing changes; keep them intact and do not broadly stage, clean, or
  commit.
- Random-controller selection now accepts an injectable RNG. Legacy defaults
  still call `Math.random()`. Optional `ControllerSpec.random_seed` is a
  separate unsigned 32-bit p1/p2 stream; it does not change Showdown's
  four-word simulator seed or enter transition lineage.
- Terminal repeatability regression configuration: format
  `gen9randombattle`, simulator seed `[101, 202, 303, 404]`, p1 controller seed
  `0x51a7`, p2 controller seed `0xc0de`. Two full terminal traces compare equal
  after protocol timestamp normalization.
- Move validation now distinguishes active actor identifiers from target
  Pokémon references: `p1a: ...` and non-active `p1: ...` targets are valid;
  target may be omitted or empty; literal `null` is accepted only with a
  trailing `[notarget]`, as the pinned `useMoveInner` source emits it. Trailing
  bracket tags are validated as tags; `[notarget]` is not a target. Source
  basis: pinned `battle-actions.ts`,
  `battle.ts`, `pokemon.ts`, and `SIM-PROTOCOL.md` references recorded in
  [`../contracts/PIPELINE_INTEGRATION.md`](../contracts/PIPELINE_INTEGRATION.md).
- Pipeline projection rejects `clearstatus`, `-clearstatus`, and `nothing` at
  both prefix and step-result entry points with structured
  `pipeline/v1/unresolved-protocol-alias` diagnostics. Candidate rejection
  preserves the committed boundary and input lineage. `-nothing` remains a
  separate supported no-payload raw-only record; pinned Splash emits it from
  `data/moves.ts:18380-18384`.
- PIPELINE-002 now defines acceptance requirements for complete-episode
  progression through one-sided forced switch, waiting, and requestless states.
  No progression implementation or synthetic pass/default behavior was added.

### Fresh verification and unresolved evidence

- `npm run build --prefix sim-core`: passed.
- `node --test sim-core/dist/tests/simulator_coverage.test.js
  sim-core/dist/tests/state_extractor.test.js
  sim-core/dist/tests/observable_state.test.js
  sim-core/dist/tests/action_codec.test.js
  sim-core/dist/tests/pipeline_integration.test.js`: 41 passed, 0 failed.
- `PYTHONPATH="$PWD/trainer/src" python3 -m pytest
  trainer/tests/test_pipeline_record.py trainer/tests/test_dataset_lineage.py
  -q`: 18 passed. The TypeScript integration test also called the Python
  record validator in fresh subprocesses for both perspectives.
- Coverage checker and `--self-test`: the six synthetic self-test assertions
  passed, then both commands exited 1 because current local source digest
  `a9e4ec60254e5cc89672777cb98611279e2b7da3fca4a9c57a233ea0ea07b8af` differs
  from the reviewed digest. The digest was intentionally not refreshed; a
  separate semantic review of the changed sources/tests is required.
- A bounded natural-rejection probe exercised all 169 valid initial joint
  action pairs for simulator seed `[101, 202, 303, 404]`; all 169 transitioned
  and none produced `pipeline/v1/rejected-action`. This is one-seed bounded
  evidence, not proof that a natural rejection is impossible. The existing
  injected rejection remains clearly labeled injected. PIPELINE-001 still
  needs a reviewer decision on its natural-rejection criterion.
- No clean-environment install/build, package install, network access, replay
  acquisition, dataset generation, feature extraction, or training occurred.
  Missing raw replay fixtures do not block the first simulator-only milestone;
  replay-specific claims still require fixtures.

### Current sequence and milestones

1. Deterministic protocol and stopping-behavior fixes.
2. SIM-COVERAGE gap disposition and complete-episode boundary requirements.
3. PIPELINE acceptance with explicit supported scope and rejection guarantees.
4. ENV reproducibility remediation in parallel.
5. Training objective/information regime together with FEATURE-001 and the
   model interface.
6. Feature extraction, bounded collector, and validated pilot dataset.
7. New-model training and held-out evaluation.
8. Live/search integration and operational hardening.

Dataset, model, and product-release milestones are defined separately in
[`../PROJECT_STATUS.md`](../PROJECT_STATUS.md). ENV-001 still needs tested
Python/Node/npm support policy, declared dependencies, a Python lock/constraints
choice, and clean-environment validation. The simulator-only record validator
uses Python standard library modules; wider trainer dependencies are separate.

### Exact next actions and blockers

1. Complete the documentation updates and final `git diff --check`.
2. Obtain separate semantic review of the move/alias/controller source and
   focused tests before any coverage digest attestation is updated.
3. Resolve the natural-rejection acceptance criterion using the bounded probe
   evidence or a real admissible simulator case; do not relabel injection.
4. Disposition per-effect simulator lifecycle gaps and review PIPELINE-002's
   real request progression requirements before claiming full episodes.
5. Resolve ENV-001 in parallel; no package acquisition is part of this task.
6. Decide the model target/information regime together with FEATURE-001 before
   extraction or collection.

[`WEST_MONROE_REVIEW_EVIDENCE.md`](WEST_MONROE_REVIEW_EVIDENCE.md) is an evidence
index for a later review, not a compliance verdict. No internal West Monroe
standard was supplied or inferred, and no completion percentage or timeline is
claimed.

### Review closeout — 2026-09-24

- PIPELINE-001 is accepted for v1 joint-actionable requests (including joint
  forced switches) with protocol fail-closed behavior, exact prefix/lineage
  joins, and disposable candidate publication. One-sided forced switch,
  waiting, requestless, and complete-episode progression remain PIPELINE-002.
- A natural post-preflight rejection was demonstrated, so the criterion remains
  mandatory. Seed `[46, 101, 202, 303]` generates Dugtrio/Arena Trap for p1 and
  Steel-type Tinkaton for p2. After both switch in, Showdown's hidden-trap
  request does not set `trapped`; the request-derived action list therefore
  offers a switch. `Side.chooseSwitch` naturally rejects it. The regression
  proves the committed boundary and lineage remain unchanged and compares the
  next valid transition with a parallel control session.
- The listed local coverage-source digest was reviewed and attested as
  `479a096563318af86addd64dd39d445c56e8c5b4d9c8ba0a1c0e100b3c3861d2`.
  This review is scoped to listed parser/pipeline sources and tests; known
  per-effect lifecycle, clean-tarball, and cross-format gaps remain.
- Fresh results: build passed; focused TypeScript 42/42; Python record/lineage
  18/18; coverage checker passed for 142 classified IDs, 111 parser tokens,
  and 86 literal emitter tokens; all six checker self-tests passed.
- ENV-001 remains blocked with a remediation plan. Optional raw replay fixtures
  are unnecessary for the first simulator-only milestone. Dataset, model, and
  product-release gates remain separate; FEATURE-001 and dataset generation
  remain unaccepted/unperformed.
- **Next task:** disposition the remaining SIM-COVERAGE lifecycle gaps that
  constrain PIPELINE-002 boundary progression. See the task-specific progress
  checkpoint for commands and detailed source evidence.

## Final checkpoint — 2026-09-24

The focused implementation and documentation work is complete. Fresh results:
build passed; focused TypeScript 41/41; Python record/lineage 18/18;
`git diff --check` passed. The coverage checker and its six successful
synthetic self-tests still stop on local source digest
`a9e4ec60254e5cc89672777cb98611279e2b7da3fca4a9c57a233ea0ea07b8af`; do not
refresh the reviewed digest before separate semantic review.

Remaining acceptance work: separate semantic review and coverage-gap
disposition; PIPELINE-001 natural-rejection criterion decision and explicit
supported-scope review; PIPELINE-002 real one-sided forced-switch, waiting,
requestless, and truncation progression; ENV-001 runtime/dependency/lock policy
and clean-environment evidence; FEATURE-001 target/information regime and model
interface. The bounded 169-pair probe found zero natural post-preflight
rejections and is not proof none exist. PIPELINE-001 and FEATURE-001 remain
unaccepted. No West Monroe compliance claim is made. Resume from the
task-specific checkpoint linked above; do not repeat completed tests or the
bounded probe.
