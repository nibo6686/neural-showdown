# Product Specification: Faithful Gen 9 Transition Capture and Battling AI

**Status:** Draft. This file is the product-behavior source of truth for the immediate capture milestone and records the longer-term AI goal separately. It does not accept a data, feature, training, or model milestone.

## Objective

**Immediate delivery milestone:** capture supported `gen9randombattle` transitions faithfully for each player using `observable-battle-state/v2`. A player capture consists of that perspective’s public protocol evidence through an exact event cursor, plus only that player’s current private request and legal actions. The capture must preserve evidence, privacy, temporal boundaries, and deterministic transition lineage; unsupported or unclassified forms stop publication explicitly.

**Long-term product goal:** provide a recommendation-only neural battling assistant for Gen 9 Random Battle singles. Start learning from legal replay-action imitation, with battle outcome/win rate as the ultimate objective. The current delivery milestone does not implement or authorize that model pipeline.

The pinned Pokemon Showdown simulator in `sim-core` is the authority for supported-format mechanics and source evidence. The current target format is `gen9randombattle`; this spec makes no claim about other generations or formats.

## Current Baseline and Status

Use [`docs/PROJECT_STATUS.md`](../PROJECT_STATUS.md) as the current readiness snapshot and each linked contract as the authority for its own field semantics. The detailed simulator inventory and active raw-protocol review are in [`SIMULATOR_COVERAGE.md`](../contracts/SIMULATOR_COVERAGE.md), [`MECHANICAL-REPRESENTATION-ASSESSMENT-2026-09-25.md`](../refactor/MECHANICAL-REPRESENTATION-ASSESSMENT-2026-09-25.md), and [`PIPELINE-002-GAP-DISPOSITION-2026-09-24.md`](../refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md).

- The repository pins `pokemon-showdown@0.11.10` and audits a Gen 9 Random Battle installation. The current source/reachability audit still has gaps; registry counts and source digests do not prove every reachable mechanic is classified.
- The current protocol review is blocked by a `-singleturn` Helping Hand `[of]` identifier shape accepted by the validators but not emitted by the pinned move callback. No replacement coverage digest or attestation has been recorded. Preserve the prior digest until the field rule is corrected and reviewed.
- `observable-battle-state/v2` and adjacent state/action/belief/transition/data contracts provide scoped foundations. They do not establish complete simulator-state projection, full-episode fidelity, a shared model feature schema, or a production inference path. `faithful_complete_episode:false` remains mandatory.
- Project status records narrow prior scopes for some pipeline work. Those records do not satisfy acceptance for this v2 capture milestone. `PIPELINE-001`, `PIPELINE-002`, and `FEATURE-001` must not be treated as broadly ready; complete-episode publication remains unaccepted.
- Existing replay feature paths are not decision-cursor safe: value examples apply all events in a turn before featurizing that turn; action-rank reconstruction uses a prior-turn context together with a whole-trajectory completed roster; the diagnostic materializer records an own-side future-public-reveal assumption. The live overlay also sends a bounded log tail without an accepted exact-cursor contract. These paths are historical evidence, not proof that the required decision-time state is correct. See `build_replay_value_dataset.py`, `build_action_rank_dataset.py`, and `benchmark_vnext_featuregen.py`.
- The overlay is currently recommendation-only. Existing checkpoints and vNext diagnostics are historical/isolated and are not prerequisites or approved inputs for this milestone.

## Non-Goals

- Claiming complete battle or complete-episode fidelity; changing `faithful_complete_episode:false`.
- Defining or integrating `FEATURE-001`, model input dimensions, training targets beyond the long-term direction below, model training, checkpoint promotion, or live model loading.
- Generating a dataset, downloading replays, or treating the existing replay-fetch route as readiness or authorization to collect data.
- Fetching or using an external Random Battle set catalog in the current implementation plan. Any such catalog is a future BeliefState hypothesis source requiring provenance, privacy review, and a separate decision.
- Folding beliefs, inferred sets, sampled hidden state, or simulator internals into `ObservableBattleState`.
- Supporting doubles, constructed-team building, other generations, or cross-format portability.
- Auto-selecting or submitting a battle action.
- Replacing Showdown mechanics with hand-authored approximations or silently treating an unknown mechanic as absent.

