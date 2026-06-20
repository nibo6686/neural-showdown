import { Battle, Teams } from 'pokemon-showdown';

type SetSpec = {
  species: string;
  ability?: string;
  item?: string;
  moves: string[];
  level?: number;
};

type ParityCase = {
  id: string;
  phase: 'immediate' | 'end_of_turn' | 'switch_entry' | 'delayed_future' | 'sequential_multihit';
  starting_state: Record<string, unknown>;
  chosen_actions: Array<{ p1: string; p2: string }>;
  oracle: Record<string, unknown>;
  local_input?: Record<string, unknown>;
  local_support: 'supported' | 'intentional_gap';
  gap_reason?: string;
};

function packedTeam(sets: SetSpec[]): string {
  return Teams.pack(sets.map(set => ({
    name: set.species,
    species: set.species,
    ability: set.ability || '',
    item: set.item || '',
    moves: set.moves,
    nature: 'Hardy',
    evs: {},
    ivs: {},
    level: set.level || 100,
  })) as any);
}

function battle(
  p1: SetSpec[],
  p2: SetSpec[],
  seed: [number, number, number, number] = [31, 41, 59, 26],
  forceRandomChance = true,
): Battle {
  const instance = new Battle({
    formatid: 'gen9customgame',
    seed,
    forceRandomChance,
    send: () => undefined,
  } as any);
  instance.setPlayer('p1', { name: 'P1', team: packedTeam(p1) });
  instance.setPlayer('p2', { name: 'P2', team: packedTeam(p2) });
  instance.choose('p1', 'team 1');
  instance.choose('p2', 'team 1');
  return instance;
}

function choose(instance: Battle, p1: string, p2: string): string[] {
  const cursor = instance.log.length;
  instance.choose('p1', p1);
  instance.choose('p2', p2);
  return instance.log.slice(cursor);
}

function active(instance: Battle, side: 0 | 1) {
  return instance.sides[side].active[0];
}

function ratio(instance: Battle, side: 0 | 1): number {
  const pokemon = active(instance, side);
  return pokemon.hp / pokemon.maxhp;
}

function residualMon(instance: Battle, side: 0 | 1, extra: Record<string, unknown> = {}): Record<string, unknown> {
  const pokemon = active(instance, side);
  return {
    hp: pokemon.hp,
    max_hp: pokemon.maxhp,
    status: pokemon.status || null,
    types: pokemon.getTypes(),
    ability: pokemon.getAbility().name,
    item: pokemon.getItem().name,
    residual_modifiers_known: true,
    volatiles: {},
    ...extra,
  };
}

function hpConditions(lines: string[], side: 'p1' | 'p2'): number[] {
  const values: number[] = [];
  for (const line of lines) {
    if (!line.startsWith(`|-damage|${side}a:`)) continue;
    const hp = Number((line.split('|')[3] || '').split(' ')[0].split('/')[0]);
    if (Number.isFinite(hp) && values[values.length - 1] !== hp) values.push(hp);
  }
  return values;
}

function damageSequence(lines: string[], side: 'p1' | 'p2', startingHp: number): number[] {
  const values = hpConditions(lines, side);
  const sequence: number[] = [];
  let previous = startingHp;
  for (const hp of values) {
    sequence.push(Math.max(0, previous - hp));
    previous = hp;
  }
  return sequence;
}

function hitCount(lines: string[]): number {
  const line = lines.find(candidate => candidate.includes('|-hitcount|'));
  if (!line) return 0;
  const value = Number(line.split('|').pop());
  return Number.isFinite(value) ? value : 0;
}

function sourceDamageFraction(lines: string[], source: string): number {
  const line = lines.find(candidate => candidate.startsWith('|-damage|') && candidate.includes(source));
  if (!line) return 0;
  const condition = line.split('|')[3] || '';
  const [hpText, maxHpText] = condition.split(' ')[0].split('/');
  const hp = Number(hpText);
  const maxHp = Number(maxHpText);
  return Number.isFinite(hp) && Number.isFinite(maxHp) && maxHp > 0 ? 1 - hp / maxHp : 0;
}

