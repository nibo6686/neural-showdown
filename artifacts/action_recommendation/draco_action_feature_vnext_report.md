# Draco / Action-Feature vNext Report (Slice 5)

**Status:** diagnostic-only
**State version:** `live-private-belief-v7` (3208D)
**Action version:** `legal-action-v4` (269D)

Follow-up to `draco_vs_psyshock_diagnostic.md` and
`action_impact_audit_report.md`. Those reports root-caused the disputed
Draco Meteor > Psyshock preference: the action schema was **side-effect blind**
— it never encoded that Draco Meteor lowers the user's Special Attack by two
stages, so a learner could not see the drawback. This report confirms the
representation gap is now closed (before training).

## Did the old action schema lack the drawback? — Yes

`legal-action-v3` (165D) has no self-stat field. The only `self`/`drop`/`boost`
column is `target_self` (a *targeting* flag). Draco Meteor and Psyshock are
therefore indistinguishable on self-cost grounds in v3:

| Field | Draco Meteor (v3) | Psyshock (v3) |
|---|---|---|
| self stat drop | (no such field) | (no such field) |
| `target_self` | 0 | 0 |

## Is the drawback now represented? — Yes

`legal-action-v4` (269D) adds explicit per-stat deltas and drawback effects.
The magnitude is preserved exactly, not flattened to a flag. Normalization is
`normalized_delta = clip(raw_stage_delta / 2, -1, 1)`, so a two-stage drop is
−1.0 and a one-stage drop would be −0.5 (distinct).

| Field (v4) | Draco Meteor (raw → norm) | Psyshock |
|---|---|---|
| `self_stat_delta_spa` | −2 → **−1.0** (two stages) | 0 → 0.0 |
| `self_stat_delta_{atk,def,spd,spe,acc,eva}` | 0 → 0.0 (unchanged) | 0 → 0.0 |
| `opponent_stat_delta_*` | 0 → 0.0 | 0 → 0.0 |
| `self_has_stat_drop` | 1.0 | 0.0 |
| `effect_has_drawback` | 1.0 | 0.0 |

The two moves differ in 16 v4 fields, including the self-SpA-drop column.
Parser-level proof: `move_stat_deltas("Draco Meteor")["self"] == {"spa": -2}`,
and the vector writes **only** `self_stat_delta_spa` (= −1.0); every other self/
opponent stat-delta field stays 0. Full 7-point proof (raw parser output, single
field written, two-stage magnitude, `has_stat_drop`, no other nonzero field, v3
unchanged, v4 prefix-preserved) is asserted in
`trainer/tests/test_action_stat_delta_fidelity.py`.

Related exact-fidelity examples (raw → normalized):

| Move | Raw self delta | Normalized |
|---|---|---|
| Overheat / Leaf Storm | `spa: -2` | `spa: -1.0` |
| Close Combat | `def: -1, spd: -1` | `def: -0.5, spd: -0.5` |
| Superpower | `atk: -1, def: -1` | `atk: -0.5, def: -0.5` |
| Curse (non-Ghost) | `atk: +1, def: +1, spe: -1` | `+0.5, +0.5, -0.5` |
| Bulk Up | `atk: +1, def: +1` | `+0.5, +0.5` |

`legal-action-v3` has no self stat-delta field and is the byte-identical prefix
of v4, so any future `legal-action-v5` extending v4 preserves this exact
information by construction.

## Curse vs Bulk Up (mixed boosts preserved)

The same parser distinguishes mixed self boosts/drops, which v3 also collapsed:

| Field (v4) | Curse | Bulk Up |
|---|---|---|
| `self_stat_delta_spe` | **−0.5** | 0.0 |
| `self_stat_delta_atk` | +0.5 | +0.5 |
| `self_stat_delta_def` | +0.5 | +0.5 |

Speed differs; Attack/Defense are preserved on both — exactly the distinction a
learner needs to value Bulk Up's clean setup over Curse's Speed cost.

## v7 state move/constraint fields (companion context)

The `live-private-belief-v7` state vector now also exposes, per active mon:
own/opponent per-slot move identity, exact own PP vs unknown opponent PP,
per-move disabled, and recharge / two-turn / Encore / inferred-Choice-lock /
Taunt constraints (see
`feature_vnext_slice5_moves_actions_counterfactual_report.md`). Together the v7
state side and the v4 action side give a future ranker both the move context and
the move consequence.

## Scope

This proves *representation*, not behavior. No hardcoded "avoid Draco Meteor"
rule was added; the live recommender's selection logic, defaults, datasets, and
checkpoints are unchanged. Whether a retrained ranker actually prefers Psyshock
when the SpA drop is costly is a **post-retraining** question, still blocked.
