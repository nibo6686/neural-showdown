---
name: wm-pr-review
description: Review a change against West Monroe quality, security, testing, and client-delivery expectations.
---

Review the current diff, staged changes, or referenced files using West Monroe engineering standards.

Structure the review in this order:

## Findings

List issues first, ordered by severity. For each issue include:

- severity (`high`, `medium`, `low`)
- impacted file or area
- why it matters
- recommended fix or follow-up

Focus on:

- behavioral regressions
- missing or weak tests
- security and data-handling risks
- maintainability issues that are likely to slow delivery
- API or UX inconsistencies

## Open Questions

- call out any assumptions that need clarification

## Change Summary

- include only after findings and questions
- keep it concise

Review against these expectations:

- the implementation solves the stated problem
- the code follows existing project patterns
- tests are sufficient for the risk of the change
- client-sensitive data is not mishandled
- comments and TODOs are intentional and minimal

If no material findings are present, say that explicitly and mention any residual risks or testing gaps.
