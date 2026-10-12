# Windows smoke test — 2026-10-09

Target: current local `main`, commit `accab655c26ada18124e790b16d5770c8bd17894`.
Scope: existing-machine simulator-record execution, selected regressions, and runtime imports. Execution surface: native PowerShell/Node/Conda Python; no browser or external service. The attached conversation transcript was historical context, not authorization to execute its old implementation, publication, or merge prompts.

## Non-passing results

| Surface | Result | Evidence and next action |
|---|---|---|
| Python record regression suite | FAIL | `test_pipeline_record.py` plus `test_dataset_lineage.py`: **55 passed, 25 failed, 4,483 subtests passed** in 22.47s. Failures comprise 24 ability-template subtest failures and one source-control test failure. See reproduction below. Review synthetic fixture construction against the current ability authority contract. |
| Default Python pipe encoding | FAIL; workaround verified | Conda Python stdin/stdout default to `cp1252`. Node sends UTF-8 JSON. The v2 episode test initially fails with `input_observation: prefix identity mismatch` in an independently rehashed foreign-request fixture. A minimal Node-to-Python probe corrupts `Pokémon`/`Flabébé` under default mode and preserves them under `PYTHONUTF8=1`. The complete v2 test then passes with this setting. Set that variable before starting Node/Python. |
| Clean Windows dependency recreation | NOT TESTED | Reused installed packages. Existing pytest 9.0.3 differs from the committed simulator-record lock's pytest 8.4.2 and the declared `<9` extra. The two failing test methods also reproduce with standard-library unittest, independent of pytest. Clean locked installation in a separate environment remains necessary for reproducibility. |
| Training and model-backed live HTTP evaluation | NOT TESTED | The current project status keeps features, datasets, training, and new live-model readiness as separate unfinished milestones. Runtime imports alone do not establish model or endpoint readiness. No checkpoint was loaded. |

The Python fixture failure is a semantic validation failure, not a missing Windows runtime. `public_ability.py:139–158` requires exactly one correctly sided roster recipient for an owner ability reveal. The synthetic controls at `test_pipeline_record.py:896` and `:1301` use `_rehashed_protocol_candidate`, which populates health-derived roster rows but does not provide the needed ability-recipient authority for these cases. The validator raises:

```text
Typed lifecycle evidence mismatch: Public ability evidence mismatch:
reveal requires exactly one correctly sided recipient
```

This points to stale/incomplete fixtures; it does not justify relaxing the validator. No source or fixture repair was made during this assessment.

## Passing results

| Check | Observed result |
|---|---|
| Direct simulator build | `npm.cmd run build --prefix sim-core` exited 0. |
| Windows launcher build | `./scripts/run_windows.ps1 -Action build -SimCoreMode native` exited 0 using its existing defaults. |
| Core regression selection | 102 passed, zero failed: action codec, state extractor, environment manager, observable state, seeded transitions, forced switches, settling, and simulator coverage. |
| TS/Python integration | Two selected integration tests passed: real two-transition publication in fresh Python processes and deterministic v2 joint transition restoration/rejection. |
| Complete seeded episode | The repeatability test passed: two runs of the 55-transition fixture, joint and one-sided actor paths, terminal state, and Python record validation. |
| V2 complete episode and privacy/tamper controls | Passed with `PYTHONUTF8=1`, zero failures, 46.44s. The same test failed under default pipe encoding after 39.10s. |
| Python-to-Node client | `SimCoreClient` started the actual server, received `pong`, created/reset seeded `gen9randombattle`, closed the environment, and shut down. |
| Simulator coverage | Checker passed: pinned `pokemon-showdown@0.11.10`, 169 classified condition/effect IDs, 111 parser tokens, 86 literal emitter tokens, seven computed families. Synthetic drift checks passed. |
| Broader package imports | NumPy, PyYAML, PyTorch, FastAPI, Pydantic, Uvicorn, and pytest imported. CUDA availability was true; no GPU workload ran. |

## Host evidence

- Windows build 10.0.26200, PowerShell 7.1.4.
- Node v24.15.0, npm 11.12.1, native installation under `C:/Program Files/nodejs`.
- Python 3.11.14 at `D:/Anaconda/envs/neuralgpu/python.exe`.
- NumPy 2.3.5, PyYAML 6.0.3, PyTorch 2.5.1+cu121, FastAPI 0.136.1, Pydantic 2.13.3, Uvicorn 0.46.0, pytest 9.0.3.
- These are observed local versions, not a supported platform matrix or a recreated lock profile.

## Reproduction

Run from the repository root, using the existing local interpreter:

```powershell
$env:PYTHON = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src).Path
$env:PYTHONUTF8 = '1'
npm.cmd run build --prefix sim-core
node --test --test-isolation=none --test-reporter=spec --test-name-pattern='PIPELINE-001 links two real transitions|v2 joint transitions restore deterministic' sim-core/dist/tests/pipeline_integration.test.js
node --test --test-isolation=none --test-reporter=spec --test-name-pattern='^real episode completes repeatably|^v2 evidence retains both owners' sim-core/dist/tests/pipeline_episode.test.js
& $env:PYTHON -m pytest trainer/tests/test_pipeline_record.py trainer/tests/test_dataset_lineage.py -q --tb=short
```

The failed Python fixtures can be isolated without rerunning the entire suite:

```powershell
& $env:PYTHON -m pytest trainer/tests/test_pipeline_record.py -q -k 'ce04_callback_a_ability_templates or rehashed_singleturn_and_singlemove' --tb=short
```

To reproduce the default encoding issue, unset `PYTHONUTF8` in the command process and run only `^v2 evidence retains both owners`; use `PYTHONUTF8=1` for the mitigation run. Variables above affect the current shell and child processes only. No system-wide settings changed.

The historical `validate_windows_simulator_record.ps1` is tied to an old commit and review patch and runs installation steps. It was inspected but not executed against this merged checkout; the environment document explicitly recommends direct current-checkout commands instead.

## Data, cleanup, and limits

All battle execution used in-memory synthetic/seeded test data. No dataset, model training, replay acquisition, checkpoint loading, package installation, network operation, commit, push, or aggregate-status update occurred. Client-owned processes were closed; test-owned environments were disposed by their existing runners. Builds changed ignored compiled output and tests created ordinary ignored caches. The Git worktree was clean before this report was added.

Results and selected test timings are retained here; full run logs and screenshots were not retained. Whole-run start/end timing was not captured. This smoke assessment does not cover the full regression suite, the 1,000-turn fixture, arbitrary formats, clean installation, or model inference.

## Final verdict

**READY WITH LIMITATIONS for existing-machine simulator-record execution.** Native startup, real transitions, and selected complete-episode/privacy flows pass when `PYTHONUTF8=1` is supplied. **Regression validation is not fully passing:** two Python test methods produce 25 failing results. Windows clean recreation and model-backed training/live readiness remain unverified. Next: repair the synthetic ability-authority fixtures against the current contract, rerun their focused tests, and separately validate a clean locked Windows environment.
