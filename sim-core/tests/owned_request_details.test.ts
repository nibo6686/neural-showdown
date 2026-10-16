import assert from 'node:assert/strict';
import test from 'node:test';
import { Teams } from 'pokemon-showdown';
import { PipelineIntegrationSession } from '../src/pipeline_integration';
import { continuePipelineEpisode } from '../src/pipeline_episode';
import { OwnedRequestHealthHost } from '../src/owned_request_health';
import { LocalBattleEnv } from '../src/env_manager';
import { declaredRequestValues, DECLARED_PROPERTIES } from '../src/owned_request_values';
import { checkNativeOwnerDetailsProjection, checkNativeOwnerLoadoutProjection, knowledgeIdentity } from '../src/perspective_knowledge';
import { joint, choice, native, env } from './helpers/owner_selection_restore';
const owners=['p1','p2'] as const;
const recipients=()=>({p1:{},p2:{}});
const read=(s:PipelineIntegrationSession,r:object)=>s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(r),r);
const fact=(pair:any,property:string,slot=1,section='current')=>pair.projection[section].find((f:any)=>f.subject===pair.projection.owner+':roster:'+slot&&f.property===property);
const basic=(name='Magikarp')=>({species:'Magikarp',name,ability:'Swift Swim',item:'',moves:['Splash']});
async function create(r:ReturnType<typeof recipients>,teams?:any[][]){const generate=Teams.generate;let count=0;try{if(teams)Teams.generate=()=>structuredClone(teams[count++]);return await PipelineIntegrationSession.create({battle_id:'P60',format:'gen9randombattle',seed:[1,2,3,4],knowledge_recipients:r});}finally{Teams.generate=generate;}}
const emit=(name:string,data:object)=>console.log('P60_WITNESS '+JSON.stringify({name,...data}));
function validate(s:PipelineIntegrationSession,r:ReturnType<typeof recipients>){for(const owner of owners){
 const pair=read(s,r[owner]);checkNativeOwnerDetailsProjection(pair.projection);assert.equal(pair.projection.result,'incomplete');assert.equal(pair.projection.current_stats_semantics,'request-declared-baseStoredStats/v1');
 const delivery=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle(owner),owner).boundaries.at(-1)?.current;
 const request=(env(s).getRequest(owner)?.raw ?? (delivery?JSON.parse(delivery.source.request_json):null)) as any;const side=native(s)[owner]!;
 for(let slot=1;slot<=pair.projection.starting.find((f:any)=>f.property==='roster_size').value.data;slot++){
  if(pair.projection.request.state==='terminal'||pair.projection.request.state==='requestless'){for(const property of DECLARED_PROPERTIES){assert.equal(fact(pair,property,slot).state,'unknown');assert.equal(fact(pair,property,slot).reason,'not_emitted');}continue;}
  // Test oracle follows actual native set references; this is not a production position resolver.
  const actor=side.pokemon.find(a=>a.set===side.team[slot-1]);assert.ok(actor);const row=request.side.pokemon[side.pokemon.indexOf(actor)];
  assert.deepEqual(fact(pair,'calculated_stats',slot).value.data,row.stats);assert.equal(fact(pair,'details',slot).value.data,row.details);assert.equal(fact(pair,'ball',slot).value.data,row.pokeball);
  const level=/, L([0-9]+)/.exec(row.details),gender=/, ([MF])(?:,|$)/.exec(row.details);
  assert.equal(fact(pair,'level',slot).value.data,level?Number(level[1]):100);assert.equal(fact(pair,'gender',slot).state,gender?'known':'known_absent');assert.equal(fact(pair,'gender',slot).value?.data??null,gender?.[1]??null);assert.equal(fact(pair,'shiny',slot).value.data,row.details.endsWith(', shiny'));
  if(row.condition==='0 fnt'){assert.equal(fact(pair,'hp_max',slot).state,'unknown');assert.equal(fact(pair,'hp_max',slot).reason,'not_emitted');}else{assert.equal(fact(pair,'hp_max',slot).value.data,Number(row.condition.split('/')[1].split(' ')[0]));}
  for(const property of DECLARED_PROPERTIES)if(fact(pair,property,slot).state!=='unknown')assert.equal(fact(pair,property,slot).observed_at,pair.binding.prefix_cursor);
 }
 assert.throws(()=>s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(r[owner]),r[owner==='p1'?'p2':'p1']),/copied-or-stale/);
 assert.equal(fact(pair,'current_moves').reason,'unimplemented_family');assert.equal(pair.projection.request.schema,'owned-active-options/v1');
}}

