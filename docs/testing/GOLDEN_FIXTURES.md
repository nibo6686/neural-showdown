# Golden Fixtures

**Status:** The initial FIXTURE-001/FIXTURE-002 acceptance plan has been
completed. Current inventory includes observable protocol, canonical action,
seeded transition, belief, dataset-lineage, terminal-observation, and simulator
coverage fixtures/tests. See [`TEST_MATRIX.md`](TEST_MATRIX.md),
[`../PROJECT_STATUS.md`](../PROJECT_STATUS.md), and the individual contracts.

New fixtures must preserve raw input, expected typed output, schema version,
privacy regime, and source/cursor provenance. Simulator-specific fixtures must
be synthetic or confirmed sanitized. Unknown protocol records and future-prefix
changes must fail closed.

Required fixture families:

- protocol-prefix request and decision boundaries;
- switch/replace, damage, healing, status, boost, faint, tera, transform, and illusion;
- repeated species and non-contiguous team slots;
- force-switch, trapped, disabled, zero-PP, move, tera-move, and switch actions;
- seeded exact transitions and repeated branch execution;
- public/private redaction and no-future-information assertions.

Accepted lower-level fixture work does not constitute acceptance of
PIPELINE-001 or FEATURE-001. Focused simulator coverage exercises confusion
start/end, another volatile, request-level trapping, `cant`, and hit-count
protocol behavior; semantic coverage beyond the reviewed fixtures remains
documented in [`../contracts/SIMULATOR_COVERAGE.md`](../contracts/SIMULATOR_COVERAGE.md).
