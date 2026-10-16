# Prompt30: 0.11.11 migration implementation plan

## Source Materials

- [Prompt29 lead decision](perspective-fidelity-prompt29-lead-review.md), [assessment](perspective-fidelity-prompt29-assessment.md), [source matrix](perspective-fidelity-prompt29-source-matrix.md), [proposed gates](perspective-fidelity-prompt29-migration-boundary.md).
- Accepted [B1 API](perspective-fidelity-prompt27-api.md), [B2 API](perspective-fidelity-prompt28-api.md), [trace](perspective-fidelity-prompt24-api.md), [delivery commitment](perspective-fidelity-prompt25-api.md).
- Current `transition.ts`, `pipeline_integration.ts`, `env_manager.ts`, `server.ts`, `pipeline_episode.ts`, reader/contract/inventory modules and Python `pipeline_record.py`; current AGENTS/AGENT_PROTOCOL. Prompt29 research is reused, not repeated.

## Status

Planning only. The lead selected verified npm 0.11.11 before B3; implementation/install is unauthorized. 0.11.10 evidence/readers remain historical, with no second default active engine. [Concrete API decisions A1–A3](perspective-fidelity-prompt30-api-decisions.md) gate execution. Detailed test audit and [first proposed prompt](perspective-fidelity-prompt30-first-prompt.md) accompany this plan.

## PR Status

PR identifiers denote separately authorized local implementation/review boundaries, not publication authority.

| PR | Scope | State | Dependency | Review gate |
|---|---|---|---|---|
| PR-01 | Fixed profiles and historical readers | Proposed | A1 | Historical caller parity, no fallback/global context leak |
| PR-02 | Target snapshot admission | Proposed | PR-01, A2 | PRE entry guard/old callers; LIVE G04–06 at PR-06 |
| PR-03 | Target fidelity/K-source quarantine | Proposed | PR-01 | PRE policy/historical callers; LIVE G07–08 at PR-06/11 |
| PR-04 | Inactive target generation/coverage inventory | Proposed | PR-01 | PRE asset dispositions; LIVE counts/config G09 at PR-06 |
| PR-05 | Inactive target grammar/replay profile | Proposed | PR-01, PR-04, A3 | PRE fixtures/old decoder; LIVE G10–12 at PR-06/07 |
| PR-06 | Candidate dependency/profile activation | Proposed | PRE portions PR-02–05 | Package/canary and target G04–14; no default promotion |
| PR-07 | Target trace/delivery timing | Proposed | PR-06 | Real public-before-request, restore/update/rollback joins |
| PR-08 | Target B1/B2 joint/reorder proof | Proposed | PR-07 | Exact accepted controls on target, independent literals |
| PR-09 | Target forced-switch B2 proof | Proposed | PR-08 | Actor/waiting-owner associations and post-prepare rollback |
| PR-10 | Target Revival B2 proof | Proposed | PR-09 | Supported actual selection/bench heal/reentry/rollback |
| PR-11 | Target provenance/coverage and fidelity disposition | Proposed | PR-04–10 | Independent target-scope acceptance; no automatic true flag |

## Goal

Make one active 0.11.11 runtime truthful about its version, grammar, snapshot authority and bounded fidelity eligibility, preserving explicitly old readers/artifacts and stopping before B3.

## Final Acceptance Contract

- FAC-1: Current native session creation→restore/continue→actor records uses only target profiles and actual same-runtime held associations; old/unknown snapshots never reach target reconstruction.
- FAC-2: Historical version-bound bundles/envelopes/results/sweeps still validate under old semantics and retain literal IDs/bytes. Mixed/unknown profiles reject; decoder selection grants no source authority.
- FAC-3: Real target public-update/owner-request joins, generated B1/B2, forced-switch and Revival paths pass their compact positive/negative/privacy/rollback gates. Constructed mechanics cannot certify generated reachability.
- FAC-4: New source/config/closure inventory and grammar are reviewed as target evidence; target true fidelity needs independent target scope plus existing per-result conditions. Migration may be accepted with fidelity false; three broader requirement failures and training gates stay unchanged.
- Not complete if imported snapshots are trusted by metadata, old rules silently handle target records, private handles escape, or target attestations merely copy old digests.

## Scope and Constraints

