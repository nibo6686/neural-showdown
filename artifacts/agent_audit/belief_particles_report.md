# Multi-Particle Randbats-Belief Two-Ply Audit

Audit date: 2026-06-19  
Scope: seeded Gen 9 singles, paired sides versus heuristic.

## Results

| Agent | Battles | Wins | Losses | Winrate | Avg latency | p95 latency | Particles | Avg branches | Avg leaves | Belief errors | Public-info violations | Damage fallbacks |
| ----- | ------: | ---: | -----: | ------: | ----------: | ----------: | --------: | -----------: | ---------: | ------------: | ---------------------: | ---------------: |
| heuristic | 20 | 10 | 10 | 50% | 1.6 ms | 3.2 ms | 0 | 0 | 0 | 0 | 0 | 0 |
| branch_one_turn | 20 | 9 | 11 | 45% | 2488 ms | 5871 ms | 0 | 20.67 | not recorded | 0 | 0 | 0 |
| branch_two_ply_material (exact upper bound) | 20 | 12 | 8 | **60%** | 2353 ms | 6962 ms | 0 | 20.95 | 14.49 | 0 | 0 | 0 |
| branch_two_ply_belief_material | 20 | 6 | 14 | **30%** | 769 ms | 1344 ms | 1 | 23.51 | 15.75 | 0 | 0 | 0 |
| branch_two_ply_belief3_material | 20 | 6 | 14 | **30%** | 2469 ms | 4017 ms | 3 | 69.73 | 46.60 | 0 | 0 | 0 |

Baseline source: `artifacts/agent_audit/belief_particles/summary.json`.
Final three-particle source, including per-decision score diagnostics:
`artifacts/agent_audit/belief_particles_detail/summary.json`.

## Aggregation and safeguards

The three-particle agent derives three stable belief seeds per decision.
Particle 0 preserves the former single-particle base seed. Every particle
sanitizes the current snapshot independently, preserves all public facts, and
scores the same three bounded root actions. Each root action is selected by the
mean of its three particle root scores; the report also retains standard
deviation, worst score, best score, and the individual particle scores.

Opponent requests and legal actions come only from sanitized particle envs.
The source opponent request and true hidden team are not passed into particle
search. Failed samples cannot silently switch to exact hidden reconstruction.

The full run recorded:

- 712 audited decisions and exactly 2136 belief samples;
- 0 belief sample errors;
- 0 public-information constraint violations;
- 0 branch errors, timeouts, or capped leaves;
- 0 damage fallbacks;
- 87 relaxed/impossible generator matches and 0 missing randbats-data cases.

The relaxed cases preserved all revealed facts and are sampling-quality
warnings, not information-boundary or branch failures.

## Smoke gate

The required five-battle smoke completed 1-4 with:

- 149 decisions and exactly 447 samples;
- 1993 ms average / 3334 ms p95 latency;
- 68.75 branches and 45.92 leaves per decision;
- 0 belief errors, public-info violations, branch errors, timeouts, caps, or
  damage fallbacks.

## Comparison

- Exact upper bound: 60%.
- Single-particle belief: 30%.
- Three-particle belief: 30%.
- Three-particle versus one-turn material: **-15 percentage points**.
- Three-particle versus heuristic: **-20 percentage points**.
- Three-particle versus exact upper bound: **-30 percentage points**.
- Average latency multiplier from one to three particles: **3.21×**.
- Branch multiplier: **2.97×**; leaf multiplier: **2.96×**.

The ensemble changed behavior, but not net performance:

- particles disagreed on their individually preferred root action in 124 of
  712 decisions (17.4%);
- the ensemble's first action differed from the single-particle agent in 3 of
  20 paired battles;
- final outcomes differed in four battles: two single-particle losses became
  wins and two wins became losses;
- the two agents still finished with the same 6-14 record.

Action-index sequences diverged in 18 of 20 battles, though comparisons after
the first divergent action are descriptive rather than state-matched because
the battle trajectories are then different.

## Performance and reliability

Three particles added approximately linear cost. Average latency increased
from 769 ms to 2469 ms and p95 from 1344 ms to 4017 ms. The ensemble remained
inside the eight-second total decision budget in every audited decision.

The exact two-ply rerun retained its 12-8 result but had eight deadline-hit
decisions and nine capped fallback leaves. Those are explicit material scoring
of already-computed successors, not damage fallbacks. The belief modes had no
deadline or cap use.

## Interpretation

### Did three particles improve over the single-particle 30% result?

No. Both modes scored 6-14 (30%).

### Did it recover toward one-turn material or heuristic?

No. It remained 15 points below one-turn material and 20 points below
heuristic.

### Did added particles reduce brittleness?

They exposed and averaged real particle disagreement, but did not reduce
outcome brittleness in this sample. Four outcomes changed and canceled exactly.
Uniformly sampling more plausible teams is therefore insufficient by itself.

### Is multi-particle belief worth continuing?

Yes as a bounded uncertainty and disagreement diagnostic; no as the next agent
to scale blindly. Five uniform particles would likely add cost without fixing
the missing belief calibration.

### Should exact two-ply remain the upper-bound mode?

Yes. Its 60% result remains useful as an explicitly hidden-information-assisted
upper bound.

### Should belief-particle mode become the preferred live-realistic mode?

Not yet. Keep single-particle belief as the cheaper live-realistic baseline and
use three-particle belief when measuring uncertainty or action disagreement.
The ensemble did not justify its 3.21× latency as the default research agent.

### Should live defaults change?

No. All branch modes remain opt-in research paths.

## Recommended next task

Build a belief-calibration audit that weights or rejects randbats samples using
only public damage ranges, observed speed order, revealed moves/items/abilities,
and public team-composition constraints. Measure whether calibrated particle
weights improve exact-hidden-set coverage and action agreement before trying
five particles.

## Validation

Passed:

```powershell
.\scripts\run_windows.ps1 -Action validate-sim-core -SimCoreMode native
.\scripts\run_windows.ps1 -Action test -SimCoreMode native
```

Results: 177 Python tests passed, 1 skipped; 26 sim-core tests passed.

Audit command:

```powershell
.\scripts\run_windows.ps1 -Action belief-particles-audit -SimCoreMode native
```
