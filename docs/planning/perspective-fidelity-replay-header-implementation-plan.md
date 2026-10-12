# Implementation Plan: Replay Header Import Boundary

**Status:** Ready for bounded implementation; independent scope/test-plan review passed.
**Last Updated:** 2026-10-10.

## Source Materials

- [Initiative plan](perspective-fidelity-implementation-plan.md): strong knowledge goal and outstanding providers.
- [Prompt18 lead review](perspective-fidelity-prompt18-lead-review.md): accepted HTML transport, unchanged semantics failures.
- [Fixture ledger](../../trainer/tests/fixtures/perspective-replay/expected-ledger.json): fixed source indices and independent facts.
- [Prompt17 evidence](perspective-fidelity-prompt17-ts-characterization.json): strict routing versus structured-state gaps.

## Status

Prompt18 supplies correctly decoded records through the existing Python HTML loader. There is no strict production replay-to-extractor boundary. Existing test-only exclusion routing cannot serve as that boundary.

## PR Status

These are local review boundaries; publication is not authorized.

| Boundary | Scope | Status | Depends On | Validation Gate |
|---|---|---|---|---|
| Prompt19 | Replay metadata classification, strict prefix admission and source mapping | Not started | Accepted Prompt18 | Actual loader-to-router-to-extractor checks; viable projection/Python checks; indexed rejection |

## Goal

Admit the evidenced replay headers without loosening ordinary protocol validation. Every requested source prefix either produces a strictly routed state trace with explicit index mapping or rejects at an identified original source record. This does not establish accurate knowledge or complete replay ingestion.

## Scope and Constraints

Authorized writes: new `sim-core/src/replay_import.ts`, new `sim-core/tests/replay_import.test.ts`, and new `docs/planning/perspective-fidelity-prompt19-*` evidence. Build outputs from the documented compiler are permitted and inventoried separately. Existing source/tests, fixture bytes, frozen contracts/schemas, capture flags, identities, coverage manifest/attestation and historical reports remain unchanged. Return to lead if an existing-file change is necessary.

The input is Prompt18's **decoded protocol-record array**, not raw HTML. Original HTML bytes/hashes and transport mapping remain in retained evidence. The adapter must not decode HTML again, trim, repair, rewrite, deduplicate or silently discard battle records. Its trace is internal and untrusted; it cannot register source authority or populate knowledge/publication contracts. OU remains diagnostic.

## Implementation Shape

Add a callable production replay-prefix adapter beside the existing extractor. It accepts decoded records, an original-source cursor, and explicit extractor context. Validate the cursor as a safe integer in `[0, records.length]`; inspect only records before that cursor. Copy/retain each selected source record with its original index.

Lead decisions:

- Before the first `|start` record, exact `|rated|` is retained replay metadata, never rewritten to native `|rated`.
- Before battle start, `|j|☆<display-name>` is retained room-presence metadata. Require exactly one payload, literal star, nonempty name without surrounding whitespace, embedded delimiter or control characters. Names remain text; no player-side, roster or authority inference follows. Other rank prefixes, aliases such as `join`/`J`, extra fields and later joins remain unsupported in this bounded contract.
- Every other record first passes unchanged `validateRawProtocolRecord`. Valid bare framing `|` and valid `tier` records are retained metadata, consistent with the existing observable sanitizer. Preserve native bare/nonempty `rated` behavior through the ordinary validator.
- Private `request` and split transport records explicitly reject; never use a replay to manufacture addressed evidence. Unknown commands and unsupported/malformed mechanics reject, including `raw` rating HTML and the evidenced OU `l`/empty-player suffix. No leave support is added here.
- Admit the entire selected prefix before creating/feeding a fresh `PlayerStateExtractor`. Any admission/extraction failure returns an indexed error, never a usable partial view or success prefix.

