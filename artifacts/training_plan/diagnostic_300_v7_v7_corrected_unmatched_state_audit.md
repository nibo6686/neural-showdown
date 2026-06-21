# diagnostic_300 v7/v7 Corrected Unmatched-State Audit

> **Superseded (materialization quality):** the fresh
> `diagnostic_300_v7_v7_post_illusion` rematerialization reduces these 519
> residuals to 15 (99.94% match). See
> `diagnostic_300_v7_v7_post_illusion_dataset_quality_audit.md`. This document is
> retained as the pre-fix residual analysis.

## Scope

This is a read-only audit of the 519 residual action-rank unmatched rows in:

`artifacts/training_plan/datasets/diagnostic_300_v7_v7_corrected`

No training, rematerialization, checkpoint promotion, live-default change,
live-bot change, schema change, push, or `legal-action-v8` work occurred.

Post-checkpoint source fix note:
`missing_candidate_reconstruction_fix_report.md` records the targeted
reconstruction fix made after checkpoint
`96e56696798dab0b5c884e3d05bcb075cf262eb7`. A lightweight replay-prefix audit
over these same 519 rows initially matched 485 and left 34 unmatched. Follow-up
triage in `residual_34_unmatched_case_triage_report.md` fixed 26 more
source-level reconstruction bugs; the same lightweight recomputation now
naturally matches 511 and leaves 8 unmatched.
The materialized `diagnostic_300_v7_v7_corrected` dataset itself was not
rematerialized, so this document remains the authoritative pre-fix artifact
audit.

Audit helper:

```powershell
& $py scripts\audit_v7_v7_unmatched_states.py `
  artifacts\training_plan\datasets\diagnostic_300_v7_v7_corrected --top 20
