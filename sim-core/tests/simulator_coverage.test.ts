import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { buildLegalActionSet, normalizeRequest } from '../src/action_codec';
import { EffectInventoryError } from '../src/effect_inventory';
import { validateRawProtocolRecord } from '../src/observable_state';
import { PlayerStateExtractor } from '../src/state_extractor';

type TeamSpec = { species: string; moves: string[]; ability?: string; item?: string };

function packedTeam(specs: TeamSpec[]): string {
  return Teams.pack(specs.map(({ species, moves, ability, item }) => ({
    name: species,
    species,
    ability: ability || '',
    item: item || '',
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

test('effect inventory permits classified typed values and keeps raw-only evidence out of typed state', () => {
  const extractor = new PlayerStateExtractor('effect-inventory', 'gen9randombattle', 'p1');
  extractor.consumeChunk([
    '|switch|p1a: Mew|Mew, L50|100/100',
    '|-start|p1a: Mew|glaiverush',
    '|-start|p1a: Mew|fly',
    '|-weather|raindance',
    '|-fieldstart|electricterrain',
    '|-sidestart|p1: P1|stealthrock',
  ].join('\n'));
  assert.ok(extractor.getView().self_team[0].volatiles.includes('glaiverush'));
  assert.ok(!extractor.getView().self_team[0].volatiles.includes('fly'));
  assert.equal(extractor.getView().field.weather, 'raindance');
  assert.ok(extractor.getView().field.pseudo_weather.includes('electricterrain'));
  assert.equal(extractor.getView().field.side_conditions.self.stealthrock, 1);
  assert.doesNotThrow(() => validateRawProtocolRecord('|-sidestart|p1: P1|stealthrock'));
});

test('unknown volatile, field, and side values fail before TypeScript projection', () => {
  const cases = [
    '|-start|p1a: Mew|futurevolatile',
    '|-fieldstart|futurefield',
    '|-sidestart|p1: P1|futuresidecondition',
  ];
  for (const record of cases) {
    const extractor = new PlayerStateExtractor('unknown-effect', 'gen9randombattle', 'p1');
    extractor.consumeChunk('|switch|p1a: Mew|Mew, L50|100/100');
    assert.throws(() => extractor.consumeChunk(record), (error: Error) => {
      assert.ok(error instanceof EffectInventoryError);
      assert.equal((error as EffectInventoryError).code, 'simulator-coverage/v1/unclassified-effect-value');
      return true;
    }, record);
    const view = extractor.getView();
    assert.deepEqual(view.self_team[0].volatiles, [], record);
    assert.deepEqual(view.field.pseudo_weather, [], record);
    assert.deepEqual(view.field.side_conditions.self, {}, record);
  }
});

test('represented value in the wrong typed family fails before TypeScript projection or mutation', () => {
  const extractor = new PlayerStateExtractor('effect-family-mismatch', 'gen9randombattle', 'p1');
  extractor.consumeChunk('|switch|p1a: Mew|Mew, L50|100/100');
  const before = extractor.getView();
  assert.throws(() => extractor.consumeChunk('|-start|p1a: Mew|stealthrock'), (error: Error) => {
    assert.ok(error instanceof EffectInventoryError);
    assert.match(error.message, /family-mismatch:side_condition/);
    return true;
  });
  assert.deepEqual(extractor.getView(), before);
});

test('pinned Costar callback emits and projects its dynamically copied classified volatile', () => {
  const sim = new Battle({
    formatid: 'gen9doublescustomgame',
    seed: [1, 2, 3, 4],
    forceRandomChance: true,
    send: () => undefined,
  } as any);
  sim.setPlayer('p1', { name: 'P1', team: packedTeam([
    { species: 'Mew', moves: ['Splash', 'Tackle'] },
    { species: 'Snorlax', moves: ['Dragon Cheer', 'Protect'] },
    { species: 'Flamigo', ability: 'Costar', moves: ['Protect', 'Tackle'] },
  ]) });
  sim.setPlayer('p2', { name: 'P2', team: packedTeam([
    { species: 'Mew', moves: ['Splash', 'Tackle'] },
    { species: 'Snorlax', moves: ['Splash', 'Tackle'] },
  ]) });
  sim.choose('p1', 'team 123');
  sim.choose('p2', 'team 12');
  sim.choose('p1', 'move 1, move 1 -1');
  sim.choose('p2', 'move 1, move 1');
  sim.choose('p1', 'move 1, switch 3');
  sim.choose('p2', 'move 1, move 1');

  const copied = '|-start|p1b: Flamigo|move: Dragon Cheer|[silent]';
  assert.ok(sim.log.includes(copied));
  const extractor = new PlayerStateExtractor('dynamic-callback-effect', 'gen9doublescustomgame', 'p1');
  const relevantEvidence = sim.log.filter((line) =>
    line.startsWith('|switch|p1a:') || line.startsWith('|switch|p1b:') || line.startsWith('|-start|p1a:') || line.startsWith('|-start|p1b:'));
  extractor.consumeChunk(relevantEvidence.join('\n'));
  const flamigo = extractor.getView().self_team.find((pokemon) => pokemon.species === 'Flamigo');
  assert.ok(flamigo?.volatiles.includes('dragoncheer'));
});

test('coverage checker covers config drift, local source hashing, and reachability routes', () => {
  const checker = path.resolve(__dirname, '../../scripts/check-simulator-coverage.cjs');
  const result = spawnSync(process.execPath, [checker, '--reachability-self-test'], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  assert.match(result.stdout, /format config root drift fails closed/);
  assert.match(result.stdout, /listed lock content changes local source digest/);
  assert.match(result.stdout, /omitting listed lock changes local source digest/);
  assert.match(result.stdout, /missing listed lock source fails closed/);
  assert.match(result.stdout, /direct, indirect, package-only, raw-only, unsupported, and unknown forms route explicitly/);
});
