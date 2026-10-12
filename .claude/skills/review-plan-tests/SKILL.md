---
name: review-plan-tests
description: Use when auditing a planning or design document for missing integration tests, wiring tests, and end-to-end data-flow validation before implementation starts.
---

# Review Plan Tests

## When to use

Use this skill when a user asks to review a plan for test coverage gaps or to strengthen test requirements before implementation.

## Inputs

- A plan file path (preferred), usually under `docs/planning/`
- If no path is provided, find recent candidates and ask the user to pick one

## Workflow

1. Locate the plan.
- Try explicit path from user first.
- Fallback search: recent `*.md` files in `docs/planning/`.

2. Decompose planned changes.
- Identify each functional change and the data/contracts it touches.
- Track boundaries: input parsing, processing, persistence, retrieval, API/UI output.

3. Check for required test layers per change.
- Unit tests for local behavior.
- Wiring tests proving new helpers are called in production paths.
- Integration tests for cross-module data flow.
- End-to-end test with realistic data and user-visible assertion.
- Error-path coverage for failures and null/empty/invalid results.
- For eval-sensitive plans such as new language support, AST/provider onboarding, prompt/extraction-quality changes, or resolution/entity-quality work, also check for bounded `tests/evaluation/` coverage that is introduced or extended in the same phase as the implementation.
- For language or framework support claims, check for a bounded
  extraction/resolution canary that runs before any full-corpus scan. Accept a
  checked-in fixture, `tests/evaluation/` case, or pinned source subset when it
  proves basic production-path extraction, evidence persistence, and
  representative same-file/cross-file resolution for the claim.

4. Flag anti-patterns.
- Island testing (components tested in isolation only).
- Mock-only tests with no real wiring verification.
- Helper tests with no caller-path proof.
- Happy-path-only coverage.
- Missing verification checkpoints between related tasks.
- Evaluation work deferred to a final validation PR instead of being used as a per-phase gate where evals are the main quality signal.
- Full repository or customer-style scan listed as the first validation gate
  for language support, with no smaller canary that can catch basic extraction
  or resolution failures early.

5. Produce a gap report.
- Severity-ordered findings.
- For each finding: missing test, risk, required test shape.
- Include a checklist the implementer can use task-by-task.

6. Offer plan patch.
- Add explicit “Required Tests” under each relevant task.
- Add verification steps between implementation tasks.
- For eval-sensitive plans, add explicit phase-gated eval slices and note when they should be red before implementation and green after.
- For language support plans, add the smallest claim-matched canary gate that
  can run during implementation before broader scans.

## Output template

```markdown
## Integration Testing Gap Analysis

### Summary
...

### Critical Gaps (Must Fix Before Implementation)
1. ...

### Recommended Improvements
1. ...

### Test Checklist for Implementation
- [ ] Unit tests
- [ ] Wiring tests
- [ ] Integration data-flow tests
- [ ] End-to-end realistic scenario
- [ ] Error-path assertions
```

## Notes

- Prefer concrete test names/locations in this repo (for example under `tests/toolkit/` or `tests/hub/`).
- When evals are the right validation mechanism, prefer concrete `tests/evaluation/` targets, fixture families, and ground-truth locations rather than vague “run evals later” wording.
- Keep recommendations scoped; avoid broad refactors while improving testability.
