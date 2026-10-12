# Prompt 7 local maintenance candidate

M01 is ready for independent lead review. Registration and omission checks are complete locally; the live provenance gate intentionally remains closed. Branch `main`, HEAD `accab655c26ada18124e790b16d5770c8bd17894`, prior dirty candidates preserved. No runtime source, semantic classification, format identity, review/attestation, aggregate status or historical evidence changed. No commit/publication or later task.

Scope/files: only the manifest's local file list/candidate sha256, `check-simulator-coverage.cjs`, and `simulator_coverage.test.ts`; other writes are Prompt 7 artifacts. Candidate-relative `local.diff` excludes earlier accepted changes. `source-hashes.json` records all three before/after hashes and 258 protected files verified unchanged. `reviewed-field-comparison.json` proves every non-owned manifest byte unchanged, including all reviewed fields and attestation text.

Exact file-list delta: 121 to 137 inputs, 16 additions, zero removals. Added helpers: `../trainer/src/neural/pipeline_json_wire.py`, `../trainer/src/neural/public_field.py`, `src/public_field.ts`. Added tests: `tests/pipeline_utf8_transport.test.ts`, `tests/perspective_field_semantics.test.ts`, `../trainer/tests/test_perspective_field_semantics.py`. Narrow closure adds `../docs/contracts/OBSERVABLE_STATE.md` (accepted Prompt 5 clarification) and the nine directly consumed `../docs/planning/perspective-fidelity-prompt4-{weather,terrain,pseudo_weather}-{lifecycle-ledger,terminal-ledger,reproduction}.json` files. These are test inputs, not planning logs. `dependencies.json` enumerates every exact path, role, importer/caller and raw hash; all 15 accepted implementation-delta hashes match prior packets, including already-listed `record_identity.test.ts` and `test_pipeline_record.py`.

Final candidate sha256: `8879baab101f4981ee3412f89faf5a8d13996975f5844503083f30ed90ee242b`. Reviewed sha256 remains `dced76bcc1b24ebb015fdc45befc6b584f1b7bf623ddbb3447906be45e37b757`. `digest-inputs.json` gives all 137 sorted paths, raw/normalized hashes and byte lengths. Existing algorithm is unchanged: concatenate each UTF-8 manifest path, NUL, validated UTF-8 file content with CRLF normalized to LF, NUL, then SHA-256. Lone CR remains identity-bearing. The manifest itself is not an input; the changed checker and TS harness are inputs.

Checks: all 16 additions are independently required. Removing one from an in-memory manifest and recomputing the shortened list digest now produces the specific required-source error. Red evidence showed all 16 lacked that diagnosis before the guard; it did not establish that unrelated review gates were bypassed. Seven mutations (six helpers/tests plus already-listed observable_state.ts) reject through the same digest-error function used by the live checker. Missing listed file rejects. Only isolated temporary source copies were mutated; protected originals stayed untouched. Existing requirements and synthetic controls remain.

Coverage review addressed rehashed omission, substantive mutation, missing-file, CRLF/UTF-8 and candidate-versus-reviewed controls. TS harness independently asserts each omission/mutation and compares normal --self-test to actual checker exit/stderr, preventing control success from masquerading as live acceptance.

Exact commands, cwd, times, counts, exits and logs are in `validation.json`. Commands run with Node's existing executable and `PYTHON=D:/Anaconda/envs/neuralgpu/python.exe`, encoding overrides removed in each shell and inherited absent by children; no Python runtime test was needed for provenance-only changes.

| Command/check | Exit/outcome |
|---|---|
| Baseline checker | 1: existing listed-source digest drift |
| Red omission self-test | 1: all 16 omission-specific controls fail |
| Green/final --reachability-self-test | 0: 16 omissions, seven mutations, missing file, two positives and existing controls pass |
| npm run build | 0 |
| Focused TS coverage harness | 0: 2/2, 15.399s |
| Final checker and --self-test | 1 each: only candidate/reviewed mismatch; synthetic controls pass |
| git diff --check | 0 |

No timeout, skipped case or unexpected remaining failure. The existing --reachability-self-test exits0 after controls; --self-test continues to the live gate. Neither changes reviewed digests. Actual rejection is `Manifest incomplete: local coverage sources are not bound to a separate semantic-review digest`.

Inspected: repository protocol/review history/current status, initiative plan, Prompt 7, Prompt 2/5/6 lead reviews, Prompt 3 M01 proposal, Prompt 5/6 hashes/dependencies, explicit manifest/checker/harness and direct field/transport imports/file reads. Matching-source Prompt 2 transport, Prompt 5 field matrix and Prompt 6 regression evidence are reused; no semantic suite, full battle matrix or long witness rerun.

Limitations: broad owner/replay knowledge and fidelity gaps remain outside scope. Historical review exclusions remain intact. No additional necessary omission was found in the narrowly inspected closure after these additions; this is not a repository-wide completeness claim. Independent lead review and its separate attestation decision remain required before the live gate can pass. Next action: review this local diff and dependency packet; no worker attestation is proposed.
