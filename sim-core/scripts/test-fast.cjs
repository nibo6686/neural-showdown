const { spawnSync } = require('node:child_process');
const path = require('node:path');
const { files } = require('../test-fast-files.json');

// Bound concurrent files: publication tests launch Python processes on Windows.
const result = spawnSync(process.execPath, ['--test', '--test-concurrency=4', ...files], {
  cwd: path.resolve(__dirname, '..'), stdio: 'inherit', timeout: 170_000,
});
if (result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
