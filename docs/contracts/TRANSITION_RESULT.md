# TransitionResult Contract

**Status:** Historical placeholder; superseded by the accepted
[`SEEDED_TRANSITION.md`](SEEDED_TRANSITION.md) contract.

The authoritative `seeded-transition/v1` contract defines simulator version,
seed/RNG provenance, parent/branch identity, ordered event evidence, and the
boundary between simulator state and observable successor state. This file does
not define a second transition schema. PIPELINE-001's record linkage is accepted
within its joint-actionable scope; see
[`PIPELINE_INTEGRATION.md`](PIPELINE_INTEGRATION.md) and
[`../PROJECT_STATUS.md`](../PROJECT_STATUS.md).

## StepResult request reporting — PIPELINE-002 first slice

`StepResultOptions.include_wait_requests` defaults to false. Opting in reports
the addressed player's current `wait:true` request in `StepResult.requests`,
with its existing request ID (possibly null), side data and empty legal-action
set. It does not turn that request into a pending choice. `view_players` still
limits which private requests and views are returned. `LocalBattleEnv.getRequest`
and the decision-drain predicate continue to expose only pending actionable
requests; legacy callers retain their default response shape.

Submission clears the reported actionable request until a new request arrives.
Restoration replays private request data into the player's tracker, but uses
Showdown's saved choice-completion state to suppress re-offering an already
consumed request. Wait requests remain distinct from absent requests. Opt-in
terminal results report null requests, and terminal status takes precedence
in pipeline classification.

This is an additive reporting option using existing request/observation fields,
not a new action or transition schema. `seeded-transition/v1` still requires two
actionable requests. The request-reporting slice received separate scoped
semantic acceptance on 2026-09-24; the coverage attestation includes its
environment regressions. This does not accept one-sided execution or complete
episodes. See the [review checkpoint](../refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md).
