# Stratified Dataset Plan

All splits are by `replay_id` before feature generation. No states or action
candidates from one battle may cross train/validation/test boundaries.

Use a deterministic seed and deduplicate battle IDs. Reserve 70% train, 15%
validation and 15% test within each stratum, then resolve overlaps by assigning
each replay once to its rarest/highest-priority stratum.

| Manifest | Battles | Broad random | Mechanic-enriched | Long/close | Higher rating | Rare mechanic reserve |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `diagnostic_300` | 300 | 120 | 75 | 45 | 30 | 30 |
| `small_1000` | 1,000 | 450 | 220 | 140 | 100 | 90 |
| `medium_5000` | 5,000 | 2,500 | 1,000 | 650 | 450 | 400 |

Higher-rating sampling is conditional on rating availability and should use the
top available quartile, not a hardcoded Elo cutoff. If a bucket is undersupplied,
fill from broad random while retaining the shortfall in manifest metadata.

Mechanic-enriched sampling should balance Tera, stages, status, item/ability,
typing, field/hazards and lock/constraint families. Rare reserve priority:
Transform/Illusion, explicit type change, ability suppression/change,
recharge/two-turn/Encore/Disable and unusual field combinations.

Each manifest row stores replay ID, source stratum(s), assigned primary stratum,
split, rating/date/turns/decision count, mechanic flags, profile version and
selection seed. Also write a summary proving no battle overlap across splits.

`diagnostic_300` is for plumbing and sensitivity only. Expand to 1,000 after
feature-build/storage checks, and to 5,000 only after the 300-run metadata,
calibration and sanity gates pass.
