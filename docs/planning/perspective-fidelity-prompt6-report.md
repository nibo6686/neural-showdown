# Prompt 6 local candidate

PR-04C is ready for lead review. The regression baseline is restored without production or contract changes. HEAD remains `accab655c26ada18124e790b16d5770c8bd17894`; existing dirty work is preserved. No commits or publication.

Scope: only `trainer/tests/test_pipeline_record.py` and `sim-core/tests/record_identity.test.ts`, plus Prompt 6 artifacts. `local.diff` compares against the pre-task dirty candidate, excluding accepted Prompt 1/2 changes. `source-hashes.json` records exact before/after hashes and 217 unchanged protected files, including every original Prompt 4 and Prompt 5 artifact and production/contracts. Original CRLF conventions are retained.

Fixture changes: the five affected methods now supply complete field objects through narrowly scoped helpers. Independent literal expectations map supported source forms to weather, terrain, Trick Room and side-condition layers. Weather upkeep/clear, terrain end and Trick Room end receive matching preceding starts. The existing prefix/identity helper updates input/successor prefixes, cursors, hashes, belief source prefixes and joins; final field changes are resealed. Weather clear stays literal `none`, terrain clear stays null, and terrain IDs remain in the existing mixed pseudo-weather list. No generic defaults were injected. All pre-existing helper bodies, including `_bundle`, `_seal_bundle` and owned ability construction, are unchanged; only the five pre-existing test methods changed. No original grammar case or publication assertion was removed or weakened. Hazard/screens retain their original v2 coverage; weather/terrain/room retain v1/v2, both owners and both boundaries.

Independent coverage: 80 added negatives span wrong values, missing field views and four lifecycle records without matching starts. All grammar and bundle identities verify before semantic rejection. API errors explicitly match public-field semantics; publication returns 2 with empty stdout and unchanged payloads. Corresponding started controls validate. No production field helper supplies expected truth.

The scalar verifier replaces its single locale text reader with `neural.pipeline_json_wire.load_json`. Numeric fixtures, 1,000 generated scalars, Unicode, lone surrogates, UTF-16 key ordering, null distinction, canonicalization and digest assertions are unchanged.

Validation uses `D:/Anaconda/envs/neuralgpu/python.exe`, `PYTHONPATH=trainer/src` (Node cwd uses `../trainer/src`), and Node `PYTHON` selecting the same executable. Every test parent removes `PYTHONUTF8` and `PYTHONIOENCODING`; children inherit their absence. The direct Node-child environment probe confirms both null while stdin still uses cp1252. Exact commands/cwd/counts/exits/times/logs are in `validation.json`.

| Check | Result | Exit |
|---|---|---|
| Five methods before repair | 130 failures; 3 main tests/256 subtests passed, 2.92s | 1 |
| Scalar before repair | 0/1; Unicode comparison mismatch, 0.267s | 1 |
| Five methods plus new negatives | 6 tests/464 subtests passed, 4.21s | 0 |
| Prompt 1 methods | 2 tests/576 subtests passed, 5.03s | 0 |
| Record/lineage/typed batch | 63 tests/4,944 subtests passed, 26.15s | 0 |
| Scalar after repair | 1/1, 0.319s | 0 |
| Identity/belief batch | 15/15, 51.328s | 0 |
| UTF-8 transport | 3/3, 2.876s | 0 |
| Python field suite | 7 tests/30 subtests, 6.75s | 0 |
| TS build; git diff --check | Pass | 0 |

No timeouts, skips or remaining required-check failures. Prompt 1's 72 rejection controls still run across eight owner/version/boundary combinations (576 subcases). A supplemental environment probe initially failed from PowerShell argument quoting; stdin script transport fixed it. Its error log is preserved; no code change resulted.

Inspected: repository protocol/review history, current status, initiative plan/Prompt 6, Prompt 5 lead review/report/matrix/failure grouping/dependencies, owned tests and identity sealing, field guards for diagnostic messages, and pinned Showdown writer callbacks. Provenance: Showdown 0.11.10 conditions.ts weather start/upkeep/end; moves.ts terrain/Trick Room and screen writers; preserved Prompt 4 ledgers and Prompt 5 dependency hashes. The Prompt 5 200-call matrix is reused because production and all dependencies are unchanged except this test file; its imported `_bundle`/`_seal_bundle` remain unchanged and the dependent Python field suite was rerun. No matrix claims were rewritten.

Unknowns/dependencies: recorded source-provenance registration drift and broader state/owner/replay knowledge gaps remain lead-owned. This candidate establishes bounded regression recovery, not full fidelity or training readiness. Acceptance criteria for this boundary are met locally; next action is lead review of the diff and evidence. No later task was started.
