import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {loadInactiveTargetInventory,runtimeData,historicalToID,selectReaderProfile} from '../src/version_profile';
const root=path.resolve(__dirname,'../../..');
const emit=(name:string,data:object)=>console.log('P35_WITNESS '+JSON.stringify({name,...data}));

test('P35 historical lookups fresh process without engine',()=>{
 const code=`const assert=require('assert/strict'),Module=require('module');let attempts=0;const load=Module._load;Module._load=function(request,...args){if(String(request).includes('pokemon-showdown')){attempts++;throw Error('native engine loading prohibited');}return load.call(this,request,...args)};
 const p=require('./sim-core/dist/src/version_profile'),helpers=require('./sim-core/dist/src/battle_helpers'),codec=require('./sim-core/dist/src/action_codec'),belief=require('./sim-core/dist/src/belief_state'),extract=require('./sim-core/dist/src/state_extractor');
 const f=require('./docs/planning/perspective-fidelity-prompt31-reader-fixtures.json').bundle;
 assert.deepEqual(helpers.resolveTypes('Pikachu',null,false),['Electric']);assert.deepEqual(helpers.resolveTypes('not-a-species',null,false),[]);
 assert.equal(p.runtimeData().moves.get('tbolt').type,'Electric');assert.deepEqual(p.runtimeData().moves.get('not-a-move'),{exists:false});
 assert.equal(helpers.moveTypeMultiplier('Electric',['Ground']),0);assert.equal(helpers.moveTypeMultiplier('Fire',['Grass']),2);assert.equal(helpers.moveTypeMultiplier('Missing',['Missing']),1);
 belief.validateObservableBattleState(f.input_observation);assert.equal(JSON.parse(belief.serializeBeliefState(f.input_belief)).belief_id,f.input_belief.belief_id);
 const request=codec.normalizeRequest('p1',f.input_observation.request.raw);assert.equal(request.rqid,f.input_observation.request.rqid);
 const tracker=new extract.PlayerStateExtractor('P35-static','gen9randombattle','p1');assert.ok(tracker);
 assert.equal(attempts,0);assert.throws(()=>p.runtimeData().species.get('Pikachu').types.push('Fire'),TypeError);
 console.log(JSON.stringify({engine_load_attempts:attempts,historical_belief_id:f.input_belief.belief_id,helper_reader_parity:true}));`;
 const proc=spawnSync(process.execPath,['-e',code],{cwd:root,encoding:'utf8',timeout:20000});assert.equal(proc.status,0,proc.stderr);
 emit('fresh-ts',{...JSON.parse(proc.stdout),fresh_process:true,full_target_coexistence:false});
});

test('P35 inactive inventory omission mutation guards',()=>{
 const candidate=loadInactiveTargetInventory();assert.equal(candidate.adopted,false);assert.equal(candidate.runtime_evidence,'UNEXECUTED');
 assert.equal(candidate.format_provenance.candidate_population.species.length,509);assert.equal(candidate.format_provenance.candidate_population.sets,879);
 assert.ok(candidate.condition_inventory.every((e:any)=>['unknown','raw-only'].includes(e.classification)));
 assert.ok(candidate.public_typed_state_lifecycle.entries.every((e:any)=>['unsupported-fail-closed','raw-only'].includes(e.disposition)));
 assert.throws(()=>selectReaderProfile({schema_version:'pipeline-linked-record/v1',transition:{simulator_revision:'sim-core@0.1.0+pokemon-showdown@0.11.11'}}),/unknown-revision/);
 const tmp=mkdtempSync(path.join(os.tmpdir(),'P35-assets-'));let rejects=0;
 const mutate=[(v:any)=>delete v.format_provenance.candidate_population,(v:any)=>v.simulator.source_revision='copied-old-revision',
 (v:any)=>v.format_provenance.effective_format.ruleset=[],(v:any)=>v.format_provenance.selector.source_sha256='0'.repeat(64),
 (v:any)=>v.condition_inventory[0].classification='represented',(v:any)=>v.public_typed_state_lifecycle.entries.pop(),(v:any)=>delete v.public_ability_effectiveness,(v:any)=>v.effect_discovery.package_wide_dynamic_callback_closure=true];
 try {
  for(const fn of mutate){const v=JSON.parse(JSON.stringify(candidate));fn(v);const f=path.join(tmp,String(rejects)+'.json');writeFileSync(f,JSON.stringify(v)+'\n');
   // A newly computed caller checksum is transport data, never the trusted candidate pin.
   const digest=createHash('sha256').update(readFileSync(f)).digest('hex');assert.equal(digest.length,64);
   assert.throws(()=>loadInactiveTargetInventory(f),/version-asset-integrity/);rejects++;}
  assert.throws(()=>loadInactiveTargetInventory(path.join(tmp,'missing.json')),/missing-version-asset/);
 }finally{rmSync(tmp,{recursive:true,force:true});}
 const vectors:any[]=['Pika-CHU',{id:'Mr. Mime'},{userid:'A_B'},{roomid:'Battle-1'},25,null,{},true];
 assert.deepEqual(vectors.map(historicalToID),['pikachu','mrmime','ab','battle1','25','','','']);
 emit('inactive-target',{static_species:509,static_sets:879,mutations_rejected:rejects,missing_file_rejected:true,adopted:false,target_runtime:'UNEXECUTED'});
});
