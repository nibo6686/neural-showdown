# Public-Evidence Belief Calibration — Design

**Date:** 2026-06-18
**Status:** DESIGN ONLY. Not to be implemented until repo hygiene is committed and the user
approves. Opt-in research mode; live defaults unchanged.
**Scope:** Gen 9 Random Battles singles, seeded research audits.

## Motivation

Three uniform belief particles scored 30% (6–14), identical to one particle and below
one-turn material (45%) and heuristic (50%). The ensemble was mechanically clean (2,136
samples, zero violations/fallbacks). The deficit is **belief quality, not plumbing**: extra
uniformly-sampled particles add variance without adding information. Before increasing
particle count, condition the sampling on the public evidence already visible in the battle.

## What the current fork already does (baseline)

`sim-core/src/belief_fork.ts` already constrains samples to public reveals:

- `matchesReveal()` hard-filters candidate sets on revealed moves, ability, item, and used
  tera; non-matching sets are rejected over up to 64 reseeded attempts.
- Public dynamic state (HP ratio, status, boosts, fainted, volatiles, hazards, weather,
  terrain) is copied from the public view.
- If no matching set is found, it relaxes to an "impossible" set and **counts** it.

What it does **not** do, and what this design adds:

1. It uses **first-match** selection — effectively uniform over matching sets, with no weight.
2. It uses only **reveals** (moves/ability/item/tera) — not observed **damage ranges**,
   **speed order**, **effectiveness outcomes**, or **randbats set-composition** structure.
3. It does not report **candidate count, weight entropy, filtered candidates, or evidence
   reasons** per decision.

## Goal

Replace uniform belief sampling with **weighted, evidence-filtered** candidate sampling, so
that particles concentrate on opponent sets consistent with everything observed publicly —
without ever reading the true hidden opponent state.

## Evidence sources and how each maps to a constraint or weight

| Evidence | Source (public) | Effect |
| --- | --- | --- |
| Revealed moves | protocol `move`/reveal | **Hard filter** (already present) |
| Revealed item / ability / tera | protocol reveals | **Hard filter** (already present) |
| Observed speed order | who-moved-first vs. known move priority | **Filter/weight** on speed tier (EV/nature/item-consistent) |
| Observed damage range | our HP delta from a known attacker vs. this defender | **Weight** sets whose `@smogon/calc` range contains the observed %, **filter** those that cannot |
| Super-effective / resisted / immune | protocol `-supereffective`/`-resisted`/`-immune` | **Filter** sets whose typing (incl. tera) contradicts the observed effectiveness |
| Team-composition / randbats constraints | installed `Teams` generator set tables | **Weight** by randbats set/role plausibility; **filter** impossible move/item/ability combos |
| Public HP / status / boosts | public view | Already copied; used to bound damage-range inference |
| Impossible-set elimination | union of the above | **Filter** (remove zero-probability candidates) |

All evidence is derived from the audited player's **public view and own request only**. No
opponent request, hidden set, or seed-derived ground truth is read in belief mode — this
invariant is unchanged and must be re-verified by the existing public-constraint checker.

## Design

### 1. Candidate enumeration (replace first-match with a candidate set)

For each hidden opponent slot, generate a bounded pool of distinct randbats candidate sets
(reseeded attempts, as today) and **keep all that pass the hard filters** instead of stopping
at the first match. Cap the pool (e.g. ≤ 16 distinct candidates) for determinism and cost.

### 2. Weighting

Each surviving candidate `c` gets weight `w(c) = Π_e f_e(c)`, a product of per-evidence
factors:

- `f_reveal` ∈ {0, 1}: hard filters (already enforced; 0 removes the candidate).
- `f_speed`: 1 if the candidate's speed (with plausible EV/nature/item) is consistent with the
  observed move order; a small penalty (e.g. 0.25) if only consistent under an unlikely spread;
  0 if impossible.
- `f_damage`: 1 if the observed damage % lies within the candidate's `@smogon/calc` range
  (using **exact** stats where our own request provides the attacker), tapering to 0 outside.
- `f_effectiveness`: 0 if the candidate typing/tera contradicts an observed
  supereffective/resisted/immune event, else 1.
- `f_randbats`: prior from set/role frequency in the installed generator (uniform if
  unavailable, so this never silently injects hidden data).

Normalize weights over the surviving pool. Record **weight entropy**
`H = −Σ p log p` (low entropy = confident belief; high = ambiguous).

### 3. Particle draw

Draw the `N` particles (N ∈ {1, 3, 5}, default 3) from the **weighted** candidate distribution
deterministically: sort candidates by weight, then pick by deterministic stratified sampling
keyed on the existing per-particle seed offsets. Particle 0 takes the **MAP** (highest-weight)
candidate so the single-particle mode degrades to "most plausible set," not a random one.

### 4. Aggregation (weighted mean)

Replace the uniform particle mean with a **weighted mean** over particles, using each
particle's draw weight. Keep reporting population std, worst, best, and the per-particle
selected actions and disagreement, as today. Tie-break by lower action index (unchanged).

### 5. Reporting (new per-decision diagnostics)

