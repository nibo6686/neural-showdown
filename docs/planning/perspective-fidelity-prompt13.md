# Prompt 13 — S01a: request-knownness characterization and additive design (no production edits)

Lead split of S01. S01 changes the observation schema and identities, so one reviewed design checkpoint precedes any production edit. Implemented by a Claude Code worker; lead reviews, an independent reviewer checks, lead reruns.

## Objective
Prove, with real raw requests through the real normalizer/observation/Python path, exactly which request-knownness the system currently loses (K07/K08/K20 in prompt3-matrix.md), and propose the smallest additive, versioned representation that preserves it without altering legal-action authority or any existing v1/v2 identity.

## Owned writes (new files only)
- sim-core/tests/request_knowledge_characterization.test.ts and trainer/tests/test_request_knowledge_characterization.py (characterization/red tests; they must pass by asserting the CURRENT lossy behavior, each labelled `CURRENT_BEHAVIOR_LOSSY`, so they flip when S01b lands).
- docs/planning/perspective-fidelity-prompt13-* : progress, design, report (<1000 words), validation.json, hashes, protected-baseline inventory, local diff.
No edits to any existing file (including env_manager.ts, action_codec.ts, observable_state.ts, state_extractor.ts, pipeline_record.py, contracts). No production change, no schema bump, no staging/commit/push/install/dataset/training.

## Required evidence
1. Raw emitted requests captured BEFORE normalization from a test-owned pinned pokemon-showdown@0.11.10 BattleStream/addressed-player harness (reuse docs/planning/perspective-fidelity-prompt12-witness.cjs ideas; do not alter it). Cases: ordinary active slots (PP/maxPP/target present); locked move (choice/Encore/two-turn); recharge; Struggle fallback; real PP 0 versus absent PP; `maybeDisabled`/`maybeTrapped` present vs absent vs known trapped/disabled; bench/waiting/forced-switch/revival/terminal requests (no active slots); both owners.
2. For each: the raw JSON fields, the normalized request (action_codec normalizeMove etc.), the observation view the pipeline emits (v1 and v2), and what Python's validator/record carries. Show concretely that absent PP/maxPP become 0, missing target becomes normal, and maybe* flags are dropped, and that PP 0 and "PP absent" become indistinguishable.
3. Confirm legal actions derive only from the current addressed request and that unknown PP never creates legal moves.
4. Design proposal (docs only): exact new-version fields (names, types, null/absent semantics: emitted / omitted / maybe-flag), where they live (new observation schema version vs sidecar), how v1/v2 bytes and identities stay unchanged, how Python independently validates them (including false-certainty and wrong-owner reseal controls), compatibility with the accepted perspective-knowledge contract (docs/contracts/PERSPECTIVE_KNOWLEDGE.md), exact file write set for S01b, and the red tests S01b must make green. Include rejected alternatives and risks.
5. Windows/UTF-8: run with PYTHONUTF8/PYTHONIOENCODING unset; Python at D:\Anaconda\envs\neuralgpu\python.exe, PYTHONPATH=trainer/src, PYTHON env var set for node tests; long commands in background.
6. Verify protected baseline hashes unchanged (use perspective-fidelity-prompt12-source-baseline.json style; only your new files and lead planning files may differ).

Return a candidate for lead review; do not begin S01b.
