const root=require('node:path').resolve(__dirname, '../../..');
const {createPipelineIntegrationSession}=require(root+'/sim-core/dist/src/pipeline_integration');
const {canonicalActionFromLegalAction}=require(root+'/sim-core/dist/src/canonical_action');
const {serializeBeliefState}=require(root+'/sim-core/dist/src/belief_state');
const {createHash}=require('node:crypto');
const {spawnSync}=require('node:child_process');
const canon=v=>Array.isArray(v)?'['+v.map(canon).join(',')+']':v&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canon(v[k])).join(',')+'}':JSON.stringify(v);
const hash=v=>createHash('sha256').update(canon(v)).digest('hex');
function seal(b){for(const k of ['input_belief','successor_belief']) {if(k==='successor_belief')b[k].parent_belief_id=b.input_belief.belief_id;b[k].belief_id='belief-'+hash(Object.fromEntries(Object.entries(b[k]).filter(([k])=>k!=='belief_id')));}}
(async()=>{const s=await createPipelineIntegrationSession({battle_id:'history-review',format:'gen9randombattle',seed:[1,2,3,4],observation_schema_version:'observable-battle-state/v2'});try{let r;for(let i=0;i<2;i++){const actions=Object.fromEntries(['p1','p2'].map(p=>{const q=s.boundary.perspectives[p].observation.request;return[p,canonicalActionFromLegalAction(q,q.legal_actions.available_indices[0])]}));r=await s.step(actions);}
const original=r.record_bundles.p1;
for(const field of ['control','source_kind','snapshot_phase']){const b=structuredClone(original); if(field!=='control'){for(const k of ['input_belief','successor_belief'])b[k].observation_history[0][field]='invalid';seal(b);}const py=spawnSync(process.env.PYTHON || 'python3',['-m','neural.pipeline_record'],{input:JSON.stringify(b),encoding:'utf8',env:{...process.env,PYTHONPATH:root+'/trainer/src'}});let ts;try{serializeBeliefState(b.input_belief);ts='accepted';}catch(e){ts=e.message}console.log(JSON.stringify({field,history:b.input_belief.observation_history.length,python:py.status,stderr:py.stderr,typescript:ts}));}
}finally{await s.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