## Functional Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| REQ-001 | The immediate capture scope SHALL be `gen9randombattle` under the pinned `pokemon-showdown@0.11.10` implementation and its verified format metadata. Every capture SHALL record the exact format and source/dependency identity needed to interpret it. | P0 | The operative format configuration and its provenance need explicit coverage; see the current mechanical assessment. |
| REQ-002 | The system SHALL construct separate perspective-owned observations. Each observation SHALL combine the exact public protocol prefix available to that player with only that player’s current legitimate private request and request-derived legal actions. | P0 | Use per-side protocol evidence and private request state as the operational inputs. Never substitute rendered chat text or an opponent’s request. See [`OBSERVABLE_STATE.md`](../contracts/OBSERVABLE_STATE.md). |
| REQ-003 | `ObservableBattleState`, `BeliefState`, raw protocol evidence, and simulator-only state SHALL remain distinct. `ObservableBattleState` may contain sanitized public evidence and the acting player’s private request; beliefs may reference evidence by provenance; serialized player captures SHALL exclude hidden simulator fields, snapshots, seeds, rewards, and omniscient state. | P0 | No embedding of BeliefState or raw simulator snapshots in the observation. See [`BELIEF_STATE.md`](../contracts/BELIEF_STATE.md) and [`SEEDED_TRANSITION.md`](../contracts/SEEDED_TRANSITION.md). |
| REQ-004 | A player capture SHALL NOT expose unrevealed opponent roster members or hidden moves, items, abilities, stats, simulator-only transformation state, or future events. Publicly emitted transformation evidence may become visible only at its exact event boundary. | P0 | Public appearance and confirmed identity must remain distinct, including Illusion/`replace`; later reveals must not mutate earlier snapshots. |
| REQ-005 | Every observation and any future feature/belief update SHALL be bounded by an exact normalized protocol-record cursor, not a turn number. Evidence after that cursor—including later records on the same turn—SHALL NOT affect the earlier observation, belief, action context, or identity. | P0 | Request/action labels may be read from later replay records only as labels; they must not flow backward into the input state. `feature_cursor <= observation_cursor` remains the DATA-001 rule if a future feature contract is accepted. |
| REQ-006 | State fields SHALL distinguish unknown, known absent, and observed/present values. Missing opponent fields, unrevealed slots, unsupported priors, and absent events SHALL remain unknown unless a permitted source establishes absence. | P0 | Null/zero/false defaults are not evidence. Preserve field-specific provenance and knownness; do not infer legality from prior outcomes. |
| REQ-007 | Protocol and state semantics SHALL be grounded in the pinned Showdown source and exact supported format. The source audit SHALL classify relevant output/state forms as typed, validated raw-only, or explicitly unsupported, with source and coverage evidence. | P0 | The full inventories belong in the simulator coverage artifacts, not duplicated here. Static package-wide emitter presence alone does not establish Gen 9 reachability. |
| REQ-008 | The shared protocol contract SHALL receive a field-by-field schema-closure audit. For every field/token shape, record its type/grammar, visibility, source role, validation rule, and unsupported-stop behavior in both TypeScript and Python publication paths. | P0 | This is the first post-current-batch implementation slice. It includes request redaction and side-private routing rules. |
| REQ-009 | Unsupported, malformed, contradictory, or unclassified protocol/state forms SHALL fail closed before capture publication. A source-classified raw-only public form counts as captured when its record, cursor, and hash are preserved, but SHALL NOT be promoted to typed/model state by guesswork. | P0 | Emit a stable diagnostic with the record index/command and preserve the last committed boundary for forms that stop. Do not repair source text to make it validate. |
| REQ-010 | A transition capture SHALL use request-bound legal actions and deterministic simulator restoration/transition lineage. Stale, invalid, rejected, or unsupported candidates SHALL publish no successor and SHALL leave the committed snapshot, prefix, and lineage unchanged. | P0 | Use the existing SeededTransition and pipeline contracts only within separately verified scope; do not synthesize pass/default choices for waiting or requestless sides. |
| REQ-011 | TypeScript and Python SHALL validate the same capture semantics, schema versions, provenance, prefix extension, content identities, and publication joins. Cross-runtime differences in canonicalization SHALL follow the applicable versioned contract; no stale identity may be silently repaired. | P0 | Keep observation, belief, transition, and DATA-001 identity rules distinct. See [`DATASET_LINEAGE.md`](../contracts/DATASET_LINEAGE.md). |
| REQ-012 | Every stop, truncation, and unsupported scope SHALL be explicit. The implementation SHALL retain `faithful_complete_episode:false` until a separate complete-episode acceptance exists. | P0 | A successfully captured transition is not proof of a complete battle or training readiness. |
| REQ-020 | The long-term assistant SHALL rank only actions legal in the acting player’s current request and display recommendations without submitting a choice. | P1 | Product interaction remains recommendation-only, matching the existing overlay boundary. Not part of current capture acceptance. |
| REQ-021 | The long-term learning path SHALL begin with replay-action imitation and preserve terminal win/loss outcomes for later outcome-oriented learning/evaluation. The ultimate product objective is stronger battle win rate, not imitation accuracy alone. | P1 | Exact objectives, weighting, eligible replay regimes, and model interface remain future contract decisions. No training/data generation is authorized here. |
| REQ-022 | A future opponent BeliefState may represent coherent joint Randbats set hypotheses conditioned only on public evidence through the current cursor. Directly revealed facts must remain satisfied; if the source has no consistent candidate, preserve the contradiction and unknown tail rather than relaxing the reveal or inventing a hidden set. | P1 | BeliefState v1 is a snapshot contract, not a posterior algorithm. Any prior source needs its own version, checksum, coverage/quality, and privacy decision. External set catalogs are deferred. |
| REQ-023 | Future action scoring SHOULD represent candidate-specific risk from plausible hidden mechanics without turning a possibility into simulator truth or a hard action ban. | P1 | Examples include possible Unaware when evaluating setup into Dondozo, Choice Scarf among explanations for a surprising speed order, and unresolved Zoroark/Illusion identity until public reveal. These are examples of future belief-aware behavior, not current capture features. |

