# Bounded PIPELINE-002 episode runner

Current status (2026-10-09): PIPELINE-002 pinned v2 capture/boundary progression
is accepted against FCE-01–FCE-08. `faithful_complete_episode` is a per-result
claim. Conditional emission and matching TS/Python enforcement received scoped
independent runtime acceptance on 2026-10-09. Capability
acceptance does not make failed/incomplete/unsupported results faithful.
See the closure audit’s final PIPELINE-002 decision for claim distinctions.

Historical baseline: semantic review accepted and coverage attested on 2026-09-24 for bounded
orchestration with exclusive serialized-session ownership. No blocking findings or
production corrections. This contract does **not** establish faithful complete-episode publication
or training readiness. Accepted joint, ordinary forced-switch and settling scopes
remain unchanged.

## Entry points and ownership

`runPipelineEpisode(options)` creates and exclusively owns a session.
`continuePipelineEpisode(session, options)` transfers exclusive ownership of an
existing session and reports only the segment starting at its current boundary;
it does not claim to return earlier records. Both close the session before returning.
Calls are sequential. Callers must not step, close or otherwise mutate the session
concurrently. Creation failure returns a failed outcome with null boundaries;
invalid continuation options retain the supplied session's committed origin.

The format is limited to `gen9randombattle`. The runner composes `step(actions)`
and `stepForcedSwitch(action)`; it never submits a waiting player's action or
advances a requestless boundary with a default/pass. An episode-specific session
preflight checks every live forced-switch request for Revival Blessing, including
joint boundaries. It reads the addressed private request without projecting its
`reviving` flag. Existing transition APIs and successful record schemas are unchanged.

## Budgets and selection

Default limits are 256 committed transitions, 512 total attempts and three rejected
candidates per committed boundary. Overrides must be positive safe integers. Published result limits must be an object with exactly
`max_transitions`, `max_attempts`, and `max_rejections_per_boundary`, each an
integer from 1 through 9007199254740991. Partial runner options are expanded to
this normalized schema. Invalid-options results may retain null limits for
controller diagnostics, but cannot pass Python publication.
Attempts count each invocation of a transition method, including failed candidate
restoration/execution. Unsupported preflight, policy validation and initialization
are not candidate attempts. Rejection counts increase only for
`pipeline/v1/rejected-action`. Boundary rejections reset only after commit; episode
attempt/rejection/transition totals never reset. No fourth attempt follows a third
rejection at the same boundary under the default policy.

Accounting distinguishes committed transitions, retryable rejected candidates,
and at most one nonrecoverable controller-stopped candidate. The latter consumes
an attempt but neither commits nor increments retryable rejections. Clean stops
require attempts = committed + rejected; unsupported-protocol and the two
recognized Revival guards may add exactly one stopped attempt. Pre-selection
guards consume no attempt. This exception never relaxes count or budget bounds.

The default `ascending-request-indices/v1` policy uses the current legal indices
in ascending order. Joint candidates are the p1-major Cartesian product; one-sided
candidates contain only the actor. A retry regenerates candidates from unchanged
committed requests, excludes every previously attempted action-ID tuple at that
boundary, then chooses the first remaining tuple. Only explicit choice rejection
is recoverable. Stale actions, malformed data, fatal simulator errors and protocol
failures are not retried. Candidate rollback is supplied by the accepted session.

Optional `action_order(observation)` receives only one player's frozen observation
and must return a permutation of all that request's legal indices. A custom policy
requires a nonempty `policy_id`; callers must version deterministic, terminating,
synchronous policies. No opponent-private data is passed to selection. The runner
cannot preempt synchronous policy/simulator calls. Accepted settling limits apply
independently to candidate restoration and execution; episode budgets do not replace
them or reset them during a wait.

Cancellation via `AbortSignal` is cooperative at committed boundaries. An in-flight
transition settles atomically; if it commits, its records are retained before the
runner checks cancellation. Terminal completion has priority over cancellation and
budgets. Otherwise the order is cancellation, transition budget, attempt budget,
scope checks, and selection. A choice rejection reaching its boundary cap stops
immediately; exhaustion of all candidate tuples also truncates.

