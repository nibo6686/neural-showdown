# ObservableBattleState Contract

`STATE-001` defines an additive, shadow-only observation boundary. The
implementation is `sim-core/src/observable_state.ts`; it consumes existing
`BattleView` and `ChoiceRequestView` values and does not replace them. It has no
model, checkpoint, live-default, or search call sites.

## Version and visibility

Supported schemas are `observable-battle-state/v1` (unchanged default) and opt-in
`observable-battle-state/v2` (scoped public opponent stages; accepted). An unknown
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
2. `BattleView.player`, `BattleView.opponent`, `ChoiceRequestView.player`, and
   `perspective` must agree. `view.opponent` must be the exact complement of
   `perspective` (`p1`/`p2`); self-opponents and invalid values are explicit
   contradictions.
3. `event_cursor` is the count of normalized protocol records in
   `protocol_prefix`; it is not a turn number.
4. Normalization converts CRLF/CR to LF, trims record boundaries, and rejects
   empty records. Supported raw commands are shape-validated before projection;
   malformed supported events fail closed just like unknown commands. The hash
   input is the canonical JSON array of the sanitized observable records.
   `protocol_prefix_hash` is SHA-256 of that canonical array.
5. `observation_id` is deterministic: it is `obs-` plus SHA-256 of the canonical
   schema/source/battle/perspective/cursor/hash/phase/request/decision/view
   identity payload.
6. Snapshots own cloned data and are recursively frozen. Later protocol records
   cannot mutate an earlier snapshot. `ObservableStateProjector` retains the
   complete canonical observable record sequence and accepts a later observation
   only when the complete earlier sequence is an exact ordered prefix. Repeated
   records, including successive `|turn|N` records, remain distinct cursor
   entries and are never deduplicated by command name. Rollback, replacement,
   truncation, reordering, altered earlier records, and hash-only claims fail
   closed.
7. A request-less state uses `request: null`, reports `available: false`, and
   uses `legal_action_indices: null`; it never fabricates legal actions.
8. `pre_decision`, `post_resolution`, `forced_switch`, and `terminal` are
   supported phases. Any other well-formed token is normalized to
   `snapshot_phase: other` and retained verbatim in `other_phase`; malformed
   tokens fail closed. A forced-switch phase requires a force-switch request; a
   terminal phase requires a terminated view.
9. Raw protocol evidence has precedence over derived fields. The adapter
   independently parses supported raw records and compares available raw-derived
   `gen`, the latest ordered `turn`, player names, team sizes, winner, and request
   `rqid` values to the projected sources. Matching evidence is accepted,
   incomplete evidence is not invented, malformed or unsupported evidence
   errors, and contradictions raise `ObservableStateContradictionError`.
   Terminal event kind is tracked separately from its winner token, so `|win|X`
   and `|tie|` in either order contradict (including `|win|tie`), while repeated
   identical terminal records are explicitly valid. Terminal evidence also
   requires a terminated view. Raw request `side.id`/`player` values, when
   present, must match `perspective` before request redaction.
   Caller-provided contradiction messages are not a substitute for this
   validation.
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
| `protocol_prefix_hash` | 64-char SHA-256 string, non-null | derived_observable | sanitized observable protocol prefix | canonical sanitized record array | raw prefix/shape errors; never silently repaired | audit only |
| `snapshot_phase` | `pre_decision \| post_resolution \| forced_switch \| terminal \| other`, non-null | derived_observable | caller decision boundary | supported token preserved; unknown well-formed token normalized to `other` | malformed token or impossible phase/request errors | timing metadata |
| `other_phase` | string or null | derived_observable | original unsupported phase token | retained only when `snapshot_phase=other` | mismatch or malformed token errors | timing metadata |
| `request` | `ObservableChoiceRequestView \| null` | public + acting_player_private | `ChoiceRequestView`, excluding `raw` | deep clone and redaction | side/perspective mismatch errors | eligible only for acting-player consumers |
| `decision_availability` | object, non-null | derived_observable | request + terminal state | no legal-action invention | mask/index contradictions error | action masking only; not current model input |
| `protocol_prefix` | string array, non-null | public evidence | raw protocol records | normalize, validate shapes, and replace every raw `\|request\|JSON` record with canonical `\|request\|{"rqid":N}` or `\|request\|{}`; clone and freeze | empty/non-string/malformed records error; raw request payload is never retained | audit/feature source only with explicit cutoff |

