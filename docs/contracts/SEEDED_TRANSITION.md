# SeededTransition Contract

Status: TRANS-001 `seeded-transition/v1` accepted (2026-09-23).
The additive ordinary forced-switch contract below passed separate semantic
review on 2026-09-24 within its forced-switch-plus-wait scope.

## Boundary

The simulator remains authoritative for mechanics and mutable battle state. A
transition consumes a complete pair of request-bound `CanonicalAction` values
at the simulator boundary and returns the existing `StepResult` plus explicit
transition metadata. `ObservableBattleState` is the caller-visible, sanitized
input used for request/action validation; it never contains the simulator's
serialized `Battle` object.

```text
ObservableBattleState[p1,p2] + CanonicalAction[p1,p2]
  + server-managed SeededSnapshotRef
    -> LocalBattleEnv / Showdown BattleStream
      -> StepResult + SeededTransitionMetadata + output snapshot
```

The boundary is additive and opt-in through `step_seeded_transition`. Existing
`step`, `step_canonical`, controllers, search, replay, live defaults, and
belief forks remain unchanged. Belief forks are not exact transition branches:
they intentionally rewrite hidden state and remain separate.

Random-controller RNG ownership is separate from the simulator's four-word
root seed. By default, `RandomBaselineAgent` continues to use global
`Math.random()`. Tests and explicit local harnesses may set a per-player
`ControllerSpec.random_seed` (unsigned 32-bit integer); p1 and p2 then have
independent controller streams. That optional controller seed/state is not part
of `SeededBattleSnapshot`, transition identity, or canonical-action lineage.
Reproducing an agent-controlled run therefore requires recording the simulator
seed, each random controller seed, format, and controller configuration, and
restarting from the same initial boundary and decision order.

## Snapshot and identity

The simulator-only `SeededBattleSnapshot` v1 contains the format, four-word root
seed, canonical SHA-256 simulator-state fingerprint, parent branch ID, derived
branch ID, transition lineage, and `Battle.toJSON()` state. The RPC boundary
exposes only an opaque server-managed `SeededSnapshotRef`; raw serialized state
never crosses the ObservableBattleState, feature, or RPC response boundary.

Fingerprints recursively sort object keys and preserve array order. Runtime
wall-clock protocol records matching `|t:|<integer>` are normalized to
`|t:|<timestamp>` for identity; raw logs remain unchanged in emitted output.
Branch IDs and transition IDs are deterministic hashes of schema, parent
identity, state fingerprints, root seed, ordered action IDs, the server-derived
simulator revision, and step index. Snapshot lineage is checked against its
derived branch ID before execution.

## Validation and execution

The transition request must contain exactly p1 and p2 observations/actions,
both actionable current requests, a non-negative step index, and a
server-resolved snapshot whose fingerprint, lineage, and root seed match the
live simulator. Every action is validated against its observation and then
against the live request before any raw choice is forwarded. Mixed-validity,
stale, unavailable, wait/team-preview, forced-invalid, or request-inconsistent
joint actions fail atomically with no state or log advance.

After all preflights pass, the existing canonical-to-choice/raw stream path is
used. Metadata retains parent/child branch IDs, input/output fingerprints,
root seed, ordered action IDs, simulator revision, step index, and ordered
emitted `log_delta`. The output snapshot is simulator-only and is never
embedded in the observable response by default.

## Determinism and rollback

Identical serialized snapshots, root seeds, server-derived simulator revision, step index, and
complete joint actions must produce identical transition IDs, branch IDs,
output fingerprints, action IDs, and emitted log deltas under the installed
sim-core runtime. The golden case is
[`tests/fixtures/seeded_transition_v1.json`](../../tests/fixtures/seeded_transition_v1.json).

Rollback removes the transition module, fixture/tests, contract, and additive
RPC/method while retaining legacy `step`, `step_canonical`, snapshot restore,
and belief-fork behavior. No search redesign, model retraining, or ENV-001
change is part of this slice.

