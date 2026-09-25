# Codex Review State

> **Current status index:** This file is an append-only review history. Earlier
> “blocked”, “not started”, or readiness statements describe their dated
> checkpoints and may be superseded by later sections. The current project gate
> summary is [`PROJECT_STATUS.md`](PROJECT_STATUS.md); the latest review entry is
> at the end of this file.

## 1. Findings H1-H5 and M1-M8

### H1. Legacy live inference permits schema-mismatched models to run

The legacy live path:

- Loads some model state dictionaries with `strict=False`.
- Pads or truncates state/action feature vectors to fit checkpoint dimensions.
- Accepts multiple feature versions.
- Does not require schema fingerprints for the legacy action ranker.

This can produce numerically valid but semantically incorrect inference.

Evidence:

- `trainer/src/neural/live_eval_server.py:674`
- `trainer/src/neural/live_eval_server.py:681`
- `trainer/src/neural/live_eval_server.py:917`
- `trainer/src/neural/live_action_recommender.py:68`
- `trainer/src/neural/live_action_recommender.py:611`

The vNext path explicitly forbids this, creating an unsafe difference between experimental and default inference.

### H2. Live legal-action handling trusts caller-supplied actions too much

When `payload.legal_actions` is supplied, the legacy recommender uses those actions directly. This bypasses parts of the independently derived request logic, including force-switch and trapped-state handling.

Evidence:

- Raw payload actions are selected first: `trainer/src/neural/live_action_recommender.py:193`
- Force-switch/trapped handling is only applied in the generated-candidate branch: `trainer/src/neural/live_action_recommender.py:211`
- Disabled actions are masked later rather than fully revalidated against the simulator/request state: `trainer/src/neural/live_action_recommender.py:591`

There is also a slot-convention risk: simulator action encoding uses one-based switch slots, while legacy live request enumeration can produce zero-based positions. The parity gate explicitly lists slot-index validation as unfinished.

Evidence:

- `sim-core/src/action_codec.ts:39`
- `trainer/src/neural/live_action_recommender.py:155`
- `artifacts/training_plan/diagnostic_training_gate.md:47`

### H3. Offline validation can be optimistic because splits are not battle-level

The replay value model uses row-level random splitting. A replay produces many correlated turn rows, so turns from the same battle can appear in both training and validation.

The action ranker splits decision groups, but those groups are created per decision and are not grouped by replay ID. The same replay can therefore contribute decisions to both sets.

Evidence:

- Value row split: `trainer/src/neural/train_value.py:35`
- Action decision-group creation: `trainer/src/neural/build_action_rank_dataset.py:280`
- Action split by group count only: `trainer/src/neural/train_action_ranker.py:323`
- Replay IDs are stored as metadata rather than used as the split key: `trainer/src/neural/build_action_rank_dataset.py:287`

The vNext diagnostic validator improves this by rejecting replay IDs that span splits:

- `trainer/src/neural/train_vnext_diagnostic.py:404`

That protection is not consistently applied to legacy pipelines.

### H4. Missing live-private checkpoints can silently activate the wrong model

The live-private loader falls back to the older public replay value model when the configured live-private checkpoint is missing, unless strict startup mode is explicitly enabled.

Evidence:

- `trainer/src/neural/live_eval_server.py:718`
- `trainer/src/neural/live_eval_server.py:762`
- Strict validation is opt-in: `trainer/src/neural/live_eval_server.py:523`

This can make a live evaluation appear healthy while using a model trained for a different information regime.

### H5. The live endpoint can expose private-state diagnostics and accept unbounded payloads

The request includes arbitrary-length logs, raw request dictionaries, URLs, and legal-action lists. The response can include private state, inferred beliefs, feature diagnostics, and action estimates.

Evidence:

- Broad request fields: `trainer/src/neural/live_eval_server.py:78`
- Private/debug response content: `trainer/src/neural/live_eval_server.py:1122`
- Capture/logging paths: `trainer/src/neural/live_eval_server.py:236`
- Action trace includes request metadata: `trainer/src/neural/action_trace.py:173`

The server defaults to localhost, which reduces exposure, but CORS and bind settings are configurable.

### M1. Replay-derived and private-data sources are combined without a hard evaluation boundary

The live-private dataset combines reconstructed public replay examples and locally generated private examples. Source kinds are recorded, but the training split is still random across rows.

Evidence:

- Combined example generation: `trainer/src/neural/build_live_private_value_dataset.py:859`
- Source metadata: `trainer/src/neural/build_live_private_value_dataset.py:920`
- Random split: `trainer/src/neural/train_live_private_value.py:50`

This creates a distribution-shift and evaluation-interpretation problem even when the reconstructed private state is logically valid for the acting player.

### M2. Fallbacks are broad and often silent

Simulator rollout exceptions are caught and converted to empty simulation results. Calibrated value failures fall back to legacy display behavior.

Evidence:

- Rollout exception handling: `trainer/src/neural/live_action_recommender.py:753`
- Calibration fallback: `trainer/src/neural/live_eval_server.py:1047`

This improves availability but weakens observability and makes degraded inference difficult to distinguish from normal inference.

### M3. Feature and action logic is duplicated across runtime, training, simulator, and vNext code

Candidate construction and action-slot semantics exist in multiple places:

- TypeScript action codec
- Legacy live recommender
- Dataset builders
- vNext shadow path
- Browser overlay integration

This creates hidden coupling and makes parity regressions likely.

Evidence:

- TypeScript action encoding: `sim-core/src/action_codec.ts:96`
- Legacy live candidates: `trainer/src/neural/live_action_recommender.py:135`
- Dataset candidates: `trainer/src/neural/build_action_rank_dataset.py:200`
- vNext candidates: `trainer/src/neural/vnext_live_shadow.py:89`

### M4. Python environment reproducibility is incomplete

`trainer/pyproject.toml` declares package metadata but no runtime dependencies. There is no evident Python lockfile or explicit Python-version environment file.

Evidence:

- `trainer/pyproject.toml:1`
- README prerequisite assumptions: `README.md:65`

The TypeScript side is better pinned, but its package uses semver ranges for development dependencies.

### M5. Seed handling is inconsistent across training and data generation

Some training paths use fixed split seeds, while vNext explicitly seeds Python, NumPy, Torch, and CUDA. Other code uses global randomness for trace sampling or data-loader order.

Evidence:

- Basic value split seed: `trainer/src/neural/train_value.py:46`
- vNext comprehensive seeding: `trainer/src/neural/train_vnext_diagnostic.py:902`
- Runtime/random trace behavior: `trainer/src/neural/eval.py:421`

### M6. Runtime latency measurement is stronger in vNext than in the default live path

The vNext dry-run records state feature generation, action feature generation, simulator impact, scoring, and serialization timings. The default live path does not expose an equivalent complete latency breakdown.

Evidence:

- vNext timing instrumentation: `trainer/src/neural/vnext_live_shadow.py:153`
- README acknowledges unresolved live timing/latency work: `README.md:543`
- Gate still lists latency and real-room validation work: `artifacts/training_plan/diagnostic_training_gate.md:47`

### M7. CORS and tracing configuration can broaden data exposure

Default CORS is constrained, but credentials are enabled, all methods/headers are allowed, and environment variables can override origins or regex behavior.

Evidence:

- `trainer/src/neural/live_eval_server.py:97`
- `trainer/src/neural/live_eval_server.py:126`
- Simulator tracing can log seeds and choices: `sim-core/src/server.ts:107`

### M8. Runtime RPC parsing relies on type assertions rather than full schema validation

The Node service parses JSON and casts it to the expected request type before dispatch. Malformed requests are handled as errors, but there is no comprehensive runtime schema validation layer.

Evidence:

- `sim-core/src/server.ts:324`
- `sim-core/src/server.ts:223`

## 2. Files already inspected

- `README.md`
- `.gitignore`
- `trainer/pyproject.toml`
- `sim-core/package.json`
- `sim-core/package-lock.json`
- `sim-core/tsconfig.json`
- `scripts/run_windows.ps1`
- `Showdown Local Eval Overlay.user.js`
- `trainer/src/neural/env_client.py`
- `sim-core/src/server.ts`
- `sim-core/src/env_manager.ts`
- `sim-core/src/state_extractor.ts`
- `sim-core/src/types.ts`
- `sim-core/src/action_codec.ts`
- `trainer/src/neural/live_eval_server.py`
- `trainer/src/neural/live_action_recommender.py`
- `trainer/src/neural/live_private_features.py`
- `trainer/src/neural/action_features.py`
- `trainer/src/neural/vnext_inference.py`
- `trainer/src/neural/vnext_live_shadow.py`
- `trainer/src/neural/train_vnext_diagnostic.py`
- `trainer/src/neural/build_dataset.py`
- `trainer/src/neural/train_bc.py`
- `trainer/src/neural/build_value_dataset.py`
- `trainer/src/neural/train_value.py`
- `trainer/src/neural/replay_fetch.py`
- `trainer/src/neural/parse_replay_logs.py`
- `trainer/src/neural/build_replay_value_dataset.py`
- `trainer/src/neural/build_live_private_value_dataset.py`
- `trainer/src/neural/train_live_private_value.py`
- `trainer/src/neural/build_action_rank_dataset.py`
- `trainer/src/neural/train_action_ranker.py`
- `trainer/src/neural/train_action_value_ranker.py`
- `trainer/src/neural/eval.py`
- `trainer/src/neural/action_trace.py`
- `trainer/tests/test_vnext_live_shadow.py`
- `trainer/tests/test_vnext_inference.py`
- `trainer/tests/test_live_eval_calibration.py`
- `trainer/tests/test_live_eval_capture.py`
- `trainer/tests/test_sim_rollout_integration.py`
- `artifacts/training_plan/diagnostic_training_gate.md`
- `artifacts/training_plan/diagnostic_1000_action_rank_training_report.md`

Repository inventories were also inspected for top-level directories, Python/TypeScript source modules, tests, configs, docs, data locations, checkpoints, and generated artifacts. No dataset or checkpoint contents were loaded.

## 3. Commands already run

- `git status --short`
- `rg --files`
- `rg --files trainer/tests -g 'test_*.py'`
- `rg --files sim-core/tests`
- Targeted `rg -n` searches for repository structure, entry points, README claims, model/feature versions, data builders, train/validation split logic, live evaluation, vNext controls, simulator action handling, tests, environment variables, subprocess usage, CORS, logging, and secret-like filenames/patterns.
- Read-only source and documentation excerpts using line-oriented shell output.
- Read-only existence checks for README-referenced generated paths, checkpoints, datasets, build output, and virtual environments.

No tests, training, servers, package installation, network calls, replay downloads, dataset loading, or checkpoint loading were run.

## 4. Confirmed facts

- The project combines Python ML tooling with a TypeScript/Node simulator service.
- Python communicates with sim-core through newline-delimited JSON over a local subprocess stdin/stdout channel.
- The simulator defines a 13-slot fixed policy action space.
- The live server provides `/evaluate`, defaults to localhost binding, and the browser overlay is recommendation-only.
- The default live path and vNext dry-run path are separate; vNext is default-off and does not submit commands to Showdown.
- vNext enforces exact dimensions, schema versions, fingerprints, and strict checkpoint state loading.
- Legacy live inference permits feature adaptation by padding/truncation and has weaker checkpoint compatibility validation.
- Replay-derived, local-private, public, behavior-cloning, action-ranker, action-value-ranker, PPO, calibration, and vNext diagnostic tracks exist in the codebase.
- The vNext diagnostic validator rejects replay IDs that cross train/validation splits; equivalent protection was not confirmed for legacy pipelines.
- Generated data and many artifacts are ignored by `.gitignore`, although some checkpoints and reports are present in the checkout.
- The inspected working tree was clean at the time of review.
- No obvious secret-bearing filenames or source-code secret patterns were found in the scanned repository paths; no secret values were inspected or printed.

## 5. Unverified hypotheses

- Row-level and decision-level legacy splits may inflate validation metrics because replay/battle identity is not consistently the split boundary.
- Caller-supplied live legal actions may disagree with canonical simulator legality in force-switch, trapped, zero-PP, disabled-move, or switch-slot cases.
- Silent feature padding/truncation may permit semantically incompatible checkpoints to return plausible scores.
- The live-private reconstruction pipeline may need a dedicated future-information audit for earlier-turn feature construction.
- Default live fallback behavior may be intentional availability behavior rather than an accidental safety gap.

## 6A. Battle-state / protocol / simulation architecture review — 2026-09-22

### Scope and method

- Continued from this file; did not repeat the repository inventory or H1-H5/M1-M8 review.
- No source changes, tests, training, package installation, replay fetching, checkpoint loading, or server startup.
- One narrow delegated pass covered canonical state modeling. The remaining protocol, simulation, action-contract, and dataset-safety scopes were inspected directly.

### Confirmed architectural facts

- `sim-core` keeps authoritative Showdown `Battle` state internally and can serialize/restore it, but its exposed `BattleView` is a repository-specific view rather than a shared canonical schema.
- `BattleView` can include `possible_*` hypothesis fields, so it is not a pure observation contract unless those fields are separated or explicitly marked as belief-derived.
- Python contains several independently reconstructed representations: raw protocol trajectories, request-derived private state, tactical state, and live belief/features. There is no enforced `Authoritative -> Observable -> Belief -> Features` pipeline.
- Replay parsing retains raw protocol lines and normalized events, but event attribution is current-turn based and lacks a shared event cursor/observation identity. The action-rank dataset deliberately uses `turn - 1` context; the replay-value dataset applies all events in a turn before featurizing, which is appropriate only if the example means post-turn state.
- TypeScript action encoding is the strongest canonical candidate: fixed 13-slot indexes, explicit move/tera/switch kinds, and one-based team slots. Python legacy action generation and caller-supplied actions can use different slot conventions and bypass independent legality checks.
- Exact branch simulation uses seeded Showdown mechanics and can reproduce a state by replaying from the beginning. Belief forks rewrite hidden opponent sets from an internal serialized state and are distinct from exact cloning. Approximate rollouts use abstract opponent classes/noise and are not full battle transitions.
- A seeded exact transition is close to reproducible when explicit seeds and deterministic choices are used, but global `Math.random`, process-dependent Python `hash()` seeding, limited opponent-action enumeration, and feature evaluation against trace context weaken reproducibility/parity guarantees.