## Result: `pipeline-episode/v1`

The control-plane result contains:

- `run_id`, `battle_id`, `ruleset`, `policy_id`, normalized `limits` (null for invalid
  options), `status`, and `stop` with a stable code/reason and optional cause code.
- `counts`: attempts, committed transitions, rejected candidates and rejections at
  the final boundary, all scoped to this invocation/segment.
- `initial_boundary` and `final_boundary`: step index, kind, branch/fingerprint,
  and each perspective's observation/belief IDs, cursor, request state and winner.
  Null means no valid committed boundary was obtained, not an empty terminal battle.
- Ordered `transition_ids` and separate `records.p1` / `records.p2` arrays of the
  existing perspective-specific bundles. A waiting side has no record for a
  one-sided transition. No rejected or failed candidate contributes records.
- Nullable `evidence_envelope`. It is `null` for v1 observations; v2 runs retain
an additive `pipeline-episode-evidence/v2` envelope as described below. Readers
continue to validate historical `pipeline-episode-evidence/v1` envelopes.
- Boolean `faithful_complete_episode`. True requires the supported validated v2
  original-origin-to-terminal chain, all current-segment actor contracts, completed
  status with terminal stop, and successful owned-session cleanup. False is a
  conservative claim accepted even when valid evidence could support true; it
  does not exempt any result from ordinary validation. This is never an
  installation-wide capability declaration.

### Conditional faithful claim — accepted pinned runtime scope, 2026-10-09

| Evidence/execution class | Permitted claim |
| --- | --- |
| Valid original-request-to-terminal win or tie | True after full chain/actor validation and successful cleanup; conservative false accepted. |
| Resumed segment with validated original-origin predecessor chain | Same eligibility; predecessor actor publication remains separately required. |
| Unbound resumed segment | False. |
| Zero-transition terminal-only evidence | False. |
| Incomplete, canceled, budget-limited, unsupported, construction/execution/settling/cleanup failure | False, including complete coverage retained after cleanup failure. |
| Historical false-valued result or legacy v1 evidence | False remains compatible under the existing validators; v1 cannot authorize true. |

TypeScript validates origin, predecessor, ordered commits, both perspectives,
terminal evidence, actor observation/belief/action/transition joins, counters and
summary references before emission. It assigns true only after successful cleanup.
Python independently applies the existing full/shared metadata and envelope rules,
then validates each actor through the ordinary or bulk publication path. Publication
remains atomic: a true Boolean, terminal status, outcome or row count is never proof.
An envelope-only validator establishes coverage, not a faithful result claim.

No schema version bump is required: the existing result/v1 Boolean field expands
from its historical reserved false value; every previously valid false result
retains its meaning and identity. True requires evidence/v2. The derived flag is
outside canonical run, origin, observation, belief and transition hash inputs;
changing it cannot repair an invalid join. No DATA-001 field is added. Predecessor
actor rows remain a separate validated publication obligation; the current segment
neither fabricates nor republishes them. Existing historical false-only milestone
statements below describe their recorded checkpoints, superseded only for emission
by the independently accepted runtime boundary. This acceptance does not approve
merge readiness, datasets, training or live-model behavior.

Run identity hashes the version, battle ID, format, policy version, normalized
limits and initial boundary summary. It identifies a configured segment, not a
unique physical retry or a hash of its outcome: external failure/cancellation may
produce different stops for the same run ID. Seeds, raw simulator payloads, wall
clock and failed-candidate data are not published or added to run identity.

The outcome is an orchestration envelope, not a player observation or model input.
The two-perspective evidence envelope is an internal validation artifact; it is
not routed to either player or to a model consumer.
For v1, route only the appropriate player's bundle to the existing Python record
validator. For v2, the Python bridge can validate the separate evidence envelope or
the full result; full-result validation returns DATA-001 rows for actor bundles only,
after every envelope and record join succeeds. Waiting players never receive a
fabricated action or DATA-001 row. DATA-001/record schemas are unchanged, and this
contract does not introduce a collector.

