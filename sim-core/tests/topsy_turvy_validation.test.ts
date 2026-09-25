import assert from 'node:assert/strict';
import test from 'node:test';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import { createPipelineIntegrationSession } from '../src/pipeline_integration';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { projectBeliefState } from '../src/belief_state';
import { validateObservableProtocolPrefix } from '../src/observable_state';
import { opponentPublicBoosts } from '../src/public_boosts';
const canonical=(x:any):string=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':x&&typeof x==='object'?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
const hash=(x:any)=>createHash('sha256').update(canonical(x)).digest('hex');
const obsId=(o:any)=>'obs-'+hash(Object.fromEntries(Object.entries(o).filter(([k])=>!['observation_id','protocol_prefix'].includes(k))));
const beliefId=(b:any)=>'belief-'+hash(Object.fromEntries(Object.entries(b).filter(([k])=>k!=='belief_id')));
const py=(x:any,code:string)=>spawnSync(process.env.PYTHON||'python3',['-c',code],{input:JSON.stringify(x),encoding:'utf8',env:{...process.env,PYTHONPATH:path.resolve(__dirname,'../../../trainer/src')}});
function inject(original:any,where:'input'|'successor',line:string, poison=false) {
 let b=structuredClone(original);const oldInput=b.input_observation.observation_id,oldNext=b.successor_observation.observation_id;
 const at=where==='input'?b.input_observation.event_cursor:b.successor_observation.event_cursor;
 if(where==='input')b.input_observation.protocol_prefix.push(line);
 b.successor_observation.protocol_prefix.splice(at,0,line);
 if(poison) {const o=b[where+'_observation'];const pk=o.view.opponent_team[0];pk.public_boosts.atk=pk.public_boosts.atk===6?5:6;}
 const refs:any={};
 for(const [which,old] of [['input',oldInput],['successor',oldNext]]) {
  const o=b[which+'_observation'];o.event_cursor=o.protocol_prefix.length;o.protocol_prefix_hash=hash(o.protocol_prefix);o.observation_id=obsId(o);
  refs[old]=Object.fromEntries(['schema_version','observation_id','source_kind','event_cursor','protocol_prefix_hash','snapshot_phase'].map(k=>[k,o[k]]));
 }
 const walk=(v:any):any=>Array.isArray(v)?v.map(walk):v&&typeof v==='object'?(refs[v.observation_id]?{...v,...refs[v.observation_id]}:Object.fromEntries(Object.entries(v).map(([k,x])=>[k,walk(x)]))):v===oldInput?b.input_observation.observation_id:v===oldNext?b.successor_observation.observation_id:v;
 for(const which of ['input','successor']) {b[which+'_belief']=walk(b[which+'_belief']);b[which+'_belief'].source_protocol_prefix=[...b[which+'_observation'].protocol_prefix];}
 b.input_belief.belief_id=beliefId(b.input_belief);b.successor_belief.parent_belief_id=b.input_belief.belief_id;b.successor_belief.belief_id=beliefId(b.successor_belief);
 return b;
}
const invalid=['','garbage','p3a: Name','p1: Name','p1A: Name','p1a:','p1a: ','p1a: \t','p1a: \ufeff','p1a Name'];
const malformed=[...invalid.map(id=>`|-invertboost|${id}|[from] move: Topsy-Turvy`),'|-invertboost','|-invertboost|p1a: Target','|-invertboost|p1a: Target|[from] move: Rigged Dice','|-invertboost|p1a: Target|[from] move: Topsy-Turvy|extra'];
const aliases=[...malformed.map(s=>s.replace('|-invertboost','|invertboost')),'|invertboost|p1a: Target|[from] move: Topsy-Turvy'];
for(const version of ['observable-battle-state/v1','observable-battle-state/v2'] as const)test(`${version} inversion publication grammar matrix verifies hashes before rejection`,async()=>{
 const s=await createPipelineIntegrationSession({battle_id:'invert-grammar',format:'gen9randombattle',seed:[1,2,3,4],observation_schema_version:version});
 try {
 const actions=Object.fromEntries((['p1','p2'] as const).map(p=>{const r=s.boundary.perspectives[p].observation.request!;return[p,canonicalActionFromLegalAction(r,r.legal_actions.available_indices[0])]})) as Parameters<typeof s.step>[0];
 const result=await s.step(actions),bad:any[]=[],good:any[]=Object.values(result.record_bundles),falseStages:any[]=[];
 for(const p of ['p1','p2'] as const)for(const where of ['input','successor'] as const) {
  const supported='|-invertboost|p1z: Unresolved|[from] move: Topsy-Turvy';
  const control=inject(result.record_bundles[p],where,supported);projectBeliefState({observation:control[where+'_observation']});good.push(control);
  if(version.endsWith('/v2')) {const poisoned=inject(result.record_bundles[p],where,supported,true);assert.throws(()=>projectBeliefState({observation:poisoned[where+'_observation']}),/stages/);falseStages.push(poisoned);
   const rejected=spawnSync(process.env.PYTHON||'python3',['-m','neural.pipeline_record'],{input:JSON.stringify(poisoned),encoding:'utf8',env:{...process.env,PYTHONPATH:path.resolve(__dirname,'../../../trainer/src')}});
   assert.equal(rejected.status,2,rejected.stderr);assert.equal(rejected.stdout,'');assert.match(rejected.stderr,/exact prefix/);}
  for(const line of [...malformed,...aliases]) {
   const b=inject(result.record_bundles[p],where,line);bad.push(b);
   assert.throws(()=>validateObservableProtocolPrefix(b[where+'_observation'].protocol_prefix,p),/invert|identifier/);
   assert.throws(()=>projectBeliefState({observation:b[where+'_observation']}),/inver|identifier|stages/);
  }
 }
 const response=py({good,bad,falseStages},`import json,sys\nfrom neural.pipeline_record import validate_pipeline_bundle,PipelineRecordError\nfrom neural.ts_identity import verify_bundle_identities\nx=json.load(sys.stdin)\nfor b in x['good']: validate_pipeline_bundle(b)\nfor b in x['bad']:\n verify_bundle_identities(b)\n try: validate_pipeline_bundle(b)\n except PipelineRecordError as e:\n  assert 'inver' in str(e),str(e)\n  if any(l.startswith('|invertboost') for l in b['successor_observation']['protocol_prefix']): assert 'unsupported raw protocol event: invertboost' in str(e)\n else: raise AssertionError('published malformed inversion')\nfor b in x['falseStages']:\n verify_bundle_identities(b)\n try: validate_pipeline_bundle(b)\n except PipelineRecordError as e: assert 'exact prefix' in str(e),str(e)\n else: raise AssertionError('published false stages')\nprint(len(x['bad']))`);
 assert.equal(response.status,0,response.stderr);assert.equal(Number(response.stdout),116);
 }finally{await s.close()}
});
test('inversion grammar rejects before routing; supported unresolved identifier is unknown',()=>{
 for(const line of malformed)assert.throws(()=>opponentPublicBoosts([line],'p1a: Target'),/inversion/);
 const line='|-invertboost|p1a: Unseen|[from] move: Topsy-Turvy';validateObservableProtocolPrefix([line],'p1');assert.ok(Object.values(opponentPublicBoosts([line],'p1a: Unseen')).every(v=>v===null));
 const result=py(malformed,`import json,sys\nfrom neural.public_boosts import public_boost_evidence\nfor line in json.load(sys.stdin):\n try: public_boost_evidence([line])\n except ValueError as e: assert 'inversion' in str(e)\n else: raise AssertionError(line)`);assert.equal(result.status,0,result.stderr);
});