### Architecture conclusion

The recommended direction is a dedicated battle-state/search layer around the existing Showdown-backed simulator. First preserve the current mechanics engine and improve its wrapper with golden fixtures; then enforce separate `ObservationSnapshot`, `BeliefState`, canonical `ActionId`, and seeded `TransitionResult` contracts. Treat replacing or supplementing the engine as a later differential-validation/performance decision, not the first architectural move.

### Required next checks

- Add protocol-prefix golden fixtures proving no future event enters an earlier observation, including switch/replace, transform/illusion, tera, status, damage, faint, and request boundaries.
- Add TS/Python action round-trip and legality-parity fixtures, especially force-switch, trapped, zero-PP, disabled moves, and switch-slot numbering.
- Add seeded exact-transition fixtures and compare returned branch views/features rather than reusing the original trace view/request.
- Define shared identity/provenance metadata: battle/replay ID, observation ID, event cursor, turn/phase/rqid, perspective, source kind, protocol-prefix hash, schema fingerprints, simulator revision, belief source/seed, and RNG lineage.
- Build a boundary audit that rejects hidden simulator fields, hypotheses, post-cutoff events, and private-state provenance mislabeled as exact observations.

## 6. Validation pass — 2026-09-22

### H1/H4 — checkpoint compatibility and fallback

Confirmed:

- Legacy policy/value loading constructs a model from checkpoint metadata and calls `load_state_dict(..., strict=False)` at `trainer/src/neural/live_eval_server.py:653-678`.
- Live-private validation checks only the declared input dimension and feature version at `trainer/src/neural/live_eval_server.py:681-695`; it does not make state-dict loading strict or validate a schema fingerprint.
- Legacy policy feature adaptation silently truncates or zero-pads unexpected dimensions at `trainer/src/neural/live_eval_server.py:917-933` and `trainer/src/neural/live_action_recommender.py:412-428`.
- The action ranker also uses `strict=False` and pads/truncates state and action vectors at `trainer/src/neural/live_action_recommender.py:63-79` and `580-625`.
- Strict startup validation is real but opt-in: `trainer/src/neural/live_eval_server.py:523-604` only enforces the stronger live-private/action-ranker checks when `NEURAL_STRICT_LIVE_EVAL` is enabled.
- If the live-private checkpoint is absent, the default loader falls back to `OLD_VALUE_MODEL_PATH` and labels the result as `public-replay-value` at `trainer/src/neural/live_eval_server.py:739-773`. The fallback reason is returned, but service health is not made fatal by default.

Assessment: H1 and H4 are confirmed for the default legacy path. The prior wording should distinguish observable fallback metadata from fail-closed startup behavior.

### H2 — legal-action generation and parity

Confirmed:

- When `payload.legal_actions` is nonempty, `trainer/src/neural/live_action_recommender.py:193-203` normalizes and trusts it directly; force-switch and trapped-state logic at `:206-209` is only applied when the caller supplies no actions.
- Caller-provided `disabled` values are carried into candidates at `:167-190` and later used for masking/scoring, rather than being independently recomputed from canonical request/simulator state.
- Python legacy switch candidates use the original enumerated team slot and a zero-based `slot` field at `trainer/src/neural/live_action_recommender.py:135-164`.
- TypeScript canonical actions normalize team slots to one-based values and assign switch action indices from the filtered bench order at `sim-core/src/action_codec.ts:39-55`; move slots are also explicitly one-based at `:119-140`.

Assessment: H2 is confirmed as a parity/trust-boundary risk. Exact disagreement cases still require table-driven tests for force-switch, trapped, fainted/disabled moves, and bench-slot gaps.

### H3/M1 — dataset provenance and metric validity

Delegated read-only validation confirmed:

- Legacy value and live-private trainers use deterministic row-level random splits (`trainer/src/neural/train_value.py:39-48`; `train_live_private_value.py:50-57`), without replay/battle IDs in the loaded arrays.
- Action-ranker training splits decision groups, not replay groups (`trainer/src/neural/train_action_ranker.py:40-47`, `322-328`). `build_action_rank_dataset.py:285-318` persists replay IDs only when debug fields are enabled.
- Live-private builders generate both perspectives and many turns per replay (`build_live_private_value_dataset.py:633-687`); default stacked arrays omit source IDs (`:816-838`).
- Legacy value calibration is computed over predictions for all rows, including training rows (`train_value.py:167-168`), so those calibration figures are in-sample.
- vNext does enforce replay-disjoint state splits (`train_vnext_diagnostic.py:404-414`) and tests collision rejection, but its multi-objective best-checkpoint logic may report value and rank metrics from different improvements (`:1264-1279`, `:1359-1363`).

Assessment: H3 and M1 are confirmed. The legacy calibration issue is an additional high-severity metric-validity finding. Actual leakage magnitude remains unknown without loading datasets.

### H5/M2/M6/M7 — HTTP exposure and observability

Confirmed:

- `EvalRequest` accepts unbounded `log` and `legal_actions` lists and an unrestricted request dictionary at `trainer/src/neural/live_eval_server.py:78-95`; no length, item-count, or body-size limits are defined in this module.
- The normal response includes private state, inferred opponent beliefs, all action estimates, model paths, and trace material under `debug` at `trainer/src/neural/live_eval_server.py:1099-1143`.
- Optional capture is sanitized, opt-in, and capped/deduplicated at `:1278-1301`; optional eval logging is compact and excludes the private request at `:1146-1186`. These mitigations do not remove the private/debug response exposure.
- Action traces persist room/player/turn/URL identifiers and bundle metadata when enabled at `trainer/src/neural/action_trace.py:173-204`.
- CORS allows credentials, all methods, and all headers, with origins/regex configurable through environment variables at `trainer/src/neural/live_eval_server.py:97-126`.
- vNext has detailed latency timings, while the legacy live server has no equivalent `perf_counter`/latency breakdown (`vnext_live_shadow.py:163-296`; no corresponding timings in `live_eval_server.py`).
- Rollout failures are converted into degraded/empty results in `live_action_recommender.py:753` and calibration failures fall back at `live_eval_server.py:1047`; the response has warning/fallback fields, but no uniform counter or latency/degradation metric was confirmed.

Assessment: H5, M2, M6, and M7 are confirmed as exposure/observability concerns, with opt-in sanitized capture and explicit response warnings as partial mitigations.

### M4/M5/M8 — reproducibility and RPC validation

Confirmed:

- `trainer/pyproject.toml:1-15` declares no runtime dependencies and no Python lockfile/environment metadata was identified in the reviewed scope.
- Legacy trainers use fixed local split RNGs (`train_value.py:45`; `train_live_private_value.py:52`; action ranker `:42`), but runtime trace sampling uses global `random.random()` at `trainer/src/neural/eval.py:421`; vNext explicitly seeds Python, NumPy, Torch, and CUDA at `train_vnext_diagnostic.py:902-907`.
- Node RPC parses JSON and casts it directly to `RPCRequest` at `sim-core/src/server.ts:323-327`; dispatch then trusts the asserted shape at `:223-251`. Invalid JSON is handled, but comprehensive runtime schema validation is absent.
- Node responses do include queue and server elapsed timing metadata at `sim-core/src/server.ts:338-380`, so M6 is specifically a default Python/live-path observability gap, not a total simulator timing gap.

Assessment: M4, M5, and M8 are confirmed in the reviewed scope.

### Focused test attempts

- `python -m pytest ...` could not start because the `python` command is absent.
- `python3 -m pytest ...` could not start because `pytest` is not installed.
- Direct `unittest` attempts for `test_live_eval_capture.py`, `test_live_eval_calibration.py`, `test_vnext_inference.py`, and `test_vnext_live_shadow.py` could not import because `numpy` is not installed.
- The compiled Node action-codec test was not run because `sim-core/dist/tests/action_codec.test.js` is absent; no build was performed.

No code, datasets, checkpoints, servers, or external resources were modified or loaded during this pass. The delegated investigator used the requested read-only H3/M1 scope and returned within the word limit; effective subagent model metadata was not exposed after spawn.

## 7. Recommended next checks

- Add fail-closed tests for legacy checkpoint state-dict/schema mismatches and missing live-private checkpoints under default configuration.
- Add table-driven Python/TypeScript action-parity tests covering force-switch, trapped states, disabled/zero-PP moves, and non-contiguous bench slots.
- Persist replay/battle IDs by default and split before row/decision expansion; change legacy calibration reporting to validation-only.
- Add request-size limits and a production-safe response mode that excludes private/debug data unless explicitly authorized.
- Add structured fallback counters and complete default-path latency fields.
- Add runtime RPC schema validation and a declared/locked Python dependency set.
- Mixed replay-reconstructed and local-private training sources may reduce real live performance despite acceptable aggregate offline metrics.
- CORS overrides, tracing, and capture paths may be used differently in actual deployments than their defaults indicate.
- README-referenced absent artifacts may be intentionally excluded generated outputs rather than broken commands.

## 8. Next validation tasks

1. Inspect and, if authorized, run focused schema-compatibility tests that inject feature dimension, version, fingerprint, and state-dictionary mismatches into legacy live loaders.
2. Build golden legal-action fixtures covering forced switches, trapping, disabled moves, zero PP, Terastallization, and one-based versus zero-based switch slots; compare simulator, dataset, legacy live, and vNext outputs.
3. Inspect dataset metadata only and verify whether every legacy train/validation split is battle/replay-disjoint.
4. Audit reconstructed private-state generation for information that is unavailable at the represented prefix turn.
5. Compare source-specific live-private performance for replay-reconstructed versus local-private examples.
6. Exercise error paths in a controlled test environment to verify that rollout, calibration, and checkpoint fallbacks are visible in structured output.
7. Measure default live endpoint latency as separate stages: request parsing, public/private feature generation, simulator work, model scoring, masking/ranking, and serialization.
8. Verify whether legacy live checkpoints carry enough metadata to enforce schema fingerprints and provenance.
9. Inspect promotion/rollback operational documentation and identify the authoritative approved-checkpoint manifest, if one exists outside the current checkout.
10. Reconcile README commands, test names, model versions, generated artifact paths, and current diagnostic status with a versioned status table.

## 9. Subagent summaries

The prior inventory/README-review used one read-only subagent. This validation pass used one additional narrow read-only H3/M1 subagent; the orchestrator handled the other scopes and was the only writer.

Summary:

- Verified the Python-plus-TypeScript hybrid architecture, NDJSON RPC protocol, fixed 13-slot action space, `/evaluate` endpoint, localhost default bind, recommendation-only overlay, launcher actions, and vNext default-off isolation.
- Identified README drift around the claimed current v7/v5 diagnostic track: later v7/v7 and v8 feature/diagnostic work exists, and several README-referenced generated dataset/checkpoint paths were absent from the checkout.
- Verified that README-reported vNext metrics and closed-gate statements correspond to archived repository reports, but recommended labeling them with the associated schema/dataset/checkpoint version.
- Found that `sim-core/dist`, `node_modules`, and the Python virtual environment were absent in the checkout, so README prerequisites should distinguish generated build outputs from committed source.
- Found that the README references `trainer/tests/test_live_eval_payload.py`, which was not present in the inspected test inventory.
- Did not modify files, run tests, start services, fetch data, or inspect dataset/checkpoint contents.

## 10. Documentation readiness gate — 2026-09-22

### Result

- Historical documentation-preparation gate: `READY_FOR_REFACTOR: YES` (this
  did not mean dataset, training, or live-model readiness).
- Created the requested documentation tree under `docs/refactor`, `docs/contracts`, `docs/testing`, `docs/data`, and `docs/models`.
- Verified all 15 requested files exist.
- Verified `CTRL-001`, `STATE-001`, `BELIEF-001`, `ACTION-001`, `FIXTURE-001`, `FIXTURE-002`, `TRANS-001`, `DATA-001`, and `SEARCH-001` are present.
- Verified every work item contains status, owner, dependencies, acceptance criteria, tests, and rollback.
- Verified documentation links and referenced existing schema/architecture targets.
- Existing top-level files `docs/action-space.md`, `docs/architecture.md`, `docs/state-schema.md`, and `docs/implement-item.md` were not changed by this phase. The latter and this state file remain pre-existing untracked documentation artifacts.
- Baseline recorded as branch `main`, tag `v1-live-eval-51-gc4477b6`, commit `c4477b6151885b35847da71110729867d9e48d5d`.
- Environment blockers recorded: missing Python/pytest/NumPy and absent `sim-core/dist`/`node_modules`; no installation or build was attempted.

### STATE-001 preparation status

STATE-001 was prepared for review and has now been reviewed. Its exact source files, smallest safe change, golden fixtures, tests, rollback plan, and validation dependencies are recorded in `docs/refactor/WORK_ITEMS.md`. It requires contract expansion and ENV-001 before implementation; `ACTION-001` remains blocked.

## 11. STATE-001 contract review — 2026-09-22

### Verdict

`ACCEPT WITH REQUIRED CHANGES`.

The proposed observation boundary is directionally consistent with the current architecture and can be introduced additively, but `docs/contracts/OBSERVABLE_STATE.md` is still a placeholder and is not implementation-ready.

