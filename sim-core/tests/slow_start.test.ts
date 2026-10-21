import assert from 'node:assert/strict';
import test from 'node:test';
import {Battle, Teams} from 'pokemon-showdown';
import {assertTypedStateMatchesPublicPrefix, projectPublicTypedState} from '../src/typed_state_lifecycle';
import {PlayerStateExtractor} from '../src/state_extractor';
import {NATIVE11_CONTEXT} from '../src/version_profile';
import {validateRawProtocolRecord} from '../src/observable_state';

function tracker() {
  const t=new PlayerStateExtractor('slow-start','gen9randombattle','p1',NATIVE11_CONTEXT);
  t.consumeChunk('|switch|p1a: Regigigas|Regigigas, L100|100/100');
  return t;
}
for (const end of ['|-end|p1a: Regigigas|Slow Start','|-end|p1a: Regigigas|Slow Start|[silent]']) {
  test(`ability presence clears: ${end}`,()=>{
    const t=tracker();
    assert.equal(t.getView().self_team[0].ability_effects,undefined);
    t.consumeChunk('|-start|p1a: Regigigas|ability: Slow Start');
    const row=t.getView().self_team[0];
    assert.deepEqual(row.ability_effects,['slowstart']);
    assert.ok(!row.volatiles.includes('slowstart'));
    assert.ok(!JSON.stringify(row).includes('counter'));
    t.consumeChunk(end);
    assert.deepEqual(t.getView().self_team[0].ability_effects,[]);
  });
}
test('Slow Start exact grammar rejects malformed neighbours',()=>{
  for(const line of ['|-start|p1a: Regigigas|Slow Start','|-start|p1a: Regigigas|move: Slow Start','|-start|p1a: Regigigas|ability: Slow Start|[silent]',
    '|-end|p1a: Regigigas|ability: Slow Start','|-end|p1a: Regigigas|Slow Start|[silent]|extra',
    '|-end|p1a: Regigigas|Slow Start|[from] ability: Slow Start']) {
    assert.throws(()=>validateRawProtocolRecord(line,NATIVE11_CONTEXT));
  }
});
test('native expiry, End callback and switch-out follow ability state without a public timer',()=>{
  const b=new Battle({formatid:'gen9randombattle',seed:'1,2,3,4',
    p1:{name:'One',team:Teams.import('Regigigas\nAbility: Slow Start\n- Splash\n\nSnorlax\nAbility: Immunity\n- Splash')!},
    p2:{name:'Two',team:Teams.import('Snorlax\nAbility: Immunity\n- Splash')!}});
  try {
    const t=tracker();let cursor=0;
    const feed=()=>{for(const line of b.log.slice(cursor)) t.consumeChunk(line);cursor=b.log.length;};
    feed();assert.deepEqual(t.getView().self_team.find(p=>p.active)!.ability_effects,['slowstart']);
    for(let n=0;n<5;n++) b.makeChoices('move 1','move 1');
    feed();assert.ok(b.log.includes('|-end|p1a: Regigigas|Slow Start'));
    assert.deepEqual(t.getView().self_team.find(p=>p.active)!.ability_effects,[]);
    const mon=b.p1.active[0];b.singleEvent('Start',mon.getAbility(),mon.abilityState,mon);feed();
    b.singleEvent('End',mon.getAbility(),mon.abilityState,mon);feed();
    assert.ok(b.log.includes('|-end|p1a: Regigigas|Slow Start|[silent]'));
    assert.deepEqual(t.getView().self_team.find(p=>p.active)!.ability_effects,[]);
    b.singleEvent('Start',mon.getAbility(),mon.abilityState,mon);feed();
    b.makeChoices('switch 2','move 1');feed();
    assert.deepEqual(t.getView().self_team.find(p=>!p.active)!.ability_effects,[]);
  } finally {b.destroy();}
});

test('retained prefix validates presence and explicit clears without accepting fabricated ability state',()=>{
  const prefix=['|switch|p1a: Regigigas|Regigigas, L100|100/100','|-start|p1a: Regigigas|ability: Slow Start'];
  const t=tracker();t.consumeChunk(prefix[1]);
  assertTypedStateMatchesPublicPrefix(prefix,'p1',t.getView(),undefined,NATIVE11_CONTEXT);
  const changed=structuredClone(t.getView());changed.self_team[0].ability_effects=[];
  assert.throws(()=>assertTypedStateMatchesPublicPrefix(prefix,'p1',changed,undefined,NATIVE11_CONTEXT),/Ability state/);
  assert.throws(()=>assertTypedStateMatchesPublicPrefix(prefix,'p1',{},undefined,NATIVE11_CONTEXT),/Ability state/);
  const empty=tracker().getView();empty.self_team[0].ability_effects=['slowstart'];
  assert.throws(()=>assertTypedStateMatchesPublicPrefix(prefix.slice(0,1),'p1',empty,undefined,NATIVE11_CONTEXT),/Ability state/);
  assert.deepEqual(projectPublicTypedState([...prefix,'|-end|p1a: Regigigas|Slow Start|[silent]'],NATIVE11_CONTEXT).ability_effects_by_ident,{'p1: Regigigas':[]});
});
