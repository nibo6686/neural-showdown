# ENV-001 Environment Validation

Status: `BLOCKED_WITH_REMEDIATION`

Current disposition as of 2026-09-30: ENV-001B has a repository-owned
simulator-record Python profile and a macOS temporary-environment run. Package
installation, sim-core build, focused record tests, and Node-to-Python selection
passed for ENV-001B. Coverage-source closures are reviewed and attested for the
macOS simulator-record and broader trainer/live profiles. ENV-001C1 also has a
repository-owned broader macOS profile and a locked focused proof on the
recorded Command Line Tools Python 3.9.6 arm64 interpreter. Windows clean
recreation and ENV-001C2 remain open; these macOS results do not establish a
Python support range or Windows/PyTorch/CUDA compatibility.
Existing model checkpoints are abandoned for the new pipeline and are not part
of the environment gate. See
[`../PROJECT_STATUS.md`](../PROJECT_STATUS.md).

Replay-fixture absence is not a prerequisite for the first simulator-only
milestone. The `-m replay` checks remain opt-in and may be recorded as skipped
when no `.log` fixtures exist. Replay assets are required only for replay
parity or a replay-sourced data milestone. ENV-001 remains open pending Windows
clean recreation and ENV-001C2.

Historical preparation flag `READY_FOR_CONTRACT_IMPLEMENTATION: NO` is superseded
by the accepted contract work in PROJECT_STATUS; it is not a current simulator-validation failure.

This document records reproducible Python/Node validation requirements. The
dependency remediation record is separate from `STATE-001`: it records
environment evidence and packaging blockers without changing the observable-
state contract. The original audit did not install packages or run commands;
subsequent verified execution results are recorded below.

## ENV-001B — Simulator-record profile and macOS clean proof

`trainer/pyproject.toml` declares the `simulator-record` optional dependency
group with pytest. ENV-001B kept the then-empty `trainer-live` group separate;
ENV-001C1 now declares the broader imports in separate groups, recorded below.
The record-validation bridge uses the Python standard library. `setuptools` is
included in the generated simulator-record lock because installing the
`trainer` package uses the declared build backend.

The selected resolver is `pip-tools` / `pip-compile`. The repository-owned,
hash-checked artifact is
[`trainer/requirements/simulator-record.txt`](../../trainer/requirements/simulator-record.txt).
It was generated from the pyproject extra and build requirements with
`pip-tools 7.6.1` in an isolated resolver venv using Command Line Tools Python
3.9.6. Package versions were resolved by the tool from the package index, not
copied from the pre-existing user-site installation. The lock SHA-256 is
`401506d07d080218f8f34b620f5fcf235ab0760463851864d55d4fd6904ca11b`.

Regenerate the artifact in a temporary resolver environment with:

```bash
RESOLVER_ROOT="$(mktemp -d /private/tmp/neural-showdown-lock.XXXXXX)"
/Library/Developer/CommandLineTools/usr/bin/python3 -m venv "$RESOLVER_ROOT"
"$RESOLVER_ROOT/bin/python" -m pip install pip-tools==7.6.1
"$RESOLVER_ROOT/bin/pip-compile" \
  --extra=simulator-record \
  --all-build-deps \
  --allow-unsafe \
  --generate-hashes \
  --output-file=trainer/requirements/simulator-record.txt \
  trainer/pyproject.toml
```

The macOS clean setup uses a separate temporary venv and installs the trainer
package after its locked dependencies. It does not use the host user site:

```bash
PROOF_ROOT="$(mktemp -d /private/tmp/neural-showdown-env001b.XXXXXX)"
/Library/Developer/CommandLineTools/usr/bin/python3 -m venv "$PROOF_ROOT/proof"
export PYTHON="$PROOF_ROOT/proof/bin/python"
"$PYTHON" -m pip install --require-hashes \
  -r trainer/requirements/simulator-record.txt
"$PYTHON" -m pip install --no-deps --no-build-isolation ./trainer
npm ci --prefix sim-core
npm run build --prefix sim-core
export PYTHONPATH="$PWD/trainer/src"
node -e 'const {spawnSync}=require("node:child_process"); const r=spawnSync(process.env.PYTHON,["-c","import sys; print(sys.executable)"],{encoding:"utf8"}); const actual=(r.stdout||"").trim(); if(r.status!==0||actual!==process.env.PYTHON){process.stderr.write(r.stderr||"Python path mismatch: "+actual); process.exit(1)} console.log(actual)'
node --test sim-core/dist/tests/pipeline_integration.test.js
"$PYTHON" -m pytest \
  trainer/tests/test_pipeline_record.py \
  trainer/tests/test_dataset_lineage.py -q
npm run check:simulator-coverage --prefix sim-core
git diff --check
```

