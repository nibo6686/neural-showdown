# Pipeline Correctness Task Checkpoint

Date: 2026-09-24

## Repository snapshot

- Branch: `refactor/state-001-observable-state`
- HEAD: `b9b3eb06d362963bb1fa2da21d7c471a84df262c`
- The worktree was already substantially modified before this task. Preserve
  all unrelated edits and untracked artifacts; do not broadly stage, clean,
  commit, or load checkpoints.
- No applicable `AGENTS.md` was found in the workspace or its parent chain.
- Read the current project status, agent protocol, work items, definition of
  done, continuation note, review-state log, and state/action/transition,
  pipeline, coverage, and lineage contracts. Independent review artifacts are
  under `/Users/nbolger/Documents/Codex/2026-09-24/files-mentioned-by-the-user-neural/outputs/`.

## Task scope and assignments

The parent owns implementation integration, aggregate status/documentation,
verification, and final review. One read-only subagent is investigating the
pinned Showdown move-record grammar and may not edit files. No package install,
network access, replay acquisition, collection, feature extraction, training,
or checkpoint work is in scope.

Required focused work:

1. Make random-controller terminal verification reproducible with explicit
   controller RNG ownership, preserve legacy defaults, and add seed/config
   regressions.
2. Correct move-record grammar from pinned simulator source, covering valid
   target identifiers, omitted targets, optional tags, and malformed input;
   `[notarget]` must retain its own meaning.
3. Make `clearstatus`, `-clearstatus`, and `nothing` fail closed at the actual
   pipeline publication boundary with a structured diagnostic and committed
   boundary/lineage preservation. Keep `-nothing` distinct and preserve known
   raw-only grammar.
4. Define acceptance requirements for one-sided forced switch, waiting, and
   requestless progression; investigate one bounded natural post-preflight
   simulator rejection, document the evidence/decision if none is admissible.
5. Update goals, sequence, ENV-001 remediation planning, separate dataset,
   model, and product-release milestones, evidence map for later West Monroe
   review, and this continuation checkpoint. PIPELINE-001 and FEATURE-001 stay
   unaccepted.

## Evidence collected so far

- Independent review rebuilt with `npm run build` successfully and reported
  37 passed / 1 failed in the required 38-test selection. Failure was a real
  terminal projection rejecting simulator-emitted targets in `p1: ...` form.
- Independent probe notes recorded two failures and three passes across five
  terminal random-controller runs; `sim-core/src/baselines/random.ts` uses
  `Math.random()` independently of the simulator seed.
- Probe notes showed the three unresolved aliases passed both pipeline
  projection APIs when synthetically appended. This did not exercise a
  collector write.
- Independent checker results: 142 condition/effect IDs, 111 parser tokens,
  86 literal emitter tokens; drift checker and self-tests passed. Counts do not
  prove semantic lifecycle coverage.
- Existing pipeline rejects some one-sided forced-switch, waiting, and
  requestless boundaries; the real forced-switch regression already documents
  rejection. No admissible natural post-preflight simulator rejection is yet
  established.
- The parent has now implemented the controller RNG seam, move-record grammar,
  structured alias diagnostics, pipeline guards, and focused regressions.

## Source-review chunk completed

- Read-only source memo confirmed `BattleActions.runMove` forms move records from
  `Pokemon.toString()` (`sim-core/node_modules/pokemon-showdown/sim/battle-actions.ts:446-461`)
  and `Battle.addMove` joins the fields (`sim/.../battle.ts:3046-3049`).
- `Pokemon.toString()` emits `p1a: ...` for active slots and `p1: ...` for
  non-active Pokémon (`sim/.../pokemon.ts:504-512`). The move target validator
  therefore needs a move-specific Pokemon reference grammar; the actor remains
  an active-position identifier.
- `BattleActions.useMoveInner` passes `${target}` to `addMove`; a null target
  serializes as literal `null`, then the no-target branch appends `[notarget]`
  before returning (`battle-actions.ts:412-462`). The parser accepts `null`
  only with that exact trailing tag. This is distinct from interpreting the
  tag itself as a target, which remains invalid.
- `[notarget]` is appended by `attrLastMove` as trailing metadata
  (`battle-actions.ts:459-462,507-509`), and `[still]` clears the target slot
  before adding a tag (`battle.ts:3052-3067`). The protocol calls for optional
  target text and says side-target moves may name a fainted Pokémon
  (`sim/SIM-PROTOCOL.md:230-252`).
- Gen 9 `-nothing` has a concrete source path: Splash's `onHit` callback emits
  `this.add('-nothing')` (`sim-core/node_modules/pokemon-showdown/data/moves.ts:18380-18384`).
  It remains valid, no-payload raw evidence. This is distinct from unresolved
  generic `nothing`.
