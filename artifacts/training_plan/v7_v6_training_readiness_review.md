# v7/v6 Training-Readiness Review (post mechanics FAIL=0)

## Status going in

- Comprehensive mechanics audit: **138 PASS / 0 FAIL / 212 INEXACT** (zero wrong-exact).
- Representative fidelity suite: **12 PASS / 0 FAIL**.
- v6 action schema: **331D**, unchanged; v7 state is `live-private-belief-v7` (3208D).
- The mechanics "no wrong-exact" gate criterion is cleared.
- The training gate remains **closed** pending the approval-gated items below.
- Live defaults remain old and intentional: state `live-private-belief-v2`,
  action `legal-action-v3`. This review changes nothing live.

This is a planning document. No training, materialization, checkpoint promotion,
or live-default change is requested or performed by it.

## 1. Data / checkpoint disposition

| Artifact | Disposition |
| --- | --- |
| Existing materialized **v5 datasets** (`diagnostic_300`, `diagnostic_1000_action_rank_v7_v5`) | **Stale for action-impact fidelity.** Their resolved-impact values predate batches 1-5; they encode wrong-exact fixed-damage/multi-hit/secondary/dynamic-type/charge/conditional impacts. Do not use for any fidelity-dependent conclusion or further training. |
| **v7/v5 rank-only checkpoint** (the `diagnostic_1000_action_rank` model) | **Do not use for conclusions.** It was trained on stale v5 action-impact features; its rank metrics reflect pre-repair (often wrong) impact signals. Keep for provenance only; not a baseline for the repaired pipeline. |
| **Tiny v7/v6 one-battle materialization** | **Schema/mechanics smoke artifact only.** It proves the v7/v6 generators run and validate; it is far too small for any learning or evaluation claim. |
| Old v2/v3 live checkpoints / defaults | Unchanged, intentional. Not part of this review. |

Net: nothing currently materialized or trained is a valid baseline for the
fidelity-clean v6 impact path. A fresh, small v7/v6 materialization is the
prerequisite for any further comparison.

## 2. INEXACT handling policy

The audit's 212 INEXACT moves are *not* wrong — they are honestly flagged as
not-exact via `impact_unknown=1` (fail-closed damaging moves), coarse next-state
flags (secondary status/stat/volatile, screen removal), or coarse non-damaging
annotation. The policy must preserve that distinction end to end.

Principles:
- **PASS candidates** may use their exact resolved-impact features as exact.
- **INEXACT candidates must never be treated as exact.** The `impact_unknown` /
  coarse-flag signals already in v6 are the mechanism; they must be carried into
  training, not silently zero-filled or imputed to exact values.

Options considered:
1. Keep INEXACT candidates with `impact_unknown=1` (and the coarse next-state
   flags) and let the model learn from the honest signal.
2. Downweight INEXACT candidates in the loss.
3. Filter INEXACT candidates out of specific diagnostics.
4. Train normally but always report exact-vs-INEXACT breakdowns.

**Recommended default policy:** **(1) + (4).** Train on all legal candidates,
keeping `impact_unknown=1` and the coarse flags intact (the model must see the
real action space, including switches and status moves that are legitimately
INEXACT), **and** report every metric split by exact-impact vs INEXACT. Do **not**
downweight or filter by default — downweighting bakes an untested assumption into
the loss, and filtering distorts the action distribution (many switches/status
moves are INEXACT and must remain rankable). Keep (2) downweighting and (3)
filtering as **diagnostic experiments only**, run after the breakdown in (4) shows
whether INEXACT candidates are actually hurting calibration. Rationale: measure
before intervening; the honest flags already prevent wrong-exact leakage.

## 3. Next dataset step (recommended)

