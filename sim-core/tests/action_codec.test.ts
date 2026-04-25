import assert from 'node:assert/strict';
import test from 'node:test';
import { buildLegalActionSet } from '../src/action_codec';

test('buildLegalActionSet masks moves, tera moves, and switches', () => {
  const request = {
    active: [
      {
        canTerastallize: 'Fire',
        trapped: false,
        moves: [
          { move: 'Fire Blast', id: 'fireblast', pp: 8, maxpp: 8, target: 'normal', disabled: false },
          { move: 'Focus Blast', id: 'focusblast', pp: 8, maxpp: 8, target: 'normal', disabled: false },
          { move: 'Rest', id: 'rest', pp: 8, maxpp: 8, target: 'self', disabled: true },
          { move: 'Scorching Sands', id: 'scorchingsands', pp: 16, maxpp: 16, target: 'normal', disabled: false },
        ],
      },
    ],
    side: {
      pokemon: [
        { active: true, condition: '100/100' },
        { active: false, condition: '100/100' },
        { active: false, condition: '0 fnt' },
        { active: false, condition: '100/100' },
      ],
    },
  };

  const legal = buildLegalActionSet(request);
  assert.equal(legal.mask.length, 13);
  assert.equal(legal.mask[0], true);
  assert.equal(legal.mask[1], true);
  assert.equal(legal.mask[2], false);
  assert.equal(legal.mask[3], true);
  assert.equal(legal.mask[4], true);
  assert.equal(legal.mask[5], true);
  assert.equal(legal.mask[7], true);
  assert.equal(legal.mask[8], true);
  assert.equal(legal.mask[9], true);
  assert.equal(legal.mask[10], false);
});

test('buildLegalActionSet does not offer zero-PP moves', () => {
  const request = {
    active: [
      {
        canTerastallize: false,
        trapped: true,
        moves: [
          { move: 'Thunderbolt', id: 'thunderbolt', pp: 0, maxpp: 24, target: 'normal', disabled: false },
          { move: 'Recover', id: 'recover', pp: 1, maxpp: 8, target: 'self', disabled: false },
        ],
      },
    ],
    side: {
      pokemon: [
        { active: true, condition: '100/100' },
        { active: false, condition: '100/100' },
      ],
    },
  };

  const legal = buildLegalActionSet(request);
  assert.equal(legal.mask[0], false);
  assert.equal(legal.actions[0], null);
  assert.equal(legal.mask[1], true);
  assert.equal(legal.actions[1]?.choice, 'move 2');
});

test('buildLegalActionSet falls back to default when no concrete action is available', () => {
  const request = {
    active: [
      {
        canTerastallize: false,
        trapped: true,
        moves: [
          { move: 'Thunderbolt', id: 'thunderbolt', pp: 0, maxpp: 24, target: 'normal', disabled: false },
          { move: 'Recover', id: 'recover', pp: 0, maxpp: 8, target: 'self', disabled: false },
        ],
      },
    ],
    side: {
      pokemon: [
        { active: true, condition: '100/100' },
        { active: false, condition: '100/100' },
      ],
    },
  };

  const legal = buildLegalActionSet(request);
  assert.deepEqual(legal.available_indices, [0]);
  assert.equal(legal.mask[0], true);
  assert.equal(legal.actions[0]?.choice, 'default');
});
