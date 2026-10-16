import assert from 'node:assert/strict';
import test from 'node:test';
import {Battle, Teams, Dex} from 'pokemon-showdown';
import {extractChannelMessages} from 'pokemon-showdown/dist/sim/battle';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {NATIVE11_CONTEXT, HISTORICAL10_CONTEXT, REPLAY_COMPAT_CONTEXT, positiveFidelityScope, loadPreparedProtocolAsset} from '../src/version_profile';
import {validatePreparedProtocolAsset} from '../src/prepared_protocol_contract';
import {validateRawProtocolRecord} from '../src/observable_state';
import {validateObservableBattleState} from '../src/belief_state';
import {publicRevealedAbilities} from '../src/public_ability';
import {PipelineIntegrationSession, validatePipelineLinkedRecordBundle, classifyPipelineBoundary} from '../src/pipeline_integration';
import {canonicalActionFromLegalAction} from '../src/canonical_action';
const root=path.resolve(__dirname,'../../..');
const emit=(name:string,data:object)=>console.log('P41_WITNESS '+JSON.stringify({name,...data}));
const record='|-ability|p1a: Gardevoir|Natural Cure|Trace|[from] ability: Trace|[of] p2a: Blissey';
const old=record.replace('|Trace|[from]','|[from]');
const malformed=[record.replace('|Trace|','|Static|'),old,record.replace('|Trace|','|Trace|Trace|'),record.replace('[of] p2a: Blissey','[of] p1a: Gardevoir'),record.replace('p1a: Gardevoir','p1: Gardevoir'),record+'|extra'];
const siblings=[record.replace('[from] ability: Trace','[from] move: Skill Swap'),record.replace('[from] ability: Trace','[from] move: Role Play'), '|-activate|p2a: Blissey|ability: Mummy|p1a: Gardevoir|[ability] Trace'];
const canonical=(x:any):string=>x===null||typeof x!=='object'?JSON.stringify(x):Array.isArray(x)?'['+x.map(canonical).join(',')+']':'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}';
const digest=(x:any)=>createHash('sha256').update(canonical(x)).digest('hex');
function reseal(bundle:any):void {
 const o=bundle.successor_observation,prior=o.observation_id;
 o.protocol_prefix_hash=digest(o.protocol_prefix);
 o.observation_id='obs-'+digest(Object.fromEntries(Object.entries(o).filter(([k])=>!['observation_id','protocol_prefix'].includes(k))));
 const b=bundle.successor_belief;
 const ref={schema_version:o.schema_version,observation_id:o.observation_id,source_kind:o.source_kind,event_cursor:o.event_cursor,protocol_prefix_hash:o.protocol_prefix_hash,snapshot_phase:o.snapshot_phase};
 for(const r of [b.observation,...b.observation_history])if(r.observation_id===prior)Object.assign(r,ref);
 for(const t of b.transition_history)if(t.output_observation_id===prior)t.output_observation_id=o.observation_id;
 b.transition_lineage.output_observation_id=o.observation_id;
 b.belief_id='belief-'+digest(Object.fromEntries(Object.entries(b).filter(([k])=>k!=='belief_id')));
}
function python(bundle:any,expected?:RegExp):void {
 const bytes=JSON.stringify(bundle);
 const p=spawnSync(process.env.PYTHON!,['-m','neural.pipeline_record','--reader-profile=native11'],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'trainer/src')},input:bytes,encoding:'utf8',timeout:30000});
 assert.equal(p.status,expected?2:0,p.stderr||String(p.error));
 if(expected){assert.equal(p.stdout,'');assert.match(p.stderr,expected);}else assert.ok(JSON.parse(p.stdout));
 assert.equal(JSON.stringify(bundle),bytes);
}
test('P41 Trace source generator emitter audience and exact profiles',()=>{
 const pkg=path.join(root,'sim-core/node_modules/pokemon-showdown');
 const sets=JSON.parse(readFileSync(path.join(pkg,'data/random-battles/gen9/sets.json'),'utf8'));
 assert.deepEqual(sets.gardevoir.sets.map((s:any)=>s.abilities),[['Trace']]);
 const sourceDomain=[...new Set<string>(Object.values(sets).flatMap((s:any)=>s.sets.flatMap((x:any)=>x.abilities)))].filter(a=>!Dex.abilities.get(a).flags.notrace&&Dex.abilities.get(a).id!=='noability').sort();
 assert.deepEqual([...NATIVE11_CONTEXT.protocol.validation_rules.ability.payload_domains.dash_trace_copy].sort(),sourceDomain);
 const gen:any=Teams.getGenerator('gen9randombattle','1,2,3,4');
 const gardevoir=gen.randomSet('Gardevoir',{},true),blissey=gen.randomSet('Blissey',{},true);
 assert.equal(gardevoir.ability,'Trace');assert.equal(blissey.ability,'Natural Cure');
 const native=new Battle({formatid:'gen9randombattle',seed:'1,2,3,4',p1:{name:'P1',team:[gardevoir]},p2:{name:'P2',team:[blissey]}});
 try {
  assert.ok(native.log.includes(record));const channels=extractChannelMessages(native.log.join('\n'),[0,1,2]);
  for(const audience of [0,1,2] as const)assert.ok(channels[audience].includes(record));
  validateRawProtocolRecord(record,NATIVE11_CONTEXT);
  for(const row of malformed)assert.throws(()=>validateRawProtocolRecord(row,NATIVE11_CONTEXT),/Malformed raw .*ability.*record/);
  for(const row of siblings)assert.throws(()=>validateRawProtocolRecord(row,NATIVE11_CONTEXT),/prepared-family-unsupported\/ability-setter/);
  for(const context of [HISTORICAL10_CONTEXT,REPLAY_COMPAT_CONTEXT]){validateRawProtocolRecord(old,context);assert.throws(()=>validateRawProtocolRecord(record,context));}
  const facts=publicRevealedAbilities([record],NATIVE11_CONTEXT)['p1: Gardevoir'];
  assert.equal(facts.ability,'naturalcure');assert.equal(facts.copied,true);assert.equal(facts.base,null);
  const asset=JSON.parse(JSON.stringify(loadPreparedProtocolAsset('native11')));asset.protocol.validation_rules.ability.dash_templates=['reveal','boost','trace-copy'];
  assert.throws(()=>validatePreparedProtocolAsset(asset,'native11'),/rule-template/);
  assert.equal(positiveFidelityScope('native11','gen9randombattle'),false);
  emit('source-emitter',{record,audiences:[0,1,2],source_qualified_domain:sourceDomain.length,generator:'actual randomSet on target gen9randombattle generator; constrained species, not full random-team reachability',prior_is_not_base:true});
 }finally{native.destroy();}
});

