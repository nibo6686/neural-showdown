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
  pipeline, coverage, and lineage contracts. Independent historical review artifacts were supplied locally
  outside the repository; they are not published inputs.

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

### CE-04-SLOTS Healing Wish implementation checkpoint (2026-10-02, unreviewed)

Pinned `Moves.healingwish` creates a private per-slot condition and emits one
public active-target full-heal provenance record only when a replacement needs
HP or status clearing. The shared contract now admits exact Healing Wish
provenance only: active target, full status-free health ratio (private split
and public `100/100` spellings), and exactly `[from] move: Healing Wish`.
`Healing Wisp`, other invented Healing-prefix names, side-only targets, partial
or status-bearing health, reordered/duplicate/extra tags, and `[wisher]` all
reject before TypeScript projection or Python DATA-001 publication. Ordinary
heals and accepted Wish grammar remain unchanged.

`state_extractor` clears existing typed status only when this exact public
Healing Wish evidence is observed; it adds no pending slot field, source link,
timer, request content, or simulator snapshot. Pinned-engine fixtures cover
both actors/perspectives, real status then forced replacement, healthy
nonapplication, `canSwitch` cancellation, terminal-before-replacement,
restored v2 twins, deterministic continuation, Python actor publication, and
v1/v2 rehash rollback/no-output controls. Future Sight, other delayed effects,
item callbacks, Revival Blessing scope, episode readiness, and
`faithful_complete_episode:false` are unchanged.

The listed coverage sources now include `tests/healing_wish.test.ts`. Computed
local digest: `d577f178573ccd5ba3fe08b169bbe5bd999d43070c4f585570642e5efcaa807c`
(**unreviewed**). Manifest `sha256`, `reviewed_sha256`, and attestation fields
remain unchanged. The coverage self-test passes; the full checker reports this
expected unreviewed local-digest mismatch until separate review updates its
attestation fields.

### CE-04C reachable public stage-transfer closure checkpoint (2026-10-06)

#### Complete route matrix

