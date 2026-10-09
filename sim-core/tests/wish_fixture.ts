import { Battle, Teams } from 'pokemon-showdown';
import type { PlayerID } from '../src/types';

function team(text: string) {
  return Teams.import(text)!;
}

/** Real pinned-engine teams; construction only makes the public lifecycle reproducible. */
export function wishBattle(actor: PlayerID, mode: 'heal' | 'drag' | 'source-faint' | 'recipient-faint' | 'terminal'): Battle {
  const lowHp = mode === 'source-faint' || mode === 'terminal';
  const recipientLowHp = mode === 'recipient-faint';
  const source = team(`Wisher (Blissey)
${lowHp ? 'Level: 1\n' : ''}Ability: Natural Cure
- Wish
- Splash

Recipient (Snorlax)
${recipientLowHp ? 'Level: 1\n' : ''}Ability: Immunity
- Splash

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  const foe = team(`Foe (Skarmory)
Ability: Sturdy
- Stealth Rock
- Splash
- Brave Bird
- Whirlwind

Reserve (Eevee)
Ability: Run Away
- Splash
`);
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? source : foe});
  battle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? source : foe});
  if (mode === 'terminal') {
    // Terminal must occur before the pending slot can resolve, with no hidden
    // reserve used to manufacture a recipient.
    const loneSource = team(`Wisher (Blissey)
Level: 1
Ability: Natural Cure
- Wish
- Splash
`);
    const loneFoe = team(`Foe (Skarmory)
Ability: Sturdy
- Splash
- Explosion
`);
    battle.destroy();
    const terminal = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    terminal.setPlayer('p1', {name: 'One', team: actor === 'p1' ? loneSource : loneFoe});
    terminal.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? loneSource : loneFoe});
    return terminal;
  }
  return battle;
}
