# Optional integrations and conventions

Read this reference when the target already has an automation framework, the requester asks for a
specific integration, or the run must produce standard CI artifacts. These integrations are
opt-in. Do not install dependencies, change runner configuration, or generate test files as part
of an ordinary smoke run.

## Selection rules

1. Inspect the target repository's manifests, lockfiles, runner configuration, task scripts, and
   existing tests before selecting a tool.
2. Prefer the repository's established language, framework, runner, fixtures, tags, and reporter.
3. Use an optional integration only when its prerequisites and mutation scope are verified.
4. If the requester asks for an integration that is not present, report it as unavailable and
   propose a separately authorized scaffolding change; do not silently install or scaffold it.
5. Keep live browser, HTTP, CLI, or other direct execution available for behaviors the selected
   runner cannot reach. Record which rows came from the runner and which came from live execution.

## Catalog and browser conventions

| Target situation | Preferred convention | Boundary |
|---|---|---|
| JavaScript/TypeScript web app with an existing Playwright suite | Playwright Test with a canonical `@smoke` tag | Use the repository's scripts, projects, fixtures, retries, traces, and reporters. |
| JavaScript/TypeScript web app that explicitly needs Gherkin | `playwright-bdd` only when the repository accepts the dependency and owns its upgrade path | Keep Playwright Test as the runner; do not add BDD solely because the app is web-based. |
| Existing cross-language BDD suite | Use the repository's established Cucumber, Reqnroll, pytest-bdd, Behave, Karate, or equivalent setup | Do not introduce a second BDD framework. |
| No suitable browser suite | Use the safest supported live browser surface, or propose a separate scaffolding workflow | Report that no durable test asset was created. |

Gherkin is optional. Use it when business-readable scenarios or cross-team collaboration justify
the extra step-definition and dependency surface. Otherwise, framework-native tests with a
canonical `@smoke` tag are the lighter convention.

When a durable suite exists or is explicitly being scaffolded, keep tag names lowercase and
document them in a repository-level `TAGS.md`. The suggested meanings are:

- `@smoke` — fast readiness and critical-flow checks
- `@regression` — broader repeatable functional coverage
- `@full` — the complete agreed suite

Do not create `TAGS.md` or modify tags during a read-only smoke run.

## API and contract conventions

Treat API coverage separately from browser coverage. Choose based on the contract and ownership
model, not on tool popularity:

- Use the repository's existing API runner first.
- Use Schemathesis when an OpenAPI or GraphQL schema is authoritative and bounded generated cases
  are safe for the target environment.
- Use Pact when the team owns and can safely exercise both consumer and provider contracts.
- Use Dredd when lightweight OpenAPI conformance is the actual requirement.

Generated API cases must be bounded, redacted in retained evidence, and excluded from production
unless the requester explicitly authorizes the exact safe operation. Do not infer consumer/provider
ownership or invent a schema endpoint.

## Reporting conventions

For automation runs, preserve standard runner output whenever the runner provides it:

1. JUnit XML is the baseline interoperable result for CI ingestion.
2. Allure is optional when the repository already uses it or human-facing history and attachments
   are required.
3. CTRF is optional and experimental; use it only when the repository has chosen it and can
   manage the schema lifecycle.
4. Playwright blob output is relevant only when Playwright sharding or a blob report is configured.

The WM report remains the semantic layer for statuses that standard pass/fail formats do not
express, including `BLOCKED`, `FLAKY`, `UNSAFE_NOT_EXECUTED`, `OWNERSHIP_UNRESOLVED`, and
`EXCLUDED_SCAFFOLDING`. Emit it as a sidecar or human-readable report; do not replace native
runner artifacts when they are available.

## Out of scope for this skill

OpenTelemetry CI/CD conventions, new framework installation, journey-catalog persistence, test
code generation, runner scaffolding, and CI workflow creation require a separate explicitly
requested workflow. This skill may identify those needs and report them as follow-up actions, but
must not perform them during a smoke run.
