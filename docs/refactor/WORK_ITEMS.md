# Refactor Work Items

All items are documentation/preparation work unless explicitly marked otherwise. No item authorizes production changes by itself. For the current readiness snapshot, see [PROJECT_STATUS.md](../PROJECT_STATUS.md).

| ID | Title | Status | Owner | Dependencies |
|---|---|---|---|---|
| CTRL-001 | Refactor control documents and baseline tag | Complete (documentation only) | Orchestrator | Review state, README |
| STATE-001 | ObservableBattleState contract | Accepted | State owner | CTRL-001, ENV-001, existing state schema |
| ENV-001 | Reproducible Python/Node validation environment | Blocked with runtime/dependency/lock policy and clean-environment remediation | Environment owner | CTRL-001, baseline tag |
| BELIEF-001 | BeliefState contract | Accepted | Belief owner | STATE-001, FIXTURE-001, TRANS-001 |
| ACTION-001 | CanonicalAction contract | Accepted | Action owner | STATE-001, existing action codec |
| FIXTURE-001 | Protocol-prefix golden fixtures | Accepted | Test owner | STATE-001 |
| FIXTURE-002 | Python/TypeScript action parity fixtures | Accepted | Test owner | ACTION-001, STATE-001 |
| TRANS-001 | Seeded transition contract | Accepted | Simulation owner | STATE-001, FIXTURE-001 |
| DATA-001 | Dataset lineage and battle-level splits | Accepted | Data owner | STATE-001, BELIEF-001 |
| SEARCH-001 | Document current rollout/search semantics | Accepted | Search owner | STATE-001, TRANS-001, BELIEF-001 |
| SIM-COVERAGE-001 | Pinned simulator state and protocol coverage | Review complete with documented gaps; not accepted | Simulation owner | ENV-001, STATE-001, BELIEF-001, ACTION-001 |
| PIPELINE-001 | Checkpoint-free transition integration | Accepted for explicit v1 joint-actionable scope | Simulation/data owners | SIM-COVERAGE-001, STATE-001, ACTION-001, TRANS-001, BELIEF-001, DATA-001 |
| PIPELINE-002 | Complete-episode boundary progression | V2 publication and reference/identity validation scoped accepted | Simulation/data owners | Review bounded Topsy-Turvy inversion; coverage pending |
| FEATURE-001 | Shared model feature contract | Unresolved; contract not accepted | Model/data owners | SIM-COVERAGE-001, PIPELINE-001, ENV-001 |

## CTRL-001 — Refactor control documents and baseline tag

- Status: Complete (documentation preparation)
- Owner: Orchestrator
- Dependencies: Review state and README read; baseline branch/tag recorded
- Acceptance criteria: All requested preparation documents exist; this registry is authoritative; aggregate state is updated only after synthesis; baseline and blockers are recorded. Documentation-preparation completion does not establish data/model readiness.
- Tests: Documentation existence check, ID/reference check, `git diff -- docs` review.
- Rollback: Remove only newly created refactor documentation if the user rejects the preparation; preserve existing top-level docs and review state history.

## STATE-001 — ObservableBattleState contract

- Status: Accepted (2026-09-23)
- Owner: State owner
- Dependencies: CTRL-001, ENV-001; `docs/state-schema.md`; `sim-core/src/types.ts`; `sim-core/src/state_extractor.ts`; `sim-core/src/env_manager.ts`.
- Acceptance criteria: Expand `docs/contracts/OBSERVABLE_STATE.md` into a normative versioned field schema with visibility classification, immutable-snapshot semantics, identity/cursor/hash rules, phase/request boundaries, source precedence, invalid-state behavior, and explicit mapping of `StepResult`, `BattleView`, and `ChoiceRequestView`.
- Tests: `sim-core/tests/observable_state.test.ts` covers deterministic prefix
  hashing, normalized-record cursors, immutability/future-event isolation,
  request-less redaction, perspective/request consistency, contradictions, and
  unsupported schemas. Full sim-core validation is 48/48 passed.
- Rollback: Revert only the contract and test changes; retain existing `BattleView` and Python representations unchanged until an adapter is available.

### STATE-001 preparation plan

Exact source files involved:

- `sim-core/src/types.ts`
- `sim-core/src/state_extractor.ts`
- `sim-core/src/env_manager.ts`
- `trainer/src/neural/parse_replay_logs.py`
- `trainer/src/neural/live_private_state.py`
- `trainer/src/neural/tactical_state.py`
- `trainer/src/neural/live_private_features.py`
- `trainer/src/neural/value_features.py`
- `docs/state-schema.md`

