# SIM-COVERAGE-001 Progress

## Current repository state

- Branch: `refactor/state-001-observable-state`
- HEAD: `b9b3eb06d362963bb1fa2da21d7c471a84df262c`
- Existing modified/untracked files were preserved; no cleanup, staging, or commit was performed.
- Pre-existing working-tree paths include `.gitignore`, Observable/PIPELINE contracts and source/tests, `sim-core/package.json`, and `tests/fixtures/observable_protocol_terminal_v1.json`. New audit-owned paths are listed below.
- Aggregate status files were not edited. No sensitive message artifact was opened, searched, or hashed.

## Acceptance criteria status

- [x] Verify repository rules, branch/HEAD, package declaration, lock entry, installed metadata, format metadata, and existing coverage tool.
- [x] Inventory Gen 9 condition/effect registries and relevant mutable simulator state, with source symbols, lifecycle, visibility, contract treatment, legality, raw evidence, tests, and per-entry classification.
- [x] Inventory parser boundary and literal emitters; review public, split, side-channel, computed, and indirect emission paths; reconcile parser and emitter token sets.
- [x] Compare simulator coverage with ObservableBattleState, BeliefState, CanonicalAction, SeededTransition, DATA-001, PIPELINE-001, and proposed FEATURE-001.
- [x] Add fail-closed simulator and local-source drift checks with distinct semantic-review digests.
- [x] Run focused simulator, parser, extractor, action, and pipeline tests plus drift validation.
- [x] Keep PIPELINE-001 and FEATURE-001 unaccepted; report semantic blockers below.

## Delegated source audits

- `condition_lifecycle_inventory` owned `/private/tmp/sim_coverage_conditions.md` (read-only source audit).
- `protocol_grammar_inventory` owned `/private/tmp/sim_coverage_protocol.md` (read-only grammar/emission audit).
- Parent verified key claims against pinned package source, local parser/extractor, and focused tests. Parent owns integration artifacts and final review.

## Verified provenance and scope

- `pokemon-showdown` declaration, package-lock entry, and installed metadata agree on exact version `0.11.10`; lock entry has resolved tarball and integrity fields.
- Installed package is not a Git checkout, so no upstream source commit is available. The lock integrity does not prove the installed unpacked tree matches the tarball. Clean-install verification was unavailable under the no-install/no-network constraints.
- Format: `gen9randombattle`, Gen 9, singles, random teams, two players. Six generated Pokémon is an expectation; emitted `teamsize` is authoritative per battle.
- Condition inventories: 33 Gen 9 condition registry IDs; 55 direct move volatile IDs; 6 secondary volatile IDs (59 union, with 2 overlaps); 46 literal callback-derived volatile identifiers; 15 side-condition IDs; 8 pseudo-weather; 4 terrain; 8 weather IDs. The classified condition/effect table contains 142 IDs across overlapping registries.
- Protocol boundary: 111 parser tokens. Package-wide TypeScript static scan: 86 literal `add()` emitter tokens. They are different scopes; computed `msg`, `addSplit`, `addMove` mutation, private `Side.send`/requests, and stream routing were reviewed separately. Five `addVolatile` call sites are dynamic and protected by source digest rather than inferred argument IDs.

## Findings and blockers

- Confusion has public `-start`/`-end` lifecycle evidence, while duration is private. `-singleturn` remains validated raw evidence and is not projected as a persistent volatile. Volatile IDs are currently an untyped public-presence list; source/counter/lock/switch-expiry semantics are not fully represented.
- Side condition count maps do not reconstruct every layer/duration callback. Weather, terrain, and pseudo-weather are coarse IDs; private duration/source/suppression counters are not player-visible features.
- Request JSON is the acting side's legal-action authority and is private. Opponent roster slots are partial/unknown, not nonexistent. Status source distinguishes request-known absence from unknown. Both perspectives are tested for public state and request privacy.
- `move` target omission is valid for self-target moves. CanonicalAction v1 does not support targeted/multi-active requests; no feature/action expansion was made.
- Three generic parser aliases (`clearstatus`, `-clearstatus`, `nothing`) have no supported-format emitter path established by examined source. The parser only checks nonempty payload. They remain classification `unknown` and raw-only; seeing one in a supported-format collection is a stop-and-review condition. `-nothing` is a distinct, source-emitted no-payload token.
- Dynamic/private source paths cannot be semantically enumerated by a token scanner alone. Simulator and local coverage source digests stop unreviewed changes; they do not establish meanings. Other-format source is outside scope.
- The installed tree cannot be independently compared to the lock tarball here. PIPELINE-001 acceptance and FEATURE-001 revision remain separate work.

