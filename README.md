# Neural Showdown

Headless Gen 9 Random Battles training harness built around a local Pokemon Showdown simulator.

## Layout

- `sim-core/`: Node/TypeScript simulator RPC server and local baseline agents
- `trainer/`: Python client, featurization, dataset, training, and evaluation code
- `configs/`: experiment configs stored as JSON-compatible YAML
- `docs/`: architecture and interface docs
- `data/`: generated raw episodes and training shards
- `artifacts/`: checkpoints and evaluation reports

## Runtime options

This project does not fundamentally require WSL. The Windows launcher now prefers native Windows `node`/`npm` for `sim-core` and only falls back to WSL when native Node is not available.

Two supported workflows today:

- full WSL workflow: run both `sim-core` and Python inside WSL
- Windows Python workflow: run Python in the Windows conda env and let the launcher start `sim-core` natively when possible

If you want the full WSL workflow, run:

```bash
cd /mnt/c/Users/cloud/Downloads/neural/final
cd sim-core && npm install && npm run build
cd ../trainer && python3 -m unittest discover -s tests
```

Key commands:

```bash
cd sim-core && npm run test
cd sim-core && npm run start
cd trainer && PYTHONPATH=src python3 -m neural.eval --config ../configs/gen9randombattle_eval.yaml
cd trainer && PYTHONPATH=src python3 -m neural.build_dataset --config ../configs/gen9randombattle_bc.yaml
cd trainer && PYTHONPATH=src python3 -m neural.train_bc --config ../configs/gen9randombattle_bc.yaml
```

## Notes

- v1 is CPU-first. The Python code will use CUDA if available, but does not require it.
- Team preview is auto-resolved with `default`.
- The fixed policy head is length `13`:
  - `0-3`: moves 1-4
  - `4-7`: moves 1-4 with terastallization
  - `8-12`: bench switches 1-5

## Windows workflow

If you want to use the Windows conda environment at `D:\Anaconda\envs\neuralgpu`, run from PowerShell. The launcher picks `sim-core` mode automatically:

- `native`: use Windows `node`/`npm`
- `wsl`: fallback when Windows Node is not available
- `auto`: default, prefer native and fall back to WSL

### Full end-to-end run with native Windows sim-core

```powershell
.\scripts\run_windows.ps1 -Action all -Profile full -SimCoreMode native
```

This will:
1. Build sim-core if needed (native Windows `node`/`npm`)
2. Collect 128 battles of dataset using native Windows sim-core
3. Train behavior cloning model on collected data
4. Evaluate trained model against 100 baseline battles
5. Print final summary with `sim_core=native` confirmation and artifact paths

Use the launcher:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_windows.ps1 -Action all
```

Available actions:

```powershell
.\scripts\run_windows.ps1 -Action setup
.\scripts\run_windows.ps1 -Action build
.\scripts\run_windows.ps1 -Action test
.\scripts\run_windows.ps1 -Action dataset
.\scripts\run_windows.ps1 -Action train
.\scripts\run_windows.ps1 -Action ppo
.\scripts\run_windows.ps1 -Action eval
.\scripts\run_windows.ps1 -Action improve
.\scripts\run_windows.ps1 -Action server
.\scripts\run_windows.ps1 -Action all
```

Mode overrides:

```powershell
.\scripts\run_windows.ps1 -Action all -SimCoreMode auto
.\scripts\run_windows.ps1 -Action all -SimCoreMode native
.\scripts\run_windows.ps1 -Action all -SimCoreMode wsl
```

Profiles:

```powershell
.\scripts\run_windows.ps1 -Action all -Profile dev
.\scripts\run_windows.ps1 -Action all -Profile full
```

### Larger evaluation runs

To evaluate with more battles (500 or 1000 instead of 100) for more robust metrics:

**Quick runs (8 parallel environments, fast but may see timeout bursts):**

```powershell
# 500 battles - throughput optimized
.\scripts\run_windows.ps1 -Action eval -EvalConfig .\configs\gen9randombattle_eval.windows.eval500.yaml -SimCoreMode native

# 1000 battles - throughput optimized
.\scripts\run_windows.ps1 -Action eval -EvalConfig .\configs\gen9randombattle_eval.windows.eval1000.yaml -SimCoreMode native
```

**Stable runs (4 parallel environments, slower but no timeout cascades):**

```powershell
# 500 battles - stability optimized (~20 min)
.\scripts\run_windows.ps1 -Action eval -EvalConfig .\configs\gen9randombattle_eval.windows.eval500-stable.yaml -SimCoreMode native

