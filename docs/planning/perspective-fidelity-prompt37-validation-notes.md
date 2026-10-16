# Prompt37 validation evidence

Final frozen candidate: build plus four new exact tests and two affected existing controls passed. Commands, process exit codes, durations and actual 180-second process-group watchdogs are in `perspective-fidelity-prompt37-commands.json`. Child bootstrap subprocesses additionally use 20-second timeouts. Workloads were sequential with visible output; all task-launched processes completed.

Node 24.21.0 used the absolute installed Node path. Python 3.9.6 used `.venv-simulator/bin/python` and absolute `trainer/src` PYTHONPATH; PYTHONUTF8, PYTHONIOENCODING and REPORT_/PROMPT environment overrides were removed. The runner is `/private/tmp/neural-prompt37-20261012/run.py`.

| Exact control | Result | Proof |
|---|---|---|
| TS P37 full assets direct mutations and integrity | PASS | Both assets, 101/108 fixtures, 27 direct coherently mutated invariant controls, immutable snapshots, missing/altered loaders, historical full validator |
| TS P37 owned bootstrap and sticky failure fresh processes | PASS | Actual owned reentry, foreign/copied/context/arbitrary-input rejection, sticky failure, zero Showdown loads |
| Python test_full_assets_mutations_and_integrity | PASS | Same 27 invariant classifications and fixture counts, immutable snapshots, loaders and historical full validator |
| Python test_owned_bootstrap_threads_and_sticky_failure | PASS | Actual owner-thread reentry, competing-thread rejection, other profile/public inspection rejection and sticky failure |
| TS P36 bounded saved prefix and historical parity | PASS | Hash-verified local prefix; source index44/routed34 Natural Cure, silent retained, historical prefix parity |
| Python test_historical_publication_and_replay_rejection | PASS | Literal historical output unchanged; replay publication rejected, exit2, empty stdout |

Each fixture and every positive/negative control is checked against its fixed selected grammar. Direct mutations exercise structural/cross-field/record-reason checks independently of code pins, so recomputing the JSON hash cannot conceal them. No target simulator, team generation, replay download, model, long witness or suite was executed.

Corrections before final freeze: initial TypeScript compilation rejected unknown context types; exact owned references fixed that. The first asset test exposed the bare Court Change alias classification mismatch; its existing quarantine was made consistent, with an explicit negative. Independent review then required strict claim metadata. Necessary correction builds are recorded; historical logs were never touched. The new full-assets log contains the final pass; the command ledger retains earlier exits, including the initial failure. No unchanged timed-out checks were repeated.

Native11 emitter/audience, real generated behavior, target TS/Python publication and positive fidelity are **UNEXECUTED**. Candidate grammar proof cannot substitute for those LIVE gates. Historical B1/B2, context, snapshot and K-source evidence is reused only for unchanged inputs, without carrying completeness forward.