### Confirmed alignment

- It is separate in intent from authoritative Showdown `Battle` serialization; `BattleView` and `ChoiceRequestView` are already player-specific projections.
- It correctly requires public/acting-player-private separation, perspective, raw-event lineage, identity fields, and exclusion of simulator-only state.
- It can be introduced without changing mechanics, checkpoints, feature values, or live defaults if first implemented as an additive adapter and shadow-tested.

### Required contract changes

- Define a normative versioned field-level schema: types, nullability, nesting, enums, canonical serialization, and fingerprint.
- Explicitly map or distinguish every relevant `StepResult`, `BattleView`, and `ChoiceRequestView` field.
- Remove or relocate hypothesis fields such as `possible_roles`, `possible_moves`, `possible_abilities`, and `possible_tera_types`; do not treat `status_source: inferred` or inferred values as exact observation data.
- Define immutable snapshot semantics, source precedence when request/protocol/simulator views disagree, and error behavior for malformed or contradictory inputs.
- Define battle/replay/observation identity, event-cursor units, request-less states, canonical prefix hashing, and uniqueness scope.
- Define phase and decision boundaries, including multiple requests/events within one turn, forced switches, terminal state, and pre/post-action ordering.
- Define the exact public/private classification for team fields, active fields, legal actions, `raw`, `log_delta`, rewards, and terminal metadata.
- Define perspective values and reject invalid or mismatched perspective/request-side combinations; do not default silently to `p1`.
- Specify representation and provenance for unrevealed, transformed, illusioned, tera, repeated-species, fainted, and replaced entities.
- Define source kinds and prevent replay/public/private source mixing without explicit lineage.

### Required tests and fixtures

- Protocol-prefix fixtures with per-line cursor and expected observation.
- No-future-event tests for same-turn and post-request ordering.
- Public/private redaction and hypothesis-field rejection tests.
- Perspective mismatch and request-side consistency tests.
- Snapshot immutability and monotonic-cursor tests.
- Golden mapping tests from existing `BattleView`/`ChoiceRequestView` without changing current feature vectors.
- Malformed protocol, missing request ID, non-monotonic cursor, contradictory field, and unsupported-schema tests.

### Environment prerequisite

`ENV-001` must precede implementation and validation that depends on Python/Node tooling. It is a separate work item and must document supported versions, dependency/lock strategy, sim-core build steps, clean-environment smoke testing, and exact focused-test commands. `ACTION-001` remains blocked.

## 12. ENV-001 environment validation — 2026-09-22

### Result

- `ENV-001: BLOCKED_WITH_REMEDIATION`.
- `READY_FOR_CONTRACT_IMPLEMENTATION: NO`.
- Added `docs/refactor/ENVIRONMENT_VALIDATION.md`.
- No packages were installed; no builds, tests, training, replay fetching, or servers were run.

### Confirmed environment facts

- Python declares only `>=3.8`; no runtime/test dependencies or Python lock/constraints are declared.
- Imports establish runtime dependencies on NumPy, PyTorch, FastAPI, Pydantic, Uvicorn, and PyYAML; pytest is required for tests.
- `sim-core/package.json` declares direct dependencies `@smogon/calc@0.11.0` and `pokemon-showdown@0.11.10`, with TypeScript and Node types as development dependencies. The lockfile provides a Node `>=16.0.0` lower bound through `pokemon-showdown`, but no project Node/npm policy is declared.
- Current host versions are Python 3.9.6, Node v24.21.0, and npm 11.19.0; they are not yet validated against the project.
- Current host lacks NumPy, PyTorch, FastAPI, Pydantic, Uvicorn, PyYAML, pytest, `sim-core/node_modules`, and `sim-core/dist/src/server.js`.
- Required sim-core setup is `npm ci --prefix sim-core` followed by `npm run build --prefix sim-core`; these commands were documented but not run.
- Required Python/sim-core variables are `PYTHONPATH`, `NEURAL_SIM_CORE_CWD`, and `NEURAL_SIM_CORE_COMMAND_JSON`.

### Gate consequence

ENV-001 must be remediated before STATE-001 adapter implementation or validation. `ACTION-001` remains blocked. The next authorized step is environment-policy remediation only; no dependency installation is implied by this update.

## 13. ENV-001 validation update — 2026-09-22

### User-reported validation evidence

- `npm test --prefix sim-core` completed successfully: build passed, 35 tests passed, 0 failed.
- Focused compiled `state_extractor` and `env_manager` tests completed successfully: 11 passed, 0 failed.
- The focused Python suite did not start because `python3 -m pytest` reported `No module named pytest`.
- Shared workspace verification confirms `sim-core/node_modules` and `sim-core/dist/src/server.js` are now present.

### Updated gate

ENV-001 remains `BLOCKED_WITH_REMEDIATION`: the Node/sim-core portion passes, but Python dependency declaration/lock policy and Python focused-test execution remain incomplete. `READY_FOR_CONTRACT_IMPLEMENTATION` remains `NO`; STATE-001 implementation and ACTION-001 remain blocked.

## 14. ENV-001 Python validation update — 2026-09-22

### User-reported evidence

- User-local installation completed for NumPy 2.0.2, PyTorch 2.8.0, FastAPI 0.128.8, Pydantic 2.13.5, Uvicorn 0.39.0, PyYAML 6.0.3, pytest 8.4.2, pip 26.0.1, setuptools 82.0.1, and wheel 0.48.0.
- Import smoke test passed.
- Focused Python suite ran: 132 passed, 4 skipped, 1 failed.
- The failure is `trainer/tests/test_sim_core_parity.py:117-119`, which expects at least three `.log` files under `data/replays/raw/gen9randombattle`; the directory currently has none. This is a missing fixture/data prerequisite, not an import or package failure.
- `trainer/tests/fixtures/replay_sample.log` exists but is not used by that test.

### Updated gate

ENV-001 remains `BLOCKED_WITH_REMEDIATION`. Node/sim-core validation is green and Python dependencies are operational, but dependency reproducibility is still undocumented/ungated and the focused suite is not fully green because the required replay-fixture policy is unresolved. `READY_FOR_CONTRACT_IMPLEMENTATION` remains `NO`; no source changes were made.

## 15. ENV-001 focused Python subset update — 2026-09-22

- User-reported replay-independent focused tests passed completely: 131 passed in 0.29s.
- This confirms the installed Python packages and the non-replay STATE-001-related tests are operational.
- ENV-001 remains `BLOCKED_WITH_REMEDIATION` because the broader suite still has the missing `data/replays/raw/gen9randombattle` fixture failure, and dependency versions are not yet declared/locked in the repository.
- `READY_FOR_CONTRACT_IMPLEMENTATION` remains `NO`; no source code was modified.

## 16. ENV-001 installation locations and accessibility — 2026-09-22

- Active Python executable: `/Library/Developer/CommandLineTools/usr/bin/python3` (Python 3.9.6).
- Python user-site packages: `/Users/nbolger/Library/Python/3.9/lib/python/site-packages`.
- Python user-site scripts: `/Users/nbolger/Library/Python/3.9/bin`; this directory is not currently on PATH, so future agents should use `python3 -m pip` and `python3 -m pytest` or add it to PATH.
- Verified import locations for NumPy, PyTorch, FastAPI, Pydantic, Uvicorn, PyYAML, and pytest are under the Python user site.
- Node executable: `/Users/nbolger/.nvm/versions/node/v24.21.0/bin/node`; npm executable: `/Users/nbolger/.nvm/versions/node/v24.21.0/bin/npm`.
- sim-core dependencies: `/Users/nbolger/Desktop/neural-showdown/sim-core/node_modules`.
- Compiled sim-core server: `/Users/nbolger/Desktop/neural-showdown/sim-core/dist/src/server.js`.
- Future agents must distinguish “not on PATH” from “not installed”; the above absolute paths and import checks are the current accessibility baseline.

## 17. Replay-policy closeout and STATE-001 slice — 2026-09-22

This section records the continuation work only; the repository-wide inventory
and prior H1-H5/M1-M8 analysis above are unchanged.

### Replay policy

- `trainer/tests/test_sim_core_parity.py::PublicReplaySanityTest` is marked with
  the registered `replay` marker.
- When `data/replays/raw/gen9randombattle/` is absent or has no `.log` files,
  the replay sanity class skips with: “Replay fixtures unavailable; run the
  documented opt-in replay-fixture setup before executing this test.”
- Replay provenance, expected storage, checksum guidance, and separate
  replay-independent, replay-backed, live/network, and training/evaluation
  commands are documented in `docs/refactor/REPLAY_FIXTURES.md`.
- No fixtures were fabricated or downloaded. Replay acquisition remains outside
  the default test and CI path.

### Dependency remediation

- `docs/refactor/ENVIRONMENT_VALIDATION.md` now separates ENV-001 from
  STATE-001 and records that the repository establishes only Python `>=3.8`.
- Runtime import dependencies are NumPy, PyTorch, FastAPI, Pydantic, Uvicorn,
  and PyYAML; pytest is a test dependency and setuptools remains a build-system
  requirement. Exact Python versions are not established by repository evidence
  and remain a blocker rather than being guessed.
- Node continues to use `sim-core/package-lock.json` and `npm ci`.

### STATE-001 implementation

- Added `sim-core/src/observable_state.ts` as an additive projection with schema
  version `observable-battle-state/v1`, explicit visibility boundaries,
  deterministic prefix hash/observation ID, normalized-record cursors,
  immutable snapshots, phase/request metadata, redaction, and fail-closed
  validation.
- Added `sim-core/tests/observable_state.test.ts` before the adapter behavior;
  existing `BattleView`, `ChoiceRequestView`, `StepResult`, feature vectors,
  checkpoints, live defaults, mechanics, and search were not changed.
- Expanded `docs/contracts/OBSERVABLE_STATE.md` into the normative field-level
  schema and source mapping; linked it from `docs/state-schema.md`.
- `ACTION-001` remains blocked pending STATE-001 review and acceptance.

### Commands and results

- `npm run build --prefix sim-core`: passed.
- `node --test sim-core/dist/tests/observable_state.test.js`: 5/5 passed.
- `node --test sim-core/dist/tests/state_extractor.test.js sim-core/dist/tests/env_manager.test.js`: 11/11 passed.
- `npm test --prefix sim-core`: 40/40 passed.
- `PYTHONPATH="$PWD/trainer/src" /Library/Developer/CommandLineTools/usr/bin/python3 -m pytest trainer/tests/test_state_provenance_no_leakage_contracts.py trainer/tests/test_tactical_state.py trainer/tests/test_public_information_belief_contracts.py -q`: 131 passed in 0.58s.
- `PYTHONPATH="$PWD/trainer/src" /Library/Developer/CommandLineTools/usr/bin/python3 -m pytest trainer/tests/test_sim_core_parity.py -q -m replay`: 2 skipped, 4 deselected; no fixture data was required.
- `git diff --check`: passed.

The remaining blockers are unchanged in substance: raw replay fixtures are
optional and absent, and Python dependency versions/lock strategy are not yet
declared or established. No servers, training, live evaluation, dataset
generation, package installation, or network replay acquisition was run.

## 18. STATE-001 remediation acceptance — 2026-09-23

The five required remediation findings were implemented in the additive
observable-state adapter, focused tests, and contract documentation only.

### Changes accepted

- Ordered canonical prefix comparison now preserves repeated records, including
  successive turn records, while rejecting rollback, replacement, reordering,
  truncation, and altered earlier records.
- Terminal event kind is tracked independently from winner identity, making win/
  tie contradictions order-independent while allowing repeated identical
  terminal evidence.
- Allowlisted protocol records now receive command-specific shape validation,
  including move targets, numeric records, optional engine tags, and request
  payload structure.
- Perspective validation requires the exact complementary opponent and rejects
  invalid/self-opponent pairs.
- Raw request JSON is validated as transient private evidence, reduced to a
  request-ID-only canonical prefix record, and excluded from observable hashes,
  serialization, and observation identity.

### Acceptance evidence

- Separate read-only acceptance review verdict: `ACCEPT`; no remaining gaps.
- `npm test --prefix sim-core`: 48 passed, 0 failed.
- `node --test sim-core/dist/tests/observable_state.test.js`: 13 passed, 0 failed.
- Replay-independent focused Python tests: 131 passed, 0 failed.
- Replay-marked parity selection: 1 skipped, 5 deselected because raw replay
  fixtures are absent; no replay acquisition was run.
- `git diff --check`: passed.

`STATE-001` is accepted. `ACTION-001` is unblocked but not started in this
checkpoint. `ENV-001` remains `BLOCKED_WITH_REMEDIATION` for its independent
dependency-policy and replay-fixture blockers.

## 19. ACTION-001 canonical-action acceptance — 2026-09-23

ACTION-001 was implemented after the STATE-001 acceptance gate and separately
reviewed. The accepted slice adds a versioned, request-bound CanonicalAction
contract with shared TypeScript/Python parity fixtures, deterministic IDs and
serialization, explicit legal-action provenance, fail-closed validation, and
an additive `step_canonical` ingress. The existing raw choice path remains the
runtime authority for legacy callers.

### Acceptance evidence

- Separate ACTION-001 review verdict: `ACCEPT`; required-changes list empty.
- Shared corpus: `tests/fixtures/canonical_action_v1.json`.
- `npm test --prefix sim-core`: 53 passed, 0 failed.
- Relevant Python tests from `trainer/tests`: 20 passed, 2 skipped for existing
  environment-dependent cases.
- `git diff --check`: passed.

### Boundaries and rollback

Targeted moves, multi-active commands, pass, and skip remain outside v1. Wait
and team-preview expose no canonical action; forced-switch exhaustion preserves
the existing synthesized default fallback. Rollback removes only the
canonical-action modules, fixtures/tests, contract, and additive ingress;
legacy action codec and raw-choice submission remain intact.

