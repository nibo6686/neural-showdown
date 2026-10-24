import assert from 'node:assert/strict';
import test from 'node:test';
import {Dex} from 'pokemon-showdown';
import {bornSession,playTo} from './helpers/born_session';
import {native,env} from './helpers/owner_selection_restore';
import {NativeBirthEnrollment,NativeObjectAssociation} from '../src/owner_identity_crosswalk';
import {NativeOwnerKnowledgeController} from '../src/native_owner_knowledge';
import {OwnedRequestHealthHost} from '../src/owned_request_health';
import {checkNativeOwnerMovesProjection,knowledgeIdentity} from '../src/perspective_knowledge';
const owners=['p1','p2'] as const;
const team='Alpha (Magikarp)\nAbility: Swift Swim\n- Splash\n- Tackle\n\nBeta (Magikarp)\nAbility: Swift Swim\n- Splash';
const recipients=()=>({p1:{},p2:{}});
const read=(s:any,r:object)=>s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(r),r).projection;
const create=(r:ReturnType<typeof recipients>,moves=true,teams={p1:team,p2:team})=>bornSession({teams,options:{battle_id:'W12',knowledge_recipients:r,...(moves?{knowledge_profile:'native-owner-moves/v1' as const}:{})}});
function controls(s:any,r:ReturnType<typeof recipients>){for(const owner of owners){
 const projection=read(s,r[owner]);checkNativeOwnerMovesProjection(projection);
 const raw:any=env(s).getRequest(owner)!.raw;
 const observation=s.boundary.perspectives[owner].observation.request!;
 assert.deepEqual(env(s).getRequest(owner)!.raw,JSON.parse(s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(owner),owner).deliveries.at(-1)!.source.request_json));
 raw.active?.[0].moves.forEach((m:any,i:number)=>{for(const key of ['id','move','pp','maxpp','target','disabled'])assert.equal(observation.active!.moves[i][key],m[key]);});
 const moves=projection.owned_moves,active=native(s)[owner]!.active[0];
 assert.equal(moves.owner,owner);assert.ok(moves.moves.every((m:any)=>m.subject.startsWith(owner+':')));
 if(projection.request.state==='ordinary_pp'){
  assert.equal(moves.option_links.length,raw.active[0].moves.length);
  for(const [i,option] of raw.active[0].moves.entries()){
   const slot=active.moveSlots[i];for(const property of ['pp','maxpp','target'])assert.equal(option[property],(slot as any)[property]);
   const row=moves.moves.find((m:any)=>m.subject===moves.option_links[i].subject);
   assert.equal(row.pp.value,option.pp);assert.equal(row.max_pp.value,option.maxpp);
  }
 }
}}

test('W1.2 both-owner born move leases delivery and legal decision callback',async()=>{
 const r=recipients(),s=await create(r);
 try{controls(s,r);const before=read(s,r.p1),subject=before.owned_moves.option_links[0].subject,slot=native(s).p1!.active[0].moveSlots[0];
  // The actual callback consumes only the addressed projection and current legal list.
  const decide=(owner:typeof owners[number])=>{
   const order=s.withOwnedDecisionInput(r[owner],input=>{
    const p=input.knowledge.projection,links=p.owned_moves.option_links;
    const score=(index:number)=>{const action=input.observation.request!.legal_actions.actions[index],link=links.find((l:any)=>action?.choice==='move '+l.option_index);return link?p.owned_moves.moves.find((m:any)=>m.subject===link.subject).pp.value:-1;};
    return [...input.legal_indices].sort((a,b)=>score(b)-score(a)||a-b);
   });
   return s.boundary.perspectives[owner].observation.request!.legal_actions.actions[order.indices[0]]!.choice;
  };
  assert.equal(decide('p1'),'move 1');await playTo(s,[{p1:decide('p1'),p2:decide('p2')}]);controls(s,r);
  assert.notEqual(native(s).p1!.active[0].moveSlots[0],slot);
  assert.equal(read(s,r.p1).owned_moves.option_links[0].subject,subject);
  assert.equal(read(s,r.p1).owned_moves.moves[0].pp.value,before.owned_moves.moves[0].pp.value-1);
  assert.deepEqual(read(s,r.p1).starting,before.starting);
 }finally{await s.close();}
});

