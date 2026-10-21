import assert from 'node:assert/strict';
import test from 'node:test';
import {Battle, Dex, Teams} from 'pokemon-showdown';
import {extractChannelMessages} from 'pokemon-showdown/dist/sim/battle';
import {NATIVE11_CONTEXT} from '../src/version_profile';
import {PlayerStateExtractor} from '../src/state_extractor';
import {classifyEffectRecord} from '../src/effect_inventory';
import {validateRawProtocolRecord} from '../src/observable_state';

function battle(first='Snorlax\nAbility: Immunity\n- Splash',second='Pikachu\nAbility: Static\n- Splash'):Battle {
  return new Battle({formatid:'gen9randombattle',seed:'1,2,3,4',
    p1:{name:'One',team:Teams.import(first)!},p2:{name:'Two',team:Teams.import(second)!}});
}
function views(b:Battle) {
  const channels=extractChannelMessages(b.log.join('\n'),[1,2]);
  return ([1,2] as const).map(n=>{
    const tracker=new PlayerStateExtractor('classes','gen9randombattle',n===1?'p1':'p2',NATIVE11_CONTEXT);
    tracker.consumeChunk(channels[n].join('\n'));return tracker.getView();
  });
}
for(const id of ['bind','clamp','firespin','infestation','magmastorm','sandtomb','snaptrap','thundercage','whirlpool','wrap']) {
  test(`new binding ID ${id} retains actual public end, without private binding state`,()=>{
    const b=battle();try {
      const target=b.p1.active[0], source=b.p2.active[0];
      assert.equal(target.addVolatile('partiallytrapped',source,Dex.moves.get(id)),true);
      assert.equal(target.removeVolatile('partiallytrapped'),true);
      assert.ok(b.log.some(line=>line.startsWith(`|-end|p1a: Snorlax|${Dex.moves.get(id).name}|[partiallytrapped]`)));
      assert.equal(classifyEffectRecord('-end',Dex.moves.get(id).name,NATIVE11_CONTEXT),'raw-only');
      for(const v of views(b))assert.ok(!v.self_team.concat(v.opponent_team).some(p=>p.volatiles.includes(id)||p.volatiles.includes('partiallytrapped')));
    } finally {b.destroy();}
  });
}
for(let fallen=1;fallen<=5;fallen++)test(`new fallen${fallen} is an emitted raw-only hint`,()=>{
  const b=battle('Kingambit\nAbility: Supreme Overlord\n- Splash');try {
    b.p1.totalFainted=fallen;const p=b.p1.active[0];
    b.singleEvent('Start',p.getAbility(),p.abilityState,p);
    assert.ok(b.log.includes(`|-start|p1a: Kingambit|fallen${fallen}|[silent]`));
    assert.equal(classifyEffectRecord('-start',`fallen${fallen}`,NATIVE11_CONTEXT),'raw-only');
    for(const v of views(b))assert.ok(!JSON.stringify(v).includes(`fallen${fallen}`));
  } finally {b.destroy();}
});
test('Chilly Reception premajor and weather emitters are exact, raw-only preparatory state stays private',()=>{
  const b=battle('Slowking\nAbility: Regenerator\n- Chilly Reception\n\nSnorlax\nAbility: Immunity\n- Splash');try {
    b.makeChoices('move 1','move 1');
    assert.ok(b.log.some(line=>line.includes('|Chilly Reception|[premajor]')));
    for(const v of views(b)){assert.equal(v.field.weather,'snowscape');assert.ok(!v.self_team.some(p=>p.volatiles.includes('chillyreception')));}
  } finally {b.destroy();}
});
test('reviewed Substitute break, removal and copy target retain public lifecycle',()=>{
  const b=battle('Snorlax\nAbility: Immunity\n- Substitute\n\nBlissey\nAbility: Natural Cure\n- Splash','Pikachu\nAbility: Static\n- Tackle');try {
    b.makeChoices('move 1','move 1');assert.ok(b.p1.active[0].volatiles.substitute);
    assert.ok(views(b)[0].self_team.find(p=>p.active)!.volatiles.includes('substitute'));
    const donor=b.p1.active[0],receiver=b.p1.pokemon[1];
    receiver.copyVolatileFrom(donor,'shedtail');
    assert.equal(receiver.volatiles.substitute.target,receiver);
    receiver.clearVolatile();assert.equal(receiver.volatiles.substitute,undefined);
    donor.addVolatile('substitute');donor.removeVolatile('substitute');
    assert.ok(!views(b)[0].self_team.find(p=>p.active)!.volatiles.includes('substitute'));
  } finally {b.destroy();}
});
test('side receiver plumbing triggers Wind Power Charge and announces layered hazards',()=>{
  const b=battle('Kilowattrel\nAbility: Wind Power\n- Tailwind');try {
    b.makeChoices('move 1','move 1');
    assert.ok(b.p1.active[0].volatiles.charge);
    const wind=b.log.findIndex(line=>line.startsWith('|-sidestart|p1:')&&line.includes('Tailwind'));
    const charge=b.log.findIndex(line=>line.startsWith('|-start|p1a: Kilowattrel|Charge'));
    assert.ok(wind>=0 && charge>wind);
    b.p2.addSideCondition('spikes',b.p1.active[0]);b.p2.addSideCondition('spikes',b.p1.active[0]);
    assert.equal(views(b)[0].field.side_conditions.opponent.spikes,2);
  } finally {b.destroy();}
});
test('grammar additions preserve exact clear, silent bench and finite item meanings',()=>{
  const good=['|request|null','|rated|','|rated|Rated battle','|-enditem|p1a: Pikachu|Life Orb|[from] move: Knock Off|[of] p2a: Snorlax',
    '|-item|p1a: Trevenant|Sitrus Berry|[from] ability: Harvest','|-damage|p1a: Pikachu|80/100|[from] move: Whirlpool|[partiallytrapped]',
    '|detailschange|p1: Terapagos|Terapagos, L77, F|[silent]'];
  for(const line of good)assert.doesNotThrow(()=>validateRawProtocolRecord(line,NATIVE11_CONTEXT),line);
  for(const line of ['|request|','|request| null','|request|[]','|request|{"rqid":null}','|rated| ','|rated||extra',
    '|-item|p1a: Trevenant|Life Orb|[from] ability: Harvest','|-item|p1a: Trevenant|Imaginary Orb',
    '|detailschange|p1: Terapagos|Terapagos|[silently]','|detailschange|p3: Terapagos|Terapagos|[silent]',
    '|detailschange|p1:  Terapagos|Terapagos|[silent]','|-damage|p1a: Pikachu|80/100|[from] move: Splash|[partiallytrapped]',
    '|-damage|p1a: Pikachu|80/100|[partiallytrapped]'])assert.throws(()=>validateRawProtocolRecord(line,NATIVE11_CONTEXT),Error,line);
  const tracker=new PlayerStateExtractor('clear','gen9randombattle','p1',NATIVE11_CONTEXT);
  tracker.consumeChunk('|request|{"wait":true}');assert.ok(tracker.getRequest());tracker.consumeChunk('|request|null');assert.equal(tracker.getRequest(),null);
  tracker.consumeChunk('|poke|p1|Terapagos, L77, F|\n|detailschange|p1: Terapagos|Terapagos, L77, F|[silent]');
  assert.equal(tracker.getView().self_team[0].hp_text,null);assert.equal(tracker.getView().self_team[0].status_source,'unknown');
});

