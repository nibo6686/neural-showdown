# Prompt49 — owned-request health adapter design

**Scope:** proposed TS-private 0.11.11 health-only adapter; no execution/adoption. Retain identical Prompt48 starting/source objects, incomplete result and action authority. Current moves/PP, ability/item/species and public-current adapters remain blocking unknowns.

## Source and first property matrix

Pinned native `Side.getRequestData` (`sim/side.ts:357`) calls each actual Pokémon’s `getSwitchRequestData` (`sim/pokemon.ts:1159`), which emits `condition=getHealth().secret` (`:2065`). Inspect exact owned `side.pokemon[].condition`, not public percentage HP. Subjects are `owner:roster:originalSlot` from authenticated object references, never request indices/ident/species.

| Selector; family | Finite meaning, state/precision |
|---|---|
| current.hp; K05 | Positive `n/max`→integer n; exact `0 fnt`→0. Known/exact. Validate ASCII integers, 0<n≤max, finite bounds. |
| current.fainted; K05 | `0 fnt`→true; positive condition→false, known/exact; require settled native faint flag corroboration. |
| current.status; K05 | Positive condition plus exactly one supported `brn/par/slp/frz/psn/tox`→known text/exact; positive condition with no status→known_absent/null/not_applicable. `0 fnt` omits status: unknown/not_emitted, never absence. |

All other shapes reject the adapted candidate, with fixed payload-free errors. No healing/injury/status-duration inference. HP maximum only validates the request ratio; do not emit hp_max because fainted requests omit it. No value comes from originals. Native fields corroborate freshness, never fill omitted request values.

`getMoveRequestData/getMoves` (`pokemon.ts:970,1089`) can substitute Recharge/locked move/Struggle, omit PP, expose restricted disabled/trap information and use transformed move slots. `side.moves/baseAbility` differ from active choices/effective originals. Therefore no current_moves, PP/maxPP, trap/disabled, legality or request-action descriptor in this slice.

## Required private seam and actual caller map

Existing FIFO trace authenticates producer→owner receipt; ledger authenticates delivery/parent/cutoff, but neither identifies request rows. B2 public `original_slots` and B3 primitive histories are insufficient. **Approval prerequisite:** dedicated finite request-health transfer in B1/B2; do not reuse/fan out occupied switch-actor receivers.

Proposed `OwnedRequestHealthHost`, registered once by the session before generation, captures writer return references with exact environment/battle/Pokémon/owner and immutable condition fields. Initial attachment requires no own getRequests override and exact equality to the pinned Battle.prototype.getRequests function/descriptor and wraps the actual battle.getRequests through B1.observe, before player writes; it installs Side/Pokémon writer hooks before calling the original getRequests. Waiting/direct getRequestData and subsequent emitRequest use those same instance hooks. Restore descriptors synchronously on retirement/failure/close.

B1/B2 provide separate controller-owned request-health enrollment via exact original-holder/object rows, checked environment/battle and restore ticket/parent. Writer captures may precede activation; no usable source until both-owner enrollment and existing activation checks succeed. Each row return joins the actual Side.getRequestData return and Side.emitRequest argument, then the exact Battle.send sideupdate occurrence→RequestEmissionTrace receipt. Require unique complete owned row coverage; copied/replaced entries have no enrollment. Array position transports an already-proven reference association, never establishes identity.

Add ledger-private `prepareHealthTransfer(deliveryToken, writerToken, owner)` validating exact selected receipt/current delivery, ledger issuer, environment, boundary and parent. Tokens are held only internally; no raw/object mapping admission API. Foreign/copied tokens or contradictory captured values reject preparation. A genuinely unsupported route without a transfer yields blocking unknowns, preserving ordinary session/action behavior. `NativeOwnerKnowledgeController.prepare` receives these prepared capabilities; preflight repeats source/subject/freshness joins before the existing synchronous install barrier. Actual callsites: native writer→env stream/ManagedPlayer receipt→ledger.prepare→health transfer→knowledge.prepare/preflight→session install→existing addressed paired read. No post-install callback or fallible work.

