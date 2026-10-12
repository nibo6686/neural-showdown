import assert from 'node:assert/strict';
import test from 'node:test';
import { BattleStream, Teams } from 'pokemon-showdown';
import { OriginalOwnerCreation } from '../src/original_owner_provider';
import { LocalBattleEnv } from '../src/env_manager';
import { PipelineIntegrationSession } from '../src/pipeline_integration';
import type { PlayerID } from '../src/types';

const labels = { battle_id: 'prompt23', format: 'gen9randombattle', simulator_revision: 'test-only' };
const options = { battle_id: labels.battle_id, format: labels.format, seed: [1,2,3,4] };
const own = (s: PipelineIntegrationSession, p: PlayerID) => s.readOriginalOwnerHolding(s.getOriginalOwnerHolding(p), p);
const literal = () => ({ name: 'Same', species: 'Snorlax', ability: 'Immunity', item: '', moves: ['Splash'],
  evs: { hp:0,atk:0,def:0,spa:0,spd:0,spe:0 }, ivs: { hp:31,atk:31,def:31,spa:31,spd:31,spe:31 }, role: 'control' });
function stage(raw1: any[], raw2: any[]) {
  const c = new OriginalOwnerCreation(labels), env = {}; c.bind(env); c.begin(env);
  const a = c.capture(env, 'p1', raw1), b = c.capture(env, 'p2', raw2);
  c.associate(env, 'p1', Teams.pack(a)); c.associate(env, 'p2', Teams.pack(b));
  return { c, env, a, b };
}

test('literal presence, equal packing, zeros, metadata and recursive detached freezing', () => {
  const first = literal(), second = { ...literal(), nature: undefined, happiness:255, pokeball:'', gender:'', level:100,
    extra: { nested:undefined, values:[0,''] } };
  Object.defineProperty(second, 'hidden', { value: undefined, enumerable:false });
  const { c, env, a, b } = stage([first], [second]);
  assert.throws(() => c.holding('p1'), /inactive/);
  const d1 = c.diagnostic(env, 'p1'), d2 = c.diagnostic(env, 'p2');
  assert.equal(d1.packed_team, 'Same|Snorlax||Immunity|Splash|||||||');
  assert.equal(d1.packed_team, d2.packed_team);
  assert.deepEqual(Object.keys(d1.field_presence[0]), ['name','species','item','ability','moves','nature','evs','gender','ivs','shiny','level','happiness','hpType','pokeball','gigantamax','dynamaxLevel','teraType']);
  assert.equal(d1.field_presence[0].nature, 'omitted');
  assert.equal(d1.field_presence[0].happiness, 'omitted'); assert.equal(d1.field_presence[0].pokeball, 'omitted');
  assert.equal(d2.field_presence[0].nature, 'undefined');
  assert.equal(d2.field_presence[0].gender, 'present');
  const raw = d2.raw_team[0] as any;
  assert.ok(Object.hasOwn(raw, 'nature')); assert.ok(Object.hasOwn(raw.extra, 'nested')); assert.ok(Object.hasOwn(raw, 'hidden'));
  assert.equal(raw.nature, undefined); assert.equal(raw.item, ''); assert.equal(raw.gender, '');
  assert.equal(raw.evs.hp, 0); assert.deepEqual(raw.extra.values, [0,'']);
  assert.deepEqual(d2.non_submitted_fields[0], { generator_metadata:['role'], unsupported:['extra','hidden'] });
  first.moves.push('Tackle'); a[0].moves.push('Rest'); a[0].evs.hp = 4;
  second.extra.values.push('changed'); b[0].ivs.hp = 0; b.reverse();
  assert.deepEqual((d1.raw_team[0] as any).moves, ['Splash']); assert.equal((d1.raw_team[0] as any).evs.hp, 0);
  assert.equal(raw.ivs.hp, 31); assert.deepEqual(raw.extra.values, [0,'']);
  for (const value of [d2, d2.raw_team, raw, raw.moves, raw.evs, raw.ivs, raw.extra, raw.extra.values]) assert.ok(Object.isFrozen(value));
  assert.throws(() => raw.moves.push('Rest'), TypeError); assert.throws(() => { raw.evs.hp = 99; }, TypeError);
  const zero = literal(); zero.ivs.hp = 0;
  const z = stage([zero], [literal()]); assert.equal((z.c.diagnostic(z.env,'p1').raw_team[0] as any).ivs.hp,0);
  assert.equal(z.c.diagnostic(z.env,'p1').packed_team, 'Same|Snorlax||Immunity|Splash||||0,,,,,|||');
  c.activate(); assert.throws(() => c.read(d1, 'p1'), /foreign-or-forged/);
});

