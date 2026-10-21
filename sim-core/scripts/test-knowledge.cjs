const {spawnSync} = require('node:child_process');
const path = require('node:path');
const {files} = require('../test-knowledge-files.json');
const env = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
  !['PYTHONUTF8', 'PYTHONIOENCODING'].includes(key.toUpperCase())));
env.PYTHON ||= process.platform === 'win32' ? 'D:/Anaconda/envs/neuralgpu/python.exe' : 'python3';

const result = spawnSync(process.execPath, ['--test', '--test-concurrency=1', '--test-timeout=300000', ...files], {
  cwd: path.resolve(__dirname, '..'), env, stdio: 'inherit', timeout: 600000,
});
if (result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
