# Multi-Particle Randbats-Belief Two-Ply Branching — Design

Audit date: 2026-06-19  
Scope: Gen 9 Random Battles singles, opt-in research mode.

## Current single-particle flow

The existing `branch_two_ply_belief_material` mode derives one deterministic
belief seed from the battle seed, audited side, and decision number. sim-core
snapshots the current battle, replaces every hidden opponent set field with a
randbats sample constrained by the audited player's public view, restores that
sanitized snapshot in an isolated env, and runs the bounded two-ply material
search there.

This path does not read the source opponent request or true hidden opponent set.
It is mechanically credible and deterministic, but one sampled team can make
the selected action brittle.

## Three-particle extension

The new `branch_two_ply_belief3_material` agent keeps the single-particle mode
unchanged and evaluates exactly three sanitized opponent states per decision.
Particle 0 uses the existing base belief seed. Particle indices 1 and 2 use
fixed per-word offsets modulo 65536. Therefore the same public state and base
seed always produce the same ordered particle set, while different particle
indices normally produce different hidden teams or sets when alternatives
exist.

The implementation accepts particle counts 1, 3, or 5, but the audit default is
exactly 3.

## Shared public root actions

Every particle must score the same root actions before scores can be averaged.
The ensemble obtains the audited player's heuristic-preferred action from the
source env. That heuristic receives only the audited player's legal view, so it
does not expose opponent private information. The remaining root actions use
the existing deterministic legal ordering. The common set is capped at three
actions.

Each particle then runs the existing bounded search with:

- the common root-action indices;
- at most three sampled current opponent replies;
- at most two own follow-up actions;
- one deterministic sampled-env heuristic reply on the second turn;
- terminal result override and otherwise material/HP leaf scoring.

Opponent actions always come from that particle's sanitized env. The true
opponent request is never passed into particle search.

## Public-information preservation

Every particle independently uses the existing sim-core belief fork, which:

- retains all publicly revealed opponent species;
- requires every revealed move;
- preserves publicly announced item and ability;
- preserves a used tera type;
- copies only public dynamic state such as HP ratio, status, boosts, volatiles,
  active/fainted state, hazards, weather, terrain, and field state;
- fills unrevealed fields and bench species from deterministic randbats
  generation rather than the source hidden team.

The existing post-restore public-constraint checker runs for every particle.
Constraint violations, impossible/relaxed samples, and missing randbats data
are summed and reported. A failed belief sample is counted; it does not silently
fall back to exact hidden reconstruction.

## Aggregation

For each root action, one particle contributes its existing root mean: best own
follow-up per bounded opponent reply, then mean over those replies. The ensemble
computes:

- mean across particles (selection objective);
- population standard deviation;
- worst particle score;
- best particle score;
- full ordered particle score list.

Ties remain deterministic by preferring the lower action index. The report also
records each particle's selected action, the number of distinct selected
actions, and whether the particles disagree.

## Diagnostics

Each decision reports:

- requested and completed particle counts;
- derived particle seeds and per-particle belief metadata;
- per-action aggregate mean, standard deviation, worst, and best scores;
- particle-selected action indices and disagreement;
- belief sample errors;
- public-information constraint violations;
- total transition branches and leaves;
- branch errors, caps, and timeouts;
- latency and damage fallbacks.

Single-particle and exact two-ply report shapes remain valid and their selection
logic is unchanged.

## Performance bounds

Three particles should cost roughly three times the single-particle search,
although current-state snapshot forks avoid the growing replay-from-turn-zero
cost of exact mode. The ensemble keeps the existing 3/3/2 action caps and an
eight-second total decision deadline. Before each particle, the remaining
deadline is passed to that particle. If the total deadline is exhausted, the
missing particle is counted as an error and no unreported exact or one-turn
fallback occurs.

The first gate is a five-battle smoke. The full paired audit proceeds only if
the smoke has zero public-information violations and zero damage fallbacks.