for(const [id,species,ability] of [['sunnyday','Ninetales','Drought'],['raindance','Pelipper','Drizzle'],['snowscape','Abomasnow','Snow Warning'],['sandstorm','Hippowdon','Sand Stream']])test(`reviewed ${id} public start/end survives effectiveWeather changes`,()=>{
  const b=battle(`${species}\nAbility: ${ability}\n- Splash`);try {
    assert.equal(views(b)[0].field.weather,id);b.field.clearWeather();assert.equal(views(b)[0].field.weather,'none');
  }finally{b.destroy();}
});
for(const [id,species,ability] of [['electricterrain','Pincurchin','Electric Surge'],['grassyterrain','Rillaboom','Grassy Surge'],['psychicterrain','Indeedee','Psychic Surge'],['mistyterrain','Weezing-Galar','Misty Surge']])test(`reviewed ${id} declaration retains explicit public lifecycle`,()=>{
  const b=battle(`${species}\nAbility: ${ability}\n- Splash`);try {
    if(id==='mistyterrain'){assert.throws(()=>views(b),/unsupported generated terrain/);return;}
    assert.equal(views(b)[0].field.terrain,id);b.field.clearTerrain();assert.equal(views(b)[0].field.terrain,null);
  }finally{b.destroy();}
});
for(const id of ['encore','disable','healblock'])test(`reviewed ${id} retains emitted start/end and raw-only private duration`,()=>{
  const b=battle();try {
    b.makeChoices('move 1','move 1');const p=b.p1.active[0];
    assert.equal(p.addVolatile(id,b.p2.active[0],Dex.moves.get(id)),true);
    assert.equal(p.removeVolatile(id),true);
    assert.ok(b.log.some(l=>l.startsWith('|-start|')&&l.toLowerCase().replace(/[^a-z]/g,'').includes(id)));
    assert.ok(b.log.some(l=>l.startsWith('|-end|')&&l.toLowerCase().replace(/[^a-z]/g,'').includes(id)));
    for(const v of views(b))assert.ok(!v.self_team.some(p=>p.volatiles.includes(id)));
  }finally{b.destroy();}
});
for(const [id,move] of [['spikes','ceaselessedge'],['stealthrock','stoneaxe']])test(`reviewed ${id} callback announces placement for a fainted setter`,()=>{
  const b=battle('Smeargle\nAbility: Own Tempo\n- Splash\n\nBlissey\nAbility: Natural Cure\n- Splash','Snorlax @ Rocky Helmet\nAbility: Immunity\n- Splash');try {
    const source=b.p1.active[0];b.damage(source.hp,source,b.p2.active[0],Dex.items.get('rockyhelmet'));b.faintMessages();
    b.singleEvent('AfterHit',Dex.moves.get(move),{},b.p2.active[0],source,Dex.getActiveMove(move));
    assert.equal(b.p1.active[0].hp,0);assert.ok(b.p2.sideConditions[id]);
    assert.equal(views(b)[0].field.side_conditions.opponent[id],1);
  }finally{b.destroy();}
});
test('reviewed Leech Seed and Rapid Spin retain explicit cleanup records',()=>{
  const b=battle();try {
    b.p1.active[0].addVolatile('leechseed',b.p2.active[0],Dex.moves.get('leechseed'));
    b.actions.useMove('rapidspin',b.p1.active[0],{target:b.p2.active[0]});
    assert.ok(b.log.some(l=>l.startsWith('|-end|p1a: Snorlax|Leech Seed|')));assert.equal(b.p1.active[0].volatiles.leechseed,undefined);views(b);
  }finally{b.destroy();}
});
test('reviewed Illusion skips called-back reveal without manufacturing an end',()=>{
  const b=battle('Zoroark\nAbility: Illusion\n- Splash\n\nPikachu\nAbility: Static\n- Splash');try {
    const p=b.p1.active[0],cursor=b.log.length;p.beingCalledBack=true;b.singleEvent('End',p.getAbility(),p.abilityState,p);
    assert.ok(!b.log.slice(cursor).some(l=>l.startsWith('|replace|')||l.includes('|Illusion')));views(b);
  }finally{b.destroy();}
});
test('reviewed Future Sight emits resolution before health without projecting slot timers',()=>{
  const b=battle('Xatu\nAbility: Synchronize\n- Future Sight\n- Splash','Snorlax\nAbility: Immunity\n- Protect\n- Splash');try {
    b.makeChoices('move 1','move 2');b.makeChoices('move 2','move 2');b.makeChoices('move 2','move 1');
    const end=b.log.findIndex(l=>l.startsWith('|-end|p2a: Snorlax|move: Future Sight'));
    assert.ok(end>=0);assert.ok(b.log.slice(end+1).some(l=>l.startsWith('|-damage|p2a: Snorlax|')));
    assert.equal(views(b)[1].self_team.find(p=>p.active)!.hp_text,b.p2.active[0].getHealth().secret.split(' ')[0]);
  }finally{b.destroy();}
});
test('reviewed freeze no longer bypasses prevention for a non-Fire Burn Up',()=>{
  const b=battle('Arcanine\nAbility: Intimidate\n- Burn Up');try {
    b.randomChance=()=>false;const p=b.p1.active[0];p.setType('Water');p.setStatus('frz',b.p2.active[0]);
    b.makeChoices('move 1','move 1');assert.equal(p.status,'frz');assert.ok(b.log.includes('|cant|p1a: Arcanine|frz'));assert.equal(views(b)[0].self_team.find(p=>p.active)!.status,'frz');
  }finally{b.destroy();}
});
