# Perspective knowledge contract proposal and implementation plan

**Status:** Draft for lead review; no contract, schema or runtime adoption.
**Last updated:** 2026-10-10. C01 / Prompt 8. All new names below are proposals.

## Source Materials

- Prompt 8 and initiative FAC-02-FAC-07 establish the settled owner/replay policy.
- Prompt 3 K01-K20/R01-R05 and C01 supply the required-family inventory and migration risks.
- Prompt 7 independent lead review closes bounded provenance maintenance, not knowledge completeness.
- Existing OBSERVABLE_STATE, BELIEF_STATE, PIPELINE_EPISODE and DATASET_LINEAGE contracts constrain historical keys/identities.
- Verified source references below distinguish current implementation from proposed behavior.

## Status

Prompt 1/2/5/6 repairs and Prompt 7 maintenance are locally accepted within their scopes. This proposal adopts nothing. The user authorized bounded read-only delegation, overriding the prompt prohibition: two Sol 6.1 source investigators and an independent draft/test reviewer; parent owns integration and all writes. Existing v1/v2 observations, beliefs, DATA records and faithful capture claims retain their meanings.

## PR Status

| Proposed PR | Scope | Status | Dependency | Gate |
|---|---|---|---|---|
| PK-01 | Contract and independent fixtures | Proposed | D01-D07 lead decisions | Exact-key/version, privacy and example review |
| PK-02 | Identity-bound transport/validation shell | Proposed | PK-01 | Real ordinary/full/compact publication |
| PK-03 | Legitimate starting witness and roster identity | Proposed | PK-02 | Pre-effect attribution and owner isolation |
| PK-04 | Request facts, PP omission and retention | Proposed | PK-03 | Wait/force/revival/terminal/restoration |
| PK-05 | One chronological family per PR | Proposed series | PK-04 and family review | Independent source/event oracles |
| PK-06 | Replay identity and starting attribution | Proposed | PK-01/02/03 and selected PK-05 families | Bounded public-log canaries |
| PK-07 | Assurance and explicit consumer routing | Proposed | Accepted required families and PK-06 | Both-owner end-to-end proof |

## Goal

Make legitimate structured knowledge available at each boundary, separating immutable original owner facts, chronological current/public knowledge and current action authority. Raw capture is insufficient until justified facts reach the consumer at the relevant boundary.

## Final Acceptance Contract

- KA-01: Original facts have unique owner attribution and immutable proofs. A required missing owner fact blocks stronger assurance even when honestly marked unknown.
- KA-02: Current/public knowledge is prefix-causal, with knownness, precision and freshness preserved at bench, wait, requestless, revival, terminal and restoration boundaries.
- KA-03: Full replay backfills only owner-starting facts. Earlier opponent knowledge, current dynamics, public appearance assignments, requests and actions stay invariant.
- KA-04: Actual capture/parser -> context -> serialization -> belief/history binding -> Python validation/publication -> named consumer path proves the claim. Fully resealed false facts/provenance reject before output.
- KA-05: Legacy identities and faithful_complete_episode remain exact. Knowledge assurance is regime/profile-specific and never implies training eligibility.

Not complete if a required fact is merely raw/reconstructable, stale values are treated as current, original attribution is ambiguous, production helpers manufacture test truth, or unknown markers evade required-source obligations.

## Scope and Constraints

Future adoption is explicit opt-in, all-at-once within each reviewed version; old payloads keep exact keys. No silent fallback to legacy reconstructed private state. Initial scope remains pinned Showdown 0.11.10/gen9randombattle. Attribution stress cases involving unreviewed mechanics do not assert operative reachability. No arbitrary engine-set reads, future opponent facts, inferred EV/IV/nature/happiness or hidden random counters. No adoption, source/test/contract/manifest/attestation/status edits in this task.

## Implementation Shape

### Version choice and bindings