Only future separately authorized write sets below; historical assets immutable. No B3/B4, K-source/Python authority adoption, replay acquisition, training or blanket historical retesting. Public schemas and identity algorithms remain unchanged unless A2 requires a separate reviewed portable-import design; no such import is planned. Replay profile selection chooses grammar, not engine provenance.

Default deployment is all-at-once after PR-11. PR-06 activates only a lead-approved disposable candidate checkout containing accepted source bytes, including uncommitted B1/B2 work; the preserved old checkout/runtime remains the default until acceptance. Do not create this checkout now. One default engine; no runtime version-toggle fallback.

## Implementation Shape

Use two fixed immutable reader profiles, not an extensible engine framework or process-global profile mutation. Historical10 binds existing assets; native11 binds new target assets only after activation. Proposed `installedNativeProfile()` returns a frozen descriptor checked against actual package/declaration/lock at producer initialization. Manager/session owns it; LocalBattleEnv verifies the installed descriptor, ManagedPlayer and PlayerStateExtractor receive its immutable reader context. No RPC/options field selects the native profile. Package changes require a fresh process, not global switching. Record metadata selects a decoder, never native authority. A historical reader's positive result cannot satisfy target eligibility or authenticate input provenance. Replay compatibility has a separate fixed context.

Target restore admission runs before `abandonForRestore`, overlay validation probes, cloning/retirement or any `Battle.fromJSON`. Only the session-private B2 ticket/controller's exact pending parent/serialization chain authorizes reconstruction. No public version argument, certificate, copied token or generic snapshot catalog is introduced.

## Codebase Touchpoints

Per-PR lists below are proposed authorized write sets, not permission to edit now. New test filenames/selectors and fixed-profile helpers are proposals. Existing historical JSON manifests, fixtures, reviewed digests and logs stay at their original paths.

## PR / Review Strategy

Execute PR-01→11 in order; each requires independent read-only source/test/evidence review and lead acceptance before its successor. Reviewer must challenge caller wiring and semantic rejection, not merely hash reconciliation. One writer per boundary; no downstream delegation/publication. Stop if a boundary needs unlisted public APIs/schema or a broader guarantee. Never merge an unsafe intermediate engine default merely to advance the stack.

## Parallel Execution Notes

Read-only review of a prepared boundary may overlap the author's documentation. Shared profile/grammar/identity writers and all validation remain sequential. PR-09/10 share B2 fixtures and are deliberately serial. Independent lanes do not duplicate source research or tests.

## PR-01: fixed profiles and historical readers

**Status:** Proposed. **Objective:** preserve old readers and reserve unsupported target profiles. **Dependencies:** A1. **Parallelism:** one writer; bounded independent review only.

### Tasks

- [ ] P1-T1 Add proposed `sim-core/src/version_profile.ts` and `trainer/src/neural/version_profile.py`: closed IDs `historical10`, `native11`, later `replay-compat-v1`; immutable contract/inventory/revision selection. Native11 initially rejects as unadopted; no engine install.
- [ ] P1-T2 Bind reader context through `protocol_contract.ts`, `observable_state.ts`, `state_extractor.ts`, `effect_inventory.ts`, `typed_state_lifecycle.ts`, `belief_state.ts`, `public_ability.ts`, `public_field.ts`, `public_boosts.ts`, `pipeline_integration.ts`, `pipeline_episode_evidence.ts`, `pipeline_episode.ts` and Python `protocol_contract.py`, `typed_state.py`, `public_ability.py`, `public_field.py`, `public_boosts.py`, `pipeline_record.py`. Thread the fixed context into semantic helper calls that currently import singleton rules. Inspect `public_health`/`public_item` helpers in both languages; retain unchanged profile-independent logic only with explicit dependency/equivalence evidence, otherwise return a precise extension to lead. No global swapping or copying whole reader implementations.
- [ ] P1-T3 Add fixed historical wrappers for TS bundle/evidence/result validators and Python bundle/evidence/result/sweep APIs. Public auto-dispatch requires unanimous explicit known record revision; zero-record/unversioned inputs require explicit historical wrapper. Python CLI gains explicit historical-reader selection for those legacy inputs. Freeze original old JSON assets at existing paths; defaults remain old before activation.
- [ ] P1-T4 New `sim-core/tests/version_profile_dispatch.test.ts`, `trainer/tests/test_version_profile_dispatch.py`; add only selected exact historical vectors.
- [ ] P1-T5 Narrow `env_manager.ts`, `server.ts` and session construction in `pipeline_integration.ts`: manager/session→installedNativeProfile→env→ManagedPlayer→PlayerStateExtractor. Include actual RPC/session callers in old-runtime PRE checks; no caller version/profile native option. Historical wrappers use separate immutable contexts in the same process.