## Durable artifacts and changes

- `docs/contracts/SIMULATOR_COVERAGE.md`: source-backed coverage narrative, limitations, contract implications, and FEATURE-001 revision requirements.
- `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json`: v2 machine inventory with 142 individually classified IDs, protocol grammars, emitter references/reconciliation, provenance and review status.
- `sim-core/scripts/check-simulator-coverage.cjs`: pin/format/registry/parser/emitter checks, complete-manifest checks, simulator and local-source hashes, and synthetic drift self-tests.
- Existing modified parser/test files and sanitized fixture from the worktree were preserved; focused tests were run against them. No aggregate status file was changed.

## Validation performed in this continuation

- `npm run build` from `sim-core/`: passed.
- `node --test dist/tests/simulator_coverage.test.js dist/tests/state_extractor.test.js dist/tests/observable_state.test.js dist/tests/action_codec.test.js dist/tests/pipeline_integration.test.js`: 38 passed, 0 failed.
- `npm run check:simulator-coverage`: passed; 142 classified IDs, 111 parser tokens, 86 literal emitter tokens.
- `node scripts/check-simulator-coverage.cjs --self-test`: passed new condition/protocol/emitter detection, missing classification, simulator digest-only review mismatch, and local digest-only review mismatch.
- `git diff --check`: passed.

## Project documentation synchronization — 2026-09-24

- Added `docs/PROJECT_STATUS.md` as the current concise gate index.
- Updated README and active refactor/control, contract, architecture, state/action,
  model/data, and testing docs to distinguish accepted lower-level contracts
  from unresolved dataset/model readiness.
- Corrected DATASET_LINEAGE's stale acceptance header and stale ACTION-001
  rollback wording; labeled earlier continuation/readiness snapshots as
  historical where needed.
- Added current-status pointers to active historical gate summaries without
  rewriting their dated experiment results.
- Preserved dated review history and unrelated worktree changes. No new tests
  were run for this documentation-only synchronization.

## Scoped semantic review addendum — 2026-09-24

- Independent read-only source review and parent integration review covered
  the changed files in `local_coverage_sources.files`: move actor/target/tag
  forms against pinned Showdown source, alias-stop points in TypeScript and
  Python publication, and rejected-candidate state/lineage behavior. The
  resulting reviewed digest is
  `479a096563318af86addd64dd39d445c56e8c5b4d9c8ba0a1c0e100b3c3861d2`.
- The coverage manifest's current and reviewed local digests now match. The
  simulator source-tree digest did not change. This review attests the listed
  local source, not all condition/effect lifecycles, tarball provenance, other
  formats, FEATURE-001 semantics, or whole-work-item completeness.
- Aliases remain classified `unknown`; publication fails with a structured
  diagnostic. `-nothing` remains distinct and raw-only based on the pinned
  Gen 9 Splash emitter.
- PIPELINE-001 is now accepted for explicit v1 joint-actionable scope. It does
  not change the SIM-COVERAGE lifecycle gaps or PIPELINE-002 progression
  blockers. Fresh coverage checker and all six synthetic self-tests pass.
- Fresh validation on 2026-09-24: TypeScript focused suite 42/42; Python
  record/lineage suite 18/18; build passed. See the task-specific pipeline
  correctness checkpoint for exact commands and the natural rejection trace.

## Prohibited-operation confirmation

No network, install, Git LFS, checkpoint/replay access, dataset generation, training, target selection, cleanup/deletion, broad staging, or commit occurred. Sensitive message files were not read, searched, hashed, quoted, or reproduced.
