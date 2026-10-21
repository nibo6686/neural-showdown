import assert from 'node:assert/strict';
import test from 'node:test';
import * as simulator from 'pokemon-showdown';
import { PipelineIntegrationSession } from '../src/pipeline_integration';
import { continuePipelineEpisode } from '../src/pipeline_episode';
import { OriginalOwnerCreation } from '../src/original_owner_provider';
import { NativeOwnerKnowledgeController } from '../src/native_owner_knowledge';
import { interpretOriginalValues } from '../src/original_owner_values';
import { checkNativeOwnerDetailsProjection, checkNativeOwnerIdentifiersProjection, knowledgeIdentity } from '../src/perspective_knowledge';
import { joint, native } from './helpers/owner_selection_restore';
const owners = ['p1','p2'] as const;
const dex = simulator.Dex.forFormat('gen9randombattle');
const recipients = () => ({ p1: {}, p2: {} });
const read = (s: PipelineIntegrationSession, r: object) => s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(r), r);
const fact = (pair: any, property: string, slot = 1, section = 'starting') => pair.projection[section].find((f: any) => f.subject === pair.projection.owner + ':roster:' + slot && f.property === property);
const basic = (species = 'Magikarp', ability = 'Swift Swim') => ({ species, ability, item: '', moves: ['Splash'], gender: 'M' });
async function create(r: ReturnType<typeof recipients>, teams?: any[][]) {
  const generate = simulator.Teams.generate; let count = 0;
  try {
    if (teams) simulator.Teams.generate = () => structuredClone(teams[count++]);
    return await PipelineIntegrationSession.create({ battle_id: 'P59', format: 'gen9randombattle', seed: [1,2,3,4], knowledge_recipients: r });
  } finally { simulator.Teams.generate = generate; }
}
const witness = (name: string, data: object) => console.log('P59_WITNESS ' + JSON.stringify({ name, ...data }));
// Independent test arithmetic and nature table, not the production rule helper.
function oracle(set: any) {
  const species = dex.species.get(set.species), level = Math.min(9999, Math.max(1, set.level || 100));
  const table: Record<string, [string,string]> = { Modest: ['spa','atk'], Adamant: ['atk','spa'], Timid: ['spe','atk'], Brave: ['atk','spe'], Quiet: ['spa','spe'], Jolly: ['spe','spa'] };
  const nature = table[set.nature];
  const value: any = {};
  for (const key of ['hp','atk','def','spa','spd','spe']) {
    const iv = Math.min(31, set.ivs?.[key] ?? 31), ev = Math.min(255, set.evs?.[key] ?? 0);
    const subtotal = Math.floor((2 * (species.baseStats as any)[key] + iv + Math.floor(ev / 4)) * level / 100);
    value[key] = key === 'hp' ? species.maxHP || subtotal + level + 10 : Math.floor((subtotal + 5) * (nature?.[0] === key ? 1.1 : nature?.[1] === key ? 0.9 : 1));
  }
  return value;
}
function assertGenerated(s: PipelineIntegrationSession, r: ReturnType<typeof recipients>, starting?: any[]) {
  for (const [i, owner] of owners.entries()) {
    const pair = read(s, r[owner]); checkNativeOwnerDetailsProjection(pair.projection);
    assert.equal(pair.projection.result, 'incomplete');
    const source = s.readOriginalOwnerHolding(s.getOriginalOwnerHolding(owner), owner);
    source.raw_team.forEach((raw: any, n) => {
      const values = oracle(raw), stats = { ...values }; delete stats.hp;
      assert.deepEqual(fact(pair, 'calculated_stats', n + 1).value.data, stats);
      assert.equal(fact(pair, 'hp_max', n + 1).value.data, values.hp);
      for (const key of ['submitted_nature','submitted_happiness','gender','shiny','ball']) {
        const rawKey = ({submitted_nature:'nature', submitted_happiness:'happiness',ball:'pokeball'} as any)[key] || key;
        assert.equal(fact(pair, key, n + 1).state, raw[rawKey] === undefined ? 'known_absent' : 'known');
      }
      assert.ok(Object.isFrozen(fact(pair, 'calculated_stats', n + 1).value.data));
    });
    assert.ok(pair.projection.starting.every((f: any) => f.owner === owner && f.subject.startsWith(owner + ':')));
    assert.equal(fact(pair, 'current_moves', 1, 'current').reason, 'unimplemented_family');
    assert.ok(fact(pair, 'hp', 1, 'current')); assert.ok(fact(pair, 'item', 1, 'current')); assert.ok(fact(pair, 'ability', 1, 'current'));
    assert.equal(pair.projection.request.schema, 'owned-active-options/v1');
    if (starting) assert.equal(pair.projection.starting, starting[i]);
    assert.throws(() => s.readOwnerKnowledge(s.getOwnerKnowledgeHandle(r[owner]), r[owner === 'p1' ? 'p2' : 'p1']), /copied-or-stale/);
  }
}