**macOS run evidence (2026-09-29):** Command Line Tools Python 3.9.6 created
`/private/tmp/neural-showdown-env001b.MsXgq1/proof`; the selected interpreter was
`/private/tmp/neural-showdown-env001b.MsXgq1/proof/bin/python`. Resolver was
`pip-tools 7.6.1` (resolver venv pip 26.0.1); the proof venv used pip 21.2.4.
The locked packages installed were `pytest 8.4.2`, `setuptools 82.0.1`,
`exceptiongroup 1.3.1`, `iniconfig 2.1.0`, `packaging 26.3`, `pluggy 1.6.0`,
`Pygments 2.21.0`, `tomli 2.4.1`, and `typing-extensions 4.16.0`.
`neural-trainer 0.1.0` installed from `./trainer`. Node was v24.21.0 / npm
11.19.0; the unchanged `sim-core/package-lock.json` SHA-256 was
`4897b92e6a6c82db2b8fe5cedb69c9b15386a0bff4d8d2a30b7a2c6d1d9a33c5`.

The same hash lock was also installed in a second temporary venv created from
the current unqualified macOS `python3` (Python 3.12.10, pip 25.0.1) at
`/private/tmp/neural-showdown-env001b.MsXgq1/current-terminal`. Under that
interpreter the pipeline integration test passed 9/9 and the Python record/
lineage tests passed 36/36. These two macOS runs are specific observed versions,
not a declared compatibility range.

- `npm ci --prefix sim-core`: passed; npm reported 15 advisories (4 moderate,
  7 high, 4 critical). The lockfile was not changed.
- `npm run build --prefix sim-core`: passed.
- Node subprocess check: passed; Node's `spawnSync(process.env.PYTHON, ...)`
  reported the temporary venv interpreter above.
- `node --test sim-core/dist/tests/pipeline_integration.test.js`: 9 passed.
- Focused Python record/lineage tests: 36 passed.
- `npm run check:simulator-coverage --prefix sim-core` (before source-list
  closure): failed with local source
  digest `5d6067858317610887ed995833e846662cea0b594845be269a91da2d438b30a8`;
  the manifest's reviewed digest is `4a43068ae878aaa5a3d6624220d424ff09cbdd5f2350c73303bfe1e5985daa77`.
  Coverage files were not changed as part of ENV-001B, so the full validation
  gate remains open.
- `git diff --check`: passed.

**Coverage-source closure review (2026-09-30): accepted and attested for the
macOS simulator-record profile only.** Added
`../trainer/requirements/simulator-record.txt` to
`local_coverage_sources.files` beside `../trainer/pyproject.toml`. The checker
hashes listed paths and normalized file contents as ordinary local inputs; the
focused regression verifies that changing or omitting the lock changes the
digest and that a missing listed lock fails closed. The recomputed local source
digest is
`da740930a51df282a0dad003810b904e9f8bfa4945f6bbfa5dd6de1c4db7c57b`, matching
the expected value. The local `sha256` and `reviewed_sha256` now bind that
digest; prior semantic attestations remain unchanged. This attestation covers
only the macOS simulator-record profile. Windows clean recreation and Windows
trainer/live packaging, including its PyTorch and accelerator decisions, remain
open; ENV-001 is not complete.

Windows will consume the same artifact through the selected Conda interpreter
in a separate authorized validation task. Use a clean/isolated Conda validation
environment or an approved clone so the existing working `neuralgpu` environment
is preserved. The current environment was not modified, and Windows clean
recreation has not been run.

```powershell
$env:PYTHON = 'D:\Anaconda\envs\neuralgpu\python.exe'
& $env:PYTHON -m pip install --require-hashes -r .\trainer\requirements\simulator-record.txt
& $env:PYTHON -m pip install --no-deps --no-build-isolation .\trainer
$env:PYTHONPATH = (Resolve-Path .\trainer\src).Path
node -e 'const {spawnSync}=require("node:child_process"); const r=spawnSync(process.env.PYTHON,["-c","import sys; print(sys.executable)"],{encoding:"utf8"}); const actual=(r.stdout||"").trim(); if(r.status!==0||actual!==process.env.PYTHON){process.stderr.write(r.stderr||"Python path mismatch: "+actual); process.exit(1)} console.log(actual)'
```