function residualCases(): ParityCase[] {
  const toxic = battle(
    [{ species: 'Mew', moves: ['Toxic', 'Splash'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] }],
  );
  const toxicRatios: number[] = [];
  const toxicHp: number[] = [];
  const toxicMaxHp = active(toxic, 1).maxhp;
  choose(toxic, 'move 1', 'move 1');
  toxicRatios.push(ratio(toxic, 1));
  toxicHp.push(active(toxic, 1).hp);
  choose(toxic, 'move 2', 'move 1');
  toxicRatios.push(ratio(toxic, 1));
  toxicHp.push(active(toxic, 1).hp);
  choose(toxic, 'move 2', 'move 1');
  toxicRatios.push(ratio(toxic, 1));
  toxicHp.push(active(toxic, 1).hp);

  const leech = battle(
    [{ species: 'Mew', moves: ['Leech Seed', 'Splash'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] }],
  );
  active(leech, 0).hp = Math.floor(active(leech, 0).maxhp / 2);
  const leechSourceStart = active(leech, 0).hp;
  const leechSourceMax = active(leech, 0).maxhp;
  const leechTargetStart = active(leech, 1).hp;
  const leechTargetMax = active(leech, 1).maxhp;
  const sourceBefore = ratio(leech, 0);
  const targetBefore = ratio(leech, 1);
  choose(leech, 'move 1', 'move 1');

  const burn = battle(
    [{ species: 'Mew', moves: ['Will-O-Wisp'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] }],
  );
  const burnBefore = ratio(burn, 1);
  const burnMaxHp = active(burn, 1).maxhp;
  choose(burn, 'move 1', 'move 1');

  const poison = battle(
    [{ species: 'Mew', moves: ['Poison Powder'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] }],
  );
  const poisonMaxHp = active(poison, 1).maxhp;
  choose(poison, 'move 1', 'move 1');

  function saltCase(
    id: string,
    target: SetSpec,
    expectedDivisor: number,
  ): ParityCase {
    const instance = battle(
      [{ species: 'Garganacl', moves: ['Salt Cure', 'Splash'] }],
      [target],
    );
    const lines = choose(instance, 'move 1', 'move 1');
    const conditions = hpConditions(lines, 'p2');
    const finalHp = active(instance, 1).hp;
    const preResidualHp = conditions.length >= 2 ? conditions[conditions.length - 2] : finalHp;
    const targetState = residualMon(instance, 1, {
      hp: preResidualHp,
      status: null,
      volatiles: { saltcure: true },
    });
    return {
      id,
      phase: 'end_of_turn',
      starting_state: { p2: { species: target.species, types: active(instance, 1).getTypes(), hp: preResidualHp } },
      chosen_actions: [{ p1: 'Salt Cure', p2: 'Splash' }],
      oracle: {
        snapshots: [{ combatants: { p2: { hp: finalHp } } }],
        residual_damage: preResidualHp - finalHp,
        divisor: expectedDivisor,
        salt_cure_residual_logged: lines.some(line => line.startsWith('|-damage|') && line.includes('Salt Cure')),
      },
      local_input: { turns: 1, state: { combatants: { p2: targetState } } },
      local_support: 'supported',
    };
  }

  const binding = battle(
    [{ species: 'Machamp', ability: 'No Guard', moves: ['Bind'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] }],
  );
  const bindingLines = choose(binding, 'move 1', 'move 1');
  const bindingConditions = hpConditions(bindingLines, 'p2');
  const bindingFinalHp = active(binding, 1).hp;
  const bindingPreResidualHp =
    bindingConditions.length >= 2 ? bindingConditions[bindingConditions.length - 2] : bindingFinalHp;
  const bindingMaxHp = active(binding, 1).maxhp;

  const bindingBand = battle(
    [{ species: 'Machamp', ability: 'No Guard', item: 'Binding Band', moves: ['Bind'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] }],
  );
  const bindingBandLines = choose(bindingBand, 'move 1', 'move 1');
  const bindingBandConditions = hpConditions(bindingBandLines, 'p2');
  const bindingBandFinalHp = active(bindingBand, 1).hp;
  const bindingBandPreResidualHp =
    bindingBandConditions.length >= 2 ? bindingBandConditions[bindingBandConditions.length - 2] : bindingBandFinalHp;
  const bindingBandMaxHp = active(bindingBand, 1).maxhp;

  const unchanged = battle(
    [{ species: 'Mew', moves: ['Splash'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] }],
  );
  const unchangedP1 = residualMon(unchanged, 0);
  const unchangedP2 = residualMon(unchanged, 1);
  choose(unchanged, 'move 1', 'move 1');

  return [
    {
      id: 'toxic_ramp_three_turns',
      phase: 'end_of_turn',
      starting_state: { p2: { species: 'Snorlax', status: null, hp_ratio: 1 } },
      chosen_actions: [
        { p1: 'Toxic', p2: 'Splash' },
        { p1: 'Splash', p2: 'Splash' },
        { p1: 'Splash', p2: 'Splash' },
      ],
      oracle: {
        p2_status: active(toxic, 1).status,
        hp_ratios: toxicRatios,
        snapshots: toxicHp.map((hp, index) => ({ combatants: { p2: { hp, toxic_stage: index + 1 } } })),
      },
      local_input: {
        turns: 3,
        state: {
          combatants: {
            p2: {
              hp: toxicMaxHp,
              max_hp: toxicMaxHp,
              status: 'tox',
              toxic_stage: 0,
              types: ['Normal'],
              ability: 'Thick Fat',
              item: '',
              residual_modifiers_known: true,
              volatiles: {},
            },
          },
        },
      },
      local_support: 'supported',
    },
    {
      id: 'leech_seed_damage_and_heal',
      phase: 'end_of_turn',
      starting_state: { p1: { hp_ratio: sourceBefore }, p2: { hp_ratio: targetBefore } },
      chosen_actions: [{ p1: 'Leech Seed', p2: 'Splash' }],
      oracle: {
        p1_hp_ratio: ratio(leech, 0),
        p2_hp_ratio: ratio(leech, 1),
        snapshots: [{ combatants: { p1: { hp: active(leech, 0).hp }, p2: { hp: active(leech, 1).hp } } }],
      },
      local_input: {
        turns: 1,
        state: {
          combatants: {
            p1: {
              hp: leechSourceStart,
              max_hp: leechSourceMax,
              status: null,
              types: ['Psychic'],
              ability: 'Synchronize',
              item: '',
              residual_modifiers_known: true,
              volatiles: {},
            },
            p2: {
              hp: leechTargetStart,
              max_hp: leechTargetMax,
              status: null,
              types: ['Normal'],
              ability: 'Thick Fat',
              item: '',
              residual_modifiers_known: true,
              volatiles: { leechseed: { source: 'p1' } },
            },
          },
        },
      },
      local_support: 'supported',
    },
    {
      id: 'burn_residual',
      phase: 'end_of_turn',
      starting_state: { p2: { species: 'Snorlax', hp_ratio: burnBefore } },
      chosen_actions: [{ p1: 'Will-O-Wisp', p2: 'Splash' }],
      oracle: {
        p2_status: active(burn, 1).status,
        p2_hp_ratio: ratio(burn, 1),
        snapshots: [{ combatants: { p2: { hp: active(burn, 1).hp } } }],
      },
      local_input: {
        turns: 1,
        state: {
          combatants: {
            p2: {
              hp: burnMaxHp,
              max_hp: burnMaxHp,
              status: 'brn',
              types: ['Normal'],
              ability: 'Thick Fat',
              item: '',
              residual_modifiers_known: true,
              volatiles: {},
            },
          },
        },
      },
      local_support: 'supported',
    },
    {
      id: 'regular_poison_residual',
      phase: 'end_of_turn',
      starting_state: { p2: { species: 'Snorlax', hp_ratio: 1 } },
      chosen_actions: [{ p1: 'Poison Powder', p2: 'Splash' }],
      oracle: {
        p2_status: active(poison, 1).status,
        p2_hp_ratio: ratio(poison, 1),
        snapshots: [{ combatants: { p2: { hp: active(poison, 1).hp } } }],
      },
      local_input: {
        turns: 1,
        state: {
          combatants: {
            p2: {
              hp: poisonMaxHp,
              max_hp: poisonMaxHp,
              status: 'psn',
              types: ['Normal'],
              ability: 'Thick Fat',
              item: '',
              residual_modifiers_known: true,
              volatiles: {},
            },
          },
        },
      },
      local_support: 'supported',
    },
    saltCase(
      'salt_cure_normal_residual',
      { species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] },
      8,
    ),
    saltCase(
      'salt_cure_water_residual',
      { species: 'Vaporeon', ability: 'Water Absorb', moves: ['Splash'] },
      4,
    ),
    saltCase(
      'salt_cure_steel_residual',
      { species: 'Corviknight', ability: 'Pressure', moves: ['Splash'] },
      4,
    ),
    {
      id: 'binding_residual',
      phase: 'end_of_turn',
      starting_state: { p2: { species: 'Snorlax', volatile: 'partiallytrapped' } },
      chosen_actions: [{ p1: 'Bind', p2: 'Splash' }],
      oracle: {
        p2_hp: active(binding, 1).hp,
        snapshots: [{ combatants: { p2: { hp: bindingFinalHp } } }],
        binding_residual_logged: bindingLines.some(
          line => line.startsWith('|-damage|') && line.includes('[from] move: Bind'),
        ),
      },
      local_input: {
        turns: 1,
        state: {
          combatants: {
            p1: {
              hp: active(binding, 0).hp,
              max_hp: active(binding, 0).maxhp,
              status: null,
              types: ['Fighting'],
              ability: 'No Guard',
              item: '',
              residual_modifiers_known: true,
              volatiles: {},
            },
            p2: {
              hp: bindingPreResidualHp,
              max_hp: bindingMaxHp,
              status: null,
              types: ['Normal'],
              ability: 'Thick Fat',
              item: '',
              residual_modifiers_known: true,
              volatiles: {
                partiallytrapped: {
                  source: 'p1',
                  source_active: true,
                  source_effect: 'Bind',
                  duration_remaining: 4,
                  divisor: 8,
                },
              },
            },
          },
        },
      },
      local_support: 'supported',
    },
    {
      id: 'binding_band_residual',
      phase: 'end_of_turn',
      starting_state: { p1_item: 'Binding Band', p2: { species: 'Snorlax', volatile: 'partiallytrapped' } },
      chosen_actions: [{ p1: 'Bind', p2: 'Splash' }],
      oracle: {
        p2_hp: active(bindingBand, 1).hp,
        snapshots: [{ combatants: { p2: { hp: bindingBandFinalHp } } }],
        binding_residual_logged: bindingBandLines.some(
          line => line.startsWith('|-damage|') && line.includes('[from] move: Bind'),
        ),
      },
      local_input: {
        turns: 1,
        state: {
          combatants: {
            p1: {
              hp: active(bindingBand, 0).hp,
              max_hp: active(bindingBand, 0).maxhp,
              status: null,
              types: ['Fighting'],
              ability: 'No Guard',
              item: 'Binding Band',
              residual_modifiers_known: true,
              volatiles: {},
            },
            p2: {
              hp: bindingBandPreResidualHp,
              max_hp: bindingBandMaxHp,
              status: null,
              types: ['Normal'],
              ability: 'Thick Fat',
              item: '',
              residual_modifiers_known: true,
              volatiles: {
                partiallytrapped: {
                  source: 'p1',
                  source_active: true,
                  source_effect: 'Bind',
                  duration_remaining: 4,
                  divisor: 6,
                },
              },
            },
          },
        },
      },
      local_support: 'supported',
    },
    {
      id: 'no_residual_unchanged',
      phase: 'end_of_turn',
      starting_state: { p1: { hp: unchangedP1.hp }, p2: { hp: unchangedP2.hp } },
      chosen_actions: [{ p1: 'Splash', p2: 'Splash' }],
      oracle: {
        snapshots: [{
          combatants: {
            p1: { hp: active(unchanged, 0).hp },
            p2: { hp: active(unchanged, 1).hp },
          },
        }],
      },
      local_input: {
        turns: 1,
        state: { combatants: { p1: unchangedP1, p2: unchangedP2 } },
      },
      local_support: 'supported',
    },
  ];
}