## User / System Flows

### FLOW-001: Capture one supported transition

1. The simulator provides the ordered public protocol records and each side’s current request boundary.
2. For each perspective, the projector validates the format, perspective/request ownership, request ID, protocol prefix, and `observable-battle-state/v2` schema.
3. The projector emits a separate immutable observation with public evidence, that side’s private request/legal-action set, exact cursor, and content-derived identity. Request JSON is transient and sanitized from the shared public prefix.
4. The transition runner validates request-bound choices and executes a disposable candidate using the authoritative Showdown simulator.
5. On success, the system projects both successor observations and validates prefix, snapshot, transition, and publication lineage before commit. On any failure, it emits a structured stop and keeps the previous boundary.

### FLOW-002: Reconcile a protocol or state form

1. The schema-closure audit maps a shared protocol field to pinned source emitters, type/visibility, validator, projection disposition, and stop behavior.
2. Scanner expansion and Gen 9 Random Battle reachability evidence determine whether the form is reachable in the supported format.
3. Typed forms receive explicit lifecycle semantics; raw-only forms remain evidence without typed interpretation; unsupported forms stop capture.
4. Changes to source, format metadata, validators, or coverage inputs require refreshed evidence and separate review before a new coverage attestation.

### FLOW-003: Future recommendation and belief flow (not current delivery)

1. A future inference path will consume a versioned player observation plus a separate, causally updated belief and current legal actions.
2. It will score only those legal candidates and show ranked suggestions to the user; the user submits any choice manually.
3. Future BeliefState priors and model features will carry source, version, evidence cursor, coverage, and uncertainty. No hidden simulator truth enters the player information regime.

### FLOW-004: Future replay imitation flow (not current delivery)

1. A future approved collector may parse public replay protocol and retain source/battle provenance.
2. Each action label will be matched against a legal candidate set reconstructed from the acting player’s information at the pre-action cursor. Unmatched or information-incomplete rows are quarantined, not repaired using the chosen action or later reveals.
3. Train/validation/test membership is battle-disjoint. Win/loss is retained as an outcome target/metric for a separately accepted objective.

## Data Model

