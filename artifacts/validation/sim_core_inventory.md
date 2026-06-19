# sim-core Inventory

Audit date: 2026-06-18

## Dependency and engine source

- `sim-core` imports the published `pokemon-showdown` npm package directly.
- Installed lockfile versions:
  - `pokemon-showdown@0.11.10`
  - `@smogon/calc@0.11.0`
- `package.json` and the lockfile pin the audited versions exactly. Dependency changes require rerunning `validate-sim-core`.
- Battle mechanics are executed by Pokemon Showdown's `BattleStream`, `Battle`, team generator, Dex, request generation, and choice validation. `sim-core` is not a separate reimplementation of battle mechanics.

## Battle lifecycle and RPCs

- `create_env` allocates a `LocalBattleEnv` and stores format, four-word seed, and player controller types.
- `reset` destroys any prior stream, creates a new `BattleStream`, attaches player/spectator streams, generates two random teams, sends `>start` and `>player` commands, and drains until an external player has an actionable request or the battle ends.
- `step` submits concrete Showdown choice strings to externally controlled player streams and drains to the next external decision.
- `agent_action` asks the random or heuristic baseline to select from the current normalized legal-action set. The baseline does not determine legality.
- `damage_estimate` calls the local `@smogon/calc` wrapper and throws on calc failure. Non-damaging moves return a separate `non_damaging_move` result.
- `legal_actions` are built from the latest Showdown `|request|` payload.

## Seeds and random teams

- A caller can supply exactly four integer seed words.
- Without a supplied seed, `sim-core` creates four values using JavaScript `Math.random()`.
- The battle PRNG receives the environment seed.
- Random teams are generated deterministically from two derived seeds:
  - p1: environment seed offset by 11
  - p2: environment seed offset by 29
- Repeated resets of the same `LocalBattleEnv` regenerate the same teams and battle seed.
- Tests confirm two environments with the same seed produce the same initial teams.

## Player views and privacy

- Each `PlayerStateExtractor` consumes only that player's stream.
- Own exact team, moves, PP, item, ability, stats, tera type, and request legality come from that player's private `|request|`.
- Opponent state is built from public protocol events such as `|poke|`, `|switch|`, `|move|`, `|-item|`, `|-ability|`, and `|-terastallize|`.
- Unrevealed opponent moves, exact item, ability, tera type, stats, and private bench data are not copied from the opponent request.
- `StepResult.omniscient` is always `null`.
- The spectator stream is exposed only as incremental public `log_delta`.
- Focused privacy tests passed for unrevealed opponent moves/item/ability/tera/stats and own private request fields.

## Fixed 13-action encoding

- Indices `0-3`: `move 1` through `move 4`.
- Indices `4-7`: matching move with `terastallize`.
- Indices `8-12`: up to five healthy, inactive team members in current bench order.
- Each enabled index stores the concrete Showdown command in `choice`.
- Disabled moves and moves with zero PP are omitted.
- Tera actions are omitted when `canTerastallize` is false or any own team member is marked terastallized.
- Switches are omitted when the active request says `trapped`.
- Active and fainted team members are excluded from switch actions.
- If no concrete action remains, index 0 is populated with `default`, delegating Struggle or other fallback resolution to Showdown.

## Forced switches and restrictions

- A single-active `forceSwitch` request returns only switch actions.
- Faint replacement requests use the same forced-switch representation.
- Choice lock, Encore, Taunt, Disable, Assault Vest, and other move restrictions are not independently inferred by `sim-core`; they are represented through Showdown's per-move `disabled` flags.
- PP legality comes from request PP values.
- Trapping comes from the request's `active[0].trapped`.
- Tera legality comes from `canTerastallize` plus own terastallized state.
- Invalid submitted choices are rejected by Showdown; `sim-core` removes the rejected concrete choice and returns the still-pending request instead of hanging.

## Format support

- The implementation is structurally singles-only.
- It reads only `active[0]`, emits one fixed action, treats `forceSwitch` as one boolean, and cannot encode multi-slot choices or targets.
- Doubles, triples, multi battles, and simultaneous multi-action forced switches are not supported by the 13-action codec.
- Team preview is automatically answered with `default`; it is not represented in the policy action space.

## Damage calculation

- The primary calculation path is `@smogon/calc`, with ranges preserved.
- Tested modifiers include effectiveness/immunity, STAB behavior, burn, Choice Band/Specs, Focus Sash via the Showdown engine, screens, weather, terrain, abilities, and tera.
- The Python action-damage layer can fall back to `heuristic_fallback` when RPC/direct calc fails. Strict live eval rejects that fallback at startup, but non-strict callers can still consume it.
- Supplied exact `stats` override the calc Pokémon's raw stats and survive calc cloning. Responses report `used_exact_attacker_stats` and `used_exact_defender_stats`. EVs, IVs, boosts, level, item, ability, status, and tera remain supported when exact stats are absent.

## Overall inventory conclusion

`sim-core` uses the authoritative Pokemon Showdown engine for battle execution and request legality. The wrapper is credible for seeded Gen 9 singles smoke tests and now has pinned dependencies and exact-stat damage regression coverage. Its action codec remains singles-specific.
