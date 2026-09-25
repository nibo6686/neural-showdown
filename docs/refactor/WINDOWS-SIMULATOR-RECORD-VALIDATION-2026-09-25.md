# Windows simulator-to-record validation — 2026-09-25

## Verdict and source identity

`WINDOWS_SIMULATOR_RECORD_PASS`; `ENV-001` remains blocked on repository-owned
Python dependency/lock policy and clean-environment proof.

- Base commit: `3ddc5fc3060e8da287425e4d08a71a2ffd77184a`.
- Transferred patch: `C:\Users\cloud\Downloads\neural-stellar-review.patch`.
- Verified patch SHA-256:
  `968e3f9318e6b67e6585afec1c74e1f4442ef875a11fd47164eb6e71f0140018`.
- Before application, forward-check passed and reverse-check failed. The patch was
  applied once. Its five review/status/manifest paths remain present; the
  validator now reports `already_applied_with_subsequent_reviewed_manifest_changes`.
- Transferred 25-file review digest:
  `4db82b9bc57984bf051f03b201bf022e0744ba03c8840239adeded5d362f33c3`.
- Prior reviewed Windows portability digest (26 files):
  `58e8a6ff8aab60b59d86e376f1872fb6cd3930dc4f2444eb1490187ca7cef34f`.
- Current reviewed cross-platform-preparation digest (28 files):
  `14dff114f66482bbdf5cb10bd0bc3579f339da2af878395b7b74c2f7913f71b0`.
  The manifest retains both earlier digests and records each narrower review
  layer separately.

The patch contributes `docs/PROJECT_STATUS.md`, `docs/codex_review_state.md`,
the PIPELINE-002 checkpoint, `docs/refactor/WORK_ITEMS.md`, and the coverage
manifest. Subsequent Windows differences are limited to the Python bridge and
test, coverage checker and manifest evidence, reusable validation/comparison
tools, the portable reference fixture, and this checkpoint. No simulator
behavior source was changed after the transferred review.
`faithful_complete_episode: false` remains mandatory.

## Portability review decisions

### Python UTF-8 bridge — accepted

Node sends JSON over a byte pipe. On Windows, reading through the locale text
wrapper changed `Pokémon` to mojibake before Python recomputed the observable
prefix hash. `pipeline_record.main()` now gives `json.load` the binary stdin
stream when available, with the existing text-stream fallback for in-process
tests. Unicode protocol text and its TypeScript identity are preserved.

Regression coverage uses a cp1252 `TextIOWrapper` over UTF-8 bytes. Separate
cases prove malformed UTF-8 and malformed JSON return exit 2, write no record,
emit the existing `pipeline-record validation failed` diagnostic, and do not
leak a traceback. No schema or valid-record identity rule changed.

### Coverage hashing — accepted

Local reviewed sources must be valid UTF-8. Their digest hashes each sorted
relative path, NUL separators, and content after replacing only CRLF pairs with
LF. Lone CR, BOMs, all other bytes/text changes, file names, membership, and
ordering remain identity-bearing. Invalid UTF-8 fails the checker instead of
being silently replaced. Installed npm simulator trees retain their existing raw
package-byte policy.

Synthetic checks prove CRLF invariance, lone-CR sensitivity, substantive-text
sensitivity, invalid-UTF-8 rejection, inventory drift, missing classifications,
and that digest-only edits cannot attest semantic review. The Windows validator
is the 26th hashed source so its checks and failure semantics cannot drift while
coverage still passes.

### Windows validator — accepted

`scripts/validate_windows_simulator_record.ps1` verifies the exact base and patch
hash, distinguishes not-applied, exactly-applied, subsequently reviewed manifest
changes, and partial/unrecognized states, then runs setup, focused tests and
coverage. Every step reports a name, status and exit code plus an aggregate
`validation_result`; independent steps continue after ordinary native-command
failure. A pre-attestation run demonstrated the intended failure path: all
behavioral checks passed, coverage reported digest drift, and the validator
returned 1. The final attested run returned 0.

## Environment, commands and results

- Windows 11 Home 64-bit `10.0.26200`, build `26200.9550`; PowerShell Core
  `7.1.4`.
