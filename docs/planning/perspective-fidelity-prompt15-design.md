# Prompt 15 (S01c design checkpoint): request-knowledge publication, retention and restoration

Status: design for lead review, 2026-10-10. New files under `docs/planning` only; no production, contract or existing-test edit; nothing staged or committed. HEAD `accab655` plus the lead's local working tree. All claims below are backed by a real run whose script and log are in `perspective-fidelity-prompt15-*` (index in section 9). Unverified items are marked **UNVERIFIED**.

## 0. Summary

1. The addressed request text is byte-exact at exactly one place, `PlayerStateExtractor.handleRequest(rawJson)` (`state_extractor.ts:362`), reached from `ManagedPlayer.start` (`env_manager.ts:403`). It is parsed and then discarded: `StepResult.requests[owner].raw` is the parsed object, not text. Retention needs a small private ledger in `ManagedPlayer`/`LocalBattleEnv` read by `PipelineIntegrationSession`; `StepResult`, `PipelineBoundary`, snapshots and bundles must not change.
2. In a real pipeline run (3 seeds x v1/v2, 362 boundaries, 724 owner rows, 1,436 deliveries) the live environment's last delivery was a fresh delivery for every non-terminal owner row, `JSON.stringify(JSON.parse(text)) === text` for all 1,436, and the S01b TS and Python builders/validators accepted all 724 rows with byte-identical TS/Python records (average about 4,048 bytes, max 4,333).
3. The restored-branch stale request is a Showdown serialization property, not a bug in `toJSON` of this repo: `state.js` omits `activeRequest` (stores only an `activeRequest:null` marker) and `fromJSON` regenerates it with `getRequests(requestState)`. An in-place mutation made by a *rejected choice* (`side.js` `updateRequestForPokemon`: drop `maybeTrapped` and add `trapped:true`, or set a move `disabled:true` plus `disabledSource`) is therefore lost on restore. It cannot occur in a committed pipeline snapshot (a rejection throws `pipeline/v1/rejected-action` and discards the candidate); it does occur for any long-lived `LocalBattleEnv`/RPC snapshot taken after a rejection.
4. Smallest fix: a conditional sibling restoration key, emitted only when the live request differs from the regenerated one. Prototype (test-owned monkeypatch) restores the live request exactly, recaptured fingerprint is stable, play continues. Every non-mutated snapshot is byte-identical (5 of 4,054 observed serializations differed). Only the mutated state gets a new fingerprint (`8e9bf1e0...` to `841143e6...`).
5. Recommended publication: **separate joined artifact** `request-knowledge-publication/v1` (Option C). Every existing validator provably rejects an added key, a nested `raw_request` and an unknown bundle version, so the only identity-preserving path is a new artifact that never nests inside existing ones. `faithful_complete_episode` stays a function of existing fields only.
6. K-fact adapter: pure function from `request-knowledge/v1` to a Prompt 12 `request` row. Derived flags are `unknown/not_emitted`. Move/roster subjects need an original-roster index and move incarnation that only S02 provides; the adapter takes an injected resolver and emits nothing without it.

## 1. Where the raw request exists and what must be retained

Path (all line numbers in the working tree):

| Stage | Location | Raw text available? |
|---|---|---|
| Showdown `sideupdate` -> `getPlayerStreams` | `LocalBattleEnv.initializeStreams` (`env_manager.ts:782`) | exact JSON line `|request|{...}` |
| per-owner chunk loop | `ManagedPlayer.start` (`env_manager.ts:403-417`): `line = rawLine.trim()` used only to detect `|request|` and call `handleRequest()` | yes, but not passed on |
| tracker | `consumeChunk` strips only a trailing `\r`; `handleRequest(rawJson)` (`state_extractor.ts:362-367`) gets `line.slice('|request|'.length)`, `JSON.parse`s it, stores `ownRequestData = rawRequest` and `currentRequest = normalizeRequest(...)` | **only here is the exact text visible** |
| `ChoiceRequestView.raw` (`types.ts:84`, set by `normalizeRequest`) | parsed object; `cloneChoiceRequest` copies it by reference | text lost; aliasing hazard |
| `StepResult.requests[owner]` (`buildStepResult`, `env_manager.ts:1111`) | clone of the above; `include_wait_requests:true` in the pipeline so wait requests are reported | parsed only |
| pipeline observation | `normalizeRequest` fields only; protocol prefix keeps `|request|{"rqid":..}` sanitized to rqid (`observable_state.ts:1594`) | no |

