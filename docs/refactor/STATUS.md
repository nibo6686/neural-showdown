# Refactor Readiness Status

## Current reconciliation — 2026-10-09

C22 and C23 are accepted and registered only within their independently reviewed finite public-consequence scopes. FCE-01 has zero unresolved reachable P0 source/evidence inventory rows after reconciling C01–C30 against their source proofs and verdicts. Unsupported expansions and unknown forms remain fail-closed. This supersedes historical open-registration summaries below, without changing their original decisions.

CE-08A positive complete-episode evidence received scoped independent acceptance on 2026-10-09. Original-to-terminal normal win, source simultaneous terminal outcome and turn-limit tie, both perspectives, actor-only publication, restoration/privacy and coherent tamper rejection are supported by matching-source recorded evidence. The long chain published 1,996 segment rows and two predecessor rows. Recovered outcome/origin Python controls each exited 2 with zero stdout (115.192s / 5.017s), resolving their missing evidence. The original long command still exited 1 at its earlier 30s timeout; the historical combined short-command 182.032s timeout remains unresolved. Neither invocation is claimed passing.

CE-08B received independent scoped acceptance for pinned v2 S01–S12 incomplete/error classification, limits/accounting and construction/cleanup delivery. FCE-08 is separately accepted for the explicitly reconciled FCE-01–FCE-08 source/semantic evidence packet. The four metadata/cleanup findings are resolved with matching artifact-only evidence; see the existing independent review record. The subsequent final PIPELINE-002 decision accepts pinned v2 capture/boundary progression. Conditional faithful_complete_episode emission and matching TS/Python validation received scoped independent runtime acceptance on 2026-10-09. True requires validated supported original-to-terminal evidence and successful execution/cleanup; false is conservative and mandatory for ineligible results. It remains a per-result claim, not a capability flag. Merge readiness and datasets/training/live remain separate. See the existing final decision for scope and next task.


## Historical project status — 2026-10-07

The following snapshot and delivery sequence retain their recorded checkpoint
meaning; the current 2026-10-09 reconciliation above governs accepted scope.

Current authoritative summary: [PROJECT_STATUS.md](../PROJECT_STATUS.md).
The current checkout is branch `refactor/state-001-observable-state`, HEAD
`6475d01e9d1bf2766339e41ac3d0738902e4046e`. The worktree is dirty; this HEAD
is not a reviewed snapshot and uncommitted work is not acceptance evidence.

- Bounded v2 transition capture and TypeScript/Python publication parity are
  accepted for the reviewed ordinary joint-actionable scope. PIPELINE-001's v1
  scope also remains separately accepted.
- Scanner expansion, source-coverage, and Gen 9 Random Battle format/reachability
  slices have accepted scoped attestations. They do not establish universal
  simulator coverage; unknown and unclosed forms remain explicit stops.
- CE-01's aggregate Glaive Rush fixture correction and CE-04C's public-stage
  source/evidence closure were accepted within their separate 2026-10-06 scopes.
- CE-06A's privacy regression now propagates the foreign p2 request through
  p1's origin observation, first actor record, every dependent p1 belief
  reference, and the initial/final summaries. The test validates every p1
  boundary/record join and canonical belief identity before TypeScript rejects
  the ownership mismatch; Python validates the altered origin record and
  rejects the same full result with exit 2 and empty stdout. No production
  change was needed. The CE-06A local/reviewed coverage digest is
  `e7d5e2f6279fc0cc0895e048e6b8fce7971431d44e0366861651d5700a291c1c`;
  it is attested only for CE-06A. Prior scoped attestations remain intact.
- CE-06B's v2 terminal/segment closure received a separate scoped attestation
  on 2026-10-06. It has recursively validated
  predecessor/origin joins, matching terminal win/tie references, explicit
  original/segment/terminal-only coverage, and actor-only publication. Source
  restored win/tie and one-sided terminal paths, resumed-chain controls, and
  rehashed tamper rejection pass. The 2026-10-06 CE-08A pre-edit
  reconciliation is blocked by a missing initial-request-to-turn-limit-tie
  chain, a missing source-engine simultaneous-outcome episode, and unresolved
  FCE-01 computed-effect dispositions between the audit and coverage manifest.
  No selective positive suite was added. CE-08A/08B and remaining P0
  dependencies remain open, and `faithful_complete_episode:false` remains
  required.
