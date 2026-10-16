import assert from 'node:assert/strict';
import test from 'node:test';
import { runInNewContext } from 'node:vm';
import { Teams } from 'pokemon-showdown';
import { canonicalActionFromLegalAction } from '../src/canonical_action';
import { LocalBattleEnv } from '../src/env_manager';
import { NativeBirthEnrollment } from '../src/owner_identity_crosswalk';
import { continuePipelineEpisode, runPipelineEpisode } from '../src/pipeline_episode';
import { createPipelineIntegrationSession, type PipelineIntegrationSession } from '../src/pipeline_integration';
import type { OwnedActionOrderRegistrations, OwnedDecisionInput, OwnedDecisionOrder } from '../src/owned_decision_input';
import type { PlayerID } from '../src/types';

const SEED = [101, 202, 303, 404] as const;
const BASIC_TEAMS = [
  'Alpha (Magikarp)\nAbility: Swift Swim\n- Splash\n- Tackle\n\nBeta (Magikarp)\nAbility: Swift Swim\n- Splash',
  'Gamma (Magikarp)\nAbility: Swift Swim\n- Splash\n- Tackle\n\nDelta (Magikarp)\nAbility: Swift Swim\n- Splash',
] as const;
type Recipients = Record<PlayerID, object>;

function recipients(): Recipients { return { p1: {}, p2: {} }; }

function registrations(
  registered: Recipients,
  onInput: (owner: PlayerID, input: OwnedDecisionInput) => readonly number[],
): OwnedActionOrderRegistrations {
  return Object.freeze({
    p1: Object.freeze({ recipient: registered.p1, callback: (input: OwnedDecisionInput) => onInput('p1', input) }),
    p2: Object.freeze({ recipient: registered.p2, callback: (input: OwnedDecisionInput) => onInput('p2', input) }),
  });
}

async function withTeams<T>(teams: readonly [string, string], run: () => Promise<T>): Promise<T> {
  const original = Teams.generate;
  let generated = 0;
  try {
    Teams.generate = function () {
      const team = teams[generated++];
      assert.ok(team, 'only the two registered teams are generated');
      return Teams.import(team)!;
    };
    return await run();
  } finally { Teams.generate = original; }
}

async function sessionWithTeams(teams: readonly [string, string], id: string, registered = recipients()): Promise<PipelineIntegrationSession> {
  return withTeams(teams, () => createPipelineIntegrationSession({
    battle_id: id, format: 'gen9randombattle', seed: [...SEED], knowledge_recipients: registered,
  }));
}

function assertIncompleteOwnerInput(input: OwnedDecisionInput, owner: PlayerID): void {
  assert.equal(input.completeness, 'incomplete');
  assert.equal(input.knowledge.projection.owner, owner);
  assert.equal(input.observation.perspective, owner);
  assert.ok(Object.isFrozen(input));
  assert.ok(Object.isFrozen(input.observation));
  assert.ok(Object.isFrozen(input.knowledge));
  assert.ok(Object.isFrozen(input.knowledge.projection.current));
  assert.ok(Object.isFrozen(input.action_context.legal_actions));
  assert.ok(Object.isFrozen(input.legal_indices));
  assert.deepEqual(input.legal_indices, input.action_context.legal_actions.available_indices);
  assert.equal('session' in input, false);
  assert.equal('environment' in input, false);
  assert.equal('recipient' in input, false);
}

function action(session: PipelineIntegrationSession, owner: PlayerID, choice: string) {
  const request = session.boundary.perspectives[owner].observation.request!;
  const legal = request.legal_actions.actions.find(candidate => candidate?.choice === choice);
  assert.ok(legal, `${choice} is legal for ${owner}`);
  return canonicalActionFromLegalAction(request, legal.index);
}

