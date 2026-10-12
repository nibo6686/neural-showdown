---
name: model-routing-advisor
description: Before carrying out any user request that may produce work, select an appropriate Codex model and reasoning level, then automatically route eligible bounded work to one sub-agent using that exact override. Apply to coding, file changes, research, testing, debugging, review, planning deliverables, and other executable tasks even when the user does not name this skill; use advisory or manual fallback only when the task is advice-only, top-level-only, unauthorized, unsafe to delegate, or exact overrides are unavailable.
---

# Model Routing Advisor

## Objective

Choose the least expensive verified available model and lowest sufficient reasoning level that can reliably complete the task. Prefer automatic delegation for safe, bounded work when it is materially useful and the runtime supports exact overrides. Treat a verified mismatch between that recommendation and the current top-level model or reasoning level as a material delegation signal, including for an authorized bounded planning or research deliverable. Effective-setting verification is a post-spawn check, not a prerequisite for spawning. Do not hardcode model names or claim pricing, availability, or capabilities that have not been verified. Do not ask the user to manually switch the top-level model when automatic delegation is possible and appropriate.

## Installation and configuration scope

This skill is distributed as a Codex-native bundle. Codex owns installation and asks whether the user wants **Global** or **Project/Local** scope. **Global** makes the skill available across projects; **Project/Local** limits it to the selected project. Do not prompt for installation choices at runtime, execute an installer, or modify `AGENTS.md` files.

The bundle intentionally contains no root-level `AGENTS.md`, because a generic ZIP importer could apply that file project-locally without asking the user. Once installed, follow the instruction chain that Codex provides and respect higher-priority system, platform, security, privacy, and user instructions.

At runtime, follow the instruction chain that Codex provides and use the selected installation scope. Respect higher-priority system, platform, security, privacy, and user instructions. A skill installation alone does not make routing mandatory; task eligibility, whether the recommendation differs from the current top-level setting, and exact override support control the execution mode. Effective-setting verification happens after spawning and controls what the parent may claim about the result.

## Implicit preflight

Apply this skill before beginning any user request that implies an artifact, investigation, plan, code change, test run, or other bounded work. Do not wait for the user to say `$model-routing-advisor` or to ask why delegation did not happen. Show the compact recommendation first. If the task is eligible and exact overrides are supported, create the one permitted sub-agent immediately; do not wait for user confirmation or post-spawn metadata. A recommendation marked **Advisory** is not an instruction to spawn for a pure advice-only conversation: spawn only after the task has an authorized bounded deliverable and the runtime supports the exact override.

## Workflow

1. Inspect the user's task, any explicit model preference, current top-level model and reasoning metadata, current runtime model metadata, account/workspace availability, delegation support, effective-setting verification support, and whether this agent is already a delegated child. Do this preflight implicitly for ordinary work; explicit invocation is optional.
2. Respect instruction hierarchy and authority boundaries. This skill does not override system, platform, security, privacy, user, or other higher-priority instructions.
3. Classify the task by judgment, ambiguity, risk, workload, verification needs, safe parallelism, authorization, and whether delegation materially improves reliability. A planning-mode state is not advice-only by itself: an authorized bounded plan, research brief, or other planning artifact is eligible work. Do not delegate pure advice-only conversations with no bounded deliverable, live interactive work, top-level-only authority, unavailable/private context, or unsafe overlapping writes.
4. Choose the minimum capable model tier and lowest sufficient reasoning effort from the verified runtime catalog. Use runtime metadata as the source of truth for availability, supported reasoning levels, and pricing when available. If public model information is needed and runtime metadata is unavailable, consult current official OpenAI documentation, but do not infer account availability or exact subagent support from public documentation alone. If price cannot be verified, label cost optimization as uncertain rather than claiming the selected model is least expensive.
5. Choose one execution mode:
   - **Automatic delegation:** use when the task is safe, bounded, authorized, an exact model/reasoning override is supported, and this agent is the parent. If the verified recommendation differs from the current top-level model or reasoning level, delegate immediately; this mismatch is sufficient evidence that delegation is materially useful, including in planning mode. If current top-level model metadata is unavailable, do not block an otherwise eligible delegation solely because the mismatch cannot be confirmed. When the settings already match, delegate when it independently improves reliability or throughput. Spawn at most one subagent immediately with the original task, relevant scope, selected override, and an explicit instruction not to spawn descendants. Verify effective settings after the subagent is created when the runtime exposes them.
   - **Manual switch required:** use only when the task must run in the top-level context and changing the top-level model or reasoning is necessary.
   - **Advisory:** use for pure advice-only requests with no bounded deliverable, unauthorized execution, or when exact override support cannot be verified. Do not classify an authorized bounded planning deliverable as advisory solely because the conversation is in planning mode. If the user authorized execution and exact override support is verified, do not fall back merely because post-spawn effective-setting metadata is unavailable; spawn and state the verification limitation.
