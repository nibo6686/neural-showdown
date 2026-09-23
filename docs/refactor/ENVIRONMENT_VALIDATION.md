# ENV-001 Environment Validation

Status: `BLOCKED_WITH_REMEDIATION`

`READY_FOR_CONTRACT_IMPLEMENTATION: NO`

This document records reproducible Python/Node validation requirements. The
dependency remediation record is separate from `STATE-001`: it records
environment evidence and packaging blockers without changing the observable-
state contract. The original audit did not install packages or run commands;
subsequent user-reported validation results are recorded below.

## 1. Supported versions

### Python

- Declared minimum: Python `>=3.8` in `trainer/pyproject.toml`.
- Declared maximum: none.
- Repository-tested version: none established.
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
- Current host: Node `v24.21.0`, npm `11.19.0`; compatibility is not yet validated.
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

The repository does not provide enough evidence to choose exact Python versions,
so none are recorded here.

## 4. sim-core build and test commands

After environment approval, from the repository root:

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
5. Keep raw replay fixtures opt-in under the policy in
   [REPLAY_FIXTURES.md](REPLAY_FIXTURES.md); the directory is currently absent or
   empty.

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
environment is operational, but ENV-001 remains blocked by the missing replay
fixture/data prerequisite and the absence of a committed Python dependency
policy. The current host package versions are evidence for this run only and are
not a lock.

## Remediation required

ENV-001 becomes ready only after the dependency policy is approved, Python
dependencies are declared and locked/constrained, a supported Python/Node/npm
matrix is recorded, sim-core builds in a clean environment, the optional
replay-fixture policy is either satisfied or explicitly accepted as an absent
fixture condition, and both Python and TypeScript focused commands complete
successfully.
