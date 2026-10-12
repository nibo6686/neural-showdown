# Prompt25 private committed session delivery API

`PipelineIntegrationSession.getRequestDeliveryHandle(owner)` returns an opaque process-local owner handle. `readRequestDeliveryHistory(handle, owner, expected?)` returns immutable addressed history; optional `expected` must be the exact held boundary row, not a copied binding. Neither history JSON, tokens in diagnostics, a matching public label nor another owner's handle grants access. Creation occurrence remains distinct with identical public labels and seeds. Existing wire APIs gain no ledger fields.

History shape:

```
{ boundaries: readonly RequestDeliveryBoundary[],
  deliveries: readonly CommittedRequestDelivery[] }
```

Each boundary row has `owner`, `session_occurrence`, `observation_id`, `branch_id`, `step_index`, immutable exact `prefix`, `boundary_cursor` (prefix length), `parent: {observation_id, branch_id, step_index} | null`, full accepted-candidate `trace`, `selected: RequestEmissionReceipt | null`, and `current: CommittedRequestDelivery | null`. A delivery has `owner`, `session_occurrence`, contiguous per-owner `sequence` starting0, opaque `delivery_reference` and literal original `source` receipt. Each newly selected native emission at an accepted boundary adds one delivery; equal text still means separate occurrences/references. A selected supported reemission retains the held parent delivery object and sequence. Its boundary `selected` remains the literal reemission, while `current.source` stays the original native evidence.

## Selection and provenance

The pinned native producer sends one owner request per sideupdate chunk; owner streams append/consume FIFO. For external session owners, the real handler replaces current request on every ordinary request, clears the waiting slot first, keeps freshly received wait requests, auto-submits default for team preview and suppresses the first already-consumed restored request. Terminal reporting returns null. Choice-error legal filtering does not rewrite request.raw. The last positional owner receipt is the sole eligible settled source when a reported request exists. Its parsed literal JSON must deeply equal actual settled StepResult.requests[owner].raw. No backward search, rqid match, projected-observation raw inference or reconstructed exact-byte oracle is used. Team-preview reported requests are unsupported rather than certified.

Initial/candidate traces are obtained only through direct privileged reads of the actual held environments; the controller has no trace/certificate input. `RequestDeliveryLedger` is internal trusted session machinery, not a public certification factory. Its prepare methods accept trusted controller boundaries/results, not independently authenticated arbitrary caller objects. Full accepted trace rows remain private history. Unselected/intermediate rows have no causal prefix/observation binding and remain unsupported for completeness. A boundary cursor is settled-prefix length, not a producer emission-time cursor. Trusted native FIFO remains necessary: identical bytes cannot detect arbitrary same-byte injection/substitution/reordering within a monkeypatched held stream.

## Restore, commit and lifetime

Capture actual resetFromSerialized result and receipt references before actions. Opaque restoration proof is tied to this held session parent and candidate environment, with a preserved trace prefix. Every reported restoration request must agree with held parent raw and have a parent delivery. No snapshot, JSON or labels recreate missing references. Snapshot fingerprint/root-seed/request checks retain their existing placement and reject before commitment.

The existing appropriate episode bundle validator runs on each actor bundle before ledger preparation. Preparation constructs both owner histories and raw comparisons without mutation. An opaque token can commit only to its originating ledger and unchanged held parent. Commit and ordinary session state assignment execute synchronously at the existing successful swap before retiring the old environment. Any earlier failure discards candidate evidence; parent histories/sequences remain unchanged. Post-commit retirement failures retain the committed ledger and the existing retired-environment close retry mechanism.

The accepted legacy unstarted-restore exception is explicitly signaled by existing OriginalOwnerCreation.activate returning false. That path retains old behavior, revokes the ledger, and supplies no delivery handle even after later transitions. A genuine native creation cannot bypass a required ledger check. Bare restore without held original delivery continuity is rejected for ledger adoption.

Requestless/terminal outcomes have selected/current null and do not advance sequences; earlier deliveries and trace rows remain history. Wait delivery grants no action authority. Close revokes ledger access before awaiting cleanup; returned frozen diagnostics remain data. Initial/binding failures revoke all access before returning an error. Existing session close behavior is preserved, including its closed-state behavior after cleanup errors.

Session APIs use existing pipeline/v1/closed errors on closed access. Internal ledger errors use request-delivery/v1/ with revoked, invalid-owner, settled-request-mismatch, suppressed-request, foreign-parent, unexpected-native-restore, missing-parent-delivery, missing-restore-continuity, observation-join, prefix-parent-join, foreign-trace-occurrence, reused-occurrence, foreign-or-stale-preparation, foreign-or-forged-handle and foreign-boundary-binding reasons. Preparation failure does not revoke committed parent history.

No registry, current request/action authority, roster crosswalk, Python authority, knowledge facts, publication, profile or capture-flag changes are adopted. Original creation sequence0, trace-local counters and committed delivery sequence0 are separate namespaces. No fork/import capability or retroactive causal labeling is added.
