# diagnostic_1000_v7_v7_post_magic_bounce Dataset Quality Audit

Read-only audit of the fresh 1,000-battle post-Magic-Bounce v7/v7 artifact. No
training, checkpoint promotion, live/default change, schema/v8 work, old-gen
work, or push occurred.

## Headline comparison

| Metric | stale post-Ditto | post-Magic-Bounce |
| --- | ---: | ---: |
| Battles | 1,000 | 1,000 |
| Decision states | 80,644 | 80,635 |
| Candidates | 617,687 | 617,555 |
| Matched decisions | 80,601 | 80,594 |
| Unmatched decisions | 43 | 41 |
| Match rate | 99.9467% | 99.9492% |
| Explicit reflected nondecisions | 0 | 9 |

The corrected artifact removes the fixable Magic Bounce contamination and
leaves exactly the predicted 41-row Illusion/public-replay residual floor.

## Magic Bounce verification

All nine protocol move rows carrying explicit
`[from] ability: Magic Bounce` provenance are classified as `no_action_label`.
They include reflected Stealth Rock, Sticky Web, Thunder Wave, Stun Spore,
Will-O-Wisp, Sleep Powder, Toxic, and Defog events. They do not become
actor-selected rank labels or reflector moveset evidence.

The two original audit cases are resolved:

- `gen9randombattle-2589608300`: reflected Defog is absent from Hatterene's
  selected moveset evidence and the later genuine Psychic decision matches;
- `gen9randombattle-2594129364`: reflected Will-O-Wisp is a nondecision and
  produces no rank group.

Neither replay ID appears among the 41 residual unmatched groups.

## Residual audit

All 41 unmatched groups have zero positives and are explicitly quarantined in
`decision_skip_audit.jsonl`; no wrong candidate is labeled.

- 23 `move_missing_from_reconstructed_active_moves`;
- 18 `switch_target_missing_from_pre_action_legal_roster`;
- 39 train / 2 validation / 0 test;
- seven replay IDs, identical to the previously classified Illusion set.

Semantic distribution:

- 33 rows:
  `gen9randombattle-2590599887`, the known double-Zoroark battle;
- three known post-Ditto rows:
  `gen9randombattle-2593348981` t1/t2 and
  `gen9randombattle-2593283718` t3;
- five known duplicate-disguise switch rows:
  `gen9randombattle-2591253252`,
  `gen9randombattle-2592993362`,
  `gen9randombattle-2593993119`, and
  `gen9randombattle-2594630503` (two rows).

These are non-self-confirming public-replay Illusion ambiguities involving a
genuine same-team displayed-species copy. They cannot be safely attributed
without a rejected identity/HP heuristic. They are public-replay limitations,
not live-play limitations, and remain correctly excluded rather than
mislabeled.

Both displayed-species uncertainty state fields remain zero across all 80,635
states because ambiguous decisions are quarantined instead of leaking future
true identity into features.

## Tensor, schema, and coverage checks

- All numeric arrays are finite; no NaN or Inf.
- Candidate indices are in range.
- Rank labels equal the recorded observed-action indicator.
- 80,594 groups have exactly one positive; 41 have zero; none have more than
  one.
- Frozen state/action versions, dimensions, ordered names, and fingerprints
  match metadata and the embedded NPZ values exactly.
- Batch 7 (columns 452:511): 51/59 columns active across 370,755 candidate
  rows.
- Batch 8 (columns 511:552): 27/41 columns active across 98,203 candidate
  rows.
- Candidate mix: 38.85% move, 21.19% move-Tera, 39.96% switch.
- Exact 700/150/150 battle splits are preserved; state splits are
  64,455/7,853/8,327.
- All prior dataset hashes are unchanged.
- Live defaults remain v2/v3; no checkpoint or model file was produced.

## Gate decision

- Structural/materialization gate: **PASS**.
- Magic Bounce repair present in the generated artifact: **PASS**.
- Residual accounting and quarantine behavior: **PASS**.
- Dataset-quality gate for a separately approved rank-only diagnostic:
  **PASS**.

This artifact is the recommended v7/v7 1,000-battle rank-diagnostic baseline.
That conclusion does not authorize training. The next step is a read-only
trainer `--validate-only` run using the updated draft config, followed by
separate explicit approval before any rank-only training command.
