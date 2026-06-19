import assert from 'node:assert/strict';
import test from 'node:test';
import { Battle, Teams } from 'pokemon-showdown';
import { estimateDamage } from '../src/damage_calc';

type SetSpec = {
  species: string;
  ability?: string;
  item?: string;
  moves: string[];
  level?: number;
  nature?: string;
  evs?: Record<string, number>;
};

function packedTeam(sets: SetSpec[]): string {
  return Teams.pack(sets.map((set) => ({
    name: set.species,
    species: set.species,
    ability: set.ability || '',
    item: set.item || '',
    moves: set.moves,
    nature: set.nature || 'Hardy',
    evs: set.evs || {},
    ivs: {},
    level: set.level || 50,
  })) as any);
}

function battle(p1: SetSpec[], p2: SetSpec[], seed: [number, number, number, number] = [1, 2, 3, 4]): Battle {
  const instance = new Battle({
    formatid: 'gen9customgame',
    seed,
    forceRandomChance: true,
    send: () => undefined,
  } as any);
  instance.setPlayer('p1', { name: 'P1', team: packedTeam(p1) });
  instance.setPlayer('p2', { name: 'P2', team: packedTeam(p2) });
  instance.choose('p1', 'team 1');
  instance.choose('p2', 'team 1');
  return instance;
}

function choose(instance: Battle, p1: string, p2: string): void {
  instance.choose('p1', p1);
  instance.choose('p2', p2);
}

test('Showdown engine enforces immunity, Protect, Substitute, priority, and Focus Sash', () => {
  const immunity = battle(
    [{ species: 'Snorlax', moves: ['Body Slam'] }],
    [{ species: 'Gengar', ability: 'Cursed Body', moves: ['Splash'] }],
  );
  choose(immunity, 'move 1', 'move 1');
  assert.ok(immunity.log.some((line) => line.includes('|-immune|p2a: Gengar')));

  const protect = battle(
    [{ species: 'Alakazam', moves: ['Protect'] }],
    [{ species: 'Snorlax', moves: ['Body Slam'] }],
  );
  const protectedHp = protect.sides[0].active[0].hp;
  choose(protect, 'move 1', 'move 1');
  assert.equal(protect.sides[0].active[0].hp, protectedHp);
  assert.ok(protect.log.some((line) => line.includes('|-activate|p1a: Alakazam|move: Protect')));

  const substitute = battle(
    [{ species: 'Alakazam', moves: ['Substitute'] }],
    [{ species: 'Blissey', moves: ['Toxic'] }],
  );
  choose(substitute, 'move 1', 'move 1');
  assert.ok(substitute.sides[0].active[0].volatiles['substitute']);
  assert.equal(substitute.sides[0].active[0].status, '');

  const priority = battle(
    [{ species: 'Snorlax', moves: ['Quick Attack'] }],
    [{ species: 'Deoxys-Speed', moves: ['Tackle'] }],
  );
  choose(priority, 'move 1', 'move 1');
  const moveLines = priority.log.filter((line) => line.startsWith('|move|'));
  assert.match(moveLines[0], /p1a: Snorlax\|Quick Attack/);

  const sash = battle(
    [{ species: 'Garchomp', level: 100, moves: ['Earthquake'] }],
    [{ species: 'Pikachu', level: 1, item: 'Focus Sash', ability: 'Static', moves: ['Splash'] }],
  );
  choose(sash, 'move 1', 'move 1');
  assert.equal(sash.sides[1].active[0].hp, 1);
  assert.equal(sash.sides[1].active[0].item, '');
});

