import assert from 'node:assert/strict';
import { Battle, Teams } from 'pokemon-showdown';
import type { PlayerID } from '../src/types';

function team(text: string) { return Teams.import(text)!; }

function prepareBurnedRecipient(battle: Battle, actor: PlayerID) {
  const other = actor === 'p1' ? 'p2' : 'p1';
  // Pinned move execution establishes the status, then Wisher returns to the
  // active slot before the snapshot used by both restored candidates.
  assert.equal(battle.choose(actor, 'switch 2'), true, battle[actor].choice.error);
  assert.equal(battle.choose(other, 'move 1'), true, battle[other].choice.error); // Will-O-Wisp
  assert.equal(battle.choose(actor, 'switch 2'), true, battle[actor].choice.error);
  assert.equal(battle.choose(other, 'move 2'), true, battle[other].choice.error); // Splash
  assert.equal(battle[actor].active[0].name, 'Wisher');
  assert.equal(battle[actor].pokemon[1].status, 'brn');
}

export function healingWishBattle(actor: PlayerID, recipientNeedsHelp: boolean, terminal = false): Battle {
  const source = team(`Wisher (Gardevoir)
Ability: Synchronize
- Healing Wish
- Splash

Recipient (Snorlax)
Ability: Thick Fat
- Splash

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  const foe = team(`Foe (Sableye)
Ability: Prankster
- Will-O-Wisp
- Splash
- Explosion

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? source : foe});
  battle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? source : foe});
  if (terminal) {
    const loneFoe = team(`Foe (Sableye)
Ability: Prankster
- Will-O-Wisp
- Splash
- Explosion
`);
    battle.destroy();
    const terminalBattle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    terminalBattle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? source : loneFoe});
    terminalBattle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? source : loneFoe});
    if (recipientNeedsHelp) prepareBurnedRecipient(terminalBattle, actor);
    return terminalBattle;
  }
  if (recipientNeedsHelp) prepareBurnedRecipient(battle, actor);
  return battle;
}

export function futureSightBattle(actor: PlayerID, mode: 'drag' | 'switch' | 'faint' | 'source-faint' | 'terminal'): Battle {
  const seer = team(`Seer (Slowking)
${mode === 'source-faint' ? 'Level: 1\n' : ''}Ability: Regenerator
- Future Sight
- Roar
- Splash

Switchin (Eevee)
Ability: Run Away
- Splash
`);
  const target = team(`Target (${mode === 'source-faint' ? 'Kyogre' : 'Snorlax'})
Ability: ${mode === 'source-faint' ? 'Drizzle' : 'Thick Fat'}
- Splash
- ${mode === 'source-faint' ? 'Water Spout' : 'Explosion'}

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  const terminalTarget = team(`Target (Snorlax)
Ability: Thick Fat
- Splash
- Explosion
`);
  const result = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  result.setPlayer('p1', {name: 'One', team: actor === 'p1' ? seer : (mode === 'terminal' ? terminalTarget : target)});
  result.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? seer : (mode === 'terminal' ? terminalTarget : target)});
  return result;
}

export function revivalBattle(actor: PlayerID, healer = 'Pawmot') {
  const b = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const own = Teams.import(`First (Snorlax)
Ability: Immunity
- Explosion
- Splash

Second (Electrode)
Ability: Soundproof
- Explosion

Healer (${healer})
- Revival Blessing
- Splash

Healthy (Blissey)
- Splash
`)!;
  const other = Teams.import(`Watcher (Giratina)
Ability: Pressure
- Splash
- Will-O-Wisp

Reserve (Blissey)
- Splash
`)!;
  b.setPlayer('p1', { team: actor === 'p1' ? own : other });
  b.setPlayer('p2', { team: actor === 'p2' ? own : other });
  const turn = (a: string, o = 'move 1') => b.makeChoices(...(actor === 'p1' ? [a, o] : [o, a]) as [string, string]);
  turn('move 2', 'move 2'); // Public burn must be cleared by revival, including opponent view.
  turn('move 1'); b.choose(actor, 'switch 2');
  turn('move 1'); b.choose(actor, 'switch 3');
  turn('move 1');
  return b;
}
