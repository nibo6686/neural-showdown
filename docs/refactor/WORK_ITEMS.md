# Refactor Work Items

All items are documentation/preparation work unless explicitly marked otherwise. No item authorizes production changes by itself.

| ID | Title | Status | Owner | Dependencies |
|---|---|---|---|---|
| CTRL-001 | Refactor control documents and baseline tag | In progress | Orchestrator | Review state, README |
| STATE-001 | ObservableBattleState contract | Accepted | State owner | CTRL-001, ENV-001, existing state schema |
| ENV-001 | Reproducible Python/Node validation environment | Blocked with remediation | Environment owner | CTRL-001, baseline tag |
| BELIEF-001 | BeliefState contract | Accepted | Belief owner | STATE-001, FIXTURE-001, TRANS-001 |
| ACTION-001 | CanonicalAction contract | Accepted | Action owner | STATE-001, existing action codec |
| FIXTURE-001 | Protocol-prefix golden fixtures | Accepted | Test owner | STATE-001 |
| FIXTURE-002 | Python/TypeScript action parity fixtures | Accepted | Test owner | ACTION-001, STATE-001 |
| TRANS-001 | Seeded transition contract | Accepted | Simulation owner | STATE-001, FIXTURE-001 |
| DATA-001 | Dataset lineage and battle-level splits | Accepted | Data owner | STATE-001, BELIEF-001 |
| SEARCH-001 | Document current rollout/search semantics | Accepted | Search owner | STATE-001, TRANS-001, BELIEF-001 |

## CTRL-001 — Refactor control documents and baseline tag

- Status: In progress
- Owner: Orchestrator
- Dependencies: Review state and README read; baseline branch/tag recorded
- Acceptance criteria: All requested documents exist; this registry is authoritative; aggregate state is updated only after synthesis; baseline and blockers are recorded.
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
- `ACTION-001` is unblocked but was not started in this checkpoint.

Validation dependencies: Python package environment with NumPy/pytest for Python tests; built `sim-core` and Node dependencies for TypeScript tests. No training, replay fetch, or server is required.

## ENV-001 — Reproducible Python/Node validation environment

- Status: Blocked with remediation (Node passes; Python has one missing-fixture failure)
- Owner: Environment owner
- Dependencies: CTRL-001; baseline branch/tag
- Acceptance criteria: Record supported Python and Node/npm versions; distinguish runtime and development dependencies; choose the supported dependency declaration/lock mechanism; document sim-core build steps; provide a clean-environment smoke test and exact focused-test commands; record platform-specific assumptions; verify the focused validation suite in a clean environment.
- Tests: Clean-environment dependency resolution; sim-core build check; focused
  Python test command; focused TypeScript test command; import/version smoke
  test. Current evidence: sim-core full suite 40/40 passed; focused
  state/env-manager suite 11/11 passed; replay-independent Python subset
  131/131 passed; replay-backed selection is marked and skips 2 tests when the
  raw fixture directory has no `.log` files. Python dependency declarations and
  lock/constraint policy remain unresolved.
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