The adapter may receive a raw request record as private simulator evidence, but
that payload is transient and never crosses the observable serialization or hash
boundary. Only the nullable request ID is retained in the canonical prefix
record. Private team data, private moves, items, stats, and other request fields
remain available only through the separately classified acting-player-private
`request` projection when the caller has a legitimate request; they are not
copied into `protocol_prefix`.

An array element containing an embedded LF/CR record separator is malformed and
is rejected before command parsing or redaction; each cursor entry therefore
represents exactly one canonical protocol record.

Raw shape validation follows the existing Showdown protocol and
`PlayerStateExtractor` handlers. In particular, a `move` record requires a
valid Pokémon identifier and non-empty move field; its protocol target is
optional for self-targeting moves, and a present non-empty target must be a
valid Pokémon identifier or `-`. `-singleturn` requires a valid Pokémon
identifier and non-empty effect. Optional tags and accepted records are
preserved as text. `switch`, `faint`, request, terminal, numeric, and
status/effect records validate their required fields and types. A command is
not accepted merely because its name is allowlisted.

The current parser also shape-validates `cant`, `-hitcount`, `-fieldactivate`,
`-message`, `detailschange`, and `activate` variants as raw evidence. These
records are not all projected into typed state. In particular, `-singleturn`
is raw-only rather than persistent volatile state, and unclassified generic
aliases remain explicit blockers. See
[`SIMULATOR_COVERAGE.md`](SIMULATOR_COVERAGE.md) for the pinned-format inventory
and current projection limits.

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
Acting-player `self_team` additionally receives the explicit self-only allowlist
`item`, `last_item`, `item_state`, `item_suppressed`, `ability`, `base_ability`,
`ability_state`, `ability_suppressed`, `moves`, `revealed_moves`, `tera_type`,
`stats`, and `boosts`. `opponent_team` omits those fields by default; the only
allowed item signal is the public literal `item: has-item`. No object spread or
whole-`PokemonView` copy is permitted at this boundary. Arrays and maps are
cloned, and the omitted `possible_*` fields are hypothesis fields. A private
field supplied in an opponent `BattleView` is therefore omitted rather than
silently exposed.

This self-only grouping mixes private fields with omitted public evidence. In
particular, protocol-derived `boosts` are public stat stages, not private base stats.
Their omission from opponent observations is a v1 representation limitation, not a
privacy requirement. Do not interpret omission as known zero. Before feature or
faithful-publication acceptance, define an explicit contract/identity-compatible
extension for public opponent stages while retaining protection for private fields.

### Public lifecycle and Illusion — scoped acceptance

The extractor clears boosts and battle volatiles on ordinary departure, drag,
faint and re-entry. It retains permanent status/item evidence where attributed,
keeps Illusion `replace` distinct, and preserves the pinned Eternamax/Dynamax
exception without expanding supported-format coverage. A successful switch tagged
`[from] Shed Tail` copies only the outgoing public Substitute, not boosts or other
volatiles. Ordinary Substitute and failed Shed Tail do not imply transfer.

An active position, its displayed identity and its confirmed roster identity are
distinct. Public position events update an appearance object independently of any
request. A fresh appearance does not inherit its displayed teammate's move/item
history. The prior entry is retained separately so public reveal can restore it
and reconcile current evidence to the real identity. A repeat reveal reuses the
already revealed entry rather than creating a duplicate. Earlier observations are
cloned/frozen snapshots; reveal never edits their state, identity or protocol prefix.
Without public reveal, opponent appearance identity remains uncertain.

Own observations combine public active evidence with the latest legitimate
own-player request at observation time. Requests never mutate public history or
supply identity to the opponent. The addressed active roster member receives the
boosts/volatiles, while inactive uncertain aliases cannot contaminate the bench.
Private move sets come from that member's request. This makes the tested live and
snapshot-restored observations equivalent despite different request delivery history.
Perspective allowlists remain unchanged, including omission of opponent boosts,
private moves, stats and abilities. No simulator-only counters or copy flags are read.