# 1000 battles - stability optimized (~40 min)
.\scripts\run_windows.ps1 -Action eval -EvalConfig .\configs\gen9randombattle_eval.windows.eval1000-stable.yaml -SimCoreMode native
```

**Stability vs. throughput tradeoff:**
- `-stable` configs use 4 parallel environments instead of 8 and timeout=30/60s instead of 20/45s
- This prevents sim-core event loop congestion that can cause cascading timeouts
- Recommended for production validation runs where reliability matters more than speed
- Use the non-stable (8-env) variants for development iteration

### Continuous improvement

The `improve` action runs a bounded curriculum loop that can be left unattended:

```powershell
.\scripts\run_windows.ps1 -Action improve -Profile full -SimCoreMode native
```

Each cycle collects fresh heuristic-labeled data, appends it into a cumulative shard, resumes behavior-cloning training from the latest checkpoint, optionally runs PPO fine-tuning, evaluates against configured baselines, and promotes the checkpoint to `*.best.pt` only when eval win rate improves.

Fast smoke configs are available for checking the plumbing without a long run:

```powershell
.\scripts\run_windows.ps1 -Action dataset -DatasetConfig .\configs\gen9randombattle_bc.smoke.windows.yaml -SimCoreMode native
.\scripts\run_windows.ps1 -Action train -DatasetConfig .\configs\gen9randombattle_bc.smoke.windows.yaml -SimCoreMode native
.\scripts\run_windows.ps1 -Action ppo -DatasetConfig .\configs\gen9randombattle_bc.smoke.windows.yaml -SimCoreMode native
.\scripts\run_windows.ps1 -Action eval -EvalConfig .\configs\gen9randombattle_eval.smoke.windows.yaml -SimCoreMode native
.\scripts\run_windows.ps1 -Action improve -DatasetConfig .\configs\gen9randombattle_bc.smoke.windows.yaml -SimCoreMode native
```

Behavior cloning now supports resumeable checkpoints when `training.resume=true`. Checkpoints include model weights, optimizer state, total epoch, global step, training history, and best score metadata. Pure behavior cloning from the heuristic is still imitation: it can smooth or generalize from the heuristic, but reliably surpassing the heuristic requires outcome-based fine-tuning, stronger labels, search, or external data.

### Reviewing run results

After a full run (`-Action all`), results and metadata are written to:

- **Dataset report**: `artifacts/latency/gen9randombattle_bc_dataset_latency.windows.json` (with battles/labels/retries/timeouts)
- **Training report**: `artifacts/checkpoints/gen9randombattle_bc.train.json` (with training history by epoch)
- **Eval report**: `artifacts/eval/gen9randombattle_eval.json` (with wins/losses/ties/latency)
- **Latency details**: `artifacts/latency/gen9randombattle_eval_latency.windows.json`
- **Improvement state**: `artifacts/improve/state.json` or the configured improvement state path

All reports include:
- `timestamp`: when the run occurred
- `profile`: which config profile was used
- `sim_core_mode`: `native` or `wsl` (proves which runtime was used)
- `python_executable`: path to Python interpreter
- `torch_device`: `cuda` or `cpu`
- `git_commit`: git commit hash if available
- platform and environment info

### Archiving results on Windows

To archive all artifacts after a run, use PowerShell's `Compress-Archive`:

```powershell
Compress-Archive -Path .\artifacts\* -DestinationPath .\artifacts.zip -Force
```

This is the recommended approach on Windows (do not use Unix `zip` command).

Defaults:

- `-Profile dev` is the default.
- `-SimCoreMode auto` is the default.
- `setup` is the only action that runs `npm install`.
- `build` only runs `npm run build`.
- `all` uses `Ensure-SimCoreBuilt` and does not reinstall dependencies on each run.
- dataset and eval use launcher-provided `sim_core` overrides, so the same config can run either natively or through WSL

If you want to keep running the modules manually, the commands below assume native Windows `node`/`npm` are available. If they are not, use the launcher in `auto` mode or force `-SimCoreMode wsl`.

One-time setup:

```powershell
cd .\sim-core
npm install
npm run build
cd ..
```

Node tests:

```powershell
cd .\sim-core
npm test
cd ..
```

Python tests:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
& $py -m unittest discover -s .\trainer\tests
```

