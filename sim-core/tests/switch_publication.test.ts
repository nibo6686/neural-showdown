import assert from 'node:assert/strict';
import test from 'node:test';
import {assertPublicHealthMatchesEvidence} from '../src/public_health';
import {assertPublicAbilityMatchesEvidence, publicRevealedAbilities} from '../src/public_ability';
import {projectPublicTypedState} from '../src/typed_state_lifecycle';
import {NATIVE11_CONTEXT} from '../src/version_profile';
import {bornSession, playTo} from './helpers/born_session';

for (const owner of ['p1','p2'] as const) {
  test(`public HP uses native multiply-before-divide rounding for ${owner}`, () => {
    const row = {ident:`${owner}: Own`, hp_text:'168/300', hp_ratio:168/300, status:null, fainted:false, active:true};
    const view = {self_team:[row], opponent_team:[]};
    const prefix = [`|switch|${owner}a: Own|Sylveon|56/100`];
    const request = {side:[{ident:row.ident, condition:'168/300', active:true}]};
    for (const authority of [request, null]) {
      assertPublicHealthMatchesEvidence(prefix, owner, view, authority, NATIVE11_CONTEXT);
      for (const wrong of [55,57]) assert.throws(() => assertPublicHealthMatchesEvidence(
        [prefix[0].replace('56/100', `${wrong}/100`)], owner, view, authority, NATIVE11_CONTEXT), /HP disagree/);
    }
  });
  test(`As One components preserve only addressed variant authority for ${owner}`, () => {
    const prefix = [`|switch|${owner}a: Own|Calyrex-Shadow|100/100`, `|-ability|${owner}a: Own|As One`, `|-ability|${owner}a: Own|Unnerve`];
    for (const ability of ['asonespectrier','asoneglastrier']) {
      const row = {ident:`${owner}: Own`, ability, base_ability:ability, ability_state:'known', ability_suppressed:false, active:true, fainted:false, transformed:false, item:null};
      const view = {self_team:[row], opponent_team:[]}, request = {side:[{...row}]};
      assertPublicAbilityMatchesEvidence(prefix, view, request, owner, NATIVE11_CONTEXT);
      const component = ability === 'asonespectrier' ? 'Grim Neigh' : 'Chilling Neigh';
      assertPublicAbilityMatchesEvidence([...prefix,`|-ability|${owner}a: Own|${component}|boost`],view,request,owner,NATIVE11_CONTEXT);
      const wrong = component === 'Grim Neigh' ? 'Chilling Neigh' : 'Grim Neigh';
      assert.throws(() => assertPublicAbilityMatchesEvidence([...prefix,`|-ability|${owner}a: Own|${wrong}|boost`],view,request,owner,NATIVE11_CONTEXT), /contradict/);
      assert.throws(() => assertPublicAbilityMatchesEvidence([prefix[0],prefix[2]],view,request,owner,NATIVE11_CONTEXT), /contradicts/);
      assert.throws(() => assertPublicAbilityMatchesEvidence(prefix, {...view,self_team:[{...row,ability:'unnerve'}]}, {side:[{...row,ability:'unnerve'}]}, owner,NATIVE11_CONTEXT), /contradict/);
    }
    const publicFact = publicRevealedAbilities(prefix,NATIVE11_CONTEXT)[`${owner}: Own`];
    assert.equal(publicFact.ability,null); assert.equal(publicFact.base,null); assert.equal(publicFact.state,'unknown');
  });
  test(`Slow Start faint cleanup requires immediate same-actor silent end for ${owner}`, () => {
    const prefix = [`|switch|${owner}a: Own|Regigigas|100/100`, `|-start|${owner}a: Own|Slow Start`, `|faint|${owner}a: Own`];
    const end = `|-end|${owner}a: Own|Slow Start|[silent]`;
    assert.doesNotThrow(() => projectPublicTypedState([...prefix,end], NATIVE11_CONTEXT));
    for (const suffix of [[`|turn|2`,end], [end.replace('|[silent]','')], [end.replace('Own','Foreign')]])
      assert.throws(() => projectPublicTypedState([...prefix,...suffix],NATIVE11_CONTEXT), /nonactive/);
  });
  test(`born Slow Start retains explicit cleared bench effects for ${owner}`, {timeout:20000}, async () => {
    const other = owner === 'p1' ? 'p2' : 'p1';
    const session = await bornSession({teams:{[owner]:'Own (Regigigas)\nAbility: Slow Start\n- Splash\n\nBench (Blissey)\n- Splash',[other]:'Foe (Blissey)\n- Splash'} as any,options:{battle_id:`slowstart-${owner}`}});
    try {
      assert.deepEqual(session.boundary.perspectives[owner].observation.view.self_team.find(row => row.name === 'Own')!.ability_effects,['slowstart']);
      await playTo(session,[{[owner]:'switch 2',[other]:'move 1'}]);
      assert.deepEqual(session.boundary.perspectives[owner].observation.view.self_team.find(row => row.name === 'Own')!.ability_effects,[]);
    } finally {await session.close();}
  });
}
