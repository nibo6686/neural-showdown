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

Status: Implemented pending review.

The first STATE-001 slice is a separate TypeScript projection. It omits
hypotheses and simulator-only fields, does not mutate `BattleView`, and has no
consumer call sites. Existing mechanics, feature vectors, checkpoints, model
inputs, live defaults, and search behavior remain authoritative and unchanged.

## D-009 — Prefix identity and fail-closed boundaries are normative

Status: Implemented pending review.

Observable cursors count normalized protocol records; hashes cover the canonical
prefix through that cursor; observation IDs are deterministic; snapshots are
immutable; request-less observations do not invent actions; invalid
perspectives, request-side mismatches, unsupported schemas, cursor rollback,
and explicit contradictions fail closed. Raw evidence is retained for audit and
cannot be rewritten to satisfy derived fields.