Dataset build:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
& $py -m neural.build_dataset --config .\configs\gen9randombattle_bc.dev.windows.yaml
```

Behavior cloning train:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
& $py -m neural.train_bc --config .\configs\gen9randombattle_bc.dev.windows.yaml
```

Evaluation:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
& $py -m neural.eval --config .\configs\gen9randombattle_eval.dev.windows.yaml
```

Latency reports are written to `artifacts/latency/`. Each report includes:

- overall model inference latency
- batch model inference latency
- RPC round-trip latency
- server queue wait inside the Node process
- server execution time inside the simulator
- transport overhead across the Python <-> `sim-core` boundary
- slowest battles and per-battle timing breakdowns
- timeout diagnostics, retry counts, and heartbeat counts

Runtime behavior:

- dataset and eval log one start line, periodic completion lines, timeout/retry lines, and one done line
- all output to stdout is single-line (no pretty-printed JSON) to prevent PowerShell continuation prompt corruption
- final summaries print in compact format: `phase done | metric1=value1 metric2=value2 ...`
- full JSON data is written to artifact files only
- a heartbeat is printed if no battle completes for `15s`
- when a simulator timeout occurs, eval prints one `eval timeout detail` line and writes compact per-timeout diagnostics to the eval and latency reports
- dataset and eval use compact `p1`-only simulator responses for faster JSON transport
- `improve` writes one cycle report per cycle under `artifacts/improve/.../reports/`
- dev profile uses smaller runs and multi-env collection/evaluation by default
- the Windows launcher prefers native `sim-core` and falls back to WSL only when needed

Timeout diagnostics include the timed-out RPC id/type, active battle numbers, env ids, step/retry counts, recent successful RPC timings, recent `sim-core` trace lines, and compact battle state summaries. The `sim-core` trace is captured on stderr by the Python client and only surfaced in timeout diagnostics, so normal stdout stays compact.

## Performance tuning and known issues

### Timeout cascades with high parallelism

When running large evals (500+) with 8 parallel environments, sim-core may experience event loop congestion around 40-50 battles, causing simultaneous timeouts across the entire batch. This is due to:
- Accumulation of state in Node.js process memory
- Event loop backpressure when handling 8 concurrent battle streams
- RPC batch queue saturation

**Root cause identified and fixed:**
- Memory leak in latency event accumulation in Python client (now drained after each close_slots)
- Events were not being cleared when environments closed, causing unbounded growth in `_latency_events` list
- This caused Python process memory bloat which eventually slowed down RPC handling

**Fix applied:**
- `close_slots()` now drains latency events immediately after closing environments
- `eval.py` and `build_dataset.py` drain remaining events before exiting
- This prevents memory accumulation from growing unbounded

**Mitigation strategies:**
1. **Use `-stable` eval configs** (4 envs, timeout=30/60s) for production runs - memory-safe and proven stable up to 1000 battles
2. **Reduce `num_envs`** in config from 8 to 4 or 2 for better stability at the cost of throughput
3. **Increase timeouts** in config `runtime.timeouts_sec`: raise `step` from 20s to 25-30s, `batch` from 45s to 60s
4. **Diagnostic tool** available: run `python diagnose_memory.py` to test memory accumulation (requires 100 cycles, ~5-10 min)

### Recommended tuning parameters

For your hardware configuration, tuning parameters in JSON/YAML configs:

```json
"runtime": {
  "num_envs": 4,                    // Reduce from 8 if timeouts occur
  "heartbeat_interval_sec": 15,     // Print progress every 15s of inactivity
  "retry_attempts_per_battle": 2,   // Retry individual battles up to 2 times
  "timeouts_sec": {
    "step": 25,                     // Increase from 20 for large evals
    "batch": 60,                    // Increase from 45 for large evals
    "reset": 45,
    "create_env": 15,
    "close_env": 5
  }
}
```

### Future improvements

To address timeout cascades at the source, consider:
1. **Sim-core memory management**: Implement periodic garbage collection or environment pool refresh
2. **Adaptive batching**: Reduce batch size if timeouts detected, increase if time permits
3. **Request queue management**: Add backpressure handling in env_client.py
4. **Process lifecycle**: Restart sim-core process every N battles to reset accumulated state
5. **Profiling**: Enable Node.js heap snapshots to identify memory leaks in sim-core
