# Exact-State Branch Scorer Design (Part D)

Audit date: 2026-06-18
Scope: seeded Gen 9 singles, one-turn branch evaluation.

## Motivation

The live-private value model collapses on sim-core branch states (see
`value_model_diagnostics.md`): it returns ~+1 for both sides. The faithful
exact-state scorer (real post-step HP, not approximate damage) already reached
45% vs the heuristic, so the trustworthy path is to score the real stepped state
directly. This design hardens that scorer with light, explainable tie-breakers.

## Scorers available (`neural.one_turn_branch`)

- `make_material_score_fn()` — original baseline: `(own_hp - opp_hp) / 6`, clamped
  to `[-1,1]`. Unrevealed opponent bench counted as alive at full HP.
- `make_state_score_fn()` — improved scorer (new). Same HP backbone plus light
  terms; clamped to `[-1,1]`.
- `make_value_score_fn()` — live-private value model, kept only as a diagnostic.

The audit picks one via `NEURAL_BRANCH_SCORER` ∈ {`state` (default), `material`,
`value`}.

## Improved formula

`score = clamp(-1, 1,  Σ w_k · term_k)` with:

| Term | Definition | Weight |
| --- | --- | ---: |
| `hp` | `(own_alive_hp − opp_alive_hp) / 6` | 1.00 |
| `alive` | `(own_alive_count − opp_alive_count) / 6` | 0.30 |
| `active_hp` | `own_active_hp − opp_active_hp` | 0.25 |
| `status` | `(opp_status_penalty − own_status_penalty) / 6` | 0.08 |
| `boost` | `boost_sum(own_active) − boost_sum(opp_active)` | 0.03 |
| `hazard` | `hazard_cost(opp_side) − hazard_cost(own_side)` | 0.05 |

- Status weights: slp/frz 1.0, tox 0.7, par 0.6, brn 0.5, psn 0.4.
- Hazard weights: stealthrock 1.0, spikes 0.5, toxicspikes 0.5, stickyweb 0.4
  (multiplied by the side-condition layer count).
- Boost sum: net of atk/def/spa/spd/spe stages, each clamped to ±6.
- Unrevealed opponent bench counted as alive at full HP via the public team size.

HP differential dominates; the rest only break ties between similar branches.
Terminal branches bypass the scorer entirely and use the real outcome (±1/0) in
`evaluate_action_branches`.

## Properties

- **Deterministic, cheap, explainable.** Pure arithmetic over the post-step view;
  no model, no RNG, no protocol re-parsing.
- **No hidden information in the scorer.** It reads only the audited player's own
  legal view: own private team, publicly revealed opponent, public team size,
  public field/hazards. (The fork *simulation* may use exact opponent data in
  seeded research mode; that is a property of the substrate, not the scorer — see
  `one_turn_branch_report.md`.)
- **No strategic rules / no per-Pokemon or per-move hardcoding.** Only generic
  HP/count/status/boost/hazard signals.
- **Perspective-correct.** Regression tests assert the score flips sign between
  p1 and p2 on a mirrored state and never rates both sides as winning.

## Deliberately excluded

Speed/turn-order proxies, type-matchup tables, move-specific logic, and
opponent-set inference were left out to keep the scorer faithful to the real
stepped state and avoid reintroducing approximate-damage-style guessing.
