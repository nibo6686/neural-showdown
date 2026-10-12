# Implementation Plan: Perspective Fidelity Before Training

**Status:** Lead-owned plan; first three handoffs prepared, no implementation authorized by this document alone.
**Last Updated:** 2026-10-09

## Source Materials

- `docs/PROJECT_STATUS.md`: current reconciliation supersedes its historical readiness table.
- `docs/refactor/COMPLETE_EPISODE_CLOSURE_AUDIT.md`: latest conditional faithful-result review and bounded acceptance evidence.
- `docs/contracts/OBSERVABLE_STATE.md`, `BELIEF_STATE.md`, `PIPELINE_EPISODE.md`, `SIMULATOR_COVERAGE.md`: visibility, uncertainty, episode and coverage boundaries.
- `docs/testing/WINDOWS-SMOKE-2026-10-09.md`: fresh Windows findings, including failing synthetic fixtures and UTF-8 mitigation.
- Current user decision: in public replay reconstruction, retrospectively revealed facts about the perspective owner's starting team are available from turn 1; never-revealed facts stay unknown.

## Status

- Existing conditional `faithful_complete_episode` emission has scoped independent acceptance. This initiative verifies and closes the stronger state-information requirement; it does not restart accepted CE/FCE work or declare universal simulator coverage.
- Windows selected complete episodes, core tests and integration work; Python record regressions fail in two methods, and default piped Python encoding corrupts Unicode.
- This chat owns sequencing, review and acceptance. The user runs implementation prompts in a separate Codex chat and returns its artifacts here. No other chat is created or messaged automatically.
- Publication, commits, merge, package installation, model training and datasets are not authorized by this planning request. Local implementation authority is specified in each prompt when the user submits it.

## PR Status

These are proposed review boundaries, not existing GitHub PRs.

| PR | Scope | Status | Depends On | Validation Gate |
|---|---|---|---|---|
| PR-01 | Repair stale ability-authority fixtures | Accepted locally for fixture scope | Existing Windows evidence | Focused failures red before repair, green after; guards preserved |
| PR-02 | Reliable UTF-8 Node/Python transport | Accepted locally for transport scope | Reviewed baseline | Real production ingress and Unicode identity/publication proof |
| PR-03 | Perspective-state and replay-knowledge closure audit | Accepted as source-backed gap inventory | Reliable validation | Field/source/visibility matrix and implementable prioritized findings |
| PR-04 | Field-ID semantic validation proof (audit V01) | Accepted defect proof | Reviewed PR-03 | Valid controls plus resealed false field maps through actual validators |
| PR-04B | Proven field-truth and ordinary field-schema repair | Released as Prompt 5 | Reviewed PR-04 | Resealed false maps reject; valid source controls remain passing |
| PR-05 | Candidate provenance reconciliation (audit M01) | Pending PR-04B review | Reviewed current candidate | Complete source/test list and omission/mutation detection; separate scoped review |
| PR-06+ | Knowledge contract and bounded state repairs | Proposed; not authorized | Reviewed PR-03/04 findings | Lead-reviewed contract, then one required state family per candidate |
| Final gate | Independent fidelity acceptance | Not ready | Accepted repairs | Claim-matched production-path evidence, no unresolved required omissions |

## Goal

Trust each supported episode's per-result fidelity claim, and ensure each perspective receives all required legitimate state information throughout the battle before feature design or training relies on it. A complete evidence chain and a full structured knowledge model are separate obligations; both must be assessed explicitly.

## Final Acceptance Contract

