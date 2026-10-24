import assert from 'node:assert/strict';
import test from 'node:test';
import {bornSession, playTo} from './helpers/born_session';
import {LocalBattleEnv} from '../src/env_manager';
import {SwitchEventHost} from '../src/owner_identity_events';
import {RequestDeliveryLedger} from '../src/request_delivery_ledger';
import type {PlayerID} from '../src/types';
const other = (owner: PlayerID): PlayerID => owner === 'p1' ? 'p2' : 'p1';
const moves = ['U-turn','Flip Turn','Volt Switch','Parting Shot','Teleport','Shed Tail','Chilly Reception','Baton Pass'];
for (const move of moves) for (const owner of ['p1','p2'] as const) {
  test(`delivered ${move} replacement has a native choice/writer binding for ${owner}`, {timeout: 20000}, async () => {
    const prepare = SwitchEventHost.prototype.prepare; let host: SwitchEventHost | undefined;
    SwitchEventHost.prototype.prepare = function(...args) {host = this; return prepare.apply(this, args);};
    const session = await bornSession({teams: {
      [owner]: `Lead (Snorlax)\nAbility: Immunity\n- ${move}\n- Splash\n\nReserve (Blissey)\n- Splash`,
      [other(owner)]: 'Foe (Blissey)\nAbility: Natural Cure\n- Splash\n\nBackup (Snorlax)\n- Splash',
    } as any, options: {battle_id: `pivot-${move}-${owner}`}});
    try {
      await playTo(session, [{[owner]: 'move 1', [other(owner)]: 'move 1'}]);
      assert.equal(session.boundary.kind, 'one_sided_forced_switch');
      const before = session.readSwitchEventHolding(session.getSwitchEventHolding(owner), owner);
      await playTo(session, [{[owner]: 'switch 2'}]);
      const after = session.readSwitchEventHolding(session.getSwitchEventHolding(owner), owner);
      assert.equal(after.events.length, before.events.length + 1);
      assert.equal(after.events.at(-1)!.original_slot, 2);
      const env = (session as any).environment;
      assert.ok(host!.inspect(env).writers.some(writer => writer.owner === owner && writer.slot === 2 && writer.valid));
      assert.equal(session.boundary.perspectives[owner].observation.view.self_team.find(row => row.active)!.name, 'Reserve');
    } finally {SwitchEventHost.prototype.prepare = prepare; await session.close();}
  });
}

test('switch submissions reject copied, foreign, replayed and different-slot choices before granting a writer', {timeout: 20000}, async () => {
  const submit = LocalBattleEnv.prototype.withCanonicalSubmission, transfer = RequestDeliveryLedger.prototype.prepareSwitchChoices;
  let checked = 0;
  RequestDeliveryLedger.prototype.prepareSwitchChoices = function(...args) {
    const proof = transfer.apply(this, args);
    assert.throws(() => this.consumeSwitchChoices({...proof}, args[0]), /foreign-or-replayed/);
    assert.throws(() => this.consumeSwitchChoices(proof, {} as LocalBattleEnv), /foreign-or-replayed/);
    return proof;
  };
  LocalBattleEnv.prototype.withCanonicalSubmission = function(owner, action, operation) {
    if (action.kind !== 'switch') return submit.call(this, owner, action, operation);
    assert.throws(() => submit.call(this, owner, {...action}, () => {}), /foreign-or-replayed/);
    assert.throws(() => submit.call(this, other(owner), action, () => {}), /foreign-or-replayed/);
    assert.throws(() => submit.call(this, owner, {...action, switch_slot: 3, choice: 'switch 3'}, () => {}), /foreign-or-replayed/);
    submit.call(this, owner, action, operation);
    assert.throws(() => submit.call(this, owner, action, () => {}), /foreign-or-replayed/); checked++;
  };
  let session;
  try {
    session = await bornSession({teams: {p1:'Lead (Snorlax)\n- U-turn\n\nReserve (Blissey)\n- Splash',p2:'Foe (Blissey)\n- Splash'}, options:{battle_id:'choice-negatives'}});
    await playTo(session, [{p1:'move 1',p2:'move 1'},{p1:'switch 2'}]);
    assert.equal(checked, 1);
  } finally {LocalBattleEnv.prototype.withCanonicalSubmission = submit; RequestDeliveryLedger.prototype.prepareSwitchChoices = transfer; await session?.close();}
});
