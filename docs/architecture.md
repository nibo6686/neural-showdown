# Architecture

## Current accepted capture boundary — 2026-10-09

PIPELINE-002 pinned v2 capture, CE-08B stop/error delivery and FCE-08 review
packet are accepted within pokemon-showdown@0.11.10 Gen 9 Random Battle singles.
The conditional faithful field is a per-result claim: validated original-origin
continuity, both perspectives, actor contracts and terminal evidence precede
successful owned cleanup and true emission. Python independently validates
ordinary/full/bulk publication atomically. Ineligible results remain false.
This does not establish merge, Windows/cross-platform, dataset, training or live
readiness. The episode contract and closure audit retain the exact scope and
historical execution limitations.

## Retained runtime overview

The system is split across two runtimes:

- `sim-core` owns the authoritative local Pokemon Showdown battle simulation.
- `trainer` owns featurization, datasets, model code, and experiment orchestration.

Communication is newline-delimited JSON over stdio. The Python process is the parent and can:

- create and destroy battle environments
- reset an environment
- submit external choices
- ask `sim-core` for a baseline agent choice for a waiting side

The simulator never exposes hidden opponent information in `views.p1` or `views.p2`. Each player view is derived only from:

- that player's `|request|` payloads
- public battle log messages emitted on the player stream

The only state authority is the local Showdown simulator.

## Current refactor boundary

The versioned `ObservableBattleState`, `BeliefState`, `CanonicalAction`,
`SeededTransition`, and `dataset-record/v1` lineage contracts are accepted and
additive. PIPELINE-001 remains accepted only for its bounded v1 scope, and
PIPELINE-002 has separate accepted transition/progression scopes. CE-06A's
two-perspective evidence and privacy scope is separately attested; CE-06B's
terminal/predecessor closure is separately attested within its own scope and
does not accept faithful complete-episode publication. FEATURE-001 has no accepted schema, and ENV-001 remains incomplete
for cross-platform claims. The pinned simulator coverage inventory documents
remaining state and protocol closure work. See [PROJECT_STATUS.md](PROJECT_STATUS.md),
[`contracts/SIMULATOR_COVERAGE.md`](contracts/SIMULATOR_COVERAGE.md), and
[`contracts/PIPELINE_INTEGRATION.md`](contracts/PIPELINE_INTEGRATION.md).

The 2026-09-24 focused correction adds independent optional random-controller
seeds for reproducible test scenarios, source-backed move target/tag validation,
and pipeline stopping for unresolved protocol aliases. The change is not yet
covered by a separate semantic-digest review. PIPELINE-001 remains unaccepted;
PIPELINE-002 documents the future requirements for complete episode progression
through one-sided forced-switch, waiting, and requestless boundaries. The
additive CE-06A envelope retains the original per-player v2 observations and
each committed successor boundary, including exact shared public-prefix
lineage. Existing DATA-001 bundles remain actor-only; evidence for a waiting
player does not create an action row. The envelope excludes beliefs and their
simulator snapshot references, seeds, raw simulator state, and opponent-private
requests. Python validates the full chain before returning actor-only DATA rows.

CE-06B versions new envelopes as `pipeline-episode-evidence/v2` and adds
`origin_coverage`, recursively validated predecessor evidence, matching final
win/tie evidence, and a `complete_capture` claim. A fresh root counts as
`original_initial_requests` only when both owned requests are present; a resumed
segment needs a predecessor whose final boundary equals the current origin.
Without it, the segment stays explicitly incomplete. Final outcome evidence
requires both perspectives terminated with null requests, the same winner/tie,
and a matching final public `|win|` or `|tie` record. Terminal DATA rows still
belong only to actors in the committed transition. Legacy v1 evidence remains
readable. Simulator completion or `complete_capture` alone cannot authorize
`faithful_complete_episode`. The accepted conditional path validates the chain and all
current actor contracts before cleanup, then emits true only for completed terminal
results after successful owned cleanup. Python independently validates claims
before atomic publication; false remains conservative. Pinned capture acceptance
is recorded separately from the accepted conditional runtime-flag boundary; merge readiness remains separate.

The lower diagram's `features(...) -> ModelInput` edge is a target architecture,
not an implemented or accepted interface. No new feature extraction, dataset
generation, or model training is authorized by this architecture description.

Research belief branches can fork the current battle through the pinned
Showdown `Battle.toJSON()` / `Battle.fromJSON()` state API. Before restoration,
the opponent's unrevealed set fields are replaced by deterministic Gen 9
randbats samples constrained only by the audited player's public view. This is
an opt-in research path; normal env reset and live recommender defaults are
unchanged.

