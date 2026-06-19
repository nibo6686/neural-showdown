# Git Checkpoint Commit Plan

## Recommended commit

Title:

```text
Add diagnostic vNext state and action feature schemas
```

Body:

```text
- add append-only live-private state schemas v3 through v7
- add diagnostic legal-action schemas v4 and v5
- add representation coverage audits and schema freeze manifest
- add controlled counterfactual and provenance tests
- extend sim-core extraction and diagnostic damage/current-type support
- preserve live state v2 and action v3 defaults
- do not rebuild datasets, train models, or promote checkpoints
```

## Suggested staging commands

Run from the repository root:

```powershell
git add -- sim-core/src/damage_calc.ts sim-core/src/state_extractor.ts sim-core/src/types.ts sim-core/tests/state_extractor.test.ts
git add -- trainer/src/neural/action_features.py trainer/src/neural/action_recommender_diagnostic.py trainer/src/neural/action_side_effects.py trainer/src/neural/action_trace.py trainer/src/neural/item_ability_counterfactual_diagnostic.py trainer/src/neural/live_action_recommender.py trainer/src/neural/live_eval_calibration.py trainer/src/neural/live_eval_server.py trainer/src/neural/live_private_features.py trainer/src/neural/live_private_state.py trainer/src/neural/moves_actions_counterfactual_diagnostic.py trainer/src/neural/resolved_action_impact.py trainer/src/neural/resolved_action_impact_diagnostic.py trainer/src/neural/species_status_counterfactual_diagnostic.py trainer/src/neural/state_counterfactual_diagnostic.py trainer/src/neural/tactical_state.py trainer/src/neural/tera_field_counterfactual_diagnostic.py
git add -- trainer/tests/test_action_features_v4.py trainer/tests/test_action_features_v5.py trainer/tests/test_action_stat_delta_fidelity.py trainer/tests/test_action_trace.py trainer/tests/test_live_eval_calibration.py trainer/tests/test_live_private_features_v3.py trainer/tests/test_live_private_features_v4.py trainer/tests/test_live_private_features_v5.py trainer/tests/test_live_private_features_v6.py trainer/tests/test_live_private_features_v7.py trainer/tests/test_moves_actions_counterfactual.py trainer/tests/test_state_counterfactual_diagnostic.py
git add -- artifacts/action_recommendation artifacts/live_eval_calibration artifacts/representation_coverage artifacts/training_plan artifacts/git_checkpoint
git add -- artifacts/agent_audit/public_evidence_belief_calibration_design.md artifacts/environment/environment_fingerprint.json artifacts/validation/sim_core_validation_results.md
git status --short
git diff --cached --check
git diff --cached --stat
```

Then, after reviewing the staged diff:

```powershell
git commit -m "Add diagnostic vNext state and action feature schemas" -m "Add append-only state v3-v7 and action v4-v5 schemas, coverage audits, counterfactual tests, and sim-core extraction/provenance support. Preserve live state v2/action v3 defaults; no dataset rebuild or training."
```

## Include

- representation/live-eval source and tests listed above;
- coverage, action recommendation, freeze and training-gate documents;
- small diagnostic JSON/JSONL evidence under the explicitly listed report
  directories;
- environment fingerprint and Markdown sim-core validation result.

## Exclude

- `data/replays`, `data/policy`, `data/value`, `data/raw`, `data/shards`;
- `artifacts/checkpoints`, replay/eval/analysis run outputs and backup folders;
- `sim-core/dist`, `node_modules`, caches and Python bytecode;
- ignored `artifacts/validation/*.json`;
- future replay profiles, sample manifests, feature datasets and models.

The tracked Markdown validation report should be included because it records the
checkpoint's dependency/parity pass. Its ignored JSON companion should remain
uncommitted. Large datasets, replay dumps and checkpoint binaries must not be
force-added unless explicitly intended.
