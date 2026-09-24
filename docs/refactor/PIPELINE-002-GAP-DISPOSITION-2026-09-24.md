# PIPELINE-002 gap disposition — 2026-09-24

## Current checkpoint — faint/restoration slice accepted and attested

Combined scoped acceptance: non-Stellar faint correction and minimal-v1 terminal
restoration/validation. Prior lifecycle/Illusion/re-entry acceptance stands.
`faithful_complete_episode:false` remains; broader fidelity is a separate gate.

### Decisions / source findings

- Minimal `terminal-request-history/v1` retains only owner-roster inputs consumed by
  `selfFromRequest`: identity/details/condition, active, moves/stats, item/abilities
  and Tera fields. Raw-v1 extras are dropped; legacy Tera strings become booleans.
  Outer schemas are unchanged; missing-history legacy snapshots cannot recover
  absent private owner history. Exact field contract: `docs/contracts/SEEDED_TRANSITION.md`.
- Recursive validation completes before teardown: addressed identities, dense arrays,
  roster invariants, typed fields, HP/status/species syntax and exact safe numeric
  stats. Valid shiny details and active-but-fainted forced-switch rows remain valid.
- `TerminalRequestHistoryValidationError` exposes structural `code`, `path`, `reason`
  without private values. Codes: `terminal-request-history/invalid` and
  `terminal-request-history/unsupported-schema`. Scope is metadata validation,
  not arbitrary corruption of simulator JSON.
- Pinned faint semantics deactivate Tera, retain known type and restore observable
  non-Tera typing; own projection overrides stale request flags. Unrevealed Illusion
  stays private. Restored history creates no actions or public raw metadata.

### Exact review scope / hashes

Review scope below. Production unchanged during review; only independent-run
timestamp comparison in Illusion tests was corrected:

- `sim-core/src/env_manager.ts`: `c597e1215997705fa9dae942c71aab77adced6b0602ce55cc0006e7ed322e930`.
- `sim-core/tests/illusion.test.ts`: `d73eb6530482cb6ad54154df976a08cc381d77abf4ce07f034463c9a7a830431`.
- `sim-core/src/state_extractor.ts`: `3e15bf37284a8dd74b7d24c04ff19aa70d4ab5634ad62db537e17492a900b040`.
- `sim-core/tests/helpers/state_lifecycle.ts`: `6018886cdbeb9d45c13ee2d292c978af928abf25bd554af526af3a33ff18ace6`.

### Review evidence / attestation

- All four incoming hashes matched. Reused build/136 relevant TS/prior20 Python
  evidence and unchanged faint semantics. Fresh build and **18 Illusion tests**,
  including Python publication checks, pass; three coverage regressions pass.
  Logs: `/tmp/neural-history-final-review-{build,tests,manifest-tests}.log`.
- Independent run exposed a timestamp-only flaky comparator. It now normalizes
  `|t:|<integer>` for independent-run comparisons per the existing identity contract;
  per-run exact-prefix checks stay unchanged. No production correction required.
- Original malformed cases and nested live-battle tests verify structured errors
  before teardown, unchanged serialized state/fingerprint/branch, and subsequent
  execution matching an untouched twin. Valid terminal observations and privacy hold.
- Lineage probe `/tmp/neural-history-lineage-review.{cjs,log}` verifies equivalent
  raw-v1 migration, no requests, changed legacy fingerprint/branch, rejection of old
  references paired with normalized state, and stable canonical second round trips.
  **Recapture references after migration; never rewrite historical references or
  records to claim the migrated state had the old identity.** Terminal import is not
  continuation under the old fingerprint. Missing-history legacy limits remain.
- All four files were already in the 24-file coverage list. Updated attestation and
  removed the resolved faint-Tera gap; no inclusion change needed. Reviewed digest:
  `6aaddf2751640263f13fa29d4e95c1bfb0987bbf78e7274493a30b8126273c70`.
  Coverage checker and six self-tests pass:
  `/tmp/neural-history-final-review-{coverage,self-test}.log`. Diff checks pass.
  Independent review agrees; requested gpt-5.6-terra/high effective metadata unavailable.

