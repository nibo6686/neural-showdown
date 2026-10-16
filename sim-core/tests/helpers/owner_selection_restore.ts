import assert from 'node:assert/strict';
import {Battle,Teams} from 'pokemon-showdown';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {PipelineIntegrationSession,validatePipelineEpisodeRecordBundle} from '../../src/pipeline_integration';
import {NativeObjectAssociation} from '../../src/owner_identity_crosswalk';
import {LocalBattleEnv} from '../../src/env_manager';
import {canonicalActionFromLegalAction} from '../../src/canonical_action';
import {NATIVE11_CONTEXT,positiveFidelityScope} from '../../src/version_profile';
const owners=['p1','p2'] as const;
export type Owner=typeof owners[number];
export const other=(owner:Owner):Owner=>owner==='p1'?'p2':'p1';
export const emit=(name:string,data:object)=>console.log('P42_WITNESS '+JSON.stringify({name,...data}));
export const env=(s:PipelineIntegrationSession):LocalBattleEnv=>(s as any).environment;
export const native=(s:PipelineIntegrationSession):Battle=>(env(s) as any).battleStream.battle;
export const holding=(s:PipelineIntegrationSession,p:Owner)=>s.readNativeObjectHolding(s.getNativeObjectHolding(p),p);
export function choice(s:PipelineIntegrationSession,p:Owner,text:string){const r=s.boundary.perspectives[p].observation.request!;const a=r.legal_actions.actions.find(a=>a?.choice===text);assert.ok(a,text+' legal for '+p);return canonicalActionFromLegalAction(r,a.index);}
export const joint=(s:PipelineIntegrationSession,p:Owner,a:string,b='move 1')=>s.step({p1:choice(s,'p1',p==='p1'?a:b),p2:choice(s,'p2',p==='p2'?a:b)});
export async function constructed(owner:Owner,healer='Pawmot'){
 const generate=Teams.generate;let count=0;
 const own=Teams.import('First (Snorlax)\nAbility: Immunity\n- Splash\n- Explosion\n\nHealer ('+healer+')\nAbility: '+(healer==='Pawmot'?'Iron Fist':'Synchronize')+'\n- Revival Blessing\n- Splash\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash')!;
 const wait=Teams.import('Watcher (Giratina)\nAbility: Pressure\n- Splash\n- Will-O-Wisp\n\nWaitingReserve (Magikarp)\nAbility: Swift Swim\n- Splash')!;
 Teams.generate=function(){return structuredClone(owners[count++]===owner?own:wait);};
 try{return await PipelineIntegrationSession.create({battle_id:'P42-'+owner+'-'+healer,format:'gen9randombattle',seed:[1,2,3,4],observation_schema_version:'observable-battle-state/v2'});}finally{Teams.generate=generate;}
}
export function publish(bundle:any,error?:RegExp){const bytes=JSON.stringify(bundle);if(!error)validatePipelineEpisodeRecordBundle(bundle,NATIVE11_CONTEXT);else assert.throws(()=>validatePipelineEpisodeRecordBundle(bundle,NATIVE11_CONTEXT),error);
 const r=spawnSync(process.env.PYTHON!,['-m','neural.pipeline_record','--reader-profile=native11'],{cwd:path.resolve(__dirname,'../../../..'),env:process.env,input:bytes,encoding:'utf8',timeout:30000});assert.equal(r.status,error?2:0,r.stderr||String(r.error));if(error){assert.equal(r.stdout,'');assert.match(r.stderr,error);}else assert.ok(JSON.parse(r.stdout));assert.equal(JSON.stringify(bundle),bytes);}
