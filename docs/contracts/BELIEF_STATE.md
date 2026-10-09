# BeliefState Contract

Status: BELIEF-001 accepted (2026-09-23).

## Purpose and boundary

BeliefState v1 is a separate, perspective-owned snapshot of hypotheses,
evidence, and unresolved uncertainty. It is additive to
ObservableBattleState v1. The implementation is sim-core/src/belief_state.ts.
It does not mutate BattleView or ObservableBattleState, and it is never
serialized as an ObservableBattleState or copied into public observation
fields.

The legacy PokemonView possible_* arrays remain for compatibility. Their
meanings are mixed: possible_roles is prior-derived; possible_moves currently
records observed move history; possible_abilities records observed current
ability history; possible_tera_types is an unpopulated placeholder. V1 does
not infer provenance from those arrays or mutate BattleView to relocate them.
Existing consumers keep using their current inputs. Future adapters must
provide explicit evidence provenance.

BeliefState v1 is a snapshot contract, not a propagation algorithm. It does
not sample, rank, calibrate, or propagate hypotheses. Its supported candidate
categories are role, move, ability, item, and tera_type. Status is observable
state in the current contracts; no inferred-status producer was found in the
inspected TypeScript path, so status hypotheses are not introduced here.

## Schema and identity

The only supported schema version is belief-state/v1. Unknown versions fail
closed. Every snapshot has:

- belief_id: belief- plus SHA-256 of canonical serialization of the identity
  payload, excluding belief_id itself;
- information_regime: player or simulator_research;
- battle_id and perspective (p1 or p2);
- an exact base observation reference: schema version, observation ID, source
  kind, event cursor, protocol-prefix hash, and snapshot phase;
- a monotonic observation history, retaining each referenced prefix hash so
  imported evidence can be checked against its original observation boundary;
- the complete sanitized source protocol prefix, retained so parent snapshots
  can prove exact prefix extension and direct evidence can be revalidated;
- parent_belief_id, nullable;
- simulator_snapshot lineage, nullable, containing only branch ID, transition
  ID, state fingerprint, and parent branch ID; opaque handles and raw simulator
  state are excluded;
- simulator_snapshot_history, retaining the root snapshot and each linked
  output snapshot used to validate historical simulator-only evidence;
- transition lineage, nullable, containing transition ID, branch IDs, input
  and output fingerprints, simulator revision, step index, input observation
  ID, and output observation ID;
- the transition lineage history, so simulator-only evidence remains bound to
  a recorded transition after later linked steps;
- deterministically ordered candidates, evidence, unresolved entries, and
  contradictions.

Canonical serialization recursively sorts object keys, preserves array order,
uses UTF-8 JSON without insignificant whitespace, and has no wall-clock fields.
Before serialization, candidates sort by category, subject_key, value, then
candidate ID; evidence sorts by evidence ID; unresolved entries sort by
category, subject_key, then reason; contradictions sort by candidate ID; and
each evidence_ids array sorts by codepoint order. Equivalent input sets
therefore produce identical bytes and belief IDs. Duplicate identical
candidates/evidence are deduplicated by their content-derived IDs; conflicting
evidence is retained.

Snapshots are deep-cloned and recursively frozen. Extending a belief creates a
new snapshot whose parent_belief_id is the prior belief ID; an earlier
snapshot never changes.

Serialization and child projection revalidate imported snapshots instead of
trusting a matching unkeyed hash alone. Validation checks exact field sets,
observation and transition history, historical prefix hashes, evidence IDs and
provenance, derived-evidence references, candidate dispositions, contradictions,
and information-regime restrictions. The observation boundary also rejects
unknown or incomplete ObservableBattleState v1 fields, opponent-private view
fields, malformed non-request protocol records, raw/view contradictions, and
raw request JSON in retained protocol prefixes. Decision availability is
recomputed from the request and terminated view; a requestless observation
cannot claim that actions are available.

## Candidates, evidence, and uncertainty

A candidate is the tuple of category, subject_key, and value. Its deterministic
candidate ID is derived from those values. Candidate disposition is derived
only from explicit evidence:

- possible: no supporting or refuting evidence;
- supported: at least one supporting assertion and no refuting assertion;
- ruled_out: at least one refuting assertion and no supporting assertion;
- contradictory: both kinds of assertion exist; the conflict is retained in
  contradictions and is never resolved by overwriting either assertion.