test('W1.2 stale bench PP never-emitted unknown and equal-byte delivery',async()=>{
 const r=recipients(),s=await create(r);
 try{const initial=read(s,r.p1),subject=initial.owned_moves.moves[0].subject;
  assert.equal(initial.owned_moves.moves.find((m:any)=>m.subject.includes('roster:2:')).pp.state,'unknown');
  await playTo(s,[{p1:'move 1',p2:'move 1'}]);const pp=read(s,r.p1).owned_moves.moves.find((m:any)=>m.subject===subject).pp.value;
  const delivery=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1').deliveries.at(-1)!;
  await playTo(s,[{p1:'switch 2',p2:'switch 2'}]);let row=read(s,r.p1).owned_moves.moves.find((m:any)=>m.subject===subject);
  assert.equal(row.pp.value,pp);assert.equal(row.pp.freshness,'last_known');assert.equal(row.membership,'present');
  await playTo(s,[{p1:'switch 2',p2:'switch 2'}]);row=read(s,r.p1).owned_moves.moves.find((m:any)=>m.subject===subject);
  assert.equal(row.pp.freshness,'current');assert.equal(row.pp.value,pp);
  const last=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1').deliveries.at(-1)!;
  assert.equal(delivery.source.request_record,last.source.request_record);assert.notEqual(delivery.delivery_reference,last.delivery_reference);
  const projection=structuredClone(read(s,r.p1));projection.owned_moves.moves[0].pp.value=null;projection.id=knowledgeIdentity(projection);assert.throws(()=>checkNativeOwnerMovesProjection(projection));
 }finally{await s.close();}
});

test('W1.2 exact zero and omitted PP do not become defaults',async()=>{
 const transfer=NativeBirthEnrollment.prototype.transferRequestHealthActors,r=recipients();
 NativeBirthEnrollment.prototype.transferRequestHealthActors=function(e,b){transfer.call(this,e,b);for(const owner of owners){const a=b[owner]!.active[0];a.deductPP('splash',a.moveSlots[0].pp);}};
 let s:any;try{s=await create(r);controls(s,r);for(const owner of owners){const move=read(s,r[owner]).owned_moves.moves[0];assert.equal(move.pp.state,'known');assert.equal(move.pp.value,0);}}
 finally{NativeBirthEnrollment.prototype.transferRequestHealthActors=transfer;await s?.close();}
 const r2=recipients(),s2=await create(r2);try{
  const p=structuredClone(read(s2,r2.p1));delete p.owned_moves.moves[0].pp;p.id=knowledgeIdentity(p);assert.throws(()=>checkNativeOwnerMovesProjection(p));
 }finally{await s2.close();}
});

test('W1.2 default output byte parity and foreign copied stale handles reject',async()=>{
 const r=recipients(),s=await create(r,false),r2=recipients(),opt=await create(r2);
 try{
  assert.equal(read(s,r.p1).schema,'perspective-knowledge-consumer/native11-details-v1');
  assert.equal(read(s,r.p1).current.find((f:any)=>f.property==='current_moves').state,'unknown');
  assert.equal(JSON.stringify(s.boundary),JSON.stringify(opt.boundary));
  for(const owner of owners){const a=structuredClone(read(s,r[owner])),b=structuredClone(read(opt,r2[owner]));for(const p of ['id','schema','policy','required_profile','owned_moves']){delete a[p];delete b[p];}b.current=b.current.map((f:any)=>f.property==='current_moves'?a.current.find((v:any)=>v.property===f.property&&v.subject===f.subject):f);assert.equal(JSON.stringify(a),JSON.stringify(b));}
  const h=opt.getOwnerKnowledgeHandle(r2.p1);assert.throws(()=>opt.readOwnerKnowledge(h,r2.p2),/copied-or-stale/);assert.throws(()=>opt.readOwnerKnowledge({...h},r2.p1),/copied-or-stale/);
  await playTo(opt,[{p1:'move 1',p2:'move 1'}]);assert.throws(()=>opt.readOwnerKnowledge(h,r2.p1),/copied-or-stale/);
  const last=opt.getOwnerKnowledgeHandle(r2.p1);await opt.close();assert.throws(()=>opt.readOwnerKnowledge(last,r2.p1),/closed/);
 }finally{await s.close();await opt.close();}
});