**Byte-exactness.** `JSON.stringify(raw)` equals the delivered text on all 1,436 deliveries in `perspective-fidelity-prompt15-probe-sidecar-run.cjs` (`roundtrip_mismatch:0`) and on all prompt13 live comparisons. That holds only because the engine serializes with `JSON.stringify`; text cannot be *proved* equal from the parsed object, and the Prompt 12 seam's `addRequestDelivery` demands the exact text. So retain text, not a re-serialization.

**Freshness per boundary** (`perspective-fidelity-prompt15-retention.json`, probe-retention): in the v2-only run (181 boundaries), for all 358 owner rows with a reported request, `reported_equals_last_delivery` held for all and the last delivery was never a restore re-emit; each committed transition produced one restore re-emit (candidate restore) plus at least one fresh delivery per owner. Boundary kinds seen: `joint_actionable` 153, `one_sided_forced_switch` 26 (the waiting owner has a fresh `{"wait":true}` delivery), `terminal` 2 (4 owner rows). **UNVERIFIED in a real pipeline run**: `one_sided_revival`, non-terminal `requestless`, `one_sided_requestless` (covered only by the prompt13 test-owned witness).

**Terminal.** `reported_request:false` for both owners, but the candidate tracker's last delivery is the *restored re-emit of the previous boundary's request* (4/4 terminal rows). It is not a delivery at the terminal boundary and must not be published as one.

**What to retain, for how long.** Per owner a ledger entry `{sequence (per-owner counter on the env), text, provenance in {fresh_delivery, restore_reemit}}`:
- Tap: `ManagedPlayer.start` request branch (or `handleRequest` taking the line), with a per-player `restoredPending` counter incremented in `resetFromSerialized` for each `side.emitRequest(side.activeRequest)` (same mechanism class as the existing `markRestoredRequestConsumed`) so re-emits are labelled by production, not asserted by a caller. Delivery order per owner is FIFO through the stream, so the counter is deterministic.
- Read: new pull method `LocalBattleEnv.getRequestDelivery(player)` returning a frozen copy. **Not** a `StepResult` field (server JSON, Python decoders and exact-key validators would change).
- Capture point: `PipelineIntegrationSession.buildInitialBoundary` and `executeTransition` right after `stepSeededTransition`/`...ForcedSwitch` and before the candidate is retired (`pipeline_integration.ts:611-619`), bound by `JSON.parse(text)` deep-equal to `request.raw` (defence against a ledger/request mismatch). Stored in a session-owned `Map<observation_id, {p1,p2}>` with an accessor; `PipelineBoundary` type and bytes unchanged.
- Lifetime: until the session closes (publication of any bundle/episode needs its input *and* successor boundaries); rejected candidates are dropped with the candidate. Cost about 4 KB per owner row (130-boundary game: about 1 MB); no cap proposed beyond the existing episode limits (lead decision D8).
- Rejected-then-redelivered requests (section 2) are fresh deliveries but with a mutated grammar (`disabledSource` key; `perspective-fidelity-prompt15-disabled-grammar.log`: S01b Python/TS grammar rejects it, `raw-grammar`). The pipeline never publishes them. Keep refusing (fail closed); extend the grammar only if a non-pipeline publisher appears.

## 2. Restored/snapshot-branch stale request: diagnosis and smallest fix