`replace` accepts the pinned conditionless `|replace|IDENT|DETAILS` form. Legacy
condition-bearing records remain supported with validated HP/status syntax; missing
fields, invalid player identity, malformed/empty conditions and excess fields reject.
It preserves existing health/status/boost/volatile evidence when no condition is
provided. Switch/drag still require conditions. The public Illusion Level Mod
`-hint` record emitted on reveal is validated and retained verbatim as raw evidence;
its text produces no typed state. Other unknown commands remain fail-closed.

These corrections preserve schema versions and change content-derived identities
where field values are corrected. The two reproduced Illusion blockers now pass
real both-actor regressions, but acceptance/coverage attestation remain separate.
Other switch/faint fields, linked effects, broader transfers, Revival Blessing and
expiry/layer/field semantics remain open. Keep `faithful_complete_episode:false`.
The [checkpoint](../refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md) records the
exact review scope, hashes and validation.

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

STATE-001 and ACTION-001 are accepted. Any implementation rollback requires a
separate scoped review; it must not erase this accepted contract or its review
history. Existing `BattleView`, `ChoiceRequestView`, `StepResult`, Python
observations, feature vectors, checkpoints, live defaults, and search remain
intact. This contract does not assert complete simulator-state reconstruction; see
[`SIMULATOR_COVERAGE.md`](SIMULATOR_COVERAGE.md) for volatile, field-lifecycle,
and raw-only protocol gaps. PIPELINE-001 and FEATURE-001 remain separate,
unaccepted work.

Combined review (2026-09-24): original Illusion regressions pass, but fresh switch
appearances lose public Tera: explicit `tera:Fire` re-entry produces opponent
`terastallized:false`/Normal types. This violates retained public state; own requests
mask it only for the owner. Correct explicit Tera projection and verify mirrored
replay/publication before acceptance. This is distinct from deferred faint Tera reset.

Tera follow-up implementation (2026-09-24): fresh switch/drag appearances now derive
Terastallized state from explicit public `tera:TYPE` details before resolving types.
This restores public typing without treating displayed identity as confirmed roster
identity. An untagged entry does not inherit the displaced appearance's Tera; reveal
retains the current appearance's Tera. Mirrored switch/drag, restoration and Python
publication checks pass. Combined semantic acceptance remains pending.

Combined semantic acceptance (2026-09-24) supersedes the pending/blocked dispositions
above only for ordinary boost/volatile clearing, Shed Tail Substitute transfer,
Illusion evidence ownership/reveal, conditionless replace/raw-only hint and non-Stellar
public Tera re-entry. Mirrored Fire fixtures establish switch/drag, restoration,
privacy, immutable prefixes and deterministic publication. Faint Tera reset is next;
Stellar defensive typing and other listed lifecycle fields remain unaccepted.
`faithful_complete_episode:false` is unchanged.

Non-Stellar faint Tera implementation (2026-09-24; review pending): public faint
clears the active Terastallized flag and resolves non-Tera species/appearance typing,
retaining known Tera type. Own projection cannot reassert the flag from an older
request. Unrevealed Illusion remains uncertain to the opponent; private owner data
cannot alter its identity. Terminal private request history is retained in opaque
versioned snapshots for exact restoration, never in public prefixes or legal actions.
This does not resolve Stellar or other temporary-form/type lifecycle gaps.

### Faint/terminal-history review — blocked, 2026-09-24

Pinned non-Stellar faint semantics and normal mirrored privacy/Illusion/teammate/
immutable-history checks pass. All four source/test hashes match; reuse build134/full157
TS and prior20 Python evidence. Fresh16 Illusion/Tera tests pass including Python
publication. No production changes or acceptance/attestation in this review.

Blocker: env_manager.ts:55-83 validates the request envelope and roster array but not
its entries. A real terminal snapshot with requests.p1.side.pokemon[0].ident = 7
passes validation, destroys prior state at line441, then throws in selfFromRequest.
Numeric details/condition also reject late; null entries and string stats succeed
as corrupt own observations. Parent confirmed the independent probe:
/tmp/neural-terminal-history-nested-probe.cjs and
/tmp/neural-faint-review-confirmed-probe.json.

