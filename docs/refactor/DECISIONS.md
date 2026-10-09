# Refactor Decisions

## Current status clarification — 2026-10-01

Accepted project evidence now includes bounded v2 transition capture and
TypeScript/Python publication parity within the reviewed ordinary
joint-actionable scope; separately attested scanner, source-coverage, and Gen 9
Random Battle reachability slices; and accepted macOS simulator-record and
broader trainer/live environment profiles within their documented scope. The
complete-episode closure audit is complete as an audit and backlog, not an
implementation acceptance. Keep `faithful_complete_episode:false`.

ENV-001 remains incomplete for cross-platform claims. Windows clean recreation
and Windows trainer/live support are deferred platform work and are not blockers
to a future scoped macOS refactor merge. These clarifications do not authorize
features, datasets, training, live-model behavior, or other formats. The dated
decisions and review records below retain their original evidence and scope.

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

## D-021 — Separate simulator-record validation from trainer/live runtime policy

Status: Accepted (2026-09-29).

Accepted 2026-09-29 after review; this accepts the ENV-001 policy direction only,
not implementation or clean-environment proof.

ENV-001 has passing existing-machine evidence but no repository-owned Python
dependency policy or clean-environment proof. The recorded macOS environment is
Command Line Tools Python 3.9.6 with Node v24.21.0/npm 11.19.0; Windows uses the
existing `neuralgpu` Conda Python 3.11.14 with Node v24.15.0/npm 11.12.1. These
are observed environments, not approved Python, Node, or npm support claims.
Continue restoring sim-core with `npm ci` from the committed
`sim-core/package-lock.json`; this decision does not replace the Node lock policy.

Options considered:

- Use `trainer/pyproject.toml` for repository-owned Python declarations and
  checked-in resolver-generated lock/constraints artifacts, allowing
  platform-specific outputs where compatibility or wheel availability requires
  them. This keeps one declaration source while supporting both recorded
  platforms, but requires compatibility and lock-format work.
- Use a Conda environment specification/lock as the dependency authority. It can
  describe a Windows trainer/GPU environment, but would require Conda for that
  policy and would not match the recorded macOS terminal-Python setup as a shared
  requirement. The existing Windows environment was not recreated from
  repository metadata.
- Keep only the existing machine instructions and declared `Python >=3.8` floor.
  This preserves flexibility but cannot reproduce Python dependencies from a
  clean checkout.

Decision: preserve macOS terminal Python and Windows `neuralgpu` Conda as
recorded working environments; do not require the same environment manager on
both platforms. Use `trainer/pyproject.toml` as the repository-owned Python
declaration source and evaluate a checked-in generated Python lock/constraints
approach in the separate ENV-001 implementation. Conda may remain a
Windows-specific environment option, but is not the sole dependency authority.
Do not derive support ranges or package pins from the currently installed
environments.

The simulator-record validation profile is Python standard-library record
validation plus `pytest` for its focused Python regression tests, and the locked
sim-core Node build/runtime restored with `npm ci`; select the Python package
through `PYTHON` and `PYTHONPATH` as documented in `ENVIRONMENT_VALIDATION.md`.
NumPy, PyTorch, and PyYAML belong to future trainer/feature work; FastAPI,
Pydantic, and Uvicorn belong to future live-server work. PyTorch wheel source,
CPU versus accelerator selection, CUDA policy, and platform-specific package
resolution require compatibility evidence in that broader scope. They are not
part of simulator-record validation.

Clean-environment proof must recreate an isolated Python environment from the
committed declarations and lock/constraints on both macOS and Windows, record
the selected Python/Node/npm versions, restore sim-core with `npm ci`, build it,
verify Node launches the selected `PYTHON`, and pass the focused TypeScript
simulator-record, Python record/lineage, and coverage checks in
`ENVIRONMENT_VALIDATION.md`. Results establish only the tested environments and
checks. Public replay fixtures remain optional for simulator-only validation;
without `.log` fixtures, replay-marked checks may skip. Fixtures are required
only for replay-parity or replay-sourced-data claims.

Follow-up actions (separate from this decision):

- [ ] Implement ENV-001 by testing a runtime compatibility matrix, declaring
  dependencies by validation versus trainer/live profile, and selecting the
  Python lock/constraints format and resolver. Resolve PyTorch platform and
  accelerator packaging only for the broader trainer/live profile; do not copy
  host-installed versions as pins.
- [ ] In a separate clean-environment validation task, recreate the selected
  profiles on macOS and Windows from repository metadata, run the focused checks
  above, and record versions, commands, results, and platform-specific failures
  in `ENVIRONMENT_VALIDATION.md`.

Follow-up status (2026-10-01): the repository-owned simulator-record profile,
macOS broader trainer/live declarations and locks, and accepted macOS clean
proofs are recorded in `ENVIRONMENT_VALIDATION.md`. Windows clean recreation
and the Windows trainer/live profile remain deferred as ENV-001C2. Their open
status keeps ENV-001 incomplete for cross-platform claims, but does not block a
scoped macOS refactor merge.

## D-022 — Resolve broader trainer/live profiles per platform

Status: Accepted (2026-09-30).

Accepted 2026-09-30 after review; this accepts the policy direction only and
does not claim clean recreation or ENV-001 completion.

