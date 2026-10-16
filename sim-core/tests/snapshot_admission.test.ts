import assert from 'node:assert/strict';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { snapshotRestorePolicy, assertBeliefForkPolicy, NativeObjectAssociation } from '../src/owner_identity_crosswalk';
import { LocalBattleEnv, EnvironmentManager } from '../src/env_manager';
import { PipelineIntegrationSession, projectPipelineProtocolPrefix } from '../src/pipeline_integration';
import { installedNativeProfile } from '../src/version_profile';
import { buildBeliefSnapshot } from '../src/belief_fork';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { projectObservableBattleState } from '../src/observable_state';
import { SEEDED_TRANSITION_SCHEMA_VERSION } from '../src/transition';
import type { StepResult, PlayerID } from '../src/types';
const owners = ['p1','p2'] as const;
const seed = [1,2,3,4];
const emit = (name: string, data: object) => console.log('P33_WITNESS '+JSON.stringify({name,...data}));
function actions(result: StepResult) { return Object.fromEntries(owners.map(p => {
  const r=result.requests[p]!; return [p,canonicalActionFromLegalAction(r,r.legal_actions.available_indices[0])];
})) as any; }
function observations(result: StepResult, prefix: string[]) { return Object.fromEntries(owners.map(p => [p,projectObservableBattleState({
  schema_version:'observable-battle-state/v1',source_kind:'sim_core',battle_id:result.env_id,perspective:p,snapshot_phase:'pre_decision',
  protocol_prefix:projectPipelineProtocolPrefix(prefix),
  view:result.views[p]!,request:result.requests[p]!,
})])) as any; }
const options = {view_players:[...owners], include_log_delta:true};
function wire(result: StepResult, snapshot: any, step_index=0, prefix: string[]=result.log_delta!) { return {schema_version:SEEDED_TRANSITION_SCHEMA_VERSION,snapshot,observations:observations(result,prefix),actions:actions(result),step_index}; }

test('P33 PRE fixed policy and held admission', async () => {
  assert.equal(snapshotRestorePolicy('0.11.10'),'legacy'); assert.equal(snapshotRestorePolicy('0.11.11'),'held-b2-required');
  assert.throws(()=>snapshotRestorePolicy('unknown'),/unsupported-runtime/);
  assertBeliefForkPolicy('0.11.10'); assert.throws(()=>assertBeliefForkPolicy('0.11.11'),/belief-fork-unsupported/);
  let s: PipelineIntegrationSession|undefined, legacy: LocalBattleEnv|undefined, checks=0;
  const admission=NativeObjectAssociation.prototype.assertRestoreAdmission, fromJSON=Battle.fromJSON;
  let reconstructions=0;
  Battle.fromJSON=function(...args:any[]) {reconstructions++; return (fromJSON as any).apply(this,args);};
  NativeObjectAssociation.prototype.assertRestoreAdmission=function(env,serialized,ticket) {
    checks++;const before=reconstructions;
    assert.throws(()=>admission.call(this,env,serialized,undefined),/restore-ticket/);
    assert.throws(()=>admission.call(this,env,serialized,{...ticket}),/restore-ticket/);
    assert.throws(()=>admission.call(this,{},serialized,ticket),/restore-ticket/);
    assert.throws(()=>admission.call(this,env,structuredClone(serialized),ticket),/admission-mismatch/);
    assert.equal(reconstructions,before);
    return admission.call(this,env,serialized,ticket);
  };
  try {
    s=await PipelineIntegrationSession.create({battle_id:'P33-held',format:'gen9randombattle',seed});
    const saved=structuredClone((s as any).snapshot.simulator_state);
    const a=Object.fromEntries(owners.map(p=>{const r=s!.boundary.perspectives[p].observation.request!;return [p,canonicalActionFromLegalAction(r,r.legal_actions.available_indices[0])];})) as any;
    await s.step(a); assert.equal(checks,1);
    legacy=new LocalBattleEnv('P33-legacy','gen9randombattle',seed);
    const restored=await legacy.resetFromSerialized(saved,options);
    assert.equal(restored.requests.p1?.side.length,6);
    const built=buildBeliefSnapshot(saved,restored.views.p1!,'p1','gen9randombattle',seed);
    assert.equal(built.snapshot.sides.length,2);
    emit('pre-policy',{target_policy_only:true,actual_old_held_session:true,actual_old_raw_restore_and_direct_belief:true,
      rejected_chain_controls_before_fromJSON:true,target_callers:'UNEXECUTED'});
  } finally {NativeObjectAssociation.prototype.assertRestoreAdmission=admission;Battle.fromJSON=fromJSON;await legacy?.close();await s?.close();}
});

