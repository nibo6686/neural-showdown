# Bounded Two-Ply Branch Search — Audit Report

Audit date: 2026-06-18  
Scope: seeded Gen 9 singles, paired sides on shared seeds versus heuristic.

## Result

| Agent | Battles | Wins | Losses | Winrate | Avg latency | p95 latency | Avg branches | Avg leaves | Errors | Damage fallbacks |
| ----- | ------: | ---: | -----: | ------: | ----------: | ----------: | -----------: | ---------: | -----: | ---------------: |
| heuristic | 20 | 10 | 10 | 50% | 1.4 ms | 2.8 ms | 0 | 0 | 0 | 0 |
| branch_one_turn_material | 20 | 9 | 11 | 45% | 1941 ms | 4246 ms | not recorded | not recorded | 0 | 0 |
| branch_two_ply_material | 20 | 12 | 8 | **60%** | 2207 ms | 6228 ms | 21.01 | 14.53 | 0 | 0 |
| action_value_ranker | 20 | 2 | 18 | 10% | 23.7 ms | 27.9 ms | 0 | 0 | 0 | 0 |

The heuristic, one-turn material, and action-value rows are the existing paired
20-battle results on the same `make_battle_seed(index // 2)` seed scheme. The
new two-ply row is from
`artifacts/agent_audit/two_ply_branch_material/summary.json`.

## Search configuration

- Root actions: heuristic-ordered, capped at 3.
- Current opponent replies: heuristic-preferred first, capped at N=3.
- Own next-turn actions: heuristic-preferred first, capped at M=2.
- Opponent next-turn action: one deterministic heuristic reply.
- Leaf scorer: real post-step material/HP differential.
- Root aggregation: best own follow-up per opponent response, then mean over
  opponent responses (`risk_lambda=0`).
- Per-decision budget: 8 seconds, with the already-computed one-turn material
  successor used for unfinished leaves.

The initial 6/3/3 smoke was too slow (5191 ms average, 10129 ms p95) and touched
the deadline frequently. A 4/3/2 cap improved latency but still produced six
deadline-hit decisions in five battles. The final 3/3/2 smoke completed 5
battles at 1455 ms average / 2858 ms p95 with zero errors, timeouts, caps, or
damage fallbacks and scored 4-1.

## Correctness and reliability

- Original env mutation: none; every branch uses a separate replayed env.
- Fixed-seed determinism: tested and passing.
- Branch bound: tested and passing.
- Terminal override: tested and passing.
- Illegal actions: ignored cleanly.
- Root forced switch: explicitly falls back to one-turn material; successor
  forced switches remain searchable.
- Heuristic damage fallback: 0.
- Branch errors: 0.
- Battle failures: 0.
- Deadline-hit decisions in the 20-battle run: 3 of 592 audit decisions (0.5%).
- Capped fallback leaves: 4.

## Performance

- Average decision latency: 2.207 seconds.
- p95 decision latency: 6.228 seconds.
- Average transition branches per decision: 21.01.
- Average scored leaves per decision: 14.53.
- Six-worker wall time: 567.7 seconds for 20 battles.
- No direct CPU/sim-core utilization counter is available. A scheduler
  occupancy proxy (`sum(battle wall time) / (run wall time * workers)`) was
  38.6%; the 97-turn straggler left workers idle near the end, so this is not a
  CPU utilization measurement.

Latency is acceptable for an offline bounded research audit, but not for live
defaults. Average latency is close to one-turn material because the root cap is
smaller, while p95 is about two seconds worse and the longest game still reaches
the decision deadline.

## Game length and passivity

Two-ply did not create systematically longer or more passive games:

- two-ply average / median / p95 turns: 25.75 / 20 / 39;
- heuristic average: 26.8 turns;
- one-turn material average: 37.0 turns.

There was one 97-turn outlier (battle 17), which contained all three
deadline-hit decisions and all four capped leaves. The outlier matters for tail
latency, but the aggregate behavior was shorter and more decisive than one-turn
material.

## Answers

### Did two-ply improve over one-turn material?

Yes: 60% versus 45%, a gain of 3 wins in the same 20-battle paired-seed setup.
On individual battles, five one-turn losses became two-ply wins, while two
one-turn wins became two-ply losses.

### Did it approach or beat heuristic?

It beat the 50% heuristic reference in this bounded sample, 12-8.

### Was latency acceptable?

For opt-in offline research, yes, with the 3/3/2 cap. For live play, no:
2.2-second average and 6.2-second p95 remain too high, and tail games can still
hit the eight-second budget.

### Did it create longer/passive games?

No systematic regression was observed. Average and median games were shorter
than one-turn material, though one 97-turn outlier remains a warning about tail
behavior.

### Should two-ply replace one-turn material for research audits?

Yes as the preferred **exact-seeded research comparison**, because it is the
first branch agent in this project to beat the heuristic reference. Keep
one-turn material as the faster control and fallback. The 20-battle sample is
promising rather than conclusive.

### Should it remain disabled in live defaults?

Yes. It is slow and its seeded replay branches regenerate the opponent's exact
hidden team/set. The scorer is live-legal, but the simulated transitions encode
hidden information, so 60% is an optimistic research upper bound.

### Recommended next task

Replace exact hidden-opponent reconstruction with deterministic randbats-belief
sampling in the same bounded two-ply evaluator, then rerun the paired audit.
That is the critical test of whether the search-depth gain survives a
live-realistic information boundary.

## Validation

Passed:

```powershell
.\scripts\run_windows.ps1 -Action validate-sim-core -SimCoreMode native
.\scripts\run_windows.ps1 -Action test -SimCoreMode native
```

Full test result: 173 passed, 1 skipped. sim-core: 23 passed.

Audit command:

```powershell
$env:PYTHONPATH = (Resolve-Path .\trainer\src)
python -m neural.agent_audit --agents branch_two_ply_material --battles 20 --workers 6 --rollouts-per-action 1 --output-dir artifacts\agent_audit\two_ply_branch_material
```

The launcher equivalent is:

```powershell
.\scripts\run_windows.ps1 -Action two-ply-branch-audit -SimCoreMode native
```
