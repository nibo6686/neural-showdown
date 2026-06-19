# Action Trace Capture Runbook (Part C)

How to capture a live/local state whose action recommendation you dispute, so it
can be inspected without sending private team data.

## What the trace is

When `NEURAL_ACTION_TRACE=1`, every `/evaluate` response gains a
`debug.action_trace` bundle with one record per legal action. When
`NEURAL_ACTION_TRACE_PATH` is also set, each `/evaluate` appends one JSONL line to
that file. The trace is **opt-in**; with neither variable set, `/evaluate` behaves
exactly as before (no shape change to defaults).

Each record reports, for every legal action: index, label, move/switch name,
legality, final score and rank, chosen flag, damage (percent/range/KO/type
effectiveness/immune), side-effect annotations (self-stat drop, recoil, recharge,
lock-in, heal, setup, status, switch, priority), and per-scorer values
(rollout / action-value-ranker / policy-prior / switch-proxy) plus the
one-turn / two-ply / belief branch scorers marked **unavailable with a reason**
(they require seeded sim-core search and are not run live). Missing components are
never silently dropped.

## 1. Start the server with tracing on

```powershell
$env:NEURAL_ACTION_TRACE = "1"
$env:NEURAL_ACTION_TRACE_PATH = ".\artifacts\action_recommendation\action_traces.jsonl"
.\scripts\run_windows.ps1 -Action live-eval -SimCoreMode native
```

Optional: also keep the existing sanitized state log:

```powershell
$env:NEURAL_EVAL_LOG_PATH = ".\artifacts\action_recommendation\eval_states.jsonl"
```

Defaults are unchanged. Do **not** set `NEURAL_ROLLOUT_WEIGHT` / `NEURAL_RANKER_WEIGHT`
/ `NEURAL_POLICY_WEIGHT` / `NEURAL_EVAL_STATE_SCORER` unless you intend to alter
behavior — leaving them unset keeps the production defaults you are auditing.

## 2. Reproduce / capture a disputed state

1. Connect the Showdown overlay (the userscript in `scripts/`) so it POSTs to
   `127.0.0.1:8765/evaluate` as you play.
2. Play (or load a local battle) to the turn you dispute. Each turn the overlay
   queries `/evaluate`, which appends a line to the JSONL.
3. Note the **room id** shown in the overlay/Showdown URL and the **turn number**.
   You'll use them to find the right line.

To capture without the overlay, POST a saved payload directly:

```powershell
$body = Get-Content .\my_payload.json -Raw
Invoke-RestMethod -Uri http://127.0.0.1:8765/evaluate -Method Post -ContentType 'application/json' -Body $body | ConvertTo-Json -Depth 8
```

(`my_payload.json` = `{room_id, url, player, log:[...], request:{...}, legal_actions:[...]}`.)

## 3. Find the room_id / turn / action in the trace

Each JSONL line is `{timestamp, room_id, player, turn, url, schema_version,
recommendation_method, chosen_label, weights, rollout_mode, metadata, records:[...]}`.

```powershell
# All captures for a room
Get-Content .\artifacts\action_recommendation\action_traces.jsonl |
  ConvertFrom-Json | Where-Object { $_.room_id -eq 'battle-gen9randombattle-123' }

# The disputed turn's chosen action and per-action scores
Get-Content .\artifacts\action_recommendation\action_traces.jsonl |
  ConvertFrom-Json |
  Where-Object { $_.room_id -eq 'battle-gen9randombattle-123' -and $_.turn -eq 14 } |
  ForEach-Object {
    "chosen: $($_.chosen_label)  method: $($_.recommendation_method)"
    $_.records | ForEach-Object {
      "{0,-22} final={1} rank={2} dmg%={3} drop={4}" -f `
        $_.label, $_.final_score, $_.ranks.final_rank, $_.damage.average_percent, ($_.side_effects.self_stat_drop | ConvertTo-Json -Compress)
    }
  }
```

The `chosen` action is the record with `ranks.final_rank == 1` (also flagged
`chosen: true`). Compare its `scorers.*` and `side_effects` against the action you
expected.

## 4. What to send / inspect

Send the matching **JSONL line(s)** only. They contain the diagnosis-relevant data.
Also useful: `draco_vs_psyshock_diagnostic.json` and the two reports
(`action_recommender_inventory.md`, `action_impact_audit_report.md`).

## 5. Avoiding logging private secrets

The trace is deliberately sanitized:

- **No raw `request` payload, no private `team` list, no PP / item / ability
  secrets, no feature vectors.** Records hold only action labels, scores, damage
  percentages, side-effect flags, and checkpoint paths.
- `room_id`, `player`, `turn`, `url` are included **only** to locate the state.
  Your own move and switch *names* appear (they are needed to read the decision);
  these are already visible to your opponent once used and are not hidden-team data.
- The writer never raises — if the path is unwritable, `/evaluate` still responds.
- A regression test (`test_action_trace.py::test_trace_does_not_leak_private_payload`)
  asserts the bundle contains no `request` / `side` / `pokemon` private keys.

If you want the in-response trace but **no** file on disk, set `NEURAL_ACTION_TRACE=1`
and leave `NEURAL_ACTION_TRACE_PATH` unset; the bundle appears under
`debug.action_trace` in the HTTP response only.
