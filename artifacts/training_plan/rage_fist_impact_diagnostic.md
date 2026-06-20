# Rage Fist Impact Diagnostic

## Scope and State Reconstruction

The exact Annihilape-versus-Cresselia decision was not present in the three
sanitized live captures; those contain only Turn 1 Slowking/Munkidori states.
Therefore the exact HP, item, boosts, stats, Tera state, and four selected moves
from the manual battle cannot be reconstructed.

The closest controlled Gen 9 random-battle fixture was used:

- level 76 Annihilape, Defiant, Fighting/Ghost, no boosts;
- moves: Rage Fist, Gunk Shot, Drain Punch, Bulk Up;
- level 80 Cresselia, Levitate, Psychic, no boosts, full HP;
- no item assumptions and calculator-inferred stats.

The diagnostic called the existing `resolve_action_impact` and
`build_action_feature_vector_v5` functions directly. A separate Smogon-calc
comparison overrode Rage Fist to 100 BP (one prior hit) and 150 BP (two prior
hits) to show the expected dynamic result. No code or model was changed.

## Damage Results

| Action | Power represented | Accuracy | Average damage | Range |
| --- | ---: | ---: | ---: | ---: |
| Rage Fist, current pipeline | 50 BP | 100% | **29.45%** | 27.45–32.03% |
| Rage Fist, correct after one hit | 100 BP | 100% | **58.29%** | 53.59–63.40% |
| Rage Fist, correct after two hits | 150 BP | 100% | **87.58%** | 80.39–94.77% |
| Gunk Shot | 120 BP | 80% | **23.43%** | 21.57–25.49% |
| Drain Punch | 75 BP | 100% | **10.91%** | 9.80–11.76% |
| Bulk Up | status | 100% | 0% immediate | non-damaging |

These percentages are controlled-fixture values, not a reconstruction of the
exact manual battle.

## v5 Feature Comparison

Key current v5 fields:

| Feature | Rage Fist | Gunk Shot |
| --- | ---: | ---: |
| `base_power_norm` | 0.20 (50 BP) | 0.48 (120 BP) |
| `accuracy_norm` / `impact_hit_chance` | 1.00 | 0.80 |
| `impact_expected_damage_fraction` | 0.2945 | 0.2343 |
| `impact_min_damage_fraction` | 0.2745 | 0.2157 |
| `impact_max_damage_fraction` | 0.3203 | 0.2549 |
| `impact_super_effective` | 1 | 0 |
| `impact_type_effectiveness_norm` | 0.50 (2×) | 0.25 (1×) |
| `impact_stab` | 1 | 0 |
| `impact_method_smogon_calc` | 1 | 1 |
| `effect_recoil` | 0 | 0 |
| `effect_has_drawback` | 0 | 0 |

Move identity/type/category fields also distinguish the actions. Accuracy is
represented sensibly: Gunk Shot's 80% hit chance is explicit, while Rage Fist is
100%. Neither move has recoil, self-stat loss, recharge, or locking, so the
generic drawback flags are correctly false. Gunk Shot's poison secondary is not
an explicit resolved-impact field; it can only be learned indirectly from move
identity/metadata features.

`impact_expected_damage_fraction` is damage conditional on a hit, not
accuracy-weighted expected damage. The separate hit-chance field allows the
ranker to account for miss risk.

## Dynamic-Power Finding

`resolve_action_impact` does **not** account for Rage Fist's accumulated
times-hit state:

- move metadata and `@smogon/calc` expose Rage Fist at static 50 BP;
- Pokémon Showdown's battle engine uses
  `50 + 50 * pokemon.timesAttacked` (capped at 350);
- the live damage request contains no `timesAttacked` or dynamic base-power
  override;
- changing controlled tactical `damage_events_recent` from 0 to 1 changed
  neither the 318D v5 action vector nor the v7 tactical-state vector;
- the damage-event count currently affects only switch-action context, not Rage
  Fist move impact.

Therefore Rage Fist is **not represented as stronger after Annihilape has been
hit**. Its resolved damage remains the 50 BP value instead of doubling to 100 BP
after the first hit.

## Failure Attribution

This is a confirmed **feature/impact bug**, but the manual Gunk Shot
recommendation is not purely explained by that bug.

Even with the bug, the controlled current features estimate Rage Fist at 29.45%
and Gunk Shot at 23.43%, while also favoring Rage Fist on accuracy, STAB, and
type effectiveness. A ranker that used these fields tactically should prefer
Rage Fist in this simplified position. The observed Gunk Shot choice therefore
also indicates a **ranker imitation/state-interaction weakness** (subject to the
missing exact state). Correct dynamic power would make the evidence much
stronger—58.29% after one hit—but cannot by itself prove what the ranker would
select.

Conclusion: **both** are involved:

1. definite Rage Fist dynamic-power representation/resolution bug;
2. likely ranker-learning weakness, because the existing bugged features already
   favor Rage Fist over Gunk Shot in the controlled matchup.

## Gate Decision and Next Action

Training should **not** proceed. Scaling the existing feature pipeline would
teach from states where Rage Fist's central mechanic is absent.

Recommended next action: design the smallest schema-aware correction that
tracks per-active-Pokémon `timesAttacked` from protocol state and passes the
result into Rage Fist base-power resolution. Add a focused before/after-hit
impact test, then regenerate only a tiny diagnostic sample to verify feature
semantics before considering any dataset rebuild or training. The gate remains
closed.