test('P57 actual runner gives both owners immutable incomplete inputs and uses a changed owned ability to order actions', async () => {
  const registered = recipients();
  const calls: PlayerID[] = [];
  let startingAbility: unknown;
  let currentAbility: unknown;
  const result = await withTeams([
    'Gardevoir\nAbility: Trace\n- Splash\n- Tackle',
    'Blissey\nAbility: Natural Cure\n- Splash',
  ], () => runPipelineEpisode({
    battle_id: 'p57-owned-ability-order', format: 'gen9randombattle', seed: [...SEED],
    limits: { max_transitions: 1 }, policy_id: 'p57-owned-ability/v1', accept_incomplete: true,
    knowledge_recipients: registered,
    owned_action_order: registrations(registered, (owner, input) => {
      calls.push(owner);
      assertIncompleteOwnerInput(input, owner);
      const subject = `${owner}:roster:1`;
      const originalFact = input.knowledge.projection.starting.find((fact: any) => fact.subject === subject && fact.property === 'ability');
      const currentFact = input.knowledge.projection.current.find((fact: any) => fact.subject === subject && fact.property === 'ability');
      if (owner === 'p1') {
        startingAbility = originalFact?.value?.data;
        currentAbility = currentFact?.value?.data;
        assert.equal(startingAbility, 'Trace');
        assert.equal(currentAbility, 'naturalcure');
        assert.ok(input.legal_indices.length > 1);
      }
      const indices = [...input.legal_indices];
      if (owner === 'p1' && currentAbility === 'naturalcure') {
        const tackle = input.action_context.legal_actions.actions.find(candidate => candidate?.choice === 'move 2');
        assert.ok(tackle);
        return [tackle.index, ...indices.filter(index => index !== tackle.index)];
      }
      return indices;
    }),
  }));
  assert.equal(result.counts.committed_transitions, 1);
  assert.deepEqual(calls, ['p1', 'p2']);
  assert.notEqual(currentAbility, startingAbility);
  const tackle = result.records.p1[0].input_observation.request!.legal_actions.actions.find(candidate => candidate?.choice === 'move 2');
  assert.ok(tackle);
  assert.equal(result.records.p1[0].action.index, tackle.index);
  const output = JSON.stringify(result);
  assert.doesNotMatch(output, /perspective-knowledge-consumer|owned-active-options|p57-private-sentinel/);
});

