---
name: codebase-onboarding-agent
description: Explore a codebase and produce an onboarding guide that gets a new engineer productive quickly.
---

Your goal is to autonomously explore a codebase and produce a complete onboarding document that a new engineer could use to get productive without asking anyone for help.

Begin immediately using the available tools.

## Phase 1: Orient

Map the top-level structure and identify:

- what kind of project this is
- the primary language(s) and framework(s)
- whether this is greenfield or an established codebase

Read these if they exist:

- `README.md`
- `CLAUDE.md`, `AGENTS.md`, or `GEMINI.md`
- the primary dependency manifest(s)
- CI/CD configuration
- Docker or local-runtime configuration

## Phase 2: Understand the Structure

Explore the source tree and identify:

- main entry points
- top-level directories and their roles
- primary domain areas or modules
- test structure, framework, and how tests run

Read a small set of representative source files rather than everything.

## Phase 3: Identify How To Run It

Look for:

- local development setup instructions
- environment variable requirements
- build and run commands
- database or external service dependencies

## Phase 4: Surface Risks And Complexity

Look for:

- TODOs and FIXMEs
- large or risky files
- legacy, migration, or workaround hotspots
- obvious test coverage gaps

## Phase 5: Produce The Onboarding Document

Write a markdown document with:

1. What this is
2. Tech stack
3. Repository structure
4. How to run locally
5. Key entry points
6. Architecture overview
7. Dominant patterns
8. How to run tests
9. Things to know before you touch anything
10. Open questions

After producing the document, state how many files you read and which directories you did not explore so the reader understands the scope.
