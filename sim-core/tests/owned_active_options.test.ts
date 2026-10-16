import assert from 'node:assert/strict';
import test from 'node:test';
import { Teams, Dex, Battle } from 'pokemon-showdown';
import { PipelineIntegrationSession } from '../src/pipeline_integration';
import { NativeBirthEnrollment } from '../src/owner_identity_crosswalk';
import { OwnedRequestHealthHost } from '../src/owned_request_health';
import { NativeOwnerKnowledgeController } from '../src/native_owner_knowledge';
import { LocalBattleEnv } from '../src/env_manager';
import { checkNativeOwnerActiveOptionsProjection, knowledgeIdentity } from '../src/perspective_knowledge';
import { choice, joint, native, env } from './helpers/owner_selection_restore';
const owners=['p1','p2'] as const;
const base={battle_id:'P53',format:'gen9randombattle',seed:[1,2,3,4],observation_schema_version:'observable-battle-state/v2' as const};
const recipients=()=>({p1:{},p2:{}});
const read=(s:PipelineIntegrationSession,r:object)=>s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(r),r);
const emit=(name:string,data:object)=>console.log('P53_WITNESS '+JSON.stringify({name,...data}));
const simple=['Alpha (Magikarp)\nAbility: Swift Swim\n- Splash\n- Tackle\n\nBeta (Magikarp)\nAbility: Swift Swim\n- Splash', 'Gamma (Magikarp)\nAbility: Swift Swim\n- Splash\n- Tackle\n\nDelta (Magikarp)\nAbility: Swift Swim\n- Splash'];
async function create(r:ReturnType<typeof recipients>,teams?:string[]){const generate=Teams.generate;let count=0;if(teams)Teams.generate=()=>Teams.import(teams[count++])!;try{return await PipelineIntegrationSession.create({...base,knowledge_recipients:r});}finally{Teams.generate=generate;}}
function check(s:PipelineIntegrationSession,r:ReturnType<typeof recipients>){
 for(const p of owners){const pair=read(s,r[p]),descriptor=pair.projection.request,request=env(s).getRequest(p)!.raw as any;
  checkNativeOwnerActiveOptionsProjection(pair.projection);assert.equal(pair.binding.request_descriptor,'owned-active-options/v1');assert.equal(pair.projection.result,'incomplete');
  assert.equal(descriptor.schema,'owned-active-options/v1');assert.equal(descriptor.cursor,pair.binding.prefix_cursor);
  assert.equal(descriptor.sequence,s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(p),p).boundaries.at(-1)!.current!.sequence);
  assert.equal(descriptor.state,'ordinary_pp');assert.match(descriptor.subject,new RegExp('^'+p+':roster:[1-6]$'));
  const slot=+descriptor.subject.split(':').at(-1),actor=native(s)[p]!.pokemon.find(a=>a.set===native(s)[p]!.team[slot-1])!;assert.equal(actor,native(s)[p]!.active[0]);
  assert.equal(descriptor.options.length,request.active[0].moves.length);
  descriptor.options.forEach((row:any,i:number)=>{assert.equal(row.option_index,i+1);assert.equal(row.request_move_id,request.active[0].moves[i].id);assert.equal(row.request_move_label,request.active[0].moves[i].move);assert.equal(row.pp.value,actor.moveSlots[i].pp);assert.equal(row.max_pp.value,actor.moveSlots[i].maxpp);});
  assert.equal(pair.projection.current.find((f:any)=>f.property==='current_moves').state,'unknown');assert.throws(()=>s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(r[p]),r[p==='p1'?'p2':'p1']),/copied-or-stale/);
 }
}
test('P53 generated ordinary options held references and privacy',async()=>{
 const r=recipients(),s=await create(r);const initial=owners.map(p=>read(s,r[p])),bytes=JSON.stringify(initial),actors=owners.map(p=>native(s)[p]!.active[0]),slots=actors.map(a=>[...a.moveSlots]);
 try{
  check(s,r);await joint(s,'p1','switch 2','switch 2');check(s,r);
  await joint(s,'p1','switch 2','switch 2');check(s,r);
  for(const [i,p] of owners.entries()){const pair=read(s,r[p]);assert.equal(pair.projection.starting,initial[i].projection.starting);assert.notEqual(native(s)[p]!.active[0],actors[i]);assert.ok(native(s)[p]!.active[0].moveSlots.every(slot=>!slots[i].includes(slot)));assert.equal(pair.projection.request.subject,p+':roster:1');}
  assert.equal(JSON.stringify(initial),bytes);const ordinary=JSON.stringify({boundary:s.boundary,snapshot:(s as any).snapshot,diagnostics:env(s).diagnostics()});for(const key of ['owned-active-options','request_move_label','native-owner-active-options'])assert.ok(!ordinary.includes(key));
  const copy:any=structuredClone(read(s,r.p1).projection);copy.request.options[0].pp.value=copy.request.options[0].max_pp.value+1;copy.id=knowledgeIdentity(copy);assert.throws(()=>checkNativeOwnerActiveOptionsProjection(copy));
  const reason:any=structuredClone(read(s,r.p1).projection);reason.request.state='unsupported';reason.request.options=null;reason.request.reason='not_emitted';reason.id=knowledgeIdentity(reason);assert.throws(()=>checkNativeOwnerActiveOptionsProjection(reason),/native unsupported options/);
  const raw:any=structuredClone(read(s,r.p1).projection);raw.request.options[0].raw_request='forbidden';raw.id=knowledgeIdentity(raw);assert.throws(()=>checkNativeOwnerActiveOptionsProjection(raw));assert.throws(()=>s.readOwnerKnowledge(raw,r.p1),/copied-or-stale/);
  emit('generated',{both_owner_actual_writer_delivery_consumer:true,fresh_restored_actor_and_slot_references:true,two_literal_original_slot_reorders:true,starting_and_suffix_immutable:true,privacy:true});
 }finally{await s.close();}
});
test('P53 constructed zero decrement equal delivery and literal labels',async()=>{
 const transfer=NativeBirthEnrollment.prototype.transferRequestHealthActors;let r=recipients(),s:PipelineIntegrationSession|undefined;
 NativeBirthEnrollment.prototype.transferRequestHealthActors=function(e,b){transfer.call(this,e,b);b.p1!.active[0].deductPP('splash',b.p1!.active[0].moveSlots[0].pp);};
 try{s=await create(r,simple);check(s,r);const desc=read(s,r.p1).projection.request;assert.equal(desc.options[0].pp.value,0);assert.equal(desc.options[0].pp.state,'known');assert.ok(!s.boundary.perspectives.p1.observation.request!.legal_actions.available_indices.includes(0));emit('zero',{constructed_native_deductPP_before_writer:true,zero_not_absence:true,disabled_emitted_row_not_action_permission:true});}finally{NativeBirthEnrollment.prototype.transferRequestHealthActors=transfer;await s?.close();}
 r=recipients();s=await create(r,simple);
 try{const before=read(s,r.p1),pp=before.projection.request.options[0].pp.value;await joint(s,'p1','move 1','move 1');check(s,r);assert.equal(read(s,r.p1).projection.request.options[0].pp.value,pp-1);assert.equal(before.projection.request.options[0].pp.value,pp);const first=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1').deliveries.at(-1)!;
  for(let i=0;i<2;i++)await joint(s,'p1','switch 2','switch 2');check(s,r);const last=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1').deliveries.at(-1)!;assert.equal(last.source.request_record,first.source.request_record);assert.notEqual(last.delivery_reference,first.delivery_reference);assert.notEqual(last.source.producer_occurrence,first.source.producer_occurrence);assert.equal(read(s,r.p1).projection.starting,before.projection.starting);
  emit('decrement-equal',{constructed_successful_native_PP_decrement:true,equal_byte_fresh_delivery_distinct_namespace:true,prior_descriptor_inert:true});
 }finally{await s.close();}
 r=recipients();s=await create(r,['Unown\nAbility: Levitate\n- Hidden Power',simple[1]]);
 try{check(s,r);const row=read(s,r.p1).projection.request.options[0];assert.notEqual(row.request_move_label,native(s).p1!.active[0].moveSlots[0].move);assert.equal(row.request_move_label,(env(s).getRequest('p1')!.raw as any).active[0].moves[0].move);emit('decorated',{constructed_literal_native_label:true,label_not_slot_move:true,generated_reachability:'not-certified'});}finally{await s.close();}
});
for(const branch of ['locked','recharge','struggle','transform','maybe-locked'] as const)test('P53 constructed unsupported '+branch,async()=>{
 const transfer=NativeBirthEnrollment.prototype.transferRequestHealthActors,r=recipients();let s:PipelineIntegrationSession|undefined;
 NativeBirthEnrollment.prototype.transferRequestHealthActors=function(e,b){transfer.call(this,e,b);const actor=b.p1!.active[0];
  if(branch==='maybe-locked')actor.maybeLocked=true;
  if(branch==='locked')actor.addVolatile('lockedmove',actor,Dex.moves.get('outrage'));
  if(branch==='recharge')actor.addVolatile('mustrecharge');
  if(branch==='struggle')for(const slot of actor.moveSlots)actor.deductPP(slot.id,slot.pp);
  if(branch==='transform')actor.transformInto(b.p2!.active[0],Dex.moves.get('transform'));
 };
 try{s=await create(r,simple);const desc=read(s,r.p1).projection.request;assert.equal(desc.state,'unsupported');assert.equal(desc.options,null);assert.notEqual(desc.reason,'none');assert.equal(read(s,r.p1).projection.current.find((f:any)=>f.property==='current_moves').state,'unknown');emit(branch,{actual_constructed_native_branch:true,options_nullable_blocking:true,generated_reachability:'not-certified'});}finally{NativeBirthEnrollment.prototype.transferRequestHealthActors=transfer;await s?.close();}
});
test('P53 writer source substitution and prepared PP rollback',async()=>{
 const original=(OwnedRequestHealthHost.prototype as any).checkMove;
 for(const fault of ['return-copy','wrong-owner','array-copy','slot-copy','value']){
  let cause:Error|undefined;
  (OwnedRequestHealthHost.prototype as any).checkMove=function(capture:any,world:any){if(capture.owner==='p1'&&capture.move?.ordinary){const source=capture.move;if(fault==='return-copy')capture.request.active[0]={...source.data};if(fault==='wrong-owner')source.actor=world.battle.p2.active[0];if(fault==='array-copy')source.actor.moveSlots=[...source.actor.moveSlots];if(fault==='slot-copy')source.actor.moveSlots[0]={...source.actor.moveSlots[0]};if(fault==='value')source.rows[0].reference.pp--;}
   try{return original.call(this,capture,world);}catch(error){cause=error as Error;throw error;}};
  try{const expected=fault==='return-copy'||fault==='wrong-owner'?/foreign-active-binding/:fault==='value'?/altered-active-row/:/stale-active-slot/;await assert.rejects(create(recipients(),simple),expected);assert.match(cause?.message??'',expected);}finally{(OwnedRequestHealthHost.prototype as any).checkMove=original;}
 }
 const r=recipients(),s=await create(r,simple),prepare=OwnedRequestHealthHost.prototype.prepare,preflight=NativeOwnerKnowledgeController.prototype.preflight,close=LocalBattleEnv.prototype.close;
 const prior=s.boundary,handle=s.getOwnerKnowledgeHandle(r.p1),pair=read(s,r.p1),history=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1');let host:OwnedRequestHealthHost,key:object,cleanup=false;
 OwnedRequestHealthHost.prototype.prepare=function(...args){host=this;key=prepare.apply(this,args);(args[0] as any).battleStream.battle.p1.active[0].moveSlots[0].pp--;return key;};
 LocalBattleEnv.prototype.close=function(){if(this.id.includes('step-')){assert.throws(()=>host!.readPrepared(key!,'p1'),/foreign-preparation/);cleanup=true;}return close.call(this);};
 try{await assert.rejects(joint(s,'p1','move 1'),/stale-active-slot/);assert.ok(cleanup);assert.equal(s.boundary,prior);assert.equal(s.getOwnerKnowledgeHandle(r.p1),handle);assert.equal(read(s,r.p1),pair);assert.equal(s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1'),history);
  OwnedRequestHealthHost.prototype.prepare=prepare;LocalBattleEnv.prototype.close=close;
  NativeOwnerKnowledgeController.prototype.preflight=function(key){preflight.call(this,key);throw new Error('P53-final-barrier');};await assert.rejects(joint(s,'p1','move 1'),/P53-final-barrier/);assert.equal(read(s,r.p1),pair);NativeOwnerKnowledgeController.prototype.preflight=preflight;
  await joint(s,'p1','move 1');check(s,r);assert.equal(read(s,r.p1).projection.starting,pair.projection.starting);const last=s.getOwnerKnowledgeHandle(r.p1);await s.close();assert.throws(()=>s.readOwnerKnowledge(last,r.p1),/closed/);
  emit('source-rollback',{actual_copied_wrong_owner_row_array_slot_value_denials:true,post_preparation_PP_mutation_reject:true,revoked_before_cleanup:true,final_barrier_reject:true,committed_pair_history_retained:true,fresh_retry:true,close_denies:true});
 }finally{OwnedRequestHealthHost.prototype.prepare=prepare;NativeOwnerKnowledgeController.prototype.preflight=preflight;LocalBattleEnv.prototype.close=close;await s.close();}
});
test('P53 constructed no-active descriptors and terminal',async()=>{
 let r=recipients(),s=await create(r,['First (Snorlax)\nAbility: Immunity\n- Splash\n- Explosion\n\nHealer (Pawmot)\nAbility: Iron Fist\n- Revival Blessing\n- Splash\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash','Watcher (Giratina)\nAbility: Pressure\n- Splash\n\nWaitingReserve (Magikarp)\nAbility: Swift Swim\n- Splash']);
 const unavailable=(p:'p1'|'p2',state:string)=>{const pair=read(s,r[p]),desc=pair.projection.request;checkNativeOwnerActiveOptionsProjection(pair.projection);assert.equal(desc.state,state);assert.equal(desc.options,null);assert.equal(desc.subject,null);assert.equal(desc.reason,'not_emitted');};
 try{await joint(s,'p1','move 2');unavailable('p1','forced_switch');unavailable('p2','waiting');await s.stepForcedSwitch(choice(s,'p1','switch 2'));await joint(s,'p1','move 1');unavailable('p1','revival_selection');unavailable('p2','waiting');await s.stepRevival(choice(s,'p1','switch 2'));check(s,r);emit('no-active',{constructed_forced_Revival_wait:true,nullable_options_not_empty_repertoire:true});}finally{await s.close();}
 r=recipients();s=await create(r,['Mewtwo\nAbility: Pressure\n- Psystrike','Magikarp\nLevel: 1\nAbility: Swift Swim\n- Splash']);
 try{await joint(s,'p1','move 1');for(const p of owners){unavailable(p,'terminal');assert.equal(read(s,r[p]).projection.request.sequence,null);}emit('terminal',{actual_constructed_terminal:true,no_retained_PP_as_current:true});}finally{await s.close();}
});
