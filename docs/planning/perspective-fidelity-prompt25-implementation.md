# Prompt25 — S01c-2b: private committed session delivery ledger

One local candidate, then lead review. Prompt24 establishes exact native
emission/receipt evidence; it establishes no causal/current authority. Implement
private session commitment without adopting knowledge facts, publication or the
source registry. Preserve the frozen wire and existing capture-flag meaning.

Workspace C:/Users/cloud/Downloads/neural/final. Read project config, agent
protocol/review state, current plan, Prompt24 lead review/API and Prompt22
delivery design. Use global implement-plan and review-plan-tests. Use independent
read-only source/oracle and candidate reviewers with project Pokemon names.
One writer owns session wiring.

## Owned writes

New sim-core/src/request_delivery_ledger.ts and corresponding new test;
narrow sim-core/src/pipeline_integration.ts initial/transition commitment,
private owner access and close wiring; new docs/planning/perspective-fidelity-
prompt25-* evidence/API documents. No env/trace/provider/registry/extractor,
replay/Python/contracts/configuration/old tests or attestations may change.
Inventory consequence-only compiler changes. Return a precise blocker if another
production seam is required. Workers do not update aggregate status.

## Decisions and implementation

1. Hold a private ledger for the actual session occurrence, distinguishable from
   every other session even with identical public labels/seeds. Take evidence
   only by direct privileged reads of the session's actual initial/candidate
   environments and held trace handles before their retirement. Copied rows,
   caller certificates, JSON and matching IDs cannot supply production provenance.
   New opaque owner access is privileged; existing wire/result/consumer APIs
   expose no manager, other-owner data or ledger fields.

2. Preserve complete accepted-candidate traces privately, including native
   emissions and restore reemissions, with distinct occurrence/local identities.
   They are not all deliveries bound to the final prefix. Select the emission
   that actually populated each settled boundary's reported owner request using
   native producer/FIFO order and real request handling. Independently compare
   parsed literal text to the actual settled StepResult.requests[owner].raw,
   while preserving exact text. The projected observation omits raw; it is not
   the raw-request oracle.
   Equality of JSON/rqid/cursor alone is insufficient. Prove selection through
   the real route, including repeated equal text and superseded/resend requests.
   Document the existing handler's selection/suppression rules and test them
   independently; do not scan backward for any earlier text that happens to match.
   Do not fabricate emission-time public cursors for intermediate trace rows.
   Keep unselected/intermediate rows unbound and explicitly unsupported for later
   completeness until their own causal proof exists.

3. Join the selected source to the exact committed owner observation:
   owner/session occurrence, observation ID, branch/step and parent reference,
   complete immutable owner protocol prefix and its length. Use the actual
   prefix carried by the validated observation; store enough exact evidence to
   reject an equal-length foreign prefix. Distinguish this settled boundary
   binding cursor from producer-local emission indices and unproved emission-time
   positions. Requests may precede public fanout. No hash/content match alone
   grants source legitimacy.

4. Assign session-owned contiguous per-owner committed delivery sequence0..N
   only to newly selected native deliveries in accepted boundaries. This namespace
   is separate from original creation sequence0 and trace-local indices.
   Equal-text new native deliveries receive distinct identities. A restored
   reemission may retain an existing parent's delivery reference only with held
   same-session parent history and supported restore/request continuity; never
   append it as fresh. Do not use snapshot/rqid/text alone to recreate a lost
   reference. If supported matching cannot be proved, return a blocker instead
   of substituting a later snapshot or guessing.

5. A freshly emitted wait request can have a delivery binding but grants no
   action authority. Requestless/terminal observations have no current binding;
   retain earlier evidence as history without resurrecting it. Bind nonacting
   owner rows as well as actor rows when supported. Sequence does not advance
   for unsupported/unselected/reemit rows. Bare/imported restore and legacy
   unstarted-restore compatibility remain unauthoritative, not newly certified.
   Do not silently skip a required real native boundary to claim a complete
   ledger. Original roster/current selectability/PP semantics remain deferred.

6. Prepare both-owner joins tentatively after settling and ordinary boundary/
   bundle validation. Existing transition code constructs bundles without
   invoking their validator there: explicitly invoke the existing appropriate
   bundle validator before ledger preparation/commit. Do not defer this check
   to downstream episode validation. Commit at the same successful state-change
   point, before old-environment disposal. Any earlier failure drops both owners'
   tentative trace/selection/sequence changes, leaving parent history unchanged.
   A post-commit retirement error retains committed lineage under existing close
   retry behavior. Capture candidate evidence before cleanup invalidates its
   trace. Later candidates cannot graft sibling/foreign occurrences even when
   counters and strings match.

7. Preserve held parent continuity through ordinary session candidate restores;
   no new fork/import API or serialized capability is authorized. Close revokes
   privileged ledger access before awaiting cleanup. Creation/binding failures
   leave no escaped supported ledger. Already returned immutable diagnostics
   remain data only. Registry request/source adoption and Python authority remain
   later boundaries; this ledger does not confer current action or K-fact authority.

## Required validation

- Preserve baseline red for missing actual session ledger, then prove initial
  creation and at least two consecutive real transitions. Local counters restart;
  committed owner sequences and exact prefix/observation joins remain coherent.
- Literal independent producer/receipt/boundary oracles for both owners.
  Repeated equal text, superseded requests, restore reemit before native emission,
  wait/force/revival/nonactor, requestless/terminal and retained history controls.
  Label synthetic fixtures/taps; retain a genuine native Random Battle witness.
- Fully coherent wrong-owner/session, equal-label foreign occurrence,
  same-length foreign prefix, wrong observation/parent/branch, stale/reused local
  index, copied/transported trace and missing original delivery controls reject.
  Match unrelated IDs first so hashing cannot mask semantic rejection.
- Real rejected candidate followed by a valid transition: both-owner history
  and sequences unchanged after rejection. Failure after one tentative owner,
  initialization failure, retirement/close cleanup failure, stale handles and
  accepted parent continuation. No hidden JSON repair or guessing fallback.
- Exact v1/v2 wire/snapshot/bundle bytes/IDs against pre-task capture; accepted
  trace/provider/env/session/settling/source/restoration/cleanup tests and replay
  loader/characterization. Repeat the three broader expected requirement failures.
  Existing supported legacy restore behavior remains intact without ledger authority.

Use D:/Anaconda/envs/neuralgpu/python.exe, absolute trainer/src PYTHONPATH, direct
TypeScript compiler and separate Node files. Unset encoding and historical report
variables. Return candidate-relative diff, report under1000 words, exact commands/
counts/exits, API/selection/causal/lifetime limits, literal witnesses, protected/
compiler hashes and independent review. Preserve all prior evidence byte-for-byte,
including the separate Prompt24 lead API clarification.

No source-registry adoption, identity crosswalk/carriers, Python bridge, K facts,
publication/consumer migration, installs/fetches/servers, datasets/training,
commits/staging/publication or attestation changes. Stop for lead review.
