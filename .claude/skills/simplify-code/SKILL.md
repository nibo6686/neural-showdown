---
name: simplify-code
description: Use when reviewing changed code or specific files for unnecessary comments, redundant documentation, low-grade fallbacks, over-engineered abstractions, and safe opportunities to simplify or refactor overly complex code.
---

# Simplify Code

## When to use

- Use this skill after implementing code, during cleanup, or before opening a PR.
- Prefer this skill when the goal is to make the code simpler and sharper without changing the intended behavior.
- Use it on explicit files when the scope is known.
- Otherwise default to reviewing the currently changed files in the working tree.

## Inputs

- Optional file path(s)
- Optional diff or review scope
- If no scope is provided, inspect the current staged and unstaged changes

## Workflow

1. Determine review scope.
- If file paths are provided, inspect only those files.
- Otherwise review the current staged and unstaged changes.
- If there are no target files or diffs, report that there is nothing to simplify.

2. Inspect the code with a simplification lens.
- Look for:
  - comments that explain obvious code instead of non-obvious intent
  - ticket or task-reference comments that do not belong in source
  - temporary PR-stage comments such as "for now", "placeholder", "later", "follow-up", or `PR-0*` references that should be removed, made durable, or tracked in the plan
  - redundant docstrings or inline documentation
  - unnecessary helper layers, wrappers, or abstractions
  - conditionals or indirection added only to support weak or low-value fallback behavior
  - deterministic fallbacks that mask real failures or silently degrade output quality
  - logging noise, debug leftovers, or boilerplate cleanup candidates
  - duplicated branching or over-split logic that could be made direct

3. Simplify safely.
- Remove or tighten comments that do not add durable value.
- Keep comments that explain why, invariants, edge cases, or architectural constraints.
- Prefer direct implementations over unnecessary indirection.
- Prefer explicit failures over low-grade fallback behavior when the fallback would hide problems or reduce quality.
- Collapse redundant branches or helper layers when the code becomes easier to read and maintain.
- Avoid broad rewrites when a local cleanup achieves most of the value.

4. Respect guardrails.
- Do not remove fallbacks that are clearly required for real compatibility, safety, or customer dependencies.
- Do not remove documentation that is part of a public contract, schema explanation, or non-obvious behavior.
- Do not refactor so aggressively that the change ceases to be reviewable.
- If a deeper refactor is warranted but too large for the current slice, note it and defer it explicitly.

5. Verify the cleanup.
- Run the smallest focused checks needed for the simplified code.
- If the cleanup affects behavior or shared flows, expand verification appropriately.

6. Report the result.
- Summarize files changed and the classes of simplification applied.
- If no meaningful simplification was justified, say so explicitly.

## Notes

- This skill is for quality cleanup, not speculative redesign.
- Simpler code is preferred, but only when the resulting behavior and operational posture are clearer and safer.