## CE-06A two-perspective evidence envelope

Accepted 2026-10-06 within its source, evidence, and privacy scope. For a
v2-observation run, `evidence_envelope` retains the segment's
origin boundary and every committed successor boundary. Each boundary contains
both complete v2 `ObservableBattleState` values, including each player's own
initial/current request and the exact normalized public prefix, cursor, prefix
hash, and observation identity. No belief object is embedded, so simulator
snapshot references do not enter this envelope. The existing `records.p1` and
`records.p2` bundles remain actor-only.

Each commit stores the origin ID, transition reference without an action ID, the
acting-player list, and both successor observations. The origin ID commits to the
run ID, ruleset, source reference, fresh/continuation kind, and complete segment
origin boundary. Every commit repeats that origin ID. The evidence identity covers
the full envelope. TypeScript and Python validate v2 observations, exact public
prefix extension for each side, consecutive step/branch/fingerprint lineage,
unique commits, request-derived actor lists, and actor-only bundle joins. Gaps,
reordering, duplicates, prefix changes, and inconsistent origin IDs fail closed.

The v1 envelope remains readable for historical evidence. New v2 envelopes add
the CE-06B closure block described next. Deterministic hashes detect inconsistent
or independently forged identities, but are not signed provenance against a
coordinated rewrite of the entire result.

## CE-06B terminal and resumed-segment closure

Implementation checkpoint dated 2026-10-06; the scoped semantic review and
digest attestation were accepted on 2026-10-06. New v2 envelopes retain a closure block with an
explicit `origin_coverage`, optional full predecessor envelope, final terminal
evidence, and `complete_capture` boolean. A fresh root is `original_initial_requests`
only when both owned initial requests are present. A restored already-terminal
root is `terminal_only`; a continuation without a validated predecessor is
`segment_only`.

A continuation predecessor is recursively validated and its final nonterminal
boundary must exactly equal the current segment origin, including both owner
observations, requests, cursors, prefixes, branch, and fingerprint. Coverage is
inherited through that chain. A terminal is recorded only when both observations
are terminated, have no follow-up request, agree on winner/tie, and end in the
matching public `|win|<name>` or `|tie` record. The terminal reference joins both
observation IDs, cursors, prefix hashes, and the final branch/fingerprint. The
accepted CE-02D turn-limit warning remains raw public prefix evidence; CE-06B
does not broaden its grammar.

`complete_capture` is true only when the validated origin chain reaches both
original initial requests and the final boundary has matching terminal evidence.
Simulator `status: completed` still describes this invocation's execution and
may cover a segment or zero-transition terminal-only result; it does not imply
`complete_capture`. The top-level result retains `faithful_complete_episode:false`
in all cases. Predecessor envelopes contain only public two-perspective evidence
and owner-specific requests, never seed, serialized simulator state, hidden
rosters/sets, foreign requests, action data, or a future prefix suffix.

The Python full-result validator checks status/terminal agreement and validates
the complete nested origin chain before returning DATA-001 rows for the current
segment's actor bundles. Nested predecessor commits do not invent or republish
past actions. A waiting/nonacting side has a boundary observation but no action
or decision row. A zero-transition terminal preserves its two final observations
and raw outcome but remains `terminal_only` and incomplete.

The CE-06B focused source-engine controls cover an ordinary win, the restored
turn-limit tie with CE-02D warnings, terminal completion after one-sided revival,
valid and missing predecessor chains, and zero-transition terminal capture.
Rehashed winner/tie, terminal cursor/reference, origin-coverage, foreign-request,
gap, reorder, duplicate, prefix, and final-boundary attacks fail before invalid
DATA-001 output; valid controls retain actor-only publication. CE-08A/08B still
own the full positive closure/review packet. `faithful_complete_episode:false`
remains mandatory.

The Python bridge keeps its one-bundle mode unchanged. Evidence-only input returns
a validation receipt and no DATA row. Full `pipeline-episode/v1` result input
validates the entire envelope and every actor bundle before emitting one array of
DATA-001 actor rows; any invalid chain returns a nonzero status and empty stdout.