### Validation Criteria

G01–G03 in the matrix: actual TS validator/Python CLI publication, old literal outputs, mixed/unknown coherent revision tampering, empty/unversioned explicit handling and interleaved profile isolation. Reuse unchanged mathematical vectors; fresh reader-wiring checks. Independent reviewer signs off complete downstream profile propagation. Safe intermediate: old producer unchanged, target unadopted. Rollback: revert only this candidate boundary; old assets/runtime untouched.

## PR-02: snapshot admission and legacy entry points

**Status:** Proposed. **Objective:** block target imports before side effects. **Dependencies:** PR-01/A2. **Parallelism:** serial env/controller owner.

### Tasks

- [ ] P2-T1 Extend `owner_identity_crosswalk.ts`, `env_manager.ts`, `pipeline_integration.ts`: proposed controller `assertRestoreAdmission(env, serialized, ticket)` validates exact pending held chain at method entry; it never no-ops for disabled/absent authority on native11. Old profile retains old behavior. Reject initial authority-free target restore before abandoning originals/trace or reconstructing overlay probes.
- [ ] P2-T2 Target `EnvironmentManager.forkBeliefEnv` rejects before `belief_fork.ts` `buildBeliefSnapshot` samples teams/constructs its donor Battle. Narrow target rejection also guards direct exported helper calls. `resetFromSerialized` admission precedes both terminal submitted-switch source-validation fromJSON and active-request override regeneration fromJSON. Audit these exact entry calls; no alternate helper may accept external target state. Standalone target raw restore is unsupported.
- [ ] P2-T3 Preserve manager `captureSeededSnapshotEnv`→held handle→`stepSeededTransitionEnv`: it advances the live battle, not fromJSON. Narrow private handle lifecycle in `env_manager.ts`: actual managed world/reset occurrence, retain on preflight rejection, consume after successful step, fresh output handle, revoke on reset/close/post-write failure. Imported/foreign/restarted handles cannot enroll. Normal JSON copies of a valid reference address the same held entry, not new authority. Grant no B2 authority. Direct env seeded steps cannot authorize reconstruction. Document restrictions in `server.ts`, `docs/contracts/SEEDED_TRANSITION.md`, `docs/contracts/BELIEF_STATE.md`, `docs/contracts/PIPELINE_INTEGRATION.md`.
- [ ] P2-T4 New `sim-core/tests/snapshot_admission.test.ts`; selected existing transition/RPC controls. No portable snapshot schema/version field.

### Validation Criteria

G04–G06: real calls, actual fromJSON/write/disposal counters, held valid retry, copied/sibling/mutated/old/unknown states and forged version metadata. Correct rejection must precede helper probes, original abandonment and retirement. Historical standalone restore remains usable only in historical10; target manager live transition still works without fabricated B2. Independent API review is mandatory. Safe state: old default unchanged, target policy armed. Rollback: old checkout/runtime, not relabeled target snapshots.

## PR-03: target claim quarantine

**Status:** Proposed. **Objective:** prevent inherited fidelity and old K-origin adoption. **Dependencies:** PR-01. **Parallelism:** separate from env writer, sequential validation.

### Tasks

- [ ] P3-T1 Add narrow target-scope eligibility lookup in `version_profile.ts`/Python peer. Wire `pipeline_episode.ts` producer/`validatePipelineEpisodeFaithfulClaim`, `pipeline_episode_evidence.ts` and Python result/evidence/sweep validators. Native11 remains false/uneligible without independent accepted scope, regardless of old manifest or self-declared metadata. Preserve historical flag meaning and old10 positives.
- [ ] P3-T2 Guard actual entry APIs in `perspective_knowledge_source.ts`/Python peer so target-native inputs cannot mint protected old10 origins. Do not update old ORIGIN_CONSTANTS, invent target facts or bridge B2 to Python.
- [ ] P3-T3 New `sim-core/tests/target_fidelity_eligibility.test.ts`, `trainer/tests/test_target_fidelity_eligibility.py`; exact bounded terminal stimulus and fully rehashed flag/origin attacks, no long episode.

