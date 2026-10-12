# Prompt 8 — Design the perspective-knowledge contract

Lead-authorized C01 design proposal. Return for contract review before implementation.

```text
Use $draft-implementation-plan and $review-plan-tests. Useful project skills: product-specification-agent and wm-spec. The project lead remains in the other conversation and owns contract decisions. No later task or further delegation.

Repository: C:\Users\cloud\Downloads\neural\final. Read repository protocol/review state, current reconciliation, initiative plan and Prompt 7 lead review. Reuse Prompt 3 matrix K01-K20/R01-R05 and tasks C01; inspect only relevant source seams to resolve specific questions. Preserve prior implementation candidates and evidence.

Objective: propose the smallest coherent contract that tracks legitimate knowledge for each player throughout battle, separating immutable owner-starting facts, current owner/public knowledge and the current action request. Define persistence, uncertainty, identity and provenance before adding a schema or training features.

Owned writes: docs/planning/perspective-fidelity-prompt8-design.md, perspective-fidelity-prompt8-examples.json, and task-specific progress/report artifacts. Existing contract files are references; propose their exact future edits in the design rather than changing them now. No source, tests, manifests, attestations or aggregate-status edits.

Settled policy:
- Simulator/live knowledge uses legitimate addressed owner evidence and exact chronological public prefixes. No future-event or opponent-private leakage.
- Public replay reconstruction uses the full replay to recover the player's OWN starting-team facts revealed at any point and makes those starting facts available from turn 1. Never-revealed or ambiguously attributed facts remain unknown.
- Acquired/copied moves, transferred items, changed abilities, transformations and dynamic HP/status/boosts are not automatically starting facts. Opponent revelations and dynamic state remain chronological.
- Retrospective replay evidence must carry explicit policy/version and provenance, distinct from causal simulator evidence. Replays must not invent private requests, PP, legal actions or trapped/disabled defaults.
- Existing faithful_complete_episode remains its pinned capture claim. Propose an explicit way to establish the stronger required knowledge assurance without silently expanding that Boolean or automatically admitting replays.

For each required family, define value/knownness, evidence source, owner, timestamp/prefix position, current versus stale semantics, identity join and persistence/clear/replacement behavior. Cover request-omitted PP versus zero, moves/slots/roster identity, original versus current item/ability, retained bench knowledge, current/effective versus starting stats, transformations/Illusion, owner details, field/lifecycle facts, waiting/requestless/revival/terminal/restoration and both perspectives.

Nature/EV/IV/happiness or other desired facts require a legitimate documented source; no arbitrary hidden engine-set reads. If source information is unavailable, say whether unknown is legitimate under the regime or blocks the requested stronger completeness claim. Do not call a missing required owner fact complete merely because it has an unknown marker. Cosmetic exclusions require an explicit proposed scope rationale.

Recommend a concrete versioning shape, comparing a new observation version with a separately identity-bound knowledge context. Existing exact v1/v2 keys and historical identities remain unchanged. Specify real integration points from capture/replay entrypoints through serialization, belief history, ordinary/full/compact Python validation and publication. Distinguish a reconstructable raw fact from a structured fact available to the consumer at the relevant boundary.

Examples must independently specify expected knowledge and provenance for both owners across initial, midbattle, waiting/requestless and terminal boundaries. Include owner starting ability/item revealed late, never-revealed facts, item transfer/consumption, copied/acquired move, Transform, Illusion/ambiguous attribution, missing PP, future-suffix invariance, replay-owner starting backfill and wrong-policy/source rejection. These are hand-authored contract examples, not generated expectations from current implementation.

Provide acceptance criteria and a bounded dependency-ordered implementation plan with write sets, independent oracles, real caller/serialization/publication tests and fully resealed semantic negatives. Identify open decisions with a recommendation and consequences. Separate verified source facts from proposals. Do not implement a broad state rewrite or represent a draft schema as accepted.

No runtime/test/contract adoption, dependency installation, network/replay fetching, checkpoint loading, dataset generation, training, live server, commit, publication, merge or attestation updates. Return design/examples, inspected source references, unresolved decisions and a memo under 1,000 words. Maintain durable progress before compaction. Return for lead review before coding.
```