### Single next prerequisite

**Correct Stellar defensive typing** in `sim-core/src/battle_helpers.ts:resolveTypes`.
Pinned `sim/pokemon.ts:getTypes` only substitutes the Tera type when it is not
Stellar; current resolver returns `['Stellar']`. Preserve legitimate public species/
type evidence and Illusion uncertainty. Add real mirrored Stellar activation,
switch/re-entry/faint and reveal/restoration tests in lifecycle/Illusion regressions,
with deterministic Python-validated publication. Do not expand to Stellar damage
boost counters or private state. Separate semantic/digest review follows.
Temporary forms/types/abilities, linked effects, wider transfers, Revival Blessing
and field/layer/expiry fidelity remain additional prerequisites.

## Findings / disposition

| Scenario | Simulator/request already provides | Pipeline gap and disposition | Smallest change; acceptance check |
| --- | --- | --- | --- |
| KO replacement; U-turn; chained entry-hazard KOs | `forceSwitch` for the chooser, `wait:true` for the other; saved action queue resumes after the required switch | **Accepted slice:** ordinary one-sided version; no complete-episode acceptance | Real KO/pivot regressions verify actor-only records, both beliefs, identity and rollback. Chained-hazard and complete-episode acceptance remain open. |
| Forced-switch-plus-wait versus actionable-plus-absent | Separate private requests; tracker retains wait data | **Accepted reporting slice:** opt-in reporting retains wait; independent classifier distinguishes states | Real switch/restore tests preserve waits and consumed-request absence. |
| During startup/resolution neither player has a request; one submitted choice awaits the other | Engine resolves automatically, emits side updates/public output/new requests or termination | **Settling accepted:** complete-delivery barrier and bounded failure/rollback; bounded runner outcomes accepted | Complete delivery and atomic failure verified. General requestless transitions remain unsupported; no fabricated pass. |
| Pawmot/Rabsca uses Revival Blessing after an ally faints | `forceSwitch`, active roster member’s `reviving:true`; `switch N` must name a fainted teammate | **Unsupported:** runner truncates revival; normalization drops reviving and builder selects incorrect targets | Preserve addressed request flag; enumerate fainted eligible slots with canonical round-trip semantics. Real revival accepts fainted targets, rejects healthy ones and resumes; verify both perspectives/Python publication. |
| Hidden Arena Trap rejects switching; visible trap ends | Request gives trapped/maybeTrapped evidence; rejection may refresh trapped flag; later requests govern switching | **Runner accepted:** candidate rollback retained; bounded request-derived reselection excludes attempted tuples | Natural Arena Trap retry selects valid moves; cap/budget exhaustion truncates. Verified accounting and current-request selection; no snapshot-derived masks. |
| Switch/drag/faint/re-entry; Shed Tail transfer | Simulator clears switch/faint state; public switch/faint/move evidence identifies lifecycle; Shed Tail copies Substitute | **Scoped acceptance:** clearing/Shed Tail, Illusion and non-Stellar public Tera re-entry | Faint and minimal-v1 restoration accepted; Stellar typing next, broader fields/linked effects open. |
| Confusion expires; Protect ends; screens/hazards/weather change | Public start/end/field records plus private effect timers; current requests remain action authority | **Deferred reconstruction/features:** confusion start/end works; single-turn is raw-only; side layers/durations and sources are incomplete | Preserve exact supported records and explicit limitations. Before adding typed features, test expiry, layer caps/removal and field replacement per chosen effect; never encode missing/private duration as zero. |
| Win/tie, budget expiry, unsupported protocol or stall | Public win/tie and terminal views; wrapper errors/log cursors | **Runner accepted:** explicit completed/truncated/failed outcomes retain committed lineage | Verified outcome reasons, budgets, final boundary and failure accounting. Terminal execution alone does not establish faithful typed-state publication. |
| Unknown aliases; doubles/other-generation mechanics | Alias guards already stop publication; package includes broader emitters | **Conditional stop / outside scope:** unknown emitted aliases need classification; other formats are excluded | Retain atomic stop and truncation evidence. No blanket grammar expansion or cross-format acceptance. |
