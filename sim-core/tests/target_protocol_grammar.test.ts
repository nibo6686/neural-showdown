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
 assert.equal(selectReaderProfile({},'native11').id,'native11');
 emit('exact-grammar',{negative_forms:negatives.length,profiles:3,target_runtime:'UNEXECUTED',silent_retained:true});
});
test('P36 immutable assets and unresolved families',()=>{
 const native=loadPreparedProtocolAsset('native11'),replay=loadPreparedProtocolAsset('replay-compat-v1');
 for(const [asset,ctx] of [[native,NATIVE11_GRAMMAR_CONTEXT],[replay,REPLAY_COMPAT_CONTEXT]] as const)for(const control of asset.protocol.valid_record_controls) {
  if(ctx===NATIVE11_GRAMMAR_CONTEXT && control.record==='|-swapsideconditions') assert.throws(()=>validateRawProtocolRecord(control.record,ctx),/prepared-family-unsupported\/court-change/);
  else validateRawProtocolRecord(control.record,ctx);
 }
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
 for(const ctx of [NATIVE11_GRAMMAR_CONTEXT,REPLAY_COMPAT_CONTEXT])for(const [row,family] of blocked) {
  if(ctx===NATIVE11_GRAMMAR_CONTEXT && ['heal-failure','chilly-reception','partial-trap','magician'].includes(family)) assert.doesNotThrow(()=>validateRawProtocolRecord(row,ctx));
  else assert.throws(()=>validateRawProtocolRecord(row,ctx),new RegExp('prepared-family-unsupported/'+family));
 }
 assert.doesNotThrow(()=>validateRawProtocolRecord('|-sidestart|p1: Player|move: Stealth Rock',NATIVE11_GRAMMAR_CONTEXT));
 for(const row of ['|editbattle|hp|p1a: Regice|1','|-zbroken|p1a: Regice'])assert.throws(()=>validateRawProtocolRecord(row,NATIVE11_GRAMMAR_CONTEXT),/Unsupported raw/);
 validateRawProtocolRecord('|-hint|Psychic Terrain doesn\'t affect airborne Pokémon.',NATIVE11_GRAMMAR_CONTEXT);
 validateRawProtocolRecord('|switch|p1a: Regice|Regice, L88|100/100',NATIVE11_GRAMMAR_CONTEXT);
 emit('assets-and-stops',{mutations_rejected:rejects,blocked_forms:blocked.length,raw_only_hint:true,live:'UNEXECUTED'});
});


const corpusForms=[
 '|-enditem|p2a: Sableye|Leftovers|[silent]|[from] ability: Pickpocket|[of] p2a: Sableye',
 '|-curestatus|p2: Probopass|par|[msg]',
 '|-anim|p1a: Glimmora|Meteor Beam|p2a: Vikavolt|[miss]',
 '|-status|p1a: Scream Tail|slp|[from] move: Relic Song',
 '|teampreview|6',
];
test('native corpus emitter forms have nearby rejection controls',()=>{
 const negatives=[corpusForms[0].replace('[of] p2a: Sableye','[of] p1a: Weavile'),
  corpusForms[0].replace('[silent]|[from]','[from]'),corpusForms[1].replace('[msg]','[from] ability: Natural Cure'),
  corpusForms[1].replace('p2:','p2b:'),corpusForms[1]+'|extra',corpusForms[2]+'|[miss]',
  corpusForms[2].replace('[miss]','[MISS]'),corpusForms[2].replace('Meteor Beam','Imaginary Beam'),
  corpusForms[3].replace('|slp|','|par|'),corpusForms[3].replace('Relic Song','relic song'),
  '|teampreview|25','|teampreview|06','|teampreview|6|extra'];
 for(const row of corpusForms)validateRawProtocolRecord(row,NATIVE11_GRAMMAR_CONTEXT);
 for(const row of negatives)assert.throws(()=>validateRawProtocolRecord(row,NATIVE11_GRAMMAR_CONTEXT),/Malformed raw/);
 assert.throws(()=>validateRawProtocolRecord('|-swapsideconditions',NATIVE11_GRAMMAR_CONTEXT),/court-change/);
});
test('bench cure clears the named reserve without clearing the active status',async()=>{
 const {PlayerStateExtractor}=await import('../src/state_extractor');
 const {NATIVE11_CONTEXT}=await import('../src/version_profile');
 const extractor=new PlayerStateExtractor('bench-cure','gen9randombattle','p1',NATIVE11_CONTEXT);
 for(const row of ['|switch|p2a: Probopass|Probopass, L88|100/100 par',
  '|switch|p2a: Chansey|Chansey, L88|100/100 brn',corpusForms[1]])extractor.consumeChunk(row);
 const team=extractor.getView().opponent_team;
 assert.equal(team.find(p=>p.name==='Probopass')!.status,null);
 assert.equal(team.find(p=>p.name==='Chansey')!.status,'brn');
 assert.equal(team.find(p=>p.name==='Chansey')!.active,true);
});


