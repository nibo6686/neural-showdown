import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import {
  canonicalActionFromLegalAction,
  deserializeCanonicalAction,
  serializeCanonicalAction,
} from '../src/canonical_action';
import { createEmptyLegalActionSet, type ChoiceRequestView, type LegalAction } from '../src/types';

type FixtureCase = {
  name: string;
  request: { player: 'p1' | 'p2'; rqid: number | null; force_switch: boolean };
  legal_action: LegalAction;
  legal_action_set: { mask: boolean[]; available_indices: number[]; actions: Array<LegalAction | null> };
  canonical_action: Record<string, unknown>;
};

const fixture = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../../tests/fixtures/canonical_action_v1.json'), 'utf8')) as { cases: FixtureCase[] };

function requestFor(testCase: FixtureCase): ChoiceRequestView {
  const legal_actions = {
    mask: [...testCase.legal_action_set.mask],
    actions: testCase.legal_action_set.actions.map((action) => action ? { ...action } : null),
    available_indices: [...testCase.legal_action_set.available_indices],
  };
  return {
    player: testCase.request.player,
    wait: false,
    team_preview: false,
    force_switch: testCase.request.force_switch,
    trapped: false,
    rqid: testCase.request.rqid,
    active: null,
    side: [],
    legal_actions,
    raw: null,
  };
}

test('canonical action fixtures round-trip deterministically', () => {
  for (const testCase of fixture.cases) {
    const request = requestFor(testCase);
    assert.deepEqual(request.legal_actions, testCase.legal_action_set, testCase.name);
    assert.deepEqual(request.legal_actions.available_indices, testCase.legal_action_set.available_indices, testCase.name);
    for (const [index, action] of testCase.legal_action_set.actions.entries()) {
      assert.equal(request.legal_actions.mask[index], action !== null, `${testCase.name}:${index}`);
      if (action) {
        assert.equal(action.index, index, `${testCase.name}:${index}`);
        assert.equal(request.legal_actions.actions[index]?.label, action.label, `${testCase.name}:${index}`);
        assert.equal(request.legal_actions.actions[index]?.choice, action.choice, `${testCase.name}:${index}`);
        assert.equal(request.legal_actions.actions[index]?.slot, action.slot, `${testCase.name}:${index}`);
      }
    }
  const action = canonicalActionFromLegalAction(request, testCase.legal_action.index);
  assert.equal(action.action_id, testCase.canonical_action.action_id);
  const serialized = serializeCanonicalAction(action, request);
  assert.equal(serialized, (testCase as FixtureCase & { serialized?: string }).serialized);
    assert.deepEqual(deserializeCanonicalAction(serialized, request), action, testCase.name);
    assert.equal(serializeCanonicalAction(action, request), serialized, testCase.name);
  }
});

test('canonical actions reject request, perspective, target, kind, and slot mismatches', () => {
  const testCase = fixture.cases[0];
  const request = requestFor(testCase);
  const action = canonicalActionFromLegalAction(request, testCase.legal_action.index);
  for (const [field, value] of [
    ['player', 'p2'],
    ['rqid', 99],
    ['target', '+1'],
    ['kind', 'switch'],
    ['move_slot', 4],
    ['move_slot', 99],
    ['index', 1],
    ['action_id', 'act-tampered'],
  ] as const) {
    const invalid = { ...action, [field]: value };
    assert.throws(() => serializeCanonicalAction(invalid, request));
  }
  assert.throws(() => serializeCanonicalAction({ ...action, extra: true } as typeof action & { extra: boolean }, request));
});

test('forced-switch requests reject move actions even when a malformed legal set includes one', () => {
  const testCase = fixture.cases[0];
  const request = requestFor(testCase);
  request.force_switch = true;
  assert.throws(() => canonicalActionFromLegalAction(request, testCase.legal_action.index), /Forced-switch/);
});

test('wait and team-preview requests expose no canonical action', () => {
  const testCase = fixture.cases[0];
  const legal_actions = createEmptyLegalActionSet();
  for (const phase of ['wait', 'team_preview'] as const) {
    const request = requestFor(testCase);
    request.wait = phase === 'wait';
    request.team_preview = phase === 'team_preview';
    request.legal_actions = legal_actions;
    assert.throws(() => canonicalActionFromLegalAction(request, 0));
  }
});