test('W1.2 post-preparation rollback wrong parent reject and fresh retry',async()=>{
 const r=recipients(),s=await create(r),preflight=NativeOwnerKnowledgeController.prototype.preflight,prepare=NativeOwnerKnowledgeController.prototype.prepare;
 try{const boundary=s.boundary,h=s.getOwnerKnowledgeHandle(r.p1),p=read(s,r.p1);
  NativeOwnerKnowledgeController.prototype.preflight=function(t){preflight.call(this,t);throw new Error('W12-post-prepare');};
  await assert.rejects(playTo(s,[{p1:'move 1',p2:'move 1'}]),/W12-post-prepare/);assert.equal(s.boundary,boundary);assert.equal(s.getOwnerKnowledgeHandle(r.p1),h);assert.equal(read(s,r.p1),p);
  NativeOwnerKnowledgeController.prototype.preflight=preflight;
  NativeOwnerKnowledgeController.prototype.prepare=function(e,b,parent,...rest){return prepare.call(this,e,b,{...parent} as any,...rest);};
  await assert.rejects(playTo(s,[{p1:'move 1',p2:'move 1'}]),/parent/);assert.equal(read(s,r.p1),p);
  NativeOwnerKnowledgeController.prototype.prepare=prepare;await playTo(s,[{p1:'move 1',p2:'move 1'}]);controls(s,r);
 }finally{NativeOwnerKnowledgeController.prototype.preflight=preflight;NativeOwnerKnowledgeController.prototype.prepare=prepare;await s.close();}
});

test('W1.2 Transform interval blocks borrowed PP and qualified base reset resumes',async()=>{
 const r=recipients(),s=await create(r,true,{p1:'Ditto\nAbility: Limber\n- Transform\n- Splash\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash',p2:team});
 try{const base=read(s,r.p1).owned_moves.moves.map((m:any)=>m.subject);
  await playTo(s,[{p1:'move 1',p2:'move 1'}]);let moves=read(s,r.p1).owned_moves;
  assert.equal(moves.roster[0].incarnation_coverage,'blocked');assert.equal(moves.roster[0].reason,'unsupported_writer');assert.equal(moves.option_links.length,0);
  assert.deepEqual(moves.moves.filter((m:any)=>m.subject.includes('roster:1:')).map((m:any)=>m.subject),base.filter((m:string)=>m.includes('roster:1:')));
  assert.ok(moves.moves.filter((m:any)=>m.subject.includes('roster:1:')).every((m:any)=>m.membership==='suspended'&&m.pp.freshness==='last_known'));
  await playTo(s,[{p1:'switch 2',p2:'move 1'},{p1:'switch 2',p2:'move 1'}]);moves=read(s,r.p1).owned_moves;
  assert.equal(moves.roster[0].incarnation_coverage,'ordinary_base');assert.equal(moves.option_links[0].subject,base[0]);assert.equal(moves.moves[0].pp.freshness,'current');assert.equal(moves.moves[0].pp.value,15);
 }finally{await s.close();}
});

test('W1.2 same-label replacement and serializer coalescing reject authority',async()=>{
 const r=recipients(),s=await create(r),accept=NativeObjectAssociation.prototype.acceptRestore;let mutate=true;
 NativeObjectAssociation.prototype.acceptRestore=function(e,input,b,t){accept.call(this,e,input,b,t);if(mutate){const a=b.p1!.active[0],deduct=a.deductPP;Object.defineProperty(a,'deductPP',{configurable:true,value:function(...args:any[]){const result=(deduct as any).apply(a,args);a.moveSlots[0]={...a.moveSlots[0]};delete (a as any).deductPP;return result;}});mutate=false;}};
 try{
  const initial=read(s,r.p1).owned_moves.moves[0];await playTo(s,[{p1:'move 1',p2:'move 1'}]);let moves=read(s,r.p1).owned_moves;
  assert.deepEqual(moves.roster[0].current_moves.value,['splash','tackle']);assert.deepEqual(moves.roster[0].unbound_positions,[1]);
  assert.equal(moves.moves.find((m:any)=>m.subject===initial.subject).pp.freshness,'last_known');assert.ok(!moves.option_links.some((m:any)=>m.subject===initial.subject));
  NativeObjectAssociation.prototype.acceptRestore=accept;
  const before=s.boundary,held=read(s,r.p1);
  // Native decode coalesces equal-ID current/base objects, changing serialized shape.
  // Keep the existing fingerprint validator: this fixture cannot commit that restore.
  await assert.rejects(playTo(s,[{p1:'move 1',p2:'move 1'}]),/restore-mismatch/);
  assert.equal(s.boundary,before);assert.equal(read(s,r.p1),held);
 }finally{NativeObjectAssociation.prototype.acceptRestore=accept;await s.close();}
});

