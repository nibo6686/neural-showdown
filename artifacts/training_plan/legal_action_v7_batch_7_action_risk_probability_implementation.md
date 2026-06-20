# legal-action-v7 Batch 7 Action Risk/Probability Implementation

## Summary

Batch 7 appends an action-selection-time risk/probability/provenance slice after
the frozen 452D `legal-action-v7` batch-6 prefix.

- Previous prefix: 452 fields.
- Previous prefix fingerprint:
  `e3e39124cd24e3e27684306e3d401859083df65965e721eb3e5e8b89c48fcb4c`.
- New slice: 59 fields.
- New dimension: 511 fields.
- New fingerprint:
  `c03b2dd345f47dae0bffefc2a0d2b5731ee7d1eb8f2bf4cabc8d415d183149f5`.
- The first 452 names and values are preserved by focused prefix tests.

No materialization, training, checkpoint promotion, live default change, or live
path change occurred.

## Added Field Groups

Accuracy / miss / crit risk:

- `hit_chance_known`, `hit_chance`, `miss_chance`
- `on_hit_damage_available`, `expected_damage_includes_miss`
- `crit_chance_known`, `crit_chance`, `guaranteed_crit`
- `accuracy_context_partial`, `accuracy_context_unknown`

The new fields summarize existing resolved impact when available and otherwise
fall back to bundled Showdown metadata. They do not overwrite v5/v6 damage
fields. Guaranteed-critical moves are represented separately from ordinary crit
probability. Ordinary crit chance is represented as Gen 9 base 1/24 when no
high-crit or guaranteed-crit metadata applies.

Branch-dependent execution / threat pressure:

- Sucker Punch, Thunderclap, and Focus Punch mark opponent-action dependency.
- Fake Out and First Impression mark first-active-turn dependency.
- Pursuit is represented as target-switch / NatDex-future relevant.
- Payback marks target-switch power-boost pressure and same-turn/history
  dependency.
- Avalanche, Lash Out, Stomping Tantrum, and Temper Flare mark history/branch
  dependency.
- Psychic Terrain priority prevention is surfaced when current terrain and
  target grounding context make that risk relevant.
- Feint was checked against local Showdown Gen 9 data and is not encoded as an
  old-gen Protect-only failure branch; it remains a current-gen 30 BP priority
  attack with Protect-breaking side behavior.

These fields do not encode branch damage as guaranteed. They identify pressure
or uncertainty around the opponent/search branch.

Random-call / callable-pool summaries:

- Metronome computes a known format pool from bundled Showdown `metronome`
  flags.
- Sleep Talk summarizes current known move slots when available, excluding
  Sleep Talk itself and moves flagged unusable by Sleep Talk.
- Nature Power maps terrain to the called move when terrain context is present.
- Copycat and Mirror Move mark last-move dependency and fail closed without
  reliable last-move provenance.
- Assist is marked party- and format-rule-dependent. It is retained as
  NatDex/future-format relevant because local data contains the move, even if it
  is absent from Gen 9 Random Battles usage.
- Beat Up marks party dependency; Fickle Beam marks random-power uncertainty
  rather than a deterministic called move.

No sampled called move is encoded.

Multi-hit / sequential-hit summaries:

- Population Bomb and Triple Axel / Triple Kick mark sequential
  `multiaccuracy` miss-stop behavior.
- 2-5 hit moves use the Gen 5+ 35/35/15/15 distribution summary.
- Loaded Dice modifies 2-5 hit and Population Bomb summaries only when the
  current known item is Loaded Dice.
- Skill Link guarantees the maximum hit count only when the current known
  ability is Skill Link.
- Per-hit contact and per-hit power changes are marked from bundled Showdown
  metadata.

No sampled hit count is encoded.

Delayed / residual pressure summaries:

- Future Sight and Doom Desire create delayed pressure, target the opposing
  slot, record a two-turn timing summary, and explicitly defer future damage to
  rollout.
- Toxic, Leech Seed, Salt Cure, binding moves, and hazards summarize residual
  or side-pressure creation.
- Binding marks pressure but leaves duration unknown because the current state
  still lacks duration and Binding Band divisor provenance for rollout parity.

## Deferred Mechanics

Still deferred to state schema / rollout provenance:

- Natural sleep and Rest counters/ranges.
- Confusion counters/ranges and self-hit branch state.
- Future Sight replacement damage generation from landing-time target stats,
  typing, field, and source provenance.
- Binding source activity/effect, duration, and Binding Band divisor.
- Copycat/Mirror Move last-move provenance and Assist party callable pools in
  formats that support Assist.
- Full accuracy modifier provenance for abilities/items/evasion beyond the
  current static/weather summary.
- Search-node branch evaluation for same-turn opponent actions.

NatDex implication:

- Pursuit and Assist are encoded as future-format/NatDex-relevant provenance.
  They do not change Gen 9 Random Battles defaults.

## Validation

Passed:

- `trainer.tests.test_action_features_v7_action_risk_probability`: 16 tests.
- v7 non-Torch focused suite plus v5 action-feature regressions: 97 tests passed
  before the Torch import gate in `test_action_features_v6`.
- `trainer.tests.test_rollout_parity_harness`: 15 tests.

Blocked by local runtime:

- `trainer.tests.test_action_features_v7` and `trainer.tests.test_action_features_v6`
  import `neural.train_vnext_diagnostic`, which imports `torch`. The bundled
  Python runtime available in this Codex thread does not include Torch, so those
  checkpoint-guard modules cannot be imported here. The batch-7 schema tests
  still validate the new 511D fingerprint and the frozen 452D prefix directly.

`git diff --check` is recorded separately in the final task verification.

The diagnostic training gate remains closed.
