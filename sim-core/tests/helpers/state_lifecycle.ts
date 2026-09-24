import { Battle, Teams } from 'pokemon-showdown';
import type { PlayerID } from '../../src/types';

export const LIFECYCLE_SEED = [1, 2, 3, 4];
export const LIFECYCLE_OPTIONS = { include_wait_requests: true, include_possible_roles: false };

/** Constructed teams, real pinned gen9 engine moves/protocol; not random-team coverage. */
export function lifecycleBattle(actor: PlayerID): Battle {
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const donor = Teams.import(`Donor (Cyclizar)
Ability: Shed Skin
- Swords Dance
- Substitute
- Shed Tail
- Explosion

Receiver (Snorlax) @ Heavy-Duty Boots
Ability: Immunity
- Splash
`)!;
  const opponent = Teams.import(`Watcher (Skarmory) @ Heavy-Duty Boots
Ability: Sturdy
- Splash
- Whirlwind
- Torment
- Will-O-Wisp

Reserve (Blissey)
Ability: Natural Cure
- Splash
`)!;
  battle.setPlayer('p1', { name: 'One', team: actor === 'p1' ? donor : opponent });
  battle.setPlayer('p2', { name: 'Two', team: actor === 'p2' ? donor : opponent });
  return battle;
}

export function lifecycleChoices(actor: PlayerID, own: string, other = 'move 1'): Record<PlayerID, string> {
  return actor === 'p1' ? { p1: own, p2: other } : { p1: other, p2: own };
}

export function prepareLifecycle(battle: Battle, actor: PlayerID, substitute: boolean): void {
  const boost = lifecycleChoices(actor, 'move 1', 'move 3');
  battle.makeChoices(boost.p1, boost.p2);
  if (substitute) {
    const sub = lifecycleChoices(actor, 'move 2');
    battle.makeChoices(sub.p1, sub.p2);
  }
}

export function illusionBattle(actor: PlayerID, knownTeammate = false): Battle {
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const fox = Teams.import(`Fox (Zoroark)
Ability: Illusion
- Nasty Plot
- Substitute
- Splash

Mask (Snorlax)
Ability: Immunity
- Amnesia
- Splash
`)!;
  if (knownTeammate) fox.reverse();
  const observer = Teams.import(`Observer (Blissey)
Ability: Natural Cure
- Splash
- Round
- Boomburst

Reserve (Snorlax)
Ability: Immunity
- Splash
`)!;
  battle.setPlayer('p1', { name: 'One', team: actor === 'p1' ? fox : observer });
  battle.setPlayer('p2', { name: 'Two', team: actor === 'p2' ? fox : observer });
  return battle;
}

/** Tera stays on the public Illusion appearance until an explicit reveal. */
export function teraIllusionBattle(actor: PlayerID): Battle {
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const teraTeam = Teams.import(`Fox (Zoroark) @ Heavy-Duty Boots
Ability: Illusion
Tera Type: Fire
- Splash
- Explosion

Mask (Snorlax) @ Heavy-Duty Boots
Ability: Immunity
- Splash
`)!;
  const watcher = Teams.import(`Observer (Skarmory) @ Heavy-Duty Boots
Ability: Sturdy
- Splash
- Whirlwind
- Boomburst

Reserve (Blissey) @ Heavy-Duty Boots
Ability: Natural Cure
- Splash
`)!;
  battle.setPlayer('p1', { name: 'One', team: actor === 'p1' ? teraTeam : watcher });
  battle.setPlayer('p2', { name: 'Two', team: actor === 'p2' ? teraTeam : watcher });
  return battle;
}

/** A one-Pokémon battle leaves the last pre-faint request stale at terminal. */
export function teraFaintBattle(actor: PlayerID): Battle {
  const battle = new Battle({ formatid: 'gen9randombattle', seed: '1,2,3,4' });
  const teraTeam = Teams.import(`Flare (Zoroark) @ Heavy-Duty Boots
Ability: Illusion
Tera Type: Fire
- Splash
`)!;
  const watcher = Teams.import(`Watcher (Skarmory) @ Heavy-Duty Boots
Ability: Sturdy
- Splash
- Boomburst
`)!;
  battle.setPlayer('p1', { name: 'One', team: actor === 'p1' ? teraTeam : watcher });
  battle.setPlayer('p2', { name: 'Two', team: actor === 'p2' ? teraTeam : watcher });
  return battle;
}
