# Action-Impact Audit Report (Part E)

**Date:** 2026-06-18
**Inputs:** the Part D synthetic fixture (`draco_vs_psyshock_diagnostic.json`, real
`smogon_calc` damage) for per-action scorer comparison; the 1406-state calibration
study (`live_eval_calibration/`) and the 20-game branch audit
(`agent_audit/live_sim_value_branch_audit_report.md`) for the population-level
action-impact↔future-position agreement.

Action-impact = how much a scorer prefers the action that leads to the better
*resulting* position. The audit asks whether the live recommender's ranking agrees
with future-position evaluation.

## Per-action table (synthetic Latios vs Hariyama, smogon_calc damage)

| State | Action | Immediate damage % | Side effect | One-turn material | Two-ply material | Ranker score | Rollout score (approx) | Blended final (0.75/0.20/0.05) | Chosen? | Notes |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| Latios vs Hariyama | Psyshock | 83.8 (2× SE) | none | n/a (no seed) | would stay high (no drop) | −3.601 (rank 4) | **3.611 (rank 1)** | **2.758 (rank 1)** | **blended ✓** | super-effective, no drawback — the defensible move |
| Latios vs Hariyama | Draco Meteor | 67.7 (neutral) | **−2 SpA** | n/a (no seed) | would drop (halved follow-up) | **−2.426 (rank 1)** | 3.267 (rank 2) | 2.650 (rank 2) | **ranker ✓** | the ranker's pick; SpA drop invisible to every scorer |
| Latios vs Hariyama | Dragon Pulse | 33.8 | none | n/a | — | −2.604 | 2.075 | 1.591 | — | |
| Latios vs Hariyama | Aura Sphere | 28.0 | none | n/a | — | −3.761 | 1.566 | 1.175 | — | |
| Latios vs Hariyama | Flamethrower | 15.7 | none | n/a | — | −2.500 | 1.298 | 0.974 | — | |
| Latios vs Hariyama | switch: Latias | — | switch | n/a | — | −3.988 | −0.100 | −0.075 | — | |

"One/two-ply material" are **unavailable live** (no PRNG seed / exact-opponent
reconstruction) — marked, not omitted. The "would …" entries are the *expected*
direction from mechanics: a 2-ply material search re-derives that after Draco Meteor
the attacker's next special hit is ≈ halved, so Draco's two-ply material is worse
than Psyshock's. That is exactly the signal the live recommender lacks.

### Reading the fixture honestly

In *this* fixture the **blended** live score picks Psyshock (the rollout term, weight
0.75, dominates and Psyshock out-damages Draco here). It is the **action-value ranker
alone** that prefers Draco and buries Psyshock at rank 4. The disputed live decision
(Draco chosen) therefore corresponds to a state where Draco's immediate-damage
estimate was *competitive* with Psyshock's — at which point **no component penalizes
the −2 SpA drop**, the ranker is already biased toward the bigger nominal move, and
Draco wins the blend. The fixture reproduces the failing component and its mechanism,
not the exact live magnitudes.

## Population-level agreement (existing measurements)

From `live_eval_calibration/action_impact_calibration_report.md` and the 20-game
branch audit — same leaf scorers, paired seeded games vs heuristic:

| Leaf scorer | Winrate vs heuristic | State sign-acc | Corr with outcome |
| --- | ---: | ---: | ---: |
| material/HP | **45%** | 0.816 | 0.713 |
| live_sim_value | 15% | 0.936 | 0.872 |
| old_live_private (value) | **0%** | 0.558 | 0.325 |
| action_value_ranker | 10% | — | — |
| heuristic baseline | 50% | — | — |

The best *future-position* signal measured to date is plain **material/HP** one-ply
(45%). The action-value ranker (the live weight-0.20 component) selects actions at
10% — worse than a one-ply material lookahead — and the collapsed old value head is
at 0%. So the live ranking is **not** aligned with future-position evaluation.

## Answers to the audit questions

- **Is the recommender overweighting immediate damage?** Partly. The dominant live
  term (rollout, 0.75) is an immediate-damage-weighted *current-state* proxy with no
  lookahead, so the blend leans on immediate damage. But the disputed pick is driven
  as much by the ranker as by raw damage.
- **Is it ignoring self-stat drops?** **Yes, completely.** No component (damage
  diag, action-feature schema, approximate score) represents Draco's −2 SpA, Close
  Combat's −1 Def/SpD, recoil, recharge, or lock-in. This is the cleanest defect.
- **Is it failing to account for future positioning?** **Yes.** Live never evaluates
  the state that *results* from an action — there are no real next-state values and
  no current→next deltas. The drawback only shows up in a *future* position, which is
  never scored.
- **Is the action-value ranker miscalibrated?** **Yes for this class of decision.**
  It prefers the higher-base-power Draco Meteor over a super-effective Psyshock, its
  165D feature schema has no self-stat-drop/recoil/recharge feature, and it selects
  at only 10% vs heuristic. Its labels also derive from the collapsed live-private
  value head.
- **Is the policy prior dominating?** **No.** Weight 0.05 and usually 0/unavailable
  (replay-policy checkpoint missing or mismarked).
- **Are rollouts unavailable or too weak?** Live rollouts are **approximate** (no
  seed) — a noisy current-state proxy, not real Showdown transitions. "Too weak":
  they cannot see a resulting position, so they cannot see a drawback.
- **Is the current state-eval scorer used correctly for action deltas?** **No.** The
  well-calibrated `live_sim_value` head (used now for *display*) is **not** used in
  action selection at all; the action path still leans on the collapsed legacy head
  (switch-proxy + ranker labels). No proper deltas are computed.
- **Are the questionable choices defensible under uncertainty?** **Sometimes, by
  accident.** Draco Meteor can be correct (guaranteed large chunk, you intend to
  pivot, switch-prediction, tera plans). The recommender is *not* reasoning about any
  of that — it has no representation of the cost or the future plan — so when it picks
  Draco it is not because it weighed the trade-off. This is why the fix is to make
  the trade-off *visible/scored*, not to ban the move.

## Conclusion

Action ranking does **not** agree with future-position evaluation. Two compounding,
independent defects: (1) **side-effect blindness** (no drawback is representable in
any scorer or in the action-feature schema) and (2) **no future-state evaluation in
live** (no resulting-state value, no delta; the calibrated value head is display-only
and the real branch tools are seeded-research-only). The well-evidenced lever is to
make resulting-state material the basis of action-impact (it already wins at 45%) and
to surface/score side effects — not to add type-chart rules.
