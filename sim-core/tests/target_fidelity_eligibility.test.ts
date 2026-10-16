import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import {Teams} from 'pokemon-showdown';
import {positiveFidelityScope,assertPositiveFidelityClaim,assertTargetEpisodeStatus,historicalKnowledgeSourceScope,installedNativeProfile} from '../src/version_profile';
import {runPipelineEpisode,validatePipelineEpisodeFaithfulClaim} from '../src/pipeline_episode';
import {SourceRegistryBuilder,LegacyContextBuilder,checkKnowledgeSourceBinding} from '../src/perspective_knowledge_source';
const root=path.resolve(__dirname,'../../..');
const load=(f:string)=>JSON.parse(readFileSync(path.join(root,f),'utf8'));
const emit=(name:string,data:object)=>console.log('P34_WITNESS '+JSON.stringify({name,...data}));
const saved=load('docs/planning/perspective-fidelity-prompt31-reader-fixtures.json');
const origin={battle_key:'fixture-Éclair-😀',format:'gen9randombattle',engine:'pokemon-showdown@0.11.10',rule_version:'pk-rules/v1'};
const replay=['|start','|switch|p1a: Éclair|Pikachu, L80|100/100','|switch|p2a: Beta|Gengar, L80|100/100','|-enditem|p1a: Éclair|Oran Berry|[eat]',
'|move|p2a: Beta|Tackle|p1a: Éclair','|replace|p2a: Beta|Zoroark, L80|100/100','|win|Éclair'];

test('P34 PRE eligibility and historical readers',()=>{
 assert.equal(positiveFidelityScope('historical10','gen9randombattle'),true);assert.equal(positiveFidelityScope('historical10','unknown'),false);
 assert.equal(positiveFidelityScope('native11','gen9randombattle'),false);
 assert.throws(()=>assertPositiveFidelityClaim('native11','gen9randombattle',true),/positive-unaccepted/);
 assertPositiveFidelityClaim('native11','gen9randombattle',false);
 assert.throws(()=>positiveFidelityScope('caller-certificate','gen9randombattle'),/unknown-fidelity/);
 assertTargetEpisodeStatus('completed',{code:'episode/v1/terminal',reason:'local-control'},true);
 assert.throws(()=>assertTargetEpisodeStatus('unknown',{code:'episode/v1/terminal',reason:'local-control'},true),/episode-status/);
 assert.throws(()=>assertTargetEpisodeStatus('truncated',{code:'episode/v1/cancelled',reason:'local-control'},true),/episode-status/);
 assert.equal(historicalKnowledgeSourceScope('0.11.11'),false);assert.equal(historicalKnowledgeSourceScope('0.11.10'),true);
 const before=JSON.stringify(saved.result);assert.equal(validatePipelineEpisodeFaithfulClaim(saved.result),true);
 const conservative=structuredClone(saved.result);conservative.faithful_complete_episode=false;
 assert.equal(validatePipelineEpisodeFaithfulClaim(conservative),true,'old helper reports eligible capture, independent of asserted flag');
 assert.equal(JSON.stringify(saved.result),before);
 const bad=load('docs/planning/perspective-fidelity-prompt31-resealed-negatives.json').target;
 const mixed=structuredClone(saved.result);mixed.records.p1[0]=bad;
 assert.throws(()=>validatePipelineEpisodeFaithfulClaim(mixed),/conflicting-revisions/);
 emit('pre-eligibility',{finite_target_policy_only:true,old_true_and_conservative_flag_meaning:true,saved_ids_unchanged:true,target_callers:'UNEXECUTED'});
});

test('P34 PRE bounded historical producer',async()=>{
 const generate=Teams.generate;let calls=0;
 Teams.generate=function(){return Teams.import(calls++===0?'Snorlax\nLevel: 100\nAbility: Immunity\n- Body Slam':'Magikarp\nLevel: 1\nAbility: Swift Swim\n- Splash')!;};
 try {
  const result=await runPipelineEpisode({battle_id:'P34-bounded',format:'gen9randombattle',seed:[1,2,3,4],observation_schema_version:'observable-battle-state/v2',limits:{max_transitions:1,max_attempts:2,max_rejections_per_boundary:1}});
  assert.equal(result.status,'completed',JSON.stringify(result.stop));assert.equal(result.faithful_complete_episode,true);
  assert.equal(result.counts.committed_transitions,1);assert.equal(validatePipelineEpisodeFaithfulClaim(result),true);
  emit('old-producer',{actual_native_episode:true,constructed_terminal_team_stimulus:true,generated_format_reachability:false,one_transition:true,historical_flag:true});
 }finally{Teams.generate=generate;}
});