test('P41 Trace owned v1 v2 publication and coherent negatives',async()=>{
 const generate=Teams.generate;
 try {
  for(const version of ['v1','v2']) {
   let calls=0,session:PipelineIntegrationSession|undefined;
   Teams.generate=function(){return Teams.import(calls++===0?'Gardevoir\nAbility: Trace\n- Splash':'Blissey\nAbility: Natural Cure\n- Splash')!;};
   try {
    session=await PipelineIntegrationSession.create({battle_id:'P41-'+version,format:'gen9randombattle',seed:[1,2,3,4],observation_schema_version:('observable-battle-state/'+version) as any});
    const initial=session.boundary;
    for(const owner of ['p1','p2'] as const)validateObservableBattleState(initial.perspectives[owner].observation,NATIVE11_CONTEXT);
    assert.equal(classifyPipelineBoundary({p1:initial.perspectives.p1.observation,p2:initial.perspectives.p2.observation}),'joint_actionable');
    const owned=initial.perspectives.p1.observation.view.self_team[0];assert.equal(owned.ability,'naturalcure');assert.equal(owned.base_ability,'trace');
    const actions=Object.fromEntries((['p1','p2'] as const).map(owner=>{const req=initial.perspectives[owner].observation.request!;return [owner,canonicalActionFromLegalAction(req,req.legal_actions.available_indices[0])];})) as any;
    const step=await session.step(actions);
    for(const owner of ['p1','p2'] as const){const bundle=step.record_bundles[owner]!;validatePipelineLinkedRecordBundle(bundle,NATIVE11_CONTEXT);python(bundle);}
    // Shared fully linked candidates; reseal identities so rule/semantic checks, not hashes, reject them.
    const base=step.record_bundles.p1!;
    const changes:Array<[string,(b:any)=>void,RegExp]>=malformed.map((line,i)=>['grammar-'+i,(b:any)=>{const o=b.successor_observation;o.protocol_prefix=o.protocol_prefix.map((x:string)=>x===record?line:x);},/Malformed raw .*ability.*record/]);
    changes.push(['setter-sibling',(b:any)=>{b.successor_observation.protocol_prefix=b.successor_observation.protocol_prefix.map((x:string)=>x===record?siblings[0]:x);},/prepared-family-unsupported\/ability-setter/],
      ['false-copy',(b:any)=>{b.successor_observation.view.self_team[0].ability='static';},/ability.*(mismatch|disagrees|contradict)|Ability.*(mismatch|disagrees|contradict)/],
      ['false-base',(b:any)=>{b.successor_observation.view.self_team[0].base_ability='naturalcure';},/ability.*(mismatch|disagrees|contradict)|Ability.*(mismatch|disagrees|contradict)/]);
    // Grammar representatives on v1, typed copy/base on v2; no fixture Cartesian product.
    for(const [name,change,error] of changes.filter(([name])=>version==='v1'?!name.startsWith('false-'):name.startsWith('false-'))) {
     const candidate=structuredClone(base);change(candidate);reseal(candidate);const before=JSON.stringify(candidate);
     assert.throws(()=>validatePipelineLinkedRecordBundle(candidate,NATIVE11_CONTEXT),error);python(candidate,error);assert.equal(JSON.stringify(candidate),before);
     emit(name,{schema:version,ts_rejection:true,python_exit:2,stdout_bytes:0,coherently_rehashed:true});
    }
    emit('owned-publication',{schema:version,owners:['p1','p2'],public_current:'naturalcure',owned_base:'trace',target_positive_fidelity:false,scope:'constructed native session, no episode completeness claim'});
   }finally{await session?.close();}
  }
 }finally{Teams.generate=generate;}
});