test('P60 generated both owners selected delivery restore and real callbacks',async()=>{
 const r=recipients(),s=await create(r);try{validate(s,r);const first=owners.map(p=>read(s,r[p])),bytes=JSON.stringify(first),actors=owners.map(p=>native(s)[p]!.active[0]);
 await joint(s,'p1','switch 2','switch 2');await joint(s,'p1','switch 2','switch 2');validate(s,r);
 for(const [i,p] of owners.entries()){assert.notEqual(native(s)[p]!.active[0],actors[i]);assert.equal(read(s,r[p]).projection.starting,first[i].projection.starting);assert.equal(read(s,r[p]).projection.original_interpretation,first[i].projection.original_interpretation);}
 const current=owners.map(p=>read(s,r[p])),calls:string[]=[];
 const result=await continuePipelineEpisode(s,{limits:{max_transitions:1},policy_id:'p60-owned-details/v1',accept_incomplete:true,owned_action_order:Object.fromEntries(owners.map(owner=>[owner,{recipient:r[owner],callback:(input:any)=>{
  calls.push(owner);assert.equal(input.knowledge,current[owners.indexOf(owner)]);checkNativeOwnerDetailsProjection(input.knowledge.projection);assert.equal(input.completeness,'incomplete');assert.ok(Object.isFrozen(fact(input.knowledge,'calculated_stats').value.data));
  const selected=input.action_context.legal_actions.actions.find((a:any)=>a?.choice==='switch 2');assert.ok(selected);return [selected.index,...input.legal_indices.filter((i:number)=>i!==selected.index)];
 }}])) as any});assert.deepEqual(calls,['p1','p2']);assert.equal(result.counts.committed_transitions,1);assert.equal(result.faithful_complete_episode,false);assert.equal(JSON.stringify(first),bytes);assert.doesNotMatch(JSON.stringify(result),/original_interpretation|native11-details|current_stats_semantics/);
 emit('generated',{genuine_both_owner_rows:true,held_reorder_fresh_B2_objects:true,selected_delivery_real_episode_callbacks:true,original_refs_and_prior_bytes_preserved:true,recipient_isolation:true});
 }finally{await s.close();}
});

