# legal-action-v7 Batch 8 Forced Decision / Secondary Chance Implementation

## Summary

Batch 8 appends a forced-decision, replacement, item-trigger, and
secondary-chance-provenance slice after the frozen 511D `legal-action-v7`
batch-7 prefix.

- Previous prefix: 511 fields.
- Previous prefix fingerprint:
  `c03b2dd345f47dae0bffefc2a0d2b5731ee7d1eb8f2bf4cabc8d415d183149f5`.
- New slice: 41 fields.
- New dimension: 552 fields.
- New fingerprint:
  `956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7`.
- Focused tests verify the first 511 names and values match a reconstructed
  batch-7 vector.

No materialization, training, checkpoint promotion, live default change, or live
path change occurred.

## Forced Decisions and Replacement Provenance

Self-pivot fields preserve the clicked action as Showdown presents it. A
candidate remains `U-turn`, `Volt Switch`, `Flip Turn`, `Parting Shot`,
`Teleport`, or `Chilly Reception`; no fake "pivot into replacement" action is
created.

Added representation:

- damaging pivots mark hit-required, after-damage, follow-up replacement
  decision, and possible miss/immunity/protection branch;
- `Parting Shot` marks pivot-after-stat-drop and follow-up replacement;
- `Teleport` and `Chilly Reception` mark replacement pressure without a hit
  requirement.

Self-KO / sacrifice fields cover:

- guaranteed self-KO: `Explosion`, `Self-Destruct`, `Misty Explosion`;
- self-KO if successful: `Memento`, `Healing Wish`, `Lunar Dance`,
  `Final Gambit`;
- healing-wish-style slot effects: `Healing Wish`, `Lunar Dance`;
- stat-drop sacrifice: `Memento`;
- damage/HP-cost sacrifice provenance: `Final Gambit`, `Steel Beam`,
  `Mind Blown`, `Chloroblast`.

HP-cost moves only mark a forced replacement when current HP provenance supports
that the cost can KO the user.

Target forced-switch / phazing fields cover:

- `Roar`, `Whirlwind`, `Dragon Tail`, `Circle Throw`;
- hit-required phazing for `Dragon Tail` / `Circle Throw`;
- negative priority for `Roar` / `Whirlwind`;
- possible Substitute blocking for hit-based phazing.

Item-trigger switch fields cover known item states only:

- own known `Eject Pack` on self-stat-drop moves;
- target known `Eject Button` on hit/effect moves;
- target known `Red Card` on damaging moves.

Unknown item state does not fake an item trigger. It is only surfaced as branch
unknown for item-relevant moves such as self-stat-drop moves where Eject Pack
would matter.

## Secondary Chance Provenance

Batch 8 preserves the existing typed status/stat/volatile slices and adds a
separate provenance layer for base and modified secondary chances:

- base chance from bundled Showdown move metadata;
- modified chance;
- Serene Grace modifier;
- Shield Dust / Covert Cloak blocking provenance;
- Sheer Force secondary removal provenance;
- separate modified flinch, status, and stat-drop chance summaries.

Rules implemented:

- `Iron Head` remains 30% flinch with no known modifier.
- Known active `Serene Grace` doubles applicable secondary chances, e.g.
  `Iron Head` 30% -> 60%, `Body Slam` 30% paralysis -> 60%.
- Known target `Shield Dust` or `Covert Cloak` marks blocking provenance and
  zeros the modified secondary chance.
- Known user `Sheer Force` marks secondary-removal provenance and zeros the
  modified secondary chance.
- Missing ability/item provenance does not invent blockers or modifiers.

## Format Scope

The current implementation is Gen 9 Random Battles scoped. Format-sensitive
behavior is kept data-driven where practical:

- Feint is not modeled as old-gen Protect-only conditional; local Gen 9
  Showdown data treats it as a 30 BP priority attack with Protect-breaking side
  behavior.
- Pursuit and Assist remain future-format / NatDex-relevant provenance from
  earlier slices; batch 8 does not implement NatDex or old-generation rules.
- Future adapters should route generation-sensitive behavior through
  Showdown/sim-core format data instead of promoting Gen 9 assumptions to
  universal rules.

## Deferred Mechanics

Still deferred to future state-schema / rollout / search work:

- exact forced replacement choice modeling after a pivot or self-KO;
- search-node handling for target switch, Red Card, and Eject Button branches;
- full ability/item suppression interactions for secondary blockers/modifiers;
- Magic Bounce / Good as Gold generalized prevention provenance;
- pending delayed attack and binding source/duration provenance;
- NatDex / old-generation behavior for Pursuit, Assist, Natural Gift, and
  generation-specific Feint rules.

## Validation

Passed:

- `trainer.tests.test_action_features_v7_forced_decision_secondary_chance`:
  12 tests.
- `trainer.tests.test_action_features_v7_action_risk_probability`: 16 tests.
- Non-Torch v7 focused suite plus v5 action-feature regressions: 109 tests.
- `trainer.tests.test_rollout_parity_harness`: 15 tests.

Known local runtime limitation:

- The bundled Python runtime in this Codex thread does not include Torch, so
  Torch-importing checkpoint guard modules in `test_action_features_v7` /
  `test_action_features_v6` remain un-runnable here. Prefix integrity is
  directly covered by the focused schema tests.

`git diff --check` is recorded separately in final verification. The diagnostic
training gate remains closed.
