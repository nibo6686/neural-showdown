# Prompt 13 (S01a) — request-knowledge: characterization and additive design

Status: candidate for lead review, 2026-10-10. Docs plus two characterization test files only; no production, contract or existing-test edit. Evidence: `perspective-fidelity-prompt13-cases.json` (raw addressed text, request views), `-observation-pins.json` (sha256 of every current v1/v2 observation), `-validation.json`, `-hashes.json`. Source: pinned `pokemon-showdown@0.11.10` `dist/sim/pokemon.js` (cited as `pokemon.js:line`), `side.js`, `battle.js`.

## 1. What the current path loses (proved with real requests)

Raw text comes from a test-owned BattleStream harness (before normalization); the same text equals the live `LocalBattleEnv` request byte-for-byte (`JSON.stringify(raw)===text`, 20 cases, both owners), `normalizeRequest(raw)` reproduces the pipeline observation request exactly, v1 and v2 request views are identical, and Python's `validate_pipeline_bundle` / `_validate_episode_observation` accept all of them.

| Raw addressed request (source) | Observation today (v1 = v2) | Lost |
|---|---|---|
| Locked move (Solar Beam turn 2) `{"moves":[{"move":"Solar Beam","id":"solarbeam"}],"trapped":true}` (`getMoves` 615-632) | one move `pp:0, maxpp:0, target:"normal", disabled:false`; `active.trapped:true, can_switch:false, can_terastallize:false`; only legal action `default` (move row dropped because pp<=0) | PP/maxpp/target/disabled were never emitted; observation shows fabricated numbers. Lock identity absent; `trapped:true` is a lock side effect, the same field a real trap sets. Earlier PP (16) not recoverable from the observation. |
| Recharge `{"moves":[{"move":"Recharge","id":"recharge"}],"trapped":true}` | same sentinels; `type/category` null | same |
| Struggle `{"moves":[{"move":"Struggle","id":"struggle","target":"randomNormal","disabled":false}]}` (`getMoveRequestData` 733-735) | `pp:0,maxpp:0,target:"randomNormal",disabled:false`; legal `move 1` only via the `id==='struggle'` exception | PP absent shown as 0 |
| Real PP 0 `{"move":"Destiny Bond",...,"pp":0,"maxpp":8,"target":"self","disabled":true}` | `pp:0,maxpp:8,disabled:true` | nothing lost for this row, but `pp:0` is now the same value as "PP absent"; only an unmarked `maxpp==0` convention separates them |
| Omitted `target` vs emitted `"normal"` (Tackle) | both `"normal"` | indistinguishable; `normalizeRequest` is non-injective (explicit `pp:0,maxpp:0,target:normal,disabled:false` row == omitted row; non-finite `pp` also becomes 0) |
| `maybeDisabled:true` after foe Imprison; shared moves `disabled:false` (hidden disable is masked, `getMoves` 677, `moves.js` Imprison) | no maybe field; all moves `disabled:false`, all listed legal | uncertainty dropped. The engine **rejects** the listed-legal shared move (`pipeline/v1/rejected-action`, both owners) |
| `maybeTrapped:true` (Shadow Tag, `getMoveRequestData` 740-749), no `trapped` | `trapped:false, can_switch:true`, switch action legal | uncertainty dropped. After a rejected switch the request is re-emitted `trapped:true` without `maybeTrapped` (`side.js` 670-682); the restored (snapshot) branch re-emits the stale pre-rejection request |
| Known trap (Mean Look) `trapped:true` | `trapped:true, can_switch:false` | preserved, but reason (trap vs lock) not representable |
| Choice lock, Encore (soft locks) | other moves `disabled:true`, PP present | preserved booleans; no reason/lock identity |
| Waiting `{"wait":true,"side":..}`, forced switch, revival (`reviving:true`) | `active:null`; roster `moves` are id strings; no PP anywhere | bench PP never emitted by the engine (`getSwitchRequestData` 776-800); cannot be invented |
| Terminal | `request:null` on both owners, although each had real requests (e.g. Revival Blessing `pp:1`) | request presence/history not retained (K20) |