**Cause chain** (pinned `pokemon-showdown@0.11.10`):
1. `side.js:329-333` `emitRequest` stores the request object as `side.activeRequest`.
2. A rejected choice mutates that object in place and re-emits it: trapped switch (`side.js:668-684`: delete `maybeTrapped`, set `trapped=true`), unavailable move (`side.js:493-512`: set `disabled=true`, `disabledSource`).
3. `state.js:63` puts `activeRequest` in the skipped SIDE keys; `serializeSide` (`state.js:170-181`) writes only `activeRequest:null` when null. The pokemon keeps `trapped:'hidden'`, `maybeTrapped:true`.
4. `Battle.fromJSON` (`state.js:132-142`) rebuilds `battle.getRequests(requestState)` from pokemon state: the pristine pre-rejection request.
5. `LocalBattleEnv.resetFromSerialized` (`env_manager.ts:727-733`) re-emits `side.activeRequest`, so the restored session offers the request the engine already rejected, including the rejected switch/move as legal.

**Reproduction** (`probe-restore.cjs`, `probe-live.cjs`, `probe-disabled.cjs`, characterization tests 1, 2, 4): harness snapshot after a rejected switch: restored text equals the *previous* delivery (`restored_equals_live_prev:true`, last false). Live `LocalBattleEnv` (external control) with `step({p1:'switch 2'})`: live `trapped:true`; snapshot -> second env: `maybeTrapped:true`, `restored_equals_live:false`, recaptured fingerprint equal (restore is stable but wrong), play continues. Disabled variant (Imprison): live `Tackle disabled:true, disabledSource:""`; restored `disabled:false`.

**Reach.** Never in a committed pipeline snapshot: serialized-state detector (`active-request-patch.cjs` detect mode, preloaded via `NODE_OPTIONS=--require` over env_manager, transition, pipeline_integration, forced_switch, revival, belief_fork and most of pipeline_episode): 4,054 `serializeBattle` calls, 5 with a live request different from the regenerated one. Two attributed with stacks: the `pipeline_integration` rejection test and the natural Arena Trap episode test, both inside `stepSeededTransition` of a candidate that `executeTransition` then discards. **UNVERIFIED**: the other 3 events (not individually attributed; a stack-enabled re-run of those tests did not reproduce them). Reachable externally through `captureSeededSnapshotEnv`/seeded RPC after a rejection.

**Smallest fix (R1, recommended if lead wants it fixed).** In `serializeBattle`, for a live (non-ended) battle compare each `side.activeRequest` with the regenerated request (`Battle.fromJSON(clone)`); only for differing sides add a sibling key (prototype name `__active_request_overrides`; precedent `TERMINAL_REQUEST_HISTORY_KEY`, stripped before `Battle.fromJSON` in `resetFromSerialized`), and apply it after `Battle.fromJSON` and before the re-emit loop. Prototype results (characterization test 3): restored equals live (both flavours), recaptured fingerprint equal, step continues, non-mutated snapshots byte-identical. Required hardening, because the key sets `side.activeRequest`, which Showdown's choose paths read (`side.js:540,596`): accept only the three engine edits (`maybeTrapped` -> `trapped:true`; per-move `disabled:true`+`disabledSource` string) relative to the regenerated request, else typed validation error like `TerminalRequestHistoryValidationError`. Python never sees `simulator_state` (it is a `_FORBIDDEN_KEY`), so no Python change.

**Identity effect.** Existing seeded-restoration identities and all accepted episode evidence: unchanged (no committed boundary carries a mutated request; 4,049/4,054 serializations unaffected). Changed: the fingerprint/branch id of a *mutated-state* snapshot only (never published). **Legal authority changes by design** for that restored branch: the switch/move the engine rejected stops being legal. Flag for lead.

**Rejected alternatives.** R2 always embed `activeRequest` (changes every non-terminal fingerprint). R3 re-derive by parsing `choice.error` text (fragile, authority-bearing). R4 do nothing in `env_manager.ts`: acceptable for S01c because the sidecar already refuses non-fresh provenance and pipeline sessions cannot hit it; the defect then stays for RPC users. Even with R1, restored re-emits stay `restore_reemit` and unattested: nothing proves the regenerated or overridden text equals the original delivery for snapshots written before the fix.

