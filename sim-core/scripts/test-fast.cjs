const path = require('node:path');
const { run } = require('node:test');
const { spec } = require('node:test/reporters');
const { files } = require('../test-fast-files.json');

// Start measured long files early; every listed file still runs exactly once.
// The CLI's glob expansion sorts paths instead of preserving this order.
const longFiles = [
  'tests/durable_jobs.test.cjs', 'dist/tests/perspective_knowledge.test.js',
  'dist/tests/pipeline_episode_stop_repair.test.js', 'dist/tests/pipeline_episode_faithful.test.js',
  'dist/tests/pipeline_integration.test.js', 'dist/tests/bench.test.js',
  'dist/tests/native11_trace.test.js', 'dist/tests/owned_request_moves.test.js',
];
const ordered = [...longFiles.filter(file => files.includes(file)), ...files.filter(file => !longFiles.includes(file))];
const stream = run({
  files: ordered, cwd: path.resolve(__dirname, '..'), concurrency: 6,
  signal: AbortSignal.timeout(170_000),
});
stream.on('test:fail', () => { process.exitCode = 1; });
stream.compose(new spec()).pipe(process.stdout);
