# vNext Shadow Warm Latency Report

## Purpose

Confirm whether vNext shadow recommendations (`/evaluate-vnext-dry-run`) are fast
enough for manual use after warmup, by measuring cold vs warm latency in a single
process **with the persistent sim-core client available** (as the live server has).

## Commands Run

Measured by exercising the existing `vnext_live_shadow.build_dry_run` repeatedly
in one process, with the sim-core client env set (so the shadow reuses a
persistent client, matching the live server):

```powershell
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
$env:NEURAL_SIM_CORE_CWD = (Resolve-Path .\sim-core)
$serverJs = (Resolve-Path .\sim-core\dist\src\server.js).Path
$env:NEURAL_SIM_CORE_COMMAND_JSON = ConvertTo-Json @('node', $serverJs) -Compress
$env:NEURAL_VNEXT_INFERENCE = '1'
# one cold call + five warm calls of build_dry_run on the fixture packet
```

No new module/harness was created; the existing shadow function was called
directly. `git diff --check` clean (no code changed).

## Packet / Fixture Source

No raw browser-extension packet is captured anywhere in the repo (the eval log is
empty/sanitized; calibration states contain no `request`/`log`). Per the task,
the existing **sanitized live-style fixture** was used as the fallback: a Gen 9
request with a Tera-legal active Pokémon (Charizard, four moves, `canTerastallize`)
plus two bench Pokémon, and a short public log. No cookies/tokens/session data.

## Cold Latency (first call in the process)

**~4478 ms total**, one-time per server process:

| Stage | ms |
| --- | ---: |
| state generation | 134.1 |
| candidate generation | 0.0 |
| impact resolution (first sim-core client spawn + first smogon calcs) | 462.5 |
| model scoring (rank model load + CUDA warmup) | 2007.2 |
| response serialization | 0.0 |
| total | 4477.5 |

## Warm Latency (subsequent calls, same process)

Five warm calls: wall **35.0, 56.9, 36.4, 61.9, 50.6 ms** (mean **~48 ms**).
Representative warm breakdown:

| Stage | ms |
| --- | ---: |
| state generation | ~2.6 |
| candidate generation | 0.0 |
| **impact resolution (10 candidates)** | **~6.6–8.7** |
| model scoring | ~1.0 (occasional ~21 on a GPU sync tick) |
| response serialization | 0.0 |
| total | ~35 |

## Candidate / Result Diagnostics

- Candidate kind counts: **4 move + 4 move_tera + 2 switch** (10 total).
- Tera candidates generated: **yes** (4).
- Switch candidates generated: **yes** (2).
- Fail-closed path: **no** (`ok=true` on every call).
- Impact methods: `smogon_calc` 6, `non_damaging` 2, `unavailable` 2 (switches).

## Bottleneck

- **Warm steady-state is not a problem** (~35–60 ms total; impact ~7 ms).
- The earlier ~2.9 s impact figure was a **cold, no-persistent-client** artifact:
  `resolve_action_impact` without a sim-core client spawns the Node damage module
  per damaging candidate. With the live server's persistent sim-core client (which
  the shadow module caches and reuses), per-call impact resolution is ~7 ms.
- The only remaining cost is the **one-time cold call (~4.5 s)** per server
  process, dominated by the rank-model load + CUDA warmup (~2 s) and the first
  sim-core client spawn / first smogon calcs (~0.5 s).

## Optimization Made

**None.** The shadow path already caches the `VNextActionRanker` and the sim-core
damage client across requests, so warm latency is already well within
interactive range. No change was warranted, and making one would risk the v5
semantics for no benefit.

## Confirmations

- v5 (or any) feature semantics changed: **no**.
- Commands sent to Showdown: **no**.
- Battles run by the model: **no**.
- Live defaults changed: **no**.
- Gate: remains **closed**.

## Usability Verdict

After the one-time warmup, vNext shadow recommendations return in ~35–60 ms — fast
enough for comfortable manual use alongside the normal `/evaluate` display. The
first decision of a server session incurs a ~4.5 s warmup.

## Remaining Blockers Before Manual Private-Match Recommendation Testing

1. **First-call warmup (~4.5 s)** is one-time but noticeable; optional low-risk
   future improvement: pre-load the rank model + sim-core client at server startup
   (not done here to avoid touching the default startup path).
2. **Real extension packet validation**: warm numbers were measured on the
   sanitized fixture; confirm with real Showdown packets that v7 state / v5
   candidates generate without fail-closed and that latency holds.
3. **Slot-index / live-parity** of serialized vNext commands vs live Showdown
   choice acceptance still needs a real-room check (display-only until then).