## 3. Terminal, waiting and requestless retention

| Boundary (per owner) | Legacy today | Sidecar should record | Not fabricated |
|---|---|---|---|
| terminal | `request:null` | `presence:terminal`, `request_present:false`, `raw_request:null`, `active:null` (S01b already so) | the previous request is not attached to the terminal record |
| waiting | `request.wait:true`, roster only | fresh `{"wait":true,"side":...}` text, `presence:waiting`, `active:null` | bench PP/moves-as-rows (engine never emits) |
| forced switch / revival | `force_switch`, `active:null` | fresh text, `presence:forced_switch\|revival_selection` | PP |
| requestless (non-terminal) | `request:null` | `raw:null`, `presence:requestless` | no inferred last request |

Last-request retention without S03: the publication manifest (section 4) may carry, for terminal and requestless rows, `last_request_ref` = id of that owner's most recent non-null sidecar at an earlier boundary. It is checkable (must equal the preceding boundary's record) and lives outside the `rkn` record. Per-row `deliveries_since_previous` from ledger sequence numbers distinguishes "no delivery occurred" from "delivery not retained". The existing terminal request history (`TERMINAL_REQUEST_HISTORY_KEY`) is canonicalised roster-only restoration data, "never a live request"; it must never feed a sidecar.

Restored boundaries (continuation segments, `restore_reemit`): rows carry `coverage:"unattested_restored"` and no record; this is stated, never filled.

## 4. Publication options

Measured facts (`probe-publication.log`, both observation versions): adding `request_knowledge` to a valid bundle -> Python `not exact; unexpected=['request_knowledge']`; any nested `raw_request` -> `contains private or raw simulator data` (`_FORBIDDEN_KEYS`, `pipeline_record.py:102`, recursive scans at about 124-126, 265-267, 924-925; TS `FORBIDDEN_KEYS` `pipeline_episode_evidence.ts:114`, checked at 152); unknown `schema_version` -> `unsupported pipeline bundle schema`. TS: bundle key equality `pipeline_integration.ts:702`, episode result field list `pipeline_episode.ts:72`. DATA record identity does not depend on bundle extras, but acceptance does.

| Option | Files/keys | Compatibility | Blast radius | faithful_complete_episode |
|---|---|---|---|---|
| A. New versions | `pipeline-linked-record/v2`, `pipeline-forced-switch-record/v2`, `pipeline-revival-record/v2` (+ transition refs), `pipeline-episode-evidence/v3`, `pipeline-episode/v2`, `pipeline-episode-publication-sweep/v2`; TS `pipeline_integration.ts` constants 27-34/types 89-118/validator 688-745/construction 592-602, `pipeline_episode.ts` 72-80, `pipeline_episode_evidence.ts` 114-116 + builders; Python `pipeline_record.py` 39-110, 497-700, 951-1095, 1096-1350; contracts PIPELINE_EPISODE/DATASET_LINEAGE | old validators reject new versions | very large (cf. rejected observation v3); must also carve `raw_request` out of three forbidden scanners | must be re-proved; risk of silent change |
| B. Optional parallel field on v1/v2 | same keys without version | proven rejected by every existing validator (above) | equals A without a version bump: **silent contract change** | rejected |
| **C. Separate joined artifact** | new `request-knowledge-publication/v1`; no existing key touched | existing artifacts and validators byte-identical | new files only | unchanged by construction |

