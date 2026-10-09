# Schema-Closure Boundary Repair Progress

## Initial state

- Branch: `refactor/state-001-observable-state`
- HEAD: `b056f7ef5433cef254d2cfdaf822cc23c0c24b0c`
- Initial `git status --short`: `?? docs/refactor/SCHEMA_CLOSURE_AUDIT.md` (pre-existing; preserve)

## Scope

Repair only audit findings B-01, B-08, and B-02. Preserve existing transaction rollback and lineage behavior, and do not alter the prior audit checkpoint.

## Progress

- Started: baseline recorded; targeted source and focused-test inspection complete.
- Reproduction: `projectPipelineProtocolPrefix(['|gen|9', '', '|turn|1'])` currently returns `['|gen|9', '|turn|1']`, while direct `validateRawProtocolRecord('')` rejects. Rehashed Python input-prefix request records `|request|{ "rqid": 12 }` and `|request|{"rqid":99}` both currently pass validation against the associated observation request rqid 12. The existing v2 public-stage control already exercises bare `|boost|...` normalization and typed opponent boosts; the six fixture classifications remain `raw-only` despite that behavior.
- Implementation: pipeline-prefix projection now rejects normalized empty segments while preserving the exact framing record and one final line delimiter. Python publication now requires canonical sanitized request JSON and joins retained request `rqid` values to the associated observation request. The six bare boost/transform fixtures are classified as represented based on v2 public-stage normalization. Added direct, atomicity, rehashed publication, classification, and v2 observation regression coverage.
- Validation: `npm run build` passed; focused TypeScript tests passed (61/61 across `pipeline_integration.test.ts`, `observable_state.test.ts`, `public_stages.test.ts`, and `protocol_contract_validation.test.ts`); focused Python suite passed (23 tests in `test_pipeline_record.py`); `git diff --check` passed.
- Follow-up B-08 parity repair: `request: null` remains a valid requestless observation; present non-null request values must be objects. Rehashed string, list, number, and boolean request values reject before DATA-001 output across v1/v2, p1/p2, and input/successor prefixes. A retained `rqid` now requires an associated object request with the same safe integer value.
- Separate review: accepted with no material findings. The coverage source list already contains every changed implementation and regression file. Attested local coverage digest: `6648d4b3836f4e90cc416a941810f0271ad2e934f0bd94a7983042711dfa9691`; previous reviewed digest: `985f33403ea2a5af4fe83aa8e647efba70d3f1f21a7809d3200c88805efafd5b`.

## Remaining boundaries

- B-03 generic effect-value classification still depends on the separate source-inventory scanner work; it was not included here.
- SLICE-002A scanner expansion remains deferred by request.