The raw request also contains unused active/action and roster fields. Next task:
minimize and recursively validate restoration history before destructive reset,
with mirrored rejection tests preserving fingerprint, observations and usability.
Valid history creates no actions and raw metadata stays out of logs/records; only
its existing opaque snapshot commitment enters lineage. Legacy compatibility limits
remain documented. Four changed files already covered; manifest/list/attestation
unchanged. Both coverage commands fail only digest drift; six self-tests pass.
Current digest300cfa84ccf97db8fb54653a02fe45c657c6c7ce45a4676448bfa60fcf7c0c02;
prior reviewed3b777601e68932a409271b7103a0013b21abbfcc9d8c4f25c0fd118f2dcfc4e2.
Stellar and wider lifecycle gaps remain; faithful_complete_episode:false unchanged.

### Terminal-history validation correction — implementation, 2026-09-24

Nested consumed fields are now validated before teardown, with structured
TerminalRequestHistoryValidationError code/path/reason and no private error values.
Minimal v1 writers retain only the own-roster fields consumed during restoration;
historical raw-v1 readers validate then drop unused action/roster data and canonicalize
Tera markers. Old raw-v1 fingerprints may migrate once; canonical round trips remain
stable. Missing-metadata legacy behavior remains. Valid history creates no actions
or raw public records. Faint semantics unchanged; separate acceptance remains pending.

Only env_manager.ts and illusion.test.ts changed. Parent build136 relevant TS tests
pass, including Python publication; prior20 Python evidence reused. Original five
malformed probes reject with unchanged fingerprints. Nested cases cover both owners,
live-state/branch preservation and continued request execution versus a twin; valid
migration/restoration tests preserve observations. Diff checks pass. Checkpoint has
source hashes and /tmp/neural-history-validation-* evidence.

Manifest/list/attestation untouched; existing list covers all affected source/tests.
Checker commands fail only on digest9a05263276c0f17e7c2f3b6baf77b874c48c07c0967b3858eb91d1fdd4a29016;
six synthetic self-tests pass. Next: review corrected minimal-v1 validation and
migration with the pending faint slice, then separately attest. Wider lifecycle
prerequisites and faithful_complete_episode:false remain unchanged.

### Faint/minimal-v1 restoration acceptance — 2026-09-24

Scoped acceptance closes the pending non-Stellar faint and terminal restoration
slice. Faint deactivates Tera while retaining known type and restoring observable
non-Tera typing; Illusion privacy and teammate/earlier-observation preservation hold.
Minimal-v1 validates consumed nested fields before teardown, returns structured
errors and preserves state/fingerprint/branch/continued choices on rejection.
Only necessary owner-roster fields persist. Terminal restoration creates no actions
or public raw history. Historical raw-v1 normalization may change identity: recapture
references and preserve historical records; old-reference/normalized-state pairing
rejects. Canonical round trips are deterministic and idempotent.

Four input hashes match. Reused build136 TS/prior20 Python and faint evidence;
fresh build18 Illusion tests (including Python publication) and3 coverage tests pass.
Independent review found one wall-clock-only flaky comparator; test-only normalization
now matches existing identity rules, with exact per-run prefix checks unchanged.
No production correction. Lineage probe and logs are in the current checkpoint.

Existing24-file list covers extractor, environment, helper and regressions; no
inclusion changes needed. Updated computed/reviewed digest:
`6aaddf2751640263f13fa29d4e95c1bfb0987bbf78e7274493a30b8126273c70`.
Removed resolved faint-Tera known gap; coverage checker and six self-tests pass.
This supersedes earlier pending/blocked dispositions only for this scoped slice.
Next: Stellar defensive typing correction with mirrored lifecycle/restore/publication
checks. Other fields, linked effects, Revival Blessing and broader episode fidelity
remain open. Keep faithful_complete_episode:false.

### Stellar defensive typing implementation — 2026-09-25; review pending

Pinned Pokemon.getTypes excludes Stellar from replacement defensive typing. Shared
resolveTypes now follows that distinction for ordinary species/Illusion projection,
keeping known Tera type and active flag separate. Own hidden Zoroark retains Dark;
opponent displayed Snorlax retains Normal until reveal, without leaking identity.
Public Stellar protocol evidence remains; opponent-private tera_type stays omitted.
No schema change. Temporary-type/Type-event reconstruction and private Stellar
attack counters remain outside this correction's scope.