**Recommendation C.** Artifact: `{schema_version, publication_id, battle_id, source_ref, ruleset, binding:{kind:"episode"|"bundle_set", run_id|bundle_digests, observation_schema_version}, rows:[{step_index, observation_id, owner, coverage, delivery_sequence, deliveries_since_previous, last_request_ref|null, record|null}], request_capture:"complete"|"partial"}`. Coverage in {`fresh_attested`, `terminal_null`, `requestless_null`, `unattested_restored`}. Validators (new): TS `sim-core/src/request_knowledge_publication.ts`, Python `trainer/src/neural/request_knowledge_publication.py`; each row runs `validate_request_knowledge(record, observation)` against the observation taken from the already-validated bundle/episode (join by `observation_id`; every committed boundary x owner must have exactly one row). The artifact is never nested in an existing envelope. `request_capture` is the artifact's own flag; it must not read or write `faithful_complete_episode` (conformance test: result flag equal with and without the artifact). Later embedding as a v3 is possible by copying the artifact verbatim.

## 5. K-fact adapter (Prompt 12 seam)

Plug-in: ledger entries feed `SourceRegistryBuilder.addRequestDelivery(owner, sequence, cursor, text)` (exact text; `cursor` = observation `event_cursor`, the lead-confirmed seam assumption **UNVERIFIED on real sessions**; S01c test asserts equality). The adapter `requestKnowledgeToRequestRow(rkn, resolver)` emits the Prompt 12 seam row `{owner, sequence, cursor, actionable, facts[]}` (the full schema `request` object additionally needs `kind,id,origin,source,prefix` hashes and fact ids; the audit builder supplies those, adapter output is the pre-hash row); `actionable` is true for `actionable|forced_switch|revival_selection` (fixtures: wait -> `false`, `facts:[]`).

| rkn field | Fact (family.property, subject) | Value |
|---|---|---|
| move `pp`, `max_pp` | K07, `pX:roster:R:move:M:incarnation:N` | known integer when non-null (real 0 stays 0); null -> `unknown/not_emitted` |
| move `disabled` | K08, same move subject | known boolean when non-null; null -> unknown |
| `maybe_disabled` | K08, broadcast to every move row of the active inventory | known `true` only when derivation `raw_true`; `omitted_singles_rule` false -> **unknown** |
| `trapped`, `maybe_trapped` | K08, `pX:roster:R` (active member only; bench gets none) | `raw_true` known `true`; any derived false or null -> **unknown** |
| `lock` | K08, `pX:roster:R` | lead decision D4: unknown in S01c (derivation from a bare row is rule-derived, no rule-evidence form exists); fallback known text only for ids `recharge`, `struggle` |
| `presence` | K20 `boundary_kind`, `pX:side` (text) | known; `request_present` -> K20 `request_presence` boolean |

Dependency: `R` (original roster index) and `N` (incarnation) are not in the request; request `side.pokemon` order is the current party order. They require the S02 original-identity/starting-moves rows; the adapter takes an injected resolver and **emits no move/roster fact without it** (never positional guessing).

## 6. Recommended split

| Slice | Write set | Red tests first | Notes |
|---|---|---|---|
| S01c-1 (optional, lead D2) restoration key | `sim-core/src/env_manager.ts`; new `sim-core/tests/active_request_restore.test.ts` | rejected-switch and rejected-disabled restore equals live; non-mutated snapshot fingerprints byte-equal (corpus of 5 sessions); malformed key rejected; legal set after restore excludes rejected action | production, snapshot-bytes + legal authority; independent of the others |
| S01c-2 delivery ledger | `env_manager.ts` (ManagedPlayer/LocalBattleEnv private ledger + `getRequestDelivery`), `pipeline_integration.ts` (session map + accessor only); new `sim-core/tests/request_delivery_ledger.test.ts` | text equals harness text for all prompt13/14 cases both owners; restore re-emit labelled `restore_reemit`; `StepResult`, `PipelineBoundary`, bundles and `observation-pins.json` unchanged; settling/`restoredRequestConsumed` behaviour unchanged | production, no identity change by design |
| S01c-3 publication artifact | new TS/Py `request_knowledge_publication`, tests, `docs/contracts/REQUEST_KNOWLEDGE_PUBLICATION.md` | full-episode coverage, tamper negatives (owner swap, stale text, missing/duplicate row, wrong run_id, cursor, unattested row with record), faithful flag equal with/without | after S01c-2 |
| S01c-4 K-fact adapter | new TS/Py adapter + tests (no registry/seam edit) | table rows above; derived flags unknown; no fact without resolver; registry cursor equals observation cursor | full rows blocked on S02 |

