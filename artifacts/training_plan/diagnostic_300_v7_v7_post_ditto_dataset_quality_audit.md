# diagnostic_300_v7_v7_post_ditto Dataset Quality Audit

Read-only audit of the fresh post-Ditto v7/v7 dataset
(`artifacts/training_plan/datasets/diagnostic_300_v7_v7_post_ditto`). No training,
rematerialization beyond the one approved run, checkpoint promotion,
live-default/live-bot change, schema change, push, or v8/old-gen work occurred.

## Headline

| Metric | post_illusion | post_ditto (this run) |
| --- | ---: | ---: |
| Decision states | 25,235 | 25,235 |
| Matched decisions | 25,220 | 25,232 |
| Unmatched decisions | 15 | **3** |
| Match rate | 99.94% | **99.99%** |
| Unmatched by kind | move 15 | **move 3** |
| Candidates | 197,429 | 197,449 |
| Displayed-species-uncertain states | 0 | 0 |

The Ditto re-transform fix removed 12 of the 15 post-Illusion residuals (the 11
Ditto re-transform rows + the 1 Struggle row). Only the 3 irreducible
non-self-confirming Illusion rows remain — matching the expected residual count.

## Documented fixes confirmed in the materialized artifact

Each is **absent** from `decision_skip_audit.jsonl` (i.e. matched in the dataset):

- **Ditto re-transform-into-same-species** (this task's fix):
  - `gen9randombattle-2590922693` t92/93/94 `Sacred Fire`: matched
  - `smogtours-gen9randombattle-929481` t68/69/70/71 `Energy Ball`: matched
  - `gen9randombattle-2594584178` t25/26/27/28 `Outrage`: matched
- **Struggle PP-exhaustion** — `smogtours-gen9randombattle-929481` t65: matched
- **Prior Ditto/Imposter Transform** — `gen9randombattle-2589571474` t20
  `Thunder Wave`: matched; future `Leaf Blade` contamination absent.
- **Actor-private Zoroark/Illusion** — `gen9randombattle-2591469202` t1
  `Sludge Bomb`, duplicate Houndstone→`Zoroark` switches t21/23/25
  (`gen9randombattle-2591404793`): matched.

`scripts/recompute_v7_v7_residual_unmatched_from_replays.py` independently confirms
22 cases → 19 matched / 3 unmatched, `all_as_expected = True`.

## The 3 residual unmatched rows (all expected, all explicit skips)

| Replay | Turn | Side | Move | True species | Category |
| --- | ---: | --- | --- | --- | --- |
| `gen9randombattle-2593348981` | 1 | p1 | Will-O-Wisp | Zoroark-Hisui | non-self-confirming Illusion |
| `gen9randombattle-2593348981` | 2 | p1 | Poltergeist | Zoroark-Hisui | non-self-confirming Illusion |
| `gen9randombattle-2593283718` | 3 | p1 | Hyper Voice | Zoroark-Hisui | non-self-confirming Illusion |

These are the irreducible cases: the disguised entity switched out **before any
`replace` reveal in that stint**, and the player also owns a genuine copy of the
displayed species (real Avalugg max HP 310 vs disguised 219; real Gumshoos max HP
321 vs disguised 219). The stints do not self-confirm, so the true species cannot
be safely attributed without fragile HP-signature entity tracking that risks
misattributing the real Pokemon. They remain explicit quarantined skips — not
leaked, not forced, no wrong labels. This is a public-replay attribution
limitation, not a live-play one (live play knows its own true side from the
Showdown request).

## Other quality signals

- **Displayed-species uncertainty:** `own_active_displayed_species_uncertain` and
  `opponent_active_displayed_species_uncertain` are 0/25,235 — no regression.
- **No-leakage preserved:** the Ditto/Illusion reconstruction only affects own-side
  rows; the 3 residuals are excluded, never injected as wrong labels; copied
  opponent moves are not backfilled into Ditto's global moveset.
- **Candidate/state distribution:** 197,449 candidates / 25,235 states ≈ 7.82 avg;
  matched-by-kind move 18,552 / move_tera 431 / switch 6,249. Candidate count rose
  marginally vs post_illusion (197,429) because the now-matched Ditto/Struggle
  decisions contribute their reconstructed move candidates.
- **v6 prefix integrity:** the first 331 action-feature names are byte-identical to
  `diagnostic_300_v7_v7_post_illusion` (and the full 552 action names + 3208 state
  names are identical), and `embedded_names_match_schema_and_metadata` passed; v6
  prefix columns are populated across all rows.
- **Batch 7/8 activity:** batch-7 (dims 452:511) 50/59 active columns over 122,036
  candidate rows; batch-8 (dims 511:552) 25/41 active columns over 30,126 rows.
- **Old datasets untouched:** `.npz` sha256 prefixes for `diagnostic_300_v7_v7`,
  `diagnostic_300_v7_v7_corrected`, `diagnostic_300_v7_v7_post_illusion`,
  `diagnostic_300_v7_v6`, `diagnostic_300_v7_v5`,
  `diagnostic_1000_action_rank_v7_v5` are byte-identical to the pre-run snapshot.

## Expected vs actual residual count

Expected 3; actual **3**. Exactly the irreducible non-self-confirming Illusion
stints. No discrepancy.

## Gate decision

- The dataset is structurally valid (all 18 checks passed), schema/fingerprint
  exact, splits correct, 99.99% matched with the 3 residuals all explicit,
  explained, irreducible skips (no wrong labels, no forced rows).
- This is the cleanest v7/v7 artifact to date and is the recommended baseline for a
  first **tiny smoke / plumbing training run** if explicitly approved — the 0.012%
  excluded rows are irreducible public-replay quarantines that inject no error.
- It is a sound quality baseline for diagnostic/plumbing purposes; the 3 residuals
  are not fixable without leaking hidden true species or HP-signature heuristics, so
  they are the accepted floor for this replay pool.
- Training, checkpoint promotion, and live promotion remain **closed** pending
  explicit approval.

## Supersession

This artifact supersedes `diagnostic_300_v7_v7_post_illusion` (15 residuals),
`diagnostic_300_v7_v7_corrected` (519 residuals), and the earlier
`diagnostic_300_v7_v7` (stale) for materialization-quality purposes. Those datasets
are retained but should not be used as the quality baseline.
