# diagnostic_1000 Action-Rank Dataset Plan

## Purpose

Scale the promising action-rank track from `diagnostic_300` to a larger frozen
v7/v5 diagnostic dataset (`diagnostic_1000_action_rank_v7_v5`), with deliberate
extra coverage of the two weak decision types found in the offline evaluation —
**Tera moves** and **switches** — without distorting the natural Random Battles
decision distribution. This document is a **plan + manifest** only. **No training
is launched here, and no full feature materialization is run.**

## Why Action-Rank Is Being Scaled Now

The offline evaluation (`diagnostic_300_action_rank_offline_eval.md`) showed the
`diagnostic_300` rank head beats every simple baseline on the validation split:
top-1 0.4556 vs 0.3909 (`max_expected_damage`) and 0.3882 (`type_prior_move`),
top-3 0.8656 vs 0.7276. It ranks non-damaging switches #1 where damage
heuristics rank them near last — i.e. it learns decision preferences beyond
damage/type priors. The limiting factor was data: only 210 independent training
battles, with sparse Tera actions (1.7% of positives) and some switch-vs-attack
confusion. More independent battles, with better Tera/switch coverage, is the
right next lever.

## Why Value-Head Work Is Paused

Per the standing decision rule (`diagnostic_training_gate.md`), reduced-capacity
regularized value-only training only just edged past the constant baseline
(test MSE 0.9453 vs ~1.0) and still overfit after one epoch. The achievable
signal on 210 battles is thin, so further `diagnostic_300` value tuning is
stopped. Action-rank is the track with demonstrated above-baseline learning, so
it gets the next dataset investment; value learning resumes only on a larger
dataset or with a redesigned target, under separate approval.

## Proposed Size and Splits

- Total battles: **1000**
- Split (battle-level, isolated): **train 700 / validation 150 / test 150**
- Source: existing replay pool only (`artifacts/training_plan/replay_catalog.jsonl`,
  14,255 eligible unique battles — no new replay downloads)
- Frozen schemas: state `live-private-belief-v7` (3208D), action
  `legal-action-v5` (318D)
- Objective: **action-rank only** (replay-imitation, one positive per matched
  group). Action-value labels remain **absent**. State-value labels will still
  be materialized by the existing pipeline (it co-produces them), but are not
  the training target.

## Enrichment Strategy

Battle-level stratified sampling, deterministic by seed `20260619`. A large
broad-random base preserves realism; modest enrichment buckets raise weak-type
coverage. Bucket targets (sum 1000):

| Bucket | Target | Definition |
| --- | ---: | --- |
| broad_random | 350 | uniform from eligible pool (realism anchor) |
| mechanics_enriched | 150 | any mechanic flag present |
| long_close | 150 | long_game or close_game_proxy (more decisions/battle) |
| switch_heavy | 110 | `input:switch` ≥ 18 (pool top-quartile) |
| higher_rating | 90 | rating in top quartile |
| tera_action_enriched | 90 | ≥1 actual Tera action (`-terastallize`) |
| rare_mechanic | 60 | any rare mechanic flag |

Key design choice: Tera is enriched on **actual Tera actions** (`-terastallize`
counts), not the `tera` battle flag (84% of battles already have Tera at the
battle level, so the flag is near-useless). Switches are enriched on **switch
decision volume** (`input:switch`), both cheaply read from the catalog's
`raw_command_counts` for every eligible battle.

**Anti-distortion check (selected vs random baseline, per 1000 battles):**

| Metric | Selected | Random baseline |
| --- | ---: | ---: |
| Switch decision total | 20,756 | 13,956 |
| Switch decisions / battle | 20.76 | 13.96 |
| **Switch share of decisions** | **0.237** | **0.252** |
| Tera action total | 1,547 | 1,333 |
| Battles with ≥1 Tera action | 924 | 850 |
| Long-game rate | 0.499 | 0.247 |
| Short/forfeit rate | 0.163 | 0.257 |

Switch *volume* rises ~49% in absolute terms while the switch *share* of
decisions stays ~24% (essentially the natural rate). Tera actions rise modestly
(+16%). So the dataset gains more switch and Tera examples mainly by favouring
longer, less-forfeited games — not by skewing the action mix. This matches the
"better coverage, not a distorted dataset" requirement.

Comparison vs `diagnostic_300`: the 300 manifest had mechanic-flag total 2090
over 300 battles (6.97/battle); the 1000 manifest has 6450 over 1000
(6.45/battle) — comparable per-battle enrichment intensity at 3.33× scale, with
the new Tera-action and switch-volume axes added.

## Expected Risks

- **Materializer is hardcoded to 300.** `benchmark_vnext_featuregen.py`'s
  `--full-manifest` preflight asserts exactly 300 entries, 210/45/45 splits, and
  the fixed `diagnostic_300_v7_v5` output path. Materializing 1000 requires a
  small, separate generalization of that preflight (parameterize expected
  count/splits/output dir). This is **not** done in this task.
- **Runtime / size.** 300 battles took ~2165s and 13.96 MiB. 1000 battles is
  ~3.33× → estimated **~2 hours wall time** and ~45 MiB (~31 MiB dataset),
  ~85k states / ~635k action candidates. Long enough to require explicit
  approval before running.
- **Replay-imitation label** still treats unmatched candidates as merely
  unchosen, not bad — top-1 understates decision quality (unchanged from 300).
- **Switch-heavy/long-close overlap** could correlate with game length; the
  share-of-decisions check above confirms it does not distort the action mix.
- **Test split discipline.** The 150-battle test split must not be used for any
  tuning; validation (150) is for exploratory analysis.

## Validation Checklist (manifest — already satisfied; see Part B)

- [x] 1000 unique battles
- [x] 700/150/150 split, exact
- [x] no split overlap (unique IDs across splits)
- [x] all entries in catalog; all replay paths exist
- [x] catalog SHA-256 recorded
- [x] mechanic coverage ≥ random baseline
- [x] seed recorded
- [x] enrichment metrics recorded (Tera action, switch volume, rates)
- [x] frozen v7/v5 schema names/dims recorded in manifest

## Exact Proposed Materialization Command (NOT run here)

Materialization is deferred. It requires (1) generalizing the
`benchmark_vnext_featuregen` full-manifest preflight to accept the 1000/700-150-150
profile and a new output directory, then (2) running, with explicit approval:

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
D:\Anaconda\envs\neuralgpu\python.exe -m neural.benchmark_vnext_featuregen `
  --full-manifest `
  --manifest .\artifacts\training_plan\manifests\diagnostic_1000_action_rank_manifest.json `
  --output-dir .\artifacts\training_plan\datasets\diagnostic_1000_action_rank_v7_v5
```

Estimated runtime ~2h on the current native sim-core path; estimated output
~45 MiB. After materialization, the dataset must pass the same v7/v5 schema /
fingerprint / split-integrity / action-value-absent checks the 300 dataset
passed before any training command is designed.

## Explicit Statement

No training was launched in this task. No checkpoint was created or promoted.
No live defaults were changed. No full feature materialization was run. Only the
battle-level manifest and its validation report were produced. The training and
live-promotion gate remains **closed**.
