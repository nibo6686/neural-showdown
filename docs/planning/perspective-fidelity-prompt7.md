# Prompt 7 — Complete candidate source provenance and omission checks

Lead-authorized M01 maintenance boundary. Submit to the implementation chat; return a local candidate for separate review.

```text
Use $implement-plan and $review-plan-tests for one bounded local maintenance candidate. The project lead remains in the other conversation and controls acceptance and attestation. No further delegation or later task.

Repository: C:\Users\cloud\Downloads\neural\final. Verify HEAD/worktree, read repository protocol/review state and current status reconciliation, the initiative plan, Prompt 2/5/6 lead reviews, Prompt 3 M01 proposal and Prompt 5/6 dependency/hash reports. Prompts 1/2/5/6 are locally accepted within their scopes; original evidence must remain unchanged.

Objective: register the actual source/test dependencies of the accepted local transport and field repairs, and ensure omission or mutation cannot silently evade provenance checks. This is evidence maintenance, not new state semantics or a claim of complete perspective fidelity.

Owned write set:
- sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json: local file list and unreviewed candidate sha256 only.
- sim-core/scripts/check-simulator-coverage.cjs: required-source checks and bounded self-test controls.
- sim-core/tests/simulator_coverage.test.ts only if necessary to invoke/assert those controls.
- Task-specific perspective-fidelity-prompt7-* progress, report, local diff and dependency packet.

Record exact baseline hashes and write set before editing. No runtime source, semantic classifications, coverage scope claims, format/source-engine identity, historical reviews or aggregate-status changes. All reviewed_sha256 and review/attestation fields must remain byte-for-byte equivalent. Candidate digest changes are not review approval.

Inspect the explicit local coverage list and dependency closure narrowly. Include the new runtime helpers pipeline_json_wire.py, public_field.py and public_field.ts, plus pipeline_utf8_transport.test.ts, perspective_field_semantics.test.ts and test_perspective_field_semantics.py, using the manifest's existing path conventions. Verify existing changed files including record_identity.test.ts and test_pipeline_record.py are covered. List each addition with its role, direct importer/caller and hash; do not register every planning log indiscriminately. Return any other necessary dependency omissions with evidence, without expanding production scope.

Add explicit required-source checks so removing a required helper/test from the list fails even if the shortened list is rehashed. Keep existing requirements and CRLF-invariant hashing. Validate red/green omission controls for each newly required file, mutation controls for both runtime helpers and tests, an already-listed changed source, a missing listed file, and candidate-versus-reviewed digest mismatch. A candidate digest update alone must never attest semantic review. Use isolated temporary fixtures or in-memory manifest copies; do not mutate real protected source to demonstrate attacks.

Exercise the actual checker path and its existing self-test/test harness. Record their precise exit behavior: the real checker is expected to remain fail-closed on the candidate-versus-reviewed mismatch until separate review. Self-tests must demonstrate expected rejections without bypassing the gate. If the existing harness couples successful controls to an attested live manifest, report the distinction clearly; do not edit reviewed hashes or suppress errors merely to obtain exit 0.

Use existing Node and D:\Anaconda\envs\neuralgpu\python.exe where needed. No installs or global environment changes; encoding workarounds unset. Build if TS harness changes. Run focused coverage self-tests/checker and git diff --check. Reuse matching-source accepted transport/field/regression evidence: no full battle matrix, full Node suite or 1,000-turn witness is warranted by provenance-only edits. If a semantic change appears necessary, return its proposed scope to the lead.

Return candidate-relative diff, exact file-list delta, before/after source hashes, final computed candidate digest and its exact inputs, protected reviewed-field comparison, commands/exits/control outcomes, and memo under 1,000 words. Provide a review packet connecting each implementation delta to prior local review and validation evidence, with all remaining exclusions and limitations explicit. Maintain durable progress before compaction.

No self-attestation, reviewed digest refresh, historical evidence rewriting, commits, publication, merge, datasets, training, replay/checkpoint loading, knowledge/schema design or later tasks. Return for independent lead review before the attestation decision.
```