## 20. FIXTURE-001 and FIXTURE-002 acceptance — 2026-09-23

Both fixture work items were completed after ACTION-001 acceptance and
separately reviewed.

- FIXTURE-001 verdict: `ACCEPT`.
- FIXTURE-002 verdict: `ACCEPT`.
- Protocol-prefix corpus: `tests/fixtures/observable_state_v1.json`, covering
  decision cutoffs, redaction, event families, repeated/non-contiguous slots,
  terminal requestless state, and exact-prefix acceptance/rejection.
- Action parity corpus: `tests/fixtures/canonical_action_v1.json`, covering
  complete masks/action arrays, labels, choices, slots, deterministic IDs,
  byte-identical TypeScript/Python serialization, and multi-action requests.
- Validation: sim-core 55/55 passed; relevant Python replay-independent suite
  135 passed; focused FIXTURE-001 tests 2/2 passed; focused FIXTURE-002 tests
  4/4 in both runtimes; `git diff --check` passed.
- No replay data or network acquisition was used, and no adapter or simulator
  semantics were changed.

## 21. TRANS-001 seeded-transition acceptance — 2026-09-23

TRANS-001 was implemented after STATE-001, ACTION-001, FIXTURE-001, and
FIXTURE-002 acceptance and separately reviewed twice. The first review returned
`REQUIRED CHANGES`; the remediation kept the slice additive and addressed the
three concrete gaps: raw simulator snapshots now stay behind server-managed
opaque handles, snapshot lineage and simulator revision are authoritative, and
the golden transition captures a non-empty ordered event delta.

### Acceptance evidence

- Separate remediation review verdict: `ACCEPT`; no blocking findings.
- `npm test --prefix sim-core`: 59 passed, 0 failed.
- Focused transition suite: 4 passed, 0 failed.
- Relevant Python replay-independent suite: 135 passed, 0 failed.
- Fixture JSON parse and `git diff --check`: passed.
- Event evidence preserves raw `|t:|<integer>` records while normalizing only
  for deterministic fingerprints/fixture comparison; moves, damage, upkeep, and
  turn advancement are asserted in order.
- RPC evidence: `capture_seeded_snapshot` returns a `SeededSnapshotRef`, raw
  `simulator_state` is rejected at the transition boundary, and output returns
  only an opaque snapshot reference. Legacy step/canonical ingress remains
  additive and the ENV-001 blocker is unchanged.

### Boundaries and rollback

The accepted v1 boundary supports complete two-player request-bound canonical
actions and rejects stale, unavailable, wait/team-preview, forced-invalid, and
mixed-validity inputs atomically. Targeted/multi-active/pass/skip semantics,
search redesign, retraining, replay acquisition, and live-default changes are
out of scope. Rollback removes only the transition module, fixtures/tests,
contract, and additive RPC/method while retaining legacy step, restore, and
belief-fork behavior.

## 22. BELIEF-001 separate BeliefState acceptance — 2026-09-23

BELIEF-001 adds a separate, versioned, perspective-owned belief snapshot beside
ObservableBattleState. The v1 schema records candidates, explicit evidence,
unresolved uncertainty, canonical identity, immutable snapshots, and
observation/transition/simulator-snapshot histories. It does not define
probability or confidence values, propagate beliefs, or change existing
consumers.

### Acceptance evidence

- Final separate read-only review verdict: `ACCEPT`; no blocking findings.
- Shared fixture: `tests/fixtures/belief_state_v1.json`.
- Focused BeliefState tests: 9 passed, 0 failed. They cover deterministic
  serialization/order, immutability, exact lineage, imported-parent validation,
  malformed and contradictory observation prefixes, requestless availability,
  derived evidence dependencies, contradictions, open-world uncertainty, and
  simulator-only truth isolation across transitions.
- `npm test --prefix sim-core`: 68 passed, 0 failed, including STATE-001,
  ACTION-001, FIXTURE-001/FIXTURE-002, and TRANS-001 regressions.
- Scoped Python suites: 194 passed, 10 skipped, 7 failed. All seven failures
  are in existing `test_live_private_value.py` checkpoint-loading paths and
  report `_pickle.UnpicklingError: invalid load key, 'v'`; no Python source or
  checkpoint was changed by BELIEF-001.
- Fixture JSON parsing and `git diff --check`: passed.
- ENV-001 remains independently blocked; BELIEF-001 did not change dependency
  policy or acquire replay fixtures.

### Boundaries and rollback

The BELIEF projector is not connected to accepted observation, action,
transition, runtime, feature, search, or training paths. Legacy possible_*
fields, Python posterior APIs, and belief-fork behavior remain unchanged.
Rollback removes only the BeliefState module, fixture/tests, contract, and
documentation links.

## 23. DATA-001 dataset-lineage acceptance — 2026-09-23

DATA-001 was implemented after STATE-001 and BELIEF-001 acceptance and passed
a separate read-only acceptance review.

### Changes accepted

- Added `docs/contracts/DATASET_LINEAGE.md` defining the additive
  `dataset-record/v1` envelope for battle/replay identity, source/private
  provenance, schema fingerprints, observation/feature cursors, exact prefix
  hash verification, deterministic identity, and battle/replay-disjoint splits.
- Added `trainer/src/neural/dataset_lineage.py` with fail-closed validation,
  deterministic serialization and record IDs, prefix validation, split
  assignment/collection checks, and source-specific metric reports.
- Added lineage metadata and complete-collection validation before writes in
  the public replay value/policy and live-private value builders. Existing
  feature vectors and legacy source labels remain unchanged.
- Added the synthetic fixture `tests/fixtures/dataset_lineage_v1.json` and
  focused coverage for valid/malformed/unsupported records, future and
  mismatched prefixes, privacy exclusion, duplicate identities, battle/replay
  split collisions, deterministic identity, and source metrics.

### Acceptance evidence

- Separate read-only review verdict: `ACCEPT`; no required changes remain.
- Focused DATA/replay/private selection: 21 passed, 21 deselected.
- `npm test --prefix sim-core`: 68 passed, 0 failed.
- `git diff --check`: passed.
- The known checkpoint-loading baseline remains separate: 194 passed, 10
  skipped, and 7 existing failures in `test_live_private_value.py`; no
  checkpoint or source workaround was made.
- No replay data, network acquisition, training, live evaluation, package
  installation, search redesign, or ENV-001 change was performed.

### Boundaries and rollback

Legacy datasets remain read-only until migrated to complete envelopes. Current
records without canonical belief or seeded-transition joins retain null fields;
the DATA-001 slice does not invent evidence, calibration, confidence, or model
inputs. Rollback removes the additive contract/module/fixture/tests and builder
metadata/validation while preserving legacy dataset files and consumers.

## 7. SEARCH-001 rollout/search semantics — 2026-09-23

### Scope and review

- Implemented the authoritative work item as a documentation-only record in
  `docs/contracts/SEARCH_SEMANTICS.md`.
- Three bounded read-only inspections covered rollout/evaluator architecture,
  accepted-contract integration, and determinism/privacy/test evidence.
- A separate read-only acceptance review returned `ACCEPT`, including a
  follow-up after two clarifications to the final document.

### Confirmed boundaries

- Exact replay rollout, approximate synthetic scoring, one-turn branching, and
  two-ply/belief branching are distinct current paths, not one shared mode set.
- Existing search does not consume ObservableBattleState, CanonicalAction,
  BeliefState, or SeededTransition. Canonical stale-action rejection and
  exact-prefix lineage guarantees do not automatically apply at the legacy
  search boundary.
- Approximate protocol context is cut at turn granularity; exact replay scoring
  combines branch records with the selected trace step's view/request context.
  Search-level future-event isolation and stable shared node identity remain
  unresolved and are stated as such.
- Existing feature vectors, checkpoints, live defaults, simulator mechanics,
  and search behavior are unchanged. Any search integration needs a separate
  scoped work item.

### Validation

- `npm test --prefix sim-core`: 68 passed, 0 failed.
- Focused Python search suites: 19 passed, 10 skipped.
- `git diff --check`: passed.
- The existing broader checkpoint-loading baseline of 194 passed, 10 skipped,
  and 7 existing failures was not re-run or altered; it remains separate.

## 8. Current pipeline readiness update — 2026-09-24

This entry is the latest current-state summary and supersedes earlier
preparation-stage statements where they differ. It does not rewrite prior
acceptance evidence.

### Accepted lower-level work

STATE-001, ACTION-001, FIXTURE-001, FIXTURE-002, TRANS-001, BELIEF-001,
DATA-001, and SEARCH-001 remain accepted as recorded above and in
[`refactor/WORK_ITEMS.md`](refactor/WORK_ITEMS.md). DATA-001's normative
contract was accepted on 2026-09-23; its contract header is synchronized to
that status.

### Current blockers and scope

- ENV-001 remains `BLOCKED_WITH_REMEDIATION`. The pinned Node simulator
  declaration, lock entry, and installed version agree, but that does not
  resolve Python dependency/lock policy or clean-environment validation.
- SIM-COVERAGE-001 records the pinned `pokemon-showdown@0.11.10` /
  `gen9randombattle` inventory and a fail-closed source/registry/token checker.
  It has explicit lifecycle and generic-protocol gaps; it is not a completeness
  claim and does not accept PIPELINE-001 or FEATURE-001.
- PIPELINE-001 remains an implementation candidate, not accepted. Focused
  evidence covers real transitions, both perspectives, successor lineage,
  deterministic cross-process identities, Python DATA-001 validation, and
  rejected-candidate preservation. A naturally occurring simulator rejection
  has not yet been covered.
- FEATURE-001 remains unresolved. The feature schema, target, reward/horizon,
  privacy/information regime, and training/runtime interface are not accepted.
- No new refactored-model dataset has been generated and no new model has been
  trained. Existing legacy/vNext checkpoints are intentionally abandoned and
  non-blocking. No claim is made that the real `/evaluate` route is verified
  for a future model.

### Current validation and next step

On 2026-09-24, `npm run build` passed; 38 focused TypeScript tests passed;
`npm run check:simulator-coverage`, its synthetic drift self-tests, and
`git diff --check` passed. These are focused contract/mechanics and drift
checks, not model-quality, dataset-quality, or live-route evidence.

Next: disposition the SIM-COVERAGE gaps, complete the PIPELINE-001 acceptance
slice including natural simulator rejection, then design FEATURE-001 before
any bulk extraction or new dataset generation. Resolve ENV-001 before claiming
reproducible generation/training readiness. The current concise gate table is
[`PROJECT_STATUS.md`](PROJECT_STATUS.md).

## 2026-09-24 focused protocol correction and milestone update

This is an additive current verification record. It does not rewrite or
supersede earlier dated pass counts and does not accept PIPELINE-001,
SIM-COVERAGE-001, ENV-001, or FEATURE-001.

### Repository state and changes

- Branch: `refactor/state-001-observable-state`.
- HEAD: `b9b3eb06d362963bb1fa2da21d7c471a84df262c`; substantial pre-existing
  worktree edits remain and were preserved.
- Random-controller action selection accepts an injected RNG while retaining
  `Math.random()` as the legacy default. Optional per-player uint32 controller
  seeds use streams separate from Showdown's four-word simulator seed.
- Move target validation now follows pinned `pokemon-showdown@0.11.10` source:
  active actor identifiers remain active-position forms; targets may identify
  active or non-active Pokémon (`p1a: ...` or `p1: ...`); target may be omitted
  or empty; literal `null` is accepted only with the exact trailing
  `[notarget]` tag, matching `BattleActions.useMoveInner`. Trailing bracket
  tags are never interpreted as targets.
- Pipeline prefix and step-result projection stop `clearstatus`,
  `-clearstatus`, and `nothing` with
  `pipeline/v1/unresolved-protocol-alias` and a structured diagnostic. A
  candidate carrying an unresolved alias cannot replace the committed boundary
  or its observation/belief lineage.
- `-nothing` remains a distinct, supported no-payload raw-only record; the
  pinned Gen 9 Splash callback emits it in `data/moves.ts:18380-18384`.
- `docs/refactor/WORK_ITEMS.md` defines PIPELINE-002 requirements for complete
  episode progression. It is not implemented.

### Fresh verification

- `npm run build --prefix sim-core`: passed.
- `node --test sim-core/dist/tests/simulator_coverage.test.js
  sim-core/dist/tests/state_extractor.test.js
  sim-core/dist/tests/observable_state.test.js
  sim-core/dist/tests/action_codec.test.js
  sim-core/dist/tests/pipeline_integration.test.js`: 41 passed, 0 failed.
  Terminal repeatability used simulator seed `[101, 202, 303, 404]`, p1 random
  controller seed `0x51a7`, p2 random controller seed `0xc0de`, and compared two
  complete normalized protocol traces.
- `PYTHONPATH="$PWD/trainer/src" python3 -m pytest
  trainer/tests/test_pipeline_record.py trainer/tests/test_dataset_lineage.py
  -q`: 18 passed. Pipeline integration also validated both perspective records
  in fresh Python subprocesses.
- `npm run check:simulator-coverage --prefix sim-core`: exit 1,
  `Local coverage source digest changed:
  a9e4ec60254e5cc89672777cb98611279e2b7da3fca4a9c57a233ea0ea07b8af`.
- `node sim-core/scripts/check-simulator-coverage.cjs --self-test`: all six
  synthetic drift assertions passed; command then exited 1 on the same changed
  local-source digest.
  The reviewed digest was not updated. Separate semantic review is required
  before attestation.
