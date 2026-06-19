import assert from 'node:assert/strict';
import test from 'node:test';
import { buildLegalActionSet, normalizeRequest } from '../src/action_codec';

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
  assert.equal(legal.actions[4]?.kind, 'move_tera');
  assert.equal(legal.actions[4]?.choice, 'move 1 terastallize');
  assert.equal(legal.actions[4]?.label, 'move_tera:Fire Blast');
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

test('buildLegalActionSet does not offer tera moves after tera has been used', () => {
  const request = {
    active: [
      {
        canTerastallize: 'Fire',
        trapped: false,
        moves: [
          { move: 'Fire Blast', id: 'fireblast', pp: 8, maxpp: 8, target: 'normal', disabled: false },
        ],
      },
    ],
    side: {
      pokemon: [
        { active: true, terastallized: true, condition: '100/100' },
        { active: false, condition: '100/100' },
      ],
    },
  };

  const legal = buildLegalActionSet(request);
  assert.equal(legal.mask[0], true);
  assert.equal(legal.mask[4], false);
  assert.equal(legal.actions[4], null);
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

test('forced replacement requests expose only healthy bench switches', () => {
  const legal = buildLegalActionSet({
    forceSwitch: [true],
    side: {
      pokemon: [
        { active: true, condition: '0 fnt' },
        { active: false, condition: '100/100' },
        { active: false, condition: '0 fnt' },
        { active: false, condition: '50/100 par' },
      ],
    },
  });

  assert.deepEqual(legal.available_indices, [8, 9]);
  assert.equal(legal.actions[8]?.choice, 'switch 2');
  assert.equal(legal.actions[9]?.choice, 'switch 4');
  assert.ok(legal.mask.slice(0, 8).every((enabled) => !enabled));
});

test('request-disabled moves encode choice lock, Encore, Taunt, Disable, Assault Vest, and PP legality', () => {
  for (const reason of ['choice-lock', 'encore', 'taunt', 'disable', 'assault-vest']) {
    const legal = buildLegalActionSet({
      active: [{
        trapped: false,
        moves: [
          { move: 'Tackle', id: 'tackle', pp: 35, maxpp: 35, disabled: reason !== 'encore' },
          { move: 'Swords Dance', id: 'swordsdance', pp: reason === 'encore' ? 20 : 0, maxpp: 20, disabled: reason !== 'taunt' },
          { move: 'Protect', id: 'protect', pp: 10, maxpp: 10, disabled: true },
        ],
      }],
      side: { pokemon: [{ active: true, condition: '100/100' }] },
    });

    const enabledMoves = legal.available_indices.filter((index) => index < 4);
    assert.ok(enabledMoves.length <= 1, `${reason} should leave at most one move enabled`);
    assert.equal(legal.mask[2], false);
  }
});

test('trapped requests remove switches while preserving legal moves', () => {
  const request = normalizeRequest('p1', {
    rqid: 7,
    active: [{
      trapped: true,
      moves: [{ move: 'Tackle', id: 'tackle', pp: 35, maxpp: 35, disabled: false }],
    }],
    side: {
      pokemon: [
        { active: true, condition: '100/100' },
        { active: false, condition: '100/100' },
      ],
    },
  });

  assert.equal(request.trapped, true);
  assert.equal(request.active?.can_switch, false);
  assert.deepEqual(request.legal_actions.available_indices, [0]);
});
