# vNext Action-Value Label Specification

Initial status: **not generated**.

The first diagnostic run must not present imitation labels, terminal result, or
v5 resolved-impact fields as true action values. Assigning the final battle
outcome to every chosen action is extremely noisy, and ordinary replays provide
no outcomes for unchosen legal actions. The existing value-delta builder is a
checkpoint-derived proxy for the observed action, not counterfactual ground
truth.

`legal-action-v5` immediate damage, accuracy, KO, field, and next-state
diagnostics are action features. They are not a Q-value because they do not
capture the opponent response, longer-horizon consequences, or the outcome of
unchosen actions.

The diagnostic dataset may store an explicit unavailable marker and provenance
metadata. No action-value loss should be enabled. Future true/proxy action-value
work requires one of:

- branch-applied next states with reliable transition deltas;
- a documented rollout/evaluator target for every legal candidate;
- controlled simulator counterfactual outcomes with consistent opponent policy.

Any future proxy must receive a new label version and be named as a proxy rather
than a true Q-value.
