# Prompt 2 — UTF-8 wire transport candidate

## Execution contract and chosen write set (before edits)

2026-10-09: PR-02 only, local candidate under `implement-plan`; main HEAD
`accab655c26ada18124e790b16d5770c8bd17894`. No commit, publication, contract,
manifest, attestation, aggregate-status update or PR-03 work authorized.

Chosen exact write set:

- `trainer/src/neural/pipeline_json_wire.py`: small shared binary-first JSON
  reader and UTF-8 text writer with ordinary text-stream fallback.
- `trainer/src/neural/pipeline_record.py`: reuse the reader and route complete
  publication/error text through the writer, retaining canonical algorithms.
- `sim-core/tests/pipeline_episode.test.ts`: two inline Python JSON ingress
  callers (`pythonCheckOriginRecordIdentity`, `pythonPublishBundles`).
- `sim-core/tests/pipeline_utf8_transport.test.ts`: focused real Node/Python
  CLI publication, identity, malformed-input and rejection regression tests.
- `README.md`: bridge usage and focused Unicode verification.
- This report.

Preserved preexisting Prompt 1 test SHA256:
`DB1E08DE96E455FE65A5678E1222DBB429F2E2F03DF1C15E04B77C0FF744796C`;
Prompt 1 report SHA256:
`2A149058FA6682EBD9A0566702B4C381215FE3988A55F9E7AEB40C7DFB199835`.
Existing untracked planning/smoke files remain owned by prior work.

## Diagnosis and progress

Read the PR-02 plan, worker prompt, repository protocol/review history, current
PROJECT_STATUS reconciliation and Windows smoke report. Existing interpreter
`D:\Anaconda\envs\neuralgpu\python.exe` reports Python 3.11.14. No AGENTS.md
found. Source/import verification will use repository trainer/src.

The baseline production `pipeline_record.main()` already binary-loads stdin
and emits ASCII-safe JSON. Its valid Unicode ingress must not be described as
broken. The inline identity probe and batch publication wrapper instead use
`json.load(sys.stdin)`, which decodes Node UTF-8 through locale cp1252. Plain
rejection stderr uses a text write and can fail on Unicode outside cp1252.
Node callers already preserve `process.env.PYTHON || 'python3'`, send UTF-8 and
decode output as UTF-8; no launcher configuration change is needed.

Next: add real-process regressions, record baseline red/green distinctions,
then implement the shared wire boundary and run focused validation. Encoding
workaround variables will be removed case-insensitively only from command or
test-child environments; no persistent/global environment changes.

### Chunk 1 — real subprocess baseline

Added three focused Node tests using a legitimate test-owned Showdown snapshot,
accented Pokémon nicknames `Flabébé` and `Pokémon`, both v2 perspectives, and
the actual production CLI. `npm.cmd run build --prefix sim-core`: exit 0.
`node --test --test-isolation=none --test-reporter=spec
sim-core/dist/tests/pipeline_utf8_transport.test.js`: exit 1, 1 passed/2 failed.
All commands select the existing interpreter through PYTHON; child environment
removes both encoding workaround keys case-insensitively.

Valid CLI publication and TypeScript-generated observation/belief/action/
transition IDs already survive the wire. Unsealed prefix tampering rejects
exit 2 with empty stdout. Locale text ingress in the inline independent identity
probe fails exit 1 with `input_observation: observation content identity mismatch`.
Malformed JSON/UTF-8 cases reject exit 2 with empty stdout. Unicode unexpected-key
diagnostic fails the exact-character assertion: stderr contains escaped
`\u672a\u77e5\U0001f600` instead of `未知😀`. Contrary to the initial risk hypothesis,
default Python stderr's backslashreplace preserves exit 2 and prevents a
traceback here; the observed defect is loss of Unicode on the UTF-8 wire.

The exact named v2 episode test also reproduced red with workaround variables
unset: exit 1, 0 passed/1 failed, 41.60s; inline identity checker raises
`input_observation: prefix identity mismatch` in the resealed foreign-origin
request control. No source was edited until this baseline completed.
An initial `node -e` interpreter probe failed only from PowerShell native argument
quoting (exit 1); the corrected here-string Node probe exited 0, showing the
exact existing interpreter and checkout `trainer/src/neural/pipeline_record.py`
import, with stdin/stdout/stderr `cp1252` and stderr `backslashreplace`.

### Chunk 2 — wire repair

Added a small shared reader/writer, retaining `json.load` byte detection and
fallback text streams without changing process-global encodings. Main still
constructs complete output only after successful validation and serializes with
the original canonical JSON options. The two inline episode helpers now read
the same production wire utility. README documents the narrow bridge behavior.
Post-edit build: exit 0. Focused transport verification follows, then the exact
episode regression and relevant existing embedded-main checks.

### Chunk 3 — review correction and final evidence

Lead review identified invalid Unicode code units in direct diagnostic paths.
Real CLI input `{"\ud800":{"root_seed":1}}` reproduced exit 1/traceback because
the nested private-key error interpolates the key directly. The focused negative
test was red, then green after UTF-8 encoding uses `backslashreplace` for invalid
code units only. Ordinary Unicode remains exact; text-stream embedding is unchanged.

Four build invocations exited 0. Final focused transport command above: exit 0,
3 passed/0 failed (1.85s); covers both perspectives, legitimate accented names,
matching canonical IDs, publication, unsealed tampering, malformed JSON/bytes,
Unicode diagnostics and invalid-surrogate rejection with exit 2/empty stdout.

Exact episode command (workarounds unset), exit 0, 1 passed/0 failed (50.65s):

```powershell
node --test --test-isolation=none --test-reporter=spec --test-name-pattern='^v2 evidence retains both owners at every commit and rejects rehashed chain tampering in TypeScript and Python$' sim-core/dist/tests/pipeline_episode.test.js
```

This completed before the invalid-surrogate-only refinement; ordinary paths are
unchanged. Existing embedding verification (PYTHONPATH=trainer/src, workarounds
unset), exit 0: 4 passed, 41 deselected, 2 subtests passed:

```powershell
& 'D:\Anaconda\envs\neuralgpu\python.exe' -m pytest trainer/tests/test_pipeline_record.py -q -k 'cli or unicode' --tb=short
```

Lead independently repeated final transport: exit 0, 3/3 (1.55s), whitespace
check exit 0 and both Prompt 1 hashes identical. Worker final whitespace check
also exits 0. Source seam: `pipeline_record.py:1359,1373,1378,1383`, shared
`pipeline_json_wire.py:7,12`, inline consumers `pipeline_episode.test.ts:457,702`.
No interpreter override, identity algorithm, validation guard or timeout changed.

Limits: existing batch wrapper is invoked only by the prohibited 1,000-turn
fixture, so that caller was source-reviewed; shared reader and embedded-main
behavior are separately exercised. No full Node suites, coverage checker,
network, server, replay, checkpoints, installation, datasets, training or
attestation performed. Reviewed digests were not refreshed; no current-digest
claim is made. Exact six-file write set remains as recorded. Next: lead accepts
or returns this local candidate; PR-03 remains outside this assignment.
