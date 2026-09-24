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

## D-015 — Existing model checkpoints are abandoned for the new pipeline

Status: Current project decision (2026-09-24).

Existing legacy and vNext checkpoints are intentionally abandoned for the
refactored approach. Their availability, quality, or LFS state is not a blocker
to defining or training a new model. Do not load, fetch, or promote them as part
of this pipeline work. This decision does not change historical reports or
legacy runtime documentation that describes older interfaces.

## D-016 — Simulator coverage is reviewed with explicit gaps

Status: Review evidence recorded (2026-09-24); PIPELINE-001 and FEATURE-001
remain unaccepted.

SIM-COVERAGE-001 pins its audit to `pokemon-showdown@0.11.10` and
`gen9randombattle`, records the state/protocol inventory and drift checker, and
retains unknown or raw-only cases as explicit blockers. Registry and token
counts are inventory measurements, not proof that every state lifecycle is
projected. Unknown scoped protocol records stop collection pending review.

## D-017 — Do not generate refactored features before FEATURE-001 acceptance

Status: Current project gate (2026-09-24).

The PIPELINE-001 implementation candidate records lineage with the
`features-not-produced/v1` sentinel. No feature dimensions, targets, reward,
horizon, or model input/output interface are inferred from legacy, v7, or v8
systems. FEATURE-001 must be versioned, shared by collection and inference, and
reviewed before bulk feature extraction or new dataset generation.

## D-018 — Keep controller randomness separate from simulator randomness

Status: Focused test-control implementation recorded (2026-09-24); no change to
the legacy random-controller default.

The simulator's four-word seed continues to own Showdown mechanics and team
generation RNG. `RandomBaselineAgent` still defaults to `Math.random()` unless
an explicit per-player `ControllerSpec.random_seed` is supplied. Explicit
controller seeds are independent unsigned 32-bit streams, one per player, and
are not part of the simulator snapshot or transition lineage. Reproducing a
random-agent scenario requires the simulator seed, controller seeds, format,
controller types, and decision order. This test-control change and its protocol
tests remain subject to separate semantic digest review.

## D-019 — Stop unresolved protocol aliases before pipeline publication

Status: Focused implementation recorded (2026-09-24); pipeline acceptance
remains pending.

`clearstatus`, `-clearstatus`, and `nothing` remain unknown scoped aliases and
stop at both pipeline protocol projection entry points with a structured
diagnostic. `-nothing` is a distinct no-payload raw-only event emitted by the
pinned Gen 9 Splash source. Move target validation follows the pinned Showdown
identifier and tag grammar; `[notarget]` is metadata, never an ordinary target.
This documents runtime behavior and does not accept SIM-COVERAGE-001 or
PIPELINE-001.

## D-020 — Complete episode boundaries require a separate progression contract

Status: Requirements registered in PIPELINE-002 (2026-09-24); implementation
not started.

PIPELINE-001 v1 fails closed on one-sided forced-switch, waiting, and
requestless boundaries. A future complete-episode collector must use actual
current requests, must not synthesize pass/default actions for non-actionable
players, and must report terminal completion or an explicit truncation with
last committed cursor and reason. No episode may be silently dropped as if
complete. PIPELINE-002 requires real simulator progression tests and separate
review before full-episode claims.