## One-sided forced switches: `seeded-forced-switch/v1`

This additive, in-process contract is limited to ordinary `gen9randombattle`
forced switches. The existing v1 joint request, metadata, identity algorithm and
RPC are unchanged. No new RPC endpoint is introduced. The subsequent bounded
settling lifecycle passed separate scoped review on 2026-09-24; see
[PIPELINE_INTEGRATION.md](PIPELINE_INTEGRATION.md#bounded-settling--scoped-acceptance-2026-09-24).

`SeededForcedSwitchRequest` contains exactly `schema_version`, `snapshot`,
`observations`, `actions`, `step_index`, `acting_player`, and `waiting_player`.
Roles are distinct p1/p2 values. Both observations are required, but `actions`
contains exactly the acting player's canonical switch. The actor must have a
nonterminal, actionable forced-switch observation in `forced_switch` phase;
the other player must have an actual `wait:true` request, no legal actions,
and `post_resolution` phase. Absence is not waiting.

`LocalBattleEnv.stepSeededForcedSwitch` validates schema, role membership,
snapshot lineage/fingerprint/root seed, format, both observation perspectives,
and exact live request IDs, flags and legal-action sets before writing a choice.
Only the actor may have a pending request. The actor's live raw request is
checked for `side.pokemon[].reviving`; such requests fail with
`seeded-forced-switch/v1/unsupported-revival-blessing`. This request-provided
flag stays private and is not copied into an opponent observation. No default,
pass, or waiting-player action is synthesized.

Metadata uses `seeded-forced-switch/v1`, both role IDs and an actor-only
`action_ids` map, plus the existing lineage, seed, revision, step and raw delta
fields. The transition hash covers that schema, roles, parent branch,
input/output fingerprints, root seed, action IDs, simulator revision and step
index. Existing v1 snapshot/ref and branch derivation are reused: the distinct
transition ID is bound into the output snapshot's branch. No hidden simulator
data becomes an observation or published record.

The local runner operates on a disposable candidate. Transactional rollback
belongs to `PipelineIntegrationSession.stepForcedSwitch`: restore and validate,
execute, project both successor observations/beliefs, verify lineage, construct
the actor bundle, then commit. Callers serialize operations within a session.
Rejected, unsupported, malformed or stale candidates publish nothing and leave
the committed snapshot/prefix/boundary unchanged. Post-commit disposal errors
cannot turn a published transition into rejection; retained environments are
retried by session `close()`.

Real regressions cover a KO replacement (p2, seed `[101,202,303,404]`) and
U-turn (p1, seed `[11,202,303,404]`, choices `move 4` / `switch 2`), repeated
identities, both belief chains, return to joint play and candidate rollback.
Revival support, general requestless settling, complete episodes and full typed
volatile reconstruction are outside this slice. See the current
[checkpoint](../refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md) for validation
and the separate 2026-09-24 semantic acceptance and coverage attestation of this
ordinary forced-switch-plus-wait slice. Complete-episode readiness is not established.

## Terminal request history — scoped acceptance (2026-09-24)

Opaque terminal snapshots produced by LocalBattleEnv may additionally contain
`__neural_terminal_request_history` with `schema_version: "terminal-request-history/v1"`
and `requests`, keyed by p1/p2. These are cloned last side-bearing requests actually
addressed to each player, retained solely to reproduce private owner observations
when Showdown ends without issuing another request. Nonterminal snapshots omit it.

Restoration validates the version, recipient/side match, roster array and terminal
scope before replacing the running environment. It strips metadata before
Battle.fromJSON and hydrates observation history without a pending action or public
protocol record. Existing canonical snapshot fingerprints cover this optional field;
terminal fingerprints consequently change. Outer snapshot/transition/record versions
remain unchanged; metadata and full simulator state stay behind opaque references.

Legacy bare terminal simulator JSON remains readable but cannot reproduce private
observation history it never retained. Exact terminal observation restoration is
covered for snapshots produced with this extension. This is an implementation
contract pending separate semantic review, not an expansion of episode fidelity.

Review disposition: outer validation is insufficient. Nested malformed roster data
can throw after environment replacement or be accepted as corrupt owner state.
Define and validate the minimal consumed restoration payload before any destructive
reset. Unknown-version and side-envelope checks already work; they do not establish
recursive validity. The v1 extension remains unaccepted until this is corrected.

### Minimal-v1 correction (scoped acceptance)

New v1 writers store only `requests[p1|p2].side.{id,pokemon}`. Each roster row
contains `ident`, `details`, `condition`, `active`, `moves`, `stats`, `baseAbility`,
`item`, `ability`, `teraType`, and boolean `terastallized`. No action list or other
unused raw-request fields are retained. This supersedes the raw-v1 writer described
above; it does not change the outer snapshot/transition/record versions.

Readers validate consumed nested fields before environment teardown, then build
fresh minimal data. Supported singles invariants include one to six dense roster
entries, addressed unique identities, at most one active slot, typed move elements,
exact five-stat maps with nonnegative safe integers, valid HP/status and species/
detail/type syntax. An active slot may be fainted, as pinned forced-switch requests
encode position separately from health. Shiny details and one-character names work.

Historical raw-v1 payloads are validated and normalized; unused fields are ignored
and dropped, and legacy empty/type-valued Tera markers become booleans. The migrated
snapshot can have a different fingerprint than the old raw payload; subsequent
minimal-v1 round trips preserve identity. Missing metadata remains compatible with
bare snapshots, subject to their inability to recover absent private observations.
Unknown versions fail closed.

Malformed consumed metadata throws `TerminalRequestHistoryValidationError` with
`code`, structural `path`, and value-free `reason`. Codes are
`terminal-request-history/invalid` and `terminal-request-history/unsupported-schema`.
These errors occur before teardown and preserve the prior environment and choices.
The guarantee concerns terminal metadata, not arbitrary malformed simulator state.
Valid history remains observation-only and cannot introduce actionable requests or
raw metadata into public output/records. Snapshot fingerprints still commit to the
private data. Acceptance and digest attestation remain pending separate review.

Acceptance disposition (2026-09-24): the corrected minimal-v1 reader/writer and
non-Stellar faint slice are accepted within the checkpoint scope, superseding the
blocked/pending dispositions above. Historical raw-v1 normalization is an import
that may produce a new fingerprint and branch ID. Capture a new snapshot reference
for normalized state; do not retain the old reference or rewrite historical records.
Existing fingerprint checks reject pairing old references with normalized state.
Newly emitted minimal-v1 round trips are stable. No terminal action is resurrected.
The opaque snapshot commitment remains part of lineage; raw history remains private.
This acceptance does not establish faithful complete-episode publication.

## Bounded revival: `seeded-revival/v1` — scoped acceptance, 2026-09-25

The new schema reuses the actor/waiting roles, exact request fields, candidate
execution and lineage derivation of the one-sided path. The schema itself enters
the transition digest. Only `canonical-revival/v1` actor actions are accepted;
ordinary forced-switch and joint schemas reject revival. Existing snapshot refs
remain `seeded-transition/v1`; no snapshot migration is required.

Scope: gen9randombattle singles, one living active reviver, a genuine waiting
partner, at most six roster entries, and at least one fainted non-active target.
Normalized target indices and request slots must agree. Both observed and restored
live requests are validated before submission. This implementation shares the
internal stepSeededForcedSwitch machinery but selects behavior by explicit schema.
The pipeline owns candidate isolation: any failed validation, simulator rejection,
projection or belief join discards the candidate without changing committed state.
Active/fainted revivers, active-target instaswitch, multi-active selection and
simultaneous selections are unsupported variants.