Smallest change implemented: introduce and document a state-boundary adapter/schema
without changing mechanics, feature values, model checkpoints, or live defaults.
The adapter validates private raw request evidence, exposes only a sanitized
canonical protocol prefix plus an immutable observation snapshot with explicit
provenance, and remains shadow-only.

Tests and golden fixtures: request-prefix fixtures, switch/replace, damage/status/faint, tera/transform/illusion, perspective redaction, event-cursor monotonicity, and rejection of future events.

Rollback: remove the adapter/schema and its tests while leaving the existing state extractor and feature paths intact.

### STATE-001 acceptance evidence — 2026-09-23

- Acceptance reviewer verdict: `ACCEPT`; no remaining STATE-001 gaps were identified.
- `npm test --prefix sim-core`: 48 passed, 0 failed.
- Focused observable-state tests: 13 passed, 0 failed.
- Replay-independent Python contract tests: 131 passed, 0 failed.
- Replay-marked parity selection: 1 skipped, 5 deselected because raw fixtures are absent; no replay acquisition was run.
- `git diff --check`: passed.
- Acceptance covers ordered prefix extension and repeated turns, symmetric terminal contradiction handling, supported-event shape validation, perspective/opponent complement checks, sanitized request serialization/hashing, raw evidence consistency, immutable snapshots, request-less states, and shadow-only scope.
- At the STATE-001 acceptance checkpoint, ACTION-001 was unblocked but had not started. ACTION-001 was subsequently accepted as recorded below.

Validation dependencies: Python package environment with NumPy/pytest for Python tests; built `sim-core` and Node dependencies for TypeScript tests. No training, replay fetch, or server is required.

## ENV-001 — Reproducible Python/Node validation environment

- Status: Blocked with runtime/dependency/lock policy and clean-environment
  remediation. The historical replay-fixture failure applies only to
  replay-specific validation; replay files are not required for the first
  simulator-only milestone.
- Owner: Environment owner
- Dependencies: CTRL-001; baseline branch/tag
- Acceptance criteria: Record supported Python and Node/npm versions; distinguish runtime and development dependencies; choose the supported dependency declaration/lock mechanism; document sim-core build steps; provide a clean-environment smoke test and exact focused-test commands; record platform-specific assumptions; verify the focused validation suite in a clean environment.
- Tests: Clean-environment dependency resolution; sim-core build check; focused
  Python test command; focused TypeScript test command; import/version smoke
  test. Historical evidence: sim-core full suite 40/40 passed; focused
  state/env-manager suite 11/11 passed; replay-independent Python subset
  131/131 passed; replay-backed selection is marked and skips when the raw
  fixture directory has no `.log` files. Fresh 2026-09-24 pipeline-record and
  DATA-lineage Python selection passed 18/18 in the existing environment.
  Python dependency/runtime policy and lock/constraint strategy remain
  unresolved, and no clean-environment run has occurred.
- Rollback: Documentation-only; retain the existing developer environment and do not alter dependency declarations until separately approved.

## BELIEF-001 — BeliefState contract

- Status: Accepted (2026-09-23)
- Owner: Belief owner
- Dependencies: STATE-001, FIXTURE-001, and TRANS-001; existing belief-fork and live-belief paths were inspected and remain unchanged.
- Acceptance criteria: Define a separate, versioned, perspective-owned snapshot for hypotheses, explicit evidence, unresolved uncertainty, and lineage without contaminating ObservableBattleState. Do not add probability or confidence unless supported by an existing calibrated contract.
- Implementation: `sim-core/src/belief_state.ts` adds belief-state/v1 with deterministic candidate/evidence IDs, canonical serialization, immutable snapshots, source observation and transition histories, fail-closed import validation, and direct/derived/prior/simulator-only provenance. It does not propagate beliefs or alter existing consumers.
- Fixture and tests: `tests/fixtures/belief_state_v1.json`; `sim-core/tests/belief_state.test.ts` covers deterministic identity/order, mutation isolation, observation and transition lineage, parent revalidation, sanitized and consistent observations, all provenance boundaries, derived-evidence references, stale/future/cross-perspective rejection, contradictions, open-world uncertainty, and simulator-truth separation.
- Evidence: Final separate read-only review `ACCEPT`; focused BELIEF tests 9/9 passed; full sim-core suite 68/68 passed; scoped Python suites 194 passed, 10 skipped, and 7 failed on the existing action-ranker checkpoint artifact (`invalid load key, 'v'`) outside this TypeScript-only slice; `git diff --check` and fixture JSON parsing passed.
- Scope boundary: Legacy possible_* fields, Python posterior APIs, belief-fork behavior, mechanics, observations, actions, transitions, features, checkpoints, live defaults, search, and training remain unchanged. ENV-001 remains separately blocked.
- Rollback: Remove the BeliefState module, fixture/tests, normative contract, and its documentation links; retain all accepted state/action/fixture/transition work and existing belief-fork behavior.

