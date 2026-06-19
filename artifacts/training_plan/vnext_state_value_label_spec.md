# vNext State-Value Label Specification

- Label version: `vnext-diagnostic-labels-v1`
- Target: `terminal_outcome_from_state_owner`
- Range: win `+1.0`, loss `-1.0`
- Ties and unknown/incomplete outcomes: excluded, not encoded as neutral
- Perspective: always the owner/acting side of the state
- Splitting: battle-level assignment from `diagnostic_300`

Both p1 and p2 acting-side decision states are included. The same completed
battle therefore supplies mirrored outcomes: the winner's states receive +1
and the loser's states receive -1. Final result is allowed as a supervised
label; future hidden opponent state is not allowed in features.

Turn-0 initial deployment protocol switches are not decision states and are
excluded.

Known-result resignations, forfeits, disconnect wins, and timeout wins are
included, including early forfeits. They describe the observed terminal
outcome, although reports must retain short/forfeit metadata for later
sensitivity checks. Replays without a recognized winner and ties are excluded.

This is an undiscounted diagnostic target. It does not claim to measure the
immediate tactical quality of each state and will be noisy early in games.
