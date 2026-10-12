# Prompt 13 (S01a) lead review

Date: 2026-10-10. Accepted locally as characterization + design. No production change.

## Lead verification (encoding overrides unset)
Checker rerun: build ok; new TS characterization 19/19; new Python 8 OK; retained TS request/observation/pipeline/identity 44/44; retained Python pipeline_record 46 OK; contract checker ok; whitespace ok; 1,195 protected entries unchanged, only the lead plan file drifted (expected), 0 unexpected files.

## Decisions
1. Sidecar `request-knowledge/v1` joined to unchanged v1/v2 observations by observation_id is approved. No edits to observation/bundle/identity code in S01b.
2. Maybe/trap flags: tri-state `true|false|null`. `false` is permitted only as a rule-derived value (pinned singles source rule: key omitted while a switch-in is available) and the record must carry `derivation` text/enum naming that rule; `null` = unknown not_emitted. Doubles are rejected. PP/target/disabled stay strictly null-when-omitted.
3. A sidecar may be built only from a freshly delivered addressed request. Snapshot-restored `StepResult.requests` are refused (required red test). Restoration/stale-request repair is S01c.
4. `presence` needs an explicit table mapped from classifyPipelineRequestState; `no_legal_actions` and `team_preview` are rejected, not mapped.
5. maybe_disabled / trapped / lock granularity: record on `active`; S01b writes an explicit broadcast/roster-join rule in a new docs/contracts/REQUEST_KNOWLEDGE.md and does not edit PERSPECTIVE_KNOWLEDGE.md; lead reviews the mapping.
6. Extra witness cases required: Struggle with maybeDisabled, Struggle from all-PP-0, Outrage/Rollout/Uproar locks, maybeTrapped/locked with empty bench (null), no_legal_actions, doubles rejection.

## Limits
Witness is test-owned (no authenticated delivery provider); absent=>false relies on pinned singles source; fragility of hard-coded counts noted.
