# Feature vNext Slice 5 — Moves / Actions Counterfactual Report

**Status:** diagnostic-only
**State version:** `live-private-belief-v7` (3208D)
**Action version:** `legal-action-v4` (269D)
**Generator:** `trainer/src/neural/moves_actions_counterfactual_diagnostic.py`
**Tests:** `trainer/tests/test_live_private_features_v7.py`,
`trainer/tests/test_action_features_v4.py`,
`trainer/tests/test_moves_actions_counterfactual.py`

Each scenario mutates exactly one controlled variable and reports how many v7/v4
fields change. Non-empty = the representation *sees* the variable. These are
representation tests, not tactical rules. States are synthetic (built through the
real live serving path) on purpose.

## State counterfactuals (`live-private-belief-v7`)

| # | Counterfactual | Fields changed | Result |
|---|---|---|---|
| 1 | own move slot A vs B (Flamethrower↔Air Slash order) | 4 | PASS |
| 2 | opponent revealed move vs unknown | 12 | PASS |
| 3 | own PP known vs unknown | 2 | PASS |
| 4 | disabled move vs available | 9 | PASS |
| 5 | Encore-locked vs no Encore | 35 | PASS |
| 6 | Choice-lock (single selectable) vs no lock | 11 | PASS |
| 7 | recharge vs no recharge | 42 | PASS |
| 8 | Taunt active vs inactive | 4 | PASS |
| 9 | two-turn lock (Outrage) vs none | 43 | PASS |
| 10 | perspective flip (p1↔p2) remaps own/opponent move fields | 68 | PASS |

Notes:

- (4) `own_active_move_slot_1_disabled` flips 0→1.
- (5) `own_encore_lock_state_active` and `own_single_move_lock_state_active` flip.
- (6) `own_choice_lock_inferred` flips (one selectable move, no Encore volatile).
- (7) `own_recharge_state_active` + `own_must_recharge` flip; two-turn stays 0.
- (9) `own_two_turn_lock_state_active` flips; recharge stays 0.
- (10) own/opponent `*_move_slot_*_id_hash_*` swap, confirming
  perspective-correct own↔opponent mapping.

## Action counterfactuals (`legal-action-v4`)

| # | Counterfactual | Evidence | Result |
|---|---|---|---|
| 1 | Draco Meteor vs Psyshock self SpA | `self_stat_delta_spa` −1.0 vs 0.0 | PASS |
| 2 | Curse vs Bulk Up | `self_stat_delta_spe` −0.5 vs 0.0; atk/def equal (+0.5) | PASS |
| 3 | damaging vs status (Flamethrower vs Will-O-Wisp) | 11 fields, `class_damage`↔`class_status` | PASS |
| 4 | Tera move vs normal move | 3 fields, `cmd_tera_move`↔`cmd_move` | PASS |
| 5 | switch vs move | 27 fields, `cmd_switch`/`switch_target_*` | PASS |
| 6 | disabled action vs enabled | 4 fields, `lock_disabled` | PASS |
| 7 | priority vs non-priority (Extreme Speed vs Tackle) | `effect_priority_norm` 0.64 vs 0.50 | PASS |
| 8 | recoil vs no recoil (Flare Blitz vs Fire Punch) | `effect_recoil` 1.0 vs 0.0 | PASS |

## Conclusion

All 10 required state distinctions and all 8 required action distinctions are
represented. Draco Meteor's self Special-Attack drop and the Curse-vs-Bulk-Up
Speed trade-off — both invisible to `legal-action-v3` — are now explicit fields.
No live default, checkpoint, or dataset changed.
