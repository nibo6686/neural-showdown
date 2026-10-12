---
name: update-docs
description: Use when code changes require documentation updates, cleanup, or new docs, especially when behavior, commands, architecture, workflows, or operator guidance changed.
---

# Update Docs

## When to use

- Use this skill when behavior, commands, architecture, workflows, configuration, or user/operator guidance changed.
- Use it to update existing docs, create a new doc when no good home exists, or clean up stale documentation after implementation.
- Prefer editing the most relevant existing doc over creating a new file.

## Inputs

- Optional changed files or diff scope
- Optional target doc path
- Optional feature, plan, or workflow context
- If no scope is provided, inspect the current changes and infer the impacted documentation surface

## Workflow

1. Determine the documentation impact.
- Review the changed files and identify whether behavior, commands, architecture, config, workflow steps, or testing guidance changed.
- If the change is internal-only and does not alter durable reader-facing understanding, record that no doc update is needed.

2. Find the best documentation home.
- Prefer updating an existing doc that already owns the topic.
- Search likely homes first:
  - `docs/toolkit/` for toolkit behavior and configuration
  - `docs/hub/` for Hub behavior or deployment
  - `docs/features/` for feature-specific behavior
  - `docs/dev-workflow/` for developer workflows and agent workflows
  - `docs/architecture/` for architecture or boundary changes
  - `docs/planning/` only for plan/status documents, not durable user guidance
- For language-specific runbooks, baselines, or operator guidance, prefer `docs/languages/<language>/` when the topic is owned by one language rather than the toolkit as a whole
- Create a new doc only when the information does not fit an existing owner cleanly.

3. Update or create documentation.
- Keep the documentation concrete and scoped to the actual change.
- Update commands, examples, file paths, behavior descriptions, and caveats to match the code.
- Remove stale steps, outdated caveats, duplicated explanations, or temporary rollout notes that no longer apply.
- When creating a new doc, choose a concise path and title consistent with neighboring docs.

4. Clean up documentation quality.
- Prefer concise, durable phrasing over narrative churn.
- Remove speculative notes, obsolete migration guidance, and stale TODO-style text unless it still materially helps readers.
- Keep examples accurate and minimal.
- Preserve genuinely useful context for operators and maintainers.

5. Verify the doc update.
- Check referenced file paths, commands, and neighboring docs for consistency.
- When commands changed, verify the documented command shape against the code or command entrypoint.
- If links or references were updated, spot-check them.

6. Report the result.
- Summarize which docs were updated or created and why.
- If no documentation update was required, say so explicitly.

## Notes

- Do not create documentation just to narrate obvious code changes.
- Documentation debt that is unrelated to the active change can be noted, but should not be folded into the current slice unless it materially improves clarity at low risk.