- The transition runner validates canonical actions against both live requests
  before submission (`sim-core/src/env_manager.ts:459-485`). Simulator choice
  errors are recorded only after a rejected/unavailable choice
  (`:216-245`). Existing postflight rejection coverage explicitly injects a
  diagnostic (`sim-core/tests/pipeline_integration.test.ts:182-198`), so it is
  not natural-rejection evidence.
- At the close of this read-only source-review chunk, no production files had
  been edited; implementation is recorded below.

## Implementation and first validation chunk

- `RandomBaselineAgent` accepts an injectable RNG whose legacy default still
  calls global `Math.random()`; `ControllerSpec.random_seed` creates separate
  p1/p2 uint32 random streams without changing the simulator's four-word seed.
- Move targets now accept active or non-active Pokémon idents, keep actor
  validation active-only, allow omitted/empty target fields, accept literal
  `null` only with `[notarget]`, and validate trailing bracket tags. The tag
  itself is never accepted as a target.
- Pipeline prefix and step-result projection now reject the three unresolved
  aliases with `pipeline/v1/unresolved-protocol-alias` plus a versioned
  diagnostic containing the input record index and command. `-nothing` remains
  a separate supported no-payload record.
- The Python `pipeline_record` publication boundary now independently rejects
  those aliases in input or successor prefixes before DATA-001 record creation;
  its exception and one-shot CLI carry a matching structured diagnostic.
- Regressions cover both captured target forms, valid/malformed target/tag
  variants, real terminal-trace repeatability, all three alias commands at both
  projection entry points, raw-only accepted records, and session committed
  boundary/lineage preservation when a synthetic unknown alias reaches the
  candidate.
- Validation attempt 1: `npm run build --prefix sim-core` passed. The requested
  focused command ran 41 tests: 40 passed, 1 failed because a new diagnostic
  index assertion compared raw-output and sanitized-prefix indices. The test was
  corrected as recorded below.

## Corrected verification and bounded rejection investigation

- Fresh validation passed: `npm run build --prefix sim-core`; then
  `node --test sim-core/dist/tests/simulator_coverage.test.js
  sim-core/dist/tests/state_extractor.test.js
  sim-core/dist/tests/observable_state.test.js
  sim-core/dist/tests/action_codec.test.js
  sim-core/dist/tests/pipeline_integration.test.js` — 41 passed, 0 failed.
  The integration test ran the Python `neural.pipeline_record` validator in
  fresh subprocesses for both perspectives.
- After adding the Python record-creation guard and CLI structured diagnostic,
  `PYTHONPATH="$PWD/trainer/src" python3 -m pytest
  trainer/tests/test_pipeline_record.py trainer/tests/test_dataset_lineage.py
  -q` passed 18/18.
- `npm run check:simulator-coverage --prefix sim-core` exited 1 with
  `Local coverage source digest changed: dbbe5bd3f03cd4c7eeef6097d8618c5614c0cdd155ff9a980fff1f06dfbee502`.
- `node sim-core/scripts/check-simulator-coverage.cjs --self-test` reported all
  six synthetic drift assertions passed, then exited 1 on that same local
  source digest mismatch. The reviewed digest was not refreshed. A separate
  semantic review of the changed source/tests is required before the manifest
  can attest this new digest.
- Bounded natural-rejection probe: `gen9randombattle`, simulator seed
  `[101, 202, 303, 404]`, every Cartesian pair from each side's 13-entry
  initial canonical action index space (169 valid legal pairs). Each trial
  created a fresh pipeline session, passed canonical preflight, and recorded
  whether `pipeline/v1/rejected-action` occurred. Result: 169 accepted
  transitions, 0 natural post-preflight simulator rejections. This single-seed
  result is bounded evidence, not proof of impossibility; the acceptance
  decision remains open. The existing injected-rejection test remains labeled
  injected.

## Source-backed null-target grammar chunk

- After the first passing tests, a targeted read of pinned
  `BattleActions.useMoveInner` showed that the emitted target string is
  interpolated before the no-target branch, so a null target becomes the
  literal `null` and then receives `[notarget]`. This supplements the captured
  non-active target case where `[notarget]` is attached after a valid
  `p2: ...` target.
- Added exact acceptance for `null|[notarget]`; `null` without the marker or
  with a different tag is rejected. `-` remains rejected as an unverified
  target form. The actor grammar remains active-position-only.
- Added source citations to the pipeline and coverage contracts and the current
  continuation note. Fresh build/test/checker results after this added parser
  branch remain to be recorded below.

## Decisions and remaining checks

