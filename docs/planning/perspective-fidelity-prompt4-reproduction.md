# Prompt 4 smallest saved reproductions

Run from repository root. This Node-to-Python command passes saved JSON bytes to the real production CLI, clears encoding overrides only in the child, preserves explicit interpreter selection and prints status/stdout-byte count to stderr plus the actual publication to stdout. It writes no output dataset/file.

```powershell
$env:PYTHON='D:\Anaconda\envs\neuralgpu\python.exe'
@'
const fs = require('fs'), cp = require('child_process'), path = require('path');
const env = {...process.env, PYTHONPATH: path.resolve('trainer/src')};
for (const key of Object.keys(env)) {
  if (['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase())) delete env[key];
}
const result = cp.spawnSync(env.PYTHON, ['-m', 'neural.pipeline_record'], {
  env, input: fs.readFileSync(process.argv[2]), encoding: 'utf8', timeout: 30000,
});
console.error(JSON.stringify({status: result.status, stdoutBytes: Buffer.byteLength(result.stdout),
  stderr: result.stderr, error: result.error?.message}));
process.stdout.write(result.stdout);
process.exit(result.status ?? 1);
'@ | node - docs/planning/perspective-fidelity-prompt4-weather-reproduction.json
```

Substitute only the final filename to replay `perspective-fidelity-prompt4-terrain-reproduction.json` or `perspective-fidelity-prompt4-pseudo_weather-reproduction.json`. Expected current defective behavior: exit 0, empty stderr from Python, one DATA-001 row; stdout 1327 / 1326 / 1355 bytes respectively. Prefix contradiction is described in the matrix. These are complete real actor bundles, not bare synthetic observations.

The six `*-terminal-full-reproduction.json` / `*-terminal-compact-reproduction.json` files exercise applicable original-to-terminal full/compact forms. Weather/terrain output two rows (2648 bytes); Trick Room four rows (5406 bytes). All currently exit 0. Their attacked terminal successor is validated and referenced by the evidence chain; DATA rows themselves serialize input IDs, not terminal field values.

To rerun the truthfully red expected-rejection tests after building, from `sim-core`:

```powershell
$env:PYTHON='D:\Anaconda\envs\neuralgpu\python.exe'
$env:FIELD_SEMANTIC_RED='1'
node --test --test-isolation=none --test-reporter=spec --test-name-pattern='V01 RED WITNESS' dist/tests/perspective_field_semantics.test.js
```

Current result is exit 1, three failures because expected atomic exit 2/empty stdout instead produces exit 0/nonempty stdout. No characterization rerun or broad suite is necessary for these saved witnesses. Each subprocess has a 30-second timeout; timeouts are errors, never semantic outcomes.
