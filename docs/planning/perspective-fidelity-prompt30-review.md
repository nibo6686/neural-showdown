# Prompt30 integration testing gap analysis

## Summary

Planning audit complete; no tests, builds, imports, installs or simulators executed. Parent applied review-plan-tests to the migration data flow and an independent Sol/high read-only reviewer (Gallade; effective telemetry unavailable) challenged the new plan/matrix. One writer; no duplicate research or downstream delegation. Candidate is acceptable for lead plan review, subject to A1–A3 API decisions, not execution authority.

## Critical gaps identified and fixed in the plan

1. **P1 — activation gate dependency cycle.** PR-03–05 originally required actual target producer/count/emitter results before PR-06 could install/activate the target. The plan now makes PR-06 depend only on PRE policy/assets/fixture and old-caller acceptance. It owns LIVE target G04–14; PR-07 owns actual timing/update checks and PR-11 blocks promotion on all required LIVE evidence. A reserved/unadopted-profile rejection cannot count as the intended target semantic rejection. Prepared support is never called a fresh target runtime pass. Failing activation confirmations return a precise owning-boundary correction, not an expanded lock-bump task.
2. **P1 — runtime profile propagation lacked actual producer ownership.** InstalledNativeProfile is now an immutable internally checked descriptor held by manager/session and verified by LocalBattleEnv, then passed through ManagedPlayer→PlayerStateExtractor and nested semantic readers. Env/server writes are explicit. Actual old RPC/session PRE canaries and target RPC/session LIVE gates complement interleaved historical/current-reader checks. Caller version/profile options and global swapping are prohibited. Bound ability/field/boost/lifecycle helpers and belief validation are listed; unlisted non-equivalent dependencies require a scope decision.
3. **P2 — managed live-snapshot handle lifetime was incomplete.** G06 now proves rejected preflight retains the same handle for retry; success consumes it, fresh output works, replay/reset/close/restart reject before choices; post-write failure revokes stale handles without claiming rollback of the live battle. Ordinary JSON copies address a legitimate server-held entry; they do not mint a new snapshot or B2 authority.

Independent reviewer confirmed all three closed after inspecting corrected plan/matrix/first prompt: no remaining material integration/test gap found in the bounded corrections. A1–A3 remain lead approvals.

## Additional source-grounded corrections

- Belief-fork helper samples Teams.generate and constructs a donor Battle; it does not call fromJSON. Target rejection occurs before that helper and manager ID/map mutation. Early fromJSON calls are terminal submitted-switch source validation and active-request override regeneration; target restore admission precedes both.
- Managed seeded RPC advances an existing live battle rather than reconstructing one. It remains a separate bounded API, with no fabricated B2 enrollment.
- Target producer/TS/Python faithful-claim validators require an explicit target eligibility gate; old digest or structural complete-capture alone cannot promote target fidelity.
- Public API restrictions and replay publication-mode ambiguity are explicitly A1–A3, not hidden implementation details or a caller-trusted snapshot certificate.

## Test checklist for implementation

- [ ] PRE local policy/fixture checks labeled; unchanged actual old callers/IDs preserved.
- [ ] LIVE target caller path, including RPC/session and every semantic helper, verified after activation.
- [ ] Actual reconstruction/generation/disposal/write counters prove target rejection before side effects.
- [ ] Coherently resealed wire negatives reach the intended semantic error; reference attacks cannot acquire authority by hashing.
- [ ] Generated target originals/order compared with literal independent slots; constructed mechanics labeled separately.
- [ ] Forced/Revival post-prepare rollback proves both-owner committed preservation and revocation before cleanup.
- [ ] Raw source→routing→extractor→bundle→TS/Python CLI publication validates exact native/replay policy and no-output failures.
- [ ] Target fidelity/K-source guard applies at producer and consumer, not only a helper predicate.
- [ ] Old artifacts/readers/attestations remain unchanged; rollback never crosses engine snapshots.
- [ ] Exact positive selectors, sequential workloads, real deadlines; broader validation separately justified/authorized.

The [test matrix](perspective-fidelity-prompt30-tests.md) assigns locations, caller paths, positive/negative controls, reuse/fresh distinctions and evidence owners. No evaluation corpus or model workload is necessary.