Legal authority: `buildLegalActionSet(raw)` equals the observation's `legal_actions` in every case; deleting `pp` from a move removes its action (absent PP never creates legality); maybe flags never change the legal set. Python accepts a resealed observation that fabricates `pp:15,maxpp:16` for an omitted-PP row, flips `disabled`, or erases a known trap (no request-knowledge oracle exists); a resealed wrong-owner `request.player` is rejected by an existing control.

## 2. Proposal: `request-knowledge/v1` sidecar (no observation/bundle change)

**Placement.** A standalone record produced from the exact addressed text, joined to an unchanged v1/v2 observation by `observation_id`. Not added to observations: `observation_id = digest(all keys except observation_id/protocol_prefix)` (`ts_identity.py:50`), Python checks exact key sets (`pipeline_record.py:378`, `_EPISODE_OBSERVATION_KEYS`), so any added key changes IDs and fails old validators. It is also the shape the accepted contract already expects (PERSPECTIVE_KNOWLEDGE.md: "independent schemas, not additions to old observations"; `request` rows carry `raw_request.json`, writers `raw-request/v1`, `terminal-requestless/v1`).

**Fields** (exact key set; all required; ASCII keys; no floats; booleans never integers):

- `schema_version: "request-knowledge/v1"`, `battle_id: string`, `perspective: "p1"|"p2"`, `observation_schema_version` (v1|v2), `observation_id: "obs-<64hex>"`, `event_cursor: int` (== observation cursor).
- `presence: "actionable"|"waiting"|"forced_switch"|"revival_selection"|"requestless"|"terminal"` (K20 `boundary_kind`; same labels as `classifyPipelineRequestState`); `request_present: boolean` (K20 `request_presence`).
- `raw_request: string|null` — exact addressed JSON text (<=65536 Unicode scalars), null iff `request_present` is false; `rqid: int|null`.
- `active: null | { lock, trapped, maybe_trapped, maybe_disabled, switch_in_available, moves[] }`:
  - `lock: "none"|"locked_move"|"recharge"|"struggle"` (K08 `lock`): one move row without `pp/maxpp` keys: id `recharge`→recharge, `struggle`→struggle, else locked_move; soft locks stay `none` (reason deliberately not modelled, K08 P2).
  - `switch_in_available: boolean` recomputed from request side (non-active, non-fainted) = the engine gate `canSwitchIn` (`pokemon.js` 731, 743-749).
  - `trapped`, `maybe_trapped: boolean|null`: `true` iff the raw key is `true`; `false` iff absent **and** `switch_in_available` (engine would have emitted, singles `isLastActive`); `null` (= unknown, reason `not_emitted`) iff absent and no switch-in. `trapped` and `maybe_trapped` never both true.
  - `maybe_disabled: boolean`: true iff raw `maybeDisabled===true`, else false (singles only).
  - `moves[]` in raw order: `{slot, id, name, pp, max_pp, target, disabled}` with `pp,max_pp: int|null`, `target: string|null`, `disabled: boolean|null`; **null means the key was absent in the raw row, never a default**. Real zero stays `0`.
- `id: "rkn-<64hex>"`: sha256 of UTF8(`request-knowledge/v1\n` + canonical JSON of the object minus `id`), canonical form identical to PERSPECTIVE_KNOWLEDGE.md (ASCII key order, minimal integers, no normalization).

Not added: bench PP (never emitted), `canTerastallize`, reasons for soft locks, retained last-known PP (S03), hidden Pressure. `active.moves` of a non-actionable state is `null`, never fabricated. Doubles (more than one `active` entry) reject.

**Compatibility with PERSPECTIVE_KNOWLEDGE.md.** The record is exactly the owner-request source plus derivable request-context facts: `pp`/`max_pp` (integer, move subject) known from non-null, unknown `not_emitted` from null; `disabled`, `maybe_disabled` (boolean; per contract per-move subject, broadcast from the active flag — flag for lead: raw granularity is per active), `trapped`, `maybe_trapped`, `lock` (roster subject), `boundary_kind`, `request_presence` (side subject). `raw_request` is `source.raw_request.json`. No contract edit needed; M02 registers the new modules.