| Option | Consequence | Recommendation |
|---|---|---|
| observable-battle-state/v3 embeds all knowledge | Changes observation/history/publication identities; replay hindsight can affect otherwise causal observation bytes | Reserve for a separately justified observation migration |
| Separate perspective-knowledge/v1 and knowledge-publication/v1 wrapper | Existing observation/record/belief bytes stay exact; strict cross-object joins and explicit consumer routing required | Recommend this shape, subject to lead approval |

The proposed wrapper has a strict ordinary/full/compact discriminant, regime/policy, original supported payload, context dictionary, binding rows and assurance report. It inserts no keys into old payloads. A context contains `owner_starting`, `chronological_current` and `request_reference`.

- `starting_context_id` binds source/regime/policy, owner, original witness, roster keys and original fact/proof records.
- `current_state_id` binds prefix-eligible chronological state, public cursor/hash and eligible addressed evidence only. Full replay digest must not alter this causal subdocument.
- `knowledge_id` binds starting/current IDs, battle/perspective, observation_id, schema/policy, snapshot phase, parent_knowledge_id and request_reference.
- Replay wrapper additionally binds the full-source digest/parser version. A changed suffix can change full-source/starting/wrapper IDs but never earlier chronological bytes or observation IDs. Canonical JSON/Unicode semantics remain unchanged; proposed new ID domain prefixes need review.

Two source identities are mandatory. Causal `prefix_source_id` hashes the immutable battle/source anchor established at origin, parser/rules versions and the exact eligible prefix records; addressed request proofs additionally bind owner, request sequence, delivery boundary/cursor and raw addressed payload digest. Causal evidence IDs hash only that prefix-scoped proof payload. Full-source attribution IDs hash the complete replay raw/canonical digests, parser/policy, owner and original-attribution certificates; they occur only in owner_starting and privileged wrapper provenance. A chronological evidence record must not carry a full-replay digest under a generic source_digest field. Trusted validation checks that the causal prefix exactly belongs to the full source, without introducing that full digest into the causal subdocument. EX14 compares serialized causal proof records and IDs, not just fact values, across changed suffixes in all three publication forms.

Binding rows join input/successor observation and belief IDs, transition/action IDs when present, commit ordinal and knowledge IDs. A wrapper history table binds every old belief observation reference to its knowledge reference without changing BeliefState keys. Retrospective original evidence cannot become causal `direct_observed` belief evidence; hypotheses stay hypotheses. A future directly context-aware belief schema requires another approved version. Nonactor boundaries carry context, while DATA publication remains actor-only.

Ordinary includes input/successor contexts and sufficient origin/parent proof. Full includes origin and every committed both-owner boundary. Compact uses immutable-ID dictionaries and the same complete join/proof table, not an optional unauthenticated sidecar. Missing context/proof, source relabeling and broken parent joins reject. Python independently verifies IDs, joins, source eligibility, fact truth and lifecycle before output. Output is a new publication wrapper around unchanged DATA rows and knowledge references; dataset-record/v1 is not reinterpreted.

### Trusted proof envelope versus perspective consumer projection

The full both-owner proof envelope is input to a trusted validation/audit boundary only. It is never the feature/agent consumer input. After validation, publish a separately identity-bound projection for exactly one perspective: that owner's permitted starting/current facts, public facts available at its cursor, its current request reference and allowed history references. Its reachable dictionary contains only those records. Opposite private contexts, raw request payloads and private proof dictionaries are absent, not merely hidden behind a perspective label. Full raw replay and future chronological events are also absent; the projection contains only the permitted owner-starting backfill and opaque provenance/source commitments needed to identify the validated policy. Proof URLs, dictionary IDs and restoration handles must not grant a consumer traversal or fetch capability to excluded data.

Validate facts from the complete source in the trusted boundary before producing this projection; an opaque digest or producer receipt alone cannot establish semantic truth. Offline audit artifacts remain privileged and distinctly typed. The consumer_projection_id binds perspective, allowed projection content, boundary/policy and validated source/context commitments; it does not expose raw excluded proof content. A receipt records which validator/version checked which source/projection, but authentication/receipt transport requires explicit lead approval before any cross-process trust is assumed. No model receives a both-owner compact dictionary or full replay just to resolve evidence_refs.

