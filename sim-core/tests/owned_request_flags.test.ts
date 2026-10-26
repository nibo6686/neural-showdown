import assert from 'node:assert/strict';
import test from 'node:test';
import {bornSession,playTo} from './helpers/born_session';
import {NativeBirthEnrollment} from '../src/owner_identity_crosswalk';
import {OwnedRequestHealthHost} from '../src/owned_request_health';
import {checkNativeOwnerMovesProjection,knowledgeIdentity} from '../src/perspective_knowledge';
const owners=['p1','p2'] as const;
const team='Magikarp\nAbility: Swift Swim\n- Splash\n- Tackle\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash';
const recipients=()=>({p1:{},p2:{}});
const read=(s:any,r:object)=>s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(r),r).projection;
const create=(r:ReturnType<typeof recipients>,teams={p1:team,p2:team},opt=true)=>bornSession({teams,options:{battle_id:'W13',knowledge_recipients:r,...(opt?{knowledge_profile:'native-owner-moves/v1' as const}:{})}});
function check(s:any,r:ReturnType<typeof recipients>){
 for(const owner of owners){
  const p=read(s,r[owner]);checkNativeOwnerMovesProjection(p);
  const raw=JSON.parse(s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(owner),owner).deliveries.at(-1).source.request_json).active?.[0];
  const request=p.owned_moves.request;
  for(const [key,wire] of Object.entries({trapped:'trapped',maybe_trapped:'maybeTrapped',maybe_disabled:'maybeDisabled',maybe_locked:'maybeLocked'})){
   const fact=request.emitted_flags[key],present=!!raw&&Object.hasOwn(raw,wire);
   assert.equal(fact.subject,request.subject);assert.equal(fact.present,present);assert.equal(fact.value,present?raw[wire]:null);assert.equal(fact.state,present?'known':'unknown');
  }
  for(const [i,option] of (request.options??[]).entries()){
   const emitted=raw.moves[i],present=Object.hasOwn(emitted,'disabled');
   assert.equal(option.disabled.present,present);assert.equal(option.disabled.value,present?emitted.disabled:null);
  }
 }
}

test('W1.3 both-owner emitted flags and omitted flags retain literal scope',async()=>{
 const transfer=NativeBirthEnrollment.prototype.transferRequestHealthActors;
 NativeBirthEnrollment.prototype.transferRequestHealthActors=function(e,b){transfer.call(this,e,b);for(const owner of owners){const a=b[owner]!.active[0];a.maybeDisabled=true;a.maybeTrapped=true;a.moveSlots[1].disabled='hidden';}};
 const r=recipients();let s:any;
 try{s=await create(r);check(s,r);for(const owner of owners){const request=read(s,r[owner]).owned_moves.request;
  for(const key of ['maybe_disabled','maybe_locked','maybe_trapped']){assert.equal(request.emitted_flags[key].value,true);assert.equal(request.emitted_flags[key].affected_options,'unspecified');}
  assert.equal(request.options[1].disabled.value,false);assert.equal(request.emitted_flags.trapped.state,'unknown');
  assert.ok(read(s,r[owner]).owned_moves.moves.every((m:any)=>!Object.hasOwn(m,'maybe_disabled')));
 }}finally{NativeBirthEnrollment.prototype.transferRequestHealthActors=transfer;await s?.close();}
 const r2=recipients(),normal=await create(r2);try{check(normal,r2);for(const owner of owners)assert.ok(Object.values(read(normal,r2[owner]).owned_moves.request.emitted_flags).every((f:any)=>f.state==='unknown'&&f.value===null));}finally{await normal.close();}
});

test('W1.3 Choice restriction and typed public Encore cause',async()=>{
 const r=recipients(),s=await create(r,{p1:team.replace('Magikarp\n','Magikarp @ Choice Scarf\n'),p2:team});
 try{await playTo(s,[{p1:'move 1',p2:'move 1'}]);check(s,r);
  const request=read(s,r.p1).owned_moves.request;assert.equal(request.restriction.state,'known');assert.deepEqual(request.restriction.permitted_options,[1]);assert.equal(request.restriction.reason.state,'unknown');
  s.withOwnedDecisionInput(r.p1,input=>[...input.legal_indices]);
 }finally{await s.close();}
 const r2=recipients(),encore=await create(r2,{p1:team,p2:'Shuckle\nAbility: Sturdy\n- Encore\n- Splash\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash'});
 try{assert.equal(read(encore,r2.p1).owned_moves.request.restriction.reason.state,'unknown');await playTo(encore,[{p1:'move 1',p2:'move 1'}]);check(encore,r2);
  assert.deepEqual(read(encore,r2.p1).owned_moves.request.restriction.reason,{state:'known',value:'encore'});
 }finally{await encore.close();}
});