test('P59 generated both owners restore reorder and real decision caller', async () => {
  const r = recipients(), s = await create(r);
  try {
    assertGenerated(s, r); const pairs = owners.map(p => read(s, r[p])), bytes = JSON.stringify(pairs), actors = owners.map(p => native(s)[p]!.active[0]);
    const original = pairs.map(p => p.projection.starting), interpretations = pairs.map(p => p.projection.original_interpretation);
    await joint(s, 'p1', 'switch 2', 'switch 2'); await joint(s, 'p1', 'switch 2', 'switch 2');
    assertGenerated(s, r, original);
    for (const [i, p] of owners.entries()) { assert.notEqual(native(s)[p]!.active[0], actors[i]); assert.equal(read(s, r[p]).projection.original_interpretation, interpretations[i]); }
    const calls: string[] = [];
    const result = await continuePipelineEpisode(s, { limits: { max_transitions: 1 }, policy_id: 'p59-original/v1', accept_incomplete: true,
      owned_action_order: Object.fromEntries(owners.map(owner => [owner, { recipient: r[owner], callback: (input: any) => {
        calls.push(owner); assert.equal(input.knowledge.projection.starting, original[owners.indexOf(owner)]);
        checkNativeOwnerDetailsProjection(input.knowledge.projection); assert.equal(input.completeness, 'incomplete');
        const selected = input.action_context.legal_actions.actions.find((a: any) => a?.choice === 'switch 2'); assert.ok(selected);
        return [selected.index, ...input.legal_indices.filter((index: number) => index !== selected.index)];
      }}])) as any });
    assert.deepEqual(calls, ['p1','p2']); assert.equal(result.counts.committed_transitions, 1); assert.equal(result.faithful_complete_episode, false);
    assert.equal(JSON.stringify(pairs), bytes); assert.doesNotMatch(JSON.stringify(result), /original_interpretation|native11-loadout|native-owner-loadout/);
    witness('generated', { genuine_generation: true, independent_arithmetic: true, fresh_B2_objects: true, original_and_interpretation_references_retained: true, actual_episode_callback: true, both_owner_privacy: true });
  } finally { await s.close(); }
});

