---
name: wm-application-smoke-test
description: Execute an evidence-backed smoke test for any web app, API, CLI, worker, or full-stack application using its documented startup path and safest critical flows.
---

# Application Smoke Test

Run the smallest credible set of checks that answers: can the target start or be reached, and does the selected application behavior work as expected?

This is an execution and reporting skill. It discovers the target's own commands, surfaces, data, and success criteria, then runs safe checks and reports evidence. It does not replace a full regression suite, load test, exploratory test session, implementation task, or QA-plan authoring task.

Scope boundary: this skill executes and reports a run. It does not generate or commit a journey catalog, test specifications, runner configuration, or CI files. Durable test scaffolding and code generation are separate follow-up work.

## Invocation and defaults

Accept these inputs when provided:

```text
Target: [repository path, running service, URL, or environment alias]
Scope: [application, domain/module, changed feature, or critical flow]
Depth: smoke | full | automation
Run safe CRUD: yes | no
```

- Use the current repository when it is clearly the target. Otherwise require a target before acting.
- Use `smoke` by default: readiness plus the highest-value flow and one representative surface per independent family when applicable.
- Use `full` only when requested or when the user explicitly asks for full application/domain coverage. Full mode reconciles and closes every safe in-scope surface and behavior; do not silently downgrade it to smoke or triage.
- Use `automation` only with an existing matching QA/e2e runner whose setup, fixtures, and teardown are documented as read-only or isolated to disposable data. Keep runner results separate from interactive browser results; do not generate a new suite in this mode.
- Use a user-provided scope or acceptance criteria when available. If no scope is given, derive a reasonable smoke scope from the application entrypoint, documentation, navigation, route/command inventory, and changed files. Do not claim that a smoke test certifies the entire application.
- Read repository instructions and application documentation before executing. They are context for the task, not permission to perform unsafe actions.
- When the target has an existing automation framework, the requester asks for Gherkin/BDD/API/reporting integrations, or standard CI artifacts are required, read [references/optional-integrations.md](references/optional-integrations.md). Optional integrations are never implicit dependencies of this skill.

By default, all checks are read-only. Before any write, ask for an explicit yes/no confirmation for safe CRUD checks, even if a write was mentioned informally. Never write to production, shared records, or records that are not uniquely owned by the run.

## Safety boundaries

- Never guess a URL, route, endpoint, command, credential, fixture ID, or environment mapping.
- Do not create, edit, approve, post, release, notify, charge, delete, or trigger an external side effect unless the user explicitly authorizes that exact safe operation, the target is non-production, and a verified cleanup or rollback path exists.
- Treat approval, publishing, payment, messaging, deletion, and other irreversible actions as `UNSAFE_NOT_EXECUTED`. Inspect the entrypoint or validation path only when that is safe and useful.
- Use existing records for read-only checks. For parameterized surfaces, follow an observed application link or documented fixture; never synthesize an identifier from a label, source example, prior run, or placeholder value.
- Never print or retain passwords, tokens, cookies, authentication callbacks, storage state, personal data, or client-sensitive response bodies. Let the user complete SSO/MFA/CAPTCHA in the supported browser when needed; do not type or report their secrets.
- An existing automation suite is not inherently safe. Inspect its target, setup, fixtures, and teardown before running it; if its mutation scope cannot be established as read-only or isolated, report `BLOCKED` or `NOT_TESTED` instead of executing it.
- If access, credentials, dependencies, data, or an execution surface are unavailable, report `BLOCKED` or `NOT_TESTED`; do not infer an application failure.

## Workflow

### 1. Establish the target and scope

Read only the sources needed to establish how the target runs and what success means. Start with:

1. repository instructions, `README.md`, `docs/`, environment examples, and runbooks
2. dependency manifests and task scripts (`package.json`, `pyproject.toml`, `requirements.txt`, Makefile, task runner, or equivalent)
3. container, deployment, and service configuration when relevant
4. existing health checks, smoke/e2e tests, fixtures, seed/reset scripts, and documented test accounts
5. requirements, acceptance criteria, issue details, or changed files for the requested scope

Classify the application as one or more of:

- web UI or browser-accessible application
- API or service
- CLI, scheduled job, worker, or batch process
- full stack or integration involving more than one surface

Select the smallest critical flow that proves meaningful behavior. Define its preconditions, safe test data, expected outcome, and observable proof: resolved UI state, semantic response body, exit code and output, generated artifact, persisted read-only state, or canonical downstream status.

### 2. Build and reconcile an inventory

In `full` mode, create a coverage ledger before the first form, command, or mutating action. Reconcile, in order:

