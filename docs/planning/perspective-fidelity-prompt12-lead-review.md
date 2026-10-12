# Prompt 12 blocker review — contract correction required

2026-10-10. HEAD `accab655c26ada18124e790b16d5770c8bd17894`. The blocker is accepted as valid; Prompt 12 runtime implementation remains incomplete, not accepted.

The frozen schema wrongly applies the internal `sha256:` ID spelling to nine external legacy positions. Actual old objects use exact typed IDs: observation `obs-`, belief `belief-`, transition `transition-`, actor DATA record `datarec-`, each followed by 64 lowercase hexadecimal digits. This contradicts the requirement to retain and join actual legacy identities. It is a contract integration defect independent of Windows.

Fresh lead evidence: generated a pinned ordinary transition per v1/v2 with seed [101,202,303,404] and new lead-owned battle IDs; both owner bundles passed TS `validatePipelineLinkedRecordBundle` and Python `validate_pipeline_bundle` (four total). Only IDs were printed, DATA/private objects remained local, and sessions closed in finally. Fresh independently resealed native observation substitution rejects at `schema union` in both knowledge cores; every table/root identity was independently checked. All 1,171 protected baseline files match. Worker-reported 108 controls cover all nine positions/both schemas/owners/knowledge forms; those isolated mutations are scalar incompatibility evidence, not genuine source/history positives.

Independent read-only review confirms the nine external positions are distinct from internal graph edges. The proposed finite correction is sound. There is no reason to rename/re-hash old objects or convert their IDs to new commitments. No source capability, original provider, complete knowledge or legacy seam has been implemented.

## Decision

Authorize the contract-only correction described in `perspective-fidelity-prompt12-contract-correction.md`: native field-specific spelling plus retained historical structural `sha256:` stand-ins at exactly nine external positions; two schema content-pin updates; paired core regressions and a separately named contract-checker regression packet. Stand-ins remain untrusted placeholders and cannot satisfy actual legacy validation. Internal identities, profile IDs, historical fixture/vector bytes, nullability and typed-reference paths remain unchanged.

This is a concrete implementation blocker, satisfying the roadmap's exception for additional contract work. Return the correction for review before resuming Prompt 12 runtime code. It is not an authorization for a broad contract redesign.

The TS ordinary validator returns void and lacks a DATA record ID. The resumed Prompt 12 may use a narrow internal DATA-001 identity adapter in its already scoped new TS module, only after actual legacy validation and only matching the existing Python identity payload/canonical bytes. Require independent ASCII/control/BMP/astral Unicode parity; no emitted DATA, new identity semantics or authority granted by hashing. This is a deferred implementation requirement, not work in the correction task. Unsupported legacy envelope kinds still reject explicitly.

No original worker evidence was rewritten, no production files repaired, no attestation updated, and no commit/publication/dataset/training action occurred. Source trust, actual cross-process authority, fact semantics, replay attribution and completeness remain later gates.
