# Prompt57 local decision-consumer candidate

## Scope and actual adoption

Implemented in the durable isolated candidate, not the original checkout. The real `pipeline_episode.ts` actionTuples/executeEpisode caller now dispatches experimental `owned_action_order` registrations `{recipient, callback}` for each owner. It requires a versioned policy_id and `accept_incomplete:true`, rejects legacy action_order coexistence, and requires the original recipient identities for continuation. Default callers remain unchanged.

Write set: two existing sources (`pipeline_episode.ts`, `pipeline_integration.ts`), new `owned_decision_input.ts`, and one new exact test. Knowledge profiles, canonical identities/actions, B1/B2, source writers, dependencies, wire/result schemas, Python/RPC and models are unchanged. [Diff](perspective-fidelity-prompt57-candidate.diff).

## Private API and authority

`session.withOwnedDecisionInput(recipient, callback)` supplies one owner's immutable observation, inseparable projection/binding pair, fresh canonical action context, legal indices and explicit incomplete status. It returns an opaque held order; `assertOwnedDecisionBatch(orders)` validates both acting owners immediately before transition submission, without an await. Original recipient, current knowledge handle/read, actual boundary/environment and committed delivery/selected receipt membership establish authority. Full request-context equality corroborates freshness only: getRequest returns clones. Equal bytes, rqid, labels, public metadata and copied values never mint orders.

Only ordinary_pp, forced-switch and Revival descriptors proceed. Waiting/terminal owners receive no callback; unsupported sources stop without fallback. Accepted unknown facts remain explicit. Originals, current health/item/ability identifiers and emitted option PP retain accepted meanings; no possession/incarnation, effectiveness/suppression/base ability, item history or broader fact adoption occurs. Canonical legal-action validation remains sole action authority; disabled PP rows grant no permission.

Callbacks must be synchronous and return a full unique legal-index permutation. Callback/inspection errors become fixed diagnostics, including cross-realm Promise rejection and prefixed private payloads. Reentrant attempts poison outer selection before candidate writes. Every failed issuance invalidates all pending authorization, preventing partial-choice recovery. Commit/rejection/close invalidate decision orders; close revokes before cleanup. Rejected candidates retain the committed parent and use fresh frames for existing bounded retries. Trusted in-process callbacks are not a shared-memory sandbox.

## Exact focused execution

[Commands/results](perspective-fidelity-prompt57-commands.json): pinned Node24.21.0 and explicit accepted simulator Python runner, absolute candidate trainer/src PYTHONPATH, encoding/report overrides unset. Anchored selectors, sequential workloads and real180-second process-group deadlines. All five runtime controls passed on first execution:

| Control | Result and proof class |
|---|---|
| Actual runner, both owners | PASS: canonical constructed Trace→Natural Cure current identifier changes actual legal ordering; immutable original Trace stays distinct; owner-only frozen incomplete inputs |
| Forced/Revival/wait/terminal | PASS: separate canonical sessions, seven bounded transitions maximum; acting-owner callbacks only, no waiting/terminal invocation |
| Authority/occurrence/source | PASS: copied/foreign/stale/wrong-owner denial; equal contexts and returned equal-byte requests retain distinct issuer/delivery/native occurrences; fresh-recipient continuation cannot recover registrations; authentic recharge descriptor blocks before callback |
| Failure/privacy/lifetime | PASS: first/second callback failures, invalid options before creation, native/foreign-realm Promises, invalid permutations, getter/iterator payloads, reentrancy and close; failed second issuance makes prior first order stale |
| Candidate rejection/retry | PASS: one-shot diagnostics-injected rejection inside the real candidate path; unchanged committed parent and fresh callback frames; one committed retry. This is injected failure proof, not a naturally arising simulator rejection or recovery contract |

[Default parity](perspective-fidelity-prompt57-default-parity.log): two fresh processes, frozen pre-Prompt57 modules versus candidate, one constructed native transition each. Literal episode output equals 32,425 bytes, SHA256 `636b2ab4f4ee484727887798e631804db990179b0f23f465c525c86ca8978dff`. Presentation clock fixed solely for timestamp parity. Private knowledge/capabilities are absent from serialized output; target fidelity remains false. No broad suites, long episodes, searches, models or prior matrices reran.

Build passed after two retained failures: initial directory EPERM plus source/test compile errors, then a test-only never[] narrowing error. A preceding incorrect launcher invocation did not execute a build; [details](perspective-fidelity-prompt57-launcher-failure.json) identify the missing exact stderr. No runtime case was rerun. Raw snapshot positive fixtures were removed before execution and replaced with authentic canonical creation; they never counted as source proof.

## Review, preservation and return

[Independent review](perspective-fidelity-prompt57-independent-review.md): ACCEPT after compile, partial authorization, Promise and diagnostic sanitization corrections; canonical fixtures statically checked. A subsequent equivalent zero-callback assertion type fix is recorded. Root took over sequential validation to reduce coordination overhead; one writer retained source/test ownership.

[Hashes/inventory](perspective-fidelity-prompt57-hashes.json) records scoped original/protected candidate comparisons, six unchanged dependency pins and generated outputs. Accepted Prompt54 archive/retention records remain untouched. The separate unreviewed archive is **NOT CREATED**: automatic approval review rejected both broad and four-file copying. A [pending-retention manifest](perspective-fidelity-prompt57-pending-retention.json) identifies the exact four-file overlay and intended destination. The durable candidate remains present; the accepted base archive is unchanged.

No pending runtime checks/processes; archive retention awaits explicit authorization. No commits, staging, publication, promotion, positive fidelity or training. Other adapters, completeness, natural rejection/recovery semantics and external/Python adoption remain separate. Stop for project-lead acceptance.

Automatic approval review rejected the proposed broad source/assets archive as an unapproved sensitive-data copy beyond Prompt57 scope. It also rejected the four-file overlay as a private source/test copy without sufficiently specific user authorization. No further archive copying was attempted.
