# Prompt 16 (S01c-1) lead review — restoration of a rejected-choice request

Date: 2026-10-10. Accepted locally. First production edit of the initiative: sim-core/src/env_manager.ts (+153/-2) plus new sim-core/tests/active_request_restore.test.ts.

## Lead verification (fresh build via `node node_modules/typescript/bin/tsc`, encoding overrides unset, each file run on its own)
- Restoration suite 15/15 (includes the 3-seed v1/v2 pipeline corpus byte-identical to pre-change evidence, both-owners-mutated, no-key for forced switch/revival/doubles, silent-drop hook, forged trap/disabled edits).
- Core set (env_manager, forced_switch, settling, transition, belief_fork, record_identity) 54/54; pipeline_integration 10/10 alone and on the pre-change dist; revival 11/11; request_knowledge 12/12; characterization 19/19; perspective_knowledge 62/62; perspective_knowledge_source 21/21; Python pipeline_record + request_knowledge 65 OK.
- Correction-round items confirmed present in source: trap edit requires regenerated Pokemon trapped (env_manager.ts:437), silent-drop counter/hook, move edit requires actually-disabled move.

## Process notes
- Running several test files in ONE node process with --test-isolation=none produced 35 spurious failures (shared state). Run files individually. Not caused by this change.
- Independent review (fresh context) found no blocker; its two follow-ups were applied.
- Worker was stopped by the lead after ~1h; the lead completed verification.

## Limits
Extra Battle.fromJSON per live serialization (~1.4 ms). Mutated-state snapshots get new fingerprints by design; restored legal set excludes the rejected action by design. Restore re-emits stay `restore_reemit`/unattested. Provenance checker drifts (env_manager.ts, Prompt 9 contract edits) -> M02. Singles only.
