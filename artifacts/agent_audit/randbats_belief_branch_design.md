# Randbats-Belief Two-Ply Branching — Design

Audit date: 2026-06-18  
Scope: Gen 9 Random Battles singles, opt-in research mode.

## Where exact hidden information entered

The exact one-turn and two-ply evaluators created a new env from the original
four-word battle seed and replayed every recorded choice. sim-core regenerated
both original teams from that seed. Although leaf scoring used only the audited
player's legal view, every simulated transition therefore used the opponent's
true unrevealed species, moves, item, ability, tera type, stats, and team order.

The exact mode remains valid as an explicitly labeled seeded upper bound. It is
not a live-realistic estimate.

The exact evaluator also bounded opponent actions from the real opponent
request. That request is private and cannot be used in belief mode.

## Public and private boundary

Belief mode may use:

- species that have appeared publicly;
- publicly used moves;
- publicly announced item, ability, and tera information;
- public HP percentage, status, boosts, volatiles, faint state, field state,
  hazards, weather, and terrain;
- the audited player's own private request/team;
- Gen 9 randbats generation data and deterministic research seeds.

It must not use:

- unrevealed opponent moves, item, ability, tera type, stats, or bench species;
- the true opponent request or legal-action list;
- the true opponent set to choose among randbats candidates;
- true hidden team order.

## Why team injection alone is insufficient

Replaying the past from turn zero with a different sampled set changes prior
damage, speed order, faints, switches, and legality. It generally fails to
reconstruct the actual current public state.

The pinned `pokemon-showdown@0.11.10` engine exposes `Battle.toJSON()` and
`Battle.fromJSON()`. Belief mode therefore snapshots the current battle,
sanitizes the opponent in the serialized state, and restores that modified
current-state snapshot into a separate branch env. This preserves public
HP/status/boost/field state without replaying history under the wrong set.

## Deterministic belief construction

For each decision:

1. Read the audited player's public opponent view.
2. For every revealed species, repeatedly call the pinned Showdown Gen 9
   randbats `randomSet` generator with deterministic derived seeds.
3. Accept a set only when it contains every revealed move and matches any
   publicly known ability, item, and used tera type.
4. If no exact candidate is generated in 64 attempts, record an impossible
   belief case and construct a conservative fallback that forcibly preserves
   the public constraints.
5. Fill unrevealed bench slots from deterministic full randbats team
   generations, excluding duplicate/revealed species.
6. Build donor serialized Pokémon from those sampled sets.
7. Replace the opponent's hidden set fields in the source snapshot. Copy back
   only public dynamic state for revealed Pokémon: HP ratio, status, boosts,
   volatiles, faint/active state, and publicly constrained fields.
8. Restore the sanitized snapshot into a new external-vs-external env.

The belief seed is derived only from the battle seed, audited side, and decision
number. Same public state and belief seed produce the same sample. Different
belief seeds can produce different plausible hidden teams.

## Branch search

The existing bounded two-ply algorithm is unchanged:

- root actions capped at 3;
- sampled opponent current actions capped at N=3;
- own follow-ups capped at M=2;
- one deterministic sampled-env heuristic reply on the second turn;
- material/HP leaf scorer;
- terminal outcomes override material;
- mean over opponent responses after choosing the best own follow-up.

The crucial difference is that opponent legal actions and heuristic ordering
come from the sampled fork's request, never the source opponent request.

## Diagnostics and leakage safeguards

Each decision records:

- sampled sets and belief seed;
- candidate attempts and constrained-field count;
- impossible belief cases and missing-data fallbacks;
- post-restore public constraint violations;
- belief samples, branches, leaves, caps, errors, timeouts, and damage
  fallbacks.

Tests verify deterministic sampling, different-seed variation, revealed-move
preservation, independence from deliberately modified true hidden bench fields,
separate exact/belief labels, and zero damage fallback.

## Limitations

- The sampler is a single deterministic particle per decision, not a posterior
  ensemble.
- Hidden team composition is drawn from the randbats generator conditioned only
  by revealed species exclusion, not a learned team-composition posterior.
- Publicly revealed sets can occasionally be inconsistent with the current
  pinned randbats generator (old sets, transformations, or unusual mechanics);
  these are counted as impossible/fallback cases.
- Snapshot sanitization is suitable for this pinned Gen 9 singles research
  substrate only. Doubles and live defaults remain out of scope.
