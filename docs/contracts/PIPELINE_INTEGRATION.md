# PIPELINE-001: checkpoint-free transition integration

Status: accepted for PIPELINE-001 v1's explicit joint-actionable boundary scope
on 2026-09-24 review. Complete-episode progression remains PIPELINE-002.
The additive ordinary one-sided forced-switch slice below passed separate semantic
review on 2026-09-24; complete-episode readiness remains unaccepted.

Review verdict (2026-09-24): accept the checkpoint-free implementation within
the v1 boundary scope described below. Focused simulator, perspective,
successor-lineage, deterministic-identity, validator, protocol-stop, and
rejected-candidate evidence passed. The pinned state/protocol inventory is in
[`SIMULATOR_COVERAGE.md`](SIMULATOR_COVERAGE.md). In that inventory,
`-singleturn` and several outcome/field records are raw-only; unsupported or
unknown records must fail closed. Separate joint/request-reporting and ordinary
forced-switch reviews stand; the bounded settling lifecycle below passed separate
semantic review on 2026-09-24 and is included in the current attestation. PIPELINE-001
supports only joint actionable requests, including joint forced switches; it
does not collect complete episodes or implement PIPELINE-002 boundaries.

Natural rejection is demonstrated by the focused hidden-trap regression:
under a reproducible `gen9randombattle` seed, p1 switches to Dugtrio with Arena
Trap while p2 switches to Steel-type Tinkaton. Showdown can report a hidden
trap as `maybeTrapped` without setting the request's `trapped` flag, so the
current request-derived action index permits a switch. `Side.chooseSwitch`
then rejects that switch through its ordinary simulator choice-error path.
The pipeline rejects the disposable candidate and preserves the committed
snapshot, prefix cursor, and observation/belief lineage. This closes the
natural-rejection criterion for the supported action encoding; injected failure
tests remain separate evidence.

No feature extractor or training target is defined. The pipeline must not add
target fields, materialize features, or produce a dataset before FEATURE-001
and target/reward decisions are reviewed. Old checkpoints are abandoned for
the new approach and are not a dependency.

This additive integration path connects a real `LocalBattleEnv` boundary to
the accepted observable-state, belief-state, canonical-action, seeded-transition
and DATA-001 contracts. It is an integration harness and record validator, not a
feature extractor, labeler, bulk collector, trainer, or live evaluator.

## Versioned path

`sim-core/src/pipeline_integration.ts` owns the in-process authoritative
simulator snapshot and builds the following chain for each perspective:

`StepResult + spectator prefix -> ObservableBattleState -> BeliefState ->
CanonicalAction -> SeededTransition -> successor observation/belief ->
perspective-specific linked record bundle`.

The current step is executed on a disposable environment restored from the
authoritative serialized snapshot. The candidate becomes the session state only
after the simulator returns without a rejection diagnostic, the successor
prefix extends the prior prefix, and both successor beliefs validate their
transition joins. A rejected or failed candidate is closed and is not published.

The JSON bridge in `trainer/src/neural/pipeline_record.py` accepts one
`pipeline-linked-record/v1` bundle per acting perspective. It verifies the
canonical action against that perspective's request; input and successor
observation/belief references; prefix extension; transition branch and
fingerprint joins; and the privacy boundary. It then creates and validates one
DATA-001 record. The bridge can run as a finite `python -m neural.pipeline_record`
stdin/stdout process. It does not start a server.

## Prefix projection policy

`sim-core-observable-prefix/v1` applies these transformations before
`ObservableBattleState` projection:

- Drop the standalone `|` protocol framing record.
- Drop `|tier|...`; the same ruleset is represented by the boundary's `format`.
- Drop `|request|...` records because they can contain either player's private
  request. The acting player's request is carried only in that perspective's
  `ObservableBattleState`; request payloads never enter the shared prefix.
- Replace a numeric `|t:|<digits>` timestamp with `|t:|0` for stable observable
  prefix identity. The raw transition delta remains simulator-internal and is
  not included in the linked record bundle.
- Pass established records unchanged. Unsupported or malformed records fail
  closed as `pipeline/v1/unsupported-observable-protocol`; the collector does
  not silently filter unknown commands or malformed raw records. The unresolved
  aliases `clearstatus`, `-clearstatus`, and `nothing` stop projection with
  `pipeline/v1/unresolved-protocol-alias` and a `pipeline-diagnostic/v1` payload
  containing the input `record_index` and `record_command`. The parser may
  shape-check those records for raw observation evidence, but the pipeline
  rejects them before publishing a boundary or linked record. The Python
  `pipeline_record` validator independently rejects the same aliases in input
  or successor prefixes before constructing a DATA-001 record, and its one-shot
  CLI returns the same structured diagnostic schema.
