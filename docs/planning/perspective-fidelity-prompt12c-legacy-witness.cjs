const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {createPipelineIntegrationSession,validatePipelineLinkedRecordBundle} = require('../../sim-core/dist/src/pipeline_integration.js');
const {canonicalActionFromLegalAction} = require('../../sim-core/dist/src/canonical_action.js');
const root = path.resolve(__dirname,'../..');
const env = Object.fromEntries(Object.entries(process.env).filter(([key])=>!['PYTHONUTF8','PYTHONIOENCODING'].includes(key.toUpperCase())));
env.PYTHONPATH=path.join(root,'trainer/src');
const code = ['import sys,json','from neural.pipeline_json_wire import load_json','from neural.pipeline_record import validate_pipeline_bundle','b=load_json(sys.stdin)','r=validate_pipeline_bundle(b)','print(json.dumps({"validated":True,"record_id":r["record_id"]}))'].join('\n');
(async()=>{
 const rows=[];
 for(const version of ['observable-battle-state/v1','observable-battle-state/v2']){
  const session=await createPipelineIntegrationSession({battle_id:'prompt12-legacy-id-witness-'+version.slice(-2),format:'gen9randombattle',seed:[101,202,303,404],observation_schema_version:version});
  try{
   const actions=Object.fromEntries(['p1','p2'].map(owner=>{const request=session.boundary.perspectives[owner].observation.request;return [owner,canonicalActionFromLegalAction(request,request.legal_actions.available_indices[0])]}));
   const result=await session.step(actions);
   for(const owner of ['p1','p2']){
    const bundle=result.record_bundles[owner]; const before=JSON.stringify(bundle); validatePipelineLinkedRecordBundle(bundle);
    const py=spawnSync(process.env.PYTHON||'D:/Anaconda/envs/neuralgpu/python.exe',['-c',code],{cwd:root,env,input:JSON.stringify(bundle),encoding:'utf8',timeout:30000,maxBuffer:1024*1024});
    if(py.error||py.status!==0)throw new Error('Python legacy validation failed: '+py.status+' '+py.stderr);
    if(JSON.stringify(bundle)!==before)throw new Error('legacy input mutated');
    rows.push({owner,version,battle_id:bundle.battle_id,typescript_validator:'validatePipelineLinkedRecordBundle',typescript_valid:true,python_validator:'validate_pipeline_bundle',python_exit:py.status,...JSON.parse(py.stdout),input_observation:bundle.input_observation.observation_id,successor_observation:bundle.successor_observation.observation_id,input_belief:bundle.input_belief.belief_id,successor_belief:bundle.successor_belief.belief_id,transition:bundle.transition.transition_id,immutable:true});
   }
  }finally{await session.close();}
 }
 fs.writeFileSync(path.join(__dirname,'perspective-fidelity-prompt12c-fresh-legacy-witness.json'),JSON.stringify({scope:'One real pinned local ordinary step per legacy schema; IDs only, no DATA or private objects persisted',encoding_overrides_unset:true,rows},null,2)+'\n');
 console.log(JSON.stringify({legacy_controls:rows.length,both_owners:true,both_schemas:true,typescript_valid:rows.every(r=>r.typescript_valid),python_exit_codes:rows.map(r=>r.python_exit),cleanup:true}));
})().catch(e=>{console.error(e.message);process.exitCode=1});