### Validation Criteria

G07–G08 prove actual producer plus both public validators and no-output failure, not a predicate-only test. Old10 flag controls retain outcome; target completion alone stays false. Independent reviewer checks scope lookup is local reviewed policy, not a transported capability. Safe state: old behavior, target quarantined. Rollback candidate only.

## PR-04: target generation/config inventory

**Status:** Proposed. **Objective:** create inactive target provenance/closure assets. **Dependencies:** PR-01. **Parallelism:** one inventory writer.

### Tasks

- [ ] P4-T1 New `sim-core/simulator_coverage/pokemon-showdown-0.11.11-gen9randombattle.json`; reuse verified Prompt29 artifact/revision/source findings. Explicitly distinguish source-equivalent old evidence from target checks not yet run. No copied reviewed digests, active complete attestation or current status promotion.
- [ ] P4-T2 `check-simulator-coverage.cjs`, effect/lifecycle loaders, Python inventory loaders: fixed profile paths and target-specific checks. Reconcile Gen9 source/rules/selector population and changed reachable effects/writers; preserve actual config/PotD policy. Do not rerun the artifact investigation or weaken checker assertions.
- [ ] P4-T3 New target inventory exact tests in `simulator_coverage.test.ts`/new `target_inventory.test.ts`; target runtime counts/config proof deferred explicitly to PR-06, not falsely marked passed.

### Validation Criteria

G09 source-bound inventory checks and coherently edited/rehashed wrong revision/config/selector disposition negatives. Independently review changed closure claims. Safe state: target data candidate/inactive, default old. Rollback removes candidate target asset/selector changes only; historical manifest intact.

## PR-05: native target grammar and replay compatibility

**Status:** Proposed. **Objective:** prepare exact separate target and replay rules. **Dependencies:** PR-01/04/A3. **Parallelism:** shared TS/Python grammar sequential.

### Tasks

- [ ] P5-T1 New `trainer/src/neural/protocol_contract_0_11_11.json` and fixed replay-compat asset; keep existing `protocol_contract.json` old bytes. Update bound grammar paths in `protocol_contract.ts`, `observable_state.ts`, `state_extractor.ts`, Python contract/semantic helpers only for finite changed reachable families classified in Prompt29. Preserve unsupported dispositions for unselected/admin/future forms.
- [ ] P5-T2 Native Natural Cure requires exact ordered from-ability/silent tags. `replay_import.ts` APIs explicitly select audited replay profile; only it permits the two enumerated exact forms. Prefix routing validates raw source before filtering; preserve every original line/source index, no normalization of silent away. Replay profile never grants original-owner/native authority or target fidelity.
- [ ] P5-T3 New `target_protocol_grammar.test.ts`, `replay_compatibility_profile.test.ts`, Python exact target grammar/publication tests and version-labeled fixtures. Source-shaped real target emitter gates wait for PR-06/07.

### Validation Criteria

G10–G12: actual importer→extractor→observation/bundle→TS/Python publication with coherently resealed malicious records; exact malformed tags and profile-confusion rejection. Independent reviewer checks immutable context reaches all semantic helpers. Safe state: inactive target grammar, explicit bounded replay decoder only. Rollback leaves old assets/readers intact.

## PR-06: exact candidate activation

**Status:** Proposed. **Objective:** install only verified target in isolated candidate. **Dependencies:** PR-02–05 PRE portions accepted; candidate path approved. **Parallelism:** no concurrent runtime work.

### Tasks

- [ ] P6-T1 Preserve old dependency tree/config/lock and accepted source hashes; create approved candidate with exact source bytes. Change candidate `sim-core/package.json`/lock pin/SRI; review transitives/optional-native changes. Activate `version_profile.ts`/Python peer and manager/env/session/server initialization with native11; honest `SIMULATOR_REVISION` in `transition.ts`, Python record consumer and `simulator-record-comparison.cjs`. Actual RPC/session readers bind native11; historical wrappers stay old10. Identity algorithms unchanged.
- [ ] P6-T2 One build; exact target package/types/required Node/Python imports and dependency metadata checks. Verify actual loaded path/artifact files, platform ABI where used, Node24.21.0 and explicit Python/PYTHONPATH without encoding/report overrides. Do not broaden Node support based on npm's ≥16 declaration versus launcher's ≥22 message.
- [ ] P6-T3 One generated initial session and joint step/restore canary; execute deferred LIVE G04–14: target restore/legacy callers, actual producer claim/K-source quarantine, runtime inventory and finite emitter/publication controls. Request-specific timing/update checks belong to PR-07. Earlier unadopted-profile rejection is not a substitute. Failure checkpoints candidate; no default promotion.

