# Prompt 16 (S01c-1) report: preserve a rejected-choice request across snapshot restore

Status: candidate for lead review. Round 1 was fully run. The correction round (below) is edited but NOT built or run, because the lead paused node-dependent work after sim-core/node_modules was found emptied. Nothing staged or committed; no installs.

## Round 1 (verified)
- `sim-core/src/env_manager.ts`: conditional sibling key `__neural_active_request_overrides` (`active-request-overrides/v1`), emitted by `serializeBattle` for a live battle only when a side's live `activeRequest` differs from the one `Battle.fromJSON` regenerates by an engine-legal edit. `resetFromSerialized` validates before `destroyBattle()`, rejects the key on ended snapshots, applies it after `Battle.fromJSON` and before the re-emit loop. Typed `ActiveRequestOverrideValidationError`.
- Legal edits only: `maybeTrapped` removed with `trapped:true` added; a move row gaining `disabled:true` with a string `disabledSource`. Everything else (extra keys, wrong side, wrong type, unknown edit, no-op, ended battle) is a typed error.
- New `sim-core/tests/active_request_restore.test.ts`: red first (8 of 10 failed pre-change with real divergences), 10 of 10 green after the change.
- Byte identity: 45 pins (3 seeds x v1/v2 pipeline sessions with joint, forced-switch and terminal boundaries; 19 witness scenarios including revival and terminal, restored and re-serialized) are byte-identical pre/post (`prompt16-pins-pre.json` vs `-post.json`). The pre-change run came from a copy of the original dist.
- Wider runs: core files 122/125 (3 `revival.test` failures also fail on the pre-change dist); episode focused 70/71 (the `segment-start.json` CRLF hash failure, unrelated); knowledge files 129/129 when run per file; Python 120 OK plus field-semantics 7 OK; contract checker and `git diff --check` exit 0. Both failures above are being triaged by the lead and were not touched.
- Coverage checker exits 1 with a local-source digest change. It already failed pre-change (manifest 8879baab, pre-change tree 8424f64d, now 14a5d30f). The manifest and attestation were not edited.

## Correction round (edited, UNVERIFIED: not built, not run)
1. Silent-drop observability: new exported `activeRequestOverrideDiagnostics` (`dropped` counter, optional `onDrop` hook). `withActiveRequestOverrides` keeps the byte-preserving fallback but increments the counter and calls the hook when an unexplained or illegal difference is not carried. Inert when unused. New test stubs an unexplained difference (`rqid += 7` on the live request) and asserts the bytes equal `battle.toJSON()`, no key, counter plus one, hook fired. Limitation: a dropped difference still means the restored branch has the regenerated request, as before this slice.
2. Tighter validation: `validateActiveRequestOverride` now takes the regenerated side. A trap edit requires the regenerated active Pokemon's `trapped` to be truthy. A move edit requires `getMoves(getLockedMove(), false)` to report that move disabled. New negative tests: forged `trapped:true` on a maybe-trapped but not trapped Pokemon (Pidgeot vs Dugtrio Arena Trap base), and forged `disabled:true` on a normal move (Rest in the Imprison base).
3. Test gaps: the name-based base routing is replaced by an explicit base name per case (`trap`, `imprison`, `arena`); new positive test with both p1 (trapped) and p2 (hidden-disabled) mutated in one snapshot; no-key assertions for a forced switch with a waiting side, revival selection and doubles; the ended-rejection test uses otherwise-valid input and asserts the "live snapshots" reason.

## What must be checked on rerun
- `npm run build` for type errors in the new code (`Battle['sides'][number]` type, `getMoves` typing).
- The Arena base assumes `maybeTrapped:true` with `trapped` falsy for Pidgeot; the test asserts the first half. The hidden-disabled check assumes `getMoves(lockedMove, false)` marks the Imprisoned move disabled in the regenerated battle; the existing positive disabled tests would fail if not.
- The both-owners test assumes `step({p1:'switch 2'})` then `step({p2:'move 2'})` leaves both rejections live, and that `LocalBattleEnv.getRequest(player)` exists (it appears at line ~1022 of env_manager.ts, not confirmed to be on that class).
- The doubles test tolerates a refusing normalizer by catching the restore error.
- Then rerun: own suite, `prompt16-corpus.cjs` against `pins-pre.json`, and the core, episode and knowledge sets. `env_manager.ts` was converted back to CRLF after one `sed -i` stripped it; the diff stat should show about +153/-2.

## Risks
CPU cost of one extra `Battle.fromJSON` per live serialization; new fingerprints for mutated-state snapshots (by design); the restored legal set changes by design; restore re-emits stay `restore_reemit`; self-review only, no independent reviewer used by me.
