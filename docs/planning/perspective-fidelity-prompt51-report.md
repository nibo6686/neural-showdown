# Prompt51 — exact update marker compatibility checkpoint

**Scope:** retained `/private/tmp/neural-showdown-native11-prompt38`. The narrow native11 serializer/admission repair passes. **Committed held-overlay→fresh B2→delivery→health consumer proof remains blocked by the existing session contract**, not the root-key validator. Return for lead acceptance/scope decision.

[Candidate diff](perspective-fidelity-prompt51-candidate.diff) · [commands/results](perspective-fidelity-prompt51-commands.json) · [preservation/changed-input hashes](perspective-fidelity-prompt51-hashes.json).

## Correction and compatibility

Only production change: `env_manager.ts` private override validator receives the already-owned `NativeRuntimeProfile` from both serializer and restore-admission callsites, and checks its ownership. When engine is exactly0.11.11, the emitted overlay may have the extra own key `update` only with literal true. Every other root key/value remains exact. The marker is preserved, never removed or normalized.

Existing maybeTrapped→trapped and disabled:true/disabledSource checks are unchanged, including regenerated native trap/disabled corroboration and the nonzero real-edit requirement. Arbitrary extra keys, wrong side/health/move values, false/string/null markers, copied runtime descriptors and update-only no-ops reject. Historical10 retains strict root-key matching. No B2, ledger, health source, schema, identity or producer-authority change; no new public API.

A new CJS test file contains two exact cases. Private-validator test exposure exists only in an isolated in-memory test module; production exports are unchanged. Historical branch testing binds that isolated module to the original checkout’s genuinely owned0.11.10 runtime implementation. Its side fixture is explicitly model-only; it proves validator policy, not historical/target runtime coexistence or native source authority.

## Executed evidence

One build exited0. Sequential exact commands used Node24.21.0, accepted explicit Python runner, absolute candidate PYTHONPATH, unset encoding/report overrides and real180-second process-group deadlines.

- [Finite validator controls](perspective-fidelity-prompt51-exact-marker-validator.log): target literal marker plus genuine-edit requirements, trap/disabled truth guards, malformed/no-op/unsupported/value/owner controls and unchanged inputs; historical strict marker rejection and marker-free edit acceptance. Lower-level/model controls are labeled.
- [Actual native producer/serializer](perspective-fidelity-prompt51-actual-native-overlay-boundary.log): constructed Shadow Tag error path emits update:true with genuine trapped edit. The serialized override equals the exact emitted JSON byte-for-byte. Previously this payload was dropped; now affected snapshot serialization gains `__neural_active_request_overrides.requests.p1` containing that literal payload. No other delta is claimed for affected snapshots.
- The same actual case proves rejected candidate remains uncommitted: exact parent, native holding, health handle/pair and delivery history remain unchanged. A valid fresh retry succeeds with identical starting references and opposite-owner isolation.
- [Affected generated health restore case](perspective-fidelity-prompt51-P50-generated-health-writer-delivery-restore-and-privacy.log) and [decode/final-barrier rollback case](perspective-fidelity-prompt51-P50-scoped-decode-exceptions-and-final-barrier-rollback.log) pass. The latter proves candidate access revokes before cleanup, exact descriptor restoration, foreign-overlay rejection and fresh retry; it does **not** become a positive committed updated-overlay witness.
- [Unaffected literal parity](perspective-fidelity-prompt51-unaffected-literal-byte-parity.log): frozen Prompt50 env module versus candidate, creation and two held switches, exactly equal ordinary boundary/bundle/snapshot/step JSON;429,949 bytes, SHA256 `ef11f34680c895287c09f9b07496b26da294cf6ab0181c5875db8bcd6682fba0`. Presentation clock alone is fixed.

No broad tests or repeated diagnostic loop ran. Prompt50’s original failed overlay diagnostic is preserved and its accepted hash checked, not rewritten.

## Blocker and independent disposition

`PipelineIntegrationSession.advance` checks actual native choice errors and throws `pipeline/v1/rejected-action` before snapshot/delivery/B2/health preparation (`pipeline_integration.ts:652–654`). Catch discards and destroys that candidate. A fresh retry restores the unchanged committed parent. There is no supported rejected-update, partial-choice or undo commit entry point. Thus the genuine updated overlay observed here has no committed parent/serialization lineage that can legitimately feed the requested positive consumer proof.

Slowking bounded independent static review: **guard repair accepted**, historical/root-edit restrictions remain fail-closed; **positive Prompt51 closure blocked** by that reachability seam. Reviewer performed no execution. No test injected a committed boundary, caller map or modified reset result to manufacture authority.

The precise prerequisite is a separately approved recoverable request-update/partial-choice session contract: error acknowledgement and choice-error clearing; candidate authority and partial-choice ownership; step/branch/snapshot fingerprint semantics; receipt/ledger/B2 parent continuity; action/bundle treatment; retry, rollback and privacy. No such contract was implemented here. Positive held-overlay restoration, altered-held-parent controls specific to that path and its consumer commit remain UNPROVED; unchanged infrastructure evidence is reused.

99 frozen original inputs,106 protected candidate inputs and six dependency pins match. One affected ignored JS output is inventoried. No whole-tree attestation, dependency changes, other current adapters, Python/publication, promotion, commits or training. No pending processes/checks.
