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
function inject(original:any,where:'input'|'successor',line:string) {
 let b=structuredClone(original);const oldInput=b.input_observation.observation_id,oldNext=b.successor_observation.observation_id;
 const at=where==='input'?b.input_observation.event_cursor:b.successor_observation.event_cursor;
 if(where==='input')b.input_observation.protocol_prefix.push(line);
 b.successor_observation.protocol_prefix.splice(at,0,line);
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
const malformed=['','garbage','p3a: Name','p1: Name','p1A: Name','p1a:','p1a: ','p1a: \t','p1a: \ufeff','p1a Name'];
const lines=[...malformed.map(id=>`|-copyboost|${id}|p2a: Donor|[from] move: Psych Up`),...malformed.map(id=>`|-copyboost|p1a: Caller|${id}|[from] move: Psych Up`),'|-copyboost','|-copyboost||p2a: Donor|[from] ability: Costar','|-copyboost|p1a: Caller|p2a: Donor','|-copyboost|p1a: Caller|p2a: Donor|[from] move: Psych Up|extra','|-copyboost|p1a: Caller|p2a: Donor|[from] ability: Costar'];
const aliasLines=[...lines.map(line=>line.replace('|-copyboost','|copyboost')), '|copyboost|p1a: Caller|p2a: Donor|[from] move: Psych Up'];
const publicationRejections=[...lines,...aliasLines];
for(const version of ['observable-battle-state/v1','observable-battle-state/v2'] as const)test(`${version} rehashed malformed copies reject both perspectives and both prefix positions`,async()=>{
 const s=await createPipelineIntegrationSession({battle_id:'psych-grammar',format:'gen9randombattle',seed:[1,2,3,4],observation_schema_version:version});
 try {
 const actions=Object.fromEntries((['p1','p2'] as const).map(p=>{const r=s.boundary.perspectives[p].observation.request!;return[p,canonicalActionFromLegalAction(r,r.legal_actions.available_indices[0])]})) as Parameters<typeof s.step>[0];
 const result=await s.step(actions),bundles:any[]=[],validBundles:any[]=Object.values(result.record_bundles);
 for(const p of ['p1','p2'] as const)for(const where of ['input','successor'] as const) {
  const good=inject(result.record_bundles[p],where,'|-copyboost|p1z: Unresolved|p2z: Donor|[from] move: Psych Up');
  projectBeliefState({observation:good[where+'_observation']});validBundles.push(good);
 }
 for(const p of ['p1','p2'] as const)for(const where of ['input','successor'] as const)for(const line of publicationRejections) {
  const b=inject(result.record_bundles[p],where,line);bundles.push(b);
  assert.throws(()=>validateObservableProtocolPrefix(b[where+'_observation'].protocol_prefix,p),/copy|identifier/);
  assert.throws(()=>projectBeliefState({observation:b[where+'_observation']}),/copy|identifier|stages/);
 }
 const response=py({valid:validBundles,bad:bundles},`import json,sys\nfrom neural.pipeline_record import validate_pipeline_bundle,PipelineRecordError\nfrom neural.ts_identity import verify_bundle_identities\nx=json.load(sys.stdin)\nfor b in x['valid']: validate_pipeline_bundle(b)\nfor b in x['bad']:\n verify_bundle_identities(b)\n try: validate_pipeline_bundle(b)\n except PipelineRecordError as e:\n  assert 'copy' in str(e),str(e)\n  if any(line.startswith('|copyboost') for line in b['successor_observation']['protocol_prefix']): assert 'unsupported raw protocol event: copyboost' in str(e),str(e)\n else: raise AssertionError('published malformed copy')\nprint(len(x['bad']))`);
 assert.equal(response.status,0,response.stderr);assert.equal(Number(response.stdout),publicationRejections.length*4);
 }finally{await s.close()}
});
test('copy helpers validate before routing; valid unresolved identities remain unknown',()=>{
 for(const line of lines)assert.throws(()=>opponentPublicBoosts([line],'p1a: Caller'),/copy/);
 const valid=['p1a: Unseen','p1z:Unseen',' p1a: Unseen ','p1a: é😀'];
 for(const ident of valid) {const line=`|-copyboost|${ident}|p2z:Unknown|[from] move: Psych Up`;validateObservableProtocolPrefix([line],'p1');assert.ok(Object.values(opponentPublicBoosts([line],ident)).every(x=>x===null));}
 const prefix=['|-setboost|p1a: Caller|atk|6','|-copyboost|p1a: Caller|p2a: Unseen|[from] move: Psych Up'];assert.ok(Object.values(opponentPublicBoosts(prefix,'p1a: Caller')).every(x=>x===null));
 const response=py({bad:lines,valid:valid.map(id=>`|-copyboost|${id}|p2z:Unknown|[from] move: Psych Up`),prefix},`import json,sys\nfrom neural.public_boosts import public_boost_evidence\nx=json.load(sys.stdin)\nfor line in x['bad']:\n try: public_boost_evidence([line])\n except ValueError as e: assert 'copy' in str(e)\n else: raise AssertionError(line)\nfor line in x['valid']:\n for stages in public_boost_evidence([line]).values(): assert all(v is None for v in stages.values())\nassert all(v is None for v in public_boost_evidence(x['prefix'])['p1: Caller'].values())`);assert.equal(response.status,0,response.stderr);
});
test('original fully rehashed review reproductions reject before Python CLI output',()=>{
 const folder=path.resolve(__dirname,'../../../artifacts/validation/psych-up-review-2026-09-25');
 for(const name of fs.readdirSync(folder).filter(n=>n.startsWith('malformed-')&&n.endsWith('.json'))) {
  const b=JSON.parse(fs.readFileSync(path.join(folder,name),'utf8'));
  const result=spawnSync(process.env.PYTHON||'python3',['-m','neural.pipeline_record'],{input:JSON.stringify(b),encoding:'utf8',env:{...process.env,PYTHONPATH:path.resolve(__dirname,'../../../trainer/src')}});
  assert.equal(result.status,2,result.stderr);assert.equal(result.stdout,'');assert.match(result.stderr,/copy/);
 }
});

test('original bare-alias reproductions reject before publication with unchanged valid controls',()=>{
 const folder=path.resolve(__dirname,'../../../artifacts/validation/psych-up-alias-review-2026-09-25');
 for(const name of ['valid-v1.json','valid-v2.json','alias-v1.json','alias-v2.json']) {
  const b=JSON.parse(fs.readFileSync(path.join(folder,name),'utf8'));
  const verification=py(b,'import json,sys; from neural.ts_identity import verify_bundle_identities; verify_bundle_identities(json.load(sys.stdin))');
  assert.equal(verification.status,0,verification.stderr);
  const result=spawnSync(process.env.PYTHON||'python3',['-m','neural.pipeline_record'],{input:JSON.stringify(b),encoding:'utf8',env:{...process.env,PYTHONPATH:path.resolve(__dirname,'../../../trainer/src')}});
  if(name.startsWith('alias')) {assert.equal(result.status,2,result.stderr);assert.equal(result.stdout,'');assert.match(result.stderr,/unsupported raw protocol event: copyboost/);assert.throws(()=>projectBeliefState({observation:b.successor_observation}),/copyboost/);}
  else {assert.equal(result.status,0,result.stderr);assert.equal(JSON.parse(result.stdout).observation_id,b.input_observation.observation_id);projectBeliefState({observation:b.successor_observation});}
 }
});