Changed: battle_helpers.ts, tests/helpers/state_lifecycle.ts, tests/illusion.test.ts.
Parent build146 relevant TypeScript tests pass; focused28 Illusion tests pass. New
cases cover both actors, direct simulator types, Stellar activation, switch/drag,
reveal/faint, both-perspective privacy, exact immutable prefixes, restoration and
repeatable Python-validated publication. Existing Fire cases remain green; prior20
Python evidence reused. No semantic acceptance/attestation issued. Checkpoint has hashes.

Next: scoped review, then add battle_helpers.ts to the current24-file coverage list
and recompute/attest only if accepted. Helper/Illusion test files already hashed.
Manifest untouched. Current listed digest (excluding battle_helpers) is
f0893ed149ee786be29a8a3a03f3ae820a62dce0d5611637573e4095cd6bef1b;
checker commands fail digest drift, six synthetic self-tests pass. Prior attestation
6aaddf2751640263f13fa29d4e95c1bfb0987bbf78e7274493a30b8126273c70 remains.
Broader lifecycle prerequisites and faithful_complete_episode:false are unchanged.

### Bounded revival evidence — scoped acceptance, 2026-09-25

Own request roster entries gain optional `reviving:true`, copied only from the
addressed simulator request. It is omitted when false/absent and never copied to
BattleView or the shared prefix. This is an additive optional request extension
under observable-battle-state/v1, used with separately versioned revival actions
and records; old ordinary observations are unchanged. The strict belief request
validator accepts only the true-valued optional field.

Pinned revival emits `|-heal|p1: Name|condition|[from] move: Revival Blessing` for
a benched target. The parser allows the bench identifier only for this exact
source-tagged -heal form; unrelated bench heals remain rejected. Existing active
identifier grammar is unchanged. The source-qualified heal clears fainted/status
and obsolete status timing evidence while setting public HP on the named target.
The active healer remains active. This follows battle.ts revival execution and
avoids retaining a burned/poisoned fainted target's old status after revival.

### Public Soak defensive typing — scoped acceptance (2026-09-25)

Public `-start|TARGET|typechange|Water` establishes an ordinary defensive-type
override on the active appearance. Own-request species refresh does not erase it;
Illusion reveal preserves it without transferring evidence to the impersonated
teammate. Public switch/drag/faint lifecycle resets it to the appropriate known
species typing; faint also clears active Tera while retaining known Tera type.
Non-Stellar Tera overrides defensive typing, while Stellar retains the ordinary
public override. Already-Terastallized targets reject Soak in the simulator.

The override is reconstructed from protocol replay, not private simulator state.
No new observation field or version; existing species/displayed identity and
tera_type/terastallized remain distinct. This is bounded Soak behavior plus shared
typechange replacement plumbing, not acceptance of other temporary-type effects.
Exact hashes, passing review checks and coverage attestation are in the PIPELINE-002 checkpoint.
At the Soak review, added-type composition remained excluded. The subsequent
implementation below corrects owner projection and is now separately accepted.

### Public added-type composition — scoped acceptance (2026-09-25)

The public typeadd slot is distinct from ordinary typechange evidence. Both views
compose ordinary types followed by the added type, without the former two-entry cap.
New additions replace that single slot; typechange removes it. Requests do not
supersede protocol evidence. Switch/drag/faint/species resets clear both components;
Tera activation clears the addition, with Stellar retaining ordinary typing.
Illusion reveal retains appearance evidence; own identity never reaches the opponent.
Protocol replay restores the same composition. No schema/snapshot migration.

Forest's Curse plus Soak and fixture-only Trick-or-Treat replacement are tested.
Generic expiry, Transform/Reflect Type and legacy training/live consumers are not
accepted by this change. Exact source hashes, validation and completed coverage
attestation are in the PIPELINE-002 checkpoint; faithful_complete_episode:false remains.

