const assert=require('node:assert/strict'),test=require('node:test');
const {BattleStream,Teams}=require('../node_modules/pokemon-showdown');
const {extractChannelMessages}=require('../node_modules/pokemon-showdown/dist/sim/battle');
const {PipelineIntegrationSession,projectPipelineProtocolPrefix}=require('../dist/src/pipeline_integration');
const {LocalBattleEnv}=require('../dist/src/env_manager');
const {PlayerStateExtractor}=require('../dist/src/state_extractor');
const {RequestDeliveryLedger}=require('../dist/src/request_delivery_ledger');
const {NativeObjectAssociation}=require('../dist/src/owner_identity_crosswalk');
const {canonicalActionFromLegalAction}=require('../dist/src/canonical_action');
const {NATIVE11_CONTEXT}=require('../dist/src/version_profile');
const owners=['p1','p2'],opts={include_wait_requests:true,view_players:owners,include_log_delta:true};
const env=s=>s.environment,history=(s,p)=>s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(p),p);
const rows=(e,p)=>e.inspectRequestEmissionTrace(e.getRequestEmissionTraceHandle(p),p);
const act=(s,p,choice)=>{const r=s.boundary.perspectives[p].observation.request;const a=r.legal_actions.actions.find(x=>x&&x.choice===choice);assert.ok(a,choice);return canonicalActionFromLegalAction(r,a.index,p);};
const emit=(name,data)=>console.log('P39_WITNESS '+JSON.stringify({name,...data}));
async function create(teams){const generate=Teams.generate;let count=0;if(teams)Teams.generate=()=>Teams.import(teams[count++]);try{return await PipelineIntegrationSession.create({battle_id:'P39',format:'gen9randombattle',seed:[1,2,3,4]});}finally{Teams.generate=generate;}}
function tap(){const push=BattleStream.prototype.pushMessage,consume=PlayerStateExtractor.prototype.consumeChunk;let seq=0;const produced=[],receipts=[];
 BattleStream.prototype.pushMessage=function(type,data){const row={stream:this,order:++seq,type,data};if(type==='update'){row.channels=extractChannelMessages(data,[0,1,2]);row.expect_requests=!this.battle.sentRequests;row.source_begin=this.battle.sentLogPos;row.source_end=row.source_begin+data.split('\n').length;}produced.push(row);return push.call(this,type,data);};
 PlayerStateExtractor.prototype.consumeChunk=function(chunk){receipts.push({tracker:this,order:++seq,chunk});return consume.call(this,chunk);};
 return {produced,receipts,restore(){BattleStream.prototype.pushMessage=push;PlayerStateExtractor.prototype.consumeChunk=consume;},assert(e){
 const sends=produced.filter(x=>x.stream===e.battleStream);
 for(const update of sends.filter(x=>x.type==='update'&&x.expect_requests)){const next=sends.filter(x=>x.order>update.order&&x.type==='sideupdate'&&x.data.slice(3).startsWith('|request|')).slice(0,2);assert.deepEqual(next.map(x=>x.data.slice(0,2)),owners,'actual update before both request producer calls');}
 for(const p of owners){const channel=p==='p1'?1:2,requests=sends.filter(x=>x.type==='sideupdate'&&x.data.startsWith(p+'\n|request|'));
 const expected=sends.filter(x=>x.type==='update'||x.type==='sideupdate'&&x.data.startsWith(p+'\n'));
 const received=receipts.filter(x=>x.tracker===e.players[p].tracker);
 assert.deepEqual(received.map(x=>x.chunk),expected.map(x=>x.type==='update'?x.channels[channel].join('\n'):x.data.slice(3)),'literal owner FIFO, including equal chunks');
 const matched=new Map(expected.map((x,i)=>[x,received[i]]));
 const privateLines=received.flatMap(x=>x.chunk.split('\n').filter(l=>l.startsWith('|request|')));
 assert.deepEqual(rows(e,p).map(x=>x.request_record),privateLines);
 for(const update of sends.filter(x=>x.type==='update'))for(const req of requests.filter(x=>x.order>update.order))assert.ok(matched.get(update).order<matched.get(req).order,'owner public FIFO before addressed request');
 }return sends;}};
}

