# Replay Reproduction Feasibility

Audit date: 2026-06-18

## Verdict

Exact reproduction of ordinary public saved Pokemon Showdown replays is not currently supported.

Partial public-state reconstruction is supported and was validated on five saved Gen 9 Random Battle logs.

## Information present in public replay logs

Public logs contain:

- format/rules, player names, team sizes, and public lead reveals
- executed moves and switches
- public HP/status/boost/field/item/ability/tera events
- faints and winner text

These events are sufficient to reconstruct many public state prefixes and verify event parsing.

## Information absent from the audited public logs

The five sampled logs contained neither:

- a `>start` input record with the four-word PRNG seed
- private `|request|` payloads

They also do not provide complete unrevealed teams, unrevealed moves/items/abilities/tera types, exact private PP throughout the battle, rejected/changed choices, or all internal RNG draws.

## Current sim-core initialization capability

- `sim-core` can initialize a battle from a format and four-word seed.
- It always generates both random teams internally from derived team seeds.
- The RPC does not accept exact packed p1/p2 teams, serialized battle state, or an input log.
- Therefore it cannot initialize from exact teams recovered from a public replay, even when some or all sets later become public.

## Choice forcing

- `sim-core` can force concrete choices for both externally controlled players.
- Local traces can replay stored fixed action indices when the regenerated requests match.
- Public replay logs record executed move/switch names, but not a reliable mapping to each side's private request slot, all simultaneous choices, or rejected choices.
- The current exact rollout implementation replays stored local trace action indices; it is not a general public protocol replay engine.

## RNG reproduction

- Locally generated traces with the original environment seed and matching generated teams can be replayed approximately to the same decision sequence.
- Public saved replays do not normally expose the battle PRNG seed.
- Without the original seed and exact initial teams, accuracy rolls, damage rolls, secondary effects, speed ties, random targets, sleep duration, and similar events cannot be reproduced exactly.
- Inferring a seed from public outcomes is neither implemented nor generally unique.

## Validated partial replay behavior

Five saved replay logs were parsed. For each, the parser's move, switch/drag, and damage-event counts matched the raw protocol command counts. Public turn prefixes, winner text, reveals, HP events, and action events are available for state-oriented validation.

Winner parsing now preserves the last non-empty player names and resolves the side when `|win|` is encountered, so later disconnect records cannot erase the label. Replays without a winner line are explicitly marked `winner_status=unknown`, and replay dataset builders skip them.

## Additions required for exact replaying

1. Extend `create_env`/`reset` to accept exact packed teams or a full Showdown input log.
2. Persist the original four-word battle seed in locally generated trace artifacts.
3. Persist exact concrete choices for every side and every request, including team preview, forced switches, targets, and rejected choices.
4. Persist request IDs and private request snapshots when exact local replay is intended.
5. Add a replay driver that validates each regenerated request before submitting the recorded choice.
6. Compare regenerated public protocol events and fail at the first divergence.
7. For public replays without private inputs, keep a separate partial public-state validator and do not label it exact replay.

## Safe wording

The current project supports “public replay parsing and partial public-state validation.” It does not support “exact replay reproduction” for ordinary public saved replays.
