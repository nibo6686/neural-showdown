# Project Status

**Current as of:** 2026-09-24
**Branch:** `refactor/state-001-observable-state`
**Workspace HEAD:** `b9b3eb06d362963bb1fa2da21d7c471a84df262c`

This page is the current status summary for the project. Detailed contract
requirements and historical review evidence remain in their linked documents.

## Readiness

| Gate | Status | Meaning |
|---|---|---|
| Refactor contract preparation | Complete for accepted items through SEARCH-001 | STATE-001, ACTION-001, FIXTURE-001/002, TRANS-001, BELIEF-001, DATA-001, and SEARCH-001 have recorded acceptance. |
| ENV-001 reproducibility | Blocked with remediation | Python dependency/lock and tested-runtime policy plus clean-environment validation remain unresolved. Optional raw replay fixtures are not required for the first simulator-only milestone. |
| SIM-COVERAGE-001 | Corrected lifecycle implementation awaits review | Prior attestation unchanged; checker reports digest and new -hint classification drift, six self-tests pass. Review combined changes and include helper/Illusion tests before attesting. |
| PIPELINE-001 | Accepted for explicit v1 joint-actionable scope | Natural hidden-trap simulator rejection and injected rejection both preserve committed state/lineage. Focused TypeScript tests pass 42/42; Python record/lineage tests pass 18/18. Complete episodes remain PIPELINE-002. |
| PIPELINE-002 | Prior slices accepted; Illusion corrections implemented pending review | Both reproduced failures corrected; real ownership/reveal/restoration/publication tests pass. Build, 126 TypeScript and 20 Python tests pass. Combined semantic review next; faithful publication remains unaccepted. |
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
2. Disposition SIM-COVERAGE gaps and define complete-episode boundary
   requirements. **Reporting, ordinary one-sided progression and bounded settling
   separately accepted. Bounded episode execution/outcomes and rejection recovery
   are accepted and attested. State corrections and fixes for the reproduced Illusion
   roster/replace and non-Stellar Tera re-entry corrections are now accepted and
   attested within their scoped evidence. Faint Tera and terminal-history restoration
   and minimal-v1 validation/restoration are now accepted and attested.
   Correct Stellar defensive typing next.
   Faithful publication and other lifecycle gaps remain unaccepted.**
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