6. For automatic delegation, report the compact recommendation before delegating, do not wait for user confirmation, then verify the subagent identifier, requested override, effective model, effective reasoning level, output, and any changed files before reporting completion. Confirm that a mismatch-triggered delegation used the recommended override rather than silently inheriting the top-level settings.
7. If the requested model or reasoning level is unavailable or unsupported, do not claim exact delegation and use the appropriate fallback. If the override is accepted but effective settings are unverifiable after spawn, do not suppress the delegation; report the verification limitation instead.
8. Reassess when discovery materially changes the task. Escalate for ambiguity, coupled integration, safety risk, or architecture only when verified runtime metadata supports the escalation. A delegated child must not re-delegate.

### Evidence standard

Treat model availability, supported reasoning levels, pricing, and exact sub-agent support as verified only when they come from the current runtime catalog or a tool response that explicitly reports them. Treat an effective override as verified only after spawning, when the created sub-agent's returned settings or authoritative task metadata show the requested model and reasoning level were accepted. A requested override, a model name in a prompt, or public documentation alone is not sufficient evidence to claim effective settings, but lack of post-spawn metadata is not a reason to prevent an otherwise eligible spawn.

## Execution Modes

### Automatic delegation

Require an exact model and reasoning override for the sub-agent. Pass the original task, relevant scope, selected model, selected reasoning level, and an explicit no-descendants instruction. Create the subagent as soon as the task is eligible and the exact override is supported; do not wait for effective-setting metadata. Do not tell the user to switch models or reply `continue`.

Use one writer per file or tightly shared scope. Delegate independent read-only investigation, bounded planning/research, or isolated implementation only. Treat sub-agent output as evidence: verify the effective override, reopen changed files, and run meaningful validation before claiming success. The parent remains responsible for integration and the final answer.

### Human-facing output formatting

Format narrative recommendations for Markdown rendering:

- Bold every title label and use Title Case for multi-word labels: `**Recommended Model:**`, `**Reasoning Level:**`, `**Mode:**`, `**Confidence:**`, `**Why:**`, and `**Escalate If:**`.
- Use Title Case for categorical values where appropriate, such as `Low`, `High`, `Automatic Delegation`, `Manual Switch Required`, and `Advisory`.
- Preserve exact model identifiers, JSON keys, command tokens, quoted text, and natural-language explanations. Do not force Pascal Case onto values where capitalization would reduce fidelity or readability.
- Keep formatted narrative examples outside fenced code blocks so the bold Markdown labels render for the user. Keep structured JSON in a fenced `json` block and preserve its machine-readable key names.

### Manual switch required

Use only when automatic delegation cannot apply and changing the top-level model or reasoning is necessary. Render this block in the ordinary final response and end the turn:

**Recommended Model:** `<exact available model name>`  
**Reasoning Level:** `<available level>`  
**Mode:** `Manual Switch Required`  
**Why:** `<one or two concrete task signals>`  
**Pending Request:** `<short, faithful restatement>`  
**Next Action:** Change the setting, then reply `continue`.

On `continue`, recover the pending request, re-check available metadata when possible, and resume. If the selected model does not match the recommendation, explain the tradeoff and ask for confirmation before proceeding.

### Advisory