This checkpoint binds the finite route matrix documented in the
[closure audit's CE-04C section](COMPLETE_EPISODE_CLOSURE_AUDIT.md#ce-04c-reachable-public-stage-transfer-closure-2026-10-06).
The installed simulator is pinned as `pokemon-showdown@0.11.10`; the operative
format resolves to `gen9randombattle`, random teams, singles. Reachability is
proved from generator roots and callback/copy callers, not registry membership.

| Path family | Classification | Source proof, current projection and evidence |
|---|---|---|
| Ordinary `-boost`/`-unboost` deltas, including source-bounded move, ability and item callbacks | Generated-format reachable and already correctly represented | `Battle.boost` emits the applied delta after modifiers and guards. Contrary changes the logged sign; reactive Defiant/Competitive use the same writer. Accepted mixed seven-stage evidence plus new generated Contrary/Leaf Storm witness prove the typed result. |
| Stage replacement (`-setboost`) | Generated-format reachable and already correctly represented | Belly Drum has generated roots and emits exact `-setboost`; new generated Azumarill witness covers its `+6 atk` result and Python publication. Anger Point's writer branch has no generated ability root. Existing zero/sign/clamp compatibility controls remain. |
| Haze / Clear Smog full clear | Generated-format reachable and already correctly represented | Haze emits `-clearallboost`; Clear Smog clears its target and emits `-clearboost`. New generated Tentacruel and Amoonguss witnesses verify those exact event scopes for both actor sides. |
| Transform move / Imposter | Generated-format reachable and already correctly represented | Both call `Pokemon.transformInto`, which copies all current stages before `-transform`. Accepted Transform evidence covers replacement and sparse/known-zero/unknown behavior; new generated Ditto witness copies a prior nonzero Shell Smash vector via Imposter. |
| Switch, drag, faint and Shed Tail | Generated-format reachable and already correctly represented | `clearVolatile` silently resets the departing/fainted Pokémon. Shed Tail's `copyVolatileFrom` explicitly does not copy boosts. Accepted v2 lifecycle and Shed Tail switch witnesses cover reset and Substitute-only transfer. |
| White Herb negative clear and one Recycle restore | Generated-format reachable and already correctly represented | White Herb consumes then emits exact `-clearnegativeboost [silent]`; Recycle has the separately bounded `-item` restore. Reuse accepted CE-04F1/selective-clear mirrored v2 and Python evidence. Fling's White Herb effect is impossible because Fling has no generated move root. |
| Mirror Armor negative reflection | Generated-format reachable and already correctly represented | Generated Corviknight can have Mirror Armor; `onTryBoost` routes the negative delta to the source through `Battle.boost`. New generated Corviknight/Arcanine witness verifies the source's `-unboost` and Python publication. Trace/Imposter copy only already seeded current abilities. |
| Psych Up, Topsy-Turvy, Spectral Thief, Power/Guard/Heart Swap | Source-proven impossible in singles | B05/B08/B15 close direct and indirect move roots. Preserve bounded exact Psych Up/Topsy compatibility tests, generic selective record semantics, and Spectral Thief's raw-only animation; `-swapboost` remains rejected. No compatibility fixture is counted as a generated witness. |
| Baton Pass | Source-proven impossible in singles | It is the only `copyvolatile` stage-sharing switch cause; no generated move root exists. Ordinary switches reset instead; v2 rejects Baton Pass stage-transfer evidence. |
| Costar, Curious Medicine, Opportunist, Mirror Herb, Simple | Source-proven impossible in singles | No generated A/I root; Trace/Imposter cannot bootstrap an unseeded ability. Costar and Curious Medicine also require an allied active target, impossible in singles. No ability/item callback stage-copy model is added. |
| Unaware/Foresight/Miracle Eye and copied crit volatiles | Raw-only/private with no public typed-stage consequence | These affect calculations or private volatile parameters, without assigning to stored public boost stages. No private critical-hit counters are added. |
| Fling White Herb, Z-Power negative clear, Freezy Frost | Source-proven impossible in singles | Their Fling, Z-item/action, or other-generation roots are outside operative M/I. Package-wide emitter membership is not reachability. |
| Bounded compatibility and raw-only forms | Raw-only/private with no public typed-stage consequence where already classified raw-only; typed aliases retain their accepted compatibility semantics | Bare stage aliases are bounded v2 replay normalization. Exact Psych Up/Topsy compatibility forms remain typed evidence but do not establish random-format reachability; Spectral Thief animation is raw-only. Unsupported Costar/swap/Baton Pass forms continue to stop. |

#### Focused witnesses and validation

The already coverage-listed `sim-core/tests/public_stages.test.ts` now includes
generated roots for Haze (Tentacruel seed `[21,2,3,4]`), Clear Smog (Amoonguss
`[148,2,3,4]`), Mirror Armor (Corviknight `[152,2,3,4]`), Contrary (Serperior
`[40,2,3,4]`), Imposter (Ditto `[9,2,3,4]`) and Belly Drum (Azumarill
`[17,2,3,4]`). Each new path is exercised from either actor position. Both
successor perspectives match simulator stages at the event cursor, retain the
input prefix, omit private opponent fields, and pass the Python record
publisher. Existing accepted evidence is reused for Transform, Psych Up,
Topsy-Turvy, selective clearing, switch/faint, Shed Tail and historical v1/v2
identity behavior.

Validation run: `npm run build`; selected Node tests for
`public_stages`, `transform_boosts`, `psych_up`, `selective_boosts`,
`topsy_turvy` and `ability_callback` — 86 passed, 0 failed; `git diff --check`
passed. No production source, contract, dependency, fixture list or coverage
attestation field changed. The coverage manifest already includes the changed
test file; its local/reviewed digest was not recalculated in this scoped run and
remains a separate coverage-attestation review item.

#### Scoped review verdict

**CE-04C is accepted as scoped source/evidence closure. No production
implementation slice is indicated.** The pinned-source review found no
generated-format route with a missing or incorrect public-stage disposition.
All generated single-battle routes map to
existing public stage records or exact lifecycle boundaries, and the focused
generated-route witnesses agree with pinned simulator state and Python
publication. No source-backed reachable public-stage mismatch remains.

This recommendation does not accept PIPELINE-002 or a complete episode, alter
the default v1 contract, change `faithful_complete_episode:false`, expose
hidden ability/item/critical-hit state, add a general stage-transfer feature,
or expand to doubles. If future source drift finds a mismatching reachable
route, create a narrow follow-up naming the emitter, typed state handler,
shared validators and regression witness.

### CE-06A two-perspective episode evidence implementation checkpoint (2026-10-06)

This checkpoint follows the 2026-10-06 accepted CE-01 aggregate Glaive Rush
fixture correction and CE-04C public-stage source/evidence closure. CE-04C's
digest attestation remains scoped to CE-04C in the closure audit. CE-06A is an
implementation checkpoint only; its scoped review hold and withheld attestation
are recorded below.

For opt-in v2 episode runs, `pipeline-episode-evidence/v1` now retains both
players' complete v2 observation at the segment origin and after every
committed transition. Each observation carries only its owner's request and the
exact normalized public prefix. The envelope carries the origin commitment,
ordered transition lineage and actor list, but no action, belief/simulator
snapshot, seed or raw simulator payload. Existing actor bundles and DATA-001
rows remain actor-only. Waiting-side observations stay in the two-perspective
boundary chain without a synthetic action or decision row. Continuations bind
to their segment-start origin and are labeled `continuation_segment`.

TypeScript and Python validators check the v2 observation identities, both
perspective identities, exact public-prefix extension, consecutive boundary and
transition lineage, actor/request agreement, per-player record ordering, and
origin/run identity joins. Rehashed gap, reorder, duplicate, prefix mutation,
and forged-origin controls reject in both runtimes. Candidate rejection leaves
the committed actor rows and evidence unchanged. The Python full-result bridge
validates the entire chain before producing actor-only DATA-001 rows; rejected
full-result validation emits no stdout publication. The accepted seed
`[101,202,303,404]` is reused for joint and one-sided progression, with no new
mechanic witness fixture.

Fresh checks: `npm run build`; focused `pipeline_episode` TypeScript tests, 22
passed; focused `test_pipeline_record.py` Python suite under the documented
Python 3.9.6 simulator-record environment, 42 passed; coverage reachability
self-tests passed; `git diff --check` passed. The normal coverage checker
reproduced local digest
`9db6c92f12bff901647998d097a1d8c0438d7b5e7ebcd40e20fd9c96d26b259a` and
reported only that local coverage sources are not bound to a separate
semantic-review digest. `local_coverage_sources.sha256` now records the
reproduced candidate; `reviewed_sha256` remains the prior CE-04C-attested digest
`c0f87af971132c6542fd89735dee6cf920b881882456bdcd670841ad38d252d3`. The
manifest continues to include `tests/public_stages.test.ts`. No attestation
fields were changed for CE-06A.

Exact SHA-256 hashes of the changed implementation and test files:

| File | SHA-256 |
|---|---|
| `sim-core/src/pipeline_episode_evidence.ts` | `4d0869ae91fe8408d745d73b1b916cb2aa1972cd025bb29842504e7d8a4ec72d` |
| `sim-core/src/pipeline_episode.ts` | `7b5cceb39f2b480c4efe41ce18bbe13bb458ac4bb5f360990e2b879659341aea` |
| `sim-core/src/belief_state.ts` | `de8ca8d8f53f1a887160f284c15a8cb01d5cdeb399ad65bf5a22230a6aa78fea` |
| `sim-core/tests/pipeline_episode.test.ts` | `05c7f2c04e8ebe7f42396f0dae7e30ab5048ed7b24d5ea830c4b76c303ce8b97` |
| `trainer/src/neural/pipeline_record.py` | `66666541a850bd2296ac8c8cdc8c2e1c5be4f01e892e82bf8e4c7c2703c6ceda` |

Remaining limits: CE-06A is not accepted; the scoped review hold below requires
focused privacy-tamper regression controls before attestation and reconciliation
of the local and reviewed manifest digests.
Deterministic hashes detect inconsistent or independently forged identities but
are not signed provenance against a coordinated rewrite of the complete result.
CE-06B segment concatenation and terminal/win/tie/final-delivery closure remain
unimplemented, as do the remaining prerequisite P0 audit rows. No dataset,
training, or live-model behavior was enabled; `faithful_complete_episode:false`
remains mandatory.

Next: obtain a separate review and scoped attestation for the CE-06A privacy
regression repair below; complete outstanding CE-04/CE-05 P0 dependencies in
the closure audit; implement/review CE-06B; then run CE-08A and CE-08B before
final branch validation and merge.

### CE-06A independent review hold (2026-10-06)

At that independent review, the five implementation/test hashes above matched
the files under review, so the recorded build, focused TypeScript/Python suites
and coverage checks were reused.
Independent review confirmed that the validators enforce owner-bound requests,
constrained opponent roster fields and declared private-payload key rejection.
A read-only runtime probe added the other player's request under the forbidden
`opponent_request` key, recomputed the envelope digest, and confirmed TypeScript
rejection plus Python full-result rejection with empty stdout.

**Medium review finding — missing durable CE-06A privacy-tamper controls.** The
checked-in episode test rehashes gap, reorder, duplicate, prefix and forged-origin
cases, but does not rehash a private-payload mutation such as a seed, simulator
snapshot, hidden set/roster, foreign request or private opponent field. Its
Python full-result no-publication assertion exercises the gap case only. The
direct probe confirms the current foreign-request guard, but there is no focused
regression control proving the full privacy family is rejected by both runtimes
before DATA-001 publication. This is a test-evidence blocker; the review did not
observe a successful privacy leak in the validators or normal publication.

At that review CE-06A was **not attested**. No implementation or test files
were changed during review. The local candidate digest then was
`9db6c92f12bff901647998d097a1d8c0438d7b5e7ebcd40e20fd9c96d26b259a` and the
reviewed digest remains the separate CE-04C value
`c0f87af971132c6542fd89735dee6cf920b881882456bdcd670841ad38d252d3`; all prior
scoped attestations remain intact. The follow-up from that hold was to add
rehashed episode-envelope privacy controls in both runtime paths, including a
full-result Python no-publication assertion, recompute the local digest and
request a separate CE-06A review. CE-06B remains outside this review and
`faithful_complete_episode:false` remains mandatory.

### CE-06A privacy-tamper regression repair checkpoint (2026-10-06, unreviewed)

The review finding above is addressed with a durable TypeScript regression; no
production code changed. The test clones the existing valid CE-06A result,
places p2's actual origin request in p1's request slot, then recomputes the p1
observation identity, initial summary observation ID, run ID, origin commitment,
all commit origin references and envelope digest. This keeps the malformed
owner relationship as the semantic failure under test rather than leaving stale
identities.

Using the full result's evidence, actor rows and root expectation, TypeScript
rejects the forged origin request with its perspective-owner error. Deep equality
checks show validation does not mutate the tampered result or original committed
result. The Python bridge receives that same rehashed full result, exits 2 and
emits empty stdout. The existing valid evidence and full-result publication
controls continue to pass.

Validation: `npm run build --prefix sim-core` passed; the focused
`pipeline_episode` TypeScript suite passed 22/22; the focused
`test_pipeline_record.py` Python publication suite passed 42/42; the coverage
reachability self-test passed. The normal checker computes
`9025a34776e69f5a8f315fe84b8ea1a628977ea62a6cd4583772c0a32ee7978c`, a drift
from prior local candidate
`9db6c92f12bff901647998d097a1d8c0438d7b5e7ebcd40e20fd9c96d26b259a` caused by
the changed, coverage-listed test. The manifest already includes
`tests/pipeline_episode.test.ts`; its local `sha256` now records the new digest
and `reviewed_sha256` remains the prior CE-04C value
`c0f87af971132c6542fd89735dee6cf920b881882456bdcd670841ad38d252d3`. The
post-update checker reports only the expected missing separate semantic-review
binding. `git diff --check` passed.

Exact current SHA-256 values for the CE-06A implementation/test files:

| File | SHA-256 |
|---|---|
| `sim-core/src/pipeline_episode_evidence.ts` | `4d0869ae91fe8408d745d73b1b916cb2aa1972cd025bb29842504e7d8a4ec72d` |
| `sim-core/src/pipeline_episode.ts` | `7b5cceb39f2b480c4efe41ce18bbe13bb458ac4bb5f360990e2b879659341aea` |
| `sim-core/src/belief_state.ts` | `de8ca8d8f53f1a887160f284c15a8cb01d5cdeb399ad65bf5a22230a6aa78fea` |
| `sim-core/tests/pipeline_episode.test.ts` | `e06d000bfae416ff2451429f5a8a6c587a2c788351af4970d265a65497f2f904` |
| `trainer/src/neural/pipeline_record.py` | `66666541a850bd2296ac8c8cdc8c2e1c5be4f01e892e82bf8e4c7c2703c6ceda` |

This checkpoint closes only the durable privacy-tamper test gap; separate review
and scoped digest attestation remain outstanding. CE-06B remains outside scope,
and `faithful_complete_episode:false` remains mandatory.

### CE-06A privacy-tamper regression review hold (2026-10-06)

The five implementation/test hashes recorded in the repair checkpoint match
the reviewed files, so its build, focused TypeScript/Python checks, and coverage
self-test were reused. The regression does exercise the intended owner check:
the fully resealed envelope carries p2's request in p1's slot, TypeScript
reports the request-perspective error without mutating the candidate or the
committed result, and Python rejects the same full result with exit 2 and empty
stdout. Valid evidence-only and full-result publication controls remain in the
test.

**Medium review finding — origin summary belief identity remains stale.**
`withRehashedForeignOriginRequest` refreshes p1's observation ID and prefix
hash, the initial-summary observation reference, run ID, origin ID, commit
origin references, and envelope evidence ID. It does not recompute
`initial_boundary.perspectives.p1.belief_id`. That identity is derived from a
belief payload containing an observation reference, while the changed summary
observation ID now identifies the tampered observation. The CE-06A validators
only check that this summary belief ID has the expected textual shape, so the
candidate reaches the intended request-owner error; however, the fixture is
not fully identity-consistent as required for the privacy-tamper control. The
regression therefore remains a review blocker until its candidate's dependent
belief identity is handled consistently.

No implementation or test file was changed during this review. The current
coverage manifest includes `tests/pipeline_episode.test.ts`. Its local coverage
digest remains
`9025a34776e69f5a8f315fe84b8ea1a628977ea62a6cd4583772c0a32ee7978c`; the
manifest's `reviewed_sha256` remains the prior scoped digest
`c0f87af971132c6542fd89735dee6cf920b881882456bdcd670841ad38d252d3`. No
coverage attestation fields were changed. The reachability self-test passes;
the normal checker reports only the expected missing semantic-review binding;
`git diff --check` passes. CE-06A is not attested. CE-06B and complete-episode
acceptance remain outside scope, and `faithful_complete_episode:false` remains
mandatory.

### CE-06A privacy regression identity-rehash checkpoint (2026-10-06, unreviewed)

The focused test was updated to address the stale summary belief ID without
changing production source. After replacing p1's origin request and refreshing
its observation identity, the helper clones p1's first input belief, updates its
observation reference and matching observation-history entry, removes
`belief_id`, and hashes the remaining payload with the same sorted-key
canonicalization used by the existing test identity helpers. `serializeBeliefState`
validates that cloned belief identity. The recomputed ID is copied into the
initial summary before recomputing the run ID, origin ID, commit origin IDs and
envelope evidence ID in dependency order. The clone is not written back to the
candidate's first p1 record; the following review hold records that remaining
consistency gap.

The focused CE-06A test still receives the ownership mismatch in TypeScript,
with deep-equality checks preserving both the candidate and original committed
result. Python rejects that same full result with exit 2, empty stdout and the
request-ownership diagnostic. The valid evidence-only and full-result
publication controls continue to pass.

Validation: `npm run build --prefix sim-core` passed; the focused
`pipeline_episode` TypeScript suite passed 22/22; the focused
`test_pipeline_record.py` Python publication suite passed 42/42. The coverage
reachability self-test passes. The manifest includes
`tests/pipeline_episode.test.ts`; its local digest is
`b22c31d2b0b8550144662bc1604c7675a8343cec601696aaaace77919a5c1334`. The
manifest's `reviewed_sha256` remains
`c0f87af971132c6542fd89735dee6cf920b881882456bdcd670841ad38d252d3`; the normal
checker reports only the expected missing separate semantic-review binding.
`git diff --check` passed. The corrected test awaits separate review;
attestation remains withheld. CE-06B and complete-episode acceptance remain
outside scope, and `faithful_complete_episode:false` remains mandatory.

Exact current SHA-256 values for the CE-06A implementation/test files:

| File | SHA-256 |
|---|---|
| `sim-core/src/pipeline_episode_evidence.ts` | `4d0869ae91fe8408d745d73b1b916cb2aa1972cd025bb29842504e7d8a4ec72d` |
| `sim-core/src/pipeline_episode.ts` | `7b5cceb39f2b480c4efe41ce18bbe13bb458ac4bb5f360990e2b879659341aea` |
| `sim-core/src/belief_state.ts` | `de8ca8d8f53f1a887160f284c15a8cb01d5cdeb399ad65bf5a22230a6aa78fea` |
| `sim-core/tests/pipeline_episode.test.ts` | `08f4760e33235296947c969e3b7d02ddb17894475b25c812aba2c030f591d17a` |
| `trainer/src/neural/pipeline_record.py` | `66666541a850bd2296ac8c8cdc8c2e1c5be4f01e892e82bf8e4c7c2703c6ceda` |

### CE-06A privacy regression identity-correction review hold (2026-10-06)

All five implementation/test hashes still match the checkpoint above, so the
recorded build, focused TypeScript/Python tests, and coverage self-test were
reused. The source list includes `tests/pipeline_episode.test.ts`; local digest
`b22c31d2b0b8550144662bc1604c7675a8343cec601696aaaace77919a5c1334` and
reviewed digest `c0f87af971132c6542fd89735dee6cf920b881882456bdcd670841ad38d252d3`
remain unchanged.


**Medium review finding — recomputed belief is not applied to the full candidate.**
The helper hashes and validates a clone of the first p1 record's input belief,
then copies only its new ID to the initial summary. `tampered.records.p1[0]`
still contains the old input observation and old input belief. Thus the changed
origin boundary and summary do not join the first p1 actor bundle. Both
validators validate the envelope boundary before actor-record joins, so they
still report the intended request-owner mismatch and the test's rejection and
no-publication assertions pass. If the owner check were bypassed, the TypeScript
and Python full-result validators would reject the stale input-observation join;
the result is therefore not a fully identity-consistent full-result fixture.
No production bypass was observed.

No source or test changes were made during this review. Coverage self-test
passes; the normal checker reports only the expected missing separate
semantic-review binding; `git diff --check` passes. The CE-06A attestation is
withheld and all manifest attestation fields remain unchanged. The fixture must
update the candidate's actor-record observation/belief lineage consistently
before a new review. CE-06B and complete-episode acceptance remain outside
scope, and `faithful_complete_episode:false` remains mandatory.

### CE-06A privacy regression lineage repair checkpoint (2026-10-06, unreviewed)

The test-only fixture now propagates the changed p1 origin observation into the
first p1 input record and rewrites every p1 belief reference to that origin in
observation/history and transition lineage/history. It rehashes each unique
p1 belief after recursively rehashing its parent, copies the results into all
input/successor record occurrences, and updates the initial/final summary
belief IDs. Existing `serializeBeliefState` validates each rehashed belief.
Assertions verify p1 record ordering and every actor-record join against the
origin/preceding and committed boundaries, including input/successor belief
references, parent links, transition metadata and transition-lineage
observation IDs. Simulator transition IDs remain unchanged because the altered
request does not change their action, seed, branch, or snapshot inputs.

The fixture confirms that the only intended semantic mismatch is the origin
p1 observation carrying p2's request. The Python identity helper accepts the
altered first p1 record; the full-result Python publication path rejects the
same candidate with exit 2, empty stdout and `request is not owned by its
perspective`. TypeScript rejects with the expected p1 request perspective/rqid
error, while deep equality confirms the candidate and original result retain
their committed evidence and lineage. Valid full-result and evidence-only
publication controls continue to pass. No production files changed.

Validation on the corrected test: `npm run build` passed; focused
`pipeline_episode.test.js` passed 22/22; focused `test_pipeline_record.py`
passed 42/42; coverage reachability self-test passed; and `git diff --check`
passed. The normal coverage checker reports only the expected requirement for
a separate semantic-review digest. The source list already contains
`tests/pipeline_episode.test.ts`; local digest is
`e7d5e2f6279fc0cc0895e048e6b8fce7971431d44e0366861651d5700a291c1c`.
`reviewed_sha256` remains `c0f87af971132c6542fd89735dee6cf920b881882456bdcd670841ad38d252d3`,
all other scoped attestations remain intact, and no CE-06A attestation is
claimed. CE-06B and complete-episode acceptance remain out of scope;
`faithful_complete_episode:false` remains mandatory.

Exact current SHA-256 values for the CE-06A implementation/test files:

| File | SHA-256 |
|---|---|
| `sim-core/src/pipeline_episode_evidence.ts` | `4d0869ae91fe8408d745d73b1b916cb2aa1972cd025bb29842504e7d8a4ec72d` |
| `sim-core/src/pipeline_episode.ts` | `7b5cceb39f2b480c4efe41ce18bbe13bb458ac4bb5f360990e2b879659341aea` |
| `sim-core/src/belief_state.ts` | `de8ca8d8f53f1a887160f284c15a8cb01d5cdeb399ad65bf5a22230a6aa78fea` |
| `sim-core/tests/pipeline_episode.test.ts` | `99801b0b7395d5df6448c25941decc8504fc3e4cdca343c3c87ffc6e662cd8b5` |
| `trainer/src/neural/pipeline_record.py` | `66666541a850bd2296ac8c8cdc8c2e1c5be4f01e892e82bf8e4c7c2703c6ceda` |

### CE-06A privacy regression correction scoped review verdict (2026-10-06): accepted

An independent review rechecked the altered origin observation, the first p1
record, all dependent p1 belief observation/history and transition references,
parent-belief rehash order, summary identities, and the run/origin/evidence
envelope identities. Actor record order, origin/preceding-boundary joins,
successor joins, transition references, and final p1 belief joins are asserted.
Only the p1 origin carrying p2's request remains semantically invalid. Transition
IDs correctly remain unchanged because their action/snapshot identity inputs do
not change.

All five source/test hashes above match the reviewed files. The successful
build, focused TypeScript suite (22/22), Python publication suite (42/42),
coverage reachability self-test, and whitespace check are reused from matching
hash evidence; valid full-result and evidence-only controls pass. TypeScript
rejects with the ownership error while preserving both candidate and original
committed data. Python rejects the same full result with exit 2, empty stdout,
and the expected request-ownership diagnostic. No material findings or
production changes.

The manifest's local and reviewed digest now both bind
`e7d5e2f6279fc0cc0895e048e6b8fce7971431d44e0366861651d5700a291c1c`. This
attestation is scoped only to CE-06A's two-perspective evidence/privacy
regression. Other scoped attestations are preserved. CE-06B terminal/segment
closure and complete-episode acceptance are not included;
`faithful_complete_episode:false` remains required.

### CE-08A turn-limit actor-row publication sweep (2026-10-07)

This follow-up closes only the independent review finding that every
intermediate actor-only DATA-001 bundle in the source turn-limit tie chain had
not passed Python publication validation. It does not attest CE-08A.

**Validation graph and bounded design.** Python first validates envelope
identity and origin, recursively validates predecessor joins, terminal evidence,
all two-perspective boundaries, and contiguous immutable prefixes. It then
validates each actor bundle's owner/request/action, observation and belief
identities, transition and lineage joins, privacy constraints, cursor and
prefix digest, and DATA-001 row. The CLI writes stdout only after the validator
returns the complete list. The new compact sweep supplies result metadata and
the evidence envelope once, ordered actor rows, and each distinct belief once.
Parent-linked deltas reconstruct repeated belief arrays; source prefixes are
rejoined only from validated envelope observations. A validation context caches
the exact already-validated observations, prefix serializations, and
DATA-001 prefix digests. Each reconstructed row still goes through the ordinary
bundle validator; only exact boundary/prefix work proved by the envelope is
reused. The result list remains atomic in memory. The predecessor bundle is
separately published through the unchanged ordinary one-bundle path.

| Control | Result |
|---|---|
| Full fresh-origin → predecessor → turn-1000 tie | 1,996 current-segment actor rows published in order; elapsed Python sweep 155,435 ms (under the 300,000 ms bound). The whole restored source-engine test took 775,470 ms. |
| Actor-only behavior | Output row pairs equal the p1/p2 record arrays and the eligible-actor count; no waiting-side row. The predecessor's two actor rows publish separately. |
| Rehashed middle-row ownership tamper | The p2 canonical action and its action ID are transplanted into a p1 row; transition action ID is derived from that action. TypeScript rejects it against p1's owned request. Python exits 2 with the expected player-ownership error and empty stdout. Original result/evidence and candidate remain unchanged. |
| Valid small episode and one-sided controls | The 55-transition v2 envelope/sweep test passes; Python publication output preserves expected actor ordering and excludes waiting-side rows. |
| Core checks | TypeScript build passed; focused episode tests passed; Python pipeline-record and dataset-lineage tests passed 54/54; coverage synthetic-drift self-tests passed; `git diff --check` passed. |

The sweep schema is documented in `docs/contracts/PIPELINE_EPISODE.md`. Its
path was added to the local source manifest; the TS/Python implementation and
focused tests were already listed. Exact changed-file hashes and the
reproducible local digest are recorded below. The turn-limit publication
finding is closed; CE-08A aggregate acceptance, CE-08B, remaining P0 gates, and
complete-episode fidelity remain open. `faithful_complete_episode:false`
remains required.

The independent scoped review accepted local coverage digest
`b68c508274203f8f470d6b98b9bacd24357d7f703fd209e23445dd0e15a20145` for the
publication-sweep closure only. The manifest binds both local and reviewed
digest fields to it. CE-08A aggregate acceptance, CE-08B, PIPELINE-002, and
complete-episode fidelity remain outside this attestation.

Exact SHA-256 hashes for files changed by this follow-up:

| File | SHA-256 |
|---|---|
| `trainer/src/neural/pipeline_record.py` | `b265e36f7cab1d4aff141ade39868cc9becaee483e279b18ced73da6653ab51f` |
| `trainer/src/neural/ts_identity.py` | `d9086a839312293258fa7a011b4965811253a9f85f66c4998219368c6cf84651` |
| `sim-core/tests/pipeline_episode.test.ts` | `0e7c26510840ff31eaaa0a529e24a59d8cf358a15e84c9abd9c04f5604920005` |
| `docs/contracts/PIPELINE_EPISODE.md` | `2249487242e709bea6640222835feeeda015bc501789b57ec736233d868323c0` |
| `docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md` | `63d624c40698dbcfabd30598fb1f92afb6a5041c587d19cf497b9d0a90b90d30` |
| `docs/PROJECT_STATUS.md` | `4665f0e9f8fff3c64dea153ae2b1e26b39dad119be98c481702004839cab71ae` |
| `docs/refactor/STATUS.md` | `17cb1d4bfb1bdb27b66e862050f0d031d9ea562b7e1b3a3d293a5b29be09fb0b` |
| `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json` | `c4f16fcc04db222f859afdd6b658c79b5b9184e32d6f607613a38e4022968f72` |

The progress document's own SHA-256 is reported with the completion results.

### CE-02D source, contract, privacy, and adversarial matrix (2026-10-06, in progress)

| Review dimension | Pinned evidence / current disposition | Validation planned for this checkpoint |
|---|---|---|
| Exact turn-limit emitter | `pokemon-showdown@0.11.10`, `gen9randombattle` (`mod: gen9`, random teams, no debug): `Battle.endTurn` increments the turn and calls `maybeTriggerEndlessBattleClause`; turns 500/600/700/800/900, each ten turns 900–980, and 990–999 emit `|bigerror|You will auto-tie if the battle doesn't end in ${turnsLeftText} (on turn 1000).`. The exact `N` set is `{1..10,20,30,40,50,60,70,80,90,100,200,300,400,500}`, with `1 turn`. At 1000 the engine emits `|message|It is turn 1000. You have hit the turn limit!`, then `|tie`; the last warning is at 999. | Fixed-seed generated teams; checkpoint/restore before turn 990, continue through the actual source `endTurn` path to the turn-limit tie; compare source log and public channels. |
| Separate EV warning | `Battle.checkEVBalance` emits the EV `bigerror` only from debug-mode `Battle.start`; the operative format and sim-core stream do not enable debug. Independently, Gen 9 Random Battle sets start at 85 EVs in each stat (510 total) and subsequent generator reductions do not increase EVs. **No operative route**; retain rejection without creating a blocker or widening grammar. | Verify the executable debug gate, no operative `checkEVBalance` caller/override, generated-set cap, and fully rehashed Python rejection of the EV payload. |
| Audience, retention, typed state, privacy | The auto-tie emitter calls ordinary unsplit `Battle.add`, so the public line is delivered identically to spectator/p1/p2 streams and retained in both public observation prefixes. It is raw-only: no typed mechanic, belief update, legal-action change, or terminal authority. Requests/errors/split/debug/showteam and unsupported diagnostic payloads remain outside public evidence and must reject before projection/publication. | Assert both perspectives retain exact ordered raw lines while projected typed fields remain equal; publish the valid control and inspect DATA-001 output for raw-only evidence and absence of request, snapshot, seed, or hidden-set material. |
| Adversarial controls | Source-shaped warning is the positive control. Negative controls cover unsupported/malformed warning text (including EV diagnostic), extra fields, whitespace mutation, a tag suffix, and a candidate chunk with a valid prefix line preceding an invalid warning. | Rehash observation/belief/prefix identities with existing helpers; verify TypeScript rejects atomically without changing candidate/committed state and Python exits 2 with empty stdout before publication. Also validate valid controls and a restored terminal-adjacent source continuation. |

The focused CE-02D TypeScript source/protocol test and Python DATA-001 publication
test sources are already in the coverage manifest. This is an in-progress
evidence matrix only; implementation/test validation and the local digest are
pending. No attestation is added, and `faithful_complete_episode:false` remains
required.

### CE-02D implementation checkpoint (2026-10-06, ready for attestation)

The matrix above is complete. The exact pinned turn-limit warning and event
order were reproduced by restoring a fixed-seed generated `gen9randombattle`
battle at turn 989 and continuing the actual Showdown `endTurn` path. The
source emitted the 10-through-1 warnings in turns 990–999, then the turn-limit
message and `|tie` at 1000. `extractChannelMessages` delivered each warning
identically to spectator, p1, and p2. Both p1 and p2 observation prefixes retain
the exact ordered lines; the typed view, request, and decision-availability
fields are unchanged when only the raw warning evidence is added.

The EV diagnostic remains source-proven unreachable for this route: its only
`Battle.start` call is debug-gated, the operative format and sim-core stream do
not enable debug, and generated sets are capped at 510 EVs because the random
team generator starts at 85 per stat and only reduces values. The exact EV
warning remains rejected.

A narrow ingress fix applies the existing raw-record validator to public
`bigerror` records before accumulation. `appendPublicSpectatorChunk` now
validates a whole chunk before appending any of it, so a valid line preceding a
malformed/private record does not partially change the committed prefix. No
production change was needed in the TS/Python protocol grammar or DATA-001
publisher. The existing actor-only DATA-001 row stores the input prefix hash;
it publishes no raw warning, private request, simulator snapshot, seed, or
hidden-team fields.

Fully rehashed candidate controls use the existing canonical identity helpers.
TypeScript verifies the observation cursors/hashes/IDs, belief IDs/references,
parent belief, and transition observation joins before testing the exact
protocol validator. Both runtimes exercise v1/v2, p1/p2, and input/successor
locations. Valid source-shaped controls pass. Unsupported/EV text, wrong-turn
text, extra fields, whitespace mutation, and tag suffixes reject; TypeScript
does not mutate the prefix candidate, and Python `main()` exits 2 with empty
stdout before DATA-001 publication. Existing contract rejection fixtures also
cover bad singular/plural and unsupported `N` values. No broad diagnostic
allowlist was introduced.

Validation results:

- `npm run build` — passed.
- `node --test dist/tests/protocol_contract_validation.test.js` — 14/14 passed,
  including the source restoration harness and both rehashed v1/v2 matrices.
- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_pipeline_record.py'`
  — 43 tests passed.
- `node --test dist/tests/simulator_coverage.test.js` — 9/9 passed.
- `node scripts/check-simulator-coverage.cjs --self-test` — every synthetic
  drift test passed; process exits 1 because the local digest is not bound to a
  separate semantic-review digest. The normal checker exits 1 for that same
  expected review gate.
- `git diff --check` — passed before this final status-note append; rerun after
  the final documentation/hash updates.

The two focused test files were already in
`local_coverage_sources.files`; no source-list change was needed. The manifest
local `sha256` is `1813f333a918cdf81c2f754ed64b53d29eb77ca3c75f8de9d32d765b96042db2`.
`reviewed_sha256` remains the separately reviewed CE-06A value
`e7d5e2f6279fc0cc0895e048e6b8fce7971431d44e0366861651d5700a291c1c`; final
CE-02D attestation remains with the independent reviewer. No scoped attestation
was changed, and `faithful_complete_episode:false` remains required.

Exact SHA-256 values for this checkpoint's source, test, manifest, and closure
audit files:

| File | SHA-256 |
|---|---|
| `sim-core/src/env_manager.ts` | `c7d0669c1ffd5359327f89a4fa05d7d4bc34138f0bf5ee5b1e24484668beb984` |
| `sim-core/tests/protocol_contract_validation.test.ts` | `25ac6364a85cb265ec3c25b481ee11c2eeab3e5c548e79719ec64167a8b554fa` |
| `trainer/tests/test_pipeline_record.py` | `818406d458d7a18d27bb5fb40531c93438ea9ac00f15e5cc24ed3fb108742869` |
| `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json` | `f20b11aff2ac7795122fac8a085ec16e6aa083d7fade8ede0e91af33e743dc65` |
| `docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md` | `7c5002cd1900decd7a0b555f294c86634b130029810281397cea41e00ac2b59e` |

Current next steps: separate semantic attestation for CE-02D, then CE-06B
segment/terminal closure and CE-08A/08B complete-episode evidence/review. This
checkpoint does not capture terminal-adjacent pipeline evidence, resumed
segment closure, or a final outcome envelope; those remain CE-06B work.

### CE-02D independent scoped review verdict (2026-10-06): accepted

The independent acceptance review found no material CE-02D findings. The
pinned Showdown warning literal and its ordering before the turn-limit tie
match the implementation grammar. The separate EV diagnostic remains rejected
with a source-backed no-route disposition for the operative format and stream.
The warning is exact, raw-only public evidence; both perspectives retain it,
typed fields remain unchanged, and actor-only DATA-001 publication excludes
the raw warning and private/simulator data.

Focused evidence was reused where the exact source/test hashes matched. The
restored source-engine test, identity-consistent rehashed control matrix,
TypeScript candidate/log rollback, Python pre-publication rejection with exit 2
and empty stdout, and valid publication controls all match the reviewed files.
Both focused tests are in the local coverage source list. The manifest now
binds local and reviewed digest
`1813f333a918cdf81c2f754ed64b53d29eb77ca3c75f8de9d32d765b96042db2` for this
scoped verdict. The coverage checker and self-test pass after attestation;
`git diff --check` passes. This review does not accept CE-06B, PIPELINE-002, or
complete-episode behavior. CE-06B terminal/segment closure remains the next
closure task, and `faithful_complete_episode:false` remains required.

### CE-06B implementation matrix (2026-10-06, in progress)

| Scenario | Required disposition | Planned source/test evidence |
|---|---|---|
| Continuous episode to normal win | Preserve both original owned requests, all commits, and matching terminal win evidence; actor rows only for acting sides. | Deterministic source-engine win through the runner; validate both full perspective chains and Python publication. |
| Source-derived tie | Preserve matching tie evidence for both sides; include CE-02D raw turn-limit warnings when using that route without widening their grammar. | Source-backed tie fixture or restored deterministic battle; reuse CE-02D warning controls and verify terminal boundary identity. |
| Terminal after one-sided progression | Keep both successor observations; the waiting side receives no action, fabricated request, or DATA-001 decision row. | Existing accepted one-sided progression fixture followed by source terminal boundary; assert actor-only rows. |
| Resumed segment with predecessor/origin chain | Count as initial-to-terminal only when validated predecessor evidence joins the original initial boundary and the entire segment chain. | Resume from committed v2 evidence; validate original request ownership, predecessor identity, and concatenated commits. |
| Resumed segment without chain | Report segment/incomplete; never claim origin-to-terminal closure from the local segment root. | No-predecessor continuation control remains valid as segment evidence but cannot satisfy complete closure. |
| Zero-transition terminal | Preserve a supported terminal boundary/outcome if available; do not invent an action row or transition. | Restored source snapshot already terminal or explicit supported no-action boundary; TS/Python controls. |
| Rehashed tampering | Reject inconsistent result before publication while preserving valid committed evidence. | Rehash outcome/winner/tie, origin/predecessor, cursor, duplicate/gap/reorder, prefix, and final-boundary mutations to reach each semantic validator. |

This is a pre-implementation matrix. `faithful_complete_episode:false` remains
required; no CE-08A/08B or dataset/model work is included.

### CE-06B implementation checkpoint (2026-10-06, ready for separate review)

| Scenario | Final implementation/evidence |
|---|---|
| Continuous win | The deterministic Gen 9 Random Battle run commits 55 transitions. The v2 envelope retains both original owned requests and both observations at each commit; matching final `|win|` references yield `original_initial_requests` and `complete_capture:true`. Full Python publication remains actor-only. |
| Source tie / accepted warning | A pinned Showdown 0.11.10 battle restored from JSON advances through `Battle.endTurn()` at the turn limit. Both public prefixes preserve the already accepted CE-02D warning and final `|tie`; terminal-only capture creates zero transitions/decision rows and remains incomplete. |
| One-sided terminal | Reuses the accepted queued-opponent-Memento Revival fixture. P1 alone acts; both terminal observations are retained with null requests, and P2 receives no fabricated action or DATA-001 row. |
| Resumed with predecessor | The final transition resumes from a replayed committed boundary with the validated prefix envelope. The prior final boundary equals the current origin, the recursive chain reaches the initial requests, and capture can be complete. |
| Resumed without predecessor | The same segment validates as `segment_only` and cannot claim initial-to-terminal coverage. |
| Zero-transition terminal | The restored source tie is represented as `terminal_only`, without invented transitions, requests, or rows. |
| Rehashed tampering | TS and full Python result-path controls cover outcome, winner, terminal cursor/reference, origin coverage/forgery, ownership, gap, reorder, duplicate, and prefix mutation. Python exits 2 with empty stdout; TS rejects without mutating the candidate or original committed result. |

Both perspectives carry v2 observations and exact public prefix/cursor joins.
Only actor bundles become DATA-001 rows. The envelope includes no simulator
snapshot/state, seed, hidden roster/set, foreign request, or future suffix.
Historical evidence v1 remains readable. The implementation does not set
`faithful_complete_episode` to true and does not implement CE-08A/08B.

Final focused validation: `npm run build --prefix sim-core` passed; the focused
`pipeline_episode` and `revival` suites passed 35/35; Python
`test_pipeline_record.py` passed 43/43; the coverage source inclusion check
passed; `git diff --check` passed. Coverage checker and self-test recompute
`5486e61f6c8ab36c2a5bc2155fc1344d3306cfe21cdda1ba7c2d36e4b333915e` from the
listed local sources. The manifest stores it in local `sha256`; the normal
checker and self-test exit 1 only because the separately reviewed digest remains
`1813f333a918cdf81c2f754ed64b53d29eb77ca3c75f8de9d32d765b96042db2` pending
independent review. All synthetic drift assertions pass; no `reviewed_sha256`
or prior scoped attestation was changed.

Exact CE-06B source, test, and supporting-file SHA-256 values. Source/test
hashes are unchanged by the scoped review; supporting-document hashes below
reflect the accepted verdict. The progress note's own final hash is reported
separately because embedding it here would make it self-referential.

| File | SHA-256 |
|---|---|
| `sim-core/src/pipeline_episode.ts` | `56dcbb5fb13f658487eb582d2a70f7144b9e0479f8252a77ea2a0b90a9c35f03` |
| `sim-core/src/pipeline_episode_evidence.ts` | `210d326f235325fbfdc1f8b37faa638c9733bea546b3c6a909d0b7accd0b7d68` |
| `trainer/src/neural/pipeline_record.py` | `be3d450ecefa18f6becddf8e32a6347cfc378a6a39eee67390334eeb593fea32` |
| `sim-core/tests/pipeline_episode.test.ts` | `05acfd43b9802a9ed08404a08c2b4cbe93eb8cbcfa8b6ca62bbed154f30a850e` |
| `sim-core/tests/revival.test.ts` | `621a6e450c435bebff3e26eccf102d538e3b05a74c31a44a1096dc7687f522fb` |
| `trainer/tests/test_pipeline_record.py` | `818406d458d7a18d27bb5fb40531c93438ea9ac00f15e5cc24ed3fb108742869` |
| `sim-core/scripts/check-simulator-coverage.cjs` | `dfa0cbd93e26d197eb9e78fdd92911d554fde240ba80acb8b2bf586d489cd530` |
| `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json` | `069e0aff1fc1e042d6749e16092f4297b1332d64e6140c2e36a729ec357f29d3` |
| `docs/contracts/PIPELINE_EPISODE.md` | `026fd22d49e5a4aad291989ffb6e0359c461b8d4eb8833de147533861d6d5a99` |
| `docs/architecture.md` | `961c2ee3c0c88f6f30e5292db8b7714952834c482966478918c0a6a84074bc5d` |
| `docs/workflows.md` | `43716e77f7e6cbea0c2b7e9bd02e3e62dd9368d7cb254c65ee69ee129c1f0011` |
| `docs/PROJECT_STATUS.md` | `6652ffc0fa865839c5f049c7788869c2bfd69f3d5f41243d29dc95532b756b37` |
| `docs/refactor/STATUS.md` | `20fc70cc8c05423a0a6af35dd455fdd0ba88ade639b9aa8932c4defee21f67da` |
| `docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md` | `48c0958dbb42ced15b65c9f1fda64c8fa7962cd03ab4201b8a406502ffffef62` |

Next steps remain the separate CE-06B semantic review, remaining P0 closure
rows, and then CE-08A/CE-08B evidence and final stop/review packet. This
implementation checkpoint is not CE-06B attestation or complete-episode
acceptance; `faithful_complete_episode:false` remains required.

### CE-06B independent scoped review verdict (2026-10-06): accepted

Independent review found no material CE-06B finding. The exact source/test
hashes above match the reviewed implementation. Fresh validation passed:
`npm run build --prefix sim-core`; focused `pipeline_episode` and `revival`
tests 35/35; Python `test_pipeline_record.py` 43/43; coverage-source inclusion;
coverage synthetic drift assertions; and `git diff --check`. After binding the
reviewed digest, the normal coverage checker and its self-test both pass.

The manifest's local and reviewed CE-06B digest is
`5486e61f6c8ab36c2a5bc2155fc1344d3306cfe21cdda1ba7c2d36e4b333915e`. This is
only a CE-06B attestation; CE-08A/08B, the remaining P0 closure rows,
PIPELINE-002 as a whole, and complete-episode fidelity remain outside this
verdict. Prior scoped attestations are unchanged, and
`faithful_complete_episode:false` remains required.

### CE-08A pre-edit reconciliation checkpoint (2026-10-06, blocked)

The compact reconciliation matrix for every ordered P0 row is recorded in the
closure audit's **CE-08A P0 reconciliation matrix** section. Accepted CE-01
through CE-06 evidence remains reusable only within its separately reviewed
scope. No CE-08A implementation/test was added and the coverage source list and
manifest were not changed.

Three independent acceptance blockers prevent a positive CE-08A suite:

1. **CE-08A-TURN-LIMIT-ORIGIN-CHAIN:** the only source-derived turn-limit tie
   fixture edits a battle to turn 989, restores it, and advances `endTurn()` to
   the warning/tie. It has zero committed transitions and the envelope marks
   it `terminal_only` with `complete_capture:false`; it does not prove the
   original-request-to-terminal chain.
2. **FCE-07-SIMULTANEOUS-OUTCOME-WITNESS:** FCE-07 separately requires a
   source-engine simultaneous outcome. Current `forcetie` settling coverage is
   synthetic, and the restored turn-limit tie is terminal-only; neither is a
   simultaneous-KO episode from original requests.
3. **FCE-01-MANIFEST-AUDIT-DISPOSITION-DRIFT:** the accepted CE-03B source-proof
   narrative is not reconciled with the coverage manifest, which still labels
   five computed `addVolatile` families and `Pokemon.addLinkedStatus` as
   `unknown fail closed` and retains generic lifecycle/semantic known gaps.
   This prevents claiming zero unresolved reachable shapes across FCE-01.

The existing complete normal win is reusable, but these blockers were not
worked around with a terminal snapshot or selected episode. `faithful_complete_episode:false`
remains required.

Validation and identities for this checkpoint:

- macOS host/profile: Darwin arm64, Node `v24.21.0`, npm `11.19.0`, Command
  Line Tools Python `3.9.6`, pytest `8.4.2`; Node-to-Python executable binding
  passed.
- `npm run build --prefix sim-core`: passed.
- Focused CE-06B TypeScript controls (`v2 evidence retains both owners...`,
  `source-restored turn-limit tie...`, and `CE-06B retains terminal evidence...`):
  3/3 passed. Prior focused episode/Revival evidence (35/35) is hash-matched
  and reusable for the accepted CE-06B scope.
- Python `test_pipeline_record.py` and `test_dataset_lineage.py`: 54 passed.
- `npm run check:simulator-coverage --prefix sim-core`: passed for 169
  classified IDs, 111 parser tokens, 86 literal emitter tokens, and 7 computed
  `addVolatile` families. Local digest remains
  `5486e61f6c8ab36c2a5bc2155fc1344d3306cfe21cdda1ba7c2d36e4b333915e`, equal
  to the separately reviewed CE-06B digest; no CE-08A digest/attestation was
  created.
- `node sim-core/scripts/check-simulator-coverage.cjs --self-test`: passed all
  synthetic drift assertions.
- The documented seven-module macOS TypeScript profile command was attempted;
  after 360 seconds Node reported `pipeline_episode.test.js` pending and was
  interrupted. The other modules reported 76 passed, 0 failed. The focused
  three-test episode/revival rerun above passed. The existing simulator-record
  comparison artifact is not regenerated: its generator is bound to base
  `3ddc5fc3060e8da287425e4d08a71a2ffd77184a` and the exact prior patch hash,
  while this checkout is at `6475d01e9d1bf2766339e41ac3d0738902e4046e`.
- `git diff --check`: passed after the audit and status updates.

Pinned identity: `pokemon-showdown@0.11.10`,
`gen9randombattle` / `gen9` / singles / random; manifest source-tree digest
`12d83949635889cd10a51a081890f9dfc6d3ed480eacf2a9a0728fb48e8e086c`;
`sim-core/package-lock.json` SHA-256
`4897b92e6a6c82db2b8fe5cedb69c9b15386a0bff4d8d2a30b7a2c6d1d9a33c5`.
The current CE-06B source/test/config hashes are preserved below; they did not
change in this blocked CE-08A reconciliation.

| File | SHA-256 |
|---|---|
| `sim-core/src/pipeline_episode.ts` | `56dcbb5fb13f658487eb582d2a70f7144b9e0479f8252a77ea2a0b90a9c35f03` |
| `sim-core/src/pipeline_episode_evidence.ts` | `210d326f235325fbfdc1f8b37faa638c9733bea546b3c6a909d0b7accd0b7d68` |
| `sim-core/tests/pipeline_episode.test.ts` | `05acfd43b9802a9ed08404a08c2b4cbe93eb8cbcfa8b6ca62bbed154f30a850e` |
| `sim-core/tests/revival.test.ts` | `621a6e450c435bebff3e26eccf102d538e3b05a74c31a44a1096dc7687f522fb` |
| `trainer/src/neural/pipeline_record.py` | `be3d450ecefa18f6becddf8e32a6347cfc378a6a39eee67390334eeb593fea32` |
| `trainer/tests/test_pipeline_record.py` | `818406d458d7a18d27bb5fb40531c93438ea9ac00f15e5cc24ed3fb108742869` |
| `sim-core/package.json` | `2fd16727a1d8ff5bdcb974661e58fd1c9b2c0ddcb232854b8f55c2de735c7174` |

### CE-08A three-blocker closure batch — pre-edit matrix (2026-10-06)

Before implementation, the single blocker matrix was recorded in the closure
audit under **CE-08A blocker closure batch — pre-edit matrix**. It binds
`CE-08A-TURN-LIMIT-ORIGIN-CHAIN`, `FCE-07-SIMULTANEOUS-OUTCOME-WITNESS`, and
`FCE-01-MANIFEST-AUDIT-DISPOSITION-DRIFT` to the pinned Showdown source paths,
required valid evidence/envelope state, privacy boundaries, tests, and explicit
failure conditions. No result or closure is implied at this checkpoint. The
batch must preserve `faithful_complete_episode:false` and leaves final CE-08A
positive-suite attestation to a later review.

### CE-08A three-blocker closure batch — execution checkpoint (2026-10-07)

The one pre-edit matrix is in the closure audit under **CE-08A blocker closure
batch — pre-edit matrix**. The audit now includes the B05/B06/B09/B11/B12/B13
source-proof crosswalk and current execution checkpoint.

- **FCE-07-SIMULTANEOUS-OUTCOME-WITNESS:** both mirrored Destiny Bond source
  witnesses pass from original requests. The route records the two faint events,
  matching source terminal outcome, no terminal requests, deterministic replay,
  and valid Python publication. A fully rehashed terminal-outcome tamper is
  rejected without TypeScript state mutation; Python exits 2 with empty stdout.
- **FCE-01-MANIFEST-AUDIT-DISPOSITION-DRIFT:** six computed paths now match
  source, manifest, audit, focused-test, and fail-closed dispositions. The
  coverage drift self-tests and focused simulator-coverage tests pass. Aggregate
  FCE-01 remains open beyond these six paths.
- **CE-08A-TURN-LIMIT-ORIGIN-CHAIN:** the fresh-initial-request → committed
  predecessor → legal switch-only source run → turn-1000 tie test passed in
  599.6 seconds. It retains full TypeScript and Python envelope validation,
  every cursor/prefix/origin assertion and rehashed outcome/origin controls,
  and publishes both perspectives at the origin and terminal-adjacent
  boundaries. A later contract review determined that these endpoint rows do
  not establish Python publication of each intermediate actor bundle: the
  evidence-only bridge checks envelope boundaries, while full-result mode
  validates every actor bundle before returning DATA-001 rows. An earlier
  all-row attempt was interrupted after 34 minutes due to repeated growing
  prefix validation. The source origin chain is sound, but the publication
  evidence subcriterion remains open for a bounded cache/bulk follow-up that
  preserves validation of every actor row. Do not treat the removed all-row
  loop as redundant for CE-08A publication acceptance.

Verified: TypeScript build; focused source turn-limit episode (1 passed); both
source simultaneous episode tests (2 passed); rehashed continuation-origin
control (1 passed); Python pipeline-record and dataset-lineage tests (54
passed); simulator-coverage tests (9 passed); coverage synthetic-drift
self-tests (all cases printed passed); reachability self-tests (exit 0); and
`git diff --check`. Final local source digest is
`f23f05dd3a4dfb6a30eca5d6cf985df22e68c5150d5bf68723468a90e36e3616`; the
manifest's local `sha256` is updated to it. `reviewed_sha256` remains
`5486e61f6c8ab36c2a5bc2155fc1344d3306cfe21cdda1ba7c2d36e4b333915e`, so the
normal checker and `--self-test` exit 1 only because the separate
semantic-review digest has not been refreshed. No local digest drift or other
coverage-checker finding remains. No CE-08A attestation or complete-episode
claim is made, and `faithful_complete_episode:false` remains required.
| `sim-core/package-lock.json` | `4897b92e6a6c82db2b8fe5cedb69c9b15386a0bff4d8d2a30b7a2c6d1d9a33c5` |
| `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json` | `069e0aff1fc1e042d6749e16092f4297b1332d64e6140c2e36a729ec357f29d3` |

The matrix and three blockers are recorded in the closure audit and surfaced in
the current project/refactor status summaries. Exact SHA-256 values after the
final whitespace check:

| Changed file | SHA-256 |
|---|---|
| `docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md` | `16366eec22ce8244e7e5216285e379466913a80e6ba77cf5e6d4abcd758990ea` |
| `docs/PROJECT_STATUS.md` | `a8b567ec06ed5db737822c89cc9e81192c045bff5ff9313826fcc7b47bda720a` |
| `docs/refactor/STATUS.md` | `255480c26c62270f521c3a4e738d4daad0aa3c5de40f126d2451cc185f625b2b` |

The progress document's own final SHA-256 is reported with this checkpoint's
results to avoid a self-referential hash.

### CE-08A blocker batch — final changed-file hashes (2026-10-07)

| File | SHA-256 |
|---|---|
| `docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md` | `11aadaa397a3d4a98321b93a6a225bc479dd43a50a302139d1896cf028cceb8c` |
| `docs/PROJECT_STATUS.md` | `ded9c164d9a1b6d4bd4459fe98c879fa3c6e2e4f41b96f5c3cd69eff23ac83ff` |
| `docs/refactor/STATUS.md` | `0de11cce7ce67784473458f7f7501c872b0341889facf980515109cbcbc7edf1` |
| `sim-core/tests/pipeline_episode.test.ts` | `45cd959dd81db739da3e0c81fd4d602612625fff7e49be8caba3981f06e2261e` |
| `sim-core/scripts/check-simulator-coverage.cjs` | `2584cba229445e179b27e24651fe44c368f9e6337b350559d4f4d2990a9bb3f4` |
| `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json` | `9ea75cc85fa9a0ac3d96c9d3016e8ae9bcd858b6c746ab24ff863ff94a0dc9b7` |
| `sim-core/tests/simulator_coverage.test.ts` | `a9d1efb19a78eab71fde2ef411d0b004851000273755e4cd5fc949c3384b485b` |

The progress document's own final SHA-256 is reported in the completion
message to avoid a self-referential value.

### CE-08A blocker-batch independent review checkpoint (2026-10-07)

The pinned turn-limit episode is bound from original p1/p2 requests through a
committed predecessor and validated continuation to the source turn-1000 tie;
the source-chain finding is closed. The simultaneous Destiny Bond witness is
also source-derived from original requests, and the six computed volatile
manifest/audit dispositions are aligned with pinned source evidence and
fail-closed drift checks. The review did not attest the blocker batch because
the turn-limit path lacks direct Python publication evidence for its
intermediate actor-only DATA-001 rows. FCE-02 requires every boundary; the
PIPELINE_EPISODE and DATA-001 full-result contract additionally validate each
actor bundle before emitting rows. The smallest follow-up is a bounded bulk
publication run that reuses only immutable prefix/boundary validation already
established for the same identities, while executing every bundle-level owner,
action, transition, privacy and DATA-001 validation. It should publish/count
every actor row and prove a rehashed invalid middle row exits 2 with empty
stdout; publish the continuation predecessor row separately. No change to
`reviewed_sha256` or semantic attestation was made. Keep
`faithful_complete_episode:false`.

Current independent-review file identities:

| File | SHA-256 |
|---|---|
| `docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md` | `f493cde689af3bfce0a89548c20ec19c08e363b2d93f9262b904abacd7b285c0` |
| `sim-core/scripts/check-simulator-coverage.cjs` | `b691c1c07cf0a27546bffab6e7bf1bbde8fbd1da89250e6fbe2b0bb5045eeed3` |
| `sim-core/tests/simulator_coverage.test.ts` | `73d1635809eefb90be335d531ff4d5ad7935cefc9bb8e5fa502724fe462791ed` |
| `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json` | `6f7d64f1a8f4b8a6dd6f915bd19883803be78af3dd2ad35dd5eb59dab733de50` |
| `sim-core/tests/pipeline_episode.test.ts` (reused source-turn evidence) | `45cd959dd81db739da3e0c81fd4d602612625fff7e49be8caba3981f06e2261e` |
| `sim-core/src/pipeline_episode_evidence.ts` (reused source-turn evidence) | `210d326f235325fbfdc1f8b37faa638c9733bea546b3c6a909d0b7accd0b7d68` |
| `trainer/src/neural/pipeline_record.py` (reviewed contract path) | `be3d450ecefa18f6becddf8e32a6347cfc378a6a39eee67390334eeb593fea32` |

The progress document's own hash is reported in the review completion message.

### FCE-01 aggregate reconciliation checkpoint (2026-10-07, blocked)

The machine-checkable C01–C30 reconciliation matrix now lives in the coverage
manifest and is enforced by `check-simulator-coverage.cjs`. It reconciles
historical discovery prose with later scoped source proofs; the B05/B06/B09/
B11/B12/B13 computed-family crosswalk remains closed and fail-closed for novel
emissions. The scanner/checker now refuses a missing C01–C30 matrix or an
aggregate disposition that hides unresolved rows.

The reconciliation identifies four unresolved reachable P0 families:
`FCE-01-VOLATILE-LIFECYCLE-TRUTH` (C17),
`FCE-01-SIDE-CONDITION-LIFECYCLE-TRUTH` (C20),
`FCE-01-CALLBACK-COMPOSITION-TRUTH` (C22), and
`FCE-01-SLOT-EFFECT-SUFFICIENCY` (C23). C17 lacks aggregate proof that every
reachable typed volatile preserves truthful public presence through expiry,
silent removal, transfer, switch, faint, and re-entry. C20 lacks aggregate
proof for every reachable side condition's layers, cap, expiry, and
effect-specific updates. C22 and C23 have finite accepted witnesses but lack
the aggregate source-route/sufficiency proof required for FCE-01. Those
witnesses remain accepted evidence; they are not aggregate closure.

Because FCE-01 is blocked, no final CE-08A positive complete-episode suite or
semantic attestation is added. The accepted normal win, original-origin
turn-limit tie, source simultaneous outcome, two-perspective envelope, and
1,996-row bulk publication sweep are retained as reusable evidence. Keep
`faithful_complete_episode:false`.

**Validation and identities.** `npm run build --prefix sim-core` passed.
`node --test --test-name-pattern "v2 evidence retains"
sim-core/dist/tests/pipeline_episode.test.js` passed (1/1, 12.3 s), and
`node --test sim-core/dist/tests/simulator_coverage.test.js` passed (9/9).
`.venv-simulator/bin/python -m pytest trainer/tests/test_pipeline_record.py
trainer/tests/test_dataset_lineage.py -q` passed (54/54, 8.91 s). The recorded
turn-limit bulk sweep remains reusable: current
`sim-core/tests/pipeline_episode.test.ts` SHA-256 is
`0e7c26510840ff31eaaa0a529e24a59d8cf358a15e84c9abd9c04f5604920005` and
current `trainer/src/neural/pipeline_record.py` SHA-256 is
`b265e36f7cab1d4aff141ade39868cc9becaee483e279b18ced73da6653ab51f`, matching
the accepted 1,996-row sweep checkpoint. `git diff --check` passed.

The coverage self-test passed its new FCE-01 missing-matrix and aggregate-drift
controls. The current local coverage-source digest is
`acf7b84320f7a44f9a47209314ef38f0ec8e09265f7bc501b3ebbb65060aa7a3`.
`reviewed_sha256` deliberately remains
`b68c508274203f8f470d6b98b9bacd24357d7f703fd209e23445dd0e15a20145`; both
normal and self-test checker invocations therefore exit 1 only with
`local coverage sources are not bound to a separate semantic-review digest`.
No semantic attestation or CE-08A positive suite is claimed.

| Changed file | SHA-256 |
|---|---|
| `sim-core/scripts/check-simulator-coverage.cjs` | `ede5caad807ddc6e9526742e26fede6f38c290abadd7fe95975d8636d067c8ac` |
| `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json` | `9f8ea327da2ceddc4849b1b44933d8ced518ade67b725d57588891339089ff77` |
| `docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md` | `68cb59efc6ef107165a4e3cc1a94b363a6e2ce6162ba8eda0a7c0d8a50bf42f1` |
| `docs/refactor/STATUS.md` | `6be4b5408077b08138454ac2f4c8436a0d00f7704c933870fd803827a0dec7e8` |

The progress document's own final SHA-256 and the current project-status hash
are reported with completion to avoid a self-referential value.

### FCE-01 independent-review correction (2026-10-07)

Review found that the initial aggregate matrix promoted C22 callback composition
and C23 slot-effect sufficiency from finite witnesses without their required
aggregate source-route proof. The matrix now records C17, C20, C22, and C23 as
unresolved. The checker now rejects an attempted promotion of any of those four
rows even if a tampered matrix also changes the aggregate disposition to
`zero-unresolved`. No production behavior or CE-08A suite changed.

**Review validation.** The independent review correction added a synthetic fully
resealed promotion control: it changes all four unresolved rows to accepted and
sets `aggregate_disposition` to `zero-unresolved`; the checker rejects the
candidate because C17/C20/C22/C23 require their missing aggregate
source/lifecycle closure. Build passed; the focused v2 two-perspective envelope
test passed (1/1); and the simulator Python record/dataset-lineage suite passed
54/54. The ordinary checker exits 1 only because the local digest
`e74e6b853f29f99febe0e8adbb47455fc322ba5dcfa8796736234bc8d7f39797` has not
received separate semantic review; `reviewed_sha256` remains
`b68c508274203f8f470d6b98b9bacd24357d7f703fd209e23445dd0e15a20145`.

| Corrected file | SHA-256 |
|---|---|
| `sim-core/scripts/check-simulator-coverage.cjs` | `7627b0f39354650b6b95751befeac615055963d9cbda66820f768a3b66dd8f75` |
| `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json` | `1c35ee6551e19c68ea1b18be7f6a939d963cb8269ea0f1c3142f49862a67e4e8` |
| `docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md` | `301e3c9896588f9293daf1e02ed60e1cb31d9f85fb5a0c15186d2dd0fb83f215` |
| `docs/refactor/STATUS.md` | `1158f2783766c3eb100c33eb5276d5d7e0ebf704d713efd0844141648b9e7fb8` |
| `docs/PROJECT_STATUS.md` | `cffe4edda67b760891f6fa825317fa3cb1a86b056c01e995361938e96c36cd4e` |


### C17/C20 evidence-derived typed-state boundary — implementation checkpoint (2026-10-07, unreviewed)

Added `public-typed-state-lifecycle/v1` to the pinned simulator manifest. The
matrix covers all 88 move-volatile IDs and 23 side-condition IDs. It retains only
Substitute as typed volatile presence and eight source-rooted side conditions
(Spikes/Toxic Spikes capped at 3/2; Stealth Rock, Sticky Web, Reflect, Light
Screen, Aurora Veil, Tailwind presence). The other 87 volatiles stay raw-only; 15
unrooted side conditions fail closed while callback composition remains C22 work.
The checker now rejects a missing lifecycle row/semantics, a classification
change, an unreviewed generated side root, or a false typed promotion.

TypeScript replays each normalized retained prefix and compares it with the
projected typed map at observation/belief validation. Python independently
replays before DATA-001 publication. Fully resealed Substitute, hazard-layer,
and screen-presence tampering rejects in both runtimes; Python exits 2 with empty
stdout and TypeScript preserves the committed boundary. Existing source-engine
witnesses cover both perspectives, restore/replay, hazard caps/removals, screen
expiry/Defog removals, Court Change, Substitute clearing, and exact Shed Tail-only
transfer. Private timers, callback state, hidden sets, and snapshots remain
excluded.

**Validation.** `npm run build --prefix sim-core` passed. The focused TypeScript
suite passed 96/96: lifecycle atlas, pipeline publication/tamper, environment
lifecycle, extractor, coverage, hazards, screens, and Court Change.
`PYTHONPATH=trainer/src python3 -m unittest -q trainer.tests.test_typed_state
trainer.tests.test_pipeline_record` passed 46/46.
`node sim-core/scripts/check-simulator-coverage.cjs --reachability-self-test`
passed all synthetic controls, including the new lifecycle drift checks. The
ordinary coverage checker exits 1 only with
`Manifest incomplete: local coverage sources are not bound to a separate
semantic-review digest`; this is expected because `reviewed_sha256` remains
`b68c508274203f8f470d6b98b9bacd24357d7f703fd209e23445dd0e15a20145` pending
separate review. The local digest is `c5a5fc3112a1778af1adb9e5b817b9639b1b183ac8a6d42f6ccc0ea043d12e4d`.
`git diff --check` passed.

C17/C20 remain unreviewed and are not attested. C22 callback composition and C23
slot-effect sufficiency remain unresolved; the FCE-01 aggregate stays open, no
CE-08A positive suite is claimed, and `faithful_complete_episode:false` remains
required.


| Changed file | SHA-256 |
|---|---|
| `sim-core/src/typed_state_lifecycle.ts` | `e3bc8c6777845ef79d95115fcb80883ee73816c69089a121ef16eae73d8811c9` |
| `sim-core/src/effect_inventory.ts` | `5076ac35c8d0a05833eddff08d6067ed74b73997b3134fd5e5e2dcf2279810e9` |
| `sim-core/src/state_extractor.ts` | `70fdb463f277d88d085f93a42f3067f17f081f291403a2ccb794175703985899` |
| `sim-core/src/observable_state.ts` | `5f1bcda1970b7b15e7e85523a3ac50291c544868336d16b291793ba162cb7315` |
| `sim-core/src/belief_state.ts` | `8cf78318f608d26570dbd01474e4be61c91690e2b801646cce6b7684b388cc6c` |
| `sim-core/scripts/check-simulator-coverage.cjs` | `c06b178d10334a8bb5c977bfc106650e5198f68b14d0b1a10323858f3027a6fb` |
| `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json` | `d57ce9d5279015de25130efee4e1129f00c2ff5594928504a7dc47b7a6073fae` |
| `trainer/src/neural/typed_state.py` | `bacc716442abfc8b9ea3a6ffd95cff16be0b55efcdfb18a4cd6495f359029670` |
| `trainer/src/neural/pipeline_record.py` | `9135255437b7895764a4a0783cc0a61892c23bc3871fa57c109cb7381e8651f4` |
| `sim-core/tests/typed_state_lifecycle.test.ts` | `14c931490aaaa4db0e165fb8b94c02aa2c25d756bbe5fb93d47058f41f011dbe` |
| `sim-core/tests/pipeline_integration.test.ts` | `d22ea3887df915d12e8746d0d605704c98849c9d8ea2082c449cc3e12c52d85a` |
| `sim-core/tests/env_manager.test.ts` | `867c44976688d5db3ab80f5a5fc32ca659d62c19d27f1ae58ee4be9a2f89e90e` |
| `sim-core/tests/simulator_coverage.test.ts` | `44f8b9f95caaf65f57d3c0960fdc8768d0550c24206e379eeefce2b634d01e38` |
| `trainer/tests/test_typed_state.py` | `9cf448129a4364142f3bc0fb0a6ca05818f9f6020e66b3d5c1b302bac7169bbc` |
| `trainer/tests/test_pipeline_record.py` | `3e12cb241dd94e9757313250404682751e7d8a464d36b468590a36e08addbddc` |
| `docs/contracts/PIPELINE_EPISODE.md` | `a45dd5d70b69b06bf353b571da436cacee7b97b5752e0745330aeec816d1d820` |
| `docs/architecture.md` | `2d3b41534c7ddd55815e8051a5ec1f2c60f4c33e27f3af758291d9d088d334b7` |
| `docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md` | `337a5051f7b31fea0ac2e1ddf747a961346541f1cf5b5788a4d4698542e39a27` |
| `docs/refactor/STATUS.md` | `99809e1d8d8d7614a1b7055fe4caf81cefdc07b2d7edaf65684bbfe802c6fec5` |
| `docs/refactor/PIPELINE-CORRECTNESS-2026-09-24-PROGRESS.md` | computed after this table to avoid self-reference |


### C17/C20 typed-row omission repair — 2026-10-07

Review finding: a prefix-derived nonempty Substitute state could be omitted
from a perspective roster and evade typed-state validation because validators
compared replay only against rows present in the view. Both runtimes now require
exactly one canonical row on the correct perspective for each nonempty volatile
ident; missing, duplicate, and wrong-side rows reject without synthesizing or
inferring hidden rows.

The ordinary linked-record control fully rehashes observation, belief and record
identities. The v2 episode-origin control additionally rehashes every affected
p1 observation and reference, belief chain, initial/final summary, actor record,
run/origin and envelope identities. It reaches the intended typed lifecycle
evidence mismatch. Valid Substitute remains accepted; Python rejects the
omitted-row ordinary and v2 controls with exit 2 and empty stdout. TS preserves
the committed boundary.

Validation passed: build; targeted TS lifecycle/ordinary-record/v2-boundary
controls (3/3); focused Python typed-state and pipeline-record tests (47/47);
coverage reachability self-test; and `git diff --check`. The normal coverage
checker remains exit 1 solely for the separate semantic-review digest gate.
Local digest: `fd2b787af19a5cc597cd511f25801003382e33649323afb83c9968771a258217`.
`reviewed_sha256` is unchanged; C17/C20 are unreviewed and unattested, C22/C23
remain open, CE-08A remains withheld, and `faithful_complete_episode:false`
remains required.

Repair-specific SHA-256 values:

| File | SHA-256 |
|---|---|
| `sim-core/src/typed_state_lifecycle.ts` | `e3bc8c6777845ef79d95115fcb80883ee73816c69089a121ef16eae73d8811c9` |
| `trainer/src/neural/typed_state.py` | `bacc716442abfc8b9ea3a6ffd95cff16be0b55efcdfb18a4cd6495f359029670` |
| `sim-core/tests/typed_state_lifecycle.test.ts` | `14c931490aaaa4db0e165fb8b94c02aa2c25d756bbe5fb93d47058f41f011dbe` |
| `trainer/tests/test_typed_state.py` | `9cf448129a4364142f3bc0fb0a6ca05818f9f6020e66b3d5c1b302bac7169bbc` |
| `sim-core/tests/pipeline_integration.test.ts` | `d22ea3887df915d12e8746d0d605704c98849c9d8ea2082c449cc3e12c52d85a` |
| `sim-core/tests/pipeline_episode.test.ts` | `037b14647cc1092150eed8726c9e070334cb241ea38a2614112968711721c878` |


### C17/C20 view-less v1 replay bypass repair — 2026-10-07

Python now replays the retained protocol prefix before taking the historical
view-less v1 compatibility path. It permits publication when replay derives no
typed state; derived Substitute or typed side-condition state without a typed
view projection rejects before DATA-001. No roster rows or identities are
inferred. Fully rehashed CLI controls cover view-less Substitute rejection,
view-less Spikes rejection, and successful publication for an empty typed
projection. Ordinary v1 and existing v2 lifecycle controls remain green.

Validation: `PYTHONPATH=trainer/src python3 -m unittest -q
trainer.tests.test_typed_state trainer.tests.test_pipeline_record` passed
48/48. The coverage reachability self-test passed. The normal coverage checker
confirms the local digest and reports only the expected separate
semantic-review digest gate: `reviewed_sha256` remains
`b68c508274203f8f470d6b98b9bacd24357d7f703fd209e23445dd0e15a20145`.
Updated local digest: `a9f78798be0a61c336b4035a0dde64bbbc7fd1b168b3df56efad89fcb2f7c06c`.
`git diff --check` passed. C17/C20 remain unreviewed and unattested; C22/C23
remain open, CE-08A remains withheld, and `faithful_complete_episode:false`
remains required.

Repair-specific SHA-256 values:

| File | SHA-256 |
|---|---|
| `trainer/src/neural/typed_state.py` | `613f86fe1c6581e27a82b0fa416ba6b11d78a4861aeab63bb56220d740f17660` |
| `trainer/tests/test_pipeline_record.py` | `af239aab7d27379d2840ff96a62c4279cb896d0cebccac93b494bee636e03e90` |


### C17/C20 partial typed-view bypass repair — 2026-10-07 (unreviewed)

Both runtimes now require the complete prefix-derived typed representation path:
nonempty volatile values require a unique canonical roster row on the owning
perspective and a present volatile map; own/opponent side-condition values
require `field.side_conditions` and their matching compartment. A missing
container is tolerated only when replay derives no typed value that needs it.
An empty or wrong-side map cannot hide a derived nonempty value. Missing
perspective remains compatible for an empty typed projection and rejects when
the prefix derives state.

Seven fully rehashed controls exercise omitted volatile row/team, missing field,
missing side-condition object, missing own/opponent compartment, and wrong-side
placement. Each TS rejection leaves the committed boundary unchanged; Python CLI
rejects with status 2 and empty stdout. Direct TS/Python controls cover missing
perspective and no-derived partial-view compatibility. A fixture helper now
projects side maps for positive v2 grammar controls that append side lifecycle
records.

Validation passed: `npm run build`; lifecycle/observation/integration TS suite
37/37; v2 episode-origin TS case 1/1; Python typed-state/pipeline-record suites
49/49; coverage synthetic self-test; `git diff --check`. The normal coverage
checker verifies local digest
`9319ea2131a777315e2194240cd2cd3bc18458676a7651a18e1f18161f2836c2`; it exits
1 only because `reviewed_sha256`
`b68c508274203f8f470d6b98b9bacd24357d7f703fd209e23445dd0e15a20145` remains
unchanged pending separate review. No attestation is claimed. C17/C20 remain
unreviewed; C22/C23 remain open; CE-08A remains withheld and
`faithful_complete_episode:false` remains required.

Repair-specific SHA-256 values:

| File | SHA-256 |
|---|---|
| `sim-core/src/typed_state_lifecycle.ts` | `4d765a382f8119eefa0fe861016cb77ad9582c53c5818712981ffe98a1901ea6` |
| `trainer/src/neural/typed_state.py` | `0858bdcd853b06b7e98c882da826eca5b9f74eec2cd869fe5ca0bca5faada6e4` |
| `sim-core/tests/typed_state_lifecycle.test.ts` | `9e1d4956c7508ef43057b77cf9e49066deeb661ebf66a8244c29dd903f7718f5` |
| `trainer/tests/test_typed_state.py` | `a1e0269ea8c570532d8d4f470c4d6f67fd136bf64b693d899565c23abd9b0d93` |
| `sim-core/tests/pipeline_integration.test.ts` | `aee7214138c83c60e056c317ca6c670414636567227acb0c5d0309b1666041d1` |
| `trainer/tests/test_pipeline_record.py` | `e7c941f8a3ff66c7c9aa03edfb1aa48425565f9149cb01431cbac12c0310ab25` |

### C17/C20 scoped review verdict — 2026-10-07

Independent review accepted C17/C20 only from implementation digest
`9319ea2131a777315e2194240cd2cd3bc18458676a7651a18e1f18161f2836c2`.
It confirmed prefix replay before compatibility, exact roster and field-map
representation for derived typed state, fully rehashed no-publication controls,
and valid historical empty-projection controls. The manifest now records C17/C20
as accepted scoped; C22/C23 remain the two FCE-01 blockers. The global
`reviewed_sha256` remains unchanged. `faithful_complete_episode:false` remains
required.

## C22/C23 independent review correction — 2026-10-08

Independent review withholds C23 acceptance: six fully rehashed real Wish
successor HP/status/fainted maps pass TypeScript validation and Python
publication for both perspectives, while private pending-slot controls reject.
The source-route atlas and valid extraction/restoration witnesses remain
reusable; they do not establish semantic result-map rejection. C22/C23 are the
two FCE-01 blockers. Manifest, checker, current contract and status records are
corrected accordingly. Exact probe hashes and reproduction steps are recorded
in the closure audit's 2026-10-08 correction.

Fresh TypeScript build and 75 focused callback/slot tests passed; the Python
pipeline-record suite passed 45/45. Production and tests are unchanged. The
local coverage digest is refreshed while `reviewed_sha256` is unchanged; no
C22/C23 attestation, CE-08A/CE-08B acceptance, or complete-episode claim is made.
`faithful_complete_episode:false` remains required.


### C22/C23 restart checkpoint — 2026-10-08 (unfinished; no attestation)

Work is preserved in the existing checkout. Background test processes have been stopped for the requested app restart. Do not run the entire `pipeline_episode.test.js` file as a quick smoke check: it includes the 1,000-turn source-chain publication fixture, and the default isolated reporter buffers the file's output. Heavy episode processes were run concurrently during this batch; those long runs are not successful evidence.

The item/identity implementation and coherent adversarial helpers are present. The earlier frozen-source matrix passed 37/37 (ordinary 2,524, full-result 196, envelope 200, sweep 196 negative candidates); source/adapter suites passed 197/197 and Python suites passed 121/121. Subsequent terminal-switch corrections invalidate reuse of those whole-source hash-bound results until the affected checks are rerun. The long turn-limit run failed at terminal projection after 4,248.3 seconds. A source-derived near-terminal probe identified an overbroad own-switch guard and stale terminal active flags; narrow corrections and base/current owned-ability authority checks are in progress. An incoming unrevealed terminal Illusion switch still requires an explicit action-authority/staging disposition. C22/C23 remain unresolved.

Parent restart checks: `npm run build --prefix sim-core` exits 0. With the accepted macOS Python profile, the exact focused episode test `v2 episode origin boundary requires exactly one visible Substitute roster row` passes 1/1 in 1.870 seconds; `git diff --check` passes. Use `--test-isolation=none --test-reporter=spec` with an exact `--test-name-pattern` for visible bounded checks.

Next: read the latest closure-audit restart checkpoint and current source hashes; resolve and validate remaining terminal identity authority or document its exact blocker; rerun affected short suites first; run only the optimized 1,000-turn fixture by itself after source freeze; refresh the candidate digest and run coverage checks. The reviewed digest stays `b68c508274203f8f470d6b98b9bacd24357d7f703fd209e23445dd0e15a20145`. Preserve prior attestations, `faithful_complete_episode:false`, CE-08A/CE-08B, and PIPELINE-002 gates.


### C22/C23 resumed source freeze and sequential validation — 2026-10-08

The incoming unrevealed terminal-switch obligation from the restart checkpoint
is implemented using the validated canonical owned switch action and predecessor
slot. Bare envelopes without the action reject; native private restoration uses
separate terminal-request-history/v2 provenance and cannot authorize public
publication. Historical departed unrevealed carriers stay raw-only/unknown;
current addressed possession remains exact, and attributable non-Illusion
history omissions reject. Exact source waiting requests carry the full roster.

The parent now owns sequential validation; no child-owned test/build process
remains. The current baseline is `/tmp/c22-c23-parent-validation-freeze.json`.
The test-only near-turn-1000 diagnostics changed its test hash after the earlier
freeze; production hashes are unchanged. The exact near-turn-1000 test passed
1/1 in 28.210s. A fresh build passed in 1.650s. The final 48-case matrix includes
33 mirrored/source-profile cases and 15 ordered-evidence/representation unit
cases; detailed counters and remaining sequential results are recorded in the
closure audit after completion. Previous interrupted, pre-correction or timed-out
runs are not counted as final passing evidence.

C22/C23 remain OPEN pending independent acceptance. Reviewed/prior attestations
and complete-episode gates are unchanged; `faithful_complete_episode:false`
remains required. No dependency, dataset, training, live, PR or commit operation
was performed.


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

The current-source focused TypeScript suite passed 241/241 and Python passed
58/58. The episode shortcut passed 33/34 before a test-only diagnostic update;
the corrected affected case passed 1/1 under the final hash. The source-derived
1,000-turn run is still unverified because its earlier outer timeout interrupted
Python bulk publication; no further long run was started after the user's
fast-stop instruction. The final test-only hash is
`sim-core/tests/pipeline_episode.test.ts` =
`1b3f39fbb948f4d547aa6359251d335c501c70d3e0ab3bed3712d2af66d275f4`.
The closure audit holds the other exact source/test hashes and scoped evidence.
The local coverage digest is refreshed separately; `reviewed_sha256`, prior
attestations, and `faithful_complete_episode:false` remain unchanged. C22/C23,
FCE-01 aggregate, CE-08A/08B and PIPELINE-002 remain open.

Final reproducible local candidate digest:
`29b17a3cdfb762f8912c850640bec6d30842503fb92e0df11a18f4d8b86c9fea`
(115 listed inputs). The synthetic coverage self-tests passed. The ordinary
checker and self-test wrapper exit 1 solely at the expected independent-review
gate because local `sha256` differs from unchanged `reviewed_sha256`.
`git diff --check` passed. The complete 1,000-turn witness remains a separate
validation step; it is not recorded as a pass.

### Independent C22/C23 review — 2026-10-09

Acceptance and attestation are withheld. The closure audit's independent review
checkpoint records two reproduced C22 defects: omission of attributable consumed
item history under the Illusion roster guard, and rejection of valid departed
unrevealed Frisk item evidence. It also records the Python prefix-tamper fixture's
earlier-join diagnostic limitation. No production or test file was changed.
The 33 checkpoint hashes matched; 48/48, 241/241, 58/58 and individual short-case
evidence were reused, with only small targeted review probes run. The inspected
terminal identity-authority and canonical history-hashing paths showed no
additional blocker; this does not accept C23 or the aggregate matrix.

The review-documentation update produces reproducible local candidate digest
`e74ef3a3fd8195bffaa3230c15ec29e82ce16c66cfb172c05514b1999bda206f`
over the same 115 inputs. `reviewed_sha256` and all prior attestations remain
unchanged. The combined 182.032s timeout and long publication witness remain
pending, with no further execution or timeout investigation. C22/C23, FCE-01,
CE-08A/08B, PIPELINE-002 and complete-episode acceptance remain open;
`faithful_complete_episode:false` is preserved.

### Three-finding carrier/prefix repair — 2026-10-09

The latest audit checkpoint records the carrier-attribution table, two TS/Python item repairs, fully joined prefix fixture correction, exact hashes and six passing targeted cases. Final build passed; no broad suite was rerun. One expanded canonical-probe attempt hit its 180s deadline; the corrected exact episode case then passed in 17.902s with the specific prefix diagnostics, Python exit 2/empty stdout and preserved evidence. The combined invocation and 1,000-turn witness remain pending. This is author evidence only; C22/C23 and later gates await separate acceptance. Prior attestations and `reviewed_sha256` are unchanged; `faithful_complete_episode:false` is preserved.

Reproducible local candidate digest (115 unchanged listed inputs):
`7970750f40adf90c24a2ed5639fe31f5cbec505e762aac0d2048cfccaf023682`

The 2026-10-09 scoped independent review in the closure audit resolves the three
carrier/prefix repair findings with no material blocker in that batch. All 35
dependency/repair hashes match; the six targeted passes were reused and no test
workload was rerun. Broader C22/C23 acceptance, the combined invocation and the
long witness remain pending. The review-record update yields reproducible local
digest `6c30c8134b8fdb86fe4fac11e56f6b3a98b45f6dcca96a3f03fd872d9e36f915`;
`reviewed_sha256`, prior attestations and `faithful_complete_episode:false`
remain unchanged.

### C22/C23 acceptance reconciliation — 2026-10-09

The closure audit now maps each acceptance obligation to source, implementation,
controls and review. C22 remains OPEN for aggregate callback and copied/opponent/
requestless ability truth evidence. The resolved item/carrier findings are not
reopened. C23's enumerated B22 slot-result and terminal-authority semantics are
accepted scoped; its conservative FCE-01 registration remains OPEN pending a
separate checker/metadata bookkeeping change. No FCE-01 closure is claimed.
The combined invocation timeout and long publication witness remain pending for
their execution/episode scopes; neither supplies C22's missing callback proof.

All 35 dependency/repair hashes and eight pinned route hashes match. Evidence was
reused without executing tests. Historical-prefix canonical identity/parity has
independent scoped review; uncovered callback changes prevent attesting the
whole 115-input candidate. The smallest substantive follow-up is the existing
generated Trace copied-ability truth review with only affected exact TS/Python
publication cases if needed. C23 registration needs only a separate coverage
checker/self-test task, without episode execution.

Reproducible local digest after these record corrections:
`ac8e5dfb61b8eebe5f21db7213d41fd976dec040c5539db25170b3aa0b3e9bb0`.
`reviewed_sha256`, prior attestations and `faithful_complete_episode:false` are
unchanged. CE-08A/08B and PIPELINE-002 remain unaccepted.


### Bounded Trace copied-ability author repair (2026-10-09)

The existing closure audit records the source/representation crosswalk and three
Trace-only repairs: requestless owned copied-name/state concealment, cached
terminal faint ability restoration, and Python v1 opponent-field exclusion.
Exact source/cleanup controls passed 3/3 (0.316s), mirrored v1/v2 joined controls
4/4 (6.371s), mirrored terminal-faint publication control 1/1 (0.993s), and the
exact Python Trace unit 1/1 (pytest 0.20s, wrapper 3.228s). Canonical helpers,
TypeScript immutability and Python exit 2/empty stdout remain required. All
workloads were sequential under real 180s process-group deadlines; none remain
running. No broad matrix, checker/self-test, combined or long witness ran.

C22 remains OPEN for broader composed/temporal source-carrier truth and
independent review. Requestless known/changed copied-name representation is
compatible, without claiming independent private provenance reconstruction.
C23 scoped semantic acceptance and pending formal registration are unchanged.
The same 115 source inputs produce local candidate `40a842004f7b5a33331b3b928b5b000471dc647f684c85f54953ad8000a2bb73`.
`reviewed_sha256`, prior attestations, `faithful_complete_episode:false` and all
later gates are unchanged. This is author evidence, not digest attestation.


### Independent Trace repair acceptance — 2026-10-09

The existing closure audit's independent Trace review accepts only the three
Trace repairs: requestless owned copy representability, terminal faint base
restoration through validated predecessor authority, and ordinary Python v1
opponent-field exclusion. Nine Trace hashes and seven canonical/authority
dependencies match; the ordinary rehash helper also matches. Recorded focused
passes are reused; this review ran no tests, build, checker, combined or long
witness. The finite C22 remainder is non-Trace requestless reveal, Imposter
terminal reset, and permanent form owner current/base replacement. Temporal
`[of]` source identity stays raw; requestless known/changed compatibility does
not require private provenance reconstruction. Source exclusions and accepted
item/health/stage/lifecycle consequence writers remain reusable.

C22 remains unresolved/source_backed:false; C23 is accepted scoped and
registered/source_backed:true. Aggregate FCE-01 stays blocked. The single
review-record digest refresh yields local candidate `250d4eb6a45dfdc212a8e36a1ce545cb7724a0cf12bc91e9e652593e1dbb3a69`.
Reviewed/prior attestations, source/config identity, faithful_complete_episode:false
and later gates are preserved. See the audit's finite obligation table and
recommended exact completion checks; no production/test edits or pending
launched checks.


### Three remaining C22 ability crosswalks — 2026-10-09 author checkpoint

The current closure-audit checkpoint supplies bounded non-Trace requestless reveal, generated Imposter terminal reset and permanent form owner current/base evidence. Exact rooted Embody Aspect boost and conditional Teraform Zero plain literals were added to the existing finite grammar; the Trace-copy domain remains unchanged because the operative packaged runtime sets Teraform Zero `notrace:1`. The audit distinguishes generated carriers/routes, constructed partners, preserving form branches and silent replacement without hidden default inference.

New joined ability publication controls passed 24/24 in 53.884s, with native/fromJSON source equality and private terminal v1 history restoration, 424 ordinary negatives plus 212 full-result and 212 v2-envelope negatives. One final partial-owner state qualification does not execute in those fully supplied terminal-pair controls; their evidence is explicitly reused by branch equivalence. Fresh affected Trace checks passed 5/5; final source/grammar/classifier controls 7/7, Python units 3/3, shared contract controls 2/2 and existing terminal-history migration 1/1 all passed. Final build passed. Commands used exact positive selectors sequentially under enforced 180s process-group deadlines. No broad matrix, full suite, combined episode invocation, 1,000-turn witness, benchmark or checker/self-test ran; no launched check/process remains pending.

All 13 final source/test/dependency hashes and the finite source-to-authority classification are in the current [closure-audit checkpoint](COMPLETE_EPISODE_CLOSURE_AUDIT.md#c22-remaining-ability-authority-crosswalks--2026-10-09-author-checkpoint). The 115-input reproducible candidate digest is `4402ef3763fabb1e38679f77892cee74128c7eb39d1a898c07eda50789a89ef2`. `reviewed_sha256` stays `b68c508274203f8f470d6b98b9bacd24357d7f703fd209e23445dd0e15a20145`. C22 remains OPEN/source_backed:false pending independent acceptance; C23 remains accepted registered, and aggregate FCE-01, CE-08A/08B and later episode gates remain blocked with `faithful_complete_episode:false`.


### Independent C22 ability crosswalk review — 2026-10-09

The [independent closure-audit checkpoint](COMPLETE_EPISODE_CLOSURE_AUDIT.md#independent-c22-ability-authority-crosswalk-review--2026-10-09-acceptance-withheld) records one reproduced requestless invalidation authority defect: generated Imposter public Transform correctly extracts unknown current ability, but a false `levitate/known` self assertion with no current request or validated terminal owner passes canonical TypeScript v1/v2 observation validation and Python's v2 episode-observation entry point. This is a direct typed-boundary defect; no DATA-001/full-result/envelope bypass was demonstrated. The named form/base/state siblings are code-derived. Joined terminal reset/replacement, eligible plain/boost reveal and accepted Trace/other writer controls remain supported and their evidence is reused. All 13 final author hashes match; the Teraform Zero TS/runtime discrepancy prose is corrected because both matching sources contain `notrace`.

C01–C30 reconciliation retains 29 accepted scoped/source-backed rows and C22 unresolved/source_backed:false. C22 and FCE-01 acceptance and whole-candidate attestation are withheld. C23 stays accepted registered; reviewed/prior attestations and `faithful_complete_episode:false` remain unchanged. The one corrected exact reproduction completed in 0.454s; its initial private-split guard rejected before spectator routing was corrected. No suite/build/checker/long workload ran, and no launched process remains. Next prerequisite is the narrow invalidation-authority repair and its named sibling controls, followed by independent review. Combined timeout (182.032s) and 1,000-turn witness remain pending in their existing scopes.

The resulting unreviewed 115-input local digest is `335ff00a79450570f64a8d17b1fe31bed04fdbab9b97843d7c29c4e75ec0e7f5`; `reviewed_sha256` remains `b68c508274203f8f470d6b98b9bacd24357d7f703fd209e23445dd0e15a20145`. This digest is bookkeeping, not an attestation.


### Requestless C22 ability invalidation author repair — 2026-10-09

The existing closure-audit checkpoint records the five-case authority table and scoped Transform/form repair, including independent current/base fields, eligible post-invalidation public writers, exact permanent replacement pairs and partial terminal predecessor continuity. Final exact TS controls passed 6/6 (1.367s), Python helpers 4/4 (2.069s), selected joined controls 4/4 (10.851s) with explicit complete-pair branch reuse, and the affected final replacement writer rerun 1/1 (3.638s). Final build and whitespace check passed. Direct candidates are canonical and immutable; actual publication controls retain valid output and rejection exit 2/empty stdout. No publication bypass is claimed for the original direct finding. No broad suite/matrix, combined or long witness/checker ran, and no task-owned check remains pending.

The reproducible 115-input local candidate digest is `93b0f178484b3a6f9878c5b86ea7df397277de9f8e4c054d57eec8cea461785c`. C22 remains OPEN/source_backed:false pending independent review; C23 stays accepted registered, FCE-01 blocked, faithful_complete_episode:false and later gates unchanged. Reviewed/prior attestations are preserved. This is an author checkpoint, not attestation.


### Independent C22 invalidation review — 2026-10-09

No material repair finding remains. All 13 author hashes match; final focused evidence and selected joined branch-equivalent publication checks are reused. The original canonical v1/v2 Transform candidates now reject for the TS ability rule without mutation; Python v2 independently verifies identity and rejects semantically with exit 2/empty stdout. The only fresh exact replay took 0.293s under a real 180s process-group limit. No suite/build/checker/combined/long witness ran.

C22 receives scoped semantic acceptance for the previously reviewed finite crosswalk plus this authority repair. FCE-01 remains unaccepted: all 30 rows were inspected, but the required C22 checker/manifest registration still reports one unresolved row. Next is only bounded C22 registration/drift validation and final 30-row/composite-review reconciliation; no additional ability implementation is identified. C23, prior attestations, faithful_complete_episode:false and later gates remain unchanged. Combined 182.032s invocation and the 1,000-turn publication witness stay pending.

Unattested local digest: `30b8b3969efc1c4f270cf3c9a8089260ac87f99d85f9f11735c91eacb794ddc5`; reviewed_sha256 remains `b68c508274203f8f470d6b98b9bacd24357d7f703fd209e23445dd0e15a20145`. See the existing audit's independent requestless-invalidation review for scope and exact next prerequisite.


### C22 registration / FCE-01 reconciliation — 2026-10-09

C22 is registered accepted-scoped against its independent finite-crosswalk/invalidation verdict; C23 retains accepted scoped registration. All C01–C30 source/evidence rows reconcile to zero unresolved reachable P0 forms. Explicit scope arrays and proof fragments reject invented acceptance/unsupported expansion; source/lifecycle/privacy and aggregate guards remain. Prior independent implementation reviews and hash-bound deltas support scoped composite digest attestation, including canonical historical-prefix parity; no production changes or new mechanic scope.

Exact checker regression passed 1/1 (4.751s), separate synthetic self-test passed (0.619s), sequential real 180s process-group timeouts. Only the changed checker test was transpiled; no broad rebuild/test ran. Final normal checker/whitespace results follow. Audit checkpoint records changed input hashes and review coverage.

Scoped local/reviewed digest: `adca1c9c1473729f3be7cb4dd40e1c80331ea43cf8aa60eb4d46dea113d4d141`. Previous C17/C20 digest is preserved as prior_c17_c20_reviewed_sha256; all earlier scoped attestations remain intact.

Combined short invocation timeout (182.032s) remains unresolved; individual passes do not establish combined success. Current-source 1,000-turn actor-row publication witness remains pending. Next prerequisite is separately authorized complete-chain witness/CE-08A positive validation, followed by separate CE-08B stop closure. No CE-08A/08B, PIPELINE-002, training/live or complete-episode promotion; faithful_complete_episode:false unchanged.

Final frozen checks: normal coverage checker passed (exit 0, 0.670s); `git diff --check` passed. No validation workload remains active.


### CE-08A one-run current-source validation checkpoint — 2026-10-09

Exactly one authorized long witness ran under a hard 30-minute process-group ceiling; no retry, combined suite, other test workload or implementation change. Entry accepted digest and all 43 recorded hashes matched; macOS CPython 3.9.6 profile and preparation build passed. Full log, command, phase timestamps, status and 21 unchanged hashes are in artifacts/validation/ce08a-current-source-2026-10-09; the existing audit checkpoint contains the evidence matrix and exact failure boundary.

Native original-origin/predecessor/both-prefix chain reached the source warning and matching terminal tie in 143.335s. Python published all 1,996 eligible segment actor rows in 252.492s; predecessor 2 rows passed separately. Rehashed foreign-owner middle row rejected with exit 2/empty stdout and retained TS evidence. Overall witness FAILED (1 selected/1 fail): 490.209s outer elapsed, exit 1, no outer timeout. The later wrong-outcome full-envelope Python subprocess timed out at its unchanged 30s limit, returning null status instead of 2; its no-output assertion and subsequent forged-origin check remain unverified. This demonstrates a validation gap, not a publication bypass. No owned process remains; no user process was killed.

Smallest next task: independently review these partial passes and authorize an isolated long-envelope outcome-validation diagnosis/payload capture plus the unreached origin check. No automatic regeneration/retry or optimization. Existing normal-win/simultaneous/restoration/adversarial short evidence is reused only within accepted scopes. Combined 182.032s invocation limitation remains pending; CE-08A acceptance, CE-08B and PIPELINE-002 remain separate, faithful_complete_episode:false unchanged.

Local documentation candidate digest: `144b763db49fe6d8a8d5dd6a987127be5ca6f787b58e30f180295bedb39f21ce`; reviewed_sha256 remains `adca1c9c1473729f3be7cb4dd40e1c80331ea43cf8aa60eb4d46dea113d4d141`. No attestation is made. No coverage checker or additional suite ran.


### CE-08A isolated outcome/origin diagnosis — 2026-10-09 (artifact blocked; no execution)

Read-only inspection of the prior log/metadata, witness capture runner, canonical test helpers and Python validation order found no saved full result, retained evidence envelope, or mutated candidate JSON. The witness directory contains only witness.log (1,967 bytes) and metadata.json (6,187 bytes); related temporary files are runners/checkpoints/logs, not payloads. Metadata contains command, interpreter, 21 hashes, text progress and exit/elapsed status only. The test sends JSON directly to spawnSync stdin; the capture runner saves console output only. All 21 frozen hashes still match, so the successful original-to-terminal chain, 1,996 segment rows, 2 predecessor rows and atomic middle-row rejection remain applicable evidence.

Runtime diagnosis: pipeline_episode.test.ts:1649 uses pythonRun's ordinary 30,000ms default for the canonically resealed full long envelope. Python validate_pipeline_episode_evidence validates the recursive predecessor, origin identity and every ordered two-perspective boundary before comparing closure.terminal with the derived final outcome (pipeline_record.py:656–664). Boundary validation replays retained public-prefix truth and checks identities; this standalone path repeats work over the long chain. The valid sweep's measured 252.492s establishes substantial workload but does not measure standalone negative latency. Expensive repeated validation / an uncalibrated short timeout is the source-backed likely explanation; no profile, persisted input or internal phase trace proves the exact stalled location or rules out another execution stall. ETIMEDOUT/null status is neither semantic rejection nor acceptance. No production bypass is demonstrated.

Outcome control: NOT RUN in this task; prior attempt timed out with null status rather than exit 2, and its stdout-length assertion was never reached. Origin control: NOT RUN; the previous test failed before constructing forgedOriginRehashed. No payload hashes or fresh canonical/join checks can be supplied for unavailable bytes. Logs and source hashes cannot reconstruct full public prefixes, owned requests, roster views, beliefs and predecessor/commit identities; the deterministic seed is a recipe requiring the expressly prohibited simulator replay, not the missing evidence itself.

Exact artifact prerequisite: a serialized valid evidence_envelope including original predecessor and every retained boundary (the full result/actor bundles are optional for these envelope-only Python checks), or the two exact serialized canonical wrongOutcomeRehashed and forgedOriginRehashed envelopes. Once obtained, independently verify canonical identities/dependent origin joins, then run each isolated Python candidate once under the already authorized sequential 180s process-group limits. Obtaining those bytes currently requires separately authorized capture/regeneration or an external retained copy. No source battle, sweep, test, retry, build, timeout change, production repair or payload fabrication ran here. The authorized isolated executions were withheld solely because their prerequisite payloads are absent.

Independent-review handoff: retain the partial positive results; keep the long-envelope outcome and origin Python rejection evidence unresolved. The historical combined-command limitation and CE-08A/CE-08B/PIPELINE-002 acceptance gates remain separate. reviewed_sha256, prior attestations, local coverage digest and faithful_complete_episode:false are unchanged; only this existing progress checkpoint is updated, outside coverage inputs.


### Independent CE-08A positive-evidence review — 2026-10-09

No material findings. CE-08A is accepted scoped for pinned original-request-to-terminal v2 positive capture: normal win, source simultaneous terminal, source turn-limit tie, every two-perspective boundary, actor-only publication, privacy/truth/restoration and coherent adversarial rejection. Artifact inspection independently verified source/harness/runner and payload hashes, canonical evidence/origin identities and intended-change-only candidates, 999 contiguous commits (1 predecessor + 998 segment), exact prefix/cursor continuity, both original requests and final warning/tie/null requests. Recorded 1,996 segment and 2 predecessor publications and middle-row rejection remain applicable. Actual isolated stdout files are empty; stderr agrees with exit-2 outcome/origin records (115.192s / 5.017s). All 21 baseline hashes and 45 current recorded source/test rows match; only new executable input is the reviewed recovery-only harness. No test, validator execution, battle generation, build or checker ran during this independent review.

Attested local/reviewed 116-input digest: `197d1b90334547f58cef0e4eead41f164838897a16fb7dfb74fa471ff491d3b2`; the prior FCE-01 reviewed digest is preserved separately, along with earlier scoped attestations. Exact scope, artifact hashes and limitations are registered in the manifest and the existing closure-audit review checkpoint. Original long invocation still failed at its insufficient 30s timeout; historical combined short-command 182.032s timeout remains unresolved. Neither is relabeled passing. Matching-source separate evidence is sufficient for this positive scope; no combined rerun is required for convenience.

Next: CE-08B reconcile S01–S12 and prove incomplete/error cause classification, last committed evidence, terminal precedence, truthful complete_capture, actor-only/no invalid publication, and FCE-08 final review identities; reuse existing evidence and run only separately authorized missing short controls. CE-08B and PIPELINE-002 acceptance/any faithful flag change remain separate. faithful_complete_episode:false is unchanged; no dataset/training/live promotion.


### CE-08B stop reconciliation ready for independent review — 2026-10-09

S01–S12/FCE-08 packet is in the existing closure audit's CE-08B QA checkpoint, with seven exact dependency hashes and execution metadata in artifacts/validation/ce08b-stop-reconciliation-2026-10-09/evidence.json. Reused accepted C25/C26 exclusions and CE-08A positive/rehash evidence; all 21 baseline hashes matched before edits. Narrow repairs preserve protocol cause indices/cleanup causes and reject contradictory Python stop/status/counter metadata. Four new focused cases passed in 2.342s; six settling rollback/resource cases passed in 0.502s; build passed. No broad/combined/long or positive witness rerun. Existing actor/identity algorithms remain unchanged; candidate digest is the manifest's local sha256, reviewed_sha256 remains the accepted CE-08A digest.

CE-08B/FCE-08 remains pending independent review of the new metadata paths and packet. Immutable complete_capture evidence does not turn failed cleanup into faithful acceptance; faithful_complete_episode:false is unchanged. Historical combined 182.032s timeout and original long command's superseded negative-timeout failure remain explicitly recorded. CE-08A and earlier acceptances remain intact; PIPELINE-002 and flag promotion stay separate.


### Independent CE-08B/FCE-08 review withheld — 2026-10-09

Seven packet dependencies and the 116-input entry candidate matched; prior focused/positive evidence was reused. Artifact-only exact controls found four scoped blockers: nonobject/unknown-key limit metadata can bypass Python budget/schema checks; both known Revival guards lose their cause; attempted Revival guard accounting conflicts with Python; final evidence construction can throw before structured failure and owned cleanup. Reproduction scripts, payloads and results are in artifacts/validation/ce08b-independent-review-2026-10-09. No production/test repair, battle regeneration, broad suite or long validation ran. CE-08B and FCE-08 acceptance/attestation are withheld; see the audit's independent review for separate FCE-01–FCE-08 reconciliation and the bounded next repair task. CE-08A/prior acceptances and reviewed_sha256 remain unchanged. Historical command failures remain explicit; faithful_complete_episode:false and separate PIPELINE-002/merge/flag gates remain intact.


### CE-08B four-finding repair ready for independent review — 2026-10-09

Strict normalized result-limit schema, distinct safe Revival causes, bounded stopped-candidate accounting and guarded evidence construction/validation with guaranteed owned cleanup are repaired. Three artifact-only exact regressions pass (4.124s / 3.155s / 0.664s); final build passed (1.636s). Canonical saved predecessor controls preserve committed records and candidate content, publish valid controls, and reject invalid metadata/envelopes with Python exit 2/empty stdout. Full matrix and exact hashes are in the existing audit checkpoint and artifacts/validation/ce08b-four-finding-repair-2026-10-09/evidence.json. No battle regeneration or broad/combined/long run. Null-limits invalid-options remains a controller diagnostic but is deliberately unpublishable. CE-08B/FCE-08 await independent review; prior acceptances, reviewed_sha256 and faithful_complete_episode:false remain unchanged. Historical combined timeout and original long invocation failure remain execution limitations. PIPELINE-002, merge readiness and flag promotion are separate.


### Independent CE-08B / FCE-08 acceptance — 2026-10-09

No material finding remains in the four metadata/finalization repairs. Eight repair/fixture hashes, five unchanged prior QA dependencies, accepted CE-08A artifact bindings and pinned source/config tree reproduce. Saved three exact repair passes and prior branch-bound stop/settling/capture evidence are reused; no test/build/battle/checker workload ran in review. S01–S12 and FCE-01–FCE-08 are explicitly reconciled in the existing audit. CE-08B is accepted only for pinned v2 incomplete/error/accounting/cleanup delivery; FCE-08 is accepted separately for its accumulated review evidence packet. Resulting scoped digest is recorded/attested in the manifest, preserving prior attestations. Historical combined 182.032s timeout and original long invocation failure remain documented; separately completed matching-source evidence is sufficient and neither original command is relabeled passing. PIPELINE-002 acceptance, merge readiness and any flag promotion require separate authorization; faithful_complete_episode:false stays unchanged.


### Final PIPELINE-002 capture acceptance / flag decision — 2026-10-09

All seven governing PIPELINE-002 criteria map to the accepted FCE-01–FCE-08 evidence; accepted entry digest and CE-08A/CE-08B dependency/artifact bindings reproduce. Accept pinned Gen9 Random Battle v2 capture/boundary progression. The faithful field is a per-result claim, and current TS literal-false/Python false-only behavior prevents documentation-only true promotion. Keep false; exact follow-up is conditional post-validation/cleanup eligibility and compatible full/compact publication, preserving historical false-valued v1 records. No new capture defect or missing evidence is identified; no tests, battles or runtime changes made. The existing audit records the full criterion/claim matrix. Historical failed invocation/combined timeout remain; merge/CI, dataset/training/live and runtime flag implementation/review remain separate.


### Conditional faithful-result candidate — 2026-10-09

Implemented conditional per-result true only for validated supported original-origin-to-terminal evidence and actor joins after successful owned cleanup; TS/Python independently enforce it. False remains conservative and compatible, including legacy v1; unbound, terminal-only, failed/incomplete/unsupported paths stay false. No canonical identity or DATA-001 change. Three saved-artifact exact flag cases, limits and Revival regressions pass; cleanup first encountered a 30s Python timeout, then the sole diagnostic retry passed all six combinations in 1.644s. Final build passes. Audit checkpoint and artifacts/validation/faithful-flag-2026-10-09/evidence.json contain exact hashes, timings and branch-scoped reuse. No battle/long/broad run occurred. Coverage inputs/local candidate digest are refreshed; reviewed_sha256/prior attestations remain unchanged. Independent runtime-flag review is next; historical combined timeout/failed long invocation and merge/CI, dataset/training/live boundaries remain.


### Independent conditional faithful-result runtime acceptance — 2026-10-09

No material finding remains. Entry 121-input digest reproduces; nine repair/fixture and seven result-log hashes match. Independently inspected eligibility/recursive origin continuity, shared actor joins before successful cleanup, TS/Python ineligible-true rejection, conservative false and legacy compatibility, canonical identity/privacy and ordinary/bulk atomic publication. Reuse six exact short passes; initial cleanup timeout remains failed, sole diagnostic retry passed. No runtime tests or battles ran in review. Accept only pinned conditional per-result runtime scope, preserving PIPELINE-002 and earlier attestations. Resulting digest is independently attested in the manifest. Historical combined timeout/original failed long command and dirty-worktree final-tip integration/CI/merge approval remain separate; no dataset/training/live readiness.
