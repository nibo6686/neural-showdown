# Development handoff to Windows — 2026-10-16

## Resume point

**Implementation accepted through Prompt60. Prompt61 design is approved. Prompt62 is the next authorized implementation and has not started.** This transfer does not change any acceptance, fidelity, training or publication decision.

There are two deliberately separate source trees:

| Tree | Purpose | Engine |
| --- | --- | --- |
| This Git repository | Historical/original checkout, work through migration preparation, governing plans and evidence | npm Showdown 0.11.10 |
| Restored candidate in a separate directory | Accepted isolated implementation through Prompt60; execute Prompt62 here | npm Showdown 0.11.11 |

Do not overlay the candidate onto the repository, install 0.11.11 in the original tree, or execute a target assignment against the original sources. The candidate's old macOS path and temporary symlink are historical aliases, not required Windows paths.

## What has been delivered

- Original-owner team retention, birth/restored actor authority and committed request delivery.
- Indexed direct-switch event association, owner-addressed immutable knowledge and atomic failure/restore behavior.
- Owned health, item/ability identifiers, ordinary request-option PP and the real episode decision caller.
- Finite original loadout/details/stat interpretation (Prompt59) and current request-declared stats/details/cosmetics (Prompt60).
- Prompt61's reviewed move-identity, PP-retention and flag design, ready for Prompt62 implementation.

All acceptance is bounded. Knowledge remains incomplete; target positive fidelity and default promotion remain disabled/unapproved. Current declared stats are not effective boosted/transformed stats. Original partial EV/IV tuples and random-gender-dependent details remain explicitly blocking. Declaration-less overlay runtime proof and positive rejected-choice recovery remain unsupported. Copied/replacement move incarnations remain excluded from Prompt62; ordinary/base continuity is the approved next scope.

## Transfer contents and provenance

The Git bundle created for this handoff contains repository history plus this local transfer commit. It is not pushed. Clone the bundle or copy an exact clone containing the handoff commit; copying only the old remote branch loses the recent work.

`artifacts/handoff/2026-10-16/` contains:

- `native11-source.tar.gz`: 517 exact source/config/test/contract files reconstructed from the accepted Prompt54 source base and accepted Prompt57/59/60 changes. SHA-256 `d4b6d691896721e0847399bd8b0b81dc6e244507406f66d8cc26916199c66c82`.
- `native11-source-manifest.json`: individual hashes, engine provenance, installed-source pins and 12 separately labeled existing fixture/lock inputs from this repository.
- `restore_native11.py`: checks archive/members, refuses to overwrite an existing nonempty destination, restores exact bytes, and verifies source and optional installed Showdown hashes.
- `run_bounded.py`: runs one explicitly selected command with a process-tree deadline on Windows or Unix. Its Windows branch has not been executed on this macOS host.

Source retention preserves bytes; old process objects, private handles and session authority do not survive. Create fresh sessions. Supplemental fixtures/lock files are not new runtime acceptance. Existing historical absolute paths in evidence are retained to preserve hashes; map them to the new roots rather than editing or resealing historical records. Reports/recorded scripts may mention helpers formerly under `/private/tmp`; those scratch tools are not runtime dependencies or an instruction to rerun the old matrix.

Excluded from the commit/bundle's new changes: generated egg-info edits, root user-owned AGENTS.md, environments, node_modules, compiled outputs, downloaded replay corpus, large native envelope dumps, and unrelated diagnostic payloads. The candidate archive retains its existing scoped execution-guidance file as part of the verified source snapshot. The uncommitted local exclusions remain on the old machine. This is a private development handoff containing historical machine paths/evidence; public publication still needs separate review and authorization.

## Packaging checks

Archive members and hashes were verified, and the restore tool reconstructed all 517 accepted files plus 12 labeled supplemental inputs into a fresh temporary directory on macOS. No application tests or builds ran. New transfer documentation/tool whitespace checks pass. The full historical snapshot still reports 470 whitespace diagnostics across 42 paths, chiefly retained patch evidence plus an existing test/proposal; those exact bytes were preserved rather than changing hash-bound source/evidence during transfer. This is not a clean feature-merge or Windows execution claim.

## Windows restore

Use a short local path, for example `C:\dev`, with Git, Node and Python installed. Avoid copying old environments or dependency directories. Preserve line endings; historical raw hashes must not be silently normalized.

From the folder containing the copied bundle, in PowerShell:

```powershell
git -c core.autocrlf=false clone -b codex/machine-handoff-2026-10-16 .\neural-showdown.bundle C:\dev\neural-showdown
Set-Location C:\dev\neural-showdown
git config core.autocrlf false
git status --short
git log -1 --oneline
py -3 .\artifacts\handoff\2026-10-16\restore_native11.py --destination C:\dev\neural-native11
```