test('P60 literal fields omissions and boosted stored-stat distinction',async()=>{
 const stats={atk:67,def:60,spa:112,spd:70,spe:111};const values=declaredRequestValues({stats,details:'Pikachu, L50, F, shiny',pokeball:'ultraball',condition:'35/142 par'}),get=(v:ReturnType<typeof declaredRequestValues>,p:string)=>v.find(f=>f.property===p)!;
 assert.deepEqual(get(values,'calculated_stats').value,stats);assert.equal(get(values,'hp_max').value,142);assert.equal(get(values,'gender').value,'F');assert.equal(get(values,'level').value,50);assert.equal(get(values,'shiny').value,true);assert.equal(get(values,'ball').value,'ultraball');assert.equal(get(values,'details').value,'Pikachu, L50, F, shiny');
 assert.ok(declaredRequestValues({}).every(v=>v.state==='unknown'&&v.reason==='not_emitted'));
 const genderless=declaredRequestValues({details:'Mew',condition:'0 fnt'});assert.equal(get(genderless,'gender').state,'known_absent');assert.equal(get(genderless,'level').value,100);assert.equal(get(genderless,'shiny').value,false);assert.equal(get(genderless,'ball').reason,'not_emitted');assert.equal(get(genderless,'hp_max').reason,'not_emitted');
 for(const row of [{stats:{...stats,extra:1}},{stats:{...stats,atk:0.5}},{stats:{atk:67}},{details:'Pikachu, shiny, F'},{details:'Pikachu, F, F'},{details:'Pikachu, L100'},{details:'Pikachu, L50, F, tera:Electric'},{pokeball:''},{pokeball:'Ultra Ball'},{condition:'143/142'},{condition:'1/0'},{condition:'1/2.0'}])assert.throws(()=>declaredRequestValues(row),/owned-request-values/);
 const evs={hp:252,atk:0,def:0,spa:252,spd:0,spe:4},ivs={hp:31,atk:31,def:31,spa:31,spd:31,spe:31};const r=recipients(),s=await create(r,[[{species:'Pikachu',ability:'Static',item:'',moves:['Nasty Plot','Splash'],nature:'Modest',level:50,gender:'F',shiny:true,pokeball:'Ultra Ball',teraType:'Electric',evs,ivs}],[basic()]]);
 try{validate(s,r);const first=read(s,r.p1),originals=first.projection.starting,interpretation=first.projection.original_interpretation;
 assert.deepEqual(fact(first,'calculated_stats').value.data,stats);assert.equal(fact(first,'hp_max').value.data,142);assert.equal(fact(first,'ball').value.data,'ultraball');assert.equal(fact(first,'details').value.data,'Pikachu, L50, F, shiny');
 const other=read(s,r.p2);assert.equal(fact(other,'gender',1,'starting').state,'known_absent');assert.equal(fact(other,'details',1,'starting').state,'unknown');assert.equal(other.projection.original_interpretation[0].normalized.gender_resolution,'unresolved');assert.equal(fact(other,'gender').state,'known');
 await joint(s,'p1','move 1');validate(s,r);const after=read(s,r.p1),actor=native(s).p1!.active[0];assert.equal(actor.boosts.spa,2);assert.equal(actor.getStat('spa'),224);assert.deepEqual(fact(after,'calculated_stats').value.data,stats);assert.equal(after.projection.starting,originals);assert.equal(after.projection.original_interpretation,interpretation);
 assert.equal(fact(read(s,r.p2),'details',1,'starting').state,'unknown');assert.equal(fact(read(s,r.p2),'gender').state,'known');
 for(const [mutate,error] of [
  [(p:any)=>fact({projection:p},'level').value.data++,/details tuple/],
  [(p:any)=>fact({projection:p},'hp_max').value.data=fact({projection:p},'hp').value.data-1,/health tuple/],
  [(p:any)=>p.current_stats_semantics='effective-battle-stats',/const/],
  [(p:any)=>p.result='strong_complete',/const/],
 ] as const){const copy:any=structuredClone(after.projection);mutate(copy);copy.id=knowledgeIdentity(copy);assert.throws(()=>checkNativeOwnerDetailsProjection(copy),error);}
 assert.throws(()=>checkNativeOwnerLoadoutProjection(after.projection));assert.throws(()=>s.readOwnerKnowledge(structuredClone(after) as any,r.p1),/copied-or-stale/);
 const splash=s.boundary.perspectives.p1.observation.request!.legal_actions.actions.find(a=>a?.choice==='move 2');assert.ok(splash);
 const result=await continuePipelineEpisode(s,{limits:{max_transitions:1},policy_id:'p60-declared-stat-policy/v1',accept_incomplete:true,owned_action_order:Object.fromEntries(owners.map(owner=>[owner,{recipient:r[owner],callback:(input:any)=>{
  const selected=input.action_context.legal_actions.actions.find((a:any)=>a?.choice===(owner==='p1'&&fact(input.knowledge,'calculated_stats').value.data.spa===112?'move 2':'move 1'));assert.ok(selected);return [selected.index,...input.legal_indices.filter((index:number)=>index!==selected.index)];
 }}])) as any});assert.equal(result.counts.committed_transitions,1);assert.equal(result.records.p1[0].action.index,splash.index);assert.doesNotMatch(JSON.stringify(result),/current_stats_semantics|original_interpretation/);
 emit('literal',{pure_exact_omission_and_malformed_controls:true,constructed_native_Nasty_Plot:true,declared_spa112_effective224:true,current_resolved_gender_does_not_repair_original:true,literal_metadata_and_ball:true,coherent_rehashed_negatives:true});
 }finally{await s.close();}
});

