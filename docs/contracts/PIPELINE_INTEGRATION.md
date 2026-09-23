# PIPELINE-001: checkpoint-free transition integration

Status: implementation candidate; acceptance remains subject to review.

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
- Pass every other record unchanged. Unsupported or malformed records fail
  closed as `pipeline/v1/unsupported-observable-protocol`; the collector does
  not silently filter unknown commands or malformed raw records. For example,
  the pinned simulator may emit `|-singleturn|`, which the current
  observable-state allowlist does not accept; self-target move records can
  also omit a target field that the current parser requires. Such terminal
  results are reported as unsupported evidence; this integration does not hide
  the record or claim a complete terminal projection.

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
| One-sided forced switch | Fail with `pipeline/v1/unsupported-one-sided-forced-switch`; do not advance. |
| One-sided requestless | Fail with `pipeline/v1/unsupported-one-sided-requestless`; do not advance. |
| Waiting | Fail with `pipeline/v1/unsupported-waiting-boundary`; do not advance. |
| Requestless nonterminal | Fail with `pipeline/v1/unsupported-requestless-boundary`; do not advance. |
| Terminal | Project a terminal successor when all protocol evidence is supported; reject a later transition with `pipeline/v1/terminal-boundary`. Unsupported events fail with `pipeline/v1/unsupported-observable-protocol`. |
| Invalid, stale, or simulator-rejected action | Reject the candidate; retain the last committed boundary and snapshot. |

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