Required privacy canary: place distinct p1/p2 secret strings in legitimate owner proofs and an unrelated future public event. After TS serialization, Python validation/publication and restoration, recursively inspect each consumer-visible payload and all resolvable references. p1 cannot retrieve p2 secrets or unrelated future replay dynamics, and vice versa; trusted audit storage can retain them. Resealed attempts to substitute an audit envelope for a consumer projection or add cross-owner/future reference capabilities reject. Starting-only hindsight does not authorize a full replay feature input.

### Fact algebra

Each fact carries subject identity, family/key, value, knownness, freshness, semantic valid_from/valid_until, observed_at, evidence_refs and attribution. Evidence records identify source kind, owner/visibility, request sequence or exact public-record ordinal, source digest/parser, prefix eligibility and writer-rule version. Owner-private proofs are stored only in that owner's scoped proof store; opposite-owner contexts cannot contain them. Unknown onset is null, not the observation turn. Replay original facts alone can have observed_at later than their availability at origin.

| Knownness | Meaning |
|---|---|
| known | Evidence supports an exact value or explicitly typed bucket/range; precision is part of the value |
| known_absent | Affirmative absence/cure/empty-item evidence, with applicability; missing key is never absence |
| unknown | Never observed, ambiguous attribution, unsupported derivation or omission; reason required, no guessed value |
| inapplicable | Proven outside this subject/state; never a substitute for an unimplemented required family |

Freshness is independent: starting facts are immutable; dynamic facts are current only with evidence or a proved persistence rule. Otherwise retain last_known value with last corroboration and invalidation reason. Keep fact history, not silent erasure. Conflicts become unresolved attribution and block exact obligations; no last-writer-wins rule. Fact IDs bind proofs/timing; deterministic ordering and duplicate rejection are required. Belief hypotheses never become known facts.

### Identity and persistence

Owner roster ID anchors to an approved original owner witness and original index, separate from mutable party slot. If starting order is unavailable, do not invent it. Replay identity starts with owner, appearance stint and exact source record ordinal; species/nickname is insufficient. Unique reveal witnesses may establish a starting crosswalk. Current public Illusion/replace links apply only chronologically. Future owner-only attribution links may be stored in owner_starting but must not rewrite earlier current/public appearance assignments, even for that owner's dynamic facts. Transform/acquisition creates current move-slot incarnations, not original roster/move entries.

Once a permitted source is fixed, its owner_starting object is immutable. Causal contexts can append discovery revisions without changing previous snapshots; missing pre-effect evidence stays blocked. Full replay attribution is computed once per full-source identity. New suffix/source means a new starting context, not mutation in place. Switching updates active/party mapping and only reviewed reset effects; faint/revival changes health and specified effects without erasing learned loadout/identity. Request disappearance removes action authority, not knowledge. Restoration needs original/current fact history and parent bindings alongside the simulator snapshot; latest request cache alone is insufficient.

### Required family contract

Every row uses the common owner/time/prefix/identity/provenance rules above. This table defines future obligations, not present support.

