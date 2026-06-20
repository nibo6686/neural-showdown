# diagnostic_300 Action-Rank Offline Evaluation

## Purpose and Scope

Evaluate the existing first multitask diagnostic checkpoint's **action-rank
head** offline against simple decision heuristics, to decide whether it learns
useful Pokémon decision preferences beyond trivial damage/type priors and is
worth scaling to a larger action-rank diagnostic dataset.

No model was trained, tuned, promoted, or modified. Live defaults untouched.
Analysis used the **validation split only**; the test split was not newly
touched (first-report test numbers are referenced for context only).

## Checkpoint Evaluated

- `artifacts/diagnostic_training/diagnostic_300_v7_v5_first/model.best.pt`
- Multitask first run, epoch 8, `shared_state_action_diagnostic_mlp` (~218.8k params)
- state `live-private-belief-v7` (3208D), action `legal-action-v5` (318D)

## Dataset / Split

- `artifacts/training_plan/datasets/diagnostic_300_v7_v5/diagnostic_300_v7_v5.npz`
- Split: **validation**, 2,254 matched action-rank groups (exactly one replay
  positive per group). Train/test groups were not used here.

## Schema / Fingerprint Validation

`validate_vnext_checkpoint_metadata` against the dataset's computed fingerprints:

- state/action schema versions: **match** (`live-private-belief-v7` / `legal-action-v5`)
- state/action dimensions: **match** (3208 / 318)
- fingerprints: **`missing_legacy`** — this checkpoint predates the fingerprint
  guardrail, so no `*_feature_names_sha256` is embedded. Status `PASS` on
  name/dim; fingerprints flagged as legacy-incomplete (not silently equivalent),
  exactly as designed. Future checkpoints will carry fingerprints.

## Command

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
D:\Anaconda\envs\neuralgpu\python.exe -m neural.evaluate_vnext_action_rank `
  --config .\configs\diagnostic_300_v7_v5.first.windows.json `
  --checkpoint .\artifacts\diagnostic_training\diagnostic_300_v7_v5_first\model.best.pt `
  --split validation
```

## Model vs Baselines (validation, 2,254 groups)

| Method | top-1 | top-3 | MRR |
| --- | ---: | ---: | ---: |
| **Action-rank model** | **0.4556** | **0.8656** | **0.6643** |
| type_prior_move (prefer regular move) | 0.3882 | 0.7276 | 0.5850 |
| max_expected_damage (= max HP delta) | 0.3909 | 0.6779 | 0.5595 |
| best_damage_move_no_switch | 0.3909 | 0.6779 | 0.5595 |
| max_ko_chance | 0.3438 | 0.6619 | 0.5274 |
| max_base_power | 0.3403 | 0.6642 | 0.5264 |
| max_accuracy_damaging | 0.3354 | 0.6619 | 0.5227 |
| random_move | 0.2070 | 0.5152 | — |
| random_legal | 0.1678 | 0.4714 | 0.3890 |

Model NLL (grouped softmax CE): **1.2785**.

The model beats every baseline on all metrics: top-1 +6.5 pts over the best
heuristic (+16.5% relative), and top-3 **+13.8 pts** over `type_prior_move` and
**+18.8 pts** over `max_expected_damage`. The large top-3/MRR gap is the
strongest signal that it ranks candidates, not just action types.

Note: `max_expected_damage` and `best_damage_move_no_switch` are identical here
because `next_opp_hp_delta` correlates −1.0 with `impact_expected_damage_fraction`,
and the damage-max candidate is essentially always a move.

Context: first-report **test** metrics were top-1 43.57% / top-3 83.02%;
validation here (45.6% / 86.6%) is consistent and slightly higher — no test
re-use.

## Breakdowns (model top-1 / top-3)

**By chosen action type**
| Chosen kind | groups | top-1 | top-3 |
| --- | ---: | ---: | ---: |
| move | 1,557 | 0.524 | 0.922 |
| switch | 639 | 0.302 | 0.759 |
| move_tera | 58 | 0.310 | 0.517 |

**By damaging vs non-damaging replay choice**
| Chosen | groups | top-1 | top-3 |
| --- | ---: | ---: | ---: |
| damaging | 1,129 | 0.565 | 0.926 |
| non-damaging | 1,125 | 0.346 | 0.805 |

**By candidate count**
| Bucket | groups | top-1 | top-3 |
| --- | ---: | ---: | ---: |
| ≤4 | 363 | 0.606 | 0.964 |
| 5–8 | 1,059 | 0.474 | 0.894 |
| 9–12 | 729 | 0.361 | 0.789 |
| >12 | 103 | 0.408 | 0.767 |

**By turn bucket** (roughly flat — no late-game collapse)
| Turn | groups | top-1 | top-3 |
| --- | ---: | ---: | ---: |
| 1–5 | 484 | 0.477 | 0.888 |
| 6–10 | 447 | 0.438 | 0.857 |
| 11–20 | 740 | 0.464 | 0.862 |
| >20 | 583 | 0.441 | 0.858 |

Masked/unmatched groups (772 unmatched + 600 initial-deployment non-decisions
dataset-wide) are excluded from rank scoring by construction, not evaluated.

## Curated Examples

Feature-level only (species/move identities are hashed, so names are not
recoverable from the dataset).

**Model beats max-damage (403 groups total).** Representative cases are
mid-game decisions (turns 5–13, 10–13 candidates) where the replay player chose
a **non-damaging switch** and the model ranked that switch #1, while
`max_expected_damage` ranked it 9th–10th. The model has learned that switching
is sometimes correct — something no damage heuristic can express.

**Max-damage beats model (257 groups total).** Worst model misses:
- a `move_tera` with expected damage 0.59 was chosen, but the model picked a
  0-damage move (model rank 7) — Tera mis-ranking;
- two cases where a damaging move was chosen but the model preferred a **switch**
  (model rank 6–7) — the model over-predicts switching in some damage spots.

So the head's mistakes cluster on (a) Tera moves and (b) occasional
switch-over-attack confusion — both consistent with the breakdowns above.

## Does It Learn Beyond Damage Heuristics?

**Yes.** It beats `max_expected_damage`, `max_ko_chance`, `max_base_power`,
`max_accuracy`, the no-switch heuristic, and the `type_prior_move` prior on
top-1, top-3, and MRR. The decisive evidence is non-damaging/switch decisions:
damage heuristics score ~0 on a chosen switch by construction, yet the model
reaches 30.2% top-1 on switches and 34.6% top-1 on non-damaging choices, and its
top-3 (86.6%) far exceeds any heuristic. It is genuinely ranking candidates
using state+action context, not replaying a type prior.

## Limitations

- Single checkpoint from a 210-battle multitask wiring run; absolute accuracy is
  modest and the value head it shares a trunk with is weak.
- `move_tera` is severely under-represented (426 of 24,624 positives, 1.7%);
  the 58 validation Tera groups give noisy, low Tera accuracy.
- Replay-imitation target: a non-matched candidate is "not chosen", not
  "objectively worse", so top-1 understates decision quality.
- Hashed identities prevent semantic (species/move-name) example inspection.
- Baselines are feature-column heuristics, not a full forward-search engine.

## Recommended Next Task

The action-rank head is promising enough to scale. **Design the next larger
action-rank diagnostic dataset/training run** (e.g. 1000 battles), keeping the
frozen v7/v5 schemas and split discipline, and explicitly **rebalance or
upweight Tera and switch decisions** (and consider a Tera-aware sampling/loss
weight) to fix the two identified weak spots. Defer value-head work per the
standing decision rule. Gate stays closed pending explicit approval to build the
larger dataset.