For long, complete v2 chains, `pipeline-episode-publication-sweep/v1` is a compact
bulk form of the same full-result publication contract. It carries the validated
result status, stop, counts, boundary summaries, transition list, and evidence
envelope once, one ordered row per actor commit (`transition_id`, action,
and input/successor belief IDs), and each distinct belief once. Its repeated
`source_protocol_prefix` is omitted, and cumulative belief arrays use parent-linked
append deltas when the exact parent prefix matches; otherwise the field is carried
in full. Python reconstructs the original belief before checking its canonical ID.
The validator derives each row's exact input and successor observations and
transition from the envelope's actor/commit position. It validates the complete
origin/predecessor/terminal/prefix chain before building any row, then hydrates
each belief prefix only from the observation named by that belief's current
reference. The existing canonical belief identity and belief history/provenance
checks run after reconstruction. Every actor row then runs the same
ownership, action legality, belief/transition lineage, privacy, and DATA-001
validation used by ordinary bundle publication. Only prefix parsing and prefix
hashing already proved for the exact envelope boundary are reused; the DATA-001
hash is computed once for each distinct joined boundary. Rows are accumulated in
memory and stdout is written only after every row succeeds, so one bad row yields
exit code 2 and empty stdout. The sweep covers only the current segment. A
continuation predecessor's actor bundles remain separately published through the
ordinary one-bundle path, and waiting/nonacting sides receive no row. Existing
single-bundle and full-result interfaces are unchanged. This bounded bridge does
not change `faithful_complete_episode:false` or establish final CE-08A acceptance.

## Outcome definitions

| Status | Stop codes (`episode/v1/` prefix) | Meaning |
| --- | --- | --- |
| completed | terminal | The final committed boundary has matching terminal views and a real winner/tie, established by accepted simulator settling. |
| truncated | transition-budget, attempt-budget, rejection-limit, action-exhausted, cancelled | Execution intentionally stops with valid partial lineage; it is never labeled terminal. |
| truncated | unsupported-format, unsupported-boundary, unsupported-revival-blessing, unsupported-protocol | The required next progression/protocol is outside supported scope. Unresolved aliases and unsupported raw events stop explicitly. |
| failed | invalid-options, execution-failed, evidence-invalid, settling-failed, cleanup-failed | Invalid policy/configuration, malformed state/protocol/lineage, fatal settling/simulator/stream error, or resource-cleanup error. Valid earlier commits remain available. |

For v2 results, `completed` must agree with the final two-perspective terminal
evidence. It does not promise origin-to-terminal closure; consult the envelope's
`complete_capture` field. `faithful_complete_episode` remains false.

`stop` never copies arbitrary error text or a candidate's private payload. Known
pipeline/settling cause codes are retained when available. Revival guards retain
the distinct safe codes `seeded-revival/v1/unsupported-request` and
`seeded-forced-switch/v1/unsupported-revival-blessing`; arbitrary exceptions
retain only the generic execution classification. A protocol diagnostic
may retain its nonnegative `cause_record_index`; raw/private error text is never
copied. Cleanup failure retains the preceding classified cause and index. A malformed raw protocol event is
failed, even though the existing projection layer uses an umbrella
`unsupported-observable-protocol` code for malformed and unsupported events.
Cleanup failure changes the outcome to failed without discarding valid commits.
An immutable complete_capture evidence fact is not a successful execution or
faithful acceptance claim. Full-result and compact publication share validation
of stop/status taxonomy and nonnegative integer counters, committed/rejected
accounting, finite declared bounds and budget-stop exhaustion; inconsistent
metadata rejects atomically before stdout. Evidence-invalid denotes the final
envelope delivery barrier failing, with no publishable envelope. Run identity,
evidence construction and validation share this guarded finalizer. A safe
`evidence_failure_stage` distinguishes construction from validation. Owned-session
cleanup is attempted afterwards even if construction fails. If cleanup also
fails, cleanup-failed takes precedence while retaining the earlier safe cause,
index and evidence stage. Committed records and summaries remain available,
but a null envelope cannot publish any of them.
A failed transition preserves the prior committed boundary; no partial successor
is returned. Result construction appends each successful transition's bundles once,
synchronously, before the next iteration.

