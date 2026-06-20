# diagnostic_1000 Action-Rank-Only Training Report

## Purpose and Scope

Exactly one **action-rank-only** diagnostic training run on the frozen
`diagnostic_1000_action_rank_v7_v5` dataset, then an offline evaluation of the
selected checkpoint against simple baselines on the validation split. State-value
and action-value objectives were disabled; only the grouped action-rank
imitation head was trained. No value/Q training, no hyperparameter search, no
checkpoint promotion, no live-default change, no private-match testing.

## Config and Commands

Config: `configs\diagnostic_1000_action_rank_v7_v5.rank_only.windows.json`

```powershell
$env:PYTHONPATH=(Resolve-Path .\trainer\src).Path
# 1) validate-only
D:\Anaconda\envs\neuralgpu\python.exe -m neural.train_vnext_diagnostic `
  --config .\configs\diagnostic_1000_action_rank_v7_v5.rank_only.windows.json --validate-only
# 2) train (once)
D:\Anaconda\envs\neuralgpu\python.exe -m neural.train_vnext_diagnostic `
  --config .\configs\diagnostic_1000_action_rank_v7_v5.rank_only.windows.json
# 3) offline eval on validation
D:\Anaconda\envs\neuralgpu\python.exe -m neural.evaluate_vnext_action_rank `
  --config .\configs\diagnostic_1000_action_rank_v7_v5.rank_only.windows.json `
  --checkpoint .\artifacts\diagnostic_training\diagnostic_1000_action_rank_v7_v5_rank_only\model.best.pt `
  --split validation `
  --out .\artifacts\diagnostic_training\diagnostic_1000_action_rank_v7_v5_rank_only\action_rank_offline_eval_validation.json
```

Code change: `train_vnext_diagnostic.py` now supports a disabled `state_value`
objective (rank-only) and derives expected battle/split counts from the manifest
instead of hardcoding 210/45/45. All value batches, value optimizer params,
value metrics, and value checkpoint selection are skipped when state-value is
disabled.

## Validate-Only Result

PASS:

- dataset, schema dims, and ordered-name fingerprints matched (state/action
  fingerprints `validated`);
- battle splits 700/150/150; 79,525 matched action-rank groups;
- state-value objective **disabled**; action-value labels **absent (0)**;
- action-rank loss finite (smoke 2.377); value loss `null`;
- `optimizer_step_source = rank_batches_only`; optimizer not created; 0 steps;
- model parameter count 218,786.

## Runtime / Device / Model

- Device: **CUDA**
- Runtime: **457.7 s (~7.6 min)**
- Epochs completed: **11** (early-stopped, patience 3 on validation rank NLL)
- Optimizer steps: 10,890 (rank batches only)
- Model parameters: **218,786** (shared MLP; value head present but untrained)
- Mandatory overfit check: **passed** (rank train top-1 0.969 in 225 steps; value MSE not evaluated)

## Objective Isolation

- Action rank trained: yes; state value: **no**; action value: **no**
- `optimizer_step_source = rank_batches_only`
- `best_validation_value_mse = None`, `test_value = None`
- Checkpoint selection metric: **validation_action_rank_nll**

## Train / Validation Rank Metrics by Epoch

| Epoch | Val NLL | Val top-1 | Val top-3 |
| ---: | ---: | ---: | ---: |
| 1 | 1.4199 | 0.4125 | 0.8256 |
| 2 | 1.3884 | 0.4402 | 0.8380 |
| 3 | 1.3675 | 0.4480 | 0.8417 |
| 4 | 1.3598 | 0.4534 | 0.8507 |
| 5 | 1.3468 | 0.4569 | 0.8506 |
| 6 | 1.3404 | 0.4565 | 0.8516 |
| 7 | 1.3404 | 0.4591 | 0.8545 |
| **8** | **1.3276** | **0.4626** | **0.8576** |
| 9 | 1.3353 | 0.4637 | 0.8517 |
| 10 | 1.3286 | 0.4591 | 0.8551 |
| 11 | 1.3334 | 0.4608 | 0.8517 |

**Best checkpoint: epoch 8** (lowest validation rank NLL 1.3276).

## Validation Offline Baseline Comparison (best checkpoint, 7,951 groups)

| Method | top-1 | top-3 | MRR |
| --- | ---: | ---: | ---: |
| **Action-rank model** | **0.4626** | **0.8576** | **0.6658** (NLL 1.3276) |
| type_prior_move | 0.3802 | 0.7303 | 0.5802 |
| max_expected_damage (= max HP delta) | 0.3820 | 0.6646 | 0.5513 |
| best_damage_move_no_switch | 0.3820 | 0.6646 | 0.5513 |
| max_ko_chance | 0.3509 | 0.6559 | 0.5306 |
| max_base_power | 0.3444 | 0.6529 | 0.5260 |
| max_accuracy_damaging | 0.3411 | 0.6541 | 0.5251 |
| random_move | 0.2069 | 0.5035 | — |
| random_legal | 0.1622 | 0.4673 | 0.3846 |

