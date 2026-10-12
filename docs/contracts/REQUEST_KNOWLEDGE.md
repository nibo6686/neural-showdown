# request-knowledge/v1 — S01b candidate sidecar

Status: local candidate for lead review, 2026-10-10 (Prompt 14). Non-publishing: no bundle, episode, dataset or observation carries it yet (S01c). It does not edit `PERSPECTIVE_KNOWLEDGE.md`, observable v1/v2, `pipeline_*`, the action codec or any schema. Runtime: `sim-core/src/request_knowledge.ts` (`buildRequestKnowledge`) and `trainer/src/neural/request_knowledge.py` (`build_request_knowledge`, independent `validate_request_knowledge`). Design: `docs/planning/perspective-fidelity-prompt13-design.md`; decisions: `prompt13-lead-review.md` 1-6.

## Inputs and refusals

`build(owner, raw_text, observation, provenance)`: the exact addressed JSON text of the owner's request (or `null`), the already-validated v1/v2 observation of the same boundary, and a provenance token. Only `fresh_delivery` is accepted: a request freshly delivered to that owner. The token is **procedural and advisory only**: it is a caller assertion, not evidence. The builders (TS and Python) check just the token; the TypeScript side has no registry check at all, and only the Python validator can consult a delivery registry. Snapshot-restored `StepResult.requests` must be passed as anything else and are refused (`provenance`); restored-branch repair is S01c. A text that is self-consistent but stale (for example a pre-rejection request re-emitted by a restored session) cannot be detected from text alone; the Python validator detects it only when a delivery registry knows a later delivery to the same owner at the same cursor.

Fail-closed grammar (singles only): exactly one of `active` (1 entry), `wait:true`, `forceSwitch:[true]`; keys `side` (`id`, `name`, `pokemon` 1..6), optional `rqid`, `noCancel`. `active[0]` keys: `moves` (1..4 rows of `move,id,pp,maxpp,target,disabled`), `maybeDisabled`, `maybeTrapped`, `trapped` (each only `true`), `canTerastallize`. Unknown keys, doubles (more than one `active`/`forceSwitch` entry or active roster member), `teamPreview`, duplicate JSON keys, floats, `pp`/`maxpp` not in 0..2147483647 and raw text over 65536 Unicode scalars reject. `side.id` and every roster `ident` prefix must equal the owner.

## Record (exact key set; ASCII keys; no floats; booleans never integers)

`schema_version` (`request-knowledge/v1`), `id` (`rkn-<64hex>`), `battle_id`, `perspective`, `observation_schema_version`, `observation_id`, `event_cursor` (= observation cursor), `presence`, `request_present`, `raw_request` (exact text or null; null iff `request_present` false), `rqid` (int or null), `active`.

`active` is null unless `presence=actionable`; otherwise `lock`, `trapped`, `maybe_trapped`, `maybe_disabled`, `switch_in_available`, `derivation`, `moves[]` (`slot,id,name,pp,max_pp,target,disabled`). Move values are null iff the raw key is absent; a real `0` stays `0`. `lock`: a single row with neither `pp` nor `maxpp` is `recharge` (`id=recharge`), `struggle` (`id=struggle`) or `locked_move` (any other id; Outrage, Rollout, Uproar, Solar Beam); otherwise `no_hard_lock`. Soft locks (Choice item, Encore, PP 0, Taunt, Imprison disables) are **not modelled as locks**: they appear only as `disabled` booleans on pp-bearing rows and the record says `no_hard_lock`. `derivation.lock` is `bare_single_row` (the rule above applied) or `pp_bearing_rows`.

All record strings are at most 256 Unicode scalars (`battle_id`, move `id`/`name`/`target`, ...); only `raw_request` may reach 65536. Over-length values reject in both builders and in the canonicalizer.

`id` = `rkn-` + sha256 of `request-knowledge/v1\n` + canonical JSON of the record without `id` (ASCII keys sorted, minimal integers, UTF-8 strings, no normalization).

## Presence table (from `classifyPipelineRequestState`)

| observation | raw text | presence |
|---|---|---|
| terminated view | null | `terminal` |
| not terminated, `request` null | null | `requestless` |
| `wait` | `wait:true` | `waiting` |
| roster member `reviving` | `forceSwitch:[true]` | `revival_selection` |
| `force_switch` | `forceSwitch:[true]` | `forced_switch` |
| otherwise with legal actions | `active` | `actionable` |
| `no_legal_actions` (not waiting, unavailable or no indices) | any | rejected `no-legal-actions` |
| `team_preview` | `teamPreview` | rejected `team-preview` |

