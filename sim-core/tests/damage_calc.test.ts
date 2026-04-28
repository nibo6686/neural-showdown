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
  assert.ok(accelerock.type_effectiveness < 1);
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