- The complete-episode closure audit is complete as a gap inventory and plan.
  The 2026-10-06 CE-08A blocker batch closed the turn-limit origin chain,
  simultaneous-outcome source witness, and six manifest/audit disposition
  paths. On 2026-10-07, the turn-limit tie path also bulk-published all 1,996
  current-segment actor rows through Python DATA-001 validation (155.4 seconds),
  separately published its two predecessor rows, and rejected a rehashed
  middle-row ownership tamper atomically. This closes that scoped review
  finding only; CE-08A's aggregate positive-suite review, CE-08B, remaining P0
  gates, and complete-episode acceptance are still open.
  `faithful_complete_episode:false` remains required.
- `faithful_complete_episode:false` remains required. The active milestone is
  faithful, privacy-correct `gen9randombattle` episode capture.
- ENV-001 is incomplete for cross-platform claims. The macOS simulator-record
  and broader trainer/live profiles have accepted evidence within their
  documented scope. Windows clean recreation and Windows trainer/live packaging
  are deferred and do not block a future scoped macOS refactor merge.
- FEATURE-001, feature extraction, datasets, training, live-model behavior, and
  other formats remain later milestones. No readiness claim is made for them.

## Historical next delivery sequence — 2026-10-07

1. Complete the separate CE-08A review against its positive-suite evidence and
   remaining FCE gates; do not promote this publication-only checkpoint into
   aggregate acceptance.
2. Complete CE-08B stop classification and final review evidence, then resolve
   remaining P0 closure-audit rows.
3. Run final macOS validation, complete branch-level `$wm-pr-review`, reconcile
   findings, then update from `main`, merge, and verify the resulting checkout.

Windows clean recreation and Windows trainer/live support remain deferred. Their
open ENV-001 work is not a blocker to this scoped macOS merge path.

## Historical preparation record — status as recorded 2026-09-24

The checkpoint below preserves its original preparation findings and validation
history. Its dates, branch/HEAD values, and then-current next steps are historical;
the current status and sequence are above.

### Project status recorded on 2026-09-24

### Gate status recorded 2026-09-24

`DOCUMENTATION_PREPARATION: COMPLETE`

`NEW_DATASET_PIPELINE_READY: NO`

`NEW_MODEL_TRAINING_READY: NO`

`NEW_MODEL_LIVE_EVALUATION_READY: NO`

The earlier `READY_FOR_REFACTOR` value referred only to completion of the
initial documentation-preparation gate. It must not be read as readiness to
construct a new dataset, train a model, or evaluate a live route.

### Gate evidence recorded 2026-09-24

- All requested documentation files plus the replay-fixture policy document
  exist.
- `CTRL-001` through `SEARCH-001` are present in [WORK_ITEMS.md](WORK_ITEMS.md).
- Every work item has status, owner, dependencies, acceptance criteria, tests, and rollback.
- Referenced documentation targets exist and work-item IDs resolve.
- The top-level state-schema clarification and normative observable-state
  contract are tracked alongside the additive adapter; replay policy remains in
  the requested documentation tree.
- Baseline branch, tag, commit, and environment blockers are recorded below.

### Objective in the original preparation scope

Prepare a controlled refactor while keeping Showdown/sim-core as the authoritative mechanics engine. Separate authoritative state, player-observable state, beliefs, canonical actions, transitions, features, and search. Preserve raw protocol events, prevent future-information leakage, make seeded transitions reproducible, and make model/data/action/schema provenance explicit.

### Baseline recorded in the original preparation scope

The following values record the original preparation baseline, not the current
workspace branch or HEAD.

- Branch: `main`
- Baseline tag: `v1-live-eval-51-gc4477b6`
- Baseline commit: `c4477b6151885b35847da71110729867d9e48d5d`
- Production source changes in this session: additive observable-state,
  canonical-action, and seeded-transition adapters; legacy mechanics,
  raw-choice consumers, and default paths remain unchanged.
- Simulator replacement: prohibited in this phase

### Environment blockers recorded at the 2026-09-24 checkpoint

- The bare `python` and direct `pytest` commands are not on PATH; use `/Library/Developer/CommandLineTools/usr/bin/python3` and `python3 -m pytest`, or add `$HOME/Library/Python/3.9/bin` to PATH.
- Python packages are installed and importable from `$HOME/Library/Python/3.9/lib/python/site-packages`.
- Node/npm are available through `<NVM_DIR>/versions/node/v24.21.0/bin`; sim-core packages and compiled server are present.
- Remaining blockers are runtime/dependency reproducibility policy and
  clean-environment validation. Raw replay fixtures are optional for the first
  simulator-only milestone and remain required only for replay-specific claims.

