# Agent Protocol

- Read `docs/codex_review_state.md` before every task.
- Use narrow scopes; do not repeat repository-wide inventory work.
- Inspect only files necessary for the assigned item.
- Return memos under 1,000 words with: Scope, Files inspected, Commands run, Confirmed facts, Findings, Unknowns, Acceptance criteria, Next action.
- Do not modify production source during preparation.
- Do not install packages, train models, fetch replays, start servers, or replace sim-core.
- Only the orchestrator may update aggregate status files, especially `STATUS.md` and `docs/codex_review_state.md`.
- Preserve exact paths, line references, IDs, and provenance.
- Stop and write a continuation note if context usage becomes high.
- Do not begin `ACTION-001` until `STATE-001` has been reviewed and accepted.

