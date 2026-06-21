# diagnostic_300_v7_v7_post_illusion Dataset Quality Audit

Read-only audit of the fresh post-Illusion v7/v7 dataset
(`artifacts/training_plan/datasets/diagnostic_300_v7_v7_post_illusion`). No
training, rematerialization beyond the one approved run, checkpoint promotion,
live-default/live-bot change, schema change, push, or v8/old-gen work occurred.

## Headline

| Metric | corrected (pre-fix) | post_illusion (this run) |
| --- | ---: | ---: |
| Decision states | 25,235 | 25,235 |
| Matched decisions | 24,716 | 25,220 |
| Unmatched decisions | 519 | **15** |
| Match rate | 97.94% | **99.94%** |
| Unmatched by kind | move 482 / move_tera 4 / switch 33 | **move 15 / move_tera 0 / switch 0** |
| Candidates | 191,667 | 197,429 |
| Displayed-species-uncertain states | 0 | 0 |

The reconstruction fix chain removed 504 of the 519 residuals. All `switch` and
`move_tera` residuals are gone; only 15 `move` residuals remain.

## Documented fixes confirmed in the materialized artifact

Each documented case is **absent** from `decision_skip_audit.jsonl` (i.e. matched
in the materialized dataset):

- **Ditto/Imposter Transform** — `gen9randombattle-2589571474` t20 p1
  `Thunder Wave`: matched. Future `Leaf Blade` contamination absent (the row is
  not a residual).
- **Actor-private Zoroark move** — `gen9randombattle-2591469202` t1 p2
  `Sludge Bomb`: matched.
- **Actor-private Zoroark-Hisui moves** — `gen9randombattle-2593348981` t6 and
  t18 `Will-O-Wisp`: matched.
- **Duplicate Houndstone/Zoroark switches** — `gen9randombattle-2591404793`
  t21/t23/t25: matched (relabeled to true `switch: Zoroark`).

`scripts/recompute_v7_v7_residual_unmatched_from_replays.py` independently
confirms 7/8 documented cases matched, 1 quarantined, `all_as_expected = True`.

## The 15 residual unmatched rows (all `move`, all explicit skips — no wrong labels)

The expected count was 1. The materialized count is 15 because the recompute
harness only tracks the 8 originally-documented rows, whereas a full
materialization covers every decision in all 300 replays and surfaces additional
Transform/Illusion patterns that were never in the documented set. The 15 break
down into three categories:

### A. Non-self-confirming Illusion stints — irreducible (3 rows)

| Replay | Turn | Side | Move | True species |
| --- | ---: | --- | --- | --- |
| `gen9randombattle-2593348981` | 1 | p1 | Will-O-Wisp | Zoroark-Hisui |
| `gen9randombattle-2593348981` | 2 | p1 | Poltergeist | Zoroark-Hisui |
| `gen9randombattle-2593283718` | 3 | p1 | Hyper Voice | Zoroark-Hisui |

These are the same irreducible category as the documented quarantined row: the
disguised entity switched out **before any `replace` reveal in that stint**, and
the player also owns a genuine copy of the displayed species (real Avalugg at max
HP 310 vs disguised 219; real Gumshoos at max HP 321 vs disguised 219). The
stints do not self-confirm, so the true species cannot be safely attributed
without HP-signature physical-entity tracking, which is fragile and risks
misattributing the real Pokemon. (The 2593348981 t1+t2 pair is the documented
quarantine plus the same stint's second decision; 2593283718 t3 is a new instance
of the identical pattern.) Quarantined/skipped, not leaked, not forced.

### B. Ditto/Imposter re-transform-into-same-species bug — fixable follow-up (11 rows)

| Replay | Turns | Side | Move |
| --- | --- | --- | --- |
| `gen9randombattle-2590922693` | 92,93,94 | p2 | Sacred Fire |
| `smogtours-gen9randombattle-929481` | 68,69,70,71 | p2 | Energy Ball |
| `gen9randombattle-2594584178` | 25,26,27,28 | p1 | Outrage |

