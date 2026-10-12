---
name: architect-pr-review
description: Review one pull request or a PR stack directly for architectural, business-goal, integration, validation, and maintainability risks. Use when the user asks for an architect-level PR review, architecture review, stack-aware architecture review, broad PR review, senior review, or review beyond ordinary bugs/style/CI triage.
---

# Architect PR Review

Use this skill to review a PR or PR stack as an architect: read the change, understand the intended goal, investigate the highest-risk design questions, and return grounded review findings. This is different from `pr-triage` and `stacked-pr-sweep`: do not focus on merge-readiness mechanics, CI status, rebasing, or clearing review comments unless those signals affect architectural risk.

When the review needs the full question repertoire or apprenticeship framing, read `references/review-judgment-rubric.md`.

## Inputs

- Repository path, default `.`
- PR number, URL, stack/list of PRs, or current branch PR
- Optional plan, Jira ticket, design note, or stated business goal
- `gh` authentication when the PR is on GitHub

## Workflow

1. Resolve PR or stack context.
- Prefer explicit PR numbers, URLs, or a user-provided stack list.
- Otherwise use the current branch PR.
- If the current PR is based on another feature branch, or the user asks for a stack review, resolve the stack root-to-leaf from base/head branches.
- Capture title, author if available, base branch, head branch, changed files, additions/deletions, linked issue/plan references, and PR description for each PR in scope.
- If GitHub context is unavailable, compare the current branch against the likely base branch and state that limitation.

2. Read for intent before findings.
- Read the PR description, linked plan or ticket, and any touched docs.
- Identify the intended technical and business outcome in one or two sentences.
- If the intent is unclear, continue the review but list that as an open question.

3. Build the changed-surface map.
- Group touched files by subsystem: CLI, orchestration, codemap, extraction, resolution, evidence, Hub API, frontend, docs, tests, workflow/CI.
- For each group, identify central contracts changed: public functions, schemas, models, registries, prompts, config, persisted data, command behavior, or UI workflows.
- Read nearby implementation and tests, not only the diff, before judging a contract change.
- In stack review mode, build both a stack-level changed-surface map and a per-PR map.

4. Select review lenses.
- Apply only the lenses that match the changed surface. Prefer a few deep investigations over a checklist dump.
- Use these default lenses:
  - Performance and scale for DB, IO, graph traversal, loops, scans, batching, and materialization.
  - Core-boundary fit for orchestration, base classes, registries, language-agnostic code, and language-specific behavior.
  - Existing-functionality overlap for new helpers, services, utilities, abstractions, or workflow glue.
  - Evaluation validity for prompts, chunking, extraction, resolution, classification, entity extraction, or LLM-assisted behavior.
  - Scope fit for sizeable PRs: whether the implementation meets the plan/business goal without avoidable underbuild or overbuild.
  - Concurrency safety for async, parallelism, shared clients, caches, mutable state, and filesystem/database writes.
  - Failure behavior for new defaults, fallbacks, try/except blocks, partial results, retries, and degraded modes.
  - Dependency blast radius for signatures, models, schemas, API responses, CLI flags, storage formats, and base classes.
  - Documentation and operator impact for new behavior, commands, configuration, architecture, or workflow changes.
  - Explainability for code that is difficult to follow; opacity can be a review finding when it blocks maintenance.

5. Investigate with evidence.
- Use `rg`, tests, nearby patterns, git history, and linked plans to confirm or reject concerns.
- Ground each finding in specific files and lines.
- Distinguish "this is a bug/risk" from "this needs author/product clarification."
- Do not infer missing validation from absence of proof in the diff alone; look for relevant tests, evals, docs, or CI configuration.

6. Decide review severity.
- `P0`: likely production-breaking, data-loss, security, or irreversible customer impact.
- `P1`: material correctness, architecture, scale, persistence, API, or workflow risk that should block merge.
- `P2`: maintainability, validation, scope-fit, or integration issue that should be fixed soon and may block depending on release context.
- `P3`: minor cleanup or follow-up; include only when it is clearly useful.
- If the issue depends on uncertain intent, write it as an open question rather than a finding.

## Stack Review Mode

Use stack review mode when the user provides multiple PRs, asks for stack review, or the current PR is based on another feature branch.

- Resolve the stack in dependency order from root to leaf.
- Read the overall plan, linked business goal, and every PR description before writing findings.
- Judge architecture against the final intended system state, not each intermediate PR in isolation.
- Do not flag an intermediate PR for incompleteness when a descendant PR clearly completes the contract.
- Still report each finding at the narrowest actionable location: the specific PR, file, and line where the correction belongs.
- Add cross-stack findings when the risk spans PR boundaries, such as contract drift, duplicated abstractions, sequencing risk, missing final integration coverage, or mismatch between the combined stack and the business goal.
- Keep operational stack work such as rebasing, refreshing checks, and clearing blockers out of scope; route that to `stacked-pr-sweep` when needed.

## Output

Lead with findings, ordered by severity. Use this structure:

- Stack summary: include only in stack review mode; list root-to-leaf order, overall goal, and the combined changed surface.
- Findings: each with severity, title, file/line reference, concrete evidence, why it matters, and the smallest actionable recommendation.
- Cross-stack findings: include when a risk spans PR boundaries; otherwise omit.
- Per-PR findings: include in stack review mode when grouping improves actionability.
- Open questions: intent, product, sequencing, or ownership questions that affect the review.
- Validation gaps: missing or insufficient tests, evals, canaries, docs, or manual verification relevant to the changed surface.
- Change summary: concise summary of what the PR changes, included after findings.
- Residual risk: only include if important risk remains after the available evidence.

If there are no architect-level findings, say that clearly and still note any meaningful validation gaps or review limitations.

## Guardrails

- Do not provide a generic architecture smell checklist; investigate only risks connected to the PR.
- Do not spend review budget on typo/style/null-check trivia unless it reveals a larger design or correctness issue.
- Do not assert that CI passed, checks failed, or eval metrics changed unless you verified the current signal.
- Do not ask the author to prove basic facts you can inspect locally.
- Do not recommend broad rewrites when a narrow fix or clearer contract would address the risk.
- Do not give a final ship/no-ship verdict unless the user explicitly asks for one; provide evidence and blocking severity instead.
- Do not penalize a single PR in a stack for being incomplete when the stack structure intentionally completes the behavior in a later PR.
