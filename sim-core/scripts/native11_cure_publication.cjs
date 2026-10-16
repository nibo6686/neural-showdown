const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'../..');
const {Teams}=require('../node_modules/pokemon-showdown');
const {PipelineIntegrationSession,validatePipelineLinkedRecordBundle}=require('../dist/src/pipeline_integration');
const {canonicalActionFromLegalAction}=require('../dist/src/canonical_action');
const {NATIVE11_CONTEXT}=require('../dist/src/version_profile');

test('P38 native Natural Cure session publication',async()=>{
 const generate=Teams.generate;let calls=0,session;
 Teams.generate=function(){return Teams.import(calls++===0?'Blissey\nLevel: 100\nAbility: Natural Cure\n- Splash\n\nPikachu\nLevel: 100\nAbility: Static\n- Splash':'Pikachu\nLevel: 1\nAbility: Static\n- Thunder Wave\n- Splash');};
 try{
  session=await PipelineIntegrationSession.create({battle_id:'P38-NC-é-Ω',format:'gen9randombattle',seed:[1,2,3,4],observation_schema_version:'observable-battle-state/v2'});
  const action=(owner,index)=>canonicalActionFromLegalAction(session.boundary.perspectives[owner].observation.request,index);
  await session.step({p1:action('p1',0),p2:action('p2',0)});
  const result=await session.step({p1:action('p1',8),p2:action('p2',1)});
  const expected='|-curestatus|p1a: Blissey|par|[from] ability: Natural Cure|[silent]';
  const oracles=[];
  for(const owner of ['p1','p2']){
   const bundle=result.record_bundles[owner];assert.ok(bundle);validatePipelineLinkedRecordBundle(bundle,NATIVE11_CONTEXT);
   const prefix=bundle.successor_observation.protocol_prefix;assert.ok(prefix.includes(expected));
   const env={...process.env,PYTHONPATH:root+'/trainer/src'};delete env.PYTHONUTF8;delete env.PYTHONIOENCODING;for(const key of Object.keys(env))if(key.startsWith('REPORT_')||key.startsWith('PROMPT'))delete env[key];
   const child=spawnSync('/Users/nbolger/Desktop/neural-showdown/.venv-simulator/bin/python',['-m','neural.pipeline_record','--reader-profile=native11'],{input:JSON.stringify(bundle),cwd:root,env,encoding:'utf8',timeout:20000});
   assert.equal(child.status,0,child.stderr);assert.ok(child.stdout.trim());
   oracles.push({owner,source_index:prefix.indexOf(expected),transition_id:bundle.transition.transition_id,python_published:true});
   fs.writeFileSync(root+'/docs/planning/perspective-fidelity-prompt38-NC-'+owner+'-bundle.json',JSON.stringify(bundle));
  }
  console.log('P38_WITNESS '+JSON.stringify({name:'NC-session-publication',record:expected,oracles,scope:'constructed teams in actual session; generated reachability unproved',native_target:true,coherent_grammar_publication_negatives:'DEFERRED'}));
 }finally{Teams.generate=generate;await session?.close();}
});
