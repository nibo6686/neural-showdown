# Prompt29 lead decision — 0.11.11 target approved for migration planning

**Date:** 2026-10-12. **Verdict:** source/artifact impact assessment accepted; select verified npm 0.11.11 as the proposed active target before B3. Upgrade execution is not yet authorized.

The lead inspected the assessment, source matrix and migration proposal; all assessment evidence hashes and 1,379 frozen inputs match. Both npm tarball SHA-512 SRI and SHA-1 values were independently recomputed against saved registry metadata and match. No tests/imports/builds were run. Target artifact SHA-256 is `49af14aaed1084887f756372c7386c9987905930cc848ed31e9202c10c592d66`; target gitHead is `739a5e1fee432ad80ff7136d70cca993be358b59`.

## Settled compatibility direction

1. **Historical readers:** retain 0.11.10 manifests, raw fixtures, IDs, attestations and version-bound structural/semantic readers as historical scope. No second active engine in the default environment and no cross-version re-simulation claim. Dispatch must use supported explicit version/profile metadata; do not broaden a version check to accept both while applying one version's rules. An unversioned legacy input can retain existing explicitly historical handling, never be auto-promoted to target scope. The plan must identify concrete reader APIs and tests affected; accidental fallback is forbidden.
2. **Snapshots:** no 0.11.10/unknown-provenance snapshot import into 0.11.11. Initial target B2 scope is held same-runtime session snapshots and validated parent/serialization occurrence only. Do not add a caller-supplied version string as authority. A portable versioned snapshot import contract, if necessary for an existing entry point, is a separate reviewed boundary before enabling that entry point on the target. Preserve old snapshot bytes and identity algorithms.
3. **Replay grammar:** explicit audited compatibility profile for the two exact Natural Cure forms; native target uses its exact source form. No broad optional-tag relaxation. Replay grammar admission is independent of native version/source authority and does not certify original-owner identity or complete knowledge. Other changed reachable forms need their finite source dispositions and focused controls.
4. **Knowledge sources:** the accepted 0.11.10 K-source profile is protected and cannot authorize 0.11.11 native facts. No B4/source/Python bridge adoption is included in dependency migration. Explicit unsupported target calls are preferable to mislabeling them.
5. **Fidelity claim:** preserve the historical flag meaning. Target-generated results must not inherit 0.11.10 positive-fidelity assurance merely because structural validators pass; target eligibility requires an explicit independently reviewed target scope. Do not copy old reviewed digests into the target manifest.

## Sequencing

Prompt30 drafts a bounded migration plan and exact acceptance gates using these decisions. Separate version/profile/restore compatibility design from package activation and target source/grammar adoption where the intermediate state is safe and independently verifiable. Keep changes to shared mutable contracts sequential. Do not invent scaffolding that is needed only to make an unsafe intermediate engine switch appear useful.

The plan must cover changed public-before-request delivery timing, generator/format inventories, exact changed reachable grammar, B1/B2 target wiring, fresh forced/Revival B2 witnesses, target provenance and fidelity gating. Reuse equivalent historical mathematical vectors/source conclusions explicitly; fresh runtime gates are still required. No blanket 179-check or long-chain rerun is authorized by this assessment. B3 waits for accepted target migration.

No installation, lock changes, node_modules replacement, production/contract edits, commits, publication or training is authorized by this decision. The lead owns plan acceptance and later execution/publication boundaries.
