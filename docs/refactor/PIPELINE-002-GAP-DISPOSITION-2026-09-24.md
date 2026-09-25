# PIPELINE-002 gap disposition — 2026-09-24

## Current checkpoint — ordinary Stellar defensive typing accepted (2026-09-25)

**Verdict:** scoped acceptance; no blocking findings or production corrections.
Prior lifecycle, Illusion, non-Stellar Tera and faint/minimal-v1 restoration
acceptances stand. `faithful_complete_episode:false` remains mandatory.

### Source findings / scope

- Pinned `sim/pokemon.ts:2053-2060` replaces defensive types only for active
  non-Stellar Tera. Stellar retains ordinary types, with Type-event semantics.
  `sim/battle-actions.ts:1921-1934` still emits activation and sets the Tera flag.
- Reviewed every `resolveTypes` caller in the extractor and heuristic. Own-request,
  activation, switch/drag, reveal, faint and replay paths keep known Tera type,
  active Terastallization and defensive typing distinct. Heuristic defensive
  fallbacks benefit; its offensive/STAB approximation is not Stellar-mechanics acceptance.
- Before reveal, owner Fox is Dark and opponent displayed Snorlax is Normal;
  reveal resolves public typing to Dark. Opponent private `tera_type` remains omitted;
  public Stellar evidence stays in the exact protocol prefix. Faint deactivates
  Terastallization but retains known type. Earlier prefixes and teammate state stay unchanged.
- No schema change. Corrected observations naturally change content-derived identity.
  Temporary types/Type events, forms/abilities, linked effects, wider transfers,
  Revival Blessing, field/layer/expiry fidelity and private offensive counters remain
  outside this acceptance. Constructed-team Gen9 evidence does not expand formats.

### Reviewed implementation hashes (SHA-256)

- `sim-core/src/battle_helpers.ts`: `6a79251137efa04c18150a5a0512756c23e33877224ae46c58624facbc37f994`.
- `sim-core/tests/helpers/state_lifecycle.ts`: `d4f44d6ed5f35a406950af0f9b11c9ff172b1b23dec190eb7ead8ab144bf1e70`.
- `sim-core/tests/illusion.test.ts`: `2af13415a40133e0889015f386d48a272feb264626840c86124c33a2c8736463`.

### Validation / attestation

All three hashes matched. Reused passing build,146 relevant TypeScript tests,
28 Illusion tests and prior20 Python checks. Mirrored cases verify activation,
switch/Whirlwind drag, reveal, ordinary/unrevealed faint, privacy, immutable prefixes,
restoration and repeatable Python-validated publication; Fire stays compatible.
Fresh independent review passed build and16 targeted Tera lifecycle tests.
Requested reviewer gpt-5.6-terra/high; effective settings were not exposed.

Added `src/battle_helpers.ts` to the coverage list (25 files). Fixture helper and
Illusion/Tera regressions were already included; no token classifications changed.
Computed/reviewed local digest: `4db82b9bc57984bf051f03b201bf022e0744ba03c8840239adeded5d362f33c3`.
Pinned simulator digest unchanged:
`95cc2b31a17340cf376739ad8f02570cd847e6647da2a0760f8623aef75290fe`.
Coverage checker, six synthetic drift self-tests and three coverage tests pass;
logs: `/tmp/neural-stellar-review-{coverage,self-test,manifest-tests}.log`.

### Next action / Windows handoff

**Single next task:** separate Windows ENV-001 environment validation of this
reviewed state. Base commit `3ddc5fc3060e8da287425e4d08a71a2ffd77184a`
on `refactor/state-001-observable-state` contains the implementation; working tree
was clean before review changes. Apply the review-only patch supplied with this
handoff, or transfer its exact manifest/documentation changes. Verify the25-file
local digest and pinned simulator digest above before comparing results.
Review changes: coverage manifest, this checkpoint, WORK_ITEMS, PROJECT_STATUS and
append-only codex_review_state. No implementation files changed during review.