test('Showdown engine applies hazards, status, boosts, paralysis speed, and guaranteed critical hits', () => {
  const hazards = battle(
    [{ species: 'Skarmory', moves: ['Stealth Rock', 'Spikes', 'Toxic Spikes', 'Splash'] }],
    [
      { species: 'Blissey', moves: ['Splash'] },
      { species: 'Arcanine', moves: ['Splash'] },
    ],
  );
  choose(hazards, 'move 1', 'move 1');
  choose(hazards, 'move 2', 'move 1');
  choose(hazards, 'move 3', 'move 1');
  assert.ok(hazards.sides[1].sideConditions['stealthrock']);
  assert.ok(hazards.sides[1].sideConditions['spikes']);
  assert.ok(hazards.sides[1].sideConditions['toxicspikes']);
  const arcanineMaxHp = hazards.sides[1].pokemon[1].maxhp;
  choose(hazards, 'move 4', 'switch 2');
  assert.ok(hazards.sides[1].active[0].hp < arcanineMaxHp);
  assert.equal(hazards.sides[1].active[0].status, 'psn');

  const status = battle(
    [{ species: 'Alakazam', moves: ['Thunder Wave'] }],
    [{ species: 'Machamp', ability: 'No Guard', moves: ['Splash'] }],
  );
  choose(status, 'move 1', 'move 1');
  assert.equal(status.sides[1].active[0].status, 'par');

  const boostsAndCrit = battle(
    [{ species: 'Alakazam', moves: ['Calm Mind', 'Frost Breath'] }],
    [{ species: 'Machamp', ability: 'No Guard', moves: ['Bulk Up', 'Tackle'] }],
  );
  choose(boostsAndCrit, 'move 1', 'move 1');
  assert.equal(boostsAndCrit.sides[0].active[0].boosts.spa, 1);
  assert.equal(boostsAndCrit.sides[0].active[0].boosts.spd, 1);
  assert.equal(boostsAndCrit.sides[1].active[0].boosts.atk, 1);
  assert.equal(boostsAndCrit.sides[1].active[0].boosts.def, 1);
  choose(boostsAndCrit, 'move 2', 'move 2');
  assert.ok(boostsAndCrit.log.some((line) => line.includes('|-crit|p2a: Machamp')));

  const speed = battle(
    [{ species: 'Deoxys-Speed', moves: ['Splash', 'Tackle'] }],
    [{ species: 'Mew', moves: ['Thunder Wave', 'Tackle'] }],
  );
  choose(speed, 'move 1', 'move 1');
  assert.equal(speed.sides[0].active[0].status, 'par');
  assert.ok(speed.sides[0].active[0].getActionSpeed() < speed.sides[1].active[0].getActionSpeed());

  for (const statusCase of [
    { move: 'Spore', expected: 'slp' },
    { move: 'Toxic', expected: 'tox' },
    { move: 'Will-O-Wisp', expected: 'brn' },
  ]) {
    const statusBattle = battle(
      [{ species: 'Mew', moves: [statusCase.move] }],
      [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] }],
    );
    choose(statusBattle, 'move 1', 'move 1');
    assert.equal(statusBattle.sides[1].active[0].status, statusCase.expected);
  }

  const scarf = battle(
    [{ species: 'Pikachu', item: 'Choice Scarf', moves: ['Tackle'] }],
    [{ species: 'Garchomp', moves: ['Tackle'] }],
  );
  choose(scarf, 'move 1', 'move 1');
  const scarfMoves = scarf.log.filter((line) => line.startsWith('|move|'));
  assert.match(scarfMoves[0], /p1a: Pikachu\|Tackle/);
});