- README Conda environment `D:\Anaconda\envs\neuralgpu`; Python `3.11.14`, pip
  `26.0.1`, pytest `9.0.3`. All required packages were already present.
- Node `v24.15.0`; npm `11.12.1`.
- `npm ci` resolved the committed lock: `pokemon-showdown@0.11.10`,
  `@smogon/calc@0.11.0`, TypeScript `5.9.3`, `@types/node@18.19.130`.

Final command:

```powershell
.\scripts\validate_windows_simulator_record.ps1 `
  -PatchPath C:\Users\cloud\Downloads\neural-stellar-review.patch
```

Final summarized results:

- Base, patch hash, and applied-with-reviewed-local-changes state: passed.
- Locked npm install and native TypeScript build: passed.
- Focused transitions, forced switches, settling, bounded episodes, Illusion /
  Stellar lifecycle, fresh-process repeatability and Python publication: 85/85.
- Focused Python record/lineage: 22 passed plus 22 subtests.
- Coverage: 142 classified condition/effect IDs, 112 parser tokens and 86 literal
  emitter tokens; digest matched; all ten synthetic checks passed.
- Matching earlier full TypeScript run: 169/169. It is reused because subsequent
  edits touched only the Python bridge/test, coverage tooling/evidence, validator
  and checkpoint.

Fresh-process equality on this Windows host covers transition, branch, state,
observation, belief, action and record IDs plus bounded-episode outcome/lineage.
Mac evidence remains separate reviewed evidence. No exported Mac result artifact
was available for direct byte comparison, so this establishes native Windows
repeatability and matching reviewed behavior, not verified cross-platform
byte-for-byte equality.

The npm install is reproducible from the committed lock. The Conda environment is
pre-existing and isolated, not a clean environment created from repository
metadata. Resolved versions are host evidence, not a supported Python matrix.

## Cross-platform comparison handoff

Windows reference:
`tests/fixtures/simulator_record_comparison_windows_v1.json`, SHA-256
`d983dbb2d83c944271590c2dd5c28dc693968ec1813aac9af1edb1ca4125e1d4`.
It contains the base/patch/28-file source identity and per-file normalized hashes,
Windows runtime evidence (including Node's exact Python subprocess executable),
explicit machine-specific JSON pointers, and six deterministic scenarios:
joint transition, one-sided KO replacement, natural Arena Trap rejection and
recovery, terminal restoration, Unicode record validation, and the 55-transition
bounded episode. Private simulator snapshots are not serialized.

Windows generation command:

```powershell
.\scripts\generate_cross_platform_simulator_record.ps1
```

Two fresh Windows generations were byte-identical and the comparator returned
`equal_portable_results:true`. Synthetic comparator probes classified an OS
release difference under `machine_specific_differences` with exit 0 and reported
a changed episode count at its exact JSON pointer under `actionable_differences`
with exit 1.

On macOS, after reproducing this exact source state and using its existing Python
environment, run:

```bash
npm ci --prefix sim-core
npm run build --prefix sim-core
PYTHON=/absolute/path/to/python3 node sim-core/scripts/simulator-record-comparison.cjs generate \
  --patch /absolute/path/to/neural-stellar-review.patch \
  --output artifacts/validation/simulator_record_comparison_macos_v1.json
node sim-core/scripts/simulator-record-comparison.cjs compare \
  --reference tests/fixtures/simulator_record_comparison_windows_v1.json \
  --candidate artifacts/validation/simulator_record_comparison_macos_v1.json
```

The generator first requires the reviewed coverage digest to match. The compare
step exits nonzero for any source or scenario difference and prints its exact JSON
pointer; declared environment differences remain visible but non-actionable.
macOS results are not yet available, so cross-platform equality remains pending.

## Remaining ENV-001 blocker and next task

The repository still declares only `Python >=3.8`; it has no approved runtime /
test dependency declarations, Python lock/constraints or Conda specification.
Replay fixtures remain optional for this simulator-only milestone.

**Single next task:** choose and commit the Python dependency/lock mechanism,
then recreate the simulator-validation environment from that metadata and rerun
the same validator as the clean-environment proof.