function fieldCases(): ParityCase[] {
  const sand = battle(
    [{ species: 'Mew', moves: ['Sandstorm'] }],
    [{ species: 'Pikachu', ability: 'Static', moves: ['Splash'] }],
  );
  const sandP1 = residualMon(sand, 0);
  const sandP2 = residualMon(sand, 1);
  choose(sand, 'move 1', 'move 1');

  const grassy = battle(
    [{ species: 'Mew', moves: ['Grassy Terrain'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] }],
  );
  active(grassy, 1).hp = Math.floor(active(grassy, 1).maxhp / 2);
  const grassyBefore = ratio(grassy, 1);
  const grassyStart = residualMon(grassy, 1);
  choose(grassy, 'move 1', 'move 1');

  const grassyAirborne = battle(
    [{ species: 'Mew', moves: ['Grassy Terrain'] }],
    [{ species: 'Charizard', ability: 'Blaze', moves: ['Splash'] }],
  );
  active(grassyAirborne, 1).hp = Math.floor(active(grassyAirborne, 1).maxhp / 2);
  const grassyAirborneStart = residualMon(grassyAirborne, 1);
  choose(grassyAirborne, 'move 1', 'move 1');

  return [
    {
      id: 'sandstorm_chip',
      phase: 'end_of_turn',
      starting_state: { weather: null, p2: { species: 'Pikachu', hp_ratio: 1 } },
      chosen_actions: [{ p1: 'Sandstorm', p2: 'Splash' }],
      oracle: {
        weather: sand.field.weather,
        p2_hp_ratio: ratio(sand, 1),
        snapshots: [{
          combatants: {
            p1: { hp: active(sand, 0).hp },
            p2: { hp: active(sand, 1).hp },
          },
        }],
      },
      local_input: {
        turns: 1,
        state: {
          weather: 'sandstorm',
          combatants: { p1: sandP1, p2: sandP2 },
        },
      },
      local_support: 'supported',
    },
    {
      id: 'grassy_terrain_healing',
      phase: 'end_of_turn',
      starting_state: { terrain: null, p2: { species: 'Snorlax', hp_ratio: grassyBefore } },
      chosen_actions: [{ p1: 'Grassy Terrain', p2: 'Splash' }],
      oracle: {
        terrain: grassy.field.terrain,
        p2_hp_ratio: ratio(grassy, 1),
        snapshots: [{ combatants: { p2: { hp: active(grassy, 1).hp } } }],
      },
      local_input: {
        turns: 1,
        state: {
          terrain: 'grassyterrain',
          combatants: { p2: grassyStart },
        },
      },
      local_support: 'supported',
    },
    {
      id: 'grassy_terrain_airborne_no_heal',
      phase: 'end_of_turn',
      starting_state: { terrain: null, p2: { species: 'Charizard', hp_ratio: ratio(grassyAirborne, 1) } },
      chosen_actions: [{ p1: 'Grassy Terrain', p2: 'Splash' }],
      oracle: {
        terrain: grassyAirborne.field.terrain,
        p2_hp_ratio: ratio(grassyAirborne, 1),
        snapshots: [{ combatants: { p2: { hp: active(grassyAirborne, 1).hp } } }],
      },
      local_input: {
        turns: 1,
        state: {
          terrain: 'grassyterrain',
          combatants: { p2: grassyAirborneStart },
        },
      },
      local_support: 'supported',
    },
  ];
}

function delayedTarget(instance: Battle, side: 0 | 1): Record<string, unknown> {
  const pokemon = active(instance, side);
  return { pokemon_id: pokemon.species.id, hp: pokemon.hp, max_hp: pokemon.maxhp };
}

function delayedAttackInput(
  move: 'futuresight' | 'doomdesire',
  sourcePokemonId: string,
  damageByTarget: Record<string, number>,
): Record<string, unknown> {
  return {
    move,
    scheduled_turn: 1,
    source_side: 'p1',
    source_pokemon_id: sourcePokemonId,
    target_side: 'p2',
    target_slot: 0,
    damage_by_target: damageByTarget,
    damage_provenance: 'bundled_showdown_fixed_fixture',
  };
}

// A complete landing-time resolver bundle for the actual replacement occupant.
// The exact landing_damage is the Showdown-derived value for THIS occupant and
// stays fixture-only; it is never reused for a different occupant.
function delayedResolverInput(
  move: 'futuresight' | 'doomdesire',
  sourcePokemonId: string,
  occupant: Record<string, unknown>,
  occupantTypes: string[],
  landingDamage: number,
  moveMeta: { type: string; category: string; basePower: number },
): Record<string, unknown> {
  return {
    move,
    scheduled_turn: 1,
    source_side: 'p1',
    source_pokemon_id: sourcePokemonId,
    target_side: 'p2',
    target_slot: 0,
    resolver_inputs: {
      source_snapshot: { id: sourcePokemonId, side: 'p1' },
      move_id: move,
      move_type: moveMeta.type,
      move_category: moveMeta.category,
      move_base_power: moveMeta.basePower,
      target_snapshot: {
        pokemon_id: occupant.pokemon_id,
        hp: occupant.hp,
        max_hp: occupant.max_hp,
        types: occupantTypes,
      },
      field_snapshot: { weather: null, terrain: null, screens: [] },
      landing_damage: landingDamage,
      damage_provenance: 'bundled_showdown_resolver_bundle',
    },
  };
}