Three entries survive observation cloning and serialized publication bundles, whose
identities Python validates without truncating types. The resulting DATA-001 record
references those observations; it does not produce a three-type feature tensor.
Legacy two-slot training/live consumers require separate compatibility work.
Transform copying remains a reproduced gap: a Mew copying Grass-added Charizard
shows Psychic to its owner instead of Fire/Flying/Grass. This is the next bounded
public-state correction, outside the accepted added-slot application scope.

### Transform defensive typing — scoped acceptance (2026-09-25)

A public -transform snapshots the target's publicly established ordinary typing
and separate added slot. Target Tera defensive type is not copied; caller Tera
keeps precedence. Later changes to either Pokemon do not mutate the other's copy.
Owner requests preserve the original roster species while current/displayed species
and effective typing describe the transformation. Switch/drag/faint restores original
appearance typing; faint also clears active Tera. Replay restores the public maps.
No public schema or private snapshot metadata is added. Three-type record bundles
remain intact through Python validation. Hidden Illusion target failures expose no
identity. General Type hooks/Roost and non-typing Transform mechanics remain excluded.
Exact hashes, reviewed scope and coverage attestation are in PIPELINE-002.
Transform copied boosts remain a reproduced separate gap: target +2 Attack copies
in the simulator but is absent from both caller observations. Other Transform
mechanics and legacy two-type feature consumers are not accepted by this review.

### Transform public boost copying — scoped acceptance (2026-09-25)

At successful public -transform, raw BattleView caller boosts are replaced by a
fresh target-public-map copy. Sparse absent stages mean zero; explicit zeros remain.
Later stage events apply once and independently; existing request refresh, replay
and lifecycle resets preserve these semantics. No private simulator stages are read.

The existing observation allowlist is unchanged: self_team publishes boosts;
opponent_team omits them. Both raw perspectives reflect the public copy, and mirrored
caller-self records preserve the stages without widening opponent publication.
No schema migration. The PIPELINE-002 checkpoint records hashes, validation and the
completed semantic/coverage review. Selective clear and other Transform fields remain
separate gaps; faithful_complete_episode:false.

The boost-copy review accepts both raw perspectives and existing caller-self records,
not complete opponent-stage publication. The next task is an explicit public-stage
representation/compatibility change, with mirrored prefix, restoration and Python
identity checks. Existing v1 records remain immutable; genuinely private fields must
not be added through a blanket raw-view copy.


### Version-two public opponent stages — scoped accepted (2026-09-25)

V2 adds only `view.opponent_team[].public_boosts`: exactly seven keys `atk`, `def`,
`spa`, `spd`, `spe`, `accuracy`, `evasion`, each an integer -6..6 or null. Zero means
public evidence establishes zero; null means this prefix has not established that
stage. V1 continues to omit opponent stages; omitted v1 maps never mean known zero.
Self `boosts` remains the existing sparse map. Private stats, abilities, moves and
simulator-only values are not added. Features are not produced or expanded.

`public_boosts` is reconstructed from the exact sanitized public prefix, independently
of supplied raw boost maps or owner requests. Ordinary switch/drag, faint, clearboost
and clearallboost establish/reset zero; setboost establishes its named stage.
Boost/unboost apply effective public deltas (up to 12 across -6..6); an unknown baseline
stays unknown. Transform replaces stages with an independent copy of the public target
at that event. Illusion stages belong to the displayed active appearance until replace;
reveal reconciles that evidence and restores the impersonated teammate's prior map.
Earlier observations remain immutable. Snapshot restoration uses the same prefix.

This is a bounded singles implementation. Selective positive/negative clears now
zero only known stages of the selected sign, preserving opposite signs, known zero and
unknown null. Raw extraction preserves sparse absent entries. This correction is
scoped accepted (2026-09-25); no schema or identity migration is made.
Negative clearing accepts untagged legacy records and pinned `[silent]`/`[zeffect]` tags.
Spectral Thief's five-field `-anim` is raw-only: its separate boost events alone update
the recipient. Other animation forms reject. Psych Up stage copying is implemented pending review
as described below. Other copying, swap/inversion and Baton Pass
anywhere in the prefix fail explicitly, including when later reset; they must not
silently inherit unresolved raw semantics. Non-singles gametype also rejects. Standard protocol aliases have the same
stage meaning. Broader lifecycle correctness remains separately gated.