**Recommend a small v7/v6 rematerialization at diagnostic_300 scale first** — not
diagnostic_1000 and not the full 15k. Reasons: it is the smallest set that already
has validated battle-level splits and known baselines, it rebuilds on the
fidelity-clean v6 impact path, and it is cheap enough to iterate. Reuse the
existing frozen `diagnostic_300` battle manifest/splits (210/45/45) so results are
comparable to the pre-repair run; only the features are regenerated.

This is **closed pending approval**. Before scaling to diagnostic_1000 or larger,
the materialization report must prove:

- **Schema/fingerprint validation** — v7 state (3208D) and v6 action (331D) names,
  order, dims, and SHA-256 fingerprints match the frozen schemas exactly.
- **Mechanics audit clean** — the run uses the FAIL=0 impact path; spot-check that
  repaired moves resolve as expected (PASS exact; INEXACT fail-closed/coarse).
- **Action match rate** — replay-choice match rate in line with the prior
  diagnostic_300 (~97-98%); unmatched groups audited and excluded as before.
- **Exact vs INEXACT candidate share** — the fraction of candidate rows with
  `impact_unknown=1` / coarse flags, broken down by move vs switch, so the INEXACT
  load is known before training.
- **Tera / switch candidate counts** — present and sane (Tera candidates generated
  when legal; switch candidates per decision), to confirm the candidate generator
  is intact post-repair.
- **No v5/v6 stale-checkpoint confusion** — new artifact paths, embedded v7/v6
  fingerprints, and the schema-assert guard reject any v5 checkpoint; no accidental
  reuse of stale data.

## 4. Next training step (recommended, gated on §3 passing)

**Only after** the diagnostic_300 v7/v6 materialization report passes, recommend a
**tiny / short action-rank-only training run on the fresh v7/v6 diagnostic_300**
(state-value and action-value disabled, as in the prior rank-only run). The goal
is **plumbing and behavior comparison, not final performance** — confirm the
repaired impact features flow into the ranker and see whether decisions shift
sensibly versus the stale-v5 run, on the same battle splits.

Required metric breakdowns (each reported separately, never just an aggregate):

- **exact-impact candidates** vs **INEXACT candidates** (top-1/top-3/MRR/NLL),
- **Tera** actions,
- **switch** actions,
- **non-damaging / status** actions,
- **dynamic-mechanic moves** (the batches 1-5 repaired families: fixed-damage,
  multi-hit, dynamic accuracy, secondary effects, dynamic type/STAB, charge/delay,
  conditional execution, history power).

Success = the pipeline runs end to end on fresh v7/v6 data, the tiny-subset overfit
check passes, and the exact-vs-INEXACT split is interpretable. It is explicitly
**not** a performance bar and produces **no promotable checkpoint**.

## 5. Remaining non-mechanics blockers (still open)

- **Value-label quality audit not done.** Value learning stays closed; the prior
  diagnostic_300 value head barely beat the constant baseline and needs more
  independent battles plus a label-quality review before any value training.
- **Live loader / defaults remain old** (`live-private-belief-v2` / `legal-action-v3`).
  No live default change is in scope; the opt-in vNext shadow route stays gated.
- **Production / live promotion remains closed.** No checkpoint is approved for
  production use; fidelity-clean features do not by themselves justify promotion.
- **Tera / switch ranker weakness likely persists.** The pre-repair ranker
  under-valued Tera and confused some switch-over-attack cases; the breakdowns in
  §4 must watch for this — mechanics repair does not address it directly.
- **Manual recommendation testing remains display-only.** Any live/private-match
  recommendation testing stays display-only and approval-gated; no auto-submit.

## Readiness decision

**Mechanics fidelity is ready; training is not yet approved.** The wrong-exact gate
is cleared, but every materialized dataset and checkpoint is stale and there is no
valid baseline on the repaired pipeline. The correct next action is a small,
approval-gated **v7/v6 diagnostic_300 rematerialization** whose report proves the
six checks in §3; only then a tiny rank-only training run per §4. Value learning,
live changes, and promotion remain separately blocked. The training gate stays
**closed**.