test('P39 generated public order restore early return and equal native occurrence',async()=>{
 const t=tap(),restored=RequestDeliveryLedger.prototype.restored;let s,restoreChecks=0,equal;
 RequestDeliveryLedger.prototype.restored=function(e,result,parent){assert.equal(parent,s.boundary);const held=owners.map(p=>history(s,p));assert.throws(()=>restored.call(this,e,result,{...parent}),/foreign-parent/);const proof=restored.call(this,e,result,parent);for(const [i,p] of owners.entries()){assert.equal(history(s,p),held[i]);assert.equal(history(s,p).boundaries.at(-1).current,held[i].boundaries.at(-1).current);}for(const p of owners){const selected=rows(e,p).at(-1);assert.equal(selected.origin,'restore_reemit');assert.equal(selected.request_record,history(s,p).boundaries.at(-1).selected.request_record);}restoreChecks++;return proof;};
 try{s=await create();t.assert(env(s));const parent=s.boundary;await s.step();const e=env(s),sends=t.assert(e);assert.equal(restoreChecks,1);
 for(const p of owners){const h=history(s,p),ob=s.boundary.perspectives[p].observation;assert.equal(h.boundaries.at(-1).parent.observation_id,parent.perspectives[p].observation.observation_id);assert.deepEqual(ob.protocol_prefix,projectPipelineProtocolPrefix(e.logLines,NATIVE11_CONTEXT));assert.equal(ob.event_cursor,ob.protocol_prefix.length);}
 const before={p1:rows(e,'p1').length,p2:rows(e,'p2').length};assert.equal(e.battleStream.battle.sentLogPos,e.battleStream.battle.log.length);
 await e.battleStream.write('>eval battle.sendUpdates()');await e.stepWithOptions({},opts);for(const p of owners)assert.equal(rows(e,p).length,before[p]);
 await e.battleStream.write('>eval p1.emitRequest(p1.activeRequest); p2.emitRequest(p2.activeRequest)');await e.stepWithOptions({},opts);equal={};for(const p of owners){const r=rows(e,p),last=r.at(-1),prior=r.at(-2);assert.equal(last.request_record,prior.request_record);assert.equal(last.origin,'native_emission');assert.notEqual(last.emission_index,prior.emission_index);equal[p]={equal_text:true,receipt_fifo:last.receipt.owner_receipt_index};}t.assert(e);
 emit('generated-order',{generated:true,restoreChecks,public_updates:sends.filter(x=>x.type==='update').map(x=>({source_begin:x.source_begin,source_end:x.source_end,routed_public_lines:x.channels[0].length})),public_cursor:s.boundary.perspectives.p1.observation.event_cursor,trace_count:before.p1,early_return_emissions:0,equal_native:equal});
 }finally{RequestDeliveryLedger.prototype.restored=restored;t.restore();await s?.close();}
});

