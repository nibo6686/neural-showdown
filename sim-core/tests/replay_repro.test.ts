import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(__dirname, '../../..');
const {reproduceReplay} = require(path.join(root, 'tools/replay_repro/index.cjs'));
const directory = path.join(root, 'sim-core/tests/fixtures/replay-repro');
for (const name of fs.readdirSync(directory).filter(name => name.endsWith('.json'))) {
  test('P0.4 replay exact reproduction: ' + name, {timeout: 30000}, async () => {
    const replay = JSON.parse(fs.readFileSync(path.join(directory, name), 'utf8'));
    const result = await reproduceReplay(replay);
    assert.equal(result.full_match, true, JSON.stringify(result));
    assert.ok(result.matched_prefix_length > 5);
    if (name.includes('2699618521')) assert.equal(result.ending, 'forfeit');
    const changed = {...replay, log: replay.log.replace('|turn|1', '|turn|999')};
    const mismatch = await reproduceReplay(changed);
    assert.equal(mismatch.full_match, false);
    assert.equal(mismatch.divergence_turn, 999);
  });
}
test('P0.4 replay rejects missing evidence and a foreign engine', async () => {
  const replay = JSON.parse(fs.readFileSync(path.join(directory, 'gen9randombattle-2699618521.json'), 'utf8'));
  await assert.rejects(reproduceReplay({...replay, inputlog: ''}), /version mismatch/);
  await assert.rejects(reproduceReplay({...replay, log: '|error|bad'}), /public battle log/);
  await assert.rejects(reproduceReplay({...replay, inputlog: replay.inputlog.replace('b8f23c99', '739a5e1f')}), /version mismatch/);
  await assert.rejects(reproduceReplay({...replay, inputlog: replay.inputlog + '\n>eval process.exit(99)'}), /Unsupported replay input command/);
});
