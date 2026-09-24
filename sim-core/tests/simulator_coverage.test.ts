import assert from 'node:assert/strict';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { buildLegalActionSet, normalizeRequest } from '../src/action_codec';
import { PlayerStateExtractor } from '../src/state_extractor';

type TeamSpec = { species: string; moves: string[] };

function packedTeam(specs: TeamSpec[]): string {
  return Teams.pack(specs.map(({ species, moves }) => ({
    name: species,
    species,
    ability: '',
    item: '',
    moves,
    nature: 'Hardy',
    evs: {},
    ivs: {},
    level: 50,
  })) as any);
}

function battle(p1: TeamSpec[], p2: TeamSpec[]): Battle {
  const result = new Battle({
    formatid: 'gen9customgame',
    seed: [1, 2, 3, 4],
    forceRandomChance: true,
    send: () => undefined,
  } as any);
  result.setPlayer('p1', { name: 'P1', team: packedTeam(p1) });
  result.setPlayer('p2', { name: 'P2', team: packedTeam(p2) });
  result.choose('p1', 'team 1');
  result.choose('p2', 'team 1');
  return result;
}

test('pinned Gen 9 simulator emits confusion lifecycle records that project symmetrically', () => {
  const sim = battle(
    [{ species: 'Mew', moves: ['Confuse Ray', 'Splash'] }],
    [{ species: 'Snorlax', moves: ['Splash', 'Tackle'] }],
  );
  sim.choose('p1', 'move 1');
  sim.choose('p2', 'move 1');
  const start = sim.log.find((line) => line === '|-start|p2a: Snorlax|confusion');
  assert.equal(start, '|-start|p2a: Snorlax|confusion');
  assert.ok(sim.sides[1].active[0].volatiles.confusion);

  assert.equal(sim.sides[1].active[0].removeVolatile('confusion'), true);
  assert.ok(sim.log.includes('|-end|p2a: Snorlax|confusion'));

  const prefix = sim.log.filter((line) => line.startsWith('|')).join('\n');
  const p1 = new PlayerStateExtractor('coverage-p1', 'gen9randombattle', 'p1');
  const p2 = new PlayerStateExtractor('coverage-p2', 'gen9randombattle', 'p2');
  p1.consumeChunk(prefix);
  p2.consumeChunk(prefix);
  assert.ok(!p1.getView().opponent_team[0].volatiles.includes('confusion'));
  assert.ok(!p2.getView().self_team[0].volatiles.includes('confusion'));
});

test('pinned Gen 9 simulator emits another volatile and its current request constrains legal choices', () => {
  const substitute = battle(
    [{ species: 'Mew', moves: ['Substitute', 'Splash'] }],
    [{ species: 'Snorlax', moves: ['Splash'] }],
  );
  substitute.choose('p1', 'move 1');
  substitute.choose('p2', 'move 1');
  assert.ok(substitute.sides[0].active[0].volatiles.substitute);
  assert.ok(substitute.log.some((line) => line === '|-start|p1a: Mew|Substitute'));

  const trapped = battle(
    [{ species: 'Mew', moves: ['Mean Look', 'Splash'] }],
    [
      { species: 'Snorlax', moves: ['Splash'] },
      { species: 'Blissey', moves: ['Splash'] },
    ],
  );
  trapped.choose('p1', 'move 1');
  trapped.choose('p2', 'move 1');
  assert.ok(trapped.log.some((line) => line === '|-activate|p2a: Snorlax|trapped'));
  const p2Request = trapped.sides[1].activeRequest as any;
  assert.equal(p2Request.active[0].trapped, true);
  const normalized = normalizeRequest('p2', p2Request);
  const legal = buildLegalActionSet(normalized);
  assert.deepEqual(legal.available_indices, [0]);
  assert.equal(legal.mask.slice(8).some(Boolean), false);
});

test('pinned simulator emits supported cant and multihit-count protocol variants', () => {
  const sleeping = battle(
    [{ species: 'Mew', moves: ['Spore', 'Splash'] }],
    [{ species: 'Snorlax', moves: ['Splash', 'Tackle'] }],
  );
  sleeping.choose('p1', 'move 1');
  sleeping.choose('p2', 'move 2');
  assert.ok(sleeping.log.includes('|cant|p2a: Snorlax|slp'));

  const multihit = battle(
    [{ species: 'Mew', moves: ['Double Slap', 'Splash'] }],
    [{ species: 'Snorlax', moves: ['Splash', 'Tackle'] }],
  );
  multihit.choose('p1', 'move 1');
  multihit.choose('p2', 'move 2');
  assert.ok(multihit.log.some((line) => /^\|-hitcount\|p2a: Snorlax\|[1-9]\d*$/.test(line)));
});