The model beats every baseline on top-1, top-3, and MRR: top-1 +8.1 pts over the
best heuristic, top-3 **+12.7 pts** over `type_prior_move`. `model beats max-damage`
on **1,319** groups vs **678** the other way.

## Breakdowns (model top-1 / top-3)

**By chosen action type**
| Kind | groups | top-1 | top-3 |
| --- | ---: | ---: | ---: |
| move | 5,459 | 0.560 | 0.944 |
| switch | 2,307 | 0.255 | 0.678 |
| move_tera | 185 | 0.178 | 0.551 |

**By damaging vs non-damaging replay choice**
| Chosen | groups | top-1 |
| --- | ---: | ---: |
| damaging | 3,884 | 0.628 |
| non-damaging | 4,067 | 0.305 |

**By candidate count**: ≤4 0.627 / 5–8 0.479 / 9–12 0.374 / >12 0.344 (more
candidates → harder, as expected).

**By turn bucket**: 1–5 0.476 / 6–10 0.442 / 11–20 0.456 / >20 0.476 (flat; no
late-game collapse).

## Final Test Metrics (touched once, after checkpoint selection)

- Test groups: 8,221
- Test top-1 **0.4608**, top-3 **0.8504**, MRR **0.6641**, NLL **1.3252**
- Test value: N/A (value head disabled)

Test was evaluated exactly once on the epoch-8 checkpoint and never used for
tuning. Validation (0.4626/0.8576) and test (0.4608/0.8504) agree closely.

## Curated Examples

Feature-level (identities hashed).

**Model beats max-damage (1,319 groups).** Mid/late-game decisions (turns 16–24,
~11 candidates) where the player chose a **non-damaging switch** and the model
ranked that switch #1 while `max_expected_damage` ranked it 10th — the model has
learned switching, which damage heuristics cannot express.

**Max-damage beats model (678 groups).** Worst misses are concentrated on
**Tera moves**: the player chose `move_tera` and the model ranked the *non-Tera*
variant of the same move above it (model rank ~6). The head under-values the
Tera commitment relative to the plain move.

## Comparison vs diagnostic_300 Action-Rank

| Metric | diagnostic_300 (multitask first ckpt, val) | diagnostic_1000 (rank-only, val) |
| --- | ---: | ---: |
| top-1 | 0.4556 | **0.4626** |
| top-3 | 0.8656 | 0.8576 |
| MRR | 0.6643 | 0.6658 |
| NLL | 1.3511 | **1.3276** |
| move top-1 | 0.524 | **0.560** |
| switch top-1 | 0.302 | 0.255 |
| move_tera top-1 | 0.310 (58 groups, noisy) | 0.178 (185 groups) |
| beats / loses vs max-dmg | 403 / 257 | 1,319 / 678 |

Overall metrics are comparable-to-slightly-better (higher top-1, lower NLL,
marginally lower top-3). Move ranking improved. **Switch and Tera per-decision
accuracy did not improve** — the 300 switch/Tera figures were higher but the
1000 sample is ~3× larger and more reliable (185 Tera groups vs 58). So the
enrichment delivered more switch/Tera *volume* but those decisions remain the
hard part; rank-only training (no shared value-auxiliary signal) may also
slightly disfavor switch state-features relative to the 300 multitask model.

## Does It Learn Beyond Damage Heuristics?

**Yes.** It beats all damage/accuracy/KO/type-prior baselines on top-1, top-3,
and MRR, and reaches 25.5% top-1 on switches and 30.5% on non-damaging choices —
decisions where damage heuristics score ~0 by construction. The decisive top-3
gap (0.858 vs 0.730 type-prior, 0.665 max-damage) shows genuine candidate-level
ranking. The clear remaining weakness is **Tera** (top-1 0.178, below type-prior
on those groups).

## Warnings / Limitations

- Single rank-only run, single config; no tuning sweep (by design).
- Replay-imitation target: unchosen candidates are "not chosen", not bad — top-1
  understates decision quality.
- Tera moves are intrinsically sparse (1.8% of positives); 185 validation Tera
  groups still give a modest sample.
- Hashed identities prevent semantic (species/move) example inspection.
- Value head exists in the checkpoint but is untrained (random init); it must not
  be used for value scoring.

## Recommended Next Task

The action-rank head now beats baselines across two dataset scales with sane
behavior (good switching; Tera is the known weak spot). Of the two options,
recommend the **offline-to-live inference readiness audit** before any
private-match testing: verify that the live action path can load and serve this
diagnostic checkpoint's schema (v7/v5) with parity to the offline evaluator, and
decide what (if anything) must change versus the current live v2/v3 defaults.
Track Tera ranking as a known representation/learning gap to revisit (e.g. a
Tera-aware loss weight or feature emphasis) rather than blocking on it. The
value-label quality audit remains the alternative if you prefer to unblock value
training first. Gate stays closed pending that decision and explicit approval.