test('reference authority rejects copied, transported, owner, occurrence, packed swaps and duplicate issuance', () => {
  const one = stage([literal()], [{...literal(), name:'Other'}]), two = stage([literal()], [literal()]);
  one.c.activate(); two.c.activate(); const handle = one.c.holding('p1');
  for (const forged of [{}, {...handle}, JSON.parse(JSON.stringify(handle)), structuredClone(handle), two.c.holding('p1')]) {
    assert.throws(() => one.c.read(forged,'p1'), /foreign-or-forged/);
  }
  assert.throws(() => one.c.read(handle,'p2'), /foreign-or-forged/);
  assert.throws(() => one.c.read(handle,'p1',one.c.read(one.c.holding('p2'),'p2').packed_team), /association-mismatch/);
  assert.throws(() => one.c.activate(), /not-staged/); assert.throws(() => one.c.begin(one.env), /duplicate-or-foreign/);
  assert.throws(() => one.c.bind({}), /duplicate-enrollment/);
  one.c.revoke(); assert.throws(() => one.c.read(handle,'p1'), /foreign-or-forged/);
});

test('missing either owner and foreign enrollment cannot activate partial authority', () => {
  for (const owner of ['p1','p2'] as const) {
    const c = new OriginalOwnerCreation(labels), env = {}; c.bind(env);
    assert.throws(() => c.begin({}), /foreign/); c.begin(env);
    const raw = c.capture(env,owner,[literal()]); c.associate(env,owner,Teams.pack(raw as any));
    assert.throws(() => c.abandonForRestore(env), /restore-forbidden/);
    assert.throws(() => c.activate(), /not-staged/); assert.throws(() => c.diagnostic(env,owner), /not-staged/);
    assert.throws(() => c.capture(env,owner,[literal()]), /invalid-capture/);
    c.abortStaging(); assert.throws(() => c.holding(owner), /inactive/);
  }
});

test('restore abandonment requires the exact unstarted enrollment; staged state cannot be bypassed', () => {
  const c=new OriginalOwnerCreation(labels), env={}; c.bind(env);
  assert.throws(()=>c.abandonForRestore({}),/restore-forbidden/);
  c.abandonForRestore(env); assert.equal(c.activate(),false);
  assert.throws(()=>c.holding('p1'),/inactive/); assert.throws(()=>c.holding('p2'),/inactive/);
  assert.throws(()=>c.begin(env),/duplicate-or-foreign/); assert.throws(()=>c.abandonForRestore(env),/restore-forbidden/);
  const staged=stage([literal()],[literal()]);
  assert.throws(()=>staged.c.abandonForRestore(staged.env),/restore-forbidden/);
  staged.c.activate(); assert.throws(()=>staged.c.abandonForRestore(staged.env),/restore-forbidden/);
  staged.c.revoke(); assert.throws(()=>staged.c.abandonForRestore(staged.env),/restore-forbidden/);
});

test('legacy unstarted serialized restore preserves old session behavior without either original authority', async () => {
  const reset=LocalBattleEnv.prototype.resetWithOptions;
  const donor=new LocalBattleEnv('restore-donor',options.format,options.seed);
  let session:PipelineIntegrationSession|undefined;
  try {
    await donor.reset(); const snapshot=donor.serializeBattle();
    LocalBattleEnv.prototype.resetWithOptions=function(opts) { return this.resetFromSerialized(structuredClone(snapshot),opts); };
    session=await PipelineIntegrationSession.create(options);
    for(const p of ['p1','p2'] as const) assert.throws(()=>session!.getOriginalOwnerHolding(p),/inactive/);
    await session.step();
    for(const p of ['p1','p2'] as const) assert.throws(()=>session!.getOriginalOwnerHolding(p),/inactive/);
    await session.close(); assert.throws(()=>session!.getOriginalOwnerHolding('p1'),/inactive/);
    LocalBattleEnv.prototype.resetWithOptions=function(opts) { return this.resetFromSerialized({ended:true},opts); };
    await assert.rejects(PipelineIntegrationSession.create(options));
  } finally { LocalBattleEnv.prototype.resetWithOptions=reset; await session?.close(); await donor.close(); }
});

