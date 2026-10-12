# Prompt 1 lead review — 2026-10-09

Scope: local fixture-repair candidate on main at `accab655c26ada18124e790b16d5770c8bd17894`; no GitHub PR or publication assessed. Applied architect-pr-review to fixture authority, validation quality and scope fit.

Reviewed test-file SHA-256: `db1e08de96e455fe65a5678e1222dbb429f2e2f03df1c15e04b77c0ff744796c`. This identifies the reviewed local candidate; it is not a simulator-coverage attestation.

## Findings

No blocking finding within this bounded fixture-repair scope.

The diff changes only `trainer/tests/test_pipeline_record.py` (51 insertions, three deletions): a dedicated positive-control helper and the two target methods. Generic `_bundle`, `_rehashed_protocol_candidate` and production validation are unchanged. Positive owned ability controls supply the correctly addressed roster/request and health facts; Trace base authority remains distinct. Transform controls retain unknown abilities without borrowing hidden target state. Opponent records receive no new ability fields.

The 72 negative variants mutate missing recipient, incorrect owner or contradictory addressed ability, reseal content identities, verify those identities independently, and require the specific public ability failure. CLI checks require exit 2 and empty stdout; post-validation immutability is asserted. Invalid controls therefore reach semantic guards rather than relying on stale hashes to reject.

This helper creates synthetic publication/grammar controls. It is not an independent source-engine oracle for real Trace/Transform lifecycles or complete-episode state truth; those remain outside this repair and belong in the planned audit.

## Evidence

Inspected worker report, exact unstaged diff, surrounding sealing/generic fixture code and `public_ability.py` authority validation. The tracked diff has no production changes.

Fresh lead run with process-local `PYTHONPATH=trainer/src` and `PYTHONUTF8=1`:

```powershell
& 'D:\Anaconda\envs\neuralgpu\python.exe' -m pytest trainer/tests/test_pipeline_record.py -q -k 'ce04_callback_a_ability_templates or rehashed_singleturn_and_singlemove' --tb=short
```

Exit 0: **2 passed, 43 deselected, 576 subtests passed in 4.79s**. `git diff --check` passed.

Worker-reported full record/lineage evidence: exit 0, **56 passed, 4,860 subtests passed** in 24.01s. Reviewed that report; did not rerun the full suites. Earlier red evidence and standard-library reproduction were already established in the Windows assessment.

## Decision and Next Action

Accept Prompt 1 locally for fixture correctness and guard preservation. Release Prompt 2, UTF-8 transport, using the prepared prompt. Preserve these changes and return the next candidate before Prompt 3. No commit, publication, merge, coverage self-attestation, broader fidelity acceptance or training authorization follows from this decision.
