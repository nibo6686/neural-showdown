# ObservableBattleState Contract

`STATE-001` defines an additive, shadow-only observation boundary. The
implementation is `sim-core/src/observable_state.ts`; it consumes existing
`BattleView` and `ChoiceRequestView` values and does not replace them. It has no
model, checkpoint, live-default, or search call sites.

## Version and visibility

The only supported schema version is `observable-battle-state/v1`. An unknown
version is an explicit error. Every field is classified as one of:

- `public`: visible in the protocol to a spectator/player;
- `acting_player_private`: available from the acting player's legitimate
  request, but not from the opponent's view;
- `derived_observable`: deterministic projection of evidence that remains safe
  to expose;
- `hypothesis`: inferred or sampled information, never part of this projection;
- `simulator_only`: engine/control information, never part of this projection.

The projection contains no `possible_roles`, `possible_moves`,
`possible_abilities`, `possible_tera_types`, `ChoiceRequestView.raw`, rewards,
controller configuration, omniscient state, or environment ID. `battle_id` is
explicit metadata and is not copied from the simulator's `env_id` unless the
caller intentionally supplies that value.

## Normative invariants

1. `perspective` is exactly `p1` or `p2`. Any other value fails closed.
2. `BattleView.player`, `ChoiceRequestView.player`, and `perspective` must agree.
   A request-side mismatch is an explicit contradiction error.
3. `event_cursor` is the count of normalized protocol records in
   `protocol_prefix`; it is not a turn number.
4. Normalization converts CRLF/CR to LF, trims record boundaries, and rejects
   empty records. The hash input is the canonical JSON array of the normalized
   records. `protocol_prefix_hash` is SHA-256 of that canonical array.
5. `observation_id` is deterministic: it is `obs-` plus SHA-256 of the canonical
   schema/source/battle/perspective/cursor/hash/phase/request/decision/view
   identity payload.
6. Snapshots own cloned data and are recursively frozen. Later protocol records
   cannot mutate an earlier snapshot. `ObservableStateProjector` retains the
   canonical normalized records and accepts a later observation only when the
   complete earlier record sequence is an exact prefix; rollback, replacement,
   reordering, altered earlier records, and hash-only claims fail closed.
7. A request-less state uses `request: null`, reports `available: false`, and
   uses `legal_action_indices: null`; it never fabricates legal actions.
8. `pre_decision`, `post_resolution`, `forced_switch`, and `terminal` are
   supported phases. Any other well-formed token is normalized to
   `snapshot_phase: other` and retained verbatim in `other_phase`; malformed
   tokens fail closed. A forced-switch phase requires a force-switch request; a
   terminal phase requires a terminated view.
9. Raw protocol evidence has precedence over derived fields. The adapter
   independently parses supported raw records and compares available raw-derived
   `gen`, `turn`, player names, team sizes, winner, and request `rqid` values to
   the projected sources. Matching evidence is accepted, incomplete evidence is
   not invented, malformed or unsupported evidence errors, and contradictions
   raise `ObservableStateContradictionError`. Caller-provided contradiction
   messages are not a substitute for this validation.
10. Hypotheses are separate from observations. Belief samples, possible roles,
    inferred opponent sets, and simulator-only hidden state require a separate
    contract and cannot be added to this object.
11. The adapter is shadow-only. Existing feature vectors, checkpoints, model
    inputs, live defaults, simulator mechanics, and search behavior are
    unchanged.

## Field-level schema and provenance

The tables below are normative. `Model input` means eligible for a future
explicit consumer; it does not authorize routing the current models through the
adapter.

### Metadata and evidence