test('P34 PRE source entry and origin negatives',()=>{
 const audit=load('docs/contracts/fixtures/perspective-knowledge-v1/replay-ordinary.json'), before=JSON.stringify(audit);
 const b=new SourceRegistryBuilder();b.setOrigin(origin);b.setReplaySource(replay);const registry=b.freeze();
 const checked=checkKnowledgeSourceBinding(audit,registry,null,audit.required_profile);
 assert.equal(checked.source_verification.replay_source,true);assert.equal(checked.fact_semantics,'unverified');assert.equal(checked.published,false);
 assert.equal(JSON.stringify(audit),before);
 assert.throws(()=>checkKnowledgeSourceBinding(audit,{} as any,null,audit.required_profile),/capability\/registry/);
 const target=new SourceRegistryBuilder();assert.throws(()=>target.setOrigin({...origin,engine:'pokemon-showdown@0.11.11'}),/registry\/origin/);
 target.setOrigin(origin);assert.equal(target.freeze().availability.origin,true,'old trusted-owner source remains supported');
 assert.ok(new LegacyContextBuilder().freeze());
 emit('old-source',{actual_saved_factory_and_checker:true,old_origin_unchanged:true,target_label_rejected:true,no_native_content_provenance_claim:true});
});

const live=String(installedNativeProfile().package_version)==='0.11.11';
test('P34 LIVE target completion and source quarantine',{skip:!live},async()=>{
 const generate=Teams.generate;let calls=0;
 Teams.generate=function(){return Teams.import(calls++===0?'Snorlax\nLevel: 100\nAbility: Immunity\n- Body Slam':'Magikarp\nLevel: 1\nAbility: Swift Swim\n- Splash')!;};
 try {
  const result=await runPipelineEpisode({battle_id:'P34-live',format:'gen9randombattle',seed:[1,2,3,4],observation_schema_version:'observable-battle-state/v2',limits:{max_transitions:1,max_attempts:2,max_rejections_per_boundary:1}});
  assert.equal(result.status,'completed');assert.equal(result.faithful_complete_episode,false);
  const malformed=structuredClone(result);(malformed as any).status='unknown';
  assert.throws(()=>validatePipelineEpisodeFaithfulClaim(malformed,installedNativeProfile().reader),/episode-status/);
  const mismatch=structuredClone(result);mismatch.status='truncated';mismatch.stop={code:'episode/v1/cancelled',reason:'LIVE mismatch'};
  assert.throws(()=>validatePipelineEpisodeFaithfulClaim(mismatch,installedNativeProfile().reader),/episode-status/);
  // Flag has no separate hash; all nested target identities come from the actual producer.
  const claim=structuredClone(result);claim.faithful_complete_episode=true;
  assert.throws(()=>validatePipelineEpisodeFaithfulClaim(claim,installedNativeProfile().reader),/positive-unaccepted/);
  writeFileSync(path.join(root,'docs/planning/perspective-fidelity-prompt34-live-target-result.json'),JSON.stringify(result));
  const beliefs:any[]=[],records:any={p1:[],p2:[]},seen=new Set<string>();
  for(const owner of ['p1','p2'] as const)for(const b of result.records[owner]) {
    for(const belief of [b.input_belief,b.successor_belief])if(!seen.has(belief.belief_id)){
      seen.add(belief.belief_id);const fields:any=structuredClone(belief),arrays:any={};delete fields.belief_id;delete fields.source_protocol_prefix;
      for(const key of ['observation_history','simulator_snapshot_history','transition_history','candidates','evidence','contradictions','unresolved']){arrays[key]={mode:'full',items:fields[key]};delete fields[key];}
      beliefs.push({belief_id:belief.belief_id,base_belief_id:null,fields,arrays});
    }
    records[owner].push({transition_id:b.transition.transition_id,action:b.action,input_belief_id:b.input_belief.belief_id,successor_belief_id:b.successor_belief.belief_id});
  }
  const {records:_records,evidence_envelope,...metadata}=result;
  writeFileSync(path.join(root,'docs/planning/perspective-fidelity-prompt34-live-target-sweep.json'),JSON.stringify({schema_version:'pipeline-episode-publication-sweep/v1',result:metadata,evidence_envelope,records,beliefs}));
  assert.throws(()=>new SourceRegistryBuilder(),/historical-origin-quarantined/);
  assert.throws(()=>new LegacyContextBuilder(),/historical-origin-quarantined/);
 }finally{Teams.generate=generate;}
});