## ACTION-001 — CanonicalAction contract

- Status: Accepted (2026-09-23)
- Owner: Action owner
- Dependencies: STATE-001; `sim-core/src/action_codec.ts`; legacy live action handling
- Acceptance criteria: One versioned action identity, one slot convention, legal-action provenance, request-bound fail-closed validation, and lossless serialization/deserialization across TypeScript and Python.
- Tests: Shared parity corpus covering moves, tera, switches, non-contiguous bench slots, forced-switch, forced-default fallback, and legacy default; direct rejection tests for stale rqid, perspective, target, kind, slot, action ID, unavailable actions, malformed forced moves, wait/team-preview, and extra fields; additive canonical-ingress regression.
- Evidence: `npm test --prefix sim-core` 53/53 passed; relevant Python action/inference/parity set 20 passed with 2 documented skips; `git diff --check` passed; separate review `ACCEPT`.
- Scope boundary: Targeted moves, multi-active commands, pass, and skip remain out of v1 and are rejected or unrepresented rather than inferred.
- Rollback: Retain TypeScript action codec and raw-choice path; remove the canonical-action modules, fixtures/tests, contract, and additive `step_canonical` ingress without changing existing consumers.

## FIXTURE-001 — Protocol-prefix golden fixtures

- Status: Accepted (2026-09-23)
- Owner: Test owner
- Dependencies: STATE-001
- Acceptance criteria: Raw event prefixes and expected observations are versioned and cover decision-time cutoffs.
- Tests: Versioned request/decision prefixes, private request redaction, switch/replace, damage/healing, status/boost/faint, tera, transform/illusion, repeated species, non-contiguous slots, requestless terminal output, no-future-information pairs, and accepted/rejected exact-prefix extension.
- Evidence: `tests/fixtures/observable_state_v1.json`; `sim-core/tests/observable_state_fixture.test.ts`; full sim-core 55/55 passed; replay-independent Python 135 passed; separate review `ACCEPT`.
- Rollback: Remove only new fixtures and expected-output files.

## FIXTURE-002 — Python/TypeScript action parity fixtures

- Status: Accepted (2026-09-23)
- Owner: Test owner
- Dependencies: ACTION-001, STATE-001
- Acceptance criteria: Identical canonical actions, masks, labels, choices, and slots are produced for shared fixtures.
- Tests: Table-driven cross-runtime comparisons over complete 13-entry masks/action arrays, available indices, labels, choices, slots, deterministic IDs, byte-identical serialization, round trips, invalid slots, request binding, forced/default cases, and multi-action requests.
- Evidence: `tests/fixtures/canonical_action_v1.json`; focused TypeScript 4/4 and Python 4/4 passed; separate review `ACCEPT`.
- Rollback: Do not route production traffic through the adapter; retain fixtures for diagnosis.

## TRANS-001 — Seeded transition contract

- Status: Accepted (2026-09-23)
- Owner: Simulation owner
- Dependencies: STATE-001, FIXTURE-001
- Acceptance criteria: Explicit seed/RNG lineage, deterministic replay of identical serialized simulator snapshots and complete canonical joint actions, emitted events, branch identity, atomic request/action preflight, and a documented boundary to ObservableBattleState.
- Tests: Seeded snapshot fingerprint/branch repeatability; serialized-state restoration with exact post-transition replay; source/sibling branch isolation; stale/invalid/unavailable/wait/team-preview/forced-invalid and mixed-validity joint-action rejection with no state advance; legacy step and canonical-ingress regressions.
- Implementation slice: `sim-core/src/transition.ts`, additive `LocalBattleEnv.stepSeededTransition`, server-managed opaque snapshot handles in `EnvironmentManager`, and `capture_seeded_snapshot`/`step_seeded_transition` RPCs. Runtime timestamps are normalized only for fingerprints; raw logs remain emitted and the simulator revision is server-derived.
- Evidence: `tests/fixtures/seeded_transition_v1.json`; `sim-core/tests/transition.test.ts` 4/4 focused passed; `npm test --prefix sim-core` 59/59 passed; relevant Python suite 135 passed; `git diff --check` passed; separate review `ACCEPT`.
- Boundary evidence: RPC transport uses opaque server-managed snapshot handles, rejects raw `simulator_state`, derives the simulator revision server-side, validates snapshot lineage, and captures a non-empty ordered event delta with raw timestamps preserved.
- Rollback: Keep existing `sim-core` step/fork APIs and do not enable new transition adapter.