| Family | Legitimate evidence and knownness | Persistence/replacement and assurance |
|---|---|---|
| K01 roster/slots | Original addressed roster; public appearance/reveal/teamsize; unknown opponent members remain unknown | Stable roster persists; party/active mapping chronological; ambiguity blocks identity-dependent facts |
| K02/K07 moves/slots | Original-attributed move membership versus current addressed slots/public execution tags | Starting immutable; current incarnation changes on Transform/acquisition/reset. Recharge/Struggle/called execution do not prove starting membership or slot order |
| K03/K04 stats/loadout/Tera | Original witness for item/base ability/Tera/five base stats; details/level/gender/shiny/ball | First post-start current request is not universally original. Missing original proof blocks required original obligations; exact HP max requires addressed condition |
| K05 health/faint/status | Exact addressed own condition; public bucket/ratio/status/cure/faint writers | Public bucket may invalidate retained exact HP; cure is known_absent, missing condition unknown; no future damage backfill |
| K06 status history | Public acquisition/cure/reentry and owner condition | Observed-since differs from actual onset; public elapsed counts need rules; hidden duration/remaining timers excluded |
| K07 PP/maxPP | Raw emitted active-owner keys per roster/move incarnation | Emitted0 is known0. Lock/recharge/Struggle/bench omission adds no value; retain stale unless persistence proved. Never default0/1 or deduct solely from chosen action |
| K08 disable/trap/lock | Raw maybeDisabled/maybeTrapped and explicit disabled/trapped; current request legality/public lock proof | Definite and maybe flags separate; absent != false. Waiting/requestless has no action request; no synthetic pass/mask or replay actions |
| K09 boosts | Public updates/copy/clear/Transform direction and eligible addressed evidence | Seven zero/unknown stages, identity and reviewed switch/faint reset; preserve v1 omissions; no hidden target stages |
| K10-K13 effects/side conditions | Public starts/ends/activations and reviewed finite lifecycle rules | IDs/source/observed timing/public count or range; absence requires complete prefix/supported rule. Raw-only is not structured completeness; one effect scope per review |
| K14 field | Public weather/terrain/Trick Room writers and known suppression evidence | Weather ID != effective weather; literal none != unseen null; mixed wire list unchanged. Hidden extender/timer unknown; suppression is not an end |
| K15 slot/pending | Attempted setup versus successful public setup/outcome | Intent/expectation distinct from established pending fact; recipient/power/timer unknown absent public proof; no slotState pointers |
| K16 form/type/Tera/Transform | Public form/type/Tera; owner addressed facts and target public attributes at Transform | Starting stats/types separately labeled; opponent revealed Tera retained chronologically; copied effective stats may be unknown despite request baseStoredStats |
| K17 Illusion | Owner undisguised request; exact public replace/reveal/stint proof | Earlier appearance snapshots unchanged; ambiguous carrier cannot establish original loadout |
| K18 item | Name/possession/absence/consumption/effectiveness from eligible owner/public evidence | Starting item never overwritten by transfer/consumption/Recycle; current name/held/effective separate; missing opponent marker != empty |
| K19 ability | Original proof versus current/base-at-form and public reveal/copy/change/suppression | Trace/Imposter/form changes are current; current baseAbility is not universal original; hidden Shield limits effectiveness certainty |
| K20 boundaries | Both owners at origin, joint/one-sided post-resolution, wait/force/revival/terminal/restoration | Persist legitimate knowledge; stale request/opponent cache/terminal-only snapshot without origin cannot confer original authority |

Nature/EV/IV/happiness are not emitted by the inspected request contract. They are unknown/unavailable under an addressed-evidence profile; no stat inversion or hidden-set read. A stronger human-owner-complete profile requiring them is blocked until separately approved legitimate owner delivery exists. Unknown alone does not satisfy that profile. Recommend retaining emitted ball/shiny/gender/level/details. A tactics-only profile may explicitly exclude cosmetic ball/display with reviewed rationale; an all-legitimate-emitted profile cannot silently omit them. Cosmetic exclusions cannot erase identity.

### Replay starting attribution

Propose `public-replay-owner-starting/v1`: complete canonical public source, full raw digest, canonicalization/parser/rules version, owner and per-fact attribution certificate. Current prefix is separately bound by exact record count, not turn cutoff; full history is never input to current reconstruction.

Identify each candidate carrier uniquely; classify the producing event and all preceding relevant changes; prove original possession rather than acquired/copied/called/transformed/form-derived state. Certificate records witness indices, exclusion/continuity checks and unknown intervals. Late ordinary reveal or proven original-item consumption may establish original facts only with a supported unmodified chain. Missing change tags in an incompletely classified source are not proof. Transfer establishes current possession, not recipient starting item; consumption establishes absence only at its event. Unsupported writer, duplicate identity or unresolved Illusion remains unknown/ambiguous. Never-revealed facts stay unknown. Backfill for owner only; the other perspective learns at chronological reveal.

