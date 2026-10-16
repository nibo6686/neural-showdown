import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {importReplayPrefix,importReplayPrefixWithMoveHistory,ReplayImportError} from '../src/replay_import';
import {reconstructPublicMoveHistory} from '../src/public_move_history';
import {validateRawProtocolRecord,projectObservableBattleState} from '../src/observable_state';
import {validateHistoricalPipelineEpisodeFaithfulClaim} from '../src/pipeline_episode';
import {REPLAY_COMPAT_CONTEXT,NATIVE11_GRAMMAR_CONTEXT} from '../src/version_profile';
import {PlayerStateExtractor} from '../src/state_extractor';
const root=path.resolve(__dirname,'../../..');
const emit=(name:string,data:object)=>console.log('P36_WITNESS '+JSON.stringify({name,...data}));
const context={env_id:'P36-é-Ω',format:'gen9randombattle',perspective:'p1' as const,protocol_profile:'replay-compat-v1' as const};
function rows(side:'p1'|'p2',silent:boolean){return ['|j|☆Player','|gen|9','|start','|switch|p1a: Regice|Regice, L88|100/100','|switch|p2a: Blissey|Blissey, L85, F|100/100',
 '|-status|'+(side==='p1'?'p1a: Regice':'p2a: Blissey')+'|par','|-curestatus|'+(side==='p1'?'p1a: Regice':'p2a: Blissey')+'|par|[from] ability: Natural Cure'+(silent?'|[silent]':'')];}
test('P36 importer context semantic and publication boundaries',()=>{
 for(const side of ['p1','p2'] as const)for(const silent of [false,true]){
  const input=rows(side,silent),out=importReplayPrefixWithMoveHistory(input,input.length,context);
  assert.equal(out.replay.source_rows.at(-1)?.record,input.at(-1));assert.equal(out.replay.protocol_prefix.at(-1),input.at(-1));
  assert.equal(out.replay.source_to_routed[6],5);assert.equal(out.replay.routed_to_source[5],6);
  const pokemon=(side==='p1'?out.replay.view.self_team:out.replay.view.opponent_team)[0];assert.equal(pokemon.status,null);
  assert.equal(out.public_move_history.appearances.length,2);assert.equal(out.public_move_history.executions.length,0);
  assert.equal(out.public_move_history.appearances[1].carrier,null);
  if(silent){assert.throws(()=>reconstructPublicMoveHistory(out.replay),/major-status source grammar/);
   assert.throws(()=>validateRawProtocolRecord(input.at(-1)! ),/major-status source grammar/);}
 }
 for(const profile of [undefined,'auto','unknown','native11'])assert.throws(()=>importReplayPrefix([],0,{...context,protocol_profile:profile} as any),/explicit-replay-profile-required|native11-unadopted/);
 assert.throws(()=>importReplayPrefix(rows('p2',true),7,{...context,protocol_profile:'historical10'}),/admission at source 6.*major-status source grammar/);
 for(const row of ['|request|{}','|split|p1'])assert.throws(()=>importReplayPrefix([row],1,context),/Private transport/);
 assert.throws(()=>projectObservableBattleState({} as any,REPLAY_COMPAT_CONTEXT),/replay-publication-unsupported/);
 assert.throws(()=>new PlayerStateExtractor('P36','gen9randombattle','p1',NATIVE11_GRAMMAR_CONTEXT as any),/unsupported-context/);
 const fixture=JSON.parse(readFileSync(path.join(root,'docs/planning/perspective-fidelity-prompt31-reader-fixtures.json'),'utf8'));
 validateHistoricalPipelineEpisodeFaithfulClaim(fixture.result);
 assert.throws(()=>projectObservableBattleState({} as any,{...REPLAY_COMPAT_CONTEXT} as any),/unsupported-context/);
 assert.equal(importReplayPrefix([],0,{...context,protocol_profile:'historical10'}).source_cursor,0);
 emit('importer-semantics',{both_sides:true,both_exact_forms:true,status_cleared:true,raw_source_indices_preserved:true,portable_publication:'unsupported',authority:false});
});
test('P36 bounded saved prefix and historical parity',()=>{
 const fixture=JSON.parse(readFileSync(path.join(root,'docs/planning/perspective-fidelity-prompt36-saved-prefix.json'),'utf8'));
 assert.equal(fixture.source_sha256,'7e7e5315b76478c7c5a6407e037242cf295bc483e036be5812cd5cbffe370724');
 assert.equal(fixture.selected_cursor,45);assert.equal(fixture.natural_cure_source_index,44);
 const out=importReplayPrefixWithMoveHistory(fixture.records,45,context);assert.equal(out.replay.source_rows[44].record,fixture.records[44]);
 assert.equal(out.replay.source_to_routed[44],34);assert.equal(out.replay.routed_to_source[34],44);
 assert.equal(out.replay.view.opponent_team[0].status,null);assert.equal(out.replay.protocol_prefix.at(-1),fixture.records[44]);
 const old=importReplayPrefix(fixture.records,44,{...context,protocol_profile:'historical10'});
 const compat=importReplayPrefix(fixture.records,44,context);assert.deepEqual(compat,old);
 assert.throws(()=>importReplayPrefix(fixture.records,45,{...context,protocol_profile:'historical10'}), (e:any)=>e instanceof ReplayImportError && e.stage==='admission' && e.source_index===44 && /major-status source grammar/.test(e.message));
 emit('saved-prefix',{source_hash:fixture.source_sha256,source_cursor:45,natural_cure_source_index:44,natural_cure_routed_index:34,historical_prefix_parity:true,full_replay_oracle:false});
});

test('P36 importer captures mutable selection once',()=>{
 const input=rows('p2',true);
 for(const api of [importReplayPrefix,importReplayPrefixWithMoveHistory]){
  let reads=0;
  const mutable={...context,get protocol_profile(){return ++reads===1?'replay-compat-v1':'historical10';}};
  const out=api(input,input.length,mutable as any);
  assert.equal(reads,1);
  const replay='replay' in out?out.replay:out;
  assert.equal(replay.source_rows[6].record,input[6]);assert.equal(replay.view.opponent_team[0].status,null);
 }
 emit('immutable-call-selection',{both_import_apis:true,caller_profile_reads:1,between_stage_profile_switch_blocked:true});
});