| Entity / Object | Fields / source | Rules |
|---|---|---|
| `ObservableBattleState` v2 | Schema/source, battle ID, perspective, phase, exact event cursor/hash/prefix, public view, nullable acting-side request, decision availability | Player-facing evidence only; immutable snapshot; public opponent stages are in v2; request raw payload is omitted/redacted. The contract remains authoritative for exact field rules. |
| `ProtocolEvidencePrefix` | Ordered normalized public records; cursor is record count; canonical sanitized-prefix hash | Preserve record order and repeats. Keep malformed/unclassified forms as explicit stops. Do not treat `log_delta` or turn number as the full prefix. |
| `ChoiceRequestView` | Current player, request ID, wait/force-switch/preview state, active moves, own roster, legal mask/actions | Private to addressed player. Legal actions come from the current request; requestless/waiting states do not invent actions. |
| `BeliefState` | Separate schema, perspective, base observation reference, candidates/evidence/unresolved/contradictions and lineage | Hypotheses never appear in ObservableBattleState. v1 defines provenance/identity, not probabilistic propagation. |
| `SeededSnapshotRef` / `SeededTransition` | Opaque simulator snapshot reference, branch/transition identity, input/output fingerprints, seed and step lineage inside simulator boundary | Raw serialized battle state stays simulator-only; restoration and candidate commit are deterministic and atomic within the accepted scope. |
| Transition capture bundle | Input and successor observations for each perspective plus validated transition/publication references | A per-transition diagnostic/capture artifact is not a generated training dataset and is not a complete-episode claim. |
| Future `MetaPrior` / model artifact | Versioned source identity, joint hypotheses/unknown mass, observation and feature/action schema fingerprints | Not part of current delivery. External catalogs require a separate provenance and privacy decision. Existing feature dimensions/checkpoints do not define this schema. |

## API / Integration Contracts

| Contract | Direction | Input | Output | Current status / boundary |
|---|---|---|---|---|
| Pinned Showdown `sim-core` | Internal authoritative simulator | `gen9randombattle`, seed/snapshot, requests and legal choices | Per-player views/requests, public protocol delta, simulator transition result | Source of truth for supported mechanics. Source/format evidence and reachability gaps remain under review. |
| Shared protocol contract | Internal TypeScript/Python | Protocol record and field shape | Validated typed projection, raw-only evidence, or explicit stop | `trainer/src/neural/protocol_contract.json`; field-by-field closure audit is required. |
| `ObservableBattleState/v2` projector | Internal, per perspective | Player-legal view, addressed request, explicit sanitized protocol prefix and phase | Immutable v2 observation, decision availability, cursor/hash/identity | v2 is required for this milestone; unknown schemas/contradictions reject. |
| Seeded transition and publication bridge | Internal simulator → Python validator | Current observations/actions and opaque snapshot lineage | Successor transition/capture bundle or structured rejection | Existing contracts define narrower scopes. This milestone needs separate evidence; it does not confer PIPELINE or dataset readiness. |
| Legacy replay fetch/parser | External public replay service → local files | Format/query and replay metadata/log | Cached replay assets and parsed trajectories | Existing routes are not part of the current plan. Public logs lack complete private requests, hidden teams, and original PRNG state; availability does not establish training eligibility. |
| Legacy live `/evaluate` overlay | Showdown client → local recommender | Current private request/legal actions plus bounded log payload | Displayed recommendation | Historical/legacy route, not the exact-cursor v2 contract. The overlay does not submit choices. |

## Validation Rules

