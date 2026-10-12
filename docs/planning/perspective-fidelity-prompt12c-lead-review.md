# Prompt 12C lead review (native legacy-ID contract correction)

Date: 2026-10-10. Reviewer: lead (continued in Claude Code after Codex credits ran out).

## Verdict
Accepted locally for the finite spelling/structure correction only. Prompt 12 runtime work may resume.

## Independent checks (lead, encoding overrides unset)
- Baseline preservation: 1,194 baseline entries, 8 owned; 0 non-owned files changed.
- Fresh `tsc` build passes.
- Python `test_perspective_knowledge`: 28 tests OK.
- TS `perspective_knowledge` suite: all dots, no failures.
- Contract checker: 26 positives / 43 negatives / 16 vectors unchanged, plus legacy-id packet 51 positives / 192 negatives.
- `git diff --check`: no whitespace errors (CRLF warnings only, pre-existing).
- Report states the nine-path schema delta and pin-only runtime edits; delta file lists the same nine paths.

## Limits (unchanged)
Native prefixes (`obs-`, `belief-`, `datarec-`, `transition-`) are spelling only. Neither prefix nor hash agreement confers authority. No source semantics, completeness or publication claim. New schema hash and legacy-id packet need later provenance reconciliation (M02).

## Not re-run by lead
Fresh real v1/v2 legacy witnesses, the 69-case retained matrix, and the 243-vector runner (worker-reported).