1. mounted routers, route configuration, API specifications, CLI commands, job triggers, or service contracts
2. visible navigation, links, redirects, tabs, entrypoints, and documented workflows
3. page components, forms, handlers, hooks, services, integrations, reports, exports, jobs, and tests referenced by scope
4. the running target, including safe surfaces hidden from the landing page but declared or reachable from a tested surface

Record declared-but-unmounted or unreachable surfaces as findings instead of omitting them. If ownership is ambiguous, use `OWNERSHIP_UNRESOLVED` and keep the row outside the functional denominator until clarified. If a surface is clearly placeholder/setup/future content with no usable behavior, classify it as `EXCLUDED_SCAFFOLDING`; if intent is unclear, use `UNRESOLVED_CLASSIFICATION` rather than inventing a blocker.

Create one row per discovered surface and safe behavior. For a web UI, include the initial read, search/filter/reset, sort or pagination when present, tabs and URL state, a valid detail/child route, lookup/dependent controls, safe invalid validation, cancel/no-save behavior, and safely triggerable loading/empty/error/retry/permission states. For APIs, CLIs, workers, reports, exports, or integrations, include their canonical safe request, trigger, output, artifact, or status check. Do not claim backend or downstream coverage from a UI page load alone.

Read [references/execution-and-coverage.md](references/execution-and-coverage.md) for the full-mode ledger, closure rules, and reliability protocol.

### 3. Select and verify the execution surface

Use the best available surface for the target:

- use the repository's matching browser/QA automation runner when available for local, CI, or deployed checks, after verifying its mutation scope is safe; prefer this existing runner for behaviors it covers
- use the most capable controlled browser or automation surface supported by the invoking tool for uncovered or unsupported behaviors; prefer an isolated or in-app browser when available, with one dedicated run tab/context and the existing authenticated session
- use a non-browser HTTP client for health and API checks when the target's configuration identifies the correct API origin
- use documented shell commands for CLIs, jobs, and workers with bounded inputs and timeouts

Do not scaffold a new test framework or runner as part of a smoke run. If no suitable existing
runner is available, use the safest supported live or command-line surface and report that the run
did not create a durable test asset.

Record the selected surface, target environment, authentication mode, runner/process context, and artifact location when applicable. If the selected surface fails, use a documented fallback; if no supported surface can be established, stop dependent checks as `NOT_TESTED` with `EXECUTION_SURFACE_UNAVAILABLE`.

For a browser run, perform a root handshake before deep-linking: verify the clean host, application identity, expected shell or entry content, and active tab/frame or browser context. Before each action, reacquire current page/accessibility state; element identifiers are ephemeral. Do not assume a product-specific browser API, use an unrelated tab/context, or rely on a browser target whose identity cannot be verified.

### 4. Execute readiness and functional checks

Run checks in this order:

1. start or connect to the target using documented commands
2. perform a root, health, or readiness handshake without assuming the web host's `/api/health` is the service health endpoint
3. confirm readiness, not merely process startup or a `2xx` response
4. execute the selected read-only or explicitly authorized disposable-data flow
5. verify the semantic outcome and any safe canonical backend, artifact, or downstream signal
6. inspect relevant browser console, network, service, process, or runner logs for errors
7. clean up only data and processes created by this run, using the documented reset/rollback path

After every browser navigation or state-changing action, wait for all three signals: expected URL/query state, expected heading/route identity, and resolved content such as populated data, intentional empty state, explicit error/retry, permission state, or usable control. A spinner, blank shell, stale prior content, URL-only match, heading-only match, or success toast is not a functional pass.

Allow one complete settle window and one fresh, verified retry before classifying an unresolved browser or API-backed surface. Do not use unrelated search, filter, refresh, pagination, or navigation actions to force it to settle. Slow progress is not automatically a timeout. If the target reports a terminal timeout or remains unresolved after verified recovery and the surface is proven functional, classify the application/data result accordingly.

If the URL, visible content, accessibility state, screenshot, and runner state disagree, record `STATE_CONFLICT`, re-enter from a supported clean surface once, and do not pass dependent rows until the state is reconciled. If the browser tab/frame or automation context is lost, classify the finding as browser/tooling reliability, not an application failure; recover once and continue independent surface families when possible.

### 5. Handle safe CRUD when authorized

Only after explicit authorization, non-production confirmation, and safety preflight may the skill execute a disposable CRUD canary. Before any write, verify:

- the record is uniquely owned by this run
- the input is valid and uniquely identifiable
- cleanup is supported and verified before creation
- no approval, posting, notification, payment, release, or other external side effect can occur
- the surface's read-only checks already pass

