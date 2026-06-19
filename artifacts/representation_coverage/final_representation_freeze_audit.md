# Final Representation Freeze Audit

**Date:** 2026-06-19  
**Decision:** Freeze `live-private-belief-v7` and `legal-action-v5` for a small
diagnostic dataset. Do not begin full reindexing or production retraining.

## Findings

The 29 matrix rows marked `blocker_before_retraining` are not all fully closed.
The central identity/mechanics slices are implemented diagnostically, while
several rows are partial or intentionally deferred. This is acceptable for a
bounded diagnostic experiment whose purpose is to test feature generation,
storage, learning sensitivity and calibration—not to produce a promotable model.

| Area | Status | Feature version | Test coverage | Retrain blocker? | Notes |
| ---- | ------ | --------------- | ------------- | ---------------- | ----- |
| Stat stages/current typing | Implemented | state v3+ | Slice 1 counterfactuals | No for diagnostic; old live models remain blocked | Complex boost operations still need long-tail coverage |
| Item/ability identity | Implemented/partial | state v4+ | Slice 2 counterfactuals | No for diagnostic | Global suppression and transfer edge cases remain |
| Species/roster/status | Implemented/partial | state v5+ | Slice 3 counterfactuals | No for diagnostic | Transform copied moves/stats and Illusion reconciliation remain partial |
| Tera/field/hazards | Implemented | state v6+ | Slice 4 counterfactuals | No for diagnostic | Exact hidden durations intentionally excluded |
| Move identity/PP/locks | Implemented/partial | state v7 | Slice 5 counterfactuals | No for diagnostic | Opponent PP is unknown by design; Choice is inferred |
| Static action consequences | Implemented/partial | action v4 | Slice 5 action tests | No for diagnostic | Numeric recoil/drain/heal and probability weighting remain |
| Resolved action impact | Implemented/partial | action v5 | Slice 6 ten-case suite | No for diagnostic | Soak override has a dual-to-mono limitation; belief calibration deferred |
| Raw/effective combat stats | Deferred | none in v7 | Damage/order tests only | Yes for full training | Own normalized raw stats and combined effective-order context remain absent |
| Switch candidate material | Partial | action v4/v5 prefix | Switch identity tests | Yes for full training | Current types, stats, item/ability, moveset and exact hazard loss remain thin |
| Full resulting-state delta | Partial | action v5 | Draco/branch/immediate-impact tests | Yes for full training | Immediate opponent HP is not authoritative future-position evaluation |
| Public belief content | Deferred | coarse counts in v7 | Privacy/determinism tests | Yes for full training | Candidate identities/distributions still collapse to counts |
| Live/default compatibility | Preserved | state v2/action v3 | Metadata/default tests | No | No live default or checkpoint was changed |

## Schema stability

State dimensions are stable and documented:

- v2 115D (live default)
- v3 217D
- v4 765D
- v5 2293D
- v6 2493D
- v7 3208D

Action dimensions are stable and documented:

- v3 165D (live default)
- v4 269D
- v5 318D

Each diagnostic state version is append-only over its predecessor. Action v4 is
an exact v3 prefix extension; v5 is an exact v4 prefix extension. Focused tests
assert ordered names, dimensions, vector prefixes and strict metadata matching.

Existing checkpoints remain compatible with their original exact schemas.
Cross-version loading is intentionally rejected rather than padded or truncated.
Diagnostic versions are opt-in and are not production defaults.

## Remaining blockers

Acceptable for `diagnostic_300`:

- incomplete combined effective-speed/order context;
- no normalized own raw-stat block;
- coarse opponent belief content;
- partial Transform/Illusion and global ability-suppression handling;
- boolean rather than numeric recoil/drain/heal;
- partial switch-target material;
- immediate rather than full next-state action consequences.

Still blocking full 15k reindex/training:

- final replay-profile evidence and battle-level sample manifests;
- measured v7/v5 feature-build throughput and storage;
- training-label contract for state value/action rank/action value;
- richer switch-candidate and effective-order representation;
- full transition-derived labels where future consequences matter;
- compact public-belief identity/distribution representation;
- small/medium benchmark results and held-out calibration/sanity gates.

## Freeze conclusion

The representation itself is ready to be frozen for a **small, disposable,
non-production diagnostic dataset**. Training is not yet gate-open: implement
the replay profiler, materialize `diagnostic_300`, benchmark feature generation,
and confirm label/split metadata first. Full reindexing remains blocked.