- FAC-01: Supported `gen9randombattle` simulator captures cover both original owned requests through matching terminal evidence, every committed boundary, actor-only rows, validated continuation joins and successful cleanup. False remains mandatory for unsupported/incomplete/failed results.
- FAC-02: Every required state/knowledge field has pinned-source provenance, availability semantics, visibility, lifecycle and independent expected-value checks. Unknown, known absent, stale, inapplicable and hidden are not conflated. No required semantic state silently disappears.
- FAC-03: A simulator perspective knows its legitimate initial owned roster/loadout from its initial owned evidence. Opponent knowledge is limited to its public prefix; hidden engine values, private opponent requests and belief hypotheses never become observation facts. Owning a team does not reveal hidden random counters.
- FAC-04: Public replay reconstruction may use the entire replay to establish later-revealed facts about that perspective's own *starting* team at turn 1. Unknowns remain unknown. Opponent discoveries and dynamic battle changes retain event timing. Attribution must distinguish original moves/items/abilities from acquired, copied, consumed or transformed ones. Ambiguous starting facts remain unknown. Preserve Illusion appearance versus roster identity.
- FAC-05: Retrospective replay owner knowledge has explicit source/provenance and information policy. It is not relabeled as causal live/simulator evidence or automatically eligible for the existing sim-core-only faithful flag. Contract/version changes require lead review.
- FAC-06: Real capture/projection/serialization/Python validation/publication paths pass with both perspectives and adversarial resealed payloads. Matching hashes alone never establish semantic truth. Earlier simulator snapshots remain invariant to future events; replay-only owner backfill is an explicit narrow exception, not permission to backfill dynamic/opponent state.
- FAC-07: No remaining required reachable state omission is hidden behind a passing sampled seed, raw-only classification, or manifest count. Raw-only is acceptable only with an explicit reason and proof that required knowledge can be recovered at the relevant boundary. Unsupported required behavior blocks the broader claim or yields a false result.

Not complete if a required field lacks a semantic disposition, a test passes only by weakening validation, the pipeline bypasses its actual consumer, or a replay is given invented private requests/legal actions. Acceptance here still does not authorize training; FEATURE-001, dataset and training gates follow separately.

## Scope and Constraints

- Initial scope: pinned `pokemon-showdown@0.11.10`, Gen 9 Random Battle singles, both perspectives, supported simulator-record path; replay knowledge policy and its integration seam must be audited.
- No production code changes in this lead chat. Preserve unrelated work, original evidence, historical acceptance and reviewed hashes. Workers never attest their own semantic review.
- No checkpoints, replay fetching, dataset generation, training, feature dimensions, dependency installation, repo cleanup, external publication or aggregate-status edits by workers.
- Local tests may use exclusively owned synthetic/in-memory battles and subprocesses. No public live server or external record writes.
- Contract changes land as a coherent reviewed boundary. No undocumented compatibility or schema rewrites.

## Implementation Shape

Simulator evidence flows from owned request/public protocol into `state_extractor` and observable projection, then integration/episode boundaries, frozen observations/beliefs, and independent Python record/publication validation. Audit every seam, including waiting, requestless, switched and terminal states. Replay reconstruction needs a separately identified knowledge-context seam: full-replay owned-starting facts plus chronological public events, with explicit policy and provenance; do not inject it into simulator-owned requests.

## Codebase Touchpoints

| Area | Planned Work | Proof |
|---|---|---|
| `trainer/tests/test_pipeline_record.py` | PR-01 fixture construction | Valid controls publish; malformed/contradictory controls reject |
| Node/Python subprocess and JSON CLI boundaries | PR-02 discover exact ingress and encoding repair | Actual UTF-8 transport and matching content identities |
| `state_extractor.ts`, `observable_state.ts`, public consequence helpers | PR-03 inventory; later bounded repairs if needed | Source-backed independent perspective oracle |
| `pipeline_integration.ts`, `pipeline_episode.ts`, `pipeline_episode_evidence.ts` | Preserve and verify faithful eligibility/continuity | True/false cases and boundary chain integrity |
| `trainer/src/neural/pipeline_record.py`, replay reconstruction modules | Independent verification; discover replay seam | Ordinary/full/compact publication and regime separation |

## PR / Review Strategy

Submit only PR-01 initially. Worker returns a local candidate, commands/exit codes, risks and exact changed files. Lead reviews those artifacts and chooses the next boundary; findings can change this plan. PR-02 follows PR-01 review, then PR-03 determines the actual state repair PRs. Do not execute provisional downstream implementation or rewrite accepted coverage attestations. Use `implement-plan` for assigned local work, `architect-pr-review` or project `wm-pr-review` for review, and `review-plan-tests` for integration coverage. No automatic publication.

## Parallel Execution Notes

External worker owns implementation; lead owns contracts and acceptance. Independent read-only inventories can run concurrently only when explicitly scoped by the worker prompt. Shared schemas, identity algorithms and coverage assets serialize. First establish a trusted validation baseline; do not repair unrelated semantics concurrently with fixture/transport work.

