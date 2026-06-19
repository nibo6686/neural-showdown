# Value Model Inventory (Part A)

Audit date: 2026-06-18
Scope: seeded Gen 9 singles. Inventory of every value/scorer model, its feature
domain, label definition, target perspective, and output scale.

## Checkpoints

| Checkpoint | Size | Type | feature_version | input_size | hidden | head |
| --- | ---: | --- | --- | ---: | --- | --- |
| `gen9randombattle_live_private_value_v2.pt` | 1.17 MB | live-private-belief-value | `live-private-belief-v2` | 115 | [256,256] | value_head Linear(256,1) |
| `gen9randombattle_live_private_value.pt` | — | live-private-belief-value | `live-private-belief-v1` | 78 | [256,256] | value_head Linear(256,1) |
| `gen9randombattle_replay_value.pt` | 0.9 MB | public-replay value | (31D public) | 31 | [256,256] | value_head Linear(256,1) |
| `gen9randombattle_value.pt` | 4.4 MB | local-trace value | (1179D base+extras) | 1179 | [256,256] | value_head Linear(256,1) |
| `gen9randombattle_action_value_ranker_v2.pt` | 1.27 MB | action-value-ranker | state `live-private-belief-v2` + action `legal-action-v3` | 280 (=115+165) | [256,128] | net Linear(128,1) |
| `gen9randombattle_action_ranker_v2.pt` | 1.27 MB | action-ranker | action `legal-action-v3` | 280 | [256,128] | Linear(128,1) |
| `gen9randombattle_action_ranker.pt` | 0.83 MB | action-ranker (legacy) | action `legal-action-v1` | 134 | [256,128] | Linear(128,1) |

All value models share `PolicyValueMLP` (`models/policy_value_mlp.py`): ReLU
trunk, separate `policy_head` and `value_head`. **The value head is a plain
`Linear(.,1)` with no `tanh`/`sigmoid`**, so the value output is an **unbounded
raw scalar**, not a probability or logit. The live server transforms it with
`p1_win_prob = (value + 1) / 2` clamped to `[0,1]`.

## Model families

### Live-private belief value (current default scorer)
- Code: `live_private_features.build_features_from_live_payload` /
  `build_live_private_feature_vector`; trained by `train_live_private_value.py`;
  dataset `build_live_private_value_dataset.py`
  (`data/value/gen9randombattle_live_private_value_v2.npz`).
- Feature domain: `live-private-belief-v2`, 115D = 31D public replay-event
  features (perspective side) + own private team/move/PP/item/ability/tera/legal
  features + opponent belief features (randbats) + tactical state features.
- Labels: public-replay examples use `value_target = result_from_winner_side(
  winner_side, perspective=side)` ∈ {-1, 0, +1} — **the final game result applied
  to every turn, perspective-correct per side, undiscounted**. Local-trace
  examples use `discounted_terminal_return(final_result, steps_to_terminal,
  gamma)` where `final_result_from_winner` is **p1-perspective** and trace
  features are always built with `player_side="p1"`.
- Target perspective: **per-side** (features and labels both encode the side), so
  the model is trained to be player-perspective: positive ≈ the feature-side is
  winning.
- Output scale: unbounded raw scalar trained by regression toward ±1.

### Public-replay value (`replay_value.pt`)
- 31D public event features only (`build_replay_value_dataset.py`). Label
  `result_from_winner_side(..., perspective=side)`. p1-or-side perspective,
  unbounded scalar. Used only as a fallback when `NEURAL_LIVE_MODEL=public-replay`.

### Local-trace value (`value.pt`)
- 1179D full sim-core base features (`build_value_dataset.py`,
  `value_features.py`). Label = discounted terminal return, **p1-perspective**.
  Not used by the live path or the branch scorer.

### Action-value ranker (`action_value_ranker_v2.pt`)
- 280D = 115D live-private state + 165D action features. **Label is a ranking
  target derived from the live-private value model:** `target_score = (value_after
  - value_before) + 0.25 * final_result` (`build_action_value_dataset.py`), with
  `final_result = result_from_winner_side(..., perspective=side)`. So the ranker
  inherits the value model's value deltas (computed on the reconstructed-replay
  training path, where the value model behaves reasonably — see diagnostics).
- Output: raw scalar ranking score, perspective-correct per side.

## Summary answers (Part A questions)

- **Checkpoint paths / feature versions / dims:** table above.
- **Label definitions:** live-private = final ±1 (undiscounted) for replays,
  discounted terminal return for traces; public-replay = final ±1; local-trace =
  discounted terminal return; action-value ranker = value-delta + 0.25·final.
- **Target perspective:** value models are player/side-perspective (positive ≈
  the feature-side winning). The trace value head is p1-only.
- **Label kind:** win/loss final result (value models); value-delta + final
  (action-value ranker). None are material/HP scores.
- **Output scale:** unbounded raw scalar (no squashing), regressed toward ±1; the
  server maps it to a pseudo win-probability with `(v+1)/2`.
- **Perspective vs side-specific:** player-perspective via per-side features (not
  hard-coded to p1), except the local-trace value model which is p1-specific.
