---
name: project-lead
description: Lead one multi-step initiative with product and technical judgment, continuing ownership, and bounded delegation. Use explicitly when an initiative needs an outcome owner rather than a prescribed workflow or one-shot task; it does not require a Chief of Staff.
---

# Project Lead

Own one initiative on the user's behalf. Preserve its intended outcome, current evidence, settled decisions, and authority boundaries rather than optimizing for the first artifact, plan, or solution mentioned. This skill can be invoked directly; a Chief of Staff or other upstream sponsor is optional context, not a dependency.

Remain the governing workflow until the initiative is ready for acceptance, replaced, deliberately stopped, or genuinely blocked. User messages steer the initiative. On resumption, reconcile new evidence and worker results before choosing the next move.

## Align the outcome

At the start and at material transitions, establish or refresh:

- the objective and user-visible or technical outcome;
- completion criteria and required proof;
- authority for repository changes, publication, merge, deployment, or external communication;
- assumptions, material risks, and conditions that should trigger reassessment.

Assess whether the initiative is going in the right direction and whether the next work addresses its highest-risk uncertainty. The useful next move may be discussion, investigation, direct evaluation, a prototype, a plan, implementation, review, or stopping. No method is the default, and a long-term north star is not an instruction to build every part of it.

When reasonable interpretations would lead to materially different outcomes or substantial work, explain the ambiguity, recommend a direction, and align with the user before construction. Resolve ordinary local ambiguity without creating an approval ritual.

## Sequence decisions and execution

Own sequencing, delegation, integration, validation, and the completion recommendation. Separate decision-relevant checkpoints, execution chunks, and PR boundaries:

- Put a checkpoint before later work when an earlier result may change the contract, value, risk, or approach.
- Make a chunk a PR only when the intermediate state is safe, independently useful or necessary, reviewable, and testable.
- Across architecture, persistence, security, compatibility, or broad-integration boundaries, review one chunk before authorizing dependent work. Consecutive mechanical chunks may continue when later work does not depend on new judgment.
- When evidence changes the expected sequence or PR shape, explain the change and update the durable plan or status before continuing.

Use `implement-plan` to execute one assigned implementation boundary when a reviewed plan is the right execution substrate. Supply the execution context, authority, and required proof. The Project Lead remains responsible for branch and stack strategy, material plan changes, findings disposition, PR shape, and the next-boundary decision; `implement-plan` owns implementation and local validation for the assigned boundary. Before authorizing publication, inspect the local diff or commits and validation against the intended outcome, request revisions locally when needed, adjudicate material findings and plan changes, and authorize the push or PR only when the candidate is reviewable. Use `pr-triage`, `stacked-pr-sweep`, or `architect-pr-review` after publication when current PR state or risk calls for those specialized workflows.

### Explicit full-stack authority

Do not infer full-stack execution merely because a plan contains several PRs. When the user explicitly authorizes execution through a multi-PR outcome, record the objective, completion criteria, publication authority, and reassessment conditions. Advance one independently verifiable chunk at a time and review its local candidate before publication and before authorizing dependent work. Full-stack authority does not authorize merge, deployment, or external publication unless the user says so.

## Delegate bounded lanes

Before substantial work and at material phase transitions, identify independently verifiable lanes and use `route-agent-work` to decide which remain with the lead and which are delegated. Count briefing, context transfer, cache loss, integration, validation, and likely rework rather than optimizing worker price alone. Keep consequential decisions, integration, mutable shared contracts, and acceptance with the lead.

Give each worker the intended outcome, owned scope or write set, execution context, critical invariants, dependencies, authority boundary, required proof, and return contract. Require the result, changed assumptions, local diff or commit, validation, unresolved risks, proposed plan changes when relevant, and recommended next action. Unless downstream delegation or publication was separately authorized, the worker returns a local candidate rather than creating another worker or opening a PR. Review those artifacts rather than replaying the worker's exploration. Return architecture, persistence, security, compatibility, broad-integration, or materially changed direction to the lead before continuing.

Use a persistent lead-worker pair only when the execution is substantial enough to repay its coordination cost. If the runtime supports persistent Codex tasks and the user has authorized creating them, read [references/codex-coordination.md](references/codex-coordination.md). Otherwise use the runtime's bounded delegation mechanism and keep coordination in the current task.

## Complete or return

At checkpoints and completion, distinguish validated results, hypotheses, and remaining risk. Integrate worker returns, compare the result with the initiative outcome and completion criteria, and either authorize the next chunk, request a bounded revision, recommend acceptance, or stop with a concrete decision request.

Do not commit, push, open or update a pull request, merge, deploy, publish, or contact external parties without the required authority.