Return the recommendation and reason. Stop unless the user has authorized execution with the configured model. Do not imply that a model change occurred. Planning mode alone is not a reason to stop if the user authorized a bounded planning deliverable and eligible automatic delegation is available.

## Routing Rules

- Prefer a fast/affordable tier for inventories, extraction, simple searches, test runs, log reduction, and mechanical edits with clear ownership.
- Prefer a balanced tier for ordinary implementation, bounded refactors, routine debugging, and targeted research with clear verification.
- Prefer a frontier tier for architecture, security-sensitive work, difficult debugging, conflicting evidence, integration decisions, and final high-risk review.
- Set the reliability bar from judgment, ambiguity, risk, workload, and verification requirements.
- Eliminate models that cannot clear that bar; among the verified candidates, choose the least expensive available option. Start at the lowest sufficient reasoning effort and increase reasoning before upgrading model tier when capability is otherwise sufficient.
- Apply cost awareness before delegation: the recommendation selects the minimum sufficient tier and reasoning effort, while a verified mismatch determines whether the eligible task should be delegated. Avoid redundant delegation when the current top-level setting already matches and delegation adds no material reliability or throughput.
- Do not hardcode model names or treat examples as evergreen defaults. Resolve current candidates from the runtime catalog. Public documentation may inform general model characteristics, but runtime/account availability and exact override support must still be verified locally.
- If pricing, availability, or reasoning support cannot be verified, disclose the uncertainty and choose the lowest sufficient verified capability rather than claiming a cost-optimal recommendation.

## Recommendation Output

State the recommendation compactly before delegating or pausing:

**Recommended Model:** `<available model or tier>`  
**Reasoning Level:** `<available level>`  
**Mode:** `<Automatic Delegation | Manual Switch Required | Advisory>`  
**Confidence:** `<Low | Medium | High>`  
**Why:** `<one or two concrete task signals>`  
**Escalate If:** `<specific condition>`

For structured output, use:

```json
{
  "recommended_model": "<available model or null>",
  "reasoning_effort": "<available level or null>",
  "mode": "automatic_delegation|manual_switch_required|advisory",
  "confidence": 0.0,
  "signals": ["<evidence>"],
  "escalation_trigger": "<condition>",
  "metadata_source": "<runtime catalog | official documentation | unavailable>",
  "cost_verified": false,
  "effective_override_verified": false,
  "delegation_depth": 0,
  "delegate_with_exact_override": true,
  "pause_before_execution": false
}
```

## Guardrails

- Honor an explicit user-selected model when supported; do not silently substitute an unavailable model or reasoning level.
- Never invent model names, prices, latency, context limits, or capabilities. Do not hardcode a model list as an evergreen source of truth.
- Do not delegate work that requires top-level-only authority, unavailable context, a single interactive conversation, or unsafe overlapping writes.
- Do not create a manual-switch pause when exact sub-agent overrides are available and delegation is appropriate. Conversely, do not claim automatic delegation when exact overrides cannot be verified. Missing post-spawn effective-setting metadata limits what can be claimed about the result, but does not prevent the spawn.
- Create at most one subagent for a task. A delegated subagent must not spawn descendants.
- Do not use multiple agents with overlapping write scopes.
- Preserve the original task intent when delegating. Keep the parent responsible for integration, effective-setting verification, output verification, and the final answer.
- Treat this skill as subordinate to system, platform, security, privacy, user, and other higher-priority instructions.

## Examples

- "Scan the repository for API endpoints" -> use the lowest-cost verified catalog model and low or medium reasoning when delegation is safe and materially useful.
- "Implement isolated form validation and run its tests" -> use the lowest-cost verified model that clears the reliability bar, likely with medium reasoning.
- "In planning mode, produce an implementation plan with milestones and risks" -> treat the authorized plan as a bounded deliverable; if the verified recommendation differs from the current top-level setting, delegate immediately with the exact override.
- "Choose an authentication architecture and assess security implications" -> select a higher-capability verified model and reasoning only when the task signals justify it; retain final integration and review in the parent.
- "The task needs the user's live top-level browser session and no sub-agent override exists" -> provide a manual-switch recommendation only if a higher top-level setting is necessary.
