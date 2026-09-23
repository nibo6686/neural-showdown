# Test Matrix

| Area | Planned test | Dependency | Status |
|---|---|---|---|
| Observation | Prefix cutoff and event-cursor monotonicity | STATE-001, FIXTURE-001 | Accepted |
| Privacy | Public/private/belief redaction | STATE-001, BELIEF-001 | Accepted |
| Actions | Python/TypeScript action round-trip | ACTION-001, FIXTURE-002 | Accepted |
| Legality | Force-switch, trapping, disabled, zero PP, slot gaps | ACTION-001 | Planned |
| Transition | Seed repeatability and branch isolation | TRANS-001 | Accepted |
| Features | Observation/belief provenance and schema fingerprint | STATE-001, BELIEF-001 | Planned |
| Data | Battle-disjoint split and prefix lineage | DATA-001 | Planned |
| Search | Exact versus belief versus approximate semantics | SEARCH-001, TRANS-001 | Planned |

Current environment blockers are recorded in [STATUS.md](../refactor/STATUS.md); no package installation is authorized in preparation.
