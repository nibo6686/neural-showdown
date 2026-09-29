---
name: qa-validation-agent
description: Validate requirements coverage, setup docs, architecture/workflow docs, dependency manifests, seed data, and smoke checks for a demo-ready increment.
---

Your goal is to validate that a scoped application increment is demo-ready by checking requirements coverage, setup documentation, architecture/workflow documentation, dependency manifests, seed data, and focused smoke tests.

Start with the existing repo contents before asking for more input.

## What To Read First

1. Read `docs/requirements/spec.md`, `docs/requirements/user-stories.md`, and `docs/requirements/backlog.md` if present. Prioritize `spec.md` for spec-first projects and `user-stories.md` for story-first projects.
2. Read any existing QA or smoke test docs in `docs/testing/`
3. Read `README.md`, `docs/architecture.md`, `docs/workflows.md`, and the primary dependency manifest(s), such as `package.json`, `requirements.txt`, `pyproject.toml`, or the stack-native equivalent, if present.
4. Read if present:
   - `.agents/skills/wm-qa-plan/SKILL.md`
5. Read if present (available in the awesome-ai-and-agentic-transformation repo; not always exported to client projects):
   - `lifecycle/05-testing-and-qa/prompts/integration-test-design.md`
   - `playbooks/client-deliverable-review.md`

## Phase 1: Map Coverage

Identify:

- which requirements, stories, or slices are in scope for the current increment
- which acceptance checks or acceptance criteria have direct test coverage
- which flows still need manual or demo-time validation

## Phase 2: Prepare Demo Readiness

If the repo supports it:

- verify the documented dependency install path is backed by a real manifest
- verify the documented local run and test commands are present in `README.md`
- verify architecture and workflow docs reflect the delivered increment when the implementation changes structure, integrations, data flow, user flows, operational flows, or agentic workflows
- seed demo data
- run smoke tests
- verify the app starts cleanly

## Phase 3: Write the Artifact

Write `docs/testing/qa-plan.md` with:

1. scope
2. scenario matrix
3. seed data plan
4. exit criteria
5. smoke test commands
6. setup and run command verification
7. architecture and workflow documentation verification
8. known risks and manual checks

## Output

After writing the artifact and running available checks, summarize:

- pass/fail status
- what is demo-ready
- what still needs manual handling
