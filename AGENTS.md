# Agent instructions

The plan of record is `docs/roadmap/LONG-TERM-PLAN.md`. Work one slice at a
time from a brief in `docs/roadmap/briefs/`. Read the plan's §1 before
starting.

- Stay inside the slice's goal and files. Put issues found outside it in the
  report as follow-ups; don't fix them now.
- Correctness rules are non-negotiable: unknown is never a default, and
  omitted ≠ false ≠ zero. No future or suffix information at a decision
  cursor, no foreign-owner private data, canonical legal actions only, and
  never weaken a validator to make a test pass.
- Do the slice yourself in this session. Don't delegate to sub-agents, act
  as a project lead or coordinator, or apply model-routing or
  automatic-delegation skills (`model-routing-advisor`, `project-lead`, and
  similar), even if they say they apply to every task. Use the session's
  default model.
- **Lean verification.** Iterate with the slice's focused tests only. Run
  `tools/test_fast.ps1` **once**, just before committing, and again only if
  code changed after that run. Don't rerun it to re-measure timing, and don't
  run pilots or measurement jobs unless the brief asks. Proof tests for
  adopted rows (positive and negative) and the leakage-invariance tests are
  deliverables, never deferred. Give potentially hanging commands a timeout.
  **Don't run the full Node or Python suite** unless the brief explicitly
  asks. Read failing-test output selectively (the failing test's lines), not
  whole logs.
- **Stacking.** When the next brief is ready, you may start it on top of a
  slice that is still under review. Review fixes for the earlier slice come
  first, in their own small commit.
- No known timeouts. A test that is known to hang or exceed its time limit
  must either be skipped in code with a stated reason (long tests opt in via
  `NEURAL_LONG_TESTS=1`), or be fixed in the current slice. Never leave a
  suite to run into a timeout it is known to hit.
- No routine corpus runs. Don't run the replay corpus (born/K census or
  differential over many battles) unless the brief explicitly asks for it.
  The curated real-replay fixtures in the fast gate are the per-slice check.
  Any corpus run a brief does ask for runs in the background under the R1
  supervisor from an immutable worktree, and must never block the slice.
- Build with `node node_modules/typescript/bin/tsc -p tsconfig.json` in
  `sim-core`. Python is `D:\Anaconda\envs\neuralgpu\python.exe`. Keep
  `PYTHONUTF8` and `PYTHONIOENCODING` unset. Keep `core.autocrlf=false`.
- Write a report of at most one page in `docs/roadmap/reports/<slice>.md`.
  No evidence packets, hash receipts or extra planning docs.
- Commit once per slice when its brief says so. Never push, merge, download
  datasets or train unless the brief says so.