test('additional corpus forms preserve source roles and finite payloads',()=>{
 const forms=[
  '|-item|p2a: Weavile|Assault Vest|[from] ability: Pickpocket|[of] p1a: Dewgong',
  '|-enditem|p1a: Golem|Custap Berry|[from] stealeat|[move] Bug Bite|[of] p2a: Scyther',
  '|-ability|p2a: Obliteryx|Opportunist|boost',
  '|-anim|p1a: Glimmora|Meteor Beam|p2: Basculin|[notarget]',
  '|teampreview|8',
  '|-hitcount|p2: Terapagos|10',
 ];
 const negatives=[forms[0].replace('p1a: Dewgong','p2a: Dewgong'),forms[1].replace('Custap Berry','Leftovers'),
  forms[1].replace('Bug Bite','Bite'),forms[2].replace('Opportunist','Illusion'),
  forms[3].replace('p2: Basculin','p1: Basculin'),forms[3].replace('p2: Basculin','p2a: Basculin'),forms[3].replace('[notarget]','[miss]'),
  forms[3]+'|[miss]','|-hitcount|p2: Terapagos|11'];
 for(const row of forms)validateRawProtocolRecord(row,NATIVE11_GRAMMAR_CONTEXT);
 for(const row of negatives)assert.throws(()=>validateRawProtocolRecord(row,NATIVE11_GRAMMAR_CONTEXT),/Malformed raw/);
 for(const row of ['|-start|p1a: Equilibra|Doom Desire','|-end|p2a: Jumbao|move: Doom Desire'])
  assert.throws(()=>validateRawProtocolRecord(row,NATIVE11_GRAMMAR_CONTEXT),/unclassified-effect-value/);
});
test('conditionless Illusion replacement preserves the appearance status until explicit clear',async()=>{
 const {PlayerStateExtractor}=await import('../src/state_extractor');
 const {NATIVE11_CONTEXT}=await import('../src/version_profile');
 const e=new PlayerStateExtractor('illusion-status','gen9randombattle','p1',NATIVE11_CONTEXT);
 for(const row of ['|switch|p2a: Falinks|Falinks, L80|100/100',
  '|-status|p2a: Falinks|par','|replace|p2a: Zoroark|Zoroark-Hisui, L80, F'])e.consumeChunk(row);
 let active=e.getView().opponent_team.find(p=>p.active)!;
 assert.equal(active.name,'Zoroark');assert.equal(active.status,'par');
 e.consumeChunk('|replace|p2a: Zoroark|Zoroark-Hisui, L80, F|90/100');
 active=e.getView().opponent_team.find(p=>p.active)!;
 assert.equal(active.status,null);
});


