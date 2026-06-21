# Randbats MetaPriorSource Adapter Report

## Result

The source-neutral prior contract now has a deterministic adapter over the
same checked-in Randbats role data already used by the older opponent-set
shortcut.

- Existing loader: `trainer/src/neural/live_opponent_beliefs.py`
- Selected source: `data/random-battles/gen9/sets.json`
- Format: `gen9randombattle`
- Source entries: 508 species/forms, 877 role declarations
- Raw source SHA-256:
  `7dc75740d17755d921c473fca68b3022f6f37a2af387d3cd9c94432bd646eaef`
- Adapter version: `randbats-role-data-adapter-v1`

No source data was scraped, regenerated, sampled, or modified.

## Representation policy

The existing file contains roles, movepools, ability alternatives, and Tera
type alternatives. It does not contain items, exact generated four-move sets,
or empirical role weights. The adapter therefore:

- emits `joint_quality = factorized`;
- weights declared roles equally when source weights are absent;
- uniformly expands ability/Tera alternatives within a role;
- stores the declared movepool as coarse role support, not an exact moveset;
- leaves item unknown;
- reserves `other_mass = 0.5` under an explicit unvalidated adapter policy;
- records coverage warnings for every approximation.

`sample_count = 0` is intentional: this source is not a sampled generator
snapshot.

## Example priors

| Species | Represented hypotheses | Known source facts | Unknown/tail |
|---|---:|---|---:|
| Dondozo | 2 | Bulky Setup; Unaware; Curse/Rest/Sleep Talk/Wave Crash role pool; Dragon/Fairy Tera alternatives | 0.5 |
| Hatterene | 4 | Bulky Setup or AV Pivot; Magic Bounce; role movepools; Fairy/Steel Tera alternatives | 0.5 |
| Great Tusk | 6 | Three declared roles; Protosynthesis; role movepools; Ground/Steel Tera alternatives | 0.5 |
| MissingNo | no prior | No checked-in role entry | belief initialization falls back to unknown mass 1.0 |

## Safety and scope

Tests confirm deterministic source identity and priors, format rejection,
missing-species fallback, and invariance to replay/context hidden-truth
perturbations. The adapter consumes no replay truth and has no strategic
counter rules.

This is not a complete generator-sampled prior, a v8 feature encoder, a schema
change, materialization, training, or live integration.
