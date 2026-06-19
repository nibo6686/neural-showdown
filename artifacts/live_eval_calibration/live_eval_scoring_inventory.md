# Live-Eval Scoring Inventory (Part A)

**Date:** 2026-06-18
**Scope:** map every scorer the live evaluator and branch search can use, what
`/evaluate` actually returns, and where action-impact deltas are computed.

## Scorers that exist

| Scorer | Defined in | Output | Perspective | Bounded? | Status |
| --- | --- | --- | --- | --- | --- |
| **old live_private_value (v2)** | `models/policy_value_mlp.py`, loaded by `live_eval_server.load_value_model_once()` | raw value head scalar | current player | **No** (unbounded linear head) | **`/evaluate` DEFAULT**; deprecated as branch scorer (collapses) |
| **live_sim_value (v1)** | `models/value_mlp.py` `BoundedValueMLP`; `one_turn_branch.make_live_sim_value_score_fn` | tanh scalar in [-1,1] | player_side | **Yes** | opt-in (`NEURAL_BRANCH_SCORER=live_sim_value`); calibrated, not competitive for branch selection |
| **material/HP** | `one_turn_branch.make_material_score_fn` | `(own_hp − opp_hp)/6` clamped [-1,1] | player_side | Yes (clamp) | **default research branch scorer** |
| **improved state scorer** | `one_turn_branch.make_state_score_fn` | weighted HP/alive/status/hazard [-1,1] | player_side | Yes | opt-in; regressed vs material |
| **action-value ranker (v2)** | `live_action_recommender` (`DEFAULT_ACTION_VALUE_RANKER_V2_PATH`) | per-action scalar (value-delta) | player_side | No | action ranking only, not a state value |
| **replay value (public 31D)** | `build_replay_value_dataset` / `policy_value_mlp` | raw value | p1-ish public | No | fallback when `NEURAL_LIVE_MODEL=public-replay` |

All three branch score functions share the signature
`_score(log, step_result, player_side)` where `step_result` carries per-side
`requests` (for value models, via `build_features_from_live_payload`) and `views`
(for material, via `views[player_side].self_team / opponent_team / team_size`).

## 1. What scores `/evaluate` (current-state evaluation)

`live_eval_server.evaluate_with_model()`:

1. Loads the **default value model** = `load_value_model_once()` →
   `artifacts/checkpoints/gen9randombattle_live_private_value_v2.pt`
   (`model_type=live-private-belief-value`, **unbounded**, feature
   `live-private-belief-v2`, dim **115**).
2. Builds live features via `build_features_from_live_payload(...)`
   (perspective-filtered to `payload.player`: own request + public protocol +
   randbats opponent beliefs; **no exact hidden opponent state**).
3. `value = model(x)` → raw scalar.
4. **`p1_win_prob = clamp((value + 1) / 2, 0, 1)`** (`live_eval_server.py:945`),
   `p2_win_prob = 1 − p1_win_prob`.

**Two structural concerns surface here:**

- **Unbounded value → linear prob map.** The default model head is *not* bounded
  (no tanh), but `/evaluate` maps it as if it were in [-1,1] via `(value+1)/2`.
  Out-of-range values are silently clamped to 0/1, which manufactures false
  certainty. The *calibrated* head (`live_sim_value_v1`, tanh) is **not** the
  `/evaluate` default.
- **Perspective.** `value` is from `payload.player`'s perspective, but it is
  written directly into **`p1_win_prob`**. This is only correct when the requesting
  player is p1. If the extension user is p2, the reported `p1_win_prob` is actually
  the *current player's* win prob mislabeled. (In practice the user usually plays
  p1, so it often looks right, but it is fragile and untested for p2.)

The recommendations doc already established this default model **collapses to ~+1
for both sides on branch states** (train/serve skew) and is "deprecated as a
one-turn branch scorer." It still *runs* on its native serving path, but its
calibration as a current-state win-prob is exactly what the user reports looking
poor.

## 2. What scores action ranking

`recommend_actions(...)` in `live_action_recommender.py` (called from
`evaluate_with_model` with `current_value=value`). It combines, by configurable
weights:

- **rollout estimate** (`NEURAL_ROLLOUT_WEIGHT`, default 0.75)
- **action-value ranker** (`NEURAL_RANKER_WEIGHT`, default 0.20)
- **replay-policy prior** (`NEURAL_POLICY_WEIGHT`, default 0.05)

with masking/fallbacks. Action recommendation does **not** by default use the
one-turn/two-ply branch leaf scorers — those live in the audit agents
(`one_turn_branch.py`, `two_ply_branch.py`), not in the live recommender path.

## 3. What scores branch leaves

`one_turn_branch.py` / `two_ply_branch.py` select the leaf scorer by
`NEURAL_BRANCH_SCORER`:

- default `material` → `make_material_score_fn` (HP differential)
- `live_sim_value` → bounded tanh head
- `value` → old live-private head (diagnostic; collapses)
- `state` → improved weighted scorer (opt-in)

Terminal states override the leaf score (win/loss/tie) via `_terminal_score`.

## 4. Default checkpoint, feature version, dimension

- **Value model checkpoint:** `gen9randombattle_live_private_value_v2.pt`
- **Feature version / dim:** `live-private-belief-v2` / **115**
- **Action ranker:** `gen9randombattle_action_value_ranker_v2.pt`
  (`state_dim=115`, `action_dim=165`, `input_size=280`)
- **Policy prior:** `gen9randombattle_replay_policy.pt`

Strict mode (`NEURAL_STRICT_LIVE_EVAL=1`) asserts these versions/dims and refuses
fallbacks at startup.

## 5. Perspective handling (summary)

- Branch score fns: explicitly `player_side` perspective, bounded [-1,1] (except
  the unbounded value heads). Material flips by construction (own−opp).
- `/evaluate`: value is `payload.player` perspective but mapped onto `p1_win_prob`
  — correct only for p1 (see concern above).
- Dataset labels (`build_live_sim_value_dataset`): perspective-correct
  `result_from_winner_side(winner, perspective=side)`, discounted by turns-to-end.

## 6. Output transform per scorer

| Scorer | Native output | Transform to win prob |
| --- | --- | --- |
| old live_private_value | unbounded raw | `(value+1)/2` clamped (in `/evaluate`) |
| live_sim_value | tanh [-1,1] | none applied live; would also be `(v+1)/2` |
| material/HP | `(own−opp)/6` clamped | none (research score only) |
| action-value ranker | per-action delta | none (ranking) |

## 7. Where action-impact deltas are computed

- **Live:** `recommend_actions` computes per-action scores from rollout + ranker +
  policy. It receives `current_value` but the headline win-prob delta vs the
  current state is **not** the primary ranking signal; rollout dominates.
- **Branch audits:** `one_turn_branch` / `two_ply_branch` compute the impact of
  each action as `leaf_score(post_step_state) − (implicit current)`; selection is
  by best post-action leaf score, i.e. the action-impact *is* the leaf scorer
  applied to the resulting state. This is where current-state calibration quality
  directly drives action choice — and why a poorly calibrated current-state value
  contaminates action-impact (addressed in `action_impact_calibration_report.md`).

## Headline finding for the audit

`/evaluate` is built on the **deprecated, unbounded, perspective-fragile**
live_private_value head with a naive `(value+1)/2 → p1_win_prob` map. The
**material/HP** scorer and the **bounded live_sim_value** head are better behaved.
Parts B–C quantify exactly how trustworthy each is; Part E recommends which to
trust.
