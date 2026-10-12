# Prompt 2 lead review — 2026-10-09

Scope: local UTF-8 transport candidate on main `accab655c26ada18124e790b16d5770c8bd17894`. No publication assessed.

## Findings and Decision

No blocking transport finding. Accept locally for the reviewed wire boundary; release Prompt 3's read-only audit. Source-provenance reconciliation remains open before broader acceptance.

Production `pipeline_record.main()` already used binary-first JSON input and ASCII-safe publication. The actual corruption occurred in inline identity/batch consumers using locale text input. The repair shares existing byte-based input semantics, gives plain diagnostics explicit UTF-8 output, and preserves text-only embedding. Invalid code units escape via backslashreplace instead of raising during diagnostic output. Canonical serialization options, guard logic, interpreter overrides, subprocess timeouts and publication-after-validation ordering remain unchanged.

Transport tests use test-owned Showdown snapshots and actual Node/Python CLI publication for both perspectives. They clear encoding override keys in child environments, validate identity-bearing Unicode, reject tampering/malformed bytes, and check exact diagnostic characters plus lone-surrogate error handling. These are transport witnesses, not broad format/state-fidelity evidence.

## Fresh Lead Validation

- `node --test --test-isolation=none --test-reporter=spec sim-core/dist/tests/pipeline_utf8_transport.test.js`: exit 0, **3 passed**, 1.42s, with both encoding overrides unset.
- Conda Python `-m pytest trainer/tests/test_pipeline_record.py -q -k 'cli or unicode' --tb=short`: exit 0, **4 passed, 41 deselected, 2 subtests passed**, 0.11s, overrides unset.
- `git diff --check`: passed.
- Prompt 1 test SHA-256 unchanged: `db1e08de96e455fe65a5678e1222dbb429f2e2f03df1c15e04b77c0ff744796c`.
- Worker-reported build and exact v2 episode red/green evidence reviewed; episode green **1 passed in 50.65s** was not repeated by this lead. It preceded the isolated surrogate-diagnostic refinement; the final transport suite covers that refinement.

## Open Provenance Item

`npm.cmd run check:simulator-coverage --prefix sim-core` exits **1**:

```text
Local coverage source digest changed: ae3ef0d656b57b35a1a6339793fc176c5ac8a363d29a09944481864444301a3d
```

This is expected detection of local changes. The new `pipeline_json_wire.py` helper and `pipeline_utf8_transport.test.ts` are absent from the manifest's explicit local source list. That digest therefore is not a complete candidate attestation for the new dependency/test surface. Prompt 3 must identify exact inclusion and independent review requirements as a separate maintenance task. No manifest, reviewed digest or historical attestation was changed here. Transport acceptance does not declare the overall coverage gate passing.

## Reviewed Candidate Hashes

| File | SHA-256 |
|---|---|
| trainer/src/neural/pipeline_json_wire.py | 5b03c4029aabe203f25a605cc8a260786597153e6b76dd40ecda4c2aef0459ff |
| trainer/src/neural/pipeline_record.py | 1e36e8fd2446dbc91936c5be54a36c463bdc6d4ad8da554ab7f46e4818a21732 |
| sim-core/tests/pipeline_episode.test.ts | bfd64c021d53901748a02e2e7941e2f45dcbf31d627275ed086a8fa97376c49a |
| sim-core/tests/pipeline_utf8_transport.test.ts | b284c1614e2fea0d23601275173e775026e42295f8c496e41a68ee4c664d0c9a |
| README.md | 927dbda9329216d48ce9ed513037de59593662c2d800153d5f6503210a26ba5b |

These identify local reviewed bytes only. Broader state sufficiency, replay policy integration, clean Windows installation and training remain unaccepted. No commit, publication, merge or training authorization.
