---
name: wm-qa-plan
description: Create a concise QA plan, scenario matrix, seed-data approach, and smoke-test checklist.
---

Generate a QA and demo validation plan from the available product specification, requirements, stories, acceptance checks, or acceptance criteria.

Produce the output in markdown using the following structure:

# QA Plan

## Scope

[What is being validated and what is intentionally out of scope]

## Test Strategy

- Unit tests
- Integration / API tests
- Functional smoke tests
- Demo readiness checks

## Scenario Matrix

| ID | Scenario | Type | Preconditions | Steps | Expected Result |
|----|----------|------|---------------|-------|-----------------|
| QA-1 | [Scenario] | [Unit / Integration / Functional / Demo] | [Setup] | [Steps] | [Outcome] |

## Demo Data Plan

- [What records should exist before the demo]
- [How to seed or reset them]

## Exit Criteria

- [ ] Critical user flows pass
- [ ] Acceptance checks or acceptance criteria are covered
- [ ] Seed data is available and realistic for the demo
- [ ] Known issues are documented with impact

## Recommended Smoke Test Script

```bash
[Commands to run before or during the demo]
```

## Known Risks / Manual Checks

- [Items that still require human judgment or exploratory validation]

Prefer concise, execution-ready checks over theory. Highlight the minimum viable set needed for a credible live demo.