| Field | Type / nullability | Visibility | Source of truth | Transformation | Contradiction behavior | Model input |
|---|---|---|---|---|---|---|
| `schema_version` | string, non-null | derived_observable | adapter constant | exact supported version | unsupported value errors | metadata only |
| `source_kind` | `sim_core \| replay \| live`, non-null | derived_observable | caller/source boundary | validated enum | unsupported value errors | metadata only |
| `battle_id` | string, non-null | derived_observable | caller lineage | no implicit `env_id` fallback | empty value errors | lineage only |
| `perspective` | `p1 \| p2`, non-null | derived_observable | caller | validated and matched to view/request | invalid/mismatch errors | orientation metadata |
| `event_cursor` | non-negative integer, non-null | derived_observable | normalized `protocol_prefix` length | count records, not turns | rollback or same-cursor hash change errors in projector | audit only |
| `observation_id` | string, non-null | derived_observable | adapter identity payload | deterministic `obs-` SHA-256 | identity mismatch is an error | lineage only |
| `protocol_prefix_hash` | 64-char SHA-256 string, non-null | derived_observable | raw protocol prefix | canonical normalized record array | raw prefix errors; never silently repaired | audit only |
| `snapshot_phase` | `pre_decision \| post_resolution \| forced_switch \| terminal \| other`, non-null | derived_observable | caller decision boundary | supported token preserved; unknown well-formed token normalized to `other` | malformed token or impossible phase/request errors | timing metadata |
| `other_phase` | string or null | derived_observable | original unsupported phase token | retained only when `snapshot_phase=other` | mismatch or malformed token errors | timing metadata |
| `request` | `ObservableChoiceRequestView \| null` | public + acting_player_private | `ChoiceRequestView`, excluding `raw` | deep clone and redaction | side/perspective mismatch errors | eligible only for acting-player consumers |
| `decision_availability` | object, non-null | derived_observable | request + terminal state | no legal-action invention | mask/index contradictions error | action masking only; not current model input |
| `protocol_prefix` | string array, non-null | public evidence | raw protocol records | normalize, clone, freeze | empty/non-string records error | audit/feature source only with explicit cutoff |

### Battle view projection

| Field | Type / nullability | Visibility | Source of truth | Transformation | Contradiction behavior | Model input |
|---|---|---|---|---|---|---|
| `view.format` | string, non-null | public | `BattleView.format` / protocol format | clone | caller/parser error | eligible |
| `view.gen` | integer or null | public | `BattleView.gen` / protocol | clone | raw conflict quarantines | eligible |
| `view.turn` | integer, non-null | public | `BattleView.turn` / protocol | clone; never used as cursor | raw conflict quarantines | eligible timing feature |
| `view.player` | `p1 \| p2`, non-null | derived_observable | `BattleView.player` | match perspective | mismatch errors | orientation metadata |
| `view.opponent` | `p1 \| p2`, non-null | derived_observable | `BattleView.opponent` | clone | perspective mismatch errors | orientation metadata |
| `view.terminated` | boolean, non-null | public/derived_observable | `BattleView.terminated` | clone | terminal-phase mismatch errors | eligible terminal feature |
| `view.winner` | `p1 \| p2 \| tie \| null` | public | protocol/`BattleView.winner` | clone | raw conflict quarantines | eligible only terminal labels |
| `view.names` | `{p1,p2: string \| null}`, non-null | public | protocol/`BattleView.names` | clone | raw conflict quarantines | normally excluded |
| `view.team_size` | `{p1,p2: integer}`, non-null | public | protocol/`BattleView.team_size` | clone | raw conflict quarantines | eligible |
| `view.active` | `{self,opponent: integer \| null}`, non-null | public | protocol/`BattleView.active` | perspective-normalized clone | raw conflict quarantines | eligible |
| `view.field` | `ObservableFieldView`, non-null | public | protocol/`BattleView.field` | clone and normalize side orientation | raw conflict quarantines | eligible |
| `view.self_team` | `ObservablePokemonView[]`, non-null | public + acting_player_private fields | `BattleView.self_team` | clone; omit hypothesis arrays | privacy contradiction errors | eligible for acting player |
| `view.opponent_team` | `ObservablePokemonView[]`, non-null | public | `BattleView.opponent_team` | clone; preserve redaction | any private leakage is a contract failure | eligible |

`ObservablePokemonView` copies the explicit public allowlist `slot`, `ident`, `name`, `species`,
`base_species`, `current_species`, `displayed_species`, `species_source`,
`transformed`, `displayed_species_uncertain`, `illusion_revealed`, `details`,
`active`, `fainted`, `hp_text`, `hp_ratio`, `status`, `status_source`,
`status_started_turn`, `status_turns_public`, `gender`, `level`, `types`,
`terastallized`, and `volatiles`. These fields are copied for both teams.
Acting-player `self_team` additionally receives the explicit private allowlist
`item`, `last_item`, `item_state`, `item_suppressed`, `ability`, `base_ability`,
`ability_state`, `ability_suppressed`, `moves`, `revealed_moves`, `tera_type`,
`stats`, and `boosts`. `opponent_team` omits those fields by default; the only
allowed item signal is the public literal `item: has-item`. No object spread or
whole-`PokemonView` copy is permitted at this boundary. Arrays and maps are
cloned, and the omitted `possible_*` fields are hypothesis fields. A private
field supplied in an opponent `BattleView` is therefore omitted rather than
silently exposed.

