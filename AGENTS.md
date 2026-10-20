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
- Run the slice's focused tests and `tools/test_fast.ps1` before reporting.
  Give potentially hanging commands a timeout. **Don't run the full Node or
  Python suite** unless the brief explicitly asks; Claude runs full-suite
  comparisons during review. Read failing-test output selectively (the failing
  test's lines), not whole logs.
- Build with `node node_modules/typescript/bin/tsc -p tsconfig.json` in
  `sim-core`. Python is `D:\Anaconda\envs\neuralgpu\python.exe`. Keep
  `PYTHONUTF8` and `PYTHONIOENCODING` unset. Keep `core.autocrlf=false`.
- Write a report of at most one page in `docs/roadmap/reports/<slice>.md`.
  No evidence packets, hash receipts or extra planning docs.
- Commit once per slice when its brief says so. Never push, merge, download
  datasets or train unless the brief says so.