The result retains a source-row ledger, source cursor, routed strict prefix, extracted view, source-to-routed mapping (null for metadata), and routed-to-source mapping. Mappings are computed by position, not string search. Source cursor and observation `event_cursor` are different quantities. A viable unchanged observable projection must preserve the routed prefix exactly and use its length as `event_cursor`; verify that correspondence before treating the mapping as a projection mapping. No new observable fields or IDs. Metadata-only boundaries may share the same observation identity while retaining different source cursors. Protect returned trace/mappings against caller mutation and preserve input arrays.

This introduces the callable import seam. It does not migrate ranker, dataset or publication callers; tests exercising the real seam must not be reported as completed caller adoption.

## Codebase Touchpoints

| File | Change | Proof |
|---|---|---|
| New `sim-core/src/replay_import.ts` | Replay-specific adapter using unchanged validators/extractor | Classification, atomic rejection, exact maps |
| New `sim-core/tests/replay_import.test.ts` | Unit and actual-loader integration | Both owners, real bytes and residual blockers |
| Existing Python `_load_replay`, TS projector and Python validators | Read/call only | Genuine cross-module data flow |

## PR / Review Strategy

Return one local candidate after fresh independent review. Previous boundary: accepted Prompt18. Next boundary is chosen by the lead from residual evidence; do not begin mechanics/identity repairs automatically. No commit, publication or merge authority.

## Parallel Execution Notes

One worker owns the new adapter/test files. A bounded read-only agent may independently draft literal oracles or review the candidate. No overlapping writes or descendants without separate authority. Source/identity and shared-contract decisions stay with the lead.

## PR 1: Replay Header Routing — Prompt19

**Status:** Not started. **Depends On:** Prompt18. **Parallelism:** implementation and independent read-only oracle review only.

### Tasks

- [ ] Reproduce current strict header failures using actual `_load_replay` output over UTF-8 byte JSON; block fallback/network/model/scoring/dataset calls.
- [ ] Implement the decided metadata rules and atomic prefix adapter. Write down its small internal input/result/error contract in the report.
- [ ] Add independent literal mapping oracles, duplicate-identical-record and metadata-only controls, invalid cursor/input/control/alias/private-record negatives, repeat/mutation safety and suffix invariance.
- [ ] Exercise both fixture files and both owners through Python loader → byte JSON → production adapter → existing extractor/strict prefix validator. For viable prefixes, call the unchanged projector, then Python identity, `_prefix` and typed-state validators. Any existing projector semantic failure remains an indexed blocked result, not filtered or repaired.

### Validation Criteria

- [ ] Green header/early HP/same-turn boundary checks for both owners. Non-state metadata, including validated framing/tier, never changes extracted state or roster/player knowledge. Native strict validators still reject replay `|rated|`/joins when called directly.
- [ ] Random Battle admission/extraction reaches the real winner prefix at source cursor 368; full 370-record input rejects `raw` at 368. Report projector/typed-state outcomes separately from admission success.
- [ ] OU's earlier supported prefixes work; complete admission rejects unsupported `-prepare` at original index 173. Preserve subsequent `fallen1`, raw, leave, empty-player and terminal owned-item-history blockers as recorded limitations; do not bypass earlier rejection to claim a valid full trace.
- [ ] Prefix results/maps remain unchanged when later metadata/state/winner suffixes change. Boundary tests before/after one same-turn event prove exact source cursor semantics. Cursor zero succeeds with an empty routed prefix; out-of-range/fractional/bool cursors and non-string selected records reject explicitly.
- [ ] Fresh TS build/new tests, retained Prompt18 loader controls, unchanged characterization 5/5 and parser controls. Existing full requirement mode remains red (two Python/one TS); new bounded header requirements pass. Encoding overrides unset; old reports not regenerated.
- [ ] Candidate-relative diff, exact commands/results, before/after witnesses, independent review disposition and complete protected-file/hash inventory. Preserve all previous evidence. No installations/node_modules changes.

## Cross-Cutting Validation

No helper-derived expected ledgers, exclusion-based state success, weaker validators or fabricated requests. Tests permit only process/I/O wrappers; actual loader, router, extractor, projector and validators run. A failure must identify the original source index and stage. Passing this boundary cannot change `faithful_complete_episode`, knowledge completeness, source authenticity or training eligibility.
