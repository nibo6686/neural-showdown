# Action Recommendation Stack Inventory (Part A)

**Date:** 2026-06-18
**Scope:** how `/evaluate` ranks legal actions today. Code: `live_eval_server.py`,
`live_action_recommender.py`, `sim_branch_evaluator.py`, `action_features.py`.
Companion: `live_eval_calibration/live_eval_scoring_inventory.md` (state-eval side).

## 1. How `/evaluate` builds legal actions

`evaluate_with_model` → `recommend_actions` → `legal_action_candidates(payload)`
(`live_action_recommender.py:192`). Order of preference:

1. `payload.legal_actions` (overlay-supplied) → `_normalize_payload_legal_actions`.
2. Else derive from the Showdown `request`: `_request_active_moves` (active block)
   plus `_request_switches` (bench), honoring `forceSwitch` / `trapped`.

Each candidate is `{index, kind, label, slot, disabled, source}`. The fixed
13-index action space (`docs/action-space.md`) is **not** used for ranking; ranking
is over these per-request candidates. Note: candidates do **not** carry the Showdown
`choice` command string, so traces report `choice: null`.

## 2. Components that contribute to action ranking

Per legal action, `ActionValueEstimator.estimate` (`live_action_recommender.py:559`)
plus `recommend_actions` produce up to three scores that are blended:

| Component | Produced by | Live availability |
| --- | --- | --- |
| **Rollout expected value** | `sim_branch_evaluator.evaluate_actions` → `_approximate_decision_rollout` | Live = **approximate** (no seed). Dominant weight 0.75. |
| **Action-value-ranker score** | `ActionRankerMLP`, checkpoint `gen9randombattle_action_value_ranker_v2.pt` | Loaded by default; weight 0.20 (normalized). |
| **Policy prior** | `replay_policy` 13-action head | Weight 0.05; often unavailable. |
| Switch-proxy value | live-private value model on a proxy state | Switches only; only blended into the *fallback* `score`, not the rollout `final_score`. |

## 3. Does action recommendation still use the legacy value head internally?

**Yes, indirectly, in two places** — even though `/evaluate`'s *displayed* value now
uses the calibrated `live_sim_value` head:

- `recommend_actions` is called with `current_value=legacy_value` and
  `value_model=model` where `model` is the **old collapsed `live_private_value_v2`**
  (`live_eval_server.py:1048-1057`). It is used for the **switch-proxy** value
  (`_estimate_switch_value`) and appears in `score_components.current_value`.
- The **action-value ranker's training labels** are value-deltas from that same
  live-private head (computed on the reconstructed-replay path where it still
  discriminates — see `agent_audit/recommendations.md` §5). So the ranker indirectly
  inherits the legacy head's value signal.

The `live_sim_value` calibrated head is **not** used anywhere in action ranking.

## 4. How damage diagnostics are used

`sim_branch_evaluator._damage_diagnostics` → `damage_engine.estimate_action_damage`
(Smogon calc via sim-core RPC). In the **approximate** path it feeds the per-action
score (`_approximate_action_value`): `average_percent/35`, `estimated_ko_chance*1.2`,
an `immune` penalty, plus a separate hand-rolled `_type_effectiveness` chart. Damage
fields (`average_percent`, `ko_chance`, `type_effectiveness`, `immune`, …) are also
attached to each row for display. Switches get `not_applicable_switch`.

## 5. How rollout diagnostics are used

`evaluate_actions` chooses mode via `_selected_rollout_mode` (`auto` → `exact` only
if a replay seed is parseable, else `approximate`). **Live has no seed → always
`approximate`.** `_approximate_decision_rollout` samples `current_value + base_score
+ Gaussian noise` against a fixed opponent-action mixture; `expected_value` = mean.
Exact sim rollout (`exact_sim_rollout`) only runs in seeded research, not live.

## 6. How ranker and action-value-ranker scores are combined

`load_action_ranker_once` selects `action_value_ranker_v2` when present (else the
plain action-ranker, else policy/switch-proxy). The ranker takes
`concat(state_features[115], action_features[165])` → scalar. In the blend the raw
ranker score is **min-max normalized across the legal set** (`normalize_rank`) before
weighting. `response_method` distinguishes `action_value_ranker` vs `action_ranker`.

## 7. How the policy prior is used

`_policy_probs` runs the replay-policy 13-action head; `policy_prob` = softmax at the
action index (0 if disabled). Weight 0.05. The default `replay_policy` checkpoint is
frequently missing/mismarked, so this term is commonly 0 with a warning.

## 8. How weights are configured

Env vars read in `recommend_actions` (defaults): `NEURAL_ROLLOUT_WEIGHT=0.75`,
`NEURAL_RANKER_WEIGHT=0.20`, `NEURAL_POLICY_WEIGHT=0.05`,
`NEURAL_ROLLOUTS_PER_ACTION=8`, `NEURAL_ROLLOUT_MODE=auto`,
`NEURAL_OPPONENT_POLICY=uniform`.

## 9. Where action-impact deltas are computed

There is **no explicit current→next state delta** in the live recommender. The
nearest things:

- `_approximate_action_value` adds a per-action `base_score` on top of a single
  shared `current_value` — so the "impact" of an action is its base_score, a
  heuristic, not a real resulting-state evaluation.
- The seeded branch tools (`one_turn_branch`, `two_ply_branch`) **do** score real
  resulting states, but are not invoked by `/evaluate`.

So live action-impact is a heuristic increment, not a state-difference.

## 10. Are move side effects represented?

| Side effect | In damage diag? | In action features (ranker)? | In approx score? |
| --- | --- | --- | --- |
| Draco Meteor / SpA self-drop | ❌ | ❌ (no self-drop feature) | ❌ |
| Close Combat-style Def/SpD drop | ❌ | ❌ | ❌ |
| Recoil | ❌ | ❌ | ❌ |
| Recharge | ❌ | ❌ | ❌ |
| Lock-in (Outrage) | partial (`locked_move_active` volatile warning if *already* locked) | ❌ | partial warning only |
| Healing | ❌ damage | ✅ `flag_recovery` | ✅ small contextual bonus |
| Setup (boosts) | ❌ | ✅ `flag_setup` | ✅ contextual |
| Status | ❌ (`non_damaging_move`) | ✅ `flag_status` | ✅ contextual no-op penalties |
| Switching (pivot) | ❌ | ✅ `flag_pivot` | ✅ small bonus |
| Tera | ✅ (`tera_damage_bonus`) | ✅ tera feature block | ✅ bonus |

**The drawback side effects that matter for the disputed case — self-stat drops,
recoil, recharge, lock-in — are represented nowhere.** Healing/setup/status/pivot/
tera *are* represented. Part F's `action_side_effects.py` fills the detection gap as
a diagnostic only.

## 11. Are scores current-state values, next-state values, deltas, damage, or blended?

**Blended heuristics over a current-state proxy.** Concretely, the live
`final_score` is:

```
final_score = 0.75 * approx_rollout_expected_value     # current_value + heuristic base_score + noise
            + 0.20 * normalized_action_ranker_score    # learned, action-conditioned, no drawback feature
            + 0.05 * policy_prob                        # replay-policy prior (often 0)
```

- **Not** next-state values (no real resulting-state evaluation in live).
- **Not** value deltas (no current→next difference).
- The rollout term is an **immediate-damage-weighted current-state proxy**; the
  ranker term is a **learned immediate action score**. Both are blind to self-stat
  drops and to the future position. This is the structural root of the Draco vs
  Psyshock dispute (see `draco_vs_psyshock_diagnostic.md`).