test('native Magician exact receiver and opposing donor roles, with unchanged replay quarantine',()=>{
 const row='|-item|p1a: Hoopa|Choice Scarf|[from] ability: Magician|[of] p2a: Porygon-Z';
 for(const source of ['p2a: Porygon-Z','p2: Porygon-Z'])validateRawProtocolRecord(row.replace('p2a: Porygon-Z',source),NATIVE11_GRAMMAR_CONTEXT);
 for(const bad of [row.replace('p2a:','p1a:'),row.replace('p2a:','p2b:'),row.replace('[of] ','[source] '),row+'|extra',row.replace('|Choice Scarf|','|Imaginary Item|')])
  assert.throws(()=>validateRawProtocolRecord(bad,NATIVE11_GRAMMAR_CONTEXT),/Malformed raw/);
 assert.throws(()=>validateRawProtocolRecord(row,REPLAY_COMPAT_CONTEXT),/prepared-family-unsupported\/magician/);
});

test('native Magician real held steps preserve receiver, donor history and Python evidence', {timeout:30000},async()=>{
 const {bornSession}=await import('./helpers/born_session');
 const {canonicalActionFromLegalAction}=await import('../src/canonical_action');
 const {spawnSync}=await import('node:child_process');
 const {NATIVE11_CONTEXT}=await import('../src/version_profile');
 const {validatePipelineLinkedRecordBundle}=await import('../src/pipeline_integration');
 for(const actor of ['p1','p2'] as const)for(const mode of ['survives','faints','terminal']) {
  const faint=mode!=='survives';
  const donor=actor==='p1'?'p2':'p1';
  const thief='Hoopa\nAbility: Magician\n- Swift';
  const victim=`Blissey @ Leftovers\nLevel: ${faint?1:100}\nAbility: Natural Cure\n- Splash${mode==='terminal'?'':'\n\nReserve (Magikarp)\n- Splash'}`;
  const session=await bornSession({teams:actor==='p1'?{p1:thief,p2:victim}:{p2:thief,p1:victim},options:{battle_id:'magician-'+actor+'-'+mode,observation_schema_version:'observable-battle-state/v2'}});
  try {
   const choices=Object.fromEntries((['p1','p2'] as const).map(owner=>{
    const request=session.boundary.perspectives[owner].observation.request!;
    const action=request.legal_actions.actions.find(a=>a?.choice==='move 1')!;
    return [owner,canonicalActionFromLegalAction(request,action.index)];
   })) as any;
   const output=await session.step(choices);
   const prefix=session.boundary.perspectives[actor].observation.protocol_prefix;
   assert.ok(prefix.some(r=>r===`|-item|${actor}a: Hoopa|Leftovers|[from] ability: Magician|[of] ${donor}${faint?'':'a'}: Blissey`));
   const receiver=(session.boundary.perspectives[actor].observation.view as any).self_team.find((p:any)=>p.ident.endsWith(': Hoopa'));
   const removed=(session.boundary.perspectives[donor].observation.view as any).self_team.find((p:any)=>p.ident.endsWith(': Blissey'));
   assert.equal(receiver.item,'leftovers');assert.equal(receiver.item_state,'held');
   assert.equal(removed.item,null);assert.equal(removed.last_item,'leftovers');assert.equal(removed.item_state,'removed');
   for(const owner of ['p1','p2'] as const) {
    const bundle=output.record_bundles[owner];validatePipelineLinkedRecordBundle(bundle,NATIVE11_CONTEXT);
    const result=spawnSync('D:/Anaconda/envs/neuralgpu/python.exe',['-m','neural.pipeline_record','--reader-profile=native11'],{cwd:path.resolve(__dirname,'../../..'),env:{...process.env,PYTHONPATH:path.resolve(__dirname,'../../../trainer/src')},input:JSON.stringify(bundle),encoding:'utf8',timeout:15000});
    assert.equal(result.status,0,result.stderr);
   }
  }finally{await session.close();}
 }
});