Original proof goes in owner_starting with actual observed_at and origin availability. Dynamic HP/status/boosts/effects/current PP and transformed/copied current moves never backfill. Future owner identity crosswalks do not relabel prior causal appearances. Replay has request_reference=null and no PP/disabled/trapped defaults or legal mask; an admitted addressed source would require a separately reviewed hybrid regime.

### Knowledge assurance

Separate assurance report binds profile/version, regime/policy, required-family manifest, source/context/boundary IDs and per-family verdict: supported-complete, legitimate-source-unknown, blocked-missing-required-evidence, blocked-attribution, unsupported. Validators recompute verdicts, not trust producer claims. Quantify at every required boundary and both owners. Unknown is legitimate for hidden opponent facts, replay never-revealed facts and documented unavailable sources within an approved evidence-relative profile. Unknown blocks a required owner's original fact or an unimplemented structured required consequence.

Recommend `addressed-owner-evidence/v1` and `public-replay-owner-starting-evidence/v1`: require complete extraction of eligible evidence plus explicit unknown dispositions, not omniscience. A separate requested owner-loadout-complete profile remains blocked by unavailable metadata and absent pre-effect original witnesses. Consumers explicitly choose profiles. Existing faithful_complete_episode is untouched; replay never inherits it or automatic DATA/training eligibility.

| Proposed profile | Required obligations | Permitted unknown/inapplicable | Blocking conditions |
|---|---|---|---|
| addressed-owner-evidence/v1 | K01-K20 within the exact reviewed finite-family manifest; original roster/moves/item/ability/Tera/base stats/details from approved original source; all eligible current/public facts; PP/maybe flags when emitted | Hidden opponent values, never-emitted bench PP, omitted active PP with retained freshness, hidden timers, documented source-unavailable nature/EV/IV/happiness; inapplicable only with a proved state/rule | Missing required original witness, lost emitted owner fact, missing required structured family, unsupported relevant writer, unproved identity/parent join |
| public-replay-owner-starting-evidence/v1 | Exact indexed public history; every supported eligible public/current consequence; all uniquely attributable owner-original facts found in complete source; explicit attribution verdict for each candidate | Never-revealed original facts, documented genuinely ambiguous carriers, unavailable PP/private action flags and hidden timers; no private request | Incomplete source scan, unsupported relevant attribution writer, discarded eligible reveal, fabricated original/current fact, future-current/opponent proof, unresolved required exact-identity obligation |
| owner-loadout-complete (version to approve) | Exact original owner roster/loadout plus required nature/EV/IV/happiness and all required boundary knowledge | Only facts explicitly excluded by that stronger profile's reviewed manifest | Any required unavailable/ambiguous owner fact; evidence-relative profile cannot satisfy this request |

Each profile is an immutable, independently reviewed required-family manifest with source/rule versions and permitted reasons. Consumer policy selects the required profile; producer profile selection cannot weaken it. Aggregate completeness is true only if every required boundary/owner/family has supported-complete or an explicitly permitted legitimate-source-unknown/proved-inapplicable verdict, with no blockers or omitted obligations. A selected-family example is never aggregate full-profile evidence. Unknown reasons are checked against source capability and rule, not accepted as free text. Unsupported relevant writers cannot be hidden as legitimate unknown; a proved cosmetic exclusion cannot become an excuse to omit identity. Missing-required-family, dishonest inapplicable and weaker-profile substitution are semantic negatives after resealing.

## Verified Source Facts and Integration Points

Paths relative to repository root; PS = sim-core/node_modules/pokemon-showdown. These are inspections, not new simulator execution evidence.