For the simulator-record profile, ENV-001C exclusions remain intentional:
PyTorch, accelerator/CUDA packages, FastAPI, Uvicorn, Pydantic, NumPy, PyYAML,
replay tooling, model dependencies, and live-server dependencies are not part of
that profile. Public replay fixtures remain optional for simulator-only checks
and are needed only for replay-specific claims.

## ENV-001C1 — macOS broader trainer/live profile

The direct-import audit of `trainer/src` found NumPy, PyYAML, PyTorch, FastAPI,
Pydantic, and Uvicorn.

- **Simulator-record:** the focused runtime bridge uses only the standard
  library; pytest is test-only and stays in the accepted `simulator-record`
  extra and lock. It is also listed in `trainer-live-test` so the broader proof
  can run focused tests from its single locked profile.
- **Broader trainer/live:** NumPy, PyYAML, FastAPI, Pydantic, and Uvicorn are
  shared imports; PyTorch is declared separately in `trainer-live-macos`.
- **Optional/legacy/deferred:** no other direct third-party imports were found
  under `trainer/src`; dependencies not supported by that import surface remain
  deferred.

`trainer/pyproject.toml` declares `trainer-live`, the platform-specific
`trainer-live-macos` extra, and `trainer-live-test` for the focused pytest
runner. The accepted `simulator-record` extra and its lock are unchanged. No
package was added based only on a historical installation. Windows CUDA/GPU
packaging remains outside this macOS profile.

The repository-owned resolver input is the macOS extras in
[`trainer/pyproject.toml`](../../trainer/pyproject.toml); the generated,
hash-checked artifact is
[`trainer/requirements/macos-trainer-live.txt`](../../trainer/requirements/macos-trainer-live.txt).
Resolver: `pip-tools==7.6.1` (`pip-compile`), installed in an isolated resolver
venv created with Command Line Tools Python 3.9.6. The resolver venv used pip
26.0.1. The generated artifact SHA-256 is
`93b4af0e5d168a205cce86e4805743b4bbc6fe668fc7c9e1052f2c5b516d6ebf`.
The lock binds versions and package hashes selected for this macOS arm64
resolution; this is not a Windows lock or a cross-platform PyTorch/CUDA claim.

Regenerate from the repository root:

```bash
RESOLVER_ROOT="$(mktemp -d /private/tmp/neural-showdown-env001c1-resolver.XXXXXX)"
/Library/Developer/CommandLineTools/usr/bin/python3 -m venv "$RESOLVER_ROOT"
"$RESOLVER_ROOT/bin/python" -m pip install pip-tools==7.6.1
"$RESOLVER_ROOT/bin/pip-compile" \
  --extra=trainer-live \
  --extra=trainer-live-macos \
  --extra=trainer-live-test \
  --all-build-deps \
  --allow-unsafe \
  --generate-hashes \
  --pip-args='--timeout 15 --retries 0' \
  --cache-dir="$RESOLVER_ROOT/pip-tools-cache" \
  --output-file=trainer/requirements/macos-trainer-live.txt \
  trainer/pyproject.toml
```

Recreate the macOS proof in a temporary venv:

```bash
PROOF_ROOT="$(mktemp -d /private/tmp/neural-showdown-env001c1.XXXXXX)"
/Library/Developer/CommandLineTools/usr/bin/python3 -m venv "$PROOF_ROOT/proof"
export PYTHON="$PROOF_ROOT/proof/bin/python"
"$PYTHON" -m pip install --require-hashes \
  -r trainer/requirements/macos-trainer-live.txt
"$PYTHON" -m pip install --no-deps --no-build-isolation ./trainer
export PYTHONPATH="$PWD/trainer/src"
"$PYTHON" -c 'import sys; print(sys.executable, sys.version)'
"$PYTHON" -c 'import numpy, yaml, torch, fastapi, pydantic, uvicorn; print("broader imports passed")'
node -e 'const {spawnSync}=require("node:child_process"); const r=spawnSync(process.env.PYTHON,["-c","import sys; print(sys.executable)"],{encoding:"utf8"}); const actual=(r.stdout||"").trim(); if(r.status!==0||actual!==process.env.PYTHON){process.stderr.write(r.stderr||"Python path mismatch: "+actual); process.exit(1)} console.log("Node selected "+actual)'
npm ci --prefix sim-core
npm run build --prefix sim-core
node --test sim-core/dist/tests/pipeline_integration.test.js
"$PYTHON" -m pytest \
  trainer/tests/test_pipeline_record.py \
  trainer/tests/test_dataset_lineage.py -q
git diff --check
```

