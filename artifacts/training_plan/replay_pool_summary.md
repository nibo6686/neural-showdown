# Replay Pool Summary

- Profile version: `replay-pool-profile-v1`
- Replay pool: `data\replays\raw\gen9randombattle`
- Total replays scanned: 15,001
- Valid / invalid: 15,001 / 0
- Eligible for `diagnostic_300`: 14,255
- Rating available: 13,113 (87.4%)
- Short/forfeit proxy: 4,517
- Long games (30+ turns): 3,492
- Close-game proxy: 5,243
- Catalog SHA-256: `0ebbad4d9a0fa35e3e37f38d964b1d04fa77207870a66048221ec1461044b24e`

## Format Distribution

- `gen9randombattle`: 15,001

## Distribution Quantiles

| Metric | Min | P25 | Median | P75 | P90 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Rating | 1000.0 | 1083.0 | 1297.0 | 1517.0 | 1784.0 | 2434.0 |
| Turns | 1.0 | 15.0 | 22.0 | 29.0 | 37.0 | 196.0 |
| Approx. decisions | 0.0 | 35.0 | 52.0 | 67.0 | 84.0 | 426.0 |

## Mechanic Coverage

| Mechanic | Battles | Percent |
| --- | ---: | ---: |
| `tera` | 12,164 | 81.1% |
| `boosts_drops` | 14,495 | 96.6% |
| `major_status` | 10,989 | 73.3% |
| `item_reveal_loss` | 10,910 | 72.7% |
| `ability_reveal_change_suppression` | 11,028 | 73.5% |
| `type_change` | 838 | 5.6% |
| `transform` | 384 | 2.6% |
| `illusion` | 259 | 1.7% |
| `weather` | 3,699 | 24.7% |
| `terrain` | 1,447 | 9.6% |
| `screens` | 582 | 3.9% |
| `tailwind` | 44 | 0.3% |
| `hazards` | 6,848 | 45.7% |
| `recharge_lock_constraints` | 838 | 5.6% |
| `encore` | 1,719 | 11.5% |
| `disable` | 565 | 3.8% |
| `taunt` | 894 | 6.0% |
| `choice_like_constraints` | 0 | 0.0% |

## Assessment

The existing pool is sufficient for a 300-battle diagnostic sample.

No targeted replay downloads are needed now; reassess after diagnostic feature-build coverage.

Detection is conservative and protocol-only: flags use public command IDs/effect text, decision count prefers `inputlog` commands, long means 30+ turns, and close means both sides publicly revealed at least five species and each suffered at least four faints. The short/forfeit proxy includes games under five turns, missing winners, timer evidence, or a winner before five publicly observed loser faints.