## PR 1: Ability-authority fixture repair

**PR ID:** PR-01. **Status:** Accepted locally for fixture scope. **Depends On:** Existing smoke evidence. **Parallelism:** One writer.

- [x] P1-T01 Reproduce the two failing methods without broad suites.
- [x] P1-T02 Correct only synthetic owned ability-recipient authority against current contracts; preserve identity resealing and cross-perspective matrices.
- [x] P1-T03 Demonstrate missing-recipient/wrong-owner/contradictory controls reject before publication; 72 resealed cases added because the corresponding Python controls were absent.

Validation: exact failing methods, then record/lineage suites; preserve guards, no test skipping or validator relaxation. A discovered production defect returns to lead rather than expanding scope.

## PR 2: UTF-8 transport

**PR ID:** PR-02. **Status:** Accepted locally for transport scope. **Depends On:** Completed PR-01 local review. **Parallelism:** One writer at subprocess/CLI boundary.

- [x] P2-T01 Locate production and test Node-to-Python ingress; reproduce accented-name corruption under Windows default encoding. Production CLI ingress was already byte-based; defects were inline text consumers and diagnostic output.
- [x] P2-T02 Choose and document explicit UTF-8 wire handling in the real producer/consumer path, preserving overrides and embedding behavior.
- [x] P2-T03 Test names/identities and failure output with the workaround unset, then run the exact v2 episode privacy test.

Validation: red-green real subprocess transport, canonical IDs and publication outcomes; no dependency on the lead shell's `PYTHONUTF8=1`, no timeout inflation, no identity changes.

## PR 3: State and knowledge closure audit

**PR ID:** PR-03. **Status:** Accepted as source-backed gap inventory. **Depends On:** Completed PR-02 local review. **Parallelism:** Independent read-only evidence lanes permitted with separate outputs.

- [x] P3-T01 Reconcile current accepted scope, latest source and manifest; do not inherit stale historical blockers.
- [x] P3-T02 Inventory relevant state families and lifecycle dispositions across both perspectives and boundaries; compare typed state, raw evidence, requests and independent Python validators. This is a family-level source inventory, not exhaustive runtime proof.
- [x] P3-T03 Record owned initial knowledge and retrospective replay attribution policy; locate actual replay entrypoints and missing integration. Contract design remains proposed.
- [x] P3-T04 Separate capture completeness, semantic state sufficiency, privacy and source-specific knowledge. Recommend contract decisions and ordered repair tasks; recommendations are not implementation authorization.

Validation: exact source symbols, legitimate owner/public reference values independent of projection helpers, existing-test references, concrete unresolved findings and red test recipes. No new implementation, self-attestation or blanket acceptance.

## Cross-Cutting Validation

- Unit: unknown/absent distinctions, writer precedence, lifecycles and contradictory inputs.
- Wiring: prove actual capture, replay knowledge context and Python publication use reviewed semantics; helper-only tests are insufficient.
- Integration: both sides, own initial bench roster, move-slot mapping, PP/disable/locks, statuses/boosts, public volatiles, sides/field, transformations, Illusion, transfers, waiting/revival/forced switch and terminal restoration.
- Oracle: compare every boundary against independently assembled legitimate player evidence and pinned source witnesses; do not reuse the implementation helper to generate expected truth.
- End-to-end: seeded original-to-terminal win/tie, one-sided paths and bound continuations; intermediate boundaries checked, not only final hashes. Reuse historical long-fixture evidence only with matching source/provenance; rerun when changed behavior requires it.
- Replay: full-replay own initial knowledge versus exact-prefix opponent/dynamic state, never-revealed and ambiguous fields, acquired moves/abilities/items, unchanged timing and no fabricated requests. The authorized backfill exception is explicitly tested.
- Adversarial: resealed false maps, missing facts, wrong owner, mixed source policy, forged true flags, broken predecessor chain, failed cleanup; Python rejection exits 2 with zero publication output.
- Environment: Windows UTF-8 default behavior and pinned dependency evidence; existing environment success is not clean-install proof.

## Open Questions

