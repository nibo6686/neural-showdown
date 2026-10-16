import assert from 'node:assert/strict';
import test from 'node:test';
import {Teams} from 'pokemon-showdown';
import {extractChannelMessages} from 'pokemon-showdown/dist/sim/battle';
import {validateRawProtocolRecord} from '../src/observable_state';
import {NATIVE11_CONTEXT,HISTORICAL10_CONTEXT,REPLAY_COMPAT_CONTEXT} from '../src/version_profile';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {constructed,checked,choice,joint,emit,holding,other,parentFault,publish,rollback,reseal,native} from './helpers/owner_selection_restore';
for(const [actor,healer] of [['p1','Pawmot'],['p2','Rabsca']] as const)test('P42 constructed revival B2 '+actor,async()=>{
 const s=await constructed(actor,healer);
 try{
  await joint(s,actor,'move 1','move 2');assert.equal(s.boundary.perspectives[actor].observation.view.self_team[0].status,'brn');
  await joint(s,actor,'move 2');assert.equal(s.boundary.kind,'one_sided_forced_switch');
  await s.stepForcedSwitch(choice(s,actor,'switch 2'));
  await joint(s,actor,'move 1');assert.equal(s.boundary.kind,'one_sided_revival');assert.equal(s.boundary.perspectives[other(actor)].observation.request!.wait,true);
  const first=s.boundary.perspectives[actor].observation.view.self_team.find(p=>p.name==='First')!;assert.equal(first.fainted,true);
  const action=choice(s,actor,'switch 2');assert.equal(action.kind,'revive');const run=()=>s.stepRevival(action);
  await assert.rejects(s.stepRevival({...action,player:other(actor)}),/unsupported-forced-switch-boundary/);
  await parentFault(s,run);if(actor==='p1')await rollback(s,run);
  const orders={ [actor]:[2,1,3],[other(actor)]:[1,2] } as any;
  const result=await checked(s,run,orders);assert.deepEqual(Object.keys(result.record_bundles),[actor]);publish(result.record_bundles[actor]);
  const expected='|-heal|'+actor+': First|50/100|[from] move: Revival Blessing';
  for(const p of ['p1','p2'] as const){assert.ok(s.boundary.perspectives[p].observation.protocol_prefix.includes(expected));const team=p===actor?s.boundary.perspectives[p].observation.view.self_team:s.boundary.perspectives[p].observation.view.opponent_team;const healed=team.find(p=>p.name==='First')!;assert.equal(healed.fainted,false);assert.equal(healed.status,null);assert.equal(healed.active,false);assert.ok(healed.hp_ratio!>0&&healed.hp_ratio!<=0.5);}
  const channels=extractChannelMessages(native(s).log.join('\n'),[0,1,2]);
  const secret=native(s)[actor]!.pokemon[1].getHealth().secret,privateHeal=expected.replace('50/100',secret);
  const ownChannel=actor==='p1'?1:2,waitingChannel=actor==='p1'?2:1;
  assert.ok(channels[ownChannel].includes(privateHeal));assert.ok(channels[0].includes(expected));assert.ok(channels[waitingChannel].includes(expected));assert.ok(!channels[waitingChannel].includes(privateHeal));
  if(actor==='p1'){const secretLeak=structuredClone(result.record_bundles[actor]);secretLeak.successor_observation.protocol_prefix=secretLeak.successor_observation.protocol_prefix.map((r:string)=>r===expected?privateHeal:r);reseal(secretLeak);publish(secretLeak,/Public health evidence mismatch.*private HP/i);}
  const falseOutcome=structuredClone(result.record_bundles[actor]);falseOutcome.successor_observation.view.self_team.find((p:any)=>p.name==='First').fainted=true;reseal(falseOutcome);publish(falseOutcome,/health.*mismatch|fainted|faint/i);
  if(actor==='p1')for(const [condition,hpText,ratio,status,fainted] of [['1/500','1/500',1/500,null,false],['200/400 brn','200/400',0.5,'brn',false],['0 fnt','0',0,null,true]] as const){
    const forged=structuredClone(result.record_bundles[actor]);const o=forged.successor_observation;
    const row=o.view.self_team.find((p:any)=>p.name==='First')!,req=o.request.side.find((p:any)=>p.ident===actor+': First')!;
    Object.assign(row,{hp_text:hpText,hp_ratio:ratio,status,fainted,active:false});req.condition=condition;req.active=false;reseal(forged);
    publish(forged,/Public health evidence mismatch.*Revival bench outcome/i);
  }
  if(actor==='p1'){
    const forged=structuredClone(result.record_bundles[actor]);const o=forged.successor_observation;
    o.protocol_prefix.push('|-status|p1a: First|brn');o.event_cursor=o.protocol_prefix.length;
    const row=o.view.self_team.find((p:any)=>p.name==='First')!,req=o.request.side.find((p:any)=>p.ident==='p1: First')!;
    Object.assign(row,{hp_text:'1/500',hp_ratio:1/500,status:'brn',fainted:false,active:false});req.condition='1/500 brn';reseal(forged);
    publish(forged,/Public health evidence mismatch.*Revival bench outcome/i);
  }
  const returning={ [actor]:[1,2,3],[other(actor)]:[1,2] } as any;
  await checked(s,()=>joint(s,actor,'switch 2'),returning);await checked(s,()=>joint(s,actor,'move 1'),returning);
  emit('revival-'+actor,{level:'actual-constructed-creation-through-native-revival-held-restore',healer,waiting:other(actor),selected_original_slot:1,selected_party_slot:2,orders,returning_orders:returning,heal:expected,actor_only_publication:true,silent_status_faint_clear:true,ordinary_continuation:true});
 }finally{await s.close();}
});
test('P42 target Pawmot Rabsca generated selector source routes',()=>{
 const gen:any=Teams.getGenerator('gen9randombattle','1,2,3,4');
 for(const species of ['Pawmot','Rabsca']){
  const set=gen.randomSet(species,{},true);assert.ok(set.moves.map((m:string)=>m.toLowerCase().replace(/[^a-z]/g,'')).includes('revivalblessing'));emit('selector-'+species,{level:'actual-constrained-target-randomSet',species,moves:set.moves,ability:set.ability,full_generated_team_witness:'UNEXECUTED'});
 }
});