- Bounded post-preflight simulator-rejection probe: format
  `gen9randombattle`, simulator seed `[101, 202, 303, 404]`, all 169 legal joint
  pairs from each side's 13-entry initial action index space. Outcome: 169
  accepted transitions, 0 natural `pipeline/v1/rejected-action` results. This
  bounded single-seed result is not proof of impossibility. Existing injected
  rejection remains labeled injected; acceptance decision remains unresolved.
- No clean install/environment, package acquisition, network, replay, dataset,
  feature-extraction, training, or checkpoint operation was performed.

### Current sequence and open decisions

1. Deterministic protocol and stopping-behavior fixes.
2. SIM-COVERAGE gap disposition and complete-episode boundary requirements.
3. PIPELINE acceptance with explicit supported scope and rejection guarantees.
4. ENV reproducibility remediation in parallel.
5. Training objective/information regime together with FEATURE-001 and the
   model interface.
6. Feature extraction, bounded collector, and validated pilot dataset.
7. New-model training and held-out evaluation.
8. Live/search integration and operational hardening.

Optional raw replay fixtures are not required for the first simulator-only
milestone; replay-specific claims still require them. Dataset, model, and
product-release gates are separate in `docs/PROJECT_STATUS.md`. The evidence
index in `docs/refactor/WEST_MONROE_REVIEW_EVIDENCE.md` makes no compliance
claim: no West Monroe internal standard was supplied. Exact source notes,
commands, and continuation actions are in
`docs/refactor/PIPELINE-CORRECTNESS-2026-09-24-PROGRESS.md`.
## Scoped PIPELINE-001 review — 2026-09-24

- Accepted PIPELINE-001 for explicit v1 joint-actionable requests, including
  joint forced switches. Complete-episode one-sided switch, waiting, and
  requestless progression remain PIPELINE-002.
- Source review established a natural post-preflight rejection path: Gen 9
  Random Battle sets provide trapping abilities; Showdown may expose a hidden
  trap as `maybeTrapped` while request-derived actions still offer a switch;
  `Side.chooseSwitch` rejects it. A deterministic real-simulator regression
  proves candidate discard and committed lineage preservation.
- Attested listed local coverage-source digest
  `479a096563318af86addd64dd39d445c56e8c5b4d9c8ba0a1c0e100b3c3861d2` after
  focused semantic review. This is not acceptance of all SIM-COVERAGE
  lifecycles or FEATURE-001.
- Fresh verification: build passed; focused TypeScript 42/42; Python
  record/lineage 18/18; coverage checker and six synthetic self-tests passed.
- Next task: disposition the remaining SIM-COVERAGE lifecycle gaps that
  constrain PIPELINE-002. No compliance claim is made.

## PIPELINE-002 request-reporting semantic review — 2026-09-24

- Accepted the reporting slice only: opt-in wait requests preserve legacy
  defaults; per-player classification distinguishes actionable, forced switch,
  waiting, absence and terminal; restoration suppresses consumed requests while
  retaining private facts; perspective privacy and joint-only guards remain.
- Reviewed the unchanged three-source/two-test diff against pinned Showdown
  request/choice semantics. Reused the matching passing build, 53 TypeScript
  tests and 18 Python tests; no production correction or runtime probe needed.
- Added reviewed `tests/env_manager.test.ts` to local coverage hashing and
  attested `3d4f9c1a5d41aef6ed8047dfc5faad87ddf86176f1022f7744b963fee042bab2`.
  Fresh coverage checker and all six self-tests passed. Simulator digest is
  unchanged; no blanket lifecycle, full typed-view or feature acceptance.
- PIPELINE-001 scoped acceptance stands; full PIPELINE-002 remains unaccepted.
  Next implementation: versioned one-sided forced-switch transitions with
  actor-only records and atomic two-perspective successor lineage. See
  `docs/refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md` for current evidence.

## PIPELINE-002 ordinary forced-switch implementation — 2026-09-24

- Implemented additive `seeded-forced-switch/v1` with distinct actor/waiting
  roles and one canonical switch; legacy joint API/identity remains unchanged.
  Both successor observations/beliefs update, but only the actor receives a
  `pipeline-forced-switch-record/v1` bundle/reference for Python validation.
- Real p2 KO and p1 U-turn regressions prove repeatability, actor-only records,
  both belief joins, resumed joint play and rollback after candidate failures.
  Revival exclusion is source-shaped synthetic coverage, not natural execution.
  Post-commit cleanup failures retry at close instead of reporting rejection.
- Build passed; focused TypeScript 67/67 and Python record/lineage 20/20 passed.
  Coverage checker and self-test command stop solely on local digest
  `5dd07856eaf1de8754e5ee39e5878b73caa67a42b56b6b6d932ec0ee3cd8add3`;
  all six synthetic checks pass. Previous attestation is unchanged.
- No semantic acceptance of the new execution slice. Single next task: separate
  review of transition/record versions, live guards, both beliefs, privacy,
  ordinary/revival scope and publication/cleanup, including Python validation
  and new tests, before digest attestation. Checkpoint:
  `docs/refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md`.

## PIPELINE-002 ordinary forced-switch semantic review — 2026-09-24

- Accepted only ordinary `gen9randombattle` forced-switch-plus-wait execution.
  No blocking findings or source corrections. Reviewed transition/record schema
  pairing, live requests, actor-only submission/publication, both successor belief
  joins/privacy, deterministic TypeScript/Python identity and atomic rollback.
  Post-commit disposal cannot masquerade as rejection; session operations are serial.
- Real p2 KO and p1 U-turn cases resume joint play. Revival Blessing is explicitly
  excluded using the pinned request-provided `reviving` flag; its exclusion test
  is synthetic. No complete-episode, chained-hazard or full typed-view acceptance.
- Independently matched the implementation digest, reused build/67 TypeScript
  evidence, and freshly passed 5 forced-switch plus 20 Python record/lineage tests.
- Added `tests/forced_switch.test.ts`, `../trainer/src/neural/pipeline_record.py`,
  `../trainer/tests/test_pipeline_record.py` to local hashing (relative to sim-core).
  Four implementation files were already hashed. Attested recomputed digest
  `b37c9b26a82b8a389042cdf84f107788baaaf63624f4bc9a167625542adc2bf2`.
  Coverage checker and all six self-tests pass; simulator digest unchanged.
- Single next implementation: bounded decision/terminal settling with explicit
  stall/error/stream-close handling and committed-lineage preservation. Exact
  scope, evidence and remaining gaps: `docs/refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md`.

## PIPELINE-002 bounded settling implementation — 2026-09-24

- Added source-emission/consumer-acknowledgement barrier for pinned Showdown
  fan-out. Decision waits for all addressed/public deliveries; terminal also
  requires source end and matching player views. Intermediate requestless output
  never invents actions. Buffered terminal output can drain after source EOF.
- Defaults: 5,000 ms per wait, 100,000 messages since previous settled boundary.
  In-process clock/scheduler controls support signal-driven tests. Structured
  settling-failure/v1 errors distinguish timeout, message-limit, simulator-error,
  stream-closed and cancelled. Failure releases waiters/timers/consumer tasks;
  coalesced destruction handles close/failure races. Candidate failures preserve
  committed lineage and publish nothing. No successful schema/identity changes.
- Changed env_manager.ts and pipeline_integration.ts; new settling.ts and
  tests/settling.test.ts. Build and 85 TypeScript/20 Python checks pass, including
  all 67 prior tests and 18 new controlled lifecycle regressions. Coverage commands
  exit 1 only for listed-source digest
  `0273358b808f31162574d05a8cc9b113cc5b45ecc50770490e972f14493b6a3e`;
  six drift self-tests pass. Prior attestation remains unchanged.
- Implementation only: no semantic acceptance of settling. Single next task is
  separate lifecycle/digest review, including inclusion of the new source/tests.
  Prior joint and ordinary forced-switch acceptance stands; full episodes,
  revival support and typed-state lifecycle completeness remain open. Current
  checkpoint: `docs/refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md`.

## PIPELINE-002 settling semantic review — 2026-09-24

- Accepted bounded settling for pinned Showdown and serialized session operations.
  No blocking findings or source corrections. Verified synchronous source emission
  versus asynchronous fan-out acknowledgements, terminal/end/EOF order, fixed
  limits, resource cleanup, sticky failure and candidate rollback. No successful
  schema/identity changes; synchronous simulator calls cannot be preempted.
- Matched all four checkpoint file hashes and prior listed-source implementation
  digest. Reused build/85 TypeScript/20 Python evidence; freshly passed 18 settling
  tests and two controlled review probes (progress cannot reset budgets; late
  output cannot publish and next transition still equals untouched control).
- Added src/settling.ts and tests/settling.test.ts to coverage hashing. Attested
  `ffc9091735e5838b66a1d29cda6afcc973a9953bf01fcbb72132217335bff1b2`.
  Coverage checker and all six self-tests pass; simulator digest unchanged.
- Single next task: bounded episode executor with explicit completed/truncated/failed
  outcomes and finite rejection recovery, as specified in the checkpoint. Public
  switch/faint/Shed Tail lifecycle fidelity is a prerequisite for faithful complete
  episode publication; Revival Blessing and unsupported boundaries truncate until
  implemented. Complete-episode readiness remains a separate acceptance milestone.

## PIPELINE-002 bounded episode implementation — 2026-09-24

- Added pipeline_episode.ts, episode regressions and PIPELINE_EPISODE contract;
  pipeline_integration.ts adds a private-request scope preflight for all forced
  requests, including joint boundaries. Existing transition schemas/APIs unchanged.
- pipeline-episode/v1 reports completed/truncated/failed, normalized budgets,
  segment origin/final committed boundary, counts, ordered transition IDs and
  committed per-player bundles. Owns/closes sessions; default 256 commits/512
  attempts/three rejected candidates per boundary. Only explicit choice rejection
  retries, excluding tried tuples from current committed requests. Cancellation
  is observed between commits. Revival and unsupported boundaries truncate.
- Real default seed [101,202,303,404] completes repeatably in 55 commits with
  both forced-switch actor paths. Natural Arena Trap retry and controlled budgets,
  cap exhaustion, protocol/revival/cancellation/failure/cleanup paths pass. Build,
  102 TypeScript (85 prior + 17 new) and 20 Python tests pass. Runtime completion
  always retains faithful_complete_episode:false; typed lifecycle fixes remain.
- Coverage commands exit 1 solely on listed-source digest
  `df2e893485475552f19e808603be2f3a4e9ca3e342ee2efaa2ef5a9c780b349c`; all six drift checks pass.
  Prior attestation unchanged; runner/tests not yet in the hashed list. No semantic
  acceptance of this implementation. Next: separate runner/preflight and coverage
  inclusion review, preserving complete-publication exclusions. Checkpoint:
  docs/refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md.

## PIPELINE-002 bounded episode semantic review — 2026-09-24

- Accepted pipeline-episode/v1 orchestration for exclusive serialized-session ownership;
  no blocking findings or production corrections. All three checkpoint hashes match.
  Distinct outcomes, 256/512/3 counting/reset/limit semantics, committed-request tuple
  exclusion and explicit-choice-rejection-only recovery match the contract. Actor-only
  records append once after commit; partial lineage/final boundary survive stops.
  Cooperative cancellation, cleanup and unsupported/revival truncation are explicit.
- Reused matching 102 TypeScript/20 Python evidence (real repeatable 55-commit completion,
  Arena Trap recovery). Fresh build and 17 runner regressions pass. Two review probes
  pass: terminal at both exact limits plus simultaneous cancellation; one synthetic
  legal tuple exhausted after one rejection with no publication. Evidence paths in
  docs/refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md.
- Added runner source/tests to hashing (22 files). Attested
  `4cb99bbc935da7db2edf70568099a19e4876eba049301d459481a0c27077d1c1`.
  Checker and six self-tests pass; simulator digest unchanged. No new Python schema.
- Next task: public boost/volatile switch/drag/faint/re-entry clearing plus supported
  Shed Tail Substitute transfer, with both-perspective/restoration/record checks and
  separate semantic review. Keep faithful_complete_episode:false; runner acceptance
  does not establish faithful complete-episode publication or broader lifecycle scope.

## PIPELINE-002 public boost/volatile lifecycle implementation — 2026-09-24

- Corrected extractor switch/drag/faint/re-entry clearing with source-supported
  retained evidence and Eternamax exception; actual Shed Tail switch tags copy only
  Substitute. No private effect counters or observation/record schema additions.
- Public occupancy is separate from request active flags; self request merging uses
  addressed identity because Showdown reorders slots. Canonical self move IDs fix
  live/replay display-name duplication revealed by new tests. Raw event order and
  perspective privacy are unchanged. Broader lifecycle fields remain separate.
- Added 15 regressions across state extractor, environment and forced-switch tests,
  with a shared constructed-team helper. Real simulator moves cover both actors:
  ordinary switch/re-entry, drag, faint/replacement, successful/failed Shed Tail;
  replay equality, both beliefs, actor-only repeatable records and Python validation.
  Build, 117 TypeScript and 20 Python tests pass; git diff --check passes.
- Listed-source digest d231c19ccde9feed1454315418b2eeb56f8bc63ea00ffab27a01af09788db6fc
  now differs from prior attestation; both checker commands exit 1 solely on drift,
  six synthetic self-tests pass. Manifest/attestation untouched. Separate semantic
  review must also consider adding tests/helpers/state_lifecycle.ts to hashing.
- Checkpoint: docs/refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md. Next task is
  semantic review of this slice. Other switch/faint fields, linked effects, broader
  transfers, Revival Blessing and wider lifecycle coverage still need disposition;
  faithful_complete_episode:false remains mandatory. No full-publication acceptance.

## PIPELINE-002 boost/volatile lifecycle review — blocked 2026-09-24