## DATA-001 — Dataset lineage and battle-level splits

- Status: Accepted (2026-09-23)
- Owner: Data owner
- Dependencies: STATE-001, BELIEF-001
- Acceptance criteria: Every example records battle/replay identity, observation cursor, source kind, private-data provenance, schema fingerprints, and battle-disjoint split membership.
- Implementation: `trainer/src/neural/dataset_lineage.py` defines the additive `dataset-record/v1` envelope, deterministic record IDs and serialization, source/private/schema lineage, exact prefix hash/cursor validation, battle/replay-disjoint collection validation, deterministic battle split assignment, and source-specific metric reporting. Public replay value/policy and live-private value builders emit lineage records and validate the complete collection before writing; legacy feature vectors and source labels remain unchanged.
- Contract and fixture: `docs/contracts/DATASET_LINEAGE.md` and `tests/fixtures/dataset_lineage_v1.json`. The fixture is synthetic and deterministic; no replay data was downloaded or generated as a claimed dataset.
- Tests: `trainer/tests/test_dataset_lineage.py` covers deterministic identity, malformed/unsupported records, future cursors, exact prefix hash mismatch, private-field exclusion, duplicate identities, battle/replay split collisions, deterministic split assignment, and source-specific metrics. Affected replay/private builder tests cover emitted lineage fields.
- Evidence: Separate read-only acceptance review `ACCEPT`; focused DATA/replay/private selection 21/21 passed; `npm test --prefix sim-core` 68/68 passed; `git diff --check` passed. Known baseline checkpoint-loading failures remain outside this slice: 194 passed, 10 skipped, 7 existing failures in `test_live_private_value.py`; no checkpoint or source workaround was made.
- Scope boundary: No replay acquisition, dataset download, training, live evaluation, feature-vector/model-input changes, checkpoint changes, search redesign, simulator changes, or ENV-001 changes. Legacy datasets remain read-only until migrated to complete envelopes.
- Rollback: Remove the additive lineage module, contract, fixture, tests, and builder metadata/validation; preserve legacy dataset outputs and disable only the new lineage-aware consumer.

## SEARCH-001 — Document current rollout/search semantics

- Status: Accepted (2026-09-23)
- Owner: Search owner
- Dependencies: STATE-001, TRANS-001, BELIEF-001
- Acceptance criteria: Exact, belief, and approximate rollout modes are explicitly distinguished with action enumeration, RNG, state-cloning, and feature-context semantics.
- Implementation: `docs/contracts/SEARCH_SEMANTICS.md` documents current legacy trace, exact replay, approximate, one-turn, and two-ply/belief behavior. It records that accepted ObservableBattleState, CanonicalAction, BeliefState, and seeded-transition interfaces are not current search inputs; search-level node identity, stale-action fail-closed behavior, and exact-prefix future-event isolation remain open constraints. No runtime path is changed.
- Tests: Existing trace/rollout behavior references were checked against `trainer/tests/test_sim_rollout.py`, `trainer/tests/test_two_ply_branch.py`, `trainer/tests/test_belief_branch.py`, the observable-state prefix fixture tests, transition tests, and BeliefState tests. `tests/fixtures/seeded_transition_v1.json` is identified as a separate TRANS-001 fixture, not search integration evidence.
- Evidence: Separate read-only acceptance review `ACCEPT`; `npm test --prefix sim-core` 68/68 passed; focused Python search suites 19 passed, 10 skipped; `git diff --check` passed. The skipped Python tests and known broader checkpoint-loading failures remain separate baseline issues.
- Scope boundary: Documentation-only. No search redesign, runtime integration, feature-vector/model-input changes, checkpoint changes, training, live evaluation, replay acquisition, simulator changes, accepted-contract edits, or ENV-001 changes.
- Rollback: Documentation-only; no runtime rollback required.

## SIM-COVERAGE-001 — Pinned simulator state and protocol coverage

- Status: Source audit and drift-check implementation complete with explicit
  gaps; not accepted as PIPELINE-001 or FEATURE-001 evidence by itself.
- Owner: Simulation owner.
- Dependencies: Pinned simulator metadata, accepted state/belief/action/
  transition contracts, and safe synthetic fixtures.