test('P39 prepared candidate rejection revokes tokens and preserves committed authority',async()=>{
 const prepare=RequestDeliveryLedger.prototype.prepare,prepareB2=NativeObjectAssociation.prototype.prepareCommit,close=LocalBattleEnv.prototype.close;let s,ledger,delivery,controller,b2,failedOccurrence,failedEnv,failedTrace,cleanupChecks=0;
 try{s=await create();const boundary=s.boundary,oldEnv=env(s),world=oldEnv.getLiveWorldOccurrence(),handles=owners.map(p=>s.getNativeObjectHolding(p)),old=owners.map((p,i)=>s.readNativeObjectHolding(handles[i],p)),hist=owners.map(p=>history(s,p));
 const first=Object.fromEntries(owners.map(p=>{const req=s.boundary.perspectives[p].observation.request;return [p,canonicalActionFromLegalAction(req,req.legal_actions.available_indices[0])]}));
 await assert.rejects(s.step({...first,p1:{...first.p1,rqid:999}}),/request ID/);assert.equal(oldEnv.getLiveWorldOccurrence(),world);
 LocalBattleEnv.prototype.close=function(...args){if(this===failedEnv){assert.throws(()=>ledger.commit(delivery),/foreign-or-stale/);assert.throws(()=>controller.commit(b2),/foreign-or-stale/);for(const [i,p] of owners.entries()){assert.equal(history(s,p),hist[i]);assert.equal(s.readNativeObjectHolding(handles[i],p),old[i]);}cleanupChecks++;const pending=close.apply(this,args);assert.throws(()=>this.inspectRequestEmissionTrace(failedTrace,'p1'),/unavailable|invalidated/);return pending;}return close.apply(this,args);};
 RequestDeliveryLedger.prototype.prepare=function(...a){const token=prepare.apply(this,a);if(a[3]){ledger=this;delivery=token;failedEnv=a[0];failedTrace=failedEnv.getRequestEmissionTraceHandle('p1');failedOccurrence=rows(a[0],'p1').at(-1).producer_occurrence;}return token;};
 NativeObjectAssociation.prototype.prepareCommit=function(...a){b2=prepareB2.apply(this,a);controller=this;throw Error('P39-after-both-prepared');};
 await assert.rejects(s.step(),/P39-after-both-prepared/);assert.equal(s.boundary,boundary);assert.equal(env(s),oldEnv);
 for(const [i,p] of owners.entries()){assert.equal(history(s,p),hist[i]);assert.equal(s.readNativeObjectHolding(handles[i],p),old[i]);}
 assert.throws(()=>controller.commit(b2),/foreign-or-stale/);assert.throws(()=>ledger.commit(delivery),/foreign-or-stale/);
 assert.equal(cleanupChecks,1);assert.equal(oldEnv.getLiveWorldOccurrence(),world);
 RequestDeliveryLedger.prototype.prepare=prepare;NativeObjectAssociation.prototype.prepareCommit=prepareB2;LocalBattleEnv.prototype.close=close;await s.step();
 for(const p of owners){assert.notEqual(history(s,p).boundaries.at(-1).selected.producer_occurrence,failedOccurrence);assert.equal(history(s,p).deliveries.at(-1).sequence,1);}
 emit('prepared-rollback',{actual_after_both_prepared:true,committed_histories_and_handles_preserved:true,discarded_tokens_reject:true,fresh_retry_occurrence:true,source_world_unwritten:true,synchronous_before_cleanup:true,preflight_retry_preserved:true,candidate_trace_revoked:true});
 }finally{RequestDeliveryLedger.prototype.prepare=prepare;NativeObjectAssociation.prototype.prepareCommit=prepareB2;LocalBattleEnv.prototype.close=close;await s?.close();}
});

test('P39 actual updated request terminal null and waiting classification',async()=>{
 const t=tap();let s;
 try{s=await create(['Snorlax\nAbility: Immunity\n- Splash\n\nBlissey\n- Splash','Wobbuffet\nAbility: Shadow Tag\n- Splash\n\nSnorlax\n- Splash']);const before=history(s,'p1'),boundary=s.boundary;
 await assert.rejects(s.step({p1:act(s,'p1','switch 2'),p2:act(s,'p2','move 1')}),/rejected-action/);
 const updates=t.produced.filter(x=>x.type==='sideupdate'&&x.data.startsWith('p1\n|request|')).map(x=>JSON.parse(x.data.slice('p1\n|request|'.length))).filter(x=>x?.update);
 assert.ok(updates.some(x=>x.active[0].trapped===true));assert.equal(history(s,'p1'),before);assert.equal(s.boundary,boundary);await s.step({p1:act(s,'p1','move 1'),p2:act(s,'p2','move 1')});t.assert(env(s));await s.close();s=undefined;
 const cases=[{label:'wait',foe:'Magikarp\nLevel: 1\n- Splash\n\nSnorlax\n- Splash',wait:true},{label:'terminal',foe:'Magikarp\nLevel: 1\n- Splash',wait:false}];
 const summaries=[];for(const c of cases){s=await create(['Mewtwo\nLevel: 100\nAbility: Pressure\n- Psystrike',c.foe]);await s.step({p1:act(s,'p1','move 1'),p2:act(s,'p2','move 1')});
 if(c.wait){const row=history(s,'p1').boundaries.at(-1);assert.equal(JSON.parse(row.selected.request_json).wait,true);assert.equal(s.boundary.perspectives.p1.observation.request.wait,true);assert.ok(s.boundary.perspectives.p2.observation.request.force_switch);}
 else for(const p of owners){const h=history(s,p),row=h.boundaries.at(-1);assert.equal(row.current,null);assert.equal(row.selected,null);assert.equal(h.deliveries.length,1);assert.equal(s.boundary.perspectives[p].observation.request,null);}
 t.assert(env(s));summaries.push({case:c.label,kind:s.boundary.kind,waiting_side_action_created:false});await s.close();s=undefined;}
 emit('constructed-classifications',{generated_reachability:'UNPROVED',native_updatedRequest:true,update_flag_retained:true,update_rejection_parent_preserved:true,cases:summaries});
 }finally{t.restore();await s?.close();}
});

