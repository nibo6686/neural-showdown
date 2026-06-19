# vNext Label Tiny-10 After Matcher Fixes

- Matched before / after: 459 / 576
- Unmatched before / after: 137 / 0
- Match rate before / after: 77.0% / 100.0%
- Unmatched reasons before: {'initial_deployment_nondecision': 20, 'move_missing_from_reconstructed_active_moves': 101, 'switch_target_missing_from_pre_action_legal_roster': 16}
- Unmatched reasons after: {}
- Skipped non-decision states: 20
- Intentionally still unmatched: 0
- Labels injected or guessed: **0**

Safe fixes: skip turn-0 initial deployments; assign public move reveals to the chronologically active species rather than actor aliases; stop the pre-action prefix before the current decision's Tera commitment; and build candidates from the exact event prefix. Remaining groups stay excluded.