A terminal observation has no request even when the owner held earlier ones; a terminal record is never built from them. This is not the pipeline `boundary_kind` (a joint property) but the K20 per-perspective side value.

## Tri-state flags and derivation

`trapped`, `maybe_trapped`: `true` iff the raw key is `true`. `false` is permitted only as a rule-derived value from the pinned singles source (`pokemon.js getMoveRequestData` 740-749): the engine emits them only while a switch-in (non-active, non-fainted roster member) exists, so absent with `switch_in_available` is `false`. Absent without a switch-in is `null` (unknown, `not_emitted`), including a locked row with an empty bench. When `trapped` is true the engine does not report `maybeTrapped`, so `maybe_trapped` is `false` with `superseded_by_trapped`. The source emits `maybeDisabled` only when it is true (singles last active, independent of the bench): absent means false in singles (`omitted_singles_rule`), so it is never null. `derivation` names the rule per field: `lock` in {`bare_single_row`, `pp_bearing_rows`}; `trapped` in {`raw_true`, `omitted_with_switch_in`, `omitted_without_switch_in`}; `maybe_trapped` adds `superseded_by_trapped`; `maybe_disabled` in {`raw_true`, `omitted_singles_rule`}. Both `true` together rejects. **Vocabulary (lead decision, PERSPECTIVE_KNOWLEDGE.md not amended):** the derived-false values (`trapped`/`maybe_trapped` false from omission, `maybe_disabled` false, `maybe_trapped` false under `superseded_by_trapped`) are sidecar-local, rule-derived values under the pinned singles source rule. They are NOT PERSPECTIVE `known_absent` and not a default. The S01c K-fact adapter must emit them as `unknown` unless a rule-evidence form is added by a reviewed contract revision; only `raw_true` flags and raw-present move values are source facts.

## Roster/broadcast rule (for lead review; PERSPECTIVE_KNOWLEDGE.md unedited)

- Request subject (`:roster:R:move:M:incarnation:N` for `pp`, `max_pp`, `disabled`, `maybe_disabled`): the move row `slot` of the fresh addressed active inventory (request expansion is exactly that inventory). `maybe_disabled` is per active in the engine; the adapter broadcasts the single boolean to every row of the active inventory (all rows share one value, identical derivation).
- Roster subject (`trapped`, `maybe_trapped`, `lock`): the roster identity of the raw `side.pokemon` entry with `active:true` (1-based position in that list) for the owner; bench members receive no fact from this record (not emitted: unknown for requests, as the contract already states).
- Side subject (`boundary_kind`, `request_presence`): `presence` and `request_present`.
- `null` move/flag values map to `unknown` with reason `not_emitted`; raw-present move values and `raw_true` flags map to known with the type in `property-types.json` (`lock` text, others boolean/integer/text). Derived-false flags map to `unknown` (see Vocabulary above). `rqid`: the pinned stream emits none; the positive path is covered by a hand-audited literal (rqid 7 in text, observation request and record).

## Python validator `validate_request_knowledge(record, observation, *, delivery_registry=None)`

Raises `RequestKnowledgeError.code`; returns `{record_id, presence, delivery_authority}` with `delivery_authority` `structure_only` without a registry and `registry_bound` with one. Order: (1) strict wire (`wire-keys`, `wire-type`, `wire-size`); observation identity (`observation-identity`, legacy `verify_observation`); (6) stale join keys (`stale`, `observation-mismatch`); (5) owner agreement among record, observation, `request.player`, raw `side.id`, roster idents (`wrong-owner`); (2) independent re-derivation of every field from `raw_request` with its own grammar (`raw-json`, `raw-grammar`, `doubles`, `team-preview`, `presence-mismatch`, `false-certainty`); (3) the observation carries `value ?? legacy default` per move, `trapped`, `can_switch`, roster and rqid (`observation-mismatch`, `no-legal-actions`); (4) a numbered move action must be an enabled row with PP, or the request-supplied Struggle row (`legality-mismatch`); registry: the text must be the latest delivery to this owner at `event_cursor` (`registry-delivery`, `registry-type`); finally `id`. A jointly resealed record, raw text and observation passes as `structure_only`; only an independently held addressed-delivery registry (Prompt 12 `SourceRegistry`, delivery cursor = observation cursor, a lead-confirmed seam assumption) detects it.

## Limits

Test-owned witness only (no authenticated delivery provider); singles gen9 only; bench PP, `canTerastallize`, soft-lock reasons, retained last-known PP and hidden Pressure are not modelled; locked rows with an empty bench keep `trapped` null although `getMoves` sets it internally (conservative).
