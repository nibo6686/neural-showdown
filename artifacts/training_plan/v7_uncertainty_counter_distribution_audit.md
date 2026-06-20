# v7 Uncertainty, Counter, and Distribution Audit

## Scope

This is a design/audit pass before any `legal-action-v7` batch 7 implementation.
It does not add fields, materialize data, train, promote checkpoints, or change
live defaults.

Principle: encode only public or legally inferable information. Do not encode
hidden sampled future values such as a natural sleep duration, confusion
duration, future crit roll, or random called move. When exact future execution is
not knowable, encode ranges, probabilities, distributions, and provenance.

Current anchors:

- `legal-action-v7` batch 6 is 452D.
- Rollout parity is 33 fixtures: 29 PASS / 0 FAIL / 4 GAP.
- v7 already has typed status/stat, volatile, item, priority/timing, HP, and
  field/side slices.
- v5/v6 impact fields already expose hit chance, accuracy-known, damage roll
  range, KO chance, and guaranteed-critical inclusion for specific moves.

## Current Handling Summary

Already represented:

- Static move accuracy as `accuracy_norm`.
- Resolved impact hit chance and `impact_accuracy_known`.
- On-hit damage roll range and `impact_damage_uncertainty`.
- `impact_damage_includes_crit` for guaranteed-critical moves currently handled
  by the calc path (`Flower Trick`, `Wicked Blow`).
- Typed status/stat chances in v7 batch 1.
- Typed volatile chances in v7 batch 2, with confusion represented as a typed
  status-like key in batch 1.
- Priority/timing context for Grassy Glide, Prankster, Triage, Gale Wings,
  Psychic Terrain priority block, charge turns, and delayed Future Sight-style
  moves.
- Coarse fail-closed handling for multi-hit families, conditional execution,
  Beat Up, Fickle Beam, and some dynamic accuracy.
- Rollout transition parity for hazards, residuals, Future Sight/Doom Desire
  scheduling, selected prevention callbacks, and Grassy Terrain healing.

Missing or under-modeled:

- Sleep and confusion counters/ranges.
- Rest sleep provenance versus ordinary sleep.
- Crit probability for ordinary moves.
- Risk-adjusted expected damage including miss/crit, distinct from on-hit
  expected damage.
- Accuracy-modifier provenance beyond a small weather-dependent subset.
- Branch-conditioned success/damage for opponent-action moves.
- Random-call move pools and distribution summaries.
- Multi-hit distributions, sequential accuracy stop rules, Loaded Dice, Skill
  Link, and per-hit effects.
- General delayed-damage target-specific landing damage generation.

## Category 1 - Sleep Counters and Rest

Current handling:

- State can expose major status `slp`.
- v7 action features can encode a move that causes sleep.
- Local Showdown source sets ordinary sleep duration as a hidden random
  `startTime`/`time` in the sleep condition; Rest then overwrites both to `3`,
  producing the fixed Rest sleep behavior in Gen 9.
- Current state/action features do not distinguish Rest sleep from ordinary
  sleep, do not encode sleep turns elapsed, and do not expose legal wake ranges.

Missing:

- `sleep_from_rest`
- `sleep_turns_elapsed`
- `sleep_can_wake_this_turn`
- `sleep_must_wake_by_turn`
- `sleep_remaining_min`
- `sleep_remaining_max`
- `sleep_hidden_duration_unknown`
- Sleep Talk callable-pool support.

Placement:

- State features: active sleep provenance, elapsed turns, public min/max
  remaining range, Rest-vs-ordinary provenance, hidden-duration-unknown flag.
- Action features: Rest sets fixed sleep provenance and HP recovery; Sleep Talk
  is a random-call action whose callable pool depends on known moves and sleep
  state.
- Rollout/search: decrement public/possible sleep counters without sampling a
  hidden duration into features. Search can branch over legal wake probabilities
  when modeling natural sleep.

No-leak rule:

- Do not store Showdown's sampled `statusState.time` for natural sleep unless it
  became public through execution. Store legal ranges and elapsed information.

