# Prompt 14 (S01b) lead review

Date: 2026-10-10. Accepted locally: `request-knowledge/v1` sidecar (TS + Python builders/validator, docs/contracts/REQUEST_KNOWLEDGE.md). New files only; no production/identity/legal-action change.

## Lead verification (final version, encoding overrides unset)
Checker rerun: build ok; new TS 12/12; new Python 19 OK; S01a characterization unchanged TS 19/19, Python 8; retained TS pipeline/identity 44/44; retained TS knowledge 83/83; retained Python 93 OK; contract checker ok; whitespace ok; 1,195 protected entries unchanged, only lead plan drift, 0 unexpected. (Worker report.md describes round one: use these counts.)

## Independent review (fresh context) and correction round
Fixed: builder/validator string-cap, wait+noCancel and terminal-request consistency; lock value renamed `no_hard_lock` with lock derivation; vocabulary text (derived-false is sidecar-local, not PERSPECTIVE known_absent; S01c adapter must emit unknown); fresh_delivery stated as procedural/advisory; rqid positive literal; missing Python negatives; TS lock table exact.

## Remaining limits (carry forward)
fresh_delivery self-asserted, TS has no registry check; validator shares builder helpers (flag/move derivation independent) and reads private _REGISTRIES; builder TypeError/KeyError on malformed observation; some TS/Python error-code divergences; witness is test-owned; singles/gen9 only; sidecar not yet published in bundles/episodes.

## Next: S01c (production boundary, design-first)
Retain raw delivered request per boundary, publish sidecar in new bundle/episode versions, fix restored/terminal stale-request retention, K-fact adapter (derived flags as unknown). Touches pipeline_integration.ts, pipeline_record.py, env_manager.ts: requires a design checkpoint (exact file/key list, version plan, identity preservation) before code.
