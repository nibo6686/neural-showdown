# Prompt44 — private direct-switch association

**Proposed; design only.** Target: retained npm 0.11.11 candidate. Prompt43 authorizes preparation, not implementation. Original checkout, wire/identity bytes, historical evidence, quarantine and fidelity=false remain protected.

## Source/caller map and scope

`initializeStreams` installs the host before input. Attach hooks after `>start` constructs Battle, before either `>player`. `Battle.start()` runs inside the second setPlayer. First switchIn resolves staged B1 after both sides/Pokémon exist, before BeforeSwitchIn. Restore uses B2 `beforeRestore→acceptRestore`, then `restart→sendUpdates` with `sentLogPos=0`: historical log re-emission is real, not a new switch.

Pinned `BattleActions.switchIn` (`battle-actions.ts:64,143–149`) passes the actual Pokémon and its `getFullDetails` callback into `Battle.add`. First scope: `isDrag=false`, no sourceEffect, exact direct switch signature. BeforeSwitchIn side effects, callbacks, names and party positions supply no identity authority. Drag, tagged pivots, replace, Transform, arbitrary add calls and replay stay unbound.

`Battle.add/addSplit` (`battle.ts:3080–3112`) recursively append marker/secret/shared rows. `addMove/attrLastMove/retargetLastMove` (`3115–3142`) append, replace and splice. `sendUpdates` (`3264–3271`) sends a slice before advancing sentLogPos. BattleStream joins that slice and `getPlayerStreams` routes it positionally (`battle-stream.ts:75–83,432–445`); spectator ingress validates before append. Projector validates before filtering framing/tier and normalizing timestamps. Prompt26 indices remain historical.

## Private API and actor authority

Propose `SwitchEventLedger`, held only by the session. All tokens are empty frozen objects registered in private maps; copies, foreign controllers/worlds, wrong-owner reads and revoked leases reject.

| Internal seam | Contract |
|---|---|
| `openBirth(env,battle,birth)` | After both owners are staged/constructed, consume trusted B1 object-reference rows; retain independently held originals and object→original-slot associations privately. No public holding input. |
| `openRestored(env,battle,b2,ticket,parent)` | B2 internally transfers its validated pending object rows after acceptRestore, bound to actual world/ticket/parent. No caller mapping or snapshot-values reconstruction. |
| `attach(env,battle,provider)` | Install before players with no actor authority; first switchIn obtains staged B1 lease before BeforeSwitchIn. Restored hooks attach after B2 validation, before restart. Match actor by reference in that lease’s map. Positions only validate supported singles shape. |
| `received(worldLease,stream,chunk)` | Registered spectator stream consumes sealed send frames FIFO. Bytes/counts corroborate actual ordered transport, never select identity by equality. |
| `prepare(env,parent,next,outputSnapshot)` / `commit(token)` | Validate both-owner routing, normalized cutoff and snapshot lineage; install detached histories only during synchronous session swap. |
| `discard(env)` / `revoke()` | Synchronously invalidate candidate/event/lease/preparation access before awaited cleanup. |

The private provider is session-bound; creation actor transfer waits for both constructed reference arrays. Pending restore transfer is unavailable before final-input/fresh-object checks. Session/controller references authenticate transfers; packed bytes, current positions, requests/rqid, public `original_slots`, labels/species and lengths/hashes cannot mint a lease.

Threat boundary: authentic pinned producer/controller execution, private session ownership and checked endpoints; not a sandbox against privileged native-method monkeypatching. An arbitrary caller possessing a native object still cannot create a signed switch outside the scoped producer frame.

## Durable rows, sends and restoration

Use a per-world tracked log **Proxy**, with private row-token/version vectors. Intercept actual push/splice and indexed writes/deletes/length operations; known splice shifts preserve surviving row tokens, removed rows tombstone. Lengths cannot supply identity. Unknown operations/array replacement invalidate dependent proof. Non-switch annotations update versions; rewriting/removing a pending switch leaf rejects its association. Nested addSplit leaves belong to one writer occurrence, not extra events.

At actual `send('update',slice)`, seal a fresh send token, exact ordered row-token/version slice and copied bytes. Corroborate the ensuing pushMessage within that call scope. Track positional split selection: public gets shared leaf, private leaf never gets a public index. Filtered/empty rows map to null. FIFO receipt plus registered stream binds the exact send occurrence; identical strings at later sends remain different occurrences.

Proxy never enters snapshots: immediately replace only returned serialized log values with a plain copy, before any clone/builder; preserve bytes and native set references. Privately bind snapshot occurrence to observed row lineage through the known serializer/clone/builder calls. Restored historical rows inherit this held lineage via B2 ticket; historical re-emission corroborates the parent and mints no new writer event. Fresh restored switch actors use fresh-world leases. No persisted metadata or portable reconstruction.

Produce a private positional map alongside the existing projector’s shared validation/filtering logic; public API still returns identical strings. Join admitted spectator indices to normalized indices, never by find/indexOf/equal-text search. Preparation requires exact parent history, complete in-scope switch receipts and indices below the committed event_cursor. Unavailable hooks prevent usable dependent authority; ordinary validators remain mandatory.

## Lifetime, reads and future boundary

Owner-scoped `getSwitchEventHolding/readSwitchEventHolding` return only immutable original-slot/event/public-index/prefix-index/branch/step metadata—no actor/set/request/seed/world/snapshot or opposing originals. No RPC, JSON field, catalog/K capability or public resolver. Earlier committed histories are immutable; historical handles cannot authorize new bindings. Successful append preserves prior entries; retirement detaches old world hooks without revoking copied committed evidence. Close revokes all reads. Rejection retains exact prior handles/history, discards tentative events synchronously and permits fresh retry. Post-send mutations never rewrite committed associations.

Future files: new `sim-core/src/owner_identity_events.ts` and one exact test; narrow private-transfer additions in `owner_identity_crosswalk.ts`; hook/serialization/spectator wiring in `env_manager.ts`; private projector map and session prepare/swap/discard/read wiring in `pipeline_integration.ts`. No native package, schemas, Prompt21/24/25 receipts or Python edits.

## Future acceptance matrix

| Combined exact case | Required independent oracle / rejection |
|---|---|
| Genuine creation + two restored reentries, both owners | Literal original slots, exact actor/set transfer, fresh worlds, held snapshot lineage, split secret/shared indices and distinct equal-text occurrences. Old numeric indices are not expected values. |
| Routing/filter/cutoff + mutations | Literal independent positions; tier/framing null and time normalization; unrelated move splice shifts preserve tokens; switch rewrite/removal, untracked replacement, missing/duplicate receipt, future event and foreign equal prefix deny association. Serialization/ordinary output bytes unchanged. |
| Capability/parent privacy | Copied/foreign/wrong-owner actor lease/history, wrong world/ticket/parent reject; no native/private metadata in observables, bundles, snapshots or diagnostics through creation/restore/commit/close. |
| Actual post-capture/precommit fault + retry | Both exact committed histories/handles unchanged; captured/prepared candidate tokens revoked before cleanup; fresh retry obtains its own writer/send/routing chain. No model-only substitute. |

Approval prerequisites: private transfer and Proxy/plain-log edge. All fallible B2, delivery, event and session checks must precede synchronous no-fail installs; otherwise stop. No identity/schema redesign authorized. Independent review (Slowking): ACCEPT after correcting command-start versus Battle.start timing; atomicity remains mandatory. Source/document reads only; no tests, builds, imports, battles or production edits. Return for lead acceptance.
