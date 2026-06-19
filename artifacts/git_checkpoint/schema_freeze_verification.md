# Schema Freeze Verification

**Date:** 2026-06-19  
**Result:** PASS

## Frozen dimensions

| Family | Version | Dimension | Role |
| --- | --- | ---: | --- |
| State | `live-private-belief-v2` | 115 | live default |
| State | `live-private-belief-v3` | 217 | diagnostic |
| State | `live-private-belief-v4` | 765 | diagnostic |
| State | `live-private-belief-v5` | 2293 | diagnostic |
| State | `live-private-belief-v6` | 2493 | diagnostic |
| State | `live-private-belief-v7` | 3208 | diagnostic head |
| Action | `legal-action-v3` | 165 | live default |
| Action | `legal-action-v4` | 269 | diagnostic |
| Action | `legal-action-v5` | 318 | diagnostic head |

The code constants exactly match `feature_schema_manifest.json`. Ordered feature
names verify the complete append-only state prefix chain v2→v7 and action prefix
chain v3→v5. Action v5 is the exact 269D v4 prefix plus 49 fields.

## Defaults and compatibility

- `FEATURE_VERSION` remains `live-private-belief-v2`.
- `ACTION_FEATURE_VERSION` remains `legal-action-v3`.
- Diagnostic builders require explicit version selection.
- Metadata validators require exact version and dimension; cross-version
  padding/truncation is not allowed.
- Old checkpoints remain paired with their old feature versions.
- No checkpoint file is part of the working-tree diff and no production
  checkpoint was overwritten.

## Artifact boundary

No replay download, replay-profile output, `diagnostic_300` manifest, feature
dataset, reindex output or trained vNext checkpoint was generated. Historical
datasets/replays/checkpoints remain ignored and unchanged during this audit.

## Verification coverage

Focused tests cover each state slice v3–v7, action v4/v5, ordered prefixes,
strict checkpoint metadata, perspective/privacy behavior and controlled
counterfactuals. Native sim-core validation and the complete repository suite
are required immediately before the checkpoint.