| Source | Verified fact / proposed seam |
|---|---|
| PS/sim/side.ts:319-328; pokemon.ts:1099-1135 | Addressed current roster emits baseStoredStats/moves/item/base/current ability/details/ball/Tera; no bench PP/nature/EV/IV/happiness |
| PS/sim/battle.ts:1885-1887,2636,1715 | Start/switch effects precede ordinary first request; first-current is not universal original proof |
| PS/sim/pokemon.ts:929-949,999-1006,1058-1080,1247-1269,1351,1430 | PP omission/maybe flags; Transform slots/storedStats; form can change baseStoredStats/baseAbility |
| sim-core/src/action_codec.ts:5-37,185-212; observable_state.ts:310-321 | Omitted defaults/ball/maybe flags/raw loss; preserve raw owner facts before normalization while old keys stay unchanged |
| sim-core/src/state_extractor.ts:149-169,232-240,362-476 | Public ingestion/latest raw request/terminal history; context alongside getView/getRequest |
| sim-core/src/env_manager.ts:683-692,698-778,1111-1140 | Packed teams are omniscient control inputs, not owner evidence; reviewed owner delivery before effects if approved; context serialize/restore beside settled both-side boundaries |
| sim-core/src/pipeline_integration.ts; observable_state.ts; belief_state.ts | Proposed capture/project/serialize and explicit binding at session boundary/record construction and history validation |
| sim-core/src/pipeline_episode_evidence.ts:242-283,446-599 | Proposed wrapper origin/commit/nonactor/closure dictionaries, old IDs unchanged |
| trainer/src/neural/pipeline_record.py | Proposed strict wrapper dispatch around existing ordinary/full/compact validators, independent semantics before output; preserve byte reader |
| trainer/src/neural/parse_replay_logs.py:95,148,184,298,332,371,397 | Raw normalized lines/tags retained, structured events lack stable source index; disk parser entrypoints need indexed output |
| build_live_private_value_dataset.py:112-192,418-493,632-691 | Turn cutoffs/full-source species aggregator/invented HP/PP/actions/provenance incompatible with proposal |
| Same file:263-302,307-366; benchmark_vnext_featuregen.py:375,406,430-553 | Future current copied moves and Illusion relabeling plus alternate benchmark reconstruction require migration/exclusion |

Additional source witnesses: PS/data/moves.ts:20670-20679 (Trick new items), 12280-12290 (Mimic current slots), 17200-17202 (Sketch base/current acquisition), 17236-17240 (Skill Swap); PS/data/abilities.ts:5064-5065 (Trace donor), 2021-2029 (Illusion reveal/faint); PS/sim/battle-actions.ts:450-455 (move source tags). Acquisition examples do not assert gen9random reachability before separate source review.

## Codebase Touchpoints and Future Contract Edits

| Proposed future contract write | Exact purpose |
|---|---|
| docs/contracts/PERSPECTIVE_KNOWLEDGE.md (new) | Fact algebra, source availability, original/chronological/request split, certificates/IDs/joins/restore/profile rules |
| docs/contracts/OBSERVABLE_STATE.md | External context relationship, exact v1/v2 unchanged, legacy request defaults not knowledge truth |
| docs/contracts/BELIEF_STATE.md | Wrapper reference table; no hindsight direct_observed; direct new keys require another version |
| docs/contracts/PIPELINE_EPISODE.md | Wrapper origin/commit/nonactor/closure dictionaries; assurance independent of capture Boolean |
| docs/contracts/DATASET_LINEAGE.md | New publication policy/version identity and separately approved eligibility; no v1 reinterpretation |

## PR / Review Strategy

Resolve D01-D07 and review PK-01 before code. Each later candidate needs independent source/oracle review and fresh authorization. PK-05 is one family per PR, split further by lifecycle where needed. PK-06 uses checked-in public-log canaries without dataset execution. Provenance/attestation follow in a separate reviewer-owned maintenance boundary. No commits/publication authorized here.

## Parallel Execution Notes

