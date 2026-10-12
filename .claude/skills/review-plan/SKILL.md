---
name: review-plan
description: Use when reviewing an implementation plan before implementation begins. Supports an integrating author-session review with an opposite-model reviewer and a standalone findings-only review without file changes.
---

# Review Plan

## When to use

- Before implementing a plan — to surface structural or strategic risks that would cause rework.
- After drafting a plan — to validate that task scoping and scale assumptions hold against the real codebase.
- When reviewing someone else's plan — to provide grounded, evidence-based feedback.
- Complements `review-plan-tests` (test coverage gaps) and `draft-implementation-plan` (plan authoring).

## Inputs

- A plan file path (preferred), usually under `docs/planning/`.
- If no path is provided, find recent candidates in `docs/planning/` and ask the user to pick one.
- Optional mode: `--integrate` or `--findings-only`. Explicit mode always wins.

## Operational modes

### Integrating review

Use when the current session created or materially revised the target plan, or when the user explicitly requests `--integrate`.

- Prefer an opposite-model reviewer for the independent candidate-finding pass.
- The main agent verifies and adjudicates the candidates.
- `Accept` and `Revise` findings are approved findings. Incorporate them directly into the executable plan body and validation tasks.
- Do not incorporate `Reject` or `Needs User Decision` items. Report them to the user.

### Findings-only review

Use when the plan was authored outside the current session, including when the user manually opens another model and asks it to run `review-plan`, or when the user explicitly requests `--findings-only`.

- The current agent performs the code-grounded review directly. Do not delegate to another model.
- Return findings in the main session without adjudication dispositions.
- Do not modify the plan, append a review log, or write repository files.

If session provenance is unclear, default to findings-only.

## Workflow

1. Select the operational mode, then load the plan and identify all referenced codebase touchpoints, source materials, and dependency plans.

2. Run the review pass appropriate to the mode.

In integrating mode:
- Use a fresh, read-only reviewer. Do not let the reviewer edit the plan or any repository files.
- Prefer an opposite-model reviewer when its CLI is available, authenticated, and use of that provider is already authorized for the repository or session. From Codex, use Claude Code non-interactively with read/search tools only. Otherwise use a native fresh-context subagent.
- Give an external reviewer one attempt with a 20-minute hard wall-clock limit measured from process launch. A provider-specific cost or turn ceiling may supplement but must not replace the time limit.
- Prefer streaming output when the CLI supports it. Poll often enough to preserve user-visible progress at least every 60 seconds. Final-text mode may remain silent until completion; silence alone is not a failure while the process is alive and still within the time limit.
- Fail early on unavailable authentication, invocation failure, process exit without a usable result, or malformed/missing structured output. At the hard limit, terminate the attempt and fall back instead of waiting indefinitely.
- Give the reviewer the plan path, repository root, four review dimensions below, and the output contract. Do not include the main agent's tentative conclusions.
- If delegation is unavailable or fails, use a native fresh-context reviewer or perform the same candidate-finding pass as a distinct self-review, and disclose the fallback.

In findings-only mode:
- Perform the review directly in the current session.
- Do not invoke an opposite-model CLI or native subagent; the current session is the independent reviewer.

Reviewer output contract:
- Return up to 7 high-signal candidate findings without modifying files. If none clear the evidence bar, say so rather than padding the review.
- For each finding include: stable ID, dimension, impact (`High`, `Medium`, or `Low`), confidence, claim, specific code evidence (`file:line`), actionable recommendation, and any unresolved question.
- Distinguish evidence-backed findings from questions that require product or architectural judgment.

3. Explore referenced code in either mode.
- For each codebase touchpoint, have the reviewer read the actual implementation.
- Have the reviewer assess current scale profile: data loading patterns, pagination, indexing, memory usage, query strategies.
- Have the reviewer assess current abstraction complexity: how many layers, strategies, or extension points exist today vs what the plan assumes.
- Have the reviewer assess current test coverage: fixture sizes, edge case coverage, scale testing.
- Require every candidate finding to be grounded in what the code actually does, not what the plan claims.

4. Assess four dimensions.

**Scalability gaps:**
- Load-all-into-memory patterns the plan builds on or introduces.
- Missing pagination, batching, or streaming in read/write paths.
- Graph traversal, aggregation, or materialization steps without performance budgets.
- Scale targets stated as goals without baseline measurements.

**Brittleness and overengineering:**
- Abstractions forced to serve multiple unrelated consumers.
- Constraints that prevent necessary diagnostic or debugging paths.
- PR dependency chains deep enough to create stall risk.
- Identity, merge, or resolution models that are too rigid or too loose.