test('literal presence and roster/move order survive the actual creation route', async () => {
  const input = [
    [{ ...literal(), moves:['Splash','Rest'], extra:{ value:undefined } }, { ...literal(), name:'Bench', ability:'Thick Fat' }],
    [{ ...literal(), nature:undefined, gender:'', happiness:255, pokeball:'', extra:{ value:undefined } },
      { ...literal(), name:'Bench', nature:'', ivs:{ ...literal().ivs,hp:0 } }],
  ];
  const expected=structuredClone(input), generate=Teams.generate, pack=Teams.pack;
  const packed: string[]=[]; let calls=0;
  Teams.generate=function() { return input[calls++] as any; };
  Teams.pack=function(team) { const value=pack.call(this,team); packed.push(value); return value; };
  let s: PipelineIntegrationSession | undefined;
  try {
    s=await PipelineIntegrationSession.create(options);
    for(const [i,p] of (['p1','p2'] as const).entries()) {
      const evidence=own(s,p); assert.deepEqual(evidence.raw_team,expected[i]); assert.equal(evidence.packed_team,packed[i]);
      assert.deepEqual(evidence.raw_team.map((set:any)=>set.name),['Same','Bench']);
      assert.ok(Object.hasOwn((evidence.raw_team[0] as any).extra,'value'));
      assert.deepEqual(evidence.non_submitted_fields[0],{generator_metadata:['role'],unsupported:['extra']});
      input[i].reverse(); input[i][0].moves.push('Tackle'); input[i][0].evs.hp=252;
      assert.deepEqual(evidence.raw_team,expected[i]);
    }
    assert.equal(own(s,'p1').field_presence[0].nature,'omitted');
    assert.equal(own(s,'p2').field_presence[0].nature,'undefined');
    assert.equal((own(s,'p2').raw_team[1] as any).ivs.hp,0);
  } finally { Teams.generate=generate; Teams.pack=pack; await s?.close(); }
});

test('duplicate nicknames stage intact but existing boundary rejection cannot activate originals', async () => {
  const generate=Teams.generate, activate=OriginalOwnerCreation.prototype.activate, reset=LocalBattleEnv.prototype.resetWithOptions;
  const expected=[literal(),{...literal(),ability:'Thick Fat'}]; let env:LocalBattleEnv|undefined, activated=0;
  Teams.generate=function() { return structuredClone(expected) as any; };
  OriginalOwnerCreation.prototype.activate=function() { activated++; return activate.call(this); };
  LocalBattleEnv.prototype.resetWithOptions=async function(...args) {
    env=this; const result=await reset.apply(this,args);
    assert.deepEqual(this.inspectStagedOriginalOwner('p1').raw_team,expected);
    assert.deepEqual(this.inspectStagedOriginalOwner('p2').raw_team,expected); return result;
  };
  try {
    await assert.rejects(PipelineIntegrationSession.create(options), /Public health evidence mismatch: p1: Same requires exactly one self_team row/);
    assert.equal(activated,0); assert.throws(()=>env!.inspectStagedOriginalOwner('p1'),/not-staged/);
  } finally {Teams.generate=generate; OriginalOwnerCreation.prototype.activate=activate; LocalBattleEnv.prototype.resetWithOptions=reset;}
});

test('actual native session captures both six-member teams before payload; packing input is detached', async () => {
  const generate = Teams.generate, pack = Teams.pack, reset = LocalBattleEnv.prototype.resetWithOptions;
  const write = BattleStream.prototype.write;
  let env: LocalBattleEnv | undefined, writes = 0; const raw: any[][] = [], generated: any[][] = [], packed: string[] = [], packing: any[][] = [];
  Teams.generate = function(...args) { const team = generate.apply(this,args); raw.push(structuredClone(team)); generated.push(team); return team; };
  Teams.pack = function(team) { packing.push(team!); const bytes = pack.call(this,team); packed.push(bytes); return bytes; };
  LocalBattleEnv.prototype.resetWithOptions = async function(...args) { env = this; return reset.apply(this,args); };
  BattleStream.prototype.write = function(input: any) {
    if (typeof input === 'string' && input.startsWith('>start')) {
      writes++;
      for (const [i,p] of (['p1','p2'] as const).entries()) {
        const d = env!.inspectStagedOriginalOwner(p); assert.deepEqual(d.raw_team,raw[i]); assert.equal(d.raw_team.length,6);
        assert.equal(d.packed_team,packed[i]); assert.equal(JSON.parse(input.split('\n')[i+1].slice(11)).team,d.packed_team);
        assert.notEqual(d.raw_team,packing[i]); assert.notEqual(d.raw_team[0],packing[i][0]);
        (packing[i][0] as any).moves.push('test-only-after-pack');
        generated[i].reverse(); generated[i][0].moves.push('generated-after-pack'); generated[i][0].evs.hp=0; generated[i][0].ivs.hp=0;
        assert.deepEqual(d.raw_team,raw[i]);
      }
    }
    return write.call(this,input);
  };
  let s: PipelineIntegrationSession | undefined;
  try {
    s = await PipelineIntegrationSession.create(options); assert.equal(writes,1);
    for (const [i,p] of (['p1','p2'] as const).entries()) {
      assert.deepEqual(own(s,p).raw_team,raw[i]); assert.equal(own(s,p).packed_team,packed[i]);
      assert.ok(raw[i].every(set => Object.hasOwn(set,'role') && !Object.hasOwn(set,'nature')));
      assert.equal(own(s,p).creation_cursor,0); assert.equal(own(s,p).creation_sequence,0);
    }
    assert.throws(() => env!.inspectStagedOriginalOwner('p1'), /not-staged/);
    await assert.rejects(env!.reset(), /duplicate-or-foreign/);
    await assert.rejects(env!.resetFromSerialized(env!.serializeBattle()), /restore-forbidden/);
  } finally { Teams.generate=generate; Teams.pack=pack; LocalBattleEnv.prototype.resetWithOptions=reset; BattleStream.prototype.write=write; await s?.close(); }
});

