import assert from 'node:assert/strict';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { PipelineIntegrationSession } from '../src/pipeline_integration';
import { OwnedRequestHealthHost } from '../src/owned_request_health';
import { NativeOwnerKnowledgeController } from '../src/native_owner_knowledge';
import { NativeBirthEnrollment, NativeObjectAssociation } from '../src/owner_identity_crosswalk';
import { LocalBattleEnv } from '../src/env_manager';
import { checkNativeOwnerHealthProjection, checkNativeOwnerProjection, knowledgeIdentity } from '../src/perspective_knowledge';
import { choice, joint, native, env } from './helpers/owner_selection_restore';
const owners = ['p1', 'p2'] as const;
const r = () => ({ p1: {}, p2: {} });
const base = { battle_id: 'P50', format: 'gen9randombattle', seed: [1,2,3,4], observation_schema_version: 'observable-battle-state/v2' as const };
const read = (s: PipelineIntegrationSession, recipient: object) => s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(recipient), recipient);
const health = (s: PipelineIntegrationSession, recipient: object, slot: number, property: string) => read(s, recipient).projection.current.find((f: any) => f.subject.endsWith(':roster:'+slot) && f.property === property);
const emit = (name: string, evidence: object) => console.log('P50_WITNESS '+JSON.stringify({name,...evidence}));
async function create(recipients: ReturnType<typeof r>, teams?: string[]) {
  const generate = Teams.generate; let calls=0;
  if (teams) Teams.generate = () => { const team=Teams.import(teams[calls++])!; for(const set of team) if(!Object.hasOwn(set,'item'))set.item=''; return team; };
  try {return await PipelineIntegrationSession.create({...base,knowledge_recipients:recipients});} finally {Teams.generate=generate;}
}
function check(s: PipelineIntegrationSession, recipients: ReturnType<typeof r>) {
  for(const owner of owners) {
    const pair=read(s,recipients[owner]), battle=native(s), side=battle[owner]!;
    checkNativeOwnerHealthProjection(pair.projection);assert.throws(()=>checkNativeOwnerProjection(pair.projection));
    assert.equal(pair.projection.result,'incomplete');assert.equal(pair.projection.request,null);
    assert.equal(pair.binding.request_adaptation,'owned_health/v1');assert.equal(pair.binding.request_descriptor,'not_adopted');
    for(const [i,set] of side.team.entries()) {
      const actor=side.pokemon.find(p=>p.set===set)!;assert.ok(actor);
      assert.equal(health(s,recipients[owner],i+1,'hp').value.data,actor.hp);
      assert.equal(health(s,recipients[owner],i+1,'fainted').value.data,actor.fainted);
      const status=health(s,recipients[owner],i+1,'status');
      if(actor.fainted){assert.equal(status.state,'unknown');assert.equal(status.reason,'not_emitted');}
      else if(actor.status)assert.equal(status.value.data,actor.status);
      else{assert.equal(status.state,'known_absent');assert.equal(status.value,null);}
    }
    for(const fact of pair.projection.current)if(fact.family!=='K05')assert.equal(fact.state,'unknown');
    assert.throws(()=>s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(recipients[owner]),recipients[owner==='p1'?'p2':'p1']),/copied-or-stale/);
  }
}
test('P50 generated health writer delivery restore and privacy',async()=>{
  const recipients=r(),s=await create(recipients),pin=Object.getOwnPropertyDescriptor(Battle.prototype,'getRequests');
  try {
    check(s,recipients);const projection=read(s,recipients.p1).projection;
    for(const fault of ['faint-absence','current-ability','bad-status','cursor']){const copy:any=structuredClone(projection);const fact=copy.current.find((f:any)=>f.property==='status');if(fault==='faint-absence'){fact.property='fainted';fact.state='known_absent';fact.value=null;fact.precision='not_applicable';}if(fault==='current-ability'){const a=copy.current.find((f:any)=>f.property==='ability');a.state='known';a.value={type:'text',data:'Pressure'};a.reason='none';a.precision='exact';a.observed_at=0;}if(fault==='bad-status'){fact.state='known';fact.value={type:'text',data:'garbage'};fact.reason='none';fact.precision='exact';}if(fault==='cursor')fact.observed_at=-1;copy.id=knowledgeIdentity(copy);assert.throws(()=>checkNativeOwnerHealthProjection(copy));}
    const first=owners.map(p=>read(s,recipients[p])),bytes=JSON.stringify(first);
    for(let n=0;n<2;n++){
      const step=await s.step({p1:choice(s,'p1','switch 2'),p2:choice(s,'p2','switch 2')});check(s,recipients);
      for(const [i,p] of owners.entries())assert.equal(read(s,recipients[p]).projection.starting,first[i].projection.starting);
      assert.equal(JSON.stringify(first),bytes);assert.deepEqual(Object.getOwnPropertyDescriptor(Battle.prototype,'getRequests'),pin);
      const ordinary=JSON.stringify({step,snapshot:(s as any).snapshot,diagnostics:env(s).diagnostics()});
      for(const key of ['owned_health','request_descriptor','request-health','original_slot'])assert.ok(!ordinary.includes(key));
    }
    const history=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1');assert.deepEqual(history.deliveries.map(d=>d.sequence),[0,1,2]);
    emit('generated',{both_owners:true,actual_writer_receipt_committed_consumer:true,two_held_reorders:true,starting_refs_and_suffix_immutable:true,privacy:true});
  } finally {await s.close();}
});
test('P50 constructed equal deliveries update forced Revival wait terminal',async()=>{
  let recipients=r(),s=await create(recipients,['Alpha (Snorlax)\nAbility: Immunity\n- Splash\n\nBeta (Blissey)\nAbility: Healer\n- Splash','Gamma (Snorlax)\nAbility: Immunity\n- Splash\n\nDelta (Blissey)\nAbility: Healer\n- Splash']);
  try{
    const first=owners.map(p=>s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(p),p).deliveries[0]);
    for(let n=0;n<2;n++)await joint(s,'p1','switch 2','switch 2');check(s,recipients);
    for(const [i,p] of owners.entries()){const last=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(p),p).deliveries[2];assert.equal(last.source.request_record,first[i].source.request_record);assert.notEqual(last.delivery_reference,first[i].delivery_reference);}
  }finally{await s.close();}
  recipients=r();s=await create(recipients,['First (Snorlax)\nAbility: Immunity\n- Splash\n- Explosion\n\nHealer (Pawmot)\nAbility: Iron Fist\n- Revival Blessing\n- Splash\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash','Watcher (Giratina)\nAbility: Pressure\n- Splash\n- Will-O-Wisp\n\nWaitingReserve (Magikarp)\nAbility: Swift Swim\n- Splash']);
  try{
    await joint(s,'p1','move 1','move 2');check(s,recipients);assert.equal(health(s,recipients.p1,1,'status').value.data,'brn');
    await joint(s,'p1','move 2');check(s,recipients);assert.equal(read(s,recipients.p1).binding.request_state,'forced_switch');assert.equal(read(s,recipients.p2).binding.request_state,'waiting');
    assert.equal(health(s,recipients.p1,1,'status').state,'unknown');assert.equal(health(s,recipients.p1,1,'fainted').value.data,true);
    await s.stepForcedSwitch(choice(s,'p1','switch 2'));await joint(s,'p1','move 1');check(s,recipients);assert.equal(read(s,recipients.p1).binding.request_state,'revival_selection');
    await s.stepRevival(choice(s,'p1','switch 2'));check(s,recipients);assert.equal(health(s,recipients.p1,1,'fainted').value.data,false);assert.equal(health(s,recipients.p1,1,'status').state,'known_absent');
  }finally{await s.close();}
  let association: NativeObjectAssociation;const commit=NativeObjectAssociation.prototype.prepareCommit;
  NativeObjectAssociation.prototype.prepareCommit=function(...args){association=this;return commit.apply(this,args);};
  recipients=r();s=await create(recipients,['Mewtwo\nLevel: 100\nAbility: Pressure\n- Psystrike','Magikarp\nLevel: 1\nAbility: Swift Swim\n- Splash']);
  try{await joint(s,'p1','move 1');for(const p of owners){const pair=read(s,recipients[p]);assert.equal(pair.binding.request_state,'terminal');assert.ok(pair.projection.current.filter((f:any)=>f.family==='K05').every((f:any)=>f.state==='unknown'&&f.reason==='not_emitted'));}
    const candidate=(s as any).newEnvironment('terminal-zero-capture') as LocalBattleEnv;
    try {const ticket=association!.prepareRestore(candidate,s.boundary,(s as any).snapshot);const terminal=await candidate.resetFromSerialized((s as any).snapshot.simulator_state,{include_wait_requests:true},ticket);assert.equal(terminal.requests.p1,null);assert.equal(terminal.requests.p2,null);}finally{await candidate.close();}
  }finally{NativeObjectAssociation.prototype.prepareCommit=commit;await s.close();}
  recipients=r();s=await create(recipients,['Snorlax\nAbility: Immunity\n- Splash\n\nBlissey\nAbility: Healer\n- Splash','Wobbuffet\nAbility: Shadow Tag\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash']);
  const received=OwnedRequestHealthHost.prototype.received;let updates=0;
  OwnedRequestHealthHost.prototype.received=function(...args){if(JSON.parse(args[2].request_json)?.update)updates++;return received.apply(this,args);};
  try{const before=read(s,recipients.p1);await assert.rejects(joint(s,'p1','switch 2'),/rejected-action/);assert.ok(updates>0);assert.equal(read(s,recipients.p1),before);await joint(s,'p1','move 1');check(s,recipients);}finally{OwnedRequestHealthHost.prototype.received=received;await s.close();}
  emit('constructed',{generated_reachability:'not-certified',equal_byte_fresh_commit:true,native_update_receipt_rejection_parent_retained:true,forced:true,Revival:true,waiting:true,terminal_health_unknown:true,actual_admitted_terminal_zero_capture:true,status_omission_vs_absence:true});
});
test('P50 source transfer and settled contradiction rollback retry',async()=>{
  const register=NativeBirthEnrollment.prototype.registerRequestHealthReceiver;
  for(const fault of ['frame','rows','owner']){
    let cause: Error | undefined;
    NativeBirthEnrollment.prototype.registerRequestHealthReceiver=function(receiver){register.call(this,{...receiver,enroll:(frame,e,b,rows)=>{try {receiver.enroll(fault==='frame'?{}:frame,e,b,fault==='rows'?{...rows}:fault==='owner'?{p1:rows.p2,p2:rows.p1}:rows);} catch(error) {cause=error as Error; throw error;}}});};
    try{await assert.rejects(create(r()),/settling\/v1\/simulator-error/);assert.match(cause?.message??'',/request-health\/v1\/foreign-transfer/);}finally{NativeBirthEnrollment.prototype.registerRequestHealthReceiver=register;}
  }
  const recipients=r(),s=await create(recipients),preflight=OwnedRequestHealthHost.prototype.preflight;
  const prior=s.boundary,old=read(s,recipients.p1),handle=s.getOwnerKnowledgeHandle(recipients.p1);
  const prepare=OwnedRequestHealthHost.prototype.prepare;let failedHost:OwnedRequestHealthHost,failedToken:object;
  OwnedRequestHealthHost.prototype.prepare=function(...args){const key=prepare.apply(this,args);return {...key};};
  await assert.rejects(joint(s,'p1','switch 2','switch 2'),/foreign-knowledge-binding/);assert.equal(read(s,recipients.p1),old);
  OwnedRequestHealthHost.prototype.prepare=function(...args){failedHost=this;failedToken=prepare.apply(this,args);const battle=(args[0] as any).battleStream.battle;battle.p1.pokemon[0].hp--;return failedToken;};
  try{
    await assert.rejects(joint(s,'p1','switch 2','switch 2'),/stale-settled-value/);assert.equal(s.boundary,prior);assert.equal(read(s,recipients.p1),old);assert.equal(s.getOwnerKnowledgeHandle(recipients.p1),handle);
    assert.throws(()=>failedHost!.readPrepared(failedToken!,'p1'),/foreign-preparation/);assert.throws(()=>failedHost!.readPrepared({...failedToken!},'p1'),/foreign-preparation/);
    OwnedRequestHealthHost.prototype.prepare=prepare;await joint(s,'p1','switch 2','switch 2');check(s,recipients);assert.equal(read(s,recipients.p1).projection.starting,old.projection.starting);
  }finally{OwnedRequestHealthHost.prototype.prepare=prepare;OwnedRequestHealthHost.prototype.preflight=preflight;await s.close();}
  emit('source',{actual_copied_frame_rows_wrong_owner_reject:true,actual_copied_health_token_reject:true,stale_settled_value_reject:true,unchanged_committed_pair:true,revoked_preparation:true,fresh_retry:true});
});
test('P50 scoped decode exceptions and final barrier rollback',async()=>{
  const recipients=r(),s=await create(recipients),decode=OwnedRequestHealthHost.prototype.decode,pin=Object.getOwnPropertyDescriptor(Battle.prototype,'getRequests');
  const prepare=OwnedRequestHealthHost.prototype.prepare,preflight=NativeOwnerKnowledgeController.prototype.preflight;let fault='throw';let currentHost:OwnedRequestHealthHost;
  OwnedRequestHealthHost.prototype.decode=function(e,t,op){
    currentHost=this;
    if(fault==='throw')return decode.call(this,e,t,()=>{op();throw new Error('P50-native-decode-throw');});
    if(fault==='foreign')return decode.call(this,e,t,()=>{op();return new Battle({formatid:'gen9randombattle'});});
    if(fault==='nested')return decode.call(this,e,t,()=>decode.call(this,e,t,op));
    return decode.call(this,e,t,op);
  };
  try{
    for(fault of ['throw','foreign','nested']){await assert.rejects(joint(s,'p1','switch 2','switch 2'),/P50-native-decode-throw|foreign-decoded-battle|foreign-or-nested-decode/);assert.deepEqual(Object.getOwnPropertyDescriptor(Battle.prototype,'getRequests'),pin);}
    const accept=NativeObjectAssociation.prototype.acceptRestore;
    NativeObjectAssociation.prototype.acceptRestore=function(...args){accept.apply(this,args);currentHost.cloneOverlay(args[0],args[2],'p1',{side:{id:'p1',pokemon:[]}});};
    fault='overlay';try {await assert.rejects(joint(s,'p1','switch 2','switch 2'),/foreign-overlay-occurrence/);}finally{NativeObjectAssociation.prototype.acceptRestore=accept;}
    OwnedRequestHealthHost.prototype.decode=decode;
    const old=read(s,recipients.p1),boundary=s.boundary;let preparedHost:OwnedRequestHealthHost,prepared:object,closedCheck=false;
    OwnedRequestHealthHost.prototype.prepare=function(...args){preparedHost=this;prepared=prepare.apply(this,args);return prepared;};
    NativeOwnerKnowledgeController.prototype.preflight=function(key){preflight.call(this,key);throw new Error('P50-final-preflight');};
    const close=LocalBattleEnv.prototype.close;
    LocalBattleEnv.prototype.close=function(){if(this.id.includes('step-')){assert.throws(()=>preparedHost!.readPrepared(prepared!,'p1'),/foreign-preparation/);closedCheck=true;}return close.call(this);};
    try{await assert.rejects(joint(s,'p1','switch 2','switch 2'),/P50-final-preflight/);assert.ok(closedCheck);assert.equal(s.boundary,boundary);assert.equal(read(s,recipients.p1),old);}finally{LocalBattleEnv.prototype.close=close;NativeOwnerKnowledgeController.prototype.preflight=preflight;}
    await joint(s,'p1','switch 2','switch 2');check(s,recipients);assert.deepEqual(Object.getOwnPropertyDescriptor(Battle.prototype,'getRequests'),pin);
  }finally{OwnedRequestHealthHost.prototype.decode=decode;OwnedRequestHealthHost.prototype.prepare=prepare;NativeOwnerKnowledgeController.prototype.preflight=preflight;await s.close();}
  emit('decode-barrier',{actual_throw_foreign_nested:true,actual_foreign_overlay_reject:true,descriptor_exact_finally:true,final_preflight_reject_before_install:true,revocation_before_cleanup:true,fresh_retry:true});
});