Rejected: Option A/B now; extending `StepResult`; embedding text in observations or snapshots; making `normalizeRequest` emit nulls (legal authority); inferring omitted PP from history (S03).

## 7. Spots where production identity or legal authority could change

1. `env_manager.ts` `ManagedPlayer.start/handleRequest/handleError`, `resetFromSerialized`, `serializeBattle`: settling acknowledge order, `restoredRequestConsumed`, snapshot bytes (S01c-1 only for mutated states).
2. `side.activeRequest` set by the restoration key gates legality in engine choose paths (S01c-1): authority-bearing input; validate.
3. `StepResult`/`PipelineBoundary`/bundle shape (RPC JSON, Python exact keys): no new fields.
4. `raw_request` in `_FORBIDDEN_KEYS` x3: sidecar must stay outside those artifacts.
5. `faithful_complete_episode` (`pipeline_episode.ts:76-80`, `pipeline_record.py:846`): publication must not read or write it.
6. Sidecar builders never feed `buildLegalActionSet`; adapter facts are claims, not legality.

## 8. Decisions needed from the lead

D1 Option C (recommended) vs A. D2 fix restoration now (R1) or defer (R4). D3 vocabulary for unattested restored rows. D4 `lock` as unknown vs known for bare rows. D5 ship adapter with injected resolver now, or wait for S02. D6 keep refusing `disabledSource` rows. D7 pull method on `LocalBattleEnv` (recommended) vs `StepResult`. D8 ledger lifetime/cap. D9 confirm `cursor` = `event_cursor`.

## 8b. Review disposition (fresh-context read-only reviewer; I did not self-review)

Confirmed: source chain, line cites (minor off-by-one cites fixed), key-exactness and forbidden-key rejections, K07/K08/K20 mapping and types. Accepted additions:
- Bench: `property-contexts.json` requires trapped/maybe_trapped/lock for request context on `roster, all_relevant`; "bench gets none" leaves that obligation uncovered. Ruling needed (D10): adapter emits bench `unknown/not_emitted`, or K08 stays incomplete by design. Same for K20 on wait rows (fixture shows `facts:[]`, table implies K20 facts): D10.
- Option C negative test must pin that any old scanner run over a container holding the artifact rejects it (desired).
- R1 cost and false positives: it rebuilds a `Battle` per live snapshot and assumes no other legitimate live-vs-regenerated difference (for example `noCancel`); untested outside singles. A pre-fix snapshot restored post-fix is not detectable as mutated, and branch ids change for RPC holders of mutated-state snapshots.
- The `restoredPending` counter must replicate the `markRestoredRequestConsumed` conditions (ended, or side already choice-done) for waiting sides.

## 9. Evidence index (all `docs/planning/perspective-fidelity-prompt15-*`)

`probe-restore.cjs`, `probe-live.cjs`, `probe-disabled.cjs`, `probe-retention.cjs` (+`retention.json`), `probe-sidecar-run.cjs`, `probe-sidecar-validate.py` (+`sidecar-validate.log`), `probe-publication.py` (+`.log`), `probe-disabled-grammar.py` (+`disabled-grammar.log`, `mutated-disabled-request.json`), `active-request-patch.cjs` (test-owned monkeypatch), `detect*.jsonl`/`detect-run.log`, `characterization.test.cjs` (+`.log`), `progress.md`, `hashes.json`, `validation.json`, `report.md`, `check-baseline.py`.

Limits: single-origin witness (registry and records come from one session); 3 seeds only; revival/requestless real-pipeline coverage absent; detector run did not complete the long `CE-08A`/turn-limit tests.