- Which required state facts remain omitted or raw-only without enough semantic reconstruction? PR-03 must answer before repair scope and final claim are settled.
- Are owned starting facts uniquely recoverable from a public replay under transformations/item transfers/Illusion? Backfill only attributed starting facts; preserve unknowns otherwise.
- Does the existing flag express the full desired semantic assurance, or is a versioned stronger contract/source-specific claim necessary? No silent extension to replay or universal mechanics.
- Clean Windows environment reproduction is pending. It remains a separate environment gate, not proof of missing battle semantics.

## Lead Progress and Next Action

2026-10-09: verified latest scoped faithful-flag acceptance and reviewed Windows results. Incorporated the user's replay hindsight exception. Applied draft-implementation-plan and review-plan-tests: added real wiring, independent truth, per-boundary and replay-policy tests so a capture-only test cannot stand in for state fidelity. No implementation or independent acceptance performed.

2026-10-09, Prompt 1 return: lead reviewed the exact test-only diff and production ability-authority rules. No blocking finding within fixture-repair scope. Lead independently repeated the two target methods: exit 0, 2 passed, 43 deselected, 576 subtests passed in 4.79s; whitespace check passed. Worker reports record/lineage suites exit 0, 56 tests and 4,860 passing subtests; the full suites were not repeated by this lead. Production validation and generic fixture helpers are unchanged. Acceptance is local fixture correctness only, not broader state fidelity or publication authorization. See `perspective-fidelity-prompt1-lead-review.md`.

2026-10-09, Prompt 2 return: lead reviewed shared wire I/O, production CLI calls, two inline consumers and real subprocess tests. No blocking transport finding. Fresh lead checks with encoding overrides unset: 3/3 transport tests, 4 embedded/Unicode tests and 2 subtests; Prompt 1 file hash unchanged. Worker exact v2 episode pass reused, not rerun by lead. The provenance checker fails closed on expected changed source digest; the new wire helper and transport test are not in the current explicit local coverage list. This remains an open source-provenance reconciliation item for the next audit, not a self-attestation or blanket runtime acceptance. See `perspective-fidelity-prompt2-lead-review.md`.

2026-10-09, Prompt 3 return: accepted the source-backed K01–K20/R01–R05 gap inventory, with limits recorded in `perspective-fidelity-prompt3-lead-review.md`. Lead verified missing PP normalization against pinned locked/recharge requests, legacy species-keyed full-replay aggregation, synthetic request defaults and incorrect hindsight provenance, plus actual observable validator wiring. Weather/terrain/pseudo-weather bypass remains unproven. Proposed new schemas, separate completeness claims and broad write sets remain design proposals, not accepted decisions.

Sequencing decision: release audit V01 as Prompt 4 before M01/C01 implementation. Resolve the highest-risk semantic-validator uncertainty while contracts stay unchanged; then reconcile the complete source/test provenance packet including probe files as appropriate, then review source-specific knowledge contract choices. Existing reviewed hashes remain unchanged. The source audit's legacy replay findings do not revoke accepted simulator-capture behavior.

2026-10-09, Prompt 4 return: accepted runtime proof of false weather/terrain/Trick Room admission. Worker reports 24 resealed attacks accepted in TS and Python ordinary/full/envelope, with 12 complete-terminal compact attacks publishing. Lead independently verified identities and reproduced three ordinary publications: rain versus sun-only prefix, Grassy versus Electric Terrain, Trick Room without a start. Lead did not rerun the 200-invocation matrix. Ordinary Python field-schema divergence is recorded at the same validator boundary. See `perspective-fidelity-prompt4-lead-review.md`.

Historical handoff: `perspective-fidelity-prompt5.md` (PR-04B) authorized ordered field-truth validation and ordinary field-schema alignment, including imported TS validation in `belief_state.ts`.

2026-10-09, Prompt 5 return: accepted locally for bounded field-truth admission; integrated regression gate remains open. Worker reports all 24 false-state attacks, 12 terminal compact attacks and six schema attacks reject, with valid controls and focused/build checks passing. Fresh lead Python suite: 7 tests/30 subtests passed, exit 0; whitespace check passed. Lead reviewed the remaining 130 failure entries as incomplete synthetic field/history contexts and the scalar identity inline reader's locale dependence. See `perspective-fidelity-prompt5-lead-review.md`. No blanket green, broader fidelity or provenance acceptance.

