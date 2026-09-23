# vNext Label Tiny-10 Dry Run

- Label version: `vnext-diagnostic-labels-v1`
- Battles: 299 valid / 1 failed
- State-value labels: 25020
- State-value distribution: {'wins': 12447, 'losses': 12573, 'draws': 0}
- Legal candidates retained for action rank: 194967
- Chosen actions matched: 25017
- Chosen actions unmatched: 3
- Chosen action match rate: 100.0%
- Matched by kind: {'move': 18363, 'move_tera': 429, 'switch': 6225}
- Unmatched by kind: {'move': 3}
- Action-rank positives / unchosen: 25017 / 169950
- Skipped states: 605
- Skip reasons: {'no_action_label': 4, 'unknown_or_draw_outcome': 0, 'chosen_action_unmatched_for_action_rank': 3, 'initial_deployment_nondecision': 598}
- Split state counts: {'test': 2427, 'train': 20339, 'validation': 2254}

State value is terminal outcome from the state owner's perspective (win +1, loss -1; ties/unknown excluded). Action rank is replay imitation with exactly one matched positive and unchosen candidates treated as unchosen rather than bad. Action-value labels are not generated.

- Ready for full `diagnostic_300` label extraction: **no**
- Training gate: **closed**.