## Evidence and limitations

Real seed `[101,202,303,404]` completes in 55 committed transitions using the default
policy, with joint transitions and one-sided records for both actors. Two runs have
identical outcomes/lineage. Final actor bundles validate through Python. The natural
Arena Trap scenario uses seed `[46,101,202,303]`, switches p1 to Dugtrio (`switch 3`)
and p2 to Tinkaton (`switch 6`), then rejects p2 `switch 2` before a valid alternate.
Controlled tests cover budgets, rejection caps/reset/accounting, cancellation,
requestless/revival stops, unsupported versus malformed protocol, simulator failure,
initialization failure and cleanup failure. Revival evidence is synthetic, not a
natural revival battle.

Review matched all three checkpoint hashes, reused 102 TypeScript / 20 Python
passing evidence, and freshly passed the build and all 17 runner regressions.
Additional probes verified terminal precedence at both exact limits with concurrent
cancellation, and action exhaustion without repeat attempts or publication. Runner
source/tests now join the hashed coverage list; checker and six self-tests pass.

Public switch/faint boost and volatile clearing and supported Shed Tail transfer
are implemented pending separate semantic review. Other switch/faint fields,
Revival Blessing support and broader lifecycle coverage remain unresolved. A real
terminal result proves execution completion only. Exact validation, review hashes
and remaining gaps are in the [checkpoint](../refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md).

## Bounded revival extension — scoped acceptance, 2026-09-25

The runner dispatches a supported `one_sided_revival` boundary to `stepRevival`.
It preserves existing budgets, explicit-choice-rejection-only retry policy and
commit-only actor record accounting. Revival consumes one transition on commit;
resumed joint play again publishes both actor records. Supported requests are
checked before action enumeration. Unsupported variants retain explicit
`episode/v1/unsupported-revival-blessing` truncation with no fabricated actions;
other unsupported paired request states retain unsupported-boundary truncation.
Natural mirrored Pawmot and Rabsca fixtures now supplement the prior synthetic
exclusion checks. Separate 2026-09-25 review accepts and attests this scope;
`faithful_complete_episode:false` is unchanged.


## Evidence-derived typed volatile and side-condition boundary (2026-10-07)

The coverage manifest contains a pinned `public-typed-state-lifecycle/v1`
classification for all 88 inventoried move volatiles and 23 side conditions.
Only Substitute and the eight source-rooted Gen 9 Random Battle side conditions
remain typed: Substitute; Spikes and Toxic Spikes as capped layer counts;
Stealth Rock, Sticky Web, Reflect, Light Screen, Aurora Veil, and Tailwind as
presence values. The remaining 87 volatile values are raw-only; the 15
side-condition entries without an approved generated direct root fail closed
while callback composition remains open under C22. C23 retains source-route
evidence through `public_consequence_matrix/v1`, which keeps slot conditions
private and witnesses valid generated consequences. Independent health replay now rejects fully rehashed false delayed
HP/status/fainted maps and missing derived rows/fields in both runtimes. C23
uses validated committed predecessor identity authority for living unrevealed
terminal Illusion in native sessions, ordinary linked bundles, and full
evidence chains. This bounded implementation awaits separate acceptance. The atlas records
start/reapply/end, cap, expiry/removal, transfer, switch/drag/faint/re-entry,
replacement, terminal, privacy, source, and test dispositions.

