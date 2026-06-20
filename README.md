# Neural Showdown

Neural Showdown is a local Gen 9 Random Battles research harness. It pairs a
TypeScript Pokemon Showdown simulator service with Python tooling for data
collection, replay ingestion, featurization, model training, evaluation, action
ranking, and live battle evaluation.

The current repository is centered on four related loops:

- Local simulator experiments: collect self-play or baseline-vs-baseline games,
  train policy/value models, and evaluate checkpoints.
- Public replay learning: fetch saved Pokemon Showdown replays, parse protocol
  logs, build public and live-private datasets, and train replay-derived models.
- Live evaluation: serve a local `/evaluate` endpoint that scores the current
  battle state and ranks legal actions using live request data, opponent beliefs,
  damage diagnostics, rollout estimates, and action rankers.
- vNext diagnostic program: a newer, frozen-schema research track
  (`live-private-belief-v7` state + `legal-action-v5` action) that materializes
  battle-level diagnostic datasets, trains isolated value / action-rank heads,
  validates representation quality offline, and prepares the action-rank model
  for eventual private-match testing. See
  [vNext Diagnostic Program](#vnext-diagnostic-program-v7v5).

This is a research codebase, not a packaged application. Most commands assume
you run them from the repository root.

### Current focus and status

The active priority is **representation correctness and dataset quality** for the
vNext program, then training models for private-match testing once the diagnostic
pipeline is trusted — not maximizing training volume. As of the latest update:

- The action-rank track is the promising one: the `diagnostic_1000` rank-only
  model beats simple offline baselines (validation top-1/top-3 0.463/0.858).
- The state-value head is weak on the diagnostic data and is paused.
- The live `/evaluate` defaults remain intentionally **old and stable**
  (`live-private-belief-v2` / `legal-action-v3`). The vNext v7/v5 work is
  **diagnostic-only**: no vNext checkpoint is promoted, and the live bot path is
  unchanged. Promotion is tracked by a closed gate
  (`artifacts/training_plan/diagnostic_training_gate.md`).
- No private or public matches have been run with vNext models.

## Repository Layout

- `sim-core/`: TypeScript RPC server around Pokemon Showdown, baseline agents,
  legal action encoding, state extraction, and Smogon damage calculation.
- `trainer/src/neural/`: Python package for configs, simulator clients,
  datasets, featurizers, models, training, evaluation, replay tools, live eval,
  and analysis.
- `trainer/tests/`: Python regression and smoke tests.
- `configs/`: JSON-compatible YAML configs for dataset collection, training,
  evaluation, smoke runs, trace runs, and larger evals.
- `data/`: generated datasets, replay caches, randbats set data, and self-play
  outputs.
- `artifacts/`: checkpoints, reports, latency traces, analysis outputs, battle
  traces, and live-eval logs.
- `artifacts/training_plan/`: the vNext diagnostic program's plans, manifests,
  datasets, audits, training/eval reports, and the promotion gate
  (`diagnostic_training_gate.md`).
- `docs/`: concise interface notes for architecture, action space, and state
  schema.
- `scripts/run_windows.ps1`: Windows launcher that sets `PYTHONPATH`, resolves
  native Node/WSL sim-core mode, injects sim-core process environment variables,
  and runs the common workflows.

## Prerequisites

Runtime pieces:

- Node.js and npm for `sim-core`.
- Python 3.8+ with PyTorch, NumPy, FastAPI/Uvicorn, pytest, and the other
  scientific/runtime packages used by the trainer.
- On this Windows setup, the launcher defaults to:

```powershell
D:\Anaconda\envs\neuralgpu\python.exe
```

The code can run on CPU. PyTorch will use CUDA when available.

Install and build the simulator:

```powershell
cd C:\Users\cloud\Downloads\neural\final
cd .\sim-core
npm install
npm run build
cd ..
```

Set Python imports for manual module runs:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
```

For workflows that call sim-core from Python, also provide the simulator command:

```powershell
$env:NEURAL_SIM_CORE_CWD = (Resolve-Path .\sim-core)
$serverJs = (Resolve-Path .\sim-core\dist\src\server.js).Path
$env:NEURAL_SIM_CORE_COMMAND_JSON = ConvertTo-Json @('node', $serverJs) -Compress
```

The Windows launcher does this environment setup for you.

## Quickstart

Run tests:

```powershell
.\scripts\run_windows.ps1 -Action test -SimCoreMode native
```

Run a dev end-to-end simulator loop:

```powershell
.\scripts\run_windows.ps1 -Action all -Profile dev -SimCoreMode native
```

That builds sim-core if needed, collects a dev behavior-cloning dataset, trains
the BC model, and evaluates it.

Run individual steps:

```powershell
.\scripts\run_windows.ps1 -Action dataset -Profile dev -SimCoreMode native
.\scripts\run_windows.ps1 -Action train   -Profile dev -SimCoreMode native
.\scripts\run_windows.ps1 -Action eval    -Profile dev -SimCoreMode native
```

Start the live eval server:

```powershell
.\scripts\run_windows.ps1 -Action live-eval -SimCoreMode native
```

Or start it manually:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
$env:NEURAL_SIM_CORE_CWD = (Resolve-Path .\sim-core)
$serverJs = (Resolve-Path .\sim-core\dist\src\server.js).Path
$env:NEURAL_SIM_CORE_COMMAND_JSON = ConvertTo-Json @('node', $serverJs) -Compress
& $py -m neural.live_eval_server
```

By default the HTTP server binds to `127.0.0.1:8765`.

### Browser overlay (recommendation-only)

`Showdown Local Eval Overlay.user.js` is a userscript that sends the live
Showdown request/log to the local server and **displays** recommendations — it
never auto-clicks or submits a choice; the user always decides manually. The
overlay is a compact, draggable pill that expands to a panel (collapse/position
persist in `localStorage`) and auto-collapses near Showdown login/modal popups.
A `vNext shadow` checkbox (default off) optionally calls `/evaluate-vnext-dry-run`
and shows the vNext recommendation side-by-side for comparison; it degrades to a
small badge when that route is disabled.

## Launcher Actions

The main launcher is `scripts/run_windows.ps1`. It supports native Windows
Node/npm, WSL, or automatic selection:

```powershell
.\scripts\run_windows.ps1 -Action test -SimCoreMode auto
.\scripts\run_windows.ps1 -Action test -SimCoreMode native
.\scripts\run_windows.ps1 -Action test -SimCoreMode wsl
```

Common actions:

```powershell
setup
build
test
dataset
train
ppo
eval
improve
trace-eval
collect-selfplay
compare-checkpoints
fetch-replays
parse-replays
build-replay-value-dataset
build-replay-policy-dataset
train-replay-value
build-live-private-value-dataset
train-live-private-value
build-action-rank-dataset
train-action-ranker
build-action-value-dataset
train-action-value-ranker
compare-action-rankers
analyze
analyze-state
analyze-rollout-actions
analyze-action-bias
analyze-tactical-failures
test-live-eval
live-eval
test-sim-rollout
server
all
benchmark-vnext-featuregen
materialize-diagnostic-300
materialize-diagnostic-1000-action-rank
```

The last three actions belong to the vNext diagnostic program; see
[vNext Diagnostic Program](#vnext-diagnostic-program-v7v5). The rest of the vNext
tooling (training, evaluation, audits, harness) runs as direct
`python -m neural.<module>` commands rather than launcher actions.

Profiles:

- `dev`: smaller/default runs for iteration.
- `full`: larger configured runs.

Default dev configs:

- Dataset/training: `configs/gen9randombattle_bc.dev.windows.yaml`
- Evaluation: `configs/gen9randombattle_eval.dev.windows.yaml`

Smoke configs are useful when checking plumbing:

```powershell
.\scripts\run_windows.ps1 -Action dataset -DatasetConfig .\configs\gen9randombattle_bc.smoke.windows.yaml -SimCoreMode native
.\scripts\run_windows.ps1 -Action eval -EvalConfig .\configs\gen9randombattle_eval.smoke.windows.yaml -SimCoreMode native
```

Large eval configs:

```powershell
.\scripts\run_windows.ps1 -Action eval -EvalConfig .\configs\gen9randombattle_eval.windows.eval500.yaml -SimCoreMode native
.\scripts\run_windows.ps1 -Action eval -EvalConfig .\configs\gen9randombattle_eval.windows.eval500-stable.yaml -SimCoreMode native
.\scripts\run_windows.ps1 -Action eval -EvalConfig .\configs\gen9randombattle_eval.windows.eval1000.yaml -SimCoreMode native
.\scripts\run_windows.ps1 -Action eval -EvalConfig .\configs\gen9randombattle_eval.windows.eval1000-stable.yaml -SimCoreMode native
```

The stable variants use fewer parallel environments and longer timeouts.

## Architecture

The system has two runtimes:

- Python is the parent process. It owns training, evaluation, replay parsing,
  model loading, live eval, and analysis.
- Node/TypeScript owns the local Pokemon Showdown simulation and damage RPC.

Python talks to sim-core over newline-delimited JSON on stdio using
`neural.env_client.SimCoreClient`. sim-core supports:

- `create_env`
- `reset`
- `step`
- `close_env`
- `agent_action` for `random` and `heuristic`
- `damage_estimate`
- `batch`
- `ping`

The simulator exposes player-legal views. Opponent hidden information is not
included in `views.p1` or `views.p2`; live-private features only use the user's
own request payload plus public battle log and randbats beliefs.

## Action Space

The fixed policy head has 13 indices:

- `0-3`: moves 1-4
- `4-7`: moves 1-4 with terastallization
- `8-12`: up to five bench switches

The concrete Showdown command changes with the current request. sim-core stores
the command in `legal_actions.actions[index].choice` and legality in
`legal_actions.mask[index]`. Illegal actions must be masked before sampling or
argmax.

Live action rankers are action-conditioned models. They score each legal action
from a concatenation of live state features and action features, rather than
only choosing from the fixed policy head.

Current **live-default** action feature schema:

- Feature version: `legal-action-v3`
- Feature dimension: `165`

The vNext diagnostic program uses a richer frozen action schema
(`legal-action-v5`, 318D) that adds explicit move side-effects/stat-deltas (e.g.
Draco Meteor's self −2 SpA) and resolved-impact features, and represents Tera
moves as a distinct `move_tera` candidate kind. It is diagnostic-only and is not
used by the live default path. See
[vNext Diagnostic Program](#vnext-diagnostic-program-v7v5).

## Model and Feature Families

Several model families coexist. They are intentionally separate because they use
different feature domains.

### Behavior Cloning Policy

Default checkpoint examples:

- `artifacts/checkpoints/gen9randombattle_bc.dev.pt`
- `artifacts/checkpoints/gen9randombattle_bc.pt`

Purpose:

- Train from local simulator decisions, usually heuristic-vs-random or related
  generated datasets.
- Produce a fixed 13-action policy/value MLP.

Primary modules:

- `neural.build_dataset`
- `neural.train_bc`
- `neural.eval`
- `neural.train_ppo`

### Local Trace Value Model

Default checkpoint:

- `artifacts/checkpoints/gen9randombattle_value.pt`

Purpose:

- Train value predictions from local traced simulator positions.

Primary modules:

- `neural.build_value_dataset`
- `neural.train_value`
- `neural.analyze_state`

### Public Replay Value and Policy Models

Default checkpoints:

- `artifacts/checkpoints/gen9randombattle_replay_value.pt`
- `artifacts/checkpoints/gen9randombattle_replay_policy.pt`

Feature domain:

- `public-replay-events-v1`
- 31D public event features from protocol logs.

Purpose:

- Learn from saved public Pokemon Showdown replays.
- Provide a replay-policy prior for live action recommendations.
- Provide an old public-value fallback path.

Primary modules:

- `neural.replay_fetch`
- `neural.parse_replay_logs`
- `neural.build_replay_value_dataset`
- `neural.build_replay_policy_dataset`
- `neural.train_replay_value`

### Live Private-Belief Value Model

Current default checkpoint:

- `artifacts/checkpoints/gen9randombattle_live_private_value_v2.pt`

Current feature domain:

- Feature version: `live-private-belief-v2`
- Feature dimension: `115`

Inputs combine:

- 31D public replay-event features.
- Own private request/team/move/PP/item/ability/tera/legal-action features.
- Opponent belief features inferred from public reveals and randbats sets.
- Tactical state features from public protocol and the private snapshot.

Purpose:

- Score live battle positions from the perspective of the current player.
- Power `/evaluate` win probability and help action recommendation.

Primary modules:

- `neural.build_live_private_value_dataset`
- `neural.train_live_private_value`
- `neural.live_eval_server`

Build and train:

```powershell
.\scripts\run_windows.ps1 -Action build-live-private-value-dataset -SimCoreMode native
.\scripts\run_windows.ps1 -Action train-live-private-value -SimCoreMode native
```

### Action Rankers

Current action-rank dataset:

- `data/policy/gen9randombattle_action_rank_v2.npz`

Current action-ranker checkpoint:

- `artifacts/checkpoints/gen9randombattle_action_ranker_v2.pt`

Current action-value dataset:

- `data/policy/gen9randombattle_action_value_rank_v2.npz`

Current action-value ranker checkpoint:

- `artifacts/checkpoints/gen9randombattle_action_value_ranker_v2.pt`

Current action-value ranker metadata:

- `model_type=action-value-ranker`
- `state_dim=115`
- `action_dim=165`
- `input_size=280`
- `response_method=action_value_ranker`

Purpose:

- Score legal actions with a scalar, action-conditioned model.
- Prefer the value-delta ranker when available.
- Fall back to action ranker, policy prior, switch proxy, or rollout diagnostics
  depending on available checkpoints and request context.

Build and train:

```powershell
.\scripts\run_windows.ps1 -Action build-action-rank-dataset -SimCoreMode native
.\scripts\run_windows.ps1 -Action train-action-ranker -SimCoreMode native
.\scripts\run_windows.ps1 -Action build-action-value-dataset -SimCoreMode native
.\scripts\run_windows.ps1 -Action train-action-value-ranker -SimCoreMode native
```

Compare rankers:

```powershell
.\scripts\run_windows.ps1 -Action compare-action-rankers -ReplayId gen9randombattle-2594788118 -Side p1 -SimCoreMode native
```

## vNext Diagnostic Program (v7/v5)

The vNext program is a separate, frozen-schema research track aimed at making the
model receive the *right* battle information in a learnable representation, then
training models for private-match testing once the diagnostic pipeline is trusted.
It is intentionally isolated from the live default path: it writes to
`artifacts/training_plan/` and `artifacts/diagnostic_training/`, never promotes a
checkpoint, and never changes the live `/evaluate` defaults.

### Frozen schemas

- State: `live-private-belief-v7`, **3208D** (richer privacy-aware belief state).
- Action: `legal-action-v5`, **318D** (adds move side-effects/stat-deltas and
  resolved-impact features; Tera moves are a distinct `move_tera` candidate kind).

Both schemas are pinned by ordered feature-name SHA-256 fingerprints. Datasets,
configs, and checkpoints record these fingerprints, and loaders refuse mismatches
(no pad/truncate).

### Pipeline stages and modules

1. **Replay pool profiling and manifest selection** —
   `neural.replay_pool_profiler`, `neural.replay_sample_manifest`. Battle-level
   deterministic stratified selection from the existing replay pool (~14k eligible
   battles), with split isolation and enrichment for sparse decision types (Tera,
   switches). Manifests live in `artifacts/training_plan/manifests/`.
2. **Feature materialization** — `neural.benchmark_vnext_featuregen`. Builds the
   v7 state and v5 candidate features per decision via sim-core, with battle-level
   train/validation/test isolation, action-rank labels (one replay-chosen positive
   per group), no action-value labels, and float16 separate state/candidate tables.
   The full-manifest path is **parallel, crash-safe, and resumable** (per-battle
   shards under `_shards/`). Launcher actions:

   ```powershell
   .\scripts\run_windows.ps1 -Action materialize-diagnostic-300 -SimCoreMode native
   .\scripts\run_windows.ps1 -Action materialize-diagnostic-1000-action-rank -SimCoreMode native
   ```

3. **Diagnostic training** — `neural.train_vnext_diagnostic` with
   `neural.models.vnext_diagnostic.VNextDiagnosticMLP` (separate state/action
   encoders + value head + grouped-rank head). Supports multitask, **value-only**,
   and **action-rank-only** objectives via config; `--validate-only` checks
   schema/fingerprints/splits and confirms which objective(s) will receive
   gradients. Checkpoints embed schema versions, dims, and fingerprints.

   ```powershell
   $env:PYTHONPATH = (Resolve-Path .\trainer\src)
   $py = 'D:\Anaconda\envs\neuralgpu\python.exe'
   & $py -m neural.train_vnext_diagnostic --config .\configs\diagnostic_1000_action_rank_v7_v5.rank_only.windows.json --validate-only
   & $py -m neural.train_vnext_diagnostic --config .\configs\diagnostic_1000_action_rank_v7_v5.rank_only.windows.json
   ```

4. **Offline evaluation** — `neural.evaluate_vnext_action_rank`. Scores a trained
   checkpoint against baselines (random, max expected damage, max KO, type prior,
   no-switch heuristic) with breakdowns by action type, candidate count, and turn.

   ```powershell
   & $py -m neural.evaluate_vnext_action_rank --config .\configs\diagnostic_1000_action_rank_v7_v5.rank_only.windows.json --checkpoint .\artifacts\diagnostic_training\diagnostic_1000_action_rank_v7_v5_rank_only\model.best.pt --split validation
   ```

5. **Live-readiness audit** — `neural.audit_vnext_live_inference_readiness`.
   Read-only: strict schema/fingerprint load, controlled scoring vs the offline
   evaluator (exact parity), command-serialization checks, latency, and a scan of
   the live code for v2/v3 assumptions.
6. **Opt-in inference harness** — `neural.vnext_inference`. Default-off, isolated,
   fail-closed scorer: strict checkpoint load, candidate scoring with masking,
   Showdown command serialization (`move`, `move <slot> terastallize`, `switch`),
   and safe `"default"` fallback on any inconsistency. Gated by
   `NEURAL_VNEXT_INFERENCE`; **not imported by the default live path**. It consumes
   precomputed v7/v5 features — live feature generation is not yet wired.

### Current datasets and checkpoints

- `artifacts/training_plan/datasets/diagnostic_300_v7_v5/` — 300 battles
  (210/45/45), 25,396 states, 189,957 candidates.
- `artifacts/training_plan/datasets/diagnostic_1000_action_rank_v7_v5/` — 1000
  battles (700/150/150), 80,899 states, 606,770 candidates, 79,525 action-rank
  positives.
- `artifacts/diagnostic_training/diagnostic_1000_action_rank_v7_v5_rank_only/model.best.pt`
  — current best vNext action-rank checkpoint (epoch 8; validation top-1/top-3
  0.4626/0.8576, test top-1 0.4608). **Not promoted; not live.**

### Reports and the gate

Every stage writes a Markdown report under `artifacts/training_plan/` (dataset
plans, manifest reports, materialization reports, training reports, the offline
eval, the legacy pipeline audit, the schema guardrails note, the live-inference
readiness audit, and the inference harness report). The promotion gate is
`artifacts/training_plan/diagnostic_training_gate.md`; it remains **closed** for
training/live/production promotion.

### Known gaps before private-match testing

- Live feature generation does not yet build v7 state or v5 candidates (including
  `move_tera`); the live path still uses the legacy `ActionRankerMLP` with v2/v3
  features. The opt-in harness scores precomputed features only.
- The action-rank model under-ranks Tera moves and is moderate on switches.
- End-to-end live decision latency (feature gen + scoring) is unmeasured; model
  scoring alone is under ~1 ms per decision group.

## Live Evaluation Server

The live server is `neural.live_eval_server`. It exposes:

- `POST /evaluate`

The request contains:

- `room_id`
- `url`
- `player`
- protocol `log`
- latest Showdown `request`
- optional `legal_actions`

The response includes:

- `p1_win_prob`
- `p2_win_prob`
- raw scalar `value`
- ranked `top_actions`
- selected model/checkpoint metadata
- feature version/dimension
- whether private state and opponent beliefs were used
- action recommendation method
- damage/rollout diagnostics under `debug`

Smoke-test the live evaluator without HTTP:

```powershell
.\scripts\run_windows.ps1 -Action test-live-eval -SimCoreMode native
```

Model selection defaults:

- Value model: `artifacts/checkpoints/gen9randombattle_live_private_value_v2.pt`
- Replay policy prior: `artifacts/checkpoints/gen9randombattle_replay_policy.pt`
- Action ranker: `artifacts/checkpoints/gen9randombattle_action_value_ranker_v2.pt` when present, otherwise the available action-ranker fallback.

Useful overrides:

```powershell
$env:NEURAL_LIVE_MODEL = 'live-private'      # default
$env:NEURAL_LIVE_MODEL = 'public-replay'     # force old 31D public replay value
$env:NEURAL_LIVE_VALUE_CHECKPOINT = '.\artifacts\checkpoints\gen9randombattle_live_private_value_v2.pt'
$env:NEURAL_ACTION_RANKER_CHECKPOINT = '.\artifacts\checkpoints\gen9randombattle_action_value_ranker_v2.pt'
$env:NEURAL_LIVE_EVAL_PORT = '8765'
```

Action recommendation weights:

```powershell
$env:NEURAL_ROLLOUTS_PER_ACTION = '8'
$env:NEURAL_ROLLOUT_MODE = 'auto'       # auto, exact, approximate
$env:NEURAL_OPPONENT_POLICY = 'uniform'
$env:NEURAL_ROLLOUT_WEIGHT = '0.75'
$env:NEURAL_RANKER_WEIGHT = '0.20'
$env:NEURAL_POLICY_WEIGHT = '0.05'
```

`NEURAL_ROLLOUT_MODE=auto` uses exact sim rollouts only when enough replay seed
information is available. Otherwise it uses approximate rollout/action
diagnostics.

### Strict Live Eval Startup

Set strict mode when you want startup to fail instead of silently using stale or
fallback pieces:

```powershell
$env:NEURAL_STRICT_LIVE_EVAL = '1'
.\scripts\run_windows.ps1 -Action live-eval -SimCoreMode native
```

Strict mode refuses to start unless:

- The selected live-private value checkpoint exists.
- Its `feature_version` is exactly `live-private-belief-v2`.
- The selected action-value ranker exists.
- The ranker's `input_size` equals `state_dim + action_dim`.
- The ranker's `action_dim` equals the current `ACTION_FEATURE_DIM`.
- The ranker's `state_dim` equals the current `LIVE_PRIVATE_FEATURE_DIM`.
- sim-core is reachable through `NEURAL_SIM_CORE_COMMAND_JSON` and
  `NEURAL_SIM_CORE_CWD`.
- The Smogon damage smoke test returns `damage_method=smogon_calc`.
- No `heuristic_fallback` appears during startup smoke diagnostics.

Startup diagnostics print selected checkpoint paths, mtimes, sizes, feature
versions, dimensions, and healthcheck results.

Run diagnostics without keeping the HTTP server open:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
$env:NEURAL_SIM_CORE_CWD = (Resolve-Path .\sim-core)
$serverJs = (Resolve-Path .\sim-core\dist\src\server.js).Path
$env:NEURAL_SIM_CORE_COMMAND_JSON = ConvertTo-Json @('node', $serverJs) -Compress
& $py -m neural.live_eval_healthcheck
```

## Replay Pipeline

The replay tooling targets public saved replays from
`https://replay.pokemonshowdown.com`. It does not collect private replays or join
live rooms.

Fetch replays:

```powershell
.\scripts\run_windows.ps1 -Action fetch-replays -Format gen9randombattle -MaxReplays 1000 -DelaySec 0.5 -SimCoreMode native
```

Parse protocol logs:

```powershell
.\scripts\run_windows.ps1 -Action parse-replays -Format gen9randombattle -SimCoreMode native
```

Build public replay value/policy datasets:

```powershell
.\scripts\run_windows.ps1 -Action build-replay-value-dataset -Format gen9randombattle -SimCoreMode native
.\scripts\run_windows.ps1 -Action build-replay-policy-dataset -Format gen9randombattle -SimCoreMode native
```

Train replay value model:

```powershell
.\scripts\run_windows.ps1 -Action train-replay-value -Format gen9randombattle -SimCoreMode native
```

Compare the public replay value path with the live-private path on one replay:

```powershell
.\scripts\run_windows.ps1 -Action compare-replay-evals -ReplayId gen9randombattle-2594788118 -Side p1 -SimCoreMode native
```

Common outputs:

- `data/replays/raw/<format>/`
- `data/replays/raw/<format>/metadata.jsonl`
- `data/replays/processed/<format>_trajectories.jsonl.gz`
- `data/replays/processed/<format>_public_policy.jsonl.gz`
- `data/value/<format>_public_replay_value.npz`
- `artifacts/replays/fetch_report.json`
- `artifacts/replays/parse_report.json`
- `artifacts/analysis/*_dataset_report.json`

## Simulator Dataset, Training, and Evaluation

Collect local simulator data:

```powershell
.\scripts\run_windows.ps1 -Action dataset -Profile dev -SimCoreMode native
```

Train behavior cloning:

```powershell
.\scripts\run_windows.ps1 -Action train -Profile dev -SimCoreMode native
```

Evaluate:

```powershell
.\scripts\run_windows.ps1 -Action eval -Profile dev -SimCoreMode native
```

Fine-tune with PPO:

```powershell
.\scripts\run_windows.ps1 -Action ppo -Profile dev -SimCoreMode native
```

Run the bounded improvement loop:

```powershell
.\scripts\run_windows.ps1 -Action improve -Profile dev -SimCoreMode native
```

Collect self-play:

```powershell
.\scripts\run_windows.ps1 -Action collect-selfplay -Profile dev -SimCoreMode native
```

The improvement loop appends data, resumes BC when configured, optionally runs
PPO, evaluates, and promotes a best checkpoint only when metrics improve.

## Traces and Analysis

Generate traced eval battles:

```powershell
.\scripts\run_windows.ps1 -Action trace-eval -Profile dev -SimCoreMode native
```

Typical outputs:

- `artifacts/battles/dev/battle_*.json`
- `artifacts/battles/dev/battle_*.md`
- `artifacts/battles/dev/battle_*.showdown.log`

Analyze decision categories:

```powershell
.\scripts\run_windows.ps1 -Action analyze -DatasetPath .\data\raw\gen9randombattle_bc.dev.jsonl.gz
```

Train and inspect a local trace value model:

```powershell
.\scripts\run_windows.ps1 -Action build-value-dataset -TraceDir .\artifacts\battles\dev
.\scripts\run_windows.ps1 -Action train-value -DatasetPath .\data\value\gen9randombattle_value.npz
.\scripts\run_windows.ps1 -Action analyze-state -TracePath .\artifacts\battles\dev\battle_0.json -StepIndex 10 -ValueCheckpoint .\artifacts\checkpoints\gen9randombattle_value.pt
```

Analyze rollout/action estimates for a replay:

```powershell
.\scripts\run_windows.ps1 -Action analyze-rollout-actions -ReplayPath .\data\replays\raw\gen9randombattle\gen9randombattle-2594788118.log -Side p1 -RolloutMode approximate
```

Useful analysis modules:

- `neural.analyze_decisions`
- `neural.analyze_state`
- `neural.analyze_rollout_actions`
- `neural.analyze_action_bias`
- `neural.analyze_tactical_failures`
- `neural.compare_checkpoints`
- `neural.compare_replay_evals`
- `neural.compare_value_models`
- `neural.compare_action_rankers`

## Damage Engine

Damage estimates are backed by `@smogon/calc` through sim-core when possible.
The Python `damage_engine` can also spawn the built Node damage module directly.
When exact attacker or defender stats are available in a private request, the
calculator uses those raw stats and reports `used_exact_attacker_stats` and
`used_exact_defender_stats`. Regression tests verify that changing exact stats
changes the returned damage range.

Healthcheck:

```powershell
$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
& $py -m neural.damage_engine --json
```

Strict live eval requires the startup smoke test to return
`damage_method=smogon_calc`; heuristic fallback is treated as a startup failure
when `NEURAL_STRICT_LIVE_EVAL=1`.

## Testing

Run all tests through the launcher:

```powershell
.\scripts\run_windows.ps1 -Action test -SimCoreMode native
```

Run the dedicated simulator parity gate before trusting new model-training or
evaluation results:

```powershell
.\scripts\run_windows.ps1 -Action validate-sim-core -SimCoreMode native
```

Run the opt-in bounded two-ply material branch audit:

```powershell
.\scripts\run_windows.ps1 -Action two-ply-branch-audit -SimCoreMode native
```

Run the live-information-boundary randbats-belief branch audit:

```powershell
.\scripts\run_windows.ps1 -Action belief-branch-audit -SimCoreMode native
```

Run the deterministic three-particle randbats-belief audit:

```powershell
.\scripts\run_windows.ps1 -Action belief-particles-audit -SimCoreMode native
```

The gate records the pinned Pokemon Showdown and Smogon calc versions, exercises
seeded Gen 9 singles mechanics/legal-action/privacy checks, validates exact-stat
damage, and parses saved public replay prefixes. Simulator dependency upgrades
must be followed by this validation command.

### Simulator performance

Pokemon Showdown battle mechanics run in Node.js on the CPU; they do not use
CUDA. PyTorch policy, value, and ranker inference uses the GPU when available.
The normal eval loop batches model inference, but one sim-core process still
executes battle RPC work on a single JavaScript thread.

For large agent audits, use process-level sharding so each worker owns an
independent unchanged sim-core process:

```powershell
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
& 'D:\Anaconda\envs\neuralgpu\python.exe' -m neural.agent_audit --battles 100 --workers 6
```

Six workers is the measured default for the current 8-core machine, leaving two
cores for the parent process and operating system. Each worker limits PyTorch
CPU threads to one to avoid oversubscription. Seeds and Showdown mechanics are
unchanged, so this optimization affects throughput rather than battle accuracy.

Manual test commands:

```powershell
cd .\sim-core
npm test
cd ..

$py = 'D:\Anaconda\envs\neuralgpu\python.exe'
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
& $py -m pytest .\trainer\tests -q
```

Useful focused tests:

```powershell
& $py -m pytest .\trainer\tests\test_live_private_value.py -q
& $py -m pytest .\trainer\tests\test_action_ranker.py -q
& $py -m pytest .\trainer\tests\test_sim_rollout.py -q
```

## Important Artifacts

Frequently used checkpoints:

- `artifacts/checkpoints/gen9randombattle_bc.dev.pt`
- `artifacts/checkpoints/gen9randombattle_bc.pt`
- `artifacts/checkpoints/gen9randombattle_replay_policy.pt`
- `artifacts/checkpoints/gen9randombattle_replay_value.pt`
- `artifacts/checkpoints/gen9randombattle_live_private_value_v2.pt`
- `artifacts/checkpoints/gen9randombattle_action_ranker_v2.pt`
- `artifacts/checkpoints/gen9randombattle_action_value_ranker_v2.pt`

Frequently used datasets:

- `data/raw/gen9randombattle_bc.dev.jsonl.gz`
- `data/shards/gen9randombattle_bc.dev.npz`
- `data/replays/processed/gen9randombattle_trajectories.jsonl.gz`
- `data/value/gen9randombattle_live_private_value_v2.npz`
- `data/policy/gen9randombattle_action_rank_v2.npz`
- `data/policy/gen9randombattle_action_value_rank_v2.npz`

Reports and diagnostics:

- `artifacts/eval/*.json`
- `artifacts/latency/*.json`
- `artifacts/analysis/*.json`
- `artifacts/analysis/*.md`
- `artifacts/replays/*.json`
- `artifacts/improve/**`
- `artifacts/live_eval_server.log`
- `artifacts/live_eval_server.err.log`

## Environment Variables

Core runtime:

- `PYTHONPATH`: should include `trainer/src`.
- `NEURAL_SIM_CORE_CWD`: working directory for the sim-core subprocess.
- `NEURAL_SIM_CORE_COMMAND_JSON`: JSON argv list used to start sim-core.

Live eval:

- `NEURAL_LIVE_EVAL_PORT`: defaults to `8765`.
- `NEURAL_LIVE_MODEL`: `live-private` or `public-replay`.
- `NEURAL_LIVE_VALUE_CHECKPOINT`: override selected value checkpoint.
- `NEURAL_ACTION_RANKER_CHECKPOINT`: override selected action ranker.
- `NEURAL_STRICT_LIVE_EVAL`: set to `1` for strict startup validation.
- `NEURAL_LIVE_CORS_ORIGINS`: comma-separated CORS origins.
- `NEURAL_LIVE_CORS_ORIGIN_REGEX`: CORS regex override.

Action recommendation:

- `NEURAL_ROLLOUTS_PER_ACTION`
- `NEURAL_ROLLOUT_MODE`
- `NEURAL_OPPONENT_POLICY`
- `NEURAL_ROLLOUT_WEIGHT`
- `NEURAL_RANKER_WEIGHT`
- `NEURAL_POLICY_WEIGHT`

vNext diagnostic program:

- `NEURAL_VNEXT_INFERENCE`: opt-in flag for the isolated vNext inference harness
  (`neural.vnext_inference`). Default off; the live default path does not depend
  on it.

sim-core tracing:

- `SIM_CORE_TRACE_RPC`
- `SIM_CORE_TRACE_SLOW_MS`

## Troubleshooting

Port already in use:

```powershell
netstat -ano | findstr :8765
Stop-Process -Id <PID> -Force
```

sim-core is not reachable:

- Make sure `sim-core/dist/src/server.js` exists.
- Run `npm run build` in `sim-core`.
- Confirm `NEURAL_SIM_CORE_CWD` points to `.\sim-core`.
- Confirm `NEURAL_SIM_CORE_COMMAND_JSON` contains a valid JSON argv list.

Strict live eval fails:

- Read the startup diagnostics JSON first; it prints selected paths, mtimes,
  dimensions, feature versions, and smoke-test results.
- Confirm the value checkpoint is v2:
  `artifacts/checkpoints/gen9randombattle_live_private_value_v2.pt`
- Confirm the action-value ranker is current:
  `artifacts/checkpoints/gen9randombattle_action_value_ranker_v2.pt`
- Rebuild/retrain stale datasets or rankers if feature dimensions changed.

Damage falls back to heuristic:

- Rebuild sim-core.
- Check that `@smogon/calc` is installed under `sim-core/node_modules`.
- Run `& $py -m neural.damage_engine --json` after setting `PYTHONPATH`.
- In strict live eval, any startup `heuristic_fallback` is a hard failure.

High-parallel eval timeouts:

- Prefer `*-stable.yaml` eval configs for long runs.
- Reduce `runtime.num_envs`.
- Increase `runtime.timeouts_sec.step` and `runtime.timeouts_sec.batch`.
- Inspect `artifacts/latency/*.json` for queue wait, server time, transport
  overhead, retries, and timeout diagnostics.

PowerShell output looks strange:

- Most Python modules intentionally print compact single-line progress and write
  full JSON/Markdown reports to artifacts. Prefer the report files for detailed
  inspection.

## Current Limitations

- Simulator parity coverage targets seeded Gen 9 singles. Doubles and other
  multi-action formats are outside the fixed 13-action codec's scope.
- Exact public replay reproduction is not supported: ordinary public replay
  logs omit the original PRNG seed, complete private teams, and private request
  choices. Public-state parsing and prefix validation remain supported.
- Exact branch search is limited by whether a trace has enough deterministic
  replay seed/state information. Without that, live recommendations use
  approximate rollouts and diagnostics.
- Public replay data is biased toward battles that players saved or uploaded.
- Replay-derived public features and live-private features are separate feature
  domains. Do not swap checkpoints across them unless the input dimensions and
  feature versions match.
- Action recommendations are model/search diagnostics, not hardcoded bans. The
  code should not forbid resisted attacks, immunities, setup, switches, or
  terastallization by rule; those should be learned or scored by models/search.
- The vNext v7/v5 program is diagnostic-only. No vNext checkpoint is promoted, the
  live `/evaluate` defaults remain v2/v3, and the opt-in vNext inference harness is
  off by default and not wired into live battles. The promotion gate
  (`artifacts/training_plan/diagnostic_training_gate.md`) stays closed until a
  controlled private-match dry run and explicit approval.