**Hand-waved complexity:**
- Tasks that bundle 3+ distinct implementation problems.
- Infrastructure that doesn't exist yet but is treated as a single task.
- Cross-system joins or correlation steps without mapping design.
- Fixture or test infrastructure requiring substantial effort but treated as implicit.
- Frontend work (especially interactive visualization) that is underscoped.

**Strategic fit and high-leverage simplification:**
- Plan assumptions that conflict with current business goals, product direction, or recently chosen strategy.
- Features, abstractions, compatibility paths, docs, or tests that can be removed instead of carried forward.
- Low-effort product-experience improvements that materially improve the planned outcome.
- Architecture or sequencing changes that avoid preserving obsolete PR-stack assumptions.
- For plans that introduce a new Evolve agent or agentic workflow, adherence to `docs/workflows/how-to-build-an-evolve-agent.md`: frontdoor entry, prompt/registry assets, scoped tool policy, retrieval strategy, trace/retrieval logs, reviewable output before writes, validation/evals, and deferred scaffolding.
- Do not add findings here just because the section exists; include only items that would materially change scope, sequencing, product outcome, or maintenance burden.

5. In integrating mode, adjudicate the candidate findings.
- The main agent owns the final review. Verify cited evidence and inspect additional code where needed.
- Assign each candidate one disposition: `Accept`, `Revise`, `Reject`, or `Needs User Decision`.
- Accept or revise only findings that clear the evidence bar and materially affect PR scope, sequencing, product outcome, or maintenance burden.
- Reject weak, duplicative, already-resolved, or category-driven findings. Report the rationale so the user can override the main agent's judgment.
- Treat a question as `Needs User Decision` only when repository evidence and existing guidance cannot resolve it and multiple credible choices remain.
- Produce no more than 7 accepted or revised recommendations. When findings exist, prefer 3-7, but do not pad. If more than 7 remain, recommend revising the plan rather than appending a laundry list.

6. In integrating mode, incorporate approved findings.
- Update the relevant goals, architecture decisions, task scope, PR boundaries, dependencies, validation criteria, and open questions in the plan body.
- Preserve task IDs and the required plan status format. Remove or revise superseded text so the plan remains internally consistent.
- Do not duplicate incorporated findings in a Review Findings appendix.
- Add a concise dated entry to an existing `Review History` section, or add that small section if absent, identifying the independent reviewer, adjudicator, and incorporated themes.
- Re-read the complete plan after editing and verify that no accepted recommendation remains only in commentary or history.

7. Evaluate whether interactive decision review would help.
- Significant ambiguity means either one unresolved `High`-impact decision or at least two unresolved `Medium`-impact decisions, with multiple credible options that would materially change architecture, product behavior, compatibility, data modeling, PR boundaries, or sequencing.
- Do not count missing facts, minor implementation details, or disagreements the main agent can resolve from code and repository guidance.
- When the threshold is met, recommend `review-to-html` and summarize the decisions it would contain.
- `review-to-html` is opt-in: do not invoke it or generate HTML without explicit user approval.

8. Summarize to the user.

In integrating mode:
- Report counts by dimension and disposition.
- Highlight the top 1-3 incorporated recommendations.
- Briefly explain material rejected candidates and all items needing user decisions.
- Return the updated plan path and, when applicable, the opt-in `review-to-html` recommendation.

In findings-only mode:
- List up to 7 findings with impact, confidence, code evidence, actionable recommendation, and unresolved question.
- State that the plan was not modified.

## Output requirements

- In integrating mode, approved findings change the plan body; do not leave the executable changes only in appendices.
- In findings-only mode, make no file changes.
- Delegated reviewers are used only in integrating mode, are read-only, and return candidate findings to the main agent; they never update the plan directly.
- Every finding must reference specific code evidence (file paths, line ranges, patterns observed).
- Recommendations must be actionable: split a task, add a prerequisite, remove a constraint, redefine a term.
- Strategic-fit and simplification findings must clear the same evidence bar as technical findings; avoid category-driven laundry lists.
- Existing historical review appendices may remain, but a new integrating review records only a concise Review History entry after incorporating approved findings.

## Notes

- If the plan references code that doesn't exist yet, note that as a hand-waved complexity finding.
- When multiple plans share a dependency, flag the cross-plan coupling risk.
- If the plan has no codebase touchpoints section, derive touchpoints from task descriptions and referenced files.
- Limit accepted or revised recommendations to 7 and do not pad. More than 7 signals the plan needs a rewrite, not a patch.