Gen 9 Randbats relevance:

- High. RestTalk sets and sleep moves appear often enough that confusing Rest's
  fixed duration with ordinary sleep can change action value.

NatDex/future relevance:

- High. Sleep mechanics and Sleep Talk callable exclusions differ across older
  generations/formats and need format-scoped tests.

## Category 2 - Confusion Counters

Current handling:

- Tactical state tracks `confusion` as a volatile boolean.
- v7 typed effect slices can represent confusion chance.
- Local Showdown source uses hidden confusion duration `random(min, 6)` where
  ordinary confusion starts at 2-5 turns and Axe Kick starts at 3-5; each move
  attempt decrements the hidden time, then there is a 33% self-hit chance if it
  remains active.
- Current features do not expose elapsed turns, legal remaining range, or the
  33% self-hit chance as state/rollout pressure.

Missing:

- `confusion_turns_elapsed`
- `confusion_can_end_this_turn`
- `confusion_must_end_by_turn`
- `confusion_remaining_min`
- `confusion_remaining_max`
- `confusion_hidden_duration_unknown`
- `confusion_self_hit_chance`

Placement:

- State features: active confusion, source class if public/inferable, elapsed
  turns, min/max remaining range, hidden-duration-unknown.
- Action features: moves that inflict confusion should keep typed probability;
  no future duration sample.
- Rollout/search: branch over end-now versus continue and self-hit versus move,
  using public ranges/probabilities.

No-leak rule:

- Do not encode the sampled `volatiles.confusion.time`.

Gen 9 Randbats relevance:

- Medium. Confusion is less central than sleep but important for moves like
  Hurricane, Dynamic Punch, Axe Kick, Outrage-family fatigue, and item/ability
  interactions.

## Category 3 - Accuracy, Crit, and Miss-Risk Distribution

Current handling:

- Static move accuracy is encoded as `accuracy_norm`.
- Resolved impact exposes `impact_hit_chance` and `impact_accuracy_known`.
- Weather-dependent accuracy for Blizzard/Thunder/Hurricane/Bleakwind Storm is
  handled from observable weather.
- Smogon calc output gives on-hit roll distribution; `average_percent`,
  `min_percent`, and `max_percent` are on-hit damage, not miss-adjusted expected
  damage.
- `impact_damage_includes_crit` is true for guaranteed-critical moves whose crit
  is baked into the calc result.
- Ordinary crit chance is not exposed.
- Accuracy context from Gravity, No Guard, Lock-On, Compound Eyes, Bright
  Powder, Wide Lens, evasion/accuracy stages, and similar effects is not
  represented as explicit provenance.

Missing:

- `on_hit_damage_expected`
- `expected_damage_including_miss`
- `crit_chance`
- `guaranteed_crit`
- `accuracy_context_known`
- `accuracy_context_partial`
- Accuracy modifier provenance bits.

Placement:

- Action features: append probability/distribution fields because they describe
  the candidate action's risk and expected value.
- State features: public accuracy/evasion stages, Gravity, Lock-On/No Guard-like
  guarantees, item/ability knownness/suppression relevant to accuracy.
- Rollout/search: sample or branch hit/miss/crit outcomes; do not collapse all
  into deterministic immediate damage.

No-leak rule:

- Do not encode actual future hit/miss/crit outcomes from replay labels.

Gen 9 Randbats relevance:

- High. Many good choices depend on whether a lower-accuracy move's upside is
  worth the risk.

## Category 4 - Branch-Dependent Execution and Threat Pressure

Current handling:

- Conditional moves such as Sucker Punch, Thunderclap, Focus Punch, Fake Out,
  First Impression, Payback, Avalanche, Lash Out, Stomping Tantrum, and Temper
  Flare fail closed for immediate damage rather than claiming wrong-exact
  current damage.
- v7 timing/priority fields cover priority and some timing, but not the branch
  condition that makes the move succeed or double.
- Tactical state has recent failed/missed/protected counters and some last-move
  failure information, but these are coarse and not tied to full branch
  provenance.
