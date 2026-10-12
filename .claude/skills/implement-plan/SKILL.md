---
name: implement-plan
description: Execute one assigned reviewable implementation boundary from a plan and return a locally validated candidate. Publish only after explicit user or governing-lead review and authorization; do not govern the initiative or continue the stack automatically.
---

# Implement Plan

Execute one reviewable implementation boundary from a plan. The user or governing workflow owns the broader objective, execution context, sequencing, publication, and continuation decisions. This skill owns implementation and local validation for the assigned boundary.

Under `project-lead`, return coherent commits, validation evidence, changed assumptions, unresolved findings, and proposed plan changes. Do not push, open a PR, delegate again, or decide the next boundary unless explicitly authorized. A direct user request for a ready-for-review PR authorizes publication after local review.

When invoked directly without a boundary, derive the smallest sensible reviewable boundary from the plan and state it before implementation. Do not continue into the next PR merely because it is ready.

## Establish the execution contract

1. Read the plan, its current status, validation criteria, and PR/review strategy.
2. Confirm the assigned boundary, worktree, branch, base, required proof, and authority for commits, delegation, push, and PR creation.
3. Verify that the plan and execution context fit current branch and PR state. Return conflicts to the lead rather than choosing a different branch, stack, or plan version. Under direct invocation, resolve ordinary context and ask only when competing sources would materially change the work.
4. Treat the plan as the execution record for this boundary, not as authority to override the user's outcome, current evidence, or a governing workflow. Return for reassessment when they materially conflict.
5. Follow an explicit deployment or rollout model from the plan. If it is absent and the distinction affects implementation, surface the assumption rather than inventing transition scaffolding.
6. Preflight required tools and live gates. For environments outside the worktree, verify imports resolve to the current checkout before trusting tests.

## Execute the boundary

- Work in the assigned worktree, branch, and base. Verify ancestry and dependencies, but return stale or incompatible context to the lead rather than restructuring the stack. Under direct invocation, choose the smallest safe arrangement within the user's authority.
- Make the smallest coherent change that advances the assigned scope. Keep unrelated cleanup out.
- Respect the caller's work split. Under a governing workflow, delegate only when the assignment permits it; otherwise propose a split to the lead. Under direct invocation, use `route-agent-work` only when its benefit exceeds briefing, context-transfer, integration, and validation costs.
- Own local integration of the assigned change. Return material shared-contract decisions, cross-lane integration, acceptance, and PR readiness to the governing lead. Stop parallel work when hidden dependencies or write conflicts appear.
- After meaningful increments, run focused verification, inspect the diff for regressions and scope creep, use `simplify-code` where it adds value, update durable documentation when behavior or operator guidance changed, and commit coherent validated increments.
- Remove temporary scaffolding and execution-history comments. Report follow-ups and validation gaps with evidence and a recommendation; let the lead decide durable tracking and ownership. Do not create a second ledger.

Return before continuing when evidence materially changes the outcome, architecture, scope, sequence, risk, or required proof. Include the evidence and a recommended next action.

## Return factual plan evidence

- When the plan is part of the assigned write set, mark factual completion and validation for the assigned tasks.
- Return proposed phase, milestone, PR-strategy, debt, and next-boundary changes to the lead. Under direct invocation, apply them within the user's authority.
- When the assigned boundary proves too large, stop at the smallest coherent safe slice and return the candidate, evidence, and proposed plan delta. Do not independently redefine the stack, publish, or begin follow-on work.

## Prepare the review candidate

Before returning the boundary for lead or user review:

1. Review the full boundary for behavioral regressions, missing tests, architectural drift, accidental complexity, documentation gaps, temporary scaffolding, and scope creep.
2. Fix justified in-scope findings. Report the evidence, impact, and recommended disposition of the rest. The lead adjudicates material deferrals, non-fixes, and ownership; under direct invocation, adjudicate them within the user's authority before publication.
3. Start with focused tests and expand to lint, type, integration, evaluation, browser, migration, or broader suites when the plan gates or blast radius require them.
4. Validate the assigned result and identify integration or live gates the lead must still run. Worker checks do not establish initiative acceptance.
5. Prepare a concise implementation handoff covering scope, commits, changed assumptions, validation, unresolved findings, and proposed plan changes. Do not prepare the full PR package before lead or user review.

## Publish the boundary

Publication is a separate checkpoint from implementation:

- Under a governing workflow, return the local candidate first. Do not push or open a PR until that lead has reviewed the diff or commits and explicitly authorizes publication.
- Under direct invocation, publish only when the user explicitly requested a ready-for-review PR or authorizes publication after seeing the candidate.
- Apply directed revisions and approved finding dispositions. Once authorized, use [references/pr-notes-template.md](references/pr-notes-template.md) to finalize the PR package, then push and open a ready-for-review PR against the approved base. Use a draft only when requested or not yet reviewable.
- Never hide a material unresolved finding or describe missing external validation as passed.

If authentication or permissions block authorized publication, report it and return the candidate and finalized PR notes. Completing this boundary does not authorize the next boundary, merge, or deployment.

## Return

Report scope, branch and commits, validation, changed assumptions, proposed or applied plan updates, notable findings, and the recommended decision. After authorized publication, also report PR state. Distinguish validated results from assumptions and unavailable gates.
