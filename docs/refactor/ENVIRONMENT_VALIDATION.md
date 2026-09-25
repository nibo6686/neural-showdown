# ENV-001 Environment Validation

Status: `BLOCKED_WITH_REMEDIATION`

Current disposition as of 2026-09-25: existing-machine simulator validation and
selected cross-platform comparison pass; ENV-001 fresh-machine recreation remains
independently pending.
The later pinned-simulator package check confirms the local Node declaration,
lock entry, and installed version agree for `pokemon-showdown@0.11.10`; it does
not resolve the Python dependency/lock policy or clean-environment validation
gaps recorded here. Existing model checkpoints are abandoned for the new
pipeline and are not part of the environment gate. See
[`../PROJECT_STATUS.md`](../PROJECT_STATUS.md).

Replay-fixture absence is not a prerequisite for the first simulator-only
milestone. The `-m replay` checks remain opt-in and may be recorded as skipped
when no `.log` fixtures exist. Replay assets are required only for replay
parity or a replay-sourced data milestone. ENV-001 remains blocked by runtime,
dependency/lock, and clean-environment policy until those are resolved.

Historical preparation flag `READY_FOR_CONTRACT_IMPLEMENTATION: NO` is superseded
by the accepted contract work in PROJECT_STATUS; it is not a current simulator-validation failure.

This document records reproducible Python/Node validation requirements. The
dependency remediation record is separate from `STATE-001`: it records
environment evidence and packaging blockers without changing the observable-
state contract. The original audit did not install packages or run commands;
subsequent user-reported validation results are recorded below.

## Verified existing environments — 2026-09-25

Use this section for simulator-record validation on the existing machines. Later
sections retain the broader environment audit and historical evidence.

| Status | Disposition |
| --- | --- |
| Existing-machine simulator validation | Passed on macOS and Windows. |
| Cross-platform comparison | Passed for six selected scenarios at source commit `117df85`; two fresh macOS runs were byte-identical, with zero actionable Windows differences. |
| Fresh-machine recreation from repository specifications | Pending: Python dependency/lock and supported-runtime policy are not established. |
| Training/data readiness | Separately gated by feature/target contracts, collection and lifecycle acceptance; `faithful_complete_episode:false`. |

| Recorded working setup | macOS | Windows |
| --- | --- | --- |
| Platform | Darwin 25.6.0, arm64 | Windows 11 Home, 10.0.26200, x64; PowerShell 7.1.4 |
| Python | 3.9.6, terminal `python3` | 3.11.14, existing `neuralgpu` Conda environment |
| Exact interpreter | `/Library/Developer/CommandLineTools/usr/bin/python3` | `D:\Anaconda\envs\neuralgpu\python.exe` |
| Node / npm | v24.21.0 / 11.19.0 | v24.15.0 / 11.12.1 |
| pytest | 8.4.2 (directly verified) | 9.0.3 (Windows checkpoint) |

macOS interpreter selection was rechecked directly and through Node's
`spawnSync(process.env.PYTHON, ...)`; both returned the path above and 3.9.6.
Windows values are recorded evidence, not a new Windows run. Exact Conda version,
environment creation recipe and complete Windows package inventory are unrecorded.
These are successful host versions, not an approved compatibility range.

### Dependencies for this scope

- Node build/runtime: existing `sim-core/node_modules` matching
  `sim-core/package-lock.json`: Showdown 0.11.10, @smogon/calc 0.11.0,
  TypeScript 5.9.3 and @types/node 18.19.130, plus locked transitive dependencies.
- Python record bridge (`neural.pipeline_record`, canonical actions and lineage):
  standard library only. Focused Python regression tests additionally need `pytest`.
  `PYTHONPATH` selects the repository package; no editable install is required.
- Training/feature workflows use NumPy, PyTorch and PyYAML; live-server workflows
  additionally use FastAPI, Pydantic and Uvicorn. Those broader packages, GPU/CUDA,
  model checkpoints and replay fixtures are not needed for the commands below.

Preserve the existing environments; no Conda creation, environment-manager change
or package installation is part of this procedure. If Node dependencies are missing,
restore them separately with the committed lock (`npm ci --prefix sim-core`).
Do not substitute `npm install` or infer a reproducible Python specification from
whatever is already installed.

### macOS: run from the repository root

