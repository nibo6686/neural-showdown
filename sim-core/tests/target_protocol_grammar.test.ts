import assert from 'node:assert/strict';
import test from 'node:test';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {validateRawProtocolRecord} from '../src/observable_state';
import {HISTORICAL10_CONTEXT,NATIVE11_GRAMMAR_CONTEXT,REPLAY_COMPAT_CONTEXT,readerContext,helperContext,
 loadPreparedProtocolAsset,selectReaderProfile} from '../src/version_profile';
const old='|-curestatus|p2a: Blissey|par|[from] ability: Natural Cure', target=old+'|[silent]';
const emit=(name:string,data:object)=>console.log('P36_WITNESS '+JSON.stringify({name,...data}));
test('P36 exact Natural Cure profiles',()=>{
 validateRawProtocolRecord(old,HISTORICAL10_CONTEXT);assert.throws(()=>validateRawProtocolRecord(target),/major-status source grammar/);
 validateRawProtocolRecord(target,NATIVE11_GRAMMAR_CONTEXT);assert.throws(()=>validateRawProtocolRecord(old,NATIVE11_GRAMMAR_CONTEXT),/major-status source grammar/);
 for(const row of [old,target])validateRawProtocolRecord(row,REPLAY_COMPAT_CONTEXT);
 const negatives=[old+'|[silent]|[silent]',old+'|[of] p1a: Regice',old+'|[silent]|[of] p1a: Regice',
 '|-curestatus|p2a: Blissey|par|[silent]|[from] ability: Natural Cure', '|-curestatus|p2a: Blissey|par|[silent]',
 target.replace('Natural Cure','Regenerator'),target.replace('Natural Cure','natural cure'),target.replace('p2a: Blissey','p2: Blissey'),
 target.replace('p2a: Blissey','p2b: Blissey'),target.replace('par|','???|'),target+'|extra'];
 for(const ctx of [NATIVE11_GRAMMAR_CONTEXT,REPLAY_COMPAT_CONTEXT])for(const row of negatives)
  assert.throws(()=>validateRawProtocolRecord(row,ctx),/Malformed raw .*record/);
 for(const ctx of [NATIVE11_GRAMMAR_CONTEXT,REPLAY_COMPAT_CONTEXT])assert.throws(()=>validateRawProtocolRecord(target.replace('-curestatus','curestatus'),ctx),/Unsupported raw protocol event: curestatus/);
 assert.throws(()=>readerContext(NATIVE11_GRAMMAR_CONTEXT),/unsupported-context/);
 assert.throws(()=>helperContext(NATIVE11_GRAMMAR_CONTEXT),/unsupported-context/);
 assert.throws(()=>readerContext(REPLAY_COMPAT_CONTEXT),/unsupported-context/);
 assert.throws(()=>selectReaderProfile({},'native11'),/native11-unadopted/);
 emit('exact-grammar',{negative_forms:negatives.length,profiles:3,target_runtime:'UNEXECUTED',silent_retained:true});
});
test('P36 immutable assets and unresolved families',()=>{
 const native=loadPreparedProtocolAsset('native11'),replay=loadPreparedProtocolAsset('replay-compat-v1');
 for(const [asset,ctx] of [[native,NATIVE11_GRAMMAR_CONTEXT],[replay,REPLAY_COMPAT_CONTEXT]] as const)for(const control of asset.protocol.valid_record_controls)validateRawProtocolRecord(control.record,ctx);
 assert.equal(native.adopted,false);assert.equal(replay.authority,false);assert.equal(replay.publication,'unsupported-without-persisted-profile-contract');
 assert.throws(()=>native.protocol.validation_rules.major_status.cure_forms.push({tags:['anything']}),TypeError);
 const tmp=mkdtempSync(path.join(os.tmpdir(),'P36-contract-'));let rejects=0;
 try{for(const profile of ['native11','replay-compat-v1'] as const){const original=loadPreparedProtocolAsset(profile);
  for(const change of [(x:any)=>x.adopted=true,(x:any)=>x.protocol.validation_rules.major_status.cure_forms.push({tags:['[silent]']}),
    (x:any)=>x.provenance.target_revision='copied-old-revision',(x:any)=>delete x.protocol.validation_rules.major_status]){
   const x=JSON.parse(JSON.stringify(original));change(x);const f=path.join(tmp,String(rejects)+'.json');writeFileSync(f,JSON.stringify(x));
   assert.throws(()=>loadPreparedProtocolAsset(profile,f),/version-asset-integrity/);rejects++;
  }
  assert.throws(()=>loadPreparedProtocolAsset(profile,path.join(tmp,'missing')),/missing-version-asset/);
 }}finally{rmSync(tmp,{recursive:true,force:true});}
 const blocked=[['|-ability|p1a: Regice|Insomnia|Clear Body|[from] move: Worry Seed|[of] p2a: Blissey','ability-setter'],
 ['|-activate|p2a: Blissey|ability: Mummy|p1a: Regice|[ability] Clear Body','ability-setter'],
 ['|-heal|p1a: Regice|90/100|[from] ability: Regenerator','heal-failure'],['|cant|p1a: Regice|move: Heal Block|Pollen Puff','heal-failure'],
 ['|-prepare|p1a: Regice|Chilly Reception|[premajor]','chilly-reception'],
 ['|-damage|p1a: Regice|80/100|[from] move: Whirlpool|[partiallytrapped]','partial-trap'],
 ['|-swapsideconditions','court-change'],['|-item|p1a: Regice|Leftovers|[from] ability: Magician|[of] p2a: Blissey','magician']];
 for(const ctx of [NATIVE11_GRAMMAR_CONTEXT,REPLAY_COMPAT_CONTEXT])for(const [row,family] of blocked)
  assert.throws(()=>validateRawProtocolRecord(row,ctx),new RegExp('prepared-family-unsupported/'+family));
 assert.throws(()=>validateRawProtocolRecord('|-sidestart|p1: Player|move: Stealth Rock',NATIVE11_GRAMMAR_CONTEXT),/candidate effect\/lifecycle semantics unproved/);
 for(const row of ['|editbattle|hp|p1a: Regice|1','|-zbroken|p1a: Regice'])assert.throws(()=>validateRawProtocolRecord(row,NATIVE11_GRAMMAR_CONTEXT),/Unsupported raw/);
 validateRawProtocolRecord('|-hint|Psychic Terrain doesn\'t affect airborne Pokémon.',NATIVE11_GRAMMAR_CONTEXT);
 validateRawProtocolRecord('|switch|p1a: Regice|Regice, L88|100/100',NATIVE11_GRAMMAR_CONTEXT);
 emit('assets-and-stops',{mutations_rejected:rejects,blocked_forms:blocked.length,raw_only_hint:true,live:'UNEXECUTED'});
});