**macOS clean proof (2026-09-30):** resolver ran under Command Line Tools
Python 3.9.6 on arm64; the final proof venv was
`/private/tmp/neural-showdown-env001c1-final.jARjuZ/proof`, using pip 21.2.4.
The local `neural-trainer 0.1.0` package installed without dependencies. Locked
versions were `annotated-doc 0.0.5`, `annotated-types 0.7.0`, `anyio 4.12.1`,
`click 8.1.8`, `exceptiongroup 1.3.1`, `fastapi 0.128.8`, `filelock 3.19.1`,
`fsspec 2025.10.0`, `h11 0.16.0`, `idna 3.20`, `iniconfig 2.1.0`,
`Jinja2 3.1.6`, `MarkupSafe 3.0.3`, `mpmath 1.3.0`, `networkx 3.2.1`,
`numpy 2.0.2`, `packaging 26.3`, `pluggy 1.6.0`, `pydantic 2.13.5`,
`pydantic-core 2.46.5`, `Pygments 2.21.0`, `pytest 8.4.2`, `PyYAML 6.0.3`,
`setuptools 82.0.1`, `starlette 0.49.3`, `sympy 1.14.0`, `tomli 2.4.1`,
`torch 2.8.0`, `typing-extensions 4.16.0`, `typing-inspection 0.4.2`, and
`uvicorn 0.39.0`.

- Broader imports passed; Node selected the temporary interpreter path above.
- `npm ci --prefix sim-core`: passed with Node v24.21.0/npm 11.19.0; it reported
  15 advisories (4 moderate, 7 high, 4 critical) and warned that install scripts
  for `esbuild@0.16.17` and `pokemon-showdown@0.11.10` were not covered by
  `allowScripts`. No Node dependency or lockfile change was made. The committed
  Node lock SHA-256 remains
  `4897b92e6a6c82db2b8fe5cedb69c9b15386a0bff4d8d2a30b7a2c6d1d9a33c5`.
- `npm run build --prefix sim-core`: passed.
- Pipeline integration test: 9 passed.
- Focused Python record/lineage tests: 36 passed.
- `git diff --check`: passed.
- The host Command Line Tools Python `pip freeze --all` SHA-256 was
  `cd7b82a9587174a529552f9dae89ce20bd97bdf17feddb6285cc2d7b98af861a`
  both before and after the temporary installs. The existing
  `simulator-record.txt` SHA-256 remains
  `401506d07d080218f8f34b620f5fcf235ab0760463851864d55d4fd6904ca11b`.

**Coverage-source review (2026-09-30): ENV-001C1 accepted and coverage-attested
for the macOS broader trainer/live profile only.** Added
`../trainer/requirements/macos-trainer-live.txt` beside the other trainer
declaration and lock inputs. The checker hashes listed file contents; existing
generic regressions cover changed content, an omitted listed source, and a
missing listed file. The recomputed local source digest is
`199d580722805f29c92077137eb0c88bc0b10138adda7724731d201bfc9cca32`; the
manifest's local `sha256` and `reviewed_sha256` now match it. The macOS lock
SHA-256 is
`93b4af0e5d168a205cce86e4805743b4bbc6fe668fc7c9e1052f2c5b516d6ebf`.
Windows clean recreation and its repository-owned Conda trainer/live profile
remain ENV-001C2; ENV-001 is not complete.

This proof establishes only the selected macOS interpreter/profile and focused
checks. It does not establish a Python support matrix, broader live-server
readiness, model/training readiness, or accelerator behavior. ENV-001C2 remains
the next environment task: repository-owned Windows Conda metadata and clean
Windows recreation/validation. ENV-001 is not complete.

## Verified existing environments — 2026-09-25

Use this section for simulator-record validation on the existing machines. Later
sections retain the broader environment audit and historical evidence.

| Status | Disposition |
| --- | --- |
| Existing-machine simulator validation | Passed on macOS and Windows. |
| Cross-platform comparison | Passed for six selected scenarios at source commit `117df85`; two fresh macOS runs were byte-identical, with zero actionable Windows differences. |
| Fresh-machine recreation from repository specifications | macOS ENV-001B simulator-record install/build/focused checks and coverage attestation passed; Windows clean recreation is pending. |
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
  standard library only. The locked `simulator-record` extra supplies `pytest`
  for focused regression tests; `setuptools` supports installation of `trainer`.
  `PYTHONPATH` selects the repository source for the simulator subprocess.
- Training/feature workflows use NumPy, PyTorch and PyYAML; live-server workflows
  additionally use FastAPI, Pydantic and Uvicorn. Those broader packages, GPU/CUDA,
  model checkpoints and replay fixtures are not needed for the commands below.