- Local bundled Showdown source confirms Feint in Gen 9 is 30 BP, +2 priority,
  `breaksProtect: true`, and does not have the older "fails unless target is
  protecting" behavior in its move definition.

Missing:

- `may_fail_due_to_opponent_action`
- `may_fail_due_to_active_turn`
- `may_fail_due_to_target_switch`
- `succeeds_if_target_attacks`
- `succeeds_if_target_switches`
- `power_boost_if_target_switches`
- `branch_damage_known_if_condition_true`
- `branch_condition_hidden_now`
- `threat_pressure_not_current_damage`

Placement:

- Action features: branch condition and pressure fields.
- State features: first-active-turn count/provenance, prior move failure,
  whether target is queued/known to attack only inside explicit search nodes,
  stats-lowered-this-turn, damaged-by-target-this-turn.
- Rollout/search: evaluate branches after opponent action is known or inside
  two-ply branch evaluation. The feature vector should not assume one branch.

No-leak rule:

- Replay future opponent action must not be encoded into pre-action candidate
  features. Search can evaluate hypothetical opponent branches separately.

Gen 9 Randbats relevance:

- High for Sucker Punch, Thunderclap, Fake Out, First Impression, Payback,
  Avalanche, Stomping Tantrum, and Temper Flare. Pursuit is NatDex/older-format
  only.

## Category 5 - Random-Call Moves and Callable Pools

Current handling:

- Random-call moves are not summarized as distributions.
- Some random or party-dependent families are fail-closed or coarse: Beat Up is
  fail-closed because it depends on party attack stats; Fickle Beam is
  fail-closed because random double power is collapsed otherwise.
- v7 typed status/stat parsers preserve probabilities for ordinary secondaries,
  but do not compute callable pools for Metronome/Sleep Talk/Copycat/Nature
  Power.
- Bundled Showdown source shows Metronome samples from legal move definitions
  flagged `metronome`; Sleep Talk samples from user's known move slots excluding
  moves with `nosleeptalk`/charge restrictions; Copycat depends on public
  `lastMove`; Nature Power maps deterministically from terrain in Gen 9 but is
  Past/nonstandard.
- Assist is not current Gen 9, but NatDex/future support would need party-move
  pool modeling.

Missing:

- `random_call_move`
- `callable_pool_known`
- `callable_count`
- `callable_damaging_count`
- `callable_status_count`
- `callable_avg_base_power`
- `callable_has_priority`
- `callable_has_phazing`
- `callable_has_sleep`
- `callable_has_status`
- `callable_pool_depends_on_party`
- `callable_pool_depends_on_last_move`
- `callable_pool_depends_on_format_rules`
- `callable_distribution_unknown`

Placement:

- Action features: callable-pool summary for the candidate move when the pool is
  public/inferable.
- State features: known move slots, last successful callable move, sleep state,
  party move knownness/provenance.
- Rollout/search: branch over callable distribution when pool is known; fail
  closed or encode distribution unknown when hidden party information controls
  the pool.

No-leak rule:

- Do not encode the actual move sampled by Metronome/Sleep Talk/Assist before
  it occurs.

Gen 9 Randbats relevance:

- Medium for Sleep Talk and Metronome-like behavior; low for Assist/Nature Power
  in strict Gen 9 Randbats. High NatDex relevance for Assist-abuse recognition.

## Category 6 - Multi-Hit and Sequential-Hit Distributions

Current handling:

- Multi-hit moves such as Bullet Seed, Rock Blast, Icicle Spear, Tail Slap,
  Scale Shot, Dragon Darts, Dual Wingbeat, Surging Strikes, Tachyon Cutter,
  Population Bomb, and Triple Axel fail closed instead of emitting wrong single
  expected/min/max damage.
- Static move metadata can see `multihit`, `multiaccuracy`, and flags, but v7
  does not expose distribution details.
- Bundled Showdown source confirms Population Bomb is `multihit: 10` with
  `multiaccuracy: true`; Triple Axel is `multihit: 3`, `multiaccuracy: true`,
  and has per-hit power ramping via `basePowerCallback`.