function delayedDamageCases(): ParityCase[] {
  const future = battle(
    [{ species: 'Slowking', moves: ['Future Sight', 'Splash'] }],
    [{ species: 'Machamp', ability: 'No Guard', moves: ['Splash'] }],
  );
  const futureStart = delayedTarget(future, 1);
  choose(future, 'move 1', 'move 1');
  const futureTurn1 = delayedTarget(future, 1);
  choose(future, 'move 2', 'move 1');
  const futureTurn2 = delayedTarget(future, 1);
  choose(future, 'move 2', 'move 1');
  const futureTurn3 = delayedTarget(future, 1);
  const futureDamage = Number(futureTurn2.hp) - Number(futureTurn3.hp);

  const switched = battle(
    [{ species: 'Slowking', moves: ['Future Sight', 'Splash'] }],
    [
      { species: 'Machamp', ability: 'No Guard', moves: ['Splash'] },
      { species: 'Blissey', ability: 'Natural Cure', moves: ['Splash'] },
    ],
  );
  const switchStart = delayedTarget(switched, 1);
  choose(switched, 'move 1', 'move 1');
  const switchTurn1 = delayedTarget(switched, 1);
  choose(switched, 'move 2', 'switch 2');
  const switchTurn2 = delayedTarget(switched, 1);
  choose(switched, 'move 2', 'move 1');
  const switchTurn3 = delayedTarget(switched, 1);
  const replacementDamage = Number(switchTurn2.hp) - Number(switchTurn3.hp);

  const duplicate = battle(
    [{ species: 'Slowking', moves: ['Future Sight', 'Splash'] }],
    [{ species: 'Machamp', ability: 'No Guard', moves: ['Splash'] }],
  );
  const duplicateStart = delayedTarget(duplicate, 1);
  choose(duplicate, 'move 1', 'move 1');
  const duplicateTurn1 = delayedTarget(duplicate, 1);
  const duplicateLines = choose(duplicate, 'move 1', 'move 1');
  const duplicateTurn2 = delayedTarget(duplicate, 1);
  choose(duplicate, 'move 2', 'move 1');
  const duplicateTurn3 = delayedTarget(duplicate, 1);
  const duplicateDamage = Number(duplicateTurn2.hp) - Number(duplicateTurn3.hp);

  const doom = battle(
    [{ species: 'Jirachi', moves: ['Doom Desire', 'Splash'] }],
    [{ species: 'Machamp', ability: 'No Guard', moves: ['Splash'] }],
  );
  const doomStart = delayedTarget(doom, 1);
  choose(doom, 'move 1', 'move 1');
  const doomTurn1 = delayedTarget(doom, 1);
  choose(doom, 'move 2', 'move 1');
  const doomTurn2 = delayedTarget(doom, 1);
  choose(doom, 'move 2', 'move 1');
  const doomTurn3 = delayedTarget(doom, 1);
  const doomDamage = Number(doomTurn2.hp) - Number(doomTurn3.hp);

  const doomSwitched = battle(
    [{ species: 'Jirachi', moves: ['Doom Desire', 'Splash'] }],
    [
      { species: 'Machamp', ability: 'No Guard', moves: ['Splash'] },
      { species: 'Blissey', ability: 'Natural Cure', moves: ['Splash'] },
    ],
  );
  const doomSwitchStart = delayedTarget(doomSwitched, 1);
  choose(doomSwitched, 'move 1', 'move 1');
  const doomSwitchTurn1 = delayedTarget(doomSwitched, 1);
  choose(doomSwitched, 'move 2', 'switch 2');
  const doomSwitchTurn2 = delayedTarget(doomSwitched, 1);
  choose(doomSwitched, 'move 2', 'move 1');
  const doomSwitchTurn3 = delayedTarget(doomSwitched, 1);
  const doomReplacementDamage = Number(doomSwitchTurn2.hp) - Number(doomSwitchTurn3.hp);

  return [
    {
      id: 'future_sight_lands_later',
      phase: 'delayed_future',
      starting_state: { target_slot: 'p2:0', target: futureStart },
      chosen_actions: [
        { p1: 'Future Sight', p2: 'Splash' },
        { p1: 'Splash', p2: 'Splash' },
        { p1: 'Splash', p2: 'Splash' },
      ],
      oracle: {
        snapshots: [
          { active_slots: { 'p2:0': futureTurn1 } },
          { active_slots: { 'p2:0': futureTurn2 } },
          { active_slots: { 'p2:0': futureTurn3 } },
        ],
        schedule_results: [true],
      },
      local_input: {
        state: { active_slots: { 'p2:0': futureStart }, delayed_attacks: {} },
        timeline: [
          { turn: 1, schedule: delayedAttackInput('futuresight', 'slowking', { machamp: futureDamage }) },
          { turn: 2 },
          { turn: 3 },
        ],
      },
      local_support: 'supported',
    },
    {
      id: 'future_sight_hits_replacement_in_target_slot',
      phase: 'delayed_future',
      starting_state: { target_slot: 'p2:0', original_target: switchStart },
      chosen_actions: [
        { p1: 'Future Sight', p2: 'Splash' },
        { p1: 'Splash', p2: 'switch Blissey' },
        { p1: 'Splash', p2: 'Splash' },
      ],
      oracle: {
        snapshots: [
          { active_slots: { 'p2:0': switchTurn1 } },
          { active_slots: { 'p2:0': switchTurn2 } },
          { active_slots: { 'p2:0': switchTurn3 } },
        ],
        schedule_results: [true],
      },
      local_input: {
        state: { active_slots: { 'p2:0': switchStart }, delayed_attacks: {} },
        timeline: [
          {
            turn: 1,
            schedule: delayedAttackInput('futuresight', 'slowking', { blissey: replacementDamage }),
          },
          { turn: 2, active_slots: { 'p2:0': switchTurn2 } },
          { turn: 3 },
        ],
      },
      local_support: 'supported',
    },
    {
      id: 'future_sight_replacement_damage_unavailable',
      phase: 'delayed_future',
      starting_state: { target_slot: 'p2:0', original_target: switchStart },
      chosen_actions: [
        { p1: 'Future Sight', p2: 'Splash' },
        { p1: 'Splash', p2: 'switch Blissey' },
        { p1: 'Splash', p2: 'Splash' },
      ],
      oracle: {
        snapshots: [
          { active_slots: { 'p2:0': switchTurn1 } },
          { active_slots: { 'p2:0': switchTurn2 } },
          { active_slots: { 'p2:0': switchTurn3 } },
        ],
        schedule_results: [true],
      },
      local_input: {
        state: { active_slots: { 'p2:0': switchStart }, delayed_attacks: {} },
        timeline: [
          {
            turn: 1,
            schedule: delayedAttackInput('futuresight', 'slowking', { machamp: futureDamage }),
          },
          { turn: 2, active_slots: { 'p2:0': switchTurn2 } },
          { turn: 3 },
        ],
      },
      local_support: 'supported',
      gap_reason: 'replacement target landing damage is absent from current local provenance',
    },
    {
      id: 'future_sight_resolver_bundle_replacement',
      phase: 'delayed_future',
      starting_state: { target_slot: 'p2:0', original_target: switchStart },
      chosen_actions: [
        { p1: 'Future Sight', p2: 'Splash' },
        { p1: 'Splash', p2: 'switch Blissey' },
        { p1: 'Splash', p2: 'Splash' },
      ],
      oracle: {
        snapshots: [
          { active_slots: { 'p2:0': switchTurn1 } },
          { active_slots: { 'p2:0': switchTurn2 } },
          { active_slots: { 'p2:0': switchTurn3 } },
        ],
        schedule_results: [true],
      },
      local_input: {
        state: { active_slots: { 'p2:0': switchStart }, delayed_attacks: {} },
        timeline: [
          {
            turn: 1,
            schedule: delayedResolverInput('futuresight', 'slowking', switchTurn2, ['normal'], replacementDamage, {
              type: 'psychic',
              category: 'special',
              basePower: 120,
            }),
          },
          { turn: 2, active_slots: { 'p2:0': switchTurn2 } },
          { turn: 3 },
        ],
      },
      local_support: 'supported',
    },
    {
      id: 'future_sight_duplicate_schedule_fails',
      phase: 'delayed_future',
      starting_state: { target_slot: 'p2:0', target: duplicateStart },
      chosen_actions: [
        { p1: 'Future Sight', p2: 'Splash' },
        { p1: 'Future Sight', p2: 'Splash' },
        { p1: 'Splash', p2: 'Splash' },
      ],
      oracle: {
        snapshots: [
          { active_slots: { 'p2:0': duplicateTurn1 } },
          { active_slots: { 'p2:0': duplicateTurn2 } },
          { active_slots: { 'p2:0': duplicateTurn3 } },
        ],
        schedule_results: [true, false],
        duplicate_failed: duplicateLines.some(line => line.startsWith('|-fail|p1a: Slowking')),
      },
      local_input: {
        state: { active_slots: { 'p2:0': duplicateStart }, delayed_attacks: {} },
        timeline: [
          { turn: 1, schedule: delayedAttackInput('futuresight', 'slowking', { machamp: duplicateDamage }) },
          { turn: 2, schedule: delayedAttackInput('futuresight', 'slowking', { machamp: duplicateDamage }) },
          { turn: 3 },
        ],
      },
      local_support: 'supported',
    },
    {
      id: 'doom_desire_lands_later',
      phase: 'delayed_future',
      starting_state: { target_slot: 'p2:0', target: doomStart },
      chosen_actions: [
        { p1: 'Doom Desire', p2: 'Splash' },
        { p1: 'Splash', p2: 'Splash' },
        { p1: 'Splash', p2: 'Splash' },
      ],
      oracle: {
        snapshots: [
          { active_slots: { 'p2:0': doomTurn1 } },
          { active_slots: { 'p2:0': doomTurn2 } },
          { active_slots: { 'p2:0': doomTurn3 } },
        ],
        schedule_results: [true],
      },
      local_input: {
        state: { active_slots: { 'p2:0': doomStart }, delayed_attacks: {} },
        timeline: [
          { turn: 1, schedule: delayedAttackInput('doomdesire', 'jirachi', { machamp: doomDamage }) },
          { turn: 2 },
          { turn: 3 },
        ],
      },
      local_support: 'supported',
    },
    {
      id: 'doom_desire_hits_replacement_in_target_slot',
      phase: 'delayed_future',
      starting_state: { target_slot: 'p2:0', original_target: doomSwitchStart },
      chosen_actions: [
        { p1: 'Doom Desire', p2: 'Splash' },
        { p1: 'Splash', p2: 'switch Blissey' },
        { p1: 'Splash', p2: 'Splash' },
      ],
      oracle: {
        snapshots: [
          { active_slots: { 'p2:0': doomSwitchTurn1 } },
          { active_slots: { 'p2:0': doomSwitchTurn2 } },
          { active_slots: { 'p2:0': doomSwitchTurn3 } },
        ],
        schedule_results: [true],
      },
      local_input: {
        state: { active_slots: { 'p2:0': doomSwitchStart }, delayed_attacks: {} },
        timeline: [
          {
            turn: 1,
            schedule: delayedAttackInput('doomdesire', 'jirachi', { blissey: doomReplacementDamage }),
          },
          { turn: 2, active_slots: { 'p2:0': doomSwitchTurn2 } },
          { turn: 3 },
        ],
      },
      local_support: 'supported',
    },
    {
      id: 'doom_desire_replacement_damage_unavailable',
      phase: 'delayed_future',
      starting_state: { target_slot: 'p2:0', original_target: doomSwitchStart },
      chosen_actions: [
        { p1: 'Doom Desire', p2: 'Splash' },
        { p1: 'Splash', p2: 'switch Blissey' },
        { p1: 'Splash', p2: 'Splash' },
      ],
      oracle: {
        snapshots: [
          { active_slots: { 'p2:0': doomSwitchTurn1 } },
          { active_slots: { 'p2:0': doomSwitchTurn2 } },
          { active_slots: { 'p2:0': doomSwitchTurn3 } },
        ],
        schedule_results: [true],
      },
      local_input: {
        state: { active_slots: { 'p2:0': doomSwitchStart }, delayed_attacks: {} },
        timeline: [
          {
            turn: 1,
            schedule: delayedAttackInput('doomdesire', 'jirachi', { machamp: doomDamage }),
          },
          { turn: 2, active_slots: { 'p2:0': doomSwitchTurn2 } },
          { turn: 3 },
        ],
      },
      local_support: 'supported',
      gap_reason: 'replacement target landing damage is absent from current local provenance',
    },
    {
      id: 'doom_desire_resolver_bundle_replacement',
      phase: 'delayed_future',
      starting_state: { target_slot: 'p2:0', original_target: doomSwitchStart },
      chosen_actions: [
        { p1: 'Doom Desire', p2: 'Splash' },
        { p1: 'Splash', p2: 'switch Blissey' },
        { p1: 'Splash', p2: 'Splash' },
      ],
      oracle: {
        snapshots: [
          { active_slots: { 'p2:0': doomSwitchTurn1 } },
          { active_slots: { 'p2:0': doomSwitchTurn2 } },
          { active_slots: { 'p2:0': doomSwitchTurn3 } },
        ],
        schedule_results: [true],
      },
      local_input: {
        state: { active_slots: { 'p2:0': doomSwitchStart }, delayed_attacks: {} },
        timeline: [
          {
            turn: 1,
            schedule: delayedResolverInput('doomdesire', 'jirachi', doomSwitchTurn2, ['normal'], doomReplacementDamage, {
              type: 'steel',
              category: 'special',
              basePower: 140,
            }),
          },
          { turn: 2, active_slots: { 'p2:0': doomSwitchTurn2 } },
          { turn: 3 },
        ],
      },
      local_support: 'supported',
    },
  ];
}

