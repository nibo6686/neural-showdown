# macOS reconciliation and simulator-record comparison — 2026-09-25

## Current checkpoint

**PASS:** reconciliation complete; fresh-process repeatability and canonical Windows/macOS equality verified for all six declared scenarios. `faithful_complete_episode:false`.

- Starting HEAD: `3ddc5fc3060e8da287425e4d08a71a2ffd77184a`; five modified review files; no staged or unmerged entries.
- Preserved all local changes in stash `6f4e90700194e95affbfe23a400fbc6a56104cc1` and `artifacts/validation/macos-2026-09-25/original-review.patch` (SHA-256 `968e3f9318e6b67e6585afec1c74e1f4442ef875a11fd47164eb6e71f0140018`). Original `/tmp/neural-stellar-review.patch` matched exactly.
- Base/local/incoming comparison: four documents already identical upstream; upstream manifest retains the entire local review and adds Windows portability/comparison evidence. No unique local edits; stash retained, deliberately not reapplied.
- Fast-forwarded to `117df85247846548fe99ee7e3d60a26d827fc05c`. No merge conflict occurred.
- Coverage checker passes incoming28-file digest `14dff114f66482bbdf5cb10bd0bc3579f339da2af878395b7b74c2f7913f71b0`. Reference SHA-256 matches `d983dbb2d83c944271590c2dd5c28dc693968ec1813aac9af1edb1ca4125e1d4`. No reference or attestation changes.
- Generator requires exact old HEAD, even though source additions are now committed. Use an isolated detached checkout at the original base with the exact incoming tree applied; verify its tracked content equals incoming. This preserves truthful base-plus-changes provenance without editing the hashed generator or rolling back the main checkout.
- Selected Python `/Library/Developer/CommandLineTools/usr/bin/python3` (3.9.6); Node v24.21.0, npm11.19.0. Existing npm dependencies available; no installation needed; build/checks passed.


## Commands and results

Artifacts below are under `artifacts/validation/macos-2026-09-25/`.

1. `git stash push -m 'macOS review preserved before Windows integration 2026-09-25'`; `git merge --ff-only 117df85`: passed. Sandbox first blocked Git metadata writes; authorized retry succeeded. No stash pop or duplicate patch application.
2. `npm run build --prefix sim-core`: passed (`build.log`). Existing installed dependencies suffice; lockfile unchanged.
3. `git worktree add --detach /tmp/neural-macos-comparison-20260925 3ddc5fc3060e8da287425e4d08a71a2ffd77184a`; apply `git diff --binary 3ddc5fc 117df85` there. Compared every incoming tracked file byte-for-byte: zero mismatches. Isolated checkout uses existing main `sim-core/node_modules` by symlink and its own freshly built output; `npm run build --prefix /tmp/neural-macos-comparison-20260925/sim-core` passed (`isolated-build.log`). No generator modification, Git spoofing, source normalization change or attestation update.
4. Twice, in separate Node processes:
   `PYTHON=/Library/Developer/CommandLineTools/usr/bin/python3 node /tmp/neural-macos-comparison-20260925/sim-core/scripts/simulator-record-comparison.cjs generate --patch /tmp/neural-stellar-review.patch --output /Users/nbolger/Desktop/neural-showdown/artifacts/validation/macos-2026-09-25/macos-runN.json` (N=1,2). Both exit0; generator checks coverage before scenarios. `generate1.log` / `generate2.log` retain summaries.
5. `node sim-core/scripts/simulator-record-comparison.cjs compare --reference artifacts/validation/macos-2026-09-25/macos-run1.json --candidate artifacts/validation/macos-2026-09-25/macos-run2.json`: exit0; `repeatability-report.json`, no differences. Both bundle SHA-256 values: `708b7d1e2d4df8dd7a7193790d11038cc3866c8c5763b8890f853d5b4aab8aa8`.
6. Same compare command with reference `tests/fixtures/simulator_record_comparison_windows_v1.json` and candidate run1: exit0; `windows-comparison-report.json`, `equal_portable_results:true`, zero actionable differences. All28 per-file source hashes match too (`source-verification.json`).

Scenarios: joint transition, one-sided forced switch, natural Arena Trap rejection/recovery, terminal restoration, Unicode publication and55-transition bounded episode. Normalization remains the declared protocol timestamp/line-ending policy. Neither reference output nor coverage attestation was edited.

Nine declared environment differences remain visible at `/environment/{architecture,node_version,npm_version,os_release,platform,python_command_from_node}` and `/environment/python/{executable,prefix,version}`. Windows x64/Python3.11.14/Node24.15.0 contrasts with macOS arm64/Python3.9.6/Node24.21.0. This proves equivalent canonical results for these scenarios, not identical raw environment bundles or universal platform fidelity.

## Final state / next action

Main HEAD remains117df85; no unresolved Git entries, no tracked source modifications. Only this checkpoint and new validation artifacts are added. Recovery stash and original patch retained. The isolated comparison worktree remains at `/tmp/neural-macos-comparison-20260925` for reproduction. Independent read-only reviewer requested gpt-5.6-terra/high; effective settings unavailable; no reviewer edits.

**Single next task:** choose and commit the repository-owned Python dependency/lock and supported-runtime policy, then recreate a clean simulator-validation environment and rerun the validator. ENV-001 clean-environment proof remains open. This comparison does not expand lifecycle acceptance or permit faithful complete-episode publication.