```

The helper treats `decision_skip_audit.jsonl` as authoritative for residual
unmatched labels. `materialization_report.json["unmatched_action_audit"]`
also contains legacy rows that were fixed by exact pre-action reconstruction
and should not be counted as residual label gaps.

## Summary

- Decision states: 25,235
- Matched labels: 24,716
- Residual unmatched labels: 519
- Match rate: 97.94%
- Exact parsed action already present in legal candidates: 0 / 519

All residual rows are missing-candidate cases, not candidate-label-index
mismatches. The chosen action is not present in the reconstructed pre-action
candidate list.

## Split Distribution

| Split | Residual unmatched |
| --- | ---: |
| train | 516 |
| validation | 1 |
| test | 2 |

Validation/test are almost clean. The residual problem is overwhelmingly
train-split concentrated.

## Action and Detail Distribution

| Category | Count |
| --- | ---: |
| `move_missing_from_reconstructed_active_moves` | 486 |
| `switch_target_missing_from_pre_action_legal_roster` | 33 |

| Parsed action type | Count |
| --- | ---: |
| move | 482 |
| move_tera | 4 |
| switch | 33 |

| Turn bucket | Count |
| --- | ---: |
| early turns 1-10 | 19 |
| mid turns 11-40 | 108 |
| late turns 41+ | 392 |

No residual row has an empty candidate list. Candidate-list shape:

| Detail / candidate shape | Count |
| --- | ---: |
| move missing, move + switch candidates | 333 |
| move missing, move-only candidates | 98 |
| move missing, switch-only candidates | 55 |
| switch target missing, move + switch candidates | 29 |
| switch target missing, move-only candidates | 4 |

## Top Replay Contributors

| Replay | Residual unmatched |
| --- | ---: |
| `gen9randombattle-2592785310` | 41 |
| `gen9randombattle-2588573746` | 32 |
| `gen9randombattle-2589422242` | 32 |
| `gen9randombattle-2589906015` | 32 |
| `gen9randombattle-2591454472` | 32 |
| `gen9randombattle-2592676390` | 32 |
| `gen9randombattle-2590172478` | 31 |
| `gen9randombattle-2589811158` | 24 |
| `gen9randombattle-2593371445` | 21 |
| `gen9randombattle-2589743938` | 20 |
| `gen9randombattle-2590019196` | 18 |
| `gen9randombattle-2591230892` | 16 |
| `gen9randombattle-2591392885` | 16 |
| `gen9randombattle-2592069985` | 16 |
| `gen9randombattle-2592381633` | 16 |
| `gen9randombattle-2593448956` | 16 |
| `gen9randombattle-2593778713` | 16 |
| `gen9randombattle-2594262295` | 16 |

The long tail is not random noise: several replays have persistent repeated
missing moves for the same active Pokemon.

## Replacement Replay

`gen9randombattle-2591433931` does **not** contribute 21 residual unmatched
entries.

It has 21 rows in the broader legacy `unmatched_action_audit` stream:

- 19 rows were fixed by exact pre-action event-prefix reconstruction.
- 2 rows are intentional initial-deployment non-decisions.
- 0 rows remain in `decision_skip_audit.jsonl` as
  `chosen_action_unmatched_for_action_rank`.

The earlier "21 unmatched" note was therefore an audit-stream interpretation
error, not a corrected dataset quality defect.

## Root Cause Categories

### 1. Missing reconstructed active moves

486 / 519 residual rows are moves that are not present in the reconstructed
active move list. The dominant examples are repeated missing status/support
moves:

| Species / move | Count |
| --- | ---: |
| Chansey / Thunder Wave | 95 |
| Gholdengo / Thunder Wave | 64 |
| Sylveon / Wish | 48 |
| Blissey / Thunder Wave | 32 |
| Dondozo / Wave Crash | 20 |
| Scream Tail / Wish | 18 |
| Vaporeon / Wish | 17 |
| Glaceon / Freeze-Dry | 16 |
| Quagsire / Toxic | 16 |
| Trevenant / Toxic | 16 |
| Jirachi / Wish | 16 |
| Gliscor / Toxic | 16 |
| Arboliva / Substitute | 16 |
| Umbreon / Wish | 16 |

This points to remaining move-set reconstruction incompleteness rather than
label matcher drift. In 431 of the 486 rows, the materializer had some legal
move candidates for the active Pokemon, but the chosen move was absent. In 55
rows, only switch candidates were available even though the replay command was
a move, which looks like a pre-action forced-replacement/active-state timing
disagreement.

### 2. Struggle / PP exhaustion

29 residual rows are `Struggle`. These are plausibly expected until PP/choice
exhaustion and forced-Struggle legality are modeled in the replay legal-action
builder. They are explicit skips and do not inject wrong positives.

### 3. Switch target missing from reconstructed legal roster

33 rows are switches whose target is not present in the reconstructed
pre-action legal roster. Examples include:

- Terapagos-Terastal after drag / Flip Turn while candidates include base
  Terapagos;
- Palafin-Hero while candidates include Palafin;
- Ogerpon-Wellspring-Tera;
- Houndstone, Glalie, Miraidon, Whimsicott, and scattered late-roster targets.

This category is consistent with remaining form/alias and roster-continuity
gaps. It is small but real. Of the 33 rows, 30 are train, 1 validation, and
2 test.

### 4. Pivot, phazing, Tera, Illusion markers

Residual marker counts:

- `[from]` switch rows: 8
- named pivot rows (`Flip Turn`, `U-turn`, `Volt Switch`, `Chilly Reception`):
  4
- `drag` rows: 1
- raw Tera markers: 5
- Illusion/Zoroark text markers: 1

These mechanics exist in the residual set but do not dominate it. The dominant
failure is still reconstructed move/roster candidate absence.

## Representative Examples

Move command while only switches are legal:

```text
replay=gen9randombattle-2587967313 turn=31 side=p2
raw=|move|p2a: Terapagos|Earth Power|p1a: Piloswine
candidates=switch Vaporeon, Palossand, Regice, Terapagos
```

Repeated missing support move:

```text
replay=gen9randombattle-2588573746 turn=32 side=p2
raw=|move|p2a: Chansey|Thunder Wave|p1a: Misdreavus
candidates=Heal Bell, Seismic Toss, Soft-Boiled, Struggle, Gastrodon-East switch
```

Switch target form/alias issue:

```text
replay=gen9randombattle-2587967313 turn=43 side=p2
raw=|switch|p2a: Terapagos|Terapagos-Terastal, L77, F|205/273|[from] Flip Turn
candidates=Flip Turn, Protect, Scald, Wish, Palossand, Regice, Terapagos
```

## Own-Side Future-Public-Reveal Assumption

The documented own-side future-public-reveal assumption remains a training-time
replay reconstruction approximation. It is not evidence of opponent hidden-truth
leakage in this audit:

- it applies to own-side reconstruction, where the player would know their own
  legal request/team facts;
- it does not justify reading unrevealed opponent ability/item/team truth;
- it is still a modeling debt because the replay lacks timestamped private
  request payloads.

Conclusion: not a no-leakage blocker for v7/v7 smoke plumbing, but still a
known caveat for interpreting replay-training quality.

## Gate Decision

The remaining 519 rows are not random benign noise. They are understood,
explicitly excluded missing-candidate cases caused mainly by move-list
reconstruction incompleteness plus smaller roster/form alias gaps.

Because 516 / 519 are train-only and validation/test have only 3 residual rows,
the corrected dataset is acceptable for a **tiny smoke training plumbing run**
if explicitly approved and described as a pipeline/overfit sanity check only.
It is not yet acceptable as a durable quality baseline or performance claim.

Recommended next step:

1. Run an explicitly approved tiny smoke training pass only to validate the
   training path on corrected v7/v7.
2. Before any larger or durable training, fix the residual move-list
   reconstruction gaps (`Thunder Wave`, `Wish`, `Toxic`, Struggle/PP handling)
   and roster/form aliases, then rematerialize with explicit approval.
3. Do not start `legal-action-v8` before this residual reconstruction work if
   the goal is cleaner v7 data quality; v8 threat features would not repair
   missing labels.
