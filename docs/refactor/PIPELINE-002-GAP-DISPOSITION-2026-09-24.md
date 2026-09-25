# PIPELINE-002 gap disposition — 2026-09-24

## Current checkpoint — Stellar typing implemented; review pending (2026-09-25)

Prior lifecycle/Illusion/non-Stellar Tera and faint/minimal-v1 restoration acceptances
stand. Stellar defensive typing correction awaits separate semantic/digest review.
`faithful_complete_episode:false` remains mandatory.

### Source findings / decisions

- Pinned `sim/pokemon.ts:2053-2060` substitutes the Tera type only when active and
  not Stellar, otherwise using ordinary types and Type-event semantics.
  `sim/battle-actions.ts:1921-1934` still emits the public Tera event and sets
  the Tera flag. Stellar does not become a replacement defensive type.
- `battle_helpers.ts:resolveTypes` now excludes Stellar from its replacement branch.
  Shared extractor callers cover own-request projection, public activation/reveal,
  switch/drag details, faint and replay. Known Tera type and active flag are unchanged.
  Before Illusion reveal, own Fox is Dark but opponent displayed Snorlax is Normal;
  reveal resolves public typing to Dark. Neither view uses Stellar as a defense type.
- Existing projection privacy remains: opponent `tera_type` is omitted, with public
  Stellar evidence retained in the exact protocol prefix. Faint deactivates the flag
  while preserving known type. No observation, transition or metadata schema change;
  corrected observations naturally produce corrected content-derived identities.
- Scope is ordinary species/Illusion defensive typing. `getTypes` also consults
  temporary types/Type events; this slice does not reconstruct those broader effects
  or private Stellar offensive counters. Do not infer full Stellar-mechanics fidelity.

### Exact changed files / hashes

- `sim-core/src/battle_helpers.ts`: `6a79251137efa04c18150a5a0512756c23e33877224ae46c58624facbc37f994`.
- `sim-core/tests/helpers/state_lifecycle.ts`: `d4f44d6ed5f35a406950af0f9b11c9ff172b1b23dec190eb7ead8ab144bf1e70`.
- `sim-core/tests/illusion.test.ts`: `2af13415a40133e0889015f386d48a272feb264626840c86124c33a2c8736463`.

### Validation / evidence

- Parent build and **146 relevant TypeScript tests pass** (136 prior + ten new
  Stellar/source cases): `/tmp/neural-stellar-{build,validation}.log`.
  Focused Illusion suite passes **28 tests**. Prior20 Python tests reused;
  new Stellar records are validated through Python in the mirrored pipeline tests.
- Both actors: direct pinned `Pokemon.getTypes()` source assertion; Stellar
  activation, switch and Whirlwind drag re-entry, revealed/unrevealed Illusion,
  ordinary terminal and unrevealed Explosion faint, both perspectives and unchanged
  teammate state. Live/restored equality, immutable earlier observations/exact prefixes,
  repeatable records/beliefs and Python publication pass. Fire cases remain green.
- Parent independently inspected helper and tests. Diff checks pass. Delegation
  requested gpt-5.6-terra/high; effective-setting metadata is unavailable.

### Review requirements / next action

**Single next task:** semantic review of ordinary Stellar defensive typing and
lifecycle/privacy/restoration/publication interactions. Verify scope against pinned
getTypes; preserve explicit limitations for temporary-type effects and offensive state.
**Add `src/battle_helpers.ts` to hashed coverage before attesting**: it is absent
from the current24-file list. Shared fixture helper and Illusion tests are already
listed. Manifest/classifications/attestation remain untouched.

Current listed digest (not including battle_helpers):
`f0893ed149ee786be29a8a3a03f3ae820a62dce0d5611637573e4095cd6bef1b`.
Prior reviewed digest:
`6aaddf2751640263f13fa29d4e95c1bfb0987bbf78e7274493a30b8126273c70`.
Coverage checker/self-test commands exit1 on digest drift; six synthetic self-tests
pass: `/tmp/neural-stellar-{coverage,self-test}.log`. Recompute after adding the helper;
a digest update alone is not semantic acceptance.
Temporary forms/types/abilities, linked effects, wider transfers, Revival Blessing
and field/layer/expiry fidelity remain separate prerequisites. Constructed fixtures
in the pinned Gen9 engine do not establish faithful complete-episode publication.

## Findings / disposition

| Scenario | Simulator/request already provides | Pipeline gap and disposition | Smallest change; acceptance check |
| --- | --- | --- | --- |
| KO replacement; U-turn; chained entry-hazard KOs | `forceSwitch` for the chooser, `wait:true` for the other; saved action queue resumes after the required switch | **Accepted slice:** ordinary one-sided version; no complete-episode acceptance | Real KO/pivot regressions verify actor-only records, both beliefs, identity and rollback. Chained-hazard and complete-episode acceptance remain open. |
| Forced-switch-plus-wait versus actionable-plus-absent | Separate private requests; tracker retains wait data | **Accepted reporting slice:** opt-in reporting retains wait; independent classifier distinguishes states | Real switch/restore tests preserve waits and consumed-request absence. |
| During startup/resolution neither player has a request; one submitted choice awaits the other | Engine resolves automatically, emits side updates/public output/new requests or termination | **Settling accepted:** complete-delivery barrier and bounded failure/rollback; bounded runner outcomes accepted | Complete delivery and atomic failure verified. General requestless transitions remain unsupported; no fabricated pass. |
| Pawmot/Rabsca uses Revival Blessing after an ally faints | `forceSwitch`, active roster member’s `reviving:true`; `switch N` must name a fainted teammate | **Unsupported:** runner truncates revival; normalization drops reviving and builder selects incorrect targets | Preserve addressed request flag; enumerate fainted eligible slots with canonical round-trip semantics. Real revival accepts fainted targets, rejects healthy ones and resumes; verify both perspectives/Python publication. |
| Hidden Arena Trap rejects switching; visible trap ends | Request gives trapped/maybeTrapped evidence; rejection may refresh trapped flag; later requests govern switching | **Runner accepted:** candidate rollback retained; bounded request-derived reselection excludes attempted tuples | Natural Arena Trap retry selects valid moves; cap/budget exhaustion truncates. Verified accounting and current-request selection; no snapshot-derived masks. |
| Switch/drag/faint/re-entry; Shed Tail transfer | Simulator clears switch/faint state; public switch/faint/move evidence identifies lifecycle; Shed Tail copies Substitute | **Scoped acceptance:** clearing/Shed Tail, Illusion and non-Stellar public Tera re-entry | Faint/restoration accepted; ordinary Stellar typing implemented pending review. Broader fields/linked effects open. |
| Confusion expires; Protect ends; screens/hazards/weather change | Public start/end/field records plus private effect timers; current requests remain action authority | **Deferred reconstruction/features:** confusion start/end works; single-turn is raw-only; side layers/durations and sources are incomplete | Preserve exact supported records and explicit limitations. Before adding typed features, test expiry, layer caps/removal and field replacement per chosen effect; never encode missing/private duration as zero. |
| Win/tie, budget expiry, unsupported protocol or stall | Public win/tie and terminal views; wrapper errors/log cursors | **Runner accepted:** explicit completed/truncated/failed outcomes retain committed lineage | Verified outcome reasons, budgets, final boundary and failure accounting. Terminal execution alone does not establish faithful typed-state publication. |
| Unknown aliases; doubles/other-generation mechanics | Alias guards already stop publication; package includes broader emitters | **Conditional stop / outside scope:** unknown emitted aliases need classification; other formats are excluded | Retain atomic stop and truncation evidence. No blanket grammar expansion or cross-format acceptance. |