test('P39 equal literal requests commit fresh deliveries through real transitions',async()=>{
 const teams=['Alpha (Snorlax)\nAbility: Immunity\n- Splash\n\nBeta (Blissey)\nAbility: Healer\n- Splash',
 'Gamma (Snorlax)\nAbility: Immunity\n- Splash\n\nDelta (Blissey)\nAbility: Healer\n- Splash'];let s;
 try{s=await create(teams);
 const originalHandles=owners.map(p=>s.getOriginalOwnerHolding(p));
 const originals=owners.map((p,i)=>s.readOriginalOwnerHolding(originalHandles[i],p));
 const deliveryHandles=owners.map(p=>s.getRequestDeliveryHandle(p));
 const initialHistories=owners.map(p=>history(s,p));const boundaries=[s.boundary];
 for(let i=0;i<2;i++){
  const actions=Object.fromEntries(owners.map(p=>[p,act(s,p,'switch 2')]));
  const result=await s.step(actions);assert.equal(result.boundary,s.boundary);assert.equal(s.boundary.kind,'joint_actionable');boundaries.push(s.boundary);
 }
 const evidence=[];
 for(const [i,p] of owners.entries()){
  const h=s.readRequestDeliveryHistory(deliveryHandles[i],p),initial=h.deliveries[0],middle=h.deliveries[1],returning=h.deliveries[2];
  assert.deepEqual(h.deliveries.map(x=>x.sequence),[0,1,2]);
  assert.equal(initial.source.request_record,returning.source.request_record,'exact unedited initial/returning native bytes');
  assert.notEqual(initial.source.request_record,middle.source.request_record);
  assert.notEqual(initial.delivery_reference,returning.delivery_reference);
  assert.notEqual(initial.source.producer_occurrence,returning.source.producer_occurrence);
  assert.equal(new Set(h.deliveries.map(x=>x.delivery_reference)).size,3);
  assert.equal(new Set(h.deliveries.map(x=>x.source.producer_occurrence)).size,3);
  for(let j=0;j<3;j++){
   const row=h.boundaries[j];assert.equal(row.current,h.deliveries[j]);assert.equal(row.selected,row.current.source);assert.equal(row.selected.origin,'native_emission');
   assert.equal(row.observation_id,boundaries[j].perspectives[p].observation.observation_id);assert.equal(row.branch_id,boundaries[j].branch_id);
   if(j){assert.deepEqual(row.parent,{observation_id:boundaries[j-1].perspectives[p].observation.observation_id,branch_id:boundaries[j-1].branch_id,step_index:boundaries[j-1].step_index});}
  }
  assert.equal(s.readOriginalOwnerHolding(originalHandles[i],p),originals[i]);
  assert.equal(s.readNativeObjectHolding(s.getNativeObjectHolding(p),p).original,originals[i]);
  assert.equal(initialHistories[i].deliveries.length,1);assert.equal(initialHistories[i].boundaries.length,1);
  assert.equal(h.deliveries[0],initialHistories[i].deliveries[0]);assert.equal(h.boundaries[0],initialHistories[i].boundaries[0]);
  evidence.push({owner:p,initial_return_bytes_equal:true,literal_bytes:Buffer.byteLength(initial.source.request_record),initial_sequence:initial.sequence,return_sequence:returning.sequence,intermediate_differs:true,parent_joins:true,earlier_history_retained:true});
 }
 emit('equal-committed-native',{level:'actual-session-constructed-distinct-name-species-joint-switches',generated_reachability:'UNPROVED',equal_pair:[0,2],sequences:[0,1,2],distinct_delivery_references:true,distinct_native_occurrences:true,held_originals_retained:true,owners:evidence});
 }finally{await s?.close();}
});