### Readiness constraints recorded at the 2026-09-24 checkpoint

- Replay policy closeout and the additive STATE-001 shadow slice are complete;
  production refactoring and model integration remain out of scope.
- Production state/model refactoring begins only after `STATE-001` is reviewed.
- `STATE-001` review result: `ACCEPT` (2026-09-23).
- `ENV-001` result remains `BLOCKED_WITH_REMEDIATION`; contract acceptance is
  still pending the documented dependency/runtime policy, lock strategy, and
  clean-environment smoke. Missing raw replay fixtures do not block the first
  simulator-only milestone.
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

### SIM-COVERAGE / PIPELINE / FEATURE gate recorded at the 2026-09-24 checkpoint

- `SIM-COVERAGE-001`: inventory and checker status are recorded in
  [`../contracts/SIMULATOR_COVERAGE.md`](../contracts/SIMULATOR_COVERAGE.md)
  and [`SIM-COVERAGE-001_PROGRESS.md`](SIM-COVERAGE-001_PROGRESS.md). Review
  evidence includes 142 classified condition/effect IDs, 111 parser tokens,
  and 86 package-wide literal emitter tokens. The counts are not completeness
  evidence. The pipeline now rejects the three unknown generic aliases before
  publication, but their semantics, private lifecycle state, side-condition
  expiry, and protocol paths outside the scoped format remain review gaps.
- `PIPELINE-001`: accepted for explicit v1 joint-actionable boundaries after
  source review and fresh validation on 2026-09-24: 42 focused TypeScript and
  18 focused Python tests passed. The seeded natural hidden-trap rejection,
  injected rejection, protocol stops, and lineage preservation are covered.
  Raw-only evidence is not typed feature state; out-of-scope boundaries remain
  explicit failures.
- `PIPELINE-002`: concrete complete-episode requirements are documented for
  one-sided forced switch, waiting, and requestless boundaries; implementation
  and real progression tests remain future work.
- `FEATURE-001`: no accepted feature schema, target definition, reward/horizon
  contract, or stable training/runtime model interface exists. Do not change
  legacy/v7/v8 dimensions to fill this gap.
- The next review is disposition of the remaining SIM-COVERAGE lifecycle gaps
  that constrain PIPELINE-002. ENV-001 remediation proceeds in parallel;
  dataset generation and training remain gated by environment, feature, target,
  and episode-policy acceptance. The full current sequence is in
  [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md).

### Focused verification recorded 2026-09-24

- `npm run build --prefix sim-core`: passed.
- Focused TypeScript selection including coverage, state extraction, observable
  state, action codec, and pipeline integration: 41 passed, 0 failed.
- `PYTHONPATH="$PWD/trainer/src" python3 -m pytest
  trainer/tests/test_pipeline_record.py trainer/tests/test_dataset_lineage.py
  -q`: 18 passed.
- Simulator coverage self-test assertions: all six passed; both checker
  commands exit 1 because the local reviewed-source digest differs after the
  new parser/pipeline/test edits. No reviewed digest was refreshed.
- `git diff --check`: passed after final code and documentation edits.
- Task-specific command/results and remaining acceptance work are in
  [`PIPELINE-CORRECTNESS-2026-09-24-PROGRESS.md`](PIPELINE-CORRECTNESS-2026-09-24-PROGRESS.md).

### Accepted preparation scope as of 2026-09-23

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

## CE-08A blocker closure batch — 2026-10-07

- FCE-07 has mirrored source-engine simultaneous-knockout witnesses from
  original requests, with replay, terminal agreement, actor-only Python
  publication, and rehashed tamper rejection.
- FCE-01's six computed `addVolatile`/`linkedStatus` paths now have a checked
  manifest/audit/test crosswalk; aggregate FCE-01 remains open.
- The fresh-origin turn-limit tie chain passed focused validation from original
  requests through the source turn-1000 tie, with a validated predecessor and
  Python envelope checks. Final CE-08A positive-suite review remains separate.
  `faithful_complete_episode:false` is unchanged.

## FCE-01 aggregate reconciliation — 2026-10-07

The C01–C30 machine-checkable reconciliation records four remaining reachable
P0 blockers: public volatile lifecycle truth (C17), aggregate side-condition
layer/expiry truth (C20), callback-composition truth (C22), and slot-effect
sufficiency (C23). The prior computed `addVolatile` / `linkedStatus`
disposition drift is closed by the manifest/audit/checker crosswalk. Final
CE-08A positive evidence remains deferred until all four are closed;
`faithful_complete_episode:false` remains required.