test('P57 forced and Revival decisions call only the acting owner; waiting and terminal owners receive no callback', async () => {
  const forcedRecipients = recipients();
  const forcedTeams = [
    'First (Snorlax)\nAbility: Immunity\n- Splash\n- Explosion\n\nHealer (Pawmot)\nAbility: Iron Fist\n- Revival Blessing\n- Splash\n\nReserve (Magikarp)\nAbility: Swift Swim\n- Splash',
    'Watcher (Giratina)\nAbility: Pressure\n- Splash\n\nWaitingReserve (Magikarp)\nAbility: Swift Swim\n- Splash',
  ] as const;
  const forced = await sessionWithTeams(forcedTeams, 'p57-forced-owner', forcedRecipients);
  try {
    await forced.step({ p1: action(forced, 'p1', 'move 2'), p2: action(forced, 'p2', 'move 1') });
    assert.equal(forced.boundary.kind, 'one_sided_forced_switch');
    const actor = (['p1', 'p2'] as const).find(owner => forced.boundary.perspectives[owner].observation.request?.force_switch)!;
    const waiting = actor === 'p1' ? 'p2' : 'p1';
    let called: PlayerID[] = [];
    const before = forced.boundary;
    assert.throws(() => forced.withOwnedDecisionInput(forcedRecipients[waiting], () => {
      called.push(waiting);
      return [];
    }), /owned-decision-input\/v1/);
    assert.equal(called.length, 0);
    const forcedResult = await continuePipelineEpisode(forced, {
      limits: { max_transitions: 1 }, policy_id: 'p57-forced/v1', accept_incomplete: true,
      owned_action_order: registrations(forcedRecipients, (owner, input) => {
        called.push(owner); assertIncompleteOwnerInput(input, owner); return input.legal_indices;
      }),
    });
    assert.equal(forcedResult.counts.committed_transitions, 1);
    assert.deepEqual(called, [actor]);
    assert.equal(forcedResult.initial_boundary?.step_index, before.step_index);
  } finally { await forced.close(); }

  const revivalRecipients = recipients();
  const revival = await sessionWithTeams(forcedTeams, 'p57-revival-owner', revivalRecipients);
  try {
    await revival.step({ p1: action(revival, 'p1', 'move 2'), p2: action(revival, 'p2', 'move 1') });
    assert.equal(revival.boundary.kind, 'one_sided_forced_switch');
    await revival.stepForcedSwitch(action(revival, 'p1', 'switch 2'));
    await revival.step({ p1: action(revival, 'p1', 'move 1'), p2: action(revival, 'p2', 'move 1') });
    assert.equal(revival.boundary.kind, 'one_sided_revival');
    const called: PlayerID[] = [];
    const revivalResult = await continuePipelineEpisode(revival, {
      limits: { max_transitions: 1 }, policy_id: 'p57-revival/v1', accept_incomplete: true,
      owned_action_order: registrations(revivalRecipients, (owner, input) => {
        called.push(owner); assertIncompleteOwnerInput(input, owner); return [...input.legal_indices].reverse();
      }),
    });
    assert.equal(revivalResult.counts.committed_transitions, 1);
    assert.deepEqual(called, ['p1']);
  } finally { await revival.close(); }

  const registered = recipients();
  const terminal = await sessionWithTeams([
    'Attacker (Mewtwo)\nAbility: Pressure\n- Psystrike',
    'Target (Magikarp)\nLevel: 1\nAbility: Swift Swim\n- Splash',
  ], 'p57-terminal-owner', registered);
  try {
    await terminal.step({ p1: action(terminal, 'p1', 'move 1'), p2: action(terminal, 'p2', 'move 1') });
    assert.equal(terminal.boundary.kind, 'terminal');
    const called: PlayerID[] = [];
    const result = await continuePipelineEpisode(terminal, {
      policy_id: 'p57-terminal/v1', accept_incomplete: true,
      owned_action_order: registrations(registered, (owner, input) => {
        called.push(owner); return input.legal_indices;
      }),
    });
    assert.equal(result.counts.attempts, 0);
    assert.deepEqual(called, []);
  } finally { await terminal.close(); }
});