- Loaded Dice removes `multiaccuracy` and changes multi-hit behavior in the
  battle action loop; Skill Link sets array multi-hit moves to their max and
  removes `multiaccuracy`.

Missing:

- `multihit_min`
- `multihit_max`
- `multihit_expected`
- `multihit_distribution_known`
- `sequential_accuracy_stops_on_miss`
- `per_hit_accuracy`
- `per_hit_power_changes`
- `loaded_dice_modified`
- `skill_link_guaranteed`
- `contact_per_hit`
- `per_hit_secondary_or_contact_relevant`

Placement:

- Action features: distribution summary and modifier provenance.
- State features: user item/ability knownness, item/ability suppression, contact
  punishers if known.
- Rollout/search: branch or compute expected distribution over hit count,
  sequential miss-stop, per-hit contact, and per-hit secondary effects.

No-leak rule:

- Do not encode the sampled hit count from the replay before execution.

Gen 9 Randbats relevance:

- High. Population Bomb, Loaded Dice users, Scale Shot, Bullet Seed, Icicle
  Spear, Triple Axel, and contact-per-hit interactions can dominate decisions.

## Category 7 - Residual and Delayed-Effect Pressure

Current handling:

- Rollout parity now passes entry hazards, Toxic, poison, burn, Leech Seed, Salt
  Cure, Sandstorm, Grassy Terrain healing, Future Sight/Doom Desire scheduling,
  and selected prevention callbacks.
- Delayed queue stores target slot, source identity, schedule/landing turn, and
  target-specific damage when supplied.
- Future Sight replacement damage remains GAP when target-specific landing
  damage is unavailable.
- Binding remains GAP because current state lacks source activity/effect,
  duration, and Binding Band divisor.
- v7 action features mark delayed future damage and typed field/side effects,
  but state features do not yet expose pending delayed pressure and residual
  provenance broadly.

Missing:

- `delayed_pressure_active`
- `delayed_pressure_scheduled`
- `turns_until_landing`
- `delayed_target_side`
- `delayed_target_slot`
- `future_damage_deferred_to_rollout`
- `future_damage_target_specific_known`
- `residual_applied_type`
- `residual_damage_rule_known`
- `residual_source_known`
- `residual_duration_known`

Placement:

- State features: pending delayed attacks, residual volatiles with source and
  duration provenance, target slot, terrain/weather/hazard state.
- Action features: whether a move schedules delayed pressure, applies a known
  residual, or depends on source/duration provenance.
- Rollout/search: compute actual future/residual damage only when target and
  source state is sufficiently known.

No-leak rule:

- Do not encode future landing damage against an unknown replacement unless the
  target-specific resolver has all public/inferable inputs.

Gen 9 Randbats relevance:

- High. Hazards, Toxic, Leech Seed, Salt Cure, Future Sight, and binding are all
  important pressure mechanics.

## Recommended v7 Batch 7 Field List

Batch 7 should be an append-only uncertainty/execution-provenance slice after
the current 452D prefix. Suggested action fields:

1. `risk_on_hit_damage_expected`
2. `risk_expected_damage_including_miss`
3. `risk_hit_chance`
4. `risk_hit_chance_known`
5. `risk_accuracy_context_known`
6. `risk_accuracy_context_partial`
7. `risk_crit_chance`
8. `risk_guaranteed_crit`
9. `risk_branch_may_fail_opponent_action`
10. `risk_branch_may_fail_active_turn`
11. `risk_branch_may_fail_target_switch`
12. `risk_branch_succeeds_if_target_attacks`
13. `risk_branch_succeeds_if_target_switches`
14. `risk_branch_power_boost_possible`
15. `risk_branch_damage_known_if_true`
16. `risk_random_call_move`
17. `risk_callable_pool_known`
18. `risk_callable_count_norm`
19. `risk_callable_damaging_frac`
20. `risk_callable_status_frac`
21. `risk_callable_avg_base_power_norm`
22. `risk_callable_has_priority`
23. `risk_callable_has_phazing`
24. `risk_callable_has_sleep_or_status`
25. `risk_callable_depends_on_party`
26. `risk_callable_depends_on_last_move`
27. `risk_callable_depends_on_format`
28. `risk_callable_distribution_unknown`
29. `risk_multihit_min_norm`
30. `risk_multihit_max_norm`
31. `risk_multihit_expected_norm`
32. `risk_multihit_distribution_known`
33. `risk_sequential_accuracy_stops_on_miss`
34. `risk_per_hit_accuracy_known`
35. `risk_per_hit_power_changes`
36. `risk_loaded_dice_modified`
37. `risk_skill_link_guaranteed`
38. `risk_contact_per_hit`
39. `risk_delayed_pressure_scheduled`
40. `risk_future_damage_deferred_to_rollout`
41. `risk_residual_damage_rule_known`
42. `risk_residual_duration_known`

