import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import { Battle, BattleStream, Teams } from 'pokemon-showdown';
import { LocalBattleEnv } from '../src/env_manager';
import { SourceRegistryBuilder } from '../src/perspective_knowledge_source';

type Row = Record<string, any>;
const FORMAT = 'gen9randombattle';
const SEED = [1,2,3,4];
const OPTIONS = {include_wait_requests:true,include_possible_roles:false};
const evidence: Row[] = [];
const team = (text: string) => Teams.import(text)!;
const other = (owner: 'p1'|'p2') => owner === 'p1' ? 'p2' : 'p1';
async function start(own: string, foe: string, owner: 'p1'|'p2') {
  const inputs = {[owner]:team(own),[other(owner)]:team(foe)};
  const originals = structuredClone(inputs);
  const stream = new BattleStream({keepAlive:true});
  await stream.write([
    `>start ${JSON.stringify({formatid:FORMAT,seed:SEED})}`,
    ...(['p1','p2'] as const).map(p => `>player ${p} ${JSON.stringify({name:p,team:Teams.pack(inputs[p])})}`),
  ].join('\n'));
  return {stream,battle:(stream as any).battle as Battle,originals};
}

test('actual environment generates and packs two arrays before submission; production original authority is absent', async () => {
  const generate = Teams.generate, pack = Teams.pack;
  const arrays: Row[][] = [], submitted: string[] = [], events: string[] = [];
  Teams.generate = function(...args: Parameters<typeof generate>) {
    const value = generate.apply(this,args);
    arrays.push(structuredClone(value)); events.push('generate'); return value;
  };
  Teams.pack = function(value) { const text = pack.call(this,value); submitted.push(text); events.push('pack'); return text; };
  const env = new LocalBattleEnv('prompt22-native',FORMAT,SEED);
  try {
    const result = await env.resetWithOptions(OPTIONS);
    assert.deepEqual(events,['generate','pack','generate','pack']);
    const creationEvents = [...events];
    assert.equal(arrays.length,2); assert.ok(arrays.every(t => t.length === 6));
    const state = env.serializeBattle() as Row;
    for (const [i,owner] of (['p1','p2'] as const).entries()) {
      const line = state.inputLog.find((r: string) => r.startsWith(`>player ${owner} `));
      assert.equal(JSON.parse(line.slice(11)).team,submitted[i]);
      assert.equal(result.requests[owner]!.player,owner);
      assert.ok(arrays[i].every(set => !Object.hasOwn(set,'nature') && Object.hasOwn(set,'role')));
    }
    const registry = new SourceRegistryBuilder().freeze();
    assert.equal(registry.availability.original_provider,'not_adopted');
    assert.deepEqual(registry.availability.initialization_witness_owners,[]);
    evidence.push({case:'native-generation',events:creationEvents,owners:['p1','p2'],sizes:arrays.map(t => t.length),
      original_provider:'not_adopted',raw_keys:arrays[0][0] && Object.keys(arrays[0][0]),
      observation_only:'test-owned tap; no provider or authority adopted'});
  } finally { Teams.generate = generate; Teams.pack = pack; await env.close(); }
});

test('packing cannot reconstruct submission omissions or generator metadata', () => {
  const original = {name:'Same',species:'Snorlax',ability:'Immunity',item:'',moves:['Splash'],
    evs:{hp:0,atk:0,def:0,spa:0,spd:0,spe:0},ivs:{hp:31,atk:31,def:31,spa:31,spd:31,spe:31},role:'control'};
  const copy = structuredClone(original);
  const absent = Teams.pack([original as any]);
  const explicit = Teams.pack([{...original,nature:'',happiness:255,pokeball:'',gender:'',level:100} as any]);
  assert.equal(absent,explicit);
  assert.deepEqual(original,copy);
  const unpacked = Teams.unpack(absent)![0] as any;
  assert.equal(Object.hasOwn(unpacked,'role'),false);
  assert.notDeepEqual(unpacked,original);
  evidence.push({case:'packing-loss',same_packed_bytes:true,original,unpacked,
    implication:'raw pre-pack array required; packed/request/snapshot is not original authority'});
});

