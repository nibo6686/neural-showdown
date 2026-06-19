import assert from 'node:assert/strict';
import test from 'node:test';
import { estimateDamage } from '../src/damage_calc';

const pikachu = {
  species: 'Pikachu',
  level: 80,
  ability: 'Static',
  stats: { hp: 200, atk: 146, def: 120, spa: 196, spd: 140, spe: 216 },
};

test('regression cases for immunities and resistance', () => {
  const gunk = estimateDamage({
    attacker: { species: 'Banette', level: 80, stats: { hp: 220, atk: 240, def: 120, spa: 120, spd: 140, spe: 110 } },
    defender: { species: 'Kingambit', level: 80, hp_fraction: 1 },
    move: 'Gunk Shot',
  });
  assert.equal(gunk.immune, true);
  assert.equal(gunk.type_effectiveness, 0);

  const outrage = estimateDamage({
    attacker: { species: 'Gouging Fire', level: 80 },
    defender: { species: 'Wigglytuff', level: 80, hp_fraction: 1 },
    move: 'Outrage',
  });
  assert.equal(outrage.immune, true);
  assert.equal(outrage.type_effectiveness, 0);

  const accelerock = estimateDamage({
    attacker: { species: 'Lycanroc', level: 80 },
    defender: { species: 'Toedscruel', level: 80, hp_fraction: 1 },
    move: 'Accelerock',
  });
  assert.equal(accelerock.immune, false);
  assert.ok(Number(accelerock.type_effectiveness) < 1);
});

test('live Vivillon-Ocean and Quagsire regressions use Smogon safely', () => {
  const hurricane = estimateDamage({
    attacker: { species: 'Vivillon-Ocean', level: 80, stats: { atk: 100, def: 100, spa: 100, spd: 100, spe: 100 } },
    defender: { species: 'Quagsire', level: 80, hp_fraction: 1, stats: { atk: 100, def: 100, spa: 100, spd: 100, spe: 100 } },
    move: 'Hurricane',
  });
  assert.equal(hurricane.damage_method, 'smogon_calc');
  assert.equal(hurricane.warnings.length, 0);
  assert.ok(hurricane.damage_rolls.length > 0);

  const earthquake = estimateDamage({
    attacker: { species: 'Quagsire', level: 80, stats: { atk: 100, def: 100, spa: 100, spd: 100, spe: 100 } },
    defender: { species: 'Vivillon-Ocean', level: 80, hp_fraction: 1, stats: { atk: 100, def: 100, spa: 100, spd: 100, spe: 100 } },
    move: 'Earthquake',
  });
  assert.equal(earthquake.damage_method, 'smogon_calc');
  assert.equal(earthquake.immune, true);
  assert.equal(earthquake.type_effectiveness, 0);
  assert.equal(earthquake.average_percent, 0);

  const teraBlast = estimateDamage({
    attacker: { species: 'Vivillon-Ocean', level: 80, tera_type: 'Flying', stats: { atk: 100, def: 100, spa: 100, spd: 100, spe: 100 } },
    defender: { species: 'Quagsire', level: 80, hp_fraction: 1, stats: { atk: 100, def: 100, spa: 100, spd: 100, spe: 100 } },
    move: 'Tera Blast',
    use_tera: true,
  });
  assert.equal(teraBlast.damage_method, 'smogon_calc');
  assert.equal(teraBlast.warnings.length, 0);
});

test('non-damaging moves bypass Smogon damage calculation', () => {
  for (const move of ['Sleep Powder', 'Quiver Dance', 'Toxic', 'Spikes']) {
    const result = estimateDamage({
      attacker: { species: 'Vivillon-Ocean', level: 80 },
      defender: { species: 'Quagsire', level: 80, hp_fraction: 1 },
      move,
    });
    assert.equal(result.damage_method, 'non_damaging_move');
    assert.deepEqual(result.damage_rolls, []);
    assert.equal(result.average_percent, 0);
    assert.equal(result.immune, false);
    assert.equal(result.type_effectiveness, null);
    assert.deepEqual(result.warnings, []);
  }
});

test('tera boosting can increase damage', () => {
  const base = estimateDamage({
    attacker: { ...pikachu, tera_type: 'Electric' },
    defender: { species: 'Charizard', level: 80, hp_fraction: 1 },
    move: 'Thunderbolt',
  });
  const tera = estimateDamage({
    attacker: { ...pikachu, tera_type: 'Electric' },
    defender: { species: 'Charizard', level: 80, hp_fraction: 1 },
    move: 'Thunderbolt',
    use_tera: true,
  });
  assert.ok(tera.average_percent > base.average_percent);
  assert.ok(tera.tera_damage_bonus > 0);
});

test('Life Orb, screens, burn, and weather are modeled', () => {
  const normal = estimateDamage({
    attacker: pikachu,
    defender: { species: 'Charizard', level: 80, hp_fraction: 1 },
    move: 'Thunderbolt',
  });
  const lifeOrb = estimateDamage({
    attacker: { ...pikachu, item: 'Life Orb' },
    defender: { species: 'Charizard', level: 80, hp_fraction: 1 },
    move: 'Thunderbolt',
  });
  assert.equal(lifeOrb.item_modifier, 1.3);
  assert.ok(lifeOrb.average_percent > normal.average_percent);

  const screened = estimateDamage({
    attacker: pikachu,
    defender: { species: 'Charizard', level: 80, hp_fraction: 1 },
    move: 'Thunderbolt',
    field: { light_screen: true },
  });
  assert.ok(screened.average_percent < normal.average_percent);

  const physical = estimateDamage({
    attacker: { species: 'Banette', level: 80, status: 'brn' },
    defender: { species: 'Blissey', level: 80, hp_fraction: 1 },
    move: 'Gunk Shot',
  });
  assert.equal(physical.burn_attack_penalty, true);

  const rain = estimateDamage({
    attacker: { species: 'Lapras', level: 80 },
    defender: { species: 'Arcanine', level: 80, hp_fraction: 1 },
    move: 'Surf',
    field: { weather: 'RainDance' },
  });
  const dry = estimateDamage({
    attacker: { species: 'Lapras', level: 80 },
    defender: { species: 'Arcanine', level: 80, hp_fraction: 1 },
    move: 'Surf',
  });
  assert.ok(rain.average_percent > dry.average_percent);
});

test('exact attacker and defender stats override inferred calc stats', () => {
  const lowAttack = estimateDamage({
    attacker: { species: 'Mew', level: 80, stats: { spa: 50 } },
    defender: { species: 'Mew', level: 80, stats: { spd: 500, hp: 400 } },
    move: 'Aura Sphere',
  });
  const highAttack = estimateDamage({
    attacker: { species: 'Mew', level: 80, stats: { spa: 500 } },
    defender: { species: 'Mew', level: 80, stats: { spd: 50, hp: 400 } },
    move: 'Aura Sphere',
  });

  assert.ok(highAttack.min_percent > lowAttack.max_percent);
  assert.equal(lowAttack.used_exact_attacker_stats, true);
  assert.equal(lowAttack.used_exact_defender_stats, true);
  assert.equal(highAttack.damage_method, 'smogon_calc');
  assert.deepEqual(highAttack.warnings, []);
});