test('P33 PRE live handle lifecycle', async () => {
  const manager=new EnvironmentManager();let id=manager.createEnv('gen9randombattle',seed).env_id;
  const make=(r: StepResult, ref: any, index=0)=>wire(r,ref,index,(manager as any).envs.get(id).logLines);
  try {
    let result=await manager.resetEnv(id,options);const ref=manager.captureSeededSnapshotEnv(id), held=make(result,JSON.parse(JSON.stringify(ref)));
    const bad=structuredClone(held);bad.snapshot.branch_id='branch-'+'0'.repeat(64);
    await assert.rejects(manager.stepSeededTransitionEnv(id,bad,options),/metadata/);
    const invalid=structuredClone(held);invalid.actions.p2.rqid=999;
    await assert.rejects(manager.stepSeededTransitionEnv(id,invalid,options));
    const next=await manager.stepSeededTransitionEnv(id,held,options);assert.notEqual(next.output_snapshot.snapshot_handle,ref.snapshot_handle);
    await assert.rejects(manager.stepSeededTransitionEnv(id,held,options),/Unknown/);
    const retry=make(next.step_result,next.output_snapshot,1);
    const advanced=await manager.stepSeededTransitionEnv(id,retry,options);
    assert.notEqual(advanced.output_snapshot.snapshot_handle,next.output_snapshot.snapshot_handle);
    const stale=make(advanced.step_result,advanced.output_snapshot,2);
    await manager.resetEnv(id,options);
    await assert.rejects(manager.stepSeededTransitionEnv(id,stale,options),/Unknown/);
    result=await manager.resetEnv(id,options);const pending=make(result,manager.captureSeededSnapshotEnv(id));
    const submit=LocalBattleEnv.prototype.stepWithCanonicalOptions;
    LocalBattleEnv.prototype.stepWithCanonicalOptions=async function(...args) {await submit.apply(this,args);throw new Error('P33-post-write');};
    try {await assert.rejects(manager.stepSeededTransitionEnv(id,pending,options),/P33-post-write/);}
    finally {LocalBattleEnv.prototype.stepWithCanonicalOptions=submit;}
    await assert.rejects(manager.stepSeededTransitionEnv(id,pending,options),/Unknown/);
    const closingRef=manager.captureSeededSnapshotEnv(id), closing=manager.closeEnv(id);
    await assert.rejects(manager.stepSeededTransitionEnv(id,{...held,snapshot:closingRef},options),/Unknown/);
    await closing;
    const restarted=new EnvironmentManager(), freshId=restarted.createEnv('gen9randombattle',seed).env_id;
    try {await restarted.resetEnv(freshId,options);restarted.captureSeededSnapshotEnv(freshId);await assert.rejects(restarted.stepSeededTransitionEnv(freshId,held,options),/Unknown/);}
    finally {await restarted.closeAll();}
    emit('pre-live-handles',{actual_old_runtime:true,json_copy_addressed_held_entry:true,preflight_retry:true,fresh_output_retry:true,
      consumed_reset_close_restart_and_post_write_revocation:true,restoration_authority:false});
  } finally {await manager.closeAll();}
});

// Activation must supply real owned native11 support. These selectors remain unexecuted PRE.
const live = String(installedNativeProfile().package_version)==='0.11.11';
test('P33 LIVE target raw and belief guards before effects',{skip:!live},async()=>{
  const fromJSON=Battle.fromJSON,generate=Teams.generate,close=LocalBattleEnv.prototype.close;
  let reconstruct=0,sample=0,dispose=0;
  Battle.fromJSON=function(...a:any[]){reconstruct++;return (fromJSON as any).apply(this,a);};
  Teams.generate=function(...a:any[]){sample++;return (generate as any).apply(this,a);};
  LocalBattleEnv.prototype.close=async function(){dispose++;return close.call(this);};
  const env=new LocalBattleEnv('P33-live','gen9randombattle',seed),manager=new EnvironmentManager();
  try {
    await assert.rejects(env.resetFromSerialized({__neural_terminal_request_history:{},__neural_active_request_overrides:{}}),/raw-restore-unsupported/);
    await assert.rejects(manager.forkBeliefEnv('missing','p1',seed),/belief-fork-unsupported/);
    assert.throws(()=>buildBeliefSnapshot({} as any,{} as any,'p1','gen9randombattle',seed),/belief-fork-unsupported/);
    assert.deepEqual([reconstruct,sample,dispose],[0,0,0]);assert.equal(manager.diagnostics().open_env_count,0);
  } finally {Battle.fromJSON=fromJSON;Teams.generate=generate;LocalBattleEnv.prototype.close=close;await env.close();await manager.closeAll();}
});

test('P33 LIVE held admission precedes probes and abandonment',{skip:!live},async()=>{
  const reset=LocalBattleEnv.prototype.resetFromSerialized, fromJSON=Battle.fromJSON;
  let s:PipelineIntegrationSession|undefined, probes=0, checked=0;
  Battle.fromJSON=function(...args:any[]){probes++;return (fromJSON as any).apply(this,args);};
  LocalBattleEnv.prototype.resetFromSerialized=async function(serialized,opts,ticket){
    const before=probes, occurrence=this.getLiveWorldOccurrence();
    await assert.rejects(reset.call(this,serialized,opts,undefined),/restore-ticket/);
    await assert.rejects(reset.call(this,serialized,opts,{...ticket}),/restore-ticket/);
    await assert.rejects(reset.call(this,structuredClone(serialized),opts,ticket),/admission-mismatch/);
    assert.equal(probes,before);assert.equal(this.getLiveWorldOccurrence(),occurrence);
    checked++;return reset.call(this,serialized,opts,ticket);
  };
  try {
    s=await PipelineIntegrationSession.create({battle_id:'P33-live-held',format:'gen9randombattle',seed});
    const held=owners.map(p=>s!.readOriginalOwnerHolding(s!.getOriginalOwnerHolding(p),p));
    const source=(s as any).environment as LocalBattleEnv, before=probes, occurrence=source.getLiveWorldOccurrence();
    await assert.rejects(reset.call(source,(s as any).snapshot.simulator_state),/restore-ticket/);
    assert.equal(probes,before);assert.equal(source.getLiveWorldOccurrence(),occurrence);
    const a=Object.fromEntries(owners.map(p=>{const r=s!.boundary.perspectives[p].observation.request!;return [p,canonicalActionFromLegalAction(r,r.legal_actions.available_indices[0])];})) as any;
    await s.step(a);assert.equal(checked,1);
    for(const [i,p] of owners.entries())assert.equal(s.readNativeObjectHolding(s.getNativeObjectHolding(p),p).original,held[i]);
  } finally {LocalBattleEnv.prototype.resetFromSerialized=reset;Battle.fromJSON=fromJSON;await s?.close();}
});
