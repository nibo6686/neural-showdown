# Prompt24 — S01c-2a: exact native request emission and receipt trace

One local candidate, then lead review. This implements the environment portion
of the delivery prerequisite. Session commit sequences and causal boundary joins
are a separate following boundary, not implicit authorization in this prompt.

Workspace C:/Users/cloud/Downloads/neural/final. Read project configuration,
agent protocol/review state, current perspective plan, Prompt23 lead review/API,
Prompt22 design/runtime boundaries, and Prompt15/16 request decisions. Use global
implement-plan and review-plan-tests skills. Use read-only source/oracle and
independent review subagents with project Pokemon names; one writer owns env.

## Owned scope

- New sim-core/src/request_emission_trace.ts and new corresponding test.
- Narrow sim-core/src/env_manager.ts producer/routed-receipt/cleanup wiring.
- New docs/planning/perspective-fidelity-prompt24-* evidence and API documents.

No pipeline session, provider, registry, extractor, replay, Python, contract,
configuration, attestation or old test edits. Inventory consequent compiler
changes separately. Return a precise blocker if another production file or
engine hook is necessary. Do not modify node_modules or aggregate status files.

## Implementation and proof

1. Capture private owner-addressed native request emissions before player-stream
   fanout and before parsing/trimming. Retain exact request record and JSON text,
   producer owner, distinct stream/creation-occurrence identity, and ordered
   environment-local emission identity. Do not stringify parsed request.raw
   or hash reconstructed JSON as an exact-byte oracle. Equal-text/rqid repeated
   emissions remain distinct.

2. Establish provenance at the actual producer call, not consumer arrival time.
   Distinguish native_emission from explicit restore_reemit. Native emission is
   not a claim of current freshness or action authority. A per-instance
   BattleStream.pushMessage observation bridge is a candidate seam: inspect the
   pinned send/sideupdate route and actual restore callback path, and prove it
   works through production. No global/prototype patching in production.
   Label restore emissions at their synchronous producer invocation. Do not keep
   an async/global restoration flag that can label subsequent native requests.
   Unknown origins remain unsupported; never default them to native authority.

3. At ManagedPlayer's real routed receipt, retain exact pre-parse text and join
   it to the correct pending producer emission for that owner/occurrence.
   Preserve repeated equal-text rows and ordering. The join relies on the held
   trusted owner stream occurrence and its producer FIFO, not text alone.
   Cross-owner, foreign-occurrence, missing/duplicate emission or mismatched
   receipt provenance/order cannot become supported trace evidence. Distinct-text
   order violations must reject. Same-byte substitution/reordering inside an
   arbitrarily monkeypatched stream is not distinguishable from bytes; do not
   claim such a detector. Document the native trusted FIFO assumption explicitly.
   Define trace validity/errors atomically. No arbitrary in-process injection
   security boundary or transported-stream authority is adopted.
   Do not change existing tracker/request normalization or legal-choice logic.

4. Keep all trace state private, process-local and owner-addressed. Diagnostic
   copies/JSON cannot grant a producer handle. Privileged inspection is allowed
   for tests and later reviewed session integration; existing StepResult, views,
   snapshots, diagnostics, boundaries, bundles and serialized outputs carry no
   trace or new secret. One owner's view grants no other-owner/manager access.
   Cleanup invalidates access before awaiting stream disposal. New reset/stream
   occurrences cannot reuse prior trace authority even if counters/text match.

5. Restored request records are reemissions, with no invented original delivery
   reference. Bare snapshots and terminal request-history restoration cannot
   mint a native fresh emission. Later native requests after restore are
   separately recorded as native_emission. Wait/force/revival are traced when
   genuinely emitted but confer no action eligibility here. Requestless/terminal
   boundaries with no emission do not resurrect retained requests.

6. Add no session-owned sequence, committed prefix, observation-ID join,
   publication, current request authority, roster association or K facts.
   Requests can precede public update fanout: record that limitation rather than
   treating arrival position as a public cursor. Local IDs are deliberately
   insufficient across candidates; following S01c-2b must select, join and commit
   supported traces before environment retirement and discard rejected joins.
   Original-provider lifetime and faithful_complete_episode meaning are unchanged.

## Validation gates

- Preserve a baseline red test for absent production emission/receipt retention;
  then prove actual session-created env→native sideupdate→owner stream→
  ManagedPlayer trace wiring. Unit helpers or test-supplied labels are insufficient.
- Independently capture literal producer/routed strings, including Unicode,
  whitespace and field order. Compare exact strings without production helpers.
  Test both owners, repeated identical emissions and receipt order.
- Actual restore/reemit then continued native actions; force/wait/revival,
  rejected-choice resend, requestless/terminal and terminal-history restoration.
  Prove producer classification regardless of when asynchronous receipt runs.
- Forged labels/JSON/handles, wrong held owner/occurrence, distinct-text order
  violations, missing/duplicate producer identity, exact-text foreign provenance
  and local-counter collisions reject supported joins. Test equal-text native
  repetitions as separate FIFO occurrences; do not relabel an undetectable
  same-byte injected swap as a proven rejection. Prove reset/close/failed
  initialization and cleanup-failure isolation.
- Native changes must preserve deterministic v1/v2 wire/snapshot/bundle bytes
  and identities against the Prompt23 baseline. Repeat affected env/session,
  settling, restoration, original provider/source and cleanup regressions plus
  loader/characterization. Run broader requirement mode separately, preserving
  the existing two Python/one TS failures.

Use D:/Anaconda/envs/neuralgpu/python.exe, absolute trainer/src PYTHONPATH,
direct TypeScript compiler, separate Node files, and unset encoding/historical
report variables. Preserve all prior evidence and protected files. Return local
candidate diff, report under1000 words, commands/counts/exits, literal witnesses,
API/provenance/lifetime limits, hashes/compiler inventory and independent review.

No installs/fetches/servers, datasets/training, commits/staging/publication,
attestation change or dependent work. Stop for lead review before S01c-2b.
