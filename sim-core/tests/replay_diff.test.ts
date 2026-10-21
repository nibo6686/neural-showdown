import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {Battle, Teams} from 'pokemon-showdown';
import {extractChannelMessages} from 'pokemon-showdown/dist/sim/battle';
import {PlayerStateExtractor} from '../src/state_extractor';
import {compareReplayPublicState} from '../src/replay_public_diff';
import {NATIVE11_CONTEXT} from '../src/version_profile';
const root=path.resolve(__dirname,'../../..');
const {extractReplay}=require(path.join(root,'tools/replay_repro/index.cjs'));
for(const folder of ['replay-repro','replay-extract'])for(const file of fs.readdirSync(path.join(root,'sim-core/tests/fixtures',folder))) {
  test(`public truth differential at decisions, both owners: ${file}`,{timeout:30000},async()=>{
    const replay=JSON.parse(fs.readFileSync(path.join(root,'sim-core/tests/fixtures',folder,file),'utf8'));
    const result=await extractReplay(replay,{diff:true});
    assert.deepEqual(result.failures,[]);assert.ok(result.boundaries>0);assert.ok(result.checks>0);
    assert.deepEqual(result.mismatches,[]);
  });
}
test('differential catches false public values and ignores hidden precision, bench and duration',()=>{
  const b=new Battle({formatid:'gen9randombattle',seed:'1,2,3,4',p1:{name:'One',team:Teams.import('Blissey\nAbility: Natural Cure\n- Splash')!},
    p2:{name:'Two',team:Teams.import('Snorlax\nAbility: Immunity\n- Splash\n\nPikachu\nAbility: Static\n- Splash')!}});
  try {
    b.damage(b.p2.active[0].hp-Math.floor(b.p2.active[0].maxhp/2),b.p2.active[0]);
    const prefix=extractChannelMessages(b.log.join('\n'),[1])[1];
    const tracker=new PlayerStateExtractor('negative','gen9randombattle','p1',NATIVE11_CONTEXT);tracker.consumeChunk(prefix.join('\n'));
    const view=tracker.getView(),before=JSON.stringify(view);
    assert.deepEqual(compareReplayPublicState(b,view,prefix).mismatches,[]);
    const bad=structuredClone(view);bad.opponent_team.find(p=>p.active)!.hp_text='1/100';bad.self_team[0].boosts.atk=1;bad.field.side_conditions.opponent.spikes=2;
    assert.deepEqual(new Set(compareReplayPublicState(b,bad,prefix).mismatches.map(m=>m.fact)),new Set(['hp','boost','side-condition']));
    const opponent=b.p2.active[0],publicHP=opponent.getHealth().shared;opponent.hp--;
    assert.equal(opponent.getHealth().shared,publicHP);opponent.moveSlots[0].pp=1;b.p2.pokemon[1].hp=1;
    b.field.weatherState.duration=79;
    assert.deepEqual(compareReplayPublicState(b,view,prefix).mismatches,[]);assert.equal(JSON.stringify(tracker.getView()),before);
  }finally{b.destroy();}
});