- Inspect current source/diffs before editing because the working tree does not
  match HEAD. Do not rewrite dated historical results; add the fresh results
  with this date.
- Keep Showdown authoritative. Scope remains Gen 9 Random Battles singles;
  actual emitted team size remains authoritative.
- Resolve ENV-001 planning only: dependencies, runtime support, lock policy,
  clean-environment validation, and whether replay fixtures are needed for a
  simulator-only first milestone. Do not install or acquire anything.
- Inspect `-nothing` source emission separately from `nothing`; no inference
  from spelling alone.
- Bound natural-rejection investigation to existing transition implementation,
  source checks, and focused test scenarios; do not fabricate an injected
  failure as a natural one.

## Next actions

1. Finish aggregate status, contract, risk, decision, and evidence-index
   updates with verified sequence and milestone dependencies.
2. Rebuild and rerun focused TypeScript and Python tests after the Python
   publication guard; run `git diff --check` and a final current-state review.
3. Preserve the reviewed digest mismatch for separate semantic review; record
   exact final outcomes and blockers here.

## Final verification and continuation checkpoint

- Final repository snapshot remains branch
  `refactor/state-001-observable-state`, HEAD
  `b9b3eb06d362963bb1fa2da21d7c471a84df262c`. The pre-existing broad tracked
  edits and untracked `docs.zip`, coverage assets, fixtures, and documentation
  remain in the worktree. No staging, cleanup, commit, fetch, package install,
  or checkpoint operation was performed.
- Read-only source investigation is complete. Parent integration is complete
  for the authorized focused fixes and docs. No agent-owned edits remain.
- After adding the precise `null|[notarget]` source form, fresh validation:
  `npm run build --prefix sim-core` passed;
  `node --test sim-core/dist/tests/simulator_coverage.test.js
  sim-core/dist/tests/state_extractor.test.js
  sim-core/dist/tests/observable_state.test.js
  sim-core/dist/tests/action_codec.test.js
  sim-core/dist/tests/pipeline_integration.test.js` passed 41/41;
  `PYTHONPATH="$PWD/trainer/src" python3 -m pytest
  trainer/tests/test_pipeline_record.py trainer/tests/test_dataset_lineage.py
  -q` passed 18/18.
- `npm run check:simulator-coverage --prefix sim-core` and
  `node sim-core/scripts/check-simulator-coverage.cjs --self-test` both exit 1
  on changed local source digest
  `a9e4ec60254e5cc89672777cb98611279e2b7da3fca4a9c57a233ea0ea07b8af`. All six
  synthetic self-test assertions pass before the digest check. The reviewed
  digest remains untouched pending separate semantic review.
- Final `git diff --check` passed. A separate whitespace scan of new untracked
  documentation passed after removing two trailing spaces from
  `docs/PROJECT_STATUS.md`.
- Completed: deterministic controller RNG seam/config regression; pinned-source
  move grammar including active/non-active/omitted/empty/tagged/null-target
  forms; TypeScript and Python structured alias stop guards and candidate
  lineage preservation; `-nothing` distinction; PIPELINE-002 criteria; updated
  milestones, ENV-001 plan, and West Monroe evidence index without a compliance
  claim.
- Exact open acceptance blockers: separate semantic review before digest
  attestation; SIM-COVERAGE per-effect lifecycle disposition; PIPELINE-001
  supported-scope/rejection review (bounded 169-pair probe had zero natural
  rejections, so the criterion needs either an admissible natural case or an
  explicit reviewer disposition); PIPELINE-002 real progression and complete
  episode/truncation tests; ENV-001 tested runtime/dependency/lock policy and
  clean-environment validation; FEATURE-001 target/information regime and
  model interface. PIPELINE-001 and FEATURE-001 remain unaccepted.
- Next actions: obtain the separate semantic review; decide the natural
  rejection acceptance criterion; disposition coverage gaps and review
  PIPELINE-002; complete ENV-001 reproducibility policy and clean run in scope
  for that future item; design FEATURE-001 and model interface before extraction
  or collection. Use this checkpoint to resume without repeating completed
  tests or redoing the bounded probe.

## Review closeout checkpoint — 2026-09-24

### Repository and ownership

- Branch remains `refactor/state-001-observable-state`; HEAD remains
  `b9b3eb06d362963bb1fa2da21d7c471a84df262c`.
- The worktree was already broadly modified. No staging, commit, cleanup,
  checkpoint access, install, network access, dataset work, or training was
  performed. Sensitive message artifacts were not accessed.
- Parent owned edits, integration, docs, and final review. The independent
  read-only reviewer checked move grammar and the request-to-choice rejection
  path; source claims were then exercised by focused local tests.

