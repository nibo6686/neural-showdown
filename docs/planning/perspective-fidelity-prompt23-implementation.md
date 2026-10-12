# Prompt23 — S02a: retain pre-effect owner originals through real creation

Lead authorization: one local implementation candidate only. Prompt22 is accepted
as source characterization/design, not runtime authority or completeness.
Implement order1 of its runtime boundaries with the decisions below. Return for
lead review before order2 or any dependent work.

## Context and skills

Workspace: C:/Users/cloud/Downloads/neural/final. Read the project Codex config,
docs/refactor/AGENT_PROTOCOL.md, docs/codex_review_state.md, the current perspective
implementation plan, Prompt22 lead review/design/runtime boundaries, accepted
PERSPECTIVE_KNOWLEDGE and source-seam APIs. Apply the globally installed
implement-plan skill to this boundary and review-plan-tests to the validation
plan. Use subagents for read-only source/oracle and independent candidate review;
one writer owns shared env/session files. Follow project Pokemon naming.

## Authorized writes

- New sim-core/src/original_owner_provider.ts.
- Narrow creation/cleanup wiring in sim-core/src/env_manager.ts.
- Mandatory private creation-origin and holder wiring in
  sim-core/src/pipeline_integration.ts.
- New sim-core/tests/original_owner_provider.test.ts. A narrowly scoped new
  integration test file is permitted if necessary to keep tests readable.
- New docs/planning/perspective-fidelity-prompt23-* candidate evidence/API docs.

Existing tests, frozen contracts, source registry, replay importer/history,
Python production, configuration, historical evidence, coverage lists and
attestations are protected. Build outputs may change only as consequences of
owned TypeScript files; inventory those separately. Do not alter node_modules.
Return a precise blocker if the boundary requires additional production writes.
Workers do not update aggregate plan/status documents.

## Implementation decisions

1. The actual PipelineIntegrationSession creation path owns a private,
   process-local creation occurrence and its two owner holdings. Public
   battle_id/format/engine/rule labels describe that occurrence but cannot mint
   its authority. Matching strings, env_id, seeds, plain objects, copied tokens,
   imported JSON and registry witnesses cannot impersonate it. Independently
   created sessions with identical public labels remain different occurrences.
   Use internal reference identity/held provenance; introduce no signing system.
   Any observation/testing access must remain privileged and owner-addressed,
   separate from existing result/wire APIs.

2. At each actual Teams.generate call in resetWithOptions, retain a detached
   deep copy before Teams.pack. Preserve complete raw arrays, original roster
   and move order, all own-property presence including undefined, nested fields,
   empty values and zeros. Recursively freeze retained data. JSON round-tripping
   and Teams.unpack are forbidden as original/presence reconstruction.
   Pack a separate mutable copy. Bind the holder to the exact owner-specific
   packed string used in the actual player payload, not a later repacking.
   Both addressed holdings must be privately staged before any start/player
   payload write. Pre-write inspection may observe staged evidence but cannot
   obtain an authorizing handle.

3. Retain role only as privileged generator metadata: source proves it is not
   submitted by the pinned packer. It grants no original fact or wire eligibility.
   Preserve unknown extra raw fields too, explicitly unsupported for later fact
   adoption; never silently discard them. Record present/undefined/omitted
   distinctions for the reviewed finite submitted-field inventory independently
   of packing defaults. This boundary performs no wire normalization, calculated
   stat derivation or default inference. Do not invent nature, gender, HP, PP,
   effective ability/form or any missing original value.

4. Issuance is one-shot for the actual creation occurrence. Prepare two-owner
   evidence atomically; failed generation, packing, submission, settling or
   initial boundary construction leaves no usable partial holder or escaped
   issuance. Activate privileged original authority only after successful
   initial settling and boundary construction, immediately before session
   creation returns. All staged handles are invalidated on failure.
   Reset/reuse cannot rebind a prior holder to new teams, owner or
   occurrence. Standalone environments retain existing behavior but have no
   session-original authority. A bare serialized restore cannot mint originals.

5. Session-held originals persist unchanged when a successful transition
   replaces/closes the previous environment, and after candidate rejection.
   Restored candidate environments gain no current identity/request authority
   merely because the session retains originals. Snapshot serialization and
   arbitrary snapshot/belief forks do not carry or recreate the capability.
   No new fork API or native birth/restore association is authorized.
   Session close invalidates privileged access before awaiting cleanup and
   releases holdings, including
   cleanup failure paths. Preserve existing cleanup behavior and prevent stale
   handles from authorizing subsequent sessions. Retaining immutable diagnostic
   copies is not continuing authority.

6. Keep SourceRegistryBuilder and original_provider:not_adopted unchanged.
   Existing StepResult, snapshots, boundaries, bundles, v1/v2 bytes/IDs,
   diagnostics and faithful_complete_episode meaning stay unchanged. Internal
   evidence sequence0/cursor0 marks creation provenance, not a request delivery,
   causal carrier, complete field inventory or new public schema.
   Never expose an opponent holding, seed, both-owner manager or audit capability
   through a perspective view.

## Required red/green and integration evidence

- First preserve a failing requirement demonstrating the current real session
  has no original holder. Then prove the production session→env→generate→copy→
  pack→submission route invokes the provider and retains both six-member owner
  teams before payload write. Unit/helper success alone is insufficient.
- Independently compare retained raw fields/order and actual payload strings.
  Prove detach/freeze by attempted mutations of generated and packing copies,
  arrays, moves and EV/IV objects. Literal controls cover absent versus own
  undefined, nested undefined, omitted nature/happiness/ball, empty item/gender,
  EV0/IV0, metadata and distinct raw inputs yielding equal packed bytes.
- Through actual provider wiring, exercise both-owner initial Trace, Imposter,
  Schooling and Crowned controls: originals stay fixed while native first
  requests/base fields change. Test-only controlled generator inputs are allowed
  for these oracles; label them synthetic. Also retain a genuine pinned native
  six-member Random Battle generation witness. Do not add production team injection.
- Reject forged/transported/copy authority, foreign owner/occurrence (including
  identical public labels), swapped packed association, duplicate issuance and
  reset reuse. Reject missing either owner atomically.
- Exercise successful real candidate replacement, rejected candidate, bare
  restore, failed creation at relevant stages, close and cleanup failure.
  Original authority stays private and unchanged until its owning session ends.
  Existing bytes/IDs/snapshots must compare equal for deterministic paired runs.
- Build and run new tests plus affected env/session and cleanup regressions,
  source seam21, restoration15, history6, adapter8, loader8, characterization5.
  Run tests with PYTHONUTF8/PYTHONIOENCODING and historical report variables unset.
  Run requirement mode separately: the existing two Python/one TS broader
  failures remain expected red, with exact evidence. Do not weaken them.

Use D:/Anaconda/envs/neuralgpu/python.exe, absolute trainer/src PYTHONPATH and
direct node node_modules/typescript/bin/tsc -p tsconfig.json from sim-core.
Run Node test files separately when shared globals could interfere.

## Return and stop

Return a candidate-relative local diff; report under1000 words; exact commands,
counts/exits and independent oracle witnesses; API/lifetime/privacy contract;
before/after protected hashes and separately inventoried compiler outputs;
independent review with resolved findings and limitations. Preserve all earlier
evidence byte-for-byte. Record expected provenance drift without self-attestation.

No request delivery ledger, crosswalk, carrier binding, registry/source adoption,
Python authority bridge, K adapter, publication or consumer migration. No installs,
fetches, servers, datasets/training, staging/commit/push/PR/merge or attestation
change. Stop for lead review; do not start Prompt24.