Candidate lists are open-world. An omitted candidate, an absent reveal, an
unsupported prior dimension, an absent data source, or a missing field is not
negative evidence and cannot rule out a candidate. No v1 probability,
confidence, weight, or calibration field is defined. Existing Python posterior
weights remain in their existing APIs and are not silently promoted to
calibrated confidence.

Every evidence record has a deterministic evidence ID, category, subject key,
candidate value, explicit supports/refutes assertion, perspective, and one
provenance class:

- direct_observed: exact sanitized protocol record, base observation ID and
  exclusive event cursor, zero-based event index, and SHA-256 of that record;
- derived: derivation ID/version and parent evidence IDs, bound to an
  observation ID and cursor;
- prior_knowledge: source ID, source version, and source digest;
- simulator_only_truth: transition ID and simulator revision, admitted only
  when information_regime is simulator_research.

Direct evidence must quote the record at its cited index in the cited
observation prefix, and its observation ID and cursor must occur in the
snapshot's observation history. A cursor N contains records 0 through N-1, so event_index
must be less than N. New observation-derived evidence must cite the current
base observation exactly. A child snapshot may retain already validated parent
evidence only when the child observation is for the same battle and
perspective, has a nondecreasing cursor, and its sanitized protocol prefix is
an exact extension of the parent's prefix. New evidence from another
perspective, another observation, a stale cursor, a mismatched record, or a
future index fails closed.

Derived evidence must reference evidence IDs already present in the parent or
current evidence batch. Prior evidence keeps its source/version/digest.
Simulator-only truth cannot enter a player information regime. Hypothetical
belief-fork samples remain branch-local and are not actual observations.

Unresolved entries state a category, subject, and explicit reason such as
no_evidence, unsupported_prior_dimension, prior_unavailable, or
contradictory_evidence. V1 does not create refuting evidence from the absence
of observations.

## Observation and transition lineage

The base observation reference must be a complete ObservableBattleState v1
with its own perspective, cursor, and prefix hash. A parent belief must match
battle and perspective. The child's prefix must extend the parent's exact
sanitized prefix; cursor rollback, same-cursor prefix mutation, perspective
change, and battle change fail closed.

When a belief is linked to a seeded transition, the caller supplies the
transition metadata, the input observation ID from the transition request,
the output observation ID, and the opaque output snapshot reference. V1 checks
that the input ID matches the parent belief observation, the output ID matches
the child base observation, the parent branch matches the parent's snapshot
reference, and the child snapshot branch, transition ID, and fingerprint match
the transition metadata. Step index and simulator revision must advance
consistently. The current TRANS-001 metadata does not itself carry observation
IDs; this explicit join is caller-supplied lineage, not an engine attestation.
BeliefState v1 does not alter TRANS-001 behavior.

The separately accepted PIPELINE-002 ordinary forced-switch slice also accepts internal
`seeded-forced-switch/v1` metadata. It validates distinct acting/waiting roles
and an actor-only action-ID map, then projects the same existing per-perspective
lineage fields for both successor beliefs. Roles, action IDs and simulator seed
are not copied into player beliefs. The serialized belief schema remains v1;
this input extension passed separate semantic review on 2026-09-24 alongside the
[transition contract](SEEDED_TRANSITION.md), within its ordinary forced-switch scope.

The latest transition may precede the current observation when an exact
observation-only child is added. Its output observation remains in
observation_history; transition_history and simulator_snapshot_history must
remain consistent and the extended belief must remain serializable.

Replay and simulator event streams can have different record numbering; equal
numeric cursors do not make them interchangeable. Decision cutoffs use exact
observable prefixes. A turn-based replay cutoff is not treated as a
pre-decision boundary unless mapped to an exact record prefix.

## Unsupported and compatibility behavior

Malformed fields, unknown enum values, duplicate IDs with unequal content,
unsupported schemas, stale references, future evidence, cross-perspective
evidence, and contradictory transition/observation joins fail closed. The
v1 serializer contains only the separate belief schema. There is no implicit
conversion to ObservableBattleState and no public observation field can carry
BeliefState.

