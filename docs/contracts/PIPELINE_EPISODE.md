# Bounded PIPELINE-002 episode runner

Status: semantic review accepted and coverage attested on 2026-09-24 for bounded
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
candidates per committed boundary. Overrides must be positive safe integers.
Attempts count each invocation of a transition method, including failed candidate
restoration/execution. Unsupported preflight, policy validation and initialization
are not candidate attempts. Rejection counts increase only for
`pipeline/v1/rejected-action`. Boundary rejections reset only after commit; episode
attempt/rejection/transition totals never reset. No fourth attempt follows a third
rejection at the same boundary under the default policy.

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
- Literal `faithful_complete_episode: false` until typed-state lifecycle corrections
  and a separate publication acceptance milestone are satisfied.

Run identity hashes the version, battle ID, format, policy version, normalized
limits and initial boundary summary. It identifies a configured segment, not a
unique physical retry or a hash of its outcome: external failure/cancellation may
produce different stops for the same run ID. Seeds, raw simulator payloads, wall
clock and failed-candidate data are not published or added to run identity.

The outcome is an orchestration envelope containing both perspective record lists,
not a player observation or model input. Route only the appropriate player's bundle
to the existing Python record validator. Python's DATA-001/record schemas are unchanged;
this slice does not introduce a Python episode-envelope validator or a collector.

## Outcome definitions

| Status | Stop codes (`episode/v1/` prefix) | Meaning |
| --- | --- | --- |
| completed | terminal | The final committed boundary has matching terminal views and a real winner/tie, established by accepted simulator settling. |
| truncated | transition-budget, attempt-budget, rejection-limit, action-exhausted, cancelled | Execution intentionally stops with valid partial lineage; it is never labeled terminal. |
| truncated | unsupported-format, unsupported-boundary, unsupported-revival-blessing, unsupported-protocol | The required next progression/protocol is outside supported scope. Unresolved aliases and unsupported raw events stop explicitly. |
| failed | invalid-options, execution-failed, settling-failed, cleanup-failed | Invalid policy/configuration, malformed state/protocol/lineage, fatal settling/simulator/stream error, or resource-cleanup error. Valid earlier commits remain available. |

`stop` never copies arbitrary error text or a candidate's private payload. Known
pipeline/settling cause codes can be retained. A malformed raw protocol event is
failed, even though the existing projection layer uses an umbrella
`unsupported-observable-protocol` code for malformed and unsupported events.
Cleanup failure changes the outcome to failed without discarding valid commits.
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
