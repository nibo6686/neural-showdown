# vNext Label Tiny-10 After Matcher Fixes

- Matched before / after: 21661 / 25017
- Unmatched before / after: 3957 / 3
- Match rate before / after: 84.6% / 100.0%
- Unmatched reasons before: {'initial_deployment_nondecision': 598, 'move_missing_from_reconstructed_active_moves': 2930, 'switch_target_missing_from_pre_action_legal_roster': 429}
- Unmatched reasons after: {'move_missing_from_reconstructed_active_moves': 3}
- Skipped non-decision states: 598
- Intentionally still unmatched: 3
- Labels injected or guessed: **0**

Safe fixes: skip turn-0 initial deployments; assign public move reveals to the chronologically active species rather than actor aliases; stop the pre-action prefix before the current decision's Tera commitment; and build candidates from the exact event prefix. Remaining groups stay excluded.