function hazardCase(
  id: string,
  target: SetSpec,
  setupMoves: string[],
  expected: Record<string, unknown>,
  localInput: Record<string, unknown>,
): ParityCase {
  const setterMoves = [...setupMoves, 'Splash'];
  const instance = battle(
    [{ species: 'Mew', moves: setterMoves }],
    [
      { species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] },
      target,
    ],
  );
  setupMoves.forEach((_, index) => choose(instance, `move ${index + 1}`, 'move 1'));
  const entryLines = choose(instance, `move ${setterMoves.length}`, 'switch 2');
  const entered = active(instance, 1);
  const entryDamage = Math.max(
    sourceDamageFraction(entryLines, 'Stealth Rock'),
    sourceDamageFraction(entryLines, 'Spikes'),
  );
  return {
    id,
    phase: 'switch_entry',
    starting_state: { target, hazards: setupMoves },
    chosen_actions: [
      ...setupMoves.map(move => ({ p1: move, p2: 'Splash' })),
      { p1: 'Splash', p2: `switch ${target.species}` },
    ],
    oracle: {
      hp_fraction_lost: entryDamage,
      status: entered.status || null,
      speed_stage: entered.boosts.spe || 0,
      ...expected,
    },
    local_input: localInput,
    local_support: 'supported',
  };
}

function hazardCases(): ParityCase[] {
  return [
    hazardCase(
      'stealth_rock_type_effectiveness',
      { species: 'Charizard', moves: ['Splash'] },
      ['Stealth Rock'],
      {},
      { target: { types: ['Fire', 'Flying'], hp_fraction: 1 }, hazards: { stealthrock: 1 } },
    ),
    hazardCase(
      'spikes_grounded_one_layer',
      { species: 'Raichu', moves: ['Splash'] },
      ['Spikes'],
      {},
      { target: { types: ['Electric'], hp_fraction: 1 }, hazards: { spikes: 1 } },
    ),
    hazardCase(
      'spikes_airborne_immunity',
      { species: 'Charizard', moves: ['Splash'] },
      ['Spikes'],
      {},
      { target: { types: ['Fire', 'Flying'], hp_fraction: 1 }, hazards: { spikes: 1 } },
    ),
    hazardCase(
      'toxic_spikes_grounded_poison',
      { species: 'Raichu', moves: ['Splash'] },
      ['Toxic Spikes'],
      {},
      { target: { types: ['Electric'], hp_fraction: 1 }, hazards: { toxicspikes: 1 } },
    ),
    hazardCase(
      'sticky_web_grounded_speed_drop',
      { species: 'Raichu', moves: ['Splash'] },
      ['Sticky Web'],
      {},
      { target: { types: ['Electric'], hp_fraction: 1 }, hazards: { stickyweb: 1 } },
    ),
    hazardCase(
      'heavy_duty_boots_prevents_hazards',
      { species: 'Charizard', item: 'Heavy-Duty Boots', moves: ['Splash'] },
      ['Stealth Rock', 'Spikes', 'Toxic Spikes', 'Sticky Web'],
      {},
      {
        target: { types: ['Fire', 'Flying'], item: 'Heavy-Duty Boots', hp_fraction: 1 },
        hazards: { stealthrock: 1, spikes: 1, toxicspikes: 1, stickyweb: 1 },
      },
    ),
  ];
}