## Variants, freshness and continuity

Support singles move, forced-switch, Revival selection and waiting requests carrying authentic owned side rows. Revival target rows bind their actual objects, not the selecting actor. Waiting retains health knowledge without action authority. Team preview/ally/doubles/non-direct writer paths remain unsupported.

`updatedRequest` mutates/re-emits activeRequest (`side.ts:521`); require original row-reference provenance plus a new emission/receipt occurrence. Before installation, compare captured health tuple against the same authoritative live objects at the settled boundary using pure field checks; any intervening health/status/faint change prevents fresh facts. Do not regenerate request data to rescue stale rows.

Restore prerequisite: State.deserializeBattle (`state.ts:133–146`) regenerates requests inside fromJSON. **Explicit approval:** temporary `Battle.prototype.getRequests` interception around one synchronous B2-ticketed fromJSON, excluding probes. Require pinned function/descriptor before interception; captured battle has no own getRequests override. Require no active/nested interception, exactly one candidate occurrence, and captured `this` identical to the returned battle. Install instance captures tentatively; restore the prototype descriptor exactly in finally. Only subsequent B2.acceptRestore with exact ticket/parent/serialization promotes bindings. Zero/multiple/nested/foreign/copied/post-finally captures reject and revoke; nothing is readable before promotion. Without approval, restored health stays unknown/unsupported_writer; no post-accept regeneration.

Cloned active-request overlays need separately held selected-emission row-to-slot lineage at accepted serialization, exact overlay occurrence/parent, fresh B2 objects and new receipt/ledger join. Base fromJSON capture cannot authorize an overlay. Existing overlay validation preserves side rows; equal bytes cannot establish lineage.

Equal-byte native deliveries retain distinct occurrence/sequence. Known facts use current freshness and committed prefix cursor as observed_at; private proof retains writer/delivery occurrence and settled corroboration. Terminal/null means no current health evidence: replace selected facts with blocking unknowns. Terminal/requestless/wait classification comes from accepted boundary+ledger selection, not missing JSON. Never carry old facts as fresh; earlier paired reads remain immutable.

## Compatibility, files and approval

Propose additive fixed `perspective-knowledge-native11-owner-health-v1/` schema/profile; retain Prompt48 assets and starting rules. Keep request:null explicitly descriptor-unadopted. Binding adds `request_adaptation: owned_health/v1`, `request_descriptor: not_adopted` and `request_state: move|forced_switch|revival_selection|waiting|terminal|requestless|unsupported`. Native health revision is selected by reviewed internal policy; old v1 reads remain inert v1, with no silent profile reinterpretation. These are private compatibility changes requiring lead approval; no historical/wire edits. Unknown unbound rows remain blocking unsupported_writer; terminal/requestless rows become blocking not_emitted. No permissive aggregate acceptance follows either.

Future files: new host/test; narrow crosswalk, env, trace/ledger, knowledge checker/controller and session wiring. Both owners prepare atomically; failure discards before cleanup, preserves committed handles; retry fresh; advance stales old handles; close revokes. Expose only inseparable own projection/binding, no raw request/opponent/native/source/proof payload or RPC.

## Future acceptance and next action

Exact integrated both-owner provider→writer→receipt→delivery→consumer; updates and equal-byte fresh delivery; reorder/held restore with literal expected slots; forced-switch/Revival/wait/terminal; copied/foreign/wrong-owner/altered value/subject/overlay negatives; final-preflight rollback/retry; suffix/starting-reference immutability and ordinary-output byte/privacy parity. Constructed mechanics labeled separately. Reuse accepted infrastructure checks; no Cartesian/full audit.

Commands: read-only cat/sed/rg; no imports/tests/builds/battles. Inspected Prompt48 acceptance, request/perspective contracts, fixed profile and named native/controller callers. Approve health slice, dedicated transfer and fixed private profile revision before implementation. Independent static review (Slowking): ACCEPT after incorporating exact initial/restore hook timing, prototype authorization and unbound fallback; no reviewer execution.
