# QA Plan

## Scope

Validate **SLICE-003: v2 per-side projection closure** for pinned `gen9randombattle`. At one exact normalized protocol-record cursor, TypeScript must produce immutable `observable-battle-state/v2` observations for p1 and p2. Each observation includes only that side's sanitized current request and legal actions.

SLICE-002B provenance, format, source-digest, reachability, and scanner checks are prerequisites. This slice covers exact-prefix behavior, request ownership and privacy, three-valued knownness, raw-only preservation, and explicit stops.

It does not execute candidates, restore a transition, publish a Python/DATA-001 record, prove cross-runtime publication parity, or claim episode fidelity. `faithful_complete_episode:false` remains required. `-singleturn` remains raw-only, `-singlemove` remains an unsupported stop, and the six unresolved computed `addVolatile` paths remain unknown/fail-closed.

## Test Strategy

- **Unit tests:** exact-prefix identity, request redaction and ownership, unknown versus known-absent values, and record disposition before filtering.
- **Integration tests:** project one pinned synthetic battle prefix for both perspectives at the same cursor, with separate current requests and legal actions.
- **Functional smoke tests:** append a same-turn suffix, retain raw-only evidence, and stop on malformed, unsupported, and unclassified input without typed-state mutation.
- **Demo readiness checks:** show the two same-cursor observations, their stable identities after a suffix, and a visible stop result. Every result retains `faithful_complete_episode:false`.

## Scenario Matrix

| ID | Scenario | Type | Preconditions | Steps | Expected Result |
|----|----------|------|---------------|-------|-----------------|
| QA-1 | SLICE-002B prerequisite | Integration | Reviewed simulator/config and local coverage digests match the checkout. | Run the normal coverage checker before the fixture suite. | The fixture suite runs only against the accepted pinned source, format, and scanner state. |
| QA-2 | Exact cursor and suffix invariance | Unit / Integration | Capture p1 and p2 v2 observations at cursor `N`; prepare a same-turn suffix. | Append the suffix and compare both observations, hashes, and identities at `N`. | The prior observations remain byte-for-byte unchanged. |
| QA-3 | Perspective ownership and privacy | Integration | Mirrored p1/p2 requests contain distinct private fields and legal actions. | Capture both views and alter data visible only to the other side. | Each view contains its own sanitized request/actions and permitted public evidence only; the other request and hidden state do not alter its content or identity. |
| QA-4 | Unknown versus known absent | Unit | Fixture includes unrevealed opponent data and an absence established by visible/request evidence. | Project both perspectives. | Unrevealed values remain unknown; only supported evidence creates a known absence. No value defaults to `null`, `0`, `false`, or an empty known value. |
| QA-5 | Raw-only preservation | Integration | Source-shaped raw-only controls include `-singleturn`, `message`, and `-nothing`. | Project through a cursor containing each control. | Order, cursor, and sanitized evidence are retained without typed-state mutation. |
| QA-6 | Unsupported and unclassified stops | Functional | Use valid `-singlemove`, an unknown effect value, and a wrong-family effect value. | Project each prefix. | Each stops with structured record-index and classification evidence before typed projection. |
| QA-7 | Computed volatile dispositions | Coverage | The six unresolved computed `addVolatile` paths are present in the pinned scanner inventory. | Run scanner/coverage checks and inspect their explicit dispositions. | Each remains unknown/fail-closed. Do not invent emitted protocol fixtures for paths whose grammar is not source-backed. |
| QA-8 | Malformed input before filtering | Unit / Integration | Use empty segment, malformed request, bad player identifier, and malformed supported-record controls. | Validate and project each control. | Every malformed control rejects before filtering or repair and cannot mutate typed state. |
| QA-9 | Explicit bounded status | Functional / Demo | One supported p1/p2 capture plus raw-only and stop results. | Inspect result envelopes. | All results retain `faithful_complete_episode:false`; stop reason is present when applicable. |

## Demo Data Plan

- Create one small, versioned, pinned synthetic fixture only. It contains a shared public prefix, distinct p1/p2 current requests, legal actions, an unrevealed opponent field, and one evidence-backed known absence.
- Derive a same-turn suffix, a cross-perspective private-field perturbation, raw-only controls, stop controls, and malformed controls from that fixture.
- Preserve the immutable baseline for every case. The artifact should show per-side sanitized observations, cursor, prefix hash, identity, and diagnostic classification.

## Exit Criteria

- [ ] A supported pinned prefix produces immutable v2 observations for both perspectives at the same cursor.
- [ ] The p1/p2 requests and legal actions remain separately owned and sanitized.
- [ ] Same-turn suffixes preserve the earlier observations and identities.
- [ ] Unknown remains distinct from evidence-backed known absence.
- [ ] Raw-only evidence is retained without typed mutation; unsupported, unclassified, and malformed inputs stop before projection.
- [ ] The coverage checker verifies the accepted SLICE-002B prerequisite state.
- [ ] Every demonstrated result retains `faithful_complete_episode:false` and documented limitations.

## Recommended Smoke Test Script

```bash
npm run build --prefix sim-core
node --test \
  sim-core/dist/tests/observable_state.test.js \
  sim-core/dist/tests/state_extractor.test.js \
  sim-core/dist/tests/pipeline_integration.test.js \
  sim-core/dist/tests/public_stages.test.js
npm run check:simulator-coverage --prefix sim-core
```

## Known Risks / Manual Checks

- Do not treat a passing SLICE-003 projection fixture as a transition, publication, dataset, or complete-episode claim. Candidate execution, restoration, rollback of committed transitions, and TypeScript/Python publication joins belong to SLICE-004.
- Review the p1 and p2 serialized views with an allowlist to ensure private request fields never cross perspectives or enter the public prefix/identity.
- The six unresolved computed `addVolatile` paths remain deliberate stops. The checker must retain their classifications until source-backed grammar and lifecycle semantics are reviewed.
- Clean-environment recreation is a separate reproducibility gate.