- `-nothing` is a distinct, supported no-payload record. The pinned Gen 9
  source emits it from Splash (`pokemon-showdown/data/moves.ts:18380-18384`);
  it is retained as raw-only evidence and does not alias `nothing`.
- Move records require an active actor ident. The target field may be omitted
  or empty; a non-empty target is a Pokémon reference such as `p2a: Eevee` or
  `p1: Phione`, with an optional active-position letter. Showdown's
  `Pokemon.toString()` uses the latter form for non-active Pokémon, and
  side-target moves may name fainted Pokémon (`sim/pokemon.ts:504-512`,
  `sim/SIM-PROTOCOL.md:240-245`). `BattleActions.useMoveInner` can serialize a
  null target as literal `null`, include source-generated `[from]` or `[anim]`
  metadata fields, and append `[notarget]` last (`sim/battle-actions.ts:446-462`).
  The parser accepts `null` only with exactly one final `[notarget]`; before it,
  only the source-supported `[from]` and `[anim]` tags are allowed. Move tags
  use the pinned emitter forms `[from]`, `[anim]`, `[still]`, `[spread]`,
  `[miss]`, `[notarget]`, and `[zeffect]`; unsupported tag names fail closed.
  `[notarget]` is never parsed as a target. The raw record remains unchanged in
  the prefix.
- The public `|-singleturn|POKEMON|EFFECT` event remains supported raw evidence;
  established raw-only records such as `-message`, `-fieldactivate`, and
  `-nothing` remain distinguishable from the three unresolved aliases.
- The parser also shape-validates `cant`, `-hitcount`, `-fieldactivate`,
  `-message`, `detailschange`, and `activate` variants. These are raw protocol
  evidence unless the state inventory specifies a typed projection. Generic
  aliases with unknown scoped grammar remain a collection stop condition.

The DATA-001 `observation_prefix_hash` uses its Python `ensure_ascii=True`
canonical JSON rule. `ObservableBattleState.protocol_prefix_hash` uses the
TypeScript canonical JSON rule with literal Unicode. The two hashes are
validated independently and are not required to match for non-ASCII prefixes.

## Boundary behavior

Pipeline v1 executes a transition only when both players have current actionable
requests and canonical legal actions. It does not synthesize a pass action for a
waiting side.

| Boundary | v1 behavior |
| --- | --- |
| Both players actionable | Execute one seeded joint transition. |
| Joint forced switches | Execute only when both current requests and selected legal switch actions validate. |
| One-sided forced switch | Legacy `step()` still fails with `pipeline/v1/unsupported-one-sided-forced-switch`. The separately versioned `stepForcedSwitch(action)` path below handles an ordinary switch plus an actual waiting request. |
| One-sided requestless | An actionable move request plus an absent request fails with `pipeline/v1/unsupported-one-sided-requestless`; do not advance. An actionable move request plus a wait request is classified as waiting. |
| Waiting | Fail with `pipeline/v1/unsupported-waiting-boundary`; do not advance or synthesize a pass/default action. |
| Requestless nonterminal | Fail with `pipeline/v1/unsupported-requestless-boundary`; do not advance or infer that no request means a default action. |
| Terminal | Project a terminal successor when all protocol evidence is supported; reject a later transition with `pipeline/v1/terminal-boundary`. Unsupported events fail with `pipeline/v1/unsupported-observable-protocol`. |
| Invalid, stale, or simulator-rejected action | Reject the candidate; retain the last committed boundary and snapshot. |

The postflight rejection guarantee is exercised by both a naturally occurring
hidden-trap rejection and a separately labeled injected diagnostic regression.
The natural case is source-backed by the pinned Gen 9 Random Battle sets and
Showdown request/choice handling (`data/random-battles/gen9/sets.json`,
`sim/pokemon.ts`, `sim/side.ts`, and `sim/battle.ts`).

The current harness is not a complete-episode collector. If an episode reaches a
boundary outside the legacy `step()` joint-actionable scope, that API must
stop with the boundary code and preserve the last committed observation cursor,
snapshot, and lineage. They must not silently drop the episode or label it
terminal/completed. Any later bounded dataset policy must retain a completion or
explicit truncation outcome and reason.

## PIPELINE-002 — Complete-episode boundary progression

This follow-up defines and implements progression for one-sided forced-switch,
waiting, one-sided requestless, and both-sides requestless states before any
claim of complete-battle collection. Acceptance requires:

1. Specify each player's request state independently, including `null`,
   `wait=true`, forced switch, request ID, phase, and the exact protocol cursor.
   Classification must not collapse an actionable player plus a waiting player
   into an undifferentiated requestless case.
2. For one-sided forced switch, advance only from the actual pending forced
   switch request and its current legal switch set. The non-actionable side gets
   no invented pass/default action; prove the Showdown stream's supported
   submission shape and successor request lineage.
3. For waiting states, wait for simulator-emitted progress or a new actionable
   request. For requestless nonterminal states, define which engine events may
   settle the boundary and how to detect a stable next decision. Do not infer
   hidden simulator state or submit synthetic choices.
4. Use candidate execution and atomic publication. A rejected, malformed, or
   unsupported progression leaves the last committed state fingerprint,
   prefix, snapshot, and observation/belief lineage unchanged.
5. Add real simulator-produced regressions for each supported state and
   requestless/wait combination, plus both perspectives, successor prefixes,
   action legality, and terminal completion. Synthetic classification tests do
   not substitute for source/runtime boundary cases.
6. Define complete versus truncated episode metadata for a later collector.
   No incomplete episode may be silently omitted or counted as terminal; record
   battle identity, last committed cursor, boundary kind, stop code, and reason.
7. Obtain separate review of the boundary state machine and explicit supported
   scope before PIPELINE-002 or a full-episode collector is accepted.

### Request-state reporting implementation — 2026-09-24

The first PIPELINE-002 slice opts into `include_wait_requests` and exports
`classifyPipelineRequestState(observation)`. Each call reads only that player's
observation and returns `actionable`, `forced_switch`, `waiting`, `requestless`,
`terminal`, or `no_legal_actions`. Terminal takes precedence; a wait request is
never actionable. A non-waiting request without available legal actions produces
`pipeline/v1/no-legal-actions` when classifying a nonterminal pipeline boundary.

The existing aggregate `boundary.kind` remains an execution summary. A forced
switch plus wait or absence remains `one_sided_forced_switch`; callers use the
per-player classifier to distinguish the partner's state. An actionable move
request plus wait now yields `waiting`, while plus absence yields
`one_sided_requestless`. All these combinations still fail the v1 execution
guard. Joint actionable requests, including joint forced switches, retain their
existing transition/action/identity contracts.

Waiting observations retain their addressed request, empty legal-action set,
request ID (including null), and exact prefix cursor, using `post_resolution`
phase. The shared prefix contains no private request payload. Existing
observation, transition and linked-record schemas already express these values;
no serialized field or schema version was added. Observation IDs appropriately
reflect newly preserved wait evidence; previously supported joint identities
remain unchanged.

Real simulator tests cover forced-switch/wait, consumed-request absence for
either player, snapshot restoration, terminal restoration, and both-perspective
Python record validation. See the [checkpoint](../refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md)
for the separate 2026-09-24 semantic review accepting this reporting slice and
its coverage digest, including environment regressions. PIPELINE-001's recorded
scoped acceptance stands. The reporting review does not accept one-sided
execution or complete-episode progression; the separately accepted execution slice follows.

### One-sided execution — scoped acceptance 2026-09-24

`session.stepForcedSwitch(action)` requires an ordinary forced-switch actor and
a waiting partner. It delegates to `seeded-forced-switch/v1` on a restored
candidate; `step()` and all existing joint schemas remain unchanged. Revival
Blessing, forced-switch-plus-absence, generic waiting/requestless, and terminal
inputs remain rejected. The method requires an explicit canonical switch.

Success returns `acting_player`, `waiting_player`, the shared `transition_id`,
the boundary with both updated perspective observations/beliefs, and
`record_bundles` with exactly the acting player's key. Both beliefs retain their
own predecessor observation/belief references and the same simulator branch.
The waiting player's updated belief is not an action-labelled record.

Actor bundles use `pipeline-forced-switch-record/v1`, retaining the existing
per-perspective envelope fields. Their transition reference uses
`pipeline-forced-switch-reference/v1` and adds only `acting_player` and
`waiting_player` to the existing reference fields. A waiting player ID is not
a private request; no waiting request/action, raw delta, root seed or snapshot
payload enters the actor bundle. Belief/observation serialized schemas stay v1;
belief projection accepts the additional internal metadata schema and enforces
exactly one action ID belonging to the actor.