No old `/Users/...` or `/private/tmp/...` directory needs to exist. The archive restores exact target bytes independently of Git checkout line endings. If a supplemental source hash differs, fix checkout conversion/configuration; do not change expected hashes to accept it.

Record `node --version`, `npm --version`, `py -0p`, OS/architecture and Python version. Recorded target evidence used Node24.21.0/npm11.19.0 and Python3.9.6 on macOS. Windows must establish its own applicable setup evidence. Prefer matching Node/npm versions; report a different Python/host configuration rather than claiming byte-identical environment provenance.

After environment setup is authorized by the resume prompt, install only the candidate's locked dependencies:

```powershell
Set-Location C:\dev\neural-native11\sim-core
npm.cmd ci --ignore-scripts --no-audit --no-fund
py -3 C:\dev\neural-showdown\artifacts\handoff\2026-10-16\restore_native11.py --destination C:\dev\neural-native11 --verify-only --verify-runtime
Set-Location C:\dev\neural-native11
py -3 -m venv .venv-simulator
.\.venv-simulator\Scripts\python.exe -m pip install --require-hashes -r .\trainer\requirements\simulator-record.txt
$env:PYTHON = (Resolve-Path .\.venv-simulator\Scripts\python.exe).Path
$env:PYTHONPATH = (Resolve-Path .\trainer\src).Path
Remove-Item Env:PYTHONIOENCODING, Env:PYTHONUTF8, Env:NODE_OPTIONS -ErrorAction SilentlyContinue
```

Use this explicit Python executable for Python-dependent checks; Python's `-m neural.pipeline_record` imports from PYTHONPATH. No trainer-live/PyTorch/model dependencies are required for the next task. If hashed lock installation fails, report exact platform/version/package diagnostics; do not upgrade packages or regenerate locks as part of the handoff.

## First bounded host check, then Prompt62

The resume prompt authorizes one build and one exact existing consumer canary after hashes and installed dependencies match, sequentially with 180-second process-tree deadlines. It does not authorize the full suite or old requirement-mode failures. Inspect the canary's name and confirm exactly one selected test.

```powershell
$tools = 'C:\dev\neural-showdown\artifacts\handoff\2026-10-16'
& $env:PYTHON "$tools\run_bounded.py" --cwd C:\dev\neural-native11\sim-core --seconds 180 -- node node_modules/typescript/bin/tsc -p tsconfig.json
& $env:PYTHON "$tools\run_bounded.py" --cwd C:\dev\neural-native11 --seconds 180 -- node --test --test-reporter=spec '--test-name-pattern=^P57 actual runner gives both owners immutable incomplete inputs and uses a changed owned ability to order actions$' sim-core/dist/tests/pipeline_owned_decision_input.test.js
```

The canary is new Windows host evidence, not a replacement for historical acceptance. Stop after a concrete host failure; one hypothesis-driven diagnostic rerun is allowed. Do not use broad retries, regenerate battles or change source/identity/fixtures just to get setup green. After passing, proceed to the already approved Prompt62 assignment using the restored candidate path. Reuse the host build if unchanged; do not build twice solely because the task name changed.

## Governing documents and authority

Read in this order:

1. This handoff and `RESUME-PROMPT.md` beside it.
2. `docs/planning/perspective-fidelity-prompt58-reconciliation.md`: 61-property remaining-work roadmap; full knowledge and an optional first experiment are separate finish lines.
3. Prompt60 report/lead review and Prompt61 design/lead review in `docs/planning/`.
4. `docs/planning/perspective-fidelity-prompt62-first-prompt.md`: exact next write set, constraints and focused proof. Substitute the restored candidate root for its historical macOS root; no other scope change.
5. `docs/requirements/spec.md`, `docs/contracts/PERSPECTIVE_KNOWLEDGE.md` and property/profile inventories when the relevant semantics require them.

The restored candidate's own planning tree is the older accepted-base snapshot. Use this repository's current planning documents to govern it. Personal project-lead/implement-plan skills may not exist on Windows; this handoff and the explicit assignment contain the needed rules. Do not block on installing personal skills or reopen approved design decisions for that reason.

Act as project lead; implementations return for scoped lead acceptance. Keep original/current/public/request facts separate; facts unavailable legitimately remain unknown, missing adapters remain incomplete. Preserve one workload at a time, exact selectors, real timeouts, unchanged evidence reuse and all recorded failures. Long useful coding is allowed; repeated testing/coordination must not dominate. No generic rules engine, new identity algorithm, broad fixture migration or unrelated repair to speed a test.

This user request authorizes a local transfer commit and bundle. It does not authorize push, merge, public uploads, new datasets, training, live use, target default promotion or positive fidelity. Prompt62 implementation and its exact focused checks are already authorized; later tasks still require lead decisions.
