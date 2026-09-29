# Project Context

<!-- BEGIN WM AI SHARED BLOCK -->
## WM Shared AI Assets (Codex)

This project uses West Monroe shared AI assets exported from the central repo.

Codex-native portable skills live in `.agents/skills/`.
Project-scoped custom agents live in `.codex/agents/` and can be spawned by name.
Portable skills still live in `.agents/skills/` as the shared source of truth. Load the relevant `SKILL.md` on demand instead of rewriting the workflow from scratch.

Requirements workflow: spec-first

Use `docs/requirements/spec.md` as the source of truth for product behavior, constraints, validation rules, and implementation slices.
Create user stories only when explicitly requested.

Selected packs: `foundation`, `delivery`

WM shared assets:
- `wm-spec` — Generate an automation-friendly product specification from a raw requirement or feature brief.
- `wm-backlog` — Turn a specification, requirements, or stories into a prioritized MVP backlog with sequencing and delivery guidance.
- `wm-qa-plan` — Create a concise QA plan, scenario matrix, seed-data approach, and smoke-test checklist.
- `wm-application-smoke-test` — Run a focused, evidence-based smoke test against a web app, API, CLI, worker, or full-stack application using a verified native runner when available or safe live execution as a fallback; do not generate test scaffolding.
- `wm-pr-review` — Review a change against West Monroe quality, security, testing, and client-delivery expectations.
- `wm-adr` — Generate a West Monroe-style architecture decision record from the current decision context.
- `wm-client-handoff` — Review a client-facing deliverable for readiness, professionalism, and West Monroe engagement standards.
- `product-specification-agent` — Convert a product brief into an automation-friendly product specification with requirements, flows, contracts, validation rules, and implementation slices.
- `backlog-prioritization-agent` — Convert requirements into an MVP backlog with dependency-aware sequencing and delivery recommendations.
- `full-stack-delivery-agent` — Implement a scoped feature with tests, product docs, architecture/workflow docs, and dependency manifests while following existing codebase patterns.
- `qa-validation-agent` — Validate requirements coverage, setup docs, architecture/workflow docs, dependency manifests, seed data, and smoke checks for a demo-ready increment.
- `codebase-onboarding-agent` — Explore a codebase and produce an onboarding guide that gets a new engineer productive quickly.
- `product-delivery-orchestrator` — Act as a PM-style orchestrator that coordinates the active requirements workflow, backlog, implementation, QA, README, architecture/workflow docs, and dependency readiness.

Working guidance:
- Think before coding: state assumptions, surface ambiguity, present tradeoffs, and ask when unclear.
- Keep solutions simple: write the minimum code required and avoid speculative features, abstractions, or configurability.
- Make surgical changes: touch only what the task requires, match existing style, and clean up only artifacts created by the current change.
- Execute against verifiable goals: define success criteria, add or use checks where practical, and loop until verified.
- Start with the smallest relevant skill or agent-skill instead of a broad freeform prompt.
- Use `product-delivery-orchestrator` when you want a visible product-to-backlog-to-delivery flow.
- For generated or changed applications, keep `README.md` current with product usage, dependency installation, environment setup, run commands, and test commands.
- Keep system documentation current when implementation changes architecture or workflows: update or create `docs/architecture.md` for structure, boundaries, data flow, integrations, and key decisions; update or create `docs/workflows.md` for user, operational, or agentic workflows.
- Keep dependency manifests current. Create the stack-native manifest when missing, such as `requirements.txt` or `pyproject.toml` for Python and `package.json` for Node.
- Prefer updating existing docs and artifacts rather than creating duplicate files.
- Preserve project-local skills and agents. Treat WM shared assets as a baseline to extend, not as a replacement for team-owned workflows.
- Keep outputs grounded in repo context, requirements, tests, and delivery constraints.
<!-- END WM AI SHARED BLOCK -->
