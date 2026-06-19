# Pre-Training Git Checkpoint Audit

**Date:** 2026-06-19  
**Scope:** vNext representation/model-design checkpoint before replay profiling,
dataset materialization, reindexing or training

## Working tree classification

| Class | Contents | Assessment |
| --- | --- | --- |
| Source code | `sim-core/src/{damage_calc,state_extractor,types}.ts`; state/action/live diagnostic modules under `trainer/src/neural/` | Intentional representation, extraction, provenance, calibration and diagnostic code |
| Tests | sim-core extractor test; v3–v7 state tests; action v4/v5, fidelity, trace, calibration and counterfactual tests | Intentional and required for checkpoint |
| Documentation/artifacts | action recommendations, representation coverage, schema manifest, training gate/design, calibration reports and this checkpoint audit | Intentional design/evidence records |
| Generated validation report | tracked `artifacts/validation/sim_core_validation_results.md`; ignored JSON companion | Markdown is small and useful checkpoint evidence; JSON remains ignored |
| Environment evidence | `artifacts/environment/environment_fingerprint.json` | Small reproducibility record; safe to include |
| Ignored/generated files | `sim-core/dist`, `node_modules`, caches, datasets, replay pool, checkpoints, analysis/eval/replay run outputs | Correctly ignored; exclude from checkpoint |
| Suspicious files | none found | No new replay catalog, sample manifest, dataset shard or model checkpoint |

`git diff --check` reports only expected LF→CRLF notices and no whitespace
errors. The untracked artifact directories are small report/diagnostic records,
not dataset materialization. The largest is the existing live-eval calibration
evidence directory at about 735 KB.

## Safety checks

- No files under `data/replays`, `data/policy`, `data/value` or
  `artifacts/checkpoints` were modified on 2026-06-19.
- Existing checkpoint binaries are ignored and unstaged.
- The full test command writes temporary smoke checkpoints under the system temp
  directory, not production artifact paths.
- No replay profiler/catalog or `diagnostic_300` manifest exists.
- No production checkpoint or live default was overwritten.

## Checkpoint scope conclusion

The tree is coherent for one representation/model-design checkpoint. Include
source, tests, hand-written/diagnostic evidence and the Markdown validation
report. Exclude all ignored large/generated ML data and runtime build outputs.