```bash
cd /Users/nbolger/Desktop/neural-showdown
export PYTHON="$(python3 -c 'import sys; print(sys.executable)')"
# Recorded result: /Library/Developer/CommandLineTools/usr/bin/python3
export PYTHONPATH="$PWD/trainer/src"
"$PYTHON" -c 'import sys, pytest; print(sys.executable, sys.version); print(pytest.__version__)'
node -e 'const r=require("node:child_process").spawnSync(process.env.PYTHON,["-c","import sys; print(sys.executable)"],{stdio:"inherit"}); process.exit(r.status ?? 1)'
node --version
npm --version
npm run build --prefix sim-core
node --test sim-core/dist/tests/{transition,forced_switch,settling,pipeline_integration,pipeline_episode,simulator_coverage,illusion}.test.js
"$PYTHON" -m pytest trainer/tests/test_pipeline_record.py trainer/tests/test_dataset_lineage.py -q
npm run check:simulator-coverage --prefix sim-core
node sim-core/scripts/check-simulator-coverage.cjs --self-test
```

If terminal Python resolves differently, select the recorded executable explicitly
before running. Exported `PYTHON` is essential: Node's Python bridge/test subprocesses
use it; setting only `PYTHONPATH` or a shell alias does not select an interpreter.
Check each command's exit status; stop and diagnose any failure.

### Windows: PowerShell in the repository root

Use the existing `neuralgpu` interpreter directly; Conda activation is optional for
this scope. If activating with `conda activate neuralgpu`, still verify the exact
executable used by Node. The following sets it explicitly:

```powershell
$env:PYTHON = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src).Path
& $env:PYTHON -c 'import sys, pytest; print(sys.executable, sys.version); print(pytest.__version__)'
node -e 'const r=require("node:child_process").spawnSync(process.env.PYTHON,["-c","import sys; print(sys.executable)"],{stdio:"inherit"}); process.exit(r.status ?? 1)'
node --version
npm.cmd --version
npm.cmd run build --prefix sim-core
$tests = @('transition','forced_switch','settling','pipeline_integration','pipeline_episode','simulator_coverage','illusion') | ForEach-Object { "sim-core/dist/tests/$_.test.js" }
node --test $tests
& $env:PYTHON -m pytest trainer/tests/test_pipeline_record.py trainer/tests/test_dataset_lineage.py -q
npm.cmd run check:simulator-coverage --prefix sim-core
node sim-core/scripts/check-simulator-coverage.cjs --self-test
```

Check `$LASTEXITCODE` after each native command; a later success does not erase an
earlier failure. `node`/`npm.cmd` must resolve to the intended installation; record
`Get-Command node,npm.cmd` if they differ from the versions above.

### Evidence and comparison reproduction

See the [Windows checkpoint](WINDOWS-SIMULATOR-RECORD-VALIDATION-2026-09-25.md)
and [macOS checkpoint](MACOS-SIMULATOR-RECORD-COMPARISON-2026-09-25.md).
The reviewed 28-file digest is
`14dff114f66482bbdf5cb10bd0bc3579f339da2af878395b7b74c2f7913f71b0`.
The macOS checkpoint records exact bundle/reference hashes, commands and the nine
declared environment differences. Equality covers joint transitions, forced
switches, trap rejection/recovery, terminal restoration, Unicode records and a
bounded episode; it does not prove arbitrary battle or environment equivalence.

The historical `validate_windows_simulator_record.ps1` runs `npm ci` and checks
HEAD against `3ddc5fc`; the bundle generator also requires that base and the original
review patch. They are not ordinary current-checkout smoke commands. For historical
bundle regeneration, follow the isolated base-plus-exact-117df85-tree procedure in
the macOS checkpoint; do not change source attestations to bypass provenance guards.
The direct commands above work independently of that historical HEAD constraint.

**Next substantive pipeline task:** implement bounded Revival Blessing request
handling: retain the `reviving` signal, enumerate fainted eligible targets and
validate actor-only execution, both successor perspectives and Python publication.
Until accepted, keep explicit unsupported-boundary truncation. Fresh-machine
recreation remains a separate environment gate, not a reason to replace these
working environments.


## 1. Supported versions

### Python

- Declared minimum: Python `>=3.8` in `trainer/pyproject.toml`.
- Declared maximum: none.
- Recorded successful host versions: Python 3.9.6 (macOS) and 3.11.14 (Windows); no general support matrix established.
- Current host: `Python 3.9.6` via `python3`; the `python` command is unavailable.
- Executable: `/Library/Developer/CommandLineTools/usr/bin/python3`
- User-site packages: `/Users/nbolger/Library/Python/3.9/lib/python/site-packages`
- User-site scripts: `/Users/nbolger/Library/Python/3.9/bin`
- `python3 -m pip` resolves pip from the user site and is the authoritative package command.

The only supported Python policy currently established by repository metadata is
the declared floor `>=3.8`; no upper bound or tested compatibility range can be
established from this repository. Python 3.9.6 is current-host evidence, not a
project support guarantee. Do not raise the floor or add an upper bound until a
compatibility matrix is tested.

### Node and npm