The initial implementation is shadow-only. It does not change simulator
mechanics, ObservableBattleState semantics, CanonicalAction v1,
seeded-transition behavior, existing feature vectors, checkpoints, live
defaults, search, or model training. It does not add belief propagation,
search integration, or model-input changes.

Rollback removes the BeliefState module, fixture/tests, this contract, and
their documentation links. Legacy BattleView fields, Python belief APIs,
belief-fork behavior, and all accepted work items remain intact.


### Public-stage observation compatibility — implementation, review pending (2026-09-25)

`belief-state/v1` may reference explicitly versioned observable v1 or v2. Its
observation/history references retain the actual version. TS validates v2 stage maps
against the exact public prefix and observation identity. Parent continuation across
versions rejects; regenerate a separate belief lineage from original evidence. V1
identity/serialization remains unchanged. See OBSERVABLE_STATE's v2 compatibility
section for historical Python reference normalization and regeneration requirements.


### Python identity correction — implementation, review pending (2026-09-25)

Python publication now verifies input/successor observation and belief content hashes
unconditionally for observable v1/v2, plus nested evidence/candidate IDs and reference
joins. It rejects stale IDs without repairing records. TS-compatible serialization
uses UTF-16 key ordering, JSON Unicode/surrogate escaping, binary64 numbers and distinct
absent/null fields. DATA-001's separate canonicalization remains unchanged.

Supported legacy v1 references may omit only schema_version while retaining all other
reference fields and valid content identities/history. Omission stays absent in hashing;
null/unknown versions, ID-only references and arbitrary IDs do not qualify. Full v2
references remain explicit. Historical records and lineage are never rewritten. Prior
Python synthetic unit fixtures now use content-bound IDs; they were not historical data.
Historical observation payloads cannot be recovered from references alone: validation
checks anchored prefix/history consistency, not unseen content. See the checkpoint for
new cross-runtime regressions and exact hashes. The prior downgrade blockers are
corrected in implementation; combined v2 acceptance/coverage attestation remain pending.


Review disposition (2026-09-25): the prior Python observation/belief identity failures
now reject, but combined v2 acceptance remains blocked. Historical reference source_kind
and snapshot_phase values must match TS's supported domains; Python currently accepts
invalid values for older entries when outer belief hashes are recomputed. See the
PIPELINE-002 checkpoint's two-transition reproduction. This does not expand the legacy
omitted-v1-version exception or establish broader publication readiness.


### Historical-reference field correction — implementation, review pending (2026-09-25)

Python validates the current reference and every history entry with one six-field
validator: exact keys, supported homogeneous observation version, strict observation
ID, source/phase domains, safe nonnegative cursor, and lowercase prefix digest bound
to that exact cursor. Histories remain nonempty, ordered, unique by observation ID,
anchored to supplied observations, and unchanged across the input/successor join.
The final entry must equal the current reference canonically. No coercion or repair.

Only otherwise complete v1 references may omit schema_version; hashes preserve actual
absence. V2 omission/null/unknown versions reject. Historical source/phase domains are
validated without requiring equality to current values. Valid records retain their
identities. TS additionally closes its first-history negative-cursor edge and requires
exact observation-ID length, preventing a trailing newline from matching a regex end
anchor. No valid producer output changes. Both previously accepted malformed-history
reproductions now reject. Combined v2 acceptance and attestation remain separate.


### Combined v2 publication acceptance — scoped (2026-09-25)

This verdict supersedes the preceding pending/blocked v2, Python identity and historical
reference dispositions only for their stated scope. Opt-in v2 public opponent stages,
content-bound observation/belief identities and complete six-field reference checks
are accepted. Default v1 and valid historical identities remain unchanged; only Python
supported v1 references may omit schema_version, without injecting it into hashes.
Negative first cursors and trailing-newline IDs reject as malformed. Rehashed false
stages still reject against public-prefix evidence; hashes alone are insufficient.

The 44-file coverage digest is attested:
`96e85e8903e00b681ce029b58d69d72c284595102bc1ffee855894779fcee11d`.
Fresh build/26 focused cases, independent original reproductions, coverage checker, ten
drift self-tests and three coverage tests pass; matching broader evidence is retained.
See the PIPELINE-002 checkpoint for exact scope and identities. Selective stage clears,
other excluded effects, feature extraction and broader lifecycle completeness remain
separate gates. `faithful_complete_episode:false` remains required.
