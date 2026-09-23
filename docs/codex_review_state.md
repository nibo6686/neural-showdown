# Codex Review State

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

- `READY_FOR_REFACTOR: YES`.
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