- `sim-core/package.json` declares no `engines` or `packageManager` field.
- `pokemon-showdown@0.11.10` in the lockfile declares `node >=16.0.0`.
- Locked TypeScript `5.9.3` declares `node >=14.17`.
- Exact supported Node line is not declared; Node `>=16` is an evidence-based minimum, not a complete support policy.
- npm version is not declared. `package-lock.json` uses lockfile version 3.
- Current host: Node `v24.21.0`, npm `11.19.0`; scoped simulator validation passed.
- Node executable: `/Users/nbolger/.nvm/versions/node/v24.21.0/bin/node`
- npm executable: `/Users/nbolger/.nvm/versions/node/v24.21.0/bin/npm`
- Local sim-core packages: `/Users/nbolger/Desktop/neural-showdown/sim-core/node_modules`
- Compiled server: `/Users/nbolger/Desktop/neural-showdown/sim-core/dist/src/server.js`

## 2. Python dependencies inferred from imports

### Runtime/import dependencies

- `numpy`
- `torch`
- `fastapi`
- `pydantic`
- `uvicorn`
- `PyYAML` (`yaml` is imported dynamically by `neural.config`)

Standard-library imports are not listed. No imports requiring pandas, SciPy, scikit-learn, requests, or matplotlib were found in the reviewed scope.

### Development/test dependencies

- `pytest`
- `setuptools>=61` is the Python build-system requirement.
- NumPy and PyTorch are also required by many tests.

No Python dependency versions are declared in `trainer/pyproject.toml` or a
Python lock/constraint file. The import scan establishes package roles, not a
reproducible version policy.

### First simulator-only milestone dependency scope

The `neural.pipeline_record`, `neural.canonical_action`, and
`neural.dataset_lineage` path used by the PIPELINE bridge imports only Python
standard-library modules. The TypeScript simulator uses the exact package-lock
dependencies (`pokemon-showdown@0.11.10` and `@smogon/calc@0.11.0`); TypeScript
and Node typings are development dependencies. `pytest` is needed only to run
Python tests. NumPy, PyTorch, FastAPI, Pydantic, Uvicorn, and PyYAML belong to
the broader trainer/runtime surface, not to this one-shot simulator-record
validator. This narrows the initial smoke scope but does not close ENV-001 for
the full training/live project.

No raw replay fixtures are needed to verify seeded Showdown transitions,
observable protocol projection, Python record validation, or TypeScript/Python
record joins. Those checks must run without replay files. Replay-marked parity
selection should report the explicit skip when the configured fixture directory
is empty; do not treat that skip as simulator-only pipeline failure.

## 3. Manifest and lock decision

The appropriate declaration strategy is to add the six imported runtime packages
to `[project].dependencies` and `pytest` to an optional test/development group;
`setuptools>=61` remains the build-system requirement. Exact version specifiers
must be selected through a compatibility check; this record does not guess them.

A reproducible Python lock or constraints file is required. The mechanism is not
selected yet; it must pin or constrain the Python version and declared packages
used by focused validation. The Node side should continue using the committed
`sim-core/package-lock.json` with `npm ci`. Node runtime dependencies are exact
in `package.json`; TypeScript and Node type development entries use semver ranges
there but resolve to exact versions in the lockfile.

Successful host versions are recorded above; they do not yet define a
fresh-machine dependency specification.

## 4. sim-core build and test commands

For dependency restoration when needed (the existing-machine commands above reuse installed packages), from the repository root:

```bash
npm ci --prefix sim-core
npm run build --prefix sim-core
```

The existing package script is:

```bash
npm test --prefix sim-core
```

which rebuilds and runs the compiled Node tests.

For state-focused TypeScript validation after the build:

```bash
node --test sim-core/dist/tests/state_extractor.test.js sim-core/dist/tests/env_manager.test.js
```

## 5. Required environment variables

For Python tests that call sim-core:

```bash
export PYTHONPATH="$PWD/trainer/src"
export NEURAL_SIM_CORE_CWD="$PWD/sim-core"
export NEURAL_SIM_CORE_COMMAND_JSON='["node","dist/src/server.js"]'
```

Live checkpoint, rollout, vNext, tracing, and HTTP variables are not required for STATE-001 validation and must remain at defaults.

## 6. Focused STATE-001 commands

After dependencies and sim-core are available:

```bash
export PYTHONPATH="$PWD/trainer/src"
python3 -m pytest \
  trainer/tests/test_state_provenance_no_leakage_contracts.py \
  trainer/tests/test_tactical_state.py \
  trainer/tests/test_public_information_belief_contracts.py \
  trainer/tests/test_sim_core_parity.py \
  -q
```

The TypeScript state-focused command is:

```bash
node --test sim-core/dist/tests/state_extractor.test.js sim-core/dist/tests/env_manager.test.js
```