test('P57 order authority rejects copied, foreign, stale, wrong-owner, and unsupported orders', async () => {
  const registered = recipients();
  const session = await sessionWithTeams(BASIC_TEAMS, 'p57-order-authority', registered);
  const foreignRecipients = recipients();
  const foreign = await sessionWithTeams(BASIC_TEAMS, 'p57-order-foreign', foreignRecipients);
  const copiedRecipients = recipients();
  const copiedSession = await sessionWithTeams(BASIC_TEAMS, 'p57-order-copy', copiedRecipients);
  try {
    type Contexts = Record<PlayerID, OwnedDecisionInput['action_context']>;
    const contexts = (): Contexts => ({} as Contexts);
    const makeOrders = (target: PipelineIntegrationSession, authority: Recipients, captured: Contexts) => [
      target.withOwnedDecisionInput(authority.p1, input => { captured.p1 = input.action_context; return input.legal_indices; }),
      target.withOwnedDecisionInput(authority.p2, input => { captured.p2 = input.action_context; return input.legal_indices; }),
    ] as const;
    const ownContext = contexts();
    const foreignContext = contexts();
    const [ownP1, ownP2] = makeOrders(session, registered, ownContext);
    const [foreignP1, foreignP2] = makeOrders(foreign, foreignRecipients, foreignContext);
    for (const owner of ['p1', 'p2'] as const) {
      assert.deepEqual(ownContext[owner], foreignContext[owner]);
      assert.notStrictEqual(ownContext[owner], foreignContext[owner]);
      const ownDelivery = session.readRequestDeliveryHistory(session.getRequestDeliveryHandle(owner), owner).boundaries.at(-1)!.current!;
      const foreignDelivery = foreign.readRequestDeliveryHistory(foreign.getRequestDeliveryHandle(owner), owner).boundaries.at(-1)!.current!;
      assert.notStrictEqual(ownDelivery.delivery_reference, foreignDelivery.delivery_reference);
      assert.notStrictEqual(ownDelivery.source.producer_occurrence, foreignDelivery.source.producer_occurrence);
    }
    session.assertOwnedDecisionBatch([ownP1, ownP2]);
    assert.throws(() => session.assertOwnedDecisionBatch([foreignP1, foreignP2]), /owned-decision-input\/v1/);

    const [copiedP1, copiedP2] = makeOrders(copiedSession, copiedRecipients, contexts());
    const copied = Object.freeze({ indices: [...copiedP1.indices] }) as OwnedDecisionOrder;
    assert.throws(() => copiedSession.assertOwnedDecisionBatch([copied, copiedP2]), /owned-decision-input\/v1/);

    const originalJson = {} as Record<PlayerID, string>;
    const originalDelivery = {} as Record<PlayerID, object>;
    const originalProducer = {} as Record<PlayerID, object>;
    for (const owner of ['p1', 'p2'] as const) {
      const delivery = session.readRequestDeliveryHistory(session.getRequestDeliveryHandle(owner), owner).boundaries.at(-1)!.current!;
      originalJson[owner] = delivery.source.request_json;
      originalDelivery[owner] = delivery.delivery_reference;
      originalProducer[owner] = delivery.source.producer_occurrence;
    }
    const [oldP1, oldP2] = makeOrders(session, registered, contexts());
    for (let turn = 0; turn < 2; turn++) {
      await session.step({ p1: action(session, 'p1', 'switch 2'), p2: action(session, 'p2', 'switch 2') });
    }
    for (const owner of ['p1', 'p2'] as const) {
      const delivery = session.readRequestDeliveryHistory(session.getRequestDeliveryHandle(owner), owner).boundaries.at(-1)!.current!;
      assert.equal(delivery.source.request_json, originalJson[owner]);
      assert.notStrictEqual(delivery.delivery_reference, originalDelivery[owner]);
      assert.notStrictEqual(delivery.source.producer_occurrence, originalProducer[owner]);
    }
    assert.throws(() => session.assertOwnedDecisionBatch([oldP1, oldP2]), /owned-decision-input\/v1/);

    const swapped = recipients();
    let wrongOwnerCallback = 0;
    const result = await withTeams(BASIC_TEAMS, () => runPipelineEpisode({
      battle_id: 'p57-order-wrong-owner', format: 'gen9randombattle', seed: [...SEED],
      limits: { max_transitions: 1 }, policy_id: 'p57-wrong-owner/v1', accept_incomplete: true,
      knowledge_recipients: swapped,
      owned_action_order: Object.freeze({
        p1: Object.freeze({ recipient: swapped.p2, callback: (input: OwnedDecisionInput) => { wrongOwnerCallback++; return input.legal_indices; } }),
        p2: Object.freeze({ recipient: swapped.p1, callback: (input: OwnedDecisionInput) => { wrongOwnerCallback++; return input.legal_indices; } }),
      }),
    }));
    assert.equal(result.counts.attempts, 0);
    assert.equal(result.counts.committed_transitions, 0);
    assert.equal(wrongOwnerCallback, 0);

    const differentRecipients = recipients();
    const callerSession = await sessionWithTeams(BASIC_TEAMS, 'p57-new-recipient-continuation', differentRecipients);
    try {
      const alien = recipients();
      let alienCallback = 0;
      const continuation = await continuePipelineEpisode(callerSession, {
        policy_id: 'p57-new-recipient/v1', accept_incomplete: true,
        owned_action_order: registrations(alien, (_owner, input) => { alienCallback++; return input.legal_indices; }),
      });
      assert.equal(continuation.counts.attempts, 0);
      assert.equal(continuation.counts.committed_transitions, 0);
      assert.equal(alienCallback, 0);
    } finally { await callerSession.close(); }

    const unsupportedRecipients = recipients();
    const transfer = NativeBirthEnrollment.prototype.transferRequestHealthActors;
    let unsupported: PipelineIntegrationSession;
    try {
      NativeBirthEnrollment.prototype.transferRequestHealthActors = function (enrollment, battle) {
        transfer.call(this, enrollment, battle);
        battle.p1!.active[0].addVolatile('mustrecharge');
      };
      unsupported = await sessionWithTeams(BASIC_TEAMS, 'p57-unsupported-owner', unsupportedRecipients);
    } finally { NativeBirthEnrollment.prototype.transferRequestHealthActors = transfer; }
    try {
      const held = unsupported.readOwnerKnowledge(unsupported.getOwnerKnowledgeHandle(unsupportedRecipients.p1), unsupportedRecipients.p1);
      assert.equal(held.projection.request?.state, 'unsupported');
      let unsupportedCallback = 0;
      assert.throws(() => unsupported.withOwnedDecisionInput(unsupportedRecipients.p1, () => {
        unsupportedCallback++; return [];
      }), error => error instanceof Error && error.message === 'owned-decision-input/v1/stale-or-unsupported-frame');
      assert.equal(unsupportedCallback, 0);
    } finally { await unsupported.close(); }
  } finally { await copiedSession.close(); await foreign.close(); await session.close(); }
});

