# Execution and coverage rules

Read this reference for `full` mode, deployed browser runs, automation fallback, or any run with
ambiguous loading, stale state, retries, or incomplete coverage.

## Coverage depth

- `smoke` checks readiness, the highest-value critical flow, and representative independent surfaces.
  It is intentionally scoped and must not claim full application coverage.
- `full` builds a reconciled inventory, attempts every safe required surface and behavior, and closes
  every row. It may finish partial when required rows fail, block, or remain untested.
- `automation` runs an existing matching suite and reports its runner identity and artifacts separately
  from interactive browser evidence.

This skill does not generate or commit journey catalogs, test specifications, runner configuration,
or CI files. If a durable rerunnable suite is wanted, treat scaffolding as a separate explicitly
requested workflow. When an existing repository-native runner is available and safe, use it before
falling back to live browser or HTTP execution.

Do not silently change `full` to `smoke`. If the requester stops the run or recovery is impossible,
record all remaining rows as `NOT_TESTED` with the exact stop reason and continue independent rows
whenever the execution surface remains usable.

## Inventory and row rules

Build the inventory from source contracts, navigation/entrypoints, implementation references, and
the running target. Reconcile declared-but-unmounted, hidden, or target-only surfaces instead of
omitting them. A UI shell is not functional coverage unless its advertised behavior resolves.

Create stable rows before execution for each surface, behavior, control, backend capability, and
explicit exclusion. Minimum full sweep when applicable:

- initial read and a valid detail/child route
- search, filter, reset, and each exposed date/range filter
- sort direction and pagination/rows-per-page or an explicit disabled-state check
- tabs and URL/query state
- lookups and dependent controls
- safe invalid validation
- cancel/no-save behavior for mutation-capable forms
- loading, empty, error, retry, permission, and disabled states when safely triggerable
- non-side-effect navigation, API, job, report, export, and integration signals

Use `EXCLUDED_SCAFFOLDING` only when placeholder/setup/future intent is evidenced. Use
`UNRESOLVED_CLASSIFICATION` when intent is ambiguous. Do not turn either into an application
blocker without evidence that the surface is expected to work.

## Adaptive execution and recovery

For every navigation or state-changing action, verify URL/query, route identity, and resolved
content. Use one complete settle window and one fresh, verified retry. Preserve first and final
observations, actual wait/retry information, and the reason for the final classification.

Before each browser action, reacquire current page state and the target by accessible name and
nearby context. Never reuse stale element identifiers. A single screenshot-confirmed coordinate
fallback is acceptable only when the accessible target is visibly present but unreliable; record
that tooling limitation and do not repeat it.

If a browser tab/frame/session or automation context is lost, verify the run identity, recover once,
and classify dependent rows as tooling `NOT_TESTED` if recovery fails. Never select an unrelated tab
or call the application broken solely because the tool lost its target. Group a blocker across a
surface family only when independent observations prove the same application/dependency condition;
a shared blocker is not a pass.

If URL, heading, content, accessibility state, or screenshot disagree, record `STATE_CONFLICT`,
cleanly re-enter once, and stop dependent checks until the state is resolved. Continue independent
families after recovery when their liveness is verified.

## Data and evidence hygiene

For parameterized surfaces, use a safe observed link or documented fixture. If no qualifying data
exists, mark the row `BLOCKED` with `NO_QUALIFYING_DATA`, record the bounded search and next action,
and never invent an identifier or deep link.

Capture screenshots, traces, responses, and logs for failures, retries, and representative
checkpoints when the selected tool can retain them. Redact secrets, credentials, callbacks, tokens,
cookies, PII, and client-sensitive values before saving. If export is unavailable, record
`NOT_RETAINED` and the strongest remaining evidence; do not claim the artifact exists.

Every non-pass row needs a clean link when one was safely observed, or an explicit explanation why
no safe link exists. Keep browser/tooling findings separate from application findings. A UI toast or
page load does not prove that an API, job, export, notification, or integration succeeded; verify
its canonical safe signal or mark that backend row `NOT_TESTED`/`BLOCKED`.

## Closure checklist

Before the final verdict:

- every discovered row has one status
- every required row is `PASS`, `NOT_APPLICABLE` with a reason, or explicitly blocked/failed/not tested
- route/surface, behavior/control, backend, and artifact denominators are closed before showing percentages
- all blockers, flakes, missing-data conditions, unsafe actions, and inventory gaps have evidence and next actions
- CRUD preflight and no-save flow audits exist for every mutation-capable surface, even when writes are ineligible
- the report distinguishes application, environment/access, data-quality, tooling, and coverage-process findings
