# diagnostic_1000_v7_v7_post_ditto Dataset Quality Audit

Read-only audit of the fresh 1,000-battle v7/v7 artifact. No training,
checkpoint promotion, live/default change, schema/v8 work, old-gen work, or
push occurred.

## Headline comparison

| Metric | post-Ditto 300 | post-Ditto 1000 |
| --- | ---: | ---: |
| Battles | 300 | 1,000 |
| Decision states | 25,235 | 80,644 |
| Candidates | 197,449 | 617,687 |
| Matched decisions | 25,232 | 80,601 |
| Unmatched decisions | 3 | 43 |
| Match rate | 99.99% | 99.9467% |
| Initial deployments skipped | 600 | 2,000 |
| Displayed-species-uncertain states | 0 | 0 |

The larger artifact remains structurally excellent, but it surfaces one new
fixable Magic Bounce category that the 300-battle sample did not contain.

## Residual audit

All 43 unmatched action groups have zero positives and are explicitly listed
in `decision_skip_audit.jsonl`. They are excluded from rank training; none is
forced onto a wrong candidate and no group has multiple positives.

The materializer's mechanical details are:

- 25 `move_missing_from_reconstructed_active_moves`;
- 18 `switch_target_missing_from_pre_action_legal_roster`;
- by parsed kind: 24 move / 1 move-Tera / 18 switch;
- by split: 40 train / 2 validation / 1 test.

Semantic triage:

### Quarantined public-replay Illusion ambiguity: 41

- The known post-Ditto floor contributes the same three rows:
  `gen9randombattle-2593348981` t1/t2 and
  `gen9randombattle-2593283718` t3.
- `gen9randombattle-2590599887` contributes 33 rows. It is a rare
  double-Zoroark battle in which both sides repeatedly disguise as genuine
  same-team displayed species. The repeated 219-HP stints, real copies, and
  later Zoroark reveals prove Illusion globally but do not safely attribute
  each earlier non-self-confirming stint without the rejected HP-signature
  heuristic.
- Five further switch rows are the same ambiguity pattern:
  `gen9randombattle-2591253252` Beartic,
  `gen9randombattle-2592993362` Slowking,
  `gen9randombattle-2593993119` Zebstrika, and
  `gen9randombattle-2594630503` Basculin/Charizard. Later `replace` or direct
  Zoroark events confirm the disguise while a genuine displayed-species copy
  prevents safe retrospective attribution.

These 41 rows are public-replay limitations, not live-play limitations. They
remain correctly quarantined rather than mislabeled. Both
`own_active_displayed_species_uncertain` and
`opponent_active_displayed_species_uncertain` remain 0/80,644 because ambiguous
rows are skipped instead of leaking true identity into features.

### New fixable Magic Bounce category: 2

1. `gen9randombattle-2589608300` t24 p2 `move: Psychic`: an earlier reflected
   `Defog` was attributed to Hatterene as if it were a learned/selected move.
   The four-move reconstruction then contains illegal `Defog` and crowds out
   the actual `Psychic`.
2. `gen9randombattle-2594129364` t2 p2
   `move_tera: Will-O-Wisp`: the protocol row is a Magic Bounce reflection
   (`[from] ability: Magic Bounce`), not a player decision by Hatterene, but the
   label parser treats it as actor-chosen.

The rows themselves are skipped, but the reflected-Defog case can also pollute
unchosen candidate sets for surrounding Hatterene decisions. This is a
training-data quality issue, not merely two missing positives. It should be
fixed by preventing reflected moves from becoming actor-selected labels or
own moveset evidence, then covered by focused regression tests.

## Schema and feature activity

- State/action names, versions, dimensions, and fingerprints exactly match the
  frozen v7/v7 schema.
- The first 331 action columns retain the v6 prefix by schema validation.
- Batch 7 (columns 452:511): 51/59 columns active; 370,861 candidate rows have
  at least one nonzero Batch-7 value.
- Batch 8 (columns 511:552): 27/41 columns active; 98,207 candidate rows have
  at least one nonzero Batch-8 value.
- The 300-battle artifact had 50/59 Batch-7 active columns across 122,036 rows
  and 25/41 Batch-8 active columns across 30,126 rows. The larger artifact
  increases both coverage and volume.
- Candidate mix is 38.85% move, 21.19% move-Tera, and 39.96% switch.
- No numeric array contains NaN or Inf.

## Manifest and split quality

- 1,000 unique Gen 9 Random Battles replays.
- Exact 700/150/150 battle-level splits and no cross-split battle leakage.
- Unsupported 24-vs-24 and 8-vs-8 replays were removed before materialization.
- Selection preserves enrichment: 924 battles contain Tera actions, 1,546 Tera
  actions total, and 20,651 switch decisions, while keeping switch share near
  the natural distribution.
- Source snapshot replay IDs exactly match the manifest in order, and manifest
  SHA-256 is recorded consistently in metadata/report/snapshot.

## Gate decision

- Structural/materialization gate: **PASS**.
- Residual accounting and quarantine behavior: **PASS**.
- Dataset-quality gate for rank-only training: **BLOCKED** on the two-row
  Magic Bounce category because reflected moves can contaminate legal candidate
  reconstruction.

Recommended next step: fix reflected-move decision/moveset attribution, add
focused Magic Bounce regression tests for both `Defog` and `Will-O-Wisp`,
explicitly approve a resume-safe rematerialization into a new superseding path
or a clean rebuild of this not-yet-trained artifact, then repeat this audit.
Do not train from this artifact in its current form.

## Post-audit Magic Bounce source-fix update

The reflected-move attribution bug is now fixed in source and covered by
targeted replay-backed tests
(`magic_bounce_reflected_move_attribution_fix_report.md`). Explicit
`[from] ability: Magic Bounce` move rows are no longer treated as
actor-selected labels or reflector moveset evidence.

The two audited battles now pass targeted recomputation:

- reflected Defog is absent from Hatterene's moveset and later Psychic matches;
- reflected Will-O-Wisp produces no actor-choice label.

This generated artifact was **not** rematerialized and remains stale: it still
contains 43 unmatched rows and at least one false-positive reflected decision.
Expected unmatched count after a future approved rematerialization is **41**,
leaving only the currently identified quarantined Illusion ambiguities.
Rank-only training remains blocked until rematerialization and re-audit.