Critical path: contract -> wrapper -> original proof/identity -> request retention. Replay inspection and family oracle drafting can run read-only concurrently after binding decisions; shared identity/serialization adoption is serialized, one writer per file. Draft names confer no authority.

## PK-01: Contract and independent examples

Status proposed; dependencies D01-D07; no runtime parallel writes. Write set: future contract edits above, reviewed example fixture directory to be chosen by lead.
- [ ] Freeze K01-K20 source/knownness/profile/cosmetic obligations and exact version keys.
- [ ] Hand-audit mirrored examples against source and privacy at all boundary classes.
Validation: independent attribution and contract/test review; missing original witness explicitly blocks stronger claim.

## PK-02: Wrapper and publication wiring

Status proposed; depends PK-01. Proposed new sim-core/src/perspective_knowledge.ts, trainer/src/neural/perspective_knowledge.py, paired tests; narrow pipeline_integration/episode_evidence/belief binding seams and pipeline_record wrapper dispatch.
- [ ] Exact kinds/IDs/context dictionaries/history joins; partial context cannot claim completeness.
- [ ] Real TS serialization -> Python CLI ordinary/full/compact -> publication, retaining legacy IDs.
Validation: independent identity payloads, Unicode with overrides absent; fully resealed wrong owner/source/parent/cursor/missing proof/unsupported profile rejects exit2/empty stdout before any row. Demonstration consumer verifies the context, not sidecar presence alone.

Concrete proposed tests: sim-core/tests/perspective_knowledge.test.ts and trainer/tests/test_perspective_knowledge.py, with bounded extensions to existing pipeline_integration.test.ts/pipeline_episode.test.ts and test_pipeline_record.py for actual wiring. Proposed non-training inspector: sim-core/scripts/inspect-perspective-knowledge.cjs, consuming only the validated single-perspective projection and displaying facts/provenance/assurance without access to the audit store. These are future new files, not existing APIs. PK-02 accepts transport/join/privacy only; no unimplemented family can receive semantic completeness before its own PK-03/04/05 gate.

## PK-03: Starting evidence and roster

Status proposed; depends PK-02. Proposed writes env_manager/state_extractor/new knowledge modules and paired tiny source tests. Pre-effect owner delivery/API needs separate legitimacy review; packed control input is insufficient.
- [ ] Establish original evidence authority and distinct roster/party/appearance identities.
- [ ] Persist original moves/item/ability/Tera/stats/details with missing-source blockers.
Validation: addressed source or approved owner delivery oracle, not projector; first-entry mutation, duplicate species/nickname, Illusion, bench and restored terminal. Resealed erased original facts/foreign private proofs/false original attribution reject semantically.

## PK-04: Request facts and retention

Status proposed; depends PK-03. Proposed raw request capture in action_codec/state_extractor/env_manager, knowledge/serialization modules and tests; old v1/v2 defaults unchanged absent separate approval.
- [ ] Emitted/omitted PP/maxPP, definite/maybe flags, slot incarnations and action authority.
- [ ] Wait/force/revival/requestless terminal/restore without erasure or current-state invention.
Validation: pinned raw request keys and public chronology for emitted0/omitted/never-known, recharge/Struggle/lock/Transform PP/bench return; real settled sessions and all wrapper forms. Resealed PP/disabled/trap/action fabrication rejects.

Restoration control: serialize a preterminal boundary, restore and continue a short owned session; compare both perspectives' fact/proof IDs, freshness, requests and published bindings with uninterrupted execution. Reseal internally coherent wrong-battle/wrong-owner history grafts, parent forks, mismatched request authority and terminal restored-request resurrection; reject semantically in ordinary/full/compact, including after compact dictionary expansion. A terminal-only context cannot certify missing origin coverage.

## PK-05: Chronological families, one PR each

