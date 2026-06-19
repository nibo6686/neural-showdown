# vNext Label Source Audit

## Existing state-value labels

`build_replay_value_dataset` assigns the final battle result to each public
replay state from p1's perspective. `build_live_private_value_dataset` improves
perspective handling by producing both p1 and p2 examples with the same terminal
result mirrored to the state owner. Local trace value data may discount terminal
return by distance to battle end. Replay/live-private value trainers regress
these scalar targets with MSE.

These labels use the future winner only as a supervised target, which is valid.
Their main weakness is high variance: every state in a won battle receives +1
and every state in a lost battle receives -1 regardless of tactical quality.
The old public value path is p1-only, and older training loaders may randomly
split examples rather than enforcing battle-level splits.

## Existing action labels

`build_replay_policy_dataset` records the replay-chosen move/switch and attempts
to map it to the fixed 13-action head. `build_action_rank_dataset` reconstructs
legal candidates, assigns one positive to the replay-chosen action, and treats
the remaining candidates as unchosen. The ranker uses grouped cross-entropy.

The observed action is perspective-correct because it is attached to the acting
side. It is an imitation target, not proof that alternatives were bad. Existing
candidate reconstruction may append an unmatched chosen action, and ordinary
move-event matching does not by itself distinguish a Tera move from the same
non-Tera move. The vNext label path instead requires an organic candidate match
and uses same-turn Tera protocol evidence.

## Existing action-value proxy

`build_action_value_dataset` predicts value before and after the observed
action using the old v2 value checkpoint, forms a value delta, adds a weighted
terminal result, and stores rank directions/sample weights. This is a
model-derived proxy for the chosen action only. Unchosen actions have no
counterfactual outcome. It is not a true Q-value label and should not be reused
as the first vNext action-value target.

## Leakage and split safety

Final outcome is permitted as a label. Features must remain prefix-time except
for the already documented own-side reconstruction assumption that later public
reveals may complete the player's roster/moves. No true hidden opponent team is
used. The `diagnostic_300` manifest fixes train/validation/test by battle before
featurization; all vNext labels inherit that split.

State terminal-outcome labels and replay-imitation action-rank labels are
suitable for the first v7/v5 diagnostic run. True action-value labels are not
yet available.
