# Test Matrix

| Area | Planned test | Dependency | Status |
|---|---|---|---|
| Observation | Prefix cutoff and event-cursor monotonicity | STATE-001, FIXTURE-001 | Accepted |
| Privacy | Public/private/belief redaction | STATE-001, BELIEF-001 | Accepted |
| Actions | Python/TypeScript action round-trip | ACTION-001, FIXTURE-002 | Accepted |
| Legality | Force-switch, trapping, disabled, zero PP, slot gaps | ACTION-001, FIXTURE-002 | Accepted contract coverage; targeted/multi-active actions remain outside v1 |
| Transition | Seed repeatability and branch isolation | TRANS-001 | Accepted |
| Simulator state/protocol | Pinned condition inventory, protocol grammar, source drift | SIM-COVERAGE-001 | Review evidence complete with explicit gaps; not a completeness acceptance |
| Pipeline integration | Two-transition lineage, both perspectives, deterministic identity, rejection preservation | PIPELINE-001 | Implementation candidate; acceptance pending natural simulator rejection coverage |
| Features | Shared collection/inference schema, information regime, feature provenance | FEATURE-001 | Not designed/accepted; no extractor or feature vector defined |
| Data | Battle-disjoint split and prefix lineage | DATA-001 | Accepted lineage contract; new refactored dataset not generated |
| Search | Exact versus belief versus approximate semantics | SEARCH-001, TRANS-001 | SEARCH-001 documentation accepted; runtime contract integration not covered |

Current environment blockers are recorded in [STATUS.md](../refactor/STATUS.md); no package installation is authorized in preparation.