test('Smogon calc path covers effectiveness, STAB, burn, choice items, weather, terrain, and abilities', () => {
  const neutral = estimateDamage({
    attacker: { species: 'Mew', level: 80 },
    defender: { species: 'Mew', level: 80 },
    move: 'Psychic',
  });
  const superEffective = estimateDamage({
    attacker: { species: 'Pikachu', level: 80 },
    defender: { species: 'Gyarados', level: 80 },
    move: 'Thunderbolt',
  });
  const resisted = estimateDamage({
    attacker: { species: 'Pikachu', level: 80 },
    defender: { species: 'Magnezone', level: 80 },
    move: 'Thunderbolt',
  });
  const immune = estimateDamage({
    attacker: { species: 'Pikachu', level: 80 },
    defender: { species: 'Golem', level: 80 },
    move: 'Thunderbolt',
  });
  assert.equal(neutral.damage_method, 'smogon_calc');
  assert.equal(superEffective.type_effectiveness, 4);
  assert.ok(Number(resisted.type_effectiveness) < 1);
  assert.equal(immune.type_effectiveness, 0);
  assert.equal(immune.max_percent, 0);

  const physical = estimateDamage({
    attacker: { species: 'Garchomp', level: 80 },
    defender: { species: 'Blissey', level: 80 },
    move: 'Earthquake',
  });
  const burned = estimateDamage({
    attacker: { species: 'Garchomp', level: 80, status: 'brn' },
    defender: { species: 'Blissey', level: 80 },
    move: 'Earthquake',
  });
  const banded = estimateDamage({
    attacker: { species: 'Garchomp', level: 80, item: 'Choice Band' },
    defender: { species: 'Blissey', level: 80 },
    move: 'Earthquake',
  });
  assert.ok(burned.average_percent < physical.average_percent);
  assert.ok(banded.average_percent > physical.average_percent);

  const special = estimateDamage({
    attacker: { species: 'Alakazam', level: 80 },
    defender: { species: 'Mew', level: 80 },
    move: 'Psychic',
  });
  const specs = estimateDamage({
    attacker: { species: 'Alakazam', level: 80, item: 'Choice Specs' },
    defender: { species: 'Mew', level: 80 },
    move: 'Psychic',
  });
  assert.ok(specs.average_percent > special.average_percent);

  const dry = estimateDamage({
    attacker: { species: 'Pelipper', level: 80 },
    defender: { species: 'Arcanine', level: 80 },
    move: 'Surf',
  });
  const rain = estimateDamage({
    attacker: { species: 'Pelipper', level: 80 },
    defender: { species: 'Arcanine', level: 80 },
    move: 'Surf',
    field: { weather: 'Rain' },
  });
  const electric = estimateDamage({
    attacker: { species: 'Pikachu', level: 80, ability: 'Lightning Rod' },
    defender: { species: 'Pelipper', level: 80 },
    move: 'Thunderbolt',
    field: { terrain: 'Electric Terrain' },
  });
  const noTerrain = estimateDamage({
    attacker: { species: 'Pikachu', level: 80, ability: 'Lightning Rod' },
    defender: { species: 'Pelipper', level: 80 },
    move: 'Thunderbolt',
  });
  assert.ok(rain.average_percent > dry.average_percent);
  assert.ok(electric.average_percent > noTerrain.average_percent);

  const adaptability = estimateDamage({
    attacker: { species: 'Porygon-Z', level: 80, ability: 'Adaptability' },
    defender: { species: 'Mew', level: 80 },
    move: 'Tri Attack',
  });
  const noDamageAbility = estimateDamage({
    attacker: { species: 'Porygon-Z', level: 80, ability: 'Pressure' },
    defender: { species: 'Mew', level: 80 },
    move: 'Tri Attack',
  });
  assert.ok(adaptability.average_percent > noDamageAbility.average_percent);
});

test('supplied exact stats change Smogon damage ranges and report exact-stat use', () => {
  const low = estimateDamage({
    attacker: { species: 'Mew', level: 80, stats: { spa: 50 } },
    defender: { species: 'Mew', level: 80, stats: { spd: 500 } },
    move: 'Aura Sphere',
  });
  const high = estimateDamage({
    attacker: { species: 'Mew', level: 80, stats: { spa: 500 } },
    defender: { species: 'Mew', level: 80, stats: { spd: 50 } },
    move: 'Aura Sphere',
  });
  assert.ok(high.average_percent > low.average_percent);
  assert.equal(low.used_exact_attacker_stats, true);
  assert.equal(low.used_exact_defender_stats, true);
  assert.equal(high.used_exact_attacker_stats, true);
  assert.equal(high.used_exact_defender_stats, true);
  assert.equal(low.damage_method, 'smogon_calc');
  assert.equal(high.damage_method, 'smogon_calc');
});
