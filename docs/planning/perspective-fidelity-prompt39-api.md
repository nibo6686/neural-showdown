# Prompt39 candidate delivery preparation lifetime

Only candidate `request_delivery_ledger.ts` and `pipeline_integration.ts` change. Original checkout production and dependencies remain unchanged.

`RequestDeliveryLedger.discard(prepared: object)` deletes only that exact pending WeakMap token. It is synchronous, idempotent and safe during cleanup. It grants no authority, exposes no state, and does not change committed parent, histories, raw requests, handles or wire schemas.

Session transition execution retains its delivery-preparation token outside the try block. On rejection, it discards that token before discarding B2 candidate association and before awaiting candidate close. On successful synchronous commit the token has already been consumed; no extra commit or sequence is created. Existing parent/current references and native object holdings remain valid following rejection. Candidate trace access revokes at close, while retry uses a new native occurrence.

Scope of rollback is rejection before the synchronous session/delivery/B2 swap. This supplies no rollback of writes in the rejected candidate world and no general transaction framework. Preflight rejection leaves the source world unchanged; native choice rejection and post-preparation failure occur in a disposable candidate, which is retired. Original source world/holdings are preserved rather than reconstructed.

Timing evidence is test-only: actual native push calls, actual routed owner tracker chunks, literal FIFO pairing by held objects/positions, and independently derived source/routed public-prefix indices. Trace counts never become public cursors. No production observer, B3 actor/event crosswalk or request-string authority is added.
