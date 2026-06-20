# diagnostic_1000 Action-Rank Manifest Validation Report

- Overall: **PASS**
- Manifest version: `diagnostic-1000-action-rank-manifest-v1`
- Objective: action-rank (state v7/3208, action v5/318)
- Seed: `20260619`
- Source replay pool: `artifacts\training_plan\replay_catalog.jsonl`
- Catalog SHA-256: `0ebbad4d9a0fa35e3e37f38d964b1d04fa77207870a66048221ec1461044b24e`
- Eligible pool: 14,255
- Splits: train 700, validation 150, test 150

## Checks

- [x] `exactly_total_entries`
- [x] `unique_ids`
- [x] `split_sizes_exact`
- [x] `no_cross_split_duplicates`
- [x] `all_entries_in_catalog`
- [x] `all_paths_exist`
- [x] `mechanic_coverage_at_least_random_baseline`
- [x] `seed_recorded`
- [x] `catalog_checksum_recorded`

## Selection Composition

- `long_close`: 150
- `rare_mechanic`: 60
- `broad_random`: 350
- `switch_heavy`: 110
- `mechanics_enriched`: 150
- `tera_action_enriched`: 90
- `higher_rating`: 90

## Enrichment vs Random Baseline (per 1000 battles)

| Metric | Selected | Random baseline |
| --- | ---: | ---: |
| Tera battles | 924 | 850 |
| Battles with >=1 Tera action | 924 | 850 |
| Tera action total | 1547 | 1333 |
| Switch decision total | 20756 | 13956 |
| Switch decisions/battle | 20.76 | 13.96 |
| Switch share of decisions | 0.237 | 0.252 |
| Long-game rate | 0.499 | 0.247 |
| Close-game rate | 0.503 | 0.39 |
| Short/forfeit rate | 0.163 | 0.257 |
| Rating available | 0.878 | 0.867 |

## Mechanic Coverage

- Selected mechanic-flag total: 6450
- Random-baseline mechanic-flag total: 5430

| Mechanic | Selected | Random baseline |
| --- | ---: | ---: |
| `tera` | 924 | 850 |
| `boosts_drops` | 996 | 993 |
| `major_status` | 869 | 766 |
| `item_reveal_loss` | 826 | 744 |
| `ability_reveal_change_suppression` | 826 | 777 |
| `type_change` | 117 | 65 |
| `transform` | 59 | 33 |
| `illusion` | 36 | 18 |
| `weather` | 374 | 256 |
| `terrain` | 148 | 107 |
| `screens` | 101 | 41 |
| `tailwind` | 1 | 0 |
| `hazards` | 604 | 472 |
| `recharge_lock_constraints` | 116 | 56 |
| `encore` | 266 | 137 |
| `disable` | 78 | 40 |
| `taunt` | 109 | 75 |
| `choice_like_constraints` | 0 | 0 |