**Identity guarantees.** v1/v2 observation bytes, IDs, bundles, belief, transition and DATA identities are not touched (S01b writes no existing file); `observation-pins.json` holds the pre-change sha256 of every observation (20 cases x 2 versions x 2 owners) that S01b tests must reproduce. The sidecar never feeds `buildLegalActionSet`.

**Python independent validation** (`validate_request_knowledge(record, observation, *, delivery_registry=None)`): (1) strict wire (exact keys, bool-not-int, scalar/size limits, duplicate-key-free raw); (2) re-derive every field from `raw_request` with its own grammar and compare — rejects false certainty (non-null `pp` for an omitted key, `trapped:false` when raw is true or maybe, `maybe_*:false` when raw true, `lock:"none"` for a locked row, `disabled:false` for omitted); fail closed on unknown raw keys; (3) join to the already-validated observation: id/schema/battle/perspective/cursor, `request.player` and each move's `pp/maxpp/target/disabled` equal `value ?? legacy default`, presence agrees with `decision_availability`/terminal; (4) legality invariant recomputed from raw: no legal move action for a null-PP row unless lock/struggle, none for `disabled:true` or `pp==0`; (5) wrong-owner: record perspective, `request.player`, raw side id and optionally an independently held addressed-delivery registry (Prompt 12 `SourceRegistry`) must agree — a jointly resealed record+raw is structural-only without the registry and is stated as such; (6) id recomputed; stale cursor/observation rejected.

## 3. S01b proposal

Write set (all new): `sim-core/src/request_knowledge.ts`, `trainer/src/neural/request_knowledge.py`, `sim-core/tests/request_knowledge.test.ts`, `trainer/tests/test_request_knowledge.py`, `docs/planning/perspective-fidelity-prompt14-*` (witness reuse of `prompt13-witness.cjs`, evidence). Optional new `docs/contracts/REQUEST_KNOWLEDGE.md`. No edit of `types.ts`, `action_codec.ts`, `observable_state.ts`, `state_extractor.ts`, `env_manager.ts`, `pipeline_*`, `pipeline_record.py` (this narrows the Prompt 3 S01 write set). `ChoiceRequestView.raw` already carries the parsed request; the builder takes `(owner, rawText, observation)`.

Deferred, separately reviewed (S01c): publishing the sidecar in bundles/episodes needs `pipeline_integration.ts` to retain `StepResult.requests[owner].raw` per boundary plus new bundle/episode versions in `pipeline_record.py`; terminal and restored-branch retention (stale re-emitted request after a rejection, terminal `request:null`) needs `env_manager.ts` restoration keys; both listed before editing.