STATE-001 now has dedicated contract tests in
`sim-core/tests/observable_state.test.ts`; the Python feature-vector tests remain
unchanged because the adapter is shadow-only.

## 7. Clean-environment smoke procedure

1. Start from a clean checkout at the recorded baseline tag.
2. Record `python3 --version`, `node --version`, and `npm --version`.
3. Create an isolated environment with `python3 -m venv .venv-env001`.
4. Install only the approved Python lock/constraints and test dependencies; do not use an unpinned ad hoc list.
5. Run `npm ci --prefix sim-core` and `npm run build --prefix sim-core`.
6. Verify imports for NumPy, PyTorch, FastAPI, Pydantic, Uvicorn, PyYAML, and pytest.
7. Set the three sim-core variables above.
8. Run the focused Python and TypeScript commands.
9. Record versions, commands, results, and platform-specific failures.

## 8. Installation locations and accessibility

The active Python client can import NumPy, PyTorch, FastAPI, Pydantic, Uvicorn, PyYAML, and pytest from `/Users/nbolger/Library/Python/3.9/lib/python/site-packages`.

The `pytest`, `pip`, `uvicorn`, and related console scripts are under `/Users/nbolger/Library/Python/3.9/bin`, which is not currently on `PATH`. Prefer `python3 -m pytest` and `python3 -m pip`; if direct console commands are needed, use:

```bash
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
```

Node and npm are accessible through the nvm-managed paths above. sim-core dependencies and compiled output are present at the documented absolute paths. Future agents must not report these packages or clients as missing unless the paths or import checks fail.

Remaining blockers are:

1. Choose and test the supported Python version range.
2. Declare runtime and test dependencies in `trainer/pyproject.toml`.
3. Select and commit a Python lock or constraints strategy with exact, verified
   versions; inventing versions is not an acceptable remediation.
4. Re-run the clean-environment smoke procedure using that metadata.
5. Keep replay fixtures opt-in under the policy in
   [REPLAY_FIXTURES.md](REPLAY_FIXTURES.md). Their absence is not a blocker for
   the first simulator-only milestone, but replay-specific parity and data
   claims remain unverified without them.

## 9. Validation evidence

User-reported on 2026-09-22:

- `npm test --prefix sim-core`: build succeeded; 40 tests passed; 0 failed,
  including the five new observable-state tests.
- Focused compiled tests for `state_extractor` and `env_manager`: 11 tests passed; 0 failed.
- Python import smoke test passed for NumPy, PyTorch, FastAPI, Pydantic, Uvicorn, PyYAML, and pytest.
- Focused Python command collected and ran 137 tests: 132 passed, 4 skipped, and 1 failed.
- The single failure was `PublicReplaySanityTest.test_saved_replays_reproduce_public_event_prefixes_but_have_no_private_seed` in `trainer/tests/test_sim_core_parity.py:117-119`.
- That test expects at least three `.log` files under `data/replays/raw/gen9randombattle`; the directory currently contains zero. The existing `trainer/tests/fixtures/replay_sample.log` is not used by this test.
- The reported user-local package versions were: NumPy 2.0.2, PyTorch 2.8.0, FastAPI 0.128.8, Pydantic 2.13.5, Uvicorn 0.39.0, PyYAML 6.0.3, pytest 8.4.2, pip 26.0.1, setuptools 82.0.1, and wheel 0.48.0.
- A replay-independent focused subset (`test_state_provenance_no_leakage_contracts.py`, `test_tactical_state.py`, and `test_public_information_belief_contracts.py`) passed completely: 131 passed.

Current continuation validation on 2026-09-22:

- `npm run build --prefix sim-core`: passed.
- `node --test sim-core/dist/tests/observable_state.test.js`: 5 passed.
- `PYTHONPATH="$PWD/trainer/src" /Library/Developer/CommandLineTools/usr/bin/python3 -m pytest trainer/tests/test_sim_core_parity.py -q -m replay`: 2 skipped and 4 deselected because the raw fixture directory has no `.log` files.
- No replay acquisition, package installation, server start, training, live
  evaluation, or dataset generation was run.

The TypeScript portion is validated for the current environment. The Python
environment is operational, but ENV-001 remains blocked by the absence of a
committed Python dependency/runtime policy and clean-environment proof. The
missing replay fixtures block only replay-specific checks, not the first
simulator-only milestone. The current host package versions are evidence for
those runs only and are not a lock.

## Remediation required

ENV-001 becomes ready only after the dependency policy is approved, Python
dependencies are declared and locked/constrained, a supported Python/Node/npm
matrix is recorded, sim-core builds in a clean environment, and focused
replay-independent Python and TypeScript commands complete successfully. The
replay-fixture policy must be explicit; an absent fixture directory is allowed
for simulator-only acceptance, while replay-specific claims still require
fixtures.