Before a TypeScript boundary is committed, the normalized retained prefix is
replayed into the typed subset and compared with each perspective's view. The
Python publication validator independently replays the same manifest contract
before it can emit DATA-001. The bounded Substitute transfer is accepted only
for the exact `[from] Shed Tail` switch record. Court Change transfers only the
manifest's typed side-condition set; no simulator snapshot, private timer,
callback source, hidden target, or other player's request is used to construct
the projection. Historical v1 view-less compatibility applies only when no prefix-derived
health, item, or typed lifecycle fact is concealed. A revealed switch or other health writer requires
its correctly sided row and derived health/status/faint fields in v1 and v2.
Current addressed requests establish exact own health; public HP uses the
pinned rounded percentage, including the 99-percent near-full rule. Without
a current request, retained own exact HP is checked against its public bucket,
not against an invented hidden numerator. Mutable view active/name fields
cannot authorize an Illusion appearance alias. A bare deserialized terminal observation cannot authorize an unrevealed owned alias. Publicly attributable normal terminals retain their existing standalone behavior. Ordinary two-observation bundles are sufficient only after the
input, beliefs, owned action, transition metadata, snapshot joins, and exact
prefix extension validate. Full envelopes validate predecessor closure before
the origin boundary and bind that boundary exactly. Stable owned slot, ident,
name, and base species order must continue; public Transform/form changes do
not change this roster identity. An incoming requestless switch can bind its owner from a canonical submitted switch action validated against the predecessor request slot and exact transition. Ordinary linked records, full results, and compact bulk rows carry that action; a bare envelope lacks it and rejects an incoming unrevealed alias. Without an action, a revealed replacement or explicit base and current non-Illusion abilities for every addressed owner can establish a visible switched identity. Drag never borrows a switch action. After public replacement, the old disguise joins its restored
bench row rather than the terminal actual owner. Authority is private,
nonserialized and temporary during validation; failed bundles cannot authorize
later standalone validation. Opposing observations retain only public identity.

The scoped C17/C20 lifecycle boundary is accepted. C22 callback composition
and C23 slot consequence sufficiency remain open, so the FCE-01 aggregate and
CE-08A remain unaccepted. Slot state remains private. `faithful_complete_episode:false` remains required.


## Ordered public item evidence (2026-10-08 implementation)

Existing v1/v2 schemas and canonical identity algorithms remain unchanged.
Ordered eligible public `-item`/`-enditem` writers establish known name, present,
consumed/removed absence, or fresh-appearance unknown. Accepted bounded Recycle
and transfer templates retain their existing grammar. Public item presence
serializes as the existing optional opponent `item:has-item`; public absence
and unknown both omit the marker, while only the former is a proven fact.
Unsupported positive markers and missing fact-bearing rows fail validation.
Owned current items follow the addressed request or validated terminal
predecessor plus suffix writers. Existing `item_state` and retained `last_item`
follow attributable public writers. After a departed unrevealed appearance, a roster admitting Illusion cannot attribute the old writer to a real teammate by nickname. That bounded historical carrier remains raw-only: current owned item stays exact to the addressed request, unsupported optional `last_item` is null and absent-item disposition is unknown. A current appearance writer or its public replacement attributes that appearance; a later replacement does not resolve an earlier departed carrier. Consumption history attributed by public replacement cannot be omitted after switch/re-entry, even when another owned Illusion carrier remains possible. A later ambiguous appearance reusing that nickname restores the previously established history on departure; its reveal/restoration/consumption writers remain raw instead of overwriting the real teammate. Validated terminal predecessor history remains checked independently. `item_suppressed` follows only prefix-established Magic
Room, the extractor's existing field semantics. Passive item provenance or
consumed activation never reacquires an item. Fresh switch/drag appearances
start unknown; replacement migrates their facts and restores displaced bench
evidence. Historical sparse compatibility is permitted only when no public or
owned fact is concealed. Previously incorrect serialized omissions and false
maps reject; validators do not repair them. Projection constructs the existing
public presence marker from public evidence without inspecting hidden loadouts.

The item and terminal identity repair matrices are implementation evidence.
Pinned waiting requests include `side.getRequestData()` (Battle.makeRequest and consumed-request branches); sparse historical `side:[]` cannot erase previously established addressed roster/item authority. Waiting sides receive no fabricated actor rows. Private terminal restoration is separately versioned in SEEDED_TRANSITION and never supplies public envelope authority.

C22 broader callback composition and C23 sufficiency stay OPEN until separate
acceptance; CE-08A, CE-08B, PIPELINE-002 and `faithful_complete_episode:false`
remain unchanged. No dataset, training, or live gate is advanced.
