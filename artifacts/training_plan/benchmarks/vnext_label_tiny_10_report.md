# vNext Label Tiny-10 Dry Run

- Label version: `vnext-diagnostic-labels-v1`
- Battles: 10 valid / 0 failed
- State-value labels: 576
- State-value distribution: {'wins': 282, 'losses': 294, 'draws': 0}
- Legal candidates retained for action rank: 4299
- Chosen actions matched: 576
- Chosen actions unmatched: 0
- Chosen action match rate: 100.0%
- Matched by kind: {'move': 383, 'move_tera': 16, 'switch': 177}
- Unmatched by kind: {}
- Action-rank positives / unchosen: 576 / 3723
- Skipped states: 20
- Skip reasons: {'no_action_label': 0, 'unknown_or_draw_outcome': 0, 'chosen_action_unmatched_for_action_rank': 0, 'initial_deployment_nondecision': 20}
- Split state counts: {'test': 160, 'train': 231, 'validation': 185}

State value is terminal outcome from the state owner's perspective (win +1, loss -1; ties/unknown excluded). Action rank is replay imitation with exactly one matched positive and unchosen candidates treated as unchosen rather than bad. Action-value labels are not generated.

- Ready for full `diagnostic_300` label extraction: **yes**
- Training gate: **closed**.