## C17/C20 scoped lifecycle verdict — 2026-10-07

Independent review accepted C17/C20's evidence-derived lifecycle boundary from
implementation digest `9319ea2131a777315e2194240cd2cd3bc18458676a7651a18e1f18161f2836c2`.
C22 callback composition and C23 slot-effect sufficiency remain FCE-01 blockers;
CE-08A remains withheld and `faithful_complete_episode:false` remains required.


## C17/C20 typed-state implementation checkpoint — 2026-10-07

A manifest-backed public-prefix projection now constrains typed volatile and
side-condition maps in TypeScript and Python publication. It keeps Substitute
and eight rooted side conditions typed, downgrades other inventoried volatiles
to raw-only, and fails closed on 15 side-condition IDs without approved generated
roots. Source-backed equivalence rules and fully rehashed cross-runtime false-map
controls are in place.

This is unreviewed implementation evidence, not a C17/C20 verdict. C22 and C23
remain unresolved, so FCE-01 and CE-08A remain open. The local coverage digest is
`c5a5fc3112a1778af1adb9e5b817b9639b1b183ac8a6d42f6ccc0ea043d12e4d`;
`reviewed_sha256` is unchanged pending separate review.

Validation: build passed; focused TypeScript 96/96; focused Python 46/46;
coverage self-test passed; normal coverage checker reports only the expected
unreviewed semantic-digest mismatch; `git diff --check` passed.
`faithful_complete_episode:false` remains required.

## C17/C20 typed-row omission repair — 2026-10-07

The typed-state validators now reject a fully rehashed observation when its
public prefix derives nonempty Substitute state for an ident that has no unique
canonical roster row on the correct perspective. Missing, duplicate, and
wrong-side rows reject before publication; row synthesis and hidden-identity
inference are not introduced.

Targeted controls cover ordinary DATA-001 records and a v2 episode-origin
boundary with rehashed observation, belief, summary, actor-record, run/origin,
envelope, and reference identities. Valid Substitute rows remain valid. The
omitted-row cases reach the typed evidence mismatch; Python exits 2 with empty
stdout and TS preserves the committed boundary.

Validation: build passed; selected TS lifecycle, ordinary-record, and v2-boundary
tests passed 3/3; Python typed-state and pipeline-record suites passed 47/47;
coverage reachability self-test and `git diff --check` passed. The ordinary
coverage checker continues to report only the expected separate semantic-review
digest gate. Local digest: `fd2b787af19a5cc597cd511f25801003382e33649323afb83c9968771a258217`;
`reviewed_sha256` is unchanged. C17/C20 remain unreviewed and unattested; C22/C23
remain open, CE-08A remains withheld, and `faithful_complete_episode:false`
remains required.

## C17/C20 view-less v1 replay bypass repair — 2026-10-07

Python publication now replays the prefix before historical v1 compatibility.
A view without typed projections publishes only when the prefix derives no
typed volatile or side-condition state. Fully rehashed Substitute and Spikes
controls reject with exit 2 and empty stdout; the empty-state v1 control and
ordinary/v2 regression coverage pass. Coverage self-test and diff check pass;
the normal checker confirms the refreshed local digest and retains only the
separate semantic-review gate. The reviewed digest is unchanged. C17/C20 remain
unreviewed, C22/C23 remain open, and `faithful_complete_episode:false` remains
required. See the audit and pipeline progress checkpoint for evidence and
hashes.

## C17/C20 partial typed-view bypass repair — 2026-10-07

Validators require projected Substitute values to have a unique owning-side
roster row and require derived own/opponent side conditions in their correct
field compartment. Missing representation containers reject only when the
prefix derives a value requiring them. Seven fully rehashed controls pass their
TS/Python rejection assertions, including Python exit 2 with empty stdout and
unchanged committed TS boundary. Focused validation passed: TS 37/37, v2
episode-origin 1/1, Python 49/49, coverage self-test, and diff check. Local
digest `9319ea2131a777315e2194240cd2cd3bc18458676a7651a18e1f18161f2836c2` is
current; reviewed digest remains unchanged pending separate review. This is not
a C17/C20 attestation. C22/C23 remain open and
`faithful_complete_episode:false` remains required.

## C22/C23 callback and slot consequence checkpoint — 2026-10-07

