# Refactor Work Items

All items are documentation/preparation work unless explicitly marked otherwise. No item authorizes production changes by itself.

| ID | Title | Status | Owner | Dependencies |
|---|---|---|---|---|
| CTRL-001 | Refactor control documents and baseline tag | In progress | Orchestrator | Review state, README |
| STATE-001 | ObservableBattleState contract | Implemented pending review | State owner | CTRL-001, ENV-001, existing state schema |
| ENV-001 | Reproducible Python/Node validation environment | Blocked with remediation | Environment owner | CTRL-001, baseline tag |
| BELIEF-001 | BeliefState contract | Planned | Belief owner | STATE-001 |
| ACTION-001 | CanonicalAction contract | Blocked pending STATE-001 | Action owner | STATE-001, existing action codec |
| FIXTURE-001 | Protocol-prefix golden fixtures | Planned | Test owner | STATE-001 |
| FIXTURE-002 | Python/TypeScript action parity fixtures | Planned | Test owner | ACTION-001, STATE-001 |
| TRANS-001 | Seeded transition contract | Planned | Simulation owner | STATE-001, FIXTURE-001 |
| DATA-001 | Dataset lineage and battle-level splits | Planned | Data owner | STATE-001, BELIEF-001 |
| SEARCH-001 | Document current rollout/search semantics | Planned | Search owner | STATE-001, TRANS-001, BELIEF-001 |

## CTRL-001 — Refactor control documents and baseline tag

- Status: In progress
- Owner: Orchestrator
- Dependencies: Review state and README read; baseline branch/tag recorded
- Acceptance criteria: All requested documents exist; this registry is authoritative; aggregate state is updated only after synthesis; baseline and blockers are recorded.
- Tests: Documentation existence check, ID/reference check, `git diff -- docs` review.
- Rollback: Remove only newly created refactor documentation if the user rejects the preparation; preserve existing top-level docs and review state history.

## STATE-001 — ObservableBattleState contract

- Status: Implemented pending review
- Owner: State owner
- Dependencies: CTRL-001, ENV-001; `docs/state-schema.md`; `sim-core/src/types.ts`; `sim-core/src/state_extractor.ts`; `sim-core/src/env_manager.ts`.
- Acceptance criteria: Expand `docs/contracts/OBSERVABLE_STATE.md` into a normative versioned field schema with visibility classification, immutable-snapshot semantics, identity/cursor/hash rules, phase/request boundaries, source precedence, invalid-state behavior, and explicit mapping of `StepResult`, `BattleView`, and `ChoiceRequestView`.
- Tests: `sim-core/tests/observable_state.test.ts` covers deterministic prefix
  hashing, normalized-record cursors, immutability/future-event isolation,
  request-less redaction, perspective/request consistency, contradictions, and
  unsupported schemas. Full sim-core validation is 40/40 passed.
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
The adapter exposes raw protocol-prefix evidence plus an immutable observation
snapshot with explicit provenance; it remains shadow-only.

Tests and golden fixtures: request-prefix fixtures, switch/replace, damage/status/faint, tera/transform/illusion, perspective redaction, event-cursor monotonicity, and rejection of future events.

Rollback: remove the adapter/schema and its tests while leaving the existing state extractor and feature paths intact.

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

- Status: Planned
- Owner: Belief owner
- Dependencies: STATE-001; `sim-core/src/belief_fork.ts`; live belief builders
- Acceptance criteria: Separate hypotheses from observations; record source, constraints, weights, seed, and impossible-state diagnostics.
- Tests: Public-information invariance; hidden-state redaction; deterministic belief sampling; impossible-state rejection.
- Rollback: Disable the new belief adapter and retain existing research forks.

## ACTION-001 — CanonicalAction contract

- Status: Blocked pending STATE-001
- Owner: Action owner
- Dependencies: STATE-001; `sim-core/src/action_codec.ts`; legacy live action handling
- Acceptance criteria: One action identity, one slot convention, legal-action provenance, and lossless serialization/deserialization across TypeScript and Python.
- Tests: Force-switch, trapped, disabled, zero-PP, tera, and non-contiguous bench-slot parity fixtures.
- Rollback: Retain TypeScript action codec as the runtime authority and disable new Python adapter use.

## FIXTURE-001 — Protocol-prefix golden fixtures

- Status: Planned
- Owner: Test owner
- Dependencies: STATE-001
- Acceptance criteria: Raw event prefixes and expected observations are versioned and cover decision-time cutoffs.
- Tests: Prefix truncation, no-future-information, repeated species, transform/illusion, tera, status, damage, faint, and request ordering.
- Rollback: Remove only new fixtures and expected-output files.

## FIXTURE-002 — Python/TypeScript action parity fixtures

- Status: Planned
- Owner: Test owner
- Dependencies: ACTION-001, STATE-001
- Acceptance criteria: Identical canonical actions, masks, labels, choices, and slots are produced for shared fixtures.
- Tests: Table-driven cross-runtime comparisons.
- Rollback: Do not route production traffic through the adapter; retain fixtures for diagnosis.

## TRANS-001 — Seeded transition contract

- Status: Planned
- Owner: Simulation owner
- Dependencies: STATE-001, FIXTURE-001
- Acceptance criteria: Explicit seed/RNG lineage, deterministic replay of identical full states and joint actions, emitted events, and branch identity.
- Tests: Seed repeatability, branch isolation, action legality, returned-state/feature alignment.
- Rollback: Keep existing `sim-core` step/fork APIs and do not enable new transition adapter.

## DATA-001 — Dataset lineage and battle-level splits

- Status: Planned
- Owner: Data owner
- Dependencies: STATE-001, BELIEF-001
- Acceptance criteria: Every example records battle/replay identity, observation cursor, source kind, private-data provenance, schema fingerprints, and battle-disjoint split membership.
- Tests: Split collision rejection, prefix leakage checks, source-specific metric reports.
- Rollback: Preserve old datasets as read-only artifacts and disable new dataset consumer.

## SEARCH-001 — Document current rollout/search semantics

- Status: Planned
- Owner: Search owner
- Dependencies: STATE-001, TRANS-001, BELIEF-001
- Acceptance criteria: Exact, belief, and approximate rollout modes are explicitly distinguished with action enumeration, RNG, state-cloning, and feature-context semantics.
- Tests: Documentation examples checked against existing trace/rollout behavior; seeded branch fixture references.
- Rollback: Documentation-only; no runtime rollback required.