Select via `observation_schema_version: 'observable-battle-state/v2'` on a pipeline
session/episode, or the explicit projector schema argument. Unknown versions reject.
Belief and transition inputs cannot mix observation versions. V2 requires explicit
matching versions on belief references/history. Python preserves historically accepted
v1 references lacking a version, interpreting those as v1 only.

There is no in-place migration. V1 serialization, IDs and reference interpretation
remain unchanged. Regeneration requires the original exact public prefixes and legitimate
perspective inputs; it builds new v2 observations, beliefs and dataset record identities.
Do not relabel an old payload or rewrite historical references. Simulator snapshot and
transition identities may remain identical for identical state/actions: those identify
execution, independently of the observation representation. Existing outer bundle,
belief, transition and dataset container versions remain valid because their nested
observation version is explicit; dataset `schema_fingerprints.observation` reports it.
TS and Python validate v2 stages against the prefix; Python additionally verifies the
v2 observation content identity. No feature or faithful-publication acceptance follows;
`faithful_complete_episode:false` remains.


Review disposition (2026-09-25): v2 acceptance is blocked by Python content-identity
validation. Relabeling v2 as v1 can retain stale observation/belief IDs; TS rejects
the same payload. The normative no-relabeling rule above is not yet fully enforced
in the Python publication boundary. See the PIPELINE-002 checkpoint reproduction.
No coverage attestation or faithful-publication acceptance is implied.


### Python identity correction — implementation, review pending (2026-09-25)

Python publication now verifies input/successor observation and belief content hashes
unconditionally for observable v1/v2, plus nested evidence/candidate IDs and reference
joins. It rejects stale IDs without repairing records. TS-compatible serialization
uses UTF-16 key ordering, JSON Unicode/surrogate escaping, binary64 numbers and distinct
absent/null fields. DATA-001's separate canonicalization remains unchanged.

Supported legacy v1 references may omit only schema_version while retaining all other
reference fields and valid content identities/history. Omission stays absent in hashing;
null/unknown versions, ID-only references and arbitrary IDs do not qualify. Full v2
references remain explicit. Historical records and lineage are never rewritten. Prior
Python synthetic unit fixtures now use content-bound IDs; they were not historical data.
Historical observation payloads cannot be recovered from references alone: validation
checks anchored prefix/history consistency, not unseen content. See the checkpoint for
new cross-runtime regressions and exact hashes. The prior downgrade blockers are
corrected in implementation; combined v2 acceptance/coverage attestation remain pending.


### Combined v2 publication acceptance — scoped (2026-09-25)

This verdict supersedes the preceding pending/blocked v2, Python identity and historical
reference dispositions only for their stated scope. Opt-in v2 public opponent stages,
content-bound observation/belief identities and complete six-field reference checks
are accepted. Default v1 and valid historical identities remain unchanged; only Python
supported v1 references may omit schema_version, without injecting it into hashes.
Negative first cursors and trailing-newline IDs reject as malformed. Rehashed false
stages still reject against public-prefix evidence; hashes alone are insufficient.

The prior accepted 44-file coverage digest is attested (current selective-clear changes
remain pending a new review):
`96e85e8903e00b681ce029b58d69d72c284595102bc1ffee855894779fcee11d`.
Fresh build/26 focused cases, independent original reproductions, coverage checker, ten
drift self-tests and three coverage tests pass; matching broader evidence is retained.
See the PIPELINE-002 checkpoint for exact scope and identities. Selective stage clears,
other excluded effects, feature extraction and broader lifecycle completeness remain
separate gates. `faithful_complete_episode:false` remains required.


### Selective stage clearing review (2026-09-25)

Scoped accepted: first-target sign-only zeroing, opposite/zero/null retention, independent
ordered recipient deltas and exact negative tags/narrow Spectral Thief animation. The
existing positive-clear grammar remains broader than its reviewed pinned emitter; no
general animation or format expansion is implied. Correctly rehashed false stage values
still reject against prefix evidence. Historical identities are not rewritten; newly
corrected raw/self projections may differ for formerly incorrect trajectories.
45-file digest attested: `15e0e2b5c8b77b615a420be79634f4d3fc01924a5723eb02ddcc040e867064a9`.
Coverage checker, ten drift self-tests and three coverage tests pass. Copy/swap/inversion,
Baton Pass, features and broader lifecycle fidelity remain excluded.


