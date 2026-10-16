import assert from 'node:assert/strict';
import test from 'node:test';
import {Teams} from 'pokemon-showdown';
import {PipelineIntegrationSession} from '../src/pipeline_integration';
import {OwnedRequestHealthHost} from '../src/owned_request_health';
import {NativeOwnerKnowledgeController} from '../src/native_owner_knowledge';
import {LocalBattleEnv} from '../src/env_manager';
import {checkNativeOwnerIdentifiersProjection,knowledgeIdentity} from '../src/perspective_knowledge';
import {choice,joint,native,env} from './helpers/owner_selection_restore';
const owners=['p1','p2'] as const;
const recipients=()=>({p1:{},p2:{}});
const read=(s:PipelineIntegrationSession,r:object)=>s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(r),r);
const emit=(name:string,data:object)=>console.log('P54_WITNESS '+JSON.stringify({name,...data}));
const basic=['Alpha (Magikarp) @ Leftovers\nAbility: Swift Swim\n- Splash\n\nBeta (Magikarp)\nAbility: Swift Swim\n- Splash','Gamma (Magikarp)\nAbility: Swift Swim\n- Splash\n\nDelta (Magikarp) @ Leftovers\nAbility: Swift Swim\n- Splash'];
async function create(r:ReturnType<typeof recipients>,teams?:string[]){const generate=Teams.generate;let count=0;if(teams)Teams.generate=()=>Teams.import(teams[count++])!;try{return await PipelineIntegrationSession.create({battle_id:'P54',format:'gen9randombattle',seed:[1,2,3,4],knowledge_recipients:r});}finally{Teams.generate=generate;}}
const fact=(pair:any,p:string,slot:number,property:string,section='current')=>pair.projection[section].find((f:any)=>f.subject===p+':roster:'+slot&&f.property===property);
function check(s:PipelineIntegrationSession,r:ReturnType<typeof recipients>){for(const p of owners){const pair=read(s,r[p]);checkNativeOwnerIdentifiersProjection(pair.projection);assert.equal(pair.projection.result,'incomplete');const request=env(s).getRequest(p)!.raw as any;
 for(let slot=1;slot<=pair.projection.starting.find((f:any)=>f.property==='roster_size').value.data;slot++){
  const actor=native(s)[p]!.pokemon.find(a=>a.set===native(s)[p]!.team[slot-1])!;const row=request.side.pokemon[native(s)[p]!.pokemon.indexOf(actor)];
  for(const property of ['item','ability']){const f=fact(pair,p,slot,property);assert.equal(f.state,row[property]===''?(property==='item'?'known_absent':'unknown'):'known');if(row[property])assert.equal(f.value.data,row[property]);else assert.equal(f.value,null);if(f.state!=='unknown')assert.equal(f.observed_at,pair.binding.prefix_cursor);assert.equal(row[property],actor[property as 'item'|'ability']);}
  assert.equal(fact(pair,p,slot,'hp').value.data,actor.hp);
 }
 assert.equal(pair.projection.request.state,'ordinary_pp');assert.equal(pair.projection.current.find((f:any)=>f.property==='current_moves').state,'unknown');assert.throws(()=>s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(r[p]),r[p==='p1'?'p2':'p1']),/copied-or-stale/);
}}
test('P54 generated both owner identifiers held continuity and privacy',async()=>{const r=recipients(),s=await create(r);try{
 check(s,r);const first=owners.map(p=>read(s,r[p])),bytes=JSON.stringify(first),actors=owners.map(p=>native(s)[p]!.active[0]);await joint(s,'p1','switch 2','switch 2');check(s,r);await joint(s,'p1','switch 2','switch 2');check(s,r);
 for(const [i,p] of owners.entries()){assert.equal(read(s,r[p]).projection.starting,first[i].projection.starting);assert.notEqual(native(s)[p]!.active[0],actors[i]);}assert.equal(JSON.stringify(first),bytes);
 const ordinary=JSON.stringify({boundary:s.boundary,snapshot:(s as any).snapshot,diagnostics:env(s).diagnostics()});assert.ok(!ordinary.includes('native-owner-identifiers'));assert.ok(!ordinary.includes('native11-identifiers-v1'));
 const malformed:any=structuredClone(read(s,r.p1).projection);fact({projection:malformed},'p1',1,'ability').state='known_absent';fact({projection:malformed},'p1',1,'ability').value=null;fact({projection:malformed},'p1',1,'ability').precision='not_applicable';malformed.id=knowledgeIdentity(malformed);assert.throws(()=>checkNativeOwnerIdentifiersProjection(malformed));assert.throws(()=>s.readOwnerKnowledge(malformed,r.p1),/copied-or-stale/);
 emit('generated',{both_owners:true,actual_writer_delivery_consumer:true,fresh_B2_actors:true,starting_and_suffix_immutable:true,privacy:true,health_PP_preserved:true});
}finally{await s.close();}});
test('P54 constructed Trace consumption empty item and equal delivery',async()=>{let r=recipients(),s=await create(r,['Gardevoir\nAbility: Trace\n- Splash','Blissey\nAbility: Natural Cure\n- Splash']);try{
 check(s,r);const pair=read(s,r.p1);assert.equal(fact(pair,'p1',1,'ability','starting').value.data,'Trace');assert.equal(fact(pair,'p1',1,'ability').value.data,'naturalcure');assert.equal(fact(pair,'p1',1,'item','starting').state,'known_absent');assert.equal(fact(pair,'p1',1,'item').state,'known_absent');await joint(s,'p1','move 1');check(s,r);assert.equal(read(s,r.p1).projection.starting,pair.projection.starting);
 emit('Trace',{actual_constructed_native_initial_copy:true,original_Trace_current_naturalcure:true,base_effectiveness_suppression_not_adopted:true});
}finally{await s.close();}
 r=recipients();s=await create(r,['First (Magikarp) @ Focus Sash\nLevel: 1\nAbility: Swift Swim\n- Splash\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash','Mewtwo\nAbility: Pressure\n- Psystrike']);try{
 check(s,r);const before=read(s,r.p1),bytes=JSON.stringify(before);await joint(s,'p1','move 1');check(s,r);assert.equal(native(s).p1!.active[0].hp,1);assert.equal(fact(read(s,r.p1),'p1',1,'item').state,'known_absent');assert.equal(fact(before,'p1',1,'item','starting').value.data,'Focus Sash');assert.equal(read(s,r.p1).projection.starting,before.projection.starting);assert.equal(JSON.stringify(before),bytes);assert.ok(s.boundary.perspectives.p1.observation.protocol_prefix.some((line:string)=>line.includes('|-enditem|')&&line.includes('Focus Sash')));
 emit('consumption',{actual_constructed_Focus_Sash_turn:true,current_absence_no_cause_fact:true,immutable_original_item:true});
}finally{await s.close();}
 r=recipients();s=await create(r,basic);try{const first=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1').boundaries.at(-1)!.current!,pair=read(s,r.p1),literal=JSON.stringify(env(s).getRequest('p1')!.raw);await joint(s,'p1','switch 2','switch 2');await joint(s,'p1','switch 2','switch 2');check(s,r);const last=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1').boundaries.at(-1)!.current!;assert.equal(JSON.stringify(env(s).getRequest('p1')!.raw),literal);assert.notEqual(last.delivery_reference,first.delivery_reference);assert.notEqual(last.source.producer_occurrence,first.source.producer_occurrence);assert.equal(read(s,r.p1).projection.starting,pair.projection.starting);emit('equal',{actual_held_same_byte_fresh_delivery:true,namespace_distinct:true});}finally{await s.close();}});
