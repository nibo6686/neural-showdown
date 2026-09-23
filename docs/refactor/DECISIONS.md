# Refactor Decisions

## D-001 — Keep Showdown/sim-core authoritative

Status: Accepted for preparation. Mechanics remain owned by the existing Showdown-backed simulator. Alternative engines are future comparison candidates only after differential validation.

## D-002 — Separate observation from belief

An observation contains only protocol-visible information and the acting player's legitimate private request. Hypotheses, sampled hidden sets, and inferred roles belong to `BeliefState`.

## D-003 — Preserve raw protocol events

Reducers may derive snapshots, but must retain the raw event prefix and a stable event cursor or hash so future-information audits are possible.

## D-004 — Prefer fail-closed compatibility

Schema, feature, action, checkpoint, and provenance mismatches must be explicit errors. Silent padding, truncation, and cross-regime fallback are not valid refactor behavior.

## D-005 — Tests and golden fixtures precede adapters

No production state/action adapter is approved until protocol-prefix, action-parity, and seeded-transition fixtures exist.

## D-006 — Raw replay fixtures are opt-in test inputs

Status: Accepted.

Replay acquisition is never part of the default test or CI path. Replay-backed
tests use the `replay` marker and skip clearly when
`data/replays/raw/gen9randombattle/` has no `.log` files. The fixture policy,
provenance requirements, and separate validation commands are recorded in
[`REPLAY_FIXTURES.md`](REPLAY_FIXTURES.md).

## D-007 — Dependency metadata remains a separate remediation

Status: Accepted with blocker retained.

ENV-001 records runtime versus test dependencies and the Node lockfile strategy,
but exact Python versions are not inferred or invented. Python support remains
the declared `>=3.8` floor until a compatibility matrix selects a tested range,
declarations, and a lock or constraints mechanism.

## D-008 — ObservableBattleState is additive and shadow-only

Status: Accepted 2026-09-23.

The first STATE-001 slice is a separate TypeScript projection. It omits
hypotheses and simulator-only fields, does not mutate `BattleView`, and has no
consumer call sites. Existing mechanics, feature vectors, checkpoints, model
inputs, live defaults, and search behavior remain authoritative and unchanged.

## D-009 — Prefix identity and fail-closed boundaries are normative

Status: Accepted 2026-09-23.

Observable cursors count normalized protocol records; hashes cover the sanitized
canonical prefix through that cursor; observation IDs are deterministic;
snapshots are immutable; request-less observations do not invent actions;
invalid perspectives, request-side mismatches, unsupported schemas, cursor
rollback, malformed supported events, private-request leakage, and explicit
contradictions fail closed. Raw request evidence remains transient and private;
it cannot be rewritten to satisfy derived fields or cross the observable
serialization boundary.

## D-010 — CanonicalAction v1 is request-bound and opt-in

Status: Accepted 2026-09-23.

CanonicalAction v1 derives from the current legal-action set, carries explicit
request identity and provenance, and uses deterministic TypeScript/Python
serialization. The additive `step_canonical` ingress validates caller actions
against the pending request before forwarding the existing raw choice. Legacy
submission, controllers, search, replay, live defaults, and checkpoints remain
unchanged. Targeted, multi-active, pass, and skip semantics require a later
contract instead of being guessed into v1.

## D-011 — Seeded transitions use authoritative simulator handles

Status: Accepted 2026-09-23.

TRANS-001 keeps the simulator authoritative and exposes only sanitized
ObservableBattleState plus request-bound CanonicalAction values at the
transition boundary. Serialized simulator snapshots remain server-managed
behind opaque handles at RPC transport; snapshot lineage is derived and
validated, and the simulator revision is owned by the runtime rather than the
caller. Raw protocol event deltas remain available as transition evidence, with
wall-clock timestamp records normalized only for deterministic identity.

## D-012 — BeliefState v1 is a separate evidence snapshot

Status: Accepted 2026-09-23.

BELIEF-001 adds a versioned, perspective-owned BeliefState beside
ObservableBattleState. It retains explicit candidates, provenance, unresolved
uncertainty, and observation/transition lineage, with deterministic identity
and immutable snapshots. The v1 contract does not define probabilities,
confidence, propagation, search integration, or model-input changes. Existing
possible_* fields, Python posterior APIs, and hypothetical belief forks retain
their current behavior. A separate read-only acceptance review returned
`ACCEPT`; ENV-001 remains independently blocked.

## D-013 — Dataset lineage is an additive, fail-closed envelope

Status: Accepted 2026-09-23.

DATA-001 adds `dataset-record/v1` around existing examples. It records stable
battle/replay identity, source and private-data provenance, observation and
feature cursors, schema fingerprints, optional accepted observation/action/
belief/transition IDs, and deterministic battle-level split membership. Exact
source prefixes can be verified by cursor and canonical hash; future cursors,
privacy contradictions, duplicate identities, and battle/replay split
collisions fail closed. Public replay value/policy and live-private builders
validate their complete lineage collections before writing new outputs.

The envelope does not change feature vectors, model inputs, checkpoints, live
defaults, simulator authority, accepted state/action/transition/belief
contracts, or legacy dataset files. Current replay-derived records without a
canonical belief or seeded-transition join retain null lineage fields rather
than inventing evidence. No calibration, confidence, replay acquisition, or
training fields are added.

## D-014 — SEARCH-001 records current semantics without integrating search

Status: Accepted 2026-09-23.

SEARCH-001 is a documentation-only account of the distinct legacy trace,
replay-seeded exact, approximate, one-turn, and two-ply/belief paths. It does
not connect search to ObservableBattleState, CanonicalAction, BeliefState, or
SeededTransition. The documentation records the current gaps in exact-prefix
future-event isolation, stale-action validation, and shared branch/node
lineage so callers do not inherit guarantees from accepted but unconsumed
contracts. Existing search, feature vectors, checkpoints, and live defaults
remain unchanged. Any search integration requires a separately scoped work
item and review.
