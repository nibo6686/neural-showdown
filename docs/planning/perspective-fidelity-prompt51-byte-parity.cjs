const path = require('node:path'), fs = require('node:fs'), crypto = require('node:crypto');
const root = '/private/tmp/neural-showdown-native11-prompt38';
const evidence = '/private/tmp/neural-prompt51';
if (!process.argv[2]) {
  const {spawnSync} = require('node:child_process');
  const values = [];
  for (const mode of ['before', 'candidate']) {
    const r = spawnSync(process.execPath, [__filename, mode], {encoding:'utf8', timeout:150000, env:process.env});
    if (r.status !== 0) throw new Error(mode + ': ' + r.stderr);
    values.push(r.stdout);
  }
  require('node:assert/strict').equal(values[0], values[1]);
  console.log('P51_BYTE_PARITY ' + JSON.stringify({fresh_processes:2, source:'frozen pre-Prompt51 modules versus candidate',
    clock:'fixed presentation clock for literal timestamp parity; no identity authority', creation_plus_two_held_switches:true,
    boundaries_bundles_snapshots_literal_json_equal:true, bytes:Buffer.byteLength(values[0]), sha256:crypto.createHash('sha256').update(values[0]).digest('hex')}));
  process.exit(0);
}
Date.now = () => 1791880000000;
if (process.argv[2] === 'before') {
  const Module = require('node:module');
  const ts = require(root + '/sim-core/node_modules/typescript');
  const sources = new Set(['env_manager']);
  const load = Module._extensions['.js'];
  Module._extensions['.js'] = function(module, file) {
    const name = path.basename(file, '.js');
    if (path.dirname(file) === root + '/sim-core/dist/src' && sources.has(name)) {
      const raw = fs.readFileSync(evidence + '/' + name + '.ts.before','utf8');
      const code = ts.transpileModule(raw,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText;
      return module._compile(code,file);
    }
    return load(module,file);
  };
}
const {PipelineIntegrationSession} = require(root + '/sim-core/dist/src/pipeline_integration');
const {canonicalActionFromLegalAction} = require(root + '/sim-core/dist/src/canonical_action');
(async () => {
  const s = await PipelineIntegrationSession.create({battle_id:'P51-byte-parity', format:'gen9randombattle',seed:[1,2,3,4],knowledge_recipients:{p1:{},p2:{}}});
  try {
    const boundaries = [s.boundary], snapshots = [s.snapshot], steps = [];
    for (let n=0;n<2;n++) {
      const choices = {};
      for(const owner of ['p1','p2']) {
        const request=s.environment.getRequest(owner);
        const i=request.legal_actions.available_indices.find(i=>request.legal_actions.actions[i]?.choice==='switch 2');
        choices[owner]=canonicalActionFromLegalAction(request,i);
      }
      steps.push(await s.step(choices)); boundaries.push(s.boundary); snapshots.push(s.snapshot);
    }
    process.stdout.write(JSON.stringify({boundaries,snapshots,steps}));
  } finally {await s.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
