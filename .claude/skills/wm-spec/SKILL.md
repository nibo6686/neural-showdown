---
name: wm-spec
description: Generate an automation-friendly product specification from a raw requirement or feature brief.
---

Generate a structured product specification from the input context. If explicit input is provided, use it. Otherwise, use the most recent product brief, requirement, feature idea, or discussion context available.

Use this skill when the project is operating in a spec-first workflow. Do not also generate user stories unless explicitly requested.

Produce the specification in this format:

# Product Specification: [Short Title]

## Objective

[1-2 sentences describing the product outcome this specification supports.]

## Non-Goals

- [Capabilities, scenarios, or technical work intentionally excluded]

## Functional Requirements

Use stable requirement IDs.

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| REQ-001 | [System behavior or capability] | P0 / P1 / P2 | [Constraints, assumptions, or clarifications] |

## User / System Flows

### FLOW-001: [Flow Name]

1. [Actor or system action]
2. [System response]
3. [Expected outcome]

## Data Model

| Entity / Object | Fields | Rules |
|-----------------|--------|-------|
| [Name] | [Key fields] | [Validation, relationships, or persistence rules] |

## API / Integration Contracts

| Contract | Direction | Request / Input | Response / Output | Notes |
|----------|-----------|-----------------|-------------------|-------|
| [Endpoint, event, file, job, or integration] | Inbound / Outbound / Internal | [Input shape] | [Output shape] | [Auth, error, or dependency notes] |

## Validation Rules

| ID | Rule | Applies To | Expected Behavior |
|----|------|------------|-------------------|
| VAL-001 | [Rule] | [Field, flow, endpoint, or object] | [Pass/fail behavior] |

## Acceptance Checks

| ID | Source Requirement | Check | Verification Method |
|----|--------------------|-------|---------------------|
| AC-001 | REQ-001 | [Observable behavior] | Unit / Integration / Functional / Manual |

## Implementation Slices

| Slice | Scope | Source Requirements | Verification |
|-------|-------|---------------------|--------------|
| SLICE-001 | [Smallest useful end-to-end increment] | [REQ IDs] | [Checks or tests] |

## Assumptions

- [Assumption that affects delivery, design, or validation]

## Open Questions

- [Question that must be resolved before or during implementation]

After generating the specification, call out the riskiest assumption and the first implementation slice.