- Evidence: [`../contracts/SIMULATOR_COVERAGE.md`](../contracts/SIMULATOR_COVERAGE.md)
  and [`SIM-COVERAGE-001_PROGRESS.md`](SIM-COVERAGE-001_PROGRESS.md). Earlier
  2026-09-24 validation passed before the current protocol edits: build, 38
  targeted tests, manifest drift check, synthetic drift self-tests, and
  `git diff --check`. Subsequent joint-action, reporting, forced-switch and settling
  reviews are recorded in the coverage contract. Settling-review evidence: build,
  85 TypeScript and 20 Python tests; fresh 18 settling regressions and two review
  probes. At that review the expanded attestation, checker and six self-tests passed.
  Subsequent episode review accepts bounded orchestration, adds runner source/tests
  to hashing and attests the recomputed digest. Fresh build/17 runner regressions
  and two review probes pass; coverage checker and six self-tests passed then.
  Subsequent lifecycle review found Illusion alias/replace defects, now corrected
  in implementation pending review. Checker stops on digest and new -hint token
  classification drift; six self-tests pass. Helper and Illusion tests need hash-list
  inclusion, and raw-only hint inventory/classification needs review before attestation.
- Remaining limits: volatile lifecycle precision, side-condition expiry,
  three unknown aliases without established scoped semantics (now blocked at
  the pipeline boundary), and simulator source installation integrity against
  the package tarball. The reviewed digest does not imply blanket coverage.
- Rollback: Remove the audit manifest/checker/tests and documentation additions;
  preserve unrelated worktree changes and accepted contracts.

## PIPELINE-001 — Checkpoint-free transition integration

- Status: Accepted for the explicit v1 joint-actionable boundary scope on
  2026-09-24 review. This does not accept complete-episode collection.
- Owner: Simulation/data owners.
- Dependencies: SIM-COVERAGE-001 disposition and accepted STATE/ACTION/BELIEF/
  TRANSITION/DATA lineage contracts.
- Current evidence: `sim-core/src/pipeline_integration.ts`,
  `trainer/src/neural/pipeline_record.py`, and focused two-transition,
  both-perspective, successor-lineage, deterministic-identity, Python record
  validation, rejected-candidate, move-grammar, terminal-repeatability, and
  unknown-alias stopping tests. Fresh focused TypeScript validation on
  2026-09-24 passed 41/41; Python record/lineage tests passed 18/18. See
  [`PIPELINE-CORRECTNESS-2026-09-24-PROGRESS.md`](PIPELINE-CORRECTNESS-2026-09-24-PROGRESS.md).
- Acceptance evidence: source-backed move grammar; deterministic controller
  replay; no-publication diagnostics for unresolved aliases; supported raw-only
  and terminal protocol projection; Python record validation; and both natural
  and injected candidate rejection with exact committed state/lineage
  preservation. Fresh focused validation on 2026-09-24 passed 42 TypeScript
  tests and 18 Python tests. The scoped local-source coverage digest has a
  separate semantic-review attestation. See
  [`PIPELINE-CORRECTNESS-2026-09-24-PROGRESS.md`](PIPELINE-CORRECTNESS-2026-09-24-PROGRESS.md)
  and [`SIM-COVERAGE-001_PROGRESS.md`](SIM-COVERAGE-001_PROGRESS.md).
- Natural-rejection case: with simulator seed `[46, 101, 202, 303]`, the
  generated teams include p1 Dugtrio/Arena Trap and p2 Tinkaton/Steel. After
  both switch to those Pokémon, the request-derived p2 action set includes a
  switch while Showdown withholds the actual trap (`maybeTrapped`); choosing
  it passes pipeline preflight and is rejected by `Side.chooseSwitch`. The
  regression proves unchanged committed boundary/lineage and equality with a
  parallel control branch after the failure. The earlier 169-pair initial
  probe remains valid but did not reach this state.
- Review verdict: accept PIPELINE-001 within the format, legal-action, and
  joint-actionable boundaries above. This does not accept SIM-COVERAGE as a
  complete semantic inventory, PIPELINE-002 progression, FEATURE-001, dataset
  readiness, or product release.
- Not in scope: bulk collection, feature extraction, target/reward selection,
  training, checkpoint loading, replay acquisition, or live evaluation.
- Rollback: Remove only the additive candidate integration and bridge while
  retaining accepted lower-level contracts.

## PIPELINE-002 — Complete-episode boundary progression

- Current checkpoint (2026-09-25): bounded Topsy-Turvy inversion implemented in raw
  and TS/Python v2 stages; exact pre-filter grammar and publication alias rejection.
  Build79 relevant TS/28 Python pass, including28 new publications,232 rehashed grammar
  cases and4 false-stage cases. Next: separate semantic review, token classification
  and two-test coverage inclusion. Rigged Dice/other mechanics excluded; no attestation.
  Keep faithful_complete_episode:false; source hashes/evidence in current checkpoint.