The Python bridge accepts paired bundle/reference versions, validates actor
identity, complementary roles, ordinary forced-switch input, canonical action,
prefix extension and all observation/belief/snapshot joins. It rejects version
mixing and extra fields (including waiting-player payloads). DATA-001 remains
`dataset-record/v1`, with transition fingerprint `seeded-forced-switch/v1` for
these records; joint records retain `seeded-transition/v1`. As for joint records,
Python verifies published joins, not the private seed-based transition hash.

Publication occurs only after both successor beliefs and the actor bundle are
constructed. Postflight rejection, unsupported protocol or malformed metadata
discards the candidate. Failure to dispose of the previous environment after
commit is retained for retry at `close()`, never reported as candidate rejection.
This shared cleanup rule preserves successful joint identities and outputs.

Tests cover natural KO/pivot boundaries for both actor IDs, repeatability,
Python actor-only validation, subsequent joint play, live preflight errors,
source-shaped synthetic revival exclusion, injected post-execution rejection,
malformed projection/action metadata and post-commit disposal failure.
A separate review accepted this ordinary forced-switch-plus-wait slice.
No natural revival or full-episode acceptance is claimed. Validation and attestation
are in the [checkpoint](../refactor/PIPELINE-002-GAP-DISPOSITION-2026-09-24.md).

## Bounded settling — scoped acceptance 2026-09-24

`LocalBattleEnv` now waits for delivery completion instead of one event-loop
turn. Source criteria are pinned to Showdown 0.11.10:

- `sim/battle-stream.ts:64-76`: `_write` synchronously processes choices, then
  calls `sendUpdates`; `pushMessage` emits the resulting messages.
- `sim/battle.ts:1300-1324`: `makeRequest` emits addressed requests before the
  write's final public update. A request alone is not a complete boundary.
- `sim/battle-stream.ts:292-320`: `getPlayerStreams` asynchronously routes each
  `update` to both player streams and the spectator, and each `sideupdate` only
  to its addressed player. `end` is ignored by that dispatcher.
- `sim/battle.ts:3196-3241`: final public output precedes the `end` signal.

The barrier counts expected deliveries at source emission and acknowledges
chunks only after each player tracker/request handler or spectator log consumer
has processed them. A decision requires all three delivery counts to match,
neither perspective to be terminal, and a pending external request. This retains
low-level partial-choice reporting: the other request may be consumed or waiting;
the existing pipeline guards still decide whether a transition is supported.
Intermediate requestless output keeps waiting and never generates a choice.
A terminal boundary requires matched deliveries, both views terminated with the
same winner, and the source `end` signal. Only the signal's existence is retained;
its private payload is never projected. EOF after that signal may precede buffered
terminal delivery; missing delivery on a closed consumer is premature closure.
EOF at a decision or before a terminal signal is an error.

Defaults are **5,000 ms** per settling wait and **100,000 source messages** since
the previous settled boundary (or stream creation). Candidate restoration and
execution each settle separately. The message budget includes requests, public
updates and end signals; it is not a battle-turn budget. The monotonic deadline
is checked on output and wake-up as well as by a timer, so a continuing microtask
stream cannot starve the timeout. These controls cannot preempt a synchronous
simulator call. `SettlingOptions` can override positive limits in process through
`LocalBattleEnv`'s fifth constructor argument or session `settling` options;
clock/scheduler injection supports controlled tests. No RPC option or successful
transition/observation/record schema changed, and controls do not enter identities.

Failures reject with `SettlingError.diagnostic`, schema `settling-failure/v1`,
containing exactly `schema_version`, `code`, `timeout_ms`, `max_messages`.
Codes are `settling/v1/timeout` (including silent stall), `message-limit`,
`simulator-error`, `stream-closed`, and `cancelled` with the same prefix.
Diagnostics contain no raw stream payload. Existing recoverable invalid-choice
handling remains separate; fatal source/consumer errors use `simulator-error`.
No failure is a terminal result or an episode truncation record.

Failure clears the timer/wait registration, stops automatic consumers, ends the
source, joins consumer tasks and clears environment resources. Concurrent close
and failure cleanup share one destruction promise. The failed low-level environment
must be reset; session candidates are disposable, so the committed environment,
snapshot, prefix, boundary and lineage remain unchanged and no successor bundle
is returned. Previously accepted joint/forced-switch guards and atomic publication
remain in force. Separate semantic review accepted this lifecycle for serialized
session operations on 2026-09-24: checkpoint hashes matched, all 18 settling
regressions passed freshly, and controlled probes verified non-resetting budgets
and rejection of late output after failure. The expanded coverage list includes
the barrier and its tests. Complete-episode outcomes, rejection recovery and
typed-state cleanup remain separate milestones; see the current checkpoint.

## Episode orchestration — accepted 2026-09-24

