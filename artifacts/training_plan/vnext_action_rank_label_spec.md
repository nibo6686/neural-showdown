# vNext Action-Rank Label Specification

- Target: `replay_chosen_action_one_hot`
- Type: one positive candidate per decision group
- Positive: the legal candidate matching the replay-observed action
- Other candidates: unchosen, not objectively bad
- Split: inherited from the replay battle
- Initial sample weighting: uniform `1.0`
- Auxiliary field: terminal outcome may be stored but does not change the v1
  imitation target or weight

## Matching rules

- Moves match Showdown-style normalized move identity and action kind.
- A same-side Tera protocol event in the turn changes the expected kind from
  `move` to `move_tera`; the ordinary move candidate must not receive the
  positive in that case.
- Switches match normalized target species.
- Forced switches use the same switch-species matching; forced status should be
  retained as metadata when reconstructable.
- Pass, wait, team preview, and unsupported commands are excluded.
- Turn-0 initial deployment `switch` protocol lines are excluded as
  non-decisions.
- Disabled or otherwise illegal candidates cannot be positive.
- A replay action that cannot be matched to the independently reconstructed
  candidate set is explicitly counted and the action-rank group is skipped.
  The chosen action must not be injected merely to force a match.

Candidate count is the complete reconstructed legal set, capped by the existing
13-action codec. The first diagnostic run does not use heuristic or rollout
scores to improve or relabel replay decisions.

The tiny-10 dry run reports the unmatched rate and action-kind breakdown. An
unmatched group remains excluded even if this reduces action-rank coverage;
coverage loss is preferable to manufacturing a positive candidate.

## Safe reconstruction rules

- Candidate state is reconstructed from the exact event/protocol prefix before
  the observed action, including earlier events in the same turn.
- The current decision's immediately preceding Tera commitment is excluded from
  that prefix so Tera remains available for the matching candidate.
- Public move reveals are assigned to the chronologically active species, not
  blindly keyed by the protocol actor alias/nickname.
- Completed roster entries use switch-detail species identities, avoiding
  nickname/form duplicates that can displace legal switch targets.

On tiny-10 these rules changed the original 459/596 match result (77.0%) to
576/576 eligible decisions (100.0%), with 20 initial-deployment non-decisions
explicitly skipped. No positive was injected or guessed.
