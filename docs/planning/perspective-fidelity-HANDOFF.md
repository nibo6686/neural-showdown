# Perspective-fidelity initiative — handoff (2026-10-10)

Read this first in a new conversation, then `perspective-fidelity-implementation-plan.md` (roadmap, acceptance contract FAC-01..07) and the lead reviews it links.

## 1. Goal
Before any model training, the system must track, for each player's perspective and at every point in a battle, exactly what that player legitimately knows. Own side: full team known from turn 1. Opponent: only what has been revealed; anything never revealed stays unknown. Unknown must never be silently replaced by a default (e.g. missing PP -> 0). The `faithful_complete_episode` flag (already conditionally accepted for supported `gen9randombattle` simulator captures) must be backed by this. Public replay reconstruction is an exception: facts revealed anywhere in a replay about the owner's own starting team count as known from turn 1; dynamic changes and opponent discoveries keep their real timing. Training, datasets and feature design are out of scope until the final gate.

## 2. How the work is run
- The user is the owner. Claude (this role) acts as project lead (`.claude/skills/project-lead`): plans, delegates, reviews, rechecks, accepts. Codex credits are exhausted, so implementation now runs in Claude Code via background worker subagents.
- Loop per boundary: write a prompt file `docs/planning/perspective-fidelity-promptNN.md` -> launch one worker (new files preferred, tight write set, progress file, evidence, hashes, protected-baseline check) -> independent fresh-context read-only reviewer -> correction round -> lead reruns the checks personally -> lead review file + plan update. Never accept on a worker's word alone.
- Skills installed in `.claude/skills/` (copied from `.agents/skills` and `~/.codex/skills/skills.zip`): project-lead, implement-plan, review-plan, review-plan-tests, architect-pr-review, draft-implementation-plan, simplify-code, update-docs, model-routing-advisor, plus the wm-* and agent skills.
- Repo guidance: `CLAUDE.md` (think first, simplicity, surgical changes), `docs/refactor/AGENT_PROTOCOL.md`.

