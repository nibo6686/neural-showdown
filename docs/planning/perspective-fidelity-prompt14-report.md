# Prompt 14 (S01b) report

Candidate for lead review; new files only, no existing file edited, nothing staged/committed/installed.

Write set: sim-core/src/request_knowledge.ts; trainer/src/neural/request_knowledge.py; sim-core/tests/request_knowledge.test.ts; trainer/tests/test_request_knowledge.py; docs/contracts/REQUEST_KNOWLEDGE.md; docs/planning/perspective-fidelity-prompt14-{witness.cjs, check-candidate.py, progress.md, run.log, *.log, validation.json, hashes.json, artifact-hashes.json, record-ids.json, local.diff, dependencies.json, report.md}.

Results (check-candidate, encoding overrides unset): build ok; new TS 11/11; new Python 15 OK; unchanged prompt13 characterization TS 19/19 and Python 8 OK; retained TS 44/44, perspective-knowledge TS 83/83, retained Python 93 OK; contract checker ok; git diff --check ok; 1195 protected entries unchanged, 0 unexpected files (only lead plan file drift). 28 witness cases, 110 case/version/owner records; TS and Python records byte-identical.

Review: fresh-context read-only reviewer used; two bugs fixed (registry_bound for requestless/terminal; validator raw grammar looser than builder), others listed as limits in the memo.