- Matched all five checkpoint hashes; reviewed ordinary clearing/retention and Shed
  Tail against pinned simulator source and actual tags. Reused 117 TypeScript/20
  Python evidence; fresh build and 16 focused tests pass. No source/test changes.
- Real constructed-team Illusion probes for both actors expose blockers. Zoroark
  Fox disguised as bench Snorlax Mask uses Nasty Plot; owner state places spa:2 and
  nastyplot on inactive Mask, not active Fox. Snapshot replay removes Mask's erroneous
  move/reveal entries, changing observation identity. Name matching/public occupancy
  and replacement reconciliation need Illusion-aware roster binding.
- Pinned abilities.ts:2022-2024 emits conditionless replace. observable_state.ts:511-518
  incorrectly requires a condition, rejecting valid reveal with unsupported-observable-
  protocol/Malformed raw replace record. Existing fixture neither changes identity nor
  uses the real grammar. These latent gaps block the requested slice acceptance.
- Attestation/list untouched. Changed sources/tests already listed; new shared fixture
  helper belongs in hashing after correction/review. Both coverage commands still exit
  1 solely on d231c19ccde9feed1454315418b2eeb56f8bc63ea00ffab27a01af09788db6fc drift;
  six self-tests pass. Evidence/probe paths and next-task criteria in
  docs/refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md.
- Highest-priority next correction: Illusion alias/roster binding and source-backed
  reveal grammar with both-perspective, restore, privacy and deterministic publication
  regressions. Other fields, linked effects and Revival Blessing remain separate;
  faithful_complete_episode:false is unchanged. No faithful-publication acceptance.

## PIPELINE-002 Illusion correction implementation — 2026-09-24

- Reproduced blockers corrected in extractor/observable validator. Public appearances
  accumulate position evidence independently of private requests; own observations
  bind it to the addressed actual roster member at projection time. Inactive uncertain
  aliases do not contaminate the bench. Reveal restores the prior displayed entry and
  reconciles evidence to the actual/reused identity without rewriting old observations.
- Conditionless replace has separate strict grammar; valid legacy condition records
  remain supported. Real reveal additionally emits a public Illusion Level Mod -hint:
  validated raw-only retention added without deriving state from prose or exposing
  private identities. Existing schemas/visibility and faithful=false remain unchanged.
- Build, 126 TypeScript and 20 Python tests pass. Eight new constructed-team real
  simulator tests cover both actors, known/unseen teammates, unrevealed departure,
  boosts/Substitute, reveal/re-entry/faint, exact prefixes/privacy, full replay equality,
  deterministic beliefs/records and Python validation. One parser regression covers
  valid/malformed replace/hint. Original probes now pass. Prior 117 tests remain green.
- Manifest/attestation unchanged. Checker and self-test exit 1 on listed-source digest
  8e74d9cf02e2d920c4131bfbb040d4167b05c62c612e8df445d6d08a5fd8d713 and -hint token
  classification drift; six synthetic tests pass. Next: separate semantic review of
  combined boost/volatile/Illusion corrections, helper/new test hashing, and raw-only
  hint inventory/classification before attestation. Exact scope/hashes/evidence in
  docs/refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md. Other lifecycle fields,
  linked effects, Revival Blessing and faithful complete-episode publication remain open.

### Combined lifecycle/Illusion review — blocked, 2026-09-24

The original identity contamination and conditionless replace failures pass the
scoped review. Pinned Illusion.onEnd/Battle.hint support conditionless replace and
raw-only hint; malformed-input guards remain. Existing mirrored tests verify
ownership, privacy, immutable prefixes, replay and deterministic publication.
However, fresh appearances at state_extractor.ts:406-448 discard public Tera on
re-entry: both-actor real probes emit tera:Fire while opponent views report
Normal/false and owner views Fire/true. Combined acceptance is blocked.

Eight checkpoint hashes match; fresh build and 43 focused tests pass; matching
126 TypeScript/20 Python evidence reused. Existing source/test coverage inclusion
is appropriate; helper and Illusion tests must also be hashed after correction.
Manifest, token classifications and attestations remain untouched. Both checker
commands fail digest and added -hint drift; all six synthetic self-tests pass.
Checkpoint contains exact digest, reproduction and completion criteria. Next:
correct explicit public Tera re-entry without alias leakage, then semantic review.
Other fields, linked effects and Revival Blessing remain outstanding;
faithful_complete_episode:false remains mandatory.

### Public Tera re-entry correction — implementation, 2026-09-24

Fresh switch/drag appearances now set their Terastallized flag from public tera:TYPE
before resolving types, matching pinned getFullDetails for both emitters and Illusion
without importing private identity. Only state_extractor.ts, illusion.test.ts and the
shared lifecycle helper changed in source/tests. Four real mirrored switch/drag cases
cover both perspectives, no-tag teammate isolation, hidden identity/reveal, restoration,
immutable prefixes, repeatable records/beliefs and Python record validation.

Fresh build/130 TypeScript tests/diff checks pass; prior 20 Python tests reused.
Original ordinary Snorlax reproduction passes. Combined acceptance remains pending;
manifest/list/classifications/attestation unchanged. Listed digest is now
5e69a24866f9142cd0414b38f5d7ec2e70ca440f8a8986b52d56eca6737cfa5a;
checker commands reject digest and -hint drift, six synthetic self-tests pass.
Next: combined semantic review, then helper/Illusion test inclusion and raw-only hint
classification/inventory before recomputing/attesting. Checkpoint records exact scope,
hashes and evidence. Broader fields/linked effects/Revival Blessing remain open;
faithful_complete_episode:false remains.

### Combined lifecycle/Illusion/Tera acceptance — 2026-09-24

Scoped acceptance: ordinary boost/volatile switch/drag/faint/re-entry clearing,
Shed Tail Substitute-only transfer, Illusion appearance/own-request ownership and
reveal reconciliation, conditionless replace/raw-only hint, and explicit non-Stellar
public Tera switch/drag re-entry. Existing Eternamax retention exception does not
expand supported formats. Pinned source and mirrored constructed-team Fire tests
support both perspectives, restore/reveal, immutable prefixes, privacy and repeatable
Python-validated records. No production corrections during review.

Eight hashes match; passing build/130 TS/prior 20 Python evidence reused. Fresh
29 Illusion/observable tests pass, including new Python publication checks. Added
shared lifecycle helper and Illusion/Tera tests to hashing (24 files), classified
-hint raw-only, reconciled its inventory/exclusion and corrected replace grammar.
Computed and attested local digest: `3b777601e68932a409271b7103a0013b21abbfcc9d8c4f25c0fd118f2dcfc4e2`.
Pinned simulator digest remains unchanged. Coverage checker and six synthetic
self-tests pass. Evidence and exact source hashes are in the current checkpoint.

This supersedes earlier pending/blocked dispositions only for the accepted scope.
Next bounded prerequisite: public Tera reset on faint with mirrored real KO,
privacy/prefix/restoration and publication checks. Stellar defensive typing,
other fields, linked effects, wider transfers, Revival Blessing and faithful
complete-episode publication remain separate gates. Keep faithful_complete_episode:false.

### Faint Tera and terminal restoration implementation — 2026-09-24

Non-Stellar faint now deactivates Tera and restores observable non-Tera typing while
retaining known Tera type. Own projection overrides stale pre-faint request flags.
Unrevealed Illusion Explosion preserves opponent uncertainty and bench teammate data.
Exact terminal restoration exposed missing legitimate own-request history: optional
terminal-only terminal-request-history/v1 metadata now stores addressed side-bearing
requests behind opaque snapshots. No public records or actions are created; malformed
version/side/roster/nonterminal metadata rejects before replacing current state.
Outer schemas unchanged; terminal fingerprints include metadata. Bare legacy terminal
JSON lacks historical private data and cannot provide exact observation restoration.

Changed: state_extractor.ts, env_manager.ts, shared lifecycle helper, illusion.test.ts.
Parent build/134 relevant TS tests pass; delegated full suite157 passes; prior20 Python
tests reused and new records validated through Python. Mirrored terminal/Illusion KO
cases verify both perspectives, replay, immutable prefixes, teammate privacy and
repeatable records/beliefs. Diff checks pass. Checkpoint contains hashes and logs.

Implementation only; separate semantic review/attestation required. Four changed
files already hashed. Manifest untouched; both checker commands fail solely on digest
300cfa84ccf97db8fb54653a02fe45c657c6c7ce45a4676448bfa60fcf7c0c02;
six synthetic self-tests pass. Prior accepted digest remains
3b777601e68932a409271b7103a0013b21abbfcc9d8c4f25c0fd118f2dcfc4e2.
Next: review this correction and terminal metadata compatibility/privacy, then attest.
Stellar and broader lifecycle gaps remain; faithful_complete_episode:false unchanged.

### Faint/terminal-history review — blocked, 2026-09-24

Pinned non-Stellar faint semantics and normal mirrored privacy/Illusion/teammate/
immutable-history checks pass. All four source/test hashes match; reuse build134/full157
TS and prior20 Python evidence. Fresh16 Illusion/Tera tests pass including Python
publication. No production changes or acceptance/attestation in this review.

Blocker: env_manager.ts:55-83 validates the request envelope and roster array but not
its entries. A real terminal snapshot with requests.p1.side.pokemon[0].ident = 7
passes validation, destroys prior state at line441, then throws in selfFromRequest.
Numeric details/condition also reject late; null entries and string stats succeed
as corrupt own observations. Parent confirmed the independent probe:
/tmp/neural-terminal-history-nested-probe.cjs and
/tmp/neural-faint-review-confirmed-probe.json.

The raw request also contains unused active/action and roster fields. Next task:
minimize and recursively validate restoration history before destructive reset,
with mirrored rejection tests preserving fingerprint, observations and usability.
Valid history creates no actions and raw metadata stays out of logs/records; only
its existing opaque snapshot commitment enters lineage. Legacy compatibility limits
remain documented. Four changed files already covered; manifest/list/attestation
unchanged. Both coverage commands fail only digest drift; six self-tests pass.
Current digest300cfa84ccf97db8fb54653a02fe45c657c6c7ce45a4676448bfa60fcf7c0c02;
prior reviewed3b777601e68932a409271b7103a0013b21abbfcc9d8c4f25c0fd118f2dcfc4e2.
Stellar and wider lifecycle gaps remain; faithful_complete_episode:false unchanged.

### Terminal-history validation correction — implementation, 2026-09-24

Nested consumed fields are now validated before teardown, with structured
TerminalRequestHistoryValidationError code/path/reason and no private error values.
Minimal v1 writers retain only the own-roster fields consumed during restoration;
historical raw-v1 readers validate then drop unused action/roster data and canonicalize
Tera markers. Old raw-v1 fingerprints may migrate once; canonical round trips remain
stable. Missing-metadata legacy behavior remains. Valid history creates no actions
or raw public records. Faint semantics unchanged; separate acceptance remains pending.

Only env_manager.ts and illusion.test.ts changed. Parent build136 relevant TS tests
pass, including Python publication; prior20 Python evidence reused. Original five
malformed probes reject with unchanged fingerprints. Nested cases cover both owners,
live-state/branch preservation and continued request execution versus a twin; valid
migration/restoration tests preserve observations. Diff checks pass. Checkpoint has
source hashes and /tmp/neural-history-validation-* evidence.

Manifest/list/attestation untouched; existing list covers all affected source/tests.
Checker commands fail only on digest9a05263276c0f17e7c2f3b6baf77b874c48c07c0967b3858eb91d1fdd4a29016;
six synthetic self-tests pass. Next: review corrected minimal-v1 validation and
migration with the pending faint slice, then separately attest. Wider lifecycle
prerequisites and faithful_complete_episode:false remain unchanged.

### Faint/minimal-v1 restoration acceptance — 2026-09-24

Scoped acceptance closes the pending non-Stellar faint and terminal restoration
slice. Faint deactivates Tera while retaining known type and restoring observable
non-Tera typing; Illusion privacy and teammate/earlier-observation preservation hold.
Minimal-v1 validates consumed nested fields before teardown, returns structured
errors and preserves state/fingerprint/branch/continued choices on rejection.
Only necessary owner-roster fields persist. Terminal restoration creates no actions
or public raw history. Historical raw-v1 normalization may change identity: recapture
references and preserve historical records; old-reference/normalized-state pairing
rejects. Canonical round trips are deterministic and idempotent.

Four input hashes match. Reused build136 TS/prior20 Python and faint evidence;
fresh build18 Illusion tests (including Python publication) and3 coverage tests pass.
Independent review found one wall-clock-only flaky comparator; test-only normalization
now matches existing identity rules, with exact per-run prefix checks unchanged.
No production correction. Lineage probe and logs are in the current checkpoint.

Existing24-file list covers extractor, environment, helper and regressions; no
inclusion changes needed. Updated computed/reviewed digest:
`6aaddf2751640263f13fa29d4e95c1bfb0987bbf78e7274493a30b8126273c70`.
Removed resolved faint-Tera known gap; coverage checker and six self-tests pass.
This supersedes earlier pending/blocked dispositions only for this scoped slice.
Next: Stellar defensive typing correction with mirrored lifecycle/restore/publication
checks. Other fields, linked effects, Revival Blessing and broader episode fidelity
remain open. Keep faithful_complete_episode:false.

### Stellar defensive typing implementation — 2026-09-25; review pending

Pinned Pokemon.getTypes excludes Stellar from replacement defensive typing. Shared
resolveTypes now follows that distinction for ordinary species/Illusion projection,
keeping known Tera type and active flag separate. Own hidden Zoroark retains Dark;
opponent displayed Snorlax retains Normal until reveal, without leaking identity.
Public Stellar protocol evidence remains; opponent-private tera_type stays omitted.
No schema change. Temporary-type/Type-event reconstruction and private Stellar
attack counters remain outside this correction's scope.