The additive [bounded episode runner](PIPELINE_EPISODE.md) composes these accepted
session methods and closes its exclusively owned session. Its control-plane outcome
separates execution completion, truncation and failure; existing actor records remain
unchanged. `assertOrdinaryForcedSwitchRequests()` checks all live forced requests
before runner attempts, including joint ones, so Revival Blessing explicitly truncates
without publishing private flags. Prior session entry-point behavior is unchanged.
The runner and preflight passed separate semantic review; their source/test coverage
is attested. Acceptance covers finite accounting, explicit outcomes, current-request
recovery and committed publication under exclusive serialized-session ownership.
Runtime completion does not establish faithful complete-episode publication.

## Record and privacy limits

The bridge emits an acting-player-specific DATA-001 envelope with observation,
action, belief and transition IDs. Its PIPELINE link bundle contains that
perspective's input and successor observations/beliefs and canonical action.
Transition metadata is projected to one perspective's action ID and the lineage
fields needed for joins; it omits both-player action metadata, RNG seed, raw log
delta and simulator state.

The record marks `private_data_provenance=acting_player_request` and
`feature_input_eligibility=acting_player_private`, because the canonical action
was selected from that player's legal request. `input_fields` is empty and
`feature_cursor` is zero. The required feature-schema fingerprint uses the
explicit `features-not-produced/v1` sentinel; it does not define a feature
vector, mapping, scaling rule or model input contract.

This vertical slice does not define reward targets, horizons, discounts,
training splits beyond DATA-001's battle grouping, model semantics or runtime
loading. It does not prove simulator mechanics correct, model quality, or live
route readiness. Those remain separate gates. No dataset is generated by the
integration tests beyond temporary in-memory records validated by the Python
bridge.

## Bounded Revival Blessing — scoped acceptance, 2026-09-25

`revival_selection` is distinct from `forced_switch`; its boundary is
`one_sided_revival`. `stepRevival` requires a revive action; `stepForcedSwitch`
continues to accept only ordinary switch actions. Both share candidate/commit
execution. The addressed request preserves optional `side[].reviving:true` only;
false/absent flags are omitted so ordinary observation identities remain unchanged.
The partner sees its own wait request, never the actor's private target roster.

Actor publication uses `pipeline-revival-record/v1` and
`pipeline-revival-reference/v1`, with the same exact fields and roles as the
ordinary one-sided schemas. Both successor observations and beliefs advance;
only the actor receives a record. Python validates revival schema/action pairing,
fainted target eligibility and slot binding, roles, identities and lineage; its
DATA-001 transition fingerprint is `seeded-revival/v1`. Private snapshots remain
opaque. No feature or training target is produced.

These additions implement only the bounded revival path; prior statements that
all revival is excluded describe the earlier accepted implementation. Separate 2026-09-25 review accepts and attests this bounded scope; unsupported
variants and faithful complete-episode publication remain unaccepted.


### Opt-in public stages — implementation, review pending (2026-09-25)

Session/episode option `observation_schema_version` defaults to observable v1; explicit
v2 adds prefix-derived opponent `public_boosts` to both successor perspectives. The
option is fixed per session. Existing record/bundle and transition container versions
remain unchanged; nested observation schema and dataset fingerprint distinguish v2.
Joint, forced-switch and revival inputs reject unknown/mixed observation versions.
Stage projection occurs before commit/publication; unsupported public-stage evidence
rejects the candidate with the prior boundary intact. Actor-only publication rules
remain unchanged. No feature production or faithful-complete-episode claim is added.


### Combined v2 publication acceptance — scoped (2026-09-25)

This verdict supersedes the preceding pending/blocked v2, Python identity and historical
reference dispositions only for their stated scope. Opt-in v2 public opponent stages,
content-bound observation/belief identities and complete six-field reference checks
are accepted. Default v1 and valid historical identities remain unchanged; only Python
supported v1 references may omit schema_version, without injecting it into hashes.
Negative first cursors and trailing-newline IDs reject as malformed. Rehashed false
stages still reject against public-prefix evidence; hashes alone are insufficient.

The 44-file coverage digest is attested:
`96e85e8903e00b681ce029b58d69d72c284595102bc1ffee855894779fcee11d`.
Fresh build/26 focused cases, independent original reproductions, coverage checker, ten
drift self-tests and three coverage tests pass; matching broader evidence is retained.
See the PIPELINE-002 checkpoint for exact scope and identities. Selective stage clears,
other excluded effects, feature extraction and broader lifecycle completeness remain
separate gates. `faithful_complete_episode:false` remains required.
