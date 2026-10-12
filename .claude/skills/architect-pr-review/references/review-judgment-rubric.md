# Review Judgment Rubric

This reference distills `docs/dev-workflow/review-judgment-rubric.html` for use during direct PR review.

## Core Practice

Aim a short, broad question at the part of the PR that looks risky, then investigate what the evidence shows. The value is in choosing the spot and the lens, not in running every lens against every change.

For direct PR or stack review, Codex may choose the spot itself from the diff, but it should preserve the spirit of the rubric:

- Keep questions broad enough to find unpredicted issues.
- Ground concerns in code, tests, docs, or PR context.
- Treat unanswered intent questions as questions, not findings.
- Use the rubric to focus architectural judgment, not to produce a score.

## Question Repertoire

Use these as review lenses and adapt the wording to the PR.

| Trigger | Broad question | What to investigate |
| --- | --- | --- |
| Database, IO, loops, graph traversal, result scans | Any performance considerations with those operations? | N+1s, missing indexes, full scans, unbounded materialization, work inside loops |
| Core or cross-cutting code | Does this follow the repo's language-agnostic principles in core classes? | Language branches that belong behind a registry or in a language module |
| New helper, service, or utility | Is there overlap with existing functionality? | Duplicate logic, unused abstractions, missed shared helpers |
| Prompt, chunking, extraction, resolution, classification | Has this been validated by a live eval or realistic canary? | Precision/recall/F1 movement, eval coverage, fixture realism |
| Sizeable PR or plan-linked work | Does it meet the technical and business goals of the plan? | Missing requirements, gold-plating, underspecified scope, abstraction value |
| Shared state, async, parallelism | Any thread-safety concerns with those calls? | Races, shared mutable state, unguarded caches, shared clients |
| Error handling, defaults, fallbacks | What happens when this fails? Does it fail loudly or quietly? | Silent degraded output, swallowed errors, misleading success states |
| Central signature, model, schema, or base class | Does anything else depend on this? | Toolkit, Hub, frontend, MCP, persisted evidence, API consumers |
| New behavior, command, or config | Is that documented? | Missing operator docs, command docs, architecture notes, migration notes |
| Opaque code | Can this section be explained clearly? | Hidden coupling, surprising control flow, maintainability risk |

## Direct Review Translation

When using this as a direct PR-review or stack-review skill:

1. Let the diff choose the likely spots.
2. Pick the relevant lenses.
3. Investigate evidence before writing a finding.
4. Report only high-signal findings and questions.
5. For stacks, judge intermediate PRs against the final intended system state.
6. Keep the final answer in code-review form: findings first, then open questions, validation gaps, and a brief summary.