test('P57 callback exceptions promises invalid permutations reentrancy and close fail before transitions', async () => {
  const originalGenerate = Teams.generate;
  let generatedTeams = 0;
  let optionCallbackCalls = 0;
  Teams.generate = function () { generatedTeams++; return Teams.import(BASIC_TEAMS[0])!; };
  try {
    const invalidVariants: Array<{ label: string; override: Record<string, unknown> }> = [
      { label: 'missing incomplete-input acknowledgement', override: { accept_incomplete: undefined } },
      { label: 'false incomplete-input acknowledgement', override: { accept_incomplete: false } },
      { label: 'unversioned policy', override: { policy_id: 'p57-unversioned' } },
      { label: 'legacy ordering coexistence', override: { action_order: () => [0] } },
    ];
    for (const variant of invalidVariants) {
      const registered = recipients();
      const result = await runPipelineEpisode({
        battle_id: `p57-options-${variant.label}`, format: 'gen9randombattle', seed: [...SEED],
        limits: { max_transitions: 1 }, policy_id: 'p57-options/v1', accept_incomplete: true,
        knowledge_recipients: registered,
        owned_action_order: registrations(registered, (_owner, input) => { optionCallbackCalls++; return input.legal_indices; }),
        ...variant.override,
      } as any);
      assert.equal(result.stop.code, 'episode/v1/invalid-options', variant.label);
      assert.equal(result.counts.attempts, 0, variant.label);
      assert.equal(result.counts.committed_transitions, 0, variant.label);
      assert.equal(optionCallbackCalls, 0, variant.label);
      assert.equal(generatedTeams, 0, variant.label);
    }
  } finally { Teams.generate = originalGenerate; }

  const registered = recipients();
  const session = await sessionWithTeams(BASIC_TEAMS, 'p57-callback-errors', registered);
  const boundary = session.boundary;
  try {
    const firstOwnerOrder = session.withOwnedDecisionInput(registered.p1, input => input.legal_indices);
    assert.throws(() => session.withOwnedDecisionInput(registered.p2, () => { throw new Error('second-owner failure'); }),
      error => error instanceof Error && error.message === 'owned-decision-input/v1/callback-failed');
    const freshSecondOwnerOrder = session.withOwnedDecisionInput(registered.p2, input => input.legal_indices);
    assert.throws(() => session.assertOwnedDecisionBatch([firstOwnerOrder, freshSecondOwnerOrder]),
      /owned-decision-input\/v1\/(foreign-or-stale-order|invalid-batch)/);

    assert.throws(() => session.withOwnedDecisionInput(registered.p1, () => { throw new Error('private callback payload'); }),
      error => error instanceof Error && error.message === 'owned-decision-input/v1/callback-failed');
    assert.throws(() => session.withOwnedDecisionInput(registered.p1, (() => Promise.resolve([0])) as any),
      /owned-decision-input\/v1\/synchronous-callback-required/);
    const foreignRejection = runInNewContext('Promise.reject(new Error("private foreign payload"))') as Promise<unknown>;
    assert.throws(() => session.withOwnedDecisionInput(registered.p1, (() => foreignRejection) as any),
      /owned-decision-input\/v1\/synchronous-callback-required/);
    assert.throws(() => session.withOwnedDecisionInput(registered.p1, () => []), /owned-decision-input\/v1\/invalid-order/);
    assert.throws(() => session.withOwnedDecisionInput(registered.p1, input => new Proxy([...input.legal_indices], {
      get(target, property, receiver) {
        if (property === '0') throw new Error('owned-decision-input/v1/private callback payload');
        return Reflect.get(target, property, receiver);
      },
    })), error => error instanceof Error && error.message === 'owned-decision-input/v1/invalid-order');
    const pendingP1 = session.withOwnedDecisionInput(registered.p1, input => input.legal_indices);
    const pendingP2 = session.withOwnedDecisionInput(registered.p2, input => input.legal_indices);
    const malformedBatch = new Proxy([pendingP1, pendingP2], {
      get(target, property, receiver) {
        if (property === Symbol.iterator) throw new Error('owned-decision-input/v1/private batch payload');
        return Reflect.get(target, property, receiver);
      },
    });
    assert.throws(() => session.assertOwnedDecisionBatch(malformedBatch),
      error => error instanceof Error && error.message === 'owned-decision-input/v1/stale-or-unsupported-frame');
    let reentrant: Promise<unknown> | undefined;
    assert.throws(() => session.withOwnedDecisionInput(registered.p1, input => {
      reentrant = session.step(); void reentrant.catch(() => undefined);
      return input.legal_indices;
    }), /owned-decision-input\/v1\/stale-or-unsupported-frame/);
    await assert.rejects(reentrant!, /owned-decision-input\/v1\/reentrant-call/);
    assert.equal(session.boundary, boundary);
    let closeResult: Promise<void> | undefined;
    assert.throws(() => session.withOwnedDecisionInput(registered.p1, input => {
      closeResult = session.close(); void closeResult.catch(() => undefined);
      return input.legal_indices;
    }), /owned-decision-input\/v1\/revoked/);
    await closeResult;
  } finally { await session.close(); }
});

