const fs = require('node:fs');
const {spawnSync}=require('node:child_process');
const path = require('node:path');
const root=path.resolve(__dirname, '../../..');
const {createPipelineIntegrationSession} = require(root+'/sim-core/dist/src/pipeline_integration');
const {canonicalActionFromLegalAction} = require(root+'/sim-core/dist/src/canonical_action');
const {projectBeliefState}=require(root+'/sim-core/dist/src/belief_state');
(async () => {
  const s = await createPipelineIntegrationSession({observation_schema_version:'observable-battle-state/v2',battle_id:'v2-review-compat',format:'gen9randombattle',seed:[1,2,3,4]});
  try {
    const actions = Object.fromEntries(['p1','p2'].map(p => {
      const req=s.boundary.perspectives[p].observation.request;
      return [p,canonicalActionFromLegalAction(req,req.legal_actions.available_indices[0])];
    }));
    const r=await s.step(actions);
    fs.writeFileSync('/tmp/v2-review-compat.json',JSON.stringify(r.record_bundles.p1));
  } finally { await s.close(); }
  const py=spawnSync(process.env.PYTHON || 'python3',[path.join(__dirname, 'downgrade.py')],{encoding:'utf8',env:{...process.env,PYTHONPATH:root+'/trainer/src'}});
  process.stdout.write(py.stdout); process.stderr.write(py.stderr);
  if(py.status) throw new Error('Python reproduction failed');
  const b=JSON.parse(fs.readFileSync('/tmp/v2-review-downgraded.json','utf8'));
  try {projectBeliefState({observation:b.input_observation}); console.log('Unexpected TS accept');}
  catch(e){console.log('TS rejection:',e.message);}
  const repaired=JSON.parse(fs.readFileSync('/tmp/v2-review-stale-belief.json','utf8'));
  try {projectBeliefState({observation:repaired.successor_observation,parent:repaired.input_belief}); console.log('Unexpected TS stale-belief accept');}
  catch(e){console.log('TS stale-belief rejection:',e.message);}
})().catch(e=>{console.error(e);process.exitCode=1;});
