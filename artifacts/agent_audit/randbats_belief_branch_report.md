# Randbats-Belief Two-Ply Branch Audit

Audit date: 2026-06-18  
Scope: seeded Gen 9 singles, paired sides versus heuristic.

## Results

| Agent | Battles | Wins | Losses | Winrate | Avg latency | p95 latency | Avg branches | Avg leaves | Belief errors | Damage fallbacks |
| ----- | ------: | ---: | -----: | ------: | ----------: | ----------: | -----------: | ---------: | ------------: | ---------------: |
| heuristic | 20 | 10 | 10 | 50% | 1.4 ms | 2.8 ms | 0 | 0 | 0 | 0 |
| branch_one_turn_material | 20 | 9 | 11 | 45% | 1941 ms | 4246 ms | not recorded | not recorded | 0 | 0 |
| branch_two_ply_material (exact upper bound) | 20 | 12 | 8 | **60%** | 2207 ms | 6228 ms | 21.01 | 14.53 | 0 | 0 |
| branch_two_ply_belief_material | 20 | 6 | 14 | **30%** | 663 ms | 985 ms | 23.51 | 15.75 | 0 | 0 |
| action_value_ranker | 20 | 2 | 18 | 10% | 23.7 ms | 27.9 ms | 0 | 0 | 0 | 0 |

The exact, heuristic, one-turn, and ranker rows are the existing paired results
using the same `make_battle_seed(index // 2)` scheme. The corrected clean belief
run is in
`artifacts/agent_audit/randbats_belief_branch_material_clean/summary.json`.

## Belief implementation

Belief mode no longer replays the original seed/team. It uses the pinned
Showdown engine's `Battle.toJSON()` / `Battle.fromJSON()` support:

1. snapshot the current source battle;
2. read only the audited player's public opponent view;
3. deterministically sample revealed-species sets and hidden bench species from
   the Gen 9 randbats generator;
4. require all revealed moves and publicly known item, ability, and used tera;
5. replace hidden opponent set fields in the serialized snapshot;
6. copy back only public dynamic state (HP ratio, status, boosts, volatiles,
   faint/active state, public constraints);
7. restore the sanitized snapshot into an isolated real sim-core env;
8. obtain opponent legal actions and heuristic ordering from that sampled env,
   never from the source opponent request.

The exact seeded mode is unchanged.

## Leakage and correctness safeguards

- Deterministic same-seed sampling: tested.
- Different belief seeds can change hidden sets: tested.
- Revealed moves are preserved: tested.
- Synthetic public item, ability, and tera constraints are preserved: tested.
- Deliberately changing the true hidden bench set does not change the belief
  sample: tested.
- Hidden bench sets come from randbats generation, not the source request.
- Post-restore public constraint checks: 0 violations in 706 decisions.
- Source env mutation: none.
- Branch errors/timeouts/caps: 0 / 0 / 0.
- Damage fallbacks: 0.

An early run found one battle-only/form species without a direct randbats table
key, causing 61 construction errors. The sampler was fixed to use the base
species generator while retaining the public forme. The failing seed and final
20-battle run then completed with zero errors or fallbacks.

## Belief diagnostics

- Belief samples: 706 (one deterministic particle per decision).
- Impossible/relaxed revealed-set cases: 22.
- Missing randbats data: 0.
- Public constraint violations: 0.
- Battle failures: 0.
- Average game length: 30.75 turns (range 15–52).

The 22 impossible cases mean the generator did not independently reproduce all
revealed constraints in 64 attempts. The fallback retained every public fact
and filled the remaining hidden fields from a sampled set. These are sampling
quality warnings, not branch-construction failures.

## Comparison

- Exact upper bound: 60%.
- Belief mode: 30%.
- Exact-to-belief delta: **-30 percentage points** (6 fewer wins).
- Belief versus one-turn material: **-15 points** (30% versus 45%).
- Belief versus heuristic: **-20 points** (30% versus 50%).
- Latency delta: belief mode is 1544 ms faster on average and 5243 ms faster at
  p95 because current-state snapshot forks avoid replaying from turn zero.

## Interpretation

### How much of the 60% exact result depended on hidden reconstruction?

In this sample, a great deal. Removing exact hidden sets cut winrate from 60% to
30%. The observed gain from deeper search did not survive the single-particle
live-information boundary.

### Does belief two-ply improve over one-turn material?

No: 30% versus 45%.

### Does it beat or approach heuristic?

No: 30% versus 50%.

### Where did errors come from?

The corrected run had no branch-construction, scoring, timeout, cap, or public
constraint errors. The weakness is belief quality/search variance, not plumbing.
The 22 relaxed cases indicate that a single generated set sometimes struggles
to match accumulated reveals.

### Is the sampler good enough for live-style research?

Yes as a mechanically credible baseline and information-leakage gate. No as a
strong decision policy. One deterministic particle per decision is too brittle:
the chosen action can overfit one plausible hidden team.

### Mode recommendations

- Keep exact two-ply as the explicitly labeled upper-bound research mode.
- Keep belief two-ply as the preferred **live-realistic diagnostic mode**, since
  it enforces the correct information boundary.
- Do not promote belief two-ply over one-turn material as the strongest agent.
- Keep all live recommender defaults unchanged.
- Do not run the optional 50-battle expansion yet; the clean 20-battle result is
  decisively below both one-turn material and heuristic.

## Recommended next task

Replace the single belief particle with a small deterministic ensemble (for
example 3 sampled opponent states per decision), aggregate each root action
across particles and opponent replies, and rerun the 20-battle gate. Reuse the
new snapshot-fork substrate so the added particles remain bounded.

## Validation commands

```powershell
.\scripts\run_windows.ps1 -Action validate-sim-core -SimCoreMode native
.\scripts\run_windows.ps1 -Action test -SimCoreMode native
```

Audit equivalent:

```powershell
python -m neural.agent_audit --agents branch_two_ply_belief_material --battles 20 --workers 6 --rollouts-per-action 1 --output-dir artifacts\agent_audit\randbats_belief_branch_material_clean
```

Validation result: 175 Python tests passed, 1 skipped; 26 sim-core tests passed;
simulator parity validation passed.
