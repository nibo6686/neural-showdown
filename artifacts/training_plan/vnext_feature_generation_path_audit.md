# vNext Feature Generation Path Audit

## Current replay dataset paths

- `neural.parse_replay_logs` converts raw protocol logs into replay
  trajectories.
- `neural.build_replay_value_dataset` and
  `neural.build_replay_policy_dataset` generate the older 31D public replay
  value/policy examples and terminal-result or observed-action labels.
- `neural.build_live_private_value_dataset` reconstructs per-turn own-side
  state from public replay evidence, creates terminal-result value targets,
  and currently emits the live-default `live-private-belief-v2` state vector.
- `neural.build_action_rank_dataset` reconstructs a state before each observed
  move/switch, enumerates legal candidates, marks the observed candidate, and
  currently emits `live-private-belief-v2` plus `legal-action-v3`.
- `neural.build_action_value_dataset` duplicates the same state for every
  candidate and derives value-delta targets from the existing v2 value
  checkpoint.

## Feature computation

- Public state is accumulated by
  `live_private_features.public_feature_vector_from_trajectory`.
- Reconstructed own state is produced by
  `build_live_private_value_dataset._reconstructed_private_state_for_side`.
- Opponent beliefs come from `live_opponent_beliefs.build_opponent_beliefs`
  using the protocol prefix.
- Tactical state comes from `tactical_state.build_tactical_state`.
- State vectors are built by
  `live_private_features.build_live_private_feature_vector`; it accepts an
  explicit feature version and already supports v7/3208D.
- Action vectors are built by `action_features`; v5/318D requires
  `build_action_feature_vector_v5` and optionally consumes normalized resolved
  impact data from `resolved_action_impact.resolve_action_impact`.

## Selection and storage limitations

The production builders import the default constants directly and expose no
config/environment switch for v7/v5. Their output paths remain under
`data/value` and `data/policy`. The action-rank/value builders append the full
state vector once per action candidate, so state vectors are duplicated.

The tiny benchmark therefore uses a separate diagnostic-only command. It reads
replay IDs and splits from `diagnostic_300`, selects v7/v5 explicitly, resolves
v5 immediate impacts through sim-core, and writes one state row per decision
plus separate candidate action rows and state-row indices. Production defaults,
builders, labels, and checkpoint paths are unchanged.

## Information boundary

The benchmark matches the existing replay-training assumption: protocol
prefixes and prefix-time opponent beliefs are used, while own-side reconstructed
state may be completed from information revealed later in the same public
replay. It does not read true hidden opponent teams or original private request
payloads. A future production-quality dataset should revisit that own-side
future-public-reveal assumption explicitly.