test('P59 literal submitted default partial and rule exception oracle', async () => {
  const stats = { hp: 252, atk: 0, def: 0, spa: 252, spd: 0, spe: 4 }, ivs = { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 };
  const raw = { ...basic('Pikachu','Static'), nature: 'Modest', evs: stats, ivs, happiness: 0, level: 50, gender: 'F', shiny: true, pokeball: 'Ultra Ball', teraType: 'Flying' };
  const r = recipients(), s = await create(r, [[raw], [basic()]]);
  try {
    const pair = read(s, r.p1); checkNativeOwnerDetailsProjection(pair.projection);
    assert.deepEqual(fact(pair,'calculated_stats').value.data, { atk: 67, def: 60, spa: 112, spd: 70, spe: 111 }); assert.equal(fact(pair,'hp_max').value.data,142);
    for (const [property, expected] of Object.entries({submitted_nature:'Modest',submitted_happiness:0,level:50,gender:'F',shiny:true,ball:'Ultra Ball',details:'Pikachu, L50, F, shiny',starting_tera:'Flying'})) assert.deepEqual(fact(pair, property).value.data, expected);
    assert.deepEqual(fact(pair,'submitted_evs').value.data, stats); assert.deepEqual(fact(pair,'submitted_ivs').value.data, ivs);
    assert.equal(pair.projection.original_interpretation[0].normalized.ball,'ultraball');
    for (const [property, mutate, error] of [
      ['normalized stat', (copy: any) => copy.original_interpretation[0].normalized.hp_max++, /rule interpretation/],
      ['fact stat', (copy: any) => fact({projection:copy},'calculated_stats').value.data.atk++, /fact interpretation/],
      ['submission absence', (copy: any) => copy.original_interpretation[0].presence.nature='omitted', /absent submission/],
      ['complete claim', (copy: any) => copy.result='strong_complete', /const/],
    ] as const) { const copy: any = structuredClone(pair.projection); mutate(copy); copy.id=knowledgeIdentity(copy); assert.throws(() => checkNativeOwnerDetailsProjection(copy), error, property); }
    assert.throws(() => checkNativeOwnerIdentifiersProjection(pair.projection));
    assert.throws(() => s.readOwnerKnowledge(structuredClone(pair) as any, r.p1), /copied-or-stale/);
  } finally { await s.close(); }
  const absent: any = { ...basic('Pikachu','Static'), level:50 }; delete absent.gender;
  const originalBytes = JSON.stringify(absent), missing = interpretOriginalValues(absent,dex,simulator);
  const get = (result: ReturnType<typeof interpretOriginalValues>, property: string) => result.facts.find(f=>f.property===property)!;
  for (const property of ['submitted_nature','submitted_evs','submitted_ivs','submitted_happiness','gender','shiny','ball']) assert.equal(get(missing, property).state,'known_absent');
  assert.equal(get(missing,'details').state,'unknown'); assert.equal(missing.interpretation.normalized.gender_resolution,'unresolved');
  assert.equal(missing.interpretation.normalized.nature,null); assert.equal(missing.interpretation.normalized.happiness,255); assert.equal(missing.interpretation.normalized.ball,'pokeball'); assert.equal(get(missing,'starting_tera').value,'Electric');
  assert.deepEqual(get(missing,'calculated_stats').value,{atk:75,def:60,spa:70,spd:70,spe:110}); assert.equal(get(missing,'hp_max').value,110); assert.equal(JSON.stringify(absent),originalBytes);
  const partial = interpretOriginalValues({...absent,nature:undefined,happiness:undefined,evs:{hp:4,atk:252},ivs:{atk:0,spe:0}},dex,simulator);
  assert.equal(partial.interpretation.presence.nature,'undefined'); assert.equal(partial.interpretation.presence.happiness,'undefined');
  assert.equal(get(partial,'submitted_evs').state,'unknown'); assert.equal(get(partial,'submitted_ivs').state,'unknown');
  assert.deepEqual(get(partial,'calculated_stats').value,{atk:91,def:60,spa:70,spd:70,spe:95});assert.equal(get(partial,'hp_max').value,111);
  assert.equal(partial.interpretation.submission.evs.atk,252); assert.equal(partial.interpretation.submission.evs.def,null); assert.equal(partial.interpretation.components.ivs.atk,'present'); assert.equal(partial.interpretation.components.ivs.hp,'omitted');
  const one = interpretOriginalValues({...basic('Shedinja','Wonder Guard'),nature:'Adamant',level:50},dex,simulator);
  assert.equal(get(one,'hp_max').value,1);assert.deepEqual(get(one,'calculated_stats').value,{atk:121,def:65,spa:45,spd:50,spe:60});
  const clamped = interpretOriginalValues({...absent,level:10000,happiness:300,evs:{...stats,hp:400},ivs:{...ivs,atk:40}},dex,simulator);
  assert.equal(clamped.interpretation.submission.evs.hp,400); assert.equal(clamped.interpretation.normalized.evs.hp,255); assert.equal(clamped.interpretation.normalized.ivs.atk,31); assert.equal(clamped.interpretation.normalized.happiness,255); assert.equal(clamped.interpretation.normalized.level,9999);
  const fixed = interpretOriginalValues({...basic('Blissey','Natural Cure'),gender:undefined},dex,simulator);assert.equal(get(fixed,'gender').state,'known_absent');assert.equal(fixed.interpretation.normalized.gender_resolution,'species_fixed');assert.equal(get(fixed,'details').value,'Blissey, F');
  witness('literal', { actual_constructed_consumer: true, literal_modest_zero_partial_oneHP_oracles: true, lower_level_defaults_presence_clamps_fixed_gender: true, random_gender_not_resolved: true, coherent_rehashed_negatives: true });
});