## 3. Environment (Windows)
- Repo `C:\Users\cloud\Downloads\neural\final`, branch main, HEAD accab655 (merged PR #2). Working tree is heavily dirty with accepted-but-uncommitted work; NOTHING has been committed, staged or published. No commits/pushes unless the user asks.
- Python: `D:\Anaconda\envs\neuralgpu\python.exe`, `PYTHONPATH=trainer/src`. Node tests need `PYTHON=<that python>`. Keep `PYTHONUTF8` and `PYTHONIOENCODING` UNSET when testing (the point is to prove UTF-8 handling).
- Build: `npm run build` fails (the user's npm install made no `.cmd` shims). Use `node node_modules/typescript/bin/tsc -p tsconfig.json` from `sim-core`, or ask the user to rerun `npm install` in PowerShell.
- Run node test files ONE AT A TIME (`node --test --test-isolation=none sim-core/dist/tests/<file>.test.js`). Combining files in one process gives spurious failures. Python: `python -m unittest trainer.tests.<module>`.
- Long commands: run in background and poll; the Python record suites take ~30-70 s.
- `git config core.autocrlf=true`: hash-pinned files must be `-text` in `.gitattributes` (done for two).

## 4. What is accepted so far (all local, uncommitted)
| Step | Result |
|---|---|
| Prompts 1-2 | Stale ability fixtures fixed; Windows UTF-8 transport (shared byte-based JSON reader). |
| Prompt 3 | Source-backed gap inventory (K01-K20, R01-R05). |
| Prompts 4-5 | Proved and fixed false weather/terrain/Trick Room acceptance (field-truth validation, TS+Python). |
| Prompt 6 | Regression baseline restored (fixtures, locale-safe identity reader). |
| Prompt 7 | Provenance registration for new files; scoped attestation (digest 8879baab...). |
| Prompts 8-11 | Perspective-knowledge contract (`docs/contracts/PERSPECTIVE_KNOWLEDGE.md` + fixtures), strict TS/Python parsing, identities, structural proof joins, non-publishing CLI. |
| Prompt 12C, 12 | Native legacy-ID spellings; source/legacy verification seam (`perspective_knowledge_source.*`): process-local registry + verified legacy context + entry check. Non-publishing. |
| Prompts 13-14 | Request-knowledge: characterization of current loss (absent PP -> 0, maybe-flags dropped) and `request-knowledge/v1` sidecar (`request_knowledge.*`, `docs/contracts/REQUEST_KNOWLEDGE.md`). Does not alter observations/identities/legal actions. Derived-false flags are sidecar-local; the adapter must emit them as unknown. `fresh_delivery` token is advisory only. |
| Prompt 15 | S01c design (see `perspective-fidelity-prompt15-design.md`); decisions below. |
| Prompt 16 (S01c-1) | `env_manager.ts`: a rejected-choice request now survives snapshot restore (conditional sibling key, validated against engine-legal edits; byte-identical for non-mutated snapshots). Review: `perspective-fidelity-prompt16-lead-review.md`. |
| Hygiene | Test-helper UTF-8 stdin reads; `.gitattributes` `-text` for `segment-start.json` and `predecessor.json`; revival fixture ability; revival 11/11. |

Counts at last lead rerun: restoration suite 15/15; core 54/54; pipeline_integration 10/10; revival 11/11; request_knowledge 12/12 + characterization 19/19; perspective_knowledge 62/62 + source 21/21; Python pipeline_record + request_knowledge 65 OK.

## 5. Decisions already made (do not relitigate)
- Publication of the request sidecar: separate joined artifact `request-knowledge-publication/v1` (Option C); do NOT embed in existing bundles/episodes or bump observation to v3.
- `faithful_complete_episode` stays a function of existing fields only.
- Coverage vocabulary for restored/terminal rows: `unattested_restored`, `terminal_null`, `requestless_null`, `fresh_attested`.
- `lock` unknown for bare rows; K-fact adapter ships with an injected resolver (full roster/move rows wait for S02); keep refusing requests carrying `disabledSource`; delivery ledger exposed by a pull method on `LocalBattleEnv` (not a `StepResult` field); registry cursor == observation `event_cursor`; `origin.battle_key` == legacy `battle_id` at the seam.
- Restoration fix (R1) approved and done. Areas of code are not "sensitive" if tests prove behavior; many older paths are likely deprecated after the refactor.
- Contract file `PERSPECTIVE_KNOWLEDGE.md` is frozen; changes need a reviewed revision.

## 6. Remaining work (ordered)
1. **Real-replay regression harness (NEW, move earlier).** Use the user's two downloaded replays as unchanged fixtures: `Gen9OU-2026-10-10-hasklne-loob.html` (OU, out of accepted random-battle scope but same mechanics) and `Gen9RandomBattle-2026-10-10-hasklne-kaiserme.html` (real random battle, 27 turns, hasklne wins). Run through the actual production loader -> reconstruction -> serialization -> validator -> perspective consumer, both perspectives, checking state throughout (not only the winner). Locate the files (user's Downloads or the Codex attachments) before starting. Observed failures to preserve as red tests first: replay ingestion rejects the bare `|rated|` header (and `join` lines); revealed moves are forgotten when a Pokemon switches back in (Kyurem Ice Beam, Perrserker U-turn); revealed items/abilities stay unknown at reveal time (Leftovers, Life Orb, Aftermath, Poison Heal, Rocky Helmet); Taunt, No Retreat, Chilly Reception (`[premajor]`), Supreme Overlord boost and Quark Drive boost lack structured state. Displayed HP, hazards, boosts and active Tera typing tracked correctly in checked examples. Add a broader replay corpus by mechanic over time. Principle: parsing, capture-complete and knowledge-accurate are separate gates; raw-only retention of a required effect must block a "complete knowledge" claim; each unknown needs an explained reason.
2. S01c-2 delivery ledger (retain raw delivered request text per boundary in `env_manager.ts`/`pipeline_integration.ts`; no identity change).
3. S01c-3 publication artifact (new TS/Python modules + `docs/contracts/REQUEST_KNOWLEDGE_PUBLICATION.md`; faithful flag equal with/without).
4. S01c-4 K-fact adapter (new files).
5. S02 original owned roster/loadout before battle effects (no provider exists yet), S03 retention across bench/wait/force/revival/terminal.
6. Families: P01 health/status, P02 moves/forms/stages, P03 items, P04 abilities, L01-L05 lifecycle effects (control effects, counters, copied state), R02 replay attribution (replace species-keyed aggregation; unique carrier; acquired/copied/ambiguous controls).
7. PK-02B-Publish (real TS->Python ordinary/full/compact), then M02 provenance reconciliation (checker currently fails: Prompt 9 contract edits, env_manager.ts, new modules/tests; do NOT edit the manifest/attestation until the final reviewed digest), E01 environment/clean-install reproduction, A01/A02 independent final acceptance by a non-author reviewer who reruns checks.
8. Small cleanup: other tests with unsafe `json.load(sys.stdin)` inline reads (ability_callback.test.ts:112, item_identity.test.ts:870, protocol_contract_validation.test.ts ~169/422/466/691, psych_up.test.ts:200/213, psych_up_validation.test.ts:46/55/70); a worker also noted a possible 3-in-4,054 unattributed snapshot request difference.

## 7. Known issues / lessons
- Incident: a scratch git worktree cleanup emptied the real `sim-core/node_modules`; the user reinstalled. Rule: workers never remove junctions/folders in the main tree; never use junctions to the main `node_modules` without verifying cleanup; no installs without user approval.
- Incident: an orphaned probe (`%TEMP%\d2.cjs`) burned ~90 min CPU and slowed everything; check `Get-Process node,python` for old processes when tests are slow, and stop workers that wait on missing marker files instead of waiting indefinitely.
- Lesson: tests checked internal structure and simulator captures, not real downloaded replay input; the real-replay harness is now mandatory. "Accepted" earlier claims were scoped (simulator captures), not universal.
- Test-process isolation quirk (see section 3). `tsc` shim missing (section 3).
- Self-review by a worker is not acceptance; use fresh-context reviewers and personal reruns.
- The user prefers plain-English explanations when status gets technical, wants things fixed now rather than deferred, and is fine with a single worker + reviewer + lead rerun per step.

## 8. Not authorized
Commits, staging, pushes, PRs, merges, package installs without approval, dataset generation, model training, external replay fetching (use only the user's supplied files), live servers, manifest/attestation edits before the final provenance step.