### Bounded Psych Up stages — implementation pending review (2026-09-25)

Only `|-copyboost|RECIPIENT|DONOR|[from] move: Psych Up` is newly supported: replace the
recipient's seven public stages with an independent donor snapshot at that event.
Unknown donor stages remain null in v2 and absent in raw sparse evidence; stale
recipient stages are removed. No type/species/private-stat copying is implied. V1
remains default; opponent stages remain v2-only. Existing identities are not migrated.
Missing/extra fields, other tags (including Costar), swap/inversion and Baton Pass
remain unsupported. Exact-prefix evidence validation remains mandatory even with valid
content hashes. Psych Up's critical-hit volatile removal/copying is not inferred from
this event; ordinary emitted records retain existing handling, while silent/layered
changes remain unresolved. Stage-only support does not claim full Psych Up support.
Coverage classification/hash inclusion and semantic acceptance remain pending.


Psych Up review (2026-09-25) remains blocked: malformed recipient identifiers bypass
TS/Python evidence-helper grammar and Python can publish correctly rehashed invalid
prefixes, although TS observable parsing rejects. Validate both full identifiers and
exact copy grammar before player-side filtering. See the current PIPELINE-002 checkpoint
and durable reproduction; no semantic acceptance or new coverage attestation is granted.


Psych Up grammar correction (2026-09-25), pending review: both evidence helpers check
exact field count/tag and both identifiers before side filtering. Identifier syntax
matches the existing trimmed observable grammar; roster presence is not required and
unresolved donor stages remain null. Python's shared publication prefix validation also
applies this guard to v1, closing the label bypass without changing valid v1 records,
defaults or identities. Three original malformed bundles now reject before output;
200 rehashed cross-runtime cases pass. Combined acceptance/coverage remain pending.


Combined Psych Up review (2026-09-25): canonical pre-filter correction passes, but
attestation remains blocked. Bare `copyboost` is not a supported observable command;
Python v1 can bypass the canonical guard and Python v2 normalizes the alias. Both can
publish fully rehashed bundles rejected by TS. Reject unsupported spelling at publication
entry independently of internal helper alias handling; preserve canonical/v1 identities.
Durable reproductions and next correction are in the current PIPELINE-002 checkpoint.


Bare-alias correction implemented (2026-09-25), review pending: Python v1/v2 publication
rejects bare `copyboost` before stage reconstruction, matching TypeScript's command
allowlist. Canonical `-copyboost` and internal helper alias behavior are unchanged.
Valid identities are preserved; expanded rehashed matrix verifies protocol rejection.
No new semantic acceptance or coverage attestation; critical-hit volatiles stay excluded.


### Combined Psych Up scoped acceptance — 2026-09-25

The preceding pending/blocked Psych Up dispositions are superseded within this scope.
Canonical exact-tag stage copying and pre-filter grammar are accepted; bare copyboost
rejects in Python/TS publication for both versions. Internal helper aliases do not expand
publishable grammar. Independent replacement, zero/null semantics, original failures,
fully rehashed false-stage rejection and unchanged valid historical IDs are verified.
Critical-hit volatiles, Costar, swap/inversion/Baton Pass and broader identity routing
remain excluded. V1 default and opt-in v2 are unchanged.54-file digest attested:
`d5e51397777285eb10e702d5998bbd7ccf1de371180301129406e0c2cbb28ae3`. Checker/self-tests/coverage tests pass.
`faithful_complete_episode:false` remains required.


### Bounded Topsy-Turvy inversion — implementation pending review (2026-09-25)

Canonical `|-invertboost|TARGET|[from] move: Topsy-Turvy` negates target public known
nonzero stages at the event; known zero stays zero and unknown stays null in v2 (absent
in sparse raw maps). All-zero simulator failure emits no inversion. Both evidence helpers
validate exact tag/count/target before routing. Python v1/v2 publication rejects bare
invertboost before reconstruction; internal helper aliases do not expand grammar.
V1 defaults, historical identities and schemas are unchanged. Rigged Dice and other
mod/tag variants remain unsupported. Semantic classification/coverage review pending;
faithful_complete_episode:false remains required.