Changed: battle_helpers.ts, tests/helpers/state_lifecycle.ts, tests/illusion.test.ts.
Parent build146 relevant TypeScript tests pass; focused28 Illusion tests pass. New
cases cover both actors, direct simulator types, Stellar activation, switch/drag,
reveal/faint, both-perspective privacy, exact immutable prefixes, restoration and
repeatable Python-validated publication. Existing Fire cases remain green; prior20
Python evidence reused. No semantic acceptance/attestation issued. Checkpoint has hashes.

Next: scoped review, then add battle_helpers.ts to the current24-file coverage list
and recompute/attest only if accepted. Helper/Illusion test files already hashed.
Manifest untouched. Current listed digest (excluding battle_helpers) is
f0893ed149ee786be29a8a3a03f3ae820a62dce0d5611637573e4095cd6bef1b;
checker commands fail digest drift, six synthetic self-tests pass. Prior attestation
6aaddf2751640263f13fa29d4e95c1bfb0987bbf78e7274493a30b8126273c70 remains.
Broader lifecycle prerequisites and faithful_complete_episode:false are unchanged.

### Ordinary Stellar defensive typing review — 2026-09-25; scoped acceptance

No blocking findings or production edits. Verified pinned getTypes and all shared
resolver callers. Both actors/perspectives cover activation, Illusion reveal,
switch/drag, faint, immutable prefixes, private identity and deterministic restoration/
Python publication. All three checkpoint hashes match; reused146 relevant TS/28
Illusion/prior20 Python evidence; fresh build16 targeted lifecycle checks pass.
Added battle_helpers.ts to25-file hashing; fixture helper/regressions already covered.
Computed/reviewed digest: 4db82b9bc57984bf051f03b201bf022e0744ba03c8840239adeded5d362f33c3.
Coverage checker, six drift self-tests and3 coverage tests pass. No schema change.
Temporary-type/Type-event reconstruction and Stellar offensive STAB/counters remain
excluded; faithful_complete_episode:false. PROJECT_STATUS stale rows reconciled.
Next: separate Windows ENV-001 validation using implementation commit
3ddc5fc3060e8da287425e4d08a71a2ffd77184a plus review-only manifest/docs changes;
checkpoint defines handoff. This is not complete-episode or environment acceptance.

### Working environment instructions — 2026-09-25

Documented successful macOS terminal Python3.9.6/Node24.21.0/npm11.19.0 and
recorded Windows neuralgpu Python3.11.14/Node24.15.0/npm11.12.1. Direct macOS
and Node-child checks resolve /Library/Developer/CommandLineTools/usr/bin/python3;
pytest8.4.2 is present. Windows pytest9.0.3 remains recorded evidence.
ENVIRONMENT_VALIDATION now separates stdlib/pytest simulator-record scope from
training/server dependencies, includes existing-environment commands, and explains
historical wrapper HEAD/install constraints. README links the instructions and
PROJECT_STATUS distinguishes existing-host success, selected cross-platform success,
fresh-machine recreation pending and separate training/data gates. No packages,
environment managers, source or attestations changed. Next substantive pipeline task:
bounded Revival Blessing request/target handling with scoped acceptance; retain
unsupported truncation until then and faithful_complete_episode:false. Fresh-machine
specification remains an independent pending gate.

### Bounded Revival Blessing implementation — 2026-09-25; review pending

Preserves addressed revival request evidence and fainted current-slot selection;
additive action/transition/record versions distinguish revival from switching.
Mirrored real Pawmot/Rabsca fixtures verify actor-only committed records, both
successor beliefs, restore/privacy/identity, public burn clearing and resumed play.
Build154 relevant TypeScript and27 Python checks pass; final focused7 revival
checks pass. Ordinary compatibility checks pass. No semantic acceptance issued;
coverage manifest unchanged and expected drift remains (ten synthetic self-tests pass).
Checkpoint lists hashes, source anchors, unsupported variants and required coverage
inclusion. Next: bounded revival semantic review; faithful_complete_episode:false.

### Bounded bench revival semantic review — scoped acceptance, 2026-09-25

No blocking findings or production/test corrections. All14 hashes matched; pinned
revival request/choice/execution, slot/fingerprint binding, schema disjointness,
owner privacy, public HP/status and candidate commitment reviewed. Reused154 TS/27
Python evidence; fresh build/seven revival regressions, seven Python rejection
probes and two exact split-HP probes pass. Both perspectives restore/replay and
advance beliefs; actor-only records publish after commitment; variants truncate.
Added both canonical codecs/tests, shared identity fixture and revival tests to
coverage (34 files); reconciled -heal bench grammar and source-qualified status clear.
Digest: 39ab09c90a564eaa80a3da3ff8275b8dcf01a7fbd79dcdece1b3945b68753ec8.
Checker, ten synthetic drift self-tests and three coverage tests pass. Historical
Windows/macOS comparison does not establish equality of this changed source.
Next: public temporary defensive-type lifecycle, starting with Soak/typechange.
Other lifecycle/linked/field gaps and unsupported revival variants remain;
faithful_complete_episode:false and separate training/data gates are unchanged.

### Soak public temporary defensive typing — implementation, 2026-09-25

Public typechange now persists across own-request refresh and Illusion reveal;
source-backed switch/drag/faint resets clear it. Stellar retains ordinary Water,
non-Stellar Tera takes precedence; already-Tera/Arceus/Silvally Soak failures do not
invent evidence. Private appearance map is rebuilt from protocol, with no schema
change or private simulator state exposure. Build and184 relevant tests pass,
including30 new mirrored Soak regressions and16 Python-validated record bundles.
Prior27 Python evidence reused for unchanged validators. Exact hashes/source anchors
and logs are in PIPELINE-002 checkpoint. Coverage checker fails expected source
drift; ten synthetic drift self-tests pass. Manifest/attestation unchanged; review
must include new soak.test.ts and shared typechange classification. Separate semantic
acceptance pending. Broader temporary typing remains open; faithful_complete_episode:false.

### Soak defensive typing semantic review — scoped acceptance, 2026-09-25

No blocking findings or production/test/schema corrections. Both file hashes and
prior 34-file computed digest match. Source establishes public appearance ownership,
request-independent temporary typing, Illusion reveal retention, switch/drag/faint
reset and Fire/Stellar precedence. Reused184 relevant tests/prior27 Python evidence;
fresh build/30 Soak cases and16 Python publication bundles pass. Added soak.test.ts
(35 hashed files), qualified protocol classifications without accepting generic
end semantics or other temporary types. Computed/reviewed digest:
`1a853d3a5266fad988027a8ee0609700cbd9f7a18a06ca71dc7991e9ba14e4b1`.
Checker, ten drift self-tests and three coverage tests pass. Pinned source unchanged.
Next: public added-type composition/lifecycle; real Soak then Forest's Curse gives
simulator/opponent Water+Grass but owner Water. This previously excluded gap remains
outside Soak acceptance. Checkpoint records reproduction and bounded next criteria.
Broader lifecycle and faithful publication remain open; faithful_complete_episode:false.

### Public added-type composition — implementation, 2026-09-25

Separate appearance-bound ordinary replacement and added slot now compose both
views across requests/replay. Added slot replaces instead of accumulating; Soak and
Tera remove it. Switch/drag/faint clearing and Illusion ownership/privacy tested.
Build/204 relevant TypeScript tests pass, including 20 new mirrored cases and20 new
Python-validated publication bundles. Prior27 Python tests reused for unchanged
validators. No schema migration. Manifest unchanged; checker reports expected drift
398a3ad465e0b55ebf6a35974feb673c216647e5048cd37083bf733c2d3c059b;
ten synthetic self-tests pass. Review must hash added_types.test.ts and reconcile
classification before attestation. Checkpoint contains exact hashes and source
anchors. Generic expiry/copy effects and older two-type training/live consumers
remain excluded. faithful_complete_episode:false; next is scoped semantic review.

### Public added-type composition review — scoped acceptance, 2026-09-25

No blocking findings or production/test/schema corrections. Both hashes and35-file
computed digest match. Pinned semantics support separate replacement/one added slot,
ordering/repetition, reset/Tera behavior and Illusion appearance ownership. Reused204
relevant tests/prior27 Python evidence; fresh build20 added-type cases including 20
Python publication validations pass. Three-type arrays survive observation cloning
and JSON bundle/identity validation; Python DATA-001 output references observations,
not a new feature tensor. Legacy two-slot training/live consumers remain excluded.
Added added_types.test.ts (36 hashed files); qualified protocol classifications.
Computed/reviewed digest:
`8dca73b1b49f2dc8a8d5a2e3e1a4b7d43f2e976a64e36f2dde3192561bb0dc09`.
Checker, ten drift self-tests, three coverage tests and diff checks pass. Next:
Transform public copied typing/refresh/restoration. Fresh pinned probe gives Mew
Fire/Flying/Grass in simulator/opponent but Psychic in owner view after copying
Grass-added Charizard. Checkpoint has reproduction and source anchors. Copy/expiry
and broader lifecycle remain unaccepted; faithful_complete_episode:false.

### Transform defensive typing — implementation, 2026-09-25

Copies public ordinary and added types separately at -transform, preserving caller
Tera and original roster identity without mutable target links. Requests/restoration
retain copy; switch/drag/faint restore original species. Build226 relevant tests pass,
including22 new mirrored cases and16 Python publication bundles. Prior27 Python
validator evidence reused. No schemas/private metadata added. Non-typing Transform,
Type-event/Roost and legacy two-type training/live consumers remain excluded.
Manifest unchanged; expected drift bee7b0975b2a8afc4cabfc8f1fd2b7e5858eeb615ec6699f81209564ac4d738b.
Ten synthetic drift self-tests pass. Checkpoint records hashes and review criteria;
next is scoped semantic review and transform_types.test.ts hashing/attestation.
faithful_complete_episode:false remains.

### Transform defensive typing review — scoped acceptance, 2026-09-25

No blocking findings or production/test/schema corrections. Both hashes and36-file
computed digest match; reused226 relevant tests/prior27 Python evidence. Fresh
build22 mirrored Transform cases including16 Python publication validations pass.
Pinned copy boundary, ordinary/added isolation, request/replay persistence,
identity/reset, caller/target Tera and privacy reviewed. Three-type arrays survive
serialization/identity checks. Added transform_types.test.ts (37 hashed files);
qualified -transform/lifecycle classifications without accepting unrelated fields.
Computed/reviewed digest:
`79a83f372d28e8c83ca32a00df8d44eb2479a15d1fd7cac4bd9ca5e66a33f804`.
Checker, ten drift self-tests, three coverage tests and diff checks pass. Next:
public Transform boost copying. Fresh pinned probe copies +2 Attack in simulator
but both caller views report empty boosts; checkpoint gives exact steps/source.
This excluded non-typing correction is separate from current scoped acceptance.
Broader lifecycle/features remain unaccepted; faithful_complete_episode:false.

### Transform public boost copying — implementation, 2026-09-25

Fresh target public-stage map replaces caller stages at -transform; absent target
keys zero stale caller stages and explicit zeros remain. No mutable links or synthetic
deltas. Existing request/replay/reset paths preserved. Build244 relevant tests pass,
including18 new mirrored cases, exact-prefix Intimidate ordering and20 new Python
publication validations. Prior27 Python evidence reused. Both raw views corrected;
self records publish copied stages, accepted opponent omission unchanged. Manifest
unchanged; expected drift c5fb1527cf0d1d2f8da8f1ab61c423fa3a6333918e53dfb89a289b13cc183288.
Ten synthetic drift checks pass. Checkpoint has exact hashes/review criteria.
Next scoped review/test hashing/attestation; selective clear and unrelated Transform
mechanics remain excluded. faithful_complete_episode:false.

### Public Transform boost copying review — scoped acceptance, 2026-09-25

No blocking findings or production/test/schema corrections. Both hashes and37-file
computed digest match. Pinned all-stage assignment, sparse/explicit zeros, negative
stages, event order, independent maps, request/replay and clearing reviewed. Reused244
relevant tests/prior27 Python evidence; fresh build18 cases/20 Python validations pass.
Both raw views correct; caller-self published stages preserved. Opponent publication
omits stages: representation limitation, not privacy requirement. Corrected contract
wording without changing v1 serialization. Added transform_boosts.test.ts (38 files)
and qualified -transform classification. Computed/reviewed digest:
`16819a7d19f47b6a412a8a9ed540cde284ac524df290cc5ac52d4293082eaab7`.
Checker, ten drift self-tests, three coverage tests and diff checks pass. Next:
public opponent-stage publication under explicit version/identity compatibility,
with no blanket private-field copying. Feature/faithful-publication acceptance
requires closing that representation gap; other semantic gaps remain separate.
faithful_complete_episode:false.


## 2026-09-25 — Public opponent-stage v2 implementation; review pending

Opt-in observable v2 adds exact-prefix opponent public_boosts with explicit unknown/zero
semantics. V1 default and original identities remain unchanged. Nested versions flow
through beliefs, transitions and Python schema fingerprints; mixed/unknown versions
reject. Historical v1 missing reference versions remain compatible. No in-place
migration; new evidence-backed representation creates new observation/belief/record
identities, while simulator trajectory IDs may remain shared. Helpers reconstruct
public evidence independently in TS/Python; unsupported operations fail closed.
Build and 265 relevant TS/27 Python pass;21 new tests include 20 actual v2 Python bundles
and 10 invalid-bundle rejections. Accepted raw extraction/typing behavior unchanged.
See checkpoint for exact hashes, commands, privacy/restoration and Illusion evidence.
Checker detects expected drift (653051a2ad2dcf9778c4df63a6dc92aefbfc361a441278430ad9dff48be7575c); ten synthetic self-tests pass. Manifest
and attestation unchanged: add new helpers/tests and review bounded classifications
before recomputing/attesting. Read-only consumer review used requested gpt-6-astra/high;
effective settings unavailable; no delegated edits. Next: scoped v2 semantic review.
Selective clears and broader faithful publication remain open; faithful_complete_episode:false.