Follow `ENVIRONMENT_VALIDATION.md`: record Windows/Python/Node/npm versions,
dependency resolution and commands; build, relevant simulator/coverage and Python
record/lineage checks. Obtain fresh Windows evidence; macOS evidence is not a Windows
pass. Report line-ending or platform differences without silently re-attesting altered
source. ENV-001 dependency/runtime policy and clean-environment gates remain unresolved.
Broader lifecycle completeness remains a separate faithful-publication prerequisite.

## Findings / disposition

| Scenario | Simulator/request already provides | Pipeline gap and disposition | Smallest change; acceptance check |
| --- | --- | --- | --- |
| KO replacement; U-turn; chained entry-hazard KOs | `forceSwitch` for the chooser, `wait:true` for the other; saved action queue resumes after the required switch | **Accepted slice:** ordinary one-sided version; no complete-episode acceptance | Real KO/pivot regressions verify actor-only records, both beliefs, identity and rollback. Chained-hazard and complete-episode acceptance remain open. |
| Forced-switch-plus-wait versus actionable-plus-absent | Separate private requests; tracker retains wait data | **Accepted reporting slice:** opt-in reporting retains wait; independent classifier distinguishes states | Real switch/restore tests preserve waits and consumed-request absence. |
| During startup/resolution neither player has a request; one submitted choice awaits the other | Engine resolves automatically, emits side updates/public output/new requests or termination | **Settling accepted:** complete-delivery barrier and bounded failure/rollback; bounded runner outcomes accepted | Complete delivery and atomic failure verified. General requestless transitions remain unsupported; no fabricated pass. |
| Pawmot/Rabsca uses Revival Blessing after an ally faints | `forceSwitch`, active roster member’s `reviving:true`; `switch N` must name a fainted teammate | **Unsupported:** runner truncates revival; normalization drops reviving and builder selects incorrect targets | Preserve addressed request flag; enumerate fainted eligible slots with canonical round-trip semantics. Real revival accepts fainted targets, rejects healthy ones and resumes; verify both perspectives/Python publication. |
| Hidden Arena Trap rejects switching; visible trap ends | Request gives trapped/maybeTrapped evidence; rejection may refresh trapped flag; later requests govern switching | **Runner accepted:** candidate rollback retained; bounded request-derived reselection excludes attempted tuples | Natural Arena Trap retry selects valid moves; cap/budget exhaustion truncates. Verified accounting and current-request selection; no snapshot-derived masks. |
| Switch/drag/faint/re-entry; Shed Tail transfer | Simulator clears switch/faint state; public switch/faint/move evidence identifies lifecycle; Shed Tail copies Substitute | **Scoped acceptance:** clearing/Shed Tail, Illusion and non-Stellar public Tera re-entry | Faint/restoration and ordinary Stellar defensive typing accepted. Broader fields/linked effects open. |
| Confusion expires; Protect ends; screens/hazards/weather change | Public start/end/field records plus private effect timers; current requests remain action authority | **Deferred reconstruction/features:** confusion start/end works; single-turn is raw-only; side layers/durations and sources are incomplete | Preserve exact supported records and explicit limitations. Before adding typed features, test expiry, layer caps/removal and field replacement per chosen effect; never encode missing/private duration as zero. |
| Win/tie, budget expiry, unsupported protocol or stall | Public win/tie and terminal views; wrapper errors/log cursors | **Runner accepted:** explicit completed/truncated/failed outcomes retain committed lineage | Verified outcome reasons, budgets, final boundary and failure accounting. Terminal execution alone does not establish faithful typed-state publication. |
| Unknown aliases; doubles/other-generation mechanics | Alias guards already stop publication; package includes broader emitters | **Conditional stop / outside scope:** unknown emitted aliases need classification; other formats are excluded | Retain atomic stop and truncation evidence. No blanket grammar expansion or cross-format acceptance. |