- Status: Request-state reporting slice separately reviewed and accepted
  2026-09-24. Ordinary one-sided forced-switch slice separately accepted under
  additive schemas with expanded coverage attestation. Bounded settling separately
  reviewed and attested 2026-09-24. Bounded episode orchestration separately
  accepted and attested. Reproduced Illusion identity/replace failures are corrected
  in implementation; scoped lifecycle/Illusion/non-Stellar Tera corrections are accepted and attested; full-item/faithful
  publication acceptance remain open.
- Owner: Simulation/data owners.
- Dependencies: PIPELINE-001 joint-actionable acceptance recorded; relevant
  SIM-COVERAGE disposition below recorded, lifecycle implementation/review pending.
- Scope: one-sided forced switch, waiting, one-sided requestless, and
  both-sides requestless boundaries. Do not add this behavior implicitly to
  PIPELINE-001 or fabricate actions for a side without a current request.
- Acceptance criteria:
  1. Define each perspective's request state independently: actionable,
     forced switch, `wait=true`, absent/requestless, terminal; retain request
     ID, phase, and exact protocol cursor. Distinguish actionable-plus-waiting
     from actionable-plus-requestless.
  2. For one-sided forced switch, advance from only the actual pending request
     and its legal switch actions; prove the Showdown request-submission shape
     and exact successor request/lineage behavior for the other side.
  3. For waiting, wait for actual simulator progress or a new request. For
     requestless nonterminal states, specify which engine events settle the
     boundary and how a stable next request is recognized. No pass/default
     action may be synthesized.
  4. Preserve atomic candidate execution: unsupported, stale, rejected, or
     malformed progression leaves state fingerprint, prefix, snapshot, and
     observation/belief lineage unchanged.
  5. Add real simulator-produced regressions for each state class and relevant
     player combination, both perspectives, legal choices, successor prefixes,
     terminal completion, and truncation behavior. Synthetic classifier tests
     alone do not establish progression.
  6. Define complete versus truncated episode records for a future collector.
     A partial episode must carry battle identity, last committed cursor,
     boundary kind, stop code, and reason; it cannot be silently omitted or
     labeled terminal.
  7. Obtain a separate review of boundary semantics, supported scope, and the
     complete-episode/censoring policy.
- Current behavior: PIPELINE-001 v1 rejects these boundaries with explicit
  codes through legacy `step()`. Additive `stepForcedSwitch(action)` progresses
  ordinary forced-switch-plus-wait boundaries, producing actor-only records and
  both successor perspectives. Revival Blessing, forced-switch-plus-absence,
  general waiting/requestless progression remain unsupported and explicitly truncate
  in the accepted runner. Faithful complete-episode publication remains unaccepted.
- Disposition and exact first-task files/criteria:
  [PIPELINE-002-GAP-DISPOSITION-2026-09-24.md](PIPELINE-002-GAP-DISPOSITION-2026-09-24.md).
  Request-state reporting/classification is accepted within its reporting scope.
  Ordinary one-sided transition/action-record semantics are separately accepted.
  Bounded settling/stall handling is separately accepted. Remaining blockers include
  Revival Blessing's dropped `reviving` flag and incorrect switch
  targets (runner preflight explicitly truncates these requests). Versioned
  completed/truncated/failed outcomes and bounded rejection reselection are accepted
  as recorded below.
- Typed-state disposition: boost/volatile switch/faint clearing and Shed Tail
  transfer pass ordinary cases. Illusion identity/replace fixes now pass real probes;
  combined semantic review remains pending. Clearing itself does not drive simulation.
  Other switch/faint fields, linked-effect cleanup and broader transfers remain open.
  Private counters, single-turn typed reconstruction, and comprehensive
  side/field durations/layers remain deferred feature/reconstruction work.
  Unknown aliases retain fail-closed stops; other formats remain outside scope.
- Verified handoff: the natural regression is Dugtrio/Arena Trap versus
  Tinkaton with seed `[46,101,202,303]`; the stale Magnet Pull title is corrected.
- Reporting-review evidence: matching slice diff and checkpoint digest verified; reused
  passing build, focused TypeScript 53/53 (including environment, transition,
  pipeline/Python bridge) and Python record/lineage 18/18. No production fixes
  required. Added reviewed environment tests to coverage hashing; freshly ran
  coverage checker and all six self-tests successfully. Exact digest and scoped
  verdict are in the checkpoint. Legacy defaults and execution guards remain.