`ObservableFieldView` contains `weather: string | null`,
`terrain: string | null`, `pseudo_weather: string[]`, and
`side_conditions: {self: Record<string, number>, opponent: Record<string,
number>}`. They are public, cloned from `BattleView.field`, and eligible for
features; raw protocol contradictions are quarantined.

For field-level completeness, the copied Pokémon and field members have these
individual rules (all rows use the same raw-protocol contradiction behavior and
model eligibility stated in the preceding table):

| Field | Type / nullability | Visibility | Source / transformation | Model input |
|---|---|---|---|---|
| `slot`, `ident`, `name`, `species`, `details` | integer/string, non-null | public | `PokemonView`, cloned | eligible |
| `base_species`, `current_species`, `displayed_species` | string or null | public | protocol-derived `PokemonView`, cloned | eligible |
| `species_source` | fixed string enum, non-null | derived_observable | preserve source label | metadata/eligible |
| `transformed`, `displayed_species_uncertain`, `illusion_revealed`, `active`, `fainted` | boolean, non-null | public/derived_observable | protocol reduction, cloned | eligible |
| `hp_text`, `status` | string or null | public | protocol/request evidence, cloned | eligible |
| `hp_ratio` | number or null | public/derived_observable | protocol condition parsing, cloned | eligible |
| `status_source` | fixed string enum, non-null | derived_observable | preserve provenance label | metadata/eligible |
| `status_started_turn`, `status_turns_public`, `gender`, `level` | integer/string or null | public/derived_observable | protocol reduction, cloned | eligible |
| `item`, `last_item` | optional string or null | public presence or acting_player_private | copy only for self; opponent may expose literal `has-item` only | eligible only at source visibility |
| `item_state`, `item_suppressed` | optional fixed enum/boolean | acting_player_private | copied only for self | eligible only at source visibility |
| `ability`, `base_ability` | optional string or null | acting_player_private | copied only for self | eligible only at source visibility |
| `ability_state`, `ability_suppressed` | optional fixed enum/boolean | acting_player_private | copied only for self | eligible only at source visibility |
| `moves`, `revealed_moves` | optional string arrays | acting_player_private | cloned only for self; omitted for opponent | eligible only at source visibility |
| `types`, `volatiles` | string arrays, non-null | public | cloned for both teams | eligible |
| `tera_type` | optional string or null | acting_player_private | copied only for self | eligible only at source visibility |
| `terastallized` | boolean, non-null | public | protocol/request reduction, cloned | eligible |
| `stats`, `boosts` | optional string-to-number maps | acting_player_private | cloned only for self; omitted for opponent | eligible only at source visibility |
| `field.weather`, `field.terrain` | string or null | public | protocol reduction, cloned | eligible |
| `field.pseudo_weather` | string array, non-null | public | protocol reduction, cloned | eligible |
| `field.side_conditions.self`, `field.side_conditions.opponent` | string-to-number maps, non-null | public | perspective-normalized protocol reduction | eligible |

### Request and decision projection

`ObservableChoiceRequestView` copies `player`, `wait`, `team_preview`,
`force_switch`, `trapped`, `rqid`, `active`, `side`, and `legal_actions` from
`ChoiceRequestView`. `raw` is deliberately omitted. `player` is non-null;
`rqid` and `active` are nullable; booleans and arrays are non-null.

`active` copies `moves`, `can_terastallize`, `tera_type`, `trapped`, and
`can_switch`. Each move copies `slot`, `move`, `id`, `pp`, `maxpp`, `target`,
`disabled`, `type`, `category`, `base_power`, and `accuracy` with the same
nullability as `RequestMoveView`; each move is acting-player-private and can be
used only by an acting-player consumer.

Each `side` entry copies `slot`, `ident`, `details`, `condition`, `active`,
`moves`, `stats`, `base_ability`, `ability`, `item`, `tera_type`, and
`terastallized`, with `base_ability`, `ability`, `item`, and `tera_type`
nullable. These are acting-player-private and request-sourced.

`legal_actions` copies the existing fixed-size `mask`, nullable `actions`, and
`available_indices` without changing slot conventions. It is acting-player-
private/action-boundary data, not a new canonical-action contract. An available
index must be an integer in the mask and have a true mask entry; otherwise the
observation is contradictory and fails closed.