for (const owner of ['p1','p2'] as const) {
  test(`initial Trace, Imposter and form effects precede first request for ${owner}`, async () => {
    const controls = [
      {label:'Trace',own:'Alakazam\nAbility: Trace\n- Splash',species:'Alakazam',ability:'naturalcure',move:'splash',originalAbility:'Trace',originalMove:'Splash'},
      {label:'Imposter',own:'Ditto\nAbility: Imposter\n- Transform',species:'Blissey',ability:'naturalcure',move:'softboiled',originalAbility:'Imposter',originalMove:'Transform'},
      {label:'Schooling',own:'Wishiwashi\nAbility: Schooling\nLevel: 100\n- Splash',species:'Wishiwashi-School',ability:'schooling',move:'splash',originalAbility:'Schooling',originalMove:'Splash'},
    ];
    for (const c of controls) {
      const {stream,battle,originals} = await start(c.own,'Blissey\nAbility: Natural Cure\n- Soft-Boiled',owner);
      try {
        const side = battle[owner]!;
        const request = side.activeRequest as any;
        assert.equal(side.active[0].species.name,c.species);
        assert.equal(side.active[0].ability,c.ability);
        assert.equal(request.active[0].moves[0].id,c.move);
        assert.equal(originals[owner][0].ability,c.originalAbility);
        assert.deepEqual(originals[owner][0].moves,[c.originalMove]);
        const witness = battle.log.find(r => r.includes(`[from] ability: ${c.label}`))!;
        assert.ok(witness);
        evidence.push({case:'initial-'+c.label,owner,original:originals[owner][0],
          current_species:c.species,current_ability:c.ability,request_move:c.move,witness});
      } finally { stream.destroy(); }
    }
    const {stream,battle,originals} = await start('Zacian @ Rusted Sword\nAbility: Intrepid Sword\n- Iron Head',
      'Blissey\nAbility: Natural Cure\n- Splash',owner);
    try {
      assert.equal(originals[owner][0].species,'Zacian');
      assert.deepEqual(originals[owner][0].moves,['Iron Head']);
      assert.equal(battle[owner]!.active[0].baseSpecies.name,'Zacian-Crowned');
      assert.deepEqual(battle[owner]!.active[0].baseMoves,['behemothblade']);
      assert.equal((battle[owner]!.activeRequest as any).active[0].moves[0].id,'behemothblade');
      evidence.push({case:'initial-crowned-start',owner,original_species:'Zacian',original_moves:['Iron Head'],
        current_base_species:'Zacian-Crowned',current_base_moves:['behemothblade'],
        implication:'runtime base fields also cannot substitute for pre-effect submission'});
    } finally { stream.destroy(); }
  });

  test(`duplicate identities and actual switch preserve original order only through privileged association for ${owner}`, async () => {
    const own = 'Same (Snorlax)\nAbility: Immunity\n- Splash\n\nSame (Snorlax)\nAbility: Thick Fat\n- Splash';
    const {stream,battle} = await start(own,'Target (Blissey)\nAbility: Natural Cure\n- Splash',owner);
    try {
      const side = battle[owner]!;
      const originalSets = [...side.team];
      const ident = (side.activeRequest as any).side.pokemon.map((p: Row) => p.ident);
      assert.equal(ident[0],ident[1]);
      await stream.write(`>${owner} switch 2\n>${other(owner)} move 1`);
      const currentToOriginal = side.pokemon.map(p => originalSets.indexOf(p.set)+1);
      assert.deepEqual(currentToOriginal,[2,1]);
      assert.equal(side.pokemon[0].position,0);
      const snapshot = structuredClone(battle.toJSON()) as Row;
      const serialized = snapshot.sides[owner === 'p1' ? 0 : 1];
      assert.equal(serialized.team,'21');
      const restored = Battle.fromJSON(snapshot);
      try {
        const s = restored[owner]!;
        assert.deepEqual(s.pokemon.map(p => s.team.indexOf(p.set)+1),[2,1]);
      } finally { restored.destroy(); }
      evidence.push({case:'duplicate-switch-restore',owner,duplicate_idents:ident,
        current_to_original:currentToOriginal,serialized_order:'21',
        authority:'privileged object/order probe only; snapshot cannot supply originals'});
    } finally { stream.destroy(); }
  });

  test(`Illusion display and disclosure do not change the acting object for ${owner}`, async () => {
    const {stream,battle,originals} = await start('Fox (Zoroark)\nAbility: Illusion\n- Splash\n\nMask (Pikachu)\nAbility: Static\n- Splash',
      'Target (Snorlax)\nAbility: Immunity\n- Tackle',owner);
    try {
      const side = battle[owner]!, actor = side.active[0];
      assert.equal(originals[owner][0].species,'Zoroark');
      assert.ok(battle.log.some(r => r.startsWith(`|switch|${owner}a: Mask|Pikachu`)));
      await stream.write(`>${owner} move 1\n>${other(owner)} move 1`);
      assert.equal(side.active[0],actor);
      const replacement = battle.log.find(r => r.startsWith(`|replace|${owner}a: Fox|Zoroark`));
      assert.ok(replacement);
      evidence.push({case:'illusion',owner,original_species:'Zoroark',public_display:'Mask/Pikachu',
        replacement,same_object:true,claim:'display is not an immutable roster certificate'});
    } finally { stream.destroy(); }
  });

  test(`wait, restoration reemit and terminal history cannot create fresh or original delivery for ${owner}`, async () => {
    const {stream,battle} = await start('Attacker (Mewtwo)\nAbility: Pressure\n- Psystrike\n- Splash',
      'Lead (Magikarp)\nAbility: Swift Swim\n- Splash\n\nBench (Snorlax)\nAbility: Immunity\n- Splash',owner);
    const env = new LocalBattleEnv('prompt22-restored-'+owner,FORMAT,SEED);
    try {
      const old = structuredClone(battle[owner]!.activeRequest) as Row;
      await stream.write(`>${owner} move 1\n>${other(owner)} move 1`);
      const state = structuredClone(battle.toJSON()) as Row;
      assert.equal((battle[owner]!.activeRequest as any).wait,true);
      assert.equal((battle[other(owner)]!.activeRequest as any).forceSwitch[0],true);
      const result = await env.resetFromSerialized(state,OPTIONS);
      assert.equal(result.requests[owner]!.wait,true);
      assert.notDeepEqual(result.requests[owner]!.raw,old);
      assert.ok(result.requests[other(owner)]!.force_switch);
      battle.win(owner);
      const terminal = await env.resetFromSerialized(structuredClone(battle.toJSON()) as Row,OPTIONS);
      assert.equal(terminal.requests.p1,null); assert.equal(terminal.requests.p2,null);
      evidence.push({case:'wait-restore-terminal',owner,wait:true,other_forced:true,terminal_requests:[null,null],
        fresh_delivery_authority:'absent; reconstructed delivery is a reemit, not a new original'});
    } finally { stream.destroy(); await env.close(); }
  });
}

test.after(() => {
  if (process.env.PROMPT22_REPORT) fs.writeFileSync(process.env.PROMPT22_REPORT,
    JSON.stringify({scope:'source characterization only; no provider, causal crosswalk or delivery ledger implemented',evidence},null,2)+'\n','utf8');
});
