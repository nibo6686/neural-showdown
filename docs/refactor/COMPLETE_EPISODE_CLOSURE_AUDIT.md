# Complete-Episode Closure Audit and Implementation Backlog

**Checkpoint: 2026-10-01 — CE-01 reviewed and accepted; remaining closure work open.** Scope is the existing worktree and
`gen9randombattle` under pinned `pokemon-showdown@0.11.10`, using
`observable-battle-state/v2`. This is planning evidence, not acceptance of
PIPELINE-002. `faithful_complete_episode:false` remains required.

## Progress ledger

- Read project instructions, the requested backlog skills, product specification,
  project status, schema-closure findings, scanner progress, and current coverage
  provenance sections. Located the authoritative coverage manifest at
  `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json`.
- Established that older assessment/status passages predate accepted SLICE-002A
  scanner and SLICE-002B provenance work. The closure inventory will reconcile
  these without rewriting historical evidence or coverage attestations.
- Initial next step (completed below): enumerate manifest unknowns/raw records and runner boundaries; verify
  targeted current source where historical gap status is ambiguous; write the
  dependency-ordered backlog and measurable specification milestone.
- Completed manifest extraction: 169 effect IDs (137 represented, 32 raw-only),
  six unresolved computed calls, 114 supported tokens, six recognized stops,
  and all package-emitter reconciliation entries. Reviewed current runner stop
  paths, actor-only accumulation, and segment-only continuation.
- Current-source verification closes historical schema B-01 and B-08; B-03 is
  covered by accepted scanner enforcement. B-02/B-06 metadata and B-04/B-07
  grammar/routing remain closure work. Accepted ordinary v2 publication and
  the Illusion repair supersede earlier blockers in the same dated checkpoint.
- Confirmed source-shaped `-singlemove` Destiny Bond and Glaive Rush emitters
  and direct Qwilfish/Froslass/Baxcalibur set candidates. A bounded raw-evidence
  slice can remove those stops without inventing typed move lifecycles.

## CE-01 implementation checkpoint — source preflight (2026-10-01)

Preflight completed before implementation. A targeted scan of pinned `data/` and
`sim/` finds four base emission forms and three mod duplicates. `P` below is the
emitter's active Pokémon identifier (`p1a: Name` or `p2a: Name` in this singles
format); the colon-space and nonempty trimmed public name are required. Pipes
in the grammar column denote literal record separators; no optional tags exist.

| Exact grammar / tag order | Pinned emitter file and symbol | Format reachability | Effect on O / B / A / T / E | Required disposition |
|---|---|---|---|---|
| `\|-singlemove\|P\|Destiny Bond` | `data/moves.ts:3619`, `Moves.destinybond.condition.onStart` | Direct: Qwilfish/Froslass set pools contain Destiny Bond. | RAW: retain public evidence and cursor/provenance; no typed volatile, timer, belief inference or action override. Simulator handles faint consequence; normal records/requests handle state and terminal evidence. | D2 after exact grammar + simulator/publication/rollback validation. |
| `\|-singlemove\|P\|Glaive Rush\|[silent]` | `data/moves.ts:6896`, `Moves.glaiverush.condition.onStart` | Direct: Baxcalibur set pools contain Glaive Rush. | RAW: preserve the mandatory final `[silent]`; damage/accuracy effect stays simulator-owned, with no typed field or inferred action restriction. | D2 after the same validation; untagged/tag-reordered forms reject. |
| `\|-singlemove\|P\|Grudge` | `data/moves.ts:8176`, `Moves.grudge.condition.onStart` | Package-only base emitter (`isNonstandard: Past`), absent from direct pool; indirect format reachability unproven. | RAW: public trigger evidence only; any PP consequence comes from the owned request and normal public records, never a fabricated typed timer. | Exact raw form may be retained safely; C02 stays D3/CE-03 for reachability proof. No mechanic/format acceptance implied. |
| `\|-singlemove\|P\|Rage` | `data/moves.ts:15098`, `Moves.rage.condition.onStart` | Package-only base emitter (`isNonstandard: Past`), absent from direct pool; indirect format reachability unproven. | RAW: public trigger evidence only; separately emitted boosts retain their existing typed semantics. | Exact raw form may be retained safely; C02 stays D3/CE-03 for reachability proof. |
| Same untagged Grudge grammar | `data/mods/partnersincrime/moves.ts:23`, `Moves.grudge.condition.onStart`; `data/mods/gen8linked/moves.ts:346`, same symbol | Package-only other-mod emitters, not operative `gen9` scripts. | Duplicate raw form; no additional fields or semantics accepted. | D4 for other-mod behavior; no grammar expansion. |
| Same untagged Destiny Bond grammar | `data/mods/gen8linked/moves.ts:407`, `Moves.destinybond.condition.onStart` | Package-only other-mod emitter. | Duplicate raw form. | D4 for other-mod behavior; no grammar expansion. |

Implementation completed one closed shared `singlemove.forms` literal suffix
table with active-only target validation in both runtimes. Table-driven positive
and negative publication/rollback coverage and direct-emitter simulator fixtures
cover both actors. No discovered form requires new typed or information-state
semantics. Unknown labels, category prefixes, extra/reordered/duplicated tags,
and malformed targets remain unsupported. Focused build, TypeScript and Python
validation pass; the coverage checker self-test passes and its full run reports
unreviewed local digest `1a3a57ceaf5096b6a83b2466c13e01b6206ad04939409adb170ed4428e0affbd`.
Separate focused review accepted CE-01 and attested local digest
`1a3a57ceaf5096b6a83b2466c13e01b6206ad04939409adb170ed4428e0affbd`.
This scoped raw-evidence approval does not accept PIPELINE-002 or the
complete-episode milestone; `faithful_complete_episode:false` stays required.

## CE-01 aggregate Glaive Rush raw-only control correction (2026-10-06, unreviewed)

The remaining aggregate effect-inventory control had synthesized
`|-start|p1a: Mew|glaiverush` and expected a typed `PokemonView.volatile`.
That is not a pinned public emitter. `Moves.glaiverush.self.volatileStatus`
creates the simulator-only volatile, while
`Moves.glaiverush.condition.onStart` emits exactly
`|-singlemove|ACTIVE|Glaive Rush|[silent]`. The aggregate control now retains
that valid record through the public-prefix projection and asserts that it
does not invent a typed volatile. Existing direct source-engine, both-actor,
rollback, privacy, historical-fixture, and TypeScript/Python-publication
evidence remains unchanged.

The coverage checker reports local digest
`457396db95e5b3ff641e8e849007a86b7456ff093ca3f48f730b2bca4540a44c` as
unreviewed. Manifest digest and review-attestation fields remain unchanged;
this is a fixture correction, not a new typed-state or CE-01 acceptance claim.

**CE-01 aggregate Glaive Rush raw-only control verdict (2026-10-06, accepted):**
Review verified the pinned `pokemon-showdown@0.11.10`
`Moves.glaiverush.condition.onStart` emitter produces only the exact public
`-singlemove|ACTIVE|Glaive Rush|[silent]` record; the volatile, accuracy, and
damage behavior remain simulator-only. The repaired aggregate fixture retains
that raw prefix and proves no typed `glaiverush` volatile is created. Focused
source-witness, TypeScript contract/extractor/protocol, both-perspective
restore/rollback/privacy, and Python publication tests passed, as did the
aggregate coverage suite, checker self-test, and post-attestation checker.
Digest `457396db95e5b3ff641e8e849007a86b7456ff093ca3f48f730b2bca4540a44c`
is attested only for this aggregate-fixture repair. No generic mechanic or
damage model, private state, CE-01 lifecycle expansion, PIPELINE-002
acceptance, or complete-episode claim is added; `faithful_complete_episode:false`
remains required.

## Episode-fidelity definition

The finish line is **faithful, privacy-correct capture of complete Gen 9 Random
Battle episodes from the initial request through terminal outcome, using
`observable-battle-state/v2`**. It is an episode evidence and publication
contract, not a complete typed simulator model. The simulator continues to
execute mechanics; the current request supplies legality.

A complete capture must retain, for **both** perspectives, the initial v2
observation/current owned request, every committed successor boundary and its
exact normalized public prefix, request availability and lineage, and the final
matching win/tie evidence. One-sided transitions must retain the waiting side's
observation/belief lineage without inventing an action or DATA-001 decision row.
A segment beginning at a resumed boundary is not a complete episode unless a
validated chain connects it to that episode's original initial request.

Raw-only is sufficient when (a) the record's exact supported grammar and audience
are established; (b) its ordered evidence, cursor and normalized hash are retained;
(c) no typed field falsely asserts current state or absence because of the missing
interpretation; (d) legal choices remain request-bound; (e) the simulator can
progress and restore through it; and (f) both runtimes accept the same publication
boundary. Raw evidence need not implement timers, hidden counters, a posterior,
or model features. A raw-only label alone does not prove these conditions.

A complete capture may use the existing versioned normalization: validated
framing/tier records are filtered, request JSON is removed or sanitized under the
appropriate boundary, and pipeline timestamps become `|t:|0`. These are declared
normalizations, not arbitrary omission. Private split HP, request/error streams,
simulator snapshots, seeds, hidden roster/set data, and later events must not
enter the shared public prefix or the other player's observation.

`status: completed` currently means simulator termination only. The proposed
future `faithful_complete_episode:true` additionally requires the acceptance
matrix below and a separate review. Valid cancellation/resource-limit results
remain incomplete; no finite budget promises all battles terminate. Valid
reachable mechanics cannot remain unsupported merely to make a subset look
complete. Runtime guards against malformed input, drift and unknown future
forms remain mandatory after closure.

## Evidence and reconciliation

All source references below are repository-local. Pinned simulator paths such as
`data/moves.ts` resolve under `sim-core/node_modules/pokemon-showdown/`; manifest
JSON pointers identify evidence rather than imply that a candidate is proven to
occur in a generated team.

| Key | Evidence read / authority |
|---|---|
| SPEC | [Product specification](../requirements/spec.md), product behavior and acceptance requirements. |
| STATUS | [Project status](../PROJECT_STATUS.md), 2026-09-29 aggregate snapshot; narrower later evidence below supersedes stale next-step statements only within its recorded scope. |
| COV | [Simulator coverage](../contracts/SIMULATOR_COVERAGE.md), source/format and scoped lifecycle/progression reviews. |
| MAN | [Coverage manifest](../../sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json), `review`, `protocol`, `condition_inventory`, `effect_discovery`, `condition_semantics`, `format_provenance`. |
| MEC | [Mechanical assessment](MECHANICAL-REPRESENTATION-ASSESSMENT-2026-09-25.md), MEC-01–MEC-14 and unexamined areas. |
| SCH | [Schema closure](SCHEMA_CLOSURE_AUDIT.md), G01–G58, exact raw forms, B-01–B-08. |
| SCAN | [Scanner progress](SCANNER_EXPANSION_PROGRESS.md), accepted 002A expansion and fail-closed value/family enforcement. |
| PIPE | [PIPELINE-002 checkpoint](PIPELINE-002-GAP-DISPOSITION-2026-09-24.md), current 003/Illusion/004A/004B and historical scoped reviews. |
| ENV | [Environment validation](ENVIRONMENT_VALIDATION.md), current 2026-09-30 disposition and macOS profiles. |
| RUN | [Episode runner](../../sim-core/src/pipeline_episode.ts), `executeEpisode`, `classifyError`, `actingPlayers`, `terminal`, `continuePipelineEpisode`. |
| INT | [Integration](../../sim-core/src/pipeline_integration.ts), prefix projection, request/boundary classification, candidate commit and selection guards. |
| PY | [Python publication](../../trainer/src/neural/pipeline_record.py), `_prefix` and record validation. |

The manifest's stored/reviewed local digest is
`199d580722805f29c92077137eb0c88bc0b10138adda7724731d201bfc9cca32`
(ENV-001C1 coverage-source review, 2026-09-30); its simulator digest is
`12d83949635889cd10a51a081890f9dfc6d3ed480eacf2a9a0728fb48e8e086c`.
These are **read evidence**, not recomputed or newly attested values.

Already accepted: expanded nested effect scanning (169 IDs: 137 represented,
32 raw-only), operative format/generator provenance (507 species keys, 869
set rows, 350 move and 203 ability candidates), 003 per-side v2 fixture, raw-only
`-end Illusion` repair, 004A ordinary v2 deterministic joint transition, 004B
ordinary v2 Python publication, and macOS ENV-001B/C1 profiles. Do not reopen
these as new implementation blockers. Their bounded tests do not prove complete
format reachability or complete episodes. In particular, the older Illusion
settling failure and older “scanner expansion next” prose are superseded by
later accepted entries, and ENV-001's remaining Windows work does not invalidate
the macOS simulator-record proof.

## Closure inventory

### Classification and effect profiles

Each inventory entry has exactly one required disposition:

- **D1 — Implement before faithful episode capture.** This includes focused
  validation/contract work needed to establish a capability; it does not always
  mean new production code.
- **D2 — Retain as validated raw evidence.** Retain current accepted raw behavior;
  where validation is pending, its explicit gate remains a faithful blocker.
- **D3 — Prove unreachable in `gen9randombattle`.** Open until pinned source,
  format, generator and indirect routes establish the proof. Absence from a set
  file or random sample is insufficient. If reachable, split out a D1 or D2
  implementation; do not silently reclassify it as excluded.
- **D4 — Exclude from the supported format.** Other formats/information regimes
  remain outside scope, with their rejection/privacy boundary preserved.

Effects use five columns: **O** observable state, **B** belief state, **A** legal
actions, **T** transition records, **E** terminal handling. The following profiles
are part of every row that cites them; an override in a row takes precedence.
This avoids mistaking a raw outcome for a new legal-action menu or belief fact.

| Profile | O | B | A | T | E |
|---|---|---|---|---|---|
| RAW | Preserve public record/prefix only; no new typed field or inferred absence. | Preserve evidence provenance at the same cursor; no posterior/category required. | Addressed current request remains authority; outcome does not create a choice. | Preserve order/repeats/hash through replay and restoration; no generic drop. | Retain through terminal; never implies termination by itself. |
| STATE | Existing typed fields must agree with permitted public/request evidence at each boundary; partial semantics must be explicit. | Same evidence cutoff; no hidden truth or future revelation. | Use fresh request even if effect changes availability/outcome. | Prefix plus correct typed successor and deterministic restoration. | Clear/reset only where source requires; final public state/outcome remains correct. |
| PRIVATE | Exclude private internal data from public observations; retain addressed request only where allowed. | Player regime excludes simulator truth; unknown stays unknown. | Use only addressed request; never expose hidden legality causes. | Opaque lineage allowed in its contract, no private payload leakage. | No hidden terminal reveal or reward inserted into player input. |
| STOP | Preserve last committed observation, cursor and hash; no candidate successor. | Preserve committed belief and lineage. | No fabricated pass/default; only explicit choice rejections are retryable. | No failed-candidate publication; stable indexed diagnostic. | Incomplete/failed with cause; cannot be faithful complete. |
| EPISODE | Both complete perspective sequences, including nonacting boundaries. | Both observation-bound belief lineages; no new posterior required. | Actor-only actions with request IDs and explicit waiting/requestless/terminal state. | Bind origin, all commits, ordering and final boundary; no missing/double commits. | Matching win/tie plus final prefix; no action required at terminal. |

### Protocol, grammar, routing and unknown values

| ID / exact scope | Source and reachability evidence | Current behavior and O/B/A/T/E effect | Required disposition / faithful gate | Dependencies and focused acceptance evidence |
|---|---|---|---|---|
| C01 `-singlemove`: Destiny Bond; Glaive Rush plus final `[silent]` | `Moves.destinybond.condition.onStart` (`data/moves.ts:3619`), `Moves.glaiverush.condition.onStart` (`:6896`). Direct pool candidates: Qwilfish/Froslass Destiny Bond (`sets.json:1462,3243`), Baxcalibur Glaive Rush (`:7337,7343`); generated-choice witness still needed. | Recognized unsupported before projection; RUN truncates. STOP now; RAW is sufficient provided existing volatiles do not acquire false persistent state. Effects execute in authoritative simulator. | **D1, blocker.** Add exact source-shaped raw-only forms; no typed one-move timer, damage multiplier or Destiny Bond model feature. | CE-01. Both actors, source-generated records, subsequent move/faint and terminal outcome, both runtime publications and restored transition; reject unknown labels, wrong tags/order/arity. |
| C02 `-singlemove`: Grudge and Rage | `data/moves.ts:8176,15098`, both source-marked `Past`; neither appears in current direct random pools. Copy/call paths not proven closed. | Same global token stop; RAW would suffice for event evidence but broad mechanic support is unproven. | **D3, blocker until source closure.** Do not require typed mechanics or expand format. | CE-03A/B. Prove excluded by generator plus indirect call/copy closure; if a valid path exists, exact raw grammar and correct existing state fields become a separate bounded slice. |
| C03 Unresolved aliases `clearstatus`, `-clearstatus`, `nothing` | MAN `review.unknowns.generic-parser-alias-semantics`; no supported emitter execution path. Canonical `-nothing` is Splash source-backed and distinct. | Stable unresolved-alias stop before publication. STOP. | **D3, blocker until supported-format absence is established.** | CE-03B; trace exact emitters/normalizers/stream origin; retain negative TS/Python controls. No alias rewriting. |
| C04 Internal bare `copyboost`, `invertboost`; bare `ability`; legacy `-fieldend RainDance` | MAN recognized aliases; SCH B-05; `effect_discovery.special_values.raindance`. Bare ability/field-end weather have compatibility-fixture evidence, not pinned emitters. | First two stop; bare ability and special raindance retain raw only. STOP/RAW respectively. | **D3 for emitter reachability, blocker to closure ledger only.** Accepted compatibility need not be removed. | CE-03B/CE-02; establish no simulator route or validate route if found. Never treat raw RainDance field-end as typed weather clearing. |
| C05 `-singleturn` Instruct emitter | `Moves.instruct`, `data/moves.ts:10009`; omitted from the closed 21-template set; no direct pool entry found. | Source form is rejected; grammar error can become execution failure rather than recognized protocol truncation. STOP. | **D3, blocker until indirect reachability proof.** | CE-03B. Source-form witness if reachable, then dedicated raw grammar; no unsupported source record counted complete. |
| C06 Schema B-04: HP/stage tag dependencies/order and unconstrained suffixes | SCH G01–G58; `Battle.add/addMove/attrLastMove`, `sim/pokemon.ts:1990–2018`, `sim/battle.ts:2034–2203`, `sim/battle-actions.ts:412–462,545,590–640,1512–1516`. Reachable generic health/stage paths; arbitrary free-text suffixes not source proof. | Partial allowlists/ranges and generic `>=` templates accept some unclosed combinations. STATE for typed values, RAW for source tags. | **D1, blocker.** Close supported-format field shapes; preserve opaque source text where it cannot affect typed state/privacy. Do not build a global protocol grammar. | CE-02A/B. Source-shaped positive and rehashed negative controls across p1/p2 and input/successor, including status/type/effect values, configured identifiers and suffixes. |
| C07 B-02 fixture raw/v2 classification drift; B-06 `move` target prose | SCH six T† aliases (`boost`, `unboost`, `setboost`, `clearboost`, `clearallboost`, `transform`) type v2 stages despite raw labels. Current shared move fixture still says target `or -`; validators reject `-`. | Metadata drift, not demonstrated runtime parity defect. STATE; no action/terminal behavior change. | **D1, closure documentation/contract blocker**, small alongside grammar work. | CE-02A. Match effective versioned projection; preserve historical IDs and accepted compatibility. Assert six aliases and omitted/empty/null/SOA move targets, with `-` rejected. |
| C08 B-07 generic `error`, split HP and private stream routing | `Side.emitRequest/emitChoiceError` (`sim/side.ts:475–493`), `Battle.addSplit` (`sim/battle.ts:3012–3020`), `BattleStream` (`sim/battle-stream.ts:84–175,343–350`); exact audience is channel-dependent, not token-derived. | `error` raw grammar has no side identity; audience relies on routing. Requests are sanitized; full source-channel matrix remains unclosed. PRIVATE + STOP for rejected choices. | **D1, privacy blocker.** Prove or enforce spectator/player stream separation for all retained paths. | CE-02C. Inject distinct private request/error/HP values for each side; verify shared prefixes and opposite views unchanged; errors cannot impersonate public evidence or terminal state. |
| C09 Any new unknown command/effect or wrong effect family | MAN scanner and `effect_inventory.ts`; generic event value allowlist now rejects unknown/mismatched IDs. Future drift is intentionally unknowable. | Guard exists; candidate may become settling/execution failure if rejection occurs in extraction. STOP. | **D1, retain guard; diagnostic coverage only.** Existing rejection behavior is accepted; reachable present unknown edges are C10–C16, not waived here. | CE-08B. Stable original cause/index and committed boundary preserved for ingestion/projection/publication variants; no requirement to predict future formats. |
| C10 Computed move `addVolatile(volatile)` | `Moves.psychup.onHit`, `data/moves.ts:14570`; literal loop over dragoncheer/focusenergy/gmaxchistrike/laserfocus. Manifest remains unknown at this callsite despite bounded stage-copy acceptance. Direct Psych Up set candidate not found; indirect paths open. | Known emitted values use existing inventory; unseen value stops. STATE for public presence/stages; silent copied parameters stay PRIVATE. | **D1, blocker to source-value closure**; no FEATURE parameter demand. | CE-03B. Record finite loop values, removal/silent-copy behavior, source route or no-route proof; ensure no stale typed volatile when copied/removed silently. |
| C11 Computed ability `addVolatile(volatile)` / Costar | `Abilities.costar.onStart`, `data/abilities.ts:695–712`; same four-ID loop; immediate `allies()[0]` guard; constructed scanner probe does not prove singles reachability. | Values classified, callsite still unknown; `[from] ability: Costar` `-copyboost` is outside Psych Up-only grammar. STATE/STOP. | **D3, blocker until singles no-ally route is proven** including transformed/copied ability and operative format. | CE-03B. Prove guard under single-active format; keep constructed scanner evidence as accepted scanner evidence, not random-format mechanics. |
| C12 Computed condition `addVolatile(effect.id)` | `Conditions.twoturnmove.onStart`, `data/conditions.ts:290`; finite move origins depend on selected/called moves. | Unknown family closure; value allowlist handles known emissions and stops others. RAW/STATE according to emitted ID, private target/duration excluded. | **D1, blocker.** Enumerate source-bounded possible IDs through selected/called move paths. | CE-03A/B; source witness for each distinct emitted schema and public lifecycle, no hidden lastMoveTargetLoc leak. |
| C13 Computed `addVolatile(move.id)` | `BattleActions` `sim/battle-actions.ts:264`, guarded by `cantusetwice` and repeated move; used for hint path. | Unknown value closure; inventory guard at emitted value. RAW; no inferred action prohibition. | **D1, blocker.** Bound flagged move IDs and emitted consequences. | CE-03A/B; repeat-use source controls prove request legality, raw hint and restoration; unreachable candidates need source proof. |
| C14 Computed `addVolatile(moveData.volatileStatus)` | `sim/battle-actions.ts:1250`, move-hit application; resolved move fields and callback mutation can supply value. | Generic known values classified; callback-derived closure remains unknown. STATE/RAW based on inventory. | **D1, blocker.** Close mutation/call graph from generator-reachable moves. | CE-03A/B; map each possible value/family and any dynamic overrides; source-drift plus representative emitting controls. |
| C15 Computed `addVolatile(linkedStatus)` | `Pokemon.addVolatile`, `sim/pokemon.ts:1946`; callers may establish linked source effects. | Manifest unknown, fail closed on unknown emitted values. STATE/PRIVATE: links/targets not generally public. | **D1, blocker.** Bound argument origins and distinguish silent internal links from public effects. | CE-03B/CE-04A; source-linked start/remove/switch/faint cases, no private source/target exposed. |
| C16 Remaining generator/callback composition | MAN `format_provenance.selection_trace/forms`, `RandomTeams.randomTeam/randomSet/randomMoveset/getAbility/getPriorityItem/getItem`; direct candidates pruned by team/role/Tera; Magic Bounce reflection and Ditto/Imposter copying have representative routes only. | Format/source drift protected; representative reachability accepted, exhaustive value/emitter closure unproven. STATE/RAW/PRIVATE per output. | **D1, blocker.** Build a bounded format output/condition/request inventory from generators and indirect calls; do not type every callback. | CE-03A/B; every reachable output/request shape has a row or proven exclusion, generated-item branches included; random sampling supplements but cannot replace source reasoning. |

### Lifecycle and progression gaps

| ID / exact scope | Source and reachability evidence | Current behavior and O/B/A/T/E effect | Required disposition / faithful gate | Dependencies and focused acceptance evidence |
|---|---|---|---|---|
| C17 Public volatile presence versus expiry, source and lock targets | MAN `condition_semantics.move_volatile`, MEC-06; `Pokemon.addVolatile/removeVolatile/clearVolatile`, per-ID callbacks. Reachable ordinary effects; reviewed confusion/Substitute and ordinary switch/faint resets are bounded evidence. | Presence set does not express all expiry/removal/transfer semantics. STATE: stale “present” at a decision is incorrect even with complete raw log. B has no volatile posterior; A request-derived; T replay must agree; E final state must not retain false public presence. | **D1, blocker only where existing typed assertions can be wrong.** Private durations/targets need no typed extension. | CE-04A, after CE-03 output paths. Audit represented reachable IDs by lifecycle equivalence class; start/end/restart, switch/drag/faint/re-entry, silent removal and linked effects. Raw-only downgrade/unknown is allowed only with explicit v2-compatible semantics. |
| C18 Temporary types: Roost, Reflect Type, Type-event expiry | MEC-03, MAN known gaps; `Moves.roost`, type callbacks, `Pokemon.getTypes`; Roost has direct Articuno/Zapdos/Moltres candidates. Reflect Type lacks demonstrated generated route. | Soak, added third type and ordinary Transform scoped accepted; Roost `-singleturn` is raw-only. **CE-04B implementation evidence now proves its duration expires in residual before the next capturable boundary; no typed temporary type is needed.** Reflect Type remains excluded. | **CE-04B implementation checkpoint, unreviewed.** Keep Reflect Type and unproven type-effect co-occurrence out of scope. | CE-04B focused review: verify exact source order, both perspectives, restored v2/Python bundles and raw-only classification; keep offense/private counters out. |
| C19 Stage/copy/transfer beyond accepted v2 | MEC-04, MAN known gaps; `Pokemon.transformInto/copyVolatileFrom`, `Battle.boost`, direct clear/invert/swap/theft emitters and ability/item callbacks. CE-04C now closes generator roots, indirect callers, reset paths and exact typed records against pinned v0.11.10. | Accepted v2 records correctly represent all surviving stage routes. Psych Up/Topsy-Turvy exact compatibility semantics remain bounded; unsupported Costar/swap/Baton Pass records still stop. No new critical-hit feature. | **CE-04C accepted as scoped source/evidence closure; no production slice remains.** Keep raw-only/private values out of public stage state; no generic transfer model. | Reuse accepted Transform, Psych Up, Topsy-Turvy, selective-clear, lifecycle, B05–B08/B11/B14–B18 source proofs; CE-04C generated witnesses cover Haze, Clear Smog, Mirror Armor, Contrary, Imposter and Belly Drum. |
| C20 Side-condition layers/caps/expiry/swap | MAN unknown “How do all side-condition layer updates expire”; `Side.sideConditions`, side callbacks. Hazards/screens direct/callback routes. | Counts starts/deletes end/swaps; count is not universally a layer model. STATE: public layer semantics may misstate hazards; B uses evidence only; A request-derived; T/E must retain actual public layer/removal events. | **D1, blocker where count asserts incorrect current public state.** Internal timers remain D2/PRIVATE. | CE-04D. One slice per differing reachable family: stackable hazards, nonstacking screens, swap/removal; capped repeat applications, expiry and restored prefixes. Explicitly define remaining count-map semantics. |
| C21 Field: weather, terrain, pseudo-weather suppression and end | MAN `condition_semantics.weather/terrain/pseudo_weather`, MEC-09; `Field`, relevant ability/item/move callbacks. Four terrain IDs and weather registry accepted; full interactions unproven. | Coarse IDs supported; sources/durations omitted. STATE for ID/suppression assertions; RAW/PRIVATE for timers/sources. | **D1 for boundary correctness review**, not a demand to type duration/source. | CE-04E. Source-generated set/replace/clear, upkeep/end, suppression vs removal, item/ability interactions and simultaneous effects; retain raw where ID stays correct and omission explicit. |
| C22 Ability/item/status callback composition | MEC-05/08, MAN nested Ability/Item conditions, `data/abilities.ts`, `data/items.ts`, `data/conditions.ts`. Generator items conditional; reflection/copy may change output. | Public names, selected suppression and coarse status supported; full copying/suppression/silent changes unclosed. STATE for public values; PRIVATE for unrevealed loadout/counters. | **D1, blocker for reachable incorrect typed fields or private leakage.** | CE-03A/B then CE-04F. Group by output shape: reveal/end/change/suppress/restore, status cure/reapply and HP consequences; compare allowed evidence under hidden-truth perturbation. No inference of unrevealed item/ability. |
| C23 Slot effects: Wish, Healing Wish, Lunar Dance, Future Move and Revival slot state | `Move.slotCondition`, `Side.slotConditions`, `Conditions.futuremove/healreplacement`; Wish/Healing Wish/Revival direct candidates in MEC; remaining routes not established. | Internal slot effects raw-only; public heal/status/faint/request effects handled independently. RAW/PRIVATE; public pending-slot model absent. | **D2, pending sufficiency validation is a blocker.** No typed countdown/slot model required if every public consequence and boundary survives. Revival selection exceptions are C25. | CE-04G. Source-generated delayed heal/damage/replacement, consumed/cancelled slot, switch/faint/terminal, split HP and restored continuation; no stale existing status/HP. |
| C24 v2 progression beyond ordinary joint transitions | PIPE 004A/B excludes forced switch, Revival, waiting/requestless and runner; COV accepts ordinary forced-switch/settling in earlier bounded scope. | Guards classify joint, forced-switch+wait, revival+wait; other waiting/requestless states stop. Both successor observations exist in integration. EPISODE/STOP. | **D1, blocker to v2 episode proof**, reuse accepted execution and change production only on failure. | CE-05A/B. p1/p2 U-turn/KO, chained entry-hazard KOs, simultaneous ordinary replacements, consecutive selections, restored request consumption, Python publication and exact cursor chain. |
| C25 Revival excluded singles variants | MAN known gaps, COV bounded bench review; `assertSupportedSelectionRequests` / `assertRevivalSelection`, source `Moves.revivalblessing` and `Side` requests. Active-target instaswitch, active/fainted reviver, simultaneous-selection reachability unresolved. | Single living reviver + waiting side + fainted bench target accepted; excluded shapes truncate. STATE/STOP; owner-only selection evidence. | **D3, blocker until each singles variant is proven unreachable or split into implementation.** Multi-active variant separately D4 (C30). | CE-05C after CE-03. Source trace normal/reaction/self-faint order, revived active slots and request generation; one witness/proof per variant. Any reachable variant needs legal slot binding, atomic rollback, both successor privacy and v2 publication. |
| C26 Waiting, one-sided actionable/requestless, both requestless, no legal actions, team preview | INT boundary classifier; `Battle.makeRequest`, `Side.emitRequest`, settling consumers; scoped singles random format normally skips constructed-team preview. | Unsupported boundaries truncate; nonwaiting empty action menu raises `pipeline/v1/no-legal-actions`; no fabricated action. EPISODE/STOP. | **D3, blocker for unresolved stable-boundary reachability.** Transient delivery gaps must be resolved by settling, not promoted to decisions. | CE-05B/C. Enumerate request-state pairs at initial/turn/switch/revival/terminal boundaries; prove impossible cases from source or implement real request/settling transition. Team preview requires format proof, not cross-format support. |
| C27 Origin, both-perspective evidence and segment retention | RUN summaries/actor-only `records`, `continuePipelineEpisode` documented segment-only; INT commit bundles. This structural gap is reachable on every one-sided transition and zero-record terminal segment. | Initial/final boundaries contain IDs/cursors but not full observations/prefixes. Actor records cannot alone guarantee the waiting side's full sequence. EPISODE. | **D1, blocker.** Version/bind episode evidence or immutable referenced payloads covering both sides, initial request, all successors and final outcome. | CE-06A/B. Walk/reconstruct complete two-perspective chains without hidden snapshots or synthetic waiting-side actions; zero-action terminal capture, actor-only DATA rows, validated resume origin and duplicate/gap rejection. |
| C28 Terminal completeness: win/tie, initial terminal, auto-tie, final delivery | RUN `terminal`; COV bounded settling/faint-terminal acceptance. `Battle` emits turn-1000 warnings via `bigerror` (`sim/battle.ts:1766`) before tie; token unaccepted. | Matching terminal checks exist; long battle warning may stop before terminal. Restore accepted in narrower scope; `completed` always false-fidelity. EPISODE; `bigerror` RAW after public-source validation. | **D1, blocker.** Allow exact public auto-tie warnings or source-bounded diagnostic grammar; prove terminal/outcome chain. Other `bigerror` branch EV warning at `:1905` needs generator no-route proof or safe grammar. | CE-02D + CE-06B/CE-08A. Source-derived long-battle tie without a 256-transition test budget, normal win, simultaneous KO/tie and terminal during one-sided progression; no successor actions, end+both views agree, no lost final records. |
| C29 Diagnostic `debug`, `showteam`; remaining unaccepted `-ohko`, `-swapboost` | MAN package emitters; `Battle.debug/debugError` (`sim/battle.ts:3079,3089`), `showteam` (`:3151`), `BattleActions` OHKO (`:1018`), move-specific stage-swap emitters (`data/moves.ts:8277,8763,14300`). Direct OHKO/swap candidates not found in inspected pools. | Unknown token stops. `showteam` can serialize full teams; never blanket public-allowlist. STATE/STOP for swaps; PRIVATE for debug/team output; RAW potentially sufficient for OHKO marker. | **D3, blocker until production-route/source-visibility proof.** Reachable public diagnostic gets its own D1 raw grammar; private diagnostics remain outside player prefix. | CE-02C/CE-03B; bind debug/team-preview options, reveal timing and all OHKO/call routes; test no hidden team publication. |
| C30 Other-format scope | MAN package emitter source paths and effective singles `gen9` format: `-burst`, `-candynamax`, `-center`, `-combine`, `-cureteam`, `-mega`, `-notarget`, `-primal`, `-waiting`, `-zbroken`, `-zpower`, `c:`, `custom`, `j`, `swap`, `updatepoke`; Dynamax/Gmax/Max Guard, Mega/Primal/Z, Rigged Dice/mods, doubles/multi-active/targeted action syntax. | Rejected/unsupported or inventory-only; no format expansion. STOP for invalid input; no required O/B/A/T/E modeling. | **D4.** Preserve pinned format/source guards. The Pledge `-combine/-waiting` branches require allied simultaneous moves; scope evidence must remain explicit in CE-03 ledger. | CE-03 source-route reconciliation records existing exclusion basis; new contradictory singles evidence reopens D1 rather than erasing it. Non-`gen9randombattle` rejection is already accepted. |

C30 source mapping is the manifest's per-token `protocol.emitted_static_tokens`:
`-cureteam` is in Gen 2/4 overrides; `-notarget` in Gen 1/1 Stadium/3 overrides;
`c:`, `custom`, `j` in Gen 9 SSB overrides; `updatepoke` in Gen 8 DLC1 rules.
The operative `gen9` random format does not load those overrides. Base-engine
`-burst/-mega/-primal` routes require the corresponding transformation species/
item/action (`Pokemon.formeChange`, `sim/pokemon.ts:1398–1408`), and
`-zpower/-zbroken` require Z action/move paths (`sim/battle-actions.ts:300,1828`);
these are excluded by the pinned Gen 9 random generator/action scope, not by
absence of their tokens in samples. `-center`/`swap` are active-position paths
(`sim/battle.ts:1696,1517`); `-candynamax` is the Dynamax action notification
(`:1707`). Pledge `-waiting/-combine` requires an allied queued Pledge action
(`Moves.firepledge/grasspledge/waterpledge`; e.g. `data/moves.ts:5579–5600`).
CE-03 keeps those format/source guards auditable; source/config drift invalidates
the exclusions. `-ohko`, `-swapboost`, `bigerror`, `debug`, and `showteam` have
base-source paths and were deliberately separated into C19/C28/C29 for closure.
The manifest's static reconciliation also lists `tier`, but the current shared
contract accepts it for validation then filters it; A03/SCH G43 govern that case.

### Exhaustive raw-only ledger

The following groups enumerate all **62 effective raw-only supported tokens**
from SCH G01–G58 exactly once. MAN has 69 raw-labelled commands: subtract the
six v2 typed exceptions in C07 and filtered `tier` to obtain 62. This is an
inventory reconciliation, not a new attestation. Each group's listed tokens
inherit its source, reachability, five effects, dependencies and acceptance.

| Raw ID / exact tokens | Source / reachability and current behavior | Disposition, effects and acceptance |
|---|---|---|
| R01 `-activate`, `activate`, `-block`, `block`, `-crit`, `crit`, `-fail`, `fail`, `-hitcount`, `hitcount`, `-immune`, `immune`, `-miss`, `miss`, `-mustrecharge`, `mustrecharge`, `-prepare`, `prepare`, `-resisted`, `resisted`, `-supereffective`, `supereffective`, `cant` | SCH G02/21/22/24/28/49/50/52, MAN outcome grammar/source groups; canonical events are public mechanic outcomes, many bare counterparts compatibility-only. Shape-validated raw retention. | **D2, RAW.** Current retention accepted; CE-02 closes relevant loose suffix grammar, CE-03 resolves bare emitter routes, CE-08 verifies continued publication. No accuracy/failure/recharge/crit feature or action inference required. |
| R02 `-fieldactivate` | SCH G18; `Field`/move callback activation output, public when emitted. | **D2, RAW.** No persistent field state implied; CE-02/04E prove source tags and no required typed mutation lost. |
| R03 `-singleturn` | SCH G27 closed 19 untagged + 2 tagged templates; PIPE emitter table; per-template dispositions R03-P/R03-X below. Four direct move families Beak Blast, Focus Punch, Protect and Roost; other literal routes unresolved. | **R03-P: D2, RAW; R03-X: D4.** Existing literal/tag/active-source controls accepted. No one-turn volatile/timer required. Roost boundary type correctness is C18; Instruct excluded template C05. CE-03 records each route; CE-04B/08 prove sufficiency. |
| R04 `-anim` | SCH G36: source, exact `Spectral Thief`, target; pinned source/fixture, generated route not established. | **D2, RAW.** Retain validated animation only; actual stages must come from separate evidence. CE-03 route proof and C19 where needed. |
| R05 `-nothing` | SCH G26; Splash `data/moves.ts:18380–18384`, canonical no-payload emitter, distinct from bare `nothing`. | **D2, RAW; accepted retention.** No state mutation required; preserve exact empty-payload grammar. |

### Random-controller terminal settling `-hitcount` source table (2026-10-02, unreviewed repair)

| Pinned source path and Gen 9 Random Battle reachability | Exact public record form | Disposition |
|---|---|---|
| `sim/battle-actions.ts:836-979` resolves `move.multihit`, returns without a record only when the loop leaves `hit === 1`; on a single-target KO it increments `hit` before breaking, calls `faintMessages`, then calls `Battle.add('-hitcount', targets[0], hit - 1)` for non-`smartTarget` multi-hit moves. The operative generator is singles and `data/random-battles/gen9/sets.json` includes Maushold's Population Bomb; `data/moves.ts:14103-14115` sets `multihit: 10`. | `|-hitcount|p1a: <name>|<1..10>` or `|-hitcount|p2a: <name>|<1..10>` while the target remains active. `Pokemon.toString()` (`sim/pokemon.ts:510-513`) uses the active slot, and singles admits only slot `a`. | **RAW only.** The accepted decimal set is exactly `1..10`: a one-hit KO reaches the `hit - 1` emitter after the loop increments before breaking; Population Bomb provides the generated ten-hit upper bound. No typed hit counter, boost/ability inference, legal-action change, hidden counter, or model feature is claimed. |
| The same source calls `faintMessages` before `Battle.add`. For a final multi-hit KO, `Pokemon.toString()` sees a non-active target and returns its side-only full name. | `|-hitcount|p1: <name>|<1..10>` or `|-hitcount|p2: <name>|<1..10>` after that faint boundary. | **RAW only.** The pinned one-hit final-KO witness is `|faint|p2a: Target` followed by `|-hitcount|p2: Target|1`. |
| Doubles/multi-active slots are excluded by the operative `gen9randombattle` singles format; `p1b:`/`p2b:` and slots `c`–`f` have no supported emitter route. Counts `0` and `11+` contradict the pinned loop and Population Bomb maximum. | No tags, extra fields, whitespace repair, noncanonical side, identifier, or count spelling. | Reject before TypeScript projection and Python DATA-001 publication; rejected rehashed candidates preserve their committed state and lineage. |

The direct TypeScript/Python matrix covers both valid active and post-faint forms,
both perspectives, v1/v2 input and successor prefixes, and the exact malformed
slot/count controls. The random-controller terminal fixture continues to prove
that its real `|-hitcount|p1: Houndstone|2` terminal record is retained and two
fixed-seed controller runs agree after excluding only `|t:|` framing.

**Correction evidence (2026-10-02, unreviewed):** The shared TypeScript/Python
finite domain is now exact decimal `1..10`. The direct source-backed terminal
witness replaces the former `1` rejection control; `0`, `11`, leading-zero,
malformed identifier, tag, and extra-field controls remain rejected before
projection or DATA-001 publication. The current coverage checker computes
`e7173364c14678c448adfeab0ce81eed56109776e8cdae501d6b6e2e7be71d1a`; it is unreviewed and does not alter either manifest digest field.

### Random-controller terminal settling `-hitcount` scoped review verdict (2026-10-02): accepted

The focused review accepts this raw-only boundary. Pinned hit-loop ordering proves that a one-hit Population Bomb KO emits a post-faint count of `1`, and generated Maushold's Population Bomb (`multihit: 10`) establishes the upper bound. Only exact four-field `-hitcount` records with canonical singles active (`p1a:`/`p2a:`) or post-faint side-only (`p1:`/`p2:`) targets and ASCII decimal counts `1..10` are accepted. Doubles slots, malformed or whitespace-repaired identifiers, leading-zero or non-ASCII count spellings, tags, and extra fields reject before TypeScript projection or Python DATA-001 publication and preserve committed lineage. Rehashed TypeScript/Python coverage exercises v1/v2, p1/p2, input/successor prefixes, rollback, and no-output rejection. The fixed-seed random-controller regression reaches the same terminal result while excluding only timestamp framing. This scoped review attests local digest `e7173364c14678c448adfeab0ce81eed56109776e8cdae501d6b6e2e7be71d1a`.

### CE-04-SLOTS Healing Wish review finding (2026-10-02, superseded by unreviewed implementation checkpoint)

**Historical blocker.** This finding identified absent lifecycle, fixture, provenance and v2 publication evidence, plus acceptance of `|-heal|p1a: Target|100/100|[from] move: Healing Wisp`. The implementation checkpoint immediately below supplies those bounded repairs and records its unreviewed digest. It does not change manifest digest fields or attest CE-04-SLOTS Healing Wish.

### CE-04-SLOTS Healing Wish source lifecycle table (2026-10-02, implementation checkpoint; unreviewed)

Pinned `Moves.healingwish` (`data/moves.ts:8639-8673`) sets
`slotCondition: 'healingwish'`; `BattleActions` creates the side-position
condition through `addSlotCondition` (`sim/battle-actions.ts:1258`). Its
replacement callback calls `target.heal(target.maxhp)`, `target.clearStatus()`,
then emits the sole public provenance form before removing the slot condition.
The status clear deliberately has no `-curestatus` record (`Pokemon.clearStatus`
is silent), so the exact public Healing Wish `-heal` is the public evidence for
both full HP and cleared status.

| Lifecycle fact | Pinned behavior | Capture disposition |
|---|---|---|
| Creation and pending state | A successful self-targeting Healing Wish installs `side.slotConditions[position].healingwish`; its EffectState holds target/side, source, source slot, order and internal callback data. | Retain the ordinary public `move` and faint evidence only. Slot condition, source identity, timers/order, raw requests and simulator snapshot remain private restoration state. |
| Outgoing user | `selfdestruct: 'ifHit'` faints the user after the condition is installed. | Existing public `faint`/replacement evidence applies. No typed pending effect, forecast, source link or delayed-effect model is added. |
| Replacement resolution | `onSwitchIn` invokes `onSwap` for the current slot occupant. If it is living and has missing HP or a status, it is fully healed, silently cleared, emits `|-heal|<active>|100/100|[from] move: Healing Wish` on the public stream, then removes the condition. The owner-private split carries its exact full HP ratio instead of `100/100`. | Shared validation accepts only the literal public active-target, status-free `100/100` form. The owner-private exact-HP split is omitted; `state_extractor` routes only the spectator public record to typed state and clears status from that provenance. |
| Healthy incoming replacement | A living, full-HP, status-free occupant does not satisfy `onSwap`; the condition remains private and emits no Healing Wish result. | No public completion or typed marker is fabricated. |
| Cancellation | `onTryHit` emits `-fail` and returns without self-destruct or a slot condition when `canSwitch(source.side)` is false. | Preserve ordinary public failure evidence; emit no pending/result state. |
| Terminal | If terminal resolution occurs after the user faints and before a replacement, no `onSwap` result occurs. | Retain terminal outcome; emit no invented Healing Wish completion. |
| Restoration/publication | Serialized candidate snapshots retain the private slot condition. Independent v2 restores make identical activation, forced replacement and next-turn transitions; both public perspectives retain the same public prefix while only the selected replacement record publishes. | Focused p1/p2 fixtures validate the replacement actor bundle and then validate both actual joint-continuation v2 bundles in Python with the resolved Healing Wish evidence in each input prefix; they also cover privacy, deterministic continuation and rejected rehashed evidence. |

The shared TypeScript/Python boundary rejects `Healing Wisp`/other invented
Healing-prefix move names, a side-only target, incomplete or status-bearing HP,
reordered/duplicate/extra tags, and `[wisher]` attachment before projection or
DATA-001 publication. It retains ordinary heals and the separately accepted
Wish `[wisher]` pair. Tests cover v1/v2, p1/p2, input/successor rehash,
committed-candidate preservation and empty stdout on rejected Python
publication. The simulator fixture covers both actors, real Will-O-Wisp status
before Healing Wish, forced replacement, status/HP result, healthy
nonapplication, `canSwitch` cancellation, terminal-before-replacement,
restored twins, deterministic continuation, and both actual resolved-prefix v2
Python bundles. It does not change Future Sight,
other delayed effects, item callbacks, Revival Blessing, or episode readiness.

`tests/healing_wish.test.ts` is listed in `local_coverage_sources.files`. The
computed local coverage digest is
`eff9daa2ac3b737c7983d0ff951244d48b9b532c54b3595904cfb2be63c023ef` and is
**unreviewed**. `sha256`, `reviewed_sha256`, and all manifest attestation fields
remain unchanged. This checkpoint does not accept CE-04-SLOTS, PIPELINE-002,
or `faithful_complete_episode:false`.

### CE-04-SLOTS Healing Wish scoped review verdict (2026-10-02): accepted

Pinned `Moves.healingwish` creates a private slot condition, then its replacement callback restores HP, silently clears status, emits exactly `|-heal|<active target>|100/100|[from] move: Healing Wish` on the public Gen 9 stream, and removes the condition. The owner-private exact HP split is omitted before typed routing; only the spectator public record changes typed HP or status. The bounded fixture covers both actors and perspectives, qualifying replacement, healthy retention, no-replacement cancellation, terminal-before-replacement, restored v2 twins, deterministic continuation, and Python validation of actual successor bundles. TypeScript/Python reject invented provenance, noncanonical targets, nonliteral or status-bearing HP, and malformed tag forms before projection or DATA-001 publication while preserving candidate lineage. This review attests `eff9daa2ac3b737c7983d0ff951244d48b9b532c54b3595904cfb2be63c023ef` for CE-04-SLOTS Healing Wish only. Future Sight, other delayed effects, item callbacks, Revival Blessing, CE-05, PIPELINE-002, and `faithful_complete_episode:false` remain outside this verdict.

### CE-04-SLOTS Future Sight delayed public-consequence lifecycle (2026-10-02, implementation checkpoint; unreviewed)

Pinned `Moves.futuresight.onTry` (`data/moves.ts:6615-6649`) creates the private `futuremove` slot condition and stores `move`, `source`, and `moveData`. `Conditions.futuremove` (`data/conditions.ts:375-424`) records the target slot and ending turn, removes the condition at residual resolution, emits the exact public end marker, and invokes ordinary move damage. The later damage emitter has no Future Sight provenance tag; its public spectator HP record is the only typed HP/faint evidence.

| Lifecycle fact | Pinned source/protocol behavior | Capture disposition |
|---|---|---|
| Creation and pending state | `addSlotCondition(target, 'futuremove')` stores source, target slot, ending turn, move data and landing calculation inputs privately. | Retain only public move/start raw evidence. No public Future Sight timer, forecast, source/target link, request payload, split HP branch, or simulator snapshot is added. |
| Activation | `Moves.futuresight.onTry` emits `|-start|<active source>|move: Future Sight` with no tag or extra field. | Shared TypeScript/Python validation accepts exactly that active-target shape and retains it raw-only. |
| Intervening source switch, drag or faint | The condition belongs to the target side position. A living current occupant at that position receives the later hit; `onEnd` only cancels for a fainted target or `target === data.source`, so a fainted original source still resolves against a living target slot. | Existing public switch/drag/faint/replacement records establish the visible occupants. No pending recipient, source link or cancellation cause is typed before the actual public damage record. |
| Resolution | `Conditions.futuremove.onEnd` emits `|-end|<active target>|move: Future Sight`, then `trySpreadMoveHit` emits ordinary `|-damage|<active target>|<condition>` records. | Exact Future Sight start/end forms are raw-only. Existing public `-damage` parsing changes typed HP/faint/status only from the spectator record; no generic delayed-damage provenance grammar is introduced. |
| Faint, replacement, cancellation | If the current target is faint when `onEnd` runs, the condition is consumed with a hint and no Future Sight end/damage result. A living replacement at the target slot can instead receive the normal result. | Retain ordinary faint/replacement evidence and no fabricated delayed completion. |
| Terminal and restoration | A terminal outcome before the residual ends the battle without a later Future Sight result. Serialized simulator state retains the private condition so restored candidates can continue deterministically. | Both public v2 observations retain only public raw records and typed public damage; private slot state remains solely in the authoritative restoration snapshot. |

`tests/future_sight.test.ts` drives pinned-engine p1/p2 fixtures through activation, source switch, source faint with a living target, target drag, target faint, replacement, terminal before residual, restored twins, deterministic continuation, both perspectives, and Python validation of actual v2 transition bundles. It confirms that the owner-private exact split-damage record never enters an observation or DATA-001 bundle. Shared malformed controls reject side-only targets, misspellings, leading/extra/reseparated source-family spellings, and missing/reordered/extra fields and tags in both v1/v2, p1/p2 and input/successor rehashed candidates before projection/publication; rollback preserves the candidate and lineage with empty Python stdout.

The new raw-only `movefuturesight` inventory entry and all Future Sight source, contract, fixture and cross-runtime tests are listed in `local_coverage_sources.files`. The checker computed `563cd723d2b31429eb4ca5a2570211b3b81035a1979c42536d7d38b620243e1d`; it is unreviewed and no manifest digest or attestation field changed. This does not attest coverage, CE-04-SLOTS, PIPELINE-002, or `faithful_complete_episode:false`, and does not broaden Doom Desire, Lunar Dance, generic delayed effects, item callbacks, CE-05, or episode readiness.

### CE-04-SLOTS Future Sight scoped review verdict (2026-10-02): accepted

Focused review accepts only Future Sight's bounded delayed public-consequence
surface. Pinned `Moves.futuresight.onTry` emits exact active-source
`|-start|<active source>|move: Future Sight`; pinned
`Conditions.futuremove.onEnd` emits exact active-target
`|-end|<active target>|move: Future Sight` before ordinary untagged damage.
The private slot condition, ending turn, original source, target slot, move
data, split HP, requests, and simulator state are omitted. Only the spectator
damage record updates typed HP/faint state. Generated Gen 9 Random Battle set
entries include Future Sight, and p1/p2 pinned-engine v2 fixtures cover
switch, faint, drag, replacement, terminal/no-result, restoration,
deterministic continuation, rollback, and Python publication. Shared
TypeScript/Python validation rejects malformed source-family forms before
projection or DATA-001 output. This scoped review attests
`563cd723d2b31429eb4ca5a2570211b3b81035a1979c42536d7d38b620243e1d` for
CE-04-SLOTS Future Sight only. Doom Desire, Lunar Dance, generic delayed
effects, item callbacks, CE-05, PIPELINE-002, and
`faithful_complete_episode:false` remain outside this verdict.
| R06 `ability`, `endability`, `enditem`, `item`, `status`, `curestatus`, `damage`, `heal`, `sethp`, `fieldstart`, `fieldend`, `weather`, `formechange`, `terastallize`, `sidestart`, `sideend`, `swapsideconditions` | SCH G01/09/10/15/16/18/19/23/34/42/48. Bare compatibility spellings retained raw; canonical dash counterparts have typed handlers. Bare ability source gap C04. | **D2, RAW**, pending CE-03 emitter reconciliation. If any is actually emitted instead of a typed canonical update, require proof raw-only doesn't leave false typed state; implement correction if it does. No alias normalization by guesswork. |
| R07 `start`, `end`, `upkeep`, `clearpoke`, `teampreview`, `done` | SCH G13/39/44/55; battle/lifecycle or adapter markers; preview route constrained by random format. | **D2, RAW.** Accepted syntax retention; marker `end` alone does not authorize terminal. CE-05/06 validates initial and terminal use and proves preview route. |
| R08 `gametype`, `rule`, `rated`, `t:` | SCH G33/54/57; format/battle metadata and normalized timestamp. | **D2, RAW.** Metadata retained, `t:` normalized under existing pipeline identity rule; no mechanics inference. Already accepted normalization, source-format join in CE-08. |
| R09 `-hint`, `-message`, `message`, `c`, `chat`, `inactive`, `inactiveoff`, `error` | SCH G33/35/51/53/56/58; MAN diagnostics/streams; `error` audience ambiguous without channel; inactive/chat often outside simulator core. | **D2, RAW only for validated public audience.** C08 is a privacy blocker, not permission to retain a private error publicly. CE-02C/03 resolve channels/routes; no parsing prose into facts/actions/terminal outcome. |

R03's per-form reachability remains explicit: `move: Beak Blast`, `move: Focus
Punch`, `Protect`, and `move: Roost` have direct candidate evidence. `move:
Protect` (Baneful Bunker/Burning Bulwark/Spiky Shield), `Crafty Shield`, `move:
Electrify`, `move: Endure`, `move: Follow Me`, `Helping Hand`, `move: Magic Coat`,
`Mat Block`, `Powder`, `Quick Guard`, `move: Rage Powder`, `move: Shell Trap`,
`Snatch`, `move: Spotlight`, and `Wide Guard` lack a closed direct/indirect route
and remain **D2 with reachability/sufficiency review pending**; lack of direct
entry does not require removing safe raw support. `Max Guard` and the tagged
`move: Follow Me|[zeffect]` are retained compatibility raw forms with **D4
format exclusions** for their Dynamax/Z source routes. Helping Hand's active
`[of]` grammar remains accepted. The exact current source line table remains in
PIPE; it is not rewritten here.

For disposition granularity, **R03-P** is the public in-format/route-pending
`-singleturn` template set and is D2; **R03-X** is only `Max Guard` and
`move: Follow Me|[zeffect]` and is D4 for their format routes. R03 is the
62-token counting row; R03-P/R03-X are the disjoint per-template decisions.


All **32 raw-only condition IDs** are covered below: the 17 original
`condition_inventory` rows plus 15 raw-only `effect_discovery.additional_entries`
rows. Their source classification is accepted; **episode sufficiency is pending
where indicated**, not assumed from the word raw-only.

| Raw effect ID / exact IDs | Source and reachability evidence | Required disposition, O/B/A/T/E and focused evidence |
|---|---|---|
| R10 `choicelock`, `flinch`, `lockedmove`, `mustrecharge`, `stall`, `trapped`, `trapper`, `twoturnmove` | MAN `condition_semantics.internal_effect`, `data/conditions.ts`, `Pokemon.volatiles/statusState`; nested item Fling also supplies flinch. Relevant singles request/outcome effects; precise internal state private. | **D2, PRIVATE + RAW for emitted consequences.** No hidden lock/trap/duration in O/B. A comes from request; natural hidden-trap rejection accepted. CE-03/04A/08 verify no stale typed presence or missing public record and deterministic terminal progression. |
| R11 `futuremove`, `healreplacement`, `healingwish`, `lunardance`, `revivalblessing`, `wish` | MAN slot/condition source refs; latter four `Moves.<id>.slotCondition/condition`, `Side.slotConditions`. Wish/Healing Wish/Revival direct; others require route closure. | **D2, PRIVATE/RAW**, C23 and C25 apply. Public delayed damage/heal and owned request are captured; no pending-slot forecast required. CE-04G/05C verify consequence/restoration/terminal and private HP separation. |
| R12 `bounce`, `dig`, `dive`, `echoedvoice`, `fly`, `phantomforce`, `pursuit`, `shadowforce`, `skydrop` | MAN additional entries `Moves.<id>.condition`, `data/moves.ts`; package source does not prove every move reachable. | **D2, RAW/PRIVATE**; indirect reachability C12/16. CE-03 classifies generated/called routes; CE-04/08 checks existing typed state and legal requests through charging, interruption, return and terminal. No typed altitude/two-turn/echo counter required. |
| R13 `magicbounce`, `rebound` | MAN `Ability.condition`, `Abilities.magicbounce/rebound`; Magic Bounce candidate + reflection source path accepted, Rebound package-only unresolved. | **D2, RAW/PRIVATE**; no hidden callback state. CE-03 handles Rebound route, CE-04F validates reflection/copy outputs and active source/privacy. |
| R14 `arceus`, `gem`, `rolloutstorage`, `silvally` | MAN internal conditions, `Conditions.<id>`; presence in Gen 9 registry not generator proof. | **D2, RAW/PRIVATE**; retain only public consequences. CE-03 source/generator branches classify reachability; no plate/memory/roll counter model required. |
| R15 `commanded`, `commanding`, `dynamax` | MAN internal conditions; Commander is ally/multi-active, Dynamax package-only in format evidence. | **D4, format excluded.** Existing raw-only registry handling can remain without claiming singles mechanics. A rejects unsupported format/actions; no O/B/T/E field expansion. CE-03 ledger binds source guards. |
| R16 special `illusion` on `-end` | MAN special value, `Abilities.illusion.onEnd` emits `replace` then `-end Illusion`; both actor regressions and repair attestation in PIPE. | **D2, RAW, accepted/no further mechanic work.** `replace` handles O identity/stages; B earlier observations immutable; A own request; T retains exact end record; E ordinary lineage. Reuse accepted controls. |
| R17 special `raindance` on `-fieldend` | MAN fixture-only special value; no typed pseudo-weather removal. | **D3 reachability proof** under C04; existing RAW compatibility remains. No weather clearing inferred. |

The single accepted computed copy path is `Pokemon.copyVolatile` at
`sim/pokemon.ts:1281` for `dragoncheer`, `focusenergy`, `gmaxchistrike`,
`laserfocus`. Its **inventory/value classification needs no further action**;
public lifecycle correctness or reachability of copy recipients is separately
C17/C19. Do not merge it with the six unresolved callsites C10–C15.

### Stop, truncation and failure ledger

These rows enumerate every RUN result code and the associated lower-level
boundaries. All use STOP unless noted; source is RUN/INT/settling and their
accepted tests. Valid guard behavior is **accepted and retained**, not a new
mechanic backlog. CE-08B verifies classification against the completed envelope.

| ID / code(s) | Reachability/current behavior | Disposition and completion consequence / focused evidence |
|---|---|---|
| S01 `episode/v1/unsupported-format` | Explicit non-`gen9randombattle` option. | **D4.** Truncated with no cross-format support; retain existing test. |
| S02 `episode/v1/unsupported-protocol` with unresolved-alias/unsupported-record/unsupported-observable cause | Current unknown tokens and six recognized stops; C01–C16/29 distinguish reachable from unproven. | **D1 for present reachable causes**, D3 proofs in their owning rows. Preserve guard/rollback; remove only specifically closed valid stop paths. No blanket allowlist. |
| S03 `episode/v1/unsupported-boundary` | `actingPlayers` returns null at waiting/requestless or incompatible states. | **D3 source-proven no-route** under accepted C26/B26 for stable nonterminal requestless/wait-only pairs; keep the synthetic guard control and accepted reachable-pair implementation. Never synthesize waiting-side actions. |
| S04 `episode/v1/unsupported-revival-blessing`; `seeded-forced-switch/v1/unsupported-revival-blessing`, `seeded-revival/v1/unsupported-request` | Selection guards outside bounded bench revival. | **D3 source-proven excluded variants** under accepted C25/B23–B25; bounded bench revival and consecutive selections remain supported; multi-active is D4. Keep selection guards for excluded request shapes. |
| S05 `episode/v1/cancelled` | Caller abort at committed boundary; terminal tested first. | **D1 retain accepted control**, no blocker to implementation completeness. Aborted episode stays incomplete; returned prefixes/lineage intact. CE-08B validates initial/after-commit cancellation and terminal precedence. |
| S06 `episode/v1/transition-budget`, `episode/v1/attempt-budget`, `episode/v1/rejection-limit` | Default limits 256 transitions/512 attempts/3 rejections at one boundary; reset after commit. These can truncate valid battles. | **D1 retain accepted bounded controls**, no obligation to remove budgets. A budgeted result is never true; tests may choose sufficient finite limits for source probes. Preserve accounting and terminal precedence. |
| S07 `episode/v1/action-exhausted` | Every current request-derived tuple rejected; hidden trap may reject a seemingly legal action. | **D1 retain accepted rejection handling**, but CE-05/08 must show a valid supported boundary is not exhausted by an adapter defect. No duplicate retries/fake defaults; immutable rejected prefix and next valid control. |
| S08 `episode/v1/invalid-options`; invalid policy order | Invalid/unknown limits, policy lacks version, or action_order isn't a legal-index permutation; invalid policy order falls to execution-failed. | **D1 retain accepted guard**, no faithful blocker. No valid episode claimed; counts/origin preserved where available. |
| S09 `episode/v1/settling-failed` | `SettlingError`: deadline/message exhaustion, EOF without settled boundary, transport/cancellation/error. Synchronous simulator calls cannot be preempted. | **D1 retain accepted guard**, plus CE-08B diagnostic propagation. Valid source record rejected during extraction must remain identifiable (C09); no swallowed late terminal or sticky-error reset. No runtime redesign required. |
| S10 `episode/v1/execution-failed`, `episode/v1/evidence-invalid` | Malformed grammar, invalid-terminal, initialization/projection/publication validation, no legal actions, policy errors and uncaught execution failure. | **D1 retain guard**, CE-02/05/08 closes valid-source causes. Corrupt evidence stays failure, not supported-mechanic truncation; no successor emitted. |
| S11 `episode/v1/cleanup-failed` | Session.close throws; already committed records remain valid but result becomes failed. | **D1 retain accepted guard.** CE-08B verifies cleanup after win/cancel/error, immutable records and incomplete result. |
| S12 `episode/v1/terminal`, `status: completed` | Both terminated views agree on winner/tie and boundary is terminal. | **D1 envelope/acceptance work C27–28**; current guard accepted. Win/tie alone cannot imply faithful coverage or full origin. |

Unsupported stop versus malformed failure must remain distinguishable without
parsing away the original cause. This audit does not assert every effect-value
rejection currently arrives through the same exception class; C09/CE-08B owns
that targeted diagnostic check.

### Accepted work needing no further implementation

| ID | Evidence and current disposition | Scope preserved |
|---|---|---|
| A01 | **D1 completed:** SCH B-01 empty-record bypass removed in current `projectPipelineProtocolPrefix`; tests cover `''`, LF and CRLF segments. B-08 Python `_prefix` now requires canonical request JSON and joins retained `rqid` to the associated request; rehashed regression exists. | Historical audit remains unchanged. Reuse `pipeline_integration.test.ts` and `test_pipeline_record.py` focused controls; no duplicate repair. |
| A02 | **D1 completed:** B-03 unknown/family-mismatched effect validation, 002A nested inventory, 002B format/config/generator trace, accepted computed copy loop. | Scanner/value closure accepted; six remaining computed semantic closures stay C10–C15. No new digest attestation here. |
| A03 | **D1 completed:** protocol loader, terminal actor spelling, Helping Hand active `[of]`, signed setboost, filters/private-request normalization and rollback matrix. | Signed Contrary/Belly Drum constructed probe proves syntax only; its generated combination reachability remains CE-03 proof work, not a need to reimplement setboost. |
| A04 | **D1 completed:** ordinary lifecycle, Shed Tail Substitute-only transfer, Illusion/reveal/Tera re-entry and faint handling, Soak/third-type composition, ordinary Transform types/stages, v2 stages/selective clearing/Psych Up/base Topsy-Turvy. | C17–22 cover only additional reachable behavior; do not replay historical blocked states as current defects. Stellar defensive evidence must be used within its recorded review scope; private offensive counters remain deferred. |
| A05 | **D1 completed:** scoped settling, actor-only ordinary forced-switch, bounded bench Revival, bounded episode controller, 003 privacy fixture and 004A/B ordinary v2 publication. | Broader v2 end-to-end paths and episode payload completeness remain C24–28. Existing DATA-001 actor-only rows are preserved. |
| A06 | **D1 completed for recorded macOS profiles:** ENV-001B install/build/record bridge and ENV-001C1 trainer/live profile. | No rerun/install in this audit; no Windows/universal support inferred. Exact final changed-source validation remains CE-08, not a new environment project. |

## Ordered implementation backlog

**Objective:** prove one complete `gen9randombattle` episode artifact can be
validated from its initial request to win/tie for both players, with no
unclassified reachable format output/request shape and no false typed state.
No frontend slice is needed. Suggested ownership is simulator/backend for
capture, shared TS/Python contract ownership for publication, and QA/source
review for reachability and final acceptance.

Priorities: **P0** blocks the future faithful-episode claim; **P1** improves a
separate feature/data/product milestone; **Stretch** is outside this format.
Implement only where focused evidence shows a gap. Reuse accepted tests and
contracts. Source/generator proofs are deliverables, not an invitation to model
every mechanic. A D3 proof that fails must produce a small new D1/D2 child slice
before the final gate closes; do not bury it inside a catch-all implementation.

Contract shorthand: **PRO** shared protocol contract and simulator coverage;
**OBS** ObservableBattleState v2; **BEL** BeliefState lineage/privacy;
**ACT** CanonicalAction/CanonicalRevival; **TRANS** SeededTransition/forced-switch/
revival; **PIPE** pipeline integration and episode envelope; **DATA** DATA-001
publication joins. References remain in SPEC and COV.

| Order / slice | Priority / owner / scope | Dependencies | Completion criteria and affected contracts | Focused validation / demo value |
|---|---|---|---|---|
| 1. **CE-01A — Destiny Bond raw boundary** | P0 shared/backend; only C01 Destiny Bond exact form. | Accepted current grammar/scanner foundations. | Accept `-singlemove` only for active actor + exact `Destiny Bond`; preserve raw and reject every other unenabled form; no typed volatile/counter. PRO/OBS/PIPE/DATA. | Source-generated p1/p2 use crosses current stop, restores and publishes; follow move/faint/outcome and prefix/hash; unknown label, side-only actor, extra tags/fields fail with rollback and no Python output. |
| 2. **CE-01B — Glaive Rush raw boundary** | P0 shared/backend; only exact Glaive Rush plus final `[silent]`. | CE-01A token/rule capability. | Retain source form; no persistent typed glaiverush assertion/multiplier. PRO/OBS/PIPE/DATA. | Both actors, next-action expiry/faint, legal request and deterministic successor; malformed/missing/reordered tag controls. |
| 3. **CE-02A — Classification and field map reconciliation** | P0 shared; C07 metadata and field/source role matrix for current format. | None; can run after 01A without waiting for 01B. | Resolve six raw/v2 exceptions and move-target prose; enumerate loose typed value/suffix shapes needing 02B. PRO/OBS. | Exact matrix matches validators/projection; legacy IDs unchanged; no new mechanics. |
| 4. **CE-02B — Reachable grammar closure** | P0 shared; C06 in small families: HP tags first, then stage tags, then remaining typed/open suffix fields. | CE-02A; CE-03 discoveries add only affected families. | For each reachable family, source-required order/dependencies/value roles accepted; malformed variants rejected; harmless opaque raw suffix policy explicit. PRO/OBS/DATA. | Source records and fully rehashed TS/Python negatives, p1/p2, input/successor; no rewrite/repair. Split each family into a separate reviewable change. |
| 5. **CE-02C — Audience and diagnostic routing** | P0 backend/shared; C08 and diagnostic/private edges in C29. | Current stream contracts; independent of 01B. | Each public/split/request/error/debug/team channel has a source-bound route and no private propagation. OBS/BEL/PIPE/PRO/DATA. | Distinct private payloads for both sides, hidden-truth perturbation, error rejection, shared-prefix comparison. |
| 6. **CE-02D — Public long-battle warning** | P0 shared/backend; C28 `bigerror` auto-tie warning only. | CE-02C audience evidence. | Source-shaped public warning preserved raw; EV warning separately dispositioned; unknown/private diagnostic text cannot become a broad bypass. PRO/PIPE/DATA. | Pinned turn-limit warning through final tie, both prefixes, source-shape tamper rejection. No global diagnostics allowlist. |
| 7. **CE-03A — Generator-to-output closure ledger** | P0 QA/source/backend; C12–14/16 direct candidates, item selectors and format guards. | Accepted 002A/B reused. | Every generated move/ability/item branch maps to existing output/request family or a precise follow-up; no “unknown but digest protected” accepted as semantic closure. PRO coverage. | Read/source probes bind pruning, called moves and item selection to format; generated witness for 01A/B; candidate membership labelled separately from realizability. |
| 8. **CE-03B — Indirect and no-route proofs** | P0 QA/source; C02–05/10–16/19/25–26/29–30 and R03/R06/R12–17. | CE-03A, current computed inventory. | Close six computed callsites; prove finite argument sets/allowed shapes; disposition all parser/emitter differences, copy/reflection/call/linked paths and explicitly named absent-direct candidates, including Contrary+Belly Drum. PRO/OBS/ACT. | One source-grounded proof or emitting control per path; absence in samples insufficient. Newly reachable missing form becomes a narrow blocker with its own validation. |
| 9. **CE-04A — Public volatile boundary truth** | P0 backend/shared; C17, C10/15 and relevant R10. | CE-03A/B; 01A/B supplies raw one-move events. | Every reachable currently typed presence/reset is true or explicitly unknown/partial at capture boundaries; hidden counters omitted. OBS/BEL/PRO. | Start/end/reapply, silent copy/removal, switch/drag/faint/re-entry and restore; compare source-authorized public facts, no simulator-private export. |
| 10. **CE-04B — Roost boundary typing** | P0 backend/shared; C18, Roost alone first. | CE-03; accepted type composition. | **Implementation checkpoint unreviewed:** source proves residual expiry before any capturable boundary; Roost stays raw-only and existing public defensive types remain authoritative. Reflect Type only if reachable. OBS/PRO. | Both sides, ordinary dual-Flying + generated Empoleon Tera-Flying, same-turn suffix immutability/restored v2/Python publication; switch/drag/faint source order and typeadd/Transform/Illusion exclusions recorded. No offense feature. |
| 11. **CE-04C — Reachable stage transfers** | Source/evidence closure; no production implementation slice. | CE-03B and CE-04A, with accepted v2 stage work reused. | Complete the C19 generator/callback/copy/clear/pass matrix; establish whether any reachable public stage is missing or incorrect. OBS/PRO/DATA. | Source proofs plus generated Haze, Clear Smog, Mirror Armor, Contrary, Imposter and Belly Drum witnesses; both sides, exact boundaries and Python publication. Recommendation: accept source/evidence closure; no generic transfer model or private crit state. |
| 12a. **CE-04D — Side layers** | P0 backend/shared; C20, stackable hazards first, nonstacking screens/swap separately. | CE-03 and relevant 02B grammar. | Existing count-map semantics correct for capped starts, expiry and removal. OBS/PRO. | Capped repeat layers, expiry and swapped sides; mirrored restoration and terminal continuation. |
| 12b. **CE-04E — Field state** | P0 backend/shared; C21, one weather/terrain/pseudo-weather family per review. | CE-03 and relevant 02B grammar. | Public ID and suppression/removal distinction correct; private timers omitted. OBS/PRO/BEL. | Set/replace/clear/upkeep, suppression and restored boundaries; raw evidence/privacy and terminal continuation. |
| 12c. **CE-04F — Ability/item/status** | P0 backend/shared; C22, one output-shape family per review. | CE-03 and 02B/C grammar/audience. | Reveal/end/change/suppress/restore values true without exposing unrevealed loadout or counters. OBS/PRO/BEL. | Mirrored source reveal/suppression/cure/reapply, hidden-truth perturbation and deterministic restored continuation. |
| 12d. **CE-04G — Slot consequences** | P0 backend/shared; C23, Wish first, remaining differing slot consequences separately. | CE-03 and 02B/C; 05C informs only revival-specific scope. | Public delayed consequences captured and existing HP/status correct; raw-only slot state meets RAW conditions. OBS/PRO/PIPE. | Delayed heal/damage, consumption/cancellation, split HP, switch/faint/terminal and restored continuation. |
| 13. **CE-05A — v2 forced-switch path** | P0 backend/QA; C24 ordinary + chained hazard replacements. | Accepted forced-switch execution, relevant 04 correctness. | Both actors' v2 successors and Python actor records validate through resumed joint play; production unchanged if already correct. ACT/TRANS/OBS/BEL/PIPE/DATA. | Mirror p1/p2 KO/U-turn, consecutive hazard KOs, simultaneous replacements, rollback and deterministic replay. |
| 14a. **CE-05B — Request-state boundary proof** | P0 backend/QA; C26, one implementation per demonstrated stable-state gap. | CE-03B, CE-05A, accepted settling. | Every stable request-state pair classified; waiting/requestless never fabricates choices; transient stream gaps never published as decisions. ACT/TRANS/OBS/BEL/PIPE. | Initial/turn/switch/terminal source traces, consumed request restoration, no-legal-action diagnostics and unsupported pair no-route proofs. |
| 14b. **CE-05C — Revival variant proof/closure** | P0 backend/QA; C25, each singles variant independently. | CE-03B, CE-05A, accepted bounded revival. | Each active-target/active-or-fainted-reviver/simultaneous-selection variant has no-route proof or correct supported execution; multi-active excluded. ACT/TRANS/OBS/BEL/PIPE/DATA. | Source request-generation traces and any reachable variant's actor slot/roster binding, rollback, both successor privacy, restore and Python validation. |
| 15. **CE-06A — Complete two-perspective envelope** | P0 shared/backend; C27 origin and per-boundary evidence retention. | CE-05 shape inventory; may design against accepted current shapes earlier. | Version/add episode evidence or immutable payload references; initial owned requests and every committed successor for both sides retained, actor-only DATA rows unchanged. PIPE/OBS/BEL/TRANS/DATA. | Independently reconstruct both sequences, no missing waiting-side evidence, no raw snapshot/seed leak; reject gap/reorder/duplicate/prefix mutation and forged origin. |
| 16. **CE-06B — Segment/terminal closure** | P0 shared/backend; C27–28. | CE-06A, CE-02D, CE-05. | Resumed segment cannot claim initial-to-terminal alone; bind concatenation or label segment incomplete; full final win/tie/no-action payload captured. PIPE/OBS/BEL/DATA. | Resumed chain vs continuous run, zero-transition terminal segment, win/tie and final delivery, requestless terminal, final outcome tamper rejection. |
| 17a. **CE-08A — Complete-episode evidence** | P0 QA/shared; FCE-01–FCE-07 positive closure suite. | All P0 semantic/proof rows and 06B. | Both-perspective v2 suite passes from initial request to terminal with zero unresolved reachable stop/false-state/privacy defects; every raw/proof/exclusion row evidenced. All affected contracts. | Source-backed family witnesses plus generated-team episodes, win/tie/long-battle, restore/replay and Python validation under recorded macOS simulator-record profile. |
| 17b. **CE-08B — Stops and final review packet** | P0 QA/shared; S01–S12 and FCE-08. | CE-08A; retain accepted negative controls throughout earlier work. | All incomplete/error classifications preserve their boundary and cannot claim complete; exact source/runtime evidence ready for separate review, no automatic promotion. PIPE/OBS/BEL/TRANS/DATA/PRO. | Tampered/rehashed, cancelled, budgeted, unsupported, malformed, exhausted, settling and cleanup cases; terminal precedence and origin falsification. Record focused results and source identities. |

The dependency spine is **01A → 01B; 02/03 → relevant 04 families → 05 → 06 →
08**. Grammar/privacy and reachability tracks can proceed independently where
file ownership permits. 04D–G and 05B–C are explicitly separate reviewable slices,
not one broad “finish all mechanics” change. Source proofs may eliminate
conditional implementation; they cannot eliminate evidence obligations.

### First next slice

**CE-01A — source-shaped Destiny Bond `-singlemove` raw evidence** is the single
smallest next implementation slice. It removes one concrete valid candidate stop
using the existing raw-prefix architecture. It changes only the shared token/rule
contract, validators/coverage mapping needed to recognize this one template, and
focused cross-runtime/rollback/source controls. It must preserve raw-only state,
current privacy, all unenabled `-singlemove` rejections, and
`faithful_complete_episode:false`.

Destiny Bond alone is independently reviewable; Glaive Rush's extra `[silent]`
template is CE-01B, not a hidden expansion of CE-01A. A full move lifecycle model,
feature definition, Grudge/Rage support and complete-episode attestation are not
prerequisites for the first slice. Demonstrate the move through a pinned
source-generated control; additionally record a generated-set witness or source
selection proof because candidate membership alone is not a generation proof.

## Measurable faithful-episode acceptance

| Gate | Required evidence before a future true claim |
|---|---|
| FCE-01 Format closure | Every current inventory entry has a completed disposition, source identity and focused evidence; **zero unresolved reachable** output/request shapes, computed-value paths, unsupported mechanics or false typed-state cases. D3 proofs include indirect routes. Other formats stay excluded. |
| FCE-02 Origin and coverage | Full p1/p2 initial v2 observation + owned request through terminal, all committed boundaries and exact prefix extensions, no missing waiting-side payload, validated resume-origin chain. Zero unmatched/duplicate commits or unexplained cursor gaps. |
| FCE-03 Privacy and causality | Mirrored private-data/hidden-truth perturbations and same-turn future suffix tests pass for all affected boundary families; zero foreign private requests, split-private HP, unrevealed sets, hidden counters, seeds or snapshots in public/player-ineligible fields. |
| FCE-04 Truthful state and raw sufficiency | Every retained raw family satisfies the six RAW conditions; every existing typed assertion has source-backed boundary semantics. Unknown differs from absence. No requirement for a feature-complete simulator model. |
| FCE-05 Actions and transitions | Every reachable stable request pair either executes correctly or has a supported-format no-route proof; no fake waiting/requestless choices. Restoration reproduces request IDs, exact prefixes, observations/beliefs and transition identity; invalid candidates leave committed state byte/identity equivalent. |
| FCE-06 Cross-runtime validation | Both runtimes accept valid full v2 evidence and reject rehashed privacy, grammar, stage, cursor, identity, origin, prefix and outcome tampering without repair/output. Actor-only decision records and nonactor evidence remain distinct. |
| FCE-07 Terminal and incompleteness | Source-derived normal win, tie/simultaneous outcome and turn-limit tie paths retain final evidence and agree across both perspectives. Segment-only, budget/cancel/reject/unsupported/malformed/settling/cleanup failures cannot report faithful complete. Terminal precedence and resource release remain verified. |
| FCE-08 Review and reproducibility | Focused implementation/source review of closed rows with exact pinned simulator/config/local identities and the recorded macOS simulator-record validation profile. No stale attestation is repurposed. A separate authorized acceptance/promotion is required; this document does not change any flag. |

Generated examples are not a statistical proof of format closure. Completion is
measured by the source-bound output/request inventory plus focused positive and
negative witnesses, not a target number of random episodes or a success
percentage. Private mechanics can stay private; diagnostic raw events can stay
raw. A terminal result that skipped a blocked family is insufficient evidence.

## Deferred milestones

| Item / disposition | Why it does not block this faithful-episode boundary | Separate dependency / acceptance |
|---|---|---|
| FEATURE-001, private counter/duration choices, offensive Stellar STAB/counters; MAN first unknown | **D4 for simulator-private fields in the player information regime; D2 for permitted public evidence.** RAW/PRIVATE effects; no legal/terminal model required because Showdown executes mechanics. | P1 feature schema, knownness, information regime and provenance decision. Public typing/stages correctness still C18–22. |
| Belief posterior, joint Randbats hypotheses, external catalogs, candidate-specific tactical reasoning | **D2 evidence-only; D4 hidden simulator-truth priors in player capture.** Keep accepted observation-bound belief lineage, no new posterior algorithm. | P1 source/version/checksum, contradiction/unknown-tail and privacy contract before prior/model work. |
| Dataset generation and replay imitation/outcome objectives | **D4 from this delivery scope.** No collection needed to validate simulator captures. Replay logs cannot supply complete original private requests/seed. | P1 feature/target eligibility, bounded collector, battle-disjoint splits, cursor/privacy checks and separately approved pilot. |
| Legacy two-type features, tactical/live consumers, v1 omission of public stages, `/evaluate` bounded log | **D4 from current v2 capture consumers.** Existing historical models are not input contracts; default v1 need not migrate. | P1 separate feature/live exact-cursor interface, three-type compatibility, inference/latency/security review. |
| New training, checkpoints, reward/objective and model promotion | **D4 from this delivery scope.** No typed-model coverage requirement sneaks into raw-capture closure. | P1 accepted data/features, frozen objective/config/seeds, held-out evaluation and model interface. Legacy checkpoints abandoned/nonblocking. |
| Windows clean recreation / ENV-001C2, broad Python range, CUDA/PyTorch | **D4 from macOS capture validation claim.** ENV-001 remains open overall; recorded macOS record profile already validated. | P1 platform-specific clean setup/proof before Windows/support-range claims. No environment/lock changes in this audit. |
| Replay fixtures and replay-specific parity | **D4 from simulator-only milestone.** Missing opt-in `.log` assets do not block current source-derived captures. | P1 replay eligibility/parity milestone; no download authorized. |
| Other generations/formats, doubles, constructed-team building, targeted/multi-active actions, custom mods | **D4.** MAN other-format grammar unknown intentionally remains unknown; no O/B/A/T/E implementation needed. | Stretch, separately scoped contracts and source coverage. Preserve format rejection. |

## Risks, verification and durable completion checkpoint

- **Raw-only is not a loophole for wrong typed state.** The largest residual
  uncertainty is whether an omitted/silent effect leaves an existing typed
  presence/type/stage/layer assertion false at a capturable boundary. CE-04
  resolves this family by family without requiring a universal model.
- **Source candidate is not generated witness.** Item selection, pruning,
  Transform/call/reflection and linked effects require finite source reasoning.
  Never infer unreachability merely because a random sample missed a mechanic.
- **Accepted history is narrower than aggregate readiness.** The old status and
  assessment next-step prose lags later accepted scanner, v2 and environment
  entries. This audit reconciles them without modifying their findings/digests.
- **Capture artifact versus decision dataset:** initial/final summaries and
  actor-only DATA rows are insufficient on their own for both-perspective
  complete-episode retention. CE-06 must provide verifiable payloads/references,
  not fabricate rows for nonacting players.

Suggested demonstration: initial p1/p2 v2 views → Destiny Bond/Glaive Rush raw
record retained → switch/revival boundary with only the actor's action → replay
of both evidence chains → matching terminal win/tie → tampered and interrupted
runs rejected or marked incomplete. No dataset or model demonstration is needed.

**Audit checkpoint (2026-10-01): CE-01 accepted after focused review.** The complete
raw/effect/emitter/stop inventories remain preserved above. CE-01 changes only
the shared `-singlemove` protocol boundary, its coverage classification,
focused implementation/tests, and the PIPELINE-002 checkpoint. The review
attested local digest `1a3a57ceaf5096b6a83b2466c13e01b6206ad04939409adb170ed4428e0affbd`;
it does not attest semantic episode acceptance. PIPELINE-002 remains unaccepted
and `faithful_complete_episode:false` remains required.

## CE-02 implementation source ledger (2026-10-01)

This ledger fixes the source boundary for the CE-02 implementation only. In
the grammar below, `<active>` is a public `p1a:`/`p2a:` Pokémon identifier,
`<side-or-active>` is a public `p1:`/`p2:` or active identifier, and `<hp>` is
the existing validated health condition. “Reachable” means an emitter is on the
pinned Gen 9 Random Battle source route; it does not assert generator closure.
It is not a coverage-digest attestation or a complete-episode acceptance.
Every tag kind listed in an ordered HP/heal/stage row is source-singleton: a
second instance of that kind is malformed even if its text differs.

| CE-02 family | Exact grammar, tag order, and identifier role | Pinned source file + symbol | Visibility and reachability | Raw/later lifecycle | Final CE-02 disposition |
|---|---|---|---|---|---|
| 02B HP — `-damage` | `|-damage|<active>|<hp>|tags`; optional tags occur only as `[from] <text>`, `[of] <side-or-active>`, `[partiallytrapped]`, `[silent]`, in exactly that order. | `sim/battle.ts`, `Battle.damage` (`2034–2060`) and `Battle.add`. | Public battle log; direct damage/recoil/residual emitters are in the pinned format route. | Typed public HP update; raw tags remain provenance. | Accepted only with this grammar; malformed/reordered tags stop before projection. |
| 02B HP — `-heal` | `|-heal|<active>|<hp>|tags`; optional tags occur only as `[from] <text>`, `[of] <side-or-active>`, `[wisher] <text>`, `[zeffect]`, `[silent]`, in exactly that order. | `sim/battle.ts`, `Battle.heal` (`2186–2203,2738`) and `BattleActions` healing paths. | Public battle log; direct healing paths are reachable. | Typed public HP update; raw tags remain provenance. | Accepted only with this grammar; malformed/reordered tags stop. |
| 02B HP — `-sethp` | `|-sethp|<active>|<hp>|tags`, where only `[from] <text>` then `[silent]` are permitted, in that order. | `sim/battle.ts`, `Battle.setHealth` / `Battle.add`. | Public battle log when source emits the health synchronization. | Typed public HP update; raw source annotation retained. | Accepted only with this grammar; no generic tag suffix bypass. |
| 02B stage — `-boost`, `-unboost`, `-setboost` | `|token|<active>|<stat>|<integer>|tags`; stat is one of the seven configured stage stats. `-boost`/`-unboost` use `0..12`; `-setboost` uses `-6..6`. Tags are `[from] <text>`, `[silent]`, `[zeffect]` in that exact order. | `sim/battle.ts`, `Battle.boost` (`1920–1955`) and `Battle.add`. | Public battle log; direct stage emitters are reachable. | Represented public stage lifecycle, with raw tags as provenance. | Accepted only in the bounded grammar and projected as represented state. |
| 02B stage — clear variants | `|-clearboost|<active>`, `|-clearallboost`, `|clearboost|<active>`, `|clearallboost`; `|-clearpositiveboost|<active>|<active>|move: <name>` has exactly those three payload fields and no tag suffix. | `sim/battle.ts`, `Battle.clearBoost` / `Battle.add`; `sim/battle-actions.ts`, `BattleActions` Spectral Thief branch (`790`). | Public battle log; ordinary/selective clear routes are reachable. | Represented public stage lifecycle. | Exact clear shapes are accepted; extra/reordered fields stop. |
| 02A C07 map — six former bare records | `boost`, `unboost`, `setboost`, `clearboost`, `clearallboost` use the bounded stage forms above; `transform` is `|-transform|<active>|<active>|[from] <text>?`. Both transform fields are active identifiers. | Stage: `sim/battle.ts`, `Battle.boost` / clear helpers. Transform: `sim/pokemon.ts`, `Pokemon.transformInto` (`1288–1290`). | Public when emitted; these direct source families are reachable in the pinned format. | All six are **represented**, not raw-only: stage records update public stages and transform updates public transform state. | C07 classification corrected to the active v2 projector; no broader copied/computed-state assertion. |
| 02C private request | `|request|<JSON>` is a side-addressed choice payload, not spectator grammar; no public identifier role exists. | `sim/side.ts`, `Side.emitRequest` (`475–478`); `sim/battle-stream.ts`, request receiver. | Private to its addressed side; reachable at every choice boundary. | Never enters public prefix, typed spectator state, or publication. | Fail closed at spectator ingest; the separate player-request path remains authoritative. |
| 02C private choice error | `|error|[Invalid/Unavailable choice] <text>` is a side-addressed diagnostic, not spectator grammar. | `sim/side.ts`, `Side.emitChoiceError` (`480–486`); `sim/battle-stream.ts`, error receiver. | Private to its addressed side; reachable after invalid choice input. | Never enters public prefix or later public lifecycle. | Fail closed before projection/publication. |
| 02C split transport | `|split|<side>` introduces secret/shared transport branches, rather than a public record grammar. | `sim/battle.ts`, `Battle.addSplit` (`3012–3020`); `sim/battle-stream.ts`, `extractChannelMessages` / spectator channel selection. | Per-side transport marker; reachable for split messages. | Never public evidence itself; only the source-selected shared payload may later be public. | Fail closed at public ingest and pipeline prefix. |
| 02C debug and team channels | `|debug|<text>` and `|showteam|<side>|<packed-team>` are diagnostics/team disclosure, not public grammar; team-preview request data is likewise private request payload. | `sim/battle.ts`, `Battle.debug`/`debugError` (`3079,3089`) and team sender (`3151`); `sim/side.ts`, `Side.emitRequest`. | Private/diagnostic or side-specific; source candidates exist, but public Gen 9 Random Battle route is not established. | Never public prefix, typed spectator state, or publication. | Fail closed. CE-03B owns any source-route/no-route proof; CE-02 does not allowlist either channel. |
| 02D `bigerror` auto-tie | Exact `|bigerror|You will auto-tie if the battle doesn't end in N turn(s) (on turn 1000).`; `N` is exactly `{1..10,20,30,40,50,60,70,80,90,100,200,300,400,500}` and only `1 turn` is singular. No identifier or tag fields. | `sim/battle.ts`, `Battle.maybeTriggerEndlessBattleClause` (`1757–1767`). | Public battle log; reachable on the source schedule: every 100 turns from 500, every 10 from 900, every turn from 990. | Raw-only public warning retained through projection; it does not mutate typed state or resolve terminal evidence. | Accepted only for this source-shaped warning. The EV-limit `bigerror` at `sim/battle.ts:1905` rejects. |
| Reachability candidates — `-singlemove` Grudge/Rage | Exact raw forms are `|-singlemove|<active>|Grudge` and `|-singlemove|<active>|Rage`, with no tag; no alternate identifier role or suffix is accepted. | `data/moves.ts`, `Moves.grudge.condition.onStart` and `Moves.rage.condition.onStart`; shared `validation_rules.singlemove.forms`. | Public if emitted, but current Gen 9 Random Battle generated-set/indirect reachability is unproven. | Raw-only provenance; no typed volatile or action lifecycle. | CE-02 preserves the CE-01 exact grammar without treating either candidate as closed. CE-03A/B remains fail-closed for reachability. |

CE-03A/B remains the fail-closed source/reachability proof track for computed,
indirect, compatibility, and no-route claims. This CE-02 change does not
attest a coverage digest or alter `faithful_complete_episode:false`.

### CE-02 spectator ingress audit (2026-10-01)

The ingress boundary is `appendPublicSpectatorChunk`, called by `listenSpectator`
before `logLines` accumulation. The table audits every CE-02 ledger command whose
audience is private or nonpublic; the shared raw contract's `request` grammar is
only for the separate addressed player path and is never spectator permission.

| Command | Allowed channel | Required spectator behavior |
|---|---|---|
| `request` | Addressed player stream only | Reject before candidate-log accumulation; retain the managed player request path. |
| `error` | Addressed player stream only | Reject before candidate-log accumulation. |
| `split` | Transport-side selection only | Reject before candidate-log accumulation; only the already-selected shared payload may be public. |
| `debug` | Diagnostic/private channel only | Reject before candidate-log accumulation. |
| `showteam` | Side-specific team channel only | Reject before candidate-log accumulation. |

Public controls remain accepted at ingress, including `|turn|1` and the exact
source-shaped auto-tie `|bigerror|...|` warning. This repair does not establish
any CE-03 route claim.

### CE-02 scoped review verdict (2026-10-01)

Accepted. Focused review confirmed the bounded ordered grammar, singleton-tag
cardinality, TypeScript/Python rejection parity, public-ingress boundary, exact
`bigerror` warning, and the raw-only, reachability-unproven Grudge/Rage
classification. The review attested local coverage digest
`8e9fa02026be4613695a3e0996ce27370fedf34e956d6f8753e6d7f87475b232`.
This scoped verdict does not accept PIPELINE-002, resolve CE-03 lifecycle or
reachability work, or change `faithful_complete_episode:false`.

### CE-02D source-backed implementation checkpoint (2026-10-06, unreviewed)

The initial source/contract/privacy/adversarial matrix and its completed
validation are recorded in the existing pipeline progress document. The pinned
`pokemon-showdown@0.11.10` `gen9randombattle` path was exercised from a
serialized turn-989 battle through the actual `Battle.endTurn` calls: the
`maybeTriggerEndlessBattleClause` warning is emitted at turns 990–999 with
values 10 through 1, then turn 1000 emits the turn-limit message and `|tie`.
The exact existing grammar remains bounded to the source schedule's finite
`N` values and singular `1 turn` form.

The other `bigerror` emitter is not operative on this route. Its
`checkEVBalance` call is behind `debugMode`; the operative format has no debug
flag and sim-core starts its battle stream without debug. Independently,
generated Gen 9 Random Battle sets initialize at 85 EVs in each stat and only
reduce values afterward, so generated teams cannot produce the over-510 side
imbalance. The exact EV diagnostic stays rejected; no general diagnostic
allowance was added.

The auto-tie record is emitted via ordinary unsplit `Battle.add` and reaches
spectator, p1, and p2 channels identically. It remains exact raw public-prefix
evidence only; it adds no typed state, belief, legal-action, or terminal
authority. A narrow ingress repair now validates `bigerror` with the existing
raw contract before public-prefix accumulation, and appends a chunk only after
all its lines validate. Private request/error/split/debug/showteam traffic
remains rejected. Actor-only DATA-001 rows are unchanged.

The restored source harness, both-perspective raw-prefix checks, raw-only state
invariant, fully rehashed TypeScript/Python controls, publication privacy
checks, and exact validation results are in the progress checkpoint. The
TypeScript protocol/source test and Python DATA-001 test were already included
in `local_coverage_sources.files`; the source list did not need expansion. The
updated local digest is `1813f333a918cdf81c2f754ed64b53d29eb77ca3c75f8de9d32d765b96042db2`;
`reviewed_sha256` remains the earlier CE-06A/coverage digest pending separate
semantic review. The synthetic coverage self-tests pass; the checker reports
the expected missing semantic-review binding. This checkpoint is ready for
attestation, not an attestation itself.

CE-02D does not validate terminal-envelope delivery or resumed-segment closure.
CE-06B and CE-08A remain dependent work; the turn-limit source trace does not
promote `faithful_complete_episode:false`.

### CE-02D scoped review verdict (2026-10-06): accepted

Independent review confirms the pinned `pokemon-showdown@0.11.10`
`gen9randombattle` emitter's exact public warning precedes the turn-1000
message and automatic tie. The separate EV warning has an explicit source-backed
no-route disposition: the only `checkEVBalance` caller is debug-gated, the
operative format/stream do not enable debug, and generated sets stay within
510 EVs. The warning remains raw-only and audience-safe; both public prefixes
retain it without typed-state changes, and actor-only DATA-001 output contains
neither the warning nor private/simulator payloads.

Hash-matched focused evidence covers the restored source-engine witness,
identity-consistent rehashed v1/v2 candidates across both perspectives and
input/successor prefixes, valid publication controls, malformed/EV/wrong-turn/
field-count/whitespace/tag rejection, TypeScript rollback, and Python exit 2
with empty stdout. The focused test sources are included in the coverage
manifest. The local coverage digest
`1813f333a918cdf81c2f754ed64b53d29eb77ca3c75f8de9d32d765b96042db2` is
attested for CE-02D only. No material findings remain. CE-06B terminal/segment
closure, PIPELINE-002, and complete-episode acceptance remain outside this
verdict; `faithful_complete_episode:false` remains required.

## CE-03A generator-to-output closure ledger (2026-10-01)

Scope is the direct Gen 9 Random Battle generator surface and the computed
`addVolatile` paths in C12–C16. Evidence labels are deliberately distinct:
**membership** means an authored set can supply an ID, **selection** means the
pinned generator can retain it under its source conditions, and **witness**
means a deterministic battle executed it. A sample never proves absence. The
coverage manifest binds the full sorted generated move/ability memberships,
finite direct move-origin values, and the `randomMoveset`, `getAbility`,
`getPriorityItem`, and `getItem` source slices plus the singles/doubles item
guard. A change fails closed until this ledger receives a new disposition.

| Direct path and pinned source | Finite values / membership; selection; realizability | Output or request family | O / B / A / T / E impact | CE-03A disposition |
|---|---|---|---|---|
| **C12** `Conditions.twoturnmove.onStart` `attacker.addVolatile(effect.id)` in `data/conditions.ts:290`; source move callbacks in `data/moves.ts` | Direct generated origins are finite: `meteorbeam`, `solarbeam` (their `onTryMove` adds `twoturnmove`). Membership is from `sets.json`; `RandomTeams.randomMoveset` selects only a retained movepool result. A charge guard is still required for a witness. Called/copy origins are not finite in this direct ledger. | Public `-prepare`, volatile `-start`/`-end`, move and HP records; no generator-time request record. | **O:** existing raw/volatile projection may see the public ID; **B:** provenance only; **A:** addressed request remains authoritative; **T:** exact public prefix only; **E:** no terminal rule. | Direct origins recorded; their lifecycle/output proof is **CE-03B**. Do not expose `lastMoveTargetLoc` or call targets. |
| **C13** `BattleActions` `pokemon.addVolatile(move.id)` at `sim/battle-actions.ts:264` | Finite direct values are `bloodmoon`, `gigatonhammer`; both are authored candidates (Ursaluna-Bloodmoon/Tinkaton). Membership does not prove selection; selection uses normal set/move pruning. A witness must repeat the selected move and pass the `cantusetwice` guard. | Public raw `-hint`/move evidence and later private request; no typed prohibition contract. | **O:** raw only; **B:** provenance only; **A:** request, not hint, gives legality; **T:** preserve the record; **E:** none. | **New narrow CE-03B blocker:** exact hint grammar plus repeated-use witness and restored request legality. |
| **C14** `BattleActions` `target.addVolatile(moveData.volatileStatus)` at `sim/battle-actions.ts:1250` | Finite direct candidate values: `curse`, `destinybond`, `disable`, `encore`, `leechseed`, `magnetrise`, `noretreat`, `partiallytrapped`, `protect`, `substitute`, `taunt`, `yawn`. A move must be selected, hit and survive immunity/target checks. Callback mutation of `moveData` is not bounded here. | Existing public `-start`/`-end`/`-activate`, HP/stage forms and addressed requests where source emits them. | **O:** represented IDs retain their existing projection; raw-only IDs remain raw; **B:** evidence only; **A:** request authoritative; **T/E:** later lifecycle and terminal truth remain separate. | **Already represented** only where current inventory says represented; every callback-mutated value is a **CE-03B** fail-closed dependency. |
| **C10/C11 and C15** computed `volatile` loops in `Moves.psychup.onHit`, `Abilities.costar.onStart`, `Pokemon.copyVolatile`; `linkedStatus` in `Pokemon.addVolatile` | Psych Up/Costar/copy have finite literal values `dragoncheer`, `focusenergy`, `gmaxchistrike`, `laserfocus`; Psych Up has no direct generated candidate and Costar's ally guard has no singles direct witness. `linkedStatus` has no finite local source value because it is caller-established. | Public stage/volatile/copy records if a route emits them; internal links may be silent. | **O:** existing represented values only; **B:** no hidden copied parameters; **A:** request authoritative; **T/E:** stale typed lifecycle could matter later. | Finite copy values remain **already represented** at the inventory level; route/no-route proof is **CE-03B**. `linkedStatus` stays **fail-closed CE-03B/CE-04**. |
| **C16 move selector** `RandomTeams.randomMoveset`, `randomSet`, `randomTeam` in `data/random-battles/gen9/teams.ts` and `sets.json` | 350 authored movepool IDs are digest-bound. `randomSet` applies role/Tera/team pruning and `randomMoveset` culls/enforces counters before sampling. A generated team is direct; any particular retained move needs source selection or a witness. | Team construction itself emits no protocol; `Battle`/`Side` later produce public setup (`player`, `teamsize`, `poke`, `switch`) and the owner-only initial `request`. | **O:** public setup and owner request are existing boundaries; **B:** no generator truth leak; **A:** initial request; **T:** CE-06 owns origin retention; **E:** none. | **Already represented** for accepted setup/request routing. Any unclassified callback output is a narrow CE-03B blocker, not an implied mechanic implementation. |
| **C16 ability selector** `RandomTeams.getAbility` / `shouldCullAbility` | 203 authored ability candidates are digest-bound. It filters viable set abilities, then samples allowed values or a fallback. Membership/selection do not establish activation or reveal. | No generator-time protocol record; later ability callbacks can emit public `-ability`, `-activate`, `-endability`, HP/stage, or private request consequences. | **O:** only public emitted evidence; **B:** unrevealed ability remains unknown; **A:** request authoritative; **T/E:** callback/lifecycle work later. | **CE-03B/CE-04 dependency.** Each direct callback output needs a row/proof; no ability gets typed by generator membership. |
| **C16 item selectors and format guard** `getPriorityItem`, `getItem`, `randomSet`; `config/formats.ts` `[Gen 9] Random Battle` | Items are selector outputs, not authored set members. Priority runs first; in the effective singles format `randomSet` calls `getItem`, while `getDoublesItem` is excluded by `if (isDoubles)`. Item result depends on retained moves, ability, role, species and team details. | No generator-time protocol record; later item callbacks can emit public `-item`, `-enditem`, `-activate`, HP/stage, or request consequences. | **O:** public reveal only; **B:** held item is private until emitted; **A:** request authoritative; **T/E:** callback/lifecycle later. | **CE-03B/CE-04 dependency.** Selector and guard drift fail closed; no broad item implementation is added. |
| **CE-01 witness obligations** `Moves.destinybond.condition.onStart`, `Moves.glaiverush.condition.onStart`; `sets.json`; `tests/singlemove.test.ts` | Membership: Destiny Bond (Qwilfish/Froslass) and Glaive Rush (Baxcalibur). Selection/witness: deterministic generated seeds `147` Froslass and `79` Baxcalibur are asserted, then each callback executes for p1 and p2. | Exact public raw `-singlemove`: `Destiny Bond`, and `Glaive Rush|[silent]`; later move/faint/win evidence is independently emitted. | **O:** raw record only; **B:** provenance only; **A:** request authoritative; **T:** prefix retained; **E:** terminal evidence remains separately represented. | **Already represented raw-only (CE-01).** This witness does not prove Grudge/Rage or indirect/copy reachability. |

The resulting direct output/request map is closed only at the source-routing
level: set membership, selector source, finite move values and item-format guard
are bound. It intentionally does not claim typed volatile expiry, copied/called
move closure, callback output semantics, initial-to-terminal envelope retention,
or any change to `faithful_complete_episode:false`.

### CE-03A child blockers

- **CE-03B-01:** source-shape and realize C13 `bloodmoon`/`gigatonhammer`
  repeat-use `-hint` evidence, then prove that raw-only handling cannot conflict
  with the following request.
- **CE-03B-02:** trace direct and indirect `twoturnmove` origins, including
  called/copy moves, and classify each public lifecycle record without leaking
  the simulator's target-location state.
- **CE-03B-03:** close callback mutation/call/reflection inputs to
  `moveData.volatileStatus`, and ability/item callback output families. A newly
  discovered record is a narrow grammar/semantic blocker, never a generic
  allowlist expansion.
- **CE-04:** after routes are closed, prove lifecycle truth for any retained
  typed volatile/field/stage assertion. Raw evidence cannot hide stale typed
  state.

**CE-03A implementation checkpoint (2026-10-01):**
`check-simulator-coverage.cjs` now fails on generated move/ability membership,
finite direct move values, selector source, or singles/doubles guard drift;
its self-test contains synthetic mutations for each case. The manifest includes
the checker and `tests/simulator_coverage.test.ts` in local coverage hashing.
The local digest is intentionally **unreviewed**:
`3adb4789cb87e6a8750af0e8fefa9d424e40ee25b61a870e1c54ca5fbf1be774`.

### CE-03A scoped review verdict (2026-10-01)

Accepted. Focused review confirmed the direct C12–C16 inventory, finite
generated values, selector and singles-item guard evidence, distinct
membership/selection/witness claims, and fail-closed scanner coverage. It
attested local coverage digest
`3adb4789cb87e6a8750af0e8fefa9d424e40ee25b61a870e1c54ca5fbf1be774`.
This verdict does not close CE-03B/CE-04, accept PIPELINE-002, or change
`faithful_complete_episode:false`.

## CE-03B source-proof closure matrix (2026-10-01)

**Evidence checkpoint; not a semantic acceptance.** This matrix dispositions
C02–05/C10–16/C19/C25–26/C29–30 and R03/R06/R12–17, with R01/R07/R09–11
cross-references for their dependent output/request routes. It supersedes the
earlier *unproven reachability* labels only for the source proofs below. It
does not widen any validator, change an inventory classification, close a
typed lifecycle gap, or change `faithful_complete_episode:false`.

All source paths below are relative to the installed pinned
`sim-core/node_modules/pokemon-showdown/`. **SP** means a source proof over the
operative generator and engine; **W** means the stated deterministic local
witness; **U** means a named proof still missing. An upper bound is sufficient
to exclude values outside it, but membership in that bound alone does not
prove selection or execution. No random sample is used as absence evidence.
The supported origin is `Battle.getTeam` without caller-supplied teams,
`Teams.getGenerator`/`RandomTeams.randomTeam`, the unmodified format/rules and
ordinary player choices. Constructed callback fixtures, arbitrary serialized
state edits, custom teams, and administrative `eval` are not generated-origin
proofs. Controlled witnesses below explicitly say where generated sets were
reassembled; they are not full generated-episode acceptance.

### Closed access domains and guards

- **M (moves):** normalize every `sets.json[*].sets[*].movepool` with
  `Dex.toID`: 350 IDs. `RandomTeams.randomSet/randomMoveset` selects only those
  retained pools. The only generated `callsMove` entry is **Sleep Talk**;
  its `onHit` samples the user's existing `moveSlots`, rejecting
  `nosleeptalk`, `charge`, Z and Max forms. Transform/Imposter copies an
  existing opponent's slots, not its learnset. Magic Bounce recreates the
  incoming `move.id` only; Dancer reuses the completed dance `move.id` only;
  Encore and `lockedmove`/`twoturnmove` select a previously available ID.
  These operations do not add a new move seed. `Pokemon.getMoveRequestData`
  and `Side.chooseMove` add **Struggle**, giving a 351-ID move upper bound;
  the **recharge** request is a control action stopped by
  `Conditions.mustrecharge.onBeforeMove`, not a new callable move family.
  The only initial slot rewrite, `Battle.runAction('start')`'s Crowned
  Iron Head substitution, cannot add Behemoth Bash here: Zamazenta-Crowned's
  authored pool has no Iron Head, ordinary Zamazenta is not given Rusted
  Shield, and the rewrite runs before item transfer. Behemoth Blade is
  already in M. No operative Gen 9 script overrides this graph
  (`data/scripts.ts` is `gen:9`).
- **No unseeded caller/copy route:** Assist, Copycat, Me First, Metronome,
  Mirror Move, Nature Power, Instruct, Mimic, Sketch, Snatch and Magic Coat
  are outside M. Their base callbacks respectively read an existing party
  slot, last/queued move, the registry, or a target slot; invoking those
  callbacks first requires their own unavailable move. The sole registry
  expander, `Moves.metronome.onHit`, therefore has no entry route. Instruct
  can target an enemy in singles, so its exclusion relies on this graph,
  not an incorrect ally-only claim. Dancer's generated Oricorio ability,
  Magic Bounce, Transform/Imposter and Encore are included in the induction;
  copying a move already copied/reflected/called does not escape M.
- **A (abilities):** 203 normalized authored candidates, filtered by
  `getAbility/shouldCullAbility`. Its singles hardcodes return abilities
  already in that bound. `Pokemon.formeChange` additionally binds the six
  reachable form-default abilities **Tera Shell, Teraform Zero, and all four
  Embody Aspect forms** (Terapagos and Ogerpon), yielding a conservative
  209-ID bound. Other reachable permanent/default changes (Shaymin,
  Palafin, Crowned forms; Disguise/Ice Face's special handling) remain in A.
  Trace reads an adjacent foe's current ability (`notrace`/`noability` and
  Ability Shield guards); Transform copies the target's current ability;
  clear/switch restores a previously bound base ability. Skill Swap,
  Entrainment, Role Play, Doodle, Simple Beam, Worry Seed and Gastro Acid
  have no move seed. Mummy, Lingering Aroma, Wandering Spirit, Receiver,
  Power of Alchemy, Rebound, Costar, Commander, Symbiosis and Pickup have
  neither an initial nor a form-default seed. Thus copying cannot introduce
  them. This bound does not assert that every authored ability is selected,
  revealed, or copied; copy/suppression flags remain authoritative.
- **I (items):** `getPriorityItem` then the singles `getItem`, plus the
  authored species' required-item choices, form a finite source upper bound.
  Arceus selects only `requiredItems[0]` (Plate, never the listed Z crystal);
  `getDoublesItem` and the `isDoubles` Clear Amulet branch are excluded.
  The following **66-ID conservative selector bound** includes the five
  Gluttony berry alternatives even though Gluttony has no A seed; those five
  branches are therefore unreachable. An empty item is also possible.
  Membership is not a witness that each remaining item is selected:

  `adamantcrystal, aguavberry, airballoon, assaultvest, boosterenergy,
  chestoberry, choiceband, choicescarf, choicespecs, cornerstonemask,
  custapberry, dracoplate, dreadplate, earthplate, eviolite, figyberry,
  fistplate, flameorb, flameplate, focussash, griseouscore, hearthflamemask,
  heavydutyboots, iapapaberry, icicleplate, insectplate, ironplate, leftovers,
  leppaberry, lifeorb, lightball, lightclay, loadeddice, lumberry,
  lustrousglobe, lustrousorb, magnet, magoberry, meadowplate, mindplate,
  passhoberry, pixieplate, powerherb, rindoberry, rockyhelmet, rustedshield,
  rustedsword, salacberry, scopelens, silkscarf, silverpowder, sitrusberry,
  skyplate, souldew, splashplate, spookyplate, stoneplate, throatspray,
  toxicorb, toxicplate, weaknesspolicy, wellspringmask, whiteherb, widelens,
  wikiberry, zapplate`.

  Trick/Switcheroo, Magician and Pickpocket transfer an existing held item
  subject to `takeItem`/`TakeItem` and empty-slot guards; Harvest restores
  `lastItem` only when it is a Berry and the weather/chance guard succeeds;
  Cud Chew reuses an eaten Berry object. They cannot synthesize an item
  outside I. Recycle/Fling/Bestow/Pluck have no M seed; Bug Bite is in M but
  consumes the existing target Berry. No selected item supplies a move or
  ability seed. Held items and item-selection inputs remain private until a
  valid source record reveals them.

The item source branches are explicitly bounded by species/required item;
role/counters (AV/Choice/setup/priority/recovery); current moves (Belly Drum,
Substitute, Trick/Switcheroo, screens, Rest, Meteor Beam, Nuzzle); ability
(Imposter, Magic Guard, Sheer Force, Guts, Unburden, Protosynthesis/Quark Drive,
Anger Shell); lead/team weather/Tera and species typing. They are the exact
`getPriorityItem/getItem` predicates already source-bound by CE-03A, not new
inferences from observed item frequencies. `randomTeam`'s PotD override still
calls the same `randomSet`; the pinned `config/config.js` has `potd = ''`.
An absent random-set key would fail construction, not supply a new move pool.

### Proof matrix

Every row inherits the O/B/A/T/E discipline from the earlier effect profiles:
only public emitted facts can change O/B; addressed requests alone authorize
A; T retains exact ordered public evidence and owned request lineage; E uses
independent terminal output. Private conditions, copied parameters, targets,
item truth and counters are never exported by this evidence task.

| Proof / assigned rows | Source chain and guards, including indirect access | Reachability / evidence | Output and disposition |
|---|---|---|---|
| **B01 — Grudge/Rage (C02)** | `Moves.grudge.volatileStatus → condition.onStart` and `Moves.rage.self.volatileStatus → condition.onStart` (`data/moves.ts`). Neither is in M; Sleep Talk/Transform/reflection/Dancer/Encore cannot introduce a seed; Metronome and other expanders have no entry. `Past` is descriptive only. | **Source-proven unreachable — SP M closure.** | Close the supported-format no-route obligation. Preserve the accepted exact raw `-singlemove` compatibility grammars; do not label either as a generated mechanic or add typed state. |
| **B02 — unresolved command aliases (C03/C04, R01/R06)** | Base `Battle.add/addMove/attrLastMove` serializes tokens verbatim; split/channel extraction selects records without alias rewriting. Literal emitters plus nonliteral command cases (`Battle.boost`'s `msg`, `BattleActions.switchIn`'s switch/drag, Gen-dependent fail/notarget, team-preview construction) never yield `clearstatus`, `-clearstatus`, `nothing`, `copyboost`, `invertboost`, or bare canonical-effect counterparts. | **Source-proven unreachable — SP serializer and operative emitter paths.** | Close no-route proof; preserve fail-closed unresolved/internal alias stops. Existing bare compatibility grammar, including bare ability and six v2 typed aliases, is unchanged and is not a generated-source support claim. Canonical `-nothing` belongs only to unavailable Splash; keep its accepted raw compatibility. |
| **B03 — legacy RainDance field end (C04/R17)** | `Moves.raindance/Abilities.drizzle → Field.setWeather/clearWeather → Conditions.raindance.onStart/onEnd` emits weather records. No M callback inserts RainDance in `Field.pseudoWeather`; `-fieldend` is the pseudo-weather family, with no stream normalizer changing weather to field. | **Source-proven unreachable — SP field family/source routing.** | Retain raw compatibility only; never treat it as typed weather removal. |
| **B04 — Instruct (C05)** | `Moves.instruct.onHit` checks lastMove, forbidden/charge/recharge flags, Dynamax, pending Beak Blast/Focus Punch/Shell Trap and PP, emits `-singleturn … move: Instruct … [of] source`, then prioritizes a move action. It lacks an M seed even through the closed indirect graph. | **Source-proven unreachable — SP M closure.** | Close as excluded from this generated format. Keep the unsupported template rejected; no new grammar or request behavior. |
| **B05 — Psych Up computed loop (C10/C19)** | `Moves.psychup.onHit`: copy boost map, remove then copy exactly `dragoncheer/focusenergy/gmaxchistrike/laserfocus`, preserving only source-side internal parameters, then `-copyboost … [from] move: Psych Up`. M has no Psych Up seed. | **Source-proven unreachable — SP**, with a finite four-ID argument set. | Close C10 source-value/route proof; keep existing bounded compatibility and represented inventory. No new transfer implementation. |
| **B06 — Costar, Commander and ally copies (C11/C30/R15)** | `Abilities.costar.onStart` first reads `pokemon.allies()[0]` and returns if absent; only then it copies the same four IDs/stages and emits Costar `-copyboost`. `Side` creates one active slot; `Side.allies` selects active living allies and `Pokemon.allies` removes self. Copying/transformation cannot add a slot. Commander needs another allied active Dondozo; Receiver/Power of Alchemy need another allied faint. | **Source-proven unreachable — SP singles slot invariant**, independently of absent A seeds. | Close as excluded. The constructed Costar scanner fixture remains a scanner test only. No tagged Costar grammar, commanded/commanding, ally stage or multi-active support. |
| **B07 — Transform's computed crit loop (C10–11/C16/C19)** | `Imposter.onSwitchIn` or `Moves.transform.onHit → Pokemon.transformInto`. Guards reject fainted/illusion/Substitute targets, already transformed participants and specified Tera/species states. It copies current slots/stages/type/ability and removes/copies exactly the four crit IDs before `-transform`. The manifest's `Pokemon.copyVolatile` label refers to this enclosing `transformInto` loop at `sim/pokemon.ts:1281`. | **Transform reachable — SP; crit-ID copy branches source-proven unreachable.** No Focus Energy/Dragon Cheer/Laser Focus M seed, Gmax route, or Lansat Berry I seed exists; none of the reachable callbacks seeds those IDs. | Retain accepted Transform fields/raw provenance. CE-04A/C owns existing-field truth across reset/copy; no critical-hit counter feature. Source-value closure is complete even though the historically named inventory family remains unchanged. |
| **B08 — reflection and re-execution (C14/C16/R13)** | `MagicBounce.onTryHit/onAllyTryHitSide` requires an enemy, reflectable flag, no previous bounce and no semi-invulnerability; recreates the same ID and sets `hasBounced`. `BattleActions.runMove` Dancer requires a successful dance, nonexternal origin, living non-semi-invulnerable dancer, then reuses that ID with `externalMove`. Encore requires an existing lastMove slot/PP and allowed flags; locked moves retain their originating ID. | **Reachable — SP** through generated Magic Bounce, Dancer, Encore, Sleep Talk and Ditto. Reflection does not manufacture a different move. Rebound has no A/form seed and copying cannot supply it: **source-proven unreachable**. | Existing move/activation/HP/stage/condition/request families; CE-04A/F verifies lifecycle/provenance after reflection or copying. Retain Rebound registry/raw compatibility without a format claim. |
| **B09 — two-turn computed ID (C12/R10/R12)** | Selected or transformed `meteorbeam/solarbeam → onTryMove → addVolatile('twoturnmove') → Conditions.twoturnmove.onStart → addVolatile(effect.id)`. These are the only M origins. Sleep Talk rejects charge flags, Dancer neither flags them as dances, reflection cannot act on these nonreflectable attacks. On repeat, their callback removes the move-ID marker; `twoturnmove` stores a private target location and lock. | **Reachable finite set `{meteorbeam, solarbeam}` — SP; W below.** | Charging emits public move/`-prepare` and later damage, with an owned locked request. The internal markers have no public `-start/-end` emitter in these two move definitions; CE-03A's generic family wording was not a claim they emit those records. Raw/private treatment is sufficient for the markers; CE-04A/CE-05 retains charge/interruption/restoration truth obligations. |
| **B10 — public animations (C12/C16/R04)** | Base emitters are `BattleActions.hitStepStealBoosts` (Spectral Thief), `BattleActions.moveHit` (later boolean-`smartTarget` hit), `Items.powerherb.onChargeMove`, and `Moves.solarbeam.onTryMove`. M intersects their guards at Solar Beam, Meteor Beam and Dragon Darts. In singles, actor/target are opposing `a` slots; `addMove` has no suffix fields. | **Reachable — SP + W** for Solar Beam, Meteor Beam and Dragon Darts. Spectral Thief remains a separately reviewed compatibility form outside M. | **CE-04-ANIM accepted.** Retain four exact raw-only labels and reject all other labels, tags, field counts and non-singles/opposite roles. |
| **B11 — repeat-use computed ID (C13)** | `BattleActions.runMove → OverrideAction(Encore) → BeforeMove → cantusetwice && lastMove.id===move.id → addVolatile(move.id)`. Finite IDs stay `bloodmoon/gigatonhammer`; after `useMove`, successful removal emits the exact one-field hint. `Battle.endTurn` disables immediate normal reuse; Encore can override a different queued legal choice before execution. Sleep Talk calls `useMove` directly and does not create an extra `runMove` hint route. | **Reachable — SP + W**, both moves repeated by faster Encore; next source request is Struggle when Encore plus repeat-use disable leaves no ordinary move. | Retain current validated raw hint; no typed prohibition. **CE-05-REPEAT** verifies owned request and restored v2 publication across this already-proven route. |
| **B12 — move-hit/self/secondary fields (C14)** | `useMoveInner → ModifyType/ModifyMove → spreadMoveHit/runMoveEffects` and self/secondary recursion. Generated root 12 values plus self/secondary add exactly **confusion, flinch, glaiverush, healblock, lockedmove, mustrecharge, roost, saltcure, sparklingaria**: **21 total**. Curse removes its volatile for non-Ghost sources and substitutes self boosts; No Retreat may remove its volatile when already trapped. Tera Blast adds only Stellar self boosts; Serene Grace changes chances; Sheer Force deletes secondaries/self; filtering callbacks cannot add IDs. | **Finite reachable-family bound — SP.** Callback branches retain target, hit, immunity, type, status, chance and self/secondary guards; membership alone does not say every branch fires on every set. | Existing classified IDs only. CE-04A owns lifecycle truth, including Curse under Ghost Tera/Transform, Psychic Noise Heal Block and self Glaive Rush/Roost. Fling's item-derived secondary and Stench/King's Rock/Razor Fang flinch insertion have no M/A/I seed; they cannot expand the bound. |
| **B13 — linked statuses (C15/R10)** | All operative fourth `addVolatile` arguments resolve to literal **trapper**. Among M, **Spirit Shackle** alone reaches one (`Moves.spiritshackle.onHit → target.addVolatile('trapped', source, move, 'trapper') → Pokemon.addVolatile`). It requires a surviving active source, a hit and status immunity success; Ghost trapping immunity can reject it. `removeVolatile/removeLinkedVolatiles/clearVolatile` unlink. Anchor Shot, Block, Jaw Lock, Mean Look, Spider Web, Thousand Waves, Octolock and G-Max roots are absent or excluded. | **Reachable finite value `{trapper}` — SP + W.** | Spirit Shackle's linkage is silent beyond its move/hit evidence; both `trapped/trapper` remain internal/raw-only. **CE-04-LINK** and CE-05 verify release and the owner's legal request, with no public link/target/counter export. |
| **B14 — Baton Pass versus Shed Tail (C15/C19)** | Only base `selfSwitch:'copyvolatile'` is Baton Pass, absent from M. **Shed Tail is generated** by Cyclizar/Orthworm; it requires a legal bench switch, more than half HP, no existing Substitute and no Commander state; costs half HP and sets `selfSwitch:'shedtail'`. `switchIn → copyVolatileFrom` copies only Substitute and explicitly does not copy stages for Shed Tail. | Baton Pass **source-proven unreachable — SP**; Shed Tail **reachable — SP + W**. | **CE-04-SHEDTAIL:** receiver gets no new `-start`; source `-start … Substitute … [from] move: Shed Tail` and receiver `switch … [from] Shed Tail` must preserve existing public Substitute truth/reset. This is not a new general stage/volatile transfer feature. |
| **B15 — stage swap/theft/inversion (C19/C29/R04)** | Power Swap/Guard Swap/Heart Swap emit `-swapboost`; Spectral Thief's `BattleActions` branch emits clear/animation and transfers positive stages; Topsy-Turvy emits `-invertboost`. All move roots are outside M. Costar is B06; Opportunist/Mirror Herb lack A/I seeds. | **Source-proven unreachable — SP M/A/I closure.** | Close no-route obligations; keep already accepted bounded compatibility fixtures. Reachable Transform stage copying, Haze/Clear Smog, Mirror Armor reflected boosts and White Herb selective clearing retain existing record families and CE-04C boundary-truth validation. |
| **B16 — Contrary + Belly Drum (C19)** | Direct Belly Drum holders are Azumarill/Eiscue/Cetitan; their generated abilities/form defaults are not Contrary. Direct Contrary holders Serperior/Malamar/Lurantis/Enamorus do not have Belly Drum. The only Trace origin is Gardevoir, whose pool lacks Belly Drum/Transform and whose copied ability is not a new move source. Transform copies slots and current ability together; it cannot combine a Belly Drum target's slots with a different target's Contrary, and already-transformed target/user guards prevent iterative grafting. Sleep Talk only reads those same slots; Belly Drum is neither reflectable nor a dance; Snatch and ability-granting/swapping moves/contact abilities lack seeds. | **Source-proven unreachable — SP relational move/ability proof**, not the invalid cross-product of independent candidate lists. | Close this named combination as excluded. Ordinary Belly Drum and Contrary boost paths remain represented separately; no special new grammar or mechanic. |
| **B17 — ability callback composition (C16/C22)** | A plus six form defaults; `Battle.runEvent/singleEvent`, `Pokemon.setAbility/formeChange/clearVolatile`, Trace/Imposter as above. Literal callback-created values include Cud Chew, Disable, Attract, Charge, Flash Fire, Confusion, Protosynthesis, Quark Drive, Slow Start, Truant and Unburden; no computed new ID emerges. Existing condition callback expiry/cure can emit end/ability/status/HP/stage/field records; form callbacks add details/form/type/HP evidence. | **Source-bounded existing families — SP.** Guards are each callback's active/species/type/contact/status/weather/terrain/damage/chance test, `setAbility` protection, and event suppression. Copied abilities retain those tests. | **CE-04-CALLBACK** groups reveal/change/end/suppress/restore and silent effects. No observation or belief learns A membership. Item/ability suppression correctness and form-default provenance remain typed-boundary work, not a reason to invent a public reveal. |
| **B18 — item callbacks and recycling (C16/C22)** | I-bound callbacks; Trick/Switcheroo and Magician/Pickpocket move existing items, Harvest/Cud Chew reuse previously held/eaten Berries. Choice items add choicelock; Booster Energy adds only Protosynthesis/Quark Drive after its active/not-transformed and weather/terrain guards; Power Herb is B10; berries/items otherwise emit item/activation/HP/status/stage or modify damage/PP/request privately. White Herb clears negative stages only. | **Source-bounded existing families — SP; W for Power Herb.** No item outside I can be supplied by transfers/recycling. | Retain internal/raw evidence and public reveals only. **CE-04-CALLBACK** and **CE-05-REPEAT** cover consume/change, Leppa PP and legal-request consequences; no held-item truth, set identity or private selector input in public prefixes/O/B/DATA. |
| **B19 — raw two-turn/lock remnants (R10/R12)** | Bounce/Dig/Dive/Fly/Phantom Force/Shadow Force/Sky Drop, Pursuit and Echoed Voice have no M seed. No called/copied/reflected access escapes M. Giga Impact supplies recharge; Outrage/Petal Dance supply lockedmove; Protect supplies stall; ordinary Choice items, flinch secondaries and Spirit Shackle supply the other internal IDs. | Listed absent move effects **source-proven unreachable — SP**; remaining internal control families **reachable — SP**. | Preserve accepted raw inventory; no altitude, echo, target-lock or recharge counter model. CE-04A/CE-05 verifies public consequences and owned choices, not hidden mechanics state. |
| **B20 — R03 singleturn forms** | Direct Beak Blast/Focus Punch/Protect/Roost callbacks are in M (and may be copied). Baneful Bunker/Burning Bulwark/Spiky Shield, Crafty Shield, Electrify, Endure, Follow Me, Helping Hand, Magic Coat, Mat Block, Powder, Quick Guard, Rage Powder, Shell Trap, Snatch, Spotlight and Wide Guard have no M seed. Max Guard and Z-Follow-Me need excluded action/item routes. | Four direct families **reachable — SP**; the remaining R03-P forms **source-proven unreachable by M**; R03-X **source-proven format-excluded**. | Keep exact validated compatibility forms raw-only. Beak Blast/Focus Punch/Protect need no typed one-turn flag; CE-04B still owns Roost type truth. Helping Hand's accepted active `[of]` validation is unchanged. |
| **B21 — special internal IDs (R14/R15/R16)** | `Conditions.arceus.onType` applies to generated Arceus/Multitype/Plate, with transformed/current-ability guard; Silvally/RKS System/Memories have no species/A/I seed. `gem` needs a Gem item, outside I; `rolloutstorage` needs Rollout/Ice Ball roots outside M. Dynamax requires `Side.canDynamaxNow` with `gen===8`; Commander is B06. Illusion's generated Zoroark route still emits `replace` then `-end … Illusion`. | Arceus and Illusion **reachable — SP**; Silvally/gem/rolloutstorage/commanded/commanding/dynamax **source-proven unreachable/excluded**. | Internal state remains private/raw-only. Arceus defensive type truth belongs to CE-04B/F; preserve already accepted Illusion identity/end handling. No new action or form scope. |
| **B22 — delayed slot consequences (C23/R11)** | Wish/Healing Wish/Revival Blessing/Future Sight are in M. `Moves.futuresight.onTry → addSlotCondition('futuremove')`, Healing Wish replacement and Wish callbacks emit delayed HP/status/faint/move effects. Lunar Dance and Doom Desire have no M seed; their corresponding routes cannot be copied/called into existence. **healreplacement** is separate: `BattleActions.runZPower` creates it only for a Z-Memento/Z-Parting-Shot replacement-heal effect, which has no Z-item/action route here. | Four families **reachable — SP**; Lunar Dance/Doom Desire/healreplacement **source-proven unreachable — SP**. | Retain slot timing/source/target privately. **CE-04-SLOTS** verifies delayed/public consequences and loss/cancellation at switch/faint/terminal; R11 raw sufficiency is not assumed from the source proof. |
| **B23 — Revival normal/copied route (C25/R11)** | Generated Pawmot/Rabsca → Revival Blessing `onTryHit` requires a fainted party member → slot condition + selfSwitch → `runAction` pauses for a switch request → `Side.chooseSwitch` accepts only a fainted target → revive action increments count, restores HP/status and emits split `-heal … [from] move: Revival Blessing`. Generated Ditto has Imposter; `Abilities.imposter.onSwitchIn → Pokemon.transformInto` copies the target's move slots, so an eligible copied Pawmot/Rabsca user reaches the same guards. Sleep Talk cannot synthesize RB: generated Sleep Talk pools lack it, and Transform preserves one copied moveset. | **Reachable — SP**; direct Pawmot/Rabsca and bounded Imposter witnesses. | Existing owner-only selection retained. **CE-05-REVIVAL** now witnesses mirrored v2 successor/publication/restoration chains, a copied user, consecutive selections, later public effects, and terminal continuation. |
| **B24 — Revival excluded singles variants (C25)** | The sole active living user is the self target. RB causes no damage/contact, no self-sacrifice and no dance/reflection; confusion/flinch failure occurs before slot creation. After successful creation, `runAction` pauses before the other queued action/residual. Reachable item callbacks do not damage a Status-move user (Life Orb excludes Status); status/weather/slot residual damage has not run. Thus the user is living at selection and cannot be the fainted active target. | **Source-proven unreachable — SP** for a fainted/inactive reviver and active-slot revival/instaswitch target on this generated singles route. | Close those C25 no-route candidates. Keep fail-closed guards and constructed negative fixtures; no implementation of the generic source branch `target.position < active.length`. Multi-active remains excluded. |
| **B25 — simultaneous/consecutive Revival (C25/C26)** | `turnLoop` stops as soon as `runAction` establishes a request. `commitChoices` sorts the new selection actions, then appends the saved old queue; `BattleQueue.resolveAction` assigns revival order 6, and the revive action removes the slot condition before the next queued move executes. The second Revival therefore cannot create its slot until the first selection is consumed. Revival's pure self output cannot KO/force-switch the opponent; an already-set ordinary switch flag causes an earlier pause. A previously fainted foe without a switch flag can wait until later `checkFainted`. | Simultaneous two-side Revival selection **source-proven unreachable — SP**; consecutive opposite-side revival selections **reachable source route** when both begin with eligible fainted bench members. | No combined multi-revival API. The CE-05-REVIVAL fixture now replays Pawmot selection then queued Rabsca selection, with each opposite owner waiting and then a joint ordinary request; source order is covered by a wrapper restoration witness. |
| **B26 — requestless/wait/empty-action boundaries (C26/R07)** | `Battle.makeRequest/getRequests` emits for every side, substituting `{wait:true, side}` for null. Move requests require a surviving side and `getMoveRequestData` supplies Struggle or recharge/locked move when ordinary choices disappear. Switch flags create `switch+wait` or ordinary `switch+switch`; invalid flags are cleared when `canSwitch` fails except revival. `turnLoop` runs synchronously until request or terminal; `checkWin` precedes new ordinary decisions. | Stable nonterminal `move+requestless`, `requestless+requestless`, `wait+wait` and nonwaiting empty-move menu **source-proven unreachable — SP** in successful engine execution. Partial channel delivery/consumed requests are transient transport states, not new engine decisions. | Retain guard stops. **CE-05-BOUNDARY** proves wrapper settling/restoration for the reachable request pairs; no fabricated actions or request-state implementation here. Terminal requestlessness remains CE-06 evidence work. |
| **B27 — team preview/setup markers (C26/R07)** | Operative rules resolve to PotD/Obtainable/Species/HP Percentage/Cancel/Sleep Clause/Illusion Level and their validation children; neither Team Preview nor Open Team Sheets is present. `Battle.start` invokes only operative `onTeamPreview` hooks, then starts queued play. | `clearpoke/poke/teampreview` preview flow **source-proven unreachable — SP rules**; `start/turn/upkeep` **reachable**. | Preserve compatibility/raw markers; no new preview actions. A generated setup does not publicly list hidden `poke` entries just because a generic setup family can. `done` has no pinned engine emitter; stream `end` is an out-of-band result channel, not public terminal authority. |
| **B28 — debug/team/private diagnostics (C29/R09)** | `Battle.debug` emits only when `format.debug || options.debug`; operative format/default stream disables it. Base `debugError` has no operative source caller. `showOpenTeamSheets` requires its absent rule or explicit administrative stream command. `Side.emitRequest/emitChoiceError` use sideupdate; split selection is in `BattleStream/getPlayerStreams`. | Normal generated route **source-proven no debug/team emission — SP**; explicit admin/debug inputs can emit them but are outside this supported route. | Preserve CE-02 spectator rejection before accumulation. `showteam` is not intrinsically a secret side channel in upstream code: when explicitly requested, its `Battle.add` contains packed teams; that is precisely why this adapter blocks it. No privacy broadening. |
| **B29 — other-format tokens (C30)** | Gen/mod overrides account for `-cureteam/-notarget/c:/custom/j/updatepoke`. Gen9 base fail paths choose `-fail`, not legacy `-notarget`. Mega/Primal/Ultra/Z require unavailable Mega/Primal/Z items or action paths; Arceus's source guard chooses Plates. `-candynamax`/Max Guard/Gmax require Gen8. `swap/-center` require multiple active positions. Pledges' `-combine/-waiting` look for a queued **allied** Pledge, absent in singles (and absent M roots). | **Source-proven unreachable/excluded — SP mod, generation, I and active-slot guards.** | Preserve existing explicit format exclusion; no doubles/triples/targeted action, Rigged Dice, transformation-item or other-mod contract. |
| **B30 — OHKO and EV-warning diagnostics (C28/C29)** | Fissure/Guillotine/Horn Drill/Sheer Cold are outside M; no indirect expander seed, hence `BattleActions` OHKO marker has no route. EV `bigerror` is called only by debug-mode `checkEVBalance`; generator starts at 85 each and only reduces values, so both teams also obey 510. | **Source-proven unreachable — SP.** Scheduled turn-limit `bigerror` remains reachable and accepted independently. | Retain OHKO/other-diagnostic stops. No broad raw warning allowance; CE-02's exact turn-limit warning is unchanged. |
| **B31 — remaining parser/emitter routing (R01/R06/R08/R09)** | Literal/nonliteral emitter reconciliation above accounts for switch/drag, move, stage `msg`, team-preview construction, serializer forwarding and private request/error. `BattleStream` administrative `chat`/tiebreak can emit chat/message; inactive/c/bare outcome aliases have no ordinary generated-engine source. `tier` is source-emitted then deliberately filtered; timestamps retain accepted normalization. Source suffix callbacks for Ivy Cudgel, Shell Side Arm and Tera Blast annotate existing move records and do not select a new command/ID. | **SP per source route.** Ordinary public outcomes and exact metadata are reachable; compatibility/admin-only aliases do not become generated mechanics. | Retain current classified raw/filtered/private behavior. CE-04-ANIM accepts its exact bounded raw forms; unknown/changed forms continue to fail closed. No generic alias rewrite or opaque-command escape hatch. |
| **B32 — Reflect Type and computed type/field outputs (C16/C18/C21)** | `Moves.reflecttype.onHit` copies the target's types but has no M seed or indirect entry. Reachable Transform, Roost, Tera/form changes and type callbacks retain their guards; Weather Ball/Tera Blast/Revelation Dance/Shell Side Arm change type/category, not ID. Move setters plus Drought/Drizzle/Snow Warning/Sand Stream/Orichalcum Pulse bound weather to sunnyday/raindance/snowscape/sandstorm. Grassy/Electric/Psychic Surge, Seed Sower and Hadron Engine bound terrain to grassy/electric/psychic; Teraform Zero clears existing weather/terrain. Trick Room is the only generated pseudo-weather setter. Ion Deluge and Plasma Fists both lack M seeds; no other reachable callback creates that field. | Reflect Type, Misty Terrain, legacy/extreme weather and other pseudo-weather setters **source-proven unreachable — SP M/A/I closure**; listed existing type/field families **source-bounded reachable — SP**. | Close Reflect Type's route obligation; keep accepted out-of-route field compatibility. Existing public type/field truth, Roost expiry and Tera/form/ability interactions remain CE-04B/E/F. Ability-created terrain is included even though no terrain-setting move appears in M. |

### Narrow child slices and acceptance evidence

| Child | Exact boundary / affected contracts | Required focused acceptance evidence (not implemented here) |
|---|---|---|
| **CE-04-ANIM — complete reachable public raw grammar** | PRO/OBS/PIPE/DATA; exact four-field `-anim` records for generated **Solar Beam** in sun, **Meteor Beam** after generated Power Herb consumption, and the second single-target `smartTarget` hit of generated **Dragon Darts**. Existing Spectral Thief compatibility stays bounded. All actor/target roles are opposing Gen 9 singles active (`p1a`/`p2a`) identifiers, with no tags. | Source table and mirrored simulator fixtures W1/W2/W6 prove each generated route for both actors. Table-driven TS/Python controls cover every label, both perspectives and input/successor prefixes; malformed labels/roles/counts/tags fail before projection and Python publication. Raw evidence introduces no typed state, legality, timer, belief or feature behavior. |
| **CE-04-SHEDTAIL — silent Substitute transfer** | OBS/PRO/TRANS/DATA; existing Substitute public truth on source switch-out and receiver, with no stage transfer. | W5, both sides; source/receiver public prefix, Substitute break/removal, drag/faint/re-entry, null/unknown versus absent, restored successor and Python parity. Hidden substitute HP is never projected. |
| **CE-04-LINK — Spirit Shackle release and request truth** | OBS/ACT/TRANS; raw-only trapped/trapper, no new link field. | W4 with Ghost immunity, source/target switch/faint, alternate living bench, restored next owned request and hidden-opponent perturbation; no inferred public trap target or countdown. |
| **CE-04-CALLBACK — bounded callback output truth** | OBS/BEL/PRO/DATA, scoped separately by existing reveal/change/end/form/HP/status/stage family. | A/I guard-domain source rows B17/B18; Trace/Imposter and form-default ability evidence, item transfer/consume/Harvest/Cud Chew and suppression/restoration, both perspectives; test only public authorizations and preserve immutable prior evidence. It is not a demand to type every callback. |
| **CE-04-SLOTS — Wish/Healing Wish/Future Sight consequences** | OBS/PRO/TRANS; retain private slot/timing state. | Source delayed heal/damage/status consequences, faint/replace/cancel/terminal, split-HP privacy and restoration; prove raw-only sufficiency without pending-slot forecasts. The excluded Z-healreplacement branch is not part of this slice. |
| **CE-05-REPEAT — Encore/repeat-use request chain** | ACT/OBS/TRANS/PIPE/DATA; exact bounded hint evidence, forced repeat and following owned Struggle request. | Implemented checkpoint: W3 both actors and both finite repeat IDs; normal repeat disabled, faster Encore overrides a different queued legal choice, the next source request is authoritative, restored continuation and v2 publication. No hint-derived action mask. |
| **CE-05-REVIVAL / CE-05-BOUNDARY — reachable pair closure** | ACT/OBS/BEL/TRANS/PIPE/DATA; bounded owner-only revival+wait, sequential opposite-side revival, joint resumed play and terminal delivery. | Pawmot/Rabsca and eligible Imposter-copy witnesses, both perspectives, waiting-side private request separation, sequential consumed-request restoration, deterministic identities and actor-only publication. B24/B25 exclusions retain active-target, multi-active, simultaneous-selection and generic waiting stops; terminal envelopes stay CE-06. |

The only newly demonstrated parser stop is CE-04-ANIM. The other children make
the remaining existing-field/request sufficiency obligations precise; their
source classification is not a claim that every wrapper path currently fails.
No lifecycle, request progression or episode-envelope implementation entered
CE-03B.

### CE-04-ANIM complete pinned-source table (2026-10-01)

`Battle.addMove` serializes each base emitter as exactly
`|-anim|<actor>|<label>|<target>`; none of the six base call sites appends an
animation tag. In the operative `gen9randombattle` singles format,
`BattleActions.runMove` supplies active Pokemon objects, so their
`Pokemon.toString()` identifiers are opposing `p1a`/`p2a` roles. The table is
an emitter-condition traversal over M and the generator/item selectors, not a
metadata or sample-only inventory. All retained forms are public raw evidence
only: no typed state, volatile, stage, type, belief, timer, legality or model
feature follows from one.

| Emitter form / exact grammar | Pinned condition and generated reachability chain | Reachability | Typed-state requirement | Disposition |
|---|---|---|---|---|
| `-anim|active actor|Spectral Thief|opposing active target` (four fields after the leading separator) | `sim/battle-actions.ts:774-804` emits only after Spectral Thief steals positive boosts. `spectralthief` is absent from M and no indirect seed escapes the CE-03B call/copy closure. | Excluded from current generated domain; separately reviewed compatibility form. | Public raw only; existing clear/boost records carry any stage truth. | Preserve exact literal compatibility grammar. |
| `-anim|active actor|Solar Beam|opposing active target` | `data/moves.ts:17899-17909`, `Moves.solarbeam.onTryMove`, calls `addMove` after `effectiveWeather()` is `sunnyday`/`desolateland`. Generated Sunflora seed `[93,2,3,4]`, slot 4, supplies the direct sun witness. | Direct reachable in sun. | Public raw only; no charge or weather state is inferred. | Accept exact label and roles from the direct sun route only. The separately possible Power Herb callback shape is **unproven for generated-team reachability** and remains the named **CE-04-CALLBACK** item-transfer child. |
| `-anim|active actor|Meteor Beam|opposing active target` | `data/items.ts:4420-4426`, `Items.powerherb.onChargeMove`, calls `useItem()`, then `addMove`. Meteor Beam is in M; `data/random-battles/gen9/teams.ts:1229` selects Power Herb when it is retained. Generated Armarouge seed `[22,2,3,4]`, slot 4 has Meteor Beam and Power Herb. Sleep Talk filters charge moves at `data/moves.ts:17535-17542`; item or Transform paths preserve the move name and do not introduce another animation form. | Direct reachable through generated item callback. | Public raw only; consumption remains in existing item evidence. | Accept exact label and roles. |
| `-anim|active actor|Dragon Darts|opposing active target` | `data/moves.ts:4265-4275` defines `multihit:2`, `smartTarget:true`; `sim/battle-actions.ts:893-900` emits when `hit > 1`, the smart-target field is boolean and a live target remains for that hit. In singles the same opposing active target receives hit two. Dragon Darts is in M; generated Dragapult seed `[59,2,3,4]`, slot 2 has it. Sleep Talk does not filter Dragon Darts by flags, but no generated set pool contains both `sleeptalk` and `dragondarts`; `randomMoveset` selects only from the chosen pool. `Pokemon.transformInto` copies the target's complete move-slot list (`sim/pokemon.ts:1216-1250`), so Transform/Imposter cannot combine those separate pools. Encore/lock repeat the same move and retain this grammar. | Direct reachable; indirect call composition has no generated co-selection route. W6 proves both direct actors. | Public raw only; no hit counter/target model is added. | Accept exact label and roles. |
| `-anim|active actor|Electro Shot|opposing active target` | `data/moves.ts:4803-4819` emits only in rain; direct M intersection excludes Electro Shot. Power Herb’s generic emitter also cannot enter it because no generated set provides the move. | Source-proven excluded from M, including callbacks/copy/call closure. | None. | Reject label. |
| `-anim|active actor|Solar Blade|opposing active target` | `data/moves.ts:17936-17946` emits only in sun; Solar Blade is absent from M and no indirect route supplies it. | Source-proven excluded from M. | None. | Reject label. |
| Other base/custom-mod labels, same-side/bench slots, missing/reordered/extra fields, and any tags | Base search finds no further non-mod `-anim` call site. `data/mods/gen9ssb/**` and other mod emitters are outside the pinned format (`mod:gen9`, `game_type:singles`); no team preview/doubles or other-mod selection occurs. | Format-excluded or malformed before routing. | None. | Reject before TS projection and Python publication. |

Call, copy, reflection and callback routes remain bounded by CE-03B. Sleep Talk
filters charge moves and its callable move set stays on the actor's selected
slots; the no-co-selection proof above closes Dragon Darts. Transform and
Imposter copy complete slots rather than joining different random-set pools.
The remaining registry/call roots are either absent from M or have format,
move-flag or allied-active-slot guards that exclude a new animation source.
The generic Power Herb callback could use the Solar Beam label after an item
transfer, but the cited Meteor Beam, Trick, and Solar Beam pools do not prove a
legal generated-team co-occurrence or execution sequence. It remains an
unproven **CE-04-CALLBACK** item-transfer child and supplies no CE-04-ANIM
reachability claim.

### CE-04-SHEDTAIL public Substitute-transfer lifecycle table (2026-10-01)

The pinned `Moves.shedtail` (`data/moves.ts:16762-16798`) is generated for
Cyclizar/Orthworm pools and succeeds only with a switchable bench, more than
half HP, no existing Substitute and no Commander state. It applies half-max-HP
direct damage, starts Substitute, marks `selfSwitch:'shedtail'`, then
`BattleActions.switchIn` (`sim/battle-actions.ts:68-132`) calls
`copyVolatileFrom(outgoing, 'shedtail')`. That method (`sim/pokemon.ts:1192-1218`)
copies only `substitute`, skips boosts, clears the departing volatile state, and
the replacement's switch record is exactly suffixed
`[from] Shed Tail`. The table limits projection to those public facts.

| Lifecycle fact | Pinned source/protocol path | Capture treatment and disposition |
|---|---|---|
| Selection and failure guards | Random Battle selected move pool; `onTryHit` checks bench/Commander/existing Substitute/HP. A public `-fail` can occur. | Selection, guard causes and hidden bench state are private/omitted; existing raw `-fail` is evidence only. Already correct. |
| Half-HP cost and outgoing Substitute | `onHit → directDamage`; `volatileStatus:'substitute' → Substitute.onStart` emits `-start|<outgoing>|Substitute|[from] move: Shed Tail`. | Public HP and Substitute presence are represented typed state; Substitute HP is private/omitted. Already correct. |
| Replacement and transfer | `switchIn` emits `switch|<incoming>|…|[from] Shed Tail`; `copyVolatileFrom(..., 'shedtail')` copies only Substitute and clears outgoing volatiles. No receiver `-start` is emitted. | Incoming Substitute and cleared outgoing Substitute are represented typed public state. Corrected the extractor to require the exact pinned switch suffix; a generic `[from] move: Shed Tail` must remain raw-only and cannot manufacture a transfer. |
| Nontransfer of other state | Same `copyVolatileFrom` branch skips every volatile other than Substitute and does not copy boosts; it does not copy identity, Tera, types, item, moves, request or hidden state. | Existing fresh replacement construction and ordinary switch clearing retain public identity/fields without a transfer. Already correct; no hidden state is projected. |
| Later Substitute removal | `Substitute.onTryPrimaryHit` removes the volatile when its private HP reaches zero and emits public `-end|<incoming>|Substitute`; ordinary removal can also emit that end record. | Existing `-end` routing removes typed public Substitute; private substitute HP/duration stays omitted. Already correct. |
| Later switch, drag, faint and re-entry | `clearVolatile` during `switchIn`; `Battle.faintMessages`; protocol `switch`/`drag`/`faint` paths. | Existing lifecycle clearing removes Substitute and boosts on departure/faint; re-entry has no stale transfer. Already correct. |
| Restoration and terminal continuation | Serialized battle restoration replays the exact public prefix; transition projection and v2 publication carry only public observations. | Both perspectives preserve the same allowed Substitute effect, with no request/hidden identity leakage. Focused fixture validates restored forced-switch continuation and Python publication; terminal state adds no Substitute-specific hidden field. |

This accepts no general volatile-copy semantics, Substitute durability model,
linked effect, request progression, or callback behavior beyond the exact
public Shed Tail transfer above.

### Reproducible local source probes and results

All probes use the installed local package and fixed seeds; none reads network
data or writes datasets. Selection witnesses use
`Teams.generate('gen9randombattle', {seed:[n,2,3,4]})[slot]` with **zero-based**
slots. Those selected sets are reassembled into small `Battle` fixtures with
`formatid:'gen9randombattle', seed:[1,2,3,4]`. This demonstrates real selector
output plus controlled battle execution, not absence or a full six-member
episode. `Battle.getTeam`'s explicit-team bypass is why the distinction matters.

| Probe | Exact local recipe and asserted result |
|---|---|
| **P1 — registry/config/source bound** | Normalize `sets.json` pools using `Dex.mod('gen9').toID`; assert 350 moves/203 abilities. Filter `dex.moves.all()` by `callsMove` and membership: only `sleeptalk`; no generated set pool co-selects Sleep Talk with Dragon Darts. Sleep Talk's source also filters `charge` and `nosleeptalk`. Traverse generated move root/self/secondary/secondaries fields: root volatile set matches CE-03A's 12, nested union is B12's 21. Resolve `dex.formats.getRuleTable('gen9randombattle')`: no Team Preview/Open Team Sheets. Read the six form-default abilities and selectors as stated above. |
| **P2 — item/source emitter bound** | Parse `data/random-battles/gen9/teams.ts` with the already installed TypeScript API; collect item-name literals in `getPriorityItem/getItem`, union selected requiredItems (Arceus first only), expand the five Gluttony berry names, exclude the `isDoubles` Clear Amulet return: 66-ID conservative I. Audit all base `add/addMove` nonliteral first arguments and operative rules; serializer/switch/stage/preview cases are B02/B31, not arbitrary protocol aliases. |
| **W1 — sunlight animation** | `p1=[seed 93/slot 4 Sunflora]`, `p2=[53/5 Ursaluna-Bloodmoon]`; choices `sunnyday/calmmind`, then `solarbeam/calmmind`. Assert source line `\|-anim\|p1a: Sunflora\|Solar Beam\|p2a: Ursaluna`; the bounded CE-04-ANIM grammar accepts it as raw-only evidence. |
| **W2 — Power Herb animation** | `p1=[22/4 Armarouge]`, `p2=[53/5 Ursaluna-Bloodmoon]`; `meteorbeam/calmmind`. Selected Armarouge holds Power Herb. Assert `\|-anim\|p1a: Armarouge\|Meteor Beam\|p2a: Ursaluna`; the bounded CE-04-ANIM grammar accepts it as raw-only evidence. |
| **W6 — smart-target animation** | Generated Dragapult `[59/2]` versus passive Snorlax; `dragondarts/splash` emits `\|-anim\|p1a: Dragapult\|Dragon Darts\|p2a: Snorlax` on hit two. The CE-04-ANIM fixture repeats the generated Solar Beam, Meteor Beam and Dragon Darts conditions with the generated actor as p1 and p2; every exact record validates/projects, while Dragon Darts tags, same-side target and malformed identifier controls reject. |
| **W3 — both repeat-use hints** | For `53/5 Ursaluna-Bloodmoon` and `117/3 Tinkaton`, p2 is `3/0 Lumineon` plus `17/2 Azumarill` bench. First choose `bloodmoon` or `gigatonhammer` versus `encore` (first Encore fails); assert that move disabled in the next owned request. Then choose `moonlight` or `playrough` versus `encore`: faster Lumineon overrides the queued move. Assert exact accepted line `\|-hint\|Some effects can force a Pokemon to use Blood Moon again in a row.` or `... Gigaton Hammer ...`. Consume p2 replacement with `switch 2` if requested; next p1 move request is enabled `struggle`. |
| **W4 — linked origin** | p1 `215/4 Decidueye` plus `17/2 Azumarill`; p2 `3/0 Lumineon` plus `22/4 Armarouge`; `spiritshackle/encore`. Assert simulator has p1 `trapper`, p2 `trapped`; the linkage supplies no new public `-start` record. These internal assertions are probe evidence only, not player output. |
| **W5 — Shed Tail** | p1 `113/2 Cyclizar` plus `17/2 Azumarill`; p2 `53/5 Ursaluna-Bloodmoon` plus `22/4 Armarouge`; `shedtail/calmmind`, then p1 `switch 2`. Assert source `-start … Substitute … [from] move: Shed Tail`, receiver `switch … [from] Shed Tail`, receiver internal Substitute and seven zero stages; no receiver `-start` is emitted. |

P1/P2 and W1–W5 completed locally. The final positive scripts asserted their
source outcomes. Initial exploratory controls that used a Normal
target for Spirit Shackle or read a post-KO null request were corrected to the
explicit recipes above; those exploratory failures are not absence evidence.

### Remaining proof obligations and drift boundary

All assigned named source/no-route candidates now have a source disposition in
B01–B32. **No no-route closure rests only on a `Past` flag, missing set entry or
random sample.** Source-bounded candidate sets deliberately do not claim that
all 350 moves, 209 ability upper-bound IDs or 66 item upper-bound IDs were
selected and activated. Individual callback combinations' *capture sufficiency*
remains the named CE-04/CE-05 acceptance work above; a future path outside the
source domains reopens this proof instead of broadening support silently.

No scanner regression was added: every proof dependency is already inside the
manifest's hashed `config`, `sim`, `data`, `dist/config`, `dist/sim`, or
`dist/data` roots. `sourceInventory`/per-root comparison in
`check-simulator-coverage.cjs` rejects a change to any of these call edges,
flags, values, source bodies or compiled counterparts; CE-03A separately binds
generated memberships/selectors/finite values/format guards. Existing
computed-callsite and family checks still retain their fail-closed runtime
classifications. A digest is drift detection, not this semantic proof, and
refreshing it without a review cannot attest a new route.

Only this audit and the PIPELINE-002 checkpoint changed. No scanner, manifest,
validator, state/transition/runtime code, tests, dependency or digest field was
edited. `git diff --check` is the final documentation check.

**CE-03B / CE-04-ANIM implementation checkpoint (2026-10-01): unreviewed.**
The missing Dragon Darts path is now source-disposed with the complete direct
generated `-anim` family. Pinned `data/moves.ts:4265-4275` defines its two-hit
`smartTarget` behavior and `sim/battle-actions.ts:893-900` emits the exact
second-hit record. The shared contract and both validators retain only
Spectral Thief compatibility plus generated Solar Beam, Meteor Beam and Dragon
Darts forms, each as four-field public raw evidence with opposing active
singles roles and no tags. The table-driven and mirrored generated fixtures
cover both actors, input/successor prefixes, malformed grammar and
no-publication rejection. This is an unreviewed implementation checkpoint; it
does not accept PIPELINE-002 or change `faithful_complete_episode:false`.
The focused checker reports local coverage digest
`ce0171ddd7377e3a2f24464212c6e48223f7ef73228098320132ce147843da7e` as
**unreviewed**; its expected digest was deliberately not updated here.

### CE-04-ANIM scoped review verdict (2026-10-01): accepted

The source table inventories all six pinned base-package emitters and limits
Solar Beam's accepted label to the direct generated sun route. Meteor Beam's
direct generated Power Herb route and Dragon Darts' second singles
`smartTarget` hit remain proven; Spectral Thief is exact compatibility only,
and Electro Shot/Solar Blade remain rejected. The generic Power Herb callback
after a hypothetical Solar Beam item transfer is explicitly unproven and stays
assigned to the CE-04-CALLBACK item-transfer child, without expanding the
grammar or claiming generated-team realizability.

The shared TypeScript/Python contract accepts only exact untagged active actor
and opposing active target records for the four literal labels. Both runtime
paths verify malformed rejection, publication rollback, input/successor
prefixes, and both perspectives; all changed implementation and fixture files
are listed by `local_coverage_sources`. Focused validation and the coverage
self-test pass. The computed local digest
`ce0171ddd7377e3a2f24464212c6e48223f7ef73228098320132ce147843da7e` is
reviewed for CE-04-ANIM. This does not accept the CE-04-CALLBACK item-transfer
child, PIPELINE-002, or `faithful_complete_episode:false`.

### CE-03B scoped source-proof review verdict (2026-10-01): accepted

The prior missing Dragon Darts route is now B10's documented reachable public
output: generated Dragon Darts has `multihit:2` and `smartTarget:true`, and
the pinned second-hit branch emits exactly
`|-anim|<active actor>|Dragon Darts|<opposing active target>` in singles.
CE-04-ANIM accepts that bounded raw-only form. No CE-03B no-route proof claims
singles excludes Dragon Darts.

B01–B32 retain their reviewed source proofs and distinguish source-proven
no-route conclusions from reachable CE-04/CE-05 child slices. The unresolved
Power Herb-to-Solar-Beam transfer is expressly assigned to CE-04-CALLBACK and
is not closed or used to broaden CE-04-ANIM. This closes CE-03B's assigned
source-proof review only; it does not accept its named lifecycle children,
PIPELINE-002, or `faithful_complete_episode:false`.

### CE-04-CALLBACK-A public ability-output source table (2026-10-01, unreviewed)

The operative format is `gen9randombattle` (`mod:gen9`, singles, random team).
`RandomTeams.getAbility` selects only the bound generated set candidate; it
does not itself emit a public ability value. The table follows only public
protocol output from that generated path and pinned base callbacks. Ability
names in a private `request.side.pokemon[].ability` or `baseAbility` remain
owner-private and are never an opponent-view source. `data/mods/**`, including
historical Gen 3/4 forms and `gen9ssb`, are outside this table.

| Public shape / exact grammar | Pinned source symbol and Gen 9 Random Battle route | Visibility and lifecycle | Existing typed state / disposition |
|---|---|---|---|
| `|-ability|<active>|<Ability>` | Base `data/abilities.ts` switch/start and callback emitters (Air Lock, Intimidate, ruin abilities and callback-target reveals), `sim/battle.ts:1959` ability boost prelude, and `data/items.ts:Ability Shield.onSetAbility`. Generated set ability selection is the only origin; a reveal occurs only when its callback emits. | Public confirmation at its record cursor. A plain record never establishes an unrevealed roster value beforehand. | Typed current ability and first independently public base ability; raw record retained. Exact plain form only. |
| `|-ability|<active>|<Ability>|boost` | `sim/battle.ts:1959` emits once for an ability-originated boost, after its normal callback guard. | Public confirmation, no counter/source model. | Typed current public ability; raw `boost` suffix retained. |
| `|-ability|<active>|<copied Ability>|[from] ability: Trace|[of] <opposing active>` | `Abilities.trace.onUpdate` (`data/abilities.ts:5060-5067`) calls `setAbility` then emits this exact order. Generated Gardevoir/Trace witness seed `[2,2,3,4]`, slot 2, supplies the direct route. | Both copied value and source target are public at this cursor. The copied current value is temporary and `clearVolatile` restores base on departure. | Typed current ability is `changed`; original base remains unknown unless independently revealed. |
| Same `[from] ability: Power of Alchemy` or `Receiver` copy form | `Abilities.powerofalchemy.onAllyFaint` and `Abilities.receiver.onAllyFaint`. Both need a living allied active/fainted ally. | Base-package grammar exists, but singles has no allied active slot. | Source-proven excluded for this format; accepted only as exact base grammar, with no reachability claim. |
| `|-endability|<active>|<old Ability>|[from] move: <Move>` followed by `|-ability|<active>|<new Ability>|[from] move: <Move>` (Role Play alone appends `[of] <active>`) | `Pokemon.setAbility` (`sim/pokemon.ts:1850-1874`) emits the end form for move effects; `data/moves.ts` emitters are Doodle, Entrainment, Role Play, Simple Beam, and Worry Seed. | The end record makes the prior live value unavailable; the following `-ability` is the sole public new-value confirmation. | End resets current to unknown; source-shaped replacement sets `changed`. These moves are absent from M, so the table preserves grammar and constructed controls without a generated-move claim. |
| `|-endability|<active>` | `Moves.gastroacid.condition.onStart` (`data/moves.ts:6670-6676`) emits target-only suppression before ending the ability callback. | Public suppression marker, but it carries no hidden ability name. Its silent expiration is not a new reveal. | Keeps any already public value, marks it suppressed, and never infers a missing ability. Gastro Acid is absent from M. |
| `|-ability|<active>|<Ability>|[from] <raindance\|sunnyday\|sandstorm\|snowscape>|[fail]` | `Field.setWeather` (`sim/field.ts:55-64`) when a generated weather ability's set attempt is rejected. | Public confirmation plus raw failed-weather provenance; no weather timer/source is typed here. | Typed ability confirmation, raw provenance. |
| `-activate`, `-start`, `-end`, `-immune`, `-block`, `cant`, HP/stage/status records with `ability:` or `[from] ability:` text | Bounded ability callbacks in `data/abilities.ts`, generated move callbacks, and `Battle.runEvent/singleEvent`; examples include Dancer, Tera Shell, Flash Fire, Neutralizing Gas, Protosynthesis and Quark Drive. | Public outcome/provenance evidence when emitted. Field roles and source semantics vary. | Retain exact raw evidence only; no private callback state, counter, source link, item state, or inferred ability is projected. |
| Switch, drag, faint, replacement, and terminal cleanup without a new ability record | `BattleActions.switchIn` calls `oldActive.clearVolatile`; `Pokemon.clearVolatile` restores `ability = baseAbility`; `Battle.faintMessages` calls the same cleanup. `replace` is Illusion identity reconciliation; terminal records do not expose private snapshots. | Source lifecycle restores the simulator value, but public projection restores only an already public base ability. | Clears stale changed/suppressed live values. Unrevealed bases remain unknown; no request/snapshot truth is imported. |
| `-transform`, `detailschange`, `-formechange` | `Pokemon.transformInto` silently sets the target current ability after `-transform`; `Pokemon.formeChange` can set a form default around public form records. | The form/Transform record proves identity/form only. It can never expose a hidden target or form ability by inference. | Clear current ability to unknown at the record; retain an independently public pre-Transform base only for later clearVolatile restoration. |
| Private request ability fields | `Side.getRequestData` serializes own `baseAbility`/`ability`; extractor ownership gates requests by addressed player. | Private to the addressed side. | Owner self view may retain it; opponent observations, v2 records, raw public prefixes, belief, DATA-001, and publication never receive it. |

The implementation fixture uses the pinned engine for generated Trace and both
acting sides, then source-shaped constructed controls for base replacement and
suppression grammar. It exercises both perspectives, v1/v2 input and successor
rehashes, immutable rejection/lineage, public restoration, Transform/form
privacy and Python publication. No item callback behavior, status cure/reapply,
slot effect beyond Wish, timer, pending ability field, source link, private
callback state, feature, or other delayed-effect support enters this child.

The computed local coverage digest is
`403e5818240fb7e2afdc34a13e9fe5d68369eeaba1671aefb3052c9fa1088cfa`;
it is unreviewed and the prior `reviewed_sha256` remains unchanged.

### CE-04-CALLBACK-A scoped review finding (2026-10-01, not accepted)

The CE-04-CALLBACK-A grammar is broader than the source-proven Gen 9 Random
Battle singles surface. Both raw validators accept
`|-ability|p1a: Pikachu|Static|[from] ability: Receiver|[of] p1a: Eevee`,
although Receiver and Power of Alchemy require an allied active and the table
classifies them as singles-excluded. They also accept arbitrary move provenance,
including `|-ability|p1a: Pikachu|Insomnia|[from] move: Splash`, even though
the named base replacement moves have no generated-move route. The matching
`-endability` form has the same unrestricted move-name rule.

`Field.setWeather` emits a failed-weather ability record only when a
`SetWeather` callback returns false. The relevant false-returning base weather
blockers have no Gen 9 Random Battle seed; normal same-weather attempts return
without this record. Nonetheless both validators accept
`|-ability|p1a: Torkoal|Drought|[from] sunnyday|[fail]`. Finally, the strict
ability provenance grammar also applies to bare `|ability|...`, which B02
retains only as a compatibility alias; for example
`|ability|p1a: Pikachu|Static|[from] ability: Trace|[of] p2a: Eevee` accepts
in both runtimes although pinned emitters use `-ability`.

Do not attest CE-04-CALLBACK-A until the supported grammar is narrowed to the
source-proven reachable forms, or each broader base form has a distinct
raw-only/excluded disposition that cannot project or publish. The local digest
remains unreviewed; this does not alter CE-04 scope, PIPELINE-002, or
`faithful_complete_episode:false`.

### CE-04-CALLBACK-A exact operative public-ability grammar (2026-10-01, unreviewed repair)

This table supersedes the broader callback grammar above for accepted public
prefixes. It follows `data/random-battles/gen9/sets.json` through the
single-active-slot `gen9randombattle` generator: Gardevoir supplies Trace,
Rayquaza supplies Air Lock, and Arcanine supplies Intimidate. The reviewed
generator has no Worry Seed, Gastro Acid, Role Play, Doodle, Entrainment,
Simple Beam, Receiver, or Power of Alchemy candidate. `Pokemon.setAbility`,
Gastro Acid, and `Field.setWeather` therefore prove base-package syntax only,
not an operative accepted prefix route.

| Command and exact fields | Allowed suffix / provenance fields in order | Pinned source symbol | Generated singles reachability | Visibility and disposition |
|---|---|---|---|---|
| `|-ability|<active ident>|<public ability>` | No suffix. | `Abilities.airlock.onStart` and same-shape generated ability callback reveals; Rayquaza/Air Lock is the simulator witness. | Reachable. | Public confirmation at this cursor; updates typed current and independently public base ability. |
| `|-ability|<active ident>|<public ability>|boost` | The sole suffix is literal `boost`. | `Abilities.intimidate.onStart` and `Battle#boost` (`sim/battle.ts:1959`); Arcanine/Intimidate is the simulator witness. | Reachable. | Public confirmation; updates typed current and independently public base ability. |
| `|-ability|<active ident>|<copied public ability>|[from] ability: Trace|[of] <active ident>` | Literal `[from] ability: Trace`, then `[of] ` plus an active source ident. No reordered, omitted, duplicate, or added field. | `Abilities.trace.onUpdate` (`data/abilities.ts:5060-5067`). | Reachable: generated Gardevoir/Trace; both actor-side witnesses. | Both displayed copied value and displayed source are public; updates only typed current ability as `changed`. |
| `|-endability|…` | No accepted suffix or field template. | `Pokemon#setAbility` can emit move-source endability; `Moves.gastroacid.condition.onStart` can emit target-only endability. | No operative route: all corresponding generator moves are absent. | Recognized `unsupported_stop`; rejects before extraction/projection/publication and cannot alter typed state. |
| `|ability|<active ident>|<public ability>` | No suffix. | No pinned base emitter; B02 compatibility spelling only. | Compatibility only, not generated output. | Retained raw-only; it never updates typed ability state. Callback provenance, `boost`, and all other suffixes reject. |

Receiver and Power of Alchemy require an allied active/fainted ally and are
excluded by the CE-03B singles-slot proof. Failed weather requires a false
`SetWeather` callback; no generated weather-blocker route was established.
Those records, every move-sourced ability replacement/suppression form, and
every suffixed bare `ability` record reject before committed-lineage mutation
or DATA-001 publication. The corrected local digest remains unreviewed.

### CE-04-CALLBACK-A repaired grammar review finding (2026-10-01, not accepted)

The source-form repair is not accepted. Both shared validators still accept a
same-side Trace source even though the pinned `Abilities.trace.onUpdate`
selects only `pokemon.adjacentFoes()` before emitting `[of] ${target}`. In
singles the source must therefore be the opposing active slot. Minimal
reproduction accepted by both boundaries:

```
|-ability|p1a: Gardevoir|Immunity|[from] ability: Trace|[of] p1a: Eevee
```

Both boundaries also accept a nonempty, trimmed arbitrary ability payload for
the dash and bare templates. This contradicts the table's source-proven
generated ability payload requirement and permits a fabricated value to reach
typed projection for `-ability` or raw publication for `ability`. Minimal
reproductions accepted by both boundaries:

```
|-ability|p1a: Gardevoir|Definitely Not An Ability
|ability|p1a: Gardevoir|Definitely Not An Ability
```

`sim-core/src/observable_state.ts#requireRawAbilityEvent` and
`trainer/src/neural/protocol_contract.py#_ability_event` must enforce the
finite operative payloads and the Trace actor/opposing-source active roles
before CE-04-CALLBACK-A can be attested. The local digest remains unreviewed.

### CE-04-CALLBACK-A finite-domain repair checkpoint (2026-10-01, unreviewed)

The shared contract now binds each accepted public ability template to an exact
finite `validation_rules.ability.payload_domains` list. The shared JSON and
matching TypeScript/Python expected-rule tables duplicate the authoritative
literals.

| Template | Actor/source roles | Exact finite domain | Source evidence |
|---|---|---|---|
| Dash reveal | target is active | `dash_reveal`: 17 values (Air Lock, As One, Beads of Ruin, Cloud Nine, Comatose, Gooey, Mirror Armor, Mold Breaker, Pressure, Sturdy, Sword of Ruin, Tablets of Ruin, Tangling Hair, Teravolt, Turboblaze, Unnerve, Vessel of Ruin) | Generated candidates intersect literal `data/abilities.ts` `-ability` emitters. |
| Dash boost | target is active | `dash_boost`: 30 emitted effect names | Generated callbacks reaching `Battle#boost`; the payload is `effect.name`, not necessarily the ability-holder name. |
| Dash Trace copy | actor is active; `[of]` is an opposing active | `dash_trace_copy`: 186 generated candidates allowed by Trace's `notrace` guard | `Abilities.trace.onUpdate` selects `adjacentFoes()`; candidates come from `sets.json`. |
| Bare compatibility reveal | target is active | `bare_reveal`: exactly the dash-reveal 17 values | B02 raw-only compatibility spelling constrained to the public reveal domain. |

The table-driven v1/v2 p1/p2 input/successor rehash matrix rejects same-side
Trace, invented and unknown text, and cross-template payloads before TypeScript
projection or Python publication. The computed coverage digest remains
`0ab90b62c0b1f41cb750f1ab2759fc3df9389fb5bfdb4edac59c5c5c97ac48ad` and
is unreviewed; this is not an attestation.

### CE-04-CALLBACK-A finite-domain review finding (2026-10-01, not accepted)

The claimed 32-value `dash_boost` domain is two values too broad. It accepts
the fabricated records below in both TypeScript and Python:

```
|-ability|p1a: Calyrex|As One (Glastrier)|boost
|-ability|p1a: Calyrex|As One (Spectrier)|boost
```

Pinned `Abilities.asoneglastrier.onSourceAfterFaint` passes
`this.dex.abilities.get('chillingneigh')` to `Battle#boost`; the Spectrier
variant analogously passes `grimneigh`. `Battle#boost` emits
`effect.name` as the `-ability` payload. Thus the source-shaped records use
`Chilling Neigh` or `Grim Neigh`, which are already domain members, never the
two As One variant names. The exact finite emitted `dash_boost` domain is not
the current 32-value list and CE-04-CALLBACK-A cannot be attested until it is
corrected and its table-driven rejection controls cover both fabricated forms.

### CE-04-CALLBACK-A emitted-boost repair checkpoint (2026-10-01, unreviewed)

`Battle#boost` emits `effect.name`. The finite `dash_boost` domain is therefore
the 30 emitted names: Anger Shell, Battle Bond, Berserk, Chilling Neigh,
Competitive, Dauntless Shield, Defiant, Download, Gooey, Grim Neigh, Gulp
Missile, Intimidate, Intrepid Sword, Justified, Lightning Rod, Mirror Armor,
Motor Drive, Moxie, Rattled, Sap Sipper, Soul-Heart, Speed Boost, Stamina,
Storm Drain, Tangling Hair, Thermal Exchange, Water Compaction, Weak Armor,
Well-Baked Body, and Wind Rider. Generated As One callbacks pass
`chillingneigh`/`grimneigh`; `As One (Glastrier)` and `As One (Spectrier)`
never publish as boost payloads and reject.

The shared JSON and matching TypeScript/Python tables carry the same list.
Table-driven v1/v2, p1/p2, input/successor controls retain valid Chilling/Grim
Neigh publication and reject both As One forms before projection/publication,
without mutation or output. The computed digest is unreviewed; this is not an
attestation: `50585303834f13303dc7c45bd51d40d9d135fe02ff03b74957f8b952fa0dbdda`.

### CE-04-CALLBACK-A emitted-boost review finding (2026-10-01, not accepted)

The 30-value `dash_boost` derivation is source-correct, but this repair is not
ready for attestation. The existing golden observable-state fixture still
contains the now-rejected record:

```
|-ability|p1a: Pikachu|Illusion
```

`tests/fixtures/observable_state_v1.json` uses that payload in an otherwise
valid decision-time prefix, so `npm test` fails
`observable-state golden fixtures preserve expected decision-time projections`
at raw validation. Reconcile that fixture with an actual source-backed reveal
or document a valid operative Illusion `-ability` emitter before claiming
existing lifecycle/historical-fixture compatibility.

The coverage checker otherwise reaches only its expected pre-attestation
semantic-review binding failure for the recorded local digest. It does not
clear the fixture regression.

### CE-04-CALLBACK-A golden-fixture repair checkpoint (2026-10-02, unreviewed)

Pinned `Abilities.illusion.onEnd` emits `replace` and then `-end` for the
revealed Pokémon. The observable-state golden prefix now uses
`|replace|p1a: Zoroark|Zoroark, L80|75/100` followed immediately by
`|-end|p1a: Zoroark|Illusion`; it removes the unrelated synthetic Eevee
replacement while retaining the ten-record ordered cutoff and its public
projection assertions. A focused regression proves this repaired fixture
projects and that the old fabricated `|-ability|p1a: Pikachu|Illusion` record
rejects before projection.

The static ability-record audit retained source-backed Ting-Lu/Vessel of Ruin
and Pressure evidence, contract acceptance/rejection fixtures, and persisted
negative review artifacts; the golden pair was the only invalid golden
projection fixture record. The manifest now hashes this fixture and its
focused test. Its computed local digest is
`ed88914a455d16e17f25e81e3e107706fbaf8bee0b6d75169b4aaf1b9451778b`, which
is **unreviewed**. No attestation or CE-04-CALLBACK-A acceptance is made.

### CE-04-CALLBACK-A scoped review verdict (2026-10-02): accepted

Review accepts the bounded public ability lifecycle surface: the exact 17
plain-reveal, 30 boost, 186 opposing-active Trace-copy, and 17 raw-only bare
compatibility domains; exact source/provenance grammar; public-only typed
projection; and Transform/form, departure, restoration, and Illusion privacy
boundaries. Static positive fixtures now use source-backed records, while
review-blocker and contract negatives remain rejection controls. TypeScript and
Python parity covers v1/v2, both perspectives, input/successor prefixes,
rollback, and no-output publication.

This attests local digest
`ed88914a455d16e17f25e81e3e107706fbaf8bee0b6d75169b4aaf1b9451778b` for
CE-04-CALLBACK-A only. The unrelated baseline `env_manager` settling failure,
item/status callbacks, other CE-04 families, CE-05, PIPELINE-002, and
`faithful_complete_episode:false` remain outside this verdict.

### CE-04-SLOTS Wish source lifecycle table (2026-10-01, implementation checkpoint)

Pinned `Moves.wish` (`data/moves.ts:21733-21763`) makes a slot condition through
`BattleActions` (`sim/battle-actions.ts:1258`). Its `onStart` stores half the
source maximum HP, the overflowed start turn, source and source slot in the
simulator condition state; none has a public protocol record. On the next
eligible residual it removes the condition at the current slot occupant and
only then, if that occupant is not fainted and receives HP, emits the exact
Wish heal record. The table deliberately distinguishes source-authorized
evidence from those private fields.

| Lifecycle fact | Pinned source/protocol behavior | Capture disposition |
|---|---|---|
| Activation | `move: Wish` is public; `slotCondition:'Wish'` then creates `side.slotConditions[position].wish`. | Retain the public `|move|<active>|Wish|<active>` record raw-only. Do not type a pending timer, source, recipient or amount. |
| Pending turns | `onStart` privately stores `hp`, `startingTurn`, source and `sourceSlot`; `onResidual` waits until the overflowed turn advances. | Retain activation raw evidence; keep the simulator condition only in owner-private restoration state. Omit all stored fields from observations, beliefs and records. |
| Source switch or drag | The condition belongs to the side position, so normal switch or drag changes the current occupant while the original source remains in condition state. | Retain ordinary public `switch`/`drag` and HP records. The next recipient is not typed from a forecast. |
| Source faint | A fainted original active cannot receive the delayed heal; its slot condition is removed during residual without a Wish `-heal` record. | Retain ordinary faint/replacement evidence. Omit cancellation cause, source state and any fabricated recipient/result. |
| Recipient switch, faint, drag or replacement | The current active slot occupant is the only possible on-end target. A fainted occupant receives no heal; a dragged or switched-in living occupant may receive it. | Existing typed HP applies only to an emitted `-heal`; retain source-qualified tags raw-only. No public pending-slot field persists after the source event. |
| Resolution | `onEnd` calls `heal(effectState.hp, target, target)` and, only for nonzero healing, emits `|-heal|<active>|<hp>|[from] move: Wish|[wisher] <source name>`. | Type the public target HP through the existing health path. Retain `[from]` and `[wisher]` as raw evidence. The wisher is not promoted into a typed link/source field. |
| Terminal boundary | A terminal result can occur before residual resolution. The simulator emits terminal evidence and no later Wish result. | Retain terminal raw/typed outcome through the existing path; omit an invented pending completion. |
| Restoration and v2 publication | Pipeline candidates restore the private condition from the authoritative snapshot while retaining the public prefix; public v2 records contain only the prefix, owned request and existing typed HP. | Owner-private snapshot state is never published. Deterministic v2 transitions retain the activation/outcome records and reject malformed rehashes before publication. |

The focused fixture uses the pinned engine for both acting sides and covers
pending-to-resolution, voluntary switch, drag, source faint, recipient faint,
replacement, terminal-before-resolution, candidate restoration, rollback and
Python publication. It verifies that existing extractor HP handling is the
only typed public effect. No pending Wish state, duration, source link,
recipient forecast or simulator snapshot is added to `ObservableBattleState`.

### CE-04-SLOTS `-heal` `[wisher]` source dependency table (2026-10-01, unreviewed repair checkpoint)

An exhaustive pinned-package search finds the one base-package emitter below.
The search also finds historical `data/mods/gen4` and custom `data/mods/gen9ssb`
copies; neither is on the `gen9randombattle` base-data path, so neither supplies
an additional allowed form.

| Pinned base-package emitter | Required `[from]` | Exact emitted field order | Gen 9 Random Battle reachability |
|---|---|---|---|
| `data/moves.ts:Moves.wish.condition.onEnd` (`21760`) | `[from] move: Wish` | `|-heal|<active target>|<health>|[from] move: Wish|[wisher] <source name>` | Reachable: `Moves.wish` is in the generated-set witness and its residual callback emits this record only after a nonzero heal. |

The shared contract now binds `[wisher]` to that sole source form. It rejects
missing, mismatched, reordered, duplicate and extra provenance tags before
TypeScript projection or Python publication; ordinary non-Wish `-heal` records
without `[wisher]` keep their existing grammar. The contract still retains the
two provenance fields raw-only and adds no public pending Wish state, timer,
source link, recipient forecast, request or snapshot. Mirrored v1/v2,
perspective and input/successor rehash controls preserve immutable candidate
state and lineage on rejection and emit no DATA-001 row. This is an unreviewed
repair checkpoint only. The local coverage digest
`9b7276277d51db992b2014b178e9dfad484aba92adbab750b54ac92200be763f` is
unreviewed; `reviewed_sha256` is unchanged. This does not attest CE-04-SLOTS, PIPELINE-002 or
`faithful_complete_episode:false`.

### CE-04-SLOTS Wish `[wisher]` scoped review verdict (2026-10-01): accepted

The pinned base-data inventory contains one operative `[wisher]` emitter:
`Moves.wish.condition.onEnd`, which emits exactly `[from] move: Wish` followed
by `[wisher] <source name>`. Historical Gen 4 and custom `gen9ssb` copies are
outside `gen9randombattle`. Shared TypeScript and Python validation now require
that complete pair and reject missing, mismatched, reordered, duplicate, extra,
and malformed forms before projection or publication; valid non-Wish heals
without `[wisher]` retain their existing grammar.

The v1/v2, p1/p2, and input/successor rehash controls retain raw-only Wish
provenance, candidate rollback, lineage preservation, and no-DATA-001
rejection. No pending Wish field, timer, source link, request disclosure, or
unrelated mechanic support was added. This review attests
`9b7276277d51db992b2014b178e9dfad484aba92adbab750b54ac92200be763f` for
CE-04-SLOTS Wish evidence only. CE-04-CALLBACK, other delayed-effect families,
CE-05, PIPELINE-002, and `faithful_complete_episode:false` remain outside this
verdict.

### CE-04-SHEDTAIL scoped review verdict (2026-10-01): accepted

Pinned `Moves.shedtail`, `BattleActions.switchIn`, and
`Pokemon.copyVolatileFrom(..., 'shedtail')` establish that the outgoing
Substitute start uses `[from] move: Shed Tail`, while only the incoming
replacement switch with the exact `[from] Shed Tail` suffix transfers the
public Substitute state. The extractor retains source-looking near misses as
raw evidence and does not project a typed transfer from them. The pinned
transfer copies Substitute only, skips boosts, and clears the departing
volatile state.

Focused fixtures prove both acting sides and both perspectives, later
Substitute end, drag/faint/terminal cleanup, privacy, v2 projection,
deterministic restoration, rejected forced-switch rollback, and Python
publication. All CE-04-SHEDTAIL implementation and test files are listed by
`local_coverage_sources`. This review attests
`14107dfaeb916b654b1acf376cf61226088abdc3fb6939d64098779f2f979d62` for
CE-04-SHEDTAIL only; it does not accept CE-04-LINK, CE-04-CALLBACK,
CE-04-SLOTS, CE-05, PIPELINE-002, or `faithful_complete_episode:false`.

### CE-04-LINK source lifecycle table (2026-10-01, implementation checkpoint)

| Source step | Pinned source and observed boundary | Public/state disposition |
|---|---|---|
| Create | `Moves.spiritshackle.secondary.onHit` calls `target.addVolatile('trapped', source, move, 'trapper')` only after a hit by an active source; Ghost immunity prevents it. | `|-activate|<target>|trapped` is raw evidence only. Neither `trapped` nor `trapper`, a link target, duration, or counter enters O/B. |
| Request | `Side.getRequestData` reports `active[0].trapped`; `buildLegalActionSet` reads only that addressed request. | The trapped owner has no voluntary switch actions; the source owner and opponent-facing public view receive no inferred link fact. |
| Release | `Pokemon.removeVolatile`, `removeLinkedVolatiles`, and `clearVolatile` unlink on source or target switch, faint, drag, replacement, and terminal cleanup. | The next target-owner request restores switches when a living bench exists. Public records retain only ordinary move/activate, departure, faint, drag, replacement, and terminal evidence. |

The focused fixture executes both acting sides, Ghost immunity, source departure,
target faint/drag/replacement, stale-action rollback, restored requests, raw
parser controls, and TypeScript/Python publication. The local coverage digest
is recorded in the PIPELINE checkpoint as **unreviewed**; this table does not
attest CE-04-LINK or change `faithful_complete_episode:false`.

### CE-04-LINK repair implementation checkpoint (2026-10-01, unreviewed)

The shared TypeScript/Python boundary now accepts trapped only as exact raw
`|-activate|<active>|trapped` evidence. It rejects fabricated `[of]` or
`[from]` source disclosures, labels, extra fields, side-only targets, and
whitespace-altered target/effect fields before projection or publication. The
rehashed rejection matrix covers both perspectives and input/successor v1/v2
prefixes, verifies immutable rejected candidates, and produces no DATA output.

The real pinned simulator fixture now explicitly produces
`observable-battle-state/v2` transitions for both Spirit Shackle actors. It
checks the trapped owner's request-only switch restriction, both published
successor perspectives, source departure/release, restored switch legality
only when the request permits it, independently restored twin sessions with
matching transition IDs/bundles/boundaries for trap and release, rejected
stale-action rollback, and Python publication without a foreign request or
trapper identity.

The focused checker computes
`21b05aa836b14a4019a91db9d619cc954af82063199205aa26cf63e4e01f6d34`.
That digest is **unreviewed**; stored/review digest fields remain unchanged.
This repair does not accept CE-04-LINK, PIPELINE-002, or change
`faithful_complete_episode:false`.

### CE-04-LINK source-faint evidence repair (2026-10-01, unreviewed)

The real v2 fixture now traps a live benched target, then uses the target's
ordinary Eruption turn to faint the active Spirit Shackle source. Pinned
`Pokemon.clearVolatile` removes the source `trapper` and its linked target
`trapped` volatile. The source owner's forced replacement is resolved first;
only the subsequent target-owner request restores `trapped:false`,
`can_switch:true`, and an eligible voluntary switch. Both actor sides compare
independently restored twins' link, faint, and replacement transitions,
bundles, and boundaries; every emitted bundle passes Python publication with
no raw request or trapper disclosure.

The computed local digest
`4398a8f03c730f43f0867477e71334555cda19641cd84ec9d74d8535ff0e3faa` is
**unreviewed**. Stored/review manifest fields remain unchanged; this evidence
does not accept CE-04-LINK, PIPELINE-002, or
`faithful_complete_episode:false`.

### CE-04-LINK source-faint scoped review verdict (2026-10-01): accepted

Pinned `Moves.spiritshackle` establishes the private `trapped`/`trapper` pair,
and `Pokemon.clearVolatile` removes linked volatile state when the active
source faints. The real v2 fixture covers both actor sides: a live target is
trapped, an ordinary Eruption turn faints the source, the source owner takes
the forced replacement, and only the next target-owner request restores an
eligible voluntary switch. It retains raw-only public activation evidence and
excludes trapper identity and raw request payloads from observations and
publication.

Independently restored twins have matching link, source-faint, and replacement
transition IDs, bundles, and successor boundaries. The pre-release target
switch rejects without changing the committed boundary; Python validates every
source-faint publication bundle. This review attests
`4398a8f03c730f43f0867477e71334555cda19641cd84ec9d74d8535ff0e3faa` for
CE-04-LINK only. It does not accept CE-04-CALLBACK, CE-04-SLOTS, CE-05,
PIPELINE-002, or `faithful_complete_episode:false`.

### CE-05-REPEAT Encore/repeat-use source lifecycle table (2026-10-02, implementation checkpoint)

The finite direct generated `cantusetwice` domain is Blood Moon and Gigaton
Hammer: `data/random-battles/gen9/sets.json:6345,6351` supplies Blood Moon and
`:6800,6806` supplies Gigaton Hammer. Both base move entries carry the
`cantusetwice` flag (`data/moves.ts:1587,6828`). The table records only this
bounded chain; it does not model generic locks or infer legality from public
text.

| Boundary | Pinned source behavior | Public/request disposition |
|---|---|---|
| Normal repeat restriction | `Battle.runEvent('DisableMove')` clears request move flags then disables a `cantusetwice` move when `pokemon.lastMove.id === moveSlot.id` (`sim/battle.ts:1601-1612`). | The next **owned** request marks Blood Moon or Gigaton Hammer disabled. No hint is emitted and no typed repeat/prohibition field is added. |
| Faster Encore override | `Moves.encore.condition.onStart` stores the eligible prior move and emits `|-start|<active target>|Encore`; `onOverrideAction` returns that stored move when a different action was queued (`data/moves.ts:4903-4924`). `BattleActions.runMove` receives the overridden ID before the repeat guard (`sim/battle-actions.ts:223-230`). | Existing public Encore evidence remains represented by its existing volatile handling. The originally requested alternate action is not retained as a public action mask or a new lock model. |
| Repeated-use hint | `BattleActions.runMove` adds the move-ID volatile only when the repeated active move has `cantusetwice` and then removes it after `useMove`; successful removal emits exactly one payload field: `|-hint|Some effects can force a Pokemon to use Blood Moon again in a row.` or `|-hint|Some effects can force a Pokemon to use Gigaton Hammer again in a row.` (`sim/battle-actions.ts:262-265,311-313`). | Exact raw-only evidence. Shared TypeScript/Python validation admits only those complete three-field records; tags, extra fields, whitespace, and invented move labels stop before projection or DATA-001 publication. |
| Next request / Struggle | Encore's `onDisableMove` disables every non-encored move. `Pokemon.getMoveRequestData` returns source-owned `Struggle` only when no moves remain (`sim/pokemon.ts:1051-1061`). | The owned request is the sole legal-action authority. `action_codec` preserves a request-supplied Struggle despite its absent PP field; it does not read the hint. |
| Expiry, switch, faint, terminal | Encore lasts three turns, ends early for unavailable PP, and emits `|-end|<active>|Encore` on removal (`data/moves.ts:4903-4935`). Standard volatile cleanup removes it at departure; terminal emits no future request. | Ordinary end/departure/faint/terminal evidence and the next owned request establish the boundary. No forecast, private Encore move, request, or simulator state is exported. A normal `cantusetwice` restriction may still apply when the final executed move is the same move. |
| Restoration and rejected retry | Pipeline candidates restore the authoritative snapshot and validate canonical actions against the current request before candidate execution. | Mirrored v2 twins preserve transition identity and prefix lineage. A stale disabled repeat action rejects without changing the committed boundary; both actual successor bundles publish through Python. |

The focused fixture executes both actor sides and both finite generated IDs. It
proves normal request disablement, a faster Encore overriding a different
queued move, the exact raw hint, the resulting source-owned Struggle request,
restored-twin deterministic continuation, retry rollback, private request
separation, and Python publication of actual v2 record bundles. The scope
excludes generic move-lock behavior, other Encore interactions, item callbacks,
Revival progression, CE-05 request-pair closure, training, complete-episode
acceptance, and any change to `faithful_complete_episode:false`.

The local coverage digest
`99af6315d68ff86879e2baf6cdbbd2ee0a01caa8a24779a0ca7f9e588cfe0bbc` is
**unreviewed**. Manifest attestation fields remain unchanged.

### CE-05-REPEAT scoped review verdict (2026-10-02): accepted

Focused review accepts the bounded generated Blood Moon/Gigaton Hammer
repeat-use chain. Pinned `cantusetwice`, `DisableMove`, Encore override, and
`getMoveRequestData` paths support the normal disabled owned request, the
faster forced repeat, the two exact raw-only `-hint` messages, and the later
owned Struggle request. The implementation does not infer action legality from
the hint. It validates malformed source-family records before projection or
publication, preserving candidate lineage and producing no DATA-001 output.

Mirrored p1/p2 v2 fixtures cover both generated IDs, both perspectives,
restored twins, deterministic continuation, stale-action rollback, private
request separation, and Python publication of actual transition bundles. The
reviewed local coverage digest is
`99af6315d68ff86879e2baf6cdbbd2ee0a01caa8a24779a0ca7f9e588cfe0bbc`.
Generic move locks, other Encore interactions, item callbacks, Revival
progression, CE-05 request-pair closure, training, PIPELINE-002, and
`faithful_complete_episode:false` remain outside this verdict.

### CE-05-REVIVAL pinned sequence table (2026-10-02, implementation checkpoint)

| Sequence boundary | Pinned source and Gen 9 singles guard | Public/request/progression disposition |
|---|---|---|
| Generated and copied user | `data/random-battles/gen9/sets.json` supplies Revival Blessing to Pawmot and Rabsca; generated Ditto supplies Imposter. `Moves.revivalblessing.onTryHit` requires a fainted party member, and `Abilities.imposter.onSwitchIn → Pokemon.transformInto` copies the active Pawmot/Rabsca move slots under its normal transform guards. | Pawmot/Rabsca are direct generated roots. The copied user receives no new revival action type: its addressed request enters the same bounded owner-only selector. Sleep Talk, active/fainted revivers, and multi-active cases remain excluded by B23/B24. |
| Create owner request | `Moves.revivalblessing` sets `slotCondition: 'revivalblessing'` and `selfSwitch`; `Battle.turnLoop` stops after `runAction` creates the switch request. `Side.chooseSwitch` accepts only a fainted `targetPokemon` for that slot condition. | The addressed owner receives `forceSwitch`, its own roster, the optional `reviving` flag, and finite fainted-bench `revive` actions. The other side receives its own `{wait:true}` request only; neither public O/B nor DATA-001 contains the owner request, target selection, or private roster data. |
| Consume selection and public outcome | `Battle.runAction('revivalblessing')` clears faint fields/status, restores half HP, emits split `|-heal|<side-only fainted bench target>|<health>|[from] move: Revival Blessing`, then removes the slot condition (`sim/battle.ts:2723-2740`). | Existing source-qualified bench `-heal` reconstruction is the only typed HP/status/faint effect. The public spectator half-HP record is retained; owner exact HP is private. Actor-only v2 record publication uses the consumed request and both successor perspectives. |
| Sequential opposite selection | `Battle.commitChoices` sorts the newly selected revive action before appending the saved queue; `BattleQueue.resolveAction` gives revival order 6. The first revive removes its slot condition, then the previously queued opposite Revival Blessing executes and pauses for the opposite owner. | There is never a combined selection API. The witness consumes p1 Pawmot's request, observes p2 Rabsca's subsequent request while p1 waits, then consumes p2's request and reaches an ordinary joint action boundary. Mirrored restored twins preserve cursor, transition, and branch identity. |
| Later play and terminal | The ordinary queue resumes after the final selection. A queued opposing terminal action may end the battle after a consumed selection; `checkWin` prevents a future request. | The fixture proves the next joint transition matches an independently restored twin and separately proves terminal observations have no fabricated request. Terminal envelopes remain CE-06. |
| Excluded variants | B24/B25 source guards exclude a fainted/inactive reviver, active-slot/instaswitch revival on this singles route, multi-active/doubles, simultaneous two-side selection, and generic waiting. | The selector stays fail-closed for those request shapes. No combined multi-revival API, active target, generic waiting, or broader episode claim was added. |

`tests/revival.test.ts` now exercises direct Pawmot/Rabsca actor sides, an
Imposter copied-user source shape, sequential opposite-side selections,
waiting-request privacy, rejected candidate rollback, restored v2 twins,
deterministic successor/ordinary continuation, terminal-after-selection, and
actual Python publication of each actor-only v2 bundle. The test file is
already included in `local_coverage_sources`; no production correction was
required. Focused TypeScript and Python validation passed. The local coverage
digest `1d5757be1d09c5ced11e260017f9e87cfc13045147a0de1adf3371db8d3bb1ce` is
**unreviewed**. Manifest attestation fields remain unchanged. This checkpoint
does not attest CE-05-REVIVAL, CE-05-BOUNDARY, PIPELINE-002, or
`faithful_complete_episode:false`.

### CE-05-REVIVAL scoped v2 progression review verdict (2026-10-02): accepted

The pinned singles path supports direct generated Pawmot/Rabsca and the bounded
Imposter-copied user: a living active user with an owner fainted bench member
creates one owner-only Revival Blessing selection. `Side.chooseSwitch` rejects
nonfainted targets, `turnLoop` pauses the saved queue, and the revival action
restores the selected fainted bench Pokémon before emitting its split
`-heal ... [from] move: Revival Blessing` consequence.

The accepted v2 witnesses cover both direct actor sides, the copied user,
sequential p1 then p2 selections, opposite-side wait privacy, rejected-choice
rollback, consumed-request restoration, deterministic twins, actual Python
actor-only bundle publication, a later ordinary joint transition, and a queued
terminal action with no fabricated request. The source order proves sequential
selection; simultaneous selection is not introduced. Active-target, inactive or
fainted reviver, multi-active/doubles, combined multi-revival, and generic
waiting variants remain explicitly excluded.

The reviewed local coverage digest is `1d5757be1d09c5ced11e260017f9e87cfc13045147a0de1adf3371db8d3bb1ce`. This accepts CE-05-REVIVAL
only; CE-05-BOUNDARY, CE-06 terminal-envelope closure, PIPELINE-002, and
`faithful_complete_episode:false` remain unaccepted.

### CE-05-BOUNDARY pinned singles request-pair table (2026-10-02, implementation checkpoint)

| Stable boundary | Pinned source path | Classification and bounded v2 evidence |
|---|---|---|
| Move + move | `Battle.endTurn → makeRequest('move')`; `getRequests` supplies a move request for each surviving side. `Side.chooseMove` and `allChoicesDone → commitChoices` require the two owned choices before `turnLoop` resumes. | **Supported and evidenced.** `pipeline_integration.test.ts` restores mirrored v2 candidates before consumption, rejects stale candidates without changing the boundary, then validates both actor bundles in Python with matching cursor, branch, transition, and successor identities. |
| Ordinary voluntary switch + switch | In the same `requestState === 'move'`, `Side.chooseSwitch` accepts a living benched target for each active, writes `choice: 'switch'`, and `commitChoices` executes the pair as ordinary joint choices. | **Supported and evidenced.** The direct v2 witness selects one owner-authorized voluntary `switch` action for each generated side; restored twins produce the same two bundles and identities, and Python validates both. It does not manufacture a switch or inspect the other owner's request. |
| Forced switch + wait | `checkFainted`/switch handling calls `makeRequest('switch')`; `getRequests('switch')` creates a switch request only for a side with a live flagged active, then substitutes `{wait: true}` for the other side. | **Supported and evidenced.** `forced_switch.test.ts` covers KO and pivot paths, both actor sides, candidate restore/rollback, actor-only publication, both successor perspectives, Python validation, and resumed joint play. |
| Revival selection + wait | `Moves.revivalblessing.selfSwitch` makes `turnLoop` stop after the living user's slot condition; `getRequests` supplies its switch request and the opposite `{wait:true}` request. `Side.chooseSwitch` permits only the owner's fainted bench target. | **Supported and evidenced.** `revival.test.ts` covers Pawmot/Rabsca, bounded Imposter copy, both owners, sequential opposite selections, consumed-request restoration, actor-only Python bundles, and the ordinary joint successor. |
| Terminal requestlessness | `Battle.win` sets `ended`, clears `requestState`, and nulls each `activeRequest`; `turnLoop` returns on `ended` before another request. | **Terminal-only.** Random-controller terminal and queued-terminal-revival witnesses restore matching terminal snapshots and perspectives with null requests. The consuming action's existing actor bundle is Python-validated; no terminal request payload or fabricated follow-up action is published. CE-06 retains terminal-envelope closure. |
| Move + wait, move + requestless, wait + wait, requestless + requestless, and nonwaiting empty action menu | For a successful nonterminal `makeRequest`, `getRequests` builds a request for every living side and replaces missing requests with `{wait:true}`. A side without Pokémon is resolved by `checkWin` before a new ordinary decision; `getMoveRequestData` supplies locked/recharge/Struggle instead of an empty menu. `turnLoop` runs synchronously until a request or terminal. | **Source-proven impossible stable pairs.** Partial channel delivery and a request already consumed by the engine are transport transients, not execution boundaries. Existing classifier guards stop them without inventing a wait/requestless action or a generic requestless executor. |

The focused closure adds only the real voluntary switch-plus-switch v2 witness;
the existing move-plus-move, switch-plus-wait, revival-plus-wait, and terminal
witnesses remain the direct dependencies named above. All covered tests use
the owner request as the sole action source. Neither opposite request payloads
nor request data enter the public prefix or DATA-001 output. The test files
were already present in `local_coverage_sources`; no production/request-classifier
change was required. The voluntary-switch witness serializes a real generated
engine boundary before consumption, starts both sessions from that serialization,
then serializes and restores the direct post-consumption state; both restored
v2 projections equal the original boundary at their respective cursors and
state fingerprints. Its fresh pipeline twins additionally bind the executed
transition/branch/successor identities and both Python bundles. The computed local digest
`3d65ae223bb5d9d3aadd7aaf6a3b35239b69c9c03b513e3ee7deb473de3161a8` is
**unreviewed**; manifest attestation fields remain unchanged. This is not CE-06, generic
waiting/requestless execution, doubles, team preview, a complete-episode
acceptance, or a change to `faithful_complete_episode:false`.

### CE-05-BOUNDARY scoped request-pair review verdict (2026-10-02): accepted

Pinned Gen 9 Random Battle singles separates stable engine boundaries from
partial delivery and consumed-request transport states. The accepted witnesses
cover owned move-plus-move, voluntary switch-plus-switch, forced switch-plus-wait,
and bounded Revival Blessing selection-plus-wait. Each uses only the addressed
owner request, preserves opposite-side request privacy, restores the consumed
request boundary, rejects stale candidates without changing lineage, and binds
deterministic cursors, transitions, branches, successors, and Python v2
publication. The direct voluntary switch-plus-switch witness restores both its
pre-consumption and post-consumption engine states.

`Battle.win` clears both active requests before `turnLoop` can create another
decision, so terminal requestlessness has matching null-request perspectives
but no fabricated action or request payload. Nonterminal move-plus-wait,
move-plus-requestless, all-wait, all-requestless, and nonwaiting empty-menu
states are source-proven impossible stable boundaries; they remain explicit
stops. Team preview, doubles, generic requestless execution, CE-06 terminal
envelopes, PIPELINE-002, and complete-episode acceptance remain excluded.

The reviewed local coverage digest is `3d65ae223bb5d9d3aadd7aaf6a3b35239b69c9c03b513e3ee7deb473de3161a8`.
This accepts CE-05-BOUNDARY only and leaves `faithful_complete_episode:false`.

### CE-04B Roost pinned lifecycle table (2026-10-02, implementation checkpoint)

| Lifecycle / interaction | Pinned source and supported-format route | Exact public evidence and boundary disposition |
|---|---|---|
| Generated roots | `data/random-battles/gen9/sets.json` contains Roost in 37 generated species rows: 26 dual Flying users (including Articuno, Zapdos, Moltres and Dragonite) and 11 non-Flying users. `RandomTeams.randomMoveset` selects from the retained row after normal set/team guards. There is no pure-Flying Roost row. | Direct generated roots exist. Articuno (`sets.json:952-963`) is the dual-Flying witness. No species/set identity is projected merely from a Roost record. |
| Successful ordinary Roost | `Moves.roost` (`data/moves.ts:16003-16031`) heals, adds `volatileStatus: 'roost'`, then `condition.onStart` emits `|-singleturn|<active actor>|move: Roost` unless the user is Terastallized. `onType` saves private `effectState.typeWas` and filters `Flying`. | The exact existing `-singleturn` record is retained **raw-only**. The ordinary `-heal` remains the existing typed public HP evidence. There is no `-typechange`, `-start roost`, `-end roost`, public duration, or public `typeWas` record. The test proves a slower Earthquake hits an ordinary dual-Flying Articuno during the same turn while the next request shows `Ice/Flying` again. |
| End of turn / next capturable request | `Battle.turnLoop` queues residual after move actions (`sim/battle.ts:2881-2895`); residual calls `fieldEvent('Residual')` (`2753-2760`), and the duration handler decrements the Roost state and invokes its end before a later request (`battle.ts:514-520`). | The temporary filter is gone before any stable request, v2 boundary, cursor, successor or terminal observation. Existing public defensive types therefore remain authoritative; no typed temporary-type field or expiry reconstruction is needed. |
| Tera | `Moves.roost.condition.onStart` returns false for a Terastallized user and, only when it still has Flying, emits `|-hint|If a Terastallized Pokemon uses Roost, it remains Flying-type.` Empoleon's generated Bulky Support row has both Roost and `teraTypes: ["Flying", "Grass"]` (`sets.json:2688+`). | This is a direct generated Tera-Flying route. It emits the existing raw diagnostic, never `-singleturn`, and leaves the already-public Tera defensive type authoritative. The mirrored Empoleon fixture validates both v2 perspectives and Python bundles. |
| Soak and one added type | Roost's `onType` receives the current internal type list, so it would filter Flying after an independently active type replacement/addition. This slice found no generated Soak or Forest's Curse movepool root, and does not claim a generated co-occurrence/call chain from their absence alone. | Existing accepted Soak/added-type reconstruction remains separate. No Roost-specific type-event grammar, inference, or fixture is added without the missing supported-format indirect route proof. |
| Transform / copied user | Generated Ditto's row supplies `Transform` plus `Imposter` (`sets.json:867-875`), while Articuno supplies Roost (`946-956`). A slower generated U-turn pivot can act after faster Articuno Roost and pause for its own replacement before residual. Ditto's `Imposter.onSwitchIn → transformInto` then reads the live target `roost.typeWas` (`data/abilities.ts:2055-2067`; `sim/pokemon.ts:1216-1242`). `BattleActions` finishes that replacement before residual. Earlier residual handlers can still call `faintMessages()` before Roost's order-25 expiry; the dedicated residual witness below covers that path. | The mirrored v2 witness is the source path: `|-singleturn|<Articuno>|move: Roost`, then U-turn replacement, then `|-transform|<Ditto>|<Articuno>|[from] ability: Imposter`; residual expires Roost before the successor request. Both public active types are `Ice/Flying` after Transform. A later source-shaped switch and Rock hit faint the already transformed Ditto; its public fainted bench state is native `Normal`, with no `typeWas`. `typeWas` stays simulator-private; no mutable type link or new Transform support is added. |
| Illusion | Generated Zoroark has Illusion but no generated Roost row. No source-proven generated chain putting active Roost under an unrevealed Illusion was established in this slice. | Explicit unsupported stop; existing `replace`/`-end … Illusion` behavior remains unchanged. No hidden identity or inferred type enters either perspective. |
| Switch, drag, faint, replacement and terminal | Roost duration is consumed during the same turn's residual. The active-Roost Imposter fixture then makes the copied Ditto leave, uses the source-shaped Rock hit to faint it, and consumes the owner-only replacement request; `faintMessages`/switch lifecycle executes before that request. Ordinary switch, drag and terminal delivery contain their existing public records only. | Both perspectives retain the public `faint`, native Normal bench type and owner-only replacement result, never `typeWas`, raw requests or hidden identity. There is no stale Roost typed state to clear at a capturable boundary. This slice adds no generic temporary-type or lifecycle cleanup model. |
| Reflect Type and other temporary type effects | B32 records no generated Reflect Type root or indirect entry. | Excluded. This Roost proof does not widen temporary-type support. |

`tests/roost.test.ts` adds mirrored p1/p2 simulator-backed
`observable-battle-state/v2` witnesses. They prove the ordinary dual-Flying
same-turn defense change, the post-residual native type at the next request,
raw-only `-singleturn` handling, generated Empoleon's Tera-Flying exception,
and the generated Articuno Roost → slower U-turn → Ditto/Imposter Transform
branch. Because residual completes before the next move request, it then uses
the first source-valid later faint path: source departure, Rock-hit Ditto faint,
and its owner-only replacement. The fixture restores serialized pre- and
post-faint requests, validates their actual v2 bundles in Python, rejects
stale candidates without committing, and continues deterministically through
ordinary switch and Whirlwind drag cleanup that return Ditto to public Normal
typing.
The target-side fixture also retains an unrevealed Zoroark/Illusion bench control:
the Ditto observer never receives that hidden roster identity. No output contains
`typeWas` or raw `|request|` data. No production code or new
accepted protocol grammar was necessary. The coverage manifest classifies
`roost` as raw-only and lists the focused test; `sha256` and `reviewed_sha256`
remain unchanged. The resulting local coverage digest is
`13023945c453d8dd5a312487edb5482fe2d7ac74f58bae2f62723f14bd6c0ad2`,
**unreviewed**; CE-04B
does not accept generic temporary types, offensive calculation, Soak/added-type
co-occurrence, Transform type links, Illusion inference, Reflect Type, doubles,
or complete-episode delivery.

### CE-04B Transform/Roost review repair (2026-10-02, unreviewed)

The former review blocker is closed by the source-shaped U-turn replacement
witness above. It reaches the private `roost.typeWas` branch while Roost is
live, proves the source-restored request and both mirrored actor sides, and
observes only the source-authorized post-residual public `Ice/Flying` result.
It does not promote `typeWas`, a temporary type, or an Illusion identity into
typed state. CE-04B remains unreviewed pending its separate scoped review.

### CE-04B active-Transform faint repair (2026-10-05, unreviewed)

Pinned move ordering rules out an intervening successor move after this
Imposter replacement: `onSwitchIn → transformInto` completes inside the U-turn
replacement, then residual completes before the next actionable request. This
later-faint witness covers the first move-request path: copied Ditto remains public `Ice/Flying` through
source departure, then a Rock hit emits its public faint and leaves its bench
view native `Normal`, non-active and non-transformed. Pre- and post-faint
serialized twins have matching state fingerprints and transition identities;
wrong-rqid requests roll back; consumed owner-only replacement and later
continuation publish in Python. Neither perspective nor a bundle contains
`typeWas`, raw `|request|`, or the unrevealed Zoroark identity. No production
code, generic Transform/type feature, manifest attestation field or new grammar
changed. The local digest is `13023945c453d8dd5a312487edb5482fe2d7ac74f58bae2f62723f14bd6c0ad2`, **unreviewed**.

### CE-04B active-Transform faint review finding (2026-10-05): superseded

The earlier no-interleaving proof was insufficient; the following residual-KO repair supersedes this finding. `Battle.fieldEvent('Residual')`
sorts all field, status, and volatile handlers and calls `faintMessages()` after
each handler (`sim/battle.ts:477-533`). Sandstorm has
`onFieldResidualOrder: 1` and damages active non-immune Pokémon
(`data/conditions.ts:620-659`); poison and toxic use residual order 9
(`data/conditions.ts:127-160`); Roost expires at residual order 25
(`data/moves.ts:16016-16030`). Therefore a sufficiently damaged Ditto that
has already transformed into the active Roost target can faint from an earlier
residual handler before Roost's duration is removed. Generated Gen 9 rows
include both Toxic Spikes and Sand Stream roots, so the current later Rock-hit
witness cannot prove this residual family absent. The required replacement is a
mirrored simulator-backed v2 witness with a source-backed pre-damaged Ditto and
an earlier residual KO, followed by the public faint/replacement, restoration,
rollback, and Python-publication checks. Do not attest CE-04B until that
witness or an equally complete generated-route exclusion exists.

### CE-04B pre-Roost-expiry residual-KO repair (2026-10-05, unreviewed)

This entry supersedes the preceding no-interleaving assertion and unresolved
finding. Pinned `Battle.fieldEvent('Residual')` invokes `faintMessages()` after
each sorted handler. Generated Tyranitar's Sand Stream is order 1
(`conditions.ts:620-659`; generated row `sets.json:1808+`), while Roost expires
at order 25 (`moves.ts:16016-16030`). The mirrored p1/p2 v2 witness pre-damages
Ditto, establishes that Sand Stream root, returns Articuno and damages it so
Roost succeeds, then uses slower U-turn to make Ditto/Imposter transform while
private `roost.typeWas` is live. The direct source log orders exact public
`-transform`, `-weather|Sandstorm|[upkeep]`, and copied-Ditto `faint`; the
order-1 handler therefore faints it before Roost expiry.

At the forced pre-replacement boundary both public views show the Roost target
as `Ice/Flying`. After residual faint, they retain that active target type and
show copied Ditto as fainted, non-active, non-transformed, native `Normal`.
Serialized pre-consumption and post-faint twins restore matching public state;
same-lineage twins match transition identities; stale forced candidates roll
back; owner-only replacement and ordinary continuation publish actual Python
v2 bundles. No observation or published bundle includes `typeWas`, raw request
payload, or the opponent's unrevealed Zoroark identity.

Poison and toxic are generated Toxic Spikes roots and residual order 9
(`conditions.ts:127-160`; `moves.ts:20515-20547`). Their status/damage records
are distinct existing evidence, but they invoke the same `faintMessages()`
before Roost's order-25 end and have the identical CE-04B public type cleanup.
They require no duplicate type-lifecycle fixture. No production code, generic
residual model, generic Transform or temporary-type support, Reflect Type,
offensive calculation, or manifest attestation changed. The local digest is
`bf4c57ae0745d28c7d2d9dd9bf0999e753c53fe6c26e12e12eedf13c3e11a1f4`, **unreviewed**.

### CE-04B Roost and active-Transform scoped review verdict (2026-10-05): accepted

Pinned residual ordering confirms that the generated Sand Stream witness is a
reachable pre-Roost-expiry faint: its order-1 field handler damages the
transformed, pre-damaged Ditto and `Battle.fieldEvent` immediately runs
`faintMessages()`, before Roost's order-25 duration end. Generated Toxic Spikes
supplies poison and toxic order-9 roots. Their distinct public status and damage
records already have their own representation; they share this slice's same
faint, transform-clear, and defensive-type cleanup, so no second Roost type
witness is required.

The mirrored v2 fixture covers both actor directions, public target type and
Ditto HP/faint/native-Normal cleanup, owner-only replacement, restored twins,
deterministic continuation, stale-candidate rollback, privacy, and actual
Python transition-bundle publication. It exposes neither `roost.typeWas`, an
unrevealed identity, a request payload, nor a simulator snapshot. No generic
residual, Transform, temporary-type, Reflect Type, or offensive-calculation
behavior entered the slice. Focused TypeScript validation passed 76/76 tests;
Python publication validation passed 34/34. The coverage-hashed local digest
`bf4c57ae0745d28c7d2d9dd9bf0999e753c53fe6c26e12e12eedf13c3e11a1f4` is
attested for CE-04B only.

### CE-04D1 public entry-hazard layer source table (2026-10-05, accepted scoped closure)

| Family / generated roots | Public records and count | Pinned lifecycle and bounded disposition |
|---|---|---|
| Spikes | `|-sidestart|<side>|Spikes` once per layer; `|-sideend|<side>|Spikes|[from] move: Rapid Spin/Mortal Spin/Defog|[of] <active>` or untagged Tidy Up | `Moves.spikes.condition.onSideStart/onSideRestart` starts at 1 and emits through cap 3; fourth `addSideCondition` returns false and emits no start. Grounded, non-Boots switch-in damage occurs in `onSwitchIn`. Direct generated setters include Skarmory/Sandslash/Quagsire; Ceaseless Edge is generated and reaches the same condition. Typed public count 0–3 is represented. |
| Toxic Spikes | `|-sidestart|<side>|move: Toxic Spikes` once per layer; same tagged/untagged removal grammar; absorbing Poison emits `|-sideend|<side>|move: Toxic Spikes|[of] <active>`; a grounded non-Poison/non-Steel/non-Boots switch-in emits `|-status|<active>|psn` at one layer or `|-status|<active>|tox` at two | `Moves.toxicspikes.condition.onSwitchIn` branches on `effectState.layers`: Poison removes all, Steel/Boots do nothing, two sets tox, and one sets psn. Direct generated Ariados roots the setter. Mirrored p1/p2 v2 switch witnesses retain count 1/2 and public status, restore the pre-switch snapshot, reject stale candidates, and publish actual bundles through Python. No timer/source/item/set data is represented. |
| Stealth Rock | `|-sidestart|<side>|move: Stealth Rock`; same tagged/untagged removal grammar; on switch-in `|-damage|<active>|<HP>|[from] Stealth Rock` with no extra tag | `Moves.stealthrock.condition` has no restart callback: duplicate application emits no start and remains count 1. `onSwitchIn` computes type effectiveness then calls `damage`, whose public record is the existing HP evidence. Generated Skarmory roots the mirrored p1/p2 v2 Charizard witnesses; each proves exact source tag, reduced public HP, retained layer, restored-twin identity, rollback, and Python publication. |
| Sticky Web | `|-sidestart|<side>|move: Sticky Web`; same tagged/untagged removal grammar; grounded, non-Boots switch-in emits `|-activate|<active>|move: Sticky Web` followed by `|-unboost|<active>|spe|1` | `Moves.stickyweb.condition` has no restart callback: duplicate application emits no start and remains count 1. `onSwitchIn` calls `add(-activate)` then `boost({spe: -1})`, so normal Battle boost emission produces the exact public speed-stage line. Generated Ariados roots mirrored p1/p2 v2 witnesses for both public records, own/public-opponent stage projections, restore/rollback, and Python publication. |
| Removal / scope | Rapid Spin, Mortal Spin and Defog use ordered `[from] move: …|[of] <active>` side-end records; Tidy Up uses an untagged end. | `Moves.rapidspin`, `mortalspin`, `defog`, and `tidyup` call `Side.removeSideCondition`; side ownership is public and both perspectives get the same layer map. Court Change is generated but `-swapsideconditions` is explicitly excluded; screens, weather, terrain, pseudo-weather, G-Max hazards, doubles, and generic swapping remain outside CE-04D1. Side conditions persist across ordinary switch/faint and are cleared only by an emitter; terminal/restoration retain only public prefix/count state. |

The prior extractor had no caps, and shared validators accepted arbitrary hazard spellings/tags. CE-04D1 adds exact source-form validation and bounded caps before TypeScript projection/Python publication. `tests/entry_hazard.test.ts` supplies pinned-engine cap, duplicate, Rapid Spin, Mortal Spin, Defog, Tidy Up, Poison absorption, and switch-in witnesses plus mirrored p1/p2 v2 restoration, deterministic transition, rollback, privacy and publication controls. The added successor witnesses cover each distinct public switch-in result: Stealth Rock damage, Sticky Web activation plus speed stage, and one-/two-layer Toxic Spikes psn/tox. They share no hidden state with the public result: neither source/timer/item/set inference, request, nor simulator snapshot is typed. No new protocol rule is needed because the exact public HP, status, activation, and stage record grammars were already shared validated forms. The computed coverage digest is recorded as unreviewed below after the checker; no manifest digest field is changed by this checkpoint. Computed local coverage digest: `f302c335197264979d898e7db62828934d5100aff474bef3212de06124207fe0` (unreviewed).

**CE-04D1 scoped verdict (2026-10-05, accepted):** Review verified the pinned `Moves.stealthrock`, `stickyweb`, and `toxicspikes` switch-in ordering and the direct generated roots. The mirrored p1/p2 v2 fixtures prove Stealth Rock damage, Sticky Web activation then Speed drop, and one-/two-layer Toxic Spikes `psn`/`tox`, with retained public layers, private requests, restored-twin deterministic identities, rollback, and Python publication. Cap, duplicate, removal, and Poison-absorption evidence remains intact. Digest `f302c335197264979d898e7db62828934d5100aff474bef3212de06124207fe0` is attested only for CE-04D1; screens, weather, terrain, Court Change, generic side swapping, doubles, private hazard/source state, and complete-episode claims remain outside this verdict.

### CE-04E1 public weather-state source lifecycle table (2026-10-05, unreviewed)

| Lifecycle / generated root | Exact public evidence and typed result | Private or excluded state / disposition |
|---|---|---|
| Direct move set or replacement | `|-weather|RainDance`, `|-weather|SunnyDay`, or `|-weather|Snowscape` only; `BattleActions` calls `Field.setWeather` for the move's `weather` property. Generated rows supply Rain Dance, Sunny Day, Snowscape, and Chilly Reception (the latter also switches). Each immediately replaces the represented field ID, without a fabricated intervening `none`. | Duration and Weather Rock item extension remain `Field.weatherState` only. Sandstorm has no generated direct move root, so its untagged start is rejected. |
| Ability set or replacement | `|-weather|<RainDance\|SunnyDay\|Sandstorm\|Snowscape>|[from] ability: <Drizzle\|Drought\|Orichalcum Pulse\|Sand Stream\|Snow Warning>|[of] <p1a/p2a active>`; `Conditions.<id>.onFieldStart` emits the tags in that order. Generated ability rows root all five forms. | The active source is raw provenance, not a typed weather source. No source slot, hidden ability, or duration enters the field view. |
| Upkeep and expiry | `|-weather|<four generated IDs>|[upkeep]` precedes the weather callback at field residual order 1. At duration expiry, `Field.clearWeather → Conditions.<id>.onFieldEnd` emits exactly `|-weather|none`; extraction sets typed `field.weather` to `null`. | Weather damage remains existing public HP evidence only; no weather-damage model was added. Item-dependent duration is omitted. |
| Suppression, switch, faint, and form | Generated Air Lock and Cloud Nine emit their ordinary public `-ability` confirmation and call `WeatherChange`; `Field.suppressingWeather/effectiveWeather` suppress mechanics while retaining `Field.weather`. The public field ID therefore remains the actual represented weather and no `-weather|none` is emitted. Ordinary weather can persist across source switch/faint until its normal duration; weather-setting ability re-entry may emit a tagged replacement. | There is no public `weather_suppressed` field: suppression is neither removal nor a distinct `-weather` record. Ability/item identity beyond separately public ability evidence, source/slot, and callback state remain absent. |
| Terminal and restoration | A terminal after Drought retains its preceding public SunnyDay evidence and terminal result; it does not invent a FieldEnd clear. Mirrored p1/p2 v2 fixtures restore from the consumed Rain Dance state, execute Cloud Nine suppression, match twin transition identities/fingerprints, reject stale rqids without mutation, and publish the actual successor bundles through Python. | Requests, split-private HP, simulator snapshots, and `weatherState` never appear in observations or DATA-001. Terrain, pseudo-weather, generic field effects, doubles, and complete-episode claims remain excluded. |

`Conditions.raindance/sunnyday/sandstorm/snowscape` define the four public
weather records, upkeep, and `none` end (`data/conditions.ts:472-718`);
`Field.setWeather/clearWeather` preserves replacement versus clear behavior
(`sim/field.ts:39-98`). `Moves` and generated `sets.json` establish the direct
Rain Dance/Sunny Day/Snowscape/Chilly Reception roots and the Drought,
Drizzle, Sand Stream, Snow Warning, and Orichalcum Pulse roots. Air Lock and
Cloud Nine (`data/abilities.ts:90-104,537-551`) prove suppression without
weather removal. `tests/weather.test.ts` adds direct source-engine and mirrored
v2 evidence for set, replacement, upkeep, suppression, expiry, terminal,
restoration, deterministic same-lineage continuation, rollback, privacy, and
Python publication. The shared TypeScript/Python contract now accepts only the
four generated IDs and their exact move, ability-active, upkeep, and clear
forms before projection/publication; malformed or historical weather forms
stop. No production extractor change was required because it already retained
the public ID and `none` clear without projecting private state. The computed
coverage digest is recorded as unreviewed below; no manifest attestation field
is changed by this slice. Computed local coverage digest:
`a2c6b2a3a424c74d6d1241c5990174d1d227f462be40a494057243b9482ab9fa`
(unreviewed).

**CE-04E1 scoped verdict (2026-10-05, accepted):** Review verified the four
generated weather IDs and their exact move, ability-active, upkeep, and clear
forms against pinned `Conditions` and `Field` sources. The p1/p2 v2 fixtures
retain the actual weather ID across direct replacement and Cloud Nine
suppression, without representing a suppression field or fabricating a clear;
they also prove restored-twin deterministic transition identity, rollback,
privacy, and Python successor publication. Weather duration, raw source
provenance beyond the retained record, hidden ability/item, request, split HP,
and simulator state remain absent from typed/public records. Digest
`a2c6b2a3a424c74d6d1241c5990174d1d227f462be40a494057243b9482ab9fa` is
attested only for CE-04E1. Terrain, pseudo-weather, generic field effects,
weather damage modeling beyond public HP records, doubles, and complete-episode
acceptance remain outside this verdict.

**CE-04E1 baseline-fixture repair verdict (2026-10-05, accepted):** The
`simulator_coverage.test.ts` inventory fixture had a stale synthetic lowercase
`|-weather|raindance` spelling. Pinned `Conditions.raindance.onFieldStart`
emits the case-sensitive public record `|-weather|RainDance`; `Moves.raindance`
sets `weather: 'RainDance'`, and `Field.setWeather` dispatches that condition.
The lowercase spelling was therefore not a missing tagged form or an operative
record: it is reclassified as a stale synthetic fixture and replaced with the
source-emitted spelling. The shared contract remains unchanged. TypeScript and
Python controls now both reject lowercase `raindance` before projection or
publication while accepting `RainDance`; duration and Weather Rock state remain
private, and suppression remains outside the weather-record grammar. The
attested local coverage digest is
`b778e062f3934444adec94fc865fd6840d1514cc4551a818ae5c5701dde4151d`.
The focused weather suite, checker, checker self-test, and Python record suite
pass. The aggregate coverage fixture's separate lowercase `electricterrain`
record still fails under CE-04E2's unreviewed terrain grammar; it does not alter
this weather-only attestation.

### CE-04E2 public terrain-state source lifecycle table (2026-10-05, unreviewed)

| Lifecycle / generated root | Exact public evidence and typed result | Private or excluded state / disposition |
|---|---|---|
| Electric Terrain set or replacement | Pincurchin `Electric Surge` and Miraidon `Hadron Engine` call `Field.setTerrain('electricterrain')`; the pinned condition emits exactly `|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge\|Hadron Engine|[of] <p1a/p2a active>`. The typed public field ID becomes `electricterrain`. | `Field.terrainState` retains source, slot, duration, and Terrain Extender result. Those values, ability membership beyond the retained raw record, requests, and snapshots remain private. |
| Grassy Terrain set or replacement | Rillaboom `Grassy Surge` on start and Arboliva `Seed Sower` after a damaging hit emit exactly `|-fieldstart|move: Grassy Terrain|[from] ability: Grassy Surge\|Seed Sower|[of] <p1a/p2a active>`. The typed public field ID becomes `grassyterrain`. | The Seed Sower hit/callback inputs are private. Its public HP consequence, if emitted, remains existing `-heal` evidence rather than terrain-specific typed mechanics. |
| Psychic Terrain set or replacement | Generated Indeedee/Indeedee-F `Psychic Surge` emits exactly `|-fieldstart|move: Psychic Terrain|[from] ability: Psychic Surge|[of] <p1a/p2a active>`, producing `psychicterrain`. | Psychic priority/blocking behavior is not inferred from terrain; owned simulator requests remain the sole legal-action authority. |
| Replacement, expiry, and actual clear | `Field.setTerrain` overwrites the previous terrain and invokes the new `FieldStart` without an intervening FieldEnd. Each reachable condition expires through `Field.clearTerrain → Condition.onFieldEnd`, emitting exactly untagged `|-fieldend|move: Electric\|Grassy\|Psychic Terrain>`. Generated Ice Spinner and Defog call `clearTerrain`; Teraform Zero has the same clear path when its generated form route has an existing terrain. Extractor clears only the matching typed ID. | The duration countdown and clear cause are not public field state. Misty Terrain has no generated M/A/I root, so its start/end spellings reject in this slice. |
| Switch, faint, form, terminal, and suppression | Terrain belongs to `Field`, so ordinary setter switch/faint/form changes do not emit a terrain clear; re-entry can emit a source-backed replacement only if `setTerrain` changes ID. Terminal completion does not call FieldEnd or fabricate a clear. `Field.effectiveTerrain` can suppress mechanics per event target, but pinned terrain code emits no distinct public terrain-suppression record or state; typed public state remains the actual field ID. | No `terrain_suppressed`, timer, setter identity, callback input, request, split-private HP, or simulator state is projected. Pseudo-weather, generic terrain effects, doubles, and complete-episode claims remain excluded. |

Pinned `Field.setTerrain/clearTerrain` (`sim/field.ts:130-166`) establishes direct replacement versus the sole clear callback path. `Moves.electricterrain/grassyterrain/psychicterrain` define exact ability-tagged FieldStart and untagged FieldEnd strings (`data/moves.ts:4701-4712,7982-8002,14679-14690`). The operative `gen9` set generator contains Pincurchin/Electric Surge, Rillaboom/Grassy Surge, Indeedee/Indeedee-F/Psychic Surge, Arboliva/Seed Sower, and Miraidon/Hadron Engine; it contains no direct terrain move or Misty Surge/Misty Terrain root. Generated Ice Spinner and Defog prove physical clear routes, while Teraform Zero reuses `clearTerrain` without a distinct public form. `tests/terrain.test.ts` directly checks all five setter callbacks, natural expiry, Ice Spinner clear, terminal preservation, and mirrored p1/p2 v2 Electric-to-Grassy replacement/clear continuations. It restores independent twins, requires matching transition IDs/fingerprints, rejects stale candidates before mutation, preserves request privacy, and publishes actual bundles through Python.

CE-04E2 adds exact shared TypeScript/Python terrain forms before extraction and DATA-001 publication: only the three IDs above, their finite ability provenance, an active canonical `[of]` role, ordered fields, and untagged matching end records. It rejects direct/missing/reordered/duplicate/extra forms, side-only/doubles/whitespace identifiers, Misty Terrain, and generic terrain spellings across v1/v2, p1/p2, input/successor rehashed candidates with no output or lineage advance. The existing extractor already represented the public field ID correctly, so no production extractor change was needed. Computed local coverage digest: `cb6a971ed3bf7706a6a268c3f93ba8e1068545e786bc835bebdf5b517cf395a7` (unreviewed; manifest attestation fields unchanged).

**CE-04E2 scoped verdict (2026-10-05, accepted):** Review verified the finite generated singles terrain source family: Electric Terrain from Electric Surge or Hadron Engine, Grassy Terrain from Grassy Surge or Seed Sower, and Psychic Terrain from Psychic Surge. The only accepted field records are their ordered active-source `-fieldstart` forms and the individual untagged `-fieldend|move: Electric Terrain`, `-fieldend|move: Grassy Terrain`, and `-fieldend|move: Psychic Terrain` clear forms. Replacement emits only the next FieldStart; expiry and generated clear routes emit the matching FieldEnd; terminal delivery preserves the current public field ID without fabricating a clear. Mirrored p1/p2 v2 fixtures, restored twins, stale-candidate rollback, private request boundaries, and Python successor publication passed. The public view retains only the source-emitted terrain ID and omits duration, source state, callbacks, requests, and simulator state. Digest `cb6a971ed3bf7706a6a268c3f93ba8e1068545e786bc835bebdf5b517cf395a7` is attested only for CE-04E2; pseudo-weather, generic terrain mechanics, action inference outside owned requests, doubles, and complete-episode claims remain outside scope.

**CE-04E2 aggregate coverage-fixture repair checkpoint (2026-10-05, unreviewed):** The aggregate effect-inventory fixture's compact `|-fieldstart|electricterrain` record was stale synthetic input. Pinned `Moves.electricterrain.condition.onFieldStart` emits the source-shaped `|-fieldstart|move: Electric Terrain|[from] ability: Electric Surge|[of] p1a: Pincurchin` record when the generated Electric Surge root calls `Field.setTerrain('electricterrain')`; there is no generated compact terrain emitter. The fixture now uses that exact emitted terrain record. The existing shared TypeScript/Python CE-04E2 matrices retain the accepted source-shaped forms and reject the compact, source-less form before extraction or DATA-001 publication. This changes no terrain grammar, finite IDs, public state, duration/source/request boundary, generic terrain support, or manifest attestation field. Computed local coverage digest: `9f88b5ebdba384722bd38351f09dfbd617907f3ced85fa9363ab26f8e5a40a0a` (unreviewed).

**CE-04E2 aggregate coverage-fixture repair verdict (2026-10-06, accepted):** Review verified that the source-shaped Electric Surge record is the sole applicable generated form and that the existing finite TypeScript/Python terrain grammar continues to reject the compact source-less form before projection or publication. The pinned `pokemon-showdown@0.11.10` terrain emitter and `gen9randombattle` roots remain bound; duration, source state, requests, split-private HP, and simulator state remain excluded. Build, focused terrain/protocol suites, the Python record suite, and checker self-tests passed. The aggregate fixture now reaches a separate stale Glaive Rush typed-volatile assertion: the current inventory intentionally classifies Glaive Rush as raw-only, so that assertion neither evaluates nor invalidates the terrain record. It does not block this fixture-only terrain attestation. Digest `9f88b5ebdba384722bd38351f09dfbd617907f3ced85fa9363ab26f8e5a40a0a` is attested only for this CE-04E2 aggregate-fixture repair; terrain grammar, typed state, generic terrain mechanics, doubles, PIPELINE-002, and complete-episode claims remain unchanged.

### CE-04E3 public Trick Room pseudo-weather source lifecycle table (2026-10-05, unreviewed)

| Lifecycle / generated root | Exact public evidence and typed result | Private or excluded state / disposition |
|---|---|---|
| Set | Generated Slowbro-Galar, Trevenant, Calyrex-Ice, and Rabsca `Trick Room` rows call `Field.addPseudoWeather('trickroom')`. `Moves.trickroom.condition.onFieldStart` emits exactly `|-fieldstart|move: Trick Room|[of] <p1a/p2a active>` and the existing public extractor retains only `field.pseudo_weather: trickroom`. | `Field.pseudoWeather.trickroom` retains duration, source, and sourceSlot; the `[of]` value is retained raw provenance only, not a typed setter field. Persistent can add `[persistent]` in the base callback, but no operative generated Persistent route exists, so that form rejects. |
| Reapplication / clear | While active, `Field.addPseudoWeather` calls `onFieldRestart`; `Moves.trickroom.condition.onFieldRestart` calls `Field.removePseudoWeather('trickroom')`, whose `onFieldEnd` emits exactly tagless `|-fieldend|move: Trick Room`. It clears the public ID and emits no replacement start. Natural residual expiry takes the same `onFieldEnd` path. | No public duration, countdown, reapplication source, or forecast is represented. Other pseudo-weather IDs retain their existing independent disposition and are not added by this slice. |
| Order, switch, faint, and terminal | `Pokemon.getActionSpeed` reads private field state and reverses speed during actual queue ordering. The public field record is evidence only; legal actions and execution order remain derived from owned requests and real transitions. Field-owned Trick Room persists across ordinary setter switch/faint/form changes. Terminal completion does not invoke FieldEnd or fabricate a clear. | No priority/speed model, legal-action mask, source identity beyond raw public evidence, request payload, snapshot, or simulator `pseudoWeather` state is exported. |
| Restoration / publication | Mirrored p1/p2 v2 fixtures start the exact record, prove a slower source move appears first on the next actual Trick Room turn, restore twins after request consumption, then reapply for exact clear. They require matching transition IDs/fingerprints, preserve boundary state on stale rqid rejection, and publish actual successor bundles through Python. | Pseudo-weather engine generalization, other IDs, doubles, and episode-completion claims remain excluded. |

Pinned `Moves.trickroom` (`data/moves.ts:20719-20751`) establishes the exact start, restart, residual order, and end callbacks; `Field.addPseudoWeather/removePseudoWeather` (`sim/field.ts:186-230`) establishes the reapplication removal path; and `Pokemon.getActionSpeed` (`sim/pokemon.ts:617-624`) establishes that the observed move ordering comes from private field state during actual queue execution. The operative Gen 9 Random Battle sets contain the listed Trick Room move roots and no generated Persistent root. `tests/trick_room.test.ts` supplies direct source-engine set/reapply/expiry/switch/terminal evidence plus mirrored p1/p2 real v2 transitions, source-backed ordering, restored continuation, deterministic identities, rollback, privacy, and Python successor publication.

CE-04E3 adds one narrow shared TypeScript/Python raw grammar boundary before extraction and DATA-001 publication: only `|-fieldstart|move: Trick Room|[of] <active>` and tagless `|-fieldend|move: Trick Room`. It rejects source-less, legacy-command, side-only/doubles, Persistent-tag, extra, reordered, and whitespace-repaired forms across v1/v2, p1/p2, and input/successor rehashed records, with no output or lineage advance. Existing extractor state already represents the public field ID correctly, so no extractor correction was needed. Computed local coverage digest: `6c49f1c3b3573020baa3d76c988f6637ddcdb3e883185c5092bcd308ee6facea` (unreviewed; manifest attestation fields unchanged).

**CE-04E3 scoped review verdict (2026-10-05, accepted):** Review verified the generated singles Trick Room roots in Slowbro-Galar, Trevenant, Calyrex-Ice, and Rabsca, the exact active-source `-fieldstart|move: Trick Room|[of] <active>` form, and the tagless `-fieldend|move: Trick Room` form for reapplication removal and residual expiry. Source switch, faint, and form changes retain the field-owned public ID; terminal delivery does not fabricate a clear. Mirrored p1/p2 v2 transitions, actual simulator slower-first ordering, restored deterministic twins, stale-rqid rollback, private request boundaries, malformed rejection before publication, and Python successor publication passed. The public view contains only `pseudo_weather: trickroom`; queue speed, action legality, duration, setter identity, requests, and simulator state remain unprojected. Digest `6c49f1c3b3573020baa3d76c988f6637ddcdb3e883185c5092bcd308ee6facea` is attested only for CE-04E3; other pseudo-weather, generic priority/speed inference, doubles, and complete-episode claims remain outside scope.

### CE-04F1 public item lifecycle table (2026-10-05, unreviewed)

| Public lifecycle shape | Pinned generated singles source and exact public form | Typed result and private/excluded state |
|---|---|---|
| Reveal | Generated Frisk rows call `Abilities.frisk.onStart`, emitting exactly `|-item|<opposing active>|<generated item>|[from] ability: Frisk|[of] <Frisk active>`. Air Balloon is the only generated plain `-item` start form: `|-item|<active>|Air Balloon>`. | The named item becomes known and held only after that public record. The selector, starting loadout until revealed, callback state, and item history remain private. |
| Consumption | `Pokemon.eatItem` (`sim/pokemon.ts:1714-1750`) emits exactly `|-enditem|<active>|<item>|[eat]`. The operative singles selectors can supply only Aguav, Chesto, Custap, Figy, Iapapa, Leppa, Lum, Mago, Passho, Rindo, Salac, Sitrus, or Wiki Berry to that emitter: `getPriorityItem/getItem` selects their source paths (`teams.ts:1197-1237,1324,1369,1395,1406`), and each item callback invokes `eatItem`. | The named known item clears and becomes `consumed`; existing HP handling remains independent. `[eat]` accepts that finite domain only, so Choice Scarf, Air Balloon, and every other non-edible generated payload reject before projection/publication. No private threshold, item-state object, or prior selector is exported. |
| Removal | Generated Knock Off calls `target.takeItem()` and emits exactly `|-enditem|<target active>|<generated item>|[from] move: Knock Off|[of] <opposing active source>`. Separately, `data/items.ts:187-202` emits tagless `|-enditem|<active target>|Air Balloon` only when an Air Balloon pops after public damage. | The named target's publicly known item clears and its public last-item value is retained as `removed`. The removal does not infer any unrevealed item. The tagless form accepts Air Balloon only. |
| Transfer/change | Generated Trick and Switcheroo set the recipient then emit `|-item|<recipient active>|<received generated item>|[from] move: Trick|Switcheroo`; their empty-side branch emits ordered `|-enditem|<active>|<generated item>|[silent]|[from] move: Trick|Switcheroo`. | Each public recipient record updates only that recipient's known current item. No transfer graph, item selection, Choice lock, or hidden pre-transfer item is inferred. |
| Raw-only/excluded callback families | Harvest/Recycle history, Pickup/Magician/Pickpocket, Bug Bite/Pluck, gems, Fling, and generic item callbacks have no typed history or callback model in this slice. Their broader lifecycle does not justify adding inferred inventory state. | Recycle/Harvest history, Choice-lock behavior, Fling, generic inventory inference, doubles, and training features remain excluded. Bare `item`/`enditem` aliases are retained raw-only with no provenance suffix. |

Pinned `data/abilities.ts:1486-1492`, `data/moves.ts:10338-10344,19395-19407,20670-20681`, `sim/pokemon.ts:1714-1770`, and `data/items.ts:185-202` establish the bounded emitted forms. `data/random-battles/gen9/sets.json` contains Frisk, Knock Off, Trick, Switcheroo, and the Sitrus-bearing generated routes; `gen9/teams.ts:getPriorityItem/getItem` supplies the finite generated payload domain, including required-form items. The direct simulator fixture proves Frisk reveal, Sitrus consumption after a public damage threshold, Knock Off removal, Trick transfer, and Air Balloon pop removal in both actor directions.

**CE-04F1 `[eat]` repair (2026-10-05, unreviewed):** The original tag-only
`[eat]` template admitted every broad generated item payload, including the
impossible `|-enditem|p1a: Target|Choice Scarf|[eat]`. Both shared validators
now bind `[eat]` to the exact selector-reachable `Pokemon.eatItem` domain in
the table. TypeScript/Python controls accept Aguav and Sitrus Berry, reject
Choice Scarf and Air Balloon, and rehash both schemas, perspectives, input and
successor prefixes before projection or DATA-001 output. The new local digest
is recorded below as unreviewed; no manifest attestation field changed.

CE-04F1 adds one shared TypeScript/Python validation boundary before projection and DATA-001 publication. It accepts only canonical singles-active targets, a finite generated item payload, and the ordered source templates above. It rejects invented or whitespace-repaired item text, side-only/doubles identifiers, same-side or malformed Frisk/Knock Off sources, reordered/duplicate/extra tags, non-edible `[eat]` payloads, and bare-alias provenance before candidate commit. The Air Balloon fixture exposed the tagless removal classification defect: extraction previously treated every empty-tag end-item record as `consumed`. It now classifies only `[eat]`/gem source forms as consumed and the exact tagless Air Balloon source form as `removed`, retaining the public last-item without inferring any hidden inventory. `tests/item.test.ts` provides mirrored p1/p2 v2 source-engine transitions, restoration, deterministic continuation, rollback, privacy, and actual Python successor publication; the Python rehash matrix covers v1/v2, p1/p2, input/successor acceptance and no-output rejection. Computed local coverage digest: `538efd728a628201d5957dc881ee2cc56582b41f04280f82b8c05d80f598934d` (unreviewed; manifest attestation fields unchanged).

**CE-04F1 tagless `-enditem` repair (2026-10-05, unreviewed):** Pinned `data/items.ts:187-202` emits the empty-tag form only as `|-enditem|<active target>|Air Balloon` when the item pops. The shared TypeScript/Python templates now bind the empty-tag form to `Air Balloon`; extraction classifies that exact source form as `removed`, while `[eat]` stays `consumed`. Tagged Knock Off, Trick, and Switcheroo forms retain their independently reviewed rules. Mirrored p1/p2 simulator-backed v2 Air Balloon fixtures prove public removal, restoration, deterministic continuation, stale-candidate rollback, both-perspective privacy, and Python successor publication. Rehashed v1/v2 p1/p2 input/successor controls accept the exact form and reject Choice Scarf or other tagless generated items, malformed/side-only/doubles targets, tags, field-count changes, whitespace, and extra payload before projection or DATA-001 output. Computed local coverage digest: `538efd728a628201d5957dc881ee2cc56582b41f04280f82b8c05d80f598934d` (unreviewed; manifest attestation fields unchanged).

**CE-04F1 tagless `-enditem` review blocker (2026-10-05):** The Air Balloon-only claim is unsupported. Pinned `Pokemon.useItem` (`sim/pokemon.ts:1758-1769`) emits tagless `|-enditem|<active>|<item>` for every non-Gem use-item path. The operative singles generator assigns `Power Herb` when a retained move is Meteor Beam (`data/random-battles/gen9/teams.ts:1229`), and `Items.powerherb.onChargeMove` calls `pokemon.useItem()` (`data/items.ts:4421-4427`). The existing generated Meteor Beam route therefore produces the minimal record `|-enditem|p1a: Armarouge|Power Herb` before its accepted `-anim` record. A controlled Gen 9 Random Battle reproduction emits that exact line. The shared TypeScript/Python Air Balloon-only template rejects this source-backed reachable record before projection and DATA-001, so CE-04F1 cannot be accepted and the coverage digest is not attested. This blocker requires a complete source-qualified tagless `useItem` payload/routing disposition; no implementation change is made in this review.

### CE-04F1 tagless `-enditem` non-Gem `useItem()` inventory (2026-10-05, unreviewed repair)

`Pokemon.useItem` (`sim/pokemon.ts:1758-1769`) emits the empty-tag form for a non-Gem item after the item's callback has reached `useItem`; the record carries no callback provenance. The operative singles item generator is therefore not itself a payload domain. The finite accepted domain is only the following source-qualified intersection; `Air Balloon` remains the separately emitted direct-pop form.

| Payload | Selected-item root | Pinned callback/use path | Public form | Gen 9 Random Battle singles disposition |
|---|---|---|---|---|
| Air Balloon | `getItem` Ground-weakness branch | `Items.airballoon.onDamagingHit/onAfterSubDamage` directly emits removal | `|-enditem|<active>|Air Balloon` | reachable; `removed`, not `useItem` |
| Booster Energy | `getPriorityItem` Fast Bulky Setup branch | `Items.boosterenergy.onStart/onUpdate` for Protosynthesis or Quark Drive calls `useItem` | tagless | reachable; consumed |
| Focus Sash | `getPriorityItem` Smeargle and `getItem` lead branches | `Items.focussash.onDamage` calls `useItem` at full HP on otherwise lethal move damage | tagless | reachable; consumed |
| Power Herb | `getPriorityItem` Meteor Beam branch | `Items.powerherb.onChargeMove` calls `useItem`; Meteor Beam is in generated sets | tagless | reachable; consumed |
| Throat Spray | `getPriorityItem` sound-move branch | `Items.throatspray.onAfterMoveSecondarySelf` calls `useItem` | tagless | reachable; consumed |
| Weakness Policy | `getPriorityItem`/`getItem` singles branches | `Items.weaknesspolicy.onDamagingHit` calls `useItem` on super-effective move damage | tagless | reachable; consumed |
| White Herb | `getPriorityItem` Shell Smash/Unburden branches | `Items.whiteherb.onUpdate` calls `useItem` after a negative stage | tagless | reachable; consumed |

`Absorb Bulb`, `Adrenaline Orb`, `Cell Battery`, terrain seeds, Eject Button/Pack, Luminous Moss, Mental Herb, Mirror Herb, Red Card, Room Service, Snowball, and Blunder Policy are not accepted simply because the base package contains a `useItem` callback: the operative singles selector gives no root (Blunder Policy is doubles-only). Gems retain their `[from] gem` emission and are outside this tagless domain. No Harvest/Recycle/Pickup/Magician history, generic callback inference, doubles, or source identity is projected.

The shared TypeScript/Python tagless `-enditem` form now accepts exactly the seven rows above. The extractor marks Air Balloon as `removed` and each finite non-Gem `useItem` payload as `consumed`; no callback, item selection, or inventory state is exported. Mirrored p1/p2 simulator-backed v2 fixtures cover all seven public records, restoration, deterministic continuation, stale-request rollback, both-perspective privacy, and Python successor publication. TypeScript/Python rehashed v1/v2 p1/p2 input/successor controls accept the finite domain and reject Choice Scarf, Leftovers, malformed/side-only/doubles identifiers, whitespace repair, tags, and extra fields before projection/DATA-001 output. Computed local coverage digest: `ac2c0fbb51697d75eef1b8c2b8b55b2c721c1c193b7f62edbcb9e750c48c824e` (unreviewed; manifest attestation fields unchanged).

**CE-04F1 scoped review verdict (2026-10-05, accepted):** Review verified that `Pokemon.useItem` emits the empty-tag form only after a non-Gem callback reaches that method, so selector membership alone cannot authorize a payload. The accepted finite intersection is Air Balloon's separately direct pop plus generated Booster Energy, Focus Sash, Power Herb, Throat Spray, Weakness Policy, and White Herb callbacks; generated Meteor Beam establishes the Power Herb path. `[eat]`, Gem, Knock Off, Trick, Switcheroo, and reveal templates retain their independent exact forms. Rehashed v1/v2 p1/p2 input/successor controls reject fabricated tagless Choice Scarf and Leftovers records, malformed identifiers, whitespace repair, tags, and extra fields before projection/DATA-001 output. Mirrored v2 simulator witnesses, restoration, deterministic continuation, rollback, privacy, and Python publication passed. Digest `ac2c0fbb51697d75eef1b8c2b8b55b2c721c1c193b7f62edbcb9e750c48c824e` is attested only for CE-04F1; generic item inference, callback history, doubles, and complete-episode claims remain outside this slice.

### CE-04D2 public nonstacking screen source table (2026-10-05, unreviewed)

| Family / generated root | Exact public records and lifecycle | Private state / scope disposition |
|---|---|---|
| Reflect | Direct generated Meowstic rows select Reflect. `Moves.reflect.condition.onSideStart/onSideEnd` emit exactly `|-sidestart|<p1/p2: side name>|Reflect` and tagless `|-sideend|<side>|Reflect`. `Side.addSideCondition` returns false on an existing condition without `onSideRestart`, so duplicate use emits no second start; residual expiry calls the same SideEnd. | The five/eight-turn duration, Light Clay, source/sourceSlot and physical mitigation calculation remain private and untyped. |
| Light Screen | Direct generated Meowstic rows select Light Screen. Its callbacks emit exactly `|-sidestart|<side>|move: Light Screen` and tagless `|-sideend|<side>|move: Light Screen`; duplicate/reapplication has no public restart and ordinary residual expiry uses the same end. | Duration, Light Clay, setter identity and special mitigation remain private. |
| Aurora Veil | Direct generated Ninetales-Alola and Abomasnow rows select Aurora Veil; pinned `onTry` requires hail/snowscape, and the generated Snow Warning roots provide that weather. Its callbacks emit exactly `|-sidestart|<side>|move: Aurora Veil` and tagless `|-sideend|<side>|move: Aurora Veil`; duplicate/reapplication has no public restart and residual expiry uses the same end. | Weather cause, duration, Light Clay, setter/source slot and mitigation stay private; public weather remains its separately reviewed field evidence. |
| Source-backed removal and boundary behavior | `Side.removeSideCondition` always invokes the condition's SideEnd before deletion. Generated Defog removes all three from the target side; generated Brick Break, Raging Bull, and Psychic Fangs each call the same removal path. `Moves.psychicfangs.onTryHit` removes Reflect, Light Screen, and Aurora Veil before its damage path; generated Mew supplies a direct Psychic Fangs root. Screens belong to Side, so ordinary setter switch/faint does not end them; terminal delivery does not fabricate an end. | Remover identity is not encoded in screen SideEnd. Court Change's later bounded atomic swap is CE-04D3; doubles, generic side swapping, Safeguard, Mist, Tailwind and other side-condition lifecycle work are not accepted by CE-04D2 itself. |

The shared TypeScript/Python boundary now accepts only the six exact dash records above: side-only canonical `p1: <name>`/`p2: <name>` targets, the matching literal start/end labels, and no tags or extra fields. It rejects bare-command aliases, active/doubles/whitespace side identifiers, label/prefix repair, tags, extra fields, and ungenerated Safeguard/Mist source-family records before extraction or DATA-001 publication. Existing side-condition extraction was already correct for nonstacking public presence: each accepted start stores count `1` and matching end deletes it; no duration/source model was added.

`tests/screen.test.ts` supplies direct pinned-engine duplicate, expiry, Defog, Brick Break, Raging Bull, and all-three-screen Psychic Fangs witnesses. Its mirrored p1/p2 `observable-battle-state/v2` transitions now use generated Mew's Psychic Fangs as the removal action for each screen: both public perspectives retain only the source-shaped tagless SideEnd and side-presence deletion, restored twins converge on the same successor fingerprint, stale-rqid candidates reject without boundary mutation, and actual emitted record bundles validate through Python. The Python rehash matrix covers v1/v2, p1/p2 and input/successor acceptance/rejection with empty stdout on rejection. Computed local coverage digest is recorded below after focused validation (unreviewed; manifest attestation fields unchanged).

**CE-04D2 Psychic Fangs repair (2026-10-05, unreviewed):** Pinned
`Moves.psychicfangs.onTryHit` calls `pokemon.side.removeSideCondition` for
Reflect, Light Screen, and Aurora Veil before damage. Direct generated Mew
supplies the operative singles root. The table and simulator fixture now cover
all three source-shaped tagless SideEnd records, both setter sides and both
public perspectives, post-start restoration, deterministic continuation,
stale-action rollback, and Python transition-bundle publication. This adds no
grammar or state-model surface. Computed local coverage digest:
`8171d803227cdf218e3b24def428c11152345476834efde4b8ec3c6eb261a56a` (unreviewed; manifest fields unchanged).

**CE-04D2 scoped review verdict (2026-10-05, accepted):** Review verified the
pinned Psychic Fangs callback, direct generated Mew route, and all three
screen removals through the ordinary tagless SideEnd records. Mirrored p1/p2
v2 transitions retain public side-state removal, both-perspective privacy,
restored-twin deterministic continuation, stale-candidate rollback, and
Python publication. Defog, Brick Break, and Raging Bull witnesses remain
intact. Digest `8171d803227cdf218e3b24def428c11152345476834efde4b8ec3c6eb261a56a`
is accepted for CE-04D2 only; generic removal, side swapping, doubles,
damage calculation, and complete-episode claims remain excluded.

### CE-04D3 Court Change public side-condition swap table (2026-10-05, unreviewed)

| Lifecycle / source path | Exact public evidence and public state | Private or excluded state |
|---|---|---|
| Generated root and grammar | Generated Cinderace rows include Court Change (`data/random-battles/gen9/sets.json:5652-5665`). In singles, `Moves.courtchange.onHitField` exchanges the two Side maps and emits exactly `|-swapsideconditions` with **no actor, side, tag, or payload**. When at least one listed condition moved, it then emits `|-activate|<active Cinderace>|move: Court Change`. The dash command is the only accepted swap command; the bare alias, payloads, tags, slots, sides, and whitespace variants reject. | The swap record names neither player nor setter. The activation's active actor is raw-only evidence; no source identity, request, or simulator map is typed. |
| Transferred public conditions | The pinned normal-singles list is `mist`, `lightscreen`, `reflect`, `spikes`, `safeguard`, `tailwind`, `toxicspikes`, `stealthrock`, `waterpledge`, `firepledge`, `grasspledge`, `stickyweb`, `auroraveil`, and `luckychant`. The extractor atomically exchanges only already-public values for those IDs. Hazard counts move unchanged; nonstacking screen presence remains `1`; a source-list condition absent on one side is deleted there and installed unchanged on the other. The simulator-backed asymmetric fixture witnesses Spikes/Toxic Spikes and Reflect/Light Screen on opposite sides before the atomic record. | Court Change does not move weather, terrain, pseudo-weather, Pokémon volatiles, requests, items, source fields, durations, Light Clay, or hidden side-condition objects. No independent start/end grammar is added for other list members. |
| Ordering and later effects | The source exchanges the internal maps before adding `-swapsideconditions`, then adds Court Change activation only after a successful exchange. The public swap is therefore applied before the successor request. In both actor directions, a later ordinary replacement receives the swapped Spikes damage and swapped Toxic Spikes poison through their independently accepted public HP/status records. Ordinary switch/faint does not undo a side-owned condition; terminal delivery fabricates no swap or removal. | Free-for-all has a different silent remove/restart protocol and is excluded by Gen 9 Random Battle singles. G-Max side conditions have no operative Gen 9 route and are excluded. This is not a generic side-swap command, doubles, or a damage-calculation model. |
| Restoration and publication | Mirrored `observable-battle-state/v2` sessions restore immediately after the consumed Court Change request, converge with untouched twins on transition/fingerprint identity, reject stale rqid candidates before mutation, retain each owner request privately, and publish the actual swap and successor bundles through Python. | Snapshot internals, request payloads, setter identity, timer, and unrepresented source condition state remain absent from both observations and DATA-001. |

CE-04D3 adds one shared TypeScript/Python exact-boundary rule before projection and DATA-001 publication. It accepts only `|-swapsideconditions` and the exact active-source Court Change activation; all malformed source-family forms reject across v1/v2, p1/p2, and input/successor rehashing with empty publication output and no lineage advance. `tests/court_change.test.ts` supplies direct source-engine and mirrored v2 witnesses for both actor sides, public count/presence preservation, later switch-in consequences, restoration, deterministic continuation, rollback, privacy, and Python publication. Computed local coverage digest: `b99158a110b0546936e6f98077214d4eda7dfadc9815230bc632ea11ba4b05ac` (unreviewed; manifest attestation fields unchanged).

**CE-04D3 review blocker (2026-10-05):** The swap implementation is broader than the reviewed hazard/screen witnesses. Generated Shiftry has a Gen 9 Random Battle `Tailwind` movepool route (`data/random-battles/gen9/sets.json:1926-1945`), and `Moves.tailwind` establishes public side condition `tailwind` (`data/moves.ts:19608-19618`). Pinned `Moves.courtchange.onHitField` includes `tailwind` in its transferred list (`data/moves.ts:3140-3196`). The current generic side-condition extractor accepts and types `|-sidestart|p1: One|Tailwind`; the new Court Change loop then transfers it. Minimal reproduction: ingest `|-sidestart|p1: One|Tailwind`, `|-sidestart|p2: Two|Spikes`, `|-swapsideconditions` as p1 and the public maps become `self:{spikes:1}`, `opponent:{tailwind:1}`. No CE-04D3 simulator-backed v2 witness, restoration/publication proof, or explicit scope disposition covers that reachable typed Tailwind transfer. This is generic side-condition swap behavior beyond the reviewed hazard/screen boundary, so CE-04D3 remains unaccepted and its digest must not be attested.

#### CE-04D3 complete transferable-side-condition inventory repair (2026-10-05, unreviewed)

`Moves.courtchange.onHitField` has a finite normal-singles transfer list. The
table below separates that pinned list from generated-format reachability; a
listed source condition does not become a supported transfer merely because
the generic side-condition view could represent it.

| Pinned ID | Current public representation | Gen 9 Random Battle singles route | Value and disposition |
|---|---|---|---|
| `spikes` | typed side map | generated setters | layer count 1–3; existing asymmetric v2 swap and later switch-in damage witness |
| `toxicspikes` | typed side map | generated setters | layer count 1–2; existing asymmetric v2 swap and later switch-in Poison witness |
| `stealthrock` | typed side map | generated setters | presence `1`; direct generated root and existing side-condition transfer witness through the same atomic loop |
| `stickyweb` | typed side map | generated setters | presence `1`; direct generated root and existing side-condition transfer witness through the same atomic loop |
| `reflect` | typed side map | generated Meowstic/Grimmsnarl | presence `1`; existing asymmetric v2 swap witness |
| `lightscreen` | typed side map | generated Meowstic/Grimmsnarl | presence `1`; existing asymmetric v2 swap witness |
| `auroraveil` | typed side map | generated Ninetales-Alola/Abomasnow under source-backed snow | presence `1`; generated start route, same pinned atomic transfer semantics; no distinct count form |
| `tailwind` | typed side map | generated Shiftry Setup Sweeper row | presence `1`; new mirrored source-engine v2 witness transfers it with asymmetric hazards, retains it until exact public `|-sideend|<actor side>|move: Tailwind` expiry, restores twins, rolls back stale candidates, and publishes both bundles through Python |
| `mist`, `safeguard`, `luckychant` | generic typed side map | no selected Gen 9 Random Battle move root; the generated set inventory contains none | explicit source-proven no-route for this format; no artificial fixture |
| `waterpledge`, `firepledge`, `grasspledge` | generic typed side map | pinned Pledge callbacks require an allied Pledge user (`isAlly`); singles has no ally active slot | source-proven singles impossible; no fixture |
| `gmaxsteelsurge`, `gmaxcannonade`, `gmaxvinelash`, `gmaxwildfire`, `gmaxvolcalith` | generic typed side map but excluded from the normal transfer claim | no Dynamax/G-Max route in Gen 9 Random Battle | explicit no-route; no fixture |

The repaired Court Change fixture uses only seeded teams emitted by the pinned
generator. Cinderace `[91,274,457,640]` supplies its generated Fast Support
set (`Pyro Ball`, `High Jump Kick`, `Sucker Punch`, `Court Change`, Libero,
Heavy-Duty Boots). The independent source roots are Skarmory/Spikes
`[212,637,1062,1487]`, Iron Treads/Stealth Rock `[6,19,32,45]`,
Ribombee/Sticky Web `[26,79,132,185]`, Meowstic/Reflect and Light Screen
`[32,97,162,227]`, Abomasnow/Aurora Veil `[45,136,227,318]`,
Ariados/two-layer Toxic Spikes `[119,358,597,836]`, and Shiftry/Tailwind
`[110,331,552,773]`. The fixture generates each complete team through
`Teams.generate('gen9randombattle', {seed})`; it does not assign moves,
abilities, items, weather, or battle state.

Each root reaches Cinderace through legal generated switches and moves, makes
the side maps asymmetric, then uses generated Court Change and an ordinary
generated source-side switch. Hazards target the opposing Cinderace side and
screens/Tailwind remain source-owned, so both swap directions are exercised.
Abomasnow's generated Snow Warning emits the source weather record before its
generated Aurora Veil. The mirrored p1/p2 v2 witnesses assert all eight
reachable represented siblings, the exact atomic records, deterministic twin
identity, direct-runtime restore, stale-rqid rollback, observation privacy,
and Python publication for both perspectives. Spikes, Stealth Rock, Sticky
Web, and Toxic Spikes additionally prove their transferred side's later
generated switch-in effects; Tailwind proves source-shaped expiry on its new
side without exposing duration or setter state. The exact Court Change grammar
is unchanged; malformed aliases, side/slot fields, tags, whitespace, and
payloads still fail before projection or DATA-001 publication.

This is local, unreviewed CE-04D3 repair evidence. The normal coverage checker
reports local digest `110e286b51c6c1530b231cc428c498711a0fa067ad93a535029df9bfb5110856`;
all manifest attestation fields remain unchanged and no readiness verdict is
claimed here. The separate broader coverage weather failure is investigated as
a baseline issue and is not repaired in this slice.

**CE-04D3 scoped review verdict (2026-10-05, accepted):** Review verified the
separate seeded `gen9randombattle` roots for Cinderace/Court Change, Spikes,
Stealth Rock, Sticky Web, Reflect, Light Screen, Aurora Veil under generated
Snow Warning, two-layer Toxic Spikes, and Tailwind. Each mirrored p1/p2 v2
source-engine witness uses only legal generated switches and moves, preserves
the exact public layer count or presence across the atomic swap, retains each
owner's request privately, restores deterministically, rejects stale requests
without mutation, and publishes successor bundles through Python. The shared
TypeScript/Python grammar remains the exact dash swap plus canonical active
Court Change activation; the extractor moves only the pinned normal-side IDs,
so no weather, terrain, pseudo-weather, item, ability, source, duration, or
other simulator state is transferred. Mist, Safeguard, Lucky Chant, Pledges,
and G-Max routes retain their recorded no-route dispositions. Digest
`110e286b51c6c1530b231cc428c498711a0fa067ad93a535029df9bfb5110856` is
accepted for CE-04D3 only. The separate `simulator_coverage.test` rejection of
the legacy `|-weather|raindance` fixture reproduces independently and is not
part of this verdict; PIPELINE-002 and `faithful_complete_episode:false` remain
unchanged.

### CE-04F2 public major-status lifecycle table (2026-10-06, unreviewed)

| Public output family | Pinned reachable emitter and exact public record | Typed result; private or excluded state |
|---|---|---|
| Ordinary apply and replacement | `Conditions.{brn,par,slp,frz,psn,tox}.onStart` emits `|-status|<active>|<id>` for direct generated move effects and Synchronize's reflected attempt. A second successful status replaces the current public ID; a same-ID attempt emits `-fail`, never a second `-status`. | `status` and `status_source: protocol` update only from the accepted record. `statusState`, toxic stage, sleep time, random selection, immunity checks, and source ownership remain private. |
| Distinct tagged apply | `Moves.rest.onHit` emits only `slp` with `[from] move: Rest`; Flame Orb and Toxic Orb emit only `brn`/`tox`; generated Effect Spore, Flame Body, Static, and Toxic Chain emit their finite status domains with `[from] ability` and opposing active `[of]` tags. | Exact source/status combinations update the public ID. Invented tags, item/ability names, same-side sources, and status-value mismatches reject before projection or publication. |
| Cure | `Pokemon.cureStatus()` emits `[msg]`; `Abilities.naturalcure.onSwitchOut` emits `[from] ability: Natural Cure`; `Conditions.frz.onModifyMove` has the finite generated frozen self-defrost move records. | `-curestatus` clears the typed status. Cure origin, duration, stale status state, and hidden ability/item selection are not exported. |
| Silent clear at replacement | `Moves.healingwish.condition.onSwap` clears status before its exact active `|-heal|<target>|100/100|[from] move: Healing Wish`; `Battle.runAction('revivalblessing')` clears a fainted bench target before its exact side-only half-heal record. | Existing bounded Healing Wish and Revival Blessing handlers clear status only from those public HP records. Slot conditions, selection request content, and exact owner-private HP are private. |
| Switch and faint | Switch conditions retain an emitted current status; Natural Cure may clear during switch via the explicit cure record. `Battle.faintMessages` then `checkFainted` replaces the simulator status with `fnt`. | A status-bearing switch condition retains status. A statusless public HP condition is clear evidence, and `faint` clears the public major-status field; neither creates a synthetic cure record. |
| Terrain and other callback context | Electric/Misty terrain, immunity abilities, berries, and callback guards can prevent, cure, or alter status execution, but no additional accepted major-status record form follows from their hidden guard/counter state. | Terrain ID remains in the separately bounded field model. Hidden grounding, duration, probability, item ownership, and request legality remain untyped; no generic callback or doubles grammar is accepted. |

The shared TypeScript/Python boundary now admits the six IDs only through that
source-shaped table, before `PlayerStateExtractor` or DATA-001 publication.
The extractor now treats an emitted HP condition without a status suffix as
public clear evidence and clears the major-status projection on `faint`; it
does not infer a clear from missing records. `tests/major_status.test.ts` covers
both perspectives, apply/replacement/cure, switch retention, statusless-HP
clear, and faint; existing `healing_wish.test.ts` and `revival.test.ts` retain
the mirrored v2 restore, deterministic continuation, rollback, privacy, and
Python successor-publication witnesses for the two silent replacement clears.

Computed local coverage digest: `ba328907f58d969aebeb167b834fcf9262bf2c87f5620047bef705c61722ea8b` (**unreviewed**).
Manifest attestation fields are unchanged. This is implementation evidence,
not a scoped review verdict; counters, sleep choice, toxic progression,
generic item callbacks, doubles, and complete-episode claims remain outside
CE-04F2.

**CE-04F2 review hold (2026-10-06):** Do not attest this checkpoint. The
shared validators accept unsupported bare `|status|...` and
`|curestatus|...` aliases although the pinned base emitters use dashed
commands. They also reject four reachable source families: frozen
self-defrost records for generated Hydro Steam, Matcha Gotcha, and Steam
Eruption; Poison Touch's generated `psn` ability provenance; and move-origin
sleep records for generated Sleep Powder, Hypnosis, and Spore. Pinned
`Conditions.frz.onModifyMove`, `Conditions.psn.onStart`, and
`Conditions.slp.onStart` establish those exact public forms. The four current
`selective_boosts` failures are separate: the White Herb scenario rejects an
unsupported `-item` source form under current item grammar, not CE-04F2.
No code, tests, manifest digest, review verdict, or readiness claim changed.

### CE-04F shared status and White Herb contract repair (2026-10-06, unreviewed)

#### CE-04F2 major-status source table

| Source-qualified family | Exact accepted public record | Boundary and exclusion |
|---|---|---|
| Ordinary source rows retained | Dashed `-status` rows already listed above, including Rest, Orbs, Effect Spore, Flame Body, Static, and Toxic Chain | `statusState`, toxic stage, sleep duration, selectors, and chance remain private. |
| Poison Touch | `|-status|<target>|psn|[from] ability: Poison Touch|[of] <opposing active>` | `data/abilities.ts:3275-3287` calls `trySetStatus('psn', source)`; `Conditions.psn.onStart` supplies the exact ability tags. Same-side, side-only, doubles, wrong-status, reordered, or extra-tag forms stop. |
| Direct generated sleep moves | `|-status|<target>|slp|[from] move: Sleep Powder`, `Hypnosis`, or `Spore` | `Conditions.slp.onStart` (`data/conditions.ts:47-57`) emits the move name. The pinned Gen 9 Random Battle movepool inventory is exactly these three direct `status:'slp'` moves; Yawn and all other move spellings stop. |
| Frozen self-defrost | `|-curestatus|<target>|frz|[from] move: Flare Blitz`, `Fusion Flare`, `Hydro Steam`, `Matcha Gotcha`, `Pyro Ball`, `Sacred Fire`, `Scald`, `Scorching Sands`, or `Steam Eruption` | `Conditions.frz.onModifyMove` (`data/conditions.ts:107-111`) emits this exact dashed form. The pinned generated-movepool inventory has exactly these nine `flags.defrost` siblings. Frozen counter, move execution state, target-thaw cases, and generic cures remain untyped. |
| Bare aliases | None | Bare `|status|...` and `|curestatus|...` are now explicit unresolved aliases and stop before projection/publication. |

The TypeScript and Python contracts share the finite table. `major_status.test.ts`,
`test_major_status_contract.py`, the contract matrix, and rehashed v1/v2,
p1/p2, input/successor Python controls accept the exact rows; malformed or bare
controls retain the candidate, produce no Python output, and preserve rollback.

#### CE-04F1 White Herb source table

| Stage | Pinned output and handling | Boundary and exclusion |
|---|---|---|
| Consume after a negative stage | `Items.whiteherb.onUpdate` (`data/items.ts:7201-7214`) calls `useItem`, yielding `|-enditem|<active>|White Herb` followed by `|-clearnegativeboost|<active>|[silent]` | Existing tagless White Herb consumption remains exact; the extractor records a consumed public item and clears only negative public stages. |
| Restore after the consumed item | `Moves.recycle.onHit` (`data/moves.ts:15376-15381`) emits `|-item|<active>|White Herb|[from] move: Recycle` | The shared grammar accepts this one White Herb payload/tag pair. `handleItem` restores `held`; a later source-backed White Herb use consumes it again. |
| Settling and publication | The prior negative selective-boost path stopped when Recycle's `-item` record missed the grammar gate, before extraction | Mirrored p1/p2 simulator fixtures now restore, repeat the second consume/clear, continue deterministically, roll back rejected candidates, preserve private fields, and publish valid successor bundles through Python. |

No generic Recycle, item-history, callback counter, item ownership inference,
other restored payload, doubles, or complete-episode support is added.

Computed local coverage digest: `16bfe90d2fc9e54efbb16aa13d47a26c642d51f18f198edc4519618c11b0b05b`
(**unreviewed**). The checker reports the expected removal of bare `status` and
`curestatus` from supported tokens and their addition as recognized unsupported
aliases. Manifest attestation fields remain unchanged.

**CE-04F2 scoped review verdict (2026-10-06, accepted):** Review verified the
finite dashed-only public major-status boundary: six status IDs, Poison Touch
`psn` with its opposing-active source, exactly Sleep Powder, Hypnosis, and
Spore for direct move-origin sleep, and exactly Flare Blitz, Fusion Flare,
Hydro Steam, Matcha Gotcha, Pyro Ball, Sacred Fire, Scald, Scorching Sands, and
Steam Eruption for frozen self-defrost. Bare `status` and `curestatus` remain
recognized unsupported aliases. TypeScript and Python rehashed controls cover
v1/v2, p1/p2, and input/successor positions; malformed candidates emit no
Python output and preserve the committed boundary. This accepts CE-04F2 only:
generic status callbacks, unlisted move forms, private counters and requests,
doubles, and complete episodes remain outside scope.

**CE-04F1 scoped review verdict (2026-10-06, accepted):** Review verified the
one restored-item extension is exactly `|-item|<active>|White Herb|[from] move:
Recycle`. It restores public held state after the source-backed tagless White
Herb consume and silent negative clear, then permits the second consume/clear;
generic Recycle payloads, tags, and item-history inference remain rejected.
Mirrored p1/p2 simulator paths, v1/v2 input/successor rehash controls,
restoration, deterministic continuation, rollback, privacy, and Python
successor publication passed. Digest
`16bfe90d2fc9e54efbb16aa13d47a26c642d51f18f198edc4519618c11b0b05b` is
attested only for CE-04F1 and CE-04F2; generic item callbacks/history, doubles,
PIPELINE-002, and complete-episode claims remain outside scope.

### CE-04C reachable public stage-transfer closure (2026-10-06)

#### Scope and source method

This is the finite Gen 9 Random Battle singles closure for public boost stages
against the pinned `pokemon-showdown@0.11.10` source and the operative
`gen9randombattle` generator. The source set is the `M` move roots,
`A` generated ability roots plus allowed form defaults, and `I` items produced
by the pinned item selectors. The proof follows those roots through
`RandomTeams.randomTeam/randomSet/randomMoveset/getAbility/getPriorityItem/getItem`,
the active-slot invariant, and the already audited reflection, caller and
ability-copy edges in B05–B08, B11 and B17. Registry presence and package-wide
or other-format emitters alone do not establish reachability.

`Battle.boost` (`sim/battle.ts:1910-1967`) and `Pokemon.boost/setBoost/clearBoosts`
(`sim/pokemon.ts:550-605,1178-1189`) are the logged delta writers. The source
scan also covered every base `clearBoosts`, `setBoost`, direct `boosts` write,
`stealsBoosts` branch and `copyVolatileFrom` callsite. The only reachable reset
without a boost-family protocol record is ordinary switch/drag/faint cleanup;
White Herb's `[silent]` clear is a separate logged path below. The only
base-source stage-map copy sites are Transform and the `copyvolatile` branch
called by Baton Pass, whose generated root is ruled out below; Shed Tail
explicitly excludes stages. No additional generated singles writer remains
unclassified.

#### Finite route matrix

| Route | Pinned source proof and generated-format disposition | Stage result and existing/new evidence |
|---|---|---|
| Ordinary move, ability and item stage deltas | Direct generated move effects and finite generated callbacks reach `Battle.boost`. It emits the applied `-boost`/`-unboost` delta after `onChangeBoost`, `onTryBoost`, clamping and callback order. Contrary is generated (including Serperior); Defiant/Competitive and other source-bounded callbacks re-enter the same writer. `onTryBoost` filters that cancel an attempted change leave stored stages unchanged. | **Generated-format reachable and already correctly represented.** v2 replays the public delta only. New Serperior/Contrary witness verifies Leaf Storm's nominal self-drop becomes the exact `|-boost|...|spa|2` line and both TypeScript and Python publish `+2`; ordinary signed/mixed seven-stage evidence is reused from public-stages, Transform, selective-clear and ability-callback tests. |
| `-setboost` replacement / Belly Drum | `Battle.boost` uses `-setboost` for the finite `bellydrum` and `angerpoint` effects. Belly Drum has generated Azumarill/Eiscue/Cetitan roots; Anger Point has no authored generated ability root and cannot be introduced by the closed Trace/Imposter ability-copy chain. | **Generated-format reachable and already correctly represented.** New generated Azumarill witness verifies `[17,2,3,4]`, Belly Drum `+6 Attack`, exact source tag, and v2/Python publication. Existing rehashed `setboost` controls cover zero, sign, clamping and aliases. |
| Haze full clear | `Moves.haze.onHitField` clears every active Pokémon and emits `-clearallboost` (`data/moves.ts:8458-8461`). Haze occurs in generated set rows; it may also be called only through the bounded same-move caller graph. | **Generated-format reachable and already correctly represented.** New generated Tentacruel witness `[21,2,3,4]` starts from a real Shell Smash record and proves Haze resets the seven-stage maps at the exact event boundary for either player, with Python publication. |
| Clear Smog target clear | `Moves.clearsmog.onHit` calls `target.clearBoosts()` then emits `-clearboost` (`data/moves.ts:2642-2643`). Amoonguss, Swalot and Gastrodon generated sets supply Clear Smog. | **Generated-format reachable and already correctly represented.** New generated Amoonguss witness `[148,2,3,4]` proves only the struck Shell Smash target clears, for either player and both publication perspectives. |
| Transform and Imposter full-map replacement | `Moves.transform.onHit` (`data/moves.ts:20596-20610`) and `Abilities.imposter.onSwitchIn` (`data/abilities.ts:2056-2065`) both reach `Pokemon.transformInto`, which copies the target's seven current stages before `-transform` (`sim/pokemon.ts:1218-1296`). Ditto has generated Transform and Imposter roots. Guards fail on faint, Illusion, Substitute, incompatible existing Transform/Tera/species state. | **Generated-format reachable and already correctly represented.** Accepted manual Transform tests prove replacement, sparse known/zero/unknown values, independent history and later events. New generated Ditto witness `[9,2,3,4]` boosts Gengar first, then switches Ditto in and verifies Imposter copies the exact nonzero seven-stage map at `-transform`, with both sides and Python successor publication. No hidden target or simulator truth is added. |
| Ordinary switch/drag/faint stage reset | `Pokemon.clearVolatile` restores all seven stored stages; callers are construction, ordinary switch-out, drag/switch handling and faint cleanup after the public faint event (`sim/pokemon.ts:1440`; `sim/battle-actions.ts:118`; `sim/battle.ts:2468`). | **Generated-format reachable and already correctly represented.** Reuse the accepted v2 switch/drag/faint witnesses in `public_stages.test.ts`, lifecycle tests, and source reset proof. A fresh stage map starts at known zero only where a public switch establishes the active Pokémon; absent earlier evidence remains unknown. |
| Shed Tail switch/copy branch | Generated Cyclizar/Orthworm can select Shed Tail. `Pokemon.copyVolatileFrom(..., 'shedtail')` skips the `boosts` assignment and copies only Substitute (`sim/pokemon.ts:1192-1200`); ordinary outgoing cleanup resets the donor. | **Generated-format reachable and already correctly represented.** B14 plus the accepted Shed Tail state-extractor and forced-switch witnesses cover the real switch, Substitute transfer and donor reset. No public stage is copied to the receiver; this does not authorize a generic stage/volatile pass model. |
| White Herb selective negative clear | Generated White Herb selection includes Shell Smash/Unburden branches; `Items.whiteherb.onUpdate` consumes the item, silently zeroes only negative stages, then emits `-clearnegativeboost [silent]` (`data/items.ts:7201-7214`). Recycle's single bounded restore path is separately source-qualified. | **Generated-format reachable and already correctly represented.** Reuse accepted CE-04F1 and `selective_boosts.test.ts`: mixed signs, zeros and unknown stages; repeat after Recycle; mirrored p1/p2 restoration, rollback and Python publication. The Fling effect branch is excluded because Fling has no M root. |
| Mirror Armor reflected negative stages | Generated Corviknight may select Mirror Armor. Its `onTryBoost` removes the negative delta from the target and calls `Battle.boost` on the source (`data/abilities.ts:2583-2600`). Trace or Transform can copy only a currently seeded ability; they do not invent an unseeded ability. | **Generated-format reachable and already correctly represented.** New generated Corviknight witness `[152,2,3,4]` receives Arcanine's Intimidate on entry; the exact `-unboost` lands on Arcanine and v2/Python agree for either actor. The ability reveal is separately validated; no hidden ability inference is introduced. |
| Psych Up copy | `Moves.psychup.onHit` replaces the caller's boost map, emits the exact Psych Up `-copyboost`, and separately copies four crit volatiles (`data/moves.ts:14549-14575`). B05 plus B08 closes direct and indirect move roots: no generated Psych Up slot or move-invention caller. | **Source-proven impossible in singles.** Retain the already accepted exact Psych Up compatibility semantics and tests for source-shaped public-prefix replay. The four crit volatile parameters remain private and create no typed public-stage effect. |
| Costar and Curious Medicine ally callbacks | Costar returns before any copy when `pokemon.allies()[0]` is absent (`data/abilities.ts:695-712`); Curious Medicine clears adjacent allies only (`:770-774`). Neither has a generated ability root, and the singles active-slot invariant leaves no ally to satisfy either guard. | **Source-proven impossible in singles.** Keep the Costar tag fail-closed. Constructed Costar scanner tests are not a generated-mechanics witness. |
| Opportunist and Mirror Herb positive-stage copy | Their callbacks retain positive deltas and later call the ordinary boost writer (`abilities.ts:2970-3001`; `items.ts:3799-3835`). Neither has an authored generated A/I root. Trace/Imposter can copy a present ability only; by induction over the generated ability roots neither can bootstrap Opportunist. Item selectors do not choose Mirror Herb. | **Source-proven impossible in singles.** No ability/item copy model or callback state is needed. Any legal stage change from a seeded copied ability still arrives through the ordinary logged delta row. |
| Topsy-Turvy inversion | The base move negates each nonzero target stage and emits `-invertboost` (`data/moves.ts:20427-20436`), but Topsy-Turvy has no generated M root and the closed caller graph cannot create one. Rigged Dice's other emitter is Gen9SSB-only. | **Source-proven impossible in singles.** Retain the accepted exact Topsy-Turvy compatibility semantics and tests; they do not establish a generated route. Keep private/public zero and unknown semantics unchanged. |
| Power Swap, Guard Swap and Heart Swap | The three base move callbacks replace stage values with `setBoost`; only Heart Swap emits `-swapboost` (`data/moves.ts:8255-8278,8741-8763,14278-14303`). None has a generated M root or indirect source. | **Source-proven impossible in singles.** `-swapboost` remains rejected before Python publication; no bilateral swap model is added. |
| Spectral Thief theft | The `stealsBoosts` branch clears positive target stages, boosts the user, then emits its animation (`sim/battle-actions.ts:775-804`). Spectral Thief has no Gen 9 Random Battle move root. | **Source-proven impossible in singles.** Existing selective-clear semantics remain reusable for evidence but do not prove the move route. Its exact animation form is separately **raw-only/private with no public typed-stage consequence** and remains bounded in `selective_boosts.test.ts`. |
| Baton Pass stage pass | `copyVolatileFrom` shares the boost map when `switchCause !== 'shedtail'`; Baton Pass is the only base `copyvolatile` caller, and its move has no generated M root. Other ordinary switches do not copy stages. | **Source-proven impossible in singles.** V2 continues to reject a Baton Pass move line as stage evidence. Reuse generic switch reset and Shed Tail-only copy exclusions; do not enable Baton Pass or general transfer. |
| Simple / Anger Point / other silent non-writers | Simple and Anger Point have no authored A root. Ability-copy sources are closed over generated abilities. `Unaware` and the Foresight/Miracle Eye calculations use modified copies for damage/hit checks and do not assign to stored `Pokemon.boosts` (`sim/pokemon.ts:559-605`; `sim/battle-actions.ts:710-714`). | **Source-proven impossible in singles** for unseeded stage writers; calculation-only paths are **raw-only/private with no public typed-stage consequence**. No private critical-hit counter or generic stage model is required. |
| Fling White Herb, Z-Power clear and Freezy Frost | White Herb's `fling.effect` can clear negative stages, Z-Power has a separate clearnegative branch, and Freezy Frost clears all stages. Fling has no M root, Gen 9 Random Battle has no Z-item/action route, and Freezy Frost is not an operative Gen 9 move root. | **Source-proven impossible in singles.** Do not expand item/move reachability based on package-wide emitters or other-generation data. |
| Bounded compatibility aliases and unsupported forms | The accepted bare `boost/unboost/setboost/clear* /transform` aliases normalize only inside the existing v2 replay contract. Exact Psych Up and Topsy-Turvy forms remain typed compatibility evidence; Spectral Thief animation is raw-only; Costar `-copyboost`, `-swapboost`, and Baton Pass transfer remain unsupported. | Compatibility is **raw-only/private with no public typed-stage consequence** only for explicitly raw-only forms. Typed compatibility records keep their accepted event semantics but confer no generated-format reachability. Rehashed Python validation, public-stage identity, historical v1/v2 behavior, and immutable prefixes remain unchanged. |

#### Witnesses and evidence reused

`tests/public_stages.test.ts` adds deterministic generator-backed, source-engine
v2 witnesses for Haze, Clear Smog, Mirror Armor, Contrary, Imposter and Belly
Drum. Their generator seeds are respectively `[21,2,3,4]` Tentacruel,
`[148,2,3,4]` Amoonguss, `[152,2,3,4]` Corviknight, `[40,2,3,4]` Serperior,
`[9,2,3,4]` Ditto, and `[17,2,3,4]` Azumarill. Each witness runs for both
actor sides, checks the actual simulator stage vector against v2 self/public
opponent vectors at the exact prefix, checks immutable input-prefix retention,
and validates both perspective successor bundles through Python. No duplicate
fixture was added for accepted Transform, Psych Up, Topsy-Turvy, White Herb,
ordinary switch/faint reset or Shed Tail evidence.

Focused validation: `npm run build` passed in `sim-core`; 86 selected TypeScript
tests passed in `public_stages`, `transform_boosts`, `psych_up`,
`selective_boosts`, `topsy_turvy` and `ability_callback`. `git diff --check`
passed after the document updates. The coverage manifest already lists
`tests/public_stages.test.ts`; no manifest sources or attestation fields were
changed. The manifest's local/reviewed digest was not recalculated in this
scoped run and remains a separate coverage-attestation review item.

#### Recommendation and remaining boundary

**CE-04C scoped review verdict (2026-10-06): accepted as source/evidence
closure with no production implementation slice.** The pinned-source review
found no reachable generated route with a missing or incorrect disposition.
Every surviving generated public-stage change is
reconstructed from the exact public event or from the documented switch,
faint, Shed Tail or Transform event boundary. The new route witnesses pass in
both actor directions and Python publication. No reachable typed-stage defect
was found, so there is no follow-up code slice to name. If later source drift
adds a route or any focused witness disagrees with simulator stages, open a
narrow slice naming the exact emitter, state handler, shared validator and
mirror test; do not reopen C19 as a generic refactor.

Known boundaries remain explicit: v1 still omits opponent stages; v2 preserves
known/zero/unknown and historical prefixes; exact compatibility support does
not prove random-format reachability; doubles, private crit data, generic
stage-transfer features and model/training behavior remain excluded. The
coverage digest/attestation, PIPELINE-002 acceptance and
`faithful_complete_episode:false` are unchanged.

#### CE-04C coverage digest attestation (2026-10-06)

The complete local coverage-source list includes
`sim-core/tests/public_stages.test.ts`. The coverage checker consumed the listed
sources and reported only the expected pre-refresh digest mismatch; its
synthetic drift self-tests all passed. The focused CE-04C evidence still matches
the reviewed witness/test contents, so the recorded successful build and 86
selected TypeScript tests are reused. No implementation or test files were
changed for this attestation.

The reproduced local coverage digest is
`c0f87af971132c6542fd89735dee6cf920b881882456bdcd670841ad38d252d3`. The
manifest's local `sha256` and `reviewed_sha256` now bind this digest. This
attestation is limited to CE-04C; all other scoped attestations and
`faithful_complete_episode:false` remain unchanged.

### CE-06B implementation checkpoint (2026-10-06, ready for scoped review)

The episode envelope now emits `pipeline-episode-evidence/v2` while retaining
validation support for historical v1 evidence. Its closure records whether the
origin covers original initial requests, a segment only, or a terminal-only
snapshot; continuation envelopes recursively retain a validated predecessor
only when its nonterminal final boundary exactly equals the current segment
origin. A matching terminal reference binds win/tie, winner, final boundary,
and both players' observation IDs, cursors, and normalized-prefix hashes.
Completion of that capture envelope does not set
`faithful_complete_episode`, which remains `false`.

| Required case | Implemented evidence and result |
|---|---|
| Continuous fresh episode to win | Existing deterministic source-engine run commits 55 transitions; both original owned requests and all successor boundaries are retained, terminal win evidence matches both perspectives, `complete_capture=true`, and actor-only DATA-001 rows publish. |
| Source-derived tie | Pinned Showdown 0.11.10 restored battle calls `endTurn()` through the accepted turn-limit warning and tie. Both raw prefixes retain CE-02D's exact public `bigerror` lines followed by `|tie`; the terminal-only snapshot has zero transitions and no decision rows. |
| Terminal after one-sided progression | Reuses the accepted queued-opposing-Memento Revival fixture. P1 has the sole committed actor row; terminal observations for both players have null requests, and no P2 action or DATA-001 row is fabricated. |
| Resumed segment with predecessor | Replays committed deterministic boundaries into the session, then resumes the final transition with the prefix envelope. Recursive predecessor/origin joins validate and the root fresh envelope is `complete_capture=true`. |
| Resumed segment without predecessor | The same continuation remains valid as `segment_only`, with `complete_capture=false`; it cannot claim the original request-to-terminal chain. |
| Zero-transition terminal | Restored source tie is represented as `terminal_only`; it retains matching outcome evidence without inventing transitions, actions, requests, or rows. |
| Rehashed adversarial candidates | TypeScript and Python reject winner/outcome/cursor/final-reference/origin-coverage, ownership, gap, reorder, duplicate, prefix, and forged-origin changes. The full Python result path exits 2 with empty stdout before DATA-001 output; TypeScript validation preserves the candidate and committed result. |

The changed files remain within the episode evidence runner/validator, focused
episode and accepted Revival tests, the coverage manifest, and existing
contract/architecture/workflow/status records. Existing actor-only publication
and privacy rules remain in force: no simulator snapshot, seed, hidden roster or
set, foreign request, or future suffix is retained in the envelope. The two
changed TypeScript source files, Python validator, and focused TypeScript tests
were already present in `local_coverage_sources.files`.

Focused validation on the final source/test set: sim-core build passed; focused
episode and Revival suites passed 35/35; Python pipeline publication tests
passed 43/43; `git diff --check` passed. All synthetic coverage drift assertions
passed. The coverage checker confirms the local digest is reproducible, but
exits 1 because `reviewed_sha256` intentionally remains the prior
`1813f333a918cdf81c2f754ed64b53d29eb77ca3c75f8de9d32d765b96042db2` until
separate CE-06B review. The manifest's local digest is
`5486e61f6c8ab36c2a5bc2155fc1344d3306cfe21cdda1ba7c2d36e4b333915e`; no
reviewed digest or prior scoped attestation was changed.

This is an implementation checkpoint, not CE-06B semantic attestation or
complete-episode acceptance. CE-08A and CE-08B still own the final positive
complete-episode evidence and stop-classification/review packet; remaining P0
closure rows remain open. Datasets, training, and live-model behavior are not
enabled. `faithful_complete_episode:false` remains required.

### CE-06B scoped review verdict (2026-10-06): accepted

The expedited independent review found no material CE-06B findings. The
continuous win envelope joins both original owned requests, every committed
two-perspective boundary, and matching final win evidence. The source-restored
turn-limit tie retains both final perspectives and only the already accepted
CE-02D raw warning. A terminal after one-sided Revival retains the waiting
side's boundary without fabricating its action or DATA-001 row. A resumed
segment inherits initial coverage only through the recursively validated
predecessor/origin chain; without it, the segment stays incomplete.

The fully rehashed origin/ownership, outcome/winner, cursor/final-boundary,
gap, duplicate, reorder, prefix and forged-origin candidates reject in
TypeScript and in Python's full-result validation before publication. Invalid
Python results exit 2 with empty stdout, and TypeScript preserves committed
evidence. Valid win, tie, one-sided, linked continuation and unlinked segment
controls pass. The envelope remains free of snapshots, seeds, hidden rosters or
sets, foreign requests and future evidence; actor-only DATA-001 behavior is
unchanged.

Source hashes match the implementation checkpoint. Fresh build, focused
TypeScript tests (35/35), Python publication tests (43/43), coverage synthetic
self-tests and `git diff --check` pass. The reproduced local digest
`5486e61f6c8ab36c2a5bc2155fc1344d3306cfe21cdda1ba7c2d36e4b333915e` is now
bound by the manifest's local and reviewed CE-06B digest fields. This verdict
attests only CE-06B. It does not accept CE-08A, CE-08B, PIPELINE-002 as a whole,
or complete-episode fidelity. `faithful_complete_episode:false` remains
required.

### CE-08A P0 reconciliation matrix (2026-10-06, in progress — blocked)

The expedited pre-edit reconciliation reuses accepted evidence only within its
recorded scope. It does not promote those scopes to full FCE-01–FCE-07 closure.
The pinned source/config identity is `pokemon-showdown@0.11.10`, format
`gen9randombattle` / `gen9` / singles / random. No implementation, test, or
coverage-source changes are made while the positive-suite prerequisites below
remain unresolved.

| Ordered P0 row | Accepted and reusable source witness/test | Open reachable shape or semantic gap |
|---|---|---|
| CE-01A / CE-01B | Accepted generated raw-only controls in `sim-core/tests/singlemove.test.ts`; scoped verdicts at audit lines 57–92. | None identified within the exact accepted forms. |
| CE-02A / CE-02B / CE-02C | Accepted grammar/audience controls in `sim-core/tests/protocol_contract_validation.test.ts`, `sim-core/tests/pipeline_integration.test.ts`, and `trainer/tests/test_pipeline_record.py`; CE-02 verdict at lines 653–661. | Reusable only for those scoped contracts; broader semantic closure still depends on FCE-01. |
| CE-02D | Accepted source warning witness in `sim-core/tests/protocol_contract_validation.test.ts:169–244`; source `Battle.maybeTriggerEndlessBattleClause`, `sim/battle.ts:1757–1767`; verdict at lines 705–724. | Exact warning grammar is closed. The source tie fixture is terminal-only and supplies no original-request episode chain. |
| CE-03A | Accepted direct generator ledger; reuse `sim-core/tests/simulator_coverage.test.ts` and `sim-core/scripts/check-simulator-coverage.cjs`; verdict at lines 772–788. | Manifest source dispositions below remain unreconciled with the accepted source-proof narrative. |
| CE-03B | Accepted assigned source-proof matrix B01–B32 and `sim-core/tests/simulator_coverage.test.ts`; verdict at lines 1106–1118. | **BLOCKER — FCE-01-MANIFEST-AUDIT-DISPOSITION-DRIFT:** the coverage manifest still records five computed `addVolatile` call families and `Pokemon.addLinkedStatus(linkedStatus)` as `unknown fail closed`; its `review.known_gaps` and `docs/PROJECT_STATUS.md` also retain generic lifecycle/semantic gaps. Reconcile those dispositions against the later accepted source proofs before claiming zero unresolved reachable shapes. |
| CE-04A | Reusable narrow lifecycle witnesses: `sim-core/tests/spirit_shackle.test.ts`, `sim-core/tests/repeat_use.test.ts`, `sim-core/tests/singlemove.test.ts`, and the CE-04-LINK verdict at line 1501. | No aggregate CE-04A verdict; C17/C15 volatile lifecycle and the manifest's duration/source/lock-target gaps remain an FCE-01/FCE-04 reconciliation dependency. |
| CE-04B | Accepted Roost/active-Transform faint witness in `sim-core/tests/roost.test.ts`; verdict at lines 1777–1797. | None within its reviewed Roost boundary. |
| CE-04C | Accepted public stage-transfer source/evidence closure in `sim-core/tests/public_stages.test.ts` and `sim-core/tests/ability_callback.test.ts`; verdict at lines 2245–2277. | None identified for scoped reachable public stage routes. |
| CE-04D | Accepted scoped witnesses in `sim-core/tests/entry_hazard.test.ts`, `sim-core/tests/screen.test.ts`, and `sim-core/tests/court_change.test.ts`; verdicts at lines 1811, 1980, and 2057. | No aggregate all-side-condition closure; general side-condition lifecycle remains in the manifest's known gaps. |
| CE-04E | Accepted finite field witnesses in `sim-core/tests/weather.test.ts`, `sim-core/tests/terrain.test.ts`, and `sim-core/tests/trick_room.test.ts`; verdicts at lines 1843, 1889, and 1908. | No gap found in reviewed finite families; no general field-state closure is claimed. |
| CE-04F | Accepted finite ability/item/status witnesses in `sim-core/tests/ability_callback.test.ts`, `sim-core/tests/item.test.ts`, and `sim-core/tests/major_status.test.ts`; verdicts at lines 1336, 1955, 2149, and 2161. | General callback composition remains an FCE-01/FCE-04 source-disposition dependency. |
| CE-04G | Accepted delayed-effect witnesses in `sim-core/tests/wish.test.ts`, `sim-core/tests/healing_wish.test.ts`, and `sim-core/tests/future_sight.test.ts`; verdicts at lines 348, 369, and 1406. | No aggregate slot-effect sufficiency verdict; accepted finite public consequences remain scoped. |
| CE-05A | Reusable forced-switch/hazard witnesses in `sim-core/tests/forced_switch.test.ts` and `sim-core/tests/entry_hazard.test.ts`. | None identified for ordinary supported replacement pairs. |
| CE-05B | Accepted request-pair/source controls in `sim-core/tests/pipeline_integration.test.ts` and `sim-core/tests/pipeline_episode.test.ts`; verdict at line 1643. | Reusable only for the accepted stable request pairs; broader closure still depends on FCE-01. |
| CE-05C | Accepted bounded bench-revival progression in `sim-core/tests/revival.test.ts`; verdict at line 1593. | Excluded active-target, active/fainted-reviver, and simultaneous variants remain source-proof exclusions, not positive witnesses; no new gap was established in this reconciliation. |
| CE-06A | Accepted origin/privacy/tamper evidence in `sim-core/tests/pipeline_episode.test.ts` and `trainer/tests/test_pipeline_record.py`; progress verdict at lines 725–747. | None in the accepted envelope/privacy scope. |
| CE-06B | Accepted terminal/segment controls in `sim-core/tests/pipeline_episode.test.ts` and `sim-core/tests/revival.test.ts`; verdict at lines 2326–2352. | Its tie evidence is explicitly `terminal_only`, so it cannot satisfy CE-08A's complete tie path. |
| CE-08A | Existing complete normal win in `sim-core/tests/pipeline_episode.test.ts:404–520` is reusable for initial requests, committed chain, publication, and tamper controls. | **BLOCKER — CE-08A-TURN-LIMIT-ORIGIN-CHAIN:** the only source-derived turn-limit tie starts from a restored turn-989 state (`pipeline_episode.test.ts:318–331`) and asserts zero commits plus `complete_capture:false` (`:535–568`). **BLOCKER — FCE-07-SIMULTANEOUS-OUTCOME-WITNESS:** FCE-07 requires simultaneous outcome evidence, but the repository has no source-engine simultaneous-KO/tie episode from original requests; `settling.test.ts:147` is a synthetic `forcetie` control. |
| CE-08B | Existing stop controls in `sim-core/tests/pipeline_episode.test.ts` and Python publication tests can be reused by the downstream stop/final-review task. | Downstream P0 row; not evaluated or implemented in CE-08A. |

FCE-01, FCE-02, and FCE-07 therefore remain open. Do not add a selective
terminal-snapshot success case to stand in for a complete source-engine episode.
Resolve the named source/disposition blockers before resuming CE-08A. The audit
preserves all prior scoped verdicts, and `faithful_complete_episode:false`
remains required.

### CE-08A blocker closure batch — pre-edit matrix (2026-10-06)

This is the single pre-edit matrix for the authorized three-blocker batch. The
source identity is pinned to `pokemon-showdown@0.11.10`, format
`gen9randombattle` / `gen9` / singles / random. A passing fixture must start
from ordinary owned initial requests; source restoration is admissible only
when its serialized predecessor and episode origin are identity- and
semantically bound to that initial chain.

| Blocker / pinned source path | Valid evidence chain and expected envelope state | Privacy boundary and positive/negative tests | Failure conditions |
|---|---|---|---|
| **CE-08A-TURN-LIMIT-ORIGIN-CHAIN** — `sim/battle.ts` (`maybeTriggerEndlessBattleClause`, `endTurn`), `sim/battle-actions.ts`, `data/random-battles/gen9/sets.json`, and the runner in `sim-core/src/pipeline_episode.ts` | Fresh source-generated teams and both original v2 requests → only owned legal actions through each committed boundary → exact CE-02D warning on both prefixes → source `|tie` terminal. A restored continuation is valid only when every predecessor commit binds back to the original p1/p2 boundary. Envelope: contiguous commits/cursors, continuous raw prefixes, `original_initial_requests`, complete capture, tie winner, terminal requests null. | Keep `bigerror` raw-only and exact; no snapshot, seed, hidden set/roster, private request, or post-terminal evidence. Test both sides, tie, null requests, cursors, prefix, restore/replay, Python publication, and rehashed origin/gap/outcome/final-boundary candidates. | Any turn-number edit, terminal-only origin relabeled complete, missing predecessor, invented terminal action/request/row, warning grammar broadening, chain join failure, or invalid Python output. |
| **FCE-07-SIMULTANEOUS-OUTCOME-WITNESS** — `sim/battle.ts` (`faintMessages`, `checkWin`, `endTurn`), relevant `data/moves.ts`/`data/abilities.ts` callbacks, random roots in `data/random-battles/gen9/sets.json`, and `gen9/teams.ts` selector | Find a source-engine singles route from both original requests whose source execution produces the specified simultaneous/tie terminal; retain every request-derived commit through matching terminal evidence. Expected envelope is complete and two-perspective, with agreement on tie/winner and no follow-up request or fabricated terminal decision. If source review proves no operative route, record the complete call/callback/format no-route proof instead of a synthetic positive. | No `forcetie`, injected terminal state, protocol-only witness, foreign request, seed, snapshot, hidden set, or future suffix. Test mirrored perspectives, restore/replay, actor-only publication and Python; if no route, source-closure tests must bind the route proof and reject invented simultaneous evidence. | A synthetic terminal, untraced callback/indirect route, unowned action, missing side evidence, post-terminal choice, disagreement, or a no-route claim based only on direct move membership. |
| **FCE-01-MANIFEST-AUDIT-DISPOSITION-DRIFT** — pinned computed-call sites in `data/moves.ts`, `data/abilities.ts`, `data/conditions.ts`, `sim/battle-actions.ts`, `sim/pokemon.ts`; authoritative manifest `sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json`; source proofs B01–B32 and later CE-03B audit rows | Reconcile each of the five computed `addVolatile` families plus `linkedStatus` against source-backed audit dispositions and focused tests. Manifest, audit, and checker must agree on reachability/value set, projection/raw/private/stop treatment, evidence, and current fail-closed behavior. | Do not expose copied or linked targets/parameters. Tests cover current pinned source paths and show both intended evidence and rejection when a disposition/evidence/source identity drifts; retain fail-closed behavior for unknown emitted values. | Any `unknown` path claimed closed only by a broad narrative, unsupported widening of the manifest, stale “known gaps” contradicting accepted source proofs, or checker acceptance of manifest/audit drift. |

No implementation or fixture result is presumed by this matrix. Each item closes
only on the evidence and failure conditions in its row; `faithful_complete_episode:false`
remains required, and this batch does not perform final CE-08A positive-suite
attestation.

### CE-03B computed `addVolatile` manifest reconciliation (2026-10-07)

The earlier C10–C15 inventory rows remain the historical discovery and blocker
record. The later accepted source proofs B05/B06/B09/B11/B12/B13 refine those
rows' current dispositions; they do not broaden the protocol grammar or remove
the unknown-emission stop. The coverage checker now compares this table with
the manifest, pinned source candidates, and the focused tests. A new or newly
reachable computed value remains rejected until separately classified.

| Proof | Source file | Argument | Disposition | Known values (sorted) | Focused tests | Failure rule |
|---|---|---|---|---|---|---|
| B05 | data/moves.ts | volatile | source-proven-unreachable | dragoncheer,focusenergy,gmaxchistrike,laserfocus | tests/psych_up.test.ts; tests/simulator_coverage.test.ts | Unknown or newly reachable computed emissions reject before projection and Python publication. |
| B06 | data/abilities.ts | volatile | source-proven-unreachable | dragoncheer,focusenergy,gmaxchistrike,laserfocus | tests/ability_callback.test.ts; tests/simulator_coverage.test.ts | Unknown or newly reachable computed emissions reject before projection and Python publication. |
| B09 | data/conditions.ts | effect.id | finite-reachable-raw-only | meteorbeam,solarbeam | tests/singlemove.test.ts; tests/simulator_coverage.test.ts | Unknown or newly reachable computed emissions reject before projection and Python publication. |
| B11 | sim/battle-actions.ts | move.id | finite-reachable-raw-only | bloodmoon,gigatonhammer | tests/repeat_use.test.ts; tests/simulator_coverage.test.ts | Unknown or newly reachable computed emissions reject before projection and Python publication. |
| B12 | sim/battle-actions.ts | moveData.volatileStatus | finite-reachable-inventory | confusion,curse,destinybond,disable,encore,flinch,glaiverush,healblock,leechseed,lockedmove,magnetrise,mustrecharge,noretreat,partiallytrapped,protect,roost,saltcure,sparklingaria,substitute,taunt,yawn | tests/simulator_coverage.test.ts; tests/pipeline_integration.test.ts | Unknown or newly reachable computed emissions reject before projection and Python publication. |
| B13 | sim/pokemon.ts | linkedStatus | finite-reachable-raw-only | trapper | tests/spirit_shackle.test.ts; tests/simulator_coverage.test.ts | Unknown or newly reachable computed emissions reject before projection and Python publication. |

The separate `sim/pokemon.ts|volatile` copy loop remains represented for its
finite inventory values; B07 records that the crit-volatile copy branches have
no generated singles route. This table does not claim aggregate FCE-01 closure:
other inventory rows and FCE-04 truth/sufficiency gates remain subject to their
scoped acceptance criteria. `faithful_complete_episode:false` remains required.

### CE-08A three-blocker closure batch — execution checkpoint (2026-10-07)

The simultaneous-outcome and manifest/audit-drift items have focused evidence;
the complete turn-limit source run is still under validation at this checkpoint.
This batch does not attest CE-08A or complete-episode fidelity.

| Blocker | Checkpoint disposition | Evidence and remaining boundary |
|---|---|---|
| **CE-08A-TURN-LIMIT-ORIGIN-CHAIN** | **Source chain passes; intermediate actor-publication evidence remains open.** | `sim-core/tests/pipeline_episode.test.ts` builds a fresh `gen9randombattle` episode from original owned requests, commits an explicit first joint-action predecessor, then continues through legal switch choices to the source turn-1000 tie using the snapshot-restoring integration path. It asserts both original requests, every step/cursor/prefix join, exact CE-02D warning, terminal tie/null requests, Python validation of the full predecessor-plus-segment envelope, and rehashed outcome/origin rejection. The focused rerun passed in 599.6 seconds. It separately publishes p1/p2 bundles at the original and terminal-adjacent boundaries. However, full-result Python mode validates every actor bundle before returning DATA-001 rows; evidence-only envelope validation plus those four endpoint rows does not validate intermediate tie-run actor records. The prior all-row attempt was interrupted after 34 minutes, so this publication subcriterion remains open pending a bounded cached/bulk validation path. |
| **FCE-07-SIMULTANEOUS-OUTCOME-WITNESS** | **Source witness and focused checks pass.** | Pinned `data/moves.ts:3604–3640` Destiny Bond faint callback queues the source faint; `sim/battle.ts:2440–2532` drains both faint events and resolves the actual terminal outcome. `sim-core/tests/pipeline_episode.test.ts` uses the accepted generated Froslass witness plus a controlled opposing Snorlax in the real `gen9randombattle` source engine, starts from both original requests, mirrors Froslass across p1/p2, checks both faint records, matching win/null terminal requests, deterministic restoration/replay, and Python publication. A fully resealed terminal-outcome tamper rejects in TypeScript without mutation and in Python with exit 2/empty stdout. This is a simultaneous-knockout win witness; the independent source turn-limit route supplies the tie witness. No `forcetie` or injected terminal is used. |
| **FCE-01-MANIFEST-AUDIT-DISPOSITION-DRIFT** | **Crosswalk reconciliation and drift self-tests pass; aggregate FCE-01 remains open.** | B05/B06/B09/B11/B12/B13 now agree between the manifest, pinned source candidates, this source-proof table, and focused test references. The checker derives the 21 B12 candidate values and current classifications, requires B05/B06 generated-singles no-route guards, compares audit/manifest dispositions and values, and rejects drift for each path. Other FCE-01 inventories and truth/sufficiency gates remain outside this batch. |

The coverage self-tests and source/provenance checks pass against the final
crosswalk. The normal checker stops at its required separate semantic-review
digest because `reviewed_sha256` intentionally remains at the prior review
value; this batch does not perform that review or attest CE-08A. The local
digest is updated independently. `faithful_complete_episode:false` remains
required.

### CE-08A blocker-batch review checkpoint — publication evidence finding (2026-10-07)

The turn-limit predecessor/origin chain is source-derived and structurally
valid from both original owned requests through the turn-1000 tie. The
simultaneous Destiny Bond witness is a real pinned `gen9randombattle`
source-engine execution from original requests, with no `forcetie` or injected
terminal. B05/B06/B09/B11/B12/B13 remain consistent across pinned source,
manifest, audit, and the coverage checker; focused audit-disposition mutation
controls now cover all six rows. Aggregate FCE-01 remains open.

The blocker-batch attestation is withheld because the turn-limit test validates
the complete Python envelope but publishes only predecessor and terminal-
adjacent actor bundles. The evidence-only bridge emits a receipt; the full-result
bridge validates every actor bundle before emitting DATA-001. Endpoint bundles
do not establish acceptance of the intermediate tie-run actor records. The
bounded CE-08A follow-up is to add a cached/bulk Python validation path that
reuses only already-validated immutable boundary/prefix work while still
validating each current-segment actor bundle's ownership, action, transition,
privacy, and DATA-001 record fields. It must publish/count every actor row,
preserve one-sided actor-only behavior, and reject a rehashed invalid middle
row with exit 2 and empty stdout. The predecessor transition is published
separately because continuation results intentionally do not republish nested
predecessor actions. No blocker-batch digest is attested here, and
`faithful_complete_episode:false` remains required.

### C17/C20 evidence-derived lifecycle closure verdict (2026-10-07, accepted scoped)

Independent review accepted the evidence-derived `public-typed-state-lifecycle/v1`
boundary for C17 and C20 from implementation digest
`9319ea2131a777315e2194240cd2cd3bc18458676a7651a18e1f18161f2836c2`.
The review verified exact one-row canonical roster joins for projected
Substitute, complete own/opponent side-condition field compartments, lifecycle
replay before legacy compatibility, and fully rehashed ordinary/v1/v2 rejection
controls. Python rejects invalid candidates before DATA-001 with exit 2 and
empty stdout; TypeScript preserves committed evidence. Raw-only evidence and
view-less historical observations with no derived typed state remain compatible.

This accepts only C17/C20. C22/C23 remain aggregate FCE-01 blockers; CE-08A,
CE-08B, PIPELINE-002, and complete-episode fidelity remain unaccepted.
`faithful_complete_episode:false` remains required. `reviewed_sha256` is left
unchanged because it is a wider source-set binding than this scoped verdict.

### CE-08A turn-limit actor-row publication sweep — scoped review verdict (2026-10-07): accepted

The independent review found no material finding in the publication sweep. The
cache is constructed only after validation of the immutable evidence envelope,
including recursive predecessor/origin, terminal, cursor, and prefix-chain
checks. Compact beliefs are reconstructed and verified against their canonical
identity, authenticated observation references, history, and provenance before
use. Each actor row is then derived from its retained commit and passes the
ordinary bundle validator for ownership, canonical action, observation/belief,
transition, cursor, prefix, lineage, privacy, and DATA-001 validation. The
only reused work is exact protocol parsing, prefix serialization, and
DATA-001 prefix hashing already proven for the same envelope observation.

The deterministic source path binds the original p1/p2 requests through its
validated predecessor to the turn-1000 tie. It emitted and validated 1,996
current-segment actor rows without a waiting-side row; the predecessor's two
rows separately passed ordinary bundle publication. The rehashed middle-row
control retains the p2 action's canonical identity and derives the matching
candidate transition action ID, then reaches the intended p1 ownership check.
TypeScript rejects it without changing committed evidence; Python exits 2 with
the ownership diagnostic and empty stdout, after buffering all output.

Build, focused v2 sweep control, Python record/lineage suite (54 passed),
coverage reachability self-test, and `git diff --check` passed against the
reviewed files. The manifest's local coverage source digest is attested only
for this publication-sweep closure. This verdict does not attest CE-08A itself,
CE-08B, PIPELINE-002, or complete-episode fidelity.
`faithful_complete_episode:false` remains required.

### CE-08A turn-limit actor-row publication sweep — implementation checkpoint (2026-10-07)

The publication-evidence finding above is closed within this bounded follow-up.
The `pipeline-episode-publication-sweep/v1` bridge validates result metadata,
the complete immutable evidence/origin/predecessor/terminal/prefix chain, and
the actor map once. It then reconstructs each current-segment actor bundle from
its ordered envelope commit and compact canonical beliefs, and applies the
ordinary bundle ownership, action, observation, belief, transition, lineage,
privacy, cursor, prefix, and DATA-001 checks. Only prefix parsing and hashing
already established for the exact joined envelope boundaries are reused. DATA
rows stay buffered until every actor bundle succeeds.

The original-request → predecessor → source turn-1000 tie fixture publishes
all **1,996** eligible current-segment actor rows in **155,435 ms**. The
continuation predecessor is separately published through ordinary bundle mode
and yields its two actor rows. No waiting-side row is created. The accepted
source tie and both original requests remain in the evidence envelope; the
candidate contains no simulator snapshot, seed, hidden set, or foreign request.

The middle-row control transplants the p2 canonical action into p1's actor row
while retaining its canonical action identity; the bridge derives the matching
transition action ID from that action. TypeScript rejects it against p1's owned
request. Python rejects the same candidate with exit 2, the canonical
player-ownership error, and empty stdout. The rejected candidate and the
committed source result/evidence remain unchanged. Valid controls publish all
rows in segment order, including actor-only behavior on one-sided boundaries.

Focused validation passed: TypeScript build; both perspective-envelope sweep
control (12.5 s); turn-limit source-engine sweep (775.5 s total, including
155.4 s for Python bulk publication); Python pipeline-record and dataset-lineage
tests (54 passed); coverage synthetic-drift self-tests; and `git diff --check`.
The local coverage digest is recorded in the progress checkpoint and manifest;
`reviewed_sha256` is unchanged for separate review. This closes only the
intermediate actor-row publication finding. It does not attest CE-08A, CE-08B,
PIPELINE-002, or complete-episode fidelity. `faithful_complete_episode:false`
remains required.

### FCE-01 aggregate reconciliation matrix (updated 2026-10-09, source/evidence closure)

The machine-checkable matrix is `review.fce01_reconciliation` in
`sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json`.
The coverage checker requires exactly C01–C30, their pinned
`pokemon-showdown@0.11.10` / `gen9randombattle` / Gen 9 singles-random source
scope, source/test witness, TypeScript/Python evidence boundary, privacy and
restoration boundary, and an aggregate disposition consistent with the
unresolved rows. Its synthetic checks reject a missing matrix, unsupported C23
scope/false closure, unsupported C22/C23 expansion, invented acceptance, and inconsistent aggregate declarations.

| Current P0 rows / family | Current disposition | Source/test/publication boundary | Record agreement |
|---|---|---|---|
| C01–C05 raw `-singlemove`, aliases, compatibility, and `-singleturn` routes | Accepted scoped raw/no-route/stop dispositions | CE-01, CE-03B B01–B32, `singlemove.test.ts`, `simulator_coverage.test.ts`; unknown or unsupported source forms stop before TypeScript/Python publication. | Later source proof supersedes the historical discovery blockers. |
| C06–C09 protocol grammar, audience, and future unknown stop | Accepted scoped grammar/privacy/stop dispositions | CE-02 validation, integration, and Python publication controls; only owned public/request evidence passes. | Historical prose reconciled; new forms remain fail closed. |
| C10–C16 computed volatile and generator/callback families | Accepted scoped source dispositions | B05/B06/B09/B11/B12/B13 crosswalk plus CE-03A/B; checker binds source, finite values, tests, audit row, and fail-closed unknown emissions. | Manifest/audit/checker crosswalk passes. |
| **C17 typed public volatile lifecycle** | **Accepted scoped — `FCE-01-VOLATILE-LIFECYCLE-TRUTH`** | The reviewed 88-ID atlas types only Substitute; the other 87 volatile values stay raw-only. TypeScript and Python replay exact prefixes, require complete representation, and reject fully rehashed false/omitted state before publication. | Scoped review accepted 2026-10-07; C22/C23 are now registered within independently accepted scopes. |
| C18–C19 temporary types and public stages | Accepted scoped dispositions | CE-04B Roost and B32 Reflect Type no-route; CE-04C stage closure with TypeScript/Python evidence. | Later accepted evidence supersedes stale historical rows. |
| **C20 typed side-condition layers/lifecycle** | **Accepted scoped — `FCE-01-SIDE-CONDITION-LIFECYCLE-TRUTH`** | The reviewed atlas types eight generated roots: capped Spikes/Toxic Spikes layers and presence for six other rooted conditions; 15 unrooted conditions reject. Prefix replay checks starts, caps, end/removal, Court Change, and complete field-compartment representation. | Scoped review accepted 2026-10-07; C22/C23 are now registered within independently accepted scopes. |
| C21 finite field families | Accepted scoped source dispositions | CE-04E finite weather, terrain, and Trick Room witnesses; timers and sources stay private/raw. | Later evidence supersedes historical discovery prose. |
| **C22 callback composition** | **ACCEPTED SCOPED — FCE-01-CALLBACK-COMPOSITION-TRUTH** | covers only the reviewed finite callback crosswalk, requestless invalidation, false-base rejection, and partial authority. B17 generated source/exclusion induction; accepted item/carrier and public-result writers; reviewed Trace/plain/boost/Imposter/permanent-form controls. No generic inference or hidden-default authority. | Registered 2026-10-09 against the independent invalidation verdict; complete-chain execution is separate. |
| **C23 slot-effect sufficiency** | **ACCEPTED SCOPED — FCE-01-C23-SLOT-RESULT-SUFFICIENCY** | covers only enumerated B22 public slot outcomes, health/status/faint representation, privacy/restoration, and validated terminal owner/action authority. Bare observations/envelopes without sufficient authority intentionally reject. | Bounded semantic acceptance registered 2026-10-09. FCE-01 source/evidence closure is reconciled; no CE-08A or episode promotion. |
| C24–C26 progression, Revival, and request pairs | Accepted scoped source/no-route dispositions | CE-05 tests and B24/B26; waiting sides retain evidence without fabricated actions or DATA-001 rows. | Later evidence supersedes historical discovery rows. |
| C27–C28 envelope/origin and terminal delivery | Accepted scoped source dispositions | CE-06A/CE-06B, CE-02D, and accepted turn-limit/simultaneous/sweep witnesses. | Actor-only publication and terminal null-request rules remain intact. |
| C29–C30 diagnostics and out-of-format multi-active forms | Accepted stop/out-of-scope dispositions | B01–B32 and pinned singles format provenance; debug/team data never enters public evidence. | Later source proof supersedes stale historical discovery rows. |

Raw-only families preserve their exact public prefix without inferring typed
state. Typed families remain subject to their listed truth boundary. Stop
families reject before projection/publication and retain the committed boundary.
The current stop ledger S01–S12 is unchanged: stops remain incomplete and are
owned by CE-08B's later cause-classification work.

The current matrix has zero unresolved reachable P0 forms within the pinned
source contract. This is FCE-01 source/evidence closure, supported by the
per-family reconciliation above and the finite C22/C23 independent verdicts;
it does not establish CE-08A positive complete-chain validation or CE-08B stop
closure. The combined short-command timeout (182.032s) and current 1,000-turn
publication witness remain pending. Historical blocker decisions below retain
their original context.

#### FCE-01 reconciliation review correction (2026-10-07)

Independent review found that finite CE-04F callback and CE-04G slot witnesses
had been promoted too far in the first aggregate matrix. C22 and C23 are now
explicit unresolved rows alongside C17 and C20. The checker pins all four current
blockers as non-source-backed unresolved rows and its synthetic controls reject
both an arithmetic-only aggregate edit and a fully updated matrix that attempts
to promote every blocker to `zero-unresolved`. The correction does not change
production behavior, accepted scoped evidence, or CE-08A's withheld state; the
C23 source-route scope was later expanded by the source-derived checkpoint below; its premature acceptance is superseded by the 2026-10-08 independent review correction.


### C17/C20 typed-state boundary implementation checkpoint (2026-10-07, unreviewed)

A shared `public-typed-state-lifecycle/v1` atlas now gives exactly one disposition
to each of the 88 inventoried move volatiles and 23 side conditions. Its source
identity is `pokemon-showdown@0.11.10`, `gen9randombattle`, Gen 9 singles, source
tree `12d83949635889cd10a51a081890f9dfc6d3ed480eacf2a9a0728fb48e8e086c`, and
generated move-candidate digest
`2f34f3af3fa9473eb979b7e81e6e741245457011554d058f31d03b38bc3692f2`. The checker
binds this identity to the current format/generator manifest and fails on an
added inventory ID, missing lifecycle row, disposition drift, a new generated
side-condition root, or missing lifecycle semantics.

The typed volatile subset is Substitute alone. Its public presence is replayed
from start/end and switch/drag/faint/replacement records; only the exact
`[from] Shed Tail` switch can transfer it. The other 87 move-volatiles retain
only validated raw-prefix evidence. The typed side subset is Spikes (cap 3),
Toxic Spikes (cap 2), Stealth Rock, Sticky Web, Reflect, Light Screen, Aurora
Veil, and Tailwind. Hazards use source-backed counts/caps; the remaining rooted
conditions use presence. Exact end/removal evidence clears the map, Court Change
swaps only this set, and switch/faint/re-entry do not affect side state. The 15
side-condition IDs without a generated direct root remain unsupported and fail
closed while indirect callback routes remain C22 work. Timers, source, callbacks,
linked targets, hidden sets, and snapshots remain untyped/private.

TypeScript compares every projected typed map to replay of the retained
normalized prefix before commit. Python independently replays the same manifest
contract before DATA-001 publication. A fully resealed false Substitute map,
hazard count, or screen-presence map is rejected in both runtimes; Python returns
exit 2 with empty stdout, and the committed TypeScript boundary is unchanged.
Existing source-engine suites cover both perspectives, restore/replay, hazards,
caps, screen expiry/removal, Defog/Tidy Up, Court Change, Substitute start/end,
silent switch/drag/faint clearing, and the Shed Tail exception.

This checkpoint implements a proposed C17/C20 closure boundary but does not
attest either row. They remain unresolved in the FCE-01 matrix pending separate
scoped review. C22 callback composition and C23 slot-effect sufficiency remain
open; the aggregate unresolved count stays four, CE-08A remains withheld, and
`faithful_complete_episode:false` remains required. Exact test results, local
coverage digest, and source/test hashes are recorded in the pipeline progress
checkpoint.

### C17/C20 roster-row omission repair (2026-10-07, unreviewed)

Review finding: prefix replay could derive a nonempty Substitute state for a
canonical ident absent from the perspective roster, because both validators
only compared replay against rows that happened to exist. A fully rehashed
record could therefore omit the row and evade the typed-state comparison.
TypeScript and Python now require every nonempty prefix-derived volatile state
to resolve to exactly one canonical roster row on the correct perspective;
missing, duplicate, or wrong-perspective rows reject before publication. This
does not synthesize rows or infer hidden identities. Normal roster visibility,
active aliases, historical identities, and raw-only volatile behavior remain
unchanged.

Fully rehashed controls cover ordinary DATA-001 records and the v2 episode
origin boundary. Valid Substitute rows remain accepted. The omitted-row controls
reach the intended typed lifecycle evidence mismatch; Python exits 2 with empty
stdout, and the committed TypeScript boundary remains unchanged. C17/C20 are
still unreviewed and unattested; C22/C23 remain open, CE-08A remains withheld,
and `faithful_complete_episode:false` remains required.

### C17/C20 view-less v1 replay bypass repair (2026-10-07, unreviewed)

Python publication now replays each retained prefix before applying historical
v1 compatibility for observations without typed view projections. Such a view
can publish only when replay derives no evidence-backed typed volatile or side
condition state. Fully rehashed Substitute and Spikes controls with the typed
projection omitted reject before DATA-001 with exit 2 and empty stdout; a
view-less v1 control whose prefix derives no typed state still publishes. The
ordinary v1 control and existing v2 lifecycle controls remain green. No roster
row is synthesized, no hidden identity is inferred, and v1 identity validation
is unchanged. The local manifest digest was refreshed without changing its
reviewed digest. This repair does not attest C17/C20; C22/C23 remain open,
CE-08A remains withheld, and `faithful_complete_episode:false` remains required.

### C17/C20 partial typed-view bypass repair (2026-10-07, unreviewed)

The TypeScript and Python validators now require a complete representation path
whenever prefix replay derives typed values. Each nonempty volatile ident must
have exactly one canonical roster row on the owning perspective, with its
volatile map present. A derived own/opponent side-condition map must be present
in the matching `field.side_conditions` compartment. Missing or partial
containers reject when they would omit derived state; omitted containers remain
compatible when replay derives no typed value requiring them. Present empty or
misdirected maps do not stand in for a nonempty derived map. Missing perspective
is likewise compatible only when the prefix derives no typed value.

Seven fully rehashed ordinary-record controls cover omitted volatile roster and
roster container, missing field, missing `side_conditions`, missing own and
opponent compartments, and placement in the wrong compartment. Python rejects
each before DATA-001 with exit 2 and empty stdout; TypeScript rejects each
without changing the committed boundary. Direct controls also verify no-derived
partial-view and missing-perspective compatibility. Existing raw-only values
and valid v1/v2 projections are unchanged. The test helper now fills replayed
side maps in legacy positive grammar fixtures that previously appended a typed
side event without its matching v2 map.

Validation passed: build; focused lifecycle, observation, and transition tests
(37/37); v2 episode-origin test (1/1); focused Python typed-state and
publication tests (49/49); coverage checker synthetic self-test; and
`git diff --check`. The normal coverage checker confirms the local digest stored
in the manifest and exits 1 only because its reviewed digest remains
`b68c508274203f8f470d6b98b9bacd24357d7f703fd209e23445dd0e15a20145` pending
separate review. This implementation checkpoint does not attest C17/C20; C22/C23
remain open, CE-08A remains withheld, and `faithful_complete_episode:false`
remains required.

### C22/C23 source-derived public-consequence checkpoint (2026-10-07)

The machine-readable public consequence matrix is
`public_consequence_matrix/v1` in
`sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json`.
It binds source tree `12d83949635889cd10a51a081890f9dfc6d3ed480eacf2a9a0728fb48e8e086c`,
move candidates `2f34f3af3fa9473eb979b7e81e6e741245457011554d058f31d03b38bc3692f2`,
ability candidates `08032a321366a43597b2b629ee84fea98bb3944d8824c4c73a4f25a569539dd0`,
and selector source `06a6f0596e28ad25133336f1115dd7f867051362b6796519d466b89a3496b529`.
The checker recomputes seven route-file hashes, direct candidate slot roots,
Future Sight's imperative `futuremove` route, exclusions, matrix categories,
and the FCE disposition. Source or candidate drift fails closed.

| Matrix ID | Category | Source-derived boundary and evidence |
|---|---|---|
| `ability-callback-roots` | public-private consequence | 203 generated ability candidates plus six B17 form defaults; reveal/copy source and target remain private. Finite CE-04F witnesses do not establish full callback composition. |
| `item-callback-roots` | public-private consequence | Items are computed through pinned `getPriorityItem/getItem` selectors and item callbacks; hidden membership and parameters remain private. B18/CE-04F are finite witnesses only. |
| `status-callback-consequences` | public-private consequence | Generated move/ability/item/condition callbacks may apply/cure status and change HP; retain public or owner-private emitted evidence and split-health audience. Fully rehashed false status/HP/ability/item parity remains C22 work. |
| `callback-public-records` | raw | Keep emitted records and tags as protocol evidence; no typed callback links. `ability_callback.test.ts`, `item.test.ts`, `major_status.test.ts`. |
| `callback-public-typed-consequences` | evidence-typed | Existing bounded projections replay public records; accepted C17/C20 contracts are unchanged. |
| `neutralizing-gas-global-ignore` | source-unreachable | Corrected 2026-10-08: B17 bounds abilities to 203 authored candidates plus six form defaults; Gas is absent from all seeds and cannot be introduced by transfer/copy cycles. Constructed engine/restoration witnesses retain known names, expose source semantics and prove generated-domain unsupported publication. Broader C22 stays open. |
| `wish-pending-slot` | raw | `Moves.wish` stores source, amount, and timing privately; preserve only its move/result records. |
| `wish-resolution` | evidence-typed | Type HP only from emitted heal evidence; `[from]`/`[wisher]` stay raw. |
| `healing-wish-replacement` | public-private consequence | Owner request controls replacement; public HP/status follows emitted evidence and split HP stays audience-bound. |
| `future-sight-pending-slot` | raw | `Moves.futuresight.onTry` calls `addSlotCondition`; retain `-start/-end` raw and omit timer/source/target. |
| `future-sight-resolution` | public-private consequence | Preserve emitted damage/faint and its owner-only exact HP split; infer no pending hit. |
| `revival-selection` | public-private consequence | Pause for the owner's fainted-bench request; the other side waits. Keep slot/source/count private. |
| `revival-resolution` | evidence-typed | Use emitted result for HP/faint/status; no hidden target or roster is inferred. |
| `lunar-dance-no-route` | source-unreachable | Has package slot data but is absent from generated moves and indirect call/copy roots. |
| `doom-desire-no-route` | source-unreachable | Its imperative `futuremove` route exists in source, but Doom Desire and Metronome/Copycat/Mirror Move caller roots are absent from generated candidates. |
| `z-healreplacement-no-route` | source-unreachable | Only `BattleActions.runZPower` creates it for Z-Memento/Z-Parting Shot; no Gen9 Random Singles Z action/item route reaches that call. |
| `unregistered-callback-or-slot-route` | unsupported | Unregistered source, candidate, or output shapes stop until separately dispositioned. |

`wish.test.ts`, `healing_wish.test.ts`, `future_sight.test.ts`, and
`revival.test.ts` use pinned-engine cases for both actors and perspectives,
restore/rollback, switch/drag, faint/replacement, terminal boundaries, and Python
publication. They exercise public outcomes while asserting slot data remains
private. The TypeScript projector and Python publication validator reject
`slotConditions`, `slot_conditions`, and equivalent pending-slot maps before
output. The implementation checkpoint originally claimed C23 closure; the independent review below rejects that acceptance because private-slot-map rejection does not establish truthful HP/status/fainted result maps.

C22 remains a distinct blocker. Current checks do not reject every fully
rehashable false ability/item/status/HP map across every copied or suppressed
callback route; in particular, they do not model Neutralizing Gas's global
ignored-ability state or all of its silent callback consequences. Do not infer
that state or promote callback composition. The FCE-01 aggregate remains
blocked, CE-08A remains withheld, and `faithful_complete_episode:false` remains
required.

### C22/C23 independent public-consequence review correction (2026-10-08)

**Verdict: withhold C22/C23 closure.** The preceding 2026-10-07 implementation
checkpoint established useful source-route and valid-extraction evidence but
prematurely accepted C23. The current reconciliation restores C23 alongside
C22 as unresolved. C17/C20 acceptance and all prior scoped evidence remain in
force; this review adds no production or test changes, no semantic attestation,
and no CE-08A/CE-08B or complete-episode acceptance.

**High: C23 delayed public result maps lack semantic rejection.**
`sim-core/src/typed_state_lifecycle.ts:172` projects only volatile and
side-condition maps; its assertion at line 178 never replays HP, fainted, or
major-status results. `trainer/src/neural/typed_state.py:165` checks the same
subset and forbidden private-slot keys. The validators at
`sim-core/src/belief_state.ts:389` and
`trainer/src/neural/pipeline_record.py:1082` therefore accept forged existing
public result fields after identities are recomputed. Private pending-slot
rejection proves privacy of that map, not sufficiency of delayed public results.

Independent pinned-engine probe: restore a two-member p1 Blissey/Snorlax team
(Wish/Splash, Immunity recipient) and p2 Skarmory (Stealth Rock/Splash), seed
`1,2,3,4`, to a v2 pipeline session. Execute p1 Wish with p2 Stealth Rock, then
p1 `switch 2` with p2 Splash. Both exact prefixes contain
`|-heal|p1a: Recipient|100/100|[from] move: Wish|[wisher] Wisher`.
For each perspective, modify only the successor Recipient row, recompute
observation ID, replace the successor belief's current/history references,
update its output-observation lineage ID, and recompute the belief ID. All
six candidates pass `verify_bundle_identities`, TypeScript
`validateObservableBattleState`, and Python `validate_pipeline_bundle`.
The Python CLI returns exit 0 with 1,270 stdout bytes for every false candidate.
The protocol prefix, request, transition fingerprint and action stay intact.

| Perspective | False successor result | Candidate JSON SHA-256 | TS / Python CLI |
|---|---|---|---|
| p1 | HP `25/100`, ratio `0.25` after public full heal | `8914c5d278c28c176a0687987d72297e8d0199fb9b0e142e960d775e1dd90e2b` | accepted / exit 0 |
| p2 | HP `25/100`, ratio `0.25` after public full heal | `976b613425c783e3cda1cc37ecd67e586b7831e280ca52e2b94b7182eb7bb666` | accepted / exit 0 |
| p1 | `status:brn`, current-turn start, zero elapsed turns after statusless heal | `0ffaf1b8dadd071e2c59d0abe9707cc6cbfa82388fc6ce05bcd91fd1e86ffc7e` | accepted / exit 0 |
| p2 | same false burned result | `8039696262505c5e1fc42f48d52882da9154aeb19a235c5d49cb2ee900d5bdee` | accepted / exit 0 |
| p1 | `fainted:true`, HP `0 fnt`, ratio `0` after public full heal | `7569444fac5448a7593064f611168394e539a1db3bd7ac2dcf4722dbf891e943` | accepted / exit 0 |
| p2 | same false fainted result | `dae3f5bc2a0e0db5c4a616204b8224427f192445bcfd3cce22c6be3708e2fe0a` | accepted / exit 0 |

Positive controls publish unchanged for both perspectives. Fully rehashed
`view.pending_slots:{wish:{endingTurn:3}}` controls reject in TypeScript;
Python returns exit 2, empty stdout, and the private-slot-state diagnostic.
These controls distinguish the semantic result-map gap from slot-map privacy.
The temporary reproduction files are `/tmp/c23-probe.cjs`,
`/tmp/c23-rehash.py`, and `/tmp/c23-{p1,p2}-{hp,status,fainted,private-slot}.json`.
No persisted simulator snapshot or private slot metadata is added to public
artifacts. Follow-up must independently replay affected public/request HP,
status and faint outcomes at exact cursors in both runtimes and reject these
fully rehashed false or omitted maps before C23 can be accepted.

**C22 remains unresolved as previously recorded.** B17/B18 and the 17-row
public-consequence matrix bound generated callback roots and finite output
families; their generic rows do not prove every copy/suppression/transfer/
restoration composition. Neutralizing Gas's global `ignoringAbility` route and
silent End/Start consequences still lack truthful aggregate typed boundaries.
The source hashes and no-route exclusions for Lunar Dance, Doom Desire and
Z-only healreplacement remain reusable source proof, with no new reachability
or callback-composition acceptance.

Fresh checks: TypeScript build passed; seven focused ability/item/status/Wish/
Healing Wish/Future Sight/Revival files passed 75/75; Python pipeline-record
suite passed 45/45. Coverage checking correctly withholds semantic acceptance
because local source `sha256` differs from `reviewed_sha256`. Only the local
source digest is refreshed for these record/checker corrections; the reviewed
digest remains unchanged. FCE-01 has two unresolved rows, C22/C23; CE-08A stays
withheld, CE-08B stays separate, and `faithful_complete_episode:false` is
required.

### C22/C23 repair acceptance matrices (2026-10-08; pre-implementation)

These are acceptance criteria, not completed evidence or an attestation. C22 and
C23 remain unresolved until every applicable row passes. `faithful_complete_episode:false`
and the independent reviewed digest are unchanged.

| C23 writer / route | Independent fact replay | Required representation / negative controls |
|---|---|---|
| switch, drag, replace; optional condition-bearing detailschange (bare sethp has no pinned Gen9 emitter) | Replay health/status in exact prefix order; replacement changes public appearance identity | One correctly sided roster row; public rounded HP; exact owner request HP; omit row/container/HP/status/fainted rejects |
| -damage, -heal, -sethp | Health condition sets ratio/faint and live status; Pain Split emits two separate one-target -sethp records | Correct last writer wins; split private ratios never become opponent truth; false and contradictory result maps reject |
| -status, -curestatus, faint; cureteam excluded | Apply/cure/faint closes status lifecycle; zero HP damage precedes faint status clear; cureteam has only gen2/gen4 mod emitters | Required fields and status evidence; false status/faint and wrong side reject; hidden sleep/toxic counters stay private |
| Wish | Delayed result uses ordinary heal writer, exact Wish/wisher grammar | Reproduce exact six review probes p1/p2 × HP/status/faint; identities/joins fully rehashed; valid controls unchanged |
| Healing Wish, Revival Blessing | Silent cure is established by emitted heal; Revival can target bench | Both perspectives, actual restored continuation and publication; no pending-slot or hidden exact HP/counter fields |
| Future Sight | Delayed damage uses ordinary damage/faint writers | Both perspectives, restored continuation; missing/false fields and ordinary/full episode entrypoints reject |
| request authority and unknown | Current addressed owner request supplies exact health; public-only health stays public precision; absent evidence makes no invented assertion | Current request and public rounding must be compatible; requestless terminal uses final public evidence; preserve unknown/private distinctions |

| C22 source / consumer | Acceptance criterion | Required witnesses / limits |
|---|---|---|
| `Pokemon.ignoringAbility`, `Abilities.neutralizinggas.onSwitchIn/onEnd` | Preserve a known ability name; distinguish name from effectiveness; global gas affects eligible active abilities | Both sides, multiple gas sources, gas start/departure/faint, silent End/Start, restored continuation |
| exemptions | Respect cantsuppress, notransform, Gastro Acid precedence, Ability Shield, Gas itself, transformed gas, commanding | Source reachability or explicit exclusion for each; never derive opponent loadout from species |
| every ability field consumer | Determine whether each consumer needs a name or effective ability; unknown effectiveness must not assert effective callbacks | Source inventory across TS/Python projection, damage, featurization, belief and publication; name retained when valid |
| callback HP/status/item/ability outcomes | Public/request facts independently validate every existing typed assertion | Reveals/change/copy/suppress/restore plus source-backed broader callback witnesses; fully rehashed omission/false/wrong-side matrix |
| privacy / closure | No hidden callback source, slot, counters, opponent ability inference or exact HP | Actual source witnesses, both perspectives and deterministic restore; valid source controls pass; publication rejection leaves candidates/commits unchanged |


### C22/C23 bounded repair checkpoint (2026-10-08)

**Implementation evidence; closure withheld.** The six reviewed false Wish
results now reject in both runtimes. C23 nevertheless remains open because a
living, unrevealed Illusion can end a battle after current requests disappear.
C22 remains open for the broader callback atlas. Neither row is promoted; the
independently reviewed digest is unchanged and
`faithful_complete_episode:false` remains mandatory.

#### Acceptance matrix disposition

| Matrix row | Result | Evidence and remaining limit |
|---|---|---|
| C23 ordinary health/status/faint writers | Pass bounded replay | Independent `public_health.ts` / `public_health.py` replay switch, drag, replace, damage, heal, one-target sethp, status, cure and faint in observable order. Zero-HP damage preserves status until faint. Pain Split emits two separate records (`data/moves.ts:13599-13602`); bare sethp has no Gen9 emitter and cureteam is mod-only. |
| C23 precision / owner authority | Pass bounded replay | `Pokemon.getHealth` (`sim/pokemon.ts:1990-2020`) supplies ceil percentages and 99 below full. The latest addressed request supplies exact self HP. Requestless retained exact self HP can only be checked for internal ratio consistency and membership in the public rounding bucket; no hidden exact numerator is invented. |
| C23 representability | Pass bounded negative controls | Unique correctly sided rows and derived HP/status/fainted/active fields required. Missing fields, rows, containers, duplicate/wrong-side rows and contradictory values reject. Historical v1 view-less compatibility cannot conceal switch-derived facts. Existing lifecycle/owned-request diagnostics retain precedence. |
| C23 Wish six independent-review probes | Pass | All six unchanged candidate JSON hashes from the preceding review still verify identities, now reject with the public-health diagnostic in TS and Python CLI exit 2 / empty stdout. Both original controls retain exit 0 / 1,270 stdout bytes. Pending-slot controls remain privacy rejects. |
| C23 source siblings / publication | Pass bounded ordinary paths | Actual restored Wish, Healing Wish, Future Sight and actor-only Revival Blessing bundles run the shared full rehash matrix at input and successor whenever the affected identity exists. Original committed bundles and valid publication bytes remain unchanged. Full-result Wish20, sibling36 and terminal sweep6 controls are separately recorded below. |
| C23 living terminal Illusion identity | **Unresolved, fails closed** | Current own request binds Actual to public Disguise, but terminal has no current request and no replace. Two mirrored direct/restored native source tests prove the transition, then verify pipeline rejection preserves the prior commit. A mutable `view.active`/name alias is explicitly rejected. Validated predecessor request authority is not supplied to the standalone health/projector/belief validators; no view-based fallback is permitted. |
| C22 Gas generated route | Source-unreachable, review pending | The complete B17 bound is 203 authored ability seeds plus six form defaults. Gas is absent; copy/transfer closure has no unseeded introduction. Constructed engine witnesses remain unsupported by generated `dash_reveal` grammar. |
| C22 Gas actual source semantics | Pass constructed harness | Both sides × start/departure/faint/Illusion, deterministic restore, two simultaneous sources, last-source cleanup, Ice Face / Shield exemptions, Slow Start silent End and restart. Session rejection and 24 fully rehashed Gas-record controls preserve committed state and reject at the intended protocol exclusion before publication. |
| C22 names / effectiveness / consumers | Pass bounded repair; aggregate open | Known names survive suppression. Internal effectiveness has active/suppressed/unknown states; unrevealed opponent item exemptions stay unknown. Pinned Gen9 switch requests include the live ability at `sim/pokemon.ts:1126`; current owner live-name/item/suppression mutations execute in the source matrix. Requestless callback truth still requires independent evidence. |
| C22 broader callbacks / complete C23 matrix | **Unresolved** | Existing generic callback rows are not exhaustive ability/item/stage truth proof. Terminal Illusion authority and complete applicable matrix acceptance still need implementation/review. No CE-08A or FCE-01 promotion. |

#### Pinned Gas exclusion and consumer semantics

`sim/pokemon.ts:834-852` gives the precise order: inactive; transformed with
notransform; cantsuppress; Gastro Acid; Shield/Gas exemption; then live,
untransformed, non-ending Gas and commanding exemption. `data/abilities.ts:2834-2895`
emits Gas start, skips transformed sources, marks ending, suppresses redundant
End while another Gas remains, and restarts eligible abilities before switch.
Switch/drag/faint therefore also remove source presence; generic `-end` does
not erase the known Gas name.

The authored Gen9 sets give both Weezing forms only Levitate. B17's six extra
form defaults are Tera Shell, Teraform Zero and the four Embody Aspect forms;
none is Gas. Trace/Transform only copy an already bound ability; clear/switch
restores an already bound base. Skill Swap, Entrainment, Role Play, Doodle,
Simple Beam, Worry Seed and Gastro Acid lack a generated move seed. Mummy,
Lingering Aroma, Wandering Spirit, Receiver, Power of Alchemy and Commander
lack an initial/default seed. Gas additionally has notrace, notransform,
noentrain, failroleplay, failskillswap and noreceiver. There is no literal
`setAbility('neutralizinggas')` root in pinned moves, abilities or Pokemon.
Ability Shield is outside the finite 66-item selector bound. Strong-weather
abilities that trigger additional Gas silent-End handling are outside A;
Commander is excluded by seed and singles. This is an induction over the
bounded source graph, not a random sample or an expanded supported format.

Consumer classification: `action_codec.ts` carries request/name authority;
`belief_fork.ts` reveal matching, `env_manager.ts` fork comparison and heuristic
set filtering compare known identity names. They retain those names.
`baselines/heuristic.ts` damage construction now passes an explicit internal `No Ability` neutral
value when effectiveness is suppressed or unknown. The calculator otherwise
installs the species-default ability for undefined input, including during clone;
a regression checks the neutral constructor and clone while retaining the known
public name. `damage_calc.ts` accepts
explicit diagnostic inputs rather than a public BattleView, so its caller-owned
ability argument is unchanged. Python `provenance_contracts.py` already
separates ability knownness from effective callback state. Existing downstream
feature consumers remain outside aggregate callback acceptance; the new
internal tri-state is not an extra published opponent loadout field.

#### Concrete terminal Illusion limit

Pinned `data/abilities.ts:1996-2034` selects the last living bench appearance,
ends it on incoming damaging hit, and emits replace on End. Dealing the winning
hit does not end Illusion. `sim/battle.ts:1442-1464` then clears both
activeRequest values. `sets.json` has generated Zoroark/Illusion/Dark Pulse
roots, checked directly; the low-level constructed foe is only a minimal
native semantics harness, not an authored team-selection claim. Both actor
roles prove input request `pN: Actual`, public switch `pNa: Disguise`, final win,
no replace, identical restored simulator state and immutable rollback at the
public-health identity boundary. Supplying prior authority from already
validated enclosing input/episode joins is the follow-up; inventing an alias
from mutable result rows would reopen a fully rehashed missing-row bypass.

#### Validation and identity controls

Focused build passed. The eight TypeScript source files (public consequences,
Wish, Healing Wish, Future Sight, Revival, ability callbacks, items and major
status) passed 106/106 in 10.782 seconds before the shared source fixture
extraction; the extraction is rerun below. Python typed-state, pipeline-record,
public-consequence and major-status suites passed 56/56 in 8.44 seconds;
public replay tests separately passed 10/10 in 0.94 seconds.
The parent-owned four initial full-episode regressions passed 4/4 in 28.75 seconds:
Wish full-result 20 fully rehashed candidates, original-to-terminal sweep six
origin candidates, and retained Substitute/owned-request compatibility checks.
Every altered record passes canonical identity verification and exact envelope
input/successor joins before semantic rejection; candidates, committed evidence
and valid controls are preserved. The Gas ordinary controls similarly prove
identities before the exact generated-protocol exclusion.

The ordinary helper's owner ability-name/item/suppression controls run when a
current request contains a live ability. Pinned Gen9 switch requests include
that live ability (`sim/pokemon.ts:1126`) in addition to baseAbility; the
original citation ended before this generation guard. These controls execute
on the actual source owner bundles, including the forced Healing Wish request.
They establish current owner authority only; requestless callback truth and
opponent item presence still require independent public evidence. No dataset,
feature, training or live-model readiness claim follows from these checks.

Sibling full-result publication controls were subsequently added from the same
shared source fixtures, without importing test registration: Healing Wish,
Future Sight and Revival Blessing, both source actors and both observers,
HP/status/faint mutations (36 fully rehashed candidates). Six tests passed
in 7.73 seconds. Revival preserves waiting/nonactor summaries and zero decision
rows; those test-only beliefs are captured from the real session. These are
truthfully labeled continuation segments with complete_capture false, not
relabeled original episodes. The final combined episode rerun is recorded below.

Broader adapter self-review initially rejected nine old synthetic positives
because they omitted derived health rows or supplied stale health. Grammar-only
controls now explicitly complete their synthetic result maps before hashing;
malformed grammar candidates retain their rejection targets. The golden
Illusion fixture uses pinned conditionless replace, preserving its preceding
burn and HP. Actual source consequence matrices never call that synthetic
completion helper. Historical compatibility is not expanded to conceal facts.

The final parent-owned episode run passed 10/10 in 42.323 seconds: the two
retained ownership/Substitute checks and eight added health checks. It includes
Wish20, sibling36, origin sweep6 and one fully rehashed requestless carrier
omission/forged-active redirection candidate. The latter rejects in both full
result and sweep publication with the health diagnostic and Python exit2 /
empty stdout. All affected joins and extant record identities are valid before
semantic rejection. Final `pipeline_episode.test.ts` hash is recorded below.

Final child reruns after fixture extraction: TypeScript build exit0; the eight
source files passed 106/106 in 9.950 seconds; five adapter/contract/extractor/
lifecycle files passed 63/63 in 22.814 seconds; combined five Python suites
passed 66/66 in 8.65 seconds. `git diff --check` passed. Reachability self-test
exit0 includes new exemption-drift and generated-Gas-seed controls. Coverage
normal and full self-test runs still intentionally fail only independent local
semantic attestation after the computed source digest is refreshed. This is
not an acceptance, review attestation or completeness promotion.

#### Repaired implementation identity

These raw UTF-8 file SHA-256 values bind the final implementation candidate, including
the parent-owned episode tests. The manifest separately computes its normalized
local source digest over the complete listed source set; no reviewed digest is
updated by this implementation batch.

| File | SHA-256 |
|---|---|
| `sim-core/src/public_health.ts` | `d569c47a246571961ce6eda1c586b8afd6ea024db6e37647369bada34e149206` |
| `sim-core/src/public_ability.ts` | `10d1178608ed2c251f93744a6777dc9663d72e37e81268c7c42bbcad82b29b71` |
| `sim-core/src/typed_state_lifecycle.ts` | `731d763d9cfc484bff3935128f2fb94819ec5109238743f7d8afb6ec170d9f7c` |
| `sim-core/src/state_extractor.ts` | `0c443a8ea58d1f4697f84613c5189ba5841ea2acb6c857c5f660ad47a63f2b17` |
| `sim-core/src/observable_state.ts` | `2deddd88a30ac86dc1c04792697c55a2d853e97e10af59b69de8c64a5dbc1cff` |
| `sim-core/src/belief_state.ts` | `06f6bd9ebdf2cfbb3e86daaadd43c0bdec5a0bc1d7b52196a909d89a0e5b02c1` |
| `sim-core/src/types.ts` | `3594671834fc26d06e73aabb80844cd83605c836404f2bddb7dcf3fb2648d4dc` |
| `sim-core/src/baselines/heuristic.ts` | `0e7ebdf965834cd2090a90e6d173b7dcce1a9a15ea5ac36a3fb588ab3deb2710` |
| `trainer/src/neural/public_health.py` | `f6e52a1aec40f21e2977efc3e7e0a48e122170a705c77ec25a801586cf39c36e` |
| `trainer/src/neural/public_ability.py` | `ae8eccbe177ac4407abe96e496537b9fe8d853a46e4055fe7962c3ea866916c0` |
| `trainer/src/neural/typed_state.py` | `23832006ec4ed625ba44dc093bf8e0d145dba0b78eb57dadf74635185cc6a63f` |
| `trainer/tests/test_pipeline_record.py` | `5d3524e77508c4c674329a197e5a2fe13d77152dd49b04288ba5f94550234937` |
| `trainer/tests/test_public_consequences.py` | `df9a2467fe76fd608bf13921eb773c79fff955be184768b69d925e5ca39e2e1e` |
| `sim-core/tests/public_consequences.test.ts` | `d6dddc21c464bc695ae22639e9a8c499812ab905deb0b08b7beff6287828bf6a` |
| `sim-core/tests/public_consequence_test_helpers.ts` | `9710ea0e4b52911c2ad04423efec24bca744bbd6d498a369c2e6e6cd8076df2e` |
| `sim-core/tests/wish_fixture.ts` | `ce6b4dd36ce55f1c38b0e96ce7e7381870b8bff2ba28c81850e68f1f73ae077d` |
| `sim-core/tests/slot_consequence_fixtures.ts` | `344612f48b43b25cccd1d0dd1965f9e1989cee008f49a24a2ab94215d4ff2f71` |
| `sim-core/tests/wish.test.ts` | `b46adde74e2df1b2e79c068f123fedbbb16c97ebd98216ca545ce9468c5df097` |
| `sim-core/tests/healing_wish.test.ts` | `67f5904769f5123c45df7f3cb739d79e3b3626353d2d07486646e2d6433bfce2` |
| `sim-core/tests/future_sight.test.ts` | `baa1557fc206bf3c4972199292b5d94764fec33751d3ad5ae455cfc210c166f8` |
| `sim-core/tests/revival.test.ts` | `f033a2f16bb14cccfb5318853dcdb70aafe47a03c0bf5a0dcc943ac90a4b912e` |
| `sim-core/tests/pipeline_episode.test.ts` | `2f8066f7158b455606df222ef5d5f6b365618e1cb55f0c600ba8e03c795f4865` |
| `sim-core/tests/observable_state.test.ts` | `8b7be43a698ba1a4aa974cb45098aade9773df381273e125411f4bd53d2c5e35` |
| `sim-core/tests/observable_state_fixture.test.ts` | `b886bad2a5db48ff5329b6b09da4bd7eef608bdb055ea9ca892a673a804de7d8` |
| `sim-core/tests/protocol_contract_validation.test.ts` | `1afc56a0c564ec70b4020a02e5301b0b5c2679e7743cb0a275e28d89b07eed2c` |
| `tests/fixtures/observable_state_v1.json` | `01bd667fc62425d89b3f8f216d1eac1756a8d63e9052668a836bb0c8d095b79b` |
| `sim-core/scripts/check-simulator-coverage.cjs` | `7173baa30b3777832fe1802b06fe6c7310f341380fe9dbd0e7dcd7a6bd007533` |

Final calculator consumer correction: build exit0 and the eight source suites
passed 107/107 in 10.799 seconds, including the neutral-effect constructor/clone
regression. The `No Ability` placeholder stays inside damage calculation and
never overwrites or serializes a PokemonView/ObservableBattleState ability name.
This supersedes the preceding 106-test source run only; all 63 adapter and 66
Python checks remain applicable because this correction changes the heuristic
calculator consumer and its regression, not publication schemas or validators.


### C22/C23 independent repair review (2026-10-08; findings retained)

**High — C22 public consumed-item presence still accepts a false result.**
`sim-core/src/belief_state.ts:300-309` allows the public opponent marker
`item:has-item`; `sim-core/src/public_ability.ts:85` and
`trainer/src/neural/public_ability.py:68` validate only self-team ability/item
request authority. No independent public item-presence replay validates the
opponent marker against consumption. This is a semantic publication gap within
the existing schema, not a request to expose opponent item names or loadouts.

Independent native pinned source probe: restore a Gen9 Snorlax Eater with
Thick Fat, Sitrus Berry and Belly Drum against Eevee Target using Tackle,
seed `1,2,3,4`, then execute both first moves. Both mirrored actor runs emit
`|-enditem|pNa: Eater|Sitrus Berry|[eat]`, followed by
`|-heal|pNa: Eater|67/100|[from] item: Sitrus Berry`. There is no later item
reacquisition record. The opposite observer's valid successor omits `item`.
Adding only `item:has-item` to that opponent row, recomputing observation and
belief IDs plus current/history/lineage references, preserves the exact public
prefix, request, transition, action and record joins. `verify_bundle_identities`
passes; TypeScript `validateObservableBattleState` accepts the input and
successor; Python CLI publishes with exit 0, 1,255 stdout bytes and empty stderr.
The enclosing original valid controls also verify and publish with exit 0 /
1,255 bytes. The parent independently reproduced both forgeries and controls.

| Source actor / observer | Control SHA-256 | False-item candidate SHA-256 |
|---|---|---|
| p1 / p2 | `00ae58920cbec6418081d38817f37c0d9bdeb7f88bff581a01e4959c3f309f48` | `d609337ca56cb8743b6a9026cb5a0c3d863c4c369d601525db2c6a0d013bb734` |
| p2 / p1 | `dc10d050f671d2a1de536e0460b5005117abce54931d7036a21f440ae1b462e2` | `5a82bc86e2d307c37af9ac3790a08c2a64829f50ed2c5af22a9144804450d9ad` |

Reproductions are `/tmp/c22-item-source-probe.cjs`,
`/tmp/c22-item-rehash.py`, `/tmp/c22-consumed-pN-valid-control.json` and
`/tmp/c22-consumed-pN-false-item.json`. They contain public actor bundles;
private snapshots remain transient in the source harness. No production fix or
new acceptance test was added. Follow-up must replay evidence-derived public
item presence through reveal/consume/remove/transfer/reacquisition and
switch/restore/terminal boundaries, retain absence versus unknown, preserve
hidden item names, and reject fully rehashed contradictions at ordinary/full
result/sweep publication boundaries. The current ordinary accepted probes are
sufficient to withhold C22; full-envelope item forgeries were not tested here.

**High — C23 living terminal Illusion owner binding remains unsupported.**
The two mirrored direct/restored source tests at
`sim-core/tests/public_consequences.test.ts:214-238` prove a valid winning
terminal with no replace after owner requests disappear. The current pipeline
rejects that valid successor and preserves the prior commit. The three focused
root/terminal checks pass because this rejection is the asserted open boundary;
they are not positive complete-episode fidelity evidence. Supplying validated
predecessor owner identity authority remains required. No mutable result-row
alias, unknown opponent identity or inferred hidden roster is authorized.

**Bounded repaired evidence verified.** All 27 raw file hashes in the repaired
implementation identity table match before review-only documentation changes.
The six unchanged original Wish candidate hashes match the preceding review,
verify canonical identities and reject in TypeScript and Python CLI exit 2 /
empty stdout at the public-health boundary. Both original positive controls
still publish with exit 0 / 1,270 bytes; both private-slot controls still reject.
The public writer inventory, last-writer ordering, exact owner/public rounding,
unknown and historical/partial representation, source sibling ordinary/full
result matrices, canonical joins, candidate/commit immutability and privacy
boundaries were inspected. Constructed Gas semantics, exemption order, known
names/effectiveness consumers and bounded generated no-route induction retain
the recorded scope; they confer no generated Gas publication acceptance.

Fresh checks: TypeScript build exit 0; eight source suites 107/107 in 17.270s;
five adapter suites 63/63 in 28.628s; focused episode health/representation
checks 9/9 in 22.977s plus the separately run owner-request check 1/1; Python four
contract suites 56/56 in 8.44s and public-replay suite 10/10 in 1.05s; focused
Illusion root/terminal checks 3/3 in 0.240s. The exact hashes remain those listed
above because review modifies only this audit, status and manifest metadata.
The failed initial Python command named a nonexistent `test_public_health.py`;
it ran zero tests, then the correct suites passed as recorded. Coverage normal
checking must continue withholding independent local semantic attestation.
C22/C23, FCE-01 and CE-08A stay open; the reviewed and prior attestation digests
and `faithful_complete_episode:false` remain unchanged. This review does not
attest aggregate or scoped callback/slot closure.


## C22/C23 implementation checkpoint — restart pause 2026-10-08

**Work paused at the user's restart request. This is an implementation
checkpoint, not a completed repair or independent semantic acceptance.** No new
tests or production changes are authorized by this checkpoint. C22/C23,
FCE-01, CE-08A/B and PIPELINE-002 remain unresolved;
`faithful_complete_episode:false`, canonical identity algorithms/schema versions,
the reviewed digest and all prior attestations remain unchanged. The manifest `sha256` is refreshed to this saved checkpoint only; it does not
attest that the current implementation passed the remaining validation. It must
be recomputed again after resumed implementation and final documentation.

### Changes saved

Shared TypeScript/Python public item replay now distinguishes named possession,
public presence, explicit absence and unknown. Exact `-item`/`-enditem` writers,
ordered switch/drag/replace replay, owned current requests and validated committed
terminal authority govern existing item fields. Opponent presence is the existing
optional `has-item` marker and reveals no private name. Missing fact-bearing
rows/containers, unsupported positive markers, false disposition/last-item and
suppression claims reject. Retained end-item history survives consumption,
switch/re-entry and untouched real bench history beneath Illusion. Magic Room
suppression derives from the public prefix, not the candidate field map.

Requestless terminal owner authority is temporary, nonserialized and bound to
validated predecessor/transition/perspective/ordered stable roster/prefix
continuity. Standalone observation validation has no trusted optional predecessor
parameter. Ordinary linked records validate action/identity/metadata joins before
using authority; full chains validate predecessor closure before their origin.
Failed candidate validation discards authority. Health, item and typed lifecycle
owner joins share this binding without exporting actual Illusion identity to the
opponent. Canonical serialization is unchanged. Source extractor terminal fields
now use final public evidence rather than reinstalling stale cached request
health/item/active fields. Extractor-only history caching is confined to its
append-only internal prefix; external candidate validators replay freshly.

### Inventory and scope

The inventoried existing fields are current item, item_state, last_item and
item_suppressed. Defaults are unknown/null/false; owned requests supply addressed
private current item; public item/end-item writers supply held, consumed/removed
and last item; switch creates a fresh public appearance; replace reconciles it.
`poke` preview item markers are historical preview grammar outside the approved
operative generated route. Transform, forme change and faint do not prove item
removal. Passive item provenance is raw unless an existing typed writer establishes
possession: Sitrus healing follows consumption, Custap/Leppa consumed activations
do not reacquire, and passive damage/healing tags do not invent a held-item writer.
Magic Room has no approved generated Gen9 root here, and no Klutz/effectiveness
inference was added. Native Smeargle White Herb Recycle, Snorlax Belly Drum and
Rotom Switcheroo witnesses are constructed compatibility/mechanics harnesses,
not new generated-root acceptance. Approved selector/root coverage is unchanged.
C22's broader callback/copy/global-composition obligations remain open.

### Completed evidence before the latest terminal-switch changes

These results are saved evidence from earlier source revisions, not hash-bound
validation of every file at this checkpoint:

- New item/identity matrix: 37/37, 2,256.833s; counted ordinary 2,524,
  full-result 196, envelope 200 and sweep 196 adversarial publication cases.
  Native/restored p1/p2 source witnesses cover consumption, restore, transfer,
  unrevealed/revealed terminal Illusion, known real bench health/history, resumed
  predecessor closure and consumption-switch-re-entry. Exact counts must be
  regenerated after the later unknown-marker and normal-terminal additions.
- Focused TS source/record suites: 197/197, 52.755s. Python contract suites:
  121/121, 9.65s. Build passed for those revisions. Accepted profile is Node
  24.21.0/npm 11.19.0 and `.venv-simulator` Python 3.9.6/pytest 8.4.2;
  pip check passed without dependency installation or lock changes.
- Latest focused episode source checks: 4/4, 8.487s, including canonical
  Substitute origin, mirrored Destiny Bond source terminal and resumed closure.
- Parent independently reproduced original identity-valid Sitrus controls
  (TS accept/Python exit 0, 1,255 stdout bytes) and both false-item candidates
  (TS public-item mismatch/Python exit 2, empty stdout). All candidates remained
  immutable. Six original identity-valid Wish forgeries still rejected with
  Python exit 2/empty stdout. Parent verified an earlier 15-file freeze and
  five focused source controls; that freeze predates the latest changes.
- Coverage reachability self-test passed before the latest checkpoint. Normal
  coverage must continue withholding independent semantic attestation.

### Latest failures, process status and next steps

The isolated optimized turn-1000 source tie test failed after 4,248.301s at a
legitimate final public own switch with requests cleared. A concurrent broad
nonlong selection had accidentally imposed heavy contention and was cancelled
at 4,839.770s. These runs are not successful evidence. The direct native near-final
reproduction identified the own-switch rejection and stale cached active flag;
a narrow normal/revealed terminal switch correction was implemented and the
native direct probe now reports a valid terminal. Normal public identity is
allowed only after a reveal or explicit validated owned request **base and
current ability strings for every slot** proving no Illusion route. Missing base
ability or a base/current Illusion ability cannot prove this condition.

The newly added short turn-1000 source/restore/publication regression currently
fails in its negative fixture: `missing-base` deletes both request base ability
and required self-row base field, so it reaches the structural `Self Pokémon view
is incomplete` error before the intended authority error. Resume by preserving
the self field as null while omitting request base ability, then rerun all five
coherent normal-terminal guard mutations in both perspectives and schemas.

Incoming **unrevealed** terminal Illusion switch/drag remains a precise open
implementation obligation. Ordinary/full-result/compact-bulk paths possess a
canonical submitted action and prior validated owned request. Before deciding
this is unsupported, assess the smallest staged action validation: verify the
terminal actor's canonical switch action and exact transition join against the
already validated predecessor, bind only that incoming owned slot, then validate
all remaining records/beliefs/chain joins atomically. A bare envelope lacks this
action and must fail closed when public evidence cannot identify the incoming
owner. Do not infer the actual owner from a nickname or unsigned hash alone.

After that repair: rebuild; finish the enlarged item/identity and coherent
full/envelope/bulk origin/predecessor matrices; run focused TS/Python source and
record suites and explicitly anchored nonlong episode cases; run the optimized
1000-chain test **alone** with visible progress; update current contract wording
and acceptance limitations; record final raw file hashes; run coverage self-test,
normal checker and diff check; recompute the normalized local digest. Do not reuse
old passing results unless exact source/test hashes match the resumed freeze.

All tracked owned sessions are complete or cancelled: 94948 (short normal switch
fixture failed), 86318 (completed), 54196 (matrix completed), 38603 (long tie
failed), 94166 (cancelled), 99771 (Python completed), 78396 (TS completed), 97480
(checker completed). No owned running test session remains and no more tests were
launched after the restart request. No production edit was made during this pause;
only this durable audit checkpoint and its manifest local hash were saved. The
parent additionally confirmed no node/pytest test processes remain, a fresh build
passed, and the exactly selected C17 origin test passed 1/1 in 1.870s with
`--test-isolation=none --test-reporter=spec`. Dependencies, datasets, training,
live applications, PRs and commits were not changed by the batch.

### Raw code/test/checker hashes at pause

These hashes identify saved files, not a final validated freeze.

| File | SHA-256 |
|---|---|
| `sim-core/src/public_item.ts` | `a8c2f60383d91837f74f2c2a46bd9f96976c268858914a538b4cc49c707c399d` |
| `trainer/src/neural/public_item.py` | `7c2410c9327e70c7ff7258a5dcb4991c885b2df64d3532cbee21dcf950bebcbe` |
| `sim-core/src/public_health.ts` | `a4b9ddc52fd7531b82f826b6d42017fb5b0d248b98bf30494578153eeed86934` |
| `trainer/src/neural/public_health.py` | `8c45c85133a1970b1d5d505961d518cd99c7e9394bf504fd9c890bbbd7f175c3` |
| `sim-core/src/state_extractor.ts` | `85ab55e21e338cedeaa6344d566f93e02732ab04f660b40cb79f7756398caf1e` |
| `sim-core/src/observable_state.ts` | `74c3b658809c6a7a6266a328beebc16395c1ea478d4061db0ec5474b38d4e327` |
| `sim-core/src/belief_state.ts` | `908fae0fabdb49c5d8a1ba40e3471abbc3b4b7aa8cacd1ea0cdaecd373f90d2c` |
| `sim-core/src/typed_state_lifecycle.ts` | `a133a8c23d94993aab0ad3a6e8f4b921aaa65f76cf0eb8aa08ff392eea75f083` |
| `trainer/src/neural/typed_state.py` | `6a2c5b42ff8730c3586d0c6441b917d2e524622365ce234056cb6d4b13a22a97` |
| `sim-core/src/pipeline_integration.ts` | `ef28d3b65d29dbe4349e5fdd6d70a7a6eb238aa628295a14fdf334a20370cc25` |
| `sim-core/src/pipeline_episode_evidence.ts` | `3acca8f8711780a5181bc8475cbe604c416b48d9d72a8286e0151d946806512f` |
| `trainer/src/neural/pipeline_record.py` | `6516d16396c42c8f687834a3e68b713f094b15269bc0bc00245edd0fbdf83423` |
| `sim-core/tests/item_identity.test.ts` | `f27ff5012d0a5d347d8b3975866fd59d4b5b547cda22e2938eab0243c098bf64` |
| `sim-core/tests/public_consequences.test.ts` | `48250e82424214a81a4005525453cdd528de6d056322dbe1b4ce49bab173f0ae` |
| `sim-core/tests/public_consequence_test_helpers.ts` | `b5d97594e0f7c12c8e1694300b3dbb61eb7e50c0fbda03b0ee5686173c0ddef6` |
| `sim-core/tests/pipeline_integration.test.ts` | `e830ef61aa2c31f95ee6d43a3acd1e60bd9d03c688ccb8c046020a3c4723abde` |
| `sim-core/tests/observable_state.test.ts` | `9e609b38df6be3697288ea3e5aa8c007a7f9b28e738280ce8c58ba9beb0bbc6f` |
| `trainer/tests/test_public_consequences.py` | `fc24bd67d6cf586819f0ab0b54ab20d3c9c8b5566e5a7530d9ce75c8c6046a6f` |
| `trainer/tests/test_pipeline_record.py` | `fe7e1fc4134680bba283e803cadb17ecbe1ba32e9d1de599e2cc8d8bb9e91f19` |
| `sim-core/tests/pipeline_episode.test.ts` | `2f8066f7158b455606df222ef5d5f6b365618e1cb55f0c600ba8e03c795f4865` |
| `sim-core/scripts/check-simulator-coverage.cjs` | `b279845db1803a54cb07310d00588462bca863415c72679c87f26c3157677b3e` |

### Resumed C22/C23 in-progress checkpoint — 2026-10-08

Production is not frozen and the previous checkpoint local digest is historical evidence only. No long test is running. Resumed exact short controls passed: incoming terminal Illusion with canonical switch and private after-terminal restoration, p1 1/1 (2.912s), p2 1/1 (2.075s); normal source terminal switch 1/1 (14.598s); accepted queued/actor-only one-sided terminal progression 2/2 (0.408s). These are implementation results before the remaining source edits, not final frozen acceptance evidence.

Remaining before freeze: truthful optional item-history projection for an old unrevealed Illusion appearance whose carrier cannot be established by the current addressed request; coherent initial/predecessor alias-origin legitimacy controls; re-entry history omission and sparse waiting-owner negatives; forced-switch private restoration review. Then rebuild and run those exact short tests sequentially. The long turn-limit test will run alone after source freeze with live phase/100-commit progress and a separately bounded Python bulk timeout. Reviewed/prior attestations and `faithful_complete_episode:false` remain unchanged; C22/C23 and the aggregate gates remain open.

### C22/C23 resumed bounded repair inventory and decisions — 2026-10-08

This candidate remains implementation-only. C22/C23, aggregate FCE-01, CE-08A/B and PIPELINE-002 remain OPEN; `faithful_complete_episode:false`, the reviewed digest and all prior attestations remain unchanged.

#### Existing item-field writers and evidence disposition

| Existing writer/path | Eligible evidence and disposition |
| --- | --- |
| `createPokemonView` defaults | Null current item with unknown disposition is an unestablished appearance, not proof of absence; no opponent marker. |
| `selfFromRequest` | Addressed current roster establishes exact current own item and held/absent state. Stable real ident is separate from a public appearance; no opposing request or hidden loadout is exported. |
| `handlePreview` `poke|side|details|item` | Existing preview presence marker is inventoried. Generated Gen 9 random battles exclude preview; legacy preview is retained raw and cannot authorize an unsupported canonical nickname/slot join. No invented activate-item writer is added. |
| `handleSwitch`/drag | New public appearance resets item facts to unknown and saves displaced evidence. A matching nickname is insufficient to retain a named possession: it may be Illusion. |
| `handleReplace` | Moves current appearance facts to revealed actual and restores prior bench evidence. A later reveal identifies its current appearance, not an earlier departed carrier. |
| `handleItem` `-item`/`-enditem`, accepted bare aliases | Exact reveal/acquire/restore versus consume/remove writer order. Berry `[eat]`, Gem source, and finite tagless `useItem` forms are consumed; Air Balloon tagless pop is removed. Existing named `last_item` and `item_state` are checked, not repaired. |
| Recycle/Trick/Switcheroo | Accepted bounded grammar restores/transfers items in order. Smeargle Recycle, Snorlax Belly Drum, and Rotom Switcheroo test teams are constructed native compatibility witnesses, not generated routes. Existing generated Belly Drum roots include Azumarill/Eiscue/Cetitan; generated Switcheroo roots include Persian/Seviper; Trick includes Rotom/Zoroark. No generated Recycle route is claimed. |
| Passive provenance and activation | Sitrus healing follows consumption and does not reacquire; Custap/Leppa `[consumed]` activation never asserts held presence. Other source item provenance remains raw-only where existing extractor fields have no writer. Power Herb, White Herb and Booster Energy use-item roots are accounted for; no generic item-tag-implies-held inference. |
| `handlePseudoWeather`/switch/request suppression | Existing suppression is public Magic Room only. Both validators derive it from prefix field-start/end, not the candidate field map. Magic Room has no operative generated selector root; no Klutz/effectiveness inference is introduced. |
| Cleanup/faint/restoration | Faint does not invent item removal. Valid source consume→switch→re-entry retains attributable known history; coherent omissions and phantom last-item/disposition claims reject. Earlier unrevealed carriers stay raw-only/unknown when current evidence cannot attribute them; exact addressed possession is preserved. |
| Requestless terminal | Validated predecessor owned items plus exact suffix writers remain authoritative. The private context retains a cloned eligible roster for historical uncertainty classification, not a mutable alias or serialized public field. |

The mirrored historical witness consumes Sitrus under Zoroark's unrevealed Disguise, departs, re-enters, and either remains unrevealed or is hit by priority Quick Attack before terminal Dark Pulse. The later reveal cannot assign the old consumption to the real bench Disguise. Current bench Sitrus remains exact; unsupported historical fields remain null/unknown. Native/fromJSON and after-terminal private restoration are checked. The publicly retained end-item record is never deleted.

#### Terminal identity and restoration authority

Current addressed request binding first requires a legitimate alias: a different active public appearance needs the real owner's current Illusion ability and exactly one legitimate owned teammate with that appearance. A non-Illusion owner or foreign nickname cannot authorize the alias, even after canonical rehashing. Terminal context requires validated predecessor semantics, exact origin/predecessor boundaries, side/perspective, prefix extension, stable ordered slot/ident/name/base-species roster, and action/transition/snapshot joins. Mutable species is excluded from stable identity because source form/Transform changes are legitimate.

An incoming unrevealed terminal switch uses the canonical submitted switch validated against the predecessor's addressed request slot. Ordinary/full/compact publication validates these action joins before semantic authority, then completes all remaining actor/belief checks atomically. A bare envelope has no action and rejects that incoming alias. Visible normal terminal switches need a revealed identity or explicit nonempty base/current non-Illusion abilities for every addressed owner. Drag never borrows switch authority. Failed candidate contexts are discarded in `finally`; standalone JSON roundtrips cannot acquire authority from a prior failed transaction. Opposing views retain public identity only.

Native private restoration uses request-only `terminal-request-history/v1` unchanged, and separate v2 only when submitted switch provenance is present. V2 binds canonical action, force flag and exact owner-channel submission cursor to pinned source terminal `side.active[0]`, stable fullname and base species, including a fainted entry-hazard incoming owner. Regular choice cursor follows the last turn; forced replacement cursor is Battle.go's exact blank/timestamp frame before its sole switch (pinned `battle.ts:2881–2882`). Cursor ±1/out-of-range, wrong slot/force kind/version or missing provenance reject before environment replacement. Metadata never becomes public envelope authority and no terminal future request is fabricated.

Pinned `battle.ts:1382,1481` waiting requests include `side.getRequestData()`. Operative wait retains the full addressed owned roster; fully rehashed empty-side/false-item waiting boundaries cannot erase previously established authority. Waiting sides receive no synthetic actor row.

#### Execution corrections and current evidence

The obsolete pre-correction matrix was interrupted and is unusable final evidence; resulting KeyboardInterrupt/status-null diagnostics are cancellation, not semantic rejection. The first optimized frozen matrix ran 168.900s with 46/48 passing. Its two execution failures were a 30s timed-out missing-predecessor subprocess and raw native twin timestamps crossing a wallclock second. The fixture now uses the existing production snapshot fingerprint, whose only normalization is the pinned source timestamp. No production validator changed for those failures.

The exact two affected cases then passed 2/2 in 3.879s. Actual separate-process CLI reproduction of the saved missing-predecessor full result and compact sweep returned exit 2 with zero stdout in 0.063s/0.052s and the intended origin-coverage/predecessor error, with the same 30s bound. Test-only startup batching separately JSON-parses each candidate, verifies canonical joins and calls fresh CLI `main()` with isolated captured streams; every invalid case still asserts 2/empty. Actual separate-process controls remain in the suites.

Independent parent reproduction against the final production hashes passed the original mirrored Sitrus forgeries and six original Wish health/status/faint forgeries: canonical identities pass, TypeScript rejects semantically without mutation, and Python exits 2 with empty stdout. Four Sitrus/Wish positive controls remain accepted/immutable with Python exit 0. The 16 source/test hashes were checked before/after; detailed reproduction is `/tmp/c22-c23-parent-final-probes.json`. Final whole-suite results and hashes follow below once the sequential checks finish.


### Resumed production/test freeze before performance correction

The following raw hashes bind the final sequential validation baseline. The
parent's freeze includes the last test-only near-turn-1000 payload diagnostics;
no production change was made for transient subprocess timeouts. The exact
near-turn-1000 terminal-switch case passed 1/1 in 28.210s; its six action-bound
valid full-publication cases, each with a 5,528-line prefix, completed in roughly
1.1–1.3s per Python subprocess. Build passed in 1.650s. The final whole matrix
and affected suites run sequentially under the parent; results follow below.

The most recent independent original-probe reproduction passed in 0.966s:
eight canonically valid Sitrus/Wish negative candidates rejected semantically
without TypeScript mutation and with actual Python CLI exit 2/empty stdout;
four positives remained accepted/immutable with exit 0. This confirms the
unchanged production hashes, rather than substituting for the final matrix.

| File | Raw SHA-256 |
| --- | --- |
| `sim-core/scripts/check-simulator-coverage.cjs` | `a1930249ec887f975ce45c1285f8c29cc78eb92f05fdfa169d42f06cceb1e351` |
| `sim-core/src/belief_state.ts` | `908fae0fabdb49c5d8a1ba40e3471abbc3b4b7aa8cacd1ea0cdaecd373f90d2c` |
| `sim-core/src/env_manager.ts` | `1a2e4b6593077b0065edcdad07c7ebe95413a3ef6791caac4e75df72650e7247` |
| `sim-core/src/observable_state.ts` | `74c3b658809c6a7a6266a328beebc16395c1ea478d4061db0ec5474b38d4e327` |
| `sim-core/src/pipeline_episode_evidence.ts` | `1f1de5c349c970d2d12a70873342a353f69dde83f427aa8fac67e11264ab52f1` |
| `sim-core/src/pipeline_integration.ts` | `e75e3a0ee38ff399fc3ffb8ea363b7dbe8cb6dee97e5a9f9858f41d7a0b310f3` |
| `sim-core/src/public_health.ts` | `1f122f8a4393331dc7563422fa9ad8cb5bf585540dd2daa3e463dfe02c2814d1` |
| `sim-core/src/public_item.ts` | `1e6380a9471d6c90295c556007182c06f5502c5ec8fba96fb55f9793b94084ca` |
| `sim-core/src/state_extractor.ts` | `3d8138e1b7e942ffb73fed76505edabe4f4c8acf12d056ba95738f5ddb410019` |
| `sim-core/src/typed_state_lifecycle.ts` | `a133a8c23d94993aab0ad3a6e8f4b921aaa65f76cf0eb8aa08ff392eea75f083` |
| `sim-core/tests/item_identity.test.ts` | `aece0f44a948aaf336737f558d1472c683b2f240bd84a5f4f30c213c450ae8c0` |
| `sim-core/tests/observable_state.test.ts` | `9e609b38df6be3697288ea3e5aa8c007a7f9b28e738280ce8c58ba9beb0bbc6f` |
| `sim-core/tests/pipeline_episode.test.ts` | `f8dd3cfb41852916690de1596ece3d61d1060ee3098a882385f8cdaf39fdefa1` |
| `sim-core/tests/pipeline_integration.test.ts` | `e830ef61aa2c31f95ee6d43a3acd1e60bd9d03c688ccb8c046020a3c4723abde` |
| `sim-core/tests/public_consequence_test_helpers.ts` | `8bd8c77bcecfa8cb05d5696ef9e86c924ce9bc1216ed27c22c936757c53e789b` |
| `sim-core/tests/public_consequences.test.ts` | `48250e82424214a81a4005525453cdd528de6d056322dbe1b4ce49bab173f0ae` |
| `trainer/src/neural/pipeline_record.py` | `5b4c729eefbb2c291abbc09c9dfa2edf10abf5947295430543eb4f2114d589d5` |
| `trainer/src/neural/public_health.py` | `023f6002bc1dd1a82c65f6091eed071ae1d36729a3255f6d0f74b2a98c3373fb` |
| `trainer/src/neural/public_item.py` | `af30a29267597032652df139329fda08db19a31a8076bc06c5ccb26d0ddb2a59` |
| `trainer/src/neural/typed_state.py` | `6a2c5b42ff8730c3586d0c6441b917d2e524622365ce234056cb6d4b13a22a97` |
| `trainer/tests/test_pipeline_record.py` | `fe7e1fc4134680bba283e803cadb17ecbe1ba32e9d1de599e2cc8d8bb9e91f19` |
| `trainer/tests/test_public_consequences.py` | `4d81b25e742b26df200a733bb0a0fb8b5ba479adc3483cc10200397122dbcdcb` |

| `sim-core/tests/protocol_contract_validation.test.ts` | `7ada0d5096ae07287895a9a37d56275a61c867cb188d9819a53e78749356932c` |
| `sim-core/package.json` | `1a81e29560c44c3997437e4f2cf22e2312e71e32448f600394dd5c0d1413f3f4` |

### Item/identity matrix result before performance correction

Fresh final-current-hash validation passed **48/48** in **142.137s**
(Node test duration 142,090.625ms), with zero failures, cancellations, skipped
cases or subprocess timeouts. The command was
`node --test --test-isolation=none --test-reporter=spec sim-core/dist/tests/item_identity.test.js`
under the accepted macOS profile, with `.venv-simulator/bin/python` and
`PYTHONPATH=trainer/src`. This supersedes the prior 46/48 and 47/48 execution
runs; neither timed-out run is passing final evidence.

| Matrix component | Cases / candidates | Coverage |
| --- | ---: | --- |
| Ordered-evidence and representation unit cases | 15 tests | Named presence/absence/unknown, replacement order, eligible owner facts, phantom/partial/false containers and historical compatibility. |
| Mirrored native compatibility/source profiles | 33 tests | Consume, restore/Recycle, Trick/Switcheroo, revealed/unrevealed Illusion, known bench disguise, known consumed bench, restored/resumed predecessor chains, consume→switch→re-entry, historical unknown carriers, forced entry-hazard terminal, waiting authority, incoming unrevealed canonical switch and source turn-1000 normal terminal switch. |
| Ordinary rehashed negatives | 2,644 | Both perspectives, input/successor, every applicable v1/v2 representation; fully joined identities, TypeScript candidate/prior-commit immutability and fresh Python exit 2/empty stdout. |
| Full-result rehashed negatives | 246 | Origin/predecessor/roster/action/transition/prefix authority and retained item facts; full result rejection before output. |
| Evidence-envelope rehashed negatives | 246 | Complete/resumed chain, exact origin/predecessor boundaries, missing/foreign/reordered/mismatched authority and bare-envelope insufficiency. |
| Compact bulk rehashed negatives | 246 | Same boundary authority, canonical actor/action/belief joins and atomic empty output for any invalid candidate. |

Constructed native teams are labeled compatibility/mechanics witnesses, not
generated roots. No accepted selector root or raw grammar exclusion is expanded.
Positive native/restored controls accompany every source profile, including
after-terminal private restoration and revealed/unrevealed continuations.
Failed full/envelope candidates cannot leave private authority usable by a later
standalone observation. Public observation identity algorithms and v1/v2 schema
versions remain unchanged; private restoration v2 is explicitly separate.

#### Remaining scope and acceptance limits

The two independent-review defects at lines 3050/3088 have bounded implementation
repairs and complete local item/identity matrices. This does not resolve C22's
generic callback/copy/global-composition proof, unsupported indirect stage or
side-condition callback routes, or all ability/item combinations. Neutralizing
Gas's generated no-route disposition remains separately reviewable. C23 retains
source-route evidence for the bounded slot consequences, but aggregate sufficiency
and independent acceptance of this candidate remain outstanding. Bare terminal
observations cannot establish an unrevealed owned alias; bare envelopes cannot
establish an incoming unrevealed switch without the canonical action. Earlier
unattributable item carriers remain raw-only/unknown rather than guessed.

C22/C23 stay OPEN. C17/C20 acceptance, prior attestations, CE-08A/CE-08B and
PIPELINE-002 gates are unchanged; `faithful_complete_episode:false` is required.
The normal coverage checker must retain its separate semantic-review gate.


### Existing-fixture adjudication during focused validation

The first focused TS run exposed two pre-existing synthetic protocol matrix
assumptions: raw grammar examples added hypothetical own targets and were
incorrectly expected to publish against an unrelated addressed roster. The
production roster/alias guards remain unchanged. The test-local matrix now
retains raw grammar positives independently; only semantically compatible
rehashed controls publish, while foreign hypothetical owned targets and
contradictory public facts are explicit semantic negatives with TS immutability
and Python exit 2/empty stdout. Both original source bundles remain positive.
The four accepted CE-02D raw warning controls (both perspectives × input and
successor) must publish and cannot be classified as semantic negatives. Counts
are printed per schema; the focused rerun result is recorded below.

The direct Python Illusion health fixture likewise omitted the active owner's
Illusion ability. Its fixture now supplies that legitimate authority and adds
missing/non-Illusion authority negatives with immutability. The three focused
Python files passed **58/58 in 8.82s** after this test-only correction. No
production validator was weakened or changed for either fixture correction.


### Reproducing the final candidate coverage digest

`local_coverage_sources.files` is the exact input list, resolved from `sim-core`.
Sort the listed relative names; hash each UTF-8 name, a NUL byte, the strict
UTF-8 file content with CRLF converted to LF (lone CR unchanged), and another
NUL byte. The SHA-256 is stored only in the manifest's local `sha256`; inserting
it into a hashed audit document would create a self-reference. Raw file hashes
above do not normalize content. After final documentation is saved, the parent
independently reproduces the digest and verifies the final hash rows.

Run `node sim-core/scripts/check-simulator-coverage.cjs --reachability-self-test`
for the drift/adversarial checker self-tests, and
`node sim-core/scripts/check-simulator-coverage.cjs` for the normal gate. The
normal command must still reject the unchanged separate semantic-review digest;
a local candidate digest does not add an attestation. `git diff --check` supplies
the whitespace check. These commands are recorded for reproducibility; their
final results are recorded separately below.


### Affected-suite evidence before performance correction

The parent ran all phases sequentially, with no overlapping heavy tests, using
Node v24.21.0/npm 11.19.0 and `.venv-simulator` Python 3.9.6/pytest 8.4.2.
Fresh `pip check` returned exit 0 (`No broken requirements found`; only the
nonfatal cache-permission warning). No dependency or lockfile update was needed.

| Phase | Command scope | Result |
| --- | --- | --- |
| Build | `npm run build --prefix sim-core` | Exit 0, 1.650s before the final matrix. |
| Final bounded item/identity matrix | `sim-core/dist/tests/item_identity.test.js` | 48/48, 142.137s; exact counters above. |
| Additional TS source/record suite | `item`, `illusion`, `wish`, `healing_wish`, `future_sight`, `record_identity`, `transition` test files | 91/91, 61.951s. |
| Focused Python | `trainer/tests/test_public_consequences.py`, `test_pipeline_record.py`, `test_typed_state.py` | 58/58, 8.82s after direct Illusion fixture authority correction. |

All TS commands use `node --test --test-isolation=none --test-reporter=spec`,
with explicit compiled test filenames and `PYTHON` pointing to the accepted
venv. Python uses `PYTHONPATH=trainer/src .venv-simulator/bin/python -m pytest`
with the three named paths. The first focused TS fixture failure is preserved
as adjudication above; its corrected rerun and full episode suite, including the single optimized
1000-chain fixture, are recorded below on completion.


The corrected focused TS suite passed **149/149 in 46.509s** (46,450.069ms
Node duration), after a fresh build passed in **4.591s**. Its eleven files are
`public_consequences`, `typed_state_lifecycle`, `observable_state`,
`observable_state_fixture`, `pipeline_integration`, `state_extractor`,
`env_manager`, `belief_state`, `protocol_contract_validation`, `forced_switch`
and `revival`, each under `sim-core/dist/tests/*.test.js`. This includes the
accepted queued terminal action and actor-only one-sided terminal witnesses.

For each observable schema, the corrected protocol matrix printed **206 semantic
positives, 104 explicit synthetic semantic negatives and 1,172 grammar
negatives**. All raw grammar positive records remain accepted independently in
both runtimes; two native source bundles and four CE-02D warning publications
are mandatory positives. Synthetic contradictions now reject at semantic
evidence guards, with full canonical joins, immutable candidates and fresh
Python exit 2/empty stdout. These are fixture corrections, not new source
routes or weakened validator assertions.


#### Episode selection correction

The attempted negative name filter selected the optimized turn-limit fixture
instead of excluding it. The parent retained that already-progressing process
as the **full episode suite**, with one 1000-chain execution and all its other
selected episode cases; the subsequent duplicate long phase is skipped. This
run is not described as nonlong or as a separately isolated single-test run.
Live source commit and Python phase diagnostics remain visible, and no second
heavy process overlaps it. Use the verified Node skip flag for future focused
nonlong selection rather than relying on a negative name filter.


#### Long-run cost and focused command

Read-only profiling found repeated historical-prefix validation at
`belief_state.ts:938–956`: every new boundary slices and hashes every prior
prefix. Node remained active around 100% CPU with approximately 355 MiB RSS;
native progress reached 900 commits in 318.394s. No risky production caching
change or restart was made during the run. The parent added only
`sim-core/package.json`'s `test:episode:focused` script using the locally verified
Node skip flag and live reporter. It is now one of the coverage digest inputs
(115 files). Dependencies and the lockfile are unchanged. The convenient
command is `PYTHON="$PWD/.venv-simulator/bin/python" npm run test:episode:focused --prefix sim-core`.
It builds and excludes the long fixture; the ordinary full test command retains
the fixture. Verification of this focused command follows below.


### Outer-budget cancellation and scoped performance correction

The retained full episode job completed its 1,000 native commits in 444.096s,
but its wrapper still had the attempted nonlong phase's **600-second outer
budget**. That budget expired during Python bulk publication. The phase is
**cancelled/unusable as passing evidence**, with no remaining Python child.
Neither the full episode suite nor the 1000-chain regression has a passing
result from that run. The later duplicate was not run.

The parent is correcting only the repeated historical prefix-hash loop in
`belief_state.ts`, with a focused `belief_state.test.ts` regression. A fresh
per-validation incremental SHA-256 stream will preserve the existing canonical
array bytes and use `Hash.copy()` at ordered prefix cursors. Every historical
identity, cursor, order and hash check remains; no state is cached across
candidates. This scoped algorithm change revokes the previous production
freeze: prior matrix and suite results above remain evidence for their listed
hashes, and are not claimed current for the new source hash. Fresh affected
validation and final raw hashes follow after the correction. The full episode
wrapper's corrected outer budget is 3,000s; individual bulk subprocesses retain
360s bounds and successful publication's 300s assertion.

C22/C23 remain OPEN, the coverage digest remains a pending local candidate, and
reviewed/prior attestations and `faithful_complete_episode:false` are unchanged.


### Fresh incremental-history correction and final revalidation freeze

The parent completed the surgical history-hash correction: a fresh
`Hash('[')` per parent-belief validation, monotonically appended existing
canonical record text with commas, then `Hash.copy().update(']')` at each
validated cursor. All prior malformed-reference, schema, identity, cursor,
order, duplicate and wrong-hash guards remain. There is no cross-call or
cross-candidate cache and no canonical identity/schema change.

Preflight `belief_state` plus `record_identity` tests passed **15/15 in
19.910s**, including stored historical identity fixtures and Python parity at
every historical position. The new regression covers Unicode, quotes,
backslashes, cursor zero, and a fully rehashed false historical digest with
candidate immutability. Build passed. All affected matrices and source suites
are freshly rerun against this new freeze; the earlier 48-case pass is not
substituted for current-source validation.

| Performance correction file | Raw SHA-256 |
| --- | --- |
| `sim-core/src/belief_state.ts` | `cae5498643de4264bbe209dfc54dacbe6f6b88a1f8ee8a2ac5edc7aee8f8cb1f` |
| `sim-core/tests/belief_state.test.ts` | `770a0eefe11c287752e156ba3f8e9b571d0833f5a64c442a32049e565dda5aed` |


### Final revalidation hash baseline after performance correction

The parent froze 20 production/test/script files in
`/tmp/c22-c23-parent-final-code-freeze.json`; their raw hashes below were
independently checked against saved file bytes. Additional existing checker,
canonical/grammar contract sources and repaired tests are included so the
identity algorithms and protocol contract can be reproduced. The three
behavior contracts have raw hashes too; this audit's own hash is intentionally
excluded from its contents. A fresh build passed in **1.516s**. Final current
validation results follow; no pre-performance result is substituted.

| File | Final raw SHA-256 |
| --- | --- |
| `docs/contracts/PIPELINE_EPISODE.md` | `b2f409fe76b1b6cd9256fdea5963cd24b5a04e8f7884f5f3dbb01c028eb9b7f2` |
| `docs/contracts/SEEDED_TRANSITION.md` | `86ecfa17f059de5289ccf67a89ca7a7880ada16adec5fba3a14bf8731c31d67a` |
| `docs/contracts/SIMULATOR_COVERAGE.md` | `e4fb66d712367df0423dce2cd2a6393884e101b6f489a6c6f1ec455bb36f47eb` |
| `sim-core/package.json` | `1a81e29560c44c3997437e4f2cf22e2312e71e32448f600394dd5c0d1413f3f4` |
| `sim-core/scripts/check-simulator-coverage.cjs` | `a1930249ec887f975ce45c1285f8c29cc78eb92f05fdfa169d42f06cceb1e351` |
| `sim-core/src/belief_state.ts` | `cae5498643de4264bbe209dfc54dacbe6f6b88a1f8ee8a2ac5edc7aee8f8cb1f` |
| `sim-core/src/canonical_action.ts` | `bb18e6eecdcb4276242d9d6767c4533141e0ebab499afe6ed7669b2d620552ee` |
| `sim-core/src/env_manager.ts` | `1a2e4b6593077b0065edcdad07c7ebe95413a3ef6791caac4e75df72650e7247` |
| `sim-core/src/observable_state.ts` | `74c3b658809c6a7a6266a328beebc16395c1ea478d4061db0ec5474b38d4e327` |
| `sim-core/src/pipeline_episode_evidence.ts` | `1f1de5c349c970d2d12a70873342a353f69dde83f427aa8fac67e11264ab52f1` |
| `sim-core/src/pipeline_integration.ts` | `e75e3a0ee38ff399fc3ffb8ea363b7dbe8cb6dee97e5a9f9858f41d7a0b310f3` |
| `sim-core/src/protocol_contract.ts` | `7764deef6838ed6512863239d2a1be3120c2107f8eb8694780e119d2a20dba41` |
| `sim-core/src/public_health.ts` | `1f122f8a4393331dc7563422fa9ad8cb5bf585540dd2daa3e463dfe02c2814d1` |
| `sim-core/src/public_item.ts` | `1e6380a9471d6c90295c556007182c06f5502c5ec8fba96fb55f9793b94084ca` |
| `sim-core/src/state_extractor.ts` | `3d8138e1b7e942ffb73fed76505edabe4f4c8acf12d056ba95738f5ddb410019` |
| `sim-core/src/typed_state_lifecycle.ts` | `a133a8c23d94993aab0ad3a6e8f4b921aaa65f76cf0eb8aa08ff392eea75f083` |
| `sim-core/tests/belief_state.test.ts` | `770a0eefe11c287752e156ba3f8e9b571d0833f5a64c442a32049e565dda5aed` |
| `sim-core/tests/item_identity.test.ts` | `aece0f44a948aaf336737f558d1472c683b2f240bd84a5f4f30c213c450ae8c0` |
| `sim-core/tests/observable_state.test.ts` | `9e609b38df6be3697288ea3e5aa8c007a7f9b28e738280ce8c58ba9beb0bbc6f` |
| `sim-core/tests/pipeline_episode.test.ts` | `37247bdb14c1f16b65622fb82a5091160a0cd6fb8607c2c35e4cd43bce249113` |
| `sim-core/tests/pipeline_integration.test.ts` | `e830ef61aa2c31f95ee6d43a3acd1e60bd9d03c688ccb8c046020a3c4723abde` |
| `sim-core/tests/protocol_contract_validation.test.ts` | `7ada0d5096ae07287895a9a37d56275a61c867cb188d9819a53e78749356932c` |
| `sim-core/tests/public_consequence_test_helpers.ts` | `8bd8c77bcecfa8cb05d5696ef9e86c924ce9bc1216ed27c22c936757c53e789b` |
| `sim-core/tests/public_consequences.test.ts` | `48250e82424214a81a4005525453cdd528de6d056322dbe1b4ce49bab173f0ae` |
| `trainer/src/neural/pipeline_record.py` | `5b4c729eefbb2c291abbc09c9dfa2edf10abf5947295430543eb4f2114d589d5` |
| `trainer/src/neural/protocol_contract.json` | `f14cb6809d56a1709276c8af8b27fdff4895677bdf2fcd5c3dd9cd7a1a0ae0d7` |
| `trainer/src/neural/protocol_contract.py` | `3340e6a6cb71c084eab846c1622e531cfad09d9575daf42be90b90a74c0f779d` |
| `trainer/src/neural/public_health.py` | `023f6002bc1dd1a82c65f6091eed071ae1d36729a3255f6d0f74b2a98c3373fb` |
| `trainer/src/neural/public_item.py` | `af30a29267597032652df139329fda08db19a31a8076bc06c5ccb26d0ddb2a59` |
| `trainer/src/neural/ts_identity.py` | `d9086a839312293258fa7a011b4965811253a9f85f66c4998219368c6cf84651` |
| `trainer/src/neural/typed_state.py` | `6a2c5b42ff8730c3586d0c6441b917d2e524622365ce234056cb6d4b13a22a97` |
| `trainer/tests/test_pipeline_record.py` | `fe7e1fc4134680bba283e803cadb17ecbe1ba32e9d1de599e2cc8d8bb9e91f19` |
| `trainer/tests/test_public_consequences.py` | `4d81b25e742b26df200a733bb0a0fb8b5ba479adc3483cc10200397122dbcdcb` |


### Current-source final matrix after performance correction

The fresh final 20-file freeze passed **48/48 in 140.487s**
(Node duration **140,421.885ms**) with zero failures, cancellations, skipped
cases or timeouts. Build passed in **1.516s**. This is the current-source
matrix result and supersedes the earlier pre-performance evidence for the
final candidate. All 33 native/source profiles and 15 ordered-evidence and
representation unit cases passed. Final canonical adversarial counts are
unchanged: **2,644 ordinary**, **246 full result**, **246 envelope**, and
**246 compact bulk**. Both perspectives, input/successor, applicable v1/v2,
restored/resumed/terminal paths and all retained item field representations
remain covered. TypeScript rejected candidates and prior commits stay immutable;
Python rejects every invalid candidate with exit 2 and empty stdout.

Command: `node --test --test-isolation=none --test-reporter=spec sim-core/dist/tests/item_identity.test.js`
using the accepted `.venv-simulator` Python and `PYTHONPATH=trainer/src`.
Raw source/test hashes are in the final revalidation table above. Broader
C22 composition, aggregate C23 sufficiency, independent semantic acceptance
and complete-episode gates remain open.

### Fast-stop validation checkpoint (2026-10-08)

The current-source focused TypeScript source/contract suite passed **241/241**
in 111.799s; the focused Python lifecycle, public-consequence and publication
suite passed **58/58** in 8.974s. The focused episode command initially passed
33/34: a historical envelope tamper assertion expected a later diagnostic,
while the strengthened validator rejected earlier at terminal transition or
actor-action continuity. The test now asserts the actual semantic rejection
without relaxing either validator; the exact affected case passed **1/1** in
18.689s after the correction. The other 33 cases have not been rerun against
the final test-only hash. The 1,000-turn source witness completed native
progress in the earlier canceled run but its Python bulk phase did not finish;
it is **not passing current-source evidence**. The user requested no further
long tests, so this run remains for a separate validation session.

The final test change is confined to `pipeline_episode.test.ts` at the raw hash
above. Its prefix candidate still reaches the intended TypeScript prefix rule;
Python rejects earlier at the actor/transition join with exit 2 and empty
stdout. Existing C22/C23 item and owner-identity adversarial matrices retain
their separate fully rehashed publication assertions. C22/C23 remain open
pending independent review; FCE-01 aggregate, CE-08A/08B and PIPELINE-002
remain open. Prior scoped attestations, `reviewed_sha256`, and
`faithful_complete_episode:false` remain unchanged.

### C22/C23 short-checkpoint continuation (2026-10-08; author evidence only)

All 33 hashes in the final revalidation table matched before this continuation.
The only test edit adds candidate immutability assertions to the existing
episode tamper helper, which is called by one episode test. The updated test
passed **1/1 in 18.422s**; TypeScript still rejects each candidate for the
documented semantic rule, Python exits 2 with empty stdout, and candidate and
committed evidence remain unchanged. The package defines
`test:episode:focused`, not `test:episode`; its exact skip selector was checked
against the turn-limit test name and selected zero tests.

The requested combined short run used `test:episode:focused` with the accepted
macOS Python path, visible reporter, and a real 180s process-group deadline.
It timed out at **182.032s** before Node emitted a test result; the owned
process group was terminated. This is an unresolved combined-run validation
limit. The corrected case then passed under an exact positive selector, so no
C22/C23 production defect was demonstrated. The prior 48/48 item/identity,
241/241 focused TypeScript, and 58/58 Python results remain reusable for their
unchanged source/test inputs. The source-derived 1,000-turn Python bulk witness
remains unverified. C22/C23 independent review, FCE-01, CE-08A/08B,
PIPELINE-002, and `faithful_complete_episode:false` retain their prior gates.
The synthetic coverage self-tests passed; the ordinary checker and self-test
wrapper exit 1 only at the unchanged separate semantic-review digest gate.
`git diff --check` passed. The reproducible candidate digest is recorded in
the manifest and pipeline progress note, outside this digest-covered audit.

The saved 180s timeout log contains the npm and TypeScript build headers but
no Node case output. It cannot establish whether Node was executing a case
or waiting on one of its Python subprocesses. The exact skip selector was
verified to select zero tests when paired with the turn-limit name, so the
1,000-turn witness was excluded. The earlier short run supplies 33 passing
cases; their relevant source and test bodies are unchanged. The sole changed
helper is invoked only by the case rerun below. Thus all 34 individual short
cases have applicable passing evidence, while the combined invocation remains
unverified. No individual production failure or individual timeout was found.

| Short episode case | Evidence | Elapsed |
| --- | --- | ---: |
| v2 episode origin boundary requires exactly one visible Substitute roster row | Reused pass (unchanged relevant inputs) | 1.612s |
| C23 fully rehashed Wish episode health matrix rejects atomically in both runtimes | Reused pass (unchanged relevant inputs) | 3.517s |
| C23 Healing Wish p1 full-result health rejection covers acting and waiting perspectives | Reused pass (unchanged relevant inputs) | 0.926s |
| C23 Healing Wish p2 full-result health rejection covers acting and waiting perspectives | Reused pass (unchanged relevant inputs) | 0.921s |
| C23 Future Sight p1 full-result health rejection covers acting and waiting perspectives | Reused pass (unchanged relevant inputs) | 1.439s |
| C23 Future Sight p2 full-result health rejection covers acting and waiting perspectives | Reused pass (unchanged relevant inputs) | 1.418s |
| C23 Revival Blessing p1 full-result health rejection covers acting and waiting perspectives | Reused pass (unchanged relevant inputs) | 0.600s |
| C23 Revival Blessing p2 full-result health rejection covers acting and waiting perspectives | Reused pass (unchanged relevant inputs) | 0.599s |
| C23 original-to-terminal publication sweep rejects rehashed origin health omissions | Reused pass (unchanged relevant inputs) | 9.461s |
| real episode completes repeatably through joint and both one-sided actor paths, with valid partial lineage | Reused pass (unchanged relevant inputs) | 2.493s |
| v2 evidence retains both owners at every commit and rejects rehashed chain tampering in TypeScript and Python | Current pass (exact selector) | 18.422s |
| continuation v2 evidence binds its segment origin to both current owned observations | Reused pass (unchanged relevant inputs) | 0.173s |
| source Destiny Bond simultaneous terminal p1 closes from original requests and publishes both actors | Reused pass (unchanged relevant inputs) | 0.207s |
| source Destiny Bond simultaneous terminal p2 closes from original requests and publishes both actors | Reused pass (unchanged relevant inputs) | 0.195s |
| resumed terminal closure needs a validated predecessor chain to claim original initial coverage | Reused pass (unchanged relevant inputs) | 6.505s |
| max_transitions stops after one committed transition without duplicate records | Reused pass (unchanged relevant inputs) | 0.014s |
| max_attempts stops after one committed transition without duplicate records | Reused pass (unchanged relevant inputs) | 0.012s |
| natural Arena Trap rejection retries a different current-request tuple and preserves control identity | Reused pass (unchanged relevant inputs) | 0.045s |
| controlled rejections stop at default three per boundary | Reused pass (unchanged relevant inputs) | 0.005s |
| controlled rejections stop at episode attempt cap | Reused pass (unchanged relevant inputs) | 0.006s |
| episode attempt budget counts rejections and successes without resetting after commit | Reused pass (unchanged relevant inputs) | 0.023s |
| cancellation is observed at committed boundaries including after an in-flight commit | Reused pass (unchanged relevant inputs) | 0.019s |
| controlled requestless boundary explicitly truncates without submitting or fabricating an action | Reused pass (unchanged relevant inputs) | 0.005s |
| source-shaped Revival Blessing flag at a real force/wait boundary truncates before any attempt | Reused pass (unchanged relevant inputs) | 0.039s |
| controlled \|nothing\| candidate output stops with no uncommitted records | Reused pass (unchanged relevant inputs) | 0.010s |
| controlled \|-singlemove\|p1a: Pikachu\|Glaive Rush candidate output stops with no uncommitted records | Reused pass (unchanged relevant inputs) | 0.012s |
| controlled \|futuremechanic\|opaque candidate output stops with no uncommitted records | Reused pass (unchanged relevant inputs) | 0.010s |
| controlled \|turn\|broken candidate output stops with no uncommitted records | Reused pass (unchanged relevant inputs) | 0.010s |
| controlled \|-boost\|bad ident\|atk\|1 candidate output stops with no uncommitted records | Reused pass (unchanged relevant inputs) | 0.011s |
| simulator failure after a valid commit retains only committed records and final lineage | Reused pass (unchanged relevant inputs) | 0.018s |
| initialization failure returns a versioned failed outcome with no committed boundary | Reused pass (unchanged relevant inputs) | 0.001s |
| invalid budgets/policy fail explicitly; cleanup failure retains committed records | Reused pass (unchanged relevant inputs) | 0.018s |
| invalid continuation options retain the existing committed origin and close its session | Reused pass (unchanged relevant inputs) | 0.013s |
| rejection cap resets only on commit, while total rejection and attempt counts accumulate | Reused pass (unchanged relevant inputs) | 0.021s |
| Combined `test:episode:focused` invocation | Unresolved timeout; no case result emitted | 182.032s |
| Source turn-limit 1,000-turn witness | Pending separate validation | — |

### Independent C22/C23 item/terminal-identity review (2026-10-09; attestation withheld)

Reviewed entry candidate `29b17a3cdfb762f8912c850640bec6d30842503fb92e0df11a18f4d8b86c9fea`. All 33 checkpoint file hashes matched, and the 115-input local coverage digest reproduced before this documentation update. Production and test files were not changed during review. The following sibling findings prevent scoped C22/C23 closure and digest attestation:

| Finding | Boundary and evidence | Required follow-up |
| --- | --- | --- |
| High — attributable consumed-item history can be omitted when an owned Illusion ability disables the global history guard | `sim-core/src/public_item.ts:74–80` and `trainer/src/neural/public_item.py:97–103` enforce history omission only when every owner has known non-Illusion current/base abilities. A native source control publicly reveals Eater with `replace`, consumes its Sitrus Berry, switches out, and re-enters. The valid successor retains `last_item:sitrusberry,item_state:consumed`. After canonical rehashing, replacing these with `last_item:null,item_state:unknown` passes TypeScript ordinary linked-record validation and Python identity verification, then publishes with exit 0 and 1,327 stdout bytes. The candidate remains unchanged. | Enforce each attributable history entry after carrier ambiguity filtering; an Illusion roster member must not globally authorize omission of already attributable public history. Extend both-perspective/input/successor/ordinary/full-envelope publication controls. |
| High — valid departed unrevealed Frisk item evidence is misbound to the real disguise roster row | `public_item.ts:44–49,81–100` and `public_item.py:54–60,104–130` treat departed `-enditem` carriers as ambiguous but retain departed `-item` facts. Pinned `data/abilities.ts:1486–1491` emits Frisk's target item reveal without an Illusion identity reveal. A native source control starts Zoroark/Leftovers disguised as Snorlax/Sitrus Berry, then switches to Eevee. Initialization passes; the first canonical joint transition fails with `pipeline/v1/observable-projection-failed: Public item evidence mismatch: p1: Disguise request/public item disagree`, with zero commits. | Include public reveal/restoration writers in departed-carrier attribution review. Preserve raw reveal evidence and current owned-request authority without assigning the disguised carrier's item to the real bench Pokémon. Add mirrored switch/restoration controls. |
| Medium — corrected Python prefix diagnostic proves an earlier join rejection, not the intended prefix semantic rule | `sim-core/tests/pipeline_episode.test.ts:1024–1030` changes both retained boundary observations and their observation IDs but leaves actor-bundle observation joins unchanged. Its expected Python diagnostic is `episode actor action does not join the retained transition boundaries`. The helper at lines 552–570 correctly checks candidate/committed immutability, exit 2, and empty stdout; these remain useful evidence. They do not establish Python rejection of an internally joined prefix mutation. | Propagate dependent actor-record/observation/belief/envelope joins before asserting Python's intended prefix rule. Keep the existing immutability and empty-output checks; do not widen the diagnostic. |

Fresh review probes used the existing canonical rehash helper and accepted macOS Python profile; no broad suite, combined episode command, long witness, benchmark, or production repair was run. The consumed-history invalid ordinary bundle is saved at `/tmp/c22-review-unrelated-illusion-history.json`, SHA-256 `149838d570ffd1ca30acacccef23f50b98807c36985be2426e71019e956629e3`. Despite that temporary filename, the confirmed witness is the publicly revealed Illusion consumer described above. The departed-Frisk pipeline result is saved at `/tmp/c22-review-departed-frisk-result.json`, SHA-256 `a3a5e4bbb25a5dc434206d4f1ed4547128ba167b7a8e9dea9fe001f96b77dcfc`. These are constructed pinned-engine mechanic controls, not proof of random-team generator legality; they demonstrate the present observation/publication and attribution defects without promoting format reachability. The history probe's control publishes successfully; the forged bundle passes identity verification before publication.

The inspected C23 authority path binds terminal owner identity to validated input/action/transition evidence, origin/predecessor continuity, perspective and roster joins; the private authority is scoped and not serialized into the opposing observation. No additional defect was found in that inspected authority/restoration boundary. The historical-prefix optimization creates a fresh incremental canonical hash stream per validation, checks every ordered historical reference, and adds no cross-candidate trust. This supports those narrow obligations only; it does not close the incomplete item/identity matrix or attest C23 as a whole.

Reused hash-matching author evidence: item/identity 48/48, focused TypeScript 241/241, focused Python 58/58, and the 34 individual short-case table above (33 applicable reused passes and one current pass). Passing selected controls do not negate the newly reproduced sibling defects. The combined invocation remains an unresolved 182.032s timeout, and the 1,000-turn publication witness remains pending. Neither was investigated or rerun here. The audit's earlier claim that every corrected Python tamper reaches its documented semantic rule is narrowed by the prefix finding above.

Verdict: **C22/C23 scoped acceptance and candidate digest attestation withheld**. C22 remains blocked by the two item findings; the fixture evidence gap needs a narrow correction. FCE-01 reconciliation still has unresolved C22/C23 rows and receives no aggregate promotion. CE-08A/08B, PIPELINE-002, training/live readiness, and complete-episode acceptance are outside this review. Prior attestations and `reviewed_sha256` remain unchanged; `faithful_complete_episode:false` is preserved. The manifest's local digest is refreshed only for this review record; its value is recorded in the progress note to avoid a digest self-reference.

### Three-finding carrier/prefix repair checkpoint (2026-10-09; author evidence only)

Entry candidate was `e74ef3a3fd8195bffaa3230c15ec29e82ce16c66cfb172c05514b1999bda206f`. This batch repairs only the latest two item findings and the joined-prefix fixture finding. No terminal authority, schema, identity algorithm, hashing optimization, or broader closure changed.

The pre-edit carrier-attribution decisions used for this repair are:

| Carrier boundary | Retained evidence and attribution |
| --- | --- |
| Established carrier | A public replacement attributes its writers; attributable consumption history is required. |
| Unrevealed current carrier | Only the addressed active owner binds the current appearance; do not assign its item to the disguise teammate. |
| Departed unrevealed carrier | Reveal/restoration/end-item writers remain raw and cannot establish the departed real carrier by nickname. |
| Re-entry | Possession starts unknown until eligible evidence; previously attributable consumed history remains required. |
| Public reveal | Replacement moves the current appearance's history and restores displaced teammate history. A later replacement does not resolve an earlier departed carrier. |
| Independent teammate history | Another possible Illusion carrier never authorizes omission. An ambiguous later nickname collision restores the established prior history on departure. |

TypeScript and Python now enforce every retained attributable history entry without a global all-roster non-Illusion exemption. Their ordered replay distinguishes a revealed carrier from an unresolved appearance: when an unresolved consumption departs, it restores that nickname's prior established history instead of deleting all history for the name. Departed-carrier ambiguity now includes `-item`/`item` reveal and restoration writers, so Frisk evidence is not assigned to the real bench disguise. Current owned possession remains authoritative to its addressed request; opposing views keep only public presence, never the private named item.

The prefix fixture propagates the changed successor prefix through both players' records, current/historical observation references, belief sources/parents, initial/final summaries, origin and envelope identities using existing canonical helpers. Every actor input/output joins its retained boundaries, and every historical reference joins an actual retained observation. Python independently verifies canonical observation/belief digests for both actor records at the changed edge. The full `verify_bundle_identities` helper also enforces prefix semantics, so it cannot pass a deliberately contradictory origin-to-successor prefix; it is not claimed as passing evidence for this candidate. Other fixture callers retain strict construction-time belief validation. The corrected candidate specifically rejects at TypeScript `evidence-commit-0-p1-prefix-lineage` and Python `episode commit 0 p1 public prefix was mutated`, with exit 2, empty stdout, candidate immutability, and unchanged original committed result.

| Exact targeted case | Result | Process elapsed |
| --- | --- | ---: |
| `carrier-specific p1 revealed consumption history rejects omission after re-entry` | Pass; v1/v2 ordinary input/successor, both-perspective valid controls, joined v2 full result/envelope, identity verification before omitted-history rejection | 1.522s |
| `carrier-specific p2 revealed consumption history rejects omission after re-entry` | Pass; mirrored same obligations | 1.466s |
| `carrier-specific p1 departed unrevealed Frisk stays raw and owned possession stays authoritative` | Pass; both views, ordinary/full result/envelope, privacy and deterministic restored replay | 0.617s |
| `carrier-specific p2 departed unrevealed Frisk stays raw and owned possession stays authoritative` | Pass; mirrored same obligations | 0.560s |
| `carrier-specific history preserves established teammate evidence across an ambiguous nickname collision` | Pass; TypeScript/Python parity, established and genuinely ambiguous controls | 0.208s |
| `v2 evidence retains both owners at every commit and rejects rehashed chain tampering in TypeScript and Python` | Pass; corrected prefix semantic control plus existing valid controls and tampering checks | 17.902s |

Each test used `node --test --test-isolation=none --test-reporter=spec --test-name-pattern='^<exact case>$' <compiled file>` under the accepted `.venv-simulator` Python / `PYTHONPATH=trainer/src` profile, sequentially with a real 180s process-group deadline. Build passed (final 1.608s). Initial new-test typing and action-order permutation issues were corrected before the passing cases. Prefix construction first exposed the deliberate prefix contradiction in the strict belief serializer and then in identity verification; the fixture now distinguishes canonical identities from the semantic rule being tested. An expanded per-record Python canonical-probe attempt timed out at 180.149s and its owned process group terminated. The final version avoids repeating probes for all 55 commits and passed at its changed edge while retaining assertions for every join. No broad matrix, combined invocation, 1,000-turn witness, full suite, or benchmark was run.

The new native fixtures are constructed pinned `pokemon-showdown@0.11.10` / `gen9randombattle` mechanic controls, not generator-legality proof. The prior 48/48, 241/241 and 58/58 evidence remains historical evidence for unchanged inputs; it is not promoted to a new whole-suite pass after shared validator changes. Unchanged terminal authority/restoration and history-hashing paths reuse their existing scoped evidence. Only the selected changed item and prefix boundaries have fresh evidence here. The combined 182.032s timeout and 1,000-turn publication witness remain pending.

Affected raw file hashes:

| File | SHA-256 |
| --- | --- |
| `sim-core/src/public_item.ts` | `98502db79fb5b92db057e140478106b273ade9134f8a5fab8a3368721dfd4a74` |
| `trainer/src/neural/public_item.py` | `85b7f8069e1169ee6eea27f30418781720aa81964237cb9a5aac6e1f9d0f39c1` |
| `sim-core/tests/item_identity.test.ts` | `9e5667a03a2470ad4447b131347ea5b467fbf140c9ede5564c39f59cceed536b` |
| `sim-core/tests/pipeline_episode.test.ts` | `dd5f0e7b5f37c902eca242644e423bd955935142d9a9edef521cbaface6d8e33` |
| `docs/contracts/PIPELINE_EPISODE.md` | `5fc2062f70864bcca9bd20ddb7b595f9c9d4715c389a23973fd3112d61cc2e74` |
| `docs/architecture.md` | `935fda41ef76ed20b0f66a1096e51811a360e6c1591cc385109a8123577580c0` |
| `docs/workflows.md` | `011f7d3d97f3d2705c23212400a888dd842da6f31c3eb1dbe855ce1e5bdded65` |

All affected source/test files were already in the coverage list; its 115 inputs are unchanged. The reproducible candidate digest is recorded in the manifest and progress note outside this digest-covered checkpoint. `reviewed_sha256`, all prior attestations, and `faithful_complete_episode:false` remain unchanged. These are author repairs, not independent acceptance: C22/C23, FCE-01, CE-08A/08B and PIPELINE-002 retain separate review/validation gates. No additional production blocker was exposed by the selected checks.

### Scoped independent review of the three-finding repair (2026-10-09)

**Verdict: all three latest findings are resolved within their repair scope; no material blocker remains in this batch.** Reviewed entry digest `7970750f40adf90c24a2ed5639fe31f5cbec505e762aac0d2048cfccaf023682` reproduced. All 35 combined dependency-baseline/repair hash entries match, including canonical helpers, extractor, protocol contracts and publication validators. The six targeted passing controls above are reused; no tests, broad matrix, combined invocation or long witness were run during this review.

The complete carrier table agrees with both runtimes: attributable history is required independently of other Illusion roster members; an unresolved departed appearance restores prior established nickname history instead of assigning its own writer to the real teammate. Frisk and restoration writers participate in departed ambiguity. The lifetime ambiguity set does not exempt retained attributable history, which is checked separately. Current owned possession still requires the exact addressed-request row. The repair neither synthesizes a roster member nor transfers owned identity/item fields into the opposing view; public item names may remain in their already-public raw evidence. Constructed pinned-engine controls establish mechanic/validator behavior only, with no generated-team reachability promotion.

The prefix candidate uses the existing canonical serializers/digests and propagates actor observations, current/historical references, belief parents, summaries and envelope identities. All actor input/output and historical-reference joins are asserted; Python independently checks canonical digests at the changed edge. Preserving the actual origin reference intentionally leaves the immutable-prefix contradiction, so full belief-prefix semantic validation is not claimed to pass. Matching evidence proves the precise TypeScript `evidence-commit-0-p1-prefix-lineage` and Python `episode commit 0 p1 public prefix was mutated` rejections, candidate/committed-state immutability, and Python exit 2 with empty stdout. This replaces the earlier stale-actor-join proof without widening diagnostics.

This verdict accepts only the three repairs, not C22/C23 as a whole or aggregate FCE-01. The 115-input digest includes changes beyond this review boundary; `reviewed_sha256` and every prior attestation remain unchanged. The combined 182.032s invocation timeout and 1,000-turn publication witness remain pending. CE-08A/08B, PIPELINE-002 and complete-episode acceptance receive no promotion; `faithful_complete_episode:false` is preserved. Only review documentation and the local digest are refreshed, with the resulting candidate recorded outside this covered audit to avoid self-reference.

### C22/C23 acceptance reconciliation (2026-10-09; no execution)

Entry digest `6c30c8134b8fdb86fe4fac11e56f6b3a98b45f6dcca96a3f03fd872d9e36f915` reproduced. All 35 dependency/repair hashes and all eight pinned callback/slot route-file hashes match. Reuse is scoped to matching dependencies and unchanged behavior: the latest six carrier/prefix passes cover changed item branches; the 34 individual episode cases and current 241/58 source/contract evidence cover their applicable unchanged paths. Earlier whole-suite passes are not relabeled as fresh runs. No tests, checker execution, combined command, long witness or benchmark were run.

| Obligation | Source / implementation | Valid and adversarial evidence | Reconciled verdict |
| --- | --- | --- | --- |
| C22 generated roots and exclusions | B17/B18; pinned sets/teams, ability/item callbacks and selector closure; eight bound route files | CE-03 source closure; generated Trace/Air Lock/Intimidate controls in `ability_callback.test.ts`; finite callback matrix | Roots bounded; does not prove all composed typed results. |
| C22 Gas, exemptions and name/effectiveness consumers | `Pokemon.ignoringAbility`; Gas callbacks; `public_ability.ts` / `.py`; heuristic neutral constructor/clone | `public_consequences.test.ts` constructed start/departure/faint/multiple-source/exemption/restoration controls and unsupported-publication negatives; 2026-10-08 independent review | Bounded source/no-route and consumer evidence reusable. No generated Gas publication requirement or hidden-effect inference. |
| C22 public item writers and carrier attribution | `public_item.ts` / `.py`; `state_extractor.selfFromRequest`; source `eatItem/useItem/takeItem/setItem`, Frisk and accepted transfer/restoration grammar | Original mirrored Sitrus probes; item/identity source profiles; six latest targeted passes and 2026-10-09 scoped carrier/prefix review | Reported item defects resolved. Current owner possession exact; old unresolved carriers raw/unknown; independent history required. |
| C22 callback health/status/stage/field consequences | Shared public-health and accepted stage/lifecycle replay; B17/B18 and the 17-row consequence atlas | Reviewed public-health matrix; accepted CE-04C/C17/C20 controls; finite callback valid controls | Retained bounded projections supported; no blanket callback composition acceptance. |
| C22 copied/replaced/restored ability truth | `assertPublicAbilityMatchesEvidence` and Python counterpart currently check owned current authority; source Trace copies an existing eligible ability | Existing Gardevoir/Trace to Static source control proves extraction; helper negatives are conditional on live owner ability | **Missing aggregate semantic evidence:** opponent/requestless copied-ability identity/state omission, false-value and wrong-side assertions lack an exhaustive joined rejection crosswalk. No new defect was executed or demonstrated here. |
| C23 writer order, precision and representation | B22; `Pokemon.getHealth`; `projectPublicHealth` / Python replay; condition/status/cure/faint grammar | Original six Wish probes independently verified/rejected in the 2026-10-08 review; `public_consequences.test.ts` writer/partial/rounding matrix and matching adapter/publication evidence | **Accepted scoped:** public facts and exact current owned request authority; requestless own exact HP proves only consistency with the public rounding bucket. |
| C23 Wish | `Moves.wish` slot/result callbacks; public `-heal` and raw wisher provenance | `wish.test.ts` both-perspective switch/drag/faint/terminal/restore controls; six original negatives; `C23 fully rehashed Wish episode health matrix` | **Accepted scoped:** result truth and raw slot sufficiency; no timer/amount forecast or hidden slot assertion. |
| C23 Healing Wish, Future Sight and Revival Blessing | B22; healing replacement, imperative `futuremove`, revival request/result; ordinary public-health writers | `healing_wish.test.ts`, `future_sight.test.ts`, `revival.test.ts`; six mirrored full-result sibling cases plus original-to-terminal health-omission sweep | **Accepted scoped:** public outcomes, missing/false representations, privacy/restoration and actor-only publication. Waiting evidence creates no row. |
| C23 unrooted siblings | B22/M closure: Lunar Dance/Doom Desire absent from generated/call-copy roots; Z-only `runZPower` healreplacement has no action/item route | Source exclusions and matrix/checker drift controls; no unsupported sibling positive witness is required | **Accepted source disposition:** retain fail-closed exclusions; not a sampled reachability claim. |
| C23 terminal owner identity and restoration | `public_health` validated predecessor/action authority; pipeline linked-record/envelope joins; private restoration v1/v2 provenance | Matching item/identity mirrored revealed/unrevealed/forced/incoming terminal profiles and origin/foreign/roster/order/action/provenance negatives; 2026-10-09 independent authority inspection and current code reconciliation | **Accepted scoped:** sufficiently bound ordinary/full-envelope paths. Bare terminal observation or incoming-alias envelope without action authority rejects intentionally. No private opponent identity or future request is created. |
| Historical-prefix optimization | `belief_state.ts` ordered per-validation SHA-256 stream, canonical record bytes, copied closing bracket at each cursor | `ordered history hashing preserves canonical Unicode identities and rejects rehashed prefix lies`; Python Unicode identity tests; matching current source/contract and full-result evidence; independent 2026-10-09 source inspection | Sufficient scoped canonical/parity evidence; no cross-candidate trust or omitted historical reference. Long-chain execution remains separately unverified. |

**Separate verdicts:** C22 remains OPEN for the copied/requestless ability and broader callback-composition evidence gap. C23's enumerated B22 public slot-result sufficiency and terminal identity obligations receive scoped semantic acceptance here. This does not claim all callback truth, all complete episodes, or a zero-unresolved FCE-01 matrix. The C23 FCE-01 registration is still conservatively OPEN because `check-simulator-coverage.cjs:26,270-274,710-713` hardcodes both blockers and requires false aggregate `source_backed` values. No guard is weakened in this read-only task. Manifest prose is corrected to reflect accepted bounded semantics rather than the obsolete unsupported-terminal finding; changing dispositions/checker/self-test registration is a small separate bookkeeping follow-up, not a remaining demonstrated C23 behavior defect.

**Validation ownership:** `spec.md` FCE-02/FCE-06/FCE-07 and `PIPELINE_EPISODE.md`'s publication-sweep contract require original-to-terminal lineage, every actor row and matching turn-limit outcomes for later episode acceptance. The pending 1,000-turn bulk witness is required for those complete-chain claims, not for the bounded C22/C23 writer/slot contract in `spec.md:216-232`. The combined short invocation remains an execution/reporter limitation: individual applicable passes establish their checks, not a combined-command pass. Neither pending command supplies C22's missing source/semantic crosswalk. Neither is made a prerequisite for the scoped C23 semantic verdict; both stay pending and no whole-episode acceptance is inferred.

**Digest verdict:** do not attest the 115-input candidate or change `reviewed_sha256`. In particular, `public_ability.ts` / `.py`, ability extraction in `state_extractor.ts`, and the callback atlas still lack C22-wide copied/opponent/requestless semantic acceptance. Historical hash parity is reviewed and is not itself the uncovered boundary. Source/config identities, prior attestations and `faithful_complete_episode:false` are preserved.

**Smallest substantive next task:** a bounded generated Trace copied-ability truth review using the existing Gardevoir-to-Static witness. Map eligible public ability name/state assertions to source and exact validators; add/execute only coherent ordinary/full-envelope omission/false/wrong-side controls if that review identifies a gap. Permitted future workload: exact positive selectors for the affected Trace cases and corresponding Python publication checks, sequentially with 180s process deadlines; no 48-case matrix, combined invocation or long witness. C23 registration bookkeeping can separately run only its coverage self-test/checker after explicit authorization; no episode execution is necessary. This reconciliation itself authorizes no test execution or production repair.


### Bounded generated Trace copied-ability repair (2026-10-09; author evidence)

Entry candidate was `ac8e5dfb61b8eebe5f21db7213d41fd976dec040c5539db25170b3aa0b3e9bb0`. This task repaired three demonstrated Trace defects: requestless owned copied names/states were trusted from the candidate; terminal owned extraction retained stale `static` after native faint restored `trace`; ordinary Python v1 accepted injected opponent Trace ability fields. The first two exact controls failed before their repairs in 0.510s and 0.310s. The opponent-field defect returned Python exit 0 for a coherently rehashed v1 candidate. No ability model, public schema, identity algorithm, unrelated callback or C23 registration was redesigned.

| Obligation | Source / current representation | Focused proof and limit |
| --- | --- | --- |
| Generated copy identity / source role | Pinned `sets.json:1966–1972` selects Gardevoir/Trace; seed `[2,2,3,4]`, slot 2. `Abilities.trace.onUpdate`, `abilities.ts:5058–5066`, filters `notrace`/`noability`, calls `setAbility`, emits copied value followed by literal Trace source and opposing active `[of]`. | Existing exact grammar role/domain controls reused. Witness is a generated carrier with a **constructed Static Pikachu partner**, not a wholly generated matchup. `[of]` is a public opposing source identity; it does not supply hidden membership or private snapshots. |
| Owned live request and public-only/cached requestless | `Pokemon.getSwitchRequestData`, `pokemon.ts:1122–1126`, exposes owner base/current ability. Extractor public copy is `static/changed`; addressed or remembered owner evidence may represent it as `static/known`. Both runtime guards now replay established Trace recipient identity/current value. | Valid generated copied observations publish. Requestless false/null/missing ability, unknown/none/missing state, and false/missing suppression reject. Without current addressed authority, `known` and `changed` are compatible established-name representations; their private provenance distinction is not independently proved by a bare requestless view. Live addressed ability contradictory to the public current copy rejects in the guard; no additional generic callback authority is claimed. |
| Opponent visibility and representability | Public v1/v2 projection omits opponent ability/base/state/suppression. Raw Trace stays retained. Trace-scoped Python v1 exclusion now agrees with TS/v2. | Injected opponent copied name/state rejects. Omitting those typed fields is correct. Missing owned recipient row/team or wrong-side placement rejects at public-health/owned-roster or the Trace representability gate; direct partial/view-less Trace controls cannot conceal established owned copy facts. |
| Cleanup and restoration | `switchIn` (`battle-actions.ts:118`) and faint cleanup (`battle.ts:2468`) call `clearVolatile`; `pokemon.ts:1460` restores base. Replay clears outgoing/incoming on switch/drag and faint; only independently public base restores without owner authority. Later ability records replace the current writer. Transform/form changes invalidate copy authority; replacement does not graft it onto another identity. | Source/extractor switch/drag/faint controls reject stale copied facts and preserve unknown public bases. Mirrored native/fromJSON terminal-faint controls prove owned `trace/known` restoration, valid ordinary/full/envelope publication, and canonically joined stale-`static` rejection. Existing validated terminal predecessor requests supply private base authority; a candidate cannot bootstrap that authority from its own base field. |
| Broader composed source-carrier truth | This guard binds the recipient copy and source role, not every source carrier's ability at every historical cursor. Current addressed owner consistency remains checked; raw source identity stays public and opponent typed ability stays omitted. | Independent temporal `[of]` source-ability consistency after later writers, other v1 opponent ability routes, copied/replaced/suppressed ability combinations and generic callback composition remain named C22 work. This is not full Trace-class independent semantic acceptance. |

**Exact execution:** all commands used `/tmp/run-trace-check.py`, which launches a new process group and enforces a real 180s deadline with child termination. Workloads ran sequentially with visible spec/pytest output; selectors were exact anchored positive names, not broad test files. Final build passed in 1.644s. No task-owned processes or pending launched checks remain.

| Command after `python3 /tmp/run-trace-check.py` | Result |
| --- | --- |
| `node --test --test-isolation=none --test-reporter=spec --test-name-pattern='^(Trace requestless copied truth rejects false name and state without mutation\|generated Trace faint restores owned base instead of cached copied request ability\|generated Trace emits exact public copy evidence for both actors)$' sim-core/dist/tests/ability_callback.test.js` | 3/3, 0.316s. Reused for unchanged source/cleanup paths after the subsequent opponent-only guard addition. |
| `node --test --test-isolation=none --test-reporter=spec --test-name-pattern='^C22 generated Trace p[12] observable-battle-state/v[12]: joined requestless copy controls$' sim-core/dist/tests/pipeline_episode.test.js` | 4/4, 6.371s. Thirteen canonical candidates per mirrored actor/version: 52 ordinary negatives, plus 26 full-result and 26 envelope negatives for v2. V1 intentionally has no full envelope. |
| `node --test --test-isolation=none --test-reporter=spec --test-name-pattern='^C22 generated Trace terminal faint cleanup publishes restored owner base and rejects stale copied name$' sim-core/dist/tests/pipeline_episode.test.js` | 1/1, 0.993s; both actors, one stale-copy candidate each in ordinary/full/envelope paths. |
| `.venv-simulator/bin/python -m pytest -vv trainer/tests/test_public_consequences.py::PublicConsequenceTests::test_trace_requestless_copy_requires_public_name_and_representable_state` | 1/1; pytest 0.20s, wrapper 3.228s. |

Node publication checks set `PYTHON=.venv-simulator/bin/python`; Python unit sets `PYTHONPATH=trainer/src`. Canonical helpers are unchanged: ordinary candidates use existing `rehash`; full candidates use `withRehashedEpisodeObservations` to update actor observations/current and historical references, belief parents, summaries, origin and envelope identities. Python independently verifies both actor records' canonical observation/belief/record joins before semantic rejection. Tests assert TypeScript candidate/original immutability and Python exit 2 with empty stdout; valid controls remain publishable. Two short joined fixture failures (4.449s/7.367s) exposed the v1 envelope assumption, exact schema diagnostic mismatch and then the genuine v1 exclusion defect; only the changed hypothesis/repair was rerun. No broad matrix, combined episode invocation, turn-1,000 chain, benchmark or coverage checker/self-test ran.

Final raw hashes for this bounded change:

| File | SHA-256 |
| --- | --- |
| `sim-core/src/public_ability.ts` | `232f41feee5a8b0c912c1defe73f743992c44d85ed6630fb263e48aca3c3abe0` |
| `sim-core/src/observable_state.ts` | `988a704abdd21dd24b4dfb5db8dedd16d4ce5308697ba7bfae453675709ae297` |
| `sim-core/src/belief_state.ts` | `3b7bbed39e078271de70ed10333bf3321177393d23d3880dbca477b20508eef5` |
| `sim-core/src/state_extractor.ts` | `2feaeaecf7bc48c3c205fde2fd07ed36bb76564d8de090a2eef5892fd9797626` |
| `trainer/src/neural/public_ability.py` | `32f3b126c7d4c784b241bc01cbbff32cd28ecefd97adaf394ddcac1a97676a77` |
| `trainer/src/neural/typed_state.py` | `997e5cbfd37dcf4adb6c332492f47a42556bca747913a889a913f5e2b79ca951` |
| `sim-core/tests/ability_callback.test.ts` | `439886f60ca77d4e74a5a027f81e21d6de3eb6020fd0dfee3e70e389e6afd943` |
| `sim-core/tests/pipeline_episode.test.ts` | `d8bc75b3af5c590cdbe04d2cf39e19b065fd2e8e21b56df59225819d95c3fd0f` |
| `trainer/tests/test_public_consequences.py` | `ba88cc7afa37b8d078712e2f6a1a2829451e193a06da5d217b33c0bfa86fec6a` |

All affected files were already among the 115 local coverage inputs. The manifest corrects Trace public source-role prose and retains all aggregate blockers. The local candidate digest is refreshed once and recorded outside this covered audit. C22 remains OPEN for the named broader classes and independent review; C23's accepted bounded semantics and pending formal registration are preserved. `reviewed_sha256`, prior attestations, `faithful_complete_episode:false`, FCE-01, CE-08A/08B, PIPELINE-002 and later readiness gates are unchanged.

### C23 bounded registration follow-up (2026-10-09)

The checker and manifest now register only C23's accepted B22 result-sufficiency, health/status/faint, privacy/restoration, and validated terminal-authority contract. C22 remains unresolved and aggregate FCE-01 stays blocked; no CE-08A, episode, or `faithful_complete_episode` promotion is made. `reviewed_sha256`, prior attestations, and later readiness gates are unchanged. The final exact compiled checker regression passed 1/1 in 1.313s and exercised the synthetic `--reachability-self-test`, including unsupported C23 scope/false closure and independent C22 promotion rejection. The plain checker exited 1 in 0.722s with only the expected `local coverage sources are not bound to a separate semantic-review digest` gate and no registration/drift errors. Checks ran sequentially under enforced 180s process-group timeouts. The final local candidate digest is recorded in the manifest; no episode tests or production validators changed.

### Independent Trace repair review and finite C22 remainder (2026-10-09)

**Findings:** no material finding in the three Trace repairs. **Verdict:** accept only requestless owned copied-name/state representability, terminal faint restoration to validated owner base authority, and ordinary Python v1 opponent Trace-field exclusion. This supersedes the author-only status of that bounded repair, not the C22 aggregate verdict. C23 remains accepted and registered for its enumerated B22 contract; C22 remains unresolved and FCE-01 remains blocked.

Entry local digest was `7772a02ed7c7ed67e062dfbb0add5e99ac01142536de954afc2ef97af8df3ac9`. All nine Trace raw hashes above match. The latest recorded canonical-action, linked-record, envelope, terminal-health TS/Python, Python publication and identity dependency hashes also match (16 source/test matches in total); the ordinary rehash helper additionally matches its last recorded hash. `withRehashedEpisodeObservations` is inside the matching episode test file: `pipeline_episode.test.ts:401-503` updates observations, current/historical references, belief parents, summaries, run/origin identities, terminal closure and envelope seal. The controls independently check both actor record identities before the named semantic rejection, retain valid publication, assert TypeScript immutability, and require Python exit 2/empty stdout. Reuse the recorded source 3/3, mirrored ordinary v1/v2 plus v2 full/envelope 4/4, terminal faint 1/1, Python unit 1/1, build and whitespace evidence. No tests, builds or checker runs were launched by this review.

The authority path is concrete: `public_ability.ts:104-126` uses current addressed ability or, only after cleanup, validated terminal predecessor base. `pipeline_integration.ts:709-730` validates action/transition/observation/belief joins before temporary terminal authority; `public_health.ts:78-164` checks perspective, exact prefix extension, ordered owner roster and transition continuity and removes temporary authority on exit. Python forwards the validated predecessor at `typed_state.py:176-182` and checks it through `public_health.py:71-121`. `state_extractor.ts:370,408,450-455` replaces the cached copied terminal name with the cached addressed base only when ordered Trace cleanup established restoration. The candidate's own base field supplies no authority. Missing recipient row/team/field and wrong-side controls reject; opponent projection remains omitted. Requestless `known`/`changed` compatibility establishes the copied name without proving private provenance.

#### Finite remaining obligation table

Paths below are relative to the pinned `pokemon-showdown@0.11.10` package unless they name project files. B17's 203 authored ability candidates plus six form defaults, closed move graph M and 66-item selector bound constrain every row; membership alone is not a realized callback witness. A later source ability change does not change an earlier recipient copy. No row requires hidden source snapshots, opponent typed abilities, a new schema or testing every candidate value.

| Boundary / generated route | Eligible evidence and exact publication risk | Reusable evidence / remaining proof |
| --- | --- | --- |
| **Trace recipient and temporal `[of]` source** — Gardevoir/Trace `sets.json:1966-1972`; `Abilities.trace.onUpdate`, `abilities.ts:5058-5066`, copies an eligible opposing current ability. Static has authored roots, e.g. Zapdos `sets.json:968-975`. Imposter may supply an already bounded current target ability; `notrace`/`noability` remain guards. | Exact copied value and opposing active source role are public at the copy event. Owner request is current authority; `[of]` stays raw source identity. Later source writers cannot retroactively replace the recipient fact. | **Covered scoped:** three repairs and grammar/source-role controls above. The witness uses generated Gardevoir with constructed Pikachu; it does not prove a wholly generated pairing. A new generated pairing is not needed to validate the already emitted public writer. Independent source ability history is not a typed contract obligation and is removed from the older open-gap wording. |
| **Non-Trace reveal followed by a requestless boundary** — B17/B18 dispatch to literal `-ability` emitters; finite `protocol_contract.json:3695-3965` domains contain 17 plain reveal and 30 `boost` values. Bare `ability` is compatibility only. | A public name remains established until an eligible later change/reset. Existing self `ability`, `ability_state` and suppression must not become false/null/missing; opponents still omit these fields. Live requests settle current owner truth. | Source grammar, Air Lock/Intimidate witnesses and live owner negatives are reusable. **Missing requestless semantic crosswalk:** ordinary helper skips ability mutations without live request authority (`public_consequence_test_helpers.ts:108-110`); Trace is now the closed exception. Smallest proof: one plain and one boost writer, each mirrored, with established-name omission/false-state negatives and last-writer/cleanup disposition; reuse shared domains instead of a 47-value execution sweep. |
| **Imposter / Transform silent current copy and reset** — generated Ditto `sets.json:867-875`; `abilities.ts:2056-2065 → Pokemon.transformInto`, `pokemon.ts:1287-1300`; copied target moves remain within M. | `-transform` proves copying occurred, not the target's hidden ability. Current owner request can establish existing self `ability/base_ability/ability_state`; public-only extraction must invalidate earlier current ability. Switch/drag/faint `clearVolatile` restores the bound base (`pokemon.ts:1460`). Requestless terminal publication must use validated predecessor plus suffix, not trust candidate or stale copied cache. | Accepted Transform type/stage tests, generated Imposter stage witness, and extractor lifecycle control (`ability_callback.test.ts:207-237`) are reusable for their fields. **Missing ability-specific terminal crosswalk**, not a demonstrated defect: mirrored generated Ditto copied-owner terminal faint, native/restored equality, canonical ordinary/v2 full/envelope valid publication and stale-current/missing-field negatives. Prior type/stage acceptance does not prove the ability name/base/state. |
| **Permanent form current/base replacement** — `Pokemon.formeChange`, `pokemon.ts:1374-1433`; generated Terapagos Tera Shift (`sets.json:7723-7739`, `abilities.ts:4875-4890`) and Ogerpon/Terapagos Tera (`battle-actions.ts:1935-1941`) introduce Tera Shell, Teraform Zero and four Embody Aspect defaults. Other reachable Shaymin/Palafin/Crowned/default changes remain in A (B17). | Form/details records invalidate prior current public ability; they do not reveal a hidden default. Addressed request establishes self current/base; a later terminal may have no new request. Exact risk is stale `ability/base_ability/ability_state` retained after a silent replacement, or candidate bootstrap of the replacement. An unsupported ability template retains its stop disposition until separately authorized support. | B17 source induction and extractor form invalidation reuse; health/type/stage consequences reuse their accepted writers. **Missing owned replacement-authority crosswalk:** separate only the actual source branches that change current/base from branches that preserve them. Smallest new regression is mirrored Terapagos plus Ogerpon only where its current/base assertion differs, with a requestless terminal and canonical stale-base/current negatives; no generic opponent-default inference. |
| **Suppression, transfer and unseeded creation** — Gas, Shield, Gastro Acid, Skill Swap, Entrainment, Role Play, Doodle, Simple Beam, Worry Seed; Mummy/Lingering Aroma/Wandering Spirit/Receiver/Power of Alchemy/Commander. | B17 excludes move/ability/default seeds and copy induction cannot bootstrap them; Receiver/Power of Alchemy/Commander additionally need an allied active slot absent in singles. Gas flags exclude copying; Shield is outside I. Mold Breaker/Teravolt/Turboblaze ignore an ability for an attack, not an enduring typed suppression writer. | **Source-excluded or raw/private; no new positive test obligation.** Reuse matching induction, constructed Gas/restoration controls and generated-domain rejection. Constructed suppression/replacement controls prove engine/stop semantics, not generated reachability. Supported Trace `ability_suppressed` false/missing controls are already covered. |
| **Item/status/HP/stage/field callback results, including copied callbacks** — B17/B18 output through existing item, health, stage, field and lifecycle writers; Trace/Imposter retain each copied callback's guards. | Only actual public writers and addressed request facts affect existing fields; private callback parameters, counters, membership and slot state remain raw/private. Provenance alone supplies no item reacquisition, status, HP or stage fact. | **Reuse accepted writer semantics**, original item/carrier repair acceptance, C17/C20 stage/lifecycle and C23 health/slot result acceptance. Do not reopen these because the ability was copied. No further generic composition test or documentation sweep is a closure prerequisite; a concrete differing writer/authority branch would need its own bounded follow-up. |

**Recommended coherent next batch:** review and, only where absent, implement the three missing ability crosswalks above: non-Trace requestless reveal, generated Imposter terminal reset, and permanent form owner current/base replacement. Completion requires a finite source-to-authority table for these exact branches; every asserted self name/base/state either agrees with the current addressed request, eligible public writer, or validated terminal predecessor plus ordered suffix, or remains unknown/unsupported where no authority exists. Use one exact plain-reveal case, one exact boost-reveal case, one mirrored Imposter cleanup case and the differing Terapagos/Ogerpon replacement cases. For each new case require valid native/restored publication, coherent observation/belief/record/envelope joins, false/null/missing relevant fields and recipient row/side rejection, TypeScript immutability and Python exit 2/empty stdout. Reuse unchanged passing inputs; exact positive selectors only, sequential 180s process-group deadlines. This recommendation authorizes no workload here and does not require the old matrix, combined command or 1,000-turn witness. C22 closure remains a separate independent verdict after those proofs; whole-candidate attestation and later episode gates remain separate.

One review-record/manifest digest refresh follows this checkpoint. `reviewed_sha256`, prior attestations, source/config identities, `faithful_complete_episode:false`, CE-08A/08B, PIPELINE-002 and later gates are preserved. No production or test files changed, and no task-owned process or pending launched check remains.


### C22 remaining ability authority crosswalks — 2026-10-09 (author checkpoint)

Entry digest `250d4eb6a45dfdc212a8e36a1ce545cb7724a0cf12bc91e9e652593e1dbb3a69` was reproduced before edits. The accepted Trace hashes above and the unchanged ordinary rehash, Python typed-state and terminal-health dependencies matched. This checkpoint supplies author evidence for the three missing rows in the finite table above; independent C22 acceptance and whole-candidate attestation remain outstanding. C23 stays accepted and registered. `faithful_complete_episode:false`, reviewed/prior attestations, FCE-01, CE-08A/08B and later gates remain unchanged.

**Pre-edit obligation → existing proof / missing control:**

| Obligation | Reused source proof | Demonstrated gap and bounded repair |
| --- | --- | --- |
| Non-Trace plain/boost requestless reveal | Accepted finite grammar; generated Air Lock `[16,2,3,4]` and Intimidate `[2,2,3,4]`; public cleanup source; live addressed owner controls. | The Trace-only replay skipped other supported reveal recipients. Both runtimes now replay eligible plain/boost/bare compatibility writers, retain established names through ordered last writers/reset, require represented owner name/state/suppression and exclude opponent ability fields. No new bare callback provenance is admitted. |
| Imposter/Transform owned current/base reset | Generated Ditto `[9,2,3,4]`, slot 4; `Abilities.imposter → Pokemon.transformInto`, `pokemon.ts:1287-1300`; accepted stage/type/lifecycle semantics; `clearVolatile` restoration at `pokemon.ts:1460`. | Terminal extraction restored copied cached names only for Trace, and terminal current/base had no analogous ability guard. A public `-transform` invalidates current public ability and reveals no hidden target default. Addressed requests establish the private current/base pair; only validated terminal continuity plus its ordered suffix can retain/reset it. Mirrored generated Ditto faint controls restore `imposter/known`, reject stale `static`, false/null/missing base/name/state/suppression and missing/wrong-side representation. |
| Permanent form replacement | B17 authored/default induction; `Pokemon.formeChange`, `pokemon.ts:1374-1433`; current owner request; accepted HP/stage/field writers. | Cached terminal owner names/bases survived a silent replacement. Extraction now invalidates replacing form evidence without inferring defaults; validators replay the already validated predecessor's suffix. The exact generated Ogerpon `Embody Aspect (Teal)\|boost` record failed settling before repair because its literal was absent from the existing boost grammar. Source-backed four Embody Aspect boost names and the conditional Teraform Zero plain name were added to the existing finite TS/Python/shared contract definitions. Bare Teraform Zero follows the existing plain compatibility domain; the Trace-copy domain is unchanged. |

**Finite form source-to-authority classification:**

| Pinned branch and route | Current/base authority disposition |
| --- | --- |
| Nonpermanent `formeChange` (`!isPermanent`), including Zen Mode, Schooling, Shields Down, Gulp Missile and move form changes | Source skips the permanent ability block. Existing addressed current/base survives; public-only form extraction remains conservative. The constructed classifier control is a mechanic/control witness, not a generated reachability claim for every named form. |
| Permanent Disguise/Ice Face exclusions (`source.id` at `pokemon.ts:1420`); generated Mimikyu/Eiscue roots `sets.json:5478,5975` | Source preserves current and base. Reuse an eligible owned `disguise/disguise` or `iceface/iceface` pair for the finite public form, never derive a name from species alone. Pure classifier controls reject a false prior current value. |
| Permanent source replacement selecting the same already established pair: Palafin/Zero to Hero (`abilities.ts:5560-5566`, `sets.json:6840`) | `setAbility` selects the same current/default and assigns base; retain only the previously addressed `zerotohero/zerotohero` pair. This has no materially different asserted name/base branch requiring another episode witness. |
| Permanent source replacement selecting a differing default: initial Terapagos Tera Shift (`abilities.ts:4875-4890`, `sets.json:7723-7739`) and Shaymin freeze (`conditions.ts:93`) | Details/form does not expose the new default. First following request establishes owner authority; when replacement is in a terminal suffix, invalidate old current/base to null/unknown until an eligible public ability writer. Same replacement-authority branch as the silent Stellar regression. |
| Null permanent Tera: Terapagos-Terastal → Stellar (`battle-actions.ts:1939-1941`) | Tera Shell is not `cantsuppress`, so both current/base replace. With no weather/terrain writer, terminal current/base are null/unknown. A constructed Torkoal/Drought partner exercises `Abilities.teraformzero`'s actual weather guard and public `Teraform Zero` writer: current/base then become publicly established `teraformzero/known`. Existing weather/HP semantics are reused. |
| Null permanent Tera: four generated Ogerpon roots (`sets.json:7547-7608`; `battle-actions.ts:1935-1937`) | Each original default is not `cantsuppress`; current/base replace. Four `Embody Aspect` `onStart` callbacks (`abilities.ts:1160-1212`) reach the same `Battle.boost` emitter, differing only in name/stat. One generated Teal representative proves this authority branch; all four exact literals receive grammar controls. Public writer establishes the owner pair; no opponent default is projected. |
| Null permanent + prior `cantsuppress` | Source would preserve current while assigning base. Operative null callers are only Ogerpon and Terapagos-Terastal, whose operative original defaults are not `cantsuppress`. This distinct conditional is source-excluded under those caller constraints; no manufactured positive route. |
| Crowned start rewrite / other defaults | Crowned uses `Battle.start`'s `setSpecies/setAbility/baseAbility` at `battle.ts:2586-2601`, before the first addressed request, not a requestless terminal `formeChange` suffix. Other authored defaults stay in B17's bound. Zygarde/Power Construct has no authored Gen9 random-set root; no new execution/reachability claim. |

**Packaged source limit (corrected by independent review):** both `data/abilities.ts:4857` and operative packaged `dist/data/abilities.js:5047` include Teraform Zero's `notrace:1`; the author's claimed source/runtime discrepancy was a prose error. Runtime Dex plus a generated Azumarill lead/Gardevoir switch into generated Stellar Terapagos confirms no Trace copy for both actors. Thus no Teraform Zero Trace-copy literal was added. Raw hashes: TypeScript abilities `7975eb69496fb38ec8c9f2d7288dedea14e78ec81579f6e2b58ad1c9716d3ce6`; operative JS abilities `433118eb946f9a79c841d5142c01223fcf4d8ddd52c764532589e349269f5474`. Both are already covered by the unchanged simulator source-tree roots (`data`, `dist/data`); source/config identity and installed engine remain unchanged. This is a specific packaged-source discrepancy, not an audit of all source/runtime differences or an inference from registry membership.

**Authority and privacy:** `public_health.ts` now exposes only its already continuity-validated terminal suffix through an internal WeakMap getter. Its predecessor, roster, prefix, action and transition guards and public serialization are unchanged. Python already has the validated predecessor cursor. `ownedAbilityAfterSuffix` retains supplied owned facts, clears current to bound base on outgoing/incoming switch, drag or faint, invalidates hidden Transform current, and separates the finite preserving/replacing form branches. Missing historical owner ability/base fields supply no positive name/base/state authority; requestless public `known`/`changed` compatibility is preserved. Opponent ability/base/state/suppression remains excluded in v1 and v2. Accepted item, health, stage, field and identity source proofs are reused; no generic callback composition model, schema migration, hidden default lookup or performance change was introduced.

**Focused execution and evidence reuse:** every command used `/tmp/run-trace-check.py` (new process group, actual 180s deadline, TERM then KILL of task children on timeout). Positive anchored selectors and explicit pytest node IDs ran sequentially with visible progress. Final build passed in 1.653s. No full suite, old matrix, combined episode command, 1,000-turn witness, benchmark, coverage checker/self-test or engine build ran. No launched process/check remains pending.

- New six scenarios × two actors × ordinary v1/v2: 24/24, 53.884s. Exact selector: `^C22 bounded ability (plain Air Lock|boost Intimidate|Imposter cleanup|Terapagos silent replacement|Terapagos public replacement|Ogerpon public replacement) p[12] observable-battle-state/v[12]: joined requestless authority controls$` in `sim-core/dist/tests/pipeline_episode.test.js`, with `node --test --test-isolation=none --test-reporter=spec` and `PYTHON=.venv-simulator/bin/python`.
- 424 ordinary joined negatives, plus 212 full-result and 212 v2-envelope negatives. Each case has native/fromJSON terminal simulator fingerprint equality and application restoration of `terminal-request-history/v1`, comparing owner current/base/state/suppression/active/fainted with the accepted record. Existing ordinary `rehash` and full `withRehashedEpisodeObservations` join observations, current/historical references, belief parents, records, origin and envelope; Python independently verifies both actor record identities before semantic rejection. TypeScript candidate/committed data remains unchanged; Python rejects with exit 2 and empty stdout. Valid ordinary/full results and envelope validation pass.
- The 24-case run bound ability source hashes `467358f7329310fe08e485f43c0460bd8ea80e514b53546fefbe0033afb151f8` (TS) and `4adec88cd22098b9838589b6123c1dd20b2ec41e98c18eeb39c74ee6fd5f805b` (Python). The only subsequent source change qualifies the fallback state branch by an actually supplied current owner ability instead of owner-row presence. All 24 cases supply current/base and take the unchanged `terminalFact` first branch; their passing evidence is reused explicitly by branch equivalence. The changed partial-owner branch is freshly covered by mirrored direct TS/Python Trace controls. The 24 cases are not described as executed against the final raw source hashes below.
- Final exact TS ability controls: 7/7, 0.300s. Selector is the anchored union of `Trace requestless copied truth rejects false name and state without mutation`, `public ability grammar accepts only generated templates and bare compatibility reveal`, and the five `C22` test names in `ability_callback.test.ts` (plain/boost, hidden Imposter, generated Ogerpon, form classifier, operative Terapagos notrace). Source carrier partners for Air Lock/Intimidate/Imposter and Teal/Terapagos publication are constructed; generated carrier/route proof and constructed mechanic witnesses are kept distinct.
- Affected accepted Trace ordinary/full/envelope and terminal checks: 5/5, 7.549s; exact anchored union `C22 generated Trace p[12] observable-battle-state/v[12]: joined requestless copy controls` and `C22 generated Trace terminal faint cleanup publishes restored owner base and rejects stale copied name`. No other Trace matrix was rerun.
- Final explicit pytest node IDs under `PYTHONPATH=trainer/src`: `trainer/tests/test_public_consequences.py::PublicConsequenceTests::{test_plain_boost_requestless_reveal_requires_name_state_and_cleanup,test_trace_requestless_copy_requires_public_name_and_representable_state,test_gas_sources_and_owned_name_suppression_partial_false_matrix}`: 3/3, wrapper 0.489s. The brace notation here abbreviates three explicit command arguments, not a pytest broad selector.
- Exact shared-contract fixture/loader tests: 2/2, 0.368s; exact existing `terminal request history migrates historical v1 data to a minimal deterministic payload` in `illusion.test.js`: 1/1, 0.209s. The terminal reader/cursor/payload format was not redesigned.

Earlier narrow failures had concrete corrections: Air Lock's generated move 1 was Swords Dance, so the fixture selected attacking move 2; Ogerpon's omitted exact grammar literal reproduced the production stop; Python's mirrored expected contract needed the same literal definitions; and a test tuple needed a TypeScript const assertion. The attempted Teraform Zero Trace source pairing led to the operative `notrace` exclusion above, with two differing source hypotheses rather than unchanged retries. All final checks above pass. Final scoped execution totals about 64s plus earlier bounded implementation/diagnostic checks; repeated unchanged failed runs were not used. Requested implementation and source investigation dominated the work; no long validation or documentation resealing loop occurred.

Final raw hashes (author evidence; unchanged reuse dependencies included):

| File | SHA-256 |
| --- | --- |
| `sim-core/src/public_ability.ts` | `3144a84167159ae652e79f8bf7871d9d432352e7b21ed3ddcb8d44f148d4f4d5` |
| `trainer/src/neural/public_ability.py` | `4042c42c36d096d454f4da63b2c1c1d4712f72e369056677b14089b216ca2f01` |
| `sim-core/src/state_extractor.ts` | `9d5c566ac77da05916e97cb5ae7d497ce36546e0d5cba8f8e86a8ee5e668f62d` |
| `sim-core/src/public_health.ts` | `d268166d2b8f6b69d8f5d0905e93bf42b8d3f918a3a7071d1201f3fdf2bdca6d` |
| `sim-core/src/protocol_contract.ts` | `65fc6f3eb2b91b150fd1b0af096aa6ab685e13fa395d091a762aced803934642` |
| `trainer/src/neural/protocol_contract.py` | `c5c3016514613a5d6fb0c611b9fa7b8256b6dcb26e7ab54cab210496582a6aab` |
| `trainer/src/neural/protocol_contract.json` | `4cbea57639e3a5d11e8387f9f84befcc531a613b13175351630b4377d087c213` |
| `sim-core/tests/ability_callback.test.ts` | `e8e74616e2486be784a63f5922b0c66f8094781ec201e32e7124784e219ef769` |
| `sim-core/tests/pipeline_episode.test.ts` | `b4a239dc7e2bedfff353548e1bd80fc49330b6808f8af88bb13d5566a2d7fc2a` |
| `trainer/tests/test_public_consequences.py` | `37139ee77d0d3d3b6aafe4c6e28dd0a36f7d5152e986ba5230e4249119a71c44` |
| `trainer/src/neural/typed_state.py` | `997e5cbfd37dcf4adb6c332492f47a42556bca747913a889a913f5e2b79ca951` |
| `sim-core/tests/public_consequence_test_helpers.ts` | `8bd8c77bcecfa8cb05d5696ef9e86c924ce9bc1216ed27c22c936757c53e789b` |
| `trainer/src/neural/public_health.py` | `023f6002bc1dd1a82c65f6091eed071ae1d36729a3255f6d0f74b2a98c3373fb` |

**Three dispositions:** non-Trace reveal, Imposter terminal reset and permanent form owner replacement now have bounded implementation/control crosswalks. They remain author candidates pending independent review. C22 stays OPEN/source_backed:false; whole-candidate digest attestation and later complete-episode gates remain separate. The reproducible candidate digest is recorded in the manifest and progress record outside this covered audit.


### Independent C22 ability authority crosswalk review — 2026-10-09 (acceptance withheld)

**Finding — medium, requestless ability invalidation authority:** `public_ability.ts:24-26,182-190` and `public_ability.py:81-82,179-186` remove the recipient fact on public Transform/form invalidation, then use the candidate's supplied current ability for suppression checks when neither a current addressed request nor validated terminal owner supplies authority. The missing fact is not retained as an unknown-current obligation. A false current name and `known` state can therefore survive the supported direct observation entry point. This contradicts REQ-002/006/009 and the finite table's requirement that unsupported owned assertions remain unknown.

One exact source-derived reproduction used generated Ditto/Imposter (`[9,2,3,4]`, slot 4) and a constructed Static Pikachu partner, the pinned spectator channel via `extractChannelMessages(...,[0])`, and `projectPipelineProtocolPrefix`. The engine copied `static`; public-only extraction correctly returned current/base `null/null`, state `unknown`. With request `null`, replacing current with false `levitate` and state with `known` passed both `projectObservableBattleState` and `validateObservableBattleState` for ordinary v1 and v2. The projector constructed canonical observation IDs; TypeScript's complete validator accepted their identities, and Python `_validate_episode_observation` verified the v2 identity and accepted its typed state. Python's episode-boundary entry point correctly rejected v1 because that entry point requires v2. No DATA-001, ordinary linked-record, full-result or envelope publication bypass was demonstrated.

The finite sibling set is one authority/invalidation defect class. Code inspection shows the same fact deletion for `detailschange` and `-formechange`, and no requestless base-name constraint in the fallback owner loop. Thus false base assertions and false state after loss of current authority need explicit dispositions in the narrow repair; only the Imposter false-current/known-state case was executed. Complete observation validators already require ability/base/state/suppression fields and health replay requires the public recipient representation, so this review does not claim that missing fields/rows pass those complete entry points. Retain eligible public known/changed compatibility and the finite preserving/replacing form distinctions rather than rejecting all requestless ability claims.

**Supported sub-boundaries and evidence reuse:** all 13 final source/test/dependency hashes in the author checkpoint match. Pinned TypeScript and operative JS ability hashes also match; both sources contain the `notrace` guard, so the preceding discrepancy sentence is corrected without changing its exclusion. Source reads confirm `formeChange`'s nonpermanent, Disguise/Ice Face preservation, same-default Palafin, differing-default and null-Tera branches; four Embody Aspect callbacks share the `Battle.boost` emitter, while Teraform Zero needs actual weather/terrain. Generated carrier roots are distinct from the constructed partners and form-classifier witnesses.

Reuse the recorded 24 joined cases (53.884s), 424 ordinary plus 212 full-result and 212 envelope negatives, final seven direct TS controls, five Trace controls, three Python controls, two contract controls, legacy-terminal migration, build and whitespace evidence for their stated scopes. The 24-case complete predecessor current/base path is unchanged by the final partial-owner fallback edit; its branch-equivalence reuse is valid and is not described as a run against final raw hashes. Final direct partial-row Trace controls cover that changed compatibility branch. Rehash helpers join observations, historical/current references, belief parents, origin/run/record/envelope identities before the intended diagnostic; matching source controls assert immutable candidates and Python exit 2/empty stdout. Those passing terminal controls establish Imposter reset/restoration and permanent-form terminal current/base authority; they do not establish the direct no-authority invalidation branch found here. Accepted Trace/suppression exclusions, item/status/health/stage/field writer semantics and C23 bounded semantics remain reusable.

**Separate verdicts:** C22 acceptance is withheld solely for the requestless invalidation authority defect above; the earlier three crosswalks' linked terminal and eligible public reveal controls remain supported. All C01–C30 machine rows were read and reconciled: C01–C21 and C23–C30 retain their prior scoped/source-backed dispositions (29 rows); C22 remains the single unresolved/source_backed:false row. FCE-01 stays blocked, consistently with the current checker registration. No C23 or later-gate promotion is made. Whole 115-input digest attestation is withheld: this narrow review covers the 13 current crosswalk/dependency files and named prior evidence, not a new current/prior coverage adjudication of every other included change. The demonstrated C22 defect independently prevents attestation; `reviewed_sha256` and prior attestations remain unchanged.

**Fresh execution and next prerequisite:** one bounded direct reproduction completed in 0.454s under the existing 180s process-group wrapper. Its initial 0.350s attempt correctly rejected private split transport before spectator-channel extraction was corrected; this was a concrete input-routing correction, not an unchanged rerun. Script `/tmp/c22-imposter-direct-review.cjs` and canonical candidates `/tmp/c22-imposter-direct-v1.json` and `/tmp/c22-imposter-direct-v2.json` retain the checkpoint. No test suites, build, checker, combined command or long witness ran. No task-owned process/check remains pending. Next: narrowly retain an invalidated-current obligation and require requestless self current/base/state assertions to have eligible public/current-owner/validated-terminal authority, otherwise unknown or unsupported; cover the named siblings with exact controls while preserving known/changed compatibility. Review that repair before C22 registration or digest attestation. The combined 182.032s timeout and 1,000-turn witness remain pending under their existing episode scopes; CE-08A/08B, PIPELINE-002 and `faithful_complete_episode:false` are unchanged. The resulting local candidate digest is recorded outside this digest-covered audit.


### C22 requestless ability invalidation repair — 2026-10-09 author checkpoint

This repairs only the independent review's requestless Transform/form authority finding above (audit line 3971 at entry). Entry candidate was `335ff00a79450570f64a8d17b1fe31bed04fdbab9b97843d7c29c4e75ec0e7f5`, independently reproduced before edits. The generated Ditto/Imposter public-only case now rejects a coherently identified false `levitate/known` observation in both TypeScript schema versions and Python's v2 episode-observation validator. No DATA-001/full-result/envelope bypass is claimed for that original direct finding.

| Authority case | Current/base/state disposition |
| --- | --- |
| Direct without owner | Transform retains an explicit unknown-current obligation and only an already established public base. Unsupported current/base assertions reject; labels supply no authority. |
| Current owned request | Each actually supplied current/base field independently authorizes its matching value. Missing/empty/partial owner rows cannot erase the invalidation obligation or supply the other field. Established current state/suppression still follows existing guards. |
| Terminal validated predecessor/action | Existing continuity and action guards remain mandatory. Replay now accepts independently supplied current **or** base, including base-only faint restoration; current-only Transform plus public reveal cannot bootstrap base. Complete-pair restoration/preserving semantics remain unchanged. |
| Public reveal after invalidation | Eligible public writers establish current; accepted established-name `known`/`changed` compatibility remains. Transform/Trace copy history cannot infer original base. New base requires the reviewed permanent `detailschange`/writer pair: Terapagos-Stellar/Teraform Zero or the four Ogerpon Tera/Embody Aspect pairs. Generic temporary form plus reveal establishes only current. |
| Silent replacement without new authority | Current/base remain unknown unless supplied by current owner, validated suffix continuity, or a source-preserving form whose matching pair was already established. The existing finite Disguise/Ice Face/Zero to Hero classifier is reused; hidden defaults are not inferred. |

Mirrored `public_ability.ts`/`.py` retain invalidation facts rather than delete them, require matching base and unknown-current suppression, and qualify replacement base writers. The extractor uses the same public replay for base establishment and preserves only eligible established permanent pairs. No ability model, public schema, identity algorithm, dependency, C23 behavior or gate registration changes.

**Frozen focused execution:** every command ran sequentially through `/tmp/c22-invalidation-run.py`, with a real 180s deadline and process-group termination. Final build `npm run build --prefix sim-core` passed (4.337s). No failed check, unchanged diagnostic rerun, or pending task-owned process remains.

- Final TS helper/direct controls: 6/6, 1.367s. Command: `PYTHON="$PWD/.venv-simulator/bin/python" python3 /tmp/c22-invalidation-run.py node --test --test-isolation=none --test-reporter=spec --test-name-pattern='^(C22 direct invalidation requires current and base authority in canonical observations|C22 partial terminal authority replays only independently supplied ability fields|Trace requestless copied truth rejects false name and state without mutation|ability lifecycle clears hidden transform/form truth and restores only public base evidence|C22 plain and boost reveal requestless names survive last writer and cleanup|C22 owned form branch classifier preserves eligible pairs and invalidates replacement defaults)$' sim-core/dist/tests/ability_callback.test.js`. The direct test exercises both actors/v1/v2, with 148 independently identity-verified Python v2 candidates (128 negatives, 20 valid); partial authority helper tests exercise base-only restoration, current-only Transform/reveal and silent replacement. TypeScript and Python candidates remain unchanged. Direct Python validation emits no stdout; it does not publish rows.
- Final Python helpers: 4/4, 2.069s. Command: `PYTHONPATH=trainer/src python3 /tmp/c22-invalidation-run.py .venv-simulator/bin/python -m pytest -v trainer/tests/test_public_consequences.py::PublicConsequenceTests::test_partial_terminal_authority_replays_only_supplied_ability_fields trainer/tests/test_public_consequences.py::PublicConsequenceTests::test_requestless_invalidation_requires_independent_current_and_base_authority trainer/tests/test_public_consequences.py::PublicConsequenceTests::test_trace_requestless_copy_requires_public_name_and_representable_state trainer/tests/test_public_consequences.py::PublicConsequenceTests::test_plain_boost_requestless_reveal_requires_name_state_and_cleanup`. The new unit checks partial owners and all five exact permanent replacement writer pairs.
- Selected joined controls: 4/4, 10.851s. Command uses `PYTHON="$PWD/.venv-simulator/bin/python" python3 /tmp/c22-invalidation-run.py node --test --test-isolation=none --test-reporter=spec --test-name-pattern='^(C22 bounded ability Imposter cleanup p1 observable-battle-state/v1: joined requestless authority controls|C22 bounded ability Imposter cleanup p2 observable-battle-state/v2: joined requestless authority controls|C22 bounded ability Terapagos silent replacement p1 observable-battle-state/v2: joined requestless authority controls|C22 bounded ability Ogerpon public replacement p2 observable-battle-state/v2: joined requestless authority controls)$' sim-core/dist/tests/pipeline_episode.test.js`. They bound intermediate ability hashes `826ae599cd5a6bde70748e8864c095b881dee941581b1a742dabfba3cd2e0790` (TS), `212944a90fd2951510635e7afecf9ac74918b7b6d874cbc979ad490d3d9ba675` (Python). They supply complete predecessor pairs; the subsequent partial-owner qualification takes the same branch for those pairs. Imposter cleanup restores a nonnull supplied base; silent Terapagos has no later writer; neither executes the subsequently qualified missing-base writer branch. Reuse those three controls by this explicit branch equivalence, not as fresh runs against final hashes.
- The affected Ogerpon replacement writer branch was freshly rerun against final source: 1/1, 3.638s, with the same command prefix and exact selector `^C22 bounded ability Ogerpon public replacement p2 observable-battle-state/v2: joined requestless authority controls$`. The selected four cases provide 70 ordinary negatives and 52 each full-result/envelope negatives, preserving canonical identity joins, native/fromJSON and private terminal restoration, valid publication, immutable candidates/committed results and actual Python publication rejection with exit 2/empty stdout.

The eight unchanged dependency/test hashes below match the prior 13-file checkpoint. Reuse its grammar, source-carrier/constructed-partner distinctions, terminal restoration and ordinary/full/envelope identity evidence within their recorded scopes; the prior 24 crosswalks are not rerun or claimed freshly bound to these final hashes. Exact replacement pair semantics are retained and freshly covered above. `git diff --check` passed. No broad matrix/full suite, combined episode workload, 1,000-turn witness, benchmark or coverage checker/self-test ran. Implementation/source investigation dominated; focused validation took under 30s, with no overhead loop.

Final raw hashes:

| File | SHA-256 |
| --- | --- |
| `sim-core/src/public_ability.ts` | `cd02e081265ad427fca3f26c4a6a74497f006b23ea33f86d8dae1929b6478180` |
| `trainer/src/neural/public_ability.py` | `6a3512c50afb706f70c1b17da3adae968960b58b2a4d3a3a8a1534ece751b3d4` |
| `sim-core/src/state_extractor.ts` | `caf69c8f945e7404b2e50487a4d8ca1f9e76d62f6ceb42b3ddcd026c49caf51e` |
| `sim-core/tests/ability_callback.test.ts` | `7606cc59795206c7a7c5f23128248da8a28874db2669f2d092f12ca4d926a4f4` |
| `trainer/tests/test_public_consequences.py` | `8116f34d16f656fb2d09fa11b5e9360c03f968dce74561179772c72d4b9ede70` |
| `sim-core/tests/pipeline_episode.test.ts` | `b4a239dc7e2bedfff353548e1bd80fc49330b6808f8af88bb13d5566a2d7fc2a` |
| `sim-core/src/public_health.ts` | `d268166d2b8f6b69d8f5d0905e93bf42b8d3f918a3a7071d1201f3fdf2bdca6d` |
| `trainer/src/neural/public_health.py` | `023f6002bc1dd1a82c65f6091eed071ae1d36729a3255f6d0f74b2a98c3373fb` |
| `sim-core/tests/public_consequence_test_helpers.ts` | `8bd8c77bcecfa8cb05d5696ef9e86c924ce9bc1216ed27c22c936757c53e789b` |
| `sim-core/src/protocol_contract.ts` | `65fc6f3eb2b91b150fd1b0af096aa6ab685e13fa395d091a762aced803934642` |
| `trainer/src/neural/protocol_contract.py` | `c5c3016514613a5d6fb0c611b9fa7b8256b6dcb26e7ab54cab210496582a6aab` |
| `trainer/src/neural/protocol_contract.json` | `4cbea57639e3a5d11e8387f9f84befcc531a613b13175351630b4377d087c213` |
| `trainer/src/neural/typed_state.py` | `997e5cbfd37dcf4adb6c332492f47a42556bca747913a889a913f5e2b79ca951` |

**Status:** author repair only, pending independent C22 acceptance. `C22 OPEN/source_backed:false`, accepted/registered C23, blocked FCE-01, `reviewed_sha256`, prior attestations, `faithful_complete_episode:false`, combined-timeout/long-witness checkpoints and later gates remain unchanged. Effective model override metadata was unavailable and is not claimed verified. The local candidate digest is recorded outside this covered audit.


### Independent C22 requestless invalidation review — 2026-10-09 (scoped semantic acceptance)

**Findings:** no material finding in this repair or its named Transform/form, false-base and partial-authority siblings. Entry digest `93b0f178484b3a6f9878c5b86ea7df397277de9f8e4c054d57eec8cea461785c` reproduced; all 13 source/test/dependency hashes in the author checkpoint match. **Open questions:** none requiring a user decision. This review changes only verdict/documentation bookkeeping; production, tests, source/config identities and prior attestations are preserved.

| Reviewed authority boundary | Verdict and evidence |
| --- | --- |
| Standalone requestless Transform/form | Retained invalidation facts require unknown current and a separately supported base. Canonical false name/base/state, omitted fields and suppression controls reach the ability rule; provenance labels cannot supply a name. |
| Current request and partial owned fields | Only supplied fields authorize their matching facts; a base-only row cannot establish copied current. Direct current-owner positives and missing/partial-owner negatives are supported. |
| Validated terminal continuity | The existing linked-record path validates observation/belief/action/transition joins before the continuity helper, including perspective, exact prefix extension and roster identity. Authority is internal and temporary. Per-field suffix replay supports base-only restoration and rejects current-only copied-base inference. Partial helper controls prove this replay rule, not standalone full-record validation of their synthetic contexts; joined native/restored controls establish the production path. |
| Public reveal after invalidation | Current may become public while base remains unknown. Known/changed compatibility for established public names is retained. Only the five reviewed permanent replacement form/writer pairs may establish a new base; species alone supplies none. Opponent ability fields stay excluded. |
| Silent replacement and preserving branches | Silent differing-default replacement remains unknown; previously established eligible Disguise/Ice Face/Zero to Hero pairs and complete validated owner continuity remain supported. No target/default/private ability is inferred. |

**Reuse:** the final 6/6 TypeScript and 4/4 Python checks match their hashes. The selected joined ordinary v1/v2 and v2 full-result/envelope checks are reused under the author's explicit branch equivalence, including the final 1/1 Ogerpon writer rerun. The complete-pair Imposter/silent-form paths are unchanged by the partial-owner qualification. Canonical observation identities are independently checked before Python semantic rejection; existing actor-bundle helpers update dependent belief, record and envelope joins. Candidate/committed-evidence immutability and publication exit 2/empty stdout remain supported by those joined checks. Accepted Trace, suppression/no-route exclusions and item/health/status/stage/field writer proofs retain their scopes; constructed controls do not promote generated reachability.

**Fresh exact reproduction:** replayed the two saved original `/tmp/c22-imposter-direct-v1.json` and `-v2.json` candidates through the current TypeScript validator, with Python `verify_observation` confirming both canonical identities. Both TS versions reject for `Public ability evidence mismatch` without mutation; Python's v2 episode-observation check rejects for that same semantic rule with exit 2 and empty stdout. The existing 180s process-group wrapper completed in 0.293s. Python v1 publication was not exercised by this v2-only entry point. This remains a direct-observation proof, not a claim that the original candidate bypassed DATA-001 or full-envelope publication. No suites, build, checker, combined command or long witness ran; no workload remains pending.

**C22 verdict:** accept the bounded generated public-consequence contract supported by the previously reviewed finite crosswalk plus this last invalidation repair: Trace and non-Trace public recipient truth/representation, owned Imposter current/base and cleanup, finite permanent form authority, accepted callback writer semantics and source exclusions. No substantive C22 obligation remains identified within that inventory. This does not authorize generic provenance, hidden state, new ability routes or unreviewed mechanics.

**FCE-01 verdict:** not accepted in this review. All 30 registration rows were inspected individually for pinned scope, witness, TS/Python, privacy/restoration and agreement fields. C01–C21 and C23–C30 retain their 29 accepted source-backed dispositions. C22 now has scoped semantic acceptance, but its machine row still says unresolved/source_backed:false and the checker explicitly requires that state (`fce01RequiredBlockers`, C22 audit marker and aggregate-disposition guard). This is a registration/reconciliation prerequisite, not another demonstrated callback defect or a requirement to rerun episode tests. No zero-unresolved machine inventory or formal aggregate closure is claimed.

**Attestation and next prerequisite:** no digest attested; `reviewed_sha256` and prior attestations are unchanged. The 115-input candidate includes the still-open checker/aggregate registration as well as prior changes outside this narrow review; semantic acceptance of C22 does not automatically attest the whole composite. Smallest next task: register this exact C22 scope in checker/manifest/audit agreement guards, preserve unsupported/source-exclusion and C23 limits, run only the exact registration regression plus synthetic self-test/checker with bounded sequential execution, and reconcile all 30 rows and composite review coverage before FCE-01/digest acceptance. No additional C22 implementation or broad mechanic validation is currently required. The combined 182.032s invocation limitation and pending 1,000-turn publication witness remain explicit later-episode evidence; CE-08A/08B, PIPELINE-002 and `faithful_complete_episode:false` are unchanged. The refreshed local digest is stored outside this covered audit.


### C22 registration and FCE-01 source/evidence reconciliation — 2026-10-09

**Findings/verdict:** no material registration finding. C22 is registered accepted-scoped against the independent requestless-invalidation verdict, not against an author assertion. C23 keeps its enumerated B22 scope. FCE-01 is accepted only as pinned source/evidence inventory closure: all C01–C30 rows were reconciled to their source proofs, validators, privacy/restoration boundaries and prior independent verdicts in the current aggregate table. C01–C16 use CE-01/02/03 and B01–B32 finite/direct/indirect/generator exclusions; C17/C20 use the independently accepted prefix-replay/representability atlas; C18/C19/C21 use CE-04 type/stage/field proofs; C22 uses the reviewed carrier, Trace/plain/boost/Imposter/form and invalidation crosswalk; C23 uses reviewed B22 public-result and terminal-authority evidence; C24–C26 use CE-05 progression/request/revival proofs; C27/C28 use CE-06 origin/terminal and separately accepted source-outcome witnesses; C29/C30 retain diagnostic/privacy and pinned singles exclusions. Raw-only, unknown and unsupported forms retain their explicit fail-closed dispositions. No new mechanic or generic callback acceptance is introduced.

**Registration changes:** C22 source_backed:true and accepted-scoped; aggregate zero-unresolved. Stale C17/C20/C23 agreement metadata is reconciled. The checker requires the C22 independent review/source/test fragments and exact finite accepted-scope arrays for C22/C23. Missing source backing, unsupported expansion, missing authority proof and inconsistent aggregate counts reject. Existing source/config, generated-root, lifecycle, computed-callback, privacy and separate digest-review guards remain. No production validator or coverage-list membership changes.

**Composite review coverage:** entry digest reproduced. All 41 unchanged latest source/test/dependency hash rows from the intervening audit matched; the only old-row mismatch is the checker changed in this registration task. Earlier CE-01–CE-06 and C17/C20 independent scoped attestations remain the baseline, augmented by the independently reviewed publication-sweep closure, C22/C23 writer/terminal/carrier repairs, Trace and finite authority crosswalk, and final invalidation verdict. These verdicts cover the intervening implementation deltas; matching hashes alone are not used as semantic acceptance. The historical-prefix optimization has independent per-validation stream/source inspection and canonical Unicode identity/parity controls, with every historical reference validated and no cross-candidate cache trust. Its long-chain execution remains unverified. The newly changed checker/test registration logic is reviewed here and covered by the exact drift controls. The resulting 115-input digest is attested only for these accumulated scoped contracts and FCE-01 inventory closure, with the old C17/C20 digest preserved separately; its value is stored in manifest/progress to avoid self-reference. This does not certify every simulator state or future collection eligibility.

**Fresh checks:** exact `coverage checker covers config drift, local source hashing, and reachability routes` regression passed 1/1, 4.751s. Only its changed TypeScript test was transpiled using the installed compiler; no source rebuild or other test was selected. Separate `--reachability-self-test` passed, 0.619s, including C22/C23 scope expansion, invented C22 acceptance, missing finite authority, missing matrix, aggregate drift and existing source/lifecycle controls. Both ran sequentially through the real 180s process-group wrapper. Normal checker and whitespace results are recorded in progress after final digest freeze. Existing semantic checks are reused only within their independent scopes; no mechanic/episode suite ran.

| Changed validation input | Raw SHA-256 |
| --- | --- |
| `sim-core/scripts/check-simulator-coverage.cjs` | `d2d5aaa31e36841cf9695a4c75f5d8dd9171f0bd28f820a14fa5489a0cda7a10` |
| `sim-core/tests/simulator_coverage.test.ts` | `c80402dbb2ff20faeb4aec57fe33109c85267b9f28ccc1bbc87e86b0cca8b2a5` |

**Remaining prerequisites:** the combined short invocation still has an unresolved 182.032s timeout; individual passing cases are not a combined-command pass. The current-source 1,000-turn actor-row publication witness remains pending despite earlier scoped sweep acceptance. Those are FCE-02/FCE-06/FCE-07 complete-chain execution evidence under `PIPELINE_EPISODE.md`, not missing C22/C23 writer semantics. Next: separately authorized current-source long witness and final CE-08A positive-suite validation; CE-08B stop classification remains separate. No CE-08A/08B, PIPELINE-002, dataset/training/live or complete-episode acceptance; faithful_complete_episode:false remains unchanged. Prior scoped attestations and unrelated edits are preserved.


### CE-08A single authorized current-source long witness — 2026-10-09 (partial evidence; not accepted)

**Preflight:** accepted FCE-01 entry digest reproduced; all 43 latest recorded source/test/dependency hashes matched. The accepted macOS simulator-record interpreter is `.venv-simulator/bin/python`, CPython 3.9.6 / Clang 21.0.0; Node v24.21.0. A preparation build passed, with no source changes. Read-only process inventory showed no other test workload before launch and no witness/Python workload after completion; no user process was terminated. Expected historical runtime was about 13 minutes (775.5s, including 155.4s valid Python publication). One run only, exact anchored positive selector, visible 100-commit progress, hard 1,800s outer process-group deadline. Existing 360s sweep subprocess ceilings and 300s successful-publication assertion were unchanged; ordinary tamper checks retain their existing 30s limits. No broad/combined suite or retry ran.

| CE-08A required evidence | Applicable evidence and result |
| --- | --- |
| FCE-01 source/evidence inventory | Independently accepted C01–C30 reconciliation reused; no reachable source gap newly identified. |
| Normal v2 original-to-win chain, every actor row and waiting-side evidence | Existing `v2 evidence retains both owners at every commit...` current/independently reviewed short controls reused within their recorded hash/branch scope; full-result plus sweep publication and one-sided nonactor exclusion. No fresh normal-win execution. |
| Source simultaneous terminal, mirrored privacy and restore/replay | Both accepted source Destiny Bond cases reused: real engine execution, matching final evidence, repeated restored envelope/transition identity and full-result actor publication. Outcome is source simultaneous faint with a win, not a fabricated tie. |
| Turn-limit origin/predecessor, every boundary, both prefixes and terminal warning/tie | Fresh native chain passed: original owned requests, recursive predecessor binding, contiguous step/cursors, immutable exact prefixes, literal CE-02D warning in both prefixes, matching tie, null final requests and complete_capture:true; faithful flag remains false. Native continuation phase 143,335ms. |
| Every current-segment actor row / separate predecessor | Fresh valid Python sweep passed: 1,996 rows in 252,492ms, exact actor/transition ordering and no waiting rows; separately published predecessor's 2 rows passed. Total eligible publication evidence: 1,998 actor rows. |
| Rehashed middle actor ownership, atomic rejection and committed evidence | Fresh passed: canonical p2 action in p1 row, matching derived transition identity, TS owner rejection, Python exit 2/empty stdout, retained committed evidence/action identities. Invalid sweep phase about 35.176s from timestamped markers. |
| Origin/lineage/prefix/cursor/privacy/terminal adversaries | Existing accepted short cross-runtime matrix reused; long-specific wrong-outcome TS rejection/immutability passed, but its Python check timed out. Long-specific forged-origin check was not reached. |
| Restoration / deterministic replay | Reuse accepted normal/simultaneous and validated predecessor/restoration controls within their scopes. This long witness additionally repeats the first source transition/fingerprint/observations/prefixes; it does not freshly replay the whole 1,000-turn chain twice. |
| No incomplete/unsupported/execution stop counted positive | Native result satisfied completed/terminal/tie assertions. The overall test still failed and is not counted as a passing CE-08A candidate. |

**Execution:** exact command is recorded in `artifacts/validation/ce08a-current-source-2026-10-09/metadata.json`: `PYTHON="$PWD/.venv-simulator/bin/python" PYTHONPATH="$PWD/trainer/src" node --test --test-isolation=none --test-reporter=spec --test-name-pattern='^source turn-limit tie retains a complete two-perspective chain and bulk-publishes every actor row$' sim-core/dist/tests/pipeline_episode.test.js`. Test inventory: exactly 1 selected, 0 pass, 1 fail. Test elapsed 489.242s; outer elapsed 490.209s, exit 1; outer deadline did not expire. All 21 frozen source/compiled hashes remained unchanged. Native and publication durations above are separate test markers, not total-runtime estimates.

**Exact missing boundary:** `pipeline_episode.test.ts:1649` invokes `pythonRun(wrongOutcomeRehashed)` with the default 30,000ms subprocess timeout. It is a canonically resealed full long envelope whose supplied terminal winner is p1 while retained final evidence is tie. TS rejects without mutation. At source line 1650 / compiled line 1726, Python publication status was null with `ETIMEDOUT; signal=SIGTERM`, rather than the required 2. Its empty-stdout assertion was not reached, so empty stdout is not claimed for this candidate. The following forged-origin Python/TS block was not reached. This is missing timely semantic-rejection evidence, not a demonstrated acceptance/publication bypass. Inspection shows Python validates predecessor and ordered boundary evidence before comparing closure/terminal truth; the log does not establish which internal boundary it occupied when killed. No semantic error was returned. Preserve this distinction rather than treating timeout as either a valid rejection or a production bypass.

**Handoff:** the source chain and every actor-row publication gap now have current-source passing evidence, but the full witness is FAIL. CE-08A validation/acceptance remains pending. Smallest follow-up is separately authorized diagnosis/reproduction of this long-envelope outcome-only Python validation under an explicit targeted time budget, followed by the unreached origin-only check; do not regenerate or retry the entire long test automatically. The failed envelope payload was local to the test and is not persisted; its exact construction, command, frozen identities and logs are preserved. Any payload-capture fixture work, subprocess-budget change or validator/performance repair requires a separate task. No implementation or assertion changes occurred here, and no independent attestation is made.

Log and timestamped phase/status/hash metadata: `artifacts/validation/ce08a-current-source-2026-10-09/witness.log` and `metadata.json`. Combined short invocation remains an unresolved historical 182.032s timeout; individual passing cases are not a combined-command pass. CE-08B, PIPELINE-002, datasets/training/live and faithful complete-episode acceptance remain separate. reviewed_sha256 and prior attestations stay unchanged; faithful_complete_episode:false remains required. Only this checkpoint/current-status bookkeeping and one local digest refresh follow execution.

| Frozen validation input | Raw SHA-256 |
| --- | --- |
| `sim-core/tests/pipeline_episode.test.ts` | `b4a239dc7e2bedfff353548e1bd80fc49330b6808f8af88bb13d5566a2d7fc2a` |
| `sim-core/src/pipeline_episode.ts` | `56dcbb5fb13f658487eb582d2a70f7144b9e0479f8252a77ea2a0b90a9c35f03` |
| `sim-core/src/pipeline_episode_evidence.ts` | `1f1de5c349c970d2d12a70873342a353f69dde83f427aa8fac67e11264ab52f1` |
| `sim-core/src/pipeline_integration.ts` | `e75e3a0ee38ff399fc3ffb8ea363b7dbe8cb6dee97e5a9f9858f41d7a0b310f3` |
| `sim-core/src/belief_state.ts` | `3b7bbed39e078271de70ed10333bf3321177393d23d3880dbca477b20508eef5` |
| `sim-core/src/observable_state.ts` | `988a704abdd21dd24b4dfb5db8dedd16d4ce5308697ba7bfae453675709ae297` |
| `sim-core/src/state_extractor.ts` | `caf69c8f945e7404b2e50487a4d8ca1f9e76d62f6ceb42b3ddcd026c49caf51e` |
| `sim-core/src/public_ability.ts` | `cd02e081265ad427fca3f26c4a6a74497f006b23ea33f86d8dae1929b6478180` |
| `sim-core/src/public_health.ts` | `d268166d2b8f6b69d8f5d0905e93bf42b8d3f918a3a7071d1201f3fdf2bdca6d` |
| `sim-core/src/public_item.ts` | `98502db79fb5b92db057e140478106b273ade9134f8a5fab8a3368721dfd4a74` |
| `sim-core/src/typed_state_lifecycle.ts` | `a133a8c23d94993aab0ad3a6e8f4b921aaa65f76cf0eb8aa08ff392eea75f083` |
| `sim-core/src/protocol_contract.ts` | `65fc6f3eb2b91b150fd1b0af096aa6ab685e13fa395d091a762aced803934642` |
| `trainer/src/neural/pipeline_record.py` | `5b4c729eefbb2c291abbc09c9dfa2edf10abf5947295430543eb4f2114d589d5` |
| `trainer/src/neural/public_ability.py` | `6a3512c50afb706f70c1b17da3adae968960b58b2a4d3a3a8a1534ece751b3d4` |
| `trainer/src/neural/public_health.py` | `023f6002bc1dd1a82c65f6091eed071ae1d36729a3255f6d0f74b2a98c3373fb` |
| `trainer/src/neural/public_item.py` | `85b7f8069e1169ee6eea27f30418781720aa81964237cb9a5aac6e1f9d0f39c1` |
| `trainer/src/neural/typed_state.py` | `997e5cbfd37dcf4adb6c332492f47a42556bca747913a889a913f5e2b79ca951` |
| `trainer/src/neural/ts_identity.py` | `d9086a839312293258fa7a011b4965811253a9f85f66c4998219368c6cf84651` |
| `trainer/src/neural/protocol_contract.py` | `c5c3016514613a5d6fb0c611b9fa7b8256b6dcb26e7ab54cab210496582a6aab` |
| `trainer/src/neural/protocol_contract.json` | `4cbea57639e3a5d11e8387f9f84befcc531a613b13175351630b4377d087c213` |
| `sim-core/dist/tests/pipeline_episode.test.js` | `b43b9fa6967203bd567249d24b12428ee6a0c0fc0ac5279b8443fe448fd740af` |


### CE-08A recovered long-envelope negatives — 2026-10-09 (QA evidence complete; review pending)

**Recovery:** bounded search confirmed the previous artifact directory held only logs/metadata, with no serialized long envelope. Added only `sim-core/scripts/recover-ce08a-adversarial.cjs`, a recovery-only harness using the existing compiled source runner, same generated source route/config/policy, and canonical `sealPipelineEpisodeEvidence`/`episodeEvidenceContentDigest` helpers. No production validator, identity algorithm, existing assertion, schema or fixture changed. All 21 old source/compiled hashes matched before and after execution. Exactly one original-request → predecessor → terminal-tie source chain was regenerated; the separate repeated-first-transition source session and all actor publication calls were omitted. Predecessor was saved immediately, then valid/mutated long envelopes before the extra canonical/semantic validation. Recovery and TS checks completed in 202.935s. No publication sweep or predecessor publication was repeated.

**Identity/semantic proof:** all envelope/origin canonical IDs and every commit's origin reference are verified. Each mutation is reversed and canonically resealed to require exact equality with the validated original; unchanged observations, transitions, owner/request boundaries, predecessor and record joins therefore cannot conceal stale dependent references. Valid TS full-envelope validation additionally used the original actor records and expected run/origin context. Wrong outcome changes only the terminal winner to p1, preserving actual terminal tie evidence; TS rejects `evidence-terminal-join`. Forged origin changes continuation_segment to fresh_episode and recomputes origin ID, every commit origin reference and envelope ID; TS rejects `evidence-origin-metadata` (the retained segment boundary is not an initial boundary), while Python rejects its incompatible predecessor/origin claim. Candidate and original-envelope canonical content digests remain unchanged after TS rejection. No false identity error is accepted as semantic proof.

| Isolated Python candidate | Exit | Stdout bytes | Measured wall duration | Diagnostic |
| --- | ---: | ---: | ---: | --- |
| wrong-outcome | 2 | 0 | 115.192s | `pipeline-record validation failed: episode terminal evidence does not join its final boundary` |
| forged-origin | 2 | 0 | 5.017s | `pipeline-record validation failed: episode predecessor does not join the current segment origin` |

Python controls ran once each, sequentially, using `.venv-simulator/bin/python -m neural.pipeline_record` with saved JSON stdin and `PYTHONPATH=trainer/src`; fixed timeouts were explicitly waived. Files and metadata were saved before launch. The runner records PIDs, source/payload hashes, exact diagnostics and stdout/stderr files; no unchanged retry ran. Its 5s activity polling is included in measured wall duration. At 72s, wrong-outcome Python had 71.19s accumulated CPU time, 100% CPU and 632,992 KiB RSS; it was actively computing. Successful terminal-rule rejection at 115.192s confirms that the earlier 30s limit cut off necessary work on this exact source-derived envelope. The standalone path validates all preceding boundaries/public-prefix facts before final closure truth. No execution stall or acceptance bypass was demonstrated. Both validators exited; no task-owned workload remains. No user process was terminated.

**Preserved artifacts:** `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/` contains valid-envelope.json, predecessor.json, wrong-outcome.json, forged-origin.json, recovery.json, python-controls.json, each control's stdout/stderr, and run-isolated-controls.py. Console recovery log is `artifacts/validation/ce08a-current-source-2026-10-09/recovery-console.log`. SHA-256/size checks confirm all four payloads unchanged. The metadata contains the 21 unchanged baseline hashes plus the new recovery-harness hash and isolated-runner hash; no simulator snapshots, hidden sets or seeds were added to the envelopes.

| Payload | Raw SHA-256 | Bytes |
| --- | --- | ---: |
| `predecessor.json` | `83165b940ab2589c001a58ccad9a7668469848d02f6865fcf55b582508f1c0f9` | 51,325 |
| `valid-envelope.json` | `e66fe6f0c418e0273d166a21696755161e3c91c2f2b120b0a4c690f930199c95` | 182,180,582 |
| `wrong-outcome.json` | `072fc0c2d46988bae40f04453c36b94f8e3f282dd06caf7549571134cc167a54` | 182,180,581 |
| `forged-origin.json` | `c011f24c9bbea21caaad13f1129d1b8501e9b5f6aebd441b7245f528ea31fb56` | 182,180,575 |

**Combined evidence / handoff:** reuse the original native chain pass (143.335s), 1,996 segment actor rows published in 252.492s, two separately published predecessor rows, and canonical middle-row atomic exit-2/empty-stdout rejection against the matching 21 source hashes. This task supplies the two previously missing long-envelope negatives. Existing accepted normal-win, mirrored simultaneous terminal, waiting-side, restoration and short privacy/lineage controls retain their scopes. The long witness's required evidence set is now assembled across the earlier execution plus isolated checks, ready for independent CE-08A semantic review; this is not a passing invocation of the original long test, and the combined short-command 182.032s timeout remains unresolved. No further negative execution or battle regeneration is identified for this narrow handoff. Independent review must assess the new harness and evidence reuse, and the final CE-08A scope; no QA self-attestation or CE-08B/PIPELINE-002 promotion. reviewed_sha256, prior attestations and faithful_complete_episode:false remain unchanged. The recovery harness is added to local coverage inputs; only the candidate digest is refreshed.


### Independent CE-08A complete recorded-evidence review — 2026-10-09 (accepted scoped)

**Findings:** no material finding in the assembled positive complete-episode evidence or recovery harness. **Open questions:** none blocking this scope. No test, battle generation, build, coverage checker, publication or semantic-validator execution was performed by this review. Artifact inspection used read-only JSON parsing, SHA-256/canonical helper calculations and structural comparisons; these are independent checks of saved evidence, not a rerun of QA workloads.

| Requirement / review crosswalk | Verified basis and scope |
| --- | --- |
| FCE-01 pinned output/request/lifecycle/source closure | Prior independent C01–C30 reconciliation and attested FCE-01 scope retained. All 30 source-backed registrations, finite computed/callback route exclusions and C17/C20/C22/C23 truth boundaries remain; no sample-based reachability promotion. |
| Normal win / one-sided waiting / actor publication | Accepted normal v2 original-to-terminal case and individual short evidence supply complete envelopes, full-result and bulk publication, one-sided evidence without actor rows, origin/prefix/outcome/privacy adversaries. Reuse their recorded scopes and intervening independently reviewed finite writer/authority corrections; no new generic callback authority. The evidence-only terminal join check does not replace these actor publication controls. |
| Simultaneous outcome / restoration | Accepted mirrored generated Froslass Destiny Bond source-engine cases, original owned requests, repeated restored envelope/transition identity and every actor row through full-result Python publication. The actual simultaneous faint outcome is a win under the pinned source rule, not a fabricated tie; turn-limit provides the separate real tie. Source partner construction and generated-format reachability remain distinguished. |
| Original → predecessor → turn-limit tie | Saved valid envelope independently has 999 contiguous commits (1 predecessor + 998 segment), both original owned requests, exact immutable prefix extension, correct cursor lengths, matching final ties and null requests. Both final prefixes contain the exact CE-02D warning and end in |tie. The persisted predecessor equals the recursively retained predecessor. Completion is original_initial_requests; no restored terminal-only relabeling. |
| Every eligible actor / separate predecessor | Original hash-bound witness reached successful exact row/transition/perspective ordering and actor-count assertions: 1,996 current-segment rows in 252.492s, plus 2 separately published predecessor rows. Saved artifact independently contains 1,998 actor entries. Recovery does not claim new actor publication; code contains no Python/sweep call. Waiting/nonactor rules are also covered by the accepted normal one-sided case. |
| Middle actor semantic tamper | Original witness passed canonical p2 action ownership, derived dependent transition identity, TS p1 rejection, unchanged committed evidence/action IDs, Python exit 2 and empty stdout before reaching its later outcome timeout. Later exit 1 does not erase earlier executed passing assertions. |
| Wrong outcome | Saved candidate SHA-256 matches QA metadata; canonical envelope/origin IDs and commit origins match. Undoing only terminal winner plus canonical reseal produces the exact valid envelope. TS evidence-terminal-join and immutable-content checks are recorded by the matching harness. Python stdout file is actually zero bytes, stderr matches terminal/final-boundary mismatch, recorded exit 2 and 115.192s. This successful same-source completion supersedes the earlier missing rejection evidence, not the historical failing invocation. |
| Forged origin | Saved SHA-256 and canonical origin/envelope IDs verified; every dependent commit origin reference updated. Undoing kind/origin references plus canonical reseal exactly restores valid evidence. TS evidence-origin-metadata is the intended fresh-origin-at-segment-boundary semantic failure, not a stale identity. Python stderr is predecessor/origin mismatch, stdout zero bytes, recorded exit 2 / 5.017s. |
| Privacy / truth / restoration / remaining adversaries | Reuse accepted CE-01–CE-06, C17/C20/C22/C23 and repaired short full-result controls for grammar, private ownership, truthful maps, stage, immutable prefixes/cursors, gaps/order/duplicates, origin and terminal claims. Independent full-prefix inspection and the long Python outcome traversal preserve those current boundaries. No target-private ability, foreign request, seed, snapshot, hidden set, timer or future suffix is authorized. Complete-chain restoration is supported by existing source/continuation/normalized-identity proofs and repeated normal/simultaneous controls; no fresh twice-replayed full 1,000-turn chain is claimed. |
| Scope / evidence dependencies | All 21 original/recovery source and compiled hashes match actual current bytes; all 45 latest source/test hash rows match. Recovery harness and isolated runner match their recorded hashes. Actual stdout/stderr files agree with python-controls.json. Raw payload digests, intended-change-only comparisons, and 999-boundary continuity were independently inspected, rather than taking prose pass labels alone. |

**CE-08A verdict:** accept the positive complete-episode capture evidence for the existing pinned pokemon-showdown@0.11.10 Gen 9 Random Battle singles v2 contract: original owned requests, complete two-perspective retained chain, valid resumed predecessor binding, source normal win/simultaneous-terminal/turn-limit tie, actor-only Python publication, truthful public evidence, privacy, deterministic restored/source progression, and coherently rehashed adversarial rejection. Separately recorded applicable evidence satisfies these requirements; neither spec FCE-02/FCE-06/FCE-07 nor PIPELINE_EPISODE requires a single combined command to establish them. No remaining CE-08A positive-evidence obligation is identified within that inventory. This is not universal simulator, training/live, other-format or faithful-complete-episode acceptance.

**Coverage / attestation:** entry 116-input digest reproduced. The accepted FCE-01 digest is the independent implementation baseline; intervening production validators, identity algorithms and existing test bodies are unchanged against the 21 frozen hashes. The only new executable coverage input is the narrow recovery harness, reviewed here: same seed/config/first switch/predecessor construction and switch policy, no actor publication, atomic payload persistence, existing canonical helpers, exact inverse-mutation equality, semantic TS error and content immutability, current-source binding. Saved isolated runner preserves ordinary neural.pipeline_record CLI behavior and records actual output/status; no hidden cache or validation bypass. The remaining deltas are reviewed evidence/status bookkeeping. Thus the resulting digest is justified only for accumulated prior scopes plus CE-08A positive capture; preserve the prior FCE-01 digest and all earlier scoped attestations. Raw payload hashes and supporting artifact hashes are recorded in manifest review metadata; they are not silently substituted for coverage source hashing. The resulting digest is recorded outside this covered audit to avoid self-reference.

**Limitations:** original long invocation still exited 1 at its 30s subprocess budget; it is not relabeled passing. Later outcome completion took 115.192s, so the old budget was insufficient. Historical combined short invocation timeout (182.032s) is also not resolved. Individual and isolated evidence supplies the required semantic checks without promising those command invocations complete. CE-08B, PIPELINE-002 and any faithful_complete_episode flag change remain separate; faithful_complete_episode:false is unchanged.

**Exact next CE-08B task:** reconcile S01–S12 with current accepted C01–C30 reachability and the v2 envelope. Prove that unsupported-format/protocol/boundary/revival, cancellation, transition/attempt/rejection budgets, action exhaustion, invalid options/policy, malformed/execution, settling and cleanup failures retain the last valid committed boundary, expose the original classified cause, and cannot count as initial-to-terminal complete capture. Verify terminal precedence at limits/cancellation and after committed terminal delivery, actor-only/empty invalid publication, immutable rejected candidates and valid prior lineage. Reuse matching existing controls; add/execute only missing exact short controls with normal AGENTS process limits, no long regeneration or publication sweep. Produce the FCE-08 final review packet/source-config-local identities for a separate acceptance review; do not change the faithful flag or promote PIPELINE-002 automatically. No such tests are run or authorized by this review record itself.


### CE-08B S01–S12 QA reconciliation / FCE-08 review packet (2026-10-09; authoring checkpoint)

**Proposed scope:** truthful pinned v2 stop/error classification, retained committed boundaries, terminal precedence, actor-only publication and reproducible review evidence. All twelve rows are review-ready within their guards/source exclusions; this is not independent acceptance, PIPELINE-002 promotion, or a faithful flag change. CE-08A's accepted positive scope at `197d1b90334547f58cef0e4eead41f164838897a16fb7dfb74fa471ff491d3b2` is preserved.

Governing requirements: spec REQ-012, FCE-02/FCE-05/FCE-06/FCE-07/FCE-08; CE-08B row 17b; `PIPELINE_EPISODE.md` outcome and CE-06B closure contracts. Hash dependencies below: RUN = pipeline_episode.ts; PUB = pipeline_record.py; EP = pipeline_episode.test.ts; ENV = pipeline_episode_evidence.ts; INT = pipeline_integration.ts; SET = settling.ts/settling.test.ts. Exact current hashes and execution metadata are in `artifacts/validation/ce08b-stop-reconciliation-2026-10-09/evidence.json` (SHA256 `2fdce486b6b79afeb606e8e49e7b234fc445504c9d590653f6bb3be508c36160`). All remain coverage-listed. Each row below has prior accepted guard/source evidence plus the indicated fresh evidence; no S-row attestation is made here.

| Row / governing obligation | Implementation / source disposition | Valid and negative evidence; dependency boundary | Disposition / missing evidence |
| --- | --- | --- | --- |
| S01 / REQ-012, FCE-07 | RUN format guard, no session initialization outside gen9randombattle | Fresh `CE-08B v2 cancellation and exhaustive rejections retain incomplete actor-free evidence`: unsupported format has no initial boundary; PUB exits 2 with empty stdout. RUN/PUB/EP | Ready for review; excluded scope stays explicit. |
| S02 / REQ-012, FCE-06/07, C09 | RUN classifyError; INT diagnostic context; unknown/alias guards remain fail-closed | Reuse five source-shaped unsupported/malformed candidate rollback controls in the 34-case table. Fresh classified-failure table checks alias, unsupported-record, unsupported-observable versus malformed-observable, exact cause/index 7, immutable origin and zero rows through valid v2 partial-result validation. RUN/INT/PUB/EP | Ready; repaired dropped diagnostic index. No broad diagnostic allowlist. |
| S03 / FCE-05/07, C26 | RUN actingPlayers; pinned B26 makeRequest/getRequests/turnLoop no-route proof | Reuse controlled requestless zero-action stop and accepted CE-05-BOUNDARY proofs/restoration. Successful stable requestless/wait-only singles pairs are source-excluded, not missing mechanics. RUN/INT/ENV/EP | Ready; current ledger metadata reconciled to accepted B26. No fabricated waiting action. |
| S04 / FCE-05/07, C25 | RUN selection guard; accepted B23–B25 source routes and exclusions | Reuse source-shaped Revival flag guard and mirrored/consecutive/copied-user accepted revival/restoration/publication. Active-target/multi-active/simultaneous selections retain excluded disposition. RUN/INT/EP | Ready; no new revival semantics or route claim. |
| S05 / FCE-02/07 | RUN terminal-before-abort loop; commit accumulation synchronous | Reuse initial/in-flight cancellation; fresh v2 initial and after-commit cancellation verify immutable prior boundary, incomplete segment and zero/two actor rows. RUN/ENV/PUB/EP | Ready; no invented nonactor row. |
| S06 / FCE-02/07 | RUN finite budgets, counters and rejection reset; PUB shared metadata accounting | Reuse both budget controls, rejection caps, aggregate attempt accounting and reset-only-on-commit. Fresh terminal-at-exact-limits control; canonical result/envelope joins with negative/contradictory counters now reject before stdout. Full and compact paths share the counter validator. RUN/PUB/EP | Ready; repaired Python acceptance of negative/inconsistent counters and stop/status mismatch. |
| S07 / FCE-05/07 | RUN enumerates current request tuples without duplicates | Reuse natural Arena Trap alternate-action success; fresh exhaustive v2 mock rejections assert every legal tuple exactly once, actor-free evidence and no complete capture. RUN/INT/ENV/PUB/EP | Ready; exhaustion control is an intentional adapter rejection, not a claim a supported source battle exhausts. |
| S08 / REQ-012, FCE-07 | RUN limitsFor/actionTuples | Reuse invalid finite limits, unversioned policy, illegal permutation and invalid continuation options retaining the origin/closing session. No selection or commit on invalid options. RUN/EP | Ready; historical guards unchanged. |
| S09 / FCE-05/07 | RUN SettlingError cause; SET sticky barrier/fan-out | Fresh five exact pipeline failure controls (timeout/message-limit/simulator-error/stream-closed/cancelled) discard progressed candidates, release resources/timers and preserve lineage; undelivered terminal closure fails. Fresh v2 classifier propagates all five original cause codes. Reuse initialization EOF and post-commit simulator failure. RUN/SET/INT/EP | Ready; no new runtime deadline/transport design. |
| S10 / FCE-06/07 | RUN malformed/execution classification and final evidence-invalid delivery barrier; PUB result metadata | Reuse malformed raw candidate rollback, initialization and execution failures plus accepted canonical prefix/privacy/origin/outcome negatives. Fresh malformed cause/index and cleanup after one valid commit preserve origin/records. Canonically unchanged envelope/actor joins plus false status/code reject atomically in ordinary and compact publication. RUN/ENV/INT/PUB/EP | Ready; evidence-invalid is explicitly registered as S10 failure, not a new stop row or truncation. |
| S11 / FCE-02/07 | RUN finally closes owned session; cleanup supersedes execution status while retaining its cause | Fresh cleanup after initial cancel, post-commit cancel, post-commit malformed error and terminal; cause/index retained, no raw private error text, earlier boundary immutable, only validated prior actor rows publish. RUN/ENV/PUB/EP | Ready; repaired loss of preceding cause. |
| S12 / FCE-02/07 | RUN terminal before abort/budgets; ENV both-perspective final joins | Reuse independently accepted CE-08A normal win, simultaneous KO win, original/predecessor/turn-limit tie, 1,996 segment + 2 predecessor publications and canonical outcome/origin/middle-row negatives. Fresh one-turn constructed engine stop fixture verifies terminal precedence at both limits with cancellation, null requests via ENV and two actor rows. RUN/ENV/PUB/EP | Ready; constructed stop fixture is not a new generated-team reachability claim. |

**Narrow repairs:** RUN adds optional sanitized `cause_record_index` and preserves prior classified cause/index when cleanup fails. PUB validates documented stop/status taxonomy (including S10 evidence-invalid) and nonnegative integer counters, committed/rejected accounting, declared limits and exact budget exhaustion. No observation, belief, transition, envelope identity, extraction, actor semantics or performance algorithm changed. Missing/invalid envelopes still fail before publication. Valid partial results may publish their already committed actor rows; invalid result metadata may publish none.

**Identity / immutability:** result stop/counter metadata is outside run/envelope hash inputs. Tests keep all canonical observations/beliefs/actions/transitions/envelope IDs and joins unchanged and validate the envelope before submitting contradictory metadata; no invented hashing scheme or stale-identity negative. Candidate and original result equality are asserted after rejection; controller failure/cancellation/cleanup controls retain frozen prior boundary objects. Python full-result and compact status negatives exit 2/empty stdout; four counter negatives exit 2/empty stdout through the shared metadata rule. Existing rehashed prefix/origin/privacy/outcome controls remain reusable at their accepted scope.

**Capture versus execution:** CE-06B defines complete_capture as the immutable original-request-to-matching-terminal chain, independently of cleanup success. Failed execution is not faithful-complete acceptance; faithful_complete_episode is always false. Do not erase truthful terminal evidence or relabel failed cleanup as completed. Unbound continuation/terminal-only controls remain complete_capture:false. This checkpoint does not redefine the accepted envelope closure contract.

**Fresh execution:** final build passed (1.673s). Four exact CE-08B cases passed (2.342s; 785.442/679.781/303.263/395.075ms), including ordinary/compact status negatives and nine classified causes. Six exact settling cases passed (0.502s; 176.624/32.325/35.207/30.469/31.202/0.162ms). All runs sequential, visible, enforced 180s process-group timeout; no timeout or owned workload remains. Initial regressions reproduced stop/status acceptance, dropped index, lost cleanup cause, and negative-count publication before repair. No broad suite, combined episode invocation, positive episode replay or long sweep ran.

**Reuse boundary:** all 21 CE-08A frozen hashes matched before edits. Afterwards only RUN, PUB, appended EP and its compiled test differ among that baseline. Existing test bodies and actor/identity/lineage functions are unchanged; accepted source proofs and capture witnesses are reused on that branch-specific basis, not relabeled current whole-file passes. New metadata paths have fresh focused evidence. Accepted macOS profile: .venv-simulator CPython 3.9.6 arm64; Node v24.21.0; pinned pokemon-showdown@0.11.10 tree `12d83949635889cd10a51a081890f9dfc6d3ed480eacf2a9a0728fb48e8e086c`; gen9randombattle singles; stop fixture seed [1,2,3,4], regular guard fixture [101,202,303,404]. Simulator snapshots stay test-local and never enter publication.

**Review handoff / limits:** no demonstrated defect remains within this reconciled matrix after the narrow repairs. Independent review must inspect new RUN/PUB metadata behavior and the focused controls before accepting CE-08B/FCE-08. Historical combined short-command timeout (182.032s) and original long-command failure at the former 30s negative timeout remain execution limitations; independently completed long negative evidence already supersedes its missing-evidence gap. Neither command is relabeled passing or required to be rerun for convenience. The manifest's local digest is the reproducible candidate; reviewed_sha256 and all prior attestations stay unchanged. PIPELINE-002 acceptance, any faithful flag change, datasets/training/live remain separate.


### Independent CE-08B / FCE-08 review (2026-10-09; acceptance and attestation withheld)

Entry candidate `0979c06c107f07d6253d5805c89745d2630ba495eb3c2d36c0e6b52cb148a566` reproduced over all 116 coverage inputs. All seven QA dependency hashes and the packet SHA256 `2fdce486b6b79afeb606e8e49e7b234fc445504c9d590653f6bb3be508c36160` match actual bytes. Reused four focused passes, six settling passes and the accepted source/capture evidence at their stated scope. No production or test code was changed during review. The following complete blocker set supersedes the author's all-rows-ready conclusion.

| Severity / S-row | Finding and exact reproduction | Smallest repair / proof boundary |
| --- | --- | --- |
| Medium — S06/S08 | PUB `_validate_pipeline_episode_result_metadata` only checks budgets when limits is a Mapping, and never rejects unknown Mapping keys. Canonically resealed zero-commit results claiming transition-budget with limits null, [] or 42 all exit 0 / 3 stdout bytes (`[]`), while the same zero-commit claim with valid finite limits correctly exits 2 / zero stdout for budget not exhausted. An extra_budget key is likewise accepted by Python with exit 0, while RUN's actual invalid-options control rejects it before any session/attempt. All observation/belief/run/origin/envelope joins use existing canonical helpers and TS envelope validation passes. | Enforce the runner's exact result-limit schema and null compatibility only for the legitimate invalid-options/no-work outcome. Add ordinary and shared compact metadata controls for nonobjects/unknown keys and preserve valid invalid-options continuation. This demonstrates invalid result acceptance, not an emitted actor-row or privacy leak. |
| Medium — S04 | RUN classifyError recognizes both `seeded-revival/v1/unsupported-request` and `seeded-forced-switch/v1/unsupported-revival-blessing`, then drops the whitelisted original cause. Pre-selection fault controls for both return identical generic stop objects and identical payload hashes, despite distinct known causes. | Preserve these two safe known cause codes, with no arbitrary error text. Exercise both guards and cleanup preservation using the same finite whitelist. No new generated route is claimed. |
| Medium — S04/S06 | The same known Revival guard thrown at candidate phase produces a legitimate controller-classified truncated result with attempts=1, committed=0, rejected=0. PUB rejects it as an unaccounted attempt because only unsupported-protocol is exempted from clean-stop equality. Both variants exit 2 / zero stdout; canonical envelope remains valid, and owned mock session closes with its boundary unchanged. The pre-selection variants (attempts=0) pass. | Reconcile nonrecoverable attempted-guard accounting with the explicit S04 classification; add before-attempt/after-attempt controls, including retained prior actor rows where applicable. This is a constructed error-boundary parity defect, not evidence of a new reachable generated mechanic or a publication bypass. |
| Medium — S10/S11 | RUN calls createPipelineEpisodeEvidence outside the final evidence-validation try and before session.close. A malformed terminal boundary first classifies as execution-failed; terminalEvidence then throws `evidence-terminal-perspectives` during construction, so the promise rejects and owned session.close is not invoked. Reproduction records closed:false. The expected versioned failure result/delivery barrier is never returned. | Guard evidence construction as well as validation and guarantee owned-session cleanup through construction failures. Add an exact construction-failure/invalid-terminal control verifying structured failure, retained prior evidence and cleanup. The negative is a controlled malformed boundary, not a generated valid-terminal defect. |

Reproductions used only the saved 51KB predecessor artifact's original observations and projectBeliefState/createPipelineEpisodeEvidence canonical helpers. No battle or long envelope was regenerated; no source-chain sweep or combined episode command ran. The first attempted extraction from valid-envelope.json correctly stopped because that artifact is an envelope, not a full result with records; no semantic verdict is taken from that harness error. The corrected bounded artifact-only controls completed in 1.565s, followed by one new unknown-key sibling control in 0.400s, sequentially with enforced 180s process-group and 30s Python limits. Positive cancellation control exits 0 with zero actor rows; finite-budget negative exits 2 with empty stdout. Artifact payload hashes, both reproduction scripts and results are persisted under `artifacts/validation/ce08b-independent-review-2026-10-09/`; review-metadata.json binds the seven unchanged dependencies and every reproduction artifact. No emitted DATA-001 actor-row leak or false typed-state/privacy bypass was demonstrated. Candidates and underlying saved observations remained unchanged; the malformed-construction control exposes the cleanup failure rather than claiming successful cleanup.

**FCE-01–FCE-08 reconciliation:**

| Gate | Independent reconciliation / current verdict |
| --- | --- |
| FCE-01 | Preserve accepted pinned source/evidence closure: manifest has exactly C01–C30, unique IDs, all source-backed, zero-unresolved. New findings concern stop/result validation, not a newly reachable output/callback family. No automatic whole-project acceptance. |
| FCE-02 | Accepted CE-06A/06B/08A original/predecessor/two-perspective positive chain remains applicable; no origin/lineage implementation change or new lineage bypass demonstrated here. Error-delivery completeness remains blocked under S10/S11. |
| FCE-03 | Accepted mirrored privacy/causality evidence and eligibility boundary remain applicable; no private field or foreign request leak demonstrated. New diagnostic index is sanitized and private error details are not copied. |
| FCE-04 | Accepted evidence-derived typed/raw dispositions remain intact; no state-extraction change or new false-map route demonstrated. |
| FCE-05 | Accepted supported request-pair progression/restoration remains intact; error/resource-release closure is incomplete because evidence construction can bypass cleanup. |
| FCE-06 | Accepted positive actor publication and canonical grammar/privacy/origin/outcome controls remain applicable. Current stop/limit schema acceptance and S04 result parity are blocked by the findings above. |
| FCE-07 | Accepted positive terminal outcomes and terminal-before-cancel/budget controls remain valid; incomplete/error closure is withheld for S04/S06/S08/S10/S11. Intrinsic immutable complete_capture is distinct from failed execution and faithful acceptance, as the existing CE-06B contract requires. |
| FCE-08 | Packet dependency/digest identities verified, but final closure review does not pass while these defects remain. No accumulated scope or flag promotion is inferred. |

**Separate verdicts:** CE-08B acceptance withheld; FCE-08 final review acceptance withheld. No digest is attested. Preserve CE-08A's accepted scope, reviewed_sha256 `197d1b90334547f58cef0e4eead41f164838897a16fb7dfb74fa471ff491d3b2`, earlier scoped attestations and faithful_complete_episode:false. Local digest alone is refreshed for this review-record update and is recorded in the manifest to avoid covered-document self-reference. The historical combined short-command 182.032s timeout and original long invocation's earlier 30s negative timeout failure remain documented execution limitations; isolated completed negative evidence supersedes the long missing-evidence gap but does not make either invocation pass.

**Exact next prerequisite:** one bounded S04/S06/S08/S10/S11 repair/proof batch for result-option schema, known Revival cause/accounting and final evidence-construction cleanup, followed by independent CE-08B/FCE-08 review. Permit only exact short artifact/controller/publication controls, sequential 180s limits; no broad suites, combined command, long witness, battle regeneration, performance or mechanic work. Then separately decide PIPELINE-002 acceptance and merge readiness; any faithful flag promotion requires explicit authorization. This review makes no merge-ready claim for the unrelated dirty checkout.


### CE-08B four-finding repair checkpoint — 2026-10-09 (pending independent review)

The four independent findings are repaired within S04/S06/S08/S10/S11. This authoring checkpoint does not attest CE-08B/FCE-08 or supersede prior accepted scopes.

| Finding / rows | Repair and exact fresh regression | Disposition |
| --- | --- | --- |
| Limits / S06/S08 | PUB requires exactly three positive JavaScript-safe integer budgets, rejecting null/nonobjects, missing/unknown keys, booleans, fractions and out-of-range values. Canonically resealed ordinary and compact controls reach the limits schema diagnostic; valid defaults, explicit budgets and maximum safe budgets pass. | Repaired, review pending. Per current explicit instruction, null-limits invalid-options remains a structured controller result but is unpublishable; no legacy null exception. |
| Revival cause / S04 | RUN preserves both exact recognized safe guard codes, before selection, during a candidate and after a saved commit; generic private text is discarded. Cleanup preserves the cause. | Repaired, review pending; no new generated mechanic claimed. |
| Attempt accounting / S04/S06 | PUB admits zero or one nonrecoverable stopped attempt only for recognized guard classifications. Commit/rejection totals, bounds, final rejection counts and clean-stop equality remain enforced. Both guards pass with 0/1/2 attempts and 0/0/1 commits; forged/missing causes and inconsistent siblings reject. | Repaired, review pending. |
| Construction / S10/S11 | RUN guards run identity, construction and validation, emits evidence-invalid with safe construction/validation stage and null envelope, and always attempts owned cleanup. Cleanup-failed wins on dual failure while retaining cause/stage/index and prior records. | Repaired, review pending. |

Fresh artifact-only suite: three exact cases pass individually (limits 4.124s; Revival 3.155s; construction/validation/cleanup 0.664s); final build passed in 1.636s. Sequential visible execution used enforced 180s process-group and 30s Python subprocess limits. No battle regeneration, broad suite, combined invocation or long witness. The 51KB predecessor supplies original observations and the saved first switch; existing canonical action/belief/envelope helpers rebuild matching actor joins. Tests assert selected action IDs equal the saved transition, validate canonical joins, preserve input/committed content, publish valid zero/two actor controls, and require every invalid publication to exit 2 with empty stdout. Construction regressions cover faults before validation, actual terminal-evidence construction, validator faults, dual cleanup failure and the original malformed-terminal boundary.

S01–S12 inventory and accepted source exclusions remain as previously recorded. The affected rows above replace their readiness conclusion only after independent review; other actor/identity/lineage and settling implementations are unchanged. Earlier four-case stop results are not claimed as fresh whole-file passes after RUN/PUB changes: the new saved-artifact cases directly exercise the changed finalization, schema and accounting paths. Unchanged settling/source proof evidence is reused within its prior scope. No observation/identity algorithm, mechanic, dependency or performance change. Exact current dependency hashes and fresh execution summary are in artifacts/validation/ce08b-four-finding-repair-2026-10-09/evidence.json.

- `sim-core/src/pipeline_episode.ts`: `30e53f61d6a60659c3c29597e5d5c24f9796c02f2bd250fc81eb2710c40df866`
- `trainer/src/neural/pipeline_record.py`: `9760ab4778c8ea7ad146208761f4207a86ddbb56f2b1699c977ba4ad9f40273b`
- `sim-core/tests/pipeline_episode_stop_repair.test.ts`: `9df965ab6493847e79af6fcca509bb1143d75364173e7e884b6529f6d8719fdf`
- `sim-core/src/pipeline_episode_evidence.ts`: `1f1de5c349c970d2d12a70873342a353f69dde83f427aa8fac67e11264ab52f1`
- `sim-core/src/pipeline_integration.ts`: `e75e3a0ee38ff399fc3ffb8ea363b7dbe8cb6dee97e5a9f9858f41d7a0b310f3`
- `sim-core/src/settling.ts`: `c520a786f90e5765e03c866975d7a130e7ad52e39aa8ca148371b2c83a4891d0`
- `sim-core/tests/settling.test.ts`: `0c3a80daa61815294d1b9713e51ed36b0e83eecb9ce97aee64fc8bd6f0fe963b`
- `artifacts/validation/ce08a-adversarial-recovery-2026-10-09/predecessor.json`: `83165b940ab2589c001a58ccad9a7668469848d02f6865fcf55b582508f1c0f9`

Local candidate digest is recorded in the manifest to avoid covered-document self-reference; reviewed_sha256 and prior scoped attestations remain unchanged. Historical combined short timeout (182.032s) and original long invocation's superseded 30s negative timeout failure remain documented; neither is relabeled passing. CE-08A acceptance is preserved, faithful_complete_episode:false unchanged. Exact next step: independent review of these RUN/PUB repairs and artifact-only regressions, then separate CE-08B and FCE-08 verdicts; PIPELINE-002, merge readiness and any flag promotion remain separate.

Repair checkpoint coverage checks: synthetic drift self-test passed (exit 0, 4.054s); normal checker returned exit 1 (0.453s) solely for the expected separate semantic-review digest gate. No source/config/reconciliation drift was reported.


### Independent CE-08B four-repair / FCE-08 final evidence review — 2026-10-09 (accepted scoped)

**Findings:** no material finding within the four-repair boundary or reconciled S01–S12 packet. **Open questions:** none blocking these scopes. No tests, build, battle regeneration, checker workload, combined invocation or long witness ran in this review. Fresh verification was read-only hash reproduction and inspection of source, contracts, tests and saved execution artifacts.

Entry 118-input digest reproduced as `c8b0faacb8f972209aed0c8e11de7bc4d2b86a832bed914a3ca1a097c702aec6`. All eight repair/fixture hashes match. The five unchanged prior QA dependencies (EP, ENV, INT, settling source/test) match; RUN/PUB differ only within the explicitly reviewed stop/metadata/finalizer boundary. The 21-input CE-08A baseline differs at RUN/PUB and appended EP/compiled EP; its 17 other dependencies match. Accepted CE-08A metadata/log/recovery/isolated-control/output artifact hashes match their manifest bindings. The pinned installed source/config tree independently reproduces `12d83949635889cd10a51a081890f9dfc6d3ed480eacf2a9a0728fb48e8e086c`, package 0.11.10, gen9randombattle/gen9 singles random.

**Four-repair semantic review:** Python accepts only the normalized result limits object with exactly max_transitions/max_attempts/max_rejections_per_boundary and positive integers through Number.MAX_SAFE_INTEGER. This matches what the runner serializes after expanding partial options, rather than imposing full-result shape on partial caller options. Nonobjects, unknown/missing keys, booleans, strings, fractions and invalid ranges reject. Null-limits invalid-options remains a safe controller diagnostic but is deliberately unpublishable under the latest explicit repair requirement; the earlier review's suggested null compatibility is not retained. Canonical run/origin/envelope resealing proves schema rejection is not a stale join. Ordinary and compact publication share the same metadata rule.

The two exact recognized Revival errors retain distinct safe cause codes; arbitrary exception text is absent. Attempted work is commits + retryable rejections + at most one nonrecoverable stopped candidate. Recognized Revival truncation and existing unsupported-protocol stops may carry that last attempt; clean cancellation/exhaustion/budget/terminal stops still require equality, and all counter/budget bounds remain. Selection errors consume zero attempts; candidate guards consume one; a guard after one valid commit consumes two with zero retryable rejections. Missing/forged causes and inconsistent siblings reject before output. Cleanup after the recognized guards preserves each cause.

Run serialization, envelope construction and validation now share the guarded finalizer; construction exceptions return evidence-invalid and null envelope instead of escaping cleanup. Construction/validation stage is a constant safe enum. Owned close is attempted afterwards. Dual construction/cleanup failure gives cleanup-failed precedence while preserving the earlier cause, index if present and evidence stage. Committed records and final summaries are retained, but null envelope rejects publication. The original malformed-terminal constructor reproduction is covered alongside before-validation/real-construction/validator failure injection. Valid retained partial rows remain publishable only with a valid envelope. A failed cleanup does not erase a truthful immutable terminal capture fact and never makes execution completed or faithful.

**S01–S12 reconciliation:**

| Row | Governing requirement / inspected evidence | Scoped verdict |
| --- | --- | --- |
| S01 unsupported format | REQ-012/FCE-07; RUN format guard, unchanged unsupported-format control and empty invalid publication; no foreign-format session initialized. | Accepted guard/exclusion. |
| S02 unsupported protocol | FCE-06/07/C09; accepted unknown/alias grammar guards, immutable candidate rollback, classified-failure cause/index controls; no broad diagnostic acceptance. | Accepted classified stop, prior source exclusions retained. |
| S03 unsupported boundary | FCE-05/07/C26/B26; supported request-pair progression and source no-route proof for stable wait/requestless singles; synthetic zero-action guard. | Accepted explicit no-route/guard, no fabricated actions. |
| S04 Revival guard | FCE-05/07/C25/B23–B25; bounded bench-revival proof/excluded variants plus both fresh saved-artifact guard phases/cleanup, distinct causes and rejection siblings. | Accepted bounded guard accounting and cause preservation. |
| S05 cancellation | FCE-02/07; initial/in-flight/after-commit controls, prior boundaries retained, incomplete chain, zero/two actor rows, terminal-before-abort. | Accepted. |
| S06 budgets | FCE-02/07; finite normalized limits, attempts/rejections/reset controls, exact budget exhaustion, fresh schema/accounting negatives, terminal precedence. | Accepted bounded limits/count semantics. |
| S07 exhaustion | FCE-05/07; accepted Arena Trap alternate action, exact tuple enumeration/exhaustion and immutable rejection, no repeated/fabricated defaults. | Accepted guard; mock exhaustion is not generated mechanic reachability. |
| S08 invalid options | REQ-012/FCE-07; existing illegal policy/limit guards, no-work continuation cleanup, fresh invalid-options null-limits publication rejection. | Accepted controller diagnostic/unpublishable result. |
| S09 settling | FCE-05/07; unchanged six focused settling resource/rollback cases, five safe causes propagated by classified-failure controls, EOF and undelivered terminal failure. | Accepted within existing settling contract; no synchronous preemption claim. |
| S10 execution/evidence | FCE-06/07; malformed/privacy/lineage publication negatives, canonical metadata negatives, fresh actual evidence construction and validator failures retaining saved commit; null envelope exits 2/empty stdout. | Accepted structured failure and delivery barrier. |
| S11 cleanup | FCE-02/07; prior cleanup after cancel/error/terminal controls, fresh construction/validation dual-failure cases and recognized guard cleanup; retained rows/cause/index/stage, safe error precedence. | Accepted owned cleanup attempt and structured cleanup failure. |
| S12 terminal | FCE-02/07; accepted source normal win, simultaneous outcome, turn-limit tie/original/predecessor/publication chain; exact-limit/cancellation precedence controls, matching null-request terminal evidence. | Accepted prior positive capture plus stop precedence. |

**FCE-01–FCE-08 reconciliation:**

| Gate | Independent final reconciliation |
| --- | --- |
| FCE-01 | Preserve accepted pinned C01–C30 source/evidence closure. All 30 current unique machine rows remain source-backed with finite implemented/raw/unreachable/excluded scope and zero-unresolved; source/config identity matches, no new writer/route or weakened guard. |
| FCE-02 | Accepted original/predecessor/both-perspective chain, cursors/prefixes/actor lineage and waiting-side evidence remain unchanged. New finalization fails safely without fabricated evidence or loss of retained commits. |
| FCE-03 | Accepted mirrored privacy/causality evidence and private request eligibility remain; new cause whitelist/stage constants expose no raw private exception data. |
| FCE-04 | Accepted evidence-derived state/raw-only dispositions and representability remain; no extraction, identity or typed-state change. |
| FCE-05 | Accepted reachable request pairs/restoration/no-route proof and rejection rollback remain; S09–S11 now complete the specified failure/resource-delivery boundary. |
| FCE-06 | Accepted actor-only ordinary/bulk publication and coherently rehashed grammar/privacy/origin/outcome controls remain. Fresh exact limits/Revival accounting tests cover changed metadata before stdout. Invalid/null envelopes emit no output; valid prior rows remain eligible. |
| FCE-07 | Accepted source-derived terminal paths remain; S01–S12 now truthfully classify incomplete/error outcomes with terminal precedence. Immutable complete_capture is evidence coverage, not successful cleanup or faithful acceptance. |
| FCE-08 | Recorded accepted macOS profile, matching artifacts/dependencies, reproduced simulator/config/local identity and this independent scoped review complete the final evidence packet. Whole-project/flag/merge decisions are not implied. |

**Separate verdicts:** CE-08B accepted for the pinned v2 S01–S12 stop/incompleteness/error, accounting and cleanup/delivery contract. FCE-08 accepted for the accumulated FCE-01–FCE-08 pinned source/semantic review evidence packet. No material evidence gap remains within those scopes.

**Reused versus fresh evidence:** reuse the three matching artifact-only repair passes (4.124s/3.155s/0.664s), build (1.636s), coverage self-test (4.054s), expected pre-attestation review gate and whitespace pass. Read and verified the prior four-case output log and its packet hash, with six settling passes and accepted 34-case/source/CE-08A positive evidence at their dependency/branch scopes; do not claim those earlier RUN/PUB whole-file passes were rerun after edits. Fresh review inspects the changed code and canonical fixture/negative joins; no new runtime result is claimed. Metadata outside identities remains canonically unchanged or run/envelope-resealed with existing helpers; invalid candidates preserve input/committed evidence and Python exit 2/empty stdout.

**Digest coverage/attestation:** the accepted CE-08A composite implementation review is the baseline, preserving all earlier scoped attestations and historical-prefix identity/parity review. Intervening RUN/PUB taxonomy/cause/index/accounting changes and appended four-case EP were independently inspected in the withheld review; all its implementation findings are now resolved by the inspected repairs and three hash-bound durable artifact-only tests. Newly listed saved predecessor bytes and test helpers are reviewed here, with canonical actor/observation/belief/run/origin joins and no seed/snapshot publication. Remaining deltas are the inspected bounded contract/status/evidence updates. The resulting 118-input digest is attested only for these accumulated pinned scopes plus CE-08B/FCE-08; it is recorded in the manifest outside this covered audit to avoid self-reference. Prior CE-08A and FCE-01 digest fields remain preserved.

**Execution limitations and next boundary:** historical combined short-command timeout (182.032s) remains unresolved; the original long invocation still failed at its insufficient 30s negative budget, superseded only as missing semantic evidence by separately completed outcome/origin controls. Neither original invocation is declared passing. These are command/runtime limitations, not missing semantic acceptance evidence for this packet. No further battle/combined run is demanded. Next requires a separately authorized PIPELINE-002 acceptance/flag decision and dirty-checkout merge-readiness review (intended change scope, unrelated edits, target branch and integration/CI requirements); neither is approved here. faithful_complete_episode:false, dataset/training/live restrictions and prior attestations remain unchanged.


### PIPELINE-002 final capture acceptance / explicit flag decision — 2026-10-09

**Findings (medium, flag compatibility boundary):** runtime flag promotion is not a documentation toggle. PipelineEpisodeResult and its producer require the literal false (pipeline_episode.ts:67/158); both ordinary full-result and shared full/compact Python metadata validators require false (pipeline_record.py:730/779). Recovery/comparison scripts and historical fixtures also assert false. Changing a capability record to true would not make current results claim faithful capture; changing every result to true would incorrectly label truncations, failed cleanup, unbound segments and terminal-only runs and would break publication. No new capture, mechanic, privacy or lineage defect is demonstrated. Recommended follow-up is conditional per-result emission and compatible validation, not a global constant replacement. No runtime or test change is authorized/performed in this decision task.

**Open questions:** none preventing acceptance of the reviewed capture capability. Runtime schema/compatibility details must be made explicit in the bounded follow-up; preserve historical false-valued v1 results and canonical identities.

**Acceptance basis:** entry digest `0f348d3675959a63b4946f411fc3141250a9c684c1c58bb95ca2090c7f62c557` reproduces over all 118 inputs. CE-08A/CE-08B saved evidence and dependency bindings match; prior source/config review pins pokemon-showdown@0.11.10, tree `12d83949635889cd10a51a081890f9dfc6d3ed480eacf2a9a0728fb48e8e086c`, gen9randombattle/gen9 singles random. FCE-01–FCE-08 are accepted and explicitly reconciled in the independent review above; this final decision evaluates the governing PIPELINE-002 criteria, rather than counting scoped milestone labels. No tests, battles, validator workloads or broad runs occurred.

| PIPELINE-002 governing criterion (WORK_ITEMS) | Applicable independently reviewed evidence / verdict |
| --- | --- |
| 1. Per-perspective request states, IDs/phase/cursors | CE-05 request-state classifier/contracts, C24–C26/B26 source routes, CE-06 two-perspective envelope; actor/wait/absent/terminal remain distinct. Accepted. |
| 2. Actual one-sided legal submission and successor lineage | Mirrored accepted forced-switch and bounded bench Revival paths, actor-only canonical actions/records and both successor observations, deterministic restoration. Accepted. |
| 3. Waiting/requestless settling without fabricated defaults | Accepted settling delivery/terminal barriers and B26 supported-format stable requestless/wait-only no-route proof; unsupported request combinations stop. Source proof replaces impossible positive fixtures, not missing progression. Accepted. |
| 4. Atomic rejected/stale/malformed execution | Accepted natural source rejection, saved coherently rehashed grammar/privacy/state/origin/lineage controls, rollback/resource tests and CE-08B retained-boundary finalizer. Accepted. |
| 5. Source regressions for reachable state classes, mirrors and outcomes | Accepted original-request normal win, generated simultaneous outcome, original/predecessor turn-limit tie, both perspectives and restored continuations; constructed guard fixtures kept separate. CE-08A plus S01–S12 covers supported lifecycle/terminal/truncation classes. Accepted. |
| 6. Complete versus truncated collector-facing records | Validated closure origin_coverage/complete_capture and separate status/stop/count/last boundary/cursor, safe diagnostics, no omitted partial chain or waiting-side row; 1,996 current-segment actor rows plus two separately published predecessor rows. Accepted; no collector/data generation authorized. |
| 7. Separate semantic/scope/censoring review | Independent CE-08A positive review, CE-08B S01–S12 and FCE-08 packet review, explicit FCE-01–FCE-08 reconciliation, and this authorized final decision. Accepted. |

Spec AC-001–AC-011 capture obligations map to those accepted contracts and FCE gates: perspective/ownership/knownness (CE-06/C17–C23), hidden-truth/suffix causality (FCE-03), grammar/reachability (FCE-01/C01–C30), rollback/restoration (FCE-05), cross-runtime publication (FCE-06) and explicit unsupported/incomplete outcomes (S01–S12/FCE-07). Future overlay/model/data AC-012/013 are explicitly outside this capture milestone. No unsupported route is promoted and no historical v1, other-format, feature or inference claim follows.

**PIPELINE-002 verdict:** accept the final reviewed pinned v2 capture/boundary-progression capability. Scope is opt-in observable-battle-state/v2, pipeline-episode/v1 control-plane result, pipeline-episode-evidence/v2 validated original/predecessor chain, actor-only existing linked bundle and dataset-record/v1 ordinary/full/bulk publication, under the accepted macOS simulator-record profile. Acceptance is a capability verdict; it does not assert every invocation completed or enable a true per-result flag. No substantive capture-evidence prerequisite remains within this pinned inventory.

**Claim distinctions / flag decision:** faithful_complete_episode is a per-result claim, not an installation-wide capability declaration. Keep its actual runtime value false in every existing result and validator. No true flag is set in a manifest or documentation as a substitute. An eventual true result is eligible only after validated supported v2 original-initial-request coverage, all required both-perspective commits/actor joins and matching terminal evidence, completed status with terminal stop, and successful owned cleanup; it must pass ordinary/full/compact publication semantics. A resumed segment may qualify only with the validated predecessor/original chain; predecessor actor publication remains separately required. Unbound resumed segments, zero-transition terminal-only evidence, v1 views, budgets, cancellation, unsupported/malformed/execution/settling/cleanup failures and invalid/null envelopes remain false. A complete_capture chain retained after cleanup failure remains a truthful coverage fact but cannot authorize a true faithful result. Capability acceptance itself authorizes none of these per-result assertions.

**Exact bounded runtime follow-up:** update the result type/producer and both Python full/shared compact metadata entry points to implement the conditional faithful eligibility rule after final validation and cleanup. Explicitly preserve historical false-valued v1 identity/publication compatibility; choose/document versioning if the result contract requires it. Do not grant standalone terminal observations new authority. Update only affected recovery/comparison consumers and false-flag assertions whose accepted complete-control semantics change. Use canonical saved-artifact positive/negative controls for original-terminal and valid predecessor chains, unbound/terminal-only, cancellation/budget/unsupported/failure/cleanup, legacy v1 and true-flag forgery; verify rejected publication is exit 2/empty stdout and committed evidence unchanged. Sequential exact short checks suffice; no 1,000-turn rerun, broad suite, battle regeneration, hashing work, new mechanic or dataset is required for that follow-up. Its runtime implementation and validation need a separately authorized task/review; they are not performed here.

**Historical limits / handoff:** combined short-command 182.032s timeout remains unresolved; original long invocation remains failed at the former 30s negative limit. Independently completed matching-source outcome/origin controls satisfy semantic evidence; neither original invocation is relabeled passing. Dirty-checkout branch integration/CI and merge-readiness review remain separate: establish intended changes, preserve unrelated work, identify target branch and final-tip validation scope before approval. No staging, commit, merge, training/live or cross-platform claim. Prior scoped attestations remain intact. Resulting documentation-only coverage identity is recorded in the manifest; this decision does not attest any future runtime flag change.


### Conditional faithful-result implementation checkpoint — 2026-10-09

**Scope/compatibility:** candidate implementing the final PIPELINE-002 flag follow-up; no independent acceptance or new capability verdict. The pre-edit eligibility table maps fresh original-to-terminal win/tie and validated predecessor-bound continuation to eligible; unbound segments, terminal-only, incomplete/canceled/budget/unsupported/execution/settling/construction/cleanup failures and legacy v1 to false. False is conservative even when evidence supports true, and never exempts ordinary validation. Result/v1 retains its Boolean field and canonical identities; true additionally requires evidence/v2. No DATA-001 schema or run/observation/belief/transition identity changes.

**Implementation/self-review:** RUN validates complete origin/lineage/both-perspective/terminal evidence, counters and summaries, then each actor using the shared ordinary action/belief/transition/terminal-authority validator before owned cleanup. It emits true only after successful cleanup; failed cleanup retains valid coverage but false fidelity. PUB independently checks full/shared metadata claim eligibility before unchanged ordinary or bulk actor validation and atomic output. Shared actor validation retains joint semantics and adds explicit one-sided schema/request/role validation; waiting sides gain no action or row. Supplied true alone never authorizes publication. Envelope-only validation proves coverage, not result fidelity. Predecessor actor rows retain their separately required publication contract.

**Saved evidence/controls:** hash-pinned accepted predecessor plus a narrow origin/first-commit extraction from the accepted long envelope supplies real bound continuation joins. Terminal suffixes in these short contract tests are constructed controls, not new source-engine witnesses; accepted normal/tie mechanic and complete-chain proofs are reused unchanged. No battle or long sweep ran. Eligible fresh/bound win/tie, conservative false, producer emission, full/bulk publication and cleanup failure controls pass. Ineligible stop/schema/legacy/terminal-only/missing envelope controls and coherently resealed origin/actor/counter negatives reach their exact rules, retain candidate/committed evidence, and reject Python with exit 2/empty stdout.

| Exact short check | Result / outer elapsed |
| --- | --- |
| faithful claim saved win tie and bound continuation publish conservatively or true | 1/1; 2.917s |
| faithful claim ineligible stops segments terminal-only and schemas reject without mutation | 1/1; 2.401s |
| faithful claim coherent origin and actor tampering reaches semantic validators | 1/1; 0.567s |
| CE-08B exact limits regression | 1/1; 4.155s |
| CE-08B exact Revival cause/accounting regression | 1/1; 3.241s |
| CE-08B construction/validation/cleanup first invocation | Python subprocess status null after 30s; outer 30.411s; not semantic rejection |
| Same cleanup diagnostic retry, once | 1/1; all six combinations; 1.644s |
| Build after failure-only payload logger | Passed; 4.752s |

Every check used the accepted macOS Python profile, sequential exact positive selectors and a 180s process-group ceiling; Python subprocesses retain 30s. A failure-only payload/diagnostic persistence branch was added after the transient timeout; successful publication and semantic assertions are unchanged, so earlier passing cases are reused at that branch scope. No timeout was raised or assertion broadened. The single diagnostic retry resolved this execution gap without a production defect. Current hashes/logs/profile and extraction provenance are in `artifacts/validation/faithful-flag-2026-10-09/evidence.json`.

**Current changed source/test/fixture SHA-256:**

- `sim-core/src/pipeline_episode.ts`: `353aac765d4995796818485d254fdbd09416b5c715981f052e0d6f5eb8415fcd`.
- `sim-core/src/pipeline_integration.ts`: `5e509d6dff1500d7a05630772a80f76c0c4f1c34a5f61462757e4b8b04c5fc70`.
- `trainer/src/neural/pipeline_record.py`: `ce9b6e83e526eeff280e2674c5a14c75b1754618f7db8ba6954b98ad6f9794e5`.
- `sim-core/tests/pipeline_episode_faithful.test.ts`: `693c11af6946eb39fc6a9a8bec6c480c1024d81ae83ed851d15b7bc0a026d845`.
- `sim-core/tests/pipeline_episode_saved_helpers.ts`: `9c24cfbefe269096d20f6da419c93651fdde3dd341eb6c3c3f0d2ee17c723ed0`.
- `sim-core/tests/pipeline_episode_stop_repair.test.ts`: `c62098985a9df8fff7291ba8bc4413ea7a27271c9abe3198958846c663e79ebd`.
- `sim-core/tests/pipeline_episode.test.ts`: `bfa0d90b0898c34a263b0d98cd0f5657852c81b07f7f6983b16a505d87ecebbc`.
- `sim-core/scripts/recover-ce08a-adversarial.cjs`: `d58a71b2e1e2cf9599cde14789a35cbfbd1fee28a79fa5752fdc7dd6c0e719e0`.
- `artifacts/validation/faithful-flag-2026-10-09/segment-start.json`: `a468592b1374317504445184242a8438112d381eb18e59931816c3d25b0127c5`.

**Review handoff:** independently review conditional emission, shared actor validation, Python full/compact Boolean and eligibility checks, compatibility and saved-fixture canonical joins. Recovery harness assertion and complete episode expectations now reflect conditional eligible true; no harness or long test was executed. The historical combined 182.032s timeout and original long invocation failure remain unchanged; previously completed separate-source evidence is not relabeled as a successful original invocation. Candidate local digest is refreshed in the manifest; reviewed_sha256 and all prior attestations remain unchanged. No training/live, merge or cross-platform readiness claim.


### Independent conditional faithful-result runtime review — 2026-10-09

**Findings:** no material finding remains within this boundary. Entry candidate `4f3445b129a43dd5f7a3254d155746d827e26ba1fe2102bbb59560cfb3b14696` reproduces over 121 inputs. Nine repair/fixture hashes and all seven saved result-log hashes match the packet. Review inspects finalizer ordering, shared joint/forced/revival actor validation, full/shared Python metadata eligibility and ordinary/bulk atomic output, saved canonical fixture joins and consumer assertions. No tests, battles, long witnesses or performance work ran in review.

**Open questions:** none blocking scoped runtime acceptance. Final-tip integration and merge policy are separate decisions.

| Obligation | Independent inspected disposition |
| --- | --- |
| Original-to-terminal v2 win/tie | Eligibility is recomputed from validated closure, original requests, both perspectives, ordered prefix/cursor/transition chain and matching final terminal evidence. Supplied Boolean/status/outcome/count alone is insufficient. Accepted. |
| Bound continuation | Recursive predecessor validation, same episode/format/source and exact origin/final-boundary joins establish original continuity. Terminal predecessor reuse rejects. Predecessor actor publication remains separately required; no implicit predecessor row is emitted. Accepted. |
| Actor validation / cleanup barrier | Every current actor validates action, observation, belief and transition joins before cleanup. One-sided role/schema/request checks remain explicit. Successful close precedes true assignment; construction/validation/cleanup failure remains false with retained safe evidence. Accepted. |
| Ineligible and historical compatibility | Unbound, terminal-only, legacy v1, incomplete/canceled/budget/unsupported/failed paths cannot authorize true. False is conservative even for an eligible result and never bypasses ordinary validation. Existing result/v1 field compatibility is explicit. Accepted. |
| Independent publication and rehashed negatives | Python independently replays envelope/metadata eligibility and validates actor rows through ordinary/full or bulk paths before any stdout. Canonically resealed origin/coverage, missing actor, invalid counters/schema and ineligible true controls reach their stated rules; candidates and committed evidence remain unchanged; invalid publication exits 2/empty stdout. Accepted. |
| Identities/privacy/scope | No canonical observation/belief/action/transition/run or DATA-001 fields change; flag remains derived metadata outside identity inputs. No foreign/private payload or new terminal authority is authorized. Scope remains pinned pokemon-showdown@0.11.10 Gen9 Random Battle v2 capture and accepted macOS profile, not global readiness. Accepted. |

**Evidence reuse:** six exact short-case passes are reused (three faithful claim cases, limits, Revival and final cleanup), with the recorded branch-scope limit: the helper changed only to persist failure payloads/diagnostics; successful publication and semantic assertions are unchanged. Final build and cleanup retry used the current helper. Initial cleanup log is a failed invocation at 30.411s with Python status null, never a pass; sole diagnostic retry passed all six construction/validation/cleanup combinations in 1.644s. Accepted prior mechanic/complete-chain proofs provide source witnesses; the new short terminal suffixes are constructed contract controls, not generated battle witnesses. No rerun is needed to relabel either invocation.

**Scoped verdict / digest coverage:** accept conditional per-result faithful emission and matching TS/Python validation only within the preceding pinned contract. Prior PIPELINE-002 and FCE/CE scoped verdicts are preserved. Accepted decision digest `2702f6c334e91444b13fa4b3e36e73fb247ccf943431f5839562ddedd8c5e63a` supplies the previously independently reviewed baseline; intervening runtime deltas are the inspected finalizer/shared actor/Python Boolean checks, extracted saved helpers and boundary fixture, new focused controls, necessary consumer expectations and bounded contract/status updates. No identity algorithm, new mechanic or unpublished production optimization is included. The resulting reproducible 121-input digest, including this record and aligned current status, is attested in the manifest outside covered documents to avoid self-reference; prior attestations remain intact.

**Residual limitations / merge handoff:** historical combined short-command 182.032s timeout and original long invocation failure remain documented; matching-source separately completed evidence does not make those invocations pass. No new runtime blocker is identified. Merge readiness still requires identifying the intended dirty-worktree changes versus unrelated edits, target branch, final-tip integration/CI validation scope and separate merge approval. No stage/commit/merge, dataset/training/live or cross-platform readiness claim.