The request members are individually defined as follows: `player` is a
non-null player enum and must match `perspective`; `wait`, `team_preview`,
`force_switch`, and `trapped` are non-null booleans copied from the request;
`rqid` is a nullable integer copied from the request; `active` is nullable and
contains the acting player's request moves plus `can_terastallize`, nullable
`tera_type`, `trapped`, and `can_switch`; `side` is a non-null array of
request-side entries; and `legal_actions` is a non-null clone of the existing
fixed-size action set. `active`, `side`, and `legal_actions` are all
acting-player-private. Within each active move, `slot`, `move`, `id`, `pp`,
`maxpp`, `target`, `disabled`, and `base_power` are non-null number/string/
boolean values, while `type`, `category`, and `accuracy` are nullable. Within
each side entry, `slot`, `ident`, `details`, `condition`, `active`, `moves`,
`stats`, and `terastallized` are non-null; `base_ability`, `ability`, `item`,
and `tera_type` are nullable. `raw` is not mapped.

`decision_availability` is:

| Field | Type / nullability | Visibility | Source / transformation | Contradiction behavior | Model input |
|---|---|---|---|---|---|
| `available` | boolean, non-null | derived_observable | false for terminal/requestless/waiting/no-actions; true for a valid request with actions | mask/index contradiction errors | action gating only |
| `reason` | enum, non-null | derived_observable | `request`, `requestless`, `waiting`, `terminal`, or `no_legal_actions` | impossible phase/request combinations error | metadata only |
| `legal_action_indices` | integer array or null | acting_player_private/derived | clone `available_indices`; null when no request or terminal/waiting | never invents actions | action masking only |

## Source mapping and boundaries

`StepResult` is mapped field-by-field as follows:

| `StepResult` field | Observable mapping | Visibility | Transformation / contradiction behavior | Model input |
|---|---|---|---|---|
| `env_id` | not copied; caller supplies `battle_id` | simulator_only | never used as an implicit identity | never |
| `terminated` | cross-checks selected `view.terminated` | public/derived_observable | mismatch errors in `projectStepResult` | terminal feature only |
| `winner` | cross-checks selected `view.winner` | public | mismatch errors in `projectStepResult` | terminal label only |
| `rewards` | excluded | simulator_only | never projected | never |
| `requests` | selects `requests[perspective]` as `request` | acting_player_private | missing entry becomes request-less; side mismatch errors | acting-player consumer only |
| `views` | selects `views[perspective]` as `view` | public + acting_player_private fields | missing view errors; hypothesis fields omitted | eligible by visibility |
| `omniscient` | excluded | simulator_only | never projected | never |
| `log_delta` | excluded from identity; caller must provide full `protocol_prefix` | public evidence delta | never treated as a cursor; future integration must reject an incomplete prefix | audit only |
| `info.turn` | cross-checks selected view turn when supplied by caller | derived_observable | mismatch is a source contradiction | timing metadata |
| `info.format` | cross-checks selected view format when supplied by caller | derived_observable | mismatch is a source contradiction | metadata/feature context |

The adapter's exact input/output mapping for the other sources is:

| Existing source | Observable mapping | Fields intentionally excluded or constrained |
|---|---|---|
| `BattleView` | `view` plus public/acting-player visibility annotations | `env_id` and all `possible_*` hypothesis fields are excluded |
| `ChoiceRequestView` | `request` and `decision_availability` | `raw` is excluded; request must match perspective |
| `StepResult` | `views[perspective]`, `requests[perspective]`, `terminated`, and `winner` are checked by `projectStepResult` | `rewards`, `omniscient`, controller state, and unselected players are excluded; `log_delta` is not a full prefix |
| Raw protocol events | `protocol_prefix`, cursor, hash, and independently derived evidence checks | supported raw records are canonicalized and compared to derived fields; incomplete evidence is not invented, while malformed/unsupported/contradictory evidence fails closed |
| Python replay observations (`parse_replay_logs.py`) | source kind `replay`, explicit protocol prefix, replay/battle ID, perspective, and phase supplied by caller | turn-grouped events are not treated as decision cursors; parser output does not invent request legality |
| `live_private_state.py` | request-side `side`, `active`, and legal-action fields when the acting player owns the request | inferred randbats sets, opponent guesses, and fallback identity are not observable fields |
| `tactical_state.py` | public protocol-derived `view` fields only when built from an explicit prefix | default `p1` fallback is not accepted by the adapter; callers must provide a valid perspective and cutoff |
| `live_private_features.py` / `value_features.py` inputs | future explicit consumers may use eligible public/private fields after validating prefix and perspective | existing vectors consume their current inputs unchanged; no adapter output is routed to models in this slice |

## Rollback and review boundary

Rollback is to remove `sim-core/src/observable_state.ts`, its focused tests, and
this contract revision. Existing `BattleView`, `ChoiceRequestView`,
`StepResult`, Python observations, feature vectors, checkpoints, live defaults,
and search remain intact. `ACTION-001` remains blocked until this contract is
reviewed and accepted.
