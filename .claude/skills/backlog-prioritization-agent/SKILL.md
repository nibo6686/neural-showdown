---
name: backlog-prioritization-agent
description: Convert requirements into an MVP backlog with dependency-aware sequencing and delivery recommendations.
---

Your goal is to turn a set of product requirements, product specifications, or user stories into an MVP backlog that a delivery team can execute immediately.

Start without asking for more input if `docs/requirements/spec.md`, `docs/requirements/user-stories.md`, or similar requirement artifacts already exist.

If project context declares `spec-first`, treat `docs/requirements/spec.md` as the source of truth. If project context declares `story-first`, treat `docs/requirements/user-stories.md` as the source of truth. Do not generate the other requirements artifact unless explicitly requested.

## What To Read

1. Read `docs/requirements/spec.md` or `docs/requirements/user-stories.md`, prioritizing the active workflow declared in project context.
2. Read any product brief or `README.md` content needed to understand the application.
3. Read if present:
   - `.agents/skills/wm-backlog/SKILL.md`
4. Read if present (available in the awesome-ai-and-agentic-transformation repo; not always exported to client projects):
   - `playbooks/feature-development-end-to-end.md`

## Phase 1: Assess the Work

Identify:

- the smallest end-to-end slice that proves the product
- which items are frontend, backend, shared, or QA-heavy
- dependencies that affect order
- stories, requirements, or implementation slices that should be split for delivery reliability

## Phase 2: Prioritize

Create a backlog with:

- `P0` stories, requirements, or slices required for a working MVP
- `P1` stories, requirements, or slices that improve the result but are not strictly required
- `Stretch` items to defer unless time remains

## Phase 3: Write the Artifact

Write the result to `docs/requirements/backlog.md` with:

1. MVP objective
2. Prioritization principles
3. Prioritized backlog table
4. Recommended implementation sequence
5. Risks and dependency notes

## Output

After writing the file, summarize:

- the top 3 stories, requirements, or slices for implementation
- the key dependency chain
- what should be deferred if the team needs a tighter MVP