- New implementation evidence: build passed; focused TypeScript 67/67 and
  Python record/lineage 20/20. Real p2 KO and p1 U-turn replacements reproduce
  identities, validate actor-only Python records, update both beliefs and resume
  joint play. Candidate rejection/projection/metadata rollback and post-commit
  disposal retry are tested. Separate semantic review found no blocking defect;
  fresh 5 forced-switch and 20 Python tests pass. Added forced-switch regressions
  and Python validator/record tests to coverage hashing; recomputed/attested digest
  and scope are recorded in the dated coverage contract. At that review the checker
  and all six self-tests passed.
- Settling acceptance: source emission/delivery acknowledgements replace
  one-tick waits; 5,000 ms and 100,000-message defaults bound settling. Structured
  timeout/message-limit/error/EOF/cancellation failures release resources and
  discard candidates. Reused matching build/85 TypeScript/20 Python evidence;
  fresh 18 settling tests and two non-resetting-budget/late-output probes pass.
  No blocking findings/corrections. Added barrier source/tests to hashing;
  computed/attested digest, checker and all six self-tests pass.
- Episode acceptance: `pipeline-episode/v1` composes accepted transitions,
  owns/closes sessions, retains committed per-player records and final lineage,
  and distinguishes completed/truncated/failed. Defaults: 256 commits, 512 attempts,
  three rejections per boundary; retries exclude attempted current-request tuples.
  Real seed completion takes 55 commits; natural Arena Trap recovery and controlled
  stop/failure cases pass. Build, 102 TypeScript and 20 Python tests pass.
  Separate review found no blocking defect or correction; all three hashes matched.
  Fresh build/17 runner tests and exact terminal-limit/cancellation and tuple-exhaustion
  probes pass. Runner source/tests added to hashing; recomputed attestation, checker
  and six self-tests pass. Existing transition/Python schemas remain unchanged.
- State-correction implementation: extractor clears outgoing/fainted and re-entering
  boosts/volatiles, preserves permanent evidence/Illusion replace and the pinned
  Eternamax exception, and transfers only Substitute on Shed Tail switch evidence.
  Public occupancy and identity-based request merging handle early requests/party
  reorder; canonical self move IDs fix tested live/replay identity differences.
  Real constructed-team tests cover both actors, exact prefixes, privacy, restore,
  actor records and both beliefs. Build, 117 TypeScript and 20 Python tests pass.
- Lifecycle review: all five hashes match; fresh build/16 focused tests pass, with
  prior 117 TypeScript/20 Python evidence reused. Mirrored real Illusion probes find
  owner boosts/moves assigned to the bench disguise, divergent replay IDs and valid
  conditionless replace rejected. Synthetic same-name/extra-condition fixtures missed
  these gaps. Ordinary clearing/Shed Tail paths reviewed positively; slice not accepted.
- Illusion correction implementation: public appearances accumulate evidence separately
  from own request projection. Reveal restores the impersonated entry and reconciles
  evidence to the actual identity; neither earlier observations nor opponent privacy
  change. Conditionless replace is accepted with separate strict grammar; its public
  -hint is retained raw-only. Real both-actor ownership, repeated reveal, departure,
  faint, replay and Python publication regressions pass. Build, 126 TypeScript and
  20 Python tests pass, including prior clearing/Shed Tail/runner checks.
- Combined review: original Illusion blockers resolved in tested scopes, but fresh
  appearances discard public Tera on re-entry (`state_extractor.ts:406-448`). Mirrored
  real probes report opponent Normal/false despite explicit tera:Fire; own view stays
  Fire/true. Fresh build/43 focused tests pass; eight hashes match prior 126/20 evidence.
- Tera correction implementation: fresh switch/drag appearances use explicit public
  tera:TYPE before resolving types, without copying roster identity. Four new real
  cases cover either actor, both perspectives, untagged teammate isolation, disguised
  reveal, restoration, immutable prefixes, deterministic records/beliefs and Python
  record validation. Fresh build/130 TypeScript tests/diff checks pass; prior 20 Python
  tests reused. Original Snorlax reproduction now passes for both perspectives.
- Combined scoped review accepted ordinary clearing/Shed Tail, Illusion ownership/
  reveal, conditionless replace/raw-only hint and non-Stellar public Tera re-entry.
  All eight hashes match; 130 TS/prior 20 Python evidence reused, 29 focused tests
  refreshed including Python publication. Helper/Illusion tests added to 24-file hash
  list; hint and replace classifications reconciled. Computed/reviewed digest:
  3b777601e68932a409271b7103a0013b21abbfcc9d8c4f25c0fd118f2dcfc4e2. Checker and six self-tests pass.
- Faint Tera implementation: deactivates Tera, restores observable non-Tera typing,
  preserves known type, and prevents stale own requests from reasserting active Tera.
  Exact terminal restoration required terminal-only terminal-request-history/v1
  metadata in opaque snapshots. It retains addressed request history, creates no
  actions/log records, and rejects malformed/misaddressed metadata before reset.