test('W1.3 Recharge and Struggle exact options allow canonical callbacks without possession',async()=>{
 const transfer=NativeBirthEnrollment.prototype.transferRequestHealthActors;
 for(const branch of ['recharge','struggle']){
  NativeBirthEnrollment.prototype.transferRequestHealthActors=function(e,b){transfer.call(this,e,b);for(const owner of owners){const a=b[owner]!.active[0];if(branch==='recharge')a.addVolatile('mustrecharge');else for(const slot of a.moveSlots)a.deductPP(slot.id,slot.pp);}};
  const r=recipients();let s:any;
  try{s=await create(r);check(s,r);for(const owner of owners){const p=read(s,r[owner]);assert.equal(p.request.state,'exact_options');assert.equal(p.request.options[0].request_move_id,branch);
   assert.equal(p.request.options[0].pp.state,'unknown');assert.equal(p.owned_moves.option_links.length,0);assert.ok(p.owned_moves.moves.every((m:any)=>m.reported_move_id!==branch));
   assert.equal(p.owned_moves.request.options[0].disabled.present,branch==='struggle');
   s.withOwnedDecisionInput(r[owner],(input:any)=>{assert.ok(input.legal_indices.some((i:number)=>input.observation.request.legal_actions.actions[i].choice===(branch==='recharge'?'default':'move 1')));return [...input.legal_indices];});
  }}finally{NativeBirthEnrollment.prototype.transferRequestHealthActors=transfer;await s?.close();}
 }
});

test('W1.3 Arena Trap emission and no-switch suppression stay distinct',async()=>{
 for(const reserve of [true,false]){
  const r=recipients(),s=await create(r,{p1:reserve?team:team.split('\n\n')[0],p2:'Dugtrio\nAbility: Arena Trap\n- Splash'});
  try{check(s,r);const trapped=read(s,r.p1).owned_moves.request.emitted_flags.trapped;
   assert.equal(trapped.state,'unknown');assert.equal(trapped.value,null);
   assert.equal(read(s,r.p1).owned_moves.request.emitted_flags.maybe_trapped.value,reserve?true:null);
  }finally{await s.close();}
 }
});

test('W1.3 locked emitted option permits decisions without a private cause',async()=>{
 const r=recipients(),s=await create(r,{p1:'Dragonite\nAbility: Multiscale\n- Outrage\n- Splash',p2:'Shuckle\nAbility: Sturdy\n- Splash'});
 try{await playTo(s,[{p1:'move 1',p2:'move 1'}]);check(s,r);const p=read(s,r.p1);
  assert.equal(p.request.state,'exact_options');assert.equal(p.request.options.length,1);assert.equal(p.request.options[0].request_move_id,'outrage');
  assert.equal(p.owned_moves.request.restriction.reason.state,'unknown');assert.equal(p.owned_moves.option_links.length,0);
  s.withOwnedDecisionInput(r.p1,input=>[...input.legal_indices]);
 }finally{await s.close();}
});

test('W1.3 default parity and copied foreign stale handles reject',async()=>{
 const r=recipients(),r2=recipients(),s=await create(r),plain=await create(r2,undefined,false);
 try{assert.equal(JSON.stringify(s.boundary),JSON.stringify(plain.boundary));
  assert.equal(read(plain,r2.p1).schema,'perspective-knowledge-consumer/native11-details-v1');
  const h=s.getOwnerKnowledgeHandle(r.p1);assert.throws(()=>s.readOwnerKnowledge({...h},r.p1));assert.throws(()=>s.readOwnerKnowledge(h,r.p2));
  await playTo(s,[{p1:'move 1',p2:'move 1'}]);assert.throws(()=>s.readOwnerKnowledge(h,r.p1));
  const p=structuredClone(read(s,r.p1));p.owned_moves.request.emitted_flags.trapped.value=false;p.id=knowledgeIdentity(p);assert.throws(()=>checkNativeOwnerMovesProjection(p));
 }finally{await s.close();await plain.close();}
});

test('W1.3 changed selected flag rejects atomically and oracle detects fabrication',async()=>{
 const r=recipients(),s=await create(r),prepare=OwnedRequestHealthHost.prototype.prepare;
 try{const before=read(s,r.p1),boundary=s.boundary;
  OwnedRequestHealthHost.prototype.prepare=function(...args){const key=prepare.apply(this,args);(args[0] as any).battleStream.battle.p1.activeRequest.active[0].maybeDisabled=true;return key;};
  await assert.rejects(playTo(s,[{p1:'move 1',p2:'move 1'}]),/altered-active-emission/);assert.equal(s.boundary,boundary);assert.equal(read(s,r.p1),before);
  OwnedRequestHealthHost.prototype.prepare=prepare;
  const {createKnowledgeDiff}=require('../../../tools/replay_repro/knowledge_diff.cjs');
  const frames=()=>owners.map(owner=>({owner,step_index:s.boundary.step_index,knowledge:{projection:structuredClone(read(s,r[owner]))}}));
  const good=createKnowledgeDiff(s,{ownerMoves:true});good.compare(s,frames());assert.equal(good.result().mismatches,0);
  const f=frames();f[0].knowledge.projection.owned_moves.request.options[0].disabled.value=true;
  const bad=createKnowledgeDiff(s,{ownerMoves:true});bad.compare(s,f);assert.ok(bad.result().mismatches>0);
 }finally{OwnedRequestHealthHost.prototype.prepare=prepare;await s.close();}
});
