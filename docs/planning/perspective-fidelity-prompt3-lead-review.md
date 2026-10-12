# Prompt 3 lead review — 2026-10-09

## Scope and Decision

Reviewed the audit memo, K01–K20/R01–R05 matrix and proposed task boundaries against targeted current and pinned source. Accept the audit as a source-backed gap inventory for the stronger perspective-knowledge milestone. This is not runtime validation, complete semantic closure or approval of every proposed implementation/schema.

Release **V01 as Prompt 4: prove or dismiss field-ID semantic validation gaps**. No production repair authorized yet. M01 provenance reconciliation follows the proof review; C01 knowledge-contract design follows evidence assessment. This changes the proposed order because validator truth is a consequential uncertainty and later source changes would otherwise require repeated provenance freezing.

## Confirmed Findings

- `action_codec.normalizeMove` substitutes zero for missing PP/maxPP; pinned `Pokemon.getMoves` locked/recharge outputs legitimately omit these fields. Omission and actual zero are distinct knowledge states. This review does not establish an action-execution defect.
- Owned initial values can exist in origin evidence but lack an explicit persistent starting-knowledge context. That is a gap against the stronger requested consumer contract, not proof of information loss in accepted complete capture.
- Legacy `_reconstructed_completed_private_teams` merges by species and collects moves/last item/ability writers without original/acquired attribution. `_reconstructed_private_state_for_side` defaults missing HP/PP, disabled/trapped state and constructs request-like legal actions. The ordinary example caller omits `full_trajectory` and labels hindsight-derived facts `reconstructed_public_prefix`. This path does not meet the user's starting-only hindsight rule; no dataset execution or new simulator regression was inferred.
- Current observable projection invokes typed lifecycle/health/item/ability checks; the field-ID replay checks identified by the audit need a focused production-path probe. Absence from these call sites is not sufficient to claim successful publication of a forged field value.
- Prior Prompt 2 provenance findings stand. Newly added dependency/test files require inclusion and omission/mutation detection, with a later independent scoped review.

## Qualifications and Contract Decisions

The family matrix is not an exhaustive per-effect runtime proof. Raw-only retention preserves events; it neither proves all required state is reconstructable nor means every raw-only field must become typed. Each required family needs an explicit source/visibility/consumer disposition. Cosmetic metadata is not automatically a training-readiness blocker; define required facts by the reviewed knowledge contract.

Keep existing conditional sim-core faithful capture acceptance intact. New observation versions, a separate knowledge-completeness claim and named helper/module layout remain recommendations. Select the smallest coherent contract after the field proof; do not pre-authorize a broad state rewrite. An alternative can satisfy the stronger requirement through explicit reconstructable knowledge without changing historical observation identities.

Replay hindsight applies to uniquely attributable owner STARTING facts only. Dynamic and opponent facts remain chronological; ambiguous/never-revealed values remain unknown. A replay-context source/policy identity must distinguish this exception from causal observations and direct-observed belief evidence. Future revelation of an acquired move/item/ability cannot authorize an initial loadout fact.

## Evidence and Limits

Lead read current `action_codec.ts`, pinned `pokemon.ts` locked request forms, actual replay aggregation/caller/default/provenance code, observable projection checks, checker required-source code and latest scoped faithful-result verdict. No test or simulator run in this review. Worker performed a source-only audit; proposed red tests remain unexecuted. Production/test/manifest files were not edited by this lead.

## Next Boundary

Prompt 4 owns only focused field semantics test/probe artifacts and a report. Validate controls first; independently reseal false maps; classify actual TS and ordinary/full/compact Python outcomes. Return semantic rejection, unrelated rejection or publication success with exact evidence. A reproduced validator defect blocks stronger assurance and receives its own repair prompt. No commit, publication, attestation update, replay acquisition, datasets or training.
