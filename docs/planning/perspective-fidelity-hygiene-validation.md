# Validation
- Build: `node node_modules/typescript/bin/tsc -p tsconfig.json` in sim-core, exit 0 (one run reported a transient missing pokemon-showdown during a concurrent change; rerun clean).
- Env: PYTHON=D:\Anaconda\envs\neuralgpu\python.exe, PYTHONPATH=../trainer/src, PYTHONUTF8 and PYTHONIOENCODING unset.
- `node --test --test-isolation=none dist/tests/revival.test.js`: before fixture change 10 pass / 1 fail (Imposter); after, 11 pass / 0 fail.
- Random-battle ability check: 300 seeds, 1800 sets, 0 empty abilities.
- Faithful: `--test-name-pattern="saved win tie and bound" dist/tests/pipeline_episode_faithful.test.js` passes (sha assertion at module load).
- git ls-files --eol: segment-start i/lf w/lf attr/-text; predecessor i/none w/none attr/-text.
- Not run: identity-sensitive wider suites (no production code changed).
