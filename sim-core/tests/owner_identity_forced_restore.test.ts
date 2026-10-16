import assert from 'node:assert/strict';
import test from 'node:test';
import {Dex} from 'pokemon-showdown';
import {canonicalActionFromLegalAction} from '../src/canonical_action';
import {PipelineIntegrationSession} from '../src/pipeline_integration';
import {constructed,checked,choice,joint,emit,holding,other,parentFault,publish,rollback,reseal} from './helpers/owner_selection_restore';
for(const actor of ['p1','p2'] as const)test('P42 constructed forced B2 '+actor,async()=>{
 const s=await constructed(actor);
 try{
  await joint(s,actor,'move 2');assert.equal(s.boundary.kind,'one_sided_forced_switch');assert.equal(s.boundary.perspectives[other(actor)].observation.request!.wait,true);
  assert.deepEqual(holding(s,actor).original_slots,[1,2,3]);
  const action=choice(s,actor,'switch 2'),run=()=>s.stepForcedSwitch(action);
  await assert.rejects(s.stepForcedSwitch({...action,player:other(actor)}),/unsupported-forced-switch-boundary/);
  await parentFault(s,run);if(actor==='p1')await rollback(s,run);
  const expected={ [actor]:[2,1,3],[other(actor)]:[1,2] } as any;
  const result=await checked(s,run,expected);assert.deepEqual(Object.keys(result.record_bundles),[actor]);publish(result.record_bundles[actor]);
  const privateRow=structuredClone(result.record_bundles[actor]);privateRow.successor_observation.view.opponent_team[0].original_slots=[1];reseal(privateRow);publish(privateRow,/public schema|unsupported|unexpected|unknown|keys|private/i);
  await checked(s,()=>joint(s,actor,'move 2'),expected);
  emit('constructed-forced-'+actor,{level:'actual-constructed-creation-KO-held-restoration',actor,waiting:other(actor),literal_orders:expected,actor_only_publication:true,parent_fault:true,ordinary_continuation:true});
 }finally{await s.close();}
});
test('P42 genuine generated KO forced B2',async()=>{
 const s=await PipelineIntegrationSession.create({battle_id:'P42-generated-KO',format:'gen9randombattle',seed:[101,202,303,404],observation_schema_version:'observable-battle-state/v2'});let steps=0;
 try{
  while(steps<20&&s.boundary.kind==='joint_actionable'){const actions=Object.fromEntries((['p1','p2'] as const).map(p=>{const req=s.boundary.perspectives[p].observation.request!;const attack=req.legal_actions.actions.filter(a=>a?.kind==='move'&&Dex.moves.get(a!.move!).basePower>0&&!Dex.moves.get(a!.move!).selfSwitch&&!Dex.moves.get(a!.move!).forceSwitch).sort((a,b)=>Dex.moves.get(b!.move!).basePower-Dex.moves.get(a!.move!).basePower)[0];assert.ok(attack,'bounded non-pivot damaging choice');return [p,canonicalActionFromLegalAction(req,attack.index)];}));await s.step(actions as any);steps++;}
  assert.equal(s.boundary.kind,'one_sided_forced_switch');assert.ok(s.boundary.perspectives.p1.observation.protocol_prefix.some(r=>r.startsWith('|faint|')));
  const actor=s.boundary.perspectives.p1.observation.request!.force_switch?'p1':'p2',waiting=other(actor);
  const old=[1,2,3,4,5,6],waitorder=[1,2,3,4,5,6];assert.deepEqual(holding(s,actor).original_slots,old);assert.deepEqual(holding(s,waiting).original_slots,waitorder);
  const request=s.boundary.perspectives[actor].observation.request!,a=request.legal_actions.actions.find(a=>a?.kind==='switch')!;assert.ok(a);
  const slot=a.slot!,expectedOrder=old.slice();[expectedOrder[0],expectedOrder[slot-1]]=[expectedOrder[slot-1],expectedOrder[0]];
  const result=await checked(s,()=>s.stepForcedSwitch(choice(s,actor,a.choice)),{[actor]:expectedOrder,[waiting]:waitorder} as any);
  assert.deepEqual(Object.keys(result.record_bundles),[actor]);publish(result.record_bundles[actor]);await s.step();
  emit('generated-KO',{level:'actual-unmodified-target-generated-session',steps,actor,original_orders:{[actor]:expectedOrder,[waiting]:waitorder},ordinary_continuation:true});
 }catch(e){emit('generated-KO-blocker',{steps,boundary:s.boundary.kind,error:String(e),generated_KO_restoration:'UNPROVED'});throw e;}finally{await s.close();}
});