test('P54 identifier source faults omissions and rollback',async()=>{
 const received=OwnedRequestHealthHost.prototype.received;
 OwnedRequestHealthHost.prototype.received=function(environment,emission,receipt){if(receipt.owner!=='p1')received.call(this,environment,emission,receipt);};
 try{const r=recipients(),s=await create(r,basic);try{const pair=read(s,r.p1);for(const property of ['item','ability']){const f=fact(pair,'p1',1,property);assert.equal(f.state,'unknown');assert.equal(f.reason,'unsupported_writer');}assert.equal(pair.projection.request.state,'unsupported');checkNativeOwnerIdentifiersProjection(pair.projection);}finally{await s.close();}}finally{OwnedRequestHealthHost.prototype.received=received;}
 const original=(OwnedRequestHealthHost.prototype as any).checkCapture;
 for(const fault of ['copy','foreign','value','unknown','label','missing','empty-ability']){let injected=false;
  (OwnedRequestHealthHost.prototype as any).checkCapture=function(c:any,w:any,settled:boolean){if(!injected&&c.owner==='p1'){injected=true;const row=c.rows[0],ids=row.identifiers;
   if(fault==='copy')c.request.side.pokemon[0]={...row.data};if(fault==='foreign')row.actor=w.battle.p2.active[0];if(fault==='value')row.data.item='choicescarf';
   if(fault==='unknown'){ids.item=row.data.item='fakeitem';ids.nativeItem=row.actor.item='fakeitem';}
   if(fault==='label'){ids.ability=row.data.ability='Swift Swim';ids.nativeAbility=row.actor.ability='Swift Swim';}
   if(fault==='missing'){delete row.data.item;delete row.data.ability;ids.itemPresent=false;ids.abilityPresent=false;ids.item=undefined;ids.ability=undefined;}
   if(fault==='empty-ability'){ids.ability=row.data.ability='';ids.nativeAbility=row.actor.ability='';}
  }return original.call(this,c,w,settled);};
  try{if(fault==='missing'||fault==='empty-ability'){const r=recipients(),s=await create(r,basic);try{const pair=read(s,r.p1);assert.equal(fact(pair,'p1',1,'ability').state,'unknown');assert.equal(fact(pair,'p1',1,'ability').reason,fault==='missing'?'not_emitted':'unsupported_writer');if(fault==='missing'){assert.equal(fact(pair,'p1',1,'item').state,'unknown');assert.equal(fact(pair,'p1',1,'item').value,null);}checkNativeOwnerIdentifiersProjection(pair.projection);}finally{await s.close();}}
   else await assert.rejects(create(recipients(),basic),fault==='copy'||fault==='foreign'?/altered-writer-row/:fault==='value'?/altered-identifier-row/:fault==='unknown'?/unknown-identifier/:/identifier-grammar/);
  }finally{(OwnedRequestHealthHost.prototype as any).checkCapture=original;}
 }
 // Omission/empty stimuli above are lower-level captured-row controls, not native gen9 emitter reachability.
 const r=recipients(),s=await create(r,basic),before=s.boundary,pair=read(s,r.p1),handle=s.getOwnerKnowledgeHandle(r.p1),history=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1'),prepare=OwnedRequestHealthHost.prototype.prepare,close=LocalBattleEnv.prototype.close,barrier=NativeOwnerKnowledgeController.prototype.preflight;let host:OwnedRequestHealthHost,key:object,cleanup=false;
 try{for(const property of ['item','ability'] as const){cleanup=false;OwnedRequestHealthHost.prototype.prepare=function(...a){host=this;key=prepare.apply(this,a);const actor=(a[0] as any).battleStream.battle.p1.active[0];actor[property]=property==='item'?'choicescarf':'pressure';return key;};LocalBattleEnv.prototype.close=function(){if(this.id.includes('step-')){assert.throws(()=>host!.readPrepared(key!,'p1'),/foreign-preparation/);cleanup=true;}return close.call(this);};await assert.rejects(joint(s,'p1','switch 2','switch 2'),/stale-identifier/);assert.ok(cleanup);assert.equal(s.boundary,before);assert.equal(read(s,r.p1),pair);assert.equal(s.getOwnerKnowledgeHandle(r.p1),handle);assert.equal(s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1'),history);}
  OwnedRequestHealthHost.prototype.prepare=prepare;LocalBattleEnv.prototype.close=close;NativeOwnerKnowledgeController.prototype.preflight=function(k){barrier.call(this,k);throw new Error('P54-final-barrier');};await assert.rejects(joint(s,'p1','switch 2','switch 2'),/P54-final-barrier/);assert.equal(read(s,r.p1),pair);NativeOwnerKnowledgeController.prototype.preflight=barrier;await joint(s,'p1','switch 2','switch 2');check(s,r);assert.equal(read(s,r.p1).projection.starting,pair.projection.starting);const final=s.getOwnerKnowledgeHandle(r.p1);await s.close();assert.throws(()=>s.readOwnerKnowledge(final,r.p1),/closed/);emit('faults',{actual_copy_foreign_altered_denials:true,lower_level_missing_empty_and_invalid_controls:true,item_and_ability_post_preparation_stale_reject:true,committed_pair_history_retained:true,revoked_before_cleanup:true,fresh_retry:true});
 }finally{OwnedRequestHealthHost.prototype.prepare=prepare;LocalBattleEnv.prototype.close=close;NativeOwnerKnowledgeController.prototype.preflight=barrier;await s.close();}
});
test('P54 constructed waiting forced Revival and terminal lifetime',async()=>{let r=recipients(),s=await create(r,['First (Snorlax)\nAbility: Immunity\n- Splash\n- Explosion\n\nHealer (Pawmot)\nAbility: Iron Fist\n- Revival Blessing\n- Splash\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash','Watcher (Giratina)\nAbility: Pressure\n- Splash\n\nWaitingReserve (Magikarp)\nAbility: Swift Swim\n- Splash']);
 const available=()=>{for(const p of owners){const pair=read(s,r[p]);checkNativeOwnerIdentifiersProjection(pair.projection);for(const f of pair.projection.current.filter((f:any)=>['item','ability'].includes(f.property)))assert.notEqual(f.state,'unknown');}};
 try{await joint(s,'p1','move 2');available();assert.equal(read(s,r.p2).projection.request.state,'waiting');await s.stepForcedSwitch(choice(s,'p1','switch 2'));await joint(s,'p1','move 1');available();assert.equal(read(s,r.p1).projection.request.state,'revival_selection');await s.stepRevival(choice(s,'p1','switch 2'));check(s,r);emit('wait',{actual_constructed_forced_Revival_wait_owned_rows:true});}finally{await s.close();}
 r=recipients();s=await create(r,['Mewtwo\nAbility: Pressure\n- Psystrike','Magikarp\nLevel: 1\nAbility: Swift Swim\n- Splash']);try{await joint(s,'p1','move 1');for(const p of owners){const pair=read(s,r[p]);checkNativeOwnerIdentifiersProjection(pair.projection);for(const f of pair.projection.current.filter((f:any)=>['item','ability'].includes(f.property))){assert.equal(f.state,'unknown');assert.equal(f.value,null);assert.equal(f.reason,'not_emitted');}}emit('terminal',{no_stale_identifier_carry_forward:true});}finally{await s.close();}
});