Recommended state fields should be designed separately because they belong in
`live-private-belief-vNext`, not action v7:

- sleep active/from Rest/elapsed/can-wake/must-wake/min-max/hidden-duration
  unknown;
- confusion active/elapsed/can-end/must-end/min-max/hidden-duration
  unknown/self-hit chance;
- active-turn count/exactness for first-turn moves;
- previous move result exactness for Stomping Tantrum/Temper Flare;
- same-turn branch state inside search nodes only;
- pending delayed attack side/slot/turns/source/damage-provenance;
- binding source/effect/duration/divisor provenance;
- callable pool provenance for party-move/last-move dependent moves.

## Recommended Rollout Tests

Add deterministic Showdown-backed fixtures for:

- Rest fixed two-turn sleep versus ordinary sleep range behavior.
- Natural sleep no-leak: state exposes range/elapsed, not sampled duration.
- Sleep Talk callable pool from known move slots.
- Confusion duration range and 33% self-hit branch without sampled duration
  leakage.
- Accuracy modifiers: Gravity, No Guard, Lock-On, Compound Eyes, Wide Lens,
  Bright Powder/evasion where represented.
- Ordinary crit probability versus guaranteed crit.
- Sucker Punch and Thunderclap succeed/fail based on opponent branch.
- Fake Out and First Impression first-active-turn success/fail.
- Payback/Avalanche/Lash Out/Stomping Tantrum/Temper Flare branch boosts.
- Feint breaking Protect in Gen 9.
- Metronome and Sleep Talk callable pool summaries.
- Population Bomb sequential miss-stop, Triple Axel power ramp, Loaded Dice,
  Skill Link, and per-hit contact.
- Future Sight replacement damage resolver only when target-specific
  landing-time state is present.
- Binding residual only with source/effect/duration/divisor provenance.

## Recommended No-Leakage Tests

- Natural sleep feature vectors are identical for two Showdown seeds that sample
  different hidden sleep durations but have the same public history.
- Confusion feature vectors are identical for hidden duration variants with the
  same public elapsed history.
- Metronome/Sleep Talk/Assist features do not change based on the sampled called
  move before it is revealed.
- Multi-hit candidate features do not encode sampled hit count.
- Accuracy/crit features do not encode replay future hit/miss/crit outcomes.
- Future Sight pending-state features do not encode replacement damage unless
  the landing target and resolver inputs are public/inferable.
- Branch-dependent action features do not encode the opponent's replay-future
  action outside a search branch node.

## Recommended Next Implementation Batch

Do not jump directly to all execution provenance. Recommended next batch:

1. Add v7 batch 7 action-risk/probability fields for hit/miss/crit,
   branch-dependent execution flags, random-call pool summaries where public,
   and multi-hit distribution summaries.
2. Add a separate state-schema design for sleep/confusion counters and pending
   delayed/residual provenance. Do not mix these into action v7 unless they are
   candidate-action summaries.
3. Add no-leakage tests before materialization.
4. Add rollout fixtures for Rest/sleep, confusion, Feint, branch moves,
   callable pools, and multi-hit distributions before any training.

The gate remains closed until these representations are implemented, tested,
and reviewed. No materialization or training is approved by this audit.