| ID | Rule | Applies To | Expected Behavior |
|---|---|---|---|
| VAL-001 | `format` must resolve exactly to the supported Gen 9 Random Battle format and pinned simulator evidence. | Session/capture | Mismatch or unverified format provenance stops capture. |
| VAL-002 | Perspective, view owner, request owner, and opponent complement must agree. | Observation/request | Contradiction fails closed. |
| VAL-003 | Cursor counts normalized protocol records; the prefix must be the exact ordered prefix through that cursor. | Observation/history | Rollback, truncation, reorder, altered earlier records, or hash-only claims reject. |
| VAL-004 | Raw request JSON never enters the public prefix, observation identity, or other player’s capture. | Requests/serialization | Keep only contract-approved request reference data in the observation; private fields remain on the addressed player side. |
| VAL-005 | Hidden simulator truth must not affect a player observation or player-regime belief absent public evidence. | Privacy/no-leakage | Hidden-state perturbation with identical allowed inputs yields identical player-visible serialization and identity. |
| VAL-006 | Unknown is not absent; absence is recorded only from evidence with a defined source and scope. | All state fields | Never coerce missing opponent fields or omitted protocol events to zero/false/empty-known. |
| VAL-007 | A prior observation cannot consume a later event, including a later event in the same turn. | Decision boundary | Earlier observation/belief ID and content remain unchanged when suffix events are appended. |
| VAL-008 | Every protocol/state form is classified before publication. | Shared protocol contract | Supported typed forms validate and project; supported raw-only forms remain raw-only; unsupported/unclassified forms stop with stable diagnostics. |
| VAL-009 | Candidate transition publication is atomic. | Transition runner | Rejection leaves committed snapshot, prefix, cursor, and lineage unchanged; no successor bundle is emitted. |
| VAL-010 | Restoration with identical serialized snapshot, seed, simulator revision, step and request-bound actions is deterministic under the pinned runtime. | Transition identity | Output branch/transition IDs, fingerprints, prefixes, and per-side successor observations match the contract. |
| VAL-011 | TypeScript and Python independently enforce exact schema and lineage rules. | Cross-runtime publication | Mismatched or stale identities reject; no padding, truncation, relabeling, or identity repair. |
| VAL-012 | Capture completion does not imply complete-episode completion. | Status/results | Keep `faithful_complete_episode:false`; unsupported boundaries carry an explicit stop/truncation reason. |

## Acceptance Checks

| ID | Source Requirement | Check | Verification Method |
|---|---|---|---|
| AC-001 | REQ-001, REQ-007 | Capture metadata binds to pinned `pokemon-showdown@0.11.10`, exact `gen9randombattle` format evidence, and reviewed source/data identities. | Coverage audit and format/source provenance review. |
| AC-002 | REQ-002, REQ-003 | For p1 and p2, output contains only that side’s public protocol evidence and current request; raw request bodies and the other side’s private fields are absent. | Mirrored serialization fixtures and Python publication validation. |
| AC-003 | REQ-004 | Hidden opponent roster/set, private stats, transformations, or simulator-state perturbations do not change a player capture unless corresponding public evidence changes. | Hidden-truth perturbation fixtures for both perspectives. |
| AC-004 | REQ-005 | Appending a same-turn suffix after a captured cursor does not alter the earlier observation, belief, hash, or identity. | Exact-prefix and immutable-snapshot fixtures. |
| AC-005 | REQ-006 | Unrevealed opponent slots/attributes remain unknown while explicitly request- or protocol-established absence is represented as known absent. | Knownness and missing-field fixture matrix. |
| AC-006 | REQ-007, REQ-008 | Every field/token in the shared protocol contract has type/grammar, visibility, source role, validation rule, and unsupported-stop disposition, with pinned-source references. | Completed schema-closure inventory reviewed against `protocol_contract.json`. |
| AC-007 | REQ-007, REQ-009 | Scanner and Gen 9 reachability review account for relevant emitted forms and state/effect registries; an unknown reachable form stops publication. The Helping Hand `[of]` mismatch is covered by a source-shaped regression before new attestation. | Source scanner, synthetic drift checks, source-generated controls, and semantic review. |
| AC-008 | REQ-009, REQ-010 | Unsupported, malformed, stale, or simulator-rejected candidates preserve the exact committed boundary and produce no successor publication. | Candidate rollback and explicit stop fixtures. |
| AC-009 | REQ-010 | Restoring the same boundary and replaying the same valid transition reproduces transition identity, fingerprints, prefix, and both successor observations. | Deterministic restoration/replay comparison under pinned sim-core. |
| AC-010 | REQ-011 | Python accepts valid TypeScript-produced capture bundles and rejects altered/stale observation, belief, transition, request, or protocol lineage without repair. | Cross-runtime fixtures and publication-validator review. |
| AC-011 | REQ-012 | Every unsupported boundary/result remains explicitly incomplete and reports `faithful_complete_episode:false`. | Result-envelope inspection and boundary matrix. |
| AC-012 | REQ-020 | The long-term overlay displays only current legal actions and never submits one. | Existing UI boundary/manual review; not a current-milestone gate. |
| AC-013 | REQ-021, REQ-022, REQ-023 | Future imitation examples use pre-action inputs, maintain battle-disjoint splits, and keep outcome targets and beliefs separate from observations. | Future FEATURE/data/model contract; no current data generation. |