### Validation Criteria

G13–G14. Independent review of resolved lock, loaded provenance and caller gate integration. Safe state: isolated target candidate, fidelity false, current default remains old. Rollback selects preserved old checkout/runtime and discards candidate access; never reconstructs target state in old engine. Installation permissions must name candidate path before this PR executes.

The install/canary and deferred LIVE confirmations use already prepared exact cases. A failing confirmation isolates its owning policy/grammar boundary for separately directed correction; PR-06 does not absorb unrelated implementation to make all checks pass. An artifact-only checkpoint is not accepted target support and cannot advance PR-07 or promotion.

## PR-07: changed public-before-request joins

**Status:** Proposed. **Objective:** prove target trace/delivery semantics. **Dependencies:** PR-06. **Parallelism:** one env/ledger test writer.

### Tasks

- [ ] P7-T1 Only if needed, narrow `env_manager.ts`, `request_emission_trace.ts`, `request_delivery_ledger.ts`, `pipeline_integration.ts`; update target docs separately from historical API records. No public cursors derived from trace counts, rqid/string fallback or causal B3 labels.
- [ ] P7-T2 Add exact target timing/request-update tests to trace/delivery tests: independent native update/sideupdate call order and actual owner FIFO receipts; restore reemit including no-log early-return behavior; valid updatedRequest native JSON; terminal/null/wait boundaries.

### Validation Criteria

G15–G17 and specifically affected existing exact controls. Same text must produce new native delivery occurrence; restoration retains parent delivery. Real post-prepare failure preserves both histories/B2 handles; retry is fresh. Reviewer verifies actual producers/callers. Safe candidate remains ineligible; rollback old runtime.

## PR-08: target B1/B2 joint proof

**Status:** Proposed. **Objective:** refresh accepted bounded APIs on target. **Dependencies:** PR-07. **Parallelism:** one new-test owner.

### Tasks

- [ ] P8-T1 Run six exact B1 and six exact B2 cases with target fixtures/literal expectations in existing birth/restore tests; adapt only proven generator/output assumptions, never weaken semantic errors. B1 constructed initial effects stay explicitly labeled.
- [ ] P8-T2 Add narrowly missing target proof; production controller/env/session edits only for demonstrated in-scope defects with lead-approved file expansion. Reuse unchanged algorithm vectors, not old target-runtime passes.

### Validation Criteria

G18: actual generated initial/reorder/restore, fresh objects/sets, exact independent originals, owner and forged-handle negatives, final input set/row-copy rejection, failure/close/legacy target policy. Review disposition distinguishes historical old authority-free restore from target unsupported API. Safe candidate fidelity false; rollback old.

## PR-09: forced-switch B2

**Status:** Proposed. **Objective:** prove supported one-sided restore boundary. **Dependencies:** PR-08. **Parallelism:** serial with Revival.

### Tasks

- [ ] P9-T1 New `owner_identity_forced_restore.test.ts`, selected scaffolding from `forced_switch.test.ts`. Genuine target generated KO/forced path, held same-runtime restore/selection/reentry/continue. If a seed loses the legal path, find one bounded witness or return a gap; no broad seed/episode sweep.
- [ ] P9-T2 Both owner literal slots/refs, waiting owner, delivery joins and candidate post-prepare rollback/privacy/close; separately label constructed native drag/mechanics if required.

### Validation Criteria

G19; actual session and consumer assertion, no lower-level-only substitute. Independent reviewer checks failure after B2 preparation rather than unrelated preflight. Rejected validator fixture stays rejected. Safe scope grows only after acceptance; rollback old.

## PR-10: Revival B2

**Status:** Proposed. **Objective:** prove supported bounded Revival path. **Dependencies:** PR-09. **Parallelism:** serial B2 writer.