Add to the belief metadata, per hidden slot and per decision:

- candidate pool size and **surviving** (post-filter) count;
- number of **filtered** candidates and the dominant filter reason
  (reveal / speed / damage / effectiveness / impossible);
- normalized **weight entropy** and the MAP weight;
- the evidence factors that were *active* (i.e. actually narrowed the pool);
- existing counters: belief errors, public-info violations, branches, leaves, caps, timeouts,
  damage fallbacks (must remain zero).

## Modes to compare (validation)

Run the existing paired audit harness, same seeds, adding one new agent:

| Mode | Already exists? |
| --- | --- |
| Exact two-ply (upper bound) | yes |
| One-particle **unweighted** belief | yes |
| Three-particle **unweighted** belief | yes |
| **Three-particle evidence-weighted belief** | **NEW** |
| One-turn material | yes |
| Heuristic | yes |

**Success criteria:**
- Zero public-information violations, belief errors, damage fallbacks, branch errors, caps,
  timeouts (same gate as before; a 5-battle smoke must be clean before the full run).
- Evidence-weighted belief **beats** unweighted belief (currently 30%) and ideally approaches
  one-turn material (45%) on the paired audit. If it does not beat unweighted belief, the
  finding is reported as negative and belief sampling is not promoted.
- Determinism: identical results under fixed seeds across two runs.

## Cost expectations

Candidate enumeration adds bounded `@smogon/calc` calls for damage-range checks per observed
hit. Damage checks reuse the already-clean exact-stat calc path (no heuristic fallback). Keep
the existing 3/3/2 action caps and the 8-second per-decision deadline; if the deadline is
exhausted, the particle is counted as an error with no hidden-state fallback.

## Scope limits (hard)

- No change to live defaults, weights, or checkpoints.
- No production training; no checkpoint overwrites.
- No team-building, no tournament data, no LLM move selection, no doubles.
- **Never** read the true hidden opponent state, opponent request, or seed-derived ground
  truth in belief/evidence mode. The public-constraint checker remains the gate.
- Do not remove exact-seeded mode or single-particle mode; evidence weighting is a new opt-in
  agent alongside them.

## State-eval dependency (added 2026-06-18 after the live-eval calibration audit)

Before this belief work proceeds, a separate audit calibrated the live state scorers
(`artifacts/live_eval_calibration/`). Its findings change which scorer this design
should rely on at branch leaves and for any value term.

**Which scorer to use while calibrating beliefs:** **material/HP**, unchanged. The
calibration audit (1406 seeded states) ranked scorers for leaf/action-impact use:
material/HP is perspective-exact, never saturates (0.3% rails), and gives the best
one-step action-impact (45% branch winrate). The bounded `live_sim_value` head is the
best *current-state estimator* (Brier 0.066, AUC 0.987) but selects worse actions
(15%) because value lookahead turns passive. The old `live_private_value` head — the
one `/evaluate` shipped — is **collapsed** (sign accuracy 0.558, positive for wins and
losses alike, 73.7% saturated) and must **not** be used as a belief leaf scorer or a
weight signal.

**Why current-state calibration affects action impact:** belief search selects the
action whose sampled-opponent resulting states score best. If the leaf scorer cannot
rank states (the collapsed head), the per-action impact deltas degrade to noise
regardless of how good the belief sampling is. A clean leaf scorer is a prerequisite
for the belief weighting to show any signal — otherwise a belief improvement would be
masked by leaf-scorer noise. Hence material/HP at the leaves during this work.

**Should belief sample weighting use material/HP, calibrated value, or both:**
weight the **belief candidates** with the public-evidence factors in this design
(reveal/damage/speed/effectiveness/randbats priors), and score **leaves** with
material/HP. Do **not** fold the value model into the candidate weights yet — the
collapsed default would corrupt them, and even the calibrated bounded head adds a
passive bias. Keep value scoring as an optional, separately-reported diagnostic term
(`NEURAL_BRANCH_SCORER=live_sim_value`), never as the belief weight.

**Which uncertainty/candidate-weight signals to expose:** in addition to the
per-decision belief diagnostics already specified (candidate pool size, surviving
count, filtered count + dominant reason, weight entropy, MAP weight, active evidence
factors), expose the **leaf-scorer identity** and, when the diagnostic value term is
on, a **value-vs-material agreement** flag per action. This lets the belief audit
separate "belief disagreement" from "scorer disagreement" — the two were conflated in
the 3-particle run.

## Open questions for implementation (resolve before coding)

1. **Damage-range inversion fidelity:** how tightly can observed % narrow the spread given
   randbats' limited spread space? May need a coarse {min/avg/max-roll} bracket rather than a
   continuous likelihood.
2. **Speed-tier inference under items/abilities** (Choice Scarf, paralysis, Tailwind): treat as
   a soft penalty, not a hard filter, to avoid over-pruning.
3. **Where weighting lives:** compute candidate weights in `belief_fork.ts` (TS, near the
   sampler and `@smogon/calc`) and pass weights up, vs. compute in Python. Recommendation: TS,
   to keep evidence next to the sampler and the pinned calc.
