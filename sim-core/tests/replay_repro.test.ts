import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(__dirname, '../../..');
const {reproduceReplay,admitReplay,main} = require(path.join(root, 'tools/replay_repro/index.cjs'));
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
test('replay rejects missing evidence and forbidden commands; foreign provenance can reproduce', async () => {
  const replay = JSON.parse(fs.readFileSync(path.join(directory, 'gen9randombattle-2699618521.json'), 'utf8'));
  await assert.rejects(reproduceReplay({...replay, inputlog: ''}), /version mismatch/);
  assert.equal((await admitReplay({...replay,inputlog:17})).reproduction,'failed');
  await assert.rejects(reproduceReplay({...replay,inputlog:replay.inputlog+'\n>version'}),/version mismatch/);
  await assert.rejects(reproduceReplay({...replay, log: '|error|bad'}), /public battle log/);
  const foreign = await admitReplay({...replay, inputlog: replay.inputlog.replace('b8f23c99', '739a5e1f')});
  assert.equal(foreign.admitted, true);
  assert.ok(foreign.server_commit.startsWith('739a5e1f'));
  const custom=await admitReplay({...replay,inputlog:replay.inputlog.replace('"formatid":"gen9randombattle"','"formatid":"gen9randombattle@@@max team size = 6"')},{extract:true,diff:true});
  assert.equal(custom.reproduction,'exact');assert.equal(custom.reason,'custom-rules');
  assert.equal(custom.extraction,'not-run');assert.equal(custom.diff_mismatch_count,null);

  await assert.rejects(reproduceReplay({...replay,inputlog:replay.inputlog+'\n>version '+foreign.server_commit}), /version mismatch/);
  await assert.rejects(reproduceReplay({...replay, inputlog: replay.inputlog + '\n>eval process.exit(99)'}), /Unsupported replay input command/);
});


test('replay batch extraction records divergence and forbidden input, then continues', {timeout:30000}, async()=>{
  const replay=JSON.parse(fs.readFileSync(path.join(directory,'gen9randombattle-2699618521.json'),'utf8'));
  const os=await import('node:os');
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'p06a-admission-'));
  try {
    const replays=[{...replay,id:'gen9randombattle-a-diverged',log:replay.log.replace('|turn|1','|turn|999')},
      {...replay,id:'gen9randombattle-b-forbidden',inputlog:replay.inputlog+'\n>eval process.exit(99)'},
      {...replay,id:'gen9randombattle-c-exact',inputlog:replay.inputlog.replace('b8f23c99','739a5e1f')}];
    for(const row of replays)fs.writeFileSync(path.join(temp,row.id+'.json'),JSON.stringify(row));
    for(const prefix of ['rom-','impulse-','smogtours-'])assert.equal((await admitReplay({...replay,id:prefix+replay.id})).reason,'side-server');
    const manifest=path.join(temp,'admission.jsonl');
    const summary=await main(temp,true,true,{manifest,quiet:true});
    const rows=fs.readFileSync(manifest,'utf8').trim().split('\n').map(line=>JSON.parse(line));
    assert.deepEqual(rows.map(row=>row.reason??'admitted'),['reproduction-diverged','failed','admitted']);
    assert.equal(rows[1].reproduction,'failed');
    assert.match(rows[1].error,/Unsupported replay input command/);
    assert.equal(rows[2].extraction,'clean'); assert.equal(rows[2].diff_mismatch_count,0);
    assert.equal(summary.admitted,1);
    const {execFile}=await import('node:child_process'), {promisify}=await import('node:util');
    const output=await promisify(execFile)(process.execPath,[path.join(root,'tools/replay_repro/census.cjs'),temp,'--workers=2'],{timeout:20000});
    const census=JSON.parse(output.stdout.trim());
    assert.equal(census.main_server_replays,3);assert.equal(census.admitted,1);
    assert.equal(census.exclusions['reproduction-diverged'],1);assert.equal(census.exclusions.failed,1);
    assert.equal(census.diff_mismatches,0);assert.ok(census.checks>0);

  } finally {fs.rmSync(temp,{recursive:true,force:true});}
});