Status proposed series; depends PK-04 plus each family review. Write set per family: new paired lifecycle module/tests, necessary extractor/knowledge/validator wiring only. Order: health/status precision; item/ability original-current/effectiveness; moves/form/type/Tera; field/source timing; finite effects/side/slot intent. Do not bundle all effects.
- [ ] Independent event ledger, named writers/reset rules and consumer availability before admitting each family.
Validation per PR: both owners/input-successor and origin/midbattle/wait/requestless/force/revival/terminal/restore or proved inapplicability; valid source controls and fully resealed false/missing/invalid lifecycle through TS/Python ordinary/full/compact.

## PK-06: Replay starting attribution

Status proposed; depends approved bindings/identity/required chronological families. Proposed writes parse_replay_logs.py, new replay_starting_knowledge.py/test_replay_starting_knowledge.py and explicit wrapper producer. Legacy builders/rankers/benchmarks remain excluded pending separate authorized migration.
- [ ] Indexed raw tags, unique carriers and original/acquired/copied/called/transformed/ambiguous certificates.
- [ ] Full-source original scan separate from strict-prefix current state; fail legacy provenance relabeling.
Validation: tiny checked-in public-log canaries with independent labels, same-turn cutoffs, late reveal/never-revealed/transfer/consumption/Transform/Illusion; mirrored owner backfill, opponent/current/request suffix invariance; real wrapper CLI with request null. Resealed source/policy/certificate/backdated dynamics reject. Later caller migrations must cover build_live_private_value_dataset.py:642, build_action_rank_dataset.py:163, build_action_value_dataset.py:72, benchmark_vnext_featuregen.py:548 and its alternate helpers, analyze_tactical_failures.py:57, compare_action_rankers.py:174, compare_replay_evals.py:203; passing full history everywhere is not a repair.

## PK-07: Assurance and explicit routing

Status proposed; depends accepted required families/PK-06. Proposed writes knowledge/integration/publication validators and named non-training demonstration consumer/tests; profile/eligibility docs only after review.
- [ ] Recompute obligations for both owners/every boundary from complete source/context dictionaries.
- [ ] Missing required evidence/unimplemented family blocks stronger true claim; preserve honest partial verdicts.
Validation: actual small origin-to-terminal simulator witness and public replay canary through caller/serialization/belief binding/all publication forms/consumer. Resealed replay capture-flag promotion, hidden-source certainty, lost original proof and policy/digest mismatch reject; prior snapshots stay immutable.

## Cross-Cutting Validation

Every implementation PR needs local semantics, real caller wiring, serialization/history joins and bounded end-to-end publication. Gold expected values are hand-audited from raw legitimate evidence, never new helpers/ports. Reseal observation/context/belief/transition/envelope IDs and verify joins before negative semantics. Explicit Python selection and encoding overrides absent. No full corpus/Node suite/1,000-turn witness/generated dataset as first gate. These are planned checks, not executions performed by Prompt 8.

## Open Decisions

| ID | Recommendation for lead | Consequence |
|---|---|---|
| D01 | Separate strict context/publication wrapper, preserve old v1/v2 | Explicit joins; no hidden identity migration |
| D02 | Legitimate pre-effect owner delivery or per-fact original proof | Original-loadout assurance blocked absent approved witness |
| D03 | Evidence-relative simulator/replay profiles; stronger full-owner profile blocked for unavailable required facts | Unknown cannot silently discharge missing required-owner obligations |
| D04 | Retain emitted ball/shiny/details; optional reviewed tactics-only exclusion | Additional retention; all-legitimate claim cannot silently omit them |
| D05 | Unique carrier/continuity certificates; no future current-identity rewrite | More legitimate ambiguity, correct original/current separation |
| D06 | Explicit new routes; legacy reconstruction remains excluded | Existing dataset/replay consumers not claimed compliant |
| D07 | Separate trusted audit envelope from identity-bound single-perspective consumer projection; approve validator receipt trust explicitly | Prevent proof/history traversal from exposing opposite private facts or future replay dynamics |

Resolve these before coding. Missing original-source authority is a material blocker, not a reason to weaken the definition of starting knowledge. Examples are a hand-authored proposal oracle, not accepted runtime fixtures.