Historical handoff: `perspective-fidelity-prompt6.md` (PR-04C) authorized test-only cleanup of five synthetic publication methods and one inline byte reader.

2026-10-09, Prompt 6 return: accepted locally; affected regression gate restored. Lead inspected scoped fixture construction and retained positive/negative assertions, verified all protected hashes and independently repeated 6 tests/464 subtests plus the scalar identity verifier (all exit 0). Worker broad evidence: 63 tests/4,944 subtests and identity/belief 15/15, with transport, field suite, Prompt 1 and build checks green. See `perspective-fidelity-prompt6-lead-review.md`. Production and original Prompt 4/5 evidence remain unchanged.

Historical handoff: `perspective-fidelity-prompt7.md` (M01) authorized required-source registration, omission/mutation controls and an unreviewed candidate provenance packet.

2026-10-09, Prompt 7 return: independently accepted scoped maintenance. Fresh lead harness 2/2; all 258 protected hashes and owned candidate hashes match. Independent recomputation matches `8879baab101f4981ee3412f89faf5a8d13996975f5844503083f30ed90ee242b` over 137 inputs. Live checker before attestation rejects only the expected review mismatch. Lead separately records scoped digest acceptance for accumulated reviewed repairs/provenance controls, preserves the prior `dced76...` digest and every pre-existing review/history field, and checks the live gate afterward. See `perspective-fidelity-prompt7-lead-review.md` and lead validation log. No universal semantic or training claim.

Historical handoff: `perspective-fidelity-prompt8.md` (C01) authorized a source-specific knowledge contract proposal and examples.

2026-10-10, Prompt 8 return: accept architectural proposal and semantic examples, with exact contracts still unfrozen. Three lead read-only subagents found no conceptual blocker; owner/source, replay/privacy and integration reviews identify precise PK-01 clarifications. Fresh lead checks confirm 237 untouched protected hashes and seven artifact hashes; this lead updates the other two protected planning files. Unique mirrored examples and fact evidence references check; whitespace passes. D01-D07 decisions and discovery/stat/crosswalk/trust clarifications are recorded in `perspective-fidelity-prompt8-lead-review.md`. Evidence-relative profiles do not close the user's stronger goal. The approved pre-effect addressed owner delivery is a provider design direction, not current legitimate captured evidence.

Historical handoff: `perspective-fidelity-prompt9.md` (PK-01) authorized exact knowledge contracts and serialized fixtures, without runtime adoption.

2026-10-10, Prompt 9 return: fresh lead document checker passes 15 positives/31 negatives/16 vectors, parity and suffix invariance; preservation checker confirms 900 protected files unchanged and four permitted cross-references changed. Three read-only lead reviewers found six exact-contract/checker gaps: escape spelling, replay source forks versus same-source discovery, layer/power representability, timer effect binding, typed privacy/reference traversal and per-property subject obligations. Return PK-01 for revision; no runtime acceptance. See `perspective-fidelity-prompt9-lead-review.md`. Original-source provider direction and architecture remain accepted.

Historical handoff: `perspective-fidelity-prompt10.md` (PK-01R) authorized those bounded corrections and independent fixture/review checks.

2026-10-10, Prompt 10 return: accept corrected PK-01R contract as the structural implementation basis. Fresh lead checker passes 26 positives/43 negatives/16 vectors plus representation/coverage/revision/suffix subsets; direct hashes confirm 927 protected and 88 candidate core files. Three read-only reviewers confirm the six corrections with no bounded blocker. Selected structural coverage canaries do not establish source semantics or complete assurance. See `perspective-fidelity-prompt10-lead-review.md`; historical evidence and attestation unchanged.

Sequencing: split PK-02 into a first reviewable structural core (PK-02A) and later trusted-source/legacy/publication wiring (PK-02B). Next user submits `perspective-fidelity-prompt11.md` for paired strict ingress, exact identities/schema/typed closure and a non-publishing CLI check. It must explicitly report semantic/completeness limits and cannot mint consumer projections or receipts. Contract data becomes an explicit runtime dependency, requiring later provenance maintenance. Review before source semantics or publication. Broader fidelity and training remain pending.
