# Rage Fist `times_attacked` Fix Report

## Change

The shared live/offline resolved-impact path now preserves Rage Fist's dynamic
base power:

1. `TacticalStateTracker` counts successful direct attack-damage events per
   species and retains the count across switches.
2. A `|start` marker establishes complete history. Without complete history,
   the observed count is treated as a lower bound and `times_attacked_known`
   remains false.
3. `damage_engine` passes a known count as `attacker.times_attacked`.
4. sim-core overrides Rage Fist base power to
   `min(350, 50 + 50 * times_attacked)` before calling `@smogon/calc`.
5. Rage Fist with an unknown count fails closed with
   `rage_fist_times_attacked_unknown` rather than silently using exact zero.

Residual damage carrying a `[from]` tag is not counted as a successful attack.
Other moves ignore `times_attacked`.

Both consumers use the fix:

- live vNext shadow calls shared `resolve_action_impact`;
- offline vNext materialization calls the same function with tactical state
  reconstructed from the replay prefix.

No browser behavior, live default, training path, or checkpoint was changed.

## Controlled Damage Results

Level 76 Annihilape versus level 80 Cresselia:

| Move/state | Average | Range |
| --- | ---: | ---: |
| Rage Fist, 0 hits (50 BP) | **29.4526%** | 27.4510–32.0261% |
| Rage Fist, 1 hit (100 BP) | **58.2925%** | 53.5948–63.3987% |
| Rage Fist, 2 hits (150 BP) | **87.5817%** | 80.3922–94.7712% |
| Gunk Shot, 0 or 2 hits | **23.4273%** | 21.5686–25.4902% |
| Drain Punch, 0 or 2 hits | **10.9069%** | 9.8039–11.7647% |

Gunk Shot and Drain Punch are unchanged by the counter.

## Schema Discipline

- Action schema: still `legal-action-v5`.
- Dimension: still 318.
- Feature names/order: unchanged.
- New feature: none.
- Corrected values: existing resolved-impact damage, KO, and next-HP-delta
  fields for Rage Fist when the counter is known.

Previously materialized v5 datasets and checkpoints are **mechanically stale for
Rage Fist impact**. They contain/trained on static-50-BP Rage Fist values. This
task did not rematerialize data or retrain/promote a checkpoint.

## Focused Tests

Passed:

```text
python -m unittest trainer.tests.test_action_features_v5 trainer.tests.test_tactical_state
32 tests OK

npm run build
node --test dist/tests/damage_calc.test.js
7 tests passed
```

Coverage includes 0/1/2-hit Rage Fist scaling, unchanged Gunk Shot/non-Rage-Fist
damage, unknown-counter fail-closed behavior, direct-hit protocol tracking, and
residual-damage exclusion.

## Decision

Training remains blocked. The Rage Fist runtime/materialization mechanic is now
correct for newly generated impacts, but the current dataset/checkpoint is stale
for that move and the broader dynamic-dependency audit contains additional known
or unverified mechanics.

Recommended next action: add focused counterfactual verification for the known
broken Last Respects and boost-dependent move plumbing before deciding whether a
small diagnostic rematerialization is warranted. Keep the gate closed.
