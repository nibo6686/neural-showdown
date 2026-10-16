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
  protocol_prefix:projectPipelineProtocolPrefix(prefix,installedNativeProfile().reader),
  view:result.views[p]!,request:result.requests[p]!,
},installedNativeProfile().reader)])) as any; }
const options = {view_players:[...owners], include_log_delta:true};
function wire(result: StepResult, snapshot: any, step_index=0, prefix: string[]=result.log_delta!) { return {schema_version:SEEDED_TRANSITION_SCHEMA_VERSION,snapshot,observations:observations(result,prefix),actions:actions(result),step_index}; }

test('P38 LIVE managed handle lifecycle', async () => {
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
    emit('target-live-handles',{actual_target_runtime:true,json_copy_addressed_held_entry:true,preflight_retry:true,fresh_output_retry:true,
      consumed_reset_close_restart_and_post_write_revocation:true,restoration_authority:false});
  } finally {await manager.closeAll();}
});