- Parent build/134 relevant TS tests and delegated full157 pass; mirrored ordinary
  terminal and unrevealed Illusion KOs cover restoration, privacy, teammate/prefix
  preservation and deterministic Python-validated publication. Prior 20 Python tests
  reused. Four changed source/test files already hashed; manifest untouched.
- Review blocked: nested terminal history is unvalidated. Numeric ident/details/
  condition throw after the prior environment is destroyed; null entries and string
  stats are accepted as corrupt own state. Parent independently reproduced. Faint
  semantics and normal privacy/publication checks pass; no attestation issued.
- Terminal-history correction: recursively validates consumed fields and constructs
  minimal-v1 data before teardown; structured invalid/unsupported-schema errors.
  Historical raw-v1 data migrates by dropping extras and canonicalizing Tera markers;
  its fingerprint may change once. Missing metadata retains legacy limitations.
  Parent build136 relevant tests pass; original five probes reject without mutation;
  nested live-battle cases preserve state/branch and continue identically to a twin.
- Faint/minimal-v1 review accepted: recursive pre-teardown validation, structured
  errors, unchanged live-state/branch/continuation on rejection, private no-action
  restoration and deterministic/idempotent normalization. Migration changes require
  new references; old-reference/normalized-state mismatch rejects. No historical
  lineage rewrite. Timestamp-only test comparator fixed; no production changes.
  Reused136 TS/prior20 Python evidence; fresh build18 Illusion and3 coverage tests
  pass. All four files already hashed; checker/six self-tests pass. Attested digest:
  6aaddf2751640263f13fa29d4e95c1bfb0987bbf78e7274493a30b8126273c70.
- Stellar implementation (2026-09-25): shared resolveTypes excludes Stellar from
  replacement defensive typing while preserving Tera type/active flag. Both-actor
  source, switch/drag, reveal, ordinary/unrevealed faint, restoration and deterministic
  Python-publication tests pass; Fire behavior remains green. Parent build146 relevant
  tests and diff checks pass; focused Illusion28. No schema/privacy expansion.
- Stellar review accepted (2026-09-25): all three hashes match; pinned source and
  extractor/heuristic callers reviewed. Reused146 TS/28 Illusion/prior20 Python
  evidence; fresh build16 targeted lifecycle and3 coverage tests pass. Added
  battle_helpers.ts to25-file hashing; checker/six self-tests pass. Attested digest:
  4db82b9bc57984bf051f03b201bf022e0744ba03c8840239adeded5d362f33c3.
  Temporary-type and offensive Stellar mechanics excluded; faithful=false.
- Windows validation and selected macOS comparison subsequently passed at117df85;
  see platform checkpoints. Broader lifecycle fidelity remains open.
- Bounded bench revival accepted (2026-09-25): all14 hashes matched, no corrections.
  Reused154 TS/27 Python; fresh build/seven revival tests, seven Python rejection
  probes and two exact split-HP/status probes pass. Added canonical codecs/tests,
  identity fixture and revival tests to34-file hashing; -heal classification updated.
  Checker/ten self-tests/three coverage tests pass; attested digest:
  39ab09c90a564eaa80a3da3ff8275b8dcf01a7fbd79dcdece1b3945b68753ec8.
  Unsupported revival variants remain explicit; faithful_complete_episode:false.
  Next prerequisite: public temporary defensive typing, starting with Soak/typechange
  across request refresh and lifecycle/restoration; see checkpoint.
- Rollback: Keep v1's explicit fail-closed boundary behavior; remove only a
  separately reviewed PIPELINE-002 progression implementation if rejected.

## FEATURE-001 — Shared model feature contract

- Status: Unresolved; design and acceptance pending.
- Owner: Model/data owners.
- Dependencies: SIM-COVERAGE-001 and PIPELINE-001 acceptance, ENV-001
  reproducibility remediation, and explicit target/model-interface decisions.
- Acceptance criteria: Versioned collection/inference schema; ordered names,
  shape/dtype, normalization, missing-value and legal-mask behavior; public vs
  belief inputs, privacy regime, event cutoff, provenance, batching, fingerprint,
  unknown-schema and migration policy; focused no-leakage and compatibility
  tests. Dimensions from legacy/v7/v8 schemas are not carried forward by
  default.
- Not in scope until accepted: bulk extraction, dataset generation, target
  fields in the collector, training, and live model loading.
- Rollback: No runtime rollback is required for a design-only contract; retain
  the prior contracts and historical feature documentation.
