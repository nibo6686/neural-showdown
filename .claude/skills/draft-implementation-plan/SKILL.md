---
name: draft-implementation-plan
description: Use when turning an HLD, PRD, chat session, or existing plan document into a concise implementation plan with clear PR boundaries, tasks, validation criteria, and minimal ambiguity.
---

# Draft Implementation Plan

## When to use

- Use this skill when the primary task is planning from existing material rather than planning from Jira.
- Prefer this skill when you need one normalized implementation plan document with PR-sized execution boundaries.
- If the source is a Jira ticket, use `jira-implementation-planner` instead.
- After the plan is drafted, use `review-plan-tests` before implementation when test coverage or integration validation may be incomplete.

Do not use this skill for brainstorming, executive strategy documents, vision framing, stakeholder alignment narratives, or high-level go-forward strategy unless the user explicitly asks to turn that material into an execution plan with implementation tasks, PR boundaries, or validation gates. Use `strategy-brief` for strategy and alignment artifacts.

## Inputs

- One or more source artifacts:
  - HLD / architecture document
  - PRD / requirements document
  - Chat session summary or decisions captured in the current thread
  - Existing implementation plan that needs normalization
- Optional supporting context:
  - related architecture docs
  - source files
  - test files

## Workflow

1. Gather the source set.
- Read the primary source document first.
- Read additional source documents only when they materially constrain scope, sequencing, or validation.
- If the source is the current chat session, summarize the decisions and assumptions before drafting.

2. Read the standard template.
- Use `codex-skills/draft-implementation-plan/references/implementation-plan-template.md` as the formatting source of truth.
- Keep the section order unless the user explicitly asks for a different structure.

3. Explore repository context.
- Search for the subsystems, files, tests, and existing planning docs tied to the requested work.
- Reuse repo terminology that already exists.
- If the source is vague, identify likely implementation areas without fabricating certainty.

4. Normalize the source into a coherent execution plan.
- Use one sequencing model per plan.
- Treat `PR` as the default and preferred execution boundary.
- Default PR sizing to one implementable review cycle. If a proposed PR would likely require multiple independently testable slices, multiple distinct validation gates, or multiple execution sessions to land safely, split it into additional PRs instead of bundling broad follow-on work into one PR section.
- Do not use the terms `slice` or `review unit` in the user-facing plan.
- If the work is a single PR, use one PR section with tasks and validation. Inside that PR, the default subdivisions are tasks and validation only; do not invent phases inside a single PR.
- If the work spans multiple PRs, use stable PR IDs such as `PR-01`, `PR-02` as the top-level execution boundary.
- Use `PHASE-01`, `PHASE-02` only when the source explicitly describes broader program stages that span multiple PRs or milestones and those phases matter outside PR review sequencing; if you use phases, keep PR and phase meanings distinct and obvious.
- Add checkbox tasks under each PR or phase, preferably with task IDs such as `P1-T01`.
- Preserve completed or in-progress work when the source already reflects real status.
- Keep `## Source Materials` minimal. Include only sources that materially change scope, sequencing, review, or validation. Omit chat-session bullets unless they carry necessary decisions unavailable elsewhere.
- Avoid extra summary sections that only restate scope, constraints, or PR tasks. Fold that material into existing sections unless it carries non-redundant execution guidance.
- Keep `## Status` focused on prerequisite context or non-PR work that materially affects execution. Let `## PR Status` or `## Phase Status` carry the main execution state.
- Default the deployment model to all-at-once unless the source explicitly requires staged rollout, coexistence windows, or temporary migration support.
- Plan directly for the final end state when deployment is all-at-once; avoid temporary deprecation, compatibility, or active-doc tasks that exist only between stacked PRs.
- When a task or PR has multiple plausible implementation shapes, include concise implementation hints for the chosen approach.
- Keep implementation hints short and execution-oriented: name the primary seam/modules, expected data or control-flow wiring, and any critical persistence/API/UI contract that must anchor the work.
- When control flow is not obvious, include a short `Implementation Shape` section that states where the work executes in the runtime or pipeline, whether it extends an existing phase/call or adds a new one, and what must happen before/after it.
- Do not turn the plan into a design document; skip alternatives unless the user explicitly asks for tradeoff analysis.
- Call out dependencies, blockers, and critical-path ordering explicitly.
- Add concrete parallelism guidance:
  - what can run concurrently
  - what must land first
  - where shared contracts or migrations create serialization points
- Add `PR / Review Strategy` guidance when PR boundaries or stacking materially affect execution.
- Keep `PR / Review Strategy` focused on review sequencing; do not invent intermediate user-facing states just to justify PR order.
- Capture PR order, merge gates, and when relevant the previous PR in the sequence and the next planned PR.
- Do not prescribe commit cadence, push timing, or day-to-day PR mechanics.
- Define validation criteria per PR or phase and cross-cutting validation for the whole plan.
- For multi-PR plans that combine into one user-visible workflow or shared architecture contract, add a short `## Final Acceptance Contract` before `## Scope and Constraints`. Use it as the definition of done for the whole stack: the user-visible workflow or architecture contract that must work, the production path that must be exercised, allowed fakes, final validation gates, and explicit "not complete if..." conditions. Keep `## Cross-Cutting Validation` as the evidence plan that proves the contract.
- For new Evolve SDK agent workflows, default the first PR to prompt + workflow descriptor/registry + fake-worker or prompt-loading tests + one realistic canary. Defer custom storage, Hub UI, deterministic classifiers, and workflow-specific orchestration unless the source artifact explicitly requires them or prior pilot runs prove the need.
- For eval-sensitive work, do not defer all evaluation coverage to the final PR. Instead, add or extend a bounded evaluation slice in the same PR as the implementation work and make it part of that PR's validation gate.
- Treat the following as eval-sensitive by default unless repo context clearly says otherwise:
  - new language support or language-promotion plans
  - AST/provider onboarding
  - prompt, extraction-quality, resolution-quality, or entity-extraction changes
  - other work where `tests/evaluation/` is the main quality signal rather than unit tests alone