test('P59 constructed Trace and Schooling retain originals through restoration', async () => {
  for (const effect of ['Trace','Schooling']) {
    const r = recipients(), own = effect==='Trace' ? basic('Gardevoir','Trace') : basic('Wishiwashi','Schooling');
    const s = await create(r, [[own], [basic('Blissey','Natural Cure')]]);
    try {
      const pair=read(s,r.p1), starting=pair.projection.starting, interpretations=pair.projection.original_interpretation, bytes=JSON.stringify(pair), actor=native(s).p1!.active[0];
      if(effect==='Trace') {assert.equal(fact(pair,'ability').value.data,'Trace'); assert.equal(fact(pair,'ability',1,'current').value.data,'naturalcure');}
      else { assert.equal(actor.species.name,'Wishiwashi-School'); assert.equal(fact(pair,'calculated_stats').value.data.atk,76); assert.equal(actor.baseStoredStats.atk,316); assert.equal(fact(pair,'details').value.data,'Wishiwashi, M'); }
      await joint(s,'p1','move 1');
      assert.notEqual(native(s).p1!.active[0],actor); assert.equal(read(s,r.p1).projection.starting,starting); assert.equal(read(s,r.p1).projection.original_interpretation,interpretations); assert.equal(JSON.stringify(pair),bytes);
      s.withOwnedDecisionInput(r.p1,input=>{assert.equal(input.knowledge.projection.starting,starting);checkNativeOwnerDetailsProjection(input.knowledge.projection);return input.legal_indices;});
    } finally {await s.close();}
  }
  witness('initial-effects',{constructed_not_generated_reachability:true,Trace_current_identifier:true,Schooling_changed_current_stats:true,held_fresh_objects_same_originals:true});
});

test('P59 rejects copied source authority and final preparation failure; fresh retry', async () => {
  const register=OriginalOwnerCreation.prototype.registerKnowledgeReceiver;
  for (const fault of ['missing','foreign']) {
    OriginalOwnerCreation.prototype.registerKnowledgeReceiver=function(receiver){return register.call(this, (environment,occurrence,rows)=>{ if(fault==='foreign')receiver(environment,{},rows); });};
    try {await assert.rejects(create(recipients(),[[basic()],[basic()]]),fault==='missing'?/missing-enrollment/:/foreign-knowledge-enrollment/);}
    finally {OriginalOwnerCreation.prototype.registerKnowledgeReceiver=register;}
  }
  const r=recipients(),s=await create(r,[[basic(),{...basic(),name:'Reserve'}],[basic(),{...basic(),name:'OtherReserve'}]]);
  const preflight=NativeOwnerKnowledgeController.prototype.preflight;
  try {
    const pair=read(s,r.p1),handle=s.getOwnerKnowledgeHandle(r.p1),boundary=s.boundary,bytes=JSON.stringify(pair);
    assert.throws(()=>s.readOwnerKnowledge(structuredClone(pair) as any,r.p1),/copied-or-stale/);
    assert.throws(()=>s.readOwnerKnowledge(handle,r.p2),/copied-or-stale/);
    NativeOwnerKnowledgeController.prototype.preflight=function(token){preflight.call(this,token);throw new Error('P59-final-barrier');};
    await assert.rejects(joint(s,'p1','switch 2','switch 2'),/P59-final-barrier/);
    assert.equal(s.boundary,boundary);assert.equal(read(s,r.p1),pair);assert.equal(s.getOwnerKnowledgeHandle(r.p1),handle);assert.equal(JSON.stringify(pair),bytes);
    NativeOwnerKnowledgeController.prototype.preflight=preflight;await joint(s,'p1','switch 2','switch 2');assert.equal(read(s,r.p1).projection.starting,pair.projection.starting);
    const last=s.getOwnerKnowledgeHandle(r.p1);await s.close();assert.throws(()=>s.readOwnerKnowledge(last,r.p1),/closed/);
    witness('authority',{actual_missing_foreign_enrollment_rejections:true,post_preparation_failure:true,committed_pair_retained:true,fresh_retry:true,close_revokes:true});
  } finally {NativeOwnerKnowledgeController.prototype.preflight=preflight;await s.close();}
});
