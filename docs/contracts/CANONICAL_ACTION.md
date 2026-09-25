# CanonicalAction Contract

Status: ACTION-001 accepted contract; additive opt-in ingress, legacy paths unchanged.

## Scope

`CanonicalAction` v1 is a request-bound representation of the current single-active action space. It is derived from the TypeScript `LegalAction` set and is mirrored by Python. It does not replace simulator submission, search, replay, live-control, or checkpoint behavior.

The shared corpus is [`tests/fixtures/canonical_action_v1.json`](../../tests/fixtures/canonical_action_v1.json). Its serialized strings are normative parity fixtures for TypeScript and Python.

## Shape and mapping

Every record has the following fixed field order:

```text
schema_version, action_id, source, player, rqid, kind, index,
move_slot, switch_slot, target, choice
```

`schema_version` is `canonical-action/v1`. `source` is `request_legal_action` and records that the action came from the current request's legal-action set. `player` and `rqid` bind the action to the current choice request (`rqid` may be null). `target` is reserved and must be null in v1.

The current mapping is:

| kind | index | slot field | choice |
| --- | --- | --- | --- |
| move | `move_slot - 1` | `move_slot` 1..4 | `move N` |
| move_tera | `move_slot + 3` | `move_slot` 1..4 | `move N terastallize` |
| switch | request-provided index 8..12 | `switch_slot` 1..6 | `switch N` |
| default | 0 | neither | `default` |

Switch `index` is the legal-action index; it is not a team slot. The team slot is carried separately in `switch_slot`.

An action is valid only when its index, kind, slot fields, choice text, player, rqid, source, and target all match the current request's legal action. Forced-switch requests accept switch actions, or the existing synthesized `default` fallback when no switch is available. A missing, stale, malformed, or unavailable action fails closed.

`action_id` is `act-` plus the SHA-256 digest of deterministic JSON for all fields except `action_id`, using the fixed order above. Serialization is deterministic JSON with no added or omitted fields. Python and TypeScript must produce byte-identical fixture strings.

## Explicit v1 boundaries

- Targeted move grammar is not yet represented. Non-null targets are rejected; no target syntax is invented here.
- `wait` and `teamPreview` do not gain a new canonical action kind and expose no canonical action. The existing legacy `default` fallback is represented only when the current legal action is the synthesized `default` action, including forced-switch exhaustion.
- Multi-active commands, pass/skip, and other Showdown command forms remain outside this slice until their request semantics and target grammar are specified.

## Rollback and adoption

The existing `step_canonical` ingress is additive and opt-in: it validates a caller-supplied action against the pending request, converts it to the canonical raw choice, and then uses the existing raw choice forwarding and retry path. The legacy `step` path remains unchanged and authoritative by default; no controller, search, replay, live-control, or checkpoint path is switched over. The codec's derivation and adoption remain shadow-only for those existing paths. The additive ingress can be rolled back without changing simulator behavior. Any future default-path replacement must first pass request-bound invalid-choice tests, Python/TypeScript parity, focused suites, and a separate ACTION-001 review.

## Bounded revival selection — scoped acceptance, 2026-09-25

`canonical-revival/v1` is additive and only supports `kind:revive`. It uses the
same core fields and hash ordering as CanonicalAction plus a required
`request_fingerprint`; its distinct schema, kind and fingerprint enter the action ID. `switch_slot` is the one-based current request-party
position; wire choice is `switch N`, `move_slot` and `target` are null. Eligible
non-active fainted targets in request order occupy indices8..12; no new action
slots or default action are invented. The current force-switch legal mask, kind,
choice, slot, player and rqid must match. Ordinary move/switch/default actions
retain `canonical-action/v1` unchanged. TypeScript and Python mirror this dispatch.
`request_fingerprint` is SHA-256 of compact UTF-8 JSON for the addressed roster,
in request order, each entry `[slot, ident, details, condition, active, reviving===true]`.
It is required only on revival actions and revalidated against the current request
in both languages. Changed roster identity/condition rejects even when rqid is null
and slot/choice recur. An exactly identical later request is not a distinct epoch;
snapshot/observation lineage remains the transition freshness authority.