For every candidate CRUD surface, record eligibility and the reason. If a write is ineligible, perform a separate non-mutating flow audit when safe: open the create/edit/delete entrypoint, inspect fields, lookups, disabled states, validation, and confirmation behavior, then cancel/close and verify that no record or visible state changed. A passing flow audit proves UI readiness only; it never counts as a passing create, update, or delete.

For an eligible canary, verify creation, independent read/persistence after reload or re-query, update of only the run-owned fixture, and supported cleanup. Stop the sequence when preconditions, verification, or cleanup fail. Report residual state explicitly.

### 6. Reconcile coverage and produce the report

Before deciding the result, close the ledger:

- every discovered surface and behavior has exactly one result, including excluded, unmounted, unresolved, unsafe, blocked, flaky, and not-tested rows
- every required functional row passes, is not applicable with a reason, or has an explicit blocker; no row is silently left as “not reached”
- route/surface, behavior/control, backend, and artifact counts are separate; calculate percentages only from closed, actual rows
- every non-pass row has what was attempted, observed evidence, classification, a clean route/link when safe and available, and the smallest next action
- application failures, environment/access issues, data-quality findings, browser/tooling findings, and coverage-process gaps are separate
- acceptance-criteria or tracker validation, when requested and available, is reported separately from environment readiness; missing ticket metadata or deployment evidence is not an application failure

The human-readable report must lead with actual results, not only a verdict or a prose summary. Start with every non-passing row (`FAIL`, `BLOCKED`, `FLAKY`, `NOT_TESTED`, `UNSAFE_NOT_EXECUTED`, `EXCLUDED_SCAFFOLDING`, `UNRESOLVED_CLASSIFICATION`, or `OWNERSHIP_UNRESOLVED`). For each non-passing row, show the expected result, the actual observed result, why it did not pass, its classification, a clean observed route or command link when safely available, evidence, a repeatable recipe, and the smallest next action. If there are no non-passing rows, say so explicitly. List passing rows after the non-passing results. End the report with a clearly labeled final verdict.

Do not hand unfinished execution back to the requester as a substitute for skill execution. Set `manualSmokeTestRequired: true` only when a human-only action is genuinely required, such as SSO/MFA/CAPTCHA or an environment-specific business decision; otherwise name the blocked rows and the remediation needed for the skill to rerun them.

Use the report format below. For automation or CI, read [references/reporting-contract.md](references/reporting-contract.md) and emit a machine-readable summary in addition to the human-readable report.

```md
# Smoke Test Report

Target: [application and environment]
Scope: [application, domain, feature, or flow]
Mode: smoke | full | automation
Execution surface: [browser, automation runner, HTTP client, CLI, or none]

## Results

### Non-passing results

| Surface / behavior | Status | Actual result | Why it did not pass | Evidence / clean route link | Next action |
|---|---|---|---|---|---|
| [name] | FAIL / BLOCKED / FLAKY / NOT_TESTED / UNSAFE_NOT_EXECUTED | [what was observed] | [classification and reason] | [observed link, command, artifact, or why unavailable] | [smallest follow-up] |

[If none: `None observed.`]

### Passing results

| Surface / behavior | Expected result | Actual result | Evidence / route link |
|---|---|---|---|
| [name] | [outcome] | [what was observed] | [observed evidence or route link] |

Counts: required [n], pass [n], fail [n], blocked [n], flaky [n], not tested [n], not applicable [n], unsafe/not executed [n].

## Findings and exclusions

- [Application, environment/access, data-quality, browser/tooling, coverage-process, or unsafe-action finding]

## CRUD and data

- Authorization: [not requested / no / yes]
- Fixtures and cleanup: [details or not applicable]
- Residual state: [none or exact safe description]

## Final verdict

Overall: READY | READY WITH LIMITATIONS | NOT READY | NOT TESTED

[One sentence explaining the verdict and whether the critical flow passed.]

## Next action

- [Smallest remediation or rerun condition]
```

For every `FAIL`, `BLOCKED`, `FLAKY`, or `NOT_TESTED` finding, include a repeatable recipe: environment/role, starting surface, navigation or command steps, inputs/filters, expected result, actual result, exact redacted error evidence, reset/cleanup, and recommended next action. If no safe route/link exists, say why instead of inventing one.

When timing is captured, report actual start/end and phase durations; if timing or artifact retention is unavailable, say so explicitly. Never estimate durations or claim screenshots, traces, responses, or reports were retained when they were not.