Deciders: [Team]

### Context

Accepted D-021 makes `trainer/pyproject.toml` the Python declaration source and
keeps simulator-record validation separate from trainer/live runtime policy.
ENV-001B now has a hash-locked simulator-record profile and macOS clean proof;
that lightweight profile and its lock remain unchanged. Broader work includes
PyTorch and platform-specific accelerator packages, but the recorded Windows
`neuralgpu` environment was populated before this repository policy and has not
been cleanly recreated. Existing Python, package, and CUDA versions are evidence
only, not compatibility claims.

### Decision Drivers

- Preserve macOS terminal Python and Windows Conda `neuralgpu` as the intended
  platform workflows.
- Keep the simulator-record profile small, hash-locked, and independent of
  trainer/live dependencies.
- Make Windows recreation depend on repository-owned metadata rather than the
  contents of an existing environment.
- Avoid implying one PyTorch artifact or accelerator policy works everywhere.
- Preserve the committed Node lock and `npm ci` policy.

### Options Considered

#### Option 1: One universal pip lock containing PyTorch

Use one pip-generated lock for the broader profile on macOS and Windows,
including PyTorch and accelerator packages.

Pros:
- One installation artifact and resolver workflow to maintain.
- Hashes could bind resolved package files for the represented targets.

Cons:
- A single lock would have to represent distinct operating-system wheels and
  accelerator choices without evidence that the targets are compatible.
- It risks turning one target's CPU/GPU resolution into a false cross-platform
  support claim.

#### Option 2: Platform/profile-specific pip locks or constraints

Keep common declarations in `pyproject.toml`, then generate separate locks or
constraints for each validated platform and profile.

Pros:
- Keeps simulator-record, macOS trainer/live, and Windows trainer/live
  dependency closures distinct.
- Allows PyTorch wheel and accelerator resolution to be verified per target.

Cons:
- Adds artifacts and resolver procedures that must stay aligned with the shared
  declarations.
- A pip lock alone does not recreate the Windows Conda interpreter environment.

#### Option 3: Shared declarations with a repository-owned Windows Conda GPU spec

Keep project dependency intent in `pyproject.toml` and add a Windows Conda
environment specification and generated lock for the `neuralgpu` runtime.
Maintain a separate pip lock for any broader macOS profile the project supports.

Pros:
- Preserves the existing Windows environment manager while making its clean
  recreation a repository-defined process.
- Lets Windows PyTorch and accelerator packages resolve for their target, while
  macOS terminal Python retains its own profile artifact.

Cons:
- Conda and pip artifacts introduce separate resolvers and require an explicit
  consistency check against the `pyproject.toml` declarations.
- More platform-specific metadata must be updated and validated together.

### Decision

Use the shared `trainer/pyproject.toml` declarations with separate
platform/profile resolution artifacts. Keep the existing simulator-record extra
and `trainer/requirements/simulator-record.txt` unchanged. For broader work,
create a macOS pip lock for any trainer/live profile the project chooses to
support and a repository-owned Windows Conda environment specification and lock
for `neuralgpu`; keep the Conda artifact a platform-specific resolution of the
shared declarations, not a replacement dependency authority. Do not publish one
universal PyTorch/CUDA lock or claim a tested Python or accelerator matrix until
clean recreation and compatibility checks establish it. Preserve the
`sim-core/package-lock.json` and `npm ci` policy.

### Consequences

**Positive:**
- Dependency intent stays in one project declaration while resolved runtime
  artifacts match the platform and profile being validated.
- The Windows workflow can remain Conda-based and become reproducible from
  repository metadata.

**Negative / Trade-offs:**
- Multiple locks/specifications and their resolver provenance require upkeep.
- Platform-specific PyTorch, accelerator, and Python compatibility must be
  maintained as separate evidence.

**Neutral:**
- Current host versions remain observations; this decision does not approve
  exact pins, a Python support range, or CUDA/runtime compatibility.
- Environment policy does not authorize dataset generation, training, model
  evaluation, or live inference; those remain separately gated by requirements
  and project status.

### Follow-up Actions

- [ ] In ENV-001C, declare broader trainer/live dependency groups in
  `trainer/pyproject.toml` without changing the simulator-record profile.
- [ ] Create repository-owned platform/profile artifacts: a macOS pip lock for
  any broader profile selected for support, plus a Windows Conda environment
  specification and generated lock that can recreate `neuralgpu` from a clean
  state.
- [ ] Resolve package pins and Python targets from native compatibility checks;
  determine PyTorch wheel/source and accelerator/CUDA runtime compatibility per
  platform. Record resolver inputs and outputs rather than copying installed
  versions.
- [ ] Recreate and validate Windows from repository metadata, then separately
  validate the macOS broader trainer/live profile if this decision supports it.
  Record commands, versions, results, and failures in
  `docs/refactor/ENVIRONMENT_VALIDATION.md`.

Follow-up status (2026-10-01): the broader macOS trainer/live profile, lock, and
documented focused clean proof are complete and accepted within that profile's
scope. The Windows Conda specification/lock, clean recreation, and
platform-specific trainer/live compatibility checks remain deferred. ENV-001
is not complete for cross-platform claims.

The proposed decision is recorded in this log; the follow-up status above is
current as of 2026-10-01.
