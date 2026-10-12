# Prompt 12 (PK-02B-Source) lead review

Date: 2026-10-10. Implemented by a Claude Code worker subagent; lead reviewed with a fresh-context read-only reviewer and reran all checks.

## Verdict
Accepted locally as non-publishing infrastructure only: process-local source registry capability, separate verified legacy-context capability, and the entry check joining a structurally valid audit to both. No semantic, completeness or publication claim.

## Lead verification (encoding overrides unset)
- Full candidate checker rerun after corrections: build; new TS 21/21; new Python 19 OK; retained TS core 62/62; retained Python core 28 OK; contract checker; legacy validators TS 15/15, Python 46 OK; whitespace; 1,195 protected entries unchanged, 0 unexpected files.
- Candidate hashes match worker report: ts 65e9031a, py fa081c09, ts test 0baeaa2f, py test 85ebe735 (prefixes).

## Corrections made after review
`missing_capabilities` always lists `original_provider`; `test_witness_matched` renamed `test_only_unverified`; exact rejection codes pinned; Python `__context__` payload retention fixed with test; boundary-row-only negatives added (rejected by structure; new joins are defence in depth).

## Lead-confirmed assumptions
1. Delivery cursor = projected public record count after the write that produced the request (consistent with contract line on exclusive indexed prefix).
2. `origin.battle_key` must equal the legacy `battle_id` at the seam. This is a seam binding choice, not frozen contract text; M02/S02 must keep it or revise explicitly.

## Limits
Registry/audits/legacy bundles share one capture; original delivery is test-only (no provider); forced-switch/revival/episode envelopes unsupported; Python capability token readable by importers (trusted-caller scope); TS/Python adapter-typing and integer-check strictness differ; `perspective-fidelity-prompt12-witness.cjs` accepted as test-owned evidence. M02 must register the new modules, witness and the TS DATA-identity port.

## Next
S01 (Prompt 13): raw request knownness before normalization.