Red tests S01b must turn green (each flips the matching `CURRENT_BEHAVIOR_LOSSY` assertion into a record assertion while the observation pins stay unchanged):
1. Locked/recharge/Struggle records: `pp/max_pp/target/disabled` null, `lock` set, `trapped:true`; ordinary rows non-null; mirrored owners.
2. Real PP 0 record `pp:0,max_pp:8,disabled:true` differs from the omitted-PP record; explicit `pp:0,maxpp:0,target:normal,disabled:false` raw differs from omitted raw.
3. `maybeDisabled` / `maybeTrapped` present vs absent vs known trapped: three distinct records; absent-without-switch-in gives null.
4. Waiting/forced-switch/revival/terminal: `active:null`, correct `presence`; terminal `raw_request:null`; no fabricated slots/actions; both owners.
5. Rejection rollback pair (maybeTrapped -> trapped) yields two distinct records.
6. Observation pins and legal sets unchanged; maybe flags and unknown PP never alter legal actions; builder is pure.
7. Cross-runtime: TS and Python derive identical records and ids for all 20 cases; Python publication (UTF-8 env unset) round-trips including non-ASCII names.
8. Python negatives: every false-certainty, wrong-owner (perspective, request.player, other owner's raw), resealed record/observation, stale cursor, duplicate JSON key, extra/missing key, bool-as-int, oversize and doubles control above.

## 4. Rejected alternatives

- Extra keys on v1/v2 observations: changes IDs and breaks exact-key validators.
- New `observable-battle-state/v3` now: schema gates in `isObservableSchema`, `OBSERVATION_VERSIONS`, episode evidence (v2-only checks), `pipeline_record.py` 319/1186/1301, `typed_state.py`, `perspective_knowledge_source.py`, plus new bundle/episode versions. Large blast radius and entangled with S02/S03; the sidecar object can later be embedded verbatim in a v3.
- Make `normalizeMove` emit nulls: changes bytes and the `move.pp<=0` legality rule, i.e. legal authority.
- Hash-only sidecar: Python cannot re-derive; weakens false-certainty checks.
- Inferring omitted PP from earlier requests or legality from knowledge: S03 history, and violates "legal actions come from the current addressed request".

## 5. Risks and unverified items

- The harness, witness and snapshot-restored sessions are test-owned (not production capture); no provider authenticates delivery yet (contract PK-03/04 pending).
- `absent => false` for the maybe flags and trapped relies on the pinned source reading (`pokemon.js` 740-749, singles only) — Python must not generalise to doubles.
- Restored branches can re-emit a stale request (observed; cause in `toJSON`/`activeRequest` not diagnosed here).
- Contract subject mismatch: `maybe_disabled` is per-move in `property-contexts.json` but per-active in the engine.
- `rqid` is absent in this stream's requests (observations carry `rqid:null`); the record must not require it.
- Seeds and team text in the witness pin outcomes (Hyper Beam via Compound Eyes, Spite order); an engine change fails loudly but would need witness edits.

## 6. Review disposition (fresh-context read-only reviewer, did not run code)

Verified by reviewer: source line cites, `canSwitchIn` derivation, `default` fallback for locked rows, rejection re-emit, contract property names, no v1/v2 identity or legal-authority risk, independent Python re-derivation feasible. Findings and handling:

1. `absent => false` vs contract ("Omitted PP/disabled/trapped does not mean 0/false"): in the contract's vocabulary this is a **known boolean `false` with a rule proof** (pinned `pokemon.js` 740-749, singles, `isLastActive`), never `known_absent` or a default. The "no contract edit needed" claim is withdrawn for these three flags: S01b must either carry a rule-evidence row or emit tri-state (`true|false|null` already is, with `null` = unknown `not_emitted`); lead decides which. PP/target/disabled stay strictly null-when-omitted.
2. Stale restored-branch request (reviewer: major): rule for S01b, **a sidecar may only be built from a freshly delivered addressed request; `StepResult.requests` of a snapshot-restored session is not a valid input**. Required red test: building from the restored `trapped_after_rejection` p1 request must be refused or flagged, while the harness text yields the `trapped:true` record. Not resolved here; restoration fix is S01c.
3. `presence` is not the pipeline `boundary_kind`: S01b needs an explicit table; `no_legal_actions` and `team_preview` are rejected, not mapped.
4. Uncovered edge cases (unverified, S01b must add witness cases): Struggle with `maybeDisabled` (all moves hidden-disabled), Struggle from all-PP-0, non-two-turn locks (Outrage/Rollout/Uproar), `maybeTrapped`/locked row with empty bench (`null`), `no_legal_actions`, doubles rejection.
5. Contract granularity: `maybe_disabled` (per move) and `trapped`/`maybe_trapped`/`lock` (roster subject) are placed on `active`; S01b must define the roster-identity join and broadcast rule with the lead.
6. Test fragility (accepted, not changed): hard-coded counts (20 cases, 68 bundles), private `_validate_episode_observation`, error-substring assert, `expectedMismatch` breadth, substring checks on JSON, `python3` fallback when `PYTHON` unset, prefix-whitelist static scan. The "normalize(raw)==observation" control reuses the production normalizer, so it proves text/live equality, not normalizer correctness.
