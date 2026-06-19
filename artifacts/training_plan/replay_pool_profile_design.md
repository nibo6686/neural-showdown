# Replay Pool Profiler Design

**Input:** existing `data/replays/raw/gen9randombattle` pool only  
**Observed pool:** 15,001 logs and 15,001 replay JSON files; no new download

## Existing tooling

- `neural.replay_fetch` stores replay JSON/log assets and `metadata.jsonl`.
- `neural.parse_replay_logs` converts protocol logs to trajectory JSONL.
- Existing dataset builders reconstruct public/private approximations but are
  too expensive for profiling because they generate feature vectors.

Implement a lightweight `neural.replay_pool_profile` scanner that reads each
metadata row plus the corresponding JSON/log once. It must not invoke state or
action featurizers.

## Per-replay output

Write compressed JSONL or Parquet plus a summary JSON. Each row contains:

- `replay_id`, normalized format, upload date/time, rating/Elo, winner;
- total turns and estimated decision states (count legal player commands from
  `inputlog` when available; otherwise count public move/switch actions);
- `early_forfeit_or_short` (recommended: fewer than 5 turns, no winner, or win
  before normal team depletion), `long_game` (recommended: at least 30 turns);
- Tera, boosts/drops, major status, item reveal/loss, ability
  reveal/change/suppression, type change, Transform and Illusion evidence;
- weather, terrain, screens, Tailwind, hazards;
- recharge/two-turn/lock-in, Encore, Disable, Taunt and Choice-like evidence;
- `close_game_proxy`;
- parse status, warnings and error text.

Protocol detection should use command IDs and effect/source text, not tactical
preference rules. Preserve raw command counts for auditability.

## Suggested event mapping

- Tera: `-terastallize`
- boosts/drops: `-boost`, `-unboost`, `-setboost`, `-swapboost`,
  `-invertboost`, `-copyboost`, clear-boost commands
- status: `-status`, `-curestatus`
- item: `-item`, `-enditem`
- ability: `-ability`, `-endability`, Neutralizing Gas source/effect text
- type: `typechange`, `typeadd`, Tera separately
- Transform/Illusion: `-transform`, `replace`, Illusion source text
- field: `-weather`, `-fieldstart/-fieldend`, `-sidestart/-sideend`
- constraints: `cant` reasons, `-start/-end` effects, `-mustrecharge`,
  `-prepare`, Encore/Disable/Taunt and publicly inferable single-move sequences

`close_game_proxy` should be conservative: both sides reveal at least five
Pokémon and the loser reaches one remaining Pokémon, or the final three turns
contain both sides below a configurable remaining-team threshold. Do not infer
hidden teams.

## Summary outputs

Report counts/rates, rating/date/turn/decision quantiles, parser failures,
mechanic co-occurrence, and replay IDs for each rare-mechanic bucket. Include
duplicate-ID detection and metadata/log/JSON mismatches.

The profiler output becomes the sole input to sample-manifest generation; sample
selection must be deterministic from a recorded seed.