- For language or framework support claims, include a bounded
  extraction/resolution canary in the relevant PR's validation gate. The canary
  can be a checked-in fixture, `tests/evaluation/` case, or pinned source
  subset. It should prove basic production-path extraction, evidence
  persistence, and representative same-file/cross-file resolution before any
  full-corpus scan.
- Do not frame full repository or customer-style scans as the first required
  validation gate for language support. Treat them as optional follow-up
  confidence checks unless the source material explicitly requires them.
- When a PR introduces new evaluation fixtures, ground truth, or a new eval family, prefer explicit red-green wording in the plan: the eval slice should be red before implementation and green after the code lands.
- Define milestones only when they add clarity; skip them for small single-PR plans.
- Include `Risks / Open Questions` inside a PR or phase only when there is a substantive local risk, dependency, or decision. Do not emit generic one-line stubs when the document-level `## Open Questions` is enough.

5. Handle uncertainty correctly.
- Do not invent file paths, APIs, or acceptance criteria that are not supported by source material or repository context.
- Record open questions and assumptions explicitly when source material is incomplete or conflicting.
- If unresolved decisions would materially change scope, PR order, schema strategy, delete-vs-defer behavior, or the implementation shape, end the user-facing response with 1-3 concise blocking clarification questions. Do not bury implementation-blocking decisions only inside `## Open Questions`.
- Prefer hard edges in the plan over hand-wavy sequencing.

6. Write the plan to a default repo location.
- Default output directory: `docs/planning/`.
- For language support work, use `docs/planning/<language>/` as the output directory.
- Default filename: derive a slug from the primary source and write `<slug>-implementation-plan.md`.
- Before appending `-implementation-plan`, strip common source suffixes such as `-hld`, `-prd`, `-plan`, `-design`, or `-spec` when present.
- If the source is the current chat session and the topic is clear, derive a functional slug from the requested capability/topic and write `<slug>-implementation-plan.md`, or `docs/planning/<language>/<slug>-implementation-plan.md` for language support work.
- If the source is the current chat session and the topic is genuinely broad, mixed, or unstable, fall back to `docs/planning/chat-session-implementation-plan-<YYYY-MM-DD>.md`, or `docs/planning/<language>/chat-session-implementation-plan-<YYYY-MM-DD>.md` for language support work.
- Do not overwrite the source document unless the user explicitly asks for in-place normalization.
- Do not place planning artifacts under `docs/languages/`; reserve that area for persistent language documentation after the support work is complete.
- Return the output path and a short summary after writing.

## Output requirements

- Include the repo-standard `## Status` section near the top.
- Include either a `## PR Status` table or a `## Phase Status` table directly after `## Status`, matching the chosen sequencing model.
- Do not include both unless the source explicitly requires program phases above PRs.
- Include `## Final Acceptance Contract` for multi-PR plans that deliver one user-visible workflow or shared architecture contract.
- Use PRs as the default top-level sections and tasks as the default subdivisions inside a PR.
- Include `## Parallel Execution Notes`, `## PR / Review Strategy`, and PR/phase sections with checkbox tasks.
- Include `## Milestones` only when they materially help comprehension.
- Each PR or phase section must include:
  - status
  - objective
  - dependencies
  - parallelism guidance
  - checkbox tasks
  - validation criteria
  - risks or open questions when needed
- For eval-sensitive plans, each PR or phase should name the bounded eval slice,
  `tests/evaluation/` work, or claim-matched canary that gates that section, not
  just the final validation PR.
- For ambiguous or high-leverage phases, include enough implementation-shape detail that another agent can execute reliably without re-deriving the intended approach from scratch.
- Keep plans concise, coherent, and execution-oriented; avoid long narrative prose and low-value source/context commentary.
- Avoid repeating the same execution status in `## Status`, the status table, and the PR sections unless the repetition adds real context.
- Keep PR guidance at the review-boundary level; leave commit timing to execution workflows.
- For non-trivial pipeline work, hybrid LLM/static flows, or fallback-heavy sequencing, recommend a separate Mermaid workflow/sequence diagram doc when it would materially reduce ambiguity. Do not add diagrams by default for straightforward plans.
- When blocking clarification questions remain, ask them explicitly in the response after returning the plan path/summary. Keep that list to 1-3 questions and reserve it for decisions that materially affect implementation.

## Notes

- If the source document is already phased, normalize the formatting before inventing a new decomposition.
- If the source is broad and architectural, bias toward implementation slices that can be validated independently.
- When a draft PR starts accumulating multiple independent task clusters, prefer more smaller PRs over one large PR that depends on the execution workflow to stop early.
- If the plan will drive coding work in this repo, recommend `review-plan-tests` after drafting so the plan includes adequate wiring, integration, and end-to-end validation.
