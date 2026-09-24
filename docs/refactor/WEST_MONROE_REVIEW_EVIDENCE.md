# West Monroe Review Evidence Index

Date: 2026-09-24

## Purpose and limits

This index organizes available evidence for a later West Monroe review. No
West Monroe internal engineering, security, delivery, or product standard was
provided for this task. This document does not claim compliance, infer a
company standard, or treat test counts as approval.

The independent project review supplied for this task is
`/Users/nbolger/Documents/Codex/2026-09-24/files-mentioned-by-the-user-neural/outputs/PROJECT_REVIEW.md`;
its adjacent `review-evidence/` directory contains the prior repository/source
snapshots, `verification.log`, and `probe-results.md`. That review is historical
evidence for the state it inspected. The current worktree contains additional
uncommitted changes and must be reviewed separately.

## Evidence available

| Review area | Current evidence | Limit or next review need |
|---|---|---|
| Mechanics authority and scope | `docs/PROJECT_STATUS.md`; `docs/contracts/PIPELINE_INTEGRATION.md`; `sim-core/package.json`, lockfile, and installed metadata pin Showdown `0.11.10`; scope is `gen9randombattle`, Gen 9 singles. | The source digest does not verify the installed files against the lock tarball without a clean install. Actual generated team size remains authoritative. |
| Player information boundaries | Accepted `docs/contracts/OBSERVABLE_STATE.md`, `BELIEF_STATE.md`, `CANONICAL_ACTION.md`, and `SEEDED_TRANSITION.md`; focused state/action/pipeline tests. | FEATURE-001 is unresolved. No feature or training-input contract is accepted. |
| Move protocol semantics | Pinned source references in `docs/contracts/PIPELINE_INTEGRATION.md`: `battle-actions.ts`, `battle.ts`, `pokemon.ts`, `SIM-PROTOCOL.md`. Regressions cover active/non-active targets, omitted target, null target with source tags before final `[notarget]`, other tags, and malformed forms. The listed local-source digest has scoped semantic attestation. | Attestation covers only listed parser/pipeline sources and tests, not every protocol emitter or cross-format grammar. |
| Unknown-record stopping | Pipeline guards reject `clearstatus`, `-clearstatus`, and `nothing` with a versioned diagnostic. Tests exercise prefix projection, direct step-result projection, and candidate failure before boundary publication. | The aliases' source semantics remain unknown. `-nothing` is separately source-backed as a no-payload Gen 9 Splash record. |
| Determinism | Terminal regression fixes simulator seed `[101, 202, 303, 404]` and per-player random-controller seeds `0x51a7` and `0xc0de`; two complete normalized protocol traces match. | The baseline's legacy default still uses `Math.random()`. Controller RNG state is separate from simulator snapshot lineage. |
| Transition/data lineage | TRANS-001, DATA-001, and scoped PIPELINE-001 acceptance; fresh focused integration test called the Python record validator in fresh processes for both perspectives; 18 focused Python record/lineage tests passed. | PIPELINE-001 does not collect complete episodes or produce a dataset. |
| Simulator coverage | `docs/contracts/SIMULATOR_COVERAGE.md`, manifest, checker, and drift self-tests; inventory is 142 condition/effect IDs, 111 parser tokens, 86 literal emitter tokens. The listed local-source digest is semantically reviewed. | Counts do not prove per-effect lifecycle coverage. Volatile/side-condition semantics, unpacked-tarball provenance, and other documented omissions remain. |
| Reproducibility | `docs/refactor/ENVIRONMENT_VALIDATION.md`; exact Node package lock and focused commands. Simulator-only Python bridge imports standard-library modules. | ENV-001 remains blocked by tested runtime/dependency policy, Python dependency declaration/lock, and clean-environment validation. Raw replay files are not required for simulator-only verification. |
| Quality and delivery process | Golden fixtures, versioned contracts, work-item register, rollback notes, and task-specific continuation log. | No CI/CD configuration or current operational/security audit is established here. Historical risks need revalidation before reuse or deployment. |
| Product definition | `docs/PROJECT_STATUS.md` separates dataset, model, and product-release milestones. | User, MVP boundary, service objectives, release ownership, and production acceptance criteria remain future decisions. |

## Fresh verification evidence — 2026-09-24

- `npm run build --prefix sim-core`: passed.
- Focused TypeScript command covering simulator coverage, state extraction,
  observable state, action codec, and pipeline integration: 42 passed, 0 failed.
- `PYTHONPATH="$PWD/trainer/src" python3 -m pytest
  trainer/tests/test_pipeline_record.py trainer/tests/test_dataset_lineage.py
  -q`: 18 passed.
- Normal coverage checker passed with 142 classified IDs, 111 parser tokens,
  and 86 literal emitter tokens; all six synthetic self-tests passed. Reviewed
  local-source digest:
  `479a096563318af86addd64dd39d445c56e8c5b4d9c8ba0a1c0e100b3c3861d2`.
- The bounded 169-pair probe at seed `[101, 202, 303, 404]` had zero natural
  postflight rejects, but source review identified a specific hidden-trap
  request mismatch. A fresh regression at seed `[46, 101, 202, 303]` reaches
  Dugtrio/Arena Trap versus Tinkaton/Steel; a currently offered p2 switch is
  naturally rejected by Showdown after preflight, and committed lineage stays
  unchanged.

Exact commands, the earlier failed assertion and correction, source notes, and
next actions are preserved in
[`PIPELINE-CORRECTNESS-2026-09-24-PROGRESS.md`](PIPELINE-CORRECTNESS-2026-09-24-PROGRESS.md).

## Review work still required

1. Review SIM-COVERAGE effect/lifecycle gaps and PIPELINE-002's complete-episode
   request progression requirements.
2. Complete ENV-001 policy and clean-environment verification before claiming
   reproducible data/model work.
3. Resolve the training objective, information regime, feature/model interface,
   dataset validation, held-out evaluation, and operational release requirements
   at their separate milestones.

PIPELINE-001 is accepted for the explicit v1 joint-actionable scope. FEATURE-001
remains unaccepted. No West Monroe compliance claim is made.

When formal West Monroe criteria are supplied, add a criterion-by-criterion
crosswalk to direct evidence and unresolved items. Do not retrofit requirements
or compliance labels into this index without that source standard.