test('P41 Trace reviewed provenance rejects stale control evidence',()=>{
 const asset=JSON.parse(JSON.stringify(loadPreparedProtocolAsset('native11')));
 assert.match(asset.protocol.source_basis[0],/Prompt41 source-qualified target Trace/);
 const control=asset.protocol.valid_record_controls.find((c:any)=>c.record===record)!;
 assert.match(control.evidence,/Prompt41 source-qualified target Trace/);
 const stale=structuredClone(asset);stale.protocol.valid_record_controls.find((c:any)=>c.record===record)!.evidence='Prompt37 bounded fixed-grammar fixture check; no target engine execution';
 assert.throws(()=>validatePreparedProtocolAsset(stale,'native11'),/control-evidence/);
 const missing=structuredClone(asset);missing.protocol.valid_record_controls=missing.protocol.valid_record_controls.filter((c:any)=>c.record!==record);
 assert.throws(()=>validatePreparedProtocolAsset(missing,'native11'),/trace-controls/);
 const script=`import json,sys,copy\nfrom neural.prepared_protocol_contract import validate_prepared_protocol_asset\na=json.load(sys.stdin)\nvalidate_prepared_protocol_asset(a,'native11')\nfor kind in ('stale','missing'):\n b=copy.deepcopy(a)\n c=next(x for x in b['protocol']['valid_record_controls'] if '|Trace|[from] ability: Trace|' in x['record'])\n if kind=='stale': c['evidence']='Prompt37 bounded fixed-grammar fixture check; no target engine execution'\n else: b['protocol']['valid_record_controls'].remove(c)\n try: validate_prepared_protocol_asset(b,'native11')\n except ValueError as e: assert ('control-evidence' if kind=='stale' else 'trace-controls') in str(e),str(e)\n else: raise AssertionError(kind+' accepted')\nprint('P41 Python provenance positive and stale/missing controls PASS')`;
 const p=spawnSync(process.env.PYTHON!,['-c',script],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'trainer/src')},input:JSON.stringify(asset),encoding:'utf8',timeout:30000});
 assert.equal(p.status,0,p.stderr||String(p.error));console.log(p.stdout.trim());
 emit('reviewed-provenance',{ts:true,python:true,stale_and_missing_reject:true,target_positive_fidelity:false});
});
