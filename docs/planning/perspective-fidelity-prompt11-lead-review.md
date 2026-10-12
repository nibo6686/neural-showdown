# Prompt 11 lead review — returned for bounded corrections

2026-10-10. Candidate HEAD `accab655c26ada18124e790b16d5770c8bd17894`. PK-02A is not accepted. No source-verifier implementation is authorized by this review.

## Findings

1. **P1 — Crosswalk permits an opponent roster.** `sim-core/src/perspective_knowledge.ts:423` and `trainer/src/neural/perspective_knowledge.py:394` check the appearance owner and certificate owner, but do not check the roster owner. In `replay-full.json`, take p2's crosswalk, change its roster and dedicated certificate subject to `p1:roster:1`, and reseal all identities. Both runtimes return structural success. This violates the owner-only starting crosswalk without requiring source truth adjudication. The projection branch already checks both identities.
2. **P2 — Original delivery observation cursor is not joined.** TS fact-evidence checks around lines 382–383 and Python around 351–355 skip the observation join when original initialization evidence has no public record indices. Change the known immutable item in `sim-full.json` from `observed_at:0` to `99` and reseal. Both runtimes accept, although the referenced initialization source declares delivery cursor 0. Check the declared source/cursor relationship; genuine source authority remains deferred.
3. **P2 — Empty containers exceed nesting limit.** TS parser/canonicalizer zero-based depth and Python parser's `MAX_DEPTH+1` permit 33 nested empty arrays. Both reject the same nesting with a scalar at its leaf. The contract requires nesting at most 32. This also passes a fully resealed `sim-full.json` with the 33-container string in `raw_request.json`. Count open containers consistently for lexical and object APIs, independently of leaf type.

These are fresh independent reproductions, not stale-hash rejects. Lead used the tests' independent resealer and checked both Python and compiled TS on the same serialized candidates. No production repairs were made.

## Evidence and scope

Fresh lead runs: Python 21 tests passed (13.836s), compiled TS 54 passed (10.290s), fresh build exited 0, retained contract checker passed 26 positives/43 negatives/16 vectors and its representation/coverage subsets, and `git diff --check` exited 0. Encoding overrides were unset for focused runtime tests. Existing tests do not cover the three findings.

Three fresh-context read-only subagents separately reviewed parsing/identity, structural closure and trust/privacy. Parser review found the nesting defect; closure review found the owner/cursor defects; trust/privacy review found no bounded blocker. These are integrating reviews, not final FAC-08 acceptance.

All four candidate source/test hashes match the worker packet. Read-only comparison against the 1,088-file baseline found only the lead-owned initiative plan changed after the worker packet; the other 1,087 match. This intentional roadmap refresh is separate from implementation scope and is not a worker preservation failure. Historical worker reports remain unmodified.

The fixed diagnostic, explicit non-publishing CLI, private-safe errors and hash-pinned dependency loading remain appropriate. Source truth, certificate attribution/writer feasibility, allowed unknowns, completeness, actual legacy-envelope verification and trusted projection/publication remain deferred. Passing structure is insufficient for any of those claims. No attestation, publication, commit, dataset or training action occurred.

## Next action

Return Prompt 11 for the three corrections in `perspective-fidelity-prompt11-revision.md`. Preserve the original candidate/evidence and provide a revision-relative diff and updated validation. Review the revision before PK-02B-Source. This is the first lead return on this boundary; after two unsuccessful revision returns, reassess scope/cause under the initiative plan.