Root cause: `_active_transform_copied_moves` in
`trainer/src/neural/build_live_private_value_dataset.py` anchors the current
Transform stint in the full-trajectory walk by `event.raw == stint_raw`. When a
Ditto re-transforms into the **same species** more than once (e.g. Entei→…→Entei,
Koraidon→Koraidon, …→Meganium→…→Meganium), the two `-transform` events have
identical `raw`, so the walk binds to the **earliest** occurrence and stops at the
intervening switch-out — never reaching the actual current stint. The copied
moveset then reflects an earlier stint and omits the move chosen in the current
stint. The single replay used to validate the Transform fix
(`gen9randombattle-2589571474`) only transformed into **distinct** species, so the
bug was not exposed.

This is a clean, safe reconstruction fix (anchor the stint by event identity /
occurrence index rather than by `raw`), recoverable without leakage or illegal
candidates. It is **not fixed in this task** (audit/materialization scope; a fix
would need its own checkpoint and a re-materialization). Recommended as the next
follow-up; it would recover these 11 rows (and likely the Struggle row below).

### C. Struggle / PP-exhaustion explicit skip — established category (1 row)

| Replay | Turn | Side | Move |
| --- | ---: | --- | --- |
| `smogtours-gen9randombattle-929481` | 65 | p2 | Struggle |

`Struggle` is the forced PP-exhaustion fallback, an explicit skip in every prior
audit until PP/choice-exhaustion legality is modeled. This row is also affected by
the category-B bug, but Struggle is not a normal candidate regardless.

## Other quality signals

- **Displayed-species uncertainty:** `own_active_displayed_species_uncertain` and
  `opponent_active_displayed_species_uncertain` are 0/25,235 — no regression; the
  actor-private de-disguise does not mark public displayed species uncertain.
- **No-leakage preserved:** the de-disguise/relabel only affect own-side rows;
  opponent pre-reveal belief never receives the true species (covered by
  regression tests). The 15 residuals are excluded, never injected as wrong
  labels.
- **Candidate/state distribution:** 197,429 candidates / 25,235 states ≈ 7.82
  avg; matched-by-kind move 18,540 / move_tera 431 / switch 6,249. Candidate count
  rose vs corrected (191,667) because de-disguised actives expose their true (and
  Tera) move candidates.
- **v6 prefix integrity:** guaranteed by the embedded append-only fingerprint
  validation (`embedded_names_match_schema_and_metadata` passed; first 331 action
  dims are the frozen v6 slice). v6 prefix columns are populated across all rows.
- **Batch 7/8 activity:** batch-7 action-risk/probability slice (dims 452:511) has
  50/59 active columns over 122,027 candidate rows; batch-8
  forced-decision/secondary-chance slice (dims 511:552) has 25/41 active columns
  over 30,115 candidate rows. Both slices are exercised.
- **Old datasets untouched:** `.npz` sha256 prefixes for
  `diagnostic_300_v7_v7`, `diagnostic_300_v7_v7_corrected`,
  `diagnostic_300_v7_v6`, `diagnostic_300_v7_v5`, and
  `diagnostic_1000_action_rank_v7_v5` are byte-identical to the pre-run snapshot.

## Expected vs actual residual count

Expected 1; actual 15. The discrepancy is fully explained: 3 irreducible
non-self-confirming Illusion rows (the documented quarantine + its same-stint
companion + one new instance of the same pattern), 11 from a newly-surfaced
fixable Ditto re-transform-same-species bug, and 1 Struggle explicit skip. None is
a leakage or wrong-label issue.

## Gate decision

- The dataset is structurally valid (all 18 checks passed), schema/fingerprint
  exact, splits correct, and 99.94% matched with the 15 residuals all explicit,
  explained skips (no wrong labels, no forced quarantined rows).
- **A tiny smoke / plumbing training run is acceptable** on this artifact if
  explicitly approved (the 0.06% excluded rows inject no error). It is **not yet a
  durable quality baseline**: the category-B Ditto re-transform bug should be
  fixed and the dataset rematerialized before durable training, and the 3
  non-self-confirming Illusion rows remain an irreducible public-replay limitation
  (not a live-play limitation — live play knows its own true side).
- Training, checkpoint promotion, and live promotion remain **closed** pending
  explicit approval.

## Supersession

This artifact supersedes `diagnostic_300_v7_v7_corrected` (519 residuals) and the
earlier `diagnostic_300_v7_v7` (stale, pre-reconstruction-fix) for
materialization-quality purposes. Those datasets are retained but should not be
used as the quality baseline.
