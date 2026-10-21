import assert from 'node:assert/strict';
import test from 'node:test';
import {Battle,Teams,Dex} from 'pokemon-showdown';
import {extractChannelMessages} from 'pokemon-showdown/dist/sim/battle';
import {installedNativeProfile,assertNativeRuntimeProfile,NATIVE11_CONTEXT,HISTORICAL10_CONTEXT,runtimeData,loadInactiveTargetInventory,positiveFidelityScope} from '../src/version_profile';
import {PipelineIntegrationSession,validateHistoricalPipelineLinkedRecordBundle} from '../src/pipeline_integration';
import {canonicalActionFromLegalAction} from '../src/canonical_action';
import {validateRawProtocolRecord} from '../src/observable_state';
import {readFileSync,writeFileSync} from 'node:fs';
import path from 'node:path';
const root=path.resolve(__dirname,'../../..');
const emit=(name:string,data:any)=>{console.log('P38_WITNESS '+JSON.stringify({name,...data}));};

test('P38 installed provenance configuration and historical isolation',()=>{
 const p=installedNativeProfile();assert.equal(p.package_version,'0.11.11');assert.equal(p.reader,NATIVE11_CONTEXT);
 assert.throws(()=>assertNativeRuntimeProfile({...p}),/unowned-runtime-profile/);
 const fs=require('node:fs'),read=fs.readFileSync;
 fs.readFileSync=function(file:any,...args:any[]){const bytes=read.call(this,file,...args);if(String(file)===path.join(p.package_root,'package.json')){const row=JSON.parse(String(bytes));row.version='0.11.10';return JSON.stringify(row);}return bytes;};
 try{assert.throws(()=>installedNativeProfile(),/installed-runtime-mismatch/);}finally{fs.readFileSync=read;}

 assert.ok(p.entry.startsWith(path.join(root,'sim-core/node_modules/pokemon-showdown')+path.sep));
 const format=Dex.formats.get('gen9randombattle');assert.equal(format.mod,'gen9');assert.equal(format.team,'random');assert.equal(format.gameType,'singles');
 const inventory=loadInactiveTargetInventory();const sets=JSON.parse(readFileSync(path.join(p.package_root,'data/random-battles/gen9/sets.json'),'utf8'));
 assert.equal(Object.keys(sets).length,509);assert.equal(Object.values(sets).reduce((n:number,x:any)=>n+x.sets.length,0),879);
 assert.equal(inventory.adopted,false);assert.equal(positiveFidelityScope('native11','gen9randombattle'),false);
 assert.notEqual(runtimeData(NATIVE11_CONTEXT),runtimeData(HISTORICAL10_CONTEXT));
 assert.deepEqual(runtimeData(NATIVE11_CONTEXT).moves.get('hpice'),runtimeData(NATIVE11_CONTEXT).moves.get('Hidden Power Ice'));
 assert.equal(runtimeData(NATIVE11_CONTEXT).moves.get('hpice').exists,true);
 assert.deepEqual(runtimeData(NATIVE11_CONTEXT).species.get('urshifuss'),runtimeData(NATIVE11_CONTEXT).species.get('Urshifu'));

 const f=JSON.parse(readFileSync(path.join(root,'docs/planning/perspective-fidelity-prompt31-reader-fixtures.json'),'utf8'));
 validateHistoricalPipelineLinkedRecordBundle(f.bundle);
 emit('provenance-config',{package:{version:p.package_version,root:p.package_root,entry:p.entry,integrity:p.integrity},format:{mod:format.mod,team:format.team,gameType:format.gameType},static_species:509,static_sets:879,historical_reader:true,target_positive_fidelity:false});
});

test('P38 genuine generated joint held restore canary',async()=>{
 let session:PipelineIntegrationSession|undefined;let phase='creation';
 try {
  session=await PipelineIntegrationSession.create({battle_id:'P38-generated',format:'gen9randombattle',seed:[1,2,3,4]});
  const original=(['p1','p2'] as const).map(owner=>session!.readOriginalOwnerHolding(session!.getOriginalOwnerHolding(owner),owner));
  phase='joint-step-held-restore';
  const actions=Object.fromEntries((['p1','p2'] as const).map(owner=>{const req=session!.boundary.perspectives[owner].observation.request!;return [owner,canonicalActionFromLegalAction(req,req.legal_actions.available_indices[0])]})) as any;
  const result=await session.step(actions);
  for(const [i,owner] of (['p1','p2'] as const).entries())assert.equal(session.readNativeObjectHolding(session.getNativeObjectHolding(owner),owner).original,original[i]);
  emit('generated-canary',{phase:'completed',actual_generation:true,held_restore:true,revision:NATIVE11_CONTEXT.profile.revision,result_keys:Object.keys(result)});
 }catch(error){emit('generated-canary',{phase,actual_generation:true,held_restore:'UNPROVED',failure:String(error)});throw error;}
 finally{await session?.close();}
});

test('P38 native Natural Cure emitter audience and quarantine',()=>{
 const native=new Battle({formatid:'gen9customgame',seed:'1,2,3,4',p1:{name:'P1',team:Teams.import('Blissey\nAbility: Natural Cure\n- Splash\n\nPikachu\nAbility: Static\n- Splash')!},p2:{name:'P2',team:Teams.import('Magikarp\nAbility: Swift Swim\n- Splash')!}});
 try{
  native.makeChoices('team 12','team 1');
  native.p1.active[0].setStatus('par');native.makeChoices('switch 2','move 1');
  const expected='|-curestatus|p1a: Blissey|par|[from] ability: Natural Cure|[silent]';
  assert.equal(native.log.filter(x=>x.startsWith('|-curestatus|')).length,1);assert.ok(native.log.includes(expected));
  const routed=extractChannelMessages(native.log.join('\n'),[0,1,2]);for(const side of [0,1,2] as const)assert.ok(routed[side].includes(expected));
  validateRawProtocolRecord(expected,NATIVE11_CONTEXT);
  for(const record of [expected.replace('|[silent]',''),expected.replace('|[from] ability: Natural Cure|[silent]','|[silent]|[from] ability: Natural Cure'),expected+'|[silent]'])assert.throws(()=>validateRawProtocolRecord(record,NATIVE11_CONTEXT));
  for(const row of ['|-heal|p1a: Blissey|90/100|[from] ability: Regenerator','|cant|p1a: Blissey|move: Heal Block|Pollen Puff'])assert.doesNotThrow(()=>validateRawProtocolRecord(row,NATIVE11_CONTEXT));
  const stops=['|-prepare|p1a: Blissey|Chilly Reception|[premajor]','|-swapsideconditions'];
  for(const row of stops)assert.throws(()=>validateRawProtocolRecord(row,NATIVE11_CONTEXT),/prepared-family-unsupported|Unsupported raw/);
  writeFileSync(path.join(root,'docs/planning/perspective-fidelity-prompt38-natural-cure-live.json'),JSON.stringify({record:expected,audiences:[0,1,2],scope:'constructed lower-level customgame mechanic, not generated reachability'}));
  emit('natural-cure',{record:expected,audiences:[0,1,2],level:'actual-native-lower-level-constructed',generated_reachability:'UNPROVED',quarantines:stops.length});
 }finally{native.destroy();}
});
