# Prompt 12 prerequisite — native legacy-ID contract correction

Paste this into the implementation conversation. Execute this prerequisite only and return for review; the source-verifier implementation remains paused at its contract boundary.

```text
Use $implement-plan. Repository: C:\Users\cloud\Downloads\neural\final. Read repository protocol/review state, initiative plan, perspective-fidelity-prompt12-report.md, perspective-fidelity-prompt12-lead-review.md, frozen PERSPECTIVE_KNOWLEDGE.md and the nine external legacy reference positions. Lead confirms a finite contract incompatibility. Correct it locally; do not implement the rest of Prompt12 yet.

Exact authorized writes:
- docs/contracts/PERSPECTIVE_KNOWLEDGE.md: clarify native external legacy spellings versus internal knowledge IDs and historical structural placeholders.
- docs/contracts/fixtures/perspective-knowledge-v1/schema.json: change only the nine external fields listed below, retaining their existing requiredness/nullability. Tiny explicit field-specific definitions are allowed if needed; no generic any-prefix domain.
- sim-core/src/perspective_knowledge.ts and trainer/src/neural/perspective_knowledge.py: change only schema.json's content hash pin. No other runtime logic change.
- sim-core/tests/perspective_knowledge.test.ts and trainer/tests/test_perspective_knowledge.py: new bounded regression tests; preserve all prior tests.
- docs/contracts/fixtures/perspective-knowledge-v1/check_contract.py: add the bounded new regression packet check without changing historical tests.
- New docs/contracts/fixtures/perspective-knowledge-v1/legacy-id-regressions.json: independent explicit positive/negative scalar vectors by field, including correctly joined structural audit controls if useful. Existing author generators, case/negative manifests, fixtures, identity vectors and profile/reference/property artifacts remain unchanged.
- New perspective-fidelity-prompt12c-* report/diff/hash/validation artifacts only. Preserve original Prompt12 evidence and lead docs.

Nine exact fields and native domains (each suffix is exactly 64 lowercase hex digits):
owner_binding.observation_id -> obs-
owner_binding.belief_id -> belief- (still nullable)
owner_binding.actor_record_id -> datarec- (still nullable)
binding.input_observation and binding.successor_observation -> obs-
binding.input_belief and binding.successor_belief -> belief- (still nullable)
binding.transition -> transition- (still nullable)
binding.actor_record -> datarec- (still nullable)

At those nine positions only, retain sha256: followed by64 lowercase hex digits as compatibility for original isolated structural canaries. Explicitly document that these are untrusted external placeholders, never a remapping of native IDs, and cannot satisfy the real source/legacy verifier unless an actual supported legacy object with that exact identity exists (current legacy validators do not produce such objects). Structural acceptance establishes spelling/joins only. Internal knowledge object IDs, internal edges, profile commitments and identities continue to require sha256: exactly; native prefixes must reject there. No schema version/profile change is needed for this finite pre-adoption compatibility correction; record new schema content hash and preserve previous hash in evidence.

Use exact field-specific anchored domains. Reject wrong native kinds, action IDs in these fields, missing/extra prefix or colon, uppercase/nonhex suffixes, wrong length, whitespace/newline, number/bool/container values, and null at nonnullable positions. Preserve allowed nulls and historical placeholder fixtures. Neither a prefix nor a matching hash establishes authority.

Tests: reproduce baseline native-ID shape rejection using actual four validated v1/v2 both-owner witness IDs, then show each native domain is admitted at its correct scalar position. Add coordinated independently resealed structural audits with matching boundary/binding legacy references for both owners and all knowledge forms; call these structure positives only, not source/history authenticity positives. Do not claim all original108 one-field mutations should become full-audit positives: after fixing shape, deliberately inconsistent references must still reject at their join. Include resealed wrong-kind/malformed IDs and internal-domain contamination controls. Preserve immutability and exact limited CLI diagnostic; actual TS wire -> Python structure check runs with encoding overrides unset.

Ensure all nine external scalar positions match the manifest and no other schema node changes. Independently compare schema before/after JSON paths, requiredness and nullability. Assert retained profile IDs, typed-reference graph, all16 identity vectors, historical26 positives/43 negatives and the retained69-case runtime matrix remain byte/status compatible. No historical canary regeneration. Fresh build, paired core suites, contract checker/new packet checks, relevant ordinary/Unicode legacy validation controls and whitespace checks suffice; no full Node suite or long witness.

Bounded fresh-context read-only subagents allowed for schema-delta review and independent negative/oracle verification. Parent integrates. Return correction-relative local diff, exact schema JSON-path delta, old/new content pin, complete before/after hashes and preservation inventory, command results, independent review and limitations under perspective-fidelity-prompt12c-*. No source-seam module or TS DATA identity adapter implementation in this prerequisite. No manifest/attestation/aggregate readiness update, broader contract change, source/provider/extractor/publication adoption, installs, external loading/upload, datasets/training, staging/commit/push/PR/merge or later work. Return for lead review; only then can Prompt12 runtime work resume.
```
