# Live-Eval Calibration Dataset Report (Part B)

**Date:** 2026-06-18
**Generator:** `trainer/src/neural/live_eval_calibration.py`
**States file:** `artifacts/live_eval_calibration/live_eval_calibration_states.jsonl`
**Metrics file:** `artifacts/live_eval_calibration/live_eval_calibration_metrics.json`

## How states were collected

Seeded sim-core Gen 9 Random Battle singles, deterministic
(`make_battle_seed(index)`), 24 games, alternating matchups for state diversity:
balanced `heuristic` vs `heuristic` and lopsided `heuristic` vs `random` (more
decisive states). For every game the harness captures per-turn snapshots holding
the protocol log, both sides' `requests`, and both sides' legal `views`. Each
actionable `(snapshot, side)` becomes one calibration state, scored from that
side's perspective and labeled with the **perspective-correct final outcome**
(+1 win / −1 loss / 0 tie). Features never contain exact hidden opponent state —
the same live/serving path used by `/evaluate`.

## Dataset size

| Field | Value |
| --- | --- |
| Games requested / used | 24 / 24 |
| **Total states** | **1406** |
| p1 / p2 | both sides scored at every shared state |
| Win / loss / tie outcomes | 672 / 734 / 0 |
| Skipped (non-actionable / no view) | 188 |
| Wall time | 14.4 s |

## Scorers recorded per state

- `material` — `(own_hp − opp_hp)/6` from the legal view (hidden bench at full HP).
- `live_sim_value` — bounded tanh head (`gen9randombattle_live_sim_value_v1.pt`).
- `old_live_private` — the **unbounded** value head that `/evaluate` uses today
  (`gen9randombattle_live_private_value_v2.pt`), via `make_value_score_fn`.

Each row also stores: `turn`, `turns_to_end`, `side`, `final_winner`, `outcome`,
a `summary` (own/opp HP, alive counts, active HP/status, hazards), and `tags`.

## State-category coverage (the requested calibration mix)

| Tag | n | Meaning |
| --- | ---: | --- |
| early | 175 | turn ≤ 3 (neutral openings) |
| winning | 68 | HP differential ≥ 1.5 |
| losing | 807 | HP differential ≤ −1.5 |
| material_ahead | 1160 | more alive mons than revealed opponent |
| material_behind | 75 | fewer alive than revealed opponent |
| near_terminal | 167 | ≤ 2 turns from game end |
| low_hp_active | 130 | active ≤ 25% HP (disadvantage) |
| own_status | 219 | own side carries a status condition |
| hazards | present | entry hazards on a side |

Post-KO advantage states are captured via `material_ahead`/`material_behind`;
obvious safe-KO and bad-switch decisions are represented within `near_terminal`
and `low_hp_active`. (The lopsided heuristic-vs-random games over-represent
`losing`/`material_ahead` from the strong side's view; both perspectives are kept,
so the opposite labels are present too. Outcome balance is near 50/50: 672 win /
734 loss.)

## Per-category mean score (sanity)

| Tag | material | live_sim_value | old_live_private |
| --- | ---: | ---: | ---: |
| winning | +0.50 | +0.51 | +1.17 |
| losing | −0.16 | −0.34 | **+0.88** |
| material_behind | −0.47 | −0.82 | −0.32 |
| low_hp_active | −0.19 | −0.28 | **+1.05** |
| near_terminal | −0.03 | −0.06 | **+0.81** |
| own_status | +0.20 | +0.25 | +1.12 |

`material` and `live_sim_value` sign correctly per category. `old_live_private`
returns a strongly **positive** score even for **losing**, **low-HP**, and
**near-terminal** states — the collapse the calibration report quantifies.

## Reproduce

```powershell
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
$env:NEURAL_SIM_CORE_CWD = (Resolve-Path .\sim-core)
$serverJs = (Resolve-Path .\sim-core\dist\src\server.js).Path
$env:NEURAL_SIM_CORE_COMMAND_JSON = ConvertTo-Json @('node', $serverJs) -Compress
& $env:PYTHONPATH\..\..\ ; D:\Anaconda\envs\neuralgpu\python.exe -m neural.live_eval_calibration --num-games 24
```
