# Prompt55 lead decision — experimental consumer approved; candidate recovery required

**Date:** 2026-10-14. **Design verdict:** approve the opt-in owner-addressed local TS ordering consumer and explicit incomplete-input policy. Implementation is blocked until the accepted candidate is recovered and hash-verified.

The lead read the corrected design and independent-review disposition and inspected the unchanged episode caller in the original checkout. The retained candidate path `/private/tmp/neural-showdown-native11-prompt38` is absent. Its cause/location is unknown; the owner has no alternate location. No current candidate-source hash verification or runtime validation is claimed. Historical evidence remains recorded; it cannot substitute for locating exact execution inputs.

## API/policy decisions

- Approve separate per-owner synchronous `owned_action_order` registrations, versioned policy identity and explicit `accept_incomplete:true`. Reject coexistence with legacy action_order. Default callers/output behavior stay unchanged; this is experimental local ordering, not model/training/live readiness.
- Approve the session-issued opaque order/frame API and both-owner batch recheck immediately before submission. Exact private ledger/receipt membership supplies authority; request clones are compared only for freshness/canonical-action corroboration. No clone equality, rqid, text or public metadata mints authority.
- Keep projection/binding paired and inputs immutable, with explicit incomplete status. First scope follows the design's supported ordinary_pp, forced and Revival descriptors. Unsupported source/descriptor stops selection without fallback; unknown facts within the accepted incomplete slice remain explicit. Waiting/terminal owners get no callback. Canonical action APIs remain the sole action authority.
- Reentrant selection/transition, asynchronous callbacks, malformed permutations, stale/copied/foreign orders and private error payloads require the stated guards. Preserve existing bounded rejection retries/accounting; no partial-choice/recoverable request-update contract.
- Continuation requires the original recipient registrations, not serialized labels or replacement identities. In-process trusted callbacks are not a shared-memory sandbox.

## Immediate next task

[Prompt56](perspective-fidelity-prompt56-first-prompt.md) recovers exact accepted source/dependency inputs in durable local storage, without new feature behavior or replaying prior validation. Preserve the 0.11.10 original checkout. Restore a legacy-path alias only for compatibility with accepted scripts; the real candidate must no longer reside solely in temporary storage.

After recovery review, implement this already approved design as a separate boundary. No policy implementation, promotion, publication or model use follows from recovery itself. Full knowledge/migration gates remain open.