### Tasks

- [ ] P10-T1 New `owner_identity_revival_restore.test.ts`, selected `revival.test.ts` scaffolding; actual session selection→bench heal→forced/reentry→ordinary continue with held originals for both owners. Mark constructed producer fixture versus generated target reachability separately; no reachability claim without genuine generated witness.
- [ ] P10-T2 Literal selected original slot, fresh refs and parent/ticket faults, post-prepare rollback/retry, actor/waiting owner isolation and output absence. No transformed/consecutive variants unless claimed supported and separately bounded.

### Validation Criteria

G20; actual validator rejection cannot be bypassed to manufacture integration support. Reviewer independently checks slot/lifetime oracle. Safe candidate scope remains explicitly bounded; rollback old.

## PR-11: target provenance/coverage disposition

**Status:** Proposed. **Objective:** reconcile target evidence and conditional flag policy. **Dependencies:** PR-04–10. **Parallelism:** read-only review; lead owns acceptance/status.

### Tasks

- [ ] P11-T1 Target manifest/checker, target-scope lookup and new target migration/API/evidence docs: reviewed source/config and local-input hashes bind exact accepted target scope. Historical attestations stay untouched; the lead separately decides any target attestation and default promotion.
- [ ] P11-T2 Exact producer→TS/Python result/envelope/bulk-sweep eligibility controls. True can be enabled only if target scope is independently accepted AND existing v2 complete-capture/terminal/actor-lineage per-result requirements hold; otherwise remain false. Do not manufacture target eligibility from historical review_status or matching hashes.
- [ ] P11-T3 Final bounded same-target end-to-end canary exercises creation, committed successor and short supported terminal stimulus/publication; reuse unchanged prior target passes. Separate generated from constructed terminal stimulus. No long chain needed for bounded migration acceptance.

### Validation Criteria

G21–G22/FAC-1–4; independent final review and lead decision. Broad claims absent from fresh evidence remain unsupported. Safe default changes only after acceptance; preserved old checkout is rollback. No in-memory sessions/snapshots cross promotion or rollback; old/new outputs retain their own version/catalog.

## Cross-Cutting Validation

The [exact test matrix](perspective-fidelity-prompt30-tests.md) is the execution contract. One workload at a time, anchored positive case selectors, real 180-second process-group deadlines for short checks; selected Python test node IDs and actual CLI stdin/stdout failure checks. One necessary build per changed compiled boundary; reuse unchanged input proofs. No tests/builds/imports were run while planning.

PRE and LIVE are evidence categories, not implementation phases. PR-01–05 acceptance covers prepared policy/fixture decoding and unchanged actual old-runtime callers. PR-06 depends only on these PRE portions, not target runtime passes. PR-06 owns deferred LIVE G04–14; PR-07 owns timing/update G15–17. PR-11 cannot accept/promote without all LIVE confirmations. Earlier unadopted-profile rejection cannot replace exact target restore/grammar/eligibility rejection. No prepared boundary claims fresh target runtime acceptance.

Broader/long checks require separate lead authorization naming the guarantee/workload: newly claimed long-chain terminal completeness, widened revival/forced variants, newly reachable emitter dependency family, identity/schema algorithm changes or unresolved multi-boundary causality. Package hash drift alone is not a reason. Preserve failed logs and reject before publication; coherently recompute dependent IDs/digests in semantic negatives.

## Open Questions — lead API approval

A1. Approve additive fixed historical wrapper/profile APIs and Python CLI historical selector; default auto-dispatch must reject ambiguous/zero-record/unversioned target input. No new wire schema or generic version registry.

A2. Approve target standalone raw restore, initial authority-free restore and belief-fork RPC as explicitly unsupported; managed live seeded transitions remain usable. A portable snapshot import/resumption contract would require a separate schema/authority decision and is excluded.

A3. Approve explicit replay-profile selection through importer and all publication callers. Existing wire records do not encode native-versus-replay grammar mode; portable replay publication requiring that distinction needs a separately reviewed schema/version contract. Initial native migration must not silently accept replay-union records in native bundles.

Recommended A3 scope is importer-only compatibility; portable replay-union publication stays disabled pending that contract. Exact proposed wrapper names, context field, native controller guard and API compatibility effects are in the API decision sheet.