## 2026-09-25 — Public opponent-stage v2 review blocked

Nine checkpoint hashes match; reused 265 TS/27 Python evidence, fresh build and 21
public-stage tests pass (20 Python publications/10 invalid-bundle checks). Default v1,
explicit v2, prefix evidence and bounded lifecycle/restoration checks remain sound in
tested paths, but publication acceptance is blocked. A real one-transition v2 bundle
can be relabeled v1 with public_boosts removed and stale observation/belief IDs retained:
Python accepts; TS rejects. Repairing observation IDs alone still lets stale belief
IDs through Python. See checkpoint and artifacts/validation/v2-public-stages-review-2026-09-25
for executable reproduction/output. Require content-identity checks for observations
and beliefs across publication versions with explicit bounded historical compatibility;
do not rewrite old IDs. No production or manifest changes; no attestation. Computed
digest 653051a2ad2dcf9778c4df63a6dc92aefbfc361a441278430ad9dff48be7575c remains
unattested. Checker detects drift; ten synthetic self-tests pass. Hashing must add both
public_boosts helpers, public_stages tests and changed belief_state tests after correction.
Next: fix downgrade loophole, then repeat review. faithful_complete_episode:false.


## 2026-09-25 — Python content identity correction implemented; review pending

Both previously reproduced downgrade paths now reject before record creation. Shared
Python TS-compatible canonicalization verifies input/successor observation and belief
IDs independent of schema labels; checks nested candidate/evidence IDs and reference
joins. Valid v1/v2 records retain supplied identities. Legacy references may omit only
the v1 schema version; omission is hashed as absent. ID-only/partial references and
arbitrary synthetic IDs have no production exemption; unit fixtures now use consistent
content IDs. No historical records/lineage rewritten. DATA-001 hashes unchanged.
Build and 268 relevant TS/28 Python pass, including cross-runtime real v1/v2 bundles,
both downgrade cases, nested tampering, Unicode/number/absence/null parity and existing
lifecycle publication. Independent 99948-number probe has zero mismatches. Checkpoint
records exact hashes/commands and bounded historical-content limitation. New helpers/tests
require coverage inclusion; manifest untouched and checker detects expected drift. Ten
synthetic self-tests pass. Next: separate semantic review of correction and combined v2
publication; faithful_complete_episode:false.


## 2026-09-25 — Combined identity/v2 review: historical reference domain blocker

Hashes match; reused 268 TS/28 Python evidence; fresh build/24 focused tests pass. Both
original downgrade reproductions independently reject before publication. Fully rehashed
false public stages reject, so hashes do not bypass prefix evidence. Legacy exception
remains narrow: omitted version only for otherwise supported v1 references; no supplied
identities are repaired. New bounded blocker: older observation_history reference
source_kind/snapshot_phase values are not domain-validated in Python. On a real second
transition, set either field to invalid in both beliefs and rehash outer IDs; Python
publishes, TS rejects. Durable reproduction/output under
artifacts/validation/identity-history-review-2026-09-25/. Correct the Python history
domains to match TS and add two-transition regressions, retaining v1 omission compatibility.
No production/manifest corrections or attestation. Expected digest drift remains; ten
synthetic self-tests pass. Next: bounded historical reference domain correction, then
combined review. faithful_complete_episode:false.


## 2026-09-25 — Historical-reference fields corrected; combined review pending

Shared Python current/history validation enforces exact keys, supported homogeneous
versions, strict ID/hash strings, source/phase domains, non-boolean safe nonnegative
cursors and prefix/history joins. Removed unsafe preliminary version-only loop. Legacy
v1 omission remains explicit and hash-preserving; no values coerced or repaired. TS
closes first-history -1 and trailing-newline ID edges within the same object contract.
Both original domain failures now reject before publication. Build/78 targeted TS/28
Python pass; table-driven two-transition v1/v2 cases exercise every reference position,
invalid field types/domains/joins, valid domains, legacy omission and unchanged IDs.
Matching prior 268-test unaffected evidence reused. Checkpoint records source hashes and
commands. No manifest update or attestation; expected digest drift and ten passing
synthetic self-tests. Next: separate combined reference/identity/v2 review.
faithful_complete_episode:false.


## 2026-09-25 — Combined historical-reference/identity/v2 publication accepted

No blocking findings or production/test corrections. All checkpoint hashes match;
fresh build/26 identity/public-stage cases pass. Independently reproduced both malformed
historical fields with recomputed outer hashes: reject before publication in both
runtimes; valid control passes. Both stale-ID downgrade paths and fully rehashed false
stages reject. Complete six-field/current/history joins and strict cursor/ID guards
reviewed; v1 default and narrow Python-only omitted-version legacy compatibility retain
valid identities. Matching 78 TS/28 Python and prior 268 unaffected evidence reused.
Added both public-stage helpers, Python identity helper and three TS tests to hashing
(44 files); qualified boost/Transform publication and excluded selective clearing.
Computed/reviewed digest 96e85e8903e00b681ce029b58d69d72c284595102bc1ffee855894779fcee11d.
Checker, ten self-tests, three coverage tests and diff checks pass. Historical pending/
blocked dispositions are superseded within this scope only. Checkpoint binds HEAD plus
local changes, documents review evidence and the next bounded task: selective positive/
negative stage clearing. No feature or faithful-publication readiness claim;
faithful_complete_episode:false.


## 2026-09-25 — selective stage clearing implementation (review pending)

Raw and TS/Python v2 public replay now clear only the selected sign, preserving opposite
signs/zero/unknown. White Herb tags and narrow Spectral Thief raw-only animation supported.
Build, 92 relevant TS tests, 28 Python tests and diff checks pass; new tests include 36
actual Python publication checks. Coverage flags changed digest and added `-anim`;
ten synthetic self-tests pass. No attestation/classification changes. Review exact file
hashes, compatibility and next action in the PIPELINE-002 current checkpoint. Keep
`faithful_complete_episode:false`; prior accepted evidence is retained below that checkpoint.


## 2026-09-25 — selective stage clearing scoped accepted

Six hashes match; no source/test correction. Raw and TS/Python v2 selected-sign clearing,
conservative unknowns, exact White Herb/Z tags and narrow raw-only Spectral Thief animation
reviewed against pinned source. V1 default/identities unchanged; no historical migration.
Fresh build17 focused cases, valid publication and correctly rehashed false-stage rejection
pass both runtimes. Matching92 TS/28 Python evidence reused. Added selective regression
hashing (45 files), reviewed classifications and attested digest `15e0e2b5c8b77b615a420be79634f4d3fc01924a5723eb02ddcc040e867064a9`.
Checker, ten drift self-tests, three coverage tests and diff checks pass. Next: bounded
Psych Up stage copying, excluding its critical-hit volatiles and other boost mechanics.
Current PIPELINE-002 checkpoint holds exact reviewed state/evidence. faithful_complete_episode:false.


## 2026-09-25 — bounded Psych Up stage implementation; review pending

First copyboost identifier receives second's independent public stage snapshot; replace
all evidence, preserve unknowns, accept exact Psych Up tag only. Raw and TS/Python v2
implemented; Costar, other boost mechanics and critical-hit volatile changes remain
excluded. Build/101 TS/28 Python pass, including28 new Python publication checks and20
fully rehashed false-stage rejections. Coverage/source token drift expected; ten drift
self-tests pass. No attestation update. Exact files/hashes, commands and review scope in
current PIPELINE-002 checkpoint. faithful_complete_episode:false.


## 2026-09-25 — Psych Up review blocked; attestation withheld

All five hashes match. Valid stage semantics pass build/nine tests,28 publication/20
false-stage rejection checks and six fresh mirrored lifecycle/restoration probes.
But missing, garbage and empty-name copy recipients bypass evidence-helper grammar;
Python publishes fully rehashed actual v2 bundles while TS rejects. Reproduction:
artifacts/validation/psych-up-review-2026-09-25/reproduce.py (control/artifacts/results
alongside). Fix both helper grammar guards before player-side filtering, including both
full identifiers and exact tag/count, then add publication regressions. No source/test
or manifest edits; new test hashing/classification deferred. Expected coverage drift;
ten self-tests pass. Current checkpoint contains exact locations/evidence.
faithful_complete_episode:false.


## 2026-09-25 — Psych Up pre-filter grammar corrected; review pending

TS/Python evidence helpers validate exact Psych Up count/tag and both complete identifiers
before side routing. Python v1/v2 publication uses the shared guard; valid v1 identities
unchanged. Valid unresolved roster identities retain unknown semantics. Build39 focused
TS/28 Python pass;200 rehashed malformed cases verify identities then reject, and three
original artifacts reject before CLI output. Existing simulator/publication/false-stage
evidence refreshed. No copying/identity/snapshot changes; critical-hit volatiles excluded.
Manifest/attestation untouched; expected token/digest drift and ten passing self-tests.
Current checkpoint records hashes, fixtures and combined review scope.
faithful_complete_episode:false.


## 2026-09-25 — Psych Up combined review blocked by publication alias

Canonical guards pass; independent original3 failures now reject with verified identities
and no output. Fresh build13 tests pass (200 rehashed matrix,28 publications,20 false-stage
rejections); matching39 TS/28 Python reused. Bare copyboost still bypasses Python v1 guard
and normalizes in v2, whereas TS rejects; both versions reproduced publishing fully
rehashed alias bundles. Evidence: artifacts/validation/psych-up-alias-review-2026-09-25/.
Next reject unsupported publication alias in both versions and extend matrix. No source,
test, classification or attestation edits. Expected coverage drift; ten self-tests pass.
faithful_complete_episode:false; critical-hit volatiles excluded.


## 2026-09-25 — bare copyboost publication guard fixed; review pending

Python prefix validation rejects bare copyboost in v1/v2 before stage reconstruction.
Canonical token/grammar, helper aliases, unresolved evidence and historical identities
unchanged. Build19 TS/28 Python pass;408 rehashed rejection matrix,12 supported matrix
controls, original canonical3 and alias2 CLI failures now reject without output. Valid
saved controls retain IDs. Five unchanged source/test hashes match prior copying evidence.
Only pipeline_record.py and psych_up_validation.test.ts changed in code/tests. Manifest
and attestation untouched; expected drift, ten passing self-tests. Current checkpoint
contains exact hashes/logs/review scope. faithful_complete_episode:false.


## 2026-09-25 — combined Psych Up stages/grammar scoped accepted

No blockers or production/test corrections. Seven hashes match. Fresh build14 cases
pass including408 rehashed rejects,12 controls,28 publications,20 false-stage rejects;
matching19 TS/28 Python and prior lifecycle evidence reused. Independently five saved
failures verify IDs then reject without output; v1/v2 controls retain identities.
Canonical copy direction/replacement/unknowns and pre-filter grammar reviewed; bare
alias rejected at publication, internal aliases unchanged. Added2 tests/7 fixtures
(54 files) and attested `d5e51397777285eb10e702d5998bbd7ccf1de371180301129406e0c2cbb28ae3`.
Checker, ten drift self-tests, three coverage tests and diff checks pass. Critical-hit
volatiles/Costar/other boost mechanics excluded. Next: bounded Topsy-Turvy inversion.
Current checkpoint binds exact reviewed state and evidence. faithful_complete_episode:false.


## 2026-09-25 — bounded Topsy-Turvy inversion implemented; review pending

Pinned target-only nonzero negation implemented raw and TS/Python v2; zero/unknown remain
distinct. Exact grammar validates before routing; bare alias rejects in both publication
versions. Build79 TS/28 Python pass, including28 new publications,232 fully rehashed
malformed/alias rejects and4 false-stage rejections. Historical valid controls unchanged.
Five sources/two tests changed; manifest untouched, expected token/digest drift, ten
self-tests pass. Current checkpoint records hashes/source/probes and separate review
scope. Rigged Dice, swap/Baton Pass/critical-hit volatiles excluded.
faithful_complete_episode:false.


## 2026-09-25 — protocol validation/publication boundary review blocked

On macOS, the independent review reproduced fully rehashed Python publications
for `|turn|١` and `|request|{"rqid":null}` in all 16 v1/v2, p1/p2, input/
successor combinations; TypeScript rejects both. Both loaders accept a
structurally malformed shared contract, both reject source-emitted
`detailschange`/extended `-endability` forms, and the TS projector drops
malformed `request` plus unclassified `tier` before validation. Grammar remains
permissive for several supported commands, and a fixture token label is wrong.
The rehashed unknown-command case still rejects after identity joins with no
output; targeted rollback, raw-only/privacy, historical-reference and
`-singlemove` stop regressions pass. Bounded Topsy-Turvy remains limited to its
reviewed base semantics and exact tag.

The shared boundary is not accepted. Preserved stored/reviewed digest
`d5e51397777285eb10e702d5998bbd7ccf1de371180301129406e0c2cbb28ae3`; current
unreviewed local digest is
`9793ca11d6ac3c696794027e0cab4150fe970bc52ee1c5fce59dcf124102b140`. Coverage
drift self-tests pass; the checker exits on the expected unreviewed digest
change. See the current [PIPELINE-002 checkpoint](refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md),
[mechanics assessment](refactor/MECHANICAL-REPRESENTATION-ASSESSMENT-2026-09-25.md),
and `artifacts/validation/protocol-boundary-review-2026-09-25/`. Keep
`faithful_complete_episode:false`; remediate this boundary before scanner
expansion and operative format coverage.