test('P57 rejected candidate reissues owner frames from the unchanged committed boundary', async () => {
  const registered = recipients();
  const inputs: Record<PlayerID, OwnedDecisionInput[]> = { p1: [], p2: [] };
  const original = LocalBattleEnv.prototype.diagnostics;
  let rejected = false;
  try {
    LocalBattleEnv.prototype.diagnostics = function () {
      const base = original.call(this) as Record<string, unknown>;
      if (!rejected && this.id.includes('pipeline-step-0')) {
        rejected = true;
        const players = base.players as Record<PlayerID, Record<string, unknown>>;
        return { ...base, players: { ...players, p1: { ...players.p1, last_choice_error: { message: 'P57 scoped candidate rejection' } } } };
      }
      return base;
    };
    const result = await withTeams(BASIC_TEAMS, () => runPipelineEpisode({
      battle_id: 'p57-rejection-retry', format: 'gen9randombattle', seed: [...SEED],
      limits: { max_transitions: 1, max_attempts: 3, max_rejections_per_boundary: 2 },
      policy_id: 'p57-retry/v1', accept_incomplete: true, knowledge_recipients: registered,
      owned_action_order: registrations(registered, (owner, input) => {
        inputs[owner].push(input);
        return [...input.legal_indices].reverse();
      }),
    }));
    assert.equal(rejected, true);
    assert.equal(result.counts.rejected_candidates, 1);
    assert.equal(result.counts.committed_transitions, 1);
    for (const owner of ['p1', 'p2'] as const) {
      assert.equal(inputs[owner].length, 2);
      assert.notEqual(inputs[owner][0], inputs[owner][1]);
      assert.equal(inputs[owner][0].observation, inputs[owner][1].observation);
      assert.deepEqual(inputs[owner][0].knowledge, inputs[owner][1].knowledge);
    }
  } finally { LocalBattleEnv.prototype.diagnostics = original; }
});