## Implementation Slices

| Slice | Scope | Source Requirements | Verification |
|---|---|---|---|
| Current batch prerequisite | Resolve the active shared-protocol review blocker: reject or correctly model the impossible side-only Helping Hand `[of]` source shape; include the missing source-backed case and preserve the prior digest until the full review passes. Do not mark coverage newly attested before review. | REQ-007–REQ-009 | Source-emitter comparison, TS/Python negative and valid controls, rehashed publication regression, separate semantic review. |
| SLICE-001 — Schema-closure audit (first post-current-batch slice) | Classify every field/token in the shared protocol contract by type/grammar, visibility, source role, validation rule, and unsupported-stop behavior. Record explicit raw-only and unsupported cases and request redaction rules. | REQ-002–REQ-009 | Complete auditable inventory and cross-runtime validator map. |
| SLICE-002 — Scanner expansion and Gen 9 reachability | Expand source scanning to the uncovered nested effect/state registries and bind operative format/provenance evidence. Classify Gen 9 Random Battle reachable forms; retain other-format forms as explicitly out of scope rather than silently dropping them. | REQ-001, REQ-007–REQ-009 | Drift checks, source-backed reachability controls, updated coverage review. |
| SLICE-003 — v2 per-side capture closure | Close field-level projection and unknown/absent/lifecycle handling for the accepted public/request boundary; keep public opponent stages in v2 and preserve appearance/confirmed identity separation. | REQ-002–REQ-007, REQ-009 | Both-perspective fixtures, privacy perturbation, prefix/future-suffix and lifecycle checks. |
| SLICE-004 — Deterministic transition and publication parity | Validate restored candidate transitions, exact v2 input/successor observations, atomic commit/rollback, and Python publication parity using contract-bound identities. | REQ-009–REQ-012 | Deterministic replay, rejection preservation, TS/Python fixture parity, structured stop matrix. |
| Separate delivery prerequisite — ENV-001 | Reproduce the relevant build and focused validation from a clean environment with declared dependency/runtime policy. This is a separate gate, not a substitute for semantic coverage. | REQ-001, REQ-011 | Clean-environment evidence recorded in [`ENVIRONMENT_VALIDATION.md`](../refactor/ENVIRONMENT_VALIDATION.md). |
| Future, separately approved | Define FEATURE-001; then decide BeliefState prior provenance, replay eligibility, imitation/outcome objectives, datasets, training, evaluation, and live inference. No retrieval or generation begins from this spec. | REQ-020–REQ-023 | New contracts, privacy/provenance review, and explicit project-status gate. |

## Assumptions

- The current product boundary is Gen 9 singles with a recommendation-only overlay; the player remains in control of submitting a choice.
- The current milestone is faithful capture of supported per-side transitions, not a claim that every Gen 9 battle can be completed or that all internal simulator state is typed into the observation.
- A source-classified `raw-only` record counts as captured when its public record, position, cursor, and hash are preserved; it is not thereby a typed state feature.
- Public protocol evidence and the addressed player request are the only operational player-information sources. Existing overlay logs are bounded and do not yet satisfy the exact-prefix requirement.
- The latest project status document and normative contract pages take precedence over older artifact reports when describing readiness. Historical schemas/checkpoints are not adopted by default.
- External set catalogs are not used or fetched in this milestone. The selected direction for future Randbats hypotheses is the pinned Showdown generator; any precomputed prior artifact and any optional external supplement still require a separate version, coverage, provenance, and privacy decision.

## Open Questions

- **OQ-001 — Future learning objective details:** Action imitation is the starting target and battle outcome is the ultimate objective. The weighting, eligible replay population, and point at which outcome-oriented training is introduced remain undecided; this does not block transition capture.
- **OQ-002 — Future belief prior artifact:** The pinned Showdown generator is the selected source-of-truth direction for future Randbats hypotheses. The precomputed artifact format, sampling/convergence policy, coverage threshold, and whether an external catalog may supplement it remain separate decisions; no retrieval is part of this plan.
- **OQ-003 — Full episode boundary:** What separate evidence and review will authorize changing `faithful_complete_episode:false` is intentionally not answered by this transition-capture spec.
