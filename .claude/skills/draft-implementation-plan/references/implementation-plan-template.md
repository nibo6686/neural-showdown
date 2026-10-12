# Implementation Plan: <Title>

**Status:** Draft
**Last Updated:** <YYYY-MM-DD>

## Source Materials

- [<primary-source>](<path>) - <why it materially affects scope or validation>
- [<supporting-source>](<path>) - <why it materially affects sequencing or review>

Omit this section when the plan only has one obvious source or when extra source context would add noise.

## Status

- Completed: [<completed PRs or tasks>]
- In Progress: [<active PRs or tasks>]
- Remaining: [<planned PRs or tasks>]

Use this section for prerequisite context or non-PR work that materially affects execution.
Do not repeat the full PR-by-PR execution state here when `## PR Status` or `## Phase Status` already covers it.

## PR Status

| PR | Scope | Status | Depends On | Validation Gate |
|---|---|---|---|---|
| `PR-01` | <short scope> | Not Started | - | <required gate> |
| `PR-02` | <short scope> | Not Started | `PR-01` | <required gate> |

Use `## Phase Status` instead only when the source explicitly requires broader program phases that span multiple PRs or milestones.
Never use phases as subdivisions inside a single PR; use tasks instead.

## Goal

<One short paragraph describing the delivery target.>

Avoid extra summary sections that only restate scope, constraints, or PR tasks unless they add non-redundant execution guidance.

## Final Acceptance Contract

Use this section for multi-PR plans that combine into one user-visible workflow or one shared architecture contract. Omit it for simple single-PR changes where the PR validation criteria are already the full definition of done.

The stack is complete only when:

- `FAC-01`: <end-to-end user workflow or architecture contract works>
- `FAC-02`: <production path is exercised; list any allowed fakes>
- `FAC-03`: <critical integration/contract is proven across PR boundaries>
- `FAC-04`: <known high-risk failure mode is prevented or explicitly owned>

## Scope and Constraints

- In scope: <item>
- Out of scope: <item>
- Constraint: <technical or product constraint>
- Deployment model: <all-at-once by default; staged only when explicitly required>
- Assumption: <assumption that shapes the plan>

## Implementation Shape

Use this section when the runtime or pipeline execution point is not obvious.

- Execution seam: <where the work actually runs in the system>
- Existing path vs new path: <extends existing phase/call or adds a new one>
- Sequencing: <what must happen immediately before and after>
- Optional fallback: <only when a second path/call exists and materially affects behavior>

Omit this section when the control flow is already obvious from the PR tasks.

## Codebase Touchpoints

| Area / File | Planned Change | Test Impact |
|---|---|---|
| `<path-or-module>` | <create / modify / investigate> | <unit / integration / e2e impact> |

## PR / Review Strategy

- `PR-01`: <smallest reviewable PR>, with gate <required validation before review or merge>, previous PR <none / link>, next PR <PR-02 / link / none>
- `PR-02`: <next PR>, with dependency on <PR-01>, previous PR <PR-01 / link>, next PR <PR-03 / link / none>
- Stacking: <single PR / stacked PRs recommended / independent PRs acceptable>
- Merge guidance: <what must land before downstream work starts>
- Exclude: commit cadence, push timing, and other execution-only mechanics

## Parallel Execution Notes

- Critical path: <tasks or PRs that gate the rest>
- Parallel lane: <work that can proceed concurrently once a prerequisite exists>
- Serialization point: <shared contract, migration, or dependency that forces ordering>
- Coordination note: <where teams or PRs must align>

When control flow spans multiple stages, fallback paths, or mixed deterministic/LLM behavior, consider adding a separate Mermaid workflow or sequence diagram document alongside the plan.

## PR 1: <Name>

**PR ID:** `PR-01`
**Status:** Not Started
**Objective:** <what this PR delivers>
**Depends On:** <none or dependency list>
**Parallelism:** <what can run now vs what must wait>

### Tasks

- [ ] `P1-T01` <concrete implementation task>
- [ ] `P1-T02` <concrete implementation task>
- [ ] `P1-T03` <test or validation task>

### Validation Criteria

- [ ] <unit-level proof>
- [ ] <integration or wiring proof>
- [ ] <end-to-end or user-visible proof>

### Risks / Open Questions

- <risk, dependency, or unresolved decision>

Omit this subsection when there are no PR-specific risks or questions beyond the document-level `## Open Questions`.

## PR 2: <Name>

**PR ID:** `PR-02`
**Status:** Not Started
**Objective:** <what this PR delivers>
**Depends On:** `PR-01`
**Parallelism:** <what can run now vs what must wait>

### Tasks

- [ ] `P2-T01` <concrete implementation task>
- [ ] `P2-T02` <concrete implementation task>
- [ ] `P2-T03` <test or validation task>

### Validation Criteria

- [ ] <unit-level proof>
- [ ] <integration or wiring proof>
- [ ] <end-to-end or user-visible proof>

### Risks / Open Questions

- <risk, dependency, or unresolved decision>

Omit this subsection when there are no PR-specific risks or questions beyond the document-level `## Open Questions`.

## Cross-Cutting Validation

- [ ] Final Acceptance Contract item(s) `<FAC-id>` are proven by <test/eval/manual workflow evidence>.
- [ ] Unit tests cover the new local behavior.
- [ ] Wiring or integration tests prove the production path uses the new behavior.
- [ ] End-to-end or realistic scenario coverage proves the user-visible outcome.
- [ ] Error-path validation covers missing config, invalid inputs, or partial failures.

## Open Questions

- <question that must be answered before or during implementation>