test('P60 forced Revival wait and terminal availability',async()=>{
 const own=Teams.import('First (Snorlax)\nAbility: Immunity\n- Splash\n- Explosion\n\nHealer (Pawmot)\nAbility: Iron Fist\n- Revival Blessing\n- Splash\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash')!;
 const wait=Teams.import('Watcher (Giratina)\nAbility: Pressure\n- Splash\n\nWaitingReserve (Magikarp)\nAbility: Swift Swim\n- Splash')!;
 let r=recipients(),s=await create(r,[own,wait]);try{const original=owners.map(p=>read(s,r[p]).projection.starting);await joint(s,'p1','move 2');validate(s,r);assert.equal(read(s,r.p2).projection.request.state,'waiting');assert.equal(fact(read(s,r.p1),'hp_max').state,'unknown');assert.equal(fact(read(s,r.p1),'calculated_stats').state,'known');
 await s.stepForcedSwitch(choice(s,'p1','switch 2'));validate(s,r);await joint(s,'p1','move 1');validate(s,r);assert.equal(read(s,r.p1).projection.request.state,'revival_selection');await s.stepRevival(choice(s,'p1','switch 2'));validate(s,r);for(const [i,p]of owners.entries())assert.equal(read(s,r[p]).projection.starting,original[i]);
 }finally{await s.close();}
 r=recipients();s=await create(r,[Teams.import('Mewtwo\nAbility: Pressure\n- Psystrike')!,Teams.import('Magikarp\nLevel: 1\nAbility: Swift Swim\n- Splash')!]);try{await joint(s,'p1','move 1');validate(s,r);for(const p of owners)assert.equal(read(s,r[p]).projection.request.state,'terminal');}finally{await s.close();}
 emit('lifecycle',{constructed_existing_forced_Revival_wait:true,fainted_denominator_unavailable:true,emitted_faint_stats_still_known:true,terminal_no_stale_facts:true,not_generated_reachability:true});
});

test('P60 altered copied row fields and post-preparation rollback',async()=>{
 const original=(OwnedRequestHealthHost.prototype as any).checkCapture;
 for(const fault of ['stats','copy','details','denominator']){let injected=false,cause='';(OwnedRequestHealthHost.prototype as any).checkCapture=function(c:any,w:any,settled:boolean){if(!injected&&c.owner==='p1'){injected=true;const row=c.rows[0];if(fault==='stats')row.data.stats.atk++;if(fault==='copy')row.data.stats={...row.data.stats};if(fault==='details')row.data.details='Magikarp, shiny, M';if(fault==='denominator')row.data.condition='1/1';}try{return original.call(this,c,w,settled);}catch(error){cause=(error as Error).message;throw error;}};
 try{await assert.rejects(create(recipients(),[[basic()],[basic()]]));assert.ok(injected);assert.match(cause,fault==='stats'||fault==='copy'?/altered-declared-stats/:fault==='details'?/altered-declared-details/:/altered-writer-row/);}finally{(OwnedRequestHealthHost.prototype as any).checkCapture=original;}}
 const r=recipients(),s=await create(r,[[basic('First'),basic('Reserve')],[basic('Other'),basic('OtherReserve')]]),prepare=OwnedRequestHealthHost.prototype.prepare,close=LocalBattleEnv.prototype.close;
 let host:OwnedRequestHealthHost,key:object,revoked=false;
 try{const before=s.boundary,pair=read(s,r.p1),handle=s.getOwnerKnowledgeHandle(r.p1),history=s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1');
 OwnedRequestHealthHost.prototype.prepare=function(...args){host=this;key=prepare.apply(this,args);const actor=(args[0] as any).battleStream.battle.p1.active[0];actor.baseStoredStats.atk++;return key;};
 LocalBattleEnv.prototype.close=function(){if(this.id.includes('step-')){assert.throws(()=>host!.readPrepared(key!,'p1'),/foreign-preparation/);revoked=true;}return close.call(this);};
 await assert.rejects(joint(s,'p1','switch 2','switch 2'),/stale-declared-stats/);assert.ok(revoked);assert.equal(s.boundary,before);assert.equal(read(s,r.p1),pair);assert.equal(s.getOwnerKnowledgeHandle(r.p1),handle);assert.equal(s.readRequestDeliveryHistory(s.getRequestDeliveryHandle('p1'),'p1'),history);
 OwnedRequestHealthHost.prototype.prepare=prepare;LocalBattleEnv.prototype.close=close;await joint(s,'p1','switch 2','switch 2');validate(s,r);assert.equal(read(s,r.p1).projection.starting,pair.projection.starting);assert.equal(read(s,r.p1).projection.original_interpretation,pair.projection.original_interpretation);assert.throws(()=>s.readOwnerKnowledge(handle,r.p1),/copied-or-stale/);const latest=s.getOwnerKnowledgeHandle(r.p1);await s.close();assert.throws(()=>s.readOwnerKnowledge(latest,r.p1),/closed/);
 emit('faults',{actual_source_alteration_and_copied_stats_rejected:true,exact_internal_causes_checked:true,post_prepare_stale_stats_reject:true,revocation_before_cleanup:true,old_pair_delivery_retained:true,fresh_retry:true});
 }finally{OwnedRequestHealthHost.prototype.prepare=prepare;LocalBattleEnv.prototype.close=close;await s.close();}
});
