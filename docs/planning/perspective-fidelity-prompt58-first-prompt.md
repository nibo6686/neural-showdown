# Prompt58 — reconcile decision requirements and the finite path to training

**Date:** 2026-10-14. **Status:** authorized read-only investigation and planning; no implementation or runtime validation.

## Objective

Produce one authoritative requirements-to-code reconciliation that answers: what information must the decision maker receive, what already works, what is missing, and which missing work actually blocks the proposed first training experiment? Explain the distinction between accepted 0.11.10 capture/public-state work and the stronger perspective-knowledge requirements. Replace stale roadmap assumptions with evidence, not another speculative implementation list.

Prompt57 is accepted and retained. The durable 0.11.11 candidate is:
`/Users/nbolger/Documents/Codex/2026-09-24/files-mentioned-by-the-user-neural/native11-recovery-2026-10-14/candidate`.

Original 0.11.10 sources/historical acceptances and target candidate capabilities are separate columns. Neither automatically inherits the other's acceptance. The consumer remains experimental and incomplete.

## Sources and scope

Read the product specification, perspective-knowledge contract and property/profile inventories, the implementation plan's FAC-01–08 and original audit matrix, the proposed ingestion strategy, and accepted reports relevant to each claim. Use source and focused test bodies to resolve discrepancies. Prompt43 records migration limitations; Prompt48/50/53/54/57 provide later adoption evidence that supersedes only their named parts. Historical documents may be stale; do not cite their tense as current capability.

Primary starting sources:

- `docs/requirements/spec.md`
- `docs/contracts/PERSPECTIVE_KNOWLEDGE.md` and its linked property/profile inventories
- `docs/planning/perspective-fidelity-implementation-plan.md`
- `docs/planning/perspective-fidelity-prompt3-matrix.md`
- `docs/planning/perspective-fidelity-prompt43-decision.md`
- Prompt48, 50, 53, 54 and 57 reports/lead decisions
- `docs/refactor/DATA_INGESTION_AND_TRAINING_STRATEGY.md` — proposal, not approved data policy

Follow existing indexes to other accepted mechanics evidence only when relevant. Do not reread every historical report or re-audit pinned Showdown wholesale.

## Required deliverable

Write one `docs/planning/perspective-fidelity-prompt58-reconciliation.md` in the original repository. No separate report, design, API, command matrix or resealing packet. Keep an executive summary readable without coding knowledge, followed by the evidence table and ordered backlog.

### 1. Requirements-to-code table

Account for every existing K01–K20 family and all explicitly required properties. Group properties only when source, lifecycle, adoption and disposition are identical; attach a compact inventory for exceptions so omitted properties cannot disappear inside a family label.

Each row must identify:

- Requirement ID/property, owner/opponent perspective, and original/current/request/public-history context.
- Why it matters to a decision or required guarantee. Distinguish a legitimate known fact from an inference, hypothesis or derived convenience.
- Legitimate source and precision; conditions where unknown/absence/inapplicability are truthful.
- 0.11.10 implemented/reviewed scope, with reusable evidence reference.
- 0.11.11 implementation and actual consumer availability, separately from tested/accepted scope.
- Disposition: available and adopted; available but unwired; implemented but proof missing; missing implementation; legitimately unavailable; or scope decision required.
- Concrete remaining gap and affected module/entry point; no generic “complete lifecycle” task.

Do not mark an owner-known required fact as safely unknown merely because the current adapter omits it. Conversely, do not require hidden opponent facts or recreate mechanics inside the information layer. Separate current ability identity from per-attack effectiveness; distinguish structured history from retained raw evidence and from model features.

### 2. Two finish lines and data regimes

Reconcile the existing full perspective-knowledge finish line without weakening FAC/K obligations. Separately propose a bounded first training experiment and list precisely where it falls short of that finish line. Any reduced profile, exclusions, feature encoding or eligibility policy is a proposed owner decision, not an accepted downgrade or training authorization.

Distinguish three regimes:

- Local native simulator: owned initialization, authentic requests and public chronology.
- Public replay alone: missing private facts/legal candidates and unresolved identity; limited eligibility.
- Verified input-log reconstruction: proposed source of human decisions, with availability/version/reproduction feasibility still unproved.

Do not assume public logs can yield complete own teams, that `.inputlog` is universally available, or that present-day npm equals the historical server. Identify which gaps depend on the chosen data regime. A local plumbing experiment does not prove human-data suitability or model strength.

### 3. Finite critical path

Return an ordered backlog of actual remaining work grouped by shared authority/writer/integration seam, not one prompt per mechanic. For each group name the outcome, reused modules/evidence, missing implementation, dependency, exact smallest future proof and why it blocks the chosen finish line. Separate mandatory correctness, integration, evidence-only work, optional features and deferred platform work.

Recommend the next useful implementation batch and identify owner decisions that change its scope. Include a concrete stop condition for the overall reconciliation: every requirement has a disposition, every mandatory gap has a named dependency/proof, and the experiment's remaining approval decisions are explicit. Do not invent numerical schedules or promise all properties can be closed in one batch.

## Execution and overhead limits

Read/search source, inspect recorded evidence and hash only disputed dependencies. No tests, builds, imports, battles, package installation, downloads/input-log fetching, benchmarks, dataset production or model loading. No production, contract, profile, manifest, aggregate-status or acceptance changes. Existing evidence is reused; uncertain runtime behavior is a named evidence gap, not an excuse to start tests.

Use two passes: inventory/dispositions, then critical-path and contradiction check. No recursive reviewer loop or independent rediscovery of every accepted mechanic. Keep consequential scope choices with the lead. If independent review is used, one read-only reviewer challenges the resulting table for omissions, false equivalence and unnecessary prerequisites; it does not repeat the inventory or run validation.

Return the single document and a short answer: what is already reusable, what was never completed, what the version change introduced, which gaps genuinely block the experiment, and the recommended next batch. Stop for lead decision. No commits, publication, promotion or training authorized.