The multi-particle research agent creates three independently seeded sanitized
forks, evaluates the same bounded root actions in each, and selects by mean
root score. Exact-seeded and single-particle modes remain separate and
unchanged.

## Validation boundary

The audited simulator dependencies are pinned in `sim-core/package.json`.
Changing Pokemon Showdown or `@smogon/calc` requires running:

```powershell
.\scripts\run_windows.ps1 -Action validate-sim-core -SimCoreMode native
```

Parity coverage is for seeded Gen 9 singles smoke tests. The 13-action codec
does not represent doubles or other multi-action formats. Exact public replay
reproduction is not supported because saved public logs omit seeds, complete
private teams, and private requests; only public-state reconstruction is
validated. Exact private-request stats are passed into damage calculation and
covered by regression tests.


## Public typed-state evidence boundary

`sim-core/src/typed_state_lifecycle.ts` reads the pinned lifecycle atlas from the
simulator coverage manifest and replays the normalized public prefix before a
TypeScript observation/belief boundary is accepted. The replay constructs only
Substitute presence, source-rooted hazard layers, and source-rooted side-condition
presence. Every other inventoried volatile remains raw-only; unrooted side
condition records stop before projection.

`trainer/src/neural/typed_state.py` independently replays the same manifest rules
before `pipeline_record.py` publishes DATA-001. Both validators compare every
typed volatile and side-condition map that is present with the prefix-derived
state. This preserves actor-only record publication and keeps private durations,
callback state, hidden requests, and simulator snapshots out of public typed
state. The exact Substitute transfer exception is bound to the source switch
tag for Shed Tail; Court Change swaps only the explicitly listed side IDs.

C17/C20 retain their accepted scoped lifecycle boundaries. C22 callback composition
and C23 slot-effect sufficiency remain aggregate FCE-01 blockers. The manifest's
public-consequence matrix binds slot source routes and private-slot rejection,
and independent ordered health/item replay rejects false maps, missing fact-bearing rows,
and unsupported opponent item presence. A living unrevealed terminal Illusion
uses private, nonserialized identity authority from a validated predecessor,
with action, transition, prefix, perspective, and ordered roster continuity.
Ordinary linked bundles and full predecessor chains can supply that authority;
a bare deserialized terminal observation cannot authorize an unrevealed alias. Temporary validation authority
is discarded on failure. These repairs await separate acceptance. The aggregate
FCE-01 and complete-episode gates remain open.


The bounded terminal switch path validates the submitted canonical owned switch before using its request slot to bind an incoming unrevealed Illusion. Full results and compact sweeps stage this action against the already validated predecessor boundary before terminal semantic replay, then finish all actor/belief joins atomically. A bare envelope has no action authority for that incoming alias. Normal visible switches remain attributable only from a revealed identity or explicit addressed base/current non-Illusion abilities. Private terminal snapshot v2 switch history supports restoration separately and never grants public authority. Departed unrevealed item writers, including Frisk reveal and Recycle restoration, remain raw where the carrier cannot be attributed. Publicly established consumption history remains required across re-entry; a later ambiguous nickname collision restores that prior history. Current owned possession remains exact to the addressed request. Generated waiting requests retain full addressed side data; sparse historical wait rows cannot erase established owned evidence.


Historical prefix identity validation uses a fresh incremental SHA-256 array
stream within each parent-belief validation. It appends the existing canonical
record text and separators once, then copies the stream and closes the array
at each validated historical cursor. Canonical bytes, observation/belief
identities, cursor/order guards and wrong-hash rejection are unchanged. No
hash state is shared across candidates or validation calls. The focused npm
episode command explicitly skips the optimized long fixture; full capture
validation still checks the complete original-to-terminal chain.


### Historical implementation checkpoint — 2026-10-09, before independent review

The pending verdict below is retained as history; current scoped acceptance is
recorded above and in the closure audit.

CE-08B finalization guards run identity, evidence construction and validation before
attempting owned-session cleanup. Failure retains committed records, emits only
safe classified diagnostics and a construction/validation stage, and leaves a
null envelope unpublishable. Cleanup failure takes precedence while preserving
the earlier cause/stage. Python requires normalized exact positive-safe-integer
limits and bounded committed/rejected/stopped-attempt accounting before emitting
rows. See PIPELINE_EPISODE and the four-finding repair checkpoint; independent
CE-08B/FCE-08 acceptance remains pending.
