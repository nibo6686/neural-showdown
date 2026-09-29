# Prioritized Backlog

## Objective

Establish an auditable support boundary for per-player `observable-battle-state/v2` transitions in the pinned `gen9randombattle` format. The MVP should prove that a supported transition preserves exact public evidence, the acting side’s private request and legal actions, cursor and lineage integrity, and explicit stops for forms that are not classified.

## Prioritization Principles

- Close shared protocol grammar, visibility, and stop rules before expanding source inventory.
- Use pinned Showdown source and operative format evidence; registry counts or package-wide emitters alone do not prove random-battle reachability.
- Keep TypeScript and Python validation, privacy, cursor, and publication behavior aligned, with rejected candidates producing no successor publication.
- Preserve uncertainty: keep supported raw-only records raw-only and stop on unsupported or unclassified forms.
- Keep the milestone to transition capture; retain `faithful_complete_episode:false` and exclude data, feature, and model work.

## Backlog Table

| Priority | Story / Requirement / Slice | Rationale | Dependencies | Suggested Owner | Demo Value |
|----------|---------------|-----------|--------------|-----------------|-----------|
| P0 | **SLICE-001 — Complete the schema-closure audit** (REQ-008; AC-006) | First post-current-batch slice. Inventory every shared protocol field and token shape for grammar/type, visibility, source role, validation, and raw-only versus unsupported-stop disposition. Include request redaction and side-private routing, contract-loader behavior, and TS/Python parity. Triage the assessment’s recorded grammar and loader findings against the current accepted snapshot before treating them as resolved. | Pinned `pokemon-showdown@0.11.10` source and `protocol_contract.json`; none of the scanner expansion depends on unrecorded assumptions. | Backend / QA | Show a field-to-source-to-validator matrix, including both runtime decisions and explicit stop behavior. |
| P0 | **SLICE-002A — Expand the simulator source scanner and effect inventory** (REQ-007–009; AC-007) | The current inventory misses nested and dynamic paths, including `Move.condition`, `Move.slotCondition`, self/nested hit effects, and ability/item condition hooks. Reconcile discovered commands and effect values with typed, raw-only, and unsupported dispositions so generic events cannot promote unknown values into state. | Accepted schema-closure matrix; pinned simulator source. | Backend | Show a scanner finding a nested or dynamic source and a drift check detecting an inventory change. |
| P0 | **SLICE-002B — Bind operative format provenance and establish reachability** (REQ-001, REQ-007–009; AC-001, AC-007) | Hash operative format configuration and relevant custom-format inputs. Distinguish direct `gen9randombattle` pool candidates from selection/pruning and indirect reachability through call, copy, reflection, and callbacks. Give each relevant reachable form source evidence and a typed, raw-only, or unsupported disposition; unresolved closure must stop capture. | Scanner/inventory output from SLICE-002A; pinned package and exact `gen9randombattle` metadata. | Backend / QA | Demonstrate that an operative format/config change changes provenance, and trace a candidate from the random-battle path to its capture disposition. |
| P0 | **SLICE-003/004 — Accept bounded v2 per-side transition capture and publication parity** (REQ-002–006, REQ-009–012; AC-002–005, AC-008–011) | Close the milestone on a bounded transition: both perspectives use only their public prefix through the exact normalized record cursor plus their own current request/legal actions; identities and deterministic transition lineage agree across runtimes. Unsupported, malformed, stale, or rejected candidates leave the committed boundary unchanged and emit no successor. Preserve unknown versus absent and the v2 public-stage contract. | Schema, scanner, and reachability dispositions above; existing observation, action, transition, and publication contracts. | Backend / QA | Walk through both player views at an exact cursor, then show a rejected candidate stopping without changing the committed boundary or publishing a successor. |
| P1 | **Scoped review and coverage attestation** | Review the source, format/config digests, scanner drift evidence, both-runtime validation, and explicit stop matrix together. Attest only the bounded transition-capture scope and its remaining exclusions. | P0 slices complete with reproducible evidence. | QA / Product | Present a reviewable evidence bundle that states exactly what is supported, raw-only, and stopped. |

## Recommended MVP Sequence

1. Complete **SLICE-001 schema closure** and disposition existing parity/grammar findings against the current accepted snapshot.
2. Expand the source scanner and reconcile nested/dynamic command and effect inventory (**SLICE-002A**).
3. Bind operative format provenance and establish direct/indirect `gen9randombattle` reachability (**SLICE-002B**).
4. Validate bounded per-side v2 transition capture, publication parity, and atomic rejection behavior (**SLICE-003/004**).
5. Complete scoped review and attest only the evidence-backed boundary.

## Risks / Watchouts

- The accepted Helping Hand `[of]` active-source correction is a narrow protocol-boundary acceptance; it does not close every protocol field, token grammar, or effect value.
- Scanner coverage can miss nested or dynamically selected behavior. A package-wide emitter or direct random-set list does not establish reachable format closure.
- Operative `config/formats.ts` and custom-format inputs are not currently covered by the assessment’s provenance digest; configuration drift could evade the coverage guard.
- Some otherwise valid generated battles can reach `-singlemove`. Keep it an explicit unsupported stop, even if this truncates a transition. Keep `-singleturn` raw-only and never infer typed volatile state from it.
- The pinned install has not been recreated from its lockfile tarball. This remains a separate ENV-001 blocker to a fresh-environment reproducibility claim.
- Do not equate a captured transition with a complete battle or episode. Keep `faithful_complete_episode:false`.

## Suggested Demo Narrative

- Start with the schema-closure matrix and show how a field’s source form, visibility, validation, and disposition agree in TypeScript and Python.
- Show the expanded scanner and drift evidence, then trace one direct or indirect `gen9randombattle` candidate against the operative format configuration.
- Demonstrate a bounded two-perspective capture through an exact event cursor. Preserve `-singleturn` as raw evidence, and show `-singlemove` taking the explicit unsupported-stop path without a successor publication.
- Close with the attested limits: `faithful_complete_episode:false`, no replay collection or dataset output, and no feature, training, or model work.

## Backlog Notes

### Stories to Split Smaller

- Keep schema grammar/visibility closure distinct from scanner and mechanic-source inventory. The schema audit produces the disposition rules that the scanner must populate.
- Keep scanner expansion separate from operative-format provenance and reachability review. One establishes source inventory; the other establishes which paths apply to the exact target format.
- Keep lifecycle semantics for individual effect families separate from the capture acceptance gate. Do not bundle broad mechanic implementation into an audit item.

### Dependencies That Could Block Delivery

- Schema closure needs the pinned source and a field-level TypeScript/Python comparison, including request sanitization and publication behavior.
- Reachability acceptance depends on scanner output and operative format/configuration inputs being included in provenance checks.
- Cross-machine reproducibility claims remain blocked until ENV-001 clean-environment recreation is separately accepted; this does not replace semantic coverage review.

### Can Be Mocked or Deferred

- Unknown or unreviewed protocol/effect forms can remain explicitly stopped; they do not need a guessed implementation to meet this bounded milestone.
- Keep `-singleturn` as validated raw-only evidence and `-singlemove` as an unsupported stop. Defer broader volatile/turn-lock, slot/side/field lifecycle, and callback-family support until source and reachability coverage is closed and a specific supported transition requires it.
- Defer replay downloading, dataset generation, feature implementation, training, model loading, external set catalogs, other formats/generations, and complete-episode publication.
