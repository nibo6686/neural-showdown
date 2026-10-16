const { spawnSync } = require('node:child_process');
const path = require('node:path');
const { files } = require('../test-fast-files.json');

// node --test keeps file-level parallel execution and its normal isolation.
const result = spawnSync(process.execPath, ['--test', ...files], {
  cwd: path.resolve(__dirname, '..'), stdio: 'inherit', timeout: 170_000,
});
if (result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
