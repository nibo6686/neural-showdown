# Prompt48 candidate — authenticated original-owner starting projection

Ready for lead review in `/private/tmp/neural-showdown-native11-prompt38`. No promotion or downstream adoption is claimed. [Candidate diff](perspective-fidelity-prompt48-candidate.diff), [commands/results](perspective-fidelity-prompt48-commands.json), [preservation and changed-input hashes](perspective-fidelity-prompt48-hashes.json).

## Fixed private API and authority

`PipelineIntegrationSession.create({…, knowledge_recipients: {p1: recipient1, p2: recipient2}})` opts in with two distinct recipient object identities. `getOwnerKnowledgeHandle(recipient)` and `readOwnerKnowledge(handle, recipient)` require the exact registered recipient and current issuer-held handle. The only returned value is frozen `{projection,binding}`. Copied handles, owner strings, foreign issuers, wrong recipients and stale handles cannot retrieve it. Recipient objects remain caller-owned and are not frozen or mutated.

A single dedicated original-creation receiver registers before generation. Enrollment authenticates the exact controller-held environment, occurrence, both owner evidence references, revision and creation boundary. It does not consume B1/B2 actor receivers or infer authority from hashes, public holdings or equal values. Private source/starting/fact references survive held restoration and legal reorder. Boundary/current cutoff changes do not reconstruct originals from mutable sets.

The target-only interpreter verifies required presence and finite submitted species, ability, item and ordered moves against the checked installed public Dex, while preserving literal originals. Explicit empty item alone yields item `known_absent`; missing fields block. Recognized `role` and optional valid `speciesId` are inert generator metadata, never identity authority or knowledge facts. Arbitrary extra metadata blocks. Raw values and presence remain in independently retained evidence. No defaults fill originals.

The fixed native-owner projection contract has policy `native-owner-original/v1`, provider `native-owner-original-provider/v1`, engine `pokemon-showdown@0.11.11`, and profile ID `sha256:e81b9dde6a35b6e52bd3f782ea731179892c24c78c8d919aac07b4c7af396e45`. It permits only the finite starting facts, blocking unknown current facts, `result: incomplete`, empty starting crosswalk and `request: null`, paired with `request_adaptation: not_adopted`. Existing action/request APIs retain their meaning. Structure validation accepts no trusted context/source: a coherently rehashed false original can be structurally valid but cannot become a consumer handle or enrolled source.

## Transaction and compatibility

Initial and successor projections prepare detached; all fallible checks occur before the existing assignment-only installation barrier. Failed creation revokes before awaited cleanup. Failed successor preparation discards candidate access while retaining committed event, delivery, B2, session and knowledge handles/pairs. Successful advancement stales old handles, retains immutable old data and issues new owner handles. Close denies all subsequent access.

Three existing source modules change: original-owner receiver, target projection checker and session opt-in/barrier wiring. New controller/test and three target-only assets complete the eight-file candidate. The historical `perspective_knowledge_source.ts` is byte-identical to its frozen baseline; interpretation was moved into the private target controller following review. Historical contract, identity, schema, B1/B2 and source-origin algorithms remain unchanged.

## Exact executed evidence

All commands ran sequentially using Node24.21.0, explicit accepted Python runner and 180-second process-group deadlines; encoding/report overrides were unset. Final TypeScript build exited0. Four anchored exact cases each executed one test and passed:

- [Generated creation/restore/isolation](perspective-fidelity-prompt48-P48-generated-authentic-consumer-restore-and-isolation.log): actual both-owner source→builder→consumer, two held reorders, identical starting/fact references, stale/foreign/recipient rejection and ordinary-output privacy.
- [Constructed initial effects](perspective-fidelity-prompt48-P48-constructed-initial-effects-and-empty-original-item.log): actual Trace and form/move mutation sessions retain literal originals and explicit empty-item absence. These are constructed mechanics, not certified generated reachability.
- [Source attacks](perspective-fidelity-prompt48-P48-source-attacks-and-projection-nonauthority.log): actual missing/duplicate/foreign/copied/wrong-owner enrollment and malformed/unsupported field rejection; six coherent structural negatives. Unowned-runtime/recipient constructor checks are lower-level controls, separately labeled.
- [Barrier rollback/retry](perspective-fidelity-prompt48-P48-final-barrier-revocation-rollback-and-fresh-retry.log): actual creation and successor faults after preparation, revocation before cleanup, unchanged committed handles, valid fresh retry and close denial.

[Literal parity](perspective-fidelity-prompt48-literal-byte-parity-frozen-baseline.log) compares frozen pre-change modules and candidate in fresh processes: creation plus two held switches produces exactly equal boundary/bundle/snapshot/step JSON, 429,949 bytes, SHA256 `9254db1798b54684e524fd5a36ed88f9d850f7a72272185b85db45bdba79797a`. Only presentation clock is fixed; emitted requests are not normalized.

Initial compilation failed after an editing-script error; the affected historical module was restored before execution. A genuine creation initially rejected unclassified `speciesId`; its [failed log](perspective-fidelity-prompt48-failed-unclassified-speciesId.log) is preserved. The finite metadata rule and lifecycle corrections received focused rebuilds/reruns; failures are not counted as passes.

## Independent disposition and remaining limits

Slowking’s bounded read-only review: **ACCEPT**, no remaining material authority, privacy, contract or lifecycle finding. Review performed no execution. Findings on early revocation, historical module isolation and Dex existence checks were corrected before final validation.

Seven frozen original inputs, five historical contract pins and six accepted candidate dependency pins match. The hash inventory lists changed/new inputs and five affected ignored emitted files; it does not claim a whole-tree rehash. Existing migration/dependency preservation evidence is reused.

B3 appearance linkage, current/request adapters, full catalog/audit, Python/publication adoption, replay owner backfill, positive fidelity and default promotion remain unsupported/later. No tests or task processes remain pending. Stop for lead acceptance.