function preventionCases(): ParityCase[] {
  const psychic = battle(
    [{ species: 'Raichu', moves: ['Psychic Terrain', 'Splash'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Quick Attack', 'Splash'] }],
  );
  choose(psychic, 'move 1', 'move 2');
  const psychicBefore = ratio(psychic, 0);
  const psychicLines = choose(psychic, 'move 2', 'move 1');

  const psychicTackle = battle(
    [{ species: 'Raichu', moves: ['Psychic Terrain', 'Splash'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Tackle', 'Splash'] }],
  );
  choose(psychicTackle, 'move 1', 'move 2');
  const tackleBefore = ratio(psychicTackle, 0);
  choose(psychicTackle, 'move 2', 'move 1');

  const psychicAirborne = battle(
    [{ species: 'Charizard', ability: 'Blaze', moves: ['Psychic Terrain', 'Splash'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Quick Attack', 'Splash'] }],
  );
  choose(psychicAirborne, 'move 1', 'move 2');
  const airborneBefore = ratio(psychicAirborne, 0);
  choose(psychicAirborne, 'move 2', 'move 1');

  const grassyGlide = battle(
    [{ species: 'Mew', moves: ['Psychic Terrain', 'Splash'] }],
    [{ species: 'Rillaboom', ability: 'Overgrow', moves: ['Grassy Glide', 'Splash'] }],
  );
  choose(grassyGlide, 'move 1', 'move 2');
  const grassyGlideBefore = ratio(grassyGlide, 0);
  choose(grassyGlide, 'move 2', 'move 1');

  const substitute = battle(
    [{ species: 'Mew', moves: ['Substitute'] }],
    [{ species: 'Celebi', moves: ['Leech Seed'] }],
  );
  choose(substitute, 'move 1', 'move 1');

  const misty = battle(
    [{ species: 'Mew', moves: ['Misty Terrain'] }],
    [{ species: 'Amoonguss', ability: 'Effect Spore', moves: ['Spore'] }],
  );
  choose(misty, 'move 1', 'move 1');

  const electric = battle(
    [{ species: 'Mew', moves: ['Electric Terrain'] }],
    [{ species: 'Amoonguss', ability: 'Effect Spore', moves: ['Spore'] }],
  );
  choose(electric, 'move 1', 'move 1');

  const damp = battle(
    [{ species: 'Electrode', moves: ['Explosion'] }],
    [{ species: 'Quagsire', ability: 'Damp', moves: ['Splash'] }],
  );
  const dampTargetBefore = ratio(damp, 1);
  const dampLines = choose(damp, 'move 1', 'move 1');

  const powder = battle(
    [{ species: 'Vivillon', ability: 'Compound Eyes', moves: ['Powder'] }],
    [{ species: 'Charizard', ability: 'Blaze', moves: ['Flamethrower'] }],
  );
  const powderAttackerBefore = active(powder, 1).hp;
  const powderLines = choose(powder, 'move 1', 'move 1');

  const suckerSuccess = battle(
    [{ species: 'Honchkrow', ability: 'Insomnia', moves: ['Sucker Punch'] }],
    [{ species: 'Mew', moves: ['Tackle', 'Splash'] }],
  );
  const suckerSuccessBefore = active(suckerSuccess, 1).hp;
  choose(suckerSuccess, 'move 1', 'move 1');

  const suckerFail = battle(
    [{ species: 'Honchkrow', ability: 'Insomnia', moves: ['Sucker Punch'] }],
    [{ species: 'Mew', moves: ['Splash'] }],
  );
  const suckerFailBefore = active(suckerFail, 1).hp;
  const suckerFailLines = choose(suckerFail, 'move 1', 'move 1');

  const thunderclapSuccess = battle(
    [{ species: 'Raging Bolt', ability: 'Protosynthesis', moves: ['Thunderclap'] }],
    [{ species: 'Mew', moves: ['Tackle', 'Splash'] }],
  );
  const thunderclapSuccessBefore = active(thunderclapSuccess, 1).hp;
  choose(thunderclapSuccess, 'move 1', 'move 1');

  const thunderclapFail = battle(
    [{ species: 'Raging Bolt', ability: 'Protosynthesis', moves: ['Thunderclap'] }],
    [{ species: 'Mew', moves: ['Splash'] }],
  );
  const thunderclapFailBefore = active(thunderclapFail, 1).hp;
  const thunderclapFailLines = choose(thunderclapFail, 'move 1', 'move 1');

  const magicBounce = battle(
    [{ species: 'Hatterene', ability: 'Magic Bounce', moves: ['Splash'] }],
    [{ species: 'Mew', moves: ['Stealth Rock'] }],
  );
  const magicBounceLines = choose(magicBounce, 'move 1', 'move 1');

  const goodAsGold = battle(
    [{ species: 'Gholdengo', ability: 'Good as Gold', moves: ['Splash'] }],
    [{ species: 'Amoonguss', moves: ['Spore'] }],
  );
  const goodAsGoldLines = choose(goodAsGold, 'move 1', 'move 1');

  return [
    {
      id: 'psychic_terrain_blocks_grounded_priority',
      phase: 'immediate',
      starting_state: { terrain: 'Psychic Terrain', p2_move: 'Quick Attack' },
      chosen_actions: [{ p1: 'Splash', p2: 'Quick Attack' }],
      oracle: {
        prevented: ratio(psychic, 0) === psychicBefore,
        p1_hp_unchanged: ratio(psychic, 0) === psychicBefore,
        fail_logged: psychicLines.some(line => line.startsWith('|-fail|')),
      },
      local_input: {
        state: {
          terrain: 'psychicterrain',
          attacker: { types: ['Normal'], ability: 'Thick Fat' },
          target: { types: ['Electric'], ability: 'Static' },
        },
        action: { name: 'Quick Attack', priority: 1 },
      },
      local_support: 'supported',
    },
    {
      id: 'psychic_terrain_does_not_block_non_priority',
      phase: 'immediate',
      starting_state: { terrain: 'Psychic Terrain', p2_move: 'Tackle' },
      chosen_actions: [{ p1: 'Splash', p2: 'Tackle' }],
      oracle: { prevented: ratio(psychicTackle, 0) === tackleBefore },
      local_input: {
        state: {
          terrain: 'psychicterrain',
          attacker: { types: ['Normal'], ability: 'Thick Fat' },
          target: { types: ['Electric'], ability: 'Static' },
        },
        action: { name: 'Tackle', priority: 0 },
      },
      local_support: 'supported',
    },
    {
      id: 'psychic_terrain_does_not_block_airborne_target',
      phase: 'immediate',
      starting_state: { terrain: 'Psychic Terrain', p2_move: 'Quick Attack', target: 'Flying' },
      chosen_actions: [{ p1: 'Splash', p2: 'Quick Attack' }],
      oracle: { prevented: ratio(psychicAirborne, 0) === airborneBefore },
      local_input: {
        state: {
          terrain: 'psychicterrain',
          attacker: { types: ['Normal'], ability: 'Thick Fat' },
          target: { types: ['Fire', 'Flying'], ability: 'Blaze' },
        },
        action: { name: 'Quick Attack', priority: 1 },
      },
      local_support: 'supported',
    },
    {
      id: 'psychic_terrain_does_not_block_grassy_glide_without_grassy_terrain',
      phase: 'immediate',
      starting_state: { terrain: 'Psychic Terrain', p2_move: 'Grassy Glide' },
      chosen_actions: [{ p1: 'Splash', p2: 'Grassy Glide' }],
      oracle: { prevented: ratio(grassyGlide, 0) === grassyGlideBefore },
      local_input: {
        state: {
          terrain: 'psychicterrain',
          attacker: { types: ['Grass'], ability: 'Overgrow' },
          target: { types: ['Psychic'], ability: 'Synchronize' },
        },
        action: { name: 'Grassy Glide', priority: 0 },
      },
      local_support: 'supported',
    },
    {
      id: 'substitute_blocks_leech_seed',
      phase: 'immediate',
      starting_state: { p1: { volatile: 'Substitute' }, p2_move: 'Leech Seed' },
      chosen_actions: [{ p1: 'Substitute', p2: 'Leech Seed' }],
      oracle: {
        prevented: !active(substitute, 0).volatiles['leechseed'],
        substitute_active: !!active(substitute, 0).volatiles['substitute'],
        leech_seed_active: !!active(substitute, 0).volatiles['leechseed'],
      },
      local_input: {
        state: {
          attacker: { types: ['Psychic', 'Grass'], ability: 'Natural Cure' },
          target: { types: ['Psychic'], ability: 'Synchronize', substitute: true },
        },
        action: { name: 'Leech Seed', priority: 0, blocked_by_substitute: true },
      },
      local_support: 'supported',
    },
    {
      id: 'misty_terrain_blocks_status',
      phase: 'immediate',
      starting_state: { terrain: null, p1: { status: null }, p2_move: 'Spore' },
      chosen_actions: [{ p1: 'Misty Terrain', p2: 'Spore' }],
      oracle: { prevented: !active(misty, 0).status, terrain: misty.field.terrain, p1_status: active(misty, 0).status || null },
      local_input: {
        state: {
          terrain: 'mistyterrain',
          attacker: { types: ['Grass', 'Poison'], ability: 'Effect Spore' },
          target: { types: ['Psychic'], ability: 'Synchronize' },
        },
        action: { name: 'Spore', priority: 0, status: 'slp' },
      },
      local_support: 'supported',
    },
    {
      id: 'electric_terrain_blocks_sleep',
      phase: 'immediate',
      starting_state: { terrain: null, p1: { status: null }, p2_move: 'Spore' },
      chosen_actions: [{ p1: 'Electric Terrain', p2: 'Spore' }],
      oracle: { prevented: !active(electric, 0).status, terrain: electric.field.terrain, p1_status: active(electric, 0).status || null },
      local_input: {
        state: {
          terrain: 'electricterrain',
          attacker: { types: ['Grass', 'Poison'], ability: 'Effect Spore' },
          target: { types: ['Psychic'], ability: 'Synchronize' },
        },
        action: { name: 'Spore', priority: 0, status: 'slp' },
      },
      local_support: 'supported',
    },
    {
      id: 'damp_blocks_explosion',
      phase: 'immediate',
      starting_state: { p1_move: 'Explosion', p2_ability: 'Damp' },
      chosen_actions: [{ p1: 'Explosion', p2: 'Splash' }],
      oracle: {
        prevented: ratio(damp, 1) === dampTargetBefore,
        fail_logged: dampLines.some(line => line.includes('[from] ability: Damp')),
      },
      local_input: {
        state: {
          attacker: { types: ['Electric'], ability: 'Soundproof' },
          target: { types: ['Water', 'Ground'], ability: 'Damp' },
        },
        action: { name: 'Explosion', priority: 0, explosion_like: true },
      },
      local_support: 'supported',
    },
    {
      id: 'powder_blocks_fire_move',
      phase: 'immediate',
      starting_state: { p1_move: 'Powder', p2_move: 'Flamethrower', p2_volatile: 'powder' },
      chosen_actions: [{ p1: 'Powder', p2: 'Flamethrower' }],
      oracle: {
        prevented: active(powder, 0).hp === active(powder, 0).maxhp,
        user_took_powder_damage: active(powder, 1).hp < powderAttackerBefore,
        fail_logged: powderLines.some(line => line.includes('[from] move: Powder')),
      },
      local_input: {
        state: {
          attacker: { types: ['Fire', 'Flying'], ability: 'Blaze', volatiles: ['powder'] },
          target: { types: ['Bug', 'Flying'], ability: 'Compound Eyes' },
        },
        action: { name: 'Flamethrower', type: 'Fire', priority: 0 },
      },
      local_support: 'supported',
    },
    {
      id: 'sucker_punch_succeeds_when_target_attacks',
      phase: 'immediate',
      starting_state: { p1_move: 'Sucker Punch', p2_move: 'Tackle' },
      chosen_actions: [{ p1: 'Sucker Punch', p2: 'Tackle' }],
      oracle: {
        prevented: active(suckerSuccess, 1).hp === suckerSuccessBefore,
      },
      local_input: {
        state: {
          attacker: { types: ['Dark', 'Flying'], ability: 'Insomnia' },
          target: { types: ['Psychic'], ability: 'Synchronize' },
          opponent_action_category: 'Physical',
        },
        action: { name: 'Sucker Punch', priority: 1, requires_target_attack: true },
      },
      local_support: 'supported',
    },
    {
      id: 'sucker_punch_fails_when_target_uses_status',
      phase: 'immediate',
      starting_state: { p1_move: 'Sucker Punch', p2_move: 'Splash' },
      chosen_actions: [{ p1: 'Sucker Punch', p2: 'Splash' }],
      oracle: {
        prevented: active(suckerFail, 1).hp === suckerFailBefore,
        fail_logged: suckerFailLines.some(line => line.startsWith('|-fail|p1a: Honchkrow')),
      },
      local_input: {
        state: {
          attacker: { types: ['Dark', 'Flying'], ability: 'Insomnia' },
          target: { types: ['Psychic'], ability: 'Synchronize' },
          opponent_action_category: 'Status',
        },
        action: { name: 'Sucker Punch', priority: 1, requires_target_attack: true },
      },
      local_support: 'supported',
    },
    {
      id: 'thunderclap_succeeds_when_target_attacks',
      phase: 'immediate',
      starting_state: { p1_move: 'Thunderclap', p2_move: 'Tackle' },
      chosen_actions: [{ p1: 'Thunderclap', p2: 'Tackle' }],
      oracle: {
        prevented: active(thunderclapSuccess, 1).hp === thunderclapSuccessBefore,
      },
      local_input: {
        state: {
          attacker: { types: ['Electric', 'Dragon'], ability: 'Protosynthesis' },
          target: { types: ['Psychic'], ability: 'Synchronize' },
          opponent_action_category: 'Physical',
        },
        action: { name: 'Thunderclap', priority: 1, requires_target_attack: true },
      },
      local_support: 'supported',
    },
    {
      id: 'thunderclap_fails_when_target_uses_status',
      phase: 'immediate',
      starting_state: { p1_move: 'Thunderclap', p2_move: 'Splash' },
      chosen_actions: [{ p1: 'Thunderclap', p2: 'Splash' }],
      oracle: {
        prevented: active(thunderclapFail, 1).hp === thunderclapFailBefore,
        fail_logged: thunderclapFailLines.some(line => line.startsWith('|-fail|p1a: Raging Bolt')),
      },
      local_input: {
        state: {
          attacker: { types: ['Electric', 'Dragon'], ability: 'Protosynthesis' },
          target: { types: ['Psychic'], ability: 'Synchronize' },
          opponent_action_category: 'Status',
        },
        action: { name: 'Thunderclap', priority: 1, requires_target_attack: true },
      },
      local_support: 'supported',
    },
    {
      id: 'magic_bounce_reflects_stealth_rock',
      phase: 'immediate',
      starting_state: { p1_ability: 'Magic Bounce', p2_move: 'Stealth Rock' },
      chosen_actions: [{ p1: 'Splash', p2: 'Stealth Rock' }],
      oracle: {
        reflected: magicBounceLines.some(line => line.includes('[from] ability: Magic Bounce')),
      },
      local_input: {
        state: {
          attacker: { types: ['Psychic'], ability: 'Synchronize' },
          target: { types: ['Psychic', 'Fairy'], ability: 'Magic Bounce', ability_known: true },
          reflection: {
            original_source: 'p2:0',
            reflector: 'p1:0',
            destination_side: 'p2',
            reflected_target: 'p2:0',
            effect_payload: { side_condition: 'stealthrock' },
          },
        },
        action: { name: 'Stealth Rock', reflectable: true, category: 'Status' },
      },
      local_support: 'supported',
    },
    {
      id: 'magic_bounce_reflection_gap',
      phase: 'immediate',
      starting_state: { p1_ability: 'Magic Bounce', p2_move: 'Stealth Rock' },
      chosen_actions: [{ p1: 'Splash', p2: 'Stealth Rock' }],
      oracle: {
        reflected: magicBounceLines.some(line => line.includes('[from] ability: Magic Bounce')),
      },
      local_support: 'intentional_gap',
      gap_reason: 'Magic Bounce reflection needs reflected action target/side-condition provenance, not just a hard-fail bit',
    },
    {
      id: 'good_as_gold_known_blocks_status',
      phase: 'immediate',
      starting_state: { p1_ability: 'Good as Gold', p2_move: 'Spore' },
      chosen_actions: [{ p1: 'Splash', p2: 'Spore' }],
      oracle: {
        prevented: !active(goodAsGold, 0).status,
        blocked: goodAsGoldLines.some(line => line.includes('[from] ability: Good as Gold')),
      },
      local_input: {
        state: {
          attacker: { types: ['Grass', 'Poison'], ability: 'Effect Spore' },
          target: { types: ['Steel', 'Ghost'], ability: 'Good as Gold', ability_known: true },
        },
        action: { name: 'Spore', category: 'Status', status: 'slp' },
      },
      local_support: 'supported',
    },
    {
      id: 'good_as_gold_status_gap',
      phase: 'immediate',
      starting_state: { p1_ability: 'Good as Gold', p2_move: 'Spore' },
      chosen_actions: [{ p1: 'Splash', p2: 'Spore' }],
      oracle: {
        blocked: goodAsGoldLines.some(line => line.includes('[from] ability: Good as Gold')),
        p1_status: active(goodAsGold, 0).status || null,
      },
      local_support: 'intentional_gap',
      gap_reason: 'Good as Gold requires ability provenance in arbitrary rollout states and broader status-move callback routing',
    },
  ];
}

function sequentialMultiHitCases(): ParityCase[] {
  const population = battle(
    [{ species: 'Maushold', ability: 'Technician', moves: ['Population Bomb'] }],
    [{ species: 'Blissey', ability: 'Natural Cure', moves: ['Splash'] }],
    [31, 41, 59, 26],
    true,
  );
  const populationStartingHp = active(population, 1).hp;
  const populationLines = choose(population, 'move 1', 'move 1');

  const populationMiss = battle(
    [{ species: 'Maushold', ability: 'Technician', moves: ['Population Bomb'] }],
    [{ species: 'Blissey', ability: 'Natural Cure', moves: ['Splash'] }],
    [1, 2, 3, 4],
    false,
  );
  const populationMissHp = active(populationMiss, 1).hp;
  const populationMissLines = choose(populationMiss, 'move 1', 'move 1');

  const tripleAxel = battle(
    [{ species: 'Weavile', ability: 'Pressure', moves: ['Triple Axel'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] }],
    [31, 41, 59, 26],
    true,
  );
  const tripleAxelStartingHp = active(tripleAxel, 1).hp;
  const tripleAxelLines = choose(tripleAxel, 'move 1', 'move 1');

  const tripleAxelMiss = battle(
    [{ species: 'Weavile', ability: 'Pressure', moves: ['Triple Axel'] }],
    [{ species: 'Snorlax', ability: 'Thick Fat', moves: ['Splash'] }],
    [1, 3, 5, 7],
    false,
  );
  const tripleAxelMissHp = active(tripleAxelMiss, 1).hp;
  const tripleAxelMissLines = choose(tripleAxelMiss, 'move 1', 'move 1');

  return [
    {
      id: 'population_bomb_sequential_hits_gap',
      phase: 'sequential_multihit',
      starting_state: { p1_move: 'Population Bomb', seed: [31, 41, 59, 26], p2_hp: populationStartingHp },
      chosen_actions: [{ p1: 'Population Bomb', p2: 'Splash' }],
      oracle: {
        hit_count: hitCount(populationLines),
        damage_sequence: damageSequence(populationLines, 'p2', populationStartingHp),
        final_hp: active(population, 1).hp,
        sequential_accuracy: true,
        stop_on_miss: true,
      },
      local_support: 'intentional_gap',
      gap_reason: 'exact sequential multi-hit rollout needs per-hit accuracy branch state, PRNG provenance, and per-hit damage trace',
    },
    {
      id: 'population_bomb_initial_miss_stops_gap',
      phase: 'sequential_multihit',
      starting_state: { p1_move: 'Population Bomb', seed: [1, 2, 3, 4], p2_hp: populationMissHp },
      chosen_actions: [{ p1: 'Population Bomb', p2: 'Splash' }],
      oracle: {
        missed: populationMissLines.some(line => line.startsWith('|-miss|')),
        hit_count: hitCount(populationMissLines),
        damage_sequence: damageSequence(populationMissLines, 'p2', populationMissHp),
        final_hp: active(populationMiss, 1).hp,
        sequential_accuracy: true,
        stop_on_miss: true,
      },
      local_support: 'intentional_gap',
      gap_reason: 'exact sequential multi-hit rollout needs per-hit accuracy branch state, PRNG provenance, and stop-on-miss execution',
    },
    {
      id: 'triple_axel_power_ramp_gap',
      phase: 'sequential_multihit',
      starting_state: { p1_move: 'Triple Axel', seed: [31, 41, 59, 26], p2_hp: tripleAxelStartingHp },
      chosen_actions: [{ p1: 'Triple Axel', p2: 'Splash' }],
      oracle: {
        hit_count: hitCount(tripleAxelLines),
        damage_sequence: damageSequence(tripleAxelLines, 'p2', tripleAxelStartingHp),
        final_hp: active(tripleAxel, 1).hp,
        sequential_accuracy: true,
        per_hit_power_ramp: [20, 40, 60],
      },
      local_support: 'intentional_gap',
      gap_reason: 'exact Triple Axel rollout needs per-hit accuracy branch state plus per-hit base-power and damage provenance',
    },
    {
      id: 'triple_axel_initial_miss_stops_gap',
      phase: 'sequential_multihit',
      starting_state: { p1_move: 'Triple Axel', seed: [1, 3, 5, 7], p2_hp: tripleAxelMissHp },
      chosen_actions: [{ p1: 'Triple Axel', p2: 'Splash' }],
      oracle: {
        missed: tripleAxelMissLines.some(line => line.startsWith('|-miss|')),
        hit_count: hitCount(tripleAxelMissLines),
        damage_sequence: damageSequence(tripleAxelMissLines, 'p2', tripleAxelMissHp),
        final_hp: active(tripleAxelMiss, 1).hp,
        sequential_accuracy: true,
        stop_on_miss: true,
      },
      local_support: 'intentional_gap',
      gap_reason: 'exact Triple Axel rollout needs per-hit accuracy branch state, PRNG provenance, and stop-on-miss execution',
    },
  ];
}

export function buildRolloutParityOracle(): { oracle: string; cases: ParityCase[] } {
  return {
    oracle: 'bundled pokemon-showdown Battle (gen9customgame, fixed PRNG seeds; deterministic normal PRNG for miss fixtures)',
    cases: [
      ...residualCases(),
      ...fieldCases(),
      ...delayedDamageCases(),
      ...hazardCases(),
      ...preventionCases(),
      ...sequentialMultiHitCases(),
    ],
  };
}

if (require.main === module) {
  process.stdout.write(`${JSON.stringify(buildRolloutParityOracle(), null, 2)}\n`);
}