for (const owner of ['p1','p2'] as const) {
  test(`synthetic initial effects retain pre-effect originals through actual session provider for ${owner}`, async () => {
    const cases = [
      { label:'Trace', text:'Alakazam\nAbility: Trace\n- Splash', species:'Alakazam', current:'Alakazam', ability:'naturalcure', originalAbility:'Trace', originalMove:'Splash', move:'splash' },
      { label:'Imposter', text:'Ditto\nAbility: Imposter\n- Transform', species:'Ditto', current:'Blissey', ability:'naturalcure', originalAbility:'Imposter', originalMove:'Transform', move:'softboiled' },
      { label:'Schooling', text:'Wishiwashi\nAbility: Schooling\nLevel: 100\n- Splash', species:'Wishiwashi', current:'Wishiwashi-School', ability:'schooling', originalAbility:'Schooling', originalMove:'Splash', move:'splash' },
      { label:'Crowned', text:'Zacian @ Rusted Sword\nAbility: Intrepid Sword\n- Iron Head', species:'Zacian', current:'Zacian-Crowned', ability:'intrepidsword', originalAbility:'Intrepid Sword', originalMove:'Iron Head', move:'behemothblade' },
    ];
    for (const c of cases) {
      const generate = Teams.generate; let calls = 0;
      Teams.generate = function() { const p = calls++ === 0 ? 'p1':'p2'; return Teams.import(p===owner ? c.text : 'Blissey\nAbility: Natural Cure\n- Soft-Boiled')!; };
      let s: PipelineIntegrationSession | undefined;
      try {
        s = await PipelineIntegrationSession.create({...options,battle_id:`prompt23-${owner}-${c.label}`});
        const original = own(s,owner).raw_team[0] as any;
        assert.equal(original.species,c.species); assert.equal(original.ability,c.originalAbility); assert.deepEqual(original.moves,[c.originalMove]);
        const env = (s as any).environment as LocalBattleEnv, battle = (env as any).battleStream.battle;
        assert.equal(battle[owner].active[0].species.name,c.current); assert.equal(battle[owner].active[0].ability,c.ability);
        assert.equal(battle[owner].activeRequest.active[0].moves[0].id,c.move);
        if (c.label==='Crowned') assert.deepEqual(battle[owner].active[0].baseMoves,['behemothblade']);
        const other = owner==='p1' ? 'p2':'p1'; assert.equal((own(s,other).raw_team[0] as any).species,'Blissey');
      } finally { Teams.generate=generate; await s?.close(); }
    }
  });
}