test('W1.2 waiting preserves stale PP and wrong decode permutation rejects',async()=>{
 const r=recipients(),s=await create(r,true,{p1:'Snorlax\nAbility: Immunity\n- Splash\n- Explosion\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash',p2:'Giratina\nAbility: Pressure\n- Splash\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash'});
 try{const before=read(s,r.p2).owned_moves.moves[0];await playTo(s,[{p1:'move 2',p2:'move 1'}]);const p=read(s,r.p2);assert.equal(p.request.state,'waiting');assert.equal(p.owned_moves.option_links.length,0);assert.equal(p.owned_moves.moves[0].pp.value,before.pp.value);assert.equal(p.owned_moves.moves[0].pp.freshness,'last_known');}
 finally{await s.close();}
 const r2=recipients(),s2=await create(r2),before=NativeObjectAssociation.prototype.beforeRestore;
 NativeObjectAssociation.prototype.beforeRestore=function(e,input,t){before.call(this,e,input,t);(input as any).sides[0].pokemon.reverse();};
 try{await assert.rejects(playTo(s2,[{p1:'move 1',p2:'move 1'}]),/altered-restore-node|decode|restore|permutation/);assert.equal(s2.boundary.step_index,0);}
 finally{NativeObjectAssociation.prototype.beforeRestore=before;await s2.close();}
});

test('W1.2 generated both-owner decision callbacks retain native request controls',async()=>{
 const {PipelineIntegrationSession}=await import('../src/pipeline_integration');
 const {observeBornSession}=await import('./helpers/born_session');
 const r=recipients(),s=await observeBornSession(()=>PipelineIntegrationSession.create({battle_id:'W12-generated',format:'gen9randombattle',seed:[5,6,7,8],knowledge_recipients:r,knowledge_profile:'native-owner-moves/v1'}));
 try{controls(s,r);for(const owner of owners){let scoreUsed=false;
  const order=s.withOwnedDecisionInput(r[owner],input=>{
   const data=input.knowledge.projection.owned_moves;
   assert.ok(data.roster.length===6&&data.option_links.length>0);assert.equal(input.knowledge.projection.owner,owner);
   const score=(index:number)=>{const action=input.observation.request!.legal_actions.actions[index],link=data.option_links.find((l:any)=>action?.choice==='move '+l.option_index),record=data.moves.find((m:any)=>m.subject===link?.subject);return record?.pp.state==='known'?record.pp.value:-1;};scoreUsed=true;
   return [...input.legal_indices].sort((a,b)=>score(b)-score(a)||a-b);
  });assert.ok(scoreUsed);assert.equal(new Set(order.indices).size,s.boundary.perspectives[owner].observation.request!.legal_actions.available_indices.length);
 }
 await playTo(s,[{p1:'switch 2',p2:'switch 2'}]);controls(s,r);
 }finally{await s.close();}
});

test('W1.2 copied roster emission after preparation rejects without publication',async()=>{
 for(const owner of owners){const r=recipients(),s=await create(r),prepare=OwnedRequestHealthHost.prototype.prepare,prior=read(s,r[owner]);
  OwnedRequestHealthHost.prototype.prepare=function(...args){const key=prepare.apply(this,args),battle=(args[0] as any).battleStream.battle,row=battle[owner].activeRequest.side.pokemon[0];row.moves=[...row.moves];return key;};
  try{await assert.rejects(playTo(s,[{p1:'move 1',p2:'move 1'}]),/stale-roster-trace/);assert.equal(read(s,r[owner]),prior);}
  finally{OwnedRequestHealthHost.prototype.prepare=prepare;await s.close();}
 }
});

test('W1.2 move oracle detects fabricated vectors incarnation and stale PP',async()=>{
 const {createKnowledgeDiff}=require('../../../tools/replay_repro/knowledge_diff.cjs');
 const r=recipients(),s=await create(r);
 const frames=()=>owners.map(owner=>({owner,step_index:s.boundary.step_index,knowledge:{projection:structuredClone(read(s,r[owner]))}}));
 try{const oracle=createKnowledgeDiff(s,{ownerMoves:true});oracle.compare(s,frames());assert.equal(oracle.result().mismatches,0);
  for(const kind of ['vector','incarnation','pp']){const f=frames(),moves=f[0].knowledge.projection.owned_moves;if(kind==='vector')moves.roster[0].current_moves.value[0]='invented';if(kind==='incarnation')moves.moves[0].incarnation=2;if(kind==='pp')moves.moves[0].pp.value++;
   const bad=createKnowledgeDiff(s,{ownerMoves:true});bad.compare(s,f);assert.ok(bad.result().mismatches>0,kind);}
  await playTo(s,[{p1:'switch 2',p2:'switch 2'}]);const f=frames();f[0].knowledge.projection.owned_moves.moves[0].pp.value--;oracle.compare(s,f);assert.ok(oracle.result().mismatches>0);
 }finally{await s.close();}
});