C23 retains source-route evidence but remains unresolved after independent semantic review. The machine-readable
`public_consequence_matrix/v1` binds the pinned source tree, move/ability
candidate digests, selector digest, eight callback/slot source-file hashes,
direct slot roots, Future Sight's imperative `futuremove` route, and the three
source-unreachable exclusions. Both-perspective source-engine tests cover
Wish, Healing Wish, Future Sight, and Revival Blessing through restoration,
rollback, switch/drag, faint/replacement, terminal outcomes, and Python
publication. Private timers, slot occupants, and source metadata remain out of
public state.

C22 stays open for broader callback-state truth. Ordered public item replay now rejects the original mirrored rehashed Sitrus
presence forgeries and unsupported presence assertions, including existing
disposition, last-item and suppression fields. Neutralizing Gas has a complete
bounded no-route disposition: absent from 203 authored candidates and six form
defaults, with no unseeded copy/transfer route. Constructed native-engine tests
prove global suppression, exemptions, multi-source cleanup, silent End/Start,
restoration and unsupported publication. Known names are retained; internal
unknown effectiveness never becomes a guessed opponent loadout.

C23 now rejects the six original Wish false HP/status/faint maps and partial
public health representation in both runtimes. Actual sibling source bundles,
full-result Wish and original-to-terminal health controls also reject after
complete rehashing. Valid living unrevealed terminal Illusion now uses validated
committed predecessor identity through native sessions, ordinary linked bundles,
and full envelopes with predecessor closure. Incoming unrevealed switches
require an action-bound ordinary/full/bulk path; bare envelopes lack the action.
Bare deserialized observations cannot authorize an unrevealed alias; mutable alias fields cannot authorize them. C23
remains open pending independent acceptance of the mirrored restoration and
coherent forgery matrix.
The checker keeps C22/C23 as unresolved; C17/C20 acceptance is unchanged.
FCE-01 and CE-08A remain open, reviewed coverage stays unchanged, and
`faithful_complete_episode:false` remains required. See the closure audit's
2026-10-08 bounded repair checkpoint for the precise acceptance matrix.


## C22/C23 resumed implementation freeze — 2026-10-08

Action-bound incoming terminal identity, private v2 switch restoration,
attributable item history and raw-only unknown historical carriers are implemented.
The exact near-turn-1000 terminal-switch/source authority test passed 1/1 in
28.210s. Source/tests are frozen while the parent runs all remaining validation
sequentially with visible output and bounded subprocess timeouts. See the closure
audit for final matrices, commands and hashes. No new semantic attestation is
claimed: C22/C23, FCE-01, CE-08A/08B and PIPELINE-002 remain open, and
`faithful_complete_episode:false` remains required.


Final current-hash item/identity matrix: **48/48 passed in 142.137s**, covering
2,644 ordinary and 246 each full-result, envelope and compact-bulk adversarial
candidates. The earlier timed-out runs are superseded. Remaining focused and
complete-chain validation is recorded separately in the closure audit; this
matrix adds no semantic attestation or gate promotion.


The subsequent full episode job exhausted its inherited 600s outer budget
during bulk publication after 1,000 native commits; it is not passing evidence.
The parent is repairing repeated historical prefix hashing with a fresh
per-validation incremental stream and unchanged canonical bytes/checks. This
source change revokes the prior freeze; the earlier 48/48 and suite passes
remain bound to their old hashes until affected current checks run. The full
episode wrapper now uses a 3,000s outer budget, with existing bounded Python
phases. Current results and hashes will be recorded in the closure audit. No
C22/C23 attestation or complete-episode gate is changed.


After the bounded per-validation history-hash correction, the fresh current
source matrix passed **48/48 in 140.487s**, with 2,644 ordinary and 246 each
full-result, envelope and bulk adversarial candidates. The new 20-file freeze
and raw hashes are recorded in the closure audit. Remaining focused suites and
complete-chain checks run sequentially; no earlier-source pass is substituted.
C22/C23 and complete-episode gates remain open pending independent acceptance.

Current-source focused TS/Python checks passed 241/241 and 58/58. The focused
episode shortcut passed 33/34 before a test-only diagnostic correction; its
affected case passed 1/1 afterward. The 1,000-turn Python bulk publication is
still unverified after the canceled run, and no further long test was started
following the user's fast-stop instruction. The closure audit records exact
hashes and limits. No scoped attestation or fidelity flag changed.

Publication path notation: `$HOME` denotes the user home; `<NVM_DIR>` denotes the local nvm installation. Resolve executables with `command -v node` and `command -v npm`, and Python locations with `python3 -m site`. These portable references preserve the recorded host versions; they do not declare a new supported runtime.