test('session isolation, successful replacement, rejection, bare restore, synchronous close revocation', async () => {
  const s = await PipelineIntegrationSession.create(options), twin = await PipelineIntegrationSession.create(options);
  const handle = s.getOriginalOwnerHolding('p1'), original = own(s,'p1'), env = (s as any).environment as LocalBattleEnv;
  const diagnostic = LocalBattleEnv.prototype.diagnostics, close = LocalBattleEnv.prototype.close;
  const restored = new LocalBattleEnv('bare',options.format,options.seed);
  try {
    assert.throws(() => twin.readOriginalOwnerHolding(handle,'p1'), /foreign-or-forged/);
    assert.throws(() => s.readOriginalOwnerHolding(handle,'p2'), /foreign-or-forged/);
    const serialized = env.serializeBattle(); await restored.resetFromSerialized(serialized);
    assert.throws(() => restored.inspectStagedOriginalOwner('p1'), /no-creation/);
    LocalBattleEnv.prototype.diagnostics = function() { const d = diagnostic.call(this) as any;
      return this.id.includes('pipeline-step-') ? {...d,players:{...d.players,p1:{...d.players.p1,last_choice_error:{message:'synthetic rejection'}}}} : d; };
    await assert.rejects(s.step(), /rejected-action/); assert.equal(own(s,'p1'),original);
    LocalBattleEnv.prototype.diagnostics = diagnostic;
    const next = await s.step(); assert.equal(next.boundary.step_index,1); assert.notEqual((s as any).environment,env);
    assert.equal(own(s,'p1'),original); assert.equal(s.getOriginalOwnerHolding('p1'),handle);
    const wire = JSON.stringify({snapshot:serialized,boundary:s.boundary,next,diagnostics:env.diagnostics()});
    assert.ok(!wire.includes('raw_team') && !wire.includes('packed_team') && !wire.includes('field_presence'));
    LocalBattleEnv.prototype.close = async function() { assert.throws(() => s.readOriginalOwnerHolding(handle,'p1'), /foreign-or-forged/);
      await close.call(this); throw new Error('synthetic cleanup failure'); };
    await assert.rejects(s.close(), /cleanup failure/); assert.throws(() => s.getOriginalOwnerHolding('p1'), /inactive/);
    assert.ok(Object.isFrozen(original.raw_team)); assert.equal(twin.readOriginalOwnerHolding(twin.getOriginalOwnerHolding('p1'),'p1').owner,'p1');
  } finally { LocalBattleEnv.prototype.diagnostics=diagnostic; LocalBattleEnv.prototype.close=close; await s.close(); await twin.close(); await restored.close(); }
});

for (const phase of ['generation','packing','missing-p1','missing-p2','submission','settling','boundary','cleanup'] as const) {
  test(`actual creation ${phase} failure leaves no usable issuance`, async () => {
    const generate=Teams.generate, pack=Teams.pack, write=BattleStream.prototype.write;
    const proto=PipelineIntegrationSession.prototype as any, boundary=proto.buildInitialBoundary;
    const activate=OriginalOwnerCreation.prototype.activate, revoke=OriginalOwnerCreation.prototype.revoke;
    const close=LocalBattleEnv.prototype.close;
    let calls=0, activated=0; const controllers=new Set<OriginalOwnerCreation>(); let escaped: PipelineIntegrationSession | undefined;
    OriginalOwnerCreation.prototype.activate=function() { activated++; return activate.call(this); };
    OriginalOwnerCreation.prototype.revoke=function() { controllers.add(this); return revoke.call(this); };
    if(phase==='generation') Teams.generate=function(...args) { if(++calls===2) throw new Error('synthetic generation failure'); return generate.apply(this,args); };
    if(phase==='missing-p1'||phase==='missing-p2') Teams.generate=function(...args) { return ++calls===(phase==='missing-p1'?1:2) ? [] : generate.apply(this,args); };
    if(phase==='packing') Teams.pack=function(raw) { if(++calls===2) throw new Error('synthetic packing failure'); return pack.call(this,raw); };
    if(phase==='submission') BattleStream.prototype.write=function(input:any) { if(typeof input==='string' && input.startsWith('>start')) throw new Error('synthetic submission failure'); return write.call(this,input); };
    if(phase==='boundary'||phase==='cleanup') proto.buildInitialBoundary=function() { escaped=this; assert.throws(()=>this.getOriginalOwnerHolding('p1'),/inactive/); throw new Error('synthetic boundary failure'); };
    if(phase==='cleanup') LocalBattleEnv.prototype.close=async function() { await close.call(this); throw new Error('synthetic cleanup failure'); };
    try {
      await assert.rejects(PipelineIntegrationSession.create({...options,settling:phase==='settling'?{max_messages:1}:undefined}), /synthetic|settling|invalid-team/);
      assert.equal(activated,0); assert.ok(controllers.size>0);
      for(const c of controllers) { assert.throws(()=>c.holding('p1'),/inactive/); assert.throws(()=>c.holding('p2'),/inactive/); }
      if(escaped) assert.throws(()=>escaped!.getOriginalOwnerHolding('p1'),/inactive/);
    } finally { Teams.generate=generate; Teams.pack=pack; BattleStream.prototype.write=write; proto.buildInitialBoundary=boundary;
      OriginalOwnerCreation.prototype.activate=activate; OriginalOwnerCreation.prototype.revoke=revoke; LocalBattleEnv.prototype.close=close; }
  });
}