### Completed fixes and review decisions

- Seeded p1/p2 random-controller streams remain independent of the simulator
  seed; legacy controller defaults remain `Math.random()`. The terminal test
  compares two complete normalized traces with simulator seed
  `[101, 202, 303, 404]`, p1 controller seed `0x51a7`, and p2 seed `0xc0de`.
- The move grammar follows pinned `pokemon-showdown@0.11.10`: active actor
  identifiers; active/non-active Pokémon targets; omitted/empty targets; and
  source-shaped tags. `useMoveInner` interpolates a null target and then
  appends `[notarget]`; parser accepts literal `null` only with exactly one
  final marker and source tags in source order. Arbitrary tags fail closed.
  Relevant sources: `sim/battle-actions.ts:412-462,545,590-640,1512-1516`,
  `sim/battle.ts:3046-3067`, `sim/pokemon.ts:504-512`,
  `sim/SIM-PROTOCOL.md:230-252`.
- `clearstatus`, `-clearstatus`, and `nothing` stop TypeScript projection and
  Python record publication with structured diagnostics. An unresolved alias
  injected after a real candidate transition cannot replace committed state;
  the test compares the next transition to a parallel control branch.
  `-nothing` remains separately supported based on Gen 9 Splash at
  `data/moves.ts:18380-18384`.
- A natural post-preflight rejection exists and is now tested. With simulator
  seed `[46, 101, 202, 303]`, generated p1 Dugtrio/Arena Trap and p2
  Tinkaton/Steel switch in together. Showdown hides trapping status at request
  time (`pokemon.ts:1050-1081,1545-1549`); `Side.chooseSwitch`
  rejects the offered p2 switch (`side.ts:850-866`). The action passes the
  same-request preflight, receives a simulator choice rejection, preserves the
  committed boundary/branch/fingerprint/cursors/observation and belief IDs,
  and matches a parallel control on the next valid joint action. This is a
  real supported-format state, not an injected failure. The separate injected
  diagnostic test remains labeled as injected.
- PIPELINE-001 review verdict: **accept for the explicit v1 joint-actionable
  scope**, including joint forced switches, raw-only supported evidence, and
  terminal projection when the trace is supported. One-sided forced switch,
  waiting, requestless progression, and complete episodes remain PIPELINE-002.
  FEATURE-001, SIM-COVERAGE blanket completeness, and dataset readiness remain
  unaccepted.
- Coverage local-source digest was semantically reviewed and attested as
  `479a096563318af86addd64dd39d445c56e8c5b4d9c8ba0a1c0e100b3c3861d2`.
  The attestation scope is only the manifest's listed local sources/tests;
  lifecycle, clean-tarball provenance, and cross-format gaps remain.

### Fresh validation

- `npm run build --prefix sim-core`: passed.
- `node --test sim-core/dist/tests/simulator_coverage.test.js
  sim-core/dist/tests/state_extractor.test.js
  sim-core/dist/tests/observable_state.test.js
  sim-core/dist/tests/action_codec.test.js
  sim-core/dist/tests/pipeline_integration.test.js`: 42 passed, 0 failed.
- `PYTHONPATH="$PWD/trainer/src" python3 -m pytest
  trainer/tests/test_pipeline_record.py trainer/tests/test_dataset_lineage.py
  -q`: 18 passed.
- `npm run check:simulator-coverage --prefix sim-core`: passed; 142 classified
  condition/effect IDs, 111 parser tokens, 86 literal emitter tokens.
- `node sim-core/scripts/check-simulator-coverage.cjs --self-test`: all six
  synthetic drift assertions passed.
- `git diff --check`: passed after documentation. A trailing-whitespace scan of
  the task checkpoint, review records, contracts, status indexes, and manifest
  also passed.

### Current blockers and next action

- Remaining acceptance blockers: SIM-COVERAGE per-effect lifecycle
  dispositions; PIPELINE-002 real progression and complete/truncated episode
  behavior; ENV-001 tested runtime/dependency/lock policy and clean-environment
  validation; FEATURE-001 target/information regime and model interface. No new
  dataset, feature extraction, training, or deployment is authorized here.
- Current project sequence and distinct dataset/model/product-release
  milestones are indexed in `docs/PROJECT_STATUS.md`. ENV-001 dependencies,
  lock/runtime policy, and simulator-only replay-fixture decision remain
  planned in `docs/refactor/ENVIRONMENT_VALIDATION.md`.
- **Single next task:** disposition the remaining SIM-COVERAGE lifecycle gaps
  that constrain PIPELINE-002 boundary progression. Resume from this closeout
  and do not repeat the completed 169-pair probe; the natural trap regression
  now addresses the rejection criterion.