export async function checked(s:PipelineIntegrationSession,run:()=>Promise<any>,expected:Record<Owner,number[]>){
 const prior=s.boundary,old=owners.flatMap(p=>native(s)[p]!.pokemon),oldsets=old.map(p=>p.set),held=owners.map(p=>s.readOriginalOwnerHolding(s.getOriginalOwnerHolding(p),p));
 const handles=owners.map(p=>s.getNativeObjectHolding(p)),deliveries=owners.map(p=>s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(p),p));
 const accept=NativeObjectAssociation.prototype.acceptRestore;let restored=0;
 NativeObjectAssociation.prototype.acceptRestore=function(environment,input,battle,ticket){accept.call(this,environment,input,battle,ticket);restored++;
  for(const [i,p] of owners.entries())for(const [position,mon] of battle[p]!.pokemon.entries()){assert.ok(!old.includes(mon));assert.ok(!oldsets.includes(mon.set));const raw=(input as any).sides[i];assert.equal(mon.set,raw.pokemon[position].set);assert.equal(battle[p]!.team.indexOf(mon.set)+1,holding(s,p).original_slots[position]);assert.equal(raw.team.split('').indexOf(String(position+1))+1,holding(s,p).original_slots[position]);}
 };
 try{const result=await run();assert.equal(restored,1);
  for(const [i,p] of owners.entries()){
   const h=holding(s,p);assert.equal(h.original,held[i]);assert.deepEqual(h.original_slots,expected[p]);assert.equal(h.observation_id,s.boundary.perspectives[p].observation.observation_id);assert.equal(h.branch_id,s.boundary.branch_id);assert.equal(h.step_index,prior.step_index+1);
   assert.throws(()=>s.readNativeObjectHolding(handles[i],p),/foreign-or-forged-holding/);assert.throws(()=>s.readNativeObjectHolding(s.getNativeObjectHolding(p),other(p)),/foreign-or-forged-holding/);
   const history=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(p),p),last=history.boundaries.at(-1)!;
   assert.equal(last.parent!.observation_id,prior.perspectives[p].observation.observation_id);assert.equal(last.parent!.branch_id,prior.branch_id);assert.equal(last.parent!.step_index,prior.step_index);
   assert.equal(last.current!.owner,p);assert.ok(history.deliveries.length>=deliveries[i].deliveries.length);assert.ok(last.trace.some(r=>r.origin==='restore_reemit'));
   assert.ok(!JSON.stringify(result).includes('original_slots'));assert.ok(!JSON.stringify(result).includes('packed_team'));assert.ok(!JSON.stringify(result).includes('objectAssociation'));
  }
  assert.equal(positiveFidelityScope('native11','gen9randombattle'),false);return result;
 }finally{NativeObjectAssociation.prototype.acceptRestore=accept;}
}
export async function rollback(s:PipelineIntegrationSession,run:()=>Promise<any>){
 const prepare=NativeObjectAssociation.prototype.prepareCommit,close=LocalBattleEnv.prototype.close;
 const boundary=s.boundary,rows=owners.map(p=>holding(s,p)),handles=owners.map(p=>s.getNativeObjectHolding(p)),history=owners.map(p=>s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(p),p));let controller:NativeObjectAssociation|undefined,token:object|undefined,cleanup=false;
 NativeObjectAssociation.prototype.prepareCommit=function(...args){controller=this;token=prepare.apply(this,args);throw new Error('P42-post-prepare');};
 LocalBattleEnv.prototype.close=function(){if(this.id.includes('step-')&&controller&&token){assert.throws(()=>controller!.commit(token!),/foreign-or-stale-preparation/);cleanup=true;}return close.call(this);};
 try{await assert.rejects(run(),/P42-post-prepare/);assert.ok(cleanup);assert.equal(s.boundary,boundary);for(const [i,p] of owners.entries()){assert.equal(s.getNativeObjectHolding(p),handles[i]);assert.equal(holding(s,p),rows[i]);assert.equal(s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(p),p),history[i]);}}finally{NativeObjectAssociation.prototype.prepareCommit=prepare;LocalBattleEnv.prototype.close=close;}
 emit('selection-post-prepare-rollback',{revoked_before_cleanup:true,both_exact_holdings_and_deliveries_retained:true,fresh_retry:'executed by caller'});
}
export async function parentFault(s:PipelineIntegrationSession,run:()=>Promise<any>){const prepare=NativeObjectAssociation.prototype.prepareRestore,before=s.boundary,held=owners.map(p=>holding(s,p));NativeObjectAssociation.prototype.prepareRestore=function(e,p,snapshot){return prepare.call(this,e,{...p},snapshot);};try{await assert.rejects(run(),/foreign-or-missing-parent/);assert.equal(s.boundary,before);for(const [i,p] of owners.entries())assert.equal(holding(s,p),held[i]);}finally{NativeObjectAssociation.prototype.prepareRestore=prepare;}}

const canonical=(x:any):string=>x===null||typeof x!=='object'?JSON.stringify(x):Array.isArray(x)?'['+x.map(canonical).join(',')+']':'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}';
const digest=(x:any)=>createHash('sha256').update(canonical(x)).digest('hex');
export function reseal(b:any){const o=b.successor_observation,prior=o.observation_id;o.protocol_prefix_hash=digest(o.protocol_prefix);o.observation_id='obs-'+digest(Object.fromEntries(Object.entries(o).filter(([k])=>!['observation_id','protocol_prefix'].includes(k))));const belief=b.successor_belief;belief.source_protocol_prefix=structuredClone(o.protocol_prefix);const ref={schema_version:o.schema_version,observation_id:o.observation_id,source_kind:o.source_kind,event_cursor:o.event_cursor,protocol_prefix_hash:o.protocol_prefix_hash,snapshot_phase:o.snapshot_phase};for(const r of [belief.observation,...belief.observation_history])if(r.observation_id===prior)Object.assign(r,ref);for(const t of belief.transition_history)if(t.output_observation_id===prior)t.output_observation_id=o.observation_id;belief.transition_lineage.output_observation_id=o.observation_id;belief.belief_id='belief-'+digest(Object.fromEntries(Object.entries(belief).filter(([k])=>k!=='belief_id')));}