test('P42 finite Revival grammar and unrelated quarantine',()=>{
 const publicHeal='|-heal|p1: First|50/100|[from] move: Revival Blessing';
 const secretHeal=publicHeal.replace('50/100','201/403');
 for(const line of [publicHeal,secretHeal])validateRawProtocolRecord(line,NATIVE11_CONTEXT);
 const malformed=[publicHeal.replace('p1: First','p1a: First'),publicHeal.replace('50/100','51/100'),publicHeal.replace('50/100','50/100 brn'),publicHeal+'|[silent]',publicHeal+'|[from] move: Revival Blessing',publicHeal.replace('p1: First','p3: First')];
 for(const line of malformed)assert.throws(()=>validateRawProtocolRecord(line,NATIVE11_CONTEXT),/Malformed raw -heal record/);
 const siblings=[publicHeal.replace('Revival Blessing','Recover'),publicHeal.replace('move: Revival Blessing','ability: Regenerator'),publicHeal.replace('Revival Blessing','Healing Wish'),publicHeal.replace('|[from] move: Revival Blessing','')];
 for(const line of siblings)assert.throws(()=>validateRawProtocolRecord(line,NATIVE11_CONTEXT),/prepared-family-unsupported\/heal-failure/);
 validateRawProtocolRecord(publicHeal,HISTORICAL10_CONTEXT);assert.throws(()=>validateRawProtocolRecord(publicHeal,REPLAY_COMPAT_CONTEXT),/prepared-family-unsupported\/heal-failure/);
 const script=`import json,sys
from neural.protocol_contract import validate_protocol_record
from neural.version_profile import NATIVE11_CONTEXT
a=json.load(sys.stdin)
for r in a['positive']:validate_protocol_record(r,reader_rules=NATIVE11_CONTEXT)
for kind in ('malformed','siblings'):
 for r in a[kind]:
  try:validate_protocol_record(r,reader_rules=NATIVE11_CONTEXT)
  except ValueError as e: assert ('Malformed raw -heal record' if kind=='malformed' else 'prepared-family-unsupported/heal-failure') in str(e),str(e)
  else:raise AssertionError('negative accepted')
print('P42 Python finite heal positives/malformed/quarantine PASS')`;
 const py=spawnSync(process.env.PYTHON || (process.platform==='win32'?'D:/Anaconda/envs/neuralgpu/python.exe':'python3'),['-c',script],{env:{...process.env,PYTHONPATH:path.resolve(__dirname,'../../../trainer/src')},input:JSON.stringify({positive:[publicHeal,secretHeal],malformed,siblings}),encoding:'utf8',timeout:30000});assert.equal(py.status,0,py.stderr);console.log(py.stdout.trim());emit('finite-heal-grammar',{public:'50/100',transport:'floor(maxHP/2)/maxHP',malformed:malformed.length,unrelated_quarantines:siblings.length,python:true});
});