The commands below document existing-environment evidence and do not install
Python packages into those environments. The clean macOS profile setup is listed
above. If Node dependencies are missing, restore them with the committed lock
(`npm ci --prefix sim-core`); do not substitute `npm install`.

### macOS: run from the repository root

```bash
cd /Users/nbolger/Desktop/neural-showdown
export PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"
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
- ENV-001B proof base: `/Library/Developer/CommandLineTools/usr/bin/python3`
  (Python 3.9.6), selected explicitly to match the recorded environment.
- At proof time, unqualified `python3` resolved to Python 3.12.10 at
  `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3`; it was not
  used for the lock generation or clean proof.
- User-site packages: `/Users/nbolger/Library/Python/3.9/lib/python/site-packages`
- User-site scripts: `/Users/nbolger/Library/Python/3.9/bin`
- The prior Python 3.9 host used its user-site `python3 -m pip`; ENV-001B used
  only pip inside temporary venvs.

`trainer/pyproject.toml` retains a declared package floor of `>=3.8`, but that is
not a tested support range. No upper bound or broader compatibility matrix is
established. The 3.9.6, 3.11.14, and 3.12.10 results here are host-specific
evidence, not a project support guarantee. Do not infer a wider range from them.

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

The scoped pytest extra and hash lock are recorded above. Broad runtime package
versions remain undeclared until ENV-001C; the import scan establishes package
roles, not a reproducible trainer/live environment.

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

For ENV-001B, `trainer/pyproject.toml` is the declaration source, `pip-tools`
generates the hash-checked `trainer/requirements/simulator-record.txt` from the
`simulator-record` extra plus build requirements, and pip consumes that artifact
on macOS venv or the selected Windows Conda interpreter. The Node side continues
to use `sim-core/package-lock.json` with `npm ci`; Node runtime dependencies are
exact in `package.json`, while TypeScript and Node type development entries
resolve through the lockfile. The single Mac-generated Python artifact has not
yet been installed in a clean Windows environment.

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

## 7. Broader clean-environment validation — ENV-001C

The former mixed-scope smoke procedure is superseded for simulator-record
validation by ENV-001B above. Do not install or verify NumPy, PyTorch,
FastAPI, Pydantic, Uvicorn, PyYAML, replay tooling, or model dependencies as part
of the simulator-record profile. ENV-001C must declare and lock those broader
trainer/live dependencies and define its own compatibility and validation matrix.

## 8. Installation locations and accessibility

The following user-site paths are historical host evidence; ENV-001B used only
the temporary virtual environments recorded above.

The active Python client can import NumPy, PyTorch, FastAPI, Pydantic, Uvicorn, PyYAML, and pytest from `/Users/nbolger/Library/Python/3.9/lib/python/site-packages`.

The `pytest`, `pip`, `uvicorn`, and related console scripts are under `/Users/nbolger/Library/Python/3.9/bin`, which is not currently on `PATH`. Prefer `python3 -m pytest` and `python3 -m pip`; if direct console commands are needed, use:

```bash
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
```

Node and npm are accessible through the nvm-managed paths above. sim-core dependencies and compiled output are present at the documented absolute paths. Future agents must not report these packages or clients as missing unless the paths or import checks fail.

Remaining blockers are:

1. Recreate the simulator-record profile from the committed lock on Windows
   using the selected Conda Python. The Mac proof does not establish Windows
   compatibility or a universal Python support range.
2. Define and validate the broader trainer/live profile, including
   platform-specific PyTorch and accelerator policy, in ENV-001C.
3. Keep replay fixtures opt-in under the policy in
   [REPLAY_FIXTURES.md](REPLAY_FIXTURES.md). Their absence is not a blocker for
   simulator-only validation, but replay-specific parity and data claims require
   fixtures.

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

The historical TypeScript and Python evidence above remains tied to its recorded
host. ENV-001B adds a temporary macOS clean install, focused results, and local
coverage attestation; pending Windows recreation and broader trainer/live work
keep ENV-001 open. The
missing replay fixtures block only replay-specific checks, not simulator-only
validation. Host package versions are evidence for those runs only and are not
the source of the generated lock.

## Remediation required

ENV-001 remains open until clean Windows recreation passes using the same Python
artifact and ENV-001C resolves the broader trainer/live profile and compatibility
matrix. This Mac result makes no universal Python or Node/npm support claim. The replay-fixture policy remains
explicit: an absent fixture directory is allowed for simulator-only acceptance,
while replay-specific claims still require fixtures.
