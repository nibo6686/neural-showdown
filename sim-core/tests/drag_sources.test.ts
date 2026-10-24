import assert from 'node:assert/strict';
import test from 'node:test';
import {BattleActions} from 'pokemon-showdown/dist/sim/battle-actions';
import {SwitchEventHost} from '../src/owner_identity_events';
import {validateRawProtocolRecord} from '../src/observable_state';
import {NATIVE11_CONTEXT} from '../src/version_profile';
import {bornSession, playTo} from './helpers/born_session';

test('Red Card source grammar admits only its native opposing active tag', () => {
  const line = '|-enditem|p1a: Own|Red Card|[of] p2a: Foe';
  validateRawProtocolRecord(line,NATIVE11_CONTEXT);
  for (const wrong of [line.replace('p2a:','p1a:'),line.replace('Red Card','Leftovers'),line+'|[silent]',line.replace('p2a:','p2:')])
    assert.throws(() => validateRawProtocolRecord(wrong,NATIVE11_CONTEXT), /Malformed raw/);
});

for (const owner of ['p1', 'p2'] as const) for (const source of ['Roar', 'Whirlwind', 'Dragon Tail', 'Red Card']) {
  test(`${source} binds the engine-selected native actor for ${owner}`, {timeout:20000}, async () => {
    const other = owner === 'p1' ? 'p2' : 'p1';
    const session = await bornSession({teams:{
      [owner]: `Own (Snorlax)${source === 'Red Card' ? ' @ Red Card' : ''}\n- Splash\n\nBench (Blissey)\n- Splash`,
      [other]: `Foe (Blissey)\n- ${source === 'Red Card' ? 'Tackle' : source}\n\nBackup (Snorlax)\n- Splash`,
    } as any,options:{battle_id:`drag-${source}-${owner}`}});
    try {
      const affected = source === 'Red Card' ? other : owner;
      const before = session.readSwitchEventHolding(session.getSwitchEventHolding(affected),affected);
      await playTo(session,[{[owner]:'move 1',[other]:'move 1'}]);
      const after = session.readSwitchEventHolding(session.getSwitchEventHolding(affected),affected);
      assert.equal(after.events.length,before.events.length+1);
      assert.equal(after.events.at(-1)!.original_slot,2);
      assert.ok(session.boundary.perspectives[affected].observation.protocol_prefix.some(line => line.startsWith(`|drag|${affected}a:`)));
    } finally {await session.close();}
  });
}

const cases = ['foreign-original','nested','foreign-side','outside','zero','two','side','position','unassociated','failed-writer'] as const;
for (const fault of cases) test(`drag frame rejects ${fault} without committing authority`, {timeout:20000}, async () => {
  const attach = SwitchEventHost.prototype.attachRestored;
  SwitchEventHost.prototype.attachRestored = function(env,battle,stream,ticket) {
    const actions = battle.actions as any;
    if (fault === 'foreign-original') actions.dragIn = function(...args: any[]) {return BattleActions.prototype.dragIn.apply(this,args as any);};
    attach.call(this,env,battle,stream,ticket);
    const original = actions.dragIn.bind(actions), switchIn = actions.switchIn.bind(actions);
    const random = battle.getRandomSwitchable.bind(battle);
    if (fault === 'outside') actions.dragIn = (side: any) => switchIn(random(side),0,null,true);
    else if (fault === 'foreign-side') actions.dragIn = () => original({},0);
    else if (fault === 'zero') actions.switchIn = () => true;
    else if (fault === 'position') actions.switchIn = (pokemon: any) => switchIn(pokemon,1,null,true);
    else if (fault === 'failed-writer') actions.switchIn = (...args: any[]) => {switchIn(...args); return false;};
    else if (fault === 'nested' || fault === 'two' || fault === 'side' || fault === 'unassociated') {
      battle.getRandomSwitchable = ((side: any) => {
        if (fault === 'nested') original(side,0);
        if (fault === 'two') switchIn(random(side),0,null,true);
        if (fault === 'side') return battle.p2!.pokemon[1];
        if (fault === 'unassociated') return {side,isActive:false};
        return random(side);
      }) as any;
    }
  };
  let session;
  try {
    session = await bornSession({teams:{p1:'Own (Snorlax)\n- Splash\n\nBench (Blissey)\n- Splash',p2:'Foe (Blissey)\n- Roar\n\nOther (Snorlax)\n- Splash'},options:{battle_id:`drag-fault-${fault}`}});
    const before = session.boundary;
    await assert.rejects(playTo(session,[{p1:'move 1',p2:'move 1'}]), /drag|simulator-error/);
    assert.equal(session.boundary,before);
  } finally {SwitchEventHost.prototype.attachRestored=attach; await session?.close();}
});

test('a native failed drag closes its frame and binds no entry', {timeout:20000}, async () => {
  const session = await bornSession({teams:{p1:'Own (Octillery)\nAbility: Suction Cups\n- Splash\n\nBench (Blissey)\n- Splash',p2:'Foe (Blissey)\n- Roar'},options:{battle_id:'failed-drag'}});
  try {
    await playTo(session,[{p1:'move 1',p2:'move 1'}]);
    assert.equal(session.readSwitchEventHolding(session.getSwitchEventHolding('p1'),'p1').events.length,1);
    await playTo(session,[{p1:'switch 2',p2:'move 1'}]);
    assert.equal(session.boundary.kind,'joint_actionable');
  } finally {await session.close();}
});
