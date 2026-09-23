# Refactor Risks

| Risk | Impact | Mitigation | Owner |
|---|---|---|---|
| Observation includes future events | Invalid training/evaluation | Prefix fixtures and monotonic event cursors | State owner |
| Belief fields enter observation | Information leakage | Separate schema and provenance checks | Belief owner |
| Python/TypeScript slot mismatch | Wrong action execution | Cross-runtime parity fixtures | Action owner |
| Seed lineage is incomplete | Non-reproducible search | Explicit transition metadata and repeatability tests | Simulation owner |
| Existing features silently change | Model regression | Golden feature snapshots and schema fingerprints | Model owner |
| Replay/private sources mix | Misleading metrics | Source lineage and battle-level splits | Data owner |
| Missing local dependencies | Validation blocked | Record environment prerequisites; do not install in this phase | Orchestrator |
| New adapter diverges from Showdown | Mechanics regression | Keep sim-core authority and differential tests | Simulation owner |
| Missing raw replay fixtures are mistaken for a production failure | Misleading readiness signal | Mark replay tests, skip with an actionable reason, and keep acquisition opt-in | Orchestrator |
| Python dependency policy is guessed from one host | Non-reproducible validation | Record the blocker; establish versions only after compatibility testing | Orchestrator |
| Observable adapter is accidentally routed into current models | Silent model/input drift | Keep the adapter shadow-only and assert unchanged feature vectors before integration | State owner |
| Prefix boundary is supplied at turn rather than record granularity | Future-information leakage | Require explicit normalized prefixes, deterministic hashes, and monotonic projector checks | State owner |
