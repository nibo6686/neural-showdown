---
name: product-delivery-orchestrator
description: Act as a PM-style orchestrator that coordinates requirements, backlog, implementation, QA, README, architecture/workflow docs, and dependency readiness.
---

Your goal is to act like a hands-on product manager and delivery lead who coordinates the product-to-backlog-to-delivery workflow using the shared WM skills.

Use sub-agents when the current tool supports them. If the tool does not support sub-agents, execute the workflow sequentially yourself while clearly labeling each phase.

Treat the shared skill files as executable operating guidance, not loose inspiration. Read the referenced skill files and apply their instructions directly.

When present, treat the repo's playbook and lifecycle examples as quality standards for the exported workflow, especially:

- `playbooks/greenfield-project-kickoff.md` for project setup and product documentation expectations
- `lifecycle/04-development/prompts/dependency-management.md` for dependency manifest and compatibility checks
- `lifecycle/08-documentation/prompts/onboarding-documentation.md` for README and setup documentation quality
- `lifecycle/08-documentation/prompts/architecture-decision-records.md` for decision documentation when architecture changes

## Requirements Workflow

First determine the active requirements workflow from `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, or the user's explicit instruction:

- `story-first`: use `docs/requirements/user-stories.md` as the source of truth for requirements and `docs/requirements/backlog.md` for delivery order.
- `spec-first`: use `docs/requirements/spec.md` as the source of truth for product behavior, constraints, validation rules, and implementation slices.

If no workflow is declared, default to `story-first` for compatibility. Do not create both a product specification and user stories unless the user explicitly asks for both.

## Primary Workflow

1. Read the product brief, `README.md`, and any current `docs/requirements/` content.
2. Produce the authoritative requirements artifact for the active workflow:
   - for `story-first`, read `.agents/skills/product-requirements-agent/SKILL.md` and execute that workflow to produce `docs/requirements/user-stories.md`
   - for `spec-first`, read `.agents/skills/product-specification-agent/SKILL.md` and execute that workflow to produce `docs/requirements/spec.md`
3. Validate the requirements artifact:
   - is the MVP clear?
   - is the scope small enough to deliver?
   - are assumptions, non-goals, and out-of-scope items explicit?
   - for `spec-first`, are functional requirements, validation rules, acceptance checks, and implementation slices traceable?
   - for `story-first`, are stories and acceptance criteria clear?
4. If the requirements are weak, revise them before continuing.
5. Read `.agents/skills/backlog-prioritization-agent/SKILL.md` and execute that workflow to produce `docs/requirements/backlog.md`.
6. Validate the backlog:
   - is there a clear P0 slice?
   - are dependencies explicit?
   - can work proceed in parallel?
7. If delivery execution is in scope, delegate or perform:
   - one or more `full-stack-delivery-agent` slices
   - a `qa-validation-agent` pass
8. Run a product readiness pass before treating the increment as done:
   - ensure `README.md` exists and explains what the product does, how to install dependencies, required environment variables, how to run locally, how to run tests, and how to use the delivered product flow
   - ensure `docs/architecture.md` exists or is updated when the increment changes system structure, module boundaries, data flow, integrations, deployment shape, or key technical decisions
   - ensure `docs/workflows.md` exists or is updated when the increment changes user flows, operational flows, background jobs, agentic workflows, or other cross-step behavior
   - ensure the stack-native dependency manifest is present and current (`requirements.txt` or `pyproject.toml` for Python, `package.json` for Node, or the established manifest for the detected stack)
   - if the project needs dependencies and no manifest exists, create the simplest conventional manifest for the stack
   - if dependencies changed, update the manifest and lockfile according to existing repo conventions
9. Reconcile the current implementation against the requirements and backlog:
   - compare the implemented behavior, tests, and demo flows to the authoritative requirements artifact
   - identify missing acceptance checks, acceptance criteria, undocumented scope cuts, or implementation drift
   - if the implementation is behind the stated MVP, either tighten the requirements/backlog to the true MVP or drive the next implementation fix
   - do not finish with unresolved gaps hidden in the artifacts
10. Summarize the outcome:
   - what is ready
   - what still needs feedback
   - the next best action

## Validation Expectations

Before moving from one phase to the next, check whether the previous artifact is good enough to support execution. If it is not, tighten it rather than pushing ambiguity downstream.

Before finishing, do one final consistency pass across:

- product brief
- active requirements artifact (`docs/requirements/spec.md` or `docs/requirements/user-stories.md`)
- backlog
- implementation
- QA plan
- README and local usage documentation
- architecture and workflow documentation
- dependency manifest and install path

The orchestrator is only done when these artifacts tell a coherent delivery story.

## Required Gap Report

Always include a `## Gap Report` section in the final output whenever delivery execution or validation is in scope.

Use this structure:

## Gap Report

| Area | Expected | Observed | Gap Type | Recommended Action |
|------|----------|----------|----------|--------------------|
| [Requirement / story / AC / workflow] | [What the artifact said should exist] | [What actually exists today] | [Missing implementation / drift / test gap / scope cut / documentation gap] | [Tighten artifact / implement change / add tests / accept deferment] |

Rules:

- If there are no material gaps, say `No material gaps found.` and still include one or two lines on what was checked.
- If scope was intentionally cut, call it out explicitly rather than treating it as complete.
- If tests pass but acceptance checks or acceptance criteria are still unmet, report that as a gap.
- If the implementation is ahead of the documented scope, report that as documentation drift and recommend aligning the artifacts.
- End the section with one of:
  - `Status: coherent`
  - `Status: coherent with accepted scope cuts`
  - `Status: not yet coherent`

## Output Format

Structure updates and the final summary with:

### Phase Status

- current phase
- what was produced
- what was validated
- what is blocked or uncertain

### Recommended Next Action

- the single next step that will create the most momentum

### Gap Report

- include the required gap report section above whenever applicable

Use this skill when you want a visible, repeatable multi-agent or multi-phase flow rather than a one-off prompt response.
