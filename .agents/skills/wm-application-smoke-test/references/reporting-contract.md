# Machine-readable reporting contract

Use this reference for automation or CI. Emit one run summary and one row for every discovered
surface, behavior, backend capability, exclusion, and CRUD preflight. Keep the JSON compact enough
to inspect and preserve the human-readable report alongside it.

The human-readable report must present the actual run results before the final verdict. Put every
non-pass row first and include its expected result, actual observed result, reason/classification,
clean observed route or command link when available, evidence, repeatable recipe, and next action.
Then list passing rows and end with a clearly labeled final verdict. A verdict without row-level
evidence is incomplete; if no non-pass rows exist, state that explicitly.

When an existing runner emits a standard artifact such as JUnit XML, preserve it and report its
path or retention status alongside the WM report. The WM JSON is supplemental: it carries richer
status and safety metadata and does not replace native runner output.

```json
{
  "verdict": "READY|READY_WITH_LIMITATIONS|NOT_READY|NOT_TESTED",
  "target": "application and environment",
  "scope": "application, domain, feature, or flow",
  "mode": "smoke|full|automation",
  "executionSurface": "browser|automation|http|cli|none",
  "coverageClosure": "CLOSED|OPEN",
  "manualSmokeTestRequired": false,
  "counts": {
    "required": 0,
    "pass": 0,
    "fail": 0,
    "blocked": 0,
    "flaky": 0,
    "notTested": 0,
    "notApplicable": 0,
    "unsafeNotExecuted": 0,
    "excludedScaffolding": 0,
    "unresolvedClassification": 0,
    "ownershipUnresolved": 0
  },
  "rows": [
    {
      "id": "surface-or-behavior-id",
      "kind": "surface|behavior|backend|crud-preflight|exclusion|ownership-gap",
      "name": "human-readable name",
      "status": "PASS|FAIL|BLOCKED|FLAKY|NOT_TESTED|NOT_APPLICABLE|UNSAFE_NOT_EXECUTED|EXCLUDED_SCAFFOLDING|UNRESOLVED_CLASSIFICATION|OWNERSHIP_UNRESOLVED",
      "required": true,
      "expected": "what should happen",
      "observed": "what happened",
      "routeLink": "clean observed URL or null",
      "classification": "application|environment-access|data-quality|browser-tool|coverage-process|inventory-gap|unsafe|scaffolding|unresolved-classification",
      "evidence": [],
      "reason": "required for every non-PASS row",
      "recipe": "repeatable steps for every non-PASS row",
      "nextAction": "smallest follow-up"
    }
  ],
  "findings": [],
  "artifacts": []
}
```

Rules:

- Compute counts and percentages from actual reconciled rows; do not infer coverage from a route
  shell, a parent page, a success toast, or a rounded checklist.
- Keep `routeLink`/target links clean and observed. Use `null` plus a reason when no safe link exists;
  never synthesize parameterized URLs.
- Separate application failures from environment/access, data-quality, browser/tooling, and
  coverage-process findings.
- A `BLOCKED` or `NOT_TESTED` row is not a pass. An unsafe action is not a failure when it was
  intentionally excluded; keep it visible as `UNSAFE_NOT_EXECUTED`.
- Do not include secrets, authentication callbacks, tokens, cookies, storage state, PII, or raw
  sensitive response bodies in JSON or artifact paths.
