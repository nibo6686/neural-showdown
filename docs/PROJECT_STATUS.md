# Project Status

**Current as of:** 2026-09-28
**Branch:** `refactor/state-001-observable-state`
**Reviewed implementation state:** HEAD `a2ef3a6c3d2c27bb396bc55fc7dc10a0fcc29c2c` plus the staged protocol-boundary batch and unstaged review/correction work. The prior 54-file digest remains the accepted Psych Up state. Bounded base Topsy-Turvy semantics are reviewed. The raw-record repair correction and active `-transform` target rule are verified. Scoped review is blocked because Helping Hand `[of]` currently accepts an inactive side-only source identifier that pinned Showdown cannot emit in the move callback; a fully rehashed v2 candidate reaches DATA-001 publication. The focused suites pass but omit this source-incompatible shape. No coverage attestation or digest change was made. See the [mechanics assessment](refactor/MECHANICAL-REPRESENTATION-ASSESSMENT-2026-09-25.md) and [PIPELINE-002 checkpoint](refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md).

This page is the current status summary for the project. Detailed contract
requirements and historical review evidence remain in their linked documents.

## Readiness

| Gate | Status | Meaning |
|---|---|---|
| Refactor contract preparation | Complete for accepted items through SEARCH-001 | STATE-001, ACTION-001, FIXTURE-001/002, TRANS-001, BELIEF-001, DATA-001, and SEARCH-001 have recorded acceptance. |
| ENV-001 reproducibility | Existing-machine validation passed; fresh-machine recreation pending | macOS terminal Python and Windows neuralgpu validation passed; selected scenarios matched at `117df85`. Dependency/lock/runtime policy and clean recreation remain pending. See ENVIRONMENT_VALIDATION for working commands. |
| SIM-COVERAGE-001 | Prior Psych Up attestation preserved; raw player-identifier review blocked | Raw TS/Python validation rejects malformed terminal actors without repair, and `-transform` targets require active player identifiers. A side-only Helping Hand `[of]` source is accepted by both validators and by a fully rehashed v2 publication candidate; this conflicts with the pinned active move source. The 224/856 matrix passes but omits that shape. Preserve the prior digest; no new attestation. |
| PIPELINE-001 | Accepted for explicit v1 joint-actionable scope | Natural hidden-trap simulator rejection and injected rejection both preserve committed state/lineage. Focused TypeScript tests pass 42/42; Python record/lineage tests pass 18/18. Complete episodes remain PIPELINE-002. |
| PIPELINE-002 | Prior scopes retained; raw identifier review blocked | Projection validates terminal actor records without repair, and both runtimes enforce the active `-transform` target form. Helping Hand `[of]` still accepts side-only IDs contrary to the pinned source and can pass rehashed publication. Preserve the prior digest. After this field rule is corrected and reviewed, scanner expansion and operative format coverage remain the next batch. `faithful_complete_episode:false`. |
| FEATURE-001 | Unresolved; no accepted feature contract | Feature schema, extraction semantics, privacy/information regime, target, reward, and model interface are not finalized. |
| New dataset generation | Not ready / not performed | DATA-001 defines lineage; PIPELINE-001 records use the `features-not-produced/v1` sentinel. No new refactored-model dataset has been generated. |
| New model training | Not ready / not performed | Training objective, feature schema, and reproducibility gates are unresolved. |
| Live evaluation of a new model | Not ready / not performed | The real `/evaluate` route has not been verified for the refactored interface. |

Existing legacy model checkpoints are intentionally abandoned for the new
approach and are **non-blocking**. Their availability or quality is not a gate
for designing or training a new model. This status does not promote any legacy
or vNext checkpoint.

## Current work sequence

1. Complete deterministic protocol and stopping-behavior fixes. **Complete.**
2. Disposition remaining SIM-COVERAGE gaps and define the faithful transition
   boundary. **Scoped identity/type/stage and progression work remains as
   accepted in its cited reviews; bounded Topsy-Turvy semantics are reviewed.
   Raw player-identifier projection repair is corrected, but the shared review
   is blocked by Helping Hand accepting a side-only `[of]` source. Preserve the
   digest until the boundary is corrected and reviewed. Scanner expansion and
   operative format/provenance coverage are the next batch. Faithful
   complete-episode publication remains unaccepted.**
3. Review PIPELINE-001 with an explicit supported scope and rejection
   guarantees. **Accepted for v1 scope.**
4. Remediate ENV-001 reproducibility in parallel.
5. Define the training objective and information regime together with
   FEATURE-001 and the model interface.
6. Implement feature extraction and a bounded collector, then validate a pilot
   dataset.
7. Train a new model and evaluate it on held-out data.
8. Integrate live/search use and complete operational hardening.

## Promotion milestones

- **Dataset milestone:** accepted episode/boundary policy, ENV-001 clean-run
  evidence, accepted feature and target contracts, bounded collection, and an
  immutable pilot manifest with battle-disjoint splits and privacy, legality,
  cursor, transition, and distribution checks. A partial episode is either
  completed or recorded with an explicit truncation reason; it is never silently
  counted as complete.
- **Model milestone:** frozen dataset and split manifest, recorded objective,
  information regime, training configuration and seeds, reproducible training,
  and held-out evaluation against declared baselines with source-specific
  results and inference-schema compatibility.
- **Product-release milestone:** verified live/search contract integration,
  operational and security review, latency/resource limits, observability,
  deployment/rollback evidence, and an accepted product boundary. Training a
  model alone does not establish release readiness.

No completion percentage or schedule is asserted; the remaining decisions and
validation gates do not support either.

## West Monroe review evidence

[`refactor/WEST_MONROE_REVIEW_EVIDENCE.md`](refactor/WEST_MONROE_REVIEW_EVIDENCE.md)
indexes available contracts, implementation and verification evidence, and
remaining review needs. No West Monroe internal standard was supplied for this
work, so the index is preparation evidence and makes no compliance claim.

No dataset, training run, replay download, checkpoint fetch, or live evaluation
is authorized by this status page.

## Current references

- [Refactor gate and accepted work](refactor/STATUS.md)
- [Work-item register](refactor/WORK_ITEMS.md)
- [Environment blocker](refactor/ENVIRONMENT_VALIDATION.md)
- [Pinned simulator state/protocol coverage](contracts/SIMULATOR_COVERAGE.md)
- [Remaining mechanics assessment and implementation plan](refactor/MECHANICAL-REPRESENTATION-ASSESSMENT-2026-09-25.md)
- [PIPELINE contract and accepted reporting scope](contracts/PIPELINE_INTEGRATION.md)
- [Current PIPELINE-002 checkpoint](refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md)
- [Accepted observation contract](contracts/OBSERVABLE_STATE.md)
- [Accepted DATA-001 lineage contract](contracts/DATASET_LINEAGE.md)
- [Current continuation checkpoint](refactor/CONTINUATION.md)
- [Historical Codex review log](codex_review_state.md)

## Documentation policy

Dated reports under `artifacts/` record the state of their original experiment
or review. They are historical evidence, not current readiness gates, unless a
current control document explicitly adopts them. Do not rewrite old metrics or
acceptance results to imply they apply to the new pipeline.
